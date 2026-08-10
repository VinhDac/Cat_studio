"""Cat_Studio — lõi.

Không phụ thuộc giao diện, không import tkinter/webview → test được mà không mở cửa sổ nào.
Mọi hiểu biết về ĐỊNH DẠNG FILE nằm ở đây; `api.py` chỉ chuyển JSON, `webui/` chỉ vẽ.

Ba tầng:  webui/ (vẽ)  →  api.py (cầu nối duy nhất)  →  core.py (lõi)

Xem `core.md` để hiểu VÌ SAO. File này giữ HÀNH VI.
"""
import json
import uuid

import kho
import luu_tru

PHIEN_BAN = "0.2"

# ---------------------------------------------------------------------------
# Thư mục dữ liệu
# ---------------------------------------------------------------------------


# Đường dẫn và đọc/ghi file nằm HẾT ở `luu_tru.py` — đây chỉ là lối tắt cho code cũ.
app_dir = luu_tru.thu_muc_app
load_settings = luu_tru.doc_cai_dat
save_settings = luu_tru.ghi_cai_dat

SETTINGS_DEFAULT = luu_tru.CAI_DAT_MAC_DINH

ACCENT_PRESETS = {
    "Cam": "#ffa657", "Xanh dương": "#4a9eff", "Lục": "#3fb950", "Tím": "#a371f7",
    "Đỏ": "#f85149", "Vàng": "#d29922", "Hồng": "#db61a2", "Xanh ngọc": "#39c5cf",
}


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

# HAI loại khối, không hơn.
#
# Từng có thêm "Vòng theo dõi" (lặp mỗi nến) và "Nhóm 1 lần" (gộp nhiều hành động).
# Bỏ cả hai, vì cả hai đều thừa:
#
#   · Vòng theo dõi — CẢ SƠ ĐỒ vốn đã là một vòng lặp: nó chạy lại từ khối Bắt đầu ở
#     mỗi nến mới, đúng như `OnTick` của MQL5 chạy lại từ đầu mỗi tick. "Chờ tới khi"
#     không cần vẽ: không cổng nào khớp thì hết lượt, nến sau tự chạy lại.
#   · Nhóm — cấu trúc của một chiến lược đến từ TÁCH TRÁCH NHIỆM, không từ lồng hộp.
#     Gộp nhóm chỉ đẻ thêm câu hỏi "nhóm có phải một đơn vị chạy không".
KIND_START = "start"     # điểm neo đánh số — mỗi nến chạy lại từ đây
KIND_ACTION = "action"   # đúng một hành động

KIND_LABELS = {
    KIND_START: "Bắt đầu",
    KIND_ACTION: "Khối",
}


def is_start_step(s):
    return isinstance(s, dict) and s.get("kind") == KIND_START


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

ACTION_TYPES = [CHECK_COND, VAO_LENH, SUA_LENH]

# Nhãn THUẦN CHỮ, không emoji: chúng hiện ở dropdown "Loại:" của hộp thoại, và giao
# diện tự vẽ icon nét theo `type` cho khớp phần còn lại.
ACTION_LABELS = {
    CHECK_COND: "Kiểm tra điều kiện",
    VAO_LENH: "Vào lệnh",
    SUA_LENH: "Sửa lệnh",
}

# ---------------------------------------------------------------------------
# HAI SƠ ĐỒ trong một chiến lược
# ---------------------------------------------------------------------------
#
#   ENTRY   — con trỏ đi SĂN. Chạy lại từ khối Bắt đầu ở mỗi nến. Có thể SINH một lệnh.
#   MANAGE  — chạy MỘT LƯỢT CHO MỖI LỆNH đang sống, cũng từ đầu, cũng mỗi nến.
#
# Thứ tự trong một nến:  cập nhật dữ liệu → MANAGE (từng lệnh) → ENTRY.
# Manage TRƯỚC Entry, đúng `OnTick` của D_02: CheckPendingActivation → ManageBreakEven
# → rồi mới tới phần quyết định. Chạy ngược lại thì lệnh vừa sinh bị quản lý ngay
# trong chính nến đẻ ra nó.
#
# Manage KHÔNG giữ con trỏ giữa các nến: nó tính lại từ trạng thái quan sát được, y
# như D_02 làm mỗi tick. Nhờ vậy mấy câu guard kiểu `if(sl >= entry) continue` không
# còn nằm trong code mà HIỆN RA THÀNH CỔNG trên sơ đồ.
TAB_ENTRY = "entry"
TAB_MANAGE = "manage"
TABS = [TAB_ENTRY, TAB_MANAGE]
TAB_LABELS = {TAB_ENTRY: "Entry", TAB_MANAGE: "Manage"}

# Entry chỉ TẠO, Manage chỉ SỬA. Một câu, và soát tĩnh được.
ACTION_TABS = {
    CHECK_COND: (TAB_ENTRY, TAB_MANAGE),
    VAO_LENH: (TAB_ENTRY,),
    SUA_LENH: (TAB_MANAGE,),
}


def hanh_dong_cua_tab(tab):
    return [t for t in ACTION_TYPES if tab in ACTION_TABS[t]]

# Hành động QUYẾT ĐỊNH ĐƯỜNG ĐI: không khớp thì nhánh đang chạy chết tại đó.
BRANCH_TYPES = (CHECK_COND,)

# ---- Toán hạng của "Kiểm tra điều kiện" -----------------------------------
# KHÔNG khai ở đây nữa: danh sách do `kho/` gom từ các module con, mỗi module khai
# phần của mình. Nhờ vậy thêm một chiến lược mới là thêm MỘT file vào `kho/`, không
# phải sờ vào `core.py` — và hộp thoại "Kho" có sẵn dữ liệu để bày ra.
TOAN_HANG = kho.TOAN_HANG
TOAN_HANG_KEYS = kho.TOAN_HANG_KEYS
NHOM_LENH_NAY = kho.NHOM_LENH_NAY
TOAN_HANG_LABELS = {t["key"]: t["nhan"] for t in TOAN_HANG}
TOAN_HANG_NHOM = {t["key"]: t["nhom"] for t in TOAN_HANG}
TOAN_HANG_THAMSO = {t["key"]: t["tham_so"] for t in TOAN_HANG}

# KÝ HIỆU, không phải chữ. Một cổng của Compress mang 4–5 điều kiện; viết "lớn hơn
# hoặc bằng" thì mỗi dòng dài gấp đôi và mắt phải đọc chữ thay vì liếc thấy quan hệ.
PHEP_SO = {
    "<": "<", "<=": "≤", ">": ">", ">=": "≥", "==": "=", "!=": "≠",
    "cat_len": "cắt lên ↗", "cat_xuong": "cắt xuống ↘",
    "trong_khoang": "trong khoảng",
}

# ---- Cách tính một khoảng cách giá -----------------------------------------
# Dùng chung cho SL/TP/đệm vào lệnh. Không có đơn vị "pip" hay "đô" nào — mọi khoảng
# cách là bội của ATR hoặc của R, đúng hợp đồng chuẩn hoá của Compress EA: cùng một
# con số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.
#
# HAI CHỮ "ATR" LÀ HAI THỨ KHÁC NHAU, và tách chúng ra là CÓ CHỦ Ý:
#   · ATR hiện tại        -> đo ĐỆM vào lệnh. Một tấm khiên mỏng ngoài mép vùng, chỉ
#                            cần đủ để lọc một nhịp phá giả.
#   · ATR trung bình vùng -> đo RỦI RO (1R). Lấy mức nhiễu thật suốt cả cú nén, nên
#                            mỗi lệnh rủi ro một R tương đương, bất kể vùng rộng hẹp.
# Gộp làm một là mất đúng cái làm cho 1R nhất quán giữa các tín hiệu.
CACH_TINH = {
    "theo_ATR": "× ATR hiện tại",
    "theo_ATR_vung": "× ATR trung bình của vùng nén",
    "theo_R": "× R (rủi ro)",
    "theo_bien_vung": "mép vùng đối diện",
    "theo_pt": "% giá vào",
    "theo_gia": "giá tuyệt đối",
}

# ---- BẢNG THAM SỐ của một chiến lược ---------------------------------------
# Hợp đồng chuẩn hoá của D_02: mỗi con số liên quan tới giá phải mang MỘT trong mấy
# đơn vị bất biến — bps của giá, bội ATR, bội R, số nến. Không pip, không đô.
#
# Vì sao phải có bảng thay vì gõ số thẳng vào điều kiện: ngưỡng nén `7` xuất hiện ở
# CẢ HAI sơ đồ (Entry "còn nén không", Manage "nén đã tan chưa"). Gõ tay hai chỗ thì
# sửa một chỗ là cặp đó lệch nhau ÂM THẦM — chiến lược vào lệnh theo một ngưỡng và
# huỷ lệnh theo ngưỡng khác. Đặt tên cho nó thì chuyện đó không xảy ra được.
DON_VI = {
    "bps": "bps của giá", "nen": "nến", "× ATR": "× ATR hiện tại",
    "× ATR vùng": "× ATR trung bình vùng", "× R": "× R (rủi ro)",
    "lot": "lot", "lệnh": "lệnh", "%": "%",
}


def make_tham_so(ten, nhan, gia_tri, don_vi="", ghi_chu=""):
    return {"ten": ten, "nhan": nhan or ten, "gia_tri": gia_tri,
            "don_vi": don_vi, "ghi_chu": ghi_chu}


def normalize_tham_so(ds):
    """Chuẩn hoá bảng tham số; bỏ dòng không tên và dòng trùng tên."""
    ra, thay = [], set()
    for t in ds or []:
        if not isinstance(t, dict):
            continue
        ten = str(t.get("ten") or "").strip()
        if not ten or ten in thay:
            continue
        thay.add(ten)
        try:
            v = float(t.get("gia_tri"))
        except (TypeError, ValueError):
            v = 0.0
        ra.append(make_tham_so(ten, str(t.get("nhan") or "").strip(), v,
                               str(t.get("don_vi") or ""),
                               str(t.get("ghi_chu") or "")))
    return ra


# Nhãn NGẮN cho chữ trên hộp. Bản dài ("× ATR trung bình của vùng nén") đúng cho hộp
# thoại và cho tooltip, nhưng nhét lên hộp thì một dòng nuốt cả khối — mà nhìn hộp là
# phải hiểu ngay, không phải đọc một đoạn văn.
CACH_TINH_NGAN = {
    "theo_ATR": "× ATR",
    "theo_ATR_vung": "× ATR vùng",
    "theo_R": "× R",
    "theo_bien_vung": "mép vùng đối diện",
    "theo_pt": "%",
    "theo_gia": "giá",
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
#
# `hoa_von` KHÔNG có tham số: nó chỉ là "SL = giá vào". Mốc kích hoạt (lãi đủ mấy R)
# và câu hỏi "đã dời chưa" đều nằm ở CỔNG phía trước, chỗ nhìn thấy được — chứ không
# giấu trong hành động như `ManageBreakEven` của D_02 giấu ba dòng guard.
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


def make_start_step(name="Mỗi nến — chạy lại từ đây"):
    """Khối BẮT ĐẦU — không làm gì cả, nhưng nói ra một điều quan trọng.

    CẢ SƠ ĐỒ là một vòng lặp: nó chạy lại từ khối này ở MỖI NẾN MỚI. Nên "chờ tới khi"
    không phải vẽ — không cổng nào khớp thì hết lượt, nến sau tự chạy lại từ đây.

    Đúng MỘT khối mỗi sơ đồ, tạo sẵn khi mở canvas trắng, không xoá được và không nhận
    đường nối đi vào. Nhờ nó `flow_entry` không bao giờ trả None, nên một đường nối
    ngược lên trên không thể "nuốt" mất điểm bắt đầu (xem core.md §3.3)."""
    return {"kind": KIND_START, "id": new_step_id(), "name": name}


def make_action_step(action):
    """Bọc một hành động thành một khối.

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


def _thay_so(v, tham_so):
    """LUẬT DUY NHẤT: ở đâu chờ một con số, một CHUỖI nghĩa là tên tham số.

    Áp đều cho chu kỳ chỉ báo, khối lượng, ngưỡng so sánh, khoảng cách SL/TP. Một luật
    dễ nhớ hơn "chỗ này được, chỗ kia không"."""
    if isinstance(v, str):
        return (tham_so or {}).get(v)
    return v


def _so_hoac_ten(v, tham_so, hien_ten=True):
    """Chuỗi hiển thị cho một ô số. `hien_ten` bật thì ra `tên = giá trị`.

    Dùng KHOẢNG TRẮNG KHÔNG NGẮT quanh dấu `=`: chữ trên hộp giờ được xuống dòng, mà
    `so_vi_the_toi_da =` nằm cuối dòng còn `3` rơi xuống dòng sau thì đọc mất nghĩa.
    Cả cụm phải đi liền một khối."""
    if not isinstance(v, str):
        return _so(v)
    gt = (tham_so or {}).get(v)
    if not hien_ten:
        return _so(gt) if gt is not None else f"{v}=?"
    return f"{v} = {_so(gt) if gt is not None else '?'}"


def _thuong_hoa(s):
    """Thường hoá chữ cái đầu, TRỪ viết tắt: "SL của…" phải giữ nguyên, còn
    "Đang có lệnh chờ" thì hạ xuống để đọc trôi sau chữ KHÔNG."""
    if len(s) >= 2 and s[1].isupper():
        return s
    return s[:1].lower() + s[1:]


def khoang_display(k, tham_so=None):
    """Một khoảng cách giá: {"tinh": "theo_ATR", "value": 1.5} -> '1.5 × ATR hiện tại'.

    `value` có thể là một CHUỖI = tên tham số, khi đó hiện `tên (giá trị)`."""
    if not isinstance(k, dict):
        return "?"
    return f"{_so_hoac_ten(k.get('value'), tham_so)} {CACH_TINH.get(k.get('tinh'), '?')}"


def toan_hang_display(o, tham_so=None):
    """{"ten": "atr", "tf": "M5", "period": 14} -> 'ATR(M5, 14)'.

    Tham số của toán hạng (chu kỳ, khung TG) hiện GIÁ TRỊ chứ không hiện tên: chúng là
    "đọc chuỗi số nào", không phải cái mà người ta chỉnh khi tinh chỉnh chiến lược.
    Ngược lại NGƯỠNG ở vế phải thì hiện cả tên — đó mới là núm vặn."""
    if not isinstance(o, dict):
        return str(o)
    ten = o.get("ten") or ""
    nhan = TOAN_HANG_LABELS.get(ten, ten or "?")
    phan = []
    for k in TOAN_HANG_THAMSO.get(ten, []):
        v = o.get(k)
        if v in (None, ""):
            continue
        v = _so_hoac_ten(v, tham_so, hien_ten=False) if k in ("period", "shift") else str(v)
        phan.append(f"nến[{v}]" if k == "shift" else v)
    return f"{nhan}({', '.join(phan)})" if phan else nhan


TOAN_HANG_DUNG_SAI = tuple(t["key"] for t in TOAN_HANG if t.get("dung_sai"))


def _la_toan_hang_dung_sai(ten):
    """Toán hạng vốn đã là đúng/sai — hộp thoại ẩn luôn ô vế phải cho chúng."""
    return kho.la_dung_sai(ten)


def ve_phai_display(c, tham_so=None):
    """Vế phải: một con số, một THAM SỐ có tên, hoặc một toán hạng khác.

    Tham số hiện cả tên lẫn giá trị (`ngưỡng nén = 7`): tên nói ý nghĩa, số nói thực
    tế — thiếu một trong hai thì phải mở bảng tham số ra mới đọc nổi sơ đồ."""
    loai = (c or {}).get("phai_loai")
    if loai == "toan_hang":
        return toan_hang_display(c.get("phai") or {}, tham_so)
    if loai == "tham_so":
        return _so_hoac_ten(str((c or {}).get("phai") or ""), tham_so)
    if (c or {}).get("phep") == "trong_khoang":
        return f"{_so((c or {}).get('phai'))} … {_so((c or {}).get('phai2'))}"
    return _so((c or {}).get("phai"))


def cond_display(c, tham_so=None):
    """Một dòng điều kiện: 'ATR chuẩn hoá (bps)(M5, 14) nhỏ hơn 7'.

    Toán hạng vốn đã đúng/sai thì viết thẳng, không ghép phép so — "Đang có vị thế
    bằng 1" là câu không ai đọc được."""
    trai = (c or {}).get("trai") or {}
    if _la_toan_hang_dung_sai(trai.get("ten")):
        s = toan_hang_display(trai, tham_so)
        # Thường hoá chữ đầu sau "KHÔNG": nhãn toán hạng viết hoa ("Đang có lệnh chờ")
        # nên ghép thẳng ra "KHÔNG Đang có lệnh chờ" — đọc vấp.
        return ("KHÔNG " + _thuong_hoa(s)) if (c or {}).get("dao") else s
    return (f"{toan_hang_display(trai, tham_so)} "
            f"{PHEP_SO.get((c or {}).get('phep'), '?')} "
            f"{ve_phai_display(c, tham_so)}")


def action_display(a, tham_so=None):
    t = (a or {}).get("type")
    ten = ((a or {}).get("name") or "").strip()
    dau = f"{ten}: " if ten else ""

    if t == CHECK_COND:
        ds = a.get("conditions") or []
        if not ds:
            return dau + "Kiểm tra điều kiện — CHƯA có điều kiện nào"
        if len(ds) == 1:
            return dau + cond_display(ds[0], tham_so)
        return dau + " VÀ ".join(cond_display(c, tham_so) for c in ds)

    if t == VAO_LENH:
        p = [f"Vào lệnh {HUONG.get(a.get('huong'), '?')} "
             f"{LOAI_LENH.get(a.get('loai'), '?')}",
             f"{_so_hoac_ten(a.get('lot'), tham_so)} lot"]
        # Lệnh chờ LUÔN neo vào mép vùng nén thuận chiều (đỉnh cho Mua, đáy cho Bán) —
        # đó là chỗ duy nhất Compress EA đặt lệnh, nên không có tham số "neo vào đâu".
        # `dem` chỉ là khoảng đẩy ra NGOÀI mép đó.
        if a.get("loai") in ("stop", "limit") and a.get("dem"):
            p.append(f"đệm {khoang_display(a['dem'], tham_so)} ngoài mép vùng")
        if a.get("sl"):
            p.append(f"SL {khoang_display(a['sl'], tham_so)}")
        if a.get("tp"):
            p.append(f"TP {khoang_display(a['tp'], tham_so)}")
        return dau + "  ·  ".join(p)

    if t == SUA_LENH:
        cd = a.get("che_do")
        s = SUA_CHE_DO.get(cd, "?")
        if cd in SUA_CAN_GIA and a.get("khoang"):
            s += f" {khoang_display(a['khoang'], tham_so)}"
        if cd in SUA_CAN_PHAN_TRAM:
            s += f" {_so(a.get('phan_tram'))}%"
        return dau + s

    return dau + ACTION_LABELS.get(t, str(t))


def dong_khoi(a, tham_so=None):
    """Chữ trên HỘP — danh sách dòng NGẮN, mỗi trường một dòng.

    Khác `action_display` (một câu đầy đủ, dùng cho hộp thoại và tooltip): trên hộp,
    "Vào lệnh Mua Chờ Stop · lot = 0.01 lot · đệm dem_vao_lenh = 0.1 × ATR hiện tại
    ngoài mép vùng · SL …" là một câu chạy dài bốn dòng, đọc không ra. Tách mỗi trường
    một dòng thì mắt quét dọc, và với nhãn đơn vị ngắn thì dòng nào cũng vừa một hàng."""
    t = (a or {}).get("type")

    if t == CHECK_COND:
        ds = a.get("conditions") or []
        return [cond_display(c, tham_so) for c in ds] or ["chưa có điều kiện nào — luôn khớp"]

    def khoang(k):
        return (f"{_so_hoac_ten(k.get('value'), tham_so)} "
                f"{CACH_TINH_NGAN.get(k.get('tinh'), '?')}")

    if t == VAO_LENH:
        ds = [f"{HUONG.get(a.get('huong'), '?')} · {LOAI_LENH.get(a.get('loai'), '?')}"
              f" · {_so_hoac_ten(a.get('lot'), tham_so, hien_ten=False)} lot"]
        if a.get("loai") in ("stop", "limit") and a.get("dem"):
            ds.append(f"đệm {khoang(a['dem'])}")
        for k, nhan in (("sl", "SL"), ("tp", "TP")):
            if a.get(k):
                ds.append(f"{nhan} {khoang(a[k])}")
        return ds

    if t == SUA_LENH:
        cd = a.get("che_do")
        s_ = SUA_CHE_DO.get(cd, "?")
        if cd in SUA_CAN_GIA and a.get("khoang"):
            s_ += f" {khoang(a['khoang'])}"
        if cd in SUA_CAN_PHAN_TRAM:
            s_ += f" {_so_hoac_ten(a.get('phan_tram'), tham_so, hien_ten=False)}%"
        return [s_]

    return [action_display(a, tham_so)]


def step_display(step):
    if is_start_step(step):
        return "◆ Bắt đầu   ·  mỗi nến chạy lại từ đây"
    return f"⚡ {action_display(step)}"


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
        # CỐ Ý KHÔNG cảnh báo "nhánh nào cũng có điều kiện". Trước đây có, vì tưởng
        # không khớp nhánh nào là chiến lược chết đứng. Sai: cả sơ đồ là một vòng lặp
        # chạy lại ở mỗi nến, nên không khớp gì = HẾT LƯỢT, nến sau chạy lại từ đầu.
        # Đó là cách "chờ" được diễn tả, và nó là trường hợp thường gặp nhất.

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


def _soat_so(v, cho, err, ten_tham_so, duong=True, nguyen=False):
    """Một ô số: hoặc con số, hoặc tên tham số có trong bảng. Trả True nếu hợp lệ."""
    if isinstance(v, str):
        if v not in (ten_tham_so or ()):
            err(f"{cho} dùng tham số \"{v}\" không có trong bảng tham số của chiến lược.")
            return False
        return True
    try:
        f = float(v)
    except (TypeError, ValueError):
        err(f"{cho} cần một con số, hoặc tên một tham số.")
        return False
    if nguyen and f != int(f):
        err(f"{cho} cần số nguyên.")
        return False
    if duong and f <= 0:
        err(f"{cho} cần giá trị lớn hơn 0.")
        return False
    return True


def _soat_toan_hang(o, cho, err, tab=None, ten_tham_so=None):
    if not isinstance(o, dict) or not o.get("ten"):
        err(f"{cho} chưa chọn toán hạng.")
        return
    ten = o.get("ten")
    if ten not in TOAN_HANG_KEYS:
        err(f'{cho} dùng toán hạng "{ten}" không còn được hỗ trợ.')
        return
    # Lỗi này MQL5 không bao giờ bắt được: hỏi về "lệnh này" ở chỗ chưa có lệnh nào.
    if tab == TAB_ENTRY and TOAN_HANG_NHOM[ten] == NHOM_LENH_NAY:
        err(f'{cho} dùng "{TOAN_HANG_LABELS[ten]}" — toán hạng nhóm "{NHOM_LENH_NAY}" '
            f"chỉ có nghĩa ở sơ đồ Manage, nơi mỗi lượt chạy gắn với một lệnh cụ thể. "
            f"Ở Entry thì chưa có lệnh nào để nói tới.")
        return
    for k in TOAN_HANG_THAMSO[ten]:
        if k == "tf" and o.get("tf") not in TIMEFRAMES:
            err(f"{cho} ({TOAN_HANG_LABELS[ten]}) chưa chọn khung thời gian.")
        if k == "period":
            _soat_so(o.get("period"), f"{cho} ({TOAN_HANG_LABELS[ten]}) — chu kỳ",
                     err, ten_tham_so, duong=True, nguyen=True)
        if k == "method" and o.get("method") not in MA_METHODS:
            err(f"{cho} ({TOAN_HANG_LABELS[ten]}) chưa chọn kiểu trung bình.")
        if k == "shift":
            v = o.get("shift", 1)
            if isinstance(v, str):
                _soat_so(v, f"{cho} — chỉ số nến", err, ten_tham_so)
            else:
                try:
                    if int(v) < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    err(f"{cho} ({TOAN_HANG_LABELS[ten]}) cần chỉ số nến ≥ 0. Dùng 1 "
                        f"để đọc nến đã đóng — nến 0 còn đang chạy nên tín hiệu sẽ vẽ lại.")


def _soat_khoang(k, cho, err, bat_buoc=True, ten_tham_so=None):
    """Soát một khoảng cách giá {"tinh", "value"}. `value` có thể là tên tham số."""
    if not k:
        if bat_buoc:
            err(f"{cho} chưa được đặt.")
        return
    if not isinstance(k, dict) or k.get("tinh") not in CACH_TINH:
        err(f"{cho} chưa chọn cách tính.")
        return
    v = k.get("value")
    if isinstance(v, str):
        if v not in (ten_tham_so or ()):
            err(f"{cho} dùng tham số \"{v}\" không có trong bảng tham số.")
        return
    try:
        v = float(v)
    except (TypeError, ValueError):
        err(f"{cho} cần giá trị là một con số hoặc một tham số.")
        return
    if k["tinh"] != "theo_gia" and v <= 0:
        err(f"{cho} cần giá trị lớn hơn 0.")


def validate_actions(actions, err, tab=None, ten_tham_so=None):
    """`err(msg, i)` được gọi cho từng lỗi. Tách khỏi phần đồ thị vì đây là lỗi ở mức
    một hành động, không phải ở mức nối dây.

    `tab` = sơ đồ đang soát. Có nó thì bắt được hai loại lỗi mà MQL5 không bao giờ
    bắt: đặt lệnh trong sơ đồ Manage, và hỏi "lệnh này" trong sơ đồ Entry."""
    for i, a in enumerate(actions or []):
        def e(m, _i=i):
            err(m, _i)
        t = (a or {}).get("type")
        if t not in ACTION_TYPES:
            e(f'Loại hành động "{t}" không còn được hỗ trợ — xoá dòng này hoặc thay '
              f"bằng loại khác.")
            continue

        if tab and tab not in ACTION_TABS[t]:
            cho = ", ".join(TAB_LABELS[x] for x in ACTION_TABS[t])
            e(f'"{ACTION_LABELS[t]}" không dùng được ở sơ đồ {TAB_LABELS[tab]} — '
              f"nó chỉ thuộc về {cho}. Entry chỉ TẠO lệnh, Manage chỉ SỬA lệnh.")
            continue

        if t == CHECK_COND:
            ds = a.get("conditions") or []
            if not ds:
                e("\"Kiểm tra điều kiện\" chưa có điều kiện nào — nó sẽ luôn khớp.")
            for k, c in enumerate(ds):
                cho = f"Điều kiện {k + 1}"
                _soat_toan_hang((c or {}).get("trai"), f"{cho} — vế trái", e, tab,
                                ten_tham_so)
                # Toán hạng đúng/sai không có vế phải — nó tự nó đã là một mệnh đề.
                if _la_toan_hang_dung_sai(((c or {}).get("trai") or {}).get("ten")):
                    continue
                if (c or {}).get("phep") not in PHEP_SO:
                    e(f"{cho} chưa chọn phép so sánh.")
                if (c or {}).get("phai_loai") == "toan_hang":
                    _soat_toan_hang(c.get("phai"), f"{cho} — vế phải", e, tab,
                                    ten_tham_so)
                else:
                    _soat_so((c or {}).get("phai"), f"{cho} — vế phải", e,
                             ten_tham_so, duong=False)
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
            _soat_so(a.get("lot"), "\"Vào lệnh\" — khối lượng", e, ten_tham_so)
            if a.get("loai") in ("stop", "limit") and not a.get("dem"):
                e("Lệnh chờ cần khoảng đệm — đặt ngay tại giá hiện tại thì nó khớp "
                  "luôn, không còn là lệnh chờ nữa.")
            _soat_khoang(a.get("dem"), "Khoảng đệm", e, False, ten_tham_so)
            _soat_khoang(a.get("sl"), "Stop Loss ban đầu", e, False, ten_tham_so)
            _soat_khoang(a.get("tp"), "Take Profit ban đầu", e, False, ten_tham_so)
            if not a.get("sl"):
                e("\"Vào lệnh\" chưa đặt Stop Loss ban đầu — vào lệnh không có SL là "
                  "để ngỏ toàn bộ tài khoản. Đặt SL ở đây, còn khối \"Sửa lệnh\" phía "
                  "sau chỉ để DỜI nó.")

        elif t == SUA_LENH:
            cd = a.get("che_do")
            if cd not in SUA_CHE_DO:
                e("\"Sửa lệnh\" chưa chọn chế độ.")
            else:
                if cd in SUA_CAN_GIA:
                    _soat_khoang(a.get("khoang"), SUA_CHE_DO[cd], e, True, ten_tham_so)
                if cd in SUA_CAN_PHAN_TRAM:
                    try:
                        pt = float(a.get("phan_tram"))
                        if not 0 < pt < 100:
                            e("Đóng một phần cần tỉ lệ trong khoảng 0–100%. "
                              "Muốn đóng hết thì chọn chế độ \"Đóng hẳn\".")
                    except (TypeError, ValueError):
                        e("Đóng một phần cần tỉ lệ là một con số.")



def validate_so_do(steps, edges, tab, ten_tham_so=None):
    """Soát MỘT sơ đồ. Thông báo dùng NHÃN trên huy hiệu, không dùng index."""
    if edges is None:
        edges = default_edges(steps)
    ra = [dict(p, tab=tab) for p in validate_flow_graph(steps, edges)]
    nhan = flow_order(steps, edges)["order"]

    for st in steps or []:
        if not isinstance(st, dict) or is_start_step(st):
            continue
        sid = st.get("id")
        n = nhan.get(sid)
        dau = f"[{n}] " if n else ""

        def err(m, i=None, _sid=sid, _dau=dau):
            ra.append({"severity": "error", "step": _sid, "index": i,
                       "tab": tab, "message": f"{_dau}{m}"})

        validate_actions([st], lambda m, i=None: err(m), tab, ten_tham_so)
    return ra


def validate_process(doc):
    """Soát CẢ HAI sơ đồ. Mỗi vấn đề mang thêm khoá `tab` để giao diện biết chỗ.

    Cố ý soát cả hai chứ không chỉ tab đang mở: giấu lỗi của tab kia đi thì người dùng
    bấm ▶ Chạy mới biết, và không hiểu vì sao."""
    ra = []
    ten_ts = {t["ten"] for t in (doc or {}).get("tham_so") or []}
    for tab in TABS:
        g = (doc or {}).get(tab) or {}
        ra += validate_so_do(g.get("steps") or [], g.get("edges"), tab, ten_ts)

    # Tham số khai ra mà không khối nào dùng — không sai, nhưng là rác dễ gây hiểu nhầm
    # ("chỉnh số này chắc đổi hành vi"), nên nói ra.
    dung = _tham_so_dang_dung(doc)
    for t in (doc or {}).get("tham_so") or []:
        if t["ten"] not in dung:
            ra.append({"severity": "warning", "step": None, "index": None,
                       "tab": TAB_ENTRY,
                       "message": f'Tham số "{t["ten"]}" không khối nào dùng tới — '
                                  f"sửa nó sẽ không đổi gì cả."})
    return ra


def _tham_so_dang_dung(doc):
    """Tên tham số đang thật sự được khối nào đó tham chiếu."""
    ra = set()

    def them(v):
        if isinstance(v, str) and v:
            ra.add(v)

    def quet_khoang(k):
        if isinstance(k, dict):
            them(k.get("value"))

    def quet_toan_hang(o):
        if isinstance(o, dict):
            them(o.get("period"))
            them(o.get("shift"))

    for tab in TABS:
        for st in ((doc or {}).get(tab) or {}).get("steps") or []:
            if not isinstance(st, dict):
                continue
            for c in st.get("conditions") or []:
                quet_toan_hang((c or {}).get("trai"))
                if (c or {}).get("phai_loai") == "tham_so":
                    them(str(c.get("phai") or ""))
                elif (c or {}).get("phai_loai") == "toan_hang":
                    quet_toan_hang(c.get("phai"))
            for k in ("dem", "sl", "tp", "khoang"):
                quet_khoang(st.get(k))
            them(st.get("lot"))
    return ra


def bang_tham_so(doc):
    """{tên: giá trị} — dạng mọi hàm hiển thị cần."""
    return {t["ten"]: t["gia_tri"] for t in (doc or {}).get("tham_so") or []}


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
                   "lot": a.get("lot", 0.01)})   # có thể là tên tham số
        for k in ("dem", "sl", "tp"):
            if isinstance(a.get(k), dict) and a[k].get("tinh"):
                ra[k] = {"tinh": a[k]["tinh"], "value": a[k].get("value", 0)}
    elif t == SUA_LENH:
        ra["che_do"] = a.get("che_do") or "doi_sl"
        if ra["che_do"] in SUA_CAN_GIA and isinstance(a.get("khoang"), dict) \
                and a["khoang"].get("tinh"):
            ra["khoang"] = {"tinh": a["khoang"]["tinh"],
                            "value": a["khoang"].get("value", 0)}
        if ra["che_do"] in SUA_CAN_PHAN_TRAM:
            ra["phan_tram"] = a.get("phan_tram", 50)
    return ra


def normalize_step(s):
    if not isinstance(s, dict):
        return None
    if s.get("kind") == KIND_START:
        return _giu_chung(s, {"kind": KIND_START})
    a = normalize_action(s)
    if a is None:
        return None
    a["kind"] = KIND_ACTION
    return _giu_chung(s, a)


def _chuan_so_do(g):
    steps = [x for x in (normalize_step(s) for s in (g or {}).get("steps") or []) if x]
    ensure_step_ids(steps)
    edges = (g or {}).get("edges")
    edges = default_edges(steps) if edges is None else clean_edges(edges, steps)
    return {"steps": steps, "edges": edges}


def normalize_process(doc):
    doc = doc or {}
    # File schema 1 chỉ có MỘT sơ đồ ở gốc — nhận nó làm Entry. Rẻ, và mở lại được
    # mọi thứ đã lưu trước khi tách hai tab.
    if "steps" in doc and TAB_ENTRY not in doc:
        doc = dict(doc, entry={"steps": doc.get("steps"), "edges": doc.get("edges")})
    tf = doc.get("timeframe")
    ra = {
        "schema": 3,
        "type": "strategy",
        "name": (doc.get("name") or "").strip() or "Chiến lược 1",
        "symbol": (doc.get("symbol") or "").strip() or "XAUUSD",
        "timeframe": tf if tf in TIMEFRAMES else "M5",
        "tham_so": normalize_tham_so(doc.get("tham_so")),
    }
    for tab in TABS:
        ra[tab] = _chuan_so_do(doc.get(tab))
    return ra


def new_process():
    """Chiến lược mới — HAI sơ đồ, mỗi cái có sẵn khối Bắt đầu.

    Không mở ra canvas trắng trơn: khối Bắt đầu là điểm neo đánh số, thiếu nó thì khối
    đầu tiên người dùng thả ra sẽ tự nhận số 1 rồi đổi số ngay khi họ thả khối thứ hai
    lên phía trên nó."""
    s = load_settings()
    ra = {"schema": 3, "type": "strategy", "name": "Chiến lược 1",
          "symbol": s.get("symbol", "XAUUSD"), "timeframe": s.get("timeframe", "M5"),
          "tham_so": []}
    for tab, ten in ((TAB_ENTRY, "Mỗi nến — tìm tín hiệu vào lệnh"),
                     (TAB_MANAGE, "Mỗi nến · với TỪNG lệnh đang sống")):
        bd = make_start_step(ten)
        bd["pos"] = [80.0, 300.0]
        ra[tab] = {"steps": [bd], "edges": []}
    return ra


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

# CHỈ lưu được cả chiến lược, không lưu cụm khối rời.
#
# Từng có template riêng cho Vòng theo dõi và Nhóm. Bỏ: một template phải là thứ CHẠY
# ĐƯỢC. Cụm khối rời thì chưa biết nó nối vào đâu, mở ra là một mớ khối lạc không có
# đường vào — dán xong vẫn phải tự nối lại từ đầu.
TEMPLATE_KINDS = {"strategy": "Chiến lược"}


# Đọc/ghi uỷ quyền hết cho `luu_tru.py`. `kind` giữ lại cho code cũ nhưng chỉ còn
# một loại — mọi lời gọi đều là "strategy".
def list_templates(kind="strategy"):
    return luu_tru.liet_ke_chien_luoc()


def save_template(kind, name, data):
    return luu_tru.ghi_chien_luoc(name, data)


def load_template(kind, name):
    return luu_tru.doc_chien_luoc(name)


def delete_template(kind, name):
    return luu_tru.xoa_chien_luoc(name)
