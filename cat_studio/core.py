"""Cat_Studio — lõi.

Không phụ thuộc giao diện, không import tkinter/webview → test được mà không mở cửa sổ nào.
Mọi hiểu biết về ĐỊNH DẠNG FILE nằm ở đây; `api.py` chỉ chuyển JSON, `webui/` chỉ vẽ.

Ba tầng:  webui/ (vẽ)  →  api.py (cầu nối duy nhất)  →  core.py (lõi)

Xem `tai_lieu/core.md` để hiểu VÌ SAO. File này giữ HÀNH VI.
"""
import json
import uuid

from . import kho
from . import luu_tru

PHIEN_BAN = "0.2"

#: Phiên bản định dạng file. 4 = nhịp chạy chuyển từ `doc["timeframe"]` (một nhịp cho cả
#: tài liệu) sang khoá `nhip` trên chính khối Bắt đầu của TỪNG sơ đồ. `normalize_process`
#: đọc được cả file cũ, nên không cần script di cư riêng.
SCHEMA = 4

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
    # ĐÚNG/SAI là một PHÉP SO, không phải một ô tick riêng. Nhờ vậy mọi điều kiện có
    # cùng một hình dạng `[đại lượng] [phép] [lượng]` — hết ngoại lệ.
    "la_dung": "là ĐÚNG", "la_sai": "là SAI",
}
#: Phép nào KHÔNG có vế phải.
PHEP_KHONG_VE_PHAI = ("la_dung", "la_sai")
#: Phép nào dùng cho toán hạng đúng/sai (và CHỈ chúng).
PHEP_DUNG_SAI = ("la_dung", "la_sai")

#: PHÉP CŨ → mới. Ba phép đã bỏ:
#:   `trong_khoang` — `a ≤ x ≤ b` chính là HAI dòng, mà cổng vốn đã là AND.
#:   `cat_len` / `cat_xuong` — CÓ trong dropdown nhưng CHƯA CÀI: `bo_chay._so_sanh`
#:      chạy tới chúng là ném `LoiChay`, tức chọn từ menu rồi bấm chạy là backtest chết.
PHEP_CU = {"trong_khoang": ">=", "cat_len": ">", "cat_xuong": "<"}

# ---- ĐƠN VỊ — MỘT bảng cho cả app ------------------------------------------
#
# ⚠ Trước đây có HAI bảng cho cùng một ý: `DON_VI` (SL/TP/đệm) và `DON_VI`
# (điều kiện). Ba cặp trùng nhau gọi bằng sáu cái tên —
# `atr ≡ atr`, `pt ≡ pt`, `gia ≡ tho`. Đó là chắp vá, không phải
# thiết kế: cùng một khái niệm phải có cùng một tên ở mọi chỗ.
#
# Mọi khoảng cách là bội của ATR hoặc của R — KHÔNG pip, KHÔNG đô. Đó là hợp đồng
# chuẩn hoá của D_02: cùng một con số mang cùng một ý nghĩa trên vàng, forex, crypto.
#
# HAI CHỮ "ATR" LÀ HAI THỨ KHÁC NHAU, và tách chúng ra là CÓ CHỦ Ý:
#   · `atr`      = ATR nến vừa đóng    → đo ĐỆM. Tấm khiên mỏng ngoài mép zone.
#   · `atr_zone` = ATR trung bình zone → đo RỦI RO (1R). Lấy mức nhiễu thật suốt cú
#                  nén, nên mỗi lệnh rủi ro một R tương đương dù zone rộng hẹp.
# Gộp làm một là mất đúng cái làm cho 1R nhất quán giữa các tín hiệu.
#
# ⚠ `pt` ("% của giá") ĐÃ BỎ. Nó là `bps` chia 100 — hai cái tên cho đúng một phép
#   chuẩn hoá, mà bảng vốn từ có hai tên cho một thứ thì người dùng phải đoán xem chúng
#   khác nhau chỗ nào (không khác). Không file đã lưu nào dùng `pt`, nên không cần phép
#   chuyển: gặp `pt` thì soát tĩnh báo "chưa chọn cách tính" — nói to, hơn là âm thầm
#   nhân/chia 100 sau lưng.
DON_VI = {
    "gia": "giá tuyệt đối",
    "bps": "bps của giá",
    "atr": "× ATR",
    "atr_zone": "× ATR zone",
    "R": "× R (rủi ro)",
    "bien_zone": "mép zone đối diện",
}

#: Nhãn NGẮN cho chữ trên hộp. Bản dài đúng cho hộp thoại và tooltip, nhưng nhét lên
#: hộp thì một dòng nuốt cả khối — mà nhìn hộp là phải hiểu ngay.
DON_VI_NGAN = {
    "gia": "giá", "bps": "bps",
    "atr": "× ATR", "atr_zone": "× ATR zone", "R": "× R",
    "bien_zone": "mép zone đối diện",
}

#: ĐƠN VỊ NÀO DÙNG ĐƯỢC Ở ĐÂU. Bày ra một lựa chọn vô nghĩa rồi soát tĩnh mắng là tệ
#: hơn không bày — nên lọc ngay tại nguồn.
#:
#:   `R` chỉ có nghĩa khi ĐÃ có R: TP đo sau khi SL định nghĩa R, còn SL thì không thể
#:       đo bằng chính nó (vòng tròn).
#:   `bien_zone` cần một mốc để đo tới, nên chỉ hợp với SL/TP.
DON_VI_CHO = {
    "dieu_kien": ("gia", "bps", "atr", "atr_zone"),
    "dem":       ("gia", "bps", "atr", "atr_zone"),
    "sl":        ("gia", "bps", "atr", "atr_zone", "bien_zone"),
    "tp":        ("gia", "bps", "atr", "atr_zone", "R", "bien_zone"),
    "sua":       ("gia", "bps", "atr", "atr_zone", "R"),
}

#: KHÔNG ĐO MỘT ĐẠI LƯỢNG BẰNG CHÍNH NÓ — kết quả luôn bằng 1, một con số không nói gì.
#:
#: Cùng lý lẽ đã viết cho `close` ở `DON_VI_CO_DINH`: `close / close × 10⁴` luôn ra
#: 10000. Ở đây là `zone_atr_tb / zone_atr_tb` — `_quy_doi` chia đúng cho `zone_atr_tb`,
#: nên chọn `× ATR zone` cho toán hạng đó là viết một điều kiện so 1 với một con số.
#:
#: ⚠ Vì sao `atr` KHÔNG nằm trong bảng này dù cũng chia cho ATR: `_quy_doi` chia cho
#: `atr(chu_ky_atr)` trên khung QUYẾT ĐỊNH, còn toán hạng `atr` mang khung và chu kỳ
#: RIÊNG. `atr(M15, 50) < 2 [× ATR]` là một tỉ lệ có nghĩa. Chỉ khi trùng cả khung lẫn
#: chu kỳ nó mới thành 1 — cấm hết là cấm nhầm cả cái dùng được.
DON_VI_CHINH_NO = {"zone_atr_tb": "atr_zone"}

#: `× ATR zone` và `mép zone đối diện` cần có zone ở phía trên mới có mẫu số.
DON_VI_CAN_ZONE = ("atr_zone", "bien_zone")

#: TÊN CŨ → tên mới. Hai bảng gộp làm một nên mọi file đã lưu phải đi qua đây.
#:
#: ⚠ `theo_pt` CỐ Ý không có mặt. `pt` đã bỏ, mà đổi nó sang `bps` thì phải NHÂN GIÁ TRỊ
#: với 100 — và giá trị có thể là một TÊN THAM SỐ, lúc đó không nhân được. Một phép đổi
#: đúng-một-nửa là loại hỏng tệ nhất: file vẫn chạy, chỉ sai 100 lần. Nên để nguyên, và
#: soát tĩnh nói to "chưa chọn cách tính". (Không file đã lưu nào dùng nó.)
DON_VI_CU = {
    "theo_ATR": "atr", "theo_ATR_vung": "atr_zone", "theo_R": "R",
    "theo_bien_vung": "bien_zone", "theo_gia": "gia",
    "tho": "gia",
}

#: Loại đại lượng nào được CHỌN đơn vị. Còn lại: nhãn cố định, ô mờ.
#:
#: Vì sao `close` KHÔNG quy đổi được dù cũng "đơn vị giá": nó là một MỨC, không phải
#: một BỀ RỘNG. `close / close × 10⁴` luôn ra 10000 — một con số không nói gì.
LOAI_CO_DON_VI = "khoang_cach"

#: ĐƠN VỊ ĐẾM — những ô số KHÔNG quy đổi gì cả, nhưng con số trong đó vẫn đo một thứ
#: cụ thể. Tách khỏi `DON_VI` vì `DON_VI` là phép TÍNH mà bộ chạy thật sự thực hiện,
#: còn mấy cái này chỉ trả lời "con số này đo cái gì".
DON_VI_DEM = {"nen": "nến", "lenh": "lệnh", "lot": "lot"}

#: MỌI đơn vị, một bảng nhãn. Bảng tham số khai `don_vi` bằng một khoá ở đây.
NHAN_DON_VI = {**DON_VI, **DON_VI_DEM}

#: Loại đại lượng → đơn vị CỐ ĐỊNH của ô so với nó. `None` = không có vế phải.
#:
#: ⚠ Trước đây bảng này chứa NHÃN (`"boi_R": "× R"`) chứ không phải KHOÁ, nên `× R` tồn
#: tại hai lần dưới hai dạng và không cách nào so được với đơn vị của một tham số. Giờ
#: mọi nơi nói cùng một thứ tiếng: khoá.
LOAI_DON_VI = {"muc_gia": "gia", "boi_R": "R", "dung_sai": None}

#: Toán hạng → đơn vị của nó, khi `loai` không đủ để nói.
#:
#: ⚠ `loai = "dem"` KHÔNG đủ: `zone_dem` đếm NẾN còn `so_vi_the` đếm LỆNH. Gộp cả hai
#: vào một đơn vị "đếm" thì nút chọn tham số sẽ mời `so_vi_the_toi_da = 3 lệnh` vào ô
#: "zone cần bao nhiêu nến" — hai con số chẳng liên quan gì nhau. Bài soát mới bắt được
#: đúng chỗ này ngay lần chạy đầu.
TOAN_HANG_DON_VI = {t["key"]: t["don_vi"] for t in TOAN_HANG if t.get("don_vi")}

#: ĐƠN VỊ CŨ của bảng tham số → khoá. Cột đó từng là CHỮ TỰ DO ai gõ gì cũng được, nên
#: sơ đồ mẫu mang `"× ATR vùng"` — một chuỗi không tồn tại ở đâu, rác còn lại từ lần đổi
#: tên vùng→zone, và không ai bắt được vì chưa có gì đọc nó.
#:
#: `"%"` cố ý không có mặt: `pt` đã bỏ, đổi sang `bps` phải nhân 100 (xem `DON_VI_CU`).
DON_VI_THAM_SO_CU = {
    "bps": "bps", "nen": "nen", "nến": "nen", "lot": "lot",
    "lệnh": "lenh", "giá": "gia", "giá tuyệt đối": "gia",
    "× ATR": "atr", "× ATR hiện tại": "atr",
    "× ATR zone": "atr_zone", "× ATR vùng": "atr_zone",
    "× ATR trung bình zone": "atr_zone",
    "× R": "R", "× R (rủi ro)": "R",
    "mép zone đối diện": "bien_zone",
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
        # ĐƠN VỊ phải là một KHOÁ, không phải chữ tự do — nó là thứ quyết định tham số
        # này được phép rơi vào ô nào. Chữ lạ thì để rỗng chứ KHÔNG đoán: soát tĩnh sẽ
        # nói ra, còn đoán sai thì con số lặng lẽ mang nghĩa khác.
        dv = str(t.get("don_vi") or "").strip()
        dv = dv if dv in NHAN_DON_VI else DON_VI_THAM_SO_CU.get(dv, "")
        ra.append(make_tham_so(ten, str(t.get("nhan") or "").strip(), v, dv,
                               str(t.get("ghi_chu") or "")))
    return ra


TOAN_HANG_LOAI = {t["key"]: t.get("loai", "muc_gia") for t in TOAN_HANG}


def _chuan_toan_hang(o):
    """Giữ lại ĐÚNG những trường toán hạng này khai, vứt phần còn lại.

    Vì sao cần: đổi toán hạng từ ATR sang "Giá đóng cửa" mà giữ nguyên `period` thì file
    mang một con số không ai đọc, và lần sau đổi ngược lại nó sống dậy — người dùng
    tưởng mình vừa gõ, thật ra là rác cũ. Giao diện đã dọn khi đổi; đây là chốt chặn cho
    file nhập từ ngoài và cho `shift` vừa bị bỏ khỏi toán hạng giá."""
    if not isinstance(o, dict) or not o.get("ten"):
        return dict(o) if isinstance(o, dict) else {}
    ten = o["ten"]
    if ten not in TOAN_HANG_KEYS:
        return dict(o)          # toán hạng lạ: giữ nguyên để soát tĩnh còn mắng đúng chỗ
    ra = {"ten": ten}
    for k in TOAN_HANG_THAMSO[ten]:
        if k in o:
            ra[k] = o[k]
    return ra


def don_vi_cua_o(o_dau, ten=None, tinh=None):
    """ĐƠN VỊ CỦA MỘT Ô SỐ — khoá, hoặc `None` nếu ô đó không mang đơn vị nào.

    Đây là chỗ DUY NHẤT trả lời câu "con số nằm trong ô này đo cái gì". Cả ba thứ dựa
    vào nó và phải nhất trí:
      · nút `▾` chỉ liệt kê tham số có ĐÚNG đơn vị này;
      · chọn tham số xong thì ô đơn vị KHOÁ, hiện đúng đơn vị này;
      · soát tĩnh so đơn vị khai trong bảng tham số với đơn vị ở chỗ dùng.

    Có ô đơn vị CHỌN ĐƯỢC (khoảng cách), có ô đơn vị CỐ ĐỊNH (chu kỳ luôn là nến, lot
    luôn là lot, `so_vi_the` luôn là đếm). Cả hai đều là "đơn vị của ô" — chỉ khác chỗ
    người dùng có được đổi hay không.
    """
    if o_dau == "chu_ky":
        return "nen"
    if o_dau == "lot":
        return "lot"
    if o_dau == "dieu_kien":
        loai = TOAN_HANG_LOAI.get(ten)
        if loai == LOAI_CO_DON_VI:
            return tinh or "gia"
        if loai == "dung_sai":
            return None
        return TOAN_HANG_DON_VI.get(ten) or LOAI_DON_VI.get(loai)
    return tinh or "gia"          # dem · sl · tp · sua


def don_vi_cho(ten, o_dau="dieu_kien", co_zone=True):
    """Toán hạng này chọn được đơn vị nào. Rỗng = ô đơn vị mờ, dùng nhãn cố định.

    `co_zone` = khối này có nằm SAU cổng zone không. Không thì `× ATR zone` và `mép zone
    đối diện` mất mẫu số → luôn NaN → cổng luôn trượt; bày ra chỉ tổ mời chọn một thứ
    chắc chắn chết.

    ⚠ Chỗ soát tĩnh gọi hàm này CỐ Ý để `co_zone=True`: `_soat_cong_zone` đã báo ca đó
    bằng câu rõ hơn nhiều ("nối nó vào sau cổng zone"). Hai nơi cùng mắng một lỗi thì
    bảng Vấn đề hiện hai dòng cho một chuyện."""
    if o_dau != "dieu_kien":
        ds = list(DON_VI_CHO.get(o_dau, ()))
    elif TOAN_HANG_LOAI.get(ten) == LOAI_CO_DON_VI:
        ds = list(DON_VI_CHO["dieu_kien"])
    else:
        return []
    tu = DON_VI_CHINH_NO.get(ten)
    return [d for d in ds
            if d != tu and (co_zone or d not in DON_VI_CAN_ZONE)]


# NHỊP mặc định của từng sơ đồ. Hai con số KHÁC NHAU là CỐ Ý (core.md §12.4):
#   Entry  là QUYẾT ĐỊNH  — 5 phút xem một lần là đủ và là đúng.
#   Manage là PHẢN ỨNG    — càng nhanh càng đúng, M1 là nhanh nhất dữ liệu cho phép.
# Bản gốc chạy `ManageBreakEven()` MỖI TICK, ngoài mọi guard nến (`Compress.mq5:128`).
# Để Manage ở M5 là một nến quét lên đủ 1R rồi quay về SL sẽ ghi −1R trong khi EA thật
# đã kịp dời SL và thoát ~0R — lệch có hệ thống, và lệch về phía ta lỗ nhiều hơn.
NHIP_MAC_DINH = {TAB_ENTRY: "M5", TAB_MANAGE: "M1"}


# ---- MỐC NEO của khối Vào lệnh -------------------------------------------
# ⚠ Trước đây khối Vào lệnh KHÔNG có trường nào cho mốc neo: việc "lệnh chờ neo vào mép
# zone thuận chiều" bị viết cứng trong bộ chạy. Nên trên màn hình chỉ hiện mỗi ô ĐỆM —
# và cái đệm, vốn chỉ là tấm khiên mỏng, hoá thành nhân vật chính, còn cái quyết định
# lệnh nằm ở đâu thì tàng hình.
#
# Giờ mốc là BẮT BUỘC và hiện ra; đệm là TÙY CHỌN, bỏ trống thì lệnh nằm đúng mép.
MOC_ENTRY = {
    "zone_HH": "Đỉnh zone (HH)",
    "zone_LL": "Đáy zone (LL)",
    "gia_hien_tai": "Giá hiện tại",
}
#: Mốc nào cần có zone ở phía trên mới có nghĩa.
MOC_CAN_ZONE = ("zone_HH", "zone_LL")


HUONG = {"mua": "Mua", "ban": "Bán"}
# ⚠ KHÔNG có "limit". Giao diện từng cho chọn "Chờ Limit", nhưng `khop_lenh.trong_nen`
# không đọc trường `loai` một lần nào — `_muc_vao` viết cứng hành vi lệnh STOP — và
# `bo_chay._vao_lenh` chỉ neo lệnh `stop` vào mép vùng nén, còn `limit` neo vào giá hiện
# tại rồi CỘNG đệm theo chiều Mua, tức Buy Limit nằm CAO HƠN giá thị trường: một mức sàn
# thật từ chối thẳng. Một ô chọn lặng lẽ làm việc khác mới là thứ nguy hiểm, nên bỏ chứ
# không cài thêm — D_02 vốn chỉ dùng lệnh chờ stop (`khop_lenh.py` đã ghi rõ). Sơ đồ cũ
# nào còn `limit` sẽ bị validator báo lỗi rõ ràng, đúng chứ không sai: chúng vốn đang cho
# số sai.
LOAI_LENH = {"market": "Thị trường", "stop": "Chờ Stop"}

# ---- Chế độ của "Sửa lệnh" -------------------------------------------------
# Một hành động, nhiều chế độ — thay vì bảy hành động gần giống nhau. Tất cả đều tác
# động lên lệnh ĐÃ CÓ, không cái nào tạo ra lệnh mới.
SUA_CHE_DO = {
    "doi_sl": "Dời Stop Loss",
    "doi_tp": "Dời Take Profit",
    "hoa_von": "Dời SL về hoà vốn",
    # ⚠ MỘT chế độ thay cho `dong_han` + `huy_cho`.
    #
    # Manage chạy MỘT LƯỢT CHO MỖI lệnh đang sống, nên "lệnh này" là duy nhất và bộ
    # chạy TỰ BIẾT nó đã khớp hay chưa: khớp rồi thì đóng, chưa khớp thì huỷ. Bắt
    # người dùng chọn giữa hai cái là bắt họ khai một thứ máy đã biết — và chọn nhầm
    # thì hành động im lặng không làm gì.
    "ket_thuc": "Kết thúc lệnh này",
}

#: CHẾ ĐỘ CŨ → mới. Hai chế độ đã bỏ:
#:   `trailing` và `dong_mot_phan` — chưa từng chạy qua một bài kiểm nào. `dong_mot_phan`
#:   thậm chí ném thẳng "chưa được cài trong sổ lệnh" khi chạy tới.
SUA_CHE_DO_CU = {"dong_han": "ket_thuc", "huy_cho": "ket_thuc",
                 "trailing": "doi_sl", "dong_mot_phan": "ket_thuc"}
# Chế độ nào cần ô "cách tính + giá trị", chế độ nào không.
#
# `hoa_von` KHÔNG có tham số: nó chỉ là "SL = giá vào". Mốc kích hoạt (lãi đủ mấy R)
# và câu hỏi "đã dời chưa" đều nằm ở CỔNG phía trước, chỗ nhìn thấy được — chứ không
# giấu trong hành động như `ManageBreakEven` của D_02 giấu ba dòng guard.
SUA_CAN_GIA = ("doi_sl", "doi_tp")


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


def make_start_step(name="Chạy lại từ đây", nhip="M5"):
    """Khối BẮT ĐẦU — không làm gì cả, nhưng nói ra một điều quan trọng.

    CẢ SƠ ĐỒ là một vòng lặp: nó chạy lại từ khối này ở MỖI NẾN MỚI. Nên "chờ tới khi"
    không phải vẽ — không cổng nào khớp thì hết lượt, nến sau tự chạy lại từ đây.

    Đúng MỘT khối mỗi sơ đồ, tạo sẵn khi mở canvas trắng, không xoá được và không nhận
    đường nối đi vào. Nhờ nó `flow_entry` không bao giờ trả None, nên một đường nối
    ngược lên trên không thể "nuốt" mất điểm bắt đầu (xem core.md §3.3)."""
    return {"kind": KIND_START, "id": new_step_id(), "name": name,
            "nhip": nhip if nhip in TIMEFRAMES else NHIP_MAC_DINH[TAB_ENTRY]}


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
    """Một khoảng cách giá: {"tinh": "atr", "value": 1.5} -> '1.5 × ATR hiện tại'.

    `value` có thể là một CHUỖI = tên tham số, khi đó hiện `tên (giá trị)`."""
    if not isinstance(k, dict):
        return "?"
    return f"{_so_hoac_ten(k.get('value'), tham_so)} {DON_VI.get(k.get('tinh'), '?')}"


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
    p = (c or {}).get("phai")
    # KIỂU SUY RA ĐƯỢC, không cần khai: có khoá `ten` là một đại lượng, còn lại là một
    # LƯỢNG `{value, tinh}` mà `value` có thể là số hoặc TÊN THAM SỐ. Đây đúng luật
    # xuyên suốt app — xem `ChuongTrinh.so()`.
    if isinstance(p, dict) and p.get("ten"):
        return toan_hang_display(p, tham_so)
    if isinstance(p, dict):
        s_ = _so_hoac_ten(p.get("value"), tham_so)
        dv = p.get("tinh")
        return f"{s_} {DON_VI[dv]}" if dv and dv in DON_VI and dv != "gia" else s_
    return _so_hoac_ten(p, tham_so)


def cond_display(c, tham_so=None):
    """Một dòng điều kiện: 'ATR chuẩn hoá (bps)(M5, 14) nhỏ hơn 7'.

    Toán hạng vốn đã đúng/sai thì viết thẳng, không ghép phép so — "Đang có vị thế
    bằng 1" là câu không ai đọc được."""
    trai = (c or {}).get("trai") or {}
    phep = (c or {}).get("phep")
    # Toán hạng đúng/sai không có vế phải — `là ĐÚNG` / `là SAI` đã là cả mệnh đề.
    if phep in PHEP_KHONG_VE_PHAI:
        return f"{toan_hang_display(trai, tham_so)} {PHEP_SO.get(phep, '?')}"
    return (f"{toan_hang_display(trai, tham_so)} "
            f"{PHEP_SO.get(phep, '?')} "
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
        return dau + s

    return dau + ACTION_LABELS.get(t, str(t))


def dong_khoi(a, tham_so=None, tab=None):
    """Chữ trên HỘP — danh sách dòng NGẮN, mỗi trường một dòng.

    Khác `action_display` (một câu đầy đủ, dùng cho hộp thoại và tooltip): trên hộp,
    "Vào lệnh Mua Chờ Stop · lot = 0.01 lot · đệm dem_vao_lenh = 0.1 × ATR hiện tại
    ngoài mép vùng · SL …" là một câu chạy dài bốn dòng, đọc không ra. Tách mỗi trường
    một dòng thì mắt quét dọc, và với nhãn đơn vị ngắn thì dòng nào cũng vừa một hàng."""
    if is_start_step(a):
        # Nhịp do PYTHON sinh ra từ khoá `nhip`, không phải chữ gõ tay trong `name`.
        # Bản cũ ghi thẳng "Mỗi nến M5" vào tên khối, nên đổi nhịp thì khối vẫn ghi M5.
        ds = [f"Mỗi nến {a.get('nhip') or NHIP_MAC_DINH[TAB_ENTRY]}"]
        if tab == TAB_MANAGE:
            # Không phải chuyện đặt tên: Manage chạy MỘT LƯỢT CHO MỖI lệnh đang sống.
            # Đó là cấu trúc, nên phải hiện ra dù người dùng đặt tên khối là gì.
            ds.append("một lượt cho MỖI lệnh đang sống")
        return ds

    t = (a or {}).get("type")

    if t == CHECK_COND:
        ds = [cond_display(c, tham_so) for c in a.get("conditions") or []]             or ["chưa có điều kiện nào — luôn khớp"]
        # CỔNG ZONE phải nhìn thấy được trên hộp. Nó không chỉ hỏi — nó ĐỊNH NGHĨA
        # zone cho mọi khối phía sau, và đó là chuyện lớn nhất một cổng có thể làm.
        if a.get("cong_zone"):
            ds.insert(0, "⬗ CỔNG ZONE — qua thì zone lớn, trượt thì zone chết")
        return ds

    def khoang(k):
        return (f"{_so_hoac_ten(k.get('value'), tham_so)} "
                f"{DON_VI_NGAN.get(k.get('tinh'), '?')}")

    if t == VAO_LENH:
        ds = [f"{HUONG.get(a.get('huong'), '?')} · {LOAI_LENH.get(a.get('loai'), '?')}"
              f" · {_so_hoac_ten(a.get('lot'), tham_so, hien_ten=False)} lot"]
        # MỐC NEO đứng TRƯỚC đệm — nó mới là thứ quyết định lệnh nằm ở đâu. Bản cũ
        # chỉ hiện đệm, nên tấm khiên mỏng hoá thành nhân vật chính.
        moc = (a.get("entry") or {}).get("moc")
        if moc:
            ds.append(f"tại {MOC_ENTRY.get(moc, moc)}")
        if a.get("dem"):
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


#: Hai đầu nhánh chênh nhau ÍT HƠN chừng này pixel thì coi như NGANG NHAU — mắt không
#: phân biệt được cái nào trên, mà `_khoa_nhanh` vẫn phải chọn một thứ tự. Xem
#: `_soat_thu_tu_nhanh`.
LECH_TOI_THIEU = 8.0


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

    # ---- HAI khối Vào lệnh trên CÙNG một đường ----
    # Cổng "số lệnh chờ = 0" chỉ được hỏi MỘT LẦN ở đầu lượt, nên hai khối Vào lệnh nối
    # tiếp nhau sẽ đẻ ra hai lệnh mà không cổng nào chặn được. D_02 chốt cứng đúng MỘT
    # lệnh chờ (`TradeManager.mqh:330-334`).
    #
    # Chặn ở đây chứ không chặn trong bộ chạy: bộ chạy phải làm ĐÚNG những gì sơ đồ vẽ,
    # còn thứ không nên vẽ thì đừng cho vẽ. Bộ chạy tự ý dừng sau lệnh đầu là nó âm thầm
    # bỏ qua một khối người dùng đã đặt vào.
    vao_lenh = [sid for sid, st in theo_id.items() if st.get("type") == VAO_LENH]
    for sid in vao_lenh:
        tham, hang = {sid}, list(ke.get(sid, []))
        while hang:
            uv = hang.pop(0)
            if uv in tham:
                continue
            tham.add(uv)
            if theo_id.get(uv, {}).get("type") == VAO_LENH:
                _loi(ra, "error", uv,
                     f"{ten(uv)} nằm SAU {ten(sid)} trên cùng một đường — một lượt sẽ "
                     f"đẻ ra HAI lệnh, mà cổng \"số lệnh chờ\" chỉ được hỏi một lần ở "
                     f"đầu lượt nên không chặn được. Hãy tách chúng thành hai NHÁNH.")
                break
            hang += ke.get(uv, [])

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

        # ---- Thứ tự nhánh phải NHÌN THẤY ĐƯỢC ----
        # `_khoa_nhanh` xếp nhánh theo (ghim, y, x, id). Hai đầu nhánh chênh `y` vài
        # pixel thì mắt thấy chúng ngang nhau, nhưng bộ chạy vẫn thử một cái trước —
        # và nếu chênh 0 thì phân định bằng `id`, một uuid KHÔNG ai nhìn thấy và không
        # ai đổi được. Kết quả backtest khi đó phụ thuộc toạ độ canvas: hai file có đồ
        # thị y hệt mà khác vị trí sẽ chạy ra khác nhau.
        # Báo LỖI chứ không cảnh báo: sửa chỉ tốn một cú kéo, còn để nguyên thì cái sai
        # không bao giờ lộ ra — sơ đồ trông vẫn đúng.
        for i, a in enumerate(thang):
            for b in thang[i + 1:]:
                ya, yb = _khoa_nhanh(theo_id[a])[1], _khoa_nhanh(theo_id[b])[1]
                if abs(ya - yb) >= LECH_TOI_THIEU:
                    continue
                _loi(ra, "error", a,
                     f"{ten(a)} và {ten(b)} là hai nhánh của {ten(sid)} nhưng nằm "
                     f"NGANG NHAU (lệch {abs(ya - yb):.0f} px). Nhánh nào được thử "
                     f"trước là do vị trí quyết, nên đặt ngang nhau là để máy tự chọn "
                     f"bằng thứ mắt không thấy. Hãy kéo một trong hai lên hoặc xuống "
                     f"ít nhất {LECH_TOI_THIEU:.0f} px.")

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
    if not isinstance(k, dict) or k.get("tinh") not in DON_VI:
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
    if k["tinh"] != "gia" and v <= 0:
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
            hai_ben = bool(a.get("so_dai_luong"))
            for k, c in enumerate(ds):
                cho = f"Điều kiện {k + 1}"
                _soat_toan_hang((c or {}).get("trai"), f"{cho} — vế trái", e, tab,
                                ten_tham_so)
                ten_t = ((c or {}).get("trai") or {}).get("ten")
                phep = (c or {}).get("phep")
                # Cơ chế "so hai đại lượng" không nhận toán hạng đúng/sai: `lệnh này đã
                # khớp > zone_HH` không phải một câu. Chuẩn hoá KHÔNG tự đổi toán hạng —
                # đổi hộ là vứt mất thứ người dùng đã chọn, nên nói ra chứ không sửa lén.
                if hai_ben and _la_toan_hang_dung_sai(ten_t):
                    e(f'{cho} — "{TOAN_HANG_LABELS.get(ten_t, ten_t)}" là một toán hạng '
                      f"ĐÚNG/SAI, không so được với một đại lượng khác. Bỏ tick "
                      f'"So hai đại lượng", hoặc tách dòng này sang một cổng riêng.')
                    continue
                # ĐÚNG/SAI dùng phép riêng và KHÔNG có vế phải — hai luật này canh
                # nhau: toán hạng số mà mang `là ĐÚNG` cũng vô nghĩa như ngược lại.
                if _la_toan_hang_dung_sai(ten_t):
                    if phep not in PHEP_DUNG_SAI:
                        e(f"{cho} — toán hạng đúng/sai chỉ dùng "
                          f"\"{PHEP_SO['la_dung']}\" hoặc \"{PHEP_SO['la_sai']}\".")
                    continue
                if phep in PHEP_DUNG_SAI:
                    e(f"{cho} — \"{PHEP_SO[phep]}\" chỉ dùng cho toán hạng đúng/sai.")
                    continue
                if phep not in PHEP_SO:
                    e(f"{cho} chưa chọn phép so sánh.")
                p_ = (c or {}).get("phai")
                if isinstance(p_, dict) and p_.get("ten"):
                    _soat_toan_hang(p_, f"{cho} — vế phải", e, tab, ten_tham_so)
                else:
                    gt = p_.get("value") if isinstance(p_, dict) else p_
                    _soat_so(gt, f"{cho} — vế phải", e, ten_tham_so, duong=False)
                    dv = p_.get("tinh") if isinstance(p_, dict) else None
                    if dv and dv not in don_vi_cho(ten_t):
                        e(f"{cho} — đơn vị \"{DON_VI.get(dv, dv)}\" không dùng được "
                          f"với {TOAN_HANG_LABELS.get(ten_t, ten_t)}: nó không phải "
                          f"một BỀ RỘNG giá nên không quy đổi được.")

        elif t == VAO_LENH:
            if a.get("huong") not in HUONG:
                e("\"Vào lệnh\" chưa chọn hướng Mua/Bán.")
            if a.get("loai") not in LOAI_LENH:
                e("\"Vào lệnh\" chưa chọn loại lệnh.")
            _soat_so(a.get("lot"), "\"Vào lệnh\" — khối lượng", e, ten_tham_so)
            if (a.get("entry") or {}).get("moc") not in MOC_ENTRY:
                e('"Vào lệnh" chưa chọn MỐC NEO — lệnh sẽ nằm ở đâu?')
            # ĐỆM là TUỲ CHỌN. Câu cũ ("lệnh chờ cần khoảng đệm, không thì khớp luôn")
            # đúng khi mốc neo còn tàng hình và mặc định là giá hiện tại. Giờ mốc hiện
            # ra: neo vào mép zone mà đệm 0 là lệnh nằm ĐÚNG mép — hợp lệ, chỉ dễ dính
            # một nhịp phá giả hơn. Đó là lựa chọn của người vẽ, không phải lỗi.
            if a.get("loai") == "stop" and not a.get("dem")                     and (a.get("entry") or {}).get("moc") == "gia_hien_tai":
                e("Lệnh chờ neo vào GIÁ HIỆN TẠI mà không có đệm thì khớp ngay — "
                  "nó không còn là lệnh chờ nữa. Thêm đệm, hoặc neo vào mép zone.")
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


#: Toán hạng chỉ có nghĩa khi ĐÃ có zone. Chúng đọc từ zone hiện hành, mà zone thì do
#: một cổng trong chính sơ đồ định nghĩa — không còn cỗ máy ẩn nào dựng sẵn nữa.
TOAN_HANG_CAN_ZONE = ("zone_dem", "zone_HH", "zone_LL", "zone_range",
                      "zone_range_atr", "zone_atr_tb", "zone_da_sinh_lenh")
#: ⚠ `DON_VI_CAN_ZONE` từng được khai LẠI ngay tại đây — hai dòng y hệt nhau cách nhau
#: 1100 dòng. Trùng như vậy thì sửa một chỗ là hai nơi nói khác nhau mà không ai thấy.
#: Bản duy nhất nằm cạnh `DON_VI_CHO`, chỗ mọi luật về đơn vị sống chung.


def _khoi_can_zone(st):
    """Khối này có đọc thứ gì thuộc về zone không → vì sao."""
    if not isinstance(st, dict):
        return None
    t = st.get("type")
    if t == CHECK_COND:
        for c in st.get("conditions") or []:
            for ve in ("trai", "phai"):
                v = (c or {}).get(ve)
                if isinstance(v, dict) and v.get("ten") in TOAN_HANG_CAN_ZONE:
                    return TOAN_HANG_LABELS.get(v["ten"], v["ten"])
            # Đơn vị `× ATR zone` cũng đọc zone, dù không toán hạng zone nào xuất hiện.
            dv = (c.get("phai") or {}).get("tinh")                 if isinstance(c.get("phai"), dict) else None
            if dv in DON_VI_CAN_ZONE:
                return DON_VI.get(dv, dv)
    if t == VAO_LENH:
        if ((st.get("entry") or {}).get("moc")) in MOC_CAN_ZONE:
            return MOC_ENTRY.get(st["entry"]["moc"], "mốc neo zone")
        for k in ("dem", "sl", "tp"):
            if (st.get(k) or {}).get("tinh") in DON_VI_CAN_ZONE:
                return DON_VI.get(st[k]["tinh"], k)
    if t == SUA_LENH and (st.get("khoang") or {}).get("tinh") in DON_VI_CAN_ZONE:
        return DON_VI.get(st["khoang"]["tinh"], "khoảng")
    return None


def khoi_sau_cong_zone(steps, edges):
    """Id những khối mà dòng chảy đã đi QUA cổng zone trước khi tới.

    Chỉ ở những khối này thì zone mới tồn tại — nên chỉ ở đây mới nên bày ra các toán
    hạng zone và đơn vị `× ATR zone` / `mép zone đối diện`.

    Tách khỏi `_soat_cong_zone` để giao diện dùng CHUNG một phép duyệt: nếu TypeScript
    tự đi lại đồ thị thì thành hai luật, và hai luật rồi sẽ lệch nhau — cùng lý do
    `dat_ten.cho` trả sẵn đường dẫn thay vì để giao diện tự quét.

    Không có cổng zone → rỗng. Cổng zone KHÔNG tự tính là "sau chính nó": điều kiện
    của cổng chạy TRƯỚC khi zone lớn thêm, nên ngay trong cổng thì zone vẫn chưa có."""
    cong = [s for s in steps or [] if isinstance(s, dict) and s.get("cong_zone")]
    if not cong:
        return set()
    _, ke = flow_map(steps, edges)
    toi, hang = set(), [cong[0].get("id")]
    while hang:
        for y in ke.get(hang.pop(), []):
            if y not in toi:
                toi.add(y)
                hang.append(y)
    return toi


def _soat_cong_zone(steps, edges, tab):
    """ZONE PHẢI ĐƯỢC MỘT CỔNG ĐỊNH NGHĨA, và cổng đó phải đứng TRƯỚC.

    ⚠ Đây là luật thay cho cỗ máy ẩn cũ. Trước đây zone tự có mặt vì một hàm chạy ngoài
    sơ đồ dựng sẵn nó; ai hỏi `zone_dem` ở đâu cũng ra số. Giờ zone chỉ tồn tại nếu
    người vẽ chỉ ra ĐIỀU KIỆN ĐẾM — và điều kiện đó chính là một cổng mang cờ
    `cong_zone`. Không có cổng thì hỏi zone là hỏi một thứ chưa được định nghĩa, và
    câu trả lời phải là một LỖI RÕ RÀNG chứ không phải số 0 im lặng.
    """
    ra = []

    def loi(msg, st=None):
        ra.append({"severity": "error", "step": (st or {}).get("id"),
                   "index": None, "tab": tab, "message": msg})

    cong = [s for s in steps if isinstance(s, dict) and s.get("cong_zone")]
    can = [(s, _khoi_can_zone(s)) for s in steps]
    can = [(s, vs) for s, vs in can if vs]

    if tab == TAB_MANAGE and cong:
        loi("Cổng zone chỉ đặt ở sơ đồ Entry. Manage chạy một lượt cho MỖI lệnh đang "
            "sống, nên đặt cổng đếm ở đó là một cây nến bị đếm nhiều lần.", cong[0])
        return ra
    if len(cong) > 1:
        loi(f"Có {len(cong)} cổng zone. Chỉ được MỘT — hai cổng cùng nuôi một zone thì "
            "cái sau đè cái trước, và không ai đọc ra được zone đang đếm theo luật nào.",
            cong[1])
    if can and not cong:
        ten = ", ".join(sorted({v for _, v in can})[:3])
        loi(f"Sơ đồ đọc {ten} nhưng KHÔNG có cổng zone nào. Zone do một cổng điều kiện "
            f"định nghĩa — hãy đánh dấu cổng nào là điều kiện đếm (ví dụ "
            f'"ATR chuẩn hoá < ngưỡng"), rồi đặt các khối hỏi về zone SAU nó.')
        return ra
    if not cong:
        return ra

    # Khối hỏi về zone phải TỚI ĐƯỢC từ cổng zone — đứng trước hoặc ở nhánh khác thì
    # nó đang hỏi zone của nến TRƯỚC, một câu hỏi không ai định nghĩa.
    toi = khoi_sau_cong_zone(steps, edges)
    for st, vs in can:
        if st.get("id") not in toi:
            loi(f'Khối này đọc {vs} nhưng KHÔNG nằm sau cổng zone. Nối nó vào sau '
                f'"{cong[0].get("name") or "cổng zone"}" — hỏi về zone trước khi zone '
                f"được định nghĩa thì không có câu trả lời nào đúng.", st)
    return ra


#: NHÃN của từng ô KHOẢNG CÁCH, và mẩu tên gợi ý.
#: Khoá là "vai" — VAI TRÒ của con số, không phải giá trị. Hai con số 1.5 nằm ở SL và
#: ở TP là hai khái niệm khác nhau dù bằng nhau, nên vai phải vào khoá gom nhóm.
VAI_SO = {
    "dem":    ("khoảng đệm", "dem"),
    "sl":     ("Stop Loss ban đầu", "sl"),
    "tp":     ("Take Profit ban đầu", "tp"),
    "khoang": ('khoảng của "Sửa lệnh"', "khoang"),
}


def di_o_so(doc):
    """Đi qua MỌI ô số của cả hai sơ đồ. Một phép duyệt, nhiều người dùng.

    Sinh ra từng bản ghi::

        {vai, khoa, nhan, goi_y, don_vi, gia_tri, tab, step, duong}

    `gia_tri` là SỐ nếu người dùng gõ tay, là CHUỖI nếu ô đang giữ tên một tham số —
    hai phía của cùng một câu hỏi:
      · số  → `_soat_so_lap` gom lại, số nào lặp thì mời đặt tên;
      · tên → `_don_vi_dang_dung` soi xem tham số ấy có đúng đơn vị của ô không.

    Viết chung một hàm là có chủ ý: hai phép duyệt "mọi ô số" đặt cạnh nhau thì sớm
    muộn một bên quên mất một ô, và cái quên đó im lặng.
    """
    def la_so(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def o(vai, khoa, nhan, goi_y, don_vi, v, tab, sid, duong):
        if la_so(v) or (isinstance(v, str) and v):
            yield {"vai": vai, "khoa": khoa, "nhan": nhan, "goi_y": goi_y,
                   "don_vi": don_vi, "gia_tri": v,
                   "tab": tab, "step": sid, "duong": duong}

    def chu_ky(x, tab, sid, duong):
        """Chu kỳ chỉ báo. Ô này luôn đo bằng NẾN, mọi chỉ báo như nhau."""
        if not isinstance(x, dict) or x.get("ten") not in TOAN_HANG_KEYS:
            return
        ten = x["ten"]
        yield from o("chu_ky", ("chu_ky", ten, x.get("period")),
                     f"chu kỳ {TOAN_HANG_LABELS[ten]}", f"chu_ky_{ten}",
                     don_vi_cua_o("chu_ky"), x.get("period"),
                     tab, sid, duong + ["period"])

    for tab in TABS:
        for st in ((doc or {}).get(tab) or {}).get("steps") or []:
            if not isinstance(st, dict):
                continue
            sid = st.get("id")
            for i, c in enumerate(st.get("conditions") or []):
                if not isinstance(c, dict):
                    continue
                trai = c.get("trai") if isinstance(c.get("trai"), dict) else {}
                yield from chu_ky(trai, tab, sid, ["conditions", i, "trai"])
                p = c.get("phai")
                if not isinstance(p, dict):
                    continue
                if p.get("ten"):
                    yield from chu_ky(p, tab, sid, ["conditions", i, "phai"])
                    continue
                tt = trai.get("ten")
                if tt not in TOAN_HANG_KEYS:
                    continue
                dv = don_vi_cua_o("dieu_kien", tt, p.get("tinh"))
                if dv is None:                      # đúng/sai: không có vế phải
                    continue
                nhan = (f"ngưỡng so với {TOAN_HANG_LABELS[tt]}"
                        f" ({NHAN_DON_VI.get(dv, dv)})")
                yield from o("nguong", ("nguong", tt, dv, p.get("value")), nhan,
                             f"nguong_{tt}_{dv}", dv, p.get("value"),
                             tab, sid, ["conditions", i, "phai", "value"])
            for k, (nhan, mau) in VAI_SO.items():
                kh = st.get(k)
                if not isinstance(kh, dict) or kh.get("tinh") not in DON_VI:
                    continue
                dv = don_vi_cua_o(k, tinh=kh["tinh"])
                yield from o(k, (k, dv, kh.get("value")),
                             f"{nhan} ({NHAN_DON_VI[dv]})", f"{mau}_{dv}", dv,
                             kh.get("value"), tab, sid, [k, "value"])
            yield from o("lot", ("lot", st.get("lot")), "khối lượng lệnh",
                         "khoi_luong", don_vi_cua_o("lot"), st.get("lot"),
                         tab, sid, ["lot"])


def _soat_so_lap(doc):
    """CÙNG MỘT CON SỐ gõ tay ở HAI NƠI cùng vai — cảnh báo, và đưa sẵn nút đặt tên.

    Đây là lý do bảng tham số tồn tại. Không phải để "khai báo trước khi dùng" — gõ
    thẳng `7` vào ô là đủ và rõ hơn. Mà là vì khi `7` xuất hiện hai chỗ, sửa một chỗ
    quên chỗ kia thì chiến lược lệch ÂM THẦM: không lỗi, không báo, chỉ là kết quả
    backtest khác đi mà không ai biết vì sao.

    ⚠ Gom nhóm theo (VAI, ĐƠN VỊ, GIÁ TRỊ) chứ không chỉ theo giá trị: `chu_ky_atr = 14`
    và `chu_ky_ma = 14` bằng nhau chỉ vì trùng hợp — gộp chúng lại là đặt tên SAI, và
    sau này đổi một cái thì kéo theo cái kia. Trùng hợp không phải là quan hệ.
    """
    nhom = {}
    for r in di_o_so(doc):
        if isinstance(r["gia_tri"], str):      # đã có tên rồi, không mời đặt nữa
            continue
        m = nhom.setdefault(r["khoa"], {**r, "cho": []})
        m["cho"].append({"tab": r["tab"], "step": r["step"], "duong": r["duong"]})

    ra = []
    for m in nhom.values():
        if len(m["cho"]) < 2:
            continue
        ra.append({
            "severity": "warning", "step": m["cho"][0]["step"], "index": None,
            "tab": m["cho"][0]["tab"],
            "message": f'Số {"%g" % m["gia_tri"]} được gõ tay ở {len(m["cho"])} chỗ, '
                       f"cùng là {m['nhan']}. Sửa một chỗ mà quên chỗ kia thì chiến "
                       f"lược lệch âm thầm — không lỗi, chỉ là kết quả khác đi. Hãy "
                       f"đặt tên cho nó.",
            "dat_ten": {"goi_y": m["goi_y"], "gia_tri": m["gia_tri"],
                        "don_vi": m["don_vi"], "nhan": m["nhan"], "cho": m["cho"]},
        })
    return ra


def _don_vi_dang_dung(doc):
    """Tên tham số → tập ĐƠN VỊ của những ô đang giữ nó."""
    ra = {}
    for r in di_o_so(doc):
        if isinstance(r["gia_tri"], str) and r["don_vi"]:
            ra.setdefault(r["gia_tri"], set()).add(r["don_vi"])
    return ra


def validate_process(doc):
    """Soát CẢ HAI sơ đồ. Mỗi vấn đề mang thêm khoá `tab` để giao diện biết chỗ.

    Cố ý soát cả hai chứ không chỉ tab đang mở: giấu lỗi của tab kia đi thì người dùng
    bấm ▶ Chạy mới biết, và không hiểu vì sao."""
    ra = []
    ds_ts = (doc or {}).get("tham_so") or []
    ten_ts = {t["ten"] for t in ds_ts}
    # ⚠ TÊN TRÙNG: `bang_tham_so` là dict comprehension nên khoá sau đè khoá trước, tức
    # bộ chạy lấy dòng CUỐI; còn `normalize_tham_so` giữ dòng ĐẦU và âm thầm vứt phần
    # sau. Hai chỗ đọc cùng một bảng ra hai con số khác nhau — canvas ghi một đằng,
    # backtest chạy một nẻo, ngay trong CÙNG một lần chạy. Phép `set` ở trên nuốt mất
    # chuyện đó nên trước đây validator không hề hay biết.
    #
    # Mức "error" là cố ý: `api` đã chặn ▶ Chạy khi còn error, nên không ai backtest được
    # một sơ đồ mà chính canvas đang nói dối.
    dem = {}
    for t in ds_ts:
        dem[t["ten"]] = dem.get(t["ten"], 0) + 1
    for ten, n in dem.items():
        if n > 1:
            ra.append({
                "severity": "error", "step": None, "index": None, "tab": TAB_ENTRY,
                "message": f'Tham số "{ten}" bị khai {n} lần. Bộ chạy lấy dòng ĐẦU, chữ '
                           f"trên khối lấy dòng CUỐI — hai nơi nói hai số khác nhau. "
                           f"Lưu lại còn xoá mất những dòng sau. Hãy xoá bớt cho còn một."})
    for tab in TABS:
        g = (doc or {}).get(tab) or {}
        ra += validate_so_do(g.get("steps") or [], g.get("edges"), tab, ten_ts)
        ra += _soat_cong_zone(g.get("steps") or [], g.get("edges") or [], tab)

    # Manage phải chạy NHANH BẰNG HOẶC HƠN Entry. Chậm hơn nghĩa là lệnh vừa sinh phải
    # nằm chờ qua vài nhịp mới được quản lý — SL/hoà vốn phản ứng trễ hơn cả lúc vào
    # lệnh, mà quản lý là PHẢN ỨNG chứ không phải quyết định (xem `NHIP_MAC_DINH`).
    nhip = {}
    for tab in TABS:
        bd = [s for s in ((doc or {}).get(tab) or {}).get("steps") or []
              if is_start_step(s)]
        nhip[tab] = bd[0].get("nhip") if bd else None
    v, m = TF_PHUT.get(nhip.get(TAB_ENTRY)), TF_PHUT.get(nhip.get(TAB_MANAGE))
    if v and m and m > v:
        ra.append({"severity": "warning", "step": None, "index": None,
                   "tab": TAB_MANAGE,
                   "message": f"Manage chạy nhịp {nhip[TAB_MANAGE]}, CHẬM hơn Entry "
                              f"({nhip[TAB_ENTRY]}). Lệnh vừa sinh phải chờ qua vài "
                              f"nhịp mới được quản lý — dời SL và huỷ lệnh chờ đều "
                              f"phản ứng trễ. Quản lý nên nhanh bằng hoặc hơn vào lệnh."})

    # Tham số khai ra mà không khối nào dùng — không sai, nhưng là rác dễ gây hiểu nhầm
    # ("chỉnh số này chắc đổi hành vi"), nên nói ra.
    dung = _tham_so_dang_dung(doc)
    for t in (doc or {}).get("tham_so") or []:
        if t["ten"] not in dung:
            ra.append({"severity": "warning", "step": None, "index": None,
                       "tab": TAB_ENTRY,
                       "message": f'Tham số "{t["ten"]}" không khối nào dùng tới — '
                                  f"sửa nó sẽ không đổi gì cả."})

    # MỘT THAM SỐ, MỘT ĐƠN VỊ. `nguong = 7` khi thì đọc là 7 bps khi thì 7 × ATR là
    # cùng một cái tên mang hai nghĩa — đúng loại bẫy mà bảng tham số sinh ra để chặn.
    # Muốn hai thứ thì đặt hai tên.
    dang_dung = _don_vi_dang_dung(doc)
    bang = {t["ten"]: t for t in ds_ts}
    for ten, ds in sorted(dang_dung.items()):
        t = bang.get(ten)
        if t is None:
            continue                      # tên không có trong bảng — đã có lỗi riêng
        if len(ds) > 1:
            ra.append({
                "severity": "error", "step": None, "index": None, "tab": TAB_ENTRY,
                "message": f'Tham số "{ten}" đang được đọc bằng '
                           f"{len(ds)} đơn vị khác nhau ("
                           + ", ".join(NHAN_DON_VI.get(d, d) for d in sorted(ds))
                           + "). Một cái tên chỉ được mang một nghĩa — tách ra thành "
                             "hai tham số."})
        elif t["don_vi"] and t["don_vi"] not in ds:
            d = next(iter(ds))
            ra.append({
                "severity": "warning", "step": None, "index": None, "tab": TAB_ENTRY,
                "message": f'Tham số "{ten}" khai đơn vị '
                           f"\"{NHAN_DON_VI.get(t['don_vi'], t['don_vi'])}\" nhưng "
                           f"đang dùng ở ô đo bằng \"{NHAN_DON_VI.get(d, d)}\". "
                           f"Bảng tham số đang nói khác chỗ dùng."})
    for t in ds_ts:
        if not t["don_vi"] and t["ten"] in dung:
            ra.append({
                "severity": "warning", "step": None, "index": None, "tab": TAB_ENTRY,
                "message": f'Tham số "{t["ten"]}" chưa có đơn vị. Chưa có đơn vị thì '
                           f"nó không hiện ra trong danh sách chọn của ô nào cả."})

    # Đặt CUỐI: đây là lời khuyên, không phải lỗi. Lỗi thật phải nằm trên đầu bảng.
    ra += _soat_so_lap(doc)
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
                p_ = (c or {}).get("phai")
                if isinstance(p_, dict) and p_.get("ten"):
                    quet_toan_hang(p_)
                elif isinstance(p_, dict):
                    them(p_.get("value"))
            for k in ("dem", "sl", "tp", "khoang"):
                quet_khoang(st.get(k))
            them(st.get("lot"))
    return ra


#: Cách tính khoảng cách nào ngầm ĐỌC toán hạng nào. `atr_zone` không xuất hiện
#: trong điều kiện nào cả, nhưng nó chính là thứ định nghĩa 1R — bảng số liệu mà thiếu
#: nó thì người dùng không kiểm được vì sao SL nằm ở đó.
#: `atr` đọc ATR trên khung QUYẾT ĐỊNH với chu kỳ `chu_ky_atr` — đúng thứ
#: `bo_chay._khoang` gọi. Ghi kèm TÊN tham số (không phải giá trị: ở đây chưa biết) để
#: bảng hiện `ATR(M5, 14)` chứ không trơ ra một chữ "ATR" không rõ là ATR nào.
TINH_CAN_TOAN_HANG = {
    "atr": ({"ten": "atr", "period": "chu_ky_atr"},),
    "atr_zone": ({"ten": "zone_atr_tb"},),
    "bien_zone": ({"ten": "zone_HH"}, {"ten": "zone_LL"}),
}


def toan_hang_dung(doc):
    """Mọi toán hạng sơ đồ THẬT SỰ đọc, đã dedupe, giữ nguyên thứ tự gặp.

    Đây là nguồn của bảng số liệu bên phải. Cố ý suy TỪ SƠ ĐỒ chứ không viết cứng một
    danh sách: viết cứng thì hôm nay là "Vùng nén" của D_02, mai thêm một engine khác là
    bảng nói dối — mà nhóm thì `kho/` đã khai sẵn ở mỗi toán hạng rồi.

    KHÔNG gồm nhóm "Lệnh này": chúng không có MỘT giá trị tại nến i (Manage chạy một
    lượt cho mỗi lệnh), nên chúng thuộc về bảng-theo-từng-lệnh (core.md §12.9)."""
    ra, da = [], set()

    def them(o):
        if not isinstance(o, dict) or not o.get("ten"):
            return
        t = o["ten"]
        if TOAN_HANG_NHOM.get(t) == NHOM_LENH_NAY:
            return
        k = (t, o.get("tf"), o.get("period"), o.get("method"))
        if k in da:
            return
        da.add(k)
        ra.append({"ten": t, "tf": o.get("tf"), "period": o.get("period"),
                   "method": o.get("method"), "shift": o.get("shift"),
                   "nhan": TOAN_HANG_LABELS.get(t, t),
                   "nhom": TOAN_HANG_NHOM.get(t, "Khác")})

    for tab in TABS:
        for st in (doc.get(tab) or {}).get("steps") or []:
            for c in st.get("conditions") or []:
                them(c.get("trai"))
                if c.get("phai_loai") == "toan_hang":
                    them(c.get("phai"))
            for k in ("dem", "sl", "tp", "khoang"):
                tinh = (st.get(k) or {}).get("tinh") if isinstance(st.get(k), dict) else None
                for t in TINH_CAN_TOAN_HANG.get(tinh, ()):
                    them(dict(t))
            # Lệnh chờ STOP neo vào MÉP VÙNG thuận chiều (`bo_chay._vao_lenh`) — đỉnh/đáy
            # vùng là thứ quyết định giá đặt, dù không điều kiện nào hỏi tới. Người dùng
            # phải thấy được nó để biết lệnh sắp nằm ở đâu.
            if st.get("type") == VAO_LENH and st.get("loai") == "stop":
                them({"ten": "zone_HH"})
                them({"ten": "zone_LL"})
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
        # CƠ CHẾ SO SÁNH — MỘT cờ cho CẢ KHỐI, không phải một nút trên từng dòng.
        #
        # Trước đây mỗi dòng có một chip `số`/`đ.lượng`, nên hai dòng trong cùng một khối
        # mang hai hình dạng khác nhau: cột lệch, và mắt phải đọc lại hình dạng ở từng
        # dòng. Đưa lên mức KHỐI thì mọi dòng trong đó giống hệt nhau — học một lần.
        #
        # Cùng lý lẽ app đã viết cho phép HOẶC: *"tách ra thành hai nhánh riêng trên sơ
        # đồ — nhìn sơ đồ là thấy được, còn chữ hoặc giấu trong hộp thoại thì không"*.
        # Muốn một cổng vừa so số vừa so đại lượng thì nối HAI cổng, và nối tiếp chính
        # là VÀ.
        #
        # ⚠ Là CƠ CHẾ chứ không phải LOẠI KHỐI: hai kiểu dùng chung bộ soát, chung phép
        # chuẩn hoá, chung hàm dựng chữ trên thẻ — chỉ khác đúng cái vế phải. Tách thành
        # loại riêng là chẻ ba đoạn mã đáng lẽ chỉ có một.
        if "so_dai_luong" in a:
            hai_ben = bool(a.get("so_dai_luong"))
        else:
            # File CŨ không có cờ — suy từ chính các điều kiện. Chính xác chứ không đoán:
            # đã đo, không sơ đồ nào từng trộn hai kiểu trong một khối.
            hai_ben = any(isinstance(c, dict) and isinstance(c.get("phai"), dict)
                          and c["phai"].get("ten")
                          for c in a.get("conditions") or [])
        for c in a.get("conditions") or []:
            if not isinstance(c, dict):
                continue
            m = {"trai": _chuan_toan_hang(c.get("trai")),
                 "phep": PHEP_CU.get(c.get("phep"), c.get("phep")) or "<"}
            ten = (m["trai"] or {}).get("ten")

            # CƠ CHẾ "so hai đại lượng": vế phải LUÔN là một đại lượng, không bao giờ là
            # số. Đơn vị cũng biến mất — hai vế cùng chia một mẫu số nên nó triệt tiêu.
            if hai_ben:
                if m["phep"] in PHEP_DUNG_SAI:
                    m["phep"] = "<"
                p_ = c.get("phai")
                m["phai"] = (_chuan_toan_hang(p_)
                             if isinstance(p_, dict) and p_.get("ten") else {"ten": ""})
                ds.append(m)
                continue

            # ĐÚNG/SAI: `dao` cũ thành một PHÉP SO. Hết ô tick ngoại lệ — mọi điều kiện
            # từ đây có cùng một hình dạng `[đại lượng] [phép] [lượng]`.
            if _la_toan_hang_dung_sai(ten):
                m["phep"] = ("la_sai" if (c.get("dao") or m["phep"] == "la_sai")
                             else "la_dung")
                ds.append(m)
                continue
            if m["phep"] in PHEP_DUNG_SAI:
                m["phep"] = "<"          # toán hạng số mà mang phép đúng/sai → vô nghĩa

            # VẾ PHẢI — MỘT ô, hai dạng, KIỂU SUY RA chứ không khai:
            #   có khoá `ten`  → một đại lượng khác
            #   còn lại        → LƯỢNG `{value, tinh}`, `value` là số HOẶC tên tham số
            #
            # `phai_loai` cũ biến mất vì nó khai lại một thứ nhìn vào là biết — và app
            # đã suy như thế ở `lot` ngay từ đầu (xem `ChuongTrinh.so()`).
            # Cơ chế "so với giá trị": vế phải LUÔN là một lượng. Một đại lượng lọt vào
            # đây (file cũ, hoặc vừa tắt cờ) thì rơi về 0 — hình dạng của khối do CỜ
            # quyết, không phải do từng dòng tự khai.
            p_ = c.get("phai")
            if isinstance(p_, dict) and p_.get("ten"):
                m["phai"] = {"value": 0.0}
            else:
                gt = p_.get("value") if isinstance(p_, dict) else p_
                if isinstance(gt, str):
                    gt = gt.strip()
                elif isinstance(gt, (int, float)) and not isinstance(gt, bool):
                    gt = float(gt)
                else:
                    gt = 0.0
                q = {"value": gt}
                # ĐƠN VỊ nhập vào LƯỢNG — cùng hình dạng `{value, tinh}` mà SL/TP dùng.
                # Chỉ giữ khi toán hạng thật sự quy đổi được: `so_lenh_cho < 4 [× ATR]`
                # thì thà rơi về `giá` còn hơn ra một con số vô nghĩa mà vẫn so được.
                dv = (p_.get("tinh") if isinstance(p_, dict) else None) or c.get("don_vi")
                dv = DON_VI_CU.get(dv, dv)
                if dv and dv != "gia" and dv in DON_VI and dv in don_vi_cho(ten):
                    q["tinh"] = dv
                m["phai"] = q
            ds.append(m)
        ra["conditions"] = ds
        if hai_ben:
            ra["so_dai_luong"] = True
        # CỔNG ZONE — chính cổng này ĐỊNH NGHĨA zone. Xem `bo_chay._chay_so_do`.
        if a.get("cong_zone"):
            ra["cong_zone"] = True
    elif t == VAO_LENH:
        ra.update({"huong": a.get("huong") or "mua", "loai": a.get("loai") or "stop",
                   "lot": a.get("lot", 0.01)})   # có thể là tên tham số
        # MỐC NEO. Sơ đồ cũ không có trường này — dựng lại đúng hành vi bộ chạy vẫn
        # đang làm, để mở file cũ ra không đổi kết quả: lệnh chờ neo mép zone thuận
        # chiều, lệnh thị trường neo giá hiện tại.
        moc = (a.get("entry") or {}).get("moc") if isinstance(a.get("entry"), dict)             else a.get("entry")
        if moc not in MOC_ENTRY:
            moc = "gia_hien_tai" if ra["loai"] == "market" else (
                "zone_HH" if ra["huong"] == "mua" else "zone_LL")
        ra["entry"] = {"moc": moc}
        for k in ("dem", "sl", "tp"):
            if isinstance(a.get(k), dict) and a[k].get("tinh"):
                ra[k] = {"tinh": a[k]["tinh"], "value": a[k].get("value", 0)}
    elif t == SUA_LENH:
        cd0 = a.get("che_do") or "doi_sl"
        ra["che_do"] = SUA_CHE_DO_CU.get(cd0, cd0)
        if ra["che_do"] in SUA_CAN_GIA and isinstance(a.get("khoang"), dict) \
                and a["khoang"].get("tinh"):
            ra["khoang"] = {"tinh": a["khoang"]["tinh"],
                            "value": a["khoang"].get("value", 0)}
    return ra


def normalize_step(s, nhip_mac_dinh="M5"):
    if not isinstance(s, dict):
        return None
    if s.get("kind") == KIND_START:
        # NHỊP thuộc về khối Bắt đầu, không phải một ô dropdown ở góc ribbon. Trước đây
        # chữ "M5" trên khối là một cái TÊN GÕ TAY không nối với `doc.timeframe` bằng
        # gì cả — đổi dropdown thì khối vẫn ghi M5, tức sơ đồ nói dối. Đúng cái lỗi
        # `7.0` viết cứng hai chỗ mà bảng tham số đã dọn.
        n = s.get("nhip")
        return _giu_chung(s, {"kind": KIND_START,
                              "nhip": n if n in TIMEFRAMES else nhip_mac_dinh})
    a = normalize_action(s)
    if a is None:
        return None
    a["kind"] = KIND_ACTION
    return _giu_chung(s, a)


def _chuan_so_do(g, nhip="M5"):
    steps = [x for x in (normalize_step(s, nhip) for s in (g or {}).get("steps") or []) if x]
    ensure_step_ids(steps)
    edges = (g or {}).get("edges")
    edges = default_edges(steps) if edges is None else clean_edges(edges, steps)
    return {"steps": steps, "edges": edges}


#: TÊN CŨ → TÊN MỚI, cho file đã lưu trước lần đổi "vùng nén" thành "zone".
#:
#: ⚠ Không có bảng này thì mở một sơ đồ cũ ra là các toán hạng biến thành "không có
#: trong kho" và validator xoá sạch — hỏng vĩnh viễn, im lặng. Chuyển tên ở ĐÂY, chỗ
#: mọi file đều phải đi qua, chứ không rải if/else khắp nơi.
#:
#: Đổi tên cả tham số: `zone_dem` từng là tên của CẢ toán hạng lẫn tham số, nên
#: `zone_dem >= zone_dem` không đọc ra được vế nào là gì.
TEN_CU = {
    "so_nen_nen": "zone_dem", "dinh_vung": "zone_HH", "day_vung": "zone_LL",
    "rong_vung": "zone_range", "rong_vung_atr": "zone_range_atr",
    "atr_tb_vung": "zone_atr_tb", "vung_da_sinh_lenh": "zone_da_sinh_lenh",
}
TEN_THAM_SO_CU = {"so_nen_nen": "zone_can_nen", "rong_vung_toi_da": "zone_range_max"}


#: Toán hạng cũ → (toán hạng mới, đơn vị). Đây là hai mục ĐÃ RỜI KHO thành ĐƠN VỊ.
#:
#: ⚠ Đổi ở đây, chỗ mọi file đều đi qua — không có bảng này thì mở sơ đồ cũ ra là
#: `atr_bps` thành "không có trong kho" và validator xoá sạch khối.
THANH_DON_VI = {
    "atr_bps": ("atr", "bps"),
    "zone_range_atr": ("zone_range", "atr"),
}


def _doi_ten_cu(doc):
    """Đổi tên toán hạng/tham số cũ sang tên mới, tại chỗ."""
    for t in doc.get("tham_so") or []:
        if isinstance(t, dict) and t.get("ten") in TEN_THAM_SO_CU:
            t["ten"] = TEN_THAM_SO_CU[t["ten"]]
    for tab in TABS:
        for st in (doc.get(tab) or {}).get("steps") or []:
            if not isinstance(st, dict):
                continue
            for c in st.get("conditions") or []:
                for ve in ("trai", "phai"):
                    v = (c or {}).get(ve)
                    if isinstance(v, dict) and v.get("ten") in TEN_CU:
                        v["ten"] = TEN_CU[v["ten"]]
                    # `atr_bps < 7`  →  `atr < 7 [bps]`. Chỉ đặt đơn vị cho VẾ TRÁI:
                    # đơn vị thuộc về vế được quy đổi, không thuộc về điều kiện.
                    if isinstance(v, dict) and v.get("ten") in THANH_DON_VI:
                        ten_moi, dv = THANH_DON_VI[v["ten"]]
                        v["ten"] = ten_moi
                        if ve == "trai":
                            c["don_vi"] = dv
                    for k in ("period", "tf"):
                        if isinstance(v, dict) and v.get(k) in TEN_THAM_SO_CU:
                            v[k] = TEN_THAM_SO_CU[v[k]]
                if c.get("phai_loai") == "tham_so" and c.get("phai") in TEN_THAM_SO_CU:
                    c["phai"] = TEN_THAM_SO_CU[c["phai"]]
                if c.get("don_vi") in DON_VI_CU:
                    c["don_vi"] = DON_VI_CU[c["don_vi"]]
            for k in ("dem", "sl", "tp", "khoang"):
                x = st.get(k)
                if not isinstance(x, dict):
                    continue
                if x.get("value") in TEN_THAM_SO_CU:
                    x["value"] = TEN_THAM_SO_CU[x["value"]]
                # HAI bảng đơn vị gộp làm một → đổi tên ở đây, chỗ mọi file đều qua.
                if x.get("tinh") in DON_VI_CU:
                    x["tinh"] = DON_VI_CU[x["tinh"]]
            if st.get("lot") in TEN_THAM_SO_CU:
                st["lot"] = TEN_THAM_SO_CU[st["lot"]]
    return doc


def normalize_process(doc):
    doc = _doi_ten_cu(doc or {})
    # ⚠ CHẶN file của bản MỚI HƠN. `normalize_action` trả None cho mọi `type` lạ và
    # `_chuan_so_do` lọc `if x`, nên khối BIẾN MẤT — kéo theo cả hai đường nối bám vào
    # nó, tức chuỗi bị CẮT ĐÔI. Rồi Ctrl+S ghi đè bản đã mất khối: hỏng vĩnh viễn, im
    # lặng. `validate_actions` có sẵn câu 'Loại hành động "…" không còn được hỗ trợ'
    # nhưng nó không bao giờ hiện được, vì mọi doc tới tay validator đều đã qua đây và
    # khối đã bị xoá trước. Chặn, đừng cố cứu — `@_bat_loi` bên `api` sẽ đưa câu này lên
    # giao diện.
    v = doc.get("schema")
    if isinstance(v, int) and not isinstance(v, bool) and v > SCHEMA:
        raise ValueError(
            f"File này thuộc bản mới hơn (schema {v}, app đang hiểu {SCHEMA}). "
            f"Cập nhật app rồi mở lại — mở bằng bản cũ sẽ MẤT những khối nó chưa biết.")
    # File schema 1 chỉ có MỘT sơ đồ ở gốc — nhận nó làm Entry. Rẻ, và mở lại được
    # mọi thứ đã lưu trước khi tách hai tab.
    if "steps" in doc and TAB_ENTRY not in doc:
        doc = dict(doc, entry={"steps": doc.get("steps"), "edges": doc.get("edges")})
    ra = {
        "schema": SCHEMA,
        "type": "strategy",
        "name": (doc.get("name") or "").strip() or "Chiến lược 1",
        "symbol": (doc.get("symbol") or "").strip() or "XAUUSD",
        "tham_so": normalize_tham_so(doc.get("tham_so")),
    }
    # DI CƯ schema ≤3 → 4: `doc["timeframe"]` là MỘT nhịp cho cả tài liệu, giờ mỗi sơ đồ
    # một nhịp trên chính khối Bắt đầu. File cũ lấy nhịp đó cho Entry; Manage nhận mặc
    # định M1 vì đó mới là nhịp đúng của nó (xem `NHIP_MAC_DINH`), và không có bộ chạy
    # nào từng chạy file cũ nên không phá kết quả của ai.
    cu = doc.get("timeframe")
    for tab in TABS:
        mac_dinh = NHIP_MAC_DINH[tab]
        if tab == TAB_ENTRY and cu in TIMEFRAMES:
            mac_dinh = cu
        ra[tab] = _chuan_so_do(doc.get(tab), mac_dinh)

    # ĐƠN VỊ CÒN TRỐNG THÌ SUY TỪ CHỖ DÙNG. Cột này mới thành khoá (trước là chữ tự do
    # ai gõ gì cũng được), nên mọi file cũ đều có dòng rỗng. Không đi hỏi người dùng
    # từng dòng: thông tin nằm sẵn ở chỗ dùng tham số ấy, và ô ở đó mới là nơi định
    # nghĩa đơn vị. Dùng ở HAI ô khác đơn vị thì để trống — `validate_process` mắng,
    # vì đoán bừa một trong hai là âm thầm đổi nghĩa một con số.
    dang_dung = _don_vi_dang_dung(ra)
    for t in ra["tham_so"]:
        if not t["don_vi"]:
            ds = dang_dung.get(t["ten"]) or set()
            if len(ds) == 1:
                t["don_vi"] = next(iter(ds))
    return ra


def new_process():
    """Chiến lược mới — HAI sơ đồ, mỗi cái có sẵn khối Bắt đầu.

    Không mở ra canvas trắng trơn: khối Bắt đầu là điểm neo đánh số, thiếu nó thì khối
    đầu tiên người dùng thả ra sẽ tự nhận số 1 rồi đổi số ngay khi họ thả khối thứ hai
    lên phía trên nó."""
    s = load_settings()
    ra = {"schema": SCHEMA, "type": "strategy", "name": "Chiến lược 1",
          "symbol": s.get("symbol", "XAUUSD"), "tham_so": []}
    for tab, ten in ((TAB_ENTRY, "Tìm tín hiệu vào lệnh"),
                     (TAB_MANAGE, "Với TỪNG lệnh đang sống")):
        bd = make_start_step(ten, NHIP_MAC_DINH[tab])
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
