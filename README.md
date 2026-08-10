<h1 align="center">
  <img src="logo/logo.png" width="88"><br>
  Cat Studio
</h1>

<p align="center">
  Vẽ sơ đồ khối cho một chiến lược giao dịch, mỗi khối mang <b>một số thứ tự do chính
  bộ máy tính ra</b>, bấm ▶ Chạy để mở <b>Strategy Tester</b>.
</p>

---

## Luật đánh số

> **SỐ = đi được bao xa · CHỮ = đi nhánh nào**

```
[1] Bắt đầu
[2] Nến này có nén không?          ⟲ đã ghim          ←────────┐
[3] Đủ K nến & vùng vừa khổ?  ─┬─ [3A]  Xu hướng LÊN  → [3A.1] Buy Stop
                               ├─ [3B]  Xu hướng XUỐNG → [3B.1] Sell Stop
                               └─ ⟲ không hướng nào hợp ───────┤
[4] Chờ khớp / chờ vùng tan   ─┬─ [4A]  Lệnh đã khớp?  → [4A.1] Hoà vốn ─┤
                               └─ [4B]  Vùng đã tan?   → [4B.1] Huỷ chờ ─┘
```

- Các nhóm ngăn bởi dấu `.`, mỗi nhóm = **SỐ** rồi tới các **CHỮ**. Chữ không bao giờ
  mở đầu một nhóm → `4A.2B` tách được thành `4A` | `2B`, không nhập nhằng.
- Mọi nhánh chụm lại một chỗ thì số **quay về mức trên** (`4`, không phải `3A.3`).
- Thứ tự ưu tiên nhánh lấy từ **vị trí trên canvas** — kéo khối lên trên là nhãn `A`/`B`
  đổi ngay lúc thả chuột, nên ưu tiên không bao giờ là thứ ngầm.
- Nhãn do **Python tính**, giao diện chỉ hiển thị. Số ở góc khối không thể nói dối.

## Ghim số ⟲

Chuột phải vào khối → **Ghim số** (hoặc `Ctrl+G`).

Khối đã ghim là **điểm quay lại hợp lệ**: mọi đường nối ngược về nó vẫn giữ nguyên số
cũ, không còn bị báo là vòng lặp ngoài ý muốn. Cạnh quay lại được vẽ **nét đứt vàng**
kèm nhãn `⟲` để nhìn sơ đồ là thấy ngay chỗ nào lặp về đâu.

Cạnh quay lại cũng chính là **nhánh mặc định**: nó luôn được thử cuối cùng và không cần
cổng điều kiện — nghĩa của nó vốn đã là *"không nhánh nào khớp thì quay về trên"*.

## Bộ khối

**Bốn loại khối:** `Bắt đầu` (điểm neo đánh số, đúng một cái, không xoá được) ·
`Kiểm tra ĐK`/`Vào lệnh`/`Sửa lệnh` (HĐ lẻ) · `Vòng theo dõi` (lặp mỗi nến) ·
`Nhóm` (chạy một lượt).

**Ba hành động — đọc · tạo · sửa:**

| Hành động | Việc |
|---|---|
| **Kiểm tra điều kiện** | Đọc thị trường + tài khoản rồi quyết đi nhánh nào. Đây cũng là **cổng rẽ nhánh**. |
| **Vào lệnh** | Mở vị thế mới: Mua/Bán · Market/Stop/Limit · lot · SL & TP ban đầu |
| **Sửa lệnh** | Tác động lên lệnh đã có: dời SL · dời TP · hoà vốn · trailing · đóng một phần · đóng hẳn · huỷ lệnh chờ |

30 toán hạng (giá, ATR, MA, Donchian, vùng nén, trạng thái lệnh, tài khoản, thời gian)
× 9 phép so. **Mọi khoảng cách là bội của ATR hoặc của R — không có pip hay đô nào**,
nên cùng một bộ số mang cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.

## Luật rẽ nhánh

Một khối nhiều đường ra thì các nhánh được **thử lần lượt từ trên xuống**:

1. Mỗi nhánh phải mở đầu bằng một **cổng** = khối HĐ lẻ *Kiểm tra điều kiện*.
2. Nhiều nhất **một** nhánh được để trống làm **nhánh mặc định**, và nó phải xếp **cuối**.
3. Cạnh quay lại (trỏ vào khối đã ghim) được miễn cả hai luật trên.

Chỉ HĐ lẻ được làm cổng: nhánh trượt phải **lùi lại được**, mà một khối chỉ *đọc* dữ
liệu thì lùi bao nhiêu lần cũng vô hại — còn một Nhóm có thể đã đặt lệnh rồi mới kiểm
tra, và lệnh đó không rút lại được.

## Chạy từ mã nguồn

Cần **Python 3.10+** và **Node.js 18+** trên Windows.

```bash
tools\setup.bat      # dựng .venv + npm install + build giao diện
tools\chay.bat       # mở app
tools\chay_test.bat  # chạy test
```

Sửa giao diện xong phải `tools\build_ui.bat` mới thấy đổi — `app_web.py` chỉ nạp
`webui\dist`, không nạp mã nguồn.

## Cấu trúc

```
core.md            sổ ghi cốt lõi — VÌ SAO mọi thứ như vậy. Đọc file này trước.
core.py            lõi — không phụ thuộc giao diện, chạy headless được
api.py             bề mặt DUY NHẤT giao diện gọi tới  (JS → api.py → core.py)
app_web.py         khởi động cửa sổ (pywebview + WebView2)
khung_cua_so.py    vá cửa sổ Win32 cho thanh tiêu đề tự vẽ (kéo/giãn/phóng to)
webui/             giao diện: React + TypeScript + React Flow
tests/             bộ test — không mở cửa sổ, không cần MT5
```

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
- Dữ liệu của bạn (`settings.json`, thư mục `templates/`) sinh ra cạnh app, không nằm
  trong repo.
