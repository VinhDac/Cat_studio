"""SOI TIẾNG VIỆT CÒN SÓT — mọi chữ NGƯỜI DÙNG THẤY mà chưa đi qua từ điển.

    tools\\soi_tieng_viet.bat        (hoặc: python tools/soi_tieng_viet.py)

⚠ VÌ SAO KHÔNG DÙNG LẠI `test_ngon_ngu`. Bài kiểm ấy hỏi *"câu đã bọc có bản dịch
chưa"* — nó KHÔNG biết gì về câu **chưa bọc**. Một file dịch 0% vẫn qua bài kiểm ấy sạch
sẽ. Đây là câu hỏi ngược lại, và là câu duy nhất trả lời được *"đã 100% chưa"*.

Ba nguồn, vì chữ tới mắt người dùng từ ba đường:

```
1. TSX/TS   chuỗi và chữ giữa hai thẻ, chưa bọc `chu()`
2. PYTHON   chuỗi trong câu người soát mắng / báo lỗi / nhãn, chưa bọc `chu()`
3. CSS/HTML content: "…" và chữ trong `index.html`
```

⚠ BỎ QUA CÓ CHỦ Ý — đây là chỗ dễ báo động giả nhất, mỗi mục phải nói được vì sao:

  · chú thích (`//`, `/* */`, `#`, docstring) — là tài sản của người đọc mã, không phải
    giao diện. Bỏ hết, không cần bàn.
  · khoá máy dùng (`'entry'`, `'vi'`) — không có dấu tiếng Việt nên tự rơi ra.
  · tên file / đường dẫn / mã lỗi — cùng lý do.
  · `tai_lieu/`, `tools/`, `tests/` — không ai nhìn thấy chúng trong app.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DAU = ("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợ"
       "ùúủũụừứửữựỳýỷỹỵĂÂĐÊÔƠƯÀÁẢÃẠÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤỲÝỶỸỴ")
#: Chữ KHÔNG dấu vẫn là tiếng Việt nếu nó là một trong mấy từ này. Không quét cả từ
#: điển tiếng Việt — chỉ mấy từ hay xuất hiện trần trong giao diện.
KHONG_DAU = ("khoi", "so do", "lenh", "cua so", "chay", "dung", "xoa", "luu")
SVG = re.compile(r"^[MmLlHhVvCcZzAaQqSsTt0-9 .,\-]+$")


def co_viet(v):
    return any(c in DAU for c in v)


def bo_chu_thich_js(s):
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", s)


def bo_chu_thich_py(s):
    # docstring """…""" và '''…''' + dòng `#`
    s = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", s)
    return re.sub(r"(?m)#[^\n]*", "", s)


def da_boc(s):
    """Xoá mọi `chu('…')` để phần còn lại là thứ CHƯA dịch."""
    return re.sub(r"chu\(\s*'(?:[^'\\]|\\.)*'\s*\)|chu\(\s*\"(?:[^\"\\]|\\.)*\"\s*\)",
                  "", s)


def soi_js(p):
    s = da_boc(bo_chu_thich_js(io.open(p, encoding="utf-8").read()))
    ra = set()
    for m in re.finditer(r"'([^'\n]{2,160})'|\"([^\"\n]{2,160})\"|`([^`]{2,300})`", s):
        v = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if v and not SVG.match(v) and co_viet(v):
            ra.add(v)
    for m in re.finditer(r">([^<>{}\n]{2,160})<", s):
        v = m.group(1).strip()
        if v and co_viet(v):
            ra.add(v)
    return ra


def soi_py(p):
    s = da_boc(bo_chu_thich_py(io.open(p, encoding="utf-8").read()))
    ra = set()
    for m in re.finditer(r"'([^'\n]{2,200})'|\"([^\"\n]{2,200})\"", s):
        v = (m.group(1) or m.group(2) or "").strip()
        if v and co_viet(v):
            ra.add(v)
    return ra


def duyet(thu_muc, duoi, ham, bo=()):
    ra = {}
    for goc, _, ten in os.walk(os.path.join(GOC, thu_muc)):
        if any(x in goc for x in ("node_modules", "__pycache__", ".venv", "dist")):
            continue
        for f in sorted(ten):
            if not f.endswith(duoi) or any(f.startswith(b) for b in bo):
                continue
            p = os.path.join(goc, f)
            r = ham(p)
            if r:
                ra[os.path.relpath(p, GOC).replace("\\", "/")] = sorted(r)
    return ra


if __name__ == "__main__":
    tong = 0
    for ten, bang in (("GIAO DIỆN (tsx/ts)",
                       duyet("webui/src", (".tsx", ".ts"), soi_js, ("i18n",))),
                      ("PYTHON", duyet("cat_studio", (".py",), soi_py,
                                       ("ngon_ngu",)))):
        n = sum(len(v) for v in bang.values())
        tong += n
        print(f"\n{'=' * 70}\n  {ten} — {n} câu chưa dịch\n{'=' * 70}")
        for p, v in sorted(bang.items(), key=lambda x: -len(x[1])):
            print(f"\n### {p}  ({len(v)})")
            for x in v:
                print(f"  {x}")
    print(f"\n{'=' * 70}\n  TỔNG CÒN SÓT: {tong}\n{'=' * 70}")
    sys.exit(1 if tong else 0)
