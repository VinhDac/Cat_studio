# D_02 Compress — chốt sơ đồ mẫu

Ghi lại kết quả một buổi mổ xẻ EA gốc. Mục đích: **sửa lại `_so_do_mau()` trong
`api.py`** cho khớp với logic thật của D_02, và chốt bộ từ vựng khối.

Đọc file này là đủ để làm tiếp, không cần hỏi lại buổi trước.

---

## 0. Việc cần làm

Sửa `_so_do_mau()` ở `api.py` (khoảng dòng 487–597). Hiện tại nó có **12 khối**,
dùng khối *Vòng theo dõi* — cả hai đều đã bị bác bỏ.

Mục tiêu: **8 khối, 3 loại động từ, không Vòng theo dõi, không Nhóm.**

---

## 1. Nguồn gốc — đọc trước khi sửa

Mã MQL5 thật:

```
C:\Users\Davin\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\D_02_Compress\
    Projects\Experts\Compress.mq5        điều phối, KHÔNG có phép tính nào
    Include\Controller\FilterEngine.mqh  máy trạng thái nén + lọc MA
    Include\Controller\TradeManager.mqh  đặt / sửa / huỷ lệnh
    Include\Inputs\Parameters.mqh        hợp đồng chuẩn hoá tham số
    Include\Model\Enums.mqh              5 trạng thái nén
    Include\Model\DataTypes.mqh          struct dữ liệu giữa các khối
    README.md                            spec đầy đủ
```

Bản thuyết trình dễ đọc: `Desktop\Making-Resume_2026\Docs\Presention_html\D_02_Compress.html`

---

## 2. D_02 đi logic thế nào

### 2.1 Bốn khối, mỗi khối một việc

| Khối | Chịu trách nhiệm | Cấm đụng |
|---|---|---|
| `Parameters.mqh` | khai báo input → `SSettings` | không tính toán |
| `Enums` + `DataTypes` | định nghĩa trạng thái + struct | không logic, không handle |
| `FilterEngine` | máy trạng thái nén + lọc xu hướng | không biết lệnh là gì |
| `TradeManager` | đặt / sửa / huỷ lệnh, dời SL | không có handle chỉ báo, không logic tín hiệu |

`Compress.mq5` **không chứa một phép tính nào**. Header ghi thẳng:
`NOTE: NO calculation logic here — orchestration only.`

### 2.2 `OnTick` là một vòng lặp tuần tự

Đây là điểm mấu chốt và là chỗ dễ hiểu sai nhất. **MQL5 không có gì chạy nền.**
`OnTick` chạy lại từ trên xuống mỗi tick:

```
1. g_filter.Update()                 làm mới trạng thái nén + xu hướng
2. g_trade.CheckPendingActivation()  lệnh chờ đã khớp chưa
3. g_trade.ManageBreakEven()         dời SL về hoà nếu đủ điều kiện
4. if IsNewBar(signal_tf):           chỉ ở đây mới ra quyết định
5. if WasActivated(): ConsumeSignal()
```

`ManageBreakEven()` **không phải luật thường trực** — nó là dòng thứ 3 của một hàm
tuần tự được gọi lặp lại. Nó tự chặn khỏi chạy hai lần bằng
`if(sl >= entry && sl > 0.0) continue;`.

→ **Hệ quả: mọi thứ của Compress tái lập được bằng chuỗi tuần tự + mũi tên quay
vòng. Không cần khối theo dõi song song.**

### 2.3 Máy trạng thái nén (`FilterEngine::UpdateCompression`)

```
IDLE ──atr_bps < N──> COUNTING ──đủ K nến & rộng ≤ max──> CONFIRMED
                                                              │
                                                    EA đặt lệnh chờ
                                                              ↓
                                                          PENDING
                                                              │
                                                        lệnh khớp
                                                              ↓
                                                         CONSUMED ──┐
                                                         (tự lặp    │
                                                          khi atr<N)│
   ▲                                                               │
   └──────────── atr_bps ≥ N, từ BẤT KỲ trạng thái nào ────────────┘
```

Ba chi tiết quan trọng:

- **`CONSUMED` không thừa.** Không có nó, sau khi lệnh khớp vùng nén vẫn còn, ATR
  vẫn dưới ngưỡng, và ngay nến sau máy lại vào lệnh trên **cùng một cú nén**. Nó là
  câu "một cú nén, một lệnh" viết thành code.
- **Đường thoát là MỘT luật, không phải bốn.** `ATR ≥ ngưỡng` áp dụng cho mọi trạng
  thái — trong code là một nhánh `else` gọi `ResetState()`.
- **Vùng nén đóng băng khi đã đặt lệnh.** `if(cur != COMP_PENDING)` mới cập nhật
  High/Low. Lệnh đặt ở mép nào thì mép đó không nhúc nhích.

### 2.4 Hợp đồng chuẩn hoá tham số

`Parameters.mqh` ghi thành luật ở header: mỗi tham số liên quan tới giá phải là **một
trong năm loại** — bps của giá, bội số ATR, bội số R, phần trăm vốn, hoặc số nến.
**Không đơn vị tuyệt đối. Không `_Point` trong logic nghiệp vụ.**

Số mặc định trong code:

| Tham số | Giá trị | Đơn vị |
|---|---|---|
| `ATR_Period` | 14 | nến |
| `ATR_Threshold_Bps` | 7.0 | bps của giá |
| `Comp_Bars` (K) | 10 | nến |
| `Range_Max_ATR` | 4.0 | × ATR hiện tại |
| `Entry_Buffer_ATR` | 0.10 | × ATR hiện tại |
| `SL_ATR_Avg` | 1.5 | × ATR **trung bình cả vùng nén** |
| `RR_Ratio` | 2.0 | × R |
| `BE_RR_Trigger` | 1.0 | × R |
| `Signal_TF` / `Trend_TF` | M5 / M15 | |
| `MA_Period` / `MA_Method` | 50 / SMA | |

**Hai chữ ATR khác nhau và đó là chủ ý:** mép vào lệnh đo bằng ATR *hiện tại*, còn
rủi ro đo bằng ATR *trung bình suốt cú nén*. Nhờ vậy 1R nhất quán giữa các tín hiệu
dù vùng nén rộng hẹp khác nhau. Đừng gộp làm một.

---

## 3. Chốt bộ từ vựng khối

**Ba loại là đủ:** `Kiểm tra ĐK` · `Vào lệnh` · `Sửa lệnh`

**Bỏ `Vòng theo dõi`** — vì `OnTick` vốn đã là vòng lặp tuần tự (mục 2.2). Chờ đợi
biểu diễn bằng một khối Kiểm tra ĐK tự lặp, không cần khối riêng.

**Bỏ `Nhóm`** — cấu trúc của D_02 đến từ tách trách nhiệm, không đến từ lồng hộp.
Gom nhóm chỉ đẻ thêm câu hỏi "nhóm có phải một đơn vị chạy không".

**Template = cả một process chạy được**, không phải cụm khối rời. Bỏ các template vụn.

### Trạng thái tan vào đồ thị

| Trạng thái trong MQL5 | Trên sơ đồ là gì |
|---|---|
| `IDLE` / `COUNTING` | đứng ở bước 1, tự lặp |
| `CONFIRMED` | đúng lúc thoát bước 1 |
| `PENDING` | đứng ở bước 4, tự lặp |
| `CONSUMED` | đứng ở bước 7 (cổng khoá), tự lặp |

`FilterEngine` phải nuôi enum 5 giá trị vì MQL5 không có đồ thị — nó chỉ có một hàm
chạy lại từ đầu mỗi tick nên phải tự nhớ mình đang ở đâu. **Ta có đồ thị rồi thì
không cần nhớ: trạng thái chính là vị trí con trỏ.**

---

## 4. Sơ đồ mẫu cần dựng — bản đã chốt

Quy ước đọc: số = bước · chữ = nhánh rẽ · ngoặc = mũi tên quay về.

```
1 · Kiểm tra ĐK — nén
      atr_bps < 7  và  đủ 10 nến liên tiếp  và  rộng vùng ≤ 4 × ATR
      1A  chưa đủ nến, hoặc nén vỡ            (quay lại 1)

2 · Kiểm tra ĐK — xu hướng
      M15:  close > MA(50) → MUA  ·  close < MA(50) → BÁN
      2A  chưa rõ hướng                        (quay lại 2)
      2B  nén vỡ                               (quay lại 1)

3 · Vào lệnh
      entry = mép vùng ± 0.10 × ATR hiện tại
      SL    = entry ∓ 1.5 × ATR trung bình cả vùng nén
      TP    = entry ± 2R

4 · Kiểm tra ĐK — lệnh đã khớp chưa
      4A  chưa khớp, nén còn                   (quay lại 4)
      4B  nén vỡ → 4B.1

   4B.1 · Sửa lệnh — huỷ lệnh chờ              (quay lại 1)

5 · Kiểm tra ĐK — đạt 1R chưa
      5A  chưa đạt                             (quay lại 5)

6 · Sửa lệnh — dời SL về hoà

7 · Kiểm tra ĐK — cổng khoá
      atr_bps ≥ 7
      7A  chưa                                 (quay lại 7)
      hết →                                    (quay lại 1)
```

**8 khối. Kiểm tra ĐK** ở 1, 2, 4, 5, 7 — **Vào lệnh** ở 3 — **Sửa lệnh** ở 4B.1 và 6.

Không có khối TP/SL riêng: chúng gắn luôn vào lệnh ở bước 3, sàn tự khớp.
Không có khối "vị thế đóng": D_02 không bao giờ chủ động đóng.

### Vì sao đặt như vậy

- **Bước 7 chính là `CONSUMED`.** Trong code nó bật ngay lúc lệnh khớp, sớm hơn vị
  trí này. Nhưng dòng chảy chỉ có một con trỏ nên trong lúc chạy 5 và 6 không có gì
  vũ trang được — đặt cổng ở 7 hay ở 4 đều ra cùng hành vi, đặt ở 7 dễ đọc hơn.
- **Sau 7 quay về 1, KHÔNG chờ vị thế đóng.** Đúng ý D_02: cho phép săn cú nén mới
  trong lúc lệnh cũ vẫn chạy.
- **Bước 6 không cần canh mãi.** Dời SL về hoà chỉ xảy ra một lần mỗi vị thế, code
  gốc tự chặn bằng `if(sl >= entry) continue`.

---

## 5. Sơ đồ mẫu hiện tại sai ở đâu

`api.py::_so_do_mau()` đang có 12 khối:

```
bd(start) · nen · du_nen · xu_huong_len · xu_huong_xuong · mua · ban
· cho(LOOP) · da_khop · vung_tan · hoa_von · huy
```

Ba chỗ lệch:

1. **Có khối `cho` = `core.make_loop_step("Chờ khớp / chờ vùng tan")`** — đây là
   *Vòng theo dõi*, đã quyết bỏ. Thay bằng khối Kiểm tra ĐK tự lặp (bước 4).
2. **Thiếu hẳn cổng khoá `CONSUMED` (bước 7).** Hiện `hoa_von` nối thẳng về `nen`,
   nên sơ đồ có thể vũ trang lại trên **cùng một cú nén** — sai bản chất "một cú nén,
   một lệnh".
3. **Thiếu bước "đạt 1R chưa" (bước 5).** `hoa_von` đang đứng ngay sau `da_khop`,
   không có chỗ chờ giá đi đủ 1R.

Tách `nen` / `du_nen` làm hai khối thì **không sai** — gộp thành một khối 3 điều
kiện (bước 1) gọn hơn, nhưng giữ hai khối cũng chấp nhận được. Tuỳ chọn, không phải lỗi.

---

## 6. Hai chỗ còn mở — quyết trước khi code

**6.1 Khối `Vào lệnh` có nhận hướng từ bước trước không?**

Bản đánh số ở mục 4 gộp mua/bán làm một bước 3, ngầm giả định khối Vào lệnh đọc được
hướng do bước 2 chọn. Nhưng mã hiện tại ghi cứng `"huong": "mua"` / `"huong": "ban"`.

- Nếu **không** đọc được → phải tách thành 2A/2B, mỗi nhánh một khối Vào lệnh
  (giống template hiện tại). Vẫn chỉ 3 loại động từ, chỉ là 9 khối thay vì 8.
- Nếu **có** → giữ đúng 8 khối như mục 4.

Kiểm `core.py` xem `VAO_LENH` có nhận hướng động không rồi hãy dựng.

**6.2 Khối Kiểm tra ĐK phải xuất ra GIÁ TRỊ, không chỉ đúng/sai.**

`entry = highest_high + 0.10 × atr_current` và `sl = 1.5 × atr_avg`. Đỉnh vùng nén và
ATR trung bình suốt cú nén đều do khối kiểm tra tính ra trong lúc đếm nến — trong
D_02 chúng đi qua struct `SCompressionData`. Khối Vào lệnh phải đọc được chúng.

Nếu khối kiểm tra chỉ trả pass/fail thì khối vào lệnh không biết đặt lệnh ở đâu.
Cần soát xem `core.py` đã có đường truyền giá trị này chưa.

---

## 7. Một chuyện ghi lại, chưa cần quyết

`Compress.mq5` dòng 22 ghi:
*"Pending can coexist with running position. Each order is based on its own
compression signal."*

D_02 cho phép đang giữ vị thế cũ mà vẫn vũ trang lệnh mới từ cú nén mới. Dòng tuần tự
**một con trỏ** thì không làm được — con trỏ đang đứng ở bước 5 thì không đồng thời
đếm nén mới.

Đây là câu hỏi **"một process chạy mấy con trỏ"**, không phải câu hỏi **"cần mấy loại
khối"**. Không đụng gì tới kết luận 3 khối. Để dành.

---

## 8. Nguyên tắc làm việc

- **Không port nguyên xi MQL5.** Mục tiêu là học cách D_02 dựng một chiến lược sạch,
  rồi áp tư duy đó — không phải parity 100%.
- **Không tự bịa thêm ngoài D_02.**
- **Đi chậm, sâu, sạch, không phức tạp hoá.**
- Sửa xong nhớ chạy `tests/test_so_do_mau.py` và `tests/test_danh_so.py`.
