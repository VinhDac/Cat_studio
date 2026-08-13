"""Kho CHỈ BÁO CHUẨN — thứ tính được từ nến, không mang ý tưởng chiến lược nào.

ATR và MA. Chúng ở đây chứ không nằm trong `engine_d02.py` vì D_02
không phát minh ra ATR — nó chỉ DÙNG. Engine nào cũng dùng được, và thêm một chiến
lược mới không phải chép lại.

Ngược lại, `atr_bps` (ATR chia giá, nhân 10⁴) thì NẰM TRONG engine D_02: đó chính là ý
tưởng riêng của nó, không phải một chỉ báo phổ thông.
"""

TEN = "Chỉ báo chuẩn"
MA_SO = "chi_bao"
MO_TA = "ATR · MA — tính thẳng từ nến, ai dùng cũng được."

CHI_BAO = [
    # ⚠ SMA của True Range, KHÔNG phải Wilder/SMMA. Đây là công thức của `iATR` trong
    # MT5 (`MQL5\\Indicators\\Examples\\ATR.mq5`): giá trị đầu là trung bình cộng của
    # `period` giá trị TR, các giá trị sau là cửa sổ trượt
    # `ATR[i] = ATR[i-1] + (TR[i] − TR[i-period]) / period`.
    # Chép nhầm sang Wilder là sai IM LẶNG và dây chuyền: ATR khác → `atr_bps` khác →
    # nến nào là "nến nén" khác → số nến nén, thời điểm xác nhận vùng, đỉnh/đáy vùng,
    # độ lớn 1R và TP lệch hết. Mà ngưỡng 7.0 bps được dò ra trên chính con số `iATR`
    # trả về, nên đổi công thức là ngưỡng đó mất nghĩa.
    {"key": "atr", "nhan": "ATR", "tham_so": ["tf", "period"],
     "cong_thuc": "SMA của True Range (đúng iATR của MT5 — KHÔNG phải Wilder)",
     "mo_ta": "Đo BỀ RỘNG một nến, tính bằng đơn vị giá. "
              "TR = max(High, Close[trước]) − min(Low, Close[trước]). "
              "D_02 đọc ở nến đã đóng [1]."},
    {"key": "ma", "nhan": "Đường trung bình MA", "tham_so": ["tf", "period", "method"],
     "cong_thuc": "SMA / EMA / SMMA / LWMA trên giá đóng cửa",
     "mo_ta": "D_02 dùng SMA(50) trên khung Trend để chọn hướng."},
]

BANG_TRANG_THAI = []

# Mỗi chỉ báo đọc được thẳng làm toán hạng, cùng bộ tham số.
#: ATR là BỀ RỘNG một nến → quy đổi được (bps, % giá…).
#: MA là một MỨC giá → không quy đổi, chỉ so với mức khác.
_LOAI = {"atr": "khoang_cach", "ma": "muc_gia"}

TOAN_HANG = [
    {"key": cb["key"], "nhan": cb["nhan"], "nhom": "Chỉ báo",
     "loai": _LOAI[cb["key"]],
     "tham_so": cb["tham_so"], "mo_ta": cb.get("mo_ta", "")}
    for cb in CHI_BAO
]
