"""Ô SỐ — cầu nối sang bài kiểm JavaScript `webui/kiem/o_so.mjs`.

VÌ SAO PHẢI CÓ
--------------
Ô số của app từng NUỐT DẤU CHẤM: ép `Number()` ngay từng phím thì `"1."` ra `1`, state
không đổi, React ghi đè ô về `"1"` — dấu chấm biến mất, phím kế cho `"15"`. Stop Loss
1,5 × ATR lặng lẽ thành **15 × ATR**, sai gấp mười, không một dòng cảnh báo.

⚠ Dán `1.5` một phát thì LỌT. Chỉ gõ từng phím mới lộ — nên bài kiểm bên kia mô phỏng
đúng chuỗi phím, chứ không set value một lần.

Bài này chỉ gọi sang đó, để `chay_tat_ca.py` (cổng kiểm trước khi đóng gói) không bỏ sót
phía giao diện. Thiếu Node thì BÁO RÕ và trượt, không lặng lẽ bỏ qua — một bài kiểm tự
tắt khi thiếu công cụ là một bài kiểm nói dối.

Chạy:  python tests\test_o_so.py
"""
import io
import os
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAI = os.path.join(GOC, "webui", "kiem", "o_so.mjs")

r = subprocess.run(["node", BAI], cwd=GOC, shell=(os.name == "nt"),
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print((r.stdout or "").rstrip())
if r.stderr.strip():
    print(r.stderr.rstrip(), file=sys.stderr)
if r.returncode != 0 and not (r.stdout or "").strip():
    print("  ✘ KHÔNG CHẠY ĐƯỢC node — bài kiểm giao diện chưa được canh.")
sys.exit(r.returncode)
