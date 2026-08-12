import { useCallback, useEffect, useRef, useState } from 'react'
import { cho_cau_noi, pyTester } from '../api'
import IconNet from '../components/Icon'
import TitleBar from '../components/TitleBar'
import { useKhungCuaSo } from '../useKhungCuaSo'
import type {
  DoanPhat, KetQuaChay, LenhVe, ProcessDoc, TrangThaiChay, XemLichSu,
} from '../types'
import BangSoLieu, { type BangCat } from './BangSoLieu'
import Chart, { type Bar, type KieuChart, type NenM1 } from './Chart'
import BangDuoi from './BangDuoi'
import NutChart from './NutChart'
import Journey from './Journey'
import ThongKe from './ThongKe'
import type { DongNk } from './Journey'
import LichSu from './LichSu'

const TF = [['M1', 1], ['M5', 5], ['M15', 15], ['M30', 30], ['H1', 60],
            ['H4', 240], ['D1', 1440]] as const
const TEN_TF: Record<number, string> =
  Object.fromEntries(TF.map(([t, p]) => [p, t]))
const TOC = [0.25, 0.5, 1, 2, 4, 8, 16] as const
const LO = 300     // số khung hình phát tiếp được trong một lô
const LUI = 720    // đệm quá khứ cho NHẬT KÝ — nến thì lấy trọn bằng `test_nen_tf`

/** CỬA SỔ STRATEGY TESTER — một TRÌNH PHÁT LẠI, không phải trình xem lịch sử.
 *
 * Vòng đời:
 *
 *     bấm ▶ ở cửa sổ vẽ
 *        → thanh tiến trình (backtest chạy trên luồng nền, ~3 s cho một năm)
 *        → phát lại từ ĐẦU: nến lớn dần, lệnh hiện ra đúng lúc, nhật ký tự chạy
 *
 * ⚠ Bản trước vẽ sẵn cả lịch sử rồi thả con trỏ vào giữa. Nhìn thì có vẻ xong, nhưng
 * nó giết đúng thứ cần xem: KHOẢNH KHẮC lệnh chờ ra đời, giá bò tới, khớp, SL dời về
 * hoà vốn, chốt. Vẽ sẵn thì không kiểm chứng được gì cả.
 *
 * Lúc phát, JS KHÔNG hỏi Python câu nào: mỗi lô `test_doan` mang đủ 300 khung hình
 * (nến · chỉ báo · vùng nén · lệnh sống · nhật ký), và lô kế được nạp trước khi dùng hết.
 */
export default function Tester() {
  useKhungCuaSo(32)

  const [doc, setDoc] = useState<ProcessDoc | null>(null)
  const [loi, setLoi] = useState('')
  const [tt, setTt] = useState<TrangThaiChay | null>(null)
  const [kq, setKq] = useState<KetQuaChay | null>(null)

  // --- con trỏ + phát ---
  const [j, setJ] = useState(0)
  const [phat, setPhat] = useState(false)
  const [toc, setToc] = useState(1)
  const [tfVe, setTfVe] = useState(5)
  const [hienBang, setHienBang] = useState(true)
  /** Đang XEM một mục lịch sử (chỉ tóm tắt, không phát lại). `null` = lần chạy hiện tại.
   *  Xem là tức thì vì Python cất sẵn bảng số và đường vốn; muốn phát lại thì phải
   *  MỞ LẠI, tức chạy lại thật. */
  const [xemLS, setXemLS] = useState<XemLichSu | null>(null)
  const [maLS, setMaLS] = useState<string | null>(null)
  /** Đếm số lần chọn một mục lịch sử — xem `epLan` ở `BangDuoi`. */
  const [lanXem, setLanXem] = useState(0)

  // --- lô đang phát ---
  const lo = useRef<DoanPhat | null>(null)
  const loSau = useRef<DoanPhat | null>(null)
  const [batDau, setBatDau] = useState(0)
  const [datNen, setDatNen] = useState<Bar[] | null>(null)
  const [themNen, setThemNen] = useState<NenM1 | null>(null)
  const [lenh, setLenh] = useState<LenhVe[]>([])
  const [dong, setDong] = useState<DongNk[]>([])
  const [khungBang, setKhungBang] = useState<BangCat | null>(null)
  const [tBayGio, setTBayGio] = useState(0)
  const delay = useRef(60)

  // ---------------- khởi động ----------------
  useEffect(() => {
    void (async () => {
      try {
        await cho_cau_noi('bootstrap_tester')
        const r = await pyTester.bootstrap_tester()
        if (!r.ok || !r.value) return setLoi(r.error ?? 'không nạp được')
        if (r.value.accent) {
          document.documentElement.style.setProperty('--accent', r.value.accent)
        }
        setDoc(r.value.doc)
        delay.current = Number((r.value.cai_dat ?? {}).delay_ms ?? 60)
        void chay()
      } catch (e) { setLoi(String(e)) }
    })()
    window.__su_kien = (ten, d) => {
      if (ten !== 'so_do_moi') return
      setDoc(d as ProcessDoc)
      void chay()
    }
  }, [])

  /* Bấm ▶ → chạy nền + hỏi tiến trình 200 ms một lần. Ba giây im lặng không phân biệt
     được với treo, nên phải THẤY nó đang chạy tới đâu. */
  const chay = async (ma?: string) => {
    setLoi(''); setPhat(false); setKq(null); setXemLS(null)
    setTt({ dang_chay: true, da: 0, tong: 0, chu: 'đang nạp nến…', xong: null, loi: null })
    // `ma` = MỞ LẠI một mục lịch sử: Python lấy sơ đồ và cài đặt từ chính mục đó, không
    // phải từ cửa sổ chính — nếu không thì "mở lại" ra một lần chạy khác hẳn.
    const r = ma ? await pyTester.test_lich_su_chay(ma) : await pyTester.test_chay({})
    if (!r.ok) { setTt(null); return setLoi(r.error ?? 'chạy hỏng') }
    for (;;) {
      await new Promise(k => setTimeout(k, 200))
      const s = await pyTester.test_trang_thai()
      if (!s.ok || !s.value) { setTt(null); return setLoi(s.error ?? 'mất kết nối') }
      setTt(s.value)
      if (s.value.dang_chay) continue
      if (s.value.loi) { setTt(null); return setLoi(s.value.loi) }
      setKq(s.value.xong!)
      await veDau(0)
      setTt(null)
      return
    }
  }

  /* Nhảy tới một vị trí — và MANG THEO QUÁ KHỨ.
   *
   * ⚠ Bản trước dựng lại chart bằng đúng MỘT cây nến (`[nenTai(r.value, 0)]`), nên bấm
   * "tới sự kiện kế tiếp" là chart trắng bốc, mọi lệnh cũ biến mất, và người xem mất
   * hẳn ngữ cảnh — không biết giá vừa từ đâu tới. Lô giờ bắt đầu SỚM HƠN con trỏ `LUI`
   * nhịp, và chart được nạp thẳng toàn bộ đoạn quá khứ đó. Cùng MỘT lời gọi, không
   * thêm vòng nào. */
  const veDau = useCallback(async (jj: number, tf = tfVe) => {
    const j0 = Math.max(0, jj - LUI)
    // Hai lời gọi, mỗi cái một việc: LÔ để phát tiếp (nhật ký · số liệu · lệnh), và
    // TOÀN BỘ NẾN để chart kéo đi đâu cũng đủ. Nhảy là chuyện hiếm nên hai vòng không sao.
    const [r, n] = await Promise.all([
      pyTester.test_doan(j0, (jj - j0) + LO),
      pyTester.test_nen_tf(TEN_TF[tf] ?? 'M5', jj),
    ])
    if (!r.ok || !r.value) return
    const L = r.value
    lo.current = L; loSau.current = null
    soDong.current = -1                 // ép dựng lại nhật ký sau khi nhảy
    const k = Math.max(0, Math.min(jj - L.j0, L.n - 1))
    setJ(L.j0 + k)
    if (n.ok && n.value) {
      const v = n.value
      setDatNen(v.t.map((t, x) => ({ time: t as never, open: v.o[x], high: v.h[x],
                                     low: v.l[x], close: v.c[x] })))
    }
    setBatDau(x => x + 1)
    setThemNen(null)
    apDung(L, k)
  }, [tfVe])

  /* Một nhịp phát: lấy khung hình kế TỪ LÔ, không hỏi Python. */
  const nhip = useCallback(() => {
    const L = lo.current
    if (!L) return false
    const k = j + 1 - L.j0
    if (k >= L.n) {
      if (!loSau.current) return false
      lo.current = loSau.current; loSau.current = null
      soDong.current = -1
      return nhip()
    }
    setJ(L.j0 + k)
    setThemNen(nenTai(L, k))
    apDung(L, k)
    // Nạp trước lô kế khi còn ~100 nhịp — để không bao giờ khựng giữa chừng.
    if (k > L.n - 100 && !loSau.current) {
      void pyTester.test_doan(L.j0 + L.n, LUI + LO).then(r => {
        if (r.ok && r.value?.n) loSau.current = r.value
      })
    }
    return true
  }, [j])

  /* Số dòng nhật ký đã hiện. Giữ ở `ref` để biết CÓ DÒNG MỚI hay không.
     Đo được: dựng lại mảng 400 dòng mỗi nhịp làm React render lại 400 phần tử và kéo
     nhịp phát từ 60 ms xuống ~190 ms — tức phát chậm gấp ba lần cái đã đặt. Nhật ký chỉ
     đổi khi có lượt mới, mà lượt mới thì 5 nhịp mới có một lần. */
  const soDong = useRef(0)

  const apDung = (L: DoanPhat, k: number) => {
    setLenh(L.lenh)
    setTBayGio(L.t[Math.max(0, Math.min(k, L.n - 1))])
    setKhungBang(dungBang(L, k))
    const jj = L.j0 + k
    let n = 0
    while (n < L.nhat_ky.length && L.nhat_ky[n].j <= jj) n++
    if (n !== soDong.current) {
      soDong.current = n
      setDong(L.nhat_ky.slice(Math.max(0, n - 400), n))
    }
  }

  useEffect(() => {
    if (!phat || !kq) return
    const id = window.setTimeout(() => { if (!nhip()) setPhat(false) },
                                 Math.max(4, delay.current / toc))
    return () => clearTimeout(id)
  }, [phat, j, toc, kq, nhip])

  /* Đổi khung hiển thị → nạp lại TOÀN BỘ nến ở khung mới. Không đụng kết quả chạy. */
  const doiTf = (p: number) => { setTfVe(p); setPhat(false); void veDau(j, p) }

  /* Nhảy tới SỰ KIỆN kế tiếp — không ai ngồi xem hết 71.000 nến buồn tẻ để đợi một lệnh.
   *
   * ⚠ Con trỏ dừng ĐÚNG NGAY sự kiện, không phải trước nó. Bản trước lùi 40 nhịp cho
   * "dễ xem nó xảy ra", nhưng thế thì lần bấm sau lại tìm thấy chính sự kiện đó (nó vẫn
   * ở phía trước con trỏ) và nhảy về đúng chỗ cũ — bấm ba lần vẫn đứng yên.
   * Dừng đúng tại sự kiện thì mũi tên/vạch hiện ngay ở mép phải, quá khứ vẫn còn nguyên
   * nhờ đệm `LUI`, và lần bấm sau đi tiếp được. Muốn xem lại khoảnh khắc thì ◀ vài nhịp
   * rồi ▶. */
  const toiSuKien = async () => {
    const L = lo.current
    if (!L) return
    setPhat(false)
    const trong = L.nhat_ky.find(x => x.j > j && x.co_viec)
    if (trong) return veDau(trong.j)
    const r = await pyTester.test_luot_ke(j)
    if (r.ok && r.value && r.value.j >= 0) await veDau(r.value.j)
  }

  /* LÙI về sự kiện trước — bản soi gương của nút trên. Trước đây chỗ này là "về đầu",
   * nhưng về đầu hẳn thì một lần bấm vứt sạch chỗ đang xem, mà `↻ Chạy lại` vốn đã
   * làm đúng việc đó rồi.
   *
   * KHÔNG có đường tắt "tìm trong lô" như chiều tới. Lô chỉ mang theo `LUI` = 720 nhịp
   * quá khứ, mà sự kiện trước thường xa hơn thế, nên đường tắt hầu như không bao giờ
   * trúng — thêm một nhánh chỉ để tiết kiệm một lời gọi 1 ms là lỗ.
   *
   * Điều kiện `x.j < j` phải NGHIÊM NGẶT, và dừng ĐÚNG NGAY sự kiện — cùng cái bẫy mà
   * nút tới đã dính rồi sửa, chỉ ngược chiều: nới ra là bấm ba lần vẫn đứng yên.
   * Hết sự kiện thì mới về nến 0. */
  const luiSuKien = async () => {
    setPhat(false)
    const r = await pyTester.test_luot_truoc(j)
    if (!r.ok || !r.value) return
    await veDau(r.value.j >= 0 ? r.value.j : 0)
  }

  /* Nhảy tới cuối lượt chạy. Dùng `test_tim_moc` chứ không thêm hàm mới: mốc cuối đã
     nằm sẵn trong `kq`, và hàm đó vốn đã kẹp chỉ số vào cây nến CÓ THẬT cuối cùng. */
  const veCuoi = async () => {
    if (!kq) return
    setPhat(false)
    const r = await pyTester.test_tim_moc(kq.t_cuoi)
    if (r.ok && r.value) await veDau(r.value.j)
  }

  /** Giá trị ô "nhảy tới mốc". PHẢI là state, không được để ô tự giữ.
   *
   * ⚠ LỖI ĐÃ SỬA: để `defaultValue` (uncontrolled) thì gõ ngày → nhảy → gõ tiếp giờ là
   * ô **im lặng hẳn**, `onChange` không bắn nữa, con trỏ kẹt ở cú nhảy dở dang trong khi
   * ô hiện một mốc khác. Tái hiện chắc chắn: gõ `07/04/2025`, đợi cú nhảy chạy xong, gõ
   * tiếp `03:00` — đồng hồ đứng ở `07-06 22:05` còn ô ghi `03:00 PM`. Nguyên nhân: cú
   * nhảy gọi `veDau` → dựng lại chart + đặt 6 state, và qua lần re-render lớn đó bộ theo
   * dõi giá trị của React lệch pha với DOM. Ô có state riêng thì React luôn nắm giá trị,
   * không còn chỗ cho lệch. */
  const [chiViec, setChiViec] = useState(false)
  const [kieu, setKieu] = useState<KieuChart>('nen')
  const [mauThuong, setMauThuong] = useState(false)
  const [hienLenh, setHienLenh] = useState(true)
  const [veNay, setVeNay] = useState(0)
  const [moc, setMoc] = useState('')
  useEffect(() => { if (kq) setMoc(chuoiMoc(kq.t_dau)) }, [kq])

  /** Cú nhảy mốc thứ mấy — để bỏ qua kết quả của cú đã cũ. */
  const lanMoc = useRef(0)
  const hoanMoc = useRef<number | undefined>(undefined)

  /* Nhảy tới một MỐC THỜI GIAN cụ thể — soi đúng đoạn đang nghi mà không phải tua từ đầu.
   *
   * ⚠ HAI CÁI BẪY, cả hai đều do ô `datetime-local` bắn ra một giá trị HỢP LỆ sau MỖI
   * đoạn gõ (gõ xong tháng đã là một mốc, gõ xong ngày lại một mốc nữa):
   *
   * 1. Không hoãn thì một lần gõ = 5-6 cú nhảy chồng nhau. Đo được: gõ `07/04/2025 03:00
   *    PM` mà con trỏ dừng ở `07-06 22:05` — vì mốc DỞ DANG `07/04 11:05 PM` rơi vào tối
   *    thứ Sáu (chợ đã đóng) nên nó bị đẩy sang phiên mở cửa Chủ nhật, và nó về đích SAU
   *    CÙNG. Chart nói một đằng, nhật ký nói một nẻo.
   * 2. Nên chỉ hoãn thôi vẫn chưa đủ: hai cú nhảy vẫn có thể về không đúng thứ tự gửi.
   *    `lanMoc` chốt lại — kết quả nào không phải của cú mới nhất thì vứt.
   *
   * Lọc theo khoảng dữ liệu bỏ luôn mấy bước vô nghĩa (năm mới gõ "2" đã là năm 0002),
   * nên không cần bắt người dùng bấm Enter mới chịu nhảy. */
  const toiMoc = (v: string, ngay = false) => {
    const t = tuChuoiMoc(v)
    if (t === null || !kq || t < kq.t_dau - 86400 || t > kq.t_cuoi + 86400) return
    window.clearTimeout(hoanMoc.current)
    hoanMoc.current = window.setTimeout(async () => {
      const lan = ++lanMoc.current
      setPhat(false)
      const r = await pyTester.test_tim_moc(t)
      if (lan !== lanMoc.current || !r.ok || !r.value) return
      await veDau(r.value.j)
    }, ngay ? 0 : 350)
  }

  const nut = (icon: string, ten: string, on: () => void, bat = false, tat = false) => (
    <button className={'tb-nut' + (bat ? ' bat' : '')} title={ten}
            disabled={tat} onClick={on}><IconNet name={icon} size={15} /></button>
  )

  return (
    <div className="khung">
      <TitleBar tieuDe={doc ? `${doc.name} — Strategy Tester` : 'Strategy Tester'}
                menus={[]}
                them={<LichSu dangXem={maLS}
                              onXem={async ma => {
                                const r = await pyTester.test_lich_su_xem(ma)
                                if (r.ok && r.value) {
                                  setXemLS(r.value); setMaLS(ma)
                                  // Mỗi lần chọn là một lần ép MỚI — xem `epLan`.
                                  setLanXem(x => x + 1)
                                }
                              }}
                              onMoLai={ma => { setMaLS(ma); void chay(ma) }} />} />

      <div className="tb">
        {/* `() => chay()` chứ KHÔNG phải `chay`: truyền thẳng thì React đưa cả đối tượng
            sự kiện vào tham số `ma`, và nút này hoá ra đi mở lại một mục lịch sử. */}
        <button className="nut chinh" onClick={() => void chay()}
                disabled={!!tt?.dang_chay}>↻ Chạy lại</button>
        {/* Đứng cạnh "Chạy lại" chứ không nhét vào cụm phát lại: hai nút này nói về CẢ
            LƯỢT CHẠY (đưa về đầu · đưa về cuối), còn năm nút kia đi từng bước quanh chỗ
            đang đứng. Trộn vào nhau thì cụm phát lại có hai nút nhảy cóc nằm lẫn giữa
            các nút đi bộ. */}
        <button className="nut" onClick={() => void veCuoi()}
                disabled={!kq} title="Nhảy tới cuối lượt chạy">⇥ Về cuối</button>
        <span className="tb-ngan" />
        {nut('dau', 'Về SỰ KIỆN trước', () => void luiSuKien(), false, !kq)}
        {nut('undo', 'Lùi 1 nến',
             () => { setPhat(false); void veDau(Math.max(0, j - 1)) }, false, !kq)}
        <button className="tb-nut rong" disabled={!kq} onClick={() => setPhat(v => !v)}
                title={phat ? 'Dừng' : 'Phát — nến hình thành từng cây như live'}>
          {phat ? '❚❚' : '▶'}
        </button>
        {nut('redo', 'Tới 1 nến', () => { setPhat(false); nhip() }, false, !kq)}
        {nut('cuoi', 'Tới SỰ KIỆN kế tiếp', () => void toiSuKien(), false, !kq)}
        <select className="o nho" value={toc} onChange={e => setToc(+e.target.value)}
                title="Tốc độ phát">
          {TOC.map(x => <option key={x} value={x}>{x}×</option>)}
        </select>
        <span className="tb-ngan" />
        <NutChart tf={tfVe} dsTf={TF} datTf={doiTf}
                  kieu={kieu} datKieu={setKieu}
                  mauThuong={mauThuong} datMau={setMauThuong}
                  hienLenh={hienLenh} datHienLenh={setHienLenh}
                  veHienTai={() => setVeNay(x => x + 1)} />
        <span className="tb-ngan" />
        {/* Ô nhảy tới mốc. TÁCH khỏi đồng hồ bên phải chứ không gộp làm một: đồng hồ đổi
            8 lần/giây lúc phát, mà một ô nhập tự đổi giá trị dưới tay người đang gõ thì
            không gõ nổi. Bấm vào ô thì nó nạp mốc hiện tại — vẫn "đi tiếp từ chỗ đang
            đứng" mà không phải ô điều khiển chung. */}
        <input type="datetime-local" className="o tb-moc" step={60} disabled={!kq}
               title="Nhảy tới mốc thời gian"
               min={kq ? chuoiMoc(kq.t_dau) : undefined}
               max={kq ? chuoiMoc(kq.t_cuoi) : undefined}
               value={moc}
               onFocus={() => {
                 const L = lo.current
                 if (L) setMoc(chuoiMoc(nenTai(L, j - L.j0).t))
               }}
               onChange={e => { setMoc(e.target.value); toiMoc(e.target.value) }}
               onKeyDown={e => { if (e.key === 'Enter') toiMoc(e.currentTarget.value, true) }} />
        <span className="tb-day" />
        {lo.current && <span className="tb-gio">{gio(nenTai(lo.current, j - lo.current.j0).t)}</span>}
        {nut('copy', 'Bảng số liệu', () => setHienBang(v => !v), hienBang)}
      </div>

      {tt?.dang_chay && (
        <div className="tt-nap">
          <div className="tt-nap-chu">{tt.chu}</div>
          <div className="tt-nap-thanh">
            <div style={{ width: tt.tong ? `${tt.da / tt.tong * 100}%` : '8%' }} />
          </div>
        </div>
      )}
      {loi && <div className="tt-loi">{loi}</div>}
      {/* Dải tóm tắt (số lệnh · T/B · tổng R · vốn · DD · nến mơ hồ) tạm BỎ theo yêu cầu —
          sẽ đặt lại chỗ khác sau. Số liệu vẫn nằm nguyên ở `kq.thong_ke`, dựng lại chỉ
          là một khối JSX; không cần đụng tới backend. */}

      <div className="tt-giua">
        <Chart tfPhut={tfVe} digits={kq?.digits ?? 2} lenh={lenh} tBayGio={tBayGio}
               batDau={batDau} dat={datNen} them={themNen}
               kieu={kieu} mauThuong={mauThuong} hienLenh={hienLenh}
               veHienTai={veNay} />
        {hienBang && <BangSoLieu k={khungBang} digits={kq?.digits ?? 2} />}
      </div>

      {/* Nhật ký TỰ giữ chuyện cụp/mở và chiều cao của nó — giống bảng dưới của cửa sổ
          chính. Nút gập nằm ngay trên hàng tab của chính nó chứ không phải ở góc thanh
          công cụ: tay đang ở đâu thì nút ở đó. */}
      {kq && (
        <BangDuoi epTab={xemLS ? 'thong-ke' : undefined} epLan={lanXem} tabs={[
          { khoa: 'nhat-ky', nhan: 'Nhật ký', dem: dong.length,
            ve: () => <Journey dong={dong} jBayGio={j} nhay={async i => {
                                 setPhat(false)
                                 const r = await pyTester.test_luot(i)
                                 if (r.ok && r.value) await veDau(Math.max(0, r.value.j - 40))
                               }}
                               soi={i => void pyTester.test_soi_luot(i)}
                               chiViec={chiViec} />,
            nut: <>
              <label className="nk-loc">
                <input type="checkbox" checked={chiViec}
                       onChange={e => setChiViec(e.target.checked)} />
                chỉ dòng có việc
              </label>
              <button className="nut-nho" onClick={async () => {
                        const r = await pyTester.test_ghi_nhat_ky()
                        if (r.ok && r.value) alert(`Đã ghi:
${r.value.duong_dan}`)
                      }}
                      title="Ghi TOÀN BỘ nhật ký ra .jsonl">Ghi ra file</button>
            </> },
          { khoa: 'thong-ke', nhan: 'Thống kê',
            ve: () => <ThongKe nguon={xemLS} thoiXem={() => { setXemLS(null); setMaLS(null) }} /> },
        ]} />
      )}
    </div>
  )
}

function nenTai(L: DoanPhat, k: number): NenM1 {
  const i = Math.max(0, Math.min(k, L.n - 1))
  return { t: L.t[i], o: L.o[i], h: L.h[i], l: L.l[i], c: L.c[i] }
}

/** Bảng số liệu tại khung hình thứ k của lô. Chỉ CẮT LÁT, không tính gì —
 *  mọi con số đã do Python tính lúc chạy. */
/** Cắt bảng số liệu tại khung `k`. EXPORT để cửa sổ Live dùng CHUNG —
 *  copy sang bản thứ hai là hai bên sẽ trôi xa nhau. */
export function dungBang(L: DoanPhat, k: number): BangCat {
  return {
    nhom: L.bang.map(g => ({
      nhom: g.nhom,
      dong: g.dong.map(d => ({ ten: d.ten, phu: d.phu, gia_tri: d.gia_tri[k] ?? null })),
    })),
    lenh: L.lenh_song[k] ?? [],
  }
}

function gio(t: number) {
  const d = new Date(t * 1000)
  const s = (n: number) => String(n).padStart(2, '0')
  return `${d.getUTCFullYear()}-${s(d.getUTCMonth() + 1)}-${s(d.getUTCDate())} `
       + `${s(d.getUTCHours())}:${s(d.getUTCMinutes())}`
}

/** unix (giây) → chuỗi của ô `datetime-local`.
 *
 * Dựng tay theo giờ UTC, KHÔNG dùng `toISOString`/`Date` tự định dạng: nến của MT5 là
 * giờ sàn và cả app hiển thị nguyên như thế, còn `Date` thì cộng lệch múi giờ của máy —
 * ô nhập sẽ lệch vài tiếng so với chính cái đồng hồ ngay cạnh nó. */
function chuoiMoc(t: number) {
  return gio(t).replace(' ', 'T')
}

/** Ngược lại — đọc chuỗi ô nhập NHƯ GIỜ UTC. `null` = chưa thành một mốc đọc được. */
function tuChuoiMoc(v: string) {
  const m = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/.exec(v)
  return m ? Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]) / 1000 : null
}
