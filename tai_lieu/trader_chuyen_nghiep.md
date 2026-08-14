# Trader chuyên nghiệp làm gì — bảng TÌNH HUỐNG · HÀNH ĐỘNG

> Soạn ngày 2026-08-14 để phục vụ **§15 của `core.md`** (RL học chọn nhánh).
>
> Đây **không phải một chiến lược**. Đây là **từ vựng**: có những tình huống nào, và ở mỗi
> tình huống người chuyên nghiệp có những nước đi nào được coi là hợp lý. Mỗi dòng có **≥2
> nước đi hợp lý** chính là một **ngã rẽ HOẶC** — chỗ RL có việc làm.

---

## 0. Phát hiện lớn nhất — và nó xác nhận §15

Đọc hết tài liệu về quản lý lệnh, thứ lặp lại nhiều nhất **không phải** một lời khuyên. Nó
là một lời **từ chối trả lời**: gần như mọi bài đều kết bằng *"phải tự kiểm xem nó có hợp
với chiến lược / thị trường của bạn không"*.

Đó không phải sự lười biếng của người viết. Đó là vì **đáp án thật sự phụ thuộc tình
huống**, và văn xuôi không có chỗ để nói điều đó. Bốn cặp dưới đây được nói thẳng là ngược
dấu nhau tuỳ bối cảnh:

| Hành động | Thắng ở đâu | Thua ở đâu |
|---|---|---|
| **SL về hoà vốn** | thị trường lình xình, hay quay đầu | xu hướng — bị quét ở nhịp hồi bình thường rồi giá đi tiếp |
| **Chốt một phần** | có sóng thứ hai thật để chạy | biên độ hẹp: một TP cố định ở mép trên ăn hơn; và nó **cắt cụt đúng những cú to** — chỗ edge sống |
| **Trail** | ATR khi biến động đổi liên tục · bước cố định khi symbol ổn định · theo cấu trúc khi có sóng nhìn thấy được | dùng sai kiểu thì hoặc bị quét sớm, hoặc trả lại quá nhiều |
| **Kiểu vào lệnh** | Stop = chắc có mặt khi nó chạy | Stop = giá xấu nhất; Limit = giá đẹp nhưng **có thể không bao giờ khớp** |

> **Đây đúng là định nghĩa của một ngã rẽ HOẶC nhiều nhánh cùng mở.** Không phải một tham
> số cần dò — mỗi nước đi đều đúng ở đâu đó. Thứ phải học là **khi nào cái nào**.

Một con số nữa đáng nhớ, tầng danh mục: **~80% tài khoản prop bị đánh rớt vì thủng hạn mức
lỗ NGÀY** — không phải vì vào lệnh dở. Tầng trên cùng quan trọng hơn tầng tín hiệu.

---

## 1. ENTRY — con trỏ đi săn

| # | Tình huống | Các nước đi hợp lý | Phân biệt bằng gì | Học được? |
|---|---|---|---|---|
| **E1** | Chưa có setup | chờ (hết lượt, nến sau chạy lại) | — | ✘ |
| **E2** | Bối cảnh có cho phép giao dịch không | ① giao dịch bình thường ② nửa size ③ nghỉ hẳn | lỗ trong ngày · số vị thế đang mở · phiên · spread · tin sắp ra | ✔ |
| **E3** | Setup đã xác nhận — **VÀO BẰNG CÁCH NÀO** | ① Market ngay ② **Stop** ngoài mức ③ **Limit** về mức ④ chia đôi Stop+Limit | phá thật rồi chạy luôn → Stop. Hay quay lại test → Limit. Sợ hụt hàng → Market | ✔✔ |
| **E4** | Lấy bao nhiêu | ① rủi ro cố định 1R ② giảm sau chuỗi thua ③ tăng khi setup loại A | | ✔ |
| **E5** | Có được đi ngược khung lớn không | ① chỉ thuận xu hướng ② ngược khi ở biên ③ không lọc hướng | | ✔ |

⚠ **E3 là ngã rẽ đắt nhất bên Entry.** Ba nhánh cùng hợp lệ ở đúng một cây nến, và cái nào
tốt hơn phụ thuộc *tốc độ thị trường hôm đó* — thứ đo được (ATR đang bung hay đang co),
nhưng không viết thành một luật cứng nào đúng mãi.

---

## 2. MANAGE — chia theo TRẠNG THÁI của lệnh

Đây là phần dày nhất, và là chỗ dân chuyên nghiệp khác nhau nhiều nhất.
Trạng thái quyết định *bộ* tình huống nào áp dụng — nên nó là **cổng phân loại**, không
phải chỗ để học (một lệnh chỉ ở đúng một trạng thái).

### 2.1 Lệnh CHỜ, chưa khớp

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M1** | Tiền đề còn nguyên | giữ nguyên | ✘ |
| **M2** | ⭐ **Tiền đề đã mất TRƯỚC khi khớp** (vùng nén tan, mức bị quét mà mình không có mặt) | ① huỷ ngay ② giữ tới hết nến ③ dời lệnh theo mức mới | ✔ |
| **M3** | Giá chạy mất, không quay lại | ① huỷ ② **đuổi** — dời giá vào theo | ✔ |
| **M4** | Đã treo quá lâu | ① huỷ theo thời gian ② giữ tiếp | ✔ |

> **M2 là hành động chuyên nghiệp nhất trong cả tài liệu này**: *lý do tôi vào đã biến mất
> trước khi tôi có mặt → tôi rút*. Không optimizer nào đẻ ra được nước này, vì nó không
> phải một ngưỡng — nó là một **quan hệ nhân quả**. D_02 đã có, đúng ở `[1A]`.

### 2.2 Đã khớp, ĐANG LỖ, chưa chạm SL

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M5** | Chưa có gì đổi | không làm gì — tôn trọng SL | ✘ |
| **M6** | ⭐ Tiền đề hỏng **trước khi** SL bị chạm | ① cắt sớm, giữ lại phần R ② chờ SL, không để nhiễu cắt oan | ✔✔ |
| **M7** | Giá đi ngược mạnh | ① cắt ② giữ · ~~giãn SL~~ | ✘ |

⚠ **Giãn SL là nước đi duy nhất trong tài liệu này được coi là SAI ở mọi bối cảnh.** Ghi
lại chính vì thế: app nên **không cho vẽ** nó, chứ không phải để RL tự học rằng nó sai.
Luật cứng của người, đúng nếp §15.4.

### 2.3 Đã khớp, LÃI NHỎ (< 1R)

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M8** | Đi được một đoạn ngắn | ① không làm gì ② dời SL bớt một phần rủi ro ③ chốt một phần sớm | ✔ |

### 2.4 ⭐⭐ Đủ 1R — MỐC QUYẾT ĐỊNH LỚN NHẤT CỦA CẢ NGHỀ

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M9** | Lãi đã đủ 1R | ① SL về **hoà vốn** ② chốt **50%** rồi trail phần còn lại ③ **để nguyên** chạy tới TP ④ **nhồi thêm** | ✔✔✔ |

Bốn nhánh, cả bốn đều là nước đi của người chuyên nghiệp, và tài liệu **nói thẳng là không
có đáp án chung**:

- ① rẻ nhất về tâm lý, **đắt nhất về kỳ vọng** trong xu hướng — bị quét ở nhịp hồi thường.
- ② giảm phương sai, nhưng **hạ R:R trung bình** (1R:2R chốt nửa ở 1R → còn 1.5R) và cắt
  cụt đúng những cú to nuôi cả hệ thống.
- ③ giữ nguyên kỳ vọng thiết kế, trả giá bằng những lần lãi 2R quay về 0.
- ④ tăng kỳ vọng khi trúng sóng lớn, nhưng đổi luôn hồ sơ rủi ro của cả rổ.

> Nếu §15 chỉ chứng minh được ở **một** chỗ thì nên chọn chỗ này. Nó là ngã rẽ 4 nhánh,
> tần suất cao (mọi lệnh thắng đều đi qua), và mốc so π₀ có sẵn — D_02 chọn cứng nhánh ①.

### 2.5 Lãi lớn (2R+) — chọn CÁCH GIỮ

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M10** | Đang chạy tốt | ① TP cố định ② trail theo **ATR** ③ trail theo **cấu trúc** (đáy/đỉnh gần nhất) ④ trail theo **MA** ⑤ chốt thang từng phần | ✔✔ |
| **M11** | Trail chặt hay lỏng | 1.5×ATR chặt · 3×ATR chuẩn trend · 4×ATR ăn to nhưng sụt sâu | ✘ **tham số** |

⚠ **M11 KHÔNG phải ngã rẽ.** Nó là con số → theo §15.2 nó là hằng số có tên trong Bảng
tham số, người đặt, RL không chạm. Ranh giới M10 / M11 là ví dụ sạch nhất cho luật đó:
*chọn KIỂU trail* là hành động; *chọn HỆ SỐ trail* là tham số.

Ghi chú thứ tự đã được nói tới nhiều lần: **trail chỉ nên bật SAU khi lệnh đã qua giai
đoạn phòng thủ** (sau hoà vốn, hoặc sau khi chốt một phần, hoặc sau một mốc R lớn hơn mốc
hoà vốn). Tức M10 nằm **sau** M9 trên sơ đồ, không song song.

### 2.6 Đứng im

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M12** | Vào lâu rồi mà không đi đâu | ① thoát theo **thời gian** ② siết SL lại ③ giữ | ✔ |

> *"Lệnh tốt chạy nhanh; lệnh dở thì không."* Thời gian **là** rủi ro. Đây là hành động mà
> hệ thống bán lẻ gần như không bao giờ có, còn bàn prop và tổ chức thì luôn có.

### 2.7 Bối cảnh đổi khi đang cầm vị thế

| # | Tình huống | Các nước đi hợp lý | Học được? |
|---|---|---|---|
| **M13** | Biến động bung · tin sắp ra · sắp đóng phiên | ① đóng hẳn ② giảm một phần ③ giãn TP theo biến động ④ giữ nguyên | ✔ |

---

## 3. Tầng DANH MỤC — đứng trên từng lệnh

| # | Tình huống | Các nước đi hợp lý | Ghi chú |
|---|---|---|---|
| **P1** | Lỗ trong ngày chạm hạn mức | ① ngừng hẳn tới phiên sau ② nửa size | **~80% tài khoản prop chết ở đây** |
| **P2** | Số vị thế đang mở | trần cứng | D_02: `Max_Positions = 3` |
| **P3** | Đã có vị thế cùng chiều / tương quan | ① không thêm ② thêm nửa size | ba cặp cùng dính USD = một lệnh gấp ba |
| **P4** | Vừa thua liên tiếp | ① giảm size ② nghỉ ③ giữ nguyên | |

⚠ Lỗ **chưa đóng** cũng tính vào hạn mức ngày. Nếu app định có P1 thì toán hạng phải là
**equity**, không phải tổng lệnh đã đóng.

---

## 4. App CÓ GÌ · THIẾU GÌ để vẽ được bảng trên

Bộ khối hôm nay (§6.3): *Kiểm tra điều kiện* · *Vào lệnh* (Mua/Bán · Market/Stop/Limit ·
lot · SL/TP) · *Sửa lệnh* (dời SL · dời TP · SL hoà vốn · kết thúc lệnh).

| Thiếu | Cần cho | Nặng nhẹ |
|---|---|---|
| **Đóng MỘT PHẦN** | M8 ② · M9 ② · M10 ⑤ · M13 ② | ⭐⭐ **nặng nhất.** "Kết thúc lệnh" hôm nay là được ăn cả ngã về không. Không có nó thì nhánh phổ biến nhất của mốc 1R **vẽ không được** |
| **Nhồi thêm vào lệnh đang chạy** | M9 ④ | ⭐⭐ đụng luật khoá §6.0 *(Manage chỉ SỬA)* — xem §5 dưới |
| **Dời GIÁ VÀO của lệnh chờ** | M3 ② (đuổi) | ⭐ Sửa lệnh hôm nay chỉ dời SL/TP |
| **Toán hạng "thời gian trong lệnh"** | M4 · M12 | ⭐⭐ không có nó thì cả nhóm thoát-theo-thời-gian biến mất |
| **Toán hạng trạng thái chuỗi** (lỗ trong ngày · số lệnh thua liên tiếp) | P1 · P4 · E2 | ⭐⭐ đây là tầng giết nhiều tài khoản nhất |
| **Trail theo cấu trúc** (đáy/đỉnh gần nhất) | M10 ③ | ⭐ cần một toán hạng swing high/low trong `kho/` |

Ngược lại, hai thứ **không cần thêm gì cả**:

- **Trail** — Manage chạy mỗi nến cho mỗi lệnh, nên *"dời SL tới giá − 3×ATR"* lặp lại từng
  nến **chính là** trailing. Không cần khối riêng.
- **SL về hoà vốn** — đã có.

---

## 5. Hai thứ phải chốt trước khi vẽ

**(a) Nhồi thêm nằm ở đâu.** Nó *tạo* lệnh, mà Entry mới được tạo — nhưng lý do nhồi lại
là *"lệnh SỐ 3 đang lãi 2R"*, mà toán hạng **Lệnh này** thì Entry bị cấm dùng (§6.0). Hôm
nay Entry chỉ nói được bằng toán hạng **sổ lệnh** dạng tổng ("có ≥1 vị thế đang lãi"),
không trỏ được vào một lệnh cụ thể. Ba đường: nới luật · thêm hành động *nhân bản lệnh này*
bên Manage · hoặc bỏ M9 ④ khỏi phạm vi.

**(b) Đóng một phần đổi định nghĩa của R.** Một lệnh chốt 50% ở 1R rồi phần còn lại chạy
tới 3R thì **R của lệnh đó là bao nhiêu** — 2.0 (bình quân) hay hai bản ghi riêng? Câu này
không phải chi tiết kế toán: theo §15.7, **R chính là phần thưởng của RL**. Định nghĩa sai
là học sai.

---

## 6. Hình dạng sơ đồ đề xuất

Hai loại ngã rẽ, và chúng **tự phân biệt được**, không cần đánh dấu gì thêm:

```
NGÃ RẼ PHÂN LOẠI        các nhánh loại trừ nhau  →  luôn chỉ 1 nhánh mở  →  RL không có việc
NGÃ RẼ CHỌN NƯỚC ĐI     các nhánh cùng mở được   →  ≥2 nhánh mở          →  RL học ở đây
```

→ Trả lời luôn một câu treo ở **§15.8**: *không cần cờ "ngã rẽ học được"*. Cấu trúc tự lọc.

```
ENTRY                                          MANAGE  (một lượt cho MỖI lệnh)
[1] Mỗi nến — đi săn                           [1] Mỗi nến — với TỪNG lệnh
[2] Bối cảnh cho phép?          (P1·P2·E2)      ├─[1A] Chưa khớp?                    ◆phân loại
[3] Có setup xác nhận?                          │    ├─[1A.1] tiền đề tan? → huỷ      (M2)
[4] VÀO BẰNG CÁCH NÀO?    ★học★  (E3)           │    └─[1A.2] treo quá lâu? → huỷ     (M4)
     ├─[4A] Stop ngoài mức                      ├─[1B] Đã khớp, đang lỗ?             ◆phân loại
     ├─[4B] Limit về mức                        │    └─[1B.1] tiền đề hỏng? → cắt sớm (M6)
     └─[4C] Market                              ├─[1C] Đủ 1R?             ★học★      (M9)
                                                │    ├─ SL về hoà vốn
                                                │    ├─ chốt một phần
                                                │    ├─ nhồi thêm
                                                │    └─ để nguyên
                                                ├─[1D] Đủ 2R+?            ★học★      (M10)
                                                │    ├─ trail ATR
                                                │    ├─ trail cấu trúc
                                                │    └─ TP cố định
                                                └─[1E] Đứng im quá lâu? → thoát       (M12)
```

`[1A] [1B] [1C] [1D] [1E]` là **phân loại theo trạng thái** — loại trừ nhau, chạy như hôm
nay. Ba ngôi sao ★ là toàn bộ chỗ RL được nói. Ba chỗ, không nhiều hơn.

---

## 7. Nguồn

- [Trade Management: Trailing Stops, Partials, and Breakeven — The Trapped Trader](https://thetrappedtrader.com/learn/foundations/risk-management/9)
- [Entries Are Only Half the Trade: The Complete Trade Management Playbook](https://vizdumb.com/trade-management-playbook-partials-trailing-runners/)
- [Trade Management After Entry: Stop Loss, Partial Profits, and Exit Rules — ChartMini](https://chartmini.com/blog/trade-management-what-to-do-after-you-enter-2026)
- [The Mathematics of Stop-Losses and Break-Even Moves — JustMarkets](https://justmarkets.com/trading-articles/learning/the-mathematics-of-stop-losses-and-break-even-moves)
- [Move Your Stop Loss to Breakeven: Why, When and How — Trading Heroes](https://www.tradingheroes.com/move-stoploss-breakeven/)
- [Partial Profit Taking: The Math and Psychology of Scaling Out — Metriclan](https://www.metriclan.com/blog/partial-profit-taking)
- [Scaling In and Out: The Ultimate Guide to Position Management — FTO](https://forextester.com/blog/scale-out-and-scale-in-trading/)
- [Time stop. How to use the time factor in trading — ATAS](https://atas.net/trading-preparation/funds-management/time-stop-how-to-use-the-time-factor-in-trading/)
- [Five Exit Strategies in Trading — QuantifiedStrategies](http://www.quantifiedstrategies.com/trading-exit-strategies/)
- [Time Based Exits for Day Trading — AlphaEx Capital](https://www.alphaexcapital.com/prop-trading/prop-trading-strategies-and-systems/day-trading-strategies-for-prop-firms/time-based-exits-for-day-trading)
- [ATR Trailing Stop Guide: Chandelier Exit & Volatility — StratBase](https://stratbase.ai/en/blog/average-true-range-trailing-stop)
- [Volatility-Adjusted Stop Losses: ATR, Chandelier, and Keltner — Volatility Box](https://volatilitybox.com/research/volatility-adjusted-stop-losses/)
- [Breakout Trading: Entry Strategies and False Signal Filtering — INFINOX](https://www.infinox.com/global/en/breakout-trading-entry-strategies/)
- [Stop order vs Limit order — Brooks Trading Course](https://www.brookstradingcourse.com/support-forum/general-trading-discussion/how-to-know-when-to-enter-using-a-stop-vs-limit/)
- [Daily Loss Limit Explained for Prop Firm Traders — FuturesHive](https://www.futureshive.com/blog/daily-loss-limit-prop-firm-guide-2026)
- [How to Pass a Prop Firm Challenge: Risk Management Framework — TradeZella](https://www.tradezella.com/blog/pass-prop-firm-challenge)
