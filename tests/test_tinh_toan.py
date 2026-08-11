"""Chỉ báo — phải khớp MT5, không phải khớp sách giáo khoa.

Con số của D_02 (ngưỡng 7,0 bps · MA 50 · ATR 14) được dò ra trên `iATR`/`iMA` của MT5.
Cài "đúng theo sách" mà lệch MT5 thì mọi tham số đã tinh chỉnh đều mất nghĩa, và lệch
kiểu đó KHÔNG báo lỗi — chỉ ra một đường vốn khác.

Bốn thứ bài này canh:

  1. **ATR là SMA của True Range**, không phải Wilder. Wilder cho số lớn hơn ở cùng chu
     kỳ, nên nến nào là "nến nén" sẽ khác.
  2. **Vùng chưa đủ dữ liệu là NaN, không phải 0.** `0` lọt qua mọi phép so.
  3. **Gộp khung theo BIÊN THỜI GIAN**, không phải đếm 5 nến — dữ liệu thật đầy lỗ hổng.
  4. **Khung lớn không được nhìn trước tương lai**: tại thời điểm T chỉ thấy nến khung
     lớn đã ĐÓNG.

Chạy:  python tests\\test_tinh_toan.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import nguon_nen as nn  # noqa: E402
from cat_studio import tinh_toan as tt  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def gan(a, b, sai_so=1e-9):
    return abs(float(a) - float(b)) <= sai_so


def nen(ts, o, h, l, c, vol=None):
    a = np.empty(len(ts), dtype=nn.DTYPE)
    a["t"], a["o"], a["h"], a["l"], a["c"] = ts, o, h, l, c
    a["vol"] = 1 if vol is None else vol
    return a


# ================= 1. True Range =================
print("\n▸ True Range")
h = [10, 12, 11, 15]
l = [8, 9, 7, 13]
c = [9, 11, 8, 14]
tr = tt.true_range(h, l, c)
kiem("TR[0] là NaN — nó cần Close của nến TRƯỚC, mà nến trước không tồn tại",
     bool(np.isnan(tr[0])))
# nến 1: max(12, c0=9) − min(9, 9)  = 12 − 9 = 3
# nến 2: max(11, c1=11) − min(7, 11)  = 11 − 7 = 4
# nến 3: max(15, c2=8)  − min(13, 8)  = 15 − 8 = 7   ← KHÔNG phải 15 − 13.
#        Đây chính là điểm của True Range: nến 3 mở GAP hẳn lên trên close trước, và TR
#        phải ôm cả cú nhảy đó. Dùng High − Low (= 2) là bỏ qua đúng phần biến động lớn
#        nhất, và ATR sẽ nhỏ hơn thật ở đúng những nến quan trọng nhất.
kiem("TR ôm cả GAP: max(High, Close trước) − min(Low, Close trước)",
     gan(tr[1], 3) and gan(tr[2], 4) and gan(tr[3], 7),
     f"— {[round(float(x), 3) for x in tr[1:]]}")

# ================= 2. ATR =================
print("\n▸ ATR — SMA của True Range, đúng iATR của MT5")
n = 60
rng = np.random.default_rng(7)
hh = 100 + np.cumsum(rng.normal(0, 0.5, n))
ll = hh - np.abs(rng.normal(0, 0.4, n)) - 0.1
cc = (hh + ll) / 2
a = tt.atr(hh, ll, cc, 14)

kiem("14 giá trị đầu là NaN — giá trị THẬT đầu tiên nằm ở chỉ số 14 (ATR.mq5:83)",
     bool(np.all(np.isnan(a[:14]))) and np.isfinite(a[14]))
tr = tt.true_range(hh, ll, cc)
kiem("ATR[14] = trung bình cộng TR[1..14]", gan(a[14], np.mean(tr[1:15]), 1e-12))
kiem("ATR[i] = cửa sổ trượt, KHÔNG phải Wilder",
     gan(a[30], np.mean(tr[17:31]), 1e-12))
# Wilder cùng chu kỳ cho một con số KHÁC — nếu hai cái trùng nhau thì bài kiểm này vô nghĩa.
w = np.mean(tr[1:15])
for i in range(15, 31):
    w = w + (tr[i] - w) / 14
kiem("và Wilder cho số KHÁC hẳn — nên chép nhầm là lệch thật",
     not gan(a[30], w, 1e-6), f"— SMA {a[30]:.4f} vs Wilder {w:.4f}")

print("\n▸ ATR chuẩn hoá (bps)")
b = tt.atr_bps(hh, ll, cc, 14)
kiem("= ATR / Close × 10000", gan(b[20], a[20] / cc[20] * 10000, 1e-9))
kiem("cùng vùng NaN với ATR — không tự bịa ra số ở chỗ chưa có dữ liệu",
     bool(np.all(np.isnan(b[:14]))))
# Đây là lý do luật "NaN chứ không 0" quan trọng: cổng nén hỏi `atr_bps < 7`.
kiem("NaN làm phép so trả FALSE → cổng TRƯỢT (0 thì cổng KHỚP, sai chết người)",
     not bool(b[0] < 7.0) and bool(0.0 < 7.0))

# ================= 3. MA =================
print("\n▸ MA — bốn kiểu, đều khởi động bằng SMA")
x = np.arange(1, 21, dtype=float)
for k in ("SMA", "EMA", "SMMA", "LWMA"):
    m = tt.ma(x, 5, k)
    kiem(f"{k}: 4 giá trị đầu NaN, giá trị đầu tiên ở chỉ số 4",
         bool(np.all(np.isnan(m[:4]))) and np.isfinite(m[4]))
# EMA/SMMA là đệ quy nên PHẢI có mồi; MT5 mồi bằng SMA chứ không bằng phần tử đầu.
# LWMA không đệ quy — giá trị đầu của nó vốn đã là trung bình CÓ TRỌNG SỐ (55/15).
kiem("EMA và SMMA mồi bằng SMA(5) = 3.0, không phải bằng phần tử đầu",
     all(gan(tt.ma(x, 5, k)[4], 3.0) for k in ("SMA", "EMA", "SMMA")))
kiem("LWMA thì không — nó có trọng số ngay từ giá trị đầu (55/15)",
     gan(tt.ma(x, 5, "LWMA")[4], 55 / 15))
kiem("SMA đúng trung bình cộng", gan(tt.ma(x, 5, "SMA")[9], np.mean(x[5:10])))
kiem("LWMA nặng về nến mới nên LỚN hơn SMA trên chuỗi tăng",
     tt.ma(x, 5, "LWMA")[9] > tt.ma(x, 5, "SMA")[9])
kiem("EMA đuổi giá nhanh hơn SMMA (alpha 2/(n+1) > 1/n)",
     tt.ma(x, 5, "EMA")[9] > tt.ma(x, 5, "SMMA")[9])
kiem("chuỗi ngắn hơn chu kỳ → toàn NaN, không nổ",
     bool(np.all(np.isnan(tt.ma([1, 2], 5, "SMA")))))

# ================= 4. Donchian & volume =================
print("\n▸ Donchian · Volume MA")
kiem("biên trên = max(High) N nến", gan(tt.donchian_tren([1, 5, 3, 2], 3)[2], 5))
kiem("biên dưới = min(Low) N nến", gan(tt.donchian_duoi([4, 1, 3, 2], 3)[3], 1))
kiem("volume MA = trung bình N nến", gan(tt.volume_ma([10, 20, 30], 3)[2], 20))

# ================= 5. Gộp khung =================
print("\n▸ Gộp khung — theo BIÊN THỜI GIAN, không phải đếm nến")
ts = np.arange(0, 10 * 60, 60)                       # 10 nến M1 từ 00:00
m1 = nen(ts, np.arange(10.), np.arange(10.) + 1, np.arange(10.) - 1, np.arange(10.))
m5 = tt.gop(m1, "M5")
kiem("10 nến M1 → 2 nến M5", len(m5) == 2, f"— {len(m5)}")
kiem("open lấy nến đầu ô, close lấy nến cuối ô",
     gan(m5["o"][0], 0) and gan(m5["c"][0], 4)
     and gan(m5["o"][1], 5) and gan(m5["c"][1], 9))
kiem("high = max cả ô, low = min cả ô",
     gan(m5["h"][0], 5) and gan(m5["l"][0], -1))
kiem("volume cộng dồn", int(m5["vol"][0]) == 5)

# Đây là ca dữ liệu THẬT: một tháng XAUUSD có 26 lỗ hổng, dài nhất 51 giờ.
thung = np.concatenate([np.arange(0, 3 * 60, 60), np.arange(7 * 60, 10 * 60, 60)])
m1t = nen(thung, np.zeros(6), np.ones(6), -np.ones(6), np.zeros(6))
m5t = tt.gop(m1t, "M5")
kiem("có LỖ HỔNG vẫn ra đúng biên ô (00:00 và 00:05), không lệch pha",
     [int(v) for v in m5t["t"]] == [0, 300], f"— {[int(v) for v in m5t['t']]}")
# Phút 5 và 6 thủng, ô vẫn phải mang mốc 300 (00:05) chứ không phải 420 (00:07).
kiem("ô thiếu phút đầu vẫn mang MỐC CỦA Ô, không mang mốc nến M1 đầu tiên",
     int(tt.gop(nen(np.array([7, 8, 9]) * 60, *[np.zeros(3)] * 4), "M5")["t"][0]) == 300)
kiem("cuối tuần KHÔNG đẻ ra nến rỗng — ô không có nến M1 nào thì không tồn tại",
     len(m5t) == 2)
# Đã đo trên dữ liệu thật: tải M1 tới đúng 2025-12-02 00:00 thì ô M5 00:00–00:04 chỉ có
# 1/5 phút, và nến gộp lệch hẳn nến M5 của MT5 (close 4225.331 vs 4225.692). Giữ nó lại
# là bộ chạy đọc một cây nến CHƯA ĐÓNG như thể đã đóng.
do_dang = nen(np.arange(0, 7 * 60, 60), *[np.zeros(7)] * 4)   # 7 phút = ô 2 mới có 2/5
kiem("ô CUỐI dở dang thì BỎ — không đọc nến chưa đóng",
     [int(v) for v in tt.gop(do_dang, "M5")["t"]] == [0],
     f'— {[int(v) for v in tt.gop(do_dang, "M5")["t"]]}')
kiem("dữ liệu dừng ĐÚNG mép ô thì ô cuối vẫn được giữ",
     len(tt.gop(nen(np.arange(0, 10 * 60, 60), *[np.zeros(10)] * 4), "M5")) == 2)
kiem("ô GIỮA thiếu vài phút vẫn giữ — nó đã đóng thật, sàn cũng dựng vậy",
     len(tt.gop(nen(np.array([0, 60, 300, 360, 600, 660, 720, 780, 840, 899]),
                    *[np.zeros(10)] * 4), "M5")) == 3)
kiem("chart muốn thấy cây nến đang chạy thì xin `giu_nen_do_dang=True`",
     len(tt.gop(do_dang, "M5", giu_nen_do_dang=True)) == 2)
kiem("gộp lên M1 là phép đồng nhất", tt.gop(m1, "M1") is m1)
kiem("mảng rỗng không nổ", len(tt.gop(np.empty(0, dtype=nn.DTYPE), "M15")) == 0)

# ================= 6. Không nhìn trước tương lai =================
print("\n▸ Khung lớn KHÔNG được nhìn trước tương lai")
ts = np.arange(0, 60 * 60, 60)                       # 60 nến M1 = 1 giờ
gia = np.arange(60, dtype=float)
m1 = nen(ts, gia, gia, gia, gia)
m5, m15 = tt.gop(m1, "M5"), tt.gop(m1, "M15")
v15 = m15["c"].astype(float)
tren_m5 = tt.theo_truc(v15, tt.moc_dong(m15, "M15"), tt.moc_dong(m5, "M5"))

kiem("hai nến M5 đầu chưa có nến M15 nào ĐÓNG → NaN, không mượn tạm giá trị nào",
     bool(np.all(np.isnan(tren_m5[:2]))), f"— {tren_m5[:3]}")
kiem("nến M5 đóng lúc 00:15 thấy đúng nến M15 vừa đóng (close = 14)",
     gan(tren_m5[2], 14), f"— {tren_m5[2]}")
kiem("suốt ba nến M5 tiếp theo GIỮ NGUYÊN giá trị cũ (FilterEngine.mqh:316-318)",
     gan(tren_m5[3], 14) and gan(tren_m5[4], 14),
     f"— {[round(float(v), 1) for v in tren_m5[2:6]]}")
kiem("sang nến M15 mới mới đổi giá trị", gan(tren_m5[5], 29), f"— {tren_m5[5]}")
kiem("KHÔNG BAO GIỜ thấy giá trị của nến M15 chưa đóng",
     not any(gan(tren_m5[i], 14) for i in range(2) if np.isfinite(tren_m5[i])))

# ================= 7. cửa gọi chung =================
print("\n▸ Cửa gọi chung")
kiem("tra bảng theo tên", np.isfinite(tt.tinh("atr", m1, 5)[10]))
# ⚠ KHÔNG đo trên `m1` (giá tăng tuyến tính): trên một đường thẳng, EMA và SMA có cùng
# độ trễ nên ra CÙNG một số, và bài kiểm sẽ luôn sai dù code đúng.
mn = nen(np.arange(60) * 60, hh, hh, ll, cc)
kiem("MA nhận thêm `method` — EMA khác SMA trên giá thật",
     not gan(tt.tinh("ma", mn, 5, method="EMA")[30], tt.tinh("ma", mn, 5)[30]),
     f'— EMA {tt.tinh("ma", mn, 5, method="EMA")[30]:.4f} '
     f'vs SMA {tt.tinh("ma", mn, 5)[30]:.4f}')
try:
    tt.tinh("chua_co", m1, 5)
    ok = False
except ValueError as e:
    ok = "chua_co" in str(e)
kiem("chỉ báo chưa cài → nổ NGAY kèm tên, không âm thầm trả 0", ok)

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
