"""TẦNG PHÒNG VỆ khi chạm sàn — biến Ý ĐỊNH của chiến lược thành việc CÓ THẬT ở sàn.

VIỆC CỦA FILE NÀY, NÓI GỌN
--------------------------
Chiến lược nói "mua 0.01 lot, SL ở 4400". Giữa câu đó và một lệnh có thật ở sàn có một
đống thứ chen vào: SL quá sát giá, giá nhảy trước khi lệnh tới, sàn không nhận kiểu
khớp, vị thế đang bị đóng băng, ống đứt. File này lo hết, và **ghi lại nó đã phải làm
gì** — vì mỗi lần nó sửa ý định là live lệch một chút khỏi backtest, mà lệch âm thầm là
thứ tệ nhất.

MỌI THỨ CHẠM SÀN ĐỀU ĐI QUA ĐÂY
-------------------------------
Mở · gắn SL/TP · sửa SL/TP · đóng · đặt chờ · sửa chờ · huỷ chờ. Không có cửa sau.
Bản trước chỉ có `gui()`, nên bốn thao tác kia gọi thẳng `order_send` — tức chúng
KHÔNG được phòng vệ, và mã lạ chúng gặp không bao giờ lộ mặt ở `CHUA_BIET`. Đó là
đúng lý do bài hiệu chuẩn "cài giả thuyết rồi mà vẫn lỗi".

BỐN KẾT CỤC, KHÔNG PHẢI HAI
---------------------------
  `ok`     — ý định thành hiện thực (kể cả khi phải sửa vài lần dọc đường)
  `bo`     — thử hết cách vẫn không được → GIẢ THUYẾT SAI, phải chỉnh con số
  `nguoi`  — máy không chữa được: AlgoTrading tắt, hết tiền, chợ đóng. Chỉnh con số
             bao nhiêu cũng vô ích, phải có người ra tay.
  `hong`   — chết trước cả khi gửi được gì (chưa cài thư viện, sàn không có symbol)

Tách `nguoi` khỏi `bo` mới cho vòng hiệu chuẩn biết lúc nào **dừng hẳn** thay vì lặp
mãi một bài không đời nào qua được.

HAI THỨ ĐỪNG LẪN
----------------
  • **Luật** ở đây là THƯỜNG TRỰC — luôn chạy, không phải bật khi cần.
  • Mấy con số trong luật (`kep_stops`, `deviation`, `thu_lai`…) là **GIẢ THUYẾT**.
    Bài hiệu chuẩn sinh ra để kiểm chúng đúng chưa, sai thì chỉnh, và chỉnh cho tới
    khi hết sai. Nó không sinh ra để trình diễn một tràng lệnh test.

RANH GIỚI QUAN TRỌNG NHẤT
-------------------------
Thử lại cái ĐÁNG thử, và tuyệt đối không thử lại cái vô vọng. Retry mù trên "thiếu
tiền" là gửi mãi một lệnh không bao giờ vào được, và che mất lỗi thật.
"""
from __future__ import annotations

import time

from . import nguon_nen as nn

try:
    import MetaTrader5 as mt5
except Exception:                               # noqa: BLE001
    mt5 = None


#: GIẢ THUYẾT mặc định. Dùng khi chưa hiệu chuẩn — và phải NÓI RA là đang đoán.
LUAT_MAC_DINH = {
    "kep_stops": None,      # điểm; None = tin con số sàn khai (thường sai, xem hiệu chuẩn)
    "deviation": 30,        # điểm trượt cho phép khi gửi lệnh thị trường
    "filling": None,        # None = tin con số sàn khai
    "thu_lai": 3,           # số lần thử thêm, với lỗi ĐÁNG thử
    "cho_ms": 500,          # giãn giữa hai lần thử thường
    "cho_bang_ms": 1500,    # 10029 vị thế đang ĐÓNG BĂNG — phải chờ tan, 500 ms là thiếu
    "cho_noi_giay": 30,     # 10031 mất kết nối — CHỜ NỐI LẠI THẬT, không ngủ mù
}

#: MỖI CON SỐ THUỘC LOẠI GÌ — và loại quyết định nó có mang từ DEMO sang THẬT được không.
#:
#: ⚠ Đây là chỗ "đo trên demo rồi chạy thật" đúng một nửa. Bảng Đề phòng nhìn thì đồng
#: nhất, nhưng chín dòng của nó có ba xuất xứ khác hẳn nhau:
#:
#:   `san`  — LUẬT CỦA SÀN. Demo và thật cấu hình như nhau cho cùng một symbol, nên đo
#:            ở demo dùng thẳng cho thật được. Đây là phần "đo một lần, xài mãi".
#:   `khop` — CHẤT LƯỢNG KHỚP. Demo không có thanh khoản thật, nên con số đo được ở đó
#:            là CHẶN DƯỚI chứ không phải sự thật — tài khoản thật gần như chắc chắn
#:            xấu hơn. Chép thẳng sang là cài hụt đúng cái ăn tiền.
#:   `ta`   — CÁCH APP TỰ XỬ. Không phụ thuộc tài khoản nào cả, mang đi đâu cũng đúng.
LOAI = {
    "kep_stops": "san",         # ngưỡng SL/TP — sàn cấu hình cho symbol
    "filling": "san",           # kiểu khớp sàn nhận
    "cho_bang_ms": "san",       # freeze level — cũng là cấu hình của sàn
    "deviation": "khop",        # TRƯỢT GIÁ — demo đẹp hơn sự thật
    "thu_lai": "ta",
    "cho_ms": "ta",
    "cho_noi_giay": "ta",
}

#: Retcode → làm gì. Đây là chỗ ranh giới "đáng thử / vô vọng / cần người" thành luật.
#:   thu      — thử lại y nguyên (trục trặc thoáng qua)
#:   noi      — nới deviation rồi thử lại (giá chạy nhanh hơn lệnh)
#:   kep      — kẹp SL/TP ra xa rồi thử lại (đặt quá sát giá)
#:   doi_fill — đổi kiểu khớp rồi thử lại
#:   cho_lau  — chờ LÂU rồi thử lại (đóng băng, quá tải) — `cho_ms` không đủ
#:   cho_noi  — CHỜ NỐI LẠI rồi thử lại. Ngủ 500 ms rồi gửi mù vào cái ống đứt là vô nghĩa.
#:   xong     — ý định ĐÃ THÀNH sẵn. Không phải lỗi: đóng một vị thế đã đóng thì mục
#:              tiêu vẫn đạt. Đây là chỗ dễ đếm nhầm thành hỏng nhất.
#:   dung     — KHÔNG thử lại. Thử nữa là tự lừa mình.
#:   nguoi    — máy không chữa được. Dừng và NÓI RÕ người phải làm gì.
XU_LY = {
    10004: "noi",       # requote
    10006: "dung",      # sàn từ chối thẳng
    10011: "thu",       # lỗi xử lý phía sàn
    10012: "thu",       # hết giờ chờ
    10013: "?",         # ⚠ MÃ HAI NGHĨA — xem `LUONG_LU`, phải hỏi terminal mới biết
    10014: "dung",      # khối lượng không hợp lệ
    10015: "noi",       # giá không hợp lệ
    10016: "kep",       # SL/TP quá sát giá  ← lỗi ta gặp thật
    10017: "nguoi",     # sàn tắt giao dịch cho tài khoản này
    10018: "nguoi",     # chợ đóng cửa
    10019: "nguoi",     # không đủ tiền
    10020: "noi",       # giá đã đổi
    10021: "noi",       # không có giá
    10022: "dung",      # hạn lệnh không hợp lệ
    10023: "thu",       # lệnh vừa đổi trạng thái — đọc lại rồi thử
    10024: "cho_lau",   # gửi quá nhiều yêu cầu  ← nghỉ, đừng dồn thêm
    10025: "xong",      # không có gì thay đổi → SL/TP vốn đã đúng rồi
    10026: "nguoi",     # sàn tắt AutoTrading phía server
    10027: "nguoi",     # AlgoTrading tắt — người dùng phải bấm, máy không tự chữa được
    10028: "dung",      # lệnh/vị thế bị khoá
    10029: "cho_lau",   # ĐÓNG BĂNG (freeze level)  ← lỗi ta gặp thật, và nó tự tan
    10030: "doi_fill",  # sàn không nhận kiểu khớp
    10031: "cho_noi",   # mất kết nối  ← lỗi ta gặp thật; ngủ rồi gửi mù là SAI BẢN CHẤT
    10032: "nguoi",     # thao tác chỉ cho tài khoản thật
    10033: "dung",      # vượt số lệnh chờ tối đa
    10034: "dung",      # vượt giới hạn khối lượng
    10035: "dung",      # loại lệnh không hợp lệ
    10036: "xong",      # VỊ THẾ ĐÃ ĐÓNG  ← gặp thật; muốn đóng mà nó đóng rồi thì… đạt
    10038: "dung",      # khối lượng đóng vượt khối lượng vị thế
    10039: "dung",      # đã có lệnh đóng cho vị thế này
    10040: "dung",      # vượt số vị thế tối đa
    10041: "thu",       # sàn huỷ lệnh — thử lại
    10042: "dung",      # symbol chỉ cho MUA
    10043: "dung",      # symbol chỉ cho BÁN
    10044: "dung",      # symbol chỉ cho ĐÓNG
    10045: "dung",      # phải đóng theo FIFO
    10046: "nguoi",     # tài khoản CẤM hedging — chiến lược nhiều lệnh song song sẽ sai
}

#: Việc NGƯỜI phải làm. Mỗi câu phải hành động được ngay — in `retcode=10027` ra là bắt
#: người dùng đi tra bảng mã đúng lúc họ đang bí.
CAN_NGUOI = {
    10017: "Sàn TẮT giao dịch cho tài khoản này — phải hỏi sàn.",
    10018: "Thị trường đang ĐÓNG CỬA — chờ tới phiên rồi chạy lại.",
    10019: "Không đủ tiền — nạp thêm hoặc giảm lot.",
    10026: "Sàn tắt AutoTrading phía SERVER — phải hỏi sàn.",
    10027: "AlgoTrading đang TẮT trên MT5 — bấm nút AlgoTrading rồi chạy lại.",
    10032: "Thao tác này chỉ chạy được trên tài khoản THẬT.",
    10046: "Tài khoản KHÔNG cho hedging — chiến lược nhiều lệnh song song sẽ chạy sai.",
}

#: MÃ MÀ BẢN THÂN MÃ KHÔNG ĐỦ ĐỂ QUYẾT — phải hỏi terminal.
#:
#: ⚠ Đo được, và nó đốt sạch một lần hiệu chuẩn: terminal trả `10013` cho hai chuyện
#: khác hẳn nhau —
#:    • yêu cầu sai tham số thật    → thử lại vô ích
#:    • KHÔNG GỬI ĐI ĐƯỢC lúc này   → rất đáng thử lại (trả về trong 0.1 ms, chưa hề
#:      ra tới sàn)
#: Xếp cứng nó vào `dung` thì mọi lần ống đứt đều bị đọc thành "sai tham số", bỏ cuộc
#: ngay lần thử đầu, và vòng lặp cứ tăng `thu_lai` — một con số không bao giờ được
#: dùng tới. Không nhìn mã mà đoán được; phải hỏi thẳng terminal đang nối hay không.
LUONG_LU = {10013}


def _dang_noi():
    """Terminal có đang nối tới sàn không. Không bao giờ ném."""
    try:
        tt = mt5.terminal_info()
        return bool(tt is not None and getattr(tt, "connected", False))
    except Exception:                           # noqa: BLE001
        return False


def _xu_ly(m):
    """Mã → cách xử. Trả None nếu chưa có luật cho mã này."""
    xu = XU_LY.get(m)
    if xu == "?":
        return "dung" if _dang_noi() else "cho_noi"
    return xu


#: MÃ CHƯA CÓ LUẬT — `{mã: số lần gặp}`.
#:
#: ⚠ Đây là chỗ CÁI CHƯA BIẾT chịu lộ mặt. Không ai liệt kê hết được mọi cách một sàn
#: từ chối lệnh, nên thay vì cố đoán cho đủ, hệ thống ĐẾM những mã nó đã gặp mà chưa có
#: cách xử rồi hiện ra. Bản trước `XU_LY.get(ma, "thu")` nuốt mã lạ vào nhánh mặc định —
#: nó vẫn chạy, có khi chạy đúng, nhưng không ai biết ta vừa gặp một thứ chưa hiểu.
CHUA_BIET = {}

#: Thứ tự thử kiểu khớp khi sàn không nhận cái đang dùng.
_FILL = (0, 1, 2)       # FOK, IOC, RETURN


# ---------------------------------------------------------------------------
# Bếp núc
# ---------------------------------------------------------------------------
def _them(bg, khoa, gt):
    """Thêm một dòng vào sổ, không lặp — cùng một cách sửa lặp 4 lần vẫn là một cách."""
    if gt and gt not in bg[khoa]:
        bg[khoa].append(gt)


def _bg(y_dinh):
    """Sổ trắng cho một thao tác. Hình dạng này là hợp đồng với `ket_noi` và giao diện."""
    return {"y_dinh": y_dinh,
            #: sửa TRƯỚC khi gửi — phòng vệ đoán đúng nên sàn không kịp từ chối.
            #: Đây là bằng chứng MẠNH NHẤT rằng giả thuyết đúng.
            "sua_truoc": [],
            #: sửa SAU khi bị từ chối — phòng vệ chữa được, vẫn tính là đạt.
            "da_sua": [],
            #: mã lạ gặp trong thao tác này, để vòng hiệu chuẩn nêu tên.
            "la": [],
            "so_lan": 0, "ket": "hong", "ma": None, "ticket": None,
            "gia_khop": None, "truot": None, "chu": "",
            #: giá trị THẬT SỰ dùng được ở lần thành công — nguyên liệu để hiệu chuẩn
            #: học: biết `filling` nào sàn nhận thì mọi lệnh sau đỡ một vòng thử.
            "fill_dung": None, "kep_dung": None, "dev_dung": None}


def cho_noi_lai(giay=30):
    """Chờ cầu nối sống lại THẬT. Trả True nếu nối lại được trong `giay` giây.

    ⚠ Vì sao không `sleep` rồi gửi tiếp: `10031` nghĩa là cái ống đứt. Ngủ 500 ms rồi
    ném lệnh vào cái ống vẫn đứt thì thử 4 lần cũng hỏng cả 4 — đo được, đúng bằng bài
    hiệu chuẩn. Phải chờ tới lúc nó THẬT SỰ nối lại rồi mới gửi, và gửi ngay lúc đó."""
    if mt5 is None:
        return False
    het = time.time() + float(giay)
    while time.time() < het:
        if _dang_noi():
            return True
        try:
            # Cầu nối Python↔terminal cũng có thể đứt, không chỉ terminal↔sàn. Dựng lại —
            # an toàn vì `nn._KetNoi` đang giữ tay đếm, không ai shutdown giữa chừng.
            if mt5.terminal_info() is None:
                mt5.initialize()
        except Exception:                       # noqa: BLE001
            pass
        time.sleep(0.5)
    return _dang_noi()


def _kep(gia, sl, tp, mua, toi_thieu, diem):
    """Đẩy SL/TP ra cho đủ khoảng tối thiểu. Trả (sl, tp, đã_sửa_gì)."""
    if not toi_thieu or not diem:
        return sl, tp, None
    xa = toi_thieu * diem
    sua = []
    if sl:
        moi = min(sl, gia - xa) if mua else max(sl, gia + xa)
        if abs(moi - sl) > diem / 2:
            sua.append(f"SL {sl:.3f}→{moi:.3f}")
            sl = moi
    if tp:
        moi = max(tp, gia + xa) if mua else min(tp, gia - xa)
        if abs(moi - tp) > diem / 2:
            sua.append(f"TP {tp:.3f}→{moi:.3f}")
            tp = moi
    return sl, tp, (" · ".join(sua) or None)


def _tt_dau(L, si):
    """Trạng thái điều chỉnh lúc bắt đầu — lấy từ luật, ngã về con số sàn khai."""
    kep = L["kep_stops"] if L["kep_stops"] is not None \
        else int(getattr(si, "trade_stops_level", 0))
    fill = L["filling"] if L["filling"] is not None \
        else max(0, int(getattr(si, "filling_mode", 1)) - 1)
    return {"dev": int(L["deviation"]), "kep": int(kep or 0), "fill": int(fill)}


def _chay(L, bg, tt, dung_yc):
    """VÒNG THỬ DÙNG CHUNG cho mọi thao tác chạm sàn.

    `dung_yc(tt)` dựng dict yêu cầu từ trạng thái điều chỉnh hiện tại, hoặc trả None
    nếu chưa dựng được (chưa có tick). Mỗi lần bị từ chối, `tt` được sửa theo luật rồi
    `dung_yc` dựng lại — nên cách sửa nằm ở MỘT chỗ cho cả bảy thao tác.

    Trả đối tượng kết quả của MT5 nếu đạt, None nếu không. `bg` bị sửa tại chỗ."""
    for _ in range(int(L["thu_lai"]) + 1):
        bg["so_lan"] += 1
        yc = dung_yc(tt)
        if yc is None:
            # ⚠ Hỏng TRƯỚC khi gửi, nên không có retcode nào để phân loại — mọi luật xử
            # lý retcode đều không với tới. Gặp thật lúc ống vừa đứt.
            bg["ma"], bg["chu"] = None, "không có tick — chờ giá về"
            _them(bg, "da_sua", "chờ tick")
            if not cho_noi_lai(min(5.0, float(L["cho_noi_giay"]))):
                time.sleep(L["cho_ms"] / 1000)
            continue

        r = mt5.order_send(yc)
        ma = getattr(r, "retcode", None)
        bg["ma"] = ma
        if r is not None and ma == mt5.TRADE_RETCODE_DONE:
            bg["ket"] = "ok"
            bg["chu"] = ""          # xoá lý do hỏng của lần thử trước — đã qua rồi
            bg["kep_dung"], bg["dev_dung"] = tt["kep"], tt["dev"]
            # ⚠ CHỈ ghi `fill_dung` khi yêu cầu THẬT SỰ mang `type_filling`. Sửa SL/TP
            # hay huỷ lệnh chờ không đụng tới kiểu khớp, nên "thành công" của chúng
            # không nói gì về kiểu khớp cả — ghi bừa thì bài hiệu chuẩn học nhầm một
            # con số vô nghĩa và mọi lệnh sau đó lại tốn một vòng thử.
            if "type_filling" in yc:
                bg["fill_dung"] = tt["fill"]
            return r

        m = int(ma or 0)
        xu = _xu_ly(m)
        if xu is None and m:
            CHUA_BIET[m] = CHUA_BIET.get(m, 0) + 1
            if m not in bg["la"]:
                bg["la"].append(m)
            _them(bg, "da_sua", f"mã {m} CHƯA CÓ LUẬT — thử lại tạm")
            xu = "thu"

        if xu == "xong":
            # Không phải lỗi: thứ ta muốn vốn đã đúng rồi (vị thế đã đóng, SL vốn ở đó).
            bg["ket"] = "ok"
            bg["chu"] = f"ý định vốn đã thành (mã {ma})"
            bg["kep_dung"], bg["dev_dung"] = tt["kep"], tt["dev"]
            return None
        if xu == "nguoi":
            bg["ket"] = "nguoi"
            bg["chu"] = CAN_NGUOI.get(m, f"cần người xử lý (mã {ma})")
            return None
        if xu == "dung":
            bg["ket"] = "bo"
            bg["chu"] = f"không thử lại (mã {ma})"
            return None

        if xu == "noi":
            tt["dev"] = min(tt["dev"] * 3, 2000)
            _them(bg, "da_sua", f"nới deviation → {tt['dev']}")
        elif xu == "kep":
            tt["kep"] = max(tt["kep"] * 2, 50) if tt["kep"] else 50
            _them(bg, "da_sua", f"kẹp SL/TP → {tt['kep']} điểm")
        elif xu == "doi_fill":
            tt["fill"] = _FILL[(_FILL.index(tt["fill"]) + 1) % len(_FILL)] \
                if tt["fill"] in _FILL else 1
            _them(bg, "da_sua", f"đổi filling → {tt['fill']}")
        elif xu == "cho_noi":
            _them(bg, "da_sua", "chờ NỐI LẠI rồi gửi")
            if not cho_noi_lai(L["cho_noi_giay"]):
                bg["ket"] = "bo"
                bg["chu"] = (f"mất kết nối quá {L['cho_noi_giay']}s — "
                             f"chờ nối lại không được")
                return None
            continue                        # nối lại rồi thì gửi NGAY, không ngủ thêm
        elif xu == "cho_lau":
            _them(bg, "da_sua", f"chờ {L['cho_bang_ms']} ms rồi thử lại")
            time.sleep(L["cho_bang_ms"] / 1000)
            continue
        time.sleep(L["cho_ms"] / 1000)

    bg["ket"] = "bo"
    # `mã None` là câu vô nghĩa với người đọc: nó nghĩa là chết TRƯỚC khi gửi được gì,
    # tức không có sàn nào từ chối cả — ống đứt. Nói đúng thứ đó ra.
    bg["chu"] = (f"thử {bg['so_lan']} lần vẫn hỏng (mã {bg['ma']})" if bg["ma"]
                 else f"mất kết nối / không có giá suốt {bg['so_lan']} lần thử — "
                      f"chưa gửi được gì tới sàn")
    return None


def _mo_symbol(symbol):
    si = mt5.symbol_info(symbol)
    if si is None:
        mt5.symbol_select(symbol, True)
        si = mt5.symbol_info(symbol)
    return si


def _vi_the(symbol, pos):
    """LUÔN đọc lại từ sàn, kể cả khi người gọi đưa sẵn đối tượng vị thế.

    ⚠ Bản trước nhận đối tượng thì dùng luôn. Nhưng đối tượng vị thế là ẢNH CHỤP tại
    một thời điểm — giữa lúc chụp và lúc dùng, SL có thể đã dính và vị thế đã đóng.
    Cầm cái ảnh đó gọi tiếp thì terminal từ chối TẠI CHỖ trong 0.1 ms với mã `10013`,
    và ta đọc thành "yêu cầu sai tham số" rồi bỏ cuộc. Gặp thật, và nó giết trọn vòng 1
    của một lần hiệu chuẩn.

    Đọc lại một lần là hết: hoặc vị thế còn đó, hoặc trả None và người gọi biết rõ."""
    so = int(pos) if isinstance(pos, int) else int(getattr(pos, "ticket", 0) or 0)
    if not so:
        return None
    for p in (mt5.positions_get(symbol=symbol) or ()):
        if int(p.ticket) == so:
            return p
    return None


def _khung(y_dinh, symbol, than):
    """Vỏ chung: dựng sổ, mở cầu nối, bắt mọi lỗi. `than(bg, L, si, diem)` làm phần việc.

    Không hàm công khai nào ở đây được phép ném — mọi hỏng hóc phải là một bản ghi đọc
    được, vì đầu bên kia là vòng hiệu chuẩn đang tự sửa mình, không phải người đọc log.
    """
    def chay(L):
        bg = _bg(y_dinh)
        if mt5 is None or not nn.CO_MT5:
            bg["chu"] = "Máy chưa cài thư viện MetaTrader5."
            return bg
        try:
            with nn._KetNoi():
                si = _mo_symbol(symbol)
                if si is None:
                    bg["chu"] = f'Sàn không có symbol "{symbol}".'
                    return bg
                than(bg, L, si, float(si.point) or 0.01)
        except Exception as e:                  # noqa: BLE001
            bg["chu"] = f"{type(e).__name__}: {e}"
        return bg
    return chay


# ---------------------------------------------------------------------------
# BẢY THAO TÁC — tất cả đi qua cùng một vòng thử
# ---------------------------------------------------------------------------
def gui(symbol, mua, lot, sl=None, tp=None, gia=None, magic=0, chu="", luat=None):
    """MỞ lệnh thị trường. Trả bản ghi đầy đủ: ý định, thứ đã phải sửa, kết cục."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))
    moc = {}

    def than(bg, L, si, diem):
        tt = _tt_dau(L, si)

        def dung_yc(tt):
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            g = float(gia or (tick.ask if mua else tick.bid))
            moc["g"] = g
            # Kẹp NGAY TỪ ĐẦU theo con số đã hiệu chuẩn — đừng đợi sàn từ chối rồi mới
            # sửa. Sàn khai `trade_stops_level` thường sai (đo được: khai 0, thật 215).
            s2, t2, sua = _kep(g, sl, tp, mua, tt["kep"], diem)
            if sua:
                _them(bg, "sua_truoc" if bg["so_lan"] <= 1 else "da_sua", sua)
            yc = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": lot,
                  "type": mt5.ORDER_TYPE_BUY if mua else mt5.ORDER_TYPE_SELL,
                  "price": g, "deviation": tt["dev"], "magic": magic, "comment": chu}
            if s2:
                yc["sl"] = round(s2, si.digits)
            if t2:
                yc["tp"] = round(t2, si.digits)
            if tt["fill"] in _FILL:
                yc["type_filling"] = tt["fill"]
            return yc

        r = _chay(L, bg, tt, dung_yc)
        if r is not None:
            bg["ticket"] = int(r.order)
            bg["gia_khop"] = float(r.price)
            bg["truot"] = round((float(r.price) - moc.get("g", r.price)) / diem
                                * (1 if mua else -1), 1)

    return _khung({"viec": "mo", "mua": bool(mua), "lot": lot, "sl": sl, "tp": tp},
                  symbol, than)(L)


def sua_stops(symbol, pos, sl=None, tp=None, luat=None):
    """GẮN / SỬA SL·TP cho một vị thế — cùng tầng phòng vệ với lúc mở.

    ⚠ Đây là chỗ hỏng nhiều nhất trong lần chạy thật: `10016` (quá sát) và `10029`
    (vừa mở xong, vị thế còn đóng băng). Cả hai đều chữa được — nếu đi qua đây."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))

    def than(bg, L, si, diem):
        p = _vi_the(symbol, pos)
        if p is None:
            # Không phải hỏng: không còn vị thế thì cũng không còn gì để bảo vệ.
            bg["ket"], bg["chu"] = "ok", "vị thế không còn — không có gì để sửa"
            return
        mua = int(p.type) == 0
        g = float(p.price_open)
        bg["ticket"] = int(p.ticket)
        tt = _tt_dau(L, si)

        def dung_yc(tt):
            s2, t2, sua = _kep(g, sl, tp, mua, tt["kep"], diem)
            if sua:
                _them(bg, "sua_truoc" if bg["so_lan"] <= 1 else "da_sua", sua)
            return {"action": mt5.TRADE_ACTION_SLTP, "symbol": symbol,
                    "position": int(p.ticket),
                    "sl": round(s2, si.digits) if s2 else 0.0,
                    "tp": round(t2, si.digits) if t2 else 0.0}

        _chay(L, bg, tt, dung_yc)

    return _khung({"viec": "sua_stops", "sl": sl, "tp": tp}, symbol, than)(L)


def dong(symbol, pos, luat=None):
    """ĐÓNG một vị thế. `10036` (đã đóng rồi) là ĐẠT, không phải hỏng."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))
    moc = {}

    def than(bg, L, si, diem):
        p = _vi_the(symbol, pos)
        if p is None:
            bg["ket"], bg["chu"] = "ok", "vị thế không còn — coi như đã đóng"
            return
        mua = int(p.type) == 0
        bg["ticket"] = int(p.ticket)
        tt = _tt_dau(L, si)

        def dung_yc(tt):
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            g = float(tick.bid if mua else tick.ask)
            moc["g"] = g
            yc = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol,
                  "volume": float(p.volume), "position": int(p.ticket),
                  "type": mt5.ORDER_TYPE_SELL if mua else mt5.ORDER_TYPE_BUY,
                  "price": g, "deviation": tt["dev"], "magic": int(p.magic),
                  "comment": "CatStudio dong"}
            if tt["fill"] in _FILL:
                yc["type_filling"] = tt["fill"]
            return yc

        r = _chay(L, bg, tt, dung_yc)
        if r is not None:
            bg["gia_khop"] = float(r.price)
            bg["truot"] = round((moc.get("g", r.price) - float(r.price)) / diem
                                * (1 if mua else -1), 1)

    return _khung({"viec": "dong"}, symbol, than)(L)


def dat_cho(symbol, mua, lot, gia, sl=None, tp=None, magic=0, chu="", luat=None):
    """ĐẶT lệnh chờ (limit). Kẹp SL/TP theo giá ĐẶT, không theo giá hiện tại."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))

    def than(bg, L, si, diem):
        tt = _tt_dau(L, si)

        def dung_yc(tt):
            s2, t2, sua = _kep(float(gia), sl, tp, mua, tt["kep"], diem)
            if sua:
                _them(bg, "sua_truoc" if bg["so_lan"] <= 1 else "da_sua", sua)
            yc = {"action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": lot,
                  "type": mt5.ORDER_TYPE_BUY_LIMIT if mua else mt5.ORDER_TYPE_SELL_LIMIT,
                  "price": round(float(gia), si.digits),
                  "type_time": mt5.ORDER_TIME_GTC, "magic": magic, "comment": chu}
            if s2:
                yc["sl"] = round(s2, si.digits)
            if t2:
                yc["tp"] = round(t2, si.digits)
            return yc

        r = _chay(L, bg, tt, dung_yc)
        if r is not None:
            bg["ticket"] = int(r.order)

    return _khung({"viec": "dat_cho", "mua": bool(mua), "lot": lot, "gia": gia},
                  symbol, than)(L)


def sua_cho(symbol, ticket, gia, sl=None, tp=None, luat=None):
    """SỬA giá (và SL/TP) của một lệnh chờ."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))

    def than(bg, L, si, diem):
        bg["ticket"] = int(ticket)
        tt = _tt_dau(L, si)

        def dung_yc(tt):
            yc = {"action": mt5.TRADE_ACTION_MODIFY, "order": int(ticket),
                  "price": round(float(gia), si.digits),
                  "type_time": mt5.ORDER_TIME_GTC}
            if sl:
                yc["sl"] = round(float(sl), si.digits)
            if tp:
                yc["tp"] = round(float(tp), si.digits)
            return yc

        _chay(L, bg, tt, dung_yc)

    return _khung({"viec": "sua_cho", "gia": gia}, symbol, than)(L)


def huy_cho(symbol, ticket, luat=None):
    """HUỶ một lệnh chờ. Lệnh không còn nữa cũng là đạt — mục tiêu vẫn thành."""
    L = dict(LUAT_MAC_DINH, **(luat or {}))

    def than(bg, L, si, diem):
        bg["ticket"] = int(ticket)
        _chay(L, bg, _tt_dau(L, si),
              lambda tt: {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket)})

    return _khung({"viec": "huy_cho"}, symbol, than)(L)
