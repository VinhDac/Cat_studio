import { useCallback, useEffect, useRef, useState } from 'react'
import { pyTester } from '../api'
import type { MucLichSu } from '../types'

/** LỊCH SỬ CÁC LẦN CHẠY — nút cạnh logo trên thanh tiêu đề.
 *
 * Hai danh sách, khác nhau ở ĐÚNG MỘT chỗ: có tên hay không.
 *
 *   · ĐÃ LƯU  — có tên, KHÔNG BAO GIỜ bị cuốn chiếu. Cái tên mới là thứ làm nó tìm lại
 *               được sau ba tháng; `hôm qua 22:41` thì tháng sau chẳng nói lên gì.
 *   · GẦN ĐÂY — tự ghi mỗi lần bấm ▶, không tên, 20 chỗ cuốn chiếu. Lưới an toàn cho
 *               lúc chạy xong mới nhớ ra "ơ lần trước bao nhiêu nhỉ".
 *
 * Bấm vào một dòng = XEM tóm tắt, hiện ngay, không chạy lại gì (Python cất sẵn bảng số
 * và đường vốn). Bấm ▶ = MỞ LẠI: chạy lại đúng sơ đồ và cài đặt đã cất, ~3 giây, ra
 * nguyên bộ phát lại chứ không phải một tấm ảnh chụp chết.
 */
export default function LichSu({ dangXem, onXem, onMoLai }: {
  /** Mã mục đang xem, `null` = đang xem lần chạy hiện tại. */
  dangXem: string | null
  onXem: (ma: string) => void
  onMoLai: (ma: string) => void
}) {
  const [mo, setMo] = useState(false)
  const [ds, setDs] = useState<MucLichSu[]>([])
  const [dangSua, setDangSua] = useState<string | null>(null)
  const [ten, setTen] = useState('')
  const boc = useRef<HTMLDivElement>(null)

  const nap = useCallback(async () => {
    const r = await pyTester.test_lich_su()
    if (r.ok && r.value) setDs(r.value.ds)
  }, [])

  useEffect(() => { if (mo) void nap() }, [mo, nap])

  /* Đóng khi bấm ra ngoài. `mousedown` chứ không phải `click`: đóng ngay lúc nhấn thì cú
     nhấn đó không lọt xuống thứ nằm dưới bảng. */
  useEffect(() => {
    if (!mo) return
    const f = (e: MouseEvent) => {
      if (!boc.current?.contains(e.target as Node)) setMo(false)
    }
    window.addEventListener('mousedown', f, true)
    return () => window.removeEventListener('mousedown', f, true)
  }, [mo])

  const luu = async (ma: string) => {
    await pyTester.test_lich_su_ten(ma, ten)
    setDangSua(null); setTen('')
    void nap()
  }
  const xoa = async (ma: string) => {
    await pyTester.test_lich_su_xoa(ma)
    void nap()
  }

  const daLuu = ds.filter(x => x.ten)
  const mem = ds.filter(x => !x.ten)

  const hang = (m: MucLichSu) => {
    const t = m.thong_ke
    return (
      <div key={m.ma} className={'ls-hang' + (m.ma === dangXem ? ' dang' : '')}
           onClick={() => { onXem(m.ma); setMo(false) }}>
        <div className="ls-dau">
          <span className="ls-ten">{m.ten || khiNao(m.t)}</span>
          {m.ten && <span className="ls-gio">{khiNao(m.t)}</span>}
        </div>
        {/* Ba dòng chứ không nhồi một dòng: gộp lại thì nó tự xuống hàng giữa chừng và
            mỗi mục cao thấp khác nhau, danh sách hết quét dọc được. */}
        <div className="ls-so">
          {t.so_lenh} lệnh · {t.ty_le_thang.toFixed(1)}% ·{' '}
          <b className={t.tong_R >= 0 ? 'lai' : 'lo'}>
            {t.tong_R > 0 ? '+' : ''}{t.tong_R.toFixed(2)}R
          </b>{' '}· DD {t.drawdown_pt.toFixed(2)}%
        </div>
        <div className="ls-phu">
          {m.nguon.symbol} · {m.cai_dat.tu} → {m.cai_dat.den}
        </div>
        <div className="ls-nut" onClick={e => e.stopPropagation()}>
          <button title="Mở lại — chạy lại sơ đồ và cài đặt đã cất"
                  onClick={() => { onMoLai(m.ma); setMo(false) }}>▶</button>
          <button title={m.ten ? 'Đổi tên' : 'Lưu lại — đặt tên thì không bị cuốn chiếu'}
                  onClick={() => { setDangSua(m.ma); setTen(m.ten || tenGoiY(m)) }}>
            {m.ten ? '✎' : '⭳'}
          </button>
          <button title="Xoá khỏi lịch sử" onClick={() => void xoa(m.ma)}>✕</button>
        </div>
        {dangSua === m.ma && (
          <div className="ls-sua" onClick={e => e.stopPropagation()}>
            <input className="o" autoFocus value={ten} placeholder="đặt tên cho lần chạy này"
                   onChange={e => setTen(e.target.value)}
                   onKeyDown={e => {
                     if (e.key === 'Enter') void luu(m.ma)
                     if (e.key === 'Escape') { setDangSua(null); setTen('') }
                   }} />
            <button className="nut chinh" onClick={() => void luu(m.ma)}>Lưu</button>
            {/* Xoá trắng tên = trả mục về dạng mềm, tức cho phép nó bị cuốn chiếu lại. */}
            <button className="nut-nho" onClick={() => { setDangSua(null); setTen('') }}>
              Thôi
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="ls" ref={boc} data-khong-keo>
      <button className={'ls-nut-mo' + (mo ? ' dang' : '') + (dangXem ? ' khac' : '')}
              onClick={() => setMo(v => !v)}
              title="Lịch sử các lần chạy">
        ⏱ Lịch sử
      </button>
      {mo && (
        <div className="ls-bang">
          {ds.length === 0 && <div className="ls-rong">chưa có lần chạy nào được ghi</div>}
          {daLuu.length > 0 && <>
            <div className="ls-muc">Đã lưu</div>
            {daLuu.map(hang)}
          </>}
          {mem.length > 0 && <>
            <div className="ls-muc">Gần đây <span>tự lưu · cuốn chiếu 20 mục</span></div>
            {mem.map(hang)}
          </>}
        </div>
      )}
    </div>
  )
}

function tenGoiY(m: MucLichSu) {
  return `${m.ten_chien_luoc} · ${khiNao(m.t)}`
}

/** "hôm nay 14:32" đọc nhanh hơn "2026-08-11 14:32" cho thứ vừa mới chạy; xa hơn hai
 *  ngày thì ngày tháng mới là thứ định vị được. */
function khiNao(t: number) {
  const d = new Date(t * 1000)
  const s = (n: number) => String(n).padStart(2, '0')
  const gio = `${s(d.getHours())}:${s(d.getMinutes())}`
  const ngay = new Date(); ngay.setHours(0, 0, 0, 0)
  const cach = Math.floor((ngay.getTime() - new Date(d).setHours(0, 0, 0, 0)) / 86400000)
  if (cach === 0) return `hôm nay ${gio}`
  if (cach === 1) return `hôm qua ${gio}`
  return `${s(d.getMonth() + 1)}-${s(d.getDate())} ${gio}`
}
