"""BỘ CHẠY — thứ tự trong một nhịp, luật lùi, và tính XÁC ĐỊNH.

Bài này dựng dữ liệu giả để KẾT QUẢ TÍNH TAY ĐƯỢC. Backtest sai thì không có gì kêu
lên — nó chỉ ra một con số khác, và con số nào cũng trông hợp lý.

Năm thứ được canh:

  1. **Thứ tự trong một nhịp**: sàn → engine → MANAGE từng lệnh → ENTRY một lượt.
     Đảo lại là lệnh vừa sinh bị quản lý ngay trong chính nến đẻ ra nó.
  2. **Luật lùi**: cổng trượt thì lùi về ngã rẽ gần nhất còn nhánh chưa thử — trừ khi
     lượt này đã chạm thị trường.
  3. **Một lượt Entry sinh nhiều nhất MỘT lệnh** (hệ quả của luật trên).
  4. **NaN không lọt qua cổng**: chưa có vùng nén thì không vào lệnh.
  5. **Tất định**: chạy lại cùng dữ liệu ra cùng id, cùng giá, cùng nhật ký.

Chạy:  python tests\\test_bo_chay.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import bo_chay as bc  # noqa: E402
import core  # noqa: E402
import nguon_nen as nn  # noqa: E402

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


def cong(ten, toan_hang, phep, gia_tri, y=0.0):
    st = core.make_action_step({
        "type": core.CHECK_COND, "name": ten,
        "conditions": [{"trai": {"ten": toan_hang}, "phep": phep,
                        "phai_loai": "so", "phai": gia_tri}]})
    st["pos"] = [0.0, y]
    return st


def vao(ten, y=0.0):
    st = core.make_action_step({
        "type": core.VAO_LENH, "name": ten, "huong": "mua", "loai": "market",
        "lot": 0.01, "sl": {"tinh": "theo_gia", "value": 1.0},
        "tp": {"tinh": "theo_R", "value": 2.0}})
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
print("\n▸ Một lượt Entry sinh nhiều nhất MỘT lệnh")
# Đây là phép SOÁT, không phải luật của bộ chạy: bộ chạy phải làm ĐÚNG những gì sơ đồ
# vẽ, còn thứ không nên vẽ thì đừng cho vẽ. Bộ chạy tự dừng sau lệnh đầu là nó âm thầm
# bỏ qua một khối người dùng đã đặt vào — tệ hơn hẳn so với báo lỗi.
v2 = vao("mua 2", y=100.0)
d2 = so_do([bd, g, v, v2], [day(bd, g), day(g, v), day(v, v2)])
loi = [p["message"] for p in core.validate_process(d2) if p["severity"] == "error"]
kiem("hai khối Vào lệnh trên CÙNG đường → báo LỖI (cổng \"số lệnh chờ\" chặn không nổi)",
     any("HAI lệnh" in m for m in loi), f"— {[m[:44] for m in loi]}")
d2b = so_do([bd, g, v, v2], [day(bd, g), day(g, v)])
kiem("hai khối Vào lệnh trên HAI nhánh khác nhau thì không sao",
     not any("HAI lệnh" in p["message"] for p in core.validate_process(d2b)))

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

g_vung = cong("bề rộng vùng ÷ ATR ≤ 4", "rong_vung_atr", "<=", 4.0)
d6 = so_do([bd, g_vung, v], [day(bd, g_vung), day(g_vung, v)],
           ts=[{"ten": "khong_dung", "nhan": "", "gia_tri": 0, "don_vi": "bps"}])
d6["tham_so"] = [dict(t, gia_tri=0.0) if t["ten"] == "nguong_nen_bps" else t
                 for t in d6["tham_so"]]          # ngưỡng 0 → không nến nào là nến nén
kq = bc.chay(d6, nen_m1([100.0] * 20), CD)
kiem("KHÔNG có vùng nén nào được sinh ra", len(kq.so.vung) == 0)
kiem("toán hạng vùng là NaN → cổng TRƯỢT → KHÔNG vào lệnh", len(kq.so.lenh) == 0)

# ================= 5. thứ tự trong một nhịp =================
print("\n▸ Thứ tự trong một nhịp: MANAGE trước ENTRY")
huy = core.make_action_step({"type": core.SUA_LENH, "name": "huỷ", "che_do": "dong_han"})
huy["pos"] = [0.0, 10.0]
m_bd = core.make_start_step("quản lý", "M1")
m_bd["pos"] = [0.0, 0.0]
m_cong = cong("lãi ≥ −99R", "lenh_lai_R", ">=", -99.0)
d7 = so_do([bd, g, v], [day(bd, g), day(g, v)],
           [m_bd, m_cong, huy], [day(m_bd, m_cong), day(m_cong, huy)])
kq = bc.chay(d7, nen_m1([110.0] * 20), CD)
e = [x["seq"] for x in kq.nhat_ky if x["tab"] == "entry"]
m = [x["seq"] for x in kq.nhat_ky if x["tab"] == "manage"]
kiem("lượt Manage của một nhịp luôn đứng TRƯỚC lượt Entry của chính nhịp đó",
     all(any(y < x for y in m) for x in e[1:]) if m else False,
     f"— {len(m)} lượt manage / {len(e)} lượt entry")
sinh = {v["lenh_id"]: x["seq"] for x in kq.nhat_ky for v in x["viec"]
        if v["loai"] == "lenh_dat"}
kiem("lệnh vừa sinh KHÔNG bị quản lý trong CÙNG lượt đẻ ra nó",
     all(x["seq"] > sinh[x["lenh_id"]] for x in kq.nhat_ky
         if x["tab"] == "manage" and x["lenh_id"] in sinh))

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

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
