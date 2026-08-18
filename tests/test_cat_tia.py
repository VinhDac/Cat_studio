"""PHÂN BỔ · CẮT TỈA · CỬA ĐỀU — một lượt chạy tách thành một con số cho MỖI khối.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Bế tắc lớn nhất của §18.5: một sơ đồ là ~40 nước đi và nhận đúng MỘT con số ở cuối, nên
không cách nào biết nước nào hay. Ba module này phá nó — nhưng chúng phá bằng cách nói ra
những câu RẤT MẠNH (*"khối này chắc chắn bỏ được"*), mà câu mạnh thì sai một chút là hỏng
to: người dùng gỡ một khối tưởng vô hại rồi kết quả đổi mà không hiểu vì sao.

Bốn điều bài này canh:

  1. ⭐ **TIỀN gắn đúng KHỐI.** `Lenh.khoi` là trường thêm vào cho việc này. Đã tin nhầm
     `Lenh.sinh_tai` một lần (chú thích của nó ghi "id khối" nhưng nó là CHỈ SỐ NẾN) —
     bảng tiền ra rỗng trơn trong khi sổ có 113 lệnh.
  2. ⚠ **"Chắc chắn bỏ được" CHỈ gồm khối chưa bao giờ được ĐẾN.** Hai cái bẫy: cổng
     luôn khớp vẫn có thể đang nuôi zone; khối Vào lệnh đẻ 0 lệnh vẫn bật
     `cham_thi_truong` và cấm lùi. Cả hai đều KHÔNG được nói là bỏ được.
  3. **Cắt theo NHÁNH**: thứ biến mất đúng bằng thứ chỉ tới được qua nó; khối còn đường
     khác thì ở lại; cắt xong không hợp lệ thì trả `None` chứ không chạy một sơ đồ méo.
  4. ⭐ **Luật ĐA SỐ CỬA SỔ.** Đo được: cắt nhánh BÁN của sơ đồ mẫu cho `+0,3872` ở một
     quý — rất thuyết phục và SAI, vì cả sáu quý chỉ 4/6 là tốt hơn.

Chạy:  python tests\\test_cat_tia.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import cat_tia, cham_diem, core, phan_bo  # noqa: E402
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


# --------------------------------------------------------------------- đồ thử
def nen_m1(gia, t0=1_700_000_000):
    g = np.asarray(gia, dtype=float)
    a = np.empty(len(g), dtype=nn.DTYPE)
    a["t"] = np.arange(t0, t0 + len(g) * 60, 60, dtype=np.int64)[:len(g)]
    for k in ("o", "h", "l", "c"):
        a[k] = g
    a["vol"] = 1
    return a


def cong(ten, phep, gia_tri, x=0.0, y=0.0):
    st = core.make_action_step({
        "type": core.CHECK_COND, "name": ten,
        # ⚠ `tf` BẮT BUỘC. Thiếu nó là sơ đồ không qua soát tĩnh — mà `test_bo_chay`
        # không bao giờ gọi `validate_process` nên chỗ này chưa từng lộ ra ở đó.
        "conditions": [{"trai": {"ten": "close", "tf": "M15"}, "phep": phep,
                        "phai": {"value": gia_tri}}]})
    st["pos"] = [x, y]
    return st


def vao(ten, x=0.0, y=0.0):
    st = core.make_action_step({
        "type": core.VAO_LENH, "name": ten, "huong": "mua", "loai": "market",
        "rui_ro": 0.5, "sl": {"tinh": "gia", "value": 1.0},
        "tp": {"tinh": "R", "value": 2.0}})
    st["pos"] = [x, y]
    return st


def day(a, b):
    return {"from": a["id"], "to": b["id"], "port": "out"}


# Sơ đồ thử — cố ý dựng đủ BA trạng thái của một cổng, để bảng phân bổ có gì mà nói:
#
#     bắt đầu → g0 ─┬→ g1 KHÔNG BAO GIỜ đúng  → v1   ← cổng bị XÉT mà chẳng khớp lần nào
#                   └→ g2 LUÔN đúng           → v2   ← nhánh thật sự chạy
#
# ⚠ Hai đầu nhánh phải LỆCH NHAU theo trục dọc. Nằm ngang nhau là soát tĩnh báo lỗi —
# và đó là lỗi thật, vì nhìn trên canvas thì không biết nhánh nào chạy trước.
BD = core.make_start_step("bắt đầu", "M15")
BD["pos"] = [0.0, 0.0]
G0 = cong("cổng ngoài", ">", 0.0, 300.0, 0.0)
G1 = cong("không bao giờ", "<", 0.0, 600.0, -200.0)
V1 = vao("mua - nhánh chết", 900.0, -200.0)
G2 = cong("luôn đúng", ">", 0.0, 600.0, 200.0)
V2 = vao("mua - nhánh sống", 900.0, 200.0)
DOC = core.normalize_process({
    "name": "thử cắt tỉa", "symbol": "X",
    "tham_so": [core.make_tham_so(k, "chu kỳ ATR", 14, "nen")
                for k in core.THAM_SO_NGAM],
    "entry": {"steps": [BD, G0, G1, V1, G2, V2],
              "edges": [day(BD, G0), day(G0, G1), day(G1, V1),
                        day(G0, G2), day(G2, V2)]},
    "manage": {"steps": [], "edges": []},
})
N3T = 7 * 24 * 60 * 3
RAMP = [100.0 + 300.0 * k / N3T for k in range(N3T)]
NEN = nen_m1(RAMP)
CD = bc.CaiDat(point=1.0, contract_size=1.0, spread_diem=0.0)

kiem("sơ đồ thử hợp lệ",
     not [p for p in core.validate_process(DOC) if p["severity"] == "error"])

# ================= 1. PHÂN BỔ =================
print("\n▸ Phân bổ — tiền theo khối, cổng chặn cái gì")
KQ = bc.chay(DOC, NEN, CD, ghi_nhat_ky=False, dem_khoi=True)
PB = phan_bo.theo_khoi(KQ, CD)
t = {x["khoi"]: x for x in PB["tien"]}
g = {x["khoi"]: x for x in PB["cong"]}

kiem("có bộ đếm", PB["co_dem"])
kiem("⭐ TIỀN gắn đúng khối — nhánh sống có lệnh, nhánh chết không",
     t[V2["id"]]["so_lenh"] > 0 and t[V1["id"]]["so_lenh"] == 0,
     f"— sống {t[V2['id']]['so_lenh']} lệnh · chết {t[V1['id']]['so_lenh']}")
kiem("tổng tiền theo khối = tổng tiền cả sổ",
     abs(sum(x["tien"] for x in PB["tien"])
         - sum(bc.lai_lenh(l, CD) for l in bc.lenh_da_dong(KQ.so))) < 0.01)
kiem("cổng luôn đúng → `luon_khop`", g[G2["id"]]["luon_khop"],
     f"— {g[G2['id']]['khop']}/{g[G2['id']]['xet']}")
kiem("cổng bị xét mà không khớp lần nào → `luon_chan`", g[G1["id"]]["luon_chan"],
     f"— {g[G1['id']]['khop']}/{g[G1['id']]['xet']}")
kiem("khối sau cổng luôn chặn KHÔNG BAO GIỜ được đến",
     t[V1["id"]]["den"] == 0)

chac = {x["khoi"] for x in PB["chac_bo_duoc"]}
kiem("⭐ `chắc chắn bỏ được` GỒM khối chưa bao giờ đến", V1["id"] in chac)
kiem("⚠ và KHÔNG gồm cổng luôn khớp (nó vẫn nằm trên dòng chảy)",
     G2["id"] not in chac)
kiem("⚠ cũng KHÔNG gồm khối đang đẻ ra lệnh", V2["id"] not in chac)

# ================= 2. CẮT NHÁNH =================
print("\n▸ Cắt nhánh — thứ biến mất đúng bằng thứ chỉ tới được qua nó")
d2 = cat_tia.bo_nhanh(DOC, G1["id"])
con = {s["id"] for s in (d2 or {"entry": {"steps": []}})["entry"]["steps"]}
kiem("cắt cổng → cả khối dưới nó biến mất",
     d2 is not None and G1["id"] not in con and V1["id"] not in con)
kiem("nhánh KIA còn nguyên", d2 is not None and {G2["id"], V2["id"]} <= con)
kiem("bản đã cắt vẫn HỢP LỆ",
     d2 is not None
     and not [p for p in core.validate_process(d2) if p["severity"] == "error"])
kiem("cắt xong vẫn chạy được", d2 is not None
     and len(bc.chay(d2, NEN, CD, ghi_nhat_ky=False).so.lenh) > 0)

kiem("cắt khối KHÔNG CÓ trong sơ đồ → None",
     cat_tia.bo_nhanh(DOC, "khong-co-that") is None)
kiem("cắt khối BẮT ĐẦU → None (không có nó thì chẳng còn gì)",
     cat_tia.bo_nhanh(DOC, BD["id"]) is None)
# ⭐ BẤT BIẾN của `bo_nhanh`: cắt BẤT KỲ khối nào cũng chỉ ra một trong hai thứ —
# `None`, hoặc một sơ đồ SOÁT TĨNH SẠCH. Không bao giờ có đường thứ ba.
#
# Đây là phép kiểm đáng giá hơn hẳn một ca lẻ, vì nó quét cả sơ đồ. Và nó ghi lại hai
# sự thật đã đoán SAI lúc viết bài này: §17 KHÔNG coi cổng cụt đuôi là lỗi, và một sơ
# đồ chỉ còn mỗi khối Bắt đầu vẫn hợp lệ. Cắt hết sạch nhánh vẫn ra thứ chạy được.
_meo = []
for _st in DOC["entry"]["steps"]:
    _d = cat_tia.bo_nhanh(DOC, _st["id"])
    if _d is not None and [p for p in core.validate_process(_d)
                           if p["severity"] == "error"]:
        _meo.append(_st.get("name"))
kiem("⚠ cắt BẤT KỲ khối nào cũng chỉ ra None hoặc sơ đồ SẠCH — không có đường thứ ba",
     not _meo, f"— méo ở {_meo}" if _meo else f"— thử {len(DOC['entry']['steps'])} khối")

# ================= 3. LUẬT ĐA SỐ =================
print("\n▸ Luật ĐA SỐ cửa sổ — thứ chặn 'đẹp một quý, sai cả năm'")
import datetime  # noqa: E402

MOC = (datetime.date(2023, 11, 14), datetime.date(2024, 5, 14))   # 6 tháng


def gia_lap(cua_so):
    """`cham_lo` giả — ép điểm từng cửa sổ để thử ĐÚNG cái luật, không phụ thuộc may rủi."""
    return lambda docs: [{"loai": "cham", "cua_so": list(cua_so)} for _ in docs]


_base = [w["diem"] for w in cham_diem.cham_cuon(KQ, *MOC, "thang")]
kiem("dựng được nhiều cửa sổ để thử", len(_base) >= 5, f"— {len(_base)} cửa sổ")

# Ứng viên "tốt hơn" ở ĐA SỐ cửa sổ → phải GIỮ nhát cắt.
_hon = [x + 1.0 for x in _base]
d3, bb3 = cat_tia.mo_sach(DOC, NEN, CD, MOC, buoc="thang", tran_nhat=1,
                          cham_lo=gia_lap(_hon))
kiem("tốt hơn ở MỌI cửa sổ → giữ nhát cắt",
     any(b["giu"] for b in bb3) and d3 is not DOC)

# Tốt hơn ở ĐÚNG MỘT cửa sổ, tệ hơn ở phần còn lại → phải BỎ QUA.
_mot = [x - 1.0 for x in _base]
_mot[0] = _base[0] + 5.0
d4, bb4 = cat_tia.mo_sach(DOC, NEN, CD, MOC, buoc="thang", tran_nhat=1,
                          cham_lo=gia_lap(_mot))
kiem("⭐ tốt hơn ở 1/6 cửa sổ (dù hơn RẤT nhiều) → BỎ QUA nhát cắt",
     bb4 and not any(b["giu"] for b in bb4) and d4 is DOC,
     f"— {bb4[0]['tot_hon']}/{bb4[0]['so_cua_so']}" if bb4 else "")
kiem("mọi nhát cắt đã thử đều vào BIÊN BẢN, kể cả cái bị bỏ", len(bb4) >= 1,
     f"— {len(bb4)} dòng")

# ================= 4. CỬA ĐỀU =================
print("\n▸ Cửa ĐỀU QUA THỜI GIAN")
_d = cham_diem.cham(KQ)
kiem("`cham` luôn tính số cửa sổ dương, kể cả khi không lọc",
     "cua_so_duong" in _d and _d["so_cua_so"] > 0,
     f"— dương {_d['cua_so_duong']}/{_d['so_cua_so']}")
kiem("không đặt cửa thì KHÔNG lọc theo nó",
     cham_diem.cham(KQ, {"deu_toi_thieu": None})["dat"] == _d["dat"])
_chat = cham_diem.cham(KQ, {"deu_toi_thieu": 1.01})
kiem("đặt ngưỡng không đạt nổi → rớt, kèm LÝ DO đọc được",
     not _chat["dat"] and "dương" in (_chat["ly_do"] or ""),
     f"— {_chat['ly_do']}")
kiem("ngưỡng 0 thì mọi sơ đồ đều qua cửa ấy",
     cham_diem.cham(KQ, {"deu_toi_thieu": 0.0})["dat"] == _d["dat"])

print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
