import { useEffect, useRef, useState, type ReactNode } from 'react'

/** RIBBON của cửa sổ RL.
 *
 *     core.md §18.6.2
 *
 * Bê nguyên bộ áo `.ribbon` / `.nhom-ribbon` / `.nut-lon` của cửa sổ vẽ — KHÔNG dựng
 * lại. Hai cửa sổ khác nhau ở NỘI DUNG nhóm, không ở cái vỏ; dựng lại là ngày mai sửa
 * màu một chỗ thì chỗ kia trôi đi.
 *
 * Khác Home đúng một chỗ: nút ở đây mở một **panel có ô nhập**, không phải một menu
 * dòng chữ. `ContextMenu` chỉ nhận `MucPhai[]` nên không dùng lại được — nhưng cái vỏ
 * nút thì dùng lại nguyên.
 */

export function Nhom({ ten, children }: { ten: string; children: ReactNode }) {
  return (
    <div className="nhom-ribbon">
      <div className="cac-nut">{children}</div>
      <div className="ten-nhom">{ten}</div>
    </div>
  )
}

export function Nut({ ten, icon, onClick, tat, title, nhan }: {
  ten: string; icon: ReactNode; onClick?: () => void; tat?: boolean; title?: string
  /** Chữ nhỏ dưới tên — giá trị đang đặt, để khỏi phải mở panel ra mới biết. */
  nhan?: string
}) {
  return (
    <button className="nut-lon" onClick={onClick} disabled={tat} title={title || ten}>
      <span className="hinh">{icon}</span>
      <span>{ten}</span>
      {nhan && <span className="rl-nut-nhan">{nhan}</span>}
    </button>
  )
}

/** Nút ribbon mở ra một PANEL có ô nhập. Đóng khi bấm ra ngoài hoặc Esc.
 *
 * ⚠ Panel `position: fixed` theo toạ độ nút, không `absolute` trong ribbon: ribbon có
 * `overflow` riêng nên panel dài sẽ bị cắt cụt — mà panel Kho đồ thì dài thật. */
export function NutPanel({ ten, icon, nhan, rong = 340, children }: {
  ten: string; icon: ReactNode; nhan?: string; rong?: number
  children: ReactNode | (() => ReactNode)
}) {
  const [mo, setMo] = useState<{ x: number; y: number } | null>(null)
  const boc = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mo) return
    const ngoai = (e: MouseEvent) => {
      if (!boc.current?.contains(e.target as Node)) setMo(null)
    }
    const phim = (e: KeyboardEvent) => { if (e.key === 'Escape') setMo(null) }
    // `mousedown` chứ không `click`: bấm vào một ô nhập trong panel rồi nhả chuột ở
    // ngoài (kéo chọn chữ) sẽ tính là click ngoài và panel đóng giữa lúc đang gõ.
    window.addEventListener('mousedown', ngoai)
    window.addEventListener('keydown', phim)
    return () => {
      window.removeEventListener('mousedown', ngoai)
      window.removeEventListener('keydown', phim)
    }
  }, [mo])

  return (
    <>
      <button className={'nut-lon' + (mo ? ' dang-mo' : '')}
              onClick={e => {
                const r = e.currentTarget.getBoundingClientRect()
                setMo(v => (v ? null : { x: r.left, y: r.bottom + 2 }))
              }}>
        <span className="hinh">{icon}</span>
        <span>{ten} ▾</span>
        {nhan && <span className="rl-nut-nhan">{nhan}</span>}
      </button>
      {mo && (
        <div ref={boc} className="rl-panel"
             style={{ left: Math.min(mo.x, window.innerWidth - rong - 12),
                      top: mo.y, width: rong }}>
          {typeof children === 'function' ? children() : children}
        </div>
      )}
    </>
  )
}

const S = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.5,
            strokeLinecap: 'round', strokeLinejoin: 'round' } as const

export const IR = {
  chay: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M6.5 4.2l11 6.8-11 6.8z" /></svg>,
  dung: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="5.5" y="5.5" width="11" height="11" rx="1.4" /></svg>,
  kho: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="3.2" y="3.2" width="6.6" height="6.6" rx="1.2" /><rect {...S} x="12.2" y="3.2" width="6.6" height="6.6" rx="1.2" /><rect {...S} x="3.2" y="12.2" width="6.6" height="6.6" rx="1.2" /><path {...S} d="M13 15.5h5M15.5 13v5" /></svg>,
  tran: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M3 5.5h16" /><path {...S} d="M11 5.5v4M11 9.5H6.5v3M11 9.5h4.5v3" /><circle {...S} cx="6.5" cy="14.6" r="2" /><circle {...S} cx="15.5" cy="14.6" r="2" /></svg>,
  cua: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M4 3.5v15M18 3.5v15" /><path {...S} d="M4 11h4.5M13.5 11H18" /><circle {...S} cx="11" cy="11" r="2.4" /></svg>,
  thang: <svg viewBox="0 0 22 22" width="22" height="22"><path {...S} d="M3 18.5h16" /><path {...S} d="M5.5 18.5v-3M9 18.5v-6M12.5 18.5v-9M16 18.5v-12" /><circle {...S} cx="5.5" cy="15" r="1.1" /><circle {...S} cx="9" cy="12" r="1.1" /><circle {...S} cx="12.5" cy="9" r="1.1" /><circle {...S} cx="16" cy="6" r="1.1" /></svg>,
  ngan: <svg viewBox="0 0 22 22" width="22" height="22"><rect {...S} x="3.2" y="6" width="15.6" height="10.5" rx="1.6" /><path {...S} d="M3.2 9.5h15.6" /><path {...S} d="M6.5 13h3" /></svg>,
  du_lieu: <svg viewBox="0 0 22 22" width="22" height="22"><ellipse {...S} cx="11" cy="5.6" rx="6.8" ry="2.6" /><path {...S} d="M4.2 5.6v10.8c0 1.4 3 2.6 6.8 2.6s6.8-1.2 6.8-2.6V5.6" /><path {...S} d="M4.2 11c0 1.4 3 2.6 6.8 2.6s6.8-1.2 6.8-2.6" /></svg>,
}
