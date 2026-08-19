import { chu, useNgon } from '../i18n'
/** PHÂN BỐ dạng cột — thứ một con số trung bình không bao giờ nói được.
 *
 *     core.md §18.9c
 *
 * ⭐ Cả ba phân bố trên bàn điều khiển đều tồn tại vì một số đo cụ thể đã cho thấy
 * trung bình che mất chuyện quan trọng:
 *
 * ```
 * điểm    sơ đồ bốc bừa thua CÓ HỆ THỐNG (~2% dương đều, ngẫu nhiên là 65%)
 *         → hình dạng cả đống mới trả lời "không gian này có gì không"
 * số lệnh 28/60 sơ đồ không vào lệnh nào, một cái đẻ 11.425
 *         → "trung bình 3.000 lệnh" là một câu vô nghĩa
 * chi phí MỘT sơ đồ chiếm 60% cả lô 60 sơ đồ (§18.4d)
 *         → và đó là lý do "còn bao lâu" phải là một KHOẢNG
 * ```
 *
 * ⚠ Cột nào có số thì **luôn cao tối thiểu 2 px**. Một thùng có 3 mẫu trong tổng 5.000
 * mà vẽ cao 0 px thì đồ thị nói "không có gì ở đây" — mà cái đuôi mới là chỗ đáng nhìn
 * nhất, đúng chỗ mọi phát hiện của §18 nằm.
 */
export default function PhanBoCot({ ten, phu, mep, so, dv, tot }: {
  ten: string
  phu?: string
  /** Mép các thùng. `so` dài hơn `mep` đúng 1 — hai thùng ngoài là tràn hai đầu. */
  mep: readonly number[]
  so: number[]
  /** Chữ sau con số ở nhãn trục: `s`, `lệnh`… */
  dv?: string
  /** Từ thùng này trở lên thì tô màu "tốt" — dùng cho mốc 0 của phân bố điểm. */
  tot?: number
}) {
  useNgon()   // đổi ngôn ngữ → vẽ lại cả cây (xem `i18n.ts`)
  const tong = so.reduce((a, b) => a + b, 0)
  if (!tong) {
    return (
      <section className="rl-o pbc">
        <div className="pbc-dau"><b>{ten}</b>{phu && <span>{phu}</span>}</div>
        <div className="rl-plot-trong">{chu('chưa có số nào')}</div>
      </section>
    )
  }
  const dinh = Math.max(...so)
  return (
    <section className="rl-o pbc">
      <div className="pbc-dau"><b>{ten}</b>{phu && <span>{phu}</span>}</div>
      <div className="pbc-cot">
        {so.map((n, i) => (
          <div className="pbc-mot" key={i}
               title={`${nhan(mep, i, dv)} — ${n.toLocaleString('vi-VN')} sơ đồ`
                      + ` (${(n / tong * 100).toFixed(1)}%)`}>
            <span className="pbc-so">{n ? n.toLocaleString('vi-VN') : ''}</span>
            <div className={'pbc-thanh' + (tot !== undefined && i >= tot ? ' tot' : '')}
                 style={{ height: n ? `${Math.max(2, (n / dinh) * 100)}%` : '0' }} />
          </div>
        ))}
      </div>
      {/* Nhãn trục nằm NGOÀI vùng cột: để trong đó thì `overflow: hidden` của ô cắt
          mất sạch — đã mắc. Cột nhiều thì ghi thưa ra, một nhãn cách một. */}
      <div className="pbc-truc">
        {so.map((_, i) => (
          <span key={i}>{so.length > 8 && i % 2 ? '' : nhan(mep, i, dv)}</span>
        ))}
      </div>
    </section>
  )
}

/** Nhãn thùng thứ `i`. Hai thùng ngoài là tràn, ghi `<` và `≥`. */
function nhan(mep: readonly number[], i: number, dv = ''): string {
  const g = (x: number) => `${x}${dv}`
  if (i === 0) return `<${g(mep[0])}`
  if (i === mep.length) return `≥${g(mep[mep.length - 1])}`
  return g(mep[i - 1])
}
