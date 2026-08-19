"""TỪ ĐIỂN — KHO ĐỒ: nhãn, nhóm, mô tả, công thức của 22 toán hạng.

    core.md §18.14

Đây là chữ người dùng đọc nhiều nhất sau chữ trên hộp khối: hộp thoại **Kho** bày cả kho
ra, và mỗi mục có một câu giải thích *"nó là cái gì, đo bằng gì, đọc ở nến nào"*. Dịch
thiếu chỗ này là mở Kho ra thấy nửa Anh nửa Việt.

⚠ Khoá là CÂU TIẾNG VIỆT NGUYÊN VĂN — rút bằng `tools/rut_cau_py.py`, tức đọc CÂY CÚ
PHÁP chứ không quét dòng. Python nối chuỗi ngầm qua nhiều dòng, nên quét dòng ra mảnh,
mà thứ tới tay người dùng là câu trọn.
"""
KHO = {
    # ------------------------------------------------------------ tên module
    "Nền tảng": "Core",
    "Giá · sổ lệnh · lệnh này — có sẵn cho mọi chiến lược.":
        "Price · order book · this order — available to every strategy.",
    "Chỉ báo chuẩn": "Standard indicators",
    "ATR · MA — tính thẳng từ nến, ai dùng cũng được.":
        "ATR · MA — computed straight from candles, usable by anyone.",
    "Một vùng giá đắp dần qua từng nến. Cổng zone trong sơ đồ quyết định nến nào được "
    "vào vùng — nên định nghĩa vùng là của người vẽ, không phải của app.":
        "A price area built up candle by candle. The zone gate in the diagram decides "
        "which candles join it — so the definition belongs to whoever draws it, not to "
        "the app.",

    # ------------------------------------------------------------------ nhóm
    "Giá": "Price",
    "Sổ lệnh": "Order book",
    "Lệnh này": "This order",
    "Chỉ báo": "Indicators",
    "Zone": "Zone",
    "chỉ báo": "indicator",
    "toán hạng": "operand",
    "bảng trạng thái": "state table",

    # -------------------------------------------------------------- toán hạng
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

    # ---------------------------------------------------------------- mô tả
    "Luôn đọc nến ĐÃ ĐÓNG — nến đang chạy thì tín hiệu sẽ vẽ lại.":
        "Always reads the CLOSED candle — on a forming candle the signal would repaint.",
    "= CountOpenPositions() của D_02.": "= D_02’s CountOpenPositions().",
    "D_02 chỉ cho ĐÚNG MỘT lệnh chờ sống một lúc (`if(m_has_pending) return`).":
        "D_02 allows EXACTLY ONE live pending order at a time "
        "(`if(m_has_pending) return`).",
    "Vốn đang thấp hơn đỉnh vốn bao nhiêu phần trăm. Dùng làm cầu dao: \"sụt quá 5 % "
    "thì ngừng vào lệnh\". Tính trên vốn ĐÃ CHỐT (lệnh đã đóng), không tính lãi nổi.":
        "How far equity sits below its peak, in percent. Use it as a circuit breaker: "
        "“past 5% drawdown, stop entering”. Measured on REALISED equity (closed "
        "orders), floating profit excluded.",
    "= `if(sl >= entry && sl > 0) continue` của ManageBreakEven, đảo lại. Thiếu nó thì "
    "Manage bắn lệnh sửa SL lại mỗi nến.":
        "= ManageBreakEven’s `if(sl >= entry && sl > 0) continue`, inverted. Without "
        "it, Manage fires an SL-modify on every candle.",
    "R = khoảng cách SL lúc VÀO LỆNH, chốt cứng theo lệnh — không tính lại.":
        "R = the SL distance AT ENTRY, fixed per order — never recomputed.",
    "SAI nghĩa là lệnh BÁN — chỉ có hai hướng, không có ca thứ ba.":
        "FALSE means a SELL — there are only two directions, no third case.",
    "Đếm từ nến ĐẶT lệnh, không phải nến khớp — nên nó đo được cả quãng lệnh chờ nằm "
    "treo. Đếm bằng nến TRỤC (nhịp của khối Bắt đầu), không phải M1.":
        "Counted from the candle the order was PLACED, not filled — so it also covers "
        "the time a pending order sat waiting. Counted in AXIS candles (the Start "
        "block’s tick), not M1.",
    "Zone đẻ ra lệnh này CÓ CÒN là zone hiện hành không. Gộp cả ba ca vào một câu: zone "
    "ấy chết mà chưa có zone mới · đã có zone mới · vẫn là nó. Lệnh chờ neo vào MÉP một "
    "zone đã chết thì cái neo hết nghĩa — nên đây là câu hỏi đúng để huỷ lệnh chờ, thay "
    "cho phép đoán gián tiếp qua ATR.":
        "Is the zone that produced this order still the current one? It folds three "
        "cases into one question: that zone died with no replacement · a new zone "
        "exists · it is still the same one. A pending order anchored to the EDGE of a "
        "dead zone has a meaningless anchor — so this is the right question for "
        "cancelling it, instead of guessing indirectly via ATR.",
    "Đo BỀ RỘNG một nến, tính bằng đơn vị giá. TR = max(High, Close[trước]) − min(Low, "
    "Close[trước]). D_02 đọc ở nến đã đóng [1].":
        "Measures a candle’s RANGE, in price units. TR = max(High, Close[prev]) − "
        "min(Low, Close[prev]). D_02 reads it on the closed candle [1].",
    "D_02 dùng SMA(50) trên khung Trend để chọn hướng.":
        "D_02 uses SMA(50) on the Trend timeframe to pick direction.",
    "SMA của True Range (đúng iATR của MT5 — KHÔNG phải Wilder)":
        "SMA of True Range (matches MT5’s iATR — NOT Wilder)",
    "SMA / EMA / SMMA / LWMA trên giá đóng cửa":
        "SMA / EMA / SMMA / LWMA on the close",
    "Vùng hiện hành đã nuốt bao nhiêu nến.":
        "How many candles the current zone has swallowed.",
    "Lệnh chờ MUA thường neo vào đây.": "A pending BUY usually anchors here.",
    "Lệnh chờ BÁN thường neo vào đây.": "A pending SELL usually anchors here.",
    "Đỉnh trừ đáy. Lọc vùng bị tin tức thổi rộng — so bằng đơn vị × ATR.":
        "High minus low. Filters out zones blown wide by news — compare in × ATR.",
    "Mức nhiễu thật suốt cả vùng → dùng nó định nghĩa 1R.":
        "The real noise level across the whole zone → use it to define 1R.",
    "Zone hiện hành có đạt phần \"hợp lệ\" của cổng zone không. Chưa có zone → CHƯA CÓ "
    "SỐ (cổng trượt), không phải SAI. ⚠ Nhãn mang chữ HIỆN HÀNH là cố ý: nó luôn hỏi về "
    "zone đang đếm lúc này. Cạnh dòng \"Lệnh này còn thuộc zone hiện hành\", hai dòng "
    "phải cùng một chủ ngữ — gọi bằng hai tên thì đọc ra thành hai zone khác nhau, mà "
    "thật ra chỉ có một. Và KHÔNG gọi là \"Zone mới\": ở Entry, zone hiện hành chính là "
    "zone sắp vào lệnh, chẳng mới gì cả — một cái nhãn phải đúng khi đứng một mình.":
        "Does the current zone meet the “valid” half of the zone gate? No zone yet → NO "
        "VALUE (the gate fails), not FALSE. ⚠ The word CURRENT in the label is "
        "deliberate: it always asks about the zone being counted right now. Next to "
        "“This order still belongs to the current zone”, both lines must share one "
        "subject — two names read as two different zones when there is only one. And "
        "it is NOT called “New zone”: in Entry the current zone IS the one about to be "
        "traded, nothing new about it — a label has to be right on its own.",
    "Là phép tra sổ lệnh xem có lệnh nào mang `zone_id` của zone hiện hành không — "
    "không phải cờ ẩn. Tính cả lệnh đã đóng: một vùng một lệnh.":
        "A lookup in the order book for any order carrying the current zone’s "
        "`zone_id` — not a hidden flag. Closed orders count too: one zone, one order.",
    "Sinh ra khi CỔNG ZONE khớp lần đầu, lớn thêm mỗi lần cổng còn khớp, và CHẾT ngay "
    "nhịp cổng trượt. Mỗi vùng mang một id riêng — lệnh đặt từ vùng nào thì ghi id vùng "
    "đó, nên \"một vùng một lệnh\" là phép tra bảng chứ không phải cờ ẩn.":
        "Born the first time the ZONE GATE matches, grows on every further match, and "
        "DIES on the tick the gate fails. Each zone carries its own id — an order "
        "records the id of the zone it came from, so “one zone, one order” is a table "
        "lookup, not a hidden flag.",
    "Mỗi lúc chỉ có MỘT vùng sống. Vùng chết rồi nến sau mới mở được vùng mới.":
        "Only ONE zone is alive at a time. A new one can open only on a candle after "
        "the old one died.",
    "Nến nào vào vùng là do CỔNG ZONE trong sơ đồ quyết — app không có ngưỡng nào viết "
    "cứng.":
        "Which candles join the zone is decided by the ZONE GATE in the diagram — the "
        "app hard-codes no threshold.",
    "Cổng được xét trên ZONE THỬ: bản sao đã cộng cây nến đang xét. Nhờ vậy \"bề rộng ≤ "
    "N\" là một HẠN MỨC, kiểm trước khi tiêu.":
        "The gate is evaluated on a TRIAL ZONE: a copy with the candle under "
        "consideration already added. That makes “width ≤ N” a LIMIT, checked before "
        "spending.",
    "Cổng trượt → vùng CHẾT ngay, dù đang có lệnh chờ treo trên mép nó.":
        "Gate fails → the zone DIES immediately, even with a pending order hanging on "
        "its edge.",
    "Đỉnh/đáy lấy từ High/Low của chính những nến đã vào vùng. Đọc nến ĐÃ ĐÓNG, không "
    "repaint.":
        "High/low come from the High/Low of the candles that actually joined the zone. "
        "Read on CLOSED candles, no repainting.",
    "atr_hien_tai và atr_tb là HAI thứ khác nhau — xem đơn vị `atr` vs `atr_zone`.":
        "atr_hien_tai and atr_tb are TWO different things — see units `atr` vs "
        "`atr_zone`.",
    "ATR nến mới nhất — dùng để đo đệm vào lệnh":
        "ATR of the latest candle — used to size the entry buffer",
    "trung bình ATR suốt cả vùng — dùng để đo 1R":
        "average ATR across the whole zone — used to size 1R",
    "cổng còn khớp hay đã trượt": "whether the gate still matches or has failed",

    # ------------------------------------------------------------ kiểu dữ liệu
    "số nguyên": "integer",
    "chuỗi": "string",
    "giá": "price",
    "đúng/sai": "true/false",
}
