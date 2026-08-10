/** Hình dạng dữ liệu đi qua cầu nối. Phải khớp với `api.py` / `core.py`.
 *
 * Lưu ý: phía JS KHÔNG tự dựng mấy shape này từ con số 0 — nó nhận từ Python và gửi
 * lại nguyên vẹn. Mọi hiểu biết về định dạng file nằm ở `core.py`.
 */

export type StepKind = 'start' | 'loop' | 'group' | 'action'

/** Một khối — coi như hộp đen. JS chỉ đụng tới `id`, `kind`, `name`, `pos`, `ghim`. */
export interface Step {
  id: string
  kind: StepKind
  name?: string
  pos?: [number, number]
  /** Ghim số: khối này là điểm quay lại hợp lệ, nhãn của nó không đổi khi có
   *  đường nối ngược về. Bật/tắt bằng chuột phải. */
  ghim?: boolean
  actions?: unknown[]
  [k: string]: unknown
}

export interface ProcEdge {
  from: string
  to: string
  port: string
  from_side?: string
  to_side?: string
}

/** Nội dung vẽ lên hộp — do `api.describe()` sinh, không phải JS tự ghép. */
export interface CardLine {
  text: string
  /** Loại hành động — giao diện dùng để CHỌN ICON. Python không gắn emoji vào text. */
  type?: string | null
  /** Nằm TRƯỚC mốc "lặp từ đây" -> chạy đúng 1 lần lúc đầu. */
  prologue: boolean
  goal: boolean
}

export interface Card {
  id: string
  kind: StepKind
  title: string
  badges: string[]
  lines: CardLine[]
  so_hanh_dong: number
  co_muc_tieu: boolean
  ghim: boolean
  la_cong: boolean
}

export interface Problem {
  severity: 'error' | 'warning' | string
  message: string
  step?: string | null
  index?: number | null
}

export interface ProcessDoc {
  name: string
  symbol: string
  timeframe: string
  steps: Step[]
  edges: ProcEdge[]
  cards: Card[]
}

export interface ToanHang {
  key: string
  nhan: string
  nhom: string
  tham_so: string[]
}

export interface Bootstrap {
  phien_ban: string
  settings: Record<string, unknown>
  app_dir: string

  kinds: StepKind[]
  kind_labels: Record<string, string>

  /** Chỉ những hành động ĐANG HIỆN. Danh sách đầy đủ ở `action_types_tat_ca`. */
  action_types: string[]
  action_types_tat_ca: string[]
  action_labels: Record<string, string>
  /** Loại hành động đóng vai CỔNG rẽ nhánh. */
  branch_type: string

  timeframes: string[]
  ma_methods: Record<string, string>
  toan_hang: ToanHang[]
  phep_so: Record<string, string>
  cach_tinh: Record<string, string>
  huong: Record<string, string>
  loai_lenh: Record<string, string>
  sua_che_do: Record<string, string>
  sua_can_gia: string[]
  sua_can_phan_tram: string[]

  template_kinds: Record<string, string>
  accent_presets: Record<string, string>
  default_max_nen: number
  max_process_steps: number
}

export interface Reply<T> {
  ok: boolean
  value?: T
  error?: string
  trace?: string
  [k: string]: unknown
}

/** Kết quả `api.validate` — `order` và bạn bè nằm NGANG HÀNG với `value`. */
export interface KetQuaSoat extends Reply<Problem[]> {
  order?: Record<string, string>
  unreachable?: string[]
  entry?: string | null
  /** Cạnh quay lại HỢP LỆ (tới khối đã ghim) — vẽ nét đứt. */
  quay_lai?: [string, string][]
  /** Vòng lặp CHƯA ghim. */
  vong_ho?: [string, string][]
  lech_nhanh?: string[]
  loop?: boolean
}
