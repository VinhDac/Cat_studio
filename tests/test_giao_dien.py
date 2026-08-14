"""BIẾN CSS MA — `var(--khong-ton-tai)` hỏng LẶNG, và nó vừa hỏng thật hai lần.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
CSS không có lỗi biên dịch. Viết `background: var(--panel)` mà `--panel` không tồn tại
thì trình duyệt coi như KHÔNG ĐẶT thuộc tính đó — nền thành trong suốt, chữ phía sau
xuyên thẳng qua. Không lỗi, không cảnh báo, `tsc` sạch, `vite build` sạch. Chỉ có nhìn
vào mới thấy sai, mà nhìn thì phải mở đúng cái menu đó ra.

Hai ca có thật, tìm ra bằng mắt chứ không bằng máy:
  · `--panel`  — nền menu ⚙ trong suốt, chữ dưới xuyên qua;
  · `--line`   — viền nét đứt rơi về `currentColor`, đậm hơn hẳn ý định.

Ngoại lệ HỢP LỆ: biến do JS đặt lúc chạy (`style={{ '--mau-khoi': … }}`). Chúng không có
trong `theme.css` và không thể có — nên khai ra ở đây, có tên có tuổi, thay vì nới lỏng
phép kiểm.

Chạy:  python tests\\test_giao_dien.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(GOC, "webui", "src")

#: Biến do JS đặt trên chính phần tử lúc chạy — xem `components/StepNode.tsx`.
DAT_LUC_CHAY = {"--mau-khoi"}

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def doc(ten):
    with io.open(os.path.join(CSS, ten), encoding="utf-8") as f:
        return f.read()


def bo_chu_thich(s):
    """Bỏ `/* … */` — chú thích NÓI VỀ một biến ma không phải là dùng nó."""
    return re.sub(r"/\*.*?\*/", " ", s, flags=re.S)


print("\n▸ Mọi `var(--x)` phải có một `--x:` ở đâu đó")
theme, app = doc("theme.css"), doc("app.css")
khai = set(re.findall(r"(--[a-z0-9-]+)\s*:", bo_chu_thich(theme + app)))
dung_bien = set(re.findall(r"var\((--[a-z0-9-]+)", bo_chu_thich(app + theme)))
ma = sorted(dung_bien - khai - DAT_LUC_CHAY)
kiem("không còn biến ma nào", not ma, f"— {ma}" if ma else f"({len(dung_bien)} biến)")

# Chốt riêng cho hai ca đã hỏng thật: chúng phải KHÔNG quay lại.
for ten in ("--panel", "--line"):
    kiem(f"`{ten}` (từng hỏng lặng) không còn được dùng",
         ten not in dung_bien)

print("\n▸ Menu ⚙ phải có nền ĐẶC")
# Menu nổi trên hộp thoại mà nền trong suốt thì vô dụng — canh thẳng thuộc tính đó.
kh = re.search(r"\.menu-th-noi\s*\{(.*?)\}", app, flags=re.S)
kiem("`.menu-th-noi` tồn tại", kh is not None)
if kh:
    than = kh.group(1)
    m = re.search(r"background:\s*var\((--[a-z0-9-]+)\)", than)
    kiem("nền lấy từ một biến CÓ KHAI",
         m is not None and m.group(1) in khai,
         f"— {m.group(1) if m else 'không có background'}")
    kiem("có đổ bóng — menu phải NỔI LÊN, không dán phẳng vào nền",
         "box-shadow" in than)
    kiem("có z-index — hàng dưới không được vẽ đè lên",
         "z-index" in than)

# Toán hạng VẾ PHẢI: bánh răng của nó nằm sát mép phải hộp thoại (787→813 trong vùng nội
# dung 0→850), nên menu 240px mở sang phải là chạy tới 1027 — tràn 177px. Và nó bị CẮT
# thật chứ không chỉ thò ra, vì `.ht-than` có `overflow: auto` nên là một khung cắt.
kh2 = re.search(r"\.ve-phai \.menu-th-noi\s*\{([^}]*)\}", bo_chu_thich(app))
kiem("menu ⚙ của vế PHẢI lật sang trái",
     kh2 is not None and "right: 0" in kh2.group(1) and "left: auto" in kh2.group(1),
     "" if kh2 else "— không có luật lật nào")
kh3 = re.search(r"\.ve-phai \.menu-th-noi::before\s*\{([^}]*)\}", bo_chu_thich(app))
kiem("mũi tên cũng lật theo, không thì nó trỏ vào chỗ trống",
     kh3 is not None and "right:" in kh3.group(1))

print("\n▸ Ô lưới không được tự đặt bề rộng RIÊNG")
# ⚠ Bẫy có thật: `.o.phep { width: 128px }` — rác từ hồi hàng điều kiện dựng bằng flex.
# Khi hàng chuyển sang LƯỚI, cột phép rộng 88px, nên ô 128px tràn 40px sang cột vế phải
# và ĐÈ LÊN nó. Không lỗi, không cảnh báo. Mà phép đo canh cột cũng không bắt được, vì
# nó so MÉP TRÁI — mép trái vẫn thẳng tăm tắp, chỉ phần đuôi thò sang ô bên cạnh.
luoi = re.search(r"\.dong-dk\s*\{(.*?)\}", bo_chu_thich(app), flags=re.S)
kiem("`.dong-dk` là một LƯỚI có cột cố định",
     luoi is not None and "grid-template-columns" in luoi.group(1))
for lop in (r"\.o\.phep", r"\.o\.nho\.don-vi"):
    kh = re.search(lop + r"\s*\{([^}]*)\}", bo_chu_thich(app))
    if kh is None:
        continue
    px = re.search(r"width:\s*(\d+)px", kh.group(1))
    kiem(f"`{lop.replace(chr(92), '')}` không tự đặt width bằng px — phải vừa cột của nó",
         px is None, f"— đang là {px.group(0)}" if px else "")

print("\n▸ Ctrl+S / Ctrl+Shift+S — thứ tự nhánh, thứ `tsc` không bắt được")
# ⚠ Chuỗi `else if` xét lần lượt. Nhánh `Ctrl+S` trần khớp CẢ khi Shift đang giữ, nên nó
# mà đứng trước thì `Ctrl+Shift+S` không bao giờ tới lượt — "Lưu thành" lặng lẽ hoá
# thành "Lưu", ghi đè luôn bản gốc thay vì tạo bản sao. Kiểu hỏng không có lỗi nào báo,
# và chỉ lộ ra khi người dùng đã mất bản gốc.
tsx = open(os.path.join(CSS, "App.tsx"), encoding="utf-8").read()
i_shift = tsx.find("ev.shiftKey && ev.key.toLowerCase() === 's'")
i_tran = tsx.find("ctrl && ev.key.toLowerCase() === 's'")
kiem("có nhánh Ctrl+Shift+S", i_shift > 0)
kiem("Ctrl+Shift+S xét TRƯỚC Ctrl+S trần", 0 < i_shift < i_tran,
     f"— shift@{i_shift} · trần@{i_tran}")

# Cả điểm của cơ chế: đã có nhà thì Ctrl+S KHÔNG hỏi gì. Hỏi tên là việc của `luuThanh`.
than_luu = re.search(r"const luu = useCallback\(async \(\) => \{(.*?)\n  \}, \[",
                     tsx, flags=re.S)
kiem("`luu` (Ctrl+S) KHÔNG tự hỏi tên — nó nhường cho `luuThanh` khi chưa có nhà",
     than_luu is not None and "window.prompt" not in than_luu.group(1))
kiem("`tenTrenDia` là thứ quyết định — không dò kho template để đoán",
     than_luu is not None and "tenTrenDia" in than_luu.group(1))

print("\n▸ Hộp thoại phải cất bản Python ĐÃ CHUẨN HOÁ, không cất bản nháp")
# ⚠ Lỗi có thật. Dòng điều kiện MỚI sinh ra với `{value: 7, tinh: 'bps'}`; đổi vế trái
# sang `Zone — số nến` thì `tinh: 'bps'` NẰM LẠI trong nháp. Ô đơn vị hiện đúng "nến"
# (hỏi `don_vi_cua_o`), xem trước cũng đúng (hỏi Python) — nhưng thứ được CẤT ĐI vẫn còn
# `bps`, nên thẻ trên canvas ghi `Zone — số nến ≥ 10 bps của giá`.
# `normalize_action` vốn đã vứt `tinh` không hợp lệ; hộp thoại chỉ cần dùng nốt thứ nó
# vừa nhận về thay vì bỏ đi.
hd = open(os.path.join(CSS, "components", "ActionDialog.tsx"), encoding="utf-8").read()
kiem("nút Lưu KHÔNG đẩy thẳng bản nháp `a` ra ngoài",
     "onLuu(a)" not in bo_chu_thich(hd))
kiem("nút Lưu đi qua `save_action` để lấy bản đã chuẩn hoá",
     re.search(r"onLuu\(\s*\(?r\.ok && r\.value\?\.action", hd) is not None)

print("\n▸ Bấm ▶ lần hai — cửa sổ tester phải NỔI LÊN rồi mới chạy lại")
# ⚠ Triệu chứng người dùng gặp: bấm ▶ lần hai trông y như nút hỏng. Tester CÓ chạy lại
# thật (JS bắt `so_do_moi` rồi gọi `chay()`), nhưng chạy SAU LƯNG cửa sổ vẽ nên không
# thấy gì nhúc nhích — đành đóng hẳn cửa sổ tester để ép nó tạo lại.
# `mo_live` đã ghi đúng bài học này cho nút ● Live từ trước; tester bị sót.
from cat_studio import api  # noqa: E402

_vet = []


class _KhungGia:
    def keo_len_truoc(self):
        _vet.append("keo")


class _CuaSoGia:
    def __init__(self):
        self.ten = None

    def set_title(self, t):
        self.ten = t


class _ApiTesterGia:
    def __init__(self):
        self._khung = _KhungGia()

    def _ban(self, ten, d):
        _vet.append("ban:" + ten)


_a = api.Api.__new__(api.Api)
_a._tester, _a._api_tester, _a._doc_tester = _CuaSoGia(), _ApiTesterGia(), None
api.Api._mo_cua_so_tester(_a, {"name": "Thử"})

kiem("cửa sổ tester được KÉO LÊN TRƯỚC", "keo" in _vet, f"— {_vet}")
kiem("và nhận sơ đồ mới để tự chạy lại", "ban:so_do_moi" in _vet)
# Thứ tự có nghĩa: `_ban` gọi `evaluate_js` ĐỒNG BỘ và lượt chạy bắt đầu ngay trong đó,
# nên đưa cửa sổ lên SAU là người dùng mất đúng cái đáng xem nhất — thanh tiến trình.
kiem("kéo lên TRƯỚC khi bắn sơ đồ, không phải sau",
     _vet == ["keo", "ban:so_do_moi"], f"— {_vet}")
kiem("cửa sổ CŨ được giữ, không huỷ đi tạo lại", _a._tester is not None
     and _a._tester.ten == "Thử — Strategy Tester", f"— {_a._tester.ten}")

print("\n▸ SPACE ở cửa sổ Tester — phát / dừng")
# ⚠ Ba chỗ phím này phá nếu không né, và không cái nào `tsc` bắt được:
#   · ô nhập (`datetime-local` nhảy tới mốc, ô tick lọc nhật ký) — Space là ký tự / là
#     bật tắt, cướp nó đi là ô hoá hỏng;
#   · nút đang có tiêu điểm — trình duyệt vốn đã bắn `click` khi nhấn Space trên
#     `<button>`, nên vừa bấm ▶ bằng chuột xong thì Space sẽ toggle HAI lần;
#   · `preventDefault` — Space mặc định là CUỘN TRANG, mà bảng nhật ký cuộn được.
ts = open(os.path.join(CSS, "tester", "Tester.tsx"), encoding="utf-8").read()
than = re.search(r"const nghe = \(ev: KeyboardEvent\) => \{(.*?)\n    \}", ts, re.S)
kiem("có bắt phím Space", than is not None)
if than:
    b = than.group(1)
    kiem("né ô nhập — INPUT · TEXTAREA · SELECT · contentEditable",
         all(x in b for x in ("INPUT", "TEXTAREA", "SELECT", "isContentEditable")))
    kiem("né cả BUTTON đang có tiêu điểm — không thì Space toggle HAI lần", "BUTTON" in b)
    kiem("chặn cuộn trang mặc định", "preventDefault" in b)
    # Phím tắt phải chết ở đúng chỗ cái nút chết, không thì nó là một cửa sau.
    kiem("chưa có kết quả thì Space không làm gì — như nút ▶ đang `disabled`",
         re.search(r"if \(!kq\) return", b) is not None)
    kiem("`preventDefault` đứng SAU mọi phép né — chặn sớm là nuốt Space của ô nhập",
         b.index("preventDefault") > max(b.index("INPUT"), b.index("BUTTON")))
    # ← → đi từng nến. GIỮ phím thì trình duyệt TỰ bắn lại `keydown` — "giữ = bấm liên
    # tiếp" có sẵn, không cần hẹn giờ. Nhưng Space thì phải BỎ nhịp lặp, nếu không giữ
    # Space là phát/dừng nhấp nháy ~30 lần/giây và thả tay ra không biết đang ở đâu.
    kiem("có bắt ← và →", "ArrowLeft" in b and "ArrowRight" in b)
    kiem("GIỮ phím: chỉ Space bỏ nhịp lặp, ←/→ thì không",
         re.search(r"ev\.repeat && la === 'phat'", b) is not None)

# Lùi ĐẮT hơn tiến: `nhip()` đọc từ lô đã nạp, còn lùi phải gọi cầu nối HAI lần và dựng
# lại chart. Giữ ← ở nhịp lặp bàn phím là ~60 lời gọi/giây qua cầu nối ĐỒNG BỘ → nghẽn.
kiem("`lui` có KHOÁ chống dồn nhịp khi giữ phím",
     re.search(r"if \(!kq \|\| dangLui\.current\) return", ts) is not None)
kiem("khoá được nhả trong `finally` — lùi hỏng một lần không được khoá chết vĩnh viễn",
     re.search(r"finally \{ dangLui\.current = false \}", ts) is not None)
# Luật §12.22: một hành động, một hàm — nút và phím tắt phải gọi CÙNG chỗ.
kiem("nút ◀ và ▶ gọi đúng `lui` / `tien` mà phím tắt gọi",
     "() => void lui(), false, !kq" in ts and "'Tới 1 nến  (→)', tien," in ts)

print(f"\n{'─' * 60}\n  {dung} đúng · {sai} sai\n{'─' * 60}")
sys.exit(1 if sai else 0)
