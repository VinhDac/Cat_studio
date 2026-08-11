import { useEffect, useMemo, useRef, useState } from 'react'
import ContextMenu from '../components/ContextMenu'

export interface DongNk {
  i: number; j: number; co_viec: boolean; lenh_id: string | null; chu: string
}

/** Một DÃY dòng giống hệt nhau nằm liền nhau, gộp thành một. */
interface Nhom {
  i: number                 // lượt ĐẦU của dãy — chỗ con trỏ sẽ nhảy tới
  j0: number; j1: number    // nến M1 đầu và cuối của dãy
  co_viec: boolean
  chu: string
  dem: number
}

/** NHẬT KÝ SỐNG — dòng nảy lên đúng lúc nó xảy ra. (Vỏ bảng nằm ở `BangDuoi`.)
 *
 * Khác bản trước (một danh sách tĩnh cuộn được): lúc PHÁT, nó phải tự chạy theo con
 * trỏ. Đó là cả điểm của việc "đọc journey sống" — thấy dòng `đặt Buy Stop` hiện ra
 * đúng nhịp mà lệnh chờ xuất hiện trên chart.
 *
 * Chữ do PYTHON dựng (`nhat_ky.dung_lo_theo_nen`), JS không ghép mẩu nào. Chỉ giữ ~400
 * dòng gần nhất trong DOM — đổ cả 135.000 dòng vào là treo hẳn WebView2.
 *
 * ⭐ GỘP DÃY LẶP là thứ đáng giá nhất ở đây. Manage chạy nhịp M1 nên MỖI nến M5 đẻ ra 5
 * dòng y hệt nhau: 296 dòng trên màn hình thật ra chỉ là ~60 sự việc, và người dùng phải
 * cuộn qua một bức tường chữ giống nhau để tìm dòng có nghĩa. Gộp lại kèm `×3` vừa gọn
 * 5 lần, vừa TRẢ LỜI THÊM được câu "cổng đó chặn mấy lượt liền" — thứ mà đếm tay không
 * ra. Chỉ gộp dãy LIỀN KỀ, không gộp cách quãng: gộp cách quãng là xáo trộn thứ tự thật.
 */
export default function Journey({ dong, jBayGio, nhay, soi, chiViec }: {
  dong: DongNk[]
  /** Nến M1 con trỏ đang đứng — quyết định dòng nào được tô sáng. */
  jBayGio: number
  nhay: (i: number) => void
  /** Kéo cửa sổ vẽ lên trước và tô đường lượt này đã đi. */
  soi: (i: number) => void
  chiViec: boolean
}) {
  const boc = useRef<HTMLDivElement>(null)

  /** Dòng đang mở menu chuột phải. Giữ cả `i` chứ không chỉ toạ độ: mọi dòng trông
   *  giống nhau, nên phải TÔ dòng đang bị tác động — mở menu mà không biết nó thuộc
   *  dòng nào thì cái bấm nhầm chỉ dời đi một bước chứ không mất. */
  const [menu, setMenu] = useState<{ x: number; y: number; i: number; chu: string } | null>(null)

  const nhom = useMemo(() => {
    const ra: Nhom[] = []
    for (const d of dong) {
      if (chiViec && !d.co_viec) continue
      const cuoi = ra[ra.length - 1]
      // Dòng CÓ VIỆC không bao giờ bị gộp: hai lần đặt lệnh giống chữ nhau vẫn là hai
      // việc khác nhau, gộp lại là giấu mất một cái.
      if (cuoi && !d.co_viec && !cuoi.co_viec && cuoi.chu === d.chu) {
        cuoi.dem++
        cuoi.j1 = d.j
      } else {
        ra.push({ i: d.i, j0: d.j, j1: d.j, co_viec: d.co_viec, chu: d.chu, dem: 1 })
      }
    }
    return ra
  }, [dong, chiViec])

  /** Nhóm được tô sáng: nhóm GẦN NHẤT tính tới con trỏ, không phải nhóm "trùng đúng nến
   *  hiện tại". Entry chỉ chạy ở biên nến M5 nên 4/5 khung hình không sinh dòng nào —
   *  lấy mốc trùng khít thì phần lớn thời gian màn hình chẳng có gì sáng, mà câu người
   *  dùng cần trả lời là "gần đây nhất chiến lược làm gì", luôn có đáp án. */
  const sang = useMemo(() => {
    let k = -1
    for (let x = 0; x < nhom.length; x++) if (nhom[x].j0 <= jBayGio) k = x
    return k
  }, [nhom, jBayGio])

  /* Luôn cuộn xuống cuối khi danh sách đổi. Không sợ giật lúc người ta đang đọc: đang
     DỪNG thì không có dòng mới nào sinh ra, nên `dong` không đổi. Còn sau khi nhảy tới
     một sự kiện thì dòng cuối CHÍNH LÀ sự kiện đó — phải thấy nó ngay. */
  useEffect(() => {
    if (boc.current) boc.current.scrollTop = boc.current.scrollHeight
  }, [nhom])

  /* ⚠ Bấm TRÁI không nhảy con trỏ nữa — phải chuột phải rồi chọn.
   *
   * Nhật ký là thứ để ĐỌC: cuộn, dò, quét mắt. Mà cả danh sách là một bức tường dòng
   * cao 20px giống hệt nhau, nên chỉ cần trượt tay một chút là mất chỗ đang xem và
   * phải tua lại — một cú lỡ tay xoá luôn ngữ cảnh vừa dựng. Nhảy con trỏ là việc
   * NẶNG (dựng lại chart, nạp lô mới), việc nặng thì phải cố ý mới gọi được.
   *
   * Chuột phải không bao giờ bị bấm nhầm, và menu còn cho biết mình sắp làm gì. */
  return (
    <div className="nk-cuon" ref={boc}>
      {nhom.map((n, k) => (
        <div key={n.i}
             className={'nk-dong' + (n.co_viec ? ' co-viec' : '')
                        + (k === sang ? ' bay-gio' : '')
                        + (menu?.i === n.i ? ' dang-menu' : '')}
             onContextMenu={e => {
               e.preventDefault()
               setMenu({ x: e.clientX, y: e.clientY, i: n.i, chu: n.chu })
             }}>
          <span className="chu">{n.chu}</span>
          {n.dem > 1 && <span className="lap" title={`${n.dem} lượt liền nhau giống hệt`}>
            ×{n.dem}
          </span>}
        </div>
      ))}

      {menu && (
        <ContextMenu x={menu.x} y={menu.y} onDong={() => setMenu(null)}
                     muc={[
                       // KHÔNG dùng icon `dau`: trên thanh công cụ nó đang mang nghĩa
                       // "về sự kiện trước". Một hình hai nghĩa là hỏng cả hai.
                       { ten: 'Nhảy tới đây', icon: 'dat-co',
                         onClick: () => nhay(menu.i) },
                       // Câu hỏi ngay sau "chuyện gì đã xảy ra" luôn là "chỗ nào trên
                       // sơ đồ". Dò tay 20 hộp mất cả phút; cái này nối thẳng hai đầu.
                       { ten: 'Xem trên sơ đồ', icon: 'branch',
                         onClick: () => soi(menu.i) },
                       { ngan: true },
                       // Nhật ký là thứ hay phải mang đi hỏi/đối chiếu. Không chép được
                       // thì chỉ còn cách gõ tay lại một dòng mono dài.
                       { ten: 'Chép dòng', icon: 'copy',
                         onClick: () => void navigator.clipboard?.writeText(menu.chu) },
                     ]} />
      )}
    </div>
  )
}
