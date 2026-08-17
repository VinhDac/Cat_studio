import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { cho_cau_noi, pyRL } from '../api'
import { useKhungCuaSo } from '../useKhungCuaSo'
import TitleBar from '../components/TitleBar'
import BangDuoi, { type TabDuoi } from '../tester/BangDuoi'
import DuongDiem from './DuongDiem'
import { IR, Nhom, Nut, NutPanel } from './RibbonRL'
import type { DatRL, DauBang, KetQuaKhoa, KhoNen, NhomChon, RLBoot,
              TrangThaiLuot } from '../types'

/** CỬA SỔ RL — bàn điều khiển máy tìm chiến lược.
 *
 *     core.md §18.6, §18.9
 *
 * Bố cục học thẳng cửa sổ vẽ, ba tầng:
 *
 *     RIBBON     ▶ Chạy · ■ Dừng │ Kho đồ │ Trần │ Ưu tiên │ Dữ liệu │ Ngân sách
 *     DASHBOARD  tiến độ + mấy ô nhìn ("tôi không muốn chạy mù")
 *     BẢNG DƯỚI  Đầu bảng · Cái chung · Vì sao rớt · Lượt khác — cụp lên xuống được
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

/** Bảng bật/tắt THẺ — dùng chung cho panel "Kho đồ" và "Thang số".
 *
 * ⭐ Không phân biệt hai panel: với giao diện, "tắt toán hạng ATR" và "tắt nấc SL 1,5"
 * là **cùng một việc** — bỏ một chuỗi thẻ vào tập `tat`. Nhờ vậy Python thêm chiều mới
 * (chế độ sửa, khung giờ, một thang nữa) là panel dài ra, JS không sửa một dòng nào. */
function ChonThe({ nhom, tat, datTat }: {
  nhom: NhomChon[]
  tat: Set<string>
  datTat: (f: (s: Set<string>) => Set<string>) => void
}) {
  const bat = (the: string) => datTat(s => {
    const n = new Set(s)
    if (n.has(the)) n.delete(the); else n.add(the)
    return n
  })
  /** Bật/tắt CẢ NHÓM — 22 toán hạng mà bấm từng cái thì không ai dùng. */
  const caNhom = (g: NhomChon, tatHet: boolean) => datTat(s => {
    const n = new Set(s)
    for (const m of g.muc) { if (tatHet) n.add(m.the); else n.delete(m.the) }
    return n
  })

  return (
    <>
      {nhom.map(g => {
        const off = g.muc.filter(m => tat.has(m.the)).length
        return (
          <div className="rl-nhom" key={g.nhom}>
            <div className="rl-nhom-ten">
              <span>{g.nhan}{g.don_vi && <em> · {g.don_vi}</em>}</span>
              <button onClick={() => caNhom(g, off < g.muc.length)}>
                {off < g.muc.length ? 'tắt hết' : 'bật hết'}
              </button>
            </div>
            <div className="rl-chip-hang">
              {g.muc.map(m => (
                <button key={m.the}
                        title={m.z ? 'cần cổng zone đứng trước (§12.6c)'
                                   : m.manage ? 'chỉ dùng được ở sơ đồ Manage' : ''}
                        className={'rl-chip' + (tat.has(m.the) ? ' tat' : '')}
                        onClick={() => bat(m.the)}>
                  {m.nhan}
                  {m.z && <span className="rl-z">z</span>}
                  {m.manage && <span className="rl-z rl-m">m</span>}
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </>
  )
}

/** Ô chờ một thứ để nhìn CHƯA DỰNG.
 *
 * ⚠ Nói thẳng nó sẽ trả lời câu gì, đừng để một khung xám trống không. Một chỗ trống
 * có chú thích là lời hứa đọc được; một chỗ trống câm là nút hứa suông. */
function ChuaCo({ ten, hoi }: { ten: string; hoi: string }) {
  return (
    <div className="rl-chua-co">
      <b>{ten}</b>
      <span>{hoi}</span>
      <em>chưa dựng</em>
    </div>
  )
}

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
  /** Cài đặt RIÊNG của RL — train · KHOÁ · chi phí. Không dùng chung với Tester. */
  const [dat, setDat] = useState<Record<string, unknown>>({})
  const [khoNen, setKhoNen] = useState<KhoNen | null>(null)
  const [khoa, setKhoa] = useState<KetQuaKhoa | null>(null)

  const nhip = useRef<number | null>(null)

  useEffect(() => {
    cho_cau_noi('rl_boot')
      .then(() => pyRL.rl_boot())
      .then(r => {
        if (!r.ok || !r.value) return setLoi(r.error || 'Không nạp được cửa sổ RL.')
        setBoot(r.value)
        setTran({ ...r.value.tran })
        setCua({ ...r.value.cua })
        setDat({ ...r.value.cai_dat })
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

  const nhomKho = useMemo(
    () => (boot?.chon || []).filter(g => g.cho === 'kho'), [boot])
  const nhomThang = useMemo(
    () => (boot?.chon || []).filter(g => g.cho === 'thang'), [boot])
  /** Tổng số thẻ và số đang bật — hiện dưới tên nút, khỏi mở panel mới biết. */
  const demChon = useCallback((gs: NhomChon[]) => {
    const tong = gs.reduce((s, g) => s + g.muc.length, 0)
    const off = gs.reduce(
      (s, g) => s + g.muc.filter(m => tat.has(m.the)).length, 0)
    return `${tong - off}/${tong}`
  }, [tat])

  const kyCham = (cua.ky as string) ?? 'tuan'
  const tenKy = kyCham === 'thang' ? 'tháng' : 'tuần'
  const coKhoa = !!(dat.khoa_tu && dat.khoa_den)
  const nhanCua: string = useMemo(() => {
    const n = Object.entries(cua).filter(
      ([k, v]) => v !== null && k !== 'ky' && k !== 'tuan_co_lenh').length
    return n ? `${tenKy} · ${n} cửa` : tenKy
  }, [cua, tenKy])

  /** Sửa MỘT ô cài đặt RL và ghi xuống ngay — panel không có nút Lưu, và không nên có:
   *  một bàn điều khiển bắt bấm Lưu là một bàn điều khiển quên mất thứ vừa gõ. */
  const datD = useCallback((k: string, v: unknown) => {
    setDat(d => {
      const moi = { ...d, [k]: v }
      pyRL.rl_luu_dat(moi)
      if (k === 'symbol' && typeof v === 'string' && v.length >= 3) {
        pyRL.rl_kho_nen(v).then(r => { if (r.ok && r.value) setKhoNen(r.value) })
      }
      return moi
    })
  }, [])

  const chay = useCallback(async () => {
    if (!boot) return
    setLoi('')
    setKhoa(null)
    const gio = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
    const d: DatRL = {
      ten: `Lượt ${gio}`, so_luot: soLuot, hat, cua, tran, tat: [...tat],
      cai_dat: {}, giu, gio_toi_da: gioToiDa, phang_toi_da: phangToiDa,
    }
    const r = await pyRL.rl_chay(d)
    if (!r.ok || !r.value) return setLoi(r.error || 'Không chạy được.')
    setMa(r.value.ma)
    setTt(null)
  }, [boot, soLuot, hat, cua, tran, tat, giu, gioToiDa, phangToiDa])

  /** ⭐ MỞ ĐOẠN KHOÁ — thứ biến "khớp dữ liệu" thành "đạt" (§18.3). */
  const moKhoa = useCallback(async () => {
    if (!ma) return
    setLoi('')
    const r = await pyRL.rl_mo_khoa(ma, 5)
    if (!r.ok || !r.value) return setLoi(r.error || 'Không mở được đoạn khoá.')
    setKhoa(r.value)
    setDat(d => ({ ...d, khoa_da_mo: r.value!.da_mo }))
  }, [ma])

  const moSoDo = useCallback(async (hang: number) => {
    if (!ma) return
    const r = await pyRL.rl_mo_so_do(ma, hang)
    if (!r.ok) setLoi(r.error || 'Không mở được sơ đồ.')
  }, [ma])

  if (loi && !boot) return <div className="rl-loi-to">{loi}</div>
  if (!boot) return <div className="rl-cho">đang mở bàn điều khiển…</div>

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
              <thead><tr>
                <th>#</th><th>điểm</th><th>trung bình tuần</th><th>dao động tuần</th>
                <th>tuần có lệnh</th><th>lệnh</th><th>sụt vốn</th><th>nước đi</th><th />
              </tr></thead>
              <tbody>
                {dauBang.map(d => (
                  <tr key={d.hang}>
                    <td>{d.hang}</td>
                    <td className="rl-diem">{so(d.diem, 4)}</td>
                    <td>{pt(d.tuan.trung_binh, 3)}</td>
                    <td>{so(d.tuan.dao_dong, 3)}%</td>
                    <td>{d.tuan.co_lenh}/{d.tuan.so_ky}</td>
                    <td>{d.so_lenh}</td>
                    <td>{so(d.sut_von_pt, 1)}%</td>
                    <td>{d.so_nuoc}</td>
                    <td><button className="rl-mo" onClick={() => moSoDo(d.hang)}>
                      Mở sơ đồ</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
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
                  <th>lãi</th><th>lệnh</th><th>sụt vốn</th><th>đạt cửa?</th>
                </tr></thead>
                <tbody>
                  {khoa.ds.map(d => (
                    <tr key={d.hang}>
                      <td>{d.hang}</td>
                      {d.loi ? <td colSpan={7} className="xau">{d.loi}</td> : <>
                        <td>{so(d.train, 4)}</td>
                        <td className={'rl-diem' + ((d.khoa ?? 0) < 0 ? ' xau' : '')}>
                          {so(d.khoa, 4)}</td>
                        <td>{so((d.khoa ?? 0) - (d.train ?? 0), 4)}</td>
                        <td>{pt(d.khoa_lai_pt, 1)}</td>
                        <td>{d.khoa_so_lenh}</td>
                        <td>{so(d.khoa_sut_von_pt, 1)}%</td>
                        <td>{d.khoa_dat ? '✔' : d.khoa_ly_do || '✘'}</td>
                      </>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      ),
    },
    {
      khoa: 'cai-chung', nhan: 'Cái chung',
      ve: () => (
        <div className="rl-tab-noi">
          <ChuaCo ten="Cái chung giữa nhóm đầu bảng"
                  hoi={'"8/10 sơ đồ dùng cùng cổng ATR < 1,0 × ATR nền" — thứ sống sót '
                       + 'qua nhiều đường đi độc lập mới là thứ đáng tin, không phải '
                       + 'sơ đồ hạng nhất.'} />
        </div>
      ),
    },
    {
      khoa: 'vi-sao', nhan: 'Vì sao rớt',
      dem: tk ? tk.rot_cua + tk.ket + tk.no : undefined,
      ve: () => (
        <div className="rl-tab-noi">
          {!tk ? <div className="rl-trong">chưa chạy lượt nào</div> : (
            <table className="rl-bang rl-bang-trai">
              <tbody>
                {Object.entries(tk.ly_do_rot).map(([k, v]) => (
                  <tr key={k}><td>{k}</td><td>{v}</td></tr>
                ))}
                {!!tk.khong_lenh && (
                  <tr><td>không vào lệnh nào (trước cả cửa)</td><td>{tk.khong_lenh}</td></tr>
                )}
                {!!tk.trung_lap && <tr><td>trùng sơ đồ đã chấm, bỏ qua</td><td>{tk.trung_lap}</td></tr>}
                {!!tk.ket && <tr className="xau"><td>lượt đi kẹt</td><td>{tk.ket}</td></tr>}
                {!!tk.no && <tr className="xau"><td>bộ chạy từ chối</td><td>{tk.no}</td></tr>}
              </tbody>
            </table>
          )}
          {tk?.no_vi?.length ? (
            <div className="rl-nho">ví dụ: {tk.no_vi.slice(0, 2).join(' · ')}</div>
          ) : null}
        </div>
      ),
    },
    {
      khoa: 'luot', nhan: 'Lượt khác', dem: ds.length,
      ve: () => (
        <div className="rl-tab-noi rl-ds">
          {ds.length === 0 ? <div className="rl-trong">chưa có lượt nào</div> : ds.map(x => (
            <button key={x.ma} className={'rl-luot' + (x.ma === ma ? ' dang' : '')}
                    onClick={() => { setMa(x.ma); setTt(null) }}>
              <b>{x.ten}</b>
              <span>{x.dang_chay ? '● đang chạy' : `${x.da_chay}/${x.tong}`}</span>
              <span>{x.diem_tot_nhat === null ? '—' : so(x.diem_tot_nhat, 3)}</span>
            </button>
          ))}
        </div>
      ),
    },
  ]

  return (
    <div className="rl-app">
      <TitleBar tieuDe="RL — tìm chiến lược" menus={[]} />

      {/* -------------------------------- RIBBON -------------------------------- */}
      <div className="ribbon">
        <Nhom ten="Chạy">
          <Nut ten="Chạy" icon={IR.chay} onClick={chay} tat={dangChay}
               nhan={`${soLuot.toLocaleString('vi-VN')} sơ đồ`}
               title="Mở một lượt tìm trên luồng nền" />
          <Nut ten="Dừng" icon={IR.dung} tat={!dangChay}
               onClick={() => ma && pyRL.rl_dung(ma)}
               title="Chấm nốt sơ đồ đang dở rồi ngừng" />
        </Nhom>

        <Nhom ten="Luật chơi">
          <NutPanel ten="Kho đồ" icon={IR.kho} rong={470}
                    nhan={demChon(nhomKho)}>
            <p className="rl-giai">
              Tắt bớt là <b>lần này tôi không muốn dùng</b> — không phải "cái này hỏng".
              Luật thì không tắt được.
            </p>
            <ChonThe nhom={nhomKho} tat={tat} datTat={setTat} />
            <div className="rl-nho">{boot.so_nuoc_di.toLocaleString('vi-VN')} nước đi
              trong kho — thêm một toán hạng là kho tự lớn.</div>
          </NutPanel>

          <NutPanel ten="Thang số" icon={IR.thang} rong={470}
                    nhan={demChon(nhomThang)}>
            <p className="rl-giai">
              Máy <b>không dò số tự do</b>, nó chọn nấc. Đo được: dò SL thang mịn bước
              0,1 trên 2025 ra <i>2,7</i> — thắng năm đó, nhưng sang ba năm chưa thấy thì
              THUA cả bản thô <i>3,0</i>. Hai nấc cạnh nhau lệch trung bình 5,11 R: đó là
              nhiễu, không phải tín hiệu.
            </p>
            <ChonThe nhom={nhomThang} tat={tat} datTat={setTat} />
            <div className="rl-nho">
              Tắt một nấc <b>không đụng tới kho nước đi</b> — kho vẫn nguyên
              {' '}{boot.so_nuoc_di.toLocaleString('vi-VN')} ô, chỉ là mấy ô mang nấc đó
              bị che. Sửa thang thật thì một mạng đã học phải học lại; che thì không.
            </div>
          </NutPanel>

          <NutPanel ten="Trần" icon={IR.tran}
                    nhan={`${tran.dk_moi_cong}·${tran.nhanh_moi_re}·${tran.khoi_entry}·${tran.khoi_manage}`}>
            <p className="rl-giai">
              Chỉ áp cho <b>máy</b> — bạn vẽ tay bao nhiêu khối cũng được. Người vẽ 28
              khối thì biết mình đang làm gì; máy sinh 28 khối là nó bịa.
            </p>
            {[['dk_moi_cong', 'điều kiện một cổng'],
              ['nhanh_moi_re', 'nhánh một ngã rẽ'],
              ['khoi_entry', 'khối sơ đồ Entry'],
              ['khoi_manage', 'khối sơ đồ Manage']].map(([k, nhan]) => (
              <label className="rl-hang" key={k}>
                <span>{nhan}</span>
                <input type="number" min={1} max={40} value={tran[k] ?? 0}
                       onChange={e => setTran(t => ({ ...t, [k]: +e.target.value }))} />
              </label>
            ))}
          </NutPanel>

          <NutPanel ten="Ưu tiên" icon={IR.cua} rong={420} nhan={nhanCua}>
            <p className="rl-giai">
              Toàn là <b>cửa</b> — "cái gì tôi KHÔNG nhận". Không cái nào là cân: sụt vốn
              không đổi chác được với lãi, cháy 60% tài khoản thì không mức lãi nào bù
              lại. Xếp hạng thì <b>luôn</b> là <i>trung bình ÷ dao động</i> — bạn chỉnh
              <i> thích gì</i>, không chỉnh <i>đo bằng gì</i>.
            </p>

            <div className="rl-nhom-ten"><span>Chấm theo kỳ</span></div>
            <div className="rl-chip-hang">
              {[['tuan', 'TUẦN'], ['thang', 'THÁNG']].map(([k, n]) => (
                <button key={k} className={'rl-chip' + (kyCham === k ? '' : ' tat')}
                        onClick={() => setCua(c => ({ ...c, ky: k }))}>{n}</button>
              ))}
            </div>
            <p className="rl-nho">
              Đổi kỳ KHÔNG phải đổi thước — vẫn là trung bình ÷ dao động, chỉ đổi độ
              phân giải nhìn. Tuần bắt được cái giật cục mà tháng làm mượt mất.
            </p>

            <label className="rl-hang">
              <span>{tenKy} có lệnh tối thiểu</span>
              <input type="number" min={boot.tuan_co_lenh_toi_thieu * 100} max={100}
                     value={Math.round(((cua.tuan_co_lenh as number) ?? 0) * 100)}
                     onChange={e => setCua(c => ({
                       ...c, tuan_co_lenh: +e.target.value / 100 }))} />
              <em>%</em>
            </label>
            <p className="rl-nho">
              Khoá cứng ở {Math.round(boot.tuan_co_lenh_toi_thieu * 100)}% — siết thêm
              được, nới ra thì không. Một sơ đồ vào <b>đúng một lệnh</b> trong 3,5 năm ăn
              điểm cao hơn sơ đồ vào 929 lệnh; cái cửa này chặn đúng chỗ đó.
            </p>

            <div className="rl-nhom-ten"><span>Chặn cái không nhận</span></div>
            {([['so_lenh_toi_thieu', 'số lệnh tối thiểu', 'lệnh'],
               ['sut_von_toi_da', 'sụt vốn tối đa', '%'],
               ['te_nhat_toi_da', `${tenKy} tệ nhất không quá`, '%'],
               ['dao_dong_toi_da', `dao động ${tenKy} tối đa`, '%'],
               ['lai_toi_thieu', 'lãi tối thiểu', '%/năm'],
               ['diem_toi_thieu', 'điểm tối thiểu', '']] as const).map(([k, nhan, dv]) => (
              <label className="rl-hang" key={k}>
                <span>{nhan}</span>
                <input type="number" step="any" placeholder="không lọc"
                       value={(cua[k] as number | null) ?? ''}
                       onChange={e => setCua(c => ({
                         ...c, [k]: e.target.value === '' ? null : +e.target.value }))} />
                <em>{dv}</em>
              </label>
            ))}
            <div className="rl-nho">Để trống là không lọc.</div>
          </NutPanel>
        </Nhom>

        <Nhom ten="Chạy trên gì">
          <NutPanel ten="Dữ liệu" icon={IR.du_lieu} rong={420}
                    nhan={`${dat.symbol || '—'}${coKhoa ? ' · có khoá' : ''}`}>
            <p className="rl-giai">
              ⭐ <b>Cài đặt RIÊNG của RL</b>, không dùng chung với Strategy Test. Tester
              có đúng MỘT khoảng; RL cần ít nhất HAI — đoạn máy đào thoải mái, và đoạn
              KHOÁ mở đúng một lần.
            </p>
            <label className="rl-hang">
              <span>symbol</span>
              <input value={String(dat.symbol ?? '')} spellCheck={false}
                     onChange={e => datD('symbol', e.target.value.toUpperCase())} />
            </label>
            {khoNen && (
              <div className={'rl-kho-nen' + (khoNen.co ? '' : ' xau')}>
                {khoNen.co
                  ? <>kho có <b>{(khoNen.so_nen ?? 0).toLocaleString('vi-VN')}</b> nến M1
                      {' · '}{khoNen.tu} → {khoNen.den}</>
                  : <>⚠ chưa có nến nào cho «{khoNen.symbol}» — chạy sẽ phải tải từ MT5</>}
              </div>
            )}

            <div className="rl-nhom-ten"><span>TRAIN — máy đào thoải mái</span></div>
            <label className="rl-hang"><span>từ</span>
              <input value={String(dat.tu ?? '')} placeholder="2021-07-01"
                     onChange={e => datD('tu', e.target.value)} /></label>
            <label className="rl-hang"><span>đến</span>
              <input value={String(dat.den ?? '')} placeholder="2025-01-01"
                     onChange={e => datD('den', e.target.value)} /></label>

            <div className="rl-nhom-ten"><span>KHOÁ — mở đúng một lần</span></div>
            <label className="rl-hang"><span>từ</span>
              <input value={String(dat.khoa_tu ?? '')} placeholder="2025-01-01"
                     onChange={e => datD('khoa_tu', e.target.value)} /></label>
            <label className="rl-hang"><span>đến</span>
              <input value={String(dat.khoa_den ?? '')} placeholder="2026-01-01"
                     onChange={e => datD('khoa_den', e.target.value)} /></label>
            <p className={'rl-nho' + (coKhoa ? '' : ' rl-canh')}>
              {coKhoa
                ? <>Đã mở <b>{Number(dat.khoa_da_mo ?? 0)}</b> lần. Không cấm bấm — nhưng
                    nhìn một đoạn đủ nhiều lần thì nó thôi là "chưa thấy", và cái đồng hồ
                    này là chỗ duy nhất nói ra chuyện đó.</>
                : <>⚠ Chưa đặt đoạn khoá — <b>mọi con số sẽ chỉ là số TRAIN</b>, đo trên
                    chính đoạn máy vừa đào bới. Đặt một khoảng KHÔNG nằm trong train.</>}
            </p>

            <div className="rl-nhom-ten"><span>Chi phí</span></div>
            {([['deposit', 'vốn', '$'], ['commission', 'hoa hồng', '$/lot'],
               ['spread_diem', 'spread', 'điểm'],
               ['truot_diem', 'trượt giá', 'điểm']] as const).map(([k, nhan, dv]) => (
              <label className="rl-hang" key={k}>
                <span>{nhan}</span>
                <input type="number" step="any" value={String(dat[k] ?? '')}
                       onChange={e => datD(k, e.target.value === '' ? 0
                                              : +e.target.value)} />
                <em>{dv}</em>
              </label>
            ))}
            <div className="rl-nho">
              Spread <b>0</b> = lấy trung vị đo được lúc tải nến
              {khoNen?.spread_tb ? ` (${khoNen.spread_tb} điểm)` : ''}. Đo được: spread
              bịa 20 điểm biến một chiến lược thua thành thắng.
            </div>
          </NutPanel>

          <NutPanel ten="Ngân sách" icon={IR.ngan} rong={380}
                    nhan={gioToiDa ? `${gioToiDa}h` : soLuot.toLocaleString('vi-VN')}>
            <label className="rl-hang">
              <span>số sơ đồ thử</span>
              <input type="number" min={1} max={500000} value={soLuot}
                     onChange={e => setSoLuot(+e.target.value)} />
            </label>
            <label className="rl-hang">
              <span>giữ lại đầu bảng</span>
              <input type="number" min={1} max={100} value={giu}
                     onChange={e => setGiu(+e.target.value)} />
            </label>
            <label className="rl-hang">
              <span>hạt giống</span>
              <input type="number" value={hat} onChange={e => setHat(+e.target.value)} />
            </label>
            <p className="rl-nho">
              Cùng hạt giống + cùng dữ liệu = <b>cùng kết quả</b>, luôn luôn. Không thế
              thì "cách này hơn cách kia" là câu không kiểm được.
            </p>

            <div className="rl-nhom-ten"><span>Dừng sớm</span></div>
            <label className="rl-hang">
              <span>chạy tối đa</span>
              <input type="number" min={0} step={0.5} placeholder="không giới hạn"
                     value={gioToiDa ?? ''}
                     onChange={e => setGioToiDa(
                       e.target.value === '' ? null : +e.target.value)} />
              <em>giờ</em>
            </label>
            <p className="rl-nho">
              Chạy qua đêm thì đặt <b>giờ</b> hợp lý hơn đặt số lượt: chi phí mỗi sơ đồ
              dao động 3–24 giây tuỳ nó đẻ ra bao nhiêu lệnh, nên "10.000 sơ đồ" không
              dịch được ra mấy tiếng.
            </p>
            <label className="rl-hang">
              <span>dừng khi phẳng</span>
              <input type="number" min={0} placeholder="không dừng"
                     value={phangToiDa ?? ''}
                     onChange={e => setPhangToiDa(
                       e.target.value === '' ? null : +e.target.value)} />
              <em>lượt</em>
            </label>
            <p className="rl-nho">
              Ngần này lượt liền mà điểm tốt nhất không nhúc nhích thì tự tắt — bản tự
              động của thứ đồ thị đang mách bằng mắt.
            </p>
          </NutPanel>
        </Nhom>
      </div>

      {loi && <div className="rl-loi">{loi}</div>}

      {/* ------------------------------ DASHBOARD ------------------------------ */}
      <div className="rl-bang-dieu-khien">
        <section className="rl-o rl-tien">
          {!tt ? (
            <div className="rl-trong">chưa chạy lượt nào — bấm ▶ Chạy</div>
          ) : (
            <>
              <div className="rl-dau">
                <b>{tt.ten}</b>
                <span className="rl-phu">
                  {tt.dang_chay ? (tt.chu || 'đang chạy')
                    : tt.dung_giua_chung ? 'đã dừng giữa chừng'
                    /* VÌ SAO NGỪNG — "xong" trống không thì không biết nó chạy đủ
                       số lượt, hết giờ, hay tự tắt vì phẳng. */
                    : (tk?.vi_sao_ngung || 'xong')}
                  {' · '}{khoang(tt.bat_dau, tt.xong_luc)}
                </span>
              </div>
              {tt.loi && <div className="rl-loi">{tt.loi}</div>}
              <div className="rl-thanh">
                <div className="rl-thanh-day" style={{
                  width: `${tt.tong ? (tt.da_chay / tt.tong) * 100 : 0}%` }} />
              </div>
              <div className="rl-so-hang">
                <div><b>{tt.da_chay}</b><em>đã chấm / {tt.tong}</em></div>
                <div><b>{tt.diem_tot_nhat === null ? '—' : so(tt.diem_tot_nhat, 4)}</b>
                  <em>điểm tốt nhất</em></div>
                <div><b>{dauBang.length}</b><em>đang giữ</em></div>
                {/* CÒN BAO LÂU — đo thật trên lô đang chạy. Không ước bằng số nến:
                    cùng số nến mà sơ đồ này 3 giây, sơ đồ kia 24 giây (§18.4). */}
                {dangChay && tt.con_lai != null && (
                  <div><b>{lau(tt.con_lai)}</b>
                    <em>còn lại · {so(tt.giay_moi_luot, 1)}s/sơ đồ</em></div>
                )}
                {tk && <div><b>
                  {tk.da_chay ? Math.round(tk.khong_lenh / tk.da_chay * 100) : 0}%
                </b><em>không vào lệnh</em></div>}
              </div>
            </>
          )}
        </section>

        <section className="rl-o rl-plot">
          <div className="rl-plot-dau">
            Điểm tốt nhất theo số sơ đồ đã chấm
            <span>còn tìm được gì nữa không — dừng được chưa</span>
          </div>
          {tt ? (
            <DuongDiem duong={tt.duong || []} daCham={tt.da_chay} tong={tt.tong}
                       dangChay={dangChay} />
          ) : <div className="rl-plot-trong">chưa chạy lượt nào</div>}
        </section>

        <section className="rl-o rl-plot">
          <ChuaCo ten="Chuỗi tuần của sơ đồ đầu bảng"
                  hoi={'"nó có ĐỀU không". Một dãy cột tuần xanh/đỏ — nhìn phát biết nó '
                       + 'kiếm đều hay ăn một cú rồi nằm im.'} />
        </section>
      </div>

      <BangDuoi tabs={tabs} />
    </div>
  )
}
