"""RÚT CÂU TRỌN từ mã Python — đọc CÂY CÚ PHÁP, không đọc từng dòng.

    python tools/rut_cau_py.py [--khuon]

⚠ VÌ SAO KHÔNG QUÉT DÒNG. Python nối chuỗi ngầm qua nhiều dòng:

```python
e(f'Loại hành động "{t}" không còn được hỗ trợ — xoá dòng này hoặc thay '
  f"bằng loại khác.")
```

Quét dòng ra HAI mảnh, mà thứ tới tay người dùng là MỘT câu. Dịch từng mảnh rồi ghép
lại theo trật tự tiếng Anh thì sai ngữ pháp — nên phải rút đúng câu trọn. `ast` gộp sẵn
phép nối ngầm thành một `Constant`, nên chỉ việc đi bộ trên cây.

HAI LOẠI, tách bạch:

```
CÂU PHẲNG   ast.Constant   dịch được ngay bằng từ điển
CÂU KHUÔN   ast.JoinedStr  có nội suy `{…}` — phải đổi thành khuôn `.format()` trước
```
"""
import ast
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAU = ("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợ"
       "ùúủũụừứửữựỳýỷỹỵĂÂĐÊÔƠƯÀÁẢÃẠÈÉẺẼẸÌÍỈĨỊÒÓỎÕỌÙÚỦŨỤỲÝỶỸỴ")


def co_viet(v):
    return isinstance(v, str) and any(c in DAU for c in v)


def rut(p):
    """`(câu phẳng, câu khuôn)` của một file."""
    try:
        cay = ast.parse(io.open(p, encoding="utf-8").read())
    except SyntaxError:
        return set(), set()
    phang, khuon = set(), set()
    # Bỏ docstring: chúng là `Expr(Constant)` đứng ĐẦU thân module/hàm/lớp.
    tai_lieu = set()
    for n in ast.walk(cay):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            th = getattr(n, "body", None) or []
            if th and isinstance(th[0], ast.Expr) and isinstance(th[0].value,
                                                                ast.Constant):
                tai_lieu.add(id(th[0].value))
    # ⚠ BỎ mảnh nằm TRONG f-string. `ast.walk` đi vào cả ruột `JoinedStr`, nên
    # `f"Khối {ten} chưa chọn cách tính."` đẻ ra một mảnh phẳng `" chưa chọn cách
    # tính."` — dịch mảnh ấy là dịch nửa câu. Đã đếm nhầm 686 câu vì chuyện này.
    trong_khuon = {id(x) for n in ast.walk(cay) if isinstance(n, ast.JoinedStr)
                   for x in n.values if isinstance(x, ast.Constant)}
    for n in ast.walk(cay):
        if (isinstance(n, ast.Constant) and id(n) not in tai_lieu
                and id(n) not in trong_khuon and co_viet(n.value)):
            phang.add(n.value)
        elif isinstance(n, ast.JoinedStr):
            v = "".join(x.value if isinstance(x, ast.Constant) else "{}"
                        for x in n.values)
            if co_viet(v):
                khuon.add(v)
    return phang, khuon


if __name__ == "__main__":
    chi_khuon = "--khuon" in sys.argv
    tp, tk = 0, 0
    for goc, _, ten in os.walk(os.path.join(GOC, "cat_studio")):
        if "__pycache__" in goc:
            continue
        for f in sorted(ten):
            if not f.endswith(".py") or f == "ngon_ngu.py":
                continue
            p = os.path.join(goc, f)
            ph, kh = rut(p)
            tp += len(ph)
            tk += len(kh)
            ds = sorted(kh if chi_khuon else ph)
            if ds:
                print(f"\n### {os.path.relpath(p, GOC)}  ({len(ds)})")
                for x in ds:
                    print("  " + x.replace("\n", "\\n"))
    print(f"\n{'=' * 70}\n  CÂU PHẲNG {tp} · CÂU KHUÔN {tk}\n{'=' * 70}")
