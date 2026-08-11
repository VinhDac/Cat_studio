"""NHẬT KÝ — bản ghi rỗng chữ, nhãn dựng lại, ghi/đọc ngược không mất gì.

Người dùng nói đây là phần quan trọng nhất, vì debug và nâng cấp model là ở hết đây.
Nên bài này canh đúng những chỗ hỏng mà vẫn "trông có vẻ chạy":

  1. **Bản ghi không chứa chữ.** Chữ dựng lúc hiển thị, cho lô đang nhìn.
  2. **Nhãn `[3A.1]` KHÔNG được lưu** — kéo một khối đi chỗ khác là nhãn đổi, mà nhật ký
     cũ vẫn phải trỏ đúng khối.
  3. **Ghi rồi đọc ngược không mất gì** — kể cả khi một khoá của lệnh trùng tên nhãn dòng.
  4. **Vân tay** đổi khi LOGIC đổi, không đổi khi chỉ kéo khối.
  5. Phân biệt "chưa có số" với "so xong thấy không đạt".

Chạy:  python tests\\test_nhat_ky.py
"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import api  # noqa: E402
from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import nguon_nen as nn  # noqa: E402
from cat_studio import nhat_ky as nk  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# --------------------------------------------------------------------------
# Một lần chạy nhỏ trên dữ liệu giả — đủ để có cả lượt CÓ VIỆC lẫn lượt HẾT LƯỢT.
def nen_m1(gia):
    g = np.asarray(gia, dtype=float)
    a = np.empty(len(g), dtype=nn.DTYPE)
    a["t"] = np.arange(0, len(g) * 60, 60, dtype=np.int64)[:len(g)]
    for k in ("o", "h", "l", "c"):
        a[k] = g
    a["vol"] = 1
    return a


bd = core.make_start_step("bắt đầu", "M5")
bd["pos"] = [0.0, 0.0]
g = core.make_action_step({
    "type": core.CHECK_COND, "name": "giá > 100",
    "conditions": [{"trai": {"ten": "close"}, "phep": ">",
                    "phai_loai": "so", "phai": 100.0}]})
g["pos"] = [0.0, 0.0]
v = core.make_action_step({
    "type": core.VAO_LENH, "name": "mua", "huong": "mua", "loai": "market",
    "lot": 0.01, "sl": {"tinh": "theo_gia", "value": 1.0},
    "tp": {"tinh": "theo_R", "value": 2.0}})
v["pos"] = [0.0, 0.0]
d = core.normalize_process({
    "name": "thử nhật ký", "symbol": "X",
    "tham_so": [{"ten": "nguong_nen_bps", "nhan": "", "gia_tri": 1e9, "don_vi": "bps"},
                {"ten": "chu_ky_atr", "nhan": "", "gia_tri": 3, "don_vi": "nến"}],
    "entry": {"steps": [bd, g, v],
              "edges": [{"from": bd["id"], "to": g["id"], "port": "out"},
                        {"from": g["id"], "to": v["id"], "port": "out"}]},
    "manage": {"steps": [], "edges": []}})

cd = bc.CaiDat(symbol="X", point=1.0, contract_size=1.0, spread_diem=0.0)
kq = bc.chay(d, nen_m1([90.0] * 30 + [110.0] * 30), cd)

# ================= 1. bản ghi rỗng chữ =================
print("\n▸ Bản ghi RỖNG CHỮ")
r = kq.nhat_ky[0]
kiem("bản ghi chỉ có số, id và nhãn kỹ thuật — không câu tiếng Việt nào",
     not any(isinstance(x, str) and " " in x
             for x in (r["tab"], r["ket"], *(r["duong"]))),
     f"— {sorted(r)}")
kiem("lưu id khối, KHÔNG lưu nhãn [3A.1]",
     all(k in {s["id"] for s in d["entry"]["steps"]} for k in r["duong"]))

# ================= 2. nhãn dựng lại =================
print("\n▸ Nhãn dựng lại, không lưu")
nhan = nk.nhan_khoi(d)
kiem("dựng được nhãn cho mọi khối", nhan.get(bd["id"]) == "1" and nhan.get(g["id"]),
     f"— {list(nhan.values())}")
# Kéo khối đi chỗ khác → nhãn có thể đổi, nhưng nhật ký vẫn trỏ đúng khối vì nó giữ id.
d2 = json.loads(json.dumps(d))
for st in d2["entry"]["steps"]:
    st["pos"] = [st["pos"][0] + 500, st["pos"][1] + 500]
kiem("kéo khối đi chỗ khác — nhật ký cũ vẫn trỏ đúng khối (vì giữ id, không giữ nhãn)",
     set(nk.nhan_khoi(d2)) == set(nhan))

# ================= 3. dựng chữ theo lô =================
print("\n▸ Dựng chữ theo lô")
lo = nk.dung_lo(kq, 0, 5, chi_co_viec=True)
kiem("lô chỉ-có-việc: mọi dòng đều có việc", lo["dong"] and all(x["co_viec"] for x in lo["dong"]))
kiem("dòng chữ nêu rõ đã đặt lệnh nào",
     "đặt Mua L-0001" in lo["dong"][0]["chu"], f"— {lo['dong'][0]['chu']}")
het = nk.dung_lo(kq, 0, 5, chi_co_viec=False)
kiem("lô mọi-lượt nhiều hơn hẳn lô chỉ-có-việc", het["tong"] > lo["tong"],
     f"— {het['tong']} vs {lo['tong']}")
kiem("lượt trượt nêu rõ CỔNG nào và HAI VẾ bằng bao nhiêu",
     "hết lượt tại" in het["dong"][0]["chu"] and "90.00" in het["dong"][0]["chu"],
     f"— {het['dong'][0]['chu']}")
kiem("chỉ dựng chữ cho lô xin, không dựng cả 100% nhật ký",
     len(het["dong"]) == 5 and het["tong"] == len(kq.nhat_ky))

# "chưa có số" KHÁC HẲN "so xong thấy không đạt" — trộn hai thứ là debug đi nhầm hướng.
g_atr = core.make_action_step({
    "type": core.CHECK_COND, "name": "ATR < 999",
    "conditions": [{"trai": {"ten": "atr", "period": 5}, "phep": "<",
                    "phai_loai": "so", "phai": 999.0}]})
g_atr["pos"] = [0.0, 0.0]
d3 = core.normalize_process(dict(
    d, entry={"steps": [bd, g_atr, v],
              "edges": [{"from": bd["id"], "to": g_atr["id"], "port": "out"},
                        {"from": g_atr["id"], "to": v["id"], "port": "out"}]}))
kq3 = bc.chay(d3, nen_m1([100.0] * 30), cd)
chu = nk.dung_lo(kq3, 0, 1, chi_co_viec=False)["dong"][0]["chu"]
kiem("chưa đủ dữ liệu → \"chưa có dữ liệu\", KHÔNG phải \"= 0, không < 999\"",
     "chưa có dữ liệu" in chu, f"— {chu}")

# ================= 4. ghi / đọc ngược =================
print("\n▸ Ghi ra đĩa rồi đọc ngược")
p = nk.ghi(kq, cd, ten="__test_nhat_ky__")
meta, lenh, luot = nk.doc_file(p)
# `Lenh.tom_tat()` có sẵn khoá `loai` (stop/limit/market). Trải phẳng nó vào bản ghi là
# ĐÈ MẤT nhãn dòng, và đọc ngược sẽ nhận nhầm lệnh thành lượt — ghi vẫn "thành công".
kiem("đọc lại ĐỦ số lệnh (khoá `loai` của lệnh không đè mất nhãn dòng)",
     len(lenh) == len(kq.so.lenh), f"— {len(lenh)}/{len(kq.so.lenh)}")
kiem("đọc lại đủ số lượt", len(luot) == len(kq.nhat_ky), f"— {len(luot)}/{len(kq.nhat_ky)}")
kiem("meta giữ NGUYÊN BẢN sơ đồ đã chạy — để mở lại lần chạy cũ",
     meta["doc"]["entry"]["steps"][0]["id"] == bd["id"])
kiem("meta giữ điều kiện chạy (spread, vốn, phí)",
     meta["spread_diem"] == cd.spread_diem and meta["deposit"] == cd.deposit)
os.remove(p)

# ================= 5. vân tay =================
print("\n▸ Vân tay — đổi khi LOGIC đổi")
kiem("kéo khối đi chỗ khác KHÔNG đổi vân tay", nk._van_tay(d) == nk._van_tay(d2))
d4 = json.loads(json.dumps(d))
d4["entry"]["steps"][1]["conditions"][0]["phai"] = 999.0
kiem("đổi một ngưỡng thì ĐỔI vân tay", nk._van_tay(d) != nk._van_tay(d4))
d5 = json.loads(json.dumps(d))
d5["entry"]["edges"] = []
kiem("đổi cách NỐI DÂY cũng đổi vân tay — cùng bộ khối mà nối khác là chiến lược khác",
     nk._van_tay(d) != nk._van_tay(d5))
d6 = json.loads(json.dumps(d))
d6["tham_so"][0]["gia_tri"] = 123.0
kiem("đổi một THAM SỐ cũng đổi vân tay", nk._van_tay(d) != nk._van_tay(d6))

# ================= 6. so hai lần chạy =================
print("\n▸ So hai lần chạy")
a = {"thong_ke": {"so_lenh": 10, "tong_R": 5.0, "ty_le_thang": 40.0, "drawdown_pt": 2.0},
     "van_tay": "aaa"}
b = {"thong_ke": {"so_lenh": 7, "tong_R": 8.0, "ty_le_thang": 40.0, "drawdown_pt": 2.0},
     "van_tay": "aaa"}
c = nk.so_hai_lan(a, b)
kiem("nêu đúng thứ ĐỔI, bỏ qua thứ không đổi",
     "-3 lệnh" in c and "+3.0 R" in c and "% thắng" not in c, f"— {c}")
kiem("hai lần y hệt → nói y hệt", "y hệt" in nk.so_hai_lan(a, a))
kiem("sơ đồ đã đổi thì nói ra — số khác nhau vì lý do khác hẳn",
     "sơ đồ ĐÃ ĐỔI" in nk.so_hai_lan(a, dict(b, van_tay="bbb")))
kiem("chưa có lần trước thì không bịa ra gì", nk.so_hai_lan(None, b) == "")

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
