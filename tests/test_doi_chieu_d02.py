"""ĐỐI CHIẾU từng luật của D_02 với sơ đồ mẫu trong Cat_Studio.

Bài này KHÔNG kiểm code chạy đúng — hai bài kia lo việc đó. Nó trả lời một câu duy
nhất: **có luật nào của EA gốc bị rơi mất khi chuyển sang sơ đồ không.**

Nguồn:
    Projects\\Experts\\Compress.mq5
    Include\\Controller\\FilterEngine.mqh
    Include\\Controller\\TradeManager.mqh
    Include\\Inputs\\Parameters.mqh

Mỗi luật ghi kèm dòng mã gốc, để sau này ai sửa sơ đồ mà làm rơi một luật thì bài này
chỉ thẳng vào luật đó, không phải đi đọc lại MQL5.

Cuối bài in bảng NHỮNG CHỖ CỐ Ý KHÁC — không phải lỗi, là quyết định. Ai đọc cũng thấy
ngay ta lệch bản gốc ở đâu và vì sao.

Chạy:  python tests\\test_doi_chieu_d02.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import api  # noqa: E402
import core  # noqa: E402
import kho  # noqa: E402

dung = sai = 0


def kiem(ma, luat, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ma}  {luat} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ma}  {luat} {chi_tiet}")


a = api.Api()
doc = a.demo_process()["value"]
TS = {t["ten"]: t["gia_tri"] for t in doc["tham_so"]}
KHOI = {tab: {core.step_title(s): s for s in doc[tab]["steps"]} for tab in core.TABS}


def cong(tab, chua):
    """Khối cổng đầu tiên có tên chứa `chua`."""
    return next(s for t, s in KHOI[tab].items() if chua in t)


def dk_cua(st):
    """{tên toán hạng: điều kiện} của một cổng."""
    return {c["trai"]["ten"]: c for c in st.get("conditions") or []}


def hd_cua(tab, chua):
    return next(s for t, s in KHOI[tab].items()
                if chua in t and s.get("type") in (core.VAO_LENH, core.SUA_LENH))


# ============================ PHÁT HIỆN NÉN ============================
print("\n▸ FilterEngine::UpdateCompression — phát hiện nén")
g_nen = cong("entry", "Vùng nén")
c = dk_cua(g_nen)

kiem("F1", "đọc ATR ở nến ĐÃ ĐÓNG [1], không repaint",
     all(x.get("shift", 1) != 0
         for s in doc["entry"]["steps"] for cc in s.get("conditions") or []
         for x in (cc["trai"], cc.get("phai")) if isinstance(x, dict)))
kiem("F2", "atr_bps = (ATR / close) × 10000",
     "atr_bps" in kho.TOAN_HANG_KEYS
     and "10000" in next(x["cong_thuc"] for x in kho.CHI_BAO if x["key"] == "atr_bps"))
kiem("F3", "nén khi atr_bps < ngưỡng N",
     c["atr_bps"]["phep"] == "<" and c["atr_bps"]["phai"] == "nguong_nen_bps")
kiem("F4", "đủ K nến nén LIÊN TIẾP",
     c["so_nen_nen"]["phep"] == ">=" and TS[c["so_nen_nen"]["phai"]] == 10)
kiem("F5", "vùng không rộng quá Range_Max × ATR (luôn bật, không tắt được)",
     c["rong_vung_atr"]["phep"] == "<=" and TS[c["rong_vung_atr"]["phai"]] == 4.0)
kiem("F6", "đỉnh/đáy vùng lấy từ High/Low các nến nén",
     {"dinh_vung", "day_vung"} <= set(kho.TOAN_HANG_KEYS))
kiem("F7", "ConsumeSignal — một cú nén, một lệnh",
     c["vung_da_sinh_lenh"].get("dao") is True)

# ============================ LỌC XU HƯỚNG ============================
print("\n▸ FilterEngine::UpdateMATrend — lọc xu hướng")
g_len, g_xuong = cong("entry", "LÊN"), cong("entry", "XUỐNG")
t_len = (dk_cua(g_len)["close"], dk_cua(g_xuong)["close"])

kiem("T1", "so Close[1] với MA[1] trên khung TREND (M15)",
     all(x["trai"]["tf"] == "M15" and x["trai"]["shift"] == 1 for x in t_len)
     and all(x["phai"]["tf"] == "M15" for x in t_len))
kiem("T2", "MUA khi Close > MA · BÁN khi Close < MA",
     t_len[0]["phep"] == ">" and t_len[1]["phep"] == "<")
kiem("T3", "Close == MA (SIDEWAY) → KHÔNG vào lệnh nào",
     ">" not in ("" if t_len[0]["phep"] != ">=" else "x")
     and t_len[0]["phep"] != ">=" and t_len[1]["phep"] != "<=")
kiem("T4", "MA dùng SMA, chu kỳ lấy từ tham số",
     t_len[0]["phai"]["method"] == "SMA" and TS[t_len[0]["phai"]["period"]] == 50)

# ============================ HẠN MỨC ============================
print("\n▸ Compress.mq5 OnTick — hạn mức")
g_cho = dk_cua(cong("entry", "Còn chỗ"))
kiem("H1", "ĐÚNG MỘT lệnh chờ  (`if(m_has_pending) return false`)",
     g_cho["so_lenh_cho"]["phep"] == "==" and g_cho["so_lenh_cho"]["phai"] == 0)
kiem("H2", "số vị thế < Max_Positions  (`if(pos_count >= max) skip`) — dùng \"<\"",
     g_cho["so_vi_the"]["phep"] == "<" and TS[g_cho["so_vi_the"]["phai"]] == 3)

# ============================ HÌNH HỌC VÀO LỆNH ============================
print("\n▸ Compress.mq5 — hình học vào lệnh")
mua, ban = hd_cua("entry", "Buy Stop"), hd_cua("entry", "Sell Stop")

kiem("V1", "lệnh CHỜ STOP, neo mép vùng thuận chiều",
     mua["loai"] == "stop" and ban["loai"] == "stop"
     and mua["huong"] == "mua" and ban["huong"] == "ban")
kiem("V2", "buf = Entry_Buffer_ATR × ATR HIỆN TẠI",
     mua["dem"]["tinh"] == "theo_ATR" and TS[mua["dem"]["value"]] == 0.10)
kiem("V3", "R = SL_ATR_Avg × ATR TRUNG BÌNH VÙNG  (hai chữ ATR khác nhau!)",
     mua["sl"]["tinh"] == "theo_ATR_vung" and TS[mua["sl"]["value"]] == 1.5)
kiem("V4", "TP = RR_Ratio × R",
     mua["tp"]["tinh"] == "theo_R" and TS[mua["tp"]["value"]] == 2.0)
kiem("V5", "hai chiều dùng CÙNG một bộ số",
     (mua["dem"], mua["sl"], mua["tp"], mua["lot"])
     == (ban["dem"], ban["sl"], ban["tp"], ban["lot"]))
kiem("V6", "lot cố định (Fixed_Lot), không sizing theo rủi ro",
     TS[mua["lot"]] == 0.01)

# ============================ QUẢN LÝ LỆNH ============================
print("\n▸ TradeManager — quản lý lệnh")
g_be = dk_cua(cong("manage", "1R"))
kiem("M1", "ManageBreakEven chỉ chạm vị thế ĐÃ KHỚP",
     g_be["lenh_da_khop"].get("dao") is not True)
kiem("M2", "`if(sl >= entry && sl > 0) continue` — SL chưa ở hoà vốn",
     g_be["lenh_sl_hoa_von"].get("dao") is True)
kiem("M3", "kích hoạt khi lãi ≥ BE_RR_Trigger × R",
     g_be["lenh_lai_R"]["phep"] == ">=" and TS[g_be["lenh_lai_R"]["phai"]] == 1.0)
kiem("M4", "dời SL về ĐÚNG giá vào, không tham số nào khác",
     "khoang" not in hd_cua("manage", "Dời SL"))

g_huy = dk_cua(cong("manage", "nén đã tan"))
kiem("M5", "huỷ lệnh chờ khi nén tan, và CHỈ khi chưa khớp",
     g_huy["lenh_da_khop"].get("dao") is True
     and g_huy["atr_bps"]["phep"] == ">=")
kiem("M6", "huỷ dùng CÙNG ngưỡng với lúc vào — một tham số, hai nơi hỏi",
     g_huy["atr_bps"]["phai"] == "nguong_nen_bps"
     and dk_cua(g_nen)["atr_bps"]["phai"] == "nguong_nen_bps")
kiem("M7", "D_02 KHÔNG bao giờ tự đóng vị thế — không khối đóng nào",
     not any(s.get("che_do") in ("dong_han", "dong_mot_phan")
             for s in doc["manage"]["steps"]))
kiem("M8", "không trailing, không đóng một phần",
     not any(s.get("che_do") == "trailing" for s in doc["manage"]["steps"]))

# ============================ HỢP ĐỒNG CHUẨN HOÁ ============================
print("\n▸ Parameters.mqh — hợp đồng chuẩn hoá")
kiem("P1", "mọi tham số có đơn vị bất biến, không pip/đô",
     all(t["don_vi"] for t in doc["tham_so"])
     and not any(x in " ".join(t["don_vi"] for t in doc["tham_so"]).lower()
                 for x in ("pip", "point", "đô")))
kiem("P2", "đủ 11 núm của D_02", len(doc["tham_so"]) == 11)
kiem("P3", "mọi khoảng cách giá là bội ATR / R, không giá tuyệt đối",
     all((s.get(k) or {}).get("tinh") in ("theo_ATR", "theo_ATR_vung", "theo_R")
         for s in doc["entry"]["steps"] for k in ("dem", "sl", "tp")
         if isinstance(s.get(k), dict)))

# ============================ RANH GIỚI ============================
print("\n▸ Ranh giới Entry / Manage")
kiem("R1", "Entry chỉ TẠO lệnh",
     not any(s.get("type") == core.SUA_LENH for s in doc["entry"]["steps"]))
kiem("R2", "Manage chỉ SỬA lệnh",
     not any(s.get("type") == core.VAO_LENH for s in doc["manage"]["steps"]))
kiem("R3", "sơ đồ mẫu SẠCH — không lỗi, không cảnh báo",
     not a.validate(doc)["value"])

# ============================ CỐ Ý KHÁC ============================
KHAC = [
    ("Đọc \"lệnh chờ đã khớp\"",
     "`HasOpenPosition()` — có vị thế NÀO BẤT KỲ không",
     "hỏi thẳng `lệnh này đã khớp` theo id",
     "Bản gốc đọc NHẦM khi lệnh chờ bị huỷ từ ngoài trong lúc còn vị thế cũ. "
     "Ta có id nên không phải đoán. CỐ Ý SỬA."),
    ("Đóng băng vùng khi có lệnh chờ",
     "`if(cur != COMP_PENDING)` mới cập nhật H/L",
     "lệnh mang `vung_id`, tự nhớ vùng của nó",
     "Không cần đóng băng nữa — snapshot đi theo lệnh."),
    ("Kiểm lại bề rộng vùng",
     "CHỈ kiểm lúc COUNTING→CONFIRMED, sau đó thôi",
     "kiểm LẠI mỗi nến ở cổng vào lệnh",
     "Bản gốc: bị Max_Positions chặn thì vùng cứ nới rộng mà vẫn CONFIRMED, "
     "entry trôi ra xa. Ta chặt hơn. KHÁC HÀNH VI — cân nhắc nếu muốn khớp 100 %."),
    ("Máy trạng thái 5 giá trị",
     "`ENUM_COMPRESSION_STATE`",
     "vị trí con trỏ trên sơ đồ + `so_lenh_cho` + `vung_da_sinh_lenh`",
     "MQL5 phải tự nhớ vì mỗi tick chạy lại từ đầu. Ta có đồ thị."),
    ("Khớp lệnh",
     "`deviation=30`, `ORDER_FILLING_FOK`, `ORDER_TIME_GTC`",
     "chưa mô hình hoá",
     "Chuyện khớp lệnh của sàn, không phải luật chiến lược. Để Strategy Tester lo."),
    ("Magic number",
     "`InpMagic_Number` lọc lệnh của chính EA",
     "id của ta",
     "Sổ lệnh là của riêng app, không lẫn với ai."),
    ("CalcLot(entry, sl)",
     "khai hai tham số nhưng BỎ QUA cả hai, luôn trả Fixed_Lot",
     "chỉ có `lot` cố định, không hứa hẹn gì thêm",
     "Không chép cái chữ ký nói dối."),
]

print(f"\n{'─' * 78}\n  BẢY CHỖ CỐ Ý KHÁC BẢN GỐC — không phải lỗi\n{'─' * 78}")
for i, (viec, goc, ta, vi_sao) in enumerate(KHAC, 1):
    print(f"\n  {i}. {viec}")
    print(f"     D_02  : {goc}")
    print(f"     ta    : {ta}")
    print(f"     vì sao: {vi_sao}")

print(f"\n{'=' * 78}\n  {dung} luật khớp, {sai} luật RƠI  ·  {len(KHAC)} chỗ cố ý khác"
      f"\n{'=' * 78}")
sys.exit(1 if sai else 0)
