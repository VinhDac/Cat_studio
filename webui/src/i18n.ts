/** NGÔN NGỮ GIAO DIỆN — một cơ chế cho cả app, mọi cửa sổ.
 *
 *     core.md §18.14
 *
 * ⭐ **KHOÁ CHÍNH LÀ CÂU TIẾNG VIỆT.** `chu('Chạy')` chứ không phải `chu('ribbon.run')`.
 * Ba thứ được nhờ đó, và cả ba đều đáng hơn cái đẹp của một hệ khoá:
 *
 * ```
 * không phải bịa khoá     — 1.500 câu là 1.500 lần đặt tên, và đặt tên sai thì sửa gấp đôi
 * dịch được TỪNG PHẦN     — câu chưa có trong từ điển thì hiện nguyên tiếng Việt, không vỡ
 * đọc mã vẫn hiểu         — `chu('Chưa chạy lượt nào')` nói ngay nó vẽ ra cái gì
 * ```
 *
 * ⚠ Nên **KHÔNG BAO GIỜ sửa câu tiếng Việt mà quên sửa từ điển** — sửa một dấu phẩy là
 * câu ấy rơi về tiếng Việt trong bản tiếng Anh, im lặng. `tests/test_ngon_ngu.py` canh
 * đúng chuyện đó: mọi khoá trong từ điển phải còn tìm thấy trong mã nguồn.
 *
 * ⚠ Và chữ trên HỘP KHỐI thì KHÔNG đi qua đây — nó do Python sinh (`core.action_display`,
 * `cond_display`), vì §12.9 cấm giao diện tự ghép câu. Muốn dịch nó thì phải dịch ở
 * Python, và ngôn ngữ đi theo cài đặt chung `ngon_ngu`, không phải hai nguồn.
 */
import { useSyncExternalStore } from 'react'

import { EN } from './i18n_en'

export type Ngon = 'vi' | 'en'

let ngon: Ngon = 'vi'
const nghe = new Set<() => void>()

/** Đổi ngôn ngữ. Mọi component đang dùng `useT()` vẽ lại ngay — không cần mở lại app. */
export function datNgon(n: Ngon) {
  if (n === ngon) return
  ngon = n === 'en' ? 'en' : 'vi'
  document.documentElement.lang = ngon
  nghe.forEach(f => f())
}

export function layNgon(): Ngon {
  return ngon
}

/** Dịch một câu. Không có trong từ điển → trả NGUYÊN câu tiếng Việt (không nổ, không rỗng). */
export function chu(s: string): string {
  return ngon === 'en' ? (EN[s] ?? s) : s
}

function dangKy(f: () => void) {
  nghe.add(f)
  return () => {
    nghe.delete(f)
  }
}

/** ⚠ VÌ SAO TÊN LÀ `chu` CHỨ KHÔNG PHẢI `t`: `t` đã là tên biến cục bộ ở vài chỗ —
 *  `(['entry','manage'] as Tab[]).map(t => …)` trong Ribbon, và một `Record` tên `t`
 *  trong hộp thoại Cài đặt. Trình biên dịch bắt được ngay, nhưng NÉ một cái tên rẻ hơn
 *  nhiều so với đi đổi biến của mã người ta đang dùng — và `chu('Chạy')` đọc rõ đúng
 *  bằng `t('Chạy')`.

/** Hook cho chỗ cần biết ngôn ngữ hiện tại (định dạng số, ngày…). */
export function useNgon(): Ngon {
  return useSyncExternalStore(dangKy, layNgon, layNgon)
}

/** Mã vùng cho `toLocaleString` — số và ngày phải theo cùng ngôn ngữ, không thì bản
 *  tiếng Anh vẫn hiện `1.234,5` kiểu Việt. */
export function vung(): string {
  return ngon === 'en' ? 'en-US' : 'vi-VN'
}
