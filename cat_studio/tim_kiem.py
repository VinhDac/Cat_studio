"""DÒ NGẪU NHIÊN — vòng tìm đơn giản nhất, và là ĐỐI CHỨNG.

    core.md §18.5, §18.8

⭐ **Không phải "thuật toán đã chọn".** §18.5 chốt là **chưa chốt** cách tìm, có chủ ý:
dò ngẫu nhiên, tiến hoá và RL là ba cách bới cùng một không gian (`nguoi_bay`), chấm bằng
cùng một thước (`cham_diem`), trên cùng một dữ liệu. Bài này là cái **đối chứng** mà mọi
cách tìm sau phải thắng — không thắng nổi nó thì cách ấy chẳng làm gì cả.

⚠ **BỐC ĐỀU TRONG KHO NƯỚC ĐI KHÔNG PHẢI BỐC ĐỀU GIỮA CÁC LỰA CHỌN.** Kho lệch nặng:
`vao_lenh` một mình chiếm 1.050/1.863 ô (**56 %**), còn `het` đúng **1** ô. Bốc đều từng ô
thì mỗi bước là một lần thử đặt lệnh, và sơ đồ gần như không bao giờ mọc quá hai khối —
tức "ngẫu nhiên" hoá ra là một thiên kiến rất mạnh mà không ai khai.

Nên bốc **HAI TẦNG**: chọn LOẠI nước trước (đều giữa mấy loại đang bật), rồi mới chọn ô
trong loại ấy. Không có núm nào để vặn, và nó là nghĩa "ngẫu nhiên" mà người đọc chờ đợi.

⚠ Một lượt chạy phải **dựng lại được y hệt từ hạt giống**. Không thì so hai lần chạy là
so hai thứ khác nhau, và "cách tìm A hơn B" thành một câu không kiểm được.
"""
import collections
import random
import time

from . import cham_diem, kinh_nghiem, nguoi_bay as nb, song_song

#: Giữ lại bao nhiêu sơ đồ đầu bảng. §18.6.5: lấy NHÓM ĐẦU, không lấy quán quân — cái
#: chung giữa nhiều sơ đồ đáng tin hơn bất kỳ sơ đồ đơn lẻ nào (đo được: quán quân nửa
#: đầu train rơi xuống hạng 13 ở nửa sau).
GIU_DAU_BANG = 20

#: Trần số nước một lượt đi. Không phải luật — chỉ là cái chốt an toàn: mặt nạ đã chừa
#: đường về đích (§18.7.4) nên lượt đi luôn kết thúc được, nhưng một vòng lặp không có
#: trần là một vòng lặp có ngày treo.
TRAN_NUOC = 300


def mot_so_do(rng, tran=None, tat=()):
    """Đi bừa một lượt trong mặt nạ → `(tài_liệu, chuỗi)`, hoặc `(None, chuỗi)` nếu kẹt.

    Kẹt là chuyện KHÔNG NÊN xảy ra — `nguoi_bay` chừa sẵn đường về đích. Trả `None` chứ
    không nổ, nhưng `tim()` đếm nó và in ra: kẹt nhiều là dấu hiệu mặt nạ có lỗ."""
    b = nb.Ban()
    for _ in range(TRAN_NUOC):
        if b.xong:
            return b.tai_lieu(), b.chuoi
        mn = nb.mat_na(b, tran, tat)
        # HAI TẦNG: loại trước, ô sau — xem docstring module.
        theo_loai = {}
        for i, x in enumerate(mn):
            if x:
                theo_loai.setdefault(nb.KHO_NUOC_DI[i][0], []).append(i)
        if not theo_loai:
            return None, b.chuoi
        b.di(rng.choice(theo_loai[rng.choice(sorted(theo_loai))]))
    return None, b.chuoi


class KetQuaTim:
    """Kết quả một lượt tìm. `qua` đã xếp hạng, `rot` giữ lại kèm lý do."""

    __slots__ = ("qua", "rot", "thong_ke", "kinh_nghiem")

    def __init__(self, qua, rot, thong_ke, kn=None):
        self.qua, self.rot, self.thong_ke = qua, rot, thong_ke
        #: Thống kê theo THẺ, gom qua mọi sơ đồ đã chấm (§18.5a). Đây là thứ DUY NHẤT
        #: của một lượt tìm còn dùng được cho lượt sau — bảng xếp hạng thì không.
        self.kinh_nghiem = kn


def tim(nen, cd, so_luot, hat=0, cua=None, tran=None, tat=(), tien_do=None,
        dung=None, giu=GIU_DAU_BANG, han_giay=None, phang_toi_da=None, so_nhan=1):
    """Dò `so_luot` sơ đồ ngẫu nhiên, chấm, giữ `giu` cái đầu bảng.

    `hat`   — hạt giống. Cùng hạt + cùng dữ liệu = cùng kết quả, luôn luôn.
    `cua`   — cửa ưu tiên (§18.6.4), xem `cham_diem.CUA_MAC_DINH`.
    `tran`  — trần độ phức tạp (§15.5), `None` là `nguoi_bay.TRAN`.
    `tat`   — khoá toán hạng KHÔNG dùng lần này (§18.6.1 tầng CHỌN).
    `tien_do(da, tong, qua)` — gọi mỗi lượt, cho cửa sổ RL đọc (§18.6.2). `qua` là
               NHÓM ĐẦU BẢNG hiện tại, đã xếp hạng — một list MỚI mỗi lần, đọc từ luồng
               khác an toàn.
    `dung()` — trả `True` thì ngừng. Máy tìm KHÔNG sống trong cửa sổ, nên phải dừng
               được từ ngoài.
    `han_giay` — chạy quá ngần này giây thì thôi. Chạy qua đêm thì đặt GIỜ hợp lý hơn
               đặt số lượt: chi phí mỗi sơ đồ dao động 3–24 giây (§18.4), nên "10.000
               sơ đồ" không dịch ra được thành mấy tiếng.
    `phang_toi_da` — chấm ngần này lượt liên tiếp mà điểm tốt nhất KHÔNG nhúc nhích thì
               thôi. Đây là bản tự động của thứ `DuongDiem` đang mách bằng mắt:
               *"phẳng 3.000 lượt gần nhất — dừng được rồi"*.
    `so_nhan` — mấy TIẾN TRÌNH chấm song song (§18.4c). `1` = chạy thẳng. Không mở
               được bể thì tự lùi về `1`, không nổ.

    ⭐ **8 nhân cho kết quả Y HỆT 1 nhân.** Sơ đồ vẫn do tiến trình CHA bốc, theo đúng
    thứ tự của một `random.Random(hạt)`; kết quả vẫn gộp vào bảng theo ĐÚNG thứ tự ấy,
    không phải thứ tự trả về. Tiến trình con chỉ chạy-và-chấm đúng một sơ đồ được đưa.
    `tests/test_song_song.py` canh chuyện đó.

    ⚠ KHÔNG giữ `KetQua` của từng lượt: mỗi cái ôm cả sổ lệnh và nhật ký, 10.000 lượt
    là hết sạch bộ nhớ. Chấm xong là vứt, chỉ giữ **tài liệu + bảng điểm** của nhóm đầu
    bảng — tài liệu là JSON, nhẹ."""
    rng = random.Random(hat)
    qua, rot = [], []
    tk = {"da_chay": 0, "trung_lap": 0, "ket": 0, "no": 0, "khong_lenh": 0,
          "rot_cua": 0, "na_lenh": 0, "qua_nang": 0, "hat": hat, "so_luot": so_luot,
          "vi_sao_ngung": "đủ số lượt"}
    da_thay = set()
    t0 = time.perf_counter()
    trang = {"tot_cu": None, "phang": 0}

    kn = kinh_nghiem.KinhNghiem()
    da_boc = [0]

    def thoi():
        """Có lý do nào để THÔI BỐC THÊM không. Ghi luôn lý do vào thống kê."""
        if dung is not None and dung():
            tk["vi_sao_ngung"] = "người dùng dừng"
            return True
        if han_giay and time.perf_counter() - t0 >= han_giay:
            tk["vi_sao_ngung"] = f"hết giờ ({han_giay / 3600:.1f}h)"
            return True
        if phang_toi_da and trang["phang"] >= phang_toi_da:
            tk["vi_sao_ngung"] = (f"phẳng {trang['phang']} lượt liền — "
                                  f"hết tìm được gì mới")
            return True
        return False

    def boc():
        """Sơ đồ TIẾP THEO đáng chấm, hoặc `None` khi thôi.

        Kẹt và trùng đều TIÊU một lượt trong ngân sách `so_luot` — giống hệt bản một
        nhân, vì chúng cũng là công đã bỏ ra."""
        while da_boc[0] < so_luot:
            if thoi():
                return None
            da_boc[0] += 1
            doc, chuoi = mot_so_do(rng, tran, tat)
            if doc is None:
                tk["ket"] += 1
                continue
            khoa = tuple(chuoi)
            if khoa in da_thay:
                # Trùng thì BỎ QUA TRƯỚC khi chạy — một lượt chấm mất hàng giây
                # (§18.4), tiêu cho một sơ đồ đã biết kết quả là tiêu không.
                tk["trung_lap"] += 1
                continue
            da_thay.add(khoa)
            return doc, chuoi
        return None

    def gop(ket, doc, chuoi):
        """Một kết quả vừa về → vào bảng. ⚠ Gọi theo ĐÚNG thứ tự bốc, không phải thứ
        tự trả về — đó là chỗ giữ cho 8 nhân bằng 1 nhân."""
        nonlocal qua
        if ket["loai"] == "na_lenh":
            # ⭐ ĐẾM RIÊNG, không gộp vào `no`. Đây không phải bộ chạy từ chối — nó là
            # ta CHỦ ĐỘNG bỏ dở để lấy lại thời gian (§18.4a). Gộp chung thì con số
            # `no` (thứ báo `nguoi_bay` có lỗ) bị một cái cố ý làm nhiễu.
            tk["na_lenh"] += 1
            return
        if ket["loai"] == "qua_nang":
            # Cũng là ta CHỦ ĐỘNG bỏ dở, nhưng vì lý do KHÁC `na_lenh` — đếm riêng thì
            # bảng "vì sao rớt" nói được sơ đồ máy đang đẻ ra loại rác nào.
            tk["qua_nang"] += 1
            return
        if ket["loai"] == "no":
            # Sơ đồ hợp lệ mà bộ chạy vẫn từ chối là một chỗ `nguoi_bay` chưa biết —
            # đếm và nói ra, đừng nuốt.
            tk["no"] += 1
            tk.setdefault("no_vi", []).append(ket["chu"])
            return
        d = ket["diem"]
        # ⭐ GHI KINH NGHIỆM cho MỌI sơ đồ đã chấm, kể cả cái rớt cửa. Chỉ ghi cái qua
        # cửa là chỉ nhìn người thắng — mà "thẻ này hay đi kèm sơ đồ tệ" cũng là tin,
        # và là loại tin rẻ nhất để có.
        kn.ghi(chuoi, d["diem"], d["dat"])
        tk["da_chay"] += 1
        if not ket["co_lenh"]:
            tk["khong_lenh"] += 1
        if d["dat"]:
            # ⚠ DỰNG LIST MỚI, không `qua.sort()` tại chỗ. CPython làm list RỖNG trong
            # lúc sort — luồng giao diện đọc đúng khoảnh khắc đó sẽ thấy danh sách
            # trống, và bảng đầu bảng nhấp nháy rỗng ngẫu nhiên. Gán một list mới thì
            # người đọc thấy hoặc bản cũ hoặc bản mới, không bao giờ thấy nửa vời.
            qua = sorted(qua + [(doc, chuoi, d)], key=lambda x: -x[2]["diem"])[:giu]
        else:
            tk["rot_cua"] += 1
            rot.append(d["ly_do"])
        # Đếm PHẲNG: bao nhiêu lượt liên tiếp mà điểm tốt nhất không nhúc nhích. Đếm cả
        # lượt rớt cửa — chúng cũng là công đã đốt mà không đổi được gì.
        tot = qua[0][2]["diem"] if qua else None
        trang["phang"] = 0 if tot != trang["tot_cu"] else trang["phang"] + 1
        trang["tot_cu"] = tot
        if tien_do is not None:
            # Mang theo cả NHÓM ĐẦU BẢNG, không chỉ điểm cao nhất: nhờ vậy bàn điều
            # khiển thấy kết quả lớn dần TRONG LÚC chạy, và mở được sơ đồ ngay — thay
            # vì ngồi nhìn một bảng rỗng suốt tám tiếng rồi mới có gì để xem.
            tien_do(tk["da_chay"], so_luot, qua)

    nhan = song_song.so_nhan_hop_ly(so_nhan) if so_nhan and so_nhan != 1 else 1
    be = song_song.mo_be(nhan, nen, cd, cua)
    tk["so_nhan"] = nhan if be else 1
    if be is None:
        # ---- MỘT NHÂN — cũng là bản đối chứng của bản song song ----
        while True:
            x = boc()
            if x is None:
                break
            gop(song_song.cham_mot(x[0], nen, cd, cua), *x)
    else:
        # ---- NHIỀU NHÂN ----
        #
        # ⚠ Tự tay giữ CỬA SỔ công việc thay vì `Pool.imap`. `imap` có một luồng tiếp
        # liệu ăn hết cái iterable ngay lập tức — với `so_luot = 100.000` thì nó bốc
        # sạch 100.000 sơ đồ vào bộ nhớ trước khi cái đầu tiên chấm xong, và mọi phép
        # dừng (người dùng bấm Dừng, hết giờ, phẳng) trở thành vô nghĩa vì đã bốc rồi.
        #
        # ⚠ CỬA SỔ PHẢI RỘNG, và đây là số đo chứ không phải ý thích. Kết quả bắt
        # buộc gộp theo THỨ TỰ BỐC, nên ta chờ ở ĐẦU hàng — mà chi phí mỗi sơ đồ chênh
        # nhau cả chục lần (3–24 s, §18.4). Một con chậm đứng đầu là mấy nhân phía sau
        # chấm xong hết rồi ngồi không. Đo trên nến thật với cửa sổ `2 × nhân`: 4 nhân
        # chỉ nhanh hơn **1,44×** thay vì gần 4×.
        #
        # Rộng thì chỉ tốn bộ nhớ giữ mấy cái tài liệu (vài KB một cái), mà đổi lại
        # nhân nào cũng luôn có việc.
        cua_so = max(4 * nhan, 16)
        try:
            cho = collections.deque()
            while True:
                while len(cho) < cua_so:
                    x = boc()
                    if x is None:
                        break
                    cho.append((x, be.apply_async(song_song.cham_mot, (x[0],))))
                if not cho:
                    break
                x, r = cho.popleft()
                gop(r.get(), *x)
                # ⚠ Dừng thì VỨT phần còn lại, không chờ cho hết. Với cửa sổ rộng, chờ
                # nốt là bấm Dừng xong ngồi đợi cả phút — mà mấy sơ đồ ấy đằng nào cũng
                # nằm ngoài điểm dừng. `finally` bên dưới giết chúng ngay.
                if thoi():
                    break
        finally:
            # `terminate` chứ không `close`: đang dừng giữa chừng thì mấy sơ đồ còn
            # trong bể là công bỏ đi, đợi chúng xong là bấm Dừng mà phải chờ thêm.
            be.terminate()
            be.join()

    tk["qua"] = len(qua)
    # Gộp lý do rớt thành bảng đếm: "8.760 sơ đồ chết" là một con số phải hiện ra, và
    # CHẾT VÌ ĐÂU còn quan trọng hơn (§18.6.3).
    ly_do = {}
    for r in rot:
        k = (r or "").split(" ")[0:3]
        ly_do[" ".join(k)] = ly_do.get(" ".join(k), 0) + 1
    tk["ly_do_rot"] = dict(sorted(ly_do.items(), key=lambda x: -x[1]))
    return KetQuaTim(qua, rot, tk, kn)
