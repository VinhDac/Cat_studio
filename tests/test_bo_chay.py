"""BỘ CHẠY — thứ tự trong một nhịp, luật lùi, và tính XÁC ĐỊNH.

Bài này dựng dữ liệu giả để KẾT QUẢ TÍNH TAY ĐƯỢC. Backtest sai thì không có gì kêu
lên — nó chỉ ra một con số khác, và con số nào cũng trông hợp lý.

Năm thứ được canh:

  1. **Thứ tự trong một nhịp**: sàn → engine → MANAGE từng lệnh → ENTRY một lượt.
     Đảo lại là lệnh vừa sinh bị quản lý ngay trong chính nến đẻ ra nó.
  2. **Luật lùi**: cổng trượt thì lùi về ngã rẽ gần nhất còn nhánh chưa thử — trừ khi
     lượt này đã chạm thị trường.
  3. **Hai khối Vào lệnh nối tiếp**: chỉ chặn khi hai lệnh KHÔNG cùng tồn tại được
     (core.md §5.1). Straddle — Mua trên, Bán dưới — phải chạy và phải ra ĐỦ hai lệnh.
  4. **NaN không lọt qua cổng**: chưa có vùng nén thì không vào lệnh.
  5. **Tất định**: chạy lại cùng dữ liệu ra cùng id, cùng giá, cùng nhật ký.

Chạy:  python tests\\test_bo_chay.py
"""
import io
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import nguon_nen as nn  # noqa: E402

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
def nen_m1(gia, t0=0):
    """Mỗi phần tử một nến M1 phẳng (o=h=l=c). Giá tính tay được, không nhiễu."""
    g = np.asarray(gia, dtype=float)
    a = np.empty(len(g), dtype=nn.DTYPE)
    a["t"] = np.arange(t0, t0 + len(g) * 60, 60, dtype=np.int64)[:len(g)]
    for k in ("o", "h", "l", "c"):
        a[k] = g
    a["vol"] = 1
    return a


def so_do(entry_steps, entry_edges, manage_steps=(), manage_edges=(), ts=None):
    return core.normalize_process({
        "name": "thử", "symbol": "X",
        "tham_so": list(ts or []) + [
            {"ten": "nguong_nen_bps", "nhan": "", "gia_tri": 1e9, "don_vi": "bps"},
            {"ten": "chu_ky_atr", "nhan": "", "gia_tri": 3, "don_vi": "nến"}],
        "entry": {"steps": list(entry_steps), "edges": list(entry_edges)},
        "manage": {"steps": list(manage_steps), "edges": list(manage_edges)},
    })


def cong(ten, toan_hang, phep, gia_tri, y=0.0, don_vi=None):
    c = {"trai": {"ten": toan_hang}, "phep": phep,
         "phai": {"value": gia_tri}}
    if don_vi:
        c["don_vi"] = don_vi
    st = core.make_action_step({
        "type": core.CHECK_COND, "name": ten, "conditions": [c]})
    st["pos"] = [0.0, y]
    return st


def vao(ten, y=0.0):
    st = core.make_action_step({
        "type": core.VAO_LENH, "name": ten, "huong": "mua", "loai": "market",
        "lot": 0.01, "sl": {"tinh": "gia", "value": 1.0},
        "tp": {"tinh": "R", "value": 2.0}})
    st["pos"] = [0.0, y]
    return st


def day(a, b):
    return {"from": a["id"], "to": b["id"], "port": "out"}


CD = bc.CaiDat(point=1.0, contract_size=1.0, spread_diem=0.0)

# ================= 1. chạy được và tất định =================
print("\n▸ Vào lệnh cơ bản")
bd = core.make_start_step("bắt đầu", "M5")
bd["pos"] = [0.0, 0.0]
g = cong("giá > 100", "close", ">", 100.0)
v = vao("mua")
d = so_do([bd, g, v], [day(bd, g), day(g, v)])

# 30 nến M1: 15 nến đầu giá 90 (cổng trượt), 15 nến sau giá 110 (cổng khớp).
kq = bc.chay(d, nen_m1([90.0] * 15 + [110.0] * 15), CD)
kiem("cổng trượt suốt đoạn giá thấp, khớp ở đoạn giá cao → CÓ lệnh",
     len(kq.so.lenh) > 0, f"— {len(kq.so.lenh)} lệnh")
kiem("lệnh THỊ TRƯỜNG khớp NGAY, không nằm treo",
     all(l.da_khop for l in kq.so.lenh))
kiem("id do TA cấp, đếm tăng từ L-0001", kq.so.lenh[0].id == "L-0001")

kq2 = bc.chay(d, nen_m1([90.0] * 15 + [110.0] * 15), CD)
kiem("TẤT ĐỊNH — chạy lại cùng dữ liệu ra cùng id, cùng giá, cùng số lượt",
     [l.id for l in kq2.so.lenh] == [l.id for l in kq.so.lenh]
     and [l.gia_khop for l in kq2.so.lenh] == [l.gia_khop for l in kq.so.lenh]
     and len(kq2.nhat_ky) == len(kq.nhat_ky))

# ================= 2. một lượt Entry, một lệnh =================
print("\n▸ Hai khối Vào lệnh nối tiếp — hỏi về LỆNH, không hỏi về hình vẽ")
# Đây là phép SOÁT, không phải luật của bộ chạy: bộ chạy phải làm ĐÚNG những gì sơ đồ
# vẽ, còn thứ không nên vẽ thì đừng cho vẽ. Bộ chạy tự dừng sau lệnh đầu là nó âm thầm
# bỏ qua một khối người dùng đã đặt vào — tệ hơn hẳn so với báo lỗi.
#
# ⚠ LUẬT ĐÃ ĐỔI (core.md §5.1). Bản trước chặn MỌI cặp Vào lệnh nối tiếp với lý do "một
# lượt sẽ đẻ ra HAI lệnh" — và nó khoá chết straddle nén, một chiến lược hợp lệ. Giờ chỉ
# chặn khi hai khối ra ĐÚNG MỘT LỆNH GIỐNG HỆT.
_trung = lambda d: any("GIỐNG HỆT" in p["message"]
                       for p in core.validate_process(d) if p["severity"] == "error")

v2 = vao("mua 2", y=100.0)                      # bản sao y hệt `v`, chỉ khác tên
kiem("hai khối Vào lệnh Y HỆT nối tiếp → LỖI (một lệnh viết hai lần)",
     _trung(so_do([bd, g, v, v2], [day(bd, g), day(g, v), day(v, v2)])))
kiem("hai khối Vào lệnh trên HAI nhánh khác nhau thì không sao",
     not _trung(so_do([bd, g, v, v2], [day(bd, g), day(g, v)])))

# STRADDLE: hai chân ngược hướng CÙNG TỒN TẠI ĐƯỢC → phải cho vẽ, và bộ chạy phải đẻ
# ra ĐỦ HAI lệnh trong MỘT lượt. `cham_thi_truong` chỉ cấm LÙI, không cấm đi tiếp.
vb = vao("bán", y=100.0)
vb["huong"] = "ban"
d2c = so_do([bd, g, v, vb], [day(bd, g), day(g, v), day(v, vb)])
kiem("straddle nối tiếp (Mua → Bán) → KHÔNG lỗi", not _trung(d2c))
kq2 = bc.chay(d2c, nen_m1([110.0] * 10), CD)
_luot = [r for r in kq2.nhat_ky if r["viec"]]
kiem("và bộ chạy đẻ ĐỦ HAI lệnh trong MỘT lượt",
     len(_luot) >= 1 and len(_luot[0]["viec"]) == 2
     and {l.huong for l in kq2.so.lenh} == {"mua", "ban"},
     f"— {len(kq2.so.lenh)} lệnh, {[l.huong for l in kq2.so.lenh]}")

# ---- NGÃ RẼ VÀ: cùng ngần ấy việc, nhưng vẽ TOẢ RA (core.md §5.1) -------------
# Hai chân straddle đối xứng và cùng lúc, nên hình toả ra mới đúng sự thật. Đầu nhánh
# toàn hành động thì không có gì để chọn → bộ chạy làm hết.
print("\n▸ Ngã rẽ VÀ — toả ra hai hành động thì làm cả hai")
d2d = so_do([bd, g, v, vb], [day(bd, g), day(g, v), day(g, vb)])
# Soát ĐÚNG luật rẽ nhánh, không soát cả bảng: `cong()` ở file này cố tình dựng cổng
# thiếu khung thời gian nên `validate_process` luôn có sẵn một lỗi khác, không liên quan.
_nhanh = [p["message"] for p in core.validate_process(d2d)
          if p["severity"] == "error"
          and ("TRỘN" in p["message"] or "cổng kiểm tra" in p["message"])]
kiem("rẽ 2 nhánh toàn Vào lệnh → luật rẽ nhánh KHÔNG kêu (là ngã rẽ VÀ)",
     not _nhanh, f"— {_nhanh}")
kq3 = bc.chay(d2d, nen_m1([110.0] * 10), CD)
r3 = next((x for x in kq3.nhat_ky if x["viec"]), None)
kiem("bộ chạy đi CẢ HAI nhánh → hai lệnh, hai hướng",
     r3 is not None and len(r3["viec"]) == 2
     and {l.huong for l in kq3.so.lenh} == {"mua", "ban"},
     f"— {[l.huong for l in kq3.so.lenh]}")
kiem("`duong` giữ CẢ HAI khối, không chỉ nhánh cuối",
     r3 is not None and v["id"] in r3["duong"] and vb["id"] in r3["duong"],
     f"— {len(r3['duong']) if r3 else 0} khối")
kiem("mỗi VIỆC mang `khoi` của chính nó — nhật ký nói được lệnh nào ở khối nào",
     r3 is not None and [x.get("khoi") for x in r3["viec"]] == [v["id"], vb["id"]])

# ⚠ CHỐT AN TOÀN. Ngã rẽ HOẶC vẫn phải giữ luật §12.5a: bắn lệnh xong thì CẤM lùi thử
# nhánh khác. Đây là thứ dễ vỡ nhất khi thêm ngã rẽ VÀ, vì cả hai đi qua cùng một chỗ.
# Kịch bản: nhánh trên (cổng khớp) vào lệnh rồi mới cụt; nhánh dưới KHÔNG được chạy.
print("\n▸ Ngã rẽ HOẶC vẫn CẤM lùi sau khi đã chạm thị trường")
ok1 = cong("giá > 100", "close", ">", 100.0, y=0.0)
cut = cong("giá > 999", "close", ">", 999.0, y=0.0)      # luôn trượt → cụt phía dưới
ok2 = cong("giá > 100 (dưới)", "close", ">", 100.0, y=200.0)
v_tren, v_duoi = vao("lệnh nhánh trên", y=0.0), vao("lệnh nhánh dưới", y=200.0)
d4 = so_do([bd, ok1, ok2, v_tren, cut, v_duoi],
           [day(bd, ok1), day(bd, ok2), day(ok1, v_tren), day(v_tren, cut),
            day(ok2, v_duoi)])
kq4 = bc.chay(d4, nen_m1([110.0] * 10), CD)
_r4 = next((x for x in kq4.nhat_ky if x["viec"]), None)
kiem("nhánh trên vào lệnh rồi cụt → KHÔNG lùi sang nhánh dưới (đúng 1 lệnh/lượt)",
     _r4 is not None and len(_r4["viec"]) == 1
     and v_duoi["id"] not in _r4["duong"],
     f"— {len(_r4['viec']) if _r4 else 0} việc")

# ================= 3. luật lùi =================
print("\n▸ Luật lùi — cổng trượt thì thử nhánh dưới")
# Ngã rẽ: nhánh TRÊN (y=0) đòi giá > 200 (trượt), nhánh DƯỚI (y=50) đòi giá > 100 (khớp).
tren = cong("giá > 200", "close", ">", 200.0, y=0.0)
duoi = cong("giá > 100", "close", ">", 100.0, y=50.0)
vt, vd = vao("từ nhánh trên", y=10.0), vao("từ nhánh dưới", y=60.0)
d3 = so_do([bd, tren, duoi, vt, vd],
           [day(bd, tren), day(bd, duoi), day(tren, vt), day(duoi, vd)])
kq = bc.chay(d3, nen_m1([110.0] * 10), CD)
r = next(x for x in kq.nhat_ky if x["viec"])
kiem("nhánh trên trượt → lùi về ngã rẽ, thử nhánh dưới, và VÀO LỆNH",
     len(kq.so.lenh) > 0 and vd["id"] in r["duong"], f"— đường {len(r['duong'])} khối")
kiem("nhật ký ghi CẢ HAI cổng đã thử, không chỉ cổng cuối",
     len(r["cong"]) == 2 and r["cong"][0]["khop"] is False
     and r["cong"][1]["khop"] is True, f"— {[c['khop'] for c in r['cong']]}")
kiem("và ghi đủ hai vế của điều kiện làm trượt",
     r["cong"][0]["ve"][0]["trai"] == 110.0 and r["cong"][0]["ve"][0]["phai"] == 200.0,
     f"— {r['cong'][0]['ve']}")

# Cổng SÂU trượt SAU khi đã vào lệnh → hết lượt ngay, KHÔNG lùi thử nhánh dưới.
sau = cong("giá > 999", "close", ">", 999.0, y=20.0)
d4 = so_do([bd, tren, duoi, vt, sau, vd],
           [day(bd, tren), day(bd, duoi), day(tren, vt), day(vt, sau), day(duoi, vd)])
tren2 = dict(tren)
d4["entry"]["steps"][1]["conditions"][0]["phai"] = 100.0     # nhánh trên KHỚP
kq = bc.chay(d4, nen_m1([110.0] * 10), CD)
r = next(x for x in kq.nhat_ky if x["viec"])
kiem("đã CHẠM THỊ TRƯỜNG rồi mà cổng sau trượt → hết lượt, không lùi sang nhánh kia",
     vd["id"] not in r["duong"] and r["ket"] == "het_luot",
     f"— {r['ket']}, {len(r['duong'])} khối")

# ================= 4. NaN không lọt qua cổng =================
print("\n▸ NaN không lọt qua cổng")
g_atr = cong("ATR < 999", "atr", "<", 999.0)
d5 = so_do([bd, g_atr, v], [day(bd, g_atr), day(g_atr, v)])
kq = bc.chay(d5, nen_m1([100.0] * 20), CD)
dau = [x for x in kq.nhat_ky if x["tab"] == "entry"][:3]
kiem("nến đầu chưa đủ dữ liệu ATR → cổng TRƯỢT, không vào lệnh",
     all(x["ket"] == "het_luot" for x in dau), f"— {[x['ket'] for x in dau]}")
kiem("và nhật ký ghi vế trái là None (chưa có), không phải 0",
     dau[0]["cong"][0]["ve"][0]["trai"] is None,
     f"— {dau[0]['cong'][0]['ve'][0]}")

# `zone_range_atr` đã rời kho — giờ là `zone_range` so bằng ĐƠN VỊ `× ATR`.
g_vung = cong("bề rộng zone ≤ 4 × ATR", "zone_range", "<=", 4.0, don_vi="atr")
d6 = so_do([bd, g_vung, v], [day(bd, g_vung), day(g_vung, v)],
           ts=[{"ten": "khong_dung", "nhan": "", "gia_tri": 0, "don_vi": "bps"}])
d6["tham_so"] = [dict(t, gia_tri=0.0) if t["ten"] == "nguong_nen_bps" else t
                 for t in d6["tham_so"]]          # ngưỡng 0 → không nến nào là nến nén
kq = bc.chay(d6, nen_m1([100.0] * 20), CD)
kiem("KHÔNG có vùng nén nào được sinh ra", len(kq.so.zone) == 0)
kiem("toán hạng vùng là NaN → cổng TRƯỢT → KHÔNG vào lệnh", len(kq.so.lenh) == 0)

# ================= 5. thứ tự trong một nhịp =================
print("\n▸ Thứ tự trong một nhịp: MANAGE trước ENTRY")
huy = core.make_action_step({"type": core.SUA_LENH, "name": "huỷ",
                             "che_do": "ket_thuc"})
huy["pos"] = [0.0, 10.0]
m_bd = core.make_start_step("quản lý", "M1")
m_bd["pos"] = [0.0, 0.0]
m_cong = cong("lãi ≥ −99R", "lenh_lai_R", ">=", -99.0)
d7 = so_do([bd, g, v], [day(bd, g), day(g, v)],
           [m_bd, m_cong, huy], [day(m_bd, m_cong), day(m_cong, huy)])
kq = bc.chay(d7, nen_m1([110.0] * 20), CD)
e = [x["seq"] for x in kq.nhat_ky if x["tab"] == "entry"]
m = [x["seq"] for x in kq.nhat_ky if x["tab"] == "manage"]
# ⚠ Bản trước so LỎNG: "mỗi lượt entry có MỘT lượt manage nào đó đứng trước" — đúng cả
# khi hai lượt thuộc HAI NHỊP KHÁC NHAU, tức nó không canh đúng thứ định canh. Và `d7`
# đóng lệnh ngay lượt Manage đầu tiên nên KHÔNG nhịp nào có cả hai tab — phép so cũ chạy
# trên tập rỗng mà vẫn xanh.
#
# Kịch bản riêng: cổng Manage KHÔNG BAO GIỜ qua, nên lệnh sống suốt và Manage chạy ở mọi
# nhịp M1 — kể cả những nhịp trùng biên M5, đúng chỗ hai tab gặp nhau.
_m_khong = cong("lãi ≥ 999R", "lenh_lai_R", ">=", 999.0)
_d7b = so_do([bd, g, v], [day(bd, g), day(g, v)],
             [m_bd, _m_khong, huy], [day(m_bd, _m_khong), day(_m_khong, huy)])
_kq7b = bc.chay(_d7b, nen_m1([110.0] * 30), CD)
_theo_j = {}
for _x in _kq7b.nhat_ky:
    _theo_j.setdefault(_x["j"], {}).setdefault(_x["tab"], []).append(_x["seq"])
_ca_hai = [v for v in _theo_j.values() if "entry" in v and "manage" in v]
kiem("dữ liệu thử CÓ nhịp chứa cả hai tab (không thì phép dưới rỗng)",
     bool(_ca_hai), f"— {len(_ca_hai)}/{len(_theo_j)} nhịp có cả hai")
kiem("lượt Manage của một nhịp luôn đứng TRƯỚC lượt Entry của CHÍNH nhịp đó",
     all(max(v["manage"]) < min(v["entry"]) for v in _ca_hai),
     f"— {len(_ca_hai)} nhịp có cả hai tab")
sinh = {v["lenh_id"]: x["seq"] for x in kq.nhat_ky for v in x["viec"]
        if v["loai"] == "lenh_dat"}
kiem("lệnh vừa sinh KHÔNG bị quản lý trong CÙNG lượt đẻ ra nó",
     all(x["seq"] > sinh[x["lenh_id"]] for x in kq.nhat_ky
         if x["tab"] == "manage" and x["lenh_id"] in sinh))

# --- sụt giảm phải đếm cả lệnh do khối "Đóng hẳn" đóng ---
#
# `ghi_tien` là closure trong `chay()`, còn `_sua_lenh` là hàm MODULE nên với không tới.
# Trước đây nhánh "Đóng hẳn" đóng lệnh xong KHÔNG ghi tiền, nên `drawdown_pt` lúc chạy
# đọc 0 % trong khi sụt giảm thật đã mấy chục phần trăm. Toán hạng đó chính là thứ người
# ta dùng làm cầu dao ("sụt giảm > 10 % thì ngừng vào lệnh") — cầu dao chết mà không ai hay.
#
# ⚠ Kịch bản phải CÓ LỖ THẬT. Dùng lại d7 (giá phẳng 110) thì cả hai đường cùng ra 0 %
# và phép so khớp một cách vô nghĩa — đã thử, nó BỎ LỌT đúng con bọ này. Giá rơi đều thì
# mọi lệnh mua đều lỗ, và hai đường buộc phải nói cùng một con số khác 0.
#
# Phép so bắt được vì hai vế ra từ HAI đường khác nhau: vế trái cộng dồn LÚC CHẠY, vế
# phải `_thong_ke` duyệt lại sổ lệnh SAU khi chạy xong.
# Kịch bản TỰ CHỨA: vốn nhỏ + lot lớn + giá rơi đều, để lỗ đủ to mà `round(…, 2)` không
# nuốt mất. Không mượn `CD`/`vao()` ở trên vì chúng chỉnh cho bài khác (lot 0,01 trên vốn
# 10.000 ra sụt giảm 0,0001 % → làm tròn thành 0,00 và phép so lại khớp vô nghĩa).
CD9 = bc.CaiDat(point=1.0, contract_size=1.0, spread_diem=0.0, deposit=1000.0)
bd9 = core.make_start_step("bắt đầu", "M5")
v9 = core.make_action_step({
    "type": core.VAO_LENH, "name": "mua", "huong": "mua", "loai": "market", "lot": 1.0,
    # `pt` (% của giá) đã bỏ — nó là `bps` chia 100, hai tên cho một phép. Cùng khoảng
    # cách y hệt: 50 % = 5.000 bps · 5.000 % = 500.000 bps.
    "sl": {"tinh": "bps", "value": 5000}, "tp": {"tinh": "bps", "value": 500000}})
m_bd9 = core.make_start_step("quản lý", "M1")
huy9 = core.make_action_step({"type": core.SUA_LENH, "name": "đóng",
                              "che_do": "ket_thuc"})
d9 = so_do([bd9, v9], [day(bd9, v9)], [m_bd9, huy9], [day(m_bd9, huy9)])
kq9 = bc.chay(d9, nen_m1([100.0 - k * 0.5 for k in range(120)]), CD9)
kiem("sụt giảm LÚC CHẠY khớp sụt giảm BÁO CÁO khi khối Sửa lệnh đóng lệnh",
     kq9.thong_ke["drawdown_pt"] > 0
     and abs(kq9._ct.drawdown_pt() - kq9.thong_ke["drawdown_pt"]) < 0.01,
     f"— lúc chạy {kq9._ct.drawdown_pt():.2f} % · báo cáo "
     f"{kq9.thong_ke['drawdown_pt']:.2f} %")

# ================= 6. thống kê & lệnh còn sống lúc hết dữ liệu =================
print("\n▸ Kết thúc backtest")
kiem("không còn lệnh nào SỐNG sau khi hết dữ liệu", not kq.so.dang_song())
kiem("lệnh đã khớp mà chưa đóng → ghi lý do `het_du_lieu`, không âm thầm bỏ",
     any(l.ly_do_dong == "het_du_lieu" for l in kq.so.lenh))
kiem("thống kê có đủ số lệnh, thắng/thua, tổng R, drawdown",
     {"so_lenh", "thang", "thua", "tong_R", "drawdown_pt", "nen_mo_ho"}
     <= set(kq.thong_ke))
kiem("`lenh_tai(i)` lọc theo nến, không cần ảnh chụp nào",
     len(kq.lenh_tai(0)) == 0 and isinstance(kq.lenh_tai(len(kq.nen5) - 1), list))


# ============= 7. toán hạng GIÁ đọc ĐÚNG KHUNG của chính nó =============
#
# Bài này sinh ra vì một lỗi đã lọt HAI LẦN: `close(M15, nến[1])` trả về giá M5, tức cổng
# xu hướng so Close M5 với MA M15. Lần vá đầu dựng đúng cột theo khung nhưng quên sửa chỗ
# ĐỌC, nên cột dựng ra không ai dùng — và cả 6 bài kiểm khi đó vẫn xanh, vì không bài nào
# soát GIÁ TRỊ LÚC CHẠY của một toán hạng giá.
#
# Cách kiểm cố ý KHÔNG so với `doc_cot`: so hai đường trong cùng một cài đặt thì cả hai
# cùng sai vẫn "khớp". Ở đây tự gộp M15 từ mảng M1 thô rồi tra tay nến M15 ĐÃ ĐÓNG gần
# nhất — một sự thật độc lập, không mượn gì của bộ chạy.
print("\n▸ Toán hạng giá đọc đúng khung của chính nó")
from cat_studio import tinh_toan as tt  # noqa: E402

# Giá TĂNG ĐỀU: mỗi nến M1 một giá khác nhau, nên close M5 và close M15 không bao giờ
# tình cờ bằng nhau — đọc nhầm khung là lộ ra ngay.
nen_g = nen_m1([100.0 + k * 0.1 for k in range(600)])
d8 = so_do([bc_start := core.make_start_step(nhip="M5")], [])
ct_g = bc.ChuongTrinh(d8, nen_g, CD)
ctx_g = bc.Ctx(ct_g, None, ct_g.ts)
o_g = {"ten": "close", "tf": "M15", "shift": 1}
ct_g._xin_cot_gia(o_g, None)                    # như lúc biên dịch một sơ đồ thật

n15 = tt.gop(nen_g, "M15")
d15, d5 = tt.moc_dong(n15, "M15"), tt.moc_dong(ct_g.nen5, ct_g.tf5)
sai_khung = lo_truoc = so_sanh = khac_m5 = 0
for i_ in range(len(ct_g.nen5)):
    ctx_g.i = i_
    v = bc._lay_toan_hang(o_g, ctx_g)
    if v != v:
        continue
    so_sanh += 1
    j_ = int(np.searchsorted(d15, d5[i_], side="right")) - 1
    if j_ < 0 or abs(float(n15["c"][j_]) - v) > 1e-9:
        sai_khung += 1
    if j_ >= 0 and d15[j_] > d5[i_]:            # nến M15 đó phải ĐÃ đóng
        lo_truoc += 1
    if abs(v - float(ct_g.nen5["c"][i_])) > 1e-9:
        khac_m5 += 1

kiem("close(M15) trả đúng giá đóng nến M15, không phải nến M5",
     so_sanh > 0 and sai_khung == 0, f"— {so_sanh} nến so, {sai_khung} sai")
kiem("và nến M15 đó đã ĐÓNG rồi (không nhìn trước tương lai)", lo_truoc == 0)
# Chốt chặn cuối: nếu ai đó lại làm CẢ HAI đường cùng đọc `nen5` thì hai phép trên vẫn
# khớp. Giá trị phải THẬT SỰ khác close M5 ở PHẦN LỚN số nến mới chứng minh nó đọc khung
# kia. Không đòi khác ở MỌI nến: cứ 3 nến M5 lại có một nến đóng cùng lúc với nến M15,
# lúc đó hai giá bằng nhau là ĐÚNG.
kiem("giá trị khác close M5 ở phần lớn nến — bằng chứng đang đọc đúng khung M15",
     khac_m5 > so_sanh * 0.5, f"— khác ở {khac_m5}/{so_sanh} nến")

# ============ ĐI TỪNG NHỊP phải ra ĐÚNG cái mà chạy trọn ra ============
#
# `chay()` giờ chỉ là vòng lặp quanh `PhienChay.mot_nhip`. Cửa sổ Live sẽ gọi thẳng
# `mot_nhip` mỗi khi sàn đóng một nến — nghĩa là hai đường đó BẮT BUỘC phải cho ra cùng
# một thứ, nếu không thì lời hứa "test như nào thì live như thế" là nói dối.
#
# Bài này lái tay `PhienChay` và so với `chay()` bằng vân tay phủ MỌI trường của MỌI
# lệnh và MỌI lượt — không phải vài con số tổng hợp, vì tổng hợp che được sai lệch.
print("\n▸ Đi từng nhịp == chạy trọn")


def _van_tay(kq):
    import hashlib
    hl = hashlib.sha256()
    for l in kq.so.lenh:
        hl.update(json.dumps(
            [l.id, l.huong, l.loai, l.lot, l.nen_dat, l.nen_khop, l.nen_dong, l.j_khop,
             l.gia_dat, l.gia_khop, l.gia_dong, l.sl, l.tp, l.R, l.ly_do_dong,
             l.trang_thai, l.zone_id], default=str).encode())
    hn = hashlib.sha256()
    for r in kq.nhat_ky:
        hn.update(json.dumps(
            [r["j"], r["nen"], r["tab"], r["ket"], r["duong"], r["lenh_id"],
             r["viec"], r["cong"], r["khoi"]], default=str).encode())
    return hl.hexdigest(), hn.hexdigest()


nen_dai = nen_m1([100.0 + (k % 37) * 0.1 for k in range(4000)])
kq_tron = bc.chay(d9, nen_dai, CD9)

# Lái tay: đúng những gì `chay()` làm, nhưng gọi từng nhịp một.
phien = bc.PhienChay(d9, nen_dai, CD9)
for jj in range(len(phien.ct.nen1)):
    phien.mot_nhip(jj)
kq_nhip = phien.ket_thuc()

vt_tron, vt_nhip = _van_tay(kq_tron), _van_tay(kq_nhip)
kiem("cùng số lệnh", len(kq_tron.so.lenh) == len(kq_nhip.so.lenh),
     f"— {len(kq_tron.so.lenh)} lệnh")
kiem("cùng số lượt nhật ký", len(kq_tron.nhat_ky) == len(kq_nhip.nhat_ky),
     f"— {len(kq_tron.nhat_ky)} lượt")
kiem("vân tay MỌI TRƯỜNG của MỌI LỆNH khớp", vt_tron[0] == vt_nhip[0])
kiem("vân tay MỌI LƯỢT nhật ký khớp", vt_tron[1] == vt_nhip[1])
kiem("thống kê khớp từng con số",
     all(str(kq_tron.thong_ke[k]) == str(kq_nhip.thong_ke.get(k))
         for k in kq_tron.thong_ke),
     f"— {len(kq_tron.thong_ke)} chỉ số")

# Và `mot_nhip` phải CHỊU ĐƯỢC việc bị gọi rời rạc — live gọi nó theo nhịp thật, có thể
# trễ, có thể ngắt quãng. Chạy nửa chừng rồi mới chạy tiếp phải ra đúng như chạy liền.
p2 = bc.PhienChay(d9, nen_dai, CD9)
for jj in range(0, 1500):
    p2.mot_nhip(jj)
giua = len(p2.so.lenh)
for jj in range(1500, len(p2.ct.nen1)):
    p2.mot_nhip(jj)
kiem("dừng giữa chừng rồi chạy tiếp — vẫn ra đúng cái đó",
     _van_tay(p2.ket_thuc())[0] == vt_tron[0], f"— giữa chừng có {giua} lệnh")

# ============ Bỏ `shift` khỏi toán hạng giá KHÔNG đổi hành vi ============
#
# `shift` là ô số THỨ BA trên hàng điều kiện — cùng hình dạng với ô "chu kỳ" của ATR
# nhưng nghĩa khác hẳn, nên đã bỏ (xem `kho/nen_tang.py`). Bỏ được là vì `doc_cot` hiểu
# "thiếu shift" ĐÚNG BẰNG `shift = 1`: `i -= max(0, shift - 1)` cho ra cùng một cây nến.
#
# Đây là chỗ canh lời hứa đó — canh bằng HÀNH VI chứ không bằng đọc lại công thức. Sai
# ở đây nghĩa là mọi file đã lưu (đều ghi `shift: 1`) âm thầm đọc lệch một cây nến.
print("\n▸ Bỏ `shift` — file cũ phải chạy y hệt")
_gia_soc = [90.0] * 15 + [110.0] * 15 + [90.0] * 15


def _chay_shift(co_shift):
    b = core.make_start_step("bắt đầu", "M5")
    b["pos"] = [0.0, 0.0]
    b["id"] = "bd_shift"        # `make_start_step` tự sinh id — xem chú thích dưới
    tr = {"ten": "close", "tf": "M5"}
    if co_shift:
        tr["shift"] = 1              # đúng cách mọi file đã lưu đang ghi
    # ID ĐẶT TAY cho MỌI khối, kể cả khối Bắt đầu. `make_*_step` tự sinh id, nên hai lần
    # dựng ra hai bộ id khác nhau — nhật ký ghi `duong`/`khoi` theo id, và vân tay lệch
    # vì một lý do CHẲNG LIÊN QUAN gì tới `shift`. (Gỡ mất một lượt: lệnh khớp từng ký
    # tự, chỉ nhật ký lệch, và chỗ lệch là id khối Bắt đầu.)
    gg = core.make_action_step({"id": "g_shift", "type": core.CHECK_COND,
                                "name": "giá > 100",
                                "conditions": [{"trai": tr, "phep": ">",
                                                "phai": {"value": 100.0}}]})
    gg["pos"] = [1.0, 0.0]
    vv = core.make_action_step({"id": "v_shift", "type": core.VAO_LENH, "name": "mua",
                                "huong": "mua", "loai": "market", "lot": 0.01,
                                "entry": {"moc": "gia_hien_tai"},
                                "sl": {"tinh": "gia", "value": 5.0}})
    vv["pos"] = [2.0, 0.0]
    return bc.chay(so_do([b, gg, vv], [day(b, gg), day(gg, vv)]),
                   nen_m1(_gia_soc), CD)


_cu, _moi = _chay_shift(True), _chay_shift(False)
kiem("file GHI `shift: 1` và file KHÔNG ghi ra cùng một kết quả",
     _van_tay(_cu) == _van_tay(_moi) and len(_moi.so.lenh) > 0,
     f"— {len(_cu.so.lenh)} lệnh / {len(_moi.so.lenh)} lệnh")
kiem("chuẩn hoá VỨT `shift` đi, không để lại trong file",
     "shift" not in core.normalize_action({
         "type": core.CHECK_COND,
         "conditions": [{"trai": {"ten": "close", "tf": "M5", "shift": 1},
                         "phep": ">", "phai": {"value": 1}}],
     })["conditions"][0]["trai"])

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
