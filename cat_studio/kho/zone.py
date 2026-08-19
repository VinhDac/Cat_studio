"""Kho ZONE — một VÙNG GIÁ do chính sơ đồ định nghĩa.

Zone không thuộc chiến lược nào. Nó là một **cơ chế chung**: một vùng giá được đắp dần
qua từng nến, và điều kiện "nến này có được vào vùng không" là **cái cổng người dùng vẽ**
(khối mang cờ `cong_zone`). Đổi cổng là đổi hẳn định nghĩa vùng — nén biến động, volume
thấp, nằm trong một dải, gì cũng được.

Vì sao nó KHÔNG nằm trong `nen_tang.py`: `nen_tang` là *"thứ MỌI chiến lược đều có"*.
Zone thì không — sơ đồ không vẽ cổng zone thì không có zone nào, và mọi toán hạng ở đây
trả `NaN`. Ba loại khác nhau, ba chỗ khác nhau:

    nen_tang    luôn có          giá · sổ lệnh · lệnh này
    chi_bao     ai gọi thì có    atr · ma
    zone        có khi sơ đồ ĐỊNH NGHĨA nó

⚠ **File này từng tên là `engine_d02.py`,** vì cơ chế vùng ban đầu là ý tưởng riêng của
EA D_02 (đếm nến có `atr_bps` dưới ngưỡng). Nhưng cái đó đã hết từ lâu: `Engine.moi_nen()`
rỗng, điều kiện đếm chuyển hẳn vào cổng trong sơ đồ. Chỉ có cái TÊN và mấy dòng mô tả là
còn kẹt lại — và mô tả sai thì hộp thoại **File → Kho** dạy sai người dùng. Xem core.md
§15.3.
"""

TEN = "Zone"
MA_SO = "zone"
MO_TA = ("Một vùng giá đắp dần qua từng nến. Cổng zone trong sơ đồ quyết định nến nào "
         "được vào vùng — nên định nghĩa vùng là của người vẽ, không phải của app.")

CHI_BAO = []

# Bảng vùng — thứ bộ chạy tự nuôi qua thời gian, không tính được từ một nến đơn lẻ.
BANG_TRANG_THAI = [{
    "key": "zone",
    "nhan": "Zone",
    "mo_ta": "Sinh ra khi CỔNG ZONE khớp lần đầu, lớn thêm mỗi lần cổng còn khớp, và "
             "CHẾT ngay nhịp cổng trượt. Mỗi vùng mang một id riêng — lệnh đặt từ vùng "
             "nào thì ghi id vùng đó, nên \"một vùng một lệnh\" là phép tra bảng chứ "
             "không phải cờ ẩn.",
    "truong": [
        {"ten": "id", "kieu": "chuỗi", "vd": "V-0003"},
        {"ten": "so_nen", "kieu": "số nguyên", "vd": "12"},
        {"ten": "dinh / day", "kieu": "giá", "vd": "2412.80 / 2409.15"},
        {"ten": "atr_tb", "kieu": "giá",
         "vd": "trung bình ATR suốt cả vùng — dùng để đo 1R"},
        {"ten": "atr_hien_tai", "kieu": "giá",
         "vd": "ATR nến mới nhất — dùng để đo đệm vào lệnh"},
        {"ten": "song", "kieu": "đúng/sai", "vd": "cổng còn khớp hay đã trượt"},
    ],
    "luat": [
        "Nến nào vào vùng là do CỔNG ZONE trong sơ đồ quyết — app không có ngưỡng nào "
        "viết cứng.",
        "Cổng được xét trên ZONE THỬ: bản sao đã cộng cây nến đang xét. Nhờ vậy "
        "\"bề rộng ≤ N\" là một HẠN MỨC, kiểm trước khi tiêu.",
        "Đỉnh/đáy lấy từ High/Low của chính những nến đã vào vùng. Đọc nến ĐÃ ĐÓNG, "
        "không repaint.",
        "atr_hien_tai và atr_tb là HAI thứ khác nhau — xem đơn vị `atr` vs `atr_zone`.",
        "Cổng trượt → vùng CHẾT ngay, dù đang có lệnh chờ treo trên mép nó.",
        "Mỗi lúc chỉ có MỘT vùng sống. Vùng chết rồi nến sau mới mở được vùng mới.",
    ],
}]

TOAN_HANG = [
    {"key": "zone_dem", "nhan": "Zone — số nến", "nhom": "Zone", "loai": "dem",
     "don_vi": "nen", "tham_so": [],
     "mo_ta": "Vùng hiện hành đã nuốt bao nhiêu nến."},
    # ⭐ CHÙM `zone` — `đỉnh ≥ đáy` là đúng theo ĐỊNH NGHĨA của vùng, không phải một câu
    # hỏi về thị trường. Và khác chùm `nen`, hai món này KHÔNG có khung giờ, nên không
    # có cách nào tách chúng ra thành hai câu khác nhau: nước so chúng với nhau bị gạch
    # thẳng khỏi kho, không phải che bằng mặt nạ. core.md §18.12
    {"key": "zone_HH", "nhan": "Zone — đỉnh (HH)", "nhom": "Zone", "loai": "muc_gia",
     "tham_so": [], "chum": "zone", "cuc": "max",
     "mo_ta": "Lệnh chờ MUA thường neo vào đây."},
    {"key": "zone_LL", "nhan": "Zone — đáy (LL)", "nhom": "Zone", "loai": "muc_gia",
     "tham_so": [], "chum": "zone", "cuc": "min",
     "mo_ta": "Lệnh chờ BÁN thường neo vào đây."},
    # BỀ RỘNG — quy đổi được. `zone_range ≤ 4 [× ATR]` thay cho `zone_range_atr ≤ 4`.
    {"key": "zone_range", "nhan": "Zone — bề rộng", "nhom": "Zone",
     "loai": "khoang_cach", "tham_so": [],
     "mo_ta": "Đỉnh trừ đáy. Lọc vùng bị tin tức thổi rộng — so bằng đơn vị × ATR."},
    {"key": "zone_atr_tb", "nhan": "Zone — ATR trung bình", "nhom": "Zone",
     "loai": "khoang_cach", "tham_so": [],
     "mo_ta": "Mức nhiễu thật suốt cả vùng → dùng nó định nghĩa 1R."},
    # ⭐ HỢP LỆ là một KHÁI NIỆM, không phải một bộ điều kiện chép đi chép lại.
    #
    # Định nghĩa nằm ở phần "hợp lệ" của chính cổng zone (`dk_hop_le`), viết MỘT lần.
    # Ở đây chỉ là cái tên để mọi nơi khác gọi tới — Entry hỏi trước khi sinh lệnh,
    # Manage hỏi trước khi huỷ lệnh chờ. Trước đó phải chép hai vế `số nến ≥ K` và
    # `bề rộng ≤ N` sang từng cổng, và hai bản chép thì sớm muộn lệch nhau.
    #
    # KHÔNG cất trạng thái: đây là hàm thuần của zone lúc này, tính lại mỗi lần được
    # hỏi. Máy trạng thái 5 giá trị của D_02 vẫn không quay lại (§7.5).
    {"key": "zone_hop_le", "nhan": "Zone hiện hành hợp lệ", "nhom": "Zone",
     "loai": "dung_sai", "dung_sai": True, "tham_so": [],
     "mo_ta": "Zone hiện hành có đạt phần \"hợp lệ\" của cổng zone không. Chưa có zone "
              "→ CHƯA CÓ SỐ (cổng trượt), không phải SAI. "
              "⚠ Nhãn mang chữ HIỆN HÀNH là cố ý: nó luôn hỏi về zone đang đếm lúc "
              "này. Cạnh dòng \"Lệnh này còn thuộc zone hiện hành\", hai dòng phải "
              "cùng một chủ ngữ — gọi bằng hai tên thì đọc ra thành hai zone khác "
              "nhau, mà thật ra chỉ có một. Và KHÔNG gọi là \"Zone mới\": ở Entry, "
              "zone hiện hành chính là zone sắp vào lệnh, chẳng mới gì cả — một cái "
              "nhãn phải đúng khi đứng một mình."},
    {"key": "zone_da_sinh_lenh", "nhan": "Zone này đã sinh lệnh", "nhom": "Zone",
     "loai": "dung_sai", "tham_so": [], "sinh_boi": "vao_lenh", "dung_sai": True,
     "mo_ta": "Là phép tra sổ lệnh xem có lệnh nào mang `zone_id` của zone hiện hành "
              "không — không phải cờ ẩn. Tính cả lệnh đã đóng: một vùng một lệnh."},
]


# ---------------------------------------------------------------------------
# MÁY VÙNG — code nằm CÙNG FILE với `BANG_TRANG_THAI["luat"]` ở trên
# ---------------------------------------------------------------------------
# Cố ý đặt ở đây chứ không trong `bo_chay.py`. Mấy câu "luật" phía trên mô tả đúng cái
# máy này bằng tiếng Việt; để code ở file khác thì sớm muộn hai bên nói khác nhau.
#
# ⚠ Và nó ĐÃ nói khác nhau một lần: bảng luật còn ghi "Nến nén = atr_bps < ngưỡng" rất
# lâu sau khi `moi_nen()` rỗng đi. Ở gần nhau thì DỄ sửa cùng lúc, nhưng không có gì
# BẮT BUỘC phải sửa cùng lúc — nên vẫn phải tự nhắc.
from .. import so_lenh                                                      # noqa: E402,F401


class Engine:
    """Trả lời 7 toán hạng nhóm "Zone".

    Bề mặt hẹp, đúng hai việc:
      * `moi_nen(ctx)` — runtime gọi MỘT LẦN mỗi nến quyết định. Nay RỖNG, xem dưới.
      * `doc(ten, ctx)` — trả giá trị cho từng toán hạng.
    """

    #: Tham số bắt buộc phải có trong bảng tham số. Thiếu là báo lỗi TRƯỚC khi chạy,
    #: chứ không phải chết ở nến thứ 40.000.
    #:
    #: Chỉ còn `chu_ky_atr`: vùng cộng dồn ATR để tính `zone_atr_tb` (định nghĩa 1R).
    #: Ngưỡng đếm thì KHÔNG bắt buộc nữa — nó nằm trong cổng người dùng vẽ, đặt tên gì
    #: cũng được. Bắt buộc một cái tên cụ thể là ép mọi chiến lược đếm theo kiểu D_02.
    THAM_SO_CAN = ("chu_ky_atr",)

    def moi_nen(self, ctx):
        """Một nến quyết định vừa đóng.

        ⚠ HÀM NÀY ĐÃ RỖNG, và đó là cả điểm của lần sửa đó.

        Trước đây nó là một CỖ MÁY ẨN: chạy mỗi nến, trước mọi sơ đồ, và viết cứng
        điều kiện đếm là "atr_bps dưới ngưỡng". Hậu quả:
          · nhìn sơ đồ không thấy vùng sinh ra ở đâu — nó chỉ đột nhiên có;
          · chiến lược thứ hai muốn đếm theo điều kiện khác (volume thấp, nến trong
            dải Bollinger, gì cũng được) thì phải SỬA ENGINE, tức lời hứa "thêm một
            chiến lược = thêm MỘT file vào kho/" tan.

        Giờ vùng do CỔNG mang cờ `cong_zone` trong chính sơ đồ định nghĩa — xem
        `bo_chay._nuoi_zone`. Điều kiện đếm thành tham số mà không cần thêm ô cấu hình
        nào: nó là cái cổng người dùng vẽ ra.

        Giữ lại hàm vì `Engine` vẫn còn việc thứ hai: `doc()`.
        """

    def doc(self, ten, ctx):
        """Giá trị của một toán hạng nhóm "Zone" ngay lúc này.

        CHƯA CÓ VÙNG NÀO → trả `NaN` chứ không trả 0. `0` là lời nói dối lọt qua mọi
        phép so: `zone_range <= 4 [× ATR]` sẽ ĐÚNG trong lúc chẳng có vùng nào tồn tại."""
        so = ctx.so
        # ZONE THỬ chỉ khác `None` trong đúng lúc CỔNG ZONE đang được đánh giá — nó là
        # zone SẼ THÀNH nếu nến này được nuốt (`bo_chay._dat_zone_thu`). Mọi khối khác
        # đọc zone thật. Nhờ nó mà cổng zone hỏi được về chính zone nó sắp tạo ra.
        thu = ctx.zone_thu
        if ten == "zone_hop_le":
            # Bộ chạy trả lời, không phải engine: nó phải đánh giá lại cả một danh sách
            # điều kiện, mà phép so + quy đổi đơn vị nằm ở `bo_chay`. Engine hỏi qua
            # `ctx` đúng như nó vẫn hỏi `ctx.so` và `ctx.chi_bao`.
            return ctx.zone_hop_le()
        if ten == "zone_da_sinh_lenh":
            # ⚠ Phải tra theo ID CỦA BẢN THỬ. Bỏ id đi thì `zone_da_sinh_lenh()` tự lấy
            # zone hiện hành — mà lúc có lỗ hổng dữ liệu, zone hiện hành là zone CŨ (đã
            # sinh lệnh) trong khi bản thử là zone MỚI tinh. Cổng sẽ đọc "đã sinh lệnh"
            # cho một zone chưa hề tồn tại.
            return so.zone_da_sinh_lenh(thu.id) if thu is not None \
                else so.zone_da_sinh_lenh()
        v = thu if thu is not None else so.zone_hien_hanh()
        if v is None:
            return float("nan")
        return {
            "zone_dem": lambda: float(v.so_nen),
            "zone_HH": lambda: float(v.dinh),
            "zone_LL": lambda: float(v.day),
            "zone_range": lambda: float(v.rong),
            "zone_atr_tb": lambda: float(v.atr_tb),
        }[ten]()


#: Toán hạng nào do máy vùng trả lời — `kho.CAN_ZONE` gom từ đây, không chép tay.
#:
#: Tên cũ là `ENGINE_TRA_LOI`, đổi vì không còn "engine" nào cả: khái niệm engine tan
#: khi cơ chế vùng thành cơ chế chung (core.md §15.3).
ZONE_TRA_LOI = ("zone_dem", "zone_HH", "zone_LL", "zone_range",
                "zone_atr_tb", "zone_da_sinh_lenh", "zone_hop_le")
