"""SỔ LỆNH — bảng `lệnh` và bảng `vùng nén`, mỗi thứ một id của CHÍNH TA.

Vì sao id phải là của ta, không mượn ticket MT5:

  · Backtest KHÔNG có ticket. Nếu định danh phụ thuộc MT5 thì nửa hệ thống không chạy
    được khi chưa nối sàn.
  · D_02 không có id nối lệnh chờ với vị thế sinh ra từ nó, nên `CheckPendingActivation`
    phải ĐOÁN bằng `HasOpenPosition()` — "có vị thế nào bất kỳ không". Lệnh chờ bị huỷ
    từ ngoài trong lúc còn vị thế cũ là nó đọc nhầm thành "đã khớp". Có id thì hỏi thẳng.
  · `ticket` vẫn giữ, nhưng chỉ là MỘT CỘT để bắc cầu sang live.

Id đếm tăng, không phải uuid: `L-0001`, `V-0003`. Đọc log là biết ngay thứ tự, và
CHẠY LẠI CÙNG DỮ LIỆU RA CÙNG ID — so hai lần backtest được. uuid thì mất cả hai.

Sổ này KHÔNG biết gì về sơ đồ. Nó chỉ giữ dữ liệu và trả lời câu hỏi; ai quyết định mở
hay sửa lệnh là việc của bộ chạy.
"""

# Trạng thái một lệnh. Cố ý CHỈ ba giá trị — mọi câu hỏi khác đều suy ra được.
CHO = "cho"        # lệnh chờ đang treo, chưa khớp
MO = "mo"          # đã khớp, đang là vị thế
DONG = "dong"      # đã đóng (TP/SL/đóng tay) hoặc lệnh chờ đã bị huỷ

LY_DO_DONG = {
    "tp": "chạm Take Profit",
    "sl": "chạm Stop Loss",
    "huy": "huỷ lệnh chờ",
    "dong_tay": "khối Sửa lệnh đóng",
    "het_du_lieu": "hết dữ liệu backtest",
}

MUA = "mua"
BAN = "ban"


class Zone:
    """Một đợt nén. Sống chừng nào CỔNG ZONE còn qua, chết ngay nhịp cổng trượt.

    ⚠ Không còn dính cứng vào "atr dưới ngưỡng" nữa: điều kiện đếm là chính cái cổng
    mang cờ `cong_zone` trong sơ đồ — xem `bo_chay._nuoi_zone`."""

    def __init__(self, id, nen):
        self.id = id
        self.nen_bat_dau = nen
        self.so_nen = 0
        self.dinh = None
        self.day = None
        self.atr_tong = 0.0
        self.atr_hien_tai = 0.0
        self.song = True

    @property
    def atr_tb(self):
        """ATR trung bình CẢ vùng — thứ định nghĩa 1R.

        Khác hẳn `atr_hien_tai` (đo đệm vào lệnh). Tách hai cái là có chủ ý: nhờ vậy
        mỗi lệnh rủi ro một R tương đương dù vùng rộng hẹp khác nhau."""
        return self.atr_tong / self.so_nen if self.so_nen else 0.0

    @property
    def rong(self):
        if self.dinh is None or self.day is None:
            return 0.0
        return self.dinh - self.day

    def them_nen(self, cao, thap, atr):
        self.so_nen += 1
        self.atr_tong += atr
        self.atr_hien_tai = atr
        self.dinh = cao if self.dinh is None else max(self.dinh, cao)
        self.day = thap if self.day is None else min(self.day, thap)


class Lenh:
    """Một lệnh, từ lúc đặt tới lúc chết.

    `R` chốt cứng LÚC VÀO và không bao giờ tính lại. Nếu tính lại theo ATR hiện tại thì
    "lãi 1R" đổi nghĩa giữa chừng, và mốc dời SL về hoà vốn trôi theo thị trường."""

    def __init__(self, id, zone_id, sinh_tai, huong, loai, lot,
                 gia_dat, sl, tp, R, nen):
        self.id = id
        self.zone_id = zone_id          # vùng nén đẻ ra nó — thay cho COMP_CONSUMED
        self.sinh_tai = sinh_tai        # id khối "Vào lệnh"
        self.huong = huong
        self.loai = loai                # market | stop | limit
        self.lot = lot
        self.gia_dat = gia_dat
        self.sl = sl
        self.tp = tp
        self.R = R
        self.trang_thai = MO if loai == "market" else CHO
        self.nen_dat = nen
        self.nen_khop = nen if loai == "market" else None
        # Nhịp M1 lúc khớp. `nen_khop` chỉ là nến TRỤC, mà một nến trục chứa nhiều nhịp
        # M1 — thiếu ô này thì không xếp nổi thứ tự giữa cú khớp và các lượt Manage rơi
        # cùng nến đó. Khai ở đây chứ không chỉ gán trong `khop()`: lệnh chưa khớp bao
        # giờ cũng phải ĐỌC được thuộc tính này, không thì mỗi chỗ đọc phải `getattr`.
        self.j_khop = None
        self.nen_dong = None
        self.gia_khop = gia_dat if loai == "market" else None
        self.gia_dong = None
        self.ly_do_dong = None
        self.ticket = None              # CHỈ điền khi chạy live; backtest để trống

    # ---- câu hỏi các toán hạng "Lệnh này" hỏi ----
    @property
    def da_khop(self):
        return self.trang_thai in (MO, DONG) and self.gia_khop is not None

    @property
    def con_song(self):
        return self.trang_thai != DONG

    @property
    def sl_o_hoa_von(self):
        """SL đã được dời về giá vào chưa.

        Suy ra từ VỊ TRÍ của SL so với giá vào, không phải một cờ riêng — y như
        `if(sl >= entry && sl > 0.0) continue` của D_02, và không thể lệch với thực tế."""
        if not self.da_khop or self.sl in (None, 0):
            return False
        return self.sl >= self.gia_khop if self.huong == MUA else self.sl <= self.gia_khop

    def lai_R(self, gia):
        """Lãi hiện tại tính theo bội R. Chưa khớp thì chưa có lãi."""
        if not self.da_khop or not self.R:
            return 0.0
        d = gia - self.gia_khop
        return (d if self.huong == MUA else -d) / self.R

    def so_nen_song(self, nen):
        return max(0, nen - self.nen_dat)

    def tom_tat(self):
        return {"id": self.id, "zone_id": self.zone_id, "sinh_tai": self.sinh_tai,
                "huong": self.huong, "loai": self.loai, "lot": self.lot,
                "gia_dat": self.gia_dat, "gia_khop": self.gia_khop,
                "sl": self.sl, "tp": self.tp, "R": self.R,
                "trang_thai": self.trang_thai, "ly_do_dong": self.ly_do_dong,
                "nen_dat": self.nen_dat, "nen_khop": self.nen_khop,
                "nen_dong": self.nen_dong, "gia_dong": self.gia_dong,
                "ticket": self.ticket}


class SoLenh:
    """Sổ giữ mọi lệnh và mọi vùng của MỘT lần chạy.

    Giữ cả lệnh đã chết chứ không xoá đi: "vùng này đã sinh lệnh chưa" phải trả lời
    được kể cả khi lệnh đó đã đóng, nếu không thì cùng một cú nén lại đẻ lệnh lần nữa."""

    def __init__(self):
        self.lenh = []
        self.zone = []
        self._dem_lenh = 0
        self._dem_vung = 0

    # ---- vùng nén ----
    def mo_zone(self, nen):
        self._dem_vung += 1
        v = Zone(f"V-{self._dem_vung:04d}", nen)
        self.zone.append(v)
        return v

    def zone_hien_hanh(self):
        return self.zone[-1] if self.zone and self.zone[-1].song else None

    def dong_zone(self):
        v = self.zone_hien_hanh()
        if v:
            v.song = False
        return v

    def zone_da_sinh_lenh(self, zone_id=None):
        """Có lệnh nào mang id vùng này không — thay cho `COMP_CONSUMED`.

        Là phép TRA BẢNG, không phải cờ ẩn. Và tính cả lệnh đã chết: một cú nén một
        lệnh, kể cả khi lệnh đó đã đóng từ lâu."""
        if zone_id is None:
            v = self.zone_hien_hanh()
            if not v:
                return False
            zone_id = v.id
        return any(l.zone_id == zone_id for l in self.lenh)

    # ---- lệnh ----
    def mo_lenh(self, zone_id, sinh_tai, huong, loai, lot, gia_dat, sl, tp, R, nen):
        self._dem_lenh += 1
        l = Lenh(f"L-{self._dem_lenh:04d}", zone_id, sinh_tai, huong, loai, lot,
                 gia_dat, sl, tp, R, nen)
        self.lenh.append(l)
        return l

    def dang_song(self):
        """Lệnh sơ đồ MANAGE phải chạy qua, mỗi cái một lượt.

        Trả theo đúng thứ tự SINH RA để một lần chạy lại cho ra kết quả y hệt."""
        return [l for l in self.lenh if l.con_song]

    def so_lenh_cho(self):
        return sum(1 for l in self.lenh if l.trang_thai == CHO)

    def so_vi_the(self):
        return sum(1 for l in self.lenh if l.trang_thai == MO)

    def khop(self, l, gia, nen, j=None):
        """`j` = chỉ số NHỊP M1 lúc khớp. `nen` chỉ là chỉ số nến TRỤC (M5), mà trong
        một nến trục có tới 5 nhịp M1 — thiếu `j` thì không xếp nổi thứ tự giữa cú khớp
        và các lượt Manage rơi cùng nến đó. Không đụng tới logic nào, chỉ là bản ghi."""
        l.trang_thai = MO
        l.gia_khop = gia
        l.nen_khop = nen
        l.j_khop = j
        return l

    def dong(self, l, gia, nen, ly_do):
        l.trang_thai = DONG
        l.gia_dong = gia
        l.nen_dong = nen
        l.ly_do_dong = ly_do
        return l


