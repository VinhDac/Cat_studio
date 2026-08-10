import { useEffect, useMemo, useState } from 'react'
import { py } from '../api'
import type { Bootstrap, Tab, ThamSo, ToanHang } from '../types'
import Modal from './Modal'

/** Hộp thoại sửa MỘT hành động.
 *
 *  Hộp thoại này KHÔNG tự soát lỗi: nó gửi bản nháp thô sang `api.save_action`, Python
 *  chuẩn hoá rồi trả về câu mô tả + danh sách lỗi. Nhờ vậy luật hợp lệ chỉ nằm ở đúng
 *  một chỗ (`core.validate_actions`), và dòng chữ xem trước ở đây chắc chắn là đúng
 *  cái lõi thực sự hiểu — chứ không phải bản dịch thứ hai do JS ghép.
 */

type HD = Record<string, any>

/* ---------- ô chọn TOÁN HẠNG (dùng cho cả vế trái lẫn vế phải) ---------- */

function OToanHang({ o, boot, tab, dat, hep }: {
  o: HD; boot: Bootstrap; tab: Tab; dat: (v: HD) => void; hep?: boolean
}) {
  /* Gom theo nhóm để dropdown 30 mục còn đọc được. `<optgroup>` giữ đúng thứ tự Python
     gửi sang — nhóm nào trước là do `core.TOAN_HANG` quyết, không phải JS sắp lại.
     Nhóm "Lệnh này" chỉ hiện ở Manage: ở Entry chưa có lệnh nào để nói tới, nên bày ra
     chỉ tổ mời người dùng chọn một thứ sẽ báo lỗi ngay sau đó. */
  const nhom = useMemo(() => {
    const m = new Map<string, ToanHang[]>()
    for (const t of boot.toan_hang) {
      if (tab === 'entry' && t.nhom === boot.nhom_lenh_nay) continue
      if (!m.has(t.nhom)) m.set(t.nhom, [])
      m.get(t.nhom)!.push(t)
    }
    return [...m.entries()]
  }, [boot.toan_hang, boot.nhom_lenh_nay, tab])

  const dinh = boot.toan_hang.find(t => t.key === o?.ten)
  const ts = dinh?.tham_so ?? []
  const sua = (k: string, v: unknown) => dat({ ...o, [k]: v })

  return (
    <div className={'cum-toan-hang' + (hep ? ' hep' : '')}>
      <select className="o" value={o?.ten ?? ''}
              onChange={e => {
                // Đổi toán hạng thì mấy tham số của cái CŨ phải rơi đi: giữ lại
                // `period` của ATR khi vừa đổi sang "Giờ" là để rác trong file.
                const moi = boot.toan_hang.find(t => t.key === e.target.value)
                const g: HD = { ten: e.target.value }
                for (const k of moi?.tham_so ?? []) {
                  if (k === 'tf') g.tf = o?.tf ?? boot.timeframes[1] ?? 'M5'
                  if (k === 'period') g.period = o?.period ?? 14
                  if (k === 'method') g.method = o?.method ?? 'SMA'
                  if (k === 'shift') g.shift = o?.shift ?? 1
                  if (k === 'ten_co') g.ten_co = o?.ten_co ?? ''
                }
                dat(g)
              }}>
        <option value="">— chọn —</option>
        {nhom.map(([g, ds]) => (
          <optgroup key={g} label={g}>
            {ds.map(t => <option key={t.key} value={t.key}>{t.nhan}</option>)}
          </optgroup>
        ))}
      </select>

      {ts.includes('tf') && (
        <select className="o nho" value={o?.tf ?? ''} title="Khung thời gian"
                onChange={e => sua('tf', e.target.value)}>
          {boot.timeframes.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      )}
      {ts.includes('period') && (
        <input className="o so nho" value={o?.period ?? ''} title="Chu kỳ (số nến)"
               onChange={e => sua('period', parseInt(e.target.value) || 0)} />
      )}
      {ts.includes('method') && (
        <select className="o nho" value={o?.method ?? 'SMA'} title="Kiểu trung bình"
                onChange={e => sua('method', e.target.value)}>
          {Object.entries(boot.ma_methods).map(([k, v]) =>
            <option key={k} value={k} title={v}>{k}</option>)}
        </select>
      )}
      {ts.includes('shift') && (
        <input className="o so nho" value={o?.shift ?? 1}
               title={'Nến thứ mấy tính từ hiện tại. Dùng 1 = nến ĐÃ ĐÓNG. '
                      + 'Nến 0 còn đang chạy nên tín hiệu sẽ vẽ lại.'}
               onChange={e => sua('shift', parseInt(e.target.value) || 0)} />
      )}
      {ts.includes('ten_co') && (
        <input className="o nho" value={o?.ten_co ?? ''} placeholder="tên cờ"
               onChange={e => sua('ten_co', e.target.value)} />
      )}
    </div>
  )
}

/* ---------- ô nhập một KHOẢNG CÁCH GIÁ ---------- */

function OKhoang({ k, boot, dat, nhan, goiY }: {
  k: HD | undefined; boot: Bootstrap; dat: (v: HD | undefined) => void
  nhan: string; goiY?: string
}) {
  return (
    <label className="hang">
      <span className="nhan-o">{nhan}</span>
      {k ? (
        <>
          <input className="o so nho" value={k.value ?? ''}
                 onChange={e => dat({ ...k, value: parseFloat(e.target.value) })} />
          <select className="o" value={k.tinh ?? ''}
                  onChange={e => dat({ ...k, tinh: e.target.value })}>
            {Object.entries(boot.cach_tinh).map(([kk, v]) =>
              <option key={kk} value={kk}>{v}</option>)}
          </select>
          <button className="nut nho" onClick={() => dat(undefined)} title="Bỏ">✕</button>
        </>
      ) : (
        <button className="nut nho" onClick={() => dat({ tinh: 'theo_ATR', value: 1 })}>
          + đặt
        </button>
      )}
      {goiY && <span className="goi-y">{goiY}</span>}
    </label>
  )
}

/* ---------- một dòng ĐIỀU KIỆN ---------- */

function DongDieuKien({ c, boot, tab, thamSo, dat, xoa, so }: {
  c: HD; boot: Bootstrap; tab: Tab; thamSo: ThamSo[]
  dat: (v: HD) => void; xoa: () => void; so: number
}) {
  const dinh = boot.toan_hang.find(t => t.key === c?.trai?.ten)
  // Toán hạng vốn đã đúng/sai thì không có vế phải — "Lệnh này đã khớp = 1" là câu
  // không ai đọc được. Danh sách do PYTHON gửi sang, JS không tự chép lại.
  const dungSai = boot.toan_hang_dung_sai.includes(c?.trai?.ten)

  return (
    <div className="dong-dk">
      <span className="so-dk">{so}</span>
      <OToanHang o={c.trai ?? {}} boot={boot} tab={tab} dat={v => dat({ ...c, trai: v })} />

      {dungSai ? (
        <label className="tick" title="Đảo lại: điều kiện đúng khi việc này KHÔNG xảy ra">
          <input type="checkbox" checked={!!c.dao}
                 onChange={e => dat({ ...c, dao: e.target.checked })} />
          KHÔNG
        </label>
      ) : (
        <>
          <select className="o nho phep" value={c.phep ?? '<'}
                  onChange={e => dat({ ...c, phep: e.target.value })}>
            {Object.entries(boot.phep_so).map(([k, v]) =>
              <option key={k} value={k}>{v}</option>)}
          </select>

          <select className="o nho" value={c.phai_loai ?? 'so'}
                  title={'Vế phải: số gõ tay · THAM SỐ có tên · hay một toán hạng khác. '
                         + 'Ngưỡng dùng ở hai chỗ thì nên là tham số — gõ tay hai nơi '
                         + 'là sửa một chỗ sẽ lệch âm thầm.'}
                  onChange={e => dat({
                    ...c, phai_loai: e.target.value,
                    phai: e.target.value === 'toan_hang' ? {}
                      : e.target.value === 'tham_so' ? (thamSo[0]?.ten ?? '') : 0,
                  })}>
            <option value="so">số</option>
            <option value="tham_so" disabled={!thamSo.length}>tham số</option>
            <option value="toan_hang">toán hạng</option>
          </select>

          {c.phai_loai === 'tham_so' ? (
            <select className="o" value={String(c.phai ?? '')}
                    onChange={e => dat({ ...c, phai: e.target.value })}>
              {thamSo.map(t => (
                <option key={t.ten} value={t.ten}>
                  {t.ten} = {t.gia_tri}{t.don_vi ? ` ${t.don_vi}` : ''}
                </option>
              ))}
            </select>
          ) : c.phai_loai === 'toan_hang' ? (
            <OToanHang o={c.phai ?? {}} boot={boot} tab={tab} hep
                       dat={v => dat({ ...c, phai: v })} />
          ) : (
            <>
              <input className="o so nho" value={c.phai ?? ''}
                     onChange={e => dat({ ...c, phai: parseFloat(e.target.value) })} />
              {c.phep === 'trong_khoang' && (
                <input className="o so nho" value={c.phai2 ?? ''} placeholder="đến"
                       onChange={e => dat({ ...c, phai2: parseFloat(e.target.value) })} />
              )}
            </>
          )}
        </>
      )}

      <button className="nut nho xoa-dk" onClick={xoa} title="Xoá điều kiện này">✕</button>
      {dinh && <div className="chu-thich-dk">{dinh.nhom}</div>}
    </div>
  )
}

/* ---------------------------------- hộp thoại --------------------------------- */

export default function ActionDialog({ action, boot, tab, thamSo, onLuu, onDong }: {
  action: HD
  boot: Bootstrap
  tab: Tab
  thamSo: ThamSo[]
  onLuu: (a: HD) => void
  onDong: () => void
}) {
  /** Loại hành động dùng được ở tab này. Entry chỉ TẠO, Manage chỉ SỬA. */
  const loaiChoPhep = boot.action_types.filter(t => boot.action_tabs[t]?.includes(tab))
  const [a, setA] = useState<HD>(() => JSON.parse(JSON.stringify(action)))
  const [xem, setXem] = useState('')
  const [loi, setLoi] = useState<string[]>([])

  const dat = (k: string, v: unknown) => setA(x => ({ ...x, [k]: v }))

  /* Xem trước + soát lỗi do PYTHON trả về, hoãn 200ms để gõ số không bắn liên tục
     qua cầu nối. */
  useEffect(() => {
    const h = setTimeout(async () => {
      const r = await py.save_action(a, tab, thamSo)
      if (r.ok) {
        setXem(r.value?.display ?? '')
        setLoi(((r as any).loi as string[]) ?? [])
      } else {
        setXem(''); setLoi([r.error ?? 'không đọc được hành động'])
      }
    }, 200)
    return () => clearTimeout(h)
  }, [a, tab, thamSo])

  async function doiLoai(t: string) {
    // Lấy mặc định từ Python chứ không tự nặn ở JS: mấy con số mặc định
    // (ATR 14, ngưỡng 7 bps, SL 1.5×ATR) là kiến thức về chiến lược, thuộc về lõi.
    const r = await py.action_defaults(t)
    setA({ ...(r.value ?? { type: t }), name: a.name })
  }

  const conds: HD[] = a.conditions ?? []

  return (
    <Modal title={`Hành động — ${boot.action_labels[a.type] ?? a.type}`} width={880}
           onClose={onDong}
           footer={
             <>
               <div className="xem-truoc" title="Đúng câu mà lõi hiểu về hành động này">
                 {xem || '…'}
               </div>
               <button className="nut" onClick={onDong}>Huỷ</button>
               <button className="nut chinh" onClick={() => onLuu(a)}>Lưu</button>
             </>
           }>

      <label className="hang">
        <span className="nhan-o">Loại</span>
        <select className="o" value={a.type} onChange={e => doiLoai(e.target.value)}>
          {loaiChoPhep.map(t =>
            <option key={t} value={t}>{boot.action_labels[t]}</option>)}
        </select>
        <span className="nhan-o phu">Tên</span>
        <input className="o" value={a.name ?? ''} placeholder="(để trống = dùng tên loại)"
               onChange={e => dat('name', e.target.value)} />
      </label>

      {/* ------------------------------ Kiểm tra điều kiện ---------------------- */}
      {a.type === 'check_cond' && (
        <div className="khoi-form">
          <div className="chu-dan">
            Mọi dòng phải cùng đúng thì mới khớp (<b>VÀ</b>). Muốn <b>HOẶC</b> thì tách
            ra thành hai nhánh riêng trên sơ đồ — nhìn sơ đồ là thấy được, còn chữ
            "hoặc" giấu trong hộp thoại thì không.
          </div>
          {conds.map((c, i) => (
            <DongDieuKien key={i} c={c} boot={boot} tab={tab} thamSo={thamSo} so={i + 1}
                          dat={v => dat('conditions',
                            conds.map((x, k) => (k === i ? v : x)))}
                          xoa={() => dat('conditions', conds.filter((_, k) => k !== i))} />
          ))}
          {!conds.length && (
            <div className="dong rong">chưa có điều kiện nào — hành động này sẽ luôn khớp</div>
          )}
          <button className="nut" onClick={() => dat('conditions', [...conds, {
            trai: { ten: 'atr_bps', tf: boot.timeframes[1] ?? 'M5', period: 14 },
            phep: '<', phai_loai: 'so', phai: 7,
          }])}>+ Thêm điều kiện</button>
        </div>
      )}

      {/* ------------------------------ Vào lệnh -------------------------------- */}
      {a.type === 'vao_lenh' && (
        <div className="khoi-form">
          <label className="hang">
            <span className="nhan-o">Hướng</span>
            {Object.entries(boot.huong).map(([k, v]) => (
              <label key={k} className="tick">
                <input type="radio" name="huong" checked={a.huong === k}
                       onChange={() => dat('huong', k)} />{v}
              </label>
            ))}
            <span className="nhan-o phu">Loại lệnh</span>
            <select className="o" value={a.loai ?? 'stop'}
                    onChange={e => dat('loai', e.target.value)}>
              {Object.entries(boot.loai_lenh).map(([k, v]) =>
                <option key={k} value={k}>{v}</option>)}
            </select>
            <span className="nhan-o phu">Lot</span>
            <input className="o so nho" value={a.lot ?? ''}
                   onChange={e => dat('lot', parseFloat(e.target.value))} />
          </label>

          {(a.loai === 'stop' || a.loai === 'limit') && (
            <OKhoang nhan="Đệm" k={a.dem} boot={boot} dat={v => dat('dem', v)}
                     goiY="đẩy giá đặt ra ngoài mép vùng — lá chắn chống phá giả" />
          )}
          <OKhoang nhan="Stop Loss" k={a.sl} boot={boot} dat={v => dat('sl', v)}
                   goiY="khoảng cách này chính là 1R" />
          <OKhoang nhan="Take Profit" k={a.tp} boot={boot} dat={v => dat('tp', v)}
                   goiY="thường đặt theo bội của R" />

          <div className="chu-dan">
            SL/TP đặt ở đây là <b>ban đầu</b>. Khối <b>Sửa lệnh</b> phía sau chỉ để
            DỜI chúng — không có SL ngay từ lúc vào là để ngỏ cả tài khoản.
          </div>
        </div>
      )}

      {/* ------------------------------ Sửa lệnh -------------------------------- */}
      {a.type === 'sua_lenh' && (
        <div className="khoi-form">
          <label className="hang">
            <span className="nhan-o">Chế độ</span>
            <select className="o" value={a.che_do ?? 'doi_sl'}
                    onChange={e => dat('che_do', e.target.value)}>
              {Object.entries(boot.sua_che_do).map(([k, v]) =>
                <option key={k} value={k}>{v}</option>)}
            </select>
          </label>

          {boot.sua_can_gia.includes(a.che_do) && (
            <OKhoang nhan="Khoảng cách mới" k={a.khoang} boot={boot}
                     dat={v => dat('khoang', v)} />
          )}

          {a.che_do === 'hoa_von' && (
            <div className="chu-dan">
              Không có tham số: chế độ này chỉ đặt <b>SL = giá vào</b>. Mốc kích hoạt
              (lãi đủ mấy R) và câu hỏi <b>"đã dời chưa"</b> thuộc về <b>cổng phía
              trước</b> — chỗ nhìn thấy được. D_02 giấu cả ba trong <code>ManageBreakEven</code>.
            </div>
          )}

          {boot.sua_can_phan_tram.includes(a.che_do) && (
            <label className="hang">
              <span className="nhan-o">Đóng</span>
              <input className="o so nho" value={a.phan_tram ?? ''}
                     onChange={e => dat('phan_tram', parseFloat(e.target.value))} />
              <span className="goi-y">% khối lượng — muốn đóng hết thì chọn "Đóng hẳn"</span>
            </label>
          )}
        </div>
      )}

      {loi.length > 0 && (
        <div className="loi-form">
          {loi.map((m, i) => <div key={i}>✖ {m}</div>)}
        </div>
      )}
    </Modal>
  )
}
