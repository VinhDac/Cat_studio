"""CẮT TỈA — bỏ một nhánh, chạy lại, so. Phép ĐỐI CHỨNG của máy tìm.

    core.md §18.5c

⭐ **Vì sao phải là đối chứng, không phải thống kê.** Đã thử đo giá trị của một mảnh bằng
cách gom trung bình qua hàng trăm sơ đồ (`kinh_nghiem`): **chết**. Hai hạt giống cho tương
quan hạng **−0,17**, cùng dấu 42/90 — tung đồng xu. Vì 143 sơ đồ ấy khác nhau ở *mọi thứ
khác*, nên tác dụng của một mảnh chìm nghỉm trong nhiễu.

Ở đây thì hai sơ đồ khác nhau **đúng một chỗ**:

```
sơ đồ D            → điểm  −0,1038
sơ đồ D BỎ nhánh X → điểm  −0,0402
                     ───────────────
                     nhánh X đóng góp  −0,0636   ← trong bối cảnh D
```

Nhiễu bị triệt tiêu **ngay trong cặp**, trước khi ai kịp lấy trung bình. Một lượt chạy
thêm cho một câu trả lời sạch, thay vì 500 lượt cho một con số nhiễu.

⚠ **Con số này đúng TRONG BỐI CẢNH D, không phải một chân lý về nhánh X.** Cùng nhánh ấy
đặt vào sơ đồ khác có thể cho dấu ngược. Gom nhiều cặp từ nhiều sơ đồ mới thành thứ nói
được về nhánh X nói chung — đó là tầng 3, không phải chỗ này.

⚠ **Và nó vẫn dính may rủi của ĐOẠN THỜI GIAN.** Nhánh BÁN lỗ trong một quý vàng lên
18,9% là chuyện đương nhiên, không phải bằng chứng nhánh BÁN dở. Muốn tách may khỏi thật
thì chấm trên nhiều cửa sổ (`cham_diem.cham_cuon`), và đó là việc của người gọi.
"""
from . import bo_chay, cham_diem, core, phan_bo


def bo_nhanh(doc, khoi):
    """Bỏ `khoi` và mọi thứ CHỈ tới được qua nó → tài liệu mới, hoặc `None`.

    ⭐ Bỏ theo NHÁNH chứ không theo từng khối, và đó là chủ ý. Gỡ một khối giữa dòng rồi
    nối cha vào con là một phép *đoán*: cổng ấy có thể đang rẽ hai đường, nối vào đường
    nào cũng là ta tự chọn hộ. Cắt cả nhánh thì không phải đoán gì — thứ biến mất đúng
    bằng thứ chỉ tới được qua nó.

    Khối nào vẫn tới được bằng đường khác thì Ở LẠI: phép dò tìm lại từ khối Bắt đầu sau
    khi đã cắt cạnh, nên chuyện đó tự đúng, không cần xét riêng.

    Trả `None` nếu kết quả không hợp lệ (§17) — ví dụ cắt xong còn một cổng cụt đuôi."""
    tab = _tab_cua(doc, khoi)
    if tab is None:
        return None
    so = doc[tab]
    bd = next((s for s in so["steps"] if core.is_start_step(s)), None)
    if bd is None or bd["id"] == khoi:
        return None

    canh = [e for e in so["edges"] if e["to"] != khoi]
    song = _toi_duoc(bd["id"], canh)
    if khoi in song:
        # Vẫn tới được bằng đường khác → cắt một cạnh không bỏ được nó. Nói `None` chứ
        # đừng trả về một tài liệu y hệt: người gọi sẽ tưởng đã thử mà thật ra chưa.
        return None

    moi = dict(doc)
    moi[tab] = {
        **so,
        "steps": [s for s in so["steps"] if s["id"] in song],
        "edges": [e for e in canh if e["from"] in song and e["to"] in song],
    }
    try:
        moi = core.normalize_process(moi)
    except Exception:                             # noqa: BLE001 — sơ đồ cụt là chuyện thường
        return None
    if any(p.get("severity") == "error" for p in core.validate_process(moi)):
        return None
    return moi


def _tab_cua(doc, khoi):
    for t in core.TABS:
        if any(s["id"] == khoi for s in doc[t]["steps"]):
            return t
    return None


def _toi_duoc(goc, canh):
    """Tập khối còn tới được từ `goc` — dò rộng, không đệ quy (sơ đồ có thể có vòng)."""
    ke = {}
    for e in canh:
        ke.setdefault(e["from"], []).append(e["to"])
    song, cho = {goc}, [goc]
    while cho:
        for x in ke.get(cho.pop(), ()):
            if x not in song:
                song.add(x)
                cho.append(x)
    return song


def ung_vien(pb):
    """Từ bảng phân bổ (§18.5b) → những chỗ ĐÁNG THỬ CẮT, đáng ngờ nhất trước.

    Xếp theo *mức đáng ngờ*, không theo *chắc chắn sai*: đây là danh sách việc cần đo,
    còn kết luận thì để phép cắt-rồi-so trả lời."""
    ra = []
    for x in pb["tien"]:
        if x["den"] and x["tien"] < 0:
            ra.append({"khoi": x["khoi"], "nhan": x["nhan"],
                       "vi_sao": f"lỗ {x['tien']:+,.2f} $ / {x['tong_R']:+.2f} R"
                                 .replace(",", "."),
                       "hang": -x["tien"]})
    for x in pb["cong"]:
        if x["luon_khop"]:
            ra.append({"khoi": x["khoi"], "nhan": x["nhan"],
                       "vi_sao": f"luôn khớp {x['khop']}/{x['xet']} — có thể thừa",
                       "hang": 0.0})
        elif x["luon_chan"]:
            ra.append({"khoi": x["khoi"], "nhan": x["nhan"],
                       "vi_sao": f"luôn chặn 0/{x['xet']} — mọi khối dưới là trang trí",
                       "hang": 1e18})
    return sorted(ra, key=lambda x: -x["hang"])


#: Mổ tối đa ngần này nhát cho MỘT sơ đồ. Chốt chặn thời gian: mỗi nhát tốn `1 + số ứng
#: viên` lượt chạy, mà một sơ đồ bệnh có thể đẻ ra rất nhiều ứng viên.
TRAN_NHAT_CAT = 4


def mo_sach(doc, nen, cd, moc, cua=None, buoc="quy", tran_nhat=TRAN_NHAT_CAT,
            cham_lo=None):
    """Cắt hết những nhánh mà bỏ đi thì tốt hơn ở ĐA SỐ cửa sổ. Trả `(sơ đồ, [biên bản])`.

    ⚠ **Luật đa số, không phải điểm gộp** — xem docstring đầu file cho con số đã dạy điều
    đó. Mỗi quyết định (giữ hay bỏ nhát cắt) đều ghi lại thành một dòng biên bản: người
    đọc phải soi lại được MÁY ĐÃ CẮT GÌ VÀ VÌ SAO, chứ không chỉ thấy kết quả cuối.

    `cham_lo(docs)` — chấm một lô SONG SONG, trả đúng thứ tự đưa vào. Bắt buộc phải
    truyền vào nếu muốn nhanh: mấy ứng viên trong cùng một nhát cắt hoàn toàn độc lập.

    ⚠ Đã mắc: bản đầu chạy `bo_chay.chay` thẳng ở đây, tức MỘT nhân, trong khi bể mười
    tiến trình ngồi không đợi lô sau. Mà mổ là phần ĐẮT NHẤT của cả vòng lặp — một lượt
    thử 5 vòng chạy quá 22 phút chỉ vì chỗ này."""
    from . import bo_chay, cham_diem, song_song
    bb = []
    for _ in range(tran_nhat):
        try:
            kq = bo_chay.chay(doc, nen, cd, ghi_nhat_ky=False, dem_khoi=True)
        except bo_chay.LoiChay:
            break
        cs0 = [w["diem"] for w in cham_diem.cham_cuon(kq, *moc, buoc, cua)]
        if not cs0:
            break
        uvs, docs = [], []
        for uv in ung_vien(phan_bo.theo_khoi(kq, cd)):
            moi = bo_nhanh(doc, uv["khoi"])
            if moi is not None:
                uvs.append(uv)
                docs.append(moi)
        if not docs:
            break
        kets = (cham_lo(docs) if cham_lo else
                [song_song.cham_mot(d, nen, cd, cua, moc, buoc) for d in docs])
        tot_nhat = None
        for uv, moi, ket in zip(uvs, docs, kets):
            cs1 = ket.get("cua_so") if ket["loai"] == "cham" else None
            if not cs1 or len(cs1) != len(cs0):
                continue
            tot = sum(1 for a, b in zip(cs0, cs1) if b > a)
            giu = tot * 2 > len(cs0)              # ⭐ ĐA SỐ
            bb.append({"cat": uv["nhan"], "vi_sao": uv["vi_sao"],
                       "tot_hon": tot, "so_cua_so": len(cs0), "giu": giu})
            if giu and (tot_nhat is None or tot > tot_nhat[0]):
                tot_nhat = (tot, moi)
        if tot_nhat is None:
            break                                 # hết cắt được
        doc = tot_nhat[1]
    return doc, bb


def thu(doc, nen, cd, cua=None, ds=None, tien_do=None):
    """Cắt từng ứng viên, chạy lại, so với bản gốc.

    Trả `(goc, [{khoi, nhan, vi_sao, diem, chenh, …}])`. `chenh > 0` nghĩa là **bỏ nhánh
    ấy đi thì TỐT HƠN** — tức nhánh ấy đang làm hại.

    ⚠ Mỗi ứng viên tốn ĐÚNG một lượt chạy. Đó là cái giá của một câu trả lời sạch, và nó
    rẻ hơn hẳn 500 lượt cho một câu trả lời nhiễu."""
    kq0 = bo_chay.chay(doc, nen, cd, ghi_nhat_ky=False, dem_khoi=True)
    d0 = cham_diem.cham(kq0, cua)
    pb = phan_bo.theo_khoi(kq0, cd)
    goc = {"diem": d0["diem"], "so_lenh": d0["so_lenh"], "dat": d0["dat"],
           "lai_pt": d0["lai_pt"], "phan_bo": pb}

    ra = []
    for k, uv in enumerate(ds if ds is not None else ung_vien(pb)):
        moi = bo_nhanh(doc, uv["khoi"])
        if moi is None:
            ra.append({**uv, "bo_duoc": False,
                       "chu": "cắt xong sơ đồ không hợp lệ — không thử được"})
            continue
        try:
            kq = bo_chay.chay(moi, nen, cd, ghi_nhat_ky=False)
        except bo_chay.LoiChay as e:
            ra.append({**uv, "bo_duoc": False, "chu": f"{e}"[:120]})
            continue
        d = cham_diem.cham(kq, cua)
        ra.append({**uv, "bo_duoc": True, "doc": moi,
                   "diem": d["diem"], "chenh": round(d["diem"] - d0["diem"], 4),
                   "so_lenh": d["so_lenh"], "lai_pt": d["lai_pt"], "dat": d["dat"],
                   # ⚠ Cắt xong mà KHÔNG CÒN LỆNH NÀO thì con số "chênh" vô nghĩa —
                   # ta không so hai chiến lược nữa, ta so một chiến lược với việc
                   # đứng ngoài thị trường. Phải nói ra chứ không để nó lẫn vào bảng.
                   "con_lenh": bool(d["so_lenh"])})
        if tien_do:
            tien_do(k + 1, uv)
    return goc, sorted(ra, key=lambda x: -(x.get("chenh") or -9e9))
