"""CHẤM SONG SONG — nhiều TIẾN TRÌNH, không phải nhiều luồng.

    core.md §18.4c

⚠ **Phải là tiến trình, không được là luồng.** `bo_chay.mot_nhip` là Python thuần và
chiếm 98% một lượt chạy (§18.4); GIL cho đúng một luồng chạy bytecode tại một thời điểm,
nên tám luồng chấm backtest nhanh bằng đúng một luồng — có khi chậm hơn vì tranh khoá.

⭐ **Và đây chính là nửa ACTOR của một hệ RL.** Mọi hệ RL chơi game thật đều tách hai
nửa: một đàn tiến trình chạy MÔI TRƯỜNG sinh ván chơi, một tiến trình chạy MẠNG học từ
đống ván ấy. OpenAI Five: ~128.000 lõi CPU cho môi trường, 256 GPU cho mạng. Cái đàn
tiến trình ở file này là nửa thứ nhất, và nó dùng lại được nguyên vẹn khi nào gắn mạng.

⚠ **TÁI LẬP ĐƯỢC là ràng buộc cứng, không phải mong muốn** (§18.5). Cho nên:

    sơ đồ vẫn do TIẾN TRÌNH CHA sinh ra, theo đúng thứ tự của một `random.Random(hạt)`
    kết quả vẫn được gộp vào bảng theo ĐÚNG THỨ TỰ ẤY, không phải thứ tự trả về

Tiến trình con chỉ làm đúng một việc: nhận một sơ đồ, chạy, chấm, trả về mấy con số. Nó
không bốc thăm, không giữ bảng xếp hạng, không biết mình là con thứ mấy. Nhờ vậy chạy 8
nhân ra kết quả y hệt chạy 1 nhân — có bài kiểm canh (`tests/test_song_song.py`).
"""
import multiprocessing as mp
import os

from . import bo_chay, cham_diem

#: Nến · điều kiện chạy · cửa — gửi MỘT LẦN lúc mở tiến trình con, không gửi kèm mỗi sơ
#: đồ. Một năm nến M1 là ~17 MB; đính vào từng tác vụ thì riêng việc đóng gói đã đắt hơn
#: cả lượt chấm.
_NEN = _CD = _CUA = None


def _mo_tien_trinh(nen, cd, cua):
    global _NEN, _CD, _CUA
    _NEN, _CD, _CUA = nen, cd, cua


def cham_mot(doc, nen=None, cd=None, cua=None):
    """Chạy + chấm MỘT sơ đồ → mấy con số JSON thuần.

    ⭐ Dùng chung cho CẢ HAI đường: chạy thẳng (1 nhân) và chạy trong tiến trình con.
    Chép ra hai bản là sớm muộn một bản quên tắt nhật ký, hoặc bắt `NaLenh` khác đi, và
    lúc ấy "8 nhân cho kết quả khác 1 nhân" — thứ không ai muốn đi tìm.

    ⚠ KHÔNG trả `KetQua`: nó ôm cả sổ lệnh lẫn mọi cột số, mà qua tiến trình thì mỗi
    lần trả là một lần đóng gói. Chỉ trả bảng điểm."""
    if nen is None:
        nen, cd, cua = _NEN, _CD, _CUA
    try:
        # Tắt nhật ký (§18.4b) — máy tìm không bao giờ đọc nó.
        kq = bo_chay.chay(doc, nen, cd, ghi_nhat_ky=False)
    except bo_chay.NaLenh:
        return {"loai": "na_lenh"}
    except bo_chay.QuaNang:
        return {"loai": "qua_nang"}
    except bo_chay.LoiChay as e:
        return {"loai": "no", "chu": f"{e}"[:120]}
    return {"loai": "cham", "diem": cham_diem.cham(kq, cua),
            "co_lenh": bool(kq.so.lenh)}


def so_nhan_hop_ly(xin=0):
    """Mấy nhân thì dùng. `0` = tự chọn.

    ⚠ Chừa lại 2 nhân, cố ý. Máy tìm chạy hàng giờ ở luồng nền của chính app đang mở;
    ăn hết sạch nhân thì cửa sổ giật và người dùng không kéo nổi một cái panel. Một
    lượt chạy nhanh hơn 8% không đáng đổi lấy tám tiếng app đơ."""
    co = os.cpu_count() or 1
    if xin and xin > 0:
        return max(1, min(int(xin), co))
    return max(1, co - 2)


def mo_be(so_nhan, nen, cd, cua):
    """Mở bể tiến trình. Trả `None` nếu không mở được — GỌI PHẢI LÙI VỀ CHẠY MỘT NHÂN.

    ⚠ Không nổ, và đó là chủ ý: `spawn` hỏng vì môi trường lạ (bản đóng gói thiếu
    `freeze_support`, chính sách máy chặn tiến trình con) là chuyện có thật, mà khi đó
    thứ người dùng cần là một lượt chạy CHẬM chứ không phải một câu lỗi."""
    if so_nhan <= 1:
        return None
    try:
        # `spawn` tường minh: mặc định của Windows vốn đã thế, nhưng viết ra thì cái
        # ràng buộc "module chính phải nạp lại được" hiện thành chữ.
        ctx = mp.get_context("spawn")
        return ctx.Pool(so_nhan, initializer=_mo_tien_trinh, initargs=(nen, cd, cua))
    except Exception:                             # noqa: BLE001 — xem docstring
        return None
