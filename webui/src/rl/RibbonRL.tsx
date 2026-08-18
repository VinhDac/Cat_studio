import { type ReactNode } from 'react'

/** RIBBON của cửa sổ RL.
 *
 *     core.md §18.6.2
 *
 * Bê nguyên bộ áo `.ribbon` / `.nhom-ribbon` / `.nut-lon` của cửa sổ vẽ — KHÔNG dựng
 * lại. Hai cửa sổ khác nhau ở NỘI DUNG nhóm, không ở cái vỏ; dựng lại là ngày mai sửa
 * màu một chỗ thì chỗ kia trôi đi.
 *
 * ⚠ Ribbon này cố ý MỎNG: chỉ Chạy · Dừng · hai núm vặn giữa hai lượt · một nút mở cửa
 * sổ ⚙. Bản cũ có sáu nút thả xuống, và cả sáu đều là đồ đặt-một-lần — sáu panel setup
 * phục vụ hai cái nút hành động. Lý do đầy đủ nằm ở `CaiDatLuot.tsx`.
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

/** Ô NHẬP ngay trên ribbon — cho đúng mấy núm vặn giữa hai lượt.
 *
 * ⭐ Không phải nút, không mở gì cả: gõ thẳng. Hai con số này (số sơ đồ · hạt giống) là
 * thứ đổi nhiều nhất trong một buổi, mà bắt mở một hộp thoại để sửa một con số thì lần
 * thứ mười là bực. Mọi thứ còn lại nằm ở cửa sổ ⚙ — xem `CaiDatLuot`. */
export function ONhap({ nhan, gt, dat, rong = 70 }: {
  nhan: string; gt: number; dat: (n: number) => void; rong?: number
}) {
  return (
    <label className="rl-o-ribbon" style={{ width: rong }}>
      <span>{nhan}</span>
      <input type="number" value={gt} onChange={e => dat(+e.target.value)} />
    </label>
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
  cai_dat: <svg viewBox="0 0 22 22" width="22" height="22"><circle {...S} cx="11" cy="11" r="3" /><path {...S} d="M11 2.6v2.2M11 17.2v2.2M2.6 11h2.2M17.2 11h2.2M5.1 5.1l1.6 1.6M15.3 15.3l1.6 1.6M16.9 5.1l-1.6 1.6M6.7 15.3l-1.6 1.6" /></svg>,
  du_lieu: <svg viewBox="0 0 22 22" width="22" height="22"><ellipse {...S} cx="11" cy="5.6" rx="6.8" ry="2.6" /><path {...S} d="M4.2 5.6v10.8c0 1.4 3 2.6 6.8 2.6s6.8-1.2 6.8-2.6V5.6" /><path {...S} d="M4.2 11c0 1.4 3 2.6 6.8 2.6s6.8-1.2 6.8-2.6" /></svg>,
}
