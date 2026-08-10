import { useState } from 'react'
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
               <button className="nut chinh" onClick={() => onLuu(ds)}>Lưu</button>
             </>
           }>
      <div className="chu-dan">
        Mỗi con số liên quan tới giá phải mang <b>một đơn vị bất biến</b> — bps của giá,
        số nến, bội ATR, bội R. <b>Không pip, không đô.</b> Nhờ vậy cùng một bộ số mang
        cùng một ý nghĩa trên vàng, forex, crypto và chỉ số.
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
              <td><input className="o so nho" value={t.gia_tri}
                         onChange={e => sua(i, 'gia_tri', parseFloat(e.target.value))} /></td>
              <td>
                <input className="o nho" value={t.don_vi} list="don-vi-tham-so"
                       onChange={e => sua(i, 'don_vi', e.target.value)} />
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

      <datalist id="don-vi-tham-so">
        {Object.keys(boot.don_vi_tham_so).map(k => <option key={k} value={k} />)}
      </datalist>

      <div className="hang nut-hang">
        <button className="nut" onClick={() => setDs(x => [...x, {
          ten: `tham_so_${x.length + 1}`, nhan: '', gia_tri: 1, don_vi: '', ghi_chu: '',
        }])}><Icon name="plus" /> Thêm tham số</button>
      </div>
    </Modal>
  )
}
