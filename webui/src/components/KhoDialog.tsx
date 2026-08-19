import { chu, useNgon } from '../i18n'
import { useEffect, useMemo, useState } from 'react'
import { py } from '../api'
import type { KhoDanhMuc } from '../types'
import Modal from './Modal'

/** Hộp thoại KHO — "app đang có những gì".
 *
 *  Dữ liệu do `kho/` bên Python tự gom từ các module con, nên thêm một engine mới là
 *  hộp thoại có ngay — KHÔNG có danh sách nào viết cứng ở đây. Đó là điểm mấu chốt:
 *  một cái kho mà phải cập nhật bằng tay thì sớm muộn nó nói khác thực tế.
 */

const TEN_TAB: Record<string, string> = { entry: 'Entry', manage: 'Manage' }

function Muc({ ten, phu, children }: {
  ten: string; phu?: string; children: React.ReactNode
}) {
  return (
    <div className="kho-muc">
      <div className="kho-dau">
        <span className="kho-ten">{ten}</span>
        {phu && <span className="kho-phu">{phu}</span>}
      </div>
      {children}
    </div>
  )
}

export default function KhoDialog({ onDong }: { onDong: () => void }) {
  useNgon()   // đổi ngôn ngữ → vẽ lại (xem `i18n.ts`)
  const [d, setD] = useState<KhoDanhMuc | null>(null)
  const [loi, setLoi] = useState('')

  useEffect(() => {
    py.kho_danh_muc().then(r => (r.ok ? setD(r.value!) : setLoi(r.error ?? chu('lỗi'))))
  }, [])

  /** Gom toán hạng theo NGUỒN rồi tới NHÓM — nhìn ra ngay thứ gì luôn có, thứ gì
   *  đến từ một chiến lược cụ thể. */
  const theoNguon = useMemo(() => {
    if (!d) return []
    return d.module.map(m => ({
      m,
      nhom: [...new Map(
        d.toan_hang.filter(t => t.nguon === m.ma_so)
          .map(t => [t.nhom, d.toan_hang.filter(
            x => x.nguon === m.ma_so && x.nhom === t.nhom)]),
      ).entries()],
      chi_bao: d.chi_bao.filter(c => c.nguon === m.ma_so),
      bang: d.bang_trang_thai.filter(b => b.nguon === m.ma_so),
    }))
  }, [d])

  return (
    <Modal title={chu("Kho — app đang có những gì")} width={900} onClose={onDong}
           footer={<button className="nut chinh" onClick={onDong}>{chu('Đóng')}</button>}>
      {loi && <div className="loi-form">✖ {loi}</div>}
      {!d && !loi && <div className="dong rong">{chu('đang đọc…')}</div>}

      {d && (
        <div className="kho">
          <div className="chu-dan">
            Danh sách này do Python <b>{chu('tự gom')}</b> {chu('từ thư mục')} <code>kho/</code>. Thêm một
            chiến lược mới = thêm một file vào đó, và mục dưới đây có ngay — không có
            danh sách nào chép tay, nên nó không thể nói khác thực tế.
          </div>

          {theoNguon.map(({ m, nhom, chi_bao, bang }) => (
            <Muc key={m.ma_so}
                 ten={m.ten}
                 phu={m.nguon ? chu('có nguồn') : chu('dùng chung')}>
              <div className="kho-mota">{m.mo_ta}</div>
              {m.nguon && <div className="kho-nguon">{chu('nguồn:')} <code>{m.nguon}</code></div>}

              {chi_bao.length > 0 && (
                <table className="kho-bang">
                  <thead><tr><th>{chu('Chỉ báo')}</th><th>{chu('Tham số')}</th><th>{chu('Công thức')}</th></tr></thead>
                  <tbody>
                    {chi_bao.map(c => (
                      <tr key={c.key}>
                        <td>{c.nhan}</td>
                        <td className="mono">{c.tham_so.join(' · ') || '—'}</td>
                        <td className="kho-mota">{c.cong_thuc ?? ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {nhom.map(([g, ds]) => (
                <table className="kho-bang" key={g}>
                  <thead><tr>
                    <th>Toán hạng · {g}</th><th>{chu('Tham số')}</th><th>{chu('Dùng ở')}</th>
                  </tr></thead>
                  <tbody>
                    {ds.map(t => (
                      <tr key={t.key}>
                        <td title={t.mo_ta}>{t.nhan}
                          {t.dung_sai && <span className="kho-cheo">{chu('đúng/sai')}</span>}</td>
                        <td className="mono">{t.tham_so.join(' · ') || '—'}</td>
                        <td>{t.tabs ? t.tabs.map(x => TEN_TAB[x]).join(', ') : chu('cả hai')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ))}

              {bang.map(b => (
                <div key={b.key} className="kho-bang-tt">
                  <div className="kho-dau2">Bảng trạng thái · {b.nhan}</div>
                  <div className="kho-mota">{b.mo_ta}</div>
                  <table className="kho-bang">
                    <thead><tr><th>{chu('Trường')}</th><th>{chu('Kiểu')}</th><th>{chu('Ghi chú')}</th></tr></thead>
                    <tbody>
                      {b.truong.map(t => (
                        <tr key={t.ten}>
                          <td className="mono">{t.ten}</td><td>{t.kieu}</td>
                          <td className="kho-mota">{t.vd}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <ul className="kho-luat">
                    {b.luat.map((l, i) => <li key={i}>{l}</li>)}
                  </ul>
                </div>
              ))}
            </Muc>
          ))}

          <Muc ten={chu("Hành động")} phu={chu("Entry chỉ TẠO · Manage chỉ SỬA")}>
            <table className="kho-bang">
              <thead><tr><th>{chu('Hành động')}</th><th>{chu('Dùng ở sơ đồ')}</th></tr></thead>
              <tbody>
                {d.hanh_dong.map(h => (
                  <tr key={h.key}>
                    <td>{h.nhan}</td>
                    <td>{h.tabs.map(x => TEN_TAB[x]).join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Muc>

          <Muc ten={chu("Từ vựng")} phu={chu("phép so · cách tính khoảng cách · chế độ Sửa lệnh")}>
            <div className="kho-chip">
              {Object.entries(d.phep_so).map(([k, v]) =>
                <span key={k} className="the">{v}</span>)}
            </div>
            <div className="kho-chip">
              {Object.entries(d.don_vi).map(([k, v]) =>
                <span key={k} className="the">{v}</span>)}
            </div>
            <div className="kho-chip">
              {Object.entries(d.sua_che_do).map(([k, v]) =>
                <span key={k} className="the">{v}</span>)}
            </div>
          </Muc>

          <Muc ten={chu("Sổ lệnh")} phu={chu("id của ta, không mượn ticket MT5")}>
            <div className="chu-dan">
              Mỗi lệnh mang một id <code>L-0001</code> {chu('và nhớ')} <code>zone_id</code> đẻ ra
              nó. Nhờ vậy <b>{chu('“vùng này đã sinh lệnh”')}</b> chỉ là một phép tra bảng, và
              không phải đoán như <code>HasOpenPosition()</code> của D_02.
              <code>ticket</code> của MT5 chỉ là một cột phụ, để trống khi backtest.
            </div>
            <table className="kho-bang">
              <thead><tr><th>{chu('Trạng thái lệnh')}</th><th>{chu('Nghĩa')}</th></tr></thead>
              <tbody>
                {Object.entries(d.trang_thai_lenh).map(([k, v]) => (
                  <tr key={k}><td className="mono">{k}</td><td>{v}</td></tr>
                ))}
              </tbody>
            </table>
            <div className="kho-chip">
              {Object.entries(d.ly_do_dong).map(([k, v]) =>
                <span key={k} className="the">{v}</span>)}
            </div>
          </Muc>

          <Muc ten={chu("Lưu trữ")} phu={d.luu_tru.goc}>
            <table className="kho-bang">
              <thead><tr><th>{chu('Mục')}</th><th>{chu('Số lượng')}</th><th>{chu('Đường dẫn')}</th></tr></thead>
              <tbody>
                {d.luu_tru.muc.map(m => (
                  <tr key={m.ten}>
                    <td>{m.ten}
                      {m.danh_sach.length > 0 &&
                        <div className="kho-mota">{m.danh_sach.join(' · ')}</div>}
                    </td>
                    <td>{m.so_luong}</td>
                    <td className="mono kho-mota">{m.duong_dan}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Muc>
        </div>
      )}
    </Modal>
  )
}
