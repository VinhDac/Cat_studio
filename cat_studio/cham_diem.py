"""CHẤM ĐIỂM một lượt chạy — bằng TIỀN, theo TUẦN.

    core.md §18.2

```
mỗi tuần kiếm/mất bao nhiêu % vốn
    → trung bình   ·   dao động (SD)   ·   trung bình ÷ dao động
```

⭐ **Vì sao theo TUẦN chứ không phải tổng cả kỳ.** Một chiến lược ăn đậm một đợt rồi trả
lại đợt khác, cộng lại vẫn dương — nhưng nó không sống được. Cái sống được là cái kiếm
**đều**. Tổng cả kỳ là MỘT con số, nó không phân biệt được hai chuyện đó; chuỗi theo tuần
thì có: cùng một mức lãi, cái nào dao động thấp hơn là cái tốt hơn.

⚠ **KHÔNG chấm bằng `tong_R`.** Đo được (§18.2b): giữ nguyên chiến lược, chỉ đổi phí hoa
hồng 0 → 3,5 $/lot thì tiền GIẢM 175 $ mà `tong_R` lại TĂNG; ở mức 50 $/lot thì tài khoản
mất một phần năm mà `tong_R` vẫn báo **+2,99 — có lãi**. R đo *giá đi được bao nhiêu lần
khoảng SL*, hoa hồng là tiền, nên nó không bao giờ vào R. Đó là định nghĩa, không phải
sót — và nó khiến R không dùng để chấm được.

⚠ **CỬA "tuần có lệnh" là BẮT BUỘC, không phải tuỳ chọn** (§18.2a). Không có nó thì một sơ
đồ vào **đúng một lệnh trong 3,5 năm** ăn điểm cao hơn sơ đồ vào 929 lệnh — và đó là số
học thuần: một tuần có lệnh trong N tuần luôn cho `±1/√(N−1)`, bất kể lệnh ấy lãi hay lỗ
bao nhiêu. Tuần trắng làm co CẢ trung bình LẪN dao động theo đúng một tỉ lệ, nên thương số
sống sót nguyên vẹn. Nằm im được điểm đẹp, và đó là điểm RẺ NHẤT để đạt tới.

⚠ **Ưu tiên là mấy cái CỬA, không phải mấy cái CÂN** (§18.6.4). Sụt vốn không đổi chác
được: cháy 60 % tài khoản thì không mức lãi nào bù lại. Với một hệ số `λ` thì sơ đồ điểm
cao mà sụt vốn 60 % vẫn thắng; với cửa thì nó không lọt vào danh sách. Và *"tôi không chấp
nhận sụt quá 25 %"* là câu phát biểu được, `λ = 0,3` thì phải dò mới biết nặng hay nhẹ.

⭐ **Xếp hạng thì LUÔN là `trung bình ÷ dao động`.** Người dùng chỉnh *"cái gì tôi không
nhận"*; máy xếp hạng phần còn lại bằng ĐÚNG MỘT cái thước (§15.1).
"""
import datetime as dt
import math
from collections import defaultdict

from . import bo_chay

#: Cửa KHOÁ CỨNG — §18.2a. Panel ưu tiên chỉ SIẾT thêm được, không nới ra.
TUAN_CO_LENH_TOI_THIEU = 0.5

#: Cửa của tầng CHỌN (§18.6.4). `None` = không lọc.
#:
#: ⭐ Toàn là CỬA, không cái nào là CÂN. Sụt vốn không đổi chác được với lãi: cháy 60%
#: tài khoản thì không mức lãi nào bù lại. Và *"tôi không nhận sụt quá 25%"* là câu
#: phát biểu được, còn `λ = 0,3` thì phải dò mới biết nặng hay nhẹ — mà dò cái nút chấm
#: điểm là dò trên chính thứ dùng để chấm (§18.1).
#:
#: ⚠ Xếp hạng thì LUÔN là `trung bình ÷ dao động`. Người dùng chỉnh *"cái gì tôi không
#: nhận"*, không chỉnh *"đo bằng gì"* — cái thước không phải ý thích (§15.1).
CUA_MAC_DINH = {
    # KỲ dùng để chấm và để xét cửa. Người dùng nói từ đầu là quan tâm cả tuần lẫn
    # tháng; chọn kỳ KHÔNG phải đổi thước, chỉ là đổi độ phân giải nhìn.
    "ky": None,                               # None = TUAN
    # ⭐ ĐIỂM CÓ HAI VẾ, và đây là chỗ nói vế DAO ĐỘNG có tham gia hay không:
    #
    #     0   điểm = trung bình                  chỉ nhìn lãi, mặc kệ đều
    #     1   điểm = trung bình ÷ dao động       cân bằng  ← mặc định
    #
    # ⚠ Đây KHÔNG phá luật *"cái thước không được là tham số"* (§15.1). Luật ấy cấm
    # chỉnh cái ĐO — chu kỳ ATR, mẫu số chuẩn hoá. Còn `trung bình` và `dao động` đều
    # đã đo xong bằng thước cố định; chọn coi trọng vế nào là **thích gì**, không phải
    # **đo bằng gì** — đúng ranh giới §18.6.4.
    #
    # ⚠ **KHÔNG có nấc 2 (`÷ dao động²`), và đây là chỗ đã thử rồi bỏ.** Đo trên sơ đồ
    # mẫu: trung bình −0,161% · dao động 1,115% ⇒ `k=1` cho −0,1446 nhưng `k=2` cho
    # −0,1296 — tức "ưu tiên đều" lại chấm CAO HƠN. Vì trung bình ÂM thì càng chia càng
    # gần 0. Và không vá được bằng đổi dấu: với dao động < 1 nó lật ngược lần nữa.
    # Một tỉ số đơn giản là KHÔNG đơn điệu theo mẫu số khi tử số âm.
    #
    # Muốn siết chặt hơn nữa thì dùng CỬA `dao_dong_toi_da` — nó đơn điệu, phát biểu
    # được, và không đụng vào thước.
    "manh_deu": None,                         # None = 1
    "tuan_co_lenh": TUAN_CO_LENH_TOI_THIEU,   # tỉ lệ kỳ có lệnh đóng
    "sut_von_toi_da": None,                   # %
    "lai_toi_thieu": None,                    # % vốn mỗi năm
    "so_lenh_toi_thieu": None,                # lệnh đã đóng
    "te_nhat_toi_da": None,                   # kỳ tệ nhất lỗ không quá bao nhiêu %
    "dao_dong_toi_da": None,                  # %
    "diem_toi_thieu": None,
}

TUAN = "tuan"
THANG = "thang"
#: Bao nhiêu kỳ một năm — để quy `lai_toi_thieu` về mỗi năm.
_KY_MOI_NAM = {TUAN: 52.0, THANG: 12.0}


def _khoa(d, ky):
    return d.isocalendar()[:2] if ky == TUAN else (d.year, d.month)


def _moi_ky(t0, t1, ky):
    """MỌI kỳ trong khoảng — kể cả kỳ KHÔNG có lệnh nào.

    ⚠ Tuần trắng cũng là dữ liệu. Bỏ chúng đi thì một chiến lược đánh 3 lần trong 5 năm
    trông y như một chiến lược đánh đều — và cửa `tuan_co_lenh` không còn gì để đếm."""
    ra, d = [], t0
    while d < t1:
        k = _khoa(d, ky)
        if not ra or ra[-1] != k:
            ra.append(k)
        d += dt.timedelta(days=1)
    return ra


#: Bước CUỐN TỚI — §18.3. Số THÁNG mỗi cửa sổ.
#:
#: ⚠ KHÔNG có bước "tuần", và đó là số đo chứ không phải ý thích: hai chiến lược chênh
#: nhau 38 điểm % qua 4,5 năm mà xét TỪNG TUẦN chỉ hơn nhau ở **52%** số tuần — tung
#: đồng xu. Một tuần lẻ không mang tin. Quý = 13 tuần, gộp 6 quý là 78 tuần, trên
#: ngưỡng nhiễu 48 tuần.
BUOC_CUON = {"thang": 1, "quy": 3, "nua_nam": 6}


def cua_so_cuon(t0, t1, buoc="quy"):
    """Chia khoảng `[t0, t1)` thành mấy cửa sổ nối nhau → `[(tu, den), …]`.

    ⭐ Đây là "cuốn tới" của §18.3: thay vì MỘT con số ngoài mẫu, ta có NHIỀU — mỗi
    cửa sổ một lần chấm trên thứ chưa từng thấy. Một lần bốc thăm khác hẳn sáu lần."""
    n = BUOC_CUON.get(buoc, 3)
    ra, a = [], t0
    while a < t1:
        thang = a.month - 1 + n
        b = a.replace(year=a.year + thang // 12, month=thang % 12 + 1, day=1)
        ra.append((a, min(b, t1)))
        a = b
    return ra


def cham_cuon(kq, t0, t1, buoc="quy", cua=None):
    """Chấm TỪNG cửa sổ cuốn tới, từ MỘT lượt chạy.

    ⚠ Cắt chuỗi kỳ chứ KHÔNG chạy lại backtest cho mỗi cửa sổ: sáu cửa sổ mà chạy sáu
    lượt là đắt gấp sáu, trong khi chuỗi lãi/lỗ theo tuần đã có sẵn cả dải — chỉ việc
    bỏ vào đúng rổ.

    Trả `[{tu, den, …ba con số…}]`."""
    c = {**CUA_MAC_DINH, **(cua or {})}
    ky = c["ky"] if c["ky"] in (TUAN, THANG) else TUAN
    goc = dict(chuoi_ky(kq, ky, kem_ngay=True))
    ra = []
    for a, b in cua_so_cuon(t0, t1, buoc):
        v = [goc.get(_khoa(d, ky), 0.0) for d in _moi_ky_ngay(a, b, ky)]
        ra.append({"tu": a.isoformat(), "den": b.isoformat(),
                   **_ba_so(v, c["manh_deu"])})
    return ra


def _moi_ky_ngay(t0, t1, ky):
    """Ngày ĐẦU của mỗi kỳ trong `[t0, t1)` — để tra vào chuỗi đã gom."""
    ra, d = [], t0
    while d < t1:
        k = _khoa(d, ky)
        if not ra or _khoa(ra[-1], ky) != k:
            ra.append(d)
        d += dt.timedelta(days=1)
    return ra


def chuoi_ky(kq, ky=TUAN, kem_ngay=False):
    """Lãi/lỗ mỗi kỳ, tính bằng **% vốn ĐẦU**, kể cả kỳ trắng.

    ⚠ Chia cho vốn ĐẦU, không phải vốn lúc đó. Chia cho vốn lúc đó là trộn lãi kép vào
    chuỗi: cùng một lệnh thắng ở tuần 200 thành một số nhỏ hơn ở tuần 1 chỉ vì vốn đã
    khác — mà dao động thì đo trên chính chuỗi ấy. Một mẫu số cố định giữ các kỳ so
    được với nhau, đúng tinh thần chuẩn hoá của §15."""
    cd, t = kq.cd, kq.nen5["t"]
    goc = defaultdict(float)
    for l in bo_chay.lenh_da_dong(kq.so):
        ngay = dt.datetime.fromtimestamp(int(t[l.nen_dong]), dt.UTC).date()
        goc[_khoa(ngay, ky)] += bo_chay.lai_lenh(l, cd)
    von = cd.deposit or 1.0
    ks = _moi_ky(*_khoang(kq), ky)
    if kem_ngay:
        # `[(khoá kỳ, % vốn)]` — cho `cham_cuon` bỏ vào đúng rổ cửa sổ.
        return [(k, goc.get(k, 0.0) / von * 100.0) for k in ks]
    return [goc.get(k, 0.0) / von * 100.0 for k in ks]


def _khoang(kq):
    """Ngày đầu và ngày cuối của lượt chạy — lấy từ NẾN, không từ ô Cài đặt.

    Ô `tu`/`den` là thứ người dùng gõ; kho nến có thể không phủ hết khoảng đó. Đếm kỳ
    theo ô gõ thì một khoảng đặt rộng quá sẽ đẻ ra hàng trăm tuần trắng ma và cửa
    `tuan_co_lenh` đánh trượt mọi chiến lược."""
    t = kq.nen5["t"]
    d0 = dt.datetime.fromtimestamp(int(t[0]), dt.UTC).date()
    d1 = dt.datetime.fromtimestamp(int(t[-1]), dt.UTC).date() + dt.timedelta(days=1)
    return d0, d1


def _ba_so(v, manh_deu=1):
    """Ba con số của §18.2 cho một chuỗi kỳ.

    `manh_deu` — vế DAO ĐỘNG có tham gia không: `0` chỉ nhìn lãi · `1` cân bằng.
    Xem `CUA_MAC_DINH["manh_deu"]` (và vì sao không có nấc 2)."""
    n = len(v)
    if not n:
        return {"trung_binh": 0.0, "dao_dong": 0.0, "diem": 0.0,
                "co_lenh": 0, "so_ky": 0, "ty_le_co_lenh": 0.0,
                "lo_trung_binh": 0.0, "te_nhat": 0.0, "tot_nhat": 0.0}
    tb = sum(v) / n
    sd = math.sqrt(sum((x - tb) ** 2 for x in v) / n)
    am = [x for x in v if x < 0]
    co = sum(1 for x in v if x != 0.0)
    k = 1 if manh_deu is None else int(manh_deu)
    if k <= 0:
        diem = tb                          # chỉ nhìn lãi — vế dưới không tham gia
    elif sd:
        diem = tb / sd
    else:
        # ⭐ `sd == 0` nghĩa là mọi kỳ y hệt nhau — hoặc không lệnh nào (điểm 0, đúng),
        # hoặc một chuỗi hằng số mà thực tế không xảy ra. Không bịa ra vô cực.
        diem = 0.0
    return {
        "trung_binh": round(tb, 4),
        "dao_dong": round(sd, 4),
        "diem": round(diem, 4),
        "co_lenh": co,
        "so_ky": n,
        "ty_le_co_lenh": round(co / n, 4),
        "lo_trung_binh": round(sum(am) / len(am), 4) if am else 0.0,
        "te_nhat": round(min(v), 4),
        "tot_nhat": round(max(v), 4),
    }


def cham(kq, cua=None):
    """Chấm một `KetQua`. Trả một bảng số, kèm `dat` và `ly_do` nếu rớt cửa.

    ⚠ Rớt cửa thì `dat=False` và `diem` vẫn tính ra — nhưng **không được dùng để xếp
    hạng**. Giữ lại con số để người đọc thấy nó rớt vì đâu, thay vì một dòng "loại"
    trống không."""
    c = {**CUA_MAC_DINH, **(cua or {})}
    ky = c["ky"] if c["ky"] in (TUAN, THANG) else TUAN
    md = c["manh_deu"]
    # CẢ HAI kỳ đều tính và đều trả về — người dùng nói từ đầu là quan tâm cả tuần lẫn
    # tháng. `ky` chỉ quyết định chấm theo cái nào, không giấu cái kia đi.
    ra = {k: _ba_so(chuoi_ky(kq, k), md) for k in (TUAN, THANG)}
    t = ra[ky]
    ra["ky"] = ky
    ra["manh_deu"] = 1 if md is None else int(md)
    ra["diem"] = t["diem"]
    ra["sut_von_pt"] = kq.thong_ke["drawdown_pt"]
    ra["lai_pt"] = kq.thong_ke["lai_pt"]
    ra["so_lenh"] = kq.thong_ke["so_dong"]
    ra["lai_moi_nam"] = round(
        ra["lai_pt"] / (t["so_ky"] / _KY_MOI_NAM[ky]), 2) if t["so_ky"] else 0.0

    # ---- CỬA — dừng ở cửa ĐẦU TIÊN trượt, và nói ra CON SỐ đã trượt.
    # "Loại" trống không thì người dùng phải đi dò; kèm con số thì sửa được ngay.
    ten_ky = "tuần" if ky == TUAN else "tháng"
    nguong = max(c["tuan_co_lenh"] or 0.0, TUAN_CO_LENH_TOI_THIEU)
    ly_do = None
    if t["ty_le_co_lenh"] < nguong:
        ly_do = (f"{ten_ky} có lệnh {t['co_lenh']}/{t['so_ky']} "
                 f"({t['ty_le_co_lenh'] * 100:.0f}%) — dưới {nguong * 100:.0f}%")
    elif c["so_lenh_toi_thieu"] and ra["so_lenh"] < c["so_lenh_toi_thieu"]:
        ly_do = (f"chỉ {ra['so_lenh']} lệnh — dưới "
                 f"{int(c['so_lenh_toi_thieu'])}")
    elif c["sut_von_toi_da"] is not None and ra["sut_von_pt"] > c["sut_von_toi_da"]:
        ly_do = f"sụt vốn {ra['sut_von_pt']:.1f}% — quá {c['sut_von_toi_da']:.0f}%"
    elif c["te_nhat_toi_da"] is not None \
            and t["te_nhat"] < -abs(c["te_nhat_toi_da"]):
        ly_do = (f"{ten_ky} tệ nhất {t['te_nhat']:.2f}% — quá "
                 f"{abs(c['te_nhat_toi_da']):.1f}%")
    elif c["dao_dong_toi_da"] is not None and t["dao_dong"] > c["dao_dong_toi_da"]:
        ly_do = (f"dao động {ten_ky} {t['dao_dong']:.2f}% — quá "
                 f"{c['dao_dong_toi_da']:.1f}%")
    elif c["lai_toi_thieu"] is not None and ra["lai_moi_nam"] < c["lai_toi_thieu"]:
        ly_do = (f"lãi {ra['lai_moi_nam']:.1f}%/năm — dưới "
                 f"{c['lai_toi_thieu']:.0f}%/năm")
    elif c["diem_toi_thieu"] is not None and ra["diem"] < c["diem_toi_thieu"]:
        ly_do = f"điểm {ra['diem']:.4f} — dưới {c['diem_toi_thieu']:.4f}"
    ra["dat"] = ly_do is None
    ra["ly_do"] = ly_do
    return ra


def xep_hang(ds, cua=None):
    """Nhiều `(nhãn, KetQua)` → xếp hạng theo điểm, đã bỏ cái rớt cửa.

    Trả `(qua, rot)` — cả hai đều là `[(nhãn, bảng_điểm)]`. Giữ `rot` chứ không vứt:
    *"8.760 sơ đồ chết"* là một con số phải hiện ra, không phải thứ im lặng biến mất."""
    qua, rot = [], []
    for ten, kq in ds:
        d = cham(kq, cua)
        (qua if d["dat"] else rot).append((ten, d))
    qua.sort(key=lambda x: -x[1]["diem"])
    return qua, rot
