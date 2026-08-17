"""SOI RÁC — tìm thứ CHẾT và chỗ GIAO DIỆN NÓI SAI BACKEND, bằng bằng chứng.

    tools\\soi_rac.bat

Năm phép, mỗi phép trả lời đúng một câu:

  1. `bootstrap` gửi khoá nào mà giao diện KHÔNG BAO GIỜ đọc?     (backend thừa)
  2. cài đặt có khoá nào KHÔNG AI đọc?                            (ô hứa suông)
  3. `core`/`bo_chay`/`khop_lenh`/`ket_noi` khai tên gì không ai dùng?
  4. còn chữ của thứ ĐÃ XOÁ nằm lại trong mã nguồn không?
  5. biến CSS nào khai mà không dùng, hoặc dùng mà không khai?

⚠ CÁI NÀY KHÔNG THAY NGƯỜI ĐỌC. Nó chỉ đưa ra NGHI CAN kèm số đếm; mỗi nghi can phải tự
tay mở ra xem. Đã có ca báo động giả thật: "giao diện đọc khoá bootstrap không gửi" —
hoá ra chúng đến từ `ApiTester`/`ApiLive`, hai bootstrap KHÁC. Nên phép 1 chỉ soi một
chiều (backend thừa), chiều ngược lại để người đọc.

⚠ Thứ CÓ CHỦ Ý mà bài này sẽ không hiểu, đừng vội xoá:
  · bảng DI CƯ tên cũ (DON_VI_CU, SUA_CHE_DO_CU, MOC_CU, TEN_CU, THANH_DON_VI,
    DON_VI_DA_BO…) — chúng tồn tại để mở file cũ không hỏng im lặng;
  · chú thích dài giải thích VÌ SAO — là tài sản, không phải rác;
  · `tai_lieu/core.md` cố ý giữ lịch sử, có băng rôn nói rõ ở đầu file.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)

from cat_studio import luu_tru   # noqa: E402
from cat_studio.api import Api   # noqa: E402

#: Chữ của thứ ĐÃ XOÁ. Còn nằm trong mã nguồn (ngoài bảng di cư) là chú thích nói dối.
DA_XOA = ("atr_bps", "engine_d02", "gia_hien_tai", "dong_mot_phan", "la_engine",
          "nguong_nen_bps", "SETTINGS_DEFAULT", "BRANCH_TYPES", "step_display",
          "canh_quay_lai", "rac_con_lai", "don_bay")

#: File giữ bảng DI CƯ — có tên đã xoá ở đây là ĐÚNG, không phải rác.
CHO_DUOC_NHAC = ("cat_studio/core.py", "cat_studio/luu_tru.py")


def _doc(*p):
    with open(os.path.join(GOC, *p), encoding="utf-8") as f:
        return f.read()


def _quet(goc, duoi):
    ra = {}
    for thu, _, fs in os.walk(os.path.join(GOC, goc)):
        if "__pycache__" in thu or "node_modules" in thu or os.sep + "dist" in thu:
            continue
        for f in fs:
            if f.endswith(duoi):
                d = os.path.join(thu, f)
                ra[os.path.relpath(d, GOC).replace("\\", "/")] = \
                    open(d, encoding="utf-8").read()
    return ra


PY = {**_quet("cat_studio", ".py"), **_quet("tests", ".py")}
PY["app_web.py"] = _doc("app_web.py")
JS = _quet("webui/src", (".ts", ".tsx"))
CSS = _quet("webui/src", ".css")
PY_ALL, JS_ALL, CSS_ALL = ("\n".join(x.values()) for x in (PY, JS, CSS))
loi = 0


def bao(tieu_de, ds, chu=""):
    global loi
    print(f"\n▸ {tieu_de}")
    if not ds:
        print("   ✔ sạch")
        return
    loi += len(ds)
    for x in ds:
        print(f"   ✘ {x}")
    if chu:
        print(f"   ({chu})")


# ---- 1. bootstrap gửi thừa ----
boot = Api().bootstrap()["value"]
bao("`bootstrap` GỬI mà giao diện không đọc",
    [k for k in boot if not re.search(rf"\b{re.escape(k)}\b", JS_ALL)],
    "gửi thứ không ai dùng là bắt cầu nối cõng thêm dữ liệu mỗi lần mở app")

# ---- 2. cài đặt không ai đọc ----
thua = []
for muc, d in (("gốc", luu_tru.CAI_DAT_MAC_DINH),
               ("test", luu_tru.CAI_DAT_MAC_DINH["test"])):
    for k in d:
        if k in ("test", "ui"):
            continue
        n = len(re.findall(rf'["\']{re.escape(k)}["\']', PY_ALL)) \
            + len(re.findall(rf"\b{re.escape(k)}\b", JS_ALL))
        if n <= 1:
            thua.append(f"[{muc}] {k}  ({n} chỗ nhắc tới)")
bao("Khoá CÀI ĐẶT không ai đọc", thua,
    "một ô hứa suông tệ hơn không có ô — người dùng tưởng mình đã đặt giới hạn")

# ---- 3. tên công khai chết ----
chet = []
for f in ("cat_studio/core.py", "cat_studio/bo_chay.py", "cat_studio/khop_lenh.py",
          "cat_studio/ket_noi.py", "cat_studio/so_lenh.py", "cat_studio/tinh_toan.py"):
    src = PY.get(f, "")
    ten = set(re.findall(r"^([A-Z][A-Z0-9_]{2,})\s*=", src, re.M))
    ten |= set(re.findall(r"^def ([a-z]\w+)\(", src, re.M))
    for t in sorted(ten):
        n = len(re.findall(rf"\b{re.escape(t)}\b", PY_ALL)) \
            + len(re.findall(rf"\b{re.escape(t)}\b", JS_ALL))
        if n <= 1:
            chet.append(f"{f}::{t}")
bao("Tên công khai KHÔNG chỗ nào dùng", chet)

# ---- 4. chữ của thứ đã xoá ----
#
# ⚠ Dòng NÓI RA rằng nó đã xoá thì KHÔNG tính — đó là bia mộ, không phải xác. Người sau
# đọc "`don_bay` ĐÃ BỎ vì bộ chạy không đọc" là hiểu ngay vì sao đừng thêm lại; xoá nốt
# dòng đó là xoá mất lý do, và ba tháng nữa ai đó sẽ thêm lại.
#
# Kèm theo: BÀI KIỂM canh phép DI CƯ buộc phải nhắc tên chết — đó chính là thứ nó kiểm.
# Nhận ra chúng bằng mấy chữ nói "cái này thành cái kia": đổi sang · tự chuyển · thay cho.
#
# Và: chú thích KỂ CHUYỆN QUÁ KHỨ ("Trước đây…", "từng…") buộc phải gọi tên cái cũ — đó
# chính là thứ nó kể. Thì quá khứ là dấu hiệu đủ rõ, người đọc không nhầm được.
BIA_MO = re.compile(
    r"(ĐÃ XOÁ|ĐÃ BỎ|đã xoá|đã bỏ|bị xoá|KHÔNG còn|không còn|ĐÃ RỜI|"
    r"ĐỔI sang|đổi sang|đã đổi tên|tự chuyển|chuyển sang|thay cho|thay bằng|"
    r"[Tt]rước đây|từng|đã hết|vốn là|hồi đó|ban đầu|bản cũ|bản trước|"
    # Nhắc từ vựng của EA GỐC khi đối chiếu là việc chính đáng — `test_doi_chieu_d02`
    # sinh ra để làm đúng chuyện đó. Và một câu phủ định ("không phải `X`") tự nó đã nói
    # rõ X không còn.
    r"D_02|không phải|ĐÃ nói|tên chết)")
sot = []
for tu in DA_XOA:
    for f, s in sorted({**PY, **JS}.items()):
        if f in CHO_DUOC_NHAC:
            continue
        for i, dong in enumerate(s.split("\n"), 1):
            if not re.search(rf"\b{re.escape(tu)}\b", dong):
                continue
            # bia mộ nằm ngay trên dòng đó, hoặc trong 3 dòng trước (chú thích nhiều dòng)
            quanh = "\n".join(s.split("\n")[max(0, i - 4):i + 1])
            if not BIA_MO.search(quanh):
                sot.append(f"{tu:<16} {f}:{i}")
bao("Chữ của thứ ĐÃ XOÁ còn nằm lại (không kèm lời giải thích)", sot,
    "chú thích nhắc tên đã xoá mà không nói nó đã xoá là chú thích dạy sai người sau")

# ---- 5. biến CSS ma ----
#
# ⚠ BA lối dùng, thiếu lối nào cũng ra báo động giả:
#   `var(--x)`            trong css
#   `mau('--x', …)`       Chart.tsx đọc biến qua getComputedStyle
#   `style={{'--x': …}}`  StepNode đặt biến inline cho từng khối
# Và bỏ chú thích ra trước khi đếm: `app.css` có một chú thích kể về `--panel`, một biến
# CỐ Ý không tồn tại — đếm cả chú thích là bài soi tự báo động về chính lời cảnh báo.
def _bo_chu_thich(s):
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", s, flags=re.M)


_css, _js = _bo_chu_thich(CSS_ALL), _bo_chu_thich(JS_ALL)
khai = set(re.findall(r"^\s*(--[\w-]+)\s*:", _css, re.M))
khai |= set(re.findall(r"['\"](--[\w-]+)['\"]\s*:", _js))          # đặt inline từ JS
dung = set(re.findall(r"var\((--[\w-]+)", _css + _js))
dung |= set(re.findall(r"mau\(\s*['\"](--[\w-]+)", _js))           # đọc qua getComputedStyle
bao("Biến CSS KHAI mà không dùng", sorted(khai - dung))
bao("Biến CSS DÙNG mà không khai", sorted(dung - khai),
    "thứ hỏng LẶNG: trình duyệt bỏ qua, build vẫn sạch, chỉ màu sai")

print(f"\n{'=' * 60}\n  {loi} nghi can — mỗi cái phải tự mở ra xem\n{'=' * 60}")
sys.exit(1 if loi else 0)
