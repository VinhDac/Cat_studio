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
    ("test_bo_chay.py", "Bộ chạy — thứ tự trong nhịp, luật lùi, tính xác định"),
    ("test_nhat_ky.py", "Nhật ký — bản ghi rỗng chữ, nhãn dựng lại, ghi/đọc ngược"),
    # ⚠ Ba module chạm TIỀN THẬT. Trước bài này cổng kiểm vẫn báo "9/9 qua" kể cả
    #    khi bảng xử lý retcode bị bẻ hỏng — tức bản phát hành biết đặt lệnh sai
    #    vẫn ra khỏi cửa. Chạy trên SÀN GIẢ nên không cần MT5.
    ("test_gui_lenh.py", "Tầng phòng vệ + vòng hiệu chuẩn — trên sàn giả"),
    ("test_zone.py", "Cổng ZONE định nghĩa zone · MỐC NEO của khối Vào lệnh"),
    ("test_nguoi_bay.py", "NGƯỜI BÀY — bày nước đi hợp lệ · đọc ngược sơ đồ · hai chiều"),
    ("test_cham_diem.py", "CHẤM ĐIỂM — theo TUẦN, bằng TIỀN · cửa chặn lỗ hổng √(N−1)"),
    ("test_tim_kiem.py", "DÒ NGẪU NHIÊN — đối chứng · bốc hai tầng · tái lập được"),
    ("test_luot_tim.py", "LƯỢT TÌM — sống NGOÀI cửa sổ · dừng được · nổ thì nói to"),
    ("test_song_song.py", "SONG SONG — 8 nhân phải ra ĐÚNG kết quả 1 nhân"),
    ("test_cat_tia.py", "PHÂN BỔ · CẮT TỈA — tiền theo KHỐI · luật ĐA SỐ cửa sổ"),
    ("test_doc_giao_dien.py", "MỌI doc tới giao diện phải ĐỦ THẺ — luật MỘT CỬA"),
    ("test_dat_ten.py", "Số gõ tay hai chỗ → cảnh báo + nút đặt tên"),
    ("test_giao_dien.py", "Biến CSS ma — thứ hỏng LẶNG, build vẫn sạch"),
    ("test_o_so.py", "Ô số — gõ TỪNG PHÍM, số thập phân không được nuốt"),
    ("test_ngon_ngu.py", "Ngôn ngữ — từ điển không được nói dối"),
]

hong = []
for ten, mo_ta in BAI:
    print(f"\n{'=' * 68}\n▶ {ten}  —  {mo_ta}\n{'=' * 68}")
    # ⭐ ÉP TIẾNG VIỆT cho mọi bài kiểm. Nhiều bài đối chiếu CHỮ trên hộp khối, mà chữ
    # ấy do Python sinh theo cài đặt `ngon_ngu` NGƯỜI DÙNG đã lưu trên đĩa (§18.14).
    # Không ép thì kết quả bộ kiểm phụ thuộc vào việc người dùng đang để app ở ngôn ngữ
    # nào — đã cắn: bật tiếng Anh xong chạy `chay_tat_ca` là 6 phép đỏ, mà mã nguồn
    # không hề sai. Bộ kiểm phải nói cùng một câu trên mọi máy.
    moi = dict(os.environ, CAT_NGON_NGU="vi")
    r = subprocess.run([sys.executable, os.path.join(HERE, ten)], env=moi)
    if r.returncode:
        hong.append(ten)

print(f"\n{'=' * 68}")
if hong:
    print(f"  ✘ HỎNG: {', '.join(hong)}")
else:
    print(f"  ✔ {len(BAI)}/{len(BAI)} bài đều qua")
print("=" * 68)
sys.exit(1 if hong else 0)
