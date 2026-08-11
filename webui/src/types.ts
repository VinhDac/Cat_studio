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
  cach_tinh: Record<string, string>
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
  phep_so: Record<string, string>
  cach_tinh: Record<string, string>
  huong: Record<string, string>
  loai_lenh: Record<string, string>
  sua_che_do: Record<string, string>
  sua_can_gia: string[]
  sua_can_phan_tram: string[]

  /** Bộ nến đã tải — hộp thoại Cài đặt quản lý (tải thêm · xoá · số MB). */
  nguon: BoNen[]
  co_mt5: boolean

  don_vi_tham_so: Record<string, string>
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
  so_vung: number
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
