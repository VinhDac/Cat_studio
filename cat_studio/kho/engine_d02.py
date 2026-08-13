"""Engine D_02 — Compress: nén biến động rồi phá vùng.

Nguồn: `MQL5\\Experts\\D_02_Compress\\Include\\Controller\\FilterEngine.mqh`

Engine này đóng góp đúng HAI thứ, và cả hai đều là ý tưởng RIÊNG của D_02:

  1. `atr_bps` — ATR chuẩn hoá theo giá: (ATR / close) × 10⁴.
     Đây là "một ngưỡng cho mọi thang giá". `ATR_Threshold_Bps = 7` nghĩa là "biến động
     dưới 0,07 % giá" trên MỌI chart — vàng $2.400 hay EURUSD 1,10 đều vậy.

  2. Bảng trạng thái `zone` — thứ engine TỰ NUÔI qua thời gian, không tính được từ
     một nến đơn lẻ: đếm nến nén liên tiếp, theo dõi đỉnh/đáy, cộng dồn ATR.

Máy trạng thái 5 giá trị của bản gốc (`IDLE / COUNTING / CONFIRMED / PENDING /
CONSUMED`) KHÔNG được chép sang. Nó tồn tại vì MQL5 không có đồ thị — mỗi tick hàm chạy
lại từ đầu nên phải tự nhớ đang ở đâu. Ta có đồ thị, nên:

  IDLE / COUNTING  ->  `zone_dem` chưa đủ K
  CONFIRMED        ->  cổng "Vùng nén đã xác nhận?" khớp
  PENDING          ->  `so_lenh_cho == 1`
  CONSUMED         ->  `zone_da_sinh_lenh` — mà cái này lại chỉ là một phép TRA BẢNG:
                       có lệnh nào mang `zone_id` của vùng hiện hành không.
"""

TEN = "D_02 Compress"
MA_SO = "d02"
MO_TA = ("Nén biến động (ATR chuẩn hoá theo bps) → đặt lệnh chờ ngay mép vùng → "
         "phá ra là khớp. Hướng do MA khung lớn quyết.")
NGUON = r"MQL5\Experts\D_02_Compress"

# ⚠ `atr_bps` ĐÃ RỜI KHỎI KHO — nó không phải một chỉ báo.
#
# Nó là `atr` nhìn bằng thước `bps`, tức một PHÉP QUY ĐỔI. Cất phép quy đổi thành một
# mục riêng làm kho phình gấp đôi ở mỗi đại lượng, và mỗi engine mới lại phải tự đẻ ra
# `*_bps` của mình. Giờ viết `atr < 7 [bps]` — đơn vị nằm ở dòng điều kiện.
# Cùng lý do với `zone_range_atr`, giờ là `zone_range ≤ 4 [× ATR]`.
CHI_BAO = []

# Bảng engine tự nuôi. Runtime cập nhật MỘT LẦN mỗi nến, trước khi chạy sơ đồ nào.
BANG_TRANG_THAI = [{
    "key": "zone",
    "nhan": "Zone",
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
        "atr_hien_tai và atr_tb là HAI thứ khác nhau — xem `don_vi` "
        "`atr` vs `atr_zone`.",
        "atr_bps ≥ ngưỡng → vùng CHẾT ngay, dù đang có lệnh chờ treo.",
    ],
}]

TOAN_HANG = [
    {"key": "zone_dem", "nhan": "Zone — số nến", "nhom": "Zone", "loai": "dem",
     "don_vi": "nen", "tham_so": [],
     "mo_ta": "= `bar_count`. Đủ K nến thì zone được xác nhận."},
    {"key": "zone_HH", "nhan": "Zone — đỉnh (HH)", "nhom": "Zone", "loai": "muc_gia",
     "tham_so": [], "mo_ta": "Lệnh chờ MUA neo vào đây."},
    {"key": "zone_LL", "nhan": "Zone — đáy (LL)", "nhom": "Zone", "loai": "muc_gia",
     "tham_so": [], "mo_ta": "Lệnh chờ BÁN neo vào đây."},
    # BỀ RỘNG — quy đổi được. `zone_range ≤ 4 [× ATR]` thay cho `zone_range_atr ≤ 4`.
    {"key": "zone_range", "nhan": "Zone — bề rộng", "nhom": "Zone",
     "loai": "khoang_cach", "tham_so": [],
     "mo_ta": "Lọc zone bị tin tức thổi rộng — so bằng đơn vị × ATR."},
    {"key": "zone_atr_tb", "nhan": "Zone — ATR trung bình", "nhom": "Zone",
     "loai": "khoang_cach", "tham_so": [],
     "mo_ta": "Đo mức nhiễu thật suốt cú nén → dùng nó định nghĩa 1R."},
    {"key": "zone_da_sinh_lenh", "nhan": "Zone này đã sinh lệnh", "nhom": "Zone",
     "loai": "dung_sai", "tham_so": [], "dung_sai": True,
     "mo_ta": "Thay cho `COMP_CONSUMED`. Không phải cờ ẩn: là phép tra sổ lệnh xem có "
              "lệnh nào mang `zone_id` của zone hiện hành không."},
]

# Bộ tham số mặc định của D_02 — dùng làm bảng tham số cho chiến lược mẫu.
# Mỗi con số PHẢI có đơn vị chuẩn hoá: bps của giá, bội ATR, bội R, hoặc số nến.
# KHÔNG pip, KHÔNG đô — đó là hợp đồng làm nên D_02.
#: ⚠ `don_vi` là một KHOÁ (`core.NHAN_DON_VI`), không phải chữ hiển thị. Cột này
#: từng là chữ tự do, và dòng `sl_theo_atr_vung` mang `"× ATR vùng"` — một chuỗi
#: không tồn tại ở đâu cả, rác từ lần đổi tên vùng→zone. Không ai bắt được vì hồi
#: đó chưa có gì đọc nó. Giờ nó quyết định tham số này rơi được vào ô nào.
THAM_SO_MAC_DINH = [
    {"ten": "nguong_nen_bps", "nhan": "Ngưỡng nén", "gia_tri": 7.0, "don_vi": "bps",
     "ghi_chu": "Nhỏ hơn ⇒ nén chặt hơn ⇒ ít tín hiệu nhưng chất hơn."},
    {"ten": "zone_can_nen", "nhan": "Zone cần bao nhiêu nến", "gia_tri": 10, "don_vi": "nen",
     "ghi_chu": "K — lò xo càng dài càng hiếm nhưng càng mạnh."},
    {"ten": "zone_range_max", "nhan": "Bề rộng zone tối đa", "gia_tri": 4.0,
     "don_vi": "atr", "ghi_chu": "Loại zone bị tin tức thổi rộng."},
    {"ten": "dem_vao_lenh", "nhan": "Đệm vào lệnh", "gia_tri": 0.10, "don_vi": "atr",
     "ghi_chu": "Lá chắn mỏng ngoài mép vùng, lọc một nhịp phá giả."},
    {"ten": "sl_theo_atr_vung", "nhan": "Stop Loss", "gia_tri": 1.5,
     "don_vi": "atr_zone", "ghi_chu": "ĐỊNH NGHĨA 1R."},
    {"ten": "ty_le_RR", "nhan": "Tỉ lệ R:R", "gia_tri": 2.0, "don_vi": "R"},
    {"ten": "hoa_von_tai", "nhan": "Mốc dời SL về hoà vốn", "gia_tri": 1.0,
     "don_vi": "R"},
    {"ten": "so_vi_the_toi_da", "nhan": "Số vị thế tối đa", "gia_tri": 3,
     "don_vi": "lenh", "ghi_chu": "= Max_Positions. Bằng nhau là đã đầy."},
    {"ten": "chu_ky_atr", "nhan": "Chu kỳ ATR", "gia_tri": 14, "don_vi": "nen"},
    {"ten": "chu_ky_ma", "nhan": "Chu kỳ MA xu hướng", "gia_tri": 50, "don_vi": "nen"},
    {"ten": "lot", "nhan": "Khối lượng", "gia_tri": 0.01, "don_vi": "lot",
     "ghi_chu": "D_02 dùng lot cố định — ĐỪNG tối ưu nó, lot to là đòn bẩy chứ không "
                "phải lợi thế."},
]


# ---------------------------------------------------------------------------
# MÁY VÙNG NÉN — code nằm CÙNG FILE với `BANG_TRANG_THAI["luat"]` ở trên
# ---------------------------------------------------------------------------
# Cố ý đặt ở đây chứ không trong `bo_chay.py`. Bốn câu "luật" phía trên mô tả đúng cái
# máy này bằng tiếng Việt; để code ở file khác thì sớm muộn hai bên nói khác nhau, và
# lời hứa "thêm một chiến lược = thêm MỘT file vào kho/" cũng tan.
#
# `kho/nen_tang.py` thì ngược lại — nó KHÔNG có Engine, vì giá/thời gian/tài khoản
# không phải ý tưởng của chiến lược nào.
from .. import so_lenh                                                      # noqa: E402


class Engine:
    """Nuôi bảng `zone` — thứ thay cho `ENUM_COMPRESSION_STATE` 5 giá trị của D_02.

    Bề mặt hẹp, đúng hai việc:
      * `moi_nen(ctx)` — runtime gọi MỘT LẦN mỗi nến quyết định, TRƯỚC khi chạy sơ đồ.
      * `doc(ten, ctx)` — trả giá trị cho 7 toán hạng nhóm "Vùng nén".
    """

    #: Tham số bắt buộc phải có trong bảng tham số. Thiếu là báo lỗi TRƯỚC khi chạy,
    #: chứ không phải chết ở nến thứ 40.000.
    #:
    #: ⚠ `nguong_nen_bps` ĐÃ RỜI khỏi đây. Nó từng bắt buộc vì engine tự đếm nến nén và
    #: cần biết ngưỡng. Giờ điều kiện đếm nằm trong CỔNG ZONE người dùng vẽ, nên ngưỡng
    #: là tham số của chính cổng đó — đặt tên gì cũng được, hoặc gõ số trần. Bắt buộc
    #: một cái tên cụ thể là ép mọi chiến lược phải đếm theo kiểu D_02.
    #:
    #: `chu_ky_atr` thì vẫn cần: zone cộng dồn ATR để tính `zone_atr_tb` (định nghĩa 1R).
    THAM_SO_CAN = ("chu_ky_atr",)

    def moi_nen(self, ctx):
        """Một nến quyết định vừa đóng.

        ⚠ HÀM NÀY ĐÃ RỖNG, và đó là cả điểm của lần sửa này.

        Trước đây nó là một CỖ MÁY ẨN: chạy mỗi nến, trước mọi sơ đồ, và viết cứng
        điều kiện đếm là "atr_bps dưới ngưỡng". Hậu quả:
          · nhìn sơ đồ không thấy zone sinh ra ở đâu — nó chỉ đột nhiên có;
          · chiến lược thứ hai muốn đếm theo điều kiện khác (volume thấp, nến trong
            dải Bollinger, gì cũng được) thì phải SỬA ENGINE, tức lời hứa "thêm một
            chiến lược = thêm MỘT file vào kho/" tan.

        Giờ zone do CỔNG mang cờ `cong_zone` trong chính sơ đồ định nghĩa — xem
        `bo_chay._nuoi_zone`. Điều kiện đếm thành tham số mà không cần thêm ô cấu hình
        nào: nó là cái cổng người dùng vẽ ra.

        Giữ lại hàm vì `Engine` vẫn còn việc thứ hai: `doc()` trả giá trị cho nhóm
        toán hạng "zone".
        """

    def doc(self, ten, ctx):
        """Giá trị của một toán hạng nhóm "Vùng nén" ngay lúc này.

        CHƯA CÓ VÙNG NÀO → trả `NaN` chứ không trả 0. `0` là lời nói dối lọt qua mọi
        phép so: `zone_range_atr <= 4` sẽ ĐÚNG trong lúc chẳng có vùng nén nào tồn tại."""
        so = ctx.so
        # ZONE THỬ chỉ khác `None` trong đúng lúc CỔNG ZONE đang được đánh giá — nó là
        # zone SẼ THÀNH nếu nến này được nuốt (`bo_chay._dat_zone_thu`). Mọi khối khác
        # đọc zone thật. Nhờ nó mà cổng zone hỏi được về chính zone nó sắp tạo ra.
        thu = ctx.zone_thu
        if ten == "zone_da_sinh_lenh":
            # ⚠ Phải tra theo ID CỦA BẢN THỬ. Bỏ id đi thì `zone_da_sinh_lenh()` tự lấy
            # zone hiện hành — mà lúc có lỗ hổng dữ liệu, zone hiện hành là zone CŨ (đã
            # sinh lệnh) trong khi bản thử là zone MỚI tinh. Cổng sẽ đọc "đã sinh lệnh"
            # cho một zone chưa hề tồn tại.
            return so.zone_da_sinh_lenh(thu.id) if thu is not None \
                else so.zone_da_sinh_lenh()
        v = thu if thu is not None else so.zone_hien_hanh()
        if v is None:
            return float("nan")
        return {
            "zone_dem": lambda: float(v.so_nen),
            "zone_HH": lambda: float(v.dinh),
            "zone_LL": lambda: float(v.day),
            "zone_range": lambda: float(v.rong),
            "zone_atr_tb": lambda: float(v.atr_tb),
        }[ten]()


#: Toán hạng nào do Engine trả lời. `atr_bps` KHÔNG nằm đây — nó là chỉ báo thuần,
#: `tinh_toan.py` tính, không cần biết vùng nén là gì.
ENGINE_TRA_LOI = ("zone_dem", "zone_HH", "zone_LL", "zone_range",
                  "zone_atr_tb", "zone_da_sinh_lenh")
