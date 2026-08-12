import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { cho_cau_noi, pyLive } from '../api'
import { useKhungCuaSo } from '../useKhungCuaSo'
import CongChot from './CongChot'
import TitleBar, { type NhomMenu } from '../components/TitleBar'
import IconNet from '../components/Icon'
import Chart, { type Bar, type KieuChart, type NenM1 } from '../tester/Chart'
import NutChart from '../tester/NutChart'
import BangSoLieu, { type BangCat } from '../tester/BangSoLieu'
import Journey, { type DongNk } from '../tester/Journey'
import BangDuoi from '../tester/BangDuoi'
import { dungBang } from '../tester/Tester'
import type { DePhong, KetQuaHieuChuan, LenhVe, LoaiSo, MucBuoc, TinKetNoi,
              VanDeLive } from '../types'

/** DẤU CHO TỪNG MỨC — và đây là chỗ "lỗi" với "hỏng" tách làm hai trên màn hình.
 *
 * ⚠ `do` và `xac` là ĐẠT. Sàn có từ chối hay không là chuyện của sàn; câu hỏi của bài
 * kiểm là *ý định có thành hiện thực không*. Tô đỏ một bước mà tầng phòng vệ đã chữa
 * xong là báo động giả, và báo động giả thì lần sau không ai đọc nữa. */
const DAU: Record<MucBuoc, { d: string; ten: string; lop: string }> = {
  tron:  { d: '✓',  ten: 'chạy trơn',                       lop: 'dat' },
  xac:   { d: '◆',  ten: 'phòng vệ chặn trước — đoán đúng',  lop: 'xac' },
  do:    { d: '⟳',  ten: 'sàn từ chối, phòng vệ chữa được',  lop: 'do' },
  hong:  { d: '✕',  ten: 'phòng vệ bó tay — phải chỉnh',     lop: 'hong' },
  nguoi: { d: '⚑',  ten: 'cần bạn ra tay',                   lop: 'hong' },
  moc:   { d: '──', ten: '',                                 lop: 'moc' },
  chinh: { d: '⚙',  ten: 'chỉnh giả thuyết',                 lop: 'chinh' },
}
const mucCua = (b: { muc?: MucBuoc; dat: boolean }): MucBuoc =>
  b.muc ?? (b.dat ? 'tron' : 'hong')

/** XUẤT XỨ CỦA CON SỐ — và đây là chỗ "đo demo rồi chạy thật" đúng một nửa.
 *
 * ⚠ Bảng Đề phòng nhìn thì đồng nhất, nhưng ba loại dưới đây trả lời khác hẳn nhau
 * cho cùng một câu: *"số này mang từ demo sang tài khoản thật được không?"* Không
 * đánh dấu ra thì người dùng chép cả bảng — kể cả dòng duy nhất không được chép. */
const LOAI: Record<LoaiSo, { nhan: string; giai: string }> = {
  san:  { nhan: 'luật sàn',  giai: 'demo và thật giống nhau — dùng thẳng được' },
  khop: { nhan: 'chất lượng khớp',
          giai: 'demo KHÔNG có thanh khoản thật — số đo chỉ là chặn dưới' },
  ta:   { nhan: 'luật của ta', giai: 'không phụ thuộc tài khoản nào' },
}

/** CỬA SỔ LIVE — DÙNG CHUNG `Chart` · `BangSoLieu` · `Journey` với Strategy Tester.
 *
 * ⚠ Không copy, không fork. Ba component đó nhập thẳng từ `../tester/`, nên sau này sửa
 * màu chart hay cách vẽ lệnh là đổi CẢ HAI cửa sổ — không có bản thứ hai để trôi xa.
 *
 * Làm được thế vì `ApiLive` kế thừa bề mặt ĐỌC của `ApiTester` và chỉ đổi đúng một chỗ:
 * `_doi_kq()` trả ẢNH CHỤP SỐNG thay cho kết quả backtest. Nên `test_doan` ở đây trả về
 * đúng bộ khoá mà tester đang ăn — giao diện không biết mình đang xem live hay backtest.
 *
 * Khác tester đúng ba chỗ:
 *    thanh công cụ  không có nút phát lại — live chỉ có MỘT con trỏ: bây giờ
 *    bảng dưới      Vấn đề · Kết nối · Nhật ký (không có Thống kê — sàn làm rồi)
 *    con trỏ        luôn ở nến mới nhất, tự nhảy khi sàn đóng nến
 */

/** Nhịp hỏi sức khoẻ kết nối. Nến thì do Python đẩy sang qua `live_nen`. */
const NHIP_MS = 1000

/** Số khung hình lấy về mỗi lần làm mới. Chỉ cần đủ cho nhật ký có bối cảnh —
 *  live không tua lại nên không cần đệm như bộ phát lại của tester. */
// ⚠ 120 chứ không 900. Đo được: `test_doan(-1, 900)` là **178 KB** mỗi phút qua cầu
// nối pywebview — mà cầu nối đó ĐỒNG BỘ và mã hoá payload HAI LẦN, nên kích thước gói
// là chỗ đau chứ không phải thời gian Python (13 ms). Live không tua lại nên 900 khung
// hình chỉ để nhật ký có bối cảnh; 120 là quá đủ.
const LO = 120

/** Trần nến cho chart Live. Đây là chart QUAN SÁT như chart trading, không phải cuốn
 *  phim để tua — 2.000 nến là quá đủ cho một màn hình và vài lần kéo lùi. Test giữ
 *  60.000 vì ở đó bạn có quyền nhảy về bất kỳ đâu. */
const TRAN_NEN = 2000

function o(x: number | null | undefined, don = '', so = 0) {
  return x == null ? '—' : `${x.toFixed(so)}${don}`
}

type Boot = { san_sang: boolean; ten: string; symbol: string; bat_dau_luc: number | null
              goi_y: string; ds_luu: string[]; symbol_mac_dinh: string
              /** Số lẻ THẬT của symbol. Viết cứng 2 thì EURUSD (5 số) vẽ ra một vạch. */
              digits: number }

export default function Live() {
  /* ⚠ KÉO + GIÃN CỬA SỔ. Thiếu đúng dòng này là cửa sổ Live không kéo được, không giãn
   * được, không bấm đúp phóng to được, không Aero Snap — vì `frameless=True` đã xoá
   * viền hệ thống mà không có ai dựng lại. Ba nút thu nhỏ/phóng to/đóng vẫn chạy nên
   * nhìn thoáng qua tưởng thanh tiêu đề ổn. App.tsx và Tester.tsx đều gọi; chỉ Live
   * sót — xem `useKhungCuaSo` để biết vì sao việc này BẮT BUỘC do web khởi động. */
  useKhungCuaSo(32)

  const [boot, setBoot] = useState<Boot | null>(null)
  const [tin, setTin] = useState<TinKetNoi | null>(null)
  /** Số liệu đang ĐÔNG CỨNG (đang hiệu chuẩn, hoặc luồng máy đứng). Phải nói ra:
   *  hiện `tuổi tick 1.4 s` đứng yên suốt ba phút là nói dối đúng chỗ cần tin nhất. */
  const [tamDung, setTamDung] = useState(false)
  const [vanDe, setVanDe] = useState<VanDeLive[]>([])
  const [chiViec, setChiViec] = useState(false)
  // Trạng thái XEM chart — thuộc về cửa sổ, không thuộc về dữ liệu.
  const [tfVe, setTfVe] = useState(5)
  const [kieu, setKieu] = useState<KieuChart>('nen')
  const [mauThuong, setMauThuong] = useState(false)
  const [hienLenh, setHienLenh] = useState(true)
  const [veNay, setVeNay] = useState(0)
  const [hienBang, setHienBang] = useState(true)
  const [dePhong, setDePhong] = useState<DePhong | null>(null)
  const [epTab, setEpTab] = useState<string | undefined>(undefined)
  const [dong, setDong] = useState<string[]>([])
  const [dangTest, setDangTest] = useState(false)
  /** `[vòng, tổng vòng, lượt, tổng lượt]` — phải có cả LƯỢT, xem chú thích ở nút. */
  const [kiemVong, setKiemVong] = useState<number[]>([0, 0, 0, 0])
  const [ketQuaTest, setKetQuaTest] = useState<KetQuaHieuChuan | null>(null)

  // --- những thứ ba component dùng chung cần, đúng tên như ở Tester ---
  const [lenh, setLenh] = useState<LenhVe[]>([])
  const [nhatKy, setNhatKy] = useState<DongNk[]>([])
  const [khungBang, setKhungBang] = useState<BangCat | null>(null)
  const [datNen, setDatNen] = useState<Bar[] | null>(null)
  /** ĐUÔI vừa chốt — Chart áp bằng `update()`, không dựng lại series, không giật
   *  tầm nhìn của người đang xem chỗ khác. */
  const [duoiNen, setDuoiNen] = useState<Bar[] | null>(null)
  const [themNen, setThemNen] = useState<NenM1 | null>(null)
  const [batDau, setBatDau] = useState(0)
  const [tBayGio, setTBayGio] = useState(0)
  const [j, setJ] = useState(0)
  const truoc = useRef('')
  /** Đã ghi bao nhiêu bước bài kiểm vào nhật ký — chỉ ghi phần MỚI. */
  const kiemDaGhi = useRef(0)

  /* ⚠ `useCallback` chứ không viết thẳng vào JSX: `Journey` đã bọc `memo`, mà một prop
     hàm mới ở mỗi lần vẽ là đủ để `memo` vô hiệu hoàn toàn. Cửa sổ Live vẽ lại mỗi
     giây, nhật ký thì hàng trăm dòng và một phút mới đổi. */
  const soi = useCallback((i: number) => { void pyLive.test_soi_luot(i) }, [])

  const ghi = useCallback((chu: string) => {
    const t = new Date().toLocaleTimeString('vi', { hour12: false })
    setDong(d => [...d.slice(-400), `${t}  ${chu}`])
  }, [])

  /** Mốc cây nến CUỐI mà chart đang giữ — để xin đuôi thay vì xin lại cả mảng. */
  const tCuoi = useRef(0)
  /** Số thứ tự lượt làm mới — xem chốt chống chồng lượt trong `lamMoi`. */
  const luot = useRef(0)

  /** Làm mới. `dayDu = false` (mặc định, mỗi lần nến đóng) chỉ xin phần ĐUÔI.
   *
   *  ⚠ Đây là chỗ tốn nhất của cửa sổ Live, đo được: một lượt đầy đủ là
   *  `test_nen_tf` **134 KB** + `test_doan` 31 KB qua cầu nối pywebview — mà cầu nối
   *  đó ĐỒNG BỘ và mã hoá payload HAI LẦN. Mỗi phút chép lại 133 KB không hề đổi chỉ
   *  để thêm một cây nến. Xin đuôi thì gói còn khoảng trăm byte.
   *
   *  Nạp đầy chỉ khi thật sự cần dựng lại lưới: lúc mở, và lúc đổi khung. */
  const lamMoi = useCallback(async (dayDu = false) => {
    /* ⚠ CHỐNG CHỒNG LƯỢT. `lamMoi` có hai `await`, mà nó bị gọi từ HAI nguồn không
     * hẹn nhau: sự kiện nến đóng, và cú đổi khung. Đổi khung giữa lúc một lượt cũ đang
     * chờ `test_doan` thì lượt cũ tỉnh dậy với `tfVe` MỚI nhưng ý định CŨ, xin nến
     * khung cũ rồi `setDuoiNen` một mảng sai lưới — chart gãy, nặng thì `s.update` ném
     * `Cannot update oldest data` và React gỡ cả cây (cửa sổ trắng).
     * Đánh số lượt, chụp tham số NGAY trước await đầu, và bỏ lượt đã cũ sau mỗi await. */
    const lan = ++luot.current
    const tf = tfVe
    const tu = dayDu ? 0 : tCuoi.current
    const d = await pyLive.test_doan(-1, LO)   // -1 = "lấy đoạn cuối", Python tự kẹp
    if (lan !== luot.current) return
    if (!d.ok || !d.value) return
    const L = d.value
    const k = L.n - 1
    setLenh(L.lenh)
    setNhatKy(L.nhat_ky)
    setKhungBang(dungBang(L, k))
    setTBayGio(L.t[k])
    setJ(L.j0 + k)
    const TEN: Record<number, string> = { 1: 'M1', 5: 'M5', 15: 'M15', 60: 'H1', 240: 'H4' }
    const n = await pyLive.test_nen_tf(TEN[tf] ?? 'M5', L.j0 + k, TRAN_NEN, tu)
    if (lan !== luot.current) return
    if (n.ok && n.value) {
      const v = n.value
      const bar = (x: number) => ({ time: v.t[x] as never, open: v.o[x],
                                    high: v.h[x], low: v.l[x], close: v.c[x] })
      if (v.t.length) tCuoi.current = v.t[v.t.length - 1]
      if (dayDu) {
        // Chỉ giữ đuôi: đây là chart QUAN SÁT, không cần cả lịch sử. Điều đáng giữ
        // chuẩn là từ lúc bấm ghi hình trở đi — phần trước chỉ để mắt có bối cảnh.
        const d0 = Math.max(0, v.t.length - TRAN_NEN)
        setDatNen(v.t.slice(d0).map((_, x) => bar(d0 + x)))
        setBatDau(x => x + 1)
        setThemNen(null)
        // Bỏ đuôi cũ: nó là lưới của KHUNG TRƯỚC. Chart đã có chốt `tfCuaBars` chặn
        // gộp chéo khung, nhưng để lại một mảng sai lưới nằm đó là mời một lỗi sau này.
        setDuoiNen(null)
      } else {
        setDuoiNen(v.t.map((_, x) => bar(x)))
      }
    }
  }, [tfVe])

  /* ⚠ Giữ `lamMoi` trong ref. Trước đây effect nạp phụ thuộc thẳng vào `lamMoi`, mà
   * `lamMoi` đổi mỗi khi `tfVe` đổi — nên **đổi khung là khởi động lại cả vòng**: gọi
   * lại `live_boot`, dựng lại bộ hẹn giờ, gắn lại listener. Đó là chỗ giật. */
  const lamMoiRef = useRef(lamMoi)
  lamMoiRef.current = lamMoi

  /* Đổi khung phải vẽ lại NGAY. Không có effect này thì nó chỉ ăn ở lần nến đóng kế
     tiếp — có khi cả phút sau — nên bấm xong tưởng nút hỏng. */
  useEffect(() => { tCuoi.current = 0; void lamMoiRef.current(true) }, [tfVe])

  useEffect(() => {
    let dung = false
    ;(async () => {
      await cho_cau_noi('live_boot')
      const b = await pyLive.live_boot()
      if (b.ok && b.value) setBoot(b.value as Boot)

      // Python đẩy sang khi vòi cấp nến nạp xong / có nến mới đóng.
      window.__su_kien = (ten, d) => {
        if (ten !== 'live_nen') return
        const x = d as { moi?: number; nap_xong?: boolean; loi?: string }
        if (x.loi) return ghi(`⚠ nến: ${x.loi}`)
        // Nạp xong lần đầu thì dựng lưới; từ đó về sau mỗi nến đóng chỉ xin ĐUÔI.
        if (x.nap_xong) {
          ghi(`Nến về: +${x.moi ?? 0}`)
          void lamMoiRef.current(!tCuoi.current)
        }
      }

      void pyLive.live_de_phong().then(d => { if (d.ok && d.value) setDePhong(d.value) })
      const nhip = async () => {
        if (dung) return
        // Truyền số bước ĐÃ nhận — Python chỉ gửi phần mới. Bài hiệu chuẩn sinh vài
        // chục bước; gửi lại cả danh sách mỗi giây là chép một thứ không đổi hàng
        // trăm lần qua đúng cái cầu nối đang làm giao diện chậm.
        const r = await pyLive.live_tin(kiemDaGhi.current)
        if (r.ok && r.value) {
          const x = r.value as { kiem_vong?: number[]; kiem_tong?: number
                                 tam_dung?: boolean
                                 kiem_dong?: { ten: string; dat: boolean; chu: string
                                               muc?: MucBuoc }[] }
          setKiemVong(x.kiem_vong ?? [0, 0, 0, 0])
          setTamDung(!!x.tam_dung)
          // Từng bước bài kiểm chảy vào nhật ký NGAY lúc xảy ra. Live thì mọi thứ chạm
          // vào sàn đều phải để lại vết đúng lúc — không gom tới cuối mới đổ ra.
          const ds = x.kiem_dong ?? []
          if (ds.length) {
            for (const b of ds) ghi(`${DAU[mucCua(b)].d} ${b.ten}${b.chu ? ' · ' + b.chu : ''}`)
            kiemDaGhi.current = x.kiem_tong ?? (kiemDaGhi.current + ds.length)
          }
        }
        if (r.ok && r.value?.tin) {
          setTin(r.value.tin)
          // ⭐ Cây nến đang chạy → chart nhấp nháy theo GIÂY như mọi chart trading.
          // `Chart.gop()` tự gộp nó vào cây đang hình thành. Chiến lược không đụng tới
          // nó: quyết định vẫn chỉ ở biên nến đã đóng.
          if (r.value.tin.nen_dang) setThemNen(r.value.tin.nen_dang)
          setVanDe(r.value.van_de ?? [])
          const van = [r.value.tin.noi_duoc, r.value.tin.nen_song,
                       r.value.tin.cho_giao_dich, r.value.tin.symbol_giao_dich_duoc,
                       (r.value.van_de ?? []).length].join('|')
          if (van !== truoc.current) {
            truoc.current = van
            ghi(r.value.tin.nen_song ? 'Kết nối OK' : `⚠ ${r.value.tin.chu}`)
            for (const v of r.value.van_de ?? []) ghi(`[${v.severity}] ${v.message}`)
          }
        }
        if (!dung) window.setTimeout(nhip, NHIP_MS)
      }
      void nhip()
    })()
    return () => { dung = true; window.__su_kien = undefined }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ghi])

  /* Ctrl+W đóng cửa sổ. Gắn phím THẬT chứ không chỉ ghi nhãn trong menu — nhãn phím mà
     bấm không ăn thì tệ hơn là không ghi. */
  useEffect(() => {
    const f = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'w') {
        e.preventDefault(); void pyLive.cua_so_dong()
      }
    }
    window.addEventListener('keydown', f)
    return () => window.removeEventListener('keydown', f)
  }, [])

  /* MENU — cửa sổ Live trước đây truyền `menus={[]}`, tức nó là cửa sổ DUY NHẤT không
     có menu nào, và mấy việc cơ bản không có chỗ nào để gọi. Giữ đúng ba việc thật sự
     thuộc về cửa sổ này; xem chart thì đã có cụm icon ở thanh công cụ rồi. */
  const menuTieuDe: NhomMenu[] = useMemo(() => [
    { ten: 'Live', muc: [
      { ten: 'Về cửa sổ vẽ', icon: 'copy',
        onClick: () => void pyLive.live_ve_so_do() },
      { ten: 'Dọn rác bài kiểm', tat: dangTest,
        viSao: dangTest ? 'đang hiệu chuẩn — nó tự dọn khi xong' : undefined,
        onClick: async () => {
          const r = await pyLive.live_don_rac()
          if (!r.ok) return ghi(`⚠ dọn rác: ${r.error}`)
          const v = r.value
          ghi(v && (v.da_dong || v.da_huy)
            ? `Đã dọn: đóng ${v.da_dong} vị thế · huỷ ${v.da_huy} lệnh chờ`
            : 'Không còn rác nào của bài kiểm.')
        } },
      { ngan: true },
      { ten: 'Đóng cửa sổ', phim: 'Ctrl+W',
        onClick: () => void pyLive.cua_so_dong() },
    ] },
  ], [dangTest, ghi])

  /** Số lẻ của symbol đang chạy. XAUUSD may mắn đúng 2; EURUSD thì 5. */
  const soLe = boot?.digits ?? 2

  const song = !!tin?.nen_song
  const that = tin?.la_that === true
  /* ⚠ CHỈ mức `hong` và `nguoi` mới thành Vấn đề.
   *
   * Bản trước lấy `!b.dat` nên mọi lần sàn từ chối đều nhảy vào đây — kể cả khi tầng
   * phòng vệ đã chữa xong và lệnh vẫn vào được. Đó là báo động giả, mà bảng Vấn đề có
   * một báo động giả thì cả bảng mất giá trị.
   *
   * Và chỉ lấy của LƯỢT CUỐI: vòng lặp cố tình chạy lại sau khi chỉnh, nên lỗi của
   * lượt 1 là thứ đã được sửa xong — treo nó lên là kể chuyện cũ. */
  const vanDeDu = [...vanDe, ...(ketQuaTest?.trang_thai === 'xong' ? [] : (() => {
    const b = ketQuaTest?.buoc ?? []
    const moc = b.map((x, i) => (x.muc === 'moc' ? i : -1)).filter(i => i >= 0)
    return b.slice(moc.length ? moc[moc.length - 1] : 0)
  })())
    .filter(b => mucCua(b) === 'hong' || mucCua(b) === 'nguoi')
    .map(b => ({ severity: mucCua(b) === 'nguoi' ? 'error' : 'warning',
                 message: `Bài kiểm — ${b.ten}: ${b.chu}`, tab: 'live' }))]
  const soLoi = vanDeDu.filter(v => v.severity === 'error').length
  const batDauChu = boot?.bat_dau_luc
    ? new Date(boot.bat_dau_luc * 1000).toISOString().slice(0, 16).replace('T', ' ')
    : ''

  const hang = (ten: string, gia: string, ok?: boolean | null, ghiChu = '') => (
    <div className="lv-hang">
      <span className="lv-ten">{ten}</span>
      <span className={'lv-gt' + (ok === true ? ' dat' : ok === false ? ' hong' : '')}>{gia}</span>
      {ghiChu && <span className="lv-phu">{ghiChu}</span>}
    </div>
  )

  return (
    <div className="khung">
      {/* Đèn kết nối + badge tài khoản nằm CẠNH LOGO, không nằm trong thanh công cụ.
          Chúng là trạng thái của cả cửa sổ, không phải một công cụ để bấm — và ở trên
          đó thì thanh công cụ trả lại chỗ cho đúng thứ là công cụ. */}
      <TitleBar tieuDe={boot?.san_sang ? `${boot.ten} · ${boot.symbol} — Live` : 'Live'}
                menus={menuTieuDe}
                them={<span className="lv-trang-thai">
                  <span className={'lv-den' + (tamDung ? ' nghi'
                                                : song ? ' song' : ' chet')} />
                  <b>{tamDung ? 'TẠM DỪNG ĐO' : song ? 'ĐANG NỐI' : 'MẤT KẾT NỐI'}</b>
                  <span className={'lv-badge' + (that ? ' that' : ' demo')}>
                    {tin?.la_that == null ? '—' : that ? '⚠ THẬT' : 'DEMO'}
                  </span>
                </span>} />

      {boot && !boot.san_sang && (
        <CongChot boot={boot}
                  xong={(ten, symbol) => {
                    setBoot({ ...boot, san_sang: true, ten, symbol })
                    // Nạp lại để lấy `bat_dau_luc` — vòi cấp nến vừa chốt mốc đó.
                    window.setTimeout(async () => {
                      const b2 = await pyLive.live_boot()
                      if (b2.ok && b2.value) setBoot(b2.value as Boot)
                    }, 2500)
                    ghi(`Bắt đầu: ${ten} · ${symbol}`)
                  }} />
      )}

      {/* Công cụ dồn về TRÁI — tay quét từ trái sang, và đó là thứ hay bấm nhất.
          Đồng hồ + nút kiểm tra đẩy sang phải: một cái để liếc, một cái hiếm bấm. */}
      <div className="tb">
        <NutChart tf={tfVe} dsTf={[['M1', 1], ['M5', 5], ['M15', 15], ['H1', 60], ['H4', 240]]}
                  datTf={setTfVe} kieu={kieu} datKieu={setKieu}
                  mauThuong={mauThuong} datMau={setMauThuong}
                  hienLenh={hienLenh} datHienLenh={setHienLenh}
                  veHienTai={() => setVeNay(x => x + 1)} />
        <span className="tb-day" />
        <span className="lv-che-do">{tBayGio ? new Date(tBayGio * 1000)
          .toISOString().slice(0, 16).replace('T', ' ') : '—'}</span>
        <span className="tb-ngan" />
        {/* Cụp bảng thông số bên phải — giống nút cùng việc ở Strategy Tester. Chart cần
            bề ngang lúc soi giá, mà bảng kia thì không phải lúc nào cũng cần nhìn. */}
        <button className={'tb-nut' + (hienBang ? ' bat' : '')}
                title={hienBang ? 'Cụp bảng thông số' : 'Mở bảng thông số'}
                onClick={() => setHienBang(v => !v)}>
          <IconNet name="copy" size={15} />
        </button>
      </div>

      {/* ---- ĐÚNG khung tester: chart trái, bảng chỉ số phải ---- */}
      <div className="tt-giua">
        <Chart tfPhut={tfVe} digits={soLe} lenh={lenh} tBayGio={tBayGio}
               batDau={batDau} dat={datNen} them={themNen} duoi={duoiNen}
               kieu={kieu} mauThuong={mauThuong} hienLenh={hienLenh}
               veHienTai={veNay} tranNen={TRAN_NEN} />
        {hienBang && <BangSoLieu k={khungBang} digits={soLe} />}
      </div>

      {/* VỎ BẢNG DƯỚI DÙNG CHUNG với Strategy Tester — thanh kéo, nút gập, số đếm,
          cách bấm tab đang mở để cụp: y hệt. Hai cửa sổ chỉ khác NỘI DUNG tab. */}
      <BangDuoi tabs={[
        { khoa: 'van-de', nhan: 'Vấn đề', dem: vanDeDu.length,
          ve: () => (
            <div className="nk-cuon">
              {vanDeDu.length === 0
                ? <div className="cd-rong">Không có vấn đề nào.</div>
                : vanDeDu.map((v, k) => (
                  <div key={k} className={'lv-vd ' + v.severity}>
                    <span className="lv-vd-muc">
                      {v.severity === 'error' ? 'LỖI' : 'CẢNH BÁO'}
                    </span>
                    <span>{v.message}</span>
                  </div>
                ))}
            </div>
          ) },
        { khoa: 'ket-noi', nhan: 'Kết nối',
          ve: () => (
            <div className="nk-cuon lv-bang">
              {/* Nút kiểm tra nằm Ở ĐÂY, cạnh chính mấy con số nó sinh ra — chứ không
                ở thanh công cụ. Bấm xong kết quả hiện ngay bên dưới, không phải đi tìm. */}
            <div className="lv-nhom">
            <div className="lv-dau lv-dau-nut">
              <span>Tài khoản</span>
              {/* ⚠ Chặn ngay ở nút, không đợi Python từ chối. Bài này MỞ VÀ ĐÓNG LỆNH
                  THẬT — đó là lý do nó chỉ chạy trên demo. Tài khoản thật thì dùng bộ
                  số đã đo ở demo, không đo lại. */}
              <button className="nut-nho"
                      disabled={dangTest || !boot?.san_sang || that}
                      title={that ? 'Bài kiểm đặt lệnh THẬT nên chỉ chạy trên demo — '
                                    + 'tài khoản thật dùng lại hồ sơ đã đo ở demo'
                                  : 'Mở/đóng lệnh thật trên demo để đo, rồi tự chỉnh '
                                    + 'tới khi hết hỏng'}
                      onClick={async () => {
                        setDangTest(true); setKetQuaTest(null); kiemDaGhi.current = 0
                        ghi('Bắt đầu hiệu chuẩn — chạy, chỉnh, chạy lại tới khi hết hỏng…')
                        // ⚠ `false` từng rơi vào đúng tham số `so_vong` → `int(False) = 0` → bài kiểm
                        // bỏ sạch phần mở/đóng market, chỉ còn ba bước lệnh chờ.
                        const r = await pyLive.live_test_ket_noi(3, 15, 4)
                        setDangTest(false)
                        if (r.ok && r.value) {
                          setKetQuaTest(r.value); ghi(`Hiệu chuẩn: ${r.value.chu}`)
                          // TỰ CẬP NHẬT, không có nút Áp dụng. Bài kiểm vừa ghi bộ số mới
                          // vào hồ sơ; khối Đề phòng phải nói ngay con số hiện hành, chứ
                          // bắt bấm thêm một nút nữa là mời người dùng quên bấm.
                          const d = await pyLive.live_de_phong()
                          if (d.ok && d.value) setDePhong(d.value)
                        }
                      }}>{!dangTest ? 'Hiệu chuẩn kết nối'
                          /* ⚠ Hiện cả LƯỢT. Chỉ hiện vòng thì nó reset về 1/3 sau mỗi
                             lượt, và bốn lượt trông y hệt một vòng lặp vô tận. */
                          : kiemVong[1] ? `đang hiệu chuẩn… lượt ${kiemVong[2]}/${kiemVong[3]}`
                                          + ` · vòng ${kiemVong[0]}/${kiemVong[1]}`
                                        : 'đang hiệu chuẩn…'}</button>
            </div>
              {hang('Số tài khoản', tin?.tai_khoan ? String(tin.tai_khoan) : '—')}
              {hang('Sàn · server', tin ? `${tin['sàn'] || '—'} · ${tin.server || '—'}` : '—')}
              {hang('Loại', tin?.la_that == null ? '—' : that ? 'THẬT' : 'Demo',
                    tin?.la_that == null ? null : !that)}
            </div>

            <div className="lv-nhom">
              <div className="lv-dau">Mạch đập</div>
              {tamDung && (
                <div className="lv-de-nghi canh">
                  Số liệu bên dưới <b>đang đông cứng</b> — máy tạm ngừng đo
                  {dangTest ? ' vì bài hiệu chuẩn đang giữ cầu nối' : ''}. Đừng đọc
                  chúng như đang sống.
                </div>
              )}
              {hang('Tuổi tick cuối', o(tin?.tuoi_tick, ' s', 1), song,
                    'terminal báo đã nối vẫn có thể là feed đứng')}
              {hang('Rớt trong phiên',
                    `${tin?.so_lan_rot ?? 0} lần · ${o(tin?.giay_rot, ' s', 0)}`,
                    (tin?.so_lan_rot ?? 0) === 0)}
              {hang('Lệch giờ server', o(tin?.lech_gio, ' phút', 0), null,
                    'nến đóng theo giờ SERVER')}
            </div>

            <div className="lv-nhom">
              <div className="lv-dau">Có giao dịch được không</div>
              {hang('AlgoTrading + EA', tin?.cho_giao_dich ? 'BẬT' : 'TẮT',
                    !!tin?.cho_giao_dich, 'tắt là mọi lệnh bị từ chối')}
              {hang('Symbol', tin?.symbol_giao_dich_duoc ? 'giao dịch được' : 'KHÔNG',
                    !!tin?.symbol_giao_dich_duoc)}
              {hang('Spread hiện tại', o(tin?.spread_diem, ' điểm', 1))}
            </div>

            {/* ĐỀ PHÒNG — trình bày Y HỆT khối Tài khoản: nhãn · giá trị · ghi chú.
                Nó BÁO CÁO hệ thống đang tự bảo vệ bằng gì, không phải form để chỉnh.
                Ghi chú nói NGUỒN — "đo được" hay "đang đoán" — mới là chỗ có giá trị. */}
            <div className="lv-nhom">
              <div className="lv-dau">Đề phòng</div>

              {/* Chú giải ba loại — đặt TRƯỚC bảng, vì không có nó thì mấy cái nhãn nhỏ
                  bên dưới chỉ là chữ trang trí. Câu chúng trả lời: số này mang từ demo
                  sang tài khoản thật được không. */}
              <div className="lv-chu-giai">
                {(['san', 'khop', 'ta'] as LoaiSo[]).map(l =>
                  <span key={l} className="lv-cg">
                    <span className={'lv-loai ' + l}>{LOAI[l].nhan}</span> {LOAI[l].giai}
                  </span>)}
              </div>

              {(dePhong?.dong ?? []).map((d, k) => {
                // Trên tài khoản THẬT, dòng `khop` đo ở demo là con số lạc quan — tô
                // riêng, vì đây đúng là chỗ chép nguyên si sang sẽ mất tiền.
                const ngo = d.loai === 'khop' && !!dePhong?.la_that && !!dePhong?.da_hieu_chuan
                return (
                  <div key={k} className={'lv-hang' + (ngo ? ' lv-ngo' : '')}>
                    <span className="lv-ten">
                      {d.ten}<span className={'lv-loai ' + d.loai}>{LOAI[d.loai].nhan}</span>
                    </span>
                    <span className="lv-gt">{d.gia}</span>
                    <span className="lv-phu">
                      {d.chu}{ngo && ' · ĐO Ở DEMO — tài khoản thật gần như chắc chắn xấu hơn'}
                    </span>
                  </div>
                )
              })}

              {dePhong?.chep_tu && (
                <div className="lv-de-nghi canh">
                  Bộ số này <b>chép từ «{dePhong.chep_tu}»</b>, không đo tại sàn này.
                  Mấy dòng <span className="lv-loai san">luật sàn</span> vẫn đúng;
                  dòng <span className="lv-loai khop">chất lượng khớp</span> chỉ là chặn dưới.
                </div>
              )}

              {/* ⚠ CÂY CẦU DEMO → THẬT. Hồ sơ khoá theo tên sàn, mà một sàn có thể có
                  nhiều pháp nhân — demo báo một chuỗi, tài khoản thật báo chuỗi khác.
                  Không có ô này thì live lặng lẽ rơi về số mặc định đang đoán. */}
              {!!dePhong?.ho_so_khac?.length && (
                <div className="lv-de-nghi canh lv-chep">
                  <span>
                    Chưa có hồ sơ cho sàn này, nhưng <b>{boot?.symbol}</b> đã đo ở nơi khác.
                    Nếu đó là cùng một sàn (demo và thật thường báo tên khác nhau), dùng lại
                    được ngay:
                  </span>
                  <span className="lv-chep-ds">
                    {dePhong.ho_so_khac.map(h => (
                      <button key={h.khoa} className="nut-nho"
                              title={`đo ${h.do_luc ?? '—'} · ${h.server || 'server ?'}`}
                              onClick={async () => {
                                const r = await pyLive.live_chep_ho_so(h.khoa)
                                if (!r.ok) return ghi(`⚠ chép hồ sơ: ${r.error}`)
                                ghi(`Đã dùng hồ sơ đo ở «${h.san}» cho sàn này.`)
                                const d = await pyLive.live_de_phong()
                                if (d.ok && d.value) setDePhong(d.value)
                              }}>
                        dùng hồ sơ «{h.san}»
                      </button>
                    ))}
                  </span>
                </div>
              )}

              {dePhong && !dePhong.da_hieu_chuan && !dePhong.ho_so_khac?.length && (
                <div className="lv-de-nghi canh">
                  Chưa hiệu chuẩn — mọi con số trên là <b>phỏng đoán</b>. Chạy bài kiểm
                  trên demo để đo thật; kết quả tự ghi vào hồ sơ, không cần bấm gì thêm.
                </div>
              )}
              {dePhong?.trang_thai === 'chua_hoi_tu' && (
                <div className="lv-de-nghi canh">
                  Lần hiệu chuẩn gần nhất <b>chưa chốt được</b> — vẫn còn chỗ hỏng sau khi
                  đã chỉnh hết mức. Số ở trên là cái tốt nhất học được, chưa phải cái đúng.
                </div>
              )}
            </div>

              {ketQuaTest && (
                <div className="lv-nhom lv-nhom-rong">
                  <div className="lv-dau">Bài kiểm — vòng lặp tự chỉnh</div>

                  {/* BA TRẠNG THÁI KẾT THÚC, không phải "N/M bước đạt". Con số đó trộn
                      bốn thứ khác hẳn nhau vào một rổ rồi bắt người đọc tự tách. */}
                  <div className={'lv-tt lv-tt-' + ketQuaTest.trang_thai}>
                    {ketQuaTest.trang_thai === 'xong' ? (
                      <><b>✓ Đã chốt xong.</b> Bảng <b>Đề phòng</b> bên trên giờ là số đã
                        qua kiểm — không còn dòng nào là phỏng đoán. {ketQuaTest.chu}</>
                    ) : ketQuaTest.trang_thai === 'nguoi' ? (
                      <><b>⚑ Cần bạn ra tay.</b> Máy dừng vì gặp thứ chỉnh con số bao
                        nhiêu cũng vô ích.</>
                    ) : (
                      <><b>⚠ Chưa chốt được.</b> {ketQuaTest.chu}</>
                    )}
                  </div>

                  {ketQuaTest.can_nguoi?.map((c, k) =>
                    <div key={k} className="lv-de-nghi canh">{c}</div>)}

                  {/* Vì sao con số trong Đề phòng vừa đổi. Không có phần này thì bảng kia
                      tự nhiên khác đi mà không ai biết tại sao — đúng kiểu lệch âm thầm. */}
                  {!!ketQuaTest.da_chinh?.length && (
                    <div className="lv-chinh">
                      <div className="lv-chinh-dau">Đã chỉnh giả thuyết
                        <span> — lỗi tự khai giá trị đúng, hồ sơ tự cập nhật</span></div>
                      {ketQuaTest.da_chinh.map((c, k) =>
                        <div key={k} className="lv-chinh-dong">⚙ {c}</div>)}
                    </div>
                  )}

                  {ketQuaTest.stops_level_that != null && (
                    <div className="lv-de-nghi canh">
                      SL/TP phải cách giá tối thiểu <b>{ketQuaTest.stops_level_that} điểm</b>
                      {' '}— đo được, không phải con số sàn khai. SL của sơ đồ ngắn hơn thế
                      sẽ bị từ chối.
                    </div>
                  )}

                  {!!ketQuaTest.ma_la?.length && (
                    <div className="lv-de-nghi canh">
                      Gặp mã sàn <b>{ketQuaTest.ma_la.join(', ')}</b> mà hệ thống chưa có
                      luật xử — đang thử lại tạm. Đây là cái ta chưa biết, và nó chịu lộ
                      mặt ở đây thay vì trôi qua im lặng.
                    </div>
                  )}

                  {/* Chú giải nằm NGAY TRÊN danh sách. Không có nó thì ◆ với ⟳ chỉ là hai
                      ký tự lạ, và người đọc lại quy hết về "có lỗi". */}
                  <div className="lv-chu-giai">
                    {(['tron', 'xac', 'do', 'hong'] as MucBuoc[]).map(m =>
                      <span key={m} className={'lv-cg ' + DAU[m].lop}>
                        <b>{DAU[m].d}</b> {DAU[m].ten}
                      </span>)}
                  </div>

                  {ketQuaTest.buoc.map((b, k) => {
                    const m = mucCua(b)
                    if (m === 'moc') {
                      return <div key={k} className="lv-moc-lap">{b.ten}</div>
                    }
                    return (
                      <div key={k} className="lv-hang">
                        <span className={'lv-ten ' + DAU[m].lop}>
                          {DAU[m].d} {b.ten}
                        </span>
                        <span className="lv-gt">{b.ms == null ? '' : `${b.ms} ms`}</span>
                        {b.chu && <span className="lv-phu">{b.chu}</span>}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) },
        /* ⚠ TAB NÀY LÀ CHỖ `dong` CHẢY RA. Trước đây mọi lời gọi `ghi(...)` — từng
           bước bài hiệu chuẩn đặt lệnh THẬT, mỗi lần mất/nối lại kết nối, mỗi lô nến
           về — đều đổ vào một state không ai vẽ. Tức bấm Hiệu chuẩn xong nhìn màn hình
           không thấy gì, đúng thứ nhật ký sinh ra để chống. */
        { khoa: 'may', nhan: 'Máy', dem: dong.length,
          ve: () => (
            <div className="nk-cuon">
              {dong.length === 0
                ? <div className="cd-rong">Chưa có gì.</div>
                : dong.map((d, k) => <div key={k} className="lv-may">{d}</div>)}
            </div>
          ) },
        { khoa: 'nhat-ky', nhan: 'Nhật ký', dem: nhatKy.length,
          ve: () => (
            <div className="nk-boc">
              {/* KHUNG HÌNH SỐ 0 của cuộn phim, ghim trên đầu. Không trộn vào danh sách
                  lượt: đây là sự kiện của PHIÊN, không phải một lượt của sơ đồ. */}
              <div className="nk-moc">
                ▶ Khởi tạo chiến thuật thành công — <b>{boot?.ten}</b> · {boot?.symbol}
                {batDauChu && <> · bắt đầu theo dõi từ <b>{batDauChu}</b></>}
              </div>
              <Journey dong={nhatKy} jBayGio={j} chiViec={chiViec} soi={soi} />
            </div>
          ),
          nut: <label className="nk-loc">
                 <input type="checkbox" checked={chiViec}
                        onChange={e => setChiViec(e.target.checked)} />
                 chỉ dòng có việc
               </label> },
      ]} epTab={epTab?.startsWith('ket-noi') ? 'ket-noi' : undefined} />

    </div>
  )
}
