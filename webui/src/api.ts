/** Vỏ bọc có kiểu quanh `window.pywebview.api`.
 *
 * Mọi lời gọi Python đi qua đây, không rải `window.pywebview` khắp components — để
 * sau này đổi cách vận chuyển (hoặc giả lập khi test) chỉ phải sửa một file.
 */
import type {
  BoNen, Bootstrap, Card, ChangRay, KetQuaChay, KetQuaSoat, KhoDanhMuc, Khung, CuaSoNen,
  LoNhatKy, ProcEdge, ProcessDoc, Reply, Step, Tab, TesterBoot, ThamSo,
  DoanPhat, MucLichSu, ThongKeChay, TrangThaiChay, XemLichSu,
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
export function cho_cau_noi(ham = 'bootstrap', timeout = 10000): Promise<void> {
  const t0 = Date.now()
  return new Promise((ok, hong) => {
    const thu = () => {
      // Chờ ĐÚNG hàm mà trang này sắp gọi: cửa sổ tester có `ApiTester` riêng, KHÔNG
      // có `bootstrap`. Chờ cứng `bootstrap` ở đó là treo 10 giây rồi báo mất kết nối.
      if (typeof window.pywebview?.api?.[ham] === 'function') return ok()
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
  /** Khối + nối của MỘT tab trong một chiến lược đã lưu, để THÊM CHỒNG lên sơ đồ đang
   *  mở. Kèm những tham số đám khối đó thật sự đọc. */
  import_steps: (ten: string, tab: Tab) =>
    goi<{ steps: Step[]; edges: ProcEdge[]; tham_so: ThamSo[]
          bo_start: boolean; ten: string }>('import_steps', ten, tab),
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
  /** `tham_so` = bảng của sơ đồ ĐÍCH. Thiếu nó thì thẻ ghi `nguong_nen_bps = ?`. */
  clone_steps: (steps: Step[], tham_so?: ThamSo[]) =>
    goi<{ steps: Step[]; map: Record<string, string>; cards: Card[] }>(
      'clone_steps', steps, tham_so ?? []),
  describe: (steps: Step[], thamSo: ThamSo[]) =>
    goi<Card[]>('describe', steps, thamSo),

  /** Danh mục kho — engine nào đang nạp, tính được những gì, lưu ở đâu. */
  kho_danh_muc: () => goi<KhoDanhMuc>('kho_danh_muc'),

  /** Nguồn của HUY HIỆU SỐ và của bảng Vấn đề — CẢ HAI sơ đồ, một lời gọi. */
  validate: (doc: ProcessDoc) => goi<never>('validate', doc) as Promise<KetQuaSoat>,

  // --- hộp thoại hành động ---
  save_action: (draft: Record<string, unknown>, tab: Tab, thamSo: ThamSo[]) =>
    goi<{ action: Record<string, unknown>; display: string }>(
      'save_action', draft, tab, thamSo),
  describe_actions: (actions: unknown[]) =>
    goi<{ text: string; type?: string | null }[]>('describe_actions', actions),
  action_defaults: (t: string) => goi<Record<string, unknown>>('action_defaults', t),

  // --- cài đặt ---
  save_settings: (s: Record<string, unknown>) =>
    goi<Record<string, unknown>>('save_settings', s),
  save_ui: (state: Record<string, unknown>) =>
    goi<Record<string, unknown>>('save_ui', state),
  save_test_settings: (t: Record<string, unknown>) =>
    goi<Record<string, unknown>>('save_test_settings', t),

  // --- nguồn nến: tài sản của APP, không của một lần chạy ---
  nguon_liet_ke: () => goi<{ ds: BoNen[]; co_mt5: boolean }>('nguon_liet_ke'),
  nguon_uoc_tinh: (symbol: string, tu: string, den: string) =>
    goi<{ so_nen: number; mb: number; du: boolean }>('nguon_uoc_tinh', symbol, tu, den),
  nguon_tai: (symbol: string, tu: string, den: string) =>
    goi<{ chu: string; ds: BoNen[] }>('nguon_tai', symbol, tu, den),
  nguon_xoa: (symbol: string) => goi<{ ds: BoNen[] }>('nguon_xoa', symbol),
  /** Nối thử MT5 ngay trong Cài đặt — trả lời "vì sao không tải được" trước khi bấm ▶. */
  nguon_kiem_ket_noi: (symbol: string) => goi<{
    noi_duoc: boolean; chu: string; terminal: string; tai_khoan: string
    symbol: string; co_symbol: boolean; goi_y: string[]
  }>('nguon_kiem_ket_noi', symbol),

  // --- ▶ Chạy → cửa sổ Strategy Tester ---
  mo_tester: (doc: ProcessDoc) => goi<{ da_mo: boolean }>('mo_tester', doc),

  // --- cửa sổ (thanh tiêu đề tự vẽ) ---
  vung_khong_keo: (vung: number[][], cao: number) => goi<null>('vung_khong_keo', vung, cao),
  keo_cua_so: (ht: number) => goi<boolean>('keo_cua_so', ht),
  cua_so_thu_nho: () => goi<null>('cua_so_thu_nho'),
  cua_so_phong_to: () => goi<boolean>('cua_so_phong_to'),
  cua_so_dang_phong_to: () => goi<boolean>('cua_so_dang_phong_to'),
  cua_so_dong: () => goi<null>('cua_so_dong'),
}

/** Bề mặt của CỬA SỔ Strategy Tester.
 *
 * Tách hẳn khỏi `py`: cửa sổ đó chạy `ApiTester` bên Python, một lớp cố ý HẸP — không
 * lưu chiến lược, không mở hộp thoại file, không đổi cài đặt. Gọi nhầm `py.*` ở đó sẽ
 * trả "api.py không có hàm …" chứ không âm thầm đụng vào cửa sổ chính.
 *
 * Nhóm `cua_so_*` trùng TÊN với `py` nhưng là hàm KHÁC — mỗi cửa sổ một thể hiện, nên
 * bấm ✕ ở tester chỉ đóng tester. Nhờ vậy `TitleBar` dùng lại được nguyên vẹn.
 */
export const pyTester = {
  bootstrap_tester: () => goi<TesterBoot>('bootstrap_tester'),
  tester_doc: () => goi<ProcessDoc | null>('tester_doc'),


  // --- chạy (luồng nền + tiến trình) ---
  test_chay: (ci: Record<string, unknown>) => goi<boolean>('test_chay', ci),
  test_trang_thai: () => goi<TrangThaiChay>('test_trang_thai'),

  // --- PHÁT LẠI: một lô = 300 khung hình, JS không hỏi gì thêm ---
  test_doan: (j0: number, n: number) => goi<DoanPhat>('test_doan', j0, n),
  /** TOÀN BỘ nến khung `tf` từ đầu dữ liệu tới con trỏ — chart kéo đi đâu cũng đủ. */
  test_nen_tf: (tf: string, j: number) =>
    goi<{ t: number[]; o: number[]; h: number[]; l: number[]; c: number[]; j: number }>(
      'test_nen_tf', tf, j),
  test_luot_ke: (j: number) => goi<{ j: number; i: number }>('test_luot_ke', j),
  /** Ngược lại: sự kiện gần nhất TRƯỚC `j`. `j = -1` nghĩa là phía trước không còn gì. */
  test_luot_truoc: (j: number) => goi<{ j: number; i: number }>('test_luot_truoc', j),
  /** Kéo cửa sổ VẼ lên trước và tô đường mà lượt `i` đã đi — tới tận điều kiện hỏng. */
  test_soi_luot: (i: number) => goi<{ da_ban: boolean }>('test_soi_luot', i),
  /** ĐƯỜNG RAY của một lệnh: nó đã đi qua những khối nào. Gọi MỘT lần cho mỗi lệnh
   *  người dùng rê chuột vào — không nhét vào lô phát, vì 300 lệnh mà 99% không ai xem. */
  test_duong_ray: (lenh_id: string) => goi<{ chang: ChangRay[] }>('test_duong_ray', lenh_id),
  /** Mốc thời gian (unix, giây) → nến M1 CÓ THẬT gần nhất về phía sau. */
  test_tim_moc: (t: number) => goi<{ j: number; t: number }>('test_tim_moc', t),
  /** Tổng kết cả lượt chạy + đường vốn. Gọi MỘT lần lúc mở tab Thống kê. */
  test_thong_ke: () => goi<ThongKeChay>('test_thong_ke'),

  // --- lịch sử các lần chạy ---
  test_lich_su: () =>
    goi<{ ds: MucLichSu[]; dang_xem: string | null }>('test_lich_su'),
  test_lich_su_xem: (ma: string) => goi<XemLichSu>('test_lich_su_xem', ma),
  test_lich_su_chay: (ma: string) => goi<boolean>('test_lich_su_chay', ma),
  test_lich_su_ten: (ma: string, ten: string) =>
    goi<MucLichSu>('test_lich_su_ten', ma, ten),
  test_lich_su_xoa: (ma: string) => goi<boolean>('test_lich_su_xoa', ma),

  // --- đọc dòng thời gian ---
  test_nen: (j: number, so: number) => goi<CuaSoNen>('test_nen', j, so),
  test_khung: (j: number) => goi<Khung>('test_khung', j),
  test_nhat_ky: (tu: number, so: number, chiCoViec: boolean) =>
    goi<LoNhatKy>('test_nhat_ky', tu, so, chiCoViec),
  test_luot: (i: number) => goi<{ j: number; nen: number; tab: string }>('test_luot', i),
  test_ghi_nhat_ky: () => goi<{ duong_dan: string }>('test_ghi_nhat_ky'),
}
