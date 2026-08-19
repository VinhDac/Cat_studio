"""Kho NỀN TẢNG — thứ MỌI chiến lược đều có.

Giá, sổ lệnh, và "lệnh này". Ba nhóm này không do chiến lược nào đóng góp: chúng đến từ
sàn và từ sổ lệnh của chính app. Không vẽ gì cả thì chúng vẫn trả lời được.

Đối lập với `zone.py` — vùng giá chỉ tồn tại khi SƠ ĐỒ định nghĩa ra nó bằng một cổng,
nên mọi toán hạng ở đó trả `NaN` cho tới lúc có vùng.

⚠ KHÔNG có nhóm "Thời gian" (`giờ` / `thứ`), và đó là chủ ý — xem core.md §15.6. Chúng
là toán hạng dễ overfit nhất trong cả kho ("chỉ đánh 14h thứ Ba" không nói gì về thị
trường), và không đọc được sang thị trường chạy 24/7.
"""

TEN = "Nền tảng"
MA_SO = "nen_tang"
MO_TA = "Giá · sổ lệnh · lệnh này — có sẵn cho mọi chiến lược."

# Không tính chỉ báo nào, không nuôi bảng trạng thái nào.
CHI_BAO = []
BANG_TRANG_THAI = []

# `tabs = None` nghĩa là dùng được ở cả hai sơ đồ.
#: `loai` QUYẾT ĐỊNH Ô ĐƠN VỊ — xem `core.DON_VI`.
#:
#:   `khoang_cach` — một BỀ RỘNG giá (ATR, bề rộng zone). Quy đổi được: bps, %, × ATR…
#:   `muc_gia`     — một MỨC giá (close, MA, đỉnh zone). KHÔNG quy đổi:
#:                   `close / close × 10⁴` luôn ra 10000, vô nghĩa.
#:   `dem`         — số đếm. ⚠ PHẢI khai thêm `don_vi`: `zone_dem` đếm NẾN còn
#:                   `so_vi_the` đếm LỆNH, gộp chung thì nút chọn tham số sẽ mời
#:                   "số vị thế tối đa = 3 lệnh" vào ô "zone cần bao nhiêu nến".
#:   `boi_R`       — vốn đã tính bằng R.
#:   `dung_sai`    — không có vế phải.
#:
#: Tách `muc_gia` khỏi `khoang_cach` là chỗ dễ bỏ sót nhất: cả hai đều "đơn vị giá",
#: nhưng chỉ bề rộng mới chuẩn hoá được.
#: ⚠ `shift` ĐÃ BỎ khỏi toán hạng giá, và đây là lý do.
#:
#: Nó là ô số THỨ BA trên hàng điều kiện — cùng chỗ, cùng hình dạng với ô "chu kỳ" của
#: ATR/MA, nhưng nghĩa khác hẳn. Một ô trắng không nhãn mang hai nghĩa tuỳ toán hạng thì
#: không ai đọc ra được. Bỏ nó đi, ô thứ ba chỉ còn MỘT nghĩa: chu kỳ chỉ báo.
#:
#: Bỏ được vì nó chưa từng khác 1: mẫu dùng 1, cả 10 file đã lưu đều 1, và `doc_cot`
#: hiểu "thiếu shift" ĐÚNG BẰNG shift 1 (`i -= max(0, shift-1)`), nên hành vi không đổi
#: một chút nào. Muốn so `close[1] > close[5]` thì thêm lại sau — thêm một trường dễ hơn
#: nhiều so với gỡ một trường người ta đã học.
#: ⭐ HAI TRƯỜNG KHAI SỰ THẬT, KHÔNG KHAI KHẨU VỊ — core.md §18.12
#:
#: `chum` — mấy mức giá cùng ĐỌC RA TỪ MỘT CÁI. Bốn giá OHLC cùng một cây nến là một
#:          chùm; đỉnh/đáy của zone là một chùm khác.
#: `cuc`  — món này có phải CỰC TRỊ của chùm ấy không (`max` / `min`).
#:
#: Vì sao đủ để suy ra luật: trong CÙNG một chùm, cực trị có quan hệ CỐ ĐỊNH với mọi
#: thành viên khác — `Giá cao nhất ≥ Giá đóng cửa` là đúng theo định nghĩa của cây nến,
#: không phải một câu hỏi về thị trường. Hỏi nó là hỏi một HẰNG SỐ.
#:
#: ⚠ `open` và `close` đều KHÔNG phải cực trị, nên `open < close` (*"nến xanh"*) vẫn là
#: một câu hỏi thật — luật này không được chạm vào nó. Đó là phép thử của cả cách khai:
#: khai đúng thì nó tự chừa ra, khai theo cảm giác thì nó cắt nhầm.
#:
#: ⚠ `ma` KHÔNG thuộc chùm nến. Trung bình của n cây đóng cửa có thể nằm TRÊN đỉnh cây
#: hiện tại trong một nhịp giảm — không có quan hệ cố định nào cả.
TOAN_HANG = [
    # ---- Giá ---- (MỨC giá: so với một mức khác, không quy đổi)
    {"key": "close", "nhan": "Giá đóng cửa", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"], "chum": "nen",
     "mo_ta": "Luôn đọc nến ĐÃ ĐÓNG — nến đang chạy thì tín hiệu sẽ vẽ lại."},
    {"key": "open", "nhan": "Giá mở cửa", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"], "chum": "nen"},
    {"key": "high", "nhan": "Giá cao nhất", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"], "chum": "nen", "cuc": "max"},
    {"key": "low", "nhan": "Giá thấp nhất", "nhom": "Giá", "loai": "muc_gia",
     "tham_so": ["tf"], "chum": "nen", "cuc": "min"},

    # ---- Sổ lệnh ---- (cái gì đang TỒN TẠI)
    # ⭐ `sinh_boi` — món này CHỈ CÓ SỐ KHÁC 0 sau khi có khối Vào lệnh. core.md §18.12
    #
    # Chưa vào lệnh lần nào thì cả ba đứng yên ở 0, nên MỌI phép so với chúng ở phía
    # trên mọi khối Vào lệnh đều là hằng số — không riêng gì `> 0`, mà cả `< 30` (luôn
    # đúng). Và nếu chính cái cổng ấy chặn đường xuống khối Vào lệnh thì đó là VÒNG
    # TRÒN: muốn có số thì phải vào lệnh, muốn vào lệnh thì phải qua cổng ấy.
    #
    # Đo được: 14/68 sơ đồ câm chết đúng vì chuyện này (`so_vi_the` 4 · `so_lenh_cho` 2
    # · `zone_da_sinh_lenh` 8) — 21%.
    {"key": "so_vi_the", "nhan": "Số vị thế đang mở", "nhom": "Sổ lệnh",
     "loai": "dem", "don_vi": "lenh", "tham_so": [], "sinh_boi": "vao_lenh",
     "mo_ta": "= CountOpenPositions() của D_02."},
    {"key": "so_lenh_cho", "nhan": "Số lệnh chờ", "nhom": "Sổ lệnh", "loai": "dem",
     "don_vi": "lenh", "tham_so": [], "sinh_boi": "vao_lenh",
     "mo_ta": "D_02 chỉ cho ĐÚNG MỘT lệnh chờ sống một lúc (`if(m_has_pending) return`)."},
    # CẦU DAO RỦI RO. Bộ chạy đã nuôi sẵn con số này từ lâu (`PhienChay.ghi_tien` →
    # `ct.drawdown_pt`) nhưng chưa ai khai nó vào kho, nên nó là mã chết: máy tính ra
    # rồi không ai hỏi tới.
    #
    # ⚠ Đo trên VỐN ĐÃ CHỐT, không tính lãi nổi — cố ý. Sụt giảm theo lãi nổi đổi từng
    # nến M1, biến một cầu dao đáng ra ổn định thành thứ giật liên tục và bật/tắt lung
    # tung trong cùng một cú giá.
    {"key": "drawdown_pt", "nhan": "Sụt vốn hiện tại", "nhom": "Sổ lệnh", "loai": "dem",
     "don_vi": "pt_von", "tham_so": [], "sinh_boi": "vao_lenh",
     "mo_ta": "Vốn đang thấp hơn đỉnh vốn bao nhiêu phần trăm. Dùng làm cầu dao: "
              "\"sụt quá 5 % thì ngừng vào lệnh\". Tính trên vốn ĐÃ CHỐT (lệnh đã "
              "đóng), không tính lãi nổi."},

    # ---- Lệnh đang xét — CHỈ sơ đồ Manage ----
    # Manage chạy một lượt cho MỖI lệnh đang sống, nên "lệnh này" luôn có nghĩa ở đó.
    # Ở Entry thì chưa có lệnh nào để nói tới → soát tĩnh báo lỗi.
    {"key": "lenh_da_khop", "nhan": "Lệnh này đã khớp", "nhom": "Lệnh này",
     "loai": "dung_sai", "tham_so": [], "dung_sai": True, "tabs": ["manage"]},
    {"key": "lenh_sl_hoa_von", "nhan": "SL của lệnh này đã ở hoà vốn",
     "nhom": "Lệnh này", "loai": "dung_sai", "tham_so": [], "dung_sai": True,
     "tabs": ["manage"],
     "mo_ta": "= `if(sl >= entry && sl > 0) continue` của ManageBreakEven, đảo lại. "
              "Thiếu nó thì Manage bắn lệnh sửa SL lại mỗi nến."},
    {"key": "lenh_lai_R", "nhan": "Lãi của lệnh này (× R)", "nhom": "Lệnh này",
     "loai": "boi_R", "tham_so": [], "tabs": ["manage"],
     "mo_ta": "R = khoảng cách SL lúc VÀO LỆNH, chốt cứng theo lệnh — không tính lại."},
    # HƯỚNG. Thiếu nó thì Manage không phân biệt được lệnh mua với lệnh bán, nên mọi
    # luật quản lý đều buộc phải đối xứng — không viết được "lệnh mua mà giá tụt dưới
    # MA thì đóng".
    {"key": "lenh_la_mua", "nhan": "Lệnh này là lệnh MUA", "nhom": "Lệnh này",
     "loai": "dung_sai", "tham_so": [], "dung_sai": True, "tabs": ["manage"],
     "mo_ta": "SAI nghĩa là lệnh BÁN — chỉ có hai hướng, không có ca thứ ba."},
    # THỜI GIAN SỐNG. Thiếu nó thì Manage chỉ phản ứng được với GIÁ và ZONE, không bao
    # giờ phản ứng được với thời gian: không viết được "lệnh chờ treo 20 nến không khớp
    # thì huỷ". `Lenh.so_nen_song()` đã có sẵn từ lâu, chỉ chưa ai khai vào kho.
    {"key": "lenh_so_nen_song", "nhan": "Lệnh này đã sống bao nhiêu nến",
     "nhom": "Lệnh này", "loai": "dem", "don_vi": "nen", "tham_so": [],
     "tabs": ["manage"],
     "mo_ta": "Đếm từ nến ĐẶT lệnh, không phải nến khớp — nên nó đo được cả quãng lệnh "
              "chờ nằm treo. Đếm bằng nến TRỤC (nhịp của khối Bắt đầu), không phải M1."},
    # ⚠ `can_zone`: hỏi câu này mà sơ đồ KHÔNG có cổng zone thì nó luôn trả SAI — đúng
    # về mặt sự thật nhưng vô nghĩa về mặt câu hỏi. Khai ra để soát tĩnh chặn ngay, thay
    # vì để người dùng vẽ xong rồi ngồi nghĩ vì sao cổng không bao giờ khớp.
    {"key": "lenh_thuoc_zone", "nhan": "Lệnh này còn thuộc zone hiện hành",
     "nhom": "Lệnh này", "loai": "dung_sai", "tham_so": [], "dung_sai": True,
     "tabs": ["manage"], "can_zone": True,
     "mo_ta": "Zone đẻ ra lệnh này CÓ CÒN là zone hiện hành không. Gộp cả ba ca vào "
              "một câu: zone ấy chết mà chưa có zone mới · đã có zone mới · vẫn là nó. "
              "Lệnh chờ neo vào MÉP một zone đã chết thì cái neo hết nghĩa — nên đây là "
              "câu hỏi đúng để huỷ lệnh chờ, thay cho phép đoán gián tiếp qua ATR."},
]
