# Cat_Studio — Sổ ghi cốt lõi

> App vẽ pipeline + mô phỏng hành vi chiến lược giao dịch.
> Fork từ **Auto_Clicker** (`C:\Users\Davin\Desktop\Auto_Clicker`), đổi miền từ *click game* sang *trading*, nối MT5 về sau.
>
> File này là **nguồn sự thật về Ý ĐỊNH**. Code là nguồn sự thật về hành vi.
> Sửa cơ chế → sửa file này cùng lúc, đừng để hai bên nói khác nhau.

Cập nhật: 2026-08-10 · Trạng thái: **P0–P4 + kho/lưu trữ/sổ lệnh xong** · test 332/332 · giao diện tester đã chạy thật
Thiết kế **Strategy Tester chốt xong** → §12. Bộ chạy chưa viết một dòng nào.

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
kho/             DANH MỤC mọi thứ app tính được, chia theo NGUỒN
  nen_tang.py      giá · thời gian · tài khoản · lệnh này   (không thuộc engine nào)
  chi_bao.py       ATR · MA · Donchian · Volume MA          (chỉ báo phổ thông)
  engine_d02.py    atr_bps · bảng vùng nén                  (ý tưởng riêng của D_02)
so_lenh.py       bảng `lệnh` + `vùng nén`, id của CHÍNH TA
luu_tru.py       MỘT chỗ duy nhất biết file nằm ở đâu
api.py           bề mặt DUY NHẤT giao diện gọi tới   (JS → api.py → core.py)
app_web.py       khởi động cửa sổ (pywebview + WebView2)
khung_cua_so.py  vá cửa sổ Win32 cho thanh tiêu đề tự vẽ (kéo / giãn / phóng to)
webui/           React + TypeScript + React Flow (@xyflow/react)
```

### Vì sao `kho/` tách khỏi `core.py`

`so_nen_nen` **chỉ có nghĩa khi engine D_02 đang nạp**. Để nó chung một danh sách phẳng
với `close` là nói dối về việc thứ gì luôn có, thứ gì đến từ một chiến lược cụ thể.

- Thêm một chiến lược = thêm **một file** vào `kho/`, không sờ `core.py`.
- Hộp thoại **Kho** (menu File) đọc thẳng `kho.danh_muc()` — không có danh sách nào
  chép tay, nên nó không thể nói khác thực tế.
- **Trùng khoá giữa hai module là lỗi CHẾT NGƯỜI** (hai engine cùng khai `atr` với hai
  nghĩa) → `kho/__init__.py` nổ ngay lúc import, không để nó âm thầm.

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

**Toán hạng của `check_cond`** — 32 cái, 6 nhóm, đủ tái lập Compress EA 100%:

| Nhóm | Toán hạng |
|---|---|
| Giá | `Close[n]`, `Open[n]`, `High[n]`, `Low[n]`, `Bid`, `Ask`, `Spread` |
| Chỉ báo | `ATR(tf, period)`, `MA(tf, period, method)`, `Donchian(tf, period).upper/lower`, `Volume_MA(tf, period)` |
| Chuẩn hoá | `ATR_bps = ATR/Close × 10000`, `X theo bội ATR`, `X theo R` |
| Vùng nén | `số_nến_nén`, `đỉnh_vùng`, `đáy_vùng`, `bề_rộng_vùng÷ATR`, `ATR_TB_vùng`, **`vùng_này_đã_sinh_lệnh`** |
| Tài khoản | `số_vị_thế`, `số_lệnh_chờ`, `số_lệnh_hôm_nay`, `drawdown_%` |
| **Lệnh này** *(chỉ Manage)* | `đã_khớp`, `là_lệnh_Mua`, `SL_đã_ở_hoà_vốn`, `lãi (×R)`, `số_nến_đã_sống`, `giá_vào` |
| Thời gian | `giờ`, `thứ` |

**Phép so dùng KÝ HIỆU, không dùng chữ:**
`<` `≤` `>` `≥` `=` `≠` · `cắt lên ↗` · `cắt xuống ↘` · `trong khoảng`.
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
| `theo_ATR` | × **ATR hiện tại** |
| `theo_ATR_vung` | × **ATR trung bình của vùng nén** |
| `theo_R` | × R (rủi ro) |
| `theo_bien_vung` | mép vùng đối diện |
| `theo_pt` / `theo_gia` | % giá vào / giá tuyệt đối |

> ⚠ **`theo_ATR` và `theo_ATR_vung` là HAI THỨ KHÁC NHAU, tách ra là có chủ ý.**
> Đệm vào lệnh đo bằng ATR *hiện tại* — tấm khiên mỏng ngoài mép vùng, đủ lọc một nhịp
> phá giả. Rủi ro đo bằng ATR *trung bình cả cú nén* — lấy mức nhiễu thật suốt đợt nén,
> nên mỗi lệnh rủi ro một R tương đương bất kể vùng rộng hẹp. Gộp làm một là mất đúng
> cái làm cho 1R nhất quán giữa các tín hiệu.

**Neo lệnh chờ:** lệnh Stop **luôn** neo vào mép vùng nén thuận chiều (đỉnh cho Mua,
đáy cho Bán) — đó là chỗ duy nhất Compress EA đặt lệnh. Nên **không có tham số "neo
vào đâu"**; `dem` chỉ là khoảng đẩy ra ngoài mép đó.

### 6.4 ⭐ BẢNG THAM SỐ — hằng số CÓ TÊN

> **LUẬT DUY NHẤT: ở đâu chờ một con số, một CHUỖI nghĩa là tên tham số.**
> Áp đều cho chu kỳ chỉ báo, khối lượng, ngưỡng so sánh, khoảng cách SL/TP.

Vì sao phải có, đo được bằng con số: sơ đồ mẫu trước khi có bảng tham số có **4 hằng
số bị viết cứng hai lần**, trong đó `7.0` nằm ở **cả hai sơ đồ** — Entry hỏi *"còn nén
không"*, Manage hỏi *"nén tan chưa"*. Sửa một chỗ là chiến lược **vào lệnh theo một
ngưỡng và huỷ lệnh theo ngưỡng khác**, âm thầm.

```jsonc
"tham_so": [
  {"ten": "nguong_nen_bps", "nhan": "Ngưỡng nén", "gia_tri": 7.0, "don_vi": "bps"},
  …
]
// rồi khối chỉ gọi bằng TÊN:
{"trai": {"ten": "atr_bps", "tf": "M5", "period": "chu_ky_atr"},
 "phep": "<", "phai_loai": "tham_so", "phai": "nguong_nen_bps"}
```

**Hiển thị có phân biệt, và đó là chủ ý:**

| Chỗ | Hiện gì | Vì sao |
|---|---|---|
| Vế phải điều kiện · khoảng cách · lot | `nguong_nen_bps = 7` | đây là **núm vặn** — tên nói ý nghĩa, số nói thực tế |
| Tham số của toán hạng (chu kỳ, nến) | `ATR(M5, 14)` | đây là **"đọc chuỗi số nào"**, không phải thứ người ta tinh chỉnh |

Soát tự động bắt hai chuyện: tham chiếu tới tham số **không tồn tại** → lỗi; tham số
khai ra mà **không khối nào dùng** → cảnh báo (sửa nó sẽ không đổi gì cả).

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
  **Ta không chép** — xem §12.6a.

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
`Ctrl+S` lưu · **`Ctrl+G` ghim số** · `Delete` xoá · `F2` đổi tên.
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
    { "trai": {"ten": "atr_bps", "tf": "M5", "period": "chu_ky_atr"},
      "phep": "<", "phai_loai": "tham_so", "phai": "nguong_nen_bps" }
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
| **P5 · Tester** | Cửa sổ Strategy Tester — thiết kế đầy đủ ở **§12** | 🔨 **thiết kế chốt xong**, khung có 3 lỗi phải sửa (§12.12) |
| **P7 · Bộ chạy** | `nguon_nen` → `tinh_toan` → `khop_lenh` → `bo_chay`. Nối MT5, kéo nến M1, backtest thật | ⬜ *(đang tới)* |

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

1. **Toán hạng đang dùng** — suy từ chính `doc`, khoá theo `(tên + tf + period)` nên ATR(M5,14)
   và ATR(M5,42) là hai dòng riêng. Toán hạng chưa được đọc trong lượt đó hiện **dấu gạch**, không hiện 0.
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
(~51 giờ)**, và bốn cái dài nhất đều là cuối tuần. Đây chính là bằng chứng cụ thể cho §12.6b:
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

### 12.22 ✅ Ba lối vào tester, một hàm

`▶ Chạy` trên ribbon · `File → Mở Strategy Tester` · phím `Ctrl+R`. Cả ba trỏ về **đúng một hàm**
`chay()` — cùng luật với 4 menu tiêu đề (§8): không tạo hành động mới nào cho một lối vào mới, nếu
không hai nơi sớm muộn cũng lệch nhau.

`ContextMenu` nhận thêm trường `phim` để hiện nhãn phím tắt mờ, dạt phải. Nó CHỈ là nhãn — phím
thật vẫn do chỗ nghe bàn phím lo, menu không tự gắn phím nào.

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

## 13. Việc còn treo

Thiết kế Strategy Tester đã chốt hết ở §12. Còn lại là **việc làm**, theo đúng thứ tự:

- [x] ~~Sửa 3 lỗi có sẵn của cửa sổ tester (§12.12)~~ — xong, đã đo bằng chuột thật
- [x] ~~`nhip` thay `timeframe`~~ — xong, schema 4, di cư file cũ tự động
- [x] ~~Sửa mô tả ATR trong `kho/chi_bao.py`~~ — xong, và bộ TÍNH cũng đã có (`tinh_toan.atr`)
- [x] ~~Lỗi soát khi hai đầu nhánh lệch dưới 8 px~~ — xong, `core.LECH_TOI_THIEU`
- [x] ~~Cập nhật `test_doi_chieu_d02.py`~~ — giờ **9 chỗ cố ý khác**, mỗi chỗ gắn nhãn có
      ĐỔI SỐ hay không (`SỐ LỆNH` · `GIÁ & P&L` · `không`); 4 chỗ đổi số
- [x] ~~`nguon_nen.py`~~ — xong, đã tải thật 30k nến XAUUSD; 22 bài kiểm không cần MT5
- [x] ~~`tinh_toan.py`~~ — xong. **Gộp M1→M5/M15/H1 trùng khít MT5 tới từng chữ số** trên
      một tháng dữ liệu thật (5.994 nến M5 · 1.999 M15 · 501 H1, lệch OHLC = 0)
- [x] ~~`khop_lenh.py`~~ — xong, 30 bài kiểm từng ca tính tay được
- [x] ~~`bo_chay.py`~~ — xong: biên dịch, vòng lặp M1, Manage/Entry theo nhịp, nhật ký
- [x] ~~**Đo tốc độ trên 1 năm thật**~~ — **2,9 s** cho 354.503 nến M1 (§12.13e)
- [x] ~~`nhat_ky.py`~~ — xong: dựng 200 dòng mất **0,6 ms**, ghi 8.020 lượt ra 3,3 MB
- [x] ~~Giao diện tester: chart Canvas · bảng 4 khối · nhật ký ảo hoá~~ — xong, đã chạy
      backtest thật trong cửa sổ và đối chiếu bảng ↔ nhật ký (§12.15)

Chưa liên quan tới tester:

- [ ] **Chồng lệnh** — D_02: nhiều VỊ THẾ (`Max_Positions`) nhưng đúng MỘT lệnh chờ. Giữa hai lần vào lệnh bắt buộc có một đợt ATR bung ra (`CONSUMED` chỉ thoát bằng `atr_bps ≥ N`).
- [ ] Có cần `HOẶC` giữa các điều kiện không? *(đang thiết kế: **không** — dùng nhiều nhánh, vì "hoặc" giấu trong hộp thoại thì nhìn sơ đồ không thấy)*
- [ ] Đóng gói `.exe` (PyInstaller) — chưa làm spec.
