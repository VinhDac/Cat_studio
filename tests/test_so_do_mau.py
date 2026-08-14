"""Sơ đồ mẫu Compress (D_02) phải mở ra SẠCH và khớp đúng logic EA gốc.

Đây là bằng chứng bộ khối — Kiểm tra ĐK · Vào lệnh · Sửa lệnh, chia hai sơ đồ Entry và
Manage — đủ sức diễn tả một chiến lược THẬT. Mẫu hỏng thì đó là lỗi THIẾT KẾ bộ khối,
không phải lỗi của cái mẫu.

Bốn điều bài này canh, vì cả bốn đều dễ trượt về chỗ cũ:

  1. HAI SƠ ĐỒ, ranh giới rạch ròi — Entry chỉ TẠO lệnh, Manage chỉ SỬA lệnh, và
     toán hạng "Lệnh này" chỉ có nghĩa ở Manage.
  2. CẢ HAI đều là vòng lặp theo nến, nên KHÔNG có mũi tên ngược nào.
  3. HAI CHỮ ATR LÀ HAI THỨ KHÁC NHAU — đệm đo bằng ATR hiện tại, rủi ro đo bằng ATR
     trung bình cả vùng nén.
  4. Ba dòng guard của `ManageBreakEven` phải HIỆN THÀNH CỔNG, đặc biệt là
     "SL chưa ở hoà vốn" — thiếu nó thì lệnh sửa SL bắn lại mỗi nến.

Chạy:  python tests\\test_so_do_mau.py
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Console Windows mặc định cp1252, in tiếng Việt là vỡ ngay.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import api  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import kho  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


a = api.Api()

# ================= 1. bootstrap =================
print("\n▸ bootstrap")
b = a.bootstrap()
kiem("bootstrap trả về được", b["ok"])
bv = b["value"]
kiem("đúng BA hành động: Kiểm tra ĐK · Vào lệnh · Sửa lệnh",
     bv["action_types"] == ["check_cond", "vao_lenh", "sua_lenh"],
     f"— {bv['action_types']}")
kiem("hai sơ đồ: Entry + Manage", bv["tabs"] == ["entry", "manage"])
kiem("Entry chỉ TẠO, Manage chỉ SỬA",
     bv["action_tabs"]["vao_lenh"] == ["entry"]
     and bv["action_tabs"]["sua_lenh"] == ["manage"])
kiem("chỉ còn HAI loại khối", bv["kinds"] == ["start", "action"])
kiem("phép so dùng KÝ HIỆU",
     [bv["phep_so"][k] for k in ("<", "<=", ">", ">=")] == ["<", "≤", ">", "≥"],
     f"— {[bv['phep_so'][k] for k in ('<', '<=', '>', '>=')]}")
print(f"    {len(bv['toan_hang'])} toán hạng / "
      f"{len(set(t['nhom'] for t in bv['toan_hang']))} nhóm, "
      f"{len(bv['don_vi'])} cách tính khoảng cách")

# ================= 2. sơ đồ mẫu =================
print("\n▸ Sơ đồ mẫu Compress")
d = a.demo_process()
kiem("mở được", d["ok"], "" if d["ok"] else f"— {d.get('error')}")
doc = d["value"]
v = a.validate(doc)

kiem("SẠCH hoàn toàn, cả hai tab — không lỗi, không cảnh báo",
     not v["value"], f"— {[(p['tab'], p['message'][:70]) for p in v['value']]}")

theo, nhan = {}, {}
for tab in core.TABS:
    g = doc[tab]
    theo[tab] = {s["id"]: s for s in g["steps"]}
    L = v["luong"][tab]
    nhan[tab] = {core.step_title(theo[tab][sid]): n for sid, n in L["order"].items()}
    kiem(f"[{core.TAB_LABELS[tab]}] mọi khối có nhãn, không khối nào lạc",
         len(L["order"]) == len(g["steps"]) and not L["unreachable"],
         f"— {len(L['order'])}/{len(g['steps'])}")
    kiem(f"[{core.TAB_LABELS[tab]}] KHÔNG mũi tên ngược — vốn đã là vòng lặp theo nến",
         not L["quay_lai"] and not L["vong_ho"] and not L["lech_nhanh"])
    kiem(f"[{core.TAB_LABELS[tab]}] có đúng một khối Bắt đầu",
         sum(1 for s in g["steps"] if core.is_start_step(s)) == 1)

print("\n  ── Nhãn trên sơ đồ ──")
for tab in core.TABS:
    print(f"    {core.TAB_LABELS[tab]}  ({len(doc[tab]['steps'])} khối)")
    for sid, n in sorted(v["luong"][tab]["order"].items(),
                         key=lambda x: (len(x[1]), x[1])):
        print(f"      [{n:<5}] {core.step_title(theo[tab][sid])}")

# ================= 3. Entry — ba cổng, đúng thứ tự OnTick =================
print("\n▸ Entry")
kiem("Entry 8 khối", len(doc["entry"]["steps"]) == 8)
kiem("không khối Sửa lệnh nào lọt vào Entry",
     not any(s.get("type") == core.SUA_LENH for s in doc["entry"]["steps"]))

keys = lambda st: [c["trai"]["ten"] for c in st["conditions"]]  # noqa: E731
# ⭐ CỔNG ZONE và cổng HỎI VỀ ZONE là HAI khối, và thứ tự nói lên nhân quả:
# cổng đầu ĐỊNH NGHĨA zone (qua thì zone lớn thêm một nến, trượt thì zone chết),
# cổng sau mới được hỏi về nó. Gộp lại một khối là hỏi `zone_dem` trước khi có ai
# nói "nến thế nào thì tính là nén".
g_nen = next(s for s in doc["entry"]["steps"] if s.get("cong_zone"))
kiem("cổng ZONE chỉ mang ĐIỀU KIỆN ĐẾM — một mình nó",
     keys(g_nen) == ["atr"], f"— {keys(g_nen)}")
# Chuẩn hoá theo giá giờ là một ĐƠN VỊ của `atr`, không phải toán hạng `atr_bps` riêng.
kiem("điều kiện đếm so bằng đơn vị bps — cùng nghĩa trên mọi symbol",
     g_nen["conditions"][0]["phai"].get("tinh") == "bps",
     f"— {g_nen['conditions'][0]['phai']}")

g_zone = next(s for s in doc["entry"]["steps"]
              if "zone" in core.step_title(s).lower() and not s.get("cong_zone"))
g_cong_zone = next(s for s in doc["entry"]["steps"] if s.get("cong_zone"))
# ⭐ ĐỔI CẤU TRÚC (core.md §12.6f): "đủ K nến" và "zone vừa khổ" giờ là ĐỊNH NGHĨA
# HỢP LỆ, nằm trong phần `dk_hop_le` của chính cổng zone — viết một lần, mọi nơi gọi
# bằng tên. Cổng này chỉ còn hỏi `Zone hợp lệ` + chuyện sổ lệnh.
kiem("cổng sau hỏi: ZONE HỢP LỆ + ZONE CHƯA SINH LỆNH",
     keys(g_zone) == ["zone_hop_le", "zone_da_sinh_lenh"], f"— {keys(g_zone)}")
kiem("định nghĩa HỢP LỆ nằm ở cổng zone, gồm đủ K nến + vừa khổ",
     [c["trai"]["ten"] for c in g_cong_zone.get("dk_hop_le") or []]
     == ["zone_dem", "zone_range"],
     f"— {[c['trai']['ten'] for c in g_cong_zone.get('dk_hop_le') or []]}")
kiem("\"zone đã sinh lệnh\" là điều kiện ĐẢO — thay cho COMP_CONSUMED",
     g_zone["conditions"][-1]["phep"] == "la_sai")
kiem("chỉ có ĐÚNG MỘT cổng zone",
     sum(1 for s in doc["entry"]["steps"] if s.get("cong_zone")) == 1)

# MỐC NEO là một TRƯỜNG, không suy ra từ hướng lệnh nữa — xem `core.MOC_ENTRY`.
mua = next(s for s in doc["entry"]["steps"]
           if s.get("type") == core.VAO_LENH and s.get("huong") == "mua")
ban = next(s for s in doc["entry"]["steps"]
           if s.get("type") == core.VAO_LENH and s.get("huong") == "ban")
kiem("lệnh MUA neo vào ĐỈNH zone", (mua.get("entry") or {}).get("moc") == "zone_HH",
     f"— {mua.get('entry')}")
kiem("lệnh BÁN neo vào ĐÁY zone", (ban.get("entry") or {}).get("moc") == "zone_LL",
     f"— {ban.get('entry')}")

g_cho = next(s for s in doc["entry"]["steps"] if "chỗ" in core.step_title(s))
kiem("cổng hạn mức: đúng MỘT lệnh chờ + số vị thế < Max_Positions",
     keys(g_cho) == ["so_lenh_cho", "so_vi_the"], f"— {keys(g_cho)}")
kiem("dùng \"<\" chứ không phải \"≤\" cho Max_Positions — bằng nhau là đã đầy",
     g_cho["conditions"][1]["phep"] == "<"
     and g_cho["conditions"][0]["phep"] == "==",
     f"— {[c['phep'] for c in g_cho['conditions']]}")

kiem("hai nhánh MUA / BÁN đối xứng",
     len(nhan["entry"]["Buy Stop trên đỉnh vùng"])
     == len(nhan["entry"]["Sell Stop dưới đáy vùng"]))

# ================= 4. Hai chữ ATR =================
print("\n▸ Hai chữ ATR — tách ra là có chủ ý")
# Giá trị nằm ở BẢNG THAM SỐ, khối chỉ gọi bằng tên — nên phải kiểm CẢ HAI vế: khối
# trỏ đúng tham số nào, và tham số đó mang đúng con số nào.
TS = {t["ten"]: t["gia_tri"] for t in doc["tham_so"]}
for ten in ("Buy Stop trên đỉnh vùng", "Sell Stop dưới đáy vùng"):
    st = next(s for s in doc["entry"]["steps"] if core.step_title(s) == ten)
    kiem(f"{ten}: đệm = ATR HIỆN TẠI",
         st["dem"]["tinh"] == "atr" and TS[st["dem"]["value"]] == 0.10,
         f"— {st.get('dem')}")
    kiem(f"{ten}: rủi ro = ATR TRUNG BÌNH VÙNG",
         st["sl"]["tinh"] == "atr_zone" and TS[st["sl"]["value"]] == 1.5,
         f"— {st.get('sl')}")
    kiem(f"{ten}: TP = 2R",
         st["tp"]["tinh"] == "R" and TS[st["tp"]["value"]] == 2.0)

# ================= 5. Manage =================
print("\n▸ Manage")
kiem("Manage 5 khối", len(doc["manage"]["steps"]) == 5)
kiem("không khối Vào lệnh nào lọt vào Manage",
     not any(s.get("type") == core.VAO_LENH for s in doc["manage"]["steps"]))

g_be = next(s for s in doc["manage"]["steps"] if "1R" in core.step_title(s))
kiem("cổng hoà vốn gói ĐỦ BA dòng guard của ManageBreakEven",
     keys(g_be) == ["lenh_da_khop", "lenh_sl_hoa_von", "lenh_lai_R"],
     f"— {keys(g_be)}")
kiem("\"SL chưa ở hoà vốn\" là điều kiện ĐẢO — thiếu nó là sửa SL mỗi nến",
     g_be["conditions"][1]["phep"] == "la_sai")

be_hd = next(s for s in doc["manage"]["steps"] if s.get("che_do") == "hoa_von")
kiem("hành động hoà vốn KHÔNG mang tham số — mốc kích hoạt đã dời lên cổng",
     "khoang" not in be_hd, f"— {be_hd}")

g_huy = next(s for s in doc["manage"]["steps"] if "tan" in core.step_title(s))
kiem("cổng huỷ: lệnh này CHƯA khớp ∧ nén đã tan",
     keys(g_huy) == ["lenh_da_khop", "atr"]
     and g_huy["conditions"][0]["phep"] == "la_sai"
     and g_huy["conditions"][1]["phep"] == ">="
     # CÙNG đơn vị với cổng vào — hai nơi hỏi một câu thì phải cùng thước.
     and g_huy["conditions"][1]["phai"].get("tinh") == "bps")

# ================= 6. Ranh giới bị phá thì phải BÁO =================
print("\n▸ Ranh giới Entry / Manage được canh")
xau = {"entry": {"steps": [dict(be_hd)], "edges": []},
       "manage": {"steps": [], "edges": []}}
kiem("nhét Sửa lệnh vào Entry → báo lỗi",
     any(p["tab"] == "entry" and "chỉ thuộc về" in p["message"]
         for p in core.validate_process(xau)))

xau2 = {"entry": {"steps": [dict(g_be)], "edges": []},
        "manage": {"steps": [], "edges": []}}
kiem("hỏi \"lệnh này\" trong Entry → báo lỗi",
     any(p["tab"] == "entry" and "Lệnh này" in p["message"]
         for p in core.validate_process(xau2)))

# ================= 7. thẻ vẽ lên hộp =================
print("\n▸ Thẻ vẽ lên hộp")
cards = {c["id"]: c for c in doc["entry"]["cards"]}
kiem("mọi khối Entry đều có thẻ", len(cards) == len(doc["entry"]["steps"]))
kiem("mỗi điều kiện là MỘT dòng riêng trên hộp",
     len(cards[g_zone["id"]]["lines"]) == 2,
     f"— {len(cards[g_zone['id']]['lines'])}")
# Chữ trên hộp hiện CẢ TÊN LẪN GIÁ TRỊ của tham số: tên nói ý nghĩa, số nói thực tế.
# Thiếu một trong hai thì phải mở bảng tham số ra mới đọc nổi sơ đồ.
# Dấu `=` kẹp giữa hai KHOẢNG TRẮNG KHÔNG NGẮT ( ): chữ trên hộp xuống dòng được,
# mà `nguong_nen_bps =` nằm cuối dòng còn `7` rơi xuống dòng sau thì đọc mất nghĩa.
# Dòng 0 của cổng zone là BĂNG RÔN "⬗ CỔNG ZONE" — nó nói khối này định nghĩa zone,
# chuyện lớn nhất một cổng làm được, nên nó phải đứng trên cùng. Điều kiện bắt đầu từ 1.
kiem("cổng zone có băng rôn nói nó ĐỊNH NGHĨA zone",
     cards[g_nen["id"]]["lines"][0]["text"].startswith("⬗ CỔNG ZONE"),
     f"— \"{cards[g_nen['id']]['lines'][0]['text']}\"")
kiem("chữ trên hộp dùng ký hiệu, và tham số hiện cả tên lẫn giá trị",
     cards[g_nen["id"]]["lines"][1]["text"]
     == "ATR(M5, 14) < nguong_nen_bps = 7 bps của giá",
     f"— \"{cards[g_nen['id']]['lines'][1]['text']}\"")
kiem("tên tham số KHÔNG bị tách khỏi giá trị khi hộp xuống dòng",
     " = " not in cards[g_nen["id"]]["lines"][1]["text"])
kiem("tham số của toán hạng thì hiện GIÁ TRỊ (14), không hiện tên — nó là "
     "\"đọc chuỗi nào\", không phải núm vặn",
     "(M5, 14)" in cards[g_nen["id"]]["lines"][1]["text"])

# Chữ trên hộp phải NGẮN, mỗi trường một dòng. Một câu chạy dài "Vào lệnh Mua Chờ Stop ·
# lot = 0.01 lot · đệm dem_vao_lenh = 0.1 × ATR hiện tại ngoài mép vùng · SL …" nhét lên
# hộp thì nuốt cả khối, mà nhìn hộp là phải hiểu ngay chứ không phải đọc một đoạn văn.
v_mua = next(x for x in doc["entry"]["steps"]
             if x.get("type") == core.VAO_LENH and x.get("huong") == "mua")
tv = cards[v_mua["id"]]
kiem("khối Vào lệnh tách mỗi trường một dòng",
     [d["text"] for d in tv["lines"]] == [
         "Mua · Chờ Stop · 0.01 lot",
         # MỐC NEO đứng TRƯỚC đệm: nó quyết định lệnh nằm ở đâu, đệm chỉ là tấm khiên.
         "tại Đỉnh zone (HH)",
         "đệm dem_vao_lenh = 0.1 × ATR",
         "SL sl_theo_atr_vung = 1.5 × ATR zone",
         "TP ty_le_RR = 2 × R"],
     f"— {[d['text'] for d in tv['lines']]}")
dong_lenh = [d["text"] for t in core.TABS for c in doc[t]["cards"] for d in c["lines"]
             if d["type"] in (core.VAO_LENH, core.SUA_LENH)]
kiem("dòng vào/sửa lệnh đều ngắn (≤ 40 ký tự) — vừa một hàng, không phải đoạn văn",
     all(len(x) <= 40 for x in dong_lenh),
     f"— dài nhất: \"{max(dong_lenh, key=len)}\"")
kiem("câu ĐẦY ĐỦ vẫn còn, để làm tooltip",
     "ngoài mép vùng" in tv["mo_ta"] and "× ATR zone" in tv["mo_ta"],
     f"— \"{tv['mo_ta']}\"")

# ================= 7b. NHỊP nằm trên khối Bắt đầu =================
print("\n▸ Nhịp chạy")
bd = {t: next(x for x in doc[t]["steps"] if core.is_start_step(x)) for t in core.TABS}
kiem("nhịp là dữ liệu của khối Bắt đầu, không phải khoá của tài liệu",
     all("nhip" in bd[t] for t in core.TABS) and "timeframe" not in doc)
kiem("Entry M5 (quyết định) · Manage M1 (phản ứng) — hai nhịp KHÁC nhau là cố ý",
     (bd["entry"]["nhip"], bd["manage"]["nhip"]) == ("M5", "M1"),
     f'— {bd["entry"]["nhip"]} / {bd["manage"]["nhip"]}')
# Chữ trên hộp phải SINH RA từ khoá `nhip`. Bản cũ gõ tay "M5" vào tên khối nên đổi
# nhịp thì khối vẫn ghi M5 — sơ đồ nói dối, đúng lỗi `7.0` viết cứng hai chỗ ngày trước.
kiem("chữ trên khối Bắt đầu sinh từ `nhip`, không phải tên gõ tay",
     core.dong_khoi(bd["entry"])[0] == "Mỗi nến M5"
     and core.dong_khoi(dict(bd["entry"], nhip="H1"))[0] == "Mỗi nến H1")
kiem("không tên khối nào còn viết cứng khung thời gian",
     not any(k in (st.get("name") or "")
             for t in core.TABS for st in doc[t]["steps"] for k in core.TIMEFRAMES),
     f'— {[st.get("name") for t in core.TABS for st in doc[t]["steps"]]}')
kiem("hộp Manage nói rõ 'một lượt cho MỖI lệnh' — đó là cấu trúc, không phải tên",
     any("MỖI lệnh" in x for x in core.dong_khoi(bd["manage"], None, core.TAB_MANAGE)))

# File schema 3 chỉ có MỘT `timeframe` cho cả tài liệu. Mở lại phải ra nhịp trên khối.
cu = {"schema": 3, "timeframe": "M15", "name": "cũ",
      "entry": {"steps": [{"kind": "start"}], "edges": []},
      "manage": {"steps": [{"kind": "start"}], "edges": []}}
mo = core.normalize_process(cu)
kiem("file cũ (schema 3) mở lại được: `timeframe` di cư sang khối Bắt đầu",
     mo["schema"] == 4 and "timeframe" not in mo
     and mo["entry"]["steps"][0]["nhip"] == "M15"
     and mo["manage"]["steps"][0]["nhip"] == "M1")
kiem("nhịp rác thì rơi về mặc định chứ không lọt vào file",
     core.normalize_process({"entry": {"steps": [{"kind": "start", "nhip": "XX"}]}}
                            )["entry"]["steps"][0]["nhip"] == "M5")

xau_nhip = json.loads(json.dumps(doc))
xau_nhip["manage"]["steps"][0]["nhip"] = "M15"
kiem("Manage chậm hơn Entry → cảnh báo (quản lý là phản ứng, phải nhanh hơn)",
     any(p["severity"] == "warning" and "CHẬM hơn Entry" in p["message"]
         for p in core.validate_process(xau_nhip)))

# ================= 7c. công thức ATR & thứ tự nhánh =================
print("\n▸ Bẫy im lặng")
atr = next(c for c in kho.chi_bao.CHI_BAO if c["key"] == "atr")
# `iATR` của MT5 là SMA của True Range, KHÔNG phải Wilder. Ngưỡng 7.0 bps của D_02 được
# dò ra trên chính con số iATR trả về — chép nhầm sang Wilder là ATR khác, atr_bps khác,
# nến nào là "nến nén" khác, rồi số nến nén / thời điểm xác nhận / 1R / TP lệch dây chuyền.
kiem("ATR khai đúng iATR của MT5 — SMA của True Range, và nói rõ KHÔNG phải Wilder",
     atr["cong_thuc"].startswith("SMA của True Range")
     and "KHÔNG phải Wilder" in atr["cong_thuc"],
     f'— {atr["cong_thuc"]!r}')

# Thứ tự nhánh lấy từ (ghim, y, x, id). Hai đầu nhánh ngang nhau thì phân định bằng
# `id` — một uuid không ai nhìn thấy — nên kết quả backtest phụ thuộc toạ độ canvas.
ngang = json.loads(json.dumps(doc))
for st in ngang["entry"]["steps"]:
    if "Xu hướng" in (st.get("name") or ""):
        st["pos"][1] = 300.0
kiem("hai nhánh đặt NGANG NHAU → báo LỖI (thứ tự phải nhìn thấy được)",
     any(p["severity"] == "error" and "NGANG NHAU" in p["message"]
         for p in core.validate_process(ngang)))
lech = json.loads(json.dumps(ngang))
for st in lech["entry"]["steps"]:
    if "XUỐNG" in (st.get("name") or ""):
        st["pos"][1] = 300.0 + core.LECH_TOI_THIEU
kiem(f"kéo lệch đủ {core.LECH_TOI_THIEU:.0f} px là hết lỗi",
     not any("NGANG NHAU" in p["message"] for p in core.validate_process(lech)))
kiem("sơ đồ mẫu không dính lỗi này",
     not any("NGANG NHAU" in p["message"] for p in core.validate_process(doc)))

# ================= 8. lưu / mở lại =================
print("\n▸ Lưu / mở lại")
r = a.save_process(dict(doc, name="__test_mau__"))
kiem("lưu được", r["ok"])
r2 = a.load_process("__test_mau__")
kiem("mở lại được", r2["ok"])
if r2["ok"]:
    v2 = a.validate(r2["value"])
    kiem("mở lại vẫn ĐÚNG y nhãn cũ, cả hai tab",
         all(v2["luong"][t]["order"] == v["luong"][t]["order"] for t in core.TABS))
    kiem("mở lại vẫn sạch", not v2["value"])
core.delete_template("strategy", "__test_mau__")

# ====== MỌI DOC TỚI TAY GIAO DIỆN ĐỀU PHẢI ĐÃ CHUẨN HOÁ ======
#
# Ca thật: `demo_process` gọi `_kem_the(_so_do_mau())` — thiếu đúng một lời gọi
# `normalize_process`. Sơ đồ mẫu vì thế thiếu cờ `so_dai_luong` (cờ này CHỈ chuẩn hoá
# mới sinh được), nên mở cổng "Xu hướng LÊN?" ra thì hộp thoại tưởng là cơ chế "so với
# giá trị": ô số trắng trơn, cột đơn vị in "giá tuyệt đối".
#
# Mà CHỮ TRÊN THẺ vẫn đúng — `cond_display` tự suy từ `phai.ten` chứ không đọc cờ. Hai
# nguồn cho một sự thật, và cái lệch thì im lặng. Đúng loại lỗi không ai thấy cho tới
# khi mở đúng cái hộp thoại đó ra.
#
# Bài này canh CẢ LỚP chứ không riêng ca ấy: chuẩn hoá lại thứ endpoint vừa trả về, phải
# ra y hệt. Lệch nghĩa là có chỗ nào đó lại quên chuẩn hoá.
print("\n▸ Mọi endpoint trả doc đều phải trả doc ĐÃ chuẩn hoá")


def _tran(doc):
    """Bỏ `cards` — nó do `_kem_the` gắn thêm, không thuộc doc."""
    return {k: ({kk: vv for kk, vv in v.items() if kk != "cards"}
                if isinstance(v, dict) else v)
            for k, v in doc.items()}


core.save_template("strategy", "__test_chuan__", api._so_do_mau())
for ten, goi in (("new_process", a.new_process),
                 ("demo_process", a.demo_process),
                 ("load_process", lambda: a.load_process("__test_chuan__"))):
    r = goi()
    d = _tran(r["value"])
    kiem(f"`{ten}` trả doc đã chuẩn hoá",
         json.dumps(d, sort_keys=True, ensure_ascii=False)
         == json.dumps(_tran(core.normalize_process(d)), sort_keys=True,
                       ensure_ascii=False))
core.delete_template("strategy", "__test_chuan__")

# Chốt riêng cho đúng cái trường đã lộ ra lỗ: nó phải tới được giao diện.
_mau = a.demo_process()["value"]
_xu_huong = [st for st in _mau["entry"]["steps"]
             if "Xu hướng" in (st.get("name") or "")]
kiem("cổng xu hướng mang cờ `so_dai_luong` khi tới tay giao diện",
     len(_xu_huong) == 2 and all(st.get("so_dai_luong") for st in _xu_huong),
     f"— {[st.get('so_dai_luong') for st in _xu_huong]}")

# Bất biến của `normalize_process` là thứ cho phép `_kem_the` tự chuẩn hoá mà không sợ
# chồng lên mấy chỗ đã chuẩn hoá sẵn.
_n1 = core.normalize_process(api._so_do_mau())
kiem("chuẩn hoá HAI lần bằng đúng MỘT lần",
     json.dumps(_n1, sort_keys=True, ensure_ascii=False)
     == json.dumps(core.normalize_process(_n1), sort_keys=True, ensure_ascii=False))

# --------------------------------------------------------------------------
# BẢNG SỐ LIỆU — hàng do `core.toan_hang_dung` sinh (core.md §12.9b, §12.9e)
#
# Trước lượt sửa này KHÔNG bài nào gọi `toan_hang_dung`, dù cả bảng số liệu LẪN danh sách
# cột engine `bo_chay` phải ghi đều treo vào nó. Triệu chứng đã có thật: bảng in ra HAI
# dòng `ATR · M5·14 · 1.412` y hệt nhau — một dòng là vế trái cổng nén (đọc bằng `bps`),
# một dòng do đệm vào lệnh dùng `× ATR` sinh ra (đơn vị GIÁ). Chúng khác nhau ở ĐƠN VỊ
# TẠI CHỖ ĐỌC, mà đơn vị thì không đi theo hàng.
print("\n▸ Bảng số liệu — hàng, đơn vị tại chỗ đọc, cột engine")

_d = core.normalize_process(api._so_do_mau())
_th = core.toan_hang_dung(_d)

# Thứ tự = thứ tự sơ đồ ĐỌC. Cổng zone góp `atr` (phần đếm) rồi `zone_dem`, `zone_range`
# (phần hợp lệ); `atr` thứ HAI là mẫu số ngầm của đơn vị `× ATR` trên `zone_range`
# (`TINH_CAN_TOAN_HANG`), không phải trùng lặp — nó là ATR khung quyết định, khác cái
# `atr(M5)` ở trên. Rồi mới tới cổng sau: `zone_hop_le`, `zone_da_sinh_lenh`.
_TEN = ["atr", "zone_dem", "zone_range", "atr", "zone_hop_le", "zone_da_sinh_lenh",
        "so_lenh_cho", "so_vi_the", "close", "ma", "zone_atr_tb", "zone_HH", "zone_LL"]
kiem("sơ đồ mẫu sinh đúng 13 hàng, đúng thứ tự sơ đồ đọc",
     [x["ten"] for x in _th] == _TEN, f"— {len(_th)} hàng")

_atr = [(i, x) for i, x in enumerate(_th) if x["ten"] == "atr"]
kiem("có ĐÚNG HAI hàng ATR — không gộp, không tách thêm", len(_atr) == 2,
     f"— {len(_atr)} hàng")

_a0, _a1 = (_atr + [(None, {}), (None, {})])[:2]
kiem("hàng ATR của cổng nén mang đơn vị `bps`",
     _a0[1].get("don_vi") == "bps" and _a0[1].get("tf") == "M5"
     and _a0[1].get("period") == "chu_ky_atr",
     f"— {_a0[1].get('tf')}·{_a0[1].get('period')} [{_a0[1].get('don_vi')}]")
kiem("hàng ATR của đệm vào lệnh mang đơn vị GIÁ (`None`) — nó là SỐ NHÂN, không phải "
     "đại lượng đang đo",
     _a1[1].get("don_vi") is None and _a1[1].get("tf") == "M5",
     f"— {_a1[1].get('tf')}·{_a1[1].get('period')} [{_a1[1].get('don_vi')}]")

# ĐÂY là hợp đồng chống trùng mặt: hai hàng khác nhau ĐÚNG ở chỗ chúng vốn khác.
_khac = sorted(k for k in set(_a0[1]) | set(_a1[1]) if _a0[1].get(k) != _a1[1].get(k))
kiem("hai hàng ATR khác nhau ĐÚNG MỘT trường: `don_vi`", _khac == ["don_vi"],
     f"— khác ở {_khac}")

# `tf` chuẩn hoá phải xảy ra Ở TẦNG NÀY, không ở `api.py`. Trước đây nó nằm dưới tầng
# hiển thị nên hai hàng khác khoá (`tf=None` vs `'M5'`) lại đổ ra cùng một mặt.
_trong = [x["ten"] for x in _th
          if "tf" in core.TOAN_HANG_THAMSO.get(x["ten"], ()) and not x.get("tf")]
kiem("mọi toán hạng khai được `tf` đều đã có `tf` — chuẩn hoá đúng tầng", not _trong,
     f"— {_trong}")

kiem("`zone_range` mang đơn vị `atr` — đơn vị lấy từ vế PHẢI của điều kiện",
     next(x["don_vi"] for x in _th if x["ten"] == "zone_range") == "atr")
_sinh = [x["ten"] for x in _th
         if x["ten"] in ("zone_atr_tb", "zone_HH", "zone_LL") and x["don_vi"] is not None]
kiem("hàng sinh từ `TINH_CAN_TOAN_HANG` KHÔNG mượn `tinh` của khối dem/sl/tp",
     not _sinh, f"— {_sinh}")

_la = [x["don_vi"] for x in _th
       if x["don_vi"] is not None
       and (x["don_vi"] == "gia" or x["don_vi"] not in core.DON_VI_HIEN)]
kiem("mọi đơn vị hiển thị đều nằm trong 4 nhánh `_quy_doi` cài — `R`/`bien_zone` không "
     "lọt tới hàm quy đổi cột", not _la, f"— {_la}")

# ⚠ RÀNG BUỘC CỨNG. `bo_chay` lấy danh sách cột engine phải ghi từ chính hàm này. Siết
# dedupe hay bỏ hàng là engine ghi thiếu cột → `kq.cot_zone` thiếu khoá → bảng trống, và
# không có gì báo. Bài này đỏ ngay tại chỗ đó.
_cv = tuple(dict.fromkeys(x["ten"] for x in _th
                          if x["ten"] in kho.engine_d02.ENGINE_TRA_LOI))
kiem("danh sách cột engine `bo_chay` phải ghi KHÔNG đổi",
     _cv == ("zone_dem", "zone_range", "zone_hop_le", "zone_da_sinh_lenh",
             "zone_atr_tb", "zone_HH", "zone_LL"), f"— {_cv}")

kiem("khung quyết định suy từ khối Bắt đầu, một chỗ duy nhất",
     core.khung_quyet_dinh(_d) == "M5", f"— {core.khung_quyet_dinh(_d)}")

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
