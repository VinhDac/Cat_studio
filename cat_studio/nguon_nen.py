"""Nguồn nến — chỗ DUY NHẤT trong app biết MetaTrader 5 tồn tại.

Mọi module khác chỉ thấy một mảng numpy. Nhờ vậy đổi nguồn (CSV, sàn khác, dữ liệu
tick) chỉ phải sửa một file, và backtest chạy được khi MT5 đang TẮT — miễn là đã tải.

BA QUYẾT ĐỊNH ĐÃ CHỐT (core.md §12.1, §12.11)
---------------------------------------------
1. **Chỉ tải M1.** M5 / M15 / H1 gộp từ M1. Một bộ dữ liệu, không tải chồng nhiều khung.
   M1 cũng là nền mô phỏng: giá đi tới đâu, lệnh khớp lúc nào đều xét theo nến M1.

2. **Một symbol giữ đúng MỘT DẢI LIỀN.** Chọn khoảng chồng lấn thì chỉ tải phần thiếu;
   chọn khoảng rời hẳn thì tải luôn phần ở giữa cho liền. Dữ liệu vụn thành nhiều mảnh
   là mời gọi một lớp lỗi rất khó thấy: backtest chạy qua chỗ thủng mà không biết.

3. **Không bao giờ tải lén.** `khoang_thieu()` + `uoc_tinh()` cho biết sẽ tải bao nhiêu
   nến, bao nhiêu MB; giao diện hỏi rồi mới gọi `tai()`.

MẤY CÁI BẪY ĐÃ ĐO, ĐỌC TRƯỚC KHI SỬA
-------------------------------------
* **`t` là giờ SERVER của sàn, không phải UTC.** MT5 trả epoch tính theo múi giờ server.
  Đừng "sửa cho đúng UTC" — mọi thứ khác trong app (nến M5 khép lúc nào, phiên nào,
  cuối tuần ở đâu) đều phải theo đúng cái đồng hồ mà sàn dựng nến, nếu không biên nến
  sẽ lệch và vùng nén đếm sai.

* **`copy_rates_range` bị chặn bởi "Max bars in chart" của terminal.** Xin một năm M1
  (~374 000 nến) một phát thì có thể trả về thiếu mà KHÔNG báo lỗi — đúng kiểu hỏng im
  lặng tệ nhất. Nên chia lô theo `NGAY_MOI_LO` ngày và ghép lại.

* **Không lưu spread từng nến.** MT5 có trả cột đó, nhưng mô hình đã chốt là spread một
  con số trong cài đặt (§12.3). Lưu thêm 4 B mỗi nến để rồi không ai đọc là phình dữ
  liệu vô ích. Thay vào đó `tai()` đo TRUNG VỊ spread và cất vào meta — đủ để giao diện
  gợi ý một con số đúng thay vì bắt người dùng đoán.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np

from . import luu_tru

try:
    import MetaTrader5 as mt5
    CO_MT5 = True
except Exception:                                        # pragma: no cover
    mt5 = None
    CO_MT5 = False


#: Một nến M1. 48 byte — một năm XAUUSD (~374k nến) khoảng 18 MB.
#: `t` = epoch giây, GIỜ SERVER. `vol` = tick volume.
DTYPE = np.dtype([("t", "<i8"), ("o", "<f8"), ("h", "<f8"),
                  ("l", "<f8"), ("c", "<f8"), ("vol", "<i8")])

#: Chia lô khi tải. 30 ngày M1 ≈ 31 000 nến — thoải mái dưới mọi giới hạn terminal.
NGAY_MOI_LO = 30

#: Số nến M1 ước tính mỗi ngày lịch. Forex chạy ~5/7 ngày, 1440 nến/ngày giao dịch.
NEN_MOI_NGAY = 1440 * 5 / 7


# ---------------------------------------------------------------------------
# Thời điểm — nhận datetime / chuỗi ISO / epoch, trả về epoch giây
# ---------------------------------------------------------------------------
def thoi_diem(x):
    """Chuẩn hoá về epoch giây (int). Trả None nếu không hiểu được.

    Nhận nhiều kiểu vì nó nằm ngay ranh giới với giao diện: JS gửi chuỗi `"2025-01-01"`,
    Python nội bộ dùng `datetime`, còn mảng nến dùng epoch."""
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return int(x)
    if isinstance(x, datetime):
        d = x if x.tzinfo else x.replace(tzinfo=timezone.utc)
        return int(d.timestamp())
    if isinstance(x, str):
        s = x.strip().replace("/", "-")
        for dinh in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return int(datetime.strptime(s[:len(dinh) + 2].strip(), dinh)
                           .replace(tzinfo=timezone.utc).timestamp())
            except ValueError:
                continue
    return None


def _ngay(epoch):
    """Epoch -> chuỗi `YYYY-MM-DD HH:MM` để hiện cho người đọc."""
    if epoch is None:
        return "—"
    return datetime.fromtimestamp(int(epoch), timezone.utc).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Chỗ cất
# ---------------------------------------------------------------------------
def _ten_file(symbol):
    """Tên file an toàn. Symbol của sàn có thể mang hậu tố lạ (`XAUUSD.m`, `XAUUSD#`)."""
    return luu_tru._ten_an_toan(str(symbol).strip().upper()) or "SYMBOL"


def _duong(symbol):
    goc = luu_tru.thu_muc_nen()
    ten = _ten_file(symbol)
    return (os.path.join(goc, ten + ".npy"), os.path.join(goc, ten + ".json"))


def doc_meta(symbol):
    """Meta của một bộ nến đã tải. None nghĩa là chưa có gì."""
    _, mj = _duong(symbol)
    try:
        with open(mj, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def doc(symbol, tu=None, den=None):
    """Mảng nến M1 đã tải, cắt theo [tu, den]. Chưa có thì trả mảng RỖNG đúng dtype.

    Trả mảng rỗng chứ không None: chỗ gọi cứ `len()` và cắt lát như thường, không phải
    rải `if is None` khắp bộ chạy."""
    mn, _ = _duong(symbol)
    try:
        a = np.load(mn, allow_pickle=False)
    except Exception:
        return np.empty(0, dtype=DTYPE)
    if a.dtype != DTYPE:                                 # file của bản cũ / hỏng
        return np.empty(0, dtype=DTYPE)
    t0, t1 = thoi_diem(tu), thoi_diem(den)
    if t0 is not None:
        a = a[a["t"] >= t0]
    if t1 is not None:
        a = a[a["t"] <= t1]
    return a


def _mb(duong):
    try:
        return round(os.path.getsize(duong) / (1024 * 1024), 2)
    except OSError:
        return 0.0


def liet_ke():
    """Mọi bộ nến đang giữ — cho bảng nguồn dữ liệu trong Cài đặt.

    Mỗi dòng đủ để trả lời ba câu người dùng hỏi: có dữ liệu từ ngày nào tới ngày nào,
    bao nhiêu nến, và **chiếm bao nhiêu MB** (để quyết định có xoá không)."""
    goc = luu_tru.thu_muc_nen()
    ra = []
    try:
        ds = sorted(f for f in os.listdir(goc) if f.endswith(".npy"))
    except OSError:
        return ra
    for f in ds:
        sym = f[:-4]
        m = doc_meta(sym) or {}
        mn, mj = _duong(sym)
        ra.append({
            "symbol": m.get("symbol", sym),
            "tu": m.get("tu"), "den": m.get("den"),
            "tu_chu": _ngay(m.get("tu")), "den_chu": _ngay(m.get("den")),
            "so_nen": int(m.get("so_nen") or 0),
            "mb": round(_mb(mn) + _mb(mj), 2),
            "digits": m.get("digits"), "point": m.get("point"),
            "contract_size": m.get("contract_size"),
            "spread_tb": m.get("spread_tb"),
            "tai_luc": m.get("tai_luc"),
        })
    return ra


def xoa(symbol):
    """Xoá hẳn một bộ nến. Trả True nếu có xoá được cái gì."""
    da = False
    for p in _duong(symbol):
        try:
            os.remove(p)
            da = True
        except OSError:
            pass
    return da


# ---------------------------------------------------------------------------
# Còn thiếu những khoảng nào
# ---------------------------------------------------------------------------
def file_du(symbol, m):
    """File `.npy` có thật sự chứa đủ số nến mà meta khai không?

    Meta và mảng nến là HAI file. Một `.npy` cụt (hỏng từ trước bản vá ghi nguyên tử, hay
    do antivirus/đồng bộ đám mây xén) vẫn để meta nguyên vẹn — mà `doc()` bắt mọi lỗi rồi
    lặng lẽ trả mảng RỖNG, còn `khoang_thieu()` chỉ nhìn meta nên khẳng định "đủ rồi".
    App tự khoá mình vào trạng thái chết: không đọc được nến, cũng không bao giờ tải lại.

    Chỉ một lệnh `stat`, không đọc file, nên gọi mỗi lần bấm ▶ cũng không tốn gì."""
    try:
        return os.path.getsize(_duong(symbol)[0]) >= int(m["so_nen"]) * DTYPE.itemsize
    except (OSError, KeyError, TypeError, ValueError):
        return False


def khoang_thieu(symbol, tu, den):
    """Muốn có [tu, den] thì còn phải tải những khoảng nào.

    Một symbol giữ đúng MỘT DẢI LIỀN, nên câu trả lời nhiều nhất là hai khoảng: phần
    trước dải đang có và phần sau nó. Nếu khoảng xin nằm rời hẳn thì phần "ở giữa" tự
    động nằm trong một trong hai khoảng đó — dải vẫn liền sau khi tải.

    Trả `[]` nghĩa là đã đủ, không cần đụng tới MT5."""
    t0, t1 = thoi_diem(tu), thoi_diem(den)
    if t0 is None or t1 is None or t1 <= t0:
        return []
    m = doc_meta(symbol)
    if not m or not m.get("so_nen"):
        return [(t0, t1)]
    if not file_du(symbol, m):
        return [(t0, t1)]
    a, b = int(m["tu"]), int(m["den"])
    ra = []
    # ⚠ Khoảng trái PHẢI kéo tới tận `a`, khoảng phải PHẢI bắt đầu từ tận `b` — kể cả
    # khi khoảng xin nằm RỜI HẲN dải đang có. Viết `min(t1, a)` / `max(t0, b)` thì với
    # một khoảng rời, ta chỉ tải đúng phần mới và để THỦNG một lỗ ở giữa: dải không còn
    # liền, mà bộ chạy sẽ chạy qua chỗ thủng đó mà không biết. Thà tải thừa phần giữa —
    # người dùng đã được báo số MB trước khi bấm.
    if t0 < a:
        ra.append((t0, a))
    if t1 > b:
        ra.append((b, t1))
    return ra


def uoc_tinh(khoang):
    """Ước lượng số nến và số MB của một danh sách khoảng, TRƯỚC khi tải.

    Cố ý ước lượng thô (1440 nến × 5/7 ngày): mục đích chỉ là để người dùng biết mình
    sắp tải 2 MB hay 200 MB. Con số thật hiện ra sau khi tải xong."""
    ngay = sum((b - a) for a, b in khoang) / 86400.0
    so_nen = int(ngay * NEN_MOI_NGAY)
    return {"so_nen": so_nen,
            "mb": round(so_nen * DTYPE.itemsize / (1024 * 1024), 2),
            "so_khoang": len(khoang)}


# ---------------------------------------------------------------------------
# MT5
# ---------------------------------------------------------------------------
class LoiNguon(Exception):
    """Lỗi nói được thành lời cho người dùng, không phải traceback."""


class _KetNoi:
    """`with _KetNoi(): …` — mở MT5, xong thì đóng.

    Đóng lại sau mỗi việc chứ không giữ mãi: app có thể mở hàng giờ, mà giữ một kết nối
    treo tới terminal suốt thời gian đó chỉ để thỉnh thoảng tải nến là chuốc rắc rối
    (người dùng đóng MT5, đổi tài khoản, mất mạng…)."""

    def __enter__(self):
        if not CO_MT5:
            raise LoiNguon("Máy chưa cài thư viện MetaTrader5 (pip install MetaTrader5).")
        if not mt5.initialize():
            ma, mo_ta = mt5.last_error()
            raise LoiNguon(
                f"Không nối được MetaTrader 5 ({ma}: {mo_ta}).\n"
                "Hãy MỞ MT5 và đăng nhập, rồi thử lại. Tải xong thì đóng MT5 vẫn "
                "backtest bình thường.")
        return self

    def __exit__(self, *a):
        try:
            mt5.shutdown()
        except Exception:
            pass
        return False


def thong_tin_symbol(symbol):
    """`digits` / `point` / `contract_size` / spread hiện tại của một symbol.

    Ba con số đầu PHẢI cất cạnh nến: thiếu chúng thì "20 points" không quy ra được tiền,
    và tính lãi/lỗ ra một con số vô nghĩa. Cất rồi thì backtest lại vẫn đúng dù MT5 tắt."""
    with _KetNoi():
        return _thong_tin(symbol)


def _thong_tin(symbol):
    si = mt5.symbol_info(symbol)
    if si is None:
        raise LoiNguon(f'Sàn không có symbol "{symbol}". '
                       f"Kiểm tra lại tên (nhiều sàn thêm hậu tố, ví dụ XAUUSDm).")
    if not si.visible:
        # Symbol ẩn khỏi Market Watch thì `copy_rates_*` trả về rỗng mà không báo lỗi.
        mt5.symbol_select(symbol, True)
        si = mt5.symbol_info(symbol) or si
    return {"symbol": si.name, "digits": si.digits, "point": si.point,
            "contract_size": si.trade_contract_size, "spread_hien_tai": si.spread}


def _lay_lo(symbol, t0, t1):
    """Một lô nến M1 trong [t0, t1] (epoch). Trả mảng thô của MT5."""
    # Nới hai đầu một ngày rồi cắt lại theo epoch: `copy_rates_range` nhận datetime và
    # diễn giải theo UTC, trong khi mốc nến là giờ server — lệch vài giờ là mất nguyên
    # phần rìa. Nới rồi cắt thì không phải đoán múi giờ của sàn.
    d0 = datetime.fromtimestamp(t0, timezone.utc) - timedelta(days=1)
    d1 = datetime.fromtimestamp(t1, timezone.utc) + timedelta(days=1)
    r = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, d0, d1)
    if r is None:
        ma, mo_ta = mt5.last_error()
        raise LoiNguon(f"MT5 từ chối trả nến ({ma}: {mo_ta}).")
    return r


def _sang_dtype(tho):
    """Mảng thô của MT5 -> `DTYPE` của ta. Bỏ cột spread/real_volume (xem đầu file)."""
    a = np.empty(len(tho), dtype=DTYPE)
    a["t"] = tho["time"]
    for k, g in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close")):
        a[k] = tho[g]
    a["vol"] = tho["tick_volume"]
    return a


def _gop(cu, moi):
    """Ghép hai mảng nến thành MỘT DẢI LIỀN: nối, sắp theo thời gian, bỏ trùng."""
    if not len(cu):
        a = moi
    elif not len(moi):
        a = cu
    else:
        a = np.concatenate([cu, moi])
    a = a[np.argsort(a["t"], kind="stable")]
    if len(a) > 1:
        a = a[np.concatenate([[True], np.diff(a["t"]) != 0])]
    return a


def tai(symbol, tu, den, tien_do=None):
    """Tải phần CÒN THIẾU của [tu, den] rồi ghép vào bộ nến của `symbol`.

    `tien_do(da, tong, chu)` được gọi sau mỗi lô — giao diện dùng để vẽ thanh tiến độ.
    Không có gì để tải thì về ngay, KHÔNG đụng tới MT5 (mở terminal không phải chuyện rẻ).
    """
    thieu = khoang_thieu(symbol, tu, den)
    if not thieu:
        m = doc_meta(symbol) or {}
        return {"da_tai": 0, "bo_qua": True, "meta": m,
                "chu": "Đã có đủ dữ liệu cho khoảng này — không tải gì thêm."}

    # Chia nhỏ TRƯỚC khi mở kết nối, để biết tổng số lô mà báo tiến độ.
    lo = []
    for a, b in thieu:
        x = a
        while x < b:
            y = min(x + NGAY_MOI_LO * 86400, b)
            lo.append((x, y))
            x = y

    with _KetNoi():
        tt = _thong_tin(symbol)
        gom, spreads = [], []
        for i, (a, b) in enumerate(lo, 1):
            tho = _lay_lo(tt["symbol"], a, b)
            if len(tho):
                gom.append(_sang_dtype(tho))
                if "spread" in (tho.dtype.names or ()):
                    spreads.append(np.asarray(tho["spread"], dtype=np.int64))
            if tien_do:
                tien_do(i, len(lo), f"{_ngay(a)} → {_ngay(b)}")

    moi = np.concatenate(gom) if gom else np.empty(0, dtype=DTYPE)
    a = _gop(doc(symbol), moi)
    if not len(a):
        raise LoiNguon(
            f'Sàn không trả về nến M1 nào cho "{symbol}" trong khoảng này.\n'
            "Thường là do khoảng ngày nằm ngoài lịch sử sàn giữ, hoặc symbol chưa được "
            "bật trong Market Watch.")

    # Spread TRUNG VỊ, không phải trung bình: vài nến tin tức có spread giãn gấp chục
    # lần sẽ kéo lệch trung bình, mà cái người dùng cần là con số THƯỜNG GẶP để điền
    # vào ô spread.
    sp = int(np.median(np.concatenate(spreads))) if spreads else None

    m = {
        "symbol": tt["symbol"], "tf": "M1",
        "tu": int(a["t"][0]), "den": int(a["t"][-1]), "so_nen": int(len(a)),
        "digits": tt["digits"], "point": tt["point"],
        "contract_size": tt["contract_size"],
        "spread_tb": sp,
        "tai_luc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    }
    mn, mj = _duong(symbol)
    _ghi_nguyen_tu(mn, lambda f: np.save(f, a, allow_pickle=False))
    _ghi_nguyen_tu(mj, lambda f: f.write(
        json.dumps(m, ensure_ascii=False, indent=2).encode("utf-8")))

    return {"da_tai": int(len(moi)), "bo_qua": False, "meta": m,
            "chu": f"Đã tải {len(moi):,} nến · giữ tổng {len(a):,} nến "
                   f"({_ngay(m['tu'])} → {_ngay(m['den'])})".replace(",", ".")}


# ---------------------------------------------------------------------------
# Soát chất lượng — thứ bộ chạy PHẢI biết trước khi tin vào dữ liệu
# ---------------------------------------------------------------------------
def _ghi_nguyen_tu(duong, ghi):
    """Ghi ra file TẠM rồi đổi tên đè lên — đổi tên trên NTFS là một thao tác nguyên tử.

    Vì sao bắt buộc riêng ở đây: `np.save` ghi thẳng lên file đích, tức nó CẮT CỤT bộ nến
    cũ rồi mới ghi lại. Ngắt giữa chừng (bấm ✕, mất điện, antivirus xen vào) thì `.npy`
    cụt còn `.json` meta vẫn mô tả bộ dữ liệu không còn tồn tại nữa — và từ đó `doc()`
    lặng lẽ trả mảng rỗng trong khi `khoang_thieu()` (chỉ nhìn meta) khẳng định không
    thiếu gì, nên app KHÔNG BAO GIỜ tải lại. Tự khoá mình vào trạng thái chết. Đo được:
    ngắt tiến trình đúng lúc `np.save` thì 20/20 lần khoá chết.

    Cách này ngắt ở đâu cũng chỉ để lại một file `.tmp` rác, còn bản cũ nguyên vẹn."""
    tam = duong + ".tmp"
    with open(tam, "wb") as f:
        ghi(f)
        f.flush()
        os.fsync(f.fileno())        # ép xuống đĩa TRƯỚC khi đổi tên, không chỉ vào cache
    os.replace(tam, duong)


def lo_hong(symbol, tu=None, den=None, nguong_phut=2):
    """Những chỗ THỦNG trong chuỗi nến M1: (bắt đầu, kết thúc, số phút).

    Vì sao phải có: luật vùng nén đếm "nến LIÊN TIẾP", mà cuối tuần và giờ sàn nghỉ để
    lại những khoảng trống dài. Bộ chạy dùng danh sách này để cho vùng nén CHẾT khi vắt
    qua một lỗ (core.md §12.6b) thay vì đếm xuyên 48 giờ chợ đóng cửa như không có gì.

    `nguong_phut=2` nghĩa là hai nến cách nhau quá 2 phút thì tính là lỗ."""
    a = doc(symbol, tu, den)
    if len(a) < 2:
        return []
    d = np.diff(a["t"])
    idx = np.nonzero(d > nguong_phut * 60)[0]
    return [(int(a["t"][i]), int(a["t"][i + 1]), int(d[i] // 60)) for i in idx]


def tom_tat(symbol, tu=None, den=None):
    """Một dòng sự thật về dữ liệu đang có — cho bảng Cài đặt và cho nhật ký lần chạy."""
    a = doc(symbol, tu, den)
    lh = lo_hong(symbol, tu, den)
    m = doc_meta(symbol) or {}
    return {
        "symbol": m.get("symbol", symbol),
        "so_nen": int(len(a)),
        "tu_chu": _ngay(int(a["t"][0])) if len(a) else "—",
        "den_chu": _ngay(int(a["t"][-1])) if len(a) else "—",
        "so_lo_hong": len(lh),
        "lo_hong_dai_nhat": max((x[2] for x in lh), default=0),
        "digits": m.get("digits"), "point": m.get("point"),
        "contract_size": m.get("contract_size"), "spread_tb": m.get("spread_tb"),
    }
