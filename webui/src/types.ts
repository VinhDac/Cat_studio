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
    ma_so: string; ten: string; mo_ta: string; la_engine: boolean; nguon: string
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
  /** Mốc neo của khối Vào lệnh — `zone_HH` · `zone_LL` · `gia_hien_tai`. */
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
  /** ZONE lớn dần trong cửa sổ lô: `[t_zone_mở, t_nến, đáy, đỉnh]`.
   *
   *  ⚠ Lô phải mang zone vì lúc phát lại `nhip()` KHÔNG hỏi Python câu nào. Thiếu nó
   *  thì zone chỉ nhúc nhích ở đường NHẢY — bấm ▶ zone đứng yên, bấm "tới sự kiện" mới
   *  thấy nó nhảy một phát. Lệnh không bị vậy vì lô vốn mang cả sự kiện tương lai và
   *  `Chart` tự cắt theo `tBayGio`; giờ zone theo đúng luật đó. */
  zone?: [number, number, number, number][]
  /** BẢNG SỐ LIỆU: nhóm do `kho/` khai, hàng do SƠ ĐỒ quyết (`core.toan_hang_dung`),
   *  mỗi hàng một mảng giá trị theo TỪNG khung hình. Không nhóm nào viết cứng ở JS —
   *  thêm engine mới là bảng có ngay. */
  bang: {
    /** KHÔNG in ra. Giao diện chỉ dùng nó để biết chỗ kẻ một đường mảnh — xem
     *  `BangSoLieu`. */
    nhom: string
    dong: {
      ten: string
      /** Bổ nghĩa: `M15·50·SMA`. Rỗng với toán hạng không có khung/chu kỳ. */
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
