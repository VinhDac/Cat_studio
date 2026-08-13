/** Ô SỐ — hai hàm thuần, không phụ thuộc React.
 *
 *  Ở riêng một file vì chúng phải KIỂM ĐƯỢC BẰNG MÁY (`webui/kiem/o_so.mjs`). Lỗi ở đây
 *  chỉ lộ khi gõ TỪNG PHÍM — dán `1.5` một phát thì lọt — nên nếu chúng nằm trong một
 *  component thì phải dựng cả DOM mới canh nổi, mà như thế thì bài kiểm sẽ không bao
 *  giờ được viết.
 */

/** Lọc một lượt gõ trong ô số.
 *
 *  `so === null` nghĩa là chuỗi còn DỞ DANG (`""`, `"-"`, `"1."`): giữ nguyên trong ô,
 *  CHƯA đẩy lên tài liệu.
 *
 *  ⚠ Vì sao phải có trạng thái dở dang: ép `Number()` ngay từng phím thì `"1."` ra `1`,
 *  state không đổi, React ghi đè ô về `"1"` — dấu chấm biến mất, phím kế cho `"15"`.
 *  Stop Loss 1,5 × ATR lặng lẽ thành 15 × ATR. Đã xảy ra thật.
 *
 *  Và cũng không đẩy chuỗi dở dang lên tài liệu được: ở đó một CHUỖI nghĩa là TÊN THAM
 *  SỐ, nên `ChuongTrinh.so("1.")` sẽ ném "tham số không có trong bảng".
 */
export function locSo(tho: string, nguyen = false): { chu: string; so: number | null } {
  let t = tho.replace(nguyen ? /[^\d]/g : /[^\d.-]/g, '')
  if (!nguyen) {
    const am = t.startsWith('-')
    const p = t.replace(/-/g, '').split('.')
    t = (am ? '-' : '') + p.shift() + (p.length ? '.' + p.join('') : '')
  }
  const xong = t !== '' && t !== '-' && !t.endsWith('.')
  return { chu: t, so: xong ? Number(t) : null }
}

/** Chốt một bản nháp dở dang khi rời ô: `""` `"-"` `"1."` → con số gần nhất đọc được. */
export function chotSo(nhap: string): number {
  const n = Number(nhap.replace(/\.$/, ''))
  return Number.isFinite(n) ? n : 0
}
