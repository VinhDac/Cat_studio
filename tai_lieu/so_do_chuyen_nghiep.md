# Sơ đồ xử lý của một trader chuyên nghiệp

> Soạn 2026-08-14. Vẽ theo **cách người ta thật sự xử lý**, không tự bó theo bộ khối app
> đang có — chỗ nào app chưa làm được thì đánh dấu `⊘` chứ không né.
> Nguồn tình huống: `trader_chuyen_nghiep.md`. Mục đích: dựng sơ đồ mẫu cho **§15 core.md**.

## Ký hiệu

```
◆    ngã rẽ PHÂN LOẠI — các nhánh loại trừ nhau, luôn đúng MỘT cái mở
         → không có gì để chọn, RL không được hỏi
★    ngã rẽ CHỌN NƯỚC ĐI — nhiều nước CÙNG hợp lý     ← CHỖ CÓ NHIỀU LỰA CHỌN
★★★  ngã rẽ quan trọng nhất của cả nghề
⟳    làm lại mỗi nến là ĐÚNG (trail là thế)
①    chỉ được làm MỘT LẦN cho mỗi lệnh — làm hai lần là hỏng, cần cờ nhớ
⊘    app chưa có (toán hạng hoặc hành động)
```

Nhãn số theo luật §3.1 (*SỐ = đi được bao xa · CHỮ = đi nhánh nào*). Nếu máy đánh số ra
khác thì lấy máy làm chuẩn — ở đây nhãn chỉ để đọc cho dễ.

---

## SƠ ĐỒ 1 — ENTRY · con trỏ ĐI SĂN

Một lượt mỗi nến. Chỉ nó được **TẠO** lệnh.

```
1   MỖI NẾN M5 — bắt đầu lượt săn
│
2 ◆ HÔM NAY CÒN ĐƯỢC ĐÁNH KHÔNG?                        ⊘ phần lớn toán hạng chưa có
│     lỗ trong ngày < hạn mức ⊘ · số vị thế < trần · đang trong phiên ⊘
│     · spread bình thường ⊘ · không sát giờ tin ⊘ · chưa có vị thế tương quan ⊘
│     └── trượt → HẾT LƯỢT (nến sau xét lại)
│
3 ◆ CÓ TIỀN ĐỀ KHÔNG?
│     vùng nén đã xác nhận · vùng này chưa từng sinh lệnh
│     └── trượt → HẾT LƯỢT
│
4 ◆ HƯỚNG NÀO?
│
├── 4A  XU HƯỚNG LÊN
│   │
│   │   ★★ BA VỞ ĐÃ TẬP — nhiều vở cùng mở được         ← LỰA CHỌN
│   │
│   ├── 4A.1A  ATR đang bung, giá chạy khỏi vùng nhanh?
│   │             → BUY MARKET · SL dưới mép vùng − đệm ATR · rủi ro 1R
│   │             (chắc chắn có mặt, trả bằng giá xấu + spread)
│   │
│   ├── 4A.1B  Vùng này hay bị test lại?
│   │             → BUY LIMIT tại mép vùng · SL dưới đáy gần nhất ⊘ · rủi ro 1R
│   │             (giá đẹp nhất, đổi lại CÓ THỂ KHÔNG BAO GIỜ KHỚP)
│   │
│   └── 4A.1C  ── nhánh mặc định, xếp cuối ──
│           │      → chờ xác nhận bằng lệnh treo
│           │
│           ├── 4A.1C.1A  Setup loại A? (thuận cả xu hướng H1)     ◆ phân loại
│           │                → BUY STOP ngoài mép + đệm ATR · rủi ro 1.5R
│           └── 4A.1C.1B  ── mặc định ──
│                            → BUY STOP ngoài mép + đệm ATR · rủi ro 1R
│
└── 4B  XU HƯỚNG XUỐNG
        ★★ (gương của 4A — SELL MARKET · SELL LIMIT · SELL STOP)
```

**Ba điều đọc ra từ hình:**

1. **SL quyết định trước, size suy ra từ SL.** Mỗi vở ghi *"SL ở đâu · rủi ro 1R"* — không
   phải *"lot 0.1"*. Nghiệp dư chọn size trước rồi nhét SL vào cho vừa.
2. **`4A.1C` là nhánh mặc định** (không cổng, xếp cuối) — nên **π₀ của Entry chính là D_02
   hôm nay**: luôn dùng lệnh treo chờ xác nhận. Hai vở kia là thứ RL được phép đề nghị.
3. **Hạng setup là ◆, không phải ★.** Setup *là* loại A hay không — đó là sự thật đọc được,
   không phải lựa chọn. Nó chỉ đổi size.

---

## SƠ ĐỒ 2 — MANAGE · một lượt cho MỖI lệnh đang sống

Chạy trước Entry trong mỗi nến. Chỉ nó được **SỬA**.
Tám nhánh, xếp theo đúng thứ tự ưu tiên của người chuyên nghiệp:
**PHÒNG THỦ → MỐC → THỜI GIAN.**

```
1   MỖI NẾN M5 — với TỪNG lệnh đang sống
│
│ ══════════ TẦNG 1 · PHÒNG THỦ — xét trước mọi thứ ══════════
│
├── 1A  CHỜ · lý do đặt lệnh ĐÃ MẤT trước khi khớp
│   │     (vùng nén tan · mức bị quét mà mình không có mặt)
│   │   ★ ba nước                                          ← LỰA CHỌN
│   ├── 1A.1A  huỷ ngay                                    ①
│   ├── 1A.1B  dời lệnh theo mức mới                       ⊘ chưa sửa được GIÁ VÀO
│   └── 1A.1C  giữ nốt nến này rồi xét lại                 ⊘ cần "đã treo mấy nến"
│
├── 1B  ĐÃ KHỚP · lý do vào lệnh ĐÃ HỎNG, dù SL chưa chạm
│   │   ★ ba nước                                          ← LỰA CHỌN
│   ├── 1B.1A  cắt hết ngay — giữ lại phần R còn sống
│   ├── 1B.1B  cắt một nửa, để nửa chạy                    ⊘ ĐÓNG MỘT PHẦN
│   └── 1B.1C  chờ SL, không đụng — không để nhiễu cắt oan
│
├── 1C  RỦI RO NGOÀI THỊ TRƯỜNG ẬP TỚI                     ⊘ cả cụm toán hạng
│   │     (sắp có tin · sắp đóng phiên · lỗ ngày sắp thủng)
│   │   ★ bốn nước                                         ← LỰA CHỌN
│   ├── 1C.1A  đóng hẳn
│   ├── 1C.1B  đóng một phần                               ⊘
│   ├── 1C.1C  siết SL sát lại                             ⟳
│   └── 1C.1D  giữ nguyên, chịu trận
│
│ ══════════ TẦNG 2 · MỐC — chỉ xét khi tầng 1 im ══════════
│
├── 1D  ĐỦ 1R · chưa xử lý mốc                             ⊘ cần cờ "đã xử lý mốc"
│   │
│   │   ★★★ BỐN NƯỚC — NGÃ RẼ LỚN NHẤT CỦA CẢ NGHỀ         ← LỰA CHỌN QUAN TRỌNG NHẤT
│   │
│   ├── 1D.1A  SL VỀ HOÀ VỐN                               ①
│   │             rẻ nhất về tâm lý · đắt nhất về kỳ vọng trong xu hướng
│   │             (bị quét ở nhịp hồi bình thường rồi giá đi tiếp)
│   ├── 1D.1B  CHỐT MỘT PHẦN rồi trail phần còn lại        ① ⊘
│   │             giảm phương sai · hạ R:R trung bình · cắt cụt đúng mấy cú to
│   ├── 1D.1C  NHỒI THÊM                                   ① ⊘ đụng luật "Manage chỉ SỬA"
│   │             tăng kỳ vọng khi trúng sóng lớn · đổi hồ sơ rủi ro cả rổ
│   └── 1D.1D  ĐỂ NGUYÊN, chạy tới TP                      ①
│                 giữ đúng kỳ vọng đã thiết kế · trả giá bằng những lần 2R về 0
│
├── 1E  ĐỦ 2R+ · đang chạy tốt
│   │   ★★ GIỮ BẰNG CÁCH NÀO                               ← LỰA CHỌN
│   ├── 1E.1A  TP cố định, không đụng gì
│   ├── 1E.1B  TRAIL theo ATR — dời SL = giá − k×ATR       ⟳
│   ├── 1E.1C  TRAIL theo CẤU TRÚC — dưới đáy gần nhất     ⟳ ⊘ cần toán hạng đáy/đỉnh
│   └── 1E.1D  CHỐT THANG từng mốc R                       ⊘
│
│ ══════════ TẦNG 3 · THỜI GIAN — xét cuối ══════════
│
├── 1F  CHỜ · treo quá lâu                                 ⊘ cần "thời gian trong lệnh"
│   │   ★ ├── 1F.1A  huỷ      └── 1F.1B  giữ tiếp
│
├── 1G  ĐÃ KHỚP · ĐỨNG IM quá lâu (vào đã lâu mà chưa tới 1R)   ⊘
│   │     "lệnh tốt chạy nhanh; lệnh dở thì không" — thời gian LÀ rủi ro
│   │   ★ ├── 1G.1A  thoát luôn   ├── 1G.1B  siết SL   └── 1G.1C  giữ
│
└── 1H  ── nhánh mặc định ── không làm gì, nến sau xét lại
```

---

## Chỗ RL thật sự được hỏi

Nhiều nhánh **không bao giờ mở cùng lúc** — `1A` (lệnh chờ) và `1D` (đã khớp đủ 1R) loại
trừ nhau theo trạng thái. Nên dù `[1]` có tám nhánh, RL chỉ có việc ở đúng những **cặp
chồng nhau được**:

| Cặp cùng mở được | Người chuyên nghiệp phân vân thật ở đây |
|---|---|
| `1B` × `1D` | lệnh vừa đủ 1R thì tiền đề hỏng — **ăn mốc hay chạy?** |
| `1B` × `1E` | đang lãi 3R thì lý do vào biến mất — chốt hay tiếp tục trail? |
| `1C` × `1D` `1E` | tin sắp ra lúc đang lãi — bảo vệ hay để chạy? |
| `1A` × `1F` | lệnh chờ vừa mất tiền đề vừa treo lâu — huỷ theo lý do nào |
| `1G` × `1B` | đứng im **và** tiền đề yếu đi — thoát theo thời gian hay theo lý do |

Cộng với **hai ngã rẽ trong từng nhánh**: chọn vở vào lệnh (`4A`), và bốn nước ở mốc 1R
(`1D`). Tổng lại vẫn đúng ba nhóm đã kết luận ở `core.md §15.9` — **không nở ra thêm**.

⚠ **Thứ tự tám nhánh `1A → 1H` chính là ưu tiên nghề nghiệp** (phòng thủ trước mốc, mốc
trước thời gian). Trong app, thứ tự đó lấy từ **vị trí trên canvas** (§3.2) — tức người vẽ
đặt nó bằng tay, và nó **chính là π₀**. RL học đúng một việc: khi nào thì đảo thứ tự đó.

---

## App phải có thêm gì để vẽ được hình này

Xếp theo mức chặn:

| # | Thiếu | Chặn nhánh nào |
|---|---|---|
| 1 | **Đóng một phần** (khối lượng cho *kết thúc lệnh*) | `1B.1B` `1C.1B` `1D.1B` `1E.1D` |
| 2 | **Cờ "đã xử lý mốc" của từng lệnh** | `1D` — không có nó thì mốc 1R nổ lại **mỗi nến**, và `1D.1B` chốt lệnh thành số 0 |
| 3 | **Toán hạng thời gian trong lệnh** | cả tầng 3 (`1F` `1G`) |
| 4 | **Toán hạng danh mục** (lỗ ngày theo equity · số lệnh thua liên tiếp · phiên · giờ tin) | `2` bên Entry, `1C` bên Manage |
| 5 | **Sửa GIÁ VÀO của lệnh chờ** | `1A.1B` |
| 6 | **Toán hạng đáy/đỉnh gần nhất** | `1E.1C` |
| 7 | **Nhồi thêm** | `1D.1C` — đụng luật khoá, cần quyết định riêng |

⚠ **Số 2 là cái bẫy im lặng nhất.** `SL về hoà vốn` lặp lại vô hại (⟳ — dời tới chỗ nó đã
nằm). `Chốt một phần` lặp lại thì **ăn mòn vị thế tới hết**. Hai hành động trông ngang
nhau trên sơ đồ nhưng một cái idempotent, một cái không — app cần phân biệt được `①` với
`⟳`, nếu không thì đây là loại lỗi chỉ lộ ra sau vài chục nến.
