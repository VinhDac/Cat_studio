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

print(f"\n{'─' * 60}\n  {dung} đúng · {sai} sai\n{'─' * 60}")
sys.exit(1 if sai else 0)
