import { useState } from 'react'
import { chotSo, locSo } from '../so'
import type { Bootstrap, ThamSo } from '../types'
import Modal from './Modal'
import Icon from './Icon'

/** Bảng THAM SỐ của chiến lược — hằng số CÓ TÊN.
 *
 *  Vì sao cần: ngưỡng nén được hỏi ở CẢ HAI sơ đồ — Entry hỏi "còn nén không", Manage
 *  hỏi "nén tan chưa". Gõ số thẳng vào hai nơi thì sửa một chỗ là hai vế lệch nhau
 *  ÂM THẦM: chiến lược vào lệnh theo một ngưỡng và huỷ lệnh theo ngưỡng khác.
 *
 *  Và đơn vị là BẮT BUỘC — đó là hợp đồng chuẩn hoá của D_02: mỗi con số phải mang một
 *  đơn vị bất biến (bps của giá · nến · × ATR · × R), không bao giờ là pip hay đô.
 */
export default function ThamSoDialog({ dsGoc, boot, dangDung, onLuu, onDong }: {
  dsGoc: ThamSo[]
  boot: Bootstrap
  /** Tên tham số đang thật sự được khối nào đó dùng — cái nào không, nói ra. */
  dangDung: Set<string>
  onLuu: (ds: ThamSo[]) => void
  onDong: () => void
}) {
  const [ds, setDs] = useState<ThamSo[]>(() => JSON.parse(JSON.stringify(dsGoc)))
  /** Bản nháp đang gõ, theo chỉ số dòng — xem chú thích ở ô giá trị. */
  const [nhap, datNhap] = useState<Record<number, string>>({})

  const sua = (i: number, k: keyof ThamSo, v: string | number) =>
    setDs(x => x.map((t, j) => (j === i ? { ...t, [k]: v } : t)))

  const trung = (i: number) =>
    ds.some((t, j) => j !== i && t.ten.trim() === ds[i].ten.trim())

  return (
    <Modal title="Tham số của chiến lược" width={820} onClose={onDong}
           footer={
             <>
               <div className="xem-truoc">
                 {ds.length} tham số · sửa ở đây là mọi khối dùng nó đổi theo
               </div>
               <button className="nut" onClick={onDong}>Huỷ</button>
               {/* Ô trùng tên đã tô đỏ từ trước, nhưng vẫn LƯU được — mà lưu là mất
                   thật: `normalize_tham_so` giữ dòng ĐẦU và vứt phần sau, trong khi bộ
                   chạy lại đọc dòng CUỐI. Chặn ngay ở nút thì không ai đi tới chỗ đó. */}
               <button className="nut chinh"
                       disabled={ds.some((_, i) => trung(i))}
                       title={ds.some((_, i) => trung(i))
                         ? 'Còn tham số trùng tên — sửa cho mỗi tên chỉ xuất hiện một lần'
                         : undefined}
                       onClick={() => onLuu(ds)}>Lưu</button>
             </>
           }>
      <div className="chu-dan">
        Mỗi con số liên quan tới giá phải mang <b>một đơn vị bất biến</b> — bps của giá,
        số nến, bội ATR, bội R. <b>Không pip, không đô.</b> Nhờ vậy cùng một bộ số mang
        cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.
        <br />
        <b>Đơn vị quyết định tham số này dùng được ở đâu:</b> ô số chỉ mời những tham
        số mang <b>đúng</b> đơn vị của nó — nên <code>chu_ky_atr</code> (nến) không bao
        giờ hiện ra ở ô Stop Loss. Một cái tên chỉ mang một nghĩa; cần hai nghĩa thì đặt
        hai tham số.
      </div>

      <table className="bang-tham-so">
        <thead>
          <tr>
            <th>Tên (khối gọi bằng tên này)</th><th>Nhãn</th>
            <th>Giá trị</th><th>Đơn vị</th><th>Ghi chú</th><th />
          </tr>
        </thead>
        <tbody>
          {ds.map((t, i) => (
            <tr key={i} className={!dangDung.has(t.ten) ? ' khong-dung' : ''}>
              <td>
                <input className={'o mono' + (trung(i) ? ' loi' : '')}
                       value={t.ten} spellCheck={false}
                       title={trung(i) ? 'Trùng tên với một tham số khác'
                         : dangDung.has(t.ten) ? '' : 'Chưa khối nào dùng tham số này'}
                       onChange={e => sua(i, 'ten', e.target.value)} />
              </td>
              <td><input className="o" value={t.nhan}
                         onChange={e => sua(i, 'nhan', e.target.value)} /></td>
              {/* ⚠ Chỗ `parseFloat` CUỐI CÙNG của app. Nó nuốt dấu chấm y hệt lỗi đã
                  sửa ở ô số bên `ActionDialog`: gõ `1` `.` `5` thì `parseFloat("1.")`
                  ra `1`, state không đổi, React ghi đè ô về `"1"`. Và gõ chữ ra `NaN`,
                  `NaN` đi thẳng vào bảng tham số. Giờ dùng chung `locSo`/`chotSo`. */}
              <td>
                <input className="o so nho" inputMode="decimal" spellCheck={false}
                       value={nhap[i] ?? t.gia_tri}
                       onChange={e => {
                         const { chu, so } = locSo(e.target.value)
                         datNhap(x => ({ ...x, [i]: chu }))
                         if (so !== null) sua(i, 'gia_tri', so)
                       }}
                       onBlur={() => {
                         const v = nhap[i]
                         if (v !== undefined && locSo(v).so === null) {
                           sua(i, 'gia_tri', chotSo(v))
                         }
                         datNhap(x => { const y = { ...x }; delete y[i]; return y })
                       }} />
              </td>
              {/* ⚠ Ô này TỪNG là chữ tự do, và cột đó âm thầm mục: sơ đồ mẫu mang
                  `"× ATR vùng"` — một chuỗi không tồn tại ở đâu cả, rác từ lần đổi tên
                  vùng→zone, không ai bắt được vì hồi đó chưa có gì đọc nó.
                  Giờ nó là một KHOÁ, và nó quyết định tham số này được mời vào ô nào:
                  `chu_ky_atr` (nến) không bao giờ hiện ra ở ô Stop Loss. */}
              <td>
                <select className={'o nho' + (t.don_vi ? '' : ' loi')}
                        value={t.don_vi}
                        title={t.don_vi ? undefined
                          : 'Chưa có đơn vị thì tham số này không hiện ra ở ô nào cả'}
                        onChange={e => sua(i, 'don_vi', e.target.value)}>
                  <option value="">— chọn —</option>
                  <optgroup label="Quy đổi">
                    {Object.entries(boot.don_vi).map(([k, v]) =>
                      <option key={k} value={k}>{v}</option>)}
                  </optgroup>
                  <optgroup label="Đếm">
                    {Object.entries(boot.don_vi_dem).map(([k, v]) =>
                      <option key={k} value={k}>{v}</option>)}
                  </optgroup>
                </select>
              </td>
              <td><input className="o" value={t.ghi_chu}
                         onChange={e => sua(i, 'ghi_chu', e.target.value)} /></td>
              <td>
                <button className="nut nho" title="Xoá tham số"
                        onClick={() => setDs(x => x.filter((_, j) => j !== i))}>✕</button>
              </td>
            </tr>
          ))}
          {ds.length === 0 && (
            <tr><td colSpan={6} className="dong rong">
              chưa có tham số nào — số gõ thẳng vào khối vẫn chạy, nhưng sửa hai nơi
              thì dễ lệch
            </td></tr>
          )}
        </tbody>
      </table>

      <div className="hang nut-hang">
        <button className="nut" onClick={() => setDs(x => [...x, {
          ten: `tham_so_${x.length + 1}`, nhan: '', gia_tri: 1, don_vi: '', ghi_chu: '',
        }])}><Icon name="plus" /> Thêm tham số</button>
      </div>
    </Modal>
  )
}
