"""MỘT LƯỢT TÌM — sống NGOÀI cửa sổ, dừng được, không chết im lặng.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
§18.6.2 chốt: **máy tìm không sống trong cửa sổ**. Một lượt chạy mất cả đêm; đóng cửa sổ
RL để mở một sơ đồ ra ngắm mà giết luôn sáu tiếng đã chạy là hỏng. Đây đúng là món nợ
§14.4 (*"đóng cửa sổ Live là dừng phiên"*) — chỗ này phải làm đúng ngay từ đầu.

Bài này canh bốn điều:

  1. ⭐ **Sổ lượt chạy nằm ở mức MODULE.** `Api` bị dựng lại mỗi lần mở cửa sổ; module
     sống theo tiến trình. Giữ lượt trên `Api` là lặp lại đúng món nợ cũ.
  2. **Dừng được từ ngoài**, và dừng rồi thì kết quả tới lúc đó vẫn dùng được.
  3. **Nổ thì NÓI TO.** Luồng nền chết im lặng là cửa sổ quay mãi thanh tiến trình mà
     không ai hiểu vì sao.
  4. **Dọn sổ không được dọn nhầm lượt ĐANG CHẠY** — dọn nó là mất cách dừng nó, mà
     luồng thì vẫn chạy tiếp: một lượt chạy MA.

Chạy:  python tests\\test_luot_tim.py
"""
import io
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import luot_tim as lt  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def cho(l, giay=60):
    t0 = time.time()
    while l.dang_chay() and time.time() - t0 < giay:
        time.sleep(0.02)
    return not l.dang_chay()


T0, TUAN = 1700000100, 7 * 24 * 60
_N = TUAN * 3
_gia = [100.0 + 4.0 * math.sin(k / 800.0) + 1.2 * math.sin(k / 70.0)
        for k in range(_N)]
NEN = np.zeros(_N, dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"), ("l", "f8"),
                          ("c", "f8"), ("vol", "f8")])
for _k, _x in enumerate(_gia):
    NEN[_k] = (T0 + _k * 60, _x, _x + 0.4, _x - 0.4, _x, 1.0)
CD = bc.CaiDat(point=1.0, contract_size=1.0, digits=2, spread_diem=0.2,
               commission=0.5, deposit=10_000.0, lot_min=0.01, lot_buoc=0.01,
               lot_max=50.0)


# ================= 1. CHẠY NỀN, HỎI ĐƯỢC TIẾN ĐỘ =================
print("\n▸ Chạy nền — trả về NGAY, tiến độ hỏi sau")

_t0 = time.time()
L = lt.bat_dau(NEN, CD, 8, ten="thử", hat=2026)
_tra_ve = time.time() - _t0
kiem("`bat_dau` trả về ngay, không chờ chạy xong", _tra_ve < 0.5,
     f"— {_tra_ve * 1000:.0f} ms")
kiem("và báo là đang chạy", L.trang_thai()["dang_chay"])
kiem("biết tổng số lượt phải chấm", L.trang_thai()["tong"] == 8)
kiem("chưa xong thì chưa có kết quả", L.ket_qua() is None)
kiem("mã lượt có hình dạng nhận ra được", L.ma.startswith("L-"), f"— {L.ma}")

_tt = L.trang_thai()
_tt["da_chay"] = 999_999
kiem("`trang_thai` trả BẢN SAO — giao diện không ghi được vào ruột lượt chạy",
     L.trang_thai()["da_chay"] != 999_999)

kiem("chạy xong trong thời gian chờ", cho(L))
_tt = L.trang_thai()
kiem("xong thì tắt cờ đang chạy", not _tt["dang_chay"])
kiem("và đóng dấu thời điểm xong", _tt["xong_luc"] is not None)
kiem("không nổ", _tt["loi"] is None, f"— {_tt['loi']}")
kiem("có bảng thống kê", _tt["thong_ke"] and _tt["thong_ke"]["da_chay"] == 8,
     f"— {_tt['thong_ke'] and _tt['thong_ke']['da_chay']}")
kiem("có kết quả để lấy", L.ket_qua() is not None)


# ================= 2. SỔ NẰM Ở MỨC MODULE =================
print("\n▸ Sổ ở mức MODULE — lượt chạy sống khi cửa sổ đóng (§18.6.2)")

kiem("tra lại được bằng mã, không cần giữ tham chiếu nào",
     lt.lay(L.ma) is L)
kiem("và có mặt trong danh sách",
     any(x["ma"] == L.ma for x in lt.danh_sach()))

# ⭐ Đây là phép thử của cả mục: VỨT mọi tham chiếu — đúng như khi cửa sổ đóng và `Api`
# bị dọn. Lượt chạy phải vẫn còn đó.
_ma = L.ma
del L
import gc  # noqa: E402

gc.collect()
kiem("VỨT hết tham chiếu (cửa sổ đóng) — lượt chạy VẪN CÒN",
     lt.lay(_ma) is not None)
kiem("và vẫn lấy được kết quả của nó", lt.lay(_ma).ket_qua() is not None)


# ================= 3. DỪNG TỪ NGOÀI =================
print("\n▸ Dừng từ ngoài")

L2 = lt.bat_dau(NEN, CD, 200, ten="dừng giữa chừng", hat=5)
time.sleep(0.05)
L2.dung()
kiem("dừng thì lượt kết thúc sớm", cho(L2, 90))
_tt = L2.trang_thai()
kiem("và ĐÁNH DẤU là dừng giữa chừng, không giả vờ đã xong",
     _tt["dung_giua_chung"])
kiem("chấm ít hơn hẳn số đã xin", _tt["thong_ke"]["da_chay"] < 200,
     f"— {_tt['thong_ke']['da_chay']}/200")
kiem("dừng rồi thì kết quả tới lúc đó VẪN dùng được", L2.ket_qua() is not None)


# ================= 4. NỔ THÌ NÓI TO =================
print("\n▸ Nổ thì nói to, không chết im lặng")

# ⚠ `nen=None` là kiểu hỏng KHÔNG phải `LoiChay`, nên `tim_kiem` không nuốt được — nó
# thoát lên tận luồng nền. Đó đúng là đường phải thử: `LoiChay` thì đã có chỗ đếm rồi.
L3 = lt.bat_dau(None, CD, 3, ten="hỏng")
kiem("luồng nền chết mà vẫn kết thúc (không treo)", cho(L3, 60))
_tt = L3.trang_thai()
kiem("cờ đang chạy vẫn được tắt", not _tt["dang_chay"])
kiem("và LÝ DO nằm ngay trong trạng thái, không nuốt lặng",
     bool(_tt["loi"]), f"— {(_tt['loi'] or '(trống)')[:70]}")
kiem("nổ thì không có kết quả giả", L3.ket_qua() is None and L3.tom_tat() == [])

# `LoiChay` thì NGƯỢC LẠI: đó là một sơ đồ hỏng, không phải lượt tìm hỏng — đếm rồi
# chạy tiếp, chứ không giết cả lượt.
_rong = np.zeros(0, dtype=NEN.dtype)
L3b = lt.bat_dau(_rong, CD, 3, ten="nến rỗng")
cho(L3b, 60)
_tt = L3b.trang_thai()
kiem("sơ đồ chạy không được thì ĐẾM, không giết cả lượt",
     _tt["loi"] is None and _tt["thong_ke"] and _tt["thong_ke"]["no"] == 3,
     f"— nổ {_tt['thong_ke'] and _tt['thong_ke']['no']}/3")


# ================= 5. KẾT QUẢ ĐỌC ĐƯỢC =================
print("\n▸ Kết quả — tóm tắt JSON thuần, sơ đồ là file BÌNH THƯỜNG")

_L = lt.lay(_ma)
_tt = _L.tom_tat()
kiem("tóm tắt là JSON thuần (không kèm `KetQua` nặng)",
     all(isinstance(x, dict) and "diem" in x and "tuan" in x for x in _tt),
     f"— {len(_tt)} mục")
if _tt:
    kiem("xếp hạng bắt đầu từ 1", _tt[0]["hang"] == 1)
    _d = _L.so_do(1)
    kiem("lấy được sơ đồ đầu bảng", _d is not None)
    kiem("và nó là file chiến lược BÌNH THƯỜNG — soát tĩnh sạch",
         not core.validate_process(_d))
    kiem("mở lại bằng `normalize_process` không đổi gì",
         core.normalize_process(_d) == _d)
else:
    print("  … lượt này không sơ đồ nào qua cửa — bỏ qua ba phép kiểm kết quả")
kiem("xin hạng không tồn tại thì trả None, không nổ",
     _L.so_do(0) is None and _L.so_do(9999) is None)


# ================= 6. ĐƯỜNG ĐIỂM TỐT NHẤT =================
print("\n▸ Đường điểm tốt nhất — chỉ ghi BẬC, không ghi từng lượt")

# Gọi thẳng `_nhip` chứ không chạy 10.000 backtest: phép ghi đường là một luật thuần
# tuý, và thử nó bằng một lượt tìm thật thì vừa chậm vừa phụ thuộc may rủi (đo được:
# 37 lượt trên 6 tuần nến mất 15 phút và KHÔNG sơ đồ nào qua cửa, nên đường rỗng và
# bài kiểm chẳng kiểm được gì).
def _qua(diem):
    """Nhóm đầu bảng giả — đúng hình dạng `(tài liệu, chuỗi, bảng điểm)` mà
    `tim_kiem` đưa sang, chỉ giữ đúng khoá `_nhip` đọc tới."""
    return [] if diem is None else [({"name": "x"}, [1, 2], {
        "diem": diem, "so_lenh": 7, "sut_von_pt": 3.0, "lai_pt": 1.0, "ky": "tuan",
        "tuan": {"trung_binh": 0.1, "dao_dong": 0.5, "co_lenh": 4, "so_ky": 6},
        "thang": {"trung_binh": 0.4, "dao_dong": 0.9, "co_lenh": 1, "so_ky": 2}})]


_L6 = lt.LuotTim("đường")
for _da, _tot in [(1, None), (2, None), (3, -0.5), (4, -0.5), (5, -0.5),
                  (6, -0.2), (7, -0.2), (8, 0.3), (9, 0.3), (10, 0.3)]:
    _L6._nhip(_da, 10, _qua(_tot))
_d = _L6.trang_thai()["duong"]
kiem("chỉ ghi khi điểm ĐỔI, không ghi từng lượt", len(_d) == 3,
     f"— {len(_d)} bậc cho 10 lượt: {_d}")
kiem("mỗi bậc ghi đúng lượt nó xảy ra", [x[0] for x in _d] == [3, 6, 8],
     f"— {[x[0] for x in _d]}")
kiem("KHÔNG ghi gì khi chưa sơ đồ nào qua cửa (điểm còn `None`)",
     all(x[0] >= 3 for x in _d))
kiem("điểm tốt nhất chỉ TĂNG — nên đường là hàm bậc thang, vẽ được bằng H rồi V",
     all(_d[i][1] < _d[i + 1][1] for i in range(len(_d) - 1)))
kiem("`trang_thai` trả BẢN SAO của đường, không phải chính nó",
     _L6.trang_thai()["duong"] is not _L6.trang_thai()["duong"])
_cop = _L6.trang_thai()["duong"]
_cop.append([99, 99])
kiem("nên giao diện có nghịch bản sao cũng không đụng được ruột",
     len(_L6.trang_thai()["duong"]) == 3)

_L7 = lt.LuotTim("rỗng")
_L7._nhip(5, 10, [])
kiem("không sơ đồ nào qua cửa thì đường RỖNG (giao diện nói đúng câu đó)",
     _L7.trang_thai()["duong"] == [])

# ⭐ ĐANG CHẠY đã thấy kết quả — không đợi `_kq`. Đây là chỗ khiến bàn điều khiển sống:
# chạy tám tiếng thì tám tiếng nhìn thấy nhóm đầu bảng lớn dần, mở sơ đồ được giữa chừng.
kiem("nhóm đầu bảng đọc được NGAY GIỮA CHỪNG, không đợi chạy xong",
     _L6.ket_qua() is None and len(_L6.tom_tat()) == 1,
     f"— _kq={_L6.ket_qua()} · {len(_L6.tom_tat())} dòng")
kiem("và mở được sơ đồ giữa chừng", _L6.so_do(1) is not None)
_tt6 = _L6.trang_thai()
kiem("có ước lượng còn bao lâu", _tt6.get("con_lai") is not None
     and _tt6.get("giay_moi_luot") is not None,
     f"— còn {_tt6.get('con_lai')}s · {_tt6.get('giay_moi_luot')}s/sơ đồ")

_L6.dung()
kiem("bấm Dừng thì NÓI RA là đang chấm nốt, không để nút câm",
     "dừng" in (_L6.trang_thai().get("chu") or "").lower(),
     f"— «{_L6.trang_thai().get('chu')}»")

# Và trên một lượt THẬT: điểm cuối đường phải bằng điểm tốt nhất đang báo.
_L8 = lt.bat_dau(NEN, CD, 6, ten="đường thật", hat=2026, cua={})
cho(_L8, 300)
_tt8 = _L8.trang_thai()
kiem("lượt thật: bậc cuối khớp `diem_tot_nhat` đang báo",
     (not _tt8["duong"] and _tt8["diem_tot_nhat"] is None)
     or (_tt8["duong"] and abs(_tt8["duong"][-1][1] - _tt8["diem_tot_nhat"]) < 1e-9),
     f"— {len(_tt8['duong'])} bậc, tốt nhất {_tt8['diem_tot_nhat']}")
kiem("và mọi bậc đều nằm trong số lượt đã chấm",
     all(1 <= x[0] <= _tt8["da_chay"] for x in _tt8["duong"]),
     f"— {_tt8['duong']}")


# ================= 7. DỌN SỔ =================
print("\n▸ Dọn sổ — không được dọn nhầm lượt ĐANG CHẠY")

L4 = lt.bat_dau(NEN, CD, 300, ten="còn chạy", hat=11)
kiem("KHÔNG xoá được lượt đang chạy", not lt.xoa(L4.ma))
L4.dung()
cho(L4, 90)
kiem("dừng rồi thì xoá được", lt.xoa(L4.ma))
kiem("xoá rồi thì tra không thấy nữa", lt.lay(L4.ma) is None)
kiem("xoá mã không có thì trả False, không nổ", not lt.xoa("L-khong-co"))

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
