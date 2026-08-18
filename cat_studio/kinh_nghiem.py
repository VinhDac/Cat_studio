"""KINH NGHIỆM — thứ còn lại sau khi hàng nghìn sơ đồ đã chạy xong.

    core.md §18.5a

⭐ **Đây là chỗ phá cái bế tắc lớn nhất của §18.5.** Một sơ đồ là ~40 nước đi và nhận
đúng MỘT con số ở cuối; không cách nào biết nước nào hay. Nên hôm nay lượt thứ 5.000 mù
y hệt lượt thứ 1 — máy tìm không tích luỹ gì cả, nó chỉ giữ một bảng xếp hạng.

Cách gỡ: đừng hỏi *"sơ đồ này mấy điểm"*, hỏi **"những sơ đồ CÓ nước đi này thì trung
bình hơn hay kém phần còn lại"**. Cùng một đống dữ liệu đã chạy, nhưng câu hỏi thứ hai
cho một con số cho **mỗi nước đi**, và con số ấy **chuyển được** sang sơ đồ chưa từng
dựng — khác hẳn *"sơ đồ #37 được 0,9 điểm"*, thứ chỉ đúng cho đúng nó.

⭐ **Đo theo THẺ trước, theo NƯỚC ĐI sau.** Kho có 1.863 nước đi nhưng chỉ vài chục thẻ
(`sl:1.5` · `tf:M5` · `huong:mua` …). 10.000 sơ đồ cho mỗi nước đi ~200 mẫu — thưa và ồn;
cho mỗi thẻ hàng nghìn mẫu. Và thẻ đúng là bộ từ vựng người dùng đang bật/tắt ở panel
Kho đồ, nên cái máy học được nói ra được bằng đúng thứ tiếng người dùng đang dùng.

⚠ **ĐÂY LÀ TƯƠNG QUAN, KHÔNG PHẢI NHÂN QUẢ — và chỗ này dễ tự lừa nhất.** Các nước đi đi
kèm nhau: một nước vô hại luôn xuất hiện cạnh một nước tốt sẽ ăn ké điểm. Con số ở đây
chỉ mách chỗ nên đào, không kết luận. Muốn nhân quả thì phải chạy CÓ và KHÔNG CÓ nó trên
cùng phần còn lại — đắt gấp đôi, để sau.

⚠ **Ít mẫu thì đừng tin.** Một thẻ xuất hiện 3 lần mà trung bình cao là chuyện thường của
xác suất. `bang()` cắt theo `toi_thieu` và LUÔN in ra số mẫu cạnh con số — giấu nó đi là
mời người đọc tin vào nhiễu.
"""
from collections import defaultdict

from . import nguoi_bay as nb

#: Dưới ngần này lần xuất hiện thì không báo cáo. 30 là mốc thô nhưng có lý: dưới đó
#: sai số của trung bình còn lớn hơn mọi khác biệt ta đang đi tìm.
TOI_THIEU = 30


class KinhNghiem:
    """Gom điểm theo THẺ và theo NƯỚC ĐI, qua nhiều sơ đồ.

    Rẻ: mỗi sơ đồ chỉ duyệt ~40 nước đi và mấy chục thẻ của chúng — không đáng gì so với
    một lượt backtest hàng giây."""

    __slots__ = ("so_do", "tong_diem", "the_lan", "the_diem", "the_dat",
                 "nuoc_lan", "nuoc_diem", "so_dat")

    def __init__(self):
        self.so_do = 0
        self.tong_diem = 0.0
        self.so_dat = 0
        # ⚠ Đếm theo SƠ ĐỒ, không theo lần xuất hiện. Một sơ đồ dùng `tf:M5` ở năm chỗ
        # vẫn là MỘT quan sát về `tf:M5`; đếm năm lần là tự nhân bản dữ liệu và mọi
        # khoảng tin cậy sau đó đều dối.
        self.the_lan = defaultdict(int)
        self.the_diem = defaultdict(float)
        self.the_dat = defaultdict(int)
        self.nuoc_lan = defaultdict(int)
        self.nuoc_diem = defaultdict(float)

    def ghi(self, chuoi, diem, dat):
        """Một sơ đồ vừa chấm xong."""
        self.so_do += 1
        self.tong_diem += diem
        self.so_dat += bool(dat)
        the_co = set()
        nuoc_co = set()
        for i in chuoi:
            n = nb.KHO_NUOC_DI[i]
            nuoc_co.add(i)
            the_co.update(nb.the(n))
        for t in the_co:
            self.the_lan[t] += 1
            self.the_diem[t] += diem
            self.the_dat[t] += bool(dat)
        for i in nuoc_co:
            self.nuoc_lan[i] += 1
            self.nuoc_diem[i] += diem

    @property
    def diem_chung(self):
        """Trung bình điểm của MỌI sơ đồ — cái mốc để so lợi thế."""
        return self.tong_diem / self.so_do if self.so_do else 0.0

    def loi_the(self, toi_thieu=TOI_THIEU):
        """`[(thẻ, số sơ đồ, trung bình, lợi thế, tỉ lệ đạt cửa)]`, tốt nhất trước.

        **lợi thế = trung bình điểm của sơ đồ CÓ thẻ này − trung bình chung.**

        Dương nghĩa là những sơ đồ dùng nó nhìn chung khá hơn phần còn lại. Xem cảnh báo
        tương quan ở đầu file trước khi kết luận bất cứ điều gì."""
        goc = self.diem_chung
        ra = []
        for t, n in self.the_lan.items():
            if n < toi_thieu:
                continue
            tb = self.the_diem[t] / n
            ra.append((t, n, round(tb, 4), round(tb - goc, 4),
                       round(self.the_dat[t] / n, 3)))
        return sorted(ra, key=lambda x: -x[3])

    def loi_the_nuoc(self, toi_thieu=TOI_THIEU):
        """Như `loi_the` nhưng theo TỪNG NƯỚC ĐI — thưa hơn nhiều, đọc sau."""
        goc = self.diem_chung
        ra = []
        for i, n in self.nuoc_lan.items():
            if n < toi_thieu:
                continue
            tb = self.nuoc_diem[i] / n
            ra.append((nb.KHO_NUOC_DI[i], n, round(tb, 4), round(tb - goc, 4)))
        return sorted(ra, key=lambda x: -x[3])

    def tom_tat(self, so_luong=12, toi_thieu=TOI_THIEU):
        """Dạng JSON thuần cho giao diện: mấy thẻ tốt nhất và tệ nhất."""
        ds = self.loi_the(toi_thieu)
        gon = [{"the": t, "so_do": n, "trung_binh": tb, "loi_the": lt, "ty_le_dat": td}
               for t, n, tb, lt, td in ds]
        k = so_luong // 2
        return {"so_do": self.so_do, "diem_chung": round(self.diem_chung, 4),
                "so_the": len(ds), "toi_thieu": toi_thieu,
                "tot": gon[:k], "te": gon[-k:][::-1] if len(gon) > k else []}
