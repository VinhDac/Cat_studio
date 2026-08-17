"""KHO — danh mục mọi thứ app tính được, gom từ các module con.

    kho/
      nen_tang.py     giá · sổ lệnh · lệnh này     LUÔN có
      chi_bao.py      ATR · MA                     ai gọi thì có
      zone.py         vùng giá + máy nuôi vùng     có khi SƠ ĐỒ định nghĩa nó

Vì sao tách ra chứ không để một danh sách phẳng trong `core.py`:

  · `zone_dem` CHỈ có nghĩa khi sơ đồ có cổng zone. Trộn nó chung với `close` là nói
    dối về việc thứ gì luôn có, thứ gì phải được định nghĩa ra mới có.
  · Thêm một cơ chế mới = thêm MỘT file vào đây, không sửa `core.py`.
  · Hộp thoại "Kho" chỉ việc đọc `danh_muc()` — nó không cần biết gì thêm.

Trùng khoá là LỖI CHẾT NGƯỜI, nên bắt ngay lúc import: hai module cùng khai `atr` với
hai nghĩa khác nhau thì mọi chiến lược dùng nó đều sai mà không báo gì.

⚠ KHÁI NIỆM "ENGINE" ĐÃ TAN. `engine_d02.py` bị xoá: cơ chế vùng vốn là ý tưởng riêng
của D_02, nhưng nó đã tổng quát hoá xong từ lâu (`moi_nen()` rỗng, điều kiện đếm nằm ở
cổng người dùng vẽ). Còn giữ một module mang tên một chiến lược cụ thể chỉ tổ khiến
người đọc tưởng phải "chọn engine". Bảng số của D_02 đi theo sơ đồ mẫu. Xem core.md
§15.3 · §15.4.
"""
from . import chi_bao, nen_tang, zone

# Thứ tự CÓ Ý NGHĨA: dropdown toán hạng xổ ra theo đúng thứ tự này.
MODULE = [nen_tang, chi_bao, zone]


def _gom(ten_thuoc_tinh):
    """Gom một danh sách từ mọi module, gắn thêm `nguon` = mã module."""
    ra = []
    for m in MODULE:
        for x in getattr(m, ten_thuoc_tinh, []):
            ra.append(dict(x, nguon=m.MA_SO))
    return ra


def _soat_trung(ds, ten):
    """Trùng khoá giữa hai module là lỗi im lặng tệ nhất — chặn ngay lúc import."""
    thay = {}
    for x in ds:
        k = x["key"]
        if k in thay:
            raise RuntimeError(
                f"kho: trùng khoá {ten} \"{k}\" giữa module \"{thay[k]}\" và "
                f"\"{x['nguon']}\". Mỗi khoá phải thuộc về đúng một nơi.")
        thay[k] = x["nguon"]
    return ds


TOAN_HANG = _soat_trung(_gom("TOAN_HANG"), "toán hạng")
CHI_BAO = _soat_trung(_gom("CHI_BAO"), "chỉ báo")
BANG_TRANG_THAI = _soat_trung(_gom("BANG_TRANG_THAI"), "bảng trạng thái")

# ---- tra cứu nhanh, để `core.py` khỏi quét lại mỗi lần ----
TOAN_HANG_KEYS = [t["key"] for t in TOAN_HANG]
THEO_KEY = {t["key"]: t for t in TOAN_HANG}
NHOM_LENH_NAY = "Lệnh này"

#: Toán hạng nào do MÁY VÙNG trả lời. Một cái tên cho cả app, `bo_chay` cũng đọc nó.
ZONE_TRA_LOI = zone.ZONE_TRA_LOI

#: Toán hạng chỉ có nghĩa khi ĐANG CÓ ZONE — gom từ chính module khai (`ZONE_TRA_LOI`),
#: không chép tay.
#:
#: ⚠ `core.TOAN_HANG_CAN_ZONE` từng là một tuple gõ tay, và nó đã lệch thật: còn sót
#: `zone_range_atr`, một toán hạng đã bị gỡ khỏi kho từ lâu. Hai nơi cùng trả lời
#: "cái nào cần zone" thì sớm muộn một nơi nói sai — mà `bo_chay` cũng đọc
#: `ZONE_TRA_LOI`, nên bản gõ tay là nguồn thứ hai không ai đồng bộ.
#: Cộng thêm toán hạng TỰ KHAI `can_zone` — thứ không do máy vùng trả lời nhưng vẫn vô
#: nghĩa khi chưa có zone (`lenh_thuoc_zone` hỏi "zone đẻ ra lệnh này còn hiện hành
#: không"). Khai tại nguồn, cùng chỗ với `don_vi` / `tabs` / `dung_sai`, để không sinh
#: ra một danh sách gõ tay thứ hai — đúng cái bẫy chú thích ngay trên vừa kể.
CAN_ZONE = tuple(dict.fromkeys(
    [k for m in MODULE for k in getattr(m, "ZONE_TRA_LOI", ())]
    + [t["key"] for t in TOAN_HANG if t.get("can_zone")]))


def nhan(key):
    return (THEO_KEY.get(key) or {}).get("nhan", key)


def nhom(key):
    return (THEO_KEY.get(key) or {}).get("nhom", "")


def tham_so(key):
    return (THEO_KEY.get(key) or {}).get("tham_so", [])


def la_dung_sai(key):
    """Toán hạng vốn đã đúng/sai — hộp thoại ẩn luôn ô vế phải cho chúng."""
    return bool((THEO_KEY.get(key) or {}).get("dung_sai"))


def tabs_cho_phep(key):
    """None = dùng được ở cả hai sơ đồ."""
    return (THEO_KEY.get(key) or {}).get("tabs")


def danh_muc():
    """Toàn bộ kho, đã chia mục — hộp thoại "Kho" vẽ thẳng từ cái này."""
    return {
        "module": [{
            "ma_so": m.MA_SO,
            "ten": m.TEN,
            "mo_ta": m.MO_TA,
            "nguon": getattr(m, "NGUON", ""),
            "so_chi_bao": len(getattr(m, "CHI_BAO", [])),
            "so_toan_hang": len(getattr(m, "TOAN_HANG", [])),
            "so_bang": len(getattr(m, "BANG_TRANG_THAI", [])),
        } for m in MODULE],
        "chi_bao": CHI_BAO,
        "toan_hang": TOAN_HANG,
        "bang_trang_thai": BANG_TRANG_THAI,
    }
