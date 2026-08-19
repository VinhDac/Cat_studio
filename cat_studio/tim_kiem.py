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

from . import cham_diem, nguoi_bay as nb, song_song

#: Giữ lại bao nhiêu sơ đồ đầu bảng. §18.6.5: lấy NHÓM ĐẦU, không lấy quán quân — cái
#: chung giữa nhiều sơ đồ đáng tin hơn bất kỳ sơ đồ đơn lẻ nào (đo được: quán quân nửa
#: đầu train rơi xuống hạng 13 ở nửa sau).
GIU_DAU_BANG = 20

#: Mép thùng của "THIẾU BAO XA" — xem `cham_diem._rot`. Thùng đầu là *suýt qua*.
MEP_THIEU = (0.1, 0.25, 0.5, 0.75)

#: MÉP các thùng của ba phân bố hiện trên bàn điều khiển (§18.9c).
#:
#: ⭐ Ba phân bố này trả lời ba câu mà một con số trung bình KHÔNG trả lời được:
#:
#: * **điểm** — có cái đuôi nào bên phải không, hay cả đám dồn về âm. Đo được: sơ đồ bốc
#:   bừa thua CÓ HỆ THỐNG (~2% dương đều, trong khi tung đồng xu là 65%), nên hình dạng
#:   của đống này là thứ đáng nhìn nhất khi hỏi *"không gian này có gì không"*.
#: * **số lệnh** — cấu trúc của rác. 28/60 sơ đồ không vào lệnh nào; một cái đẻ 11.425.
#: * **chi phí** — vì sao "còn bao lâu" phải là một KHOẢNG: một sơ đồ có thể chiếm 60%
#:   cả lô (§18.4d). Trung bình che mất chuyện đó, phân bố thì không.
#:
#: Thùng của `lệnh` và `giây` chia theo LOGARIT, cố ý: dải thật trải từ 0 tới hàng chục
#: nghìn, chia đều thì mọi thứ dồn vào thùng đầu và đồ thị nói không được gì.
MEP_DIEM = (-0.6, -0.4, -0.25, -0.15, -0.08, -0.03, 0.0, 0.03, 0.08, 0.15, 0.25, 0.4)
MEP_LENH = (1, 10, 50, 200, 1000, 5000)
MEP_GIAY = (0.5, 1, 2, 5, 10, 30)


def _thung(mep, x):
    """Chỉ số thùng của `x` — `0` là dưới mép đầu, `len(mep)` là trên mép cuối."""
    for i, m in enumerate(mep):
        if x < m:
            return i
    return len(mep)


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

    __slots__ = ("qua", "rot", "thong_ke")

    def __init__(self, qua, rot, thong_ke):
        self.qua, self.rot, self.thong_ke = qua, rot, thong_ke


def tim(nen, cd, so_luot, hat=0, cua=None, tran=None, tat=(), tien_do=None,
        dung=None, giu=GIU_DAU_BANG, han_giay=None, phang_toi_da=None, so_nhan=1,
        so_nhan_dung=None):
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
    `so_nhan_dung()` — trả về số nhân MUỐN DÙNG lúc này, hỏi lại mỗi lượt.

    ⭐ Đây là cái van CPU chạy được GIỮA CHỪNG, và nó rẻ vì không đụng tới bể: chỉ cần
    thu hẹp CỬA SỔ CÔNG VIỆC. Ít việc trong bể thì mấy tiến trình dư nằm im, không ăn
    CPU — khỏi dựng lại bể, khỏi mất việc đang dở. Máy tìm chạy hàng giờ ngay trong app
    người dùng đang mở, nên "nhường lại máy" phải làm được ngay, không phải đợi lượt sau.

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
          # ⭐ CHẾT TỪ LÚC VẼ — câm vì một cổng KHÔNG BAO GIỜ khớp, chứ không phải chạy
          # rồi không ăn. Tách khỏi `khong_lenh` vì hai thứ này bảo ta sửa hai chỗ khác
          # nhau: cái này là kho đồ bày ra hằng số thay vì câu hỏi (§18.11), cái kia là
          # lệnh có sinh mà sàn không nhận. Đo được 56,7% số sơ đồ câm nằm ở vế này.
          "chet_tu_dau": 0, "chan_theo_toan_hang": {},
          "rot_cua": 0, "na_lenh": 0, "qua_nang": 0, "hat": hat, "so_luot": so_luot,
          # ⚠ Đếm CỘNG DỒN, khác hẳn `len(qua)` — bảng đầu bảng bị chặn ở `giu` nên nó
          # bão hoà và không còn nói được "còn tìm được gì nữa không".
          "qua_cong_don": 0,
          # Ba phân bố — xem `MEP_DIEM`. Gồm CẢ sơ đồ rớt cửa: hình dạng cả đống mới
          # nói được không gian này có gì, chỉ nhìn người thắng thì không.
          "hist_diem": [0] * (len(MEP_DIEM) + 1),
          "hist_lenh": [0] * (len(MEP_LENH) + 1),
          "hist_giay": [0] * (len(MEP_GIAY) + 1),
          # `{tên cửa: {so, nguong, thieu[5], vi_du[3]}}` — xem `cham_diem._rot`.
          "rot_chi_tiet": {},
          "vi_sao_ngung": "đủ số lượt"}
    da_thay = set()
    t0 = time.perf_counter()
    trang = {"tot_cu": None, "phang": 0}

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
        if ket.get("giay") is not None:
            tk["hist_giay"][_thung(MEP_GIAY, ket["giay"])] += 1
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
        tk["da_chay"] += 1
        tk["hist_diem"][_thung(MEP_DIEM, d["diem"])] += 1
        tk["hist_lenh"][_thung(MEP_LENH, d["so_lenh"])] += 1
        if not ket["co_lenh"]:
            tk["khong_lenh"] += 1
            if ket.get("chan"):
                tk["chet_tu_dau"] += 1
                c = tk["chan_theo_toan_hang"]
                c[ket["chan"]] = c.get(ket["chan"], 0) + 1
        if d["dat"]:
            tk["qua_cong_don"] += 1
            # ⚠ DỰNG LIST MỚI, không `qua.sort()` tại chỗ. CPython làm list RỖNG trong
            # lúc sort — luồng giao diện đọc đúng khoảnh khắc đó sẽ thấy danh sách
            # trống, và bảng đầu bảng nhấp nháy rỗng ngẫu nhiên. Gán một list mới thì
            # người đọc thấy hoặc bản cũ hoặc bản mới, không bao giờ thấy nửa vời.
            qua = sorted(qua + [(doc, chuoi, d)], key=lambda x: -x[2]["diem"])[:giu]
        else:
            tk["rot_cua"] += 1
            rot.append(d["ly_do"])
            # ⭐ Gom theo CỬA, giữ cả MỨC ĐỘ. Bản cũ cắt lấy ba chữ đầu của câu tiếng
            # Việt nên mất sạch con số — bảng chỉ đếm được, không nói được trượt bao xa.
            r = d.get("rot")
            if r:
                o = tk["rot_chi_tiet"].setdefault(
                    r["cua"], {"so": 0, "nguong": r["nguong"],
                               "thieu": [0] * (len(MEP_THIEU) + 1), "vi_du": []})
                o["so"] += 1
                o["thieu"][_thung(MEP_THIEU, r["thieu"])] += 1
                if len(o["vi_du"]) < 3:
                    o["vi_du"].append(d["ly_do"])
        # Đếm PHẲNG: bao nhiêu lượt liên tiếp mà điểm tốt nhất không nhúc nhích. Đếm cả
        # lượt rớt cửa — chúng cũng là công đã đốt mà không đổi được gì.
        tot = qua[0][2]["diem"] if qua else None
        trang["phang"] = 0 if tot != trang["tot_cu"] else trang["phang"] + 1
        trang["tot_cu"] = tot
        if tien_do is not None:
            # Mang theo cả NHÓM ĐẦU BẢNG, không chỉ điểm cao nhất: nhờ vậy bàn điều
            # khiển thấy kết quả lớn dần TRONG LÚC chạy, và mở được sơ đồ ngay — thay
            # vì ngồi nhìn một bảng rỗng suốt tám tiếng rồi mới có gì để xem.
            tien_do(tk["da_chay"], so_luot, qua, tk)

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
        try:
            cho = collections.deque()
            while True:
                # Hỏi LẠI mỗi lượt — đó là chỗ cái van CPU ăn ngay giữa chừng.
                dung_may = nhan
                if so_nhan_dung is not None:
                    try:
                        dung_may = max(1, min(int(so_nhan_dung() or nhan), nhan))
                    except Exception:             # noqa: BLE001
                        dung_may = nhan
                cua_so = max(4 * dung_may, 8)
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
    return KetQuaTim(qua, rot, tk)
