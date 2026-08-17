"""SỐ GÕ TAY HAI CHỖ → cảnh báo + nút đặt tên.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
Bảng tham số từng là một BƯỚC SETUP: muốn dùng số 7 thì phải khai `nguong = 7` trước.
Vô nghĩa — gõ thẳng `7` vào ô vừa ngắn hơn vừa rõ hơn, và người dùng nhìn hai ảnh chụp
màn hình cạnh nhau thấy chúng y hệt.

Bảng tham số chỉ đáng tồn tại vì MỘT lý do: khi cùng một con số nằm ở HAI nơi, sửa một
chỗ quên chỗ kia thì chiến lược lệch ÂM THẦM — không lỗi, không báo, chỉ là kết quả
backtest khác đi mà không ai biết vì sao. Nên bảng tham số là BẢN GHI của những con số
đã đủ quan trọng để có tên, và chỗ duy nhất ép người dùng nghĩ tới nó là dòng cảnh báo.

Bài này canh bốn điều:
  1. số lặp ĐÚNG VAI → cảnh báo, kèm đủ dữ liệu để đặt tên bằng một nút.
  2. TRÙNG HỢP thì KHÔNG gom: `14` của ATR và `14` của MA không phải một khái niệm.
  3. đường dẫn `cho` chỉ ĐÚNG Ô — chứng minh bằng cách thay số bằng tên rồi chạy lại
     backtest: kết quả phải GIỐNG HỆT. Đây là phần quan trọng nhất của bài.
  4. sau khi đặt tên, cảnh báo biến mất và sơ đồ không sinh lỗi mới.

Chạy:  python tests\\test_dat_ten.py
"""
import io
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import kho  # noqa: E402


class _ZoneGia:
    """Zone giả tối thiểu — đủ cho `_khoang` tính `mép zone đối diện`."""
    dinh, day, atr_tb = 105.0, 95.0, 1.0


class _CtxGia:
    """Ngữ cảnh giả: `_khoang` chỉ cần `ct.so` và `so.zone_hien_hanh`."""
    class ct:
        so = staticmethod(float)

    class so:
        @staticmethod
        def zone_hien_hanh():
            return _ZoneGia()


_CTX_ZONE = _CtxGia()

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


#: Cùng bẫy với `test_zone`: mốc phải trùng biên nến M5, không thì `la_nhip5` toàn False
#: và sơ đồ Entry không chạy lượt nào.
T0 = 1700000100
CD = bc.CaiDat(symbol="X", spread_diem=0, point=0.01, digits=2,
               contract_size=1.0, deposit=10000.0)
YEN = [100.0] * 400
DONG = [100.0 + k * 3.0 for k in range(1, 60)]


def nen_m1(gia):
    a = np.zeros(len(gia), dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"),
                                  ("l", "f8"), ("c", "f8"), ("vol", "f8")])
    a["t"] = T0 + np.arange(len(gia)) * 60
    for k in "ohlc":
        a[k] = gia
    a["vol"] = 1.0
    return a


def dk_atr(nguong, chu_ky):
    # ⚠ Đơn vị `gia` (ATR thô), KHÔNG phải `atr_nen`. Hai lý do, cả hai đều làm bài kiểm
    # ra 0 zone nếu chọn sai:
    #   · `YEN` phẳng tuyệt đối → ATR = 0 ở mọi chu kỳ → `atr / atr_nen` = 0/0 = NaN;
    #   · 400 nến M1 = 80 nến M5, chưa đủ 100 nến cho ATR nền thôi NaN.
    # Thước tỉ số được kiểm riêng ở `test_zone.py` mục 7, với dữ liệu đủ dài và có
    # biến động thật.
    return [{"trai": {"ten": "atr", "tf": "M5", "period": chu_ky},
             "phep": "<", "phai": {"value": nguong, "tinh": "gia"}}]


def so_do():
    """Entry: [bắt đầu] → [cổng zone] → [cổng thứ hai] → [vào lệnh].

    Hai cổng CỐ Ý gõ cùng một cặp số (chu kỳ 14 · ngưỡng 50 × ATR nền) — đúng cái bẫy mà bài
    này canh. Cổng thứ hai không mang cờ `cong_zone`: chỉ được có MỘT cổng zone."""
    bd = core.make_start_step("bd", "M5")
    bd["pos"] = [0.0, 0.0]
    g1 = core.make_action_step({"id": "g1", "type": core.CHECK_COND, "name": "cổng zone",
                                "cong_zone": True, "conditions": dk_atr(50.0, 14)})
    g1["pos"] = [1.0, 0.0]
    g2 = core.make_action_step({"id": "g2", "type": core.CHECK_COND, "name": "cổng 2",
                                "conditions": dk_atr(50.0, 14)})
    g2["pos"] = [2.0, 0.0]
    v = core.make_action_step({
        "id": "v1", "type": core.VAO_LENH, "name": "mua", "huong": "mua",
        "loai": "stop", "rui_ro": 0.5, "entry": {"moc": "zone_HH"},
        "dem": {"tinh": "gia", "value": 1.0},
        "sl": {"tinh": "gia", "value": 1.0}})
    v["pos"] = [3.0, 0.0]

    qly = core.make_start_step("qly", "M1")
    qly["pos"] = [0.0, 0.0]
    #: Hai khối Sửa lệnh cùng mang khoảng 2.0 giá — lặp ở vai `khoang`, KHÁC vai với `sl`
    #: của khối Vào lệnh dù cùng đơn vị. Bài kiểm dưới canh đúng chỗ đó.
    #: ⚠ MỘT dời SL, MỘT dời TP — không phải hai lần dời SL. §17.3 cấm hai khối ghi lên
    #: CÙNG một thứ nối tiếp nhau mà không có cổng ở giữa (khối trên bị đè ngay, không để
    #: lại dấu vết). Bài này soi chuyện SỐ LẶP, không soi chuyện đó.
    s1 = core.make_action_step({"id": "s1", "type": core.SUA_LENH, "name": "dời SL",
                                "che_do": "doi_sl", "khoang": {"tinh": "gia", "value": 2.0}})
    s1["pos"] = [1.0, 0.0]
    s2 = core.make_action_step({"id": "s2", "type": core.SUA_LENH, "name": "dời TP",
                                "che_do": "doi_tp", "khoang": {"tinh": "gia", "value": 2.0}})
    s2["pos"] = [2.0, 0.0]
    #: `chu_ky_atr` engine LUÔN đòi phải có (zone cộng dồn ATR để ra `zone_atr_tb` = 1R),
    #: nên bảng tham số không bao giờ rỗng. Đây chính là ca đụng tên thật: người dùng gõ
    #: tay `14` hai chỗ trong khi dòng `chu_ky_atr = 14` vẫn nằm đó, không ai dùng.
    return core.normalize_process({
        "name": "thử đặt tên", "symbol": "X",
        "tham_so": [core.make_tham_so("chu_ky_atr", "Chu kỳ ATR", 14, "nến")],
        #: ⚠ `make_start_step("bd", …)` KHÔNG lấy "bd" làm id — nó tự sinh một id. Nối
        #: dây bằng chuỗi "bd" thì cạnh đầu bị vứt lặng lẽ, sơ đồ vẫn hợp lệ, và
        #: backtest ra 0 zone / 0 lệnh. Luôn dùng `bd["id"]`.
        "entry": {"steps": [bd, g1, g2, v],
                  "edges": [{"from": bd["id"], "to": "g1", "port": "out"},
                            {"from": "g1", "to": "g2", "port": "out"},
                            {"from": "g2", "to": "v1", "port": "out"}]},
        "manage": {"steps": [qly, s1, s2],
                   "edges": [{"from": qly["id"], "to": "s1", "port": "out"},
                             {"from": "s1", "to": "s2", "port": "out"}]}})


def canh_bao_dat_ten(doc):
    return [p for p in core.validate_process(doc) if p.get("dat_ten")]


def loi(doc):
    return [p["message"] for p in core.validate_process(doc)
            if p["severity"] == "error"]


def dat_ten(doc, p):
    """Làm ĐÚNG việc mà nút "Đặt tên cho số này" làm ở giao diện: đi theo từng đường
    dẫn, thay số bằng tên, rồi thêm một dòng vào bảng tham số.

    Cố ý viết lại ở đây thay vì gọi hàm Python nào đó — vì phía làm thật là TypeScript.
    Bài kiểm này canh cái HỢP ĐỒNG (`cho` trỏ đúng ô nào), không canh cách hiện thực."""
    d = {k: v for k, v in doc.items()}
    dt = p["dat_ten"]
    ts = list(d.get("tham_so") or [])
    # Cùng luật đụng tên với giao diện: cùng giá trị thì DÙNG LẠI, khác thì thêm hậu tố.
    cu = next((t for t in ts if t["ten"] == dt["goi_y"]), None)
    ten, dung_lai = dt["goi_y"], bool(cu) and float(cu["gia_tri"]) == dt["gia_tri"]
    if cu and not dung_lai:
        dang_co = {t["ten"] for t in ts}
        i = 2
        while ten in dang_co:
            ten, i = f"{dt['goi_y']}_{i}", i + 1
    for c in dt["cho"]:
        st = next(s for s in d[c["tab"]]["steps"] if s.get("id") == c["step"])
        o = st
        for k in c["duong"][:-1]:
            o = o[k]
        o[c["duong"][-1]] = ten
    if not dung_lai:
        ts.append(core.make_tham_so(ten, dt["nhan"], dt["gia_tri"], dt["don_vi"]))
    d["tham_so"] = ts
    return d


def van_tay(doc):
    """Dấu vân tay của một lần chạy — đủ để bắt mọi sai lệch do đặt tên gây ra."""
    kq = bc.chay(doc, nen_m1(YEN + DONG), CD)
    return (len(kq.so.zone),
            tuple(round(z.rong, 9) for z in kq.so.zone),
            tuple((l.huong, l.loai, l.lot, round(l.gia_dat, 9),
                   round(l.sl or 0.0, 9), round(l.R or 0.0, 9),
                   l.trang_thai, l.nen_dat) for l in kq.so.lenh))


print("\n▸ 1. Số lặp ĐÚNG VAI thì cảnh báo, kèm đủ dữ liệu để đặt tên")
D = so_do()
cb = canh_bao_dat_ten(D)
theo_ten = {p["dat_ten"]["goi_y"]: p for p in cb}
kiem("bắt được chu kỳ 14 lặp", "chu_ky_atr" in theo_ten, f"— {sorted(theo_ten)}")
kiem("bắt được ngưỡng 50 lặp", "nguong_atr_gia" in theo_ten)
kiem("bắt được khoảng 2.0 của Sửa lệnh lặp", "khoang_gia" in theo_ten)
kiem("mọi cảnh báo đều là warning, không chặn ▶ Chạy",
     all(p["severity"] == "warning" for p in cb))
kiem("không sinh lỗi nào", loi(D) == [], f"— {loi(D)}")
if "nguong_atr_gia" in theo_ten:
    dt = theo_ten["nguong_atr_gia"]["dat_ten"]
    kiem("ngưỡng: đúng 2 chỗ, đúng giá trị, đúng nhãn đơn vị",
         len(dt["cho"]) == 2 and dt["gia_tri"] == 50.0 and dt["don_vi"] == "gia",
         f"— {dt['gia_tri']} {dt['don_vi']} ở {len(dt['cho'])} chỗ")
    kiem("hai chỗ là hai KHỐI khác nhau",
         {c["step"] for c in dt["cho"]} == {"g1", "g2"},
         f"— {sorted(c['step'] for c in dt['cho'])}")

print("\n▸ 2. TRÙNG HỢP thì KHÔNG gom — trùng số không phải là quan hệ")
D2 = so_do()
#: Cổng 2 đổi sang MA chu kỳ 14: vẫn là số 14, nhưng là chu kỳ của một chỉ báo KHÁC.
#: Gộp chúng lại là đặt tên sai, và sau này đổi `chu_ky_atr` sẽ kéo theo cả MA.
D2["entry"]["steps"][2]["conditions"] = [
    {"trai": {"ten": "close", "tf": "M5", "shift": 1}, "phep": ">",
     "phai": {"ten": "ma", "tf": "M5", "period": 14, "method": "SMA", "shift": 1}}]
D2 = core.normalize_process(D2)
g2 = {p["dat_ten"]["goi_y"] for p in canh_bao_dat_ten(D2)}
kiem("chu kỳ 14 của ATR và của MA KHÔNG bị gom", "chu_ky_atr" not in g2, f"— {sorted(g2)}")
kiem("ngưỡng 50 cũng hết lặp theo", "nguong_atr_gia" not in g2)
kiem("nhưng khoảng 2.0 vẫn còn lặp", "khoang_gia" in g2)

#: `sl` 1.0 giá và `khoang` 2.0 giá cùng đơn vị nhưng khác VAI. Đổi khoảng thành 1.0 để
#: chúng bằng nhau — vẫn phải KHÔNG gom, vì "SL ban đầu" và "bước dời SL" là hai thứ.
D3 = so_do()
for s in D3["manage"]["steps"]:
    if s.get("khoang"):
        s["khoang"]["value"] = 1.0
g3 = {p["dat_ten"]["goi_y"] for p in canh_bao_dat_ten(D3)}
kiem("cùng số cùng đơn vị nhưng khác VAI thì không gom",
     "sl_gia" not in g3 and "khoang_gia" in g3, f"— {sorted(g3)}")

print("\n▸ 3. Đường dẫn `cho` trỏ ĐÚNG Ô — chứng minh bằng backtest")
goc = van_tay(D)
kiem("sơ đồ gốc có chạy ra lệnh (bài kiểm không rỗng)",
     len(goc[2]) > 0 and goc[0] > 0, f"— {goc[0]} zone, {len(goc[2])} lệnh")
sau = D
for p in sorted(canh_bao_dat_ten(D), key=lambda x: x["dat_ten"]["goi_y"]):
    sau = dat_ten(sau, p)
sau = core.normalize_process(sau)
kiem("đặt tên xong, backtest RA ĐÚNG KẾT QUẢ CŨ", van_tay(sau) == goc,
     "— vân tay khớp" if van_tay(sau) == goc else f"\n      cũ  {goc}\n      mới {van_tay(sau)}")
kiem("mọi số đã thành tên — không còn chỗ nào gõ tay lặp",
     canh_bao_dat_ten(sau) == [],
     f"— còn {[p['dat_ten']['goi_y'] for p in canh_bao_dat_ten(sau)]}")

print("\n▸ 4. Sau khi đặt tên, sơ đồ vẫn sạch")
kiem("không sinh lỗi mới", loi(sau) == [], f"— {loi(sau)}")
kiem("bảng tham số có đúng ba dòng — KHÔNG đẻ ra `chu_ky_atr_2`",
     {t["ten"] for t in sau["tham_so"]} == {"chu_ky_atr", "khoang_gia", "nguong_atr_gia"},
     f"— {sorted(t['ten'] for t in sau['tham_so'])}")
kiem("không dòng nào bị báo 'không khối nào dùng tới'",
     not [p for p in core.validate_process(sau) if "không khối nào dùng tới" in p["message"]])
#: Một con số dùng MỘT chỗ thì im lặng — cảnh báo mọi số là làm phiền, không phải giúp.
D4 = so_do()
D4["entry"]["steps"][2]["conditions"] = dk_atr(60.0, 21)
D4 = core.normalize_process(D4)
g4 = {p["dat_ten"]["goi_y"] for p in canh_bao_dat_ten(D4)}
kiem("số chỉ dùng một chỗ thì IM LẶNG",
     "chu_ky_atr" not in g4 and "nguong_atr_gia" not in g4, f"— {sorted(g4)}")

print("\n▸ 5. ĐƠN VỊ THUỘC VỀ CÁI Ô — ai điền vào cũng phải mang đúng đơn vị ấy")
#
# Trước đây cột `don_vi` của bảng tham số là CHỮ TỰ DO, chỉ để đọc — và nó âm thầm mục:
# sơ đồ mẫu mang `"× ATR vùng"`, một chuỗi không tồn tại ở đâu, rác từ lần đổi tên
# vùng→zone. Không ai bắt được vì chưa có gì đọc nó.
#
# Giờ nó là một KHOÁ, và nó quyết định tham số ấy được mời vào ô nào. Ba việc dựa vào
# đúng một hàm `don_vi_cua_o` và phải nhất trí: nút ▾ lọc · ô đơn vị khoá · soát tĩnh.
kiem("chu kỳ luôn đo bằng NẾN", core.don_vi_cua_o("chu_ky") == "nen")
kiem("rủi ro luôn đo bằng % VỐN — không phải % giá (§15.13)",
     core.don_vi_cua_o("rui_ro") == "pt_von")
# `lot` đã bỏ khỏi cả khối Vào lệnh lẫn bảng đơn vị: không ô nào nhận nó nữa, nên một
# tham số khai `lot` là con số không dùng được ở đâu cả.
kiem("`lot` biến khỏi bảng đơn vị — bày ra thứ không ô nào nhận là rác",
     "lot" not in core.NHAN_DON_VI and "lot" not in core.DON_VI_THAM_SO_CU)
kiem("khoảng cách lấy đơn vị ĐANG CHỌN",
     core.don_vi_cua_o("sl", tinh="atr_zone") == "atr_zone")
kiem("toán hạng đúng/sai KHÔNG có đơn vị",
     core.don_vi_cua_o("dieu_kien", "zone_da_sinh_lenh") is None)

#: ⚠ Chỗ này bài kiểm bắt được lỗi thật ngay lần chạy đầu: `zone_dem` và `so_vi_the`
#: cùng `loai = "dem"`, nên hồi đầu cả hai ra đơn vị "đếm" — tức nút ▾ sẽ mời
#: `so_vi_the_toi_da = 3 lệnh` vào ô "zone cần bao nhiêu nến". Hai con số chẳng liên
#: quan gì nhau. Sửa bằng cách để chính TOÁN HẠNG khai đơn vị của nó.
kiem("`zone_dem` đếm NẾN, `so_vi_the` đếm LỆNH — không gộp",
     core.don_vi_cua_o("dieu_kien", "zone_dem") == "nen"
     and core.don_vi_cua_o("dieu_kien", "so_vi_the") == "lenh",
     f"— {core.don_vi_cua_o('dieu_kien', 'zone_dem')} / "
     f"{core.don_vi_cua_o('dieu_kien', 'so_vi_the')}")
kiem("mọi toán hạng KHÔNG phải đúng/sai đều có đơn vị",
     all(core.don_vi_cua_o("dieu_kien", t["key"]) is not None
         for t in kho.TOAN_HANG if t.get("loai") != "dung_sai"),
     "— thiếu thì nút ▾ câm lặng mà không ai biết vì sao")

# File CŨ: đơn vị là chữ tự do. Mở lên phải tự lành.
D5 = so_do()
D5["tham_so"] = [core.make_tham_so("chu_ky_atr", "Chu kỳ ATR", 14, "nến")]
kiem("chữ cũ (`nến`) đổi thành khoá (`nen`)",
     core.normalize_process(D5)["tham_so"][0]["don_vi"] == "nen")
#: Suy từ CHỖ DÙNG chỉ chạy được khi tham số THẬT SỰ nằm trong một ô — nên bản này phải
#: cho hai cổng gọi `chu_ky_atr` bằng tên, chứ không gõ thẳng 14 như `so_do()` mặc định.
D5b = so_do()
D5b["tham_so"] = [core.make_tham_so("chu_ky_atr", "Chu kỳ ATR", 14, "linh tinh")]
for st in D5b["entry"]["steps"]:
    for c in st.get("conditions") or []:
        c["trai"]["period"] = "chu_ky_atr"
kiem("chữ LẠ thì không đoán bừa — suy từ CHỖ DÙNG ra `nen`",
     core.normalize_process(D5b)["tham_so"][0]["don_vi"] == "nen",
     "— `chu_ky_atr` đang nằm ở ô chu kỳ, mà ô chu kỳ luôn là nến")

# MỘT THAM SỐ, MỘT ĐƠN VỊ.
D6 = so_do()
D6["tham_so"] = [core.make_tham_so("chu_ky_atr", "", 14, "nen"),
                 core.make_tham_so("hai_mat", "", 4.0, "atr")]
D6["entry"]["steps"][1]["conditions"][0]["phai"] = {"value": "hai_mat", "tinh": "atr_nen"}
D6["entry"]["steps"][2]["conditions"][0]["phai"] = {"value": "hai_mat", "tinh": "atr"}
D6 = core.normalize_process(D6)
kiem("một tên đọc bằng HAI đơn vị → LỖI, không phải cảnh báo",
     any(p["severity"] == "error" and "hai_mat" in p["message"]
         and "đơn vị khác nhau" in p["message"] for p in core.validate_process(D6)),
     f"— {[p['message'][:60] for p in core.validate_process(D6) if 'hai_mat' in p['message']]}")

D7 = so_do()
D7["tham_so"] = [core.make_tham_so("chu_ky_atr", "", 14, "nen"),
                 core.make_tham_so("nguong", "", 50.0, "atr")]   # khai atr…
D7["entry"]["steps"][1]["conditions"][0]["phai"] = {"value": "nguong", "tinh": "atr_nen"}
D7["entry"]["steps"][2]["conditions"][0]["phai"] = {"value": "nguong", "tinh": "atr_nen"}
D7 = core.normalize_process(D7)
kiem("bảng khai một đằng, chỗ dùng một nẻo → cảnh báo",
     any(p["severity"] == "warning" and "nói khác chỗ dùng" in p["message"]
         for p in core.validate_process(D7)))

# `mép zone đối diện` — con số gõ vào KHÔNG được dùng.
kiem("`bien_zone` bỏ qua giá trị: 1 và 99 cho cùng một khoảng",
     bc._khoang({"tinh": "bien_zone", "value": 1.0}, _CTX_ZONE, neo=110.0)
     == bc._khoang({"tinh": "bien_zone", "value": 99.0}, _CTX_ZONE, neo=110.0),
     "— nên hộp thoại khoá ô số đó lại")

print(f"\n{'─' * 60}\n  {dung} đúng · {sai} sai\n{'─' * 60}")
sys.exit(1 if sai else 0)
