"""Cat_Studio — lõi ứng dụng.

Mọi module của app nằm trong gói này; ở thư mục gốc chỉ còn `app_web.py`, tức ĐIỂM KHỞI
ĐỘNG. Nhìn vào gốc là thấy ngay "chạy cái gì", còn "gồm những gì" thì mở gói ra xem.

Thứ tự phụ thuộc, đọc từ dưới lên — không có vòng nào:

    luu_tru      chỗ DUY NHẤT biết file nằm ở đâu
    nguon_nen    chỗ DUY NHẤT biết MetaTrader5
    tinh_toan    chỉ báo thuần (mảng vào, mảng ra)
    khop_lenh    mô hình khớp lệnh thuần
    so_lenh      sổ lệnh + vùng nén
    core         đồ thị, đánh số, soát lỗi, chuẩn hoá tài liệu
    kho/         danh mục toán hạng · chỉ báo · engine (app TỰ GOM từ đây)
    bo_chay      vòng lặp backtest — ráp tất cả những thứ trên
    nhat_ky      nhật ký lượt chạy
    lich_su      lịch sử các lần chạy
    khung_cua_so vá khung cửa sổ Win32 cho thanh tiêu đề tự vẽ
    api          bề mặt DUY NHẤT giao diện gọi tới

Gói CỐ Ý không re-export gì ở đây: `from cat_studio import core` phải nạp đúng module đó,
không kéo theo cả cây. Nạp `api` là kéo theo numpy và MetaTrader5, mà `tests/test_danh_so`
chỉ cần `core`.
"""
