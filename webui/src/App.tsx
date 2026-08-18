import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow, Background, BackgroundVariant, ConnectionMode,
  useNodesState, useEdgesState, addEdge, useReactFlow, ReactFlowProvider, MarkerType,
  useStore,
  type Node, type Edge, type Connection, type NodeChange, type EdgeChange,
} from '@xyflow/react'

import { py, cho_cau_noi } from './api'
import type {
  Bootstrap, Card, ProcEdge, Problem, ProcessDoc, SoDo, SoiKhoi, SoiLuot, Step, StepKind,
  Tab, ThamSo,
} from './types'
import Ribbon, { PillTab, type MucMenu } from './components/Ribbon'
import StepNode from './components/StepNode'
import ActionDialog from './components/ActionDialog'
import SettingsDialog from './components/SettingsDialog'
import TemplatePicker from './components/TemplatePicker'
import KhoDialog from './components/KhoDialog'
import ThamSoDialog from './components/ThamSoDialog'
import ContextMenu, { type MucPhai } from './components/ContextMenu'
import TitleBar, { type NhomMenu } from './components/TitleBar'
import { useKhungCuaSo } from './useKhungCuaSo'

const nodeTypes = { buoc: StepNode }

/** Mũi tên chỉ cần đủ để biết dây chạy về hướng nào. To quá thì nó nặng hơn cả cái
 *  cổng nó cắm vào và hút mắt khỏi nội dung khối. */
const MUI_TEN = { type: MarkerType.ArrowClosed, width: 10, height: 10, color: '#6a6a6a' }

/** 'default' = đường bezier. Cố ý KHÔNG dùng 'smoothstep': hộp cao thấp khác nhau nên
 *  hai đầu nối hiếm khi cùng độ cao, đường bậc thang gãy khúc trông như lỗi vẽ. */
const KIEU_DUONG_NOI = { type: 'default', animated: false, markerEnd: MUI_TEN }

/** Giữ Ctrl HOẶC Shift rồi bấm để chọn thêm khối. Shift cũng là phím quét-khung mặc
 *  định của React Flow, nên Shift+kéo trên nền vẫn quét chọn nhiều khối. */
const PHIM_CHON_NHIEU = ['Control', 'Meta', 'Shift']

/* ---------- đổi qua lại giữa tài liệu của Python và node/edge của React Flow ------- */

function so_do_sang_rf(doc: SoDo): { nodes: Node[]; edges: Edge[] } {
  // ⚠ `?? []` cho CẢ BA, dù `normalize_process` đã bảo đảm chúng có mặt. Một tài liệu
  // thiếu khoá thì đáng ra hiện canvas rỗng, KHÔNG được làm trắng cả cửa sổ — đã cắn:
  // sơ đồ máy vẽ thiếu `cards` và `doc.cards.map` ném
  // `Cannot read properties of undefined`, nuốt luôn cú "Mở sơ đồ" từ cửa sổ RL.
  const theo_id = new Map((doc.cards ?? []).map(c => [c.id, c]))
  const nodes: Node[] = (doc.steps ?? []).map((s, i) => ({
    id: s.id,
    type: 'buoc',
    position: { x: s.pos?.[0] ?? 80 + i * 340, y: s.pos?.[1] ?? 120 },
    data: { step: s, card: theo_id.get(s.id) as Card },
  }))
  const edges: Edge[] = (doc.edges ?? []).map(e => ({
    id: `${e.from}->${e.to}:${e.port}`,
    source: e.from,
    target: e.to,
    // Mặc định phải→trái: luồng chạy trái sang phải, nên đường nối đi ra cạnh phải của
    // hộp trước và vào cạnh trái của hộp sau.
    sourceHandle: e.from_side ?? 'right',
    targetHandle: e.to_side ?? 'left',
    markerEnd: MUI_TEN,
  }))
  return { nodes, edges }
}

function rf_sang_steps(nodes: Node[]): Step[] {
  return nodes.map(n => ({
    ...(n.data as { step: Step }).step,
    pos: [Math.round(n.position.x), Math.round(n.position.y)] as [number, number],
  }))
}

function rf_sang_edges(edges: Edge[]): ProcEdge[] {
  return edges.map(e => ({
    from: e.source,
    to: e.target,
    port: 'out',
    from_side: e.sourceHandle ?? 'right',
    to_side: e.targetHandle ?? 'left',
  }))
}

/* ---------------------------------- Undo ---------------------------------- */

/** Ảnh chụp hoàn tác gom CẢ HAI sơ đồ + tab đang mở.
 *  Chụp riêng từng tab thì Ctrl+Z sau khi đổi tab sẽ hoàn tác nhầm sơ đồ. */
interface Anh { tab: Tab; entry: DoThi; manage: DoThi; ten: string }

const TOI_DA_UNDO = 60

/** Bảng dưới: cao tối thiểu khi kéo, và cao khi đã gập (vừa đủ hàng tab). */
const CAO_TOI_THIEU = 90
const CAO_GAP = 33

/** Bộ nhớ tạm Ctrl+C/Ctrl+V cho KHỐI trên canvas. Giữ cả đường nối GIỮA các khối được
 *  chép — chép 3 khối đang nối nhau mà mất dây thì coi như chép hụt. */
let boNhoKhoi: { steps: Step[]; edges: ProcEdge[] } = { steps: [], edges: [] }

/* --------------------------------- App ----------------------------------- */

interface DoThi { nodes: Node[]; edges: Edge[] }
const RONG: DoThi = { nodes: [], edges: [] }

function Ung() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  /** Tab đang mở. `nodes`/`edges` LUÔN là đồ thị của tab này; tab kia nằm ở `kho`. */
  const [tab, setTab] = useState<Tab>('entry')
  const kho = useRef<Record<Tab, DoThi>>({ entry: RONG, manage: RONG })
  const [ten, setTen] = useState('Chiến lược 1')
  /** Tên template mà tài liệu đang mở NẰM DƯỚI. `null` = chưa lưu bao giờ. Xem `nap`. */
  const [tenTrenDia, setTenTrenDia] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('XAUUSD')
  const [vanDe, setVanDe] = useState<Problem[]>([])
  /* Khối nào đã đi QUA cổng zone. Python tính (`core.khoi_sau_cong_zone`) rồi gửi kèm
     `validate` — hộp thoại chỉ nhận một `Set`, không tự đi lại đồ thị. Hai đoạn mã cùng
     duyệt một sơ đồ là hai luật, và chúng sẽ lệch nhau. */
  const [sauCongZone, setSauCongZone] = useState<Set<string>>(new Set())
  const [tabDuoi, setTabDuoi] = useState<'van-de' | 'nhat-ky'>('van-de')
  const [nhatKy, setNhatKy] = useState<{ gio: string; msg: string; tag?: string | null }[]>([])
  const [sanSang, setSanSang] = useState(false)
  const [trangThai, setTrangThai] = useState('đang khởi động…')
  const [boot, setBoot] = useState<Bootstrap | null>(null)
  const [dangSua, setDangSua] = useState<string | null>(null)
  /** {id khối -> nhãn}. CHUỖI chứ không phải số — có rẽ nhánh rồi thì "4A.2B" mới nói
   *  đủ chuyện. Do Python tính, không phải JS đếm. */
  const [thuTu, setThuTu] = useState<Record<string, string>>({})
  /** Cạnh QUAY LẠI hợp lệ (tới khối đã ghim) — vẽ nét đứt để nhìn ra chỗ nào lặp. */
  const [quayLai, setQuayLai] = useState<Set<string>>(new Set())
  const [vongHo, setVongHo] = useState(0)
  const [panelCao, setPanelCao] = useState(176)
  const [panelGap, setPanelGap] = useState(false)
  /** Đang kéo một đường nối. Bật lên thì MỌI cổng của MỌI khối hiện rõ — không thì
   *  phải đoán xem thả vào đâu được. */
  const [dangNoi, setDangNoi] = useState(false)
  const [moCaiDat, setMoCaiDat] = useState(false)
  const [moKho, setMoKho] = useState(false)
  const [moThamSo, setMoThamSo] = useState(false)
  /** Bảng tham số của chiến lược — hằng số CÓ TÊN, dùng chung cho cả hai sơ đồ. */
  const [thamSo, setThamSo] = useState<ThamSo[]>([])
  /** Tên tham số đang thật sự được khối nào đó dùng — Python tính, JS chỉ hiện. */
  const [tsDangDung, setTsDangDung] = useState<Set<string>>(new Set())
  /** Menu chuột phải đang mở.
   *
   *  Cố ý CHỈ giữ "đang bấm phải vào cái gì", không giữ sẵn danh sách mục menu: mục
   *  menu là những closure đọc `nodes`/`edges`/`dangChon`. Nhét chúng vào state lúc bấm
   *  phải là đóng băng luôn trạng thái của khoảnh khắc đó — bấm phải rồi mới chọn khối,
   *  xong bấm "Chép" sẽ chép nhầm cái đang chọn TRƯỚC đó.
   *
   *  `noi` = vị trí bấm phải theo toạ độ CANVAS, để "Dán" rơi đúng chỗ đã bấm chứ không
   *  rơi vào chỗ con trỏ lúc chọn dòng menu. */
  const [menuPhai, setMenuPhai] = useState<
    { x: number; y: number; loai: 'nen' | 'khoi' | 'day' | 'nhip'; id?: string;
      noi?: { x: number; y: number } } | null>(null)
  const [moPicker, setMoPicker] = useState<
    { tieuDe: string; xong: (t: string) => void } | null>(null)

  const { fitView, zoomIn, zoomOut, setCenter, screenToFlowPosition } = useReactFlow()
  /* Mức thu phóng phải ĐĂNG KÝ THEO DÕI, không gọi getZoom() lúc render: React Flow
     đổi viewport không làm component này vẽ lại, nên con số sẽ đứng im mãi. */
  const mucZoom = useStore(st => st.transform[2])
  /* Kéo + giãn cửa sổ: phải do WEB khởi động, xem chú thích trong useKhungCuaSo. */
  useKhungCuaSo(32)

  const lui = useRef<Anh[]>([])
  const toi = useRef<Anh[]>([])
  const cuoiLog = useRef<HTMLDivElement>(null)
  const [coLui, setCoLui] = useState(false)
  const [coToi, setCoToi] = useState(false)

  /** Đổi màu nhấn tức thì. Chỉ cần ghi đè một biến CSS — đây chính là lý do theme dùng
   *  biến chứ không viết cứng màu ở từng chỗ. */
  const doiMauNgay = useCallback((mau: string) => {
    document.documentElement.style.setProperty('--accent', mau)
    document.documentElement.style.setProperty('--accent-soft', mau + '2b')
  }, [])

  const ghi = useCallback((m: string, tag?: string | null) => {
    const gio = new Date().toLocaleTimeString('vi-VN', { hour12: false })
    setNhatKy(x => [...x.slice(-600), { gio, msg: m, tag }])
  }, [])

  /** Chụp trạng thái TRƯỚC khi thay đổi. Ảnh chụp nguyên khối thay vì tính diff: tài
   *  liệu chỉ vài chục KB, mà diff sai thì undo hỏng theo kiểu rất khó tìm. */
  /** Trạng thái hiện tại của CẢ HAI sơ đồ — tab đang mở lấy từ `nodes`/`edges` sống. */
  const anhHienTai = useCallback((): Anh => ({
    tab, ten,
    entry: tab === 'entry' ? { nodes, edges } : kho.current.entry,
    manage: tab === 'manage' ? { nodes, edges } : kho.current.manage,
  }), [tab, ten, nodes, edges])

  const chup = useCallback(() => {
    lui.current.push(anhHienTai())
    if (lui.current.length > TOI_DA_UNDO) lui.current.shift()
    toi.current = []
    setCoLui(true); setCoToi(false)
  }, [anhHienTai])

  const apDung = useCallback((a: Anh) => {
    kho.current = { entry: a.entry, manage: a.manage }
    setTab(a.tab)
    setNodes(a[a.tab].nodes); setEdges(a[a.tab].edges); setTen(a.ten)
  }, [setNodes, setEdges])

  const hoanTac = useCallback(() => {
    const a = lui.current.pop()
    if (!a) return
    toi.current.push(anhHienTai())
    apDung(a)
    setCoLui(lui.current.length > 0); setCoToi(true)
    setTrangThai('đã hoàn tác')
  }, [anhHienTai, apDung])

  const lamLai = useCallback(() => {
    const a = toi.current.pop()
    if (!a) return
    lui.current.push(anhHienTai())
    apDung(a)
    setCoToi(toi.current.length > 0); setCoLui(true)
    setTrangThai('đã làm lại')
  }, [anhHienTai, apDung])

  /* ---------------- SOI MỘT LƯỢT trên sơ đồ ----------------
   *
   * Nhật ký ở cửa sổ tester trả lời "chuyện gì đã xảy ra" bằng chữ. Câu tiếp theo luôn
   * là "chỗ nào trên sơ đồ", mà dò tay 20 hộp thì mất cả phút. Chuột phải một dòng →
   * cửa sổ này nhảy lên trước và tự tô đúng đường lượt đó đã đi. */
  const [soi, setSoi] = useState<SoiLuot | null>(null)
  const soiRef = useRef<((d: SoiLuot) => void) | null>(null)
  soiRef.current = (d: SoiLuot) => {
    if (d.tab !== tab) doiTab(d.tab)
    setSoi(d)
  }

  /** Cửa sổ RL đẩy sang một sơ đồ máy vẽ. Cùng `ref` một lý do với `soiRef`. */
  const soDoMayRef = useRef<((d: ProcessDoc) => void) | null>(null)
  soDoMayRef.current = (d: ProcessDoc) => {
    // ⭐ ĐI ĐÚNG ĐƯỜNG "mở file", không có nhánh riêng nào: sơ đồ máy vẽ là file chiến
    // lược BÌNH THƯỜNG (§18.6.5). Có `chup()` nên Ctrl+Z lấy lại được bản đang vẽ —
    // thứ máy đẩy sang không được nuốt mất việc người đang làm.
    chup()
    nap(d, `nhận sơ đồ từ RL: ${d.name}`, null)
  }

  useEffect(() => {
    window.__su_kien = (ten, d) => {
      // Qua `ref` chứ không đóng gói `tab`/`doiTab` vào effect: gắn lại listener mỗi
      // lần đổi tab là thừa, mà quên phụ thuộc thì nó tô nhầm tab — bẫy cũ, tránh hẳn.
      if (ten === 'soi_luot') soiRef.current?.(d as SoiLuot)
      else if (ten === 'so_do_may') soDoMayRef.current?.(d as ProcessDoc)
    }
    return () => { window.__su_kien = undefined }
  }, [])

  // Esc để thoát. Soi xong mà không rời ra được thì sơ đồ kẹt trong trạng thái mờ.
  useEffect(() => {
    if (!soi) return
    const f = (e: KeyboardEvent) => { if (e.key === 'Escape') setSoi(null) }
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [soi])

  /** Nạp lại `boot` từ Python.
   *
   *  ⚠ Trước đây `boot` chỉ nạp ĐÚNG MỘT LẦN lúc mở app và không bao giờ mới lại. Hộp
   *  thoại Cài đặt lấy giá trị ban đầu từ nó, nên sửa ngày → Lưu → mở lại là thấy y
   *  nguyên số CŨ, và người dùng kết luận "bấm lưu không lưu được" — trong khi đĩa đã
   *  ghi đúng. Giao diện nói dối về chính thứ nó vừa làm.
   *
   *  `bootstrap` chỉ 1 ms / 7 KB nên nạp lại nguyên cục là rẻ và chắc hơn vá từng mảnh,
   *  và nó đồng bộ luôn danh sách nguồn nến sau khi xoá. */
  const lamMoiBoot = useCallback(async () => {
    const b = await py.bootstrap()
    if (b.ok && b.value) setBoot(b.value)
  }, [])

  /* ------------------------------ khởi động ------------------------------ */
  useEffect(() => {
    (async () => {
      try {
        await cho_cau_noi()
        const b = await py.bootstrap()
        if (!b.ok) { setTrangThai('lỗi bootstrap: ' + b.error); return }
        setBoot(b.value!)
        const s = (b.value!.settings ?? {}) as Record<string, any>
        if (s.accent) doiMauNgay(String(s.accent))
        const ui = (s.ui ?? {}) as Record<string, any>
        if (ui.panel_cao) setPanelCao(Math.max(CAO_TOI_THIEU, Math.min(600, Number(ui.panel_cao))))
        if (ui.panel_gap) setPanelGap(true)

        // ⭐ MỞ APP LÀ MỘT TỜ TRẮNG, LUÔN LUÔN — chỉ có khối Bắt đầu.
        //
        // Trước đây nó tự mở template ĐẦU TIÊN trong kho. Hai chỗ sai: cái "đầu tiên"
        // ấy do thứ tự kho quyết định chứ không phải người dùng chọn, và mở app ra đã
        // thấy sẵn một sơ đồ cũ thì mỗi lần muốn làm việc mới đều phải dọn trước.
        //
        // Cũng KHÔNG mở sơ đồ mẫu: mẫu chỉ để xem thử. Muốn cái cũ thì menu "Mở ▾" —
        // đó là một câu người dùng nói ra, không phải thứ app đoán hộ.
        const r = await py.new_process()
        if (r.ok && r.value) nap(r.value, 'sơ đồ mới', null)
        setSanSang(true)
        setTrangThai('sẵn sàng')
      } catch (e) {
        setTrangThai('không kết nối được Python: ' + String(e))
      }
    })()
    // chỉ chạy 1 lần lúc mở app
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** Hộp cao thấp khác nhau và React Flow chỉ biết chiều cao thật SAU khi vẽ xong.
   *  Gọi `fitView` ngay lúc nạp thì nó tính theo chiều cao 0 và thu phóng ra một con
   *  số vô nghĩa — sơ đồ mẫu 8 khối bị cắt mất nguyên một nhánh ở mép trên.
   *  Nên: nạp xong thì DỰNG CỜ, `useNodesInitialized` báo đo xong mới fit. */
  const canFit = useRef(false)
  /* ĐẾM THẲNG TRONG STORE của React Flow, không dùng `useNodesInitialized`:
     - `useNodesInitialized` trả `true` khi canvas RỖNG, nên ngay sau `nap()` nó đã
       `true` trong khi khối mới còn chưa được vẽ lần nào;
     - mảng `nodes` của `useNodesState` KHÔNG mang `measured` — chiều cao thật nằm
       trong `nodeLookup` của store.
     Đếm số khối ĐÃ CÓ CHIỀU CAO rồi so với số khối đang có: bằng nhau mới là đo xong. */
  const daDo = useStore(s => {
    let n = 0
    for (const nd of s.nodeLookup.values()) if (nd.measured?.height) n++
    return n
  })
  useEffect(() => {
    if (!canFit.current || !nodes.length || daDo !== nodes.length) return
    canFit.current = false
    fitView({ padding: 0.2, duration: 300, maxZoom: 1 })
  }, [daDo, nodes, fitView])

  /** `nha` = tên template mà tài liệu này ĐANG NẰM DƯỚI, `null` là chưa có chỗ nào.
   *
   *  Đây là "đường dẫn file" của Word, và là thứ DUY NHẤT phân biệt được Ctrl+S "lưu
   *  luôn" với Ctrl+S "hỏi tên". Không suy ra được từ `ten`: sơ đồ mới tinh cũng đã có
   *  sẵn tên "Chiến lược 1". Và cũng KHÔNG được suy bằng cách dò xem tên đó có trong kho
   *  chưa — một sơ đồ mới trùng tên với template cũ sẽ lặng lẽ đè mất nó.
   *
   *  Bắt buộc truyền, không cho mặc định: mỗi lần nạp một tài liệu là một lần phải trả
   *  lời "cái này có nhà chưa". Để mặc định thì chỗ quên sẽ im lặng thừa hưởng nhà của
   *  tài liệu trước, và Ctrl+S đè lên một template chẳng liên quan. */
  const nap = useCallback((doc: ProcessDoc, loi: string, nha: string | null) => {
    kho.current = { entry: so_do_sang_rf(doc.entry), manage: so_do_sang_rf(doc.manage) }
    setTab('entry')
    setNodes(kho.current.entry.nodes); setEdges(kho.current.entry.edges)
    setTen(doc.name); setSymbol(doc.symbol)
    setThamSo(doc.tham_so ?? [])
    setTenTrenDia(nha)
    canFit.current = true
    ghi(loi)
  }, [setNodes, setEdges, ghi])

  /** Đổi tab: cất đồ thị đang mở vào kho, lấy đồ thị kia ra.
   *  KHÔNG chụp hoàn tác — đổi tab không sửa gì cả. */
  const doiTab = useCallback((t: Tab) => {
    if (t === tab) return
    kho.current[tab] = { nodes, edges }
    setNodes(kho.current[t].nodes); setEdges(kho.current[t].edges)
    setTab(t)
    canFit.current = true
  }, [tab, nodes, edges, setNodes, setEdges])

  /** Tài liệu đầy đủ: tab đang mở lấy từ node sống, tab kia lấy từ kho. */
  const layDoc = useCallback((): ProcessDoc => {
    const g = (t: Tab) => (t === tab
      ? { steps: rf_sang_steps(nodes), edges: rf_sang_edges(edges), cards: [] }
      : { steps: rf_sang_steps(kho.current[t].nodes),
          edges: rf_sang_edges(kho.current[t].edges), cards: [] })
    return { name: ten, symbol, tham_so: thamSo,
             entry: g('entry'), manage: g('manage') }
  }, [tab, nodes, edges, ten, symbol, thamSo])

  /* --------------------------- soát liên tục -------------------------- */
  useEffect(() => {
    if (!sanSang) return
    const h = setTimeout(async () => {
      const r = await py.validate(layDoc())
      if (!r.ok) return
      // Vấn đề của CẢ HAI tab, không lọc: giấu lỗi tab kia thì bấm ▶ Chạy mới lòi ra.
      setVanDe(r.value ?? [])
      const l = r.luong?.[tab]
      // Số thứ tự do PYTHON tính, bằng chính phép duyệt mà bộ máy chạy dùng — JS không
      // tự đếm, nếu không con số lại nói khác thực tế.
      setThuTu(l?.order ?? {})
      setQuayLai(new Set((l?.quay_lai ?? []).map(([a, b]) => `${a}|${b}`)))
      setVongHo((l?.vong_ho ?? []).length)
      setSauCongZone(new Set(l?.sau_cong_zone ?? []))
      setTsDangDung(new Set(((r as any).tham_so_dang_dung as string[]) ?? []))
    }, 250)   // gộp lại: kéo hộp bắn ra hàng chục thay đổi mỗi giây
    return () => clearTimeout(h)
  }, [nodes, edges, sanSang, tab, layDoc])

  /* Tên chiến lược nằm ở THANH TIÊU ĐỀ cửa sổ. Hoãn 400ms vì gõ từng chữ mà gọi sang
     Python mỗi phím thì phí cầu nối. */
  useEffect(() => {
    if (!sanSang) return
    const h = setTimeout(() => { py.set_title(ten) }, 400)
    return () => clearTimeout(h)
  }, [ten, sanSang])

  /* Ghi nhớ bố cục bảng dưới. Hoãn 500ms: kéo chuột bắn ra hàng chục thay đổi. */
  useEffect(() => {
    if (!sanSang) return
    const h = setTimeout(() => { py.save_ui({ panel_cao: panelCao, panel_gap: panelGap }) }, 500)
    return () => clearTimeout(h)
  }, [panelCao, panelGap, sanSang])

  /** Kéo mép trên bảng dưới để chỉnh chiều cao. Bám theo con trỏ cho tới khi thả, kể cả
   *  khi chuột đi ra ngoài cửa sổ — nếu chỉ nghe trên chính thanh kéo thì kéo nhanh một
   *  cái là mất dấu. */
  const batDauKeoPanel = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    if (panelGap) setPanelGap(false)
    const y0 = e.clientY
    const cao0 = panelGap ? CAO_GAP : panelCao
    const di = (ev: MouseEvent) =>
      setPanelCao(Math.max(CAO_TOI_THIEU, Math.min(600, cao0 + (y0 - ev.clientY))))
    const thoi = () => {
      window.removeEventListener('mousemove', di)
      window.removeEventListener('mouseup', thoi)
      document.body.style.cursor = ''
    }
    document.body.style.cursor = 'ns-resize'
    window.addEventListener('mousemove', di)
    window.addEventListener('mouseup', thoi)
  }, [panelCao, panelGap])

  useEffect(() => {
    if (tabDuoi === 'nhat-ky') cuoiLog.current?.scrollIntoView({ block: 'end' })
  }, [nhatKy, tabDuoi])

  /* ------------------------------ thao tác ------------------------------- */
  const dangChon = useMemo(() => nodes.filter(n => n.selected), [nodes])

  /** Vị trí con trỏ mới nhất, toạ độ màn hình.
   *  Cố ý dùng `useRef` chứ không `useState`: chuột bắn ra hàng trăm sự kiện mỗi giây,
   *  để vào state là vẽ lại toàn bộ canvas theo từng cái nhích chuột. */
  const viTriChuot = useRef<{ x: number; y: number } | null>(null)
  useEffect(() => {
    const f = (e: MouseEvent) => { viTriChuot.current = { x: e.clientX, y: e.clientY } }
    window.addEventListener('mousemove', f)
    return () => window.removeEventListener('mousemove', f)
  }, [])

  /** Điểm dán, theo toạ độ CANVAS (đã tính cả thu phóng và cuộn).
   *  Con trỏ không nằm trên canvas thì lấy GIỮA khung nhìn — điều thật sự cần bảo đảm
   *  là khối dán ra phải NHÌN THẤY ĐƯỢC. */
  const diemDan = useCallback(() => {
    const khung = document.querySelector('.vung-canvas')?.getBoundingClientRect()
    if (!khung) return null
    const c = viTriChuot.current
    const trong = !!c && c.x >= khung.left && c.x <= khung.right
                       && c.y >= khung.top && c.y <= khung.bottom
    return screenToFlowPosition(trong ? c! : {
      x: khung.left + khung.width / 2, y: khung.top + khung.height / 2,
    })
  }, [screenToFlowPosition])

  const themKhoi = useCallback(async (kind: StepKind, loaiHD?: string,
                                      taiDay?: { x: number; y: number },
                                      moSua = true) => {
    const r = await py.new_step(kind, loaiHD)
    if (!r.ok || !r.value) { ghi('không tạo được khối: ' + r.error, 'err'); return }
    chup()
    const { step, card } = r.value
    // `taiDay` = chỗ vừa bấm chuột phải. Nút trên ribbon thì không có "chỗ nào" nên vẫn
    // xếp tiếp về bên phải khối xa nhất, đúng chiều chạy trái→phải.
    const x = taiDay ? Math.round(taiDay.x)
                     : (nodes.length ? Math.max(...nodes.map(n => n.position.x)) + 380 : 80)
    const y = taiDay ? Math.round(taiDay.y)
                     : (nodes.length ? nodes[nodes.length - 1].position.y : 200)
    step.pos = [x, y]
    setNodes(n => [...n.map(k => ({ ...k, selected: false })),
      { id: step.id, type: 'buoc', position: { x, y }, data: { step, card }, selected: true }])
    ghi(`thêm khối ${card.title}`)
    // Mở luôn hộp thoại của khối vừa thêm: Vòng/Nhóm mới là RỖNG, còn HĐ lẻ thì mặc
    // định chưa nói lên điều gì — cả hai đều vô nghĩa cho tới khi cấu hình. Bắt người
    // dùng đi tìm rồi double-click là một bước thừa. Chỉ muốn cái khối thôi thì Esc.
    if (moSua) setDangSua(step.id)
  }, [nodes, chup, setNodes, ghi])

  const xoa = useCallback(() => {
    // Khối Bắt đầu không xoá được: nó là điểm neo đánh số, mất nó là một vòng lặp nối
    // ngược lên trên có thể làm mọi khối mất số (xem core.md §3.3).
    const bo = new Set(dangChon
      .filter(n => (n.data as { step: Step }).step.kind !== 'start').map(n => n.id))
    if (!bo.size) return
    chup()
    setNodes(n => n.filter(k => !bo.has(k.id)))
    setEdges(e => e.filter(k => !bo.has(k.source) && !bo.has(k.target)))
    ghi(`xoá ${bo.size} khối`)
  }, [dangChon, chup, setNodes, setEdges, ghi])

  const doiTen = useCallback(() => {
    const n = dangChon[0]
    if (!n) return
    const cu = (n.data as { card: Card }).card.title
    const moi = window.prompt('Tên khối:', cu)
    if (moi == null) return
    chup()
    setNodes(ds => ds.map(k => {
      if (k.id !== n.id) return k
      const d = k.data as { step: Step; card: Card }
      const t = moi.trim() || cu
      return { ...k, data: { step: { ...d.step, name: t }, card: { ...d.card, title: t } } }
    }))
  }, [dangChon, chup, setNodes])

  /** ⟲ GHIM SỐ — bật/tắt cho mọi khối đang chọn.
   *
   *  Khối đã ghim là một ĐIỂM QUAY LẠI hợp lệ: đường nối ngược về nó không làm đổi số
   *  của nó và không còn bị báo là vòng lặp ngoài ý muốn. Đây là cách nói với app
   *  "chỗ này tôi CỐ Ý lặp lại". */
  const doiGhim = useCallback(() => {
    if (!dangChon.length) return
    const ids = new Set(dangChon.map(n => n.id))
    // Nhiều khối đang chọn mà trạng thái lẫn lộn -> ghim HẾT (thay vì đảo từng cái,
    // vốn để lại đúng cái mớ lẫn lộn ban đầu).
    const bat = !dangChon.every(n => (n.data as { step: Step }).step.ghim)
    chup()
    setNodes(ds => ds.map(k => {
      if (!ids.has(k.id)) return k
      const d = k.data as { step: Step; card: Card }
      return {
        ...k,
        data: { step: { ...d.step, ghim: bat }, card: { ...d.card, ghim: bat } },
      }
    }))
    ghi(bat ? `ghim số ${ids.size} khối — quay về đây vẫn giữ đúng số`
            : `bỏ ghim ${ids.size} khối`, 'ok')
  }, [dangChon, chup, setNodes, ghi])

  /** NHỊP CHẠY của sơ đồ — sống trên khối Bắt đầu, không phải một ô ở góc ribbon.
   *
   *  Chữ trên khối do Python sinh từ khoá `nhip`, nên đổi ở đây là khối đổi theo ngay.
   *  Bản cũ ghi thẳng "M5" vào TÊN khối, không nối với `doc.timeframe` bằng gì cả —
   *  đổi dropdown thì khối vẫn ghi M5, tức sơ đồ nói dối. */
  const doiNhip = useCallback(async (id: string, nhip: string) => {
    const k = nodes.find(n => n.id === id)
    if (!k) return
    const st = { ...(k.data as { step: Step }).step, nhip }
    // Nhờ Python dựng lại thẻ: chữ trên hộp là việc của lõi, JS không tự ghép.
    const r = await py.describe([st], thamSo)
    chup()
    setNodes(ds => ds.map(n => n.id === id
      ? { ...n, data: { step: st, card: r.value?.[0] ?? (n.data as { card: Card }).card } }
      : n))
    ghi(`Nhịp sơ đồ ${tab === 'entry' ? 'Entry' : 'Manage'}: mỗi nến ${nhip}`)
  }, [nodes, thamSo, chup, setNodes, ghi, tab])


  /** Ctrl+D: nhân bản MỌI khối đang chọn, kèm cả dây nối GIỮA chúng. Chỉ nhân bản khối
   *  đầu tiên thì chọn 3 khối bấm Ctrl+D ra 1 khối — vừa sai vừa im lặng. */
  const nhanBan = useCallback(async () => {
    const nguon = dangChon.filter(n => (n.data as { step: Step }).step.kind !== 'start')
    if (!nguon.length) return
    const goc = nguon.map(n => ({
      ...JSON.parse(JSON.stringify((n.data as { step: Step }).step)),
      pos: [Math.round(n.position.x), Math.round(n.position.y)] as [number, number],
    }))
    const r = await py.clone_steps(goc)          // id do core cấp, JS không tự nặn
    if (!r.ok || !r.value) { ghi('không nhân bản được: ' + r.error, 'err'); return }
    const { steps: moi, map, cards } = r.value
    chup()
    const mot = moi.length === 1
    setNodes(ds => [...ds.map(k => ({ ...k, selected: false })), ...moi.map((st, i) => {
      const card = mot ? { ...cards[i], title: cards[i].title + ' (bản sao)' } : cards[i]
      if (mot) st.name = card.title
      const p: [number, number] = [(st.pos?.[0] ?? 80) + 40, (st.pos?.[1] ?? 120) + 60]
      return {
        id: st.id, type: 'buoc', position: { x: p[0], y: p[1] },
        data: { step: { ...st, pos: p }, card }, selected: true,
      }
    })])
    const idChon = new Set(nguon.map(n => n.id))
    setEdges(e => [...e, ...rf_sang_edges(e)
      .filter(x => idChon.has(x.from) && idChon.has(x.to))
      .filter(x => map[x.from] && map[x.to])
      .map(x => ({
        id: `${map[x.from]}->${map[x.to]}:${Date.now()}${Math.round(performance.now())}`,
        source: map[x.from], target: map[x.to],
        sourceHandle: x.from_side ?? 'right', targetHandle: x.to_side ?? 'left',
        markerEnd: MUI_TEN,
      }))])
    ghi(`nhân bản ${moi.length} khối`)
  }, [dangChon, chup, setNodes, setEdges, ghi])

  /** Ghi khối đã sửa trở lại node, và LẤY LẠI nội dung hộp từ Python — không tự dựng
   *  lại thẻ ở JS, nếu không hộp sẽ mô tả khác với những gì core thực sự hiểu. */
  const ghiBuoc = useCallback(async (s: Step) => {
    const r = await py.describe([s], thamSo)
    const card = r.ok ? r.value![0] : null
    chup()
    setNodes(ds => ds.map(k => (k.id === s.id
      ? { ...k, data: { step: s, card: card ?? (k.data as { card: Card }).card } }
      : k)))
    setDangSua(null)
    ghi(`sửa "${card?.title ?? s.name ?? s.id}"`)
  }, [chup, setNodes, ghi, thamSo])

  /* ------------------------------- chép / dán ----------------------------- */
  const chepKhoi = useCallback(() => {
    if (!dangChon.length) return
    const idChon = new Set(dangChon.map(n => n.id))
    boNhoKhoi = {
      // Lấy `pos` từ VỊ TRÍ THẬT của node lúc này, không lấy `step.pos` trong data: kéo
      // khối chỉ đổi `node.position`, còn `step.pos` mãi tới lúc lưu/soát mới được ghi
      // lại. Chép sau khi kéo mà dùng `step.pos` là lấy nhầm chỗ cũ.
      steps: dangChon.map(n => ({
        ...JSON.parse(JSON.stringify((n.data as { step: Step }).step)),
        pos: [Math.round(n.position.x), Math.round(n.position.y)] as [number, number],
      })),
      edges: rf_sang_edges(edges).filter(e => idChon.has(e.from) && idChon.has(e.to)),
    }
    ghi(`đã chép ${dangChon.length} khối`)
  }, [dangChon, edges, ghi])

  /** Thả một CỤM khối lên canvas: id mới, giữ nối trong cụm, chọn sẵn cả cụm, một
   *  Ctrl+Z hoàn tác cả mẻ.
   *
   *  Tách ra vì có hai lối vào — dán từ bộ nhớ (Ctrl+V) và **thêm khối từ một chiến
   *  lược khác**. Viết hai lần thì sớm muộn một bên quên remap id hoặc quên `chup()`. */
  const thaCum = useCallback(async (
    buoc: Step[], canh: ProcEdge[], taiDay?: { x: number; y: number }, ts?: ThamSo[],
  ) => {
    if (!buoc.length) return 0
    // Bảng tham số phải đi kèm, nếu không thẻ dựng ra ghi `nguong_nen = ?`. Với lần
    // NHẬP thì phải là bảng ĐÃ GỘP — tham số mới thêm chưa nằm trong `thamSo` của lần
    // render này.
    const r = await py.clone_steps(buoc, ts ?? thamSo)
    if (!r.ok || !r.value) { ghi('không dán được: ' + r.error, 'err'); return 0 }
    const { steps: moi, map, cards } = r.value
    chup()
    // Dời cả CỤM cho góc trên-trái của nó rơi vào con trỏ, giữ nguyên khoảng cách tương
    // đối giữa các khối — dán 3 khối đang nối thành chuỗi mà mỗi cái văng một nơi thì
    // coi như phải xếp lại từ đầu.
    const goc = taiDay ?? diemDan()
    const x0 = Math.min(...moi.map(s => s.pos?.[0] ?? 80))
    const y0 = Math.min(...moi.map(s => s.pos?.[1] ?? 120))
    const dx = goc ? Math.round(goc.x - x0) : 40
    const dy = goc ? Math.round(goc.y - y0) : 40
    setNodes(ds => [...ds.map(k => ({ ...k, selected: false })), ...moi.map((st, i) => {
      const p: [number, number] = [(st.pos?.[0] ?? 80) + dx, (st.pos?.[1] ?? 120) + dy]
      return {
        id: st.id, type: 'buoc', position: { x: p[0], y: p[1] },
        data: { step: { ...st, pos: p }, card: cards[i] }, selected: true,
      }
    })])
    // Nối lại theo bảng tra id cũ→mới. Không remap là đường nối trỏ về bản GỐC.
    setEdges(e => [...e, ...canh
      .filter(x => map[x.from] && map[x.to])
      .map(x => ({
        id: `${map[x.from]}->${map[x.to]}:${Date.now()}${Math.round(performance.now())}`,
        source: map[x.from], target: map[x.to],
        sourceHandle: x.from_side ?? 'right', targetHandle: x.to_side ?? 'left',
        markerEnd: MUI_TEN,
      }))])
    return moi.length
  }, [chup, setNodes, setEdges, ghi, diemDan, thamSo])

  /** Ctrl+V: dán ra bản sao có id MỚI, đặt NGAY CHỖ CON TRỎ, nối lại y như bản gốc. */
  const danKhoi = useCallback(async (taiDay?: { x: number; y: number }) => {
    if (!boNhoKhoi.steps.length) return
    const n = await thaCum(boNhoKhoi.steps, boNhoKhoi.edges, taiDay)
    if (n) ghi(`đã dán ${n} khối`)
  }, [thaCum, ghi])

  /** THÊM CHỒNG khối từ một chiến lược đã lưu — không thay sơ đồ đang mở.
   *
   *  Khối vào không có đường nối nào từ khối Bắt đầu, nên nó **không có số** và bảng Vấn
   *  đề gọi nó là "không bao giờ chạy tới" (mức cảnh báo, ▶ Chạy vẫn bấm được). Nối vào
   *  là số hiện ra. Đó là hệ quả của cơ chế đánh số, không phải thứ phải cài riêng.
   *
   *  ⚠ Tham số phải đi theo. Khối tham chiếu tham số bằng TÊN: thiếu một cái thì khối
   *  trông vẫn bình thường trên canvas nhưng bấm ▶ mới ném "Bảng tham số thiếu …", và
   *  không ai đoán ra vì sao. Tên ĐÃ CÓ thì GIỮ NGUYÊN giá trị hiện tại — đè lên là lặng
   *  lẽ đổi hành vi của cả chiến lược đang làm dở chỉ vì vừa nhập một khối. */
  const themKhoiTu = useCallback(async (ten: string) => {
    const r = await py.import_steps(ten, tab)
    if (!r.ok || !r.value) { ghi('không nhập được: ' + r.error, 'err'); return }
    const { steps: buoc, edges: canh, tham_so: ts, bo_start } = r.value
    if (!buoc.length) {
      ghi(`"${ten}" không có khối nào ở sơ đồ ${tab === 'entry' ? 'Entry' : 'Manage'}`, 'err')
      return
    }
    const co = new Map(thamSo.map(t => [t.ten, t]))
    const them = ts.filter(t => !co.has(t.ten))
    const giu = ts.filter(t => co.has(t.ten)
                               && String(co.get(t.ten)!.gia_tri) !== String(t.gia_tri))
    const tsMoi = [...thamSo, ...them]
    if (them.length) setThamSo(tsMoi)

    const n = await thaCum(buoc, canh, undefined, tsMoi)
    if (!n) return

    const chu = [`đã thêm ${n} khối từ "${ten}"`]
    if (bo_start) chu.push('bỏ khối Bắt đầu của nguồn')
    if (them.length) {
      chu.push(`thêm ${them.length} tham số (`
               + them.map(t => `${t.ten} = ${t.gia_tri}`).join(' · ') + ')')
    }
    if (giu.length) {
      chu.push('giữ nguyên ' + giu.map(t =>
        `${t.ten} = ${co.get(t.ten)!.gia_tri} (nguồn ghi ${t.gia_tri})`).join(' · '))
    }
    ghi(chu.join(' · '))
  }, [tab, thamSo, thaCum, ghi])

  /* ------------------------------ tài liệu -------------------------------- */
  const soDoMoi = useCallback(async () => {
    const r = await py.new_process()
    if (!r.ok || !r.value) { ghi('không tạo được sơ đồ mới: ' + r.error, 'err'); return }
    chup()
    nap(r.value, 'sơ đồ mới — chỉ có khối Bắt đầu', null)
  }, [chup, nap, ghi])

  const moMau = useCallback(async () => {
    const r = await py.demo_process()
    if (!r.ok || !r.value) { ghi('không mở được sơ đồ mẫu: ' + r.error, 'err'); return }
    chup()
    nap(r.value, 'mở sơ đồ mẫu Compress', null)
  }, [chup, nap, ghi, fitView])

  /** Ghi thật xuống kho template. Trả `true` nếu xong. */
  const ghiTemplate = useCallback(async (t: string) => {
    const r = await py.save_process({ ...layDoc(), name: t })
    if (!r.ok) { ghi('lưu hỏng: ' + r.error, 'err'); return false }
    setTen(t); setTenTrenDia(t)
    ghi(`đã lưu "${t}"`, 'ok'); setTrangThai('đã lưu')
    return true
  }, [layDoc, ghi])

  /** `Ctrl+Shift+S` — LƯU THÀNH: luôn hỏi tên, tạo một template mới.
   *
   *  Sau đó bản đang mở CHUYỂN sang sống dưới tên mới, đúng như Word: bạn đang sửa tiếp
   *  bản sao, không phải bản gốc. Bản gốc nằm nguyên chỗ cũ. */
  const luuThanh = useCallback(async () => {
    const t = window.prompt('Lưu chiến lược thành tên:', ten)?.trim()
    if (!t) return
    // ⚠ Gõ trúng tên đã có thì PHẢI hỏi. `save_process` ghi đè không nói một lời, mà đây
    // là cửa duy nhất người dùng tự tay gõ ra một cái tên — gõ trùng là chuyện thường.
    if (t !== tenTrenDia) {
      const ds = await py.list_templates()
      if (ds.ok && (ds.value ?? []).includes(t)
          && !window.confirm(`Đã có chiến lược "${t}". Ghi đè lên nó?`)) return
    }
    await ghiTemplate(t)
  }, [ten, tenTrenDia, ghiTemplate])

  /** `Ctrl+S` — LƯU. Đã có nhà thì ghi thẳng, không hỏi gì; chưa có thì hoá thành
   *  "Lưu thành". Đúng cơ chế Word, và đó là cả điểm của `tenTrenDia`.
   *
   *  ⚠ Ghi theo tên ĐANG HIỆN trong ô trên ribbon, không theo `tenTrenDia`. Ô đó sửa
   *  được và nhìn thấy được, nên sửa xong mà Ctrl+S vẫn đè lên tên cũ là ô tên nói dối.
   *  Sửa tên rồi Ctrl+S ⇒ ra một template mới, bản cũ còn nguyên. */
  const luu = useCallback(async () => {
    if (!tenTrenDia) { await luuThanh(); return }
    await ghiTemplate(ten)
  }, [tenTrenDia, ten, luuThanh, ghiTemplate])

  const moChienLuoc = useCallback(async (t: string) => {
    const r = await py.load_process(t)
    if (!r.ok || !r.value) { ghi('mở hỏng: ' + r.error, 'err'); return }
    chup()
    nap(r.value, `mở "${t}"`, t)
  }, [chup, nap, ghi, fitView])

  const moFile = useCallback(async () => {
    const r = await py.open_process_file()
    if (!r.ok) { if (r.error) ghi('mở hỏng: ' + r.error, 'err'); return }
    chup()
    nap(r.value!, 'mở từ file ngoài', null)
  }, [chup, nap, ghi, fitView])

  const luuRaFile = useCallback(async () => {
    const r = await py.save_process_file(layDoc())
    if (r.ok) ghi(`đã lưu ra ${r.value?.path}`, 'ok')
    else if (r.error) ghi('lưu hỏng: ' + r.error, 'err')
  }, [layDoc, ghi])

  /** Đặt khối đang chọn làm khối CHẠY ĐẦU TIÊN.
   *
   *  Phải làm cả hai việc: gỡ mọi đường nối đi vào nó, và đưa nó lên đầu danh sách.
   *  Chỉ làm một trong hai thì bấm xong không thấy gì đổi — kiểu khó chịu nhất.
   *  (Khi sơ đồ có khối Bắt đầu thì khối đó luôn thắng — nút này chỉ có nghĩa cho
   *  những sơ đồ cũ chưa có khối Bắt đầu.) */
  const datBatDau = useCallback(() => {
    const n = dangChon[0]
    if (!n) return
    chup()
    setEdges(e => e.filter(k => k.target !== n.id))
    setNodes(ds => [n, ...ds.filter(k => k.id !== n.id)])
    ghi(`đặt "${(n.data as { card: Card }).card.title}" làm khối bắt đầu`, 'ok')
  }, [dangChon, chup, setNodes, setEdges, ghi])

  /* ------------------------------- nối dây -------------------------------- */
  const noi = useCallback((c: Connection) => {
    if (c.source === c.target) return          // tự nối vào chính mình thì vô nghĩa
    // Khối Bắt đầu không nhận đường vào — chặn ngay lúc thả chuột thay vì để bảng Vấn
    // đề báo sau.
    const dich = nodes.find(n => n.id === c.target)
    if (dich && (dich.data as { step: Step }).step.kind === 'start') {
      ghi('khối Bắt đầu không nhận đường nối đi vào — nó là điểm neo đánh số', 'warn')
      return
    }
    chup()
    setEdges(e => addEdge({ ...c, id: `${c.source}->${c.target}:${Date.now()}`,
                            markerEnd: MUI_TEN }, e))
  }, [nodes, chup, setEdges, ghi])

  /** Double-click lên dây = huỷ kết nối. Cùng quy ước với khối: nhấp đúp lên thứ gì thì
   *  tác động lên chính thứ đó. Có `chup()` nên lỡ tay thì Ctrl+Z lấy lại được. */
  const xoaDay = useCallback((idDay: string) => {
    chup()
    setEdges(e => e.filter(k => k.id !== idDay))
    ghi('đã huỷ 1 kết nối (Ctrl+Z để lấy lại)')
  }, [chup, setEdges, ghi])

  const huyNoi = useCallback((ev: React.MouseEvent, d: Edge) => {
    ev.stopPropagation()
    xoaDay(d.id)
  }, [xoaDay])

  /** Gỡ MỌI dây chạm tới các khối này. Khối mất hết dây thì thành không-ai-dẫn-tới:
   *  huy hiệu về "–" và bảng Vấn đề báo "không bao giờ chạy tới". Nên đây chính là cách
   *  "tắt tạm" một khối mà vẫn giữ nó trên canvas — không cần cờ bật/tắt riêng. */
  const ngatKetNoi = useCallback((ids: string[]) => {
    const bo = new Set(ids)
    const dinh = edges.filter(k => bo.has(k.source) || bo.has(k.target))
    if (!dinh.length) return
    chup()
    setEdges(e => e.filter(k => !bo.has(k.source) && !bo.has(k.target)))
    ghi(`đã ngắt ${dinh.length} kết nối (Ctrl+Z để lấy lại)`)
  }, [edges, chup, setEdges, ghi])

  /* ------------------------------- ▶ Chạy --------------------------------- */
  const chay = useCallback(async () => {
    const r = await py.mo_tester(layDoc())
    if (!r.ok) {
      const ds = ((r as any).loi as Problem[] | undefined)?.map(p => '✖ ' + p.message).join('\n\n')
      window.alert((r.error ?? 'không chạy được') + (ds ? '\n\n' + ds : ''))
      setTabDuoi('van-de')
      return
    }
    ghi('▶ mở Strategy Tester', 'ok')
    setTrangThai('đã mở Strategy Tester')
  }, [layDoc, ghi])

  /* -------------------------------- ● Live --------------------------------
   *
   * ⚠ LUÔN đi qua hộp thoại chốt, kể cả khi vào bằng Ctrl+L. Đây là cửa duy nhất giữa
   * một sơ đồ đang vẽ dở và một kết nối tiêu tiền thật — không có đường tắt nào, vì
   * đường tắt là thứ người ta dùng đúng lúc vội, mà vội là lúc dễ sai nhất. */
  const moLive = useCallback(async () => {
    // Mở THẲNG cửa sổ Live. Cổng chốt (chọn chiến lược · symbol · kiểm kết nối) nằm
    // trong chính cửa sổ đó — cửa sổ vẽ không gánh hộp thoại nào cả.
    const r = await py.mo_live(layDoc())
    if (!r.ok) { window.alert(r.error ?? 'không mở được Live'); return }
    ghi('● mở cửa sổ Live', 'ok')
    setTrangThai('đã mở Live')
  }, [layDoc, ghi])

  /* --------------------------------- ✦ RL ---------------------------------
   *
   * ⚠ KHÔNG truyền sơ đồ đang vẽ: cửa sổ RL không chạy nó, nó tự SINH ra sơ đồ
   * (core.md §18.6). Nút này chỉ mở cửa. */
  const moRL = useCallback(async () => {
    const r = await py.mo_rl()
    if (!r.ok) { window.alert(r.error ?? 'không mở được RL'); return }
    ghi('✦ mở cửa sổ RL', 'ok')
    setTrangThai('đã mở RL')
  }, [ghi])

  /** Vẽ lại thẻ CẢ HAI sơ đồ theo bảng tham số `ds`. Tách ra vì hai chỗ cần: sửa bảng
   *  tham số, và đặt tên cho một con số (chỗ đó còn sửa cả các bước trước khi gọi).
   *
   *  `tu` cho phép truyền thẳng bảng nút MỚI vào: `nodes` ở đây là giá trị của lần
   *  render này, `setNodes` vừa gọi xong chưa kịp phản ánh. */
  const veLaiThe = useCallback(async (ds: ThamSo[], tu?: Map<Tab, Node[]>) => {
    for (const t of ['entry', 'manage'] as Tab[]) {
      const ns = tu?.get(t) ?? (t === tab ? nodes : kho.current[t].nodes)
      const r = await py.describe(ns.map(n => (n.data as { step: Step }).step), ds)
      if (!r.ok) continue
      const the = new Map((r.value ?? []).map(c => [c.id, c]))
      const moi = ns.map(n => (the.has(n.id)
        ? { ...n, data: { ...(n.data as object), card: the.get(n.id) as Card } } : n))
      if (t === tab) setNodes(moi); else kho.current[t] = { ...kho.current[t], nodes: moi }
    }
  }, [tab, nodes, setNodes])

  /** Đổi bảng tham số — vẽ lại thẻ CẢ HAI sơ đồ, vì một tham số có thể được dùng ở
   *  bất cứ đâu và chữ trên hộp phải đổi theo ngay. */
  const luuThamSo = useCallback(async (ds: ThamSo[]) => {
    chup()
    setThamSo(ds)
    setMoThamSo(false)
    await veLaiThe(ds)
    ghi(`cập nhật ${ds.length} tham số`, 'ok')
  }, [chup, veLaiThe, ghi])

  /** ĐẶT TÊN CHO MỘT CON SỐ — một nút, không phải một quy trình.
   *
   *  Python đã nói sẵn con số nằm ở NHỮNG Ô NÀO (`dat_ten.cho`), nên ở đây chỉ việc đi
   *  theo đường dẫn và thay số bằng tên. Cố ý KHÔNG quét lại sơ đồ ở phía giao diện:
   *  hai đoạn mã quét cùng một thứ là hai luật, và sớm muộn chúng sẽ lệch nhau.
   *
   *  Thay HẾT mọi chỗ chứ không chỉ chỗ đang bấm — để lại một chỗ gõ tay thì cảnh báo
   *  biến mất nhưng cái bẫy vẫn còn nguyên, mà lần này còn khó thấy hơn. */
  const datTenCho = useCallback(async (dt: NonNullable<Problem['dat_ten']>) => {
    /* Tên gợi ý có thể đã có sẵn trong bảng — hai trường hợp KHÁC HẲN nhau:
         cùng giá trị  → DÙNG LẠI dòng đó. `chu_ky_atr = 14` engine luôn đòi phải có;
                         tạo thêm `chu_ky_atr_2 = 14` là đúng cái rác ta đang dọn.
         khác giá trị  → thêm hậu tố. Đè lên là âm thầm đổi một thứ người dùng không hỏi. */
    const cu = thamSo.find(t => t.ten === dt.goi_y)
    let ten = dt.goi_y
    const dungLai = !!cu && Number(cu.gia_tri) === dt.gia_tri
    if (cu && !dungLai) {
      const dangCo = new Set(thamSo.map(t => t.ten))
      for (let i = 2; dangCo.has(ten); i++) ten = `${dt.goi_y}_${i}`
    }

    chup()
    const doi = new Map<Tab, Node[]>()
    for (const t of ['entry', 'manage'] as Tab[]) {
      const ns = t === tab ? nodes : kho.current[t].nodes
      const can = dt.cho.filter(c => c.tab === t)
      if (!can.length) { doi.set(t, ns); continue }
      doi.set(t, ns.map(n => {
        const duong = can.filter(c => c.step === n.id)
        if (!duong.length) return n
        const st = JSON.parse(JSON.stringify((n.data as { step: Step }).step)) as Step
        for (const c of duong) {
          let o: Record<string, unknown> = st as unknown as Record<string, unknown>
          for (const k of c.duong.slice(0, -1)) o = o?.[k] as Record<string, unknown>
          if (o) o[c.duong[c.duong.length - 1]] = ten
        }
        return { ...n, data: { ...(n.data as object), step: st } }
      }))
    }
    for (const t of ['entry', 'manage'] as Tab[]) {
      const ns = doi.get(t) as Node[]
      if (t === tab) setNodes(ns); else kho.current[t] = { ...kho.current[t], nodes: ns }
    }

    const ds = dungLai ? thamSo
      : [...thamSo, { ten, nhan: dt.nhan, gia_tri: dt.gia_tri,
                      don_vi: dt.don_vi, ghi_chu: '' }]
    setThamSo(ds)
    await veLaiThe(ds, doi)
    ghi(`${dungLai ? 'dùng lại' : 'đặt'} tên "${ten}" = ${dt.gia_tri}`
        + ` cho ${dt.cho.length} chỗ`, 'ok')
  }, [chup, tab, nodes, setNodes, thamSo, veLaiThe, ghi])

  /* --------------------------- menu chuột phải --------------------------- */

  /** Bấm phải vào khối PHẢI CHỌN khối đó trước — không thì mục "Chép" sẽ chép cái đang
   *  chọn TỪ TRƯỚC ĐÓ, sai một cách rất khó nhận ra vì menu vẫn hiện đúng chỗ.
   *
   *  Ngoại lệ: khối đó đã nằm trong nhóm đang chọn thì giữ nguyên cả nhóm — người dùng
   *  cố ý chọn nhiều rồi mới bấm phải, phá nhóm đi là làm hỏng ý định của họ. */
  const bamPhaiKhoi = useCallback((ev: React.MouseEvent, n: Node) => {
    ev.preventDefault()
    if (!nodes.some(k => k.id === n.id && k.selected)) {
      setNodes(ds => ds.map(k => ({ ...k, selected: k.id === n.id })))
    }
    setMenuPhai({ x: ev.clientX, y: ev.clientY, loai: 'khoi', id: n.id,
                  noi: screenToFlowPosition({ x: ev.clientX, y: ev.clientY }) })
  }, [nodes, setNodes, screenToFlowPosition])

  const bamPhaiNen = useCallback((ev: React.MouseEvent | MouseEvent) => {
    ev.preventDefault()
    setMenuPhai({ x: ev.clientX, y: ev.clientY, loai: 'nen',
                  noi: screenToFlowPosition({ x: ev.clientX, y: ev.clientY }) })
  }, [screenToFlowPosition])

  const bamPhaiDay = useCallback((ev: React.MouseEvent, d: Edge) => {
    ev.preventDefault()
    setMenuPhai({ x: ev.clientX, y: ev.clientY, loai: 'day', id: d.id })
  }, [])

  /** Danh sách nhịp của một khối Bắt đầu. Dùng CHUNG cho submenu chuột phải và cho nhấp
   *  đúp — hai lối vào cùng một danh sách thì không thể lệch nhau. */
  const mucNhip = useCallback((id: string): MucPhai[] => {
    const nay = (nodes.find(n => n.id === id)?.data as { step: Step } | undefined)?.step.nhip
    return (boot?.timeframes ?? []).map(t => ({
      ten: (t === nay ? '● ' : '○ ') + t,
      onClick: () => void doiNhip(id, t),
    }))
  }, [nodes, boot, doiNhip])

  /** Các mục của menu — dựng LÚC RENDER nên luôn đọc trạng thái mới nhất. */
  const mucMenuPhai = useMemo<MucPhai[]>(() => {
    if (!menuPhai) return []
    const taiDay = menuPhai.noi
    const soChep = boNhoKhoi.steps.length
    const mucDan: MucPhai = {
      ten: soChep ? `Dán (${soChep} khối)` : 'Dán', icon: 'paste',
      tat: !soChep, viSao: 'chưa chép khối nào',
      onClick: () => danKhoi(taiDay),
    }

    // Nhấp đúp khối Bắt đầu: mở THẲNG danh sách nhịp, không kèm mục nào khác. Người ta
    // nhấp đúp vì muốn đổi nhịp, dội cả menu chuột phải ra là bắt họ tìm lại.
    if (menuPhai.loai === 'nhip') return mucNhip(menuPhai.id!)

    if (menuPhai.loai === 'day') {
      return [{ ten: 'Xoá kết nối', icon: 'unlink', onClick: () => xoaDay(menuPhai.id!) }]
    }

    if (menuPhai.loai === 'nen') {
      return [
        mucDan,
        { ngan: true },
        { ten: 'Thêm Kiểm tra điều kiện', icon: 'check-cond',
          onClick: () => themKhoi('action', 'check_cond', taiDay) },
        // Entry chỉ TẠO lệnh, Manage chỉ SỬA lệnh — menu phải nói đúng như ribbon.
        ...(tab === 'entry'
          ? [{ ten: 'Thêm Vào lệnh', icon: 'vao-lenh',
               onClick: () => themKhoi('action', 'vao_lenh', taiDay) }]
          : [{ ten: 'Thêm Sửa lệnh', icon: 'sua-lenh',
               onClick: () => themKhoi('action', 'sua_lenh', taiDay) }]),
      ]
    }

    // --- menu của khối ---
    const nhieu = dangChon.length > 1
    const ids = dangChon.map(n => n.id)
    const idNguon = menuPhai.id!
    const stNguon = (nodes.find(n => n.id === idNguon)?.data as { step: Step })?.step
    const laStart = stNguon?.kind === 'start'
    const daGhimHet = dangChon.length > 0
      && dangChon.every(n => (n.data as { step: Step }).step.ghim)

    // Nối được tới: mọi khối trừ chính nó, trừ khối Bắt đầu (không nhận đường vào), và
    // trừ những khối ĐÃ nối rồi. Cố ý KHÔNG loại khối tạo thành vòng — nối ngược lên
    // trên là hợp lệ, và ghim số là cách nói rằng nó cố ý.
    const daNoi = new Set(edges.filter(e => e.source === idNguon).map(e => e.target))
    const ungVien: MucPhai[] = nodes
      .filter(n => n.id !== idNguon && !daNoi.has(n.id)
                   && (n.data as { step: Step }).step.kind !== 'start')
      .sort((a, b) => (thuTu[a.id] ?? 'zzz').localeCompare(thuTu[b.id] ?? 'zzz',
                                                          undefined, { numeric: true }))
      .map(n => ({
        // Nhãn đứng trước tên: thứ tự đọc trong menu trùng thứ tự chạy trên canvas.
        ten: `${thuTu[n.id] ?? '–'}  ·  ${(n.data as { card: Card }).card.title}`
             + ((n.data as { step: Step }).step.ghim ? '  ⟲' : ''),
        onClick: () => noi({ source: idNguon, target: n.id,
                             sourceHandle: 'right', targetHandle: 'left' } as Connection),
      }))
    const coDay = edges.some(e => ids.includes(e.source) || ids.includes(e.target))

    return [
      { ten: 'Sửa', icon: 'edit', tat: nhieu || laStart,
        viSao: laStart ? 'khối Bắt đầu không có gì để sửa' : 'chỉ sửa được một khối một lúc',
        onClick: () => setDangSua(idNguon) },
      { ten: 'Đổi tên…', icon: 'edit', tat: nhieu, viSao: 'chỉ đổi tên một khối một lúc',
        onClick: doiTen },
      // Chỉ hiện ở khối Bắt đầu: nhịp là của SƠ ĐỒ, mà khối Bắt đầu là điểm neo của nó.
      ...(laStart && !nhieu
          ? [{ ten: 'Nhịp chạy', icon: 'motSo', con: mucNhip(idNguon) } as MucPhai]
          : []),
      { ngan: true },
      { ten: daGhimHet ? 'Bỏ ghim số' : 'Ghim số ⟲', icon: daGhimHet ? 'bo-ghim' : 'ghim',
        tat: laStart, viSao: 'khối Bắt đầu luôn là số 1, không cần ghim',
        onClick: doiGhim },
      { ten: 'Nối tới', icon: 'branch',
        tat: nhieu || !ungVien.length,
        viSao: nhieu ? 'chỉ nối được từ một khối' : 'đã nối tới mọi khối còn lại rồi',
        con: ungVien },
      { ten: 'Ngắt hết kết nối', icon: 'unlink', tat: !coDay,
        viSao: 'khối này chưa có dây nào', onClick: () => ngatKetNoi(ids) },
      { ngan: true },
      { ten: nhieu ? `Chép (${ids.length} khối)` : 'Chép', icon: 'copy', onClick: chepKhoi },
      mucDan,
      { ten: nhieu ? `Nhân bản (${ids.length} khối)` : 'Nhân bản', icon: 'plus',
        tat: laStart && !nhieu, viSao: 'chỉ được một khối Bắt đầu', onClick: nhanBan },
      { ngan: true },
      { ten: nhieu ? `Xoá (${ids.length} khối)` : 'Xoá', icon: 'trash',
        tat: laStart && !nhieu,
        viSao: 'khối Bắt đầu là điểm neo đánh số — không xoá được', onClick: xoa },
    ]
  }, [menuPhai, nodes, edges, dangChon, thuTu, tab, danKhoi, xoaDay, themKhoi, doiTen,
      doiGhim, mucNhip, chepKhoi, nhanBan, noi, ngatKetNoi, xoa])

  /* ------------------------------ phím tắt ------------------------------- */
  useEffect(() => {
    const f = (ev: KeyboardEvent) => {
      const o = ev.target as HTMLElement
      if (o && (o.tagName === 'INPUT' || o.tagName === 'TEXTAREA' || o.tagName === 'SELECT')) return
      // Hộp thoại đang mở thì phím tắt của canvas PHẢI im: nếu không, bấm Delete trong
      // hộp thoại vừa xoá hành động vừa xoá luôn cả khối phía sau.
      if (document.querySelector('.lop-phu')) return
      const ctrl = ev.ctrlKey || ev.metaKey
      if (ctrl && ev.key.toLowerCase() === 'z' && !ev.shiftKey) { ev.preventDefault(); hoanTac() }
      else if (ctrl && (ev.key.toLowerCase() === 'y' || (ev.shiftKey && ev.key.toLowerCase() === 'z'))) { ev.preventDefault(); lamLai() }
      else if (ctrl && ev.key.toLowerCase() === 'd') { ev.preventDefault(); nhanBan() }
      else if (ctrl && ev.key.toLowerCase() === 'c') { ev.preventDefault(); chepKhoi() }
      else if (ctrl && ev.key.toLowerCase() === 'v') { ev.preventDefault(); danKhoi() }
      else if (ctrl && ev.shiftKey && ev.key.toLowerCase() === 's') {
        ev.preventDefault(); luuThanh()
      }
      else if (ctrl && ev.key.toLowerCase() === 's') { ev.preventDefault(); luu() }
      else if (ctrl && ev.key.toLowerCase() === 'g') { ev.preventDefault(); doiGhim() }
      // Ctrl+R: `preventDefault` BẮT BUỘC — mặc định của Chromium là nạp lại trang, tức
      // mất trắng sơ đồ đang vẽ dở. Chặn nó cũng là một cái lợi kèm theo.
      else if (ctrl && ev.key.toLowerCase() === 'r') { ev.preventDefault(); void chay() }
      else if (ctrl && ev.key.toLowerCase() === 'l') { ev.preventDefault(); void moLive() }
      else if (ev.key === 'Delete') { ev.preventDefault(); xoa() }
      else if (ev.key === 'F2') { ev.preventDefault(); doiTen() }
    }
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [hoanTac, lamLai, nhanBan, luu, luuThanh, xoa, doiTen, chepKhoi, danKhoi, doiGhim,
      chay])

  /* Kéo hộp: chụp ảnh MỘT lần lúc bắt đầu kéo, không phải mỗi frame — nếu không thì một
     cú kéo tạo ra 60 bước undo và Ctrl+Z thành vô dụng. */
  const dangKeo = useRef(false)
  const batDauKeo = useCallback(() => {
    if (!dangKeo.current) { dangKeo.current = true; chup() }
  }, [chup])
  const ketThucKeo = useCallback(() => { dangKeo.current = false }, [])

  /* Gắn số thứ tự vào node ngay trước khi vẽ. Không nhét vào state `nodes` để đừng làm
     bẩn dữ liệu khối — số thứ tự là thứ TÍNH RA, không phải thuộc tính. */
  /* ⚠ Chỉ soi khi ĐANG Ở ĐÚNG TAB của lượt đó. Thiếu chốt này thì bấm sang tab kia
   * (hoặc Ctrl+Z ra một ảnh chụp ở tab khác) là **cả sơ đồ bên đó bị làm mờ 100%** —
   * không khối nào sáng vì id hai tab không bao giờ trùng — kèm dòng cảnh báo SAI
   * "sơ đồ đã đổi từ lúc chạy" trên một sơ đồ chưa ai đụng vào.
   *
   * Kẹp ở NƠI TIÊU THỤ chứ không rải `setSoi(null)` vào `doiTab`/`nap`/`apDung`: rải
   * thì sớm muộn có hàm thứ tư quên mất. Và cách này còn đúng hơn — quay lại đúng tab
   * là soi sáng lại, thay vì mất luôn. */
  const soiHopLe = soi && soi.tab === tab ? soi : null

  const nodesCoSo = useMemo(() => {
    const soi = soiHopLe
    const tren = soi ? new Set(soi.duong) : null
    const cong = new Map((soi?.cong ?? []).map(c => [c.khoi, c]))
    return nodes.map(n => {
      const card = (n.data as { card: Card }).card
      const c = cong.get(n.id)
      // ⚠ Chỉ tô TỪNG DÒNG khi số dòng còn khớp. Sửa sơ đồ sau khi chạy (thêm/bớt một
      // điều kiện) là dòng thứ k không còn là điều kiện thứ k nữa — lúc đó tô cả khối
      // thôi. Thà nói ít hơn nói sai.
      const veKhop = c && c.ve.length === card.lines.length
      const soiKhoi: SoiKhoi | undefined = soi && (tren!.has(n.id) || c)
        ? { daChay: tren!.has(n.id), truot: !!c && !c.khop,
            dieuKien: veKhop ? c!.ve.map(v => v.dat) : [] }
        : undefined
      return { ...n, data: { ...(n.data as object), thuTu: thuTu[n.id],
                             soiKhoi, moSoi: !!soi && !soiKhoi } }
    })
  }, [nodes, thuTu, soiHopLe])

  /** Có id nào trong lượt không còn trên sơ đồ nữa không — tức sơ đồ đã bị sửa sau khi
   *  chạy. Tô nửa vời mà không nói gì thì người đọc tin vào một đường không có thật. */
  const soiLech = useMemo(() => {
    if (!soiHopLe) return false
    const co = new Set(nodes.map(n => n.id))
    return [...soiHopLe.duong, ...soiHopLe.cong.map(c => c.khoi)].some(k => !co.has(k))
  }, [soiHopLe, nodes])

  /* Cạnh quay lại vẽ NÉT ĐỨT màu khác: nhìn sơ đồ là thấy ngay chỗ nào lặp về đâu,
     không phải dò từng mũi tên. */
  const edgesCoNet = useMemo(() => edges.map(e => (
    quayLai.has(`${e.source}|${e.target}`)
      ? {
          ...e,
          className: 'day-quay-lai',
          style: { ...e.style, stroke: 'var(--ghim)', strokeDasharray: '6 4' },
          markerEnd: { ...MUI_TEN, color: '#d9a441' },
          label: '⟲',
        }
      : e)), [edges, quayLai])

  const mucLuu: MucMenu[] = [
    { nhan: 'Lưu', chay: luu },
    { nhan: 'Lưu thành…', chay: luuThanh },
    { nhan: 'Lưu ra file khác…', chay: luuRaFile },
  ]
  const mucMo: MucMenu[] = [
    { nhan: 'Mở chiến lược (thay toàn bộ)',
      chay: () => setMoPicker({ tieuDe: 'Mở chiến lược',
                                xong: t => { setMoPicker(null); moChienLuoc(t) } }) },
    { nhan: 'Mở từ file khác…', chay: moFile },
    // Chữ "Thêm khối" để phân biệt hẳn với "thay toàn bộ" ngay bên trên — hai thứ này
    // mà lẫn nhau thì một cú bấm nhầm xoá sạch sơ đồ đang làm dở.
    { nhan: 'Thêm khối từ chiến lược khác…',
      chay: () => setMoPicker({ tieuDe: 'Thêm khối từ chiến lược',
                                xong: t => { setMoPicker(null); void themKhoiTu(t) } }) },
    { nhan: 'Sơ đồ mẫu Compress (xem thử)', chay: moMau },
  ]

  /* 4 menu trên thanh tiêu đề. Cố ý KHÔNG tạo hành động mới nào — tất cả trỏ về đúng
     những hàm ribbon đang gọi, nên hai nơi không thể lệch nhau. */
  const menuTieuDe: NhomMenu[] = useMemo(() => [
    { ten: 'File', muc: [
      { ten: 'Sơ đồ mới', icon: 'plus', onClick: soDoMoi },
      { ten: 'Mở chiến lược…', icon: 'folder', onClick: () => setMoPicker({
          tieuDe: 'Mở chiến lược',
          xong: t => { setMoPicker(null); moChienLuoc(t) } }) },
      { ten: 'Mở từ file…', onClick: moFile },
      { ten: 'Thêm khối từ chiến lược khác…', icon: 'paste',
        onClick: () => setMoPicker({ tieuDe: 'Thêm khối từ chiến lược',
                                     xong: t => { setMoPicker(null); void themKhoiTu(t) } }) },
      { ten: 'Sơ đồ mẫu Compress (xem thử)', onClick: moMau },
      { ngan: true },
      // Trỏ thẳng về `chay` — đúng hàm mà nút ▶ trên ribbon gọi, nên hai lối vào không
      // thể lệch nhau (cùng luật với 4 menu còn lại).
      { ten: 'Mở Strategy Tester', icon: 'chay', phim: 'Ctrl+R', onClick: chay },
      { ten: 'Mở Live…', icon: 'chay', phim: 'Ctrl+L',
        onClick: moLive },
      { ngan: true },
      { ten: 'Lưu', icon: 'save', phim: 'Ctrl+S', onClick: luu },
      { ten: 'Lưu thành…', icon: 'save', phim: 'Ctrl+Shift+S', onClick: luuThanh },
      { ten: 'Lưu ra file khác…', onClick: luuRaFile },
      { ngan: true },
      { ten: 'Tham số chiến lược…', icon: 'edit', onClick: () => setMoThamSo(true) },
      { ten: 'Kho — app đang có những gì…', icon: 'folder',
        onClick: () => setMoKho(true) },
      { ngan: true },
      { ten: 'Cài đặt…', icon: 'gear', onClick: () => setMoCaiDat(true) },
      { ten: 'Thoát', onClick: () => py.cua_so_dong() },
    ] },
    { ten: 'Sửa', muc: [
      { ten: 'Hoàn tác', icon: 'undo', tat: !coLui, viSao: 'chưa có gì để hoàn tác',
        onClick: hoanTac },
      { ten: 'Làm lại', icon: 'redo', tat: !coToi, viSao: 'chưa hoàn tác gì', onClick: lamLai },
      { ngan: true },
      { ten: 'Chép', icon: 'copy', tat: !dangChon.length, viSao: 'chưa chọn khối nào',
        onClick: chepKhoi },
      { ten: 'Dán', icon: 'paste', onClick: () => danKhoi() },
      { ten: 'Nhân bản', icon: 'plus', tat: !dangChon.length, viSao: 'chưa chọn khối nào',
        onClick: nhanBan },
      { ten: 'Ghim số ⟲', icon: 'ghim', tat: !dangChon.length,
        viSao: 'chưa chọn khối nào', onClick: doiGhim },
      { ten: 'Xoá', icon: 'trash', tat: !dangChon.length, viSao: 'chưa chọn khối nào',
        onClick: xoa },
    ] },
    { ten: 'Xem', muc: [
      { ten: 'Phóng to', onClick: () => zoomIn({ duration: 150 }) },
      { ten: 'Thu nhỏ', onClick: () => zoomOut({ duration: 150 }) },
      { ten: 'Vừa khung', icon: 'fit', onClick: () => fitView({ padding: 0.2, duration: 300, maxZoom: 1 }) },
      { ngan: true },
      { ten: panelGap ? 'Hiện bảng dưới' : 'Ẩn bảng dưới', onClick: () => setPanelGap(v => !v) },
    ] },
    { ten: 'Trợ giúp', muc: [
      { ten: 'Số = đi được bao xa · Chữ = đi nhánh nào', tat: true,
        viSao: 'luật đánh số của sơ đồ' },
      { ten: 'Ghim số ⟲ = cho phép nối ngược về mà vẫn giữ đúng số', tat: true,
        viSao: 'chuột phải vào khối để ghim' },
      { ten: `Cat Studio ${boot?.phien_ban ?? ''}`.trim(), tat: true,
        viSao: 'chỉ để xem phiên bản' },
    ] },
  ], [soDoMoi, moFile, moMau, luu, luuThanh, luuRaFile, moChienLuoc, hoanTac, lamLai, coLui, coToi,
      chepKhoi, danKhoi, nhanBan, doiGhim, xoa, dangChon, zoomIn, zoomOut, fitView,
      panelGap, boot, setMoKho, setMoThamSo, chay, themKhoiTu])

  const soLoi = vanDe.filter(v => v.severity === 'error').length
  const soCanhBao = vanDe.length - soLoi
  const tabCoLoi: Record<Tab, boolean> = {
    entry: vanDe.some(v => v.tab === 'entry' && v.severity === 'error'),
    manage: vanDe.some(v => v.tab === 'manage' && v.severity === 'error'),
  }

  return (
    <div className="khung">
      <TitleBar tieuDe={`${ten} — Cat Studio`} menus={menuTieuDe} />
      <Ribbon
        tab={tab}
        themKiemTra={() => themKhoi('action', 'check_cond')}
        themVaoLenh={() => themKhoi('action', 'vao_lenh')}
        themSuaLenh={() => themKhoi('action', 'sua_lenh')}
        sua={() => dangChon[0] && setDangSua(dangChon[0].id)}
        datBatDau={datBatDau} doiGhim={doiGhim}
        nhanBan={nhanBan} xoa={xoa}
        hoanTac={hoanTac} lamLai={lamLai}
        vuaKhung={() => fitView({ padding: 0.2, duration: 300, maxZoom: 1 })}
        mucLuu={mucLuu} mucMo={mucMo}
        ten={ten} datTen={setTen}
        symbol={symbol} datSymbol={setSymbol}
        chay={chay}
        live={moLive}
        rl={moRL}
        coChon={dangChon.length > 0}
        chonDaGhim={dangChon.length > 0
          && dangChon.every(n => (n.data as { step: Step }).step.ghim)}
        coTheHoanTac={coLui} coTheLamLai={coToi}
      />

      <div className={'vung-canvas' + (dangNoi ? ' dang-noi' : '')}>
        {/* Pill NỔI TRÊN canvas, không chiếm một dải riêng: nó là câu trả lời cho
            "đang vẽ sơ đồ NÀO", nên nằm ngay trên chính cái đang vẽ là đúng chỗ. */}
        <PillTab tab={tab} datTab={doiTab} tabCoLoi={tabCoLoi} />

        {/* Dải SOI — nổi trên canvas, ngay cạnh pill tab. Bắt buộc phải có: sơ đồ đang
            mờ đi một cách bất thường thì phải nói ra vì sao, và phải có đường thoát
            nhìn thấy được chứ không chỉ phím Esc. */}
        {soiHopLe && (
          <div className="soi-dai">
            <span className="soi-nhan">Soi lượt</span>
            <span className="soi-chu">{soiHopLe.chu}</span>
            {soiLech && (
              <span className="soi-canh" title="Có khối trong lượt này không còn trên sơ đồ">
                sơ đồ đã đổi từ lúc chạy
              </span>
            )}
            <button className="soi-tat" title="Thôi soi (Esc)"
                    onClick={() => setSoi(null)}>✕</button>
          </div>
        )}

        <ReactFlow
          nodes={nodesCoSo} edges={edgesCoNet}
          onNodesChange={onNodesChange as (c: NodeChange[]) => void}
          onEdgesChange={onEdgesChange as (c: EdgeChange[]) => void}
          onConnect={noi}
          onConnectStart={() => setDangNoi(true)}
          onConnectEnd={() => setDangNoi(false)}
          onNodeDragStart={batDauKeo}
          onNodeDragStop={ketThucKeo}
          onNodeDoubleClick={(ev, n) => {
            // Khối Bắt đầu không có hộp thoại sửa — thứ DUY NHẤT đổi được ở nó là NHỊP,
            // nên nhấp đúp mở thẳng danh sách nhịp thay vì không làm gì.
            if ((n.data as unknown as { step: Step }).step.kind === 'start') {
              setMenuPhai({ x: ev.clientX, y: ev.clientY, loai: 'nhip', id: n.id })
            } else setDangSua(n.id)
          }}
          onEdgeDoubleClick={huyNoi}
          onPaneContextMenu={bamPhaiNen}
          onNodeContextMenu={bamPhaiKhoi}
          onEdgeContextMenu={bamPhaiDay}
          nodeTypes={nodeTypes}
          connectionMode={ConnectionMode.Loose}
          proOptions={{ hideAttribution: true }}
          minZoom={0.2} maxZoom={2}
          defaultEdgeOptions={KIEU_DUONG_NOI}
          deleteKeyCode={null}
          multiSelectionKeyCode={PHIM_CHON_NHIEU}
          fitView
        >
          <Background variant={BackgroundVariant.Dots} gap={22} size={1.4}
                      color="var(--canvas-dot)" />
        </ReactFlow>

        {menuPhai && (
          <ContextMenu x={menuPhai.x} y={menuPhai.y} muc={mucMenuPhai}
                       onDong={() => setMenuPhai(null)} />
        )}

        {/* Gợi ý neo ở ĐÁY canvas, không phải giữa: giữa là chỗ khối Bắt đầu đứng, đặt
            chữ ở đó là chữ đè lên hộp. Chỉ hiện khi chưa nối dây nào. */}
        {edges.length === 0 && nodes.length <= 1 && sanSang && (
          <div className="trong-rong duoi">
            <div className="to">Bắt đầu từ khối ①</div>
            <div>
              Bấm <b>Kiểm tra ĐK</b> ở thanh trên để thêm một nhánh điều kiện, rồi kéo
              từ cổng bên cạnh hộp <b>Bắt đầu</b> để nối.
              <br />Nhiều cổng cùng nối từ một khối = <b>rẽ nhánh</b>, thử lần lượt từ
              trên xuống. Chuột phải vào khối → <b>Ghim số ⟲</b> để cho phép nối ngược
              về nó mà số vẫn giữ nguyên.
            </div>
          </div>
        )}
      </div>

      <div className={'bang-duoi' + (panelGap ? ' thu-gon' : '')}
           style={{ height: panelGap ? CAO_GAP : panelCao }}>
        <div className="thanh-keo" onMouseDown={batDauKeoPanel} title="Kéo để chỉnh chiều cao" />
        <div className="hang-tab" onDoubleClick={() => setPanelGap(v => !v)}>
          <button className={'tab' + (tabDuoi === 'van-de' ? ' dang' : '')}
                  onClick={() => { setTabDuoi('van-de'); setPanelGap(false) }}>
            Vấn đề{vanDe.length ? ` (${vanDe.length})` : ''}
          </button>
          <button className={'tab' + (tabDuoi === 'nhat-ky' ? ' dang' : '')}
                  onClick={() => { setTabDuoi('nhat-ky'); setPanelGap(false) }}>
            Nhật ký
          </button>
          <span className="day" />
          {tabDuoi === 'nhat-ky' && !panelGap &&
            <button className="nut-nho" onClick={() => setNhatKy([])}>Xoá nhật ký</button>}
          <button className="nut-nho nut-gap" onClick={() => setPanelGap(v => !v)}
                  title={panelGap ? 'Mở bảng' : 'Gập bảng xuống'}>
            {panelGap ? '▲' : '▼'}
          </button>
        </div>
        {!panelGap && <div className="noi-dung-tab">
          {tabDuoi === 'van-de' ? (
            vanDe.length === 0
              ? <div className="trong">Không có vấn đề nào.</div>
              : vanDe.map((v, i) => (
                <div key={i}
                     className={'dong-van-de ' + (v.severity === 'error' ? 'loi' : 'canh-bao')}
                     title="Bấm để nhảy tới khối bị lỗi"
                     onClick={() => {
                       // Lỗi có thể ở tab kia — nhảy tab trước rồi mới chọn khối.
                       if (v.tab !== tab) doiTab(v.tab)
                       const id = v.step as string | null | undefined
                       if (!id) return
                       setTimeout(() => {
                         setNodes(ds => ds.map(k => ({ ...k, selected: k.id === id })))
                         const n = (v.tab === tab ? nodes : kho.current[v.tab].nodes)
                           .find(k => k.id === id)
                         if (n) setCenter(n.position.x + 150, n.position.y + 80,
                                          { zoom: mucZoom, duration: 350 })
                       }, v.tab !== tab ? 60 : 0)
                     }}>
                  <span className="muc">{v.severity === 'error' ? '●' : '▲'}</span>
                  <span className={'nhan-tab t-' + v.tab}>{v.tab === 'entry' ? 'Entry' : 'Manage'}</span>
                  <span>{v.message}</span>
                  {v.dat_ten && (
                    // Nút NGAY TRONG dòng cảnh báo, không phải "mở bảng tham số rồi tự
                    // gõ lại": chỗ phát hiện vấn đề cũng là chỗ sửa được nó.
                    <button className="nut nho dat-ten"
                            title={`Thêm tham số "${v.dat_ten.goi_y}" = ${v.dat_ten.gia_tri}`
                                   + ` và thay vào cả ${v.dat_ten.cho.length} chỗ`}
                            onClick={e => {
                              e.stopPropagation()   // không nhảy tới khối
                              void datTenCho(v.dat_ten!)
                            }}>
                      Đặt tên cho số này
                    </button>
                  )}
                </div>
              ))
          ) : (
            nhatKy.length === 0
              ? <div className="trong">Chưa có gì.</div>
              : <div className="nhat-ky">
                  {nhatKy.map((l, i) => (
                    <div key={i} className={'dong-log' + (l.tag ? ' t-' + l.tag : '')}>
                      <span className="gio">{l.gio}</span>{l.msg}
                    </div>
                  ))}
                  <div ref={cuoiLog} />
                </div>
          )}
        </div>}
      </div>

      <div className="thanh-trang-thai">
        <button className="nut-tt" onClick={() => setMoCaiDat(true)} title="Cài đặt">
          <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor"
               strokeLinecap="round" strokeLinejoin="round">
            <circle cx="8" cy="8" r="4.9" strokeWidth="1.3" />
            <circle cx="8" cy="8" r="1.9" strokeWidth="1.3" />
            <g strokeWidth="2">
              <path d="M8 1.3v1.4M8 13.3v1.4M14.7 8h-1.4M2.7 8H1.3" />
              <path d="M12.7 3.3l-1 1M4.3 11.7l-1 1M12.7 12.7l-1-1M4.3 4.3l-1-1" />
            </g>
          </svg>
        </button>
        <span><span className="so">{nodes.length}</span> khối</span>
        <span><span className="so">{edges.length}</span> đường nối</span>
        {soLoi > 0 && <span style={{ color: 'var(--err)' }}>{soLoi} lỗi</span>}
        {soCanhBao > 0 && <span style={{ color: 'var(--warn)' }}>{soCanhBao} cảnh báo</span>}
        {quayLai.size > 0 && (
          <span style={{ color: 'var(--ghim)' }} title="Đường nối quay về khối đã ghim số">
            ⟲ {quayLai.size} vòng lặp đã ghim
          </span>
        )}
        {vongHo > 0 && (
          <span style={{ color: 'var(--warn)' }} title="Ghim khối đích lại để xác nhận là cố ý">
            {vongHo} vòng chưa ghim
          </span>
        )}
        <span className="day" />
        <span>{trangThai}</span>
        <div className="cum-zoom">
          <button className="nut-zoom" onClick={() => zoomOut()} title="Thu nhỏ">−</button>
          <button className="nut-zoom" onClick={() => zoomIn()} title="Phóng to">+</button>
          <button className="nut-zoom" title="Vừa khung"
                  onClick={() => fitView({ padding: 0.2, duration: 300, maxZoom: 1 })}>
            <svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor"
                 strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2.5 5.5v-3h3M13.5 5.5v-3h-3M2.5 10.5v3h3M13.5 10.5v3h-3" />
            </svg>
          </button>
        </div>
        <span className="so">{Math.round(mucZoom * 100)}%</span>
      </div>

      {moKho && <KhoDialog onDong={() => setMoKho(false)} />}

      {moThamSo && boot && (
        <ThamSoDialog dsGoc={thamSo} boot={boot} dangDung={tsDangDung}
                      onLuu={luuThamSo} onDong={() => setMoThamSo(false)} />
      )}

      {moCaiDat && boot && (
        <SettingsDialog boot={boot} doiMauNgay={doiMauNgay}
                        lamMoiBoot={lamMoiBoot}
                        onDong={() => setMoCaiDat(false)} />
      )}

      {moPicker && (
        <TemplatePicker tieuDe={moPicker.tieuDe}
                        onChon={moPicker.xong} onDong={() => setMoPicker(null)}
                        onDuyetFile={() => { setMoPicker(null); moFile() }} />
      )}

      {dangSua && boot && (() => {
        const n = nodes.find(k => k.id === dangSua)
        if (!n) return null
        const st = (n.data as { step: Step }).step
        if (st.kind === 'start') return null      // khối Bắt đầu không có gì để sửa
        // Một khối CHÍNH LÀ một hành động -> mở thẳng hộp thoại hành động, khỏi bắt
        // người dùng đi qua một lớp "danh sách 1 phần tử" vô nghĩa.
        return (
          <ActionDialog action={st as Record<string, any>} boot={boot} tab={tab}
                        thamSo={thamSo} coZone={sauCongZone.has(st.id)}
                        onDong={() => setDangSua(null)}
                        onLuu={a => ghiBuoc({ ...a, kind: 'action', id: st.id,
                                              pos: st.pos, ghim: st.ghim } as Step)} />
        )
      })()}

    </div>
  )
}

export default function App() {
  return <ReactFlowProvider><Ung /></ReactFlowProvider>
}
