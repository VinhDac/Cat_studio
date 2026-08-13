/* Ô SỐ — gõ TỪNG PHÍM, không phải dán một phát.
 *
 * Lỗi thật đã xảy ra: ép `Number()` ngay từng phím thì `"1."` ra `1`, state không đổi,
 * React ghi đè ô về `"1"` — dấu chấm biến mất, phím kế cho `"15"`. SL 1,5 × ATR thành
 * 15 × ATR, sai gấp mười, không một dòng cảnh báo. Dán `1.5` một phát thì LỌT, nên bài
 * kiểm phải mô phỏng đúng chuỗi phím.
 *
 * Chạy:  node webui/kiem/o_so.mjs
 */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

// Biên dịch ĐÚNG MỘT file `src/so.ts` (nó cố ý không import gì) rồi nạp bản .js.
// Không tự bóc chú thích kiểu bằng regex: bóc bằng tay là một bộ biên dịch thứ hai,
// và nó sẽ vỡ ngay lần đầu ai đó viết một chữ ký hơi khác.
const goc = new URL('..', import.meta.url).pathname.replace(/^\//, '')
const ra = mkdtempSync(join(tmpdir(), 'catso-'))
// `--skipLibCheck` + `--types` rỗng: chỉ dịch ĐÚNG file này, đừng lôi cả cây @types
// của node_modules vào (chúng có lỗi kiểu riêng, không liên quan gì tới ta).
try {
  execFileSync('npx', ['tsc', 'src/so.ts', '--target', 'es2020', '--module', 'es2020',
                       '--skipLibCheck', '--types', 'node', '--outDir', ra],
               { cwd: goc, stdio: 'pipe', shell: true })
} catch (e) {
  // tsc có thể thoát khác 0 vì lỗi kiểu ở nơi khác mà VẪN xuất ra file — chỉ hỏng thật
  // khi không có file nào để nạp.
  if (!existsSync(join(ra, 'so.js'))) {
    console.error(String(e.stdout ?? e))
    throw new Error('không dịch nổi src/so.ts')
  }
}
const { locSo, chotSo } = await import(pathToFileURL(join(ra, 'so.js')).href)

let dung = 0, sai = 0
const kiem = (ten, dk, chi = '') => {
  if (dk) { dung++; console.log(`  \u2714 ${ten} ${chi}`) }
  else { sai++; console.log(`  \u2718 ${ten} ${chi}`) }
}

/** Mô phỏng ô nhập có kiểm soát: gõ từng ký tự, React ghi đè ô theo state sau mỗi phím. */
function go(phim, nguyen = false) {
  let v = null            // giá trị THẬT (lên tài liệu)
  let nhap = null         // bản nháp trong ô
  for (const k of phim) {
    const truoc = nhap ?? (v ?? '')
    const { chu, so } = locSo(String(truoc) + k, nguyen)
    nhap = chu
    if (so !== null) v = so
  }
  // rời ô
  if (nhap !== null && locSo(nhap, nguyen).so === null) v = chotSo(nhap)
  return v
}

console.log('\n\u25b8 Gõ từng phím — số thập phân phải ra đúng')
for (const [phim, mong] of [['1.5', 1.5], ['0.05', 0.05], ['12.75', 12.75],
                            ['1.', 1], ['.5', 0.5], ['-2.5', -2.5], ['100', 100]]) {
  const ra = go(phim)
  kiem(`gõ "${phim}" \u2192 ${mong}`, ra === mong, ra === mong ? '' : `\u2014 RA ${ra}`)
}

console.log('\n\u25b8 Chữ không lọt, dấu chấm thứ hai không lọt')
kiem('gõ "1a.b5" \u2192 1.5', go('1a.b5') === 1.5, `\u2014 ${go('1a.b5')}`)
kiem('gõ "1.2.3" \u2192 1.23 (chấm thứ hai bị nuốt)', go('1.2.3') === 1.23, `\u2014 ${go('1.2.3')}`)
kiem('ô CHU KỲ chỉ nhận số nguyên: "1.5" \u2192 15', go('1.5', true) === 15, `\u2014 ${go('1.5', true)}`)

console.log('\n\u25b8 Dán một phát vẫn phải đúng (đường này VỐN đã chạy được)')
kiem('dán "1.5"', locSo('1.5').so === 1.5)
kiem('dán "0.05"', locSo('0.05').so === 0.05)

console.log('\n\u25b8 Dở dang thì CHƯA đẩy lên tài liệu')
for (const t of ['', '-', '1.', '.']) {
  kiem(`"${t}" \u2192 chưa đẩy`, locSo(t).so === null, `\u2014 ${JSON.stringify(locSo(t))}`)
}

console.log(`\n${'\u2500'.repeat(56)}\n  ${dung} đúng \u00b7 ${sai} sai\n${'\u2500'.repeat(56)}`)
process.exit(sai ? 1 : 0)
