"""BỘ CHẠY — chỗ mọi thứ ráp lại: đồ thị + nến + chỉ báo + sổ lệnh → một lần backtest.

    nguon_nen  →  nến M1
    tinh_toan  →  chỉ báo (mảng), gộp khung
    khop_lenh  →  lệnh khớp lúc nào, giá nào
    core       →  đồ thị đã chuẩn hoá, thứ tự nhánh
    so_lenh    →  sổ lệnh + sổ vùng nén
    file này   →  vòng lặp, và CHỈ vòng lặp

BỐN LUẬT ĐÃ CHỐT (core.md §12.1, §12.4, §12.5)
----------------------------------------------
1. **Hai đồng hồ.** Bước từng nến M1 (thị trường). Sơ đồ chỉ chạy khi nến của NHỊP nó
   khép — Entry M5, Manage M1.

2. **Thứ tự trong một nhịp:** khớp lệnh (sàn) → cập nhật engine → MANAGE từng lệnh đang
   sống → ENTRY một lượt. Manage trước Entry, đúng `OnTick` của bản gốc; ngược lại thì
   lệnh vừa sinh bị quản lý ngay trong chính nến đẻ ra nó.

3. **Luật đi:** cổng trượt thì lùi về ngã rẽ gần nhất còn nhánh chưa thử — TRỪ KHI lượt
   này đã chạm thị trường (`vao_lenh`/`sua_lenh`), khi đó hết lượt ngay. Đã bắn lệnh ra
   thì không rút lại được, nên không được quay lui thử nhánh khác.

4. **Cổng LUÔN tính đủ mọi điều kiện**, không ngắt ở cái sai đầu tiên — nếu ngắt thì
   nhật ký vĩnh viễn không trả lời được "ba điều kiện kia lúc đó thế nào".

BIÊN DỊCH TRƯỚC — điều kiện SỐNG CÒN, không phải tối ưu sớm
------------------------------------------------------------
`bien_dich()` chạy MỘT LẦN trước vòng lặp: mọi tên toán hạng → chỉ số cột đã tính sẵn,
mọi tên tham số → `float`, `flow_map` → danh sách kề bằng chỉ số nguyên. Vòng chạy sau
đó không đụng một chuỗi nào.

Không có bước này thì 1–3 triệu phép đánh giá bằng dict + chuỗi mất hàng chục giây mỗi
lần bấm ▶, và cả kiến trúc "tính một lần, đọc mãi mãi" sụp. Lợi ích thứ hai cũng lớn
ngang: mọi lỗi "toán hạng chưa hỗ trợ", "tham số không có trong bảng" nổ ra Ở ĐÂY kèm
nhãn khối `[3A.1]`, chứ không nổ ở nến thứ 40.000.
"""
import math

import numpy as np

from . import core
from . import khop_lenh
from . import kho
from . import so_lenh as sl
from . import tinh_toan as tt

NAN = float("nan")


class LoiChay(Exception):
    """Lỗi nói được thành lời, kèm nhãn khối. Không phải traceback."""


# ---------------------------------------------------------------------------
# Cấu hình một lần chạy
# ---------------------------------------------------------------------------
class CaiDat:
    """Điều kiện chạy — đúng những ô trong Cài đặt Strategy Test."""

    def __init__(self, symbol="XAUUSD", tu=None, den=None, spread_diem=20.0,
                 point=0.01, contract_size=100.0, digits=2,
                 deposit=10_000.0, commission=0.0, don_bay=100):
        self.symbol = symbol
        self.tu, self.den = tu, den
        self.spread_diem = float(spread_diem)
        self.point = float(point)
        self.contract_size = float(contract_size)
        self.digits = int(digits)
        self.deposit = float(deposit)
        self.commission = float(commission)     # USD mỗi lot, tính ROUND-TURN
        self.don_bay = don_bay

    @property
    def spread_gia(self):
        """Spread quy ra ĐƠN VỊ GIÁ. `khop_lenh` cố ý không biết `point` là gì."""
        return self.spread_diem * self.point


# ---------------------------------------------------------------------------
# Ngữ cảnh đánh giá — thứ duy nhất toán hạng và Engine nhìn thấy
# ---------------------------------------------------------------------------
class Ctx:
    """Trạng thái tại MỘT thời điểm quyết định. Đọc-thôi với người dùng nó.

    Cố ý gom vào một chỗ: mọi toán hạng, mọi Engine chỉ được nhìn qua cái cửa này, nên
    thêm một nguồn dữ liệu là sửa đúng một chỗ."""

    __slots__ = ("ct", "so", "i", "j", "tab", "lenh", "co_lo_hong", "ts",
                 "zone_da_xet", "zone_thu")

    def __init__(self, ct, so, ts):
        self.ct, self.so, self.ts = ct, so, ts
        self.i = 0            # chỉ số trên trục quyết định (nến M5)
        self.j = 0            # chỉ số trên trục M1
        self.tab = core.TAB_ENTRY
        self.lenh = None      # lệnh đang được xét (chỉ Manage)
        self.co_lo_hong = False
        #: Cổng zone ĐÃ được xét ở nến trục này chưa. Luật lùi có thể quay lại một
        #: ngã rẽ, nhưng một cây nến chỉ được đếm vào zone đúng MỘT lần.
        self.zone_da_xet = False
        #: ZONE THỬ — bản zone SẼ THÀNH nếu nến này được nuốt. Chỉ khác `None` trong
        #: đúng lúc CỔNG ZONE đang được đánh giá; mọi khối khác đọc zone thật.
        self.zone_thu = None

    def zone_hop_le(self):
        """Zone hiện hành có đạt phần "hợp lệ" của cổng zone không.

        HÀM THUẦN, tính lại mỗi lần được hỏi — không cất trạng thái, nên máy trạng thái
        5 giá trị của bản gốc vẫn không quay lại (core.md §7.5).

        Ba câu trả lời, và ca giữa mới là ca dễ sai:
          chưa có zone            → NaN  (cổng trượt; trả SAI thì `KHÔNG hợp lệ` hoá
                                          ĐÚNG giữa lúc chẳng có zone nào)
          chưa khai `dk_hop_le`   → NaN  (hỏi một khái niệm chưa ai định nghĩa)
          có zone, có định nghĩa  → đúng/sai

        ⚠ Đọc zone THẬT, không đọc zone thử: "hợp lệ" nói về cây zone đã chốt, còn zone
        thử chỉ tồn tại trong đúng lúc cổng đếm đang cân nhắc có nuốt nến này không."""
        if not self.ct.dk_hop_le or self.so.zone_hien_hanh() is None:
            return NAN
        thu, self.zone_thu = self.zone_thu, None
        try:
            khop, _ = _xet_dieu_kien(self.ct.dk_hop_le, self)
        finally:
            self.zone_thu = thu
        return bool(khop)

    # -- giá --
    @property
    def bid(self):
        """Giá Bid ngay lúc này = close của nến M1 vừa đóng."""
        return float(self.ct.nen1["c"][self.j])

    @property
    def ask(self):
        return self.bid + self.ct.cd.spread_gia

    def gia_nen(self, cot, shift=0):
        """Một cột giá của nến TRỤC QUYẾT ĐỊNH, lùi `shift` nến."""
        k = self.i - int(shift)
        return float(self.ct.nen5[cot][k]) if k >= 0 else NAN

    def chi_bao(self, ten, tf=None, period=None, method=None, shift=1):
        """Giá trị một chỉ báo đã tính sẵn, tại thời điểm này."""
        return self.ct.doc_cot(
            {"ten": ten, "tf": tf, "period": period, "method": method}, self.i, shift)


# ---------------------------------------------------------------------------
# Chương trình đã biên dịch
# ---------------------------------------------------------------------------
class ChuongTrinh:
    """Sơ đồ + dữ liệu đã nhai xong, sẵn sàng cho vòng lặp."""

    def __init__(self, doc, nen1, cd):
        self.doc, self.nen1, self.cd = doc, nen1, cd
        self.ts = core.bang_tham_so(doc)
        self.engine = kho.engine_d02.Engine()
        self._cot = {}
        self.nhip = {}
        self._kiem_tham_so()
        self._dung_truc()
        self._dung_cot()
        self._dung_luong()

    # ---------------------------------------------------------------- tham số
    def _kiem_tham_so(self):
        thieu = [k for k in self.engine.THAM_SO_CAN if k not in self.ts]
        if thieu:
            raise LoiChay(
                f"Bảng tham số thiếu {', '.join(thieu)} — engine Compress cần chúng để "
                f"nuôi vùng nén. Mở Tham số chiến lược và thêm vào.")

    def so(self, v, o_dau=""):
        """Một ô "số hoặc tên tham số" → `float`.

        Luật xuyên suốt app: *ở đâu chờ một con số, một CHUỖI nghĩa là tên tham số.*
        Giải ở đây, một lần, để vòng chạy không bao giờ đụng chuỗi."""
        if isinstance(v, str):
            if v not in self.ts:
                raise LoiChay(f'{o_dau}tham số "{v}" không có trong bảng tham số.')
            return float(self.ts[v])
        try:
            return float(v)
        except (TypeError, ValueError):
            raise LoiChay(f"{o_dau}giá trị {v!r} không phải số.")

    # ------------------------------------------------------------------ trục
    def _dung_truc(self):
        """Trục quyết định (nhịp Entry) + bảng tra M1 → chỉ số trục.

        Cột chỉ báo cất trên trục Entry (~72k mục một năm) chứ không trên trục M1 (374k):
        chỉ báo chỉ đổi khi nến khung nó khép, nhân 5 lần bộ nhớ để chép lại cùng một
        con số là phí. Manage chạy nhịp M1 nên cần bảng tra — dựng một lần, 4 byte/nến."""
        # Luật "nhịp của một tab" nằm ở `core.nhip_cua` — bảng số liệu cũng phải biết
        # khung quyết định để chuẩn hoá ô khung trống, và hai bản chép tay thì trôi được.
        for tab in core.TABS:
            self.nhip[tab] = core.nhip_cua(self.doc, tab)
        self.tf5 = self.nhip[core.TAB_ENTRY]
        self.nen5 = tt.gop(self.nen1, self.tf5)
        if not len(self.nen5):
            raise LoiChay("Không đủ nến để dựng dù một cây nến trên khung quyết định.")

        dong5 = tt.moc_dong(self.nen5, self.tf5)
        dong1 = tt.moc_dong(self.nen1, "M1")
        # Với mỗi nến M1, nến trục nào đã ĐÓNG gần nhất. −1 = chưa có nến trục nào.
        self.m1_to_5 = np.searchsorted(dong5, dong1, side="right") - 1
        # NHỊP ENTRY = nến M1 ĐẦU TIÊN thuộc về một nến trục MỚI.
        #
        # ⚠ Trước đây là `np.isin(dong1, dong5)` — "nến M1 nào đóng ĐÚNG KHÍT mốc đóng
        # của một nến trục". Phép trùng khít ấy phụ thuộc DỮ LIỆU M1 CÓ ĐỦ PHÚT CUỐI hay
        # không: thiếu đúng cây phút đó thì cả nến trục KHÔNG ĐƯỢC CHẠY ENTRY lần nào —
        # cổng zone không được xét, zone không lớn cũng không chết.
        #
        # Đo trên 260.000 nến XAUUSD thật: 188 nến trục (0,36 %) không có nhịp nào. Phần
        # lớn vô hại vì nến sau mang cờ `lo_hong5` và giết zone đúng chỗ. Nhưng khi CHÍNH
        # nến không-nhịp là nến mang cờ lỗ hổng thì cờ bốc hơi cùng nến — zone sống XUYÊN
        # qua một quãng chợ đóng, trái hẳn luật đã ghi ở `_nuoi_zone`: "48 giờ chợ đóng
        # cửa không phải giá đứng yên".
        #
        # Luật mới không phụ thuộc phút cuối. Đo lại trên cùng bộ nến: GIỮ NGUYÊN toàn bộ
        # 51.938 nhịp cũ, thêm 184 nhịp bị bỏ sót, và mỗi nến trục có ĐÚNG MỘT nhịp.
        moi = np.zeros(len(dong1), dtype=bool)
        if len(dong1):
            moi[0] = self.m1_to_5[0] >= 0
            moi[1:] = (self.m1_to_5[1:] != self.m1_to_5[:-1]) & (self.m1_to_5[1:] >= 0)
        self.la_nhip5 = moi

        # Lỗ hổng trên TRỤC QUYẾT ĐỊNH: hai nến cách nhau quá 2 bước là chợ đã đóng.
        buoc = core.TF_PHUT[self.tf5] * 60
        d = np.diff(self.nen5["t"], prepend=self.nen5["t"][0])
        self.lo_hong5 = d > 2 * buoc

    # ------------------------------------------------------------------- cột
    def _dung_cot(self):
        """Tính TRƯỚC mọi chỉ báo sơ đồ dùng tới, mỗi (tên, tf, chu kỳ, kiểu) một lần.

        Sơ đồ mẫu hỏi `atr_bps(M5, 14)` ở HAI chỗ (cổng vào và cổng huỷ) — tính hai lần
        là phí đúng gấp đôi, mà kết quả bắt buộc phải giống nhau."""
        for tab in core.TABS:
            for st in (self.doc.get(tab) or {}).get("steps") or []:
                # `dk_hop_le` (phần "hợp lệ" của cổng zone) cũng đọc toán hạng, nên
                # cũng phải xin cột — quên nó thì `Zone hợp lệ` nổ "chưa có cột" giữa
                # lúc chạy, và nổ ở một chỗ chẳng liên quan gì tới cổng zone.
                for c in (st.get("conditions") or []) + (st.get("dk_hop_le") or []):
                    for o in (c.get("trai"), c.get("phai")):
                        if isinstance(o, dict) and o.get("ten"):
                            self._xin_cot(o, tab, st)
                    # Đơn vị `bps` / `%` chia cho GIÁ ĐÓNG cùng khung — cột đó phải có
                    # sẵn dù sơ đồ không hỏi `close` ở đâu cả.
                    tr = c.get("trai")
                    dv = (c.get("phai") or {}).get("tinh")                         if isinstance(c.get("phai"), dict) else None
                    if isinstance(tr, dict) and dv in ("bps", "pt"):
                        self._xin_cot({"ten": "close", "tf": tr.get("tf")}, tab, st)
        # Engine cần `atr` trên khung quyết định dù sơ đồ có hỏi hay không: zone cộng
        # dồn nó để tính `zone_atr_tb`, và đơn vị `× ATR` chia cho nó.
        self._xin_cot({"ten": "atr", "tf": self.tf5,
                       "period": self.ts["chu_ky_atr"]}, None, None)
        # ĐỊNH NGHĨA "hợp lệ" — lấy từ cổng zone của ENTRY, đúng một cái (soát tĩnh đã
        # bắt ca nhiều hơn một). Giữ ở đây chứ không đi tìm lại mỗi lần `zone_hop_le`
        # được hỏi: nó bị hỏi trong vòng lặp nến, mà đi lại danh sách khối mỗi lần là
        # phí đúng cái `bien_dich` sinh ra để tránh.
        self.dk_hop_le = next(
            (st.get("dk_hop_le") for st in
             (self.doc.get(core.TAB_ENTRY) or {}).get("steps") or []
             if st.get("cong_zone") and st.get("dk_hop_le")), None)

    #: Chu kỳ mặc định khi ô để trống. Trùng mặc định của hộp thoại hành động.
    CHU_KY_MAC_DINH = 14

    def khoa(self, o):
        """Khoá cột của một toán hạng. DỰNG Ở ĐÚNG MỘT CHỖ.

        Trước đây `_xin_cot` áp mặc định `period=14` còn `doc_cot` truyền thẳng `None`,
        nên cùng một chỉ báo ra hai khoá khác nhau: tính lúc biên dịch xong xuôi rồi tới
        lúc chạy lại báo "chưa được tính trước". Lỗi chỉ lộ ra với điều kiện KHÔNG ghi
        `period` — mà sơ đồ mẫu thì ô nào cũng ghi, nên nó trốn kỹ."""
        # Toán hạng GIÁ không có chu kỳ. Để mặc định 14 chui vào khoá thì `close(M15)`
        # thành `('close','M15',14.0,None)` — vô nghĩa, và đụng ngay nếu sau này có một
        # toán hạng giá thật sự nhận chu kỳ.
        if o["ten"] in self.COT_GIA:
            return (o["ten"], o.get("tf") or self.tf5, None, None)
        ck = o.get("period", self.CHU_KY_MAC_DINH)
        if ck is None:
            ck = self.CHU_KY_MAC_DINH
        return (o["ten"], o.get("tf") or self.tf5, self.so(ck), o.get("method") or None)

    #: Toán hạng giá → cột nào của mảng nến.
    COT_GIA = {"close": "c", "open": "o", "high": "h", "low": "l"}

    def _xin_cot(self, o, tab, st):
        ten = o["ten"]
        if ten in self.COT_GIA:
            return self._xin_cot_gia(o, st)
        if ten not in tt.BANG:
            return                              # toán hạng phi-chỉ-báo, tra lúc chạy
        nhan = f"[{core.step_title(st)}] " if st else ""
        try:
            k = self.khoa(o)
            ck = k[2]
            if k in self._cot:
                return
            nen = tt.gop(self.nen1, k[1])
            gt = tt.tinh(ten, nen, ck, method=k[3] or "SMA")
            # Đưa về TRỤC QUYẾT ĐỊNH: giá trị của nến khung lớn ĐÃ ĐÓNG gần nhất.
            # Đây là chỗ lỗi nhìn trước tương lai sẽ nằm nếu làm ẩu.
            if k[1] != self.tf5:
                gt = tt.theo_truc(gt, tt.moc_dong(nen, k[1]),
                                  tt.moc_dong(self.nen5, self.tf5))
            self._cot[k] = gt
        except (ValueError, KeyError) as e:
            raise LoiChay(f"{nhan}{e}")

    def _xin_cot_gia(self, o, st):
        """Cột GIÁ của một khung thời gian, đưa về trục quyết định.

        ⚠ LỖI ĐÃ SỬA: trước đây `close(M15, nến[1])` đọc thẳng `nen5` — tức nến M5 — nên
        cổng xu hướng so **Close M5 với MA M15**, trong khi D_02 so Close[1] với MA[1]
        CÙNG khung Trend (`FilterEngine.mqh:324-328`). Sai im lặng: không báo lỗi, chỉ ra
        một chuỗi lệnh khác. Giá phải đi qua đúng đường của chỉ báo — gộp lên khung của
        nó rồi `theo_truc` về trục quyết định."""
        k = self.khoa(o)
        if k in self._cot:
            return
        nen = tt.gop(self.nen1, k[1])
        gt = tt._f(nen[self.COT_GIA[o["ten"]]])
        if k[1] != self.tf5:
            gt = tt.theo_truc(gt, tt.moc_dong(nen, k[1]),
                              tt.moc_dong(self.nen5, self.tf5))
        self._cot[k] = gt

    def doc_cot(self, o, i, shift=None):
        k = self.khoa(o)
        a = self._cot.get(k)
        if a is None:
            raise LoiChay(f"Chỉ báo {o['ten']} chưa được tính trước — lỗi biên dịch.")
        # `shift` ĐẾM NGƯỢC TỪ NẾN ĐÃ ĐÓNG. Mọi cột ở đây vốn đã là "giá trị của nến đã
        # đóng gần nhất", nên `nến[1]` (quy ước MT5: nến vừa đóng) chính là lệch 0.
        # Mặc định 1 để công thức không ghi `shift` vẫn ra đúng nến đã đóng.
        if shift is None:
            shift = o.get("shift")
        i -= max(0, int(shift if shift is not None else 1) - 1)
        return float(a[i]) if 0 <= i < len(a) else NAN

    # ----------------------------------------------------------------- luồng
    def _dung_luong(self):
        """`flow_map` một lần cho mỗi tab: điểm vào + danh sách kề đã sắp ưu tiên."""
        self.luong = {}
        for tab in core.TABS:
            g = self.doc.get(tab) or {}
            steps, edges = g.get("steps") or [], g.get("edges") or []
            theo_id, ke = core.flow_map(steps, edges)
            self.luong[tab] = {
                "theo_id": theo_id, "ke": ke,
                "vao": core.flow_entry(steps, edges),
            }
        # Sơ đồ Entry có cổng zone không. Không có thì zone không tồn tại — và bước 5
        # của `mot_nhip` KHÔNG được đi giết một thứ chẳng ai định nghĩa.
        self.co_cong_zone = any(
            (st.get("action") or st).get("cong_zone")
            for st in (self.doc.get(core.TAB_ENTRY) or {}).get("steps") or []
            if isinstance(st, dict))


# ---------------------------------------------------------------------------
# Đánh giá toán hạng
# ---------------------------------------------------------------------------
def _gia_thoat(l, bid, cd):
    """Giá ƯỚC nếu đóng lệnh này ngay bây giờ: Mua thoát ở Bid, Bán thoát ở **Ask**.

    Đo lãi nổi của lệnh BÁN bằng Bid là báo lãi cao hơn thật đúng một spread — với XAUUSD
    spread 37 điểm thì đủ để một cổng "lãi ≥ 1R" khớp sớm hơn một nhịp, và bảng số liệu
    hiện một con số mà đóng lệnh ra không được.

    `Lenh.lai_R` cố ý KHÔNG biết spread là gì (`so_lenh` là mô hình thuần), nên phép quy
    đổi thuộc về chỗ gọi. Gom vào một hàm để ba chỗ gọi — toán hạng, bảng số liệu, hàng
    lệnh sống — không thể nói ba con số khác nhau."""
    return bid if l.huong == sl.MUA else bid + cd.spread_gia


def _lay_toan_hang(o, ctx):
    """Một toán hạng → một con số (hoặc đúng/sai). Đây là cây cầu DUY NHẤT giữa sơ đồ và
    dữ liệu.

    Không có nguồn → `NaN`, và NaN làm mọi phép so trả False, tức cổng TRƯỢT. Trả 0 thì
    cổng KHỚP và chiến lược vào lệnh giữa lúc chưa biết gì."""
    ten = o.get("ten")
    ct = ctx.ct

    if ten in tt.BANG:
        return ct.doc_cot(o, ctx.i, o.get("shift", 0))
    if ten in kho.engine_d02.ENGINE_TRA_LOI:
        return ct.engine.doc(ten, ctx)

    # ⚠ LỖI ĐÃ SỬA (lần hai — lần đầu vá hụt). Trước đây chỗ này gọi `ctx.gia_nen`, mà
    # `gia_nen` đọc THẲNG `ct.nen5` nên bỏ qua sạch khoá `tf`: `close(M15, nến[1])` trả
    # về giá M5. Đợt vá trước đã dựng đúng cột theo khung (`_xin_cot_gia`) và đúng khoá
    # (`khoa`) — nhưng QUÊN sửa chỗ đọc này, nên cột dựng ra không ai dùng. Đo lại trên
    # một tháng thật: 66,5 % số nến trả sai số, lệch tối đa 11,37.
    #
    # Gọi Y HỆT đường chỉ báo ở trên, không phải chỉ "cũng dùng doc_cot": `gia_nen` hiểu
    # `shift` là *lùi shift nến*, còn `doc_cot` hiểu `nến[1]` là *lệch 0* (quy ước MT5).
    # Hai vế của một cổng đi hai đường thì lệch nhau thêm một nến nữa.
    if ten in ct.COT_GIA:
        return ct.doc_cot(o, ctx.i, o.get("shift", 0))
    if ten == "so_vi_the":
        return float(ctx.so.so_vi_the())
    if ten == "so_lenh_cho":
        return float(ctx.so.so_lenh_cho())
    l = ctx.lenh
    if l is None:
        return NAN                              # "lệnh này" ở Entry — soát tĩnh đã chặn
    if ten == "lenh_da_khop":
        return bool(l.da_khop)
    if ten == "lenh_sl_hoa_von":
        return bool(l.sl_o_hoa_von)
    if ten == "lenh_lai_R":
        return float(l.lai_R(_gia_thoat(l, ctx.bid, ct.cd)))
    if ten == "lenh_thuoc_zone":
        # `zone_hien_hanh()` CHỈ trả zone còn SỐNG, nên một phép so id gộp trọn ba ca:
        # zone ấy đã chết mà chưa có zone mới (None) · đã có zone khác · vẫn là nó.
        #
        # ⚠ So ID chứ không so đối tượng: zone là thứ mutate liên tục, mà `Lenh.zone_id`
        # thì chốt cứng lúc đặt. Id là chỗ duy nhất hai bên gặp nhau mà không ai đổi.
        v = ctx.so.zone_hien_hanh()
        return bool(v is not None and l.zone_id == v.id)
    raise LoiChay(f'Toán hạng "{ten}" chưa được cài trong bộ chạy.')


def _so_sanh(trai, phep, phai):
    """Một phép so. NaN ở bất kỳ vế nào → False (cổng trượt), không nổ."""
    # ĐÚNG/SAI là một phép so, không phải một ô tick riêng — nhờ vậy mọi điều kiện
    # có cùng hình dạng và `_xet_cong` không còn nhánh ngoại lệ nào.
    # ⚠ NaN PHẢI XÉT TRƯỚC, và đây là chỗ lời hứa ngay trên đầu hàm từng bị phá.
    #
    # `bool(float("nan"))` trong Python là **True**. Hai nhánh đúng/sai dưới đây trước
    # kia chạy TRƯỚC phép kiểm NaN, nên một toán hạng "chưa có số" lại đọc thành ĐÚNG —
    # ngược hẳn luật "không có nguồn thì điều kiện TRƯỢT" (core.md §12.13).
    #
    # Đo được trên một năm: `Zone hiện hành hợp lệ` trả NaN **6.295 lần**, và CẢ 6.295
    # lần đều là lúc KHÔNG có zone nào. Cổng Manage `... và Zone hiện hành hợp lệ là
    # ĐÚNG` vì thế khớp giữa lúc chẳng có zone mới nào, và huỷ sạch lệnh chờ — đúng thứ
    # vế đó sinh ra để ngăn.
    #
    # Cả `la_dung` lẫn `la_sai` đều trả False: "chưa có số" thì KHÔNG trả lời được,
    # không phải trả lời ngược lại.
    if trai != trai:
        return False
    if phep == "la_dung":
        return bool(trai)
    if phep == "la_sai":
        return not bool(trai)
    if isinstance(trai, bool):
        return trai
    if trai != trai or (isinstance(phai, float) and phai != phai):
        return False
    if phep == "<":
        return trai < phai
    if phep == "<=":
        return trai <= phai
    if phep == ">":
        return trai > phai
    if phep == ">=":
        return trai >= phai
    if phep == "==":
        return trai == phai
    if phep == "!=":
        return trai != phai
    raise LoiChay(f'Phép so "{phep}" chưa được cài trong bộ chạy.')


def _quy_doi(x, don_vi, o, ctx):
    """Đổi giá trị vế trái sang ĐƠN VỊ được chọn. Đây là chỗ `atr_bps` sống tiếp.

    Công thức phải TRÙNG KHÍT bản cũ, nếu không mọi sơ đồ đã lưu đổi hành vi âm thầm:

      bps  =  x / close × 10⁴   — `close` CÙNG khung, CÙNG shift với vế trái, đúng
                                  `iClose(signal_tf, 1)` của D_02 (FilterEngine.mqh:202)
      × ATR       =  x / atr(chu_ky_atr)   — ATR nến vừa đóng, giống `rong_atr` cũ
                                             (`so_lenh.Zone.rong_atr` chia `atr_hien_tai`)
      × ATR zone  =  x / zone_atr_tb       — ATR trung bình cả zone, thước của RỦI RO

    Không có mẫu số → NaN, và NaN làm cổng TRƯỢT. Trả 0 thì cổng KHỚP giữa lúc chưa
    biết gì — đúng loại lỗi im lặng cả kiến trúc này dựng lên để tránh."""
    if don_vi in (None, "", "gia") or isinstance(x, bool) or x != x:
        return x
    if don_vi == "bps":
        c = ctx.ct.doc_cot({"ten": "close", "tf": o.get("tf")}, ctx.i,
                           o.get("shift", 0))
        if c != c or not c:
            return NAN
        return x / c * 10000.0
    if don_vi == "atr":
        a = ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"])
        return x / a if a == a and a else NAN
    if don_vi == "atr_zone":
        v = ctx.so.zone_hien_hanh()
        return x / v.atr_tb if v and v.atr_tb else NAN
    raise LoiChay(f'Đơn vị so sánh "{don_vi}" chưa được cài trong bộ chạy.')


def quy_doi_cot(kq, o, cot, don_vi):
    """Bản-THEO-CỘT của `_quy_doi` ngay trên. `None` = không có mẫu số.

    ⚠ HAI HÀM NÀY PHẢI SỬA CÙNG LÚC. `_quy_doi` tính MỘT nến cho CỔNG (và cho vết nhật
    ký); hàm này tính CẢ LÔ cho BẢNG SỐ LIỆU. Công thức lệch nhau là bảng hiện 5.35 còn
    nhật ký hiện một số khác đúng lúc đang debug cổng — core.md §12.9. Đặt hai hàm dính
    nhau là cách rẻ nhất để lần sau ai sửa một cái sẽ thấy cái kia.

    Khác duy nhất, và là cố ý: mẫu số `atr_zone` đọc từ CỘT đã ghi lúc chạy, KHÔNG hỏi
    lại `so.zone_hien_hanh()`. Đối tượng đó mutate liên tục nên ở con trỏ nào cũng trả
    trạng thái CUỐI backtest — đúng lỗi §12.9d.
    ⚠ Đổi lại, cột `zone_atr_tb` được CHỤP ở bước 5 của `mot_nhip`, tức SAU khi sơ đồ
    chạy xong nến đó, còn `_quy_doi` đọc zone GIỮA lúc sơ đồ chạy. Trên phần lớn nến là
    một; nến nào zone bị chốt trong chính lượt ấy thì hai bên lệch. Vẫn chọn cột, vì lựa
    chọn kia sai ở MỌI nến.

    Thiếu cột mẫu số → `None` (bảng để trống CẢ HÀNG). Mẫu số 0/NaN tại một nến → NaN
    tại đúng nến đó. Thà bỏ trống còn hơn bịa một con số (§12.9b)."""
    if don_vi in (None, "", "gia") or cot is None:
        return cot
    ct = kq._ct
    if don_vi == "bps":
        # `close` CÙNG khung với VẾ TRÁI — y hệt `_quy_doi`, không phải khung quyết định.
        mau, he = ct._cot.get(ct.khoa({"ten": "close", "tf": o.get("tf")})), 10000.0
    elif don_vi == "atr":
        # ATR khung QUYẾT ĐỊNH, chu kỳ `chu_ky_atr` — khoá này khớp khít
        # `ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"])` mà `_quy_doi` gọi.
        mau, he = ct._cot.get(ct.khoa({"ten": "atr", "tf": ct.tf5,
                                       "period": ct.ts["chu_ky_atr"]})), 1.0
    elif don_vi == "atr_zone":
        mau, he = kq.cot_zone.get("zone_atr_tb"), 1.0
    else:
        return cot          # đơn vị lạ từ file nhập ngoài: trả THÔ, đừng nổ giữa lô
    if mau is None or len(mau) != len(cot):
        return None
    # ⚠ Phép MẢNG, không vòng lặp Python: `ApiLive` không ghi đè `_cot_toan_hang` nên hàm
    # này chạy trên MỖI nhịp làm mới của Live, × số hàng × cả lô.
    with np.errstate(divide="ignore", invalid="ignore"):
        ra = np.asarray(cot, dtype=float) / np.asarray(mau, dtype=float) * he
    ra[~np.isfinite(ra)] = NAN
    return ra


def _xet_cong(st, ctx):
    """Một cổng: trả `(khớp?, [vết từng điều kiện])`."""
    return _xet_dieu_kien(st.get("conditions"), ctx)


def _xet_dieu_kien(ds, ctx):
    """Một DANH SÁCH điều kiện: trả `(khớp?, [vết từng điều kiện])`.

    Tách khỏi `_xet_cong` để phần "hợp lệ" của cổng zone (`dk_hop_le`) đi qua ĐÚNG phép
    so này — chép ra bản thứ hai là sớm muộn một bản quên quy đổi đơn vị, quên NaN, hoặc
    quên luật "đại lượng hay lượng suy từ khoá `ten`".

    LUÔN tính đủ mọi điều kiện, không ngắt ở cái sai đầu tiên — vết đó là thứ duy nhất
    trả lời được "cổng trượt vì con số nào" khi nhật ký được đọc lại."""
    vet, khop = [], True
    for c in ds or []:
        phep = c.get("phep") or "<"
        p_ = c.get("phai")
        # KIỂU SUY RA, không khai: có khoá `ten` là một đại lượng khác, còn lại là
        # LƯỢNG `{value, tinh}` — `value` là số hoặc TÊN THAM SỐ, `ct.so()` lo cả hai.
        la_dai_luong = isinstance(p_, dict) and p_.get("ten")
        # ĐƠN VỊ nằm ở vế PHẢI nhưng quy đổi vế TRÁI — vì nó trả lời "con số bạn gõ
        # mang nghĩa gì", mà con số đó đứng bên phải.
        dv = None if la_dai_luong else (p_ or {}).get("tinh")
        t = _quy_doi(_lay_toan_hang(c["trai"], ctx), dv, c["trai"], ctx)
        if la_dai_luong:
            p = _lay_toan_hang(p_, ctx)
        elif phep in ("la_dung", "la_sai"):
            p = NAN                          # không có vế phải
        else:
            try:
                p = ctx.ct.so((p_ or {}).get("value", 0))
            except LoiChay:
                p = NAN
        dat = _so_sanh(t, phep, p)
        vet.append({"trai": _js(t), "phai": _js(p), "dat": bool(dat)})
        khop = khop and dat
    return khop, vet


def _js(x):
    """Số cho nhật ký: NaN không qua nổi JSON, và `None` mới đúng nghĩa "chưa có"."""
    if isinstance(x, bool):
        return x
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


# ---------------------------------------------------------------------------
# Khoảng cách giá — sáu cách tính
# ---------------------------------------------------------------------------
def _khoang(k, ctx, neo=None, R=None):
    """`{tinh, value}` → một khoảng cách tính bằng ĐƠN VỊ GIÁ.

    ⚠ `atr` và `atr_zone` là HAI THỨ KHÁC NHAU, và đây là chỗ duy nhất giữ
    cho chúng khác nhau (core.md §6.3):
      * `atr`      = ATR của nến VỪA ĐÓNG   → đo đệm vào lệnh (`comp.atr_current`)
      * `atr_zone` = ATR TRUNG BÌNH cả vùng → ĐỊNH NGHĨA 1R    (`comp.atr_avg`)
    Gộp làm một là mất đúng cái làm cho 1R nhất quán, mà validator KHÔNG bắt được."""
    if not k:
        return NAN
    v = ctx.ct.so(k.get("value", 0))
    tinh = k.get("tinh")
    if tinh == "atr":
        return v * ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"])
    if tinh == "atr_zone":
        vung = ctx.so.zone_hien_hanh()
        return v * vung.atr_tb if vung else NAN
    if tinh == "R":
        return v * (R if R is not None else NAN)
    if tinh == "gia":
        return v
    # ⚠ `bps` từng được BÀY RA cho SL/TP/đệm (`DON_VI_CHO`) mà KHÔNG cài ở đây: chọn nó
    # là ném `LoiChay` giữa lúc backtest. Nó chính là `pt` cũ đổi mẫu số — `pt` đã bỏ vì
    # trùng ý nghĩa với `bps` (chênh đúng 100 lần), giữ hai tên cho một phép là rác.
    if tinh == "bps":
        return v / 10000.0 * (neo if neo is not None else NAN)
    if tinh == "bien_zone":
        vung = ctx.so.zone_hien_hanh()
        if vung is None or neo is None:
            return NAN
        return abs(neo - (vung.day if neo >= vung.dinh else vung.dinh))
    raise LoiChay(f'Cách tính "{tinh}" chưa được cài trong bộ chạy.')


# ---------------------------------------------------------------------------
# Hai hành động chạm thị trường
# ---------------------------------------------------------------------------
def _vao_lenh(st, ctx):
    """Đặt một lệnh. Trả bản ghi `viec` cho nhật ký, hoặc None nếu không đặt được.

    MỐC NEO giờ là một TRƯỜNG của khối, không còn suy ra từ hướng lệnh.

    ⚠ Trước đây chỗ này viết cứng "lệnh chờ neo mép zone thuận chiều, lệnh thị trường
    neo giá hiện tại". Trên màn hình vì thế chỉ hiện mỗi ô ĐỆM — và cái đệm, vốn chỉ là
    tấm khiên mỏng lọc một nhịp phá giả, hoá thành nhân vật chính; còn thứ QUYẾT ĐỊNH
    lệnh nằm ở đâu thì tàng hình. Giờ mốc hiện ra và bắt buộc, đệm là tuỳ chọn: bỏ
    trống thì lệnh nằm đúng mép.

    `entry = HH của zone + đệm` của bản gốc giờ đọc thẳng được trên khối."""
    ct, so_ = ctx.ct, ctx.so
    huong = st.get("huong", sl.MUA)
    loai = st.get("loai", "stop")
    lot = ct.so(st.get("lot", 0.01))
    vung = so_.zone_hien_hanh()

    moc = (st.get("entry") or {}).get("moc") or (
        "gia_hien_tai" if loai == "market" else
        ("zone_HH" if huong == sl.MUA else "zone_LL"))
    if moc == "zone_HH":
        if vung is None:
            return None                 # chưa có zone → chưa có mốc để neo
        mep = vung.dinh
    elif moc == "zone_LL":
        if vung is None:
            return None
        mep = vung.day
    else:
        mep = ctx.ask if huong == sl.MUA else ctx.bid
    # ĐỆM là tuỳ chọn. Không có thì lệnh nằm đúng mốc — hợp lệ, chỉ dễ dính một nhịp
    # phá giả hơn. Đó là lựa chọn của người vẽ, không phải lỗi.
    dem = _khoang(st.get("dem"), ctx, neo=mep) if st.get("dem") else 0.0
    if dem != dem:
        return None
    gia_dat = mep + dem if huong == sl.MUA else mep - dem

    R = _khoang(st.get("sl"), ctx, neo=gia_dat)
    if R != R or R <= 0:
        return None                     # chưa có vùng nén → chưa định nghĩa được 1R
    slg = gia_dat - R if huong == sl.MUA else gia_dat + R
    tpg = None
    if st.get("tp"):
        d = _khoang(st["tp"], ctx, neo=gia_dat, R=R)
        if d == d:
            tpg = gia_dat + d if huong == sl.MUA else gia_dat - d

    l = so_.mo_lenh(vung.id if vung else None, ctx.i, huong, loai, lot,
                    gia_dat, slg, tpg, R, ctx.i)
    # Lệnh THỊ TRƯỜNG khớp NGAY, không phải chờ giá quay lại chạm `gia_dat`. Thiếu chỗ
    # này thì nó nằm treo như một lệnh chờ và có thể không bao giờ khớp — sai hẳn bản
    # chất, dù sơ đồ mẫu D_02 không dùng tới nên bài kiểm cũ không thấy.
    if loai == "market":
        so_.khop(l, gia_dat, ctx.i, ctx.j)
    return {"loai": "lenh_dat", "lenh_id": l.id, "huong": huong,
            "khop_ngay": loai == "market",
            "gia_dat": _js(gia_dat), "sl": _js(slg), "tp": _js(tpg), "R": _js(R)}


def _sua_lenh(st, ctx):
    """Sửa lệnh đang xét. Bảy chế độ. Trả bản ghi `viec`, hoặc None nếu không đổi gì."""
    l, so_ = ctx.lenh, ctx.so
    if l is None or not l.con_song:
        return None
    cd = st.get("che_do")
    truoc = {"sl": l.sl, "tp": l.tp}

    if cd == "hoa_von":
        if l.gia_khop is None:
            return None
        l.sl = l.gia_khop
    elif cd in ("doi_sl", "doi_tp"):
        d = _khoang(st.get("khoang"), ctx, neo=ctx.bid, R=l.R)
        if d != d:
            return None
        moi = ctx.bid - d if (l.huong == sl.MUA) == (cd == "doi_sl") else ctx.bid + d
        setattr(l, "sl" if cd == "doi_sl" else "tp", moi)
    elif cd == "ket_thuc":
        # MỘT chế độ thay cho `dong_han` + `huy_cho`. Manage chạy một lượt cho MỖI
        # lệnh, nên "lệnh này" là duy nhất và ta TỰ BIẾT nó đã khớp hay chưa — bắt
        # người dùng chọn giữa hai cái là bắt họ khai một thứ máy đã biết, mà chọn
        # nhầm thì hành động im lặng không làm gì.
        if not l.da_khop:
            so_.dong(l, None, ctx.i, "huy")
            return {"loai": "lenh_huy", "lenh_id": l.id}
        so_.dong(l, ctx.bid if l.huong == sl.MUA else ctx.ask, ctx.i, "dong_tay")
        # Ghi tiền NGAY, y như đường sàn đóng lệnh — xem chú thích ở `chay()`.
        ctx.ct.ghi_tien(l)
        return {"loai": "lenh_dong", "lenh_id": l.id, "ly_do": "dong_tay",
                "gia": _js(l.gia_dong)}
    else:
        raise LoiChay(f'Chế độ sửa lệnh "{cd}" chưa được cài trong bộ chạy.')

    if truoc["sl"] == l.sl and truoc["tp"] == l.tp:
        return None
    return {"loai": "lenh_sua", "lenh_id": l.id, "che_do": cd,
            "sl": _js(l.sl), "tp": _js(l.tp)}


# ---------------------------------------------------------------------------
# Đi trên đồ thị
# ---------------------------------------------------------------------------
def _dat_zone_thu(ctx):
    """Bày ra ZONE THỬ cho cổng zone nhìn — rồi `_nuoi_zone` mới quyết giữ hay bỏ.

    ⭐ VÌ SAO CỔNG PHẢI NHÌN ZONE ĐÃ CỘNG NẾN NÀY (core.md §12.6c).

    Cổng zone trả lời đúng một câu: *"cây nến này có được nuốt vào zone không?"* Nên thứ
    nó phải phán xét là **hậu quả nó sắp gây ra**, không phải trạng thái trước đó. Nhờ
    vậy `Zone — bề rộng ≤ 4 × ATR` thành một HẠN MỨC: kiểm trước khi tiêu, zone không
    bao giờ vượt. Nhìn zone trước khi nuốt thì cây nến làm vỡ hạn mức đã nằm trong zone
    rồi, zone chết muộn một nhịp và chết với hình dạng đã sai.

    Và ca NẾN ĐẦU TIÊN hết là ca đặc biệt: zone thử luôn có ít nhất một nến, nên
    `bề rộng` = high − low của chính nó. Không NaN, nên không có chuyện điều kiện trượt
    làm zone không bao giờ hình thành được.

    ⚠ Dựng đúng thứ `_nuoi_zone` SẼ dựng ngay sau đó, kể cả nhánh lỗ hổng dữ liệu — hai
    bên lệch nhau là cổng phán xét một zone khác với zone thật sự được tạo ra."""
    if ctx.zone_da_xet:
        # Nến này đã xét & nuốt xong (luật lùi quay lại) — zone thật CHÍNH LÀ bản thử.
        return
    v = None if ctx.co_lo_hong else ctx.so.zone_hien_hanh()
    cao, thap = ctx.gia_nen("h"), ctx.gia_nen("l")
    atr = ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"])
    if v is not None:
        ctx.zone_thu = v.thu_them(cao, thap, atr)
    else:
        # Zone MỚI. Id riêng, không đụng bộ đếm thật — và nhờ nó mà
        # `zone_da_sinh_lenh` tra ra ĐÚNG "chưa có lệnh nào", thay vì đọc nhầm zone cũ.
        z = sl.Zone("(thử)", ctx.i)
        z.them_nen(cao, thap, atr)
        ctx.zone_thu = z


def _nuoi_zone(ctx, khop):
    """CỔNG ZONE vừa được xét — lớn lên hay chết.

    ⚠ ĐÂY LÀ CHỖ ZONE ĐƯỢC ĐỊNH NGHĨA, và nó nằm trong sơ đồ chứ không nằm trong một
    cỗ máy ẩn nữa.

    Trước đây `engine.moi_nen()` chạy mỗi nến, TRƯỚC mọi sơ đồ, và viết cứng điều kiện
    đếm là "atr_bps dưới ngưỡng". Nhìn sơ đồ không thấy zone ở đâu, và chiến lược thứ
    hai muốn đếm theo điều kiện khác thì phải sửa engine.

    Giờ: cổng nào mang cờ `cong_zone` thì CHÍNH NÓ là điều kiện đếm. Cổng qua → zone
    lớn thêm một nến. Cổng trượt → zone chết ngay. Điều kiện đếm thành tham số mà không
    cần thêm một ô cấu hình nào — nó là cái cổng bạn vẽ ra.

    ĐÚNG MỘT LẦN mỗi nến trục: luật lùi có thể quay lại một ngã rẽ, nhưng một cây nến
    chỉ được đếm một lần.
    """
    if ctx.zone_da_xet:
        return
    ctx.zone_da_xet = True
    so = ctx.so
    if not khop:
        so.dong_zone()
        return
    # Khoảng trống dữ liệu > 2 bước nến thì zone CHẾT dù cổng vẫn qua: "nén" là giá
    # đứng yên trong một quãng LIỀN MẠCH, 48 giờ chợ đóng cửa không phải giá đứng yên.
    if ctx.co_lo_hong:
        so.dong_zone()
    v = so.zone_hien_hanh() or so.mo_zone(ctx.i)
    v.them_nen(ctx.gia_nen("h"), ctx.gia_nen("l"),
               ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"]))


def _chay_so_do(tab, ctx):
    """Một LƯỢT chạy của một sơ đồ. Trả bản ghi nhật ký.

    LUẬT LÙI (core.md §12.5a): cổng trượt thì lùi về ngã rẽ gần nhất còn nhánh chưa
    thử — TRỪ KHI lượt này đã chạm thị trường, khi đó hết lượt ngay. Đã bắn lệnh ra thì
    không rút lại được, nên quay lui thử nhánh khác là đẻ ra lệnh thứ hai.

    ⭐ NGÃ RẼ VÀ (core.md §5.1): ngã rẽ mà MỌI đầu nhánh đều là hành động thì không có
    gì để chọn — bộ chạy làm HẾT các nhánh. Luật do `core.la_nga_re_va` giữ, dùng chung
    với soát tĩnh.

    ⚠ RANH GIỚI PHẢI SẮC, lẫn là hỏng ngầm:

        nhánh HOẶC  →  đi tiếp = THỬ PHƯƠNG ÁN KHÁC. Đã chạm thị trường thì CẤM (§12.5a)
        nhánh VÀ    →  đi tiếp = LÀM NỐT VIỆC ĐÃ ĐỊNH. Không phải lùi, nên không cấm

    Vì thế `cham_thi_truong` được hỏi ở MỨC ĐANG QUAY VỀ, không hỏi một lần cho cả lượt:
    cùng một cú "hết nhánh ở đây" mang hai nghĩa tuỳ mức cha là VÀ hay HOẶC."""
    ct = ctx.ct
    L = ct.luong[tab]
    theo_id, ke = L["theo_id"], L["ke"]
    vao = L["vao"]
    if not vao:
        return None

    def _la_va(ds):
        return core.la_nga_re_va([theo_id[s] for s in ds if s in theo_id])

    # ⚠ `duong` là ĐÃ ĐI QUA THEO THỨ TỰ, không phải tổ tiên của khối đang đứng.
    #
    # Trước đây nó bị `pop` mỗi lần lùi, tức luôn song song với `ngan`. Với ngã rẽ VÀ thì
    # cách đó nói dối: đi qua cả `[4A]` lẫn `[4B]` mà log chỉ còn `[4B]`, nhánh kia biến
    # mất dù nó vừa đặt một lệnh thật. Chỉ append thì đúng chữ §12.8 vẫn viết ("đường đã
    # đi, THEO THỨ TỰ") và đúng cả ca cũ: một cổng ĐÃ KHỚP rồi mới cụt phía dưới thì nó
    # vẫn nằm trong đường — vì lượt đó thật sự đã đi tới đó.
    duong = [vao]
    ngan = [list(ke.get(vao, []))]
    va = [_la_va(ngan[0])]
    cham_thi_truong = False
    # Ghi MỌI cổng đã thử, không chỉ cổng cuối. Ở một ngã rẽ, lượt trượt 1A rồi trượt
    # tiếp 1B — chỉ ghi 1B thì nhật ký trả lời được "1B trượt vì số nào" nhưng KHÔNG
    # trả lời được "thế 1A thì sao", mà đó thường mới là câu cần hỏi.
    viec, cong = [], []
    ket = "het_luot"

    for _ in range(core.MAX_PROCESS_STEPS):
        di = None
        while ngan[-1]:
            s = ngan[-1].pop(0)
            st = theo_id[s]
            if core.is_branch_gate(st):
                # Cổng zone nhìn ZONE THỬ (đã cộng nến này), mọi cổng khác nhìn zone
                # thật. Dựng trước khi xét, dẹp ngay sau — không để rò sang khối sau.
                if st.get("cong_zone"):
                    _dat_zone_thu(ctx)
                khop, vet = _xet_cong(st, ctx)
                ctx.zone_thu = None
                cong.append({"khoi": s, "ve": vet, "khop": bool(khop)})
                if st.get("cong_zone"):
                    _nuoi_zone(ctx, bool(khop))
                if not khop:
                    continue
            di = s
            break

        if di is None:
            # Hết nhánh ở mức này → quay về mức cha.
            if len(ngan) == 1:
                break
            ngan.pop()
            va.pop()
            # Mức cha là VÀ thì đi tiếp là LÀM NỐT (luôn được); là HOẶC thì đi tiếp là
            # THỬ PHƯƠNG ÁN KHÁC, và cái đó bị cấm sau khi đã chạm thị trường.
            if cham_thi_truong and not va[-1]:
                break
            continue

        duong.append(di)
        st = theo_id[di]
        t = st.get("type")
        if t == core.VAO_LENH:
            v = _vao_lenh(st, ctx)
            cham_thi_truong = True
            if v:
                # ⚠ Gắn KHỐI vào việc. Một lượt qua ngã rẽ VÀ đặt hai lệnh ở hai khối
                # khác nhau; không có khoá này thì nhật ký có hai dòng `lenh_dat` mà
                # không nói được cái nào của khối nào — đúng câu người ta cần khi debug.
                viec.append(dict(v, khoi=di))
        elif t == core.SUA_LENH:
            v = _sua_lenh(st, ctx)
            cham_thi_truong = True
            if v:
                viec.append(dict(v, khoi=di))

        ngan.append(list(ke.get(di, [])))
        va.append(_la_va(ngan[-1]))
        if not ngan[-1]:
            ket = "xong"
            # Đi hết một nhánh. Còn nhánh VÀ nào chưa làm ở phía trên thì LÀM NỐT —
            # tìm mức VÀ gần nhất còn việc, KHÔNG đụng gì nếu không tìm thấy (để `duong`
            # giữ nguyên đường vừa đi).
            k = len(ngan) - 1
            while k > 0 and not (va[k] and ngan[k]):
                k -= 1
            if not (va[k] and ngan[k]):
                break
            del ngan[k + 1:], va[k + 1:]
    else:
        raise LoiChay(f"Sơ đồ {tab} chạy quá {core.MAX_PROCESS_STEPS} bước — có vòng "
                      f"lặp không thoát được.")

    return {"nen": ctx.i, "j": ctx.j, "tab": tab,
            "lenh_id": ctx.lenh.id if ctx.lenh is not None else None,
            "duong": duong, "ket": ket, "cong": cong,
            "khoi": cong[-1]["khoi"] if cong else None,
            "viec": viec}


# ---------------------------------------------------------------------------
# Kết quả một lần chạy — BẤT BIẾN sau khi tính xong
# ---------------------------------------------------------------------------
class KetQua:
    """Dòng thời gian. Giao diện chỉ ĐỌC, không bao giờ ghi (core.md §12.7).

    Trạng thái sổ lệnh tại nến i là một PHÉP LỌC trên `so.lenh`, không phải một ảnh
    chụp — `so_lenh.Lenh` vốn đã mang sẵn `nen_dat` / `nen_khop` / `nen_dong`."""

    def __init__(self, ct, so, nhat_ky, cot, thong_ke):
        self._ct = ct
        self._sl_theo_lenh = None       # dựng lười, dùng lại cho mọi lệnh
        self.nen1, self.nen5 = ct.nen1, ct.nen5
        self.tf = ct.tf5
        self.so, self.nhat_ky, self.cot = so, nhat_ky, cot
        self.thong_ke = thong_ke
        self.doc = ct.doc
        #: `[[t, vốn, sụt_giảm_%], …]` — mỗi nến trục có lệnh đóng một điểm. Cố định,
        #: không theo con trỏ: đây là tổng kết cả lượt chạy (`_thong_ke`).
        self.duong_von = []

    def lenh_tai(self, i):
        """Mọi lệnh CÒN SỐNG tại nến quyết định thứ i — cho chart vẽ."""
        ra = []
        for l in self.so.lenh:
            if l.nen_dat > i:
                continue
            if l.nen_dong is not None and l.nen_dong <= i:
                continue
            ra.append(l)
        return ra

    def bang(self, i, j):
        """Bảng số liệu tại con trỏ — xem `_bang`."""
        return _bang(self, i, j)

    def the_lenh(self, i, tu_t=None):
        """Lệnh để CHART vẽ: mọi lệnh đã tồn tại tính tới nến i (kể cả đã đóng, vì lệnh
        đã đóng vẫn phải vẽ hai mũi tên nối nhau)."""
        return [_the_lenh(self, l) for l in self.so.lenh
                if l.nen_dat <= i and (tu_t is None
                                       or self.nen5["t"][l.nen_dong if l.nen_dong
                                                         is not None else i] >= tu_t)]


def _thong_ke(so, cd, ct):
    """Bảng tổng kết + ĐƯỜNG VỐN. Lãi/lỗ bằng TIỀN suy ra từ giá, không lưu thêm trường.

    ⚠ LỖI ĐÃ SỬA: phải cộng dồn theo THỨ TỰ ĐÓNG LỆNH, không phải thứ tự tạo lệnh. Tổng
    thì thứ tự nào cũng ra một số, nhưng ĐƯỜNG ĐI của vốn thì không — mà sụt giảm lại đo
    trên chính đường đi đó. Đo trên một năm thật: **9/386 lệnh đóng đảo thứ tự** so với
    lúc đặt. Lần này may mà con số cuối vẫn bằng nhau, nhưng đồ thị vẽ ra thì giật ngược
    thời gian, và một bộ dữ liệu khác là sụt giảm sai hẳn.

    Trả `(bảng_số, đường_vốn)`. Cả hai ra từ MỘT vòng lặp nên điểm cuối đường vốn bằng
    đúng `von_cuoi` và đáy sâu nhất bằng đúng `drawdown_pt` — không có hai nguồn để lệch.
    """
    xong = sorted((l for l in so.lenh
                   if l.nen_dong is not None and l.gia_dong is not None
                   and l.gia_khop is not None),
                  key=lambda l: (l.nen_dong, l.id))

    lai, thang, thua, tong_r = 0.0, 0, 0, 0.0
    r_thang, r_thua, lai_duong, lo_am = [], [], 0.0, 0.0
    von = dinh = cd.deposit
    dd_pt, dd_tien, dd_luc = 0.0, 0.0, None
    thua_lien, thua_dai = 0, 0
    duong = []

    for l in xong:
        chieu = 1.0 if l.huong == sl.MUA else -1.0
        tien = (l.gia_dong - l.gia_khop) * chieu * l.lot * cd.contract_size
        tien -= cd.commission * l.lot           # round-turn, trừ một lần lúc đóng
        lai += tien
        von += tien
        r = (l.gia_dong - l.gia_khop) * chieu / l.R if l.R else 0.0
        tong_r += r
        if tien > 0:
            thang += 1
            r_thang.append(r)
            lai_duong += tien
            thua_lien = 0
        else:
            thua += 1
            r_thua.append(r)
            lo_am -= tien
            thua_lien += 1
            thua_dai = max(thua_dai, thua_lien)

        dinh = max(dinh, von)
        sut = (dinh - von) / dinh * 100.0 if dinh else 0.0
        if sut > dd_pt:
            dd_pt, dd_tien = sut, dinh - von
            dd_luc = int(ct.nen5["t"][l.nen_dong])
        # Nhiều lệnh cùng đóng trong MỘT nến trục thì gộp làm một điểm: thư viện vẽ đòi
        # mốc thời gian tăng ngặt. Giữ `von` của lệnh cuối (đúng số dư sau nến đó) nhưng
        # giữ mức sụt SÂU NHẤT, để đáy đồ thị vẫn bằng đúng `drawdown_pt`.
        t = int(ct.nen5["t"][l.nen_dong])
        if duong and duong[-1][0] == t:
            duong[-1][1] = round(von, 2)
            duong[-1][2] = min(duong[-1][2], round(-sut, 3))
        else:
            duong.append([t, round(von, 2), round(-sut, 3)])

    n = thang + thua
    tb = lambda ds: round(sum(ds) / len(ds), 3) if ds else 0.0
    return {
        "so_lenh": len(so.lenh),
        "so_dong": n,
        "so_huy": sum(1 for l in so.lenh if l.ly_do_dong == "huy"),
        "thang": thang, "thua": thua,
        "ty_le_thang": round(thang / n * 100, 1) if n else 0.0,
        "lai_tien": round(lai, 2),
        "tong_R": round(tong_r, 2),
        "von_dau": round(cd.deposit, 2),
        "von_cuoi": round(cd.deposit + lai, 2),
        "lai_pt": round(lai / cd.deposit * 100, 2) if cd.deposit else 0.0,
        "drawdown_pt": round(dd_pt, 2),
        "drawdown_tien": round(dd_tien, 2),
        "drawdown_luc": dd_luc,
        "R_moi_lenh": round(tong_r / n, 3) if n else 0.0,
        "R_khi_thang": tb(r_thang),
        "R_khi_thua": tb(r_thua),
        # `None` = chưa có lệnh lỗ nào, KHÔNG phải 0. Hai chuyện khác hẳn nhau.
        "he_so_lai": round(lai_duong / lo_am, 2) if lo_am else None,
        "chuoi_thua": thua_dai,
        "so_zone": len(so.zone),
    }, duong


# ---------------------------------------------------------------------------
# VÒNG LẶP
# ---------------------------------------------------------------------------
class PhienChay:
    """MỘT lần chạy đang diễn ra — trạng thái sống, đi từng nhịp một.

    ⚠ VÌ SAO PHẢI CÓ LỚP NÀY. Trước đây toàn bộ chuyện này là thân của `chay()`: một
    vòng lặp quét trọn mảng nến, với mười mấy biến trạng thái nằm trong lòng hàm. Backtest
    thì hợp, nhưng LIVE thì ngược hẳn — mỗi phút về đúng MỘT nến.

    Nếu viết một bộ chạy thứ hai cho live thì hai bộ sẽ trôi xa nhau, và lời hứa "test
    như nào thì live như thế" chết ngay ngày đầu. Nên trạng thái ra khỏi thân hàm, thân
    vòng lặp thành `mot_nhip(j)`, và:

        backtest = vòng lặp gọi `mot_nhip`
        live     = gọi `mot_nhip` mỗi khi sàn đóng một nến

    ĐÚNG MỘT ĐOẠN CODE, không phải hai bản song song.

    Việc tách này KHÔNG được đổi một con số nào — `tests/test_bo_chay.py` giữ đúng điều
    đó bằng vân tay phủ mọi trường của mọi lệnh và mọi lượt.

    Thứ tự trong MỘT nến M1 — chốt ở core.md §12.1 và §6.0, không được đổi:

        1. SÀN xử lý trước: lệnh chờ khớp, SL/TP bị chạm (`khop_lenh`).
        2. Nếu nến này khép một nến TRỤC → engine cập nhật vùng nén.
        3. Nếu tới nhịp MANAGE → chạy Manage một lượt cho TỪNG lệnh đang sống.
        4. Nếu tới nhịp ENTRY → chạy Entry đúng một lượt.

    Sàn đi TRƯỚC sơ đồ vì đó là sự thật vật lý: giá chạm SL lúc 09:03 thì tới 09:05 khi
    chiến lược thức dậy, lệnh đã đóng rồi. Đảo lại là cho chiến lược sửa một lệnh mà thị
    trường đã đóng từ hai phút trước.
    """

    def __init__(self, doc, nen1, cd=None, tien_do=None):
        cd = cd or CaiDat()
        doc = core.normalize_process(doc)
        self.cd = cd
        self.doc = doc
        self.tien_do = tien_do
        self.ct = ct = ChuongTrinh(doc, nen1, cd)
        self.so = so = sl.SoLenh()
        self.ctx = Ctx(ct, so, ct.ts)

        # Vốn ĐÃ CHỐT (chỉ tính lệnh đã đóng) — đủ để `drawdown_pt` có nguồn thật thay vì
        # trả 0. Lãi nổi cố tình KHÔNG tính vào: drawdown theo lãi nổi đổi từng nến M1 và
        # biến một toán hạng đáng ra ổn định thành thứ giật liên tục.
        self.tien = {"von": cd.deposit, "dinh": cd.deposit}

        # ⚠ Phải gắn lên `ct`: `_sua_lenh` là hàm MODULE nên nó không với tới phương thức
        # của lớp này. Chế độ "Đóng hẳn" đóng lệnh xong không ghi tiền được là
        # `drawdown_pt` bỏ sót sạch những lệnh đó — mà toán hạng đó chính là thứ người ta
        # dùng làm cầu dao ("sụt giảm > 10 % thì ngừng vào lệnh"), nên cầu dao chết im lặng.
        ct.ghi_tien = self.ghi_tien
        ct.drawdown_pt = lambda: (0.0 if not self.tien["dinh"] else
                                  (self.tien["dinh"] - self.tien["von"])
                                  / self.tien["dinh"] * 100.0)

        self.nhat_ky = []
        nhip_m = core.TF_PHUT[ct.nhip[core.TAB_MANAGE]]
        dong1 = tt.moc_dong(ct.nen1, "M1")
        self.la_nhip_m = (np.mod(dong1, nhip_m * 60) == 0) if nhip_m > 1 else \
            np.ones(len(dong1), dtype=bool)
        self.mo_ho = 0
        self.i5_truoc = -1
        #: Nến trục đã CHỤP cột zone — chụp sau khi sơ đồ chạy, xem bước 5.
        self.i5_chup = -1
        self.i5 = -1

        # DANH SÁCH LỆNH SỐNG, tự nuôi. `so.dang_song()` quét TOÀN SỔ mỗi lần gọi; gọi nó
        # trên mỗi nến M1 là 354.000 × 550 lệnh = 195 triệu phép kiểm, và đo được nó ăn 57 %
        # thời gian một lần chạy. Nuôi danh sách ở đây là O(số lệnh ĐANG SỐNG) — thường 1–3.
        # Cố ý nuôi ở BỘ CHẠY chứ không sửa `so_lenh`: đó là chuyện tốc độ của vòng lặp,
        # không phải chuyện mô hình sổ lệnh.
        self.song, self.n_lenh = [], 0

        # ⚠ VÙNG NÉN PHẢI THÀNH CỘT. `Zone` mutate liên tục (đếm nến, nới đỉnh/đáy), nên
        # trạng thái vùng tại nến i KHÔNG suy ra được từ đối tượng cuối cùng. Bảng số liệu
        # mà hỏi lại `so.zone_hien_hanh()` thì ở con trỏ nào cũng đọc ra trạng thái CUỐI
        # BACKTEST — bảng nói một đằng, nhật ký nói một nẻo, đúng lúc đang debug.
        # 7 cột × 71k nến × 8 B = 4 MB một năm. Rẻ hơn nhiều so với một buổi đi tìm nhầm.
        # Danh sách suy TỪ SƠ ĐỒ, không viết cứng: thêm một engine khác là bảng có ngay.
        self.CV = CV = tuple(dict.fromkeys(
            x["ten"] for x in core.toan_hang_dung(doc)
            if x["ten"] in kho.engine_d02.ENGINE_TRA_LOI))
        self.cot_zone = {k: np.full(len(ct.nen5), NAN) for k in CV}
        self.dung_sai = {k for k in CV if k in core.TOAN_HANG_DUNG_SAI}
        self.zone_id = [None] * len(ct.nen5)
        self.so_zone = np.zeros(len(ct.nen5), dtype=np.int32)

    def ghi_tien(self, l):
        cd = self.cd
        if l.gia_dong is None or l.gia_khop is None:
            return
        chieu = 1.0 if l.huong == sl.MUA else -1.0
        self.tien["von"] += ((l.gia_dong - l.gia_khop) * chieu * l.lot * cd.contract_size
                             - cd.commission * l.lot)
        self.tien["dinh"] = max(self.tien["dinh"], self.tien["von"])

    # ----------------------------------------------------------------- một nhịp
    def mot_nhip(self, j):
        """Xử lý ĐÚNG một nến M1. Đây là toàn bộ bộ máy — backtest gọi nó trong vòng
        lặp, live gọi nó mỗi khi sàn đóng một nến."""
        ct, so, ctx, cd = self.ct, self.so, self.ctx, self.cd

        # Đồng bộ đầu nến: lệnh mới sinh ở lượt Entry nến TRƯỚC giờ mới được xét khớp —
        # đúng bản chất, giá của nến trước đã là quá khứ.
        if len(so.lenh) != self.n_lenh:
            self.song.extend(so.lenh[self.n_lenh:])
            self.n_lenh = len(so.lenh)
        if self.song:
            self.song[:] = [l for l in self.song if l.con_song]

        i5 = int(ct.m1_to_5[j])
        self.i5 = i5
        ctx.j, ctx.i = j, max(i5, 0)
        nen = ct.nen1[j]

        # ---- 1. SÀN ----
        for l in list(self.song):
            for e in khop_lenh.trong_nen(l, nen, cd.spread_gia):
                if e["loai"] == "khop":
                    so.khop(l, e["gia"], ctx.i, ctx.j)
                else:
                    so.dong(l, e["gia"], ctx.i, e["ly_do"])
                    self.ghi_tien(l)
                    if e.get("mo_ho"):
                        self.mo_ho += 1

        if i5 < 0:
            return                          # chưa có nến trục nào đóng — chưa quyết gì

        # ---- 2. ENGINE (một lần mỗi nến trục) ----
        if i5 != self.i5_truoc:
            ctx.co_lo_hong = bool(ct.lo_hong5[i5])
            ctx.lenh = None
            # ⚠ Cờ này mở ra ở ĐẦU nến trục và chỉ đóng lại khi cổng zone được xét.
            # Sau khi chạy xong Entry, còn mở nghĩa là dòng chảy KHÔNG TỚI được cổng —
            # xem chú thích ở cuối `mot_nhip`.
            ctx.zone_da_xet = False
            ct.engine.moi_nen(ctx)
            self.i5_truoc = i5

        # ---- 3. MANAGE — một lượt cho MỖI lệnh đang sống ----
        if self.la_nhip_m[j]:
            ctx.tab = core.TAB_MANAGE
            for l in list(self.song):
                if not l.con_song:
                    continue        # vừa bị chính lượt Manage trước đó đóng
                ctx.lenh = l
                r = _chay_so_do(core.TAB_MANAGE, ctx)
                if r:
                    r["seq"] = len(self.nhat_ky)
                    self.nhat_ky.append(r)
            ctx.lenh = None

        # ---- 4. ENTRY — đúng một lượt ----
        if ct.la_nhip5[j]:
            ctx.tab = core.TAB_ENTRY
            r = _chay_so_do(core.TAB_ENTRY, ctx)
            if r:
                r["seq"] = len(self.nhat_ky)
                self.nhat_ky.append(r)
            if self.tien_do and i5 % 2000 == 0:
                self.tien_do(i5, len(ct.nen5))

        # ---- 5. CHỐT ZONE + chụp cột (sau khi sơ đồ đã chạy) ----
        #
        # ⚠ Phải chụp Ở ĐÂY chứ không ở bước 2 nữa: từ nay zone lớn lên NGAY TRONG lúc
        # sơ đồ chạy, nên chụp trước là chụp trạng thái của nến trước.
        if i5 >= 0 and self.i5_chup != i5 and ct.la_nhip5[j]:
            # Dòng chảy KHÔNG TỚI được cổng zone (một cổng phía trên trượt) → ZONE CHẾT.
            #
            # Chọn thế chứ không cho zone đứng im, vì "nén" nghĩa là giá đứng yên trong
            # một quãng LIỀN MẠCH. Nến không được kiểm thì ta KHÔNG BIẾT nó có nén hay
            # không — cho zone sống xuyên qua một khoảng không kiểm là tự lừa mình.
            if not ctx.zone_da_xet and ct.co_cong_zone:
                so.dong_zone()
            for k in self.CV:
                v = ct.engine.doc(k, ctx)
                self.cot_zone[k][i5] = float(v) if k in self.dung_sai else v
            v_ht = so.zone_hien_hanh()
            self.zone_id[i5] = v_ht.id if v_ht else None
            self.so_zone[i5] = len(so.zone)
            self.i5_chup = i5

    # ------------------------------------------------------------------ ảnh chụp
    def anh_chup(self):
        """`KetQua` đọc được TẠI ĐÂY, mà KHÔNG chốt sổ.

        ⚠ Live phải có cái này. `ket_thuc()` đóng sạch lệnh còn sống — gọi nó lúc đang
        chạy live là tự tay đóng lệnh thật. Ảnh chụp thì không đụng vào gì cả: nó chỉ
        gói `ct`/`so`/`nhat_ky` lại cho mấy hàm đọc (`bang`, `the_lenh`, `lenh_tai`)
        dùng — đúng những hàm mà cửa sổ tester đang ăn.

        Nhờ vậy `Chart`, `BangSoLieu`, `Journey` chạy ở Live mà không sửa một dòng: hai
        cửa sổ đọc CÙNG một hình dạng dữ liệu, từ cùng một đoạn code."""
        kq = KetQua(self.ct, self.so, self.nhat_ky, self.ct._cot,
                    {"so_luot": len(self.nhat_ky), "nen_mo_ho": self.mo_ho})
        kq.duong_von = []
        kq.cot_zone = self.cot_zone
        kq.zone_id = self.zone_id
        kq.so_zone = self.so_zone
        return kq

    # ------------------------------------------------------------------- kết sổ
    def ket_thuc(self):
        """Hết dữ liệu → chốt sổ, trả `KetQua` bất biến.

        ⚠ CHỈ backtest gọi hàm này. Live thì không bao giờ "hết dữ liệu" nên không được
        chốt sổ — gọi nhầm nó lúc đang live là đóng sạch lệnh thật."""
        ct, so, ctx = self.ct, self.so, self.ctx
        # Lệnh còn sống lúc hết dữ liệu: đóng theo giá đóng nến cuối, ghi rõ lý do, và
        # tách riêng trong thống kê (core.md §12.13).
        cuoi = float(ct.nen1["c"][-1])
        for l in list(so.dang_song()):
            so.dong(l, cuoi if l.da_khop else None, ctx.i,
                    "het_du_lieu" if l.da_khop else "huy")
            self.ghi_tien(l)

        tk, duong_von = _thong_ke(so, self.cd, ct)
        tk["nen_mo_ho"] = self.mo_ho
        tk["so_luot"] = len(self.nhat_ky)
        kq = KetQua(ct, so, self.nhat_ky, ct._cot, tk)
        kq.duong_von = duong_von
        kq.cot_zone = self.cot_zone
        kq.zone_id = self.zone_id
        kq.so_zone = self.so_zone
        return kq


def chay(doc, nen1, cd=None, tien_do=None):
    """Chạy trọn một backtest. Trả `KetQua` bất biến.

    Chỉ là vòng lặp quanh `PhienChay.mot_nhip` — mọi luật nằm ở đó, xem docstring của
    lớp. Giữ hàm này vì nó là cửa mà cả app lẫn bộ test gọi vào."""
    phien = PhienChay(doc, nen1, cd, tien_do)
    for j in range(len(phien.ct.nen1)):
        phien.mot_nhip(j)
    return phien.ket_thuc()


# ---------------------------------------------------------------------------
# BẢNG SỐ LIỆU — bốn khối, mỗi khối một nguồn rõ ràng (core.md §12.9)
# ---------------------------------------------------------------------------
def _bang(kq, i, j):
    """Số liệu tại con trỏ. Bốn khối, KHÔNG trộn lẫn nguồn.

    ⚠ Bảng này và nhật ký PHẢI nói cùng một thứ. Chỗ dễ lệch nhất: toán hạng nhóm
    "Lệnh này" không có MỘT giá trị tại nến i — Manage chạy một lượt cho MỖI lệnh, nên
    mỗi lệnh một bộ số. Vì thế chúng nằm ở khối THỨ TƯ, mỗi lệnh một hàng, chứ không bị
    ép thành một con số duy nhất."""
    ct = kq._ct
    so = kq.so
    ra = {"toan_hang": [], "engine": [], "tai_khoan": [], "lenh": []}

    for k, cot in sorted(ct._cot.items()):
        ten, tf, ck, pp = k
        nhan = core.TOAN_HANG_LABELS.get(ten, ten)
        phan = [tf] + ([str(int(ck))] if ck else []) + ([pp] if pp else [])
        v = float(cot[i]) if 0 <= i < len(cot) else NAN
        ra["toan_hang"].append({"ten": f"{nhan}({', '.join(phan)})", "gia_tri": _js(v)})

    # ĐỌC CỘT, không hỏi lại `so.zone_hien_hanh()`: sổ đang ở trạng thái CUỐI backtest,
    # nên hỏi lại là ở con trỏ nào cũng ra cùng một đáp án — sai và im lặng.
    cv = kq.cot_zone
    co = 0 <= i < len(kq.nen5)
    ra["engine"] = [
        {"ten": core.TOAN_HANG_LABELS.get(k, k),
         "gia_tri": (bool(cv[k][i]) if k in core.TOAN_HANG_DUNG_SAI else _js(cv[k][i]))
         if co and cv[k][i] == cv[k][i] else None}
        for k in cv]

    song = kq.lenh_tai(i)
    ra["tai_khoan"] = [{"ten": x, "gia_tri": y} for x, y in (
        ("Giá Bid", _js(float(ct.nen1["c"][j]))),
        ("Số lệnh chờ", sum(1 for l in song if not l.da_khop)),
        ("Số vị thế đang mở", sum(1 for l in song if l.da_khop)),
        ("Số lệnh đã đóng", sum(1 for l in so.lenh if l.nen_dong is not None
                                and l.nen_dong <= i)),
        ("Số vùng nén đã sinh", int(kq.so_zone[i]) if co else 0),
    )]

    gia = float(ct.nen1["c"][j])
    for l in song:
        ra["lenh"].append({
            "id": l.id, "huong": l.huong, "da_khop": bool(l.da_khop),
            "gia_vao": _js(l.gia_khop), "sl": _js(l.sl), "tp": _js(l.tp),
            "lai_R": _js(l.lai_R(_gia_thoat(l, gia, ct.cd))) if l.da_khop else None,
            "sl_hoa_von": bool(l.sl_o_hoa_von),
            "so_nen_song": int(l.so_nen_song(i)),
        })
    return ra


def _moc_muc(kq):
    """Mọi mốc SL/TP của từng lệnh theo thời gian: `{id: [[t, sl, tp], …]}`.

    Điểm ĐẦU lấy từ chính bản ghi `lenh_dat`, không suy ngược từ `gia_dat ± R` như bản
    trước: cách suy ngược đúng với SL nhưng chịu thua với TP, vì công thức khoảng cách
    TP không được lưu lại đâu cả.

    Dựng lười một lần rồi dùng lại — mỗi khung hình phát lại đều hỏi tới nó."""
    if kq._sl_theo_lenh is None:
        m = {}
        for r in kq.nhat_ky:
            for v in r["viec"]:
                if v.get("loai") in ("lenh_dat", "lenh_sua"):
                    m.setdefault(v["lenh_id"], []).append(
                        [int(kq.nen5["t"][r["nen"]]), v.get("sl"), v.get("tp")])
        kq._sl_theo_lenh = m
    return kq._sl_theo_lenh


def _muc_lich_su(kq, l, k, hien_tai):
    """Đường đi của MỘT MỨC theo thời gian: `[[t, v], …]`. `k` = 1 cho SL, 2 cho TP.

    Nguồn là chính NHẬT KÝ, không phải suy đoán — nên chart vẽ ra đúng cái bậc thang mà
    `Dời SL về hoà vốn` tạo ra, đúng nến nó xảy ra. Đó là khoảnh khắc người dùng muốn
    kiểm chứng nhất, mà bản trước chỉ vẽ mức cuối cùng nên nó tàng hình.

    ⚠ TP phải đi qua đây y như SL. Trước đây chart vẽ TP bằng `l.tp` — tức mức TP lúc
    BACKTEST ĐÃ XONG — rồi kéo ngược về tận lúc đặt lệnh: nếu chiến lược có `Dời Take
    Profit` thì con trỏ đứng ở quá khứ vẫn thấy mức TP của tương lai. Đúng cái lỗi mà
    `sl_lich_su` sinh ra để chữa, chỉ là bỏ sót một nửa."""
    if hien_tai is None:
        return []
    ra, cuoi = [], None
    for moc in _moc_muc(kq).get(l.id) or []:
        v = moc[k]
        if v is None or v == cuoi:
            continue
        ra.append([int(moc[0]), float(v)])
        cuoi = v
    return ra or [[int(kq.nen5["t"][l.nen_dat]), float(hien_tai)]]


def _sl_lich_su(kq, l):
    return _muc_lich_su(kq, l, 1, l.sl)


def lenh_tai_nen(kq, l, i, gia):
    """Một lệnh còn sống, NHÌN TỪ nến quyết định thứ i. Không được lộ tương lai.

    ⚠ LỖI ĐÃ SỬA — `Lenh` là đối tượng của CUỐI backtest. `l.da_khop`, `l.gia_khop`,
    `l.sl`, `l.tp` đều là trạng thái cuối, và mọi lần `Sửa lệnh` đã ghi đè lên chúng.
    Đọc thẳng ra bảng thì L-0006 — đặt 17:55, khớp 19:55 — hiện ngay là "đã khớp,
    −1.21R" khi con trỏ mới ở 17:59, tức bảng nói khác nhật ký ĐÚNG LÚC người dùng đang
    kiểm. Đó chính là cái bẫy core.md §12.9 dựng cả mục ra để cảnh báo, và chart đã
    dính một lần rồi (§12.16). Mọi trường dưới đây phải cắt theo `i`."""
    khop = l.nen_khop is not None and l.nen_khop <= i
    s, p = _muc_tai(kq, l, i)
    hoa_von = False
    if khop and s is not None:
        hoa_von = s >= l.gia_khop if l.huong == sl.MUA else s <= l.gia_khop
    return {
        "id": l.id, "huong": l.huong, "loai": l.loai, "da_khop": bool(khop),
        "gia_dat": _js(l.gia_dat),
        "gia_vao": _js(l.gia_khop) if khop else None,
        "sl": _js(s), "tp": _js(p),
        # Qua `_gia_thoat`: lệnh BÁN thoát ở Ask, không phải Bid — xem hàm đó.
        "lai_R": _js(l.lai_R(_gia_thoat(l, gia, kq._ct.cd))) if (khop and l.R) else None,
        "sl_hoa_von": bool(hoa_von),
    }


def _muc_tai(kq, l, i):
    """(SL, TP) của một lệnh TẠI nến quyết định thứ i — không phải mức cuối cùng."""
    t = int(kq.nen5["t"][i])
    s, p = l.sl, l.tp
    for k, (tt, vs, vp) in enumerate(_moc_muc(kq).get(l.id) or []):
        if tt > t:
            break
        if k == 0 or vs is not None:
            s = vs
        if k == 0 or vp is not None:
            p = vp
    return s, p


def _the_lenh(kq, l):
    """Một lệnh → thứ chart cần để vẽ. Chart KHÔNG được biết gì ngoài đây."""
    return {
        "sl_lich_su": _sl_lich_su(kq, l),
        "tp_lich_su": _muc_lich_su(kq, l, 2, l.tp),
        "id": l.id, "huong": l.huong, "trang_thai": l.trang_thai,
        "t_dat": int(kq.nen5["t"][l.nen_dat]),
        "t_khop": int(kq.nen5["t"][l.nen_khop]) if l.nen_khop is not None else None,
        "t_dong": int(kq.nen5["t"][l.nen_dong]) if l.nen_dong is not None else None,
        "gia_dat": _js(l.gia_dat), "gia_khop": _js(l.gia_khop),
        "gia_dong": _js(l.gia_dong), "sl": _js(l.sl), "tp": _js(l.tp),
        "ly_do_dong": l.ly_do_dong, "lot": l.lot,
        "lai_R": _js((l.gia_dong - l.gia_khop) * (1 if l.huong == sl.MUA else -1) / l.R)
        if (l.gia_dong is not None and l.gia_khop is not None and l.R) else None,
    }
