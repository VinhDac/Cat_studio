"""CHẤM SONG SONG — nhiều nhân phải ra ĐÚNG kết quả một nhân.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
§18.5 chốt một ràng buộc cứng: *cùng hạt giống + cùng dữ liệu = cùng kết quả, luôn
luôn*. Không có nó thì câu "cách tìm A hơn B" là câu không kiểm được — hai lượt chạy
khác nhau thì so cái gì.

Song song là chỗ dễ đánh mất tính ấy nhất, và **đánh mất một cách LẶNG LẼ**: bể tiến
trình trả kết quả theo thứ tự nào xong trước, nên chỉ cần gộp vào bảng theo thứ tự trả
về là bảng xếp hạng đổi theo tốc độ từng nhân — chạy hai lần ra hai kết quả, mà cả hai
đều "trông đúng". Bài này canh đúng chuyện đó.

Ba điều:

  1. **8 nhân = 1 nhân**, từng con số một: bảng đầu bảng, chuỗi nước đi, thống kê.
  2. **Bốc ở tiến trình CHA**, nên `mot_so_do` vẫn đi đúng một đường với cùng hạt.
  3. **Mở bể hỏng thì LÙI về một nhân**, không nổ — bản đóng gói hoặc máy chặn tiến
     trình con là chuyện có thật, và khi đó cần một lượt chạy chậm chứ không cần lỗi.

⚠ MỌI THỨ nằm trong `main()` và có chốt `if __name__ == "__main__"`. Bắt buộc: `spawn`
nạp lại module chính trong từng tiến trình con, nên một file test chạy ở mức module sẽ
tự chạy lại chính nó trong mỗi con — một quả bom phân hạch, không phải một bài kiểm.

Chạy:  python tests\\test_song_song.py
"""
import io
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import song_song  # noqa: E402
from cat_studio import tim_kiem as tk  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


def nen_thu():
    """Ba tuần nến M1 tổng hợp — đủ dài để có tuần, đủ ngắn để bài kiểm chạy nhanh."""
    n = 7 * 24 * 60 * 3
    gia = [100.0 + 4.0 * math.sin(k / 800.0) + 1.2 * math.sin(k / 70.0)
           for k in range(n)]
    a = np.zeros(n, dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"), ("l", "f8"),
                           ("c", "f8"), ("vol", "f8")])
    for k, x in enumerate(gia):
        a[k] = (1_700_000_000 + k * 60, x, x + 0.4, x - 0.4, x, 1.0)
    return a


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nen = nen_thu()
    cd = bc.CaiDat(point=1.0, contract_size=1.0, digits=2, spread_diem=0.2,
                   commission=0.5, deposit=10_000.0, lot_min=0.01, lot_buoc=0.01,
                   lot_max=50.0)
    N, HAT = 24, 2026

    print("\n▸ Số nhân — tự chọn thì phải chừa lại cho giao diện")
    co = os.cpu_count() or 1
    kiem("`0` = tự chọn, chừa 2 nhân",
         song_song.so_nhan_hop_ly(0) == max(1, co - 2),
         f"— máy có {co} nhân → dùng {song_song.so_nhan_hop_ly(0)}")
    kiem("xin nhiều hơn số nhân thật thì kẹp lại", song_song.so_nhan_hop_ly(999) == co)
    kiem("xin 1 thì đúng 1", song_song.so_nhan_hop_ly(1) == 1)
    kiem("`mo_be(1, …)` trả None — một nhân thì không dựng bể",
         song_song.mo_be(1, nen, cd, None) is None)

    print("\n▸ Chạy MỘT nhân (đối chứng)")
    r1 = tk.tim(nen, cd, N, hat=HAT, so_nhan=1)
    print(f"  chấm {r1.thong_ke['da_chay']} · qua cửa {len(r1.qua)} · "
          f"kẹt {r1.thong_ke['ket']} · trùng {r1.thong_ke['trung_lap']} · "
          f"nã lệnh {r1.thong_ke['na_lenh']}")
    kiem("có chạy được cái nào", r1.thong_ke["da_chay"] > 0)
    kiem("thống kê ghi lại là chạy 1 nhân", r1.thong_ke["so_nhan"] == 1)

    print("\n▸ Chạy 4 NHÂN — phải ra y hệt")
    r4 = tk.tim(nen, cd, N, hat=HAT, so_nhan=4)
    print(f"  chấm {r4.thong_ke['da_chay']} · qua cửa {len(r4.qua)} · "
          f"{r4.thong_ke['so_nhan']} nhân")

    kiem("⭐ CHUỖI NƯỚC ĐI của cả bảng đầu bảng — GIỐNG HỆT",
         [c for _, c, _ in r1.qua] == [c for _, c, _ in r4.qua],
         f"— {len(r1.qua)} sơ đồ")
    kiem("⭐ ĐIỂM từng sơ đồ — giống hệt",
         [d["diem"] for _, _, d in r1.qua] == [d["diem"] for _, _, d in r4.qua])
    kiem("⭐ toàn bộ bảng điểm — giống hệt tới từng khoá",
         [d for _, _, d in r1.qua] == [d for _, _, d in r4.qua])
    # ⚠ KHÔNG so hai tài liệu bằng `==`. `id` của khối sinh ngẫu nhiên (không theo hạt
    # giống), nên hai lần dựng CÙNG một sơ đồ vẫn ra hai tài liệu khác nhau — kể cả khi
    # cùng chạy một nhân. "Tái lập được" nói về CHUỖI NƯỚC ĐI và mấy con số, không nói
    # về từng byte của file. So bằng nhãn từng khối: nó không mang `id`.
    def the(d):
        return [core.action_display(s) for t in core.TABS for s in d[t]["steps"]]

    kiem("sơ đồ đầu bảng dựng ra CÙNG một dãy khối (id thì ngẫu nhiên, kệ nó)",
         (not r1.qua) or the(r1.qua[0][0]) == the(r4.qua[0][0]))

    bo = ("da_chay", "trung_lap", "ket", "no", "khong_lenh", "rot_cua", "na_lenh",
          "qua", "hat", "so_luot", "vi_sao_ngung", "ly_do_rot")
    lech = [k for k in bo if r1.thong_ke.get(k) != r4.thong_ke.get(k)]
    kiem("⭐ THỐNG KÊ — giống hệt (trừ `so_nhan`, đúng ra phải khác)",
         not lech, f"— lệch: {lech}" if lech else "")
    kiem("`so_nhan` có ghi lại và > 1", r4.thong_ke["so_nhan"] > 1,
         f"— {r4.thong_ke['so_nhan']}")
    kiem("lý do rớt cửa cũng giống hệt", r1.rot == r4.rot)

    print("\n▸ Chạy lại 4 nhân lần nữa — vẫn thế")
    r4b = tk.tim(nen, cd, N, hat=HAT, so_nhan=4)
    kiem("⭐ hai lượt 4 nhân giống nhau (không phụ thuộc nhân nào xong trước)",
         [c for _, c, _ in r4.qua] == [c for _, c, _ in r4b.qua]
         and r4.thong_ke["da_chay"] == r4b.thong_ke["da_chay"])

    print("\n▸ Dừng từ ngoài vẫn ăn, kể cả khi đang chạy nhiều nhân")
    dem = [0]

    def dung_ngay():
        dem[0] += 1
        return dem[0] > 5

    r5 = tk.tim(nen, cd, 500, hat=HAT, so_nhan=4, dung=dung_ngay)
    kiem("bấm Dừng thì ngừng bốc thêm, không chạy hết 500",
         r5.thong_ke["da_chay"] < 500,
         f"— chấm {r5.thong_ke['da_chay']}/500 · {r5.thong_ke['vi_sao_ngung']}")

    print(f"\n{'=' * 68}")
    print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
    print("=" * 68)
    return 1 if sai else 0


# ⚠ CHỐT BẮT BUỘC — xem docstring đầu file. Bỏ nó đi là mỗi tiến trình con chạy lại cả
# bài kiểm, và mỗi con lại đẻ ra bốn con nữa.
if __name__ == "__main__":
    sys.exit(main())
