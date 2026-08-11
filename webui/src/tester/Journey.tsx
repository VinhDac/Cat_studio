import { useEffect, useRef } from 'react'

export interface DongNk {
  i: number; j: number; co_viec: boolean; lenh_id: string | null; chu: string
}

/** NHẬT KÝ SỐNG — dòng nảy lên đúng lúc nó xảy ra.
 *
 * Khác bản trước (một danh sách tĩnh cuộn được): lúc PHÁT, nó phải tự chạy theo con
 * trỏ. Đó là cả điểm của việc "đọc journey sống" — thấy dòng `đặt Buy Stop` hiện ra
 * đúng nhịp mà lệnh chờ xuất hiện trên chart.
 *
 * Chữ do PYTHON dựng (`nhat_ky.dung_lo_theo_nen`), JS không ghép mẩu nào. Chỉ giữ ~400
 * dòng gần nhất trong DOM — đổ cả 135.000 dòng vào là treo hẳn WebView2.
 */
export default function Journey({ dong, nhay }: {
  dong: DongNk[]
  nhay: (i: number) => void
}) {
  const boc = useRef<HTMLDivElement>(null)
  /* Luôn cuộn xuống cuối khi danh sách đổi. Không sợ giật lúc người ta đang đọc: đang
     DỪNG thì không có dòng mới nào sinh ra, nên `dong` không đổi. Còn sau khi nhảy tới
     một sự kiện thì dòng cuối CHÍNH LÀ sự kiện đó — phải thấy nó ngay. */
  useEffect(() => {
    if (boc.current) boc.current.scrollTop = boc.current.scrollHeight
  }, [dong])

  return (
    <div className="nk">
      <div className="nk-dau">
        <span>Nhật ký — chiến lược phản ứng gì, ở khối nào, vì con số nào</span>
        <span className="nk-dem">{dong.length} dòng gần nhất</span>
      </div>
      <div className="nk-cuon" ref={boc}>
        {dong.map((d, k) => (
          <div key={d.i} className={'nk-dong' + (d.co_viec ? ' co-viec' : '')}
               onClick={() => nhay(d.i)}>{d.chu}</div>
        ))}
      </div>
    </div>
  )
}
