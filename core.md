# Cat_Studio — Sổ ghi cốt lõi

> App vẽ pipeline + mô phỏng hành vi chiến lược giao dịch.
> Fork từ **Auto_Clicker** (`C:\Users\Davin\Desktop\Auto_Clicker`), đổi miền từ *click game* sang *trading*, nối MT5 về sau.
>
> File này là **nguồn sự thật về Ý ĐỊNH**. Code là nguồn sự thật về hành vi.
> Sửa cơ chế → sửa file này cùng lúc, đừng để hai bên nói khác nhau.

Cập nhật: 2026-08-10 · Trạng thái: **P0–P4 xong, app chạy được** · test 61/61

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
core.py          lõi — không phụ thuộc giao diện, chạy headless được, test không cần mở cửa sổ
api.py           bề mặt DUY NHẤT giao diện gọi tới   (JS → api.py → core.py)
app_web.py       khởi động cửa sổ (pywebview + WebView2)
khung_cua_so.py  vá cửa sổ Win32 cho thanh tiêu đề tự vẽ (kéo / giãn / phóng to)
webui/           React + TypeScript + React Flow (@xyflow/react)
```

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
3. **Vòng theo dõi** được miễn cảnh báo *"nhánh nào cũng có điều kiện"*: không cổng nào
   khớp thì nó chờ nến sau — đó chính là việc của một vòng theo dõi, không phải lỗi.
   Cùng lý do, một Vòng theo dõi **rỗng** mà có ≥2 nhánh là mẫu *"chờ tới khi"* hợp lệ,
   không báo "chưa có hành động nào".

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
- Mở **cửa sổ pywebview thứ hai** (chi tiết bàn sau).
- Bộ khung dựng trước: cửa sổ + `api.mo_tester(doc)` + kênh sự kiện `window.__su_kien("test", …)`
  dùng lại đúng cơ chế gom lô 150 ms.

---

## 5. Luật rẽ nhánh (kế thừa nguyên vẹn)

Một khối có **nhiều đường ra** thì phải quyết định được đi đường nào:

1. Các nhánh được **thử lần lượt từ TRÊN xuống DƯỚI** (theo vị trí canvas).
2. Mỗi nhánh phải mở đầu bằng một **CỔNG** = khối *HĐ lẻ* mang đúng **một** hành động `check_cond`.
3. Nhiều nhất **MỘT** nhánh được để trống làm **nhánh mặc định** — và nó **bắt buộc xếp cuối cùng**
   (nhánh mặc định luôn khớp, xếp trên thì các nhánh dưới không bao giờ chạy tới).
4. Hai cổng cùng điều kiện y hệt → cảnh báo (cái dưới không bao giờ tới lượt).

**Vì sao chỉ HĐ lẻ được làm cổng:** ở điểm rẽ các nhánh thử lần lượt, nên nhánh trượt phải **lùi lại được**.
Một khối `check_cond` chỉ **đọc** dữ liệu thị trường nên lùi bao nhiêu lần cũng vô hại.
Một *Nhóm* thì không hứa được điều đó — nó có thể **đã đặt lệnh** rồi mới kiểm tra, và lệnh đó không rút lại được.

**Ngữ nghĩa ngược nhau — nhớ kỹ:**

| | Khớp | Không khớp |
|---|---|---|
| `check_cond` làm **cổng** | đi tiếp nhánh này | **chết nhánh** này, thử nhánh dưới |
| Khối **mục tiêu** (goal) | **kết thúc sớm** cả vòng | chạy tiếp |

---

## 6. Bộ khối & hành động của Cat_Studio

### 6.1 Ba LOẠI KHỐI (`kind`) — ánh xạ 1-1 từ Auto_Clicker

| Auto_Clicker | Cat_Studio | Nghĩa |
|---|---|---|
| `loop` — Action_Loop | `loop` — **Vòng theo dõi** | Lặp lại theo **mỗi nến mới**, tối đa N nến, kết thúc sớm khi khối mục tiêu khớp. Đây là chỗ mô hình hoá "chờ nén đủ K nến". |
| `group` — Nhóm HĐ 1 lần | `group` — **Nhóm 1 lần** | Vài hành động chạy đúng một lượt |
| `action` — HĐ lẻ | `action` — **HĐ lẻ** | Đúng một hành động. **Chỉ loại này được làm cổng.** |
| — | `start` — **Bắt đầu** 🆕 | Điểm neo đánh số (§4.2) |

### 6.2 BA HÀNH ĐỘNG — đọc · tạo · sửa

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
| `kích hoạt` (chờ khớp) | **loại khối** `Vòng theo dõi` — lặp mỗi nến tới khi thoả hoặc hết N nến |
| `vào` | **Vào lệnh** |
| `thoát` | chế độ `đóng hẳn` / `huỷ lệnh chờ` của **Sửa lệnh** |

**Để dành (ẩn):** `dat_co` — **Đặt cờ**. Bật/tắt một cờ có tên, đọc lại bằng toán hạng
`Cờ`. Đây là cơ chế tổng quát để chốt "tín hiệu này dùng rồi, khỏi dùng lại"
(= `COMP_CONSUMED` của EA). Lõi hiểu đủ, chỉ bị lọc khỏi bảng chọn bằng
`core.HANH_DONG_AN` — mở lại là bỏ **một chuỗi** khỏi tập đó.

**Toán hạng của `check_cond`** — 30 cái, 6 nhóm, đủ tái lập Compress EA 100%:

| Nhóm | Toán hạng |
|---|---|
| Giá | `Close[n]`, `Open[n]`, `High[n]`, `Low[n]`, `Bid`, `Ask`, `Spread` |
| Chỉ báo | `ATR(tf, period)`, `MA(tf, period, method)`, `Donchian(tf, period).upper/lower`, `Volume_MA(tf, period)` |
| Chuẩn hoá | `ATR_bps = ATR/Close × 10000`, `X theo bội ATR`, `X theo R` |
| Trạng thái vùng | `số_nến_nén`, `đỉnh_vùng`, `đáy_vùng`, `bề_rộng_vùng`, `bề_rộng_vùng/ATR`, `ATR_trung_bình_vùng` |
| Trạng thái | `đang_có_vị_thế`, `đang_có_lệnh_chờ`, `lệnh_chờ_vừa_khớp`, `cờ(tên)` |
| Tài khoản | `số_lệnh_đang_mở`, `lãi_lỗ_hiện_tại_theo_R`, `drawdown_%`, `số_lệnh_hôm_nay` |
| Thời gian | `giờ`, `thứ`, `nến_mới(tf)` |
| Phép so | `<` `<=` `>` `>=` `==` `!=` · `cắt lên` · `cắt xuống` · `trong khoảng` |

Toán hạng vốn đã **đúng/sai** (`đang_có_vị_thế`, `cờ`…) không có vế phải — hộp thoại
đổi sang một ô tick **KHÔNG**. *"Đang có vị thế bằng 1"* là câu không ai đọc được.

**Mọi khoảng cách giá** (SL, TP, đệm vào lệnh, mốc hoà vốn) dùng chung một kiểu
`{tinh, value}` với `tinh` ∈ `theo_ATR · theo_R · theo_biên_vùng · theo_% · theo_giá`.
**Không có đơn vị pip hay đô** — đúng hợp đồng chuẩn hoá của Compress EA (§7.1).

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
| **Thêm khối** | Loop · Nhóm · HĐ lẻ · Rẽ nhánh · Delay | **Kiểm tra ĐK** · **Vào lệnh** · **Sửa lệnh** · Vòng theo dõi · Nhóm |
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
| **Nền** | Dán · ─ · Thêm Kiểm tra ĐK / Vào lệnh / Sửa lệnh · ─ · Thêm Vòng theo dõi / Nhóm |
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
  "schema": 1,
  "type": "strategy",
  "name": "Compress",
  "symbol": "XAUUSD",          // 🆕
  "timeframe": "M5",           // 🆕
  "steps": [
    { "kind": "start",  "id": "s…", "pos": [80, 300] },                       // 🆕
    { "kind": "action", "id": "s…", "type": "check_cond", "pos": [400, 120],
      "ghim": true,                                                           // 🆕
      "conditions": [
        { "trai": { "ten": "atr_bps", "tf": "M5", "period": 14 },
          "phep": "<", "phai_loai": "so", "phai": 7.0 }
      ] },
    { "kind": "action", "id": "s…", "type": "vao_lenh", "huong": "mua",
      "loai": "stop", "lot": 0.01,
      "dem": { "tinh": "theo_ATR", "value": 0.1 },
      "sl":  { "tinh": "theo_ATR", "value": 1.5 },
      "tp":  { "tinh": "theo_R",   "value": 2 } },
    { "kind": "action", "id": "s…", "type": "sua_lenh", "che_do": "hoa_von",
      "muc_tieu": "vi_the", "khoang": { "tinh": "theo_R", "value": 1 } },
    { "kind": "loop",   "id": "s…", "name": "Chờ khớp", "actions": [],
      "loop_start_index": 0, "max_nen": 200, "tf": "M5" }
  ],
  "edges": [
    { "from": "s…", "to": "s…", "port": "out", "from_side": "right", "to_side": "left" }
  ]
}
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
| Cần thêm | `pywebview` (**cài trong `.venv` riêng** — gói `quantconnect-stubs` global chiếm namespace `Microsoft` và giết pywebview lúc khởi động) |
| **Bỏ** so với Auto_Clicker | `pyautogui`, `keyboard`, `pyperclip`, `pillow`, toàn bộ `winrt-*` (OCR), `overlay_ui.py`, `overlays.py`, `update_mods.py`, `data/mods_*.txt` |
| Máy | Windows 10 Pro 19045 — cần .NET ≥ 4.7.2 và WebView2 Runtime |

---

## 11. Kế hoạch

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| **P0 · Khung** | Fork Auto_Clicker → Cat_studio, gỡ sạch phần game/OCR/overlay. Đổi logo + tiêu đề. | ✅ `python app_web.py` mở cửa sổ Cat Studio |
| **P1 · Đồ thị** | `core.py`: khối/cạnh, `flow_map`, `flow_order`, `diem_gop`, soát lỗi — kèm sửa Bẫy 1, 3, 4 | ✅ 41/41 test |
| **P2 · Số 🆕** | Khối `start` + cờ `ghim` + cạnh quay lại + huy hiệu ⟲ + menu chuột phải + `Ctrl+G` | ✅ vẽ vòng lặp không còn cảnh báo sai |
| **P3 · Hành động** | 3 hành động + `dat_co` ẩn. 30 toán hạng, 9 phép so, 7 chế độ Sửa lệnh. `ActionDialog`. | ✅ |
| **P4 · Canvas** | React Flow, ribbon, undo 60 bước, template, chép/dán, phím tắt | ✅ |
| **P5 · Tester** | Cửa sổ Strategy Tester — **mới có bộ khung**: `api.mo_tester` chặn lỗi rồi mở cửa sổ thứ hai, `api.tester_doc` để cửa sổ đó hỏi sơ đồ | 🔨 khung xong, nội dung **bàn sau** |
| **P6 · Mẫu** | Sơ đồ mẫu Compress EA, khớp §7 | ✅ 12 khối, 15 cạnh, 3 vòng đã ghim, **soát sạch** |
| **P7 · MT5** | Nối `MetaTrader5`, kéo nến, tính chỉ báo, backtest thật | ⬜ *(sau)* |

### Sơ đồ mẫu ra đúng thế này

```
[1] Bắt đầu
[2] Nến này có nén không?          ⟲ đã ghim          ←────────┐
[3] Đủ K nến & vùng vừa khổ?  ─┬─ [3A]  Xu hướng LÊN  → [3A.1] Buy Stop
                               ├─ [3B]  Xu hướng XUỐNG → [3B.1] Sell Stop
                               └─ ⟲ không hướng nào hợp ───────┤
[4] Chờ khớp / chờ vùng tan   ─┬─ [4A]  Lệnh đã khớp?  → [4A.1] Hoà vốn ─┤
                               └─ [4B]  Vùng đã tan?   → [4B.1] Huỷ chờ ─┘
```

---

## 12. Việc còn treo

- [ ] **Strategy Tester hiển thị gì** — bảng lệnh, đường equity, log từng bước, hay biểu đồ nến? *(bàn sau)*
- [ ] Bộ chạy: duyệt đồ thị theo nến, đánh giá `check_cond`, ghi log kèm nhãn `[3A.1]` — chưa viết.
- [ ] Nối MT5: `copy_rates_from_pos`, `iATR`/`iMA` tính bằng Python hay gọi terminal?
- [ ] Có cần `HOẶC` giữa các điều kiện không? *(đang thiết kế: **không** — dùng nhiều nhánh, vì "hoặc" giấu trong hộp thoại thì nhìn sơ đồ không thấy)*
- [ ] Mở `dat_co` (Đặt cờ) ra khi nào — nó là cách chốt `COMP_CONSUMED`.
- [ ] Đóng gói `.exe` (PyInstaller) — chưa làm spec.
