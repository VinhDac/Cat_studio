"""ĐỌC SƠ ĐỒ RA LỜI — một chiến lược hiện ra dưới dạng LOGIC, không dưới dạng hộp.

    core.md §18.5, §18.10

VÌ SAO MODULE NÀY PHẢI CÓ
-------------------------
Cái thước đang ở trạng thái **không đọc được**: đoạn giữ lại trả về `0/8` cho nhóm đầu
bảng và `0/8` cho nhóm bốc bừa. Hai nhóm chết như nhau thì con số ấy không phân biệt
được *"không gian rỗng"* với *"thước hỏng"* — và sửa tiếp theo cảm giác là bắt đầu vòng
luẩn quẩn.

⭐ Nhưng một sơ đồ **là logic**, và logic thì ĐỌC ĐƯỢC BẰNG MẮT — không cần thước, không
cần backtest, không cần cửa. Đọc mà thấy vô nghĩa thì biết ngay người bày đang bịa; đọc
mà thấy có lý thì biết chỗ hỏng nằm ở khâu chấm. Đó là phép đo duy nhất lúc này còn
phân biệt được hai khả năng ấy, nên nó đi trước mọi thứ khác.

Vướng đúng một chỗ: sơ đồ máy vẽ hiện ra là những cái hộp trên canvas, và đọc tám mươi
cái bằng mắt trên canvas thì không ai đọc nổi. Module này bày nó ra thành lời.

HAI THỨ PHẢI PHÂN BIỆT ĐƯỢC NGAY TỪ CÁI NHÌN ĐẦU
------------------------------------------------
Đây là cả lý do bảng chữ dưới đây trông như vậy:

```
LỌC   trượt là THÔI — vùng còn lại co lại, sơ đồ không làm gì cả
CHIA  trượt là SANG VẾ KIA — hai vế phủ kín, luôn có đúng một vế khớp
```

Nối bốn cái LỌC là vứt đi bốn lần, và cái còn lại chính là *"phần lịch sử khớp"* — tức
overfit, không phải chiến lược. Nên khi đọc, thứ cần thấy trước nhất là mỗi cái cổng
đang **vứt** hay đang **chia**.

⚠ Chữ nghĩa lấy từ `core.cond_display` / `core.action_display`, KHÔNG ghép lại ở đây.
Ghép bản thứ hai là sớm muộn mô tả một đằng, lõi hiểu một nẻo — đúng cái bẫy `_kem_the`
đã ghi lại một lần.
"""
from . import core, nguoi_bay


def _do_thi(g):
    """`(khối theo id, con của mỗi khối, id khối Bắt đầu)`."""
    st = {s["id"]: s for s in (g.get("steps") or [])}
    con = {}
    for e in (g.get("edges") or []):
        con.setdefault(e["from"], []).append(e["to"])
    bd = next((s["id"] for s in (g.get("steps") or []) if core.is_start_step(s)), None)
    return st, con, bd


def _thu_tu(st, ke):
    """Thứ tự bộ chạy THỬ các nhánh — theo toạ độ, y như `_chay_so_do`.

    Không phải chuyện thẩm mỹ: đọc sai thứ tự là đọc một chiến lược khác."""
    return sorted(ke, key=lambda i: core._khoa_nhanh(st[i]))


def _hanh_dong(s, ts):
    return core.action_display(s, ts)


def _dieu_kien(s, ts):
    """Một cổng → một dòng. Nhiều điều kiện thì nối bằng VÀ, đúng nghĩa của cổng."""
    ds = s.get("conditions") or []
    ra = " VÀ ".join(core.cond_display(c, ts) for c in ds) or "(không điều kiện — LUÔN khớp)"
    hl = s.get("dk_hop_le") or []
    if hl:
        ra += "   [hợp lệ khi: " + " VÀ ".join(
            core.cond_display(c, ts) for c in hl) + "]"
    if s.get("cong_zone"):
        ra = "⟨zone⟩ " + ra
    return ra


def _nhanh(st, con, sid, ts, sau, ra):
    """Viết ra mọi thứ NẰM DƯỚI `sid`. `sid` tự nó đã được viết bởi bên gọi."""
    tab = "  " * sau
    ke = _thu_tu(st, con.get(sid) or [])

    if not ke:
        return

    if len(ke) == 2:
        cap = nguoi_bay.cap_chia(st[ke[0]], st[ke[1]])
        if cap is not None:
            # ⭐ PHÉP CHIA. Viết bằng chính câu người đọc nghĩ trong đầu: một câu hỏi,
            # hai câu trả lời, không có đường thứ ba. Vế ngược KHÔNG in lại điều kiện —
            # in ra là mời người đọc phải tự đối chiếu xem nó có đúng là phủ định không,
            # trong khi `cap_chia` vừa bảo đảm chuyện đó rồi.
            ra.append(f"{tab}CHIA  {core.cond_display(cap[0], ts)} ?")
            for nhan, k in (("ĐÚNG", ke[0]), ("SAI ", ke[1])):
                ra.append(f"{tab}├─ {nhan}")
                _khoi(st, con, k, ts, sau + 2, ra, bo_qua_cong=True)
            return

    if len(ke) == 1:
        _khoi(st, con, ke[0], ts, sau, ra)
        return

    # Ngã rẽ THƯỜNG. Đầu nhánh toàn hành động là VÀ (làm hết), toàn cổng là HOẶC
    # (thử lần lượt) — `core.la_nga_re_va` giữ luật, dùng chung với soát tĩnh.
    va = core.la_nga_re_va([st[i] for i in ke])
    ra.append(f"{tab}{'LÀM CẢ' if va else 'THỬ LẦN LƯỢT'}:")
    for k in ke:
        ra.append(f"{tab}├─")
        _khoi(st, con, k, ts, sau + 2, ra)


def _khoi(st, con, sid, ts, sau, ra, bo_qua_cong=False):
    """Viết `sid` rồi viết tiếp phần dưới nó."""
    s = st[sid]
    tab = "  " * sau
    if s.get("type") == core.CHECK_COND:
        if not bo_qua_cong:
            # LỌC — trượt là thôi, sơ đồ không làm gì. Đây là thứ cho một chiến lược
            # quyền ĐỨNG NGOÀI, và cũng là thứ cộng dồn lại thành overfit.
            ra.append(f"{tab}LỌC   {_dieu_kien(s, ts)}")
        else:
            # Đầu một vế của phép chia: điều kiện đã in ở dòng CHIA rồi.
            pass
    else:
        ra.append(f"{tab}→ {_hanh_dong(s, ts)}")
    _nhanh(st, con, sid, ts, sau + (0 if bo_qua_cong else 1), ra)


def tom_tat(doc):
    """Mấy con số đọc được ngay: mấy lá, mấy phép chia, mấy cái lọc, có đường nào
    tới hành động mà KHÔNG qua cái lọc nào không.

    ⚠ Đường không qua lọc nghĩa là nến nào cũng đẻ ra một hành động — máy nã lệnh chứ
    không phải chiến lược. Hai vế của phép chia phủ kín nên chúng không lọc được gì."""
    ra = {"la": 0, "chia": 0, "loc": 0, "khoi": 0, "khong_loc": False}
    for tab in core.TABS:
        st, con, bd = _do_thi(doc.get(tab) or {})
        if bd is None:
            continue
        ra["khoi"] += len(st) - 1
        trong_cap = set()
        for ke in con.values():
            if len(ke) == 2 and nguoi_bay.cap_chia(st[ke[0]], st[ke[1]]) is not None:
                ra["chia"] += 1
                trong_cap |= {ke[0], ke[1]}
        for i, s in st.items():
            if s.get("type") == core.CHECK_COND and i not in trong_cap:
                ra["loc"] += 1
            if i != bd and not con.get(i):
                ra["la"] += 1

        def di(i, loc):
            s = st[i]
            if s.get("type") == core.CHECK_COND and i not in trong_cap:
                loc = True
            if s.get("type") in (core.VAO_LENH, core.SUA_LENH) and not loc:
                ra["khong_loc"] = True
            for j in con.get(i, ()):
                di(j, loc)

        di(bd, False)
    return ra


def van(doc, ten=None, dau=None):
    """MỘT sơ đồ → một khối chữ đọc được.

    `dau` — dòng đầu tự do (điểm, số lệnh…). Cố ý là THAM SỐ chứ không tự lấy: module
    này chỉ biết về LOGIC, còn điểm là chuyện của cái thước — mà cái thước thì đang là
    thứ đang bị nghi ngờ, nên nó không được lẫn vào đây."""
    doc = core.normalize_process(doc)
    ts = {t["ten"]: t.get("gia_tri") for t in (doc.get("tham_so") or [])}
    tt = tom_tat(doc)
    ra = [f"┏━ {ten or doc.get('name') or 'Máy vẽ'}"]
    if dau:
        ra.append(f"┃  {dau}")
    ra.append(f"┃  {tt['khoi']} khối · {tt['chia']} phép chia · {tt['loc']} cái lọc · "
              f"{tt['la']} lá"
              + ("   ⚠ CÓ ĐƯỜNG KHÔNG QUA LỌC NÀO (nến nào cũng bắn)"
                 if tt["khong_loc"] else ""))
    for tab in core.TABS:
        g = doc.get(tab) or {}
        st, con, bd = _do_thi(g)
        if bd is None or not con.get(bd):
            ra.append(f"┃")
            ra.append(f"┃ {tab.upper()}   (trống — không làm gì)")
            continue
        ra.append(f"┃")
        ra.append(f"┃ {tab.upper()}   nhịp {st[bd].get('nhip')}")
        than = []
        _nhanh(st, con, bd, ts, 1, than)
        ra += [f"┃ {d}" for d in than]
    ra.append("┗━")
    return "\n".join(ra)
