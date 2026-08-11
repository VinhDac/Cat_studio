"""NHẬT KÝ — phần quan trọng nhất của Strategy Tester.

Người dùng nói thẳng: *"đây là phần quan trọng nhất, vì người dùng debug, nâng cấp
model là ở hết đây."* Nên nó phải chịu được 135.000 dòng mà vẫn đọc được và vẫn nhẹ.

BA LUẬT
-------
1. **Bản ghi RỖNG CHỮ.** `bo_chay` chỉ nhả ra số nguyên, số thực và id. Chữ tiếng Việt
   được DỰNG Ở ĐÂY, và chỉ dựng cho lô đang nhìn (~200 dòng). 135.000 bản ghi vì thế
   không tốn một byte chữ nào lúc chạy.

2. **Lưu `id` khối, KHÔNG lưu nhãn `[3A.1]`.** Nhãn là hàm thuần của (đồ thị + VỊ TRÍ)
   và §9 đã cấm lưu nó vào file. Ghi nhãn vào nhật ký thì kéo một khối lên 1 px là toàn
   bộ nhật ký cũ trỏ vào khối khác — không đối chiếu lại được với lần chạy trước. Nhãn
   được DỰNG LẠI lúc hiển thị, từ chính bản `doc` đã đóng băng trong lần chạy đó.

3. **Chữ do PYTHON sinh**, JS không ghép một mẩu chuỗi nào — luật bất di bất dịch #2.

MỘT BẢN GHI = MỘT LƯỢT CHẠY
---------------------------
Không ghi từng khối đi qua: 7 khối × 71.000 nến = 500.000 dòng rác không ai đọc nổi.
Ghi đúng cái người debug cần biết — *lượt này đi tới đâu rồi chết vì sao*.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

import core
import luu_tru


# ---------------------------------------------------------------------------
# Nhãn khối — dựng lại, không lưu
# ---------------------------------------------------------------------------
def nhan_khoi(doc):
    """`{id khối: "3A.1"}` cho cả hai sơ đồ.

    Tính lại từ `doc` mỗi lần hiển thị. Rẻ (một lượt duyệt đồ thị 7 khối) và luôn đúng
    với chính bản `doc` đã chạy."""
    ra = {}
    for tab in core.TABS:
        g = doc.get(tab) or {}
        L = core.flow_order(g.get("steps") or [], g.get("edges"))
        ra.update(L.get("order") or {})
    return ra


def _khoi_theo_id(doc):
    """`{id: khối}` — cần cả KHỐI chứ không chỉ tên, vì phải đọc lại `conditions` để
    biết điều kiện thứ i hỏi toán hạng nào và bằng phép so nào."""
    ra = {}
    for tab in core.TABS:
        for st in (doc.get(tab) or {}).get("steps") or []:
            ra[st["id"]] = st
    return ra


# ---------------------------------------------------------------------------
# Dựng chữ
# ---------------------------------------------------------------------------
def _gio(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%m-%d %H:%M")


def _so(x, digits=2):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "đúng" if x else "sai"
    return f"{x:.{digits}f}"


def _vi_sao(cong, ts, khoi):
    """Vì sao lượt này chết — cổng nào, điều kiện thứ mấy, hai vế bằng bao nhiêu.

    Lấy điều kiện SAI ĐẦU TIÊN của cổng cuối cùng đã thử. Cổng luôn được tính đủ mọi
    điều kiện (core.md §12.5b) nên các vế còn lại vẫn nằm trong bản ghi — bấm vào dòng
    là xem được hết, không phải chạy lại."""
    if not cong:
        return ""
    c = cong[-1]
    st = khoi.get(c["khoi"])
    if st is None:
        return ""
    ds = st.get("conditions") or []
    for i, v in enumerate(c["ve"]):
        if v["dat"]:
            continue
        if i >= len(ds):
            break
        dk = ds[i]
        trai = core.toan_hang_display(dk.get("trai"), ts)
        phep = core.PHEP_SO.get(dk.get("phep"), dk.get("phep") or "?")
        if v["trai"] is None:
            # "chưa có số" KHÁC HẲN "so xong thấy không đạt" — trộn hai thứ này là lúc
            # debug sẽ đi tìm nhầm hướng.
            return f"{trai} chưa có dữ liệu"
        if isinstance(v["trai"], bool) or dk.get("dao"):
            dao = "KHÔNG " if dk.get("dao") else ""
            return f"{dao}{trai} = {_so(v['trai'])}"
        return f"{trai} = {_so(v['trai'])}, không {phep} {_so(v['phai'])}"
    return ""


def _viec_chu(v):
    """Một việc đã làm → một câu."""
    t = v["loai"]
    if t == "lenh_dat":
        h = "Mua" if v["huong"] == "mua" else "Bán"
        ngay = " (khớp ngay)" if v.get("khop_ngay") else ""
        return (f"đặt {h} {v['lenh_id']} @{_so(v['gia_dat'])}"
                f"  SL {_so(v['sl'])}  TP {_so(v['tp'])}{ngay}")
    if t == "lenh_sua":
        return (f"sửa {v['lenh_id']} · {core.SUA_CHE_DO.get(v['che_do'], v['che_do'])}"
                f" → SL {_so(v['sl'])}")
    if t == "lenh_huy":
        return f"huỷ lệnh chờ {v['lenh_id']}"
    if t == "lenh_dong":
        return f"đóng {v['lenh_id']} @{_so(v.get('gia'))} · {v.get('ly_do')}"
    return t


def dong_chu(r, nhan, khoi, ts, nen5):
    """MỘT bản ghi → MỘT dòng chữ.

    Dạng:  `11-05 19:00  ENTRY  [1]→[2]→[3]→[3A]→[3A.1]  đặt Mua L-0007 @3986.33 …`
    """
    t = _gio(nen5["t"][r["nen"]]) if 0 <= r["nen"] < len(nen5) else "—"
    tab = "ENTRY " if r["tab"] == core.TAB_ENTRY else "MANAGE"
    duong = "→".join(f"[{nhan.get(k, '?')}]" for k in r["duong"])
    lenh = f" {r['lenh_id']}" if r.get("lenh_id") else ""

    if r["viec"]:
        duoi = " · ".join(_viec_chu(v) for v in r["viec"])
    else:
        cuoi = r.get("cong") and r["cong"][-1]["khoi"]
        vs = _vi_sao(r.get("cong"), ts, khoi)
        duoi = f"hết lượt tại [{nhan.get(cuoi, '?')}]" + (f" · {vs}" if vs else "")
    return f"{t}  {tab}{lenh}  {duong}  {duoi}"


def dung_lo(kq, tu=0, so=200, chi_co_viec=True):
    """Dựng chữ cho MỘT LÔ đang nhìn thấy. Đây là cửa duy nhất giao diện gọi.

    `chi_co_viec=True` là mặc định: 135.000 dòng đều đều thì mắt không bắt được chỗ bất
    thường. Bật hết khi cần đào sâu."""
    ds = loc(kq.nhat_ky, chi_co_viec)
    doc = kq.doc
    nhan, khoi = nhan_khoi(doc), _khoi_theo_id(doc)
    ts = core.bang_tham_so(doc)
    ra = []
    for k in ds[tu:tu + so]:
        r = kq.nhat_ky[k]
        ra.append({"i": k, "nen": r["nen"], "tab": r["tab"],
                   "lenh_id": r.get("lenh_id"), "co_viec": bool(r["viec"]),
                   "chu": dong_chu(r, nhan, khoi, ts, kq.nen5)})
    return {"tong": len(ds), "tu": tu, "dong": ra}


def dung_lo_theo_nen(kq, j0, t_den):
    """Những lượt xảy ra TRONG một lô khung hình, kèm chỉ số M1 để phát đúng lúc.

    Khác `dung_lo` (cuộn theo trang): hàm này phục vụ PHÁT LẠI — nhật ký phải hiện ra
    đúng cái nhịp mà nó xảy ra, chứ không phải đổ ra một cục. Nhờ vậy người xem thấy
    dòng "đặt Buy Stop" nảy lên đúng lúc lệnh chờ hiện trên chart."""
    doc = kq.doc
    nhan, khoi = nhan_khoi(doc), _khoi_theo_id(doc)
    ts = core.bang_tham_so(doc)
    ra = []
    for i, r in enumerate(kq.nhat_ky):
        if r["j"] < j0:
            continue
        if kq.nen1["t"][r["j"]] > t_den:
            break
        ra.append({"i": i, "j": r["j"], "co_viec": bool(r["viec"]),
                   "lenh_id": r.get("lenh_id"),
                   "chu": dong_chu(r, nhan, khoi, ts, kq.nen5)})
    return ra


def loc(nhat_ky, chi_co_viec=True):
    """Chỉ số các lượt được hiện. Trả CHỈ SỐ chứ không trả bản ghi — để giao diện cuộn
    tới đúng dòng mà không phải chép cả danh sách."""
    if not chi_co_viec:
        return list(range(len(nhat_ky)))
    return [i for i, r in enumerate(nhat_ky) if r["viec"]]


# ---------------------------------------------------------------------------
# Ghi ra đĩa
# ---------------------------------------------------------------------------
def _van_tay(doc):
    """Dấu vân tay của SƠ ĐỒ (không tính vị trí khối): hai lần chạy cùng vân tay thì
    cùng logic, dù các khối đã bị kéo đi chỗ khác."""
    loi = json.dumps(
        [[[{k: v for k, v in s.items() if k != "pos"}
           for s in (doc.get(t) or {}).get("steps") or []],
          # Cạnh PHẢI nằm trong vân tay: hai sơ đồ cùng bộ khối mà nối khác nhau là hai
          # chiến lược khác nhau. Bỏ `pos` vì kéo khối đi chỗ khác không đổi logic —
          # nhưng nhớ là nó ĐỔI THỨ TỰ NHÁNH (§12.5c), nên chỗ mơ hồ đã bị soát chặn.
          sorted((e.get("from"), e.get("to")) for e in (doc.get(t) or {}).get("edges") or [])]
         for t in core.TABS] + [doc.get("tham_so") or []],
        sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(loi.encode("utf-8")).hexdigest()[:12]


def ghi(kq, cd, ten=None):
    """Ghi một lần chạy ra `du_lieu/nhat_ky/<tên>.jsonl`. Trả đường dẫn.

    Dòng ĐẦU là meta — kèm nguyên bản `doc` đã chạy, để mở lại lần chạy cũ và SO hai
    lần chạy. `so_lenh.py` hứa "chạy lại cùng dữ liệu ra cùng id"; file này là chỗ kiểm
    chứng lời hứa đó."""
    ten = ten or f"{kq.doc.get('name', 'chien_luoc')} {_van_tay(kq.doc)}"
    p = os.path.join(luu_tru.thu_muc_nhat_ky(),
                     luu_tru._ten_an_toan(ten) + ".jsonl")
    meta = {
        "loai": "meta", "phien_ban": core.PHIEN_BAN,
        "luc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "van_tay": _van_tay(kq.doc),
        "symbol": cd.symbol, "tf": kq.tf,
        "so_nen_m1": int(len(kq.nen1)), "so_nen_truc": int(len(kq.nen5)),
        "spread_diem": cd.spread_diem, "point": cd.point,
        "contract_size": cd.contract_size, "deposit": cd.deposit,
        "commission": cd.commission,
        "thong_ke": kq.thong_ke,
        "doc": kq.doc,
    }
    with open(p, "w", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
        for l in kq.so.lenh:
            # LỒNG vào khoá `"lenh"`, KHÔNG trải phẳng: `Lenh.tom_tat()` có sẵn một
            # khoá tên `loai` (stop / limit / market) và nó ĐÈ MẤT nhãn dòng, khiến đọc
            # ngược file lại nhận nhầm 29 lệnh thành 29 lượt. Lỗi chỉ lộ khi đọc lại —
            # ghi thì vẫn "thành công".
            f.write(json.dumps({"loai": "lenh", "lenh": l.tom_tat()},
                               ensure_ascii=False) + "\n")
        for r in kq.nhat_ky:
            f.write(json.dumps({"loai": "luot", **r}, ensure_ascii=False) + "\n")
    return p


def doc_file(duong_dan):
    """Đọc lại một lần chạy đã ghi. Trả `(meta, lệnh, lượt)`."""
    meta, lenh, luot = {}, [], []
    with open(duong_dan, encoding="utf-8") as f:
        for dong in f:
            d = json.loads(dong)
            if d.get("loai") == "meta":
                meta = d
            elif d.get("loai") == "lenh":
                lenh.append(d["lenh"])
            else:
                luot.append(d)
    return meta, lenh, luot


def so_hai_lan(cu, moi):
    """So hai lần chạy — thứ vòng lặp "nâng cấp model" thật sự cần.

    Trả một dòng chữ trả lời đúng câu hỏi mỗi lần bấm ▶: *"so với lần trước thì sao?"*"""
    if not cu:
        return ""
    a, b = cu.get("thong_ke") or {}, moi.get("thong_ke") or moi
    phan = []
    for k, nhan, lam_tron in (("so_lenh", "lệnh", 0), ("tong_R", "R", 1),
                              ("ty_le_thang", "% thắng", 1),
                              ("drawdown_pt", "% DD", 2)):
        if k not in a or k not in b:
            continue
        d = b[k] - a[k]
        if abs(d) < 10 ** -lam_tron / 2:
            continue
        phan.append(f"{d:+.{lam_tron}f} {nhan}")
    if cu.get("van_tay") != moi.get("van_tay"):
        phan.append("sơ đồ ĐÃ ĐỔI")
    return "so với lần trước: " + (" · ".join(phan) if phan else "y hệt")
