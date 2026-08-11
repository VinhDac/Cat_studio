import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { pyTester } from '../api'
import type { ThongKeChay, XemLichSu } from '../types'

/** TAB THỐNG KÊ — tổng kết cả lượt chạy. CỐ ĐỊNH, không tua theo con trỏ.
 *
 * Mọi con số và cả hai đường cong ra từ MỘT vòng lặp trong `bo_chay._thong_ke`, nên điểm
 * cuối đường vốn bằng đúng `von_cuoi` và đáy đường sụt giảm bằng đúng `drawdown_pt` —
 * không có hai nguồn để lệch nhau.
 *
 * Đường vốn là VỐN ĐÃ CHỐT, mỗi nến trục có lệnh đóng một điểm (386 lệnh → 384 điểm cho
 * một năm). Cố ý KHÔNG vẽ lãi nổi: lãi nổi đổi theo từng nến M1 → 353.000 điểm, giật
 * liên tục, và `drawdown_pt` vốn đã cố tình loại nó ra vì đúng lý do đó (core.md §12.13e).
 *
 * KHÔNG có `số vùng nén` dù `thong_ke` đang mang sẵn: đó là khái niệm riêng của một
 * chiến lược, đúng cái bẫy đã gỡ ở bảng số liệu bên phải (core.md §12.9c).
 */
export default function ThongKe({ nguon, thoiXem }: {
  /** Có thì vẽ mục LỊCH SỬ này; `null` thì hỏi lần chạy hiện tại. Cùng một hình dạng dữ
   *  liệu (`_tom_tat_chay` bên Python dựng cả hai), nên không có nhánh vẽ thứ hai. */
  nguon: XemLichSu | null
  thoiXem: () => void
}) {
  const [hienTai, setHienTai] = useState<ThongKeChay | null>(null)
  const [loi, setLoi] = useState('')

  useEffect(() => {
    if (nguon) return                 // đang xem lịch sử, không cần hỏi lần chạy hiện tại
    let song = true
    void pyTester.test_thong_ke().then(r => {
      if (!song) return
      if (r.ok && r.value) setHienTai(r.value)
      else setLoi(r.error || 'không đọc được thống kê')
    })
    return () => { song = false }
  }, [nguon])

  const d = nguon ? nguon.tom_tat : hienTai
  if (loi) return <div className="tk-trong">{loi}</div>
  if (!d) return <div className="tk-trong">đang tính…</div>

  const t = d.tk
  const tien = (v: number) => v.toLocaleString('en-US', { minimumFractionDigits: 2,
                                                         maximumFractionDigits: 2 })
  const dau = (v: number) => (v > 0 ? '+' : '')
  const lop = (v: number) => (v > 0 ? 'lai' : v < 0 ? 'lo' : '')

  return (
    <div className="tk">
      {/* Dải này bắt buộc: không có nó thì người dùng đang nhìn số của một lần chạy CŨ mà
          tưởng là lần đang mở — kiểu nhầm tốn cả buổi. */}
      {nguon && (
        <div className="tk-bao-cu">
          Đang xem lần chạy cũ
          <b>{nguon.ten || gio(nguon.t)}</b>
          {nguon.chay_lai_duoc
            ? <span className="tk-phu">bấm ▶ trong Lịch sử để mở lại xem phát lại</span>
            : <span className="tk-canh">⚠ {nguon.vi_sao} — không mở lại phát lại được</span>}
          <button className="nut-nho" onClick={thoiXem}>Về lần chạy hiện tại</button>
        </div>
      )}
      <div className="tk-khoang">
        <b>{gio(d.t_dau)}</b> → <b>{gio(d.t_cuoi)}</b>
        <span className="tk-phu">
          {d.symbol} · Entry {d.nhip.entry} · Manage {d.nhip.manage}
          {/* Khoảng ĐÃ YÊU CẦU vs khoảng THẬT SỰ có nến. Lệch nhau là chuyện thường
              (thiếu dữ liệu đầu/cuối) — mà đọc số không biết nó tính trên quãng nào thì
              con số vô nghĩa. */}
          {(d.yc_tu || d.yc_den) && ` · đã yêu cầu ${d.yc_tu || '…'} → ${d.yc_den || '…'}`}
        </span>
      </div>

      <div className="tk-so">
        <Nhom ten="Vốn" hang={[
          ['vốn đầu', tien(t.von_dau)],
          ['vốn cuối', tien(t.von_cuoi)],
          ['lãi ròng', `${dau(t.lai_tien)}${tien(t.lai_tien)}`, lop(t.lai_tien)],
          ['', `${dau(t.lai_pt)}${t.lai_pt.toFixed(2)} %`, lop(t.lai_pt)],
          ['tổng R', `${dau(t.tong_R)}${t.tong_R.toFixed(2)}`, lop(t.tong_R)],
        ]} />
        <Nhom ten="Lệnh" hang={[
          ['đã đặt', String(t.so_lenh)],
          ['đã khớp', String(t.so_dong)],
          ['đã huỷ', String(t.so_huy)],
          ['lượt chạy', t.so_luot.toLocaleString('en-US')],
        ]} />
        <Nhom ten="Thắng / thua" hang={[
          ['thắng', String(t.thang)],
          ['thua', String(t.thua)],
          ['tỷ lệ thắng', `${t.ty_le_thang.toFixed(1)} %`],
          ['chuỗi thua dài nhất', String(t.chuoi_thua)],
        ]} />
        <Nhom ten="Chất lượng" hang={[
          ['R mỗi lệnh', `${dau(t.R_moi_lenh)}${t.R_moi_lenh.toFixed(3)}`, lop(t.R_moi_lenh)],
          ['R khi thắng', `+${t.R_khi_thang.toFixed(2)}`, 'lai'],
          ['R khi thua', t.R_khi_thua.toFixed(2), 'lo'],
          // `null` = chưa có lệnh lỗ nào, KHÔNG phải 0 — hai chuyện khác hẳn nhau.
          ['hệ số lãi', t.he_so_lai == null ? '—' : t.he_so_lai.toFixed(2),
           t.he_so_lai != null && t.he_so_lai >= 1 ? 'lai' : 'lo'],
        ]} />
        <Nhom ten="Rủi ro" hang={[
          ['sụt giảm lớn nhất', `${t.drawdown_pt.toFixed(2)} %`, 'lo'],
          ['', `${tien(t.drawdown_tien)} $`, 'lo'],
          ['chạm đáy lúc', t.drawdown_luc ? gio(t.drawdown_luc) : '—'],
          ['nến mơ hồ', String(t.nen_mo_ho)],
        ]} />
      </div>

      <Do ten="Đường vốn — chốt theo lệnh đã đóng" cao={190} kieu="von"
          ds={d.duong_von.map(x => ({ t: x[0], v: x[1] }))} moc={t.von_dau}
          nhanY={v => Math.round(v).toLocaleString('en-US')}
          nhanO={v => `${tien(v)} $`} />
      <Do ten="Sụt giảm từ đỉnh vốn" cao={120} kieu="sut"
          ds={d.duong_von.map(x => ({ t: x[0], v: x[2] }))} moc={0}
          nhanY={v => v.toFixed(2)}
          nhanO={v => `${v.toFixed(2)} %`} />
    </div>
  )
}

function Nhom({ ten, hang }: { ten: string; hang: (string | undefined)[][] }) {
  return (
    <div className="tk-nhom">
      <div className="tk-ten">{ten}</div>
      <table><tbody>
        {hang.map((h, i) => (
          <tr key={i}>
            <td>{h[0]}</td>
            <td className={'mono ' + (h[2] ?? '')}>{h[1]}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  )
}

type Diem = { t: number; v: number }

/** MỘT ĐỒ THỊ, VẼ TAY.
 *
 * ⚠ Bản trước dùng lightweight-charts cho hai đồ thị này. Bỏ, vì ba lý do và không lý do
 * nào là "cho vui": nó **đóng khung một mảng nền đen** riêng giữa bảng vốn màu xám, nó
 * **dán logo TradingView** vào góc, và nó kéo cả một bộ máy biểu đồ nến chỉ để vẽ một
 * đường gấp khúc 384 điểm. Chart PHÁT LẠI thì vẫn giữ nó — chỗ đó cần trục thời gian,
 * thu phóng, kéo ngang, marker; chỗ này thì không.
 *
 * Mẹo giữ cho không phải đo bề ngang bằng JS: SVG dùng `preserveAspectRatio="none"` với
 * hệ toạ độ cố định 1000×100, cho nó tự kéo giãn đầy khung. Nét không bị méo theo nhờ
 * `vector-effect="non-scaling-stroke"`. Còn CHỮ thì đứng ngoài SVG — nhãn là thẻ HTML đặt
 * theo phần trăm, nên không dính cái phép kéo giãn ấy.
 */
function Do({ ten, cao, ds, moc, kieu, nhanY, nhanO }: {
  ten: string
  cao: number
  ds: Diem[]
  /** Mức tham chiếu: vốn ban đầu, hoặc mốc 0 của sụt giảm. */
  moc: number
  kieu: 'von' | 'sut'
  nhanY: (v: number) => string
  nhanO: (v: number) => string
}) {
  const boc = useRef<HTMLDivElement>(null)
  const [tro, setTro] = useState<{ k: number; x: number } | null>(null)
  // Id riêng cho mỗi đồ thị: hai `clipPath` trùng id thì cái sau đè cái trước và một
  // trong hai đồ thị bị cắt theo mốc của đồ thị kia.
  const id = useId().replace(/:/g, '')

  const g = useMemo(() => {
    if (ds.length < 2) return null
    const t0 = ds[0].t, t1 = ds[ds.length - 1].t
    let lo = Math.min(moc, ...ds.map(p => p.v))
    let hi = Math.max(moc, ...ds.map(p => p.v))
    if (hi === lo) { hi += 1; lo -= 1 }
    const dem = (hi - lo) * 0.08
    lo -= dem; hi += dem
    const X = (t: number) => (t - t0) / (t1 - t0) * 1000
    const Y = (v: number) => (1 - (v - lo) / (hi - lo)) * 100
    const duong = ds.map((p, i) => `${i ? 'L' : 'M'}${X(p.t).toFixed(2)} ${Y(p.v).toFixed(3)}`).join('')
    // Vùng tô: đóng kín xuống ĐƯỜNG MỐC, không phải xuống đáy khung. Tô xuống đáy thì
    // mảng màu chỉ nói "có số", tô tới mốc thì nó nói "lãi hay lỗ" — mà đó mới là câu hỏi.
    const yMoc = Y(moc)
    const vung = `${duong}L${X(t1).toFixed(2)} ${yMoc.toFixed(3)}L${X(t0).toFixed(2)} ${yMoc.toFixed(3)}Z`
    return { t0, t1, lo, hi, X, Y, duong, vung, yMoc,
             vach: vachY(lo, hi), thang: vachThang(t0, t1) }
  }, [ds, moc])

  if (!g) return <div className="tk-do"><div className="tk-do-ten">{ten}</div>
    <div className="tk-rong" style={{ height: cao }}>chưa có lệnh nào đóng</div></div>

  const pt = (e: React.MouseEvent) => {
    const r = boc.current?.getBoundingClientRect()
    if (!r || r.width <= 0) return
    const f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width))
    const t = g.t0 + f * (g.t1 - g.t0)
    // Điểm GẦN NHẤT theo thời gian, không phải theo chỉ số: các điểm cách nhau không đều
    // (lệnh đóng dày thưa tuỳ đoạn), chia đều chỉ số là trỏ sai chỗ.
    let k = 0
    for (let i = 1; i < ds.length; i++) {
      if (Math.abs(ds[i].t - t) < Math.abs(ds[k].t - t)) k = i
    }
    setTro({ k, x: f * 100 })
  }

  const p = tro ? ds[tro.k] : null

  return (
    <div className="tk-do">
      <div className="tk-do-ten">{ten}</div>
      <div className="tk-do-hang">
        <div className="tk-ve" style={{ height: cao }} ref={boc}
             onMouseMove={pt} onMouseLeave={() => setTro(null)}>
          <svg viewBox="0 0 1000 100" preserveAspectRatio="none">
            {g.vach.map(v => (
              <line key={v} x1="0" x2="1000" y1={g.Y(v)} y2={g.Y(v)}
                    className="tk-luoi" vectorEffect="non-scaling-stroke" />
            ))}
            {/* Mảng tô CẮT ĐÔI ở đường mốc: trên mốc = đang lãi (xanh), dưới mốc = đang
                lỗ (đỏ). Đúng nghĩa xanh/đỏ mà bảng màu đã dành riêng cho lãi/lỗ, và nhẹ
                mắt hơn hẳn một khối cam duy nhất phủ nửa khung. */}
            <defs>
              <clipPath id={`${id}-tren`}>
                <rect x="0" y="-20" width="1000" height={g.yMoc + 20} />
              </clipPath>
              <clipPath id={`${id}-duoi`}>
                <rect x="0" y={g.yMoc} width="1000" height={120 - g.yMoc} />
              </clipPath>
            </defs>
            <path d={g.vung} className="tk-to lai" clipPath={`url(#${id}-tren)`} />
            <path d={g.vung} className="tk-to lo" clipPath={`url(#${id}-duoi)`} />
            <line x1="0" x2="1000" y1={g.yMoc} y2={g.yMoc}
                  className="tk-moc" vectorEffect="non-scaling-stroke" />
            <path d={g.duong} className={'tk-net ' + kieu}
                  vectorEffect="non-scaling-stroke" />
            {p && (
              <line x1={g.X(p.t)} x2={g.X(p.t)} y1="0" y2="100"
                    className="tk-doc" vectorEffect="non-scaling-stroke" />
            )}
          </svg>

          {/* Nhãn nằm NGOÀI svg: trong svg thì phép kéo giãn 1000×100 bóp méo hết chữ. */}
          {g.vach.map(v => (
            <span key={v} className="tk-nhan-y" style={{ top: `${g.Y(v)}%` }}>{nhanY(v)}</span>
          ))}
          {p && <>
            <i className="tk-cham" style={{ left: `${g.X(p.t) / 10}%`, top: `${g.Y(p.v)}%` }} />
            <div className={'tk-o-tro' + (g.X(p.t) > 600 ? ' trai' : '')}
                 style={{ left: `${g.X(p.t) / 10}%` }}>
              <b>{nhanO(p.v)}</b>{gio(p.t)}
            </div>
          </>}
        </div>
        <div className="tk-truc-x">
          {g.thang.map(m => (
            <span key={m.t} style={{ left: `${(m.t - g.t0) / (g.t1 - g.t0) * 100}%` }}>
              {m.ten}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

/** 4-5 mốc TRÒN cho trục giá: bước là 1 · 2 · 2.5 · 5 nhân luỹ thừa 10, nên nhãn ra số
 *  dễ đọc chứ không phải `9971.8333`.
 *
 *  Có 2.5 trong danh sách vì thiếu nó thì một biên độ 93$ nhảy thẳng từ bước 20 lên bước
 *  50 — tức cả đồ thị chỉ còn 2 vạch, gần như không có trục. Bước 25 cho đúng 4 vạch. */
function vachY(lo: number, hi: number) {
  const tho = (hi - lo) / 4
  const mu = Math.pow(10, Math.floor(Math.log10(tho)))
  const b = [1, 2, 2.5, 5, 10].map(x => x * mu).find(x => x >= tho) ?? 10 * mu
  const ra: number[] = []
  for (let v = Math.ceil(lo / b) * b; v <= hi; v += b) ra.push(Math.round(v * 1e6) / 1e6)
  return ra
}

/** Mốc trục ngang: mỗi đầu tháng một vạch, thưa dần nếu quãng chạy quá dài. */
function vachThang(t0: number, t1: number) {
  const ra: { t: number; ten: string }[] = []
  const d = new Date(t0 * 1000)
  d.setUTCDate(1); d.setUTCHours(0, 0, 0, 0)
  d.setUTCMonth(d.getUTCMonth() + 1)
  while (d.getTime() / 1000 < t1) {
    const m = d.getUTCMonth()
    ra.push({ t: d.getTime() / 1000,
              ten: m === 0 ? `T1/${String(d.getUTCFullYear()).slice(2)}` : `T${m + 1}` })
    d.setUTCMonth(m + 1)
  }
  const buoc = Math.ceil(ra.length / 14)      // quá 14 vạch thì chữ chồng lên nhau
  return buoc > 1 ? ra.filter((_, i) => i % buoc === 0) : ra
}

function gio(t: number) {
  const d = new Date(t * 1000)
  const s = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}-${s(d.getUTCMonth() + 1)}-${s(d.getUTCDate())} `
       + `${s(d.getUTCHours())}:${s(d.getUTCMinutes())}`
}
