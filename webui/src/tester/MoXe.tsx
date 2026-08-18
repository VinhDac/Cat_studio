import { useCallback, useEffect, useState } from 'react'
import { pyTester } from '../api'
import type { PhanBo, ThuBo } from '../types'

/** MỔ XẺ — tiền ra từ khối nào, cổng chặn cái gì, và bỏ một nhánh đi thì sao.
 *
 *     core.md §18.5b, §18.5c
 *
 * ⭐ **Đây là chỗ MỘT con số của cả sơ đồ tách thành một con số cho MỖI khối.** Trước
 * tab này, người vẽ chỉ biết *"sơ đồ tôi lỗ 10,31 R"* — biết mình lỗ mà không biết lỗ ở
 * đâu, nên sửa gì cũng là đoán. Đo trên chính sơ đồ mẫu: −10,28 trong số −10,31 ấy đến
 * từ ĐÚNG một nhánh.
 *
 * ⚠ **Nút "thử bỏ" KHÔNG bao giờ trả về một con số gộp**, và đó là chỗ đã trả giá để
 * học: cắt nhánh BÁN của sơ đồ mẫu cho `+0,3872` trên quý 2024-Q1 — rất thuyết phục và
 * SAI, vì xét sáu quý thì chỉ 4/6 quý bỏ đi là tốt hơn. Một cửa sổ đủ để kết luận sai.
 * Nên ở đây luôn là **từng quý một, kèm số quý tốt hơn**.
 */
export default function MoXe({ sanSang }: { sanSang: boolean }) {
  const [pb, setPb] = useState<PhanBo | null>(null)
  const [loi, setLoi] = useState('')
  const [dangThu, setDangThu] = useState<string | null>(null)
  const [thu, setThu] = useState<Record<string, ThuBo | { loi: string }>>({})

  useEffect(() => {
    if (!sanSang) return
    setThu({})
    pyTester.test_phan_bo().then(r => {
      if (r.ok && r.value) { setPb(r.value); setLoi('') } else setLoi(r.error || '')
    })
  }, [sanSang])

  const thuBo = useCallback(async (khoi: string) => {
    setDangThu(khoi)
    const r = await pyTester.test_thu_bo(khoi)
    setThu(t => ({ ...t, [khoi]: r.ok && r.value ? r.value : { loi: r.error || 'hỏng' } }))
    setDangThu(null)
  }, [])

  if (loi) return <div className="mx-trong">{loi}</div>
  if (!pb) return <div className="mx-trong">chưa chạy lần nào</div>

  return (
    <div className="mx">
      <div className="mx-nhac">
        Mỗi dòng là <b>một phần của sơ đồ</b>, không phải cả sơ đồ. Bấm
        {' '}<b>thử bỏ</b> để cắt nhánh ấy đi rồi chạy lại — kết quả hiện
        {' '}<b>theo từng quý</b>, cố ý không gộp thành một số.
      </div>

      <div className="mx-ten">TIỀN RA TỪ ĐÂU</div>
      {pb.tien.length === 0 ? <div className="mx-trong">sơ đồ không có khối Vào lệnh nào</div> : (
        <table className="mx-bang">
          <thead><tr>
            <th>khối</th><th>đến</th><th>lệnh</th><th>đã đóng</th>
            <th>tiền $</th><th>R</th><th>thắng/thua</th><th />
          </tr></thead>
          <tbody>
            {pb.tien.map(x => (
              <Hang key={x.khoi} khoi={x.khoi} thu={thu[x.khoi]} dang={dangThu === x.khoi}
                    onThu={thuBo} cot={9}>
                <td className="mx-trai">{x.nhan}</td>
                <td>{x.den.toLocaleString('vi-VN')}</td>
                <td>{x.so_lenh}</td>
                <td>{x.da_dong}</td>
                <td className={x.tien < 0 ? 'xau' : 'tot'}>{x.tien.toFixed(2)}</td>
                <td className={x.tong_R < 0 ? 'xau' : 'tot'}>{x.tong_R.toFixed(2)}</td>
                <td>{x.thang}/{x.thua}</td>
              </Hang>
            ))}
          </tbody>
        </table>
      )}

      <div className="mx-ten">CỔNG CHẶN CÁI GÌ</div>
      <table className="mx-bang">
        <thead><tr>
          <th>cổng</th><th>xét</th><th>khớp</th><th>tỉ lệ</th><th>ghi chú</th><th />
        </tr></thead>
        <tbody>
          {pb.cong.map(x => (
            <Hang key={x.khoi} khoi={x.khoi} thu={thu[x.khoi]} dang={dangThu === x.khoi}
                  onThu={thuBo} cot={7}>
              <td className="mx-trai">{x.nhan}</td>
              <td>{x.xet.toLocaleString('vi-VN')}</td>
              <td>{x.khop.toLocaleString('vi-VN')}</td>
              <td>{x.ty_le === null ? '—' : `${(x.ty_le * 100).toFixed(1)}%`}</td>
              <td className="mx-trai mx-nho">
                {!x.xet ? 'chưa bao giờ được xét'
                  : x.luon_chan ? 'LUÔN CHẶN — mọi khối dưới là trang trí'
                  : x.luon_khop ? (x.zone
                      ? 'luôn khớp, nhưng là cổng ZONE — nó vẫn nuôi vùng nén, KHÔNG bỏ được'
                      : 'luôn khớp — có thể thừa')
                  : ''}
              </td>
            </Hang>
          ))}
        </tbody>
      </table>

      {pb.chac_bo_duoc.length > 0 && (
        <>
          <div className="mx-ten">CHẮC CHẮN BỎ ĐƯỢC</div>
          <div className="mx-nhac">
            Dòng chảy <b>chưa bao giờ tới</b> mấy khối này, nên gỡ ra là kết quả không
            đổi một xu — không cần chạy lại để biết.
          </div>
          {pb.chac_bo_duoc.map(x => (
            <div className="mx-chet" key={x.khoi}><b>{x.nhan}</b><span>{x.vi_sao}</span></div>
          ))}
        </>
      )}
    </div>
  )
}

/** Một hàng + phần bung ra khi đã thử bỏ. */
function Hang({ khoi, thu, dang, onThu, cot, children }: {
  khoi: string
  thu?: ThuBo | { loi: string }
  dang: boolean
  onThu: (k: string) => void
  cot: number
  children: React.ReactNode
}) {
  return (
    <>
      <tr>
        {children}
        <td>
          <button className="nut-nho" disabled={dang} onClick={() => onThu(khoi)}
                  title="Cắt nhánh này rồi chạy lại, so theo từng quý">
            {dang ? 'đang chạy…' : 'thử bỏ'}
          </button>
        </td>
      </tr>
      {thu && (
        <tr><td colSpan={cot} className="mx-ket">
          {'loi' in thu ? <span className="xau">{thu.loi}</span> : <KetQuaBo t={thu} />}
        </td></tr>
      )}
    </>
  )
}

function KetQuaBo({ t }: { t: ThuBo }) {
  const da = t.tot_hon * 2 > t.so_cua_so
  return (
    <div className="mx-bo">
      <div className={'mx-chot' + (da ? ' tot' : '')}>
        bỏ nhánh này thì <b>tốt hơn ở {t.tot_hon}/{t.so_cua_so} quý</b>
        {!t.con_lenh && (
          <em> ⚠ cắt xong KHÔNG còn lệnh nào — mấy con số này là so với việc đứng ngoài
            thị trường, không phải so hai chiến lược</em>
        )}
      </div>
      <div className="mx-quy">
        {t.cua_so.map(w => (
          <span key={w.tu} className={'mx-o ' + (w.chenh > 0 ? 'tot' : w.chenh < 0 ? 'xau' : '')}
                title={`${w.tu} → ${w.den}\ntrước ${w.truoc}  ·  sau ${w.sau}`}>
            <i>{w.tu.slice(0, 7)}</i>
            <b>{w.chenh > 0 ? '+' : ''}{w.chenh.toFixed(3)}</b>
          </span>
        ))}
      </div>
      <div className="mx-nho">
        cả dải: điểm {t.truoc.diem} → {t.sau.diem} · lệnh {t.truoc.so_lenh} → {t.sau.so_lenh}
        {' · '}⚠ con số gộp này <b>không</b> dùng để quyết — xem hàng quý ở trên.
      </div>
    </div>
  )
}
