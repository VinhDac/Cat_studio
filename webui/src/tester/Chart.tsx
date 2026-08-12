import { useEffect, useRef, useState } from 'react'
import {
  BarSeries, CandlestickSeries, LineSeries, LineStyle, LineType, createChart,
  createSeriesMarkers,
  type IChartApi, type ISeriesApi, type SeriesMarker, type Time, type UTCTimestamp,
} from 'lightweight-charts'
import { pyTester } from '../api'
import type { ChangRay, LenhVe } from '../types'

/** CHART — ba họ màu, mỗi họ MỘT nghĩa.
 *
 *   xám              — nến. Bối cảnh, không phải nhân vật.
 *   cam              — ĐÚNG MỘT thứ: giá lệnh chờ. Mức duy nhất chưa có tốt hay xấu.
 *   xanh · đỏ · trắng — tốt · xấu · không bên nào. Dùng cho CẢ mức lẫn kết quả.
 *
 * ⚠ Luật cũ là "cam = mọi mức lệnh, xanh/đỏ = CHỈ kết quả", và TP/SL đều cam. Nghe thì
 * chặt, nhưng bắt mắt phải đọc chữ mới biết đường nào là đích đường nào là tử huyệt.
 * Giờ TP xanh / SL đỏ: cùng một trục nghĩa với thắng/thua, vì TP đúng là chỗ cái tốt
 * nằm. Cam co lại còn một việc duy nhất nên nó lại càng rõ hơn trước.
 *
 * ⚠ HƯỚNG mua/bán không còn mũi tên. Nó không mất: **xanh nằm trên = Mua, xanh nằm
 * dưới = Bán** — đọc hướng từ phía mình đang nhắm tới, thẳng hơn một cái ▲.
 *
 * ⚠ Mọi CHẤM đặt ở ĐÚNG MỨC GIÁ (`atPriceMiddle`), không lơ lửng trên/dưới nến. Bản
 * trước mũi tên vào nằm dưới nến còn ô vuông ra nằm trên nến, nên hai đầu một lệnh
 * trông như hai vật thể rời — mà chúng là hai đầu của cùng một đoạn.
 *
 * ⚠ Và mọi đường CHỈ CHẠY TRONG QUÃNG LỆNH SỐNG. Bản trước dùng `createPriceLine`, mà nó
 * luôn kéo suốt bề ngang chart — ba đường của một lệnh đặt lúc 09:00 cũng chạy ngược về
 * 06:00, quãng nó chưa tồn tại. Nhiễu, và nói dối. `LineSeries` hai điểm là hết.
 */

/** Ngưỡng HOÀ. Nhãn in 2 chữ số, nên cái gì in ra `0.00R` thì không được xanh cũng
 *  không được đỏ — màu mà cãi nhau với con số ngay cạnh nó thì tin cái nào? */
const HOA = 0.005

const VIEC_CHU: Record<string, string> = {
  lenh_dat: 'đặt lệnh', lenh_sua: 'sửa', lenh_dong: 'đóng tay', lenh_huy: 'huỷ',
}
const MOC_CHU: Record<string, string> = {
  khop: 'khớp', sl: 'chạm SL', tp: 'chạm TP', het_du_lieu: 'hết dữ liệu',
  // Lệnh chờ còn treo lúc hết dữ liệu — khác hẳn "khối Huỷ chờ đã huỷ nó", mà bộ chạy
  // lại dùng chung một chuỗi `ly_do_dong` cho cả hai. Nói rõ ra để không lẫn.
  huy: 'còn treo lúc hết dữ liệu', dong: 'đóng',
}

export interface NenM1 { t: number; o: number; h: number; l: number; c: number }

/* Trần số nến giữ trong chart. 60.000 nến M5 ≈ một năm — tức thực tế là KHÔNG có trần.
   Chart phải hành xử như một cuốn VIDEO: kéo đi đâu cũng còn quá khứ ở đó. */
const TRAN = 60000

export type Bar = { time: UTCTimestamp; open: number; high: number; low: number; close: number }
type Diem = { time: UTCTimestamp; value: number }

export type KieuChart = 'nen' | 'bar' | 'line'

export default function Chart({ tfPhut, digits, lenh, tBayGio, batDau, them, dat,
                                duoi = null,
                                kieu = 'nen', mauThuong = false, hienLenh = true,
                                veHienTai = 0, tranNen = TRAN }: {
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
  /** ĐUÔI — vài cây cuối vừa chốt lại, áp bằng `update()` chứ không dựng lại series.
   *
   *  ⚠ Vì sao cần một cửa riêng thay vì cứ nạp lại `dat`: nạp lại chạy `setData` cả
   *  2.000 cây, `scrollToRealTime()` và xoá cờ `daKeo` — tức mỗi phút lại GIẬT người
   *  dùng về mép phải trong khi họ đang xem chỗ khác. Mà tốn nhất là 134 KB qua cầu
   *  nối chỉ để thêm một cây. Đuôi thì áp tại chỗ, không đụng vào tầm nhìn. */
  duoi?: Bar[] | null
  /** Vẽ giá bằng gì. Đổi kiểu phải DỰNG LẠI series — lightweight-charts không đổi tại
   *  chỗ được. Chớp một cái, chấp nhận được vì đây là thao tác cố ý. */
  kieu?: KieuChart
  /** `true` = nến xanh/đỏ như mọi nơi khác. Mặc định XÁM.
   *  ⚠ Bật lên là một cặp màu mang HAI nghĩa trên cùng màn hình (nến tăng/giảm và
   *  lệnh thắng/thua), nên lúc đó đường kết quả được vẽ DÀY hơn để còn tách được. */
  mauThuong?: boolean
  /** Ẩn toàn bộ visual vào lệnh / sửa lệnh — để nhìn giá trần. */
  hienLenh?: boolean
  /** Tăng số này = kéo chart về nến đang chạy. Dùng số chứ không dùng hàm: prop hàm
   *  đổi mỗi lần render cha, mà việc này chỉ được xảy ra khi người dùng BẤM. */
  veHienTai?: number
  /** Trần số nến giữ trong bộ nhớ chart.
   *
   *  ⚠ Hai cửa sổ dùng hai giá trị khác hẳn nhau, và đó là chủ ý:
   *    • **Test** = cuộn phim đã quay xong → phải giữ TOÀN BỘ, kéo về tháng trước vẫn có.
   *    • **Live** = chart quan sát như chart trading → chỉ cần cửa sổ gần đây.
   *  Live mà giữ 60.000 nến là tải cả lịch sử về chỉ để hiện một màn hình. */
  tranNen?: number
}) {
  const boc = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)
  // Kiểu series đổi theo , nên giữ ở dạng chung — mọi thứ ta gọi trên nó
  // (, ) đều có ở cả ba kiểu.
  const nen = useRef<ISeriesApi<'Candlestick' | 'Bar' | 'Line'> | null>(null)
  const bars = useRef<Bar[]>([])
  const lop = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  /** Vân tay dữ liệu ĐÃ VẼ của từng đường — xem chú thích trong `doan`. */
  const veRoi = useRef<Map<string, string>>(new Map())
  const mark = useRef<ReturnType<typeof createSeriesMarkers<Time>> | null>(null)
  const daKeo = useRef(false)
  /** `bars.current` đang là lưới của KHUNG NÀO. Xem chú thích ở nhịp phát. */
  const tfCuaBars = useRef(0)
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
    chart.current = c
    c.timeScale().subscribeVisibleLogicalRangeChange(() => { daKeo.current = true })
    return () => {
      c.remove(); chart.current = null; nen.current = null
      lop.current.clear(); veRoi.current.clear()
    }
  }, [digits])

  /* ---------------- SERIES GIÁ — dựng lại khi đổi KIỂU, không đổi màu ----------------
   *
   * ⚠ Bản trước gộp `kieu` và `mauThuong` vào effect dựng CHART, nên bấm một nút màu là
   * huỷ cả chart rồi dựng lại — mà effect nạp dữ liệu chỉ chạy theo `[batDau, dat]`, hai
   * cái đó không đổi, nên chart mới dựng xong KHÔNG AI ĐỔ NẾN VÀO: trắng bốc. Và kèm
   * theo là mất luôn vị trí đang xem, mất mức thu phóng.
   *
   * Giờ: đổi màu KHÔNG dựng lại gì (xem effect dưới). Đổi kiểu chỉ thay đúng series giá
   * — trục thời gian, zoom và mọi đường lệnh giữ nguyên — rồi đổ lại `bars.current`
   * NGAY TẠI ĐÂY chứ không chờ effect khác. */
  const [doiSeries, setDoiSeries] = useState(0)
  useEffect(() => {
    const c = chart.current
    if (!c) return
    if (nen.current) { try { c.removeSeries(nen.current) } catch { /* đã gỡ */ } }
    const gia = { type: 'price' as const, precision: digits,
                  minMove: Math.pow(10, -digits) }
    const s = kieu === 'line'
      ? c.addSeries(LineSeries, { color: mau('--nen-len', '#9aa0a6'), lineWidth: 2,
                                  priceLineVisible: false, priceFormat: gia })
      : kieu === 'bar' ? c.addSeries(BarSeries, { priceFormat: gia })
                       : c.addSeries(CandlestickSeries, { priceFormat: gia })
    nen.current = s
    mark.current = createSeriesMarkers<Time>(s, [])
    if (bars.current.length) {
      s.setData(kieu === 'line'
        ? bars.current.map(b => ({ time: b.time, value: b.close })) as never
        : bars.current)
    }
    setDoiSeries(x => x + 1)        // ép vẽ lại marker: chúng bám vào series vừa thay
  }, [kieu, digits])

  /* MÀU đổi TẠI CHỖ. Đây là một `applyOptions`, không phải một lần dựng lại — bấm là
     thấy ngay, không nháy, không mất chỗ đang xem. */
  useEffect(() => {
    const s = nen.current
    if (!s || kieu === 'line') return
    const len = mauThuong ? mau('--ok', '#4ec96a') : mau('--nen-len', '#9aa0a6')
    const xuong = mauThuong ? mau('--err', '#e5534b') : mau('--nen-xuong', '#5c6166')
    s.applyOptions(kieu === 'bar'
      ? { upColor: len, downColor: xuong }
      // Nến tăng RỖNG (chỉ viền) ở chế độ xám — vẫn phân biệt được chiều mà không
      // tranh màu với lệnh.
      : { upColor: mauThuong ? len : 'rgba(0,0,0,0)',
          borderUpColor: len, wickUpColor: len,
          downColor: xuong, borderDownColor: xuong, wickDownColor: xuong })
  }, [mauThuong, kieu, doiSeries])

  // ---------------- dựng lại ----------------
  useEffect(() => {
    const s = nen.current
    if (!s) return
    // Cắt theo trần NGAY khi nhận: Live chỉ cần cửa sổ gần đây, giữ cả lịch sử là
    // tải về rồi vứt đi.
    const nguon = dat ?? []
    bars.current = nguon.length > tranNen ? nguon.slice(nguon.length - tranNen) : nguon.slice()
    tfCuaBars.current = tfPhut
    // Line series ăn `{time, value}`, hai kiểu kia ăn OHLC — cùng một mảng nguồn.
    s.setData(kieu === 'line'
      ? bars.current.map(b => ({ time: b.time, value: b.close })) as never
      : bars.current)
    daKeo.current = false
    chart.current?.timeScale().scrollToRealTime()
    // ⚠ KHÔNG cho `tfPhut` vào deps. Đổi khung là `tfPhut` đổi TRƯỚC, `dat` về sau —
    // cho nó vào đây thì effect chạy ngay với `dat` CŨ và đóng dấu khung MỚI lên lưới
    // cũ, tức tự tay mở lại đúng cái cổng mà `tfCuaBars` sinh ra để chặn.
    // Không có nó, effect chỉ chạy khi `dat` thật sự về — lúc đó `tfPhut` đã đúng.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batDau, dat, tranNen])

  // ---------------- một nhịp phát: nến lớn dần ----------------
  useEffect(() => {
    const s = nen.current
    if (!s || !them) return
    /* ⚠ CHỐT SỐNG CÒN. `doiTf` đặt `tfVe` rồi mới `await veDau(...)`, nên có một khung
     * hình mà `tfPhut` ĐÃ là khung mới trong khi `bars.current` vẫn là lưới khung CŨ và
     * `them` vẫn là cây nến M1 cũ. Gộp chéo như thế sinh ra một mốc LÙI VỀ QUÁ KHỨ so
     * với cây cuối (M5 09:10 → H1 09:00), và `s.update()` của lightweight-charts ném
     * thẳng `Cannot update oldest data`. Lỗi ném trong useEffect mà app không có
     * ErrorBoundary → React gỡ cả cây → CỬA SỔ TESTER TRẮNG BỐC, phải mở lại.
     * Đã tái hiện: M5 → H1 sau khi phát một nhịp là dính.
     * Bỏ qua nhịp này thôi: `veDau` đang trên đường về và sẽ dựng lại toàn bộ lưới. */
    if (tfCuaBars.current !== tfPhut) return
    const truoc = bars.current.length
    const moc = bars.current[bars.current.length - 1]?.time as number | undefined
    gop(bars.current, them, tfPhut)
    if (bars.current.length > tranNen)
      bars.current.splice(0, bars.current.length - tranNen)
    const cuoi = bars.current[bars.current.length - 1]
    // Chốt THỨ HAI, canh thẳng điều kiện bất hợp lệ thay vì canh cách nó xảy ra: mốc
    // mới mà LÙI so với cây cuối thì `s.update` ném `Cannot update oldest data`, và lỗi
    // ném trong effect làm React gỡ cả cây → cửa sổ trắng. Thà bỏ một nhịp vẽ.
    if (moc !== undefined && (cuoi.time as number) < moc) return
    s.update(kieu === 'line'
      ? { time: cuoi.time, value: cuoi.close } as never : cuoi)
    if (!daKeo.current && bars.current.length !== truoc) {
      chart.current?.timeScale().scrollToRealTime()
    }
  }, [them, tfPhut])

  /* ---------------- ĐUÔI: vài cây vừa chốt ----------------
     Cùng hai chốt an toàn với nhịp phát ở trên: sai lưới khung thì bỏ qua (đang đổi
     khung, `dat` mới đang trên đường về), và mốc LÙI thì bỏ qua (`s.update` ném
     `Cannot update oldest data`, mà lỗi ném trong effect làm React gỡ cả cây → cửa
     sổ trắng bốc). */
  useEffect(() => {
    const s = nen.current
    if (!s || !duoi || !duoi.length) return
    if (tfCuaBars.current !== tfPhut) return
    for (const b of duoi) {
      const cuoi = bars.current[bars.current.length - 1]
      const t = b.time as number
      if (cuoi && t < (cuoi.time as number)) continue
      if (cuoi && t === (cuoi.time as number)) bars.current[bars.current.length - 1] = b
      else bars.current.push(b)
      s.update(kieu === 'line' ? { time: b.time, value: b.close } as never : b)
    }
    if (bars.current.length > tranNen)
      bars.current.splice(0, bars.current.length - tranNen)
    // KHÔNG `scrollToRealTime()` ở đây: người dùng có thể đang kéo xem chỗ khác, và
    // giật họ về mép phải mỗi phút là đúng thứ làm chart trading khó dùng.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duoi])

  // Kéo chart về nến đang chạy. Bỏ qua lần đầu (`veHienTai = 0`).
  useEffect(() => {
    if (!veHienTai) return
    daKeo.current = false
    chart.current?.timeScale().scrollToRealTime()
  }, [veHienTai])

  // ---------------- LỆNH ----------------
  useEffect(() => {
    const c = chart.current
    if (!c) return
    const CAM = mau('--accent', '#ffa657')
    const LAI = mau('--ok', '#4ec96a')
    const LO = mau('--err', '#e5534b')
    // "Không bên nào" — hoà và huỷ. Lấy `--text` chứ không cứng #fff: sang theme sáng
    // nó tự thành gần-đen, vẫn đúng nghĩa "trung tính" trên nền lúc đó.
    const TRUNG = mau('--text', '#e8e8e8')
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
        veRoi.current.set(khoa, '')
      } else {
        // ⚠ Màu là OPTION của series, chỉ đặt lúc TẠO. Không có dòng này thì một lệnh
        // chờ bị huỷ giữa chừng giữ nguyên đường CAM mãi mãi, thay vì chuyển trắng như
        // luật màu đã hứa — series đã tồn tại từ lúc nó còn đang chờ.
        s.applyOptions({ color: o.color, lineStyle: o.style ?? LineStyle.Solid })
      }
      /* ⚠ Effect này chạy lại MỖI KHUNG HÌNH (`tBayGio` đổi mỗi nhịp), mà `setData` của
       * lightweight-charts quét và sắp lại TOÀN BỘ trục thời gian. Một lượt chạy một năm
       * có ~500 lệnh × 3 đường = 1.500 lời gọi mỗi nhịp, phần lớn cho những lệnh đã đóng
       * từ nửa năm trước với dữ liệu Y HỆT — phát lại đứng hình vì thế.
       * Lệnh đã đóng thì `diem` BẤT BIẾN, nên nhớ vân tay rồi bỏ qua. Vân tay chỉ tính
       * DỮ LIỆU, không tính màu — nên nó không che mất cú đổi màu ở ngay trên. */
      const van = `${diem.length}|${diem[0].time},${diem[0].value}`
                + `|${diem[diem.length - 1].time},${diem[diem.length - 1].value}`
      if (veRoi.current.get(khoa) === van) return
      veRoi.current.set(khoa, van)
      s.setData(diem)
    }

    const mk: SeriesMarker<Time>[] = []

    /** Một CHẤM, đặt đúng trên MỨC GIÁ — không lơ lửng trên/dưới nến. */
    const cham = (t: number, gia: number, color: string, text?: string) =>
      mk.push({ time: t as UTCTimestamp, position: 'atPriceMiddle', price: gia,
                color, shape: 'circle', text })

    for (const l of hienLenh ? lenh : []) {
      if (l.t_dat > tBayGio) continue
      /* ⚠ Lệnh của BÀI KIỂM vẽ khác hẳn. Chúng sống có mấy giây nên đoạn vào→ra co
       * thành một chấm, và ba nhãn `R` chồng lên nhau — đúng cái rối bạn thấy.
       * Chúng là DỤNG CỤ ĐO, không phải kết quả chiến lược: một chấm mờ, không nhãn,
       * không đường TP/SL. Trộn chung một ngôn ngữ hình là tự làm rối. */
      if ((l as { la_kiem?: boolean }).la_kiem) {
        if (l.gia_khop != null && l.t_khop != null) {
          mk.push({ time: l.t_khop as UTCTimestamp, position: 'atPriceMiddle',
                    price: l.gia_khop, color: mau('--dim', '#7a7a7a'),
                    shape: 'circle', size: 0.6 })
        }
        continue
      }
      const daKhop = l.t_khop != null && l.t_khop <= tBayGio
      const daDong = l.t_dong != null && l.t_dong <= tBayGio
      const daHuy = daDong && l.ly_do_dong === 'huy'
      const het = daDong ? l.t_dong! : tBayGio
      /** Màu PHÁN QUYẾT — `null` nghĩa là lệnh chưa ngã ngũ, chưa được tô gì. */
      const pq = daHuy ? TRUNG
        : !daDong ? null
        : Math.abs(l.lai_R ?? 0) < HOA ? TRUNG
        : (l.lai_R ?? 0) > 0 ? LAI : LO

      // --- mức VÀO: từ lúc đặt tới lúc khớp (hoặc tới bây giờ nếu còn chờ).
      //     Huỷ thì cả đoạn chuyển trắng — nhưng VẪN gạch đứt. Màu nói "không thắng
      //     không thua", HÌNH nói "có xảy ra hay không": hoà là đường liền dày có chữ,
      //     huỷ là gạch đứt mảnh không chữ. Cho lệnh huỷ nổi bằng lệnh hoà là sai
      //     trọng số — nó là chuyện KHÔNG xảy ra. ---
      if (l.gia_dat != null) {
        doan(`${l.id}:vao`, hai(l.t_dat, daKhop ? l.t_khop! : het, l.gia_dat),
             { color: daHuy ? TRUNG : CAM, style: LineStyle.Dashed })
        cham(l.t_dat, l.gia_dat, daHuy ? TRUNG : CAM)
        if (daHuy) cham(l.t_dong!, l.gia_dat, TRUNG)
      }
      // --- TP: vẽ theo LỊCH SỬ y hệt SL, không phải bằng mức cuối backtest ---
      if (!daHuy) {
        const dp: Diem[] = (l.tp_lich_su ?? [])
          .filter(([t]) => t <= het)
          .map(([t, v]) => ({ time: t as UTCTimestamp, value: v }))
        if (dp.length) {
          dp.push({ time: Math.max(het, dp[dp.length - 1].time as number + 1) as UTCTimestamp,
                    value: dp[dp.length - 1].value })
          doan(`${l.id}:tp`, dp, { color: LAI, style: LineStyle.Dotted, bac: true })
        }
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
          doan(`${l.id}:sl`, ds, { color: LO, style: LineStyle.Dotted, bac: true })
        }
      }

      if (!daKhop) continue

      // --- CHẤM VÀO: đầu trái của đoạn vào→ra. Còn đang chạy thì cam (chưa có phán
      //     quyết); đóng rồi thì nhuộm theo phán quyết cùng với đường. ---
      if (l.gia_khop != null) cham(l.t_khop!, l.gia_khop, pq ?? CAM)

      // --- ĐOẠN vào→ra + CHẤM RA. Dốc lên xanh, dốc xuống đỏ, nằm ngang trắng — nhìn
      //     ĐỘ DỐC là biết lãi lỗ mà không cần đọc số. Chữ chỉ còn con R. ---
      if (daDong && l.gia_dong != null && l.gia_khop != null) {
        doan(`${l.id}:kq`, [
          { time: l.t_khop as UTCTimestamp, value: l.gia_khop },
          { time: Math.max(l.t_dong!, l.t_khop! + 1) as UTCTimestamp, value: l.gia_dong },
          // Nến đang xanh/đỏ thì đường kết quả phải DÀY hơn, không thì nhìn một cái
          // không biết vạch xanh kia là nến tăng hay lệnh thắng.
        ], { color: pq!, width: mauThuong ? 3 : 2 })
        cham(l.t_dong!, l.gia_dong, pq!, `${(l.lai_R ?? 0).toFixed(2)}R`)
      }
    }

    for (const [k, s] of [...lop.current]) {
      if (!con.has(k)) { c.removeSeries(s); lop.current.delete(k); veRoi.current.delete(k) }
    }
    mk.sort((a, b) => (a.time as number) - (b.time as number))
    mark.current?.setMarkers(mk)
  }, [lenh, tBayGio, hienLenh, mauThuong, doiSeries])

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
  }, [lenh, tBayGio, hienLenh, mauThuong, doiSeries])

  /* ĐƯỜNG RAY — nạp MỘT LẦN cho mỗi lệnh người dùng thật sự rê vào, rồi nhớ lại.
   *
   * ⚠ Không nhét vào lô phát: một lần chạy có ~300 lệnh mà hầu hết không ai soi, gói
   * đường ray của tất cả vào mỗi lô là phình payload cho thứ không dùng.
   * ⚠ Và không gọi theo mỗi lần chuột nhúc nhích: `subscribeCrosshairMove` bắn liên
   * tục, gọi Python theo nó là đúng thứ cơ chế lô sinh ra để tránh. Khoá theo id lệnh
   * nên quét ngang 10 lệnh là 10 lời gọi, không phải 500. */
  const rayNho = useRef<Map<string, ChangRay[]>>(new Map())
  const [ray, setRay] = useState<{ id: string; ds: ChangRay[] } | null>(null)

  useEffect(() => {
    const id = hien?.l.id
    if (!id || ray?.id === id) return
    const co = rayNho.current.get(id)
    if (co) return setRay({ id, ds: co })
    let bo = false
    void pyTester.test_duong_ray(id).then(r => {
      if (bo || !r.ok || !r.value) return
      rayNho.current.set(id, r.value.chang)
      setRay({ id, ds: r.value.chang })
    })
    return () => { bo = true }
  }, [hien?.l.id, ray?.id])

  // Chạy lại → id lệnh lặp lại nhưng nội dung khác hẳn. Dọn sạch, thà nạp lại (0,2 ms)
  // còn hơn hiện đường ray của lượt chạy trước.
  useEffect(() => { rayNho.current.clear(); setRay(null) }, [batDau])

  // Đường ray CẮT THEO CON TRỎ. Đang xem tới 09:30 mà bảng đã ghi "chạm SL" của 12:05
  // là lộ tương lai — đúng cái luật cả chart này đang giữ. Cắt ở đây chứ không gọi lại
  // Python: mỗi chặng đã mang sẵn `t`.
  const rayHien = ray && hien && ray.id === hien.l.id
    ? ray.ds.filter(c => c.t <= tBayGio) : []

  return (
    <div className="chart-boc" ref={boc}>
      {hien && (
        <div className="chart-goi-y"
             style={{
               left: hien.x + 14,
               // Bảng cao hơn hẳn khi có đường ray, nên rê ở nửa dưới là nó tràn khỏi
               // chart. Chạm nửa dưới thì lật lên trên con trỏ.
               top: hien.y > (boc.current?.clientHeight ?? 400) / 2
                 ? undefined : hien.y + 14,
               bottom: hien.y > (boc.current?.clientHeight ?? 400) / 2
                 ? (boc.current?.clientHeight ?? 400) - hien.y + 14 : undefined,
             }}>
          <b>{hien.l.id}</b> {hien.l.huong === 'mua' ? '▲ Mua' : '▼ Bán'} {hien.l.lot}
          <div>đặt {hien.l.gia_dat?.toFixed(digits)} · {gio(hien.l.t_dat)}</div>
          {hien.l.t_khop != null && hien.l.t_khop <= tBayGio && (
            <div>vào {hien.l.gia_khop?.toFixed(digits)} · {gio(hien.l.t_khop)}</div>
          )}
          {hien.l.t_dong != null && hien.l.t_dong <= tBayGio && (
            <>
              <div>ra {hien.l.gia_dong?.toFixed(digits) ?? '—'} · {gio(hien.l.t_dong)}</div>
              <div className={Math.abs(hien.l.lai_R ?? 0) < HOA ? ''
                              : (hien.l.lai_R ?? 0) > 0 ? 'lai' : 'lo'}>
                {hien.l.lai_R != null ? `${hien.l.lai_R.toFixed(2)} R · ` : ''}
                {hien.l.ly_do_dong}
              </div>
            </>
          )}

          {/* ĐƯỜNG RAY — lệnh này đi qua những khối nào. Chặng THỤT VÀO, không có tên
              tab, là chặng do THỊ TRƯỜNG quyết chứ không phải sơ đồ; phân biệt được
              hai thứ đó thường là cả câu trả lời khi soi một lệnh thua. */}
          {rayHien.length > 0 && (
            <div className="ray">
              {rayHien.map((c, k) => c.tab === null ? (
                <div key={k} className="ray-d cho">{MOC_CHU[c.moc ?? ''] ?? c.moc}</div>
              ) : (
                <div key={k} className="ray-d">
                  <span className="ray-tab">{c.tab === 'entry' ? 'Entry' : 'Manage'}</span>
                  <span className="ray-khoi">{c.khoi.join(' → ')}</span>
                  {c.dem > 1 && (
                    <span className="ray-dem">
                      ×{c.t_het > tBayGio ? '…' : c.dem}
                    </span>
                  )}
                  {c.viec.length > 0 && (
                    <span className="ray-viec">
                      {c.viec.map(v => VIEC_CHU[v] ?? v).join(', ')}
                    </span>
                  )}
                </div>
              ))}
            </div>
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
