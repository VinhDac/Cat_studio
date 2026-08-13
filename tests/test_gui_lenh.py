"""TẦNG PHÒNG VỆ + VÒNG HIỆU CHUẨN — chạy trên một SÀN GIẢ, không cần MT5.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Ba module `gui_lenh` · `ket_noi` · `phien_live` là chỗ DUY NHẤT trong app chạm vào tiền
thật, và trước bài này chúng KHÔNG có một dòng test nào. Cổng kiểm trước khi đóng gói
(`tools\\dong_goi.bat` bước 3) vẫn báo "9/9 qua" kể cả khi bảng xử lý retcode bị bẻ hỏng
hoàn toàn — tức một bản phát hành biết đặt lệnh sai vẫn ra khỏi cửa.

Sàn giả ở đây nói dối ĐÚNG KIỂU sàn thật đã đo được:
  · khai `trade_stops_level = 0` nhưng ngưỡng thật là 215 điểm
  · khai nhận FOK nhưng chỉ nhận IOC
  · vị thế vừa mở thì ĐÓNG BĂNG một lúc (mã 10029)

BỐN THỨ ĐƯỢC CANH
-----------------
  1. **Mã THÀNH CÔNG không được đọc thành thất bại.** `10010` (khớp một phần) mà gửi
     lại là nhân đôi vị thế thật — đo được: xin 5 lot, bắn ra 15.
  2. **Mã LẠ trên lệnh thị trường thì DỪNG.** Không biết lệnh đã vào hay chưa mà gửi
     lại là đánh cược bằng tiền.
  3. **Vòng hiệu chuẩn không được nói dối.** Lượt vỡ giữa chừng phải ra `chua_hoi_tu`,
     không được ra `xong`.
  4. **Ý định phải thành hiện thực.** Sàn từ chối mà tầng phòng vệ chữa được thì vẫn
     là đạt; chỉ khi nó bó tay mới là hỏng.

Chạy:  python tests\\test_gui_lenh.py
"""
import io
import os
import sys
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# ---------------------------------------------------------------------------
# SÀN GIẢ
# ---------------------------------------------------------------------------
DONE = 10009
NGUONG = 215        # điểm — ngưỡng SL/TP THẬT, sàn không khai ra
FILL = 1            # chỉ nhận IOC
BANG = 0.6          # giây — vị thế mới mở còn đóng băng


class _O:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class SanGia(types.ModuleType):
    TRADE_ACTION_DEAL, TRADE_ACTION_PENDING = 1, 5
    TRADE_ACTION_SLTP, TRADE_ACTION_MODIFY, TRADE_ACTION_REMOVE = 6, 7, 8
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT = 2, 3
    ORDER_TIME_GTC = 0
    TRADE_RETCODE_DONE = DONE

    def __init__(self, kich_ban=()):
        super().__init__("MetaTrader5")
        self.gia = 4400.0
        self.vt, self.cho, self.da_gui = {}, {}, []
        self.dem = 1000
        self.kich_ban = list(kich_ban)
        self.noi = True
        #: Sàn LÀM THẬT rồi mới trả mã mờ — đúng cái xảy ra khi timeout/mất kết nối:
        #: yêu cầu tới nơi, khớp xong, chỉ có câu trả lời là lạc.
        self.khop_roi_moi_bao = False

    def initialize(self, *a, **k):
        return True

    def shutdown(self):
        pass

    def symbol_select(self, s, v=True):
        return True

    def terminal_info(self):
        return _O(connected=self.noi, trade_allowed=True)

    def account_info(self):
        return _O(login=1, server="Gia", company="San Gia", trade_mode=0,
                  margin_mode=2, trade_expert=True)

    def symbol_info(self, s):
        return _O(point=0.01, digits=2, trade_stops_level=0, trade_freeze_level=0,
                  volume_min=0.01, volume_max=100.0, volume_step=0.01,
                  filling_mode=1, trade_mode=4)

    def symbol_info_tick(self, s):
        if not self.noi:
            return None
        self.gia += 0.05
        return _O(time=int(time.time()), ask=self.gia + 0.15, bid=self.gia)

    def positions_get(self, symbol=None):
        return tuple(self.vt.values())

    def orders_get(self, symbol=None):
        return tuple(self.cho.values())

    def history_deals_get(self, a, b):
        return ()

    def copy_rates_from_pos(self, *a):
        return None

    def _lam_that(self, yc):
        """Khớp một lệnh thị trường như thường — nhưng người gọi sẽ KHÔNG biết."""
        if yc.get("action") == self.TRADE_ACTION_DEAL and "position" not in yc:
            self.dem += 1
            t = self.dem
            self.vt[t] = _O(ticket=t, type=yc["type"], price_open=float(yc["price"]),
                            volume=yc["volume"], magic=yc.get("magic", 0),
                            sl=0.0, tp=0.0, time=int(time.time()), _sinh=time.time())

    def order_send(self, yc):
        self.da_gui.append(dict(yc))
        if self.kich_ban:
            ma = self.kich_ban.pop(0)
            if ma:
                if self.khop_roi_moi_bao:
                    self._lam_that(yc)
                return _O(retcode=ma, order=0, price=0.0)
        if not self.noi:
            return _O(retcode=10031, order=0, price=0.0)
        act = yc.get("action")
        if act == self.TRADE_ACTION_DEAL and "position" not in yc:
            if yc.get("type_filling") != FILL:
                return _O(retcode=10030, order=0, price=0.0)
            mua = yc["type"] == self.ORDER_TYPE_BUY
            g = float(yc["price"]) + (0.5 if mua else -0.5)
            self.dem += 1
            t = self.dem
            self.vt[t] = _O(ticket=t, type=0 if mua else 1, price_open=g,
                            volume=yc["volume"], magic=yc.get("magic", 0),
                            sl=0.0, tp=0.0, time=int(time.time()), _sinh=time.time())
            return _O(retcode=DONE, order=t, price=g)
        if act == self.TRADE_ACTION_DEAL:
            p = self.vt.pop(int(yc["position"]), None)
            return _O(retcode=DONE if p else 10013, order=0, price=float(yc["price"]))
        if act == self.TRADE_ACTION_SLTP:
            p = self.vt.get(int(yc["position"]))
            if p is None:
                return _O(retcode=10013, order=0, price=0.0)
            if time.time() - p._sinh < BANG:
                return _O(retcode=10029, order=0, price=0.0)
            sl = float(yc.get("sl") or 0)
            if sl and abs(self.gia - sl) / 0.01 < NGUONG:
                return _O(retcode=10016, order=0, price=0.0)
            p.sl, p.tp = sl, float(yc.get("tp") or 0)
            return _O(retcode=DONE, order=int(p.ticket), price=0.0)
        if act == self.TRADE_ACTION_PENDING:
            self.dem += 1
            t = self.dem
            self.cho[t] = _O(ticket=t, type=yc["type"], price_open=yc["price"],
                             volume_initial=yc["volume"], magic=yc.get("magic", 0),
                             sl=0.0, tp=0.0, time_setup=int(time.time()))
            return _O(retcode=DONE, order=t, price=yc["price"])
        if act == self.TRADE_ACTION_MODIFY:
            o = self.cho.get(int(yc["order"]))
            if o is None:
                return _O(retcode=10035, order=0, price=0.0)
            o.price_open = yc["price"]
            return _O(retcode=DONE, order=o.ticket, price=yc["price"])
        if act == self.TRADE_ACTION_REMOVE:
            self.cho.pop(int(yc["order"]), None)
            return _O(retcode=DONE, order=0, price=0.0)
        return _O(retcode=10013, order=0, price=0.0)


def cam(kich_ban=(), tmp=None):
    """Cắm sàn giả vào ĐÚNG thuộc tính `mt5` của hai module.

    ⚠ Không `sys.modules.pop` rồi import lại: gói `cat_studio` vẫn giữ thuộc tính cũ
    nên lần import sau trả về đúng module cũ đang trỏ vào sàn giả của lần trước."""
    san = SanGia(kich_ban)
    sys.modules["MetaTrader5"] = san
    from cat_studio import nguon_nen as nn
    nn.CO_MT5 = True

    class _Gia:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    nn._KetNoi = _Gia
    from cat_studio import gui_lenh, ket_noi
    gui_lenh.mt5 = ket_noi.mt5 = san
    gui_lenh.CHUA_BIET.clear()
    if tmp:
        ket_noi._duong = lambda: os.path.join(tmp, "ho_so.json")
    return san, gui_lenh, ket_noi


def dem_deal(san):
    """Số lệnh THỊ TRƯỜNG (mở vị thế) thật sự bắn ra sàn."""
    return sum(1 for y in san.da_gui
               if y.get("action") == SanGia.TRADE_ACTION_DEAL and "position" not in y)


# ---------------------------------------------------------------------------
print("\n--- 1. Mã THÀNH CÔNG không được đọc thành thất bại ---")
# ⚠ Đây là lỗi đắt nhất từng tìm ra ở tầng này: `10010` = khớp MỘT PHẦN, lệnh ĐÃ vào
# sàn. Đọc thành "chưa xong" rồi gửi lại là nhân đôi vị thế THẬT.
san, gl, kn = cam(kich_ban=[10010, 10010])
bg = gl.gui("XAUUSD", True, 5.0, luat={"cho_ms": 1})
kiem("10010 (khớp một phần) là ĐẠT", bg["ket"] == "ok", f"ket={bg['ket']}")
kiem("chỉ bắn ra ĐÚNG MỘT lệnh thị trường", dem_deal(san) == 1,
     f"{dem_deal(san)} lệnh cho một ý định")

san, gl, kn = cam(kich_ban=[10008])
bg = gl.dat_cho("XAUUSD", True, 0.01, 4000.0, luat={"cho_ms": 1})
kiem("10008 (lệnh chờ đã đặt) là ĐẠT", bg["ket"] == "ok", f"ket={bg['ket']}")

print("\n--- 2. Mã LẠ: lệnh thị trường thì DỪNG, thao tác vô hại thì thử lại ---")
san, gl, kn = cam(kich_ban=[10999] * 6)
bg = gl.gui("XAUUSD", True, 0.01, luat={"thu_lai": 3, "cho_ms": 1})
kiem("mã lạ trên lệnh thị trường → dừng ngay",
     bg["ket"] == "bo" and dem_deal(san) == 1, f"{dem_deal(san)} lệnh bắn ra")
kiem("mã lạ vẫn chịu lộ mặt", 10999 in gl.CHUA_BIET and 10999 in bg["la"])

san, gl, kn = cam(kich_ban=[10999, 10999])
bg = gl.huy_cho("XAUUSD", 123, luat={"thu_lai": 3, "cho_ms": 1})
kiem("mã lạ trên thao tác VÔ HẠI thì vẫn thử lại", bg["so_lan"] > 1,
     f"thử {bg['so_lan']} lần")

print("\n--- 3. Sàn từ chối mà chữa được thì VẪN LÀ ĐẠT ---")
san, gl, kn = cam()
bg = gl.gui("XAUUSD", True, 0.01, magic=kn.MAGIC_KIEM, luat={"cho_ms": 1})
kiem("10030 filling — tự đổi rồi vào được",
     bg["ket"] == "ok" and bg["fill_dung"] == FILL, f"fill={bg['fill_dung']}")
pos = list(san.vt.values())[0]
bg2 = gl.sua_stops("XAUUSD", pos, san.gia - 1.0, None,
                   luat={"kep_stops": 260, "cho_bang_ms": 700, "cho_ms": 1})
kiem("10029 đóng băng — chờ tan rồi qua", bg2["ket"] == "ok", bg2["chu"])
kiem("SL bị KẸP ra xa theo ngưỡng đã cài", bool(bg2["sua_truoc"] or bg2["da_sua"]),
     str(bg2["sua_truoc"] or bg2["da_sua"]))

print("\n--- 4. Kẹp SL/TP theo GIÁ HIỆN TẠI, không theo giá mở ---")
# Mua ở giá thấp, giá đã chạy xa lên: kéo SL lên khoá lời KHÔNG được bị đẩy về sát giá vào.
san, gl, kn = cam()
san.gia = 4400.0
bg = gl.gui("XAUUSD", True, 0.01, luat={"cho_ms": 1})
pos = list(san.vt.values())[0]
vao = float(pos.price_open)
san.gia = vao + 100.0                       # giá chạy xa 10.000 điểm
san.da_gui.clear()
gl.sua_stops("XAUUSD", pos, vao + 95.0, None, luat={"kep_stops": 215, "cho_ms": 1})
sltp = [y for y in san.da_gui if y.get("action") == SanGia.TRADE_ACTION_SLTP]
kiem("SL khoá lời KHÔNG bị đẩy xuống dưới giá vào",
     bool(sltp) and float(sltp[-1]["sl"]) > vao,
     f"vào {vao:.2f} · gửi SL {float(sltp[-1]['sl']):.2f}" if sltp else "không gửi gì")

print("\n--- 5. `10036` / vị thế biến mất: đóng vẫn là ĐẠT ---")
san, gl, kn = cam()
gl.gui("XAUUSD", True, 0.01, luat={"cho_ms": 1})
pos = list(san.vt.values())[0]
kiem("đóng lần 1 đạt", gl.dong("XAUUSD", pos)["ket"] == "ok")
kiem("đóng lần 2 (đã đóng rồi) VẪN đạt", gl.dong("XAUUSD", pos)["ket"] == "ok")

print("\n--- 6. Lỗi CẦN NGƯỜI: dừng ngay, không thử lại ---")
san, gl, kn = cam(kich_ban=[10027] * 5)
bg = gl.gui("XAUUSD", True, 0.01, luat={"cho_ms": 1})
kiem("AlgoTrading tắt → 'nguoi', một lần thử",
     bg["ket"] == "nguoi" and bg["so_lan"] == 1, f"{bg['ket']}/{bg['so_lan']}")
kiem("nói rõ người phải làm gì", "AlgoTrading" in bg["chu"])

print("\n--- 7. Vòng hiệu chuẩn: chốt được, và KHÔNG nói dối ---")
import tempfile
san, gl, kn = cam(tmp=tempfile.mkdtemp())
kq = kn.hieu_chuan("XAUUSD", so_vong=2, nghi_giay=0, lap_toi_da=4)
kiem("chốt xong", kq["trang_thai"] == "xong", kq["trang_thai"])
kiem("không còn bước hỏng nào ở lượt cuối",
     kq["cuoi"]["dem"].get("hong", 0) == 0, str(kq["cuoi"]["dem"]))
kiem("đo được ngưỡng SL/TP thật (~215)",
     kq["stops_level_that"] and 150 <= kq["stops_level_that"] <= 320,
     str(kq["stops_level_that"]))
kiem("kẹp cài ra XA HƠN ngưỡng đo được",
     (kq["luat"]["kep_stops"] or 0) > (kq["stops_level_that"] or 0),
     f"kẹp {kq['luat']['kep_stops']} / ngưỡng {kq['stops_level_that']}")
kiem("học được kiểu khớp sàn thật sự nhận", kq["luat"]["filling"] == FILL,
     str(kq["luat"]["filling"]))
kiem("dọn sạch, không để lại rác", not san.vt and not san.cho,
     f"vt={len(san.vt)} chờ={len(san.cho)}")

print("\n--- 8. Lượt VỠ giữa chừng KHÔNG được báo 'xong' ---")
# ⚠ Đây là lời nói dối trấn an: lượt chưa chạy hết thì không có bước nào 'hỏng', nên
# mọi dấu hiệu đều đẹp và vòng lặp tuyên bố đã chốt — trong khi 6/7 thao tác chạm sàn
# chưa bao giờ được thử.
san, gl, kn = cam(tmp=tempfile.mkdtemp())
lan = {"n": 0}
that_su = san.positions_get


def no_giua(symbol=None):
    """Cầu nối đứt giữa lượt — đúng cảnh 'bài kiểm đứt vì mất cầu nối' đã gặp thật."""
    lan["n"] += 1
    if lan["n"] >= 3:
        raise RuntimeError("cầu nối đứt giữa chừng")
    return that_su(symbol=symbol)


san.positions_get = no_giua
kq = kn.hieu_chuan("XAUUSD", so_vong=3, nghi_giay=0, lap_toi_da=4)
san.positions_get = that_su
kiem("lượt vỡ → KHÔNG phải 'xong'", kq["trang_thai"] != "xong", kq["trang_thai"])
kiem("và nói rõ là vỡ giữa chừng", "VỠ GIỮA CHỪNG" in kq["chu"], kq["chu"][:70])

# Còn `tien_do` (thanh tiến độ do cửa sổ truyền vào) thì NGƯỢC LẠI: nó ném cũng không
# được phép giết một lượt đang đặt lệnh thật.
san, gl, kn = cam(tmp=tempfile.mkdtemp())


def tien_do_hong(*a):
    raise ValueError("cửa sổ đã đóng")


kq = kn.hieu_chuan("XAUUSD", so_vong=2, nghi_giay=0, lap_toi_da=4,
                   tien_do=tien_do_hong)
kiem("thanh tiến độ hỏng KHÔNG giết được lượt", kq["trang_thai"] == "xong",
     kq["trang_thai"])

print("\n--- 9. `_suy_chinh` không được tụt xuống dưới phép đo ---")
L = dict(gl.LUAT_MAC_DINH, kep_stops=100)
moi, _, _ = kn._suy_chinh({"stops_level_that": 300, "ma_hong": [10016],
                           "dem": {"hong": 1}}, L)
kiem("gặp 10016 vẫn phải ≥ ngưỡng đo × biên",
     moi.get("kep_stops", 0) >= 300 * kn.BIEN_KEP,
     f"đo 300 → cài {moi.get('kep_stops')}")

print("\n--- 10. Dọn rác hỏng thì phải KÊU ---")
san, gl, kn = cam()
gl.gui("XAUUSD", True, 0.01, magic=kn.MAGIC_KIEM, luat={"cho_ms": 1})
san.kich_ban = [10045] * 8              # FIFO → 'dung', không đóng được
d = kn.don_rac("XAUUSD")
kiem("đóng không được thì ghi lại", bool(d["khong_don_duoc"]), str(d["khong_don_duoc"]))
kiem("và nói thẳng còn sót", "CÒN SÓT" in d["chu"], d["chu"])

print("\n--- 11. MÃ MỜ NGHĨA trên lệnh thị trường: thà bỏ lỡ còn hơn mở HAI ---")
#
# Sàn khớp THẬT rồi trả 10012 (timeout). Người gọi không biết lệnh đã vào hay chưa. Vòng
# thử mà gửi lại thì MỘT ý định ra HAI vị thế — mất tiền thật, và ticket đầu không ai
# đối chiếu. Luật bất đối xứng vốn đã có cho MÃ LẠ; đây là áp nốt cho nhóm mã mờ nghĩa.
for _ma in (10012, 10031, 10011, 10023):
    san, gl, _ = cam([_ma] * 6)
    san.khop_roi_moi_bao = True
    _bg = gl.gui("XAUUSD", True, 0.10, luat={"cho_ms": 1, "cho_noi_giay": 0})
    kiem(f"mã {_ma}: sàn khớp rồi báo mờ → CHỈ MỘT vị thế",
         len(san.vt) == 1, f"— {len(san.vt)} vị thế / gửi {len(san.da_gui)} lần")
    kiem(f"mã {_ma}: bản ghi nói rõ vì sao dừng",
         _bg["ket"] == "bo" and "không nói được" in _bg["chu"], f"— {_bg['chu'][:55]}")

# Chiều ngược lại: SỬA SL/TP gửi lại là VÔ HẠI, nên vẫn phải thử lại.
san, gl, _ = cam([10012, 10012])
san.vt[1] = _O(ticket=1, type=0, price_open=4400.0, volume=0.1, sl=0.0, tp=0.0,
               magic=0, time=int(time.time()), _sinh=time.time())
_bg2 = gl.sua_stops("XAUUSD", 1, sl=4390.0, luat={"cho_ms": 1})
kiem("sửa SL/TP gặp mã mờ thì VẪN thử lại (thao tác bất biến)",
     _bg2["so_lan"] >= 2, f"— thử {_bg2['so_lan']} lần")

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
