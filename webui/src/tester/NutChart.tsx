import { chu, useNgon } from '../i18n'
import IconNet from '../components/Icon'
import type { KieuChart } from './Chart'

/** CỤM NÚT XEM CHART — dùng chung cho Strategy Tester và Live.
 *
 * ⚠ Ở đây chứ không viết hai lần: `Chart` đã là component dùng chung, thì cái điều
 * khiển nó cũng phải vậy. Thêm một kiểu vẽ là sửa một chỗ, cả hai cửa sổ có ngay.
 *
 * Toàn ICON, không chữ — thanh công cụ live vốn đã phải nhường chỗ cho đèn kết nối và
 * badge tài khoản. Nghĩa nằm ở `title`, rê chuột là ra.
 */
const KIEU: [KieuChart, string, string][] = [
  ['nen', 'kieu-nen', chu('Nến')],
  ['bar', 'kieu-bar', 'Thanh (bar)'],
  ['line', 'kieu-line', chu('Đường')],
]

export default function NutChart({ tf, dsTf, datTf, kieu, datKieu, mauThuong,
                                   datMau, hienLenh, datHienLenh,
                                   hienZone, datHienZone, veHienTai }: {
  tf: number
  /** `[nhãn, số phút]` — do cửa sổ truyền vào, vì hai nơi có bộ khung khác nhau. */
  dsTf: readonly (readonly [string, number])[]
  datTf: (p: number) => void
  kieu: KieuChart
  datKieu: (k: KieuChart) => void
  mauThuong: boolean
  datMau: (v: boolean) => void
  hienLenh: boolean
  datHienLenh: (v: boolean) => void
  hienZone: boolean
  datHienZone: (v: boolean) => void
  /** `null` = đang bám nến hiện tại, nút tắt. Nút sáng thường trực là một nút chết. */
  veHienTai: (() => void) | null
}) {
  useNgon()   // đổi ngôn ngữ → vẽ lại (xem `i18n.ts`)
  const nut = (icon: string, ten: string, on: () => void, bat = false, tat = false) => (
    <button className={'tb-nut' + (bat ? ' bat' : '')} title={ten}
            disabled={tat} onClick={on}><IconNet name={icon} size={15} /></button>
  )

  return (
    <>
      <select className="o nho" value={tf} onChange={e => datTf(+e.target.value)}
              title={chu("Khung hiển thị — chỉ đổi CÁCH VẼ")}>
        {dsTf.map(([t, p]) => <option key={t} value={p}>{t}</option>)}
      </select>
      <span className="tb-ngan" />
      {KIEU.map(([k, ic, ten]) =>
        <span key={k}>{nut(ic, ten, () => datKieu(k), kieu === k)}</span>)}
      <span className="tb-ngan" />
      {nut('ve-mau', mauThuong ? chu('Nến về màu xám (để dành xanh/đỏ cho lãi lỗ)')
                               : chu('Nến xanh/đỏ như thường'),
           () => datMau(!mauThuong), mauThuong)}
      {nut('an-lenh', hienLenh ? chu('Ẩn visual vào lệnh / sửa lệnh') : chu('Hiện lại visual lệnh'),
           () => datHienLenh(!hienLenh), !hienLenh)}
      {/* Zone là PHÔNG NỀN. Mặc định bật, nhưng lệnh mới là nhân vật chính — thấy
          vướng là tắt được ngay, không phải chịu đựng. */}
      {nut('zone', hienZone ? chu('Ẩn phông zone (vùng nén)') : chu('Hiện phông zone (vùng nén)'),
           () => datHienZone(!hienZone), !hienZone)}
      {/* Chỉ bấm được khi đã kéo lệch khỏi mép phải — xem chú thích `veHienTai`. */}
      {nut('ve-nay', chu('Về nến hiện tại'), () => veHienTai?.(), false, !veHienTai)}
    </>
  )
}
