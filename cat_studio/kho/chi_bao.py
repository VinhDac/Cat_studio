"""Kho CHỈ BÁO CHUẨN — thứ tính được từ nến, không mang ý tưởng chiến lược nào.

ATR và MA — hai cái, hết. Chúng ở đây vì chúng tính thẳng từ nến và ai gọi cũng được,
khác với `zone.py` (một CƠ CHẾ, chỉ có khi sơ đồ định nghĩa ra nó).

⚠ Chuẩn hoá KHÔNG nằm ở đây. `atr` nhìn bằng thước nào là chuyện của ĐƠN VỊ trên dòng
điều kiện (`atr < 0,75 [× ATR nền]`), không phải của một toán hạng riêng — nếu không thì
mỗi đại lượng lại đẻ thêm một mục `*_bps`, `*_ti_so`… và kho phình gấp đôi ở mỗi thứ.
Xem core.md §15.1.
"""

TEN = "Chỉ báo chuẩn"
MA_SO = "chi_bao"
MO_TA = "ATR · MA — tính thẳng từ nến, ai dùng cũng được."

CHI_BAO = [
    # ⚠ SMA của True Range, KHÔNG phải Wilder/SMMA. Đây là công thức của `iATR` trong
    # MT5 (`MQL5\\Indicators\\Examples\\ATR.mq5`): giá trị đầu là trung bình cộng của
    # `period` giá trị TR, các giá trị sau là cửa sổ trượt
    # `ATR[i] = ATR[i-1] + (TR[i] − TR[i-period]) / period`.
    # Chép nhầm sang Wilder là sai IM LẶNG và dây chuyền: ATR khác → nến nào là "nến
    # nén" khác → số nến nén, thời điểm xác nhận vùng, đỉnh/đáy vùng, độ lớn 1R và TP
    # lệch hết. ATR còn là MẪU SỐ của đơn vị `× ATR` và `× ATR nền`, nên đổi công thức
    # là đổi nghĩa mọi ngưỡng đã dò ra trên nó.
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
#: ATR là BỀ RỘNG một nến → quy đổi được (× ATR nền, × ATR zone…).
#: MA là một MỨC giá → không quy đổi, chỉ so với mức khác.
_LOAI = {"atr": "khoang_cach", "ma": "muc_gia"}

TOAN_HANG = [
    {"key": cb["key"], "nhan": cb["nhan"], "nhom": "Chỉ báo",
     "loai": _LOAI[cb["key"]],
     "tham_so": cb["tham_so"], "mo_ta": cb.get("mo_ta", "")}
    for cb in CHI_BAO
]
