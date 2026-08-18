/** Hình dạng dữ liệu đi qua cầu nối. Phải khớp với `api.py` / `core.py`.
 *
 * Lưu ý: phía JS KHÔNG tự dựng mấy shape này từ con số 0 — nó nhận từ Python và gửi
 * lại nguyên vẹn. Mọi hiểu biết về định dạng file nằm ở `core.py`.
 */

/** Hai loại khối, không hơn. `start` là điểm neo — cả sơ đồ chạy lại từ đó mỗi nến. */
export type StepKind = 'start' | 'action'

/** Một khối — coi như hộp đen. JS chỉ đụng tới `id`, `kind`, `name`, `pos`, `ghim`. */
export interface Step {
  id: string
  kind: StepKind
  name?: string
  pos?: [number, number]
  /** Ghim số: khối này là điểm quay lại hợp lệ, nhãn của nó không đổi khi có
   *  đường nối ngược về. Bật/tắt bằng chuột phải. */
  ghim?: boolean
  /** CHỈ khối Bắt đầu: nhịp chạy của sơ đồ ("M5" / "M1" …). Trước đây là
   *  `doc.timeframe` + một dropdown trên ribbon; giờ thuộc về chính điểm neo. */
  nhip?: string
  [k: string]: unknown
}

export interface ProcEdge {
  from: string
  to: string
  port: string
  from_side?: string
  to_side?: string
}

/** Một dòng chữ trên hộp — do `api.describe()` sinh, không phải JS tự ghép.
 *  Khối "Kiểm tra điều kiện": mỗi dòng là MỘT điều kiện (nối nhau bằng VÀ).
 *  Khối "Vào lệnh" / "Sửa lệnh": mỗi dòng là MỘT TRƯỜNG (lot · đệm · SL · TP). */
export interface CardLine {
  text: string
  /** Loại hành động — giao diện dùng để CHỌN ICON. Python không gắn emoji vào text. */
  type?: string | null
}

export interface Card {
  id: string
  kind: StepKind
  title: string
  badges: string[]
  lines: CardLine[]
  /** Câu đầy đủ, dùng làm tooltip. `lines` là bản ngắn để vẽ lên hộp. */
  mo_ta: string
  /** CHỈ khối Bắt đầu — nhịp chạy, để menu chuột phải tick đúng mục. */
  nhip?: string
  ghim: boolean
  la_cong: boolean
  /** Khoá màu NGỮ NGHĨA do Python suy ra: `start · hoi · mua · ban · sua`. Không phải mã
   *  màu — giao diện tự ánh xạ sang biến CSS, nên đổi bảng màu không phải sửa Python. */
  mau?: string
}

export interface Problem {
  severity: 'error' | 'warning' | string
  message: string
  step?: string | null
  index?: number | null
  /** Sơ đồ nào — bảng Vấn đề hiện lỗi của CẢ HAI tab, kèm nhãn. */
  tab: Tab
  /** Chỉ có ở cảnh báo "số gõ tay hai chỗ" — đủ dữ liệu để đặt tên bằng MỘT nút.
   *  `cho` là đường đi vào từng ô số, để giao diện khỏi phải quét lại sơ đồ (quét hai
   *  lần bằng hai đoạn mã là hai luật, và chúng sẽ lệch nhau). */
  dat_ten?: {
    goi_y: string; gia_tri: number; don_vi: string; nhan: string
    cho: { tab: Tab; step: string; duong: (string | number)[] }[]
  }
}

/** Hai sơ đồ trong một chiến lược.
 *  `entry` đi săn (một lượt mỗi nến) · `manage` chạy một lượt cho MỖI lệnh đang sống. */
export type Tab = 'entry' | 'manage'

export interface SoDo {
  steps: Step[]
  edges: ProcEdge[]
  cards: Card[]
}

/** Một núm vặn của chiến lược. Hằng số CÓ TÊN, đơn vị bất biến (bps · nến · ×ATR ·
 *  ×R) — không pip, không đô. Đây là hợp đồng chuẩn hoá của D_02. */
export interface ThamSo {
  ten: string
  nhan: string
  gia_tri: number
  don_vi: string
  ghi_chu: string
}

export interface ProcessDoc {
  name: string
  symbol: string
  tham_so: ThamSo[]
  entry: SoDo
  manage: SoDo
}

/** Danh mục kho — mọi thứ app tính được, do `kho/` tự gom từ các module con. */
export interface KhoDanhMuc {
  module: {
    ma_so: string; ten: string; mo_ta: string; nguon: string
    so_chi_bao: number; so_toan_hang: number; so_bang: number
  }[]
  chi_bao: { key: string; nhan: string; tham_so: string[]; cong_thuc?: string
             mo_ta?: string; nguon: string }[]
  toan_hang: ToanHang[]
  bang_trang_thai: {
    key: string; nhan: string; mo_ta: string; nguon: string
    truong: { ten: string; kieu: string; vd: string }[]
    luat: string[]
  }[]
  hanh_dong: { key: string; nhan: string; tabs: Tab[] }[]
  don_vi: Record<string, string>
  sua_che_do: Record<string, string>
  phep_so: Record<string, string>
  trang_thai_lenh: Record<string, string>
  ly_do_dong: Record<string, string>
  luu_tru: {
    goc: string
    muc: { ten: string; duong_dan: string; so_luong: number; danh_sach: string[] }[]
  }
}

export interface ToanHang {
  key: string
  nhan: string
  nhom: string
  tham_so: string[]
  /** Module nào cung cấp: `nen_tang` · `chi_bao` · `d02` … */
  nguon?: string
  mo_ta?: string
  dung_sai?: boolean
  /** null/thiếu = dùng được ở cả hai sơ đồ. */
  tabs?: Tab[] | null
}

export interface Bootstrap {
  phien_ban: string
  settings: Record<string, unknown>
  app_dir: string

  kinds: StepKind[]
  kind_labels: Record<string, string>

  tabs: Tab[]
  tab_labels: Record<string, string>
  action_types: string[]
  action_labels: Record<string, string>
  /** Hành động nào dùng được ở tab nào. Entry chỉ TẠO, Manage chỉ SỬA. */
  action_tabs: Record<string, Tab[]>
  /** Loại hành động đóng vai CỔNG rẽ nhánh. */
  branch_type: string
  /** Tên nhóm toán hạng chỉ có nghĩa ở Manage. */
  nhom_lenh_nay: string
  /** Toán hạng vốn đã đúng/sai — hộp thoại ẩn ô vế phải. */
  toan_hang_dung_sai: string[]

  timeframes: string[]
  /** Nhịp mặc định mỗi sơ đồ: Entry M5 (quyết định) · Manage M1 (phản ứng). */
  nhip_mac_dinh: Record<Tab, string>
  ma_methods: Record<string, string>
  toan_hang: ToanHang[]
  /** Tám phép: `< ≤ > ≥ = ≠` + `là ĐÚNG` / `là SAI`. Hai phép cuối dùng CHO VÀ CHỈ CHO
   *  toán hạng đúng/sai, và chúng KHÔNG có vế phải. */
  phep_so: Record<string, string>
  /** ĐƠN VỊ — MỘT bảng cho cả app: điều kiện, SL/TP/đệm, sửa lệnh.
   *  Trước đây là hai bảng (`CACH_TINH` + `DON_VI_SS`) trùng nhau ba cặp. */
  don_vi: Record<string, string>
  don_vi_ngan: Record<string, string>
  /** Đơn vị nào dùng được ở đâu: `dieu_kien` · `dem` · `sl` · `tp` · `sua`. */
  don_vi_cho: Record<string, string[]>
  huong: Record<string, string>
  loai_lenh: Record<string, string>
  /** Mốc neo — dùng chung cho khối Vào lệnh VÀ khối Sửa lệnh. Danh sách do Python gom
   *  từ kho (mọi toán hạng MỨC GIÁ không cần hỏi thêm con số), không gõ tay. */
  moc_entry: Record<string, string>
  /** Mốc nào chỉ có nghĩa khi phía trên có cổng zone. */
  moc_can_zone: string[]
  /** MỌI đơn vị → nhãn, kể cả đơn vị ĐẾM. Bảng tham số khai `don_vi` bằng khoá ở đây. */
  nhan_don_vi: Record<string, string>
  /** Đơn vị ĐẾM (`nen` · `lenh` · `lot`) — không quy đổi gì, chỉ nói con số đo cái gì. */
  don_vi_dem: Record<string, string>
  /** Toán hạng → đơn vị CỐ ĐỊNH của ô so với nó. `null` = đúng/sai, không có vế phải. */
  toan_hang_don_vi: Record<string, string | null>
  /** Toán hạng → loại đại lượng. Quyết định ô đơn vị sống hay mờ. */
  toan_hang_loai: Record<string, string>
  /** Loại DUY NHẤT được chọn đơn vị: `khoang_cach`. */
  loai_co_don_vi: string
  /** Toán hạng → đơn vị chính là NÓ. Chọn cái đó thì kết quả luôn = 1, nên không bày. */
  don_vi_chinh_no: Record<string, string>
  /** Toán hạng chỉ có nghĩa khi đã có zone. */
  toan_hang_can_zone: string[]
  /** Đơn vị chỉ có nghĩa khi đã có zone (`× ATR zone` · `mép zone đối diện`). */
  don_vi_can_zone: string[]
  /** Bốn chế độ: dời SL · dời TP · SL về hoà vốn · KẾT THÚC LỆNH NÀY (gộp đóng+huỷ). */
  sua_che_do: Record<string, string>
  sua_can_gia: string[]

  /** Bộ nến đã tải — hộp thoại Cài đặt quản lý (tải thêm · xoá · số MB). */
  nguon: BoNen[]
  co_mt5: boolean

  /** LUẬT SÀN đã ĐO ĐƯỢC, theo symbol. Có mặt = hồ sơ hiệu chuẩn thắng ô gõ tay. */
  luat_san?: Record<string, {
    lot_min: number; lot_buoc: number; lot_max: number; stops_level: number
    nguon: string; do_luc: string
  }>

  /** Đơn vị của những ô CỐ ĐỊNH ngoài điều kiện: `chu_ky` → nến, `lot` → lot. */
  don_vi_o: Record<string, string>
  template_kinds: Record<string, string>
  accent_presets: Record<string, string>
  max_process_steps: number
}

export interface Reply<T> {
  ok: boolean
  value?: T
  error?: string
  trace?: string
  [k: string]: unknown
}

export interface LuongSoDo {
  order: Record<string, string>
  unreachable: string[]
  /** Cạnh quay lại HỢP LỆ (tới khối đã ghim) — vẽ nét đứt. */
  quay_lai: [string, string][]
  /** Vòng lặp CHƯA ghim. */
  vong_ho: [string, string][]
  lech_nhanh: string[]
  /** Khối nào dòng chảy đã đi QUA cổng zone trước khi tới — chỉ ở đó zone mới tồn tại,
   *  nên chỉ ở đó mới bày ra toán hạng zone và đơn vị `× ATR zone`. */
  sau_cong_zone: string[]
}

/** Kết quả `api.validate` — soát CẢ HAI sơ đồ trong một lời gọi. */
export interface KetQuaSoat extends Reply<Problem[]> {
  so_loi?: number
  so_canh_bao?: number
  luong?: Record<Tab, LuongSoDo>
}


/* ======================= STRATEGY TESTER =======================
 * Mọi hình dạng dưới đây do `api.ApiTester` sinh. Giao diện KHÔNG tự tính con số nào —
 * kể cả một phép cộng. Chữ trong nhật ký cũng do Python dựng (core.md §12.8).
 */

export interface BoNen {
  symbol: string
  tu: number | null; den: number | null
  tu_chu: string; den_chu: string
  so_nen: number
  /** Dung lượng đang chiếm — thứ người dùng cần để quyết có xoá không. */
  mb: number
  digits?: number; point?: number; contract_size?: number
  /** Spread TRUNG VỊ đo trên chính dữ liệu đã tải — gợi ý cho ô spread. */
  spread_tb?: number | null
  tai_luc?: string
}

export interface TesterBoot {
  phien_ban: string
  accent?: string
  doc: ProcessDoc | null
  cai_dat: Record<string, unknown>
  timeframes: string[]
  nguon: BoNen[]
  co_mt5: boolean
}

export interface ThongKe {
  so_lenh: number; so_dong: number; so_huy: number
  thang: number; thua: number; ty_le_thang: number
  lai_tien: number; tong_R: number; von_cuoi: number; drawdown_pt: number
  von_dau: number; lai_pt: number
  drawdown_tien: number
  /** Thời điểm chạm đáy sụt giảm. `null` = chưa có lệnh nào đóng. */
  drawdown_luc: number | null
  R_moi_lenh: number; R_khi_thang: number; R_khi_thua: number
  /** `null` = CHƯA CÓ lệnh lỗ nào, không phải 0. Hai chuyện khác hẳn nhau. */
  he_so_lai: number | null
  chuoi_thua: number
  so_zone: number
  /** Số nến M1 có CẢ SL lẫn TP trong biên độ. 0 = kết quả không phụ thuộc giả định
   *  đường đi 4 điểm (core.md §12.13d). */
  nen_mo_ho: number
  so_luot: number
}

/** Tab Thống kê — tổng kết CẢ LƯỢT CHẠY, cố định, không theo con trỏ. */
export interface ThongKeChay {
  tk: ThongKe
  /** `[thời_điểm, vốn, sụt_giảm_%]` — mỗi nến trục có lệnh đóng một điểm. Sụt giảm là
   *  số ÂM để vẽ úp xuống. */
  duong_von: [number, number, number][]
  /** Khoảng THẬT SỰ có nến. */
  t_dau: number; t_cuoi: number
  /** Khoảng ĐÃ YÊU CẦU trong Cài đặt — lệch với trên là chuyện thường. */
  yc_tu: string; yc_den: string
  symbol: string
  nhip: { entry: string; manage: string }
}

/** Một mục lịch sử, bản GỌN cho danh sách. `ten === null` = mục mềm (bị cuốn chiếu);
 *  có tên = đã lưu, không bao giờ bị cuốn. */
export interface MucLichSu {
  ma: string
  t: number
  ten: string | null
  ten_chien_luoc: string
  van_tay: string
  cai_dat: { symbol?: string; tu?: string; den?: string } & Record<string, unknown>
  nguon: { symbol: string; so_nen: number; t_dau: number; t_cuoi: number }
  thong_ke: ThongKe
}

export interface XemLichSu {
  tom_tat: ThongKeChay
  nguon: { symbol: string; so_nen: number; t_dau: number; t_cuoi: number }
  ten: string | null
  t: number
  /** Nến nguồn còn khớp lúc chạy không — không khớp thì KHÔNG mở lại phát lại được. */
  chay_lai_duoc: boolean
  vi_sao: string
}

export interface KetQuaChay {
  so_nen_m1: number; so_nen_truc: number; tf: string
  t_dau: number; t_cuoi: number
  thong_ke: ThongKe
  /** Một dòng trả lời "so với lần trước thì sao" — vòng lặp nâng cấp model. */
  so_hai_lan: string
  digits: number
}

/** Cửa sổ nến M1 kết thúc Ở CON TRỎ. Không có nến nào bên phải — nến chưa xảy ra thì
 *  chưa tồn tại, đó là cả điểm của replay. */
export interface CuaSoNen {
  t: number[]; o: number[]; h: number[]; l: number[]; c: number[]
  j0: number; j: number
}

export interface LenhVe {
  id: string; huong: string; trang_thai: string
  t_dat: number; t_khop: number | null; t_dong: number | null
  gia_dat: number | null; gia_khop: number | null; gia_dong: number | null
  sl: number | null; tp: number | null
  ly_do_dong: string | null; lot: number; lai_R: number | null
  /** Đường đi của SL theo thời gian `[[t, sl], …]`, dựng từ chính nhật ký. Nhờ nó chart
   *  vẽ được cái BẬC THANG lúc `Dời SL về hoà vốn` chạy — bản trước chỉ có SL cuối cùng
   *  nên khoảnh khắc đó tàng hình. */
  /** Lệnh do BÀI KIỂM đặt, không phải chiến lược — chart vẽ mờ, không nhãn. */
  la_kiem?: boolean
  sl_lich_su?: [number, number][]
  /** Y hệt `sl_lich_su` nhưng cho TP. Cần riêng vì chế độ `Dời Take Profit` làm TP nhảy
   *  bậc giữa đời lệnh — vẽ bằng mức cuối là lộ tương lai. */
  tp_lich_su?: [number, number][]
}

/** SOI MỘT LƯỢT trên sơ đồ — do `api.test_soi_luot` bắn sang cửa sổ vẽ.
 *
 *  `cong` mang MỌI cổng lượt đó đã thử, kèm vết TỪNG điều kiện theo đúng thứ tự các
 *  dòng trong hộp — nhờ vậy tô được tới đúng dòng điều kiện hỏng, không chỉ tô cả hộp. */
export interface SoiLuot {
  tab: Tab
  duong: string[]
  cong: { khoi: string; khop: boolean; ve: { trai: number | null; phai: number | null; dat: boolean }[] }[]
  ket: string
  lenh_id: string | null
  nhan: Record<string, string>
  chu: string
}

/** Thứ bơm vào từng node lúc vẽ. `null` = không soi gì. */
export interface SoiKhoi {
  daChay: boolean
  truot: boolean
  /** `dat` của từng điều kiện, cùng thứ tự với `card.lines`. Rỗng = không tô dòng nào
   *  (khối không phải cổng, hoặc số điều kiện đã đổi từ lúc chạy). */
  dieuKien: boolean[]
}

/** Một chặng trên ĐƯỜNG RAY của một lệnh — xem `api.test_duong_ray`.
 *  `tab = null` nghĩa là chặng này do THỊ TRƯỜNG, không phải sơ đồ (khớp, chạm SL/TP). */
export interface ChangRay {
  tab: string | null
  moc?: string
  khoi: string[]
  dem: number
  viec: string[]
  /** Chặng bắt đầu / kết thúc lúc nào. Cần cả hai: hiện theo `t`, nhưng `t_het` còn ở
   *  tương lai thì con số lặp chưa chốt — in ra như đã xong là lộ tương lai. */
  t: number
  t_het: number
}

export interface DongBang { ten: string; gia_tri: number | string | boolean | null }

export interface Khung {
  j: number; i: number; t: number
  bang: {
    toan_hang: DongBang[]
    engine: DongBang[]
    tai_khoan: DongBang[]
    /** Mỗi lệnh đang sống MỘT HÀNG — nhóm "Lệnh này" không có một giá trị duy nhất
     *  tại nến i, vì Manage chạy một lượt cho mỗi lệnh. */
    lenh: {
      id: string; huong: string; da_khop: boolean
      gia_vao: number | null; sl: number | null; tp: number | null
      lai_R: number | null; sl_hoa_von: boolean; so_nen_song: number
    }[]
  }
  lenh: LenhVe[]
}

export interface LoNhatKy {
  tong: number; tu: number
  dong: { i: number; nen: number; tab: string; lenh_id: string | null
          co_viec: boolean; chu: string }[]
}


/** Tiến trình một lần chạy — backtest chạy trên luồng nền, giao diện hỏi 200 ms/lần.
 *  Ba giây im lặng không phân biệt được với treo. */
export interface TrangThaiChay {
  dang_chay: boolean
  da: number; tong: number; chu: string
  xong: KetQuaChay | null
  loi: string | null
}

/** MỘT LÔ khung hình để PHÁT LẠI — cửa duy nhất dùng lúc phát.
 *
 * Mang đủ mọi thứ ba vùng cần cho ~300 nhịp, nên khi phát thì JS không hỏi Python một
 * câu nào. Gọi cầu nối 33 lần/giây thì phát sẽ giật, mà nhịp đều mới là thứ quan trọng
 * nhất khi xem nến hình thành. */
export interface DoanPhat {
  j0: number; n: number
  t: number[]; o: number[]; h: number[]; l: number[]; c: number[]
  /** ZONE lớn dần trong cửa sổ lô: `[t_zone_mở, t_nến, đáy, đỉnh, hợp_lệ]`.
   *
   *  `hợp_lệ` (1/0) đọc từ cột `zone_hop_le` GHI LÚC CHẠY, không tính lại ở JS — nên
   *  lúc phát lại zone đổi màu đúng cây nến nó vừa hợp lệ. Sơ đồ chưa khai phần "hợp
   *  lệ" thì luôn 0 và chart giữ màu trung tính.
   *
   *  ⚠ Lô phải mang zone vì lúc phát lại `nhip()` KHÔNG hỏi Python câu nào. Thiếu nó
   *  thì zone chỉ nhúc nhích ở đường NHẢY — bấm ▶ zone đứng yên, bấm "tới sự kiện" mới
   *  thấy nó nhảy một phát. Lệnh không bị vậy vì lô vốn mang cả sự kiện tương lai và
   *  `Chart` tự cắt theo `tBayGio`; giờ zone theo đúng luật đó. */
  zone?: [number, number, number, number, number][]
  /** BẢNG SỐ LIỆU: nhóm do `kho/` khai, hàng do SƠ ĐỒ quyết (`core.toan_hang_dung`),
   *  mỗi hàng một mảng giá trị theo TỪNG khung hình. Không nhóm nào viết cứng ở JS —
   *  thêm engine mới là bảng có ngay. */
  bang: {
    /** KHÔNG in ra. Giao diện chỉ dùng nó để biết chỗ kẻ một đường mảnh — xem
     *  `BangSoLieu`. */
    nhom: string
    dong: {
      ten: string
      /** Bổ nghĩa: `M15·50·SMA`, có thể kèm ĐƠN VỊ TẠI CHỖ ĐỌC — `M5·14 [bps]`.
       *  Chữ đơn vị do PYTHON ghép từ `core.DON_VI_NGAN`; cửa sổ Tester/Live không nhận
       *  bảng đơn vị nào, nên gửi khoá thô sang là buộc JS đẻ ra một bảng nhãn thứ hai.
       *  Đơn vị GIÁ không in nhãn. Rỗng với toán hạng không có khung/chu kỳ/đơn vị. */
      phu: string
      gia_tri: (number | string | boolean | null)[]
    }[]
  }[]
  lenh_song: {
    id: string; huong: string; da_khop: boolean
    loai: string; gia_dat: number | null
    gia_vao: number | null; sl: number | null; tp: number | null
    lai_R: number | null; sl_hoa_von: boolean
  }[][]
  tai_khoan: { cho: number; mo: number; gia: number }[]
  lenh: LenhVe[]
  nhat_ky: { i: number; j: number; co_viec: boolean; lenh_id: string | null; chu: string }[]
}

/* ======================= LIVE =======================
 * Cửa sổ Live trả lời một câu khác hẳn tester: có TIN được cái đang chạy không.
 */

export interface TinKetNoi {
  noi_duoc: boolean
  nen_song: boolean
  chu: string
  tai_khoan: number | null
  server: string
  /** Tên sàn. Khoá tiếng Việt có dấu — do Python đặt, giữ nguyên để không lệch hợp đồng. */
  'sàn': string
  /** `null` = chưa đọc được. Đọc từ `trade_mode`, KHÔNG hỏi người dùng. */
  la_that: boolean | null
  cho_giao_dich: boolean
  symbol_giao_dich_duoc: boolean
  tuoi_tick: number | null
  spread_diem: number | null
  /** spread thật ÷ spread đã backtest. ≥ 2 là chiến lược đang chạy ở thế giới khác. */
  spread_lech: number | null
  lech_gio: number | null
  /** Cây nến ĐANG hình thành — chỉ để CHART sống theo giây. Chiến lược không bao giờ
   *  đọc nó: quyết định chỉ ở biên nến đã đóng. */
  nen_dang: { t: number; o: number; h: number; l: number; c: number } | null
  tre_ms: number
  tre_p50: number | null
  tre_p95: number | null
  so_lan_rot: number
  giay_rot: number
  phien_giay: number
}

export interface VanDeLive {
  severity: 'error' | 'warning' | string
  message: string
  tab: string
}

export interface DeNghi { spread_diem: number | null; vi_sao: string
                          stops_level_that: number | null }

/** BỐN MỨC, không phải đạt/hỏng — xem `ket_noi._cham`.
 *    `tron`  chạy trơn        `xac`   phòng vệ sửa TRƯỚC khi gửi (giả thuyết đúng sẵn)
 *    `do`    sàn từ chối, phòng vệ chữa được → VẪN ĐẠT
 *    `hong`  phòng vệ bó tay → phải chỉnh con số
 *    `nguoi` máy không chữa được → cần người ra tay
 *  Cộng hai mức KHÔNG phải bước chạm sàn, chỉ để đọc nhật ký:
 *    `moc`   mốc "── lượt 2/4"      `chinh` một dòng chỉnh giả thuyết
 */
export type MucBuoc = 'tron' | 'xac' | 'do' | 'hong' | 'nguoi' | 'moc' | 'chinh'

export interface BuocTest {
  ten: string; dat: boolean; chu: string; ms: number | null
  muc?: MucBuoc; ma?: number | null
}

/** Con số Đề phòng thuộc loại gì — quyết định nó có mang từ DEMO sang THẬT được không.
 *    `san`  luật của sàn        → demo và thật giống nhau, chép sang vô tư
 *    `khop` chất lượng khớp     → demo KHÔNG có thanh khoản thật, số đo là CHẶN DƯỚI
 *    `ta`   cách app tự xử      → không phụ thuộc tài khoản nào
 *  Xem `gui_lenh.LOAI`. */
export type LoaiSo = 'san' | 'khop' | 'ta'

export interface DongDePhong { ten: string; gia: string; chu: string; loai: LoaiSo }

/** Hồ sơ đã đo cho CÙNG symbol nhưng dưới tên sàn khác — ứng viên để chép sang. */
export interface HoSoKhac {
  khoa: string; san: string; server: string
  do_luc: string | null; so_vong: number | null; trang_thai: string | null
}

export interface DePhong {
  da_hieu_chuan: boolean
  trang_thai: string | null
  /** Đang chạy trên tài khoản thật hay không — đổi cách đọc mấy dòng `khop`. */
  la_that: boolean | null
  /** Hồ sơ này chép từ sàn khác sang, không phải đo tại chỗ. */
  chep_tu: string | null
  do_o_server: string
  ho_so_khac: HoSoKhac[]
  dong: DongDePhong[]
}

/** Kết quả VÒNG LẶP hiệu chuẩn. `trang_thai` là câu trả lời, `buoc` chỉ là dấu vết. */
export interface KetQuaHieuChuan {
  trang_thai: 'xong' | 'nguoi' | 'chua_hoi_tu'
  chay_duoc: boolean
  chu: string
  buoc: BuocTest[]
  /** Lịch sử chỉnh giả thuyết — mỗi dòng "khoá: cũ → mới — vì sao". */
  da_chinh: string[]
  can_nguoi: string[]
  /** Mã sàn trả về mà ta chưa có luật xử. Đây là chỗ cái chưa biết lộ mặt. */
  ma_la: number[]
  luat: Record<string, number | null>
  lan: { luat: Record<string, number | null>; chu: string
         dem: Record<string, number> }[]
  de_nghi: DeNghi | null
  stops_level_that: number | null
}

/* ==========================================================================
 *  CỬA SỔ RL — bàn điều khiển máy tìm chiến lược (core.md §18.6)
 * ========================================================================== */

/** Một THẺ tắt được ở tầng CHỌN — `th:atr`, `sl:1.5`, `tf:M5`… (§18.6.1).
 *
 * Giao diện chỉ cầm chuỗi `the` rồi gửi ngược lại; nó KHÔNG cần biết một thẻ nghĩa là
 * gì. Thêm một chiều mới (chế độ sửa, nấc thang, khung giờ…) là việc của Python một
 * mình — panel tự dài ra. */
export interface MucChon {
  the: string; nhan: string
  /** Toán hạng zone — chỉ có nghĩa SAU cổng zone (§12.6c). */
  z?: boolean
  /** Chỉ dùng được ở sơ đồ Manage. */
  manage?: boolean
}

export interface NhomChon {
  /** `kho` = panel Kho đồ · `thang` = panel Thang số. */
  cho: 'kho' | 'thang'
  nhom: string; nhan: string
  don_vi: string | null
  muc: MucChon[]
}

/** Ba con số của §18.2 cho một kỳ (tuần hoặc tháng). */
export interface BaSo {
  trung_binh: number; dao_dong: number; diem: number
  co_lenh: number; so_ky: number; ty_le_co_lenh: number
  lo_trung_binh: number; te_nhat: number; tot_nhat: number
}

/** Một dòng trong nhóm đầu bảng. */
export interface DauBang {
  hang: number; diem: number; so_lenh: number
  sut_von_pt: number; lai_pt: number
  /** CẢ HAI kỳ — `ky` nói cái nào đang được dùng để chấm. */
  tuan: BaSo; thang: BaSo; ky: string
  /** Dương ở mấy cửa sổ cuốn tới — con số đáng đọc hơn `diem` (§18.5f). */
  cua_so_duong?: number
  so_cua_so?: number
  /** Điểm TỪNG cửa sổ. Không kèm ngày: mọi sơ đồ một lượt chạy cùng dải nên cửa sổ
   *  giống hệt nhau — thứ cần đọc ở dải này là HÌNH DẠNG, không phải mốc lịch. */
  cua_so?: number[]
  so_nuoc: number; ten: string
}

export interface ThongKeTim {
  da_chay: number; trung_lap: number; ket: number; no: number
  khong_lenh: number; rot_cua: number; qua: number
  /** Bỏ dở giữa chừng vì vượt trần nhịp vào lệnh (§18.4a). Không phải lỗi. */
  na_lenh?: number
  hat: number; so_luot: number
  /** Vì sao lượt chạy ngừng: đủ số lượt · hết giờ · phẳng · người dùng dừng. */
  vi_sao_ngung?: string
  ly_do_rot: Record<string, number>
  /** Rớt ở cửa nào, TRƯỢT BAO XA, kèm ví dụ nguyên văn.
   *
   * ⚠ `ly_do_rot` chỉ đếm được vì nó gom câu tiếng Việt bằng cách cắt ba chữ đầu —
   * `"tuần có lệnh 12/53 (23%) — dưới 50%"` co lại thành `"tuần có lệnh"`. Cái này giữ
   * cả MỨC ĐỘ, nên trả lời được *nới cửa một chút thì thêm bao nhiêu cái lọt*. */
  rot_chi_tiet?: Record<string, {
    so: number
    nguong: number
    /** Năm thùng "thiếu bao xa" — thùng ĐẦU là suýt qua (<10%). */
    thieu: number[]
    vi_du: string[]
  }>
  no_vi?: string[]
  /** Bỏ dở vì ÔM LỆNH (§18.4d) — khác `na_lenh`, cái đó là nã lệnh. */
  qua_nang?: number
  /** Ba phân bố cho bàn điều khiển — mép thùng khai ở `BangDieuKhien.tsx`. */
  hist_diem?: number[]
  hist_lenh?: number[]
  hist_giay?: number[]
  /** Số sơ đồ qua cửa CỘNG DỒN — khác `qua`, cái đó là kích thước bảng đầu bảng. */
  qua_cong_don?: number
  /** Đã chạy bằng mấy nhân THẬT — có thể nhỏ hơn số xin, nếu không mở được bể. */
  so_nhan?: number
}

/** Trạng thái một lượt tìm. `luot_tim.LuotTim.trang_thai()` + nhóm đầu bảng. */
export interface TrangThaiLuot {
  ma: string; ten: string
  /** MỘT DÒNG mô tả lượt này chạy với gì — symbol · khoảng · kỳ · phạt · thẻ tắt · số
   *  sơ đồ · hạt. Không có nó thì sổ lượt là hai chục dòng không phân biệt được. */
  nhan?: string
  dang_chay: boolean
  da_chay: number; tong: number
  diem_tot_nhat: number | null
  bat_dau: number; xong_luc: number | null
  loi: string | null
  dung_giua_chung: boolean
  thong_ke: ThongKeTim | null
  /** ĐƯỜNG điểm tốt nhất — `[[đã chấm, điểm], …]`, chỉ có BẬC (điểm chỉ tăng). */
  duong: [number, number][]
  /** Giây trung bình một sơ đồ, đo THẬT trên lô đang chạy (không ước bằng số nến). */
  giay_moi_luot?: number
  /** Giây còn lại ước tính. */
  con_lai?: number
  /** Chỉ có ở `rl_trang_thai`, không có ở `rl_danh_sach`. */
  dau_bang?: DauBang[]
  /** Câu đang làm gì lúc chuẩn bị (tải nến…). */
  chu?: string
  /** Số sơ đồ qua cửa CỘNG DỒN — khác `dau_bang.length`, cái đó bị chặn ở `giu`. */
  qua_cong_don?: number
  /** `[[đã chấm, số qua cửa cộng dồn], …]`, chỉ ghi khi ĐỔI. */
  duong_qua?: [number, number][]
  /** Nhịp GẦN ĐÂY (giây/sơ đồ) — cùng `giay_moi_luot` dựng thành một KHOẢNG. */
  giay_gan_day?: number
  con_lai_som?: number
  con_lai_muon?: number
  /** Đủ mẫu để ước chưa. Dưới 30 lượt thì mọi con số "còn bao lâu" đều là bịa. */
  du_de_uoc?: boolean
  /** Số nhân ĐANG dùng — kéo thanh là đổi ngay, không đợi lượt sau. */
  nhan_dung?: number | null
  so_nhan?: number
}

export interface RLBoot {
  phien_ban: string
  accent?: string
  chon: NhomChon[]
  tran: Record<string, number>
  cua: CuaRL
  tuan_co_lenh_toi_thieu: number
  so_nuoc_di: number
  /** Máy có mấy nhân — đầu trên của thanh kéo CPU. */
  so_nhan_may: number
  cai_dat: Record<string, unknown>
  kho_nen: KhoNen
  luot: TrangThaiLuot[]
}

/** Mấy cái CỬA — "cái gì tôi KHÔNG nhận". `null` = không lọc.
 *
 * ⚠ Toàn là cửa, không cái nào là cân: sụt vốn không đổi chác được với lãi. Và xếp
 * hạng thì LUÔN là `trung bình ÷ dao động` — chỉnh được *thích gì*, không chỉnh được
 * *đo bằng gì* (§18.6.4). */
export interface CuaRL {
  /** Chấm theo `tuan` hay `thang`. `null` = tuần. */
  ky: string | null
  /** Vế DAO ĐỘNG có tham gia không: `0` chỉ nhìn lãi · `1` cân bằng. `null` = 1.
   *
   * ⚠ Không có nấc 2. Đo trên sơ đồ mẫu: trung bình −0,161% · dao động 1,115% ⇒
   * `k=1` cho −0,1446 nhưng `k=2` cho −0,1296 — "ưu tiên đều" lại chấm CAO HƠN, vì
   * trung bình ÂM thì càng chia càng gần 0. Tỉ số không đơn điệu theo mẫu số. */
  manh_deu: number | null
  tuan_co_lenh: number | null
  sut_von_toi_da: number | null
  lai_toi_thieu: number | null
  so_lenh_toi_thieu: number | null
  te_nhat_toi_da: number | null
  dao_dong_toi_da: number | null
  diem_toi_thieu: number | null
}

/** Kho nến đang có gì — hiện TRƯỚC khi bấm chạy, để khỏi đặt khoảng ngoài dải rồi
 *  ngồi đợi mới biết. */
export interface KhoNen {
  symbol: string
  co: boolean
  so_nen?: number
  tu?: string
  den?: string
  so_lo_hong?: number
  spread_tb?: number | null
  chu?: string
}

/** Bộ ĐẶT gửi sang Python khi bấm Chạy. */
export interface DatRL {
  ten: string
  so_luot: number
  hat: number
  cua: Record<string, number | string | null>
  tran: Record<string, number>
  /** Thẻ KHÔNG dùng lần này — `th:atr`, `sl:1.5`, `tf:M5`… */
  tat: string[]
  /** Đè lên Cài đặt → Strategy Test: symbol · từ · đến · vốn · phí · spread · trượt. */
  cai_dat: Record<string, unknown>
  /** Giữ bao nhiêu sơ đồ đầu bảng. */
  giu?: number
  /** Chạy quá ngần này GIỜ thì thôi — hợp lý hơn đặt số lượt khi chạy qua đêm. */
  gio_toi_da?: number | null
  /** Phẳng ngần này lượt liền thì tự dừng — bản tự động của thứ `DuongQua` mách. */
  phang_toi_da?: number | null
  /** Mấy TIẾN TRÌNH chấm song song. `1` = chạy thẳng, `0` = tự chọn theo số nhân máy. */
  so_nhan?: number
}

/** MỔ XẺ — một lượt chạy tách thành một con số cho MỖI khối (§18.5b). */
export interface PhanBoTien {
  khoi: string; tab: string; nhan: string
  den: number; so_lenh: number; da_dong: number
  tien: number; thang: number; thua: number; tong_R: number
}
export interface PhanBoCong {
  khoi: string; tab: string; nhan: string
  xet: number; khop: number
  ty_le: number | null
  zone: boolean; luon_khop: boolean; luon_chan: boolean
}
export interface PhanBo {
  co_dem: boolean
  tien: PhanBoTien[]
  cong: PhanBoCong[]
  /** Khối dòng chảy CHƯA BAO GIỜ tới — gỡ ra thì kết quả không đổi, khỏi chạy lại. */
  chac_bo_duoc: { khoi: string; tab: string; nhan: string; vi_sao: string }[]
}

/** Kết quả CẮT một nhánh rồi chạy lại (§18.5c).
 *
 * ⚠ Đọc `cua_so` / `tot_hon`, ĐỪNG đọc mỗi `truoc`/`sau`. Đo được: cắt nhánh BÁN của sơ
 * đồ mẫu cho `+0,3872` trên một quý — rất thuyết phục và sai, vì cả sáu quý thì chỉ 4/6
 * quý bỏ đi là tốt hơn. */
export interface ThuBo {
  khoi: string; buoc: string
  truoc: { diem: number; so_lenh: number; lai_pt: number }
  sau: { diem: number; so_lenh: number; lai_pt: number }
  cua_so: { tu: string; den: string; truoc: number; sau: number; chenh: number }[]
  tot_hon: number
  so_cua_so: number
  /** Cắt xong còn lệnh nào không. Không còn thì mọi con số là so với ĐỨNG NGOÀI. */
  con_lenh: boolean
}

/** Điểm MỘT cửa sổ cuốn tới trong đoạn khoá (§18.3). */
export interface CuaSoCham {
  tu: string; den: string
  diem: number; trung_binh: number; dao_dong: number
  co_lenh: number; so_ky: number
}

/** Một dòng so TRAIN với ĐOẠN KHOÁ (§18.3). */
export interface DongKhoa {
  hang: number
  train?: number
  khoa?: number
  khoa_lai_pt?: number
  khoa_sut_von_pt?: number
  khoa_so_lenh?: number
  khoa_tuan?: BaSo
  khoa_dat?: boolean
  khoa_ly_do?: string | null
  /** Điểm TỪNG cửa sổ cuốn tới — rỗng khi chia "một khối". */
  cua_so?: CuaSoCham[]
  cua_so_duong?: number
  so_cua_so?: number
  loi?: string
}

export interface KetQuaKhoa {
  ds: DongKhoa[]
  /** Đã mở đoạn khoá bao nhiêu lần. KHÔNG chặn, chỉ ĐẾM. */
  da_mo: number
  tu: string
  den: string
  /** Có chia cửa sổ cuốn tới không, và bước bao lâu (`thang` · `quy` · `nua_nam`). */
  cuon: boolean
  buoc: string
}
