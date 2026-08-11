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

import core
import khop_lenh
import kho
import so_lenh as sl
import tinh_toan as tt

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

    __slots__ = ("ct", "so", "i", "j", "tab", "lenh", "co_lo_hong", "ts")

    def __init__(self, ct, so, ts):
        self.ct, self.so, self.ts = ct, so, ts
        self.i = 0            # chỉ số trên trục quyết định (nến M5)
        self.j = 0            # chỉ số trên trục M1
        self.tab = core.TAB_ENTRY
        self.lenh = None      # lệnh đang được xét (chỉ Manage)
        self.co_lo_hong = False

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
        for tab in core.TABS:
            bd = [s for s in (self.doc.get(tab) or {}).get("steps") or []
                  if core.is_start_step(s)]
            self.nhip[tab] = (bd[0].get("nhip") if bd else None) \
                or core.NHIP_MAC_DINH[tab]
        self.tf5 = self.nhip[core.TAB_ENTRY]
        self.nen5 = tt.gop(self.nen1, self.tf5)
        if not len(self.nen5):
            raise LoiChay("Không đủ nến để dựng dù một cây nến trên khung quyết định.")

        dong5 = tt.moc_dong(self.nen5, self.tf5)
        dong1 = tt.moc_dong(self.nen1, "M1")
        # Với mỗi nến M1, nến trục nào đã ĐÓNG gần nhất. −1 = chưa có nến trục nào.
        self.m1_to_5 = np.searchsorted(dong5, dong1, side="right") - 1
        # Nến M1 nào ĐÓNG ĐÚNG lúc một nến trục đóng → đó là nhịp chạy Entry.
        self.la_nhip5 = np.isin(dong1, dong5)

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
                for c in st.get("conditions") or []:
                    for o in (c.get("trai"), c.get("phai")):
                        if isinstance(o, dict) and o.get("ten"):
                            self._xin_cot(o, tab, st)
        # Engine cần `atr_bps` và `atr` trên khung quyết định dù sơ đồ có hỏi hay không.
        for ten in ("atr_bps", "atr"):
            self._xin_cot({"ten": ten, "tf": self.tf5,
                           "period": self.ts["chu_ky_atr"]}, None, None)

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


# ---------------------------------------------------------------------------
# Đánh giá toán hạng
# ---------------------------------------------------------------------------
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

    if ten in ("close", "open", "high", "low"):
        return ctx.gia_nen(ten[0] if ten != "close" else "c", o.get("shift", 0))
    if ten == "bid":
        return ctx.bid
    if ten == "ask":
        return ctx.ask
    if ten == "spread":
        return ct.cd.spread_diem

    if ten == "so_vi_the":
        return float(ctx.so.so_vi_the())
    if ten == "so_lenh_cho":
        return float(ctx.so.so_lenh_cho())
    if ten == "so_lenh_hom_nay":
        hnay = int(ct.nen5["t"][ctx.i]) // 86400
        return float(sum(1 for x in ctx.so.lenh
                         if int(ct.nen5["t"][x.nen_dat]) // 86400 == hnay))
    if ten == "drawdown_pt":
        return ct.drawdown_pt()

    if ten in ("gio", "thu"):
        t = int(ct.nen1["t"][ctx.j])
        return float((t // 3600) % 24) if ten == "gio" else float((t // 86400 + 4) % 7 + 2)

    l = ctx.lenh
    if l is None:
        return NAN                              # "lệnh này" ở Entry — soát tĩnh đã chặn
    if ten == "lenh_da_khop":
        return bool(l.da_khop)
    if ten == "lenh_la_mua":
        return l.huong == sl.MUA
    if ten == "lenh_sl_hoa_von":
        return bool(l.sl_o_hoa_von)
    if ten == "lenh_lai_R":
        return float(l.lai_R(ctx.bid))
    if ten == "lenh_so_nen_song":
        return float(l.so_nen_song(ctx.i))
    if ten == "lenh_gia_vao":
        return float(l.gia_khop) if l.gia_khop is not None else NAN
    raise LoiChay(f'Toán hạng "{ten}" chưa được cài trong bộ chạy.')


def _so_sanh(trai, phep, phai, phai2=None):
    """Một phép so. NaN ở bất kỳ vế nào → False (cổng trượt), không nổ."""
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
    if phep == "trong_khoang":
        return phai <= trai <= (phai2 if phai2 is not None else phai)
    # `cat_len` / `cat_xuong` cần giá trị nến trước — chưa dùng ở sơ đồ mẫu.
    raise LoiChay(f'Phép so "{phep}" chưa được cài trong bộ chạy.')


def _xet_cong(st, ctx):
    """Một cổng: trả `(khớp?, [vết từng điều kiện])`.

    LUÔN tính đủ mọi điều kiện, không ngắt ở cái sai đầu tiên — vết đó là thứ duy nhất
    trả lời được "cổng trượt vì con số nào" khi nhật ký được đọc lại."""
    vet, khop = [], True
    for c in st.get("conditions") or []:
        t = _lay_toan_hang(c["trai"], ctx)
        loai = c.get("phai_loai") or "so"
        if loai == "toan_hang":
            p = _lay_toan_hang(c["phai"], ctx)
        elif isinstance(c.get("phai"), str):
            p = ctx.ct.so(c["phai"])
        else:
            p = c.get("phai")
            p = float(p) if isinstance(p, (int, float)) else NAN
        dat = _so_sanh(t, c["phep"], p, c.get("phai2"))
        if c.get("dao"):
            dat = not dat
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

    ⚠ `theo_ATR` và `theo_ATR_vung` là HAI THỨ KHÁC NHAU, và đây là chỗ duy nhất giữ
    cho chúng khác nhau (core.md §6.3):
      * `theo_ATR`      = ATR của nến VỪA ĐÓNG   → đo đệm vào lệnh (`comp.atr_current`)
      * `theo_ATR_vung` = ATR TRUNG BÌNH cả vùng → ĐỊNH NGHĨA 1R    (`comp.atr_avg`)
    Gộp làm một là mất đúng cái làm cho 1R nhất quán, mà validator KHÔNG bắt được."""
    if not k:
        return NAN
    v = ctx.ct.so(k.get("value", 0))
    tinh = k.get("tinh")
    if tinh == "theo_ATR":
        return v * ctx.chi_bao("atr", period=ctx.ts["chu_ky_atr"])
    if tinh == "theo_ATR_vung":
        vung = ctx.so.vung_hien_hanh()
        return v * vung.atr_tb if vung else NAN
    if tinh == "theo_R":
        return v * (R if R is not None else NAN)
    if tinh == "theo_gia":
        return v
    if tinh == "theo_pt":
        return v / 100.0 * (neo if neo is not None else NAN)
    if tinh == "theo_bien_vung":
        vung = ctx.so.vung_hien_hanh()
        if vung is None or neo is None:
            return NAN
        return abs(neo - (vung.day if neo >= vung.dinh else vung.dinh))
    raise LoiChay(f'Cách tính "{tinh}" chưa được cài trong bộ chạy.')


# ---------------------------------------------------------------------------
# Hai hành động chạm thị trường
# ---------------------------------------------------------------------------
def _vao_lenh(st, ctx):
    """Đặt một lệnh. Trả bản ghi `viec` cho nhật ký, hoặc None nếu không đặt được.

    NEO: lệnh chờ stop neo vào MÉP VÙNG thuận chiều (Mua → đỉnh, Bán → đáy) rồi cộng
    đệm ra ngoài — đúng `entry = highest_high + buf` của bản gốc. Lệnh thị trường thì
    neo vào giá hiện tại."""
    ct, so_ = ctx.ct, ctx.so
    huong = st.get("huong", sl.MUA)
    loai = st.get("loai", "stop")
    lot = ct.so(st.get("lot", 0.01))
    vung = so_.vung_hien_hanh()

    if loai == "stop" and vung is not None:
        mep = vung.dinh if huong == sl.MUA else vung.day
    else:
        mep = ctx.ask if huong == sl.MUA else ctx.bid
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
        so_.khop(l, gia_dat, ctx.i)
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
    elif cd == "trailing":
        d = _khoang(st.get("khoang"), ctx, neo=ctx.bid, R=l.R)
        if d != d:
            return None
        moi = ctx.bid - d if l.huong == sl.MUA else ctx.bid + d
        # Trailing chỉ ĐI THEO một chiều. Cho nó lùi lại là nới rủi ro ra, tức không
        # còn là trailing nữa.
        if l.sl is not None and ((moi <= l.sl) if l.huong == sl.MUA else (moi >= l.sl)):
            return None
        l.sl = moi
    elif cd == "dong_han":
        so_.dong(l, ctx.bid if l.huong == sl.MUA else ctx.ask, ctx.i, "dong_tay")
        return {"loai": "lenh_dong", "lenh_id": l.id, "ly_do": "dong_tay",
                "gia": _js(l.gia_dong)}
    elif cd == "huy_cho":
        if l.da_khop:
            return None
        so_.dong(l, None, ctx.i, "huy")
        return {"loai": "lenh_huy", "lenh_id": l.id}
    elif cd == "dong_mot_phan":
        raise LoiChay("Chế độ \"Đóng một phần\" chưa được cài trong sổ lệnh.")
    else:
        raise LoiChay(f'Chế độ sửa lệnh "{cd}" chưa được cài trong bộ chạy.')

    if truoc["sl"] == l.sl and truoc["tp"] == l.tp:
        return None
    return {"loai": "lenh_sua", "lenh_id": l.id, "che_do": cd,
            "sl": _js(l.sl), "tp": _js(l.tp)}


# ---------------------------------------------------------------------------
# Đi trên đồ thị
# ---------------------------------------------------------------------------
def _chay_so_do(tab, ctx):
    """Một LƯỢT chạy của một sơ đồ. Trả bản ghi nhật ký.

    LUẬT LÙI (core.md §12.5a): cổng trượt thì lùi về ngã rẽ gần nhất còn nhánh chưa
    thử — TRỪ KHI lượt này đã chạm thị trường, khi đó hết lượt ngay. Đã bắn lệnh ra thì
    không rút lại được, nên quay lui thử nhánh khác là đẻ ra lệnh thứ hai."""
    ct = ctx.ct
    L = ct.luong[tab]
    theo_id, ke = L["theo_id"], L["ke"]
    vao = L["vao"]
    if not vao:
        return None

    duong = [vao]
    ngan = [list(ke.get(vao, []))]
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
                khop, vet = _xet_cong(st, ctx)
                cong.append({"khoi": s, "ve": vet, "khop": bool(khop)})
                if not khop:
                    continue
            di = s
            break

        if di is None:
            # Không nhánh nào ở đây khớp.
            if cham_thi_truong or len(ngan) == 1:
                break
            ngan.pop()
            duong.pop()
            continue

        duong.append(di)
        st = theo_id[di]
        t = st.get("type")
        if t == core.VAO_LENH:
            v = _vao_lenh(st, ctx)
            cham_thi_truong = True
            if v:
                viec.append(v)
        elif t == core.SUA_LENH:
            v = _sua_lenh(st, ctx)
            cham_thi_truong = True
            if v:
                viec.append(v)

        ngan.append(list(ke.get(di, [])))
        if not ngan[-1]:
            ket = "xong"
            break
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
        "so_vung": len(so.vung),
    }, duong


# ---------------------------------------------------------------------------
# VÒNG LẶP
# ---------------------------------------------------------------------------
def chay(doc, nen1, cd=None, tien_do=None):
    """Chạy trọn một backtest. Trả `KetQua` bất biến.

    Thứ tự trong MỘT nến M1 — chốt ở core.md §12.1 và §6.0, không được đổi:

        1. SÀN xử lý trước: lệnh chờ khớp, SL/TP bị chạm (`khop_lenh`).
        2. Nếu nến này khép một nến TRỤC → engine cập nhật vùng nén.
        3. Nếu tới nhịp MANAGE → chạy Manage một lượt cho TỪNG lệnh đang sống.
        4. Nếu tới nhịp ENTRY → chạy Entry đúng một lượt.

    Sàn đi TRƯỚC sơ đồ vì đó là sự thật vật lý: giá chạm SL lúc 09:03 thì tới 09:05 khi
    chiến lược thức dậy, lệnh đã đóng rồi. Đảo lại là cho chiến lược sửa một lệnh mà thị
    trường đã đóng từ hai phút trước."""
    cd = cd or CaiDat()
    doc = core.normalize_process(doc)
    ct = ChuongTrinh(doc, nen1, cd)
    so = sl.SoLenh()
    ctx = Ctx(ct, so, ct.ts)

    # Vốn ĐÃ CHỐT (chỉ tính lệnh đã đóng) — đủ để `drawdown_pt` có nguồn thật thay vì
    # trả 0. Lãi nổi cố tình KHÔNG tính vào: drawdown theo lãi nổi đổi từng nến M1 và
    # biến một toán hạng đáng ra ổn định thành thứ giật liên tục.
    tien = {"von": cd.deposit, "dinh": cd.deposit}

    def ghi_tien(l):
        if l.gia_dong is None or l.gia_khop is None:
            return
        chieu = 1.0 if l.huong == sl.MUA else -1.0
        tien["von"] += ((l.gia_dong - l.gia_khop) * chieu * l.lot * cd.contract_size
                        - cd.commission * l.lot)
        tien["dinh"] = max(tien["dinh"], tien["von"])

    ct.drawdown_pt = lambda: (0.0 if not tien["dinh"] else
                              (tien["dinh"] - tien["von"]) / tien["dinh"] * 100.0)

    nhat_ky = []
    nhip_m = core.TF_PHUT[ct.nhip[core.TAB_MANAGE]]
    dong1 = tt.moc_dong(ct.nen1, "M1")
    la_nhip_m = (np.mod(dong1, nhip_m * 60) == 0) if nhip_m > 1 else \
        np.ones(len(dong1), dtype=bool)
    mo_ho = 0
    i5_truoc = -1

    # DANH SÁCH LỆNH SỐNG, tự nuôi. `so.dang_song()` quét TOÀN SỔ mỗi lần gọi; gọi nó
    # trên mỗi nến M1 là 354.000 × 550 lệnh = 195 triệu phép kiểm, và đo được nó ăn 57 %
    # thời gian một lần chạy. Nuôi danh sách ở đây là O(số lệnh ĐANG SỐNG) — thường 1–3.
    # Cố ý nuôi ở BỘ CHẠY chứ không sửa `so_lenh`: đó là chuyện tốc độ của vòng lặp,
    # không phải chuyện mô hình sổ lệnh.
    song, n_lenh = [], 0

    # ⚠ VÙNG NÉN PHẢI THÀNH CỘT. `VungNen` mutate liên tục (đếm nến, nới đỉnh/đáy), nên
    # trạng thái vùng tại nến i KHÔNG suy ra được từ đối tượng cuối cùng. Bảng số liệu
    # mà hỏi lại `so.vung_hien_hanh()` thì ở con trỏ nào cũng đọc ra trạng thái CUỐI
    # BACKTEST — bảng nói một đằng, nhật ký nói một nẻo, đúng lúc đang debug.
    # 7 cột × 71k nến × 8 B = 4 MB một năm. Rẻ hơn nhiều so với một buổi đi tìm nhầm.
    # Toán hạng nào do ENGINE trả lời thì phải GHI THÀNH CỘT — đối tượng vùng nén mutate
    # liên tục, hỏi lại nó sau khi chạy xong là ở con trỏ nào cũng ra trạng thái cuối.
    # Danh sách suy TỪ SƠ ĐỒ, không viết cứng: thêm một engine khác là bảng có ngay.
    CV = tuple(dict.fromkeys(
        x["ten"] for x in core.toan_hang_dung(doc)
        if x["ten"] in kho.engine_d02.ENGINE_TRA_LOI))
    cot_vung = {k: np.full(len(ct.nen5), NAN) for k in CV}
    dung_sai = {k for k in CV if k in core.TOAN_HANG_DUNG_SAI}
    vung_id = [None] * len(ct.nen5)
    so_vung = np.zeros(len(ct.nen5), dtype=np.int32)

    for j in range(len(ct.nen1)):
        # Đồng bộ đầu nến: lệnh mới sinh ở lượt Entry nến TRƯỚC giờ mới được xét khớp —
        # đúng bản chất, giá của nến trước đã là quá khứ.
        if len(so.lenh) != n_lenh:
            song.extend(so.lenh[n_lenh:])
            n_lenh = len(so.lenh)
        if song:
            song[:] = [l for l in song if l.con_song]

        i5 = int(ct.m1_to_5[j])
        ctx.j, ctx.i = j, max(i5, 0)
        nen = ct.nen1[j]

        # ---- 1. SÀN ----
        for l in list(song):
            for e in khop_lenh.trong_nen(l, nen, cd.spread_gia):
                if e["loai"] == "khop":
                    so.khop(l, e["gia"], ctx.i)
                else:
                    so.dong(l, e["gia"], ctx.i, e["ly_do"])
                    ghi_tien(l)
                    if e.get("mo_ho"):
                        mo_ho += 1

        if i5 < 0:
            continue                        # chưa có nến trục nào đóng — chưa quyết gì

        # ---- 2. ENGINE (một lần mỗi nến trục) ----
        if i5 != i5_truoc:
            ctx.co_lo_hong = bool(ct.lo_hong5[i5])
            ctx.lenh = None
            ct.engine.moi_nen(ctx)
            for k in CV:
                v = ct.engine.doc(k, ctx)
                cot_vung[k][i5] = float(v) if k in dung_sai else v
            v_ht = so.vung_hien_hanh()
            vung_id[i5] = v_ht.id if v_ht else None
            so_vung[i5] = len(so.vung)
            i5_truoc = i5

        # ---- 3. MANAGE — một lượt cho MỖI lệnh đang sống ----
        if la_nhip_m[j]:
            ctx.tab = core.TAB_MANAGE
            for l in list(song):
                if not l.con_song:
                    continue        # vừa bị chính lượt Manage trước đó đóng
                ctx.lenh = l
                r = _chay_so_do(core.TAB_MANAGE, ctx)
                if r:
                    r["seq"] = len(nhat_ky)
                    nhat_ky.append(r)
            ctx.lenh = None

        # ---- 4. ENTRY — đúng một lượt ----
        if ct.la_nhip5[j]:
            ctx.tab = core.TAB_ENTRY
            r = _chay_so_do(core.TAB_ENTRY, ctx)
            if r:
                r["seq"] = len(nhat_ky)
                nhat_ky.append(r)
            if tien_do and i5 % 2000 == 0:
                tien_do(i5, len(ct.nen5))

    # Lệnh còn sống lúc hết dữ liệu: đóng theo giá đóng nến cuối, ghi rõ lý do, và tách
    # riêng trong thống kê (core.md §12.13).
    cuoi = float(ct.nen1["c"][-1])
    for l in list(so.dang_song()):
        so.dong(l, cuoi if l.da_khop else None, ctx.i,
                "het_du_lieu" if l.da_khop else "huy")
        ghi_tien(l)

    tk, duong_von = _thong_ke(so, cd, ct)
    tk["nen_mo_ho"] = mo_ho
    tk["so_luot"] = len(nhat_ky)
    kq = KetQua(ct, so, nhat_ky, ct._cot, tk)
    kq.duong_von = duong_von
    kq.cot_vung = cot_vung
    kq.vung_id = vung_id
    kq.so_vung = so_vung
    return kq


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

    # ĐỌC CỘT, không hỏi lại `so.vung_hien_hanh()`: sổ đang ở trạng thái CUỐI backtest,
    # nên hỏi lại là ở con trỏ nào cũng ra cùng một đáp án — sai và im lặng.
    cv = kq.cot_vung
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
        ("Số vùng nén đã sinh", int(kq.so_vung[i]) if co else 0),
    )]

    gia = float(ct.nen1["c"][j])
    for l in song:
        ra["lenh"].append({
            "id": l.id, "huong": l.huong, "da_khop": bool(l.da_khop),
            "gia_vao": _js(l.gia_khop), "sl": _js(l.sl), "tp": _js(l.tp),
            "lai_R": _js(l.lai_R(gia)) if l.da_khop else None,
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


def _sl_lich_su(kq, l):
    """Đường đi của SL theo thời gian: `[[t, sl], …]`.

    Nguồn là chính NHẬT KÝ, không phải suy đoán — nên chart vẽ ra đúng cái bậc thang mà
    `Dời SL về hoà vốn` tạo ra, đúng nến nó xảy ra. Đó là khoảnh khắc người dùng muốn
    kiểm chứng nhất, mà bản trước chỉ vẽ SL cuối cùng nên nó tàng hình."""
    if l.sl is None:
        return []
    ra, cuoi = [], None
    for t, s, _ in _moc_muc(kq).get(l.id) or []:
        if s is None or s == cuoi:
            continue
        ra.append([t, float(s)])
        cuoi = s
    return ra or [[int(kq.nen5["t"][l.nen_dat]), float(l.sl)]]


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
        "lai_R": _js((gia - l.gia_khop) * (1.0 if l.huong == sl.MUA else -1.0) / l.R)
        if (khop and l.R) else None,
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
