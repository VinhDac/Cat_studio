"""Nguồn nến — luật cất giữ và luật "một dải liền".

Bài này CỐ Ý không cần MT5: nó kiểm phần lý lẽ, thứ sai thầm lặng và sai vĩnh viễn.
Phần nói chuyện với terminal thì phải có MT5 mở mới thử được, và đã thử tay.

Ba thứ đáng sợ nhất, đều được canh ở đây:

  1. **Dải bị THỦNG.** Xin một khoảng rời hẳn dải đang có mà chỉ tải phần mới thì giữa
     hai mảnh còn một lỗ, và bộ chạy sẽ chạy xuyên qua nó mà không biết.
  2. **Nến trùng / lộn xộn.** Ghép hai lần tải chồng lấn phải ra một dãy tăng dần,
     không trùng — nếu không thì đếm "nến liên tiếp" sai ngay.
  3. **Lỗ hổng cuối tuần không được nhận ra.** Luật vùng nén dựa vào nó (core.md §12.6b).

Chạy:  python tests\\test_nguon_nen.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import nguon_nen as nn  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def nen(t_dau, so, buoc=60):
    """Một dãy nến M1 giả, giá tăng đều — chỉ cần đúng cột `t` là đủ cho mọi luật ở đây."""
    a = np.empty(so, dtype=nn.DTYPE)
    a["t"] = np.arange(t_dau, t_dau + so * buoc, buoc, dtype=np.int64)[:so]
    for k in ("o", "h", "l", "c"):
        a[k] = np.arange(so, dtype=np.float64)
    a["vol"] = 1
    return a


# ================= 1. thời điểm =================
print("\n▸ Đọc thời điểm")
kiem("chuỗi ngày, chuỗi ngày-giờ, epoch, None — đều hiểu",
     nn.thoi_diem("2025-01-01") == 1735689600
     and nn.thoi_diem("2025-01-01 00:00:00") == 1735689600
     and nn.thoi_diem(1735689600) == 1735689600
     and nn.thoi_diem(None) is None)
kiem("rác thì trả None chứ không ném lỗi qua cầu nối",
     nn.thoi_diem("hôm qua") is None and nn.thoi_diem("") is None)

# ================= 2. MỘT DẢI LIỀN =================
print("\n▸ Luật MỘT DẢI LIỀN")
GIO = 3600
DA_CO = {"symbol": "T", "tu": 1000 * GIO, "den": 2000 * GIO, "so_nen": 5}
that = nn.doc_meta
nn.doc_meta = lambda s: DA_CO                       # thay tạm, khỏi đụng đĩa
# Mục này soát riêng phần SỐ HỌC KHOẢNG, nên cũng phải thay luôn phép kiểm file: bản thật
# đọc kích thước `.npy` trên đĩa để bắt file cụt (xem `nguon_nen.file_du`), mà ở đây làm
# gì có file nào. Phép kiểm đó có bài riêng ở mục 5.
that_file_du = nn.file_du
nn.file_du = lambda s, m: True

kiem("chưa có gì → tải trọn khoảng xin",
     (lambda: (nn.__dict__.update(doc_meta=lambda s: None),
               nn.khoang_thieu("T", 10 * GIO, 20 * GIO))[1])()
     == [(10 * GIO, 20 * GIO)])
nn.doc_meta = lambda s: DA_CO

kiem("nằm gọn trong dải đã có → KHÔNG tải gì",
     nn.khoang_thieu("T", 1200 * GIO, 1800 * GIO) == [])
kiem("thò ra bên phải → chỉ tải phần thò",
     nn.khoang_thieu("T", 1500 * GIO, 2200 * GIO) == [(2000 * GIO, 2200 * GIO)])
kiem("thò ra bên trái → chỉ tải phần thò",
     nn.khoang_thieu("T", 800 * GIO, 1500 * GIO) == [(800 * GIO, 1000 * GIO)])
kiem("bọc cả hai đầu → hai khoảng",
     nn.khoang_thieu("T", 800 * GIO, 2200 * GIO)
     == [(800 * GIO, 1000 * GIO), (2000 * GIO, 2200 * GIO)])

# Đây là cái bẫy đã bắt được lúc chạy thật: khoảng RỜI HẲN mà chỉ tải phần mới thì dải
# bị thủng, và bộ chạy sẽ chạy xuyên qua chỗ thủng mà không biết.
kiem("khoảng RỜI bên phải → tải luôn phần Ở GIỮA cho liền dải",
     nn.khoang_thieu("T", 3000 * GIO, 3500 * GIO) == [(2000 * GIO, 3500 * GIO)],
     f"— {[(x // GIO, y // GIO) for x, y in nn.khoang_thieu('T', 3000 * GIO, 3500 * GIO)]}")
kiem("khoảng RỜI bên trái → cũng vá liền",
     nn.khoang_thieu("T", 100 * GIO, 500 * GIO) == [(100 * GIO, 1000 * GIO)])
kiem("khoảng ngược đời (đến < từ) → không tải gì, không nổ",
     nn.khoang_thieu("T", 2000 * GIO, 1000 * GIO) == [])
nn.doc_meta = that
nn.file_du = that_file_du

print("\n▸ Ước tính trước khi tải")
u = nn.uoc_tinh([(0, 30 * 86400)])
kiem("30 ngày ≈ 30k nến ≈ 1,4 MB — đủ để người dùng biết mình sắp tải gì",
     28_000 < u["so_nen"] < 33_000 and 1.0 < u["mb"] < 2.0, f"— {u}")
kiem("một năm ≈ 18 MB, khớp con số đã ghi ở core.md §12.7",
     15 < nn.uoc_tinh([(0, 365 * 86400)])["mb"] < 20,
     f"— {nn.uoc_tinh([(0, 365 * 86400)])['mb']} MB")

# ================= 3. ghép hai lần tải =================
print("\n▸ Ghép hai lần tải")
a1, a2 = nen(0, 100), nen(50 * 60, 100)             # chồng lấn 50 nến
g = nn._gop(a1, a2)
kiem("chồng lấn → bỏ trùng, không nhân đôi", len(g) == 150, f"— {len(g)}")
kiem("thời gian TĂNG DẦN và không trùng",
     bool(np.all(np.diff(g["t"]) > 0)))
kiem("ghép với mảng rỗng vẫn ra đúng dải",
     len(nn._gop(np.empty(0, dtype=nn.DTYPE), a1)) == 100
     and len(nn._gop(a1, np.empty(0, dtype=nn.DTYPE))) == 100)
kiem("tải lô sau TRƯỚC lô trước vẫn ra đúng thứ tự",
     bool(np.all(nn._gop(a2, a1)["t"] == g["t"])))

# ================= 4. lỗ hổng =================
print("\n▸ Nhận ra lỗ hổng (cuối tuần)")
lien = nen(0, 60)
sau = nen(60 * 60 + 48 * 3600, 60)                  # cách 48 giờ = cuối tuần
mau = nn._gop(lien, sau)
_doc = nn.doc
nn.doc = lambda s, tu=None, den=None: mau
lh = nn.lo_hong("T")
kiem("thấy đúng MỘT lỗ", len(lh) == 1, f"— {len(lh)}")
kiem("đo đúng độ dài (~48 giờ)", lh and 2870 < lh[0][2] < 2890, f"— {lh[0][2] if lh else 0} phút")
nn.doc = lambda s, tu=None, den=None: lien
kiem("chuỗi liền mạch → không báo lỗ nào", nn.lo_hong("T") == [])
nn.doc = _doc

# ================= 5. hình dạng dữ liệu =================
print("\n▸ Hình dạng dữ liệu")
kiem("một nến đúng 48 byte — một năm ≈ 18 MB", nn.DTYPE.itemsize == 48)
kiem("KHÔNG lưu spread từng nến (mô hình đã chốt là một con số ở Cài đặt)",
     "spread" not in (nn.DTYPE.names or ()))
kiem("chưa tải gì → trả mảng RỖNG đúng dtype, không phải None",
     isinstance(nn.doc("__khong_ton_tai__"), np.ndarray)
     and nn.doc("__khong_ton_tai__").dtype == nn.DTYPE)


# ================= 6. ghi nguyên tử & file cụt =================
#
# Meta và mảng nến là HAI file. Trước đây `np.save` ghi thẳng lên file đích, nên ngắt
# giữa chừng để lại `.npy` cụt + meta nguyên vẹn → `doc()` trả rỗng, `khoang_thieu()` chỉ
# nhìn meta nên bảo "đủ rồi", và app KHÔNG BAO GIỜ tải lại. Tự khoá vào trạng thái chết.
print("\n▸ Ghi nguyên tử và chốt chặn file cụt")
import json as _json  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

from cat_studio import luu_tru  # noqa: E402

_tam = tempfile.mkdtemp(prefix="catstudio_test_")
_that_goc = luu_tru.goc
luu_tru.goc = lambda: _tam
try:
    _n = 300
    _a = np.zeros(_n, dtype=nn.DTYPE)
    _a["t"] = np.arange(0, _n * 60, 60, dtype=np.int64)
    _mn, _mj = nn._duong("ZZ")
    nn._ghi_nguyen_tu(_mn, lambda f: np.save(f, _a, allow_pickle=False))
    nn._ghi_nguyen_tu(_mj, lambda f: f.write(_json.dumps(
        {"symbol": "ZZ", "tu": 0, "den": (_n - 1) * 60, "so_nen": _n}).encode("utf-8")))

    kiem("ghi rồi đọc lại được nguyên vẹn", len(nn.doc("ZZ")) == _n)
    kiem("dữ liệu đủ → khoang_thieu trả rỗng",
         nn.khoang_thieu("ZZ", 0, (_n - 1) * 60) == [])

    with open(_mn, "r+b") as _f:                     # cắt cụt như một lần ghi dở
        _f.truncate(os.path.getsize(_mn) - 500)
    kiem("file .npy CỤT → khoang_thieu đòi tải lại, không kẹt ở 'đã đủ'",
         nn.khoang_thieu("ZZ", 0, (_n - 1) * 60) == [(0, (_n - 1) * 60)])

    _truoc = os.path.getsize(_mn)

    def _no(f):
        f.write(b"x" * 64)
        raise RuntimeError("giả lập mất điện")

    try:
        nn._ghi_nguyen_tu(_mn, _no)
    except RuntimeError:
        pass
    kiem("ngắt giữa lúc ghi → bản CŨ còn nguyên, không cụt thêm",
         os.path.getsize(_mn) == _truoc)
finally:
    luu_tru.goc = _that_goc
    shutil.rmtree(_tam, ignore_errors=True)

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
