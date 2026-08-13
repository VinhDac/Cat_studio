"""KHO — danh mục mọi thứ app tính được, gom từ các module con.

    kho/
      nen_tang.py     giá · thời gian · tài khoản · lệnh này   (không thuộc engine nào)
      chi_bao.py      ATR · MA · Donchian · Volume MA          (chỉ báo phổ thông)
      engine_d02.py   atr_bps · bảng vùng nén                  (ý tưởng riêng của D_02)

Vì sao tách ra chứ không để một danh sách phẳng trong `core.py`:

  · `zone_dem` CHỈ có nghĩa khi engine D_02 đang nạp. Trộn nó chung với `close` là
    nói dối về việc thứ gì luôn có, thứ gì đến từ một chiến lược cụ thể.
  · Thêm một chiến lược mới = thêm MỘT file vào đây, không sửa `core.py`.
  · Hộp thoại "Kho" chỉ việc đọc `danh_muc()` — nó không cần biết gì thêm.

Trùng khoá là LỖI CHẾT NGƯỜI, nên bắt ngay lúc import: hai engine cùng khai `atr` với
hai nghĩa khác nhau thì mọi chiến lược dùng nó đều sai mà không báo gì.
"""
from . import chi_bao, engine_d02, nen_tang

# Thứ tự CÓ Ý NGHĨA: dropdown toán hạng xổ ra theo đúng thứ tự này.
MODULE = [nen_tang, chi_bao, engine_d02]

# Module nào là ENGINE (mang ý tưởng chiến lược) — dùng để chia mục trong hộp thoại Kho.
ENGINE = [engine_d02]


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

#: Toán hạng chỉ có nghĩa khi ĐANG CÓ ZONE — gom từ chính các engine khai
#: (`ENGINE_TRA_LOI`), không chép tay.
#:
#: ⚠ `core.TOAN_HANG_CAN_ZONE` từng là một tuple gõ tay, và nó đã lệch thật: còn sót
#: `zone_range_atr`, một toán hạng đã bị gỡ khỏi kho từ lâu. Hai nơi cùng trả lời
#: "cái nào cần zone" thì sớm muộn một nơi nói sai — mà `bo_chay` cũng đọc
#: `ENGINE_TRA_LOI`, nên bản gõ tay là nguồn thứ hai không ai đồng bộ.
CAN_ZONE = tuple(k for m in MODULE for k in getattr(m, "ENGINE_TRA_LOI", ()))


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
            "la_engine": m in ENGINE,
            "nguon": getattr(m, "NGUON", ""),
            "so_chi_bao": len(getattr(m, "CHI_BAO", [])),
            "so_toan_hang": len(getattr(m, "TOAN_HANG", [])),
            "so_bang": len(getattr(m, "BANG_TRANG_THAI", [])),
        } for m in MODULE],
        "chi_bao": CHI_BAO,
        "toan_hang": TOAN_HANG,
        "bang_trang_thai": BANG_TRANG_THAI,
    }
