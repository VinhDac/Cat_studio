"""NGÔN NGỮ phía PYTHON — chữ trên hộp khối, tên toán hạng, câu người soát mắng.

    core.md §18.14

⭐ **VÌ SAO PHẢI CÓ BẢN PYTHON, KHÔNG DỊCH HẾT Ở GIAO DIỆN.** §12.9 đã chốt từ lâu: chữ
hiện trên hộp do **Python sinh**, giao diện không tự ghép câu — ghép thì sớm muộn nó mô
tả khác với thứ lõi thực sự hiểu, và người dùng tin vào cái sai. Luật ấy vẫn đúng, nên
hệ quả là: muốn hộp khối nói tiếng Anh thì **Python phải biết ngôn ngữ**.

Cùng một luật khoá với `webui/src/i18n.ts` — **khoá là câu tiếng Việt nguyên văn**:

```
chu("Kiểm tra điều kiện")   →  "Check condition"
chu("câu chưa dịch")        →  "câu chưa dịch"      ← không nổ, không rỗng
```

⚠ **MỘT nguồn sự thật**: cài đặt `ngon_ngu` trong `luu_tru.CAI_DAT_MAC_DINH`. Giao diện
đọc nó, Python đọc nó. Hai nguồn thì sớm muộn ribbon tiếng Anh còn hộp khối tiếng Việt,
và không ai biết bên nào mới đúng.

⚠ **TIẾN TRÌNH CON.** `song_song` đẻ tiến trình bằng `spawn`, tức module này được nạp
LẠI từ đầu ở mỗi tiến trình con và biến `_NGON` về mặc định. Chấp nhận được vì tiến
trình con chỉ chạy-và-chấm, không sinh chữ cho ai đọc. Nếu ngày nào nó phải trả về câu
tiếng Việt thì phải truyền ngôn ngữ qua `_mo_tien_trinh`, đừng để nó tự đoán.
"""

import os

#: ⭐ KHOÁ CỨNG cho BỘ KIỂM. `CAT_NGON_NGU=vi` thì `dat()` không đổi được nữa.
#:
#: ⚠ Vì sao cần: nhiều bài kiểm đối chiếu CHỮ trên hộp khối, mà chữ ấy đi theo cài đặt
#: người dùng đã lưu trên đĩa. Không khoá thì bật tiếng Anh xong chạy bộ kiểm là đỏ 6
#: phép, trong khi mã nguồn không hề sai — một bộ kiểm phụ thuộc trạng thái người dùng
#: thì không còn là bộ kiểm. Đã cắn đúng một lần, ngay đợt dịch này.
_KHOA = os.environ.get("CAT_NGON_NGU") or None

#: Ngôn ngữ đang dùng. `vi` | `en`.
_NGON = "en" if _KHOA == "en" else "vi"


def dat(ma):
    """Đặt ngôn ngữ. Gọi lúc mở app và mỗi lần lưu cài đặt.

    Có `CAT_NGON_NGU` thì lời gọi này bị BỎ QUA — xem `_KHOA`."""
    global _NGON
    if _KHOA:
        return _NGON
    _NGON = "en" if str(ma or "").lower() == "en" else "vi"
    return _NGON


def dang_dung():
    return _NGON


def chu(s):
    """Dịch một câu. Không có trong từ điển → trả NGUYÊN câu tiếng Việt.

    ⚠ Dự phòng này là thứ giữ cho app không vỡ, và cũng là thứ **nuốt lỗi**: sửa một dấu
    phẩy trong câu gốc mà quên từ điển thì câu ấy lặng lẽ rơi về tiếng Việt.
    `tests/test_ngon_ngu.py` canh đúng chỗ đó."""
    if _NGON == "vi" or not isinstance(s, str):
        return s
    return EN.get(s, s)


def bang(d):
    """Dịch mọi GIÁ TRỊ của một bảng nhãn, giữ nguyên khoá.

    Dùng cho `ACTION_LABELS`, `DON_VI`, `HUONG`… — mấy bảng mà khoá là mã máy còn giá
    trị là chữ người đọc."""
    return {k: chu(v) for k, v in d.items()}


from .ngon_ngu_kho import KHO

#: TỪ ĐIỂN — khoá là câu tiếng Việt nguyên văn trong mã.
#:
#: ⚠ MỘT bảng, gom từ nhiều MẢNH (`ngon_ngu_*.py`). Tách file chỉ vì độ dài — chia
#: thành hai bảng để hai chỗ tra thì *"tra bảng nào trước"* thành một câu hỏi không có
#: đáp án đúng.
_GOC = {
    # ---------------------------------------------------------- loại khối
    "Kiểm tra điều kiện": "Check condition",
    "Vào lệnh": "Open order",
    "Sửa lệnh": "Modify order",
    "Hành động": "Action",
    "Bắt đầu": "Start",

    # ---------------------------------------------------------- phép so
    "là ĐÚNG": "is TRUE",
    "là SAI": "is FALSE",

    # ---------------------------------------------------------- đơn vị
    "giá tuyệt đối": "absolute price",
    "× ATR": "× ATR",
    "× ATR nền": "× baseline ATR",
    "× ATR zone": "× zone ATR",
    "× R (rủi ro)": "× R (risk)",
    "mép zone đối diện": "opposite zone edge",

    # ---------------------------------------------------------- hướng · loại lệnh
    "Mua": "Buy",
    "Bán": "Sell",
    "Thị trường": "Market",
    "Chờ Stop": "Stop pending",

    # ---------------------------------------------------------- chế độ Sửa lệnh
    "Dời Stop Loss": "Move Stop Loss",
    "Dời Take Profit": "Move Take Profit",
    "Dời SL về hoà vốn": "Move SL to break-even",
    "Kết thúc lệnh này": "Close this order",

    # ---------------------------------------------------------- toán hạng
    "Giá đóng cửa": "Close",
    "Giá mở cửa": "Open",
    "Giá cao nhất": "High",
    "Giá thấp nhất": "Low",
    "Số vị thế đang mở": "Open positions",
    "Số lệnh chờ": "Pending orders",
    "Sụt vốn hiện tại": "Current drawdown",
    "Lệnh này đã khớp": "This order has filled",
    "SL của lệnh này đã ở hoà vốn": "This order’s SL is at break-even",
    "Lãi của lệnh này (× R)": "This order’s profit (× R)",
    "Lệnh này là lệnh MUA": "This order is a BUY",
    "Lệnh này đã sống bao nhiêu nến": "Candles this order has lived",
    "Lệnh này còn thuộc zone hiện hành": "This order still belongs to the current zone",
    "ATR": "ATR",
    "Đường trung bình MA": "Moving average (MA)",
    "Zone — số nến": "Zone — candle count",
    "Zone — đỉnh (HH)": "Zone — high (HH)",
    "Zone — đáy (LL)": "Zone — low (LL)",
    "Zone — bề rộng": "Zone — width",
    "Zone — ATR trung bình": "Zone — average ATR",
    "Zone hiện hành hợp lệ": "Current zone is valid",
    "Zone này đã sinh lệnh": "This zone has produced an order",

    # ---------------------------------------------------------- nhóm kho
    "Giá": "Price",
    "Sổ lệnh": "Order book",
    "Lệnh này": "This order",
    "Chỉ báo": "Indicators",
    "Zone": "Zone",

    # ---------------------------------------------------------- mảnh câu mô tả
    "rủi ro": "risk",
    "% vốn": "% of equity",
    "đệm": "buffer",
    "ngoài mép vùng": "beyond the zone edge",
    "CHƯA có điều kiện nào": "NO condition yet",
    "Kiểm tra điều kiện — CHƯA có điều kiện nào":
        "Check condition — NO condition yet",
    "chưa chọn": "not chosen",
    "chưa chọn toán hạng": "operand not chosen",
    "một con số": "a number",
    "VÀ": "AND",
    "Mỗi nến": "Every",
    "một lượt cho MỖI lệnh đang sống": "one pass for EACH live order",
    "chưa có điều kiện nào — luôn khớp": "no condition yet — always matches",
    "⬗ CỔNG ZONE · ĐẾM — qua thì zone lớn, trượt thì zone chết":
        "⬗ ZONE GATE · COUNT — pass and the zone grows, fail and it dies",
    "⬗ HỢP LỆ khi — zone vẫn sống dù chưa đạt":
        "⬗ VALID when — the zone stays alive even before it qualifies",
    "tại": "at",
}

EN = {**_GOC, **KHO}
