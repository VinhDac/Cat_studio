import { chu, useNgon } from '../i18n'
import { useEffect, useState } from 'react'
import { pyLive } from '../api'
import Modal from '../components/Modal'

/** CỔNG CHỐT — thứ đầu tiên hiện ra khi cửa sổ Live mở.
 *
 * ⚠ Nằm TRONG cửa sổ Live, không phải ở cửa sổ vẽ. Vào bằng Ctrl+L hay bằng nút thì
 * cũng đáp xuống đúng một chỗ, và cửa sổ vẽ không phải gánh thêm một hộp thoại chẳng
 * liên quan gì tới việc vẽ.
 *
 * Không đóng được bằng ✕ hay Esc: đóng nó ra một cửa sổ Live rỗng không biết mình đang
 * chạy gì. Muốn thoát thì đóng cả cửa sổ.
 */
export default function CongChot({ boot, xong }: {
  boot: { goi_y: string; ds_luu: string[]; symbol_mac_dinh: string }
  xong: (ten: string, symbol: string) => void
}) {
  useNgon()   // đổi ngôn ngữ → vẽ lại (xem `i18n.ts`)
  // '' = dùng sơ đồ đang mở ở cửa sổ vẽ. Ưu tiên nó nếu có: người bấm Ctrl+L gần như
  // luôn muốn chạy đúng cái vừa vẽ xong.
  const [chon, setChon] = useState(boot.goi_y ? '' : (boot.ds_luu[0] ?? ''))
  const [symbol, setSymbol] = useState(boot.symbol_mac_dinh || 'XAUUSD')
  const [kn, setKn] = useState<{ noi_duoc: boolean; chu: string; terminal: string
                                 tai_khoan: string; co_symbol: boolean
                                 goi_y: string[] } | null>(null)
  const [dangKiem, setDangKiem] = useState(false)
  const [loi, setLoi] = useState('')

  /** Lỗi của SƠ ĐỒ đang chọn. Hỏi ngay lúc chọn, không đợi bấm "Bắt đầu" — cổng chốt
   *  sinh ra để nói TRƯỚC. `null` = chưa soát xong. */
  const [soDo, setSoDo] = useState<{ ten: string; loi: string[] } | null>(null)

  useEffect(() => { void kiem(symbol) }, [])
  useEffect(() => {
    let bo = false
    setSoDo(null)
    void pyLive.live_soat_so_do(chon).then(r => {
      if (!bo && r.ok && r.value) setSoDo(r.value)
    })
    return () => { bo = true }
  }, [chon])

  async function kiem(s: string) {
    setDangKiem(true); setKn(null)
    // `pyLive` chứ không `py`: cửa sổ này chạy `ApiLive`, không thấy `Api` chính.
    const r = await pyLive.live_kiem_ket_noi(s)
    setDangKiem(false)
    setKn(r.ok && r.value ? r.value : {
      noi_duoc: false, chu: r.error ?? chu('không gọi được sang Python'),
      terminal: '', tai_khoan: '', co_symbol: false, goi_y: [],
    })
  }

  const noiDuoc = !!kn?.noi_duoc && !!kn?.co_symbol
  const soDoOk = !!soDo && soDo.loi.length === 0

  return (
    /* ✕ ĐÓNG HẲN CỬA SỔ, không phải đóng hộp thoại. Bỏ qua cổng chốt thì còn lại một
       cửa sổ Live rỗng không biết mình đang chạy gì — tệ hơn hẳn so với đóng luôn. */
    <Modal title="Chạy Live — chốt trước khi bắt đầu" width={540} khoaNen khoaEsc
           onClose={() => void pyLive.cua_so_dong()}
           footer={
             <>
               {loi && <span className="loi-ghi">{loi}</span>}
               <button className="nut do" disabled={!noiDuoc || !soDoOk}
                       onClick={async () => {
                         setLoi('')
                         const r = await pyLive.live_chon(chon, symbol.trim().toUpperCase())
                         if (!r.ok) return setLoi(r.error ?? chu('không chạy được'))
                         xong(r.value!.ten, r.value!.symbol)
                       }}>● Bắt đầu</button>
             </>
           }>
      <label className="hang">
        <span className="nhan-o">Chiến lược</span>
        <select className="o" value={chon} onChange={e => setChon(e.target.value)}>
          {boot.goi_y && <option value="">{boot.goi_y} — đang mở ở cửa sổ vẽ</option>}
          {boot.ds_luu.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>

      <label className="hang">
        <span className="nhan-o">Symbol</span>
        <input className="o" value={symbol} spellCheck={false}
               onChange={e => setSymbol(e.target.value.toUpperCase())} />
        <button className="nut" disabled={dangKiem} onClick={() => void kiem(symbol)}>
          {dangKiem ? chu('đang nối…') : 'Kiểm tra'}
        </button>
      </label>

      {/* Lỗi SƠ ĐỒ hiện ngay dưới ô chọn. `validate_process` cố ý dễ tính vì nó soát
          một sơ đồ đang VẼ DỞ; Live hỏi thêm một câu — sơ đồ này có đặt nổi lệnh không.
          Một "Chiến lược 1" mới tinh qua được cái trước nhưng trượt cái sau. */}
      {soDo && soDo.loi.length > 0 && (
        <div className="cd-ket-noi hong">
          <div>⚠ Sơ đồ chưa chạy Live được:</div>
          {soDo.loi.map((m, k) => <div key={k} className="phu">· {m}</div>)}
        </div>
      )}

      {kn && (
        <div className={'cd-ket-noi' + (noiDuoc ? ' duoc' : ' hong')}>
          <div>{noiDuoc ? '✓' : '⚠'} {kn.chu}</div>
          {kn.terminal && (
            <div className="phu">{kn.terminal}
              {kn.tai_khoan && <> · tài khoản {kn.tai_khoan}</>}</div>
          )}
          {kn.goi_y.length > 0 && (
            <div className="phu">sàn này có:{' '}
              {kn.goi_y.map(s => (
                <button key={s} className="cd-goi-y"
                        onClick={() => { setSymbol(s); void kiem(s) }}>{s}</button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="chu-dan">
        Chạy <b>chế độ QUAN SÁT</b> — nối, đo, soi vấn đề, <b>không đặt lệnh nào</b>.
        Sơ đồ còn lỗi thì Python chặn ở đây, không cho qua.
      </div>
    </Modal>
  )
}
