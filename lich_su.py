"""Lịch sử các lần chạy backtest.

⭐ Ý CHÍNH: **không lưu kết quả, lưu thứ ĐẺ RA kết quả.**

Bộ chạy tất định và một năm chỉ mất 2,9 giây, nên một mục lịch sử chỉ cần chứa ĐẦU VÀO
(sơ đồ đã đóng băng + cài đặt + dấu vết dữ liệu nguồn) kèm một BẢN TÓM TẮT nhỏ để mở ra
là thấy ngay. Lưu cả `KetQua` thì riêng nhật ký đã 3,3 MB một lần chạy; lưu đầu vào +
tóm tắt thì **~40 KB**. Muốn xem lại phát lại thì bấm "Mở lại" — chạy lại 3 giây và ra
nguyên bộ chart · nhật ký · bảng số liệu, giống hệt tới từng id lệnh (`so_lenh.py` hứa
thế và có bài kiểm cho lời hứa đó).

MỀM hay ĐÃ LƯU chỉ khác nhau ở MỘT chỗ: có `ten` hay không.

* `ten = None` → mục mềm, tự ghi mỗi lần bấm ▶, bị cuốn chiếu khi quá `GIU`.
* `ten = "..."` → đã lưu, **không bao giờ bị cuốn**. Cái tên mới là thứ làm nó tìm lại
  được sau ba tháng — `hôm qua 22:41` thì tháng sau chẳng nói lên gì.

Một thư mục, một định dạng, nên `Mở lại` chạy y hệt nhau ở cả hai danh sách — không có
hai đường code để lệch nhau.
"""
import json
import os
import time

import luu_tru
import nhat_ky

#: Giữ bao nhiêu mục MỀM. Mục đã đặt tên không tính vào đây.
GIU = 20


def _thu_muc():
    return luu_tru._thu_muc("lich_su")


def _duong(ma):
    return os.path.join(_thu_muc(), f"{ma}.json")


def _ma_moi():
    """Mã mục = mốc thời gian, nên sắp theo tên file cũng là sắp theo thời gian.

    Trùng thì thêm hậu tố. Không đoán độ phân giải đồng hồ cho đủ mịn — cứ HỎI ĐĨA: mốc
    giây thôi thì hai lần chạy khép trong cùng một giây ghi đè nhau, mất im lặng một mục;
    mà thêm phần trăm giây cũng chỉ đẩy xác suất xuống chứ không khử được. Đây thì khử
    hẳn, và đọc ra vẫn hiểu ngay là lần chạy nào."""
    goc = time.strftime("%Y%m%d-%H%M%S")
    ma, n = goc, 1
    while os.path.exists(_duong(ma)):
        ma, n = f"{goc}-{n}", n + 1
    return ma


#: Bản GỌN của từng mục, theo `ma`. Xem `liet_ke`.
_dem = {}


def ghi(kq, cd, tom_tat):
    """Ghi một lần chạy vào lịch sử. Trả mục vừa ghi, hoặc `None` nếu bỏ qua.

    BỎ QUA khi lần chạy này giống hệt mục mới nhất — cùng vân tay sơ đồ và cùng cài đặt
    thì kết quả giống hệt (bộ chạy tất định), một dòng nữa không mang thêm thông tin
    nào. Chỉ dập lại mốc thời gian của mục cũ."""
    vt = nhat_ky._van_tay(kq.doc)
    ci = _cai_dat(cd)
    ds = liet_ke()
    if ds and ds[0]["van_tay"] == vt and ds[0]["cai_dat"] == ci:
        cu = doc(ds[0]["ma"])
        if cu:
            cu["t"] = int(time.time())
            _ghi_file(cu)
            return _gon(cu)
        return None

    m = {
        "ma": _ma_moi(),
        "t": int(time.time()),
        "ten": None,                      # None = mục mềm; có tên = đã lưu
        "ten_chien_luoc": kq.doc.get("name") or "chiến lược",
        "van_tay": vt,
        "cai_dat": ci,
        "doc": kq.doc,                    # đã chuẩn hoá — `bo_chay.chay` chuẩn hoá trước
        # Dấu vết dữ liệu nguồn: `Mở lại` chỉ ra đúng số cũ nếu nến còn y nguyên. Không
        # ghi lại đây thì ba tháng nữa chạy lại ra bộ số khác mà vẫn bảo đó là lần cũ.
        "nguon": {
            "symbol": cd.symbol,
            "so_nen": int(len(kq.nen1)),
            "t_dau": int(kq.nen1["t"][0]) if len(kq.nen1) else 0,
            "t_cuoi": int(kq.nen1["t"][-1]) if len(kq.nen1) else 0,
        },
        "tom_tat": tom_tat,               # đúng payload của `test_thong_ke`
    }
    _ghi_file(m)
    don_dep()
    return _gon(m)


def _cai_dat(cd):
    """Những ô cài đặt THẬT SỰ đổi kết quả. `delay_ms` không nằm đây — nó chỉ là tốc độ
    phát lại, đổi nó mà coi là một lần chạy khác thì lịch sử đầy rác."""
    return {"symbol": cd.symbol, "tu": cd.tu, "den": cd.den,
            "spread_diem": cd.spread_diem, "deposit": cd.deposit,
            "commission": cd.commission, "don_bay": getattr(cd, "don_bay", None)}


def _ghi_file(m):
    _dem.pop(m["ma"], None)             # ghi đè thì bản nhớ tạm cũ hết đúng
    luu_tru.ghi_json_nguyen_tu(_duong(m["ma"]), m)


def doc(ma):
    """Một mục ĐẦY ĐỦ (kèm `doc` và `tom_tat`). `None` nếu không đọc được."""
    try:
        with open(_duong(str(ma)), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _gon(m):
    """Bản GỌN cho danh sách: bỏ `doc` và đường vốn — chúng chiếm gần hết dung lượng mà
    danh sách thì không dùng tới."""
    tt = m.get("tom_tat") or {}
    return {
        # `.get` cho MỌI khoá: `liet_ke` chỉ canh `m.get("ma")` nên một mục thiếu `t`
        # (sửa tay, hoặc đổi định dạng sau này) sẽ ném KeyError và kéo sập CẢ danh sách —
        # mất luôn những mục lành.
        "ma": m.get("ma"), "t": m.get("t", 0), "ten": m.get("ten"),
        "ten_chien_luoc": m.get("ten_chien_luoc"),
        "van_tay": m.get("van_tay"),
        "cai_dat": m.get("cai_dat") or {},
        "nguon": m.get("nguon") or {},
        "thong_ke": tt.get("tk") or {},
    }


def liet_ke():
    """Mọi mục, MỚI NHẤT TRƯỚC. Mục hỏng bị bỏ qua chứ không làm sập cả danh sách.

    ⚠ NHỚ TẠM bản gọn theo `ma`. Không có nó thì mỗi lần gọi phải đọc và parse TOÀN BỘ
    mọi mục — mà một mục nặng ~69 KB, trong đó riêng đường vốn đã 62 KB, còn danh sách
    thì không dùng tới nó. Mỗi lần bấm ▶ gọi hàm này 2-3 lượt: đo được 300 mục = 0,38 s
    mỗi lượt, cộng vào một lần chạy vốn chỉ 2,9 s. Chưa đau vì mục chưa đặt tên bị cuốn
    chiếu, nhưng mục ĐÃ ĐẶT TÊN miễn nhiễm cuốn chiếu (§12.21) nên nó sẽ phình theo thời
    gian dùng.

    An toàn vì `lich_su` là nơi DUY NHẤT ghi/xoá file lịch sử, và cả hai chỗ đó đều dọn
    bộ nhớ tạm — không có đường nào sửa file sau lưng nó."""
    ra = []
    try:
        ten_file = os.listdir(_thu_muc())
    except OSError:
        return ra
    con = set()
    for f in ten_file:
        if not f.endswith(".json"):
            continue
        ma = f[:-5]
        con.add(ma)
        if ma not in _dem:
            m = doc(ma)
            if not (m and m.get("ma")):
                continue
            _dem[ma] = _gon(m)
        ra.append(_dem[ma])
    for ma in [x for x in _dem if x not in con]:      # file bị xoá ngoài app
        _dem.pop(ma, None)
    ra.sort(key=lambda x: x["t"], reverse=True)
    return ra


def dat_ten(ma, ten):
    """Đặt tên = CHUYỂN THÀNH ĐÃ LƯU. `ten` rỗng thì trả về mục mềm."""
    m = doc(ma)
    if not m:
        return None
    m["ten"] = (ten or "").strip() or None
    _ghi_file(m)
    don_dep()
    return _gon(m)


def xoa(ma):
    _dem.pop(str(ma), None)
    try:
        os.remove(_duong(str(ma)))
        return True
    except OSError:
        return False


def don_dep(giu=GIU):
    """Cuốn chiếu: chỉ xoá mục MỀM, và chỉ khi đã quá `giu`. Mục đã đặt tên miễn nhiễm —
    đó là cả điểm của việc đặt tên."""
    mem = [x for x in liet_ke() if not x.get("ten")]
    for x in mem[giu:]:
        xoa(x["ma"])
