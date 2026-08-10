"""Engine D_02 — Compress: nén biến động rồi phá vùng.

Nguồn: `MQL5\\Experts\\D_02_Compress\\Include\\Controller\\FilterEngine.mqh`

Engine này đóng góp đúng HAI thứ, và cả hai đều là ý tưởng RIÊNG của D_02:

  1. `atr_bps` — ATR chuẩn hoá theo giá: (ATR / close) × 10⁴.
     Đây là "một ngưỡng cho mọi thang giá". `ATR_Threshold_Bps = 7` nghĩa là "biến động
     dưới 0,07 % giá" trên MỌI chart — vàng $2.400 hay EURUSD 1,10 đều vậy.

  2. Bảng trạng thái `vung_nen` — thứ engine TỰ NUÔI qua thời gian, không tính được từ
     một nến đơn lẻ: đếm nến nén liên tiếp, theo dõi đỉnh/đáy, cộng dồn ATR.

Máy trạng thái 5 giá trị của bản gốc (`IDLE / COUNTING / CONFIRMED / PENDING /
CONSUMED`) KHÔNG được chép sang. Nó tồn tại vì MQL5 không có đồ thị — mỗi tick hàm chạy
lại từ đầu nên phải tự nhớ đang ở đâu. Ta có đồ thị, nên:

  IDLE / COUNTING  ->  `so_nen_nen` chưa đủ K
  CONFIRMED        ->  cổng "Vùng nén đã xác nhận?" khớp
  PENDING          ->  `so_lenh_cho == 1`
  CONSUMED         ->  `vung_da_sinh_lenh` — mà cái này lại chỉ là một phép TRA BẢNG:
                       có lệnh nào mang `vung_id` của vùng hiện hành không.
"""

TEN = "D_02 Compress"
MA_SO = "d02"
MO_TA = ("Nén biến động (ATR chuẩn hoá theo bps) → đặt lệnh chờ ngay mép vùng → "
         "phá ra là khớp. Hướng do MA khung lớn quyết.")
NGUON = r"MQL5\Experts\D_02_Compress"

CHI_BAO = [
    {"key": "atr_bps", "nhan": "ATR chuẩn hoá (bps)", "tham_so": ["tf", "period"],
     "cong_thuc": "(ATR / Close[1]) × 10000",
     "mo_ta": "1 bps = 0,01 % giá. Ngưỡng 7 = biến động dưới 0,07 % giá — cùng một "
              "con số mang cùng một ý nghĩa trên mọi symbol."},
]

# Bảng engine tự nuôi. Runtime cập nhật MỘT LẦN mỗi nến, trước khi chạy sơ đồ nào.
BANG_TRANG_THAI = [{
    "key": "vung_nen",
    "nhan": "Vùng nén",
    "mo_ta": "Sinh ra khi atr_bps tụt dưới ngưỡng, chết khi bung lên lại. Mỗi vùng "
             "mang một id riêng — lệnh đặt từ vùng nào thì ghi id vùng đó, nên "
             "\"một cú nén một lệnh\" là phép tra bảng chứ không phải cờ ẩn.",
    "truong": [
        {"ten": "id", "kieu": "chuỗi", "vd": "V-0003"},
        {"ten": "so_nen", "kieu": "số nguyên", "vd": "12"},
        {"ten": "dinh / day", "kieu": "giá", "vd": "2412.80 / 2409.15"},
        {"ten": "atr_tb", "kieu": "giá",
         "vd": "trung bình ATR suốt cả vùng — dùng để đo 1R"},
        {"ten": "atr_hien_tai", "kieu": "giá",
         "vd": "ATR nến mới nhất — dùng để đo đệm vào lệnh"},
        {"ten": "song", "kieu": "đúng/sai", "vd": "còn nén hay đã tan"},
    ],
    "luat": [
        "Nến nén = atr_bps < ngưỡng. Đọc ở nến ĐÃ ĐÓNG [1], không repaint.",
        "Đỉnh/đáy lấy từ High/Low của chính những nến nén đó.",
        "atr_hien_tai và atr_tb là HAI thứ khác nhau — xem `cach_tinh` "
        "`theo_ATR` vs `theo_ATR_vung`.",
        "atr_bps ≥ ngưỡng → vùng CHẾT ngay, dù đang có lệnh chờ treo.",
    ],
}]

TOAN_HANG = [
    {"key": "atr_bps", "nhan": "ATR chuẩn hoá (bps)", "nhom": "Chỉ báo",
     "tham_so": ["tf", "period"],
     "mo_ta": "(ATR / Close[1]) × 10000 — ngưỡng dùng chung cho mọi thang giá."},

    {"key": "so_nen_nen", "nhan": "Số nến nén liên tiếp", "nhom": "Vùng nén",
     "tham_so": [], "mo_ta": "= `bar_count`. Đủ K nến thì vùng được xác nhận."},
    {"key": "dinh_vung", "nhan": "Đỉnh vùng", "nhom": "Vùng nén", "tham_so": [],
     "mo_ta": "Lệnh chờ MUA neo vào đây."},
    {"key": "day_vung", "nhan": "Đáy vùng", "nhom": "Vùng nén", "tham_so": [],
     "mo_ta": "Lệnh chờ BÁN neo vào đây."},
    {"key": "rong_vung", "nhan": "Bề rộng vùng", "nhom": "Vùng nén", "tham_so": []},
    {"key": "rong_vung_atr", "nhan": "Bề rộng vùng ÷ ATR", "nhom": "Vùng nén",
     "tham_so": [],
     "mo_ta": "Bộ lọc chống vùng do tin tức thổi rộng. D_02 luôn bật, không tắt được."},
    {"key": "atr_tb_vung", "nhan": "ATR trung bình của vùng", "nhom": "Vùng nén",
     "tham_so": [], "mo_ta": "Đo mức nhiễu thật suốt cú nén → dùng nó định nghĩa 1R."},
    {"key": "vung_da_sinh_lenh", "nhan": "Vùng này đã sinh lệnh", "nhom": "Vùng nén",
     "tham_so": [], "dung_sai": True,
     "mo_ta": "Thay cho `COMP_CONSUMED`. Không phải cờ ẩn: là phép tra sổ lệnh xem có "
              "lệnh nào mang `vung_id` của vùng hiện hành không."},
]

# Bộ tham số mặc định của D_02 — dùng làm bảng tham số cho chiến lược mẫu.
# Mỗi con số PHẢI có đơn vị chuẩn hoá: bps của giá, bội ATR, bội R, hoặc số nến.
# KHÔNG pip, KHÔNG đô — đó là hợp đồng làm nên D_02.
THAM_SO_MAC_DINH = [
    {"ten": "nguong_nen_bps", "nhan": "Ngưỡng nén", "gia_tri": 7.0, "don_vi": "bps",
     "ghi_chu": "Nhỏ hơn ⇒ nén chặt hơn ⇒ ít tín hiệu nhưng chất hơn."},
    {"ten": "so_nen_nen", "nhan": "Số nến nén cần có", "gia_tri": 10, "don_vi": "nến",
     "ghi_chu": "K — lò xo càng dài càng hiếm nhưng càng mạnh."},
    {"ten": "rong_vung_toi_da", "nhan": "Bề rộng vùng tối đa", "gia_tri": 4.0,
     "don_vi": "× ATR", "ghi_chu": "Loại vùng bị tin tức thổi rộng."},
    {"ten": "dem_vao_lenh", "nhan": "Đệm vào lệnh", "gia_tri": 0.10, "don_vi": "× ATR",
     "ghi_chu": "Lá chắn mỏng ngoài mép vùng, lọc một nhịp phá giả."},
    {"ten": "sl_theo_atr_vung", "nhan": "Stop Loss", "gia_tri": 1.5,
     "don_vi": "× ATR vùng", "ghi_chu": "ĐỊNH NGHĨA 1R."},
    {"ten": "ty_le_RR", "nhan": "Tỉ lệ R:R", "gia_tri": 2.0, "don_vi": "× R"},
    {"ten": "hoa_von_tai", "nhan": "Mốc dời SL về hoà vốn", "gia_tri": 1.0,
     "don_vi": "× R"},
    {"ten": "so_vi_the_toi_da", "nhan": "Số vị thế tối đa", "gia_tri": 3,
     "don_vi": "lệnh", "ghi_chu": "= Max_Positions. Bằng nhau là đã đầy."},
    {"ten": "chu_ky_atr", "nhan": "Chu kỳ ATR", "gia_tri": 14, "don_vi": "nến"},
    {"ten": "chu_ky_ma", "nhan": "Chu kỳ MA xu hướng", "gia_tri": 50, "don_vi": "nến"},
    {"ten": "lot", "nhan": "Khối lượng", "gia_tri": 0.01, "don_vi": "lot",
     "ghi_chu": "D_02 dùng lot cố định — ĐỪNG tối ưu nó, lot to là đòn bẩy chứ không "
                "phải lợi thế."},
]
