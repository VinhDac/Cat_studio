"""Mô hình KHỚP LỆNH — phần việc của SÀN, tách hẳn khỏi phần việc của sơ đồ.

    sơ đồ quyết định  →  ĐẶT lệnh ở mức nào
    file này quyết định →  lệnh đó KHỚP lúc nào, ở GIÁ nào

Tách riêng vì đây là thứ DUY NHẤT đổi mà đổi cả đường vốn: cùng một sơ đồ, hai mô hình
khớp khác nhau cho hai kết quả khác hẳn. Phải soi được, thay được, và thay mà không phải
đụng vào bộ chạy.

Toàn bộ file là HÀM THUẦN trên vài con số — không numpy, không sổ lệnh, không đồ thị.

════════════════════════════════════════════════════════════════════════════
1. ĐƯỜNG ĐI 4 ĐIỂM  (core.md §12.2)
════════════════════════════════════════════════════════════════════════════
Đừng xử lý SL/TP như trường hợp đặc biệt. Biến mỗi nến M1 thành một ĐƯỜNG ĐI rồi bước
qua nó:

    C ≥ O (nến tăng)  →  O → L → H → C
    C < O (nến giảm)  →  O → H → L → C

Giá nhúng xuống trước rồi mới đẩy lên, hoặc ngược lại — suy từ chính chiều của nến.
Trùng cách MT5 sinh tick ở chế độ "1 minute OHLC", nên số của ta so được với Strategy
Tester của MT5.

Rồi mọi thứ còn lại thành MỘT luật: *"giá chạm mức X ở bước thứ k của đường đi"*. Lệnh
chờ khớp, SL bị chạm, TP bị chạm — cùng một phép kiểm, chỉ khác mức giá. Không còn
"trường hợp SL và TP cùng nến": đường đi đã trả lời cái nào tới trước.

════════════════════════════════════════════════════════════════════════════
2. SPREAD — quy MỌI mức về Bid MỘT LẦN  (core.md §12.3)
════════════════════════════════════════════════════════════════════════════
Nến là giá **Bid**. Ask = Bid + spread. Quy đổi một lần rồi vẫn chỉ một đường đi:

    Mua — giá vào  (khớp ở Ask)   sàn so Ask   →  ngưỡng Bid = P − spread
    Mua — SL / TP  (đóng ở Bid)   sàn so Bid   →  ngưỡng Bid = P
    Bán — giá vào  (khớp ở Bid)   sàn so Bid   →  ngưỡng Bid = P
    Bán — SL / TP  (đóng ở Ask)   sàn so Ask   →  ngưỡng Bid = P − spread

Chi phí spread vì thế hiện ra ĐÚNG CHỖ nó phát sinh — lệnh Mua Stop kích hoạt SỚM hơn
(tính theo Bid), rồi giá phải đi xa thêm đúng một spread nữa mới chạm TP — chứ không
phải một khoản trừ bịa ra ở cuối.

D_02 hoàn toàn không xử lý spread (grep `spread` trong toàn EA = 0 kết quả) trong khi
sàn thì kích hoạt Buy Stop theo Ask trên một mức giá tính từ nến Bid. Spread = 0 cho
kết quả lãi hơn thực tế MỘT CÁCH CÓ HỆ THỐNG.

════════════════════════════════════════════════════════════════════════════
3. GAP — mở cửa đã nhảy qua mức
════════════════════════════════════════════════════════════════════════════
Điểm ĐẦU của đường đi là O. Chạm mức ngay ở bước 0 nghĩa là nến MỞ CỬA đã ở bên kia
mức — khớp tại O, KHÔNG phải tại mức đặt. Ba bước sau thì giá đi liên tục nên chạm mức
là khớp đúng mức.

Chiến lược này CHỈ dùng lệnh chờ stop, nên gap qua entry là ca thường gặp chứ không phải
ngoại lệ — và đúng những lệnh đó cho kết quả cực đoan nhất. Bỏ qua gap là backtest đẹp
hơn thực tế ở đúng chỗ nguy hiểm nhất.
"""

#: Lý do đóng — khớp `so_lenh.LY_DO_DONG`.
SL, TP = "sl", "tp"

#: Hướng lệnh — khớp `so_lenh.MUA` / `so_lenh.BAN`.
MUA, BAN = "mua", "ban"


# ---------------------------------------------------------------------------
# Đường đi trong một nến
# ---------------------------------------------------------------------------
def duong_di(o, h, l, c):
    """Bốn điểm giá (Bid) mà nến M1 này đi qua, THEO THỨ TỰ.

    Nến tăng thì giả định giá nhúng xuống đáy trước rồi mới đẩy lên đỉnh; nến giảm thì
    ngược lại. Đây không phải phỏng đoán tuỳ tiện — nó suy từ chính chiều của nến, và
    trùng cách MT5 sinh tick ở chế độ "1 minute OHLC"."""
    o, h, l, c = float(o), float(h), float(l), float(c)
    return (o, l, h, c) if c >= o else (o, h, l, c)


def _cham(duong, nguong, len_tren):
    """Bước đầu tiên đường đi chạm `nguong`. Trả `(buoc, gia_bid)` hoặc None.

    `len_tren=True`  → chờ giá LÊN tới ngưỡng (`>=`)
    `len_tren=False` → chờ giá XUỐNG tới ngưỡng (`<=`)

    Chạm ở bước 0 là GAP: nến mở cửa đã ở bên kia mức, nên giá thực tế là giá MỞ CỬA
    chứ không phải mức đặt. Ba bước sau giá đi liên tục nên khớp đúng mức."""
    for k, p in enumerate(duong):
        if (p >= nguong) if len_tren else (p <= nguong):
            return (k, duong[0] if k == 0 else nguong)
    return None


# ---------------------------------------------------------------------------
# Quy mức về Bid
# ---------------------------------------------------------------------------
def _muc_vao(huong, gia_dat, spread):
    """(ngưỡng Bid, chờ giá lên?) để một lệnh chờ STOP kích hoạt."""
    if huong == MUA:
        return (gia_dat - spread, True)      # sàn so Ask ≥ giá đặt
    return (gia_dat, False)                  # sàn so Bid ≤ giá đặt


def _gia_vao(huong, gia_bid, spread):
    """Giá GHI VÀO SỔ khi khớp: lệnh Mua vào ở Ask, lệnh Bán vào ở Bid."""
    return gia_bid + spread if huong == MUA else gia_bid


def _muc_ra(huong, muc, la_sl, spread):
    """(ngưỡng Bid, chờ giá lên?) để SL hoặc TP của một vị thế bị chạm."""
    if huong == MUA:                          # vị thế Mua đóng ở Bid
        return (muc, not la_sl)               # SL nằm dưới → chờ xuống; TP trên → lên
    return (muc - spread, la_sl)              # vị thế Bán đóng ở Ask


def _gia_ra(huong, gia_bid, spread):
    """Giá GHI VÀO SỔ khi đóng: vị thế Mua đóng ở Bid, vị thế Bán đóng ở Ask."""
    return gia_bid if huong == MUA else gia_bid + spread


# ---------------------------------------------------------------------------
# Một nến, một lệnh
# ---------------------------------------------------------------------------
def trong_nen(lenh, nen, spread=0.0):
    """Nến M1 này làm gì với một lệnh? Trả danh sách sự kiện THEO THỨ TỰ xảy ra.

    `lenh` là dict/đối tượng có: `huong` · `da_khop` · `gia_dat` · `sl` · `tp`.
    `nen` có `o` `h` `l` `c`. `spread` tính bằng ĐƠN VỊ GIÁ (points × point size) —
    file này cố ý không biết `digits` là gì, chỗ gọi quy đổi.

    Sự kiện: `{"loai": "khop"|"dong", "buoc": 0..3, "gia": …, "ly_do": "sl"|"tp"}`.

    Một nến có thể sinh HAI sự kiện: lệnh chờ khớp ở bước 1 rồi chính nến đó quét tiếp
    tới SL ở bước 2. Với mô hình đường đi thì đó chỉ là hai bước liền nhau, không phải
    một ca đặc biệt phải viết riêng.
    """
    huong = _lay(lenh, "huong", MUA)
    d = duong_di(_lay(nen, "o"), _lay(nen, "h"), _lay(nen, "l"), _lay(nen, "c"))
    ra = []
    buoc_dau = 0

    if not _lay(lenh, "da_khop", False):
        gia_dat = _lay(lenh, "gia_dat")
        if gia_dat is None:
            return ra
        nguong, len_tren = _muc_vao(huong, float(gia_dat), spread)
        hit = _cham(d, nguong, len_tren)
        if hit is None:
            return ra                        # chưa khớp thì chưa có SL/TP nào để chạm
        k, bid = hit
        ra.append({"loai": "khop", "buoc": k, "gia": _gia_vao(huong, bid, spread),
                   "gap": k == 0})
        # SL/TP chỉ được xét TỪ bước khớp trở đi. Xét cả bước trước là để một cái SL
        # chưa tồn tại giết một vị thế chưa mở.
        buoc_dau = k

    dong = _cham_ra(lenh, d, spread, buoc_dau, huong)
    if dong:
        ra.append(dong)
    return ra


def _cham_ra(lenh, d, spread, buoc_dau, huong):
    """SL hay TP tới trước? Trả sự kiện đóng, hoặc None."""
    ung = []
    for muc, la_sl, ly_do in ((_lay(lenh, "sl"), True, SL),
                              (_lay(lenh, "tp"), False, TP)):
        if muc is None:
            continue
        nguong, len_tren = _muc_ra(huong, float(muc), la_sl, spread)
        hit = _cham(d[buoc_dau:], nguong, len_tren)
        if hit:
            k, bid = hit
            k += buoc_dau
            # Chạm ở bước 0 của LÁT CẮT mà lát cắt không bắt đầu từ đầu nến thì KHÔNG
            # phải gap — đó là chính cái giá vừa khớp lệnh, giá đi liên tục từ đó.
            if buoc_dau and k == buoc_dau:
                bid = nguong
            ung.append((k, ly_do, _gia_ra(huong, bid, spread)))
    if not ung:
        return None
    # Bước nhỏ hơn thì tới trước. Cùng bước là SL và TP chạm cùng một điểm giá — về
    # nguyên tắc không xảy ra (chúng nằm hai phía giá vào), chỉ có khi lệnh bị đặt sai;
    # khi đó chọn SL, tức giả định xấu nhất.
    ung.sort(key=lambda x: (x[0], x[1] != SL))
    k, ly_do, gia = ung[0]
    return {"loai": "dong", "buoc": k, "gia": gia, "ly_do": ly_do,
            "mo_ho": len(ung) > 1}


def ca_hai_trong_nen(lenh, nen, spread=0.0):
    """Cả SL LẪN TP đều nằm trong biên độ nến M1 này?

    Không dùng để quyết định gì — đường đi đã quyết rồi. Dùng để ĐẾM: chạy một năm mà
    con số này bằng 0 thì có bằng chứng kết quả không phụ thuộc vào giả định đường đi.
    Đó là bằng chứng, không phải niềm tin."""
    if not _lay(lenh, "da_khop", False):
        return False
    huong = _lay(lenh, "huong", MUA)
    lo, hi = float(_lay(nen, "l")), float(_lay(nen, "h"))
    trong = []
    for muc, la_sl in ((_lay(lenh, "sl"), True), (_lay(lenh, "tp"), False)):
        if muc is None:
            return False
        nguong, _ = _muc_ra(huong, float(muc), la_sl, spread)
        trong.append(lo <= nguong <= hi)
    return all(trong)


def _lay(o, ten, mac_dinh=None):
    """Đọc một trường, chấp nhận cả dict lẫn đối tượng.

    Để `khop_lenh` dùng được với `so_lenh.Lenh` thật, với dict trong bài kiểm, và với
    một dòng của mảng numpy — mà không phải import cái nào trong ba thứ đó."""
    if isinstance(o, dict):
        return o.get(ten, mac_dinh)
    try:
        return o[ten]                        # dòng numpy có tên trường
    except (TypeError, IndexError, KeyError, ValueError):
        pass
    return getattr(o, ten, mac_dinh)
