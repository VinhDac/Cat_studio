import { useEffect, useRef, useState } from 'react'
import {
  CandlestickSeries, LineSeries, LineStyle, LineType, createChart, createSeriesMarkers,
  type IChartApi, type ISeriesApi, type SeriesMarker, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import type { LenhVe } from '../types'

/** CHART — ba tầng, ba họ màu, mỗi họ MỘT nghĩa.
 *
 *   nến        xám     — bối cảnh. Giá là thứ XẢY RA.
 *   mức lệnh   cam     — "chỗ ta đặt". Không gì khác trên chart màu cam.
 *   kết quả    xanh/đỏ — và CHỈ có nghĩa này.
 *
 * ⚠ Vì sao nến phải xám: bản trước nến xanh/đỏ, mũi tên hướng xanh/đỏ, lãi lỗ cũng
 * xanh/đỏ — một cặp màu mang ba nghĩa thì chẳng còn nghĩa nào. Làm nến im đi không phải
 * để đẹp: để lúc không có lệnh thì chart lặng như tờ, lúc có lệnh thì mắt bị kéo tới ngay.
 *
 * HƯỚNG mua/bán KHÔNG dùng màu nữa — dùng HÌNH: ▲ mua, ▼ bán.
 *
 * ⚠ Và mọi đường CHỈ CHẠY TRONG QUÃNG LỆNH SỐNG. Bản trước dùng `createPriceLine`, mà nó
 * luôn kéo suốt bề ngang chart — ba đường của một lệnh đặt lúc 09:00 cũng chạy ngược về
 * 06:00, quãng nó chưa tồn tại. Nhiễu, và nói dối. `LineSeries` hai điểm là hết.
 */

export interface NenM1 { t: number; o: number; h: number; l: number; c: number }

/* Trần số nến giữ trong chart. 60.000 nến M5 ≈ một năm — tức thực tế là KHÔNG có trần.
   Chart phải hành xử như một cuốn VIDEO: kéo đi đâu cũng còn quá khứ ở đó. */
const TRAN = 60000

export type Bar = { time: UTCTimestamp; open: number; high: number; low: number; close: number }
type Diem = { time: UTCTimestamp; value: number }

export default function Chart({ tfPhut, digits, lenh, tBayGio, batDau, them, dat }: {
  tfPhut: number
  digits: number
  lenh: LenhVe[]
  /** Thời điểm CON TRỎ. Lệnh vẽ theo trạng thái TẠI ĐÂY — lô mang cả sự kiện tương lai
   *  (tới 300 nhịp = 5 giờ), vẽ thẳng trạng thái cuối là lộ tương lai. */
  tBayGio: number
  batDau: number
  /** Nến M1 mới nhất — mỗi nhịp phát một cây, gộp vào cây đang hình thành. */
  them: NenM1 | null
  /** TOÀN BỘ nến khung hiển thị từ đầu dữ liệu tới con trỏ, Python đã gộp sẵn.
   *  Nạp lại mỗi lần NHẢY hoặc đổi khung — 60.000 nến mất 15 ms, 3 MB. */
  dat: Bar[] | null
}) {
  const boc = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  const nen = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const bars = useRef<Bar[]>([])
  const lop = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const mark = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)
  const daKeo = useRef(false)
  const [hien, setHien] = useState<{ l: LenhVe; x: number; y: number } | null>(null)

  const mau = (t: string, dp = '#888') =>
    getComputedStyle(document.documentElement).getPropertyValue(t).trim() || dp

  // ---------------- dựng chart ----------------
  useEffect(() => {
    const el = boc.current
    if (!el) return
    const c = createChart(el, {
      layout: { background: { color: mau('--canvas-bg', '#181818') }, textColor: mau('--muted') },
      grid: { vertLines: { color: mau('--border-soft') }, horzLines: { color: mau('--border-soft') } },
      rightPriceScale: { borderColor: mau('--border') },
      timeScale: { borderColor: mau('--border'), timeVisible: true, secondsVisible: false,
                   rightOffset: 8 },
      crosshair: { mode: 0 },
      autoSize: true,
    })
    // NẾN XÁM: tăng thì RỖNG (chỉ viền), giảm thì ĐẶC tối. Vẫn phân biệt được chiều mà
    // không tranh màu với lệnh.
    const s = c.addSeries(CandlestickSeries, {
      upColor: 'rgba(0,0,0,0)', borderUpColor: mau('--nen-len', '#9aa0a6'),
      wickUpColor: mau('--nen-len', '#9aa0a6'),
      downColor: mau('--nen-xuong', '#5c6166'), borderDownColor: mau('--nen-xuong', '#5c6166'),
      wickDownColor: mau('--nen-xuong', '#5c6166'),
      priceFormat: { type: 'price', precision: digits, minMove: Math.pow(10, -digits) },
    })
    chart.current = c
    nen.current = s
    mark.current = createSeriesMarkers<Time>(s, [])
    c.timeScale().subscribeVisibleLogicalRangeChange(() => { daKeo.current = true })
    return () => { c.remove(); chart.current = null; nen.current = null; lop.current.clear() }
  }, [digits])

  // ---------------- dựng lại ----------------
  useEffect(() => {
    const s = nen.current
    if (!s) return
    bars.current = dat ? dat.slice() : []
    s.setData(bars.current)
    daKeo.current = false
    chart.current?.timeScale().scrollToRealTime()
  }, [batDau, dat])

  // ---------------- một nhịp phát: nến lớn dần ----------------
  useEffect(() => {
    const s = nen.current
    if (!s || !them) return
    const truoc = bars.current.length
    gop(bars.current, them, tfPhut)
    if (bars.current.length > TRAN) bars.current.splice(0, bars.current.length - TRAN)
    s.update(bars.current[bars.current.length - 1])
    if (!daKeo.current && bars.current.length !== truoc) {
      chart.current?.timeScale().scrollToRealTime()
    }
  }, [them, tfPhut])

  // ---------------- LỆNH ----------------
  useEffect(() => {
    const c = chart.current
    if (!c) return
    const CAM = mau('--accent', '#ffa657')
    const LAI = mau('--ok', '#4ec96a')
    const LO = mau('--err', '#e5534b')
    const XAM = mau('--dim', '#7a7a7a')
    const con = new Set<string>()

    /** Một đoạn đường, giữ theo KHOÁ. Nhịp sau chỉ `setData` chứ không dựng lại series —
     *  dựng/xoá series mỗi nhịp là chart nháy và tụt nhịp phát. */
    const doan = (khoa: string, diem: Diem[],
                  o: { color: string; style?: LineStyle; width?: 1 | 2 | 3; bac?: boolean }) => {
      if (diem.length < 2) return
      con.add(khoa)
      let s = lop.current.get(khoa)
      if (!s) {
        s = c.addSeries(LineSeries, {
          color: o.color, lineWidth: o.width ?? 1,
          lineStyle: o.style ?? LineStyle.Solid,
          lineType: o.bac ? LineType.WithSteps : LineType.Simple,
          priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
        })
        lop.current.set(khoa, s)
      }
      s.setData(diem)
    }

    const mk: SeriesMarker<Time>[] = []
    for (const l of lenh) {
      if (l.t_dat > tBayGio) continue
      const daKhop = l.t_khop != null && l.t_khop <= tBayGio
      const daDong = l.t_dong != null && l.t_dong <= tBayGio
      const daHuy = daDong && l.ly_do_dong === 'huy'
      const het = daDong ? l.t_dong! : tBayGio

      // --- mức VÀO: từ lúc đặt tới lúc khớp (hoặc tới bây giờ nếu còn chờ) ---
      if (l.gia_dat != null) {
        doan(`${l.id}:vao`, hai(l.t_dat, daKhop ? l.t_khop! : het, l.gia_dat),
             { color: CAM, style: LineStyle.Dashed })
      }
      // --- TP: sống suốt đời lệnh ---
      if (l.tp != null && !daHuy) {
        doan(`${l.id}:tp`, hai(l.t_dat, het, l.tp), { color: CAM, style: LineStyle.Dotted })
      }
      // --- SL: vẽ theo LỊCH SỬ, nên lúc dời về hoà vốn nó nhảy BẬC ngay trên chart.
      //     Đây là khoảnh khắc đáng kiểm chứng nhất, mà bản trước chỉ vẽ SL cuối cùng
      //     nên nó tàng hình. ---
      if (!daHuy) {
        const ds: Diem[] = (l.sl_lich_su ?? [])
          .filter(([t]) => t <= het)
          .map(([t, v]) => ({ time: t as UTCTimestamp, value: v }))
        if (ds.length) {
          ds.push({ time: Math.max(het, ds[ds.length - 1].time as number + 1) as UTCTimestamp,
                    value: ds[ds.length - 1].value })
          doan(`${l.id}:sl`, ds, { color: CAM, style: LineStyle.Dotted, bac: true })
        }
      }

      if (!daKhop) {
        if (daHuy) {
          // Lệnh chờ bị huỷ: KHÔNG thắng không thua, nên không đụng tới màu kết quả.
          mk.push({ time: l.t_dong as UTCTimestamp, position: 'aboveBar',
                    color: XAM, shape: 'square', text: `✕ ${l.id} huỷ` })
        }
        continue
      }

      // --- mũi tên VÀO: HÌNH cho hướng, màu CAM cho "đây là lệnh" ---
      mk.push({
        time: l.t_khop as UTCTimestamp,
        position: l.huong === 'mua' ? 'belowBar' : 'aboveBar',
        color: CAM, shape: l.huong === 'mua' ? 'arrowUp' : 'arrowDown',
        text: l.id,
      })

      // --- VẠCH NỐI vào→ra: chỗ DUY NHẤT mang màu kết quả. Dốc lên xanh, dốc xuống đỏ,
      //     nên nhìn ĐỘ DỐC là biết lãi lỗ mà không cần đọc số. ---
      if (daDong && l.gia_dong != null && l.gia_khop != null) {
        const lai = (l.lai_R ?? 0) >= 0
        doan(`${l.id}:kq`, [
          { time: l.t_khop as UTCTimestamp, value: l.gia_khop },
          { time: Math.max(l.t_dong!, l.t_khop! + 1) as UTCTimestamp, value: l.gia_dong },
        ], { color: lai ? LAI : LO, width: 2 })
        mk.push({
          time: l.t_dong as UTCTimestamp,
          position: l.huong === 'mua' ? 'aboveBar' : 'belowBar',
          color: lai ? LAI : LO, shape: 'square',
          text: `${l.id} ${l.lai_R?.toFixed(2)}R`,
        })
      }
    }

    for (const [k, s] of [...lop.current]) {
      if (!con.has(k)) { c.removeSeries(s); lop.current.delete(k) }
    }
    mk.sort((a, b) => (a.time as number) - (b.time as number))
    mark.current?.setMarkers(mk)
  }, [lenh, tBayGio])

  // ---------------- bảng nhỏ khi rê chuột ----------------
  useEffect(() => {
    const c = chart.current
    if (!c) return
    const f = (p: { time?: Time; point?: { x: number; y: number } }) => {
      if (p.time == null || !p.point) return setHien(null)
      const t = p.time as number
      const g = lenh.find(l => l.t_dat <= t && l.t_dat <= tBayGio
                               && (l.t_dong ?? tBayGio) >= t)
      setHien(g ? { l: g, x: p.point.x, y: p.point.y } : null)
    }
    c.subscribeCrosshairMove(f)
    return () => c.unsubscribeCrosshairMove(f)
  }, [lenh, tBayGio])

  return (
    <div className="chart-boc" ref={boc}>
      {hien && (
        <div className="chart-goi-y" style={{ left: hien.x + 14, top: hien.y + 14 }}>
          <b>{hien.l.id}</b> {hien.l.huong === 'mua' ? '▲ Mua' : '▼ Bán'} {hien.l.lot}
          <div>đặt {hien.l.gia_dat?.toFixed(digits)} · {gio(hien.l.t_dat)}</div>
          {hien.l.t_khop != null && hien.l.t_khop <= tBayGio && (
            <div>vào {hien.l.gia_khop?.toFixed(digits)} · {gio(hien.l.t_khop)}</div>
          )}
          {hien.l.t_dong != null && hien.l.t_dong <= tBayGio && (
            <>
              <div>ra {hien.l.gia_dong?.toFixed(digits) ?? '—'} · {gio(hien.l.t_dong)}</div>
              <div className={(hien.l.lai_R ?? 0) >= 0 ? 'lai' : 'lo'}>
                {hien.l.lai_R != null ? `${hien.l.lai_R.toFixed(2)} R · ` : ''}
                {hien.l.ly_do_dong}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function hai(t1: number, t2: number, v: number): Diem[] {
  return [{ time: t1 as UTCTimestamp, value: v },
          { time: Math.max(t2, t1 + 1) as UTCTimestamp, value: v }]
}

/** Gộp một nến M1 vào mảng nến khung hiển thị — chỉ để VẼ.
 *  Python vẫn là nguồn sự thật cho mọi con số đi vào QUYẾT ĐỊNH (`tinh_toan.gop`). */
function gop(bars: Bar[], x: NenM1, tfPhut: number) {
  const b = tfPhut * 60
  const moc = Math.floor(x.t / b) * b as UTCTimestamp
  const cuoi = bars[bars.length - 1]
  if (!cuoi || cuoi.time !== moc) {
    bars.push({ time: moc, open: x.o, high: x.h, low: x.l, close: x.c })
  } else {
    cuoi.high = Math.max(cuoi.high, x.h)
    cuoi.low = Math.min(cuoi.low, x.l)
    cuoi.close = x.c
  }
}

function gio(t: number | null) {
  if (t == null) return '—'
  const d = new Date(t * 1000)
  const s = (n: number) => String(n).padStart(2, '0')
  return `${s(d.getUTCMonth() + 1)}-${s(d.getUTCDate())} ${s(d.getUTCHours())}:${s(d.getUTCMinutes())}`
}
