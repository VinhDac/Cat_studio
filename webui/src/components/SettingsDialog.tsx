import { useState } from 'react'
import { py } from '../api'
import type { BoNen, Bootstrap } from '../types'
import Modal from './Modal'

/** CÀI ĐẶT của app — hai mục: giao diện, và Strategy Test.
 *
 * Điều kiện chạy backtest nằm Ở ĐÂY chứ không ở cửa sổ tester. Cài đặt là thứ đặt một
 * lần rồi quên; để nó trong cửa sổ tester thì mỗi lần bấm ▶ lại phải đi qua một bảng
 * nữa mới chạy được — một thao tác hoá ba. Giờ bấm ▶ ở cửa sổ vẽ là tester mở ra và
 * CHẠY LUÔN bằng đúng những gì lưu ở đây.
 */
export default function SettingsDialog({ boot, doiMauNgay, lamMoiBoot, onDong }: {
  boot: Bootstrap
  doiMauNgay: (mau: string) => void
  /** Nạp lại `boot` sau khi lưu — xem chú thích trong `luu()`. */
  lamMoiBoot: () => Promise<void>
  onDong: () => void
}) {
  const s = boot.settings as Record<string, any>
  const t = (s.test ?? {}) as Record<string, any>
  const [symbol, setSymbol] = useState(String(s.symbol ?? 'XAUUSD'))
  const [accent, setAccent] = useState(String(s.accent ?? '#ffa657'))

  const [tSymbol, setTSymbol] = useState(String(t.symbol ?? 'XAUUSD'))
  const [tu, setTu] = useState(String(t.tu ?? ''))
  const [den, setDen] = useState(String(t.den ?? ''))
  const [spread, setSpread] = useState(Number(t.spread_diem ?? 20))
  const [deposit, setDeposit] = useState(Number(t.deposit ?? 10000))
  const [phi, setPhi] = useState(Number(t.commission ?? 0))
  const [donBay, setDonBay] = useState(Number(t.don_bay ?? 100))
  const [delay, setDelay] = useState(Number(t.delay_ms ?? 60))

  const [nguon, setNguon] = useState<BoNen[]>(boot.nguon ?? [])
  const [ketNoi, setKetNoi] = useState<{
    noi_duoc: boolean; chu: string; terminal: string; tai_khoan: string
    co_symbol: boolean; goi_y: string[]
  } | null>(null)
  const [dangKiem, setDangKiem] = useState(false)

  async function kiemKetNoi() {
    setDangKiem(true); setKetNoi(null)
    const r = await py.nguon_kiem_ket_noi(tSymbol)
    setDangKiem(false)
    // Cả lỗi cầu nối cũng phải hiện ra ở đây: im lặng là đúng thứ nút này sinh ra để chữa.
    setKetNoi(r.ok && r.value ? r.value : {
      noi_duoc: false, chu: r.error ?? 'không gọi được sang Python',
      terminal: '', tai_khoan: '', co_symbol: false, goi_y: [],
    })
  }

  const bo = nguon.find(n => n.symbol === tSymbol)

  const [loiLuu, setLoiLuu] = useState('')

  async function luu() {
    setLoiLuu('')
    // ⚠ PHẢI xem kết quả. Trước đây bỏ qua rồi `onDong()` vô điều kiện, nên đĩa đầy hay
    // mất quyền ghi thì hộp thoại vẫn đóng như đã lưu xong — im lặng, không dấu vết.
    for (const r of [
      await py.save_settings({ symbol, accent }),
      await py.save_test_settings({
        symbol: tSymbol, tu, den, spread_diem: spread,
        deposit, commission: phi, don_bay: donBay, delay_ms: delay,
      }),
    ]) {
      if (!r.ok) return setLoiLuu(r.error ?? 'không lưu được cài đặt')
    }
    // ⚠ NẠP LẠI `boot` rồi mới đóng. `boot` vốn chỉ nạp MỘT LẦN lúc mở app, mà hộp thoại
    // này lấy giá trị ban đầu từ đó — nên lưu xong, mở lại là thấy y nguyên số CŨ, và
    // người dùng kết luận "bấm lưu không lưu được" (thật ra đĩa đã ghi đúng). `bootstrap`
    // chỉ 1 ms / 7 KB nên nạp lại là rẻ nhất, và nó đồng bộ luôn cả danh sách nguồn nến.
    await lamMoiBoot()
    onDong()
  }

  /* KHÔNG còn nút "Tải thêm". Thiếu nến thì chính lần bấm ▶ tự tải đúng phần thiếu rồi
     chạy tiếp (`api._tai_neu_thieu`) — bớt hẳn một bước, và không còn cảnh bấm ▶ rồi bị
     đuổi ngược về đây.

     Luật "không bao giờ tải lén" vẫn giữ, chỉ đổi cách: thay vì bắt bấm thêm một nút,
     tải cứ tải nhưng NÓI RA trên thanh tiến trình kèm số MB.

     Nút Xoá thì ở lại: tải là an toàn và đảo ngược được nên tự động, còn xoá thì không —
     phải do tay người. */
  async function xoa(sym: string) {
    if (!confirm(`Xoá hẳn bộ nến ${sym}?`)) return
    const r = await py.nguon_xoa(sym)
    if (r.ok) setNguon(r.value?.ds ?? [])
  }

  return (
    <Modal title="Cài đặt" width={620} onClose={onDong}
           footer={
             <>
               {loiLuu && <span className="loi-ghi">{loiLuu}</span>}
               <button className="nut" onClick={onDong}>Huỷ</button>
               <button className="nut chinh" onClick={luu}>Lưu</button>
             </>
           }>
      <label className="hang">
        <span className="nhan-o">Mã mặc định</span>
        <input className="o" value={symbol} spellCheck={false}
               onChange={e => setSymbol(e.target.value.toUpperCase())} />
      </label>

      <label className="hang">
        <span className="nhan-o">Màu nhấn</span>
        <div className="cum-mau">
          {Object.entries(boot.accent_presets).map(([ten, mau]) => (
            <button key={ten} title={ten}
                    className={'o-mau' + (mau === accent ? ' dang-chon' : '')}
                    style={{ background: mau }}
                    /* Đổi ngay lúc bấm chứ không đợi Lưu: chọn màu mà không thấy nó
                       trông thế nào thì chọn bằng gì. */
                    onClick={() => { setAccent(mau); doiMauNgay(mau) }} />
          ))}
        </div>
      </label>

      {/* ---------------- STRATEGY TEST ---------------- */}
      <div className="cd-muc">Strategy Test</div>
      {!boot.co_mt5 && (
        <div className="chu-dan canh">
          Máy chưa cài thư viện <code>MetaTrader5</code> — không tải được nến mới.
          Backtest vẫn chạy được trên dữ liệu đã tải.
        </div>
      )}

      <div className="cd-nguon-bang">
        <div className="cd-nguon-dau">Nguồn dữ liệu — nến M1</div>
        {nguon.length === 0
          ? <div className="cd-rong">chưa tải bộ nến nào</div>
          : nguon.map(n => (
            <div key={n.symbol} className="cd-dong">
              <b>{n.symbol}</b>
              <span className="mono">{n.tu_chu} → {n.den_chu}</span>
              <span className="mono">{n.so_nen.toLocaleString('vi')} nến</span>
              <b className="mono">{n.mb} MB</b>
              <button className="nut nho" onClick={() => xoa(n.symbol)}>Xoá</button>
            </div>
          ))}
      </div>

      <div className="hang cd-hang">
        <label>Symbol<input className="o nho" value={tSymbol} spellCheck={false}
               onChange={e => setTSymbol(e.target.value.toUpperCase())} /></label>
        <label>Từ<input className="o nho" value={tu} placeholder="2025-01-01"
               onChange={e => setTu(e.target.value)} /></label>
        <label>Đến<input className="o nho" value={den} placeholder="2026-01-01"
               onChange={e => setDen(e.target.value)} /></label>
        {/* Nút này trả lời câu "sao máy mới không tự tải được?" NGAY TẠI ĐÂY, chứ không
            để người dùng bấm ▶ rồi gặp một lỗi nói về khoảng thời gian. */}
        <button className="nut" onClick={kiemKetNoi} disabled={dangKiem}>
          {dangKiem ? 'đang nối…' : 'Kiểm tra kết nối MT5'}
        </button>
        <span className="cd-tu-tai">thiếu nến thì ▶ Chạy tự tải</span>
      </div>

      {ketNoi && (
        <div className={'cd-ket-noi' + (ketNoi.noi_duoc && ketNoi.co_symbol ? ' duoc' : ' hong')}>
          <div>{ketNoi.noi_duoc && ketNoi.co_symbol ? '✓' : '⚠'} {ketNoi.chu}</div>
          {ketNoi.terminal && (
            <div className="phu">{ketNoi.terminal}
              {ketNoi.tai_khoan && <> · tài khoản {ketNoi.tai_khoan}</>}
            </div>
          )}
          {/* Nhiều sàn thêm hậu tố (XAUUSDm, XAUUSD.r…). Liệt kê mã CÓ THẬT trên sàn
              đang nối, bấm một cái là điền — hơn hẳn để người dùng đoán. */}
          {ketNoi.goi_y.length > 0 && (
            <div className="phu">
              sàn này có:{' '}
              {ketNoi.goi_y.map(s => (
                <button key={s} className="cd-goi-y" onClick={() => setTSymbol(s)}>{s}</button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="hang cd-hang">
        <label title="Nến là giá Bid; Ask = Bid + spread">
          Spread<input className="o nho" type="number" value={spread}
                 onChange={e => setSpread(+e.target.value)} />points
        </label>
        <label>Vốn<input className="o nho" type="number" value={deposit}
               onChange={e => setDeposit(+e.target.value)} />USD</label>
        <label title="Tính round-turn — trừ một lần khi lệnh đóng">
          Phí<input className="o nho" type="number" value={phi}
              onChange={e => setPhi(+e.target.value)} />USD/lot
        </label>
        <label>Đòn bẩy 1:<input className="o nho" type="number" value={donBay}
               onChange={e => setDonBay(+e.target.value)} /></label>
        <label title="Nhịp PHÁT LẠI — không phải tốc độ mô phỏng">
          Delay<input className="o nho" type="number" value={delay}
                onChange={e => setDelay(+e.target.value)} />ms
        </label>
      </div>

      {/* Spread tính bằng POINT chỉ có nghĩa khi biết point size của symbol: XAUUSD 3
          chữ số thì 20 points = 0,02 USD — quá nhỏ. Hiện quy đổi ngay cạnh ô, kèm trung
          vị đo được trên chính dữ liệu đã tải, để không phải đoán. */}
      {bo?.point != null && (
        <div className="chu-dan">
          {tSymbol}: 1 point = {bo.point} · spread {spread} points ={' '}
          <b>{(spread * bo.point).toFixed(3)} USD</b>
          {bo.spread_tb != null && (
            <> · trung vị đo được trên dữ liệu đã tải: <b>{bo.spread_tb} points</b></>
          )}
        </div>
      )}

      <div className="chu-dan">
        Cài đặt lưu vào <code>du_lieu/cai_dat.json</code> cạnh app, không nằm trong repo.
        Phiên bản {boot.phien_ban} · {boot.app_dir}
      </div>
    </Modal>
  )
}
