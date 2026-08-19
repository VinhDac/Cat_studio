"""NGÔN NGỮ GIAO DIỆN — từ điển không được nói dối.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Khoá của từ điển là **câu tiếng Việt nguyên văn** (`chu('Chạy')`). Cách khai ấy đổi lấy
ba thứ đáng giá — không phải bịa khoá, dịch được từng phần, đọc mã vẫn hiểu — nhưng nó
mua kèm đúng một cái bẫy:

    sửa một dấu phẩy trong câu tiếng Việt mà quên sửa từ điển
    → câu ấy RƠI VỀ TIẾNG VIỆT trong bản tiếng Anh
    → không nổ, không log, không ai biết cho tới lúc người dùng nhìn thấy

Cơ chế dự phòng *"không có khoá thì trả nguyên câu"* là thứ giữ cho app không vỡ, nhưng
chính nó cũng là thứ nuốt lỗi. Nên phải có một chỗ khác canh: **mọi khoá trong từ điển
phải còn tìm thấy được trong mã nguồn**.

Bốn điều bài này canh:

  1. Mọi khoá EN còn tồn tại trong mã — khoá mồ côi = một câu đã bị sửa mà quên báo.
  2. Mọi lời gọi `chu('…')` có mặt trong từ điển — bọc rồi mà chưa dịch thì vẫn tiếng Việt.
  3. Không bản dịch nào RỖNG hoặc trùng nguyên văn tiếng Việt (dịch dối).
  4. Cài đặt `ngon_ngu` có mặt ở MỌI cửa boot — thiếu một cửa là cửa sổ ấy nói tiếng Việt
     trong khi ba cửa kia nói tiếng Anh.

Chạy:  python tests\\test_ngon_ngu.py
"""
import io
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import luu_tru  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def doc(p):
    return io.open(os.path.join(GOC, p), encoding="utf-8").read()


def bo_chu_thich(s):
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", s)


# ---- nguồn ----
# ⚠ Đọc MỌI mảnh `i18n_en*.ts`, không chỉ mảnh đầu. Từ điển tách file vì độ dài, mà bài
# kiểm chỉ đọc một mảnh thì nó báo 196 câu "thiếu bản dịch" trong khi chúng có đủ — một
# bài kiểm nói dối còn tệ hơn không có bài kiểm nào.
_MANH = sorted(f for f in os.listdir(os.path.join(GOC, "webui", "src"))
               if f.startswith("i18n_en") and f.endswith(".ts"))
EN_SRC = "\n".join(bo_chu_thich(doc(f"webui/src/{f}")) for f in _MANH)
KHOA = {}
for m in re.finditer(r"(?m)^\s*'((?:[^'\\]|\\.)+)':\s*\n?\s*'((?:[^'\\]|\\.)*)'", EN_SRC):
    KHOA[m.group(1)] = m.group(2)

MA = []
for goc, _, ten in os.walk(os.path.join(GOC, "webui", "src")):
    for f in ten:
        if f.endswith((".tsx", ".ts")) and not f.startswith("i18n"):
            MA.append(doc(os.path.relpath(os.path.join(goc, f), GOC).replace("\\", "/")))
MA_HET = "\n".join(MA)

print("\n▸ Từ điển ↔ mã nguồn")
kiem("từ điển đọc được và không rỗng", len(KHOA) > 50, f"— {len(KHOA)} khoá")

# ---- 1. khoá MỒ CÔI ----
_moi = sorted(k for k in KHOA if k not in MA_HET)
kiem("⭐ MỌI khoá còn tìm thấy trong mã — khoá mồ côi = câu đã bị sửa mà quên báo",
     not _moi, f"— {len(_moi)} mồ côi, ví dụ: {_moi[:3]}" if _moi else "")

# ---- 2. gọi `chu('…')` mà CHƯA dịch ----
_goi = set()
for m in re.finditer(r"chu\(\s*'((?:[^'\\]|\\.)+)'\s*\)", bo_chu_thich(MA_HET)):
    _goi.add(m.group(1))
for m in re.finditer(r'chu\(\s*"((?:[^"\\]|\\.)+)"\s*\)', bo_chu_thich(MA_HET)):
    _goi.add(m.group(1))
_thieu = sorted(g for g in _goi if g not in KHOA)
kiem("mọi câu ĐÃ BỌC `chu()` đều có bản dịch",
     not _thieu, f"— {len(_thieu)} thiếu, ví dụ: {_thieu[:3]}" if _thieu else "")
kiem("và số câu đã bọc là đáng kể", len(_goi) > 100, f"— {len(_goi)} chỗ")

# ---- 3. dịch DỐI ----
_doi = sorted(k for k, v in KHOA.items() if not v.strip() or v.strip() == k.strip())
kiem("không bản dịch nào RỖNG hay chép nguyên tiếng Việt",
     not _doi, f"— {_doi[:3]}" if _doi else "")

# ---- 4. cài đặt tới được MỌI cửa sổ ----
print("\n▸ Cài đặt `ngon_ngu` — mỗi cửa sổ là một ngữ cảnh JS riêng")
kiem("có trong cài đặt mặc định",
     luu_tru.CAI_DAT_MAC_DINH.get("ngon_ngu") in ("vi", "en"))

API = doc("cat_studio/api.py")
kiem("`save_settings` nhận nó", 'cd["ngon_ngu"]' in API)
# `bootstrap` trả CẢ `settings` nên cửa sổ chính có sẵn; ba cửa còn lại trả từng khoá.
# ⚠ ĐẾM ĐƯỢC THẬT rồi mới so. Bản đầu chỉ so hai phép đếm với nhau, mà cả hai đều
# bằng 0 vì mẫu tìm sai một dấu — bài kiểm QUA, và qua giả thì tệ hơn hỏng.
_ac = len(re.findall(r'"accent":\s*\(self\._cha\._cai_dat or \{\}\)', API))
_nn = len(re.findall(r'"ngon_ngu":\s*\(self\._cha\._cai_dat or \{\}\)', API))
kiem("đếm được cửa boot (nếu không thì phép so dưới là 0 == 0, qua giả)",
     _ac >= 3, f"— {_ac} cửa có `accent`")
kiem("⭐ mọi cửa boot có `accent` thì cũng có `ngon_ngu` — thiếu một cửa là cửa sổ ấy "
     "nói tiếng Việt trong khi ba cửa kia nói tiếng Anh",
     _ac == _nn and _nn > 0, f"— accent {_ac} · ngon_ngu {_nn}")

for f, ten in (("webui/src/App.tsx", "cửa sổ chính"), ("webui/src/rl/RL.tsx", "RL"),
               ("webui/src/tester/Tester.tsx", "Tester"),
               ("webui/src/live/Live.tsx", "Live")):
    kiem(f"{ten} áp ngôn ngữ lúc mở", "datNgon(" in doc(f))

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
