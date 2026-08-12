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
    "sl": {"tinh": "theo_pt", "value": 50}, "tp": {"tinh": "theo_pt", "value": 5000}})
m_bd9 = core.make_start_step("quản lý", "M1")
huy9 = core.make_action_step({"type": core.SUA_LENH, "name": "đóng",
                              "che_do": "dong_han"})
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
             l.trang_thai, l.vung_id], default=str).encode())
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

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
