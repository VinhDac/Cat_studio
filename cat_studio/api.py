"""Cat_Studio — bề mặt DUY NHẤT giao diện web gọi tới.

    JS  →  window.pywebview.api.<tên>()  →  api.py  →  core.py

Hai luật của file này:

1. **KHÔNG BAO GIỜ ném lỗi qua cầu nối.** Mọi hàm công khai bọc `@_bat_loi`, luôn trả
   `{"ok": bool, "value": …, "error": str, "trace": str}`. Một exception lọt qua là
   promise bên JS treo vĩnh viễn, không có thông báo gì.

2. **Mọi thuộc tính không-callable trên `Api` PHẢI bắt đầu bằng `_`.**
   pywebview duyệt `dir(js_api)` để liệt kê hàm; gặp một thuộc tính là đối tượng
   Window, nó đọc trúng property `width`/`title`… mà mấy property đó lại quay về
   UI thread đang bị chặn → app treo "Not Responding" vĩnh viễn.
"""
import datetime
import functools
import inspect
import json
import os
import threading
import time
import traceback

from . import core
from . import kho
from . import cham_diem
from . import gui_lenh
from . import ket_noi
from . import khung_cua_so
from . import luot_tim
from . import nguoi_bay
from . import phien_live
from . import bo_chay
from . import lich_su
from . import luu_tru
from . import nguon_nen
from . import nhat_ky
from . import so_lenh
from . import tinh_toan


def _bat_loi(fn):
    """Bọc một phương thức: không bao giờ ném lỗi qua cầu nối.

    ⚠ `__signature__` KHÔNG được quên. pywebview dựng hàm JS bằng
    `inspect.getfullargspec(attr).args[1:]` (webview/util.py, `get_functions`), và
    `getfullargspec` KHÔNG lần theo `__wrapped__` của `functools.wraps`. Một wrapper
    `(*a, **kw)` trần vì thế khai báo ra hàm JS KHÔNG THAM SỐ NÀO — mọi đối số bên JS
    gửi đi đều bị vứt IM LẶNG, và lỗi hiện ra ở tận đâu đâu ("khối rỗng", "sơ đồ mất
    dây") chứ không phải ở chỗ gọi.
    Gán `__signature__` là cách duy nhất bắt `getfullargspec` thấy đúng tham số thật."""
    @functools.wraps(fn)
    def bao(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc(limit=6)}
    bao.__signature__ = inspect.signature(fn)
    return bao


def _ok(v=None, **them):
    ra = {"ok": True, "value": v}
    ra.update(them)
    return ra


def _loi(chu):
    """Thất bại CÓ LÝ DO ĐỌC ĐƯỢC — khác với ngoại lệ. Cùng hình dạng với `_bat_loi` trả
    về, nên phía JS chỉ có một chỗ để kiểm tra."""
    return {"ok": False, "error": chu}


# ---------------------------------------------------------------------------
# Hành động mặc định
# ---------------------------------------------------------------------------


def _hanh_dong_mac_dinh(loai):
    """Giá trị khởi điểm của một hành động mới.

    Cố ý là những con số DÙNG ĐƯỢC NGAY chứ không phải 0: mặc định của Compress EA
    (ATR 14, ngưỡng 7 bps, SL 1.5×ATR, TP 2R) đã chạy được trên nhiều symbol, nên
    người dùng mới có thứ hợp lý để sửa chứ không phải bịa từ số không."""
    if loai == core.VAO_LENH:
        return {"type": loai, "huong": "mua", "loai": "stop", "rui_ro": 0.5,
                "dem": {"tinh": "atr", "value": 0.1},
                "sl": {"tinh": "atr", "value": 1.5},
                "tp": {"tinh": "R", "value": 2}}
    if loai == core.SUA_LENH:
        return {"type": loai, "che_do": "hoa_von"}
    return {"type": core.CHECK_COND, "conditions": [{
        "trai": {"ten": "atr", "tf": "M5", "period": 14}, "don_vi": "atr_nen",
        "phep": "<", "phai": {"value": 0.75, "tinh": "atr_nen"}}]}


# ---------------------------------------------------------------------------
# Thẻ vẽ lên hộp — NỘI DUNG DO PYTHON SINH
# ---------------------------------------------------------------------------


def _spread(symbol, ci, meta):
    """Spread (điểm) cho một lần chạy — GÕ TAY thắng, không có thì lấy SỐ ĐO ĐƯỢC.

    core.md §16.2. Ngược thứ tự với luật sàn (§16.1) là có lý do: luật sàn là thứ sàn
    ÁP ĐẶT nên số đo luôn đúng hơn, còn spread là **điều kiện chạy thử** — người dùng
    có quyền hỏi "nếu spread xấu gấp đôi thì sao", và đó là một câu hỏi đúng đắn.

    ⚠ KHÔNG có số bịa cuối cùng. Mặc định cũ là `20`, và đo được nó làm sơ đồ mẫu 2025
    ra **+12,78 R** trong khi spread thật (97) cho **+6,66 R** — một con số bịa làm
    chiến lược thua trông như đang thắng. Không đo được và cũng không gõ tay thì NÓI TO,
    đúng nếp câu lỗi "chưa đặt khoảng thời gian".
    """
    sp = ci.get("spread_diem") or meta.get("spread_tb")
    if not sp:
        raise RuntimeError(
            f"Chưa biết spread của {symbol}.\n\n"
            f"Tải nến từ MT5 thì app tự đo (trung vị spread cất cạnh kho nến), hoặc "
            f"điền ô Spread ở Cài đặt → Strategy Test.\n\n"
            f"Cố ý KHÔNG đoán: spread quyết định cả kết quả — cùng sơ đồ mẫu, spread 20 "
            f"điểm cho +12,78 R còn spread thật 97 điểm cho +6,66 R.")
    return float(sp)


#: Ba thứ TẢ CHÍNH SYMBOL, đi liền một bộ. Không phải cài đặt — không ai được gõ tay,
#: vì chúng là sự thật của sàn, không phải điều kiện chạy thử (khác `spread`, xem `_spread`).
THONG_SO_SYMBOL = ("point", "contract_size", "digits")


def _thong_so(symbol, meta):
    """`point` · `contract_size` · `digits` cho `CaiDat` — thiếu thì NỔ, không đoán.

    core.md §16.3. Trước đây ba dòng này là `meta.get(k) or <số>`, và mấy con số ấy
    (`0.01` · `100.0` · `2`) **sai cho chính XAUUSD** — kho nến ghi `0.001` · `100.0` ·
    `3`. Chúng chưa nổ chỉ vì kho nến hiện tại có đủ meta; symbol mới thiếu meta là chạy
    bằng số bịa mà không ai biết.

    ⚠ `point` là thứ chết người: nó nhân vào SPREAD, `stops_level` và TRƯỢT GIÁ. Đo trên
    sơ đồ mẫu 2025 — cùng sơ đồ, cùng bộ nến, chỉ thay `point` 0,001 → 0,01:

        meta thật   +1,25 % vốn · 284 lệnh
        số bịa      −8,48 % vốn ·  52 lệnh      (spread 0,097 $ → 0,970 $)

    Cùng nếp `_spread`: không đo được thì NÓI TO. Một lượt chạy sai mà im lặng tệ hơn
    hẳn một lượt chạy không được.
    """
    ra = {}
    for k in THONG_SO_SYMBOL:
        v = (meta or {}).get(k)
        if v in (None, "", 0):
            raise RuntimeError(
                f"Chưa biết `{k}` của {symbol}.\n\n"
                f"Ba thông số này (point · contract_size · digits) cất cạnh kho nến, do "
                f"MT5 cấp lúc tải. Tải lại nến của {symbol} là có.\n\n"
                f"Cố ý KHÔNG đoán: `point` nhân vào spread, stops level và trượt giá — "
                f"sai 10 lần thì cùng một sơ đồ đang +1,25 % vốn thành −8,48 %, và 232 "
                f"trong 284 lệnh biến mất mà không báo gì.")
        ra[k] = v
    return ra


def _luat_san(symbol, ci):
    """Bốn luật sàn cho `CaiDat` — HỒ SƠ ĐÃ ĐO thắng, ô gõ tay là dự phòng.

    core.md §16.1. Thứ tự đó là chủ ý và trùng nếp §14.9 (*hồ sơ là CACHE CỦA PHÉP ĐO,
    không phải cài đặt*): một con số đo được từ chính cái sàn ấy luôn đúng hơn một con
    số gõ tay. Chưa từng hiệu chuẩn symbol này thì rơi về ô trong Cài đặt, và ô đó rơi
    về mặc định — nên app vẫn chạy khi chưa nối sàn lần nào.

    Trả kèm khoá `_nguon` KHÔNG được: `CaiDat` không nhận. Ai muốn biết nguồn thì gọi
    `ket_noi.luat_san` — `bootstrap` làm đúng thế để giao diện hiện ra.
    """
    hs = ket_noi.luat_san(symbol) or {}
    ra = {}
    for k in ket_noi.LUAT_SAN:
        v = hs.get(k)
        if v in (None, ""):
            v = ci.get(k, luu_tru.CAI_DAT_MAC_DINH["test"][k])
        ra[k] = v
    return ra


def _mau_khoi(st):
    """Khoá MÀU của khối — ngữ nghĩa, không phải mã màu. Giao diện tự ánh xạ sang biến
    CSS, nên đổi bảng màu là việc của CSS, không phải sửa Python.

    Suy từ `type` + `huong` — đều là phạm trù của chính app (không phải khái niệm riêng
    của một chiến lược), nên chiến lược nào sau này cũng ra màu đúng."""
    if core.is_start_step(st):
        return "start"
    t = st.get("type")
    if t == core.VAO_LENH:
        return "ban" if st.get("huong") == "ban" else "mua"
    if t == core.SUA_LENH:
        return "sua"
    return "hoi"


def _the_buoc(st, ts=None, tab=None):
    """Một khối -> thẻ để giao diện vẽ.

    Giao diện KHÔNG tự ghép chữ: nếu nó ghép thì sớm muộn nó mô tả khác với thứ lõi
    thực sự hiểu. Nó chỉ chọn ICON theo `type`.

    Chữ trên hộp lấy từ `core.dong_khoi` — dòng NGẮN, mỗi trường một dòng. Câu đầy đủ
    (`core.action_display`) để dành cho tooltip: nhìn hộp thì cần liếc ra ngay, rê chuột
    mới cần biết đủ chi tiết."""
    the = {"id": st.get("id"), "kind": st.get("kind"), "title": core.step_title(st),
           "badges": [], "lines": [], "mo_ta": "", "ghim": bool(st.get("ghim")),
           "la_cong": core.is_branch_gate(st), "mau": _mau_khoi(st)}

    the["lines"] = [{"text": x, "type": st.get("type")}
                    for x in core.dong_khoi(st, ts, tab)]

    if core.is_start_step(st):
        the["badges"] = ["chạy lại từ đây"]
        the["nhip"] = st.get("nhip")
        the["mo_ta"] = ("Điểm neo đánh số. Cả sơ đồ là một vòng lặp — mỗi nến "
                        f"{st.get('nhip')} nó chạy lại từ khối này.")
        return the

    # Bỏ `name` trước khi sinh câu đầy đủ: tiêu đề hộp ĐÃ hiện tên rồi.
    the["mo_ta"] = core.action_display(
        {k: v for k, v in st.items() if k != "name"}, ts)

    if st.get("type") == core.CHECK_COND:
        n = len(st.get("conditions") or [])
        the["badges"].append("cổng rẽ nhánh" if core.is_branch_gate(st) else "kiểm tra")
        # Khối CÓ điều kiện thì chữ tự nói (`Giá đóng cửa(M15) > MA(M15, 50)`), nhưng
        # khối RỖNG ở hai cơ chế nhìn giống hệt nhau — nhãn này là chỗ phân biệt duy nhất.
        if st.get("so_dai_luong"):
            the["badges"].append("so hai đại lượng")
        if n > 1:
            the["badges"].append(f"{n} điều kiện · VÀ")
    return the


def _kem_the(doc):
    """Gắn `cards` vào từng sơ đồ. Chữ trên hộp do Python sinh, JS không ghép lại.

    Truyền cả bảng tham số xuống để dòng chữ hiện `ngưỡng nén = 7` thay vì trơ ra một
    cái tên không ai biết bằng bao nhiêu.

    ⚠ CHUẨN HOÁ NGAY TẠI ĐÂY, chứ không tin từng chỗ gọi nhớ làm. Đây là hàm DUY NHẤT
    chuẩn bị một doc cho giao diện, nên nó phải là chỗ bảo đảm luật *"mọi doc tới tay
    giao diện đều đã chuẩn hoá"*.

    Vì sao gắt thế, có ca thật: `demo_process` từng gọi `_kem_the(_so_do_mau())` — thiếu
    đúng một lời gọi `normalize_process`. Sơ đồ mẫu vì vậy thiếu cờ `so_dai_luong` (cờ
    này chỉ chuẩn hoá mới sinh ra được), nên mở cổng "Xu hướng LÊN?" ra thì hộp thoại
    tưởng là cơ chế "so với giá trị": ô số trắng trơn, cột đơn vị in "giá tuyệt đối".
    Mà CHỮ TRÊN THẺ vẫn đúng — `cond_display` tự SUY từ `phai.ten` chứ không đọc cờ. Hai
    nguồn cho một sự thật, và cái lệch thì im lặng.

    Lỗ đó có từ trước; nó chỉ lộ ra khi `so_dai_luong` thành trường đầu tiên mà giao diện
    KHÔNG suy lại được. Vá dòng 449 thì lần sau ai thêm endpoint mới lại quên tiếp.

    An toàn vì `normalize_process` BẤT BIẾN — chạy hai lần bằng đúng một lần
    (`tests/test_so_do_mau.py` canh chuyện đó), nên mấy chỗ đã chuẩn hoá rồi gọi thêm
    một lần nữa cũng không đổi gì."""
    doc = core.normalize_process(doc)
    ts = core.bang_tham_so(doc)
    for tab in core.TABS:
        g = doc.get(tab) or {"steps": [], "edges": []}
        g["cards"] = [_the_buoc(s, ts, tab) for s in g.get("steps") or []]
        doc[tab] = g
    return doc


# ---------------------------------------------------------------------------
class NenCuaSo:
    """Phần CHUNG của một cửa sổ tự vẽ khung: giữ cửa sổ của CHÍNH MÌNH và vá khung
    của CHÍNH MÌNH.

    ⚠ Vì sao phải tách ra thành lớp nền — ba lỗi đã có thật, không phải giả định:

      1. `_mo_cua_so_tester` truyền `js_api=self`, tức cửa sổ tester dùng CHUNG một
         `Api` với cửa sổ chính, mà `self._window` lại trỏ cửa sổ chính. Bấm ✕ trên
         thanh tiêu đề tự vẽ của tester gọi `cua_so_dong()` → `self._window.destroy()`
         → ĐÓNG CỬA SỔ CHÍNH. Thu nhỏ, phóng to, đổi tiêu đề, hộp thoại file: nhắm
         nhầm cửa sổ y hệt.
      2. `KhungTuVe` giữ đúng MỘT `hwnd` và MỘT bảng vùng-cấm. Kéo thanh tiêu đề của
         tester `PostMessage` vào hwnd cửa sổ chính → kéo nhầm cửa sổ.
      3. Hai cửa sổ ghi đè vùng cấm của nhau, nên chỗ có nút bấm ở cửa sổ này lại
         thành chỗ kéo được ở cửa sổ kia.

    Mỗi cửa sổ một thể hiện của lớp này là hết cả ba, và không phải nhớ kỷ luật gì."""

    #: Hậu tố tiêu đề. Lớp con đổi cái này chứ không viết lại `set_title`.
    _HAU_TO = "Cat Studio"

    def __init__(self):
        # Gạch dưới hết — xem chú thích đầu file.
        self._window = None
        self._khung = khung_cua_so.KhungTuVe()

    # -- gắn cửa sổ (Python gọi, không phải JS) --
    def _gan_window(self, w):
        self._window = w

    def _va_khung(self, chua_chuoi, cho=4.0, nhip=0.15):
        """Tìm hwnd theo tiêu đề rồi vá khung. THỬ LẠI cho tới `cho` giây.

        ⚠ Phải thử lại chứ không hẹn giờ một phát: `webview.create_window` trả về NGAY,
        còn việc dựng cửa sổ thật thì đẩy sang UI thread. Đo được — hẹn 0,45 s thì
        `tim_hwnd` chạy lúc cửa sổ chưa `IsWindowVisible`, không thấy gì, và cửa sổ mở
        ra frameless mà KHÔNG kéo được: trông y như lỗi của `khung_cua_so`.

        Vá hỏng thật thì cửa sổ vẫn dùng được, chỉ là không kéo/giãn được — thà vậy còn
        hơn không mở nổi."""
        het = time.monotonic() + cho
        while time.monotonic() < het:
            h = khung_cua_so.tim_hwnd(chua_chuoi)
            if h and self._khung.va(h):
                return True
            time.sleep(nhip)
        return False

    def _ban(self, ten, du_lieu):
        """Đẩy sự kiện sang JS của CHÍNH cửa sổ này. Nuốt lỗi: cửa sổ có thể đã đóng
        giữa chừng."""
        if not self._window:
            return
        try:
            self._window.evaluate_js(
                f"window.__su_kien && window.__su_kien("
                f"{json.dumps(ten)}, {json.dumps(du_lieu, ensure_ascii=False)})")
        except Exception:
            pass

    # ------------------------------------------------------- khung cửa sổ
    # Xem `khung_cua_so.py`: kéo/giãn PHẢI do web khởi động, vì WebView2 là cửa sổ con
    # phủ kín cửa sổ cha nên cha không bao giờ nhận được chuột.
    @_bat_loi
    def vung_khong_keo(self, vung, cao):
        self._khung.dat_vung_cam(vung, cao)
        return _ok(True)

    @_bat_loi
    def keo_cua_so(self, ht):
        return _ok(self._khung.bat_dau_keo(ht))

    @_bat_loi
    def cua_so_thu_nho(self):
        self._window.minimize()
        return _ok(True)

    @_bat_loi
    def cua_so_phong_to(self):
        self._khung.phong_to_hay_khoi_phuc(self._window)
        return _ok(self._khung.dang_phong_to())

    @_bat_loi
    def cua_so_dang_phong_to(self):
        return _ok(self._khung.dang_phong_to())

    @_bat_loi
    def cua_so_dong(self):
        self._window.destroy()
        return _ok(True)

    @_bat_loi
    def set_title(self, ten):
        if self._window:
            self._window.set_title(f"{ten} — {self._HAU_TO}" if ten else self._HAU_TO)
        return _ok(True)


class Api(NenCuaSo):
    """Mọi phương thức công khai ở đây thành `window.pywebview.api.<tên>` bên JS."""

    def __init__(self):
        super().__init__()
        self._tester = None          # cửa sổ Strategy Tester (pywebview Window)
        self._api_tester = None      # Api RIÊNG của cửa sổ đó
        self._live = None            # cửa sổ Live
        self._api_live = None
        self._rl = None              # cửa sổ RL (§18.6)
        self._api_rl = None
        self._doc_tester = None
        self._cai_dat = core.load_settings()
        self._khoa = threading.Lock()

    # ------------------------------------------------------------------ cơ bản
    @_bat_loi
    def ping(self):
        return _ok("pong")

    @_bat_loi
    def bootstrap(self):
        """Mọi hằng số giao diện cần, lấy MỘT lần lúc mở app.

        JS không viết cứng danh sách nào — nhãn, khung thời gian, toán hạng, phép so
        đều từ đây. Thêm một toán hạng ở core là giao diện có ngay, không phải sửa JS."""
        return _ok({
            "phien_ban": core.PHIEN_BAN,
            "settings": self._cai_dat,
            "app_dir": core.app_dir(),
            "nguon": nguon_nen.liet_ke(),
            "co_mt5": nguon_nen.CO_MT5,
            # LUẬT SÀN đã ĐO ĐƯỢC, theo từng symbol — §16.1. Giao diện dùng nó để nói rõ
            # số đang chạy đến từ ĐÂU: hồ sơ hiệu chuẩn hay ô gõ tay. Không nói thì người
            # dùng sửa ô mà không hiểu vì sao kết quả không đổi.
            "luat_san": {s: ls for s in {
                (self._cai_dat.get("test") or {}).get("symbol"),
                self._cai_dat.get("symbol"), "XAUUSD"} if s
                for ls in [ket_noi.luat_san(s)] if ls},

            "kinds": [core.KIND_START, core.KIND_ACTION],
            "kind_labels": core.KIND_LABELS,

            "tabs": core.TABS,
            "tab_labels": core.TAB_LABELS,
            "action_types": core.ACTION_TYPES,
            "action_labels": core.ACTION_LABELS,
            "action_tabs": {k: list(v) for k, v in core.ACTION_TABS.items()},
            "branch_type": core.CHECK_COND,
            "nhom_lenh_nay": core.NHOM_LENH_NAY,
            "toan_hang_dung_sai": list(core.TOAN_HANG_DUNG_SAI),

            "timeframes": core.TIMEFRAMES,
            "nhip_mac_dinh": core.NHIP_MAC_DINH,
            "ma_methods": core.MA_METHODS,
            # Gửi nguyên dict từ `kho/` — thêm một trường ở đó là giao diện có ngay,
            # không phải nhớ sửa chỗ này.
            "toan_hang": core.TOAN_HANG,
            "phep_so": core.PHEP_SO,
            # ĐƠN VỊ — MỘT bảng cho cả app: điều kiện, SL/TP/đệm, sửa lệnh.
            # Trước đây là hai bảng (`CACH_TINH` + `DON_VI_SS`) trùng nhau ba cặp.
            "don_vi": core.DON_VI,
            "don_vi_ngan": core.DON_VI_NGAN,
            "don_vi_cho": {k: list(v) for k, v in core.DON_VI_CHO.items()},
            "huong": core.HUONG,
            "loai_lenh": core.LOAI_LENH,
            # MỐC NEO của khối Vào lệnh — xem `core.MOC_ENTRY`.
            "moc_entry": core.MOC_ENTRY,
            # MỌI đơn vị, một bảng nhãn — kể cả đơn vị ĐẾM (nến · lệnh · lot).
            # Bảng tham số khai `don_vi` bằng một khoá ở đây, và ô số chỉ mời những
            # tham số có ĐÚNG đơn vị của nó.
            "nhan_don_vi": core.NHAN_DON_VI,
            "don_vi_dem": core.DON_VI_DEM,
            # Toán hạng → đơn vị CỐ ĐỊNH của ô so với nó (`None` = không có vế phải).
            "toan_hang_don_vi": {
                t["key"]: core.don_vi_cua_o("dieu_kien", t["key"])
                for t in kho.TOAN_HANG},
            "toan_hang_loai": core.TOAN_HANG_LOAI,
            "loai_co_don_vi": core.LOAI_CO_DON_VI,
            # Toán hạng nào KHÔNG đo được bằng chính nó (kết quả luôn = 1).
            "don_vi_chinh_no": core.DON_VI_CHINH_NO,
            # Toán hạng nào chỉ có nghĩa khi đã có zone, và đơn vị nào cũng vậy.
            "toan_hang_can_zone": list(core.TOAN_HANG_CAN_ZONE),
            "don_vi_can_zone": list(core.DON_VI_CAN_ZONE),
            "moc_can_zone": list(core.MOC_CAN_ZONE),
            "sua_che_do": core.SUA_CHE_DO,
            "sua_can_gia": list(core.SUA_CAN_GIA),

            "don_vi_o": {k: core.don_vi_cua_o(k) for k in ("chu_ky", "rui_ro")},
            "template_kinds": core.TEMPLATE_KINDS,
            "accent_presets": core.ACCENT_PRESETS,
            "max_process_steps": core.MAX_PROCESS_STEPS,
        })

    # ------------------------------------------------------------------ mô tả
    @_bat_loi
    def describe(self, steps, tham_so=None):
        ts = {t["ten"]: t["gia_tri"] for t in (tham_so or [])}
        return _ok([_the_buoc(s, ts) for s in (steps or []) if isinstance(s, dict)])

    @_bat_loi
    def action_defaults(self, action_type):
        return _ok(_hanh_dong_mac_dinh(action_type))

    @_bat_loi
    def save_action(self, draft, tab=None, tham_so=None):
        """Chuẩn hoá + soát một hành động. Hộp thoại KHÔNG tự soát — nó gửi bản nháp
        thô sang đây, để luật hợp lệ chỉ nằm ở đúng một chỗ."""
        a = core.normalize_action(draft)
        if a is None:
            return {"ok": False, "error": "Loại hành động không hợp lệ."}
        ts = {t["ten"]: t["gia_tri"] for t in (tham_so or [])}
        loi = []
        core.validate_actions([a], lambda m, i=None: loi.append(m), tab, set(ts))
        return _ok({"action": a, "display": core.action_display(a, ts)}, loi=loi)

    # ------------------------------------------------------------------ khối
    @_bat_loi
    def new_step(self, kind="action", action_type=None, tab=None):
        st = (core.make_start_step(
                  "Chạy lại từ đây",
                  core.NHIP_MAC_DINH.get(tab, core.NHIP_MAC_DINH[core.TAB_ENTRY]))
              if kind == core.KIND_START
              else core.make_action_step(
                  _hanh_dong_mac_dinh(action_type or core.CHECK_COND)))
        return _ok({"step": st, "card": _the_buoc(st)})

    @_bat_loi
    def clone_steps(self, steps, tham_so=None):
        """Nhân bản khối: id mới + thẻ chữ.

        ⚠ `tham_so` là bảng tham số của sơ đồ ĐÍCH. Thiếu nó thì thẻ dựng ra ghi
        `nguong_nen = ?` — khối vừa dán/vừa nhập trông như hỏng, trong khi tham số
        vẫn có đủ; chỉ là chỗ dựng chữ không được đưa cho. Ctrl+V dính lỗi này từ đầu,
        chỉ là ít ai để ý vì thường dán ngay trong cùng một sơ đồ."""
        moi, tra = core.clone_steps(steps)
        ts = core.bang_tham_so({"tham_so": tham_so or []})
        return _ok({"steps": moi, "map": tra, "cards": [_the_buoc(s, ts) for s in moi]})

    # ------------------------------------------------------------------ soát
    @_bat_loi
    def validate(self, doc):
        """Nguồn của HUY HIỆU SỐ và của bảng Vấn đề — cho CẢ HAI sơ đồ, một lời gọi.

        Trả về `{value: [vấn đề…], luong: {entry: {...}, manage: {...}}}`. Mỗi vấn đề
        mang khoá `tab` để giao diện gắn nhãn và nhảy đúng chỗ.

        Soát cả hai tab chứ không chỉ tab đang mở: giấu lỗi của tab kia thì bấm ▶ Chạy
        mới lòi ra, mà lúc đó không ai hiểu vì sao."""
        probs = core.validate_process(doc)
        # Khối nào ĐỌC được toán hạng zone — tính trên CẢ tài liệu, đúng một lần, và là
        # CÙNG hàm mà `validate_process` vừa dùng. Manage không có cổng zone của riêng nó
        # nhưng vẫn đọc được: zone do Entry định nghĩa, tới lượt Manage chạy đã có sẵn.
        cho_zone = core.khoi_doc_duoc_zone(doc)
        luong = {}
        for tab in core.TABS:
            g = (doc or {}).get(tab) or {}
            st = g.get("steps") or []
            ed = g.get("edges")
            kq = core.flow_order(st, core.default_edges(st) if ed is None else ed)
            luong[tab] = {
                "order": kq["order"],
                "unreachable": kq["unreachable"],
                "quay_lai": [list(c) for c in kq["quay_lai"]],
                "vong_ho": [list(c) for c in kq["vong_ho"]],
                "lech_nhanh": kq["lech_nhanh"],
                # Khối nào đã đi QUA cổng zone — hộp thoại dùng nó để KHÔNG bày ra toán
                # hạng zone và đơn vị `× ATR zone` ở chỗ zone chưa tồn tại. Trả kèm ở
                # đây thay vì thêm một lệnh riêng: sơ đồ đổi là bảng này đổi theo, không
                # có đường nào để hai bên lệch nhau.
                "sau_cong_zone": sorted(cho_zone.get(tab) or ()),
            }
        return _ok(probs,
                   so_loi=sum(1 for p in probs if p["severity"] == "error"),
                   so_canh_bao=sum(1 for p in probs if p["severity"] == "warning"),
                   luong=luong,
                   tham_so_dang_dung=sorted(core._tham_so_dang_dung(doc)))

    # ------------------------------------------------------------------ tài liệu
    @_bat_loi
    def new_process(self):
        return _ok(_kem_the(core.new_process()))

    @_bat_loi
    def demo_process(self):
        """Sơ đồ mẫu: chiến lược Compress — nén biến động rồi phá vùng.

        Dựng bằng chính các khối người dùng có, không phải thứ đặc biệt gì — mở ra là
        thấy ngay bộ khối này diễn tả được một chiến lược thật tới đâu."""
        return _ok(_kem_the(_so_do_mau()))   # `_kem_the` tự chuẩn hoá

    @_bat_loi
    def load_process(self, name):
        return _ok(_kem_the(core.normalize_process(
            core.load_template("strategy", name))))

    @_bat_loi
    def import_steps(self, ten, tab):
        """Khối + đường nối của MỘT tab trong một chiến lược đã lưu, để THÊM CHỒNG lên
        sơ đồ đang mở. Không đụng gì tới sơ đồ hiện tại — việc ghép là của giao diện.

        Hai thứ lọc ở đây, cả hai đều là luật chứ không phải cho gọn:

        * **Bỏ khối Bắt đầu** — sơ đồ đang mở đã có một cái rồi, hai khối Bắt đầu là sơ
          đồ hỏng.
        * **Chỉ một tab** — toán hạng nhóm "Lệnh này" chỉ tồn tại ở Manage, nên bê một
          khối Manage sang Entry là tạo ra khối không soát nổi.

        Và trả kèm **những tham số đám khối đó THẬT SỰ đọc**: khối tham chiếu tham số
        bằng TÊN, nên thiếu một cái là khối trông vẫn bình thường trên canvas nhưng bấm
        ▶ mới ném `"Bảng tham số thiếu …"`. Ai nhập cũng không đoán ra vì sao."""
        d = core.normalize_process(core.load_template("strategy", ten))
        tab = tab if tab in core.TABS else core.TAB_ENTRY
        g = d.get(tab) or {}
        goc = g.get("steps") or []
        buoc = [s for s in goc if not core.is_start_step(s)]
        giu = {s["id"] for s in buoc}
        canh = [e for e in (g.get("edges") or [])
                if e.get("from") in giu and e.get("to") in giu]
        # Dùng LẠI đúng bộ quét của validator, trên một `doc` giả chỉ có đám khối này —
        # viết một bộ quét thứ hai là sớm muộn hai bên hiểu khác nhau.
        dung = core._tham_so_dang_dung({tab: {"steps": buoc}})
        return _ok({
            "steps": buoc, "edges": canh,
            "tham_so": [t for t in (d.get("tham_so") or []) if t["ten"] in dung],
            "bo_start": len(goc) != len(buoc),
            "ten": d.get("name") or ten,
        })

    @_bat_loi
    def save_process(self, doc):
        d = core.normalize_process(doc)
        p = core.save_template("strategy", d["name"], d)
        return _ok({"path": p, "name": d["name"]})

    @_bat_loi
    def list_templates(self, kind="strategy"):
        return _ok(core.list_templates(kind))

    @_bat_loi
    def delete_template(self, kind, name):
        return _ok(core.delete_template(kind, name))

    # -- file ngoài --
    #: ⚠ MỘT CHUỖI, không phải tuple `(mô tả, đuôi)`. pywebview đòi mỗi bộ lọc là một
    #: chuỗi đúng dạng `Mô tả (*.đuôi)` và tự tách lấy đuôi; đưa tuple vào thì
    #: `parse_file_type` ném `TypeError: expected string, got 'tuple'` NGAY, trước cả khi
    #: hộp thoại kịp mở — nên "Mở từ file khác…", "Duyệt file khác…" và "Lưu ra file
    #: khác…" đều bấm mà không thấy gì. Lỗi có được báo, nhưng vào bảng Nhật ký ở dưới,
    #: chỗ người dùng đang không mở.
    _LOC = "Chiến lược Cat_Studio (*.json)"

    @_bat_loi
    def open_process_file(self):
        import webview
        # `FileDialog.OPEN` chứ không phải hằng `OPEN_DIALOG` cũ — pywebview đã đánh dấu
        # bỏ nó ("will be removed in a future version"), cùng giá trị 10.
        r = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=False, file_types=(self._LOC,))
        if not r:
            return {"ok": False}          # người dùng bấm Huỷ — KHÔNG phải lỗi
        with open(r[0], encoding="utf-8") as f:
            return _ok(_kem_the(core.normalize_process(json.load(f))))

    @_bat_loi
    def save_process_file(self, doc):
        import webview
        d = core.normalize_process(doc)
        r = self._window.create_file_dialog(
            webview.FileDialog.SAVE, save_filename=f"{d['name']}.json",
            file_types=(self._LOC,))
        if not r:
            return {"ok": False}
        p = r if isinstance(r, str) else r[0]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return _ok({"path": p})

    # ------------------------------------------------------------------ chạy
    @_bat_loi
    def mo_tester(self, doc):
        """▶ Chạy — mở cửa sổ Strategy Tester.

        Chặn TRƯỚC nếu còn lỗi ở BẤT KỲ tab nào: mở tester ra để nó báo lại đúng mấy
        lỗi mà bảng Vấn đề đã hiện sẵn là bắt người dùng đi hai vòng cho một thông tin."""
        probs = core.validate_process(doc)
        loi = [p for p in probs if p["severity"] == "error"]
        if loi:
            return {"ok": False, "error": "Sơ đồ còn lỗi, chưa chạy được.", "loi": loi}
        canh_bao = [p for p in probs if p["severity"] == "warning"]
        d = core.normalize_process(doc)
        self._mo_cua_so_tester(d)
        return _ok({"da_mo": True}, canh_bao=canh_bao)

    @_bat_loi
    def mo_live(self, doc=None):
        """Mở cửa sổ LIVE. KHÔNG kiểm gì ở đây.

        ⚠ Cổng chốt (chọn chiến lược · symbol · kiểm kết nối) nằm TRONG chính cửa sổ
        Live, không phải ở cửa sổ vẽ — xem `ApiLive.live_boot`. Hàm này chỉ mở cửa, và
        đưa sang sơ đồ đang vẽ để cổng bên kia có cái mà gợi ý.
        """
        import webview
        trang = luu_tru.trang_giao_dien()
        co_trang = os.path.exists(trang)

        if self._live is not None:
            self._api_live._goi_y(doc)
            # Cửa sổ còn sống thì KÉO NÓ LÊN. Không có dòng này thì bấm ● Live hay
            # Ctrl+L lúc cửa sổ đang bị lấp sau trông y như nút hỏng.
            self._api_live._khung.keo_len_truoc()
            return _ok({"da_mo": True})

        self._api_live = ApiLive(self)
        self._api_live._goi_y(doc)
        self._live = webview.create_window(
            # ⚠ Tiêu đề mang đuôi riêng "— Live" để bản vá khung khớp được chắc chắn —
            # xem dưới. Cửa sổ không khung vẫn có tiêu đề Win32 (taskbar, Alt+Tab).
            "Cat Studio — Live",
            url=f"{trang.replace(os.sep, '/')}?live=1" if co_trang else None,
            html=None if co_trang else _TRANG_TESTER_TAM,
            js_api=self._api_live,            # ⚠ KHÔNG phải `self` — xem `NenCuaSo`
            width=1180, height=780, min_size=(900, 600),
            background_color="#202020",
            frameless=True, easy_drag=False)
        self._api_live._gan_window(self._live)

        al0 = self._api_live

        def quen_di():
            # ⚠ PHẢI DỪNG LUỒNG MÁY. Đo được: không có `_dung = True` thì `_vong()`
            # chạy mãi sau khi cửa sổ đóng — điều kiện `self._window is not None` không
            # bao giờ đổi vì không ai gán lại. Mở Live lần hai là có HAI luồng cùng kéo
            # nến và cùng giành cầu nối MT5.
            #
            # Chọn nghĩa: ĐÓNG CỬA SỔ = DỪNG PHIÊN. Chưa có luồng đặt lệnh nên không có
            # gì phải giữ chạy ngầm; ngày thêm nó thì đây là chỗ phải bàn lại, và chú
            # thích này là lời nhắc.
            al0._dung = True
            al0._window = None
            self._live = None
            self._api_live = None

        self._live.events.closed += quen_di
        # Khớp theo "— Live" chứ không theo "Live" trần: `tim_hwnd` khớp CHUỖI CON, mà
        # một chiến lược đặt tên "Live" sẽ làm tiêu đề tester ("Live — Strategy Tester")
        # khớp trước → vá nhầm cửa sổ, và cửa sổ Live thì không kéo/giãn được gì cả.
        # Cùng luật với tester, xem `_mo_cua_so_tester`.
        al = self._api_live
        threading.Thread(target=lambda: al._va_khung("— Live"),
                         daemon=True).start()
        return _ok({"da_mo": True})

    def _nhan_so_do_may(self, doc):
        """Cửa sổ RL đẩy sang một sơ đồ máy vẽ — mở nó ở cửa sổ VẼ.

        ⭐ Nó là file chiến lược BÌNH THƯỜNG (§18.6.5): cùng JSON, cùng canvas, cùng
        Tester. Nên chỗ này không có đường riêng nào — bắn đúng sự kiện mà "mở file"
        vẫn dùng, rồi kéo cửa sổ lên.

        Bắn TRƯỚC rồi mới kéo: kéo trước thì cửa sổ hiện ra trong một nhịp còn chưa có
        gì thay đổi, nhìn như bấm hụt (bài học của `test_soi_luot`)."""
        self._ban("so_do_may", core.normalize_process(doc))
        self._khung.keo_len_truoc()

    @_bat_loi
    def mo_rl(self):
        """Mở CỬA SỔ RL — bàn điều khiển máy tìm chiến lược (§18.6).

        Không kiểm gì cả: cửa sổ này không chạy sơ đồ đang vẽ, nó tự sinh ra sơ đồ.
        Cửa sổ còn sống thì KÉO LÊN, không dựng lại — một lượt tìm có thể đang chạy
        trong đó, và dựng lại là mất chỗ nhìn nó."""
        import webview
        trang = luu_tru.trang_giao_dien()
        co_trang = os.path.exists(trang)

        if self._rl is not None:
            self._api_rl._khung.keo_len_truoc()
            return _ok({"da_mo": True})

        self._api_rl = ApiRL(self)
        self._rl = webview.create_window(
            "Cat Studio — RL",
            url=f"{trang.replace(os.sep, '/')}?rl=1" if co_trang else None,
            html=None if co_trang else _TRANG_TESTER_TAM,
            js_api=self._api_rl,              # ⚠ KHÔNG phải `self` — xem `NenCuaSo`
            width=1180, height=800, min_size=(940, 620),
            background_color="#202020",
            frameless=True, easy_drag=False)
        self._api_rl._gan_window(self._rl)

        def quen_di():
            # ⚠ CHỈ quên CỬA SỔ, KHÔNG dừng lượt tìm nào. Sổ nằm ở `luot_tim` (mức
            # module) đúng để chuyện này an toàn: đóng cửa sổ RL rồi mở lại là thấy
            # lượt cũ vẫn đang chạy. Ngược hẳn với `mo_live`, nơi đóng cửa sổ = dừng
            # phiên — và §18.6.2 chốt là RL không được mắc lại món nợ đó.
            self._rl = None
            self._api_rl = None

        self._rl.events.closed += quen_di
        ar = self._api_rl
        threading.Thread(target=lambda: ar._va_khung("— RL"), daemon=True).start()
        return _ok({"da_mo": True})

    def _mo_cua_so_tester(self, doc):
        """Cửa sổ thứ hai.

        CỬA SỔ CÒN SỐNG THÌ GIỮ, chỉ nạp sơ đồ mới. Bản cũ huỷ rồi tạo lại mỗi lần bấm
        ▶ — mà vòng lặp debug thật là *sửa → chạy → so*, nên mỗi lần chạy là mất con
        trỏ nến, mất mức thu phóng, mất vị trí cuộn nhật ký, mất cả bộ lọc đang đặt."""
        self._doc_tester = doc
        if self._tester is not None:
            self._tester.set_title(f"{doc['name']} — Strategy Tester")
            # ⚠ KÉO LÊN TRƯỚC, rồi mới bắn sơ đồ. Thiếu dòng này thì bấm ▶ lần hai trông
            # y như nút hỏng: tester CÓ chạy lại thật, nhưng chạy sau lưng cửa sổ vẽ nên
            # không thấy gì nhúc nhích — người dùng phải đóng hẳn cửa sổ tester để ép nó
            # tạo lại. `mo_live` đã ghi đúng bài học này cho nút ● Live; tester bị sót.
            #
            # Trước khi bắn chứ không sau: `_ban` gọi `evaluate_js` ĐỒNG BỘ và lượt chạy
            # bắt đầu ngay trong đó, nên đưa cửa sổ lên sau là người dùng mất đúng cái
            # đáng xem nhất — thanh tiến trình chạy từ đầu.
            self._api_tester._khung.keo_len_truoc()
            # Cửa sổ còn sống: đẩy sơ đồ mới xuống, nó TỰ CHẠY LẠI. Bấm ▶ là chạy, không
            # phải mở ra một bảng cài đặt nữa rồi bấm tiếp.
            self._api_tester._ban("so_do_moi", doc)
            return

        import webview
        trang = luu_tru.trang_giao_dien()
        co_trang = os.path.exists(trang)

        # ⚠ KHÔNG được viết `file:///{trang}`. pywebview coi mọi url mở đầu `file://`
        # là KHÔNG phải local url nên không dựng http server cho cửa sổ đó, mà trang
        # build ra là ES module (`<script type="module" crossorigin>`) → origin "null"
        # → Chromium chặn → TRANG TRẮNG. Đúng bài học `app_web.py` đã ghi cho cửa sổ
        # chính. Truyền đường dẫn cục bộ TRẦN thì pywebview tự phục vụ qua http.
        self._api_tester = ApiTester(self)
        self._tester = webview.create_window(
            f"{doc['name']} — Strategy Tester",
            url=f"{trang.replace(os.sep, '/')}?tester=1" if co_trang else None,
            html=None if co_trang else _TRANG_TESTER_TAM,
            js_api=self._api_tester,          # ⚠ KHÔNG phải `self` — xem `NenCuaSo`
            width=1180, height=780, min_size=(900, 600),
            background_color="#202020",
            frameless=True, easy_drag=False)
        self._api_tester._gan_window(self._tester)

        def quen_di():
            """Người dùng đóng tester → quên tham chiếu, nếu không lần bấm ▶ sau sẽ
            `set_title` lên một cửa sổ đã chết."""
            self._tester = None
            self._api_tester = None

        self._tester.events.closed += quen_di
        # Vá khung phải đợi cửa sổ được map xong — `_va_khung` tự thử lại. Khớp theo
        # "— Strategy Tester" chứ không theo tên chiến lược: tên có thể chứa bất cứ
        # chữ gì, kể cả "Cat Studio", và khớp nhầm là vá lên cửa sổ chính.
        at = self._api_tester
        threading.Thread(target=lambda: at._va_khung("— Strategy Tester"),
                         daemon=True).start()

    # ------------------------------------------------------------------ kho
    @_bat_loi
    def kho_danh_muc(self):
        """Mọi thứ app tính được, đã chia mục — cho hộp thoại "Kho".

        Dữ liệu do `kho/` tự gom từ các module con, nên thêm một engine mới là hộp
        thoại có ngay, không phải sửa gì ở đây."""
        d = kho.danh_muc()
        d["luu_tru"] = luu_tru.tom_tat()
        d["hanh_dong"] = [{"key": k, "nhan": core.ACTION_LABELS[k],
                           "tabs": list(core.ACTION_TABS[k])}
                          for k in core.ACTION_TYPES]
        d["don_vi"] = core.DON_VI
        d["sua_che_do"] = core.SUA_CHE_DO
        d["phep_so"] = core.PHEP_SO
        d["trang_thai_lenh"] = {
            so_lenh.CHO: "Lệnh chờ đang treo",
            so_lenh.MO: "Đã khớp — đang là vị thế",
            so_lenh.DONG: "Đã đóng / đã huỷ",
        }
        d["ly_do_dong"] = so_lenh.LY_DO_DONG
        return _ok(d)

    # ------------------------------------------------------------------ cài đặt
    @_bat_loi
    def save_settings(self, s):
        cd = dict(self._cai_dat)
        if (s or {}).get("symbol"):
            cd["symbol"] = str(s["symbol"]).strip().upper()
        if (s or {}).get("accent"):
            cd["accent"] = str(s["accent"])
        self._cai_dat = core.save_settings(cd)
        return _ok(self._cai_dat)

    @_bat_loi
    def save_test_settings(self, t):
        """Điều kiện chạy Strategy Test. Danh sách trắng RIÊNG, không nhét vào
        `save_settings`: hàm kia đang giữ nghĩa "cài đặt của trình soạn thảo", trộn vào
        là hai thứ khác hẳn nhau cùng một cửa và sớm muộn giẫm chân nhau."""
        t = t or {}
        cu = dict(luu_tru.CAI_DAT_MAC_DINH["test"])
        cu.update(self._cai_dat.get("test") or {})
        for k in ("tu", "den"):
            if k in t:
                cu[k] = str(t[k]).strip()
        if t.get("symbol"):
            cu["symbol"] = str(t["symbol"]).strip().upper()
        # `lot_*` và `stops_level` là LUẬT SÀN dự phòng (§16.1) — dùng khi chưa hiệu
        # chuẩn symbol này lần nào. Có hồ sơ thì `_luat_san` lấy hồ sơ, mấy ô này ngồi im.
        for k in ("spread_diem", "truot_diem", "deposit", "commission",
                  "lot_min", "lot_buoc", "lot_max", "stops_level"):
            if k in t:
                try:
                    cu[k] = float(t[k])
                except (TypeError, ValueError):
                    pass
        for k in ("delay_ms",):
            if k in t:
                try:
                    cu[k] = int(t[k])
                except (TypeError, ValueError):
                    pass
        cd = dict(self._cai_dat)
        cd["test"] = cu
        self._cai_dat = core.save_settings(cd)
        return _ok(cu)

    # ---------------------------------------------------------- nguồn dữ liệu
    # Nằm ở Api CHÍNH vì nguồn nến là tài sản của APP, không phải của một lần chạy:
    # tải một lần rồi mọi chiến lược đều dùng chung, và xoá thì xoá hẳn.
    @_bat_loi
    def nguon_kiem_ket_noi(self, symbol):
        """Nối thử tới MT5 ngay trong Cài đặt, TRƯỚC khi bấm ▶.

        Câu "sao máy mới không tự tải được?" trước đây không có chỗ nào trả lời: người
        dùng chỉ gặp một lỗi lúc chạy, mà câu lỗi đó nói về khoảng thời gian chứ không
        nói gì về kết nối. Nút này hỏi thẳng và trả lời thẳng."""
        return _ok(nguon_nen.kiem_ket_noi(symbol))

    @_bat_loi
    def nguon_xoa(self, symbol):
        nguon_nen.xoa(symbol)
        return _ok({"ds": nguon_nen.liet_ke()})

    @_bat_loi
    def save_ui(self, state):
        """Bố cục bảng dưới.

        PHẢI đi qua Python chứ không dùng `localStorage`: pywebview phục vụ trang trên
        một cổng NGẪU NHIÊN mỗi lần chạy, mà `localStorage` gắn theo origin — nên lần
        sau mở app là origin khác và mọi thứ đã nhớ biến mất."""
        ui = dict(self._cai_dat.get("ui") or {})
        for k in ("panel_cao", "panel_gap"):
            if (state or {}).get(k) is not None:
                ui[k] = state[k]
        self._cai_dat["ui"] = ui
        core.save_settings(self._cai_dat)
        return _ok(ui)

    def dong_app(self):
        """Cửa sổ chính đóng — dọn cửa sổ tester theo. KHÔNG bọc `_bat_loi`: pywebview
        gọi nó từ sự kiện `closing`, không phải từ JS."""
        try:
            if self._tester:
                self._tester.destroy()
        except Exception:
            pass


class NenChay(NenCuaSo):
    """Phần CHUNG của cửa sổ nào có CHẠY trên dữ liệu: lo nến và điều kiện chạy.

    `ApiTester` và `ApiRL` đều cần đúng hai việc: *thiếu nến thì tải*, và *dựng
    `CaiDat` từ Cài đặt của cửa sổ chính*. Chép ra hai bản là hai bản trôi được — mà
    trôi ở đây thì tester và máy tìm chạy trên hai bộ điều kiện khác nhau, và mọi so
    sánh giữa chúng thành vô nghĩa mà không ai thấy.

    Bề mặt vẫn HẸP: lớp này không thêm một hàm nào cho JS gọi, nó chỉ gom hai phép
    dựng. Cửa sổ nào lộ ra cái gì vẫn do lớp con quyết."""

    def __init__(self):
        super().__init__()
        self._tt = {}

    def _tai_neu_thieu(self, sym, tu, den):
        """Thiếu nến cho khoảng này thì TỰ TẢI đúng phần thiếu, rồi chạy tiếp.

        Bỏ nút "Tải thêm" đi được là nhờ chỗ này. Luật cũ ghi ở `nguon_uoc_tinh` là
        *"không bao giờ tải lén"*, và nó vẫn đúng — chỉ là cách giữ luật đổi: thay vì
        bắt bấm thêm một nút, tải cứ tải nhưng **nói ra** trên chính thanh tiến trình,
        kèm số MB. Gõ nhầm `2015` thay vì `2025` thì thấy ngay `≈180 MB` mà đóng lại,
        không cần một hộp xác nhận nào.

        `khoang_thieu` vốn chỉ trả về những mẩu CÒN THIẾU nên đây là tải bổ sung, không
        phải tải lại từ đầu; đủ rồi thì không đụng tới MT5 một lần nào."""
        # ⚠ Chặn khoảng RỖNG ngay đây. `khoang_thieu` trả `[]` cho cả hai trường hợp
        # "đã đủ nến" LẪN "không đọc nổi mốc thời gian" — mà `[]` được hiểu là "khỏi
        # tải". Nên máy mới, ô From/To chưa đặt, bấm ▶ là KHÔNG tải gì rồi báo "Không
        # có nến nào cho XAUUSD", đổ tội cho mã symbol trong khi lỗi thật là chưa đặt
        # khoảng.
        if nguon_nen.thoi_diem(tu) is None or nguon_nen.thoi_diem(den) is None:
            raise RuntimeError(
                "Chưa đặt khoảng thời gian để chạy.\n\n"
                "Mở Cài đặt → Strategy Test và điền hai ô Từ / Đến "
                "(dạng 2025-01-01), rồi bấm ▶ lại.")
        thieu = nguon_nen.khoang_thieu(sym, tu, den)
        if not thieu:
            return
        ut = nguon_nen.uoc_tinh(thieu)
        self._tt.update({"da": 0, "tong": 0,
                         "chu": f"đang tải nến {sym} từ MT5 (≈{ut['mb']} MB)…"})
        try:
            nguon_nen.tai(sym, tu, den, tien_do=lambda i, n, c: self._tt.update(
                {"da": int(i), "tong": int(n),
                 "chu": f"đang tải nến {sym} từ MT5 · {c}"}))
        except nguon_nen.LoiNguon as e:
            # Trước đây lỗi này rơi vào nút "Tải thêm" nên tự nó đã rõ. Giờ nó rơi vào
            # GIỮA một lần chạy, nên phải tự nói ra là đang thiếu gì.
            a, b = thieu[0][0], thieu[-1][1]
            raise RuntimeError(
                f"Thiếu nến {sym} khoảng {nguon_nen._ngay(a)} → {nguon_nen._ngay(b)} "
                f"và không tải được.\n\n{e}") from None

        # ⚠ Tải xong mà ĐẦU khoảng vẫn thiếu = nguồn không có dữ liệu xa tới thế. Phải
        # dừng, vì hai lý do:
        #   1. chạy tiếp trên một khoảng ngắn hơn thì người dùng tưởng mình đang
        #      backtest từ 2015 trong khi thật ra từ 2016;
        #   2. khoảng đó KHÔNG BAO GIỜ lấp được, nên mỗi lần bấm ▶ lại mở MT5 tải lại
        #      một lượt vô ích — cái giá này chỉ xuất hiện từ khi bỏ nút "Tải thêm".
        # Chỉ xét đầu khoảng: thiếu ở ĐUÔI là chuyện thường (dữ liệu chỉ có tới hôm
        # nay), không có lý do gì chặn.
        con = nguon_nen.khoang_thieu(sym, tu, den)
        t0 = nguon_nen.thoi_diem(tu)
        if con and t0 is not None and con[0][0] <= t0:
            tt = nguon_nen.tom_tat(sym)
            raise RuntimeError(
                f"MT5 không có nến {sym} sớm tới {nguon_nen._ngay(t0)}.\n"
                f"Nguồn chỉ có từ {tt['tu_chu']} đến {tt['den_chu']}.\n\n"
                f'Sửa ô "Từ" ở Cài đặt → Strategy Test thành {tt["tu_chu"][:10]} '
                f"trở đi rồi chạy lại.")

    #: Khối cài đặt lớp con này chạy theo. `ApiRL` đổi thành `"rl"` — RL có khoảng
    #: TRAIN và khoảng KHOÁ, hình dạng khác hẳn `test` (§18.3).
    _KHOI_CAI_DAT = "test"

    def _nen_va_cd(self, ci):
        """`(nến, CaiDat, ci đã gộp)` — MỘT chỗ dựng điều kiện chạy, mọi cửa sổ dùng.

        ⚠ ĐỌC LẠI cài đặt từ cửa sổ chính mỗi lần, không dùng bản JS nhớ từ lúc mở cửa
        sổ: người dùng sửa Cài đặt rồi bấm ▶ lại thì phải ăn ngay. Cửa sổ phụ sống lâu
        hơn một lần chạy, nên mọi thứ nó "nhớ" đều có nguy cơ cũ."""
        k = self._KHOI_CAI_DAT
        luu = dict(luu_tru.CAI_DAT_MAC_DINH[k])
        luu.update((self._cha._cai_dat or {}).get(k) or {})
        luu.update(ci or {})
        sym = luu.get("symbol") or "XAUUSD"
        self._tai_neu_thieu(sym, luu.get("tu"), luu.get("den"))
        m = nguon_nen.doc_meta(sym) or {}
        nen = nguon_nen.doc(sym, luu.get("tu"), luu.get("den"))
        if not len(nen):
            raise RuntimeError(
                f"Không có nến nào cho {sym} trong khoảng này. Kiểm tra lại mã symbol "
                f"và khoảng From→To ở Cài đặt → Strategy Test.")
        cd = bo_chay.CaiDat(
            symbol=sym, tu=luu.get("tu"), den=luu.get("den"),
            spread_diem=_spread(sym, luu, m),
            truot_diem=luu.get("truot_diem", 0),
            deposit=luu.get("deposit", 10000.0),
            commission=luu.get("commission", 0.0),
            # 0 = tắt. Khối `test` không có khoá này nên Tester không bao giờ bị cắt —
            # người vẽ tay bao nhiêu lệnh cũng được (§18.4a).
            lenh_moi_tuan_toi_da=luu.get("lenh_moi_tuan_toi_da", 0),
            luot_moi_nen_toi_da=luu.get("luot_moi_nen_toi_da", 0),
            **_thong_so(sym, m), **_luat_san(sym, luu))
        return nen, cd, luu


class ApiTester(NenChay):
    """Bề mặt của CỬA SỔ Strategy Tester. Tách hẳn khỏi `Api` — xem `NenCuaSo`.

    Cố ý HẸP: cửa sổ tester không được lưu chiến lược, không mở hộp thoại file, không
    đổi cài đặt. Nó chỉ đọc sơ đồ đã đóng băng rồi chạy. Bề mặt hẹp là cách rẻ nhất để
    một cửa sổ phụ không lặng lẽ sửa trạng thái của cửa sổ chính."""

    _HAU_TO = "Strategy Tester"

    def __init__(self, cha):
        super().__init__()
        self._cha = cha          # `Api` của cửa sổ chính — chỉ ĐỌC
        self._kq = None          # kết quả lần chạy gần nhất (bất biến)
        self._cd = None
        self._chi_co_viec = True

    @_bat_loi
    def ping(self):
        return _ok("pong")

    @_bat_loi
    def bootstrap_tester(self):
        """Mọi thứ giao diện tester cần, lấy MỘT lần lúc mở cửa sổ."""
        return _ok({
            "phien_ban": core.PHIEN_BAN,
            "accent": (self._cha._cai_dat or {}).get("accent"),
            "doc": self._cha._doc_tester,
            # Điều kiện chạy do CỬA SỔ CHÍNH giữ (File → Cài đặt → Strategy Test).
            # Tester chỉ đọc rồi chạy — nó không có ô nhập nào.
            "cai_dat": (self._cha._cai_dat or {}).get("test") or {},
            "timeframes": core.TIMEFRAMES,
        })

    # ------------------------------------------------------------- chạy
    @_bat_loi
    def test_chay(self, ci):
        """▶ Chạy backtest TRÊN LUỒNG NỀN, trả về ngay. Giao diện hỏi `test_trang_thai`.

        Chạy nền chứ không đồng bộ vì người dùng phải THẤY tiến trình: một năm mất ~3
        giây, và ba giây im lặng thì không phân biệt được với treo. Luồng nền ở đây an
        toàn vì nó KHÔNG chia sẻ trạng thái nào — nó dựng một `KetQua` mới rồi mới gán
        vào `self._kq` bằng một phép gán duy nhất."""
        self._ma_lich_su = None      # ▶ thường = lần chạy MỚI, không phải mở lại mục cũ
        self._tt = {"dang_chay": True, "da": 0, "tong": 0, "chu": "đang nạp nến…",
                    "xong": None, "loi": None}
        threading.Thread(target=self._chay_nen, args=(ci or {},), daemon=True).start()
        return _ok(True)

    @_bat_loi
    def test_trang_thai(self):
        """Tiến trình lần chạy đang diễn ra. Giao diện hỏi ~200 ms một lần."""
        return _ok(getattr(self, "_tt", {"dang_chay": False}))

    def _chay_nen(self, ci, doc=None):
        try:
            self._tt.update(self._chay_that(ci, doc))
        except Exception as e:
            self._tt.update({"loi": f"{type(e).__name__}: {e}"})
        finally:
            self._tt["dang_chay"] = False

    def _chay_that(self, ci, doc=None):
        # ĐỌC LẠI cài đặt từ cửa sổ chính mỗi lần chạy, không dùng bản JS nhớ từ lúc mở
        # cửa sổ: người dùng sửa Cài đặt rồi bấm ▶ lại thì phải ăn ngay. Cửa sổ tester
        # sống lâu hơn một lần chạy, nên mọi thứ nó "nhớ" đều có nguy cơ cũ.
        #
        # `doc` truyền vào = đang MỞ LẠI một mục lịch sử: sơ đồ và cài đặt lấy từ mục đó
        # chứ không phải từ cửa sổ chính, nếu không thì "mở lại" chạy ra một lần chạy
        # khác hẳn và cái tên lịch sử thành nói dối.
        doc = doc or self._cha._doc_tester
        if not doc:
            raise RuntimeError("Chưa có sơ đồ nào để chạy.")
        nen, cd, ci = self._nen_va_cd(ci)      # NenChay — dùng chung với cửa sổ RL
        cu = self._tom_tat_lan_truoc()
        self._tt.update({"tong": 0, "chu": "đang biên dịch sơ đồ…"})

        def tien_do(i, tong):
            self._tt.update({"da": int(i), "tong": int(tong),
                             "chu": f"đang chạy {i:,}/{tong:,} nến".replace(",", ".")})

        kq = bo_chay.chay(doc, nen, cd, tien_do=tien_do)
        self._kq, self._cd = kq, cd          # gán MỘT lần, sau khi đã tính xong
        self._chi_co_viec = True
        # Vào lịch sử NGAY, không đợi người dùng bấm gì: lưới an toàn chỉ có tác dụng
        # khi nó tự giăng. Bản tóm tắt dùng ĐÚNG payload của `test_thong_ke` nên mở một
        # mục cũ và xem lần chạy hiện tại đi qua cùng một đường vẽ.
        try:
            lich_su.ghi(kq, cd, self._tom_tat_chay())
        except Exception:
            pass                             # hỏng lịch sử KHÔNG được làm hỏng lần chạy
        return {"xong": {
            "so_nen_m1": int(len(self._kq.nen1)),
            "so_nen_truc": int(len(self._kq.nen5)),
            "tf": self._kq.tf,
            "t_dau": int(self._kq.nen1["t"][0]), "t_cuoi": int(self._kq.nen1["t"][-1]),
            "thong_ke": self._kq.thong_ke,
            # Vân tay PHẢI lấy trên bản ĐÃ CHUẨN HOÁ ở cả hai lần: `normalize_process`
            # sắp lại khoá và dọn rác, nên hash bản thô ở lần này rồi so với bản đã
            # chuẩn hoá ở lần trước là lúc nào cũng kêu "sơ đồ ĐÃ ĐỔI".
            "so_hai_lan": nhat_ky.so_hai_lan(
                cu, {"thong_ke": self._kq.thong_ke,
                     "van_tay": nhat_ky._van_tay(self._kq.doc)}),
            "digits": cd.digits,
        }}

    def _tom_tat_lan_truoc(self):
        """Lần chạy trước — để trả lời "so với lần trước thì sao".

        Chưa chạy lần nào TRONG PHIÊN NÀY thì lấy mục mới nhất trong lịch sử: trước đây
        đóng cửa sổ tester là câu trả lời đó mất sạch, mà vòng lặp nâng cấp model thì
        chẳng ai làm gọn trong một phiên."""
        if getattr(self, "_kq", None) is not None:
            return {"thong_ke": self._kq.thong_ke,
                    "van_tay": nhat_ky._van_tay(self._kq.doc)}
        ds = lich_su.liet_ke()
        if not ds:
            return None
        return {"thong_ke": ds[0]["thong_ke"], "van_tay": ds[0]["van_tay"]}

    # ------------------------------------------------- đọc dòng thời gian
    @_bat_loi
    def test_nen_tf(self, tf, j, tran=60000, tu_t=0):
        """TOÀN BỘ nến khung `tf` từ ĐẦU dữ liệu tới con trỏ — để chart kéo đi đâu cũng đủ.

        Chart phải hành xử như một cuốn VIDEO: quá khứ luôn có sẵn, kéo qua kéo lại thoải
        mái. Bản trước mỗi lần nhảy lại dựng chart từ một cửa sổ 720 nhịp, nên kéo ra
        ngoài khoảng đó là trắng — sai hẳn bản chất.

        Trả mảng SONG SONG (`t[] o[] h[] l[] c[]`) chứ không phải danh sách object: một
        năm M5 là 71.000 nến, dạng object thì JSON phình gấp mấy lần mà chẳng thêm gì.

        Nến CUỐI cố ý để DỞ DANG (`giu_nen_do_dang`) — nó chính là cây đang hình thành
        tại con trỏ. Còn `gop` mặc định bỏ nó đi, vì lúc QUYẾT ĐỊNH thì đọc một cây nến
        chưa đóng là nhìn trước tương lai."""
        kq = self._doi_kq()
        j = max(0, min(int(j), len(kq.nen1) - 1))
        a = tinh_toan.gop(kq.nen1[:j + 1], tf if tf in core.TF_PHUT else kq.tf,
                          giu_nen_do_dang=True)
        # `tu_t > 0` = XIN ĐUÔI: chỉ những cây từ mốc đó trở đi.
        #
        # ⚠ Đây là chỗ tốn nhất của cửa sổ Live, đo được: mỗi lần nến đóng nó xin lại
        # cả 2.000 cây = **134 KB** qua cầu nối pywebview — mà cầu nối đó ĐỒNG BỘ và
        # mã hoá payload HAI LẦN. Chép 133 KB không đổi chỉ để thêm một cây. Xin đuôi
        # thì gói còn khoảng trăm byte, và chart `update()` thay vì dựng lại series.
        if int(tu_t or 0) > 0:
            a = a[a["t"] >= int(tu_t)]
        if len(a) > int(tran):
            a = a[-int(tran):]
        return _ok({"t": a["t"].tolist(), "o": a["o"].tolist(), "h": a["h"].tolist(),
                    "l": a["l"].tolist(), "c": a["c"].tolist(), "j": j,
                    "zone": self._hop_zone(kq, a, int(tu_t or 0))})

    @staticmethod
    def _hop_zone(kq, a, tu_t):
        """Zone thành HỘP để chart vẽ phông nền: `[t_đầu, t_cuối, đáy, đỉnh]`.

        Đi kèm gói nến chứ không làm một lệnh riêng: nến với zone luôn phải nói cùng một
        con trỏ, mà tách hai lệnh thì giữa hai lời gọi con trỏ đã có thể nhảy.

        Trả MỐC THỜI GIAN, không phải chỉ số nến — người dùng đổi khung hiển thị
        (M1/M5/M15) thì hộp vẫn nằm đúng chỗ, vì thời gian thì khung nào cũng như nhau.

        ⚠ CẮT Ở CON TRỎ THEO **CẢ HAI CHIỀU**.

        Ngang: `kq.so.zone` là danh sách của CẢ lần chạy, kể cả zone hình thành SAU chỗ
        đang xem — vẽ hết là lộ tương lai.

        Dọc: `v.dinh` / `v.day` là đỉnh–đáy CUỐI CÙNG của zone, tức đã gồm cả những nến
        chưa tới. Bản đầu của hàm này chỉ cắt chiều ngang nên hộp vẫn CAO BẰNG TƯƠNG LAI:
        đo được trên nến thật — con trỏ ở nến thứ 2 của zone, đáy thật là 4484,49 mà hộp
        vẽ 4476,62, tức đáy của 13 nến sau đó. Nên đỉnh–đáy phải tính lại từ chính đoạn
        nến `[b0..b1]` đã cắt, không đọc thuộc tính của zone.

        MỘT hộp mỗi zone, không phải bậc thang từng nến: rẻ hơn ~20 lần, và ở độ mờ này
        thì cái bậc không ai đọc được. Cái cần kể là "chỗ này có một đợt nén, rộng chừng
        này, cao chừng này"."""
        if not len(a):
            return []
        n5 = getattr(getattr(kq, "_ct", None), "nen5", None)
        if n5 is None or not len(n5):
            return []
        t_cuoi = int(a["t"][-1])
        ra = []
        for v in getattr(kq.so, "zone", ()) or ():
            if v.dinh is None or v.day is None or v.so_nen <= 0:
                continue
            b0 = int(v.nen_bat_dau)
            if not (0 <= b0 < len(n5)):
                continue
            t0 = int(n5["t"][b0])
            if t0 > t_cuoi:                 # chưa tới con trỏ
                continue
            b1 = min(len(n5) - 1, b0 + int(v.so_nen) - 1)
            # Cắt DỌC: chỉ lấy tới cây nến cuối cùng người xem đã thấy.
            while b1 > b0 and int(n5["t"][b1]) > t_cuoi:
                b1 -= 1
            t1 = min(int(n5["t"][b1]), t_cuoi)
            if tu_t > 0 and t1 < tu_t:      # xin ĐUÔI: bỏ zone đã nằm hẳn phía trước
                continue
            doan = n5[b0:b1 + 1]
            if not len(doan):
                continue
            ra.append([t0, t1, float(doan["l"].min()), float(doan["h"].max())])
        return ra

    @_bat_loi
    def test_doan(self, j0, n=300):
        """MỘT lô khung hình liên tiếp — cửa DUY NHẤT dùng lúc PHÁT LẠI.

        ⚠ Vì sao phải kéo theo lô: phát ở 60 ms/nhịp mà mỗi nhịp gọi cầu nối hai lần
        (nến + số liệu) là ~33 lời gọi/giây. `evaluate_js` của pywebview ĐỒNG BỘ và
        payload bị mã hoá hai lần, nên phát sẽ giật và tụt nhịp — mà "xem nến hình thành
        như thật" thì nhịp đều mới là cái quan trọng nhất.
        Một lời gọi cho 300 nhịp là 0,1 lời gọi/giây. Khác nhau 300 lần.

        Lô mang đủ MỌI thứ ba vùng cần, nên khi phát thì JS không hỏi Python một câu nào."""
        kq = self._doi_kq()
        n = max(1, min(int(n), 2000))
        # `j0 < 0` = "lấy ĐOẠN CUỐI". Live không tua nên nó không bao giờ biết chỉ số
        # cuối là bao nhiêu — mà hỏi thêm một lời gọi nữa chỉ để biết con số đó thì
        # giữa hai lời gọi sàn đã có thể đóng thêm nến, và hai bên nói lệch nhau.
        j0 = (len(kq.nen1) - n) if int(j0) < 0 else int(j0)
        j0 = max(0, min(j0, len(kq.nen1) - 1))
        j1 = min(len(kq.nen1), j0 + n)
        a = kq.nen1[j0:j1]
        i5 = kq._ct.m1_to_5[j0:j1]
        cv = kq.cot_zone

        def cot_theo_khung(mang):
            return [(float(mang[k]) if 0 <= k < len(mang)
                     and mang[k] == mang[k] else None) for k in i5]

        # BẢNG SỐ LIỆU — sinh TỪ SƠ ĐỒ, nhóm theo `nhom` mà `kho/` đã khai.
        #
        # ⚠ Trước đây khối "Vùng nén (engine)" bị VIẾT CỨNG ở đây. Hôm nay nó đúng vì
        # chiến lược mẫu là D_02; mai thêm một engine khác là bảng nói dối, và ai đó phải
        # nhớ sửa tay. Giờ bảng chỉ liệt kê đúng những toán hạng SƠ ĐỒ THẬT SỰ ĐỌC, và
        # nhóm lấy thẳng từ danh mục — thêm engine là bảng có ngay, không sửa giao diện.
        bang, nhom_dau, ct_ = [], {}, kq._ct
        for o in core.toan_hang_dung(kq.doc):
            ds = self._cot_toan_hang(kq, o, i5, a)
            if ds is None:
                continue
            # Ô khung để trống nghĩa là "khung quyết định" — mặc định đó nay nằm ở
            # `core.toan_hang_dung`, tức CÙNG tầng với khoá dedupe. Điền ở đây (tầng hiển
            # thị) là chỗ đã đẻ ra hai hàng `ATR M5·14 1.412` giống hệt nhau: khoá thì
            # khác (`tf=None` vs `'M5'`), mặt thì bị san phẳng về một.
            phan = [o["tf"]] if o.get("tf") else []
            if o.get("period"):
                p = o["period"]
                p = ct_.so(p) if isinstance(p, str) else p
                # ⚠ ĐÃ SỬA: trước là `str(p).rstrip("0").rstrip(".")` — `period` gõ tay
                # `50` cho ra `"5"`, `200` cho ra `"2"`. Trốn được vì sơ đồ mẫu ô nào cũng
                # dùng TÊN tham số nên đi qua `so()` → float → đuôi `.0` hứng trọn.
                phan.append(f"{p:g}" if isinstance(p, float) else str(p))
            if o.get("method"):
                phan.append(str(o["method"]))
            # Nhãn tách LÀM ĐÔI. Trước đây nối thành `ATR chuẩn hoá (bps)(M5, 14)` rồi
            # giao diện dán cả cục vào cột trái, nên tên dài bị cắt cụt trong khi giữa
            # nhãn và số là một khe rỗng dài. Giờ phần bổ nghĩa (khung · chu kỳ · kiểu)
            # là một cột riêng, nằm đúng vào cái khe đó.
            phu = "·".join(phan)
            # ĐƠN VỊ TẠI CHỖ ĐỌC. Quy ước giống hệt `core.ve_phai_display`: đơn vị GIÁ
            # KHÔNG in nhãn (`don_vi is None` đã nghĩa là giá). Chữ do PYTHON ghép từ
            # `core.DON_VI_NGAN` — cửa sổ Tester/Live không nhận bảng đơn vị nào, gửi khoá
            # thô sang là buộc JS đẻ ra một bảng nhãn thứ hai lệch được.
            # Vào `phu`, KHÔNG vào `nhan`: §6.4 — nhãn thuộc TOÁN HẠNG (dùng chung hộp
            # thoại / nhật ký / kho), đơn vị thuộc CHỖ DÙNG. Và vẫn đúng BA cột (§12.9c).
            if o.get("don_vi"):
                phu = (phu + " " if phu else "") + f"[{core.DON_VI_NGAN[o['don_vi']]}]"
            if o["nhom"] not in nhom_dau:
                nhom_dau[o["nhom"]] = {"nhom": o["nhom"], "dong": []}
                bang.append(nhom_dau[o["nhom"]])
            nhom_dau[o["nhom"]]["dong"].append(
                {"ten": o["nhan"], "phu": phu, "gia_tri": ds})

        # Lệnh SỐNG tại từng khung + lệnh đã đóng còn nằm trong tầm nhìn (để vẽ).
        song, tk = [], []
        for x, k in enumerate(i5):
            ds = kq.lenh_tai(int(k))
            gia = float(a["c"][x])
            # Cắt theo `k` — KHÔNG đọc thẳng `l.da_khop`/`l.sl`, đó là trạng thái cuối
            # backtest. Xem `bo_chay.lenh_tai_nen`.
            song.append([bo_chay.lenh_tai_nen(kq, l, int(k), gia) for l in ds])
            tk.append({"cho": sum(1 for l in ds if not l.da_khop),
                       "mo": sum(1 for l in ds if l.da_khop),
                       "gia": gia})

        i_cuoi = int(i5[-1]) if len(i5) else 0
        nk = nhat_ky.dung_lo_theo_nen(kq, j0, int(a["t"][-1]) if len(a) else 0)
        return _ok({
            "j0": j0, "n": int(j1 - j0),
            "t": a["t"].tolist(), "o": a["o"].tolist(), "h": a["h"].tolist(),
            "l": a["l"].tolist(), "c": a["c"].tolist(),
            "bang": bang, "lenh_song": song, "tai_khoan": tk,
            "lenh": kq.the_lenh(i_cuoi), "nhat_ky": nk,
            "zone": self._zone_trong_lo(kq, i5),
        })

    @staticmethod
    def _zone_trong_lo(kq, i5):
        """Zone LỚN DẦN qua từng nến trục của lô: `[t_zone_mở, t_nến, đáy, đỉnh]`.

        ⚠ VÌ SAO LÔ PHẢI MANG ZONE. Lúc phát lại, `nhip()` lấy khung hình TỪ LÔ và không
        hỏi Python một câu nào — đó là cả điểm của lô (phát 60 ms/nhịp mà gọi cầu nối
        mỗi nhịp thì giật). Nhưng zone thì chỉ được nạp ở đường NHẢY, nên suốt lúc phát
        nó đứng yên: bấm ▶ zone không nhúc nhích, bấm "tới sự kiện" mới thấy nó nhảy một
        phát. Đúng lỗi người dùng gặp.
        Lệnh không bị vậy vì lô mang sẵn cả sự kiện tương lai và `Chart` tự cắt theo
        `tBayGio`. Giờ zone theo đúng luật đó.

        Rẻ: lô 300 nhịp M1 = 60 nến trục, nên nhiều nhất 60 bản ghi (~2 KB). Gửi kèm còn
        rẻ hơn một lời gọi riêng.

        Mỗi bản ghi là trạng thái zone TÍNH TỚI nến đó — nên `Chart` chỉ việc lấy bản
        ghi mới nhất có `t_nến ≤ tBayGio`, và không bao giờ lộ tương lai."""
        n5 = getattr(getattr(kq, "_ct", None), "nen5", None)
        if n5 is None or not len(i5):
            return []
        lo0, lo1 = int(i5[0]), int(i5[-1])
        ra = []
        for v in getattr(kq.so, "zone", ()) or ():
            if v.dinh is None or v.so_nen <= 0:
                continue
            b0 = int(v.nen_bat_dau)
            b1 = min(len(n5) - 1, b0 + int(v.so_nen) - 1)
            if b1 < lo0 or b0 > lo1:            # zone không chạm cửa sổ lô
                continue
            t0 = int(n5["t"][b0])
            # HỢP LỆ tại TỪNG nến — đọc cột đã ghi lúc chạy, không tính lại. Nhờ vậy
            # lúc phát lại, zone đổi màu đúng cây nến nó vừa hợp lệ; và không có sơ đồ
            # nào khai "hợp lệ" thì cột vắng mặt, chart giữ nguyên màu trung tính.
            c_hl = (kq.cot_zone or {}).get("zone_hop_le")
            for b in range(max(b0, lo0), min(b1, lo1) + 1):
                doan = n5[b0:b + 1]
                hl = 0
                if c_hl is not None and 0 <= b < len(c_hl):
                    v_hl = c_hl[b]
                    hl = 1 if (v_hl == v_hl and v_hl) else 0   # NaN → chưa biết → 0
                ra.append([t0, int(n5["t"][b]),
                           float(doan["l"].min()), float(doan["h"].max()), hl])
        return ra

    def _cot_toan_hang(self, kq, o, i5, a):
        """Giá trị một toán hạng tại TỪNG khung hình của lô. `None` = chưa ghi lại được.

        Ba nguồn, theo đúng thứ tự rẻ dần: cột đã tính sẵn (chỉ báo + giá), cột engine đã
        ghi lúc chạy (vùng nén), rồi mới tới thứ suy được từ sổ lệnh/thời gian."""
        ten = o["ten"]
        ct = kq._ct

        def theo(mang, ep_bool=False):
            ra = []
            for k in i5:
                if not (0 <= k < len(mang)):
                    ra.append(None); continue
                v = mang[k]
                if ep_bool:
                    ra.append(bool(v) if v == v else None)
                else:
                    ra.append(float(v) if v == v else None)
            return ra

        cot = None
        k = ct.khoa(o) if (ten in tinh_toan.BANG or ten in ct.COT_GIA) else None
        if k is not None and k in ct._cot:
            cot = ct._cot[k]
        elif ten in kq.cot_zone:
            if ten in core.TOAN_HANG_DUNG_SAI:
                return theo(kq.cot_zone[ten], True)   # đúng/sai: không có đơn vị nào
            cot = kq.cot_zone[ten]
        if cot is not None:
            # ĐƠN VỊ TẠI CHỖ ĐỌC. Trước đây hàm này luôn trả giá trị THÔ (đơn vị giá),
            # nên cổng `atr < 7 [bps]` in ra 1.412 đứng cạnh một ngưỡng 7 bps — không ai
            # nhẩm được. Giờ mỗi hàng mang theo đơn vị điểm nó được đọc.
            dv = o.get("don_vi")
            if dv:
                q = bo_chay.quy_doi_cot(kq, o, cot, dv)
                if q is None:
                    # PHÂN BIỆT HAI LOẠI RỖNG. Không có NGUỒN → `return None` và hàng biến
                    # mất (như cũ). Có nguồn nhưng THIẾU MẪU SỐ → hàng Ở LẠI và in gạch:
                    # bỏ hàng thì người dùng mất dấu một toán hạng sơ đồ ĐANG đọc.
                    return [None] * len(i5)
                cot = q
            return theo(cot)
        if ten in ("so_lenh_cho", "so_vi_the"):
            cho = ten == "so_lenh_cho"
            return [sum(1 for l in kq.lenh_tai(int(x)) if l.da_khop != cho) for x in i5]
        if ten == "bid":
            return [float(v) for v in a["c"]]
        if ten == "ask":
            return [float(v) + self._cd.spread_gia for v in a["c"]]
        if ten == "spread":
            return [self._cd.spread_diem] * len(i5)
        if ten in ("gio", "thu"):
            return [float((int(t) // 3600) % 24) if ten == "gio"
                    else float((int(t) // 86400 + 4) % 7 + 2) for t in a["t"]]
        return None     # chưa ghi lại theo nến — thà bỏ trống còn hơn bịa một con số

    @_bat_loi
    def test_luot(self, i):
        """Một lượt cụ thể → vị trí con trỏ, để bấm dòng nhật ký là chart nhảy tới."""
        kq = self._doi_kq()
        r = kq.nhat_ky[int(i)]
        return _ok({"j": r["j"], "nen": r["nen"], "tab": r["tab"],
                    "lenh_id": r.get("lenh_id"), "cong": r.get("cong")})

    @_bat_loi
    def test_luot_ke(self, j):
        """Lượt CÓ VIỆC gần nhất sau vị trí `j`. `j = -1` nghĩa là hết.

        Không ai ngồi xem hết 71.000 nến buồn tẻ để đợi một cây nến có chuyện. Nút này
        là thứ biến "phát lại" từ một món đồ chơi thành một công cụ dùng được."""
        kq = self._doi_kq()
        j = int(j)
        for r in kq.nhat_ky:
            if r["j"] > j and r["viec"]:
                return _ok({"j": int(r["j"]), "i": int(r["nen"])})
        return _ok({"j": -1, "i": -1})

    @_bat_loi
    def test_soi_luot(self, i):
        """SOI một lượt TRÊN SƠ ĐỒ: kéo cửa sổ vẽ lên trước và tô đường lượt đó đã đi.

        Nhật ký trả lời "chuyện gì đã xảy ra" bằng chữ; câu hỏi tiếp theo luôn là "chỗ
        nào trên sơ đồ", mà dò tay một sơ đồ 20 hộp thì mất cả phút. Cái này nối thẳng
        hai đầu đó.

        Gửi nguyên `duong` và `cong` chứ không tự tóm tắt: `cong` đã ghi MỌI cổng đã
        thử kèm vết TỪNG điều kiện (`_xet_cong` cố ý tính đủ, không ngắt ở cái sai đầu
        tiên), nên giao diện tô được tới đúng dòng điều kiện hỏng. Tóm tắt ở đây là vứt
        đi đúng phần đắt nhất."""
        kq = self._doi_kq()
        i = int(i)
        if not (0 <= i < len(kq.nhat_ky)):
            return _ok({"da_ban": False})
        r = kq.nhat_ky[i]
        nhan = nhat_ky.nhan_khoi(kq.doc)
        self._cha._ban("soi_luot", {
            "tab": r["tab"],
            "duong": list(r["duong"]),
            "cong": r["cong"],
            "ket": r["ket"],
            "lenh_id": r.get("lenh_id"),
            "nhan": {k: nhan.get(k, "?") for k in
                     set(r["duong"]) | {c["khoi"] for c in r["cong"]}},
            "chu": nhat_ky.dong_chu(r, nhan, nhat_ky._khoi_theo_id(kq.doc),
                                    core.bang_tham_so(kq.doc), kq.nen5),
        })
        # Bắn TRƯỚC rồi mới kéo cửa sổ: kéo trước thì cửa sổ hiện ra trong một nhịp còn
        # chưa có gì được tô, nhìn như bấm hụt.
        self._cha._khung.keo_len_truoc()
        return _ok({"da_ban": True})

    @_bat_loi
    def test_luot_truoc(self, j):
        """Bản soi gương của `test_luot_ke`: lượt CÓ VIỆC gần nhất TRƯỚC `j`.

        Cùng MỘT định nghĩa "sự kiện" với hàm kia (`viec` khác rỗng) — khác đi thì hai
        nút thôi là nghịch đảo của nhau, bấm tới rồi bấm lui sẽ không về chỗ cũ.

        Duyệt ngược chứ không lọc rồi tìm: nhật ký một năm là ~135.000 lượt, dựng thêm
        một danh sách chỉ để lấy một phần tử là phí. `j = -1` nghĩa là phía trước không
        còn sự kiện nào — giao diện lấy đó làm hiệu lệnh về đầu."""
        kq = self._doi_kq()
        j = int(j)
        for r in reversed(kq.nhat_ky):
            if r["j"] < j and r["viec"]:
                return _ok({"j": int(r["j"]), "i": int(r["nen"])})
        return _ok({"j": -1, "i": -1})

    # Thứ tự hiện các mốc RƠI VÀO CÙNG một nến M5. Trong nến thì không có thứ tự thật —
    # đây là thứ tự KỂ CHUYỆN: đặt rồi mới khớp, khớp rồi Manage mới thấy nó đã khớp.
    _HANG_RAY = {"dat": 0, "khop": 1, "so_do": 2, "dong": 3}

    def _chi_muc_ray(self, kq):
        """Nhật ký → {lenh_id: [lượt]}. Dựng MỘT LẦN cho mỗi lần chạy.

        Quét thẳng 77.000 lượt cho từng lệnh thì rê chuột qua 300 lệnh là 23 triệu vòng.
        Dựng chỉ mục một lần rồi dùng lại: một vòng quét, xong."""
        cu = getattr(self, "_ray_cua", None)
        if cu is not None and cu[0] is kq:
            return cu[1]
        cm = {}
        for r in kq.nhat_ky:
            ids = {r["lenh_id"]} if r.get("lenh_id") else set()
            ids.update(v["lenh_id"] for v in r["viec"] if v.get("lenh_id"))
            for i in ids:
                cm.setdefault(i, []).append(r)
        self._ray_cua = (kq, cm)
        return cm

    @_bat_loi
    def test_duong_ray(self, lenh_id):
        """ĐƯỜNG RAY của một lệnh: từ lúc đặt tới lúc đóng, nó đi qua những khối nào.

        Đây là câu hỏi mà cả app sinh ra để trả lời — "vì sao lệnh này ra đời, và khối
        nào đã động vào nó". Nhật ký đã ghi đủ (`duong` = dãy khối của mỗi lượt), việc ở
        đây chỉ là GOM cho người đọc nổi.

        Hai thứ được gom:
          • các lượt LIỀN NHAU đi cùng một đường mà không làm gì → một chặng kèm `dem`.
            Manage chạy mỗi nến, một lệnh sống 3 giờ là 36 lượt y hệt nhau;
          • KHỚP và CHẠM SL/TP không có trong nhật ký — chúng là việc của thị trường,
            không phải của sơ đồ. Chèn từ chính bản ghi lệnh, và để `tab = None` để
            giao diện tách được "sơ đồ quyết" với "thị trường quyết". Đó thường là câu
            cần phân biệt nhất lúc soi một lệnh thua.

        Trả CẢ ĐỜI lệnh; cắt theo con trỏ là việc của giao diện (mỗi chặng có `t`) — nhờ
        vậy rê chuột một lệnh chỉ tốn đúng một lời gọi, không phải mỗi nhịp một lời."""
        kq = self._doi_kq()
        lid = str(lenh_id)
        l = next((x for x in kq.so.lenh if x.id == lid), None)
        if l is None:
            return _ok({"chang": []})

        nhan = nhat_ky.nhan_khoi(kq.doc)
        t5 = kq.nen5["t"]

        # XẾP THỜI GIAN TRƯỚC, GỘP SAU. Làm ngược lại thì một cục "manage ×96" nuốt cả
        # các lượt trước lẫn sau lúc khớp, đẩy "khớp" xuống dưới nó — kể sai thứ tự câu
        # chuyện. Và vì cục đó mang dấu thời gian của lượt ĐẦU, con trỏ mới tới giữa
        # chừng đã thấy đủ 96, tức lộ tương lai.
        moc = []
        for r in self._chi_muc_ray(kq).get(lid, []):
            viec = [v["loai"] for v in r["viec"] if v.get("lenh_id") == lid]
            moc.append({"tab": r["tab"], "khoi": [nhan.get(k, "?") for k in r["duong"]],
                        "viec": viec, "t": int(t5[r["nen"]]), "j": int(r["j"]),
                        "hang": self._HANG_RAY["dat" if "lenh_dat" in viec else "so_do"]})
        if l.nen_khop is not None:
            # ⚠ Xếp theo NHỊP M1 (`j`), không chỉ theo nến trục. Một nến M5 chứa 5 nhịp
            # M1 mà Manage chạy từng nhịp, nên nếu chỉ so nến trục thì mọi lượt Manage
            # rơi cùng nến với cú khớp đều bị đẩy xuống DƯỚI mốc "khớp" — kể cả những
            # lượt chạy TRƯỚC lúc khớp, lúc lệnh còn đang chờ. Đúng cái kể-sai-thứ-tự
            # mà hàm này sinh ra để chặn, chỉ là ở thang đo nhỏ hơn một bậc.
            moc.append({"tab": None, "moc": "khop", "khoi": [], "viec": [],
                        "t": int(t5[l.nen_khop]),
                        "j": getattr(l, "j_khop", None) if getattr(l, "j_khop", None) is not None else -1,
                        "hang": self._HANG_RAY["khop"]})
        # Sơ đồ TỰ TAY hạ màn thì đã có chặng `viec` kể rồi — thêm nữa là kể hai lần cùng
        # một chuyện. Nhưng KHÔNG lọc theo `ly_do_dong`: chuỗi `"huy"` dùng chung cho hai
        # đường khác hẳn nhau — khối "Huỷ chờ" (có ghi nhật ký) và lệnh chờ còn treo lúc
        # HẾT DỮ LIỆU (đóng sau vòng lặp, không có bản ghi nào). Lọc theo chuỗi là loại
        # nhầm cái thứ hai, và đường ray của nó không bao giờ có đoạn kết.
        da_ke = any(("lenh_dong" in m["viec"] or "lenh_huy" in m["viec"]) for m in moc)
        if l.nen_dong is not None and not da_ke:
            moc.append({"tab": None, "moc": l.ly_do_dong or "dong", "khoi": [], "viec": [],
                        "t": int(t5[l.nen_dong]), "j": float("inf"),
                        "hang": self._HANG_RAY["dong"]})
        moc.sort(key=lambda c: (c["t"], c["j"], c["hang"]))

        chang = []
        for m in moc:
            cu = chang[-1] if chang else None
            if (cu is not None and m["tab"] is not None and cu["tab"] == m["tab"]
                    and cu["khoi"] == m["khoi"] and not m["viec"] and not cu["viec"]):
                cu["dem"] += 1
                cu["t_het"] = m["t"]
                continue
            m.pop("hang"); m.pop("j")
            # `t` = chặng bắt đầu lúc nào, `t_het` = kết thúc lúc nào. Giao diện cần cả
            # hai: hiện chặng theo `t`, nhưng `t_het` còn ở tương lai thì con số lặp
            # chưa chốt, không được in ra như thể đã xong.
            chang.append(dict(m, dem=1, t_het=m["t"]))
        return _ok({"chang": chang})

    def _tom_tat_chay(self):
        """Tổng kết cả lượt chạy. DỰNG Ở ĐÚNG MỘT CHỖ.

        Vừa là thứ tab Thống kê vẽ, vừa là thứ lịch sử cất đi — nên mở một mục cũ và xem
        lần chạy hiện tại đi qua cùng một đường vẽ, không có hai hình dạng để lệch nhau.

        Kèm cả khoảng ĐÃ YÊU CẦU lẫn khoảng THẬT SỰ có nến: hai cái lệch nhau là chuyện
        thường (thiếu dữ liệu đầu/cuối), mà đọc số không biết nó tính trên quãng nào thì
        con số vô nghĩa."""
        kq = self._doi_kq()
        return {
            "tk": kq.thong_ke,
            "duong_von": kq.duong_von,
            "t_dau": int(kq.nen1["t"][0]), "t_cuoi": int(kq.nen1["t"][-1]),
            "yc_tu": self._cd.tu, "yc_den": self._cd.den,
            "symbol": self._cd.symbol,
            "nhip": dict(kq._ct.nhip),
        }

    @_bat_loi
    def test_thong_ke(self):
        """Tab Thống kê của lần chạy ĐANG XEM. Gọi một lần lúc mở tab."""
        return _ok(self._tom_tat_chay())

    # ------------------------------------------------------------- lịch sử
    @_bat_loi
    def test_lich_su(self):
        """Danh sách mục lịch sử, mới nhất trước. Bản GỌN — không kèm sơ đồ, không kèm
        đường vốn; hai thứ đó chiếm gần hết dung lượng mà danh sách không dùng tới."""
        return _ok({"ds": lich_su.liet_ke(),
                    "dang_xem": getattr(self, "_ma_lich_su", None)})

    @_bat_loi
    def test_lich_su_xem(self, ma):
        """Bản tóm tắt của một mục — hiện NGAY, không phải chạy lại gì.

        Kèm `chay_lai_duoc`: nến nguồn còn khớp thì mới mở lại xem phát lại được."""
        m = lich_su.doc(ma)
        if not m:
            return _loi("Không đọc được mục lịch sử này.")
        return _ok({"tom_tat": m.get("tom_tat"), "nguon": m.get("nguon"),
                    "ten": m.get("ten"), "t": m.get("t"),
                    **self._soat_nguon(m)})

    def _soat_nguon(self, m):
        """Nến nguồn còn y nguyên như lúc chạy không?

        `Mở lại` chỉ ra đúng bộ số cũ nếu dữ liệu chưa đổi. Không soát thì ba tháng nữa
        nó lặng lẽ chạy ra một kết quả khác mà vẫn mang cái tên cũ — đúng loại nói dối
        khó phát hiện nhất."""
        ng = m.get("nguon") or {}
        ci = m.get("cai_dat") or {}
        nen = nguon_nen.doc(ng.get("symbol") or ci.get("symbol") or "XAUUSD",
                            ci.get("tu"), ci.get("den"))
        if not len(nen):
            return {"chay_lai_duoc": False, "vi_sao": "không còn nến nào cho khoảng này"}
        if (int(len(nen)) != int(ng.get("so_nen") or -1)
                or int(nen["t"][0]) != int(ng.get("t_dau") or -1)
                or int(nen["t"][-1]) != int(ng.get("t_cuoi") or -1)):
            return {"chay_lai_duoc": False,
                    "vi_sao": f"dữ liệu nguồn đã đổi ({ng.get('so_nen'):,} → "
                              f"{len(nen):,} nến)".replace(",", ".")}
        return {"chay_lai_duoc": True, "vi_sao": ""}

    @_bat_loi
    def test_lich_su_chay(self, ma):
        """MỞ LẠI một mục: chạy lại đúng sơ đồ và cài đặt đã cất, trên luồng nền."""
        m = lich_su.doc(ma)
        if not m:
            return _loi("Không đọc được mục lịch sử này.")
        s = self._soat_nguon(m)
        if not s["chay_lai_duoc"]:
            return _loi(f"Không mở lại được — {s['vi_sao']}.")
        self._ma_lich_su = str(ma)
        self._tt = {"dang_chay": True, "da": 0, "tong": 0, "chu": "đang nạp nến…",
                    "xong": None, "loi": None}
        threading.Thread(target=self._chay_nen,
                         args=(m.get("cai_dat") or {}, m.get("doc")), daemon=True).start()
        return _ok(True)

    @_bat_loi
    def test_lich_su_ten(self, ma, ten):
        """Đặt tên = chuyển mục mềm thành ĐÃ LƯU (không bao giờ bị cuốn chiếu). Tên rỗng
        thì trả nó về mục mềm."""
        return _ok(lich_su.dat_ten(ma, ten))

    @_bat_loi
    def test_lich_su_xoa(self, ma):
        return _ok(lich_su.xoa(ma))

    @_bat_loi
    def test_tim_moc(self, t):
        """Nến M1 đầu tiên có thời điểm ≥ `t` — cho ô "nhảy tới mốc" trên thanh công cụ.

        Phải hỏi Python chứ không nhẩm ở JS: dữ liệu có 271 lỗ hổng (chợ đóng cửa), nên
        `(t − t_đầu) / 60` ra một chỉ số lệch hẳn. `searchsorted` thì luôn rơi đúng vào
        cây nến CÓ THẬT gần nhất về phía sau — chọn nhằm chiều thứ Bảy thì nhảy tới đúng
        lúc mở cửa, chứ không rơi vào khoảng trống."""
        kq = self._doi_kq()
        j = int(kq.nen1["t"].searchsorted(int(t), side="left"))
        j = max(0, min(j, len(kq.nen1) - 1))
        return _ok({"j": j, "t": int(kq.nen1["t"][j])})

    @_bat_loi
    def test_ghi_nhat_ky(self):
        kq = self._doi_kq()
        return _ok({"duong_dan": nhat_ky.ghi(kq, self._cd)})

    def _doi_kq(self):
        kq = getattr(self, "_kq", None)
        if kq is None:
            raise RuntimeError("Chưa chạy backtest nào — bấm ▶ Chạy trước.")
        return kq


class ApiLive(ApiTester):
    """Bề mặt của CỬA SỔ LIVE. Hẹp hơn cả `ApiTester`.

    ⚠ NGUYÊN TẮC: máy live KHÔNG sống trong cửa sổ. Phiên live là một luồng trong tiến
    trình app; cửa sổ chỉ là cái để nhìn. Nhờ vậy đóng cửa sổ không dừng live, mở lại
    thì xem tiếp — giống Discord. Ở bản này chưa có luồng đặt lệnh, nhưng cấu trúc đã
    đặt đúng chỗ để không phải bẻ lại sau.

    ĐỢT NÀY CHẠY CHẾ ĐỘ QUAN SÁT: nối, đo sức khoẻ kết nối, soi vấn đề. KHÔNG đặt lệnh.
    Lý do ở kế hoạch: chưa ai nên để một cái máy đặt lệnh thật khi chưa ngồi nhìn nó
    chạy câm vài ngày và so nhật ký với tester.
    """

    _HAU_TO = "Live"

    def __init__(self, cha):
        super().__init__(cha)
        self.doc = None
        self.symbol = ""
        self.doc_goi_y = None
        self.suc_khoe = None
        self.phien = None            # `phien_live.PhienLive` — vòi cấp nến
        self.bat_dau = time.time()
        self._dung = False
        #: Đang chạy bài hiệu chuẩn → TẠM DỪNG mọi thứ khác đụng vào cầu nối.
        #: ⚠ Đo được: `mt5` giữ MỘT kết nối cho cả tiến trình, và `_KetNoi` đóng nó khi
        #: thoát. Nhịp đo sức khoẻ 1 giây và vòi cấp nến 10 giây cắt ngang bài kiểm đang
        #: chạy dở → mọi lệnh từ vòng 2 trả `10031 mất kết nối`. Người dùng chỉ thấy
        #: "bài kiểm hỏng" mà không có cách nào biết vì sao. Đúng loại lỗi ẩn cần chặn.
        self._dang_kiem = False
        # (vòng, tổng vòng, lượt, tổng lượt) — cho nút hiện tiến độ THẬT
        self._kiem_vong = (0, 0, 0, 0)
        self._kiem_dong = []         # từng bước bài kiểm, chảy ra nhật ký NGAY

        # ⚠ HAI MẶT PHẲNG TÁCH HẲN — đây là chỗ sửa gốc của cả chuyện lag.
        #
        # Bản trước: `live_tin()` do JS gọi MỖI GIÂY, và chính nó giành ổ khoá MT5 rồi
        # bắn 5 lượt IPC sang terminal. Tức việc NHÌN xếp hàng chung với việc LÀM —
        # cùng ổ khoá mà vòi cấp nến đang dùng, và (ngày mai) cùng ổ khoá mà `order_send`
        # sẽ dùng. Lần nào rơi trúng lúc bận thì đứng, lần nào không thì mượt: đúng cảm
        # giác "lúc lag lúc không", và nó là kiến trúc chứ không phải cảm giác.
        #
        # Giờ: LUỒNG MÁY LIVE sở hữu kết nối và tự đo, cất vào đây. `live_tin()` chỉ đọc
        # bộ nhớ — không IPC, không giành khoá, không bao giờ chờ ai.
        self._tin = None             # bản đo sức khoẻ mới nhất
        self._van_de = []            # danh sách vấn đề tương ứng
        self._tin_luc = 0.0
        # `SucKhoe.do()` sửa bộ đếm rớt và hàng đo độ trễ tại chỗ — hai luồng cùng gọi
        # là hỏng số liệu. Gần như luôn chỉ luồng máy gọi; khoá này chỉ để bịt khe hẹp
        # lúc `_tin_hien()` phải tự đo nhịp đầu.
        self._khoa_do = threading.Lock()

    # ⚠ KẾ THỪA `ApiTester` là CỐ Ý, và chỉ để lấy BỀ MẶT ĐỌC: `test_doan`,
    # `test_nen_tf`, `test_luot`, `test_duong_ray`, `test_soi_luot`… Nhờ đó `Chart`,
    # `BangSoLieu`, `Journey` chạy ở cửa sổ Live mà KHÔNG sửa một dòng — hai cửa sổ đọc
    # cùng một hình dạng dữ liệu từ cùng một đoạn code, đúng như đã chốt.
    #
    # Đổi lại phải BỊT những cửa không có nghĩa ở live. Để hở thì bấm nhầm là chạy
    # backtest đè lên phiên live đang chạy.
    def test_chay(self, ci=None):
        return _loi("Cửa sổ Live không chạy backtest — dùng cửa sổ Strategy Tester.")

    def test_lich_su_chay(self, ma=None):
        return _loi("Cửa sổ Live không mở lại lần chạy cũ.")

    @_bat_loi
    def test_doan(self, j0, n=300):
        """Như tester, nhưng LỆNH LẤY TỪ SÀN chứ không từ sổ mô phỏng.

        ⚠ Đây là cốt lõi phân biệt hai cửa sổ. Tester không có sàn nên sự thật là sổ mô
        phỏng. Live thì có: chiến lược chỉ QUYẾT ĐỊNH, còn cái gì tồn tại thật thì chỉ
        MT5 biết. Vẽ theo sổ mô phỏng sai hai chiều — lệnh bài kiểm đặt (có ticket thật)
        thì không hiện, mà lệnh engine tưởng đã đặt nhưng sàn từ chối thì lại vẽ ra."""
        r = super().test_doan(j0, n)
        if r.get("ok") and r.get("value") and self.phien:
            t0 = getattr(self.phien, "t_bat_dau", None)
            if t0:
                r["value"]["lenh"] = ket_noi.lenh_san(self.symbol, int(t0))
        return r

    def _doi_kq(self):
        """Ảnh chụp SỐNG của phiên live, thay cho kết quả backtest bất biến.

        Đây là chỗ duy nhất phải đổi để cả bề mặt đọc kia dùng được cho live."""
        kq = self.phien.anh_chup() if self.phien else None
        if kq is None:
            raise RuntimeError("Phiên live chưa nạp xong nến.")
        return kq

    def _goi_y(self, doc):
        """Sơ đồ đang mở ở cửa sổ vẽ — chỉ là GỢI Ý cho cổng chốt, chưa phải cái sẽ chạy."""
        self.doc_goi_y = doc

    @_bat_loi
    def live_boot(self):
        """Cửa sổ Live vừa mở. `san_sang = False` nghĩa là CỔNG CHỐT chưa qua.

        ⚠ Cổng chốt nằm Ở ĐÂY, trong chính cửa sổ Live — không phải ở cửa sổ vẽ. Vào
        bằng Ctrl+L hay bằng nút thì cũng đáp xuống đúng một chỗ, và cửa sổ vẽ không
        phải gánh thêm một hộp thoại chẳng liên quan gì tới việc vẽ."""
        cd = (self._cha._cai_dat or {}).get("test") or {}
        return _ok({
            "phien_ban": core.PHIEN_BAN,
            "accent": (self._cha._cai_dat or {}).get("accent"),
            "san_sang": self.doc is not None,
            # Khung hình SỐ 0 của cuộn phim — giao diện ghim nó lên đầu nhật ký.
            "bat_dau_luc": (self.phien.t_bat_dau if self.phien else None),
            "ten": (self.doc or {}).get("name", ""),
            "symbol": self.symbol,
            "goi_y": (self.doc_goi_y or {}).get("name") or "",
            "ds_luu": core.list_templates("strategy"),
            "symbol_mac_dinh": self.symbol or cd.get("symbol") or "XAUUSD",
            # ⚠ SỐ LẺ CỦA SYMBOL. Cửa sổ Live viết cứng `digits=2` — đúng cho XAUUSD
            # nhưng ô Symbol ở cổng chốt là ô gõ tự do: chọn EURUSD (5 số) thì bước giá
            # 0.01 gộp 1.08501 và 1.08528 vào một mức, nến dẹp thành một vạch, và mọi
            # con số in ra `.toFixed(2)` thành "1.09". Lấy từ chính engine đang chạy.
            "digits": int(getattr(getattr(self.phien, "cd", None), "digits", 0) or 0)
                      or int((nguon_nen.doc_meta(self.symbol) or {}).get("digits") or 2),
            "cai_dat": cd,
        })

    @_bat_loi
    def live_kiem_ket_noi(self, symbol):
        """Nối thử — DÙNG CHUNG hàm với Cài đặt, không viết lại.

        Phải khai lại ở đây vì cửa sổ Live chạy `ApiLive`, không thấy `Api` chính: gọi
        `py.nguon_kiem_ket_noi` ở cửa sổ này chỉ ra "api.py không có hàm…"."""
        return _ok(nguon_nen.kiem_ket_noi(symbol))

    @_bat_loi
    def live_soat_so_do(self, ten):
        """Sơ đồ định chạy có lỗi gì không — hỏi TRƯỚC khi bấm, không phải sau.

        ⚠ Bản trước chỉ soát trong `live_chon`, tức người dùng phải bấm "Bắt đầu" mới
        biết sơ đồ hỏng. Mà cổng chốt sinh ra để nói TRƯỚC. Một chiến lược mới tinh chưa
        vẽ gì cũng phải bị chặn ở đây."""
        doc = core.load_template("strategy", str(ten)) if ten else self.doc_goi_y
        if not doc:
            return _ok({"ten": "", "loi": ["Chưa chọn chiến lược."], "canh_bao": []})
        doc = core.normalize_process(doc)
        ds = core.validate_process(doc)
        loi = [p["message"] for p in ds if p["severity"] == "error"]
        return _ok({
            "ten": doc.get("name", ""),
            "loi": loi + self._loi_live(doc),
            "canh_bao": [p["message"] for p in ds if p["severity"] != "error"],
        })

    @staticmethod
    def _loi_live(doc):
        """Những thứ CHỈ Live mới coi là lỗi.

        ⚠ `validate_process` cố ý dễ tính — nó soát một sơ đồ ĐANG VẼ DỞ, mà vẽ dở thì
        chưa vào lệnh được là chuyện thường. Đo được: một "Chiến lược 1" mới tinh, chưa
        có gì ngoài khối Bắt đầu, đi qua nó với 0 lỗi 0 cảnh báo.
        Ở cửa sổ vẽ thế là đúng. Ở Live thì đó là một cái máy sẽ nối vào sàn rồi ngồi im
        mãi mãi — và người dùng tưởng nó đang canh. Nên thêm đúng một câu hỏi:
        **sơ đồ này có thể đặt nổi một lệnh không.**"""
        so = doc.get("entry") or {}
        steps, edges = so.get("steps") or [], so.get("edges") or []
        vao = [s for s in steps if s.get("type") == core.VAO_LENH]
        if not vao:
            return ["Sơ đồ Entry không có khối \"Vào lệnh\" nào — chạy Live thì nó "
                    "không bao giờ đặt lệnh."]
        # Có khối nhưng không nối tới thì cũng như không. `flow_order` đã tính sẵn phần
        # KHÔNG BAO GIỜ CHẠY TỚI, dùng lại chứ không tự đi đồ thị lần nữa.
        try:
            xa = set(core.flow_order(steps, edges).get("unreachable") or ())
        except Exception:                       # noqa: BLE001
            xa = set()
        if all(s["id"] in xa for s in vao):
            return ["Khối \"Vào lệnh\" không nối tới được từ khối Bắt đầu — chạy Live "
                    "thì nó không bao giờ chạy tới đó."]
        return []

    @_bat_loi
    def live_chon(self, ten, symbol):
        """Qua cổng chốt: chốt chiến lược + symbol rồi mới cho cửa sổ chạy.

        `ten` rỗng = dùng sơ đồ đang mở ở cửa sổ vẽ. Sơ đồ còn lỗi thì CHẶN CỨNG —
        ở tester sai thì mất một lần chạy, ở live thì mất tiền."""
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            raise RuntimeError("Chưa chọn symbol.")
        doc = core.load_template("strategy", str(ten)) if ten else self.doc_goi_y
        if not doc:
            raise RuntimeError("Chưa chọn chiến lược.")
        doc = core.normalize_process(doc)
        # Chốt THỨ HAI, sau cái ở giao diện — đây là cửa duy nhất giữa một sơ đồ vẽ dở
        # và một kết nối tiêu tiền thật, nên soát hai lớp bằng CÙNG một bộ luật.
        loi = [p["message"] for p in core.validate_process(doc)
               if p["severity"] == "error"] + self._loi_live(doc)
        if loi:
            raise RuntimeError("Sơ đồ chưa chạy Live được:\n"
                               + "\n".join("· " + m for m in loi[:5]))
        self.doc = doc
        self.symbol = symbol
        self.suc_khoe = ket_noi.SucKhoe(symbol)
        self._window.set_title(f"{doc['name']} · {symbol} — Live")

        # Vòi cấp nến chạy trong LUỒNG RIÊNG, không trong cửa sổ. Đóng cửa sổ không
        # dừng phiên; cửa sổ chỉ là cái để nhìn.
        # Điều kiện chạy lấy ĐÚNG bộ của Strategy Tester — cùng spread, cùng phí, cùng
        # đòn bẩy. Live mà chạy trên một bộ số khác thì so nhật ký hai cửa sổ vô nghĩa.
        ci = (self._cha._cai_dat or {}).get("test") or {}
        m = nguon_nen.doc_meta(symbol) or {}
        cd = bo_chay.CaiDat(
            symbol=symbol,
            spread_diem=_spread(symbol, ci, m),
            truot_diem=ci.get("truot_diem", 0),
            deposit=ci.get("deposit", 10000.0),
            commission=ci.get("commission", 0.0),
            **_thong_so(symbol, m), **_luat_san(symbol, ci))
        self.phien = phien_live.PhienLive(doc, symbol, cd)
        threading.Thread(target=self._vong, daemon=True).start()
        return _ok({"ten": doc["name"], "symbol": symbol})

    #: Nhịp của LUỒNG MÁY. Mọi thứ chạm sàn đều nằm trên đúng luồng này.
    NHIP_DO = 1.0          # giây — đo sức khoẻ, và cũng là nhịp giá cho chart
    NHIP_NEN = 10          # cứ ngần này nhịp đo thì hỏi nến mới một lần (~10 s)

    def _vong(self):
        """LUỒNG MÁY LIVE — nơi DUY NHẤT được chạm vào sàn trong lúc chạy.

        ⚠ Trước đây có HAI chỗ chạm sàn: luồng này (10 giây một lần, kéo nến) và
        `live_tin()` do JS gọi (mỗi giây, 5 lượt IPC). Hai bên giành cùng một ổ khoá
        `_KetNoi`, nên nhịp nào của bên này rơi trúng lúc bên kia đang giữ là đứng —
        đó chính là "lúc lag lúc không". Gộp về một luồng thì KHÔNG CÒN AI ĐỂ GIÀNH.

        Và quan trọng hơn cho ngày mai: khi luồng gửi lệnh vào đây, nó nối tiếp trên
        cùng luồng này chứ không cạnh tranh với giao diện. Giao diện đọc bộ nhớ, mãi mãi.

        Nhịp nến 10 giây chứ không 60: nến đóng theo giờ SERVER, mà giờ server lệch giờ
        máy — canh đúng phút là có lúc trễ cả một nhịp. Hỏi thừa thì rẻ, trễ thì không.
        """
        # Đo NGAY một nhịp trước khi nạp: `nap()` kéo 7.200 nến, mất vài giây, mà
        # trong lúc đó đèn kết nối phải sáng chứ không được nằm ở "MẤT KẾT NỐI".
        try:
            self._do_suc_khoe()
        except Exception:                       # noqa: BLE001
            pass
        if not self.phien.nap():
            self._ban("live_nen", {"loi": self.phien.loi})
            return
        self._ban("live_nen", {"moi": len(self.phien.nen1), "nap_xong": True})
        dem = 0
        while not self._dung and self._window is not None:
            time.sleep(self.NHIP_DO)
            if self._dang_kiem:
                # Bài kiểm đang giữ cầu nối — không đo, không kéo nến. Nhưng KHÔNG
                # xoá `_tin`: giao diện giữ số liệu cuối còn hơn nhấp nháy về rỗng.
                continue
            try:
                self._do_suc_khoe()
            except Exception:                   # noqa: BLE001
                pass
            dem += 1
            if dem < self.NHIP_NEN:
                continue
            dem = 0
            try:
                n = self.phien.nhip()
                if n:
                    self._ban("live_nen", {"moi": n, "nap_xong": True})
            except Exception:                   # noqa: BLE001
                pass

    def _do_suc_khoe(self):
        """Một nhịp đo, CẤT VÀO BỘ NHỚ. Gần như chỉ luồng máy gọi."""
        if self.suc_khoe is None:
            return None
        with self._khoa_do:
            tin = self.suc_khoe.do()
            self._tin = tin
            self._van_de = self.suc_khoe.van_de(tin)
            self._tin_luc = time.time()
        return tin

    def _tin_hien(self):
        """Bản đo mới nhất. Chưa có thì đo MỘT lần rồi cất — chỉ lần đầu mới chờ.

        Cần vì `live_de_phong` chạy ngay lúc mở cửa sổ, trước khi luồng
        máy kịp đo nhịp đầu. Không có nhánh này thì tên sàn rỗng → tra hồ sơ trượt →
        khối Đề phòng báo "chưa hiệu chuẩn" trong khi hồ sơ nằm sẵn đó."""
        if self._tin is None and self.suc_khoe is not None and not self._dang_kiem:
            try:
                self._do_suc_khoe()
            except Exception:                   # noqa: BLE001
                pass
        return self._tin or {}

    @_bat_loi
    def live_tin(self, da_co=0):
        """Bản đo mới nhất + vấn đề. **ĐỌC BỘ NHỚ, không chạm sàn.**

        ⚠ Đây là hàm mà giao diện gọi thường xuyên nhất, nên nó phải là hàm RẺ NHẤT.
        Bản trước nó tự đi đo — mỗi lời gọi là 5 lượt IPC sang terminal MT5 dưới ổ khoá
        chung. Giờ luồng máy đo sẵn, hàm này chỉ trả cái đã có.

        `da_co` = số bước bài kiểm giao diện ĐÃ nhận. Chỉ gửi phần MỚI: bài hiệu chuẩn
        sinh vài chục bước, gửi lại cả danh sách mỗi giây là chép một thứ không đổi qua
        cầu nối hàng trăm lần.

        Gộp mọi thứ vào MỘT lời gọi: tách ra thì bảng vấn đề và dải kết nối đọc hai lần
        đo khác nhau, và sẽ có lúc dải báo xanh còn bảng báo mất kết nối."""
        n = len(self._kiem_dong)
        # ⚠ TUỔI của bản đo, và nó phải chảy ra ngoài.
        #
        # Đọc bộ nhớ thì rẻ, nhưng đổi lại số liệu có thể CŨ mà vẫn trông như đang
        # sống: lúc hiệu chuẩn ta cố ý ngừng đo, và nếu luồng máy chết thì nó đứng
        # hẳn. Hiện `tuổi tick 1.4 s` đông cứng suốt ba phút là đúng loại nói dối im
        # lặng mà cả app này sinh ra để chống — nên gửi kèm tuổi, để giao diện nói
        # thẳng "đang tạm dừng" thay vì giả vờ tươi.
        cu = round(time.time() - self._tin_luc, 1) if self._tin_luc else None
        return _ok({
            "tin": self._tin,
            "van_de": list(self._van_de),
            "dang_kiem": self._dang_kiem,
            "tin_cu_giay": cu,
            # Ngưỡng 3 nhịp: trễ một nhịp là bình thường, ba nhịp là có chuyện.
            "tam_dung": bool(self._dang_kiem
                             or (cu is not None and cu > self.NHIP_DO * 3)),
            "kiem_vong": list(self._kiem_vong),
            "kiem_tong": n,
            "kiem_dong": self._kiem_dong[max(0, int(da_co or 0)):],
        })

    @_bat_loi
    def live_de_phong(self):
        """Khối ĐỀ PHÒNG — hệ thống đang tự bảo vệ bằng những gì, và mỗi con số từ đâu ra.

        Trình bày như khối Tài khoản: nhãn · giá trị · ghi chú. Nó BÁO CÁO, không phải
        để chỉnh — chỉnh là việc của bài hiệu chuẩn, tự ghi vào hồ sơ.

        Ghi chú nói NGUỒN mới là chỗ có giá trị, và nó có BA mức chứ không hai:
          *đã chỉnh*  — bài kiểm gặp lỗi rồi tự sửa con số này. Bằng chứng mạnh nhất.
          *đã kiểm*   — chạy qua bài kiểm mà không hỏng lần nào → giả thuyết ĐÚNG SẴN.
                        Đây là chỗ dễ hiểu nhầm nhất: không đổi gì KHÔNG phải là chưa
                        thử, mà là thử rồi và không cần đổi.
          *đang đoán* — chưa hiệu chuẩn lần nào. Con số bịa.
        """
        tin = self._tin_hien()
        hs = ket_noi.doc_ho_so(tin.get("sàn") or "", self.symbol) or {}
        L = dict(gui_lenh.LUAT_MAC_DINH, **(hs.get("luat") or {}))
        do = bool(hs.get("do_luc"))
        # Khoá nào bài kiểm đã ĐỘNG VÀO — đọc từ chính lịch sử chỉnh, mỗi dòng dạng
        # "kep_stops: 0 → 258 — vì sao". Không đoán lại, không lưu trùng.
        da_chinh = {c.split(":", 1)[0].strip(): c.split("—", 1)[-1].strip()
                    for c in (hs.get("da_chinh") or []) if ":" in c}

        def chu(khoa, mac_dinh):
            if not do:
                return "đang đoán — chưa hiệu chuẩn"
            if khoa in da_chinh:
                return f"đã chỉnh · {da_chinh[khoa]}"
            return f"đã kiểm {hs.get('do_luc')} — chạy qua bài kiểm không hỏng lần nào" \
                if not mac_dinh else f"đã kiểm — {mac_dinh}"

        la = dict.fromkeys(list(gui_lenh.CHUA_BIET) + list(hs.get("ma_la") or []))
        tt = hs.get("trang_thai")
        return _ok({
            "da_hieu_chuan": do,
            "trang_thai": tt,
            # Đo ở tài khoản nào, đang chạy ở tài khoản nào — hai câu khác nhau, và chỗ
            # lệch giữa chúng là toàn bộ rủi ro của luồng "đo demo, chạy thật".
            "la_that": tin.get("la_that"),
            "chep_tu": hs.get("chep_tu"),
            "do_o_server": hs.get("server", ""),
            # Chưa có hồ sơ cho sàn này, nhưng CÙNG SYMBOL đã đo ở sàn khác → mời chép.
            "ho_so_khac": ([] if do else
                           ket_noi.ho_so_khac(tin.get("sàn") or "", self.symbol)),
            "dong": [
                {"ten": "SL/TP tối thiểu", "loai": gui_lenh.LOAI["kep_stops"],
                 "gia": f"{L['kep_stops']} điểm" if L.get("kep_stops") else "theo sàn khai",
                 "chu": (f"đo được ngưỡng thật {hs.get('stops_level_that')} điểm — "
                         f"sàn khai {hs.get('stops_level', '?')}")
                        if hs.get("stops_level_that")
                        else chu("kep_stops", "sàn khai thường SAI")},
                {"ten": "Trượt cho phép", "loai": gui_lenh.LOAI["deviation"],
                 "gia": f"{L['deviation']} điểm",
                 "chu": chu("deviation", "")},
                {"ten": "Kiểu khớp", "loai": gui_lenh.LOAI["filling"],
                 "gia": "theo sàn khai" if L["filling"] is None
                        else ("FOK", "IOC", "RETURN")[int(L["filling"]) % 3],
                 "chu": chu("filling", "tự đổi nếu sàn không nhận")},
                {"ten": "Thử lại", "loai": gui_lenh.LOAI["thu_lai"],
                 "gia": f"{L['thu_lai']} lần · giãn {L['cho_ms']} ms",
                 "chu": chu("thu_lai", "chỉ với lỗi ĐÁNG thử")},
                {"ten": "Mất kết nối", "loai": gui_lenh.LOAI["cho_noi_giay"],
                 "gia": f"chờ nối lại tối đa {L['cho_noi_giay']} s",
                 "chu": chu("cho_noi_giay", "chờ NỐI LẠI rồi gửi, không ngủ rồi gửi mù")},
                {"ten": "Vị thế đóng băng", "loai": gui_lenh.LOAI["cho_bang_ms"],
                 "gia": f"chờ {L['cho_bang_ms']} ms",
                 "chu": chu("cho_bang_ms", "mã 10029 — băng tự tan, chờ là qua")},
                {"ten": "Lỗi đã có luật", "loai": "ta",
                 "gia": f"{len(gui_lenh.XU_LY)} mã",
                 "chu": "mã nào thử lại, mã nào dừng hẳn, mã nào vốn đã đạt"},
                {"ten": "Cần người ra tay", "loai": "ta",
                 "gia": f"{len(gui_lenh.CAN_NGUOI)} mã",
                 "chu": "hết tiền · chợ đóng · AlgoTrading tắt — chỉnh số vô ích"},
                {"ten": "Lỗi CHƯA có luật", "loai": "ta",
                 "gia": ", ".join(str(k) for k in la) if la else "0",
                 "chu": ("đã gặp mà chưa biết cách xử — đang thử lại tạm"
                         if la else "chưa gặp mã lạ nào")},
            ]})

    @_bat_loi
    def live_chep_ho_so(self, tu_khoa):
        """Dùng hồ sơ đã đo ở sàn khác cho sàn đang chạy.

        ⚠ Đây là cây cầu DEMO → THẬT, và là chỗ duy nhất người dùng phải tự quyết. Máy
        không tự chép được: nó không biết `Exness Technologies Ltd` với `Exness (SC)
        Ltd` là một sàn hay hai. Nhưng nó BIẾT mình đang không có hồ sơ, và im lặng rơi
        về số mặc định đang đoán là đúng kiểu chết ngầm cả tầng này sinh ra để chặn.

        Bản chép để lại vết `chep_tu` — và mấy dòng loại `khop` (trượt giá) vẫn phải
        đọc là CHẶN DƯỚI, vì chúng đo ở một tài khoản khác."""
        tin = self._tin_hien()
        san = tin.get("sàn") or ""
        if not san:
            return _loi("Chưa đọc được tên sàn — kiểm tra kết nối trước.")
        d = ket_noi.chep_ho_so(str(tu_khoa), san, self.symbol)
        if d is None:
            return _loi(f"Không thấy hồ sơ «{tu_khoa}».")
        return _ok({"san": san, "tu": str(tu_khoa), "do_luc": d.get("do_luc")})

    @_bat_loi
    def live_ve_so_do(self):
        """Kéo cửa sổ VẼ lên trước. Cùng lối với "Xem trên sơ đồ" ở nhật ký tester.

        Live chạy ngầm hàng giờ nên cửa sổ vẽ hay bị lấp sau — mà không có đường quay
        về thì người dùng phải đi tìm trên taskbar."""
        self._cha._khung.keo_len_truoc()
        return _ok({"da_keo": True})

    @_bat_loi
    def live_don_rac(self):
        return _ok(ket_noi.don_rac(self.symbol))

    @_bat_loi
    def live_test_ket_noi(self, so_vong=3, nghi_giay=15, lap_toi_da=4):
        """HIỆU CHUẨN: vòng lặp TỰ CHỈNH bằng lệnh thật trên demo.

        Không phải "chạy một bài rồi báo lỗi". Chạy → chỗ nào phòng vệ bó tay thì suy
        ra giá trị đúng từ chính lỗi đó → ghi vào hồ sơ → chạy lại, tới khi hết chỗ
        phải chỉnh. Kết thúc ở một trong ba trạng thái, không có "N/M bước đạt".

        ⚠ Giành cầu nối trong suốt thời gian chạy. Không có chốt này thì nhịp đo sức
        khoẻ và vòi cấp nến cắt ngang, và bài kiểm hỏng từ vòng 2 — đã đo được."""
        if self._dang_kiem:
            return _loi("Bài kiểm đang chạy rồi.")
        self._dang_kiem = True
        # (vòng, tổng vòng, lượt, tổng lượt) — PHẢI có cả lượt. Chỉ đẩy vòng thì nó
        # reset về 1/3 sau mỗi lượt và cả bài kiểm trông như chạy vô tận.
        self._kiem_vong = (0, int(so_vong), 0, int(lap_toi_da))
        self._kiem_dong = []
        try:
            # Tiến độ chảy ra ngoài qua `live_tin` — bài kiểm chạy vài phút, bấm xong
            # không thấy gì thì không phân biệt được với treo.
            return _ok(ket_noi.hieu_chuan(
                self.symbol, so_vong=int(so_vong), nghi_giay=float(nghi_giay),
                lap_toi_da=int(lap_toi_da),
                tien_do=lambda k, n, l, lm: setattr(
                    self, "_kiem_vong", (k + 1, n, l + 1, lm)),
                ghi_ra=self._kiem_dong.append))
        finally:
            self._dang_kiem = False
            self._kiem_vong = (0, 0, 0, 0)


_TRANG_TESTER_TAM = """
<!doctype html><meta charset="utf-8">
<body style="margin:0;background:#202020;color:#e8e8e8;
             font:14px 'Segoe UI',system-ui,sans-serif;display:grid;
             place-items:center;height:100vh">
  <div style="text-align:center">
    <div style="font-size:15px;color:#ffa657;margin-bottom:6px">Strategy Tester</div>
    <div style="color:#9a9a9a">Chưa build giao diện — chạy <code>npm run build</code>
      trong <code>webui/</code>.</div>
  </div>
</body>
"""


# ---------------------------------------------------------------------------
# Sơ đồ mẫu — chiến lược Compress (D_02)
# ---------------------------------------------------------------------------
#
# Chép lại từ EA thật:
#   MQL5\Experts\D_02_Compress\Projects\Experts\Compress.mq5
#                             \Include\Controller\{FilterEngine,TradeManager}.mqh
#
# HAI SƠ ĐỒ, và ranh giới giữa chúng là điều quan trọng nhất:
#
#   ENTRY   chạy MỘT lượt mỗi nến, đi săn tín hiệu. Chỉ nó được TẠO lệnh.
#   MANAGE  chạy MỘT LƯỢT CHO MỖI LỆNH đang sống, cũng mỗi nến. Chỉ nó được SỬA lệnh.
#
# Thứ tự trong một nến: MANAGE trước, ENTRY sau — đúng `OnTick`:
#     CheckPendingActivation → ManageBreakEven → rồi mới tới phần quyết định.
# Chạy ngược lại thì lệnh vừa sinh bị quản lý ngay trong chính nến đẻ ra nó.
#
# BA THỨ D_02 PHẢI GIẤU TRONG C++, Ở ĐÂY HIỆN RA THÀNH CỔNG:
#
#   `if(m_has_pending) return false`      → điều kiện "số lệnh chờ = 0"
#   `if(pos_count >= max_positions) skip` → điều kiện "số vị thế < 3"
#   `if(sl >= entry) continue`            → điều kiện "SL chưa ở hoà vốn"
#
# VÀ `COMP_CONSUMED` KHÔNG CẦN CỜ ẨN: lệnh mang `vùng_id`, nên "vùng này đã sinh lệnh"
# chỉ là một phép tra bảng — có lệnh nào trỏ về vùng hiện hành không.

#: SƠ ĐỒ MẪU nằm ở `cat_studio/mau/compress.json` — MỘT FILE JSON, y như mọi chiến lược
#: khác. Trước đây nó là ~220 dòng Python dựng khối ngay trong `api.py`, tức một chiến
#: lược cụ thể nằm trong tầng mà §2 định nghĩa là *"bề mặt DUY NHẤT giao diện gọi tới"*.
#: Bảng 11 con số của nó cũng đi theo, vào đúng ô `tham_so` của file đó — chỗ mọi chiến
#: lược khác vẫn để số của mình. Xem core.md §15.4.
#:
#: ⚠ ID CỐ ĐỊNH, chép nguyên trong file (`mau01`, `mau02`, …). Sơ đồ mẫu là một HẰNG SỐ
#: nên nó phải ra y hệt nhau mỗi lần mở: `_van_tay` băm cả id, nên id sinh ngẫu nhiên
#: biến "mở sơ đồ mẫu hai lần" thành hai chiến lược khác nhau — lịch sử đẻ hai dòng
#: trùng hệt, và "so với lần trước" lúc nào cũng nói "sơ đồ ĐÃ ĐỔI". Id chỉ cần duy
#: nhất TRONG MỘT tài liệu, nên đặt cứng hoàn toàn an toàn; nhập sơ đồ này vào một sơ đồ
#: khác thì `clone_steps` vẫn cấp id mới như thường.
#: ⚠ Đi qua `luu_tru.thu_muc_goi()`, KHÔNG dùng `dirname(__file__)`. Đó là hàm dựng ra
#: đúng cho câu hỏi "tài nguyên đi kèm nằm đâu": bản đóng gói giải nén vào `sys._MEIPASS`
#: và `__file__` của một module trong gói không còn là đường dẫn có thật trên đĩa. Cùng
#: một cửa mà `webui/dist` đang đi.
_DUONG_MAU = os.path.join(luu_tru.thu_muc_goi(), "cat_studio", "mau", "compress.json")


def _so_do_mau():
    """Compress: biến động co lại như lò xo → đặt lệnh chờ ngay mép vùng → phá ra là khớp.

    Mọi khoảng cách là bội của ATR hoặc của R, không một pip hay đô nào — nên cùng một
    bộ số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.

    ⚠ NẠP LẠI TỪ FILE MỖI LẦN GỌI, không cache. Người gọi sửa tại chỗ là chuyện thường
    (`_kem_the`, `normalize_process`, rồi người dùng kéo khối) — mà một hằng số dùng
    chung bị sửa tại chỗ là loại lỗi im lặng tệ nhất: sơ đồ mẫu lần thứ hai đã khác lần
    thứ nhất, và không có gì báo. File 7 KB, đọc lại rẻ hơn nhiều so với một buổi đi tìm.
    """
    with open(_DUONG_MAU, encoding="utf-8") as f:
        return json.load(f)



#: Mấy nhóm THẺ tắt được, kèm nhãn tiếng Việt và thứ tự bày ra — core.md §18.6.1.
#:
#: ⚠ Chỉ mang NHÃN và THỨ TỰ. Danh sách giá trị lấy từ `nguoi_bay.THE_CHON`, thứ tự
#: quét thẳng từ kho nước đi — nên thêm một toán hạng, một nấc thang, một chế độ sửa là
#: panel có ngay, không phải sửa ở đây. Nhóm nào không khai dưới đây thì KHÔNG bày ra,
#: và đó là cách duy nhất một nhóm bị bỏ sót — nên bài kiểm canh đúng chuyện ấy.
_NHOM_CHON = [
    ("kho", "th", "Toán hạng", None),
    ("kho", "tf", "Khung giờ", None),
    ("kho", "moc", "Mốc neo vào lệnh", None),
    ("kho", "huong", "Hướng lệnh", None),
    ("kho", "loai", "Loại lệnh", None),
    ("kho", "sua", "Chế độ Sửa lệnh", None),
    ("thang", "nguong", "Ngưỡng cổng", "× đơn vị toán hạng"),
    ("thang", "sl", "Stop Loss", "× ATR / ATR zone"),
    ("thang", "tp", "Take Profit", "× R"),
    ("thang", "rui_ro", "Rủi ro mỗi lệnh", "% vốn"),
    ("thang", "dem_vao", "Đệm quanh mốc neo", "× ATR"),
    ("thang", "dem_nen", "Đếm nến", "nến"),
    ("thang", "dem_lenh", "Đếm lệnh", "lệnh"),
    ("thang", "pt_von", "Sụt vốn", "%"),
    ("thang", "boi_R", "Lãi đang có", "× R"),
    ("thang", "chu_ky", "Chu kỳ chỉ báo", "nến"),
]

#: Nhãn cho mấy giá trị KHÔNG phải số. Số thì tự nó là nhãn.
_NHAN_THE = {
    **{t["key"]: t["nhan"] for t in kho.TOAN_HANG},
    **core.MOC_ENTRY, **core.HUONG, **core.LOAI_LENH, **core.SUA_CHE_DO,
}


def _chon_rl():
    """Mọi thứ tầng CHỌN bật/tắt được, đã gom nhóm và gắn nhãn.

    Giao diện chỉ cầm CHUỖI THẺ (`th:atr`, `sl:1.5`) rồi gửi ngược lại — nó không cần
    biết một thẻ nghĩa là gì, nên thêm chiều mới là việc của Python một mình."""
    def _sap(v):
        try:
            return (0, float(v), "")
        except ValueError:
            return (1, 0.0, v)

    ra = []
    for cho, nhom, nhan, don_vi in _NHOM_CHON:
        gia = nguoi_bay.THE_CHON.get(nhom)
        if not gia:
            continue
        ra.append({
            "cho": cho, "nhom": nhom, "nhan": nhan, "don_vi": don_vi,
            "muc": [{"the": f"{nhom}:{g}",
                     "nhan": _NHAN_THE.get(g, g),
                     # Toán hạng zone chỉ có nghĩa SAU cổng zone (§12.6c) — đánh dấu
                     # để người dùng hiểu vì sao tắt nó lại kéo theo mấy cái khác.
                     "z": nhom == "th" and g in kho.CAN_ZONE,
                     "manage": nhom == "th"
                               and list(_TH_TAB.get(g) or ()) == [core.TAB_MANAGE]}
                    for g in sorted(gia, key=_sap)],
        })
    return ra


_TH_TAB = {t["key"]: t.get("tabs") for t in kho.TOAN_HANG}


class _BaoQuaLuot(dict):
    """`self._tt` của `NenChay` nhưng đổ thẳng vào bảng trạng thái của một `LuotTim`.

    `NenChay._tai_neu_thieu` báo tiến trình tải nến bằng `self._tt.update(...)`. Cửa sổ
    RL thì chỉ hỏi `rl_trang_thai(ma)` — nó không biết `self._tt` tồn tại. Không bắc
    cầu ở đây thì suốt lúc tải nến (có thể hàng phút) thanh tiến trình đứng im và người
    dùng tưởng treo. Kế thừa `dict` để `NenChay` không phải biết gì về chuyện này."""

    def __init__(self, luot):
        super().__init__()
        self._luot = luot

    def update(self, *a, **k):          # noqa: D102 — xem docstring lớp
        super().update(*a, **k)
        self._luot._ghi(da_chay=self.get("da", 0), tong=self.get("tong", 0),
                        chu=self.get("chu", ""))


def _nhan_cau_hinh(dat, ci):
    """Một DÒNG mô tả lượt này chạy với gì — để sổ lượt phân biệt được.

    Cố ý ngắn và cố ý chỉ nói thứ NGƯỜI DÙNG ĐÃ ĐỔI so với mặc định. Liệt kê hết thì
    hai mươi dòng giống nhau y như lúc không có dòng nào."""
    cua = dat.get("cua") or {}
    ky = cua.get("ky") or "tuan"
    p = [f"{ci.get('symbol') or '—'}",
         f"{ci.get('tu') or '?'}→{ci.get('den') or '?'}",
         "tháng" if ky == "thang" else "tuần"]
    # ⚠ KHÔNG `or 1`: `manh_deu = 0` là một lựa chọn THẬT ("chỉ nhìn lãi") mà `0 or 1`
    # nuốt mất, và nhãn im lặng nói dối đúng cái nó sinh ra để nói.
    md = cua.get("manh_deu")
    if (1 if md is None else int(md)) <= 0:
        p.append("chỉ lãi")
    n = sum(1 for k, v in cua.items()
            if v is not None and k not in ("ky", "tuan_co_lenh", "manh_deu"))
    if n:
        p.append(f"{n} phạt")
    if dat.get("tat"):
        p.append(f"tắt {len(dat['tat'])} thẻ")
    p.append(f"{int(dat.get('so_luot') or 0):,} sơ đồ".replace(",", "."))
    p.append(f"hạt {int(dat.get('hat') or 0)}")
    return " · ".join(p)


class ApiRL(NenChay):
    """Bề mặt của CỬA SỔ RL — bàn điều khiển máy tìm chiến lược.

        core.md §18.6

    Cố ý HẸP như `ApiTester`: cửa sổ này không lưu chiến lược, không mở hộp thoại file,
    không đổi cài đặt. Nó **đặt · chạy · nhìn · mở** (§18.6.2), hết.

    ⚠ Và nó KHÔNG giữ lượt chạy nào. Sổ nằm ở `luot_tim` — mức module, sống theo tiến
    trình. Đóng cửa sổ RL không dừng lượt tìm; mở lại là thấy nó vẫn đang chạy. Đó là
    món nợ §14.4 (*"đóng cửa sổ Live là dừng phiên"*) cố ý không mắc lại.
    """

    _HAU_TO = "RL"
    #: ⭐ RL có CÀI ĐẶT RIÊNG. Strategy Test có đúng MỘT khoảng; RL cần ít nhất HAI —
    #: đoạn máy đào và đoạn KHOÁ (§18.3). Mượn khối `test` là sai từ gốc: hình dạng ấy
    #: không diễn tả nổi thứ RL cần.
    _KHOI_CAI_DAT = "rl"

    def __init__(self, cha):
        super().__init__()
        self._cha = cha          # `Api` của cửa sổ chính — chỉ ĐỌC

    def _dat(self):
        """Cài đặt RL hiện tại, đã trộn mặc định."""
        d = dict(luu_tru.CAI_DAT_MAC_DINH["rl"])
        d.update((self._cha._cai_dat or {}).get("rl") or {})
        return d

    @_bat_loi
    def rl_luu_dat(self, d):
        """Ghi cài đặt RIÊNG của RL. Danh sách trắng — không cho JS nhét khoá lạ vào."""
        cu = self._dat()
        moi = {k: (d or {}).get(k, cu[k]) for k in luu_tru.CAI_DAT_MAC_DINH["rl"]}
        # ⚠ `khoa_da_mo` KHÔNG cho giao diện ghi. Nó là cái đồng hồ đếm số lần đoạn
        # khoá bị nhìn; cho JS đặt lại là cho phép xoá dấu vết, mà cả điểm của nó là
        # KHÔNG xoá được.
        moi["khoa_da_mo"] = cu["khoa_da_mo"]
        self._cha._cai_dat = {**(self._cha._cai_dat or {}), "rl": moi}
        core.save_settings(self._cha._cai_dat)
        return _ok(moi)

    # ------------------------------------------------------------------ ĐẶT
    @_bat_loi
    def rl_boot(self):
        """Mọi thứ bàn điều khiển cần, lấy MỘT lần lúc mở cửa sổ.

        ⭐ Mọi danh sách ở đây lấy TỪ NGUỒN, không gõ tay: thêm một toán hạng vào kho
        là panel có ngay, thêm một nấc thang là ô chọn dài thêm."""
        ci = self._dat()
        return _ok({
            "phien_ban": core.PHIEN_BAN,
            "accent": (self._cha._cai_dat or {}).get("accent"),
            # --- tầng CHỌN (§18.6.1) ---
            "chon": _chon_rl(),
            "tran": dict(nguoi_bay.TRAN),
            "cua": dict(cham_diem.CUA_MAC_DINH),
            "tuan_co_lenh_toi_thieu": cham_diem.TUAN_CO_LENH_TOI_THIEU,
            "so_nuoc_di": len(nguoi_bay.KHO_NUOC_DI),
            # --- điều kiện chạy ---
            # Mặc định lấy từ Cài đặt của cửa sổ vẽ, nhưng SỬA ĐƯỢC ngay tại đây: bàn
            # điều khiển mà phải sang cửa sổ khác mới đổi được khoảng thời gian thì nó
            # không phải bàn điều khiển. `_nen_va_cd` vốn đã nhận đè, chỉ thiếu ô nhập.
            "cai_dat": ci,
            "kho_nen": self._kho_nen(ci.get("symbol") or "XAUUSD"),
            "luot": luot_tim.danh_sach(),
        })

    @_bat_loi
    def rl_kho_nen(self, symbol):
        """Kho nến của symbol này đang có gì — gọi lại khi người dùng đổi mã.

        ⭐ Hiện TRƯỚC khi bấm chạy. Không có nó thì đặt khoảng ngoài dải đã tải rồi
        ngồi đợi, cuối cùng nhận *"không có nến nào"* — hoặc tệ hơn, app lặng lẽ tải
        180 MB từ MT5."""
        return _ok(self._kho_nen(str(symbol or "").strip().upper()))

    @staticmethod
    def _kho_nen(sym):
        try:
            t = nguon_nen.tom_tat(sym)
        except Exception as e:                    # noqa: BLE001
            return {"symbol": sym, "co": False, "chu": f"{type(e).__name__}: {e}"[:120]}
        return {"symbol": sym, "co": bool(t["so_nen"]),
                "so_nen": t["so_nen"], "tu": t["tu_chu"], "den": t["den_chu"],
                "so_lo_hong": t["so_lo_hong"], "spread_tb": t.get("spread_tb")}

    # ------------------------------------------------------------------ CHẠY
    @_bat_loi
    def rl_chay(self, dat):
        """Mở một lượt tìm trên LUỒNG NỀN, trả về mã ngay.

        Nến có thể phải tải từ MT5 (vài chục giây), nên chuyện đó cũng đẩy sang luồng
        nền: cửa sổ không được đứng hình trong lúc tải."""
        dat = dat or {}
        # ⭐ CHẠY LẠI Y HỆT — dựng lại từ ẢNH CHỤP của lượt cũ, không từ trạng thái
        # giao diện lúc này. Giao diện đã trôi đi (người dùng vặn vài núm rồi), nên
        # "y hệt" mà lấy từ đó thì không y hệt. Đây cũng là chỗ rẻ nhất: không phải
        # bơm hai chục ô ngược lên JS rồi bơm xuôi lại.
        cu = luot_tim.lay(str(dat.get("tu_luot") or ""))
        if cu is not None and cu.cau_hinh:
            dat = {**cu.cau_hinh, "ten": f"Chạy lại {cu.ten}"}
        l = luot_tim.LuotTim(str(dat.get("ten") or "Lượt tìm"))
        l.cau_hinh = dict(dat)
        l._ghi(nhan=_nhan_cau_hinh(dat, self._dat()))
        l._ghi(tong=int(dat.get("so_luot") or 100), chu="đang chuẩn bị nến…")
        luot_tim._ghi_so(l)
        threading.Thread(target=self._chay_nen_rl, args=(l, dat),
                         daemon=True).start()
        return _ok({"ma": l.ma})

    def _chay_nen_rl(self, l, dat):
        try:
            # ⚠ Báo tiến trình TẢI NẾN vào chính bảng của lượt tìm, không vào `self._tt`
            # riêng: cửa sổ chỉ hỏi `rl_trang_thai(ma)`, nên thứ nó không hỏi thì nó
            # không thấy — và người dùng ngồi nhìn một thanh đứng im suốt lúc tải.
            self._tt = _BaoQuaLuot(l)
            nen, cd, _ = self._nen_va_cd(dat.get("cai_dat") or {})
            # Tải xong thì TRẢ THANH TIẾN TRÌNH VỀ việc thật. Lúc tải, `da/tong` là số
            # nến; để nguyên thì thanh nhảy về 100% rồi mới bò lại từ 0, và câu "đang
            # chuẩn bị nến…" nói dối suốt lượt chạy.
            l._ghi(chu="", da_chay=0, tong=int(dat.get("so_luot") or 100))
            gio = dat.get("gio_toi_da")
            l._chay(nen, cd, int(dat.get("so_luot") or 100),
                    hat=int(dat.get("hat") or 0),
                    cua=dat.get("cua") or None,
                    tran=dat.get("tran") or None,
                    tat=tuple(dat.get("tat") or ()),
                    giu=int(dat.get("giu") or luot_tim.tim_kiem.GIU_DAU_BANG),
                    han_giay=float(gio) * 3600 if gio else None,
                    phang_toi_da=int(dat["phang_toi_da"])
                    if dat.get("phang_toi_da") else None,
                    so_nhan=int(dat.get("so_nhan") or 1))
        except Exception as e:                    # noqa: BLE001
            # Hỏng lúc CHUẨN BỊ (thiếu nến, chưa đặt khoảng…) cũng phải hiện ra ở đúng
            # chỗ người dùng đang nhìn, chứ không im lặng để thanh tiến trình quay mãi.
            l._ghi(loi=f"{type(e).__name__}: {e}", dang_chay=False,
                   xong_luc=time.time())

    @_bat_loi
    def rl_cau_hinh(self, ma):
        """Ảnh chụp cấu hình của một lượt — cho người đọc soi lại mình đã chạy với gì."""
        l = luot_tim.lay(str(ma))
        if l is None:
            return _loi("Không thấy lượt tìm này.")
        return _ok({"cau_hinh": l.cau_hinh, "nhan": l.trang_thai().get("nhan") or ""})

    @_bat_loi
    def rl_dung(self, ma):
        l = luot_tim.lay(str(ma))
        if l is None:
            return _loi("Không thấy lượt tìm này.")
        l.dung()
        return _ok(True)

    @_bat_loi
    def rl_xoa(self, ma):
        return _ok(luot_tim.xoa(str(ma)))

    # ------------------------------------------------------------------ NHÌN
    @_bat_loi
    def rl_trang_thai(self, ma):
        """Tiến trình một lượt. Giao diện hỏi ~500 ms một lần."""
        l = luot_tim.lay(str(ma))
        if l is None:
            return _loi("Không thấy lượt tìm này.")
        return _ok({**l.trang_thai(), "dau_bang": l.tom_tat()})

    @_bat_loi
    def rl_danh_sach(self):
        return _ok({"ds": luot_tim.danh_sach()})

    # --------------------------------------------------------------- MỞ KHOÁ
    @_bat_loi
    def rl_mo_khoa(self, ma, so_luong=5):
        """⭐ Chạy nhóm đầu bảng trên ĐOẠN KHOÁ — đoạn chưa từng dùng để chọn.

            core.md §18.3

        Đây là thứ biến *"sơ đồ khớp dữ liệu"* thành *"sơ đồ đạt"*. Mọi con số khác
        trên bàn điều khiển đều là số TRAIN — đo trên chính đoạn máy vừa đào bới hàng
        nghìn lượt; con số đáng tin duy nhất là con số đo ở đây.

        ⚠ **ĐẾM, không chặn.** Đây là studio, không phải cái lồng: bấm bao nhiêu lần
        cũng được. Nhưng mỗi lần bấm thì `khoa_da_mo` tăng và nằm đó — để lần thứ mười
        người đọc biết ngay con số mình đang tin đã mòn tới đâu. Nhìn một đoạn dữ liệu
        đủ nhiều lần thì nó thôi là "chưa thấy", và cái đồng hồ này là chỗ duy nhất nói
        ra chuyện đó.
        """
        l = luot_tim.lay(str(ma))
        if l is None:
            return _loi("Không thấy lượt tìm này.")
        d = self._dat()
        if not (d.get("khoa_tu") and d.get("khoa_den")):
            return _loi("Chưa đặt ĐOẠN KHOÁ.\n\nMở Dữ liệu và điền hai ô «khoá từ / "
                        "đến» — một khoảng KHÔNG nằm trong đoạn train. Không có nó thì "
                        "mọi con số vẫn chỉ là số TRAIN.")
        dau = l.tom_tat(int(so_luong))
        if not dau:
            return _loi("Lượt này chưa có sơ đồ nào qua cửa.")

        nen, cd, _ = self._nen_va_cd({"tu": d["khoa_tu"], "den": d["khoa_den"]})
        # ⚠ ĐÚNG bộ cửa lượt train đã dùng, không phải mặc định. Chọn bằng một thước
        # rồi nghiệm thu bằng thước khác thì cái chênh lệch đọc ra là chênh của THƯỚC.
        cua = l.cua
        cuon = str(d.get("cach_chia") or "cuon_toi") == "cuon_toi"
        buoc = str(d.get("buoc_cuon") or "quy")
        t0 = nguon_nen.thoi_diem(d["khoa_tu"])
        t1 = nguon_nen.thoi_diem(d["khoa_den"])
        moc = (datetime.datetime.fromtimestamp(t0, datetime.UTC).date(),
               datetime.datetime.fromtimestamp(t1, datetime.UTC).date())

        ra = []
        for x in dau:
            doc = l.so_do(x["hang"])
            if doc is None:
                continue
            try:
                # Không nhật ký: chỗ này chỉ CHẤM (§18.4b). Muốn xem nhật ký thì mở
                # sơ đồ sang cửa sổ vẽ rồi chạy Tester — ở đó nó đầy đủ.
                kq = bo_chay.chay(doc, nen, cd, ghi_nhat_ky=False)
                diem = cham_diem.cham(kq, cua)
                # ⭐ CUỐN TỚI: chấm TỪNG cửa sổ, từ CÙNG một lượt chạy. Sáu cửa sổ mà
                # chạy sáu lượt là đắt gấp sáu — chuỗi lãi/lỗ theo tuần đã có sẵn cả
                # dải, chỉ việc bỏ vào đúng rổ (§18.3).
                cs = cham_diem.cham_cuon(kq, *moc, buoc, cua) if cuon else []
            except Exception as e:              # noqa: BLE001
                ra.append({"hang": x["hang"], "loi": f"{type(e).__name__}: {e}"[:120]})
                continue
            duong = sum(1 for w in cs if w["diem"] > 0)
            ra.append({"hang": x["hang"], "train": x["diem"], "khoa": diem["diem"],
                       "khoa_lai_pt": diem["lai_pt"],
                       "khoa_sut_von_pt": diem["sut_von_pt"],
                       "khoa_so_lenh": diem["so_lenh"],
                       "khoa_tuan": diem["tuan"], "khoa_dat": diem["dat"],
                       "khoa_ly_do": diem["ly_do"],
                       # Điểm TỪNG cửa sổ — thứ trả lời "có đều QUA THỜI GIAN không",
                       # mà một con số gộp cả dải không nói ra được.
                       "cua_so": [{"tu": w["tu"], "den": w["den"], "diem": w["diem"],
                                   "trung_binh": w["trung_binh"],
                                   "dao_dong": w["dao_dong"],
                                   "co_lenh": w["co_lenh"], "so_ky": w["so_ky"]}
                                  for w in cs],
                       "cua_so_duong": duong, "so_cua_so": len(cs)})

        d["khoa_da_mo"] = int(d.get("khoa_da_mo") or 0) + 1
        self._cha._cai_dat = {**(self._cha._cai_dat or {}), "rl": d}
        core.save_settings(self._cha._cai_dat)
        return _ok({"ds": ra, "da_mo": d["khoa_da_mo"], "cuon": cuon, "buoc": buoc,
                    "tu": d["khoa_tu"], "den": d["khoa_den"]})

    # ------------------------------------------------------------------ MỞ
    @_bat_loi
    def rl_mo_so_do(self, ma, hang):
        """Đẩy sơ đồ hạng `hang` sang CỬA SỔ VẼ và kéo cửa sổ đó lên trước.

        ⭐ Nó là một file chiến lược BÌNH THƯỜNG (§18.6.5) — cùng JSON, cùng cửa sổ vẽ,
        cùng Tester. Không có loại "sơ đồ của máy"."""
        l = luot_tim.lay(str(ma))
        if l is None:
            return _loi("Không thấy lượt tìm này.")
        doc = l.so_do(int(hang))
        if doc is None:
            return _loi(f"Lượt này không có sơ đồ hạng {hang}.")
        self._cha._nhan_so_do_may(doc)
        return _ok({"ten": doc["name"]})
