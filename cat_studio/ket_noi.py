"""SỨC KHOẺ KẾT NỐI tới sàn — thứ quan trọng nhất khi chạy live.

VÌ SAO CÓ FILE RIÊNG
--------------------
Backtest hỏng thì ra một con số sai và ta nhìn thấy. Live hỏng thì thường KHÔNG ra gì
cả — nó im lặng. Ba kiểu chết im lặng đã biết, và cả ba đều không hiện ra ở chỗ nào
khác trong app:

  1. **Terminal báo "connected" mà feed đứng.** `terminal_info().connected` vẫn True
     trong khi tick cuối đã 40 phút không đổi. Nhìn chart thì thấy nến đứng yên và cứ
     tưởng thị trường lặng.
  2. **Nút AlgoTrading tắt.** Mọi lệnh gửi đi đều bị từ chối, mà lý do nằm trong một
     retcode chứ không nằm trên màn hình.
  3. **Spread live khác xa spread đã backtest.** Kết nối tốt, lệnh gửi được, nhưng chiến
     lược đang chạy trong một thế giới khác cái đã thử. Đây là kiểu chết đắt nhất vì
     không có gì báo động cả.

Nên module này KHÔNG đo "có nối được không" (câu đó `nguon_nen.kiem_ket_noi` trả rồi).
Nó đo **có TIN được không**.

LUẬT: không hàm nào ở đây được phép ném. Mọi hỏng hóc là một câu trả lời có ích.
"""
from __future__ import annotations

import json
import os
import statistics
import time
from collections import deque

from . import gui_lenh
from . import nguon_nen as nn

try:
    import MetaTrader5 as mt5
except Exception:                               # noqa: BLE001
    mt5 = None


#: Tick cũ hơn ngần này giây thì coi là feed đã đứng, dù terminal nói gì đi nữa.
TICK_QUA_HAN = 90.0

#: Giữ ngần này lần đo độ trễ gần nhất. 60 lần ~ một phút nếu nhịp đo là một giây.
SO_LAN_DO = 60


#: Hồ sơ kết nối — CACHE, không phải cài đặt.
#:
#: Khác nhau ở chỗ: cài đặt là thứ người dùng gõ vào, hồ sơ là thứ ĐO ĐƯỢC từ sàn. Mất
#: file này không hỏng gì cả, chỉ là phải chạy lại bài test — nên nó nằm riêng, xoá
#: thoải mái, và không bao giờ trộn vào `cai_dat.json`.
#:
#: Khoá theo **sàn + symbol**, KHÔNG theo server. Demo và thật của cùng một sàn là hai
#: server khác nhau (`Exness-MT5Trial7` vs server thật) — khoá theo server thì hiệu
#: chuẩn trên demo không bao giờ áp được cho tài khoản thật, tức cả luồng "test trên
#: demo rồi sang thật" chết ngay ở bước cuối.
FILE_HO_SO = "ho_so_ket_noi.json"


def _khoa(san, symbol):
    return f"{(san or '?').strip()}|{(symbol or '?').strip().upper()}"


def _duong():
    from . import luu_tru
    return os.path.join(luu_tru.goc(), FILE_HO_SO)


def _doc_tat_ca():
    try:
        with open(_duong(), encoding="utf-8") as f:
            tat_ca = json.load(f)
        return tat_ca if isinstance(tat_ca, dict) else {}
    except Exception:                           # noqa: BLE001
        return {}


def doc_ho_so(san, symbol):
    """Hồ sơ đã đo cho sàn+symbol này, hoặc None. KHÔNG BAO GIỜ ném."""
    return _doc_tat_ca().get(_khoa(san, symbol))


def ghi_ho_so(san, symbol, du_lieu):
    """Ghi đè hồ sơ của sàn+symbol này, giữ nguyên hồ sơ của sàn khác."""
    from . import luu_tru
    tat_ca = _doc_tat_ca()
    tat_ca[_khoa(san, symbol)] = du_lieu
    luu_tru.ghi_json_nguyen_tu(_duong(), tat_ca)
    return du_lieu


def ho_so_khac(san, symbol):
    """Hồ sơ đã đo cho CÙNG symbol nhưng dưới tên sàn khác.

    ⚠ Sinh ra từ một cái bẫy im lặng: hồ sơ khoá theo `account_info().company`, mà một
    sàn có thể có nhiều pháp nhân — demo báo một chuỗi, tài khoản thật báo chuỗi khác.
    Khi đó live KHÔNG tìm thấy hồ sơ và lặng lẽ rơi về số mặc định đang đoán, không có
    gì báo. Hàm này để hỏi thẳng: *"chưa có hồ sơ cho sàn này — dùng cái đã đo ở kia?"*
    """
    ra = []
    khoa_minh = _khoa(san, symbol)
    duoi = (symbol or "").strip().upper()
    for k, v in _doc_tat_ca().items():
        if k == khoa_minh or not isinstance(v, dict):
            continue
        if not k.upper().endswith("|" + duoi):
            continue
        ra.append({"khoa": k, "san": k.rsplit("|", 1)[0],
                   "server": v.get("server", ""), "do_luc": v.get("do_luc"),
                   "so_vong": v.get("so_vong"),
                   "trang_thai": v.get("trang_thai")})
    ra.sort(key=lambda x: x.get("do_luc") or "", reverse=True)
    return ra


def chep_ho_so(tu_khoa, san, symbol):
    """Chép hồ sơ từ một sàn khác sang sàn đang chạy — CÓ ĐỂ LẠI VẾT.

    Giữ nguyên `do_luc` gốc và ghi thêm `chep_tu`: bộ số này không phải đo ở đây, và
    khối Đề phòng phải nói ra điều đó. Xoá vết là biến một bản sao thành một phép đo
    giả — đúng kiểu lệch âm thầm mà cả tầng này sinh ra để chống."""
    goc = _doc_tat_ca().get(tu_khoa)
    if not isinstance(goc, dict):
        return None
    moi = dict(goc)
    moi["chep_tu"] = tu_khoa
    moi["chep_luc"] = time.strftime("%Y-%m-%d %H:%M")
    return ghi_ho_so(san, symbol, moi)


def _tk_that(tk):
    """Tài khoản THẬT hay demo. `trade_mode`: 0 = demo, 1 = contest, 2 = real."""
    return bool(tk) and int(getattr(tk, "trade_mode", 0)) == 2


def thong_so_tinh(symbol):
    """Luật của sàn ĐỌC ĐƯỢC NGAY, không phải đặt lệnh nào.

    Tách hẳn khỏi phần phải-đặt-lệnh vì hai thứ khác nhau về giá phải trả: cái này đọc
    được trên MỌI tài khoản kể cả tài khoản thật, nên luôn kiểm mỗi lần mở Live. Cái kia
    cần demo.

    Bốn con số dưới đây là bốn cách một chiến lược chạy tốt trong backtest hỏng ngay
    ngày đầu live, mà không cái nào hiện ra ở chỗ khác."""
    ra = {"netting": None, "stops_level": None, "freeze_level": None,
          "lot_min": None, "lot_max": None, "lot_buoc": None,
          "filling_khai": None, "chu": ""}
    if mt5 is None or not nn.CO_MT5:
        ra["chu"] = "Máy chưa cài thư viện MetaTrader5."
        return ra
    try:
        with nn._KetNoi():
            tk = mt5.account_info()
            if tk is not None:
                # ⚠ NETTING là cái lớn nhất. D_02 dựa hẳn vào nhiều lệnh sống song song
                # ("pending can coexist with running position"). Tài khoản netting thì
                # hai lệnh mua CỘNG LẠI thành một vị thế — chiến lược chạy ra kết quả
                # khác backtest mà không có gì báo. ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2.
                ra["netting"] = int(getattr(tk, "margin_mode", 2)) != 2
            si = mt5.symbol_info(symbol)
            if si is None:
                mt5.symbol_select(symbol, True)
                si = mt5.symbol_info(symbol)
            if si is None:
                ra["chu"] = f'Sàn không có symbol "{symbol}".'
                return ra
            # SL/TP gần giá hơn `stops_level` điểm là sàn TỪ CHỐI. D_02 tính SL theo ATR,
            # lúc nén chặt thì SL rất sát — đây là chỗ sẽ hỏng đầu tiên khi live.
            ra["stops_level"] = int(getattr(si, "trade_stops_level", 0))
            ra["freeze_level"] = int(getattr(si, "trade_freeze_level", 0))
            ra["lot_min"] = float(getattr(si, "volume_min", 0))
            ra["lot_max"] = float(getattr(si, "volume_max", 0))
            ra["lot_buoc"] = float(getattr(si, "volume_step", 0))
            ra["filling_khai"] = int(getattr(si, "filling_mode", 0))
            ra["chu"] = "OK"
    except Exception as e:                      # noqa: BLE001
        ra["chu"] = f"{type(e).__name__}: {e}"
    return ra


class SucKhoe:
    """Theo dõi kết nối theo thời gian. Một thể hiện cho một phiên live.

    Giữ LỊCH SỬ chứ không chỉ ảnh chụp: "đang nối được" là câu vô nghĩa nếu trong ba
    giờ qua nó rớt bốn lần. Cái quyết định có dám để máy chạy qua đêm là con số rớt,
    không phải cái đèn xanh lúc này.
    """

    def __init__(self, symbol, spread_test_diem=None):
        self.symbol = symbol
        #: Spread (điểm) mà backtest đã dùng — để so với spread thật. `None` = chưa biết.
        self.spread_test_diem = spread_test_diem
        self.tre = deque(maxlen=SO_LAN_DO)      # ms mỗi lần đo
        self.so_lan_rot = 0
        self.rot_luc = None                     # mốc bắt đầu lần mất kết nối đang diễn ra
        self.tong_giay_rot = 0.0
        self.dang_noi = None                    # None = chưa đo lần nào
        self.bat_dau = time.time()
        self.loi_cuoi = ""

    # ------------------------------------------------------------------ đo một nhịp
    def do(self):
        """Một nhịp đo. Trả bản tin đầy đủ. KHÔNG BAO GIỜ ném."""
        t0 = time.perf_counter()
        r = self._doc()
        r["tre_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)
        self.tre.append(r["tre_ms"])

        # Đếm rớt theo CẠNH XUỐNG, không đếm theo trạng thái: nối được suốt 3 giờ rồi
        # rớt một lần thì đó là MỘT lần rớt, không phải một nghìn lần đo thấy rớt.
        song = bool(r["nen_song"])
        if self.dang_noi is None:
            self.dang_noi = song
        elif song != self.dang_noi:
            if not song:
                self.so_lan_rot += 1
                self.rot_luc = time.time()
            elif self.rot_luc:
                self.tong_giay_rot += time.time() - self.rot_luc
                self.rot_luc = None
            self.dang_noi = song

        r.update(self.tom_tat())
        return r

    def tom_tat(self):
        dang_rot = self.rot_luc is not None
        return {
            "tre_p50": round(statistics.median(self.tre), 1) if self.tre else None,
            "tre_p95": (round(sorted(self.tre)[int(len(self.tre) * 0.95) - 1], 1)
                        if len(self.tre) >= 5 else None),
            "so_lan_rot": self.so_lan_rot,
            "giay_rot": round(self.tong_giay_rot
                              + (time.time() - self.rot_luc if dang_rot else 0.0), 1),
            "phien_giay": round(time.time() - self.bat_dau, 1),
        }

    # ------------------------------------------------------------------ đọc sàn
    def _doc(self):
        ra = {
            "noi_duoc": False, "nen_song": False, "chu": "",
            "tai_khoan": None, "server": "", "sàn": "", "la_that": None,
            "cho_giao_dich": False, "symbol_giao_dich_duoc": False,
            "tuoi_tick": None, "spread_diem": None, "spread_lech": None,
            "lech_gio": None,
            # Cây nến ĐANG HÌNH THÀNH. Chiến lược không bao giờ đọc nó (quyết định chỉ
            # trên nến đã đóng), nhưng CHART phải có — không thì trên M1 màn hình đứng
            # im tới 60 giây và trông như mất kết nối.
            "nen_dang": None,
        }
        if mt5 is None or not nn.CO_MT5:
            ra["chu"] = "Máy chưa cài thư viện MetaTrader5."
            return ra
        try:
            with nn._KetNoi():
                ra["noi_duoc"] = True
                tt = mt5.terminal_info()
                tk = mt5.account_info()
                if tk:
                    ra["tai_khoan"] = int(tk.login)
                    ra["server"] = str(tk.server)
                    ra["sàn"] = str(tk.company)
                    ra["la_that"] = _tk_that(tk)
                    # Hai cái cùng phải bật: terminal cho phép, VÀ tài khoản cho EA giao
                    # dịch. Thiếu một cái là lệnh bị từ chối, mà lý do nằm trong retcode.
                    ra["cho_giao_dich"] = bool(getattr(tt, "trade_allowed", False)) and \
                        bool(getattr(tk, "trade_expert", False))

                si = mt5.symbol_info(self.symbol)
                if si is None:
                    mt5.symbol_select(self.symbol, True)
                    si = mt5.symbol_info(self.symbol)
                if si is None:
                    ra["chu"] = f'Sàn không có symbol "{self.symbol}".'
                    return ra
                # SYMBOL_TRADE_MODE_FULL = 4. Nhiều sàn để vàng ở chế độ chỉ-đóng ngoài
                # giờ, hoặc chỉ-xem — nối tốt mà vẫn không đặt được lệnh nào.
                ra["symbol_giao_dich_duoc"] = int(getattr(si, "trade_mode", 0)) == 4

                tick = mt5.symbol_info_tick(self.symbol)
                if tick and tick.time:
                    # ⚠ ĐÂY là mạch đập thật. `terminal_info().connected` vẫn True khi
                    # feed đã đứng — chỉ tuổi của tick cuối mới nói ra điều đó.
                    ra["tuoi_tick"] = round(time.time() - int(tick.time), 1)
                    ra["nen_song"] = ra["tuoi_tick"] <= TICK_QUA_HAN
                    diem = float(getattr(si, "point", 0.0)) or 0.0
                    if diem and tick.ask and tick.bid:
                        ra["spread_diem"] = round((tick.ask - tick.bid) / diem, 1)
                        if self.spread_test_diem:
                            ra["spread_lech"] = round(
                                ra["spread_diem"] / float(self.spread_test_diem), 2)
                    # Giờ server lệch giờ máy bao nhiêu — nến M5 đóng theo giờ SERVER,
                    # nên lệch giờ là lệch cả nhịp quyết định.
                    ra["lech_gio"] = round((int(tick.time) - time.time()) / 60.0)
                    # Nhịp này vốn đã đọc tick — gửi kèm cây nến đang chạy thì chart
                    # sống theo từng giây mà KHÔNG tốn thêm một lời gọi nào.
                    try:
                        r1 = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M1, 0, 1)
                        if r1 is not None and len(r1):
                            x = r1[0]
                            ra["nen_dang"] = {
                                "t": int(x["time"]), "o": float(x["open"]),
                                "h": float(x["high"]), "l": float(x["low"]),
                                "c": float(x["close"])}
                    except Exception:           # noqa: BLE001
                        pass
                ra["chu"] = "OK" if ra["nen_song"] else "Feed đứng — tick cuối đã cũ."
        except Exception as e:                  # noqa: BLE001
            self.loi_cuoi = f"{type(e).__name__}: {e}"
            ra["chu"] = self.loi_cuoi
        return ra

    # ------------------------------------------------------------------ vấn đề
    def van_de(self, tin):
        """Bản tin → danh sách VẤN ĐỀ, cùng hình dạng với bảng Vấn đề của cửa sổ vẽ.

        Mỗi dòng phải hành động được. "Kết nối kém" là vô dụng; "AlgoTrading đang tắt —
        bấm nút đó trên MT5" thì làm được ngay."""
        ra = []

        def them(muc, chu):
            ra.append({"severity": muc, "message": chu, "tab": "live"})

        if not tin["noi_duoc"]:
            them("error", tin["chu"] or "Không nối được MetaTrader 5.")
            return ra
        if tin["la_that"]:
            them("error", "Đang nối vào TÀI KHOẢN THẬT — mọi lệnh là tiền thật.")
        if not tin["nen_song"]:
            them("error", f"Feed đứng: tick cuối đã {tin['tuoi_tick']}s "
                          f"(ngưỡng {TICK_QUA_HAN:.0f}s). Terminal vẫn báo đã nối.")
        if not tin["cho_giao_dich"]:
            them("error", "Không được phép giao dịch — bật nút AlgoTrading trên MT5, "
                          "và kiểm tra tài khoản có cho EA giao dịch không.")
        if not tin["symbol_giao_dich_duoc"]:
            them("error", f'Symbol "{self.symbol}" không ở chế độ giao dịch đầy đủ '
                          f"(có thể đang chỉ-đóng hoặc ngoài giờ).")
        if tin.get("tre_p95") and tin["tre_p95"] > 500:
            them("warning", f"Độ trễ p95 {tin['tre_p95']} ms — chậm bất thường.")
        # Hồ sơ hiệu chuẩn — ba cảnh báo dưới đây đều sinh từ một lần chạy thật.
        hs = doc_ho_so(tin.get("sàn") or "", self.symbol)
        if not hs:
            them("warning", "Chưa hiệu chuẩn cho sàn này — chưa biết trượt giá và độ trễ "
                            "đặt lệnh thật. Chạy bài kiểm trên tài khoản demo.")
        else:
            if hs.get("server") and tin.get("server") and hs["server"] != tin["server"]:
                them("warning", f"Hồ sơ đo trên server {hs['server']}, đang chạy trên "
                                f"{tin['server']} — số liệu có thể không còn đúng.")
            if tin.get("la_that") and hs.get("truot_vao"):
                them("warning", "Trượt giá trong hồ sơ đo trên DEMO (thường bằng 0) — "
                                "tài khoản thật gần như chắc chắn khác.")
        if self.so_lan_rot:
            them("warning", f"Đã rớt kết nối {self.so_lan_rot} lần trong phiên này "
                            f"(tổng {tin['giay_rot']:.0f}s mất mạng).")
        return ra


# ---------------------------------------------------------------------------
# BÀI TEST ĐẶT LỆNH — chỉ trên tài khoản DEMO
# ---------------------------------------------------------------------------
#: Retcode của MT5 → câu người đọc LÀM ĐƯỢC GÌ. In `retcode=10027` ra màn hình là bắt
#: người dùng đi tra bảng mã, mà lúc đó họ đang bí chứ không đang rảnh.
RETCODE = {
    10004: "sàn báo giá lại (requote) — giá nhảy nhanh hơn lệnh đi",
    10006: "sàn TỪ CHỐI lệnh",
    10011: "sàn lỗi khi xử lý yêu cầu",
    10012: "hết giờ chờ phản hồi",
    10013: "yêu cầu không hợp lệ — sai tham số lệnh",
    10014: "khối lượng không hợp lệ — xem lot tối thiểu/bước lot của symbol",
    10015: "giá không hợp lệ",
    10016: "SL/TP không hợp lệ — thường là đặt quá sát giá (stops level)",
    10017: "sàn TẮT giao dịch cho tài khoản này",
    10018: "thị trường đang ĐÓNG CỬA",
    10019: "không đủ tiền",
    10020: "giá đã đổi trước khi lệnh tới",
    10021: "không có giá (thị trường lặng hoặc feed đứt)",
    10023: "lệnh vừa đổi trạng thái",
    10024: "gửi quá nhiều yêu cầu — sàn chặn bớt",
    10025: "không có gì thay đổi (SL/TP vốn đã đúng)",
    10026: "sàn tắt AutoTrading phía SERVER",
    10027: "AlgoTrading đang TẮT trên MT5 — bấm nút AlgoTrading rồi thử lại",
    10028: "lệnh/vị thế đang bị KHOÁ",
    10029: "vị thế đang ĐÓNG BĂNG (freeze level) — chưa sửa được, phải chờ tan",
    10030: "sàn không nhận kiểu khớp (filling mode) này",
    10031: "mất kết nối tới sàn",
    10032: "thao tác chỉ cho tài khoản THẬT",
    10033: "vượt số lệnh chờ tối đa",
    10034: "vượt giới hạn khối lượng của tài khoản",
    10035: "loại lệnh không hợp lệ",
    10036: "VỊ THẾ ĐÃ ĐÓNG rồi",
    10038: "khối lượng đóng vượt khối lượng vị thế",
    10039: "đã có lệnh đóng cho vị thế này",
    10040: "vượt số vị thế tối đa",
    10045: "sàn bắt đóng theo FIFO",
    10046: "tài khoản KHÔNG cho hedging",
}


def _giai_ma(rc):
    if rc is None:
        return "không có phản hồi từ sàn"
    return f"{RETCODE.get(int(rc), 'sàn từ chối')} (mã {rc})"


# ---------------------------------------------------------------------------
# HIỆU CHUẨN — VÒNG LẶP TỰ CHỈNH, đặt lệnh thật, chỉ chạy trên DEMO
# ---------------------------------------------------------------------------
#: BẢN CHẤT CỦA PHẦN NÀY, nói một câu:
#:
#:     Đây KHÔNG phải bài thi để chấm điểm. Đây là vòng lặp tự chỉnh cho tới khi
#:     bảng Đề phòng ĐÚNG.
#:
#: Nên thứ giao lại ở cuối không phải một danh sách lỗi, mà là một bộ con số mà mỗi
#: dòng đều ghi *đo được*. Bản trước in ra "14/21 bước đạt" rồi thôi — con số đó vừa
#: vô nghĩa (trộn bốn thứ khác hẳn nhau vào một rổ) vừa vô dụng (biết rồi thì làm gì?).
#:
#: BỐN MỨC, KHÔNG PHẢI ĐẠT/HỎNG:
#:   `tron`  — chạy trơn, phòng vệ không phải động tay
#:   `xac`   — phòng vệ sửa TRƯỚC khi gửi nên sàn không kịp từ chối
#:             → bằng chứng MẠNH NHẤT rằng giả thuyết đúng
#:   `do`    — sàn từ chối, phòng vệ chữa được, ý định vẫn thành
#:             → VẪN LÀ ĐẠT. Lỗi mà ta đã đề phòng đúng thì không phải lỗi của ta.
#:   `hong`  — phòng vệ bó tay → giả thuyết SAI, phải chỉnh con số rồi chạy lại
#:   `nguoi` — máy không chữa được (AlgoTrading tắt, hết tiền, chợ đóng)
#:             → chỉnh con số bao nhiêu cũng vô ích. DỪNG và nói rõ người phải làm gì.
#:
#: Vì sao phải mở/đóng lệnh THẬT thay vì đặt một lệnh không thể khớp: mấy con số dưới
#: đây KHÔNG có cách nào đọc ra, chỉ đo được —
#:   • trượt giá lúc VÀO và lúc RA — cái ăn thẳng vào biên lợi nhuận
#:   • độ trễ THẬT của từng loại thao tác (gửi != sửa != đóng)
#:   • sàn có thật sự nhận filling mode nó khai không
#:   • ngưỡng SL/TP thật (đo được: sàn khai 0, thật 215)
#: Lặp nhiều vòng và giãn cách để GIÁ CHẠY: đo sáu lần ở cùng một mức giá thì ra sáu
#: con số giống nhau, đó là một điểm chứ không phải một phân bố.
def _tk_so(x):
    import statistics as st
    if not x:
        return None
    y = sorted(x)
    return {"p50": round(st.median(y), 1), "p95": round(y[max(0, int(len(y) * .95) - 1)], 1),
            "min": round(y[0], 1), "max": round(y[-1], 1), "n": len(y)}


#: Magic của bài kiểm. Tách hẳn khỏi magic chiến lược để dọn rác không bao giờ đụng
#: nhầm lệnh thật.
MAGIC_KIEM = 777001

#: Trần vòng lặp. Đây là ĐẶT LỆNH THẬT trên demo — lặp vô tận là đốt thời gian thật,
#: nên hết trần mà con số chưa hội tụ thì nói thẳng "chưa chốt được", không im lặng.
LAP_TOI_DA = 4

#: Biên an toàn cho ngưỡng SL/TP. Đo được 215 thì cài 215 là cài đúng mép — spread
#: giãn một nhịp là lại bị từ chối. 1.2 lần cho nó chỗ thở.
BIEN_KEP = 1.2

#: Biên cho trượt giá. Đo p95 rồi nhân lên: deviation quá hẹp thì lệnh bị từ chối,
#: quá rộng thì khớp giá xấu — nhưng KHÔNG khớp còn tệ hơn khớp xấu.
BIEN_TRUOT = 1.5


def rac_con_lai(symbol):
    """Còn vị thế / lệnh chờ nào của BÀI KIỂM sót lại không.

    ⚠ Sinh ra từ một lần chạy thật: bài kiểm đứt giữa chừng vì mất cầu nối, để lại một
    vị thế đang mở. Nếu không ai soi thì nó nằm đó âm thầm ăn/lỗ, và người dùng mở Live
    lên chẳng thấy gì bất thường. Đây là đúng loại lỗi ẩn cần chặn."""
    ra = {"vi_the": [], "lenh_cho": [], "chu": ""}
    if mt5 is None or not nn.CO_MT5:
        return ra
    try:
        with nn._KetNoi():
            ra["vi_the"] = [int(p.ticket) for p in (mt5.positions_get(symbol=symbol) or ())
                            if p.magic == MAGIC_KIEM]
            ra["lenh_cho"] = [int(o.ticket) for o in (mt5.orders_get(symbol=symbol) or ())
                              if o.magic == MAGIC_KIEM]
    except Exception as e:                      # noqa: BLE001
        ra["chu"] = f"{type(e).__name__}: {e}"
    return ra


def don_rac(symbol):
    """Đóng/huỷ sạch mọi thứ của bài kiểm. Gọi được cả từ nút riêng lẫn từ `finally`.

    Đi qua `gui_lenh` như mọi thứ khác — dọn rác cũng là chạm sàn, và đây đúng là lúc
    hay đứt nhất (bài kiểm vừa hỏng vì mất kết nối thì dọn cũng gặp mất kết nối)."""
    ra = {"da_dong": 0, "da_huy": 0, "chu": ""}
    if mt5 is None or not nn.CO_MT5:
        return ra
    try:
        with nn._KetNoi():
            for pos in (mt5.positions_get(symbol=symbol) or ()):
                if pos.magic != MAGIC_KIEM:
                    continue
                if gui_lenh.dong(symbol, pos)["ket"] == "ok":
                    ra["da_dong"] += 1
            for o in (mt5.orders_get(symbol=symbol) or ()):
                if o.magic != MAGIC_KIEM:
                    continue
                if gui_lenh.huy_cho(symbol, int(o.ticket))["ket"] == "ok":
                    ra["da_huy"] += 1
    except Exception as e:                      # noqa: BLE001
        ra["chu"] = f"{type(e).__name__}: {e}"
    return ra


#: Mã nghĩa là "chưa đo được, thử lại nấc này" chứ KHÔNG phải "SL quá sát".
#: ⚠ Không tách ra thì phép dò đọc nhầm một lần đóng băng thành "ngưỡng cao hơn" và
#: trả về con số to hơn sự thật — rồi mọi SL sau đó bị đẩy ra xa vô cớ. Đo được: cùng
#: một sàn ra 410 điểm ở lượt này và 324 ở lượt sau, chênh nhau chính vì nhiễu.
#: `10013` nằm đây vì terminal trả nó cả khi không gửi đi được — xem `gui_lenh.LUONG_LU`.
_NHIEU = (10029, 10031, 10024, 10012, 10011, 10021, 10013)


def do_stops_level(symbol, pos, si, cao=800, thap=20):
    """Dò ngưỡng SL/TP THẬT bằng cách đặt sát dần tới khi sàn từ chối.

    ⚠ Vì sao phải dò: lần chạy thật sàn khai `trade_stops_level = 0` nhưng SL cách 300
    điểm vẫn bị từ chối `10016`. Con số khai KHÔNG dùng được. Mà D_02 tính SL theo ATR —
    lúc nén chặt SL còn ngắn hơn thế, nên nếu không biết ngưỡng thật thì live sẽ bị từ
    chối im lặng đúng lúc vào lệnh.

    Chia đôi: mỗi lần thử là một `order_send` thật, nên 6 lần là biết. Trả số ĐIỂM tối
    thiểu ĐẶT ĐƯỢC, hoặc None nếu không đo được.

    Gọi thẳng `order_send` — CỐ Ý. Đây là phép ĐO, mà tầng phòng vệ thì sinh ra để né
    đúng cái ta đang muốn chạm vào. Cho nó chen vào đây là đo chính nó.

    ⚠ PHẢI TRẢ LẠI HIỆN TRƯỜNG. Phép đo này kết thúc với SL nằm SÁT GIÁ NHẤT CÓ THỂ —
    đó là định nghĩa của nó. Vàng chạy vài chục điểm mỗi phút nên cái SL ấy dính gần
    như ngay, vị thế đóng, và ba bước sau của vòng kiểm vẫn cầm vị thế cũ mà gọi tiếp →
    terminal từ chối tại chỗ, cả vòng chết. Gặp thật. Một phép đo mà làm hỏng thứ nó
    vừa đo thì không phải phép đo."""
    if mt5 is None:
        return None
    so = int(pos.ticket)
    mua = pos.type == 0
    g = float(pos.price_open)
    diem = float(si.point) or 0.01
    dat = None
    try:
        for _ in range(8):
            giua = (cao + thap) // 2
            sl = g - giua * diem if mua else g + giua * diem
            r = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol,
                                "position": so, "sl": round(sl, si.digits),
                                "tp": 0.0})
            ma = int(getattr(r, "retcode", 0) or 0)
            ok = r is not None and ma == mt5.TRADE_RETCODE_DONE
            if not ok and (ma in _NHIEU or not gui_lenh._dang_noi()):
                time.sleep(1.5)                 # nhiễu, không phải câu trả lời
                if gui_lenh._vi_the(symbol, so) is None:
                    return dat                  # vị thế mất rồi, hết cái để đo
                continue
            if not ok and gui_lenh._vi_the(symbol, so) is None:
                # Bị từ chối vì vị thế không còn, KHÔNG phải vì SL sát. Đọc nhầm chỗ
                # này là thổi phồng ngưỡng lên rồi mọi SL sau bị đẩy xa vô cớ.
                return dat
            if ok:
                dat, cao = giua, giua           # đặt được → thử sát hơn nữa
            else:
                thap = giua                     # bị từ chối → phải xa hơn
            if cao - thap <= 10:
                break
    finally:
        try:
            mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol,
                            "position": so, "sl": 0.0, "tp": 0.0})
        except Exception:                       # noqa: BLE001
            pass
    return dat


def _cham(bg):
    """Bản ghi tầng phòng vệ → (mức, câu giải thích).

    ⚠ ĐÂY là chỗ "lỗi" và "hỏng" tách làm hai, và đó là toàn bộ ý nghĩa của bài kiểm.
    Sàn từ chối mà phòng vệ chữa được thì bài kiểm ĐẠT — nó vừa chứng minh giả thuyết
    đúng. Chỉ khi phòng vệ bó tay mới là hỏng, và chỉ khi đó mới phải chỉnh con số."""
    if bg["ket"] == "nguoi":
        return "nguoi", bg["chu"]
    if bg["ket"] != "ok":
        return "hong", bg["chu"] or _giai_ma(bg["ma"])
    phu = []
    if bg.get("truot") is not None:
        phu.append("trượt %+.1f điểm" % bg["truot"])
    if bg["so_lan"] > 1:
        phu.append("thử %d lần" % bg["so_lan"])
    if bg["da_sua"]:
        phu.append("phòng vệ chữa được: " + " · ".join(bg["da_sua"][:3]))
        return "do", " · ".join(phu)
    if bg["sua_truoc"]:
        phu.append("phòng vệ sửa TRƯỚC khi gửi: " + " · ".join(bg["sua_truoc"][:2]))
        return "xac", " · ".join(phu)
    if bg["chu"]:
        phu.append(bg["chu"])
    return "tron", " · ".join(phu)


def _mot_luot(symbol, so_vong, nghi_giay, lot, luat, tien_do, ghi_ra,
              lap=0, lap_toi_da=1, nguong_biet=None):
    """MỘT lượt hiệu chuẩn: `so_vong` vòng lệnh thật, chấm theo bốn mức.

    Mọi thao tác đi qua `gui_lenh` — bản trước chỉ có bước mở đi qua đó, nên bốn bước
    còn lại vừa không được phòng vệ vừa không khai báo mã lạ. Đó là chỗ `10029` và
    `10036` lọt lưới suốt.

    TỪ CHỐI nếu không phải demo — đọc `trade_mode`, không hỏi. Không bao giờ ném."""
    ra = {"chay_duoc": False, "chu": "", "buoc": [], "so_vong": 0,
          "truot_vao": None, "truot_ra": None, "tre_mo": None, "tre_sua": None,
          "tre_dong": None, "tre_cho": None, "loi": [], "do_luc": None,
          "de_nghi": None, "stops_level_that": None, "fill_hoc": None,
          "can_nguoi": [], "ma_hong": [], "ma_la": [], "dem": {}}
    if mt5 is None or not nn.CO_MT5:
        ra["chu"] = "Máy chưa cài thư viện MetaTrader5."
        return ra

    tv, tr, t_mo, t_sua, t_dong, t_cho = [], [], [], [], [], []

    def ghi(ten, muc, chu="", ms=None, ma=None):
        b = {"ten": ten, "muc": muc, "dat": muc in ("tron", "do", "xac"),
             "chu": chu, "ms": ms, "ma": ma}
        ra["buoc"].append(b)
        ra["dem"][muc] = ra["dem"].get(muc, 0) + 1
        if muc == "hong":
            ra["loi"].append(ten + ": " + chu)
            if ma:
                ra["ma_hong"].append(int(ma))
        elif muc == "nguoi":
            ra["can_nguoi"].append(chu)
        # ⚠ Chảy ra NGAY, không gom tới cuối. Live thì mọi thứ chạm vào sàn đều phải để
        # lại vết đúng lúc nó xảy ra — bài kiểm đặt 5 lệnh thật mà nhật ký im lặng suốt
        # hai phút là đúng cái app này sinh ra để chống.
        if ghi_ra:
            try:
                ghi_ra(b)
            except Exception:               # noqa: BLE001
                pass
        return b

    def xong(bg, ten, ms=None, gio=None):
        """Chấm một bản ghi phòng vệ thành một bước. Trả True nếu đi tiếp được."""
        muc, chu = _cham(bg)
        for m in bg.get("la", ()):
            if int(m) not in ra["ma_la"]:
                ra["ma_la"].append(int(m))
        # ⚠ CHỈ học `filling` khi tầng phòng vệ ĐÃ PHẢI ĐỔI nó. Sàn nhận luôn kiểu nó
        # khai thì chẳng có gì để học — ghi đè vào hồ sơ một con số "đúng sẵn" chỉ làm
        # ta tưởng đã đo trong khi chưa đo gì. Và bước đóng/huỷ cũng mang `type_filling`
        # nhưng không hề bị từ chối vì nó, nên để chúng ghi đè là học nhầm.
        if (bg["ket"] == "ok" and bg.get("fill_dung") is not None
                and any("filling" in s for s in bg.get("da_sua", ()))):
            ra["fill_hoc"] = int(bg["fill_dung"])
        if gio is not None and muc in ("tron", "do", "xac") and ms is not None:
            gio.append(ms)
        ghi(ten, muc, chu, ms, bg.get("ma"))
        return muc != "nguoi"

    try:
        with nn._KetNoi():
            tk = mt5.account_info()
            if tk is None:
                ra["chu"] = "Không đọc được tài khoản."
                return ra
            if _tk_that(tk):
                ra["chu"] = ("TỪ CHỐI: %s là TÀI KHOẢN THẬT. Bài này mở và đóng lệnh "
                             "thật nên chỉ chạy trên demo." % tk.login)
                return ra
            si = mt5.symbol_info(symbol)
            if si is None:
                mt5.symbol_select(symbol, True)
                si = mt5.symbol_info(symbol)
            if si is None:
                ra["chu"] = "Sàn không có symbol " + str(symbol)
                return ra
            ra["chay_duoc"] = True
            ra["server"], ra["login"], ra["san"] = str(tk.server), int(tk.login), str(tk.company)
            v = float(lot or si.volume_min)
            diem = float(si.point) or 0.01
            magic = MAGIC_KIEM

            for vong in range(int(so_vong)):
                if tien_do:
                    # ⚠ Có cả LƯỢT chứ không chỉ vòng. Bản trước chỉ đẩy `vòng k/3` và
                    # nó reset mỗi lượt, nên bốn lượt trông y hệt một vòng lặp vô tận —
                    # người dùng không có cách nào biết nó đang tiến hay đang treo.
                    tien_do(vong, int(so_vong), int(lap), int(lap_toi_da))
                mua = vong % 2 == 0
                nhan = "MUA" if mua else "BÁN"

                # --- mở ---
                t0 = time.perf_counter()
                bg = gui_lenh.gui(symbol, mua, v, magic=magic,
                                  chu="CatStudio hieu chuan", luat=luat)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                if not xong(bg, "vòng %d: mở %s market" % (vong + 1, nhan), ms, t_mo):
                    return ra
                if bg["ket"] != "ok":
                    continue
                if bg["truot"] is not None:
                    tv.append(bg["truot"])

                pos = None
                for p in (mt5.positions_get(symbol=symbol) or ()):
                    if p.magic == magic:
                        pos = p
                        break
                if pos is None:
                    ghi("vòng %d: tìm vị thế vừa mở" % (vong + 1), "hong", "không thấy")
                    continue

                # --- đo ngưỡng SL/TP thật (chỉ vòng đầu, và chỉ khi chưa biết) ---
                if vong == 0 and not nguong_biet:
                    nguong = do_stops_level(symbol, pos, si)
                    ra["stops_level_that"] = nguong
                    ghi("đo ngưỡng SL/TP thật", "tron" if nguong else "hong",
                        ("tối thiểu ~%d điểm (sàn khai %s)"
                         % (nguong, getattr(si, "trade_stops_level", "?")))
                        if nguong else "không đo được")
                    # Phép dò vừa nghịch SL và có thể đã làm vị thế đóng — đọc lại,
                    # đừng cầm ảnh cũ đi tiếp.
                    pos = gui_lenh._vi_the(symbol, int(pos.ticket))
                    if pos is None:
                        ghi("vòng %d: vị thế sau phép đo" % (vong + 1), "hong",
                            "đã đóng trong lúc dò ngưỡng")
                        continue
                elif vong == 0:
                    ra["stops_level_that"] = nguong_biet

                # --- gắn rồi sửa SL/TP, QUA tầng phòng vệ ---
                # Cố tình xin 200 điểm ở lượt hai: nó SÁT HƠN ngưỡng đã đo, nên đây
                # chính là phép thử "phòng vệ có kẹp ra đúng chỗ không". Kẹp được →
                # `xac`, tức giả thuyết đúng. Bản trước gửi thẳng nên chỉ ra `10016`.
                for lan, xa in ((1, 300), (2, 200)):
                    g = float(pos.price_open)
                    sl = g - xa * diem if mua else g + xa * diem
                    tp = g + xa * 2 * diem if mua else g - xa * 2 * diem
                    t0 = time.perf_counter()
                    bg2 = gui_lenh.sua_stops(symbol, pos, sl, tp, luat=luat)
                    ms = round((time.perf_counter() - t0) * 1000, 1)
                    if not xong(bg2, "vòng %d: %s SL/TP (%d điểm)"
                                % (vong + 1, "gắn" if lan == 1 else "sửa", xa),
                                ms, t_sua):
                        return ra

                # --- đóng ---
                t0 = time.perf_counter()
                bg3 = gui_lenh.dong(symbol, pos, luat=luat)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                if not xong(bg3, "vòng %d: đóng vị thế" % (vong + 1), ms, t_dong):
                    return ra
                if bg3["ket"] == "ok" and bg3["truot"] is not None:
                    tr.append(bg3["truot"])
                ra["so_vong"] += 1

                if vong < int(so_vong) - 1:
                    time.sleep(float(nghi_giay))        # để GIÁ CHẠY

            # --- lệnh chờ: đặt · sửa · huỷ ---
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                gia = round(float(tick.bid) * 0.9, si.digits)
                t0 = time.perf_counter()
                bgp = gui_lenh.dat_cho(symbol, True, v, gia, magic=magic,
                                       chu="CatStudio cho", luat=luat)
                ms = round((time.perf_counter() - t0) * 1000, 1)
                if not xong(bgp, "lệnh chờ: đặt", ms, t_cho):
                    return ra
                if bgp["ket"] == "ok" and bgp["ticket"]:
                    tk_cho = bgp["ticket"]
                    t0 = time.perf_counter()
                    bgm = gui_lenh.sua_cho(symbol, tk_cho, round(gia * 0.99, si.digits),
                                           luat=luat)
                    ms = round((time.perf_counter() - t0) * 1000, 1)
                    if not xong(bgm, "lệnh chờ: sửa giá", ms, t_cho):
                        return ra
                    t0 = time.perf_counter()
                    bgd = gui_lenh.huy_cho(symbol, tk_cho, luat=luat)
                    ms = round((time.perf_counter() - t0) * 1000, 1)
                    if not xong(bgd, "lệnh chờ: huỷ", ms, t_cho):
                        return ra

            ra["truot_vao"] = _tk_so(tv)
            ra["truot_ra"] = _tk_so(tr)
            ra["tre_mo"] = _tk_so(t_mo)
            ra["tre_sua"] = _tk_so(t_sua)
            ra["tre_dong"] = _tk_so(t_dong)
            ra["tre_cho"] = _tk_so(t_cho)
            ra["do_luc"] = time.strftime("%Y-%m-%d %H:%M")

            # Spread THẬT để backtest chạy trên đúng điều kiện live: spread sàn cộng
            # trượt giá đo được. Không có phần cộng thêm này thì backtest lạc quan hơn
            # live đúng bằng lượng trượt, mãi mãi, mà không ai thấy.
            tick = mt5.symbol_info_tick(symbol)
            sp = round((tick.ask - tick.bid) / diem, 1) if tick else None
            tr_vao = abs((ra["truot_vao"] or {}).get("p95") or 0)
            ra["de_nghi"] = {
                "spread_diem": round((sp or 0) + tr_vao, 1) if sp else None,
                "vi_sao": ("spread sàn %s điểm + trượt giá p95 %s điểm đo được"
                           % (sp, round(tr_vao, 1))) if sp else "",
                "stops_level_that": ra.get("stops_level_that"),
            }
            d = ra["dem"]
            ra["chu"] = ("%d trơn · %d xác nhận · %d phòng vệ đỡ · %d hỏng"
                         % (d.get("tron", 0), d.get("xac", 0),
                            d.get("do", 0), d.get("hong", 0)))
    except Exception as e:                      # noqa: BLE001
        ra["chu"] = "%s: %s" % (type(e).__name__, e)
    finally:
        # ⚠ DỌN BẰNG MỌI GIÁ. Lần chạy thật vừa rồi đứt giữa chừng vì mất cầu nối và để
        # lại một vị thế đang mở — không có `finally` thì nó nằm đó không ai biết.
        try:
            d = don_rac(symbol)
            if d["da_dong"] or d["da_huy"]:
                ra["buoc"].append({"ten": "dọn rác sau lượt kiểm", "muc": "tron",
                                   "dat": True, "ma": None,
                                   "chu": "đóng %d vị thế · huỷ %d lệnh chờ"
                                          % (d["da_dong"], d["da_huy"]), "ms": None})
        except Exception:                       # noqa: BLE001
            pass
    return ra


#: Cách xử có nghĩa là "còn thử lại" — tăng `thu_lai` mới có tác dụng với chúng.
_CON_THU = ("thu", "noi", "kep", "doi_fill", "cho_lau", "cho_noi")


def _suy_chinh(kq, L):
    """Lỗi vừa gặp TỰ KHAI giá trị đúng. Trả `({khoá: giá trị mới}, [vì sao], {mã bó tay})`.

    ⚠ Đây là trái tim của vòng lặp. Không có hàm này thì bài kiểm chỉ biết kêu, còn
    chỉnh vẫn là việc của người — mà người thì không biết `10029` nghĩa là tăng
    `cho_bang_ms`. Mỗi luật dưới đây đọc được thành một câu tiếng Việt: *lỗi X vừa nói
    rằng con số Y đang sai, và sai theo hướng này.*"""
    moi, vi_sao = {}, []
    hong = set(kq.get("ma_hong") or ())

    def dat(khoa, gt, ly_do):
        cu = L.get(khoa)
        if gt is None or (cu is not None and gt == cu):
            return
        moi[khoa] = gt
        vi_sao.append("%s: %s → %s — %s" % (khoa, cu, gt, ly_do))

    # 1. NGƯỠNG SL/TP — con số đo được, cộng biên thở.
    ng = kq.get("stops_level_that")
    if ng:
        can = int(round(ng * BIEN_KEP))
        if not L.get("kep_stops") or L["kep_stops"] < can:
            dat("kep_stops", can, "đo được ngưỡng thật %d điểm × biên %.1f" % (ng, BIEN_KEP))
    # Phòng vệ vẫn để lọt 10016 → con số đang dùng CÒN THIẾU, bất kể đo được bao nhiêu.
    if 10016 in hong:
        cu = L.get("kep_stops") or ng or 100
        dat("kep_stops", int(cu * 1.5), "vẫn lọt 10016 — kẹp đang thiếu")

    # 2. KIỂU KHỚP — học luôn cái sàn thật sự nhận. Đo được: lệnh nào cũng phải đổi
    #    filling ở lần thử đầu, tức mỗi lệnh live đang trả một vòng gửi thừa. Mãi mãi.
    if kq.get("fill_hoc") is not None:
        dat("filling", int(kq["fill_hoc"]), "sàn thật sự nhận kiểu này")

    # 3. TRƯỢT GIÁ — deviation phải phủ được cái đã đo, không thì là con số bịa.
    tv = kq.get("truot_vao") or {}
    do_duoc = max(abs(tv.get("p95") or 0), abs(tv.get("max") or 0))
    if do_duoc:
        can = int(round(do_duoc * BIEN_TRUOT))
        if int(L.get("deviation") or 0) < can:
            dat("deviation", can, "trượt đo được tới %.0f điểm × biên %.1f"
                % (do_duoc, BIEN_TRUOT))

    # 4. MẤT KẾT NỐI — đã chờ nối lại rồi mà vẫn hỏng thì phải chờ LÂU hơn và thử thêm.
    if 10031 in hong:
        dat("cho_noi_giay", min(int(L.get("cho_noi_giay") or 30) * 2, 120),
            "10031 vẫn lọt — chờ nối lại chưa đủ lâu")
        dat("thu_lai", min(int(L.get("thu_lai") or 3) + 2, 8), "10031 vẫn lọt")

    # 5. ĐÓNG BĂNG — freeze chưa tan mà ta đã gửi lại.
    if 10029 in hong:
        dat("cho_bang_ms", min(int(L.get("cho_bang_ms") or 1500) * 2, 8000),
            "10029 vẫn lọt — băng chưa tan đã gửi lại")

    # 6. SÀN CHẶN VÌ DỒN DẬP — giãn nhịp ra.
    if 10024 in hong:
        dat("cho_ms", min(int(L.get("cho_ms") or 500) * 2, 4000),
            "10024 — đang gửi dồn quá nhanh")

    # 7. HỎNG MÀ KHÔNG RÕ MÃ → cho thêm một nhịp thử.
    #
    # ⚠ CHỈ với mã CÒN ĐƯỢC THỬ LẠI. Bản trước tăng `thu_lai` cho mọi mã hỏng, kể cả
    # mã xếp `dung` — tức chỉnh một con số không bao giờ được dùng tới, rồi vòng lặp
    # tưởng mình vừa tiến bộ nên chạy tiếp. Đo được: `thu_lai 3→4→5→6→7` suốt bốn lượt
    # trong khi mã hỏng là `10013` (không thử lại), đốt sạch bài kiểm mà không sửa gì.
    con_thu = {m for m in hong if (gui_lenh._xu_ly(m) or "thu") in _CON_THU}
    bo_tay = hong - con_thu
    if con_thu and not (con_thu & {10016, 10031, 10029, 10024}):
        dat("thu_lai", min(int(L.get("thu_lai") or 3) + 1, 8),
            "còn hỏng ở mã %s — cho thêm một lần thử"
            % ", ".join(str(m) for m in sorted(con_thu)))
    return moi, vi_sao, bo_tay


def hieu_chuan(symbol, so_vong=3, nghi_giay=15, lot=None, tien_do=None, ghi_ra=None,
               luat=None, lap_toi_da=LAP_TOI_DA):
    """VÒNG LẶP TỰ CHỈNH: chạy → chỗ nào hỏng thì suy ra giá trị đúng → chạy lại.

    Kết thúc ở ĐÚNG BA trạng thái, và phải nói rõ là cái nào:

      `xong`       — không còn gì để chỉnh. Bảng Đề phòng đã đúng.
      `nguoi`      — gặp thứ máy không chữa được. Dừng, và nói người phải làm gì.
      `chua_hoi_tu`— hết trần lặp mà vẫn còn hỏng. Nói thẳng chỗ chưa chốt được,
                     kèm những gì đã thử. KHÔNG im lặng để đó.

    Không có trạng thái "14/21 bước đạt" — con số đó trộn bốn thứ khác hẳn nhau vào
    một rổ rồi bắt người đọc tự tách."""
    L = dict(gui_lenh.LUAT_MAC_DINH, **(luat or {}))
    ra = {"trang_thai": "chua_hoi_tu", "chu": "", "lan": [], "luat": L,
          "da_chinh": [], "can_nguoi": [], "cuoi": None,
          "chay_duoc": False, "buoc": [], "de_nghi": None, "stops_level_that": None,
          "ma_la": []}

    for lap in range(int(lap_toi_da)):
        if ghi_ra:
            try:
                ghi_ra({"ten": "── lượt %d/%d" % (lap + 1, int(lap_toi_da)),
                        "muc": "moc", "dat": True, "chu": "", "ms": None, "ma": None})
            except Exception:                   # noqa: BLE001
                pass
        # ⚠ Ngưỡng SL/TP ĐO MỘT LẦN rồi dùng lại. Phép dò tốn ~8 lệnh thật và kết quả
        # dao động theo giá đang chạy — đo được 410 điểm ở lượt này, 324 ở lượt sau.
        # Đo lại mỗi lượt thì lần nào nhích lên là lại sinh một lần "chỉnh", và vòng
        # lặp leo thang mãi vì nhiễu chứ không vì sai.
        kq = _mot_luot(symbol, so_vong, nghi_giay, lot, L, tien_do, ghi_ra,
                       lap=lap, lap_toi_da=int(lap_toi_da),
                       nguong_biet=ra["stops_level_that"])
        ra["lan"].append({"luat": dict(L), "chu": kq.get("chu", ""),
                          "dem": kq.get("dem", {})})
        ra["cuoi"] = kq
        ra["chay_duoc"] = kq.get("chay_duoc", False)
        ra["buoc"] = kq.get("buoc", [])
        ra["de_nghi"] = kq.get("de_nghi") or ra["de_nghi"]
        if kq.get("stops_level_that"):
            ra["stops_level_that"] = kq["stops_level_that"]
        for m in kq.get("ma_la") or ():
            if m not in ra["ma_la"]:
                ra["ma_la"].append(m)

        if not kq.get("chay_duoc"):
            ra["trang_thai"] = "nguoi"
            ra["chu"] = kq.get("chu") or "Không chạy được bài kiểm."
            ra["can_nguoi"] = [ra["chu"]]
            return _chot(ra, symbol, L)
        if kq.get("can_nguoi"):
            # Chỉnh con số bao nhiêu cũng vô ích — dừng ngay, đừng đốt thêm lệnh thật.
            ra["trang_thai"] = "nguoi"
            ra["can_nguoi"] = kq["can_nguoi"]
            ra["chu"] = "Cần bạn ra tay: " + kq["can_nguoi"][0]
            return _chot(ra, symbol, L)

        chinh, vi_sao, bo_tay = _suy_chinh(kq, L)
        if not chinh and kq.get("dem", {}).get("hong"):
            # ⚠ CÒN HỎNG mà không con số nào chỉnh được → DỪNG NGAY, đừng lặp tiếp.
            # Bản trước rơi thẳng vào nhánh "xong" ở đây, tức báo ĐẠT trong khi vẫn
            # còn bước hỏng — một lời nói dối, và đúng loại nguy nhất: nói dối theo
            # hướng trấn an. Lặp tiếp cũng vô nghĩa: cùng bộ số thì cùng kết quả.
            ra["trang_thai"] = "chua_hoi_tu"
            ra["chu"] = ("Còn %d bước hỏng mà KHÔNG con số nào chỉnh được%s. Đây là chỗ "
                         "ta chưa hiểu, không phải chỗ cài sai — chạy lại cũng vậy thôi."
                         % (kq["dem"]["hong"],
                            (" (mã %s)" % ", ".join(str(m) for m in sorted(bo_tay)))
                            if bo_tay else ""))
            return _chot(ra, symbol, L)
        if not chinh:
            ra["trang_thai"] = "xong"
            d = kq.get("dem", {})
            ra["chu"] = ("Đã chốt xong sau %d lượt — %d trơn · %d xác nhận · "
                         "%d phòng vệ đỡ, không còn gì để chỉnh."
                         % (lap + 1, d.get("tron", 0), d.get("xac", 0), d.get("do", 0)))
            return _chot(ra, symbol, L)
        L.update(chinh)
        ra["luat"] = L
        ra["da_chinh"].extend(vi_sao)
        if ghi_ra:
            for c in vi_sao:
                try:
                    ghi_ra({"ten": "chỉnh giả thuyết", "muc": "chinh", "dat": True,
                            "chu": c, "ms": None, "ma": None})
                except Exception:               # noqa: BLE001
                    pass

    ra["trang_thai"] = "chua_hoi_tu"
    ra["chu"] = ("Hết %d lượt mà vẫn còn hỏng — chưa chốt được. Đã thử: %s"
                 % (int(lap_toi_da), "; ".join(ra["da_chinh"][-3:]) or "không chỉnh gì"))
    return _chot(ra, symbol, L)


def _chot(ra, symbol, L):
    """Ghi bộ số cuối vào hồ sơ. Kể cả khi chưa hội tụ — cái đã học được vẫn hơn không.

    ⚠ Ghi cả `luat`: đây là thứ `gui_lenh` sẽ dùng cho MỌI lệnh live sau này, và là
    thứ khối Đề phòng đọc ra để trình bày. Không ghi thì bài kiểm chạy xong lại về
    số mặc định, tức chạy để làm gì."""
    kq = ra.get("cuoi") or {}
    try:
        ho_so = {k: kq.get(k) for k in ("truot_vao", "truot_ra", "tre_mo", "tre_sua",
                                        "tre_dong", "tre_cho", "so_vong", "do_luc",
                                        "de_nghi", "stops_level_that")}
        ho_so.update(thong_so_tinh(symbol))
        ho_so["server"] = kq.get("server", "")
        ho_so["luat"] = dict(L)
        ho_so["trang_thai"] = ra["trang_thai"]
        ho_so["da_chinh"] = list(ra["da_chinh"])
        ho_so["ma_la"] = list(ra["ma_la"])
        if kq.get("san"):
            ghi_ho_so(kq["san"], symbol, ho_so)
    except Exception:                           # noqa: BLE001
        pass
    return ra




# ---------------------------------------------------------------------------
# LỆNH CỦA SÀN — nguồn sự thật của cửa sổ Live
# ---------------------------------------------------------------------------
#: ⚠ CỐT LÕI. Ở tester, sự thật là sổ lệnh MÔ PHỎNG — vì không có sàn nào cả. Ở live,
#: sự thật là SÀN: chiến lược chỉ *quyết định*, còn cái gì thật sự tồn tại thì chỉ MT5
#: biết.
#:
#: Vẽ chart Live từ sổ mô phỏng sai theo hai chiều, và chiều thứ hai mới nguy:
#:   • lệnh do bài kiểm đặt — CÓ THẬT, có ticket — không hiện, vì engine không biết;
#:   • engine "nghĩ" đã đặt mà sàn từ chối → chart vẽ ra một lệnh KHÔNG TỒN TẠI.
#:
#: Nên nguồn lệnh của Live là `positions_get` · `orders_get` · `history_deals_get`, cắt
#: từ mốc bấm Live. Không thêm tầng nào — bỏ bớt một tầng trùng lặp.
def lenh_san(symbol, tu_luc):
    """Mọi lệnh CÓ THẬT ở sàn từ `tu_luc` (unix giây) → đúng hình dạng `LenhVe` mà
    `Chart` đang ăn. Không bao giờ ném."""
    ra = []
    if mt5 is None or not nn.CO_MT5:
        return ra
    try:
        import datetime as _dt
        with nn._KetNoi():
            si = mt5.symbol_info(symbol)
            digits = int(getattr(si, "digits", 2)) if si else 2

            def lam(id_, huong, t_dat, gia_dat, sl, tp, lot, la_kiem=False,
                    t_khop=None, gia_khop=None, t_dong=None, gia_dong=None,
                    ly_do=None, lai_r=None):
                return {"id": id_, "huong": huong, "trang_thai": "dong" if t_dong else "mo",
                        "t_dat": int(t_dat), "t_khop": t_khop and int(t_khop),
                        "t_dong": t_dong and int(t_dong),
                        "gia_dat": gia_dat, "gia_khop": gia_khop, "gia_dong": gia_dong,
                        "sl": sl or None, "tp": tp or None,
                        "ly_do_dong": ly_do, "lot": lot, "lai_R": lai_r,
                        "la_kiem": bool(la_kiem),
                        "sl_lich_su": [[int(t_dat), sl]] if sl else [],
                        "tp_lich_su": [[int(t_dat), tp]] if tp else []}

            # 1. VỊ THẾ đang mở
            for p in (mt5.positions_get(symbol=symbol) or ()):
                if int(p.time) < tu_luc:
                    continue
                ra.append(lam(f"#{p.ticket}", "mua" if p.type == 0 else "ban",
                              p.time, float(p.price_open), float(p.sl), float(p.tp),
                              float(p.volume), p.magic == MAGIC_KIEM, t_khop=p.time,
                              gia_khop=float(p.price_open)))

            # 2. LỆNH CHỜ chưa khớp
            for o in (mt5.orders_get(symbol=symbol) or ()):
                if int(o.time_setup) < tu_luc:
                    continue
                ra.append(lam(f"#{o.ticket}", "mua" if o.type in (2, 4, 6) else "ban",
                              o.time_setup, float(o.price_open), float(o.sl), float(o.tp),
                              float(o.volume_initial), o.magic == MAGIC_KIEM))

            # 3. VỊ THẾ ĐÃ ĐÓNG — ghép từ deal theo `position_id`. Một vị thế có ít nhất
            #    hai deal (vào và ra); ghép lại mới ra được giá vào/ra và lãi.
            t0 = _dt.datetime.fromtimestamp(max(0, tu_luc - 60))
            t1 = _dt.datetime.now() + _dt.timedelta(hours=1)
            nhom = {}
            for d in (mt5.history_deals_get(t0, t1) or ()):
                if d.symbol != symbol or not d.position_id:
                    continue
                nhom.setdefault(int(d.position_id), []).append(d)
            for pid, ds in nhom.items():
                ds.sort(key=lambda x: x.time)
                vao = next((x for x in ds if x.entry == 0), None)     # DEAL_ENTRY_IN
                raa = next((x for x in ds if x.entry == 1), None)     # DEAL_ENTRY_OUT
                if vao is None or raa is None or int(vao.time) < tu_luc:
                    continue
                mua = vao.type == 0
                ra.append(lam(f"#{pid}", "mua" if mua else "ban",
                              vao.time, float(vao.price), None, None, float(vao.volume),
                              vao.magic == MAGIC_KIEM, t_khop=vao.time, gia_khop=float(vao.price),
                              t_dong=raa.time, gia_dong=float(raa.price),
                              ly_do="dong",
                              lai_r=round(float(raa.profit), 2)))
            ra.sort(key=lambda x: x["t_dat"])
    except Exception:                           # noqa: BLE001
        pass
    return ra
