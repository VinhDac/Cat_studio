"""Kho CHỈ BÁO CHUẨN — thứ tính được từ nến, không mang ý tưởng chiến lược nào.

ATR, MA, Donchian, Volume MA. Chúng ở đây chứ không nằm trong `engine_d02.py` vì D_02
không phát minh ra ATR — nó chỉ DÙNG. Engine nào cũng dùng được, và thêm một chiến
lược mới không phải chép lại.

Ngược lại, `atr_bps` (ATR chia giá, nhân 10⁴) thì NẰM TRONG engine D_02: đó chính là ý
tưởng riêng của nó, không phải một chỉ báo phổ thông.
"""

TEN = "Chỉ báo chuẩn"
MA_SO = "chi_bao"
MO_TA = "ATR · MA · Donchian · Volume MA — tính thẳng từ nến, ai dùng cũng được."

CHI_BAO = [
    {"key": "atr", "nhan": "ATR", "tham_so": ["tf", "period"],
     "cong_thuc": "Trung bình True Range theo Wilder",
     "mo_ta": "Đo BỀ RỘNG một nến, tính bằng đơn vị giá. D_02 đọc ở nến đã đóng [1]."},
    {"key": "ma", "nhan": "Đường trung bình MA", "tham_so": ["tf", "period", "method"],
     "cong_thuc": "SMA / EMA / SMMA / LWMA trên giá đóng cửa",
     "mo_ta": "D_02 dùng SMA(50) trên khung Trend để chọn hướng."},
    {"key": "donchian_tren", "nhan": "Donchian — biên trên", "tham_so": ["tf", "period"],
     "cong_thuc": "max(High) trong N nến"},
    {"key": "donchian_duoi", "nhan": "Donchian — biên dưới", "tham_so": ["tf", "period"],
     "cong_thuc": "min(Low) trong N nến"},
    {"key": "volume_ma", "nhan": "Volume trung bình", "tham_so": ["tf", "period"],
     "cong_thuc": "Trung bình tick volume N nến"},
]

BANG_TRANG_THAI = []

# Mỗi chỉ báo đọc được thẳng làm toán hạng, cùng bộ tham số.
TOAN_HANG = [
    {"key": cb["key"], "nhan": cb["nhan"], "nhom": "Chỉ báo",
     "tham_so": cb["tham_so"], "mo_ta": cb.get("mo_ta", "")}
    for cb in CHI_BAO
]
