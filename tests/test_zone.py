"""CỔNG ZONE + MỐC NEO — hai cơ chế vừa thay cho một cỗ máy ẩn.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Trước đây zone do `engine_d02.Engine.moi_nen()` dựng: chạy mỗi nến, TRƯỚC mọi sơ đồ, và
viết cứng điều kiện đếm là "atr_bps dưới ngưỡng". Hai hậu quả:

  · nhìn sơ đồ không thấy zone sinh ra ở đâu — nó chỉ đột nhiên có mặt;
  · chiến lược thứ hai muốn đếm theo điều kiện khác thì phải SỬA ENGINE.

Giờ **cổng mang cờ `cong_zone` trong chính sơ đồ** là điều kiện đếm. Và khối Vào lệnh
có **MỐC NEO** hiện ra thành một trường, thay vì suy ra từ hướng lệnh.

Bài này canh bốn điều:
  1. cổng qua → zone lớn; cổng trượt → zone chết NGAY.
  2. điều kiện đếm là THAM SỐ — đổi cổng là đổi luật đếm, không sửa một dòng engine nào.
  3. dòng chảy không tới được cổng → zone chết (không được sống xuyên quãng không kiểm).
  4. hỏi zone mà không có cổng zone → LỖI RÕ RÀNG, không phải số 0 im lặng.

Chạy:  python tests\\test_zone.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
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


#: Mốc bắt đầu PHẢI chia hết cho 300 (một nến M5).
#:
#: ⚠ Bẫy thật, mất một lượt gỡ: `la_nhip5` bật ở nến M1 nào ĐÓNG ĐÚNG lúc một nến M5
#: đóng. Lấy mốc `1700000000` (dư 200 khi chia 300) thì KHÔNG nến M1 nào trùng biên M5
#: — `la_nhip5` toàn False, sơ đồ Entry không chạy lượt nào, và mọi bài kiểm ở dưới báo
#: "không có zone" trong khi cơ chế hoàn toàn đúng.
T0 = 1700000100          # = 5666667 × 300


def nen_m1(gia):
    a = np.zeros(len(gia), dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"),
                                  ("l", "f8"), ("c", "f8"), ("vol", "f8")])
    a["t"] = T0 + np.arange(len(gia)) * 60
    for k in "ohlc":
        a[k] = gia
    a["vol"] = 1.0
    return a


TS = [core.make_tham_so("chu_ky_atr", "ATR", 14, "nến"),
      core.make_tham_so("nguong", "ngưỡng", 50.0, "bps"),
      core.make_tham_so("lot", "lot", 0.01, "lot")]

CD = bc.CaiDat(symbol="X", spread_diem=0, point=0.01, digits=2,
               contract_size=1.0, deposit=10000.0)

#: Giá ĐỨNG YÊN (ATR → 0, mọi cổng "atr_bps < ngưỡng" đều qua) rồi NHẢY.
#:
#: ⚠ Phải đủ DÀI: nhịp Entry là M5 và ATR chu kỳ 14, nên cần ít nhất 14 nến M5 = 70 nến
#: M1 thì `atr` mới thôi NaN. Bản đầu của bài kiểm này dùng 60 nến M1 → chỉ ra 12 nến
#: M5 → ATR NaN suốt → cổng không bao giờ qua → "không có zone nào", mà nguyên nhân
#: nằm ở DỮ LIỆU THỬ chứ không ở cơ chế.
YEN = [100.0] * 400
DONG = [100.0 + k * 3.0 for k in range(1, 60)]

DK_NEN = [{"trai": {"ten": "atr_bps", "tf": "M5", "period": "chu_ky_atr"},
           "phep": "<", "phai": {"value": "nguong"}}]
#: Cổng KHÔNG dính dáng gì tới ATR — cỗ máy ẩn cũ không đếm kiểu này được.
DK_GIA = [{"trai": {"ten": "close", "tf": "M5", "shift": 1}, "phep": "<",
           "phai": {"value": 105.0}}]


def so_do(dk_cong, cong_zone=True, moc="zone_HH"):
    """Sơ đồ Entry: [bắt đầu] -> [cổng] -> [vào lệnh]."""
    bd = core.make_start_step("bd", "M5")
    bd["pos"] = [0.0, 0.0]
    a = {"id": "g1", "type": core.CHECK_COND, "name": "cổng", "conditions": dk_cong}
    if cong_zone:
        a["cong_zone"] = True
    g = core.make_action_step(a)
    g["pos"] = [1.0, 0.0]
    v = core.make_action_step({
        "id": "v1", "type": core.VAO_LENH, "name": "mua", "huong": "mua",
        "loai": "stop", "lot": "lot", "entry": {"moc": moc},
        "dem": {"tinh": "gia", "value": 1.0},
        "sl": {"tinh": "gia", "value": 1.0}})
    v["pos"] = [2.0, 0.0]
    bdm = core.make_start_step("qly", "M1")
    bdm["pos"] = [0.0, 0.0]
    return core.normalize_process({
        "name": "thử zone", "symbol": "X", "tham_so": TS,
        "entry": {"steps": [bd, g, v],
                  "edges": [{"from": bd["id"], "to": g["id"], "port": "out"},
                            {"from": g["id"], "to": v["id"], "port": "out"}]},
        "manage": {"steps": [bdm], "edges": []}})


def chay(doc, gia):
    return bc.chay(doc, nen_m1(gia), CD)


def loi(d):
    return [p["message"] for p in core.validate_process(d) if p["severity"] == "error"]


print("\n▸ 1. Cổng qua thì zone LỚN, cổng trượt thì zone CHẾT")
kq = chay(so_do(DK_NEN), YEN + DONG)
kiem("có zone hình thành", len(kq.so.zone) >= 1, f"— {len(kq.so.zone)} zone")
v0 = kq.so.zone[0]
kiem("zone đếm được nhiều nến", v0.so_nen >= 3, f"— {v0.so_nen} nến")
kiem("đỉnh/đáy zone lấy từ chính đoạn giá yên",
     abs(v0.dinh - 100.0) < 1e-9 and abs(v0.day - 100.0) < 1e-9,
     f"— HH {v0.dinh} / LL {v0.day}")
kiem("giá bung ra thì zone CHẾT", not kq.so.zone[-1].song or len(kq.so.zone) > 1)

print("\n▸ 2. ĐIỀU KIỆN ĐẾM là tham số — đổi cổng là đổi luật, không sửa engine")
kq2 = chay(so_do(DK_GIA), YEN + DONG)
kiem("zone đếm theo điều kiện GIÁ, không phải ATR", len(kq2.so.zone) >= 1,
     f"— {len(kq2.so.zone)} zone, {kq2.so.zone[0].so_nen} nến")
kiem("zone chết đúng lúc giá vượt 105",
     abs(kq2.so.zone[0].dinh - 100.0) < 1e-9, f"— HH {kq2.so.zone[0].dinh}")

print("\n▸ 3. KHÔNG có cổng zone → engine không dựng sẵn zone nào")
kq3 = chay(so_do(DK_NEN, cong_zone=False, moc="gia_hien_tai"), YEN + DONG)
kiem("không cổng zone thì KHÔNG có zone nào", len(kq3.so.zone) == 0,
     f"— {len(kq3.so.zone)} zone")
kiem("nhưng lệnh neo GIÁ HIỆN TẠI vẫn đặt được", len(kq3.so.lenh) > 0,
     f"— {len(kq3.so.lenh)} lệnh")

print("\n▸ 4. Dòng chảy KHÔNG TỚI cổng zone → zone chết")


def so_do_chan(nguong_chan):
    """[bắt đầu] -> [chặn] -> [cổng zone]. Chặn trượt là dòng chảy không tới cổng."""
    bd = core.make_start_step("bd", "M5")
    bd["pos"] = [0.0, 0.0]
    chan = core.make_action_step({
        "id": "c0", "type": core.CHECK_COND, "name": "chặn",
        "conditions": [{"trai": {"ten": "close"}, "phep": "<",
                        "phai": {"value": nguong_chan}}]})
    chan["pos"] = [1.0, 0.0]
    gz = core.make_action_step({"id": "g1", "type": core.CHECK_COND,
                                "name": "cổng zone", "cong_zone": True,
                                "conditions": DK_NEN})
    gz["pos"] = [2.0, 0.0]
    bdm = core.make_start_step("qly", "M1")
    bdm["pos"] = [0.0, 0.0]
    return core.normalize_process({
        "name": "chặn", "symbol": "X", "tham_so": TS,
        "entry": {"steps": [bd, chan, gz],
                  "edges": [{"from": bd["id"], "to": chan["id"], "port": "out"},
                            {"from": chan["id"], "to": gz["id"], "port": "out"}]},
        "manage": {"steps": [bdm], "edges": []}})


kq4a = chay(so_do_chan(999.0), YEN)
kiem("chặn luôn qua → zone sống bình thường", len(kq4a.so.zone) >= 1,
     f"— {kq4a.so.zone[0].so_nen if kq4a.so.zone else 0} nến")
kq4b = chay(so_do_chan(50.0), YEN)
kiem("chặn luôn trượt → KHÔNG zone nào (nến không được kiểm thì không đếm)",
     len(kq4b.so.zone) == 0, f"— {len(kq4b.so.zone)} zone")

print("\n▸ 5. Soát tĩnh — hỏi zone mà không có cổng thì phải KÊU")
d5 = so_do(DK_NEN, cong_zone=False)         # mốc zone_HH nhưng không cổng
kiem("mốc neo zone mà thiếu cổng → lỗi",
     any("cổng zone" in m for m in loi(d5)), f"— {(loi(d5) or [''])[0][:60]}")

d6 = so_do([{"trai": {"ten": "zone_dem"}, "phep": ">=", "phai": {"value": 5}}], cong_zone=False, moc="gia_hien_tai")
kiem("toán hạng zone mà thiếu cổng → lỗi",
     any("cổng zone" in m for m in loi(d6)), f"— {(loi(d6) or [''])[0][:60]}")

kiem("có cổng zone rồi thì SẠCH", not loi(so_do(DK_NEN)), f"— {loi(so_do(DK_NEN))}")

# Hai cổng zone: cái sau đè cái trước, không ai đọc ra zone đang đếm theo luật nào.
d8 = so_do(DK_NEN)
d8["entry"]["steps"][2] = core.make_action_step({
    "id": "v1", "type": core.CHECK_COND, "name": "cổng 2",
    "cong_zone": True, "conditions": DK_GIA})
d8["entry"]["steps"][2]["pos"] = [2.0, 0.0]
# Khớp câu ĐÚNG chứ không khớp bừa: `any("cổng zone" in m)` từng qua vì một thông báo
# hoàn toàn khác ("chưa chọn khung thời gian") — bài kiểm xanh mà chẳng kiểm gì.
kiem("hai cổng zone → lỗi",
     any("Chỉ được MỘT" in m for m in loi(d8)), f"— {(loi(d8) or [''])[0][:70]}")

# Cổng zone ở Manage: một cây nến bị đếm nhiều lần (mỗi lệnh sống một lượt).
d9 = so_do(DK_NEN)
gm = core.make_action_step({"id": "m1", "type": core.CHECK_COND, "name": "sai chỗ",
                            "cong_zone": True, "conditions": DK_NEN})
gm["pos"] = [1.0, 0.0]
d9["manage"]["steps"].append(gm)
kiem("cổng zone đặt ở Manage → lỗi",
     any("Manage" in m for m in loi(d9)), f"— {(loi(d9) or [''])[0][:60]}")

print("\n▸ 6. MỐC NEO quyết định lệnh nằm ở đâu")
kq9 = chay(so_do(DK_NEN, moc="zone_HH"), YEN + DONG)
l9 = kq9.so.lenh[0] if kq9.so.lenh else None
kiem("neo ĐỈNH zone: giá đặt = HH + đệm",
     l9 is not None and abs(l9.gia_dat - 101.0) < 1e-6, f"— {l9 and l9.gia_dat}")

kq10 = chay(so_do(DK_NEN, moc="gia_hien_tai"), YEN + DONG)
kiem("neo GIÁ HIỆN TẠI vẫn đặt được lệnh", len(kq10.so.lenh) > 0,
     f"— {len(kq10.so.lenh)} lệnh")

# ĐỆM là TUỲ CHỌN — bỏ trống thì lệnh nằm ĐÚNG mốc.
d11 = so_do(DK_NEN)
d11["entry"]["steps"][2].pop("dem", None)
kq11 = chay(d11, YEN + DONG)
l11 = kq11.so.lenh[0] if kq11.so.lenh else None
kiem("bỏ đệm → lệnh nằm ĐÚNG mép zone",
     l11 is not None and abs(l11.gia_dat - 100.0) < 1e-6, f"— {l11 and l11.gia_dat}")

print("\n▸ 7. ĐƠN VỊ SO SÁNH — `atr_bps` cũ giờ là `atr [bps]`")
# ⚠ Bài này ở ĐÂY chứ không ở `test_tinh_toan.py`: chuẩn hoá theo giá không còn là một
# hàm nữa, nó là HÀNH VI của dòng điều kiện. Cách duy nhất kiểm đúng là chạy sơ đồ thật
# rồi so với con số tính tay.
from cat_studio import tinh_toan as tt7  # noqa: E402

GIA7 = [100.0 + (k % 7) * 0.4 for k in range(600)]
m5 = tt7.gop(nen_m1(GIA7), "M5")
atr7 = tt7.atr(m5["h"].astype(float), m5["l"].astype(float),
               m5["c"].astype(float), 14)
bps7 = atr7 / m5["c"].astype(float) * 1e4
tay = float(bps7[~np.isnan(bps7)][-20])          # một mốc sau khi ATR đã ấm máy


def so_do_bps(nguong, don_vi="bps"):
    c = {"trai": {"ten": "atr", "tf": "M5", "period": "chu_ky_atr"},
         "phep": "<", "phai": {"value": nguong}}
    if don_vi:
        c["don_vi"] = don_vi
    return so_do([c], moc="gia_hien_tai")


duoi = chay(so_do_bps(tay * 0.5), GIA7)
tren = chay(so_do_bps(tay * 2.0), GIA7)
kiem("ngưỡng bps DƯỚI giá trị thật → không zone nào",
     len(duoi.so.zone) == 0, f"— tay {tay:.2f} bps · {len(duoi.so.zone)} zone")
kiem("ngưỡng bps TRÊN giá trị thật → có zone",
     len(tren.so.zone) >= 1, f"— {len(tren.so.zone)} zone")

# CÙNG một con số, có đơn vị và không có đơn vị, phải cho kết quả NGƯỢC nhau — đó là
# bằng chứng phép quy đổi thật sự chạy, chứ không phải ngưỡng tình cờ đúng cả hai đường.
# ATR thô ở đây ~2,3 (giá ~101) còn ATR theo bps ~229. Ngưỡng nằm giữa thì tách bạch.
giua = tay * 0.5
kiem("cùng ngưỡng: CÓ đơn vị bps → không zone",
     len(chay(so_do_bps(giua), GIA7).so.zone) == 0, f"— ngưỡng {giua:.1f}")
kiem("cùng ngưỡng: KHÔNG đơn vị (thô) → có zone",
     len(chay(so_do_bps(giua, don_vi=None), GIA7).so.zone) >= 1,
     "— quy đổi có thật, không phải ngưỡng tình cờ")

# Đơn vị chỉ sống với `khoang_cach`. Gắn vào toán hạng ĐẾM phải bị normalize vứt.
d7 = so_do([{"trai": {"ten": "so_lenh_cho"}, "phep": "<", "phai": {"value": 4, "tinh": "atr"}}], moc="gia_hien_tai")
kiem("đơn vị gắn vào toán hạng ĐẾM bị vứt (`so_lenh_cho < 4 × ATR` vô nghĩa)",
     "tinh" not in d7["entry"]["steps"][1]["conditions"][0]["phai"])
kiem("còn gắn vào `atr` thì giữ",
     so_do_bps(7.0)["entry"]["steps"][1]["conditions"][0]["phai"].get("tinh") == "bps")

print("\n▸ 8. CHỈ BÀY RA THỨ DÙNG ĐƯỢC — lọc tại nguồn, không bày rồi mắng")
#
# Luật này app đã có từ lâu (`core.DON_VI_CHO`: *"bày ra một lựa chọn vô nghĩa rồi soát
# tĩnh mắng là tệ hơn không bày"*), và dropdown toán hạng cũng đã ẩn nhóm "Lệnh này" ở
# Entry. Mới áp một nửa: zone thì chưa. Đây là chỗ canh nửa còn lại.
d8 = so_do(DK_NEN)
sau = core.khoi_sau_cong_zone(d8["entry"]["steps"], d8["entry"]["edges"])
kiem("khối SAU cổng zone nằm trong danh sách", "v1" in sau, f"— {sorted(sau)}")
kiem("CHÍNH cổng zone thì KHÔNG — điều kiện của nó chạy trước khi zone lớn thêm",
     "g1" not in sau)
kiem("khối Bắt đầu (đứng TRƯỚC cổng) cũng không",
     d8["entry"]["steps"][0]["id"] not in sau)
d8b = so_do(DK_NEN, cong_zone=False, moc="gia_hien_tai")
kiem("không có cổng zone thì danh sách RỖNG",
     core.khoi_sau_cong_zone(d8b["entry"]["steps"], d8b["entry"]["edges"]) == set())

# Ba nhát cắt trên danh sách ĐƠN VỊ.
kiem("chưa qua cổng zone: `× ATR zone` KHÔNG được bày ra",
     "atr_zone" not in core.don_vi_cho("atr", co_zone=False),
     f"— {core.don_vi_cho('atr', co_zone=False)}")
kiem("đã qua cổng zone thì có",
     "atr_zone" in core.don_vi_cho("atr", co_zone=True))
kiem("KHÔNG đo một đại lượng bằng CHÍNH NÓ: `Zone — ATR trung bình` không có `× ATR zone`",
     "atr_zone" not in core.don_vi_cho("zone_atr_tb", co_zone=True),
     f"— {core.don_vi_cho('zone_atr_tb', co_zone=True)}")
kiem("nhưng `× ATR` thì vẫn được — nó chia cho ATR hiện tại, một tỉ lệ có nghĩa",
     "atr" in core.don_vi_cho("zone_atr_tb", co_zone=True))
kiem("`atr` KHÔNG bị cấm `× ATR`: khung/chu kỳ riêng nên tỉ lệ vẫn có nghĩa",
     "atr" in core.don_vi_cho("atr", co_zone=True))

# `pt` ("% của giá") đã bỏ — nó là `bps` chia 100, hai tên cho một phép.
kiem("`% của giá` biến khỏi MỌI danh sách đơn vị",
     "pt" not in core.DON_VI
     and not any("pt" in v for v in core.DON_VI_CHO.values()),
     f"— còn {sorted(core.DON_VI)}")
# `bps` từng được BÀY RA cho SL/TP mà bộ chạy chưa cài → chọn vào là ném lỗi lúc chạy.
kiem("`bps` bày ra cho SL/TP thì bộ chạy phải CÀI THẬT (trước đây ném LoiChay)",
     "bps" in core.DON_VI_CHO["sl"]
     and abs(bc._khoang({"tinh": "bps", "value": 50},
                        type("C", (), {"ct": type("T", (), {"so": staticmethod(float)})})(),
                        neo=2000.0) - 10.0) < 1e-9,
     "— 50 bps của 2000 = 10,0")

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
