import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { Card, StepKind } from '../types'
import IconNet, { ICON_HANH_DONG } from './Icon'

/** Số dòng hiện tối đa trên một hộp.
 *
 * Yêu cầu là "nhìn hộp phải hiểu khối này kiểm tra gì" — nhưng một cổng 6 điều kiện mà
 * vẽ hết thì hộp cao gấp đôi và sơ đồ hết đọc được. Cắt ở đây rồi ghi rõ còn bao nhiêu;
 * muốn xem hết thì double-click mở hộp thoại.
 */
const TOI_DA_DONG = 6

const MAU: Record<StepKind, string> = {
  start: 'var(--start)',
  action: 'var(--accent)',
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
  /* Icon lấy theo loại hành động của dòng ĐẦU — một khối chỉ mang một hành động, nên
     dòng nào cũng cùng loại. Khối Bắt đầu thì không có dòng nào. */
  const icon = laStart ? 'start' : (ICON_HANH_DONG[card.lines[0]?.type ?? ''] ?? 'action')

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
          <IconNet name={icon} size={13} />
          <span className="ten" title={card.title}>{card.title}</span>
        </div>

        {!laStart && (
          <div className="than">
            {hien.map((d, i) => (
              <div key={i} className="dong" title={d.text}>
                {/* Nhiều điều kiện nối nhau bằng VÀ — ghi ra để không ai đoán là HOẶC. */}
                <span className="danh">{i > 0 ? 'và' : ''}</span>
                <span>{d.text}</span>
              </div>
            ))}
            {con > 0 && (
              <div className="dong con-nua">
                <span className="danh" /><span>… còn {con} điều kiện</span>
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
