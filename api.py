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
import khung_cua_so


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
        return {"type": loai, "che_do": "hoa_von", "muc_tieu": "vi_the",
                "khoang": {"tinh": "theo_R", "value": 1}}
    if loai == core.DAT_CO:
        return {"type": loai, "ten_co": "da_dung_tin_hieu", "gia_tri": True}
    return {"type": core.CHECK_COND, "conditions": [{
        "trai": {"ten": "atr_bps", "tf": "M5", "period": 14},
        "phep": "<", "phai_loai": "so", "phai": 7.0}]}


# ---------------------------------------------------------------------------
# Thẻ vẽ lên hộp — NỘI DUNG DO PYTHON SINH
# ---------------------------------------------------------------------------


def _dong_the(a, prologue=False):
    return {"text": core.action_display(a), "type": (a or {}).get("type"),
            "prologue": prologue, "goal": False}


def _the_buoc(st):
    """Một khối -> thẻ để giao diện vẽ.

    Giao diện KHÔNG tự ghép chữ: nếu nó ghép thì sớm muộn nó mô tả khác với thứ lõi
    thực sự hiểu. Nó chỉ chọn ICON theo `type`."""
    kind = st.get("kind")
    the = {"id": st.get("id"), "kind": kind, "title": core.step_title(st),
           "badges": [], "lines": [], "so_hanh_dong": 0,
           "co_muc_tieu": False, "ghim": bool(st.get("ghim")),
           "la_cong": core.is_branch_gate(st)}

    if kind == core.KIND_START:
        the["badges"] = ["điểm neo đánh số"]
        return the

    if core.has_actions(st):
        acts = st.get("actions") or []
        the["so_hanh_dong"] = len(acts)
        mo_dau = st.get("loop_start_index", 0) if core.is_loop_step(st) else 0
        the["lines"] = [_dong_the(a, i < mo_dau) for i, a in enumerate(acts)]
        if core.is_loop_step(st):
            the["badges"].append(f"tối đa {st.get('max_nen', core.DEFAULT_MAX_NEN)} nến")
            if st.get("tf"):
                the["badges"].append(st["tf"])
        else:
            the["badges"].append("chạy 1 lần")
        return the

    the["so_hanh_dong"] = 1
    the["lines"] = [_dong_the(st)]
    if core.is_branch_gate(st):
        the["badges"].append("cổng rẽ nhánh")
    return the


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

            "kinds": [core.KIND_START, core.KIND_LOOP, core.KIND_GROUP, core.KIND_ACTION],
            "kind_labels": core.KIND_LABELS,

            "action_types": core.hanh_dong_hien(),
            "action_types_tat_ca": core.ACTION_TYPES,
            "action_labels": core.ACTION_LABELS,
            "branch_type": core.CHECK_COND,

            "timeframes": core.TIMEFRAMES,
            "ma_methods": core.MA_METHODS,
            "toan_hang": [{"key": k, "nhan": n, "nhom": g, "tham_so": p}
                          for k, n, g, p in core.TOAN_HANG],
            "phep_so": core.PHEP_SO,
            "cach_tinh": core.CACH_TINH,
            "huong": core.HUONG,
            "loai_lenh": core.LOAI_LENH,
            "sua_che_do": core.SUA_CHE_DO,
            "sua_can_gia": list(core.SUA_CAN_GIA),
            "sua_can_phan_tram": list(core.SUA_CAN_PHAN_TRAM),

            "template_kinds": core.TEMPLATE_KINDS,
            "accent_presets": core.ACCENT_PRESETS,
            "default_max_nen": core.DEFAULT_MAX_NEN,
            "max_process_steps": core.MAX_PROCESS_STEPS,
        })

    # ------------------------------------------------------------------ mô tả
    @_bat_loi
    def describe(self, steps):
        return _ok([_the_buoc(s) for s in (steps or []) if isinstance(s, dict)])

    @_bat_loi
    def describe_actions(self, actions):
        return _ok([{"text": core.action_display(a), "type": (a or {}).get("type")}
                    for a in (actions or [])])

    @_bat_loi
    def action_defaults(self, action_type):
        return _ok(_hanh_dong_mac_dinh(action_type))

    @_bat_loi
    def save_action(self, draft):
        """Chuẩn hoá + soát một hành động. Hộp thoại KHÔNG tự soát — nó gửi bản nháp
        thô sang đây, để luật hợp lệ chỉ nằm ở đúng một chỗ."""
        a = core.normalize_action(draft)
        if a is None:
            return {"ok": False, "error": "Loại hành động không hợp lệ."}
        loi = []
        core.validate_actions([a], lambda m, i=None: loi.append(m))
        return _ok({"action": a, "display": core.action_display(a)}, loi=loi)

    # ------------------------------------------------------------------ khối
    @_bat_loi
    def new_step(self, kind="action", action_type=None):
        if kind == core.KIND_START:
            st = core.make_start_step()
        elif kind == core.KIND_LOOP:
            st = core.make_loop_step()
        elif kind == core.KIND_GROUP:
            st = core.make_group_step()
        else:
            st = core.make_action_step(
                _hanh_dong_mac_dinh(action_type or core.CHECK_COND))
        return _ok({"step": st, "card": _the_buoc(st)})

    @_bat_loi
    def clone_steps(self, steps):
        moi, tra = core.clone_steps(steps)
        return _ok({"steps": moi, "map": tra, "cards": [_the_buoc(s) for s in moi]})

    # ------------------------------------------------------------------ soát
    @_bat_loi
    def validate(self, steps, edges=None):
        """Nguồn của HUY HIỆU SỐ và của bảng Vấn đề.

        `order` trả ra ngang hàng với `value` (không lồng vào trong) để giao diện đọc
        thẳng — nó cần số thứ tự ở mọi lần vẽ lại, không chỉ khi có lỗi."""
        steps = steps or []
        if edges is None:
            edges = core.default_edges(steps)
        doc = {"steps": steps, "edges": edges}
        probs = core.validate_process(doc)
        luong = core.flow_order(steps, edges)
        return _ok(probs,
                   so_loi=sum(1 for p in probs if p["severity"] == "error"),
                   so_canh_bao=sum(1 for p in probs if p["severity"] == "warning"),
                   order=luong["order"],
                   unreachable=luong["unreachable"],
                   entry=luong["entry"],
                   quay_lai=[list(c) for c in luong["quay_lai"]],
                   vong_ho=[list(c) for c in luong["vong_ho"]],
                   lech_nhanh=luong["lech_nhanh"],
                   loop=luong["loop"])

    # ------------------------------------------------------------------ tài liệu
    @_bat_loi
    def new_process(self):
        d = core.new_process()
        d["cards"] = [_the_buoc(s) for s in d["steps"]]
        return _ok(d)

    @_bat_loi
    def demo_process(self):
        """Sơ đồ mẫu: chiến lược Compress — nén biến động rồi phá vùng.

        Dựng bằng chính các khối người dùng có, không phải thứ đặc biệt gì — mở ra là
        thấy ngay bộ khối này diễn tả được một chiến lược thật tới đâu."""
        d = _so_do_mau()
        d["cards"] = [_the_buoc(s) for s in d["steps"]]
        return _ok(d)

    @_bat_loi
    def load_process(self, name):
        d = core.normalize_process(core.load_template("strategy", name))
        d["cards"] = [_the_buoc(s) for s in d["steps"]]
        return _ok(d)

    @_bat_loi
    def save_process(self, name, steps, edges=None, symbol=None, timeframe=None):
        d = core.normalize_process({"name": name, "steps": steps, "edges": edges,
                                    "symbol": symbol, "timeframe": timeframe})
        p = core.save_template("strategy", name, d)
        return _ok({"path": p, "name": name})

    @_bat_loi
    def list_templates(self, kind="strategy"):
        return _ok(core.list_templates(kind))

    @_bat_loi
    def delete_template(self, kind, name):
        return _ok(core.delete_template(kind, name))

    @_bat_loi
    def save_step_template(self, kind, name, step):
        st = core.normalize_step(step)
        if not st:
            return {"ok": False, "error": "Khối không hợp lệ."}
        core.save_template(kind, name, st)
        return _ok({"name": name})

    @_bat_loi
    def insert_step_template(self, kind, name):
        st = core.normalize_step(core.load_template(kind, name))
        if not st:
            return {"ok": False, "error": "Template hỏng."}
        st["id"] = core.new_step_id()
        st.pop("ghim", None)
        return _ok({"step": st, "card": _the_buoc(st)})

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
            d = core.normalize_process(json.load(f))
        d["cards"] = [_the_buoc(s) for s in d["steps"]]
        return _ok(d)

    @_bat_loi
    def save_process_file(self, name, steps, edges=None, symbol=None, timeframe=None):
        import webview
        r = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=f"{name or 'chien_luoc'}.json",
            file_types=(self._LOC,))
        if not r:
            return {"ok": False}
        p = r if isinstance(r, str) else r[0]
        d = core.normalize_process({"name": name, "steps": steps, "edges": edges,
                                    "symbol": symbol, "timeframe": timeframe})
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return _ok({"path": p})

    # ------------------------------------------------------------------ chạy
    @_bat_loi
    def mo_tester(self, name, steps, edges=None, symbol=None, timeframe=None):
        """▶ Chạy — mở cửa sổ Strategy Tester.

        Chặn TRƯỚC nếu sơ đồ còn lỗi: mở tester ra để nó báo lại đúng mấy lỗi mà bảng
        Vấn đề đã hiện sẵn là bắt người dùng đi hai vòng cho cùng một thông tin."""
        steps = steps or []
        if edges is None:
            edges = core.default_edges(steps)
        probs = core.validate_process({"steps": steps, "edges": edges})
        loi = [p for p in probs if p["severity"] == "error"]
        if loi:
            return {"ok": False, "error": "Sơ đồ còn lỗi, chưa chạy được.", "loi": loi}
        canh_bao = [p for p in probs if p["severity"] == "warning"]

        d = core.normalize_process({"name": name, "steps": steps, "edges": edges,
                                    "symbol": symbol, "timeframe": timeframe})
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
# Sơ đồ mẫu — chiến lược Compress
# ---------------------------------------------------------------------------


def _so_do_mau():
    """Compress: nén biến động → đặt lệnh chờ ngoài mép vùng → phá ra là khớp.

    Mọi khoảng cách là bội của ATR hoặc của R, không có pip/đô nào — nên cùng một bộ
    số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số."""
    def dk(ten, conds, x, y):
        s = core.make_action_step({"type": core.CHECK_COND, "name": ten,
                                   "conditions": conds})
        s["pos"] = [x, y]
        return s

    def hd(ten, act, x, y):
        s = core.make_action_step(dict(act, name=ten))
        s["pos"] = [x, y]
        return s

    def tt(ten, key, tf="M5", **kw):
        return dict({"ten": key, "tf": tf}, **kw)

    bd = core.make_start_step()
    bd["pos"] = [40, 340]

    nen = dk("Nến này có nén không?",
             [{"trai": tt("", "atr_bps", period=14), "phep": "<",
               "phai_loai": "so", "phai": 7.0}], 320, 200)

    du_nen = dk("Đủ K nến & vùng vừa khổ?",
                [{"trai": tt("", "so_nen_nen"), "phep": ">=", "phai_loai": "so",
                  "phai": 10},
                 {"trai": tt("", "rong_vung_atr"), "phep": "<=", "phai_loai": "so",
                  "phai": 4.0}], 660, 200)

    xu_huong_len = dk("Xu hướng LÊN (M15)",
                      [{"trai": tt("", "close", tf="M15", shift=1), "phep": ">",
                        "phai_loai": "toan_hang",
                        "phai": tt("", "ma", tf="M15", period=50, method="SMA")},
                       {"trai": tt("", "co_lenh_cho"), "dao": True}], 1000, 60)

    xu_huong_xuong = dk("Xu hướng XUỐNG (M15)",
                        [{"trai": tt("", "close", tf="M15", shift=1), "phep": "<",
                          "phai_loai": "toan_hang",
                          "phai": tt("", "ma", tf="M15", period=50, method="SMA")},
                         {"trai": tt("", "co_lenh_cho"), "dao": True}], 1000, 340)

    mua = hd("Buy Stop trên đỉnh vùng",
             {"type": core.VAO_LENH, "huong": "mua", "loai": "stop", "lot": 0.01,
              "dem": {"tinh": "theo_ATR", "value": 0.1},
              "sl": {"tinh": "theo_ATR", "value": 1.5},
              "tp": {"tinh": "theo_R", "value": 2}}, 1340, 60)

    ban = hd("Sell Stop dưới đáy vùng",
             {"type": core.VAO_LENH, "huong": "ban", "loai": "stop", "lot": 0.01,
              "dem": {"tinh": "theo_ATR", "value": 0.1},
              "sl": {"tinh": "theo_ATR", "value": 1.5},
              "tp": {"tinh": "theo_R", "value": 2}}, 1340, 340)

    # Vòng theo dõi: mỗi nến mới lại thử hai cổng phía sau. Không cổng nào khớp thì
    # đơn giản là chờ nến sau — đó là lý do khối này tồn tại, và cũng là lý do nó
    # được miễn luật "phải có nhánh mặc định".
    cho = core.make_loop_step("Chờ khớp / chờ vùng tan")
    cho["pos"] = [1680, 200]
    cho["tf"] = "M5"
    cho["max_nen"] = 200
    cho["actions"] = []

    da_khop = dk("Lệnh đã khớp?", [{"trai": tt("", "lenh_da_khop")}], 2020, 60)
    vung_tan = dk("Vùng đã tan? (ATR bung ra)",
                  [{"trai": tt("", "atr_bps", period=14), "phep": ">=",
                    "phai_loai": "so", "phai": 7.0}], 2020, 340)

    hoa_von = hd("Dời SL về hoà vốn khi lãi 1R",
                 {"type": core.SUA_LENH, "che_do": "hoa_von", "muc_tieu": "vi_the",
                  "khoang": {"tinh": "theo_R", "value": 1}}, 2360, 60)

    huy = hd("Huỷ lệnh chờ",
             {"type": core.SUA_LENH, "che_do": "huy_cho", "muc_tieu": "lenh_cho"},
             2360, 340)

    # `nen` là điểm quay lại: mọi đường đi hết một vòng đều về đây đếm tiếp nến.
    # GHIM nó lại → số của nó không đổi và không có cảnh báo vòng lặp nào.
    nen["ghim"] = True

    steps = [bd, nen, du_nen, xu_huong_len, xu_huong_xuong, mua, ban, cho,
             da_khop, vung_tan, hoa_von, huy]

    def e(a, b):
        return {"from": a["id"], "to": b["id"], "port": "out",
                "from_side": "right", "to_side": "left"}

    edges = [
        e(bd, nen), e(nen, du_nen),
        e(du_nen, xu_huong_len), e(du_nen, xu_huong_xuong),
        e(xu_huong_len, mua), e(xu_huong_xuong, ban),
        e(mua, cho), e(ban, cho),
        e(cho, da_khop), e(cho, vung_tan),
        e(da_khop, hoa_von), e(vung_tan, huy),
        # ── Ba cạnh QUAY LẠI, đều trỏ vào khối đã GHIM ──
        # Không xu hướng nào hợp -> khỏi vào lệnh, quay về đếm nến tiếp.
        e(du_nen, nen),
        # Lệnh chờ bị huỷ vì vùng tan -> bắt đầu lại chu kỳ.
        e(huy, nen),
        # Đã dời SL về hoà vốn -> lệnh tự lo phần còn lại, đi tìm đợt nén mới.
        e(hoa_von, nen),
    ]
    return {"schema": 1, "type": "strategy", "name": "Compress (mẫu)",
            "symbol": "XAUUSD", "timeframe": "M5", "steps": steps, "edges": edges}
