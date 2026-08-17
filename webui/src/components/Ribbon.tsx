import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import type { Tab } from '../types'
import Icon from './Icon'

/** Thanh công cụ kiểu ribbon của Paint: nút nhóm lại, nhãn nhóm nằm DƯỚI, có vạch
 *  ngăn giữa các nhóm. Mọi thứ "thêm vào" nằm ở trên; canvas phía dưới chỉ để di
 *  chuyển và nối. */

function Nhom({ ten, children }: { ten: string; children: ReactNode }) {
  return (
    <div className="nhom-ribbon">
      <div className="cac-nut">{children}</div>
      <div className="ten-nhom">{ten}</div>
    </div>
  )
}

function Nut({ ten, icon, onClick, tat, title }: {
  ten: string; icon: ReactNode; onClick?: () => void; tat?: boolean; title?: string
}) {
  return (
    <button className="nut-lon" onClick={onClick} disabled={tat} title={title || ten}>
      <span className="hinh">{icon}</span>
      <span>{ten}</span>
    </button>
  )
}

export interface MucMenu { nhan: string; chay: () => void; tat?: boolean; lyDo?: string }

/** Nút có menu xổ xuống.
 *  Mục bị tắt vẫn HIỆN kèm lý do: giấu đi thì người dùng tưởng tính năng không tồn tại. */
function NutMenu({ ten, icon, muc }: { ten: string; icon: ReactNode; muc: MucMenu[] }) {
  const [mo, setMo] = useState(false)
  const [viTri, setViTri] = useState({ x: 0, y: 0 })
  const boc = useRef<HTMLDivElement>(null)
  const nut = useRef<HTMLButtonElement>(null)
  const bang = useRef<HTMLDivElement>(null)

  /* Menu này ĐỊNH VỊ THEO KHUNG NHÌN, không theo khối cha.
     `.ribbon` có `overflow-x: auto`, mà theo chuẩn CSS hễ một trục thôi `visible` thì
     trục kia cũng thôi luôn — nên dải ribbon cắt cụt menu theo CHIỀU DỌC: bấm "Mở ▾"
     ra một mẩu menu bị xén, không bấm được mục nào.
     `position: fixed` thoát khỏi mọi vùng cắt của khối cha. */
  useLayoutEffect(() => {
    if (!mo || !nut.current) return
    const r = nut.current.getBoundingClientRect()
    const m = bang.current?.getBoundingClientRect()
    const le = 6
    setViTri({
      x: Math.max(le, Math.min(r.left, window.innerWidth - (m?.width ?? 268) - le)),
      y: Math.max(le, Math.min(r.bottom + 2, window.innerHeight - (m?.height ?? 0) - le)),
    })
  }, [mo])

  useEffect(() => {
    if (!mo) return
    const f = (e: MouseEvent) => {
      if (!boc.current?.contains(e.target as globalThis.Node)) setMo(false)
    }
    const dong = () => setMo(false)
    window.addEventListener('mousedown', f)
    window.addEventListener('resize', dong)
    return () => {
      window.removeEventListener('mousedown', f)
      window.removeEventListener('resize', dong)
    }
  }, [mo])

  return (
    <div className="boc-menu" ref={boc}>
      <button className="nut-lon" ref={nut} onClick={() => setMo(v => !v)}>
        <span className="hinh">{icon}</span>
        <span>{ten} ▾</span>
      </button>
      {mo && (
        <div className="menu-xo" ref={bang} style={{ left: viTri.x, top: viTri.y }}>
          {muc.map((m, i) => (
            <button key={i} className="muc-menu" disabled={m.tat}
                    title={m.tat ? m.lyDo : undefined}
                    onClick={() => { setMo(false); m.chay() }}>
              {m.nhan}{m.tat && m.lyDo ? <span className="ly-do">— {m.lyDo}</span> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const S = {
  fill: 'none', stroke: 'currentColor', strokeWidth: 1.5,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const,
}

/** Icon 22px của ribbon — to hơn bộ 16px trong `Icon.tsx` nên vẽ riêng, cùng ngôn ngữ nét. */
const I = {
  /* Một đường vào, hai đường ra — đúng hình rẽ nhánh người dùng vẽ trên giấy. */
  branch: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M2.5 11h5M7.5 11l5-5M7.5 11l5 5" /><circle {...S} cx="15.5" cy="6" r="2.6" /><circle {...S} cx="15.5" cy="16" r="2.6" /></svg>,
  vao: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="2.6" y="7.4" width="4" height="7.2" rx="1" /><path {...S} d="M4.6 4.8v2.6M4.6 14.6v2.6" /><path {...S} d="M10 14.6l4.8-4.8M11.2 9.2h3.8v3.8" /><path {...S} d="M18.6 4.4v13.2" strokeDasharray="2.2 2.2" /></svg>,
  sua: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M3 15.6h16" strokeDasharray="2.4 2.2" /><path {...S} d="M3 6.4h16" strokeDasharray="2.4 2.2" /><path {...S} d="M11 4.6v12.8" /><path {...S} d="M8.6 9.2L11 6.8l2.4 2.4M8.6 12.8L11 15.2l2.4-2.4" /></svg>,
  start: <svg viewBox="0 0 22 22" width="22" height="22"><circle {...S} cx="11" cy="11" r="8" /><path {...S} d="M11 5.4l3.6 5.6-3.6 5.6-3.6-5.6z" /></svg>,
  edit: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="3.5" y="3.5" width="15" height="15" rx="2" /><path {...S} d="M7.5 13.5l6-6M11 6.5l4 4" /></svg>,
  copy: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="7" y="7" width="11" height="11" rx="1.8" /><path {...S} d="M14.5 4.5H5.8A1.3 1.3 0 0 0 4.5 5.8v8.7" /></svg>,
  del: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M4.5 6.5h13M9 6.5V4.5h4v2M6.5 6.5l1 12h7l1-12" /><path {...S} d="M9.5 9.5v6M12.5 9.5v6" /></svg>,
  undo: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M6 9.5H14a4.5 4.5 0 0 1 0 9h-3" /><path {...S} d="M9 6l-3.5 3.5L9 13" /></svg>,
  redo: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M16 9.5H8a4.5 4.5 0 0 0 0 9h3" /><path {...S} d="M13 6l3.5 3.5L13 13" /></svg>,
  save: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M4.5 5.8A1.3 1.3 0 0 1 5.8 4.5h8.4l3.3 3.3v8.4a1.3 1.3 0 0 1-1.3 1.3H5.8a1.3 1.3 0 0 1-1.3-1.3z" /><path {...S} d="M7.5 4.5v4h6v-4M7.5 17.5v-4h7v4" /></svg>,
  open: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M3.5 17V6.5A1 1 0 0 1 4.5 5.5h4l2 2.2h6a1 1 0 0 1 1 1V17z" /><path {...S} d="M3.5 17l2.6-6h13l-2.6 6z" /></svg>,
  // Số ① — CỐ Ý không dùng hình tam giác play: nút ▶ Chạy ở ngay cạnh, hai biểu tượng
  // play trong một ribbon thì không ai đoán được cái nào làm gì.
  motSo: <svg viewBox="0 0 22 22" width="22" height="22"><circle {...S} cx="11" cy="11" r="7.8" /><path {...S} d="M9.6 8.6L11.4 7.4v7.4M9.8 14.8h3.4" /></svg>,
  ghim: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M13.2 2.6l6.2 6.2-2.5 1.4-4-4z" /><path {...S} d="M12.9 6.2L6.4 11.4l4.2 4.2 4.5-6.2" /><path {...S} d="M8.6 13.4L3.2 18.8" /></svg>,
  fit: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M4 8V4.5h3.5M18 8V4.5h-3.5M4 14v3.5h3.5M18 14v3.5h-3.5" /><rect {...S} x="8" y="8" width="6" height="6" rx="1" /></svg>,
}

export interface RibbonProps {
  tab: Tab
  themKiemTra: () => void
  themVaoLenh: () => void
  themSuaLenh: () => void
  sua: () => void
  datBatDau: () => void
  doiGhim: () => void
  nhanBan: () => void
  xoa: () => void
  hoanTac: () => void
  lamLai: () => void
  vuaKhung: () => void
  mucLuu: MucMenu[]
  mucMo: MucMenu[]
  // cụm chạy ghim mép phải ribbon
  ten: string
  datTen: (v: string) => void
  symbol: string
  datSymbol: (v: string) => void
  chay: () => void
  live: () => void
  coChon: boolean
  chonDaGhim: boolean
  coTheHoanTac: boolean
  coTheLamLai: boolean
}

const TEN_TAB: Record<Tab, string> = { entry: 'Entry', manage: 'Manage' }
const CHU_THICH_TAB: Record<Tab, string> = {
  entry: 'Sơ đồ ĐI SĂN — chạy một lượt mỗi nến. Chỉ nó được TẠO lệnh.',
  manage: 'Sơ đồ QUẢN LÝ — chạy một lượt cho MỖI lệnh đang sống. Chỉ nó được SỬA lệnh.',
}

/** Pill chuyển sơ đồ — nằm NGAY DƯỚI dải ribbon, sát mép trái.
 *
 *  Đặt ở đó vì nó không phải một nút trong ribbon mà là câu trả lời cho "mọi thứ phía
 *  trên đang tác động lên sơ đồ NÀO". Chấm đỏ trên tab kia để lỗi không trốn được sau
 *  lưng: bấm ▶ Chạy mới biết tab kia hỏng là quá muộn. */
export function PillTab({ tab, datTab, tabCoLoi }: {
  tab: Tab; datTab: (t: Tab) => void; tabCoLoi: Record<Tab, boolean>
}) {
  return (
    <div className="pill-tab">
      {(['entry', 'manage'] as Tab[]).map(t => (
        <button key={t} className={'pill' + (tab === t ? ' dang' : '')}
                title={CHU_THICH_TAB[t]} onClick={() => datTab(t)}>
          {TEN_TAB[t]}
          {tabCoLoi[t] && <span className="cham-loi" title="Sơ đồ này đang có lỗi" />}
        </button>
      ))}
    </div>
  )
}

export default function Ribbon(p: RibbonProps) {
  return (
    <div className="ribbon">
      {/* Nút nào hiện là do TAB quyết: Entry chỉ TẠO lệnh, Manage chỉ SỬA lệnh.
          Làm mờ thì người dùng vẫn phải đoán vì sao; ẩn hẳn thì bảng chọn luôn đúng
          với việc đang làm. */}
      <Nhom ten="Thêm khối">
        <Nut ten="Kiểm tra ĐK" icon={I.branch} onClick={p.themKiemTra}
             title={'Thêm cổng "Kiểm tra điều kiện" — nối nhiều cổng vào cùng một khối '
                    + 'để chia nhánh. Khớp thì đi nhánh đó, không khớp thì thử nhánh dưới.'} />
        {p.tab === 'entry' && (
          <Nut ten="Vào lệnh" icon={I.vao} onClick={p.themVaoLenh}
               title="Mở vị thế mới: Mua/Bán, loại lệnh, khối lượng, SL và TP ban đầu" />
        )}
        {p.tab === 'manage' && (
          <Nut ten="Sửa lệnh" icon={I.sua} onClick={p.themSuaLenh}
               title="Tác động lên lệnh ĐÃ CÓ — bốn chế độ: dời SL · dời TP · SL về hoà vốn · kết thúc lệnh này" />
        )}
      </Nhom>

      <Nhom ten="Sửa">
        <Nut ten="Sửa" icon={I.edit} onClick={p.sua} tat={!p.coChon}
             title="Mở hộp thoại sửa khối đang chọn (hoặc double-click vào khối)" />
        <Nut ten="Nhân bản" icon={I.copy} onClick={p.nhanBan} tat={!p.coChon}
             title="Nhân bản khối đang chọn (Ctrl+D)" />
        <Nut ten="Xoá" icon={I.del} onClick={p.xoa} tat={!p.coChon}
             title="Xoá khối đang chọn (Delete)" />
      </Nhom>

      <Nhom ten="Luồng">
        <Nut ten="Đặt số ①" icon={I.motSo} onClick={p.datBatDau} tat={!p.coChon}
             title="Biến khối đang chọn thành khối ① — khối chạy đầu tiên" />
        <Nut ten={p.chonDaGhim ? 'Bỏ ghim' : 'Ghim số'} icon={I.ghim}
             onClick={p.doiGhim} tat={!p.coChon}
             title={'Ghim số của khối đang chọn: mọi đường nối quay ngược về nó vẫn giữ '
                    + 'đúng số cũ, và không còn cảnh báo vòng lặp'} />
        <Nut ten="Vừa khung" icon={I.fit} onClick={p.vuaKhung}
             title="Thu cả sơ đồ vào vừa màn hình" />
      </Nhom>

      <Nhom ten="Hoàn tác">
        <Nut ten="Hoàn tác" icon={I.undo} onClick={p.hoanTac} tat={!p.coTheHoanTac} title="Ctrl+Z" />
        <Nut ten="Làm lại" icon={I.redo} onClick={p.lamLai} tat={!p.coTheLamLai} title="Ctrl+Y" />
      </Nhom>

      <Nhom ten="Template">
        <NutMenu ten="Lưu" icon={I.save} muc={p.mucLuu} />
        <NutMenu ten="Mở" icon={I.open} muc={p.mucMo} />
      </Nhom>

      {/* Cụm chạy — ghim mép phải. Hai tầng: tên chiến lược ở trên, hàng nút hạ xuống
          dưới cho ngang hàng với nhãn nhóm. Xếp chồng nên KHÔNG tốn thêm bề ngang. */}
      <div className="cum-chay">
        <input className="o o-ten-process" value={p.ten} spellCheck={false}
               placeholder="Tên chiến lược"
               title="Tên chiến lược — cũng hiện trên thanh tiêu đề"
               onChange={e => p.datTen(e.target.value)} />
        <div className="hang-chay">
          <input className="o nho o-symbol" value={p.symbol} spellCheck={false}
                 title="Mã giao dịch" placeholder="XAUUSD"
                 onChange={e => p.datSymbol(e.target.value.toUpperCase())} />
          {/* LIVE đứng TRÁI và màu đỏ. Đỏ không phải để đẹp: hai nút cạnh nhau, một
              cái tiêu vài giây CPU, một cái tiêu tiền thật — chúng không được trông
              giống nhau. Trái/phải cũng cố ý: tay quen bấm cái bên phải. */}
          <button className="nut do" onClick={p.live}
                  title="Mở cửa sổ Live — chạy trên kết nối thật (Ctrl+L)">● Live</button>
          <button className="nut chinh" onClick={p.chay}
                  title="Mở Strategy Tester để chạy thử sơ đồ này (Ctrl+R)">▶ Test</button>
        </div>
      </div>
    </div>
  )
}
