"""Mô hình khớp lệnh — thứ DUY NHẤT đổi mà đổi cả đường vốn.

Cùng một sơ đồ, hai mô hình khớp khác nhau cho hai đường vốn khác hẳn, và sai ở đây
KHÔNG báo lỗi — chỉ ra một con số đẹp hơn hoặc xấu hơn thực tế. Nên bài này soi từng ca
một, bằng những con số tính tay được.

Năm thứ được canh:

  1. **Đường đi 4 điểm** quyết cái nào tới trước, kể cả khi cả SL lẫn TP đều nằm trong
     biên độ nến.
  2. **Spread quy về Bid** đúng bốn dòng của bảng — lệch một dòng là lãi/lỗ sai có hệ thống.
  3. **Gap**: mở cửa đã qua mức thì khớp ở giá MỞ CỬA, không phải ở mức đặt.
  4. **Khớp rồi chết trong CÙNG một nến** phải ra hai sự kiện đúng thứ tự.
  5. **SL/TP chỉ được xét TỪ lúc khớp trở đi** — không cho một cái SL chưa tồn tại giết
     một vị thế chưa mở.
  6. **Trượt giá LUÔN theo chiều bất lợi** (§16.2) — cả bốn ca vào/ra × mua/bán.

Chạy:  python tests\\test_khop_lenh.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import khop_lenh as kl  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def gan(a, b, e=1e-9):
    return a is not None and abs(float(a) - float(b)) <= e


def nen(o, h, l, c):
    return {"o": o, "h": h, "l": l, "c": c}


def cho(huong, gia_dat, sl=None, tp=None):
    return {"huong": huong, "da_khop": False, "gia_dat": gia_dat, "sl": sl, "tp": tp}


def mo(huong, sl=None, tp=None):
    return {"huong": huong, "da_khop": True, "sl": sl, "tp": tp}


# ================= 1. đường đi =================
print("\n▸ Đường đi 4 điểm")
kiem("nến TĂNG: O → L → H → C (nhúng xuống trước)",
     kl.duong_di(10, 12, 9, 11) == (10, 9, 12, 11))
kiem("nến GIẢM: O → H → L → C (đẩy lên trước)",
     kl.duong_di(10, 12, 9, 8) == (10, 12, 9, 8))
kiem("nến doji (C == O) tính là tăng — một luật, không có ca lửng lơ",
     kl.duong_di(10, 12, 9, 10) == (10, 9, 12, 10))

# ================= 2. lệnh chờ khớp =================
print("\n▸ Lệnh chờ STOP khớp — chưa có spread")
e = kl.trong_nen(cho(kl.MUA, 100), nen(98, 101, 97, 100), 0)
kiem("Buy Stop 100, nến chạm 101 → khớp ĐÚNG 100", len(e) == 1 and gan(e[0]["gia"], 100),
     f"— {e}")
kiem("khớp ở bước 2 (O→L→H), không phải bước 0", e[0]["buoc"] == 2 and not e[0]["gap"])
kiem("nến không chạm tới → KHÔNG khớp",
     kl.trong_nen(cho(kl.MUA, 100), nen(98, 99.5, 97, 99), 0) == [])
e = kl.trong_nen(cho(kl.BAN, 100), nen(102, 103, 99, 100), 0)
kiem("Sell Stop 100, nến thủng 99 → khớp ĐÚNG 100", len(e) == 1 and gan(e[0]["gia"], 100))

print("\n▸ GAP — mở cửa đã nhảy qua mức")
e = kl.trong_nen(cho(kl.MUA, 100), nen(103, 104, 102, 103), 0)
kiem("Buy Stop 100 mà nến mở 103 → khớp ở 103, KHÔNG phải 100",
     gan(e[0]["gia"], 103) and e[0]["gap"] and e[0]["buoc"] == 0, f"— {e[0]}")
e = kl.trong_nen(cho(kl.BAN, 100), nen(97, 98, 96, 97), 0)
kiem("Sell Stop 100 mà nến mở 97 → khớp ở 97 (xấu hơn mức đặt)",
     gan(e[0]["gia"], 97) and e[0]["gap"])

# ================= 3. spread =================
print("\n▸ Spread — quy mọi mức về Bid")
# Mua vào ở Ask: sàn so Ask ≥ 100, tức Bid ≥ 99.8. Nến chạm 99.9 là ĐỦ.
e = kl.trong_nen(cho(kl.MUA, 100), nen(99, 99.9, 98, 99.5), 0.2)
kiem("Buy Stop kích hoạt SỚM hơn theo Bid (Bid ≥ 100 − spread)", len(e) == 1, f"— {e}")
kiem("nhưng GIÁ VÀO SỔ vẫn đúng 100 (giá Ask đã đặt)", gan(e[0]["gia"], 100))
kiem("cùng nến đó mà KHÔNG có spread thì KHÔNG khớp — spread đổi kết quả thật",
     kl.trong_nen(cho(kl.MUA, 100), nen(99, 99.9, 98, 99.5), 0) == [])
# Bán vào ở Bid: spread không dịch ngưỡng vào lệnh.
kiem("Sell Stop vào ở Bid nên spread KHÔNG dịch ngưỡng",
     kl.trong_nen(cho(kl.BAN, 100), nen(101, 102, 100, 100.5), 0.2) != []
     and kl.trong_nen(cho(kl.BAN, 100), nen(101, 102, 100.1, 100.5), 0.2) == [])

print("\n▸ Spread khi ĐÓNG")
# Vị thế Mua đóng ở Bid → SL chạm đúng theo Bid, không dịch.
e = kl.trong_nen(mo(kl.MUA, sl=95, tp=110), nen(100, 101, 95, 96), 0.2)
kiem("vị thế MUA: SL chạm theo Bid, đóng đúng 95",
     e and e[0]["ly_do"] == kl.SL and gan(e[0]["gia"], 95), f"— {e}")
# Vị thế Bán đóng ở Ask → SL 105 chạm khi Ask ≥ 105, tức Bid ≥ 104.8.
e = kl.trong_nen(mo(kl.BAN, sl=105, tp=90), nen(100, 104.9, 99, 104), 0.2)
kiem("vị thế BÁN: SL chạm theo Ask (Bid ≥ SL − spread), đóng đúng 105",
     e and e[0]["ly_do"] == kl.SL and gan(e[0]["gia"], 105), f"— {e}")
kiem("cùng nến đó không spread thì SL CHƯA chạm",
     kl.trong_nen(mo(kl.BAN, sl=105, tp=90), nen(100, 104.9, 99, 104), 0) == [])

# ================= 4. SL hay TP tới trước =================
print("\n▸ Cả SL lẫn TP trong một nến — đường đi quyết")
l = mo(kl.MUA, sl=95, tp=105)
e = kl.trong_nen(l, nen(100, 106, 94, 104), 0)          # nến TĂNG: O→L→H→C
kiem("nến TĂNG chạm cả hai: xuống đáy TRƯỚC → SL thắng",
     e and e[0]["ly_do"] == kl.SL and gan(e[0]["gia"], 95), f"— {e}")
e = kl.trong_nen(l, nen(100, 106, 94, 96), 0)           # nến GIẢM: O→H→L→C
kiem("nến GIẢM chạm cả hai: lên đỉnh TRƯỚC → TP thắng",
     e and e[0]["ly_do"] == kl.TP and gan(e[0]["gia"], 105), f"— {e}")
kiem("và cả hai ca đều được ĐÁNH DẤU mơ hồ, để còn đếm được",
     e[0]["mo_ho"] and kl.ca_hai_trong_nen(l, nen(100, 106, 94, 96), 0))
kiem("nến chỉ chạm một mức → không mơ hồ",
     not kl.trong_nen(l, nen(100, 101, 94, 96), 0)[0]["mo_ho"]
     and not kl.ca_hai_trong_nen(l, nen(100, 101, 94, 96), 0))

print("\n▸ GAP khi đóng")
e = kl.trong_nen(mo(kl.MUA, sl=95, tp=105), nen(90, 91, 89, 90), 0)
kiem("gap thủng SL: đóng ở 90 chứ không phải 95 — XẤU hơn mức đặt",
     e and e[0]["ly_do"] == kl.SL and gan(e[0]["gia"], 90), f"— {e}")
e = kl.trong_nen(mo(kl.MUA, sl=95, tp=105), nen(110, 111, 109, 110), 0)
kiem("gap vượt TP: đóng ở 110 — TỐT hơn mức đặt, đúng như sàn khớp",
     e and e[0]["ly_do"] == kl.TP and gan(e[0]["gia"], 110))

# ================= 5. khớp rồi chết cùng nến =================
print("\n▸ Khớp rồi chết trong CÙNG một nến")
# Nến giảm: O=99 → H=101 (khớp Buy Stop 100) → L=94 (thủng SL 95) → C=95
e = kl.trong_nen(cho(kl.MUA, 100, sl=95, tp=120), nen(99, 101, 94, 95), 0)
kiem("hai sự kiện, đúng thứ tự khớp → đóng", len(e) == 2
     and e[0]["loai"] == "khop" and e[1]["loai"] == "dong", f"— {e}")
kiem("khớp ở 100, rồi SL ở 95", gan(e[0]["gia"], 100) and gan(e[1]["gia"], 95))
kiem("bước của sự kiện đóng phải SAU bước khớp", e[1]["buoc"] > e[0]["buoc"],
     f"— khớp bước {e[0]['buoc']}, đóng bước {e[1]['buoc']}")

# Nến TĂNG: O=99 → L=94 → H=101 → C=100. Đáy 94 tới TRƯỚC khi lệnh khớp ở 100.
e = kl.trong_nen(cho(kl.MUA, 100, sl=95, tp=120), nen(99, 101, 94, 100), 0)
kiem("đáy đi qua TRƯỚC lúc khớp → SL đó KHÔNG được tính (lệnh chưa tồn tại)",
     len(e) == 1 and e[0]["loai"] == "khop", f"— {e}")

# ================= 6. biên =================
print("\n▸ Biên")
kiem("lệnh chờ chưa khớp thì SL/TP không bao giờ được xét",
     kl.trong_nen(cho(kl.MUA, 200, sl=95, tp=105), nen(100, 106, 94, 96), 0) == [])
kiem("vị thế không SL không TP → nến nào cũng không đóng",
     kl.trong_nen(mo(kl.MUA), nen(100, 200, 1, 150), 0) == [])
kiem("chạm ĐÚNG mức (bằng nhau) là chạm, không phải trượt",
     kl.trong_nen(mo(kl.MUA, sl=95), nen(100, 101, 95, 96), 0) != [])
kiem("đọc được cả dict lẫn đối tượng",
     kl.trong_nen(type("L", (), {"huong": "mua", "da_khop": True,
                                 "sl": 95, "tp": None})(),
                  nen(100, 101, 94, 96), 0) != [])

# ======================= 6. TRƯỢT GIÁ — core.md §16.2 =======================
#
# ⚠ LUÔN THEO CHIỀU BẤT LỢI, cả bốn ca. Ngoài đời một lệnh Stop khớp BẰNG HOẶC XẤU HƠN
# giá kích hoạt, không bao giờ tốt hơn: lúc giá phá qua mức là lúc sổ lệnh mỏng nhất.
# Mô hình đối xứng ("khi tốt khi xấu, trung bình 0") nghe công bằng nhưng sai bản chất,
# và nó sai đúng về phía làm backtest ĐẸP LÊN.
print("\n▸ Trượt giá luôn theo chiều bất lợi")

_S, _T = 0.2, 0.05          # spread · trượt, đơn vị giá


def _gia(su_kien):
    return su_kien[0]["gia"] if su_kien else None


# VÀO — Mua vào ở Ask nên trượt đẩy giá LÊN; Bán vào ở Bid nên trượt kéo XUỐNG.
_v_mua = _gia(kl.trong_nen(cho(kl.MUA, 100), nen(100, 101, 99, 100.5), _S, _T))
_v_ban = _gia(kl.trong_nen(cho(kl.BAN, 100), nen(100, 101, 99, 99.5), _S, _T))
kiem("VÀO Mua: trượt đẩy giá khớp LÊN (mua đắt hơn)",
     gan(_v_mua, _gia(kl.trong_nen(cho(kl.MUA, 100), nen(100, 101, 99, 100.5), _S)) + _T),
     f"— {_v_mua}")
kiem("VÀO Bán: trượt kéo giá khớp XUỐNG (bán rẻ hơn)",
     gan(_v_ban, _gia(kl.trong_nen(cho(kl.BAN, 100), nen(100, 101, 99, 99.5), _S)) - _T),
     f"— {_v_ban}")

# RA — vị thế Mua đóng ở Bid nên trượt kéo XUỐNG; vị thế Bán đóng ở Ask nên đẩy LÊN.
_r_mua = kl.trong_nen(mo(kl.MUA, sl=95), nen(100, 101, 94, 96), _S, _T)
_r_ban = kl.trong_nen(mo(kl.BAN, sl=105), nen(100, 106, 99, 104), _S, _T)
kiem("RA Mua (chạm SL): trượt kéo giá đóng XUỐNG (lỗ thêm)",
     gan(_r_mua[0]["gia"],
         kl.trong_nen(mo(kl.MUA, sl=95), nen(100, 101, 94, 96), _S)[0]["gia"] - _T),
     f"— {_r_mua[0]['gia']}")
kiem("RA Bán (chạm SL): trượt đẩy giá đóng LÊN (lỗ thêm)",
     gan(_r_ban[0]["gia"],
         kl.trong_nen(mo(kl.BAN, sl=105), nen(100, 106, 99, 104), _S)[0]["gia"] + _T),
     f"— {_r_ban[0]['gia']}")

# Trượt KHÔNG được đụng NGƯỠNG kích hoạt: sàn nhìn giá thật để quyết lệnh có nổ hay
# không; trượt là chuyện xảy ra SAU đó, lúc đi tìm thanh khoản.
kiem("trượt KHÔNG làm lệnh khớp sớm/muộn hơn — chỉ đổi GIÁ",
     [e["buoc"] for e in kl.trong_nen(cho(kl.MUA, 100), nen(99, 101, 98, 100.5), _S, _T)]
     == [e["buoc"] for e in kl.trong_nen(cho(kl.MUA, 100), nen(99, 101, 98, 100.5), _S)])
kiem("trượt 0 → trùng khít bản không có trượt",
     kl.trong_nen(mo(kl.MUA, sl=95, tp=110), nen(100, 111, 94, 96), _S, 0.0)
     == kl.trong_nen(mo(kl.MUA, sl=95, tp=110), nen(100, 111, 94, 96), _S))

print(f"\n{'=' * 52}\n  {dung} đúng, {sai} sai\n{'=' * 52}")
sys.exit(1 if sai else 0)
