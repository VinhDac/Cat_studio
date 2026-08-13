"""Đánh số phân cấp, ghim số, và ba trường hợp "gặp lại khối đã có nhãn".

ĐÁNH SỐ: SỐ = đi được bao xa, CHỮ = đi nhánh nào.

    1
    2
    3
    4
    ├── 4A            <- cổng nhánh A
    │   ├── 4A.1
    │   ├── 4A.2
    │   │   ├── 4A.2A
    │   │   └── 4A.2B
    │   └── 4A.3
    └── 4B
        ├── 4B.1
        └── 4B.2
    5                 <- điểm gộp: mọi nhánh đều dẫn tới đây nên số về lại mức trên
    6

Bài này canh đúng ba chỗ Auto_Clicker làm sai (core.md §3.3):
  Bẫy 1 — cờ "có vòng lặp" bật cả khi đồ thị KHÔNG có vòng
  Bẫy 2 — vòng lặp nuốt mất khối bắt đầu -> mọi huy hiệu biến thành "–"
  Bẫy 3 — thông báo lỗi đánh số theo index danh sách chứ không theo huy hiệu

Không mở cửa sổ, không nối MT5 -> chạy được ở bất cứ đâu.
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Console Windows mặc định cp1252, và khi stdout là PIPE thì Python cũng lấy bảng mã
# đó — in một dấu ✔ là chết ngay, bài test "hỏng" mà không có lấy một dòng lý do.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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


# ---------------- tiện ích dựng sơ đồ ----------------
def cong(nguong, x, y, ten=None):
    """Khối HĐ lẻ "Kiểm tra điều kiện" — đây chính là cái cổng của một nhánh."""
    s = core.make_action_step({
        "type": core.CHECK_COND,
        "name": ten or f"ĐK {nguong}",
        "conditions": [{"trai": {"ten": "atr", "tf": "M5", "period": 14}, "don_vi": "bps",
                        "phep": "<", "phai": {"value": nguong}}],
    })
    s["pos"] = [x, y]
    return s


def viec(ten, x, y):
    """Một khối KHÔNG phải cổng — dùng làm mắt xích thường trên chuỗi."""
    s = core.make_action_step({
        "type": core.SUA_LENH, "che_do": "hoa_von", "muc_tieu": "vi_the",
        "khoang": {"tinh": "R", "value": 1}, "name": ten})
    s["pos"] = [x, y]
    return s


def noi_day(b, cap):
    return [{"from": b[x]["id"], "to": b[y]["id"]} for x, y in cap]


def nhan_cua(b, cap):
    """{tên biến: nhãn} — để so với sơ đồ mong đợi bằng mắt thường."""
    kq = core.flow_order(list(b.values()), noi_day(b, cap))
    nguoc = {v["id"]: k for k, v in b.items()}
    return {nguoc[s]: n for s, n in kq["order"].items()}, kq


def loi(steps, edges, sev=None):
    ds = core.validate_flow_graph(steps, edges)
    return [p for p in ds if sev is None or p["severity"] == sev]


def loi_hd_tab(a, tab):
    ra = []
    core.validate_actions([a], lambda m, i=None: ra.append(m), tab)
    return ra


# ================= 1. Đánh số phân cấp =================
print("\n▸ Đánh số phân cấp")
b = {t: viec(t, 0, 0) for t in ("1", "2", "3", "4", "5", "6")}
b["4A"] = cong(7, 300, 0)
b["4B"] = cong(8, 300, 400)
b["4A.1"] = viec("a1", 600, 0)
b["4A.2"] = viec("a2", 900, 0)
b["4A.2A"] = cong(9, 1200, -50)
b["4A.2B"] = cong(10, 1200, 150)
b["4A.3"] = viec("a3", 1500, 0)
b["4B.1"] = viec("b1", 600, 400)
b["4B.2"] = viec("b2", 900, 400)
CAP = [("1", "2"), ("2", "3"), ("3", "4"),
       ("4", "4A"), ("4", "4B"),
       ("4A", "4A.1"), ("4A.1", "4A.2"),
       ("4A.2", "4A.2A"), ("4A.2", "4A.2B"),
       ("4A.2A", "4A.3"), ("4A.2B", "4A.3"),
       ("4A.3", "5"), ("4B", "4B.1"), ("4B.1", "4B.2"), ("4B.2", "5"),
       ("5", "6")]
nhan, kq = nhan_cua(b, CAP)
lech = [f"{k}→{v}" for k, v in nhan.items() if k != v]
kiem("mọi khối mang đúng nhãn trong sơ đồ", not lech, f"— lệch: {lech or 'không'}")
kiem("điểm gộp kéo số về lại mức trên cùng", nhan.get("5") == "5" and nhan.get("6") == "6")
kiem("không khối nào bị bỏ sót", not kq["unreachable"])
kiem("không báo nhầm là có vòng lặp", kq["loop"] is False)

# nhánh không gộp lại -> đơn giản là không có số ở mức trên nữa
b2 = {"1": viec("1", 0, 200), "A": cong(7, 300, 0), "B": cong(8, 300, 400),
      "A1": viec("a", 600, 0), "B1": viec("b", 600, 400)}
CAP2 = [("1", "A"), ("1", "B"), ("A", "A1"), ("B", "B1")]
n2, _ = nhan_cua(b2, CAP2)
kiem("nhánh không gộp → mỗi nhánh tự kết thúc, không có số mức trên",
     n2 == {"1": "1", "A": "1A", "B": "1B", "A1": "1A.1", "B1": "1B.1"}, f"— {n2}")

# không có edges -> chuỗi thẳng như từ trước tới nay
bs = [viec("x", 0, 0), viec("y", 0, 0), viec("z", 0, 0)]
cu = core.flow_order(bs, core.default_edges(bs))
kiem("không rẽ nhánh thì vẫn là 1, 2, 3",
     sorted(cu["order"].values()) == ["1", "2", "3"], f"— {sorted(cu['order'].values())}")

# ================= 2. Ưu tiên nhánh lấy từ VỊ TRÍ =================
print("\n▸ Thứ tự ưu tiên nhánh")
n3, _ = nhan_cua(b2, CAP2)
kiem("cổng nằm TRÊN là nhánh A", n3["A"] == "1A" and n3["B"] == "1B")
b2["B"]["pos"] = [300, -300]                      # kéo cổng B lên trên cổng A
n4, _ = nhan_cua(b2, CAP2)
kiem("kéo cổng lên trên thì nhãn đổi ngay → ưu tiên không bao giờ là thứ ngầm",
     n4["B"] == "1A" and n4["A"] == "1B", f"— B={n4['B']}, A={n4['A']}")
b2["B"]["pos"] = [300, 400]

# ================= 3. Khối Bắt đầu =================
print("\n▸ Khối Bắt đầu")
bd = core.make_start_step()
bd["pos"] = [0, 200]
b3 = {"BD": bd, "A": cong(7, 300, 0), "B": cong(8, 300, 400),
      "A1": viec("a", 600, 0), "B1": viec("b", 600, 400)}
CAP3 = [("BD", "A"), ("BD", "B"), ("A", "A1"), ("B", "B1")]
n5, kq5 = nhan_cua(b3, CAP3)
kiem("khối Bắt đầu mang số 1, các nhánh là 1A/1B",
     n5 == {"BD": "1", "A": "1A", "B": "1B", "A1": "1A.1", "B1": "1B.1"}, f"— {n5}")

# Bẫy 2: vòng lặp nuốt mất điểm bắt đầu.
b4 = {"1": viec("1", 0, 0), "2": viec("2", 300, 0), "3": viec("3", 600, 0)}
kq6 = core.flow_order(list(b4.values()), noi_day(b4, [("1", "2"), ("2", "3"), ("3", "1")]))
kiem("KHÔNG có khối Bắt đầu + vòng khép kín → mất hết nhãn (đúng bệnh của bản cũ)",
     kq6["entry"] is None and not kq6["order"])

b5 = {"BD": core.make_start_step(), "1": viec("1", 300, 0),
      "2": viec("2", 600, 0), "3": viec("3", 900, 0)}
b5["BD"]["pos"] = [0, 0]
b5["1"]["ghim"] = True
n7, kq7 = nhan_cua(b5, [("BD", "1"), ("1", "2"), ("2", "3"), ("3", "1")])
kiem("CÓ khối Bắt đầu → vòng khép kín vẫn giữ đủ nhãn",
     n7 == {"BD": "1", "1": "2", "2": "3", "3": "4"}, f"— {n7}")

# khối Bắt đầu không được nhận đường vào
b6 = {"BD": core.make_start_step(), "1": viec("1", 300, 0)}
b6["BD"]["pos"] = [0, 0]
ds = loi(list(b6.values()), noi_day(b6, [("BD", "1"), ("1", "BD")]), "error")
kiem("nối ngược vào khối Bắt đầu → báo LỖI",
     any("Bắt đầu" in p["message"] and "ĐI VÀO" in p["message"] for p in ds),
     f"— {[p['message'][:60] for p in ds]}")

# ================= 4. GHIM SỐ =================
print("\n▸ Ghim số ⟲")
b7 = {"BD": core.make_start_step(), "1": viec("một", 300, 0),
      "2": viec("hai", 600, 0), "3": viec("ba", 900, 0)}
b7["BD"]["pos"] = [0, 0]
CAP7 = [("BD", "1"), ("1", "2"), ("2", "3"), ("3", "1")]

# chưa ghim -> cảnh báo, nhưng nhãn vẫn còn đủ
n8, kq8 = nhan_cua(b7, CAP7)
kiem("chưa ghim: nhãn vẫn đủ, nhưng ghi nhận là vòng CHƯA GHIM",
     n8 == {"BD": "1", "1": "2", "2": "3", "3": "4"} and len(kq8["vong_ho"]) == 1
     and not kq8["quay_lai"], f"— {n8}, vong_ho={len(kq8['vong_ho'])}")
w = loi(list(b7.values()), noi_day(b7, CAP7), "warning")
kiem("chưa ghim → cảnh báo có gợi ý bấm chuột phải → Ghim số",
     any("Ghim số" in p["message"] for p in w),
     f"— {[p['message'][:70] for p in w]}")

# ghim rồi -> hết cảnh báo, số cũ vẫn nguyên
b7["1"]["ghim"] = True
n9, kq9 = nhan_cua(b7, CAP7)
kiem("ghim rồi: SỐ CŨ VẪN HỢP LỆ, không đổi tí nào",
     n9 == n8, f"— {n9}")
kiem("ghim rồi: cạnh quay lại được ghi nhận, không còn là vòng hở",
     len(kq9["quay_lai"]) == 1 and not kq9["vong_ho"],
     f"— quay_lai={kq9['quay_lai']}, vong_ho={kq9['vong_ho']}")
w2 = loi(list(b7.values()), noi_day(b7, CAP7), "warning")
kiem("ghim rồi → KHÔNG còn cảnh báo vòng lặp nào",
     not any("VÒNG LẶP" in p["message"] or "Ghim số" in p["message"] for p in w2),
     f"— {[p['message'][:60] for p in w2]}")

# quay lại từ trong một nhánh
b8 = {"BD": core.make_start_step(), "M": viec("mua", 300, 200),
      "A": cong(7, 600, 0), "B": cong(8, 600, 400), "A1": viec("a", 900, 0)}
b8["BD"]["pos"] = [0, 200]
b8["M"]["ghim"] = True
CAP8 = [("BD", "M"), ("M", "A"), ("M", "B"), ("A", "A1"), ("B", "M")]
n10, kq10 = nhan_cua(b8, CAP8)
kiem("nhánh B quay về khối đã ghim → giữ nguyên số, không cảnh báo",
     n10.get("M") == "2" and not kq10["vong_ho"] and len(kq10["quay_lai"]) == 1,
     f"— {n10}")

# ================= 5. Bẫy 1 — dương tính giả =================
print("\n▸ Bẫy 1: nhánh chụm không đều KHÔNG phải vòng lặp")
# 1 rẽ 3 nhánh A,B,C; A và B cùng về M; C đi đường riêng.
# `diem_gop` cần khối chung cho CẢ BA nhánh -> không có -> B đụng M do A đánh nhãn.
# Auto_Clicker báo "VÒNG LẶP" ở đây. Đồ thị này KHÔNG có vòng nào.
b9 = {"1": viec("1", 0, 200), "A": cong(7, 300, 0), "B": cong(8, 300, 200),
      "C": viec("c", 300, 400), "M": viec("m", 600, 100), "Z": viec("z", 600, 400)}
CAP9 = [("1", "A"), ("1", "B"), ("1", "C"), ("A", "M"), ("B", "M"), ("C", "Z")]
n11, kq11 = nhan_cua(b9, CAP9)
kiem("DAG không vòng → loop phải là False (bản cũ trả True)",
     kq11["loop"] is False, f"— loop={kq11['loop']}")
kiem("nhận diện đúng là 'nhánh chụm không đều'",
     len(kq11["lech_nhanh"]) == 1 and not kq11["vong_ho"],
     f"— lech_nhanh={len(kq11['lech_nhanh'])}, vong_ho={len(kq11['vong_ho'])}")
# Chỉ xét cảnh báo GẮN VỚI MỘT KHỐI. Cảnh báo "chưa có khối Bắt đầu" (step=None)
# có nhắc chữ "vòng lặp" trong câu khuyên — đó là lời khuyên, không phải chẩn đoán sai.
w3 = [p for p in loi(list(b9.values()), noi_day(b9, CAP9), "warning") if p["step"]]
kiem("không cảnh báo nào GẮN VỚI KHỐI gọi đây là vòng lặp",
     not any("vòng lặp" in p["message"].lower() for p in w3),
     f"— {[p['message'][:70] for p in w3]}")

# ================= 6. Bẫy 3 — thông báo dùng nhãn =================
print("\n▸ Bẫy 3: thông báo lỗi dùng NHÃN, không dùng index")
b10 = {"BD": core.make_start_step(), "1": viec("1", 300, 0),
       "A": cong(7, 600, 0), "B": viec("mặc định", 600, 200),
       "C": viec("thừa", 600, 400)}
b10["BD"]["pos"] = [0, 200]
CAP10 = [("BD", "1"), ("1", "A"), ("1", "B"), ("1", "C")]
e10 = loi(list(b10.values()), noi_day(b10, CAP10), "error")
kiem("hai nhánh không cổng → báo lỗi",
     any("không có cổng" in p["message"] for p in e10),
     f"— {[p['message'][:60] for p in e10]}")
kiem("thông báo có nhãn dạng [2] / [2A] chứ không phải \"Bước 3\"",
     any("[2]" in p["message"] for p in e10) and
     not any("Bước " in p["message"] for p in e10),
     f"— {[p['message'][:80] for p in e10]}")

# ================= 7. Luật rẽ nhánh =================
print("\n▸ Luật rẽ nhánh")
b11 = {"1": viec("1", 0, 200), "A": cong(7, 300, 0), "MD": viec("mặc định", 300, 400)}
kiem("nhánh mặc định xếp DƯỚI CÙNG → không lỗi",
     not loi(list(b11.values()), noi_day(b11, [("1", "A"), ("1", "MD")]), "error"))
b11["MD"]["pos"] = [300, -300]        # kéo nhánh mặc định lên trên
kiem("nhánh mặc định xếp TRÊN → báo lỗi",
     any("dưới cùng" in p["message"]
         for p in loi(list(b11.values()), noi_day(b11, [("1", "A"), ("1", "MD")]), "error")))

b12 = {"1": viec("1", 0, 200), "A": cong(7, 300, 0), "A2": cong(7, 300, 400)}
kiem("hai cổng TRÙNG điều kiện → cảnh báo",
     any("giống hệt" in p["message"]
         for p in loi(list(b12.values()), noi_day(b12, [("1", "A"), ("1", "A2")]), "warning")))

b13 = {"1": viec("1", 0, 0)}
kiem("đường nối trỏ về CHÍNH NÓ → lỗi",
     any("CHÍNH NÓ" in p["message"]
         for p in loi(list(b13.values()), noi_day(b13, [("1", "1")]), "error")))

# ---- NGÃ RẼ VÀ: đầu nhánh quyết định nghĩa (core.md §5.1) ---------------------
# Toàn câu hỏi → HOẶC (chọn một). Toàn hành động → VÀ (làm hết): hai mệnh lệnh cạnh
# nhau thì không có gì để chọn, nên "chọn một" vốn đã là cách đọc vô nghĩa.
print("\n▸ Ngã rẽ VÀ — đầu nhánh quyết định nghĩa")

_g, _h = cong(7, 300, 0), viec("hành động", 300, 100)
kiem("hai HÀNH ĐỘNG → ngã rẽ VÀ", core.la_nga_re_va([_h, viec("hđ 2", 300, 200)]))
kiem("hai CÂU HỎI → không phải VÀ", not core.la_nga_re_va([_g, cong(9, 300, 200)]))
kiem("TRỘN hỏi + làm → không phải VÀ", not core.la_nga_re_va([_g, _h]))
kiem("một nhánh thôi → không phải ngã rẽ", not core.la_nga_re_va([_h]))
_ghim = viec("đã ghim", 300, 200)
_ghim["ghim"] = True
kiem("có CẠNH QUAY LẠI → không phải VÀ (cạnh quay lại vốn mang vai phương án thay thế)",
     not core.la_nga_re_va([_h, _ghim]))

b14 = {"1": cong(7, 0, 100), "A": viec("Mua", 300, 0), "B": viec("Bán", 300, 200)}
kiem("rẽ 2 nhánh TOÀN hành động → KHÔNG lỗi (là ngã rẽ VÀ)",
     not loi(list(b14.values()), noi_day(b14, [("1", "A"), ("1", "B")]), "error"))

b15 = {"1": cong(7, 0, 100), "G": cong(9, 300, 0),
       "A": viec("Mua", 300, 200), "B": viec("Bán", 300, 400)}
kiem("TRỘN câu hỏi với ≥2 hành động → vẫn LỖI (không đọc ra CHỌN hay LÀM HẾT)",
     any("TRỘN" in p["message"] for p in
         loi(list(b15.values()), noi_day(b15, [("1", "G"), ("1", "A"), ("1", "B")]),
             "error")))

b16 = {"1": cong(7, 0, 100), "G": cong(9, 300, 0), "MD": viec("mặc định", 300, 200)}
kiem("câu hỏi + ĐÚNG MỘT hành động xếp cuối → vẫn là nhánh mặc định, không lỗi",
     not loi(list(b16.values()), noi_day(b16, [("1", "G"), ("1", "MD")]), "error"))

# ---- HAI khối Vào lệnh nối tiếp: hỏi về LỆNH, không hỏi về hình vẽ -------------
#
# Luật cũ chặn MỌI cặp Vào lệnh nối tiếp nhau, và nó khoá chết straddle nén — Buy Stop
# trên đỉnh zone + Sell Stop dưới đáy zone, hai lệnh CÙNG TỒN TẠI ĐƯỢC trong sổ. Luật
# mới chỉ chặn khi hai khối ra ĐÚNG MỘT LỆNH GIỐNG HỆT.
print("\n▸ Hai khối Vào lệnh trên cùng một đường")


def vao(x, y, **kw):
    """Khối "Vào lệnh". Mặc định là chân MUA của straddle."""
    a = {"type": core.VAO_LENH, "huong": "mua", "loai": "stop", "lot": 0.01,
         "entry": {"moc": "zone_HH"}, "dem": {"tinh": "atr", "value": 0.1},
         "sl": {"tinh": "atr_zone", "value": 1.5}, "tp": {"tinh": "R", "value": 2}}
    a.update(kw)
    s = core.make_action_step(a)
    s["pos"] = [x, y]
    return s


def noi_tiep(a, b_):
    d = {"A": a, "B": b_}
    return loi(list(d.values()), noi_day(d, [("A", "B")]), "error")


_trung = lambda ds: any("GIỐNG HỆT" in p["message"] for p in ds)

kiem("straddle: Buy đỉnh zone → Sell đáy zone → KHÔNG lỗi (cùng tồn tại được)",
     not _trung(noi_tiep(vao(0, 0),
                         vao(0, 200, huong="ban", entry={"moc": "zone_LL"}))))
kiem("hai khối Y HỆT nối tiếp → LỖI (một lệnh viết hai lần)",
     _trung(noi_tiep(vao(0, 0), vao(0, 200))))
kiem("cùng entry, khác TP → KHÔNG lỗi (chốt lời hai mức, sổ giữ cả hai)",
     not _trung(noi_tiep(vao(0, 0), vao(0, 200, tp={"tinh": "R", "value": 4}))))
kiem("cùng hướng+mốc, khác ĐỆM → KHÔNG lỗi (rải thang, hai giá khác nhau)",
     not _trung(noi_tiep(vao(0, 0), vao(0, 200, dem={"tinh": "atr", "value": 0.5}))))
kiem("cùng mọi thứ, khác LOT → KHÔNG lỗi (hai ticket, sàn giữ cả hai)",
     not _trung(noi_tiep(vao(0, 0), vao(0, 200, lot=0.02))))
# `name` và `pos` KHÔNG được nằm trong khoá: đổi tên khối hay kéo nó đi chỗ khác không
# đẻ ra một cái lệnh khác. Đây là khoá về LỆNH, không phải về khối.
kiem("khác mỗi TÊN khối → VẪN LỖI (tên không phải một phần của lệnh)",
     _trung(noi_tiep(vao(0, 0, name="Buy A"), vao(0, 200, name="Buy B"))))
kiem("khoá so sánh KHÔNG chứa name/pos/id",
     not ({"name", "pos", "id"} & set(core._KHOA_MOT_LENH)),
     f"— {core._KHOA_MOT_LENH}")

# ================= 8. Chuẩn hoá giữ cờ ghim =================
print("\n▸ Chuẩn hoá & nhân bản")
st = viec("x", 10, 20)
st["ghim"] = True
kiem("normalize_step giữ cờ ghim", core.normalize_step(st).get("ghim") is True)
kiem("normalize_step giữ pos", core.normalize_step(st).get("pos") == [10.0, 20.0])
moi, tra = core.clone_steps([st])
kiem("nhân bản KHÔNG chép cờ ghim (hai điểm quay lại là gần như chắc chắn sai ý)",
     "ghim" not in moi[0] and moi[0]["id"] != st["id"])
kiem("nhân bản trả bảng tra cũ→mới", tra.get(st["id"]) == moi[0]["id"])

d = core.new_process()
kiem("chiến lược mới có HAI sơ đồ, mỗi cái một khối Bắt đầu",
     set(core.TABS) <= set(d)
     and all(len(d[t]["steps"]) == 1 and core.is_start_step(d[t]["steps"][0])
             for t in core.TABS))

# ================= 8b. Chỉ còn HAI loại khối =================
print("\n▸ Bộ từ vựng khối")
kiem("chỉ còn 2 loại khối: Bắt đầu + Khối",
     set(core.KIND_LABELS) == {core.KIND_START, core.KIND_ACTION},
     f"— {sorted(core.KIND_LABELS)}")
kiem("lõi không còn biết Vòng theo dõi / Nhóm",
     not any(hasattr(core, t) for t in
             ("KIND_LOOP", "KIND_GROUP", "make_loop_step", "make_group_step",
              "has_actions", "is_loop_step", "is_group_step")))
kiem("khối kiểu cũ trong file cũ bị bỏ qua, không làm hỏng cả sơ đồ",
     core.normalize_step({"kind": "loop", "id": "sxxx", "actions": []}) is None)
kiem("template chỉ còn loại 'chiến lược', không lưu cụm khối rời",
     list(core.TEMPLATE_KINDS) == ["strategy"], f"— {list(core.TEMPLATE_KINDS)}")
kiem("đúng BA hành động, không còn Đặt cờ",
     core.ACTION_TYPES == [core.CHECK_COND, core.VAO_LENH, core.SUA_LENH],
     f"— {core.ACTION_TYPES}")

# ================= 8d. Entry chỉ TẠO, Manage chỉ SỬA =================
print("\n▸ Ranh giới Entry / Manage")
kiem("Vào lệnh chỉ ở Entry", core.ACTION_TABS[core.VAO_LENH] == (core.TAB_ENTRY,))
kiem("Sửa lệnh chỉ ở Manage", core.ACTION_TABS[core.SUA_LENH] == (core.TAB_MANAGE,))
kiem("Kiểm tra ĐK dùng ở cả hai",
     set(core.ACTION_TABS[core.CHECK_COND]) == set(core.TABS))
kiem("đặt lệnh trong Manage → báo lỗi",
     any("chỉ thuộc về" in m for m in loi_hd_tab(
         {"type": core.VAO_LENH, "huong": "mua", "loai": "market", "lot": 0.01,
          "sl": {"tinh": "atr_zone", "value": 1.5}}, core.TAB_MANAGE)))
kiem("sửa lệnh trong Entry → báo lỗi",
     any("chỉ thuộc về" in m for m in loi_hd_tab(
         {"type": core.SUA_LENH, "che_do": "hoa_von"}, core.TAB_ENTRY)))

_dk_lenh = {"type": core.CHECK_COND,
            "conditions": [{"trai": {"ten": "lenh_da_khop"}, "phep": "la_dung"}]}
kiem('hỏi "lệnh này" trong Entry → báo lỗi',
     any("Lệnh này" in m for m in loi_hd_tab(_dk_lenh, core.TAB_ENTRY)),
     f"— {loi_hd_tab(_dk_lenh, core.TAB_ENTRY)}")
kiem('hỏi "lệnh này" trong Manage → hợp lệ',
     not loi_hd_tab(_dk_lenh, core.TAB_MANAGE),
     f"— {loi_hd_tab(_dk_lenh, core.TAB_MANAGE)}")

# ================= 8c. Hai chữ ATR là hai thứ khác nhau =================
print("\n▸ Hợp đồng chuẩn hoá")
kiem("có RIÊNG cách tính theo ATR trung bình của vùng nén",
     "atr_zone" in core.DON_VI and "atr" in core.DON_VI)
kiem("hai cách tính ATR mô tả khác nhau, không lẫn được",
     core.DON_VI["atr"] != core.DON_VI["atr_zone"],
     f"— \"{core.DON_VI['atr']}\" vs \"{core.DON_VI['atr_zone']}\"")
kiem("không có cách tính nào theo pip / điểm / tiền",
     not any(t in " ".join(core.DON_VI.values()).lower()
             for t in ("pip", "point", "điểm", "đô")))

# ================= 8e. Phép so là KÝ HIỆU =================
print("\n▸ Phép so")
kiem("dùng ký hiệu, không dùng chữ",
     [core.PHEP_SO[k] for k in ("<", "<=", ">", ">=", "==", "!=")]
     == ["<", "≤", ">", "≥", "=", "≠"],
     f"— {[core.PHEP_SO[k] for k in ('<', '<=', '>', '>=', '==', '!=')]}")
kiem("không còn chữ 'lớn hơn' / 'nhỏ hơn' / 'bằng' nào",
     not any(t in " ".join(core.PHEP_SO.values()).lower()
             for t in ("lớn hơn", "nhỏ hơn", "bằng")))

# ================= 9. Mô tả hành động =================
print("\n▸ Mô tả hành động")
_cau = core.action_display({"type": core.CHECK_COND, "conditions": [
    # ĐƠN VỊ nằm TRONG lượng — cùng hình dạng `{value, tinh}` mà SL/TP dùng.
    {"trai": {"ten": "atr", "tf": "M5", "period": 14},
     "phep": "<", "phai": {"value": 7, "tinh": "bps"}}]})
kiem("Kiểm tra điều kiện đọc được thành câu, dùng ký hiệu",
     # ĐƠN VỊ đi liền con số bên phải — "7 bps của giá" đọc như một đại lượng.
     _cau == "ATR(M5, 14) < 7 bps của giá", f"— {_cau}")
kiem("toán hạng đúng/sai không ghép phép so",
     core.action_display({"type": core.CHECK_COND,
                          "conditions": [{"trai": {"ten": "lenh_da_khop"}, "phep": "la_dung"}]})
     == "Lệnh này đã khớp là ĐÚNG")
kiem("Sửa lệnh · hoà vốn KHÔNG còn tham số — mốc kích hoạt đã dời lên cổng",
     core.action_display({"type": core.SUA_LENH, "che_do": "hoa_von"})
     == "Dời SL về hoà vốn"
     and "khoang" not in core.normalize_action(
         {"type": core.SUA_LENH, "che_do": "hoa_von",
          "khoang": {"tinh": "R", "value": 1}}))
_vao = core.action_display({"type": core.VAO_LENH, "huong": "mua", "loai": "stop",
                            "lot": 0.01, "dem": {"tinh": "atr", "value": 0.1},
                            "sl": {"tinh": "atr_zone", "value": 1.5},
                            "tp": {"tinh": "R", "value": 2}})
kiem("Vào lệnh nói rõ đệm neo NGOÀI MÉP VÙNG", "ngoài mép vùng" in _vao, f"— {_vao}")
kiem("Vào lệnh phân biệt ATR hiện tại (đệm) với ATR vùng (rủi ro)",
     "đệm 0.1 × ATR" in _vao and "SL 1.5 × ATR zone" in _vao,
     f"— {_vao}")

# ================= 10. Soát hành động =================
print("\n▸ Soát hành động")


def loi_hd(a):
    ra = []
    core.validate_actions([a], lambda m, i=None: ra.append(m))
    return ra


kiem("Vào lệnh thiếu SL → báo lỗi",
     any("Stop Loss" in m for m in loi_hd(
         {"type": core.VAO_LENH, "huong": "mua", "loai": "market", "lot": 0.01})))
# ĐỆM là TUỲ CHỌN từ khi mốc neo hiện ra: neo mép zone mà đệm 0 là lệnh nằm ĐÚNG mép,
# hợp lệ. Chỉ neo vào GIÁ HIỆN TẠI mà không đệm mới sai — lệnh chờ đó khớp ngay.
kiem("lệnh chờ neo mép zone, KHÔNG đệm → hợp lệ",
     not any("đệm" in m for m in loi_hd(
         {"type": core.VAO_LENH, "huong": "mua", "loai": "stop", "lot": 0.01,
          "entry": {"moc": "zone_HH"},
          "sl": {"tinh": "atr_zone", "value": 1.5}})))
kiem("lệnh chờ neo GIÁ HIỆN TẠI mà thiếu đệm → báo lỗi",
     any("đệm" in m for m in loi_hd(
         {"type": core.VAO_LENH, "huong": "mua", "loai": "stop", "lot": 0.01,
          "entry": {"moc": "gia_hien_tai"},
          "sl": {"tinh": "atr_zone", "value": 1.5}})))
kiem("Vào lệnh thiếu MỐC NEO → báo lỗi",
     any("MỐC NEO" in m for m in loi_hd(
         {"type": core.VAO_LENH, "huong": "mua", "loai": "stop", "lot": 0.01,
          "dem": {"tinh": "atr", "value": 0.1},
          "sl": {"tinh": "atr_zone", "value": 1.5}})))
# `dong_mot_phan` và `trailing` ĐÃ BỎ — chưa từng chạy qua một bài kiểm nào, và
# `dong_mot_phan` còn ném thẳng "chưa được cài trong sổ lệnh" khi chạy tới. Sơ đồ cũ
# mang chúng thì `normalize_action` chuyển sang chế độ gần nhất.
kiem("chế độ cũ tự chuyển: đóng một phần → Kết thúc lệnh",
     core.normalize_action(
         {"type": core.SUA_LENH, "che_do": "dong_mot_phan"})["che_do"] == "ket_thuc")
kiem("chế độ cũ tự chuyển: đóng hẳn và huỷ chờ đều → Kết thúc lệnh",
     core.normalize_action({"type": core.SUA_LENH, "che_do": "dong_han"})["che_do"]
     == core.normalize_action({"type": core.SUA_LENH, "che_do": "huy_cho"})["che_do"]
     == "ket_thuc")
kiem("Kiểm tra điều kiện rỗng → báo (nó sẽ luôn khớp)",
     any("luôn khớp" in m for m in loi_hd(
         {"type": core.CHECK_COND, "conditions": []})))
# `shift` ĐÃ BỎ khỏi toán hạng giá — nó là ô số thứ ba trên hàng điều kiện, cùng hình
# dạng với ô "chu kỳ" của ATR nhưng khác nghĩa hẳn. Bài kiểm cũ canh "nến[0] hợp lệ, nến
# âm thì không"; giờ canh chuyện mạnh hơn: chuẩn hoá phải VỨT nó đi, không để nằm lại
# trong file như một con số vô chủ.
_dk_shift = core.normalize_action({"type": core.CHECK_COND, "conditions": [
    {"trai": {"ten": "close", "tf": "M5", "shift": 3}, "phep": ">",
     "phai": {"value": 1}}]})
kiem("`shift` bị vứt khỏi toán hạng giá, `tf` thì giữ",
     "shift" not in _dk_shift["conditions"][0]["trai"]
     and _dk_shift["conditions"][0]["trai"]["tf"] == "M5",
     f"— {_dk_shift['conditions'][0]['trai']}")
# Cùng luật, chiều ngược lại: trường của toán hạng KHÁC cũng không được bám lại.
_dk_rac = core.normalize_action({"type": core.CHECK_COND, "conditions": [
    {"trai": {"ten": "close", "tf": "M5", "period": 14, "method": "SMA"},
     "phep": ">", "phai": {"value": 1}}]})
kiem("đổi toán hạng thì `period`/`method` của cái cũ rơi đi",
     set(_dk_rac["conditions"][0]["trai"]) == {"ten", "tf"},
     f"— {_dk_rac['conditions'][0]['trai']}")

# ============ CƠ CHẾ SO SÁNH — một cờ cho CẢ KHỐI ============
#
# Trước đây mỗi DÒNG có một chip `số`/`đ.lượng`, nên hai dòng trong cùng một khối mang
# hai hình dạng: cột lệch, và mắt phải đọc lại hình dạng ở từng dòng. Cái chip ấy chỉ
# tồn tại vì một hàng phải gánh hai hình dạng — nâng lựa chọn lên mức KHỐI thì nó thừa.
#
# Là CƠ CHẾ chứ không phải LOẠI KHỐI: hai kiểu dùng chung bộ soát, chung phép chuẩn hoá,
# chung hàm dựng chữ trên thẻ — chỉ khác đúng cái vế phải.
print("\n▸ Cơ chế so sánh — một cờ cho cả khối")


def _dk(trai, phai, phep="<", co=None):
    a = {"type": core.CHECK_COND, "conditions": [
        {"trai": trai, "phep": phep, "phai": phai}]}
    if co is not None:
        a["so_dai_luong"] = co
    return core.normalize_action(a)


_atr = {"ten": "atr", "tf": "M5", "period": 14}
_ma = {"ten": "ma", "tf": "M5", "period": 50, "method": "SMA"}

# File CŨ không có cờ — suy từ chính các điều kiện, không đoán.
kiem("file cũ có vế phải là ĐẠI LƯỢNG → cờ tự bật",
     _dk({"ten": "close", "tf": "M5"}, _ma, ">")["so_dai_luong"] is True)
kiem("file cũ có vế phải là SỐ → không gắn cờ",
     "so_dai_luong" not in _dk(_atr, {"value": 7, "tinh": "bps"}))

# Cờ QUYẾT ĐỊNH hình dạng, không phải từng dòng tự khai.
_bat = _dk(_atr, {"value": 7, "tinh": "bps"}, co=True)
kiem("bật cờ: vế phải là SỐ cũng bị viết lại thành đại lượng",
     _bat["conditions"][0]["phai"] == {"ten": ""},
     f"— {_bat['conditions'][0]['phai']}")
_tat = _dk({"ten": "close", "tf": "M5"}, _ma, ">", co=False)
kiem("tắt cờ: vế phải là ĐẠI LƯỢNG cũng bị viết lại thành số",
     _tat["conditions"][0]["phai"] == {"value": 0.0}
     and "so_dai_luong" not in _tat,
     f"— {_tat['conditions'][0]['phai']}")
kiem("bật cờ: ĐƠN VỊ biến mất — hai vế cùng mẫu số thì nó triệt tiêu",
     "tinh" not in _bat["conditions"][0]["phai"])
kiem("bật cờ: phép đúng/sai rơi về `<`",
     _dk(_atr, _ma, "la_dung", co=True)["conditions"][0]["phep"] == "<")

# Toán hạng đúng/sai + cờ bật: NÓI RA, không sửa lén. Đổi hộ toán hạng là vứt mất thứ
# người dùng đã chọn, mà họ không hề biết.
_ds = _dk({"ten": "zone_da_sinh_lenh"}, _ma, "<", co=True)
kiem("bật cờ mà toán hạng ĐÚNG/SAI → báo lỗi, KHÔNG tự đổi toán hạng",
     any("ĐÚNG/SAI" in m and "không so được" in m for m in loi_hd(_ds))
     and _ds["conditions"][0]["trai"]["ten"] == "zone_da_sinh_lenh",
     f"— {[m[:50] for m in loi_hd(_ds)]}")

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
