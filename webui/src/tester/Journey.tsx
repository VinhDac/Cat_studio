import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export interface DongNk {
  i: number; j: number; co_viec: boolean; lenh_id: string | null; chu: string
}

/** Một DÃY dòng giống hệt nhau nằm liền nhau, gộp thành một. */
interface Nhom {
  i: number                 // lượt ĐẦU của dãy — bấm vào là nhảy tới đúng đó
  j0: number; j1: number    // nến M1 đầu và cuối của dãy
  co_viec: boolean
  chu: string
  dem: number
}

/** Bảng nhật ký cao tối thiểu lúc kéo, và cao khi đã gập (vừa đủ hàng tab). */
const CAO_TOI_THIEU = 90
const CAO_GAP = 33

/** NHẬT KÝ SỐNG — dòng nảy lên đúng lúc nó xảy ra.
 *
 * Khác bản trước (một danh sách tĩnh cuộn được): lúc PHÁT, nó phải tự chạy theo con
 * trỏ. Đó là cả điểm của việc "đọc journey sống" — thấy dòng `đặt Buy Stop` hiện ra
 * đúng nhịp mà lệnh chờ xuất hiện trên chart.
 *
 * Chữ do PYTHON dựng (`nhat_ky.dung_lo_theo_nen`), JS không ghép mẩu nào. Chỉ giữ ~400
 * dòng gần nhất trong DOM — đổ cả 135.000 dòng vào là treo hẳn WebView2.
 *
 * ⭐ GỘP DÃY LẶP là thứ đáng giá nhất ở đây. Manage chạy nhịp M1 nên MỖI nến M5 đẻ ra 5
 * dòng y hệt nhau: 296 dòng trên màn hình thật ra chỉ là ~60 sự việc, và người dùng phải
 * cuộn qua một bức tường chữ giống nhau để tìm dòng có nghĩa. Gộp lại kèm `×3` vừa gọn
 * 5 lần, vừa TRẢ LỜI THÊM được câu "cổng đó chặn mấy lượt liền" — thứ mà đếm tay không
 * ra. Chỉ gộp dãy LIỀN KỀ, không gộp cách quãng: gộp cách quãng là xáo trộn thứ tự thật.
 */
export default function Journey({ dong, jBayGio, nhay, ghiFile }: {
  dong: DongNk[]
  /** Nến M1 con trỏ đang đứng — quyết định dòng nào được tô sáng. */
  jBayGio: number
  nhay: (i: number) => void
  ghiFile: () => void
}) {
  const boc = useRef<HTMLDivElement>(null)
  const [cao, setCao] = useState(210)
  const [gap, setGap] = useState(false)
  const [chiViec, setChiViec] = useState(false)

  const nhom = useMemo(() => {
    const ra: Nhom[] = []
    for (const d of dong) {
      if (chiViec && !d.co_viec) continue
      const cuoi = ra[ra.length - 1]
      // Dòng CÓ VIỆC không bao giờ bị gộp: hai lần đặt lệnh giống chữ nhau vẫn là hai
      // việc khác nhau, gộp lại là giấu mất một cái.
      if (cuoi && !d.co_viec && !cuoi.co_viec && cuoi.chu === d.chu) {
        cuoi.dem++
        cuoi.j1 = d.j
      } else {
        ra.push({ i: d.i, j0: d.j, j1: d.j, co_viec: d.co_viec, chu: d.chu, dem: 1 })
      }
    }
    return ra
  }, [dong, chiViec])

  /** Nhóm được tô sáng: nhóm GẦN NHẤT tính tới con trỏ, không phải nhóm "trùng đúng nến
   *  hiện tại". Entry chỉ chạy ở biên nến M5 nên 4/5 khung hình không sinh dòng nào —
   *  lấy mốc trùng khít thì phần lớn thời gian màn hình chẳng có gì sáng, mà câu người
   *  dùng cần trả lời là "gần đây nhất chiến lược làm gì", luôn có đáp án. */
  const sang = useMemo(() => {
    let k = -1
    for (let x = 0; x < nhom.length; x++) if (nhom[x].j0 <= jBayGio) k = x
    return k
  }, [nhom, jBayGio])

  /* Luôn cuộn xuống cuối khi danh sách đổi. Không sợ giật lúc người ta đang đọc: đang
     DỪNG thì không có dòng mới nào sinh ra, nên `dong` không đổi. Còn sau khi nhảy tới
     một sự kiện thì dòng cuối CHÍNH LÀ sự kiện đó — phải thấy nó ngay. */
  useEffect(() => {
    if (boc.current) boc.current.scrollTop = boc.current.scrollHeight
  }, [nhom])

  /** Kéo mép trên để chỉnh chiều cao. Bám theo con trỏ cho tới khi thả, kể cả khi chuột
   *  đi ra ngoài cửa sổ — chỉ nghe trên chính thanh kéo thì kéo nhanh một cái là mất
   *  dấu. Giống hệt bảng dưới của cửa sổ chính. */
  const batDauKeo = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setGap(false)
    const y0 = e.clientY
    const cao0 = gap ? CAO_GAP : cao
    const di = (ev: MouseEvent) =>
      setCao(Math.max(CAO_TOI_THIEU, Math.min(600, cao0 + (y0 - ev.clientY))))
    const thoi = () => {
      window.removeEventListener('mousemove', di)
      window.removeEventListener('mouseup', thoi)
    }
    window.addEventListener('mousemove', di)
    window.addEventListener('mouseup', thoi)
  }, [cao, gap])

  return (
    <div className="nk" style={{ height: gap ? CAO_GAP : cao }}>
      <div className="thanh-keo" onMouseDown={batDauKeo} title="Kéo để chỉnh chiều cao" />
      <div className="hang-tab" onDoubleClick={() => setGap(v => !v)}>
        <button className="tab dang" onClick={() => setGap(v => !v)}>
          Nhật ký <span className="nk-dem">{nhom.length}</span>
        </button>
        <span className="day" />
        {!gap && <>
          <label className="nk-loc">
            <input type="checkbox" checked={chiViec}
                   onChange={e => setChiViec(e.target.checked)} />
            chỉ dòng có việc
          </label>
          <button className="nut-nho" onClick={ghiFile}
                  title="Ghi TOÀN BỘ nhật ký ra .jsonl">Ghi ra file</button>
        </>}
        <button className="nut-nho nut-gap" onClick={() => setGap(v => !v)}
                title={gap ? 'Mở nhật ký' : 'Gập nhật ký xuống'}>
          {gap ? '▲' : '▼'}
        </button>
      </div>

      {!gap && (
        <div className="nk-cuon" ref={boc}>
          {nhom.map((n, k) => (
            <div key={n.i}
                 className={'nk-dong' + (n.co_viec ? ' co-viec' : '')
                            + (k === sang ? ' bay-gio' : '')}
                 onClick={() => nhay(n.i)}>
              <span className="chu">{n.chu}</span>
              {n.dem > 1 && <span className="lap" title={`${n.dem} lượt liền nhau giống hệt`}>
                ×{n.dem}
              </span>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
