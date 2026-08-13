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
from cat_studio import so_lenh  # noqa: E402

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
# ⭐ ĐỔI LUẬT (core.md §12.6c). Trước đây CHÍNH cổng zone bị loại khỏi danh sách, lý do
# ghi là "điều kiện của nó chạy trước khi zone lớn thêm". Lý do ấy mô tả đúng code cũ
# nhưng khoá chết câu người dùng buộc phải viết được: "zone rộng quá thì thôi, không
# tính là zone nữa" — câu đó chỉ có MỘT chỗ đúng để đứng là chính cổng định nghĩa zone.
kiem("CHÍNH cổng zone CŨNG nằm trong danh sách — nó nhìn ZONE THỬ (đã cộng nến này)",
     "g1" in sau)
kiem("khối Bắt đầu (đứng TRƯỚC cổng) cũng không",
     d8["entry"]["steps"][0]["id"] not in sau)
d8b = so_do(DK_NEN, cong_zone=False, moc="gia_hien_tai")
kiem("không có cổng zone thì danh sách RỖNG",
     core.khoi_sau_cong_zone(d8b["entry"]["steps"], d8b["entry"]["edges"]) == set())

# ---- ZONE THỬ: cổng zone phán xét HẬU QUẢ nó sắp gây ra (core.md §12.6c) ------------
#
# Cổng zone trả lời "cây nến này có được nuốt không?", nên nó phải nhìn zone SAU khi
# nuốt. Nhờ vậy `bề rộng ≤ N` thành một HẠN MỨC: kiểm trước khi tiêu, zone không bao giờ
# vượt. Nhìn zone TRƯỚC khi nuốt thì cây nến làm vỡ hạn mức đã nằm trong zone rồi.
print("\n▸ 8b. ZONE THỬ — cổng zone nhìn zone ĐÃ CỘNG nến đang xét")

_z = so_lenh.Zone("V-0001", 0)
_z.them_nen(110.0, 100.0, 2.0)
_t = _z.thu_them(130.0, 90.0, 4.0)
kiem("`thu_them` KHÔNG đụng bản thật",
     (_z.so_nen, _z.dinh, _z.day) == (1, 110.0, 100.0),
     f"— thật {_z.so_nen} nến {_z.day}–{_z.dinh}")
kiem("bản thử đã cộng nến mới", (_t.so_nen, _t.dinh, _t.day) == (2, 130.0, 90.0),
     f"— thử {_t.so_nen} nến {_t.day}–{_t.dinh}")
kiem("bản thử GIỮ id — `zone_da_sinh_lenh` tra đúng zone", _t.id == "V-0001")
kiem("`atr_tb` của bản thử tính cả nến mới", _t.atr_tb == 3.0, f"— {_t.atr_tb}")

# NẾN ĐẦU TIÊN hết là ca đặc biệt: zone thử luôn có ít nhất một nến nên bề rộng là một
# con số thật, không phải NaN. Đây là thứ làm hướng "zone thử" thắng hướng "zone trước".
_moi = so_lenh.Zone("(thử)", 0)
_moi.them_nen(105.0, 100.0, 1.0)
kiem("nến ĐẦU của một zone: bề rộng = high−low của chính nó, KHÔNG phải NaN",
     _moi.rong == 5.0 and _moi.so_nen == 1, f"— rộng {_moi.rong}")

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

print("\n▸ 9. MỖI NẾN TRỤC ĐƯỢC CHẠY ĐÚNG MỘT LẦN, kể cả khi dữ liệu M1 thủng")
#
# Nhịp Entry TỪNG được lấy bằng phép trùng khít mốc (`np.isin(dong1, dong5)`) — "nến M1
# nào đóng ĐÚNG lúc nến trục đóng". Thiếu đúng cây phút đó thì cả nến trục không được
# chạy lần nào: cổng zone không được xét, zone không lớn cũng không chết.
#
# Đo trên 260.000 nến XAUUSD thật: 188 nến trục (0,36 %) bị bỏ. Hậu quả nặng nhất là khi
# CHÍNH nến bị bỏ mang cờ lỗ hổng — cờ bốc hơi cùng nến, zone sống XUYÊN qua một quãng
# chợ đóng, trái luật mà `_nuoi_zone` tự tuyên bố ("48 giờ chợ đóng cửa không phải giá
# đứng yên").
_nen9 = nen_m1([100.0] * 200)
# Đục THỦNG đúng cây phút cuối của một nến M5 (mốc đóng chia hết cho 300).
_thung = [k for k in range(80, 180) if (int(_nen9["t"][k]) + 60) % 300 == 0][0]
_ct9 = bc.ChuongTrinh(so_do(DK_NEN), np.delete(_nen9, _thung), CD)
_co9 = np.zeros(len(_ct9.nen5), dtype=bool)
_co9[_ct9.m1_to_5[_ct9.la_nhip5]] = True
kiem("thủng phút cuối vẫn KHÔNG bỏ sót nến trục nào",
     bool(_co9[1:].all()), f"— {int((~_co9[1:]).sum())} nến trục không có nhịp nào")
_dem9 = np.bincount(_ct9.m1_to_5[_ct9.la_nhip5], minlength=len(_ct9.nen5))
kiem("và không nến trục nào bị chạy HAI lần",
     int(_dem9.max()) <= 1, f"— nhiều nhất {int(_dem9.max())} nhịp/nến")

# Hệ quả: zone không được sống xuyên một quãng chợ đóng.
_kq9 = chay(so_do(DK_NEN), YEN + DONG)
_xuyen = [v.id for v in _kq9.so.zone
          if v.so_nen > 1
          and _kq9._ct.lo_hong5[v.nen_bat_dau + 1:v.nen_bat_dau + v.so_nen].any()]
kiem("không zone nào sống xuyên lỗ hổng dữ liệu", not _xuyen, f"— {_xuyen}")

print("\n▸ 10. HỘP ZONE trên chart KHÔNG được lộ tương lai")
#
# `_hop_zone` gửi zone sang chart làm phông nền. `kq.so.zone` là danh sách của CẢ lần
# chạy, và `v.dinh`/`v.day` là đỉnh–đáy CUỐI CÙNG — tức đã gồm cả những nến người xem
# chưa tới. Phải cắt ở con trỏ theo CẢ HAI CHIỀU.
#
# ⚠ Bản đầu chỉ cắt chiều NGANG, nên hộp vẫn cao bằng tương lai. Đo trên nến thật: con
# trỏ ở nến thứ 2 của zone, đáy thật 4484,49 mà hộp vẽ 4476,62 — đáy của 13 nến sau.
# Không ai thấy, vì nó chỉ là một mảng mờ sau lưng cây nến.
from cat_studio import api as _api          # noqa: E402
from cat_studio import tinh_toan as _tt     # noqa: E402

#: ⚠ KHÔNG dùng `YEN` (giá phẳng 100,0 suốt): đỉnh và đáy khi đó bằng nhau ở MỌI mốc,
#: nên phép so luôn đúng bất kể hàm sai hay đúng — một bài kiểm tự xác nhận.
#: Đây là dải NỞ DẦN: biên độ lớn lên từng nến nên đỉnh–đáy tới nến thứ 2 khác hẳn tới
#: nến thứ 5. Vẫn đủ hẹp để cổng `atr < 50 bps` không giết zone.
#: Dải phải NỞ RA **SAU KHI ZONE ĐÃ BẮT ĐẦU** (nến M5 thứ 14, tức nến M1 thứ 70 — trước
#: đó ATR còn NaN vì chu kỳ 14). Nở sớm rồi chặn trần thì tới lúc zone mở, đỉnh–đáy đã
#: đứng yên, và phép so ở dưới đúng ở mọi mốc bất kể hàm sai hay đúng.
#: Biên độ tối đa ±0,30 → ATR ~6 bps, dưới xa ngưỡng 50 bps nên cổng vẫn qua.
NO_DAN = [100.0 + (0.02 if i < 80 else min(0.30, 0.02 + 0.003 * (i - 80)))
          * (1 if i % 2 else -1) for i in range(400)]
_kq = chay(so_do(DK_NEN), NO_DAN + DONG)
_v = _kq.so.zone[0]
_n5 = _kq._ct.nen5
_b0 = _v.nen_bat_dau
# ⚠ CHỐT CHẶN cho chính bài kiểm này: nếu dữ liệu thử làm đỉnh–đáy đứng yên qua mọi mốc
# thì phép so bên dưới luôn đúng, kể cả khi hàm sai. Đã dính đúng bẫy đó một lần (dữ liệu
# `YEN` phẳng 100,0 → hh = ll = 100 ở mọi mốc). Bắt ngay, đừng để nó xanh giả.
_moc = [(float(_n5["l"][_b0:_b0 + k].min()), float(_n5["h"][_b0:_b0 + k].max()))
        for k in (1, 2, 5)]
kiem("dữ liệu thử PHÂN BIỆT ĐƯỢC các mốc (không thì bài dưới xanh giả)",
     len(set(_moc)) > 1, f"— {[tuple(round(x, 3) for x in m) for m in _moc]}")

for _k in (1, 2, 5):
    _a = _tt.gop(_kq.nen1[:(_b0 + _k) * 5], "M5", giu_nen_do_dang=True)
    _hop = _api.ApiTester._hop_zone(_kq, _a, 0)
    _that = (float(_n5["l"][_b0:_b0 + _k].min()), float(_n5["h"][_b0:_b0 + _k].max()))
    kiem(f"con trỏ ở nến thứ {_k}: hộp cao đúng bằng những gì ĐÃ THẤY",
         bool(_hop) and abs(_hop[-1][2] - _that[0]) < 1e-9
         and abs(_hop[-1][3] - _that[1]) < 1e-9,
         (f"— hộp {tuple(round(x, 4) for x in _hop[-1][2:])} · thật "
          f"{tuple(round(x, 4) for x in _that)}") if _hop else "— không có hộp nào")

# Zone hình thành SAU con trỏ thì không được hiện.
_a0 = _tt.gop(_kq.nen1[:_b0 * 5], "M5", giu_nen_do_dang=True)
kiem("zone chưa bắt đầu thì KHÔNG có hộp nào",
     not [h for h in _api.ApiTester._hop_zone(_kq, _a0, 0)
          if h[0] >= int(_n5["t"][_b0])])

print("\n▸ 11. ZONE phải LỚN DẦN trong lúc PHÁT LẠI, không đợi tới lúc nhảy")
#
# Lúc phát lại, `nhip()` lấy khung hình TỪ LÔ và không hỏi Python một câu nào — đó là cả
# điểm của lô (phát 60 ms/nhịp mà gọi cầu nối mỗi nhịp thì giật). Nhưng zone từng chỉ
# được nạp ở đường NHẢY, nên suốt lúc phát nó ĐỨNG YÊN: bấm ▶ zone không nhúc nhích,
# bấm "tới sự kiện" mới thấy nó nhảy một phát.
#
# Lệnh không bị vậy vì lô mang sẵn cả sự kiện tương lai và `Chart` cắt theo `tBayGio`.
# Bài này canh zone theo đúng luật đó.
_at11 = _api.ApiTester(object())
_at11._kq = _kq
_L = _at11.test_doan(0, min(300, len(_kq.nen1)))["value"]
kiem("lô mang theo bản ghi zone", bool(_L.get("zone")),
     f"— {len(_L.get('zone') or [])} bản ghi")

# Mô phỏng ĐÚNG phép gộp của `Tester.apDung`: bản ghi mới nhất có `t_nến ≤ con trỏ`.
_hop11, _buoc11 = {}, []
for _k in range(_L["n"]):
    _t11 = _L["t"][_k]
    for _z in _L.get("zone") or []:
        if _z[1] <= _t11 and (_z[0] not in _hop11 or _hop11[_z[0]][1] < _z[1]):
            _hop11[_z[0]] = _z
    _buoc11.append(tuple(sorted((z[0], z[2], z[3]) for z in _hop11.values())))
_doi11 = sum(1 for _i in range(1, len(_buoc11)) if _buoc11[_i] != _buoc11[_i - 1])
kiem("hộp zone NỞ RA nhiều lần trong một lô, không đứng yên",
     _doi11 >= 2, f"— đổi {_doi11} lần trong {_L['n']} khung")

kiem("và không bản ghi nào vượt quá con trỏ (không lộ tương lai)",
     all(z[1] <= _L["t"][_L["n"] - 1] for z in _hop11.values()))

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
