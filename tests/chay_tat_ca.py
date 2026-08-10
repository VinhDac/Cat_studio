"""Chạy toàn bộ test.

    python tests\\chay_tat_ca.py

Không mở cửa sổ, không nối MT5 -> chạy được ở bất cứ đâu, kể cả trên CI.
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BAI = [
    ("test_danh_so.py", "Đánh số phân cấp · ghim số · ba trường hợp gặp lại khối cũ"),
    ("test_kho_va_lenh.py", "Kho backend · sổ lệnh (id của ta) · lưu trữ · tham số"),
    ("test_so_do_mau.py", "Sơ đồ mẫu Compress phải mở ra SẠCH"),
    ("test_doi_chieu_d02.py", "ĐỐI CHIẾU từng luật của D_02 — có luật nào rơi không"),
    ("test_nguon_nen.py", "Nguồn nến — luật MỘT DẢI LIỀN, ghép lô, nhận ra lỗ hổng"),
    ("test_tinh_toan.py", "Chỉ báo — khớp MT5, NaN chứ không 0, gộp khung không nhìn trước"),
    ("test_khop_lenh.py", "Khớp lệnh — đường đi 4 điểm, spread quy về Bid, gap"),
]

hong = []
for ten, mo_ta in BAI:
    print(f"\n{'=' * 68}\n▶ {ten}  —  {mo_ta}\n{'=' * 68}")
    r = subprocess.run([sys.executable, os.path.join(HERE, ten)])
    if r.returncode:
        hong.append(ten)

print(f"\n{'=' * 68}")
if hong:
    print(f"  ✘ HỎNG: {', '.join(hong)}")
else:
    print(f"  ✔ {len(BAI)}/{len(BAI)} bài đều qua")
print("=" * 68)
sys.exit(1 if hong else 0)
