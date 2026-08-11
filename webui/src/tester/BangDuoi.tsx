import { useCallback, useState } from 'react'
import Journey, { type DongNk } from './Journey'
import ThongKe from './ThongKe'

/** Bảng dưới cao tối thiểu lúc kéo, và cao khi đã gập (vừa đủ hàng tab). */
const CAO_TOI_THIEU = 90
const CAO_GAP = 33

/** VỎ BẢNG DƯỚI — giữ chiều cao, chuyện cụp/mở, và hàng tab. Nội dung do tab quyết.
 *
 * Bê nguyên `.bang-duoi` của cửa sổ chính: thanh kéo ở mép trên, hàng tab bên trái,
 * `▼/▲` ở góc phải, nhấp đúp hàng tab cũng cụp. Nút gập nằm trên chính bảng chứ không ở
 * góc thanh công cụ — tay đang ở đâu thì nút ở đó.
 *
 * Tách khỏi `Journey` vì giờ có hai tab: vỏ là chuyện của bảng, danh sách dòng là
 * chuyện của nhật ký. Gộp lại thì thêm tab thứ ba là phải sửa cả hai.
 */
export default function BangDuoi({ dong, jBayGio, nhay, ghiFile }: {
  dong: DongNk[]
  jBayGio: number
  nhay: (i: number) => void
  ghiFile: () => void
}) {
  const [tab, setTab] = useState<'nhat-ky' | 'thong-ke'>('nhat-ky')
  const [cao, setCao] = useState(210)
  const [gap, setGap] = useState(false)
  const [chiViec, setChiViec] = useState(false)

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

  /** Bấm vào tab thì MỞ luôn bảng ra: đang gập mà bấm tab rồi chẳng thấy gì thì tưởng
   *  hỏng. Bấm lại đúng tab đang mở thì gập — nút gập thứ hai, tiện tay. */
  const doiTab = (t: 'nhat-ky' | 'thong-ke') => {
    if (t === tab && !gap) setGap(true)
    else { setTab(t); setGap(false) }
  }

  return (
    <div className="nk" style={{ height: gap ? CAO_GAP : cao }}>
      <div className="thanh-keo" onMouseDown={batDauKeo} title="Kéo để chỉnh chiều cao" />
      <div className="hang-tab" onDoubleClick={() => setGap(v => !v)}>
        <button className={'tab' + (tab === 'nhat-ky' && !gap ? ' dang' : '')}
                onClick={() => doiTab('nhat-ky')}>
          Nhật ký <span className="nk-dem">{dong.length}</span>
        </button>
        <button className={'tab' + (tab === 'thong-ke' && !gap ? ' dang' : '')}
                onClick={() => doiTab('thong-ke')}>
          Thống kê
        </button>
        <span className="day" />
        {/* Chỉ hiện nút của tab đang mở — giống cửa sổ chính giấu "Xoá nhật ký" khi
            đang ở tab Vấn đề. */}
        {!gap && tab === 'nhat-ky' && <>
          <label className="nk-loc">
            <input type="checkbox" checked={chiViec}
                   onChange={e => setChiViec(e.target.checked)} />
            chỉ dòng có việc
          </label>
          <button className="nut-nho" onClick={ghiFile}
                  title="Ghi TOÀN BỘ nhật ký ra .jsonl">Ghi ra file</button>
        </>}
        <button className="nut-nho nut-gap" onClick={() => setGap(v => !v)}
                title={gap ? 'Mở bảng' : 'Gập bảng xuống'}>
          {gap ? '▲' : '▼'}
        </button>
      </div>

      {!gap && (tab === 'nhat-ky'
        ? <Journey dong={dong} jBayGio={jBayGio} nhay={nhay} chiViec={chiViec} />
        : <ThongKe />)}
    </div>
  )
}
