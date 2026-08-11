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
export default function SettingsDialog({ boot, doiMauNgay, onDong }: {
  boot: Bootstrap
  doiMauNgay: (mau: string) => void
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

  const bo = nguon.find(n => n.symbol === tSymbol)

  async function luu() {
    await py.save_settings({ symbol, accent })
    await py.save_test_settings({
      symbol: tSymbol, tu, den, spread_diem: spread,
      deposit, commission: phi, don_bay: donBay, delay_ms: delay,
    })
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
        <span className="cd-tu-tai">thiếu nến thì ▶ Chạy tự tải</span>
      </div>

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
