"""NGƯỜI BÀY — sinh ra sơ đồ, và đọc ngược sơ đồ thành chuỗi nước đi.

    core.md §18.7

`core.validate_flow_graph` là NGƯỜI SOÁT: vẽ xong rồi mới nói đúng/sai. Module này là
NGƯỜI BÀY: sơ đồ đang dở thì **bày ra nước đi nào còn hợp lệ**. Cùng một tri thức, đổi
hình dạng — và hình dạng này mới là thứ mọi cách tìm dùng được.

Ba điều đã chốt ở §18.7, cả ba nằm trong đây:

  1. **Sơ đồ = MỘT chuỗi nước đi.** Chuỗi ấy vừa để lưu, vừa để dựng lại y hệt, vừa để
     đột biến, vừa để cho mạng đọc. Không có bản thứ hai phải giữ đồng bộ bằng tay.

  2. **`KHO_NUOC_DI` CỐ ĐỊNH + `mat_na()` thay đổi.** Danh sách không bao giờ co giãn;
     mỗi bước chỉ bật vài ô. Mạng nơ-ron bắn xác suất trên một danh sách cố định — danh
     sách co giãn mỗi bước thì không đầu ra nào khớp được. Dò ngẫu nhiên và tiến hoá
     thì kiểu nào cũng chạy, nên viết đúng ngay từ đầu KHÔNG tốn thêm gì.

  3. **Đi được HAI CHIỀU.** `Ban.di()` là chiều xuôi (sinh), `doc_nguoc()` là chiều
     ngược (đọc sơ đồ vẽ tay ra chuỗi). Chiều ngược mở ra việc cho máy học từ sơ đồ
     người dùng đã vẽ, thay vì mò từ số không — và nó cho luôn một bài kiểm không có
     cách nào kiểm khác: đọc ngược rồi dựng xuôi phải ra ĐÚNG sơ đồ cũ.

⚠ **KHO_NUOC_DI sinh từ `kho.TOAN_HANG` × `THANG`, KHÔNG gõ tay.** Thêm một toán hạng
vào kho là kho nước đi tự lớn. Chép một bản thứ hai ở đây là dựng lại đúng cái bẫy
`CAN_ZONE` và `MOC_ENTRY` đã cắn một lần (§15.8).

⚠ **Đổi `THANG` là đổi `KHO_NUOC_DI`.** Với dò ngẫu nhiên và tiến hoá thì vô hại; với
một mạng đã học rồi thì phải học lại. Đừng đổi giữa chừng một phiên học (§18.7.2).

⭐ **Thứ bổ nghĩa là nước đi RIÊNG, không nhân vào nước chính.** Khung giờ, chu kỳ chỉ
báo, đệm vào lệnh — nếu nhét vào chính nước `dk_so` thì kho phình từ 462 lên hơn hai
vạn. Tách ra thì chúng chỉ CỘNG thêm vài chục ô, mà vẫn diễn tả đủ. Đây là chỗ quyết
định kho ở lại cỡ nghìn hay nhảy lên cỡ vạn.

NGỮ PHÁP — sơ đồ là một CÂY, viết theo lối duyệt sâu:

    nhip M5
    cong_zone                             ← cổng này ĐỊNH NGHĨA zone
    dk  atr < 0,75 × ATR nền
      tf_trai M5 · chu_ky_trai 14         ← bổ nghĩa cho điều kiện vừa thêm
    hop_le                                ← từ đây là danh sách "zone hợp lệ" (§12.6f)
    dk  zone_dem ≥ 8
    cong_moi                              ← chốt cổng, cổng sau là khối MỚI
    dk  zone_hop_le là ĐÚNG
    mo_nhanh                              ← rẽ tại đây
      dk  close > ma · tf_trai M15 · tf_phai M15 · chu_ky_phai 50
      vao_lenh mua · stop · zone_HH · SL 1,5 · TP 2R · rủi ro 0,5%
      dem 0,1
    dong_nhanh                            ← hết nhánh, quay về chỗ rẽ
    mo_nhanh …
    het                                   ← xong sơ đồ này, sang sơ đồ sau

`mo_nhanh`/`dong_nhanh` là một cặp ngoặc, nên diễn tả được mọi cây.
"""
from . import core, kho

# ---------------------------------------------------------------------------
# THANG SỐ — core.md §18.1
# ---------------------------------------------------------------------------
#
# ⭐ Máy KHÔNG dò số tự do, nó chọn nấc. Đo được: dò SL thang mịn bước 0,1 trên 2025 ra
# `2,7` (+58,23 R năm đó) nhưng sang ba năm chưa thấy thì THUA cả bản thô `3,0`
# (−13,30 R so với −8,65 R). Hai nấc cạnh nhau lệch trung bình 5,11 R — đó là NHIỄU.
#
# ⚠ Đây KHÔNG phải hàng rào chống overfit chính. Chuẩn hoá (§15) làm con số mang cùng
# nghĩa sang thị trường khác; nó KHÔNG cứu khỏi việc khớp với chính bộ dữ liệu đã dùng
# để chọn. Hàng rào chính là dữ liệu chưa thấy (§18.3). Thang thô chỉ đỡ gánh cho nó.
THANG = {
    "nguong": (0.25, 0.5, 0.75, 1.0, 1.5, 2.0),     # ngưỡng cổng, theo đơn vị toán hạng
    "sl": (0.5, 1.0, 1.5, 2.0, 3.0),
    "tp": (1.0, 1.5, 2.0, 3.0, 5.0),                # × R
    "rui_ro": (0.25, 0.5, 1.0),                     # % vốn
    "boi_R": (0.5, 1.0, 1.5, 2.0, 3.0),             # lãi đang có, × R
    "dem_nen": (1, 2, 3, 5, 8, 10, 13),
    "dem_lenh": (0, 1, 2, 3, 5),
    "pt_von": (5.0, 10.0, 20.0, 30.0),              # sụt vốn %
    "dem_vao": (0.1, 0.25, 0.5, 1.0),               # đệm quanh mốc neo, × ATR
    # CHU KỲ chỉ báo. Có mặt vì sơ đồ người vẽ CÓ đặt nó (ATR 14, MA 50) và chiều ngược
    # phải đọc được — nhưng để thưa, đúng tinh thần §18.1: nó là con số, không phải
    # cái thước (`CHU_KY_ATR_NEN` mới là thước, và nó cố định).
    "chu_ky": (5, 10, 14, 20, 50, 100, 200),
}

#: Nấc nào hợp với toán hạng nào — suy từ `loai`/`don_vi` của kho, không khai tay.
_THANG_THEO_DON_VI = {"nen": "dem_nen", "lenh": "dem_lenh", "pt_von": "pt_von"}

#: Phép so cho toán hạng SỐ. `la_dung`/`la_sai` cố ý đứng ngoài — chúng chỉ dành cho
#: toán hạng đúng/sai, và bày một lựa chọn vô nghĩa rồi để soát tĩnh mắng là tệ hơn
#: không bày (bất biến "chỉ bày ra thứ dùng được").
PHEP_SO_HOC = tuple(k for k in core.PHEP_SO if k not in core.PHEP_KHONG_VE_PHAI)

#: CẶP PHÉP của một nước CHIA — `(vế thuận, vế ngược)`. Hai vế phải **phủ kín**: không
#: giá trị nào lọt ra ngoài cả hai, không giá trị nào rơi vào cả hai.
#:
#: ⭐ Đây là chỗ `chia` khác hẳn `dk`: thêm một điều kiện là VỨT phần không khớp, còn
#: chia là GIỮ cả hai bên. Nối bốn cổng thì vùng còn lại co bốn lần và số lệnh rụng
#: theo — chia bốn lần thì tổng số lệnh KHÔNG ĐỔI, chỉ chi tiết hơn. Đo được: 263/400
#: sơ đồ máy vẽ chỉ có ĐÚNG MỘT đường ở Entry, tức một cái lọc chứ không phải chiến lược.
#:
#: ⚠ Cố ý KHÔNG có `==`/`!=`: một vế của phép chia ấy gần như rỗng, tức nó là cái lọc
#: đội lốt phép chia — đúng thứ đang phải dẹp.
PHEP_CHIA = ((">", "<="), (">=", "<"))
#: Vế thuận → vế ngược. Cùng nguồn với `PHEP_CHIA`, không khai bản thứ hai.
PHEP_NGUOC = dict(PHEP_CHIA)

#: `key → (chùm, cực trị)`. Hỏi kho, không khai bản thứ hai.
_CHUM = {t["key"]: (t.get("chum"), t.get("cuc")) for t in kho.TOAN_HANG}
#: Toán hạng nào chỉ CÓ SỐ sau khi đã có khối Vào lệnh.
SINH_BOI_LENH = frozenset(t["key"] for t in kho.TOAN_HANG
                          if t.get("sinh_boi") == "vao_lenh")


def quan_he_co_dinh(a, b):
    """Quan hệ giữa hai mức giá này đã CỐ ĐỊNH chưa — tức hỏi nó là hỏi hằng số?

    ⭐ Suy từ đúng hai trường kho khai (`chum`, `cuc`), không có bảng liệt kê nào ở đây.
    Thêm một mức giá mới vào kho là luật tự phủ tới nó.

        cùng chùm + ít nhất một bên là CỰC TRỊ  →  cố định
        `Giá cao nhất ≥ Giá đóng cửa`               đúng theo định nghĩa cây nến
        `Zone đỉnh ≥ Zone đáy`                      đúng theo định nghĩa vùng

    ⚠ `open` với `close` đều KHÔNG phải cực trị nên KHÔNG cố định — `open < close` là
    *"nến xanh"*, một câu hỏi thật. Đây là phép thử của cả cách khai: khai đúng thì luật
    tự chừa nó ra.

    ⚠ CÙNG MỘT LÚC mới cố định. Hai cây nến khác khung giờ là hai cây khác nhau — bộ
    chạy đọc nến ĐÃ ĐÓNG của từng khung, không cái nào bọc cái nào. Nên với chùm có
    khung giờ, luật này chỉ áp khi hai vế cùng khung; chùm không có khung giờ (`zone`)
    thì không tách được, và nước đi ấy bị gạch thẳng khỏi kho."""
    ca, xa = _CHUM.get(a, (None, None))
    cb, xb = _CHUM.get(b, (None, None))
    return bool(ca) and ca == cb and bool(xa or xb)


#: Toán hạng nào có ô `period` — hỏi kho, không khai tay.
CO_CHU_KY = tuple(t["key"] for t in kho.TOAN_HANG if "period" in (t.get("tham_so") or ()))
#: Toán hạng nào có ô `tf`.
CO_TF = tuple(t["key"] for t in kho.TOAN_HANG if "tf" in (t.get("tham_so") or ()))
#: `method` của MA cố ý KHÔNG thành nước đi — SMA là mặc định hợp lý, và mỗi nút thêm
#: vào là một chiều nữa cho máy mài. Sơ đồ người vẽ cũng chỉ dùng SMA.
PP_MA = "SMA"


def _thang_cho(t):
    """Thang số hợp với toán hạng `t`, hoặc `None` nếu nó không so với một con số."""
    loai = t.get("loai")
    if loai == "dung_sai":
        return None                     # không có vế phải — chỉ `la_dung` / `la_sai`
    if loai == "muc_gia":
        return None                     # mức giá so với MỨC GIÁ khác, xem `dk_gia`
    if loai == "boi_R":
        return THANG["boi_R"]
    if loai == "dem":
        return THANG.get(_THANG_THEO_DON_VI.get(t.get("don_vi"), ""))
    if loai == "khoang_cach":
        return THANG["nguong"]
    return None


def _thang_ten(key):
    """Toán hạng này so với thang nào — cùng nguồn với `_thang_cho`, tra bằng tên."""
    t = next((x for x in kho.TOAN_HANG if x["key"] == key), None)
    if t is None:
        raise KhongDocDuoc(f"Toán hạng `{key}` không có trong kho.")
    loai = t.get("loai")
    if loai == "boi_R":
        return "boi_R"
    if loai == "dem":
        ten = _THANG_THEO_DON_VI.get(t.get("don_vi"))
        if ten is None:
            raise KhongDocDuoc(f"Toán hạng `{key}` đếm bằng đơn vị chưa có thang.")
        return ten
    return "nguong"


# ---------------------------------------------------------------------------
# KHO NƯỚC ĐI — cố định, sinh từ kho × thang
# ---------------------------------------------------------------------------
#
# Mỗi nước đi là một `tuple` bất biến, phần tử đầu là LOẠI. Dùng tuple chứ không dict
# để nó băm được và so sánh được — chuỗi nước đi phải là thứ đem đi so, đem đi lưu.
#
#   ("nhip", tf)
#   ("dk_so",  key, phep, gia_tri, don_vi|None)   toán hạng ⋈ một LƯỢNG
#   ("dk_gia", key, phep, key2)                   mức giá ⋈ MỨC GIÁ khác
#   ("dk_ds",  key, phep)                         toán hạng đúng/sai
#   ("tf_trai"|"tf_phai", tf)                     bổ nghĩa điều kiện vừa thêm
#   ("chu_ky_trai"|"chu_ky_phai", n)
#   ("vao_lenh", huong, loai, moc, sl, tp, rui_ro)
#   ("dem", v)                                    đệm cho khối Vào lệnh vừa thêm
#   ("sua_lenh", che_do, khoang|None)
#   ("chia_so",  key, phep, gia_tri, don_vi|None)  CHIA ĐÔI theo một LƯỢNG
#   ("chia_gia", key, phep, key2)                 chia đôi theo mức giá khác
#   ("chia_ds",  key)                             chia đôi theo đúng/sai
#   ("cong_moi",) ("cong_zone",) ("hop_le",) ("mo_nhanh",) ("dong_nhanh",) ("het",)


def _CO_TF_CHUM(a, b):
    """Hai vế này có TÁCH RA hai lúc khác nhau được không (cả hai đều có khung giờ)."""
    return a in CO_TF and b in CO_TF


def _kho_dieu_kien():
    ra = []
    gia = [t for t in kho.TOAN_HANG if t.get("loai") == "muc_gia"]
    for t in kho.TOAN_HANG:
        k = t["key"]
        if t.get("loai") == "dung_sai":
            ra += [("dk_ds", k, p) for p in core.PHEP_KHONG_VE_PHAI]
            continue
        if t.get("loai") == "muc_gia":
            # So hai MỨC GIÁ với nhau. Không so với số: `close < 2000` là một con số
            # tuyệt đối, đúng thứ §15 dựng lên để cấm.
            # ⚠ GẠCH THẲNG KHỎI KHO, không che bằng mặt nạ: cặp cố định mà KHÔNG có
            # khung giờ thì không đời nào tách ra thành câu hỏi được, nên nó không phải
            # một nước đi đang tạm không dùng — nó không phải nước đi.
            ra += [("dk_gia", k, p, u["key"]) for p in PHEP_SO_HOC
                   for u in gia
                   if u["key"] != k and not (not _CO_TF_CHUM(k, u["key"])
                                             and quan_he_co_dinh(k, u["key"]))]
            continue
        thang = _thang_cho(t)
        if not thang:
            continue
        # ĐƠN VỊ của vế phải. `don_vi_cho` đã lọc sẵn cái nào có nghĩa cho toán hạng
        # này; `gia` (tuyệt đối) bị bỏ vì cùng lý do trên. Toán hạng ĐẾM thì không có
        # đơn vị nào — 3 nến là 3 nến.
        dvs = [None] if t.get("loai") == "dem" else (
            [d for d in core.don_vi_cho(k) if d != "gia"] or [None])
        ra += [("dk_so", k, p, g, d) for p in PHEP_SO_HOC for g in thang for d in dvs]
    return ra


def _kho_chia():
    """Nước CHIA — một phép so **và phủ định của nó**, đẻ ra hai vế cùng một lúc.

    Cùng nguồn với `_kho_dieu_kien`: cùng kho toán hạng, cùng thang số, cùng luật đơn
    vị. Khác đúng hai chỗ — chỉ lấy MỘT phép mỗi cặp (vế kia suy ra được; bày cả hai là
    hai cái tên cho một phép chia), và không có `==`."""
    ra = []
    gia = [t for t in kho.TOAN_HANG if t.get("loai") == "muc_gia"]
    for t in kho.TOAN_HANG:
        k = t["key"]
        if t.get("loai") == "dung_sai":
            # Đúng/sai chia sẵn làm đôi rồi — không phải chọn phép, cũng không có ngưỡng.
            ra.append(("chia_ds", k))
            continue
        if t.get("loai") == "muc_gia":
            ra += [("chia_gia", k, p, u["key"]) for p, _ in PHEP_CHIA
                   for u in gia
                   if u["key"] != k and not (not _CO_TF_CHUM(k, u["key"])
                                             and quan_he_co_dinh(k, u["key"]))]
            continue
        thang = _thang_cho(t)
        if not thang:
            continue
        dvs = [None] if t.get("loai") == "dem" else (
            [d for d in core.don_vi_cho(k) if d != "gia"] or [None])
        ra += [("chia_so", k, p, g, d) for p, _ in PHEP_CHIA for g in thang
               for d in dvs]
    return ra


def _kho_bo_nghia():
    ra = [(v, tf) for v in ("tf_trai", "tf_phai") for tf in core.TIMEFRAMES]
    ra += [(v, n) for v in ("chu_ky_trai", "chu_ky_phai") for n in THANG["chu_ky"]]
    ra += [("dem", v) for v in THANG["dem_vao"]]
    return ra


def _kho_hanh_dong():
    ra = []
    for h in core.HUONG:
        for l in core.LOAI_LENH:
            # ⚠ Lệnh THỊ TRƯỜNG chỉ có một mốc neo có nghĩa: giá hiện tại. Cho nó chọn
            # trong sáu mốc là bày ra năm nước đi TRÙNG NHAU — `normalize_action` ép
            # về `close` hết. Kho nước đi có hai ô cho cùng một sơ đồ là mạng học một
            # thứ bằng hai đường, và chuỗi mất tính duy nhất.
            mocs = ["close"] if l == "market" else list(core.MOC_ENTRY)
            ra += [("vao_lenh", h, l, m, sl, tp, rr) for m in mocs
                   for sl in THANG["sl"] for tp in THANG["tp"] for rr in THANG["rui_ro"]]
    for cd in core.SUA_CHE_DO:
        if cd in core.SUA_CAN_GIA:
            ra += [("sua_lenh", cd, g) for g in THANG["sl"]]
        else:
            ra.append(("sua_lenh", cd, None))
    return ra


CAU_TRUC = ("cong_moi", "cong_zone", "hop_le", "mo_nhanh", "dong_nhanh", "het")

KHO_NUOC_DI = tuple(
    [("nhip", tf) for tf in core.TIMEFRAMES]
    + _kho_dieu_kien() + _kho_chia() + _kho_bo_nghia() + _kho_hanh_dong()
    + [(c,) for c in CAU_TRUC])

#: nước đi → chỉ số. Chiều ngược cần nó, và nó cũng là phép kiểm không có trùng lặp.
CHI_SO = {n: i for i, n in enumerate(KHO_NUOC_DI)}
assert len(CHI_SO) == len(KHO_NUOC_DI), "KHO_NUOC_DI có nước đi TRÙNG"

_DK = ("dk_so", "dk_gia", "dk_ds")
_CHIA = ("chia_so", "chia_gia", "chia_ds")

#: XẾP CHỖ trên canvas. Không phải chuyện thẩm mỹ: §17 đọc toạ độ để biết nhánh nào
#: được thử trước (`_khoa_nhanh`), nên đây là một phần của NGHĨA sơ đồ. Lấy đúng bước
#: mà sơ đồ mẫu đang dùng, để sơ đồ máy vẽ mở ra trông y như sơ đồ vẽ tay.
X0, Y0, BUOC_X, BUOC_Y = 40.0, 300.0, 300.0, 280.0

#: TRẦN ĐỘ PHỨC TẠP — core.md §15.5. Bốn số, KHÔNG cộng thành một điểm: cộng lại thì
#: lúc vượt trần không biết cái gì vượt.
#:
#: ⚠ **Trần chỉ áp cho MÁY.** `validate_process` không có luật nào như thế và sẽ không
#: bao giờ có — người vẽ 28 khối thì biết mình đang làm gì, máy sinh 28 khối là nó bịa.
#: Vì thế trần nằm ở ĐÂY (người bày) chứ không ở người soát.
#:
#: ⚠ Và nó là CÀI ĐẶT, không phải luật: tầng CHỌN (§18.6.1) chỉnh được. Nên `mat_na`
#: nhận nó làm tham số thay vì đọc hằng số — nới trần không làm một con số nào trong
#: sơ đồ đổi nghĩa, nên không đụng luật "cái thước không được là tham số" (§15.1).
#:
#: Số `4` không bốc ra: đúng bằng chỗ nhiều nhất người dùng từng viết tay.
TRAN = {"dk_moi_cong": 4, "nhanh_moi_re": 3, "khoi_entry": 12, "khoi_manage": 8}


# ---------------------------------------------------------------------------
# BÀN — một chiến lược đang dựng
# ---------------------------------------------------------------------------


class Ban:
    """Entry dựng trước, `het` thì sang Manage, `het` lần nữa là xong.

    Giữ ĐỦ thứ để `mat_na` trả lời được mà không phải dò lại đồ thị mỗi bước — dò lại
    là O(n²) trên thứ sẽ chạy hàng triệu lần."""

    __slots__ = ("chuoi", "tab", "so_do", "khoi", "canh", "diem", "ngan_xep",
                 "cong", "ds", "dk", "dk_doi", "hd", "co_zone", "co_nhip", "xong",
                 "x", "y", "dem_nhanh", "cuoi", "co_con", "co_hop_le",
                 "zone_o_entry", "hop_le_o_entry")

    def __init__(self):
        self.chuoi = []                 # [chỉ số nước đi]
        self.tab = 0
        self.so_do = {t: {"steps": [], "edges": []} for t in core.TABS}
        self.xong = False
        #: Entry đã đặt cổng zone chưa — THEO CẢ CHIẾN LƯỢC. §12.6d: cổng zone nằm ở
        #: Entry mà Manage vẫn ĐỌC được zone; đặt lại theo tab thì `lenh_thuoc_zone`
        #: (toán hạng chỉ có ở Manage, lại cần zone) vĩnh viễn không dùng được.
        self.zone_o_entry = self.hop_le_o_entry = False
        self._mo_tab()

    # ---- dựng ----
    def _mo_tab(self):
        t = core.TABS[self.tab]
        bd = core.make_start_step(nhip=core.NHIP_MAC_DINH[t])
        bd["pos"] = [X0, Y0]
        self.so_do[t] = {"steps": [bd], "edges": []}
        self.khoi = self.so_do[t]["steps"]
        self.canh = self.so_do[t]["edges"]
        self.diem = bd["id"]
        self.cuoi = None                # LOẠI của khối đang ở `diem` (None = Bắt đầu)
        self.co_con = set()             # id nào đã có đường nối đi ra
        self.x, self.y, self.dem_nhanh = X0 + BUOC_X, Y0, {}
        self.ngan_xep = []              # chỗ rẽ đang mở
        self.cong = None                # cổng đang mở, còn nhận thêm điều kiện
        self.ds = "conditions"          # cổng đang mở đang điền danh sách nào
        self.dk = None                  # điều kiện vừa thêm (chỗ bổ nghĩa bám vào)
        #: VẾ NGƯỢC của phép chia vừa đi — CÙNG MỘT đối tượng với điều kiện nằm trong
        #: khối đang chờ trên ngăn xếp, nên bổ nghĩa `self.dk` là phải bổ nghĩa cả nó.
        #: Hai vế chia đôi cùng một toán hạng thì khung giờ và chu kỳ bắt buộc giống
        #: nhau — lệch một cái là hai vế thôi phủ kín, và cái lọt ra giữa đúng bằng thứ
        #: phép chia sinh ra để xoá.
        self.dk_doi = None
        self.hd = None                  # khối Vào lệnh vừa thêm (chỗ `dem` bám vào)
        self.co_nhip = False
        # ⭐ `co_zone` và `co_hop_le` đi theo VỊ TRÍ, không theo cả sơ đồ: chúng được
        # cất vào ngăn xếp lúc `mo_nhanh` và lấy lại lúc `dong_nhanh`.
        #
        # ⚠ Đây là chỗ đã cắn: để chúng toàn cục thì một nhánh SONG SONG với cổng zone
        # vẫn tưởng mình có zone — mà §12.6c đòi khối phải nằm SAU cổng zone trên đồ
        # thị, chứ không phải "sơ đồ có một cổng zone ở đâu đó". Đo được 11 lỗi
        # *"đọc Zone … nhưng KHÔNG nằm sau cổng zone"* trên 60 sơ đồ sinh tự động.
        #
        # Manage thì kế thừa từ Entry (§12.6d) — nó không có cổng zone của riêng mình.
        self.co_zone = bool(self.tab) and self.zone_o_entry
        self.co_hop_le = bool(self.tab) and self.hop_le_o_entry

    def _gan(self, st):
        """Treo một khối vào điểm hiện tại rồi dời điểm tới nó.

        ⚠ ĐẶT CHỖ luôn, không để giao diện tự xếp sau. §17 (`_lt_nhanh_ngang_nhau`)
        bắt lỗi khi hai đầu nhánh nằm ngang nhau: thứ tự thử nhánh do VỊ TRÍ quyết,
        nên nhánh không có toạ độ là thứ tự do `id` — một uuid không ai nhìn thấy.
        Sơ đồ máy vẽ mà không đặt chỗ thì mọi ngã rẽ đều là lỗi.

        ⚠ Phép dời chỗ nằm ĐÚNG MỘT NƠI, ở đây. Từng để nó trong `mo_nhanh` và sót
        đúng một đường: sau `dong_nhanh`, treo thẳng một khối lên chỗ rẽ (không qua
        `mo_nhanh`) cũng là đẻ ra một nhánh — mà nhánh ấy không được dời, nên nằm chồng
        khít lên nhánh trước. Đếm ở chỗ NỐI DÂY thì không có đường nào lọt."""
        k = self.dem_nhanh.get(self.diem, 0)
        self.dem_nhanh[self.diem] = k + 1
        self.y += k * BUOC_Y
        st["pos"] = [self.x, self.y]
        self.x += BUOC_X
        self.khoi.append(st)
        self.canh.append({"from": self.diem, "to": st["id"], "port": "out"})
        self.co_con.add(self.diem)
        self.diem, self.cuoi = st["id"], st["type"]
        return st

    def _het_cong(self):
        self.cong, self.ds, self.dk, self.hd = None, "conditions", None, None
        self.dk_doi = None

    # ---- một nước ----
    def di(self, i):
        """Đi nước thứ `i`. TẠI CHỖ — bàn dựng một lần rồi vứt, không cần bất biến.

        Không tự kiểm hợp lệ: gọi `mat_na` trước là việc của bên gọi. Kiểm hai lần thì
        vòng trong chạy chậm gấp đôi mà chẳng bắt thêm được gì."""
        n = KHO_NUOC_DI[i]
        self.chuoi.append(i)
        loai = n[0]

        if loai == "nhip":
            self.khoi[0]["nhip"] = n[1]
            self.co_nhip = True
        elif loai in _DK:
            if self.cong is None:
                self.cong = self._gan(core.make_action_step(
                    {"type": core.CHECK_COND, "conditions": []}))
            # ⚠ `dk_doi` phải theo `dk` như hình với bóng. Để nó sống sót qua một
            # điều kiện MỚI là bổ nghĩa của điều kiện ấy rơi vào vế ngược của phép chia
            # trước đó — hai điều kiện chẳng liên quan gì nhau.
            self.dk, self.dk_doi = _dieu_kien(n), None
            self.cong.setdefault(self.ds, []).append(self.dk)
            if loai == "dk_gia":
                self.cong["so_dai_luong"] = True
            if self.ds == "dk_hop_le":
                self.co_hop_le = self.hop_le_o_entry = True
            self.hd = None
        elif loai in ("tf_trai", "chu_ky_trai", "tf_phai", "chu_ky_phai"):
            ben = "trai" if loai.endswith("_trai") else "phai"
            khoa = "tf" if loai.startswith("tf") else "period"
            self.dk[ben][khoa] = n[1]
            if self.dk_doi is not None:
                self.dk_doi[ben][khoa] = n[1]
        elif loai == "vao_lenh":
            self._het_cong()
            _, h, l, m, sl, tp, rr = n
            self.hd = self._gan(core.make_action_step({
                "type": core.VAO_LENH, "huong": h, "loai": l, "rui_ro": rr,
                "entry": {"moc": m},
                "sl": {"tinh": "atr_zone" if self.co_zone else "atr", "value": sl},
                "tp": {"tinh": "R", "value": tp}}))
        elif loai == "dem":
            self.hd["dem"] = {"tinh": "atr", "value": n[1]}
        elif loai == "sua_lenh":
            self._het_cong()
            a = {"type": core.SUA_LENH, "che_do": n[1]}
            if n[2] is not None:
                a["khoang"] = {"tinh": "atr_zone" if self.co_zone else "atr",
                               "value": n[2]}
            self._gan(core.make_action_step(a))
        elif loai == "cong_moi":
            self._het_cong()
        elif loai == "cong_zone":
            self._het_cong()
            self.cong = self._gan(core.make_action_step(
                {"type": core.CHECK_COND, "conditions": [], "cong_zone": True}))
            self.co_zone = self.zone_o_entry = True
        elif loai == "hop_le":
            self.ds, self.dk, self.dk_doi = "dk_hop_le", None, None
        elif loai in _CHIA:
            self._het_cong()
            ca, cb = _cap_dk(n)
            co = {"so_dai_luong": True} if loai == "chia_gia" else {}
            # ⭐ Vế NGƯỢC dựng SẴN nhưng chưa treo lên — `dong_nhanh` mới treo. Nhờ vậy
            # thứ tự khối trong file đúng bằng lối duyệt sâu, tức `chia` và cặp
            # `mo_nhanh` viết tay ra CÙNG một sơ đồ, giống tới từng toạ độ.
            ve_nguoc = core.make_action_step(
                {"type": core.CHECK_COND, "conditions": [cb], **co})
            self.ngan_xep.append((self.diem, self.x, self.y, self.cuoi,
                                  self.co_zone, self.co_hop_le, ve_nguoc))
            self._gan(core.make_action_step(
                {"type": core.CHECK_COND, "conditions": [ca], **co}))
            # ⭐ NIÊM PHONG: `cong = None` nên không nước `dk_*` nào chui thêm vào được.
            # Thêm một điều kiện vào một vế là hai vế thôi phủ kín, và cái lọt ra giữa
            # đúng bằng thứ phép chia sinh ra để xoá. Vẫn giữ `dk` để bổ nghĩa bám vào —
            # khung giờ và chu kỳ vẫn phải điền, và điền MỘT lần cho cả hai vế.
            self.cong = None
            self.dk, self.dk_doi = ca, ve_nguoc["conditions"][0]
        elif loai == "mo_nhanh":
            self._het_cong()
            # Nhớ chỗ để quay về, KÈM `co_zone`/`co_hop_le`: chúng đi theo vị trí, nên
            # nhánh sau không được thừa hưởng cổng zone của nhánh trước. Ô cuối là VẾ
            # NGƯỢC đang chờ — `mo_nhanh` không có vế nào nên `None`.
            self.ngan_xep.append((self.diem, self.x, self.y, self.cuoi,
                                  self.co_zone, self.co_hop_le, None))
        elif loai == "dong_nhanh":
            self._het_cong()
            (self.diem, self.x, self.y, self.cuoi,
             self.co_zone, self.co_hop_le, ve_nguoc) = self.ngan_xep.pop()
            if ve_nguoc is not None:
                # Đóng vế THUẬN là mở ngay VẾ NGƯỢC. Cặp này sinh ra cùng nhau và không
                # bao giờ đứng một mình — đó là cả nghĩa của phép chia.
                self._gan(ve_nguoc)
        elif loai == "het":
            self._het_cong()
            if self.tab + 1 < len(core.TABS):
                self.tab += 1
                self._mo_tab()
            else:
                self.xong = True
        return self

    # ---- kết quả ----
    def tai_lieu(self, ten="Máy vẽ", dat_ten=True):
        """Chuỗi nước đi → tài liệu chiến lược BÌNH THƯỜNG (§18.6.5).

        Không có loại "sơ đồ của máy": cùng JSON, cùng cửa sổ vẽ, cùng Tester."""
        d = core.normalize_process(
            {"name": ten, "tham_so": [], **{t: self.so_do[t] for t in core.TABS}})
        return _du_tham_so(_dat_ten_so_lap(d) if dat_ten else d)


def _du_tham_so(doc):
    """Điền sẵn `core.THAM_SO_NGAM` — thứ bộ chạy đọc mà không khối nào gọi tên.

    Thiếu là `LoiChay` ngay khi dựng chương trình. Hỏi `core` chứ không viết tay tên
    nào: danh sách đổi thì chỗ này tự theo."""
    co = {t["ten"] for t in doc["tham_so"]}
    them = [core.make_tham_so(k, "chu kỳ ATR", 14, "nen")
            for k in core.THAM_SO_NGAM if k not in co]
    if not them:
        return doc
    return core.normalize_process({**doc, "tham_so": doc["tham_so"] + them})


def _dat_ten_so_lap(doc):
    """Số nào xuất hiện ≥2 chỗ CÙNG VAI thì hoá thành một tham số có tên.

    ⚠ Không phải chuyện thẩm mỹ. §18.6.5 nói sơ đồ máy vẽ là file bình thường và người
    dùng **sẽ sửa tay nó**. Hai ô cùng giữ số `1,5`, sửa một ô quên ô kia, thì chiến
    lược lệch ÂM THẦM — không lỗi, chỉ là kết quả khác đi. Chính `_soat_so_lap` sinh ra
    để cảnh báo chuyện đó; máy đẻ ra sơ đồ dính sẵn bảy cảnh báo ấy là máy đẻ ra việc.

    ⭐ Nhóm và đặt tên đều lấy từ `core.di_o_so` — nơi DUY NHẤT biết ô số nào ở đâu và
    nên gọi là gì. Ở đây chỉ ghi vào, không tự nghĩ ra tên nào."""
    nhom = {}
    for r in core.di_o_so(doc):
        if isinstance(r["gia_tri"], str):
            continue                                   # ô đang giữ một cái tên rồi
        nhom.setdefault(r["khoa"], []).append(r)
    them, da_dung = [], set()
    for ds in nhom.values():
        if len(ds) < 2:
            continue
        r = ds[0]
        ten = r["goi_y"]
        while ten in da_dung:                          # hai vai khác nhau, tên gợi ý trùng
            ten += "_"
        da_dung.add(ten)
        them.append(core.make_tham_so(ten, r["nhan"], r["gia_tri"], r["don_vi"]))
        for x in ds:
            _ghi(doc, x["tab"], x["step"], x["duong"], ten)
    if not them:
        return doc
    return core.normalize_process({**doc, "tham_so": doc["tham_so"] + them})


def _ghi(doc, tab, sid, duong, gt):
    """Ghi `gt` vào ô mà `di_o_so` đã chỉ sẵn đường tới."""
    o = next(s for s in doc[tab]["steps"] if s.get("id") == sid)
    for k in duong[:-1]:
        o = o[k]
    o[duong[-1]] = gt


def _o(ten):
    """Ô toán hạng mới. `method` điền luôn — SMA là mặc định hợp lý, và mỗi nút thêm
    vào là một chiều nữa cho máy mài. Sơ đồ người vẽ cũng chỉ dùng SMA."""
    o = {"ten": ten}
    if "method" in core.TOAN_HANG_THAMSO.get(ten, ()):
        o["method"] = PP_MA
    return o


def _dieu_kien(n):
    """Một nước `dk_*` → một điều kiện đúng hình dạng `normalize_action` chờ."""
    if n[0] == "dk_ds":
        return {"trai": _o(n[1]), "phep": n[2]}
    if n[0] == "dk_gia":
        return {"trai": _o(n[1]), "phep": n[2], "phai": _o(n[3])}
    _, k, p, g, d = n
    phai = {"value": g}
    if d:
        phai["tinh"] = d
    return {"trai": _o(k), "phep": p, "phai": phai}


def cap_chia(sa, sb):
    """Hai khối này có phải HAI VẾ của một phép chia không → `(thuận, ngược)` hoặc None.

    ⭐ ĐỊNH NGHĨA DUY NHẤT của *"phép chia"* khi nhìn vào một sơ đồ ĐÃ VẼ XONG. Chiều
    ngược (`_Doc.la_chia`) và cái đọc sơ đồ ra lời (`dien_giai`) đều hỏi ở đây. Hai bản
    định nghĩa thì sớm muộn một bản nhận rộng hơn bản kia — rồi sơ đồ hiện ra một đằng
    mà dựng lại một nẻo, đúng loại lệch im lặng khó tìm nhất.

    ⚠ CHẶT TAY: đúng thứ nước `chia` đẻ ra, không hơn. Cổng trần, đúng một điều kiện,
    cùng toán hạng, cùng lượng, và vế THUẬN đứng trước. Nhận rộng hơn là đọc một ngã rẽ
    bình thường thành phép chia."""
    for x in (sa, sb):
        if (not isinstance(x, dict) or x.get("type") != core.CHECK_COND
                or x.get("cong_zone") or x.get("dk_hop_le")
                or len(x.get("conditions") or ()) != 1):
            return None
    if bool(sa.get("so_dai_luong")) != bool(sb.get("so_dai_luong")):
        return None
    ca, cb = sa["conditions"][0], sb["conditions"][0]
    if ca.get("trai") != cb.get("trai") or ca.get("phai") != cb.get("phai"):
        return None
    pa, pb = ca.get("phep"), cb.get("phep")
    if pa in core.PHEP_KHONG_VE_PHAI:
        return (ca, cb) if (pa, pb) == ("la_dung", "la_sai") else None
    return (ca, cb) if (pa, pb) in PHEP_CHIA else None


def _cap_dk(n):
    """Nước `chia_*` → `(điều kiện vế THUẬN, điều kiện vế NGƯỢC)`.

    Đi qua đúng `_dieu_kien` như nước `dk_*` — một chỗ dựng điều kiện, không hai."""
    if n[0] == "chia_ds":
        return (_dieu_kien(("dk_ds", n[1], "la_dung")),
                _dieu_kien(("dk_ds", n[1], "la_sai")))
    if n[0] == "chia_gia":
        _, k, p, k2 = n
        return (_dieu_kien(("dk_gia", k, p, k2)),
                _dieu_kien(("dk_gia", k, PHEP_NGUOC[p], k2)))
    _, k, p, g, d = n
    return (_dieu_kien(("dk_so", k, p, g, d)),
            _dieu_kien(("dk_so", k, PHEP_NGUOC[p], g, d)))


# ---------------------------------------------------------------------------
# MẶT NẠ — §17 nhìn từ phía NGƯỜI BÀY
# ---------------------------------------------------------------------------
#
# ⚠ Đây là NGĂN TRƯỚC, không phải soát sau. Sơ đồ hỏng KHÔNG BAO GIỜ được sinh ra —
# thay vì sinh ra rồi tốn 17 giây backtest mới biết là rác (§18.5).

#: Toán hạng nào chỉ có nghĩa ở sơ đồ nào — lấy từ kho, không khai bản thứ hai.
_TAB_CUA = {t["key"]: tuple(t.get("tabs") or core.TABS) for t in kho.TOAN_HANG}


def mat_na(b, tran=None, tat=()):
    """Danh sách `bool` dài đúng `len(KHO_NUOC_DI)` — nước nào đi được LÚC NÀY.

    ⭐ Danh sách CỐ ĐỊNH, mặt nạ THAY ĐỔI. Đó là §18.7.2, và là lý do một mạng nơ-ron
    cắm vào được mà không phải sửa gì.

    `tran` — trần độ phức tạp (§15.5), `None` là lấy `TRAN`.
    `tat`  — THẺ người dùng không muốn dùng lần này (§18.6.1 tầng CHỌN). Xem `the()`.

    ⚠ `tat` là tầng CHỌN, KHÔNG phải tầng LUẬT: tắt một thứ chỉ là "lần này tôi không
    muốn dùng", không phải "cái này hỏng". Vì thế nó là tham số chứ không nằm trong
    `_duoc` — và tắt hết cũng không sao, mặt nạ vẫn còn đường về đích."""
    if b.xong:
        return [False] * len(KHO_NUOC_DI)
    c = _BoiCanh(b, tran or TRAN)
    tat = frozenset(tat or ())
    if not tat:
        return [_duoc(n, c) for n in KHO_NUOC_DI]
    return [False if tat & the(n) else _duoc(n, c) for n in KHO_NUOC_DI]


def the(n):
    """Nước đi này DÙNG những thẻ nào — tắt một thẻ là tắt mọi nước mang nó.

    ⭐ MỘT cơ chế cho MỌI thứ tầng CHỌN tắt được: toán hạng, khung giờ, mốc neo, hướng
    lệnh, loại lệnh, chế độ sửa, **và từng NẤC của thang số**.

    Nấc thang là chỗ đáng nói: tắt nấc `SL 0,5` không hề đụng tới `THANG` hay
    `KHO_NUOC_DI` — kho vẫn y nguyên 1.863 ô, chỉ là mấy ô mang thẻ `sl:0.5` bị mặt nạ
    che. Giữ được §18.7.2 (*danh sách CỐ ĐỊNH, mặt nạ thay đổi*) mà vẫn cho người dùng
    sửa thang: sửa thang thật thì một mạng đã học phải học lại, còn che mặt nạ thì không.
    """
    loai = n[0]
    if loai == "dk_so":
        # Tên thang THẬT của toán hạng ấy, không gộp hết vào "ngưỡng": `zone_dem` đo
        # bằng NẾN, `so_vi_the` bằng LỆNH, `drawdown_pt` bằng % VỐN, `lenh_lai_R` bằng
        # bội R. Gộp lại thì panel bày ra một cái thang trộn bốn đơn vị, vô nghĩa.
        return {f"th:{n[1]}", f"{_thang_ten(n[1])}:{n[3]}"}
    if loai == "dk_gia":
        return {f"th:{n[1]}", f"th:{n[3]}"}
    if loai in ("dk_ds", "chia_ds"):
        return {f"th:{n[1]}"}
    # Chia mang ĐÚNG thẻ của điều kiện nó dựng ra: tắt một toán hạng là tắt cả nước hỏi
    # nó lẫn nước chia theo nó. Một cơ chế, không hai.
    if loai == "chia_so":
        return {f"th:{n[1]}", f"{_thang_ten(n[1])}:{n[3]}"}
    if loai == "chia_gia":
        return {f"th:{n[1]}", f"th:{n[3]}"}
    if loai in ("nhip", "tf_trai", "tf_phai"):
        return {f"tf:{n[1]}"}
    if loai in ("chu_ky_trai", "chu_ky_phai"):
        return {f"chu_ky:{n[1]}"}
    if loai == "vao_lenh":
        _, h, l, m, sl, tp, rr = n
        return {f"huong:{h}", f"loai:{l}", f"moc:{m}",
                f"sl:{sl}", f"tp:{tp}", f"rui_ro:{rr}"}
    if loai == "dem":
        return {f"dem_vao:{n[1]}"}
    if loai == "sua_lenh":
        return {f"sua:{n[1]}"} | ({f"sl:{n[2]}"} if n[2] is not None else set())
    return frozenset()          # nước CẤU TRÚC — không tắt được, chúng là bộ xương


def _gom_the():
    """Mọi thẻ CÓ THẬT trong kho, gom theo nhóm — quét từ `KHO_NUOC_DI`, không gõ tay.

    ⚠ Quét chứ không liệt kê: thêm một toán hạng, một nấc thang, một chế độ sửa là
    panel tầng CHỌN có ngay. Gõ tay một bản thứ hai ở đây là dựng lại đúng cái bẫy
    `CAN_ZONE` và `MOC_ENTRY` đã cắn (§15.8)."""
    ra = {}
    for n in KHO_NUOC_DI:
        for t in the(n):
            nhom, gia = t.split(":", 1)
            ra.setdefault(nhom, set()).add(gia)
    return ra


#: `{nhóm thẻ: {giá trị}}` — nguồn của panel "Kho đồ" và "Thang số" ở cửa sổ RL.
THE_CHON = _gom_the()


#: Trường của ô toán hạng → tên nước đi bổ nghĩa nó.
_TEN_NUOC = {"tf": "tf", "period": "chu_ky"}


def _thieu_o(o):
    """Ô toán hạng còn THIẾU trường bắt buộc nào — `("tf",)`, `("period",)`, …

    ⚠ Đây là chỗ mặt nạ và soát tĩnh dễ lệch nhau nhất, và đo được: bỏ qua nó thì sinh
    bừa 60 sơ đồ ra 910 lỗi `chưa chọn khung thời gian`. `TOAN_HANG_THAMSO` là nguồn
    duy nhất nói toán hạng nào đòi trường nào — hỏi nó, đừng liệt kê lại."""
    if not isinstance(o, dict) or not o.get("ten"):
        return ()
    ra = []
    for k in core.TOAN_HANG_THAMSO.get(o["ten"], ()):
        if k == "tf" and o.get("tf") not in core.TIMEFRAMES:
            ra.append("tf")
        elif k == "period" and o.get("period") is None:
            ra.append("period")
    return tuple(ra)


class _BoiCanh:
    """Mọi thứ `_duoc` cần, tính MỘT lần cho cả mặt nạ thay vì mỗi nước một lần."""

    __slots__ = ("b", "tab", "trong_nhanh", "nhanh_rong", "dau", "kieu", "da_hoi",
                 "cong_du", "co_vao_lenh", "no", "cuoi_la_cong", "can_dem",
                 "lenh_tren_duong", "het_khoi", "het_cho_cong", "het_dk", "het_nhanh",
                 "con_sua_duoc", "het_cho_chia", "du_nhanh_chia", "chi_luong")

    def __init__(self, b, tran):
        self.b = b
        self.tab = core.TABS[b.tab]
        # ---- TRẦN §15.5 — ba phép đếm riêng, không cộng lại ----
        # ⭐ CHỖ ĐÃ HỨA bị trừ RA KHỎI QUỸ ngay từ đầu. Mỗi phép chia còn treo trên
        # ngăn xếp nợ hai khối chưa đặt xuống: vế NGƯỢC và một hành động cho nó. Đặt
        # chỗ theo từng nước (mỗi `chia` tự kiểm "còn 4 chỗ không") thì ba phép chia
        # lồng nhau cùng tranh MỘT quỹ và đều thấy đủ — đo được 60/60 lượt đi kẹt cứng
        # ở đúng đấy. Trừ trước thì mọi phép đếm phía dưới tự đúng, khỏi nhớ thêm luật.
        no_chia = 2 * sum(1 for e in b.ngan_xep if e[6] is not None)
        con = tran["khoi_entry" if self.tab == core.TAB_ENTRY
                   else "khoi_manage"] - (len(b.khoi) - 1) - no_chia
        self.het_khoi = con < 1
        # ⭐ CHỪA CHỖ. Một cổng mới bắt buộc kéo theo một HÀNH ĐỘNG phía sau (§17
        # `_lt_cong_cut`), nên đẻ cổng lúc chỉ còn đúng một suất khối là tự đi vào ngõ
        # cụt: cổng đứng đó, không đóng nhánh được, không `het` được, mặt nạ tắt sạch.
        # Đo được: 19/60 lượt đi tắc cứng ở đúng chỗ này.
        self.het_cho_cong = con < 2
        self.het_dk = len((b.cong or {}).get(b.ds) or ()) >= tran["dk_moi_cong"]
        self.het_nhanh = b.dem_nhanh.get(b.diem, 0) >= tran["nhanh_moi_re"]
        # ⭐ Một phép CHIA tốn BỐN suất khối: hai cổng + một hành động mỗi vế. Cùng cái
        # bẫy `het_cho_cong` đã cắn một lần — chừa thiếu là đi thẳng vào ngõ cụt: vế
        # ngược đứng đó, không đóng được, không `het` được, mặt nạ tắt sạch.
        self.het_cho_chia = con < 4
        self.du_nhanh_chia = b.dem_nhanh.get(b.diem, 0) + 2 <= tran["nhanh_moi_re"]
        # Cùng lý lẽ, ngõ cụt thứ hai: ở Manage một nhánh chỉ đóng được bằng khối Sửa
        # lệnh, mà §17.2 cấm hai khối ghi đè nhau — đường nào đã dùng hết các chế độ
        # thì cổng mới trên đó vĩnh viễn không có gì để nối tiếp.
        self.con_sua_duoc = (self.tab != core.TAB_MANAGE
                             or any(_sua_khong_giam(b, cd) for cd in core.SUA_CHE_DO))
        self.trong_nhanh = bool(b.ngan_xep)
        # Nhánh RỖNG = vừa `mo_nhanh` xong, chưa treo khối nào lên nhánh ấy.
        self.nhanh_rong = self.trong_nhanh and b.diem == b.ngan_xep[-1][0]
        self.dau = b.diem == b.khoi[0]["id"]
        ds = (b.cong or {}).get(b.ds) or []
        # Một cổng KHÔNG trộn hai kiểu so sánh: `so_dai_luong` là cờ của cả KHỐI.
        self.kieu = None if not ds else (
            "gia" if b.cong.get("so_dai_luong") else "so")
        # ⭐ Danh sách HỢP LỆ thì LUÔN so với một LƯỢNG — `normalize_action` ép thế và
        # nói rõ vì sao: cờ *"so hai đại lượng"* là của phần ĐẾM, để nó lan sang đây là
        # âm thầm viết lại vế phải của định nghĩa hợp lệ.
        #
        # ⚠ Người bày phải nói ĐÚNG CÂU ẤY. Không nói thì `cong_zone → dk_ds → hop_le →
        # dk_gia` đi lọt sạch mặt nạ, rồi `dk_gia` bật cờ và cờ ấy ép điều kiện ĐÚNG/SAI
        # bên `conditions` thành *"so với một đại lượng"* — sơ đồ ra lò với một vế phải
        # rỗng và người soát mắng. Lỗi này CÓ TRƯỚC nước `chia`; chia chỉ đổi xác suất
        # bốc nên nó mới lộ ra.
        self.chi_luong = b.ds == "dk_hop_le"
        self.da_hoi = {c["trai"]["ten"] for c in ds}
        # Cổng RỖNG luôn khớp (§6.0) — chưa có điều kiện thì chưa được đi tiếp.
        self.cong_du = b.cong is None or bool(b.cong.get(b.ds))
        self.co_vao_lenh = any(s.get("type") == core.VAO_LENH for s in b.khoi)
        # ⚠ CỔNG CỤT = cổng KHÔNG CÓ GÌ PHÍA SAU (`_lt_cong_cut`), không phải "khối
        # cuối cùng là một cổng". Sau `dong_nhanh` thì `diem` lùi về chỗ rẽ — chỗ ấy
        # là một cổng, nhưng nó ĐÃ có nhánh con nên không cụt. Lẫn hai thứ này thì mọi
        # ngã rẽ thành ngõ cụt: đo được, 19/60 lượt đi tắc cứng ở đúng chỗ đó.
        self.cuoi_la_cong = b.cuoi == core.CHECK_COND and b.diem not in b.co_con
        # ⭐ ĐIỀU KIỆN CÒN DỞ thì mọi nước khác đều tắt. Một điều kiện thiếu khung giờ
        # là một điều kiện soát tĩnh sẽ mắng — bày ra nước đi khác lúc đó là mời máy
        # tìm dựng ra sơ đồ hỏng rồi mới biết, đúng thứ người bày sinh ra để chặn.
        # Khoá là TÊN NƯỚC ĐI (`chu_ky_trai`), không phải tên trường (`period`) — hai
        # cái tên cho cùng một thứ, và lệch nhau thì mặt nạ tắt sạch rồi lượt đi kẹt
        # cứng. Đã cắn một lần.
        self.no = {} if b.dk is None else {
            f"{_TEN_NUOC[k]}_{ben}": True
            for ben, o in (("trai", b.dk.get("trai")), ("phai", b.dk.get("phai")))
            for k in _thieu_o(o)}
        # ⚠ Lệnh CHỜ neo vào `close` mà không đệm thì khớp ngay ở nhịp sau — nó không
        # còn là lệnh chờ nữa. Người soát báo LỖI; ở đây thành "chưa đi tiếp được".
        self.can_dem = (b.hd is not None and "dem" not in b.hd
                        and b.hd.get("loai") == "stop"
                        and (b.hd.get("entry") or {}).get("moc") == "close")
        self.lenh_tren_duong = {
            (s["huong"], s["loai"], (s.get("entry") or {}).get("moc"),
             (s.get("sl") or {}).get("value"), (s.get("tp") or {}).get("value"),
             s.get("rui_ro"))
            for s in _duong_len(b) if s.get("type") == core.VAO_LENH}


def _chua_co_so(k, c):
    """Toán hạng này còn ĐỨNG YÊN Ở 0 — hỏi nó lúc này là hỏi một hằng số.

    ⭐ `sinh_boi: "vao_lenh"` trong kho: `so_vi_the`, `so_lenh_cho`, `drawdown_pt`,
    `zone_da_sinh_lenh` chỉ khác 0 sau khi đã có khối Vào lệnh. Sơ đồ Entry chưa có
    khối nào như thế thì mọi phép so với chúng đều là hằng số — kể cả `< 30` (luôn
    đúng), không riêng `> 0`.

    Và tệ hơn hằng số: nếu chính cái cổng ấy chặn đường xuống khối Vào lệnh thì đó là
    VÒNG TRÒN — muốn có số phải vào lệnh, muốn vào lệnh phải qua cổng ấy. Đo được 14/68
    sơ đồ câm chết đúng ở đây (21%).

    ⚠ HƠI CHẶT hơn mức cần: một nhánh SONG SONG có thể đã đẻ lệnh từ nến trước, nên về
    lý thì cổng ấy vẫn tới được. Chấp nhận, vì cùng cái sơ đồ ấy vẫn dựng được bằng cách
    đi nhánh có lệnh TRƯỚC — thứ mất đi là một thứ tự đi, không phải một sơ đồ. Đổi lại
    là một luật đọc được trong một dòng."""
    return (k in SINH_BOI_LENH and c.tab == core.TAB_ENTRY and not c.co_vao_lenh)


def _duoc(n, c):
    b, loai = c.b, n[0]

    # ---- còn dở: CHỈ mấy nước lấp chỗ trống ----
    if c.no:
        return loai in c.no
    if c.can_dem:
        return loai == "dem"

    if loai == "nhip":
        # Nhịp là nước MỘT LẦN và phải đứng đầu: đặt hai lần thì lần sau ghi đè lần
        # trước, tức chuỗi mang một nước không để lại dấu vết nào.
        if not (c.dau and b.cong is None and not b.co_nhip):
            return False
        # Manage KHÔNG được chậm hơn Entry: lệnh vừa sinh phải chờ qua vài nhịp mới
        # được quản lý — dời SL và huỷ lệnh chờ đều phản ứng trễ.
        return (c.tab == core.TAB_ENTRY
                or core.TIMEFRAMES.index(n[1])
                <= core.TIMEFRAMES.index(b.so_do[core.TAB_ENTRY]["steps"][0]["nhip"]))

    if loai in _DK:
        # TRẦN §15.5: một cổng bao nhiêu điều kiện thì thôi, và cổng MỚI thì tốn một
        # khối nữa (kèm một suất chừa cho hành động sau nó). Hai phép đếm khác nhau,
        # đừng gộp.
        if c.het_dk or (b.cong is None and (c.het_cho_cong or not c.con_sua_duoc)):
            return False
        k = n[1]
        if c.tab not in _TAB_CUA[k]:
            return False               # toán hạng của Manage, đặt ở Entry là vô nghĩa
        if _chua_co_so(k, c):
            return False
        if k in kho.CAN_ZONE and not b.co_zone:
            return False               # §12.6c: toán hạng zone chỉ SAU cổng zone
        # ⚠ `zone_hop_le` có HAI luật riêng, cả hai đều do `_soat_cong_zone` canh:
        #   · VÒNG TRÒN — cổng zone hỏi nó là hỏi kết quả của chính nó (và bộ chạy thì
        #     TỪNG tràn ngăn xếp ở đấy). Cấm cả ở phần ĐẾM lẫn phần HỢP LỆ.
        #   · CHƯA ĐỊNH NGHĨA — hỏi khi cổng zone chưa khai phần HỢP LỆ là hỏi một khái
        #     niệm chưa ai định nghĩa.
        if k == "zone_hop_le" and ((b.cong or {}).get("cong_zone") or not b.co_hop_le):
            return False
        if k in c.da_hoi:
            return False               # hỏi hai lần cùng một thứ trong một cổng
        if loai == "dk_gia" and c.chi_luong:
            return False
        if c.kieu is not None and c.kieu != ("gia" if loai == "dk_gia" else "so"):
            return False
        if loai == "dk_gia":
            return not (n[3] in c.da_hoi or (n[3] in kho.CAN_ZONE and not b.co_zone))
        # ⚠ ĐƠN VỊ cũng cần zone. `atr < 0,5 × ATR zone` không có cổng zone là lỗi y
        # như dùng thẳng toán hạng zone — dễ quên vì cái zone nấp trong ĐƠN VỊ, không
        # nằm ở tên toán hạng.
        if loai == "dk_so" and n[4] == "atr_zone" and not b.co_zone:
            return False
        return True

    if loai in _CHIA:
        # Luật TOÁN HẠNG y hệt `dk_*` — cùng kho, cùng luật zone, cùng luật tab. Khác ở
        # luật CHỖ: chia đẻ ra hai cổng và hai nhánh cùng lúc, nên nó là một nước CẤU
        # TRÚC chứ không phải một nước điền vào cổng đang mở.
        if c.het_cho_chia or not c.con_sua_duoc or not c.du_nhanh_chia:
            return False
        # §5 mỗi nhánh mở đầu bằng CỔNG: hai vế đều là cổng nên chia MỞ ĐẦU được một
        # nhánh — nhưng không chia ngay trên một nhánh còn rỗng (nhánh ấy sẽ không có
        # đầu của riêng nó), và cổng đang mở phải đủ điều kiện trước khi bị đóng lại.
        if c.nhanh_rong or not c.cong_du:
            return False
        # ⭐ KHÔNG chia ngay dưới khối Bắt đầu — và đây là luật quan trọng nhất của nước
        # này. Hai vế của một phép chia PHỦ KÍN, nên luôn có đúng một vế khớp: một cái
        # cây toàn phép chia thì nến nào cũng rơi xuống một hành động, tức máy nã lệnh
        # chứ không phải chiến lược. Phải có ít nhất một CÁI LỌC ở trên để sơ đồ còn
        # được quyền KHÔNG LÀM GÌ — và chỗ rẻ nhất bảo đảm điều đó là ngay tại gốc.
        #
        # Đo được ngay khi thiếu luật này: 146/400 sơ đồ có đường tới hành động không
        # qua một cái lọc nào. `mo_nhanh` cấm `dau` sẵn, nên đây cũng là chỗ nhất quán.
        if c.dau:
            return False
        k = n[1]
        if c.tab not in _TAB_CUA[k] or (k in kho.CAN_ZONE and not b.co_zone):
            return False
        if _chua_co_so(k, c):
            return False
        # Hai vế nằm trên cổng MỚI, dưới cổng hiện tại — nên không có vòng tròn như khi
        # chính cổng zone tự hỏi `zone_hop_le`. Chỉ cần phần HỢP LỆ đã được khai.
        if k == "zone_hop_le" and not b.co_hop_le:
            return False
        if loai == "chia_gia":
            return not (n[3] in kho.CAN_ZONE and not b.co_zone)
        if loai == "chia_so" and n[4] == "atr_zone" and not b.co_zone:
            return False
        return True

    # ---- bổ nghĩa: chỉ ngay sau điều kiện nó bổ nghĩa, và không đặt lại ----
    if loai in ("tf_trai", "chu_ky_trai", "tf_phai", "chu_ky_phai"):
        if b.dk is None:
            return False
        ben = "trai" if loai.endswith("_trai") else "phai"
        o = b.dk.get(ben)
        if not isinstance(o, dict) or not o.get("ten"):
            return False               # vế phải là một LƯỢNG, không có khung/chu kỳ
        khoa = "tf" if loai.startswith("tf") else "period"
        if khoa in o:
            return False               # đặt rồi
        if khoa == "tf":
            # ⭐ Cùng chùm + có cực trị + CÙNG KHUNG GIỜ = hỏi một hằng số
            # (`Giá cao nhất(M5) > Giá thấp nhất(M5)` luôn đúng). Khác khung giờ thì là
            # hai cây nến khác nhau, hỏi được. Nên luật rơi vào ĐÚNG nước đặt khung giờ,
            # chứ không vào nước dựng điều kiện.
            kia = b.dk.get("phai" if ben == "trai" else "trai")
            if (isinstance(kia, dict) and kia.get("tf") == n[1]
                    and quan_he_co_dinh(o["ten"], kia.get("ten"))):
                return False
        return o["ten"] in (CO_TF if khoa == "tf" else CO_CHU_KY)

    if loai == "vao_lenh":
        # §6.0 Entry chỉ TẠO · §5 mỗi nhánh mở đầu bằng CỔNG (nên không treo hành động
        # ngay dưới khối Bắt đầu, cũng không mở đầu một nhánh bằng nó).
        if c.tab != core.TAB_ENTRY or c.dau or c.nhanh_rong or not c.cong_du:
            return False
        if c.het_khoi:
            return False
        if n[3] in core.MOC_CAN_ZONE and not b.co_zone:
            return False
        # §17 `_lt_lenh_trung_doc`: hai khối Vào lệnh GIỐNG HỆT trên cùng một đường chỉ
        # tạo ra ĐÚNG MỘT lệnh — khối thứ hai là một lời hứa suông trên hình vẽ.
        return n[1:] not in c.lenh_tren_duong
    if loai == "dem":
        return b.hd is not None and "dem" not in b.hd
    if loai == "sua_lenh":
        if c.tab != core.TAB_MANAGE or c.dau or c.nhanh_rong or not c.cong_du:
            return False
        if c.het_khoi:
            return False
        return _sua_khong_giam(b, n[1])

    if loai == "cong_moi":
        # Chỉ có nghĩa khi đang có cổng ĐÃ có điều kiện: đóng cổng rỗng là để lại một
        # cổng luôn khớp, còn bấm khi không có cổng nào là nước trống. Và cổng SAU nó
        # phải còn chỗ trong trần khối, không thì đóng cổng là đi vào ngõ cụt.
        return (b.cong is not None and c.cong_du and not c.het_cho_cong
                and c.con_sua_duoc)
    if loai == "cong_zone":
        # MỘT cổng zone mỗi CHIẾN LƯỢC — nhiều zone cùng lúc đang hoãn có chủ ý
        # (§15.11). Hỏi `zone_o_entry` (toàn cục) chứ KHÔNG hỏi `co_zone` (theo vị
        # trí): cổng zone ở nhánh A rồi thêm một cổng nữa ở nhánh B là "có 2 cổng
        # zone", dù đứng ở B thì `co_zone` đã về false.
        return (not b.zone_o_entry and c.tab == core.TAB_ENTRY and c.cong_du
                and not c.het_cho_cong)
    if loai == "hop_le":
        # `dk_hop_le` chỉ có nghĩa trên chính cổng ĐỊNH NGHĨA zone (§12.6f), và phần
        # ĐẾM phải xong trước — hai danh sách, không quay lại.
        return (b.cong is not None and b.cong.get("cong_zone")
                and b.ds == "conditions" and bool(b.cong.get("conditions")))
    if loai == "mo_nhanh":
        # TRẦN §15.5: một ngã rẽ bao nhiêu nhánh thì thôi — quá nhiều đường thì không
        # theo dõi nổi. Nhánh mới mở đầu bằng CỔNG (§5) nên cũng phải chừa chỗ cho
        # hành động đóng nó.
        #
        # ⚠ Và KHÔNG mở nhánh khi nhánh hiện tại còn RỖNG. Hai `mo_nhanh` liên tiếp đẩy
        # CÙNG MỘT chỗ rẽ vào ngăn xếp hai lần; đóng nhánh trong xong thì `diem` bằng
        # đúng đỉnh ngăn xếp, nên nhánh ngoài trông rỗng VĨNH VIỄN — mở nhánh bị cấm
        # (rỗng), đóng nhánh bị cấm (rỗng), đẻ cổng bị cấm (hết chỗ). Ngõ cụt, và mặt
        # nạ tắt sạch: đo được **80/150** lượt đi chết ở đúng đây.
        return (c.cong_du and not c.dau and not c.nhanh_rong and not c.het_nhanh
                and not c.het_cho_cong and c.con_sua_duoc)
    # ⚠ NHÁNH KHÔNG ĐƯỢC KẾT THÚC BẰNG CỔNG (`_lt_cong_cut`): "khớp điều kiện rồi thì
    # không có gì phía sau" — chiến lược dừng ngay tại đó, tức cái cổng vừa hỏi xong
    # một câu rồi không làm gì với câu trả lời.
    if loai == "dong_nhanh":
        # ⚠ Đóng vế THUẬN của một phép chia là ĐẺ NGAY vế ngược + một hành động cho nó.
        # KHÔNG phải kiểm chỗ ở đây: hai khối ấy đã bị trừ khỏi quỹ từ lúc `chia`, nên
        # đóng nhánh chỉ TRẢ LẠI chỗ, không bao giờ tiêu thêm.
        return (c.trong_nhanh and not c.nhanh_rong and c.cong_du
                and not c.cuoi_la_cong)
    if loai == "het":
        # Mọi nhánh phải đóng, cổng cuối không bỏ dở, và Entry bắt buộc có ít nhất một
        # khối Vào lệnh — sơ đồ Entry không bao giờ vào lệnh là sơ đồ không làm gì.
        if c.trong_nhanh or not c.cong_du or c.cuoi_la_cong:
            return False
        return c.co_vao_lenh if c.tab == core.TAB_ENTRY else True
    return False


def _duong_len(b):
    """Mọi khối trên ĐƯỜNG từ điểm hiện tại ngược lên khối Bắt đầu.

    Mấy luật §17 nói về "cùng một đường" (`_lt_lenh_trung_doc`, `_lt_sau_ket_thuc`,
    `_lt_sua_de_doc`) đều hỏi đúng cái đường này. Chuỗi đang dựng là một nhánh thẳng
    nên chỉ cần lần theo `from` là đủ."""
    truoc = {e["to"]: e["from"] for e in b.canh}
    theo_id = {s["id"]: s for s in b.khoi}
    ra, cur = [], b.diem
    while cur:
        s = theo_id.get(cur)
        if s is not None:
            ra.append(s)
        cur = truoc.get(cur)
    return ra


def _sua_khong_giam(b, che_do):
    """§17.1 + §17.2: sau `Kết thúc lệnh` thì hết, và không hai khối ghi đè nhau."""
    ghi = core.SUA_GHI_LEN.get(che_do)
    for s in _duong_len(b):
        if s.get("type") == core.SUA_LENH:
            g = core.SUA_GHI_LEN.get(s.get("che_do"))
            if g == "*" or ghi == "*" or g == ghi:
                return False
    return True


# ---------------------------------------------------------------------------
# CHIỀU NGƯỢC — sơ đồ có sẵn → chuỗi nước đi
# ---------------------------------------------------------------------------


class KhongDocDuoc(Exception):
    """Sơ đồ có thứ kho nước đi chưa diễn tả được.

    ⚠ NỔ, không đoán. Đọc ngược mà lặng lẽ bỏ qua một khối là chuỗi trả về mô tả một
    sơ đồ KHÁC với cái vừa đọc — đúng loại hỏng im lặng cả app này cấm (§16.3)."""


def doc_nguoc(doc, lam_tron=False):
    """Tài liệu chiến lược → chuỗi chỉ số nước đi dựng lại đúng nó.

    ⭐ Đây là chiều mở ra việc **cho máy học từ sơ đồ người dùng vẽ tay** (§18.7.3), và
    là bài kiểm duy nhất chứng minh hai chiều khớp nhau.

    `lam_tron=True` cho phép **kéo con số về nấc gần nhất** khi sơ đồ người vẽ dùng một
    giá trị không có trên thang (người vẽ đâu bị buộc theo thang — máy mới bị). Trả kèm
    danh sách đã kéo, vì lúc đó chuỗi mô tả một sơ đồ *xấp xỉ*, không phải sơ đồ gốc.

    Trả `(chuoi, da_lam_tron)`."""
    doc = core.normalize_process(doc)
    gt = {t["ten"]: t["gia_tri"] for t in doc["tham_so"]}
    d = _Doc(gt, lam_tron)
    for tab in core.TABS:
        so = doc[tab]
        bd = next((s for s in so["steps"] if core.is_start_step(s)), None)
        if bd is None:
            raise KhongDocDuoc(f"Sơ đồ {tab} không có khối Bắt đầu.")
        if bd.get("nhip") != core.NHIP_MAC_DINH[tab]:
            d.them(("nhip", bd.get("nhip")), f"nhịp của sơ đồ {tab}")
        con = {}
        d.cong_mo = False
        for e in so["edges"]:
            con.setdefault(e["from"], []).append(e["to"])
        # ⚠ Sơ đồ RỖNG là hợp lệ ở Manage — "không quản lý gì cả" là một lựa chọn
        # (đặt SL/TP lúc vào rồi để yên). Ở Entry thì không: sơ đồ không nối đi đâu là
        # sơ đồ không bao giờ vào lệnh.
        if not con.get(bd["id"]):
            if tab == core.TAB_ENTRY:
                raise KhongDocDuoc("Sơ đồ Entry không nối đi đâu cả — không bao giờ "
                                   "vào được lệnh.")
        else:
            d.duyet({s["id"]: s for s in so["steps"]}, con, bd["id"])
        d.ra.append(CHI_SO[("het",)])
    return d.ra, d.tron


class _Doc:
    """Trạng thái của một lượt đọc ngược. Gom lại để khỏi chuyền năm tham số."""

    def __init__(self, gt, lam_tron):
        self.ra, self.tron, self.gt, self.lam_tron = [], [], gt, lam_tron
        #: Có CỔNG đang mở không — tức nước điều kiện tiếp theo có phải đóng cổng cũ
        #: trước không. Trước đây suy từ *"nước vừa rồi có phải `mo_nhanh`"*, mà đó chỉ
        #: là một trong bốn đường làm cổng đóng lại (còn `dong_nhanh`, `chia_*`, và
        #: chính khối hành động). Suy sai thì chuỗi mang một nước `cong_moi` mà mặt nạ
        #: không cho đi — dựng lại vẫn ra đúng sơ đồ, nhưng chuỗi thôi là thứ đem so
        #: được, và §18.7.2 sống bằng chuỗi.
        self.cong_mo = False

    # ---- đồ thị ----
    def duyet(self, theo_id, con, sid):
        ke = con.get(sid) or []
        if len(ke) == 1:
            self.khoi(theo_id[ke[0]])
            self.duyet(theo_id, con, ke[0])
        elif len(ke) > 1:
            # Duyệt theo ĐÚNG thứ tự bộ chạy sẽ thử nhánh (`core._khoa_nhanh` — trên
            # xuống dưới, trái sang phải), không theo thứ tự cạnh nằm trong file. Sai
            # thứ tự ở đây là chuỗi dựng lại một sơ đồ chạy KHÁC.
            thu_tu = sorted(ke, key=lambda i: core._khoa_nhanh(theo_id[i]))
            # ⭐ PHÉP CHIA đọc thành MỘT nước, không thành hai `mo_nhanh`. Hai lối viết
            # ra cùng một sơ đồ, nên phải chọn lấy một làm chính tắc — không thì một sơ
            # đồ có hai chuỗi, và "chuỗi là thứ đem đi so, đem đi lưu" mất nghĩa.
            n = self.la_chia(theo_id, thu_tu)
            if n is not None:
                self.them(n, "phép chia")
                self.cong_mo = False
                # Bổ nghĩa điền MỘT lần cho cả hai vế — `Ban.dk_doi` chép sang vế kia.
                self.bo_nghia(theo_id[thu_tu[0]]["conditions"][0], "phép chia")
                self.duyet(theo_id, con, thu_tu[0])
                self.ra.append(CHI_SO[("dong_nhanh",)])
                self.cong_mo = False
                # KHÔNG duyệt lại vế ngược như một khối: `dong_nhanh` vừa đẻ ra nó.
                self.duyet(theo_id, con, thu_tu[1])
                return
            for k in thu_tu:
                self.ra.append(CHI_SO[("mo_nhanh",)])
                self.cong_mo = False
                self.khoi(theo_id[k])
                self.duyet(theo_id, con, k)
                self.ra.append(CHI_SO[("dong_nhanh",)])
                self.cong_mo = False

    def la_chia(self, theo_id, ke):
        """Ngã rẽ này có phải một PHÉP CHIA không → nước `chia_*`, hoặc `None`.

        ⚠ CHẶT TAY có chủ ý — chỉ nhận đúng thứ `chia` đẻ ra: hai vế, mỗi vế một cổng
        trần với ĐÚNG MỘT điều kiện, cùng toán hạng, cùng lượng, phép so là một cặp
        trong `PHEP_CHIA` và vế thuận nằm TRÊN. Nhận rộng hơn là đọc một ngã rẽ bình
        thường thành phép chia — rồi dựng xuôi lại ra một sơ đồ khác. Không nhận được
        thì rơi về lối `mo_nhanh`, vẫn đúng, chỉ dài hơn."""
        if len(ke) != 2:
            return None
        sa, sb = theo_id[ke[0]], theo_id[ke[1]]
        cap = cap_chia(sa, sb)
        if cap is None:
            return None
        ca, cb = cap
        pa = ca.get("phep")
        ten = (ca.get("trai") or {}).get("ten")
        if pa in core.PHEP_KHONG_VE_PHAI:
            n = ("chia_ds", ten)
        elif sa.get("so_dai_luong"):
            n = ("chia_gia", ten, pa, (ca.get("phai") or {}).get("ten"))
        else:
            # ⚠ `nac` có thể LÀM TRÒN và ghi vào sổ `tron`. Ở đây nó mới chỉ đang DÒ
            # xem có phải phép chia không, nên dò hụt là phải xoá dấu vết — không thì
            # sổ làm tròn có một dòng cho thứ chưa hề đọc.
            moc = len(self.tron)
            try:
                g = self.nac(ca.get("phai") or {}, _thang_ten(ten), "phép chia")
            except KhongDocDuoc:
                return None
            n = ("chia_so", ten, pa, g, (ca.get("phai") or {}).get("tinh"))
            if n not in CHI_SO:
                del self.tron[moc:]
        return n if n is not None and n in CHI_SO else None

    def khoi(self, s):
        t, ten = s.get("type"), core.step_title(s)
        if t == core.CHECK_COND:
            if self.cong_mo:
                self.ra.append(CHI_SO[("cong_moi",)])
            self.cong_mo = True
            if s.get("cong_zone"):
                self.ra.append(CHI_SO[("cong_zone",)])
            if not s.get("conditions"):
                raise KhongDocDuoc(f"Cổng “{ten}” không có điều kiện nào.")
            for c in s["conditions"]:
                self.dieu_kien(c, s, ten)
            if s.get("dk_hop_le"):
                self.ra.append(CHI_SO[("hop_le",)])
                for c in s["dk_hop_le"]:
                    # `so_dai_luong=False`: danh sách HỢP LỆ luôn ở chế độ LƯỢNG, khớp
                    # đúng `normalize_action`. Mặt nạ canh cùng câu ấy (`chi_luong`).
                    self.dieu_kien(c, dict(s, so_dai_luong=False), ten)
        elif t == core.VAO_LENH:
            self.cong_mo = False
            self.them(("vao_lenh", s.get("huong"), s.get("loai"),
                       (s.get("entry") or {}).get("moc"),
                       self.nac(s.get("sl"), "sl", ten), self.nac(s.get("tp"), "tp", ten),
                       self.nac(s.get("rui_ro"), "rui_ro", ten)), f"khối “{ten}”")
            if s.get("dem"):
                self.them(("dem", self.nac(s["dem"], "dem_vao", ten)),
                          f"đệm của “{ten}”")
        elif t == core.SUA_LENH:
            self.cong_mo = False
            cd = s.get("che_do")
            self.them(("sua_lenh", cd,
                       self.nac(s.get("khoang"), "sl", ten)
                       if cd in core.SUA_CAN_GIA else None), f"khối “{ten}”")
        else:
            raise KhongDocDuoc(f"Khối lạ: {t!r}")

    # ---- một điều kiện ----
    def dieu_kien(self, c, s, ten):
        tr, phep = c["trai"], c["phep"]
        if phep in core.PHEP_KHONG_VE_PHAI:
            self.them(("dk_ds", tr["ten"], phep), f"điều kiện ở “{ten}”")
        elif s.get("so_dai_luong"):
            self.them(("dk_gia", tr["ten"], phep, (c.get("phai") or {}).get("ten")),
                      f"điều kiện ở “{ten}”")
        else:
            p = c.get("phai") or {}
            self.them(("dk_so", tr["ten"], phep,
                       self.nac(p, _thang_ten(tr["ten"]), ten), p.get("tinh")),
                      f"điều kiện ở “{ten}”")
        self.bo_nghia(c, ten)

    def bo_nghia(self, c, ten):
        """Khung giờ / chu kỳ của một điều kiện — phần bám SAU nước dựng ra nó.

        Tách riêng vì phép CHIA cũng cần nó: nước `chia_*` dựng luôn hai điều kiện, còn
        khung giờ và chu kỳ vẫn đi sau, và đi ĐÚNG MỘT lần cho cả hai vế."""
        for ben, o in (("trai", c.get("trai")), ("phai", c.get("phai"))):
            if not isinstance(o, dict) or not o.get("ten"):
                continue
            if o.get("tf"):
                self.them((f"tf_{ben}", o["tf"]), f"khung giờ ở “{ten}”")
            if o.get("period") is not None:
                self.them((f"chu_ky_{ben}", self.nac(o["period"], "chu_ky", ten)),
                          f"chu kỳ ở “{ten}”")

    # ---- số ----
    def nac(self, o, thang, ten):
        """Một ô số → giá trị TRÊN THANG. Tham số đặt tên được tra ra giá trị thật."""
        v = o.get("value") if isinstance(o, dict) else o
        if isinstance(v, str):
            if v not in self.gt:
                raise KhongDocDuoc(f"“{ten}”: tham số `{v}` không có trong bảng tham số.")
            v = self.gt[v]
        if v is None:
            return None
        v = float(v)
        nac = THANG[thang]
        gan = min(nac, key=lambda x: abs(x - v))
        if abs(gan - v) < 1e-9:
            return type(nac[0])(gan)
        if not self.lam_tron:
            raise KhongDocDuoc(
                f"“{ten}”: giá trị {core._so(v)} không có trên thang `{thang}` "
                f"({' · '.join(core._so(x) for x in nac)}).\n\n"
                f"Người vẽ tay không bị buộc theo thang, máy thì có (§18.1). Gọi "
                f"`doc_nguoc(doc, lam_tron=True)` để kéo về nấc gần nhất — nhưng khi đó "
                f"chuỗi mô tả một sơ đồ XẤP XỈ, không phải sơ đồ gốc.")
        self.tron.append((ten, thang, v, gan))
        return type(nac[0])(gan)

    def them(self, n, cho):
        i = CHI_SO.get(n)
        if i is None:
            raise KhongDocDuoc(f"{cho}: {n!r} không có trong kho nước đi.")
        self.ra.append(i)


# ---------------------------------------------------------------------------
# Dựng lại từ chuỗi
# ---------------------------------------------------------------------------


def dung(chuoi, ten="Máy vẽ"):
    """Chuỗi nước đi → tài liệu chiến lược. Chiều xuôi, chạy một mạch."""
    b = Ban()
    for i in chuoi:
        b.di(i)
    return b.tai_lieu(ten)
