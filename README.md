<h1 align="center">
  <img src="logo/logo.png" width="88"><br>
  Cat Studio
</h1>

<p align="center">
  Vẽ sơ đồ khối cho một chiến lược giao dịch, mỗi khối mang <b>một số thứ tự do chính
  bộ máy tính ra</b>, bấm ▶ Chạy để mở <b>Strategy Tester</b>.
</p>

---

## Một chiến lược = hai sơ đồ

```
   ┌── Tab ENTRY ────────────────┐     ┌── Tab MANAGE ───────────────────┐
   │  con trỏ ĐI SĂN             │     │  chạy MỘT LƯỢT CHO MỖI LỆNH     │
   │  một lượt mỗi nến           │     │  đang sống, cũng mỗi nến        │
   │  chỉ nó được TẠO lệnh       │     │  chỉ nó được SỬA lệnh           │
   └─────────────────────────────┘     └─────────────────────────────────┘
```

Mỗi nến: cập nhật dữ liệu → **Manage** cho từng lệnh → **Entry**. Manage trước, đúng
`OnTick` của D_02 — chạy ngược lại thì lệnh vừa sinh bị quản lý ngay trong nến đẻ ra nó.

**Mỗi sơ đồ tự nó đã là một vòng lặp**: nó chạy lại từ khối Bắt đầu ở mỗi nến. Nên
*"chờ tới khi"* không phải vẽ — không cổng nào khớp thì hết lượt, nến sau chạy lại.
Không cần khối "vòng lặp", không cần mũi tên quay ngược.

**Ranh giới khoá được:**

| | Entry | Manage |
|---|---|---|
| Kiểm tra ĐK | ✔ | ✔ |
| Vào lệnh | ✔ | ✘ |
| Sửa lệnh | ✘ | ✔ |
| Toán hạng nhóm *"Lệnh này"* | ✘ báo lỗi | ✔ |

> **Entry chỉ TẠO. Manage chỉ SỬA.** App soát tĩnh được, chỉ thẳng vào khối sai —
> loại lỗi MQL5 không bao giờ bắt.

Pill `Entry | Manage` là chip nổi ở góc trên-trái canvas, có **chấm đỏ khi tab kia
đang lỗi**.

## Luật đánh số

> **SỐ = đi được bao xa · CHỮ = đi nhánh nào**

Sơ đồ mẫu — chiến lược Compress (D_02):

```
ENTRY                                        MANAGE
[1] Mỗi nến M5 — tìm tín hiệu                [1] Mỗi nến M5 — với TỪNG lệnh
[2] Vùng nén đã xác nhận?                          ├─[1A] Chưa khớp mà nén đã tan?
      atr < 0,75×ATR nền · nến nén ≥ 10            │        → [1A.1] Huỷ lệnh chờ
      rộng÷ATR ≤ 4 · KHÔNG vùng đã sinh lệnh       └─[1B] Đã khớp, đủ 1R,
[3] Còn chỗ cho lệnh mới?                          │        SL chưa hoà vốn?
      số lệnh chờ = 0 · số vị thế < 3              │        → [1B.1] Dời SL về giá vào
      ├─[3A] Xu hướng LÊN?  → [3A.1] Buy Stop
      └─[3B] Xu hướng XUỐNG? → [3B.1] Sell Stop
```

## Ghim số ⟲

Chuột phải vào khối → **Ghim số** (hoặc `Ctrl+G`).

Khối đã ghim là **điểm quay lại hợp lệ**: mọi đường nối ngược về nó vẫn giữ nguyên số
cũ, không còn bị báo là vòng lặp ngoài ý muốn. Cạnh quay lại được vẽ **nét đứt vàng**
kèm nhãn `⟲` để nhìn sơ đồ là thấy ngay chỗ nào lặp về đâu.

Cạnh quay lại cũng chính là **nhánh mặc định**: nó luôn được thử cuối cùng và không cần
cổng điều kiện — nghĩa của nó vốn đã là *"không nhánh nào khớp thì quay về trên"*.

## Bộ khối

**Hai loại khối:** `Bắt đầu` (điểm neo, đúng một cái mỗi sơ đồ, không xoá được) và `Khối`.

**Ba hành động — đọc · tạo · sửa:**

| Hành động | Việc |
|---|---|
| **Kiểm tra điều kiện** | Đọc thị trường + tài khoản rồi quyết đi nhánh nào. Đây cũng là **cổng rẽ nhánh**. |
| **Vào lệnh** | Mở vị thế mới: Mua/Bán · Market/Stop · **rủi ro % vốn** · mốc neo · đệm · SL & TP ban đầu |
| **Sửa lệnh** | Tác động lên lệnh đã có: dời SL · dời TP · SL về hoà vốn · **kết thúc lệnh này** (gộp đóng hẳn + huỷ chờ — với một lệnh, "đóng" và "huỷ" là cùng một ý định) |

**22 toán hạng** (giá · chỉ báo · sổ lệnh · **lệnh này** · zone) × **8 phép so**, viết bằng
**ký hiệu** `< ≤ > ≥ = ≠` chứ không phải chữ (hai phép còn lại là `là ĐÚNG` / `là SAI`,
dành riêng cho toán hạng đúng/sai) — một cổng mang 4–5 điều kiện thì mắt phải liếc thấy
quan hệ, không phải đọc chữ. **Mọi khoảng cách là bội của ATR hoặc của R — không có pip
hay đô nào**, nên cùng một bộ số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.

> **BA chữ ATR là ba thứ khác nhau, tách ra là có chủ ý.**
> **ATR hiện tại** đo *đệm vào lệnh* — tấm khiên mỏng ngoài mép vùng, đủ lọc một nhịp
> phá giả.
> **ATR trung bình cả vùng** đo *rủi ro* (1R) — nên mỗi lệnh rủi ro một R tương đương bất
> kể vùng rộng hẹp.
> **ATR nền** (100 nến, chu kỳ **cố định**) là *cái thước*: `atr < 0,75 × ATR nền` nghĩa là
> "yên hơn chính thị trường này dạo gần đây". Thước cũ chia cho GIÁ (`bps`) đã bỏ — đo
> trên XAUUSD 2021–2026, cùng một cổng khớp 74 % số nến năm 2023 và 7,8 % năm 2026, tức
> chiến lược tự tắt dần theo giá vàng.

> **Khối lượng KHÔNG phải một ô nhập.** Khối Vào lệnh khai **rủi ro % vốn**; lot do bộ chạy
> suy ra từ đó và khoảng cách SL. Lot là con số tuyệt đối — 0,01 lot trên tài khoản
> $10.000 khác hẳn trên $100.000, nên mọi kết quả về tiền đổi nghĩa khi đổi tài khoản.

## Luật rẽ nhánh

Một khối nhiều đường ra thì các nhánh được **thử lần lượt từ trên xuống**:

1. Mỗi nhánh phải mở đầu bằng một **cổng** = khối *Kiểm tra điều kiện*.
2. Nhiều nhất **một** nhánh được để trống làm **nhánh mặc định**, và nó phải xếp **cuối**.
3. Cạnh quay lại (trỏ vào khối đã ghim) được miễn cả hai luật trên.

Không nhánh nào khớp thì **hết lượt** — nến sau chạy lại từ đầu. Đó là cách "chờ" được
diễn tả, không phải lỗi.

Cổng phải là *Kiểm tra điều kiện*: nhánh trượt phải **lùi lại được**, mà một khối chỉ
*đọc* dữ liệu thì lùi bao nhiêu lần cũng vô hại — còn *Vào lệnh* / *Sửa lệnh* đã tác
động ra thị trường rồi, không rút lại được.

## Chạy từ mã nguồn

Cần **Python 3.10+** và **Node.js 18+** trên Windows.

```bash
tools\setup.bat          # dựng .venv + npm install + build giao diện
tools\tao_shortcut.bat   # tạo shortcut "Cat Studio" ra Desktop (icon con mèo)
tools\chay.bat           # mở app từ dòng lệnh
tools\chay_test.bat      # chạy test
```

Shortcut chạy bằng `pythonw.exe` nên **không kèm cửa sổ console đen**. Đổi lại nó
không có stderr để nhìn, nên `app_web.py` báo mọi lỗi khởi động (thiếu .NET, thiếu
WebView2, chưa build giao diện) bằng **hộp thoại Windows** chứ không in ra màn hình.

Sửa giao diện xong phải `tools\build_ui.bat` mới thấy đổi — `app_web.py` chỉ nạp
`webui\dist`, không nạp mã nguồn.

## Cấu trúc

```
app_web.py         ĐIỂM KHỞI ĐỘNG — thứ duy nhất còn ở gốc (pywebview + WebView2)
cat_studio/        toàn bộ lõi app
  core.py            đồ thị, đánh số, soát lỗi
  kho/               danh mục mọi thứ app tính được, chia theo LOẠI
    nen_tang.py        giá · sổ lệnh · lệnh này      LUÔN có
    chi_bao.py         ATR · MA                      ai gọi thì có
    zone.py            vùng giá + máy nuôi vùng      có khi SƠ ĐỒ định nghĩa nó
  mau/compress.json  sơ đồ mẫu — một chiến lược thì là JSON, như mọi chiến lược khác
  so_lenh.py         bảng lệnh + vùng nén, id của CHÍNH TA
  luu_tru.py         MỘT chỗ duy nhất biết file nằm ở đâu
  api.py             bề mặt DUY NHẤT giao diện gọi tới  (JS → api.py → core.py)
  khung_cua_so.py    vá cửa sổ Win32 cho thanh tiêu đề tự vẽ (kéo/giãn/phóng to)
tai_lieu/          sổ ghi cốt lõi
  core.md            VÌ SAO mọi thứ như vậy. Đọc file này trước.
  D02_Compress_ban_giao.md   bàn giao chiến lược gốc
webui/             giao diện: React + TypeScript + React Flow
tests/             bộ test — không mở cửa sổ, không cần MT5
du_lieu/           dữ liệu của bạn (sinh ra lúc chạy, không nằm trong repo)
tools/             kịch bản: chạy · build giao diện · chạy test · ĐÓNG GÓI
dist/              sản phẩm đóng gói + bản .zip phát hành (không nằm trong repo)
```

Menu **File → Kho** liệt kê mọi thứ app tính được, chia theo nguồn: nền tảng · chỉ báo
chuẩn · zone. Danh sách do Python **tự gom** từ `kho/`, nên thêm một cơ chế mới là hộp
thoại có ngay — không có danh sách nào chép tay.

Menu **File → Tham số chiến lược** sửa bảng hằng số CÓ TÊN. Ngưỡng nén được hỏi ở cả
hai sơ đồ; gõ số thẳng vào hai nơi thì sửa một chỗ là hai vế lệch nhau âm thầm.

Ba tầng, mỗi tầng biết đúng việc của mình:

- `core.py` giữ toàn bộ logic và **không import webview** — test được mà không mở cửa sổ.
- `api.py` là chỗ duy nhất giao diện gọi tới. Giao diện **không bao giờ tự biết định
  dạng file**; nó chỉ gửi/nhận JSON.
- `webui/` chỉ lo hiển thị. Ngay cả dòng mô tả hành động cũng do Python sinh
  (`core.action_display`), để hai bên không thể nói khác nhau.

## Lưu ý

- Chỉ chạy trên **Windows** (dùng API riêng của Windows cho thanh tiêu đề tối).
- Cần **.NET Framework 4.7.2+** và **Microsoft Edge WebView2 Runtime** — app tự kiểm
  lúc mở và báo bằng tiếng Việt nếu thiếu.
- Cài `pywebview` trong **`.venv` riêng**: nếu Python global có gói `quantconnect-stubs`
  thì nó chiếm namespace `Microsoft` và pywebview chết ngay lúc khởi động.
- Dữ liệu của bạn nằm trong `du_lieu/` cạnh app, không nằm trong repo. Bản cũ
  (`settings.json` + `templates/`) được chép sang tự động lúc mở app lần đầu.
