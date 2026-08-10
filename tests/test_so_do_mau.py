"""Sơ đồ mẫu Compress phải mở ra SẠCH: không lỗi, không cảnh báo vòng lặp hở.

Bài này là bằng chứng bộ khối (Kiểm tra điều kiện / Vào lệnh / Sửa lệnh) đủ sức diễn
tả một chiến lược THẬT — chứ không phải chỉ vẽ cho vui. Mẫu hỏng thì đó là lỗi thiết
kế bộ khối, không phải lỗi của cái mẫu.

Chạy:  python tests\\test_so_do_mau.py
"""
import io
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

print("\n▸ bootstrap")
b = a.bootstrap()
kiem("bootstrap trả về được", b["ok"])
bv = b["value"]
kiem("chỉ hiện 3 hành động: Kiểm tra ĐK / Vào lệnh / Sửa lệnh",
     bv["action_types"] == ["check_cond", "vao_lenh", "sua_lenh"],
     f"— {bv['action_types']}")
kiem("lõi vẫn hiểu đủ 4 hành động (Đặt cờ để dành, chỉ bị ẩn khỏi bảng chọn)",
     len(bv["action_types_tat_ca"]) == 4)
kiem("có đủ toán hạng cho Compress",
     {"atr_bps", "ma", "close", "so_nen_nen", "rong_vung_atr", "lenh_da_khop"}
     <= {t["key"] for t in bv["toan_hang"]})
print(f"    {len(bv['toan_hang'])} toán hạng / "
      f"{len(set(t['nhom'] for t in bv['toan_hang']))} nhóm, "
      f"{len(bv['phep_so'])} phép so, {len(bv['sua_che_do'])} chế độ Sửa lệnh")

print("\n▸ sơ đồ mẫu Compress")
d = a.demo_process()
kiem("mở được", d["ok"])
doc = d["value"]
kiem("có đúng một khối Bắt đầu",
     sum(1 for s in doc["steps"] if core.is_start_step(s)) == 1)

v = a.validate(doc["steps"], doc["edges"])
kiem("KHÔNG có lỗi nào", v["so_loi"] == 0,
     f"— {[p['message'][:90] for p in v['value'] if p['severity'] == 'error']}")
kiem("mọi khối đều có nhãn (không khối nào lạc)",
     len(v["order"]) == len(doc["steps"]) and not v["unreachable"],
     f"— {len(v['order'])}/{len(doc['steps'])}, lạc: {v['unreachable']}")
kiem("mọi cạnh quay lại đều ĐÃ GHIM, không còn vòng hở nào",
     len(v["quay_lai"]) == 3 and not v["vong_ho"],
     f"— quay_lai={len(v['quay_lai'])}, vòng hở={len(v['vong_ho'])}")
kiem("không cảnh báo nào nhắc tới vòng lặp chưa ghim",
     not any("chưa được ghim" in p["message"] for p in v["value"]))
kiem("SẠCH hoàn toàn — không lỗi, không cảnh báo",
     not v["value"], f"— {[p['message'][:80] for p in v['value']]}")

# Hai nhánh MUA/BÁN phải đối xứng: cùng mức, chỉ khác chữ. Lệch nhau (một cái "4",
# cái kia "3B") là dấu hiệu `diem_gop` nhận nhầm đầu nhánh làm điểm gộp khi đồ thị
# có vòng lặp — đúng lỗi đã sửa.
_nhan = {core.step_title(theo := {s["id"]: s for s in doc["steps"]}[sid]): n
         for sid, n in v["order"].items()}
kiem("nhánh MUA và BÁN đối xứng (3A / 3B)",
     _nhan.get("Xu hướng LÊN (M15)") == "3A"
     and _nhan.get("Xu hướng XUỐNG (M15)") == "3B",
     f"— LÊN={_nhan.get('Xu hướng LÊN (M15)')}, "
     f"XUỐNG={_nhan.get('Xu hướng XUỐNG (M15)')}")
kiem("sau khi hai nhánh chụm lại, số về mức trên cùng (4)",
     _nhan.get("Chờ khớp / chờ vùng tan") == "4",
     f"— {_nhan.get('Chờ khớp / chờ vùng tan')}")

print("\n  ── Nhãn trên sơ đồ ──")
theo = {s["id"]: s for s in doc["steps"]}
for sid, n in sorted(v["order"].items(),
                     key=lambda x: (len(x[1].split(".")[0]), x[1])):
    g = "  ⟲ đã ghim" if theo[sid].get("ghim") else ""
    print(f"    [{n:<4}] {core.step_title(theo[sid])}{g}")

if v["value"]:
    print("\n  ── Còn lại ──")
    for p in v["value"]:
        print(f"    {'●' if p['severity'] == 'error' else '▲'} {p['message'][:120]}")

print("\n▸ thẻ vẽ lên hộp")
cards = {c["id"]: c for c in doc["cards"]}
kiem("mọi khối đều có thẻ", len(cards) == len(doc["steps"]))
kiem("cổng rẽ nhánh được đánh dấu `la_cong`",
     sum(1 for c in cards.values() if c["la_cong"]) >= 5)
kiem("khối đã ghim được đánh dấu trên thẻ",
     any(c["ghim"] for c in cards.values()))
mot = next(c for c in cards.values() if c["kind"] == "action" and c["la_cong"])
kiem("chữ trên hộp do Python sinh, đọc được thành câu",
     bool(mot["lines"]) and len(mot["lines"][0]["text"]) > 10,
     f"— \"{mot['lines'][0]['text'][:70]}\"")

print("\n▸ lưu / mở lại")
r = a.save_process("__test_mau__", doc["steps"], doc["edges"], "XAUUSD", "M5")
kiem("lưu được", r["ok"])
r2 = a.load_process("__test_mau__")
kiem("mở lại được", r2["ok"])
if r2["ok"]:
    v2 = a.validate(r2["value"]["steps"], r2["value"]["edges"])
    kiem("mở lại vẫn ĐÚNG y nhãn cũ (cờ ghim và pos sống sót qua file)",
         v2["order"] == v["order"], f"— {v2['order'] == v['order']}")
core.delete_template("strategy", "__test_mau__")

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
