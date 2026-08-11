"""Kho backend · sổ lệnh · cơ sở lưu trữ · bảng tham số.

Bốn thứ này ăn khớp với nhau, nên canh chung một bài:

  kho/       phân loại theo NGUỒN — nền tảng · chỉ báo chuẩn · engine. Trùng khoá là
             lỗi im lặng tệ nhất nên phải chặn ngay lúc import.
  so_lenh.py id của CHÍNH TA, không mượn ticket MT5. Nhờ nó "vùng này đã sinh lệnh"
             là một phép tra bảng chứ không phải cờ ẩn — và cái bug đoán mò
             `HasOpenPosition()` của D_02 không thể tái diễn.
  luu_tru.py mọi đường dẫn ở đúng MỘT chỗ, có di cư từ bố cục cũ.
  tham số    hằng số CÓ TÊN. `nguong_nen_bps` được hỏi ở CẢ HAI sơ đồ; gõ tay hai nơi
             là sửa một chỗ thì hai vế lệch nhau âm thầm.

Chạy:  python tests\\test_kho_va_lenh.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import api  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import kho  # noqa: E402
from cat_studio import luu_tru  # noqa: E402
from cat_studio import so_lenh  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# ================= 1. KHO =================
print("\n▸ Kho backend")
d = kho.danh_muc()
kiem("có ba module: nền tảng · chỉ báo · engine D_02",
     [m["ma_so"] for m in d["module"]] == ["nen_tang", "chi_bao", "d02"],
     f"— {[m['ma_so'] for m in d['module']]}")
kiem("chỉ D_02 được đánh dấu là ENGINE",
     [m["ma_so"] for m in d["module"] if m["la_engine"]] == ["d02"])
kiem("engine D_02 ghi rõ nguồn MQL5",
     "D_02_Compress" in next(m for m in d["module"] if m["ma_so"] == "d02")["nguon"])

nguon = {t["key"]: t["nguon"] for t in kho.TOAN_HANG}
kiem("`close` là NỀN TẢNG — không chiến lược nào sở hữu nó",
     nguon["close"] == "nen_tang")
kiem("`atr` là CHỈ BÁO CHUẨN — D_02 dùng chứ không phát minh",
     nguon["atr"] == "chi_bao")
kiem("`atr_bps` và vùng nén thuộc ENGINE D_02 — ý tưởng riêng của nó",
     nguon["atr_bps"] == "d02" and nguon["so_nen_nen"] == "d02"
     and nguon["vung_da_sinh_lenh"] == "d02")
kiem("`lệnh này` là nền tảng, và chỉ dùng được ở Manage",
     nguon["lenh_da_khop"] == "nen_tang"
     and kho.tabs_cho_phep("lenh_da_khop") == ["manage"])
kiem("bảng trạng thái `vùng nén` do engine D_02 khai",
     [b["key"] for b in d["bang_trang_thai"]] == ["vung_nen"])
kiem("mọi khoá toán hạng là DUY NHẤT giữa các module",
     len(kho.TOAN_HANG_KEYS) == len(set(kho.TOAN_HANG_KEYS)))
print(f"    {len(kho.TOAN_HANG)} toán hạng · {len(kho.CHI_BAO)} chỉ báo · "
      f"{len(kho.BANG_TRANG_THAI)} bảng trạng thái")


# trùng khoá phải nổ ngay
class _GiaEngine:
    MA_SO, TEN, MO_TA = "gia", "Giả", ""
    CHI_BAO = BANG_TRANG_THAI = []
    TOAN_HANG = [{"key": "close", "nhan": "Đụng hàng", "nhom": "Giá", "tham_so": []}]


try:
    kho._soat_trung(kho._gom("TOAN_HANG")
                    + [dict(x, nguon="gia") for x in _GiaEngine.TOAN_HANG], "toán hạng")
    kiem("trùng khoá giữa hai module → nổ ngay lúc import", False, "— không nổ")
except RuntimeError as e:
    kiem("trùng khoá giữa hai module → nổ ngay lúc import", "close" in str(e))

# ================= 2. SỔ LỆNH =================
print("\n▸ Sổ lệnh — id của ta")
so = so_lenh.SoLenh()
v1 = so.mo_vung(nen=10)
for i in range(10):
    v1.them_nen(cao=2410 + i * 0.1, thap=2408, atr=1.2)

kiem("id đếm tăng, đọc log là biết thứ tự", v1.id == "V-0001")
kiem("ATR trung bình vùng ≠ ATR nến mới nhất — hai thứ khác nhau, cố ý",
     abs(v1.atr_tb - 1.2) < 1e-9 and v1.so_nen == 10)
kiem("đỉnh/đáy vùng lấy từ chính các nến nén", v1.dinh > v1.day)
kiem("chưa có lệnh nào → vùng CHƯA sinh lệnh", so.vung_da_sinh_lenh() is False)

R = 1.5 * v1.atr_tb
l1 = so.mo_lenh(v1.id, "s_mua", so_lenh.MUA, "stop", 0.01,
                gia_dat=v1.dinh + 0.1 * v1.atr_hien_tai,
                sl=v1.dinh - R, tp=v1.dinh + 2 * R, R=R, nen=20)
kiem("lệnh mang id riêng và NHỚ vùng đẻ ra nó",
     l1.id == "L-0001" and l1.vung_id == "V-0001")
kiem("backtest không có ticket MT5", l1.ticket is None)
kiem("lệnh chờ chưa khớp", l1.trang_thai == so_lenh.CHO and not l1.da_khop)
kiem("→ \"vùng này đã sinh lệnh\" giờ ĐÚNG — thay cho COMP_CONSUMED",
     so.vung_da_sinh_lenh() is True)
kiem("đếm được: 1 chờ, 0 vị thế",
     so.so_lenh_cho() == 1 and so.so_vi_the() == 0)

so.khop(l1, gia=l1.gia_dat, nen=21)
kiem("khớp rồi: 0 chờ, 1 vị thế",
     so.so_lenh_cho() == 0 and so.so_vi_the() == 1 and l1.da_khop)
kiem("lãi tính theo bội R", abs(l1.lai_R(l1.gia_khop + R) - 1.0) < 1e-9)
kiem("lệnh BÁN thì lãi ngược chiều",
     abs(so_lenh.Lenh("L-x", "V-x", "s", so_lenh.BAN, "market", 0.01,
                      100, 102, 96, 2, 0).lai_R(98) - 1.0) < 1e-9)

kiem("SL chưa ở hoà vốn", l1.sl_o_hoa_von is False)
l1.sl = l1.gia_khop
kiem("dời SL về giá vào → sl_o_hoa_von thành ĐÚNG, suy ra từ vị trí SL chứ không "
     "phải một cờ riêng", l1.sl_o_hoa_von is True)

# đóng rồi vẫn phải nhớ vùng — nếu không, cùng cú nén lại đẻ lệnh lần nữa
so.dong(l1, gia=l1.tp, nen=40, ly_do="tp")
kiem("đóng rồi vẫn tính là vùng ĐÃ sinh lệnh — một cú nén, một lệnh",
     so.vung_da_sinh_lenh() is True)
kiem("lệnh đã đóng không còn trong danh sách Manage phải chạy", not so.dang_song())

so.dong_vung()
v2 = so.mo_vung(nen=60)
kiem("vùng mới có id mới và CHƯA sinh lệnh",
     v2.id == "V-0002" and so.vung_da_sinh_lenh() is False)

l2 = so.mo_lenh(v2.id, "s_ban", so_lenh.BAN, "market", 0.01, 100, 102, 96, 2, 61)
kiem("lệnh market khớp ngay", l2.trang_thai == so_lenh.MO and l2.da_khop)
kiem("hai lệnh sống độc lập — Manage chạy một lượt cho mỗi cái",
     [x.id for x in so.dang_song()] == ["L-0002"])
kiem("chạy lại cùng dữ liệu ra cùng id → so được hai lần backtest",
     [x.id for x in so.lenh] == ["L-0001", "L-0002"])

# ================= 3. LƯU TRỮ =================
print("\n▸ Cơ sở lưu trữ")
kiem("mọi thứ nằm dưới đúng MỘT thư mục gốc",
     os.path.basename(luu_tru.goc()) == "du_lieu")
kiem("chiến lược có thư mục riêng, tên đúng nghĩa",
     os.path.basename(luu_tru.thu_muc_chien_luoc()) == "chien_luoc")
kiem("tên file bị chặn thoát ra ngoài thư mục",
     os.path.dirname(luu_tru.duong_dan_chien_luoc("../../hack"))
     == luu_tru.thu_muc_chien_luoc(),
     f"— {luu_tru.duong_dan_chien_luoc('../../hack')}")
tt = luu_tru.tom_tat()
kiem("tóm tắt kho nói rõ đường dẫn thật", tt["goc"] and len(tt["muc"]) == 3)

# ================= 4. BẢNG THAM SỐ =================
print("\n▸ Bảng tham số")
a = api.Api()
doc = a.demo_process()["value"]
ten_ts = {t["ten"] for t in doc["tham_so"]}
kiem("sơ đồ mẫu mang đủ bộ tham số của D_02", len(doc["tham_so"]) == 11)
kiem("tham số nào cũng có ĐƠN VỊ — hợp đồng chuẩn hoá",
     all(t["don_vi"] for t in doc["tham_so"]))
kiem("không đơn vị nào là pip / điểm / đô",
     not any(x in " ".join(t["don_vi"] for t in doc["tham_so"]).lower()
             for x in ("pip", "point", "điểm", "đô")))

dung_ts = core._tham_so_dang_dung(doc)
kiem("MỌI tham số đều được dùng — không có núm vặn chết",
     ten_ts == dung_ts, f"— thừa: {ten_ts - dung_ts}")

# đây là cái bug bảng tham số sinh ra để chặn
ai_dung_nguong = []
for tab in core.TABS:
    for st in doc[tab]["steps"]:
        for c in st.get("conditions") or []:
            if c.get("phai_loai") == "tham_so" and c["phai"] == "nguong_nen_bps":
                ai_dung_nguong.append(tab)
kiem("`nguong_nen_bps` được hỏi ở CẢ HAI sơ đồ nhưng chỉ khai MỘT lần",
     sorted(ai_dung_nguong) == ["entry", "manage"], f"— {ai_dung_nguong}")


def hang_so_go_tay(d):
    """{giá trị: [nơi dùng]} — chỉ những con số GÕ THẲNG, không qua tham số."""
    ra = {}
    for tab in core.TABS:
        for st in d[tab]["steps"]:
            noi = f"{tab}/{core.step_title(st)}"
            for c in st.get("conditions") or []:
                if c.get("phai_loai") == "so":
                    ra.setdefault(c["phai"], []).append(noi)
            for k in ("dem", "sl", "tp", "khoang"):
                v = (st.get(k) or {}).get("value") if isinstance(st.get(k), dict) else None
                if v is not None and not isinstance(v, str):
                    ra.setdefault(v, []).append(f"{noi}/{k}")
    return ra


lap = {v: n for v, n in hang_so_go_tay(doc).items() if len(n) > 1}
kiem("KHÔNG còn hằng số gõ tay nào lặp lại giữa các khối", not lap, f"— {lap or 'sạch'}")

# tham số không tồn tại → báo lỗi
xau = dict(doc, tham_so=[t for t in doc["tham_so"] if t["ten"] != "nguong_nen_bps"])
kiem("bỏ một tham số đang dùng → báo lỗi, không im lặng chạy sai",
     any("nguong_nen_bps" in p["message"] for p in core.validate_process(xau)))

thua = dict(doc, tham_so=doc["tham_so"] + [
    core.make_tham_so("khong_ai_dung", "Thừa", 1, "nến")])
kiem("khai tham số không ai dùng → cảnh báo",
     any("không khối nào dùng" in p["message"] for p in core.validate_process(thua)))

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
