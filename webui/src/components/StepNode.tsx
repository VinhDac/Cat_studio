import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { Card, StepKind } from '../types'
import IconNet, { ICON_HANH_DONG } from './Icon'

/** Số dòng hành động hiện tối đa trên một hộp.
 *
 * Yêu cầu là "nhìn hộp phải hiểu khối này làm gì" — nhưng một Nhóm 40 hành động mà vẽ
 * hết thì hộp cao bằng cả màn hình và sơ đồ hết đọc được. Cắt ở đây rồi ghi rõ còn bao
 * nhiêu; muốn xem hết thì double-click mở hộp thoại.
 */
const TOI_DA_DONG = 8

const MAU: Record<StepKind, string> = {
  start: 'var(--start)',
  loop: 'var(--loop)',
  group: 'var(--group)',
  action: 'var(--action)',
}

const TEN_LOAI: Record<StepKind, string> = {
  start: 'Bắt đầu',
  loop: 'Vòng theo dõi',
  group: 'Nhóm 1 lần',
  action: 'HĐ lẻ',
}

const ICON_KHOI: Record<StepKind, string> = {
  start: 'start', loop: 'loop', group: 'group', action: 'action',
}

const SIDES: [string, Position][] = [
  ['top', Position.Top],
  ['right', Position.Right],
  ['bottom', Position.Bottom],
  ['left', Position.Left],
]

export default function StepNode({ data, selected }: NodeProps) {
  const card = (data as { card: Card }).card
  const thuTu = (data as { thuTu?: string }).thuTu
  const hien = card.lines.slice(0, TOI_DA_DONG)
  const con = card.lines.length - hien.length
  const laStart = card.kind === 'start'

  return (
    <>
      {/* 4 cổng ở giữa 4 cạnh — mỗi cạnh phải có CẢ source LẪN target.
          Chỉ đặt source thì kéo nối vẫn được (nhờ ConnectionMode.Loose) nhưng React
          Flow không phân giải nổi đầu ĐÍCH của một đường nối đã có, và vẽ ra mấy mẩu
          cụt bên cạnh hộp. Cái target trùng id, trùng vị trí, ẩn đi và không bắt
          chuột — nó chỉ cần TỒN TẠI để đường nối bám vào. */}
      {SIDES.map(([id, pos]) => (
        <Handle key={id} type="source" id={id} position={pos} />
      ))}
      {/* Khối Bắt đầu KHÔNG có cổng đích: nó là điểm neo, không bao giờ được chạy tới
          từ chỗ khác. Không cho thả dây vào là chặn lỗi ngay từ lúc kéo, thay vì để
          bảng Vấn đề báo sau. */}
      {!laStart && SIDES.map(([id, pos]) => (
        <Handle key={'t-' + id} type="target" id={id} position={pos}
                style={{ opacity: 0, pointerEvents: 'none' }} />
      ))}

      <div className={'hop'
        + (selected ? ' dang-chon' : '')
        + (thuTu ? '' : ' khong-toi')
        + (laStart ? ' la-start' : '')
        + (card.ghim ? ' da-ghim' : '')
        + (card.la_cong ? ' la-cong' : '')}>

        {/* Số THỨ TỰ CHẠY THẬT, do Python tính bằng chính phép duyệt của bộ máy.
            Không có số = đường nối không dẫn tới khối này, nó sẽ KHÔNG chạy — phải
            nhìn thấy được ngay, không thì lại rơi vào cảnh sơ đồ nói dối. */}
        <div className={'so-thu-tu' + (thuTu ? '' : ' trong') + (card.ghim ? ' ghim' : '')}
             title={thuTu
               ? (card.ghim
                 ? `Bước ${thuTu} — SỐ ĐÃ GHIM: mọi đường nối quay về đây vẫn giữ đúng số này`
                 : `Bước ${thuTu} — số = đi được bao xa, chữ = đi nhánh nào`)
               : 'Không có đường nối dẫn tới — sẽ không chạy'}>
          {thuTu ?? '–'}
          {card.ghim && <span className="dau-ghim" aria-hidden>⟲</span>}
        </div>

        <div className="dau">
          <span className="dai-mau" style={{ background: MAU[card.kind] }} />
          <IconNet name={ICON_KHOI[card.kind]} size={13} />
          <span className="ten" title={card.title}>{card.title}</span>
          <span className="loai">{TEN_LOAI[card.kind]}</span>
        </div>

        {!laStart && (
          <div className="than">
            {hien.length === 0 && <div className="dong rong">chưa có hành động nào</div>}
            {hien.map((d, i) => (
              <div key={i}
                   className={'dong' + (d.prologue ? ' mo-dau' : '')}
                   title={d.text}>
                <span className="danh">
                  {d.prologue ? '1×' : card.kind === 'loop' ? '↻' : ''}
                </span>
                <IconNet name={ICON_HANH_DONG[d.type ?? ''] ?? ''} size={12} />
                <span>{d.text}</span>
              </div>
            ))}
            {con > 0 && (
              <div className="dong con-nua">
                <span className="danh" /><span>… còn {con} hành động</span>
              </div>
            )}
          </div>
        )}

        {card.badges.length > 0 && (
          <div className="chan">
            {card.badges.map((b, i) => <span key={i} className="the">{b}</span>)}
            {card.ghim && <span className="the the-ghim">⟲ đã ghim số</span>}
          </div>
        )}
      </div>
    </>
  )
}
