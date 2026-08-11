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
import functools
import inspect
import json
import os
import threading
import time
import traceback

import core
import kho
import khung_cua_so
import bo_chay
import lich_su
import luu_tru
import nguon_nen
import nhat_ky
import so_lenh
import tinh_toan


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
        return {"type": loai, "huong": "mua", "loai": "stop", "lot": 0.01,
                "dem": {"tinh": "theo_ATR", "value": 0.1},
                "sl": {"tinh": "theo_ATR", "value": 1.5},
                "tp": {"tinh": "theo_R", "value": 2}}
    if loai == core.SUA_LENH:
        return {"type": loai, "che_do": "hoa_von"}
    return {"type": core.CHECK_COND, "conditions": [{
        "trai": {"ten": "atr_bps", "tf": "M5", "period": 14},
        "phep": "<", "phai_loai": "so", "phai": 7.0}]}


# ---------------------------------------------------------------------------
# Thẻ vẽ lên hộp — NỘI DUNG DO PYTHON SINH
# ---------------------------------------------------------------------------


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
        if n > 1:
            the["badges"].append(f"{n} điều kiện · VÀ")
    return the


def _kem_the(doc):
    """Gắn `cards` vào từng sơ đồ. Chữ trên hộp do Python sinh, JS không ghép lại.

    Truyền cả bảng tham số xuống để dòng chữ hiện `ngưỡng nén = 7` thay vì trơ ra một
    cái tên không ai biết bằng bao nhiêu."""
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
            "cach_tinh": core.CACH_TINH,
            "huong": core.HUONG,
            "loai_lenh": core.LOAI_LENH,
            "sua_che_do": core.SUA_CHE_DO,
            "sua_can_gia": list(core.SUA_CAN_GIA),
            "sua_can_phan_tram": list(core.SUA_CAN_PHAN_TRAM),

            "don_vi_tham_so": core.DON_VI,
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
    def describe_actions(self, actions):
        return _ok([{"text": core.action_display(a), "type": (a or {}).get("type")}
                    for a in (actions or [])])

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
        `nguong_nen_bps = ?` — khối vừa dán/vừa nhập trông như hỏng, trong khi tham số
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
        return _ok(_kem_the(_so_do_mau()))

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
    _LOC = ("Chiến lược Cat_Studio (*.json)", "*.json")

    @_bat_loi
    def open_process_file(self):
        import webview
        r = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False, file_types=(self._LOC,))
        if not r:
            return {"ok": False}          # người dùng bấm Huỷ — KHÔNG phải lỗi
        with open(r[0], encoding="utf-8") as f:
            return _ok(_kem_the(core.normalize_process(json.load(f))))

    @_bat_loi
    def save_process_file(self, doc):
        import webview
        d = core.normalize_process(doc)
        r = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=f"{d['name']}.json",
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

    def _mo_cua_so_tester(self, doc):
        """Cửa sổ thứ hai.

        CỬA SỔ CÒN SỐNG THÌ GIỮ, chỉ nạp sơ đồ mới. Bản cũ huỷ rồi tạo lại mỗi lần bấm
        ▶ — mà vòng lặp debug thật là *sửa → chạy → so*, nên mỗi lần chạy là mất con
        trỏ nến, mất mức thu phóng, mất vị trí cuộn nhật ký, mất cả bộ lọc đang đặt."""
        self._doc_tester = doc
        if self._tester is not None:
            self._tester.set_title(f"{doc['name']} — Strategy Tester")
            # Cửa sổ còn sống: đẩy sơ đồ mới xuống, nó TỰ CHẠY LẠI. Bấm ▶ là chạy, không
            # phải mở ra một bảng cài đặt nữa rồi bấm tiếp.
            self._api_tester._ban("so_do_moi", doc)
            return

        import webview
        trang = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "webui", "dist", "index.html")
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
        d["cach_tinh"] = core.CACH_TINH
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
        for k in ("spread_diem", "deposit", "commission"):
            if k in t:
                try:
                    cu[k] = float(t[k])
                except (TypeError, ValueError):
                    pass
        for k in ("don_bay", "delay_ms"):
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
    def nguon_liet_ke(self):
        return _ok({"ds": nguon_nen.liet_ke(), "co_mt5": nguon_nen.CO_MT5})

    @_bat_loi
    def nguon_uoc_tinh(self, symbol, tu, den):
        """Bấm Tải sẽ tải bao nhiêu? BÁO TRƯỚC số MB — không bao giờ tải lén."""
        k = nguon_nen.khoang_thieu(symbol, tu, den)
        return _ok(dict(nguon_nen.uoc_tinh(k), du=not k))

    @_bat_loi
    def nguon_tai(self, symbol, tu, den):
        r = nguon_nen.tai(symbol, tu, den,
                          tien_do=lambda i, n, c: self._ban(
                              "tai", {"da": i, "tong": n, "chu": c}))
        return _ok({"chu": r["chu"], "meta": r["meta"], "ds": nguon_nen.liet_ke()})

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


class ApiTester(NenCuaSo):
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

    @_bat_loi
    def tester_doc(self):
        """Cửa sổ tester hỏi: tôi đang phải chạy sơ đồ nào?"""
        return _ok(self._cha._doc_tester)

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
        luu = dict(luu_tru.CAI_DAT_MAC_DINH["test"])
        luu.update((self._cha._cai_dat or {}).get("test") or {})
        luu.update(ci or {})
        ci = luu
        doc = doc or self._cha._doc_tester
        if not doc:
            raise RuntimeError("Chưa có sơ đồ nào để chạy.")
        m = nguon_nen.doc_meta(ci.get("symbol") or "XAUUSD") or {}
        nen = nguon_nen.doc(ci.get("symbol") or "XAUUSD", ci.get("tu"), ci.get("den"))
        if not len(nen):
            raise RuntimeError(
                "Chưa có nến nào cho khoảng này. Mở Cài đặt → Strategy Test → Tải thêm.")
        cd = bo_chay.CaiDat(
            symbol=ci.get("symbol") or "XAUUSD", tu=ci.get("tu"), den=ci.get("den"),
            spread_diem=ci.get("spread_diem", m.get("spread_tb") or 20),
            point=m.get("point") or 0.01,
            contract_size=m.get("contract_size") or 100.0,
            digits=m.get("digits") or 2,
            deposit=ci.get("deposit", 10000.0),
            commission=ci.get("commission", 0.0),
            don_bay=ci.get("don_bay", 100))
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
    def test_nen(self, j, so=400):
        """Cửa sổ nến M1 kết thúc ở con trỏ. KHÔNG trả nến bên phải con trỏ.

        Đó là cả điểm của replay: nến chưa xảy ra thì CHƯA TỒN TẠI. Thấy trước nến sau
        rồi thì mọi phán đoán "chỗ này lẽ ra nên vào lệnh" đều là tự lừa mình."""
        kq = self._doi_kq()
        j = max(0, min(int(j), len(kq.nen1) - 1))
        i0 = max(0, j - int(so) + 1)
        a = kq.nen1[i0:j + 1]
        return _ok({
            "t": a["t"].tolist(), "o": a["o"].tolist(), "h": a["h"].tolist(),
            "l": a["l"].tolist(), "c": a["c"].tolist(), "j0": i0, "j": j,
        })

    @_bat_loi
    def test_khung(self, j):
        """Mọi thứ giao diện cần tại MỘT vị trí con trỏ: bảng số liệu + lệnh để vẽ."""
        kq = self._doi_kq()
        j = max(0, min(int(j), len(kq.nen1) - 1))
        i = max(0, int(kq._ct.m1_to_5[j]))
        return _ok({
            "j": j, "i": i,
            "t": int(kq.nen1["t"][j]),
            "bang": kq.bang(i, j),
            "lenh": kq.the_lenh(i),
        })

    @_bat_loi
    def test_nen_tf(self, tf, j, tran=60000):
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
        if len(a) > int(tran):
            a = a[-int(tran):]
        return _ok({"t": a["t"].tolist(), "o": a["o"].tolist(), "h": a["h"].tolist(),
                    "l": a["l"].tolist(), "c": a["c"].tolist(), "j": j})

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
        j0 = max(0, min(int(j0), len(kq.nen1) - 1))
        n = max(1, min(int(n), 2000))
        j1 = min(len(kq.nen1), j0 + n)
        a = kq.nen1[j0:j1]
        i5 = kq._ct.m1_to_5[j0:j1]
        cv = kq.cot_vung

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
            # Ô khung để trống nghĩa là "khung quyết định" (`ChuongTrinh.khoa`). Bảng ghi
            # rõ khung THẬT chứ không bỏ trống: `ATR` trơ ra một mình thì người dùng
            # không biết đang xem ATR của khung nào. Toán hạng engine vốn không có khung.
            tf = o.get("tf")
            if not tf and (o["ten"] in tinh_toan.BANG or o["ten"] in ct_.COT_GIA):
                tf = ct_.tf5
            phan = [tf] if tf else []
            if o.get("period"):
                phan.append(str(ct_.so(o["period"]) if isinstance(o["period"], str)
                                else o["period"]).rstrip("0").rstrip("."))
            if o.get("method"):
                phan.append(str(o["method"]))
            # Nhãn tách LÀM ĐÔI. Trước đây nối thành `ATR chuẩn hoá (bps)(M5, 14)` rồi
            # giao diện dán cả cục vào cột trái, nên tên dài bị cắt cụt trong khi giữa
            # nhãn và số là một khe rỗng dài. Giờ phần bổ nghĩa (khung · chu kỳ · kiểu)
            # là một cột riêng, nằm đúng vào cái khe đó.
            if o["nhom"] not in nhom_dau:
                nhom_dau[o["nhom"]] = {"nhom": o["nhom"], "dong": []}
                bang.append(nhom_dau[o["nhom"]])
            nhom_dau[o["nhom"]]["dong"].append(
                {"ten": o["nhan"], "phu": "·".join(phan), "gia_tri": ds})

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
        })

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

        k = ct.khoa(o) if (ten in tinh_toan.BANG or ten in ct.COT_GIA) else None
        if k is not None and k in ct._cot:
            return theo(ct._cot[k])
        if ten in kq.cot_vung:
            return theo(kq.cot_vung[ten], ten in core.TOAN_HANG_DUNG_SAI)
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
    def test_nhat_ky(self, tu=0, so=200, chi_co_viec=True):
        kq = self._doi_kq()
        return _ok(nhat_ky.dung_lo(kq, int(tu), int(so), bool(chi_co_viec)))

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


def _so_do_mau():
    """Compress: biến động co lại như lò xo → đặt lệnh chờ ngay mép vùng → phá ra là khớp.

    Mọi khoảng cách là bội của ATR hoặc của R, không một pip hay đô nào — nên cùng một
    bộ số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số."""

    def dk(ten, conds, x, y):
        s = core.make_action_step({"type": core.CHECK_COND, "name": ten,
                                   "conditions": conds})
        s["pos"] = [x, y]
        return s

    def hd(ten, act, x, y):
        s = core.make_action_step(dict(act, name=ten))
        s["pos"] = [x, y]
        return s

    def so(ten, phep, gia_tri, **kw):
        return {"trai": dict({"ten": ten}, **kw), "phep": phep,
                "phai_loai": "so", "phai": gia_tri}

    def ts(ten, phep, ten_tham_so, **kw):
        """Vế phải là một THAM SỐ CÓ TÊN, không phải số gõ tay.

        Nhờ vậy `nguong_nen_bps` chỉ tồn tại ở MỘT chỗ, dù nó được hỏi ở cả hai sơ đồ —
        Entry hỏi "còn nén không", Manage hỏi "nén tan chưa". Gõ tay hai nơi thì sửa
        một chỗ là hai vế lệch nhau âm thầm."""
        return {"trai": dict({"ten": ten}, **kw), "phep": phep,
                "phai_loai": "tham_so", "phai": ten_tham_so}

    def dung_sai(ten, dao=False):
        c = {"trai": {"ten": ten}}
        if dao:
            c["dao"] = True
        return c

    def canh(a, b):
        return {"from": a["id"], "to": b["id"], "port": "out",
                "from_side": "right", "to_side": "left"}

    # ========================= ENTRY =========================
    e_bd = core.make_start_step("Tìm tín hiệu", core.NHIP_MAC_DINH[core.TAB_ENTRY])
    e_bd["pos"] = [40, 300]

    e_nen = dk("Vùng nén đã xác nhận?", [
        ts("atr_bps", "<", "nguong_nen_bps", tf="M5", period="chu_ky_atr"),
        ts("so_nen_nen", ">=", "so_nen_nen"),          # đủ K nến liên tiếp
        ts("rong_vung_atr", "<=", "rong_vung_toi_da"),  # vùng không quá rộng
        dung_sai("vung_da_sinh_lenh", dao=True),        # = COMP_CONSUMED
    ], 340, 300)

    e_cho = dk("Còn chỗ cho lệnh mới?", [
        so("so_lenh_cho", "==", 0),      # D_02: đúng MỘT lệnh chờ tại một thời điểm
        ts("so_vi_the", "<", "so_vi_the_toi_da"),   # bằng nhau là đã đầy
    ], 700, 300)

    def vao(huong):
        return {
            "type": core.VAO_LENH, "huong": huong, "loai": "stop", "lot": "lot",
            # Đệm đo bằng ATR HIỆN TẠI — tấm khiên mỏng ngoài mép vùng, đủ lọc một
            # nhịp phá giả. Lệnh chờ luôn neo vào mép vùng thuận chiều.
            "dem": {"tinh": "theo_ATR", "value": "dem_vao_lenh"},
            # Rủi ro đo bằng ATR TRUNG BÌNH CẢ VÙNG NÉN — lấy mức nhiễu thật suốt cú
            # nén, nên mỗi lệnh rủi ro một R tương đương dù vùng rộng hẹp khác nhau.
            # HAI CHỮ ATR NÀY LÀ HAI THỨ KHÁC NHAU, tách ra là có chủ ý.
            "sl": {"tinh": "theo_ATR_vung", "value": "sl_theo_atr_vung"},
            "tp": {"tinh": "theo_R", "value": "ty_le_RR"},
        }

    e_len = dk("Xu hướng LÊN?", [{
        "trai": {"ten": "close", "tf": "M15", "shift": 1}, "phep": ">",
        "phai_loai": "toan_hang",
        "phai": {"ten": "ma", "tf": "M15", "period": "chu_ky_ma",
                 "method": "SMA"}}], 1060, 160)
    e_mua = hd("Buy Stop trên đỉnh vùng", vao("mua"), 1420, 160)

    e_xuong = dk("Xu hướng XUỐNG?", [{
        "trai": {"ten": "close", "tf": "M15", "shift": 1}, "phep": "<",
        "phai_loai": "toan_hang",
        "phai": {"ten": "ma", "tf": "M15", "period": "chu_ky_ma",
                 "method": "SMA"}}], 1060, 440)
    e_ban = hd("Sell Stop dưới đáy vùng", vao("ban"), 1420, 440)

    entry = {
        "steps": [e_bd, e_nen, e_cho, e_len, e_mua, e_xuong, e_ban],
        "edges": [canh(e_bd, e_nen), canh(e_nen, e_cho),
                  canh(e_cho, e_len), canh(e_len, e_mua),
                  canh(e_cho, e_xuong), canh(e_xuong, e_ban)],
    }

    # ========================= MANAGE =========================
    # Chạy lại từ đầu mỗi nến, CHO TỪNG LỆNH. Không giữ con trỏ — mọi câu hỏi đều tính
    # lại từ trạng thái quan sát được, y như D_02 làm mỗi tick.
    m_bd = core.make_start_step("Quản lý lệnh", core.NHIP_MAC_DINH[core.TAB_MANAGE])
    m_bd["pos"] = [40, 300]

    m_huy = dk("Chưa khớp mà nén đã tan?", [
        dung_sai("lenh_da_khop", dao=True),
        # CÙNG một `nguong_nen_bps` với cổng nén bên Entry — đây chính là chỗ hai
        # hằng số gõ tay sẽ lệch nhau nếu không có bảng tham số.
        ts("atr_bps", ">=", "nguong_nen_bps", tf="M5", period="chu_ky_atr"),
    ], 400, 160)
    m_huy_hd = hd("Huỷ lệnh chờ",
                  {"type": core.SUA_LENH, "che_do": "huy_cho"}, 760, 160)

    # Ba dòng guard của `ManageBreakEven` gói đúng vào một cổng. Vế "SL chưa ở hoà vốn"
    # KHÔNG được thiếu: Manage chạy lại mỗi nến, không có nó thì lệnh sửa SL bắn hoài.
    m_be = dk("Đã khớp, đủ 1R, SL chưa hoà vốn?", [
        dung_sai("lenh_da_khop"),
        dung_sai("lenh_sl_hoa_von", dao=True),
        ts("lenh_lai_R", ">=", "hoa_von_tai"),
    ], 400, 440)
    m_be_hd = hd("Dời SL về giá vào",
                 {"type": core.SUA_LENH, "che_do": "hoa_von"}, 760, 440)

    manage = {
        "steps": [m_bd, m_huy, m_huy_hd, m_be, m_be_hd],
        "edges": [canh(m_bd, m_huy), canh(m_huy, m_huy_hd),
                  canh(m_bd, m_be), canh(m_be, m_be_hd)],
    }

    return {"schema": 3, "type": "strategy", "name": "Compress (mẫu)",
            "symbol": "XAUUSD",
            # Bộ tham số lấy thẳng từ `kho/engine_d02.py` — cùng một nguồn với mặc
            # định của EA, nên không có chuyện tài liệu nói một đằng mẫu chạy một nẻo.
            "tham_so": [dict(t) for t in kho.engine_d02.THAM_SO_MAC_DINH],
            "entry": entry, "manage": manage}
