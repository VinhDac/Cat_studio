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
import traceback

import core
import kho
import khung_cua_so
import luu_tru
import so_lenh


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


def _the_buoc(st, ts=None):
    """Một khối -> thẻ để giao diện vẽ.

    Giao diện KHÔNG tự ghép chữ: nếu nó ghép thì sớm muộn nó mô tả khác với thứ lõi
    thực sự hiểu. Nó chỉ chọn ICON theo `type`.

    Chữ trên hộp lấy từ `core.dong_khoi` — dòng NGẮN, mỗi trường một dòng. Câu đầy đủ
    (`core.action_display`) để dành cho tooltip: nhìn hộp thì cần liếc ra ngay, rê chuột
    mới cần biết đủ chi tiết."""
    the = {"id": st.get("id"), "kind": st.get("kind"), "title": core.step_title(st),
           "badges": [], "lines": [], "mo_ta": "", "ghim": bool(st.get("ghim")),
           "la_cong": core.is_branch_gate(st)}

    if core.is_start_step(st):
        the["badges"] = ["mỗi nến chạy lại từ đây"]
        return the

    the["lines"] = [{"text": x, "type": st.get("type")}
                    for x in core.dong_khoi(st, ts)]
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
        g["cards"] = [_the_buoc(s, ts) for s in g.get("steps") or []]
        doc[tab] = g
    return doc


# ---------------------------------------------------------------------------
class Api:
    """Mọi phương thức công khai ở đây thành `window.pywebview.api.<tên>` bên JS."""

    def __init__(self):
        # Gạch dưới hết — xem chú thích đầu file.
        self._window = None
        self._tester = None
        self._doc_tester = None
        self._khung = khung_cua_so.KhungTuVe()
        self._cai_dat = core.load_settings()
        self._khoa = threading.Lock()

    # -- gắn cửa sổ (app_web.py gọi, không phải JS) --
    def _gan_window(self, w):
        self._window = w

    def _ban(self, ten, du_lieu):
        """Đẩy sự kiện sang JS. Nuốt lỗi: cửa sổ có thể đã đóng giữa chừng."""
        if not self._window:
            return
        try:
            self._window.evaluate_js(
                f"window.__su_kien && window.__su_kien("
                f"{json.dumps(ten)}, {json.dumps(du_lieu, ensure_ascii=False)})")
        except Exception:
            pass

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
    def new_step(self, kind="action", action_type=None):
        st = (core.make_start_step() if kind == core.KIND_START
              else core.make_action_step(
                  _hanh_dong_mac_dinh(action_type or core.CHECK_COND)))
        return _ok({"step": st, "card": _the_buoc(st)})

    @_bat_loi
    def clone_steps(self, steps):
        moi, tra = core.clone_steps(steps)
        return _ok({"steps": moi, "map": tra, "cards": [_the_buoc(s) for s in moi]})

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
        """Cửa sổ thứ hai. Còn là bộ khung — nội dung bàn sau.

        Dựng sẵn ở đây vì phần khó không phải giao diện tester mà là ĐƯỜNG ĐI: cửa sổ
        thứ hai, kênh sự kiện riêng, và việc đóng nó không được kéo theo cửa sổ chính."""
        import webview
        cu = self._tester
        if cu is not None:
            try:
                cu.destroy()
            except Exception:
                pass
            self._tester = None
        trang = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "webui", "dist", "index.html")
        self._tester = webview.create_window(
            f"Strategy Tester — {doc['name']}",
            url=f"file:///{trang}?tester=1" if os.path.exists(trang) else None,
            html=None if os.path.exists(trang) else _TRANG_TESTER_TAM,
            js_api=self, width=1100, height=740, min_size=(820, 560),
            background_color="#202020")
        self._doc_tester = doc

    @_bat_loi
    def tester_doc(self):
        """Cửa sổ tester hỏi: tôi đang phải chạy sơ đồ nào?"""
        return _ok(self._doc_tester)

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
        if (s or {}).get("timeframe") in core.TIMEFRAMES:
            cd["timeframe"] = s["timeframe"]
        if (s or {}).get("accent"):
            cd["accent"] = str(s["accent"])
        self._cai_dat = core.save_settings(cd)
        return _ok(self._cai_dat)

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

    @_bat_loi
    def set_title(self, ten):
        if self._window:
            self._window.set_title(f"{ten} — Cat Studio" if ten else "Cat Studio")
        return _ok(True)

    # ------------------------------------------------------------------ cửa sổ
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

    def dong_app(self):
        """Cửa sổ chính đóng — dọn cửa sổ tester theo. KHÔNG bọc `_bat_loi`: pywebview
        gọi nó từ sự kiện `closing`, không phải từ JS."""
        try:
            if self._tester:
                self._tester.destroy()
        except Exception:
            pass


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
    e_bd = core.make_start_step("Mỗi nến M5 — tìm tín hiệu")
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
    m_bd = core.make_start_step("Mỗi nến M5 — với TỪNG lệnh đang sống")
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
            "symbol": "XAUUSD", "timeframe": "M5",
            # Bộ tham số lấy thẳng từ `kho/engine_d02.py` — cùng một nguồn với mặc
            # định của EA, nên không có chuyện tài liệu nói một đằng mẫu chạy một nẻo.
            "tham_so": [dict(t) for t in kho.engine_d02.THAM_SO_MAC_DINH],
            "entry": entry, "manage": manage}
