"""MỌI TÀI LIỆU TỚI TAY GIAO DIỆN ĐỀU PHẢI CÓ ĐỦ THẺ.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
`api._kem_the` tự nhận trong docstring của nó là **hàm DUY NHẤT chuẩn bị một doc cho
giao diện**, và cảnh báo bằng đúng câu chữ:

    *"Vá dòng 449 thì lần sau ai thêm endpoint mới lại quên tiếp."*

Lần sau ấy đã tới. Đường **RL → cửa sổ vẽ** (`_nhan_so_do_may`) gọi `normalize_process`
thay vì `_kem_the` — mà chuẩn hoá KHÔNG sinh ra `cards`. Hậu quả:

```
StepNode đọc card.lines  →  Cannot read properties of undefined
                         →  React gỡ cả cây, cửa sổ vẽ TRẮNG BÓC
                         →  cửa sổ RL không đổi gì, trông như bấm hụt
```

Và nó lẩn được lâu vì **sơ đồ NGƯỜI VẼ không dính**: `cards` được ghi vào file lúc lưu,
nên mở lại là có sẵn. Chỉ sơ đồ đi THẲNG từ Python sang giao diện — máy vẽ, sơ đồ mẫu —
mới chạm vào lỗ này.

Nên bài này không kiểm một endpoint. Nó kiểm **cái luật**: mọi con đường đưa doc tới
giao diện đều phải đi qua một cửa, và cửa ấy phải trả về đủ thẻ cho MỌI khối.

Chạy:  python tests\\test_doc_giao_dien.py
"""
import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import api, core, nguoi_bay, tim_kiem  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def du_the(doc):
    """Mọi tab có `cards`, và MỖI khối có đúng một thẻ mang `lines`."""
    for tab in core.TABS:
        g = doc.get(tab) or {}
        cards = g.get("cards")
        if cards is None:
            return f"tab {tab} thiếu hẳn khoá `cards`"
        if len(cards) != len(g.get("steps") or []):
            return (f"tab {tab}: {len(cards)} thẻ cho "
                    f"{len(g.get('steps') or [])} khối")
        for c in cards:
            if "lines" not in c:
                return f"tab {tab}: một thẻ thiếu `lines` — StepNode đọc nó"
    return None


# ================= 1. CHUẨN HOÁ không đủ, phải KÈM THẺ =================
print("\n▸ Chuẩn hoá KHÔNG sinh ra thẻ — đó là cả gốc của lỗi")

_may, _ = tim_kiem.mot_so_do(random.Random(5))
_ch = core.normalize_process(_may)
kiem("`normalize_process` bảo đảm khoá `cards` CÓ MẶT",
     all("cards" in (_ch.get(t) or {}) for t in core.TABS))
kiem("⚠ nhưng nó KHÔNG sinh ra thẻ — mảng rỗng, mọi khối vẫn thiếu",
     du_the(_ch) is not None, f"— {du_the(_ch)}")
kiem("⭐ `_kem_the` mới là chỗ dựng thẻ", api._kem_the(_may) and
     du_the(api._kem_the(_may)) is None, f"— {du_the(api._kem_the(_may))}")

# ================= 2. MỌI NGUỒN DOC =================
print("\n▸ Mọi con đường đưa doc tới giao diện")

_rng = random.Random(2026)
_nguon = [
    ("sơ đồ mới", lambda: api._kem_the(core.new_process())),
    ("sơ đồ mẫu", lambda: api._kem_the(api._so_do_mau())),
    ("máy vẽ (RL)", lambda: api._kem_the(tim_kiem.mot_so_do(_rng)[0])),
]
for ten, lam in _nguon:
    d = lam()
    v = du_the(d)
    kiem(f"{ten} — đủ thẻ", v is None, f"— {v}" if v else "")

# ⭐ Nhiều sơ đồ máy khác nhau, vì chúng khác nhau về HÌNH DẠNG: có cái không có khối
# Manage nào, có cái đầy nhánh. Một mẫu duy nhất không đại diện được.
_hong = []
for _k in range(30):
    _d, _ = tim_kiem.mot_so_do(_rng)
    if _d is None:
        continue
    _v = du_the(api._kem_the(_d))
    if _v:
        _hong.append(_v)
kiem("⭐ 30 sơ đồ máy đủ hình dạng — không cái nào thiếu thẻ",
     not _hong, f"— {_hong[:2]}" if _hong else "")

# ================= 3. LUẬT MỘT CỬA =================
print("\n▸ Luật MỘT CỬA — không endpoint nào được đi vòng")

_src = io.open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "cat_studio", "api.py"), encoding="utf-8").read()

# Mọi cú `_ban(...)` mang tên sự kiện chở SƠ ĐỒ đều phải kèm `_kem_the`.
_su_kien_doc = ("so_do_may", "so_do_moi")
_lech = []
for dong in _src.split("\n"):
    if "_ban(" not in dong:
        continue
    for sk in _su_kien_doc:
        if sk in dong and "_kem_the" not in dong:
            _lech.append(dong.strip()[:80])
kiem("⚠ mọi sự kiện CHỞ SƠ ĐỒ đều đi qua `_kem_the`",
     not _lech, f"— đi vòng: {_lech}" if _lech else "")

kiem("`_kem_the` tự chuẩn hoá, nên gọi nó là đủ — không phải nhớ hai bước",
     du_the(api._kem_the({"entry": {"steps": [], "edges": []}})) is None)

# ⚠ Chạy hai lần phải bằng đúng một lần: nhiều chỗ đã chuẩn hoá rồi mới gọi tới.
_d1 = api._kem_the(_may)
kiem("bất biến — `_kem_the` hai lần bằng một lần", api._kem_the(_d1) == _d1)

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
