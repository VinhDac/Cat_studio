import { useCallback, useState, type ReactNode } from 'react'

/** Bảng dưới cao tối thiểu lúc kéo, và cao khi đã gập (vừa đủ hàng tab). */
const CAO_TOI_THIEU = 90
const CAO_GAP = 33

/** VỎ BẢNG DƯỚI — giữ chiều cao, chuyện cụp/mở, và hàng tab. Nội dung do tab quyết.
 *
 * Bê nguyên `.bang-duoi` của cửa sổ chính: thanh kéo ở mép trên, hàng tab bên trái,
 * `▼/▲` ở góc phải, nhấp đúp hàng tab cũng cụp. Nút gập nằm trên chính bảng chứ không ở
 * góc thanh công cụ — tay đang ở đâu thì nút ở đó.
 *
 * ⚠ VỎ NÀY DÙNG CHUNG cho cả Strategy Tester lẫn Live — hai cửa sổ khác nhau ở NỘI
 * DUNG tab, không ở cái vỏ. Trước đây Live tự dựng lại hàng tab và ra một bảng trông
 * khác hẳn: mất thanh kéo, mất nút gập, mất số đếm, chữ so le. Nên tab là THAM SỐ.
 */

export interface TabDuoi {
  khoa: string
  nhan: string
  /** Số hiện cạnh nhãn (số dòng nhật ký, số vấn đề…). */
  dem?: number
  ve: () => ReactNode
  /** Nút riêng của tab, hiện ở góc phải khi tab đang mở. */
  nut?: ReactNode
}
export default function BangDuoi({ tabs, epTab, epLan = 0 }: {
  tabs: TabDuoi[]
  /** Ép mở một tab từ ngoài (chọn một mục lịch sử → nhảy sang Thống kê). */
  epTab?: string
  /** ĐẾM SỐ LẦN ÉP. Tăng lên là ép lại, kể cả khi `epTab` không đổi giá trị. */
  epLan?: number
}) {
  const [tab, setTab] = useState(tabs[0]?.khoa ?? '')
  const [cao, setCao] = useState(210)
  const [gap, setGap] = useState(false)

  /* Ép tab từ ngoài: chọn một mục lịch sử = nhảy thẳng sang Thống kê và mở bảng ra.
     Bắt người dùng bấm thêm hai nhát mới thấy thứ vừa chọn thì danh sách kia vô dụng. */
  /* ⚠ Chốt theo LẦN ép, không theo GIÁ TRỊ. Bản trước so `epTab !== epCu`: chọn mục
     lịch sử thứ nhất thì nhảy sang Thống kê (đúng), người dùng bấm sang tab Nhật ký,
     rồi chọn mục lịch sử THỨ HAI — `epTab` vẫn là 'thong-ke' nên không nhảy nữa, trông
     y như bấm hụt. Cùng một đích vẫn là một lần ép mới. */
  const [epCu, setEpCu] = useState(`${epLan}|${epTab ?? ''}`)
  const epNay = `${epLan}|${epTab ?? ''}`
  if (epTab && epNay !== epCu) { setEpCu(epNay); setTab(epTab); setGap(false) }

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
  const doiTab = (t: string) => {
    if (t === tab && !gap) setGap(true)
    else { setTab(t); setGap(false) }
  }

  const dang = tabs.find(t => t.khoa === tab) ?? tabs[0]

  return (
    <div className="nk" style={{ height: gap ? CAO_GAP : cao }}>
      <div className="thanh-keo" onMouseDown={batDauKeo} title="Kéo để chỉnh chiều cao" />
      <div className="hang-tab" onDoubleClick={() => setGap(v => !v)}>
        {tabs.map(t => (
          <button key={t.khoa} className={'tab' + (tab === t.khoa && !gap ? ' dang' : '')}
                  onClick={() => doiTab(t.khoa)}>
            {t.nhan}{t.dem != null && <span className="nk-dem">{t.dem}</span>}
          </button>
        ))}
        <span className="day" />
        {/* Chỉ hiện nút của tab ĐANG MỞ — giống cửa sổ chính giấu "Xoá nhật ký" khi
            đang ở tab Vấn đề. */}
        {!gap && dang?.nut}
        <button className="nut-nho nut-gap" onClick={() => setGap(v => !v)}
                title={gap ? 'Mở bảng' : 'Gập bảng xuống'}>
          {gap ? '▲' : '▼'}
        </button>
      </div>

      {/* ⚠ `ve()` gọi như HÀM THƯỜNG, nên tab KHÔNG ĐƯỢC dùng hook nào bên trong.
          Hook trong đó sẽ thành hook của chính `BangDuoi`, và đổi sang tab có số hook
          khác là React ném lỗi — cả cửa sổ chết. Đã cắn một lần thật ở cửa sổ cài đặt
          RL (xem chú thích `MUC` trong `rl/CaiDatLuot.tsx`).
          Cần hook thì làm tab ấy thành component và dựng bằng JSX. */}
      {!gap && dang?.ve()}
    </div>
  )
}
