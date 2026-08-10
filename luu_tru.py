"""Cơ sở lưu trữ — MỘT chỗ duy nhất biết file nằm ở đâu.

    <cạnh app>/du_lieu/
        cai_dat.json          cài đặt app
        chien_luoc/*.json     chiến lược đã lưu
        nen/                  cache nến tải về (Strategy Tester dùng sau)
        nhat_ky/              nhật ký lệnh của từng lần chạy (sau)

Trước đây đường dẫn rải rác trong `core.py` (`app_dir`, `_thu_muc_tpl`, …) và dùng
từ vựng cũ của Auto_Clicker ("templates", 3 loại). Giờ chỉ còn một loại — chiến lược —
nên gọi đúng tên nó, và gom về một module để đổi bố cục chỉ phải sửa một nơi.

KHÔNG ném lỗi khi đọc: file rác hay thiếu quyền thì trả mặc định. Đọc cài đặt mà chết
thì app không mở lên được, đắt hơn nhiều so với việc mất vài tuỳ chọn.
"""
import json
import os
import re
import sys

THU_MUC_GOC = "du_lieu"
FILE_CAI_DAT = "cai_dat.json"
THU_MUC_CHIEN_LUOC = "chien_luoc"
THU_MUC_NEN = "nen"
THU_MUC_NHAT_KY = "nhat_ky"

CAI_DAT_MAC_DINH = {
    "symbol": "XAUUSD",
    "timeframe": "M5",
    "accent": "#ffa657",
    "ui": {"panel_cao": 176, "panel_gap": False},
}


def thu_muc_app():
    """Cạnh file exe (bản đóng gói) hoặc cạnh mã nguồn (bản chạy thẳng)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def goc():
    d = os.path.join(thu_muc_app(), THU_MUC_GOC)
    os.makedirs(d, exist_ok=True)
    return d


def _thu_muc(ten):
    d = os.path.join(goc(), ten)
    os.makedirs(d, exist_ok=True)
    return d


def thu_muc_chien_luoc():
    return _thu_muc(THU_MUC_CHIEN_LUOC)


def thu_muc_nen():
    return _thu_muc(THU_MUC_NEN)


def thu_muc_nhat_ky():
    return _thu_muc(THU_MUC_NHAT_KY)


# ---------------------------------------------------------------------------
# Cài đặt
# ---------------------------------------------------------------------------


def doc_cai_dat():
    ra = json.loads(json.dumps(CAI_DAT_MAC_DINH))
    try:
        with open(os.path.join(goc(), FILE_CAI_DAT), encoding="utf-8") as f:
            ra.update(json.load(f) or {})
    except Exception:
        pass
    return ra


def ghi_cai_dat(s):
    try:
        with open(os.path.join(goc(), FILE_CAI_DAT), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return s


# ---------------------------------------------------------------------------
# Chiến lược
# ---------------------------------------------------------------------------


def _ten_an_toan(ten):
    """Tên file an toàn. Chặn cả `..` và dấu phân cách để một cái tên gõ tay không
    ghi được ra ngoài thư mục chiến lược."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (ten or "").strip())
    s = s.strip(". ")
    return s or "khong_ten"


def duong_dan_chien_luoc(ten):
    return os.path.join(thu_muc_chien_luoc(), _ten_an_toan(ten) + ".json")


def liet_ke_chien_luoc():
    try:
        return sorted(f[:-5] for f in os.listdir(thu_muc_chien_luoc())
                      if f.endswith(".json"))
    except Exception:
        return []


def ghi_chien_luoc(ten, doc):
    p = duong_dan_chien_luoc(ten)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return p


def doc_chien_luoc(ten):
    with open(duong_dan_chien_luoc(ten), encoding="utf-8") as f:
        return json.load(f)


def xoa_chien_luoc(ten):
    p = duong_dan_chien_luoc(ten)
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


# ---------------------------------------------------------------------------
# Di cư từ bố cục cũ
# ---------------------------------------------------------------------------


def di_cu():
    """Chuyển `settings.json` + `templates/strategy/` của bản cũ sang `du_lieu/`.

    Chạy MỘT lần lúc khởi động. Chỉ CHÉP những gì chưa có ở nơi mới — không đè, không
    xoá bản cũ. Người dùng mở lại bản cũ vẫn thấy đủ dữ liệu của họ."""
    da = []
    app = thu_muc_app()
    cu_cai_dat = os.path.join(app, "settings.json")
    moi_cai_dat = os.path.join(goc(), FILE_CAI_DAT)
    if os.path.exists(cu_cai_dat) and not os.path.exists(moi_cai_dat):
        try:
            with open(cu_cai_dat, encoding="utf-8") as f:
                ghi_cai_dat(json.load(f))
            da.append(FILE_CAI_DAT)
        except Exception:
            pass

    cu_tpl = os.path.join(app, "templates", "strategy")
    if os.path.isdir(cu_tpl):
        for f in os.listdir(cu_tpl):
            if not f.endswith(".json"):
                continue
            dich = os.path.join(thu_muc_chien_luoc(), f)
            if os.path.exists(dich):
                continue
            try:
                with open(os.path.join(cu_tpl, f), encoding="utf-8") as g:
                    noi_dung = g.read()
                with open(dich, "w", encoding="utf-8") as g:
                    g.write(noi_dung)
                da.append(f"chien_luoc/{f}")
            except Exception:
                pass
    return da


# ---------------------------------------------------------------------------
# Cho hộp thoại "Kho"
# ---------------------------------------------------------------------------


def tom_tat():
    """Kho đang chứa gì — đường dẫn thật + số lượng, để nhìn là biết tìm ở đâu."""
    def dem(d):
        try:
            return len([f for f in os.listdir(d) if not f.startswith(".")])
        except Exception:
            return 0

    return {
        "goc": goc(),
        "muc": [
            {"ten": "Chiến lược", "duong_dan": thu_muc_chien_luoc(),
             "so_luong": len(liet_ke_chien_luoc()),
             "danh_sach": liet_ke_chien_luoc()},
            {"ten": "Nến đã tải", "duong_dan": thu_muc_nen(),
             "so_luong": dem(thu_muc_nen()), "danh_sach": []},
            {"ten": "Nhật ký chạy", "duong_dan": thu_muc_nhat_ky(),
             "so_luong": dem(thu_muc_nhat_ky()), "danh_sach": []},
        ],
    }
