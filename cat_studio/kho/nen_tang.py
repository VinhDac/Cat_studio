"""Kho NỀN TẢNG — thứ MỌI chiến lược đều có, không thuộc engine nào.

Giá, thời gian, tài khoản, và "lệnh này". Bốn nhóm này không do chiến lược nào đóng
góp: chúng đến từ sàn và từ sổ lệnh của chính app. Gỡ hết engine ra thì chúng vẫn còn.

Đối lập với `engine_*.py` — mỗi engine là MỘT ý tưởng chiến lược, mang theo bảng trạng
thái riêng và những toán hạng chỉ có nghĩa khi engine đó đang chạy.
"""

TEN = "Nền tảng"
MA_SO = "nen_tang"
MO_TA = "Giá · thời gian · tài khoản · lệnh này — có sẵn cho mọi chiến lược."

# Không tính chỉ báo nào, không nuôi bảng trạng thái nào.
CHI_BAO = []
BANG_TRANG_THAI = []

# `tabs = None` nghĩa là dùng được ở cả hai sơ đồ.
#: `loai` QUYẾT ĐỊNH Ô ĐƠN VỊ — xem `core.DON_VI`.
#:
#:   `khoang_cach` — một BỀ RỘNG giá (ATR, bề rộng zone). Quy đổi được: bps, %, × ATR…
#:   `muc_gia`     — một MỨC giá (close, MA, đỉnh zone). KHÔNG quy đổi:
#:                   `close / close × 10⁴` luôn ra 10000, vô nghĩa.
#:   `dem`         — số đếm. ⚠ PHẢI khai thêm `don_vi`: `zone_dem` đếm NẾN còn
#:                   `so_vi_the` đếm LỆNH, gộp chung thì nút chọn tham số sẽ mời
#:                   "số vị thế tối đa = 3 lệnh" vào ô "zone cần bao nhiêu nến".
#:   `boi_R`       — vốn đã tính bằng R.
#:   `dung_sai`    — không có vế phải.
#:
#: Tách `muc_gia` khỏi `khoang_cach` là chỗ dễ bỏ sót nhất: cả hai đều "đơn vị giá",
#: nhưng chỉ bề rộng mới chuẩn hoá được.
#: ⚠ `shift` ĐÃ BỎ khỏi toán hạng giá, và đây là lý do.
#:
#: Nó là ô số THỨ BA trên hàng điều kiện — cùng chỗ, cùng hình dạng với ô "chu kỳ" của
#: ATR/MA, nhưng nghĩa khác hẳn. Một ô trắng không nhãn mang hai nghĩa tuỳ toán hạng thì
#: không ai đọc ra được. Bỏ nó đi, ô thứ ba chỉ còn MỘT nghĩa: chu kỳ chỉ báo.
#:
#: Bỏ được vì nó chưa từng khác 1: mẫu dùng 1, cả 10 file đã lưu đều 1, và `doc_cot`
#: hiểu "thiếu shift" ĐÚNG BẰNG shift 1 (`i -= max(0, shift-1)`), nên hành vi không đổi
#: một chút nào. Muốn so `close[1] > close[5]` thì thêm lại sau — thêm một trường dễ hơn
#: nhiều so với gỡ một trường người ta đã học.
TOAN_HANG = [
    # ---- Giá ---- (MỨC giá: so với một mức khác, không quy đổi)
    {"key": "close", "nhan": "Giá đóng cửa", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"],
     "mo_ta": "Luôn đọc nến ĐÃ ĐÓNG — nến đang chạy thì tín hiệu sẽ vẽ lại."},
    {"key": "open", "nhan": "Giá mở cửa", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"]},
    {"key": "high", "nhan": "Giá cao nhất", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"]},
    {"key": "low", "nhan": "Giá thấp nhất", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"]},

    # ---- Sổ lệnh ---- (cái gì đang TỒN TẠI)
    {"key": "so_vi_the", "nhan": "Số vị thế đang mở", "nhom": "Sổ lệnh",
     "loai": "dem", "don_vi": "lenh", "tham_so": [],
     "mo_ta": "= CountOpenPositions() của D_02."},
    {"key": "so_lenh_cho", "nhan": "Số lệnh chờ", "nhom": "Sổ lệnh", "loai": "dem",
     "don_vi": "lenh", "tham_so": [],
     "mo_ta": "D_02 chỉ cho ĐÚNG MỘT lệnh chờ sống một lúc (`if(m_has_pending) return`)."},

    # ---- Lệnh đang xét — CHỈ sơ đồ Manage ----
    # Manage chạy một lượt cho MỖI lệnh đang sống, nên "lệnh này" luôn có nghĩa ở đó.
    # Ở Entry thì chưa có lệnh nào để nói tới → soát tĩnh báo lỗi.
    {"key": "lenh_da_khop", "nhan": "Lệnh này đã khớp", "nhom": "Lệnh này",
     "loai": "dung_sai", "tham_so": [], "dung_sai": True, "tabs": ["manage"]},
    {"key": "lenh_sl_hoa_von", "nhan": "SL của lệnh này đã ở hoà vốn",
     "nhom": "Lệnh này", "loai": "dung_sai", "tham_so": [], "dung_sai": True,
     "tabs": ["manage"],
     "mo_ta": "= `if(sl >= entry && sl > 0) continue` của ManageBreakEven, đảo lại. "
              "Thiếu nó thì Manage bắn lệnh sửa SL lại mỗi nến."},
    {"key": "lenh_lai_R", "nhan": "Lãi của lệnh này (× R)", "nhom": "Lệnh này",
     "loai": "boi_R", "tham_so": [], "tabs": ["manage"],
     "mo_ta": "R = khoảng cách SL lúc VÀO LỆNH, chốt cứng theo lệnh — không tính lại."},
]
