"""VÂN TAY HÀNH VI — chốt trạng thái app để chứng minh một đợt dọn không làm hỏng gì.

    tools\\van_tay.bat            chạy, so với vân tay đã chốt
    tools\\van_tay.bat --chot     chốt lại vân tay mới (SAU khi cố ý đổi hành vi)

VÌ SAO CÓ FILE NÀY
------------------
Bộ kiểm trả lời "có hỏng không". File này trả lời một câu khác, và là câu đúng cho một
đợt DỌN DẸP: **"có đổi gì không?"** — dọn mà đổi một con số nào thì không còn là dọn.

Nó băm bốn thứ, đúng bốn thứ mà mọi bên khác nhìn vào:

  1. KHO       mọi toán hạng, chỉ báo, module — thứ bộ sinh và dropdown nhìn thấy
  2. BẢNG HẰNG đơn vị, phép so, chế độ sửa, mốc neo — luật chơi viết thành dữ liệu
  3. BOOTSTRAP khoá giao diện nhận được
  4. BACKTEST  số cuối cùng trên dữ liệu thật — thứ duy nhất không cãi được

Ba cái đầu bắt được lỗi ở tầng khai báo; cái cuối bắt được mọi thứ còn lại.

⚠ Vân tay LỆCH không có nghĩa là sai. Nó nghĩa là **có thứ đã đổi hành vi** — và bạn phải
biết mình vừa đổi cái gì. Cố ý thì `--chot` lại; không cố ý thì vừa tìm ra một con bọ.
"""
import argparse
import hashlib
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace",
                              line_buffering=True)
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)

from cat_studio import api, bo_chay as bc, cham_diem, core, kho   # noqa: E402
from cat_studio import nguoi_bay as nb   # noqa: E402
from cat_studio import nguon_nen as nn   # noqa: E402

FILE = os.path.join(GOC, "tai_lieu", "van_tay.json")

#: Khoảng đo. Hai năm, một lãi một lỗ — một năm thì dễ trùng ngẫu nhiên.
NAM = (2023, 2025)
SYMBOL = "XAUUSD"


def _thu_thap():
    ra = {"kho": {
        "toan_hang": [(t["key"], t["nhom"], t.get("loai"), t.get("don_vi"),
                       tuple(t.get("tabs") or ()), bool(t.get("dung_sai")))
                      for t in kho.TOAN_HANG],
        "chi_bao": [c["key"] for c in kho.CHI_BAO],
        "can_zone": list(kho.CAN_ZONE),
        "module": [m.MA_SO for m in kho.MODULE],
    }, "bang": {
        "DON_VI": core.DON_VI,
        "DON_VI_CHO": {k: list(v) for k, v in core.DON_VI_CHO.items()},
        "DON_VI_DEM": core.DON_VI_DEM, "PHEP_SO": core.PHEP_SO,
        "SUA_CHE_DO": core.SUA_CHE_DO, "SUA_GHI_LEN": core.SUA_GHI_LEN,
        "MOC_ENTRY": core.MOC_ENTRY, "MOC_CAN_ZONE": list(core.MOC_CAN_ZONE),
        "HUONG": core.HUONG, "LOAI_LENH": core.LOAI_LENH,
        "ACTION_TYPES": core.ACTION_TYPES, "CHU_KY_ATR_NEN": core.CHU_KY_ATR_NEN,
        "KHOA_MOT_LENH": list(core._KHOA_MOT_LENH),
        # Danh sách LUẬT ĐỒ THỊ: thêm/bớt một luật là đổi hành vi soát tĩnh, phải lộ ra.
        "LUAT_DO_THI": [f.__name__ for f in core.LUAT_DO_THI],
    }, "bootstrap_khoa": sorted(api.Api().bootstrap()["value"].keys())}

    doc = core.normalize_process(api._so_do_mau())
    ra["mau_soat"] = [f"{p['severity']}:{p['message'][:70]}"
                      for p in core.validate_process(doc)]
    ra["mau_the"] = [core.action_display(s)
                     for tab in core.TABS for s in doc[tab]["steps"]]

    # NGƯỜI BÀY — kho nước đi và trần độ phức tạp là thứ MỌI máy tìm dựng trên đó.
    # Thêm một toán hạng vào kho hay đổi một nấc thang là kho nước đi đổi theo, và
    # một mạng đã học phải học lại (§18.7.2) — đúng loại thay đổi phải lộ ra.
    #
    # Kèm chuỗi nước đi của SƠ ĐỒ MẪU: nó là vân tay của CẢ HAI CHIỀU cùng lúc — đọc
    # ngược đổi hay dựng xuôi đổi đều làm nó lệch.
    ra["nguoi_bay"] = {
        "so_nuoc": len(nb.KHO_NUOC_DI),
        "theo_loai": {k: sum(1 for n in nb.KHO_NUOC_DI if n[0] == k)
                      for k in sorted({n[0] for n in nb.KHO_NUOC_DI})},
        "thang": {k: list(v) for k, v in nb.THANG.items()},
        "tran": dict(nb.TRAN),
        "mau_chuoi": [list(map(str, nb.KHO_NUOC_DI[i]))
                      for i in nb.doc_nguoc(doc, lam_tron=True)[0]],
    }

    ra["backtest"] = {}
    luat = api._luat_san(SYMBOL, {})
    for n in NAM:
        tu, den = f"{n}-01-01", f"{n + 1}-01-01"
        nen = nn.doc(SYMBOL, tu, den)
        if not len(nen):
            ra["backtest"][str(n)] = "KHÔNG CÓ NẾN"
            continue
        # ⚠ VIẾT CỨNG cả bốn số của symbol, CỐ Ý — không đọc từ meta kho nến. Vân tay
        # phải đổi khi MÃ NGUỒN đổi, không phải khi ai đó tải lại nến (`spread_tb` được
        # đo lại mỗi lần tải). Bốn số này là số thật của XAUUSD, chép từ meta một lần.
        #
        # ⚠ `contract_size` từng bị QUÊN ở đây và bài này vẫn chạy — nó lặng lẽ ăn số
        # mặc định của `CaiDat`, mà số ấy tình cờ đúng bằng 100. Ngày đổi mặc định
        # thành số giả (§16.3) là vân tay lệch toác: vốn 10.125 → 1.920. Chính cái lưới
        # này suýt bị thủng bởi đúng loại lỗi nó sinh ra để bắt.
        cd = bc.CaiDat(symbol=SYMBOL, tu=tu, den=den,
                       point=0.001, digits=3, contract_size=100.0,
                       spread_diem=97, commission=3.5, deposit=10_000.0, **luat)
        kq = bc.chay(doc, nen, cd)
        tk = kq.thong_ke
        # `drawdown_luc` là một MỐC THỜI GIAN, không phải kết quả — bỏ ra để vân tay
        # không đổi chỉ vì kho nến được tải thêm vài nến ở đuôi.
        # Khoá là CHỮ: file JSON đọc lại chỉ có khoá chữ, để int vào đây thì phần so
        # sánh bên dưới tra trượt và in ra "cũ null" thay vì chỗ đổi thật.
        ra["backtest"][str(n)] = {k: tk[k] for k in sorted(tk) if k != "drawdown_luc"}
        # ĐIỂM — thứ mọi máy tìm tối ưu vào. Đổi công thức chấm mà không ai biết là đổi
        # cái đích, và mọi kết quả cũ hết so được với kết quả mới.
        ra["backtest"][str(n)]["_diem"] = cham_diem.cham(kq)
    return ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chot", action="store_true",
                    help="ghi đè vân tay đã chốt (dùng SAU khi cố ý đổi hành vi)")
    tuy = ap.parse_args()

    ra = _thu_thap()
    chuoi = json.dumps(ra, ensure_ascii=False, sort_keys=True, default=str)
    bam = hashlib.sha256(chuoi.encode()).hexdigest()[:16]

    print(f"VÂN TAY: {bam}")
    print(f"  {len(ra['kho']['toan_hang'])} toán hạng · {len(ra['bang']['DON_VI'])} đơn vị"
          f" · {len(ra['bang']['SUA_CHE_DO'])} chế độ sửa"
          f" · {len(ra['bang']['MOC_ENTRY'])} mốc neo"
          f" · {len(ra['bang']['LUAT_DO_THI'])} luật đồ thị")
    for n, tk in ra["backtest"].items():
        if isinstance(tk, dict):
            print(f"  {n}: {tk['so_lenh']} lệnh · {tk['tong_R']} R · "
                  f"DD {tk['drawdown_pt']}% · vốn {tk['von_cuoi']}")

    cu = json.load(open(FILE, encoding="utf-8")) if os.path.exists(FILE) else None
    if tuy.chot or cu is None:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        json.dump({"bam": bam, "chi_tiet": ra}, open(FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)
        print(f"\n→ đã chốt vân tay vào {os.path.relpath(FILE, GOC)}")
        return 0
    if cu["bam"] == bam:
        print("\n✔ TRÙNG KHÍT vân tay đã chốt — không hành vi nào đổi")
        return 0

    print(f"\n✘ LỆCH vân tay đã chốt ({cu['bam']}). Mục đã đổi:")
    for k in ra:
        moi = json.dumps(ra[k], sort_keys=True, default=str)
        goc = json.dumps(cu["chi_tiet"].get(k), sort_keys=True, default=str)
        if moi != goc:
            print(f"    · {k}")
            if isinstance(ra[k], dict):
                for k2 in ra[k]:
                    a = json.dumps(ra[k][k2], sort_keys=True, default=str)
                    b = json.dumps((cu["chi_tiet"].get(k) or {}).get(k2),
                                   sort_keys=True, default=str)
                    if a != b:
                        print(f"        {k2}:\n          cũ  {b[:150]}\n          mới {a[:150]}")
    print("\nCố ý đổi thì chạy lại với `--chot`. Không cố ý thì bạn vừa tìm ra một con bọ.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
