export interface BangCat {
  toan_hang: { ten: string; gia_tri: unknown }[]
  engine: { ten: string; gia_tri: unknown }[]
  tai_khoan: { ten: string; gia_tri: unknown }[]
  lenh: {
    id: string; huong: string; da_khop: boolean
    gia_vao: number | null; sl: number | null; tp: number | null
    lai_R: number | null; sl_hoa_von: boolean
  }[]
}

/** BẢNG SỐ LIỆU bên phải — bốn khối, MỖI KHỐI MỘT NGUỒN RÕ RÀNG.
 *
 * Vì sao phải chia bốn chứ không đổ chung một danh sách: toán hạng nhóm "Lệnh này"
 * KHÔNG có một giá trị duy nhất tại nến i — Manage chạy một lượt cho MỖI lệnh đang
 * sống, nên mỗi lệnh một bộ số. Ép chúng thành một con số là bảng bắt đầu nói khác
 * nhật ký, đúng lúc đang debug (core.md §12.9).
 *
 * Mọi con số ở đây do Python đọc từ CỘT đã ghi lúc chạy, không phải hỏi lại sổ lệnh —
 * sổ đang ở trạng thái cuối backtest, hỏi lại là con trỏ nào cũng ra một đáp án.
 */
export default function BangSoLieu({ k, digits }: { k: BangCat | null; digits: number }) {
  if (!k) return <div className="bang-trong">chưa chạy</div>
  const so = (v: number | string | boolean | null) => {
    if (v === null || v === undefined) return '—'
    if (typeof v === 'boolean') return v ? 'đúng' : 'sai'
    if (typeof v === 'string') return v
    return Number.isInteger(v) ? String(v) : v.toFixed(Math.max(2, digits))
  }
  const khoi = (ten: string, ds: { ten: string; gia_tri: unknown }[]) => (
    <div className="bang-khoi" key={ten}>
      <div className="bang-ten">{ten}</div>
      <table><tbody>
        {ds.map(d => (
          <tr key={d.ten}>
            <td>{d.ten}</td>
            <td className="mono">{so(d.gia_tri as never)}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  )

  return (
    <div className="bang-so-lieu">
      {khoi('Toán hạng đang dùng', k.toan_hang)}
      {khoi('Vùng nén (engine)', k.engine)}
      {khoi('Tài khoản', k.tai_khoan)}
      <div className="bang-khoi">
        <div className="bang-ten">Lệnh đang sống ({k.lenh.length})</div>
        {k.lenh.length === 0
          ? <div className="bang-rong">không có lệnh nào</div>
          : (
            <table className="bang-lenh"><thead>
              <tr><th>lệnh</th><th>vào</th><th>SL</th><th>TP</th><th>R</th></tr>
            </thead><tbody>
              {k.lenh.map(l => (
                <tr key={l.id} className={l.da_khop ? '' : 'cho'}>
                  <td>
                    <span className={l.huong === 'mua' ? 'mua' : 'ban'}>
                      {l.huong === 'mua' ? '▲' : '▼'}
                    </span> {l.id}
                    {l.sl_hoa_von && <span className="the-nho" title="SL đã ở hoà vốn">hoà vốn</span>}
                  </td>
                  <td className="mono">{so(l.gia_vao)}</td>
                  <td className="mono">{so(l.sl)}</td>
                  <td className="mono">{so(l.tp)}</td>
                  <td className={'mono ' + ((l.lai_R ?? 0) >= 0 ? 'lai' : 'lo')}>
                    {l.lai_R == null ? 'chờ' : l.lai_R.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody></table>
          )}
      </div>
    </div>
  )
}
