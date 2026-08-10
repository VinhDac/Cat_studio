/** Vỏ bọc có kiểu quanh `window.pywebview.api`.
 *
 * Mọi lời gọi Python đi qua đây, không rải `window.pywebview` khắp components — để
 * sau này đổi cách vận chuyển (hoặc giả lập khi test) chỉ phải sửa một file.
 */
import type {
  Bootstrap, Card, KetQuaSoat, ProcessDoc, Reply, Step, Tab,
} from './types'

type PyApi = Record<string, (...a: unknown[]) => Promise<unknown>>

declare global {
  interface Window {
    pywebview?: { api: PyApi }
    __su_kien?: (ten: string, d: unknown) => void
  }
}

/** Chờ cầu nối sẵn sàng.
 *
 * Cố ý KHÔNG dùng sự kiện 'pywebviewready': nếu nó bắn trước khi bundle chạy xong thì
 * listener gắn sau sẽ không bao giờ nhận được, và app treo ở màn hình trắng.
 *
 * ⚠ Và cố ý KHÔNG kiểm `window.pywebview?.api` cho xong: pywebview tạo sẵn
 * `api: {}` — một object RỖNG nhưng TRUTHY — ngay từ khung hình đầu tiên, rồi mới đổ
 * hàm vào sau bằng `_createApi(funcList)`. Kiểm trống rỗng như vậy là qua ngay lập
 * tức, và lời gọi đầu tiên chết với "api.py không có hàm bootstrap" — trông y như lỗi
 * phía Python trong khi Python hoàn toàn ổn.
 * Phải chờ một HÀM CÓ THẬT xuất hiện.
 */
export function cho_cau_noi(timeout = 10000): Promise<void> {
  const t0 = Date.now()
  return new Promise((ok, hong) => {
    const thu = () => {
      if (typeof window.pywebview?.api?.bootstrap === 'function') return ok()
      if (Date.now() - t0 > timeout) return hong(new Error('Không kết nối được tới Python'))
      setTimeout(thu, 40)
    }
    thu()
  })
}

async function goi<T>(ten: string, ...args: unknown[]): Promise<Reply<T>> {
  const api = window.pywebview?.api
  if (!api || typeof api[ten] !== 'function') {
    return { ok: false, error: `api.py không có hàm "${ten}"` }
  }
  try {
    return (await api[ten](...args)) as Reply<T>
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}

export const py = {
  bootstrap: () => goi<Bootstrap>('bootstrap'),
  set_title: (ten: string) => goi<null>('set_title', ten),

  // --- tài liệu ---
  new_process: () => goi<ProcessDoc>('new_process'),
  demo_process: () => goi<ProcessDoc>('demo_process'),
  load_process: (ten: string) => goi<ProcessDoc>('load_process', ten),
  save_process: (doc: ProcessDoc) =>
    goi<{ path: string; name: string }>('save_process', doc),
  open_process_file: () => goi<ProcessDoc>('open_process_file'),
  save_process_file: (doc: ProcessDoc) => goi<{ path: string }>('save_process_file', doc),

  // --- template ---
  list_templates: () => goi<string[]>('list_templates', 'strategy'),
  delete_template: (ten: string) => goi<boolean>('delete_template', 'strategy', ten),

  // --- khối ---
  new_step: (kind: string, actionType?: string) =>
    goi<{ step: Step; card: Card }>('new_step', kind, actionType ?? null),
  clone_steps: (steps: Step[]) =>
    goi<{ steps: Step[]; map: Record<string, string>; cards: Card[] }>('clone_steps', steps),
  describe: (steps: Step[]) => goi<Card[]>('describe', steps),

  /** Nguồn của HUY HIỆU SỐ và của bảng Vấn đề — CẢ HAI sơ đồ, một lời gọi. */
  validate: (doc: ProcessDoc) => goi<never>('validate', doc) as Promise<KetQuaSoat>,

  // --- hộp thoại hành động ---
  save_action: (draft: Record<string, unknown>, tab: Tab) =>
    goi<{ action: Record<string, unknown>; display: string }>('save_action', draft, tab),
  describe_actions: (actions: unknown[]) =>
    goi<{ text: string; type?: string | null }[]>('describe_actions', actions),
  action_defaults: (t: string) => goi<Record<string, unknown>>('action_defaults', t),

  // --- cài đặt ---
  save_settings: (s: Record<string, unknown>) =>
    goi<Record<string, unknown>>('save_settings', s),
  save_ui: (state: Record<string, unknown>) =>
    goi<Record<string, unknown>>('save_ui', state),

  // --- ▶ Chạy → cửa sổ Strategy Tester ---
  mo_tester: (doc: ProcessDoc) => goi<{ da_mo: boolean }>('mo_tester', doc),
  tester_doc: () => goi<ProcessDoc | null>('tester_doc'),

  // --- cửa sổ (thanh tiêu đề tự vẽ) ---
  vung_khong_keo: (vung: number[][], cao: number) => goi<null>('vung_khong_keo', vung, cao),
  keo_cua_so: (ht: number) => goi<boolean>('keo_cua_so', ht),
  cua_so_thu_nho: () => goi<null>('cua_so_thu_nho'),
  cua_so_phong_to: () => goi<boolean>('cua_so_phong_to'),
  cua_so_dang_phong_to: () => goi<boolean>('cua_so_dang_phong_to'),
  cua_so_dong: () => goi<null>('cua_so_dong'),
}
