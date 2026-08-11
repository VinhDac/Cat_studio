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

# ================= 7. hai nút nhảy sự kiện là NGHỊCH ĐẢO của nhau =================
#
# `test_luot_ke` và `test_luot_truoc` là hai nút ►► / ◄◄ trên thanh phát lại. Chúng chỉ
# dùng được nếu là nghịch đảo thật của nhau: bấm tới rồi bấm lui phải về ĐÚNG chỗ cũ.
# Hai cách hỏng, cả hai đều "trông có vẻ chạy":
#   • điều kiện lỏng (`<=` thay vì `<`) → bấm ba lần vẫn đứng yên tại chỗ;
#   • hai hàm hiểu "sự kiện" khác nhau → đi tới một đường, đi lui một đường khác.
print("\n▸ Nhảy sự kiện — tới và lui phải là nghịch đảo")

# Giá lên xuống nhiều lần để có NHIỀU lượt có việc, không phải một lượt duy nhất.
song = []
for _ in range(6):
    song += [90.0] * 12 + [110.0] * 12
kq7 = bc.chay(d, nen_m1(song), cd)

at = api.ApiTester(object())
at._kq = kq7

moc_that = [int(r["j"]) for r in kq7.nhat_ky if r["viec"]]
kiem("dựng được lượt chạy có nhiều sự kiện để soi", len(moc_that) >= 3,
     f"— {len(moc_that)} sự kiện")

# Đi XUÔI từ trước điểm đầu tiên, rồi đi NGƯỢC từ sau điểm cuối — gom lại cả hai.
#
# ⚠ PHẢI có chặn. Đúng cái lỗi bài này canh (điều kiện lỏng `<=`) làm hàm trả về CHÍNH
# chỗ đang đứng, nên vòng `while True` không bao giờ thoát: bài test treo thay vì trượt,
# mà treo thì không ai đọc được nó hỏng ở đâu. Chặn ở gấp đôi số sự kiện thật.
def di(buoc, tu):
    ra, cur = [], tu
    for _ in range(len(moc_that) * 2 + 4):
        v = buoc(cur)["value"]
        if v["j"] < 0:
            return ra
        ra.append(v["j"])
        cur = v["j"]
    return ra + ["KHÔNG DỪNG"]


xuoi = di(at.test_luot_ke, -1)
nguoc = di(at.test_luot_truoc, len(kq7.nen1))

kiem("đi xuôi ghé đúng mọi sự kiện", xuoi == moc_that, f"— {len(xuoi)} chặng")
kiem("đi ngược ghé ĐÚNG BẤY NHIÊU chặng đó — cùng một định nghĩa 'sự kiện'",
     nguoc == list(reversed(moc_that)), f"— {len(nguoc)} chặng")

# Đây là bài chặn cái bẫy `<=`: đứng ĐÚNG TRÊN một sự kiện mà bấm lui thì phải nhích
# được sang sự kiện trước nó, không được trả về chính nó.
dung_yen = [x for x in moc_that[1:]
            if at.test_luot_truoc(x)["value"]["j"] == x]
kiem("đứng đúng trên một sự kiện, bấm lui thì NHÍCH — không trả về chính nó",
     not dung_yen, f"— {len(dung_yen)} chỗ đứng yên")

vong = [(e, at.test_luot_ke(e)["value"]["j"]) for e in moc_that[:-1]]
kiem("tới rồi lui về đúng chỗ cũ",
     all(at.test_luot_truoc(ke)["value"]["j"] == e for e, ke in vong),
     f"— {len(vong)} vòng")

kiem("trước sự kiện đầu tiên thì báo hết (-1) — giao diện lấy đó làm hiệu lệnh về đầu",
     at.test_luot_truoc(moc_that[0])["value"]["j"] == -1)
kiem("sau sự kiện cuối cùng thì báo hết (-1)",
     at.test_luot_ke(moc_that[-1])["value"]["j"] == -1)

# ================= 8. đường ray của một lệnh =================
#
# Đường ray trả lời "lệnh này đi qua những khối nào". Nó GỘP các lượt giống nhau lại,
# và chính chỗ gộp là chỗ dễ kể sai chuyện:
#   • gộp TRƯỚC rồi mới xếp thời gian → một cục "manage ×22" nuốt cả các lượt trước lẫn
#     sau lúc khớp, đẩy mốc "khớp" xuống dưới nó;
#   • và vì cục đó mang dấu thời gian của lượt ĐẦU, con trỏ mới tới giữa chừng đã thấy
#     đủ 22 — lộ tương lai, đúng thứ cả chart đang cấm.
print("\n▸ Đường ray — gộp mà không được kể sai thứ tự")

# Cần một lệnh CHỜ thật (đặt xong còn treo mấy nến rồi mới khớp) thì pha "trước khi
# khớp" mới tồn tại. Lệnh thị trường khớp ngay nên không soi được chỗ này.
v8 = core.make_action_step({
    "type": core.VAO_LENH, "name": "mua chờ", "huong": "mua", "loai": "stop",
    "lot": 0.01, "dem": {"tinh": "theo_gia", "value": 5.0},
    "sl": {"tinh": "theo_gia", "value": 1.0},
    "tp": {"tinh": "theo_R", "value": 2.0}})
v8["pos"] = [0.0, 0.0]
bdm8 = core.make_start_step("theo dõi", "M1")
bdm8["pos"] = [0.0, 0.0]
# Cổng HAI điều kiện, cố ý. Cổng một điều kiện không soi được hợp đồng "một vết cho mỗi
# điều kiện": ngắt sớm ở cái sai đầu tiên vẫn ra đúng một vết, nên bài kiểm sẽ mù.
# Điều kiện 1 sai ở đoạn giá 90, điều kiện 2 luôn đúng — nên nếu ai đó cho `_xet_cong`
# ngắt sớm thì vết cụt đi và bài kiểm dưới bắt được ngay.
g8 = core.make_action_step({
    "type": core.CHECK_COND, "name": "giá trong khoảng",
    "conditions": [{"trai": {"ten": "close"}, "phep": ">",
                    "phai_loai": "so", "phai": 100.0},
                   {"trai": {"ten": "close"}, "phep": "<",
                    "phai_loai": "so", "phai": 1000.0}]})
g8["pos"] = [0.0, 0.0]
d8 = core.normalize_process({
    "name": "thử ray", "symbol": "X", "tham_so": d["tham_so"],
    "entry": {"steps": [bd, g8, v8],
              "edges": [{"from": bd["id"], "to": g8["id"], "port": "out"},
                        {"from": g8["id"], "to": v8["id"], "port": "out"}]},
    "manage": {"steps": [bdm8], "edges": []}})
kq8 = bc.chay(d8, nen_m1([90.0] * 20 + [110.0] * 12 + [116.0] * 15), cd)
at8 = api.ApiTester(object())
at8._kq = kq8

l8 = kq8.so.lenh[0]
ray = at8.test_duong_ray(l8.id)["value"]["chang"]
kiem("lệnh mẫu có pha CHỜ thật (đặt xong còn treo rồi mới khớp)",
     l8.nen_khop is not None and l8.nen_khop > l8.nen_dat,
     f"— đặt nến {l8.nen_dat}, khớp nến {l8.nen_khop}")

vi_khop = next((k for k, c in enumerate(ray) if c.get("moc") == "khop"), -1)
truoc = [c for c in ray[:vi_khop] if c["tab"] == "manage"]
sau = [c for c in ray[vi_khop + 1:] if c["tab"] == "manage"]
kiem("mốc KHỚP nằm giữa — có chặng manage cả trước lẫn sau nó",
     vi_khop > 0 and truoc and sau,
     f"— {len(truoc)} chặng trước, {len(sau)} chặng sau")

kiem("thời gian không lùi dọc đường ray",
     all(ray[k]["t"] <= ray[k + 1]["t"] for k in range(len(ray) - 1)))

# Đây là bài chặn chính: một chặng KHÔNG được kéo dài vắt qua chặng kế tiếp. Gộp trước
# rồi xếp sau là vi phạm đúng chỗ này.
vat = [k for k in range(len(ray) - 1) if ray[k]["t_het"] > ray[k + 1]["t"]]
kiem("không chặng nào gộp VẮT QUA một mốc sau nó", not vat,
     f"— {len(vat)} chỗ vắt")

# Cắt theo con trỏ phải ra một TIỀN TỐ liền mạch, không lỗ chỗ.
moc_cat = int(kq8.nen5["t"][l8.nen_khop]) - 1
cat = [c for c in ray if c["t"] <= moc_cat]
kiem("cắt ở ngay trước lúc khớp → đúng phần đã xảy ra, chưa thấy 'khớp'",
     cat == ray[:len(cat)] and all(c.get("moc") != "khop" for c in cat),
     f"— {len(cat)}/{len(ray)} chặng")
kiem("chặng còn dở thì `t_het` vẫn ở tương lai — giao diện lấy đó để KHÔNG in số lặp",
     any(c["t_het"] > moc_cat for c in ray) or len(cat) == len(ray))

# ================= 9. soi một lượt trên sơ đồ =================
#
# `test_soi_luot` bắn sang CỬA SỔ VẼ để nó tô đường lượt đó đã đi. Giao diện tô tới tận
# DÒNG điều kiện hỏng, và nó làm được điều đó chỉ nhờ một giả định: `ve` có đúng một
# phần tử cho mỗi điều kiện của cổng, ĐÚNG THỨ TỰ các dòng trong hộp. Giả định đó không
# nằm ở đâu ngoài đây — lệch một cái là giao diện tô đỏ nhầm dòng, mà nhìn vẫn "có vẻ
# chạy". Bài này giữ nó.
print("\n▸ Soi một lượt trên sơ đồ")


class ChaGia:
    """Cửa sổ VẼ giả — chỉ để bắt xem tester bắn sang đúng chỗ."""
    def __init__(self):
        self.ban = []
        self._khung = type("K", (), {"keo_len_truoc": lambda s: True})()

    def _ban(self, ten, d):
        self.ban.append((ten, d))


cha = ChaGia()
at9 = api.ApiTester(cha)
at9._kq = kq8
khoi9 = {s["id"]: s for s in d8["entry"]["steps"] + d8["manage"]["steps"]}

k_truot = next(k for k, r in enumerate(kq8.nhat_ky) if r["ket"] == "het_luot" and r["cong"])
at9.test_soi_luot(k_truot)
kiem("bắn sang CỬA SỔ VẼ, không phải cửa sổ tester",
     len(cha.ban) == 1 and cha.ban[0][0] == "soi_luot")
d = cha.ban[0][1]
kiem("mang đủ đường đi, cổng đã thử và nhãn để gọi tên khối",
     d["duong"] and d["cong"] and d["chu"]
     and all(k in d["nhan"] for k in d["duong"]))

# ĐÂY là hợp đồng: mỗi cổng có đúng một vết cho mỗi điều kiện, đúng thứ tự.
lech = [c["khoi"] for c in d["cong"]
        if len(c["ve"]) != len(khoi9[c["khoi"]].get("conditions") or [])]
kiem("mỗi cổng: số VẾT khớp đúng số ĐIỀU KIỆN — giao diện tô theo chỉ số này",
     not lech, f"— {len(lech)} cổng lệch")

xau = [c for c in d["cong"] if not c["khop"]]
kiem("cổng trượt có ít nhất một điều kiện `dat = False` để tô đỏ",
     xau and all(any(not v["dat"] for v in c["ve"]) for c in xau),
     f"— {len(xau)} cổng trượt")
kiem("cổng ĐỖ thì mọi điều kiện đều đạt — không có cái nào lọt",
     all(all(v["dat"] for v in c["ve"]) for c in d["cong"] if c["khop"]))

# Lượt CÓ VIỆC: đường đi phải dài hơn một khối, và mọi cổng trên đường đều có nhãn.
cha.ban.clear()
k_viec = next(k for k, r in enumerate(kq8.nhat_ky) if r["viec"])
at9.test_soi_luot(k_viec)
dv = cha.ban[0][1]
kiem("lượt có việc: đi qua nhiều khối, mọi cổng đã thử đều có nhãn",
     len(dv["duong"]) > 1 and all(c["khoi"] in dv["nhan"] for c in dv["cong"]),
     f"— {len(dv['duong'])} khối")

cha.ban.clear()
at9.test_soi_luot(999999)
kiem("chỉ số ngoài khoảng thì im lặng, không bắn gì", not cha.ban)

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
