# Sổ tay giữ sạch — đọc trước khi sửa bất cứ thứ gì

> `core.md` trả lời **VÌ SAO** mọi thứ như vậy. File này trả lời **LÀM THẾ NÀO** để thêm
> đồ mà không làm rối. Ngắn có chủ ý: dài quá thì không ai đọc, mà không đọc thì vô dụng.

---

## 0. Ba lệnh, thuộc lòng

```bat
tools\chay_test.bat      :: 14 bài kiểm — "có hỏng không"
tools\van_tay.bat        :: vân tay hành vi — "có ĐỔI gì không"
tools\soi_rac.bat        :: soi rác — "có thứ gì chết / nói dối không"
```

**Trước khi sửa:** chạy `van_tay` một lần cho chắc nó đang xanh.
**Sau khi sửa:** chạy cả ba. Thêm `tools\build_ui.bat` nếu có động vào `webui/`.

Hai câu hỏi khác nhau, và chỗ này hay bị lẫn:

| | trả lời câu |
|---|---|
| `chay_test` | *"tôi có làm hỏng cái gì không?"* |
| `van_tay` | *"tôi có ĐỔI cái gì không?"* |

Một đợt **dọn dẹp** phải xanh cả hai. Một đợt **đổi hành vi** thì `van_tay` LỆCH là đúng —
xem nó liệt kê mục nào đổi, đối chiếu với thứ mình vừa làm, rồi `tools\van_tay.bat --chot`.

⚠ **Đừng bao giờ `--chot` mà chưa đọc phần nó in ra.** Chốt bừa là xoá mất cái lưới duy
nhất bắt được lỗi âm thầm.

---

## 1. Tôi muốn thêm… thì sửa file nào

Đây là phần đáng giá nhất của cả file. Con số trong ngoặc là **số nơi phải sửa** — càng
nhỏ càng tốt, và nếu bạn thấy nó phình lên thì đó là dấu hiệu cần dọn lại kiến trúc.

### Thêm một TOÁN HẠNG (1–3 nơi)

1. `cat_studio/kho/<module>.py` — thêm một mục vào `TOAN_HANG`, khai đủ
   `key · nhan · nhom · loai` và (nếu `loai == "dem"`) `don_vi`, `tabs`, `dung_sai`,
   `can_zone`.
2. `cat_studio/bo_chay.py::_lay_toan_hang` — trả giá trị lúc chạy.
3. *Chỉ khi cần một cột tính trước:* `tinh_toan.BANG` + `ChuongTrinh._dung_cot`.

**Hết.** Dropdown, hộp thoại Kho, soát tĩnh, bảng số liệu, danh sách `CAN_ZONE` — tất cả
tự gom từ `kho/`. Nếu bạn thấy mình phải sửa chỗ thứ tư, **dừng lại**: chỗ đó đang giữ
một bản chép tay của kho, và nó là bug chờ ngày nổ.

### Thêm một ĐƠN VỊ (2 nơi, nhưng nơi thứ hai có BA hàm)

1. `core.DON_VI` + `DON_VI_NGAN` + `DON_VI_CHO` (ô nào được chọn nó).
2. `bo_chay` — **cả ba**: `_quy_doi` (một nến, cho cổng) · `quy_doi_cot` (cả lô, cho bảng
   số liệu) · `_khoang` (SL/TP/đệm).

⚠ **Ba hàm đó phải sửa CÙNG LÚC.** Lệch nhau thì bảng hiện một số, nhật ký hiện số khác,
đúng lúc đang debug. Chú thích ở `quy_doi_cot` đã ghi sẵn cảnh báo này.
⚠ Nếu đơn vị cần một mẫu số tính trước, `_dung_cot` phải xin cột **vô điều kiện** — nó có
thể bị hỏi từ điều kiện, `dk_hop_le`, SL, TP, đệm, hoặc ô khoảng của Sửa lệnh. Quét đủ sáu
chỗ để tiết kiệm một cột là đổi một khoản rẻ lấy một chỗ chắc chắn có ngày bỏ sót.

### Thêm một LUẬT ĐỒ THỊ (2 nơi, cả hai một dòng — **rồi nơi thứ ba**)

1. Viết hàm `_lt_<tên>(b)` trong `core.py`, dùng `b.ten()` · `b.loi()` · `b.nga_re()` ·
   `b.cap()` · `b.truoc`.
2. Thêm **một dòng** vào `LUAT_DO_THI`.

Không luật nào biết luật nào. Xoá một luật không gãy luật khác. Thứ tự chỉ đổi thứ tự
dòng lỗi hiện ra, không đổi kết quả.

3. ⚠ **`nguoi_bay._duoc` phải biết luật đó.** Người soát nói "sai rồi", người bày nói
   "đừng đi nước ấy" — cùng một tri thức, hai hình dạng. Lệch nhau thì máy tìm đốt 17
   giây backtest cho một sơ đồ hỏng, và đốt đều đặn. Đo được: viết người bày lần đầu
   mà quên bảy luật ⇒ sinh bừa 60 sơ đồ ra **910 lỗi**.

`tests/test_nguoi_bay.py` canh đúng chuyện này: sinh 60 sơ đồ ngẫu nhiên, đòi soát tĩnh
trả về **0 lỗi 0 cảnh báo**. Thêm luật mà quên bước 3 là bài đó đỏ ngay.

### Thêm/sửa một NƯỚC ĐI của người bày

1. `nguoi_bay.KHO_NUOC_DI` — sinh từ `kho.TOAN_HANG` × `THANG`, **đừng gõ tay danh sách**.
2. `Ban.di` — nước đó làm gì.
3. `_duoc` — lúc nào được đi.
4. `_Doc.khoi` / `_Doc.dieu_kien` — **chiều ngược** cũng phải đẻ ra nó.

⚠ Quên bước 4 thì `doc_nguoc` nổ `KhongDocDuoc` khi gặp sơ đồ có thứ ấy — to tiếng, không
im lặng, nhưng vẫn là quên.
⚠ Đổi `THANG` hay `KHO_NUOC_DI` là **một mạng đã học phải học lại**. Vân tay canh chỗ này.

### Thêm một CHẾ ĐỘ SỬA LỆNH (3 nơi)

1. `core.SUA_CHE_DO` (nhãn) + `SUA_GHI_LEN` (**nó ghi lên thứ gì của lệnh**) +
   `SUA_CAN_GIA` (có cần ô khoảng không).
2. `bo_chay._sua_lenh` — nhánh xử lý.
3. Nếu nó ghi SL: **phải đi qua `_sl_moi`** (đúng phía · đủ xa · chỉ siết). Đừng gán thẳng.

⚠ Quên `SUA_GHI_LEN` thì luật §17.2/§17.3 mù với chế độ mới — sơ đồ vẫn vẽ được hai khối
giẫm lên nhau mà không ai báo.

### Thêm một MỐC NEO — **không phải làm gì cả**

`MOC_ENTRY` sinh từ kho: mọi toán hạng `loai == "muc_gia"` mà tham số ⊆ `{tf}`. Thêm một
toán hạng mức giá là mốc neo có ngay, ở cả khối Vào lệnh lẫn Sửa lệnh.

### Thêm một SYMBOL — **không phải sửa mã**

Tải nến symbol đó từ MT5 là xong: `point` · `contract_size` · `digits` · `spread_tb` được
cất cạnh kho nến. Thiếu thứ nào thì app **nổ kèm lời giải thích**, không đoán —
`api._thong_so` (§16.3) và `api._spread` (§16.2).

⚠ Một thứ **chưa ai bắt**: mật độ nến M1 thật. Meta kho nến có thể ghi 2016→2026 trong khi
M1 thật chỉ từ giữa 2021. Tự soi: `số nến ÷ số ngày` phải ≈ 1.130 *(§15.0)*.

### Thêm một CỬA SỔ (4 nơi)

1. `api.py` — lớp `ApiXxx(NenCuaSo)` *(hoặc `NenChay` nếu cửa sổ đó CHẠY trên dữ liệu)*,
   `_HAU_TO` riêng, bề mặt **hẹp**.
2. `api.Api.mo_xxx` — `create_window(url=…?xxx=1, js_api=<ApiXxx>)`, rồi
   `events.closed += quen_di` và một luồng `_va_khung("— Xxx")`.
3. `webui/src/main.tsx` — thêm một dòng `?xxx=1`. **Đừng** thêm entry cho Vite.
4. `webui/src/api.ts` — một `pyXxx` riêng. Gọi nhầm `py.*` ở cửa sổ đó sẽ trả *"api.py
   không có hàm …"* chứ không âm thầm đụng cửa sổ chính.

⚠ `js_api=` phải là **thể hiện riêng**, không phải `self` — xem `NenCuaSo`, ba lỗi đã có
thật (bấm ✕ ở cửa sổ con đóng cửa sổ chính…).
⚠ Quyết định **đóng cửa sổ = dừng hay không**. Live thì DỪNG; RL thì KHÔNG (sổ ở
`luot_tim`, mức module). Chọn sai là món nợ §14.4.

### Thêm một ô CÀI ĐẶT

1. `luu_tru.CAI_DAT_MAC_DINH["test"]`
2. `api.save_test_settings` — danh sách trắng
3. `api` — chỗ dựng `CaiDat`
4. `bo_chay.CaiDat` — **và phải có chỗ ĐỌC nó**
5. `SettingsDialog.tsx`
6. `lich_su._cai_dat` — **nếu nó đổi được kết quả**

⚠ Bước 4 và 6 là chỗ hay quên, và cả hai đều hỏng im lặng. `don_bay` từng đi qua bước
1·2·3·5 mà **không ai đọc** — một ô hứa suông suốt nhiều tháng. Thiếu bước 6 thì hai lần
chạy khác nhau bị lịch sử ghi là một, và "so với lần trước" nói dối.

---

## 2. Bất biến — phá cái nào là hỏng cả hệ

| | |
|---|---|
| **Không hỏng im lặng** | Thà nổ to còn hơn chạy ra số sai. Không `except: pass`, không mặc định che dữ liệu thiếu. |
| **Một nguồn sự thật** | Hai danh sách phải đồng bộ tay = bug chờ ngày nổ. Gom tại nguồn, đừng chép. |
| **Python sinh chữ, JS chỉ hiển thị** | `core.action_display` là nơi duy nhất dựng câu. JS tự dựng là hai bên sớm muộn nói khác nhau. |
| **Chỉ bày ra thứ dùng được** | Bày một lựa chọn vô nghĩa rồi soát tĩnh mắng còn tệ hơn không bày. |
| **Sơ đồ không được nói dối** | Vẽ ba việc thì lượt chạy phải làm ba việc. |
| **Cái thước không được là tham số** | Ngưỡng thì chỉnh được; thứ dùng để ĐO thì không. |
| **Test như nào thì live như thế** | Backtest phải chơi theo đúng luật sàn mà live đã đo. |
| **Không đổi nửa vời** | Không quy đổi được thì để soát tĩnh NÓI TO, đừng đoán. Một phép đổi đúng-một-nửa là loại hỏng tệ nhất: file vẫn chạy, chỉ sai. |

---

## 3. Bẫy đã cắn thật — đừng đạp lại

- **Thứ phải sống lâu hơn cửa sổ thì đừng giữ trên `Api`.** `Api` dựng lại mỗi lần mở cửa
  sổ. Sổ lượt tìm nằm ở **mức module** vì thế — và phép kiểm là *vứt sạch tham chiếu rồi
  `gc.collect()`, nó vẫn phải còn*. Đây là món nợ §14.4 (*"đóng cửa sổ Live là dừng
  phiên"*) không được mắc lại. *(§18.8)*
- **Một SƠ ĐỒ hỏng ≠ một LƯỢT CHẠY hỏng.** `LoiChay` thì đếm rồi chạy tiếp; lỗi khác thì
  tắt cờ và ghi lý do. Lẫn hai thứ: hoặc một sơ đồ rác giết cả đêm chạy, hoặc luồng nền
  chết im lặng và thanh tiến trình quay mãi. *(§18.8)*
- **"Bốc đều" trong một danh sách LỆCH là một thiên kiến không ai khai.** `vao_lenh` chiếm
  56 % kho nước đi, `het` chiếm 1 ô — bốc đều từng ô thì mỗi bước là một lần thử đặt lệnh.
  Bốc HAI TẦNG (loại trước, ô sau). Và nó không chỉ làm lệch thống kê: bộ bốc cũ không bao
  giờ đụng `hop_le`, nên hai lỗ hổng lọt qua 60 sơ đồ mà bài kiểm vẫn xanh. **Bộ bốc nào
  thì tìm ra lỗi nấy.** *(§18.8)*
- **"Có zone chưa" và "chỉ được MỘT zone" là HAI câu hỏi, hai biến.** Cái đầu theo **vị
  trí** (cất vào ngăn xếp lúc rẽ nhánh — nhánh song song không thừa hưởng), cái sau **toàn
  cục** (hai cổng ở hai nhánh vẫn là hai cổng). Nghe giống nhau, trả lời khác nhau. *(§18.8)*
- **Một luật cấm ĐÚNG ở từng bước vẫn dồn người đi vào chỗ chết.** Người bày phải trả lời
  được *"đi nước này rồi còn về đích được không"*, không chỉ *"nước này hợp lệ không"* —
  nên nước đẻ CỔNG phải chừa sẵn một suất khối cho hành động đóng nó. *(§18.7.4)*
- **Toạ độ khối là một phần của NGHĨA, không phải trang trí.** `_khoa_nhanh` đọc `pos` để
  biết nhánh nào được thử trước. Sơ đồ sinh tự động mà không đặt `pos` thì **mọi ngã rẽ
  đều là lỗi**. *(§18.7.4)*
- **Hai bên đòi ngược nhau thì không ai đúng.** `chu_ky_atr` từng bị bộ chạy đòi vô điều
  kiện còn soát tĩnh mắng là thừa — không cách nào làm vừa lòng cả hai. Gom về **một** chỗ
  trả lời (`core.can_tham_so_ngam`). *(§18.7.4, §16.3)*
- **Chuẩn hoá theo biến động sụp khi biến động = 0.** Mọi tỉ số hoá `0/0` hoặc luôn đúng.
  Cần một cái mốc **không co lại được** — và cái duy nhất như vậy là chi phí giao dịch.
  *(§15.13b)*
- **`normalize` vứt giá trị lạ là giết luôn cơ hội báo lỗi.** Giữ lại rồi để validator nói.
  `atr < 7 [bps]` bị vứt `bps` thành `atr < 7` — vẫn chạy, chỉ là một chiến lược khác hẳn.
  *(§13.0d · §15.7)*
- **Kho nến nói dối về chính nó.** Meta ghi 2016→2026 nhưng M1 thật chỉ từ giữa 2021.
  Soi mật độ trước khi đo bất cứ thứ gì: `số nến ÷ số ngày` phải ≈ 1.130. *(§15.0)*
- **Lot cố định giấu mọi thứ.** Phí, sụt vốn, rủi ro thật — tất cả vô hình cho tới khi
  chuyển sang rủi ro % vốn. *(§15.13)*
- **Một MẶC ĐỊNH trông đúng khiến chỗ QUÊN không bao giờ lộ ra.** `api` từng dự phòng
  `point=0.01 · digits=2` — trông y như XAUUSD mà sai (thật là `0.001 · 3`), nên không ai
  soi; `van_tay` thì quên hẳn `contract_size` và vẫn xanh suốt vì mặc định tình cờ đúng.
  Vì thế mặc định `CaiDat` nay là **số giả** (`point=1 · contract_size=1 · spread=0`): sai
  mà trông giả thì nhìn phát biết. *(§16.3)*
- **`bool(NaN)` là `True`.** "Chưa có số" đọc thành ĐÚNG. *(§12.6g)*
- **Fixture trong test dùng tên đã chết vẫn chạy** nhờ bảng di cư — rồi ngày bỏ bảng di cư
  là cả bài kiểm sập mà không ai hiểu vì sao.

---

## 4. Khi `soi_rac` kêu

Nó đưa **nghi can**, không đưa bản án. Mỗi cái phải tự mở ra xem. Ba loại báo động giả đã
biết, đã dạy cho nó, nhưng vẫn nên nhớ:

- **Bia mộ** — chú thích nói *"`X` ĐÃ BỎ vì…"* là tài sản, không phải rác. Xoá nó là xoá
  mất lý do, và ba tháng nữa có người thêm lại.
- **Bảng di cư** — `DON_VI_CU`, `SUA_CHE_DO_CU`, `MOC_CU`, `THANH_DON_VI`, `DON_VI_DA_BO`
  cố ý giữ tên đã chết để mở file cũ không hỏng im lặng.
- **Biến CSS đặt từ JS** — `StepNode` đặt `--mau-khoi` inline, `Chart` đọc biến qua
  `mau('--x')`. Không phải `var()` nào cũng nằm trong `.css`.

---

## 5. Bản đồ nhanh

```
cat_studio/
  core.py          hằng số · đồ thị & đánh số · chuẩn hoá · soát lỗi · chữ hiện ra
                   └─ LUAT_DO_THI: mỗi luật một hàm `_lt_*`, thêm luật = thêm một dòng
  nguoi_bay.py     §17 nhìn NGƯỢC: sơ đồ dở → nước đi hợp lệ, và sơ đồ → chuỗi nước đi
                   └─ KHO_NUOC_DI cố định + mat_na() thay đổi. Chỗ mọi máy tìm cắm vào.
  cham_diem.py     §18.2: chuỗi lãi/lỗ theo TUẦN → trung bình ÷ dao động, + mấy cái CỬA
                   └─ chấm bằng TIỀN. `tong_R` mù hoa hồng nên không dùng để chấm.
  tim_kiem.py      dò NGẪU NHIÊN — đối chứng mà mọi cách tìm sau phải thắng
                   └─ bốc HAI TẦNG (loại trước, ô sau) · tái lập bằng hạt giống
  luot_tim.py      vòng đời một lượt tìm: bắt đầu · dừng · tiến độ · kết quả
                   └─ SỔ Ở MỨC MODULE — lượt chạy sống khi cửa sổ đóng (§18.6.2)
  bo_chay.py       CaiDat · một nhịp · vào/sửa lệnh · quy đổi đơn vị · thống kê
  khop_lenh.py     phần việc của SÀN: khớp lúc nào, ở giá nào (hàm thuần, không numpy)
  kho/             danh mục app tính được — nen_tang · chi_bao · zone
  mau/             sơ đồ mẫu, là JSON như mọi chiến lược khác
  api.py           bề mặt DUY NHẤT giao diện gọi tới (JS → api → core/bo_chay)
                   └─ Api (cửa sổ vẽ) · ApiTester · ApiLive · ApiRL — mỗi cửa sổ MỘT
                      thể hiện, bề mặt hẹp. NenCuaSo lo khung, NenChay lo nến+CaiDat.
webui/src/
  App.tsx          cửa sổ VẼ · tester/ · live/ · rl/ — main.tsx rẽ bằng ?tester ?live ?rl
tools/
  chay_test · van_tay · soi_rac · build_ui · chay · dong_goi
tai_lieu/
  core.md          VÌ SAO — đọc trước khi sửa cơ chế
  notes.md         LÀM THẾ NÀO — file này
  van_tay.json     vân tay đã chốt (do tools\van_tay.bat quản)
```
