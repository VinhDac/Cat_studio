"""PHÂN BỔ — một lượt chạy trả về bao nhiêu con số, thay vì đúng một.

    core.md §18.5b

⭐ **Đây là chỗ phá bế tắc lớn nhất của §18.5.** Một sơ đồ là ~40 nước đi và nhận đúng
MỘT con số ở cuối, nên không cách nào biết nước nào hay. Phân bổ đổi chuyện đó: cùng một
lượt chạy, nhưng hỏi **tiền đi ra từ khối nào** và **cổng nào chặn cái gì**.

⚠ **Đây là KẾ TOÁN, không phải thống kê — và đó là cả điểm của nó.** Phép đo trước
(`kinh_nghiem`, lợi thế theo thẻ) hỏi *"trung bình các sơ đồ CÓ thẻ này thì sao"*, và đo
được là **nhiễu**: hai hạt giống cho tương quan hạng **−0,17**, cùng dấu 42/90 — tung
đồng xu. Vì 143 sơ đồ ấy khác nhau ở mọi thứ khác.

Ở đây thì khác hẳn: `Lenh.khoi` là id ĐÚNG cái khối đã đẻ ra lệnh ấy. Đồng tiền đó đi ra
từ đúng khối đó — không phải tương quan, là cộng trừ.

⚠ `Lenh.khoi` là trường THÊM VÀO cho việc này. Đừng nhầm với `Lenh.sinh_tai` — cái đó là
CHỈ SỐ NẾN, dù chú thích cũ của nó ghi là "id khối". Đã tin nhầm một lần: bảng tiền ra
rỗng trơn trong khi sổ có 113 lệnh.

⚠ **"Chắc chắn bỏ được" là một câu MẠNH, nên chỗ này rất dè dặt.** Bỏ một khối chỉ chắc
chắn không đổi gì khi khối ấy **CHƯA BAO GIỜ ĐƯỢC ĐẾN**. Hai cái bẫy đã suýt mắc:

* **Cổng luôn khớp KHÔNG hiển nhiên bỏ được.** Cổng zone nuôi vùng nén như một hiệu ứng
  phụ (`_nuoi_zone`, `ctx.zone_da_xet`) kể cả khi nó khớp — gỡ nó ra là zone chết khác
  đi, tức ĐỔI KẾT QUẢ.
* **Khối Vào lệnh đẻ 0 lệnh KHÔNG hiển nhiên bỏ được.** Chỉ cần dòng chảy ĐẾN nó là
  `cham_thi_truong` bật, và luật lùi (§12.5a) cấm thử nhánh khác từ đó trở đi. Không
  đẻ lệnh vẫn đổi đường đi.

Nên `chac_bo_duoc` chỉ gồm khối **đến 0 lần**. Mọi thứ khác chỉ là **nghi can** — muốn
biết thì phải cắt rồi chạy lại mà so (tầng 2), không được suy.
"""
from collections import defaultdict

from . import bo_chay, core

#: Khối nào là cổng rẽ nhánh thì đọc bằng `core.is_branch_gate`; còn đây là mấy loại
#: khối "làm việc" mà phân bổ tiền có nghĩa.
_LOAI_TIEN = (core.VAO_LENH,)


def theo_khoi(kq, cd=None):
    """Bảng phân bổ của MỘT lượt chạy.

    Cần `kq` chạy với `dem_khoi=True` thì phần CỔNG mới có; phần TIỀN thì luôn có, vì
    nó đọc thẳng sổ lệnh.

    Trả `{"tien": [...], "cong": [...], "chac_bo_duoc": [...], "co_dem": bool}`."""
    cd = cd or kq.cd
    dem = kq.dem_khoi or {}
    doc = kq.doc
    theo_id, tab_cua = {}, {}
    for t in core.TABS:
        for st in doc[t]["steps"]:
            theo_id[st["id"]] = st
            tab_cua[st["id"]] = t

    # ---- TIỀN theo từng khối Vào lệnh — đọc thẳng sổ lệnh, không tốn gì ----
    goc = defaultdict(lambda: {"so_lenh": 0, "da_dong": 0, "tien": 0.0,
                               "thang": 0, "thua": 0, "tong_R": 0.0})
    dong = set(id(l) for l in bo_chay.lenh_da_dong(kq.so))
    for l in kq.so.lenh:
        o = goc[l.khoi]
        o["so_lenh"] += 1
        if id(l) in dong:
            tien = bo_chay.lai_lenh(l, cd)
            o["da_dong"] += 1
            o["tien"] += tien
            o["thang" if tien > 0 else "thua"] += 1
            if l.R:
                o["tong_R"] += (tien + cd.commission * l.lot) / (
                    l.R * l.lot * cd.contract_size)

    tien = []
    for st in _khoi(doc, lambda x: x.get("type") in _LOAI_TIEN):
        o = goc.get(st["id"])
        d = dem.get(st["id"], [0, 0, 0])
        tien.append({
            "khoi": st["id"], "tab": tab_cua[st["id"]],
            "nhan": st.get("name") or core.action_display(st),
            "den": d[0],
            "so_lenh": o["so_lenh"] if o else 0,
            "da_dong": o["da_dong"] if o else 0,
            "tien": round(o["tien"], 2) if o else 0.0,
            "thang": o["thang"] if o else 0,
            "thua": o["thua"] if o else 0,
            "tong_R": round(o["tong_R"], 2) if o else 0.0,
        })
    tien.sort(key=lambda x: x["tien"])

    # ---- CỔNG: xét bao nhiêu lượt, khớp bao nhiêu ----
    cong = []
    for st in _khoi(doc, core.is_branch_gate):
        d = dem.get(st["id"], [0, 0, 0])
        xet, khop = d[1], d[2]
        cong.append({
            "khoi": st["id"], "tab": tab_cua[st["id"]],
            "nhan": st.get("name") or core.action_display(st),
            "xet": xet, "khop": khop,
            "ty_le": round(khop / xet, 4) if xet else None,
            "zone": bool(st.get("cong_zone")),
            # Hai đầu mút — chỗ đáng nhìn nhất, nhưng chỉ là NGHI CAN (xem docstring).
            "luon_khop": bool(xet and khop == xet),
            "luon_chan": bool(xet and khop == 0),
        })
    cong.sort(key=lambda x: (x["ty_le"] is not None, x["ty_le"] or 0))

    # ---- CHẮC CHẮN bỏ được: CHƯA BAO GIỜ ĐƯỢC ĐẾN ----
    chac = []
    if kq.dem_khoi is not None:
        for st in _khoi(doc, lambda x: not core.is_start_step(x)):
            if dem.get(st["id"], [0, 0, 0])[0] == 0:
                chac.append({"khoi": st["id"], "tab": tab_cua[st["id"]],
                             "nhan": st.get("name") or core.action_display(st),
                             "vi_sao": "dòng chảy chưa bao giờ tới khối này"})

    return {"co_dem": kq.dem_khoi is not None,
            "tien": tien, "cong": cong, "chac_bo_duoc": chac}


def _khoi(doc, loc):
    for t in core.TABS:
        for st in doc[t]["steps"]:
            if loc(st):
                yield st
