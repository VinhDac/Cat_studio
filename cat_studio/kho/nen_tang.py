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
TOAN_HANG = [
    # ---- Giá ----
    {"key": "close", "nhan": "Giá đóng cửa", "nhom": "Giá",
     "tham_so": ["tf", "shift"],
     "mo_ta": "Dùng nến[1] để đọc nến ĐÃ ĐÓNG — nến 0 còn chạy nên tín hiệu sẽ vẽ lại."},
    {"key": "open", "nhan": "Giá mở cửa", "nhom": "Giá", "tham_so": ["tf", "shift"]},
    {"key": "high", "nhan": "Giá cao nhất", "nhom": "Giá", "tham_so": ["tf", "shift"]},
    {"key": "low", "nhan": "Giá thấp nhất", "nhom": "Giá", "tham_so": ["tf", "shift"]},
    {"key": "bid", "nhan": "Giá Bid", "nhom": "Giá", "tham_so": []},
    {"key": "ask", "nhan": "Giá Ask", "nhom": "Giá", "tham_so": []},
    {"key": "spread", "nhan": "Spread (điểm)", "nhom": "Giá", "tham_so": [],
     "mo_ta": "Đơn vị ĐIỂM — đây là chuyện khớp lệnh của sàn, không phải đơn vị chiến "
              "lược. Đừng lấy nó làm khoảng cách SL/TP."},

    # ---- Tài khoản ----
    {"key": "so_vi_the", "nhan": "Số vị thế đang mở", "nhom": "Tài khoản",
     "tham_so": [], "mo_ta": "= CountOpenPositions() của D_02."},
    {"key": "so_lenh_cho", "nhan": "Số lệnh chờ", "nhom": "Tài khoản", "tham_so": [],
     "mo_ta": "D_02 chỉ cho ĐÚNG MỘT lệnh chờ sống một lúc (`if(m_has_pending) return`)."},
    {"key": "so_lenh_hom_nay", "nhan": "Số lệnh hôm nay", "nhom": "Tài khoản",
     "tham_so": []},
    {"key": "drawdown_pt", "nhan": "Drawdown (%)", "nhom": "Tài khoản", "tham_so": []},

    # ---- Lệnh này — CHỈ sơ đồ Manage ----
    # Manage chạy một lượt cho MỖI lệnh đang sống, nên "lệnh này" luôn có nghĩa ở đó.
    # Ở Entry thì chưa có lệnh nào để nói tới → soát tĩnh báo lỗi.
    {"key": "lenh_da_khop", "nhan": "Lệnh này đã khớp", "nhom": "Lệnh này",
     "tham_so": [], "dung_sai": True, "tabs": ["manage"]},
    {"key": "lenh_la_mua", "nhan": "Lệnh này là lệnh Mua", "nhom": "Lệnh này",
     "tham_so": [], "dung_sai": True, "tabs": ["manage"]},
    {"key": "lenh_sl_hoa_von", "nhan": "SL của lệnh này đã ở hoà vốn",
     "nhom": "Lệnh này", "tham_so": [], "dung_sai": True, "tabs": ["manage"],
     "mo_ta": "= `if(sl >= entry && sl > 0) continue` của ManageBreakEven, đảo lại. "
              "Thiếu nó thì Manage bắn lệnh sửa SL lại mỗi nến."},
    {"key": "lenh_lai_R", "nhan": "Lãi của lệnh này (× R)", "nhom": "Lệnh này",
     "tham_so": [], "tabs": ["manage"],
     "mo_ta": "R = khoảng cách SL lúc VÀO LỆNH, chốt cứng theo lệnh — không tính lại."},
    {"key": "lenh_so_nen_song", "nhan": "Số nến lệnh này đã sống", "nhom": "Lệnh này",
     "tham_so": [], "tabs": ["manage"]},
    {"key": "lenh_gia_vao", "nhan": "Giá vào của lệnh này", "nhom": "Lệnh này",
     "tham_so": [], "tabs": ["manage"]},

    # ---- Thời gian ----
    {"key": "gio", "nhan": "Giờ (0–23)", "nhom": "Thời gian", "tham_so": []},
    {"key": "thu", "nhan": "Thứ (2–8)", "nhom": "Thời gian", "tham_so": []},
]
