"""VÒI CẤP NẾN cho Live — kéo nến M1 từ sàn rồi đẩy qua đúng bộ chạy của backtest.

VÌ SAO FILE NÀY NGẮN
--------------------
Vì nó cố ý không chứa luật giao dịch nào. Mọi quyết định vẫn nằm ở
`bo_chay.PhienChay.mot_nhip` — đúng cái hàm mà backtest gọi trong vòng lặp. File này
chỉ làm một việc: **biến "sàn vừa đóng một nến M1" thành một lời gọi `mot_nhip`.**

Đó là cả điểm của lần tách bộ chạy: backtest và live đi qua ĐÚNG MỘT ĐOẠN CODE, nên
"test như nào thì live như thế" là chuyện của kiến trúc chứ không phải của kỷ luật.

NHỊP
----
    sức khoẻ kết nối   1 giây     (ket_noi.SucKhoe — không ở đây)
    quyết định         mỗi nến M1 ĐÓNG → Manage; mỗi nến M5 đóng → Entry
    khớp lệnh, SL/TP   thời gian thực, do SÀN làm — ta chỉ đọc kết quả

Không chạy theo tick, vì bộ chạy đọc `close`/`ATR` của nến ĐÃ ĐÓNG. Chạy theo tick là
đọc nến đang hình thành, giá trị nhảy liên tục, và live sẽ khác backtest — đúng thứ
đang cố tránh. Bản gốc MQL5 cũng quyết định ở biên nến (`if(!IsNewBar(...)) return;`).
"""
from __future__ import annotations

import time

from . import bo_chay
from . import nguon_nen as nn

try:
    import MetaTrader5 as mt5
except Exception:                               # noqa: BLE001
    mt5 = None


#: Số nến M1 kéo về lúc mở. Phải đủ để chỉ báo ấm máy VÀ để engine dựng lại được trạng
#: thái vùng nén: MA(50) trên M15 cần 750 nến M1, cộng lịch sử vùng nén → 5 ngày cho
#: thoải mái. Kéo một lần lúc mở, sau đó mỗi phút chỉ thêm một cây.
SO_NEN_NAP = 7200


class PhienLive:
    """Một phiên live: nến vào, `mot_nhip` chạy, ảnh chụp ra.

    ⚠ KHÔNG sống trong cửa sổ. Đóng cửa sổ Live không được dừng phiên — cửa sổ chỉ là
    cái để nhìn. Vì thế lớp này không biết gì về giao diện.
    """

    def __init__(self, doc, symbol, cd):
        # ⚠ `cd` BẮT BUỘC. Trước đây là `cd or CaiDat(symbol=symbol)`, tức một phiên
        # LIVE có thể chạy bằng point/spread giả. Live sai im lặng là thứ tệ nhất trong
        # cả app này — §16.3.
        self.doc = doc
        self.symbol = symbol
        self.cd = cd
        self.phien = None
        self.nen1 = None
        self.t_cuoi = 0          # thời điểm nến M1 cuối ĐÃ xử lý
        #: Mốc bắt đầu PHIÊN. Mọi thứ trước nó là chạy trên lịch sử để dựng lại trạng
        #: thái — MÔ PHỎNG, không phải việc đã xảy ra ở sàn. Không được hiện ra như kết
        #: quả live: trộn hai thứ đó là nói dối đúng chỗ người ta cần tin nhất.
        self.t_bat_dau = None
        #: Chỉ số nến LÀ KHUNG HÌNH ĐẦU của cuộn phim. Trước nó chỉ dùng để TÍNH CHỈ BÁO.
        self.j_bat_dau = 0
        self.loi = ""
        self.nap_luc = None

    # ------------------------------------------------------------------ nạp lần đầu
    def nap(self):
        """Nạp nến quá khứ để CHỈ BÁO có cái mà tính — rồi bắt đầu quay từ đây.

        ⚠ HAI THỨ KHÁC HẲN NHAU, đừng gộp:

          • **Chỉ báo cần lịch sử.** ATR(14) M5 cần 14 nến đã đóng, MA(50) M15 cần 12,5
            giờ. Đọc nến cũ để TÍNH RA con số không phải là "chiến lược đã chạy" — đó là
            mở mắt ở khung hình đầu tiên. Nên `ChuongTrinh` vẫn dựng trên cả mảng.

          • **Trạng thái chiến lược thì KHÔNG.** Vùng nén đang đếm, cờ "vùng này đã sinh
            lệnh", sổ lệnh — bắt đầu từ số 0 lúc bấm Live.

        Bản trước chạy `mot_nhip` qua cả 7.200 nến quá khứ, đẻ ra 208 dòng nhật ký và
        mấy lệnh MÔ PHỎNG rồi bày lên như chuyện đã xảy ra ở sàn. Sai bản chất: test là
        bộ phim đã quay xong, live là máy quay vừa bấm nút.

        Và đây cũng đúng bản gốc: `FilterEngine::Initialize` của D_02 đặt
        `m_comp_bar_count = 0`, `state = COMP_IDLE` — gắn EA vào chart là nó bắt đầu
        trống rỗng, phải chờ một cú nén MỚI."""
        a = self._keo(SO_NEN_NAP)
        if a is None or not len(a):
            return False
        self.nen1 = a
        self.j_bat_dau = len(a) - 1
        self.phien = bo_chay.PhienChay(self.doc, a, self.cd)
        self.phien.mot_nhip(self.j_bat_dau)     # khung hình SỐ 0 của cuộn phim
        self.t_cuoi = int(a["t"][-1])
        self.t_bat_dau = self.t_cuoi
        self.nap_luc = time.time()
        return True

    # ------------------------------------------------------------------ mỗi nhịp
    def nhip(self):
        """Có nến M1 nào vừa đóng thì chạy nó. Trả số nến vừa xử lý.

        ⚠ Chạy MỌI nến còn thiếu chứ không chỉ nến mới nhất. App bận, máy ngủ, mạng rớt
        — bỏ nến là bỏ luôn quyết định của những phút đó, và trạng thái vùng nén lệch
        hẳn so với backtest. `mot_nhip` chịu được gọi ngắt quãng; bài kiểm ở
        `test_bo_chay.py` giữ đúng điều đó."""
        if self.phien is None:
            return 0
        a = self._keo(600)                      # 10 phút gần nhất là thừa đủ để bắt kịp
        if a is None or not len(a):
            return 0
        moi = a[a["t"] > self.t_cuoi]
        if not len(moi):
            return 0
        # Nối vào mảng cũ rồi DỰNG LẠI `ChuongTrinh` trên mảng dài hơn: chỉ báo tính lại
        # bằng ĐÚNG phép của backtest, không có bản "tính dần" thứ hai để lệch.
        import numpy as np
        nen_moi = np.concatenate([self.nen1, moi])
        # Dựng lại `ChuongTrinh` trên mảng dài hơn để chỉ báo tính bằng ĐÚNG phép của
        # backtest, rồi chạy lại TỪ KHUNG HÌNH SỐ 0 — không phải từ đầu mảng. Trạng thái
        # live là hàm thuần của (sơ đồ, nến từ lúc bấm Live), nên dựng lại ra đúng cái cũ.
        #
        # ⚠ DỰNG VÀO BIẾN CỤC BỘ RỒI MỚI CÔNG BỐ. Bản trước gán thẳng `self.phien` rồi
        # mới phát lại — tức trong suốt lúc phát lại, `self.phien` là một phiên RỖNG.
        # Luồng cầu nối gọi `anh_chup()` đúng lúc đó thì đọc được nhật ký 0 dòng, lệnh
        # 0 cái, và cửa sổ chớp trắng một nhịp. Đo được: giữa `nhip()` thấy 0/0 trong
        # khi trước và sau đều là 19/17. Gán MỘT PHÁT ở cuối thì không có khe nào.
        phien_moi = bo_chay.PhienChay(self.doc, nen_moi, self.cd)
        for j in range(self.j_bat_dau, len(nen_moi)):
            phien_moi.mot_nhip(j)
        self.nen1, self.phien = nen_moi, phien_moi
        self.t_cuoi = int(nen_moi["t"][-1])
        return len(moi)

    def anh_chup(self):
        return self.phien.anh_chup() if self.phien else None

    # ------------------------------------------------------------------ kéo nến
    def _keo(self, so):
        if mt5 is None or not nn.CO_MT5:
            self.loi = "Máy chưa cài thư viện MetaTrader5."
            return None
        try:
            with nn._KetNoi():
                r = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, int(so))
            if r is None or not len(r):
                self.loi = "Sàn không trả nến nào."
                return None
            # ⚠ BỎ cây cuối: `copy_rates_from_pos` trả cả nến ĐANG HÌNH THÀNH. Đưa nó
            # vào bộ chạy là quyết định trên một cây nến chưa đóng — giá trị còn nhảy,
            # và backtest không bao giờ làm thế.
            r = r[:-1]
            if not len(r):
                return None
            # DÙNG CHUNG phép đổi của `nguon_nen`, không chép lại: bản chép cũ ở
            # đây giống nó từng byte, mà hai nơi cùng dựng một mảng nến thì sớm muộn
            # một nơi quên cột. (Nhánh `hasattr(nn, "tu_mt5")` cũ là nhánh chết vĩnh
            # viễn — `tu_mt5` chưa từng tồn tại trong repo.)
            return nn._sang_dtype(r)
        except Exception as e:                  # noqa: BLE001
            self.loi = f"{type(e).__name__}: {e}"
            return None



