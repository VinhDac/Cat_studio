import { useCallback, useEffect, useRef, useState } from 'react'
import { cho_cau_noi, pyRL } from '../api'
import { useKhungCuaSo } from '../useKhungCuaSo'
import TitleBar from '../components/TitleBar'
import BangDuoi, { type TabDuoi } from '../tester/BangDuoi'
import MoXe from '../tester/MoXe'
import BangDieuKhien from './BangDieuKhien'
import CuaSoCaiDat, { buocCua, coKhoaCua, kyCham, nhanCua, TEN_BUOC, tenKyCua,
                      type DieuKhien } from './CaiDatLuot'
import { IR, Nhom, Nut, ONhap } from './RibbonRL'
import type { DatRL, DauBang, KetQuaKhoa, KhoNen, RLBoot,
              TrangThaiLuot } from '../types'

/** CỬA SỔ RL — bàn điều khiển máy tìm chiến lược.
 *
 *     core.md §18.6, §18.9
 *
 * Bố cục học thẳng cửa sổ vẽ, ba tầng:
 *
 *     RIBBON     ▶ Chạy · ■ Dừng │ số sơ đồ · hạt giống │ ⚙ Cài đặt
 *                (mọi đồ đặt-một-lần nằm trong cửa sổ ⚙ — xem `CaiDatLuot`)
 *     DASHBOARD  tiến độ + mấy ô nhìn ("tôi không muốn chạy mù")
 *     BẢNG DƯỚI  Đầu bảng · Đoạn khoá · Cái chung · Vì sao rớt · Lượt khác — cụp được
 *
 * Bốn việc của §18.6.2 nằm đúng ba tầng đó: **ĐẶT** ở ribbon · **CHẠY** ở ribbon ·
 * **NHÌN** ở dashboard · **MỞ** ở bảng dưới.
 *
 * ⚠ **Máy tìm KHÔNG sống trong cửa sổ này.** Sổ lượt chạy nằm ở `luot_tim` bên Python
 * (mức module), nên đóng cửa sổ rồi mở lại là thấy lượt cũ vẫn đang chạy. Vì thế
 * component này KHÔNG giữ trạng thái nào của lượt chạy — nó chỉ giữ MÃ và hỏi lại.
 *
 * ⚠ Và mọi con số trên màn hình đều là số TRAIN (§18.6.3). Dải nhắc ở bảng đầu bảng
 * không phải trang trí: một bảng số đẹp đẽ không được trông như kết luận.
 */

/** Nhịp hỏi tiến độ. Một lượt chấm mất vài giây nên 500 ms là quá đủ, mà cầu nối
 *  pywebview thì ĐỒNG BỘ — hỏi dày là tự làm chậm chính lượt đang chạy. */
const NHIP_MS = 500

/** Gõ xong ngần này mới ghi cài đặt xuống đĩa — xem `datD`. Đủ ngắn để không ai kịp
 *  tắt app giữa chừng, đủ dài để một câu gõ liền mạch chỉ tốn MỘT lượt ghi. */
const HOAN_GHI_MS = 400

const so = (x: number | null | undefined, n = 2) =>
  x === null || x === undefined || Number.isNaN(x) ? '—' : x.toFixed(n)
const pt = (x: number | null | undefined, n = 2) =>
  x === null || x === undefined ? '—' : `${x >= 0 ? '+' : ''}${x.toFixed(n)}%`

function lau(g: number): string {
  g = Math.max(0, Math.round(g))
  if (g < 60) return `${g}s`
  if (g < 3600) return `${Math.floor(g / 60)}m ${g % 60}s`
  return `${Math.floor(g / 3600)}h ${Math.floor((g % 3600) / 60)}m`
}
const khoang = (t0: number, t1: number | null) =>
  lau((t1 ?? Date.now() / 1000) - t0)

/** Nhãn ngắn của một cửa sổ cuốn tới: `Q1/25` · `03/25` · `H2/25`.
 *
 * Ngày đầy đủ thì một dải 18 cửa sổ không nhét vừa một dòng, mà thứ cần đọc ở dải ấy
 * là HÌNH DẠNG — đỏ ở đâu, xanh ở đâu — chứ không phải ngày chính xác. Ngày đầy đủ
 * vẫn còn, nằm trong tooltip. */
function nhanKy(tu: string, buoc: string): string {
  const [y, m] = tu.split('-')
  const nam = y.slice(2)
  if (buoc === 'thang') return `${m}/${nam}`
  if (buoc === 'nua_nam') return `H${+m <= 6 ? 1 : 2}/${nam}`
  return `Q${Math.floor((+m - 1) / 3) + 1}/${nam}`
}

/** Tên cửa cho người đọc. Khoá là tên trong `cham_diem.CUA_MAC_DINH`. */
const TEN_CUA: Record<string, string> = {
  tuan_co_lenh: 'kỳ có lệnh',
  so_lenh_toi_thieu: 'số lệnh tối thiểu',
  sut_von_toi_da: 'sụt vốn tối đa',
  te_nhat_toi_da: 'kỳ tệ nhất',
  dao_dong_toi_da: 'dao động tối đa',
  lai_toi_thieu: 'lãi tối thiểu',
  deu_toi_thieu: 'đều qua thời gian',
  diem_toi_thieu: 'điểm tối thiểu',
}
/** Nhãn năm thùng của "thiếu bao xa" — khớp `tim_kiem.MEP_THIEU`. */
const NHAN_THIEU = ['suýt qua (<10%)', 'thiếu 10–25%', 'thiếu 25–50%',
                    'thiếu 50–75%', 'thiếu ≥75%']

/** Có dương ở QUÁ NỬA cửa sổ không — cùng luật với cửa `deu_toi_thieu` (§18.5f). */
const deu = (d: DauBang) =>
  !!d.so_cua_so && (d.cua_so_duong ?? 0) * 2 > d.so_cua_so

export default function RL() {
  useKhungCuaSo()
  const [boot, setBoot] = useState<RLBoot | null>(null)
  const [loi, setLoi] = useState('')
  /** MÃ lượt đang xem. Không giữ trạng thái lượt ở đây — xem chú thích đầu file. */
  const [ma, setMa] = useState<string | null>(null)
  const [tt, setTt] = useState<TrangThaiLuot | null>(null)
  const [ds, setDs] = useState<TrangThaiLuot[]>([])

  // --- tầng CHỌN (§18.6.1) ---
  const [tat, setTat] = useState<Set<string>>(new Set())
  const [tran, setTran] = useState<Record<string, number>>({})
  const [cua, setCua] = useState<Record<string, number | string | null>>({})
  const [soLuot, setSoLuot] = useState(200)
  const [hat, setHat] = useState(2026)
  const [giu, setGiu] = useState(20)
  const [gioToiDa, setGioToiDa] = useState<number | null>(null)
  const [phangToiDa, setPhangToiDa] = useState<number | null>(null)
  /** Mấy tiến trình chấm song song. `0` = tự chọn (chừa 2 nhân cho giao diện). */
  const [soNhan, setSoNhan] = useState(0)
  /** Cài đặt RIÊNG của RL — train · KHOÁ · chi phí. Không dùng chung với Tester. */
  const [dat, setDat] = useState<Record<string, unknown>>({})
  const [khoNen, setKhoNen] = useState<KhoNen | null>(null)
  const [khoa, setKhoa] = useState<KetQuaKhoa | null>(null)

  /** Mục đang mở của cửa sổ ⚙, `null` là đang đóng. */
  const [moCaiDat, setMoCaiDat] = useState<string | null>(null)
  /** Hạng sơ đồ đang SOI ở tab Mổ xẻ. `null` là chưa chọn cái nào. */
  const [soi, setSoi] = useState<number | null>(null)

  const nhip = useRef<number | null>(null)

  useEffect(() => {
    cho_cau_noi('rl_boot')
      .then(() => pyRL.rl_boot())
      .then(r => {
        if (!r.ok || !r.value) return setLoi(r.error || 'Không nạp được cửa sổ RL.')
        setBoot(r.value)
        setTran({ ...r.value.tran })
        setCua({ ...r.value.cua })
        datRef.current = { ...r.value.cai_dat }
        setDat(datRef.current)
        setKhoNen(r.value.kho_nen)
        setDs(r.value.luot)
        // Có lượt đang chạy từ trước (cửa sổ vừa mở lại) → bám ngay vào nó. Đây chính
        // là chỗ chứng minh máy tìm không sống trong cửa sổ.
        const dang = r.value.luot.find(x => x.dang_chay)
        if (dang) setMa(dang.ma)
      })
      .catch(e => setLoi(String(e)))
  }, [])

  // --- NHÌN: hỏi tiến độ ---
  useEffect(() => {
    if (!ma) return
    let song = true
    const hoi = async () => {
      const r = await pyRL.rl_trang_thai(ma)
      if (!song) return
      if (r.ok && r.value) {
        setTt(r.value)
        if (!r.value.dang_chay) {
          pyRL.rl_danh_sach().then(x => { if (song && x.ok && x.value) setDs(x.value.ds) })
          return                        // xong thì thôi hỏi — không quay vô ích
        }
      }
      nhip.current = window.setTimeout(hoi, NHIP_MS)
    }
    hoi()
    return () => {
      song = false
      if (nhip.current) window.clearTimeout(nhip.current)
    }
  }, [ma])

  const ky = kyCham(cua)
  const tenKy = tenKyCua(cua)
  const coKhoa = coKhoaCua(dat)
  const buoc = buocCua(dat)

  /** Sửa MỘT ô cài đặt RL. Không có nút Lưu, và không nên có: một bàn điều khiển bắt
   *  bấm Lưu là một bàn điều khiển quên mất thứ vừa gõ.
   *
   *  ⚠ Nhưng GHI thì phải HOÃN. `rl_luu_dat` đi qua cầu nối pywebview **đồng bộ**, rồi
   *  `ghi_json_nguyen_tu` ghi file tạm + `fsync` + đổi tên. Ghi thẳng mỗi lần gõ thì một
   *  đoạn ghi chú là hàng trăm lần fsync, cửa sổ khựng theo từng phím — và người dùng
   *  đọc ra đúng một câu: *"app hay treo"*. Ô nhập vẫn phản hồi tức thì vì `dat` đổi
   *  ngay; chỉ cái đĩa là đợi. */
  const hoan = useRef<number | null>(null)
  /** Bản mới nhất của `dat`, đọc được ngay trong `datD` mà không phải phụ thuộc vào
   *  `dat` (làm `datD` dựng lại mỗi lần gõ) cũng không đặt hiệu ứng phụ trong hàm cập
   *  nhật của `setState` (StrictMode gọi hàm ấy hai lần). */
  const datRef = useRef<Record<string, unknown>>({})

  const datD = useCallback((k: string, v: unknown) => {
    const moi = { ...datRef.current, [k]: v }
    datRef.current = moi
    setDat(moi)
    if (hoan.current) window.clearTimeout(hoan.current)
    hoan.current = window.setTimeout(() => {
      hoan.current = null
      pyRL.rl_luu_dat(moi)
      if (k === 'symbol' && typeof v === 'string' && v.length >= 3) {
        pyRL.rl_kho_nen(v).then(r => { if (r.ok && r.value) setKhoNen(r.value) })
      }
    }, HOAN_GHI_MS)
  }, [])

  // Đóng cửa sổ trong lúc còn một lượt ghi đang hoãn thì GHI NỐT. Không có chỗ này thì
  // gõ xong ghi chú rồi tắt ngay là mất — đúng loại mất mát im lặng.
  useEffect(() => () => {
    if (hoan.current) {
      window.clearTimeout(hoan.current)
      pyRL.rl_luu_dat(datRef.current)
    }
  }, [])

  const chay = useCallback(async () => {
    if (!boot) return
    setLoi('')
    setKhoa(null)
    const gio = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    const d: DatRL = {
      ten: `Lượt ${gio}`, so_luot: soLuot, hat, cua, tran, tat: [...tat],
      cai_dat: {}, giu, gio_toi_da: gioToiDa, phang_toi_da: phangToiDa,
      so_nhan: soNhan,
    }
    const r = await pyRL.rl_chay(d)
    if (!r.ok || !r.value) return setLoi(r.error || 'Không chạy được.')
    setMa(r.value.ma)
    setTt(null)
  }, [boot, soLuot, hat, cua, tran, tat, giu, gioToiDa, phangToiDa, soNhan])

  /** ⭐ CHẠY LẠI Y HỆT — dựng lại từ ẢNH CHỤP của lượt cũ.
   *
   *  Cố ý gửi đúng một cái mã sang Python chứ không bơm hai chục ô cài đặt ngược lên
   *  đây rồi bơm xuôi lại: trạng thái giao diện đã trôi đi (vừa vặn vài núm xong), nên
   *  "y hệt" mà lấy từ nó thì không y hệt. Ảnh chụp nằm ở `LuotTim.cau_hinh`. */
  const chayLai = useCallback(async (cu: string) => {
    setLoi('')
    setKhoa(null)
    const r = await pyRL.rl_chay({ tu_luot: cu } as unknown as DatRL)
    if (!r.ok || !r.value) return setLoi(r.error || 'Không chạy lại được.')
    setMa(r.value.ma)
    setTt(null)
  }, [])

  /** ⭐ MỞ ĐOẠN KHOÁ — thứ biến "khớp dữ liệu" thành "đạt" (§18.3). */
  const moKhoa = useCallback(async () => {
    if (!ma) return
    setLoi('')
    const r = await pyRL.rl_mo_khoa(ma, 5)
    if (!r.ok || !r.value) return setLoi(r.error || 'Không mở được đoạn khoá.')
    setKhoa(r.value)
    setDat(d => ({ ...d, khoa_da_mo: r.value!.da_mo }))
  }, [ma])

  // ⭐ Hai hàm này gói `(mã, hạng)` lại rồi đưa cho `MoXe` — cùng một component với
  // cửa sổ Tester, chỉ khác đúng hai hàm gọi. Chép ra bản thứ hai là sớm muộn một bản
  // quên mất luật "không bao giờ đưa một con số gộp".
  const napPhanBo = useCallback(
    () => pyRL.rl_phan_bo(ma || '', soi ?? 1), [ma, soi])
  const thuBoNhanh = useCallback(
    (khoi: string) => pyRL.rl_thu_bo(ma || '', soi ?? 1, khoi), [ma, soi])

  const moSoDo = useCallback(async (hang: number) => {
    if (!ma) return
    setLoi('')
    const r = await pyRL.rl_mo_so_do(ma, hang)
    if (!r.ok) return setLoi(r.error || 'Không mở được sơ đồ.')
    // ⚠ Sơ đồ ĐÃ sang cửa sổ vẽ, nhưng Windows không cho kéo cửa sổ ấy lên trước.
    // Không nói ra thì màn hình RL không đổi gì và cú bấm trông y như rơi vào hư không
    // — mà thật ra việc đã xong, chỉ là cửa sổ nằm dưới.
    if (r.value && !r.value.len_truoc) {
      setLoi(`Đã đẩy "${r.value.ten}" sang cửa sổ vẽ — nhưng Windows không cho kéo cửa `
             + 'sổ ấy lên trước. Bấm vào nó trên thanh tác vụ.')
    }
  }, [ma])

  if (loi && !boot) return <div className="rl-loi-to">{loi}</div>
  if (!boot) return <div className="rl-cho">đang mở bàn điều khiển…</div>

  // Một bọc cho CẢ cửa sổ cài đặt. Dựng ở đây chứ không trong `CuaSoCaiDat`: trạng
  // thái vẫn thuộc về cửa sổ RL — hộp thoại chỉ là chỗ NHÌN và SỬA, không phải chỗ ở.
  const dk: DieuKhien = {
    boot, tat, setTat, tran, setTran, cua, setCua, dat, datD, khoNen,
    soLuot, setSoLuot, hat, setHat, giu, setGiu,
    gioToiDa, setGioToiDa, phangToiDa, setPhangToiDa, soNhan, setSoNhan,
  }

  const dangChay = !!tt?.dang_chay
  const tk = tt?.thong_ke
  const dauBang: DauBang[] = tt?.dau_bang || []

  // ------------------------------------------------------------ BẢNG DƯỚI
  const tabs: TabDuoi[] = [
    {
      khoa: 'dau-bang', nhan: 'Đầu bảng', dem: dauBang.length,
      ve: () => (
        <div className="rl-tab-noi">
          <div className="rl-train">
            ⚠ Mọi con số dưới đây là số <b>TRAIN</b> — đo trên chính đoạn dữ liệu máy vừa
            đào bới. Nó chưa phải kết luận. Và đừng lấy quán quân: <b>cái chung</b> giữa
            mấy cái đầu bảng mới đáng tin — nó sống sót qua nhiều đường đi khác nhau.
          </div>
          {dauBang.length === 0 ? (
            <div className="rl-trong">
              {dangChay ? 'chưa có sơ đồ nào qua cửa' : 'không sơ đồ nào qua cửa'}
            </div>
          ) : (
            <table className="rl-bang">
              {/* CẢ HAI KỲ cùng lúc — người dùng quan tâm cả tuần lẫn tháng, mà
                  `cham` vốn đã tính sẵn cả hai. Cặp cột đang DÙNG ĐỂ CHẤM được tô
                  đậm, để không phải nhớ mình đặt kỳ nào ở panel Thưởng. */}
              <thead><tr>
                <th>#</th>
                {/* ⭐ `dương n/m` đứng TRƯỚC `điểm`, cố ý. Đo được: 6/8 cái từng nằm ở
                    bảng này chỉ ăn may một đoạn (§18.5f) — nên `điểm` không được là
                    con số đầu tiên đập vào mắt. */}
                <th className="cham">dương</th>
                <th>hình dạng theo cửa sổ</th>
                <th>điểm</th>
                <th className={ky === 'tuan' ? 'cham' : ''}>tb tuần</th>
                <th className={ky === 'tuan' ? 'cham' : ''}>dđ tuần</th>
                <th className={ky === 'thang' ? 'cham' : ''}>tb tháng</th>
                <th className={ky === 'thang' ? 'cham' : ''}>dđ tháng</th>
                <th>{tenKy} có lệnh</th>
                <th>lệnh</th><th>sụt vốn</th><th>nước đi</th><th />
              </tr></thead>
              <tbody>
                {dauBang.map(d => {
                  const k = d.ky === 'thang' ? d.thang : d.tuan
                  return (
                  <tr key={d.hang}>
                    <td>{d.hang}</td>
                    <td className={'rl-diem' + (deu(d) ? ' tot' : ' xau')}>
                      {d.so_cua_so ? `${d.cua_so_duong}/${d.so_cua_so}` : '—'}</td>
                    <td className="rl-trai">
                      <span className="rl-cuon-dai rl-dai-nho">
                        {(d.cua_so || []).map((c, i) => (
                          <span key={i} title={`cửa sổ ${i + 1}: ${so(c, 4)}`}
                                className={'rl-cuon-o rl-o-nho '
                                  + (c > 0 ? 'duong' : c < 0 ? 'am' : 'trong')} />
                        ))}
                      </span>
                    </td>
                    <td>{so(d.diem, 4)}</td>
                    <td className={d.ky === 'thang' ? '' : 'cham'}>
                      {pt(d.tuan.trung_binh, 3)}</td>
                    <td className={d.ky === 'thang' ? '' : 'cham'}>
                      {so(d.tuan.dao_dong, 3)}%</td>
                    <td className={d.ky === 'thang' ? 'cham' : ''}>
                      {pt(d.thang?.trung_binh, 3)}</td>
                    <td className={d.ky === 'thang' ? 'cham' : ''}>
                      {d.thang ? `${so(d.thang.dao_dong, 3)}%` : '—'}</td>
                    <td>{k?.co_lenh}/{k?.so_ky}</td>
                    <td>{d.so_lenh}</td>
                    <td>{so(d.sut_von_pt, 1)}%</td>
                    <td>{d.so_nuoc}</td>
                    <td><button className="rl-mo" onClick={() => moSoDo(d.hang)}>
                      Mở sơ đồ</button></td>
                  </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      ),
    },
    {
      khoa: 'mo-xe', nhan: 'Mổ xẻ',
      dem: soi ?? undefined,
      // ⭐ Trước tab này, muốn hiểu một sơ đồ máy vừa đẻ ra thì phải đẩy sang cửa sổ vẽ,
      // chạy Tester, rồi mới mở được bảng — bốn bước cho câu "cái này sống nhờ đâu".
      nut: dauBang.length > 0 ? (
        <div className="rl-chip-hang">
          {dauBang.slice(0, 8).map(d => (
            <button key={d.hang}
                    className={'rl-chip' + (soi === d.hang ? '' : ' tat')}
                    onClick={() => setSoi(d.hang)}>#{d.hang}</button>
          ))}
        </div>
      ) : undefined,
      ve: () => (
        soi === null
          ? <div className="mx-trong">
              {dauBang.length === 0
                ? 'chưa sơ đồ nào qua cửa để soi'
                : 'chọn một sơ đồ ở góc phải để soi'}
            </div>
          : <MoXe sanSang={!!ma} nap={napPhanBo} thuBo={thuBoNhanh}
                  tieu={`đang soi sơ đồ hạng #${soi} — chạy lại trên ĐOẠN TRAIN`} />
      ),
    },
    {
      khoa: 'doan-khoa', nhan: 'Đoạn khoá',
      dem: khoa ? khoa.ds.length : undefined,
      nut: coKhoa && dauBang.length > 0 && !dangChay ? (
        <button className="rl-mo" onClick={moKhoa}>
          Chạy 5 cái đầu bảng trên đoạn khoá
        </button>
      ) : undefined,
      ve: () => (
        <div className="rl-tab-noi">
          {!coKhoa ? (
            <div className="rl-train">
              ⚠ Chưa đặt <b>đoạn khoá</b>. Mở <b>Dữ liệu</b> và điền hai ô «khoá từ /
              đến» — một khoảng KHÔNG nằm trong train. Không có nó thì mọi con số trên
              màn hình vẫn chỉ là <b>số TRAIN</b>, đo trên chính đoạn máy vừa đào bới.
            </div>
          ) : !khoa ? (
            <div className="rl-trong">
              {dauBang.length === 0 ? 'chưa có sơ đồ nào qua cửa để mang sang đoạn khoá'
                : dangChay ? 'đang chạy — mở khoá sau khi xong'
                : 'bấm nút góc phải để chạy nhóm đầu bảng trên đoạn khoá'}
            </div>
          ) : (
            <>
              <div className="rl-train">
                Đoạn khoá <b>{khoa.tu} → {khoa.den}</b> · đã mở <b>{khoa.da_mo}</b> lần.
                {' '}Rơi từ train xuống là <b>bình thường</b> — train đã bị đào bới hàng
                nghìn lượt. Quan trọng là nó còn <b>dương</b> hay không. Rơi qua âm nghĩa
                là sơ đồ ấy chỉ tồn tại trong đoạn train.
              </div>
              <table className="rl-bang">
                <thead><tr>
                  <th>#</th><th>điểm train</th><th>điểm KHOÁ</th><th>chênh</th>
                  <th>lãi</th><th>lệnh</th><th>sụt vốn</th>
                  {khoa.cuon && <th>{TEN_BUOC[khoa.buoc]} dương</th>}
                  <th>đạt cửa?</th>
                </tr></thead>
                <tbody>
                  {khoa.ds.map(d => (
                    <tr key={d.hang}>
                      <td>{d.hang}</td>
                      {d.loi ? <td colSpan={khoa.cuon ? 8 : 7} className="xau">
                        {d.loi}</td> : <>
                        <td>{so(d.train, 4)}</td>
                        <td className={'rl-diem' + ((d.khoa ?? 0) < 0 ? ' xau' : '')}>
                          {so(d.khoa, 4)}</td>
                        <td>{so((d.khoa ?? 0) - (d.train ?? 0), 4)}</td>
                        <td>{pt(d.khoa_lai_pt, 1)}</td>
                        <td>{d.khoa_so_lenh}</td>
                        <td>{so(d.khoa_sut_von_pt, 1)}%</td>
                        {khoa.cuon && (
                          <td className={(d.cua_so_duong ?? 0) * 2 < (d.so_cua_so ?? 0)
                                         ? 'xau' : ''}>
                            {d.so_cua_so ? `${d.cua_so_duong}/${d.so_cua_so}` : '—'}
                          </td>
                        )}
                        <td>{d.khoa_dat ? '✔' : d.khoa_ly_do || '✘'}</td>
                      </>}
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* CUỐN TỚI — từng cửa sổ một, xếp thành dải.
                  Đây là chỗ trả lời câu "có đều QUA THỜI GIAN không", mà một con số
                  gộp cả dải không nói ra được: đo trên XAUUSD, một sơ đồ điểm gộp
                  +0,0009 mà chỉ 8/18 quý dương. */}
              {khoa.cuon && khoa.ds.some(d => d.cua_so?.length) && (
                <>
                  <div className="rl-nhom-ten rl-to">
                    <span>TỪNG CỬA SỔ — bước {TEN_BUOC[khoa.buoc]}</span></div>
                  <p className="rl-nho">
                    Hàng nào nhiều ô đỏ là hàng ấy <b>không sống qua thời gian</b> — dù
                    con số gộp có đẹp. Ô mờ là cửa sổ <b>không lệnh nào</b>. Rê chuột
                    lên ô để xem ngày và ba con số.
                  </p>
                  {khoa.ds.filter(d => d.cua_so?.length).map(d => (
                    <div className="rl-cuon" key={d.hang}>
                      <span className="rl-cuon-hang">#{d.hang}</span>
                      <span className="rl-cuon-dai">
                        {d.cua_so!.map(w => (
                          <span key={w.tu}
                                className={'rl-cuon-o ' + (!w.co_lenh ? 'trong'
                                           : w.diem > 0 ? 'duong' : 'am')}
                                title={`${w.tu} → ${w.den}\n`
                                       + `điểm ${so(w.diem, 4)} · `
                                       + `tb ${pt(w.trung_binh, 3)} · `
                                       + `dđ ${so(w.dao_dong, 3)}%\n`
                                       + `${w.co_lenh}/${w.so_ky} ${tenKy} có lệnh`}>
                            <i>{nhanKy(w.tu, khoa.buoc)}</i>
                            <b>{so(w.diem, 2)}</b>
                          </span>
                        ))}
                      </span>
                      <span className="rl-cuon-tong">
                        {d.cua_so_duong}/{d.so_cua_so} dương</span>
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </div>
      ),
    },
    {
      khoa: 'vi-sao', nhan: 'Vì sao rớt',
      dem: tk ? tk.rot_cua + tk.ket + tk.no + (tk.na_lenh ?? 0) : undefined,
      ve: () => (
        <div className="rl-tab-noi">
          {!tk ? <div className="rl-trong">chưa chạy lượt nào</div> : <>
            <div className="rl-nho">
              Cột <b>suýt qua</b> là thứ đáng đọc nhất ở đây: nó trả lời
              {' '}<i>nới cửa một chút thì có thêm bao nhiêu cái lọt</i> — thay vì phải
              đoán rồi chạy lại cả lượt.
            </div>
            {Object.entries(tk.rot_chi_tiet || {}).length > 0 && (
              <table className="rl-bang vs-bang">
                <thead><tr>
                  <th>rớt ở cửa</th><th>ngưỡng</th><th>số sơ đồ</th>
                  <th>suýt qua</th><th>trượt xa bao nhiêu</th><th>ví dụ</th>
                </tr></thead>
                <tbody>
                  {Object.entries(tk.rot_chi_tiet || {})
                    .sort((a, b) => b[1].so - a[1].so)
                    .map(([k, v]) => (
                    <tr key={k}>
                      <td className="rl-trai">{TEN_CUA[k] || k}</td>
                      <td>{v.nguong}</td>
                      <td>{v.so.toLocaleString('vi-VN')}</td>
                      {/* Thùng ĐẦU của `thiếu` = trượt dưới 10% — tức nới một tí là lọt. */}
                      <td className={v.thieu[0] ? 'tot' : ''}>
                        {v.thieu[0].toLocaleString('vi-VN')}</td>
                      <td className="rl-trai">
                        <span className="vs-dai">
                          {v.thieu.map((n, i) => (
                            <span key={i} className="vs-o"
                                  title={`${NHAN_THIEU[i]} — ${n} sơ đồ`}>
                              <span className="vs-thanh"
                                    style={{ height: n
                                      ? `${Math.max(8, n / Math.max(...v.thieu) * 100)}%`
                                      : '0' }} />
                            </span>
                          ))}
                        </span>
                      </td>
                      <td className="rl-trai rl-nho">{v.vi_du[0] || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="rl-nhom-ten rl-to"><span>CHẾT TRƯỚC CẢ CỬA</span></div>
            <table className="rl-bang rl-bang-trai">
              <tbody>
                {!!tk.khong_lenh && (
                  <tr><td>không vào lệnh nào</td><td>{tk.khong_lenh}</td></tr>
                )}
                {!!tk.na_lenh && (
                  <tr><td>nã lệnh — bỏ dở giữa chừng (quá
                    {' '}{Number(dat.lenh_moi_tuan_toi_da ?? 0)} lệnh/tuần)</td>
                    <td>{tk.na_lenh}</td></tr>
                )}
                {!!tk.qua_nang && (
                  <tr><td>ôm lệnh — bỏ dở giữa chừng (quá
                    {' '}{Number(dat.luot_moi_nen_toi_da ?? 0)} lượt/nến)</td>
                    <td>{tk.qua_nang}</td></tr>
                )}
                {!!tk.trung_lap && <tr><td>trùng sơ đồ đã chấm, bỏ qua</td><td>{tk.trung_lap}</td></tr>}
                {!!tk.ket && <tr className="xau"><td>lượt đi kẹt</td><td>{tk.ket}</td></tr>}
                {!!tk.no && <tr className="xau"><td>bộ chạy từ chối</td><td>{tk.no}</td></tr>}
              </tbody>
            </table>
            {tk.no_vi?.length ? (
              <div className="rl-nho">ví dụ: {tk.no_vi.slice(0, 2).join(' · ')}</div>
            ) : null}
          </>}
        </div>
      ),
    },
    {
      khoa: 'luot', nhan: 'Lượt khác', dem: ds.length,
      ve: () => (
        <div className="rl-tab-noi rl-ds">
          {ds.length === 0 ? <div className="rl-trong">chưa có lượt nào</div> : ds.map(x => (
            <div key={x.ma} className={'rl-luot' + (x.ma === ma ? ' dang' : '')}>
              <button className="rl-luot-chon"
                      onClick={() => { setMa(x.ma); setTt(null) }}>
                <b>{x.ten}</b>
                {/* ⭐ Dòng này là thứ khiến sổ lượt DÙNG ĐƯỢC. Không có nó thì hai
                    chục dòng "Lượt 14:05" không phân biệt nổi cái nào chạy với gì —
                    và mấy con số bên cạnh hết so được với nhau. */}
                <i>{x.nhan || '—'}</i>
                <span>{x.dang_chay ? '● đang chạy' : `${x.da_chay}/${x.tong}`}
                  {' · '}{x.diem_tot_nhat === null ? '—' : so(x.diem_tot_nhat, 3)}</span>
              </button>
              <button className="rl-mo rl-luot-lai" disabled={dangChay}
                      title="Chạy lại với ĐÚNG cấu hình lượt này, không phải cấu hình đang đặt"
                      onClick={() => chayLai(x.ma)}>chạy lại y hệt</button>
            </div>
          ))}
        </div>
      ),
    },
  ]

  return (
    <div className="rl-app">
      <TitleBar tieuDe="RL — tìm chiến lược" menus={[]} />

      {/* -------------------------------- RIBBON --------------------------------
          Chỉ thứ BẤM NHIỀU. Mọi đồ đặt-một-lần nằm ở cửa sổ ⚙ (`CaiDatLuot`) — xem
          docstring ở đó cho lý do. */}
      <div className="ribbon">
        <Nhom ten="Chạy">
          <Nut ten="Chạy" icon={IR.chay} onClick={chay} tat={dangChay}
               nhan={`${soLuot.toLocaleString('vi-VN')} sơ đồ`}
               title="Mở một lượt tìm trên luồng nền" />
          <Nut ten="Dừng" icon={IR.dung} tat={!dangChay}
               onClick={() => ma && pyRL.rl_dung(ma)}
               title="Chấm nốt sơ đồ đang dở rồi ngừng" />
        </Nhom>

        {/* Hai núm duy nhất vặn giữa hai lượt — để thẳng ngoài này, khỏi mở cửa sổ. */}
        <Nhom ten="Lượt này">
          <ONhap nhan="số sơ đồ" gt={soLuot} dat={setSoLuot} rong={72} />
          <ONhap nhan="hạt giống" gt={hat} dat={setHat} rong={62} />
        </Nhom>

        <Nhom ten="Luật chơi · dữ liệu">
          <Nut ten="Cài đặt" icon={IR.cai_dat} onClick={() => setMoCaiDat('kho')}
               nhan={nhanCua(dk)}
               title="Kho đồ · thang số · trần · thưởng·phạt · dữ liệu · ngân sách · ghi chú" />
        </Nhom>
      </div>

      {loi && <div className="rl-loi">{loi}</div>}

      {/* ------------------------------ DASHBOARD ------------------------------ */}
      <BangDieuKhien tt={tt} nhan={tt?.nhan || nhanCua(dk)} dangChay={dangChay}
                     tongNhan={boot.so_nhan_may || 1} dauBang={dauBang}
                     boot={boot} moSoDo={moSoDo} />

      <BangDuoi tabs={tabs} />

      {moCaiDat && (
        <CuaSoCaiDat d={dk} mucDau={moCaiDat} onClose={() => setMoCaiDat(null)} />
      )}
    </div>
  )
}
