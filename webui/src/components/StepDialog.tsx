import { useCallback, useEffect, useState } from 'react'
import { py } from '../api'
import type { Bootstrap, Step } from '../types'
import Modal from './Modal'
import ActionDialog from './ActionDialog'
import Icon, { ICON_HANH_DONG } from './Icon'

/** Hộp thoại sửa một Vòng theo dõi / một Nhóm 1 lần.
 *
 *  Hai loại dùng CHUNG khung này, Nhóm chỉ tắt bớt: không số nến, không khung thời
 *  gian, không mốc "lặp từ đây" — vì Nhóm chạy đúng một lượt nên mấy thứ đó vô nghĩa.
 */

type HD = Record<string, any>

/** Bộ nhớ tạm Ctrl+C/Ctrl+V cho HÀNH ĐỘNG, tách hẳn khỏi bộ nhớ chép KHỐI ngoài canvas. */
let boNho: HD[] = []

export default function StepDialog({ step, boot, onLuu, onDong }: {
  step: Step
  boot: Bootstrap
  onLuu: (s: Step) => void
  onDong: () => void
}) {
  const laLoop = step.kind === 'loop'
  const [s, setS] = useState<Step>(() => JSON.parse(JSON.stringify(step)))
  const [dong, setDong] = useState<{ text: string; type?: string | null }[]>([])
  const [chonDs, setChonDs] = useState<number[]>([])
  const chon = chonDs.length ? chonDs[chonDs.length - 1] : -1
  const [suaHD, setSuaHD] = useState<{ i: number; a: HD } | null>(null)
  /** Ngăn hoàn tác RIÊNG của hộp thoại, không dính gì tới Ctrl+Z ngoài canvas: ngoài
   *  đó hoàn tác việc thêm/xoá/nối KHỐI, trong đây là thêm/xoá/xếp lại HÀNH ĐỘNG.
   *  Trộn chung thì Ctrl+Z trong hộp thoại lại làm biến mất một khối phía sau. */
  const [lui, setLui] = useState<Step[]>([])
  const [toi, setToi] = useState<Step[]>([])

  const hd: HD[] = (s.actions as HD[]) ?? []
  const batDau = Math.max(0, Math.min(Number(s.loop_start_index ?? 0), hd.length))

  /* Chữ trên từng dòng do PYTHON sinh — JS không ghép lại lần thứ hai. */
  const lamMoi = useCallback(() => {
    py.describe_actions(hd).then(r => r.ok && setDong(r.value ?? []))
  }, [hd])
  useEffect(() => { lamMoi() }, [lamMoi])

  const dat = (k: string, v: unknown) => setS(x => ({ ...x, [k]: v }))

  const chup = () => {
    setLui(l => [...l.slice(-49), JSON.parse(JSON.stringify(s))])
    setToi([])
  }
  /** Mọi thay đổi danh sách hành động đi qua ĐÚNG MỘT chỗ này — thêm, sửa, xoá, dán,
   *  lên/xuống. Đặt `chup()` ở đây thì không thể sót thao tác nào. */
  const datHD = (x: HD[]) => { chup(); setS(o => ({ ...o, actions: x })) }

  const hoanTac = () => {
    if (!lui.length) return
    setToi(t => [...t, JSON.parse(JSON.stringify(s))])
    setS(lui[lui.length - 1])
    setLui(l => l.slice(0, -1))
    setChonDs([])          // chỉ số cũ có thể trỏ vào hành động không còn nữa
  }
  const lamLai = () => {
    if (!toi.length) return
    setLui(l => [...l, JSON.parse(JSON.stringify(s))])
    setS(toi[toi.length - 1])
    setToi(t => t.slice(0, -1))
    setChonDs([])
  }

  async function them() {
    const r = await py.action_defaults(boot.action_types[0])
    setSuaHD({ i: -1, a: r.value ?? { type: boot.action_types[0] } })
  }

  function luuHD(a: HD) {
    if (!suaHD) return
    datHD(suaHD.i < 0 ? [...hd, a] : hd.map((x, k) => (k === suaHD.i ? a : x)))
    setSuaHD(null)
  }

  function bamDong(i: number, ev: React.MouseEvent) {
    if (ev.ctrlKey || ev.metaKey) {
      setChonDs(d => (d.includes(i) ? d.filter(k => k !== i) : [...d, i]))
    } else if (ev.shiftKey && chon >= 0) {
      const [a, b] = [Math.min(chon, i), Math.max(chon, i)]
      setChonDs(Array.from({ length: b - a + 1 }, (_, k) => a + k))
    } else {
      setChonDs([i])
    }
  }

  function doiCho(huong: -1 | 1) {
    if (chon < 0) return
    const j = chon + huong
    if (j < 0 || j >= hd.length) return
    const x = [...hd]
    ;[x[chon], x[j]] = [x[j], x[chon]]
    datHD(x)
    setChonDs([j])
  }

  return (
    <>
      <Modal title={`${laLoop ? 'Vòng theo dõi' : 'Nhóm 1 lần'} — ${s.name ?? ''}`}
             width={820} onClose={onDong}
             footer={
               <>
                 <button className="nut" onClick={hoanTac} disabled={!lui.length}
                         title="Hoàn tác trong hộp thoại này">↶</button>
                 <button className="nut" onClick={lamLai} disabled={!toi.length}>↷</button>
                 <div className="chen" />
                 <button className="nut" onClick={onDong}>Huỷ</button>
                 <button className="nut chinh" onClick={() => onLuu(s)}>Lưu</button>
               </>
             }>

        <label className="hang">
          <span className="nhan-o">Tên</span>
          <input className="o" value={String(s.name ?? '')}
                 onChange={e => dat('name', e.target.value)} />
          {laLoop && (
            <>
              <span className="nhan-o phu">Khung TG</span>
              <select className="o nho" value={String(s.tf ?? '')}
                      title="Để trống = dùng khung thời gian chính của chiến lược"
                      onChange={e => dat('tf', e.target.value)}>
                <option value="">(chính)</option>
                {boot.timeframes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <span className="nhan-o phu">Tối đa</span>
              <input className="o so nho" value={String(s.max_nen ?? boot.default_max_nen)}
                     title="Chạy quá chừng này nến mà chưa thoả thì bỏ cuộc"
                     onChange={e => dat('max_nen', parseInt(e.target.value) || 1)} />
              <span className="goi-y">nến</span>
            </>
          )}
        </label>

        <div className="ds-hanh-dong">
          {hd.length === 0 && <div className="dong rong">chưa có hành động nào</div>}
          {hd.map((_, i) => (
            <div key={i}
                 className={'dong-hd' + (chonDs.includes(i) ? ' dang-chon' : '')
                            + (laLoop && i < batDau ? ' mo-dau' : '')}
                 onClick={e => bamDong(i, e)}
                 onDoubleClick={() => setSuaHD({ i, a: hd[i] })}>
              <span className="danh">{laLoop ? (i < batDau ? '1×' : '↻') : ''}</span>
              <Icon name={ICON_HANH_DONG[dong[i]?.type ?? ''] ?? ''} size={13} />
              <span className="chu">{dong[i]?.text ?? '…'}</span>
            </div>
          ))}
        </div>

        <div className="hang nut-hang">
          <button className="nut" onClick={them}>+ Thêm</button>
          <button className="nut" disabled={chon < 0}
                  onClick={() => setSuaHD({ i: chon, a: hd[chon] })}>Sửa</button>
          <button className="nut" disabled={!chonDs.length}
                  onClick={() => { boNho = chonDs.map(i => hd[i]) }}>Chép</button>
          <button className="nut" disabled={!boNho.length}
                  onClick={() => datHD([...hd, ...JSON.parse(JSON.stringify(boNho))])}>
            Dán
          </button>
          <button className="nut" disabled={chon < 0} onClick={() => doiCho(-1)}>↑</button>
          <button className="nut" disabled={chon < 0} onClick={() => doiCho(1)}>↓</button>
          <button className="nut" disabled={!chonDs.length}
                  onClick={() => {
                    datHD(hd.filter((_, i) => !chonDs.includes(i)))
                    setChonDs([])
                  }}>Xoá</button>
          {laLoop && (
            <button className="nut" disabled={chon < 0}
                    title={'Các dòng PHÍA TRÊN chỉ chạy 1 lần lúc đầu; từ dòng này trở '
                           + 'xuống mới lặp lại theo từng nến.'}
                    onClick={() => { chup(); dat('loop_start_index', chon) }}>
              ↻ Lặp từ đây
            </button>
          )}
        </div>
      </Modal>

      {suaHD && (
        <ActionDialog action={suaHD.a} boot={boot}
                      onLuu={luuHD} onDong={() => setSuaHD(null)} />
      )}
    </>
  )
}
