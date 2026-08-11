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
    "accent": "#ffa657",
    "ui": {"panel_cao": 176, "panel_gap": False},
    # Điều kiện chạy Strategy Test. Ở ĐÂY chứ không ở cửa sổ tester: bấm ▶ là phải CHẠY
    # NGAY, không phải mở ra một bảng nữa rồi mới bấm tiếp. Cài đặt là thứ đặt một lần
    # rồi quên; nó thuộc về app, không thuộc về một lần chạy.
    "test": {
        "symbol": "XAUUSD", "tu": "", "den": "",
        "spread_diem": 20.0,      # nến là giá Bid; Ask = Bid + spread
        "deposit": 10000.0,
        "commission": 0.0,        # USD mỗi lot, ROUND-TURN
        "don_bay": 100,
        "delay_ms": 60,           # nhịp PHÁT LẠI, không phải tốc độ mô phỏng
    },
}


def thu_muc_app():
    """Nơi ĐẶT DỮ LIỆU NGƯỜI DÙNG: cạnh file exe (bản đóng gói) hoặc cạnh mã nguồn."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def thu_muc_goi():
    """Nơi chứa TÀI NGUYÊN ĐI KÈM (giao diện đã build trong `webui/dist`).

    ⚠ KHÁC HẲN `thu_muc_app`, và trộn hai cái là hỏng theo cả hai chiều. Bản đóng gói
    một-file giải nén tài nguyên vào một thư mục TẠM (`sys._MEIPASS`) rồi xoá lúc thoát:
    để dữ liệu người dùng ở đó là mất sạch sau mỗi lần chạy. Ngược lại, tìm `webui/dist`
    cạnh .exe thì không thấy, vì nó nằm trong gói."""
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))


def trang_giao_dien():
    """Đường dẫn tới `index.html` đã build. Một chỗ duy nhất, hai cửa sổ cùng dùng."""
    return os.path.join(thu_muc_goi(), "webui", "dist", "index.html")


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
    """Đọc cài đặt. Hỏng thì trả mặc định, không ném lỗi.

    CHỈ giữ những khoá còn trong bảng mặc định: khi một cài đặt bị bỏ đi (ví dụ
    `timeframe` chuyển thành `nhip` trên khối Bắt đầu), khoá cũ trong file sẽ nằm lại
    vĩnh viễn và người đọc sau này tưởng nó vẫn có tác dụng."""
    ra = json.loads(json.dumps(CAI_DAT_MAC_DINH))
    try:
        with open(os.path.join(goc(), FILE_CAI_DAT), encoding="utf-8") as f:
            d = json.load(f) or {}
        ra.update({k: v for k, v in d.items() if k in CAI_DAT_MAC_DINH})
    except Exception:
        pass
    return ra


def ghi_cai_dat(s):
    """Lưu cài đặt. NÉM LỖI nếu không ghi được — không nuốt.

    Trước đây bọc `try/except: pass` rồi vẫn `return s`, nên đĩa đầy hoặc mất quyền ghi
    thì nơi gọi tưởng đã lưu xong. Lần mở app sau, cài đặt Strategy Test lặng lẽ về mặc
    định và không ai hiểu vì sao. `api` đã có `@_bat_loi` để đưa câu lỗi lên giao diện —
    cứ để nó làm việc của nó."""
    ghi_json_nguyen_tu(os.path.join(goc(), FILE_CAI_DAT), s)
    return s


def ghi_json_nguyen_tu(duong, du_lieu):
    """Ghi JSON qua file TẠM rồi `os.replace` — đổi tên trên NTFS là nguyên tử.

    Ngắt giữa lúc ghi (bấm ✕, mất điện, antivirus xen vào) mà ghi thẳng lên file đích thì
    để lại một file JSON CỤT: `doc_cai_dat` trả mặc định, còn một template cụt thì mất
    hẳn chiến lược. Cách này cùng lắm để lại một `.tmp` rác, bản cũ nguyên vẹn."""
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tam, duong)


# ---------------------------------------------------------------------------
# Chiến lược
# ---------------------------------------------------------------------------


def _ten_an_toan(ten):
    """Tên file an toàn. Chặn cả `..` và dấu phân cách để một cái tên gõ tay không
    ghi được ra ngoài thư mục chiến lược."""
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (ten or "").strip())
    s = s.strip(". ")
    # ⚠ Tên THIẾT BỊ của Windows: `NUL.json` bị ánh xạ vào hố đen ở BẤT KỲ thư mục nào.
    # Đã chạy thử dưới pythonw.exe (đường app thật): lưu tên "NUL" báo THÀNH CÔNG,
    # `os.path.exists` trả True, nhưng đĩa không có file và sơ đồ bốc hơi không một dòng
    # lỗi; "AUX"/"COM1" còn TREO CỨNG lúc đọc lại. Đáng lo vì "con" là từ tiếng Việt rất
    # hay gặp, mà app này mặc định người dùng đặt tên bằng tiếng Việt.
    # Thêm gạch dưới thay vì đổi tên khác: hàm giữ được tính lũy đẳng
    # (`_ten_an_toan("_con") == "_con"`), nên tên lấy từ `liet_ke` đưa ngược vào vẫn ra
    # đúng file, không cộng dồn gạch qua mỗi vòng.
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", s):
        s = "_" + s
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
    """Lưu một chiến lược. Ghi NGUYÊN TỬ: ngắt giữa chừng mà ghi thẳng lên file đích thì
    còn lại một JSON cụt, tức mất hẳn chiến lược cũ chứ không phải mất bản mới."""
    p = duong_dan_chien_luoc(ten)
    ghi_json_nguyen_tu(p, doc)
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
