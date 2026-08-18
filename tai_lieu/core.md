# Cat_Studio — Sổ ghi cốt lõi

> App vẽ pipeline + mô phỏng hành vi chiến lược giao dịch.
> Fork từ **Auto_Clicker** (`C:\Users\Davin\Desktop\Auto_Clicker`), đổi miền từ *click game* sang *trading*, nối MT5 về sau.
>
> File này là **nguồn sự thật về Ý ĐỊNH**. Code là nguồn sự thật về hành vi.
> Sửa cơ chế → sửa file này cùng lúc, đừng để hai bên nói khác nhau.
>
> ⚠ **VÍ DỤ TRONG CÁC MỤC TRƯỚC §15 CÓ THỂ DÙNG TỪ VỰNG CŨ** — `atr < 7 [bps]`,
> `lot = 0,01`, `kho/engine_d02.py`, `gia_hien_tai`. Chúng được **giữ nguyên có chủ ý**:
> mỗi mục kể lại chuyện lúc nó được quyết, và xoá đi là mất phần *vì sao*. Bộ đồ nghề
> HIỆN TẠI nằm ở **§6.3** (bảng toán hạng · đơn vị · phép so) và **§15** (lý do đổi).
> Chỗ nào hai bên đá nhau thì **§15 thắng**.

Cập nhật: 2026-08-17 · Trạng thái: **P0–P7 + P9 xong** · 14/14 bài kiểm qua · đã đóng gói và chạy thật
Tester + bộ chạy đã đo trên nhiều năm dữ liệu thật (§12). **P8 · Live** nối sàn ở **chế độ QUAN SÁT** — §14.
🆕 **§15 · Dọn kho đồ cho việc TÌM CHIẾN LƯỢC TỰ ĐỘNG** — 6/7 đợt đã cài, hạng mục 10 hoãn có chủ ý.

---

## 0. Một câu

> Vẽ sơ đồ khối cho một chiến lược giao dịch, mỗi khối mang **một số thứ tự do chính bộ máy tính ra**,
> bấm ▶ Chạy thì mở **Strategy Tester** để xem chiến lược đó hành xử ra sao.

---

## 1. Nguồn tham chiếu

| Nguồn | Đường dẫn | Lấy gì |
|---|---|---|
| **Auto_Clicker** | `C:\Users\Davin\Desktop\Auto_Clicker` | Toàn bộ kiến trúc, giao diện, cơ chế đánh số, rẽ nhánh, undo, template, khung cửa sổ |
| **Compress EA** | `…\MQL5\Experts\D_02_Compress` | Chiến lược mẫu để tái lập bằng Python và làm **sơ đồ mẫu** |

---

## 2. Kiến trúc kế thừa từ Auto_Clicker — GIỮ NGUYÊN

Ba tầng, mỗi tầng biết đúng việc của mình. Đây là thứ làm app không tự mâu thuẫn — **không được phá.**

```
core.py          lõi — đồ thị, đánh số, soát lỗi. Không phụ thuộc giao diện.
kho/             DANH MỤC mọi thứ app tính được, chia theo LOẠI
  nen_tang.py      giá · sổ lệnh · lệnh này      LUÔN có
  chi_bao.py       ATR · MA                      ai gọi thì có
  zone.py          vùng giá + máy nuôi vùng      có khi SƠ ĐỒ định nghĩa nó
mau/compress.json  sơ đồ mẫu — một chiến lược, nên nó là JSON như mọi chiến lược khác
so_lenh.py       bảng `lệnh` + `vùng nén`, id của CHÍNH TA
luu_tru.py       MỘT chỗ duy nhất biết file nằm ở đâu
api.py           bề mặt DUY NHẤT giao diện gọi tới   (JS → api.py → core.py)
app_web.py       khởi động cửa sổ (pywebview + WebView2)
khung_cua_so.py  vá cửa sổ Win32 cho thanh tiêu đề tự vẽ (kéo / giãn / phóng to)
webui/           React + TypeScript + React Flow (@xyflow/react)
```

### Vì sao `kho/` tách khỏi `core.py`

`zone_dem` **chỉ có nghĩa khi sơ đồ có cổng zone**. Để nó chung một danh sách phẳng với
`close` là nói dối về việc thứ gì luôn có, thứ gì phải được định nghĩa ra mới có.

- Thêm một cơ chế = thêm **một file** vào `kho/`, không sờ `core.py`.
- Hộp thoại **Kho** (menu File) đọc thẳng `kho.danh_muc()` — không có danh sách nào
  chép tay, nên nó không thể nói khác thực tế.
- **Trùng khoá giữa hai module là lỗi CHẾT NGƯỜI** (hai module cùng khai `atr` với hai
  nghĩa) → `kho/__init__.py` nổ ngay lúc import, không để nó âm thầm.

⚠ **Khái niệm "ENGINE" đã TAN — §15.3.** `engine_d02.py` bị xoá. Cơ chế vùng vốn là ý
tưởng riêng của D_02, nhưng nó đã tổng quát hoá xong từ lâu (`moi_nen()` rỗng, điều kiện
đếm nằm ở cổng người dùng vẽ) — giữ một module mang tên một chiến lược cụ thể chỉ khiến
người đọc tưởng phải "chọn engine". Bảng số của D_02 đi theo sơ đồ mẫu, vào
`mau/compress.json`.

### Vì sao `so_lenh.py` dùng id của ta

D_02 **không có** id nối lệnh chờ với vị thế sinh ra từ nó, nên `CheckPendingActivation`
phải ĐOÁN bằng `HasOpenPosition()` — *"có vị thế nào bất kỳ không"*. Lệnh chờ bị huỷ từ
ngoài trong lúc còn vị thế cũ là nó **đọc nhầm thành đã khớp**.

- `L-0001`, `V-0003` — **đếm tăng, không uuid**: đọc log biết ngay thứ tự, và chạy lại
  cùng dữ liệu ra cùng id nên so được hai lần backtest.
- `ticket` của MT5 chỉ là **một cột phụ**, để trống khi backtest.
- Lệnh mang `vung_id` → *"vùng này đã sinh lệnh"* (thay `COMP_CONSUMED`) chỉ là một
  **phép tra bảng**, không phải cờ ẩn. Và tính cả lệnh đã đóng: một cú nén, một lệnh.
- `sl_o_hoa_von` suy ra từ **vị trí SL so với giá vào**, không phải cờ riêng — y như
  `if(sl >= entry) continue` của bản gốc, và không thể lệch với thực tế.

### Bố cục lưu trữ

```
<cạnh app>/du_lieu/
    cai_dat.json          cài đặt app
    chien_luoc/*.json     chiến lược đã lưu
    nen/                  cache nến tải về      (Strategy Tester dùng sau)
    nhat_ky/              nhật ký lệnh từng lần chạy  (sau)
```

`luu_tru.di_cu()` chuyển `settings.json` + `templates/strategy/` của bản cũ sang, chỉ
CHÉP những gì chưa có — không đè, không xoá bản cũ.

**Luật bất di bất dịch:**

1. **JS không bao giờ biết định dạng file.** Nó gửi/nhận JSON, mọi hiểu biết về schema nằm ở `core.py`.
2. **Nội dung chữ trên hộp do Python sinh** (`core.action_display` → `api.describe`). JS chỉ chọn icon theo `type`. Hai bên không thể nói khác nhau.
3. **Số ở góc khối do Python tính**, bằng **chính phép duyệt** mà bộ chạy dùng. JS không tự đếm.
4. **Không throw qua cầu nối.** Mọi hàm `Api` bọc `@_bat_loi` → luôn trả `{ok, value, error, trace}`.
5. **Mọi thuộc tính không-callable trên `Api` phải bắt đầu bằng `_`.** pywebview duyệt `dir(js_api)`; đọc trúng property của Window là treo UI thread vĩnh viễn ("Not Responding").

### Cầu nối JS ↔ Python

**Không có HTTP, không có route.** Là `window.pywebview.api.<tên>()`.
`webview.start(..., http_server=True)` chỉ để phục vụ file tĩnh (Vite build là ES module,
`file://` cho origin `"null"` → Chromium chặn → màn hình trắng).

**Hệ quả phải nhớ:** cổng là **ephemeral, đổi mỗi lần chạy** → origin đổi → `localStorage` **vô dụng**.
Mọi trạng thái UI cần nhớ phải đi qua Python (`save_ui`).

### Đẩy sự kiện lúc chạy

Không websocket, không SSE, không polling. Python gọi ngược:
`self._window.evaluate_js('window.__su_kien("run", <json>)')`, **gom lô ~150 ms/lần**.
Đẩy từng dòng là ngốn sạch UI thread.

### Vì sao thanh tiêu đề phải tự vẽ

Windows 10 **không cho** đổi màu thanh tiêu đề (`DWMWA_CAPTION_COLOR` là của Win11, Win10 trả `E_INVALIDARG`).
→ `frameless=True` rồi tự vẽ, `khung_cua_so.py` vá lại từng thứ đã mất: viền kéo giãn, phóng to đúng vùng
làm việc (không che taskbar), menu hệ thống.

> **Bài học đắt nhất, chép nguyên:** vá `WM_NCHITTEST` **một mình là vô ích**. WebView2 là cửa sổ con
> (`Chrome_RenderWidgetHostHWND`) phủ kín cửa sổ cha; Windows chỉ hỏi cửa sổ trên cùng dưới con trỏ,
> và nó luôn trả `HTCLIENT`. Cửa sổ cha không bao giờ được hỏi.
> → **Kéo cửa sổ phải do WEB khởi động**: JS gọi `keo_cua_so(ht)` → `PostMessageW(WM_KEO_RIENG)` →
> proc (đang ở UI thread — chỗ duy nhất `ReleaseCapture()` chạy được) làm `ReleaseCapture()` +
> `SendMessageW(WM_NCLBUTTONDOWN)`. **`Post` chứ không `Send`** vì vòng lặp kéo của Windows là modal,
> `Send` sẽ khoá luôn thread Python suốt cú kéo.

---

## 3. ⭐ CƠ CHẾ ĐÁNH SỐ — thứ quan trọng nhất

### 3.1 Luật

> **SỐ = đi được bao xa · CHỮ = đi nhánh nào**

```
1
2
3
4
├── 4A                 ← cổng nhánh A (khối ĐẦU nhánh mang đúng nhãn nhánh)
│   ├── 4A.1
│   ├── 4A.2
│   │   ├── 4A.2A
│   │   └── 4A.2B
│   └── 4A.3
└── 4B
    ├── 4B.1
    └── 4B.2
5                      ← ĐIỂM GỘP: mọi nhánh đều dẫn tới đây → số về lại mức trên
6
```

**Ngữ pháp:** các nhóm ngăn bởi dấu `.`, mỗi nhóm = **SỐ** rồi tới các **CHỮ** (có thể không có).
`4A.2B` tách thành `4A` | `2B`. Chữ **không bao giờ** mở đầu một nhóm, số luôn đứng ngay sau dấu chấm
→ máy tách được, không nhập nhằng.

### 3.2 Ai quyết cái gì

| Thứ | Do đâu quyết | Ghi chú |
|---|---|---|
| **Định danh khối** | `id = "s" + uuid4().hex[:8]` | Bền. Kéo khối / đổi tên không đổi id. **Không bao giờ dùng số thứ tự làm id.** |
| **Nhãn hiện ở góc** | `flow_order(steps, edges)` tính lại mỗi lần | **Không lưu vào file.** Là hàm thuần của (đồ thị + vị trí). |
| **Thứ tự ưu tiên nhánh** | `_khoa_nhanh(step)` → `(y, x, str(id))` | **Lấy từ VỊ TRÍ TRÊN CANVAS**, không phải thứ tự nối dây |
| **Khối bắt đầu** | `flow_entry` = khối đầu tiên trong danh sách **không có đường nối đi vào** | |
| **Điểm gộp** | `diem_gop(cur, ke)` = khối gần nhất mà **MỌI** nhánh đều dẫn tới | Giao các tập BFS, trừ chính nó, lấy gần nhất |

**Vì sao ưu tiên nhánh lấy từ vị trí:** thứ tự nối dây là thứ **vô hình** — kéo khối cách mấy cũng không đổi,
người dùng không có cách nào biết nhánh nào thử trước. Vị trí thì **nhìn thấy**, và nhãn `A`/`B` đổi
**ngay lúc thả chuột** → ưu tiên không bao giờ là thứ ngầm.

**Vì sao nhãn phải do Python tính:** trước khi có rẽ nhánh, lời hứa "số ở góc khối không nói dối" được giữ
bằng cách cho bộ chạy và bộ đánh số đi **chung một phép duyệt**. Có nhánh rồi thì huy hiệu vẽ **CẢ CÂY**
(tĩnh) còn bộ chạy chỉ đi **MỘT đường** (động) — không còn là cùng một phép duyệt nữa.
Chỗ duy nhất nó còn có thể nói dối là **thứ tự ưu tiên nhánh** → nên đó chính là thứ phải dùng chung:
cả hai bên đều chỉ lấy thứ tự từ `flow_map()`.

### 3.3 ⚠ Ba cái bẫy đã đo được trong Auto_Clicker (PHẢI SỬA khi fork)

**Bẫy 1 — cờ `loop` là DƯƠNG TÍNH GIẢ.**
`dat()` bật `vong = True` khi gán nhãn cho khối **đã có nhãn** — mà một đồ thị **hoàn toàn không có vòng**
vẫn kích hoạt được. Ví dụ tái lập: `1 → {A, B, C}`, `A→M`, `B→M`, `C→Z`.
`diem_gop` cần một khối chung cho **cả ba** nhánh, không tìm ra → các nhánh đi độc lập → `B` đụng `M`
(đã được `A` đánh nhãn) → `loop: True` dù **không hề có vòng**.
→ Hậu quả: cảnh báo "VÒNG LẶP" sai, thanh trạng thái báo động, bộ chạy nhắc mỗi 200 bước.
→ **Cách sửa:** thay cờ toàn cục bằng **ngăn xếp đường đi hiện tại**. Chỉ là vòng thật khi khối gặp lại
nằm **trên chính đường đang đi** (ancestor). Đụng nhau ở điểm gộp là *merge*, không phải *cycle*.

**Bẫy 2 — vòng lặp nuốt mất khối bắt đầu là LỖI CHẾT.**
`1→2→3→1` khiến **mọi** khối đều có đường vào → `flow_entry` trả `None` → `order` rỗng →
**mọi huy hiệu hiện `–`**, kèm lỗi "Không tìm được bước bắt đầu".
→ **Cách sửa:** **khối BẮT ĐẦU cố định** (§4.2). Nó không bao giờ nhận được đường vào,
nên mọi vòng lặp ở chỗ khác luôn an toàn.
*(Chính đây là lý do trực giác "tạo sẵn 1 khối bắt đầu" là đúng — nó không chỉ để dễ đánh số.)*

**Bẫy 3 — bảng "Vấn đề" đánh số theo INDEX danh sách, không theo huy hiệu.**
`validate_process` ghi `f"Bước {si + 1}"` từ `enumerate(steps)`.
→ Panel có thể nói *"Bước 7"* về một khối mà huy hiệu ghi `4A.2`.
→ **Cách sửa:** mọi thông báo lỗi phải dùng nhãn từ `flow_order`, không dùng index.

**Bẫy 4 — `diem_gop` nhận nhầm ĐẦU NHÁNH làm điểm gộp khi đồ thị có vòng.**
*(Chỉ lộ ra sau khi vòng lặp thành công dân hạng nhất — Auto_Clicker chưa từng gặp.)*
Đi hết một vòng là "tới được" lại chính các nhánh vừa xuất phát, nên phép giao các tập
tới-được trả về một đầu nhánh. Hậu quả đo được ở sơ đồ mẫu: nhánh MUA mang nhãn `4`
còn nhánh BÁN mang `3B` — **hai nhánh song song mà lệch hẳn một cấp.**
→ **Cách sửa:** truyền `da_nhan` (tập khối đã có nhãn) vào `diem_gop`. Nó làm hai việc:
bỏ hẳn nhánh nào có ĐẦU đã mang nhãn (đó là cạnh quay lại, không đi tới đâu cả), và
dừng phép loang ở mọi khối đã có nhãn. Điểm gộp cũng phải tính **một lần** trong
`re_nhanh` rồi dùng lại — tính lại sau khi các nhánh đã có nhãn là ra kết quả khác.

**Bẫy 5 — `_bat_loi` nuốt mất danh sách tham số.**
pywebview dựng hàm JS bằng `inspect.getfullargspec(attr).args[1:]`, mà `getfullargspec`
**không** lần theo `__wrapped__` của `functools.wraps`. Một decorator `(*a, **kw)` trần
vì thế khai báo ra hàm JS **không tham số nào** → mọi đối số JS gửi đi bị vứt **im
lặng**, lỗi hiện ra ở tận đâu đâu.
→ **Cách sửa:** gán `bao.__signature__ = inspect.signature(fn)`.

**Bẫy 6 — `window.pywebview.api` là object RỖNG nhưng TRUTHY ngay từ đầu.**
pywebview tạo sẵn `api: {}` rồi mới đổ hàm vào sau bằng `_createApi(funcList)`. Chờ
bằng `if (window.pywebview?.api)` là qua ngay lập tức, và lời gọi đầu tiên chết với
*"api.py không có hàm bootstrap"* — trông y như lỗi Python trong khi Python hoàn toàn ổn.
→ **Cách sửa:** chờ một **hàm có thật**: `typeof window.pywebview?.api?.bootstrap === 'function'`.

### 3.4 Vòng lặp: đã hợp lệ sẵn

- Nối ngược lên trên **là hợp lệ**, có chủ ý (App.tsx cố ý **không** loại khối tạo thành vòng khỏi menu "Nối tới").
- Chốt chặn: `MAX_PROCESS_STEPS = 10000` bước cho một lần chạy.
- **Ngoại lệ vẫn là lỗi:** đường nối trỏ về **chính nó** (self-loop).

---

## 4. 🆕 Cơ chế MỚI của Cat_Studio

### 4.1 Ghim số ⟲ — hợp thức hoá vòng lặp

**Yêu cầu:** *"cho tôi khả năng fixed đánh số của 1 khối (chuột phải hiện lên menu) thì được phép loop lại
mà số cũ vẫn hợp lệ."*

**Thiết kế:**

- Mỗi khối có cờ `ghim: bool` (mặc định `false`), **lưu vào file**.
- Bật/tắt bằng **chuột phải → `📌 Ghim số` / `Bỏ ghim số`**.
- Khối đã ghim là một **điểm quay lại hợp lệ**.

**Luật đánh số khi gặp khối đã có nhãn:**

| Trường hợp | Xử lý | Cảnh báo |
|---|---|---|
| Khối **đã ghim** | Dừng đi tiếp trên nhánh đó. **Giữ nguyên nhãn cũ.** Ghi cạnh đó là **cạnh quay lại**. | ❌ không |
| Chưa ghim, nằm **trên đường đang đi** (ancestor) | Vòng lặp ngoài ý muốn | ⚠ *"Vòng lặp chưa ghim — hãy ghim khối `X` để xác nhận đây là vòng cố ý"* |
| Chưa ghim, **không** phải ancestor | Điểm gộp lệch nhánh (Bẫy 1) | ⚠ *"các nhánh của `Y` chụm lại không đều"* — **không** gọi là vòng lặp |

**Hiển thị:**
- Huy hiệu khối ghim đổi sang màu `--ghim` + icon `⟲`, hộp có viền vàng, thẻ chân ghi
  *"⟲ đã ghim số"*.
- **Cạnh quay lại vẽ nét đứt vàng kèm nhãn `⟲`** → nhìn sơ đồ là thấy ngay chỗ nào lặp về đâu.

**Hệ quả kéo theo — cạnh quay lại CHÍNH LÀ nhánh mặc định:**

1. `_khoa_nhanh` xếp mọi nhánh trỏ vào khối đã ghim **xuống cuối**, bất kể vị trí canvas.
   Khối quay về gần như luôn nằm phía TRÊN (đầu vòng lặp), nên xếp theo vị trí sẽ đẩy
   nó lên đầu và **mọi nhánh dưới nó không bao giờ được thử**.
2. Cạnh quay lại **không cần cổng** và được miễn luật "nhánh mặc định phải xếp cuối" —
   nghĩa của nó vốn đã là *"không nhánh nào khớp thì quay về trên"*. Bắt nó viết điều
   kiện phủ định của tất cả các nhánh trên là thừa và dễ sai.
3. **Không còn cảnh báo "nhánh nào cũng có điều kiện".** Đã bỏ hẳn: cả sơ đồ là một
   vòng lặp chạy lại mỗi nến (§6.1), nên không khớp nhánh nào = **hết lượt**, nến sau
   chạy lại từ đầu. Đó là cách "chờ" được diễn tả, và là trường hợp thường gặp nhất.

> **Ghi chú:** sơ đồ mẫu Compress **không dùng ghim số một lần nào** — đúng như nó
> phải vậy sau khi biết cả sơ đồ đã là vòng lặp. Ghim số để dành cho những chiến lược
> thật sự cần quay ngược *trong cùng một lượt*.

### 4.2 Khối BẮT ĐẦU (`kind: "start"`)

**Yêu cầu:** *"mặc định tạo cho tôi 1 khối bắt đầu, mục đích chỉ để đánh số cho dễ."*

- **Đúng một khối** mỗi sơ đồ, **tạo sẵn** khi mở canvas trắng.
- **Không hành động gì cả** — thuần điểm neo đánh số. Nhãn luôn là `1`.
- **Cấm mọi đường nối đi vào.** Giao diện từ chối kéo dây tới, validator báo lỗi nếu file bị sửa tay.
- **Không xoá được** (menu chuột phải mờ đi, có ghi lý do).
- `flow_entry` trả thẳng khối `start` → §3.3 Bẫy 2 biến mất.

Ví dụ đúng ý người dùng — 5 nhánh điều kiện entry từ khối bắt đầu:

```
                    ┌── 1A  Kiểm tra ĐK ──→ 1A.1 Mua  ──→ 1A.2 Kiểm tra ĐK ─┬─ 1A.2A  SL chặt
                    │                                                        └─ 1A.2B  SL rộng
                    ├── 1B  Kiểm tra ĐK ──→ 1B.1 Bán  ──→ …
[1] BẮT ĐẦU ────────┼── 1C  Kiểm tra ĐK ──→ … ──┐
                    ├── 1D  Kiểm tra ĐK ──→ … ──┴──→ quay về khối [3] đã ghim ⟲
                    └── 1E  (mặc định, không cổng — luôn xếp DƯỚI CÙNG)
```

### 4.3 Bấm ▶ Chạy → cửa sổ **Strategy Tester**

- Không chạy thẳng trên canvas như Auto_Clicker.
- Mở **cửa sổ pywebview thứ hai**.
- Bộ khung đã dựng: cửa sổ + `api.mo_tester(doc)` (soát lỗi trước, còn `error` thì không mở)
  + `api.tester_doc()` để cửa sổ đó hỏi ngược lại sơ đồ.

→ **Toàn bộ thiết kế nằm ở §12.** Bộ khung đó hiện còn **ba lỗi chắc chắn** — xem §12.12.

---

## 5. Luật rẽ nhánh (kế thừa nguyên vẹn)

Một khối có **nhiều đường ra** thì phải quyết định được đi đường nào:

1. Các nhánh được **thử lần lượt từ TRÊN xuống DƯỚI** (theo vị trí canvas).
2. Mỗi nhánh phải mở đầu bằng một **CỔNG** = khối mang hành động `check_cond`.
   *(Trừ ngã rẽ mà MỌI đầu nhánh đều là hành động — khi đó nó là ngã rẽ **VÀ** và bộ
   chạy làm hết, xem §5.0.)*
3. Nhiều nhất **MỘT** nhánh được để trống làm **nhánh mặc định** — và nó **bắt buộc xếp cuối cùng**
   (nhánh mặc định luôn khớp, xếp trên thì các nhánh dưới không bao giờ chạy tới).
4. Hai cổng cùng điều kiện y hệt → cảnh báo (cái dưới không bao giờ tới lượt).

**Vì sao cổng phải là `check_cond`:** ở điểm rẽ các nhánh thử lần lượt, nên nhánh trượt phải **lùi lại được**.
Một khối `check_cond` chỉ **đọc** dữ liệu thị trường nên lùi bao nhiêu lần cũng vô hại.
`Vào lệnh` hay `Sửa lệnh` thì không: chúng đã tác động ra thị trường, không rút lại được.

**Ngữ nghĩa ngược nhau — nhớ kỹ:**

| | Khớp | Không khớp |
|---|---|---|
| `check_cond` làm **cổng** | đi tiếp nhánh này | **chết nhánh** này, thử nhánh dưới |

Không nhánh nào khớp thì **hết lượt** — nến sau chạy lại từ khối Bắt đầu. Đó là cách
"chờ" được diễn tả, và là trường hợp thường gặp nhất, KHÔNG phải lỗi.

### 5.0 ⭐⭐ ĐẦU NHÁNH QUYẾT ĐỊNH NGHĨA CỦA NGÃ RẼ — HOẶC hay VÀ

> **Toàn CÂU HỎI → HOẶC** (chọn một). **Toàn HÀNH ĐỘNG → VÀ** (làm hết).

Người dùng bỏ hai cổng xu hướng rồi nối `[4]` toả sang cả Buy Stop lẫn Sell Stop, và
nói thẳng cái luật:

> *"bạn phải phân loại được điều kiện với hành động. nếu điều kiện rẽ nhánh thì sẽ là
> hoặc, còn hành động í thì sẽ là cả hai."*

**Đúng, và tôi đã cãi sai.** Lập luận của tôi là *"một hình mang hai nghĩa thì không đọc
được"*. Lập luận đó hỏng ở hai chỗ:

1. **Hai mệnh lệnh cạnh nhau thì "chọn một" vốn đã vô nghĩa** — chọn theo căn cứ nào?
   Không có câu hỏi nào cả. Chỉ còn đúng một cách đọc, nên không có gì để nhập nhằng.
2. **Hình không mang hai nghĩa — ĐẦU NHÁNH mang, và nó nhìn thấy được.** `§4.6` vừa cho
   khối màu theo mục đích (lam = hỏi · xanh/đỏ = mua/bán · tím = sửa), nên nhìn từ xa là
   phân biệt ngay. Khác hẳn ca ô số không nhãn ở `§6.3` — chỗ đó người dùng **không có
   tín hiệu nào**, đây thì tín hiệu to và có màu.

Và bắt vẽ nối tiếp thay thì **sơ đồ nói dối**: `[4] → Buy → Sell` đọc ra là *"đặt Buy,
RỒI mới đặt Sell"*, trong khi hai chân straddle đối xứng và cùng lúc. Hình toả ra mới
đúng sự thật; thêm chân thứ ba là thêm một nhánh, chứ không phải kéo dài một sợi dây.

| Đầu các nhánh | Nghĩa | |
|---|---|---|
| toàn **câu hỏi** | **HOẶC** — thử lần lượt trên xuống | như cũ |
| câu hỏi + **đúng 1** hành động (xếp cuối) | HOẶC + nhánh mặc định | như cũ |
| toàn **hành động** (≥2) | **VÀ — làm hết** | 🆕 |
| câu hỏi + **≥2** hành động | thật sự nhập nhằng → **lỗi** | như cũ |

Thứ tự chạy của ngã rẽ VÀ vẫn lấy từ **vị trí trên canvas**, trên xuống — không đẻ khái
niệm mới. Kết quả trên sơ đồ của người dùng: **167/167 nến đẻ đúng một cặp Mua/Bán cùng
`zone_id`**, y hệt bản nối tiếp.

⚠ **Có CẠNH QUAY LẠI thì KHÔNG phải VÀ.** Cạnh quay lại (trỏ vào khối đã ghim) mang sẵn
vai *"không nhánh nào khớp thì quay về trên"* — tức một **phương án thay thế**, đúng
nghĩa HOẶC. Trộn nó vào một ngã rẽ VÀ là hai nghĩa trong một chỗ.

**`core.la_nga_re_va` là NGUỒN DUY NHẤT của luật này**, dùng chung cho soát tĩnh (cho vẽ
hay không) và bộ chạy (đi thế nào). Hai bên tự suy riêng là sớm muộn soát tĩnh nói một
đằng bộ chạy chạy một nẻo.

#### 5.0a ⚠ RANH GIỚI PHẢI SẮC — *lùi* khác *làm nốt*

Đây là chỗ dễ hỏng ngầm nhất, vì cả hai đi qua đúng một đoạn mã trong `_chay_so_do`:

```
nhánh HOẶC  →  đi tiếp = THỬ PHƯƠNG ÁN KHÁC   → đã chạm thị trường thì CẤM (§12.5)
nhánh VÀ    →  đi tiếp = LÀM NỐT VIỆC ĐÃ ĐỊNH  → không phải lùi, nên không cấm
```

Nên `cham_thi_truong` được hỏi **ở mức đang quay về**, không hỏi một lần cho cả lượt:
cùng một cú *"hết nhánh ở đây"* mang hai nghĩa tuỳ mức cha là VÀ hay HOẶC. `bo_chay` giữ
một ngăn xếp `va[]` song song với `ngan[]` đúng để trả lời câu đó.

Bài kiểm neo cả hai chiều: ngã rẽ VÀ phải ra **hai** lệnh, và ngã rẽ HOẶC mà nhánh trên
đã vào lệnh rồi mới cụt thì **không được** lùi sang nhánh dưới. Sơ đồ mẫu (XOR) chạy lại
ra **trùng từng con số**: 550 lệnh · −19,52 R · DD 1,08 %.

#### 5.0b `duong` trong nhật ký = ĐÃ ĐI QUA, không phải TỔ TIÊN

Trước đây `duong` bị `pop` mỗi lần lùi nên nó luôn song song với ngăn xếp — tức là *tổ
tiên của khối đang đứng*. Với ngã rẽ VÀ, cách đó **nói dối**: lượt đi qua cả `[4A]` lẫn
`[4B]` mà log chỉ còn `[4B]`, nhánh kia biến mất dù nó vừa đặt một lệnh thật.

Giờ chỉ append. Đúng chữ `§12.8` vẫn viết (*"đường đã đi, THEO THỨ TỰ"*), và tốt hơn cả
ở ca cũ — một cổng **đã khớp** rồi mới cụt phía dưới thì nó vẫn nằm trong đường, vì lượt
đó thật sự đã đi tới đó:

```
trước:  [1]→[2]→[3]           hết lượt tại [4B]
sau:    [1]→[2]→[3]→[4]       hết lượt tại [4B]      ← [4] đã khớp, giờ mới thấy
```

Kèm theo: **mỗi bản ghi `viec` mang `khoi` của chính nó.** Một lượt qua ngã rẽ VÀ đặt hai
lệnh ở hai khối khác nhau; không có khoá này thì nhật ký có hai dòng `lenh_dat` mà không
nói được cái nào của khối nào — đúng câu người ta cần khi debug.

### 5.1 ⭐ HAI KHỐI VÀO LỆNH NỐI TIẾP — luật hỏi về *LỆNH*, không hỏi về *hình vẽ*

Người dùng bỏ hai cổng xu hướng rồi nối thẳng `[4] Còn chỗ cho lệnh mới?` sang **cả hai**
khối Vào lệnh, và hỏi: *"tôi bỏ điều kiện xác định chiều, thì nó đặt 2 lệnh chứ, có sai
logic gì đâu."*

Ý định là một **straddle nén**: đặt sẵn Buy Stop trên đỉnh zone và Sell Stop dưới đáy
zone, giá phá ra bên nào thì ăn bên đó. Hoàn toàn hợp lệ — và với một cú nén thì nó còn
tự nhiên hơn việc chọn hướng bằng MA, vì không ai biết lò xo sẽ bung lên hay xuống.

**App chặn cả hai cách vẽ, bằng hai luật mâu thuẫn nhau:**

```
song song  [4] ─┬─ Buy Stop      luật rẽ nhánh chặn: "mỗi nhánh phải mở đầu bằng cổng"
                └─ Sell Stop     và chặn ĐÚNG — đo được 0/182 nến đẻ ra hai lệnh:
                                 rẽ nhánh là XOR, khối thứ hai CHẾT vĩnh viễn

nối tiếp   [4] → Buy Stop → Sell Stop      luật cũ chặn: "một lượt sẽ đẻ ra HAI lệnh"
                                           mà lời khuyên của nó — "hãy tách thành hai
                                           NHÁNH" — chỉ thẳng vào luật ở trên
```

Vòng kín: **không có đường hợp lệ nào để đặt hai lệnh trong một nhịp.** Mà bộ chạy thì
làm được sẵn — nối tiếp chạy 3 tháng ra **167/167 nến đẻ đúng một cặp Mua/Bán cùng
`zone_id`**. Chỉ soát tĩnh chặn.

**Chỗ sai của luật cũ là ở TẦNG CÂU HỎI.** Nó đếm *số khối Vào lệnh trên một đường* —
một câu hỏi về **hình vẽ**. Câu đúng là về **lệnh**:

> **Hai lệnh này có CÙNG TỒN TẠI ĐƯỢC trong sổ không?**
> Được → cho vẽ. Không được → chặn.

Cùng tồn tại được thì sổ giữ cả hai, và "hai lệnh" đúng nghĩa là hai lệnh. Không cùng tồn
tại được thì chúng rơi vào **đúng một chỗ** — đó không phải hai lệnh, mà là **một lệnh
viết hai lần**.

| Hai khối khác nhau ở | Cùng tồn tại? | |
|---|---|---|
| **hướng** | ✔ | Buy trên đỉnh + Sell dưới đáy — straddle |
| **mốc neo** | ✔ | cùng Buy, một ở đỉnh zone một ở giá hiện tại — hai giá khác nhau |
| **đệm** | ✔ | cùng Buy đỉnh zone, 0.1 và 0.5 × ATR — rải thang |
| **SL / TP** | ✔ | cùng giá vào, chốt lời hai mức — sàn giữ cả hai |
| **lot** | ✔ | hai ticket riêng |
| **không khác gì cả** | ✘ **lỗi** | một lệnh viết hai lần — gần như luôn là `Ctrl+D` rồi quên sửa |

Khoá so sánh là `core._KHOA_MOT_LENH` = `(huong, loai, lot, entry, dem, sl, tp)`.

⚠ **SL/TP/lot NẰM TRONG khoá, và đó là chủ ý.** Bảng đầu tiên tôi trình chỉ có bốn khoá
(`hướng · loại · mốc · đệm`); nhưng *cùng giá vào mà khác TP* là hai chân chốt lời hai
mức, sàn giữ cả hai — chặn nó là phá đúng cái nguyên tắc luật này vừa dựng lên.

⚠ **`name` / `pos` / `id` ĐỨNG NGOÀI khoá.** Đổi tên khối hay kéo nó sang chỗ khác không
sinh ra một cái lệnh khác. Đây là khoá về LỆNH, không phải về khối.

⚠ **So THÔ, không quy tên tham số về giá trị.** `dem = 0.1` và `dem = dem_vao_lenh` (= 0.1)
ra cùng một giá nhưng ở đây coi là khác nhau — cố ý, để mỗi tầng lo việc của mình: *"hai
chỗ cùng một SỐ"* là việc của `_soat_so_lap` (§6.4), luật này chỉ lo *"hai khối cùng một
LỆNH"*. Trộn vào thì `validate_flow_graph` — vốn là hàm thuần về đồ thị — phải biết bảng
giá trị tham số.

**Luật rẽ nhánh KHÔNG đổi.** Song song vẫn là XOR và vẫn bị chặn, vì ở đó cái sai là thật:
khối thứ hai không bao giờ chạy tới, mà sơ đồ thì trông như nó có chạy.

> ⚠ **Straddle thiếu OCO — chưa có luật nào bắt.** Đặt hai chân xong, một chân khớp thì
> chân kia vẫn nằm đó. Manage của sơ đồ mẫu chỉ huỷ lệnh chờ khi *nén đã tan*, mà lúc một
> chân vừa khớp thì nén đang **bung ra** — có thể kịp, có thể không. Giá phá lên khớp Buy
> rồi quét ngược xuống khớp luôn Sell là **ôm cả long lẫn short**. Vẽ được bằng một cổng
> Manage: `lệnh này chưa khớp` **và** `số vị thế > 0` → **Kết thúc lệnh này**. Chưa đưa
> vào sơ đồ mẫu vì mẫu vẫn là D_02 một chiều.

---

## 6. Bộ khối & hành động của Cat_Studio

### 6.0 ⭐⭐ MỘT CHIẾN LƯỢC = HAI SƠ ĐỒ

```
   ┌── Tab ENTRY ────────────────────┐     ┌── Tab MANAGE ───────────────────┐
   │  con trỏ ĐI SĂN                 │     │  chạy MỘT LƯỢT CHO MỖI LỆNH     │
   │  một lượt mỗi nến               │     │  đang sống, cũng mỗi nến        │
   │  chỉ nó được TẠO lệnh           │     │  chỉ nó được SỬA lệnh           │
   └─────────────────────────────────┘     └─────────────────────────────────┘
```

**Thứ tự trong một nến:**

```
0.  runtime cập nhật vùng nén · xu hướng · chỉ báo      ← không phải khối
1.  với MỖI lệnh đang sống → chạy MANAGE từ khối 1
2.  chạy ENTRY từ khối 1                                ← có thể sinh một lệnh mới
```

**Manage TRƯỚC Entry** — đúng `OnTick`: `CheckPendingActivation` → `ManageBreakEven` →
rồi mới tới phần quyết định. Chạy ngược lại thì lệnh vừa sinh bị quản lý ngay trong
chính nến đẻ ra nó.

**Manage KHÔNG giữ con trỏ giữa các nến.** Nó tính lại từ trạng thái quan sát được, y
như D_02 làm mỗi tick. Nhờ vậy mấy câu guard kiểu `if(sl >= entry) continue` **hiện ra
thành cổng** trên sơ đồ thay vì chôn trong C++.

**Ranh giới khoá được — đây là món quà của việc tách tab:**

| | Entry | Manage |
|---|---|---|
| Kiểm tra ĐK | ✔ | ✔ |
| **Vào lệnh** | ✔ | ✘ |
| **Sửa lệnh** | ✘ | ✔ |
| Toán hạng nhóm **"Lệnh này"** | ✘ **báo lỗi** | ✔ |

> **Entry chỉ TẠO. Manage chỉ SỬA.** Một câu, và `validate_actions(…, tab)` soát tĩnh
> được — chỉ thẳng vào khối sai. Đây là loại lỗi MQL5 không bao giờ bắt.

Ribbon **ẩn hẳn** nút không thuộc tab (không làm mờ): làm mờ thì người dùng vẫn phải
đoán vì sao.

Pill `Entry | Manage` là một **chip nổi ở góc trên-trái CANVAS**, không chiếm dải
ngang riêng. Nó trả lời câu "đang vẽ sơ đồ NÀO", nên nằm ngay trên chính cái đang vẽ
là đúng chỗ — và lấy lại được ~34px chiều cao. Có **chấm đỏ khi tab kia đang lỗi**, để
lỗi không trốn được sau lưng.

### 6.1 ⭐ MỖI SƠ ĐỒ LÀ MỘT VÒNG LẶP

> Sơ đồ chạy lại **từ khối Bắt đầu ở MỖI NẾN MỚI** — đúng như `OnTick` của MQL5 chạy
> lại từ đầu mỗi tick. D_02 không có gì chạy nền cả.

Hệ quả, và nó gỡ được rất nhiều thứ:

- **"Chờ tới khi" KHÔNG phải vẽ.** Không cổng nào khớp → hết lượt → nến sau tự chạy
  lại. Bản vẽ tay đầu tiên của sơ đồ mẫu có **5 vòng tự-lặp + 3 mũi tên "quay lại 1"**;
  cả 8 cạnh đó biến mất.
- **Không cần loại khối "Vòng theo dõi".** Nó chỉ là cái vòng lặp lớn vẽ lại lần nữa
  ở bên trong.
- **Trạng thái không cần khối.** `IDLE / COUNTING / CONFIRMED / PENDING / CONSUMED` của
  `FilterEngine` tồn tại vì MQL5 **không có đồ thị** — mỗi tick nó chạy lại từ đầu nên
  phải tự nhớ đang ở đâu. Ta có đồ thị, và trạng thái vùng nén là **dữ liệu đọc được**
  qua toán hạng (`số_nến_nén`, `đỉnh_vùng`, …), không phải khối.

### 6.2 HAI LOẠI KHỐI — hết

| kind | Nghĩa |
|---|---|
| `start` — **Bắt đầu** | Điểm neo: mỗi nến chạy lại từ đây. Đúng một cái, không xoá được, không nhận đường vào (§4.2). |
| `action` — **Khối** | Đúng một hành động. Mang `check_cond` thì nó là **cổng rẽ nhánh**. |

**Đã bỏ `Vòng theo dõi` và `Nhóm 1 lần`:**

- *Vòng theo dõi* — thừa, xem §6.1.
- *Nhóm* — cấu trúc của một chiến lược đến từ **tách trách nhiệm**, không từ lồng hộp.
  Gộp nhóm chỉ đẻ thêm câu hỏi "nhóm có phải một đơn vị chạy không".
- Kéo theo: **bỏ template cụm khối rời**. Một template phải là thứ **chạy được** —
  cụm khối rời mở ra là một mớ khối lạc không có đường vào, dán xong vẫn phải nối lại
  từ đầu. `TEMPLATE_KINDS` chỉ còn `strategy`.

### 6.3 BA HÀNH ĐỘNG — đọc · tạo · sửa

> **Chốt sau khi bàn lại.** Ban đầu định 8 hành động (3 hiện, 5 ẩn). Khi làm rõ rằng
> SL/TP là thao tác **sửa lệnh đã có** chứ không phải hành động riêng, cả 5 cái định
> ẩn đều tan vào ba việc cơ bản — không cái nào bị mất đi, chỉ là không cần khối riêng.

| key | Nhãn | Việc |
|---|---|---|
| `check_cond` | **Kiểm tra điều kiện** | ĐỌC thị trường + tài khoản rồi quyết đi nhánh nào. **Đây là CỔNG rẽ nhánh.** |
| `vao_lenh` | **Vào lệnh** | TẠO vị thế mới: Mua/Bán · Market/Stop/Limit · lot · **SL & TP ban đầu** |
| `sua_lenh` | **Sửa lệnh** | SỬA lệnh ĐÃ CÓ. Chế độ: `dời SL` · `dời TP` · `hoà vốn` · `trailing` · `đóng một phần` · `đóng hẳn` · `huỷ lệnh chờ` |

**Năm khái niệm cũ đi đâu:**

| Định làm khối riêng | Thật ra là |
|---|---|
| `cầu dao` (chặn rủi ro) | toán hạng `số_lệnh_mở`, `drawdown_%`, `giờ` trong **Kiểm tra điều kiện** |
| `cổng` | chính là **Kiểm tra điều kiện** đứng đầu một nhánh |
| `kích hoạt` (chờ khớp) | không cần gì cả — cả sơ đồ chạy lại mỗi nến (§6.1), nên "chờ" là hết lượt |
| `vào` | **Vào lệnh** |
| `thoát` | chế độ `đóng hẳn` / `huỷ lệnh chờ` của **Sửa lệnh** |

*(Từng có `dat_co` — Đặt cờ — để dành làm bộ nhớ. Bỏ: D_02 không cần, và giữ một cơ
chế không ai dùng chỉ tổ rác. Cần thì thêm lại lúc có ca dùng thật.)*

**Toán hạng của `check_cond`** — **22 cái, 5 nhóm**, đủ tái lập Compress EA 100 %:

| Nhóm | Toán hạng |
|---|---|
| Giá (4) | `close`, `open`, `high`, `low` — mỗi cái chọn khung |
| Chỉ báo (2) | `atr(tf, period)`, `ma(tf, period, method)` |
| Sổ lệnh (3) | `so_vi_the`, `so_lenh_cho`, `drawdown_pt` |
| Zone (7) | `zone_dem`, `zone_HH`, `zone_LL`, `zone_range`, `zone_atr_tb`, `zone_hop_le`, **`zone_da_sinh_lenh`** |
| **Lệnh này** (6) *(chỉ Manage)* | `lenh_da_khop`, `lenh_la_mua`, `lenh_sl_hoa_von`, `lenh_lai_R`, `lenh_so_nen_song`, `lenh_thuoc_zone` |

⚠ **Bảng này TỪNG hứa 32 cái / 6 nhóm, trong đó 13 cái chưa bao giờ tồn tại** (`Bid` ·
`Ask` · `Spread` · `Donchian` · `Volume_MA` · `số lệnh hôm nay` · `giá vào` · `giờ` ·
`thứ` …). Ai đọc file này để thiết kế sẽ thiết kế cho một cái kho không có thật — nguy hơn
hẳn một con số sai. Lý do bỏ từng cái: **§15.6**. Nhóm "Chuẩn hoá" cũ đã **hoà tan thành
ĐƠN VỊ** (`atr_bps` → `atr [× ATR nền]`), đúng thiết kế.
**Số lượng lấy từ `len(kho.TOAN_HANG)`, đừng gõ tay lần nữa** — chính cái gõ tay là thứ đã
lệch ba chỗ (core.md 32 · README 17 · thực tế 19).

**Phép so dùng KÝ HIỆU, không dùng chữ — 8 cái:**
`<` `≤` `>` `≥` `=` `≠` · `là ĐÚNG` · `là SAI`.
*(`cắt lên ↗` · `cắt xuống ↘` · `trong khoảng` KHÔNG có, và không thêm lại — **§15.9**.)*
Một cổng của Compress mang 4–5 điều kiện; viết *"lớn hơn hoặc bằng"* thì mỗi dòng dài
gấp đôi và mắt phải **đọc chữ** thay vì **liếc thấy quan hệ**.

**`vùng_này_đã_sinh_lệnh` thay cho `COMP_CONSUMED`** — và nó KHÔNG phải cờ ẩn: lệnh
mang `vùng_id`, nên câu hỏi chỉ là một phép tra bảng *"có lệnh nào trỏ về vùng hiện
hành không"*.

Toán hạng vốn đã **đúng/sai** (`đang_có_vị_thế`, `cờ`…) không có vế phải — hộp thoại
đổi sang một ô tick **KHÔNG**. *"Đang có vị thế bằng 1"* là câu không ai đọc được.

**Mọi khoảng cách giá** (SL, TP, đệm vào lệnh, mốc hoà vốn) dùng chung một kiểu
`{tinh, value}`. **Không có đơn vị pip hay đô** — đúng hợp đồng chuẩn hoá của
Compress EA (§7.1):

| `tinh` | Nghĩa |
|---|---|
| `atr` | × **ATR hiện tại** |
| `atr_nen` | × **ATR NỀN** — ATR dài hạn (100 nến) của chính thị trường đó |
| `atr_zone` | × **ATR trung bình của zone** |
| `R` | × R (rủi ro) |
| `bien_zone` | mép zone đối diện |
| `gia` | giá tuyệt đối |

⚠ **`pt` ("% của giá") đã bỏ.** Nó là `bps` chia 100 — hai cái tên cho đúng một phép
chuẩn hoá, nên người dùng phải đoán xem chúng khác nhau chỗ nào (không khác). Không có
phép chuyển tự động, nên gặp `pt` thì soát tĩnh nói to. Một phép đổi đúng-một-nửa là loại
hỏng tệ nhất: file vẫn chạy, chỉ sai.

⚠ **`bps` ("phần vạn của giá") CŨNG ĐÃ BỎ — §15.7.** Nó chuẩn hoá theo **mức giá**, mà thứ
trôi qua thời gian là **chế độ biến động**. Đo trên XAUUSD 2021–2026: cùng cổng
`atr < 7 [bps]` khớp **74,3 %** số nến năm 2023 và **7,8 %** năm 2026 — chiến lược tự tắt
dần theo giá vàng mà sơ đồ không nói một câu nào. `atr_nen` chia cho chính thị trường đó
nên nó đứng yên (độ trôi 68 điểm → 7,4 điểm). Cũng **không đổi tự động** được: `7 bps` và
`0,75 × ATR nền` là hai con số khác hẳn nhau.

⚠ **CÁI THƯỚC KHÔNG ĐƯỢC LÀ THAM SỐ.** `core.CHU_KY_ATR_NEN = 100`, cố định, không đưa vào
bảng tham số và không đưa vào không gian tìm kiếm. **Ngưỡng** thì ngược lại — đó là quyết
định của chiến lược.

⚠ **`lot` ĐÃ BỎ khỏi khối Vào lệnh — §15.13.** Nó là đơn vị tuyệt đối cuối cùng còn sót:
0,01 lot trên $10.000 khác hẳn trên $100.000. Nay khối Vào lệnh khai **rủi ro % vốn**, còn
khối lượng do bộ chạy suy ra từ đó và khoảng cách SL. Đo được: số lệnh và tổng R không đổi
một chút nào, nhưng **sụt vốn đổi 20–30 lần** — vì con số cũ (`DD 0,66 %`) nói về việc cỡ
lệnh quá bé chứ không nói gì về chiến lược.

⚠ **`bien_zone` KHÔNG dùng con số bạn gõ.** `_khoang` tính `v` rồi vứt — nó trả thẳng
khoảng cách tới mép zone đối diện, nên `SL = 1 [mép zone đối diện]` và `SL = 99 […]` ra y
hệt. Hộp thoại **khoá ô số** khi chọn đơn vị đó, thay vì để một con số vô nghĩa nằm đó.

#### CHỈ BÀY RA THỨ DÙNG ĐƯỢC

Luật chung, đã ghi sẵn trong `core.DON_VI_CHO`: *"bày ra một lựa chọn vô nghĩa rồi soát
tĩnh mắng là tệ hơn không bày — nên lọc ngay tại nguồn."* Bốn nhát cắt:

| Cắt gì | Vì sao | Bảng |
|---|---|---|
| Theo **chỗ dùng** | `R` ở SL là vòng tròn (đo rủi ro bằng chính rủi ro); `bien_zone` ở đệm không có mốc để đo tới | `DON_VI_CHO` |
| Theo **loại đại lượng** | chỉ **bề rộng** giá mới chuẩn hoá được; `close / close × 10⁴` luôn ra 10000 | `TOAN_HANG_LOAI` |
| **Không đo bằng chính nó** | `zone_atr_tb` với `× ATR zone` ⇒ luôn = 1 | `DON_VI_CHINH_NO` |
| Theo **zone** | trước cổng zone thì `× ATR zone` không có mẫu số ⇒ NaN ⇒ cổng luôn trượt | `khoi_sau_cong_zone` |

Nhát cuối cũng lọc **danh sách toán hạng**: khối chưa đi qua cổng zone thì không thấy
`Zone — số nến / đỉnh / đáy / bề rộng / ATR trung bình / đã sinh lệnh` — thay vì thấy rồi
bị `_soat_cong_zone` báo lỗi đỏ. Cùng một luật mà dropdown toán hạng vốn đã áp cho nhóm
*"Lệnh này"* ở Entry; đây là áp nốt cho zone.

`core.khoi_sau_cong_zone()` là **một** phép duyệt, dùng chung cho cả soát tĩnh lẫn giao
diện (gửi kèm `validate.luong[tab].sau_cong_zone`). TypeScript **không** tự đi lại đồ
thị — hai đoạn mã duyệt cùng một sơ đồ là hai luật, và chúng sẽ lệch nhau.

> ⚠ **`atr` và `atr_zone` là HAI THỨ KHÁC NHAU, tách ra là có chủ ý.**
> Đệm vào lệnh đo bằng ATR *hiện tại* — tấm khiên mỏng ngoài mép zone, đủ lọc một nhịp
> phá giả. Rủi ro đo bằng ATR *trung bình cả cú nén* — lấy mức nhiễu thật suốt đợt nén,
> nên mỗi lệnh rủi ro một R tương đương bất kể zone rộng hẹp. Gộp làm một là mất đúng
> cái làm cho 1R nhất quán giữa các tín hiệu.

**Toán hạng giá không còn `shift`.** Nó là ô số **thứ ba** trên hàng điều kiện — cùng
chỗ, cùng hình dạng với ô *chu kỳ* của ATR/MA, nhưng nghĩa khác hẳn; một ô trắng không
nhãn mang hai nghĩa tuỳ toán hạng thì không ai đọc ra. Bỏ được vì nó chưa từng khác 1
(mẫu, cả 10 file đã lưu), và `doc_cot` hiểu *thiếu shift* **đúng bằng** `shift = 1`
(`i -= max(0, shift - 1)`) — `tests/test_bo_chay.py` canh chuyện đó bằng backtest, không
bằng đọc lại công thức. Giờ ô thứ ba chỉ còn **một** nghĩa (chu kỳ) và nghĩa đó được viết
ra thành chữ. Với D_02 thì đây là bám sát **hơn**: EA luôn dùng `iClose(tf, 1)` và không
có tuỳ chọn nào khác.

**Neo lệnh chờ:** lệnh Stop **luôn** neo vào mép vùng nén thuận chiều (đỉnh cho Mua,
đáy cho Bán) — đó là chỗ duy nhất Compress EA đặt lệnh. Nên **không có tham số "neo
vào đâu"**; `dem` chỉ là khoảng đẩy ra ngoài mép đó.

### 6.4 ⭐ BẢNG THAM SỐ — **bản ghi**, không phải bước setup

> **LÕI: ở đâu chờ một con số, một CHUỖI nghĩa là tên tham số.**
> Áp đều cho chu kỳ chỉ báo, khối lượng, ngưỡng so sánh, khoảng cách SL/TP.
>
> **GIAO DIỆN: gõ = số · chọn = tham số. Tên không bao giờ gõ được.**
>
> **ĐƠN VỊ THUỘC VỀ CÁI Ô. Ai điền vào ô đó cũng phải mang đúng đơn vị ấy.**

#### Vì sao giao diện hẹp hơn lõi

Lõi nhận cả hai. Giao diện thì cố ý **chỉ cho gõ chữ số**, và đây là lý do.

Trước đây năm ô số trong app chạy **hai luật trái nhau**: chỉ ô "vế phải điều kiện" thật
sự nhận được một cái tên (nó có `<datalist>` và placeholder *"số hoặc tên tham số"*).
Bốn ô còn lại — chu kỳ, chỉ số nến, SL/TP/đệm, lot — chạy `parseInt`/`parseFloat`, nên
**hiện ra một cái tên mà gõ vào là nuốt mất**: `chu_ky_atr` → `0`. Tức app dạy *"chỗ này
gõ tên được"* ở một ô rồi phá lời dạy đó ở bốn ô kia. Nhìn ô chu kỳ đang hiện
`chu_ky_atr`, người dùng tưởng đó là chỗ **đặt tên**. Không trách được.

Nên `ActionDialog.OSo` là **một** ô dùng cho **cả năm chỗ**, và nó bỏ hẳn khả năng gõ
chữ — không phải dán nhãn giải thích, mà làm cho việc gõ tên **bất khả thi**. Khi ô đang
giữ một cái tên, nó vẽ thành **chip** (không sửa được, có `✕` để về số, đỏ + gạch ngang
nếu cái tên đó không còn trong bảng).

Tên vào ô bằng **hai** đường, và cả hai đều là CHỌN, không phải gõ:

1. nút *"Đặt tên cho số này"* ở bảng Vấn đề — đường chính, xuất hiện khi một số lặp;
2. nút `▾` ngay trong ô số — mời những tham số **đã có**.

> ⚠ Bản đầu **không có** nút `▾`, và đó là một cửa một chiều: bấm `✕` trên một chip là
> tham số biến mất khỏi ô, mà cảnh báo đặt tên chỉ đếm **số gõ tay** — còn đúng một số
> thì không đủ hai, không có cảnh báo, không có nút, **không đường nào lấy lại**.

Hệ quả: cả app còn **đúng một** ô để gõ chữ đặt tên — cột **Tên** của bảng Tham số.

#### Đơn vị thuộc về cái ô

Mỗi ô số có một đơn vị (`core.don_vi_cua_o`) — hoặc **chọn được** (khoảng cách: bps ·
× ATR · × ATR zone…), hoặc **cố định** (chu kỳ luôn `nến`, lot luôn `lot`, `zone_dem`
luôn `nến`, `so_vi_the` luôn `lệnh`). Mỗi tham số khai một đơn vị bằng **khoá** trong
cùng bảng đó. Từ đó:

- nút `▾` **chỉ mời tham số đúng đơn vị của ô** — `chu_ky_atr` (nến) không bao giờ hiện
  ra ở ô Stop Loss;
- chọn tham số xong thì **ô đơn vị khoá** (vẫn hiện, có 🔒): một cái tên chỉ mang một
  nghĩa. Cần `7 bps` và `7 × ATR` thì đặt **hai** tham số;
- soát tĩnh so đơn vị khai với đơn vị ở chỗ dùng: dùng hai đơn vị → **lỗi**; khai một
  đằng dùng một nẻo → **cảnh báo**.

⚠ `loai = "dem"` **không đủ** để suy ra đơn vị: `zone_dem` đếm **nến** còn `so_vi_the`
đếm **lệnh**. Gộp chung thì nút `▾` mời `so_vi_the_toi_da = 3 lệnh` vào ô *"zone cần bao
nhiêu nến"*. Nên toán hạng tự khai `don_vi` (`kho/*.py`) — bài kiểm bắt đúng chỗ này ngay
lần chạy đầu.

#### ⚠ 6.4a LỖI THẬT: hộp thoại CẤT bản nháp, trong khi HIỆN bản Python đã chuẩn hoá

*"tại sao bị lỗi đơn vị, nến thành bps"* — ô trong hộp thoại ghi `Zone — số nến ≥ 10`
đơn vị **nến**, mà thẻ trên canvas ghi `Zone — số nến ≥ 10 **bps của giá**`.

Chuỗi hỏng, và cả bốn mắt xích đều "đúng phần việc của mình":

1. Dòng điều kiện **MỚI** sinh ra với `{value: 7, tinh: "bps"}` (`ActionDialog.tsx`).
2. Đổi vế trái sang `Zone — số nến` → **`tinh: "bps"` NẰM LẠI**. Không ai dọn.
3. Ô đơn vị hiện đúng **"nến"** — nó hỏi `core.don_vi_cua_o`, không đọc `tinh`. Phần xem
   trước cũng đúng — nó hỏi `api.save_action`, tức đi qua `normalize_action`.
4. Nhưng nút **Lưu** gọi `onLuu(a)` — đẩy thẳng **bản nháp** ra canvas. Thẻ dựng lại từ
   đó, và `action_display` thì đọc `tinh`.

> **Hộp thoại nhờ Python chuẩn hoá, trình bày câu trả lời của Python, rồi cất đi bản của
> chính nó.** Xem trước và dữ liệu cất đi là hai thứ khác nhau — mà cái người dùng tin là
> cái nhìn thấy.

`normalize_action` vốn **đã** vứt `tinh` không hợp lệ (`don_vi_cho("zone_dem")` rỗng nên
`tinh` không được giữ). Nên bản vá chỉ là **dùng nốt thứ nó vừa trả về**: `save_action`
trả cả `action` lẫn `display`, hộp thoại đang lấy mỗi `display` rồi bỏ `action`.

⚠ **Gọi LẠI `save_action` lúc bấm Lưu**, không dùng kết quả của phần xem trước: xem trước
hoãn 200 ms, gõ xong bấm Lưu ngay là nó chưa kịp chạy và ta cất một bản còn cũ hơn cả
nháp. Hỏng đường truyền thì ngã về nháp — thà giữ nguyên thứ vừa gõ còn hơn mất.

*(File đã lưu thì vẫn sạch, vì `normalize_process` chạy lúc ghi. Chỉ node trong bộ nhớ và
cái thẻ là sai — tức nhìn sai suốt cả phiên làm việc, tới khi mở lại file mới hết.)*

⚠ Cột `don_vi` của bảng tham số **từng là chữ tự do**, và nó âm thầm mục: sơ đồ mẫu mang
`"× ATR vùng"` — một chuỗi không tồn tại ở đâu, rác từ lần đổi tên vùng→zone, không ai
bắt được vì chưa có gì đọc nó. File cũ đi qua `DON_VI_THAM_SO_CU`; chữ lạ thì **để trống
rồi suy từ chỗ dùng**, chứ không đoán.

#### Cơ chế so sánh — MỘT cờ cho cả khối

Một ô tích cạnh ô **Tên**: `☑ So hai đại lượng`. Nó quyết hình dạng **mọi dòng** trong
khối đó:

| Cờ | Mỗi dòng | Lưới |
|---|---|---|
| tắt | `[đại lượng ⚙] [phép] [số ▾] [đơn vị]` — kèm cả dòng đúng/sai | 6 cột |
| bật | `[đại lượng ⚙] [phép] [đại lượng ⚙]` | 5 cột — **bỏ hẳn** cột đơn vị |

Cột đơn vị bị **bỏ**, không phải làm mờ: hai vế cùng chia một mẫu số nên nó triệt tiêu,
giữ một cột rỗng là chiếm 118px mà chẳng nói gì, trong khi hai ô chọn toán hạng đang
chật. Cả khối cùng một cơ chế nên mọi dòng vẫn thẳng cột.

⚠ Ô **⚙ luôn chiếm chỗ**, kể cả khi toán hạng chưa chọn hoặc không có tham số nào — mà
11/17 toán hạng đúng là không có. Chỉ *vẽ* bánh răng khi thật sự có tham số; còn lại để
trống. Bản đầu ẩn hẳn ô đó, nên ngay trong một khối, dòng `ATR` có ⚙ mà dòng `Zone — số
nến` không → hai ô chọn rộng khác nhau → cột lệch.

⚠ Trước đây lựa chọn này là một **chip trên từng dòng** (`số` / `đ.lượng`). Chip ấy chỉ
tồn tại vì **một hàng phải gánh hai hình dạng** — hậu quả là hai dòng cùng khối trông
khác nhau, cột lệch, và mắt phải đọc lại hình dạng ở mỗi dòng. Nâng lựa chọn lên mức
KHỐI thì mọi dòng trong đó giống hệt nhau, và cái chip tự thừa.

Cùng lý lẽ app đã viết cho phép HOẶC: *"tách ra thành hai nhánh riêng trên sơ đồ — nhìn
sơ đồ là thấy được, còn chữ hoặc giấu trong hộp thoại thì không."* Muốn một cổng vừa so
số vừa so đại lượng thì **nối hai cổng** — nối tiếp chính là VÀ.

**Là CƠ CHẾ, không phải LOẠI KHỐI.** Hai kiểu dùng chung bộ soát, chung phép chuẩn hoá,
chung hàm dựng chữ trên thẻ — chỉ khác đúng cái vế phải. Tách thành loại khối riêng là
chẻ ba đoạn mã đáng lẽ chỉ có một.

Ba luật đi kèm:

- **Cờ được LƯU trên khối**, không suy ra được: khối vừa tạo chưa có điều kiện nào để
  suy, mà vẫn phải biết thêm dòng kiểu nào. File cũ (không có cờ) thì suy từ chính các
  điều kiện — đã đo, không sơ đồ nào từng trộn hai kiểu trong một khối, nên phép suy này
  không có ca mập mờ.
- **Đổi cờ viết lại vế phải của mọi dòng**, giữ vế trái và phép so. Có mất dữ liệu, và
  đó là chủ ý: hình dạng do cờ quyết. Hộp thoại là bản nháp — Huỷ là xong, lưu rồi vẫn
  còn Hoàn tác.
- **Toán hạng đúng/sai + cờ bật → LỖI, không sửa lén.** `lệnh này đã khớp > zone_HH`
  không phải một câu; nhưng đổi hộ toán hạng là vứt mất thứ người dùng đã chọn mà họ
  không hề biết. Chuẩn hoá ép HÌNH DẠNG, soát tĩnh nói về NGHĨA.

⚠ `đúng/sai` ở lại cùng `số`, không tách ra cơ chế thứ ba — đo sơ đồ mẫu thì ba cổng
(`Zone đã đủ điều kiện`, hai cổng Manage) **thật sự trộn** `số` với `đúng/sai`. Tách là
gãy ba cổng có thật.

#### ⚙ Tham số của toán hạng nằm trong menu riêng

Khung thời gian · chu kỳ · kiểu trung bình **không** nằm trên hàng điều kiện nữa. Trước
đây chúng nằm inline nên vế trái phình từ **1 ô** (`zone_dem`) tới **4 ô** (MA) tuỳ toán
hạng — hàng nào cũng lệch hàng nào, và thêm một chỉ báo 4 tham số là hỏng bố cục.

Gom vào menu `⚙` thì hàng **luôn bốn cột**: `[đại lượng ⚙] [phép] [lượng] [đơn vị]`.

Không mất thông tin: **thẻ trên canvas vẫn ghi đủ** `ATR(M5, 14) < nguong_nen_bps = 7 bps
của giá` mà không phải bấm gì. Sơ đồ được **đọc** ở canvas, hộp thoại chỉ để **sửa**. Và
`method` (SMA/EMA) là chuyện riêng của MA — để mỗi chỉ báo giữ núm vặn của chính nó thì
hàng ở ngoài mới generic được.

**Bảng này KHÔNG bắt buộc.** Gõ thẳng `7` vào ô là hợp lệ, và với một con số dùng đúng
một chỗ thì gõ thẳng còn **rõ hơn** — bắt khai `nguong = 7` trước rồi mới được dùng chỉ
là một vòng thừa. Hai màn hình "gõ số 7" và "chọn tham số bằng 7" trông y hệt nhau; nếu
đó là toàn bộ lợi ích thì bảng tham số không đáng tồn tại.

Nó đáng tồn tại vì **một** lý do: khi cùng một con số nằm ở **hai nơi**. Sửa một chỗ
quên chỗ kia thì chiến lược lệch **âm thầm** — không lỗi, không báo, chỉ là kết quả
backtest khác đi mà không ai biết vì sao. Sơ đồ mẫu trước đây có **4 hằng số viết cứng
hai lần**, trong đó `7.0` nằm ở **cả hai sơ đồ**: Entry hỏi *"còn nén không"*, Manage
hỏi *"nén tan chưa"*.

Nên chỗ duy nhất ép người dùng nghĩ tới bảng tham số là **dòng cảnh báo** —
`core._soat_so_lap`:

> ▲ Số 7 được gõ tay ở 2 chỗ, cùng là ngưỡng so với ATR (bps của giá). Sửa một chỗ mà
> quên chỗ kia thì chiến lược lệch âm thầm. **[ Đặt tên cho số này ]**

Nút thay số bằng tên ở **cả hai chỗ** cùng lúc và thêm dòng vào bảng. Để lại một chỗ gõ
tay thì cảnh báo biến mất mà cái bẫy vẫn còn — và lần này còn khó thấy hơn.

**Gom nhóm theo `(VAI, ĐƠN VỊ, GIÁ TRỊ)`, không chỉ theo giá trị.** `chu_ky_atr = 14`
và `chu_ky_ma = 14` bằng nhau chỉ vì **trùng hợp**; gộp lại là đặt tên sai, và sau này
đổi một cái sẽ kéo theo cái kia. Tương tự `SL = 1.5 × ATR zone` và `TP = 1.5 R`. Trùng
số không phải là quan hệ.

Python trả kèm `dat_ten.cho` — **đường dẫn tới đúng từng ô số**. Giao diện chỉ đi theo
đường dẫn mà thay, cố ý **không quét lại sơ đồ**: hai đoạn mã quét cùng một thứ là hai
luật, và sớm muộn chúng sẽ lệch nhau. `tests/test_dat_ten.py` chứng minh đường dẫn đúng
bằng cách chạy backtest trước và sau khi đặt tên — kết quả phải **giống hệt**.

Đụng tên thì phân hai ca: **cùng giá trị → dùng lại** dòng đã có (`chu_ky_atr` engine
luôn đòi phải có, đẻ thêm `chu_ky_atr_2 = 14` chính là thứ rác đang dọn); **khác giá
trị → thêm hậu tố**, vì đè lên là âm thầm đổi một thứ người dùng không hỏi.

```jsonc
"tham_so": [
  {"ten": "nguong_nen_bps", "nhan": "Ngưỡng nén", "gia_tri": 7.0, "don_vi": "bps"},
  …
]
// rồi khối gọi bằng TÊN — cùng chỗ, cùng hình dạng với một con số:
{"trai": {"ten": "atr", "tf": "M5", "period": "chu_ky_atr"},
 "phep": "<", "phai": {"value": "nguong_nen_bps", "tinh": "bps"}}
```

⚠ `tinh` trong `phai` mới là thứ **bộ chạy quy đổi** — đơn vị nằm ở CHỖ DÙNG. Còn
`don_vi` trong bảng tham số là một **khoá** (`NHAN_DON_VI`) quyết định tham số ấy được
mời vào ô nào, và khi bạn chọn nó thì `tinh` bị **khoá** theo nó. Hai thứ luôn khớp —
soát tĩnh báo lỗi nếu lệch. (Trước đây cột đó là chữ tự do chỉ để đọc; xem §6.4.)

**Hiển thị có phân biệt, và đó là chủ ý:**

| Chỗ | Hiện gì | Vì sao |
|---|---|---|
| Vế phải điều kiện · khoảng cách · lot | `nguong_nen_bps = 7` | đây là **núm vặn** — tên nói ý nghĩa, số nói thực tế |
| Tham số của toán hạng (chu kỳ, nến) | `ATR(M5, 14)` | đây là **"đọc chuỗi số nào"**, không phải thứ người ta tinh chỉnh |

Soát tự động bắt ba chuyện: tham chiếu tới tham số **không tồn tại** → lỗi; tham số
khai ra mà **không khối nào dùng** → cảnh báo; và **số gõ tay hai chỗ cùng vai** →
cảnh báo kèm nút đặt tên.

Bộ mặc định lấy thẳng từ `kho/engine_d02.py::THAM_SO_MAC_DINH` — cùng một nguồn với
mặc định của EA, nên không có chuyện tài liệu nói một đằng mẫu chạy một nẻo.

---

## 7. Chiến lược mẫu — Compress EA, dịch sang sơ đồ

### 7.1 Ý tưởng một câu

> Biến động co lại như lò xo nén → đặt sẵn **lệnh chờ stop** ngay mép vùng → giá phá ra là khớp.
> **Mọi khoảng cách đều là bội của ATR hoặc của R, không bao giờ là pip/đô cố định**
> → tín hiệu mang **cùng một ý nghĩa** trên vàng, forex, crypto, chỉ số.

### 7.2 Bốn bước

| # | Việc | Công thức |
|---|---|---|
| 1 · **Phát hiện** | Đọc ATR ở **nến đã đóng `[1]`**, chuẩn hoá ra bps | `atr_bps = ATR/Close × 10000` · nén khi `atr_bps < N` |
| 2 · **Xác nhận** | Đếm **K** nến nén liên tiếp, và vùng chúng tạo ra không rộng quá | `bar_count ≥ K` **và** `zone_range/ATR ≤ Range_Max_ATR` |
| 3 · **Vũ trang** | MA khung lớn quyết hướng, đặt lệnh chờ ngoài mép vùng | xem §7.3 |
| 4 · **Quản lý** | Khớp → khoá tín hiệu. Lãi đủ `BE_RR × R` → dời SL về hoà vốn | |

### 7.3 Hình học vào lệnh

```
buf     = Entry_Buffer_ATR × ATR(hiện tại)        ← lá chắn chống phá giả
R       = SL_ATR_Avg       × ATR(trung bình vùng)  ← khoảng cách SL = 1R

MUA  STOP : entry = đỉnh_vùng + buf ,  SL = entry − R ,  TP = entry + RR × R
BÁN  STOP : entry = đáy_vùng  − buf ,  SL = entry + R ,  TP = entry − RR × R
```

**Hai ATR làm hai việc khác nhau, cố ý:**
- `ATR(hiện tại)` → **đệm vào lệnh**, lọc phá giả một nhịp.
- `ATR(trung bình cả đợt nén)` → **kích thước rủi ro**, để mỗi lệnh rủi ro một `R` tương đương
  bất kể vùng rộng hẹp ra sao.

> ⚠ SL là `SL_ATR_Avg × ATR_avg` — **KHÔNG phải mép vùng bên kia** (tài liệu cũ ghi sai).

### 7.4 Luật hướng

- `MUA` chỉ khi `Close > MA` trên khung Trend **và** `Allow_Buy`.
- `BÁN` chỉ khi `Close < MA` trên khung Trend **và** `Allow_Sell`.
- Bật cả hai thì **MUA được xét trước** → mỗi đợt nén chỉ ra đúng một hướng.
- `Close == MA` → `TREND_SIDEWAY` → **không vào lệnh nào cả**.

### 7.5 Máy trạng thái nén

| Trạng thái | Nghĩa |
|---|---|
| `IDLE` | Biến động bình thường (`ATR ≥ N`). Chờ đợt nén mới. |
| `COUNTING` | Đang đếm nến nén tới **K**. |
| `CONFIRMED` | Đủ **K** nến **và** vùng vừa khổ → sẵn sàng vũ trang. |
| `PENDING` | Lệnh chờ đang sống. **Vùng bị đóng băng** — đỉnh/đáy không đổi nữa. |
| `CONSUMED` | Lệnh đã khớp. Khoá chu kỳ mới **cho tới khi `ATR ≥ N` trở lại** → một lò xo chỉ giao dịch một lần. |

`ATR ≥ N` khi đang `COUNTING` / `CONFIRMED` / `PENDING` → đợt nén **tan** → về `IDLE` và **huỷ lệnh chờ**.

> Máy trạng thái này tồn tại để trả lời đúng một câu hỏi tinh tế:
> *làm sao một đợt nén chỉ đẻ ra đúng một lệnh, chứ không bắn lại mỗi tick khi giá vẫn còn im?*

### 7.6 Tham số (mặc định code · giá trị XAU)

| Input | Code | XAU | Nghĩa | Tinh chỉnh? |
|---|---|---|---|---|
| `ATR_Period` | 14 | 42 | Cửa sổ ATR | ❌ cấu trúc lõi |
| `ATR_Threshold_Bps` | 7.0 | 8 | Ngưỡng nén `N` (bps). **Nhỏ hơn ⇒ chặt hơn ⇒ ít nhưng chất** | ✅✅ chính |
| `Comp_Bars` | 10 | 15 | Số nến nén liên tiếp `K` | ✅✅ chính |
| `Entry_Buffer_ATR` | 0.10 | 0.15 | Đệm vào lệnh (× ATR hiện tại) | ✅ |
| `Range_Max_ATR` | 4.0 | 6 | Loại vùng rộng quá (× ATR) — **luôn bật, không tắt được** | ✅ |
| `Trend_TF` / `MA_Period` / `MA_Method` | M15 / 50 / SMA | M30 / 200 / EMA | Bộ lọc xu hướng | ✅ vừa |
| `RR_Ratio` | 2.0 | 4.5 | TP = × R | ✅ |
| `SL_ATR_Avg` | 1.5 | 7 | SL = × ATR trung bình. **Định nghĩa 1R** | ✅ |
| `BE_Enabled` / `BE_RR_Trigger` | true / 1.0 | true / 3 | Dời SL về hoà vốn khi lãi × R | ✅ |
| `Fixed_Lot` | 0.01 | 0.01 | Khối lượng cố định | ❌ **không bao giờ tối ưu** |
| `Max_Positions` | 0 | 3 | Trần lệnh mở đồng thời (0 = vô hạn) | ❌ |

### 7.7 Những thứ EA **KHÔNG** có — đừng mô hình hoá thừa

Trailing stop · đóng một phần · lệnh chờ hết hạn theo thời gian · lọc phiên/giờ · lọc spread ·
lọc tin · sizing theo % vốn · martingale · sửa lệnh chờ sau khi đặt.

### 7.8 Lỗi có thật trong EA — biết để không chép theo

- `CalcLot(entry, sl)` **bỏ qua cả hai tham số**, luôn trả `fixed_lot`.
- `IsTrendOk()` **không kiểm** `ma_trend.result` — trước khi nến Trend đầu tiên đóng, trạng thái là
  `SIDEWAY` (=0) nên chặn cả hai hướng. Vô tình thành cổng khởi động, nhưng là **ngẫu nhiên chứ không cố ý**.
- `CheckPendingActivation()` khớp **bất kỳ** vị thế nào cùng symbol+magic → lệnh chờ bị huỷ từ bên ngoài
  trong lúc đang có lệnh khác mở sẽ bị **đọc nhầm là đã khớp**.
- Giá entry/SL/TP **không** `NormalizeDouble`, **không** kiểm `stops_level`/`freeze_level`, không trừ spread.
- `ChartView.mqh` là **code chết** — tham chiếu struct `STradeState` không tồn tại, biên dịch sẽ hỏng.
- **Bề rộng vùng chỉ được kiểm ĐÚNG MỘT LẦN** lúc chuyển `COUNTING`→`CONFIRMED`. Đã `CONFIRMED`
  rồi thì vùng vẫn nới rộng mỗi nến mà không bị kiểm lại — nên khi `Max_Positions` hoặc `SIDEWAY`
  chặn, entry của nến sau trôi ra xa và lệnh vẫn được đặt dù vùng đã rộng hơn `Range_Max_ATR`.
  Phép kiểm nằm lọt trong nhánh `cur == COMP_COUNTING` nên trông giống sơ suất hơn là chủ ý.
  **Ta không chép** — xem §12.6.

---

## 8. Giao diện — chép nguyên, chỉ đổi nhãn

### 8.1 Bảng màu (`theme.css`) — **giữ y hệt**

Accent `#ffa657` là **cam**, trùng luôn màu logo mèo → không phải đổi gì.

```css
--bg / --chrome : #202020   /* = ĐÚNG màu thanh tiêu đề Windows, đã lấy mẫu pixel */
--surface       : #2b2b2b   /* bề mặt đồ vật nổi: hộp trên canvas, hộp thoại */
--field         : #2d2d2d
--raised        : #383838      --raised-hover : #454545
--border        : #3f3f3f      --border-soft  : #353535
--text          : #e8e8e8      --muted : #9a9a9a      --dim : #7a7a7a
--ok   : #4ec96a   --err : #e5534b   --warn : #d9a441
--accent: #ffa657  --accent-soft : rgba(255,166,87,.16)
--loop : #ffa657   --group : #6cb6ff   --action : #a8a8a8
--canvas-bg : #1a1a1a   --canvas-dot : #333333
--radius : 8px   --radius-sm : 6px
--font : "Segoe UI", system-ui, sans-serif      --mono : Consolas, "Cascadia Mono", monospace
```

Cat_Studio thêm: `--start: #4ec96a` (khối Bắt đầu) · `--ghim: #d9a441` (khối ghim số) ·
`--day-quay-lai: #d9a441` nét đứt (cạnh quay lại).

### 8.2 Canvas

- **React Flow (`@xyflow/react`)**, `ConnectionMode.Loose`.
- Mỗi khối có **4 cổng ở giữa 4 cạnh**, mỗi cạnh phải có **cả `source` lẫn `target`**.
  Chỉ đặt `source` thì kéo nối vẫn được nhưng React Flow không phân giải nổi đầu **đích** của một
  đường nối đã có → vẽ ra mấy mẩu cụt bên cạnh hộp. Cái `target` trùng id, trùng vị trí,
  `opacity: 0` + `pointerEvents: none` — nó chỉ cần **tồn tại** để đường nối bám vào.
- Đường nối: **bezier** (`type: 'default'`). Cố ý **không** `smoothstep` — hộp cao thấp khác nhau nên
  hai đầu hiếm khi cùng độ cao, đường bậc thang gãy khúc trông như lỗi vẽ.
- Mũi tên `ArrowClosed` 10×10 `#6a6a6a`. To hơn thì nó nặng hơn cả cái cổng nó cắm vào.
- Mặc định nối **phải → trái** (luồng chạy trái sang phải).
- **Double-click lên dây = huỷ kết nối** (cùng quy ước với khối: nhấp đúp lên thứ gì thì tác động lên chính nó).
- **Ngắt hết kết nối** của một khối = cách "tắt tạm" nó mà vẫn giữ trên canvas — huy hiệu về `–`,
  panel Vấn đề báo "không bao giờ chạy tới". Không cần thêm cờ bật/tắt riêng.

### 8.3 Ribbon (kiểu Paint: nhãn nhóm nằm **dưới**)

| Nhóm | Auto_Clicker | → Cat_Studio |
|---|---|---|
| **Thêm khối** | Loop · Nhóm · HĐ lẻ · Rẽ nhánh · Delay | **Kiểm tra ĐK** + (**Vào lệnh** ở Entry / **Sửa lệnh** ở Manage) |
| **Template** | Lưu ▾ (Process/Loop/Nhóm) · Mở ▾ | Lưu ▾ · Mở ▾ — **chỉ cả chiến lược**, không lưu cụm khối rời |
| **Sửa** | Sửa · Nhân bản · Xoá | *(y hệt)* |
| **Luồng** | Đặt số ① · Xem điểm | Đặt số ① · **Ghim số ⟲** · Vừa khung |
| **Hoàn tác** | Hoàn tác · Làm lại | *(y hệt)* |
| **Template** | Lưu ▾ · Mở ▾ | *(y hệt)* |
| *(mép phải)* | Tên Process · Chờ Ns · ▶ Chạy / ■ Dừng | Tên chiến lược · Symbol · TF · **▶ Chạy → Strategy Tester** |

### 8.4 Menu chuột phải

Hỗ trợ sẵn: menu con (`con`), vạch ngăn (`ngan`), mục mờ **kèm lý do** (`tat` + `viSao`).
> Mục bị tắt vẫn **HIỆN** kèm lý do — giấu đi thì người dùng tưởng tính năng không tồn tại.
> Mờ mà không nói vì sao là bực nhất.

| Bấm phải vào | Mục |
|---|---|
| **Nền** | Dán · ─ · Thêm Kiểm tra ĐK + (Vào lệnh **hoặc** Sửa lệnh, theo tab) |
| **Khối** | Sửa · Đổi tên… · ─ · **Ghim số ⟲** 🆕 · Nối tới ▸ · Ngắt hết kết nối · ─ · Chép · Dán · Nhân bản · ─ · Xoá |
| **Dây** | Xoá kết nối |

Khối **Bắt đầu** làm mờ đúng những mục vô nghĩa với nó (Sửa, Ghim, Nhân bản, Xoá) —
**kèm lý do**, không im lặng.

Menu **"Nối tới ▸"** liệt kê mọi khối còn lại **sắp theo nhãn** (`1`, `1A`, `1A.1`, `2`…) → thứ tự đọc
trong menu trùng thứ tự chạy trên canvas. **Cố ý KHÔNG loại khối tạo thành vòng.**

Mục menu **dựng lúc render**, không nhét sẵn vào state: mục menu là closure đọc `nodes`/`edges`/`dangChon`;
đóng băng chúng lúc bấm phải sẽ khiến "Chép" chép nhầm cái đang chọn **trước đó**.

**Bấm phải vào khối phải CHỌN khối đó trước** — trừ khi nó đã nằm trong nhóm đang chọn (người dùng
cố ý chọn nhiều rồi mới bấm phải, phá nhóm đi là làm hỏng ý định của họ).

### 8.5 Phím tắt

`Ctrl+Z` hoàn tác · `Ctrl+Y` làm lại · `Ctrl+D` nhân bản · `Ctrl+C`/`Ctrl+V` chép/dán khối ·
`Ctrl+S` lưu · **`Ctrl+Shift+S` lưu thành…** · **`Ctrl+G` ghim số** · `Delete` xoá · `F2` đổi tên.

**Cửa sổ Tester: `Space` = phát / dừng · `←` `→` = lùi / tới một nến.** Phím quen của mọi trình phát, và ở đó tay đang
cầm chuột để rê crosshair nên với sang nút ▶ là mất chỗ đang chỉ. Ba chỗ phải né, không
né thì phím này phá nhiều hơn nó giúp — và **`tsc` không bắt được cái nào**:

| né gì | vì sao |
|---|---|
| `INPUT` · `TEXTAREA` · `SELECT` · `contentEditable` | Space trong ô nhập là ký tự / là bật tắt. Bắt theo **THẺ** đang có tiêu điểm chứ không theo danh sách id — thêm ô mới sau này là tự động được bảo vệ |
| `BUTTON` đang có tiêu điểm | trình duyệt vốn đã bắn `click` khi nhấn Space trên `<button>`; vừa bấm ▶ bằng chuột xong thì nút GIỮ tiêu điểm → Space toggle **hai lần** → trông như phím chết |
| `preventDefault` cho phần còn lại | Space mặc định là **cuộn trang**, mà bảng nhật ký cuộn được — không chặn thì mỗi lần dừng phát màn hình lại nhảy |

⚠ `preventDefault` phải đứng **SAU** mọi phép né, không phải đầu hàm — chặn sớm là nuốt
luôn Space của ô nhập. Và phím tắt **chết ở đúng chỗ cái nút chết** (`if (!kq) return`,
đúng lúc nút ▶ đang `disabled`); nếu không nó là một cửa sau.

**GIỮ PHÍM đã có sẵn, không cần hẹn giờ.** Trình duyệt tự bắn lại `keydown` (`ev.repeat`)
theo nhịp lặp của hệ điều hành, nên `←` `→` giữ là đi liên tiếp. Nhưng **Space phải BỎ
nhịp lặp**: giữ Space mà toggle ~30 lần/giây thì phát/dừng nhấp nháy, thả tay ra không
đoán nổi nó đang ở trạng thái nào.

⚠ **TỚI và LÙI không đối xứng về GIÁ**, dù trên thanh công cụ là hai nút giống nhau.
`nhip()` đọc khung hình kế **từ lô đã nạp** — không hỏi Python câu nào. Còn lùi phải
`veDau()`: **hai** lời gọi cầu nối (`test_doan` + `test_nen_tf`) và dựng lại chart. Giữ
`←` ở nhịp lặp bàn phím là ~60 lời gọi/giây qua một cầu nối **đồng bộ, mã hoá payload hai
lần** (§12.16) — chắc chắn nghẽn.

→ Lùi có **khoá**: đang lùi thì **bỏ** nhịp lặp mới, và nhả khoá trong `finally` (lùi
hỏng một lần không được khoá chết vĩnh viễn). Giữ phím vẫn lùi liên tục, chỉ theo nhịp
cầu nối trả lời được. **Bỏ** nhịp thừa đúng hơn **xếp hàng** chúng — xếp hàng thì thả tay
rồi màn hình còn chạy tiếp.

Nút ◀ ▶ và phím tắt gọi **cùng một hàm** (`lui` / `tien`), đúng luật §12.22.
`tests/test_giao_dien.py` canh cả 11 điều trên, kể cả **thứ tự** `preventDefault`.

#### 8.5a ✅ LƯU — cơ chế của Word, và một trạng thái mới để có nó

Trước đây `Ctrl+S` **lúc nào cũng hỏi tên**, kể cả một chiến lược đã lưu hai mươi lần.
Người dùng yêu cầu đúng nếp Word:

| | điều kiện | làm gì |
|---|---|---|
| `Ctrl+S` | tài liệu **đã có chỗ trên đĩa** | ghi đè, **không hỏi gì** |
| `Ctrl+S` | tài liệu **mới tinh** | hoá thành *Lưu thành…* |
| `Ctrl+Shift+S` | luôn luôn | hỏi tên → template mới, bản đang mở **chuyển sang** tên đó |

**Thứ phải thêm là một TRẠNG THÁI, không phải một cái nút:** `tenTrenDia` — tên template
mà tài liệu đang nằm dưới, `null` là chưa có nhà. Đây chính là *"đường dẫn file"* của Word.

⚠ **Không suy ra được từ `ten`**: sơ đồ mới tinh cũng đã có sẵn tên `"Chiến lược 1"`.
⚠ **Và không được dò kho để đoán** (`ten` có trong `list_templates()` chưa) — một sơ đồ
mới trùng tên với template cũ sẽ **lặng lẽ đè mất nó**.

`nap(doc, loi, nha)` bắt buộc truyền `nha`, **không cho mặc định**: mỗi lần nạp một tài
liệu là một lần phải trả lời *"cái này có nhà chưa"*. Để mặc định thì chỗ quên sẽ im lặng
thừa hưởng nhà của tài liệu trước, và `Ctrl+S` đè lên một template chẳng liên quan.
`tsc` bắt được mọi chỗ quên — đó là lý do bắt buộc thay vì tuỳ chọn.

| Nạp từ đâu | `nha` | vì sao |
|---|---|---|
| mở một template | tên template | đúng chỗ nó đang nằm |
| vừa lưu xong | tên vừa lưu | |
| `File → Mới` · sơ đồ mẫu | `null` | sơ đồ mẫu do Python **sinh ra**, không nằm trong kho |
| `Mở từ file khác…` | `null` | file ngoài kho, mà `save_process` chỉ biết ghi **vào** kho |

**Ghi theo tên ĐANG HIỆN trong ô ribbon, không theo `tenTrenDia`.** Ô đó sửa được và nhìn
thấy được, nên sửa xong mà `Ctrl+S` vẫn đè lên tên cũ là ô tên nói dối. Sửa tên rồi
`Ctrl+S` ⇒ ra một template mới, bản cũ còn nguyên.

⚠ **`Ctrl+Shift+S` gõ trúng tên đã có thì PHẢI hỏi.** `save_process` ghi đè không nói một
lời, mà đây là cửa duy nhất người dùng tự tay gõ ra một cái tên — gõ trùng là chuyện thường.

⚠ **Thứ tự hai nhánh phím tắt là thứ `tsc` KHÔNG bắt được.** Chuỗi `else if` xét lần lượt,
mà nhánh `Ctrl+S` trần khớp cả khi Shift đang giữ. Để nó đứng trước thì `Ctrl+Shift+S`
không bao giờ tới lượt — *Lưu thành* lặng lẽ hoá thành *Lưu*, **ghi đè luôn bản gốc thay
vì tạo bản sao**, và chỉ lộ ra khi bản gốc đã mất. `tests/test_giao_dien.py` canh đúng
thứ tự đó bằng cách so vị trí hai chuỗi trong `App.tsx`.
Hộp thoại đang mở (`.lop-phu` tồn tại) thì phím tắt canvas **phải im** — nếu không, `Delete` trong hộp
thoại vừa xoá hành động vừa xoá luôn cả khối phía sau.

### 8.6 Undo

Chụp **ảnh nguyên khối** (`{nodes, edges, ten}`), không tính diff — tài liệu chỉ vài chục KB, mà diff sai
thì undo hỏng theo kiểu rất khó tìm. Tối đa **60** bước.
Kéo khối: chụp **một lần** lúc bắt đầu kéo, không phải mỗi frame — nếu không một cú kéo tạo 60 bước undo
và `Ctrl+Z` thành vô dụng.

---

## 9. Định dạng file

```jsonc
{
  "schema": 3,
  "type": "strategy",
  "name": "Compress",
  "symbol": "XAUUSD",
  "timeframe": "M5",

  // Hằng số CÓ TÊN — khối gọi bằng tên, không gõ số hai nơi.
  "tham_so": [
    {"ten": "nguong_nen_bps", "nhan": "Ngưỡng nén", "gia_tri": 7.0,
     "don_vi": "bps", "ghi_chu": "Nhỏ hơn ⇒ nén chặt hơn ⇒ ít nhưng chất."}
  ],

  // HAI sơ đồ. File schema 1/2 mở ra vẫn được — `steps` ở gốc nhận làm `entry`.
  "entry":  { "steps": [ … ], "edges": [ … ] },
  "manage": { "steps": [ … ], "edges": [ … ] }
}

// một khối trông thế này:
{ "kind": "action", "id": "s…", "type": "check_cond", "pos": [400, 120],
  "conditions": [
    { "trai": {"ten": "atr", "tf": "M5", "period": "chu_ky_atr"},
      "phep": "<", "phai": {"value": "nguong_nen_bps", "tinh": "bps"} }
  ] }
```

- **`id` bền, nhãn KHÔNG lưu.** Nhãn là hàm thuần của `(steps, edges)` → tính lại mỗi lần mở.
- `from_side`/`to_side` thuần thị giác **nhưng phải lưu** — không thì mở lại file là sơ đồ tự vẽ khác đi.
- **Không có `edges`** ≡ **chuỗi thẳng `1→2→3`** (`default_edges`) → file cũ mở ra vẫn đúng, không phải di cư.
- `clean_edges` bỏ dây trỏ tới khối đã xoá và bỏ trùng — **không tự ý sửa ý người dùng thành thứ khác.**

---

## 10. Môi trường

| | |
|---|---|
| Python | 3.14.2 |
| Node | v20.19.0 · npm 10.8.2 |
| MetaTrader5 (pip) | 5.0.5735 ✔ đã có |
| Cần thêm | `pywebview` — xem ghi chú ngay dưới bảng |
| **Bỏ** so với Auto_Clicker | `pyautogui`, `keyboard`, `pyperclip`, `pillow`, toàn bộ `winrt-*` (OCR), `overlay_ui.py`, `overlays.py`, `update_mods.py`, `data/mods_*.txt` |
| Máy | Windows 10 Pro 19045 — cần .NET ≥ 4.7.2 và WebView2 Runtime |
| WebView2 (đo được) | **151.0.4129.72 → Chromium 151**. Đáng ghi vì nó quyết định dùng được tính năng CSS nào; đừng đoán là bản cũ rồi tự né. |

**✅ `quantconnect-stubs` không còn giết pywebview nữa.** Gói đó ship một thư mục `Microsoft/` ở
`site-packages`, mà pywebview (backend WinForms) cần `Microsoft.Win32.SystemEvents` — một
**namespace .NET**. pythonnet gắn bộ tìm của nó vào **cuối** `sys.meta_path`, tức sau bộ tìm đọc
`site-packages`, nên gói Python cướp mất tên và app chết ngay lúc mở cửa sổ với
`FileNotFoundException: Could not load … 'Microsoft'` — một câu **không liên quan gì tới lỗi
thật**. Trước đây phải né bằng một `.venv` riêng; giờ `app_web._uu_tien_namespace_dotnet()` đẩy
`DotNetFinder` lên đầu `meta_path` **trước** `import webview`. Bộ tìm đó chỉ nhận namespace .NET
có thật nên không nuốt nhầm gói Python nào.

---

## 11. Kế hoạch

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| **P0 · Khung** | Fork Auto_Clicker → Cat_studio, gỡ sạch phần game/OCR/overlay. Đổi logo + tiêu đề. | ✅ `python app_web.py` mở cửa sổ Cat Studio |
| **P1 · Đồ thị** | `core.py`: khối/cạnh, `flow_map`, `flow_order`, `diem_gop`, soát lỗi — kèm sửa Bẫy 1, 3, 4 | ✅ 41/41 test |
| **P2 · Số 🆕** | Khối `start` + cờ `ghim` + cạnh quay lại + huy hiệu ⟲ + menu chuột phải + `Ctrl+G` | ✅ vẽ vòng lặp không còn cảnh báo sai |
| **P3 · Hành động** | 3 hành động. 32 toán hạng / 6 nhóm, 9 phép so (ký hiệu), 7 chế độ Sửa lệnh. | ✅ |
| **P4 · Canvas** | React Flow, ribbon, **pill Entry/Manage**, undo 60 bước (gom cả hai tab), template, chép/dán, phím tắt | ✅ |
| **P4b · Kho + lưu trữ** | `kho/` chia theo engine · `so_lenh.py` id của ta · `du_lieu/` · bảng tham số · hộp thoại **Kho** (menu File) | ✅ |
| **P6 · Mẫu** | Sơ đồ mẫu Compress EA, khớp §7 | ✅ **Entry 7 khối · Manage 5 khối · KHÔNG một mũi tên ngược**, soát sạch |
| **P5 · Tester** | Cửa sổ Strategy Tester — thiết kế đầy đủ ở **§12** | ✅ phát lại · nhật ký ảo hoá · thống kê · lịch sử lần chạy |
| **P7 · Bộ chạy** | `nguon_nen` → `tinh_toan` → `khop_lenh` → `bo_chay`. Nối MT5, kéo nến M1, backtest thật | ✅ **2,9 s cho 354.503 nến M1**, `nen_mo_ho = 0` (§12.13e) |
| **P8 · Live 🆕** | Nối sàn thật: vòi cấp nến · sức khoẻ kết nối · tầng phòng vệ · hiệu chuẩn — **§14** | ✅ chế độ **QUAN SÁT**. Luồng đặt lệnh chưa nối (§14.14) |
| **P9 · Đóng gói** | `tools\dong_goi.bat` — PyInstaller `onedir`, chạy bộ kiểm trước khi gói | ✅ 66 MB · chạy trên máy trắng ra **trùng từng con số** (§13.1) |

### Sơ đồ mẫu ra đúng thế này

**Tab ENTRY** — 7 khối
```
[1] Mỗi nến M5 — tìm tín hiệu
[2] Vùng nén đã xác nhận?
        atr_bps < 7 · số nến nén ≥ 10 · rộng vùng ÷ ATR ≤ 4 · KHÔNG vùng này đã sinh lệnh
[3] Còn chỗ cho lệnh mới?
        số lệnh chờ = 0 · số vị thế < 3
      ├─[3A] Xu hướng LÊN?   (close M15 nến[1] > MA M15 50) → [3A.1] Buy Stop trên đỉnh vùng
      └─[3B] Xu hướng XUỐNG? (close M15 nến[1] < MA M15 50) → [3B.1] Sell Stop dưới đáy vùng
```

**Tab MANAGE** — 5 khối, chạy một lượt cho MỖI lệnh đang sống.
Nhịp **M1** chứ không phải M5 — xem §12.4 (hoà vốn của bản gốc chạy mỗi tick).
```
[1] Mỗi nến M1 — với TỪNG lệnh đang sống
      ├─[1A] Chưa khớp mà nén đã tan?          → [1A.1] Huỷ lệnh chờ
      │         KHÔNG lệnh này đã khớp · atr_bps ≥ 7
      └─[1B] Đã khớp, đủ 1R, SL chưa hoà vốn?  → [1B.1] Dời SL về giá vào
                lệnh này đã khớp · KHÔNG SL đã ở hoà vốn · lãi (×R) ≥ 1
```

Bốn chỗ dễ làm sai, ghi lại để khỏi trượt về:

1. **`ManageBreakEven` = MỘT cổng + MỘT hành động, không tách "ĐK đạt 1R" thành khối
   riêng trên đường chính.** Tách ra là sai hành vi: chưa đủ 1R sẽ chặn luôn phần sau.
   Ba dòng guard của bản gốc (`entry>0 && tp>0`, `sl >= entry`, `bid < trigger`) gói
   đúng vào cổng `[1B]`.
2. **Vế "SL chưa ở hoà vốn" KHÔNG được thiếu.** Manage chạy lại mỗi nến, thiếu nó thì
   lệnh sửa SL bắn lại hoài.
3. **`COMP_CONSUMED` không cần khối** — `KHÔNG vùng này đã sinh lệnh` là một phép tra
   bảng trên `vùng_id` của các lệnh.
4. **`< Max_Positions` chứ không phải `≤`** — bản gốc `if(pos_count >= max) skip`.
   Bằng nhau là đã đầy.

---

## 12. ⭐⭐ STRATEGY TESTER — thiết kế đã chốt

> Chốt ngày 2026-08-10 sau một đợt đọc lại toàn bộ `core.py` / `api.py` / `kho/` và cả 6 file
> MQL5 của D_02. Mười một quyết định dưới đây **quyết định kết quả backtest**, không phải chi
> tiết kỹ thuật. Sửa sau là vứt sạch mọi kết quả đã chạy — nên ghi lại kèm lý do ở đây.

### 12.0 Một câu

**Tính một lần, đọc mãi mãi.** Chạy hết backtest một lượt, sinh ra một dòng thời gian bất
biến; giao diện chỉ là đầu đọc trượt trên đó. Tua lại = dời con trỏ, không có cơ chế thứ hai.

### 12.1 ⭐ HAI ĐỒNG HỒ

| Đồng hồ | Là gì | Nhịp |
|---|---|---|
| **M1** | đồng hồ của **thị trường** — giá đi tới đâu, lệnh khớp lúc nào | mỗi nến M1 |
| **M5** | đồng hồ của **chiến lược** — bao lâu thức dậy nhìn một lần | mỗi nến M5 |

Bộ mô phỏng bước từng nến M1: cập nhật giá → xét lệnh chờ có khớp không → xét SL/TP có bị
chạm không. Chỉ khi nến M1 đóng đúng biên M5 thì process mới chạy một vòng.

**Vì sao tách:** nhìn lén tương lai bị chặn bởi *cấu trúc* chứ không bởi sự cẩn thận. Process
chỉ được gọi lúc M5 khép, và tại đó nến M5 vừa đóng là nến mới nhất nó thấy. MA M15 chỉ đổi
giá trị khi biên M15 khép — ba lần một giờ, không phải mỗi lần process chạy. Đúng bản gốc:
`FilterEngine.mqh:316-318` chỉ tính lại MA khi có nến Trend TF mới.

**Chỉ tải MỘT bộ dữ liệu.** M5, M15, H1 gộp từ M1.

### 12.2 ⭐ ĐƯỜNG ĐI 4 ĐIỂM trong một nến M1

Đừng xử lý SL/TP như trường hợp đặc biệt. Biến mỗi nến M1 thành một đường đi rồi bước qua nó:

| Nến | Đường đi |
|---|---|
| C ≥ O (tăng) | O → **L** → **H** → C |
| C < O (giảm) | O → **H** → **L** → C |

Giá nhúng xuống trước rồi mới đẩy lên, hoặc ngược lại — suy từ chính chiều của nến. Trùng
cách MT5 sinh tick ở chế độ "1 minute OHLC", nên số của ta so được với Strategy Tester của MT5.

Rồi mọi thứ còn lại thành **một luật duy nhất**: *"giá chạm mức X ở bước thứ k của đường đi"*.
Lệnh chờ khớp, SL bị chạm, TP bị chạm — cùng một phép kiểm, chỉ khác mức giá.

Cho không hai ca khó:

- **Nến mở cửa đã nhảy qua mức** → điểm đầu đường đi là O, nên khớp **tại O**, không phải tại
  mức đặt. Đúng bản chất gap cuối tuần của XAUUSD. Chiến lược này *chỉ* dùng lệnh stop nên gap
  qua entry là ca thường gặp, không phải ngoại lệ.
- **Khớp rồi chết ngay trong cùng nến M1** → hai sự kiện ở hai bước liền nhau, tự nhiên.

Không còn "trường hợp SL và TP cùng nến" — đường đi đã trả lời cái nào tới trước. Nhưng khi cả
hai mức nằm trong biên độ một nến M1 thì **nhật ký vẫn ghi một dòng riêng**: không phải để cảnh
báo, mà để **đếm được**. Chạy một năm mà con số đó bằng 0 nghĩa là kết quả không phụ thuộc vào
giả định đường đi — đó là bằng chứng, không phải niềm tin.

### 12.3 Spread · phí · tiền

OHLC là giá **Bid**. Quy mọi mức về Bid **một lần**, rồi vẫn chỉ một đường đi chạy trên Bid:

| Mức | Sàn so với | Quy về Bid |
|---|---|---|
| Mua — giá vào (khớp ở Ask) | Ask | `P − spread` |
| Mua — SL/TP (đóng ở Bid) | Bid | `P` |
| Bán — giá vào (khớp ở Bid) | Bid | `P` |
| Bán — SL/TP (đóng ở Ask) | Ask | `P − spread` |

Chi phí spread vì thế hiện ra **đúng chỗ nó phát sinh** — lúc vào lệnh — chứ không phải một
khoản trừ bịa ra ở cuối.

- `spread`: ô nhập, **mặc định 20 points**. Hiện quy đổi ra USD ngay cạnh ô, vì "20 points" chỉ
  có nghĩa khi biết `point` của symbol (XAUUSD 2 chữ số → 0.20 USD; EURUSD 5 chữ số → 2 pip).
- `commission (USD/lot)`: tính **round-turn**, trừ một lần khi lệnh đóng, nhật ký ghi thành dòng riêng.
- `deposit` / `margin (1:…)`: **chỉ để hiển thị** một cột trong bảng phải. Không chặn lệnh, không
  stop-out — với lot 0.01 thì chặn thật là luật thừa.
- D_02 **hoàn toàn không xử lý spread** (grep `spread` trong toàn EA = 0 kết quả) nhưng sàn thì
  kích hoạt Buy Stop theo Ask trên một mức giá tính từ nến Bid. Spread = 0 cho kết quả lãi hơn
  thực tế **một cách có hệ thống**.

### 12.4 ✅ NHỊP THUỘC VỀ KHỐI BẮT ĐẦU

**Entry nhịp M5 · Manage nhịp M1.**

- Entry là **quyết định** — 5 phút xem một lần là đúng.
- Manage là **phản ứng** — càng nhanh càng đúng, và M1 là nhanh nhất dữ liệu cho phép.

**Vì sao Manage không thể là M5:** `ManageBreakEven()` của D_02 nằm **ngoài mọi guard nến**
(`Compress.mq5:128`), chạy mỗi tick. Một nến M5 quét lên đủ 1R rồi quay đầu về SL: EA thật đã
kịp dời SL nên thoát ~0R, còn ta chạy Manage mỗi M5 thì thoát −1R. Lệch **có hệ thống**, và lệch
về phía bản mô phỏng lỗ nhiều hơn thực tế.

**Nhịp ghi trên khối Bắt đầu, KHÔNG phải dropdown trên ribbon.** Hiện chữ "M5" trên khối là một
cái tên gõ tay (`'Mỗi nến M5 — tìm tín hiệu'`) không nối với `doc.timeframe` bằng gì cả — đổi
dropdown thì khối vẫn ghi M5, sơ đồ nói dối. Đúng lỗi `7.0` viết cứng hai chỗ mà §6.4 đã dọn.

→ Chữ trên khối do Python sinh · bỏ dropdown trên ribbon · đổi tên trường `timeframe` → `nhip`
(giờ có bốn thứ đều gọi là timeframe, để tên chung chung là mời gọi nhầm).

**Đã làm** — `schema` lên **4**: `nhip` là khoá trên chính khối Bắt đầu của từng sơ đồ, không
còn `doc["timeframe"]`. `normalize_process` di cư file cũ (nhịp cũ → Entry, Manage → M1) nên
không cần script riêng. Sửa nhịp bằng chuột phải vào khối → **Nhịp chạy** → chọn khung; hộp đổi
chữ ngay vì `core.dong_khoi` sinh nó từ khoá đó. Bỏ luôn `timeframe` khỏi `cai_dat.json` và
`SettingsDialog` — mặc định giờ nằm ở `core.NHIP_MAC_DINH`, một nguồn sự thật.

Thêm một phép soát: **Manage chạy chậm hơn Entry → cảnh báo.** Lệnh vừa sinh mà phải chờ qua
vài nhịp mới được quản lý thì dời SL và huỷ lệnh chờ đều phản ứng trễ hơn cả lúc vào lệnh.

Hai chỗ suýt sót, ghi lại: `luu_tru.doc_cai_dat` giờ **vứt khoá lạ** — bỏ một cài đặt mà không
vứt thì khoá cũ nằm lại trong file vĩnh viễn và người đọc sau tưởng nó còn tác dụng. Và
`StepNode` trước đây ẩn hẳn thân hộp với khối `start` (`{!laStart && …}`), nên dòng nhịp sinh ra
rồi mà không hiện — điều kiện phải là "có dòng nào không", không phải "có phải khối Bắt đầu không".

| Khung | Là gì | Ở đâu |
|---|---|---|
| M5 / M1 | nhịp sơ đồ thức dậy | **khối Bắt đầu** — sự thật của logic |
| M15 (MA), M5 (ATR) | chỉ báo đọc khung nào | từng điều kiện — tuyệt đối, không dính nhịp |
| M1 | nền mô phỏng | cài đặt Strategy Test |
| M1…D1 trên toolbar | nhìn cho thoáng | chỉ là cách vẽ, không đụng kết quả |

### 12.5 ⭐ LUẬT ĐI TRONG SƠ ĐỒ

Ba luật, phải chốt trước dòng code đầu tiên của bộ chạy.

**a) Cổng trượt thì lùi về đâu.** Không chỗ nào trong đồ thị đánh dấu nhánh "đúng/sai" — cạnh
chỉ có `{from, to, port, from_side, to_side}`, ngữ nghĩa nằm ở *thứ tự* nhánh. Nên:

> Cổng trượt → lùi về **ngã rẽ gần nhất còn nhánh chưa thử**.
> **Trừ khi** lượt này đã chạy `vao_lenh` hoặc `sua_lenh` → **hết lượt ngay**.

Vế sau là chỗ quan trọng: đã bắn lệnh ra thị trường thì không rút lại được, nên không được quay
lui thử nhánh khác — nếu không một lượt Entry đẻ ra hai lệnh, trong khi cổng `số lệnh chờ = 0`
chỉ được hỏi một lần ở đầu lượt. D_02 chốt cứng đúng một lệnh chờ (`TradeManager.mqh:330-334`).

Luật này **không có biệt lệ**: cổng chỉ có một đường ra ([2], [3] của sơ đồ mẫu) mà trượt thì tự
rơi vào "không còn nhánh nào chưa thử → hết lượt".

**b) Cổng LUÔN tính đủ mọi điều kiện, không ngắt ở cái sai đầu tiên.** Ngắt sớm thì nhật ký
*vĩnh viễn* không trả lời được "ba điều kiện kia lúc đó thế nào" — chúng chưa từng được tính.
Mà đó đúng là câu cần khi debug: *"cổng trượt vì ATR, nhưng số nến nén đã tới đâu rồi?"*
Chi phí: vài phép so số thực. Ngoại lệ duy nhất được ngắt là điều kiện **không có nguồn dữ
liệu** — khi đó ghi lý do chứ không ghi số.

**c) Thứ tự nhánh mà mơ hồ thì BÁO LỖI.** `_khoa_nhanh` xếp nhánh theo `(ghim, y, x, id)`; hai
khối trùng `y` và `x` thì phân định bằng **uuid** — thứ người dùng không nhìn thấy và không đổi
được. Kéo một khối lên vài pixel là đổi chiến lược trong khi sơ đồ trông y hệt.

> Hai đầu nhánh của cùng một ngã rẽ lệch nhau **dưới 8 px** → `validate_process` báo **lỗi**.

✅ **Đã làm** — `core.LECH_TOI_THIEU = 8.0`, soát trong `validate_so_do` ngay cạnh luật nhánh mặc
định. Báo **lỗi** chứ không cảnh báo: sửa chỉ tốn một cú kéo, còn để nguyên thì cái sai không bao
giờ lộ ra vì sơ đồ trông vẫn đúng. Cạnh quay lại (trỏ vào khối đã ghim) được miễn — nó luôn xếp
cuối bất kể toạ độ, nên không có gì mơ hồ.

### 12.6 Vùng nén

**a) Kiểm bề rộng MỖI NẾN, không chốt một lần.** D_02 kiểm `rong_vung_atr ≤ 4` đúng một lần lúc
chuyển COUNTING→CONFIRMED (`FilterEngine.mqh:268-291`), sau đó vùng vẫn nới rộng mỗi nến mà
**không bị kiểm lại** (`:249-266`). Nên khi bị Max_Positions / SIDEWAY / đang có lệnh chờ chặn,
vùng cứ phình và nến sau vẫn vào lệnh dù đã rộng 6–7×ATR — entry lúc đó xa hẳn chỗ giá thật sự nén.

Ta kiểm lại mỗi nến ở cổng [2]. **Ra ít lệnh hơn**, và những lệnh mất đi đúng là loại entry đã
trôi xa. Đây là chỗ duy nhất trong danh sách khác biệt thật sự đổi *số lệnh*.

> Lý do chọn bản sạch: bản gốc kiểm một lần rồi cấp cho vùng một **giấy phép vĩnh viễn**, trong
> khi thứ nó cấp phép cho vẫn tiếp tục biến dạng. Cấp phép cho một trạng thái rồi để trạng thái
> đó tự do đổi là mâu thuẫn. Bản của ta không có giấy phép nào: điều kiện đúng ở thời điểm nào
> thì vào lệnh ở thời điểm đó, không có trạng thái ẩn nào phải nhớ.
> Khớp 100% thì phải thêm một toán hạng `vung_da_xac_nhan` — tức mang trở lại đúng cái máy trạng
> thái 5 giá trị mà §7.5 đã cố tình bỏ đi.

**b) Khoảng trống dữ liệu > 2 bước nến → VÙNG NÉN CHẾT, đếm lại từ đầu.** Cổng [2] hỏi 10 nến
nén *liên tiếp*, nhưng trên mảng nến thì nến cuối chiều thứ Sáu và nến đầu chiều Chủ nhật nằm
sát nhau — máy sẽ đếm xuyên qua 48 giờ chợ đóng cửa.

Hậu quả cụ thể: vùng bắc cầu cuối tuần → đặt lệnh chờ → lệnh nằm đó suốt weekend (lệnh chờ của
ta **không có hạn**, đúng `ORDER_TIME_GTC` của bản gốc) → gap mở cửa Chủ nhật khớp nó cách xa
entry. Đúng loại lệnh cho kết quả cực đoan nhất và làm lệch hẳn thống kê.

> "Nén" nghĩa là giá đứng yên trong một quãng **liền mạch**. 48 giờ chợ đóng không phải giá đứng
> yên — không có giá nào cả.

### 12.6c ⭐ CỔNG ZONE ĐỌC ĐƯỢC TOÁN HẠNG ZONE — vì nó phán xét hậu quả của chính nó

Người dùng chỉ vào chart: lệnh chờ **đã khớp rồi** — tức giả thuyết về zone đã trúng —
mà cái hộp zone vẫn phình ra, nuốt luôn cây nến vừa phá vỡ nó.

**Đo trên một năm XAUUSD thật:** 89 % zone (491/550) tiếp tục **nở bề rộng** sau khi đã
sinh lệnh · trung vị **1,93×** · lớn nhất **17,0×**. Đếm theo số nến thì 96 %, trung vị
**+24 nến**, nặng nhất **10 → 188 nến**. Không phải ca hiếm — gần như mọi zone.

#### Vì sao KHÔNG sửa được bằng cách vẽ

Người dùng đã thử đúng ba đường, cả ba đều cụt, và đó mới là bằng chứng lỗ nằm ở cơ chế:

1. **Đặt `bề rộng ≤ 4 × ATR` ở cổng `[3]`** — nó nằm SAU cổng zone nên chỉ **lọc lệnh**,
   không giết zone. Người dùng tưởng mình đã đặt hạn mức; thật ra chưa từng đặt được.
2. **Thêm một cổng "kiểm tra lại zone" sau khối Vào lệnh** — nhánh đó chạy **đúng một
   nến**. Từ nến sau, cổng `[3]` đã trượt ở vế `zone_da_sinh_lenh là SAI`, dòng chảy
   không bao giờ tới nữa. Mà zone phình là chuyện của những nến *sau đó*.
3. **Nối một hành động huỷ zone** — không có. `ACTION_TYPES` chỉ có `check_cond` ·
   `vao_lenh` · `sua_lenh`, và `SUA_CHE_DO` chỉ có `doi_sl · doi_tp · hoa_von ·
   ket_thuc`. Tất cả đều về **lệnh**; zone là thứ *đọc được*, không phải thứ khối tác
   động vào (§6.3).

Zone chỉ có **đúng một cửa sinh-tử**: cổng mang cờ `cong_zone`. Mà đứng ở cổng đó thì
app lại **cấm đọc toán hạng zone** — nên câu *"rộng quá thì thôi, không tính là zone
nữa"* **không có chỗ nào hợp lệ để đứng**.

#### Luật mới, và nó chỉ là một câu

> **Cổng zone trả lời "cây nến này có được nuốt vào zone không?" — nên thứ nó phải nhìn
> là ZONE SAU KHI NUỐT, tức chính hậu quả nó sắp gây ra.**

`bo_chay._dat_zone_thu` bày ra **ZONE THỬ** (`so_lenh.Zone.thu_them` — bản sao đã cộng
cây nến đang xét) ngay trước khi cổng được đánh giá, rồi dẹp ngay sau. `engine_d02.doc`
ưu tiên nó. Mọi khối khác vẫn đọc zone thật.

Hai thứ rơi ra từ đó, không phải tính năng phải cài thêm:

- **`bề rộng ≤ N` thành một HẠN MỨC** — kiểm trước khi tiêu, nên zone **không bao giờ
  vượt**. Nhìn zone *trước* khi nuốt thì cây nến làm vỡ hạn mức đã nằm trong zone rồi:
  zone chết muộn một nhịp, và chết với hình dạng đã sai.
- **Ca NẾN ĐẦU TIÊN hết là ca đặc biệt.** Zone thử luôn có ít nhất một nến nên
  `bề rộng` = high − low của chính nó, một con số thật. Đây là chỗ hướng "zone thử"
  thắng hẳn hướng "zone như đang có": hướng kia gặp zone rỗng → NaN → cổng trượt → zone
  **không bao giờ hình thành được**.

⚠ **`zone_da_sinh_lenh` phải tra theo ID CỦA BẢN THỬ.** Bỏ id đi thì hàm tự lấy zone hiện
hành — mà lúc có lỗ hổng dữ liệu, zone hiện hành là zone **CŨ** (đã sinh lệnh) trong khi
bản thử là zone **MỚI** tinh. Cổng sẽ đọc "đã sinh lệnh" cho một zone chưa hề tồn tại.

⚠ **`_dat_zone_thu` phải dựng ĐÚNG thứ `_nuoi_zone` sẽ dựng**, kể cả nhánh lỗ hổng dữ
liệu. Hai bên lệch nhau là cổng phán xét một zone khác với zone thật sự được tạo ra —
loại lỗi im lặng tuyệt đối.

#### Đo được

Thêm đúng một dòng `Zone — bề rộng ≤ zone_range_max` vào cổng `[2]` của sơ đồ mẫu:

| | zone nở bề rộng sau khi sinh lệnh | nở gấp, trung vị | nặng nhất |
|---|---|---|---|
| không có hạn mức (như cũ) | 89 % | 1,93× | **17,0×** |
| có hạn mức ở cổng zone | 74 % | **1,18×** | **3,1×** |

Phần nở còn lại là **hợp lệ**: hạn mức là `4 × ATR hiện tại`, ATR giãn thì trần giãn
theo — đúng câu người dùng viết ra. Hết ca phình vô hạn.

⭐ **Sơ đồ CŨ không đổi một con số nào** — 550 lệnh · −19,52 R · DD 1,08 % · vốn 9.933,09
· 98 T / 292 B, trùng khít trước và sau. Đúng như phải vậy: zone thử chỉ tồn tại trong
đúng lúc cổng zone được đánh giá, và sơ đồ nào không hỏi về zone ở đó thì không thấy gì
khác. *(Thêm điều kiện vào thì số đổi hẳn — 853 lệnh · −16,08 R · DD 1,54 % — nhưng đó
là người dùng đổi chiến lược, không phải cơ chế tự đổi.)*

`core.khoi_sau_cong_zone` giờ tính **cả chính cổng zone**, và vì giao diện đọc thẳng
`validate.luong[tab].sau_cong_zone` từ đó nên dropdown ở cổng `[2]` có ngay toán hạng
zone — **không sửa một dòng TypeScript nào**. Đúng lý do §6.3 bắt hai bên dùng chung một
phép duyệt.

### 12.7 ⭐ DÒNG THỜI GIAN BẤT BIẾN · con trỏ

Không lưu "khung hình". Một lần chạy sinh ra ba hình dạng dữ liệu, đóng băng sau khi tính xong:

1. **mảng nến M1** — trục thời gian;
2. **các CỘT** — mỗi chỉ báo/metric là một mảng `float64` trên **trục M5**, đọc từ con trỏ M1
   bằng một phép chia nguyên;
3. **hai danh sách thưa** — sổ lệnh và nhật ký, mỗi bản ghi tự mang chỉ số nến của nó.

**Trạng thái sổ lệnh tại nến i là một PHÉP LỌC, không phải một ảnh chụp** — `so_lenh.Lenh` vốn
đã mang sẵn `nen_dat` / `nen_khop` / `nen_dong`. Chỗ này thiết kế cũ đã vô tình làm đúng.

> **Luật chọn chỗ cất:** thứ gì biến đổi theo nến mà không tự mang dấu thời gian thì thành một
> **cột**; thứ gì đã mang chỉ số nến thì để nguyên trong danh sách thưa.

Áp vào ca khó nhất — `VungNen` mutate liên tục nên trạng thái vùng tại nến i không suy ra được
từ đối tượng cuối cùng → 6 toán hạng vùng nén thành 6 cột. Đường vốn cũng chỉ là một cột nữa.

**Bộ nhớ (1 năm XAUUSD):** nến M1 ~374k dòng ≈ **18 MB** · mỗi cột M5 (71.760 dòng) 0,55 MB ·
~25 cột ≈ **14 MB** · nhật ký vài MB → **tổng ~40 MB**. Nếu chụp ảnh trạng thái mỗi nến thay vì
cột thì 150–350 MB, và con số đó phình theo mọi thứ ta thêm vào trạng thái. Thêm một metric ở
thiết kế cột = thêm 0,55 MB, cố định.

**CON TRỎ = một ĐIỂM trên đường đi giá** (nến M1 × 4 điểm). Không phải "một cây nến", cũng không
phải "một dòng nhật ký".

- **Xem** → trượt liên tục qua từng điểm. Nến đang chạy **lớn dần** ở mép phải đúng như thật:
  một cây nến M5 mọc qua 5 nến M1 × 4 điểm = **20 nhịp**. `delay(ms)` là khoảng cách giữa hai nhịp.
- **Debug** → bấm một dòng nhật ký, con trỏ **nhảy** tới đúng điểm đó.

Cùng một con trỏ, hai cách di chuyển. Và vì replay đúng nghĩa nên **nến bên phải chưa tồn tại** —
không có gì để che, không thể tự lừa mình bằng "chỗ này lẽ ra nên vào lệnh". Thêm một nút "xem
trọn lệnh" cho lúc muốn tua nhanh xem một lệnh đã đóng kết thúc ra sao.

`delay(ms)` là thứ **duy nhất** đổi mà không phải tính lại. Mọi ô cài đặt khác đổi là dòng thời
gian cũ hết hiệu lực.

### 12.8 Nhật ký — phần quan trọng nhất

Người dùng nói thẳng: *"đây là phần quan trọng nhất, vì người dùng debug, nâng cấp model là ở
hết đây."*

**Một bản ghi = một LƯỢT CHẠY.** Trong một nến có nhiều lượt (Manage cho L-0001, Manage cho
L-0002, rồi Entry). Không ghi từng khối đi qua — 7 khối × 71.760 nến = 500k dòng rác.

```
nen      int      chỉ số nến — khoá để tua
seq      int      thứ tự trong nến
tab      "entry" | "manage"
lenh_id  "L-0007" | None     ← lượt Manage này đang xét lệnh nào
duong    [id khối…]          ← đường đã đi, THEO THỨ TỰ
ket      "het_luot" | "xong"
ve[]     mọi điều kiện của cổng cuối: hai vế + đạt/không từng cái
viec     None | {lenh_dat | lenh_khop | lenh_dong | lenh_sua | vung_mo | vung_dong, …}
```

**Lưu `id` khối, KHÔNG lưu nhãn `[3A.1]`.** Nhãn là hàm thuần của (đồ thị + vị trí) và §9 đã cấm
lưu nó vào file. Ghi nhãn vào nhật ký thì kéo một khối lên 1 px là toàn bộ nhật ký cũ trỏ vào
khối khác. Nhãn được **dựng lại** lúc hiển thị bằng `core.flow_order` trên bản `doc` đã đóng
băng trong `meta`.

**Ghi cả `duong`** chứ không chỉ khối cuối: đồ thị được phép có vòng lặp (§4.1) nên đường từ khối
Bắt đầu tới một khối **không duy nhất**, không suy ngược lại được.

**Chữ do Python dựng, theo lô đang nhìn** (~200 dòng) — đúng luật bất di bất dịch #2. 150k bản
ghi không tốn một byte chữ nào lúc chạy.

```
14:35  ENTRY   [1]→[2]                    hết lượt tại [2] · atr_bps 8.31 ≥ 7.0
14:40  ENTRY   [1]→[2]→[3]→[3A]→[3A.1]    đặt Buy Stop L-0007 @ 2334.12  SL 2330.60  TP 2341.16
14:41  MANAGE  L-0007  [1]→[1A]           hết lượt tại [1A] · lệnh này đã khớp = sai
```

**Danh sách phải ảo hoá.** 150k dòng đổ thẳng vào DOM sẽ treo WebView2 — không phải rủi ro, là
chắc chắn ngay lần chạy một năm đầu tiên. Chỉ dựng ~200 dòng đang nhìn, chiều cao dòng cố định
để tính thanh cuộn bằng phép nhân. Tự viết ~60 dòng, không thêm thư viện.

**Mặc định lọc "chỉ lượt có VIỆC xảy ra"**, có nút bật "mọi lượt". 150k dòng đều đều thì mắt
không bắt được chỗ bất thường.

**Ghi ra đĩa** một file `.jsonl` mỗi lần chạy trong `luu_tru.thu_muc_nhat_ky()`, đầu file là
nguyên bản `normalize_process(doc)` + hash — để mở lại và **so hai lần chạy**.

#### 12.8b ✅ GỘP DÃY LẶP — thứ đáng giá nhất của bảng nhật ký

Chạy thật rồi mới lòi ra: 296 dòng trên màn hình mà 7/9 dòng liên tiếp **giống hệt nhau từng
chữ**. Manage chạy nhịp M1 nên mỗi nến M5 đẻ ra 5 dòng y đúc; người dùng phải cuộn qua một bức
tường chữ trùng lặp để tìm dòng có nghĩa.

Gộp **dãy liền kề** giống hệt lại thành một dòng kèm huy hiệu `×4`. Ba điều:

- gọn ~5 lần (mỗi nến M5: 6 dòng → 3);
- **trả lời thêm** được câu *"cổng đó chặn mấy lượt liền"* — thứ cuộn tay đếm không ra;
- chỉ gộp **liền kề**, không gộp cách quãng: gộp cách quãng là xáo trộn thứ tự thật. Dòng
  **có việc** thì KHÔNG BAO GIỜ bị gộp — hai lần đặt lệnh trùng chữ vẫn là hai việc khác nhau.

Kết quả thật trên một nến M5: `MANAGE ×1 · ENTRY ×1 · MANAGE ×4`. Dòng ENTRY cắt đôi dãy Manage,
và chính chỗ cắt đó làm nhịp M5 hiện ra bằng mắt.

Kèm theo: ô lọc **"chỉ dòng có việc"** (mỗi dòng đã mang sẵn cờ `co_viec`, lọc ở JS, không đụng
backend) và nút **Ghi ra file**.

**Dòng được tô trắng là dòng GẦN NHẤT tính tới con trỏ**, không phải "dòng vừa được thêm" và cũng
không phải "dòng trùng đúng nến hiện tại":

- *"dòng vừa thêm"* sai khi **tua ngược** — tua lùi thì dòng mới nhất không còn là chỗ đang đứng;
- *"trùng đúng nến hiện tại"* thì 4/5 khung hình **chẳng có gì sáng** (Entry chỉ chạy ở biên nến
  M5). Đã dựng thử đúng cách này và chụp màn hình mới thấy — bảng tối om suốt.
- Còn *"gần nhất tính tới con trỏ"* thì **luôn có đáp án**, và đúng cả khi tua tới lẫn tua lui.

Cụp/mở: bê nguyên `.bang-duoi` của cửa sổ chính — thanh kéo ở mép trên để chỉnh chiều cao, hàng
tab bên trái, `▼/▲` ở góc phải hàng tab, nhấp đúp hàng tab cũng cụp. Nút gập nằm trên chính bảng
nhật ký chứ không ở góc thanh công cụ: *tay đang ở đâu thì nút ở đó*. Chữ 12px, bằng bảng số liệu.

### 12.9 Bảng số liệu bên phải

**Nó phải dựng từ chính vết đánh giá của lượt đang xem, không được hỏi lại bộ tra.** Nếu không,
bảng và nhật ký sẽ nói khác nhau *đúng lúc đang debug*: `số lệnh chờ` đầu nến là 1, cuối nến là
0, mà cổng [3] đọc nó ở giữa. Bảng ghi 1 còn nhật ký ghi cổng đọc 0 và khớp → mất một buổi tưởng
là bug chiến lược trong khi đó là bug của công cụ.

Bốn khối, mỗi khối một nguồn rõ ràng:

1. **Toán hạng đang dùng** — suy từ chính `doc`, khoá theo
   `(tên + tf ĐÃ CHUẨN HOÁ VỀ KHUNG QUYẾT ĐỊNH + period + method + ĐƠN VỊ TẠI CHỖ ĐỌC)` nên
   ATR(M5,14) và ATR(M5,42) là hai dòng riêng — và ATR(M5,14) đọc bằng `bps` cũng là một dòng
   riêng với ATR(M5,14) đọc bằng giá (xem 12.9e). Toán hạng chưa được đọc trong lượt đó hiện
   **dấu gạch**, không hiện 0.
2. **Trạng thái engine** — `VungNen.tom_tat()` (đã có sẵn, chưa ai gọi).
3. **Tài khoản** — equity, drawdown, margin đã dùng, số vị thế, số lệnh chờ.
4. **Bảng theo TỪNG LỆNH đang sống** — mỗi lệnh một hàng, cột là 6 toán hạng nhóm "Lệnh này".
   Thiếu bảng này thì tab Manage vô hình.

#### 12.9b ✅ BẢNG TỰ SINH TỪ SƠ ĐỒ — không một nhóm nào viết tay

Bản đầu chia bốn khối như trên, nhưng khối 2 mang đúng cái tên `Vùng nén (engine)` **viết cứng
trong `BangSoLieu.tsx`**. Hôm nay nó đúng vì chiến lược mẫu là D_02; làm chiến lược khác là bảng
nói dối, và ai đó phải nhớ sửa tay. Nhận xét của người dùng nói thẳng ra điều đó:

> *"không nên có cả vùng nén(engine) … tôi chỉ cần xem số các phép toán đang dùng là được. về sau
> làm chế thuật khác sẽ loạn."*

Nên bảng **không còn khối nào định trước**:

- **Hàng nào có** ← `core.toan_hang_dung(doc)`: quét đúng những toán hạng sơ đồ **thật sự đọc** —
  hai vế của mọi điều kiện, cộng những thứ một *cách tính* ngầm đọc (`TINH_CAN_TOAN_HANG`), cộng
  đỉnh/đáy vùng khi có lệnh chờ **stop** (giá đặt neo vào mép vùng, không điều kiện nào hỏi tới
  nhưng người dùng phải thấy lệnh sắp nằm ở đâu). Dedupe, giữ nguyên thứ tự gặp.
- **Nhóm nào có** ← chính `nhom` mà `kho/` đã khai ở mỗi toán hạng — nhưng xem 12.9c, tên nhóm
  cuối cùng KHÔNG được in ra.
- **Giá trị** ← `ApiTester._cot_toan_hang`, ba nguồn theo thứ tự rẻ dần: cột đã tính sẵn (chỉ báo
  + giá) → cột engine ghi lúc chạy → thứ suy được từ sổ lệnh/thời gian. Không tra được thì trả
  `None` và bảng để trống: **thà bỏ trống còn hơn bịa một con số**.
- `bo_chay` cũng lấy danh sách cột engine cần ghi từ chính `toan_hang_dung` (∩ `ENGINE_TRA_LOI`),
  nên nó chỉ ghi những cột bảng sẽ dùng — bỏ được bộ 6 cột cố định trước đây.

Thêm một engine mới vào `kho/` là bảng có ngay, **không sửa một dòng giao diện nào**.

Nhóm *"Lệnh này"* cố ý ĐỨNG NGOÀI cơ chế trên: nhóm đó không có **một** giá trị tại nến `i` —
Manage chạy một lượt cho **mỗi** lệnh đang sống. Ép thành một con số là bảng lại nói khác nhật ký,
đúng cái bẫy đầu mục này cảnh báo. Nên nó là bảng riêng bên dưới, mỗi lệnh một hàng.

#### 12.9c ✅ BỎ HẲN TÊN NHÓM · ba cột · lệnh hai dòng

Cơ chế 12.9b đã tổng quát, nhưng **kết quả in ra thì không**: `VÙNG NÉN` đứng ngang hàng với
`CHỈ BÁO / TÀI KHOẢN / GIÁ`, mà ba cái kia là phạm trù phổ quát còn nó là khái niệm riêng của một
chiến lược. Người dùng: *"tôi không thích gọi là vùng nén vì đây không tổng quát."* Đây là một
bài học chung: **cơ chế tổng quát vẫn có thể đẻ ra một màn hình không tổng quát.**

Chốt: **tên nhóm không in ra nữa.** `nhom` vẫn về đủ trong payload, nhưng giao diện chỉ dùng nó để
biết **chỗ kẻ một đường mảnh**. Không tiêu đề nào thì không tiêu đề nào sai được — chiến lược nào
sau này cũng đúng, vĩnh viễn. Cấu trúc không mất, vì danh sách vốn xếp theo đúng thứ tự sơ đồ đọc
nên các số cùng loại tự nằm cạnh nhau. Bỏ 4 tiêu đề còn thu lại ~110px chiều cao.

**Ba cột thay vì hai.** Chỗ phí nhất là khe rỗng giữa nhãn trái và số phải, trong khi tên dài lại
bị cắt cụt. Tách nhãn làm đôi ngay ở `api.py` (`ten` + `phu`) rồi đặt `phu` (`M15·50·SMA`, chữ mờ
10.5px) vào đúng cái khe đó: hết phí chỗ, và tên ngắn lại nên thôi bị cắt. Số dùng
`tabular-nums` — thiếu nó thì lúc phát cả cột giật ngang theo từng con số, mắt không quét dọc nổi.

Chữ **12px** — 11px mỏi mắt, 13px chiếm chỗ mà chẳng rõ thêm.

**Mỗi lệnh HAI DÒNG.** Một dòng 5 cột thì ba mức giá bị cắt thành `2643.0…`, đọc ra một con số vô
nghĩa. Dòng trên là *tình trạng* (hướng · id · đã khớp/chờ Stop · R), dòng dưới là *ba mức giá đủ
số*. Chấm hoà vốn chuyển sang nằm cạnh **SL** — nó nói về SL chứ không nói về cái id.

Phương án *"hiện cả hai giá trị / thêm một dòng phụ mờ dưới mỗi hàng"* (bàn ở 12.9e) đã bị **bác**
vì cùng lý lẽ này: 4 trong 12 hàng của sơ đồ mẫu là `khoang_cach` nên dòng phụ tốn ~84px — gần
trọn 110px vừa thu về khi bỏ tên nhóm — mà **vẫn** để lại con số trùng trên màn hình.

#### 12.9d ⚠ LỖI THẬT: hàng lệnh đọc trạng thái CUỐI backtest

Tìm ra lúc soi ảnh chụp kiểm bố cục mới, không phải lúc tìm lỗi.

`L-0006` **đặt** 17:55 nhưng mãi **19:55** mới khớp — bảng lại hiện *"đã khớp · −1.21R"* ngay ở con
trỏ 17:59. Nguyên nhân: hàng lệnh đọc thẳng `l.da_khop` / `l.gia_khop` / `l.sl` / `l.tp`, mà `Lenh`
là đối tượng của **cuối backtest** và mọi lần *Sửa lệnh* đã ghi đè lên chúng.

Đây đúng là cái bẫy §12.9 dựng cả mục ra để cảnh báo, và **chart đã dính đúng nó một lần rồi**
(§12.16). Một cơ chế cắt lát đã có sẵn không tự lan sang chỗ mới: chỗ nào đọc `Lenh` cũng phải hỏi
lại "trường này là của lúc nào".

Sửa: `bo_chay.lenh_tai_nen(kq, l, i, gia)` cắt **mọi** trường theo `i`. Kèm hai thứ:

- `_moc_muc(kq)` gom mọi mốc SL/TP từ nhật ký (`lenh_dat` + `lenh_sua`), `_muc_tai` tra ngược ra
  mức tại nến `i` — nên **TP cũng hết rò**, không chỉ SL.
- `_sl_lich_su` lấy điểm đầu từ chính bản ghi `lenh_dat` thay vì suy ngược `gia_dat ± R`. Cách suy
  ngược đúng với SL nhưng chịu thua với TP, vì công thức khoảng cách TP không được lưu ở đâu cả.

Kiểm lại: 17:59 → `chờ Stop @2638.965`, `lai_R = None`; 20:05 → `đã khớp`, `−0.37R`.

Khi con trỏ đứng đúng lượt có lệnh được đặt, hiện thêm **phép tính vào lệnh đã dùng số nào**:
`đệm = 0.10 × ATR_hiện_tại = 0.42 · R = 1.5 × ATR_TB_vùng = 4.80`. Đây là chỗ **duy nhất** bắt
được lỗi lẫn hai loại ATR mà §6.3 cảnh báo — validator không bắt được lỗi đó.

#### 12.9e ⚠ LỖI THẬT: hai hàng ATR trùng mặt · ĐƠN VỊ THEO CHỖ DÙNG

Triệu chứng người dùng chụp lại: bảng có **hai dòng y hệt nhau**, `ATR · M5·14 · 1.412`, cách nhau
một dòng. Không trùng do hiển thị — trùng **từ nguồn**: hàng đầu là vế trái cổng nén, hàng sau do
`TINH_CAN_TOAN_HANG["atr"]` sinh ra vì đệm vào lệnh dùng cách tính `× ATR`. Khoá dedupe giữ chúng
riêng (`tf='M5'` vs `tf=None`), rồi `api.py` điền `tf=None → M5` và `ChuongTrinh.khoa` cũng điền
`tf or tf5`, nên hai hàng khác khoá lại đổ ra cùng một mặt và cùng một cột.

Bốn câu chốt:

1. **Một hàng = một cặp *(toán hạng, đơn vị tại chỗ nó được đọc)*.** Cùng `atr(M5,14)` đọc ở cổng
   nén là `bps`, ở đệm vào lệnh là GIÁ — hai con số khác nhau, nên hai hàng. Gộp lại thì hàng đó
   nói dối cho một trong hai chỗ. Kèm theo: `tf` để trống được chuẩn hoá về **khung quyết định**
   ngay tại `core.toan_hang_dung` (`core.khung_quyet_dinh`), tức cùng tầng với khoá dedupe — chứ
   không ở tầng hiển thị như trước.
2. **Đơn vị lấy từ `phai.tinh` của ĐIỀU KIỆN**, qua `core.don_vi_cua_o` (§6.4 — đơn vị thuộc về
   cái ô, và một hàng bảng *là* một ô). **Không** lấy từ `tinh` của đệm/SL/TP: ở đó `atr` là **số
   nhân** của `_khoang`, không phải đại lượng đang được đo — lấy nhầm là in `ATR [× ATR] = 1.000`
   và mất đúng con số 1.412 mà đệm cần. Vắng `tinh` nghĩa là **GIÁ**, không phải "chưa biết"
   (`normalize_action` chặn `gia` khỏi `phai.tinh`).
3. **Đơn vị đi vào `phu`**, không vào `nhan` (§6.4: nhãn thuộc TOÁN HẠNG, dùng chung hộp
   thoại/nhật ký/kho) và **không** thành cột thứ tư (§12.9c vẫn ba cột). Dạng `M5·14 [bps]`, chữ
   do Python ghép từ `core.DON_VI_NGAN` — Tester/Live không nhận bảng đơn vị nào, gửi khoá thô là
   buộc JS đẻ ra một bảng nhãn thứ hai lệch được.
4. **Đơn vị đồng thời là một lời khai phụ thuộc.** `X <= 4 [× ATR zone]` đọc ngầm `zone_atr_tb`
   làm mẫu số; không khai thì nó không vào `bo_chay.CV`, engine không ghi cột, và hàng đó trống
   vĩnh viễn. Mẫu số **phải** đến từ cột đã ghi lúc chạy, không hỏi lại `so.zone_hien_hanh()`
   (đúng lỗi §12.9d); thiếu cột thì để trống cả hàng. `bo_chay.quy_doi_cot` (bản theo CỘT, cho
   bảng) và `bo_chay._quy_doi` (bản theo NẾN, cho cổng và cho vết nhật ký) **phải sửa cùng lúc** —
   công thức lệch nhau là bảng hiện một số còn nhật ký hiện số khác đúng lúc đang debug cổng.

Đo lại sau khi sửa, trên một lần chạy thật của sơ đồ mẫu: `ATR · M5·14 [bps] · 4.697` đứng cạnh
`ATR · M5·14 · 1.242`, và đối chiếu **226 lượt** chạy cổng nén thì bảng khớp vết nhật ký với lệch
tối đa **0.000e+00**.

⚠ Hệ quả ngoài yêu cầu ban đầu, phải nói ra: cổng zone viết `zone_range <= zone_range_max [× ATR]`
nên hàng `Zone — bề rộng` cũng chuyển từ đơn vị giá sang `[× ATR]`. Cùng một luật, cùng một lỗi.

#### 12.9e ✅ ĐƠN VỊ THEO CHỖ ĐỌC — một hàng là một CẶP (toán hạng, đơn vị)

Người dùng gửi ảnh chụp bảng, chỉ vào **hai dòng `ATR · M5·14 · 1.412` giống hệt nhau**:
*"đổi cho tôi atr đầu thành bps để tiện theo dõi."*

Hai dòng đó không phải lỗi vẽ trùng. Chúng là **hai lần đọc khác nhau của cùng một toán
hạng**: dòng đầu là vế trái cổng nén (`atr < 7 [bps]`), dòng sau do đệm vào lệnh
(`0.15 × ATR`) ngầm cần qua `TINH_CAN_TOAN_HANG`. Bảng không in đơn vị nên chúng bị san
phẳng thành một mặt.

Và cái người dùng chỉ vào mới là chỗ đau thật: **cổng so bằng `bps`, bảng in bằng GIÁ.**
Không ai nhẩm được `1.412` có nhỏ hơn ngưỡng `7 bps` hay không — mà đó đúng là câu bảng
sinh ra để trả lời. Bảng và cổng nói hai thang khác nhau về cùng một con số, đúng cái bẫy
§12.9 dựng cả mục ra để cảnh báo.

> **§6.4 đã có sẵn luật này rồi: *"ĐƠN VỊ THUỘC VỀ CÁI Ô."* Bảng số liệu chưa áp. Một hàng
> bảng CHÍNH LÀ một ô — nó là điểm con số được đọc.**

Nên khoá dedupe lên `(ten, tf, period, method, don_vi)`, và `don_vi` lấy bằng chính
`core.don_vi_cua_o` — đúng hàm mà nút `▾`, ô khoá của hộp thoại và soát tĩnh đang dùng, để
một hàng không bao giờ khai được đơn vị mà cái ô ấy vốn cấm. Kết quả trên sơ đồ mẫu:

```
ATR              M5·14 [bps]      4.238   ← cổng nén so với 7
ATR              M5·14            1.423   ← đệm vào lệnh, đơn vị GIÁ
Zone — bề rộng   [× ATR]         10.760   ← cổng so với 4   (trước: 16.11 đơn vị giá)
```

Hai dòng thôi trùng mặt **như một hệ quả**, không phải như một bản vá: chúng vốn dĩ là hai
thứ khác nhau, giờ mới được phép nói ra.

**Bốn chỗ dễ sai, cả bốn đều đã cắn ít nhất một lần:**

1. ⚠ **`tf` để trống phải chuẩn hoá Ở TẦNG SINH HÀNG, không ở tầng hiển thị.** Mặc định
   *"ô khung trống = khung quyết định"* trước đây nằm trong `api.py`. Nên hai hàng **khác
   khoá** (`tf=None` vs `tf='M5'`) lại đổ ra **cùng một mặt** — đó chính là cơ chế đẻ ra
   cặp dòng trùng trong ảnh chụp. Luật nhịp gom về `core.nhip_cua` / `khung_quyet_dinh`,
   một chỗ duy nhất cho cả `bo_chay._dung_truc` lẫn `toan_hang_dung`.
2. ⚠ **Toán hạng do `TINH_CAN_TOAN_HANG` sinh KHÔNG được mượn `tinh` của khối.** Ở đó `atr`
   là **số nhân** của `_khoang` (`v × ATR`), không phải đại lượng đang được đo. Gán bừa là
   in `ATR [× ATR] = 1.000` — mất đúng con số 1.423 mà đệm vào lệnh cần.
3. ⚠ **Đơn vị cũng là một lời khai phụ thuộc.** `X ≤ 4 [× ATR zone]` đọc ngầm `zone_atr_tb`
   làm **mẫu số**. Không khai thì nó không vào danh sách cột engine, engine không ghi cột,
   và hàng đó trống vĩnh viễn không ai hiểu vì sao.
4. ⚠ **`quy_doi_cot` và `_quy_doi` phải sửa CÙNG LÚC**, nên đặt dính nhau trong
   `bo_chay.py`. Một cái tính MỘT nến cho **cổng** (và cho vết nhật ký), cái kia tính CẢ LÔ
   cho **bảng**. Công thức lệch nhau là bảng hiện 4.238 còn nhật ký hiện số khác — đúng lúc
   đang debug chính cái cổng đó.

Chỉ hiển thị 4 đơn vị `DON_VI_CHO["dieu_kien"]` cài được (`gia` · `bps` · `atr` · `atr_zone`):
`R` và `bien_zone` hợp lệ ở ô SL/TP nhưng `_quy_doi` gặp chúng là `raise LoiChay`, mà nổ
giữa lúc dựng lô 300 khung hình thì **mất cả bảng lẫn nến lẫn nhật ký**, không chỉ một hàng.

Mẫu số đọc từ **CỘT đã ghi lúc chạy**, không hỏi lại `so.zone_hien_hanh()` — đối tượng đó
mutate liên tục nên ở con trỏ nào cũng trả trạng thái CUỐI backtest (§12.9d). Thiếu cột mẫu
số thì hàng **Ở LẠI và in gạch**, không biến mất: bỏ hàng là người dùng mất dấu một toán
hạng sơ đồ ĐANG đọc.

Đơn vị vào `phu`, **không vào `nhan`** — nhãn thuộc TOÁN HẠNG (dùng chung hộp thoại · nhật
ký · kho), đơn vị thuộc CHỖ DÙNG. Vẫn đúng ba cột của §12.9c, và đơn vị GIÁ không in nhãn
(cùng quy ước `ve_phai_display`).

**Đã đo: backtest KHÔNG đổi một con số nào** — 550 lệnh · −19,52 R · DD 1,08 % · vốn
9.933,09 trước và sau, trên cùng 353.129 nến. Đúng như phải vậy: `_quy_doi` (thứ cổng dùng)
không bị đụng tới, đây thuần là tầng hiển thị. `tests/test_so_do_mau.py` canh cả hình dạng
hàng lẫn **danh sách cột engine không đổi** — trước lượt này không bài nào gọi
`toan_hang_dung`, dù cả bảng lẫn bộ chạy đều treo vào nó.

#### 12.6f ⭐⭐ CỔNG ZONE CÓ HAI DANH SÁCH — *đếm* và *hợp lệ*

*"ta chưa định nghĩa ra thế nào là một zone chuẩn chỉ, khiến cả bài toán rối hơn."*

Đúng, và nó vừa đẻ ra một sơ đồ **chết hẳn**: người dùng đưa `Zone — số nến ≥ 10` vào
cổng zone, soát tĩnh báo SẠCH, chạy một năm ra **0 zone · 0 lệnh**.

**Vì sao:** cổng zone hỏi *"nến này có được vào zone không"* và được xét trên **zone thử**
(§12.6c) — zone thử của cây nến đầu tiên luôn có đúng **1** nến. `1 ≥ 10` sai ⇒ zone chết
⇒ nến sau lại bắt đầu từ 1 ⇒ **không bao giờ chín được**. Đòi zone phải lớn trước khi nó
được phép lớn.

##### Luật phân loại — hỏi "TRƯỢT vế này nghĩa là gì"

```
"nén HỎNG rồi"   → phần ĐẾM      → zone CHẾT
"chưa TỚI LÚC"   → phần HỢP LỆ   → zone SỐNG, đếm tiếp
```

| điều kiện | trượt nghĩa là | thuộc về |
|---|---|---|
| `bề rộng ≤ N × ATR` | giá đã bung ra khỏi khoảng — **nén hỏng** | **ĐẾM** |
| `số nến ≥ K` | mới được 4 nến — **chưa tới lúc** | **HỢP LỆ** |

⚠ Bề rộng **phải** ở phần ĐẾM mới ngắt được zone. Để nó ở phần HỢP LỆ thì zone vẫn sống,
vẫn phình, chỉ là không dùng được — và vẫn **chặn zone mới** (mỗi lúc chỉ một zone). Đúng
cảnh trước §12.6c: phình trung vị 1,93×, lớn nhất **17×**.

##### Một khối, hai danh sách

`dk_hop_le` là danh sách điều kiện **thứ hai** trên chính cổng zone, cùng hình dạng với
`conditions` và đi qua **cùng một** phép chuẩn hoá (`_chuan_dieu_kien`) và **cùng một**
phép so (`_xet_dieu_kien`) — chép ra bản thứ hai là sớm muộn một bản quên quy đổi đơn vị.

- Phần **đếm** quyết dòng chảy như mọi cổng: qua thì đi tiếp, trượt thì hết lượt.
- Phần **hợp lệ** **không** chặn gì. Nó chỉ định nghĩa toán hạng `Zone hợp lệ`.

⚠ **Nhãn mang chữ "HIỆN HÀNH" là cố ý.** Toán hạng này luôn hỏi về zone đang đếm lúc
này. Đứng cạnh dòng `Lệnh này còn thuộc zone hiện hành` bên Manage, hai dòng phải cùng
một chủ ngữ — gọi bằng hai tên thì đọc ra thành **hai zone khác nhau**, mà thật ra chỉ
có một:

```
Lệnh này còn thuộc zone hiện hành là SAI      ← nó không phải zone của lệnh này
và Zone hiện hành hợp lệ là ĐÚNG              ← và nó đã hợp lệ
                                              ⇒ "đã có một zone khác, và zone đó hợp lệ"
```

Và **không** gọi là *"Zone mới"*: ở Entry, zone hiện hành chính là zone sắp vào lệnh,
chẳng mới gì cả. Nó chỉ "mới" nhờ dòng phía trên nói ra điều đó — mà **một cái nhãn phải
đúng khi đứng một mình**.

Nhờ đó *"hợp lệ"* được viết ra **đúng một lần**. Trước đây phải chép `số nến ≥ K` và
`bề rộng ≤ N` sang từng cổng cần hỏi — Entry `[3]` một bản, Manage `[1A]` một bản — và
hai bản chép thì sớm muộn lệch nhau (đúng thứ §6.4 dựng bảng tham số ra để chống).

```
[2]  ⬗ CỔNG ZONE · ĐẾM    atr < 7 · bề rộng ≤ zone_range_max
     ⬗ HỢP LỆ khi         số nến ≥ zone_can_nen
[3]  Zone hiện hành hợp lệ là ĐÚNG  và  Zone này đã sinh lệnh là SAI
[4]  → sinh lệnh
```

##### `Zone hiện hành hợp lệ` KHÔNG mang máy trạng thái quay lại

§7.5 cố ý bỏ `IDLE/COUNTING/CONFIRMED/…`, nên phải nói rõ chỗ khác nhau:

> Máy trạng thái là **nhớ một trạng thái**. Cái này là **đặt tên cho một điều kiện**, rồi
> tính lại mỗi lần được hỏi — `Ctx.zone_hop_le()` là hàm thuần của zone lúc này, không
> cất gì cả. Cùng lý lẽ bảng tham số dùng cho những con số: đặt tên một lần, dùng nhiều
> nơi, sửa một chỗ.

Chưa có zone, hoặc chưa khai `dk_hop_le` → **NaN** (cổng trượt), không phải SAI. Trả SAI
thì `KHÔNG Zone hợp lệ` hoá ĐÚNG giữa lúc chẳng có zone nào — đúng loại nói dối §12.13 cấm.

⚠ **Đọc zone THẬT, không đọc zone thử.** "Hợp lệ" nói về cây zone đã chốt; zone thử chỉ
tồn tại trong đúng lúc phần đếm đang cân nhắc có nuốt nến này không.

##### Bốn phép soát

| | |
|---|---|
| hỏi `Zone hiện hành hợp lệ` mà chưa khai `dk_hop_le` | **lỗi** — hỏi một khái niệm chưa ai định nghĩa |
| cổng zone tự hỏi `Zone hiện hành hợp lệ` | **lỗi** — vòng tròn, đó là kết quả của chính nó |
| `dk_hop_le` trên cổng KHÔNG phải cổng zone | **lỗi** — và `normalize` cố ý **GIỮ** nó lại để validator nói được (bài học §13.0d: xoá trước thì validator không bao giờ thấy) |
| `số nến ≥ K` đặt nhầm vào phần đếm | bài kiểm canh: **0 zone** |

##### ⚠ 12.6g LỖI THẬT: `bool(NaN)` là **True**, nên "chưa có số" đọc thành ĐÚNG

*"khi zone mới mới tạo được 1 nến mà 2 lệnh zone cũ đã bị huỷ."*

`_so_sanh` hứa ngay ở dòng docstring đầu tiên: *"NaN ở bất kỳ vế nào → False (cổng
trượt)"*. Nhưng hai nhánh đúng/sai chạy **TRƯỚC** phép kiểm NaN:

```python
if phep == "la_dung":
    return bool(trai)          # ← bool(float("nan")) là True
...
if trai != trai: return False  # ← không bao giờ tới lượt
```

Đo trên một năm: `Zone hiện hành hợp lệ` trả `NaN` **6.295 lần**, và **cả 6.295 lần đều
là lúc KHÔNG có zone nào**. Cổng Manage `… và Zone hiện hành hợp lệ là ĐÚNG` vì thế khớp
giữa lúc chẳng có zone mới nào — huỷ sạch lệnh chờ, đúng thứ vế ấy sinh ra để ngăn.

| | trước | sau |
|---|---|---|
| cổng `[1A]` khớp | 1391 | **662** |
| zone nhỏ nhất lúc huỷ | **0 nến** (không có zone) | **10** = đúng ngưỡng |
| huỷ khi zone chưa đủ ngưỡng | phần lớn | **0** |

**Cả `là ĐÚNG` lẫn `là SAI` đều trả False khi chưa có số** — *chưa có số thì không trả
lời được, chứ không phải trả lời ngược lại.*

⚠ Đây **không** phải lỗi riêng của `zone_hop_le`: nó dính mọi toán hạng đúng/sai có thể
"chưa có số", và luật §12.13 đã bị phá âm thầm ở nhánh này từ trước. `zone_hop_le` chỉ là
cái đầu tiên trả NaN thật sự nên mới lộ ra. Bài kiểm nay canh thẳng `_so_sanh`, không đi
vòng qua một chiến lược cụ thể.

*(Số backtest xấu đi sau khi sửa — 2152 lệnh · −43,31 R → 1954 · −54,66 R — vì trước đó
lệnh chờ bị huỷ sớm vô cớ, vô tình cắt bớt lệnh xấu. Một lợi thế đến từ LỖI, không phải
từ chiến lược.)*

**Đo:** cấu trúc mới cho ra **853 lệnh · −16,08 R** — **trùng khít** bản cũ đặt đúng hai
điều kiện đó theo lối chép tay. Cơ chế không đổi kết quả, chỉ đổi chỗ viết. Và sơ đồ mẫu
(chưa dùng `dk_hop_le`) vẫn **550 lệnh · −19,52 R · DD 1,08 %**, không lệch một con số.

#### 12.6d ✅ MANAGE ĐỌC ĐƯỢC ZONE — định nghĩa và đọc là hai chuyện

*"tại sao bên tab Manage, phần điều kiện không có điều kiện zone. Entry vẫn có."*

Hai luật, mỗi luật đều đúng, cộng lại thành một cái bẫy:

1. **Chỉ khối đã đi qua cổng zone mới được đọc toán hạng zone** — `khoi_sau_cong_zone`
   tính trên khối của **từng tab**.
2. **Manage không được có cổng zone** — nó chạy một lượt cho MỖI lệnh đang sống, đặt
   cổng đếm ở đó là một cây nến bị đếm nhiều lần.

⇒ `sau_cong_zone` của Manage **luôn rỗng**, nên Manage **vĩnh viễn không đọc được zone**.
Ép một toán hạng zone vào thì soát tĩnh mắng *"Sơ đồ đọc Zone — đỉnh (HH) nhưng KHÔNG có
cổng zone nào"* — một câu vô nghiệm, vì Manage không được phép có cổng.

**Mà bộ chạy thì đọc được bình thường.** Zone nằm trong **sổ dùng chung** (`ctx.so`),
không thuộc tab nào. Đo được: cho cổng `[1A]` của Manage đọc `Zone — đỉnh (HH)`, bỏ qua
soát tĩnh, nó trả `2627.998` — một cái giá thật. Chỉ soát tĩnh và dropdown chặn.

> **Chỗ luật bị lẫn:** *định nghĩa* zone và *đọc* zone bị gộp làm một. Cùng lý lẽ §5 đã
> viết cho cổng rẽ nhánh — **đọc thì lặp lại bao nhiêu lần cũng vô hại, chỉ tác động mới
> không rút lại được**. Cấm Manage ĐỊNH NGHĨA zone là đúng; cấm nó ĐỌC là quét nhầm.

`core.khoi_doc_duoc_zone(doc)` nhìn **cả tài liệu** thay vì từng tab, và là nguồn duy
nhất cho cả soát tĩnh lẫn giao diện:

| tab | được đọc zone ở | |
|---|---|---|
| Entry | khối đi qua cổng zone (kể cả chính cổng — §12.6c) | như cũ |
| Manage | **mọi khối**, nếu Entry có cổng zone | 🆕 |
| Manage | không khối nào, nếu Entry không có cổng zone | không có zone thì không có gì để đọc |

Luật *"cổng zone chỉ đặt ở Entry"* **giữ nguyên** — nó vẫn đúng, và bài kiểm canh cả hai
chiều.

⚠ **Manage đọc zone của lượt Entry TRƯỚC ĐÓ.** Trong một nến, Manage chạy trước Entry
(§6.0), nên zone nó thấy là zone tính tới hết nến trước. Manage nhịp M1 còn thấy cùng một
zone suốt 5 nhịp giữa hai lượt Entry. Đó là sự thật của thứ tự, không phải sai sót — nhưng
ai viết *"zone lúc này"* ở Manage thì phải hiểu đúng nghĩa đó.

#### 12.6e ✅ `Lệnh này còn thuộc zone hiện hành` — câu hỏi đúng để huỷ lệnh chờ

Lệnh chờ neo vào **MÉP một zone**. Zone ấy chết là cái neo hết nghĩa — nên câu cần hỏi
khi quyết định huỷ là *"zone đẻ ra lệnh này còn hiện hành không"*.

Cổng `[1A]` của sơ đồ mẫu đang hỏi `atr ≥ 7 bps`: một phép **đoán gián tiếp** rằng zone
đã chết. Từ §12.6c, zone chết được **trong khi `atr` vẫn < 7** (vượt hạn mức bề rộng), và
còn chết vì lỗ hổng dữ liệu hay vì dòng chảy không tới cổng. Phép đoán ấy trượt hết những
ca đó, lệnh chờ nằm lại treo trên một zone đã chết.

```
[1A]  KHÔNG  lệnh này đã khớp
  và  KHÔNG  lệnh này còn thuộc zone hiện hành
      → Kết thúc lệnh này
```

**Một phép so ID gộp trọn ba ca**, vì `so.zone_hien_hanh()` chỉ trả zone còn **sống**:

| tình huống | trả lời |
|---|---|
| zone ấy chết, chưa có zone mới → `None` | ✘ không thuộc |
| đã có zone khác | ✘ không thuộc |
| vẫn là nó, vẫn sống | ✔ thuộc |

⚠ **So ID, không so đối tượng.** Zone mutate liên tục; `Lenh.zone_id` thì chốt cứng lúc
đặt. Id là chỗ duy nhất hai bên gặp nhau mà không ai đổi.

⚠ **"Zone" ở đây là zone ĐANG ĐẾM, chưa xét hợp lệ.** `Zone` không có trường nào về tính
hợp lệ — §7.5 cố ý bỏ máy trạng thái, `CONFIRMED` được thay bằng *"cổng [3] khớp"*, một
thứ chỉ tồn tại trong khoảnh khắc dòng chảy đi qua. Đo được: **45 % zone chết non**, chưa
bao giờ đủ số nến. Nên toán hạng này bắn **ngay khi zone chết**, không đợi có zone mới
hợp lệ. Muốn đợi thì ghép thêm hai vế `Zone — số nến ≥ …` và `Zone — bề rộng ≤ …` vào
chính cổng đó (Manage đọc được zone từ §12.6d), dùng lại **đúng tham số có tên** mà cổng
`[3]` đang dùng nên không rơi vào bẫy "một số gõ hai chỗ" của §6.4.

⚠ **Khai `can_zone` tại nguồn**, và `kho.CAN_ZONE` gom thêm từ đó. Hỏi câu này mà sơ đồ
không có cổng zone thì nó luôn trả SAI — đúng sự thật nhưng vô nghĩa; soát tĩnh chặn ngay
thay vì để người dùng ngồi nghĩ vì sao cổng không bao giờ khớp. Gom tại nguồn chứ không
gõ tay danh sách thứ hai — đúng cái bẫy `CAN_ZONE` đã kể (`zone_range_atr` còn sót lại
trong bản gõ tay sau khi toán hạng đó bị gỡ).

> **Thay `[1A]` là ĐỔI CHIẾN LƯỢC, không chỉ dọn dẹp.** Đo trên "Compress updated" một
> năm: huỷ đúng lúc thì ô `số lệnh chờ = 0` được giải phóng sớm hơn nhiều, nên số lệnh
> nhảy **1.034 → 2.160**. Toán hạng đã cài; ghép nó vào cổng nào là quyết định của người
> vẽ, sơ đồ mẫu **giữ nguyên** `atr ≥ 7`.

### 12.10 Chart — chỉ lệnh, không gì khác

Tuyệt đối không indicator, không vẽ gì thêm. Ép bằng kiểu dữ liệu: component chart nhận đúng
`{nen[], lenh[]}` và **không có đường nào chạm tới `cot`**.

| Trạng thái lệnh | Vẽ |
|---|---|
| chờ | 3 đường ngang: entry · TP · SL |
| đã khớp | mũi tên theo chiều mua/bán |
| đã đóng | mũi tên đầu + mũi tên cuối + vạch nối; rê chuột hiện profit, giờ vào, giờ ra |

Không có thư viện chart nào trong `package.json` → **tự vẽ Canvas 2D**, hợp với bộ icon nét tự
vẽ sẵn có và không phụ thuộc mạng. Cuộn chuột = zoom. Crosshair là một cờ chế độ chuột.

Nút đổi timeframe trên toolbar **chỉ đổi cách vẽ** (gộp M1 lên M5/M15/H1…), không đụng kết quả.

### 12.11 ✅ Cài đặt Strategy Test · nguồn nến

**Nằm trong Cài đặt của APP** (bánh răng ở thanh trạng thái, hoặc File → Cài đặt), thành một mục
riêng "Strategy Test" — **KHÔNG nằm trong cửa sổ tester**.

> Cài đặt là thứ đặt một lần rồi quên. Để nó trong cửa sổ tester thì mỗi lần bấm ▶ lại phải đi
> qua một bảng nữa mới chạy được — một thao tác hoá ba. Giờ **bấm ▶ ở cửa sổ vẽ là tester mở ra
> và CHẠY LUÔN**, cửa sổ đó chỉ còn nút `↻ Chạy lại`.

Khoá riêng `test` trong `du_lieu/cai_dat.json` + hàm `save_test_settings` với danh sách trắng
riêng — **không nhét vào `save_settings`**, hàm đó đang giữ nghĩa "cài đặt của trình soạn thảo";
trộn vào là hai thứ khác hẳn nhau cùng một cửa và sớm muộn giẫm chân nhau.

Ô nhập: `symbol` · `từ` · `đến` · `spread (points)` · `vốn (USD)` · `phí (USD/lot)` ·
`đòn bẩy 1:…` · `delay (ms)`. Cộng bảng **nguồn dữ liệu** ngay trên đó: mỗi symbol một dòng —
có từ ngày nào đến ngày nào, bao nhiêu nến, **bao nhiêu MB**, nút Xoá, nút Tải thêm.

Quản lý nguồn nến đặt ở `Api` CHÍNH chứ không ở `ApiTester`: nến là tài sản của **app** — tải một
lần rồi mọi chiến lược dùng chung — không phải của một lần chạy.

⚠ **Tester KHÔNG nhớ cài đặt.** `test_chay` đọc lại từ cửa sổ chính mỗi lần chạy. Nhớ ở phía JS
thì sửa Cài đặt xong bấm ▶ lại vẫn ăn bản cũ — mà cửa sổ tester sống lâu hơn một lần chạy, nên
mọi thứ nó "nhớ" đều có nguy cơ cũ.

Ô spread hiện **quy đổi ngay cạnh**: `XAUUSD: 1 point = 0.001 · spread 37 points = 0.037 USD ·
trung vị đo được trên dữ liệu đã tải: 37 points`. Thiếu dòng này thì "20 points" là con số vô
nghĩa — XAUUSD 3 chữ số thì đó chỉ là 0,02 USD, nhỏ hơn spread thật gần hai lần.

**Nguồn nến** ✅ — `nguon_nen.py`, chỗ **duy nhất** biết MT5 tồn tại. Ràng buộc duy nhất:
terminal phải đang mở và đã đăng nhập **lúc tải**; tải xong đóng MT5 vẫn backtest bình thường.

- Tải **M1 theo symbol**, một symbol giữ đúng **một dải liền**. `từ`/`đến` điều khiển cả tải lẫn
  chạy: chồng lấn thì chỉ tải phần thiếu rồi nối vào; rời hẳn thì tải luôn phần ở giữa cho liền,
  nhưng **báo trước số MB** — không bao giờ tải lén.
- Kèm một file `.json` cạnh cache giữ `digits` / `point` / `contract_size` lấy lúc tải → tính ra
  tiền vẫn đúng dù MT5 đang tắt, và ô "20 points" quy đổi được ra USD.
- Danh sách trong Settings: mỗi symbol một dòng — có dữ liệu từ ngày nào đến ngày nào, bao nhiêu
  nến, **bao nhiêu MB**, nút xoá.
- Bấm ▶ mà thiếu dữ liệu thì **không tự tải**, chỉ báo và mời bấm Tải.

**Đã đo thật** (XAUUSD, Exness, 2025-11): 29.917 nến một tháng = **1,37 MB** → một năm ≈
**16,5 MB**, khớp ước tính. Tải một tháng mất **0,2 giây**, nên một năm chỉ vài giây — không cần
thanh tiến độ cầu kỳ. Xin lại khoảng đã có: **0,00 s, không đụng tới MT5**.

⚠ **`spread_tb` là con số phải nhìn.** XAUUSD của Exness có `digits = 3`, nên `20 points` chỉ là
**0,02 USD** — quá nhỏ. Trung vị đo được trên dữ liệu thật là **37 points**. Vì thế `tai()` tính
trung vị (không phải trung bình — vài nến tin tức giãn gấp chục lần sẽ kéo lệch) và cất vào meta,
để ô spread trong Cài đặt gợi ý đúng thay vì bắt người dùng đoán.

**`lo_hong()` — thứ luật vùng nén cần.** Một tháng XAUUSD có **26 lỗ**, dài nhất **3.083 phút
(~51 giờ)**, và bốn cái dài nhất đều là cuối tuần. Đây chính là bằng chứng cụ thể cho §12.6:
không cắt vùng nén ở lỗ hổng thì máy sẽ đếm "nến liên tiếp" xuyên qua 51 giờ chợ đóng cửa.

**Một cái bẫy đã bắt được lúc chạy thật:** xin một khoảng **rời hẳn** dải đang có mà chỉ tải phần
mới thì dải bị **thủng** ở giữa, và bộ chạy sẽ chạy xuyên qua chỗ thủng mà không biết. `khoang_thieu`
vì thế luôn kéo khoảng trái tới tận đầu dải và khoảng phải từ tận cuối dải — thà tải thừa phần
giữa, vì người dùng đã được báo số MB trước khi bấm.

### 12.12 ✅ BA LỖI CÓ SẴN của cửa sổ tester — ĐÃ SỬA

Không phải rủi ro. Là lỗi chắc chắn, và chúng sẽ giả dạng thành "Python hỏng" đúng lúc đang
debug bộ chạy. Đã sửa xong và **đo bằng thao tác chuột thật** — xem cuối mục.

1. **`file:///` → trang trắng.** `api.py:366` ghi cứng `url=f"file:///{trang}?tester=1"`.
   pywebview coi mọi url mở đầu `file://` là không-local nên **không dựng http server** cho cửa
   sổ đó, mà `dist/index.html` là `<script type="module" crossorigin>` → origin `null` →
   Chromium chặn. Chính `app_web.py:183-186` đã ghi lại đúng bài học này rồi.
   → truyền đường dẫn cục bộ **trần**, không tiền tố `file://`.
2. **`js_api=self` → bấm ✕ trong tester ĐÓNG CỬA SỔ CHÍNH.** Dùng chung một instance `Api` mà
   `self._window` vẫn trỏ cửa sổ chính. → tách `ApiTester` riêng, có `_window`/`_khung` của nó.
3. **`KhungTuVe` giữ đúng MỘT hwnd** → kéo thanh tiêu đề tester kéo nhầm cửa sổ chính.

Thêm một chỗ nữa cùng loại: **`_mo_cua_so_tester` huỷ rồi tạo lại cửa sổ mỗi lần bấm ▶**
→ mất con trỏ, mất zoom, mất vị trí cuộn nhật ký, mất bộ lọc. Mà vòng lặp debug thật là
*sửa → chạy → so*. → cửa sổ còn sống thì **giữ**, chỉ nạp sơ đồ mới rồi bắn `so_do_moi`
xuống; con trỏ neo theo **thời gian nến**, không theo chỉ số.

**Cách sửa** (`api.py`): tách lớp nền `NenCuaSo` giữ `_window` + `_khung` + 7 hàm cửa sổ; `Api`
và `ApiTester` đều kế thừa. Mỗi cửa sổ MỘT thể hiện là hết cả ba lỗi, không phải nhớ kỷ luật gì.
`ApiTester` cố ý HẸP — không lưu chiến lược, không mở hộp thoại file, không đổi cài đặt.
`TitleBar` bên JS dùng lại nguyên vẹn: cầu nối tra hàm theo TÊN trên api của đúng cửa sổ đang
chạy, nên `cua_so_dong` ở tester rơi vào `ApiTester.cua_so_dong`.

**Hai cái bẫy lòi ra lúc sửa, ghi lại kẻo lần sau vấp tiếp:**

1. **`?tester=1` chưa ai đọc.** `api.py` gắn tham số đó vào url từ lâu nhưng không chỗ nào
   trong `webui/src` đọc `location.search`, nên cửa sổ thứ hai dựng lại y hệt trình soạn thảo.
   → một dòng `if` trong `main.tsx`, không cần entry thứ hai cho Vite.
2. **`useKhungCuaSo` nằm ở TRANG, không nằm trong `TitleBar`.** Trang tester vẽ `TitleBar` là
   ra đúng thanh tiêu đề, trông xong hẳn — nhưng **không kéo được, không giãn được**, vì hook
   gắn handler chuột lại ở `App.tsx`. Triệu chứng giống hệt "vá khung hỏng" nên rất dễ đi sai
   hướng. (Trước đó còn một tầng nữa: `_va_khung` hẹn giờ 0,45 s chạy TRƯỚC khi cửa sổ kịp
   `IsWindowVisible` → không tìm ra hwnd → cũng không kéo được. Giờ nó thử lại tới 4 s.)

**Đã đo bằng chuột thật, không phải suy luận:** bấm ▶ hai lần → vẫn đúng **hai** cửa sổ · kéo
thanh tiêu đề tester 300,200 → 400,300 trong khi cửa sổ chính **đứng yên** ở 20,20 · giãn mép
phải 1180 → 1302 px · bấm ✕ trên tester → tester đóng, **cửa sổ chính còn sống**.

### 12.13 Những thứ backend CHƯA CÓ (kiểm kê 2026-08-10)

Cat_Studio là một bộ soạn thảo hoàn chỉnh và một bộ chạy **bằng không**. Phải viết mới:

| Module | Trách nhiệm |
|---|---|
| ✅ `nguon_nen.py` | chỗ **duy nhất** biết MT5 tồn tại. Tải · cache · liệt kê · xoá · MB · `lo_hong()` |
| ✅ `tinh_toan.py` | chỉ báo thuần: mảng nến → mảng `float64`. Warm-up trả **NaN**, không trả 0. Kèm `gop()` (M1 → M5/M15/H1) và `theo_truc()` (đưa cột khung lớn về trục quyết định) |
| ✅ `khop_lenh.py` | mô hình sàn: đường đi 4 điểm, spread, gap. **Tách riêng** vì đây là thứ duy nhất đổi mà đổi cả đường vốn. Hàm THUẦN — không numpy, không sổ lệnh, không đồ thị |
| ✅ `bo_chay.py` | biên dịch sơ đồ → chương trình phẳng, rồi vòng lặp nến |
| ✅ `bo_chay.KetQua` | vật chứa bất biến của một lần chạy (không cần file riêng — nó chỉ là kết quả của `chay()`) |
| ✅ `nhat_ky.py` | bản ghi rỗng chữ + dựng câu theo lô + ghi/đọc `.jsonl` + so hai lần chạy |
| `api_tester.py` | `Api` riêng cho cửa sổ thứ hai |

**Biên dịch sơ đồ MỘT LẦN trước vòng lặp** không phải tối ưu sớm mà là điều kiện sống còn:
`atr_bps(M5, chu_ky_atr)` → "cột số 3", mọi tên tham số → `float`, `flow_map` → danh sách kề
bằng chỉ số nguyên. Vòng chạy sau đó không đụng một chuỗi nào. Không có bước này thì 1–3 triệu
phép đánh giá bằng dict + chuỗi mất 10–30 giây mỗi lần bấm ▶. **Phải đo trên 1 năm thật trước
khi viết giao diện.**

Ngoài ra:

- **Công thức ATR trong `kho/chi_bao.py` đang SAI** — ghi *"theo Wilder"*, nhưng `iATR` của MT5
  (thứ D_02 thật sự gọi) là **SMA của True Range** (`Indicators/Examples/ATR.mq5:83,91`). Sai im
  lặng và dây chuyền: ATR khác → `atr_bps` khác → nến nào là nến nén khác → số nến nén, thời
  điểm xác nhận, đỉnh/đáy vùng, độ lớn 1R, TP lệch hết. **Cài theo MT5** và sửa luôn câu mô tả —
  ngưỡng 7.0 bps được dò ra trên chính con số `iATR` trả về.
  ✅ **Đã sửa mô tả**: `"SMA của True Range (đúng iATR của MT5 — KHÔNG phải Wilder)"`, kèm công
  thức cửa sổ trượt `ATR[i] = ATR[i-1] + (TR[i] − TR[i-period]) / period` trong chú thích. Câu
  cảnh báo nằm ngay trong chuỗi hiển thị chứ không chỉ trong comment — hộp thoại Kho là chỗ
  người ta tra công thức, để cảnh báo ở comment thì không ai thấy. Bộ TÍNH thì vẫn chưa có.
- **Sáu toán hạng khai mà không có nguồn**: `drawdown_pt`, `so_lenh_hom_nay`, `bid`, `ask`,
  `spread`, `gio`, `thu`. Chọn được trong hộp thoại → vẽ ra sơ đồ hợp lệ mà bộ chạy không chạy
  nổi; sơ đồ mẫu tình cờ không dùng nên test vẫn xanh và lỗi này đang trốn. → **cài luôn cả
  sáu**, không đánh dấu "chưa hỗ trợ" (nhãn đó để lâu sẽ mục).
- **Toán hạng vùng nén khi chưa có vùng nào** → trả 0 là lời nói dối lọt qua mọi phép so.
  Không có nguồn thì **điều kiện TRƯỢT** và nhật ký ghi lý do.
- **Lệnh còn sống lúc hết dữ liệu** → đóng theo giá đóng nến cuối, ghi `het_du_lieu`, tách riêng
  trong thống kê.
- `so_lenh.Lenh` cần thêm **đúng hai trường**: `phi` và `lai_tien`. **Không** thêm trường thời
  gian thật — `nen_khop` + mảng nến đã cho ra `datetime` bằng một phép tra bảng, thêm nữa là chép
  cùng một sự thật ra hai chỗ.

### 12.13b Bảng đối chiếu D_02 — 9 chỗ cố ý khác, 4 chỗ ĐỔI SỐ

`tests/test_doi_chieu_d02.py` in ra bảng này mỗi lần chạy. Cột quan trọng nhất là **có đổi số
không** — thiếu nó thì chín dòng trông ngang nhau, trong khi chỉ bốn dòng đụng tới kết quả, và
đúng bốn dòng đó mới cần lôi ra xem lại khi số không khớp MT5.

| # | Chỗ khác | Đổi gì |
|---|---|---|
| 3 | Kiểm lại bề rộng vùng mỗi nến (bản gốc chỉ kiểm một lần) | **SỐ LỆNH** — ta ra ít hơn |
| 5 | Manage nhịp M1 (bản gốc chạy hoà vốn mỗi tick) | **GIÁ & P&L** — ta lỗ nhiều hơn |
| 6 | Vùng nén chết khi gặp khoảng trống dữ liệu | **SỐ LỆNH** — bỏ vùng bắc cầu cuối tuần |
| 7 | Mô hình khớp: đường đi 4 điểm · spread · gap ở giá mở cửa | **GIÁ & P&L** — bản gốc không có spread |
| 1, 2, 4, 8, 9 | id thay `HasOpenPosition` · `vung_id` thay đóng băng vùng · đồ thị thay máy trạng thái · id thay magic · bỏ `CalcLot` nói dối | không |

Hai bài kiểm neo bảng này vào code thật để nó không trôi thành văn viết cho vui: **R4** đòi nhịp
mẫu đúng M5/M1, **R5** đòi `rong_vung_atr` vẫn nằm trong cổng vào lệnh.

### 12.13c Gộp khung — đã đối chiếu với MT5

Gộp theo **BIÊN THỜI GIAN TUYỆT ĐỐI** (`t // 300`), KHÔNG phải đếm 5 nến một cụm. Dữ liệu M1
thật đầy lỗ hổng, nên đếm cụm thì chỉ cần một nến thiếu là mọi nến M5 sau đó lệch pha khỏi biên
thật của sàn — và không có gì báo cho biết.

**Đã đối chiếu trên một tháng XAUUSD thật** với chính nến mà MT5 dựng: 5.994 nến M5 · 1.999 M15
· 501 H1, **lệch OHLC lớn nhất = 0**. Cùng số nến, cùng mốc thời gian, cùng giá.

⚠ **Ô CUỐI CÙNG bị BỎ nếu dữ liệu chưa chạy hết ô.** Đây là thứ phép đối chiếu trên lôi ra:
dữ liệu M1 dừng đúng `2025-12-02 00:00` thì ô M5 `00:00–00:04` chỉ có 1/5 phút, và nến gộp ra
lệch hẳn MT5 (close 4225.331 vs 4225.692). Giữ nó là bộ chạy đọc một cây nến **chưa đóng** như
thể đã đóng — đúng loại lỗi nhìn trước tương lai mà cả kiến trúc này dựng lên để tránh.

Bỏ đúng ô CUỐI, không bỏ ô thiếu phút ở giữa: ô giữa thiếu vài phút vẫn là ô đã đóng thật (sàn
cũng dựng vậy), chỉ ở ô cuối ta mới không biết sau đó còn gì. Chart muốn thấy cây nến đang chạy
lớn dần thì xin `giu_nen_do_dang=True`.

### 12.13d Khớp lệnh — bốn luật đã cài

`khop_lenh.py` cố ý **không biết** `digits` là gì, không biết sổ lệnh, không import numpy. Nó
nhận một lệnh + một nến + spread (đơn vị GIÁ) và trả danh sách sự kiện. Nhờ vậy mọi ca đều kiểm
được bằng con số tính tay.

| Luật | Cài thế nào |
|---|---|
| SL/TP cùng nến | đường đi 4 điểm quyết cái nào tới trước; nến tăng → đáy trước, nến giảm → đỉnh trước |
| Spread | quy mọi mức về Bid MỘT lần: Mua-vào và Bán-ra dịch `− spread`, hai cái kia giữ nguyên |
| Gap | chạm mức ở **bước 0** nghĩa là mở cửa đã ở bên kia → khớp tại giá MỞ CỬA |
| Khớp rồi chết cùng nến | chỉ là hai bước liền nhau trên cùng đường đi, không phải ca đặc biệt |

Hai chi tiết dễ bỏ sót, đã có bài kiểm riêng:

- **SL/TP chỉ được xét TỪ bước khớp trở đi.** Nến tăng `O=99 → L=94 → H=101` khớp Buy Stop 100
  ở bước 2; cái đáy 94 đi qua ở bước 1, TRƯỚC khi lệnh tồn tại, nên không được tính là chạm SL.
  Xét cả nến là để một cái SL chưa tồn tại giết một vị thế chưa mở.
- **Gap qua TP thì tốt hơn mức đặt, gap qua SL thì xấu hơn** — đúng như sàn khớp, và bất đối
  xứng đó là thật chứ không phải thiên vị.

`ca_hai_trong_nen()` đếm số nến mà cả SL lẫn TP đều nằm trong biên độ. Không dùng để quyết định
gì — đường đi đã quyết rồi. Chạy một năm mà con số đó bằng 0 thì có **bằng chứng** kết quả không
phụ thuộc vào giả định đường đi.

### 12.13e Bộ chạy — đã đo trên một năm thật

| | |
|---|---|
| Dữ liệu | XAUUSD M1 2025, **354.503 nến** (16,2 MB) · 271 lỗ hổng, dài nhất 4.388 phút |
| Một lần bấm ▶ | **2,9 giây** → 70.795 nến M5 · 134.067 lượt chạy |
| Kết quả | 548 lệnh · 386 đóng · 162 huỷ · thắng 25,6 % · **tổng −7,5R** |
| **`nen_mo_ho`** | **0** |

`nen_mo_ho = 0` suốt một năm là con số quan trọng nhất bảng này: **không một nến M1 nào có cả SL
lẫn TP nằm trong biên độ**. Nghĩa là kết quả trên KHÔNG phụ thuộc vào giả định đường đi 4 điểm —
đó là bằng chứng, không phải niềm tin (§12.13d).

**Lần đo đầu là 11,5 giây.** `cProfile` chỉ thẳng: `so_lenh.dang_song()` ăn **57 %** thời gian —
nó quét TOÀN SỔ mỗi lần gọi, mà bộ chạy gọi nó trên mỗi nến M1: 354.000 × 550 lệnh = **195 triệu**
phép kiểm. Bộ chạy giờ tự nuôi danh sách lệnh đang sống, O(1–3) mỗi nến → **2,9 s**, và kết quả
**giống hệt tới từng con số** (550 lệnh, 99 thắng, 289 thua, −9,5R, 135.010 lượt) — đó mới là bằng
chứng tối ưu không đổi hành vi.

Nuôi danh sách ở BỘ CHẠY chứ không sửa `so_lenh`: đó là chuyện tốc độ của vòng lặp, không phải
chuyện mô hình sổ lệnh.

*(Bảng trên là số SAU khi sửa lỗi khung giờ ở 12.13e-bis. Trước đó là 550 lệnh · −9,5R, và phép
so "giống hệt tới từng con số" của tối ưu `dang_song` được đo trên bộ số cũ đó — nó vẫn đúng: tối
ưu không đổi hành vi, cái đổi số là lỗi dưới đây.)*

#### 12.13e-bis ⚠ LỖI THẬT: toán hạng GIÁ bỏ quên khung thời gian
> **⚠ MỤC NÀY GHI "ĐÃ SỬA" NHƯNG VÁ HỤT — xem §13.0a.** Đợt vá dưới đây mới làm 2/3 bước: dựng
> đúng cột và đúng khoá, nhưng quên sửa chỗ ĐỌC, nên cột dựng ra không ai dùng. Con số 3,48 % và
> bảng §12.13e đều đo trên mã còn lỗi.

Tìm ra lúc dựng bảng số liệu tổng quát, không phải lúc tìm lỗi.

`close(M15, nến[1])` **đọc thẳng `nen5`** — tức nến M5. Nên cổng xu hướng đang so **Close M5 với
MA M15**, trong khi D_02 so `Close[1]` với `MA[1]` **cùng khung Trend** (`FilterEngine.mqh:324`).
Chỉ báo thì đã đúng từ đầu (chúng đi qua `_xin_cot`); riêng bốn toán hạng giá
`close/open/high/low` đi đường tắt.

Hai chỗ sửa, cả hai nằm ở `bo_chay.ChuongTrinh`:

1. `_xin_cot_gia` — toán hạng giá cũng **xin một cột riêng cho khung của nó**, rồi đưa về trục
   quyết định bằng đúng cách chỉ báo vẫn làm (giá trị của nến khung lớn **đã đóng** gần nhất).
2. `khoa()` gán `period=None` cho toán hạng giá. Để mặc định 14 chui vào khoá thì `close(M15)`
   thành `('close','M15',14.0,None)` — vô nghĩa, và đụng ngay nếu sau này có toán hạng giá thật
   sự nhận chu kỳ.

Cùng lúc chốt luôn nghĩa của `shift`: **đếm ngược từ nến ĐÃ ĐÓNG**. Mọi cột ở đây vốn đã là "giá
trị của nến đã đóng gần nhất", nên `nến[1]` (quy ước MT5) chính là **lệch 0**.

Đo mức lệch: trung bình **1,34**, lớn nhất **56**, và **chiều xu hướng khác nhau trên 3,48 % số
nến**. Thống kê cuối tình cờ không đổi mấy (548 lệnh, 99T/287B, −7,5R) — nhưng "tình cờ không đổi
mấy" không phải là lý do để giữ một phép so sai khung.

### 12.13f Nhật ký — đã chạy trên dữ liệu thật

Dựng chữ cho lô 14 dòng đang nhìn mất **0,6 ms**; 8.020 bản ghi không tốn một byte chữ nào lúc
chạy. Ghi ra `.jsonl` (3,3 MB) mất 0,06 s, đọc ngược lại đủ cả lệnh lẫn lượt.

```
11-05 19:00  ENTRY   [1]→[2]→[3]→[3A]→[3A.1]  đặt Mua L-0001 @3986.33  SL 3982.42  TP 3994.15
11-06 11:45  MANAGE L-0003  [1]→[1B]→[1B.1]   sửa L-0003 · Dời SL về hoà vốn → SL 4013.73
11-07 05:55  MANAGE L-0004  [1]→[1A]→[1A.1]   huỷ lệnh chờ L-0004
11-20 03:00  ENTRY   [1]  hết lượt tại [2] · ATR chuẩn hoá (bps)(M5, 14) = 21.44, không < 7.00
11-02 23:00  ENTRY   [1]  hết lượt tại [2] · ATR chuẩn hoá (bps)(M5, 14) chưa có dữ liệu
```

**Ba chỗ hỏng mà vẫn "trông có vẻ chạy", đã bắt được và có bài kiểm riêng:**

1. **`Lenh.tom_tat()` có sẵn khoá `loai`** (stop/limit/market). Trải phẳng nó vào bản ghi là
   ĐÈ MẤT nhãn dòng, nên đọc ngược file nhận nhầm 29 lệnh thành 29 lượt — mà **ghi thì vẫn báo
   thành công**. Lồng vào `{"loai": "lenh", "lenh": …}` là hết.
2. **"chưa có số" bị đọc thành "so xong thấy không đạt"** — `NaN` hiện ra là `= —, không < 7.00`,
   nghe như một phép so thất bại. Hai chuyện rất khác nhau lúc debug, giờ tách hẳn thành
   `"… chưa có dữ liệu"`.
3. **Vân tay chỉ hash các KHỐI**, không hash cạnh và tham số — hai sơ đồ cùng bộ khối mà nối
   khác nhau lại ra cùng vân tay, tức "so hai lần chạy" sẽ nói "sơ đồ không đổi" trong khi nó đã
   đổi hẳn. Giờ hash cả cạnh lẫn bảng tham số, và vẫn bỏ `pos` (kéo khối không đổi logic).

### 12.15 ✅ Giao diện tester — đã chạy thật trong cửa sổ

```
 thanh công cụ   ⚙ ▶Chạy │ ⏮ ◀ ▶ ▶ ⏭  delay 60ms │ 🔍+ 🔍− ✛ Nến▾ M5▾ │ 2025-01-02 12:45
 dải tóm tắt     550 lệnh · 99T/289B · thắng 25.5% · tổng −9.5R · vốn 9966.93 · nến mơ hồ 0
 ┌──────────────────────────── chart ──────────────────────┬─── bảng số liệu ───┐
 │  nến M5 · CHỈ vẽ lệnh · crosshair                        │ toán hạng đang dùng│
 │  ▲──────▼  lệnh đã xong (hai mũi tên + vạch nối)         │ vùng nén (engine)  │
 │  ▲────    lệnh đang sống                                 │ tài khoản          │
 │  ┄┄┄┄┄┄   lệnh chờ: 3 đường entry · TP · SL              │ lệnh đang sống     │
 ├──────────────────────────── nhật ký (ảo hoá) ────────────┴────────────────────┤
 │ 01-02 12:40 MANAGE L-0003 [1]→[1B]→[1B.1] sửa L-0003 · Dời SL về hoà vốn …    │
 └───────────────────────────────────────────────────────────────────────────────┘
```

**Ba vùng đọc CÙNG MỘT con trỏ `j`** (chỉ số nến M1), nên chúng không thể nói khác nhau. Xem thì
trượt liên tục, debug thì bấm một dòng nhật ký để nhảy mốc — cùng một con trỏ, hai cách di chuyển.

**Đã đối chiếu bằng mắt trên dữ liệu thật**, đúng cái mà bản phản biện lo nhất: bấm dòng
`MANAGE L-0003 · Dời SL về hoà vốn` thì bảng phải hiện `L-0003` gắn chấm *hoà vốn*, `SL = giá vào
= 2643.067`, và `Vùng này đã sinh lệnh = đúng`. **Bảng và nhật ký khớp nhau**, vì bảng dựng từ
CỘT đã ghi lúc chạy chứ không hỏi lại sổ lệnh.

**Ba chi tiết đáng ghi:**

- **Chart nhận đúng `{nen, lenh}`** và không có đường nào chạm tới bảng số liệu — luật "tuyệt đối
  không indicator trên chart" được ép bằng KIỂU DỮ LIỆU, muốn vi phạm phải sửa chữ ký hàm.
- **Gộp M1 → khung vẽ làm ở JS, cố ý và có giới hạn.** Python vẫn là nguồn sự thật cho mọi con số
  đi vào QUYẾT ĐỊNH (`tinh_toan.gop`); JS chỉ gộp OHLC để VẼ. Nhờ vậy kéo con trỏ trong một nến M5
  thì cây nến cuối LỚN DẦN mà không phải hỏi Python 20 lần một giây.
- **Nhật ký ảo hoá tự viết ~40 dòng**, chiều cao dòng cố định (hằng `CAO` trong `Journey.tsx` PHẢI
  khớp `.nk-dong` trong `app.css`). 135.000 dòng đổ thẳng vào DOM là treo hẳn WebView2.

**Một lỗi bố cục bắt được lúc soi ảnh:** bảng "Lệnh đang sống" thiếu `table-layout: fixed` nên bốn
cột số dính liền thành `2643.0672643.0672647.8181.19` — đọc ra một con số vô nghĩa, mà đây lại
đúng là bảng người dùng nhìn để đánh giá. Nhãn "hoà vốn" cũng đổi thành một CHẤM: thêm một chữ
nữa trên hàng là vỡ cả bảng, còn thông tin thì rê chuột vẫn đọc được.

### 12.16 ⭐ PHÁT LẠI — sửa một hiểu sai của tôi

Bản đầu tôi dựng một **trình xem lịch sử**: mở ra là mọi lệnh đã vẽ sẵn đủ hình hài, con trỏ thả
vào giữa. Nhìn thì có vẻ xong. Nhưng người dùng nói thẳng: *"tín hiệu pending, tín hiệu vào vì bạn
vẽ sẵn hết rồi nên tôi cũng không kiểm tra được"* — và đúng.

> **Cốt lõi là KHOẢNH KHẮC**: lệnh chờ hiện ra, giá bò tới, khớp, SL dời về hoà vốn, chốt — với
> nhật ký tự chạy và chỉ báo nhảy số cùng nhịp. Vẽ sẵn là giết đúng thứ đó.

**Vòng đời giờ là:** bấm ▶ ở cửa sổ vẽ → **thanh tiến trình** (backtest chạy trên luồng nền) →
phát lại **từ đầu**, nến hình thành từng cây.

| Việc | Cách làm |
|---|---|
| Nến lớn dần | `series.update()` mỗi nhịp M1 — cây nến khung hiển thị phình ra qua 5 nhịp |
| Trục thời gian · kéo ngang · zoom | `lightweight-charts` của TradingView |
| Lệnh hiện đúng lúc | vẽ theo **trạng thái TẠI CON TRỎ**, không phải trạng thái cuối |
| Nhật ký sống | dòng nảy lên đúng nhịp nó xảy ra, tự cuộn khi đang phát |
| Nhảy tới sự kiện | `test_luot_ke` — không ai xem hết 71.000 nến buồn tẻ để đợi một lệnh |
| Tốc độ | 0,25× → 16× |

**Dùng thư viện ngoài, có cân nhắc.** `lightweight-charts` là dependency đầu tiên ngoài React và
React Flow. Ba thứ thiếu — trục thời gian, kéo ngang, zoom — đều là bài đã có lời giải; tự viết
lại là ~400 dòng để đổi lấy một bản kém hơn. Bundle tăng 583 KB (gzip 189 KB), chấp nhận được.

**KÉO THEO LÔ, không hỏi từng khung hình.** Phát ở 60 ms/nhịp mà mỗi nhịp gọi cầu nối hai lần là
~33 lời gọi/giây; `evaluate_js` đồng bộ và payload mã hoá hai lần, nên phát sẽ giật — mà nhịp đều
mới là thứ quan trọng nhất khi xem nến hình thành. `test_doan(j0, 300)` mang đủ mọi thứ ba vùng
cần cho 300 nhịp: **9 ms, 171 KB**. Lô kế nạp trước khi dùng hết 2/3.

**Ba lỗi bắt được lúc soi ảnh chạy thật:**

1. **Chart lộ tương lai TRONG một lô.** Nó vẽ lệnh theo `trang_thai` cuối cùng, mà lô mang cả sự
   kiện còn ở tương lai (tới 300 nhịp = 5 giờ) — nên bảng nói "L-0006 đang sống, −0,81R" trong khi
   chart đã vẽ nó đóng ở −1,00R. Đúng cái bệnh "vẽ sẵn" vừa chữa, chỉ nhỏ hơn. Giờ chart nhận
   `tBayGio` và tự suy trạng thái tại đó.
2. **Nhật ký dựng lại 400 dòng mỗi nhịp** kéo nhịp phát từ 60 ms xuống ~190 ms. Chỉ dựng lại khi
   CÓ dòng mới — mà lượt mới thì 5 nhịp mới có một lần.
3. **Cài đặt bị JS nhớ** từ lúc mở cửa sổ (xem §12.11).

### 12.17 BẢNG MÀU CỦA CHART — ba tầng, ba nghĩa

Bản trước có **ba thứ dùng chung một cặp màu**: nến xanh/đỏ, hướng lệnh xanh/đỏ, lãi/lỗ xanh/đỏ.
Một cặp màu mang ba nghĩa thì chẳng còn nghĩa nào — người dùng nói thẳng *"màu xanh đỏ đang khó
nhìn vì nến cũng cùng màu đó"*.

| Tầng | Màu | Nghĩa DUY NHẤT |
|---|---|---|
| Nến | **xám** — tăng rỗng viền sáng, giảm đặc tối | bối cảnh. Giá là thứ XẢY RA |
| Mức lệnh (vào · SL · TP) | **cam** `#ffa657` | "chỗ TA đặt" |
| Kết quả (thắng/thua) | **xanh / đỏ** | và chỉ có nghĩa này |

Làm nến im đi không phải để đẹp: để lúc không có lệnh thì chart lặng như tờ, lúc có lệnh thì mắt
bị kéo tới ngay. **Hướng mua/bán không dùng màu nữa — dùng HÌNH:** ▲ mua, ▼ bán.

| Trạng thái | Vẽ gì |
|---|---|
| Chờ | 3 đoạn cam: vào (gạch đứt) · TP, SL (chấm) — **chỉ trong quãng lệnh sống** |
| Khớp | ▲/▼ cam tại nến khớp · SL, TP cam vẫn treo |
| Đóng | **vạch nối vào→ra** xanh/đỏ + ô vuông `L-0007 −1.00R` |
| Huỷ (nén tan) | `✕` **xám** — không thắng không thua, không đụng màu kết quả |

**Phông ZONE — xám, và LAM RẤT NHẠT khi đã hợp lệ.** Zone không phải một mức lệnh, cũng
không phải một kết quả, nên nó không được mượn màu của ai. Xanh **dương** là màu duy nhất
còn trống trên chart (`#6cb6ff`, lấy từ `--group` sẵn có — không đẻ màu mới):

```
zone thường   nền rgba(255,255,255, 0.05)   viền rgba(255,255,255, 0.14)
zone HỢP LỆ   nền rgba(108,182,255, 0.07)   viền rgba(108,182,255, 0.22)
```

⚠ **Giữ dưới 0.1 là ràng buộc, không phải gu.** Zone là phông; đậm lên một chút là nó
tranh mắt với đường lệnh cam, mà cam mới là "chỗ TA đặt". `tests/test_giao_dien.py` đọc
thẳng alpha trong `Chart.tsx` và chặn cả ba: quá đậm · mượn cam · mượn xanh lá/đỏ.

Cờ hợp lệ đi kèm **từng bản ghi zone** (`[t_mở, t_nến, đáy, đỉnh, hợp_lệ]`), đọc từ cột
`zone_hop_le` **ghi lúc chạy** chứ không tính lại ở JS — nên lúc phát lại, zone **đổi màu
đúng cây nến nó vừa hợp lệ**, không phải tô sẵn. Sơ đồ chưa khai phần *hợp lệ* thì cột
vắng mặt và mọi zone giữ nguyên màu trung tính: chưa định nghĩa thì không có gì để tô.

⚠ `bo_chay` ghi cột này **ngay khi cổng zone có `dk_hop_le`**, kể cả khi không cổng nào
hỏi tới nó — chart không phải một điều kiện trong sơ đồ nên `toan_hang_dung` không thấy
nó. Thiếu dòng đó thì zone hợp lệ vẫn xám ở đúng những sơ đồ khai nó mà chưa dùng.

**Hai thứ sửa được nhờ đổi `createPriceLine` → `LineSeries`:**

1. **Đường không còn kéo suốt chart.** `PriceLine` luôn full-width, nên ba đường của một lệnh đặt
   lúc 09:00 cũng chạy ngược về 06:00 — quãng nó chưa tồn tại. Nhiễu, và nói dối.
2. **Vạch nối vào→ra quay lại** (§12.10 có, bản lightweight-charts đầu làm rơi). Nó chính là chỗ
   mang màu kết quả: dốc lên xanh, dốc xuống đỏ, nằm ngang = hoà vốn.

**Đường SL vẽ theo LỊCH SỬ**, dựng từ chính nhật ký (`lenh_sua`), nên lúc `Dời SL về hoà vốn` chạy
thì nó **nhảy bậc** ngay trên chart — khoảnh khắc đáng kiểm chứng nhất, mà bản trước chỉ vẽ SL
cuối cùng nên nó tàng hình. ⚠ Điểm đầu KHÔNG được lấy `Lenh.sl`: đó là SL HIỆN TẠI, đã bị mọi lần
dời ghi đè — lấy nó làm điểm đầu là ra một đường phẳng và cái bậc biến mất. Nay điểm đầu lấy thẳng
từ bản ghi `lenh_dat` trong nhật ký (§12.9d), chính xác và dùng được cho cả TP.

### 4.5 ✅ THÊM KHỐI TỪ CHIẾN LƯỢC KHÁC — nhập chồng, không thay

`Mở ▾ → Thêm khối từ chiến lược khác…` (và mục cùng tên trong menu File). Chữ **thêm** để phân
biệt hẳn với *"Mở chiến lược (thay toàn bộ)"* ngay bên trên — hai thứ này mà lẫn nhau thì một cú
bấm nhầm xoá sạch sơ đồ đang làm dở.

**Nhập = DÁN từ file.** Máy móc đã có sẵn: `Ctrl+V` vốn cấp id mới, giữ nối *giữa những khối được
chép*, thả cả cụm giữ nguyên khoảng cách tương đối, chọn sẵn cả cụm, và `chup()` trước nên **một
Ctrl+Z hoàn tác cả mẻ**. Đã tách phần đó ra thành `thaCum(buoc, canh, taiDay, ts)` dùng chung —
viết hai lần thì sớm muộn một bên quên remap id hoặc quên `chup()`.

**"Không đánh số" không phải thứ phải cài — nó là HỆ QUẢ.** Số do Python tính bằng phép duyệt từ
khối Bắt đầu; khối vừa nhập chưa có đường nối nào dẫn vào nên nằm ngoài phép duyệt và hiện `–`.
Kèm theo, bảng Vấn đề gọi chúng là *"không bao giờ chạy tới"* ở mức **cảnh báo** (không phải lỗi),
nên ▶ Chạy vẫn bấm được. Nối vào là số hiện ra ngay.

**Hai thứ bị lọc, cả hai đều là luật:**

- **Bỏ khối Bắt đầu của nguồn** — sơ đồ đang mở đã có một cái, hai khối Bắt đầu là sơ đồ hỏng.
- **Chỉ nhập CÙNG TAB** — toán hạng nhóm "Lệnh này" chỉ tồn tại ở Manage, nên bê một khối Manage
  sang Entry là tạo ra khối không soát nổi. Đây là luật, không phải làm cho gọn.

**⚠ THAM SỐ PHẢI ĐI THEO.** Khối tham chiếu tham số bằng **TÊN**. Nhập một khối dùng
`nguong_nen_bps` vào chiến lược không có tham số đó thì khối trông vẫn bình thường trên canvas,
nhưng bấm ▶ mới ném `"Bảng tham số thiếu nguong_nen_bps"` — và không ai đoán ra vì sao. Nên
`import_steps` trả kèm đúng những tham số đám khối đó **thật sự đọc**, quét bằng chính
`core._tham_so_dang_dung` mà validator dùng (một `doc` giả chỉ chứa đám khối đó) — viết bộ quét
thứ hai là sớm muộn hai bên hiểu khác nhau.

> **Tên ĐÃ CÓ thì GIỮ NGUYÊN giá trị hiện tại, không đè.** Đè lên là lặng lẽ đổi hành vi của cả
> chiến lược đang làm dở chỉ vì vừa nhập một khối. Nhật ký ghi rõ đã giữ cái nào và nguồn ghi bao
> nhiêu.

#### 4.5b ⚠ Lỗi có sẵn của Ctrl+V, lộ ra nhờ tính năng này

`clone_steps` dựng thẻ bằng `_the_buoc(s)` — **không có bảng tham số**, nên thẻ ghi
`nguong_nen_bps = ?`. Ctrl+V dính từ đầu, chỉ ít ai để ý vì thường dán ngay trong cùng một sơ đồ
và mắt đã quen con số ở khối gốc. Nhập từ file thì cả cụm 6 khối hiện `?` — trông như hỏng hẳn.

Sửa: `clone_steps(steps, tham_so)`. Với lần **nhập** phải truyền bảng **ĐÃ GỘP**, vì tham số vừa
thêm chưa nằm trong `thamSo` của lần render đang chạy — gộp trước, thả cụm sau.

### 4.6 ✅ MÀU KHỐI THEO MỤC ĐÍCH

Trước đây `dai-mau` chỉ có hai màu: xanh cho Bắt đầu, **cam cho MỌI khối hành động** — nhìn xa thì
Kiểm tra ĐK, Vào lệnh, Sửa lệnh giống hệt nhau.

`api._mau_khoi(st)` gắn vào thẻ một **khoá ngữ nghĩa**, không phải mã màu: `start · hoi · mua ·
ban · sua`. Suy từ `type` + `huong` — phạm trù của chính app, không phải khái niệm riêng của một
chiến lược, nên chiến lược nào sau này cũng ra màu đúng. Giao diện ánh xạ khoá → biến CSS, nên đổi
bảng màu là việc của CSS.

| khối | màu | vì sao |
|---|---|---|
| Bắt đầu | xám `--action` | ĐIỂM NEO, không phải hành động |
| Kiểm tra ĐK | lam `--khoi-hoi` | một câu hỏi |
| Vào lệnh · Mua | xanh `--ok` + ▲ | |
| Vào lệnh · Bán | đỏ `--err` + ▼ | |
| Sửa lệnh | tím `--khoi-sua` | không đụng `--warn`/`--accent` đã có nghĩa khác |

**Khối Bắt đầu phải bỏ màu xanh.** `--start` và `--ok` trùng đúng một mã `#4ec96a`, nên để khối Mua
màu xanh mà giữ nguyên Bắt đầu thì hai loại khối nhìn y hệt nhau. Trả xanh về đúng MỘT nghĩa: mua.

**Nền dải tiêu đề nhuộm 10% mới là thứ quyết định, không phải cái thanh.** Ở mức thu phóng 67% —
mức hay dùng để nhìn cả sơ đồ — thanh 3px chỉ còn 2px và gần như biến mất; một dải nhuộm thì vẫn
quét mắt ra được. Thanh cũng được kéo cao hết dải tiêu đề thay vì 15px giữa chừng.

**Hướng dùng HÌNH ▲/▼ chứ không chỉ dùng màu** — cùng ngôn ngữ với chart (§12.17), và đọc được cả
khi mù màu.

Cái lợi kèm theo: cam đang mang hai nghĩa cùng lúc — "khối hành động" và "đang chọn · số thứ tự".
Đẩy khối hành động sang màu riêng thì **cam chỉ còn nghĩa *của ta · đang chọn***, viền chọn nổi hẳn.

Thân khối, viền, phông chữ, huy hiệu: **không đổi một pixel**.

### 12.23 ✅ Bỏ nút "Tải thêm" — ▶ Chạy tự tải phần còn thiếu

Luật cũ ghi ở `nguon_uoc_tinh` là *"không bao giờ tải lén"*, và nó đẻ ra một nút. Luật vẫn đúng,
chỉ là cách giữ nó sai: luật đúng phải là **"không bao giờ tải mà không NÓI"** — thanh tiến trình
nói ra là đủ, không cần bắt bấm thêm một bước.

Giờ `▶ Chạy` → `_tai_neu_thieu(symbol, tu, den)`:

- `khoang_thieu` rỗng → **không đụng tới MT5 một lần nào**, chạy luôn.
- Có thiếu → tải **đúng phần thiếu** (tải bổ sung, không tải lại từ đầu), chữ chạy vào chính thanh
  loading đang có: `đang tải nến XAUUSD từ MT5 (≈4.1 MB)…` rồi `đang chạy 210.000/353.129 nến`.

**Số MB thay cho hộp xác nhận.** Gõ nhầm `2015` thay vì `2025` thì thấy ngay `≈171.95 MB` mà đóng
lại — không cần một hộp `confirm` nào, đúng thứ vừa bỏ đi.

**Lỗi phải tự nói ra đang thiếu gì.** Trước đây lỗi MT5 rơi vào nút "Tải thêm" nên tự nó đã rõ;
giờ nó rơi vào GIỮA một lần chạy. Đã kiểm bằng cách tắt `CO_MT5`:

```
Thiếu nến XAUUSD khoảng 2010-01-01 00:00 → 2016-08-09 00:00 và không tải được.
Máy chưa cài thư viện MetaTrader5 (pip install MetaTrader5).
```

**⚠ Xin XA hơn thứ nguồn có thì phải DỪNG, không được chạy tiếp.** Tải xong mà đầu khoảng vẫn
thiếu nghĩa là MT5 không có dữ liệu xa tới thế. Hai lý do phải ném lỗi:

1. chạy tiếp trên khoảng ngắn hơn thì người dùng tưởng mình đang backtest từ 2015 trong khi thật
   ra từ 2016;
2. khoảng đó **không bao giờ lấp được**, nên mỗi lần bấm ▶ lại mở MT5 tải lại một lượt vô ích —
   cái giá này chỉ xuất hiện *từ khi bỏ nút "Tải thêm"*, trước đó người dùng chỉ bấm Tải một lần
   rồi thôi.

Chỉ xét ĐẦU khoảng. Thiếu ở đuôi là chuyện thường (dữ liệu chỉ có tới hôm nay), chặn là vô lý.

```
MT5 không có nến XAUUSD sớm tới 2010-01-01 00:00.
Nguồn chỉ có từ 2016-08-09 00:00 đến 2026-01-02 00:00.

Sửa ô "Từ" ở Cài đặt → Strategy Test thành 2016-08-09 trở đi rồi chạy lại.
```

**Nút Xoá trong bảng nguồn thì Ở LẠI.** Tải là an toàn và đảo ngược được nên tự động; xoá thì
không, phải do tay người bấm.

### 8.4 ⚠ LỖI: ba nút hộp thoại file đều chết vì một hằng số sai kiểu

*"nút mở từ file khác, duyệt từ file khác đang không dùng được."*

`_LOC` khai là **tuple** `("Chiến lược Cat_Studio (*.json)", "*.json")`, rồi truyền
`file_types=(self._LOC,)`. pywebview đòi mỗi bộ lọc là một **CHUỖI** đúng dạng `Mô tả (*.đuôi)`
và tự tách lấy đuôi — đưa tuple vào thì `parse_file_type` ném `TypeError: expected string, got
'tuple'` **ngay, trước cả khi hộp thoại kịp mở**.

Một hằng số sai kiểu giết **ba** nút cùng lúc, vì cả ba dùng chung nó: *Mở từ file khác…* ·
*Duyệt file khác…* (trong hộp chọn chiến lược) · *Lưu ra file khác…*.

**Vì sao im lặng suốt:** `_bat_loi` bắt gọn ngoại lệ thành `{ok: false, error: …}`, và JS có báo —
nhưng báo vào **bảng Nhật ký ở dưới**, chỗ người dùng đang không mở. Bấm nút thì thấy *không có gì
xảy ra*. Lỗi được xử lý đúng mà vẫn vô hình: chỗ báo lỗi phải nằm nơi người ta đang nhìn.

Sửa: `_LOC` thành một chuỗi. Nhân tiện đổi `webview.OPEN_DIALOG`/`SAVE_DIALOG` sang
`webview.FileDialog.OPEN`/`.SAVE` — pywebview đã in cảnh báo *"will be removed in a future
version"* ngay trên stderr, cùng giá trị 10/30.

Đã bấm thật cả hai: hộp `Open` và hộp `Save As` đều hiện ra, Esc huỷ xong app vẫn chạy.

### 13.0 ✅ ĐỢT SOÁT TRƯỚC ĐÓNG GÓI — 7 chỗ đã sửa

Soát 5 hướng song song (logic sơ đồ · đúng số · dữ liệu · cầu nối · phòng thủ & đóng gói), mỗi
phát hiện nặng qua một vòng phản biện. 25 phát hiện thô → 8 cái nặng nhất đưa đi phản biện → 8
sống sót. Hai cái nặng nhất tự tái hiện lại bằng tay trước khi sửa.

#### ⚠ 13.0a Toán hạng giá — VÁ HỤT LẦN ĐẦU, nay mới xong

§12.13e-bis ghi là "ĐÃ SỬA". **Sai: mới làm 2 trong 3 bước.** Đã dựng đúng cột theo khung
(`_xin_cot_gia`) và đúng khoá (`khoa`) — nhưng **quên sửa chỗ ĐỌC**: `_lay_toan_hang` vẫn gọi
`ctx.gia_nen`, mà `gia_nen` đọc thẳng `ct.nen5`. Cột dựng ra không ai dùng. Thuốc pha xong không
ai uống.

Đo lại trên một tháng thật: **66,5 % số nến trả sai số**, lệch tối đa 11,37 — chứ không phải
3,48 % như §12.13e-bis ghi, vì lần đó tôi đo *chênh lệch giữa hai cột*, không đo *thứ cổng thật sự
đọc*. Và có **hai lỗi chồng nhau**: sai mảng, cộng thêm sai quy ước `shift` (`gia_nen` hiểu là lùi
`shift` nến, `doc_cot` hiểu `nến[1]` là lệch 0).

Sửa: gọi **y hệt đường chỉ báo** — `ct.doc_cot(o, ctx.i, o.get("shift", 0))`. Cùng một dạng gọi thì
hai vế của một cổng mới cùng quy ước. KHÔNG đụng `ctx.gia_nen`: `kho/engine_d02` dùng nó nuôi vùng
nén, mà vùng nén sống trên trục quyết định nên đọc `nen5` ở đó là ĐÚNG.

**Số thật đổi theo:** 548 lệnh · −7,50 R · DD 0,79 % → **547 lệnh · −10,50 R · DD 0,91 %**. Bảng
§12.13e là đo trên mã còn lỗi.

**Vì sao 9/9 vẫn xanh suốt:** không bài nào soát GIÁ TRỊ LÚC CHẠY của một toán hạng giá —
`test_doi_chieu_d02` cố ý chỉ soát *tờ khai* (docstring của nó ghi rõ), còn `test_bo_chay` chưa
chạm tới. Đã thêm mục 7 vào `test_bo_chay`: tự gộp M15 từ mảng M1 thô rồi tra tay nến M15 **đã
đóng** gần nhất — một sự thật ĐỘC LẬP, không mượn gì của bộ chạy. Kèm một phép chốt "giá trị phải
KHÁC close M5 ở phần lớn nến", vì nếu ai đó lại làm cả hai đường cùng đọc `nen5` thì phép so đầu
vẫn khớp.

#### ⚠ 13.0b drawdown_pt bỏ sót lệnh do khối "Đóng hẳn" đóng

`ghi_tien` là closure trong `chay()`, `_sua_lenh` là hàm MODULE nên với không tới. Nhánh `dong_han`
đóng lệnh xong không ghi tiền → `drawdown_pt` **lúc chạy** đọc 0 % trong khi sụt giảm thật đã mấy
chục phần trăm. Toán hạng đó chính là thứ người ta dùng làm **cầu dao** ("sụt giảm > 10 % thì ngừng
vào lệnh") — cầu dao chết im lặng. Bảng thống kê cuối vẫn đúng (`_thong_ke` tự duyệt lại sổ lệnh),
nên hai nơi nói hai con số khác nhau.

Sửa: gắn `ct.ghi_tien = ghi_tien`, gọi trong nhánh `dong_han`. Sơ đồ mẫu dùng `hoa_von`/`huy_cho`
nên bộ số của nó không bị mục này ảnh hưởng.

⚠ Bài kiểm đầu tiên tôi viết **BỎ LỌT** con bọ này: nó dùng lại kịch bản giá phẳng 110, nên cả hai
đường cùng ra 0 % và phép so khớp một cách vô nghĩa. Kịch bản phải **có lỗ thật** (vốn nhỏ, lot
lớn, giá rơi đều) thì hai đường mới buộc phải nói cùng một con số khác 0.

#### 13.0c Ghi nến NGUYÊN TỬ + chốt chặn file cụt

`np.save` ghi thẳng lên file đích, tức **cắt cụt bộ cũ rồi mới ghi lại**. Ngắt giữa chừng để lại
`.npy` cụt còn `.json` meta vẫn mô tả bộ đã mất — rồi `doc()` lặng lẽ trả mảng rỗng trong khi
`khoang_thieu()` (chỉ nhìn meta) khẳng định "đủ rồi", nên app **không bao giờ tải lại**. Tự khoá vào
trạng thái chết; đo được 20/20 lần khi kill đúng lúc `np.save`.

Hai miếng vá, cùng một file, không đổi định dạng:
`_ghi_nguyen_tu` (ghi `.tmp` → `fsync` → `os.replace`, đổi tên trên NTFS là nguyên tử) và
`file_du(symbol, m)` — một lệnh `stat` so kích thước với `so_nen × itemsize`, thiếu thì coi như
chưa có gì và tải lại. Cái thứ hai còn tự chữa những file ĐÃ hỏng sẵn từ trước.

Tách `file_du` ra thành hàm riêng thay vì viết thẳng trong `khoang_thieu`: bộ kiểm mục 2 cố ý thay
tạm `doc_meta` để soát riêng phần số học khoảng, không đụng đĩa — có hàm riêng thì nó thay tạm được
y như vậy.

#### 13.0d Bốn chỗ còn lại

- **Tên thiết bị Windows** (`CON`/`PRN`/`AUX`/`NUL`/`COM1-9`/`LPT1-9`) — `NUL.json` bị ánh xạ vào hố
  đen ở BẤT KỲ thư mục nào: lưu báo THÀNH CÔNG, `os.path.exists` trả True, mà đĩa không có file;
  `AUX` còn treo cứng lúc đọc lại. Thêm gạch dưới. Giữ tính lũy đẳng để tên lấy từ `liet_ke` đưa
  ngược vào không cộng dồn gạch. Đáng lo vì **"con" là từ tiếng Việt rất hay gặp**.
- **Bỏ `limit` khỏi `LOAI_LENH`** — giao diện cho chọn "Chờ Limit" mà `khop_lenh` không đọc trường
  `loai` một lần nào, và `_vao_lenh` đặt Buy Limit CAO HƠN giá thị trường. Bỏ chứ không cài thêm:
  cài là thêm tính năng, mà một ô chọn lặng lẽ làm việc khác mới là thứ phải dọn.
- **Chặn file schema mới hơn** — `normalize_action` trả None cho `type` lạ và `_chuan_so_do` lọc
  `if x`, nên khối BIẾN MẤT kéo theo cả dây, chuỗi bị cắt đôi, rồi Ctrl+S ghi đè vĩnh viễn.
  `validate_actions` có sẵn câu cảnh báo cho tình huống này nhưng không bao giờ hiện được, vì
  normalize đã xoá khối trước khi validator nhìn thấy. Chặn ở đầu `normalize_process`.
- **Tham số trùng tên** — `bang_tham_so` (dict comprehension) lấy dòng CUỐI, `normalize_tham_so`
  giữ dòng ĐẦU: canvas ghi một đằng, bộ chạy chạy một nẻo, **ngay trong cùng một lần chạy**.
  `validate_process` trước đây gom tên vào một `set` nên nuốt mất chuyện đó. Nay báo mức **error**
  (đủ để chặn ▶ Chạy) và nút Lưu của hộp Tham số bị khoá khi còn trùng.

#### 13.0e Dọn nốt — 6 mục "để sau", làm luôn

- **`lich_su.liet_ke()` nhớ tạm bản gọn theo `ma`.** Trước đây mỗi lần gọi phải đọc và parse TOÀN
  BỘ mọi mục (~69 KB/mục, riêng đường vốn 62 KB) mà danh sách không dùng tới, trong khi mỗi lần
  bấm ▶ gọi 2-3 lượt. Đo được **40 mục: 233 ms → 0,5 ms** (nhanh hơn ~450×). An toàn vì `lich_su`
  là nơi DUY NHẤT ghi/xoá file lịch sử, và cả `_ghi_file` lẫn `xoa` đều dọn bộ nhớ tạm; `liet_ke`
  còn tự bỏ mục nào file đã biến mất ngoài app.
- **Mã mục lịch sử không đè nhau nữa.** Mốc GIÂY thì hai lần chạy khép trong cùng một giây ghi đè
  nhau. ⚠ Bản vá đầu của tôi (thêm phần trăm giây) **không sửa được gì** — 20 lần gọi liên tiếp
  vẫn ra 1 mã, vì cả 20 rơi vào cùng một phần trăm giây. Đừng đoán độ phân giải đồng hồ cho đủ
  mịn: cứ HỎI ĐĨA, trùng thì thêm hậu tố. Khử hẳn, không phải giảm xác suất.
- **`lich_su._gon` dùng `.get` cho mọi khoá.** `liet_ke` chỉ canh `m.get("ma")`, nên một mục thiếu
  `t` ném KeyError và kéo sập CẢ danh sách — mất luôn những mục lành.
- **Lãi nổi của lệnh BÁN đo bằng Ask, không phải Bid** (`_gia_thoat`). Đo bằng Bid là báo lãi cao
  hơn thật đúng một spread; với XAUUSD spread 37 điểm thì đủ để một cổng "lãi ≥ 1R" khớp sớm hơn
  một nhịp, và bảng số liệu hiện một con số mà đóng lệnh ra không được. Gom vào MỘT hàm cho ba chỗ
  gọi (toán hạng · bảng số liệu · hàng lệnh sống) khỏi nói ba con số khác nhau. `Lenh.lai_R` vẫn cố
  ý không biết spread là gì — `so_lenh` là mô hình thuần, quy đổi thuộc về chỗ gọi.
- **`ghi_cai_dat` NÉM lỗi thay vì nuốt.** Trước đây `try/except: pass` rồi vẫn `return s`, nên đĩa
  đầy hoặc mất quyền thì nơi gọi tưởng đã lưu; lần mở sau cài đặt lặng lẽ về mặc định.
- **Ghi JSON nguyên tử cho cài đặt · template · lịch sử** (`luu_tru.ghi_json_nguyen_tu`), cùng cách
  với nến ở 13.0c. Ngắt giữa lúc ghi thì mất bản MỚI, không mất bản CŨ.

#### ✅ 13.0f Sơ đồ mẫu phải có ID CỐ ĐỊNH

Phát hiện lúc kiểm bản dọn, không nằm trong danh sách soát: mở "Sơ đồ mẫu Compress" ba lần thì lịch
sử đẻ **ba dòng trùng hệt nhau**, và `so_hai_lan` lần nào cũng nói *"sơ đồ ĐÃ ĐỔI"*.

`_van_tay` băm cả `id` khối, mà `_so_do_mau()` sinh id ngẫu nhiên mỗi lần gọi → cùng một logic ra
ba vân tay khác nhau.

⚠ **Suýt sửa nhầm chỗ.** Tôi định đi chuẩn hoá đồ thị để bỏ `id` khỏi vân tay — việc lớn, và chạm
vào chuyện "thế nào là cùng một chiến lược". Nhìn lại thì lỗi không nằm ở vân tay: **sơ đồ mẫu là
một HẰNG SỐ, nên nó phải ra y hệt nhau mỗi lần mở.** Sinh id ngẫu nhiên cho một hằng số mới là chỗ
bất thường. Sửa đúng chỗ đó: 4 dòng trong `_so_do_mau`, không đụng `_van_tay`.

Id chỉ cần duy nhất TRONG MỘT tài liệu nên đặt cứng hoàn toàn an toàn, và nhập sơ đồ mẫu vào một sơ
đồ khác thì `clone_steps` vẫn cấp id mới như thường.

Kiểm: 3 lần mở lại và chạy → **1 mục lịch sử**, `so_hai_lan` trả *"y hệt"*. Luồng lưu/mở file vốn
đã đúng từ trước (ids nằm trong file), đã kiểm lại luôn.

### 13.2 ✅ Dọn thư mục gốc

- **`settings.json` ở gốc: xoá.** Của bản cũ, `luu_tru.di_cu()` đã chuyển sang
  `du_lieu/cai_dat.json` từ lâu và từ đó nó nằm không — nhưng ai đọc repo vẫn tưởng nó có tác dụng.
- **`logo/` : xoá.** Trùng byte-for-byte với `assets/` (chỉ khác tên file), không một chỗ nào gọi
  tới. `assets/logo.ico` thì `tools/tao_shortcut.ps1` đang dùng thật nên giữ.
- **`tai_lieu/`**: `core.md` + `D02_Compress_ban_giao.md`. `README.md` ở lại gốc theo lệ.
- **Mọi sản phẩm build vào `dist/`**, kể cả bản `.zip` phát hành — thư mục gốc không giữ thứ gì
  sinh ra từ lệnh build. `build/` thì `tools/dong_goi.bat` tự xoá sau khi nén xong.

#### 13.3 ✅ Gom lõi vào gói `cat_studio/`

Thư mục gốc còn đúng **một file `.py`: `app_web.py`** — điểm khởi động. Nhìn vào gốc là thấy ngay
"chạy cái gì"; "gồm những gì" thì mở gói ra xem.

11 module + `kho/` vào `cat_studio/`, và **import trong gói chuyển sang tương đối** (`from . import
core`, `kho/` dùng `from .. import so_lenh`). Ngoài gói — `app_web.py` và 9 bài kiểm — dùng
`from cat_studio import …`.

⚠ **Chỗ vỡ mà đổi tên import không lộ ra:** `luu_tru` xác định gốc dự án bằng
`dirname(__file__)`. File này giờ nằm TRONG gói, nên nó trả về thư mục gói chứ không phải gốc —
`du_lieu/` bị đẻ vào trong `cat_studio/`, và `webui/dist` tìm không thấy. Thêm một bậc `..`
(`_GOC_MA_NGUON`) là xong, nhưng nếu chỉ chạy `import` để kiểm thì không bao giờ thấy: phải chạy
thật mới lộ. Đây là loại lỗi mà "gom file cho gọn" hay kéo theo.

`__init__.py` cố ý **không re-export gì**: `from cat_studio import core` phải nạp đúng một module,
không kéo cả cây. Nạp `api` là kéo theo numpy và MetaTrader5, mà `tests/test_danh_so` chỉ cần
`core`.

`.spec` chỉ đổi `hiddenimports` thành `cat_studio.kho.*`; `tools/*.bat` không phải sửa gì vì tất cả
đều trỏ vào `app_web.py` ở gốc.

Kiểm: **9/9 bài qua**, đóng gói lại, giải nén sang thư mục khác chạy ra **547 lệnh · −10,50 R ·
DD 0,91 % · vốn cuối 9955,04** — trùng từng con số với trước khi gom.

### 13.4 ⚠ MÁY MỚI KHÔNG TỰ TẢI ĐƯỢC — chuỗi rỗng bị hiểu là "đã đủ"

Cài bản đóng gói lên máy mới, bấm ▶, nhận:

```
RuntimeError: Không có nến nào cho XAUUSD trong khoảng này.
Kiểm tra lại mã symbol và khoảng From→To ở Cài đặt → Strategy Test.
```

Câu lỗi đổ tội cho **mã symbol**, trong khi symbol hoàn toàn đúng. Chuỗi hỏng:

1. Mặc định `test.tu` và `test.den` là **chuỗi rỗng**;
2. `thoi_diem("")` trả `None`;
3. `khoang_thieu` gặp `None` thì trả `[]` — **mà `[]` nghĩa là "đã đủ, khỏi tải"**;
4. `_tai_neu_thieu` về ngay, KHÔNG tải gì;
5. `doc()` trả mảng rỗng → ném câu lỗi nói về symbol.

Một giá trị rỗng đi qua bốn tầng rồi biến thành một câu lỗi nói về chuyện khác hẳn.

⚠ **Đợt soát §13.0 ĐÃ TÌM RA lỗi này** — nguyên văn *"máy trắng bấm ▶ lần đầu: tính năng tự-tải-nến
KHÔNG chạy, và lỗi đổ tội nhầm cho mã symbol"*, xếp mức `vua`. Nó nằm trong 25 phát hiện nhưng rơi
khỏi danh sách 7 mục phải sửa, và tôi không rà lại. Tìm ra rồi vẫn để lọt thì công soát thành công cốc.

**Ba chỗ sửa:**

- **Mặc định khoảng = một năm gần nhất, tính theo HÔM NAY** (`_khoang_mac_dinh()`), không ghi cứng
  một mốc — ghi cứng thì sang năm người mới cài thấy một khoảng đã lỗi thời.
- **Chặn khoảng rỗng ngay ở `_tai_neu_thieu`**, nói đúng bệnh: *"Chưa đặt khoảng thời gian để
  chạy. Mở Cài đặt → Strategy Test và điền hai ô Từ / Đến."*
- **Nút "Kiểm tra kết nối MT5" trong Cài đặt** (`nguon_nen.kiem_ket_noi`). Câu *"sao máy mới không
  tải được?"* trước đây không có chỗ nào trả lời: người dùng chỉ gặp lỗi lúc bấm ▶, mà lúc đó đã
  muộn. Giờ hỏi được TRƯỚC, và câu trả lời nói rõ: nối được chưa · terminal và tài khoản nào · sàn
  có mã đó không — và nếu không có thì **liệt kê mã CÓ THẬT trên sàn đang nối**, bấm một cái là điền.
  Thử tiền tố ngắn dần (6 → 4 → 3 ký tự) vì gõ nhầm một chữ ở giữa là lúc cần gợi ý nhất mà tìm
  theo 6 ký tự lại hụt sạch. Hàm này **không bao giờ ném**: mọi hỏng hóc đều là một câu trả lời.

### 13.1 ✅ ĐÓNG GÓI — đã build và chạy thật

```bat
tools\dong_goi.bat
```

**MỘT lệnh, sáu bước** — theo đúng nếp `tools/build.bat` của Auto_Clicker, vì nếp đó đã trả lời sẵn
mấy câu hỏi mà làm tay hay quên:

1. đóng app nếu đang chạy (không thì PyInstaller không ghi đè được `.exe`);
2. build giao diện web — quên bước này là gói ra một cửa sổ trắng;
3. **chạy bộ kiểm; đỏ thì DỪNG, không đóng gói** — thêm so với Auto_Clicker;
4. PyInstaller theo `Cat_Studio.spec`;
5. kèm `DOC-TRUOC-KHI-CHAY.txt` vào trong gói;
6. nén `Cat_Studio-windows.zip` rồi **xoá `build/`** — thư mục đó chỉ là chỗ làm việc trung gian
   của PyInstaller, để lại chỉ tổ rác thư mục gốc.

Dùng `.venv\Scripts\python.exe` chứ không Python global — cùng lý do Auto_Clicker ghi: gói
`quantconnect-stubs` ở global chiếm namespace `Microsoft`. Mã nguồn đã tự chữa được
(`_uu_tien_namespace_dotnet`, §10), nhưng đóng gói bằng môi trường sạch thì gói nhẹ hơn và không
kéo theo rác.

Ra `dist/Cat_Studio/` — **66 MB · 211 file** — và `Cat_Studio-windows.zip` để đưa sang máy khác.

**Chọn `onedir` chứ không `onefile`** — quyết định, không phải mặc định. `onefile` giải nén TOÀN BỘ
gói (numpy + cây DLL .NET của pythonnet + MetaTrader5) vào thư mục tạm ở MỖI lần mở: vài giây chờ
trước khi thấy cửa sổ, lần nào cũng vậy, mà chẳng đổi lại được gì. `onedir` mở gần như tức thì.

**Hai thư mục, không được trộn** — đây là chỗ dễ hỏng nhất và đã tách hẳn thành hai hàm có tên:

| | hàm | khi đóng gói |
|---|---|---|
| Dữ liệu người dùng | `luu_tru.thu_muc_app()` | cạnh `.exe`, sống lâu hơn tiến trình |
| Tài nguyên đi kèm | `luu_tru.thu_muc_goi()` | `sys._MEIPASS`, xoá lúc thoát |

Trộn hai cái là hỏng theo cả hai chiều: để `du_lieu/` trong `_MEIPASS` thì mất sạch sau mỗi lần
chạy; tìm `webui/dist` cạnh `.exe` thì không thấy vì nó nằm trong gói. Trước đây hai chỗ tự ghép
đường dẫn từ `__file__` — nay cùng gọi `luu_tru.trang_giao_dien()`.

**Đã kiểm bằng cách chạy bản đóng gói thật**, không suy luận:

- mở từ thư mục trắng → cửa sổ hiện đủ giao diện, và `du_lieu/` được tạo **cạnh .exe**;
- chép nến vào rồi bấm ▶ → chạy trọn một backtest một năm, ra **547 lệnh · −10,50 R · DD 0,91 % ·
  vốn cuối 9955,04** — **trùng từng con số** với bản chạy từ mã nguồn. Đó mới là bằng chứng gói
  không làm lệch gì, chứ không phải "mở lên thấy cửa sổ là xong".

`console=False` nên mọi lỗi khởi động phải đi qua MessageBox — `app_web` đã làm thế từ trước cho
thiếu .NET / thiếu WebView2 / xung đột namespace. `upx=False`: nén UPX hay bị antivirus báo nhầm,
không đáng đổi lấy vài MB.

### 12.22 ✅ Ba lối vào tester, một hàm

`▶ Chạy` trên ribbon · `File → Mở Strategy Tester` · phím `Ctrl+R`. Cả ba trỏ về **đúng một hàm**
`chay()` — cùng luật với 4 menu tiêu đề (§8): không tạo hành động mới nào cho một lối vào mới, nếu
không hai nơi sớm muộn cũng lệch nhau.

`ContextMenu` nhận thêm trường `phim` để hiện nhãn phím tắt mờ, dạt phải. Nó CHỈ là nhãn — phím
thật vẫn do chỗ nghe bàn phím lo, menu không tự gắn phím nào.

⚠ **Bấm ▶ lần hai phải KÉO CỬA SỔ LÊN TRƯỚC.** *"tôi đang phải tắt hẳn window test đi
nếu muốn chạy sơ đồ mới."* Cửa sổ còn sống thì §12.12 đã chốt là **giữ** (không huỷ đi
tạo lại, để khỏi mất con trỏ · thu phóng · vị trí cuộn), và JS bắt `so_do_moi` rồi gọi
`chay()` — nên nó **có chạy lại thật**. Chỉ là chạy **sau lưng cửa sổ vẽ**: không thấy gì
nhúc nhích, và nút trông như hỏng.

`mo_live` đã ghi đúng bài học này cho nút ● Live từ trước (*"không có dòng này thì bấm
● Live lúc cửa sổ đang bị lấp sau trông y như nút hỏng"*) — tester bị sót. Thêm
`_khung.keo_len_truoc()`, và **đặt TRƯỚC `_ban`**: `_ban` gọi `evaluate_js` đồng bộ nên
lượt chạy bắt đầu ngay trong đó; đưa cửa sổ lên sau là người dùng mất đúng cái đáng xem
nhất — thanh tiến trình chạy từ đầu.

⚠ **`Ctrl+R` bắt buộc `preventDefault()`**: mặc định của Chromium là **nạp lại trang**, tức mất
trắng sơ đồ đang vẽ dở. Chặn nó lại còn là một cái lợi kèm theo. Đã bấm thật để kiểm chứ không
tin suông — cửa sổ tester mở ra và cửa sổ chính vẫn nguyên, không nạp lại.

### 12.21 ✅ LỊCH SỬ CÁC LẦN CHẠY — không lưu kết quả, lưu thứ ĐẺ RA nó

Nút `⏱ Lịch sử` cạnh logo trên thanh tiêu đề tester (`TitleBar` nhận thêm ô cắm `them`).

**Ý chính.** Bộ chạy tất định và một năm mất 2,9 giây, nên một mục lịch sử chỉ cần chứa **đầu vào**
— sơ đồ đã đóng băng + cài đặt + dấu vết dữ liệu nguồn — kèm một **bản tóm tắt** nhỏ để mở ra là
thấy ngay:

| | |
|---|---|
| Lưu cả `KetQua` | riêng nhật ký đã **3,3 MB** một lần chạy |
| Lưu đầu vào + tóm tắt | **~40 KB** |

Mở một mục → tóm tắt hiện **tức thì**. Bấm `▶` → chạy lại 3 giây và ra **nguyên bộ phát lại**
(chart · nhật ký · bảng số liệu · tua đi tua lại), không phải một tấm ảnh chụp chết. Chỉ làm được
thế vì `so_lenh.py` hứa *"chạy lại cùng dữ liệu ra cùng id"* và có bài kiểm cho lời hứa đó. Đã đo:
mở lại mục đã lưu ra đúng **548 lệnh · −7,50 R**, khớp bản gốc từng con số.

**MỀM và ĐÃ LƯU khác nhau ở ĐÚNG MỘT chỗ: có `ten` hay không.**

- `ten = None` → mục mềm, tự ghi mỗi lần bấm ▶, cuốn chiếu khi quá **20**.
- `ten = "…"` → đã lưu, **miễn nhiễm cuốn chiếu**. Cái tên mới là thứ làm nó tìm lại được sau ba
  tháng — `hôm qua 22:41` thì tháng sau chẳng nói lên gì.

Một thư mục, một định dạng, nên `Mở lại` chạy **y hệt nhau** ở cả hai danh sách — không có hai
đường code để lệch nhau. "Lưu" chỉ là ghi một cái tên vào file đã có.

**Chạy lại mà không đổi gì thì KHÔNG đẻ dòng mới.** Cùng vân tay sơ đồ + cùng cài đặt = kết quả
giống hệt (tất định), một dòng nữa mang đúng 0 thông tin. Chỉ dập lại mốc thời gian. `delay_ms` cố
ý **không** nằm trong bộ cài đặt đem so — nó chỉ là tốc độ phát lại, tính nó vào thì lịch sử đầy rác.

**Chỗ cơ chế này có thể nói dối, đã chặn.** `Mở lại` chỉ ra đúng số cũ nếu nến nguồn còn y nguyên.
Mỗi mục ghi `symbol · số nến · nến đầu · nến cuối`; lúc mở, `_soat_nguon` so lại và nếu lệch thì
**từ chối chạy** kèm câu *"dữ liệu nguồn đã đổi (353.129 → 401.664 nến)"* — chứ không lặng lẽ chạy
ra bộ số khác rồi vẫn mang cái tên cũ. Bản tóm tắt thì vẫn còn vĩnh viễn.

**Hai thứ được thêm mà không phải viết mới:**

1. `_tom_tat_chay()` dựng ở **một chỗ** — vừa là thứ tab Thống kê vẽ, vừa là thứ lịch sử cất đi.
   Nên mở mục cũ và xem lần chạy hiện tại đi qua **cùng một đường vẽ**, không có hình dạng thứ hai.
2. `so_hai_lan` giờ **sống qua các phiên**: chưa chạy lần nào trong phiên thì `_tom_tat_lan_truoc`
   lấy mục mới nhất trong lịch sử. Trước đây đóng cửa sổ tester là câu *"so với lần trước thì
   sao"* mất sạch, mà vòng lặp nâng cấp model thì chẳng ai làm gọn trong một phiên.

**Một lỗi `tsc` bắt được, đáng ghi.** `onClick={chay}` — sau khi `chay` nhận thêm tham số `ma` thì
React truyền cả **đối tượng sự kiện** vào đó, và nút `↻ Chạy lại` hoá ra đi *mở lại một mục lịch
sử* với mã là một `MouseEvent`. Phải viết `onClick={() => void chay()}`.

### 12.20 ✅ Tab Thống kê — tổng kết cố định, không tua

Tab thứ hai của **bảng dưới**, cạnh `Nhật ký`, dùng chung thanh kéo và nút gập đã có. Nội dung xếp
**dọc và cuộn được**: khối số → đường vốn → sụt giảm.

**Cố định, không theo con trỏ.** Đây là tổng kết cả lượt chạy, `test_thong_ke()` gọi đúng một lần
lúc mở tab. Ghi rõ **khoảng thật sự có nến** *và* **khoảng đã yêu cầu** trong Cài đặt — hai cái
lệch nhau là chuyện thường, mà đọc số không biết nó tính trên quãng nào thì con số vô nghĩa.

**Đường vốn là VỐN ĐÃ CHỐT**, mỗi nến trục có lệnh đóng một điểm (386 lệnh → 384 điểm cho một
năm). Cố ý KHÔNG vẽ lãi nổi: nó đổi theo từng nến M1 → 353.000 điểm, giật liên tục, và
`drawdown_pt` vốn đã cố tình loại nó ra vì đúng lý do đó (§12.13e).

**Số và cả hai đường ra từ MỘT vòng lặp** trong `_thong_ke`, nên điểm cuối đường vốn *bằng đúng*
`von_cuoi` và đáy đường sụt giảm *bằng đúng* `drawdown_pt` — không có hai nguồn để lệch nhau. Nhiều
lệnh cùng đóng trong một nến trục thì gộp làm một điểm (thư viện vẽ đòi mốc tăng ngặt), giữ `von`
của lệnh cuối nhưng giữ mức sụt **sâu nhất**, để đáy đồ thị vẫn khớp con số.

**KHÔNG có `số vùng nén`** dù `thong_ke` đang mang sẵn — khái niệm riêng của một chiến lược, đúng
cái bẫy đã gỡ ở bảng số liệu bên phải (§12.9c).

#### 12.20c ✅ HAI ĐỒ THỊ VẼ TAY — bỏ lightweight-charts ở tab này

Bản đầu dùng lightweight-charts cho cả hai. Bỏ, vì ba lý do và không lý do nào là "cho vui":

- nó **đóng khung một mảng nền đen** riêng giữa bảng vốn màu xám — người dùng: *"để nó đè lên nền
  xám luôn chứ, lại để nền đen như này"*;
- nó **dán logo TradingView** vào góc mỗi đồ thị;
- nó kéo cả một bộ máy biểu đồ nến chỉ để vẽ một đường gấp khúc 384 điểm.

Chart **phát lại** thì vẫn giữ nó — chỗ đó cần trục thời gian, thu phóng, kéo ngang, marker, tooltip
theo nến. Chỗ này không cần gì trong số đó.

Mẹo để **không phải đo bề ngang bằng JS**: `<svg preserveAspectRatio="none">` với hệ toạ độ cố
định 1000×100, cho nó tự kéo giãn đầy khung; nét không méo theo nhờ `vector-effect:
non-scaling-stroke`. Còn CHỮ thì đứng **ngoài** SVG — nhãn là thẻ HTML đặt theo phần trăm, nên
không dính phép kéo giãn đó. Không `ResizeObserver`, không state kích thước, tự co giãn.

Ba chi tiết làm rồi mới thấy cần:

1. **Mảng tô cắt đôi ở đường mốc** — trên mốc xanh (đang lãi), dưới mốc đỏ (đang lỗ), bằng hai
   `clipPath`. Tô một màu cam duy nhất thì nửa khung thành một khối cam nặng trịch mà chẳng nói
   gì; cắt đôi thì đúng nghĩa xanh/đỏ mà bảng màu đã dành riêng cho lãi/lỗ (§12.17).
   `clipPath` phải mang **id riêng từng đồ thị** (`useId`) — trùng id thì đồ thị này bị cắt theo
   mốc của đồ thị kia.
2. **Bước trục giá phải có 2.5.** Thiếu nó thì biên độ 93 $ nhảy thẳng từ bước 20 lên bước 50 —
   cả đồ thị còn đúng 2 vạch, gần như không có trục. Có 2.5 thì ra bước 25, đủ 4 vạch.
3. **Crosshair tự làm.** Bỏ thư viện là mất cái crosshair đọc số, mà đó là thứ duy nhất đáng giữ
   lại: rê chuột ra vạch dọc + chấm trên đường + ô ghi `9,959.10 $ · 2025-07-25 11:00`. Tìm điểm
   gần nhất **theo thời gian**, không theo chỉ số — các điểm cách nhau không đều (lệnh đóng dày
   thưa tuỳ đoạn), chia đều chỉ số là trỏ sai chỗ.

#### 12.20b ⚠ LỖI THẬT: đường vốn cộng dồn theo thứ tự TẠO lệnh

`_thong_ke` duyệt `so.lenh` — tức thứ tự **đặt** lệnh — rồi cộng dồn vốn theo đó. Tổng thì thứ tự
nào cũng ra một số, nhưng **đường đi** của vốn thì không, mà `drawdown_pt` lại đo trên chính đường
đi đó. Đo trên một năm thật: **9/386 lệnh đóng đảo thứ tự** so với lúc đặt.

Lần này may: cả hai cách đều ra 0.792 %. Nhưng đồ thị vẽ ra sẽ giật ngược thời gian, và một bộ dữ
liệu khác là con số sai hẳn. Sửa: sắp theo `(nen_dong, id)` trước khi cộng dồn.

Nhân tiện `_thong_ke` trả thêm: `von_dau · lai_pt · drawdown_tien · drawdown_luc · R_moi_lenh ·
R_khi_thang · R_khi_thua · he_so_lai · chuoi_thua`. `he_so_lai` trả **`None` khi chưa có lệnh lỗ
nào**, không phải 0 — hai chuyện khác hẳn nhau, và bảng hiện dấu gạch.

### 12.19 ✅ Ô "nhảy tới mốc" trên thanh công cụ

*"thêm phần move to date ở ribbon để tôi muốn test khoảng thời gian cụ thể nếu cần."*

Một ô `datetime-local` (Chromium có sẵn bộ chọn ngày, không thêm thư viện nào), **tách khỏi đồng
hồ bên phải** chứ không gộp làm một: đồng hồ đổi 8 lần/giây lúc phát, mà một ô nhập tự đổi giá trị
dưới tay người đang gõ thì không gõ nổi. Bấm vào ô thì nó nạp mốc hiện tại, nên vẫn "đi tiếp từ
chỗ đang đứng".

**Tìm nến phải hỏi Python** (`ApiTester.test_tim_moc` → `searchsorted`), không nhẩm ở JS: dữ liệu
có 271 lỗ hổng nên `(t − t_đầu) / 60` ra một chỉ số lệch hẳn. Chọn nhằm chiều thứ Bảy thì nhảy
đúng tới phiên mở cửa Chủ nhật; chọn ngoài khoảng thì kẹp về nến đầu/cuối. Đo thật:
`07-04 15:00 → 07-04 15:00` · `07-04 23:05 → 07-06 22:05 (CN)` · `2030-… → nến cuối`.

**Ba cái bẫy, cả ba đều đã cắn:**

1. **Giờ UTC.** Nến MT5 là giờ sàn và cả app hiển thị nguyên như thế. Để `Date` tự định dạng là nó
   cộng lệch múi giờ máy — ô nhập lệch vài tiếng so với chính cái đồng hồ ngay cạnh nó. Dựng và
   đọc chuỗi bằng tay theo UTC.

2. **Ô bắn ra một giá trị HỢP LỆ sau MỖI đoạn gõ** (xong tháng đã là một mốc, xong ngày lại một
   mốc nữa). Không hoãn thì một lần gõ = 5-6 cú nhảy chồng nhau, và cú **về đích sau cùng** mới là
   cái hiển thị. Đo được: gõ `07/04/2025 03:00 PM` mà con trỏ dừng ở `07-06 22:05`, vì mốc dở dang
   `07/04 11:05 PM` rơi vào tối thứ Sáu (chợ đã đóng) nên bị đẩy sang phiên Chủ nhật. → hoãn 350ms
   + một số đếm `lanMoc` để vứt kết quả của cú đã cũ.

3. **⚠ Ô uncontrolled thì IM LẶNG HẲN sau cú nhảy đầu.** Tái hiện chắc chắn: gõ `07/04/2025`, đợi
   cú nhảy chạy xong, gõ tiếp `03:00` — `onChange` không bắn nữa, đồng hồ kẹt ở `07-06 22:05` còn
   ô ghi `03:00 PM`. Cú nhảy gọi `veDau` → dựng lại chart + đặt 6 state, và qua lần re-render lớn
   đó **bộ theo dõi giá trị của React lệch pha với DOM**. Cho ô một state riêng (controlled) là
   hết — React luôn nắm giá trị, không còn chỗ cho lệch.

   Bài học: cái bẫy này **chỉ lộ ra khi gõ có ngắt quãng**. Gõ liền một mạch thì hoãn 350ms gộp
   hết lại thành một cú nhảy và mọi thứ trông đúng. Kiểm bằng "gõ một phát rồi chụp" là bỏ lọt.

### 12.18 Nút "Tới sự kiện kế tiếp" — hai lỗi, một gốc

Người dùng báo: *"nút tới sự kiện kế tiếp bị lỗi, nó xoá luôn đi những sự kiện cũ."* Hai lỗi, và
cả hai đều từ một chỗ: **nhảy = dựng lại chart từ số không**.

1. **Chart trắng bốc sau khi nhảy.** `veDau` nạp đúng MỘT cây nến (`[nenTai(L, 0)]`) rồi để phát
   bồi thêm. Mọi lệnh cũ biến mất, và người xem mất hẳn ngữ cảnh — không biết giá vừa từ đâu tới.
   → Lô giờ bắt đầu **sớm hơn con trỏ `LUI = 720` nhịp** (≈144 nến M5, nửa màn hình) và chart được
   nạp thẳng toàn bộ đoạn quá khứ đó. **Cùng một lời gọi**, không thêm vòng nào.

2. **Bấm ba lần vẫn đứng yên.** Nút nhảy tới *40 nhịp TRƯỚC* sự kiện cho "dễ xem nó xảy ra" —
   nhưng thế thì lần bấm sau lại tìm thấy chính sự kiện đó (nó vẫn nằm phía trước con trỏ) và
   nhảy về đúng chỗ cũ. Một vòng lặp đứng im.
   → Dừng **ĐÚNG NGAY sự kiện**: mũi tên hiện ở mép phải, quá khứ vẫn còn nguyên nhờ đệm, và lần
   bấm sau đi tiếp được. Muốn xem lại khoảnh khắc thì ◀ vài nhịp rồi ▶.

Kèm hai chi tiết nhỏ mà thiếu thì vẫn lạc: nhật ký **luôn cuộn xuống cuối** khi danh sách đổi
(đang dừng thì không có dòng mới nên không sợ giật), và dòng vừa nhảy tới được **tô sáng** — nó
trả lời "tôi đang đứng ở đâu" ngay lúc chart đổi.

### 12.14 So hai lần chạy

Mục đích của bạn là *nâng cấp model*, mà đó là một vòng lặp: sửa → chạy lại → chỗ nào tốt lên,
chỗ nào xấu đi, **lệnh nào biến mất**. Giữ tóm tắt lần chạy trước (vài trăm KB) để bấm ▶ xong
hiện được một dòng:

```
so với lần trước: −3 lệnh · +2 lượt trượt tại [2] · tổng R 18.5 → 21.0
```

---

## 14. ⭐⭐ LIVE — nối sàn thật, và cách chống CHẾT IM LẶNG

> Chốt ngày 2026-08-13, sau khi bộ chạy và tester đã đo trên một năm dữ liệu thật.
>
> Live **không thêm một luật giao dịch nào**. Nó đổi đúng hai thứ: *nguồn nến* và *nguồn
> sự thật*. Toàn bộ phần còn lại của §14 sinh ra để trả lời một câu duy nhất —
> **làm sao biết nó đang thật sự chạy đúng?**

### 14.0 Một câu

> Backtest hỏng thì ra một con số sai và ta **nhìn thấy**. Live hỏng thì thường không ra
> gì cả — nó **im lặng**. Cả §14 là để bắt cái im lặng đó phải nói.

Bốn module mới, và chỉ ba trong số đó chạm sàn:

| Module | Việc | Chạm sàn? |
|---|---|---|
| `phien_live.py` | vòi cấp nến: sàn đóng nến M1 → gọi `bo_chay.PhienChay.mot_nhip` | đọc nến |
| `ket_noi.py` | sức khoẻ kết nối · hồ sơ đo được · **vòng hiệu chuẩn** · lệnh của sàn | ✔ đặt lệnh |
| `gui_lenh.py` | **tầng phòng vệ** — ý định của chiến lược → việc có thật ở sàn | ✔ đặt lệnh |
| `api.ApiLive` | bề mặt của cửa sổ Live, kế thừa bề mặt ĐỌC của `ApiTester` | qua luồng máy |

### 14.1 ⭐ MỘT ĐOẠN CODE CHO CẢ HAI

`phien_live.py` chỉ 160 dòng, và đó là **kết quả có chủ ý** chứ không phải chưa làm xong.
Nó cố ý không chứa luật giao dịch nào: mọi quyết định vẫn nằm ở
`bo_chay.PhienChay.mot_nhip` — **đúng cái hàm** backtest gọi trong vòng lặp. Việc duy
nhất của file là biến *"sàn vừa đóng một nến M1"* thành một lời gọi `mot_nhip`.

> Đó là cả điểm của lần tách bộ chạy: *"test như nào thì live như thế"* thành chuyện của
> **kiến trúc**, không phải của kỷ luật.

Hệ quả kéo theo, và nó đắt hơn vẻ ngoài: `nhip()` **dựng lại `ChuongTrinh` trên mảng nến
dài hơn** rồi chạy lại từ khung hình số 0, thay vì nuôi chỉ báo tăng dần. Có một bản
"tính dần" thứ hai là có hai phép tính chỉ báo, và sớm muộn chúng lệch nhau.

⚠ **Dựng vào biến cục bộ rồi mới công bố.** Bản trước gán thẳng `self.phien` rồi mới phát
lại — tức trong suốt lúc phát lại, `self.phien` là một phiên RỖNG. Luồng cầu nối gọi
`anh_chup()` đúng lúc đó thì đọc được nhật ký 0 dòng, lệnh 0 cái, và cửa sổ chớp trắng
một nhịp. Đo được: giữa `nhip()` thấy 0/0 trong khi trước và sau đều là 19/17. Gán **một
phát ở cuối** thì không có khe nào.

### 14.2 Nhịp — quyết định ở BIÊN NẾN, không theo tick

| Việc | Nhịp | Ai làm |
|---|---|---|
| sức khoẻ kết nối · giá cho chart | **1 giây** (`ApiLive.NHIP_DO`) | luồng máy |
| hỏi nến mới | **10 giây** (`NHIP_NEN = 10` nhịp đo) | luồng máy |
| quyết định | mỗi nến M1 đóng → Manage · mỗi nến M5 đóng → Entry | `mot_nhip` |
| khớp lệnh · SL/TP | thời gian thực — **SÀN làm**, ta chỉ đọc kết quả | sàn |

**Không chạy theo tick**, vì bộ chạy đọc `close`/`ATR` của nến **đã đóng**. Chạy theo tick
là đọc một cây nến đang hình thành, giá trị nhảy liên tục, và live sẽ khác backtest —
đúng thứ đang cố tránh. Bản gốc MQL5 cũng quyết định ở biên nến (`if(!IsNewBar(...)) return;`).

**Hỏi nến 10 giây chứ không 60:** nến đóng theo giờ **SERVER**, mà giờ server lệch giờ máy
— canh đúng phút là có lúc trễ cả một nhịp. Hỏi thừa thì rẻ, trễ thì không.

⚠ **`_keo` bỏ cây nến CUỐI.** `copy_rates_from_pos` trả cả nến đang hình thành. Đưa nó vào
bộ chạy là quyết định trên một cây nến chưa đóng.

⚠ **`nhip()` chạy MỌI nến còn thiếu, không chỉ nến mới nhất.** App bận, máy ngủ, mạng rớt
— bỏ nến là bỏ luôn quyết định của những phút đó, và trạng thái vùng nén lệch hẳn so với
backtest. `mot_nhip` chịu được gọi ngắt quãng; `test_bo_chay.py` giữ đúng điều đó.

### 14.3 ⭐ KHUNG HÌNH SỐ 0 — lịch sử để TÍNH, không phải chuyện ĐÃ XẢY RA

Hai thứ khác hẳn nhau, và bản đầu đã gộp chúng làm một:

- **Chỉ báo cần lịch sử.** ATR(14) M5 cần 14 nến đã đóng, MA(50) M15 cần 12,5 giờ. Đọc
  nến cũ để TÍNH RA con số không phải là "chiến lược đã chạy" — đó là mở mắt ở khung hình
  đầu tiên. Nên `ChuongTrinh` vẫn dựng trên **cả mảng** (`SO_NEN_NAP = 7200` ≈ 5 ngày).
- **Trạng thái chiến lược thì KHÔNG.** Vùng nén đang đếm, cờ *"vùng này đã sinh lệnh"*,
  sổ lệnh — **bắt đầu từ số 0** lúc bấm Live.

> Bản trước chạy `mot_nhip` qua cả 7.200 nến quá khứ, đẻ ra **208 dòng nhật ký** và mấy
> lệnh MÔ PHỎNG rồi bày lên như chuyện đã xảy ra ở sàn. Sai bản chất: **test là bộ phim đã
> quay xong, live là máy quay vừa bấm nút.**

Và đây cũng đúng bản gốc: `FilterEngine::Initialize` đặt `m_comp_bar_count = 0`,
`state = COMP_IDLE` — gắn EA vào chart là nó bắt đầu trống rỗng, phải chờ một cú nén MỚI.

`t_bat_dau` (mốc bấm Live) là ranh giới, và nó phải chảy ra tới giao diện: mọi thứ trước
nó là mô phỏng để dựng trạng thái, **không được hiện ra như kết quả live**. Trộn hai thứ
đó là nói dối đúng chỗ người ta cần tin nhất.

### 14.4 ⭐ MỘT LUỒNG CHẠM SÀN — giao diện chỉ ĐỌC BỘ NHỚ

Đây là chỗ sửa gốc của cả chuyện lag, và nó là **kiến trúc chứ không phải cảm giác**.

> Bản trước có HAI chỗ chạm sàn: luồng máy (10 giây một lần, kéo nến) và `live_tin()` do
> JS gọi **mỗi giây**, tự đi đo bằng 5 lượt IPC. Hai bên giành cùng một ổ khoá `_KetNoi`,
> nên nhịp nào của bên này rơi trúng lúc bên kia đang giữ là đứng — đúng cảm giác *"lúc
> lag lúc không"*.

Giờ: **luồng máy `_vong()` sở hữu kết nối và tự đo, cất vào bộ nhớ.** `live_tin()` chỉ đọc
cái đã có — không IPC, không giành khoá, không bao giờ chờ ai. Quan trọng hơn cho ngày
mai: khi luồng gửi lệnh vào, nó nối tiếp trên **cùng luồng này** chứ không cạnh tranh với
giao diện.

Ba thứ đi kèm, cả ba đều là luật:

- **Gộp mọi thứ vào MỘT lời gọi** (`live_tin`): tách ra thì bảng Vấn đề và dải kết nối đọc
  hai lần đo khác nhau, và sẽ có lúc dải báo xanh còn bảng báo mất kết nối.
- **Chỉ gửi phần MỚI** của nhật ký bài kiểm (`da_co`): bài hiệu chuẩn sinh vài chục bước,
  gửi lại cả danh sách mỗi giây là chép một thứ không đổi qua cầu nối hàng trăm lần.
- ⚠ **TUỔI của bản đo phải chảy ra ngoài** (`tin_cu_giay` · `tam_dung`). Đọc bộ nhớ thì rẻ,
  đổi lại số liệu có thể CŨ mà vẫn trông như đang sống — lúc hiệu chuẩn ta cố ý ngừng đo,
  và nếu luồng máy chết thì nó đứng hẳn. Hiện `tuổi tick 1,4 s` đông cứng suốt ba phút là
  đúng loại nói dối im lặng mà cả app này sinh ra để chống. Ngưỡng: quá **3 nhịp** thì
  giao diện nói thẳng *"đang tạm dừng"* thay vì giả vờ tươi.

⚠ **Đóng cửa sổ Live PHẢI dừng luồng máy** (`_dung = True`). Không có dòng đó thì `_vong()`
chạy mãi — điều kiện `self._window is not None` không bao giờ đổi vì không ai gán lại — và
mở Live lần hai là có **HAI luồng** cùng kéo nến, cùng giành cầu nối.

> **Chọn nghĩa: ĐÓNG CỬA SỔ = DỪNG PHIÊN.** Chưa có luồng đặt lệnh nên không có gì phải
> giữ chạy ngầm. Ngày thêm nó thì đây là chỗ **phải bàn lại** — `ApiLive` được viết sẵn
> theo hướng "máy live không sống trong cửa sổ" để lúc đó không phải bẻ lại cấu trúc.

### 14.5 CỔNG CHỐT — nói TRƯỚC, không nói sau

Cổng chốt (chọn chiến lược · symbol · kiểm kết nối) nằm **TRONG chính cửa sổ Live**, không
phải ở cửa sổ vẽ. Vào bằng `Ctrl+L` hay bằng nút thì cũng đáp xuống đúng một chỗ, và cửa
sổ vẽ không phải gánh thêm một hộp thoại chẳng liên quan gì tới việc vẽ. Không đóng được
bằng ✕ hay Esc — đóng nó ra một cửa sổ Live rỗng không biết mình đang chạy gì.

Sơ đồ được soát **ngay lúc chọn**, không đợi bấm "Bắt đầu", và soát **hai lớp bằng cùng
một bộ luật** (giao diện gọi `live_soat_so_do`, `live_chon` soát lại lần nữa): đây là cửa
duy nhất giữa một sơ đồ vẽ dở và một kết nối tiêu tiền thật.

⚠ **`validate_process` cố ý DỄ TÍNH — Live thì không được.** Nó soát một sơ đồ *đang vẽ
dở*, mà vẽ dở thì chưa vào lệnh được là chuyện thường. Đo được: một *"Chiến lược 1"* mới
tinh, chưa có gì ngoài khối Bắt đầu, đi qua nó với **0 lỗi 0 cảnh báo**. Ở cửa sổ vẽ thế
là đúng; ở Live đó là một cái máy sẽ nối vào sàn rồi **ngồi im mãi mãi** trong khi người
dùng tưởng nó đang canh.

Nên `_loi_live` thêm đúng một câu hỏi — *sơ đồ này có thể đặt nổi một lệnh không* — và trả
lời bằng hai phép kiểm: Entry có khối **Vào lệnh** nào không, và khối đó có **nối tới
được** từ khối Bắt đầu không (dùng lại `flow_order().unreachable`, không tự đi đồ thị lần
nữa).

Điều kiện chạy lấy **ĐÚNG bộ của Strategy Tester** — cùng spread, cùng phí, cùng đòn bẩy.
Live mà chạy trên một bộ số khác thì so nhật ký hai cửa sổ là vô nghĩa.

### 14.6 ⭐ SỨC KHOẺ KẾT NỐI — ba kiểu chết im lặng

`ket_noi.SucKhoe` **không** đo *"có nối được không"* (câu đó `nguon_nen.kiem_ket_noi` trả
rồi). Nó đo **có TIN được không**. Ba kiểu chết dưới đây không hiện ra ở chỗ nào khác
trong app:

1. **Terminal báo "connected" mà feed đứng.** `terminal_info().connected` vẫn `True` trong
   khi tick cuối đã 40 phút không đổi. Nhìn chart thì thấy nến đứng yên và cứ tưởng thị
   trường lặng. → mạch đập thật là **tuổi của tick cuối**, ngưỡng `TICK_QUA_HAN = 90 s`.
2. **Nút AlgoTrading tắt.** Mọi lệnh gửi đi đều bị từ chối, mà lý do nằm trong một retcode
   chứ không nằm trên màn hình. → kiểm **cả hai**: terminal cho phép VÀ tài khoản cho EA
   giao dịch.
3. **Spread live khác xa spread đã backtest.** Kết nối tốt, lệnh gửi được, nhưng chiến
   lược đang chạy trong một thế giới khác cái đã thử. **Kiểu chết đắt nhất vì không có gì
   báo động cả.** → `spread_lech` = spread thật ÷ spread đã test.

Cộng ba thứ nữa đọc luôn trong cùng nhịp đó:

- **`lech_gio`** — nến M5 đóng theo giờ SERVER, nên lệch giờ là lệch cả nhịp quyết định.
- **`symbol_giao_dich_duoc`** — nhiều sàn để vàng ở chế độ chỉ-đóng ngoài giờ, hoặc
  chỉ-xem: nối tốt mà vẫn không đặt được lệnh nào (`SYMBOL_TRADE_MODE_FULL = 4`).
- **`nen_dang`** — cây nến đang hình thành. Chiến lược **không bao giờ** đọc nó, nhưng
  chart phải có, không thì trên M1 màn hình đứng im tới 60 giây và trông như mất kết nối.
  Nhịp này vốn đã đọc tick nên gửi kèm **không tốn thêm một lời gọi nào**.

**Giữ LỊCH SỬ chứ không chỉ ảnh chụp.** *"Đang nối được"* là câu vô nghĩa nếu trong ba giờ
qua nó rớt bốn lần. Cái quyết định có dám để máy chạy qua đêm là **con số rớt**, không
phải cái đèn xanh lúc này. Đếm rớt theo **cạnh xuống**, không theo trạng thái: nối được
suốt 3 giờ rồi rớt một lần là MỘT lần rớt, không phải một nghìn lần đo thấy rớt.

**`van_de()` trả về đúng hình dạng bảng Vấn đề của cửa sổ vẽ**, và mỗi dòng phải **hành
động được**: *"kết nối kém"* là vô dụng, *"AlgoTrading đang tắt — bấm nút đó trên MT5"* thì
làm được ngay. Nối vào **TÀI KHOẢN THẬT** là một dòng mức `error`, cố ý.

`thong_so_tinh()` tách riêng vì nó đọc được trên **mọi** tài khoản kể cả tài khoản thật,
nên luôn kiểm mỗi lần mở Live. Bốn con số, mỗi con số là một cách chiến lược chạy tốt
trong backtest hỏng ngay ngày đầu live — và ⚠ **netting là cái lớn nhất**: D_02 dựa hẳn
vào nhiều lệnh sống song song, tài khoản netting thì hai lệnh mua **cộng lại** thành một
vị thế, và kết quả khác backtest mà không có gì báo.

### 14.7 ⭐ TẦNG PHÒNG VỆ (`gui_lenh.py`) — bốn kết cục, không phải hai

Chiến lược nói *"mua 0.01 lot, SL ở 4400"*. Giữa câu đó và một lệnh có thật ở sàn có một
đống thứ chen vào: SL quá sát giá, giá nhảy trước khi lệnh tới, sàn không nhận kiểu khớp,
vị thế đang bị đóng băng, ống đứt. File này lo hết — và **ghi lại nó đã phải làm gì**, vì
mỗi lần nó sửa ý định là live lệch một chút khỏi backtest, mà lệch âm thầm là thứ tệ nhất.

**MỌI thứ chạm sàn đều đi qua đây.** Bảy thao tác: mở · gắn SL/TP · sửa SL/TP · đóng · đặt
chờ · sửa chờ · huỷ chờ. Không có cửa sau. *(Bản trước chỉ có `gui()`, nên sáu thao tác kia
gọi thẳng `order_send` — vừa không được phòng vệ, vừa không khai báo mã lạ. Đó là chỗ
`10029` và `10036` lọt lưới suốt.)*

| Kết cục | Nghĩa |
|---|---|
| `ok` | ý định thành hiện thực — **kể cả khi phải sửa vài lần dọc đường** |
| `bo` | thử hết cách vẫn không được → **GIẢ THUYẾT SAI**, phải chỉnh con số |
| `nguoi` | máy không chữa được (AlgoTrading tắt, hết tiền, chợ đóng). Chỉnh số bao nhiêu cũng vô ích |
| `hong` | chết trước cả khi gửi được gì (chưa cài thư viện, sàn không có symbol) |

> Tách `nguoi` khỏi `bo` mới cho vòng hiệu chuẩn biết lúc nào **dừng hẳn** thay vì lặp mãi
> một bài không đời nào qua được.

**Hai thứ đừng lẫn:** *luật* ở đây là **thường trực** — luôn chạy, không phải bật khi cần.
Còn mấy con số trong luật (`kep_stops`, `deviation`, `thu_lai`…) là **GIẢ THUYẾT**, và §14.8
sinh ra để kiểm chúng.

**Ranh giới quan trọng nhất:** thử lại cái ĐÁNG thử, và tuyệt đối không thử lại cái vô
vọng. Retry mù trên *"thiếu tiền"* là gửi mãi một lệnh không bao giờ vào được, và che mất
lỗi thật.

#### 14.7a Bảng retcode — mỗi mã một cách xử

`XU_LY` có **42 mã**, chia chín cách: `thu` · `noi` (nới deviation) · `kep` (đẩy SL/TP ra
xa) · `doi_fill` · `cho_lau` · `cho_noi` · `xong` · `dung` · `nguoi`. Ba chỗ đáng ghi:

⚠ **`cho_noi` chứ không phải ngủ rồi gửi tiếp.** `10031` nghĩa là **cái ống đứt**. Ngủ
500 ms rồi ném lệnh vào cái ống vẫn đứt thì thử 4 lần cũng hỏng cả 4 — đo được, đúng bằng
một lần hiệu chuẩn. Phải chờ tới lúc nó **thật sự nối lại** rồi gửi **ngay lúc đó**.

⚠ **`10013` là MÃ HAI NGHĨA.** Terminal trả nó cho *yêu cầu sai tham số* (thử lại vô ích)
**và** cho *không gửi đi được lúc này* (trả về trong 0,1 ms, chưa hề ra tới sàn — rất đáng
thử lại). Không nhìn mã mà đoán được; phải **hỏi thẳng terminal** đang nối hay không
(`LUONG_LU`). Xếp cứng nó vào `dung` thì mọi lần ống đứt bị đọc thành "sai tham số", bỏ
cuộc ngay lần thử đầu, và vòng hiệu chuẩn cứ tăng `thu_lai` — một con số không bao giờ
được dùng tới.

⚠ **`CHUA_BIET` — chỗ cái chưa biết chịu lộ mặt.** Không ai liệt kê hết được mọi cách một
sàn từ chối lệnh, nên thay vì cố đoán cho đủ, hệ thống **đếm** những mã đã gặp mà chưa có
luật rồi hiện ra. Bản trước `XU_LY.get(ma, "thu")` nuốt mã lạ vào nhánh mặc định — nó vẫn
chạy, có khi chạy đúng, nhưng **không ai biết ta vừa gặp một thứ chưa hiểu**.

#### 14.7b Ba luật BẤT ĐỐI XỨNG — và cả ba đều tốn tiền nếu sai

**1 · Mã THÀNH CÔNG không được đọc thành thất bại.** `10008` (chờ đã đặt) · `10009` ·
`10010` (khớp MỘT PHẦN) · `10025` (không có gì thay đổi → SL/TP vốn đã đúng) · `10036` (vị
thế đã đóng → muốn đóng mà nó đóng rồi thì… đạt).

> Đo được: sàn khớp một phần thì lệnh **ĐÃ VÀO**, nhưng vòng thử đọc thành "chưa xong" rồi
> **GỬI LẠI** — xin 5 lot mà bắn ra 3 lệnh, thành **15 lot thật**, và hai ticket đầu biến
> mất khỏi sổ nên không ai thấy. **Một "thành công" bị đọc thành "thất bại" tốn tiền gấp
> bội một thất bại bị đọc thành thành công.**

**2 · Mã MỜ NGHĨA trên lệnh thị trường thì DỪNG** (`MO_HO_TREN_DEAL = {10011, 10012, 10023,
10031}`). Timeout và mất kết nối là đúng nghĩa *"không biết"* — yêu cầu có thể đã tới sàn
và khớp xong rồi, chỉ có câu trả lời là lạc. Gửi lại một `TRADE_ACTION_DEAL` trong tình
trạng đó là **đánh cược bằng tiền thật**. Dựng lại được trên sàn giả: sàn khớp thật rồi trả
`10012` → một ý định ra **HAI vị thế**. `10041` (sàn TỪ CHỐI) **không** nằm đây: từ chối là
bằng chứng lệnh KHÔNG vào, thử lại an toàn.

**3 · Mã LẠ: `dung` với lệnh thị trường, `thu` với mọi thứ khác.** Không biết mã nghĩa gì
tức là không biết lệnh đã vào sàn hay chưa. Nhưng gửi lại một lệnh **sửa SL/TP** hay **huỷ
lệnh chờ** thì vô hại — cùng lắm là "không có gì thay đổi". Bất đối xứng này phải nằm
**trong luật**, không để nhánh mặc định nuốt.

#### 14.7c Hai cái bẫy đã cắn lúc chạy thật

⚠ **Kẹp SL/TP theo giá HIỆN TẠI, không theo giá mở.** `stops_level` là khoảng cách tối
thiểu tới **giá đang chạy** — sàn đo từ đó. Kẹp theo giá mở thì khi giá đã chạy xa, việc
kéo SL lên khoá lời bị đẩy ngược về sát giá vào: mua ở 4400, giá 4500, xin SL 4495 (khoá
+95 điểm) mà **lại gửi đi SL 4397** — xoá sạch phần lời đã khoá, và sổ vẫn ghi "ok".

⚠ **`_vi_the` LUÔN đọc lại từ sàn**, kể cả khi người gọi đưa sẵn đối tượng vị thế. Đối
tượng vị thế là **ảnh chụp tại một thời điểm** — giữa lúc chụp và lúc dùng, SL có thể đã
dính và vị thế đã đóng. Cầm cái ảnh đó gọi tiếp thì terminal từ chối tại chỗ trong 0,1 ms
với mã `10013`, và ta đọc thành "yêu cầu sai tham số" rồi bỏ cuộc. Gặp thật, và nó giết
trọn vòng 1 của một lần hiệu chuẩn.

Còn **`sua_truoc` và `da_sua` là hai cột khác nhau**, không gộp: sửa TRƯỚC khi gửi nghĩa là
phòng vệ **đoán đúng** nên sàn không kịp từ chối — đó là bằng chứng **mạnh nhất** rằng giả
thuyết đúng. Sửa SAU khi bị từ chối là chữa được, vẫn đạt, nhưng yếu hơn.

### 14.8 ⭐ HIỆU CHUẨN — vòng lặp TỰ CHỈNH, không phải bài thi

> **Đây KHÔNG phải bài thi để chấm điểm. Đây là vòng lặp tự chỉnh cho tới khi bảng Đề
> phòng ĐÚNG.**

Nên thứ giao lại ở cuối không phải một danh sách lỗi, mà là **một bộ con số mà mỗi dòng
đều ghi *đo được***. Bản trước in ra *"14/21 bước đạt"* rồi thôi — con số đó vừa vô nghĩa
(trộn bốn thứ khác hẳn nhau vào một rổ) vừa vô dụng (biết rồi thì làm gì?).

**Vì sao phải mở/đóng lệnh THẬT** thay vì đặt một lệnh không thể khớp: bốn thứ dưới đây
**không có cách nào đọc ra, chỉ đo được** — trượt giá lúc vào và lúc ra · độ trễ thật của
từng loại thao tác (gửi ≠ sửa ≠ đóng) · sàn có thật sự nhận filling mode nó khai không ·
ngưỡng SL/TP thật. Lặp nhiều vòng và **giãn cách để giá chạy**: đo sáu lần ở cùng một mức
giá thì ra sáu con số giống nhau — đó là một điểm, không phải một phân bố.

**TỪ CHỐI nếu không phải demo** — đọc `trade_mode`, không hỏi.

#### 14.8a Bốn mức chấm, không phải đạt/hỏng

| Mức | Nghĩa |
|---|---|
| `tron` | chạy trơn, phòng vệ không phải động tay |
| `xac` | phòng vệ **sửa TRƯỚC** khi gửi nên sàn không kịp từ chối → bằng chứng mạnh nhất |
| `do` | sàn từ chối, phòng vệ **chữa được**, ý định vẫn thành → **VẪN LÀ ĐẠT** |
| `hong` | phòng vệ bó tay → giả thuyết SAI, phải chỉnh con số rồi chạy lại |
| `nguoi` | máy không chữa được → **DỪNG** và nói rõ người phải làm gì |

> **Lỗi mà ta đã đề phòng đúng thì không phải lỗi của ta.** Tô đỏ một bước mà tầng phòng vệ
> đã chữa xong là **báo động giả**, và báo động giả thì lần sau không ai đọc nữa.

#### 14.8b Ba trạng thái kết thúc — và mỗi cái phải nói rõ là cái nào

| | |
|---|---|
| `xong` | không còn gì để chỉnh. Bảng Đề phòng đã đúng |
| `nguoi` | gặp thứ máy không chữa được. Dừng, và nói người phải làm gì |
| `chua_hoi_tu` | hết trần lặp (`LAP_TOI_DA = 4`) mà vẫn còn hỏng. **Nói thẳng chỗ chưa chốt được**, kèm những gì đã thử |

`_suy_chinh()` là **trái tim** của vòng lặp: *lỗi vừa gặp TỰ KHAI giá trị đúng*. Mỗi luật
đọc được thành một câu — `10029` vẫn lọt ⇒ `cho_bang_ms` đang thiếu ⇒ nhân đôi. Không có
hàm này thì bài kiểm chỉ biết kêu, còn chỉnh vẫn là việc của người — mà người thì không
biết `10029` nghĩa là tăng `cho_bang_ms`.

**Ba lần nói dối theo hướng trấn an đã bị chặn**, và cả ba đều lọt qua chính cái chốt dựng
cho nó:

1. ⚠ **Lượt VỠ GIỮA CHỪNG từng ra `xong`.** `chay_duoc` đã bật từ đầu, `dem` không có mục
   `hong` nào (lượt chỉ NGỪNG chứ không có bước nào thất bại), nên `hieu_chuan` thấy đủ ba
   dấu hiệu tốt và tuyên bố **"xong"** — trong khi 6/7 thao tác chạm sàn chưa bao giờ được
   thử. Giờ `vo_giua` → `chua_hoi_tu`: lượt chưa chạy hết thì **mọi** kết luận rút ra từ nó
   đều không có cơ sở, kể cả kết luận "không còn gì để chỉnh".
2. ⚠ **Còn hỏng mà không con số nào chỉnh được → DỪNG NGAY.** Bản trước rơi thẳng vào nhánh
   "xong". Lặp tiếp cũng vô nghĩa: cùng bộ số thì cùng kết quả. *"Đây là chỗ ta chưa hiểu,
   không phải chỗ cài sai."*
3. ⚠ **Chỉ tăng `thu_lai` cho mã CÒN ĐƯỢC THỬ LẠI.** Bản trước tăng cho mọi mã hỏng kể cả
   mã xếp `dung` — tức chỉnh một con số không bao giờ được dùng tới, rồi vòng lặp tưởng
   mình vừa tiến bộ nên chạy tiếp. Đo được: `thu_lai 3→4→5→6→7` suốt bốn lượt trong khi mã
   hỏng là `10013`, đốt sạch bài kiểm mà không sửa gì.

⚠ **Bài kiểm GIÀNH cầu nối suốt thời gian chạy** (`_dang_kiem`). `mt5` giữ MỘT kết nối cho
cả tiến trình, và `_KetNoi` đóng nó khi thoát. Nhịp đo sức khoẻ 1 giây và vòi cấp nến 10
giây cắt ngang bài kiểm đang chạy dở → mọi lệnh từ vòng 2 trả `10031 mất kết nối`. Người
dùng chỉ thấy "bài kiểm hỏng" mà không có cách nào biết vì sao.

⚠ **Tiến độ phải có cả LƯỢT chứ không chỉ vòng.** Bản trước chỉ đẩy `vòng k/3` và nó reset
mỗi lượt, nên bốn lượt trông y hệt một vòng lặp vô tận. Và **nhật ký chảy ra NGAY**, không
gom tới cuối: bài kiểm đặt 5 lệnh thật mà nhật ký im lặng suốt hai phút là đúng cái app này
sinh ra để chống.

#### 14.8c Đo ngưỡng SL/TP thật — và trả lại hiện trường

Lần chạy thật: sàn khai `trade_stops_level = 0` nhưng SL cách **300 điểm** vẫn bị từ chối
`10016`. **Con số khai KHÔNG dùng được.** Mà D_02 tính SL theo ATR — lúc nén chặt SL còn
ngắn hơn thế, nên không biết ngưỡng thật thì live bị từ chối im lặng **đúng lúc vào lệnh**.

`do_stops_level` chia đôi khoảng, mỗi lần thử là một `order_send` thật, 6–8 lần là biết.
Ba chi tiết, cả ba đều học từ một lần hỏng:

- **Gọi thẳng `order_send`, CỐ Ý.** Đây là phép ĐO, mà tầng phòng vệ sinh ra để né đúng cái
  ta đang muốn chạm vào. Cho nó chen vào đây là **đo chính nó**.
- ⚠ **Tách NHIỄU khỏi câu trả lời** (`_NHIEU`). Không tách thì một lần đóng băng bị đọc
  thành "ngưỡng cao hơn" và trả về con số to hơn sự thật — rồi mọi SL sau đó bị đẩy ra xa
  vô cớ. Đo được: cùng một sàn ra **410 điểm** ở lượt này và **324** ở lượt sau.
- ⚠ **PHẢI TRẢ LẠI HIỆN TRƯỜNG.** Phép đo kết thúc với SL nằm **sát giá nhất có thể** — đó
  là định nghĩa của nó. Vàng chạy vài chục điểm mỗi phút nên cái SL ấy dính gần như ngay,
  vị thế đóng, và ba bước sau vẫn cầm vị thế cũ mà gọi tiếp → cả vòng chết. **Một phép đo
  mà làm hỏng thứ nó vừa đo thì không phải phép đo.**

Vì nhiễu như thế nên **đo MỘT LẦN rồi dùng lại** cho các lượt sau (`nguong_biet`): đo lại
mỗi lượt thì lần nào nhích lên là lại sinh một lần "chỉnh", và vòng lặp leo thang **vì
nhiễu chứ không vì sai**.

Biên: `BIEN_KEP = 1.2` (đo 215 mà cài 215 là cài đúng mép — spread giãn một nhịp là lại bị
từ chối) · `BIEN_TRUOT = 1.5` (deviation quá hẹp thì lệnh bị từ chối, quá rộng thì khớp giá
xấu — nhưng **KHÔNG khớp còn tệ hơn khớp xấu**).

#### 14.8d Dọn rác BẰNG MỌI GIÁ

Bài kiểm đứt giữa chừng vì mất cầu nối, để lại **một vị thế đang mở**. Không ai soi thì nó
nằm đó âm thầm ăn/lỗ, và người dùng mở Live lên chẳng thấy gì bất thường.

- `MAGIC_KIEM = 777001` tách hẳn khỏi magic chiến lược → dọn rác **không bao giờ đụng nhầm
  lệnh thật**.
- `don_rac` gọi được cả từ nút riêng lẫn từ `finally`, và **đi qua `gui_lenh`** như mọi thứ
  khác — dọn rác cũng là chạm sàn, và đây đúng là lúc hay đứt nhất.
- ⚠ **Dọn hỏng thì phải KÊU.** Bản trước `if ok: đếm` — thất bại rơi vào im lặng, và
  `{"da_dong": 0}` không phân biệt được với *"không có gì để dọn"*. Rác ở đây là **vị thế
  thật đang ăn/lỗ**, đúng thứ nguy nhất khi để âm thầm.

### 14.9 HỒ SƠ KẾT NỐI — cache, không phải cài đặt

`du_lieu/ho_so_ket_noi.json`. Khác cài đặt ở chỗ: **cài đặt là thứ người dùng gõ vào, hồ sơ
là thứ ĐO ĐƯỢC từ sàn.** Mất file này không hỏng gì cả, chỉ là phải chạy lại bài kiểm — nên
nó nằm riêng, xoá thoải mái, và **không bao giờ trộn vào `cai_dat.json`**.

⚠ **Khoá theo `sàn + symbol`, KHÔNG theo server.** Demo và thật của cùng một sàn là hai
server khác nhau (`Exness-MT5Trial7` vs server thật) — khoá theo server thì hiệu chuẩn trên
demo không bao giờ áp được cho tài khoản thật, tức cả luồng *"test trên demo rồi sang
thật"* chết ngay ở bước cuối.

⚠ **Nhưng tên sàn cũng không chắc.** Một sàn có thể có nhiều pháp nhân — demo báo một chuỗi
(`Exness Technologies Ltd`), tài khoản thật báo chuỗi khác (`Exness (SC) Ltd`). Khi đó live
**không tìm thấy hồ sơ và lặng lẽ rơi về số mặc định đang đoán**, không có gì báo. Nên
`ho_so_khac()` hỏi thẳng: *"chưa có hồ sơ cho sàn này — dùng cái đã đo ở kia?"*

> Máy **không tự chép**: nó không biết hai chuỗi đó là một sàn hay hai. Nhưng nó **BIẾT**
> mình đang không có hồ sơ, và im lặng rơi về số mặc định là đúng kiểu chết ngầm cả tầng
> này sinh ra để chặn. Đây là chỗ **duy nhất** người dùng phải tự quyết.

**Bản chép để lại vết** (`chep_tu` + `chep_luc`), giữ nguyên `do_luc` gốc. Xoá vết là biến
một bản sao thành một phép đo giả.

#### ⚠ 14.9a BA XUẤT XỨ — và chỉ hai trong ba mang từ demo sang thật được

Bảng Đề phòng nhìn thì đồng nhất, nhưng các dòng của nó trả lời **khác hẳn nhau** cho cùng
một câu: *"số này mang từ demo sang tài khoản thật được không?"*

| `LOAI` | Là gì | Mang sang thật? |
|---|---|---|
| `san` | **luật của sàn** — `kep_stops`, `filling`, `cho_bang_ms` | ✔ demo và thật cấu hình như nhau cho cùng symbol. Đo một lần, xài mãi |
| `khop` | **chất lượng khớp** — `deviation` (trượt giá) | ⚠ demo **không có thanh khoản thật**, số đo được chỉ là **CHẶN DƯỚI**. Chép thẳng là cài hụt đúng cái ăn tiền |
| `ta` | **cách app tự xử** — `thu_lai`, `cho_ms`, `cho_noi_giay` | ✔ không phụ thuộc tài khoản nào |

Không đánh dấu ra thì người dùng chép cả bảng — **kể cả dòng duy nhất không được chép.**

### 14.10 Bảng ĐỀ PHÒNG — hệ thống đang tự bảo vệ bằng gì, và số đó từ đâu ra

Trình bày như khối Tài khoản: nhãn · giá trị · ghi chú. Nó **BÁO CÁO**, không phải để
chỉnh — chỉnh là việc của bài hiệu chuẩn, tự ghi vào hồ sơ.

Ghi chú nói **NGUỒN** mới là chỗ có giá trị, và nó có **BA mức chứ không hai**:

| | |
|---|---|
| *đã chỉnh* | bài kiểm gặp lỗi rồi **tự sửa** con số này. Bằng chứng mạnh nhất |
| *đã kiểm* | chạy qua bài kiểm mà **không hỏng lần nào** → giả thuyết ĐÚNG SẴN |
| *đang đoán* | chưa hiệu chuẩn lần nào. **Con số bịa** |

> ⚠ Mức giữa là chỗ dễ hiểu nhầm nhất: **không đổi gì KHÔNG phải là chưa thử**, mà là thử
> rồi và không cần đổi. Gộp nó với *đang đoán* là vứt mất toàn bộ giá trị của một lần chạy
> sạch.

Mức *đã chỉnh* đọc thẳng từ `da_chinh` của hồ sơ (mỗi dòng dạng `kep_stops: 0 → 258 — vì
sao`), không đoán lại, không lưu trùng. Ba dòng cuối bảng là **kiểm kê luật**: bao nhiêu mã
đã có luật · bao nhiêu mã cần người · và **những mã CHƯA có luật đã gặp** (§14.7a).

Và bảng phải nói rõ **đo ở tài khoản nào · đang chạy ở tài khoản nào** — hai câu khác nhau,
và chỗ lệch giữa chúng là toàn bộ rủi ro của luồng *"đo demo, chạy thật"*.

### 14.11 ⭐ SỰ THẬT CỦA LIVE LÀ SÀN, không phải sổ mô phỏng

Ở tester, sự thật là sổ lệnh MÔ PHỎNG — vì không có sàn nào cả. Ở live, sự thật là **SÀN**:
chiến lược chỉ *quyết định*, còn cái gì thật sự tồn tại thì chỉ MT5 biết.

Vẽ chart Live từ sổ mô phỏng sai theo **hai chiều**, và chiều thứ hai mới nguy:

- lệnh do bài kiểm đặt — **CÓ THẬT, có ticket** — không hiện, vì engine không biết;
- engine "nghĩ" đã đặt mà sàn từ chối → chart vẽ ra một lệnh **KHÔNG TỒN TẠI**.

Nên nguồn lệnh của Live là `positions_get` · `orders_get` · `history_deals_get`, cắt từ mốc
bấm Live, trả về **đúng hình dạng `LenhVe`** mà `Chart` đang ăn — không thêm tầng nào, bỏ
bớt một tầng trùng lặp. Vị thế đã đóng ghép từ deal theo `position_id` (một vị thế có ít
nhất hai deal, vào và ra). Lệnh của bài kiểm mang cờ `la_kiem` để phân biệt được với lệnh
của chiến lược.

Đây cũng là **chỗ DUY NHẤT phải đổi** để cả bề mặt đọc của tester dùng được cho live:
`ApiLive._doi_kq()` trả **ảnh chụp SỐNG** thay cho `KetQua` bất biến của backtest.

### 14.12 Giao diện Live — dùng chung ba component với tester

**Không copy, không fork.** `Chart` · `BangSoLieu` · `Journey` nhập thẳng từ `../tester/`,
nên sau này sửa màu chart hay cách vẽ lệnh là đổi **CẢ HAI** cửa sổ — không có bản thứ hai
để trôi xa. Làm được thế vì `ApiLive` **kế thừa bề mặt ĐỌC của `ApiTester`** và chỉ đổi
đúng `_doi_kq()`; giao diện không biết mình đang xem live hay backtest.

Đổi lại phải **bịt những cửa không có nghĩa ở live** — `test_chay`, `test_lich_su_chay` trả
lỗi thẳng. Để hở thì bấm nhầm là chạy backtest **đè lên phiên live đang chạy**.

Khác tester đúng ba chỗ:

| | Tester | Live |
|---|---|---|
| thanh công cụ | phát lại, tua, nhảy mốc | **không có** — live chỉ có MỘT con trỏ: *bây giờ* |
| bảng dưới | Nhật ký · Thống kê | Vấn đề · **Kết nối** · Nhật ký (không Thống kê — sàn làm rồi) |
| con trỏ | thả đâu cũng được | luôn ở nến mới nhất, tự nhảy khi sàn đóng nến |

Ba con số của giao diện, mỗi con số một lý do:

- **`LO = 120` khung hình mỗi lần làm mới, không phải 900.** Đo được: `test_doan(-1, 900)`
  là **178 KB mỗi phút** qua cầu nối pywebview — mà cầu nối đó **đồng bộ và mã hoá payload
  hai lần**, nên *kích thước gói* mới là chỗ đau chứ không phải thời gian Python (13 ms).
  Live không tua lại nên lô chỉ để nhật ký có bối cảnh.
- **`TRAN_NEN = 2000`** — chart Live là chart **quan sát** như chart trading, không phải
  cuộn phim để tua. Tester giữ 60.000 vì ở đó bạn có quyền nhảy về bất kỳ đâu.
- **`digits` lấy từ chính engine đang chạy**, không viết cứng 2. Ô Symbol ở cổng chốt là ô
  gõ tự do: chọn EURUSD (5 số) mà bước giá 0,01 thì 1.08501 và 1.08528 gộp vào một mức,
  nến dẹp thành một vạch, và mọi con số in ra `.toFixed(2)` thành "1.09".

⚠ **`useKhungCuaSo` phải gọi ở TRANG Live.** Thiếu đúng một dòng đó là cửa sổ Live không
kéo được, không giãn được, không Aero Snap — vì `frameless=True` đã xoá viền hệ thống mà
không có ai dựng lại. Ba nút thu nhỏ/phóng to/đóng vẫn chạy nên nhìn thoáng qua tưởng thanh
tiêu đề ổn. `App.tsx` và `Tester.tsx` đều gọi; chỉ Live sót (cùng bẫy §12.12).

⚠ **Vá khung khớp theo `"— Live"` chứ không `"Live"` trần.** `tim_hwnd` khớp **chuỗi con**,
mà một chiến lược đặt tên "Live" sẽ làm tiêu đề tester (`Live — Strategy Tester`) khớp
trước → vá nhầm cửa sổ.

Kèm nút **`live_ve_so_do`** kéo cửa sổ vẽ lên trước: live chạy ngầm hàng giờ nên cửa sổ vẽ
hay bị lấp sau, mà không có đường quay về thì người dùng phải đi tìm trên taskbar.

### 14.13 Bài kiểm trên SÀN GIẢ — `tests/test_gui_lenh.py`

Ba module chạm tiền thật, và trước bài này chúng **không có một dòng test nào**. Cổng kiểm
trước khi đóng gói (`dong_goi.bat` bước 3) vẫn báo *"9/9 qua"* kể cả khi bảng xử lý retcode
bị bẻ hỏng hoàn toàn — tức **một bản phát hành biết đặt lệnh sai vẫn ra khỏi cửa**.

Sàn giả **nói dối ĐÚNG KIỂU sàn thật đã đo được**, và đó là toàn bộ giá trị của nó:

- khai `trade_stops_level = 0` nhưng ngưỡng thật là **215 điểm**;
- khai nhận FOK nhưng chỉ nhận **IOC**;
- vị thế vừa mở thì **đóng băng** một lúc (mã `10029`).

Bốn thứ được canh: mã thành công không được đọc thành thất bại · mã lạ trên lệnh thị trường
thì dừng · vòng hiệu chuẩn không được nói dối (vỡ giữa chừng phải ra `chua_hoi_tu`) · ý
định phải thành hiện thực. **Chạy được ở bất cứ đâu, không cần MT5.**

### 14.14 Trước khi nối LUỒNG ĐẶT LỆNH — ba thứ phải chốt

Hôm nay `gui_lenh` chỉ được gọi từ `ket_noi.hieu_chuan` và `don_rac`. **Chiến lược chưa nối
vào nó**, và đó là quyết định, không phải thiếu sót:

> Chưa ai nên để một cái máy đặt lệnh thật khi chưa ngồi nhìn nó chạy câm vài ngày và so
> nhật ký với tester.

Ngày nối, ba câu này phải có lời trước dòng code đầu tiên — cùng nếp §12.5:

1. **Sổ lệnh của ai là sự thật?** Engine giữ `so_lenh.Lenh` với id của ta, sàn giữ ticket.
   Lệnh sàn từ chối thì engine phải quên nó đi hay giữ lại? §14.11 đã chốt *hiển thị* theo
   sàn; còn *quyết định* của Manage đang đọc sổ mô phỏng.
2. **Lệch giữa ý định và hiện thực đi đâu?** `sua_truoc`/`da_sua` đang chảy vào nhật ký bài
   kiểm. Với lệnh thật, chúng phải vào **nhật ký lượt chạy** — nếu không thì "vì sao live
   khác backtest" vĩnh viễn không trả lời được.
3. **Đóng cửa sổ = dừng phiên, còn đúng nữa không?** §14.4 chọn thế vì chưa có gì phải giữ.
   Có lệnh thật rồi thì đóng cửa sổ mà bỏ mặc vị thế là chuyện khác hẳn.

---

## 15. ⭐⭐ TÌM CHIẾN LƯỢC TỰ ĐỘNG — kho đồ phải chuẩn hoá TRƯỚC

> **Trạng thái: đang duyệt từng hạng mục một.** Mục ghi ✅ là **đã duyệt nhưng CHƯA CÀI** —
> code vẫn là bản cũ cho tới khi có dòng "đã cài" kèm số đo. Đây là chỗ duy nhất ghi ý
> định của đợt này; đừng sửa §6.3 trước khi cài, để tài liệu không nói về một cơ chế
> chưa tồn tại.

### 15.0 Vì sao CHUẨN HOÁ là việc đầu tiên, không phải thuật toán

Đợt này **không tinh chỉnh tham số**. Đó là quyết định, không phải thiếu sót:

> **Không dò số ⇒ số phải tự đúng.**

Gánh nặng chuyển từ *thuật toán tìm* sang *bộ từ vựng*. Nếu được mài số cho khớp dữ liệu
thì kho đồ bẩn cũng không sao — thuật toán sẽ bù. Ta không làm thế, nên một luật tìm ra
phải là **một câu nói về thị trường**, không phải một con số vừa vặn với mấy năm XAUUSD.

**Phép thử nghiệm thu của kho đồ, một câu:**

> Một luật viết ra phải đọc được nguyên vẹn trên XAU, EUR, BTC và chỉ số —
> **không đổi một con số nào.**

Cái nào trượt phép thử đó chính là chỗ chiến lược sẽ chết khi đổi thị trường.

⚠ **PHÉP THỬ NÀY CÓ ĐIỂM MÙ, và nó đã cắn thật — §15.13b.** Nó ngầm giả định **cái thước
luôn khác 0**. Khi biến động thật sự bằng 0 (chợ chết lặng, nến phẳng), mọi tỉ số hoá
`0/0` hoặc luôn đúng, và **chuẩn hoá càng triệt để thì càng không còn gì bám vào**. Phải
có đúng một cái mốc **không co lại được** — và cái duy nhất như vậy là **chi phí giao
dịch**.

⭐ **MỘT KHO DUY NHẤT — không có thứ NGƯỜI dùng được mà MÁY không được.**

Từng có lúc tôi đề nghị chia hai (giữ `bps` cho người vẽ, cấm bộ sinh chọn). Người dùng bác,
và bác đúng:

> Nếu một món đồ không đủ rõ để giao cho máy, thì nó **cũng sẽ lừa người** — chỉ chậm hơn,
> nên khó bắt hơn. Sửa món đồ, đừng chia đối tượng.

Chia hai còn đẻ ra thứ tệ hơn: hai danh sách phải đồng bộ tay, đúng cái bẫy `CAN_ZONE` đã
cắn một lần. Và nó phá luôn lời hứa cuối cùng của dự án — *thứ máy tìm ra phải là thứ người
vẽ được* — vì hai bên không còn cùng một bộ đồ nghề. **Phép thử §15.0 là cổng DUY NHẤT:
món nào trượt thì ra khỏi kho, với ai cũng vậy.**

⚠ **KHO NẾN NÓI DỐI VỀ CHÍNH NÓ — mọi phép đo phải bỏ phần đầu.** `du_lieu/nen/XAUUSD.json`
ghi `tu: 2016-08-09` · `so_nen: 1.770.149`, nhìn như **10 năm M1**. Thật ra 2016–2020 chỉ
có **1 nến MỖI NGÀY** (1.789 nến — chắc một lần tải nhầm khung D1). M1 thật bắt đầu từ
**giữa 2021**, tức khoảng **5 năm rưỡi**. Chia train/test theo ngày mà không soi mật độ là
train trên rác. Soi trước khi đo bất cứ thứ gì: `số nến ÷ số ngày` phải ≈ **1.130** cho M1;
mấy năm đầu ra **1**.

### 15.1 ✅ Hạng mục 1 — THƯỚC ĐO NÉN: `atr_bps` → `ATR / ATR nền`

`atr_bps` **không phải phép chuẩn hoá ổn định**. Người dùng rút ra từ chạy thật, và đo
được trên toàn bộ M1 thật (353.821 nến M5, 2021–2026, ATR(14)):

| năm | giá TB | `atr_bps` trung vị | **% nến khớp cổng `atr < 7`** |
|---|---|---|---|
| 2021 | 1.794 | 5,18 | **69,9 %** |
| 2022 | 1.804 | 6,17 | 60,2 % |
| 2023 | 1.945 | 5,03 | **74,3 %** |
| 2024 | 2.381 | 6,11 | 62,4 % |
| 2025 | 3.345 | 7,84 | 40,7 % |
| 2026 | 4.676 | 12,48 | **7,8 %** |

Cùng một cái cổng, không đổi một con số: **2023 khớp 74 % số nến, 2026 khớp 7,8 %** —
chênh gần **10 lần**. Chiến lược tự tắt dần theo thời gian mà sơ đồ không nói một câu nào.

**Vì sao hỏng.** `atr_bps = ATR/close × 10⁴` chuẩn hoá theo **MỨC GIÁ**. Nhưng thứ trôi
không phải mức giá — mà là **CHẾ ĐỘ BIẾN ĐỘNG**. Vàng lên 2,6 lần (1.794 → 4.676) trong
khi ATR lên **6 lần**. Chia cho giá không chạm được vào phần chênh đó.

*(Đừng đọc nhầm §Engine `atr_bps` là "một ngưỡng cho mọi thang giá". Câu đó đúng về
**thang giá** — vàng $2.400 và EURUSD 1,10 — nhưng sai về **thời gian**: cùng một thị
trường, giá đi lên là ngưỡng trôi.)*

**Thước mới: đo ATR bằng ATR DÀI HẠN CỦA CHÍNH THỊ TRƯỜNG ĐÓ** — `ATR(14) / ATR(100)`.
"Nén" đúng nghĩa là *nhỏ so với chính nó dạo này*, không phải *nhỏ so với cái giá đang là
bao nhiêu*.

Tỉ số dao động quanh **1,00** (ATR ngắn xoay quanh ATR dài). **90 % số nến nằm trong
0,44 – 1,71**; thấp nhất 0,17 · cao nhất 5,20. Phân vị gần như không nhúc nhích:

| | 2021 | 2023 | 2026 |
|---|---|---|---|
| 10 % yên nhất | 0,45 | 0,47 | 0,63 |
| trung vị | 1,00 | 0,99 | 0,95 |
| 90 % | 1,60 | 1,57 | 1,47 |

Và đây là con số quyết định — **độ trôi của tỉ lệ khớp cổng qua các năm**:

| thước | ngưỡng | % nến khớp (năm thấp nhất .. cao nhất) | lệch |
|---|---|---|---|
| `atr_bps` | 7 | 7,8 % .. 75,8 % | **68 điểm** |
| tỉ số | 0,60 | 7,9 % .. 21,0 % | 13,1 điểm |
| tỉ số | 0,70 | 17,1 % .. 26,9 % | 9,9 điểm |
| **tỉ số** | **0,75** | **22,6 % .. 30,0 %** | **7,4 điểm** |
| tỉ số | 0,80 | 28,1 % .. 33,4 % | 5,3 điểm |

**Ổn định hơn khoảng 9 lần.**

**Cài bằng ĐƠN VỊ, không bằng toán hạng mới.** Thêm `× ATR nền` vào `core.DON_VI`, dùng
cho mọi toán hạng `khoang_cach`. Đúng con đường `atr_bps` đã đi khi nó tan thành đơn vị
`bps` (§`THANH_DON_VI`): **chuẩn hoá thuộc về CÁI THƯỚC, không thuộc về CÁI TÊN**. Không
đi đường này thì mỗi engine mới lại đẻ một `*_ti_so` của riêng nó và kho phình gấp đôi ở
mỗi đại lượng.

⚠ **CÁI THƯỚC KHÔNG ĐƯỢC LÀ THAM SỐ.** ATR nền **cố định 100 nến** — không cho chỉnh,
không đưa vào không gian tìm kiếm. Thước mà co giãn được thì nó không còn là thước, và một
bộ tìm kiếm được phép chỉnh thước sẽ chỉnh nó cho vừa dữ liệu — đúng thứ §15.0 vừa cấm.
**Ngưỡng** (`0,75`) thì ngược lại: đó là quyết định của chiến lược, vẫn nằm trong không
gian tìm.

**Hai chỗ nói thật, không giấu:**

1. **Càng siết càng kém ổn định.** Ở ngưỡng 0,50 tỉ lệ vẫn chênh 6 lần giữa các năm
   (2,1 % .. 13,6 %). Vùng dùng được là **0,6 – 0,8**; dưới 0,5 thì nến quá hiếm và số bắt
   đầu nhảy.
2. **Xu hướng nhẹ 2025–2026 là CÓ THẬT.** Ít nến yên hơn hẳn (ngưỡng 0,6 chỉ còn khớp
   7,9 % thay vì 21 %) — vàng dạo này biến động dai dẳng thật. Thước cũ **giấu** chuyện đó
   sau việc giá tăng; thước mới báo đúng. Một cái thước tốt phải để thị trường đổi lộ ra,
   không phải làm phẳng nó đi.

#### ✅ ĐÃ CÀI — và đây là bằng chứng nó làm đúng việc

`DON_VI` bỏ `bps`, thêm `atr_nen`; `core.CHU_KY_ATR_NEN = 100`; ba chỗ quy đổi
(`_quy_doi` · `quy_doi_cot` · `_khoang`) cài cùng lượt; `_dung_cot` xin cột ATR nền **vô
điều kiện** — nó có thể bị hỏi từ điều kiện, `dk_hop_le`, SL, TP, đệm, hay ô khoảng của
Sửa lệnh, và đi quét đủ sáu chỗ để tiết kiệm một cột là đổi một khoản rẻ lấy một chỗ
chắc chắn có ngày bỏ sót.

Sơ đồ mẫu đổi sang `nguong_nen = 0,75 [× ATR nền]`. **Chạy trên từng năm dữ liệu thật:**

| năm | nến M1 | lệnh | zone | tổng R | DD % | thắng % |
|---|---|---|---|---|---|---|
| 2022 | 352.976 | **485** | 1047 | −4,96 | 0,35 | 28,6 |
| 2023 | 351.899 | **421** | 938 | −29,96 | 0,66 | 23,1 |
| 2024 | 354.351 | **447** | 967 | −37,37 | 0,77 | 24,0 |
| 2025 | 353.129 | **453** | 1119 | +12,01 | 0,62 | 28,6 |
| 2026 (½) | 174.259 | 234 | 628 | +12,71 | 0,97 | 30,7 |

⭐ **Số lệnh mỗi năm giờ nằm trong 421–485 — chênh 15 %.** Với thước cũ, tỉ lệ nến khớp
cổng chênh **9,5 lần** giữa 2023 và 2026, nên số lệnh phải sụp theo. Đây chính là thứ
đợt này mua được: **chiến lược không còn tự tắt dần theo giá vàng.**

*(Bộ số neo CŨ — 550 lệnh · −19,52 R · DD 1,08 % — chính thức hết hiệu lực. Mốc mới để
phát hiện hồi quy là bảng trên, cụ thể **2025: 453 lệnh · +12,01 R · DD 0,62 % · vốn
10.045,83**.)*

### 15.2 Đã duyệt, chờ tới lượt cài

- **`lot` ra khỏi không gian tìm kiếm** → mỗi lệnh rủi ro đúng **x % vốn**, lot suy ra từ
  khoảng cách SL. Lot là **đơn vị tuyệt đối cuối cùng còn sót** trong kho: 0,01 lot trên
  tài khoản $10.000 khác hẳn trên $100.000, nên R vẫn đúng mà **tiền và sụt vốn thì không
  chuyển được sang tài khoản khác** — mà sụt vốn lại đúng là thứ sắp dùng để chấm điểm.
  Thêm nữa, để `lot` tự do là mời bộ tìm kiếm kéo đòn bẩy ăn điểm; chú thích trong
  `THAM_SO_MAC_DINH` đã ghi sẵn *"lot to là đòn bẩy chứ không phải lợi thế"*.
- **Thêm phép đo KHOẢNG CÁCH giữa hai mức giá.** Nay 7/19 toán hạng là `muc_gia`
  (close · open · high · low · ma · zone_HH · zone_LL) và chúng chỉ so được **BÊN NÀO**,
  không so được **BAO XA**: viết được `giá > MA`, không viết được `giá cao hơn MA 0,5 ATR`.
  Đây là dấu vết D_02 — nó chỉ cần biết *hướng* nên kho dừng ở đó.
- **Thêm toán hạng "lệnh này đã sống bao nhiêu nến".** Manage nay chỉ phản ứng được với
  **giá** và **zone**, không bao giờ phản ứng được với **thời gian** — không viết được
  *"lệnh chờ treo 20 nến không khớp thì huỷ"*.

#### ✅ 15.13 ĐÃ CÀI — `lot` biến mất, `rủi ro % vốn` thay chỗ

Trường `lot` **bỏ hẳn** khỏi khối Vào lệnh. Bộ chạy tự tính:

```
tiền mạo hiểm = vốn ĐÃ CHỐT × rủi_ro%
lot           = tiền mạo hiểm ÷ (khoảng cách SL × contract_size)
```

Vốn lấy từ **cùng một nguồn** với `drawdown_pt` (`PhienChay.tien["von"]`) — hai con số nói
về vốn mà lấy từ hai chỗ thì sớm muộn một chỗ nói sai. **Lãi nổi không tính vào**: cỡ lệnh
nhảy theo lãi nổi của lệnh đang mở là một vòng phản hồi, và nó phóng đại đúng lúc đang thua.

⚠ **Không làm tròn về bước lot 0,01.** Trong backtest, làm tròn là bịa thêm sai số vào đúng
cái vừa dựng lên để chính xác. Ở LIVE thì `gui_lenh` mới là chỗ biết bước lot thật của sàn,
và nó đã có tầng phòng vệ riêng (§14.7).

⚠ **Không đổi tự động, không có mặc định.** `0,01 lot` quy ra bao nhiêu phần trăm phụ thuộc
vốn LẪN khoảng cách SL của từng lệnh — không có con số nào đúng. Thiếu `rui_ro` thì soát
tĩnh **nói to**, y hệt cách `bps` và `pt` đã xử.

**Đo được — và đây mới là chỗ đáng nhìn:**

| năm | lệnh | tổng R | DD % *(lot 0,01)* | **DD % *(rủi ro 0,5 %)*** |
|---|---|---|---|---|
| 2022 | 485 | −4,96 | 0,35 | **15,11** |
| 2023 | 421 | −29,96 | 0,66 | **21,91** |
| 2024 | 447 | −37,37 | 0,77 | **20,09** |
| 2025 | 453 | +12,01 | 0,62 | **10,01** |
| 2026 (½) | 234 | +12,71 | 0,97 | **6,16** |

⭐ **Số lệnh và tổng R KHÔNG đổi một chút nào** — đúng như phải vậy: cỡ lệnh không quyết
định lệnh nào được đặt hay nó lãi mấy R.

⭐ **Sụt vốn thì đổi 20–30 lần.** Đó không phải chiến lược xấu đi, mà là **con số cũ đang
nói dối**: `0,01 lot` trên tài khoản $10.000 mạo hiểm ~0,045 % mỗi lệnh, nên `DD 0,66 %`
không nói được gì về chiến lược cả — nó nói về việc cỡ lệnh quá bé. Ở mức rủi ro người ta
thật sự dùng, năm 2023 sụt **21,9 %**. Đó mới là sự thật, và đó chính là con số bước
**phần thưởng** sắp phải chấm điểm.
- **Không thêm chỉ báo nào** (không RSI/ADX/Donchian…). Kho giữ đúng `atr` + `ma`. Chỗ
  biến thiên nằm ở zone + hình học vào lệnh + chính sách Manage, không nằm ở số chỉ báo.

### 15.3 ✅ Hạng mục 2 — ZONE RA KHỎI `engine_d02`, và khái niệm "engine" TAN

**Cơ chế zone đã hết chất D_02 từ trước**, chỉ là chưa ai dọn: `Engine.moi_nen()` đã rỗng,
điều kiện sinh zone nằm ở **cổng người dùng vẽ** (`cong_zone` → `bo_chay._nuoi_zone`), và
`nguong_nen_bps` đã rời khỏi `THAM_SO_CAN`. Nên đây là việc **chuyển nhà**, không phải
thiết kế lại.

⚠ **LỖI THẬT: bảng mô tả zone đang nói cơ chế ĐÃ CHẾT — và người dùng đọc được nó.**
`BANG_TRANG_THAI["zone"]` còn ba câu, cả ba đều sai từ lúc `moi_nen` rỗng đi:

```
"Sinh ra khi atr_bps tụt dưới ngưỡng, chết khi bung lên lại"
"Nến nén = atr_bps < ngưỡng"
"atr_bps ≥ ngưỡng → vùng CHẾT ngay, dù đang có lệnh chờ treo"
```

Zone nay sinh và chết **theo cổng zone trong sơ đồ**, không dính gì `atr_bps`. Mà chính
mấy câu đó là thứ hiện ra ở **menu File → Kho** — app đang dạy sai người dùng về chính nó.
Đây là mặt trái của quyết định "để code máy zone CÙNG FILE với bảng luật của nó": ở gần
nhau thì dễ sửa cùng lúc, nhưng **không có gì bắt buộc** phải sửa cùng lúc, và lần này thì
không.

**Chỗ đứng mới: `kho/zone.py`, một file riêng — KHÔNG nhập vào `nen_tang.py`.**
`nen_tang` là *"thứ MỌI chiến lược đều có"*; zone không phải — sơ đồ không vẽ cổng zone thì
không có zone nào. Zone là **một CƠ CHẾ chung, bật lên khi sơ đồ có cổng zone**. Ba loại
khác nhau, phải ở ba chỗ khác nhau:

| | nghĩa |
|---|---|
| `nen_tang` | luôn có — giá, sổ lệnh, lệnh này |
| `chi_bao` | tính từ nến, ai gọi thì có — atr, ma |
| `zone` | **cơ chế**, có khi sơ đồ định nghĩa nó |

**`engine_d02.py` XOÁ HẲN.** Zone dọn đi, bảng số dọn đi (§15.4) thì nó rỗng. Giữ một file
rỗng để nói *"D_02 từng ở đây"* là giữ rác — `core.md` đã kể chuyện đó rồi. Kho còn ba
module: `nen_tang` · `chi_bao` · `zone`.

Kéo theo, và phải dọn cùng lượt, nếu không lại thành một lời nói dối nữa:

- `kho.ENGINE` thành rỗng → `danh_muc()` bỏ cờ `la_engine`, hộp thoại Kho bỏ mục "engine",
  còn một danh sách phẳng theo nguồn.
- `ENGINE_TRA_LOI` **đổi tên** — không còn "engine" nào để trả lời. Nó nay là *"toán hạng
  do máy zone trả lời"*.
- `kho.CAN_ZONE` thì **không phải sửa**: nó tự gom từ module (`ENGINE_TRA_LOI` + cờ
  `can_zone`), không gõ tay. Đúng cái lợi mà thiết kế `kho/` dựng ra để có — chú thích
  ngay tại đó đã kể lần bản gõ tay lệch thật.

### 15.4 ✅ Hạng mục 3 — BẢNG SỐ CỦA D_02 RỜI KHO · sơ đồ mẫu thành FILE JSON

`kho/engine_d02.py` giữ `THAM_SO_MAC_DINH` — 11 con số cụ thể của Compress. Đó là **dữ
liệu của MỘT chiến lược**, không phải **đồ nghề**. Kho trả lời câu *"app tính được cái
gì"*, không phải câu *"chiến lược nào dùng số nào"*. Đúng một chỗ đọc nó: `api._so_do_mau()`.

**Và đi thẳng thêm một bước: sơ đồ mẫu ra khỏi `api.py`, thành một file JSON trong repo.**
`_so_do_mau()` hiện là ~200 dòng mô tả một chiến lược cụ thể nằm trong tầng mà §2 định
nghĩa là *"bề mặt DUY NHẤT giao diện gọi tới"*. Mọi chiến lược khác đều là JSON; sơ đồ mẫu
không có lý do gì đặc biệt. 11 con số đi theo nó, vào đúng bảng `tham_so` của chính file
đó — chỗ mọi chiến lược khác vẫn để số của mình.

⚠ **ID phải giữ nguyên** — §13.0f đã chốt sơ đồ mẫu mang **ID CỐ ĐỊNH**. Đổi sang JSON là
chép nguyên id, không sinh lại; `tests/test_so_do_mau.py` canh chỗ này.

**Hai trong 11 số đã chết vì hai hạng mục vừa duyệt** — sửa luôn trong lượt này, đừng chép
nguyên rồi để đó:

| số cũ | thành |
|---|---|
| `nguong_nen_bps = 7,0 [bps]` | `nguong_nen = 0,75 [× ATR nền]` (§15.1) |
| `lot = 0,01 [lot]` | rủi ro **x % vốn**, lot suy từ SL (§15.2) |

Chín số còn lại đã chuẩn hoá đúng rồi (× ATR · × ATR zone · × R · số nến) — giữ nguyên.

⚠ **Đổi `nguong_nen` là ĐỔI CHIẾN LƯỢC, không phải dọn dẹp.** Cổng `[2]` chuyển từ
"khớp 7,8 %–75,8 % số nến tuỳ năm" sang "khớp 22,6 %–30,0 %", nên **mọi con số neo của sơ
đồ mẫu sẽ đổi** — 550 lệnh · −19,52 R · DD 1,08 % không còn dùng làm vân tay được nữa.
Phải đo lại và ghi bộ số neo MỚI ngay trong lượt cài, nếu không thì mất luôn cái mốc dùng
để phát hiện hồi quy.

### 15.5 ✅ Hạng mục 4 — TRẦN ĐỘ PHỨC TẠP: ba con số, chỉ áp cho MÁY

Không chặn thì bộ sinh sẽ đẻ ra `atr < 0,73 và số nến ≥ 11 và bề rộng ≤ 3,8 và giá > MA và
ATR > 1,2 và số vị thế < 2 và zone chưa sinh lệnh → Mua`. Backtest có thể rất đẹp. Nhưng
mở ra **không đọc được nó nói gì**, và nó gần như chắc chắn chỉ vừa khít dữ liệu cũ.

⚠ **ĐẾM SỐ KHỐI LÀ CÁCH ĐO TỒI** — đo trên chính sơ đồ của người dùng mới lộ ra:

| sơ đồ | Entry | Manage | tổng khối | tổng đk | **đk/cổng nhiều nhất** | nhánh nhiều nhất |
|---|---|---|---|---|---|---|
| Mẫu Compress | 8 | 5 | 13 | 14 | 3 | 2 |
| Compress updated | 10 | 5 | 15 | 19 | **4** | 2 |
| Cây quyết định đầy đủ | 17 | 11 | **28** | 17 | 3 | **5** |

Cây quyết định đầy đủ có **gấp đôi số khối** mà **dễ đọc hơn**: nó trải quyết định ra nhiều
nhánh, mỗi nhánh hỏi 2–3 câu ngắn, thay vì dồn 4 câu vào một cổng.
→ **Nhiều khối không rối. Nhồi nhiều thứ vào một chỗ mới rối.**

**Ba trần riêng, KHÔNG cộng thành một điểm** — cộng lại thì lúc vượt trần không biết cái gì
vượt, và không sửa được đúng chỗ:

| đếm gì | trần cho máy | vì sao đếm nó |
|---|---|---|
| **điều kiện một cổng** | **4** | thứ bắt người đọc giữ nhiều câu trong đầu cùng lúc |
| **nhánh một ngã rẽ** | **3** | quá nhiều đường thì không theo dõi nổi |
| **khối Entry** | **12** | để sơ đồ còn vừa màn hình |
| **khối Manage** | **8** | |

Số `4` không bốc ra: đó đúng bằng chỗ nhiều nhất người dùng từng viết tay. Đủ để máy diễn
đạt được mọi thứ đã từng vẽ, mà không cho nó nhồi thêm.

**Trần chỉ áp cho BỘ SINH, không áp cho người vẽ.** App không đổi, `validate_process` không
thêm một luật nào, người dùng vẫn vẽ 28 khối · 6 điều kiện một cổng như hôm nay. Người vẽ
28 khối thì biết mình đang làm gì; máy sinh 28 khối là nó bịa.

**Căn cứ đặt trần là "đọc hết được không", không phải thống kê.** Độ phức tạp ở đây **không
phải mẹo chống overfit** — chống overfit đã có tập kiểm tra lo. Nó là **yêu cầu của sản
phẩm**: thứ nhận về phải là một sơ đồ đọc được. Chiến lược 40 khối tổng quát hoá tốt vẫn là
hỏng mục tiêu.

**Bốn số này nằm trong CÀI ĐẶT, chỉnh được.** Đây là quyết định về sản phẩm, không phải một
cái thước bên trong chiến lược — nên nó **không mâu thuẫn** với luật "cái thước không được
là tham số" ở §15.1. Nới trần không làm một con số nào trong sơ đồ đổi nghĩa; nới thước thì
có.

⚠ **Nhưng trần đã chỉnh được thì PHẢI LƯU KÈM TỪNG LẦN CHẠY.** Không lưu thì một kết quả
đẹp không phân biệt được là *tìm giỏi* hay là *ai đó vừa nới trần*. Cùng nếp §12.21: không
lưu kết quả, lưu **thứ đẻ ra nó**.

### 15.6 ✅ Hạng mục 5 — TÀI LIỆU ĐANG HỨA 13 TOÁN HẠNG KHÔNG CÓ THẬT

Ba con số, không cái nào đúng: `core.md` §6.3 ghi **32 toán hạng · 6 nhóm**, `README` ghi
**17**, thật ra **19 · 5 nhóm**.

Nhưng đây không phải lỗi đánh máy. §6.3 liệt kê **13 toán hạng chưa bao giờ tồn tại**:

```
Bid · Ask · Spread · Donchian(upper/lower) · Volume_MA
số lệnh hôm nay · drawdown % · là lệnh Mua · số nến đã sống · giá vào · giờ · thứ
```

Ai đọc `core.md` để thiết kế bộ sinh sẽ thiết kế cho một cái kho không có thật — nguy hơn
hẳn một con số sai. **Tài liệu là nguồn sự thật về Ý ĐỊNH, nên nó phải nói đúng cái ý định
ĐÃ THÀNH; ý định chưa làm thì để ở §13, không nằm trong bảng mô tả kho.**

**Cắt khỏi tài liệu (không làm, có lý do):**

| cắt | vì sao |
|---|---|
| `Donchian` · `Volume_MA` | đã duyệt **không thêm chỉ báo** (§15.2) |
| `Bid` · `Ask` | giá thị trường ngay lúc quyết định ≈ `close` của nến vừa đóng, lệch đúng spread |
| ~~`Spread`~~ | ⚠ **LÝ DO ĐÃ SAI — xem §15.13b.** Tôi gạch nó với lý do *"backtest chạy spread hằng số nên hỏi nó là vô nghĩa"*. Một hằng số vẫn là con số thật, và nó là **cái mốc DUY NHẤT không co lại khi biến động về 0** — thứ quý nhất trong kho. Quyết lại ở bước LUẬT CHƠI. |
| `giá vào` | `lãi (× R)` đã trả lời gần hết, và trả lời bằng đơn vị đã chuẩn hoá |
| `số lệnh hôm nay` | phụ thuộc múi giờ và lịch chợ, không đọc được sang thị trường khác |
| nhóm "Chuẩn hoá" | đã **hoà tan thành ĐƠN VỊ** (`atr_bps` → `atr [bps]`) — đúng thiết kế, chỉ tài liệu chưa theo |

**Thêm thật (2 lỗ hổng có thật):**

- **`là lệnh Mua`** — Manage hôm nay **không phân biệt được lệnh mua với lệnh bán**. Không
  viết được luật quản lý bất đối xứng (*"lệnh mua mà giá tụt dưới MA thì đóng"*). Rẻ, và là
  lỗ hổng thật.
- **`drawdown %`** — cầu dao rủi ro (*"sụt quá 5 % thì ngừng vào lệnh"*). Chuẩn hoá được
  theo % vốn, và ăn khớp với việc `lot` vừa đổi sang **% rủi ro** (§15.2). §6.3 từng xếp
  "cầu dao" vào đây rồi lại không làm.

⚠ **BỎ `giờ` / `thứ`, và bỏ có chủ ý.** Cổ điển, hữu ích thật, nhưng đây là **toán hạng dễ
overfit nhất trong cả kho**: bộ tìm kiếm sẽ moi ra *"chỉ đánh 14h thứ Ba"* — một câu không
nói gì về thị trường. Và nó trượt thẳng phép thử §15.0: crypto chạy 24/7, "thứ Ba" không
đọc được sang đó. Cần lọc phiên thì thêm lại sau, kèm ca dùng thật.

**Kho sau đợt này: 22 toán hạng** = 19 hiện có + `số nến đã sống` + `là lệnh Mua` +
`drawdown %`. Sửa cả `core.md` §6.3 lẫn `README` cho khớp — và **lấy số từ
`len(kho.TOAN_HANG)`, đừng gõ tay lần nữa**, vì đúng cái gõ tay là thứ vừa lệch ba chỗ.

### 15.7 ✅ Hạng mục 6 — BỎ HẲN đơn vị `bps`

`bps` (phần vạn của giá) chính là **cái thước vừa bị chứng minh là trôi** ở §15.1. Nói cho
công bằng thì nó không sai — nó chuẩn hoá đúng theo **thang giá** (vàng $4.676 so được với
EURUSD 1,10), chỉ hỏng theo **thời gian**, khi chính thị trường đó đi lên. Nhưng "đúng một
nửa" không đủ để ở lại kho sau luật MỘT KHO DUY NHẤT (§15.0).

**Bỏ nó không mất gì — đo trên cả ba sơ đồ đang có, `bps` chỉ nằm ở ĐÚNG MỘT VIỆC:**

| sơ đồ | dùng `bps` ở đâu |
|---|---|
| Mẫu Compress | `nguong_nen_bps = 7,0` · Entry `[2] atr < …` · Manage `[1A] atr ≥ …` |
| Compress updated | `nguong_nen_bps = 7,0` · Entry `[2] atr < …` |
| Cây quyết định đầy đủ | `nguong_vung = 7,0` · Entry `[2] atr < …` |

Cả ba đều là **ngưỡng nén** — đúng thứ §15.1 thay bằng `× ATR nền`. Không có chỗ nào khác
trong toàn bộ điều kiện, SL, TP hay đệm dùng tới nó.

⚠ **KHÔNG có phép đổi tự động, và đó là chủ ý.** `7 bps` không quy ra `× ATR nền` bằng bất
kỳ phép nhân nào — tỉ số phụ thuộc ATR nền lúc đó. Gặp `bps` trong file cũ thì **soát tĩnh
nói to** ("chưa chọn cách tính"), y hệt cách `pt` đã xử: *một phép đổi đúng-một-nửa là loại
hỏng tệ nhất — file vẫn chạy, chỉ sai.*

`DON_VI` sau đợt này có **6**: `gia` · `atr` · `atr_nen` 🆕 · `atr_zone` · `R` · `bien_zone`
— bỏ `bps`, thêm `atr_nen`, nên số lượng không đổi. *(`pt` đã bỏ từ trước.)*

### 15.8 ✅ Hạng mục 7 — MỐC NEO lấy thẳng từ kho, bỏ danh sách gõ tay

Khối **Vào lệnh** nói lệnh nằm ở đâu bằng hai phần: `Buy Stop tại [mốc neo] + [đệm]`. Mốc
neo là **gốc**, đệm chỉ là nhích ra khỏi gốc đó.

`core.MOC_ENTRY` hiện gõ tay **3 dòng**: `zone_HH` · `zone_LL` · `gia_hien_tai`. Mà kho đã
biết tính **7 mức giá** (`loai: muc_gia`): `close` · `open` · `high` · `low` · **`ma`** ·
`zone_HH` · `zone_LL`.

⚠ **Đây là DANH SÁCH GÕ TAY THỨ HAI nằm ngoài kho** — đúng cái bẫy `CAN_ZONE` đã cắn (chú
thích tại `kho/__init__.py` kể lần bản gõ tay còn sót `zone_range_atr` sau khi toán hạng đó
bị gỡ). Nó chỉ có 3 dòng vì hồi viết chỉ cần đủ cho D_02, mà D_02 chỉ neo vào mép zone.

**Sửa: ô mốc neo đọc thẳng `loai == "muc_gia"` từ kho.** Không thêm một từ vựng nào, nhưng
viết được ngay những câu hôm nay không viết được:

```
Buy Stop  tại [MA]        + 0,2 ATR     ← neo vào đường trung bình
Buy Stop  tại [đỉnh nến]  + 0,1 ATR     ← phá đỉnh nến trước
```

**`MOC_CAN_ZONE` cũng bỏ** — suy được từ `kho.CAN_ZONE`, không cần bản thứ hai.

**Bỏ `gia_hien_tai`, dùng `close`.** Nó là dấu vết còn lại của danh sách gõ tay: không có
trong kho, nên không ai kiểm được nó nghĩa là gì. Tại biên nến — chỗ duy nhất sơ đồ được
chạy — "giá hiện tại" và `close` của nến vừa đóng là cùng một mức, lệch đúng spread.
Đo được: đang có **2 khối trong *Compress updated*** dùng nó (Buy/Sell Stop neo tại giá
hiện tại), đổi sang `close` là xong, hành vi không đổi.

*(Ghi chú: `gia_hien_tai` gần như chắc chắn là rác còn lại từ loại lệnh `limit` đã bị gỡ —
chú thích tại `LOAI_LENH` kể rằng `limit` từng neo vào giá hiện tại.)*

#### ✅ ĐÃ CÀI — và luật lọc, không phải danh sách

`core.MOC_ENTRY` nay **sinh ra từ kho**:

> mốc neo = một **MỨC GIÁ** (`loai == "muc_gia"`) mà app đọc được **không cần hỏi thêm
> con số nào** — tham số nhiều nhất là `tf`, và `tf` pin vào **khung quyết định** (nhịp
> của khối Bắt đầu, nhìn thấy được trên sơ đồ).

Ra **6 mốc**: `close` · `open` · `high` · `low` · `zone_HH` · `zone_LL` — gấp đôi bản gõ
tay, và thêm được `Buy Stop tại [đỉnh nến] + 0,1 ATR` mà không thêm một từ vựng nào.
`MOC_CAN_ZONE` giao với `kho.CAN_ZONE`, cũng không gõ tay.

⚠ **`ma` CHƯA có mặt, và đó là luật lọc chứ không phải bỏ sót.** Neo vào MA thì phải nói
MA chu kỳ bao nhiêu — một con số không hiện ra là đúng thứ cả hệ thống này cấm. Cho nó
vào đòi ô mốc neo phải thành **bộ chọn toán hạng đầy đủ** như vế trái của điều kiện
(component `OToanHang` đã có sẵn, chỉ thiếu một phép lọc theo `loai`). Đó là một việc của
giao diện — làm riêng thì sạch hơn nhét kèm vào đây.

**Nhãn giờ trùng khít nhãn ở dòng điều kiện** (`Zone — đỉnh (HH)`, không phải
`Đỉnh zone (HH)`). Trước đây cùng một mức giá đọc ra hai cái tên tuỳ chỗ nhìn.

**Bộ chạy: ba nhánh `if` gõ tay → một lời gọi `_lay_toan_hang`.** Mốc neo đi qua đúng cây
cầu mà điều kiện đi, nên thêm một mốc không phải sửa hai nơi nữa. `_dung_cot` xin cột cho
mốc y như cho một vế điều kiện — quên chỗ đó thì `_vao_lenh` ném *"chưa được tính trước"*
ở đúng cây nến đầu tiên khối được chạy tới.

⚠ **Lệnh THỊ TRƯỜNG bỏ qua mốc neo, và hộp thoại ẨN hẳn ô đó.** Nó khớp ở giá thị trường;
bịa ra một cái mốc rồi khớp ở chỗ khác mới là nói dối. Bày ra một ô mà bộ chạy bỏ qua là
đúng thứ `DON_VI_CHO` đã cấm — *"bày ra một lựa chọn vô nghĩa rồi soát tĩnh mắng là tệ hơn
không bày"*.

**Khối Sửa lệnh cũng có mốc neo** (§15.10), **tuỳ chọn** — bỏ trống thì đo từ giá hiện
tại, đúng hành vi cũ, nên file cũ mở ra không đổi gì. Có mốc thì viết được
`SL tại [đáy zone] − 0,2 ATR`. `normalize_action` **vứt** mốc ở chế độ không đo khoảng
cách (`hoà vốn` · `kết thúc`) — giữ lại là để rác.

⭐ **Sơ đồ mẫu không đổi một con số nào** (485 · 421 · 447 · 453 · 234). `tsc --noEmit` và
`vite build` sạch.

### 15.9 ✅ Hạng mục 8 — GIỮ 8 PHÉP SO · không thêm `cắt lên` / `cắt xuống`

`core.PHEP_SO` có 8: `< ≤ > ≥ = ≠` · `là ĐÚNG` · `là SAI`. §6.3 hứa thêm ba cái không có:
`trong khoảng` · `cắt lên ↗` · `cắt xuống ↘`.

`trong khoảng` **bỏ đúng, không bàn lại**: `a ≤ x ≤ b` là hai dòng, mà một cổng vốn đã là
AND — thêm nó chỉ là cách viết thứ hai cho cùng một điều.

`cắt lên` / `cắt xuống` thì từng nằm trong dropdown mà **chưa bao giờ chạy** (`_so_sanh` ném
`LoiChay`, tức chọn vào rồi bấm ▶ là backtest chết giữa chừng), nên bị gỡ. Câu thật là:
**thêm lại đàng hoàng không? — KHÔNG.** Ba lý do, ghi ra để sau này không ai mở lại:

**1. Nó đòi BỘ NHỚ, mà app này dựng trên nguyên tắc không nhớ gì.**
`giá > MA` là **trạng thái** (đúng suốt nhiều nến); `giá cắt lên MA` là **sự kiện** (đúng
một nến). Muốn biết "vừa cắt" thì phải nhớ nến trước hai vế bằng bao nhiêu — một trạng thái
**không hiện trên sơ đồ**. Bên Manage còn nặng hơn: sơ đồ chạy một lượt cho MỖI lệnh, nên
bộ nhớ phải khoá theo *(điều kiện, lệnh)*. Đó đúng là máy trạng thái ẩn mà §6.1 và §7.5 cố
ý xoá bỏ.

**2. Thứ người ta cần "cắt lên" để làm thì hệ thống đã có cách RÕ HƠN.** Công dụng chính của
nó là *chỉ vào lệnh một lần, không vào lại mỗi nến*. Ở đây câu đó được hỏi thẳng:
`zone này đã sinh lệnh là SAI` · `số lệnh chờ = 0` · `lệnh này còn thuộc zone hiện hành`.
Ba câu ấy **nhìn sơ đồ là thấy**; "cắt lên" thì giấu cùng ý đó vào trong một cái tên.

**3. Nó phá một luật ngầm cả kho đang giữ:** mọi toán hạng là câu hỏi về **LÚC NÀY**, trả
lời được chỉ bằng trạng thái hiện tại. "Cắt lên" là câu hỏi về **hai thời điểm** — cho nó
vào là mở cửa cho cả họ "N nến trước" tràn theo, và `shift` vừa mới bị gỡ khỏi toán hạng giá
đúng vì lý do đó.

### 15.10 ⚠ Hạng mục 9 — LỖI THẬT: `Dời SL` NỚI LỎNG ĐƯỢC STOP

`SUA_CHE_DO` có **4** (`doi_sl` · `doi_tp` · `hoa_von` · `ket_thuc`); §6.3 ghi **7** và
docstring của `_sua_lenh` ghi *"Bảy chế độ"* — thừa `trailing` và `dong_mot_phan`, hai cái
**chưa từng chạy** (`dong_mot_phan` ném thẳng *"chưa được cài trong sổ lệnh"*). Xoá khỏi
tài liệu.

⚠ **Nhưng đây mới là chuyện: `doi_sl` đặt SL cách GIÁ HIỆN TẠI một khoảng, và KHÔNG so với
SL cũ.**

```python
moi = ctx.bid - d if (l.huong == sl.MUA) == (cd == "doi_sl") else ctx.bid + d
setattr(l, "sl" if cd == "doi_sl" else "tp", moi)      # ← gán thẳng, không kiểm
```

Mua ở 2400, luật *"SL cách giá 10"*:

```
giá 2410  →  SL = 2400   ✔ siết
giá 2405  →  SL = 2395   ✘ SL LÙI RA
giá 2395  →  SL = 2385   ✘ lùi tiếp
```

**SL chạy theo giá đi xuống, nên lệnh không bao giờ chạm SL.** Lỗ mở rộng không giới hạn.

⭐ **Đây là ca mẫu của thứ nguy nhất trong cả dự án: BỘ TÌM KIẾM LÀ MỘT CÁI FUZZER NHẮM VÀO
CHÍNH SIMULATOR.** Mọi lỗ hổng mô phỏng đều thành tiền miễn phí và optimizer sẽ tìm ra. Lỗ
này cho ra một chiến lược *"không bao giờ thua"* trong backtest — vì lệnh lỗ không bao giờ
đóng — và nó sẽ đứng đầu bảng xếp hạng. Người vẽ tay chưa ai vấp phải vì không ai cố tình
viết một cái SL chạy trốn; máy thì không có ý định gì cả, nó chỉ leo lên chỗ điểm cao.

**Sửa: `Dời SL` CHỈ ĐƯỢC SIẾT, KHÔNG ĐƯỢC NỚI** (theo hướng lệnh). Luật cứng, không phải
tuỳ chọn: nới SL sau khi vào lệnh là **phá luôn định nghĩa 1R** mà mọi con số của hệ thống
đang đo bằng nó — lệnh không còn rủi ro một R nữa, mà `tong_R` thì vẫn cộng như thường.

⚠ **BẤT ĐỐI XỨNG, và đó là chủ ý: TP để tự do.** Dời TP xa ra không tăng rủi ro một xu nào.
Cùng nếp §14.7b — ba luật bất đối xứng bên `gui_lenh` cũng dựng trên đúng lý lẽ này.

**Chỗ thứ hai: `Sửa lệnh` KHÔNG có mốc neo.** Khối Vào lệnh chọn được gốc (đỉnh zone · MA …
— §15.8), khối Sửa lệnh thì SL luôn tính từ `ctx.bid`. Nên không viết được `SL tại [đáy
zone] − 0,2 ATR`. **Dùng chung đúng cơ chế mốc neo của §15.8** — hai khối cùng nói về một vị
trí giá thì phải nói bằng cùng một cách, không đẻ cách thứ hai.

**Không thêm `đóng một phần`:** nó bắt sổ lệnh chia nhỏ lot và phá cách tính *một lệnh =
một R*. Cần thì thêm sau, kèm ca dùng thật.

#### ✅ ĐÃ CÀI — `bo_chay._siet_sl`, một cái kẹp cho CẢ HAI lối vào

`doi_sl` **và** `hoa_von` cùng đi qua nó. `hoa_von` cũng phải kẹp, và đây là chỗ dễ bỏ
sót: SL đã siết quá hoà vốn rồi thì kéo nó **về** hoà vốn chính là nới ra. Sơ đồ mẫu chặn
ca đó bằng cổng *"SL chưa ở hoà vốn"* — nhưng **một sơ đồ do máy sinh thì không có gì bắt
nó phải vẽ cái cổng ấy**, mà đó chính là đối tượng ta đang dựng hệ thống cho.

`tp` **không** đi qua kẹp — bất đối xứng có chủ ý.
SL đang là `None`/`0` thì mọi SL đều tính là siết: từ rủi ro vô hạn xuống hữu hạn.

**Bài kiểm neo cả hai tầng** (`tests/test_bo_chay.py`): bốn ca đơn vị (mua/bán × siết/nới)
+ **một bài BẰNG HÀNH VI** — giá rơi đều, Manage dời SL cách giá 10 mỗi nến. Không kẹp thì
SL tụt theo giá mãi và lệnh sống tới hết dữ liệu; có kẹp thì SL đứng nguyên ở `giá vào −
10` và giá rơi xuống chạm nó (`ly_do_dong == "sl"`). Bài đơn vị một mình không đủ: cái
đáng sợ là **hành vi lệnh không bao giờ đóng**, không phải một phép so.

⭐ **Sơ đồ mẫu KHÔNG đổi một con số nào** sau lượt này (485 · 421 · 447 · 453 · 234 lệnh,
trùng khít bảng §15.1) — đúng như phải vậy: nó vốn đã chặn ca nới bằng cổng.

### 15.11 ⏸ Hạng mục 10 — NHIỀU ZONE CÙNG LÚC: hoãn, có chủ ý

Hôm nay mỗi lúc chỉ có **một** zone (`so.zone_hien_hanh()`), các zone nối đuôi nhau:
`A sống → chết → B sống → chết → C…`. Mọi toán hạng zone đều hỏi về zone đang đếm lúc này.

**Không viết được:** một zone lớn trên H1 và một zone nhỏ trên M5 chạy song song, rồi hỏi
*"giá đang nén ở cả hai khung không"*. Cũng không hỏi được về *zone trước đó*.

**Vì sao không rẻ:** có hai zone thì `Zone — đỉnh (HH)` hỏi đỉnh của **zone nào**? Phải đặt
tên zone, phải chọn zone trên giao diện, rồi kéo theo *lệnh thuộc zone nào* ·
*zone nào đã sinh lệnh* · *cổng nào nuôi zone nào*. Đụng `so_lenh.Zone`,
`zone_hien_hanh()`, `_nuoi_zone`, `_dat_zone_thu`, và cả luật "cổng zone chỉ đặt ở Entry".

**Mất gì khi hoãn — nói thẳng:** mọi chiến lược bộ tìm kiếm đẻ ra sẽ là loại **một zone**,
tức cùng hình dạng với D_02. Đó là giới hạn thật của phase này, không phải chuyện nhỏ.

**Vẫn hoãn, vì đúng một lý do:**

> Chín hạng mục trên đều là **DỌN DẸP**. Cái này **ĐỔI CƠ CHẾ**.

Trộn hai loại vào một đợt thì lúc số chạy ra khác, không phân biệt được là do dọn hay do đổi
cơ chế. Dọn xong → chạy lại → số ổn định → rồi mới mở cái này.

### 15.12 CHỐT KHO ĐỒ — bảng nghiệm thu

**Ngăn 1 · TOÁN HẠNG — 22** *(19 cũ + 3 mới)*

| nhóm | | |
|---|---|---|
| Giá (4) | `close` `open` `high` `low` | |
| Chỉ báo (2) | `atr` `ma` | không thêm cái nào |
| Sổ lệnh (3) | `so_vi_the` `so_lenh_cho` | 🆕 `drawdown_pt` |
| Lệnh này (6) *chỉ Manage* | `lenh_da_khop` `lenh_sl_hoa_von` `lenh_lai_R` `lenh_thuoc_zone` | 🆕 `so_nen_song` · 🆕 `la_lenh_mua` |
| Zone (7) | `zone_dem` `zone_HH` `zone_LL` `zone_range` `zone_atr_tb` `zone_hop_le` `zone_da_sinh_lenh` | |

**Ngăn 2 · VÀO LỆNH** — hướng (2) · loại (2: market/stop) · **mốc neo = mọi toán hạng
`muc_gia` (7)** · đệm · SL · TP · **rủi ro x % vốn** *(thay `lot`)*

**Ngăn 3 · SỬA LỆNH** — 4 chế độ (`doi_sl` `doi_tp` `hoa_von` `ket_thuc`), **có mốc neo**
như ngăn 2, và **`doi_sl` chỉ siết không nới**

**Thước & phép**

| | |
|---|---|
| đơn vị (6) | `gia` · `atr` · 🆕 `atr_nen` · `atr_zone` · `R` · `bien_zone` — **bỏ `bps`** |
| phép so (8) | `< ≤ > ≥ = ≠` · `là ĐÚNG` · `là SAI` — không thêm `cắt lên/xuống` |
| ATR nền | **cố định 100 nến, không phải tham số** |
| thêm phép đo | khoảng cách giữa hai mức giá *(đang thiếu hẳn)* |

**Trần cho bộ sinh** *(nằm trong cài đặt, chỉnh được, lưu kèm mỗi lần chạy)*
4 điều kiện/cổng · 3 nhánh/ngã rẽ · 12 khối Entry · 8 khối Manage

**Module kho** — `nen_tang` · `chi_bao` · `zone` 🆕. **`engine_d02.py` xoá hẳn**, khái niệm
"engine" tan. Sơ đồ mẫu thành **file JSON**, bảng số của nó đi theo nó.

### 15.14 ✅ ĐÃ CÀI XONG — bảy đợt, test xanh sau từng đợt

| đợt | việc | số của sơ đồ mẫu |
|---|---|---|
| 1 | Kho chuyển nhà · 3 toán hạng mới → **22** | **trùng khít** |
| 2 | Thước: bỏ `bps`, thêm `× ATR nền` | **đổi** — bộ neo mới |
| 3 | `_siet_sl` — SL chỉ siết | trùng khít |
| 4 | Mốc neo 3 → 6, dùng chung với Sửa lệnh | trùng khít |
| 5 | `lot` → **rủi ro % vốn** | lệnh/R trùng khít, **DD đổi 20–30×** |
| 6 | Sơ đồ mẫu → `mau/compress.json` (−190 dòng khỏi `api.py`) | trùng khít |
| 7 | `core.md` §6.3 + `README` khớp thực tế | — |

**BỘ SỐ NEO MỚI** (thay 550 lệnh · −19,52 R · DD 1,08 %, đã hết hiệu lực):

| năm | lệnh | zone | tổng R | **DD %** | thắng % |
|---|---|---|---|---|---|
| 2022 | 485 | 1047 | −4,96 | 15,11 | 28,6 |
| 2023 | 421 | 938 | −29,96 | 21,91 | 23,1 |
| 2024 | 447 | 967 | −37,37 | 20,09 | 24,0 |
| **2025** | **453** | **1119** | **+12,01** | **10,01** | **28,6** |
| 2026 (½) | 234 | 628 | +12,71 | 6,16 | 30,7 |

*(XAUUSD · spread 90 điểm · commission 3,5/lot · vốn 10.000 · rủi ro 0,5 %/lệnh.)*

⚠ **File cũ sẽ BÁO LỖI khi mở, và đó là chủ ý.** Ba thứ không đổi tự động được vì không có
phép đổi nào đúng: `bps` → `atr_nen` · `lot` → `rui_ro` · `atr_bps` → đơn vị rỗng. Soát tĩnh
nói to ở đúng khối sai. Cùng nếp `pt` đã xử: *một phép đổi đúng-một-nửa là loại hỏng tệ
nhất — file vẫn chạy, chỉ sai.*

#### ⚠ 15.13a LỖ HỔNG CỦA SIZING THEO RỦI RO: **R siêu nhỏ → LOT khổng lồ**

Lộ ra ngay khi di cư file người dùng, và nó là một ca mẫu nữa của *"bộ tìm kiếm là cái
fuzzer nhắm vào simulator"*.

`lot = vốn × rủi_ro% ÷ (R × contract_size)` — **R nằm dưới mẫu số, và không có sàn chặn**.
Zone gần như phẳng cho `zone_atr_tb ≈ 0` ⇒ `R ≈ 0` ⇒ lot nổ tung. Đo trên *Compress
updated*, năm 2024:

| | |
|---|---|
| R nhỏ nhất | **0,0004** giá *(bốn phần mười nghìn của một đô vàng)* |
| lot lớn nhất | **862,15** |
| lot trung vị | 0,19 — hoàn toàn bình thường |
| 85 lệnh có lot > 1 | gánh **90 %** tổng phí |
| lãi/lỗ THÔ | −1.504 |
| **phí hoa hồng** | **−5.616** (3,5/lot × 1.605 lot) |

**Phí chiếm 79 % tổng thua lỗ.** Rủi ro *danh nghĩa* vẫn đúng 0,5 % mỗi lệnh — theo đúng
công thức — nhưng **phí thì bám vào LOT chứ không bám vào rủi ro**, nên một cái SL hẹp phi
lý biến thành một hoá đơn phí phi lý. Và ngoài đời không sàn nào nhận 862 lot.

Lot cố định **giấu** chuyện này: 0,01 lot thì phí là 3,5 xu, vô hình.

⚠ **Sơ đồ mẫu KHÔNG dính** — đã kiểm: lot lớn nhất 0,46–1,54 · R nhỏ nhất 0,30–0,99 · phí
175–454 $/năm. Nên bộ số neo §15.13 sạch. Cái bẫy chỉ cắn sơ đồ nào cho phép zone suy
biến (*Compress updated* hạ `zone_range_max` xuống 3,0 và đẻ gấp đôi số zone).

#### ⭐⭐ 15.13b ĐIỂM MÙ CỦA CHUẨN HOÁ — thước co lại thì mọi tỉ số vô nghĩa

Trước khi đề xuất luật mới, tôi thử sửa **bằng đúng đồ nghề đã có**: thêm một dòng
`Zone — ATR trung bình ≥ 0,1 × ATR nền` vào phần ĐẾM của cổng zone.

**Đo được: không đổi MỘT con số nào.** 994 lệnh · −51,43 R · DD 71,67 % · lot lớn nhất
862,15 · phí 5.616 — trùng khít cả hai bên. Điều kiện có sống sót qua `normalize` (3 → 4
dòng đếm), nó chỉ đơn giản là **không bao giờ trượt**.

**Vì sao — và đây là chỗ đáng ghi nhất của cả đợt này:**

`Compress updated` đặt `SL = mép zone đối diện`, nên `R ≈ bề rộng zone + đệm`. Cổng của nó
đã có chốt chặn `zone_range ≥ 1 × ATR`, nghe rất chắc. Nhưng nó là một **TỈ SỐ**:

```
thị trường chết lặng:   ATR        = 0,0002
                        zone_range = 0,0004
                        0,0004 / 0,0002 = 2  ≥ 1   ✓ QUA CỔNG
⇒ zone hợp lệ · SL = 0,0004 $ · lot = 862
```

Mọi con số đều "đúng luật". Thêm một chốt chặn theo tỉ số nữa cũng vô ích, **vì cái mẫu số
cũng co lại theo** — đó chính là thứ phép đo ở trên chứng minh.

> ⚠ **Phép thử nghiệm thu ở §15.0 có ĐIỂM MÙ, và tôi phải ghi nó ra:**
> *"một luật phải đọc được nguyên vẹn trên mọi thị trường"* ngầm giả định **cái thước
> luôn khác 0**. Khi biến động thật sự bằng 0, mọi tỉ số hoá `0/0` hoặc luôn đúng, và
> **chuẩn hoá càng triệt để thì càng không có gì bám vào**.

**Cần đúng MỘT cái mốc không co lại được.** Và cái duy nhất như vậy là **CHI PHÍ GIAO
DỊCH**: spread 0,09 $ là 0,09 $, thị trường chết lặng hay không cũng thế. Từ đó ra một câu
duy nhất, thuộc bước **LUẬT CHƠI**:

> **R phải lớn hơn chi phí vào-ra.** SL hẹp hơn spread + phí thì lệnh đó không thể lãi,
> bất kể thị trường đi đâu.

⚠ **SỬA LẠI MỘT QUYẾT ĐỊNH CỦA CHÍNH §15.6.** Ở đó tôi gạch `Spread` khỏi kho với lý do
*"backtest dùng spread HẰNG SỐ — hỏi nó trong backtest là vô nghĩa"*. **Lý do đó sai.** Một
hằng số vẫn là một con số thật, và ở đây nó là **cái mốc duy nhất không co lại** — tức là
đúng thứ quý nhất trong cả kho. Có đưa `Spread` trở lại hay chốt chặn nằm thẳng trong luật
chơi (không thành toán hạng) là câu hỏi mở của bước sau.

*(Ghi cả quá trình vào đây có chủ ý: tôi đã đi tìm cách sửa TRƯỚC khi hiểu vì sao nó hỏng,
và trượt ba lần — hai lần đặt sai chỗ, một lần sửa nhầm tầng. Phép đo phủ định ở trên đáng
giá hơn nhiều so với cái luật tôi định thêm ngay từ đầu.)*

---

## 16. ⭐⭐ LUẬT CHƠI — môi trường mà chiến lược phải chơi trong đó

> Kho đồ (§15) trả lời *"được dùng gì"*. Mục này trả lời *"luật của trò chơi là gì"* —
> và luật thì **AI không được đổi, AI chỉ được chơi**.

Phần lớn luật đã khoá và có bài kiểm từ lâu: nhịp chạy lại mỗi nến (§6.1) · Manage trước
Entry (§6.0) · Entry chỉ tạo Manage chỉ sửa · đường đi 4 điểm trong một nến (§12.2) · bốn
luật khớp (§12.13d) · tính xác định · không nhìn trước tương lai. Mục này chỉ ghi những
thứ **còn hở**.

### 16.1 ✅ Hạng mục 1 — LUẬT SÀN vào backtest

**`du_lieu/ho_so_ket_noi.json` đã ĐO SẴN luật sàn thật, và backtest không dùng một dòng
nào.** `CaiDat` chỉ biết spread · point · contract_size · deposit · commission; còn
`don_bay` thì là một **cài đặt CHẾT** — không có phép kiểm ký quỹ nào trong bộ chạy.

Số đo được (Exness, XAUUSD, 12/08/2026):

```
lot_min       0.01
lot_buoc      0.01
lot_max     200.0        ← sàn không nhận lớn hơn
stops_level 410 điểm     ← SL gần hơn 0,41 $ thì sàn TỪ CHỐI CẢ LỆNH
```

⭐ **Hai con số đó giải trọn cái lỗ 862 lot ở §15.13a — mà không phải bịa một luật nào.**
Hôm trước tôi định thêm quy tắc mới *"R phải lớn hơn chi phí vào-ra"*. **Không cần:** sàn
đã có luật của nó, đã đo được, và nó chặt hơn. Lệnh SL 0,0004 $ / 862 lot vi phạm **cả
hai** ngưỡng.

**Cài:** `CaiDat` nhận thêm 4 trường; `lam_tron_lot()` làm tròn **XUỐNG** theo bước rồi kẹp
`[min, max]`; dưới `lot_min` trả `None` = **không vào lệnh** (không kẹp lên — tài khoản quá
nhỏ cho mức rủi ro đó thì câu trả lời đúng là *không đánh*, chứ không phải *đánh với rủi ro
gấp mấy lần mức đã khai*). `stops_level` chặn ở **ba chỗ**, cùng một hằng số, đọc qua đúng
một hàm `cd_stops()`:

| chỗ | sàn từ chối khi |
|---|---|
| `_vao_lenh` · SL | `R < stops_level` |
| `_vao_lenh` · lệnh chờ | `|giá đặt − giá thị trường| < stops_level` |
| `_sua_lenh` · dời SL/TP | `|mức mới − giá thị trường| < stops_level` |

⚠ **TÔI TỰ SỬA LẠI MÌNH.** §15.13 chốt *"KHÔNG làm tròn lot — làm tròn là bịa thêm sai số
vào đúng cái vừa dựng lên để chính xác"*. **Sai.** Bước lot 0,01 là **luật thật của sàn**,
đo được trong hồ sơ, không phải sai số tôi thêm vào. Chỗ tôi lẫn: *mô hình hoá thêm* khác
*tôn trọng một ràng buộc có thật*.

**Nguồn số: HỒ SƠ ĐO ĐƯỢC thắng → ô gõ tay (Cài đặt) → mặc định.** Đúng nếp §14.9 (*hồ sơ
là cache của phép đo, không phải cài đặt*). `ket_noi.luat_san(symbol)` tra **theo symbol**
(lúc backtest không nối sàn nào nên không biết hỏi sàn nào), nhiều sàn thì lấy hồ sơ **đo
gần đây nhất**, và trả kèm `nguon` + `do_luc`.

⚠ **Đọc `stops_level_that`, KHÔNG đọc `stops_level`.** Sàn *khai* `stops_level = 0` (nghĩa
là "không giới hạn") trong khi thực tế từ chối SL gần hơn 410 điểm — chính vì thế vòng hiệu
chuẩn mới đi ĐO lấy (§14.8c). Đọc con số sàn khai là tin vào thứ đã biết là sai.

**Giao diện nói rõ số đến từ đâu**, và **khoá mờ** bốn ô khi có hồ sơ — không cho sửa một
thứ mà bộ chạy sẽ bỏ qua.

#### Đo được

**Sơ đồ mẫu** — đổi nhẹ, vài lệnh SL hẹp hơn 0,41 $ bị từ chối:

| năm | lệnh | tổng R | DD % |
|---|---|---|---|
| 2022 | 485 → **455** | −4,96 → **+5,46** | 14,8 → **10,9** |
| 2023 | 421 → **379** | −29,96 → **−37,69** | 21,6 → **23,3** |
| 2024 | 447 → **435** | −37,37 → **−24,38** | 19,6 → **14,3** |
| 2025 | 453 → **447** | +12,01 → **+6,66** | 9,7 → **9,3** |

**`Compress updated`** — cái lỗ biến mất hẳn:

| năm | lot lớn nhất | phí | sụt vốn | vốn cuối |
|---|---|---|---|---|
| 2023 | 105,35 → **1,01** | 3.349 → **660** | 54,0 % → **25,4 %** | 4.748 → **8.184** |
| 2024 | 200,00 → **1,22** | 3.754 → **718** | 56,3 % → **26,2 %** | 4.448 → **7.563** |

*(Cột "trước" đã có sẵn trần `lot_max` mặc định 200 — nên chênh lệch ở trên là công của
riêng `stops_level`.)*

**BỘ SỐ NEO MỚI** *(XAUUSD · spread 90 · commission 3,5/lot · vốn 10.000 · rủi ro 0,5 %
· luật sàn Exness)*: **2025 = 447 lệnh · +6,66 R · DD 9,33 % · vốn 10.092**.

### 16.2 ✅ Hạng mục 2 — CHI PHÍ: spread · hoa hồng · trượt giá

#### ⚠ Con số nguy hiểm nhất trong app là mặc định `spread = 20`

Sơ đồ mẫu, 2025, **chỉ đổi mỗi spread** (luật sàn đã bật):

| spread | tổng R | vốn cuối |
|---|---|---|
| **20 điểm** *(mặc định cũ)* | **+12,78** | 10.409 |
| 90 điểm | +6,66 | 10.092 |
| 97 điểm *(kho nến đo được)* | +6,65 | 10.091 |
| 150 điểm | −1,65 | 9.678 |
| 250 điểm | **−11,84** | 9.250 |

**Cùng chiến lược, cùng năm: từ +12,78 R thành −11,84 R.** Một con số bịa làm chiến lược
thua trông như đang thắng — và nó nằm ở chỗ không ai nghĩ phải kiểm.
*(90 hay 97 thì chênh 0,01 R — chuyện không phải chọn số nào, mà là **đừng dùng 20**.)*

**Sửa:** mặc định thành `0` = **tự lấy `spread_tb` đo từ chính kho nến**. Không đo được và
cũng không gõ tay thì `_spread()` **ném lỗi kèm chính con số trên**, chứ không đoán — thà
không chạy còn hơn chạy ra một kết quả không ai truy được nguồn.

⚠ **Thứ tự NGƯỢC với luật sàn (§16.1), và có lý do.** Luật sàn là thứ sàn **áp đặt** nên số
đo luôn đúng hơn gõ tay → hồ sơ thắng. Spread là **điều kiện chạy thử** — người dùng có
quyền hỏi *"nếu spread xấu gấp đôi thì sao"*, và đó là câu hỏi đúng đắn → gõ tay thắng.

#### Hoa hồng KHÔNG đụng tới R — nhớ kỹ ở bước phần thưởng

| $/lot | tổng R | vốn cuối |
|---|---|---|
| 0 | +6,66 | 10.300 |
| 3,5 | +6,66 | 10.092 |
| 7,0 | +6,66 | 9.895 |

**Tổng R không đổi một chút nào.** Spread nằm *trong giá khớp* nên nó ăn vào R; hoa hồng là
tiền trừ ngoài, R không thấy. ⭐ **Chấm điểm bằng R thì hoa hồng VÔ HÌNH** — mà §15.13a đã
đo được ca hoa hồng chiếm **79 %** tổng thua lỗ. Phần thưởng phải nhìn cả tiền, không chỉ R.

#### Trượt giá — LUÔN theo chiều bất lợi

Ngoài đời lệnh Stop khớp **bằng hoặc xấu hơn** giá kích hoạt, không bao giờ tốt hơn: lúc
giá phá qua mức chính là lúc sổ lệnh mỏng nhất. Mô hình đối xứng (*"khi tốt khi xấu, trung
bình 0"*) nghe công bằng nhưng sai bản chất, và **sai đúng về phía làm backtest đẹp lên**.

Bốn ca, một luật: `vào Mua +` · `vào Bán −` · `ra Mua −` · `ra Bán +`.

⚠ **Trượt chỉ đụng GIÁ KHỚP, không đụng NGƯỠNG kích hoạt.** Sàn nhìn giá thật để quyết lệnh
có nổ hay không; trượt là chuyện xảy ra SAU đó, lúc đi tìm thanh khoản. Bài kiểm canh đúng
chỗ này (số lệnh không đổi, chỉ giá đổi).

**Mặc định 0 = không mô hình hoá**, cố ý không bịa: hồ sơ hiệu chuẩn đo `p95 = 0` nhưng chỉ
với **n = 3** — quá ít để tin. Bằng 0 thì backtest đang **lạc quan** ở khoản này, và nói
thẳng ra thế.

**Đo được — và đây là con số đáng lo:**

| trượt | tổng R | vốn cuối |
|---|---|---|
| 0 | +6,65 | 10.091 |
| 10 điểm (0,01 $) | +3,85 | 9.935 |
| **30 điểm (0,03 $)** | **+0,25** | 9.778 |
| 60 điểm | −4,21 | 9.583 |
| 100 điểm | −15,36 | 9.076 |

⭐ **Lợi thế của sơ đồ mẫu MỎNG HƠN mức trượt giá hợp lý.** Chỉ 3 xu trượt trên vàng là nó
về hoà. Đó không phải lỗi của mô hình — đó là sự thật về chiến lược, và là đúng loại sự thật
mà một backtest không mô hình hoá chi phí sẽ giấu đi.

#### Còn treo — spread TỪNG NẾN

MT5 **có** trả spread mỗi nến; `nguon_nen._sang_dtype` cố ý vứt đi, giữ mỗi trung vị, với lý
do ghi rõ *"mô hình đã chốt là spread một con số"*. Lý do đó đúng hồi đó.

Nhưng spread thật của vàng giãn mạnh đúng lúc **tin ra** — mà đó chính là lúc zone bị phá và
chiến lược này vào lệnh. Một con số cố định vì thế **tính thiếu chi phí đúng vào những lệnh
thật sự xảy ra**. Tốn: ~7 MB thêm (trên 85 MB) và **phải tải lại toàn bộ 5,5 năm**.

**Hoãn có chủ ý.** Nhưng ghi lại một điều: *không làm thì không có cách nào biết nó lệch bao
nhiêu* — nên đây là món nợ đã biết, không phải một chỗ đã yên.

### 16.3 ✅ Hạng mục 3 — SYMBOL: `point` · `contract_size` · `digits` thiếu thì NỔ

> Phát hiện lúc bàn §18 (bộ sinh), khi hỏi *"hệ thống có dính chặt vào XAUUSD không"*.
> Câu trả lời hoá ra là **có**, ở đúng bốn dòng — và cả bốn đều hỏng **im lặng**.

`api.py` từng dựng `CaiDat` thế này, ở **cả hai** đường (Tester và Live):

```python
point=m.get("point") or 0.01           # kho nến XAUUSD ghi 0.001
contract_size=m.get("contract_size") or 100.0
digits=m.get("digits") or 2            # kho nến XAUUSD ghi 3
```

⚠ **Mấy con số dự phòng ấy SAI cho chính XAUUSD.** Chúng chưa nổ chỉ vì kho nến hiện tại có
đủ meta. Thêm một symbol thiếu meta là chạy bằng số bịa, không một dòng báo.

Đo, sơ đồ mẫu 2025, chỉ thay `point` 0,001 → 0,01:

| | lãi %vốn | số lệnh |
|---|---|---|
| meta thật | **+1,25%** | 284 |
| số dự phòng | **−8,48%** | 52 |

Thủ phạm là **`point`** (hai cái kia gần như vô hại: `digits` sai cho kết quả y hệt,
`contract_size` sai 10× cho +2,69%). `point` nhân vào **spread**, **`stops_level`** và
**trượt giá** — sai 10 lần thì spread `0,097 $` thành `0,970 $`, và 232 trong 284 lệnh biến
mất.

**Đã sửa — bốn chỗ, cùng một nếp với `_spread` (§16.2): thiếu thì NÓI TO.**

| chỗ | trước | nay |
|---|---|---|
| `api._thong_so` | *(chưa có)* | ba số một bộ, thiếu **bất kỳ** cái nào là `RuntimeError` kèm số đo |
| `api` Tester + Live | `or <số bịa>` | `**_thong_so(sym, m)` |
| `bo_chay.PhienChay` | `cd or CaiDat()` | `cd` **bắt buộc** |
| `phien_live.PhienLive` | `cd or CaiDat(symbol=…)` | `cd` **bắt buộc** |

Hai dòng `cd or CaiDat()` không caller nào dùng, nhưng chúng là cái cửa để một phiên **LIVE**
chạy bằng point giả. Bỏ hẳn.

#### Mặc định của `CaiDat` nay là SỐ GIẢ, cố ý

```
spread_diem  20.0 → 0.0      point  0.01 → 1.0      contract_size  100.0 → 1.0
```

Nghĩa: *một đơn vị giá = một điểm, không mất phí gì*. Bộ test dùng chúng để số học đọc ra
bằng mắt. Điểm chính: **chúng không được giống bất kỳ symbol thật nào**.

⭐ **Một con số sai mà trông hợp lý là loại tệ nhất.** Mặc định cũ trông y như XAUUSD nên
không ai soi; mặc định giả thì nhìn phát biết ngay. Đường thật đi qua `_thong_so` và
`_spread`, cả hai **nổ** chứ không rơi về mặc định.

#### ⚠ Chính cái lưới suýt bị thủng bởi lỗi nó sinh ra để bắt

`tools/van_tay.py` **quên truyền `contract_size`** — và bài vẫn xanh suốt, vì nó lặng lẽ ăn
mặc định `100.0`, tình cờ đúng. Đổi mặc định thành số giả là vân tay lệch toác: *vốn cuối
10.124 → 1.920, sụt vốn 9,2% → 81%*.

Bài học không phải "van_tay viết ẩu", mà là: **một mặc định trông đúng khiến chỗ quên không
bao giờ lộ ra.** Nay `van_tay` viết cứng cả bốn số (cố ý không đọc meta — vân tay phải đổi
khi *mã nguồn* đổi, không phải khi ai đó tải lại nến).

Kèm theo, một lỗi thứ hai lộ ra ở đúng lúc tệ nhất: `van_tay` cất khoá năm bằng **số**, đọc
lại từ JSON thành **chữ**, nên phần in ra chỗ đổi tra trượt và in `cũ null` thay vì hai con
số cần so. Một công cụ giải thích sai đúng lúc cần nó giải thích. Đã ép về khoá chữ.

#### Thêm một symbol mới thì cần gì

Không cần đụng mã. Cần **dữ liệu đủ**, và app sẽ tự nói khi thiếu:

| | thiếu thì | ai bắt |
|---|---|---|
| `point` · `contract_size` · `digits` | nổ, kèm số đo | `api._thong_so` |
| `spread` | nổ, kèm số đo | `api._spread` (§16.2) |
| `lot_min` · `lot_buoc` · `lot_max` · `stops_level` | rơi về ô gõ tay rồi về mặc định | `api._luat_san` (§16.1) |
| mật độ nến M1 thật | *chưa ai bắt* — phải tự soi, §15.0 | — |

---

---

## 17. ⭐⭐ LUẬT KẾT HỢP — khối nào đi được với khối nào

> §16 nói **sàn** cho phép gì. Mục này nói **sơ đồ** có tự mâu thuẫn không.
>
> Một câu chung cho cả mục, và mọi luật dưới đây chỉ là nó nhìn từ các góc khác nhau:
>
> ⭐ **SƠ ĐỒ KHÔNG ĐƯỢC NÓI DỐI.** Vẽ ba việc thì lượt chạy phải làm ba việc. Vẽ một
> việc mà lượt chạy không làm gì — dù kết quả vẫn "chạy được" — là thứ duy nhất app này
> không cho qua.

⚠ **Mấy luật này KHÔNG phải để phục vụ bộ sinh.** Chúng đúng tự thân: người vẽ tay cũng
sai đúng những chỗ ấy, chỉ là mắt người thường bắt được nên ít khi lộ ra. Đừng biện minh
một luật bằng *"máy sinh sẽ không thấy"* — nếu luật chỉ đúng với máy thì nó không phải luật.

**Đã có sẵn từ trước** (§5, §5.1, §6.0, §12.6): mỗi nhánh phải mở đầu bằng cổng · nhánh
mặc định xếp cuối · ngã rẽ VÀ khi mọi đầu nhánh là hành động · Entry chỉ tạo Manage chỉ
sửa · toán hạng zone chỉ sau cổng zone · cổng rỗng (luôn khớp) · hai nhánh nằm ngang nhau
· self-loop · khối Bắt đầu không nhận đường vào.

**Lỗ hổng đo được — cả năm đều nằm ở phía SỬA LỆNH.** Phía Vào lệnh được soát rất kỹ
(`_KHOA_MOT_LENH`); phía Sửa lệnh gần như không soát gì, và `_sua_lenh` thì **im lặng
nuốt**: nó mở đầu bằng `if not l.con_song: return None`.

### 17.1 ✅ Sau `Kết thúc lệnh này` thì hết

```
Kết thúc lệnh này
     └─ Dời SL          ← lệnh đã đóng, khối này không bao giờ làm gì
```

Báo lỗi ở **mọi** khối nối sau, kể cả khi khối đó là một CỔNG: cổng vẫn đánh giá được
(nó đọc thị trường), nhưng nhánh nó dẫn tới thì chết, và mấy toán hạng *"Lệnh này"* khi
đó đang hỏi về một cái lệnh đã đóng — câu hỏi không còn nghĩa.

### 17.2 ✅ Ngã rẽ VÀ không được có hai hành động GHI ĐÈ nhau

Ngã rẽ VÀ **làm hết**. "Làm hết" chỉ có nghĩa khi mấy việc đó không giẫm lên nhau:

```
[1] ─┬─ Dời SL về hoà vốn      ┐
     ├─ Trail SL theo ATR      ├─ cả ba cùng ghi SL
     └─ Siết SL sát lại        ┘   ⇒ chỉ cái CUỐI còn dấu vết
```

`core.SUA_GHI_LEN` là nguồn duy nhất của luật này — song song với `_KHOA_MOT_LENH` bên
Vào lệnh:

| ghi lên | chế độ |
|---|---|
| `sl` | `doi_sl` · `hoa_von` |
| `tp` | `doi_tp` |
| `*` (cả cái lệnh) | `ket_thuc` — nên nó đá với **mọi** chế độ, kể cả chính nó |

*(Muốn "chọn một trong ba" thì mỗi nhánh phải mở đầu bằng một cổng — khi đó nó thành ngã
rẽ HOẶC và chỉ một nhánh chạy. Đó mới là hình vẽ đúng với ý định.)*

### 17.3 ✅ Nối tiếp cũng vậy — trừ khi có CỔNG ở giữa

Cùng luật §17.2, chỉ khác hình vẽ: một lượt đi qua cả hai khối, khối dưới ghi đè khối
trên ngay lập tức.

⚠ **CỔNG Ở GIỮA thì KHÔNG phải lỗi**, và đây là chỗ phải phân biệt cho sạch:

```
Dời SL về hoà vốn
     └─ Lãi ≥ 2R ?              ← cổng TRƯỢT ĐƯỢC
          └─ Trail SL theo ATR  ← nên khối trên có tác dụng thật
```

Vì thế phép loang **dừng ở mọi cổng** thay vì đi xuyên qua. Nguồn là `ket_thuc` thì bỏ
qua — §17.1 đã chặn bằng một câu chính xác hơn, hai câu cho một lỗi là ồn.

*(Ca `Dời SL → Kết thúc` cũng bị bắt, và đúng: dời SL xong đóng lệnh ngay thì dời làm gì.)*

### 17.4 ✅ Hai lệnh GIỐNG HỆT — soi cả hai chiều

Luật `_KHOA_MOT_LENH` có từ §5.1 chỉ loang **dọc theo đường**, nên nó mù với ca hai khối
là hai **nhánh** của cùng một ngã rẽ:

```
✅ bắt được               ✘ trước đây KHÔNG bắt
[1] → Mua                 [1] ─┬─ Mua
       └→ Mua                  └─ Mua
```

Ngã rẽ VÀ chạy cả hai, đẻ ra đúng hai lệnh trùng khít — cùng một cái sai, chỉ khác hình
vẽ. Nay soi cả hai chiều, dùng chung đúng một khoá so sánh.

### 17.5 ✅ `Hoà vốn` chạy cả trên lệnh CHƯA KHỚP — cảnh báo

Manage chạy một lượt cho MỖI lệnh đang sống, **kể cả lệnh chờ**. Mà `hoà vốn` = *"SL =
giá vào"*, lệnh chờ thì chưa có giá vào → `_sua_lenh` trả `None`, im lặng.

⚠ **Cảnh báo chứ không phải lỗi, có chủ ý.** Cách lọc lệnh chờ có nhiều đường —
`Lệnh này đã khớp`, hoặc `lãi (×R) ≥ 1` (lệnh chờ luôn 0R nên cũng lọc được), hoặc cách
khác. Đòi đúng một toán hạng là chặn nhầm những cách viết hợp lệ. Chỉ nhắc khi phía trên
**không có cổng nào** — lúc đó chắc chắn không có gì lọc.

*(Mấy chế độ kia không dính: `Dời SL`/`Dời TP` sửa được cả lệnh chờ — sàn thật cũng cho.
`Kết thúc` thì lệnh chờ là huỷ, lệnh đã khớp là đóng, cả hai đều có nghĩa.)*

### 17.6 ⚠ `Hoà vốn` PHẢI TRỪ CẢ CHI PHÍ — nếu không nó lỗ có hệ thống

`SL = giá vào` **nghe như** hoà vốn nhưng không phải: chạm nó thì phần giá đúng bằng 0, mà
**hoa hồng vẫn bị trừ**. Lệnh "hoà vốn" ấy thật ra lỗ đúng một khoản phí — và nó lỗ như thế
ở **mọi** lệnh được dời, âm thầm, có hệ thống.

```
tiền = (giá đóng − giá vào) × lot × contract − hoa_hồng × lot  =  0
⇒  giá đóng = giá vào + hoa_hồng / contract          ← lot TỰ TRIỆT TIÊU
```

Cộng thêm **trượt giá**: chạm SL thì khớp xấu hơn đúng `truot`, nên mốc phải đẩy ra thêm
chừng ấy nữa.

⚠ **KHÔNG cộng spread — cộng là tính hai lần.** Nó đã nằm trong `gia_khop` (lệnh Mua vào ở
Ask) và trong ngưỡng ra (`_muc_ra` dịch sẵn cho lệnh Bán). Đây đúng là chỗ dễ cộng thừa.

Với XAUUSD, hoa hồng 3,5/lot và contract 100 → mốc đẩy ra **0,035 $ = 35 điểm**.

**Đo được** *(sơ đồ mẫu, spread 97, hoa hồng 3,5, luật sàn Exness)*:

| năm | lệnh | tổng R | DD % | vốn cuối |
|---|---|---|---|---|
| 2022 | 455 | +4,10 | 10,77 | 9.744 |
| 2023 | 379 | −40,12 | 23,70 | 7.864 |
| 2024 | 435 | −26,30 | 15,20 | 8.480 |
| **2025** | **447** | **+7,28** | **9,21** | **10.125** |

Số lệnh không đổi (mốc hoà vốn không quyết định lệnh nào được đặt), nhưng **R nhích lên**
ở mọi năm — vì mấy lệnh về hoà vốn nay thoát ở đúng số 0 thay vì âm một khoản phí.

### 17.7 ⚠ LỖI THẬT (có từ trước): SL đặt SAI PHÍA là ĐÓNG LỆNH, không phải dời SL

Lộ ra ngay khi cài §17.6 — và nó **không phải do §17.6 gây ra**, chỉ là đẩy mốc ra thêm
làm nó hiện hình.

`hoa_von` đặt `SL = giá vào` mà **không hỏi giá đang ở đâu**. Lệnh đang LỖ thì giá vào nằm
**TRÊN** thị trường, nên với một lệnh Mua, "dời SL về hoà vốn" hoá thành **"cắt lỗ ngay bây
giờ"** — và cắt ở một mức tệ hơn cả giá thị trường đang có.

Đo được lúc chưa sửa: lệnh vào 104, hoà vốn đặt SL 109 (trên thị trường), **đóng ngay ở
chính cây nến vào**, lỗ −15 $.

Sơ đồ mẫu che được chuyện này nhờ cổng `lãi ≥ 1R` đứng trước — nhưng đó là **may nhờ người
vẽ**, không phải nhờ hệ thống. Sơ đồ không vẽ cái cổng ấy thì không có gì chặn.

**Sửa:** mọi lần ghi SL đi qua một cửa duy nhất `_sl_moi`, ba phép theo đúng thứ tự sàn thật
kiểm:

| | |
|---|---|
| **1. đúng phía** | SL lệnh Mua phải DƯỚI thị trường, lệnh Bán phải TRÊN |
| **2. đủ xa** | cách thị trường ít nhất `stops_level` (§16.1) |
| **3. chỉ siết** | `_siet_sl` (§15.10) |

⭐ **Sơ đồ mẫu không đổi một con số nào** sau lượt sửa này — đúng như phải vậy: nó vốn đã
đúng nhờ cái cổng. Phép kiểm không tốn gì ở chỗ sơ đồ vẽ đúng, và chặn được đúng chỗ sơ đồ
vẽ sai.

---

### 15.15 Còn treo sau đợt này

- [ ] **Mốc neo `ma`** — cần ô mốc thành bộ chọn toán hạng đầy đủ (`OToanHang` đã có, chỉ
      thiếu phép lọc theo `loai`). §15.8.
- [ ] **Nhiều zone cùng lúc** — hoãn có chủ ý, §15.11.
- [ ] **Tên tham số gợi ý xấu**: `nguong_atr_atr_nen` (bộ sinh tên ghép `nguong_{toán
      hạng}_{đơn vị}`). Cosmetic, nhưng người dùng nhìn thấy.
- [x] ~~**Sang bước LUẬT CHƠI**~~ — **XONG**, cả bốn: **(1)** chi phí vào-ra §16.2;
      **(2)** spread một nguồn duy nhất, thiếu thì nổ §16.2; **(3)** mô hình trượt giá
      §16.2; **(4)** khoảng train/khoá §18.3, lấy theo M1 **thật** đúng như §15.0 cảnh báo.

#### Hai file chiến lược của người dùng — đã di cư

Bản gốc sao lưu ở `du_lieu/sao_luu_truoc_dot_15/`. Chỉ làm **hai việc cơ học**, mỗi việc
có đúng một câu trả lời: `bps` → `× ATR nền` (0,75) và `lot` → `rủi ro % vốn` (0,5).
**Không đụng cấu trúc đồ thị** — sửa hộ cấu trúc là sửa chiến lược của người khác.

| | |
|---|---|
| *Compress updated* | 7 thay đổi · soát tĩnh **SẠCH** |
| *Cây quyết định đầy đủ* | 13 thay đổi · còn **1 lỗi** và **1 chỗ đáng ngờ** — cả hai là chuyện THIẾT KẾ, để người vẽ quyết |

⚠ **Hai chỗ đó, cả hai đều có TỪ TRƯỚC đợt này:**

1. **`che_do: "giu_nguyen"` không tồn tại** (khối *"Để yên"*, `[1CA]`). Trong hệ thống này
   *"không làm gì"* không phải một khối — nó là **không có khối**, nhánh cụt ở đó và hết
   lượt (§6.1).
2. **Ngã rẽ 5 nhánh sau `[1C] Lệnh đã khớp` là ngã rẽ VÀ, không phải HOẶC.** Cả năm đầu
   nhánh đều là *hành động*, nên theo §5.0 bộ chạy **LÀM HẾT** — kể cả *"Chốt hết"*
   (`ket_thuc`), tức mọi lệnh đã khớp bị đóng ngay lượt Manage đầu tiên. Tên các khối đọc
   ra như một lựa chọn năm đường; hình vẽ thì nói *làm cả năm*. Muốn "chọn một" thì mỗi
   nhánh phải mở đầu bằng một **cổng**.

---

## 18. ⭐⭐ BỘ SINH — máy được đổi những gì

> §15 dựng **kho đồ**, §16 dựng **luật sàn**, §17 dựng **luật kết hợp**. Ba mục đó là cái
> hộp. Mục này bắt đầu nói về thứ chạy trong hộp.
>
> **18.1** máy đổi gì · **18.2** chấm điểm · **18.3** dữ liệu ⏸ · **18.4** thông lượng ·
> **18.5** cách tìm · **18.6** cửa sổ RL · **18.7** ✅ người bày *(đã cài)*
>
> **Còn thiếu để cửa sổ RL có thứ để hiển thị — ba món, xem §18.8.**
>
> ⭐ **CORE là BỐN thứ, và chỉ bốn:** kho đồ (§15) · luật chơi (§16, §17) · cách chấm
> (§18.2) · dữ liệu (§18.3). Dò ngẫu nhiên, tiến hoá và RL là ba cách bới **cùng một không
> gian**, chấm bằng **cùng một thước**, trên **cùng một dữ liệu** — nên thuật toán tìm
> **không thuộc core**, và không chốt ở giai đoạn này (§18.5). Thông lượng (§18.4) là số đo
> của máy, không phải quyết định thiết kế.

⭐ **Ta không dạy máy đoán giá.** Ta cho máy vẽ sơ đồ trong đúng kho đồ và luật chơi vừa
dựng, rồi chấm điểm cái nó vẽ ra. Đầu ra là **một sơ đồ đọc được**, không phải một mô hình
hộp đen — nếu nhìn vào kết quả mà không hiểu nó làm gì thì bộ sinh đã hỏng, dù điểm cao.

### 18.1 ✅ Ba thứ máy đổi được — và số thì lấy từ THANG, không dò tự do

```
1. khối nào      cổng · vào lệnh · sửa lệnh
2. nối thế nào   ai đi trước ai, nhánh nào rẽ đâu
3. số nào        SL · TP · ngưỡng · rủi ro · số nến
```

Hai cái đầu là **logic** — đó mới là thứ đáng đi tìm. Cái thứ ba là số, và số phải chọn từ
một **thang thưa có sẵn**:

| ô | thang | đơn vị |
|---|---|---|
| SL | 0,5 · 1 · 1,5 · 2 · 3 | `× ATR zone` / `× ATR` |
| TP | 1 · 1,5 · 2 · 3 · 5 | `× R` |
| ngưỡng | 0,25 · 0,5 · 0,75 · 1 · 1,5 · 2 | theo `don_vi` của toán hạng |
| rủi ro | 0,25 · 0,5 · 1 | `%` vốn |
| đếm nến | 1 · 2 · 3 · 5 · 8 · 13 | `nến` |

#### Vì sao thưa — đo được, không phải cảm tính

Dò SL trên **một năm** (2025) bằng thang mịn bước 0,1 từ 1,0 đến 3,0 — đúng cái việc
"optimize tham số" — rồi đem con số thắng cuộc sang những năm **chưa hề dùng để dò**:

| | SL 1,5 *(mặc định)* | SL 3,0 *(thang thô)* | SL 2,7 *(thang mịn)* |
|---|---|---|---|
| **2025** — năm đi dò | | +46,82 | **+58,23** ← thắng |
| 2022 | +4,10 | +13,69 | +9,50 |
| 2023 | −40,12 | −3,42 | −2,31 |
| 2024 | −26,30 | −18,92 | −20,49 |
| **tổng 3 năm chưa thấy** | −62,32 | **−8,65** | −13,30 |

Đọc bảng này ra **hai thứ khác hẳn nhau** nằm trong cùng một cuộc dò:

```
1,5 → 3,0    hướng đi       THẬT   −62 → −9, thấy ở mọi năm
3,0 → 2,7    độ chính xác   NHIỄU  hai nấc cạnh nhau lệch trung bình 5,11 R
```

Nấc `2,6 · 2,7 · 2,8` cho `+49 · +58 · +48`. Cái bướu ở `2,7` chỉ là vài lệnh may không bị
quét râu nến. **Thang thô bắt trọn phần thật và bỏ phần nhiễu** — mà lại còn ra kết quả
tốt hơn ngoài mẫu.

⚠ **Chuẩn hoá KHÔNG cứu được chuyện này, và đây là chỗ rất dễ lẫn.** §15 làm cho con số
*mang cùng một nghĩa* ở mọi thị trường, mọi năm — nó giải bài toán **mang đi được**. Nó
không đụng gì tới bài toán **khớp với chính bộ dữ liệu đã dùng để chọn**: `2,7 × ATR zone`
mang đi tốt y như `3,0`, và vẫn là con số của riêng năm 2025.

#### Nhưng overfit không biến mất — nó DỜI sang logic

```
không gian SỐ      SL 5 × TP 5 × ngưỡng 6 × rủi ro 3      ≈ 450
không gian LOGIC   22 toán hạng · 4 khối · 12 điều kiện   ≈ hàng tỉ
```

Dò 450 con số trên 5 năm thì khó ăn may. Dò hàng tỉ sơ đồ thì **chắc chắn** có cái trúng
khớp lịch sử mà chẳng có lý gì. Nên logic vừa là thứ đáng đi tìm nhất, vừa là thứ phải canh
chặt nhất — và nó được canh bởi hai thứ, không phải thang số:

| canh bằng | ở đâu |
|---|---|
| **luật kết hợp** — cắt sẵn phần lớn sơ đồ vô nghĩa | §17, đã xong |
| **chấm điểm + dữ liệu chưa thấy** | §18.2 · §18.3 |

Thang thô chỉ làm hai hàng rào đó phải gánh ít hơn. Nó không phải hàng rào chính.

⚠ **Thang chưa nằm trong mã.** Chưa có bộ sinh nên chưa có chỗ đặt. Cùng cảnh với trần độ
phức tạp (§15.5) — cả hai vào cùng lúc với bộ sinh, và khi vào thì phải **sinh từ một bảng
duy nhất** trong `core.py`, không chép tay ở hai nơi.

### 18.2 ✅ Chấm điểm — bằng TIỀN, theo TUẦN

```
mỗi tuần kiếm/mất bao nhiêu % vốn
    → trung bình   ·   dao động (SD)   ·   trung bình ÷ dao động
```

Ba con số đó là điểm. Xem thêm theo **tháng** cho dễ đọc, nhưng chấm theo **tuần**.

⭐ **Vì sao theo TUẦN chứ không phải tổng cả kỳ:** một chiến lược ăn đậm một đợt rồi trả
lại đợt khác, cộng lại vẫn dương — nhưng nó không sống được. Cái sống được là cái kiếm
**đều**. Tổng cả kỳ là một con số, nó không phân biệt được hai chuyện đó. Chuỗi theo tuần
thì có: cùng một mức lãi, cái nào dao động thấp hơn là cái tốt hơn.

**"Risk" = dao động (SD), không phải lỗ trung bình.** SD phạt **cả hai phía**: một chiến
lược có tuần +5% nằm cạnh tuần −3% là chiến lược sớm muộn trả lại chỗ đã ăn. `Lỗ trung bình
tuần` vẫn hiện ra cho người đọc, nhưng không dùng để chấm.

#### 18.2a ⚠ CỬA BẮT BUỘC — tuần có lệnh ≥ một nửa

```
số tuần CÓ lệnh đóng  <  ½ số tuần   →   LOẠI THẲNG, không chấm
```

⚠ **Câu này từng nằm ở đây và nó SAI, ghi lại để đừng ai tin lại:** *"đánh quá ít lệnh thì
nhiều tuần trắng tự kéo trung bình xuống, không cần cửa phụ nào"*.

Đo mới bắt được. Đi từng nấc thang cho tham số `nguong_nen` trên TRAIN 3,5 năm:

| ngưỡng | điểm | số lệnh |
|---|---|---|
| **0,25** | **−0,0739** ← cao nhất cả bảng | **1** |
| 0,75 *(sơ đồ mẫu)* | −0,1764 | 929 |

**Một sơ đồ vào đúng MỘT lệnh trong 3,5 năm ăn điểm cao hơn sơ đồ vào 929 lệnh.** Và đó
không phải trùng hợp — nó là số học thuần:

```
1 tuần có lệnh trong N tuần  →  điểm = ±1/√(N−1) = ±1/√182 = ±0,0741
                                            (đo được: −0,0739)
```

⭐ **Kết quả KHÔNG phụ thuộc lệnh đó lãi hay lỗ bao nhiêu.** Tuần trắng làm co **cả** trung
bình **lẫn** dao động theo đúng một tỉ lệ, nên thương số sống sót nguyên vẹn. Nằm im được
điểm đẹp, và đó là điểm **rẻ nhất** để đạt tới — bất kỳ máy tìm nào cũng sẽ vồ ngay.

Vá bằng một **cái cửa**, không phải sửa công thức: sửa công thức là bịa thêm một phép toán
để chữa một triệu chứng; cái cửa nói thẳng ra điều kiện — *chiến lược phải thật sự chơi*.

| | tuần trắng | qua cửa? |
|---|---|---|
| sơ đồ mẫu | 1/236 | ✔ |
| sơ đồ một lệnh | 235/236 | ✘ |

Đây cũng đúng thứ người dùng nói ngay từ đầu khi mô tả cách chấm mình muốn: *"kiếm tiền
đều và ổn định mới sống"*.

#### 18.2b ⚠ `tổng R` KHÔNG dùng để chấm — nó mù chi phí hoa hồng

`bo_chay.py::_thong_ke` tính hai thứ từ hai nguồn khác nhau, và đó là chủ ý:

```python
tien = (gia_dong - gia_khop) * chieu * lot * contract_size
tien -= commission * lot           # TIỀN có trừ phí
r    = (gia_dong - gia_khop) * chieu / R     # R chỉ có GIÁ
```

R đo *giá đi được bao nhiêu lần khoảng SL*. Phí hoa hồng là **tiền**, không phải khoảng
giá — nên nó không bao giờ vào R. Spread và trượt giá thì CÓ (chúng dời giá khớp); phí thì
không. Đây không phải lỗi, là định nghĩa. Nhưng nó khiến R **không dùng để chấm được**.

Đo: một chiến lược, một năm (2025), chỉ đổi phí:

| phí $/lot | tổng R | lãi thật | % vốn | sụt vốn |
|---|---|---|---|---|
| 0 | +6,65 | +299 $ | +3,00% | 8,96% |
| 3,5 | **+7,28** | +124 $ | +1,25% | 9,21% |
| 7 | +5,92 | −121 $ | −1,21% | 10,40% |
| 20 | +2,51 | −806 $ | −8,06% | 12,85% |
| 50 | **+2,99** | **−2063 $** | **−20,64%** | 23,17% |

- phí 0 → 3,5: tiền **giảm** 175 $, `tổng R` lại **tăng**.
- phí 50: tài khoản mất **một phần năm**, `tổng R` vẫn báo **+2,99 — có lãi**.

Phí ăn **0,0122 R mỗi lệnh** trong khi cả chiến lược chỉ kiếm **0,026 R mỗi lệnh** — gần
một nửa kỳ vọng, và `tổng R` không thấy gì.

Lần thứ hai, trên 4,5 năm: `SL 3,0` được `tổng R` khen **+25,38 R**, tiền thật **+0,27%** —
gần như huề vốn.

*(Cột R có nhúc nhích chút ít vì hoà vốn nay có cộng chi phí — §17.7 — chứ không phải R
biết tính phí. Nhúc nhích không theo chiều nào: nhiễu, càng không chấm được.)*

⭐ **R giữ nguyên vai trò cũ và vẫn rất cần** — nó là đơn vị để **ra lệnh** (`TP 2 × R`) và
để so một lệnh với một lệnh. Nó chỉ không phải đơn vị để chấm một **chiến lược**.

#### 18.2c Số đo trên 4,5 năm M1 thật — cách chấm này có phân biệt được không

`2021-07 → 2026-01` · 236 tuần · 54 tháng · sơ đồ mẫu, chỉ đổi SL:

| | SL 1,5 | SL 3,0 |
|---|---|---|
| cả kỳ | −38,06% vốn | +0,27% vốn |
| *(tổng R — để đối chiếu)* | *−62,03 R* | *+25,38 R* |
| **trung bình tuần** | −0,161% | +0,001% |
| **dao động tuần** | 1,115% | 1,311% |
| **return/risk tuần** | **−0,145** | **+0,001** |
| lỗ trung bình tuần | −0,862% | −0,975% |
| tuần trắng | 1/236 | 1/236 |
| sụt vốn sâu nhất | 46,10% | 24,98% |

#### 18.2d ✅ ĐIỂM CÓ HAI VẾ — và người dùng chỉnh được nâng vế nào

Điều đầu tiên người dùng nói khi bàn về chấm điểm là **bốn** con số, không phải một:
*"average return 1 tuần, average return 1 tháng, average risk 1 tuần, 1 tháng, và
return/risk"*. Một ô ghi `điểm = 0,0187` trả lời được đúng con số cuối, ba con số kia
biến mất — mà chúng mới là thứ đọc ra được *"kiếm bao nhiêu"* và *"kiếm có đều không"*.

Nên panel Thưởng·Phạt tách công thức làm hai vế, và mỗi vế nói thẳng nó là gì:

```
vế TRÊN   trung bình   lãi mỗi tuần, tính bằng % vốn ĐẦU   → kiếm được BAO NHIÊU
vế DƯỚI   dao động     chuỗi lãi tuần lệch nhau bao nhiêu  → kiếm có ĐỀU không
```

Và **cả hai kỳ** đều tính, đều trả về, đều hiện trên bảng đầu bảng — cặp cột đang dùng
để chấm thì tô đậm. `cham()` vốn đã tính sẵn cả tuần lẫn tháng; giấu một cái đi là phí.

| nấc `manh_deu` | điểm | nghĩa |
|---|---|---|
| `0` | `trung bình` | chỉ nhìn lãi, mặc kệ giật cục |
| `1` *(mặc định)* | `trung bình ÷ dao động` | cân bằng |

⚠ **Không phá luật §15.1 (*"cái thước không được là tham số"*).** Luật ấy cấm chỉnh cái
**ĐO** — chu kỳ ATR, mẫu số chuẩn hoá. Còn `trung bình` và `dao động` đều đã đo xong
bằng thước cố định; chọn coi trọng vế nào là **thích gì**, không phải **đo bằng gì** —
đúng ranh giới §18.6.4.

##### ⚠ KHÔNG có nấc 2 (`÷ dao động²`) — đã cài, đo, rồi bỏ

Nấc thứ ba *"ưu tiên đều"* nghe rất thuận tai và **sai về số học**. Đo trên chính sơ đồ
mẫu ở §18.2c:

```
trung bình −0,161%   dao động 1,115%
    k = 1   →  −0,1446
    k = 2   →  −0,1296      ← "ưu tiên đều" chấm CAO HƠN
```

Vì trung bình **ÂM** thì càng chia càng gần 0. Và không vá được bằng đổi dấu: với dao
động **< 1** nó lật ngược thêm lần nữa. **Một tỉ số không đơn điệu theo mẫu số khi tử số
âm** — mà phần lớn sơ đồ máy sinh ra đều có tử số âm, nên đây không phải trường hợp
hiếm, nó là trường hợp thường.

⭐ Muốn siết chặt hơn thì dùng **cửa** `dao_dong_toi_da`: nó đơn điệu, phát biểu được
(*"tôi không nhận dao động quá 1,5%"*), và không đụng vào thước. Đúng bài học §18.6.4 —
cửa, không phải cân.

### 18.3 ⏸ Dữ liệu — KHOÁ + CUỐN TỚI đã cài, phần HỌC còn cất lại

⭐ **Đã chốt và không bàn lại:**

| | |
|---|---|
| **KHOÁ** | phải có một đoạn **không bước nào chạm tới**, mở **đúng một lần**, lúc cuối |
| **độ dài tối thiểu** | ≥ **48 tuần** — dưới ngưỡng đó con số là tung đồng xu, đo ở dưới |
| **lấy theo M1 THẬT** | §15.0, không theo meta kho nến |

⏸ **Ba phương án chia phần còn lại**, bàn khi chưa có bộ sinh nên chưa kiểm chứng được
cái nào. Ghi ra để khỏi bàn lại từ đầu — **đọc kèm §18.3b**, chỗ chốt rằng cột *"mất gì"*
của hàng cuối chỉ đúng với phần HỌC, không đúng với phần NGHIỆM THU:

| | hình | được gì | mất gì |
|---|---|---|---|
| **hai phần** | train · khoá | train dài nhất (183 tuần) | chọn ứng viên ngay trên đoạn máy vừa đào |
| **ba phần** | train · valid · khoá | valid **không** tham gia chọn lọc — đúng nếp DL: dừng lúc nào, giữ bản nào | train còn 130 tuần |
| **cuốn tới** | train ban đầu → cuốn từng quý → khoá | **6 lần** chấm ngoài mẫu thay vì 1; đúng cách dùng thật | mỗi vòng tìm lại = ×6 thời gian |

⚠ **Ba chỗ đã sai trong lúc bàn, ghi lại để đừng lặp:**

1. *"Chia đôi train là đủ, khỏi cần valid"* — **sai**. Cả hai nửa đều tham gia chấm và lọc,
   nên cả hai đều là train. Valid theo nghĩa DL là đoạn **không hề tham gia** vào việc cái
   gì sống sót.
2. *"Walk forward không dùng được"* — **sai**. Cái sai chỉ là **bước một tuần** (52%, đo ở
   dưới). Đổi bước thành **quý** thì cấu trúc cuốn-tới đúng, và cho **nhiều** lần chấm ngoài
   mẫu thay vì một — quan trọng vì xếp hạng chỉ chuyển được **+0,54** sang đoạn khác.
3. *"236 tuần ÷ 48 = chỉ đủ 5 lần chấm"* — **sai**, xem cuối mục.

#### Vì sao phải khoá — một tuần lẻ là tung đồng xu

```
cả kỳ:      SL 3,0 hơn SL 1,5 tới 38 điểm %   — rõ như ban ngày
từng tuần:  SL 3,0 chỉ thắng ở 122/236 tuần   = 52%
```

Nhiễu đang gấp **7 lần** tín hiệu (`SD 1,115% ÷ |trung bình| 0,161%`), nên cần chừng
**48 tuần ≈ 1 năm** thì trung bình mới nổi lên trên nhiễu. Đó là lý do đoạn khoá dài
**một năm**, không phải một quý.

⚠ **Một năm khoá đủ để bắt chiến lược CÓ BIÊN THẬT, không đủ để phân biệt hai chiến lược
gần giống nhau.** Đừng đọc chênh lệch nhỏ ở đoạn khoá thành kết luận. Điểm test ngang ngửa
train là **tin tốt**; vênh xa là máy đã học vẹt.

#### Ý "walk forward theo tuần" nằm ở đâu

Ý gốc: *máy sống qua từng tuần, tự xem kiếm/lỗ bao nhiêu, tích luỹ.* Giữ nguyên — nó nằm
trong phần train. Chỉ có một chỗ phải nói rõ:

| | |
|---|---|
| người thật | đi qua lịch sử **một** lần, không quay lại |
| máy học | đi **đi lại** hàng nghìn lần trên cùng đoạn đó |

Đi qua một lượt chỉ cho máy 236 tuần kinh nghiệm — không đủ để học gì. Nên *"walk forward
theo tuần"* là **cách CHẤM**, không phải cách HỌC.

Và máy **không được phản ứng với một tuần lẻ**:

```
BƯỚC   vẫn từng tuần một, vẫn không nhìn lại   ← giữ nguyên ý gốc
CHẤM   trên cửa sổ ~1 năm gần nhất             ← không phải tuần vừa rồi
```

Đúng như người đánh thật không đổi hệ thống sau một tuần lỗ.

⚠ **Một phép tính SAI đã suýt lọt vào đây, ghi lại để đừng ai tính lại:** *"236 tuần ÷ 48
tuần = chỉ đủ 5 lần chấm"*. Sai. **Nhiều sơ đồ chấm chung một đoạn dữ liệu được** — dữ liệu
không bị tiêu theo từng sơ đồ. 48 tuần là độ dài một **cửa sổ**, không phải giá tiền mỗi
lần thử. Thứ bị tiêu là **tính "chưa thấy" của đoạn khoá**, và nó chỉ bị tiêu khi ta *nhìn*
vào đó — nên luật chỉ có một dòng: mở đúng một lần.

#### 18.3b ✅ CUỐN TỚI — đã cài, ở ĐOẠN KHOÁ chứ không ở vòng tìm

Bảng ba phương án ở trên ghi cái giá của "cuốn tới" là **×6 thời gian**. Cái giá ấy chỉ
đúng nếu hiểu cuốn tới là *tìm lại từ đầu mỗi quý*. Nhưng thứ đắt giá nhất của nó —
**nhiều lần chấm ngoài mẫu thay vì một** — lấy được gần như **miễn phí**:

```
chạy MỘT lượt backtest trên cả đoạn khoá
    → chuỗi lãi/lỗ theo tuần đã có sẵn CẢ DẢI
    → chỉ việc bỏ vào đúng rổ cửa sổ rồi chấm từng rổ
```

`cham_diem.cham_cuon(kq, t0, t1, buoc, cua)` — cắt chuỗi kỳ, không chạy lại backtest.
Sáu cửa sổ mà chạy sáu lượt là đắt gấp sáu; cắt chuỗi thì gần như bằng không.

⭐ **Vì sao đáng làm — một con số gộp cả dải giấu mất cấu trúc thời gian.** Đo trên
XAUUSD 2021-07 → 2026-01, 18 quý, chỉ đổi SL:

| | SL 1,5 | SL 3,0 |
|---|---|---|
| điểm **gộp** cả dải | −0,1446 | **+0,0009** |
| **quý dương** | 4/18 | **8/18** |

SL 3,0 có điểm gộp *dương* — nhìn qua thì đạt. Nhưng nó chỉ dương ở **8 trên 18 quý**;
mười quý còn lại là lỗ. Một con số gộp không phân biệt được *"kiếm đều"* với *"ăn đậm
một đợt rồi trả lại"*, mà đó đúng là câu hỏi §18.2 sinh ra để trả lời. Dải cửa sổ trả
lời được, con số gộp thì không.

⚠ **Bước nhỏ nhất là THÁNG, không có "tuần"** — `BUOC_CUON = {thang: 1, quy: 3,
nua_nam: 6}`. Lý do là số đo ngay trên đầu mục này: hai chiến lược chênh nhau 38 điểm %
qua 4,5 năm mà xét từng tuần chỉ hơn nhau ở **52%** số tuần. Một tuần lẻ không mang tin.

| | |
|---|---|
| Python | `cham_diem.cua_so_cuon` · `cham_diem.cham_cuon` · `api.rl_mo_khoa` |
| cài đặt | `cach_chia` (`mot_khoi` \| `cuon_toi`) · `buoc_cuon` — khối `"rl"` |
| JS | panel **Dữ liệu** → *cách chia thời gian*; tab **Đoạn khoá** → dải ô từng cửa sổ |

⚠ **`rl_mo_khoa` chấm bằng ĐÚNG bộ cửa lượt train đã dùng** — `LuotTim.cua`, cất lúc
`_chay`. Chọn trên train bằng một thước rồi nghiệm thu bằng thước khác thì cái chênh
lệch đọc ra là chênh của **THƯỚC**, không phải của sơ đồ. Lỗi này đã có thật một lượt:
`cua` chưa hề được gán, `NameError` rơi vào `except` và mọi dòng mở khoá thành một dòng
báo lỗi.

⏸ **Vẫn CẤT LẠI: cuốn tới ở vòng TÌM** (tìm lại từ đầu mỗi quý, mang kinh nghiệm sang
quý sau). Đó mới là cái ×6 thời gian, và nó cần thuật toán học của §18.5 — chưa chốt.
Cái đã cài là phần **nghiệm thu**, không phải phần **học**.

#### 18.3a ⭐ Hướng đi tiếp: NHIỀU SYMBOL, không phải nhiều lịch sử hơn

236 tuần là giới hạn của **kho nến đang có**, không phải một định luật. App không phụ thuộc
MT5 — MT5 chỉ là đường **đặt lệnh**; nguồn nến hoàn toàn thay được.

⭐ **Nhiều symbol không phải là "nhiều dữ liệu hơn" — nó là BẰNG CHỨNG LOẠI KHÁC.** Thêm
lịch sử XAU chỉ cho thêm tuần của cùng một thị trường. Thêm EUR, chỉ số, crypto thì hỏi
được một câu khác hẳn: *sơ đồ này có phải chỉ đúng với vàng không?* Một sơ đồ ăn được trên
XAU có thể là may; ăn được trên bốn thị trường khác nhau thì khó mà may.

Đây chính là **thứ cả §15 làm ra để đổi lấy**: chuẩn hoá về `× ATR`, `× R`, `× ATR nền` là
để con số mang cùng một nghĩa sang thị trường khác. Không dùng đa symbol thì công đó phí.

**Chưa tải gì cả — việc của phase cốt lõi là chắc rằng lõi không dính symbol nào.** Đã soi
và tìm ra bốn chỗ dính thật, đã bịt: **§16.3**. Nay thêm symbol chỉ là thêm file; thiếu dữ
liệu thì app nổ kèm lời giải thích, không đoán.

⚠ Cái giá phải nhớ trước: **mỗi symbol nhân thẳng vào thời gian chạy.** 17,2 s × 4 symbol
= 69 s một lượt chấm (§18.4). Chốt bao nhiêu symbol là chốt luôn ngân sách tìm kiếm.

### 18.4 ✅ Thông lượng — đủ, không cần làm gì

Đo trên máy đang dùng, sơ đồ mẫu, đọc nến **không** tính vào (trả một lần rồi dùng lại):

| khoảng | 1 lượt chấm | nến M1 |
|---|---|---|
| TRAIN 3,5 năm | **17,2 s** | 1,24 triệu |
| 1 năm | 3,2 s | 353 nghìn |
| 1 quý | 0,78 s | 86 nghìn |
| *đọc nến* | *0,08 s* | |

```
8 nhân, một đêm (8 h)  →  ~10.000 sơ đồ chấm trên đủ 3,5 năm
```

Với không gian đã bị chặn bởi trần độ phức tạp (§15.5) và thang số thô (§18.1), chừng đó
**đủ**. Không làm gì thêm.

#### ⚠ Con số trên là SÀN, không phải trung bình — đo bằng sơ đồ NGƯỜI viết

Bảng trên đo bằng **sơ đồ mẫu**: một sơ đồ người viết cẩn thận, cổng chặt, 929 lệnh trong
3,5 năm. Sơ đồ máy sinh bừa thì khác hẳn, và khác **rất** nhiều:

| chạy | nến | giây / sơ đồ |
|---|---|---|
| sơ đồ mẫu | 1,24 triệu (3,5 năm) | **17,2** |
| máy vẽ, lô A | 121 nghìn (12 tuần) | **3,3** |
| máy vẽ, lô B | 60 nghìn (6 tuần) | **24,3** |

Lô B **ít nến hơn một nửa** mà **đắt gấp 7 lần** lô A. Vì:

⭐ **Chi phí một lượt chấm KHÔNG tỉ lệ với số nến — nó tỉ lệ với SỐ LỆNH sơ đồ đẻ ra.**
Sơ đồ sinh bừa hay có cổng lỏng, vào lệnh gần như mỗi nến; đo được một cái đẻ **10.220
lệnh** trên 12 tuần. Sổ lệnh dài thì mọi phép hỏi trên nó cũng dài theo.

Hệ quả cho việc đặt ngân sách: **không ước lượng thời gian bằng số nến.** Phải đo giây
thật trên chính lô đang chạy — và đó cũng là thứ bàn điều khiển nên hiện ra (còn bao lâu),
vì "không chạy mù" gồm cả chuyện biết khi nào xong.

Sàn nhà nằm ở `bo_chay.mot_nhip` — chạy **một lần mỗi nến M1** bằng Python thuần. Muốn
nhanh hơn nhiều lần thì phải viết lại lõi; chưa có bộ sinh thì chưa biết cần nhanh tới đâu,
nên **không viết lại**.

#### ⏸ Món nợ CÓ TÊN: backtest nhanh ~30× — nó chặn đúng một thứ

| dùng cách nào | tốn | cần gì thêm |
|---|---|---|
| tìm một lượt, tiến hoá | 6 h | **không cần gì** |
| cuốn tới 6 vòng, tiến hoá | ~36 h *(1,5 ngày)* | **không cần gì** |
| cuốn tới 6 vòng, **DL thật** *(~100k lượt/vòng)* | ~15 ngày | **17,2 s → 0,6 s** |

⚠ **GPU KHÔNG gỡ được cái tường này**, và đây là chỗ rất dễ tưởng nhầm *("DL thì phải dùng
GPU chứ")*. Đo được: `mot_nhip` chiếm **98%** thời gian một lượt chạy (9,04 s / 9,19 s), là
vòng lặp Python từng nến M1 — GPU không chạm được. Còn phần GPU chạm được thì bé tí:

```
backtest cho 10.000 sơ đồ         10.000 × 17,2 s   =  172.000 s
mạng bắn 1.772 chiều, ~20 nước    200.000 lượt      ≈      200 s     ← 0,1%
```

Mua GPU về là tăng tốc cho 0,1%. Thứ phải mua là **backtest nhanh hơn** (hoặc nhiều nhân
hơn — nó song song hoàn toàn theo ứng viên).

30× là con số **đạt được**: vòng lặp Python từng nến là chỗ chậm nhất có thể, biên dịch hoặc
vector hoá nó là việc đã biết cách làm, không phải nghiên cứu. **Nhưng không làm bây giờ** —
tiến hoá chạy được ngay mà không cần, và chưa chạy thật lần nào thì chưa biết cần bao nhiêu.

#### 18.4a ✅ CẮT RÁC — bỏ dở sơ đồ nã lệnh, **1,3×** (không phải 24× như đã đoán)

Máy sinh ra sơ đồ vào lệnh mỗi nến. Đo trên một quý XAUUSD:

```
sơ đồ NGƯỜI viết       929 lệnh / 3,5 NĂM     ≈   4 lệnh/tuần
máy vẽ #2            7.986 lệnh / 3 tháng     ≈ 614 lệnh/tuần
máy vẽ #4           11.425 lệnh / 3 tháng     ≈ 879 lệnh/tuần
```

Luật, một câu: **cả dải chỉ được `trần/tuần × số tuần` lệnh. Vượt là ném `NaLenh` và bỏ
dở ngay.** `CaiDat.lenh_moi_tuan_toi_da`, mặc định 200 cho khối `"rl"`; khối `"test"`
KHÔNG có ô này nên người vẽ tay không bao giờ bị cắt.

⚠ **Đã đổi luật một lần, ghi lại để đừng quay về.** Bản đầu so với **số tuần ĐÃ TRÔI**.
Cắt sớm hơn thật, nhưng cắt oan: một sơ đồ dồn 16 lệnh vào 4 giờ đầu rồi thôi hẳn có
nhịp cả dải 5,3/tuần, mà xét theo tuần-đã-trôi thì nó đang ở ~670/tuần. Ngân sách cả dải
phát biểu đúng thứ cần loại và không có ca oan nào. Bài kiểm giữ đúng ca đó làm mốc.

⚠ **Và đây là chỗ tôi đã hứa sai — ghi lại vì cái sai ấy đáng nhớ hơn con số.** Ước 24×,
thực tế **1,3×**:

| | trôi | sơ đồ | cắt | sơ đồ/giờ | vượt hạn |
|---|---|---|---|---|---|
| không trần | 402 s | 38 | 0 | 340 | 1,34× |
| trần 200 | 315 s | 38 | 4 | **434** | **1,05×** |

Sai vì tưởng rác chiếm phần lớn thời gian. Chỉ **4/38** vượt trần; thời gian nằm rải đều
ở những sơ đồ *bình thường*. Bài học: **đừng ước bằng ca xấu nhất, phải đo phân bố.**

Cái được thứ hai lại quan trọng ngang: **trần GIỜ thành thật** (vượt 1,05× thay vì
1,34×). `han_giay` chỉ được kiểm giữa hai sơ đồ, nên một con nã lệnh đã bắt đầu là phải
chấm nốt — đặt 8 tiếng rồi đi ngủ mà không có cái van này thì không có gì bảo đảm.

#### 18.4b ✅ TẮT NHẬT KÝ + `zone_da_sinh_lenh` thành `set` — **1,43×**

Profile một năm XAUUSD, sơ đồ mẫu. Hai chỗ chưa ai động tới:

**1. Máy tìm vẫn dựng NHẬT KÝ mà không bao giờ đọc.**

```
một năm · MỘT sơ đồ  →  124.944 mục nhật ký  ·  907.666 lượt gọi `_js`
```

`chay(..., ghi_nhat_ky=False)`. Nhật ký là thứ cửa sổ Tester đọc để trả lời *"cổng này
trượt vì con số nào"* — đắt và **đúng chỗ** ở đó. Mở sơ đồ đầu bảng sang cửa sổ vẽ là
vẫn có đủ.

⚠ **Ngắt sớm thì KHÔNG được, và đây là chỗ suýt sai.** Tắt nhật ký nghe như tặng kèm
phép ngắt ở điều kiện sai đầu tiên. Nhưng `zone_hop_le` **đặt `ctx.zone_da_xet` như một
hiệu ứng phụ**, và bước 5 của `mot_nhip` đọc đúng cờ ấy để quyết định zone sống hay
chết. Bỏ qua một điều kiện là đổi thời điểm zone chết — đổi **KẾT QUẢ**, không phải đổi
tốc độ. Tắt nhật ký chỉ được bỏ việc **GHI**, không được bỏ việc **TÍNH**.

⚠ `so_luot` phải đếm THẲNG, không suy từ `len(nhat_ky)` — không thì tắt nhật ký là bảng
số liệu lặng lẽ báo 0 lượt.

**2. `zone_da_sinh_lenh` quét cả sổ lệnh mỗi lần hỏi.**

```
89.306 câu hỏi  →  8,13 TRIỆU vòng lặp   = 13,8% cả lượt chạy
```

Và nó lớn theo **bình phương**: sổ càng dài thì mỗi câu hỏi càng lâu, mà số câu hỏi cũng
càng nhiều. Thay bằng một `set` ghi trong `mo_lenh`.

⭐ §18.4 từng đo riêng nó **1,11×** rồi cất đi với lý do *"không đáng đánh đổi thêm một
nguồn sự thật"*. Cả hai vế nay đã khác:

- **con số cũ đo lúc nhật ký còn bật**, tức mẫu số bị thổi phồng;
- **không có nguồn sự thật thứ hai**: tập được ghi ở ĐÚNG MỘT chỗ, dòng ngay dưới
  `self.lenh.append(l)` trong `mo_lenh`. Hai dòng liền nhau thì không có đường nào lệch.
  Và `zone_id` không bao giờ bị sửa sau khi lệnh sinh ra (đã soi).

**Kết quả, cùng một sơ đồ trên một năm:**

| | thời gian |
|---|---|
| trước | 4,11 s |
| tắt nhật ký | 3,28 s |
| + `set` | **2,87 s** |

**1,43×**, và **vân tay TRÙNG KHÍT** — 445 lệnh · 967 zone · lãi −7,35% · −8,13 R ·
điểm −0,1038, giống hệt từng con số.

#### 18.4c ✅ SONG SONG — 8,4× tổng cộng, và một bài học về Amdahl

`cat_studio/song_song.py`. **Tiến trình, không phải luồng**: `bo_chay` là Python thuần và
chiếm 98% một lượt chạy, nên tám luồng nhanh bằng đúng một luồng.

⭐ **Tái lập được là ràng buộc cứng**, nên: sơ đồ vẫn do tiến trình CHA bốc theo đúng thứ
tự `random.Random(hạt)`, kết quả vẫn gộp vào bảng theo ĐÚNG thứ tự ấy — không theo thứ tự
trả về. `tests/test_song_song.py` canh 8 nhân = 1 nhân tới từng khoá bảng điểm.

⚠ **Song song lúc đầu VÔ DỤNG, và lý do đáng nhớ hơn con số:**

```
              trước cắt "quá nặng"    sau
 1 nhân            212,8 s          100,4 s
 4 nhân            147,8 s           35,3 s
10 nhân            144,8 s           25,2 s
```

4 nhân và 10 nhân **bằng nhau** ở cột trái. Vì **một sơ đồ ôm 60% công** — 25,8 triệu lượt
chạy sơ đồ, ~300 lệnh sống cùng lúc. Một sơ đồ thì không chẻ ra cho nhiều nhân được, nên
thêm nhân không giúp gì. Đó là Amdahl, không phải lỗi cài đặt. **Cắt con quái trước, song
song mới ăn.**

Bốn cái bẫy của `spawn` trên Windows, cả bốn đều là hỏng lặng:

- **`app_web.py` nạp pythonnet + webview ở mức module.** `spawn` nạp lại module chính
  trong mỗi con → mỗi con kéo cả .NET vào cho thứ nó không dùng. Đã dời vào `main()`.
- **Thiếu `multiprocessing.freeze_support()`.** Bản chạy từ mã nguồn không sao, bản ĐÓNG
  GÓI thì mỗi tiến trình con khởi động lại nguyên cái app — tám cửa sổ mở cùng lúc.
- **`Pool.imap` nuốt sạch iterable.** Luồng tiếp liệu của nó ăn hết ngay; với `so_luot =
  100.000` là bốc sạch 100.000 sơ đồ vào bộ nhớ trước khi cái đầu tiên chấm xong, và mọi
  phép dừng thành vô nghĩa. Phải tự giữ **cửa sổ công việc**.
- **File test chạy ở mức module = bom phân hạch.** `spawn` nạp lại `__main__`, nên
  `test_song_song.py` phải có chốt `if __name__ == "__main__"`.

⚠ Và **cửa sổ công việc phải RỘNG** (`4 × nhân`): kết quả bắt buộc gộp theo thứ tự bốc nên
ta chờ ở ĐẦU hàng, mà chi phí mỗi sơ đồ chênh nhau cả chục lần. Với cửa sổ `2 × nhân`, 4
nhân chỉ nhanh hơn **1,44×** thay vì gần 4×.

#### 18.4d ✅ TRẦN LƯỢT CHẠY SƠ ĐỒ — thứ `NaLenh` mù

```
#37   864 lệnh  ·  25.801.659 lượt chạy sơ đồ  ·  134 s  (60% cả lô 60 sơ đồ)
#1    750 lệnh  ·      642.403 lượt            ·  5,9 s
```

Cùng cỡ số lệnh, chênh nhau **40 lần** số lượt. Vì #37 **ôm lệnh không đóng**: 25,8M ÷
86.379 nến ≈ **300 lệnh sống cùng lúc**, mà Manage chạy một lượt cho MỖI lệnh đang sống.

⭐ Nên chi phí thật đi theo **số lượt chạy sơ đồ**, không theo số lệnh. `lượt ÷ nến` đọc ra
được thành một câu người nói được: *"trung bình bao nhiêu lệnh sống cùng lúc"*.

```
sơ đồ mẫu người viết              0,35
sơ đồ máy nặng nhất còn dùng được 7,4
con quái #37                      299
trần đặt                          30
```

⚠ **Chặn bằng con số ĐẾM ĐƯỢC, không bằng THỜI GIAN.** Chặn bằng giây thì máy chậm cắt
nhiều hơn máy nhanh — cùng hạt giống ra hai kết quả khác nhau, tức mất tính tái lập
(§18.5), thứ đang là ràng buộc cứng.

#### 18.5b ✅ PHÂN BỔ — một lượt chạy trả về ~10 con số thay vì 1

`cat_studio/phan_bo.py`. Bế tắc lớn nhất của §18.5 là *"~40 nước đi, một con số"*. Phân bổ
hỏi hai câu khác: **tiền đi ra từ khối nào**, và **cổng nào chặn cái gì**.

```
Sell Stop dưới đáy vùng   55 lệnh   −531,46 $   −10,28 R
Buy Stop trên đỉnh vùng   58 lệnh    −67,46 $    −0,03 R
Xu hướng XUỐNG?           55 xét → 55 khớp (100%)   ← thừa về logic
```

Cả sơ đồ mẫu lỗ −10,31 R; bảng nói ngay **−10,28 đến từ một nhánh**.

⭐ **Đây là KẾ TOÁN, không phải thống kê** — `Lenh.khoi` là id ĐÚNG cái khối đã đẻ ra lệnh.
Khác hẳn phép đo đã chết ở §18.5d.

⚠ **`Lenh.sinh_tai` KHÔNG phải id khối** — nó là CHỈ SỐ NẾN, dù chú thích cũ của nó ghi là
*"id khối Vào lệnh"*. Đã tin theo một lần: bảng tiền ra rỗng trơn trong khi sổ có 113 lệnh.
`Lenh.khoi` là trường thêm vào cho việc này.

⚠ **"Chắc chắn bỏ được" CHỈ gồm khối CHƯA BAO GIỜ ĐƯỢC ĐẾN.** Hai cái bẫy đã suýt mắc:

- **Cổng luôn khớp KHÔNG hiển nhiên bỏ được** — cổng zone vẫn *nuôi* vùng nén như hiệu ứng
  phụ kể cả khi khớp. Gỡ ra là zone chết khác đi, tức đổi KẾT QUẢ.
- **Khối Vào lệnh đẻ 0 lệnh KHÔNG hiển nhiên bỏ được** — chỉ cần dòng chảy ĐẾN nó là
  `cham_thi_truong` bật và luật lùi (§12.5a) cấm thử nhánh khác.

Bộ đếm mặc định TẮT, tốn **+4,3%** khi bật. Tester bật (chạy đúng một sơ đồ người đang
nhìn); máy tìm tắt.

#### 18.5c ✅ CẮT TỈA — phép ĐỐI CHỨNG, 0,64 giây một câu trả lời sạch

`cat_studio/cat_tia.py`. Bỏ một nhánh, chạy lại, so.

⭐ **Cắt theo NHÁNH chứ không theo khối.** Gỡ một khối giữa dòng rồi nối cha vào con là một
phép *đoán* — cổng ấy có thể đang rẽ hai đường. Cắt cả nhánh thì thứ biến mất đúng bằng
thứ chỉ tới được qua nó, không phải đoán gì.

⚠ **Bất biến, có bài kiểm quét mọi khối:** cắt bất kỳ khối nào cũng chỉ ra `None` hoặc một
sơ đồ **soát tĩnh sạch** — không có đường thứ ba. Và hai điều đã đoán SAI lúc viết:
§17 **không** coi cổng cụt đuôi là lỗi, và sơ đồ chỉ còn khối Bắt đầu **vẫn hợp lệ**.

⚠ **MỘT CỬA SỔ ĐỦ ĐỂ KẾT LUẬN SAI, RẤT THUYẾT PHỤC.** Đo trên sơ đồ mẫu:

```
bỏ nhánh BÁN, quý 2024-Q1 (vàng +8,7%)   →  +0,3872   ← đẹp và SAI
xét cả sáu quý                            →  tốt hơn ở 4/6
```

Nên `mo_sach` chỉ giữ một nhát cắt khi nó **tốt hơn ở ĐA SỐ cửa sổ**, không phải khi điểm
gộp tốt hơn. Mọi nhát cắt đã thử đều vào **biên bản**, kể cả cái bị bỏ — người đọc phải
soi lại được máy đã thử gì và vì sao quyết như thế.

#### 18.5d ⚠ ĐÃ THỬ VÀ CHẾT: đo lợi thế bằng THỐNG KÊ QUAN SÁT

Ghi lại vì nó tốn hai tiếng và vì nó rất dễ có người làm lại.

Ý tưởng: gom hàng trăm sơ đồ, hỏi *"những sơ đồ CÓ thẻ này thì trung bình hơn hay kém"*.
Đo trên **500 sơ đồ × 2 hạt giống**:

```
tương quan hạng giữa hai hạt   −0,172
cùng dấu lợi thế               38/90  (42% — tung đồng xu)
chu_ky:10                      ĐẦU bảng ở hạt này, ĐÁY bảng ở hạt kia
```

**Chết.** Vì 143 sơ đồ mang một thẻ thì khác nhau ở *mọi thứ khác*, và cái khác ấy át hẳn
tác dụng của một thẻ.

⭐ **Bài học tổng quát: nhiễu phải bị triệt tiêu TRONG TỪNG CẶP, trước khi ai kịp lấy trung
bình.** Đó là toàn bộ khác biệt giữa phép đo này và `cat_tia` — cùng là "so sánh", nhưng
một bên so đám mây với đám mây, một bên so vật với vật.

Code đã **xoá** (`kinh_nghiem.py`), giữ lại đúng bài học này. Không giữ code chết.

#### 18.5f ✅ CỬA "ĐỀU QUA THỜI GIAN" — cửa đáng giá nhất thêm vào sau này

`cham_diem.CUA_MAC_DINH["deu_toi_thieu"]`. Phải DƯƠNG ở ít nhất ngần này phần các cửa sổ.

```
cửa cũ cho qua                    ~8% sơ đồ bốc bừa
+ cửa "đều"                       ~2%
```

> **6 trong 8** cái từng nằm ở bảng đầu bảng chỉ ăn may một đoạn thị trường.

Chính nó giết con quán quân `+0,9686` mà thật ra chỉ *"học"* được rằng vàng lên 18,9% quý
đó (§18.6.3).

⚠ **Là CỬA, không phải đổi thước.** Thước vẫn `trung bình ÷ dao động` — §15.1 nguyên vẹn.

⚠ **2% thấp hơn NGẪU NHIÊN rất xa.** Nếu lãi mỗi kỳ là tung đồng xu thì xác suất dương ≥
nửa số cửa sổ là **~65%**; ta đo được **2%**. Nghĩa là sơ đồ bốc bừa KHÔNG ngẫu nhiên —
**chúng thua có hệ thống**, vì mỗi lệnh đều trả spread và hoa hồng. Giao dịch bừa thì lỗ
đều; đó là số học, không phải xui.

⚠ **Số cửa sổ là số NGUYÊN** nên ngưỡng này thô hơn nó trông: với 4 cửa sổ thì `0,5` và
`0,4` ra CÙNG một luật (≥2/4). Muốn nới thật thì đổi `buoc_deu` cho mịn hơn, đừng vặn con
số này.

#### 18.5g ✅ KIỂM CÁI THƯỚC — chỉnh vào một đáp án đã biết

Trước khi hỏi *"máy tìm có giỏi không"*, phải hỏi *"cái thước có nói thật không"*. Cách rẻ
nhất: cho chạy một thứ **biết trước đáp án**.

```
vàng 2024                     +27,1%      ← đáp án
mua-và-giữ, thước chấm        +33,61% lãi · điểm +0,1387 · sụt vốn 0,00%
                              rớt cửa "tuần có lệnh 1/53"
```

**Thước đúng cả ba việc**: thấy tiền, chấm dương, và loại vì một lý do đọc được thành lời
(đây đúng là chiến lược một lệnh — thứ §18.2a sinh ra để chặn).

⭐ Nên mọi kết luận đo đạc của §18 vẫn đứng. Và nó khoanh câu hỏi lại cho sắc: **vấn đề
không nằm ở dụng cụ, nằm ở chỗ không gian hiện tại chưa đẻ ra sơ đồ nào tử tế.**

⚠ Nhưng **KHÔNG biến "thắng mua-và-giữ" thành mục tiêu**. Đích của phase này là **sơ đồ hợp
lí** — mọi khối có việc, mọi cổng có tác dụng; lãi là **bằng chứng và cái cửa**, không phải
cái thang để leo. Biến lãi thành đích là quay lại đúng cái bẫy §18.1.

#### ⏸ CẤT LẠI: học (tiến hoá · thống kê · mạng)

Đã viết `tien_hoa.py` (sinh → chấm → mổ → đột biến → lặp) rồi **xoá**. Lý do không phải nó
sai, mà là **chưa có gì để học**:

```
sơ đồ người viết cẩn thận nhất   lỗ −7,35% trong năm vàng lên +27%
mổ nó bằng dụng cụ mới           −0,42 → −0,04.  Vẫn âm.
sơ đồ bốc bừa                    ~2% dương đều (ngẫu nhiên là 65%)
```

Máy học bằng cách bắt chước cái tốt. Chưa chứng minh được **có cái tốt nào tồn tại** trong
không gian hiện tại — mà kho đồ còn nhỏ thì đó là chuyện đương nhiên của phase 0.

Ba con số đã đo, để khi nào quay lại thì khỏi dò lại:

- **Dân số 20 con cần ~1.000 sơ đồ mỗi vòng** (ở tỉ lệ qua cửa 2%). Ba lượt thử với 30 ·
  80 · 120 sơ đồ đều chỉ ra **1–2 con sống sót** — thiếu công suất từ lúc bấm chạy.
- **Đột biến = cắt chuỗi nước đi rồi đi nốt.** Đo được: cắt ở 30% · 50% · 80%, **9/9** ra
  sơ đồ soát tĩnh sạch. Mặt nạ luôn chừa đường về đích nên cắt ở đâu cũng đi tiếp được.
- **Ba bẫy plateau** và ba chỗ chặn, cả ba đều thành con số hiện trên màn hình: mổ chỉ đi
  xuống (cần đột biến); đột biến từ top-K co cụm (cần ~30% bốc bừa + bốc ĐỀU trong top-K,
  vì thứ tự bên trong bảng đã đo là nhiễu +0,54); điểm nhiễu (cần nhóm bốc bừa làm ĐỐI
  CHỨNG chạy song song mãi).

⭐ Và **nhóm bốc bừa làm hai việc bằng một thứ**: nguồn cái mới, và cái mốc phải thắng.

#### ⏸ Còn lại: viết lại lõi backtest

| | được | giá |
|---|---|---|
| **biên dịch sơ đồ thay vì đi bộ** | ~30× | viết lại lõi |

⭐ Có một sự thật cấu trúc khiến cái 30× làm được, ghi lại để khỏi phải tìm lại: **điều
kiện Entry hầu hết là hàm KHÔNG TRẠNG THÁI của mấy cột số.** `ATR(M5) < ngưỡng × ATR nền`
tính sẵn được cho cả dải thành một mảng bool; lúc chạy chỉ còn tra chỉ số. Chỉ **lệnh** và
**zone** mới thật sự tuần tự.

#### Hai thứ đã đo rồi CẤT ĐI, đừng làm sớm

- **Sàng hai tầng** *(quý 0,78 s lọc trước, TRAIN 17,2 s chấm sau)* — nếu tầng 1 giết 90%
  thì 6 h còn 0,9 h. Đã tính, **chưa làm**: đó là tối ưu cho một vấn đề chưa xảy ra. Nếu
  ngày nào làm, luật sống còn là **tầng 1 chỉ được loại thứ HỎNG, không được loại thứ LỖ**
  (0 lệnh · cháy tài khoản · sụt vốn > 50%). Một quý = 13 tuần, còn cần 48 (§18.3) — bắt
  13 tuần chấm điểm là lặp lại đúng cái sai đã chứng minh ở §18.1.
- **`so_lenh.zone_da_sinh_lenh` quét lại cả sổ lệnh mỗi lần hỏi** (6,7 triệu vòng cho 87
  nghìn câu hỏi trên một năm). Thay bằng `set` thì kết quả **trùng khít** nhưng chỉ nhanh
  hơn **1,11×** — đo rồi, không đáng đánh đổi thêm một nguồn sự thật lúc này.

### 18.5 ✅ Cách tìm — CHƯA CHỐT, và đó là chủ ý

⭐ **Thuật toán tìm KHÔNG thuộc core.** Core là bốn thứ: kho đồ (§15) · luật chơi (§16, §17)
· cách chấm (§18.2) · dữ liệu (§18.3). Dò ngẫu nhiên, tiến hoá và RL là **ba cách bới cùng
một không gian, chấm bằng cùng một thước, trên cùng một dữ liệu**. Đổi cái nào cũng không
phải đụng xuống bốn thứ kia — nên không cần chốt bây giờ, và chốt sớm là tự trói.

⚠ **Một khuyến nghị đã RÚT LẠI, ghi để đừng ai đào lên dùng:** *"dùng tiến hoá, không dùng
RL"*. Nó đúng với **không gian hôm nay** (nhỏ, đã bị chặn bởi §15.5 và §18.1) nhưng sai khi
đem làm quyết định kiến trúc — giai đoạn sau phình kho, phình luật thì phải đập đi làm lại.
Kế hoạch từ đầu là *làm nền nhỏ mà chắc, rồi mới mở rộng*; chọn thuật toán là việc của lúc
mở rộng.

#### Thứ ĐÃ đo được và giữ lại: mặt điểm TRƠN

Đi từng nấc thang §18.1 cho từng tham số của sơ đồ mẫu, chấm theo §18.2, trên TRAIN 3,5 năm:

| tham số | khoảng điểm | số lần đổi chiều |
|---|---|---|
| SL `× ATR zone` | −0,204 … −0,070 | 1/3 |
| TP `× R` | −0,230 … −0,096 | 1/3 |
| ngưỡng cổng `× ATR nền` | −0,269 … −0,058 | 1/4 |
| hoà vốn tại `× R` | −0,208 … −0,118 | 1/2 |
| số vị thế tối đa | −0,176 … −0,139 | 0/2 |
| rủi ro % vốn | −0,176 … −0,169 | 1/1 |

**Cả sáu đều trơn** — đổi một nấc thì điểm nhích một chút, đổi chiều nhiều nhất một lần.
Trơn nghĩa là *hàng xóm của sơ đồ tốt thì cũng tốt*, tức **leo dốc có tác dụng**. Đó là điều
kiện để bất kỳ cách tìm có hướng nào (tiến hoá, RL) hơn được dò mù. Số đo này thuộc về
**không gian**, không thuộc thuật toán — nên nó vẫn đúng dù sau này chọn cái gì.

*(Chính phép đo này bắt được lỗ hổng §18.2c: dòng `ngưỡng 0,25` cho điểm cao nhất bảng với
đúng 1 lệnh.)*

#### Một sự thật của hệ này, ảnh hưởng mọi lựa chọn sau

⭐ **Không có điểm giữa chừng.** Sơ đồ dựng dở không vào lệnh nào, nên **không chấm được**.
Mọi cách tìm ở đây đều chỉ nhận đúng một con số ở cuối mỗi lượt. Hệ quả: MCTS và beam search
không dùng được (chúng sống nhờ điểm của trạng thái dở dang), còn RL thì đói thưởng — không
phải không làm được, nhưng phải biết trước.

#### Việc còn lại của nền: §17 từ NGƯỜI SOÁT thành NGƯỜI BÀY

Hôm nay `validate_flow_graph` là **người soát**: vẽ xong rồi mới nói đúng/sai. Thứ mọi cách
tìm đều cần là **người bày**:

```
nuoc_di_hop_le(sơ đồ đang dở)  →  [thêm cổng X · nối vào nhánh Y · đặt SL nấc Z · …]
```

Cùng một tri thức (§17), đổi hình dạng. Phục vụ cả ba, không phải chọn một:

| ai dùng | dùng thế nào |
|---|---|
| dò ngẫu nhiên | bốc bừa một nước trong danh sách |
| tiến hoá | lùi vài nước rồi dựng lại khác đi |
| RL | policy chấm từng nước rồi chọn |

Kèm hai món lợi:

- **Sơ đồ = một chuỗi nước đi.** Chuỗi ấy vừa là thứ để đột biến, vừa là thứ policy sinh ra,
  vừa là thứ lưu lại để dựng lại y hệt. Một cách biểu diễn, ba việc. RL **bắt buộc** phải có
  nó; tiến hoá thì không, nên xây kiểu người-bày ngay từ đầu là chỗ RL được chuẩn bị sẵn mà
  không phải làm RL bây giờ.
- **Sơ đồ hỏng không bao giờ được sinh ra**, thay vì sinh ra rồi tốn 17 s backtest mới biết
  là rác.

### 18.6 CỬA SỔ RL — bàn điều khiển, không phải một cái nút

> Ý định người dùng, nguyên văn: *"ta không xây dựng 1 hệ thống cứng nhắc, ta đang làm 1
> game/studio"*. Cửa sổ RL là chỗ **chơi**: bật tắt đồ nghề, chỉnh thưởng phạt, nhìn máy
> học, can thiệp. Cửa sổ Home chỉ thêm một ribbon nhỏ để **mở sơ đồ ra xem**, không hơn.
>
> Bàn từng phần, chốt từng phần. Dưới đây là phần đã chốt.

#### 18.6.1 ✅ Phần 1 — hai TẦNG: **LUẬT** không tắt được · **CHỌN** tắt thoải mái

Chỗ này người dùng ghép nhầm hai thứ *(hỏi: "setup luật chơi — hình như là cái người bày
bạn đang đề cập")*, và tách được chúng ra là việc đầu tiên phải làm, vì **cả cửa sổ dựng
trên nó**: cái gì lên panel bật/tắt, cái gì không bao giờ được xuất hiện thành nút.

| | là gì | ví dụ | chỉnh được? |
|---|---|---|---|
| **LUẬT** §17 | cái gì **HỎNG** | *sau `Kết thúc lệnh` không nối được gì nữa* | **không** |
| **CHỌN** | cái gì bạn **MUỐN** lần này | *lần này đừng đụng zone* | **có** |

⭐ **"Người bày" (§18.5) thuộc tầng LUẬT.** Nó chỉ đổi *hình dạng* của §17 từ **soát** sang
**bày ra** — cùng một tri thức, không phải tri thức mới, nên không có gì để chỉnh. Cho tắt
là cho máy vẽ sơ đồ **nói dối**: hình vẽ ba việc, lượt chạy làm một việc. Đó không phải sở
thích, đó là hỏng — và §17 mở đầu bằng đúng câu ấy.

Tầng CHỌN thì ngược lại, **nên chỉnh thoải mái**:

```
kho đồ        tắt/bật từng toán hạng, từng loại khối
độ phức tạp   trần khối · nhánh · điều kiện              §15.5, đã chốt
thang số      nấc nào cho SL, TP, ngưỡng, rủi ro         §18.1, đã chốt
ưu tiên       ghét sụt vốn tới đâu, thèm lãi tới đâu
dữ liệu       symbol nào, khoảng nào                     §18.3, §18.3a
```

#### Cách chấm cũng chia đúng hai tầng ấy

| | |
|---|---|
| **khoá cứng** | chấm bằng **TIỀN, theo TUẦN** — vì `tổng R` mù phí, đo rồi (§18.2b); và cửa "tuần có lệnh" (§18.2a) |
| **chỉnh được** | nặng tay với sụt vốn tới đâu, với lãi tới đâu |

⭐ **Chỉnh được THÍCH GÌ, không chỉnh được ĐO BẰNG GÌ.** Cái thước không phải ý thích — đúng
bất biến đã chốt từ §15: *"cái thước không được là tham số"*.

⚠ Vì sao chỗ này đáng một mục riêng: một studio đúng nghĩa thì **nhiều nút là tốt**. Nhưng
một nút cho phép tắt §17, hoặc cho phép chấm bằng `tổng R`, thì không phải nút — nó là con
bọ có nhãn. Ranh giới nằm ở câu hỏi *"tắt cái này thì hệ thống nói dối, hay chỉ là chạy
theo kiểu khác?"*

#### 18.6.2 ✅ Phần 2 — cửa sổ làm BỐN việc, và máy KHÔNG sống trong cửa sổ

Chốt động từ trước khi bàn nút nằm đâu: một bàn điều khiển không rõ động từ thì sớm muộn
thành bức tường nút bấm.

```
1. ĐẶT    chọn kho · trần · thang · ưu tiên · dữ liệu     (tầng CHỌN, §18.6.1)
2. CHẠY   bắt đầu · dừng · chạy tiếp
3. NHÌN   nó đang tới đâu, cái tốt nhất hiện ra sao
4. MỞ     lấy sơ đồ tốt nhất sang cửa sổ vẽ
```

**Ribbon ở cửa sổ Home = đúng việc 4**, không gì khác.

⭐ **Máy tìm KHÔNG sống trong cửa sổ.** Một lượt chạy mất cả đêm (§18.4); đóng cửa sổ RL để
mở một sơ đồ ra ngắm mà giết luôn 6 tiếng đã chạy là hỏng. Cửa sổ chỉ là **cái để nhìn**.

App đã có tiền lệ, và nó đang là **nợ**: §14.4 — *"đóng cửa sổ Live là dừng phiên"*, dù
`ApiLive` vốn dựng theo hướng *"máy live không sống trong cửa sổ"*. RL không được phép mắc
lại món nợ ấy — làm đúng ngay từ đầu, vì ở đây cái giá cao hơn hẳn (một đêm, không phải một
phiên xem).

#### Cắt khỏi phase 1 — có chủ ý

| cắt | vì sao |
|---|---|
| panel tham số DL/RL | chưa chốt thuật toán (§18.5) thì mọi nút ở đây là **nút hứa suông** — đúng loại §16.3 và `don_bay` đã dạy |
| tạm dừng giữa chừng rồi chạy tiếp | dừng hẳn + chạy lại là đủ dùng |
| plot đẹp | số nào ĐÁNG hiện mới là chỗ dễ sai — phần 3 |

Người dùng tự nói: *"tôi hiểu cách 1 DL hình thành, nhưng không biết setting như nào cho phù
hợp"*. Đó chính là lý do để nó sau cùng — chưa có bộ sinh thì **không ai** biết, và bày nút
ra bây giờ là bày nút đoán mò.

#### 18.6.3 ✅ Phần 3 — số nào được phép lên màn hình

**Hiện, mỗi cái một việc:**

| | việc của nó |
|---|---|
| **trung bình tuần %** và **dao động tuần %** — để **RỜI** | `0,05 ÷ 0,5` và `0,5 ÷ 5` cho cùng một điểm nhưng là hai chiến lược khác hẳn |
| điểm = trung bình ÷ dao động | §18.2 |
| tuần có lệnh | để thấy nó **có chơi thật** — cái cửa §18.2a |
| sụt vốn sâu nhất | |
| đã chấm / ngân sách | §18.4 |

⚠ **KHÔNG hiện `tổng R`.** Đo rồi: `+25,38 R` trong khi tiền thật `+0,27%` (§18.2b). Để nó
nằm cạnh điểm thật là mời người ta đọc nhầm.

**Hai đồ thị, mỗi cái trả lời đúng một câu:**

| | câu nó trả lời |
|---|---|
| điểm tốt nhất theo số lượt đã chấm | *còn tìm được gì nữa không — dừng được chưa* |
| chuỗi tuần của cái tốt nhất | *nó có ĐỀU không* — tiêu chí gốc của người dùng |

#### ⭐ Phần chính: mọi số trên màn hình đều là số TRAIN

Đoạn khoá chưa mở (§18.3). Một bảng số đẹp đẽ không được trông như kết luận — nó là kết quả
đo trên chính đoạn dữ liệu máy vừa đào bới hàng nghìn lượt.

Và luật *"mở đúng một lần"* hiện mới chỉ là **lời hứa**. Có một cái nút *"chạy trên đoạn
khoá"* bấm bao nhiêu lần tuỳ thích thì cái khoá là giả.

**Không chặn — ĐẾM.**

```
Đoạn khoá 2025 — bạn đã mở 3 lần
```

Không cấm bấm: đây là studio, không phải cái lồng. Nhưng mỗi lần bấm thì con số tăng và nằm
đó, để lần thứ mười người đọc nhìn phát biết ngay con số mình đang tin đã mòn tới đâu. Cùng
tinh thần `_spread` và `_thong_so` (§16.2, §16.3): app **không giấu**, app **nói ra**.

#### 18.6.4 ✅ Phần 4 — "ưu tiên" là mấy cái CỬA, không phải mấy cái CÂN

⚠ **Bịt một chỗ hở tự tạo ra ở §18.6.1:** mục đó hứa tầng CHỌN có *"ghét sụt vốn tới đâu,
thèm lãi tới đâu"*, nhưng công thức §18.2 là `trung bình ÷ dao động` — **không có khe nào để
cắm cái nút ấy vào**.

```
CÂN    điểm = trung bình÷dao động − λ × sụt vốn        ← chỉnh λ
CỬA    sụt vốn > 25% → loại. Còn lại xếp theo điểm.    ← chỉnh 25%    ✅ chọn cái này
```

**1. Sụt vốn không đổi chác được.** Cháy 60% tài khoản thì không mức lãi nào bù lại — đã ra
khỏi cuộc chơi. Với `λ` nhỏ, sơ đồ điểm cao mà sụt vốn 60% vẫn thắng; với cửa thì nó không
bao giờ lọt vào danh sách. Cân chỉ đúng cho những thứ **thật sự đổi được cho nhau**.

**2. Cửa là câu nói được, `λ` thì không.** *"Tôi không chấp nhận sụt quá 25%"* — phát biểu
được, và biết mình vừa nói gì. *"λ = 0,3"* thì phải **dò** mới biết nặng hay nhẹ — mà dò cái
nút chấm điểm là dò trên chính thứ dùng để chấm, đúng cái bẫy §18.1.

**3. Trùng với dữ liệu đã đo.** Hai bản SL của sơ đồ mẫu (§18.2c):

| | điểm | sụt vốn |
|---|---|---|
| SL 1,5 | −0,145 | **46,1%** |
| SL 3,0 | +0,001 | 25,0% |

Cửa ở 30% loại thẳng bản 46% — **cùng kết luận với điểm**, mà không phải chỉnh cân nào.

**Panel ưu tiên = một nhúm cửa:**

```
sụt vốn tối đa            %
tuần có lệnh tối thiểu    %      ← §18.2a, khoá cứng ở ½, panel chỉ SIẾT thêm được
lãi tối thiểu             %/năm  (để trống là không lọc)
```

⭐ **Xếp hạng thì LUÔN là `trung bình ÷ dao động`.** Bạn chỉnh *"cái gì tôi không nhận"*;
máy xếp hạng phần còn lại bằng **đúng một cái thước**. Lại là §15: *cái thước không được là
tham số*.

#### 18.6.5 ✅ Phần 5 — nó đẻ ra cái gì

##### Một DANH SÁCH NGẮN, không phải một nhà vô địch

Cái điểm cao nhất là cái **khớp lịch sử nhất** — theo đúng định nghĩa của việc đi tìm. Lấy
đúng nó là lấy cái đã bị mài kỹ nhất.

Nhìn cả nhóm đầu bảng thì đọc ra thứ khác hẳn:

```
8/10 sơ đồ dùng chung một cổng   →  chỗ này là THẬT
mỗi cái quản lệnh một kiểu       →  chỗ này là nhiễu
```

⭐ **Cái CHUNG giữa nhiều sơ đồ đáng tin hơn bất kỳ sơ đồ đơn lẻ nào** — nó sống sót qua
nhiều đường đi khác nhau, không phải một. Và người đọc ra nó là **người dùng**; máy không
kết luận hộ.

Đo được, và nó nói thẳng *đừng lấy quán quân*: chấm 24 biến thể trên hai nửa của train —

| | nửa đầu | nửa sau |
|---|---|---|
| SL2,0 TP2,0 ng0,75 | **hạng 1** | hạng 13 |
| SL3,0 TP2,0 ng0,75 | hạng 11 | **hạng 1** |

Quán quân đổi chỗ hoàn toàn (tương quan thứ hạng **+0,54**; top 8 chỉ giữ **4/8**). Nhưng
**hướng lớn thì giữ** — mọi bản `SL 3,0` bám top ở cả hai nửa, mọi bản `SL 1,0` nằm đáy ở cả
hai. Đúng bài học §18.1: hướng đi thật, độ chính xác là nhiễu.

⏸ *Lọc nhóm đầu bảng bằng gì (nửa kia của train · valid riêng · các vòng cuốn tới) thì phụ
thuộc §18.3 — đang cất lại.*

##### File chiến lược BÌNH THƯỜNG — không có loại "sơ đồ của máy"

Cùng JSON · cùng thư mục · mở bằng cùng cửa sổ vẽ · chạy bằng cùng Tester · lên Live cùng
đường. `cat_studio/mau/compress.json` đã chứng minh định dạng chịu được: sơ đồ mẫu là JSON y
hệt mọi chiến lược khác.

Nghĩa là **sửa tay được ngay**: máy tìm ra khung, người thấy chỗ nào ngứa thì đổi, chạy lại,
so. Đó mới là studio.

Đây không phải phát minh mới — nó là lời chốt của chính người dùng từ §15: *"kho người dùng
được và máy dùng phải thống nhất"*. Máy đẻ ra định dạng riêng là lời chốt ấy vỡ, và ba tháng
sau có hai đường code làm cùng một việc.

⚠ **Tên khối do máy đặt sẽ vô nghĩa** (`[1A] cổng 1`). Nhưng chỗ này **không phải làm gì
thêm**: `core.action_display` là nơi duy nhất dựng chữ (Python dựng, JS chỉ hiện — bất biến
§12). Bộ sinh điền đúng mấy trường `action_display` đọc thì sơ đồ máy vẽ đọc ra y như sơ đồ
vẽ tay.

---

### 18.7 ✅ NGƯỜI BÀY — ĐÃ CÀI: `cat_studio/nguoi_bay.py`

> Từng là **việc duy nhất đang chặn**: chưa có nó thì không câu hỏi nào ở §18.3 (chia dữ
> liệu), §18.4 (nhanh bao nhiêu) hay §18.5 (thuật toán nào) **kiểm chứng được** — chỉ cãi
> được bằng lý lẽ suông. Nay có rồi; §18.7.4 ghi những gì đã cài và những gì nó bắt được.

Bốn ô của một bài toán học tăng cường, và ba ô đã có sẵn:

| | ở đâu |
|---|---|
| **TRẠNG THÁI** — sơ đồ đang dở | *ô còn thiếu, mục này lấp* |
| **HÀNH ĐỘNG** — nước đi hợp lệ tiếp theo | người bày |
| **PHẦN THƯỞNG** — điểm cuối lượt | §18.2, xong |
| **CHÍNH SÁCH** — chọn nước nào | chỗ thuật toán cắm vào, §18.5, chưa chốt |

Ba điểm dưới đây là **hình dạng**, không phải số. Hình dạng sai thì đập đi làm lại; số sai
thì vặn lại. Cả ba đều **rẻ hôm nay** và đắt về sau.

#### 18.7.1 ✅ Sơ đồ = MỘT CHUỖI NƯỚC ĐI, và chỉ một cách biểu diễn

```
1  bắt đầu · M5
2  thêm điều kiện   ATR < 0,75 × ATR nền
3  thêm điều kiện   zone hợp lệ
4  vào lệnh         mua · market · SL 1,5 × ATR zone · TP 2 × R · rủi ro 0,5%
5  kết thúc
```

Năm dòng đó **LÀ** sơ đồ, không phải bản tóm tắt của nó.

⭐ **Một cách biểu diễn, bốn việc:** lưu file · dựng lại y hệt · đột biến · cho mạng đọc.
Không có bản thứ hai nào phải giữ đồng bộ bằng tay — đúng bất biến *một nguồn sự thật*.

#### 18.7.2 ✅ Kho nước đi **CỐ ĐỊNH** + **mặt nạ** hợp lệ

```
SAI    người bày trả về:  [3 nước đi hợp lệ lúc này]
ĐÚNG   người bày trả về:  [toàn bộ 1.772 nước] + mặt nạ bật 3 cái
```

Mạng nơ-ron bắn xác suất trên **một danh sách cố định**. Danh sách co giãn mỗi bước thì
không đầu ra nào khớp được. Mà dò ngẫu nhiên và tiến hoá thì kiểu nào cũng chạy — nên viết
đúng ngay từ đầu **không tốn thêm gì**, viết sai thì lúc cắm DL phải đập ra làm lại.

#### 1.772 — đếm từ kho, không phải con số bịa

| loại nước đi | số | từ đâu |
|---|---|---|
| điều kiện, vế phải là **số** | 1.056 | 22 toán hạng × 8 phép so × 6 nấc |
| điều kiện, vế phải là **giá** | 392 | 7 mức giá × 8 phép so × 7 mức giá |
| vào lệnh | 300 | 2 hướng × 2 loại × 5 SL × 5 TP × 3 rủi ro |
| sửa lệnh | 12 | 4 chế độ, cái cần khoảng thì × 5 nấc |
| cấu trúc | 12 | đóng nhánh · mở nhánh · kết thúc · 8 khung giờ |
| | **1.772** | |

Con số này **rơi ra từ** kho đồ (§15) nhân thang số (§18.1) — không ai đặt nó. Thêm một toán
hạng thì kho nước đi tự lớn, **không phải sửa bảng nào**.

1.772 là cỡ rất dễ chịu: mô hình ngôn ngữ có từ vựng 30.000–200.000. Một lớp đầu ra 1.772
chiều là chuyện thường.

**Ba cách dùng, một cơ chế:**

| | |
|---|---|
| dò ngẫu nhiên | bốc trong mấy ô đang bật |
| tiến hoá | đổi một ô đang bật sang ô khác đang bật |
| DL | mạng bắn 1.772 số, nhân mặt nạ, chọn |

⚠ **Đổi thang số là đổi kho nước đi.** Với ngẫu nhiên và tiến hoá thì vô hại; với một mạng
đã học rồi thì **phải học lại**. Nên thang số nằm ở tầng CHỌN (§18.6.1) là đúng, nhưng
**không được đổi giữa chừng một phiên học**.

#### 18.7.3 ✅ Người bày đi **HAI CHIỀU**

```
xuôi    sơ đồ đang dở   →  mặt nạ nước đi hợp lệ      (để SINH)
ngược   sơ đồ có sẵn    →  chuỗi nước đi              (để ĐỌC)
```

Như công thức nấu ăn: **xuôi** là đang nấu thì bước sau làm gì; **ngược** là nhìn món đã
xong rồi viết lại công thức.

Chiều ngược là chiều dễ quên nhất, và nó mở ra ba thứ:

| | |
|---|---|
| ⭐ **học từ sơ đồ người dùng vẽ tay** | máy bắt đầu từ chỗ đã biết là hợp lý, không mò từ số không |
| chữa bệnh **thưởng chỉ có ở cuối lượt** | §18.5 — đây là cách chuẩn để chữa |
| **một bài kiểm miễn phí** | đọc ngược sơ đồ mẫu rồi dựng xuôi lại phải ra **đúng nó** |

Cái thứ ba chạy được **ngay khi người bày vừa xong**, và nó chứng minh hai chiều khớp nhau —
thứ không có cách nào kiểm khác.

⭐ Chiều ngược gần như **miễn phí nếu thiết kế cùng lúc** với chiều xuôi. Làm sau thì phải
viết lại cả người bày.

#### 18.7.4 ✅ ĐÃ CÀI — `cat_studio/nguoi_bay.py`, test 41/41

| | |
|---|---|
| kho nước đi | **1.863** — sinh từ kho × thang, không gõ tay |
| trần độ phức tạp | §15.5 vào code lần đầu: `4 · 3 · 12 · 8`, là **tham số** của `mat_na` |
| hai chiều | đọc ngược sơ đồ mẫu → **44 nước** → dựng xuôi lại **trùng khít** |
| sinh bừa | 60/60 lượt tới đích · **0 lỗi 0 cảnh báo** từ soát tĩnh · 0 lượt nổ khi chạy |

```
vao_lenh 1.050 · dk_so 486 · dk_gia 252 · dk_ds 12 · sua_lenh 12
nhip 9 · tf_trai 9 · tf_phai 9 · chu_ky_trai 7 · chu_ky_phai 7 · dem 4
cong_moi · cong_zone · hop_le · mo_nhanh · dong_nhanh · het
```

⭐ **Thứ bổ nghĩa là nước đi RIÊNG** (`tf_*`, `chu_ky_*`, `dem`) chứ không nhân vào nước
chính. Nhét khung giờ vào `dk_so` thì kho phồng từ 486 lên hơn hai vạn; tách ra thì chỉ
**cộng 36 ô**. Đây là chỗ quyết định kho ở cỡ nghìn hay nhảy lên cỡ vạn.

#### Cái giá của "người bày phải nói ĐÚNG như người soát"

Viết xong lần đầu tưởng là xong. Cho sinh bừa 60 sơ đồ thì soát tĩnh mắng **910 lỗi**. Bảy
chỗ mặt nạ hụt so với §17, phải bổ đủ — và không chỗ nào đoán ra được nếu không đo:

| chỗ hụt | hậu quả |
|---|---|
| toán hạng chưa khai `tf`/`period` mà cho đi tiếp | 910 lỗi *"chưa chọn khung thời gian"* |
| nhánh kết thúc bằng CỔNG | cổng cụt — hỏi xong rồi không làm gì |
| `× ATR zone` trong ĐƠN VỊ mà không có cổng zone | zone nấp trong đơn vị, không ở tên toán hạng |
| lệnh chờ neo `close` mà không đệm | khớp ngay, không còn là lệnh chờ |
| hai khối Vào lệnh giống hệt trên một đường | chỉ ra ĐÚNG một lệnh |
| nhịp Manage chậm hơn Entry | lệnh vừa sinh phải chờ mới được quản |
| xếp chỗ trên canvas | §17 đọc toạ độ để biết nhánh nào thử trước — **không đặt `pos` thì mọi ngã rẽ là lỗi** |

Cái cuối đáng nhớ nhất: **toạ độ là một phần của NGHĨA**, không phải trang trí.

#### Ba ngõ cụt — mặt nạ phải CHỪA CHỖ, không chỉ cấm

Ba lần lượt đi tắc cứng (mặt nạ tắt sạch giữa chừng), cả ba đều là *đúng luật ở từng bước
mà không có lối ra*:

1. **Cổng cụt hiểu sai** — sau `dong_nhanh` thì `diem` lùi về chỗ rẽ; chỗ ấy LÀ một cổng
   nhưng ĐÃ có nhánh con nên không cụt. Lẫn hai thứ ⇒ 19/60 lượt tắc. *Cổng cụt = cổng
   **không có gì phía sau**, không phải "khối cuối là cổng".*
2. **Hết ngân sách khối** — đẻ cổng khi chỉ còn một suất là tự vào ngõ cụt: cổng đứng đó,
   không đóng nhánh được, không `het` được. Nay nước đẻ CỔNG phải chừa sẵn một suất cho
   hành động sau nó.
3. **Hết chế độ Sửa lệnh** — ở Manage nhánh chỉ đóng được bằng khối Sửa lệnh, mà §17.2 cấm
   hai khối ghi đè nhau. Đường đã dùng hết các chế độ thì cổng mới trên đó vĩnh viễn không
   có gì nối tiếp.

⭐ Bài học chung: **một luật cấm đúng ở từng bước vẫn có thể dồn người đi vào chỗ chết.**
Người bày phải trả lời được câu *"đi nước này rồi còn về đích được không"*, không chỉ
*"nước này có hợp lệ không"*.

#### Hai lỗi của APP lộ ra trong lúc dựng

**1. `chu_ky_atr` bị đòi vô điều kiện, rồi lại bị mắng là thừa.**

`bo_chay._kiem_tham_so` đòi nó cho MỌI chiến lược *(lý do ghi trong code — "engine
Compress nuôi vùng nén" — chỉ đúng một nửa: nó còn là chu kỳ của cái ATR mà mọi phép đổi
`× ATR` dùng)*. Nhưng khai nó vào thì `validate_process` mắng *"tham số không khối nào dùng
tới"*. **Hai bên đòi ngược nhau, không cách nào làm vừa lòng cả hai** — 20/25 sơ đồ sinh tự
động rơi vào đúng cái kẹp ấy.

Sửa: `core.THAM_SO_NGAM` + `core.can_tham_so_ngam(doc)` — **một chỗ** trả lời "có cần
không", ba nơi hỏi (bộ chạy · soát tĩnh · người bày). Nay không bao giờ nói ngược nhau.

**2. `tools/van_tay.py` cất khoá năm bằng SỐ, đọc lại từ JSON thành CHỮ** — nên lúc báo
lệch nó in `cũ null` thay vì hai con số cần so. Một công cụ giải thích sai đúng lúc cần nó
giải thích nhất. *(Cùng đợt: nó còn quên truyền `contract_size` — xem §16.3.)*

#### Sau khi có người bày thì đo được ngay những gì

Mấy câu ở §18.3, §18.4, §18.5 đang cất lại chính là mấy câu này — **giờ đo được rồi**:

- bao nhiêu % sơ đồ sinh ngẫu nhiên vào nổi **một lệnh** *(quyết định ngân sách thật)*
  — số đầu tiên đã có: **9/25** trên nến tổng hợp
- tiến hoá có thắng nổi dò ngẫu nhiên không *(nếu không thì bỏ tiến hoá)*
- một vòng cuốn tới tốn bao lâu thật *(quyết định A hay B, và có cần nhanh 30× không)*
- chia dữ liệu hai/ba phần hay cuốn tới — cái nào cho con số ngoài mẫu ổn định hơn

### 18.8 ✅ BA MÓN trước frontend — XONG CẢ BA

> §18.6.2 chốt cửa sổ RL có bốn việc, mà ba trong bốn từng **không có gì phía sau**. Làm
> frontend lúc ấy là dựng đúng thứ §18.6.2 vừa cấm: **nút hứa suông**.
>
> Ba món dưới đã cài xong, mỗi món một module và một bài kiểm.

**1. ✅ CHẤM ĐIỂM — ĐÃ CÀI: `cat_studio/cham_diem.py`, test 22/22**

```
chuoi_ky(kq, TUAN|THANG)  →  lãi/lỗ mỗi kỳ tính bằng % vốn ĐẦU, KỂ CẢ kỳ trắng
cham(kq, cua)             →  ba con số + mọi cửa + `dat` / `ly_do`
xep_hang(ds, cua)         →  (qua, rớt) — rớt vẫn giữ, không im lặng biến mất
```

Đối chiếu với số đo tay ở §18.2c — **khớp tới chữ số cuối**:

| | trung bình tuần | dao động | điểm |
|---|---|---|---|
| SL 1,5 | −0,161% | 1,115% | **−0,145** |
| SL 3,0 | +0,001% | 1,311% | **+0,001** |

⭐ **Cửa §18.2a chặn đúng lỗ hổng nó sinh ra để chặn.** Sơ đồ vào một lệnh trong 3,5 năm
ăn điểm **−0,065**, cao hơn sơ đồ thật (**−0,145**) — rồi rớt cửa với dòng *"tuần có lệnh
1/236 (0%) — dưới 50%"*. Bài kiểm viết đẳng thức ấy ra: một kỳ có lệnh trong N kỳ **luôn**
cho `±1/√(N−1)`, thử ở N = 10 · 100 · 236 với lệnh 0,5 · 5 · 500 — cùng một con số.

Ba điều đáng ghi lại:

- **Chia cho vốn ĐẦU, không phải vốn lúc đó.** Chia cho vốn lúc đó là trộn lãi kép vào
  chuỗi: cùng một lệnh thắng ở tuần 200 thành số nhỏ hơn ở tuần 1 chỉ vì vốn đã khác — mà
  dao động lại đo trên chính chuỗi ấy.
- **Đếm kỳ theo NẾN, không theo ô `tu`/`den`.** Ô ấy là thứ người dùng gõ; đặt rộng quá là
  đẻ ra hàng trăm tuần trắng ma và cửa `tuan_co_lenh` đánh trượt mọi chiến lược.
- **`bo_chay.lai_lenh` tách ra thành một chỗ duy nhất**, `_thong_ke` và `cham_diem` cùng
  gọi. Chép công thức tiền ra hai bản là bảng số liệu nói một đằng, điểm chấm nói một nẻo.

⚠ **Một lần tự phức tạp hoá, đã rút lại:** thử làm `chu_ky_atr` thành "chỉ cần khi sơ đồ
đụng zone hoặc `× ATR`". SAI — `bo_chay._dung_cot` xin cột ATR **vô điều kiện** (có chủ ý),
nên một chiến lược chỉ so `close > open` cũng chết `KeyError`. Cách đúng đơn giản hơn hẳn:
nó **luôn** cần, và `_tham_so_dang_dung` **luôn** tính nó là đang dùng — `core.THAM_SO_NGAM`.

**2. ✅ VÒNG TÌM — ĐÃ CÀI: `cat_studio/tim_kiem.py`, test 21/21**

Dò ngẫu nhiên. **Không phải "thuật toán đã chọn"** — §18.5 vẫn để ngỏ; đây là **đối chứng**
mà mọi cách tìm sau phải thắng. Không thắng nổi nó thì cách ấy chẳng làm gì cả.

```
tim(nen, cd, so_luot, hat, cua, tran, tien_do, dung)  →  KetQuaTim(qua, rot, thong_ke)
```

`hat` cho tái lập · `tien_do` cho cửa sổ RL đọc · `dung()` cho dừng **từ ngoài** (§18.6.2).

##### ⭐ Bốc HAI TẦNG — "đều" trong kho KHÔNG phải "đều" giữa các lựa chọn

Kho nước đi lệch nặng: `vao_lenh` một mình chiếm **1.050/1.863 ô (56 %)**, `het` đúng **1**
ô. Bốc đều từng ô thì mỗi bước là một lần thử đặt lệnh, và "ngẫu nhiên" hoá ra là một thiên
kiến rất mạnh **mà không ai khai**. Nên: chọn LOẠI nước trước (đều giữa mấy loại đang bật),
rồi mới chọn ô trong loại ấy — loại đông nhất tụt từ 20 % xuống 12 %, không núm nào để vặn.

⚠ **Và nó không chỉ làm lệch thống kê.** Bộ đi bừa cũ (bốc đều) gần như không bao giờ đụng
tới `hop_le`, nên **hai lỗ hổng quanh `zone_hop_le` lọt qua 60 sơ đồ mà bài kiểm vẫn xanh**.
*Bộ bốc nào thì tìm ra lỗi nấy* — đó là lý do bài `test_nguoi_bay` nay cũng bốc hai tầng.

##### Bốn ngõ cụt / lỗ hổng nữa, cả bốn đều do vòng tìm phát hiện

| chỗ hỏng | biểu hiện |
|---|---|
| `mo_nhanh` **hai lần liên tiếp** ở cùng chỗ rẽ | cùng một chỗ vào ngăn xếp hai lần ⇒ nhánh ngoài trông RỖNG vĩnh viễn: mở cấm, đóng cấm, đẻ cổng cấm. **80/150 lượt chết** |
| `zone_hop_le` trong `dk_hop_le` | định nghĩa một khái niệm bằng chính nó ⇒ **tràn ngăn xếp**, sập cả lượt tìm |
| `zone_hop_le` khi cổng zone **chưa khai** phần hợp lệ | hỏi một khái niệm chưa ai định nghĩa |
| **`co_zone` toàn cục** thay vì theo VỊ TRÍ | nhánh SONG SONG với cổng zone vẫn tưởng mình có zone — §12.6c đòi khối nằm **sau** cổng zone *trên đồ thị*, không phải "sơ đồ có cổng zone ở đâu đó". **11 lỗi** trên 60 sơ đồ |

⭐ Cái cuối là lỗi *khái niệm*, không phải lỗi cẩu thả: `co_zone`, `co_hop_le` đi theo **vị
trí** nên phải cất vào ngăn xếp lúc `mo_nhanh` và lấy lại lúc `dong_nhanh`. Còn *"chỉ MỘT
cổng zone"* thì ngược lại — **toàn cục**, vì hai cổng ở hai nhánh vẫn là hai cổng. Hai câu
hỏi nghe giống nhau, trả lời bằng hai biến khác nhau.

##### Một lỗi của APP nữa

`Ctx.zone_hop_le` **tràn ngăn xếp** khi `dk_hop_le` hỏi `zone_hop_le`. Soát tĩnh CÓ bắt ca
đó (*"đó là kết quả của chính nó"*) và chú thích ngay đấy còn hứa *"bộ chạy trả NaN"* —
nhưng bộ chạy không trả NaN, nó gọi lại chính mình tới khi Python hết ngăn xếp. Ai gọi
thẳng `bo_chay.chay` là bỏ qua soát tĩnh, nên nay có chốt chặn ngay trong `Ctx`.

##### Số đo đầu tiên của một lượt tìm thật

150 lượt trên 12 tuần nến tổng hợp: **115/150 sơ đồ không vào nổi một lệnh (77 %)** ·
148/150 rớt cửa, phần lớn vì *"tuần có lệnh"* · **2 cái qua**. Đó chính là con số §18.7.4
đặt ra để quyết định ngân sách thật.

**3. ✅ LƯỢT CHẠY — ĐÃ CÀI: `cat_studio/luot_tim.py`, test 35/35**

```
bat_dau(nen, cd, so_luot, …)  →  LuotTim      trả về NGAY, chạy trên luồng nền
  .trang_thai()   ảnh chụp tiến độ, là BẢN SAO
  .dung()         xin dừng — chấm nốt sơ đồ đang dở rồi mới ngừng
  .tom_tat()      nhóm đầu bảng, JSON thuần
  .so_do(hạng)    file chiến lược BÌNH THƯỜNG (§18.6.5)
lay(ma) · danh_sach() · xoa(ma)
```

⭐ **Sổ lượt chạy nằm ở mức MODULE, không nằm trên `Api`.** Đây là cả điểm của món này:
`Api` bị dựng lại mỗi lần mở cửa sổ, module thì sống theo tiến trình. Bài kiểm thử đúng
chuyện ấy — **vứt sạch mọi tham chiếu rồi `gc.collect()`, lượt chạy vẫn còn và vẫn lấy
được kết quả**. Đó là món nợ §14.4 (*"đóng cửa sổ Live là dừng phiên"*) không được mắc lại.

**Hai loại hỏng, hai cách xử — không lẫn:**

| | |
|---|---|
| một SƠ ĐỒ chạy không được (`LoiChay`) | **đếm rồi chạy tiếp** — sơ đồ hỏng, không phải lượt hỏng |
| luồng nền chết (lỗi khác) | tắt cờ, **ghi lý do vào trạng thái**, không có kết quả giả |

Cửa sổ quay mãi thanh tiến trình mà không ai hiểu vì sao là đúng loại hỏng lặng cả app này
cấm — nên `dang_chay` luôn được tắt trong `finally`, và `loi` luôn có mặt.

Kèm mấy chi tiết nhỏ mà thiếu là đau: `trang_thai()` trả **bản sao** (giao diện cầm bản
gốc là cầm thứ luồng nền đang ghi vào) · dừng giữa chừng thì **đánh dấu**, không giả vờ đã
xong · dọn sổ **không bao giờ đụng lượt đang chạy** (dọn nó là mất cách dừng nó, mà luồng
vẫn chạy tiếp — một lượt chạy MA).

⚠ **Một luồng, chưa song song.** Hôm nay là một nhân. §18.4 đo 8 nhân cho ~10.000 sơ đồ
một đêm — nhân lên 8 lần là việc RIÊNG và phải dùng **tiến trình con**, không phải luồng
(`bo_chay` là Python thuần nên GIL chặn). Chưa làm vì chưa chạy thật lần nào.

#### Ba món xong — frontend giờ chỉ còn là BÀY RA thứ đã có

| việc §18.6.2 | dựa vào |
|---|---|
| **ĐẶT** | `kho.TOAN_HANG` · `nguoi_bay.THANG` · `nguoi_bay.TRAN` · `cham_diem.CUA_MAC_DINH` |
| **CHẠY** | `luot_tim.bat_dau` / `.dung()` |
| **NHÌN** | `luot_tim.trang_thai()` · `.tom_tat()` |
| **MỞ** | `luot_tim.so_do(hạng)` → file chiến lược bình thường |

### 18.9 ✅ CỬA SỔ RL — đã dựng

| | |
|---|---|
| Python | `api.ApiRL` — bề mặt hẹp, đúng 8 hàm |
| JS | `webui/src/rl/RL.tsx` · `pyRL` trong `api.ts` · route `?rl=1` |
| vào từ đâu | nút **✦ RL** trên ribbon cửa sổ vẽ |

Bốn việc §18.6.2, mỗi việc một chỗ:

```
ĐẶT    kho (bật/tắt từng toán hạng) · trần · cửa ưu tiên · ngân sách + hạt giống
CHẠY   rl_chay → mã lượt, trả về NGAY;  rl_dung(ma)
NHÌN   rl_trang_thai(ma) mỗi 500 ms — tiến độ · điểm tốt nhất · vì sao rớt
MỞ     rl_mo_so_do(ma, hạng) → bắn `so_do_may` sang cửa sổ vẽ
```

⭐ **`ApiRL` KHÔNG giữ lượt chạy nào.** Sổ ở `luot_tim` (mức module), nên `quen_di` lúc
đóng cửa sổ chỉ quên **cửa sổ** — khác hẳn `mo_live`, nơi đóng cửa sổ = dừng phiên. Mở
lại cửa sổ RL là `rl_boot` thấy lượt cũ vẫn chạy và tự bám vào nó.

⭐ **Sơ đồ máy đẩy sang đi ĐÚNG đường "mở file"**, không có nhánh riêng: `_nhan_so_do_may`
bắn một sự kiện, `App.tsx` gọi `chup()` rồi `nap()` — nên **Ctrl+Z lấy lại được bản đang
vẽ**. Thứ máy đẩy sang không được nuốt mất việc người đang làm.

#### 18.9a ✅ Ô nhìn thứ nhất — ĐƯỜNG ĐIỂM TỐT NHẤT

Trả lời đúng một câu, và là câu thực dụng nhất của cả bàn điều khiển: **"còn tìm được gì
nữa không — dừng được chưa"**. Đường phẳng vài nghìn lượt là tín hiệu tắt máy, khỏi đốt
cả đêm cho phần cuối không tìm thêm được gì.

| | |
|---|---|
| Python | `luot_tim.LuotTim._duong` — `[[đã chấm, điểm], …]` |
| JS | `webui/src/rl/DuongDiem.tsx` |

**Chỉ ghi khi điểm ĐỔI.** Điểm tốt nhất chỉ tăng, nên đây là một hàm **bậc thang** — mọi
điểm giữa hai bậc đều suy ra được. 10.000 lượt thường chỉ đẻ vài chục bậc: vài trăm byte
qua cầu nối thay vì vài trăm KB. Đo trên một lượt thật: **2 bậc cho 6 lượt**.

Ba chi tiết nhỏ mà thiếu là sai:

- **Vẽ bậc thang thật** (`H` rồi `V`), không nối xiên. Nối xiên là vẽ ra một cú cải thiện
  từ từ đã không hề xảy ra — nó nhảy đúng một cái, tại đúng một lượt.
- **Luôn kẻ mốc 0.** Điểm âm là chuyện thường (phần lớn sơ đồ sinh bừa đều lỗ), nên một
  đường đi lên mà không biết đã qua vạch 0 chưa thì đọc ra nghĩa ngược.
- **`trang_thai()` phải chép cả `duong`.** `dict()` sao chép NÔNG — để nguyên là giao diện
  cầm đúng cái list luồng nền đang `append` vào giữa lúc nó đang duyệt.

Và con số đáng nhìn nhất không nằm trên đường mà ở dòng chữ dưới nó: **phẳng bao nhiêu lượt
gần nhất**. Quá 35% cả lượt chạy thì mách thẳng *"dừng được rồi"*.

⚠ **Bài kiểm gọi thẳng `_nhip`, không chạy một lượt tìm thật** — và đó là bài học phải
ghi: lần đầu thử bằng lượt tìm thật thì **37 lượt trên 6 tuần nến mất 15 phút và KHÔNG sơ
đồ nào qua cửa**, nên đường rỗng và bài kiểm chẳng kiểm được gì. Phép ghi đường là một luật
thuần tuý; thử nó bằng backtest thật là vừa chậm vừa phụ thuộc may rủi.

#### 18.9b ✅ Hai panel nói được thứ ta đã xây

Panel *"ưu tiên"* cũ có đúng một dòng công thức khoá cứng và một xấp ô số. Nó **đúng**
nhưng không nói ra được thứ đã có sẵn dưới lõi, nên bàn điều khiển trông như chỉnh được
ít hơn hẳn thứ hệ thống làm được.

**Thưởng·Phạt** — hai vế của điểm hiện thành hai dòng đọc được (§18.2d), nút *nâng vế
nào* hai nấc, và ngay dưới là **con số đã giết nấc thứ ba**. Một chỗ trống ghi *"không
có nấc 2"* mà không nói vì sao thì lần sau lại có người thêm nó vào.

**Dữ liệu** — *cách chia thời gian* (§18.3b) nằm cạnh hai ô đoạn khoá, đúng chỗ nó có
nghĩa. Chọn `cuon_toi` mới hiện nút chọn bước; chọn `mot_khoi` thì câu giải thích đổi
theo, nói thẳng cái mình vừa mất.

⚠ **`manh_deu` KHÔNG được đếm vào nhãn "n phạt" trên mặt nút.** Nó là nút của vế
THƯỞNG; đếm vào đó thì nút nói dối ngay từ ngoài — *"1 phạt"* trong khi chưa lọc gì cả.

#### Ba chỗ dọn được nhờ đợt này

- **`NenChay`** — lớp nền mới, gom *"thiếu nến thì tải"* và *"dựng `CaiDat` từ Cài đặt
  cửa sổ chính"*. `ApiTester` và `ApiRL` cùng dùng. Chép ra hai bản là tester và máy tìm
  chạy trên hai bộ điều kiện khác nhau, và mọi so sánh giữa chúng thành vô nghĩa mà không
  ai thấy. `_chay_that` ngắn đi 20 dòng.
- **`nguoi_bay.mat_na(b, tran, tat)`** — thêm `tat`: khoá toán hạng không dùng lần này.
  Là tầng CHỌN nên nó là **tham số**, không nằm trong `_duoc` (§18.6.1).
- **`_BaoQuaLuot`** — bắc cầu tiến trình TẢI NẾN vào bảng của lượt tìm. Không có nó thì
  suốt lúc tải (có thể hàng phút) thanh tiến trình đứng im và người dùng tưởng treo, vì
  cửa sổ chỉ hỏi `rl_trang_thai(ma)` — thứ nó không hỏi thì nó không thấy.

⚠ Và một chi tiết nhỏ mà đúng nếp cả app: tải xong thì **trả thanh tiến trình về việc
thật** (`da=0, tong=số sơ đồ`) và **xoá câu "đang chuẩn bị nến…"**. Để nguyên thì thanh
nhảy lên 100% rồi bò lại từ 0, và dòng chữ nói dối suốt lượt chạy.

#### Đã đi trọn một vòng thật

`ĐẶT → CHẠY → NHÌN → MỞ` trên XAUUSD 2025-01 → 2025-03, tắt bớt `ma` và `drawdown_pt`:
6 sơ đồ · 3 không vào lệnh nào · 4 rớt cửa (*"tuần có lệnh"*) · **2 qua** · sơ đồ đầu bảng
đẩy sang cửa sổ vẽ và **soát tĩnh 0 vấn đề**.

---

## 13. Việc còn treo

Tester (§12), bộ chạy (§12.13e), đóng gói (§13.1) và Live chế độ quan sát (§14) đều đã
xong và **đo trên dữ liệu thật** — chi tiết nằm ở từng mục, không chép lại thành danh sách
ở đây. Dưới là **thứ chưa có**.

### Live — một việc lớn, và nó chặn phần còn lại

- [ ] **LUỒNG ĐẶT LỆNH.** `gui_lenh` đã có đủ bảy thao tác và có bài kiểm trên sàn giả,
      nhưng **chưa ai gọi nó từ chiến lược**. Ba câu phải chốt trước: **§14.14**.
- [ ] **Phiên sống qua cửa sổ.** Hôm nay đóng cửa sổ Live là dừng phiên (§14.4). `ApiLive`
      đã dựng theo hướng "máy live không sống trong cửa sổ" nên đổi được, nhưng chỉ đáng
      đổi khi có lệnh thật để giữ.
- [ ] **Hiệu chuẩn cho tài khoản THẬT.** Bài kiểm từ chối chạy ngoài demo (§14.8), nên dòng
      `deviation` mãi mãi là **chặn dưới** (§14.9a). Chưa có cách nào đo trượt giá thật mà
      không đặt lệnh thật — có thể là *đo thụ động* trên chính lệnh của chiến lược.

### Thiết kế còn treo (không dính Live)

- [ ] **Chồng lệnh** — D_02: nhiều VỊ THẾ (`Max_Positions`) nhưng đúng MỘT lệnh chờ. Giữa
      hai lần vào lệnh bắt buộc có một đợt ATR bung ra (`CONSUMED` chỉ thoát bằng
      `atr_bps ≥ N`).
- [ ] Có cần `HOẶC` giữa các điều kiện không? *(đang thiết kế: **không** — dùng nhiều nhánh,
      vì "hoặc" giấu trong hộp thoại thì nhìn sơ đồ không thấy)*
