import { memo } from 'react'

export interface BangCat {
  /** Nhóm do `kho/` khai, hàng do SƠ ĐỒ quyết. `nhom` KHÔNG được in ra — xem dưới. */
  nhom: { nhom: string; dong: { ten: string; phu: string; gia_tri: unknown }[] }[]
  lenh: {
    id: string; huong: string; da_khop: boolean
    loai: string; gia_dat: number | null
    gia_vao: number | null; sl: number | null; tp: number | null
    lai_R: number | null; sl_hoa_von: boolean
  }[]
}

/** BẢNG SỐ LIỆU bên phải — đúng những toán hạng SƠ ĐỒ ĐANG DÙNG, chạy số sống.
 *
 * ⚠ HAI LẦN SỬA, GHI LẠI CẢ HAI VÌ LẦN SAU DỄ LẶP:
 *
 * 1. Bản đầu có một khối `Vùng nén (engine)` VIẾT CỨNG ở file này. Hôm nay nó đúng vì
 *    chiến lược mẫu là D_02; mai làm chiến lược khác là bảng nói dối. Đã bỏ: danh sách
 *    giờ do Python suy TỪ SƠ ĐỒ (`core.toan_hang_dung`).
 *
 * 2. Nhưng nhóm vẫn được IN RA, và `VÙNG NÉN` đứng ngang hàng với CHỈ BÁO / TÀI KHOẢN /
 *    GIÁ — ba cái kia là phạm trù phổ quát, cái đó là khái niệm riêng của một chiến
 *    lược. Người dùng: *"tôi không thích gọi là vùng nén vì đây không tổng quát"*.
 *    Nên giờ **tên nhóm không in ra nữa**: `nhom` chỉ còn dùng để biết CHỖ KẺ một đường
 *    mảnh. Không tiêu đề nào thì không tiêu đề nào sai được — chiến lược nào sau này
 *    cũng đúng. Cấu trúc vẫn còn vì danh sách vốn xếp theo thứ tự sơ đồ đọc, nên các số
 *    cùng loại tự nằm cạnh nhau.
 *
 * Nhãn tách làm hai cột: tên chính, rồi `phu` (`M15·50·SMA`) mờ hơn nằm đúng vào cái
 * khe giữa nhãn và số — chỗ trước đây bỏ không, và cũng là lý do tên dài bị cắt cụt.
 *
 * "Lệnh đang sống" cố ý ĐỨNG NGOÀI cơ chế trên: nhóm toán hạng "Lệnh này" không có MỘT
 * giá trị tại nến i — Manage chạy một lượt cho MỖI lệnh. Ép thành một con số là bảng bắt
 * đầu nói khác nhật ký, đúng lúc đang debug (core.md §12.9). Mỗi lệnh HAI DÒNG: dòng
 * trên là tình trạng, dòng dưới là ba mức giá đủ số — một dòng 5 cột thì số bị cắt thành
 * `2643.0…`, đọc ra một con số vô nghĩa.
 *
 * Mọi con số ở đây do Python đọc từ CỘT đã ghi lúc chạy, không phải hỏi lại sổ lệnh — sổ
 * đang ở trạng thái cuối backtest, hỏi lại thì con trỏ nào cũng ra một đáp án.
 */
/** ⚠ BỌC `memo` ở cuối file — `k` chỉ đổi mỗi lần làm mới (một phút một lần ở Live),
 *  còn cửa sổ thì vẽ lại mỗi giây. */
function BangSoLieu({ k, digits }: { k: BangCat | null; digits: number }) {
  if (!k) return <div className="bang-trong">chưa chạy</div>

  const so = (v: unknown) => {
    if (v === null || v === undefined) return '—'
    if (typeof v === 'boolean') return v ? 'đúng' : 'sai'
    if (typeof v === 'string') return v
    if (typeof v !== 'number') return '—'
    return Number.isInteger(v) ? String(v) : v.toFixed(Math.max(2, digits))
  }
  const gia = (v: number | null) => (v === null ? '—' : v.toFixed(digits))

  return (
    <div className="bang-so-lieu">
      <table className="bang-toan-hang"><tbody>
        {k.nhom.map((g, gi) => g.dong.map((d, di) => (
          <tr key={g.nhom + d.ten}
              className={gi > 0 && di === 0 ? 'sang-nhom' : undefined}>
            {/* `title` vì tên rất dài vẫn có thể bị cắt — rê chuột là đọc đủ. */}
            <td className="ten" title={d.ten}>{d.ten}</td>
            <td className="phu">{d.phu}</td>
            <td className="gt">{so(d.gia_tri)}</td>
          </tr>
        )))}
      </tbody></table>

      <div className="bang-lenh-khoi">
        <div className="bang-ten">
          Lệnh đang sống <span className="dem">{k.lenh.length}</span>
        </div>
        {k.lenh.length === 0
          ? <div className="bang-rong">không có lệnh nào</div>
          : k.lenh.map(l => (
            <div className={'the-lenh' + (l.da_khop ? '' : ' cho')} key={l.id}>
              <div className="d1">
                <span className={l.huong === 'mua' ? 'mua' : 'ban'}>
                  {l.huong === 'mua' ? '▲' : '▼'}
                </span>
                <span className="ma">{l.id}</span>
                <span className="tt">
                  {l.da_khop ? 'đã khớp' : `chờ ${l.loai === 'limit' ? 'Limit' : 'Stop'}`}
                </span>
                <span className={'r ' + ((l.lai_R ?? 0) >= 0 ? 'lai' : 'lo')}>
                  {l.lai_R == null ? '' : `${l.lai_R.toFixed(2)} R`}
                </span>
              </div>
              <div className="d2">
                <span><i>{l.da_khop ? 'vào' : 'đặt'}</i>{gia(l.da_khop ? l.gia_vao : l.gia_dat)}</span>
                <span><i>SL</i>{gia(l.sl)}
                  {/* Chấm hoà vốn nằm cạnh SL chứ không cạnh id: nó nói về SL. */}
                  {l.sl_hoa_von && <b className="cham" title="SL đã ở hoà vốn" />}
                </span>
                <span><i>TP</i>{gia(l.tp)}</span>
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}

export default memo(BangSoLieu)
