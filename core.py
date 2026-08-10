"""Cat_Studio — lõi.

Không phụ thuộc giao diện, không import tkinter/webview → test được mà không mở cửa sổ nào.
Mọi hiểu biết về ĐỊNH DẠNG FILE nằm ở đây; `api.py` chỉ chuyển JSON, `webui/` chỉ vẽ.

Ba tầng:  webui/ (vẽ)  →  api.py (cầu nối duy nhất)  →  core.py (lõi)

Xem `core.md` để hiểu VÌ SAO. File này giữ HÀNH VI.
"""
import json
import os
import re
import sys
import uuid

PHIEN_BAN = "0.1"

# ---------------------------------------------------------------------------
# Thư mục dữ liệu
# ---------------------------------------------------------------------------


def app_dir():
    """Thư mục cạnh file exe (bản đóng gói) hoặc cạnh mã nguồn (bản chạy thẳng).

    Dữ liệu người dùng (settings.json, templates/) sinh ra ở đây chứ không nằm trong
    repo — cài lại app không mất chiến lược đã lưu."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _duong(*phan):
    return os.path.join(app_dir(), *phan)


SETTINGS_DEFAULT = {
    "symbol": "XAUUSD",
    "timeframe": "M5",
    "accent": "#ffa657",
    "ui": {"panel_cao": 176, "panel_gap": False},
}

ACCENT_PRESETS = {
    "Cam": "#ffa657", "Xanh dương": "#4a9eff", "Lục": "#3fb950", "Tím": "#a371f7",
    "Đỏ": "#f85149", "Vàng": "#d29922", "Hồng": "#db61a2", "Xanh ngọc": "#39c5cf",
}


def load_settings():
    ra = json.loads(json.dumps(SETTINGS_DEFAULT))
    try:
        with open(_duong("settings.json"), encoding="utf-8") as f:
            ra.update(json.load(f) or {})
    except Exception:
        pass
    return ra


def save_settings(s):
    try:
        with open(_duong("settings.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return s


# ---------------------------------------------------------------------------
# Khung thời gian & ký hiệu
# ---------------------------------------------------------------------------

# Thứ tự CÓ Ý NGHĨA: giao diện xổ ra theo đúng thứ tự này, và "khung lớn hơn" so được
# bằng chỉ số trong danh sách.
TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
TF_PHUT = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240,
           "D1": 1440, "W1": 10080, "MN1": 43200}

MA_METHODS = {"SMA": "Trung bình đơn", "EMA": "Trung bình mũ",
              "SMMA": "Trung bình làm mượt", "LWMA": "Trung bình có trọng số"}


# ---------------------------------------------------------------------------
# LOẠI KHỐI
# ---------------------------------------------------------------------------

KIND_START = "start"     # điểm neo đánh số — không làm gì cả
KIND_LOOP = "loop"       # Vòng theo dõi — lặp theo mỗi nến mới
KIND_GROUP = "group"     # Nhóm hành động chạy 1 lượt
KIND_ACTION = "action"   # HĐ lẻ — chỉ loại này được làm CỔNG rẽ nhánh

KIND_LABELS = {
    KIND_START: "Bắt đầu",
    KIND_LOOP: "Vòng theo dõi",
    KIND_GROUP: "Nhóm 1 lần",
    KIND_ACTION: "HĐ lẻ",
}

DEFAULT_MAX_NEN = 1000


def is_start_step(s):
    return isinstance(s, dict) and s.get("kind") == KIND_START


def is_loop_step(s):
    return isinstance(s, dict) and s.get("kind") == KIND_LOOP


def is_group_step(s):
    return isinstance(s, dict) and s.get("kind") == KIND_GROUP


def has_actions(s):
    return is_loop_step(s) or is_group_step(s)


# ---------------------------------------------------------------------------
# HÀNH ĐỘNG
# ---------------------------------------------------------------------------

# BA ĐỘNG TỪ: ĐỌC — TẠO — SỬA. Đủ để diễn tả mọi chiến lược, không thừa cái nào.
#
#   check_cond  ĐỌC  thị trường + tài khoản rồi quyết đi nhánh nào  (cũng là CỔNG rẽ nhánh)
#   vao_lenh    TẠO  một vị thế mới, kèm SL/TP ban đầu
#   sua_lenh    SỬA  một lệnh ĐÃ CÓ: dời SL, dời TP, hoà vốn, trailing, đóng, huỷ chờ
#
# Mấy khái niệm tưởng là hành động riêng thật ra tan hết vào ba cái trên:
#   "cầu dao"  -> toán hạng tài khoản/thời gian trong check_cond (so_lenh_mo, drawdown_pt, gio)
#   "cổng"     -> chính là check_cond đứng đầu một nhánh
#   "kích hoạt"-> không phải hành động mà là LOẠI KHỐI "Vòng theo dõi" (chờ tới khi thoả)
#   "thoát"    -> chế độ "đóng" / "huỷ chờ" của sua_lenh
CHECK_COND = "check_cond"
VAO_LENH = "vao_lenh"
SUA_LENH = "sua_lenh"
DAT_CO = "dat_co"

# `HANH_DONG_AN` chỉ lọc khỏi BẢNG CHỌN của giao diện — lõi vẫn hiểu và chạy đủ.
# Mở lại một hành động = bỏ đúng một chuỗi khỏi tập dưới đây, không viết lại gì.
ACTION_TYPES = [CHECK_COND, VAO_LENH, SUA_LENH, DAT_CO]
HANH_DONG_AN = {DAT_CO}

# Nhãn THUẦN CHỮ, không emoji: chúng hiện ở dropdown "Loại:" của hộp thoại, và giao
# diện tự vẽ icon nét theo `type` cho khớp phần còn lại.
ACTION_LABELS = {
    CHECK_COND: "Kiểm tra điều kiện",
    VAO_LENH: "Vào lệnh",
    SUA_LENH: "Sửa lệnh",
    DAT_CO: "Đặt cờ",
}

# Hành động QUYẾT ĐỊNH ĐƯỜNG ĐI: không khớp thì nhánh đang chạy chết tại đó.
BRANCH_TYPES = (CHECK_COND,)

# Hành động ĐẠT MỤC TIÊU: khớp là kết thúc SỚM cả Vòng theo dõi.
# Tách khỏi BRANCH_TYPES vì ngữ nghĩa ngược nhau — goal: khớp là XONG;
# branch: khớp mới được ĐI TIẾP.
GOAL_TYPES = ()


def hanh_dong_hien():
    return [t for t in ACTION_TYPES if t not in HANH_DONG_AN]


# ---- Toán hạng của "Kiểm tra điều kiện" -----------------------------------
# (key, nhãn, nhóm, tham số cần nhập)
# `tham_so` là những ô phụ hộp thoại phải hiện thêm khi chọn toán hạng đó.
TOAN_HANG = [
    ("close",          "Giá đóng cửa",            "Giá",        ["tf", "shift"]),
    ("open",           "Giá mở cửa",              "Giá",        ["tf", "shift"]),
    ("high",           "Giá cao nhất",            "Giá",        ["tf", "shift"]),
    ("low",            "Giá thấp nhất",           "Giá",        ["tf", "shift"]),
    ("bid",            "Giá Bid",                 "Giá",        []),
    ("ask",            "Giá Ask",                 "Giá",        []),
    ("spread",         "Spread (điểm)",           "Giá",        []),

    ("atr",            "ATR",                     "Chỉ báo",    ["tf", "period"]),
    ("atr_bps",        "ATR chuẩn hoá (bps)",     "Chỉ báo",    ["tf", "period"]),
    ("ma",             "Đường trung bình MA",     "Chỉ báo",    ["tf", "period", "method"]),
    ("donchian_tren",  "Donchian — biên trên",    "Chỉ báo",    ["tf", "period"]),
    ("donchian_duoi",  "Donchian — biên dưới",    "Chỉ báo",    ["tf", "period"]),
    ("volume_ma",      "Volume trung bình",       "Chỉ báo",    ["tf", "period"]),

    ("so_nen_nen",     "Số nến nén liên tiếp",    "Vùng nén",   []),
    ("dinh_vung",      "Đỉnh vùng",               "Vùng nén",   []),
    ("day_vung",       "Đáy vùng",                "Vùng nén",   []),
    ("rong_vung",      "Bề rộng vùng",            "Vùng nén",   []),
    ("rong_vung_atr",  "Bề rộng vùng ÷ ATR",      "Vùng nén",   []),
    ("atr_tb_vung",    "ATR trung bình của vùng", "Vùng nén",   []),

    ("co_vi_the",      "Đang có vị thế",          "Trạng thái", []),
    ("co_lenh_cho",    "Đang có lệnh chờ",        "Trạng thái", []),
    ("lenh_da_khop",   "Lệnh chờ vừa khớp",       "Trạng thái", []),
    ("co",             "Cờ",                      "Trạng thái", ["ten_co"]),

    ("so_lenh_mo",     "Số lệnh đang mở",         "Tài khoản",  []),
    ("lai_lo_R",       "Lãi/lỗ hiện tại (× R)",   "Tài khoản",  []),
    ("drawdown_pt",    "Drawdown (%)",            "Tài khoản",  []),
    ("so_lenh_hom_nay", "Số lệnh hôm nay",        "Tài khoản",  []),

    ("gio",            "Giờ (0–23)",              "Thời gian",  []),
    ("thu",            "Thứ (2–8)",               "Thời gian",  []),
    ("nen_moi",        "Có nến mới",              "Thời gian",  ["tf"]),
]

TOAN_HANG_KEYS = [k for k, _, _, _ in TOAN_HANG]
TOAN_HANG_LABELS = {k: n for k, n, _, _ in TOAN_HANG}
TOAN_HANG_NHOM = {k: g for k, _, g, _ in TOAN_HANG}
TOAN_HANG_THAMSO = {k: p for k, _, _, p in TOAN_HANG}

PHEP_SO = {
    "<": "nhỏ hơn", "<=": "nhỏ hơn hoặc bằng",
    ">": "lớn hơn", ">=": "lớn hơn hoặc bằng",
    "==": "bằng", "!=": "khác",
    "cat_len": "cắt lên", "cat_xuong": "cắt xuống",
    "trong_khoang": "trong khoảng",
}

# ---- Cách tính một khoảng cách giá -----------------------------------------
# Dùng chung cho SL/TP/đệm vào lệnh. Không có đơn vị "pip" hay "đô" nào — mọi khoảng
# cách là bội của ATR hoặc của R, đúng hợp đồng chuẩn hoá của Compress EA: cùng một
# con số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.
CACH_TINH = {
    "theo_ATR": "× ATR",
    "theo_R": "× R (rủi ro)",
    "theo_bien_vung": "mép vùng đối diện",
    "theo_pt": "% giá vào",
    "theo_gia": "giá tuyệt đối",
}

HUONG = {"mua": "Mua", "ban": "Bán"}
LOAI_LENH = {"market": "Thị trường", "stop": "Chờ Stop", "limit": "Chờ Limit"}

# ---- Chế độ của "Sửa lệnh" -------------------------------------------------
# Một hành động, nhiều chế độ — thay vì bảy hành động gần giống nhau. Tất cả đều tác
# động lên lệnh ĐÃ CÓ, không cái nào tạo ra lệnh mới.
SUA_CHE_DO = {
    "doi_sl": "Dời Stop Loss",
    "doi_tp": "Dời Take Profit",
    "hoa_von": "Dời SL về hoà vốn",
    "trailing": "Trailing Stop",
    "dong_mot_phan": "Đóng một phần",
    "dong_han": "Đóng hẳn",
    "huy_cho": "Huỷ lệnh chờ",
}
# Chế độ nào cần ô "cách tính + giá trị", chế độ nào không.
SUA_CAN_GIA = ("doi_sl", "doi_tp", "trailing")
SUA_CAN_PHAN_TRAM = ("dong_mot_phan",)


# ---------------------------------------------------------------------------
# Định danh khối
# ---------------------------------------------------------------------------


def new_step_id():
    """ID bền cho một khối.

    Đồ thị cần định danh KHÔNG ĐỔI khi khối bị kéo sang chỗ khác hay đổi tên:
    dùng số thứ tự thì kéo-thả một cái là mọi đường nối trỏ sai, dùng tên thì đổi
    tên một cái là gãy."""
    return "s" + uuid.uuid4().hex[:8]


def ensure_step_ids(steps):
    """Cấp id cho khối chưa có, và dọn id trùng. Sửa TẠI CHỖ rồi trả lại chính nó."""
    da_dung = set()
    for st in steps or []:
        if not isinstance(st, dict):
            continue
        sid = st.get("id")
        if not sid or sid in da_dung:
            sid = new_step_id()
            st["id"] = sid
        da_dung.add(sid)
    return steps


# ---------------------------------------------------------------------------
# Dựng khối
# ---------------------------------------------------------------------------


def make_start_step(name="Bắt đầu"):
    """Khối BẮT ĐẦU — thuần điểm neo đánh số, không làm gì cả.

    Đúng MỘT khối mỗi sơ đồ, tạo sẵn khi mở canvas trắng, không xoá được và không
    nhận đường nối đi vào. Nhờ nó `flow_entry` không bao giờ trả None, nên một vòng
    lặp nối ngược lên trên không thể "nuốt" mất điểm bắt đầu (xem core.md §3.3)."""
    return {"kind": KIND_START, "id": new_step_id(), "name": name}


def make_loop_step(name="Vòng theo dõi"):
    return {"kind": KIND_LOOP, "id": new_step_id(), "name": name, "actions": [],
            "loop_start_index": 0, "max_nen": DEFAULT_MAX_NEN, "tf": ""}


def make_group_step(name="Nhóm mới"):
    # Cố ý KHÔNG có max_nen/loop_start_index — Nhóm chạy đúng một lượt.
    return {"kind": KIND_GROUP, "id": new_step_id(), "name": name, "actions": []}


def make_action_step(action):
    """Bọc một hành động thành khối HĐ lẻ.

    GIỮ LẠI `action["id"]` nếu có: nếu không thì mỗi lần sửa hành động là khối đổi id
    và mọi đường nối trỏ vào nó gãy hết."""
    st = dict(action or {})
    st["kind"] = KIND_ACTION
    st["id"] = st.get("id") or new_step_id()
    return st


def step_title(step):
    ten = (step.get("name") or "").strip()
    if ten:
        return ten
    if is_start_step(step):
        return "Bắt đầu"
    if is_loop_step(step):
        return "Vòng theo dõi"
    if is_group_step(step):
        return "Nhóm"
    return ACTION_LABELS.get(step.get("type"), "Hành động")


# ---------------------------------------------------------------------------
# Mô tả hành động — CHỮ HIỆN TRÊN HỘP DO ĐÂY SINH
# ---------------------------------------------------------------------------
# Giao diện không tự ghép câu: nếu nó ghép thì sớm muộn nó mô tả khác với thứ lõi
# thực sự hiểu, và người dùng tin vào cái sai.


def _so(x):
    """Bỏ đuôi .0 cho gọn: 2.0 -> '2', 1.5 -> '1.5'."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    return str(int(f)) if f == int(f) else str(f)


def khoang_display(k):
    """Một khoảng cách giá: {"tinh": "theo_ATR", "value": 1.5} -> '1.5 × ATR'."""
    if not isinstance(k, dict):
        return "?"
    return f"{_so(k.get('value'))} {CACH_TINH.get(k.get('tinh'), '?')}"


def toan_hang_display(o):
    """{"ten": "atr", "tf": "M5", "period": 14} -> 'ATR(M5, 14)'."""
    if not isinstance(o, dict):
        return str(o)
    ten = o.get("ten") or ""
    nhan = TOAN_HANG_LABELS.get(ten, ten or "?")
    phan = []
    for k in TOAN_HANG_THAMSO.get(ten, []):
        v = o.get(k)
        if v in (None, ""):
            continue
        phan.append(f"nến[{v}]" if k == "shift" else str(v))
    return f"{nhan}({', '.join(phan)})" if phan else nhan


def _la_toan_hang_dung_sai(ten):
    """Toán hạng vốn đã là đúng/sai — hộp thoại ẩn luôn ô vế phải cho chúng."""
    return ten in ("co_vi_the", "co_lenh_cho", "lenh_da_khop", "co", "nen_moi")


def ve_phai_display(c):
    """Vế phải: hoặc một con số, hoặc một toán hạng khác."""
    if (c or {}).get("phai_loai") == "toan_hang":
        return toan_hang_display(c.get("phai") or {})
    v = (c or {}).get("phai")
    if (c or {}).get("phep") == "trong_khoang":
        return f"{_so((c or {}).get('phai'))} … {_so((c or {}).get('phai2'))}"
    return _so(v)


def cond_display(c):
    """Một dòng điều kiện: 'ATR chuẩn hoá (bps)(M5, 14) nhỏ hơn 7'.

    Toán hạng vốn đã đúng/sai thì viết thẳng, không ghép phép so — "Đang có vị thế
    bằng 1" là câu không ai đọc được."""
    trai = (c or {}).get("trai") or {}
    if _la_toan_hang_dung_sai(trai.get("ten")):
        return ("KHÔNG " if (c or {}).get("dao") else "") + toan_hang_display(trai)
    return (f"{toan_hang_display(trai)} "
            f"{PHEP_SO.get((c or {}).get('phep'), '?')} "
            f"{ve_phai_display(c)}")


def action_display(a):
    t = (a or {}).get("type")
    ten = ((a or {}).get("name") or "").strip()
    dau = f"{ten}: " if ten else ""

    if t == CHECK_COND:
        ds = a.get("conditions") or []
        if not ds:
            return dau + "Kiểm tra điều kiện — CHƯA có điều kiện nào"
        if len(ds) == 1:
            return dau + cond_display(ds[0])
        return dau + " VÀ ".join(cond_display(c) for c in ds)

    if t == VAO_LENH:
        p = [f"Vào lệnh {HUONG.get(a.get('huong'), '?')} "
             f"{LOAI_LENH.get(a.get('loai'), '?')}", f"{_so(a.get('lot'))} lot"]
        if a.get("loai") in ("stop", "limit") and a.get("dem"):
            p.append(f"đệm {khoang_display(a['dem'])}")
        if a.get("sl"):
            p.append(f"SL {khoang_display(a['sl'])}")
        if a.get("tp"):
            p.append(f"TP {khoang_display(a['tp'])}")
        return dau + "  ·  ".join(p)

    if t == SUA_LENH:
        cd = a.get("che_do")
        s = SUA_CHE_DO.get(cd, "?")
        if cd in SUA_CAN_GIA and a.get("khoang"):
            s += f" {khoang_display(a['khoang'])}"
        if cd in SUA_CAN_PHAN_TRAM:
            s += f" {_so(a.get('phan_tram'))}%"
        if cd == "hoa_von" and a.get("khoang"):
            s += f" (kích hoạt khi lãi {khoang_display(a['khoang'])})"
        return dau + s

    if t == DAT_CO:
        return (dau + f"Đặt cờ \"{a.get('ten_co') or '?'}\" = "
                      f"{'bật' if a.get('gia_tri') else 'tắt'}")

    return dau + ACTION_LABELS.get(t, str(t))


def step_display(step):
    if is_start_step(step):
        return "◆ Bắt đầu   ·  điểm neo đánh số"
    if is_loop_step(step):
        n = len(step.get("actions") or [])
        return (f"↻ {step_title(step)}   ·  {n} hành động  ·  "
                f"tối đa {step.get('max_nen', DEFAULT_MAX_NEN)} nến")
    if is_group_step(step):
        n = len(step.get("actions") or [])
        return f"▤ {step_title(step)}   ·  {n} hành động  ·  chạy 1 lần"
    return f"⚡ {action_display(step)}   (chạy 1 lần)"


# ---------------------------------------------------------------------------
# ĐỒ THỊ
# ---------------------------------------------------------------------------

# Trần số bước chạy trong 1 chiến lược. Đồ thị CHO PHÉP nối ngược lên trên (vòng lặp),
# nên phải có chốt chặn — nếu không, một cái nối sai là chạy mãi không dừng.
MAX_PROCESS_STEPS = 10000


def _khoa_nhanh(step):
    """Khoá sắp thứ tự ưu tiên nhánh: CẠNH QUAY LẠI xuống cuối, rồi TRÊN→DƯỚI, TRÁI→PHẢI.

    Vì sao lấy vị trí trên canvas chứ không phải thứ tự tạo dây: thứ tự tạo dây là thứ
    VÔ HÌNH — kéo khối cách mấy cũng không đổi, nên người dùng không có cách nào biết
    nhánh nào được thử trước. Vị trí thì nhìn thấy, và nhãn A/B trên huy hiệu đổi ngay
    lúc thả chuột, nên ưu tiên không bao giờ là thứ ngầm.
    Chốt bằng `id` để hai khối chồng khít nhau vẫn ra thứ tự cố định.

    Nhánh trỏ vào khối ĐÃ GHIM luôn xếp CUỐI, bất kể nó nằm đâu trên canvas. Đó là
    cạnh quay lại — nghĩa của nó là "không nhánh nào khớp thì quay về trên", tức đúng
    vai nhánh mặc định. Mà khối quay về gần như luôn nằm phía TRÊN (đầu vòng lặp), nên
    xếp theo vị trí sẽ đẩy nó lên đầu và mọi nhánh dưới nó không bao giờ được thử."""
    pos = step.get("pos") or []
    try:
        x, y = float(pos[0]), float(pos[1])
    except (TypeError, ValueError, IndexError):
        x = y = 0.0
    return (1 if step.get("ghim") else 0, y, x, str(step.get("id") or ""))


def flow_map(steps, edges):
    """(bảng_tra_id, kế_tiếp) với `kế_tiếp[id] = [id, ...]` THEO ĐÚNG THỨ TỰ ƯU TIÊN.

    ĐÂY LÀ NGUỒN SỰ THẬT DUY NHẤT VỀ THỨ TỰ NHÁNH — cả bộ đánh số lẫn bộ chạy đều
    chỉ lấy thứ tự từ đây, nên huy hiệu không thể ghi A trước B mà máy lại thử B trước."""
    theo_id = {s.get("id"): s for s in (steps or [])
               if isinstance(s, dict) and s.get("id")}
    ke = {}
    for e in (edges or []):
        if not isinstance(e, dict) or (e.get("port") or "out") != "out":
            continue
        a, b = e.get("from"), e.get("to")
        if a in theo_id and b in theo_id:
            ds = ke.setdefault(a, [])
            if b not in ds:      # nối hai lần cùng một cặp vẫn chỉ là một nhánh
                ds.append(b)
    for ds in ke.values():
        ds.sort(key=lambda sid: _khoa_nhanh(theo_id[sid]))
    return theo_id, ke


def is_branch_gate(step):
    """Khối này có phải CỔNG của một nhánh không.

    Cổng = khối HĐ lẻ mang đúng một hành động `check_cond`.

    Cố ý KHÔNG cho Nhóm hay Vòng theo dõi làm cổng: ở điểm rẽ các nhánh được thử lần
    lượt, nên nhánh trượt phải LÙI LẠI ĐƯỢC — mà lùi chỉ an toàn khi nhánh đó chưa kịp
    làm gì ra thị trường. Một khối `check_cond` chỉ ĐỌC dữ liệu nên lùi bao nhiêu lần
    cũng vô hại; một Nhóm thì không hứa được điều đó (nó có thể đã đặt lệnh rồi mới
    kiểm tra, và lệnh đó không rút lại được)."""
    return (isinstance(step, dict) and step.get("kind") == KIND_ACTION
            and step.get("type") == CHECK_COND)


def _khoa_dieu_kien(conds):
    """Dấu vân tay của một bộ điều kiện, để phát hiện hai cổng giống hệt nhau.
    Sắp khoá trước khi ghép: hai dict cùng nội dung khác thứ tự khoá vẫn phải ra cùng
    một chuỗi, nếu không cảnh báo 'hai nhánh trùng điều kiện' sẽ bỏ sót."""
    return json.dumps([cond_display(c) for c in (conds or [])], ensure_ascii=False)


def flow_entry(steps, edges):
    """Khối BẮT ĐẦU của sơ đồ.

    Ưu tiên tuyệt đối cho khối `kind == "start"`: nó là điểm neo, KHÔNG nhận đường vào,
    nên nó luôn hợp lệ làm điểm bắt đầu. Nhờ vậy một vòng lặp nối ngược lên trên không
    thể làm mọi khối đều có đường vào — lỗi khiến TOÀN BỘ huy hiệu biến thành "–".

    Không có khối `start` (file cũ / chép tay) thì quay về luật cũ: khối đầu tiên trong
    danh sách mà không có đường nối đi vào. Không tìm được thì trả None và
    `validate_flow_graph` báo lỗi thay vì đoán bừa."""
    ds = [s for s in (steps or []) if isinstance(s, dict) and s.get("id")]
    if not ds:
        return None
    for s in ds:
        if is_start_step(s):
            return s["id"]
    co_vao = {e.get("to") for e in (edges or [])
              if isinstance(e, dict) and (e.get("port") or "out") == "out"}
    for s in ds:
        if s["id"] not in co_vao:
            return s["id"]
    return None


# Sentinel: "khối này không phải điểm rẽ". Phải khác `None`, vì None đã có nghĩa
# riêng rồi — "là điểm rẽ nhưng các nhánh không chụm lại ở đâu cả".
_KHONG_RE = object()


def _chu_nhanh(k):
    """0 -> 'A', 1 -> 'B'. Quá 26 nhánh từ một khối là chuyện không xảy ra thật,
    nhưng vẫn phải ra chuỗi phân biệt được."""
    return chr(65 + k) if k < 26 else f"({k + 1})"


def diem_gop(cur, ke, da_nhan=None):
    """Khối GẦN NHẤT mà MỌI nhánh ĐI TỚI của `cur` đều dẫn tới, hoặc None.

    Nhờ nó mà số quay về mức trên cùng sau khi hết nhánh: 4 rẽ ra 4A/4B, hai nhánh
    chụm lại thì khối sau đó là "5" chứ không phải "4A.4". Không nhánh nào gặp nhau
    -> None, nghĩa là mỗi nhánh tự kết thúc và đơn giản là KHÔNG CÓ số 5 nào cả.

    `da_nhan` = những khối ĐÃ được đánh nhãn, tức nằm phía SAU LƯNG phép duyệt.
    Phải truyền vào, nếu không đồ thị có vòng lặp sẽ cho kết quả vô nghĩa: đi vòng một
    lượt là "tới được" lại chính các nhánh vừa xuất phát, nên phép giao nhận nhầm một
    ĐẦU NHÁNH làm điểm gộp — khi đó nhánh A vừa mang nhãn "3A" vừa mang nhãn "4".
    Đúng lỗi làm sơ đồ mẫu Compress đánh số lệch (một nhánh "4", nhánh kia "3B").

    Hai việc `da_nhan` làm:
      · nhánh nào có ĐẦU đã mang nhãn thì bỏ qua hẳn — đó là cạnh quay lại, nó không
        đi tới đâu cả mà là về chỗ cũ;
      · phép loang dừng lại ở mọi khối đã có nhãn, không đi xuyên qua chúng.
    """
    da_nhan = da_nhan or set()
    nhanh = [uv for uv in (ke.get(cur) or []) if uv not in da_nhan]
    if len(nhanh) < 2:
        return None

    def toi_duoc(bd):
        tham, hang = set(), [bd]
        while hang:
            n = hang.pop(0)
            if n in tham or n in da_nhan:
                continue
            tham.add(n)
            hang.extend(ke.get(n) or [])
        return tham

    chung = None
    for uv in nhanh:
        t = toi_duoc(uv)
        chung = t if chung is None else (chung & t)
    chung = (chung or set()) - {cur}
    if not chung:
        return None
    tham, hang = set(), list(nhanh)
    while hang:
        n = hang.pop(0)
        if n in tham or n in da_nhan:
            continue
        tham.add(n)
        if n in chung:
            return n
        hang.extend(ke.get(n) or [])
    return None


def flow_order(steps, edges):
    """Nhãn hiện ở góc khối -> {id: "1" | "4" | "4A" | "4A.2" | "4A.2B.1"}.

    LUẬT: SỐ = đi được bao xa, CHỮ = đi nhánh nào.
    Chữ dính ngay sau số của khối RẼ (khối 4 rẽ ra thì cổng hai nhánh là 4A, 4B), dấu
    chấm ngăn giữa nhãn nhánh và số bước bên trong nhánh (4A.1, 4A.2).

    Ngữ pháp: các nhóm ngăn bởi dấu chấm, mỗi nhóm = SỐ rồi tới các CHỮ (có thể không
    có). "4A.2B" tách thành "4A" | "2B" — chữ không bao giờ mở đầu một nhóm, số luôn
    đứng ngay sau dấu chấm, nên tách được bằng máy, không nhập nhằng.

    GẶP LẠI KHỐI ĐÃ CÓ NHÃN — ba trường hợp KHÁC HẲN nhau (Auto_Clicker gộp cả ba
    thành một cờ `loop` duy nhất và báo động sai; xem core.md §3.3 Bẫy 1):

      1. Khối đã GHIM  -> vòng lặp CÓ CHỦ Ý. Giữ nguyên nhãn cũ, ghi lại là cạnh
                          quay lại, KHÔNG cảnh báo gì. Đây là "số cũ vẫn hợp lệ".
      2. Khối nằm trên ĐƯỜNG ĐANG ĐI (ancestor) -> vòng lặp ngoài ý muốn -> cảnh báo
                          kèm gợi ý ghim khối đó lại.
      3. Còn lại -> hai nhánh chụm vào cùng một khối mà `diem_gop` không nhận ra
                          (nhánh chụm không đều). KHÔNG phải vòng lặp.

    Trả về: {"order", "unreachable", "entry", "quay_lai", "vong_ho", "lech_nhanh"}
    """
    theo_id, ke = flow_map(steps, edges)
    bat_dau = flow_entry(steps, edges)
    nhan = {}
    duong = []          # ngăn xếp các khối ĐANG MỞ trên đường đi hiện tại
    quay_lai = []       # [(từ, tới)] cạnh quay lại hợp lệ — tới khối đã ghim
    vong_ho = []        # [(từ, tới)] vòng lặp chưa ghim
    lech_nhanh = []     # [id] khối bị hai nhánh cùng với tới

    def gap_lai(dich, tu):
        if theo_id.get(dich, {}).get("ghim"):
            if (tu, dich) not in quay_lai:
                quay_lai.append((tu, dich))
        elif dich in duong:
            if (tu, dich) not in vong_ho:
                vong_ho.append((tu, dich))
        elif dich not in lech_nhanh:
            lech_nhanh.append(dich)

    def chuoi(tu, cur, tien_to, i, dung_tai):
        """Đánh số một chuỗi; khối đầu mang nhãn f"{tien_to}{i}", rồi +1 dần.
        Dừng khi tới `dung_tai` (điểm gộp — để dành cho mức trên) hoặc hết đường."""
        them = 0
        try:
            for _ in range(MAX_PROCESS_STEPS):
                if cur is None or cur not in theo_id or cur == dung_tai:
                    return
                if cur in nhan:
                    gap_lai(cur, tu)
                    return
                nhan[cur] = f"{tien_to}{i}"
                duong.append(cur)
                them += 1
                gop = re_nhanh(cur, f"{tien_to}{i}", dung_tai)
                if gop is _KHONG_RE:
                    ds = ke.get(cur) or []
                    tu, cur, i = cur, (ds[0] if ds else None), i + 1
                    continue
                if gop is None or gop == dung_tai:
                    return
                tu, cur, i = cur, gop, i + 1
        finally:
            for _ in range(them):
                duong.pop()

    def re_nhanh(cur, nhan_cur, dung_tai):
        """Nếu `cur` là điểm rẽ thì đánh số hết các nhánh của nó.

        Trả về ĐIỂM GỘP (có thể None), hoặc `_KHONG_RE` nếu đây không phải điểm rẽ.
        Điểm gộp phải tính MỘT LẦN ở đây rồi dùng lại — tính lại sau khi các nhánh đã
        có nhãn thì `da_nhan` đã khác và ra kết quả khác."""
        nhanh = ke.get(cur) or []
        if len(nhanh) < 2:
            return _KHONG_RE
        gop = diem_gop(cur, ke, set(nhan))
        for k, uv in enumerate(nhanh):
            dau_nhanh(cur, uv, nhan_cur + _chu_nhanh(k),
                      gop if gop is not None else dung_tai)
        return gop

    def dau_nhanh(tu, uv, nhan_nhanh, dung_tai):
        """Khối ĐẦU nhánh mang đúng nhãn nhánh ("4A" — chính là cái cổng), các khối
        sau nó mang "4A.1", "4A.2"… Cổng lại rẽ tiếp thì chữ nối thêm chữ ("4AA"),
        vẫn đúng ngữ pháp vì một nhóm cho phép nhiều chữ."""
        if uv is None or uv not in theo_id or uv == dung_tai:
            return
        if uv in nhan:
            gap_lai(uv, tu)
            return
        nhan[uv] = nhan_nhanh
        duong.append(uv)
        try:
            gop = re_nhanh(uv, nhan_nhanh, dung_tai)
            if gop is not _KHONG_RE:
                if gop is not None and gop != dung_tai:
                    chuoi(uv, gop, nhan_nhanh + ".", 1, dung_tai)
                return
            sau = ke.get(uv) or []
            if sau:
                chuoi(uv, sau[0], nhan_nhanh + ".", 1, dung_tai)
        finally:
            duong.pop()

    chuoi(None, bat_dau, "", 1, None)
    return {
        "order": nhan,
        "unreachable": [sid for sid in theo_id if sid not in nhan],
        "entry": bat_dau,
        "quay_lai": quay_lai,
        "vong_ho": vong_ho,
        "lech_nhanh": lech_nhanh,
        # Giữ khoá `loop` cho giao diện: giờ nó chỉ bật khi có vòng THẬT.
        "loop": bool(quay_lai or vong_ho),
    }


def canh_quay_lai(steps, edges):
    """Tập {(từ, tới)} các cạnh quay lại — giao diện vẽ nét đứt cho chúng."""
    return {tuple(c) for c in flow_order(steps, edges)["quay_lai"]}


# ---------------------------------------------------------------------------
# Soát lỗi
# ---------------------------------------------------------------------------


def _loi(ds, sev, sid, msg):
    ds.append({"severity": sev, "step": sid, "index": None, "message": msg})


def validate_flow_graph(steps, edges):
    """Soát riêng phần ĐỒ THỊ — lỗi ở mức nối dây, không phải ở mức một hành động."""
    ra = []
    ds = [s for s in (steps or []) if isinstance(s, dict) and s.get("id")]
    if not ds:
        return ra

    theo_id, ke = flow_map(steps, edges)
    kq = flow_order(steps, edges)
    nhan = kq["order"]

    def ten(sid):
        """Tên khối kèm NHÃN THẬT trên huy hiệu.

        Cố ý không dùng index trong danh sách: Auto_Clicker ghi f"Bước {i+1}" nên panel
        Vấn đề có thể nói "Bước 7" về một khối mà huy hiệu ghi "4A.2" (core.md §3.3)."""
        n = nhan.get(sid)
        return f'[{n}] "{step_title(theo_id[sid])}"' if n else f'"{step_title(theo_id[sid])}"'

    # ---- Khối trùng id ----
    # `flow_map` tra theo id nên hai khối cùng id thì một cái BIẾN MẤT khỏi sơ đồ:
    # không nhãn, không dấu vết. Nhìn canvas thấy đủ khối, chạy thì thiếu.
    dem = {}
    for s in ds:
        dem[s["id"]] = dem.get(s["id"], 0) + 1
    for sid, n in dem.items():
        if n > 1:
            _loi(ra, "error", sid,
                 f'Có {n} khối trùng id với nhau ({ten(sid)}) — chỉ MỘT cái được chạy, '
                 f"những cái còn lại biến mất khỏi sơ đồ mà không báo gì. "
                 f"Hãy xoá bớt rồi tạo lại.")

    # ---- Khối Bắt đầu ----
    bd = [s for s in ds if is_start_step(s)]
    if len(bd) > 1:
        _loi(ra, "error", bd[1]["id"],
             f"Sơ đồ có {len(bd)} khối Bắt đầu — chỉ được đúng một. "
             f"Hãy xoá bớt, giữ lại một cái.")
    if not bd:
        _loi(ra, "warning", None,
             "Sơ đồ chưa có khối Bắt đầu. Thêm một cái để việc đánh số có điểm neo cố "
             "định — không có nó, một vòng lặp nối ngược lên trên có thể làm mất luôn "
             "điểm bắt đầu và mọi khối đều mất số.")
    for s in bd:
        vao = [e for e in (edges or [])
               if isinstance(e, dict) and e.get("to") == s["id"]]
        if vao:
            _loi(ra, "error", s["id"],
                 f"Khối Bắt đầu có {len(vao)} đường nối ĐI VÀO. Nó là điểm neo, "
                 f"không bao giờ được chạy tới từ chỗ khác. Hãy gỡ mấy đường đó.")

    # ---- Đường nối trỏ về chính nó ----
    for e in (edges or []):
        if isinstance(e, dict) and e.get("from") and e.get("from") == e.get("to") \
                and e["from"] in theo_id:
            _loi(ra, "error", e["from"],
                 f"{ten(e['from'])} có đường nối trỏ về CHÍNH NÓ — chạy tới đây là quay "
                 f"lại chính mình mãi mãi. Muốn lặp thì nối về một khối phía trước và "
                 f"ghim số khối đó.")

    # ---- Cổng khớp rồi mà phía sau trống ----
    for sid, st in theo_id.items():
        if is_branch_gate(st) and not ke.get(sid):
            _loi(ra, "warning", sid,
                 f"{ten(sid)} khớp điều kiện rồi thì không có gì phía sau — chiến lược "
                 f"kết thúc ngay tại đó. Nối tiếp một khối vào nếu bạn muốn nhánh này "
                 f"làm gì đó.")

    # ---- Luật rẽ nhánh ----
    # Nhiều đường ra KHÔNG phải lỗi, nhưng phải quyết định được đi đường nào. Ở điểm rẽ
    # các nhánh được thử lần lượt trên->dưới, nên mỗi nhánh phải mở đầu bằng một CỔNG,
    # trừ tối đa MỘT nhánh mặc định — và nhánh mặc định luôn khớp nên bắt buộc xếp CUỐI.
    for sid, nhanh in ke.items():
        if len(nhanh) < 2 or sid not in theo_id:
            continue
        # Cạnh QUAY LẠI (trỏ vào khối đã ghim) không cần cổng và luôn được thử cuối —
        # nghĩa của nó vốn đã là "không nhánh nào khớp thì quay về trên", tức đúng vai
        # nhánh mặc định. Bắt nó phải có cổng là bắt viết lại điều kiện phủ định của
        # tất cả các nhánh trên, thừa và dễ sai.
        quay = [uv for uv in nhanh if theo_id[uv].get("ghim")]
        thang = [uv for uv in nhanh if uv not in quay]
        khong_cong = [uv for uv in thang if not is_branch_gate(theo_id[uv])]
        if len(khong_cong) > 1:
            ds_ten = ", ".join(ten(uv) for uv in khong_cong)
            _loi(ra, "error", sid,
                 f"{ten(sid)} rẽ {len(nhanh)} nhánh nhưng có {len(khong_cong)} nhánh "
                 f"không có cổng kiểm tra ({ds_ten}) — chạy tới đây không biết chọn "
                 f'nhánh nào. Mỗi nhánh phải bắt đầu bằng khối HĐ lẻ '
                 f'"{ACTION_LABELS[CHECK_COND]}", nhiều nhất một nhánh được để trống '
                 f"làm nhánh mặc định.")
        elif khong_cong and khong_cong[0] != thang[-1]:
            _loi(ra, "error", sid,
                 f"{ten(khong_cong[0])} là nhánh mặc định (không có cổng kiểm tra) "
                 f"nhưng không nằm dưới cùng của {ten(sid)} — nhánh mặc định luôn khớp "
                 f"nên các nhánh xếp dưới nó không bao giờ chạy tới. Hãy kéo nó xuống "
                 f"thấp nhất.")
        elif not khong_cong and not quay and not is_loop_step(theo_id[sid]):
            # Vòng theo dõi được miễn: không nhánh nào khớp thì nó chờ nến sau, chứ
            # không phải chiến lược kết thúc. Đó chính là việc của một vòng theo dõi.
            _loi(ra, "warning", sid,
                 f"{ten(sid)} rẽ {len(nhanh)} nhánh và nhánh nào cũng có điều kiện — "
                 f"không khớp nhánh nào thì chiến lược kết thúc tại đây. Muốn luôn có "
                 f"lối đi thì thêm một nhánh không cổng xếp dưới cùng, hoặc nối ngược "
                 f"về một khối đã ghim số.")

        # Hai cổng cùng điều kiện y hệt: cái dưới không bao giờ tới lượt.
        da_thay = {}
        for uv in nhanh:
            if not is_branch_gate(theo_id[uv]):
                continue
            khoa = _khoa_dieu_kien(theo_id[uv].get("conditions"))
            if khoa in da_thay:
                _loi(ra, "warning", uv,
                     f"{ten(uv)} có điều kiện giống hệt {ten(da_thay[khoa])} xếp trên — "
                     f"khớp thì nhánh trên thắng, nhánh này không bao giờ chạy.")
            else:
                da_thay[khoa] = uv

    # ---- Điểm bắt đầu ----
    if kq["entry"] is None:
        _loi(ra, "error", None,
             "Không tìm được khối bắt đầu — mọi khối đều có đường nối đi vào. Hãy thêm "
             "một khối Bắt đầu, hoặc gỡ bớt một đường nối.")

    # ---- Vòng lặp CHƯA ghim ----
    for tu, toi in kq["vong_ho"]:
        _loi(ra, "warning", toi,
             f"{ten(tu)} nối ngược về {ten(toi)} tạo thành VÒNG LẶP, nhưng {ten(toi)} "
             f'chưa được ghim số. Bấm chuột phải vào nó → "Ghim số" để xác nhận đây là '
             f"vòng lặp cố ý — số của nó sẽ được giữ nguyên và cảnh báo này biến mất. "
             f"Vòng chỉ dừng khi chạy đủ {MAX_PROCESS_STEPS} bước.")

    # ---- Nhánh chụm không đều ----
    # KHÔNG gọi là vòng lặp. Đây là lúc `diem_gop` không tìm ra khối chung cho MỌI
    # nhánh (vd 3 nhánh mà chỉ 2 nhánh gặp nhau), nên số không quay về được mức trên.
    for sid in kq["lech_nhanh"]:
        _loi(ra, "warning", sid,
             f"{ten(sid)} được nhiều nhánh cùng dẫn tới, nhưng KHÔNG PHẢI mọi nhánh của "
             f"điểm rẽ đều dẫn tới đây — nên số không quay về được mức trên cùng và khối "
             f"này mang nhãn của nhánh chạm tới nó trước. Nối nốt các nhánh còn lại vào "
             f"đây nếu bạn muốn nó là điểm gộp thật.")

    # ---- Khối không bao giờ chạy tới ----
    for sid in kq["unreachable"]:
        _loi(ra, "warning", sid,
             f"{ten(sid)} không bao giờ chạy tới — chưa có đường nối dẫn vào từ khối "
             f"bắt đầu.")

    return ra


# ---- soát HÀNH ĐỘNG -------------------------------------------------------


def _soat_toan_hang(o, cho, err):
    if not isinstance(o, dict) or not o.get("ten"):
        err(f"{cho} chưa chọn toán hạng.")
        return
    ten = o.get("ten")
    if ten not in TOAN_HANG_KEYS:
        err(f'{cho} dùng toán hạng "{ten}" không còn được hỗ trợ.')
        return
    for k in TOAN_HANG_THAMSO[ten]:
        if k == "tf" and o.get("tf") not in TIMEFRAMES:
            err(f"{cho} ({TOAN_HANG_LABELS[ten]}) chưa chọn khung thời gian.")
        if k == "period":
            try:
                if int(o.get("period")) <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                err(f"{cho} ({TOAN_HANG_LABELS[ten]}) cần chu kỳ là số nguyên dương.")
        if k == "method" and o.get("method") not in MA_METHODS:
            err(f"{cho} ({TOAN_HANG_LABELS[ten]}) chưa chọn kiểu trung bình.")
        if k == "ten_co" and not (o.get("ten_co") or "").strip():
            err(f"{cho} (Cờ) chưa nhập tên cờ.")
        if k == "shift":
            try:
                if int(o.get("shift", 1)) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                err(f"{cho} ({TOAN_HANG_LABELS[ten]}) cần chỉ số nến ≥ 0. "
                    f"Dùng 1 để đọc nến đã đóng — nến 0 còn đang chạy nên tín hiệu sẽ "
                    f"vẽ lại.")


def _soat_khoang(k, cho, err, bat_buoc=True):
    """Soát một khoảng cách giá {"tinh", "value"}."""
    if not k:
        if bat_buoc:
            err(f"{cho} chưa được đặt.")
        return
    if not isinstance(k, dict) or k.get("tinh") not in CACH_TINH:
        err(f"{cho} chưa chọn cách tính.")
        return
    try:
        v = float(k.get("value"))
    except (TypeError, ValueError):
        err(f"{cho} cần giá trị là một con số.")
        return
    if k["tinh"] != "theo_gia" and v <= 0:
        err(f"{cho} cần giá trị lớn hơn 0.")


def validate_actions(actions, err):
    """`err(msg, i)` được gọi cho từng lỗi. Tách khỏi phần đồ thị vì đây là lỗi ở mức
    một hành động, không phải ở mức nối dây."""
    for i, a in enumerate(actions or []):
        def e(m, _i=i):
            err(m, _i)
        t = (a or {}).get("type")
        if t not in ACTION_TYPES:
            e(f'Loại hành động "{t}" không còn được hỗ trợ — xoá dòng này hoặc thay '
              f"bằng loại khác.")
            continue

        if t == CHECK_COND:
            ds = a.get("conditions") or []
            if not ds:
                e("\"Kiểm tra điều kiện\" chưa có điều kiện nào — nó sẽ luôn khớp.")
            for k, c in enumerate(ds):
                cho = f"Điều kiện {k + 1}"
                _soat_toan_hang((c or {}).get("trai"), f"{cho} — vế trái", e)
                # Toán hạng đúng/sai không có vế phải — nó tự nó đã là một mệnh đề.
                if _la_toan_hang_dung_sai(((c or {}).get("trai") or {}).get("ten")):
                    continue
                if (c or {}).get("phep") not in PHEP_SO:
                    e(f"{cho} chưa chọn phép so sánh.")
                if (c or {}).get("phai_loai") == "toan_hang":
                    _soat_toan_hang(c.get("phai"), f"{cho} — vế phải", e)
                else:
                    try:
                        float((c or {}).get("phai"))
                    except (TypeError, ValueError):
                        e(f"{cho} — vế phải phải là một con số.")
                    if (c or {}).get("phep") == "trong_khoang":
                        try:
                            if float(c.get("phai2")) <= float(c.get("phai")):
                                e(f"{cho} — cận trên phải lớn hơn cận dưới.")
                        except (TypeError, ValueError):
                            e(f"{cho} — phép \"trong khoảng\" cần hai con số.")

        elif t == VAO_LENH:
            if a.get("huong") not in HUONG:
                e("\"Vào lệnh\" chưa chọn hướng Mua/Bán.")
            if a.get("loai") not in LOAI_LENH:
                e("\"Vào lệnh\" chưa chọn loại lệnh.")
            try:
                if float(a.get("lot")) <= 0:
                    e("\"Vào lệnh\" cần khối lượng lớn hơn 0.")
            except (TypeError, ValueError):
                e("\"Vào lệnh\" cần khối lượng là một con số.")
            if a.get("loai") in ("stop", "limit") and not a.get("dem"):
                e("Lệnh chờ cần khoảng đệm — đặt ngay tại giá hiện tại thì nó khớp "
                  "luôn, không còn là lệnh chờ nữa.")
            _soat_khoang(a.get("dem"), "Khoảng đệm", e, bat_buoc=False)
            _soat_khoang(a.get("sl"), "Stop Loss ban đầu", e, bat_buoc=False)
            _soat_khoang(a.get("tp"), "Take Profit ban đầu", e, bat_buoc=False)
            if not a.get("sl"):
                e("\"Vào lệnh\" chưa đặt Stop Loss ban đầu — vào lệnh không có SL là "
                  "để ngỏ toàn bộ tài khoản. Đặt SL ở đây, còn khối \"Sửa lệnh\" phía "
                  "sau chỉ để DỜI nó.")

        elif t == SUA_LENH:
            cd = a.get("che_do")
            if cd not in SUA_CHE_DO:
                e("\"Sửa lệnh\" chưa chọn chế độ.")
            else:
                if cd in SUA_CAN_GIA or cd == "hoa_von":
                    _soat_khoang(a.get("khoang"), SUA_CHE_DO[cd], e,
                                 bat_buoc=(cd in SUA_CAN_GIA))
                if cd in SUA_CAN_PHAN_TRAM:
                    try:
                        pt = float(a.get("phan_tram"))
                        if not 0 < pt < 100:
                            e("Đóng một phần cần tỉ lệ trong khoảng 0–100%. "
                              "Muốn đóng hết thì chọn chế độ \"Đóng hẳn\".")
                    except (TypeError, ValueError):
                        e("Đóng một phần cần tỉ lệ là một con số.")

        elif t == DAT_CO:
            if not (a.get("ten_co") or "").strip():
                e("\"Đặt cờ\" chưa có tên cờ.")


def validate_process(doc):
    """Soát cả tài liệu. Thông báo dùng NHÃN trên huy hiệu, không dùng index."""
    steps = doc.get("steps") or []
    edges = doc.get("edges")
    if edges is None:
        edges = default_edges(steps)
    ra = list(validate_flow_graph(steps, edges))
    nhan = flow_order(steps, edges)["order"]
    _, ke = flow_map(steps, edges)

    for st in steps:
        if not isinstance(st, dict):
            continue
        sid = st.get("id")
        n = nhan.get(sid)
        dau = f"[{n}] " if n else ""

        def err(m, i=None, _sid=sid, _dau=dau):
            ra.append({"severity": "error", "step": _sid, "index": i,
                       "message": f"{_dau}{m}"})

        if has_actions(st):
            # Vòng theo dõi RỖNG mà có từ 2 nhánh trở ra là mẫu "chờ tới khi": mỗi nến
            # mới thử lại các cổng phía sau, chưa cổng nào khớp thì chờ tiếp. Nó cố ý
            # không làm gì cả — báo "sẽ không làm gì" ở đây là báo nhầm.
            cho_doi = is_loop_step(st) and len(ke.get(sid) or []) >= 2
            if not (st.get("actions") or []) and not cho_doi:
                ra.append({"severity": "warning", "step": sid, "index": None,
                           "message": f'{dau}"{step_title(st)}" chưa có hành động nào — '
                                      f"chạy tới đây sẽ không làm gì cả."})
            validate_actions(st.get("actions"), err)
        elif st.get("kind") == KIND_ACTION:
            validate_actions([st], lambda m, i=None: err(m))

        if is_loop_step(st):
            try:
                if int(st.get("max_nen", DEFAULT_MAX_NEN)) <= 0:
                    err("Số nến tối đa phải lớn hơn 0.")
            except (TypeError, ValueError):
                err("Số nến tối đa phải là số nguyên.")
    return ra


# ---------------------------------------------------------------------------
# Đường nối
# ---------------------------------------------------------------------------


def default_edges(steps):
    """Chuỗi thẳng 1 → 2 → 3…

    Nhờ hàm này mà "không có đường nối" và "nối thành chuỗi thẳng" là MỘT — file cũ
    (không có khoá `edges`) mở ra vẫn ra đúng sơ đồ nó vẫn chạy, không phải di cư gì."""
    ds = [s for s in (steps or []) if isinstance(s, dict) and s.get("id")]
    return [{"from": a["id"], "to": b["id"], "port": "out"} for a, b in zip(ds, ds[1:])]


def clean_edges(edges, steps):
    """Bỏ đường nối trỏ tới khối không còn tồn tại, và bỏ trùng.

    KHÔNG tự ý sửa ý người dùng thành thứ khác — chỉ vứt cái đã vô nghĩa."""
    co = {s.get("id") for s in (steps or []) if isinstance(s, dict)}
    ra, thay = [], set()
    for e in edges or []:
        if not isinstance(e, dict):
            continue
        a, b = e.get("from"), e.get("to")
        if a not in co or b not in co:
            continue
        khoa = (a, b, e.get("port") or "out")
        if khoa in thay:
            continue
        thay.add(khoa)
        moi = {"from": a, "to": b, "port": e.get("port") or "out"}
        # Cạnh nào của hộp thì đường nối cắm vào — thuần thị giác, nhưng PHẢI lưu,
        # nếu không mở lại file là sơ đồ tự vẽ khác đi so với lúc người dùng sắp.
        for k in ("from_side", "to_side"):
            if e.get(k):
                moi[k] = str(e[k])
        ra.append(moi)
    return ra


# ---------------------------------------------------------------------------
# Chuẩn hoá & tài liệu
# ---------------------------------------------------------------------------

_KHOA_CHUNG = ("id", "name", "pos", "ghim")


def _giu_chung(nguon, dich):
    """Chuyển các khoá dùng chung từ dict gốc sang dict đã chuẩn hoá.

    `normalize_step` dựng lại từng khối bằng danh sách khoá cố định (cố ý — để file rác
    không lọt vào). Nhưng thế thì mấy khoá này bị rơi mất: `id` là định danh nút,
    `pos` là chỗ người dùng đã kéo nút tới, `ghim` là cờ ghim số."""
    if nguon.get("id"):
        dich["id"] = nguon["id"]
    if nguon.get("name"):
        dich["name"] = str(nguon["name"])
    if nguon.get("ghim"):
        dich["ghim"] = True
    pos = nguon.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        try:
            dich["pos"] = [float(pos[0]), float(pos[1])]
        except (TypeError, ValueError):
            pass
    return dich


def normalize_action(a):
    if not isinstance(a, dict):
        return None
    t = a.get("type")
    if t not in ACTION_TYPES:
        return None
    ra = {"type": t}
    if (a.get("name") or "").strip():
        ra["name"] = a["name"].strip()
    if a.get("id"):
        ra["id"] = a["id"]

    if t == CHECK_COND:
        ds = []
        for c in a.get("conditions") or []:
            if not isinstance(c, dict):
                continue
            m = {"trai": dict(c.get("trai") or {}), "phep": c.get("phep") or "<",
                 "phai_loai": c.get("phai_loai") or "so"}
            m["phai"] = dict(c["phai"]) if m["phai_loai"] == "toan_hang" \
                and isinstance(c.get("phai"), dict) else c.get("phai")
            if c.get("phai2") is not None:
                m["phai2"] = c["phai2"]
            if c.get("dao"):
                m["dao"] = True
            ds.append(m)
        ra["conditions"] = ds
    elif t == VAO_LENH:
        ra.update({"huong": a.get("huong") or "mua", "loai": a.get("loai") or "stop",
                   "lot": a.get("lot", 0.01)})
        for k in ("dem", "sl", "tp"):
            if isinstance(a.get(k), dict) and a[k].get("tinh"):
                ra[k] = {"tinh": a[k]["tinh"], "value": a[k].get("value", 0)}
    elif t == SUA_LENH:
        ra["che_do"] = a.get("che_do") or "doi_sl"
        if isinstance(a.get("khoang"), dict) and a["khoang"].get("tinh"):
            ra["khoang"] = {"tinh": a["khoang"]["tinh"],
                            "value": a["khoang"].get("value", 0)}
        if ra["che_do"] in SUA_CAN_PHAN_TRAM:
            ra["phan_tram"] = a.get("phan_tram", 50)
        if a.get("muc_tieu") in ("vi_the", "lenh_cho"):
            ra["muc_tieu"] = a["muc_tieu"]
    elif t == DAT_CO:
        ra.update({"ten_co": (a.get("ten_co") or "").strip(),
                   "gia_tri": bool(a.get("gia_tri", True))})
    return ra


def normalize_step(s):
    if not isinstance(s, dict):
        return None
    kind = s.get("kind")

    if kind == KIND_START:
        return _giu_chung(s, {"kind": KIND_START})

    if kind == KIND_LOOP:
        acts = [x for x in (normalize_action(a) for a in s.get("actions") or []) if x]
        try:
            mn = max(1, int(s.get("max_nen", DEFAULT_MAX_NEN)))
        except (TypeError, ValueError):
            mn = DEFAULT_MAX_NEN
        try:
            ls = max(0, min(len(acts), int(s.get("loop_start_index", 0))))
        except (TypeError, ValueError):
            ls = 0
        ra = {"kind": KIND_LOOP, "actions": acts, "loop_start_index": ls, "max_nen": mn}
        if s.get("tf") in TIMEFRAMES:
            ra["tf"] = s["tf"]
        return _giu_chung(s, ra)

    if kind == KIND_GROUP:
        acts = [x for x in (normalize_action(a) for a in s.get("actions") or []) if x]
        return _giu_chung(s, {"kind": KIND_GROUP, "actions": acts})

    a = normalize_action(s)
    if a is None:
        return None
    a["kind"] = KIND_ACTION
    return _giu_chung(s, a)


def normalize_process(doc):
    steps = [x for x in (normalize_step(s) for s in (doc or {}).get("steps") or []) if x]
    ensure_step_ids(steps)
    edges = (doc or {}).get("edges")
    edges = default_edges(steps) if edges is None else clean_edges(edges, steps)
    tf = (doc or {}).get("timeframe")
    return {
        "schema": 1,
        "type": "strategy",
        "name": ((doc or {}).get("name") or "").strip() or "Chiến lược 1",
        "symbol": ((doc or {}).get("symbol") or "").strip() or "XAUUSD",
        "timeframe": tf if tf in TIMEFRAMES else "M5",
        "steps": steps,
        "edges": edges,
    }


def new_process():
    """Sơ đồ mới — CÓ SẴN khối Bắt đầu.

    Không mở ra canvas trắng trơn: khối Bắt đầu là điểm neo đánh số, thiếu nó thì khối
    đầu tiên người dùng thả ra sẽ tự nhận số 1 rồi đổi số ngay khi họ thả khối thứ hai
    lên phía trên nó."""
    bd = make_start_step()
    bd["pos"] = [80.0, 300.0]
    s = load_settings()
    return {"schema": 1, "type": "strategy", "name": "Chiến lược 1",
            "symbol": s.get("symbol", "XAUUSD"), "timeframe": s.get("timeframe", "M5"),
            "steps": [bd], "edges": []}


def clone_steps(steps):
    """Nhân bản: id MỚI cho từng khối + bảng tra cũ→mới để nối lại dây.

    Không remap là dây của bản sao trỏ về BẢN GỐC."""
    moi, tra = [], {}
    for s in steps or []:
        st = normalize_step(s)
        if not st:
            continue
        cu = st.get("id")
        st["id"] = new_step_id()
        # Cờ ghim KHÔNG chép sang bản sao: hai khối cùng ghim là hai điểm quay lại,
        # gần như chắc chắn không phải ý người dùng khi họ chỉ bấm Ctrl+D.
        st.pop("ghim", None)
        if cu:
            tra[cu] = st["id"]
        moi.append(st)
    return moi, tra


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

TEMPLATE_KINDS = {"strategy": "Chiến lược", "loop": "Vòng theo dõi", "group": "Nhóm"}


def _thu_muc_tpl(kind):
    d = _duong("templates", kind)
    os.makedirs(d, exist_ok=True)
    return d


def _ten_an_toan(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (name or "").strip()) or "khong_ten"


def list_templates(kind="strategy"):
    try:
        return sorted(f[:-5] for f in os.listdir(_thu_muc_tpl(kind))
                      if f.endswith(".json"))
    except Exception:
        return []


def save_template(kind, name, data):
    p = os.path.join(_thu_muc_tpl(kind), _ten_an_toan(name) + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def load_template(kind, name):
    p = os.path.join(_thu_muc_tpl(kind), _ten_an_toan(name) + ".json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def delete_template(kind, name):
    p = os.path.join(_thu_muc_tpl(kind), _ten_an_toan(name) + ".json")
    if os.path.exists(p):
        os.remove(p)
        return True
    return False
