import { chu, datNgon, useNgon } from '../i18n'
import { useCallback, useEffect, useRef, useState } from 'react'
import { cho_cau_noi, pyTester } from '../api'
import IconNet from '../components/Icon'
import TitleBar from '../components/TitleBar'
import { useKhungCuaSo } from '../useKhungCuaSo'
import type {
  DoanPhat, KetQuaChay, LenhVe, ProcessDoc, TrangThaiChay, XemLichSu,
} from '../types'
import BangSoLieu, { type BangCat } from './BangSoLieu'
import Chart, { type Bar, type HopZone, type KieuChart, type NenM1 } from './Chart'
import BangDuoi from './BangDuoi'
import NutChart from './NutChart'
import Journey from './Journey'
import ThongKe from './ThongKe'
import MoXe from './MoXe'
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
  useNgon()   // đổi ngôn ngữ → vẽ lại (xem `i18n.ts`)
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
        if (!r.ok || !r.value) return setLoi(r.error ?? chu('không nạp được'))
        datNgon((r.value as { ngon_ngu?: string }).ngon_ngu === 'en' ? 'en' : 'vi')
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
    setTt({ dang_chay: true, da: 0, tong: 0, chu: chu('đang nạp nến…'), xong: null, loi: null })
    // `ma` = MỞ LẠI một mục lịch sử: Python lấy sơ đồ và cài đặt từ chính mục đó, không
    // phải từ cửa sổ chính — nếu không thì "mở lại" ra một lần chạy khác hẳn.
    const r = ma ? await pyTester.test_lich_su_chay(ma) : await pyTester.test_chay({})
    if (!r.ok) { setTt(null); return setLoi(r.error ?? chu('chạy hỏng')) }
    for (;;) {
      await new Promise(k => setTimeout(k, 200))
      const s = await pyTester.test_trang_thai()
      if (!s.ok || !s.value) { setTt(null); return setLoi(s.error ?? chu('mất kết nối')) }
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
      setZone(v.zone ?? [])
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
    const t = L.t[Math.max(0, Math.min(k, L.n - 1))]
    setTBayGio(t)
    /* ZONE lớn dần theo con trỏ. Lấy bản ghi MỚI NHẤT có `t_nến ≤ con trỏ` cho mỗi
       zone — nên nó nở ra từng khung lúc phát, và không bao giờ lộ tương lai dù lô
       mang sẵn cả những nến phía trước. Chỉ đặt state khi thật sự đổi: `apDung` chạy
       mỗi khung hình, dựng mảng mới mỗi lần là ép Chart vẽ lại vô ích. */
    if (L.zone?.length) {
      setZone(cu => {
        const m = new Map(cu.map(z => [z[0], z]))
        let doi = false
        for (const z of L.zone!) {
          if (z[1] > t) continue
          const c = m.get(z[0])
          if (!c || c[1] < z[1]) { m.set(z[0], z); doi = true }
        }
        return doi ? [...m.values()].sort((x, y) => x[0] - y[0]) : cu
      })
    }
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

  /* MỘT hàm cho MỘT việc, nút và phím tắt cùng gọi — luật §12.22, không đẻ hành động
   * thứ hai cho một lối vào mới.
   *
   * ⚠ TIẾN và LÙI KHÔNG ĐỐI XỨNG VỀ GIÁ, dù trên thanh công cụ chúng là hai nút giống
   * nhau. `nhip()` đọc khung hình kế TỪ LÔ đã nạp — không hỏi Python câu nào. Còn lùi
   * thì phải `veDau()`, tức HAI lời gọi cầu nối (`test_doan` + `test_nen_tf`) và dựng
   * lại chart. Giữ phím ← ở tốc độ lặp của Windows (~30 lần/giây) là ~60 lời gọi mỗi
   * giây qua một cầu nối ĐỒNG BỘ, mã hoá payload hai lần (§12.16) — chắc chắn nghẽn.
   *
   * Nên lùi có KHOÁ: đang lùi thì bỏ qua nhịp lặp mới. Giữ phím vẫn lùi liên tục, chỉ
   * là theo nhịp cầu nối trả lời được, chứ không phải nhịp bàn phím bắn ra. Bỏ nhịp
   * thừa đúng hơn xếp hàng chúng lại — xếp hàng thì thả tay rồi màn hình còn chạy tiếp. */
  const dangLui = useRef(false)

  const lui = useCallback(async () => {
    if (!kq || dangLui.current) return
    dangLui.current = true
    setPhat(false)
    try { await veDau(Math.max(0, j - 1)) } finally { dangLui.current = false }
  }, [kq, j, veDau])

  const tien = useCallback(() => {
    if (!kq) return
    setPhat(false)
    nhip()
  }, [kq, nhip])

  /* SPACE = phát / dừng. Phím quen của mọi trình phát, và ở đây tay đang cầm chuột để
   * rê crosshair nên với sang ▶ là mất chỗ đang chỉ.
   *
   * ⚠ BA CHỖ PHẢI NÉ, không né thì phím này phá nhiều hơn nó giúp:
   *
   * 1. Ô `datetime-local` (nhảy tới mốc) và ô tick "chỉ dòng có việc" — Space trong ô
   *    nhập là ký tự / là bật tắt, cướp nó đi là ô hoá hỏng. Bắt theo THẺ đang có tiêu
   *    điểm, không theo danh sách id: thêm một ô mới sau này là tự động được bảo vệ.
   * 2. Nút đang có tiêu điểm — trình duyệt vốn đã bắn `click` khi nhấn Space trên
   *    `<button>`. Vừa bấm ▶ bằng chuột thì nút GIỮ tiêu điểm, nên Space sau đó sẽ
   *    toggle HAI lần và trông như phím chết. Để nguyên hành vi mặc định của nút, ta
   *    không xen vào.
   * 3. `preventDefault` cho phần còn lại: Space mặc định của trang là CUỘN XUỐNG, mà
   *    bảng nhật ký thì cuộn được — không chặn là mỗi lần dừng phát màn hình lại nhảy.
   */
  useEffect(() => {
    const nghe = (ev: KeyboardEvent) => {
      const la = ev.code === 'Space' || ev.key === ' ' ? 'phat'
               : ev.key === 'ArrowRight' ? 'tien'
               : ev.key === 'ArrowLeft' ? 'lui' : null
      if (!la) return
      const el = document.activeElement as HTMLElement | null
      const the = el?.tagName
      if (the === 'INPUT' || the === 'TEXTAREA' || the === 'SELECT'
          || the === 'BUTTON' || el?.isContentEditable) return
      // Chưa chạy xong thì không có gì để phát — đúng như nút ▶ đang `disabled`.
      // Phím tắt phải chết ở đúng chỗ cái nút chết, không thì nó là một cửa sau.
      if (!kq) return
      // ⚠ GIỮ PHÍM: trình duyệt TỰ bắn lại `keydown` (`ev.repeat`), nên "giữ = bấm liên
      // tiếp" có sẵn, không cần hẹn giờ nào. Nhưng chỉ đúng với ←/→.
      // Space thì phải BỎ nhịp lặp: giữ Space mà toggle ~30 lần/giây thì phát/dừng
      // nhấp nháy và thả tay ra không đoán nổi nó đang ở trạng thái nào.
      if (ev.repeat && la === 'phat') return
      ev.preventDefault()
      if (la === 'phat') setPhat(v => !v)
      else if (la === 'tien') tien()
      else void lui()
    }
    window.addEventListener('keydown', nghe)
    return () => window.removeEventListener('keydown', nghe)
  }, [kq, tien, lui])

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
  const [hienZone, setHienZone] = useState(true)
  /** HỘP ZONE làm phông nền — về cùng gói với nến, đã cắt ở con trỏ. */
  const [zone, setZone] = useState<HopZone[]>([])
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
                disabled={!!tt?.dang_chay}>{chu('↻ Chạy lại')}</button>
        {/* Đứng cạnh "Chạy lại" chứ không nhét vào cụm phát lại: hai nút này nói về CẢ
            LƯỢT CHẠY (đưa về đầu · đưa về cuối), còn năm nút kia đi từng bước quanh chỗ
            đang đứng. Trộn vào nhau thì cụm phát lại có hai nút nhảy cóc nằm lẫn giữa
            các nút đi bộ. */}
        <button className="nut" onClick={() => void veCuoi()}
                disabled={!kq} title={chu("Nhảy tới cuối lượt chạy")}>{chu('⇥ Về cuối')}</button>
        <span className="tb-ngan" />
        {nut('dau', chu('Về SỰ KIỆN trước'), () => void luiSuKien(), false, !kq)}
        {nut('undo', chu('Lùi 1 nến  (←)'), () => void lui(), false, !kq)}
        <button className="tb-nut rong" disabled={!kq} onClick={() => setPhat(v => !v)}
                title={(phat ? chu('Dừng') : chu('Phát — nến hình thành từng cây như live'))
                       + '  (Space)'}>
          {phat ? '❚❚' : '▶'}
        </button>
        {nut('redo', chu('Tới 1 nến  (→)'), tien, false, !kq)}
        {nut('cuoi', chu('Tới SỰ KIỆN kế tiếp'), () => void toiSuKien(), false, !kq)}
        <select className="o nho" value={toc} onChange={e => setToc(+e.target.value)}
                title={chu("Tốc độ phát")}>
          {TOC.map(x => <option key={x} value={x}>{x}×</option>)}
        </select>
        <span className="tb-ngan" />
        <NutChart tf={tfVe} dsTf={TF} datTf={doiTf}
                  kieu={kieu} datKieu={setKieu}
                  mauThuong={mauThuong} datMau={setMauThuong}
                  hienLenh={hienLenh} datHienLenh={setHienLenh}
                  hienZone={hienZone} datHienZone={setHienZone}
                  veHienTai={() => setVeNay(x => x + 1)} />
        <span className="tb-ngan" />
        {/* Ô nhảy tới mốc. TÁCH khỏi đồng hồ bên phải chứ không gộp làm một: đồng hồ đổi
            8 lần/giây lúc phát, mà một ô nhập tự đổi giá trị dưới tay người đang gõ thì
            không gõ nổi. Bấm vào ô thì nó nạp mốc hiện tại — vẫn "đi tiếp từ chỗ đang
            đứng" mà không phải ô điều khiển chung. */}
        <input type="datetime-local" className="o tb-moc" step={60} disabled={!kq}
               title={chu("Nhảy tới mốc thời gian")}
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
        {nut('copy', chu('Bảng số liệu'), () => setHienBang(v => !v), hienBang)}
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
               zone={zone} hienZone={hienZone}
               veHienTai={veNay} />
        {hienBang && <BangSoLieu k={khungBang} digits={kq?.digits ?? 2} />}
      </div>

      {/* Nhật ký TỰ giữ chuyện cụp/mở và chiều cao của nó — giống bảng dưới của cửa sổ
          chính. Nút gập nằm ngay trên hàng tab của chính nó chứ không phải ở góc thanh
          công cụ: tay đang ở đâu thì nút ở đó. */}
      {kq && (
        <BangDuoi epTab={xemLS ? 'thong-ke' : undefined} epLan={lanXem} tabs={[
          { khoa: 'nhat-ky', nhan: chu('Nhật ký'), dem: dong.length,
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
                      title={chu("Ghi TOÀN BỘ nhật ký ra .jsonl")}>Ghi ra file</button>
            </> },
          { khoa: 'thong-ke', nhan: chu('Thống kê'),
            ve: () => <ThongKe nguon={xemLS} thoiXem={() => { setXemLS(null); setMaLS(null) }} /> },
          // ⭐ MỔ XẺ — chỗ MỘT con số của cả sơ đồ tách thành một con số cho MỖI khối.
          // Xem docstring `MoXe.tsx`.
          { khoa: 'mo-xe', nhan: chu('Mổ xẻ'),
            ve: () => <MoXe sanSang={!!kq}
                            nap={pyTester.test_phan_bo}
                            thuBo={pyTester.test_thu_bo} /> },
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
