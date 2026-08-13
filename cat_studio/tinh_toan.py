"""Chỉ báo — hàm THUẦN: mảng nến vào, mảng số ra, cùng độ dài.

`kho/` chỉ MÔ TẢ chỉ báo bằng tiếng Việt ("SMA của True Range…") để đổ vào hộp thoại và
soát tên. Đây mới là chỗ ra CON SỐ. Cố ý tách: `kho/` là danh mục, đổi một câu mô tả
không được phép làm đổi kết quả backtest.

BA LUẬT CỦA FILE NÀY
--------------------
1. **Vùng chưa đủ dữ liệu trả `NaN`, không trả 0.** `0` là một lời nói dối lọt qua mọi
   phép so: `atr_bps < 7` sẽ ĐÚNG suốt 14 nến đầu và chiến lược vào lệnh giữa lúc chưa
   có chỉ báo nào. `NaN` thì mọi phép so đều trả False — cổng trượt, và nhật ký ghi
   được lý do.

2. **Khớp MT5, không khớp sách giáo khoa.** Con số của D_02 dò ra trên `iATR`/`iMA` của
   MT5; đúng theo sách mà lệch MT5 thì mọi tham số đã tinh chỉnh đều mất nghĩa. Chỗ nào
   MT5 làm khác thông lệ đều có chú thích kèm dòng mã gốc.

3. **Không hàm nào biết tới đồ thị, sổ lệnh hay pywebview.** Nhờ vậy kiểm thử được bằng
   vài mảng dựng tay, và sau này chạy live dùng lại nguyên vẹn.

GỘP KHUNG THỜI GIAN — CHỖ DỄ SAI NHẤT
--------------------------------------
Gộp theo **BIÊN THỜI GIAN TUYỆT ĐỐI** (`t // 300`), KHÔNG phải đếm 5 nến một cụm. Dữ
liệu M1 thật đầy lỗ hổng — cuối tuần, phiên mỏng, nến không có tick (đã đo: một tháng
XAUUSD có 26 lỗ, dài nhất 51 giờ). Đếm 5 nến một cụm thì chỉ cần một nến thiếu là mọi
nến M5 sau đó lệch pha khỏi biên thật của sàn, và không có gì báo cho biết.
"""
import numpy as np

from . import core

#: Kiểu số dùng xuyên suốt. float64 vì `atr_bps` là hiệu của hai số lớn gần bằng nhau —
#: float32 mất chữ số đúng ở chỗ quan trọng nhất.
F = np.float64


def _f(x):
    return np.asarray(x, dtype=F)


# ---------------------------------------------------------------------------
# Gộp khung thời gian
# ---------------------------------------------------------------------------
def gop(nen, tf, giu_nen_do_dang=False):
    """Gộp mảng nến M1 lên khung `tf` ("M5", "M15", …).

    Trả về mảng cùng `dtype` với đầu vào. Một nến khung lớn được tạo khi có ÍT NHẤT MỘT
    nến M1 rơi vào ô thời gian đó — đúng cách MT5 dựng nến: cuối tuần không đẻ ra nến
    rỗng, phiên mỏng thiếu vài phút vẫn ra một nến.

    `t` của nến gộp là MỐC MỞ ô (bội số của độ dài khung), không phải `t` của nến M1 đầu
    tiên có mặt. Nhờ vậy biên nến trùng khít với biên của sàn kể cả khi phút đầu ô bị
    thủng — nếu lấy nến M1 đầu tiên thì một ô mất phút :00 sẽ có mốc :01 và mọi phép
    so biên sau đó lệch.

    ⚠ **Ô CUỐI CÙNG bị BỎ nếu dữ liệu chưa chạy hết ô đó.** Đã đo trên dữ liệu thật: tải
    M1 tới đúng `2025-12-02 00:00` thì ô M5 `00:00–00:04` chỉ có 1/5 phút, và nến gộp ra
    lệch hẳn nến M5 của MT5 (close 4225.331 vs 4225.692). Giữ nó lại là bộ chạy đọc một
    cây nến CHƯA ĐÓNG như thể đã đóng — đúng loại lỗi nhìn trước tương lai mà cả kiến
    trúc này dựng lên để tránh. Bỏ đúng ô cuối chứ không bỏ ô thiếu phút ở giữa: ô giữa
    thiếu vài phút vẫn là ô đã đóng thật (sàn cũng dựng vậy), chỉ ở ô cuối ta mới không
    biết sau đó còn gì.

    `giu_nen_do_dang=True` chỉ dùng khi VẼ (chart muốn thấy cây nến đang chạy lớn dần)."""
    phut = core.TF_PHUT.get(tf)
    if phut is None:
        raise ValueError(f"Không biết khung thời gian {tf!r}")
    if not len(nen):
        return nen
    if phut == 1:
        return nen
    b = phut * 60
    o = nen["t"] // b                       # số hiệu ô thời gian
    dau = np.concatenate([[True], np.diff(o) != 0])
    i0 = np.nonzero(dau)[0]                 # chỉ số M1 mở mỗi ô
    i1 = np.append(i0[1:], len(nen))        # chỉ số kết thúc (hở)

    ra = np.empty(len(i0), dtype=nen.dtype)
    ra["t"] = o[i0] * b
    ra["o"] = nen["o"][i0]
    ra["c"] = nen["c"][i1 - 1]
    # `np.maximum.reduceat` gộp từng đoạn một lượt — vòng for Python trên 374k nến là
    # vài giây, mà bước này chạy lại mỗi lần bấm ▶.
    ra["h"] = np.maximum.reduceat(nen["h"], i0)
    ra["l"] = np.minimum.reduceat(nen["l"], i0)
    ra["vol"] = np.add.reduceat(nen["vol"], i0)

    if not giu_nen_do_dang and len(ra):
        # Nến M1 cuối cùng đóng lúc `t + 60`. Chưa chạm mép ô thì ô đó chưa đóng.
        if int(nen["t"][-1]) + 60 < int(ra["t"][-1]) + b:
            ra = ra[:-1]
    return ra


def moc_dong(nen, tf):
    """Thời điểm ĐÓNG của từng nến = mốc mở + độ dài khung.

    Cần riêng vì mọi phép "khung lớn đã đóng chưa" đều so theo giờ đóng, còn mảng nến
    lại lưu giờ MỞ. Trộn hai thứ này là nguồn gốc kinh điển của lỗi nhìn trước tương lai."""
    return _f(nen["t"]) + core.TF_PHUT[tf] * 60


def theo_truc(gia_tri, dong_nguon, dong_dich):
    """Đưa một cột của khung LỚN về trục thời gian của khung quyết định.

    > Giá trị tại thời điểm T = nến khung lớn **ĐÃ ĐÓNG** gần nhất, đóng vào lúc ≤ T.

    Đây là chỗ lỗi nhìn trước tương lai sẽ nằm nếu làm ẩu. Bản gốc chỉ tính lại MA khi
    có nến Trend TF mới và dùng lại giá trị cũ suốt các nến M5 ở giữa
    (`FilterEngine.mqh:316-318`) — hàm này tái tạo đúng hành vi đó, nhưng bằng cấu trúc
    chứ không bằng một câu guard phải nhớ.

    Chưa có nến khung lớn nào đóng thì trả `NaN` (không phải giá trị đầu tiên — dùng nó
    là đọc một con số chưa tồn tại)."""
    gia_tri, dong_nguon, dong_dich = _f(gia_tri), _f(dong_nguon), _f(dong_dich)
    i = np.searchsorted(dong_nguon, dong_dich, side="right") - 1
    ra = np.full(len(dong_dich), np.nan, dtype=F)
    co = i >= 0
    ra[co] = gia_tri[i[co]]
    return ra


# ---------------------------------------------------------------------------
# Trung bình trượt
# ---------------------------------------------------------------------------
def _tb_truot(x, n):
    """Trung bình trượt cửa sổ `n`, `n-1` phần tử đầu là NaN. Bỏ qua được NaN đầu chuỗi."""
    x = _f(x)
    if n <= 1:
        return x.copy()
    ra = np.full(len(x), np.nan, dtype=F)
    if len(x) < n:
        return ra
    cs = np.cumsum(np.nan_to_num(x, nan=0.0))
    tong = np.empty(len(x) - n + 1, dtype=F)
    tong[0] = cs[n - 1]
    tong[1:] = cs[n:] - cs[:-n]
    ra[n - 1:] = tong / n
    # Cửa sổ nào chạm phải NaN thì kết quả cũng phải là NaN — `nan_to_num` ở trên biến
    # NaN thành 0, tức là âm thầm coi "chưa có dữ liệu" bằng "giá bằng 0".
    if np.isnan(x).any():
        dem = np.cumsum(np.isnan(x).astype(np.int64))
        co_nan = np.empty(len(x) - n + 1, dtype=bool)
        co_nan[0] = dem[n - 1] > 0
        co_nan[1:] = (dem[n:] - dem[:-n]) > 0
        ra[n - 1:][co_nan] = np.nan
    return ra


def true_range(h, l, c):
    """TR[i] = max(High[i], Close[i-1]) − min(Low[i], Close[i-1]).

    TR[0] là **NaN**: nó cần Close của nến trước, mà nến trước không tồn tại. MT5 đặt 0
    ở đây (`ATR.mq5:73`) rồi bắt đầu ATR từ chỉ số `period` để không bao giờ đọc tới nó
    — ta trả NaN cho thẳng thắn, và `atr()` cũng bắt đầu từ đúng chỉ số ấy."""
    h, l, c = _f(h), _f(l), _f(c)
    ra = np.full(len(h), np.nan, dtype=F)
    if len(h) < 2:
        return ra
    ctr = c[:-1]
    ra[1:] = np.maximum(h[1:], ctr) - np.minimum(l[1:], ctr)
    return ra


def atr(h, l, c, chu_ky):
    """ATR đúng `iATR` của MT5 — **SMA của True Range**, KHÔNG phải Wilder.

    `MQL5\\Indicators\\Examples\\ATR.mq5`: giá trị đầu tiên nằm ở chỉ số `period` và
    bằng trung bình cộng TR[1..period] (:83), các giá trị sau là cửa sổ trượt
    `ATR[i] = ATR[i-1] + (TR[i] − TR[i-period]) / period` (:92) — chính là SMA tính tăng
    dần. Wilder/SMMA cho số LỚN HƠN và mượt hơn ở cùng chu kỳ, nên chép nhầm là
    `atr_bps` khác → nến nào là "nến nén" khác → cả chuỗi lệnh lệch, mà ngưỡng 7,0 bps
    của D_02 lại được dò ra trên chính con số `iATR` trả về."""
    tr = true_range(h, l, c)
    return _tb_truot(tr, int(chu_ky))


def ma(x, chu_ky, kieu="SMA"):
    """Trung bình trượt trên một chuỗi giá. Bốn kiểu của MT5.

    Mọi kiểu đều khởi động bằng SMA của `chu_ky` giá trị đầu, đúng như MT5 — không phải
    bằng phần tử đầu tiên. Khác chỗ này là hai đường lệch nhau hàng chục nến."""
    x = _f(x)
    n = int(chu_ky)
    kieu = (kieu or "SMA").upper()
    if kieu not in core.MA_METHODS:
        raise ValueError(f"Không biết kiểu MA {kieu!r}")
    if n <= 0 or len(x) < n:
        return np.full(len(x), np.nan, dtype=F)

    if kieu == "SMA":
        return _tb_truot(x, n)

    if kieu == "LWMA":
        w = np.arange(1, n + 1, dtype=F)
        ra = np.full(len(x), np.nan, dtype=F)
        # Cửa sổ trượt có trọng số: `sliding_window_view` không sao chép dữ liệu.
        cua = np.lib.stride_tricks.sliding_window_view(x, n)
        ra[n - 1:] = (cua * w).sum(axis=1) / w.sum()
        return ra

    # EMA / SMMA: đệ quy, phải chạy tuần tự. Trên trục M5 một năm (~72k phần tử) mất
    # vài chục mili giây — không đáng đổi lấy một công thức vector khó đọc.
    alpha = 2.0 / (n + 1.0) if kieu == "EMA" else 1.0 / n
    ra = np.full(len(x), np.nan, dtype=F)
    truoc = np.mean(x[:n])
    ra[n - 1] = truoc
    for i in range(n, len(x)):
        truoc = truoc + alpha * (x[i] - truoc)
        ra[i] = truoc
    return ra


# ---------------------------------------------------------------------------
# Cửa duy nhất bộ chạy gọi tới
# ---------------------------------------------------------------------------
#: Chỉ báo nào cần cột giá nào. Bộ chạy chỉ việc tra bảng, không `if/elif` một dãy.
# ⚠ `atr_bps` KHÔNG còn ở đây. Nó là `atr` chia cho `close` — một phép QUY ĐỔI, giờ
# nằm ở đơn vị của dòng điều kiện (`bo_chay._quy_doi`). Giữ một cột riêng cho nó là
# tính hai lần cùng một thứ, và là lý do kho từng có hai mục cho một đại lượng.
#
# Donchian và Volume MA cũng đã bỏ: chưa sơ đồ nào dùng tới. Thêm lại khi cần thật.
BANG = {
    "atr": lambda n, ck, **k: atr(n["h"], n["l"], n["c"], ck),
    "ma": lambda n, ck, method="SMA", **k: ma(n["c"], ck, method),
}


def tinh(ten, nen, chu_ky, **kw):
    """Tính một chỉ báo trên một mảng nến ĐÃ Ở ĐÚNG KHUNG.

    Không nhận `tf`: việc gộp khung là của `gop()`, và trộn hai trách nhiệm vào một hàm
    là cách nhanh nhất để một ngày nào đó gộp hai lần hoặc quên gộp."""
    if ten not in BANG:
        raise ValueError(f"Chưa cài chỉ báo {ten!r} — có: {', '.join(sorted(BANG))}")
    return BANG[ten](nen, chu_ky, **kw)
