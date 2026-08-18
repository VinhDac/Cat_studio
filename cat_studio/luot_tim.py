"""MỘT LƯỢT TÌM — bắt đầu · dừng · hỏi tiến độ · lấy kết quả.

    core.md §18.6.2, §18.8

⭐ **MÁY TÌM KHÔNG SỐNG TRONG CỬA SỔ.** Một lượt chạy mất cả đêm (§18.4); đóng cửa sổ RL
để mở một sơ đồ ra ngắm mà giết luôn sáu tiếng đã chạy là hỏng. Cửa sổ chỉ là **cái để
nhìn** — nó hỏi `trang_thai()`, không giữ lượt chạy.

Vì thế **sổ lượt chạy nằm ở mức MODULE**, không nằm trên `Api`. `Api` bị dựng lại mỗi lần
mở cửa sổ; module thì sống theo tiến trình. Đây chính là món nợ §14.4 (*"đóng cửa sổ Live
là dừng phiên"*) — chỗ này làm đúng ngay từ đầu vì cái giá cao hơn hẳn.

⚠ **Một luồng, chưa song song.** Đúng một luồng nền cho mỗi lượt, nên hôm nay là một
nhân. §18.4 đo được 8 nhân cho ~10.000 sơ đồ một đêm — nhân lên 8 lần là một việc RIÊNG
(tiến trình con, không phải luồng: `bo_chay` là Python thuần nên GIL chặn). Chưa làm vì
chưa chạy thật lần nào; xem `notes.md`.
"""
import threading
import time
import uuid

from . import tim_kiem

#: Giữ tối đa ngần này lượt trong sổ. Lượt XONG cũ nhất bị dọn trước; lượt đang chạy
#: không bao giờ bị dọn — dọn mất một lượt đang chạy là mất luôn cách dừng nó.
GIU_LUOT = 20

_SO = {}
_KHOA = threading.Lock()


class LuotTim:
    """Một lượt tìm đang (hoặc đã) chạy. Giao diện chỉ ĐỌC, không bao giờ ghi."""

    __slots__ = ("ma", "ten", "_tt", "_kq", "_xin_dung", "_khoa", "_luong", "_duong",
                 "_dau_bang", "_t0_cham", "cua", "cau_hinh", "nhan_dung",
                 "_moc", "_duong_qua")

    def __init__(self, ten):
        self.ma = "L-" + uuid.uuid4().hex[:8]
        self.ten = ten
        self._kq = None
        #: CỬA lượt này chạy với. Giữ lại vì ĐOẠN KHOÁ phải chấm bằng ĐÚNG bộ cửa ấy:
        #: chọn trên train bằng một thước rồi nghiệm thu bằng thước khác thì hai con số
        #: không so được với nhau, và cái chênh lệch đọc ra sẽ là chênh của cái THƯỚC
        #: chứ không phải của sơ đồ.
        self.cua = None
        #: ẢNH CHỤP TOÀN BỘ cấu hình lượt này chạy với — nguyên văn cái đã gửi sang.
        #:
        #: ⭐ Không có nó thì sổ lượt chạy là một danh sách **không phân biệt được**:
        #: hai mươi dòng "Lượt 14:05" mà không dòng nào nói mình chạy với kho gì, cửa
        #: gì, trên khoảng nào. Một bàn điều khiển đẻ ra kết quả mà không ghi lại thứ
        #: đã đẻ ra chúng thì mấy con số ấy không dùng để so được.
        #:
        #: Và nó là thứ khiến `chạy lại y hệt` thành THẬT: chạy lại từ ảnh chụp này,
        #: không phải từ trạng thái giao diện lúc này — trạng thái ấy đã trôi đi rồi.
        self.cau_hinh = {}
        #: Số nhân MUỐN DÙNG lúc này — giao diện kéo thanh là đổi ngay ô này, và
        #: `tim_kiem.tim` hỏi lại mỗi lượt. Xem `tim(..., so_nhan_dung=)`.
        self.nhan_dung = None
        #: Mốc `(đã chấm, giây)` lấy thưa — để ước "còn bao lâu" thành một KHOẢNG.
        #:
        #: ⭐ Một con số duy nhất là con số giả chính xác: chi phí mỗi sơ đồ chênh nhau
        #: tới 1.000 lần (0,1 s → 134 s). Hai mốc — nhịp CẢ LƯỢT và nhịp GẦN ĐÂY — cho
        #: một khoảng, và khoảng ấy tự thu hẹp khi máy chạy lâu hơn.
        self._moc = []
        self._xin_dung = False
        self._khoa = threading.Lock()
        self._luong = None
        #: ĐƯỜNG ĐIỂM TỐT NHẤT — `[[đã chấm, điểm], …]`, chỉ ghi khi điểm ĐỔI.
        #:
        #: ⭐ Nó trả lời đúng một câu, và là câu thực dụng nhất của cả bàn điều khiển:
        #: *"còn tìm được gì nữa không — dừng được chưa"*. Đường phẳng vài nghìn lượt
        #: là tín hiệu tắt máy, khỏi đốt cả đêm.
        #:
        #: Ghi khi ĐỔI chứ không mỗi lượt: điểm tốt nhất chỉ tăng, nên đây là một hàm
        #: bậc thang — mọi điểm ở giữa hai bậc đều suy ra được. 10.000 lượt thường chỉ
        #: đẻ ra vài chục bậc, tức vài trăm byte thay vì vài trăm KB qua cầu nối.
        self._duong = []
        #: NHÓM ĐẦU BẢNG hiện tại — cập nhật mỗi lượt, KHÔNG đợi chạy xong.
        #:
        #: ⭐ Đây là chỗ khiến bàn điều khiển sống: chạy tám tiếng thì tám tiếng nhìn
        #: thấy kết quả lớn dần, và mở được sơ đồ ra xem ngay giữa chừng. Trước đây
        #: `tom_tat` đòi `_kq` — thứ chỉ có KHI XONG — nên bảng rỗng suốt lượt chạy.
        #:
        #: `tim_kiem` gán một list MỚI mỗi lần nên đọc từ luồng khác an toàn.
        self._dau_bang = []
        #: Mốc lượt CHẤM đầu tiên — để tính "còn bao lâu". Cố ý không dùng `bat_dau`:
        #: khoảng giữa hai mốc ấy là lúc TẢI NẾN, có thể hàng phút, và tính nó vào thì
        #: ước lượng đầu lượt sai lệch rất nặng.
        self._t0_cham = None
        # ⚠ `nhan` tính MỘT LẦN lúc bắt đầu, không mỗi nhịp: giao diện hỏi trạng thái
        # 500 ms một lần, mà cấu hình thì đứng yên suốt lượt.
        #: ĐƯỜNG "QUA CỬA" — `[[đã chấm, số qua cửa cộng dồn], …]`, chỉ ghi khi ĐỔI.
        #:
        #: ⭐ Thay cho đường "điểm tốt nhất" của bản cũ. Cùng là hàm bậc thang, nhưng nó
        #: trả lời đúng câu *"còn tìm được gì nữa không"* mà KHÔNG dựa vào một con số đã
        #: đo được là nhiễu — 6/8 cái đầu bảng chỉ ăn may một đoạn (§18.5f).
        self._duong_qua = []
        self._tt = {"ma": self.ma, "ten": ten, "nhan": "", "dang_chay": True,
                    "da_chay": 0,
                    "tong": 0, "diem_tot_nhat": None, "bat_dau": time.time(),
                    "xong_luc": None, "loi": None, "dung_giua_chung": False,
                    "thong_ke": None}

    # ---- giao diện đọc ----
    def trang_thai(self):
        """Ảnh chụp tiến trình. Trả BẢN SAO — giao diện cầm bản gốc là cầm thứ luồng
        nền đang ghi vào.

        ⚠ `duong` cũng phải chép: `dict()` chỉ sao chép NÔNG, nên để nguyên là giao
        diện cầm đúng cái list luồng nền đang `append` vào giữa lúc nó đang duyệt."""
        with self._khoa:
            return {**self._tt, "duong": list(self._duong),
                    "duong_qua": list(self._duong_qua),
                    "nhan_dung": self.nhan_dung}

    def ket_qua(self):
        """`KetQuaTim` khi đã xong, `None` khi còn chạy."""
        return self._kq

    def tom_tat(self, so_luong=10):
        """Nhóm đầu bảng, dạng JSON thuần — không kèm `KetQua` nào (nặng).

        Đọc `_dau_bang` chứ KHÔNG đọc `_kq`: `_kq` chỉ có khi chạy xong, mà bàn điều
        khiển phải thấy kết quả lớn dần ngay trong lúc chạy."""
        return [{"hang": k, "diem": d["diem"], "so_lenh": d["so_lenh"],
                 "ten": self._ten(k),
                 "sut_von_pt": d["sut_von_pt"], "lai_pt": d["lai_pt"],
                 # ⭐ TRẢ CẢ HAI KỲ. Người dùng nói từ đầu là quan tâm cả tuần lẫn
                 # tháng; `cham` đã tính sẵn cả hai nên giấu một cái đi là phí. Cột
                 # nào dùng để chấm thì bảng tự đánh dấu.
                 "tuan": d["tuan"], "thang": d["thang"], "ky": d["ky"],
                 # ⭐ Hai con số ĐÁNG ĐỌC hơn cả `diem`: điểm gộp đã đo được là biết
                 # nói dối (§18.5f), còn "dương n/m" thì không.
                 "cua_so_duong": d.get("cua_so_duong"),
                 "so_cua_so": d.get("so_cua_so"),
                 "cua_so": d.get("cua_so"),
                 "so_nuoc": len(chuoi)}
                for k, (doc, chuoi, d) in enumerate(self._dau_bang[:so_luong], 1)]

    def _ten(self, hang):
        """Tên của sơ đồ hạng `hang` — CÓ HẠNG và CÓ MÃ LƯỢT.

        ⚠ Trước đây mọi sơ đồ máy đẻ ra đều tên đúng một chữ `"Máy vẽ"`. Mở ba cái liên
        tiếp thì cửa sổ vẽ hiện cùng một cái tên trên thanh tiêu đề, và nó trông y hệt
        MỘT sơ đồ bị vặn lại số — đúng thứ khiến người dùng tưởng máy đang sửa file của
        mình. Một cái tên không phân biệt được là một lời nói dối rẻ tiền."""
        return f"Máy vẽ #{hang} · {self.ma}"

    def so_do(self, hang):
        """Tài liệu chiến lược của cái xếp hạng `hang` (1 là đầu bảng).

        ⭐ Trả về một file chiến lược BÌNH THƯỜNG (§18.6.5) — cùng JSON, mở bằng cùng
        cửa sổ vẽ, chạy bằng cùng Tester. Và mở được NGAY GIỮA CHỪNG, không đợi xong."""
        ds = self._dau_bang
        if not 1 <= hang <= len(ds):
            return None
        # Đặt tên lúc ĐƯA RA, không lúc sinh: lúc sinh chưa biết hạng, mà hạng là thứ
        # người dùng đang nhìn trên bảng. Chép nông là đủ — chỉ đổi đúng một khoá.
        return {**ds[hang - 1][0], "name": self._ten(hang)}

    # ---- điều khiển ----
    def dung(self):
        """Xin dừng. Lượt đang chấm một sơ đồ thì chấm nốt rồi mới ngừng — cắt ngang
        giữa một backtest là để lại một bảng số nửa vời.

        ⚠ Và NÓI RA chuyện đó. Một sơ đồ bệnh có thể chấm mất hàng phút; không nói thì
        người dùng bấm Dừng rồi ngồi nhìn nút không phản ứng, tưởng hỏng."""
        self._xin_dung = True
        self._ghi(chu="đang dừng — chấm nốt sơ đồ dở")

    def dang_chay(self):
        return bool(self._luong and self._luong.is_alive())

    # ---- luồng nền ----
    def _ghi(self, **kw):
        with self._khoa:
            self._tt.update(kw)

    def _nhip(self, da, tong, qua, tk=None):
        """Một lượt vừa chấm xong. Chạy trên LUỒNG NỀN — chỉ đụng thứ có khoá."""
        tot = qua[0][2]["diem"] if qua else None
        self._dau_bang = qua                  # gán nguyên: list MỚI, xem `tim_kiem`
        if self._t0_cham is None:
            self._t0_cham = time.time()
        with self._khoa:
            if tot is not None and (not self._duong or self._duong[-1][1] != tot):
                self._duong.append([da, tot])
            q = (tk or {}).get("qua_cong_don")
            if q is not None and (not self._duong_qua or self._duong_qua[-1][1] != q):
                self._duong_qua.append([da, q])
        # CÒN BAO LÂU — đo thật trên chính lô đang chạy. Không ước bằng số nến: đo được
        # cùng số nến mà sơ đồ này 3 giây, sơ đồ kia 24 giây (§18.4), vì chi phí đi theo
        # SỐ LỆNH sơ đồ đẻ ra chứ không theo số nến.
        troi = max(time.time() - self._t0_cham, 1e-6)
        moi = troi / max(da, 1)
        con = max(tong - da, 0)
        with self._khoa:
            if not self._moc or da - self._moc[-1][0] >= max(1, tong // 200):
                self._moc.append((da, troi))
            # NHỊP GẦN ĐÂY — lấy trên đoạn 25% cuối, để cái khoảng phản ánh cả việc máy
            # đang chạy nhanh dần (lô toàn sơ đồ rác) hay chậm dần.
            k = max(0, len(self._moc) - max(2, len(self._moc) // 4))
            d0, t0 = self._moc[k]
            gan = ((troi - t0) / (da - d0)) if da > d0 else moi
        lo, hi = sorted((moi, gan))
        self._ghi(da_chay=da, tong=tong, diem_tot_nhat=tot,
                  giay_moi_luot=round(moi, 3),
                  giay_gan_day=round(gan, 3),
                  con_lai=round(moi * con),
                  con_lai_som=round(lo * con), con_lai_muon=round(hi * con),
                  # ⚠ Dưới ngần này mẫu thì KHÔNG hiện gì — độ chắc của ước lượng tăng
                  # theo √N, và một con số ở lượt thứ ba là bịa.
                  du_de_uoc=da >= 30,
                  qua_cong_don=(tk or {}).get("qua_cong_don", 0),
                  thong_ke=tk or self._tt.get("thong_ke"))

    def _chay(self, nen, cd, so_luot, **kw):
        self.cua = kw.get("cua")
        try:
            kq = tim_kiem.tim(
                nen, cd, so_luot, tien_do=self._nhip,
                dung=lambda: self._xin_dung, **kw)
            self._kq = kq
            self._ghi(thong_ke=kq.thong_ke, dung_giua_chung=self._xin_dung, chu="")
        except Exception as e:                    # noqa: BLE001
            # ⚠ NỔ THÌ NÓI TO. Luồng nền chết im lặng là cửa sổ quay mãi thanh tiến
            # trình mà không ai hiểu vì sao — đúng loại hỏng lặng cả app này cấm.
            self._ghi(loi=f"{type(e).__name__}: {e}")
        finally:
            self._ghi(dang_chay=False, xong_luc=time.time())


def bat_dau(nen, cd, so_luot, ten="Lượt tìm", **kw):
    """Mở một lượt tìm trên LUỒNG NỀN và trả về ngay.

    `kw` chuyển thẳng cho `tim_kiem.tim` (`hat`, `cua`, `tran`, `giu`)."""
    l = LuotTim(ten)
    l._ghi(tong=so_luot)
    l._luong = threading.Thread(target=l._chay, args=(nen, cd, so_luot),
                                kwargs=kw, daemon=True)
    _ghi_so(l)
    l._luong.start()
    return l


def lay(ma):
    with _KHOA:
        return _SO.get(ma)


def danh_sach():
    """Mọi lượt trong sổ, mới nhất trước."""
    with _KHOA:
        ds = list(_SO.values())
    return [l.trang_thai() for l in sorted(ds, key=lambda x: -x._tt["bat_dau"])]


def xoa(ma):
    """Bỏ một lượt ĐÃ XONG khỏi sổ. Lượt đang chạy thì không — phải `dung()` trước."""
    with _KHOA:
        l = _SO.get(ma)
        if l is None or l.dang_chay():
            return False
        del _SO[ma]
        return True


def _ghi_so(l):
    with _KHOA:
        _SO[l.ma] = l
        if len(_SO) <= GIU_LUOT:
            return
        # Dọn lượt XONG cũ nhất. Không đụng lượt đang chạy: dọn nó là mất luôn cách
        # dừng nó, và luồng vẫn chạy tiếp — một lượt chạy MA, không ai gọi lại được.
        cu = sorted((x for x in _SO.values() if not x.dang_chay()),
                    key=lambda x: x._tt["bat_dau"])
        for x in cu[:len(_SO) - GIU_LUOT]:
            del _SO[x.ma]
