import { useState } from 'react'
import { py } from '../api'
import type { Bootstrap } from '../types'
import Modal from './Modal'

export default function SettingsDialog({ boot, doiMauNgay, onDong }: {
  boot: Bootstrap
  doiMauNgay: (mau: string) => void
  onDong: () => void
}) {
  const s = boot.settings as Record<string, any>
  const [symbol, setSymbol] = useState(String(s.symbol ?? 'XAUUSD'))
  const [tf, setTf] = useState(String(s.timeframe ?? 'M5'))
  const [accent, setAccent] = useState(String(s.accent ?? '#ffa657'))

  async function luu() {
    await py.save_settings({ symbol, timeframe: tf, accent })
    onDong()
  }

  return (
    <Modal title="Cài đặt" width={520} onClose={onDong}
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
        <span className="nhan-o phu">Khung TG</span>
        <select className="o nho" value={tf} onChange={e => setTf(e.target.value)}>
          {boot.timeframes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
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

      <div className="chu-dan">
        Cài đặt lưu vào <code>settings.json</code> cạnh app, không nằm trong repo.
        Phiên bản {boot.phien_ban} · {boot.app_dir}
      </div>
    </Modal>
  )
}
