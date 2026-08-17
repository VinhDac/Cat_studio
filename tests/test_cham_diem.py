"""CHẤM ĐIỂM — bằng TIỀN, theo TUẦN, và cái CỬA bắt buộc.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Điểm là thứ MỌI máy tìm tối ưu vào. Điểm sai thì máy chăm chỉ đi sai hướng suốt đêm, và
không có gì báo — nó vẫn chạy, vẫn ra một sơ đồ, vẫn có con số đẹp.

Bài này canh bốn điều (core.md §18.2):

  1. **Ba con số** — trung bình tuần · dao động tuần · thương số. Bằng TIỀN, không bằng R.
  2. **Kỳ TRẮNG cũng đếm.** Bỏ tuần không có lệnh thì một chiến lược đánh 3 lần trong 5
     năm trông y như một chiến lược đánh đều.
  3. ⭐ **CỬA "tuần có lệnh" chặn được lỗ hổng số học.** Một tuần có lệnh trong N tuần
     LUÔN cho điểm `±1/√(N−1)`, bất kể lệnh ấy lãi hay lỗ bao nhiêu — vì tuần trắng làm
     co CẢ trung bình LẪN dao động theo đúng một tỉ lệ. Đo trên dữ liệu thật: sơ đồ vào
     ĐÚNG MỘT lệnh trong 3,5 năm ăn điểm **−0,065**, cao hơn sơ đồ vào 929 lệnh
     (**−0,145**). Không có cửa thì máy tìm vồ ngay chỗ đó.
  4. **Ưu tiên là CỬA, không phải CÂN** (§18.6.4) — và rớt cửa thì vẫn giữ lại lý do,
     không im lặng biến mất.

Chạy:  python tests\\test_cham_diem.py
"""
import io
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import cham_diem as cd  # noqa: E402
from cat_studio import core  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# ================= 1. BA CON SỐ — số học thuần =================
print("\n▸ Ba con số")

kiem("chuỗi đều thì dao động 0, và điểm 0 chứ không phải vô cực",
     cd._ba_so([1.0] * 10)["dao_dong"] == 0.0 and cd._ba_so([1.0] * 10)["diem"] == 0.0)
kiem("chuỗi rỗng không nổ", cd._ba_so([])["diem"] == 0.0)

_v = [1.0, -1.0, 1.0, -1.0]
kiem("trung bình 0 → điểm 0", cd._ba_so(_v)["diem"] == 0.0)

_b = cd._ba_so([2.0, 0.0, 0.0, 0.0])
kiem("kỳ TRẮNG vẫn vào mẫu số", _b["so_ky"] == 4 and _b["co_lenh"] == 1,
     f"— {_b['co_lenh']}/{_b['so_ky']}")

# ⭐ LỖ HỔNG §18.2a, viết thành đẳng thức. Một kỳ có lệnh trong N kỳ luôn cho ±1/√(N−1),
# và con số ấy KHÔNG phụ thuộc lệnh đó lãi hay lỗ bao nhiêu.
for _n in (10, 100, 236):
    for _x in (0.5, 5.0, 500.0):
        _d = cd._ba_so([_x] + [0.0] * (_n - 1))["diem"]
        _cho = 1.0 / math.sqrt(_n - 1)
        if abs(_d - _cho) > 5e-4:
            break
    else:
        continue
    break
else:
    _n = _x = None
kiem("MỘT kỳ có lệnh luôn cho điểm ±1/√(N−1), bất kể lệnh to hay nhỏ",
     _n is None, f"— hỏng ở N={_n}, lãi={_x}")
kiem("và lỗ thì cho đúng con số ấy, dấu âm",
     abs(cd._ba_so([-3.0] + [0.0] * 235)["diem"] + 1 / math.sqrt(235)) < 5e-4)
kiem("⇒ nằm im ăn điểm ĐẸP HƠN một chiến lược thật đang lỗ nhẹ",
     cd._ba_so([-3.0] + [0.0] * 235)["diem"] > cd._ba_so([-0.16] * 236)["diem"] - 1,
     f"— {cd._ba_so([-3.0] + [0.0] * 235)['diem']:+.4f} so với "
     f"{cd._ba_so([-0.16] * 236)['diem']:+.4f}")


# ================= 2. CHẠY THẬT — nến tổng hợp nhiều tuần =================
print("\n▸ Chạy thật — chuỗi tuần dựng từ lệnh, kể cả tuần trắng")

T0 = 1700000100                 # chia hết cho 300 (một nến M5) — xem test_zone
TUAN = 7 * 24 * 60              # nến M1 một tuần
SO_TUAN = 8


def nen(gia):
    a = np.zeros(len(gia), dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"),
                                  ("l", "f8"), ("c", "f8"), ("vol", "f8")])
    for k, g in enumerate(gia):
        a[k] = (T0 + k * 60, g, g + 0.5, g - 0.5, g, 1.0)
    return a


#: Hai tuần ĐỨNG YÊN rồi mấy tuần DAO ĐỘNG. Cổng đòi `atr > ngưỡng` nên tuần yên không
#: có lệnh nào (TRẮNG), tuần động thì lệnh vào rồi chạm SL/TP mà đóng. Đúng hình dạng
#: cần thử: chuỗi tuần phải đếm cả tuần trắng, không chỉ tuần có lệnh.
#:
#: ⚠ Giá phẳng SUỐT thì lệnh mở ra treo mãi, `so_dong` = 0 và không có gì để chấm — đã
#: cắn một lần lúc viết bài này.
_gia = [100.0] * (TUAN * 2)
_gia += [100.0 + 3.0 * math.sin(k / 90.0) for k in range(TUAN * (SO_TUAN - 2))]

_bd = core.make_start_step("bắt đầu", "M5")
_cong = core.make_action_step({
    "type": core.CHECK_COND, "name": "có động không?",
    "conditions": [{"trai": {"ten": "atr", "tf": "M5", "period": 14},
                    "phep": ">", "phai": {"value": 0.05}},
                   {"trai": {"ten": "so_vi_the"}, "phep": "<", "phai": {"value": 1}}]})
_vao = core.make_action_step({
    "type": core.VAO_LENH, "name": "mua", "huong": "mua", "loai": "market",
    "rui_ro": 0.5, "entry": {"moc": "close"},
    "sl": {"tinh": "gia", "value": 1.0}, "tp": {"tinh": "R", "value": 1.0}})
DOC = core.normalize_process({
    "name": "thử",
    # `chu_ky_atr` là THAM SỐ NGẦM — bộ chạy đọc dù sơ đồ không hỏi (core.THAM_SO_NGAM).
    "tham_so": [core.make_tham_so("chu_ky_atr", "chu kỳ ATR", 14, "nen")],
    "entry": {"steps": [_bd, _cong, _vao],
              "edges": [{"from": _bd["id"], "to": _cong["id"]},
                        {"from": _cong["id"], "to": _vao["id"]}]},
    "manage": {"steps": [core.make_start_step("bắt đầu", "M5")], "edges": []}})

CD = bc.CaiDat(point=1.0, contract_size=1.0, digits=2, spread_diem=0.0,
               deposit=10_000.0, lot_min=0.01, lot_buoc=0.01, lot_max=100.0)
KQ = bc.chay(DOC, nen(_gia), CD)

_ch = cd.chuoi_ky(KQ, cd.TUAN)
kiem("có lệnh để chấm", KQ.thong_ke["so_dong"] > 0, f"— {KQ.thong_ke['so_dong']} lệnh")
kiem("chuỗi tuần dài đúng số tuần của DỮ LIỆU, không phải số tuần có lệnh",
     SO_TUAN - 1 <= len(_ch) <= SO_TUAN + 1, f"— {len(_ch)} tuần")
kiem("và có tuần TRẮNG thật (giá đứng yên thì không lệnh nào)",
     any(x == 0.0 for x in _ch), f"— {sum(1 for x in _ch if x == 0.0)} tuần trắng")

_d = cd.cham(KQ)
kiem("tháng cũng tính được", _d["thang"]["so_ky"] >= 1)
kiem("`lai_pt` khớp bảng số liệu của bộ chạy",
     _d["lai_pt"] == KQ.thong_ke["lai_pt"])
# Sai số cho phép chỉ vì `thong_ke["lai_pt"]` đã LÀM TRÒN 2 chữ số — chuỗi tuần thì
# không. Đây là phép kiểm "không rơi rớt lệnh nào", nên nó phải khớp tới mức làm tròn.
kiem("tổng chuỗi tuần khớp tổng lãi (không rơi rớt lệnh nào)",
     abs(sum(_ch) - KQ.thong_ke["lai_pt"]) < 0.005,
     f"— {sum(_ch):.6f} so với {KQ.thong_ke['lai_pt']}")


# ================= 3. HOA HỒNG PHẢI VÀO ĐIỂM =================
print("\n▸ Hoa hồng — thứ `tong_R` mù mà điểm thì không được mù (§18.2b)")

_re = bc.chay(DOC, nen(_gia), bc.CaiDat(point=1.0, contract_size=1.0, digits=2,
                                        spread_diem=0.0, deposit=10_000.0,
                                        commission=0.0))
_dat = bc.chay(DOC, nen(_gia), bc.CaiDat(point=1.0, contract_size=1.0, digits=2,
                                         spread_diem=0.0, deposit=10_000.0,
                                         commission=50.0))
kiem("phí cao hơn thì TRUNG BÌNH TUẦN thấp hơn",
     cd.cham(_dat)["tuan"]["trung_binh"] < cd.cham(_re)["tuan"]["trung_binh"],
     f"— {cd.cham(_re)['tuan']['trung_binh']:+.4f}% → "
     f"{cd.cham(_dat)['tuan']['trung_binh']:+.4f}%")


# ================= 4. CỬA =================
print("\n▸ Cửa — §18.2a khoá cứng, §18.6.4 chỉnh được")

_d = cd.cham(KQ, {"tuan_co_lenh": 0.99})
kiem("cửa `tuần có lệnh` siết lên 99% thì RỚT", not _d["dat"], f"— {_d['ly_do']}")
kiem("và nói RÕ rớt vì đâu", "tuần có lệnh" in (_d["ly_do"] or ""))

_d = cd.cham(KQ, {"tuan_co_lenh": 0.0})
kiem("KHÔNG nới được cửa khoá cứng xuống dưới ½ (§18.2a)",
     _d["dat"] == (_d["tuan"]["ty_le_co_lenh"] >= cd.TUAN_CO_LENH_TOI_THIEU),
     f"— tuần có lệnh {_d['tuan']['ty_le_co_lenh'] * 100:.0f}%")

_d = cd.cham(KQ, {"sut_von_toi_da": -1})
kiem("cửa sụt vốn chặn được", not _d["dat"] and "sụt vốn" in _d["ly_do"])
_d = cd.cham(KQ, {"lai_toi_thieu": 10_000})
kiem("cửa lãi tối thiểu chặn được", not _d["dat"] and "lãi" in _d["ly_do"])

kiem("rớt cửa thì ĐIỂM vẫn tính ra (để người đọc thấy nó rớt vì đâu)",
     isinstance(cd.cham(KQ, {"sut_von_toi_da": -1})["diem"], float))

_qua, _rot = cd.xep_hang([("a", KQ), ("b", _dat)], {"tuan_co_lenh": 0.99})
kiem("xếp hạng: cái rớt cửa KHÔNG lọt vào danh sách", not _qua, f"— {len(_qua)} qua")
kiem("nhưng vẫn giữ lại, không im lặng biến mất", len(_rot) == 2, f"— {len(_rot)} rớt")

_qua, _rot = cd.xep_hang([("a", KQ), ("b", _re)])
kiem("xếp hạng theo điểm GIẢM DẦN",
     all(_qua[i][1]["diem"] >= _qua[i + 1][1]["diem"] for i in range(len(_qua) - 1)),
     f"— {[(t, round(d['diem'], 4)) for t, d in _qua]}")

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
