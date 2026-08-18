"""NGƯỜI BÀY — bày ra nước đi hợp lệ, và đọc ngược sơ đồ thành chuỗi.

VÌ SAO BÀI NÀY PHẢI CÓ
----------------------
`validate_flow_graph` là NGƯỜI SOÁT: vẽ xong rồi mới nói đúng/sai. `nguoi_bay` là NGƯỜI
BÀY: sơ đồ đang dở thì bày ra nước đi nào còn hợp lệ. Hai bên phải nói **cùng một điều**
— nếu người bày cho đi một nước mà người soát mắng, thì mọi máy tìm sẽ đốt 17 giây
backtest cho một sơ đồ hỏng, và đốt đều đặn.

Bài này canh năm điều (core.md §18.7):

  1. **Kho nước đi CỐ ĐỊNH** — không trùng, không rỗng, và sinh TỪ KHO chứ không gõ tay
     (thêm một toán hạng là kho nước đi phải tự lớn).
  2. **Hai chiều KHỚP NHAU** — đọc ngược sơ đồ mẫu rồi dựng xuôi lại phải ra ĐÚNG nó.
     Đây là phép kiểm duy nhất chứng minh chiều ngược không nói dối, và chiều ngược là
     thứ mở ra việc cho máy học từ sơ đồ người dùng vẽ tay.
  3. **Sinh bừa cũng không ra sơ đồ hỏng** — đi ngẫu nhiên trong mặt nạ, mọi sơ đồ ra
     lò đều phải qua soát tĩnh với 0 lỗi.
  4. **Sơ đồ máy vẽ CHẠY ĐƯỢC** — không chỉ hợp lệ trên giấy.
  5. **Nổ chứ không đoán** — sơ đồ có thứ kho chưa diễn tả được thì `KhongDocDuoc`,
     không phải lặng lẽ bỏ qua rồi trả về một chuỗi mô tả sơ đồ KHÁC.

Chạy:  python tests\\test_nguoi_bay.py
"""
import io
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cat_studio import api  # noqa: E402
from cat_studio import bo_chay as bc  # noqa: E402
from cat_studio import core  # noqa: E402
from cat_studio import kho  # noqa: E402
from cat_studio import nguoi_bay as nb  # noqa: E402

dung = sai = 0


def kiem(ten, dk, chi_tiet=""):
    global dung, sai
    if dk:
        dung += 1
        print(f"  ✔ {ten} {chi_tiet}")
    else:
        sai += 1
        print(f"  ✘ {ten} {chi_tiet}")


# ================= 1. KHO NƯỚC ĐI =================
print("\n▸ Kho nước đi — cố định, không trùng, sinh từ kho")

kiem("kho không rỗng", len(nb.KHO_NUOC_DI) > 100, f"— {len(nb.KHO_NUOC_DI):,} nước")
kiem("không nước đi nào TRÙNG",
     len(set(nb.KHO_NUOC_DI)) == len(nb.KHO_NUOC_DI))
kiem("mọi nước đi đều BĂM ĐƯỢC (tuple bất biến — chuỗi phải đem đi so, đem đi lưu)",
     all(isinstance(hash(n), int) for n in nb.KHO_NUOC_DI))

# ⭐ SINH TỪ KHO, không gõ tay. Mọi toán hạng có mặt trong kho đồ mà KHÔNG xuất hiện
# trong một nước đi nào là một toán hạng máy không bao giờ dùng tới — hoặc kho nước đi
# đang giữ một danh sách chép tay đã lạc hậu (đúng cái bẫy `CAN_ZONE`, §15.8).
_trong_nuoc = {n[1] for n in nb.KHO_NUOC_DI if n[0] in ("dk_so", "dk_gia", "dk_ds")}
_thieu = [t["key"] for t in kho.TOAN_HANG if t["key"] not in _trong_nuoc]
kiem("MỌI toán hạng trong kho đều có nước đi", not _thieu, f"— thiếu: {_thieu}")

_mocs = {n[3] for n in nb.KHO_NUOC_DI if n[0] == "vao_lenh"}
kiem("mọi mốc neo đều dùng được", _mocs == set(core.MOC_ENTRY),
     f"— {sorted(_mocs)}")
_cd = {n[1] for n in nb.KHO_NUOC_DI if n[0] == "sua_lenh"}
kiem("mọi chế độ Sửa lệnh đều dùng được", _cd == set(core.SUA_CHE_DO))

# Lệnh THỊ TRƯỜNG chỉ có một mốc có nghĩa — sáu nước đi cho cùng một sơ đồ là mạng học
# một thứ bằng sáu đường, và chuỗi mất tính duy nhất.
_mkt = {n[3] for n in nb.KHO_NUOC_DI if n[0] == "vao_lenh" and n[2] == "market"}
kiem("lệnh thị trường chỉ có MỘT mốc neo (không đẻ nước đi trùng nghĩa)",
     _mkt == {"close"}, f"— {sorted(_mkt)}")



def _hop_le_ca_chuoi(chuoi):
    """Đi lại chuỗi từ đầu, mỗi nước phải được MẶT NẠ cho phép.

    ⚠ `dung()` không kiểm gì cả, nên một chuỗi dựng đúng sơ đồ VẪN có thể chứa nước đi
    máy không bao giờ đi được. Chuỗi như thế là thứ không đem đi so được."""
    b = nb.Ban()
    for i in chuoi:
        if not nb.mat_na(b)[i]:
            return False
        b.di(i)
    return True


def _co_duong_khong_loc(d):
    """Có đường nào từ Bắt đầu tới một HÀNH ĐỘNG mà không qua cổng LỌC nào không?

    Cổng nằm trong một CẶP CHIA không lọc được gì — hai vế phủ kín nên luôn có đúng một
    vế khớp. Chỉ cổng đứng một mình mới cho sơ đồ quyền KHÔNG LÀM GÌ."""
    g = d[core.TAB_ENTRY]
    st = {s["id"]: s for s in g["steps"]}
    con = {}
    for e in g["edges"]:
        con.setdefault(e["from"], []).append(e["to"])
    cap = set()
    for ke in con.values():
        if len(ke) != 2:
            continue
        sa, sb = st.get(ke[0]) or {}, st.get(ke[1]) or {}
        if len(sa.get("conditions") or ()) != 1 or len(sb.get("conditions") or ()) != 1:
            continue
        ca, cb = sa["conditions"][0], sb["conditions"][0]
        if ca.get("trai") != cb.get("trai") or ca.get("phai") != cb.get("phai"):
            continue
        pa, pb = ca.get("phep"), cb.get("phep")
        if nb.PHEP_NGUOC.get(pa) == pb or {pa, pb} == {"la_dung", "la_sai"}:
            cap |= {ke[0], ke[1]}
    xau = []

    def di(i, loc):
        s = st.get(i) or {}
        if s.get("type") == core.CHECK_COND and i not in cap:
            loc = True
        if s.get("type") in (core.VAO_LENH, core.SUA_LENH) and not loc:
            xau.append(i)
        for j in con.get(i, ()):
            di(j, loc)

    di(next(s["id"] for s in g["steps"] if core.is_start_step(s)), False)
    return bool(xau)


# ================= 2. HAI CHIỀU KHỚP NHAU =================
print("\n▸ Hai chiều — đọc ngược sơ đồ mẫu rồi dựng xuôi lại")

GOC = core.normalize_process(api._so_do_mau())
_chuoi, _tron = nb.doc_nguoc(GOC, lam_tron=True)
kiem("đọc ngược được sơ đồ mẫu", bool(_chuoi), f"— {len(_chuoi)} nước đi")
kiem("mọi chỉ số nằm trong kho",
     all(0 <= i < len(nb.KHO_NUOC_DI) for i in _chuoi))

MOI = nb.dung(_chuoi, ten=GOC["name"])


def hinh(d):
    """HÌNH DẠNG của sơ đồ: khối gì, nối vào đâu.

    Bỏ `id` (uuid sinh mỗi lần một khác), `name` (máy không đặt tên khối) và TÊN THAM
    SỐ (máy dùng tên `core` tự gợi ý, người vẽ dùng tên ngắn của mình — hai cái tên cho
    cùng một con số không phải hai sơ đồ khác nhau)."""
    gt = {t["ten"]: t["gia_tri"] for t in d["tham_so"]}

    def mo(x):
        if isinstance(x, dict):
            return {k: mo(v) for k, v in x.items() if k not in ("id", "name", "pos")}
        if isinstance(x, list):
            return [mo(v) for v in x]
        return float(gt[x]) if isinstance(x, str) and x in gt else x

    ra = {}
    for tab in core.TABS:
        so = d[tab]
        num = {s["id"]: k for k, s in enumerate(so["steps"])}
        ra[tab] = (mo(so["steps"]),
                   sorted((num[e["from"]], num[e["to"]]) for e in so["edges"]))
    return ra


_a, _b = hinh(GOC), hinh(MOI)
kiem("ĐỒ THỊ dựng lại trùng khít (cùng cạnh, cùng thứ tự)",
     [_a[t][1] for t in core.TABS] == [_b[t][1] for t in core.TABS])
_lech = [f"{t}#{k}" for t in core.TABS
         for k in range(max(len(_a[t][0]), len(_b[t][0])))
         if (_a[t][0][k:k + 1] or [None])[0] != (_b[t][0][k:k + 1] or [None])[0]]
# ⚠ `zone_range_max = 4,0` không có trên thang `nguong` — người vẽ tay không bị buộc
# theo thang, máy thì có (§18.1). Nên một chỗ lệch là ĐÚNG, và nó phải được BÁO RA.
kiem("KHỐI dựng lại trùng khít, trừ đúng những chỗ đã báo làm tròn",
     len(_lech) <= len(_tron), f"— lệch {_lech}, đã báo tròn {len(_tron)}")
kiem("và chỗ làm tròn được BÁO RA, không nuốt lặng", bool(_tron),
     f"— {[(t, v, g) for _, t, v, g in _tron]}")

_v = core.validate_process(MOI)
kiem("sơ đồ dựng lại QUA soát tĩnh, 0 lỗi 0 cảnh báo",
     not _v, f"— {[p['message'][:60] for p in _v]}")

# ⚠ Không làm tròn thì phải NỔ, không được lặng lẽ kéo về nấc gần nhất: chuỗi khi đó
# mô tả một sơ đồ KHÁC với cái vừa đọc.
try:
    nb.doc_nguoc(GOC)
    _no = False
except nb.KhongDocDuoc as e:
    _no = "thang" in str(e)
kiem("giá trị ngoài thang mà KHÔNG xin làm tròn thì NỔ (không đoán)", _no)


# ================= 3. SINH BỪA CŨNG KHÔNG RA SƠ ĐỒ HỎNG =================
print("\n▸ Sinh ngẫu nhiên — người bày và người soát phải nói cùng một điều")


#: Trần độ phức tạp (§15.5) nhìn từ phía người đi: một cổng bao nhiêu điều kiện thì đủ.
#:
#: ⚠ Không có trần này thì lượt đi LANG THANG — đo được: bốc đều trong mặt nạ thì
#: 29/60 lượt chạm mốc 120 nước mà vẫn đang thêm điều kiện vào cùng một cổng. Mặt nạ
#: KHÔNG sai (nó vẫn cho thêm, và thêm vẫn hợp lệ); sai là ở người đi không biết dừng.
#: Đây chính là việc của thuật toán tìm, không phải của người bày.
DK_MOI_CONG = 3


def sinh_that(rng, toi_da=200):
    """Đi bừa trong mặt nạ cho tới khi xong. Trả `(tài liệu, chuỗi)`."""
    b = nb.Ban()
    for _ in range(toi_da):
        if b.xong:
            break
        mn = nb.mat_na(b)
        duoc = [i for i, x in enumerate(mn) if x]
        if not duoc:
            return None, b.chuoi
        # Cổng đã đủ điều kiện thì thôi thêm — ép lượt đi TIẾN chứ đừng dày mãi.
        if len((b.cong or {}).get(b.ds) or ()) >= DK_MOI_CONG:
            tien = [i for i in duoc if nb.KHO_NUOC_DI[i][0] not in
                    ("dk_so", "dk_gia", "dk_ds")]
            duoc = tien or duoc
        # ⭐ BỐC HAI TẦNG: loại trước, ô sau. Bốc đều từng ô là một thiên kiến rất mạnh
        # (`vao_lenh` chiếm 56% kho) — và nó KHÔNG chỉ làm lệch thống kê: bộ đi bừa cũ
        # gần như không bao giờ đụng tới `hop_le`, nên hai lỗ hổng quanh `zone_hop_le`
        # lọt qua 60 sơ đồ mà bài này vẫn báo xanh. Bộ bốc nào thì tìm ra lỗi nấy.
        theo_loai = {}
        for i in duoc:
            theo_loai.setdefault(nb.KHO_NUOC_DI[i][0], []).append(i)
        # Và nghiêng về `het` khi chuỗi đã dài.
        i = nb.CHI_SO[("het",)]
        b.di(i if (mn[i] and rng.random() < len(b.chuoi) / 40.0)
             else rng.choice(theo_loai[rng.choice(sorted(theo_loai))]))
    return (b.tai_lieu() if b.xong else None), b.chuoi


_rng = random.Random(20260817)
_ds, _ket = [], 0
for _ in range(60):
    _d, _c = sinh_that(_rng)
    if _d is None:
        _ket += 1
        continue
    _ds.append((_d, _c))

kiem("sinh bừa thì lượt nào cũng đi tới đích", not _ket,
     f"— {_ket} lượt kẹt (mặt nạ tắt hết trước khi xong)")
kiem("sinh được sơ đồ", len(_ds) >= 50, f"— {len(_ds)}/60")

_hong = [(p["severity"], p["message"][:70]) for d, _ in _ds
         for p in core.validate_process(d) if p["severity"] == "error"]
kiem("KHÔNG sơ đồ nào bị người soát mắng LỖI", not _hong,
     f"— {len(_hong)} lỗi, ví dụ: {_hong[:2]}")

_canh_bao = [p["message"][:70] for d, _ in _ds for p in core.validate_process(d)]
kiem("và cũng không cảnh báo nào", not _canh_bao,
     f"— {len(_canh_bao)}, ví dụ: {_canh_bao[:2]}")

# Chuỗi phải DỰNG LẠI ĐÚNG cái vừa sinh — đó là điều kiện để lưu/đột biến/replay được.
_khac = sum(1 for d, c in _ds if hinh(nb.dung(c)) != hinh(d))
kiem("dựng lại từ chuỗi ra ĐÚNG sơ đồ vừa sinh", not _khac, f"— {_khac} cái lệch")

# Và đọc ngược sơ đồ MÁY VẼ phải ra lại đúng chuỗi ấy — hai chiều khép kín.
_lech_nguoc = 0
for d, c in _ds[:20]:
    try:
        c2, _ = nb.doc_nguoc(d)
    except nb.KhongDocDuoc:
        _lech_nguoc += 1
        continue
    if hinh(nb.dung(c2)) != hinh(d):
        _lech_nguoc += 1
kiem("đọc ngược chính sơ đồ máy vẽ cũng khép kín", not _lech_nguoc,
     f"— {_lech_nguoc}/20 lệch")


# ================= 4. SƠ ĐỒ MÁY VẼ CHẠY ĐƯỢC =================
print("\n▸ Chạy thật — hợp lệ trên giấy chưa đủ")

T0 = 1700000100          # chia hết cho 300 (một nến M5) — xem test_zone
_n = 3000
_gia = [100.0 + 8.0 * np.sin(k / 40.0) + (k % 7) * 0.3 for k in range(_n)]
_nen = np.zeros(_n, dtype=[("t", "i8"), ("o", "f8"), ("h", "f8"), ("l", "f8"),
                           ("c", "f8"), ("vol", "f8")])
for _k, _g in enumerate(_gia):
    _nen[_k] = (T0 + _k * 60, _g, _g + 0.6, _g - 0.6, _g, 1.0)

_CD = bc.CaiDat(point=1.0, contract_size=1.0, digits=2, spread_diem=0.0,
                deposit=10_000.0, lot_min=0.01, lot_buoc=0.01, lot_max=100.0)
_no_khi_chay, _co_lenh, _thieu_nen = [], 0, 0
for _d, _ in _ds[:25]:
    try:
        _kq = bc.chay(_d, _nen, _CD)
    except Exception as e:                       # noqa: BLE001 — đang ĐO xem có nổ không
        # ⚠ "Không đủ nến" KHÔNG phải lỗi sơ đồ: máy được chọn khung W1/MN1, mà bộ nến
        # tổng hợp ở đây chỉ dài 3000 phút. Đó là dữ liệu của bài kiểm thiếu, không
        # phải người bày sai — và nó nói to, đúng nếp.
        if "không đủ nến" in str(e).lower():
            _thieu_nen += 1
            continue
        _no_khi_chay.append(f"{type(e).__name__}: {e}"[:90])
        continue
    _co_lenh += bool(_kq.so.lenh)
kiem("không sơ đồ nào làm bộ chạy NỔ", not _no_khi_chay,
     f"— {len(_no_khi_chay)}, ví dụ: {_no_khi_chay[:2]}"
     + (f" (bỏ qua {_thieu_nen} ca thiếu nến)" if _thieu_nen else ""))
# Không đòi con nào cũng vào lệnh: phần lớn sơ đồ sinh bừa có cổng không bao giờ cùng
# đúng, và đó là chuyện BÌNH THƯỜNG — chính nó quyết định ngân sách thật của máy tìm
# (§18.7.4). Chỉ đòi cơ chế thông suốt: phải có ÍT NHẤT một cái vào được lệnh.
kiem("có sơ đồ thật sự vào được lệnh", _co_lenh > 0, f"— {_co_lenh}/25")


# ================= 5. MẶT NẠ NÓI ĐÚNG LUẬT =================
print("\n▸ Mặt nạ — vài luật §17 kiểm thẳng")

_b = nb.Ban()
_mn = nb.mat_na(_b)
kiem("mới mở: KHÔNG được vào lệnh ngay dưới khối Bắt đầu (§5 — nhánh mở đầu bằng cổng)",
     not any(_mn[i] for i, n in enumerate(nb.KHO_NUOC_DI) if n[0] == "vao_lenh"))
kiem("mới mở: KHÔNG được `het` (Entry chưa có khối Vào lệnh nào)",
     not _mn[nb.CHI_SO[("het",)]])
kiem("mới mở: đặt nhịp thì được", any(_mn[nb.CHI_SO[("nhip", tf)]]
                                     for tf in core.TIMEFRAMES))
kiem("mới mở: toán hạng ZONE bị tắt (chưa có cổng zone — §12.6c)",
     not any(_mn[i] for i, n in enumerate(nb.KHO_NUOC_DI)
             if n[0] in ("dk_so", "dk_gia", "dk_ds") and n[1] in kho.CAN_ZONE))
kiem("mới mở: toán hạng của MANAGE bị tắt ở Entry",
     not any(_mn[i] for i, n in enumerate(nb.KHO_NUOC_DI)
             if n[0] in ("dk_so", "dk_gia", "dk_ds") and n[1] == "lenh_da_khop"))

_b.di(nb.CHI_SO[("cong_zone",)])
_mn = nb.mat_na(_b)
kiem("sau cổng zone: toán hạng zone BẬT",
     any(_mn[i] for i, n in enumerate(nb.KHO_NUOC_DI)
         if n[0] == "dk_so" and n[1] == "zone_dem"))
# ⚠ `zone_hop_le` là ngoại lệ và có luật riêng: nó là KẾT QUẢ của chính cổng zone, và
# chưa khai phần HỢP LỆ thì nó còn là một khái niệm chưa ai định nghĩa.
kiem("nhưng `zone_hop_le` thì KHÔNG — nó là kết quả của chính cổng này",
     not any(_mn[i] for i, n in enumerate(nb.KHO_NUOC_DI)
             if n[0] == "dk_ds" and n[1] == "zone_hop_le"))
kiem("nhưng cổng zone thứ hai thì KHÔNG (§15.11 — nhiều zone đang hoãn)",
     not _mn[nb.CHI_SO[("cong_zone",)]])
kiem("cổng RỖNG chưa được đóng (§6.0 — cổng không điều kiện thì luôn khớp)",
     not _mn[nb.CHI_SO[("cong_moi",)]])

_dk = next(i for i, n in enumerate(nb.KHO_NUOC_DI)
           if n[0] == "dk_so" and n[1] == "atr")
_b.di(_dk)

# ⭐ ĐIỀU KIỆN CÒN DỞ thì mọi nước khác đều tắt. `atr` đòi khung giờ và chu kỳ; chưa
# khai đủ mà cho đi tiếp là đẻ ra đúng lỗi `chưa chọn khung thời gian` — đo được 910
# lỗi trên 60 sơ đồ hồi chưa có luật này.
_mn = nb.mat_na(_b)
kiem("điều kiện chưa khai đủ: CHỈ mấy nước lấp chỗ trống được bật",
     {nb.KHO_NUOC_DI[i][0] for i, x in enumerate(_mn) if x} == {"tf_trai",
                                                                "chu_ky_trai"})
kiem("và `cong_moi` bị tắt trong lúc đó", not _mn[nb.CHI_SO[("cong_moi",)]])

_mn = nb.mat_na(_b)
kiem("chu kỳ cho vế trái bật (ATR có ô `period`)",
     any(_mn[nb.CHI_SO[("chu_ky_trai", n)]] for n in nb.THANG["chu_ky"]))
kiem("chu kỳ cho vế PHẢI tắt (vế phải là một LƯỢNG, không có chu kỳ)",
     not any(_mn[nb.CHI_SO[("chu_ky_phai", n)]] for n in nb.THANG["chu_ky"]))

_b.di(nb.CHI_SO[("tf_trai", "M5")])
_b.di(nb.CHI_SO[("chu_ky_trai", 14)])
_mn = nb.mat_na(_b)
kiem("khai đủ rồi thì không đặt lại chu kỳ", not _mn[nb.CHI_SO[("chu_ky_trai", 14)]])
kiem("cổng có điều kiện ĐỦ rồi thì đóng được", _mn[nb.CHI_SO[("cong_moi",)]])
kiem("hỏi LẠI cùng toán hạng trong một cổng thì KHÔNG", not _mn[_dk])
kiem("`hop_le` bật — đây đúng là cổng định nghĩa zone (§12.6f)",
     _mn[nb.CHI_SO[("hop_le",)]])


# ---- TRẦN ĐỘ PHỨC TẠP §15.5 — chỉ áp cho MÁY, người vẽ không bị chặn ----
print("\n▸ Trần độ phức tạp — §15.5")


def them_mot_dieu_kien(b):
    """Thêm một điều kiện `dk_so` đang hợp lệ, khai đủ cho tới khi nó xong.

    ⚠ CỐ Ý chỉ lấy `dk_so`. Lấy bừa thì cổng ăn hết năm mức giá (`close` `open` `high`
    `low` `ma`) rồi HẾT `dk_gia` để thêm — bài kiểm sẽ báo "trần chặn" trong khi thật
    ra chỉ là cạn từ vựng. Hai nguyên nhân khác nhau, không được lẫn."""
    i = next(i for i, x in enumerate(nb.mat_na(b))
             if x and nb.KHO_NUOC_DI[i][0] == "dk_so")
    b.di(i)
    while True:                       # lấp nốt khung giờ / chu kỳ nếu toán hạng đòi
        mn = nb.mat_na(b)
        cho = [i for i, x in enumerate(mn) if x and nb.KHO_NUOC_DI[i][0].startswith(
            ("tf_", "chu_ky_"))]
        if not cho or any(x for i, x in enumerate(mn)
                          if nb.KHO_NUOC_DI[i][0] == "cong_moi"):
            return b
        b.di(cho[0])


# ⚠ Mở CỔNG ZONE trước, và đó không phải tiểu tiết: trước cổng zone, sơ đồ Entry chỉ
# có ĐÚNG BỐN toán hạng số dùng được (`so_vi_the` · `so_lenh_cho` · `drawdown_pt` ·
# `atr`) — vừa đúng bằng trần. Không mở zone thì bài kiểm dưới báo "trần chặn" trong
# khi thật ra là CẠN TỪ VỰNG, hai chuyện khác hẳn nhau.
_bt = nb.Ban()
_bt.di(nb.CHI_SO[("cong_zone",)])
for _k in range(nb.TRAN["dk_moi_cong"]):
    them_mot_dieu_kien(_bt)
kiem(f"cổng đủ {nb.TRAN['dk_moi_cong']} điều kiện thì KHÔNG thêm được nữa",
     not any(x for i, x in enumerate(nb.mat_na(_bt))
             if nb.KHO_NUOC_DI[i][0] in ("dk_so", "dk_gia", "dk_ds")),
     f"— đang có {len((_bt.cong or {}).get('conditions') or ())}")
kiem("nhưng đóng cổng thì vẫn được (không phải ngõ cụt)",
     nb.mat_na(_bt)[nb.CHI_SO[("cong_moi",)]])

# Trần là CÀI ĐẶT của tầng CHỌN (§18.6.1), không phải luật — nới ra là mặt nạ nới theo.
kiem("nới trần thì thêm được ngay (trần là cài đặt, không phải luật)",
     any(x for i, x in enumerate(nb.mat_na(_bt, {**nb.TRAN, "dk_moi_cong": 9}))
         if nb.KHO_NUOC_DI[i][0] in ("dk_so", "dk_gia", "dk_ds")))


# ---- TẦNG CHỌN: tắt THẺ (§18.6.1) ----
print("\n▸ Tầng CHỌN — tắt thẻ")

# ⭐ MỘT cơ chế cho MỌI chiều: toán hạng, khung giờ, mốc neo, hướng, loại lệnh, chế độ
# sửa, VÀ từng nấc thang. Bài này canh cả bảy, không chỉ toán hạng.
_MAU_THE = {
    "th": "th:atr", "tf": "tf:M5", "moc": "moc:zone_HH", "huong": "huong:mua",
    "loai": "loai:market", "sua": "sua:hoa_von", "sl": "sl:1.5", "tp": "tp:2.0",
    "nguong": "nguong:0.75", "rui_ro": "rui_ro:0.5", "chu_ky": "chu_ky:14",
}
_thieu_the = [k for k, v in _MAU_THE.items()
              if v.split(":", 1)[1] not in nb.THE_CHON.get(k, ())]
kiem("mọi nhóm thẻ ĐỀU có mặt trong kho", not _thieu_the, f"— thiếu {_thieu_the}")

_hong = []
for _nhom, _the in _MAU_THE.items():
    _b2 = nb.Ban()
    _co = any(_the in nb.the(n) for n in nb.KHO_NUOC_DI)
    # Tắt thẻ ⇒ KHÔNG nước đi nào mang thẻ đó còn bật, ở bất kỳ trạng thái nào.
    _mn = nb.mat_na(_b2, None, {_the})
    if not _co or any(x and _the in nb.the(nb.KHO_NUOC_DI[i])
                      for i, x in enumerate(_mn)):
        _hong.append(_the)
kiem("tắt một thẻ thì MỌI nước mang thẻ đó tắt theo", not _hong, f"— {_hong}")

# ⚠ Kho nước đi KHÔNG đổi khi tắt thẻ — đó là cả điểm của cách làm này (§18.7.2).
_truoc = len(nb.KHO_NUOC_DI)
nb.mat_na(nb.Ban(), None, set(_MAU_THE.values()))
kiem("và KHO NƯỚC ĐI không hề đổi (mặt nạ che, không sửa kho)",
     len(nb.KHO_NUOC_DI) == _truoc, f"— {_truoc} → {len(nb.KHO_NUOC_DI)}")

# Tắt hết vẫn phải đi tới đích được — `tat` là CHỌN, không được biến thành ngõ cụt.
_b3 = nb.Ban()
_tat_nhieu = {f"tf:{t}" for t in core.TIMEFRAMES[3:]} | {"loai:stop", "huong:ban"}
_ket = 0
for _ in range(200):
    if _b3.xong:
        break
    _mn = nb.mat_na(_b3, None, _tat_nhieu)
    _duoc = [i for i, x in enumerate(_mn) if x]
    if not _duoc:
        _ket = 1
        break
    _tl = {}
    for i in _duoc:
        _tl.setdefault(nb.KHO_NUOC_DI[i][0], []).append(i)
    _b3.di(_rng.choice(_tl[_rng.choice(sorted(_tl))]))
kiem("tắt nhiều thẻ vẫn đi tới đích được (CHỌN không được thành ngõ cụt)",
     _b3.xong and not _ket, f"— {len(_b3.chuoi)} nước, kẹt={_ket}")
kiem("và sơ đồ ra lò vẫn qua soát tĩnh",
     _b3.xong and not core.validate_process(_b3.tai_lieu()))

# ================= 6. PHÉP CHIA =================
print("\n▸ Phép chia — GIỮ cả hai bên, không vứt bên nào")

# ⭐ VÌ SAO MỤC NÀY PHẢI CÓ. Nối thêm một cổng là VỨT phần không khớp: vùng còn lại co
# lại, số lệnh rụng theo, và điểm của một sơ đồ ít lệnh là may rủi. Máy chỉ có nước
# "thêm điều kiện" nên nó chỉ viết được CÁI LỌC — đo được 263/400 sơ đồ chỉ có ĐÚNG MỘT
# đường ở Entry, và `nếu A … ngược lại …` tự mọc ra đúng 6/600 lần. Nước `chia` là chỗ
# sửa đúng cái đó, nên mấy bất biến dưới đây là thứ giữ cho nó không trượt về cũ.

_CHIA_MAU = ("chia_gia", "high", ">", "low")
kiem("nước chia có trong kho", _CHIA_MAU in nb.CHI_SO)

# Mỗi phép chia chỉ có MỘT tên. Bày cả `>` lẫn `<=` cho cùng một chỗ cắt là hai nước đi
# ra cùng một sơ đồ — đúng thứ `_kho_hanh_dong` đã dẹp một lần ở mốc neo lệnh thị trường.
_phep_chia = {n[2] for n in nb.KHO_NUOC_DI if n[0] == "chia_gia"}
kiem("mỗi chỗ cắt chỉ có MỘT nước (không hai tên cho một phép chia)",
     _phep_chia == {p for p, _ in nb.PHEP_CHIA}, f"— {sorted(_phep_chia)}")
kiem("⚠ không có `==` — một vế của phép chia ấy gần như rỗng, tức cái lọc đội lốt",
     not [n for n in nb.KHO_NUOC_DI if n[0] in nb._CHIA and "==" in n])

# ---- đi một nước chia rồi soi cái bàn ----
_bc = nb.Ban()
for _n in [("dk_so", "atr", ">", 0.5, "atr_nen"), ("tf_trai", "M5"),
           ("chu_ky_trai", 14), _CHIA_MAU]:
    _bc.di(nb.CHI_SO[_n])

kiem("chia xong: vế THUẬN đã treo lên, vế NGƯỢC nằm chờ trên ngăn xếp",
     len(_bc.ngan_xep) == 1 and _bc.ngan_xep[-1][6] is not None)
kiem("⭐ NIÊM PHONG — không cổng nào đang mở, nên không nhét thêm điều kiện vào được",
     _bc.cong is None)
_mn = nb.mat_na(_bc)
kiem("và mặt nạ nói đúng câu ấy: mọi nước `dk_*` đều TẮT",
     not [i for i, x in enumerate(_mn)
          if x and nb.KHO_NUOC_DI[i][0] in nb._DK and nb.KHO_NUOC_DI[i][0] != "chia"],
     "" if not [i for i, x in enumerate(_mn) if x and nb.KHO_NUOC_DI[i][0] in nb._DK]
     else f"— còn bật {[nb.KHO_NUOC_DI[i] for i, x in enumerate(_mn) if x and nb.KHO_NUOC_DI[i][0] in nb._DK][:2]}")

# Bổ nghĩa điền MỘT lần, phải sang CẢ HAI vế — lệch một cái là hai vế thôi phủ kín.
_bc.di(nb.CHI_SO[("tf_trai", "H1")])
_bc.di(nb.CHI_SO[("tf_phai", "H1")])
_ve_a = _bc.khoi[-1]["conditions"][0]
_ve_b = _bc.ngan_xep[-1][6]["conditions"][0]
kiem("⭐ bổ nghĩa điền MỘT lần mà sang CẢ HAI vế",
     _ve_a["trai"] == _ve_b["trai"] and _ve_a["phai"] == _ve_b["phai"],
     f"— {_ve_a['trai']} vs {_ve_b['trai']}")
kiem("hai vế là PHỦ ĐỊNH của nhau",
     nb.PHEP_NGUOC.get(_ve_a["phep"]) == _ve_b["phep"],
     f"— {_ve_a['phep']} ↔ {_ve_b['phep']}")

# ---- đóng vế thuận thì vế ngược mọc ra ----
_bc.di(nb.CHI_SO[("vao_lenh", "mua", "market", "close", 1.5, 2.0, 0.5)])
_truoc_khoi = len(_bc.khoi)
_bc.di(nb.CHI_SO[("dong_nhanh",)])
kiem("đóng vế THUẬN là VẾ NGƯỢC mọc ra ngay (cặp này không đứng một mình)",
     len(_bc.khoi) == _truoc_khoi + 1
     and _bc.khoi[-1]["conditions"][0]["phep"] == _ve_b["phep"])

_cha = [e["from"] for e in _bc.canh if e["to"] == _bc.khoi[-1]["id"]]
_cha_a = [e["from"] for e in _bc.canh if e["to"] == _ve_a and False] or None
kiem("hai vế cùng MỘT cha — đúng một ngã rẽ, không phải hai chỗ rẽ",
     len(_cha) == 1 and sum(1 for e in _bc.canh if e["from"] == _cha[0]) == 2)

_hai = [s for s in _bc.khoi if s["id"] in
        {e["to"] for e in _bc.canh if e["from"] == _cha[0]}]
kiem("và LỆCH NHAU theo trục dọc (§17 đọc toạ độ để biết thử nhánh nào trước)",
     _hai[0]["pos"][1] != _hai[1]["pos"][1],
     f"— y = {_hai[0]['pos'][1]} và {_hai[1]['pos'][1]}")
kiem("⭐ bộ chạy đọc ngã rẽ này là HOẶC (chọn MỘT), không phải VÀ (làm hết)",
     not core.la_nga_re_va(_hai))

_bc.di(nb.CHI_SO[("vao_lenh", "ban", "market", "close", 1.5, 2.0, 0.5)])
_bc.di(nb.CHI_SO[("het",)])
_bc.di(nb.CHI_SO[("het",)])
kiem("sơ đồ có phép chia QUA soát tĩnh, 0 lỗi 0 cảnh báo",
     _bc.xong and not core.validate_process(_bc.tai_lieu()),
     f"— {[x['message'][:60] for x in core.validate_process(_bc.tai_lieu())][:2]}")

# ---- chiều ngược: một sơ đồ ↔ một chuỗi ----
_c_nguoc, _ = nb.doc_nguoc(_bc.tai_lieu())
kiem("⭐ đọc ngược ra nước CHIA, không phải hai `mo_nhanh` (một sơ đồ, một chuỗi)",
     _CHIA_MAU in [nb.KHO_NUOC_DI[i] for i in _c_nguoc]
     and nb.CHI_SO[("mo_nhanh",)] not in _c_nguoc,
     f"— {[nb.KHO_NUOC_DI[i][0] for i in _c_nguoc]}")
kiem("và chuỗi ấy dựng lại ĐÚNG sơ đồ vừa đọc",
     hinh(nb.dung(_c_nguoc)) == hinh(_bc.tai_lieu()))
kiem("mọi nước trong chuỗi đọc ngược đều HỢP LỆ với mặt nạ", _hop_le_ca_chuoi(_c_nguoc))

# ---- luật QUAN TRỌNG NHẤT: phải còn được quyền KHÔNG LÀM GÌ ----
# Hai vế phủ kín nên LUÔN có đúng một vế khớp. Một cái cây toàn phép chia thì nến nào
# cũng rơi xuống một hành động — đó là máy nã lệnh, không phải chiến lược. Đo được khi
# thiếu luật này: 146/400 sơ đồ có đường tới hành động không qua một cái lọc nào.
kiem("KHÔNG chia ngay dưới khối Bắt đầu (phải có một cái LỌC ở trên)",
     not nb.mat_na(nb.Ban())[nb.CHI_SO[_CHIA_MAU]])

_rng6 = random.Random(7)
_na = 0
_la1 = 0
for _ in range(120):
    _d, _ = sinh_that(_rng6)
    if _d is None:
        continue
    if _co_duong_khong_loc(_d):
        _na += 1
    _g = _d[core.TAB_ENTRY]
    _co = {e["from"] for e in _g["edges"]}
    _la1 += sum(1 for s in _g["steps"] if s["id"] not in _co) == 1
kiem("⭐ MỌI đường tới hành động đều qua ít nhất một cái LỌC", not _na,
     f"— {_na}/120 sơ đồ nã lệnh")
kiem("⭐ và Entry thôi là một sợi dây — trước khi có phép chia là 65,8% một lá",
     _la1 < 12, f"— {_la1}/120 sơ đồ chỉ có một lá")

# ---- ngõ cụt: chia LỒNG NHAU vẫn đi tới đích ----
# Mỗi phép chia đang treo NỢ hai khối chưa đặt xuống. Đặt chỗ theo từng nước thì ba
# phép chia lồng nhau cùng tranh MỘT quỹ và đều thấy đủ — đo được 60/60 lượt đi kẹt.
_rng7 = random.Random(99)
_ket7 = _sau7 = 0
for _ in range(80):
    _d7, _c7 = sinh_that(_rng7)
    if _d7 is None:
        _ket7 += 1
        continue
    _sau7 = max(_sau7, sum(1 for i in _c7 if nb.KHO_NUOC_DI[i][0] in nb._CHIA))
kiem("chia LỒNG NHAU không đẻ ra ngõ cụt", not _ket7,
     f"— {_ket7}/80 kẹt · sâu nhất {_sau7} phép chia trong một sơ đồ")

# ---- luật `dk_hop_le` (tìm ra lúc làm phép chia) ----
# `normalize_action` ép danh sách HỢP LỆ luôn so với một LƯỢNG, và nói rõ vì sao. Người
# bày phải nói cùng câu — không thì `cong_zone → dk_ds → hop_le → dk_gia` đi lọt sạch
# mặt nạ rồi bị người soát mắng. Lỗi này CÓ TRƯỚC phép chia.
_bh = nb.Ban()
for _n in [("cong_zone",), ("dk_ds", "zone_da_sinh_lenh", "la_dung"), ("hop_le",)]:
    _bh.di(nb.CHI_SO[_n])
_mnh = nb.mat_na(_bh)
kiem("⚠ danh sách HỢP LỆ không nhận `dk_gia` (nó luôn so với một LƯỢNG)",
     not [i for i, x in enumerate(_mnh) if x and nb.KHO_NUOC_DI[i][0] == "dk_gia"])
kiem("nhưng vẫn nhận phép đếm bình thường",
     any(x for i, x in enumerate(_mnh) if nb.KHO_NUOC_DI[i][0] == "dk_so"))


print(f"\n{'=' * 68}")
print(f"  {dung}/{dung + sai} kiểm qua" if not sai else f"  ✘ {sai} bài HỎNG")
print("=" * 68)
sys.exit(1 if sai else 0)
