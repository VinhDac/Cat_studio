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

/** Khoá màu (do Python suy, xem `api._mau_khoi`) → biến CSS.
 *
 * Trước đây chỉ có hai màu: xanh cho Bắt đầu, **cam cho MỌI khối hành động** — nên nhìn
 * xa thì Kiểm tra ĐK, Vào lệnh, Sửa lệnh giống hệt nhau.
 *
 * Một cái lợi kèm theo: cam đang mang hai nghĩa cùng lúc — "khối hành động" và "đang
 * chọn / số thứ tự". Đẩy khối hành động sang màu riêng thì cam chỉ còn nghĩa *của ta ·
 * đang chọn*, và viền chọn nổi hẳn lên. */
const MAU: Record<string, string> = {
  start: 'var(--action)',
  hoi: 'var(--khoi-hoi)',
  mua: 'var(--ok)',
  ban: 'var(--err)',
  sua: 'var(--khoi-sua)',
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
  const laVa = card.lines[0]?.type === 'check_cond'
  const mau = card.mau ?? (laStart ? 'start' : 'hoi')
  /* Hướng dùng HÌNH chứ không chỉ dùng màu — cùng ngôn ngữ với chart (core.md §12.17),
     và đọc được cả khi mù màu. */
  const mui = mau === 'mua' ? '▲' : mau === 'ban' ? '▼' : ''

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

        {/* `--mau-khoi` đặt trên chính dải tiêu đề: cả thanh trái lẫn nền nhuộm đều đọc
            từ nó, nên đổi một chỗ là đổi cả hai. */}
        <div className={'dau mau-' + mau} style={{ '--mau-khoi': MAU[mau] ?? MAU.hoi
                                                 } as React.CSSProperties}>
          <span className="dai-mau" />
          {mui ? <span className="mui-huong" aria-hidden>{mui}</span>
               : <IconNet name={icon} size={13} />}
          <span className="ten" title={card.title}>{card.title}</span>
        </div>

        {hien.length > 0 && (
          /* Tooltip là CÂU ĐẦY ĐỦ. Trên hộp chỉ để dòng ngắn — mỗi trường một dòng —
             vì nhìn hộp là để liếc ra ngay khối làm gì; rê chuột mới cần đủ chi tiết.

             Khối Bắt đầu CŨNG có thân: nhịp chạy ("Mỗi nến M5") là dòng do Python sinh
             từ khoá `nhip`. Trước đây nó là chữ gõ tay trong TÊN khối, nên đổi nhịp thì
             khối vẫn ghi số cũ. Điều kiện ở đây vì thế phải là "có dòng nào không",
             không phải "có phải khối Bắt đầu không". */
          <div className="than" title={card.mo_ta}>
            {hien.map((d, i) => (
              <div key={i} className="dong">
                {/* "và" CHỈ đúng với khối kiểm tra: ở đó mỗi dòng là một điều kiện nối
                    nhau bằng VÀ, phải ghi ra để không ai đoán là HOẶC. Ở khối vào/sửa
                    lệnh, mỗi dòng là một TRƯỜNG (lot, đệm, SL, TP) — dán "và" vào là
                    nói sai. */}
                <span className="danh">{laVa && i > 0 ? 'và' : ''}</span>
                <span>{d.text}</span>
              </div>
            ))}
            {con > 0 && (
              <div className="dong con-nua">
                <span className="danh" /><span>… còn {con} dòng nữa</span>
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
