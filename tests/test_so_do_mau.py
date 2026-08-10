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

import api  # noqa: E402
import core  # noqa: E402

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
      f"{len(bv['cach_tinh'])} cách tính khoảng cách")

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
kiem("Entry 7 khối", len(doc["entry"]["steps"]) == 7)
kiem("không khối Sửa lệnh nào lọt vào Entry",
     not any(s.get("type") == core.SUA_LENH for s in doc["entry"]["steps"]))

keys = lambda st: [c["trai"]["ten"] for c in st["conditions"]]  # noqa: E731
g_nen = next(s for s in doc["entry"]["steps"] if "nén" in core.step_title(s).lower())
kiem("cổng nén: ngưỡng + đủ K nến + vùng vừa khổ + VÙNG CHƯA SINH LỆNH",
     keys(g_nen) == ["atr_bps", "so_nen_nen", "rong_vung_atr", "vung_da_sinh_lenh"],
     f"— {keys(g_nen)}")
kiem("\"vùng đã sinh lệnh\" là điều kiện ĐẢO — thay cho COMP_CONSUMED",
     g_nen["conditions"][-1].get("dao") is True)

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
         st["dem"]["tinh"] == "theo_ATR" and TS[st["dem"]["value"]] == 0.10,
         f"— {st.get('dem')}")
    kiem(f"{ten}: rủi ro = ATR TRUNG BÌNH VÙNG",
         st["sl"]["tinh"] == "theo_ATR_vung" and TS[st["sl"]["value"]] == 1.5,
         f"— {st.get('sl')}")
    kiem(f"{ten}: TP = 2R",
         st["tp"]["tinh"] == "theo_R" and TS[st["tp"]["value"]] == 2.0)

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
     g_be["conditions"][1].get("dao") is True)

be_hd = next(s for s in doc["manage"]["steps"] if s.get("che_do") == "hoa_von")
kiem("hành động hoà vốn KHÔNG mang tham số — mốc kích hoạt đã dời lên cổng",
     "khoang" not in be_hd, f"— {be_hd}")

g_huy = next(s for s in doc["manage"]["steps"] if "tan" in core.step_title(s))
kiem("cổng huỷ: lệnh này CHƯA khớp ∧ nén đã tan",
     keys(g_huy) == ["lenh_da_khop", "atr_bps"]
     and g_huy["conditions"][0].get("dao") is True
     and g_huy["conditions"][1]["phep"] == ">=")

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
     len(cards[g_nen["id"]]["lines"]) == 4, f"— {len(cards[g_nen['id']]['lines'])}")
# Chữ trên hộp hiện CẢ TÊN LẪN GIÁ TRỊ của tham số: tên nói ý nghĩa, số nói thực tế.
# Thiếu một trong hai thì phải mở bảng tham số ra mới đọc nổi sơ đồ.
# Dấu `=` kẹp giữa hai KHOẢNG TRẮNG KHÔNG NGẮT ( ): chữ trên hộp xuống dòng được,
# mà `nguong_nen_bps =` nằm cuối dòng còn `7` rơi xuống dòng sau thì đọc mất nghĩa.
kiem("chữ trên hộp dùng ký hiệu, và tham số hiện cả tên lẫn giá trị",
     cards[g_nen["id"]]["lines"][0]["text"]
     == "ATR chuẩn hoá (bps)(M5, 14) < nguong_nen_bps = 7",
     f"— \"{cards[g_nen['id']]['lines'][0]['text']}\"")
kiem("tên tham số KHÔNG bị tách khỏi giá trị khi hộp xuống dòng",
     " = " not in cards[g_nen["id"]]["lines"][0]["text"])
kiem("tham số của toán hạng thì hiện GIÁ TRỊ (14), không hiện tên — nó là "
     "\"đọc chuỗi nào\", không phải núm vặn",
     "(M5, 14)" in cards[g_nen["id"]]["lines"][0]["text"])

# Chữ trên hộp phải NGẮN, mỗi trường một dòng. Một câu chạy dài "Vào lệnh Mua Chờ Stop ·
# lot = 0.01 lot · đệm dem_vao_lenh = 0.1 × ATR hiện tại ngoài mép vùng · SL …" nhét lên
# hộp thì nuốt cả khối, mà nhìn hộp là phải hiểu ngay chứ không phải đọc một đoạn văn.
v_mua = next(x for x in doc["entry"]["steps"]
             if x.get("type") == core.VAO_LENH and x.get("huong") == "mua")
tv = cards[v_mua["id"]]
kiem("khối Vào lệnh tách mỗi trường một dòng",
     [d["text"] for d in tv["lines"]] == [
         "Mua · Chờ Stop · 0.01 lot",
         "đệm dem_vao_lenh = 0.1 × ATR",
         "SL sl_theo_atr_vung = 1.5 × ATR vùng",
         "TP ty_le_RR = 2 × R"],
     f"— {[d['text'] for d in tv['lines']]}")
dong_lenh = [d["text"] for t in core.TABS for c in doc[t]["cards"] for d in c["lines"]
             if d["type"] in (core.VAO_LENH, core.SUA_LENH)]
kiem("dòng vào/sửa lệnh đều ngắn (≤ 40 ký tự) — vừa một hàng, không phải đoạn văn",
     all(len(x) <= 40 for x in dong_lenh),
     f"— dài nhất: \"{max(dong_lenh, key=len)}\"")
kiem("câu ĐẦY ĐỦ vẫn còn, để làm tooltip",
     "ngoài mép vùng" in tv["mo_ta"] and "trung bình của vùng nén" in tv["mo_ta"],
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

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
