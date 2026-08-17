"""DÒ NGẪU NHIÊN — vòng tìm đơn giản nhất, và là ĐỐI CHỨNG.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
§18.5 chốt là **chưa chốt** cách tìm. Dò ngẫu nhiên không phải "thuật toán đã chọn" — nó
là cái mốc mà mọi cách tìm sau phải thắng. Mốc mà sai thì mọi so sánh về sau đều vô nghĩa,
và cái sai ấy không bao giờ tự lộ ra: vòng tìm vẫn chạy, vẫn ra một danh sách.

Bài này canh năm điều (core.md §18.5, §18.8):

  1. ⭐ **Bốc HAI TẦNG, không bốc đều từng ô.** Kho nước đi lệch nặng — `vao_lenh` chiếm
     1.050/1.863 ô (56 %), `het` đúng 1 ô. Bốc đều từng ô thì "ngẫu nhiên" hoá ra là một
     thiên kiến rất mạnh mà không ai khai.
  2. **Tái lập được.** Cùng hạt giống = cùng kết quả. Không thì "A hơn B" là câu không
     kiểm được.
  3. **Không lượt nào KẸT** — hồi quy cho lỗi `mo_nhanh` hai lần ở cùng chỗ rẽ (80/150
     lượt chết).
  4. **Không lượt nào làm bộ chạy NỔ** — hồi quy cho vòng tròn `zone_hop_le` (tràn ngăn
     xếp, sập cả lượt tìm).
  5. **Rớt cửa thì GIỮ LẠI kèm lý do**, không im lặng biến mất.

Chạy:  python tests\\test_tim_kiem.py
"""
import io
import math
import os
import random
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import nguoi_bay as nb  # noqa: E402
from cat_studio import tim_kiem as tk  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# ================= 1. BỐC HAI TẦNG =================
print("\n▸ Bốc hai tầng — 'đều' trong kho KHÔNG phải 'đều' giữa các lựa chọn")

_kho = Counter(n[0] for n in nb.KHO_NUOC_DI)
kiem("kho nước đi LỆCH thật (nên chuyện này đáng canh)",
     _kho["vao_lenh"] / len(nb.KHO_NUOC_DI) > 0.4,
     f"— vao_lenh {_kho['vao_lenh'] * 100 // len(nb.KHO_NUOC_DI)}% kho, `het` 1 ô")


def di(rng, hai_tang, so_luot=30):
    dem = Counter()
    for _ in range(so_luot):
        b = nb.Ban()
        for _ in range(tk.TRAN_NUOC):
            if b.xong:
                break
            mn = nb.mat_na(b)
            duoc = [i for i, x in enumerate(mn) if x]
            if not duoc:
                break
            if hai_tang:
                tl = {}
                for i in duoc:
                    tl.setdefault(nb.KHO_NUOC_DI[i][0], []).append(i)
                i = rng.choice(tl[rng.choice(sorted(tl))])
            else:
                i = rng.choice(duoc)
            dem[nb.KHO_NUOC_DI[i][0]] += 1
            b.di(i)
    return dem


_deu = di(random.Random(7), False)
_hai = di(random.Random(7), True)
_p_deu = max(_deu.values()) / sum(_deu.values())
_p_hai = max(_hai.values()) / sum(_hai.values())
kiem("hai tầng thì KHÔNG loại nào áp đảo", _p_hai < _p_deu,
     f"— loại đông nhất {_p_hai * 100:.0f}% (bốc đều: {_p_deu * 100:.0f}%)")


# ================= 2. HỒI QUY — hai ngõ cụt đã cắn =================
print("\n▸ Hồi quy — hai chỗ đã làm sập vòng tìm")

_b = nb.Ban()
_b.di(next(i for i, n in enumerate(nb.KHO_NUOC_DI)
           if n[0] == "dk_so" and n[1] == "so_vi_the"))
_b.di(nb.CHI_SO[("mo_nhanh",)])
kiem("KHÔNG mở nhánh khi nhánh hiện tại còn RỖNG "
     "(hai `mo_nhanh` liên tiếp ⇒ ngõ cụt vĩnh viễn)",
     not nb.mat_na(_b)[nb.CHI_SO[("mo_nhanh",)]])

_z = nb.Ban()
_z.di(nb.CHI_SO[("cong_zone",)])
kiem("cổng ZONE không hỏi được `zone_hop_le` ở phần ĐẾM (vòng tròn)",
     not any(nb.mat_na(_z)[i] for i, n in enumerate(nb.KHO_NUOC_DI)
             if n[0] == "dk_ds" and n[1] == "zone_hop_le"))
_z.di(next(i for i, n in enumerate(nb.KHO_NUOC_DI)
           if n[0] == "dk_ds" and n[1] == "zone_da_sinh_lenh"))
_z.di(nb.CHI_SO[("hop_le",)])
kiem("và cũng không hỏi được ở phần HỢP LỆ — đó là chỗ ĐỊNH NGHĨA nó",
     not any(nb.mat_na(_z)[i] for i, n in enumerate(nb.KHO_NUOC_DI)
             if n[0] == "dk_ds" and n[1] == "zone_hop_le"))

# Chốt chặn ở BỘ CHẠY, không chỉ ở mặt nạ: ai gọi thẳng `bo_chay.chay` là bỏ qua soát
# tĩnh, và trước đây chỗ đó tràn ngăn xếp chứ không trả NaN như chú thích đã hứa.
_bd = core.make_start_step("bắt đầu", "M5")
_cz = core.make_action_step({
    "type": core.CHECK_COND, "cong_zone": True,
    "conditions": [{"trai": {"ten": "zone_dem"}, "phep": ">=", "phai": {"value": 2}}],
    "dk_hop_le": [{"trai": {"ten": "zone_hop_le"}, "phep": "la_dung"}]})
_vl = core.make_action_step({
    "type": core.VAO_LENH, "huong": "mua", "loai": "market", "rui_ro": 0.5,
    "entry": {"moc": "close"}, "sl": {"tinh": "gia", "value": 1.0},
    "tp": {"tinh": "R", "value": 1.0}})
_vong = core.normalize_process({
    "name": "vòng tròn",
    "tham_so": [core.make_tham_so("chu_ky_atr", "chu kỳ ATR", 14, "nen")],
    "entry": {"steps": [_bd, _cz, _vl],
              "edges": [{"from": _bd["id"], "to": _cz["id"]},
                        {"from": _cz["id"], "to": _vl["id"]}]},
    "manage": {"steps": [core.make_start_step("bắt đầu", "M5")], "edges": []}})
kiem("soát tĩnh BÁO ca vòng tròn ấy",
     any("chính nó" in p["message"] for p in core.validate_process(_vong)))

T0 = 1700000100
_n = 3000
_g = [100.0 + 3.0 * math.sin(k / 70.0) for k in range(_n)]
_nen = np.zeros(_n, dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"), ("l", "f8"),
                           ("c", "f8"), ("vol", "f8")])
for _k, _x in enumerate(_g):
    _nen[_k] = (T0 + _k * 60, _x, _x + 0.4, _x - 0.4, _x, 1.0)
_CD = bc.CaiDat(point=1.0, contract_size=1.0, digits=2, spread_diem=0.0,
                deposit=10_000.0, lot_min=0.01, lot_buoc=0.01, lot_max=50.0)
try:
    bc.chay(_vong, _nen, _CD)
    _ok = True
except RecursionError:
    _ok = False
kiem("và BỘ CHẠY trả NaN chứ không tràn ngăn xếp (ai gọi thẳng vẫn an toàn)", _ok)


# ================= 3. VÒNG TÌM CHẠY THẬT =================
print("\n▸ Vòng tìm — chạy thật trên nến tổng hợp")

TUAN = 7 * 24 * 60
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

_moc = []
R = tk.tim(NEN, CD, 15, hat=2026, tien_do=lambda a, b, c: _moc.append((a, b, c)))
_t = R.thong_ke
kiem("chạy hết số lượt đã xin", _t["da_chay"] + _t["ket"] + _t["trung_lap"] == 15,
     f"— chạy {_t['da_chay']} · kẹt {_t['ket']} · trùng {_t['trung_lap']}")
kiem("KHÔNG lượt nào kẹt", _t["ket"] == 0, f"— {_t['ket']} kẹt")
kiem("KHÔNG lượt nào làm bộ chạy nổ", _t["no"] == 0,
     f"— {_t['no']}: {_t.get('no_vi', [])[:1]}")
kiem("có báo tiến độ", len(_moc) == _t["da_chay"], f"— {len(_moc)} nhịp")
kiem("số sơ đồ KHÔNG vào lệnh nào được đếm và nói ra",
     "khong_lenh" in _t, f"— {_t['khong_lenh']}/{_t['da_chay']}")
kiem("rớt cửa thì GIỮ LẠI kèm lý do", len(R.rot) == _t["rot_cua"] and
     all(x for x in R.rot), f"— {_t['rot_cua']} rớt")
kiem("và gom được thành bảng ĐẾM lý do", bool(_t["ly_do_rot"]),
     f"— {list(_t['ly_do_rot'].items())[:2]}")
kiem("nhóm đầu bảng xếp theo điểm GIẢM DẦN",
     all(R.qua[i][2]["diem"] >= R.qua[i + 1][2]["diem"]
         for i in range(len(R.qua) - 1)))
kiem("và mọi cái trong đó đều ĐẠT cửa", all(d["dat"] for _, _, d in R.qua))
kiem("sơ đồ máy đẻ ra QUA được soát tĩnh",
     all(not core.validate_process(doc) for doc, _, _ in R.qua),
     f"— {len(R.qua)} sơ đồ")

_R2 = tk.tim(NEN, CD, 15, hat=2026)
kiem("TÁI LẬP: cùng hạt giống ra cùng kết quả",
     [c for _, c, _ in R.qua] == [c for _, c, _ in _R2.qua]
     and R.thong_ke["da_chay"] == _R2.thong_ke["da_chay"])
_R3 = tk.tim(NEN, CD, 15, hat=7)
kiem("hạt khác thì đi đường khác",
     _R3.thong_ke["khong_lenh"] != _t["khong_lenh"]
     or [c for _, c, _ in _R3.qua] != [c for _, c, _ in R.qua])

_dem = [0]


def _dung_ngay():
    _dem[0] += 1
    return _dem[0] > 3


_R4 = tk.tim(NEN, CD, 50, hat=1, dung=_dung_ngay)
kiem("DỪNG được từ ngoài (máy tìm không sống trong cửa sổ — §18.6.2)",
     _R4.thong_ke["da_chay"] <= 3, f"— chạy {_R4.thong_ke['da_chay']}/50")

_R5 = tk.tim(NEN, CD, 15, hat=2026, giu=1)
kiem("`giu` chặn đúng số sơ đồ giữ lại", len(_R5.qua) <= 1, f"— {len(_R5.qua)}")

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
