import { chu, useNgon } from '../i18n'
import { useEffect, useMemo, useState } from 'react'
import { py } from '../api'
import type { Bootstrap, Tab, ThamSo, ToanHang } from '../types'
import Modal from './Modal'
import { chotSo, locSo } from '../so'

/** Hộp thoại sửa MỘT hành động.
 *
 *  Hộp thoại này KHÔNG tự soát lỗi: nó gửi bản nháp thô sang `api.save_action`, Python
 *  chuẩn hoá rồi trả về câu mô tả + danh sách lỗi. Nhờ vậy luật hợp lệ chỉ nằm ở đúng
 *  một chỗ (`core.validate_actions`), và dòng chữ xem trước ở đây chắc chắn là đúng
 *  cái lõi thực sự hiểu — chứ không phải bản dịch thứ hai do JS ghép.
 */

type HD = Record<string, any>

/* ---------- Ô SỐ — MỘT kiểu ô cho MỌI chỗ chờ một con số ---------- */

/** LUẬT DUY NHẤT: **gõ = số. Tên tham số thì KHÔNG gõ được — chỉ app đặt.**
 *
 *  Vì sao phải có luật này, và vì sao nó cố tình "ngu":
 *
 *  Python có đúng một quy ước — *"ở đâu chờ một con số, một CHUỖI nghĩa là tên tham
 *  số"*. Giao diện trước đây chỉ làm thật ở MỘT trong năm ô. Bốn ô còn lại (`chu kỳ`,
 *  `chỉ số nến`, `SL/TP/đệm`, `lot`) chạy `parseInt`/`parseFloat` nên **hiện ra một cái
 *  tên mà gõ vào là nuốt mất**: `chu_ky_atr` → `0`. Ô bên phải thì có `<datalist>` và
 *  placeholder *"số hoặc tên tham số"* — tức app dạy "chỗ này gõ tên được" ở một ô rồi
 *  phá lời dạy đó ở bốn ô kia. Người dùng nhìn ô thứ ba đang hiện `chu_ky_atr` và tưởng
 *  đấy là chỗ ĐẶT TÊN. Không trách được.
 *
 *  Nên ô này bỏ hẳn khả năng gõ chữ. Không phải dán nhãn giải thích — mà làm cho việc
 *  gõ tên **bất khả thi**. Còn tên ở đâu ra? Đúng MỘT đường: bảng Vấn đề thấy một con
 *  số gõ tay ở hai chỗ → nút "Đặt tên cho số này" (`core._soat_so_lap`). Khối thứ ba chỉ
 *  cần gõ lại con số ấy là luật "cùng giá trị → dùng lại" gộp nó về đúng cái tên cũ.
 *
 *  Đổi lại: gắn một tham số ĐÃ CÓ vào khối mới mất hai bước thay vì một. Chấp nhận, để
 *  giữ được "chỉ có MỘT đường cho một cái tên chui vào ô".
 */
function OSo({ v, dat, thamSo, donVi, lop, title, nguyen, tat }: {
  v: number | string | undefined
  dat: (x: number | string) => void
  thamSo: ThamSo[]
  /** ĐƠN VỊ CỦA Ô — `core.don_vi_cua_o`. Nút ▾ chỉ mời tham số mang ĐÚNG đơn vị này,
   *  nên `chu_ky_atr` (nến) không bao giờ hiện ra ở ô Stop Loss. */
  donVi?: string | null
  lop?: string
  title?: string
  /** Chu kỳ là số nến — chấp nhận chữ số, không dấu chấm. */
  nguyen?: boolean
  /** `mép zone đối diện` không dùng con số nào cả — khoá ô lại thay vì để gõ vô ích. */
  tat?: boolean
}) {
  /** Bản nháp đang gõ — `null` = ô đang hiển thị theo giá trị thật. Xem chú thích ở ô
   *  nhập bên dưới: ép về số từng phím là nuốt mất dấu chấm. */
  const [nhap, datNhap] = useState<string | null>(null)
  const laTen = typeof v === 'string' && v !== ''
  const ts = laTen ? thamSo.find(t => t.ten === v) : undefined
  // Chỉ những tham số ĐÚNG đơn vị của ô này. Đây là chỗ luật "một tham số một đơn vị"
  // trả công: danh sách luôn ngắn, và không bao giờ mời một con số sai nghĩa.
  const hop = donVi ? thamSo.filter(t => t.don_vi === donVi && t.ten !== v) : []

  if (tat) {
    return <span className="o so nho tat-hoan-toan" title={title}>—</span>
  }
  if (laTen) {
    return (
      <span className={'chip-ts' + (ts ? '' : ' mat') + (lop ? ' ' + lop : '')}
            title={ts
              ? `Tham số "${v}" = ${ts.gia_tri}`
                + (ts.don_vi ? ` (${ts.don_vi})` : '')
                + `
Bấm ✕ để quay lại gõ một con số.`
              : `Không còn tham số nào tên "${v}" trong bảng — bấm ✕ để gõ lại một số.`}>
        <span className="chip-ten">{v}</span>
        <button className="chip-x" title={chu("Bỏ tên, quay lại gõ số")}
                onClick={() => dat(ts ? Number(ts.gia_tri) : 0)}>✕</button>
      </span>
    )
  }
  return (
    <span className={'cum-so' + (lop ? ' ' + lop : '')}>
      {/* ⚠ BẢN NHÁP khi đang gõ. Không ép về số ngay từng phím, vì số DỞ DANG thì ép là
          MẤT KÝ TỰ: gõ `1` `.` `5` → `Number("1.")` ra `1` → state không đổi → React ghi
          đè ô về `"1"`, dấu chấm biến mất → phím `5` cho `"15"`. SL 1,5 × ATR thành
          15 × ATR, sai gấp mười, không một dòng cảnh báo. (Dán `1.5` một phát thì lọt,
          nên bài kiểm phải GÕ TỪNG PHÍM mới thấy.)

          Cũng không đẩy chuỗi dở dang lên tài liệu được: ở đó một CHUỖI nghĩa là tên
          tham số, và `ct.so("1.")` sẽ ném "tham số không có trong bảng". Nên bản nháp
          nằm lại trong ô, chỉ số HOÀN CHỈNH mới đi lên. */}
      <input className="o so nho" inputMode="decimal" spellCheck={false}
             value={nhap ?? (v ?? '')} title={title}
             onChange={e => {
               // Chữ không lọt vào được, nên không thể nhầm ô này với ô đặt tên.
               const { chu, so } = locSo(e.target.value, nguyen)
               datNhap(chu)
               if (so !== null) dat(so)
             }}
             onBlur={() => {
               // Rời ô thì bản nháp hết nhiệm vụ. Còn dở dang thì chốt về con số gần
               // nhất đọc được, chứ không để ô trống mang nghĩa mơ hồ.
               if (nhap !== null && locSo(nhap, nguyen).so === null) dat(chotSo(nhap))
               datNhap(null)
             }} />
      {/* Nút này CHỈ HIỆN khi có tham số dùng được. Không có thì ô sạch như cũ — đúng
          luật "chỉ bày ra thứ dùng được", áp cho chính cái nút chọn. */}
      {hop.length > 0 && (
        <select className="chon-ts" value=""
                title={chu("Dùng một tham số đã có thay cho con số này")}
                onChange={e => e.target.value && dat(e.target.value)}>
          <option value="">▾</option>
          {hop.map(t => (
            <option key={t.ten} value={t.ten}>{t.ten} = {t.gia_tri}</option>
          ))}
        </select>
      )}
    </span>
  )
}

/* ---------- ô chọn TOÁN HẠNG (dùng cho cả vế trái lẫn vế phải) ---------- */

function OToanHang({ o, boot, tab, dat, hep, thamSo, coZone, boDungSai }: {
  o: HD; boot: Bootstrap; tab: Tab; dat: (v: HD) => void; hep?: boolean
  thamSo: ThamSo[]
  /** Khối này có nằm SAU cổng zone không — Python trả trong `validate.luong`. */
  coZone: boolean
  /** Cơ chế "so hai đại lượng" không nhận toán hạng đúng/sai: `lệnh này đã khớp >
   *  zone_HH` không phải một câu. */
  boDungSai?: boolean
}) {
  /* Gom theo nhóm để dropdown còn đọc được. `<optgroup>` giữ đúng thứ tự Python gửi
     sang — nhóm nào trước là do `core.TOAN_HANG` quyết, không phải JS sắp lại.

     HAI phép lọc, cùng MỘT lý lẽ: đừng bày ra thứ chắc chắn sẽ báo lỗi.
       · nhóm "Lệnh này" ẩn ở Entry — chưa có lệnh nào để nói tới;
       · toán hạng zone ẩn ở khối CHƯA đi qua cổng zone — zone chưa tồn tại, hỏi nó thì
         `_soat_cong_zone` báo lỗi đỏ ngay sau đó.
     Phép thứ nhất đã có từ trước, phép thứ hai là áp nốt cùng luật. */
  const nhom = useMemo(() => {
    const m = new Map<string, ToanHang[]>()
    const canZone = new Set(boot.toan_hang_can_zone)
    for (const t of boot.toan_hang) {
      if (tab === 'entry' && t.nhom === boot.nhom_lenh_nay) continue
      // Cái ĐANG chọn thì luôn giữ lại — lọc mất nó đi thì ô hoá rỗng và người dùng
      // mất luôn thông tin mình đã chọn gì.
      if (!coZone && canZone.has(t.key) && t.key !== o?.ten) continue
      if (boDungSai && t.dung_sai && t.key !== o?.ten) continue
      if (!m.has(t.nhom)) m.set(t.nhom, [])
      m.get(t.nhom)!.push(t)
    }
    return [...m.entries()]
  }, [boot.toan_hang, boot.nhom_lenh_nay, boot.toan_hang_can_zone, tab, coZone,
      boDungSai, o?.ten])

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
                  if (k === 'ten_co') g.ten_co = o?.ten_co ?? ''
                }
                dat(g)
              }}>
        <option value="">{chu('— chọn —')}</option>
        {nhom.map(([g, ds]) => (
          <optgroup key={g} label={g}>
            {ds.map(t => <option key={t.key} value={t.key}>{t.nhan}</option>)}
          </optgroup>
        ))}
      </select>

      {/* ⚙ THAM SỐ CỦA CHÍNH TOÁN HẠNG ĐÓ — mỗi chỉ báo một menu riêng.
          Trước đây khung thời gian · chu kỳ · kiểu trung bình nằm thẳng trên hàng, nên
          vế trái phình từ 1 ô (`zone_dem`) tới 4 ô (MA) tuỳ bạn chọn gì — hàng lệch
          nhau, và thêm một chỉ báo 4 tham số là hỏng hẳn bố cục.
          Gom vào menu thì vế trái LUÔN một khối, mọi toán hạng như nhau. Không mất
          thông tin: thẻ trên canvas vẫn ghi đủ `ATR(M5, 14)` mà không phải bấm gì —
          sơ đồ được ĐỌC ở canvas, hộp thoại chỉ để SỬA.
          Và `method` (SMA/EMA) là chuyện riêng của MA, ATR không có: để mỗi chỉ báo
          giữ núm vặn của chính nó thì hàng ở ngoài mới generic được. */}
      {/* ⚠ Ô ⚙ LUÔN CHIẾM CHỖ, kể cả khi toán hạng chưa chọn hoặc không có tham số nào.
          Bản đầu chỉ vẽ khi `ts.length > 0`, mà 11/17 toán hạng không có tham số — nên
          NGAY TRONG một khối, dòng ATR có ⚙ còn dòng `Zone — số nến` không, hai ô chọn
          rộng khác nhau, cột lệch. Đúng cái vừa dọn cả buổi.
          Chừa chỗ nhưng KHÔNG vẽ nút chết: bề rộng không đổi, mà cũng không có cái
          bánh răng vô dụng nằm đó. Cùng cách ô đơn vị đang làm. */}
      {ts.length === 0 ? (
        <span className="menu-th trong" aria-hidden="true" />
      ) : (
        <details className="menu-th" onToggle={e => {
          // Đóng menu kia khi mở menu này — hai popover chồng nhau thì không đọc được.
          const el = e.currentTarget as HTMLDetailsElement
          if (!el.open) return
          el.closest('.dong-dk, .khoi-form')
            ?.querySelectorAll('details.menu-th[open]')
            .forEach(x => { if (x !== el) (x as HTMLDetailsElement).open = false })
        }}>
          <summary className="ctl-banh-rang"
                   title={'Cài đặt cho ' + (dinh?.nhan ?? chu('toán hạng này'))}>
            ⚙
          </summary>
          <div className="menu-th-noi">
            <div className="menu-th-dau">{dinh?.nhan}</div>
            {ts.includes('tf') && (
              <label className="menu-th-dong">
                <span>{chu('Khung thời gian')}</span>
                <select className="o nho" value={o?.tf ?? ''}
                        onChange={e => sua('tf', e.target.value)}>
                  {boot.timeframes.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
            )}
            {ts.includes('period') && (
              <label className="menu-th-dong">
                <span>{chu('Chu kỳ (nến)')}</span>
                <OSo v={o?.period} thamSo={thamSo} nguyen
                     donVi={boot.don_vi_o.chu_ky}
                     title={chu("Chu kỳ chỉ báo, tính bằng số nến.")}
                     dat={x => sua('period', x)} />
              </label>
            )}
            {ts.includes('method') && (
              <label className="menu-th-dong">
                <span>{chu('Kiểu trung bình')}</span>
                <select className="o nho" value={o?.method ?? 'SMA'}
                        onChange={e => sua('method', e.target.value)}>
                  {Object.entries(boot.ma_methods).map(([k, v]) =>
                    <option key={k} value={k} title={v}>{k}</option>)}
                </select>
              </label>
            )}
            {ts.includes('ten_co') && (
              <label className="menu-th-dong">
                <span>{chu('Tên cờ')}</span>
                <input className="o nho" value={o?.ten_co ?? ''}
                       onChange={e => sua('ten_co', e.target.value)} />
              </label>
            )}
          </div>
        </details>
      )}
    </div>
  )
}

/* ---------- ô nhập một KHOẢNG CÁCH GIÁ ---------- */

function OKhoang({ k, boot, dat, nhan, goiY, thamSo, oDau, coZone }: {
  k: HD | undefined; boot: Bootstrap; dat: (v: HD | undefined) => void
  nhan: string; goiY?: string; thamSo: ThamSo[]
  /** Ô này là chỗ nào: `dem` · `sl` · `tp` · `sua`. Quyết định danh sách đơn vị. */
  oDau: string
  coZone: boolean
}) {
  /* ⚠ Trước đây ô này bày ra CẢ BẢY đơn vị cho mọi chỗ, dù `core.DON_VI_CHO` đã chia
     sẵn từ lâu — nên SL mời chọn `× R` (đo rủi ro bằng chính rủi ro: vòng tròn), còn
     đệm mời chọn `mép zone đối diện` (không có mốc để đo tới). Ba phép lọc, cùng một
     lý lẽ "đừng bày thứ chắc chắn báo lỗi":
       · theo CHỖ DÙNG   — `DON_VI_CHO[oDau]`;
       · theo ZONE       — chưa qua cổng zone thì `× ATR zone` luôn NaN;
       · giữ cái ĐANG chọn, để lọc không xoá mất lựa chọn cũ của người dùng. */
  const ds = (boot.don_vi_cho[oDau] ?? Object.keys(boot.don_vi)).filter(
    d => d === k?.tinh || coZone || !boot.don_vi_can_zone.includes(d))
  const laThamSo = typeof k?.value === 'string' && k.value !== ''
  /* ⚠ `<div className="hang">`, KHÔNG phải `<label>`. Luật HTML: bấm bất kỳ đâu trong
     một `<label>` sẽ kích điều khiển ĐẦU TIÊN bên trong nó. Bọc CẢ HÀNG bằng `<label>`
     thì bấm chữ "Tên" lại mở dropdown "Loại", bấm nhãn "Đệm" lại nhảy vào ô số — tay ở
     một chỗ, chuyện xảy ra ở chỗ khác. Nhãn của từng điều khiển đã có riêng rồi. */
  return (
    <div className="hang">
      <span className="nhan-o">{nhan}</span>
      {k ? (
        <>
          {/* `mép zone đối diện` là một MỐC, không nhân với gì: `bo_chay._khoang` tính
              `v` rồi vứt, nên `SL = 1` và `SL = 99` ra y hệt. Khoá ô số lại thay vì để
              một con số vô nghĩa nằm đó. */}
          <OSo v={k.value} thamSo={thamSo} donVi={k.tinh} tat={k.tinh === 'bien_zone'}
               title={k.tinh === 'bien_zone'
                 ? chu('Mép zone đối diện là một MỐC — không nhân với con số nào')
                 : undefined}
               dat={x => dat({ ...k, value: x })} />
          {/* Chọn tham số rồi thì KHOÁ đơn vị: tham số đã khai đơn vị của nó, và một
              cái tên chỉ được mang một nghĩa. */}
          {laThamSo ? (
            <span className="o don-vi khoa"
                  title={`Đơn vị do tham số "${k.value}" quy định — muốn đơn vị khác `
                         + 'thì đặt một tham số khác.'}>
              {boot.don_vi[String(k.tinh ?? 'gia')]} 🔒
            </span>
          ) : (
            <select className="o" value={k.tinh ?? ''}
                    onChange={e => dat({ ...k, tinh: e.target.value })}>
              {ds.map(kk => <option key={kk} value={kk}>{boot.don_vi[kk]}</option>)}
            </select>
          )}
          <button className="nut nho" onClick={() => dat(undefined)} title={chu("Bỏ")}>✕</button>
        </>
      ) : (
        <button className="nut nho" onClick={() => dat({ tinh: 'atr', value: 1 })}>
          + đặt
        </button>
      )}
      {goiY && <span className="goi-y">{goiY}</span>}
    </div>
  )
}

/* ---------- một dòng ĐIỀU KIỆN ---------- */

function DongDieuKien({ c, boot, tab, thamSo, dat, xoa, so, coZone, haiBen }: {
  c: HD; boot: Bootstrap; tab: Tab; thamSo: ThamSo[]
  dat: (v: HD) => void; xoa: () => void; so: number; coZone: boolean
  /** CƠ CHẾ của cả khối: so hai đại lượng, hay so với một giá trị. */
  haiBen: boolean
}) {
  /* MỘT ĐIỀU KIỆN = ba trường: [đại lượng] [phép] [lượng].
   *
   * ⚠ Trước đây có BẢY. Bốn cái đã đi — xem `core.normalize_action`:
   *   `phai_loai` khai lại một thứ nhìn vào là biết (app đã suy như thế ở `lot`);
   *   `dao`       thật ra là một PHÉP SO (`là ĐÚNG` / `là SAI`);
   *   `phai2`     chỉ phục vụ phép "trong khoảng", mà `a ≤ x ≤ b` chính là HAI dòng;
   *   `don_vi`    nhập vào LƯỢNG, cùng hình dạng `{value, tinh}` mà SL/TP đang dùng.
   */
  const ten = (c?.trai?.ten ?? '') as string
  const loai = boot.toan_hang_loai[ten] ?? 'muc_gia'
  const dungSai = loai === 'dung_sai'
  const phep = (c.phep ?? '<') as string
  // `là ĐÚNG` / `là SAI` là một PHÉP SO, không phải ô tick — và chúng KHÔNG có vế phải.
  const khongVePhai = phep === 'la_dung' || phep === 'la_sai'

  /* VẾ PHẢI — hình dạng do CƠ CHẾ CỦA KHỐI quyết, không phải từng dòng tự khai.
   *
   * ⚠ Trước đây mỗi dòng có một chip `số`/`đ.lượng`, nên hai dòng trong cùng một khối
   * mang hai hình dạng: cột lệch, và mắt phải đọc lại hình dạng ở từng dòng. Cái chip
   * đó chỉ tồn tại vì MỘT hàng phải gánh HAI hình dạng — đưa lựa chọn lên mức khối thì
   * nó tự biến mất. */
  const phai = (c.phai ?? {}) as HD
  const laDaiLuong = haiBen

  /* Đơn vị chỉ SỐNG khi vế trái là một BỀ RỘNG giá và vế phải là một con số.
     Vế phải là đại lượng khác thì đơn vị TRIỆT TIÊU: `atr < zone_range [bps]` ra kết
     quả y hệt `atr < zone_range`, vì cả hai vế cùng chia một mẫu số. */
  const coDonVi = loai === boot.loai_co_don_vi && !laDaiLuong && !khongVePhai
  /** Vế phải đang giữ TÊN một tham số → đơn vị do tham số quy định, ô đơn vị khoá. */
  const laThamSo = typeof phai.value === 'string' && phai.value !== ''
  /** Đơn vị CỦA Ô này — nút ▾ lọc tham số theo đúng nó. */
  const donViO = khongVePhai || laDaiLuong ? null
    : (coDonVi ? String(phai.tinh ?? 'gia') : boot.toan_hang_don_vi[ten] ?? null)
  /* CHỈ BÀY NHỮNG ĐƠN VỊ DÙNG ĐƯỢC cho đúng điều kiện này. Hai nhát cắt, cùng lý lẽ đã
     ghi sẵn trong `core.DON_VI_CHO`: *"bày ra một lựa chọn vô nghĩa rồi soát tĩnh mắng
     là tệ hơn không bày"*.
       · KHÔNG ĐO MỘT ĐẠI LƯỢNG BẰNG CHÍNH NÓ — `Zone — ATR trung bình` chia cho
         `zone_atr_tb` thì luôn ra 1, y như lý lẽ đã viết cho `close/close`;
       · `× ATR zone` chỉ có mẫu số khi khối nằm SAU cổng zone; trước đó luôn NaN, tức
         cổng luôn trượt.
     Cái ĐANG chọn thì giữ lại, để phép lọc không âm thầm đổi lựa chọn cũ. */
  const dsDonVi = (boot.don_vi_cho.dieu_kien ?? []).filter(
    d => d === phai.tinh
      || (d !== boot.don_vi_chinh_no[ten]
          && (coZone || !boot.don_vi_can_zone.includes(d))))

  // Phép so LỌC theo loại vế trái — danh sách sai không bày ra, thay vì bày rồi mắng.
  const laDS = (k: string) => k === 'la_dung' || k === 'la_sai'
  const dsPhep = Object.entries(boot.phep_so).filter(([k]) =>
    dungSai && !haiBen ? laDS(k) : !laDS(k))

  return (
    <div className={'dong-dk' + (haiBen ? ' hai-ben' : '')}>
      <span className="so-dk">{so}</span>
      <OToanHang o={c.trai ?? {}} boot={boot} tab={tab} thamSo={thamSo} coZone={coZone}
                 boDungSai={haiBen}
                 dat={v => {
                   // Đổi đại lượng thì phép so cũ có thể không còn hợp — sửa luôn,
                   // đừng để một dòng vô nghĩa nằm đó chờ soát tĩnh mắng.
                   const l2 = boot.toan_hang_loai[(v.ten ?? '') as string] ?? 'muc_gia'
                   const ds = l2 === 'dung_sai'
                   dat({ ...c, trai: v,
                         phep: ds ? (khongVePhai ? phep : 'la_dung')
                                  : (khongVePhai ? '<' : phep) })
                 }} />

      <select className="o nho phep" value={phep}
              onChange={e => dat({ ...c, phep: e.target.value })}>
        {dsPhep.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>

      {khongVePhai ? (
        <span className="ve-phai trong" />
      ) : (
        <div className="ve-phai">
          {laDaiLuong ? (
            <OToanHang o={phai} boot={boot} tab={tab} hep thamSo={thamSo} coZone={coZone}
                       boDungSai dat={v => dat({ ...c, phai: v })} />
          ) : (
            /* ⚠ Ô này TỪNG có `<datalist>` tham số và placeholder "số hoặc tên tham
               số" — nó chính là câu dạy sai: bốn ô số còn lại trong app không hề gõ tên
               được. Giờ mọi ô số đều là `OSo`: gõ = số, tên thì chỉ nút "Đặt tên cho số
               này" ở bảng Vấn đề mới đặt được. */
            <OSo v={phai.value} thamSo={thamSo} lop="rong" donVi={donViO}
                 tat={phai.tinh === 'bien_zone'}
                 title={phai.tinh === 'bien_zone'
                   ? chu('Mép zone đối diện là một MỐC, không nhân với con số nào')
                   : chu('Gõ một con số. Số này lặp ở nhiều chỗ thì bảng Vấn đề sẽ mời đặt tên cho nó.')}
                 dat={x => dat({ ...c, phai: { ...phai, value: x } })} />
          )}
        </div>
      )}

      {/* ĐƠN VỊ — chỉ tồn tại ở cơ chế "so với một giá trị".
          So HAI ĐẠI LƯỢNG thì hai vế cùng chia một mẫu số nên đơn vị triệt tiêu: cột
          này bị BỎ HẲN, không phải làm mờ. (Bản đầu vẫn in đơn vị tự nhiên của vế trái
          — `close` → "giá tuyệt đối" — tức mâu thuẫn với chính tooltip của nó.) Cả khối
          cùng một cơ chế nên mọi dòng vẫn thẳng cột, và 118px đó trả về cho hai ô chọn
          toán hạng, đúng chỗ đang chật.

          Trong cơ chế "so với giá trị" thì nó LUÔN chiếm một cột kể cả khi mờ: bỏ hẳn
          thì nút ✕ trượt sang cột khác và lệch hàng với mọi dòng còn lại.

          KHOÁ khi vế phải là một THAM SỐ: tham số đã khai đơn vị của nó rồi, và một
          cái tên chỉ được mang MỘT nghĩa. Cho đổi ở đây thì `nguong = 7` chỗ này đọc
          là 7 bps, chỗ kia 7 × ATR — đúng cái bẫy mà bảng tham số sinh ra để chặn.
          Vẫn HIỆN chứ không ẩn: ẩn đi thì cột lệch, và đọc điều kiện lại phải mở bảng
          tham số mới biết đang so cái gì với cái gì. */}
      {haiBen ? null : coDonVi && laThamSo ? (
        <span className="o nho don-vi khoa"
              title={`Đơn vị do tham số "${phai.value}" quy định — một cái tên chỉ mang `
                     + 'một nghĩa. Muốn đơn vị khác thì đặt một tham số khác.'}>
          {boot.don_vi[String(phai.tinh ?? 'gia')]} 🔒
        </span>
      ) : coDonVi ? (
        <select className="o nho don-vi" value={String(phai.tinh ?? 'gia')}
                title={chu("Quy đổi vế trái trước khi so — cùng một con số mang cùng ý nghĩa trên mọi symbol")}
                onChange={e => {
                  const p2 = { ...phai } as HD
                  if (e.target.value === 'gia') delete p2.tinh
                  else p2.tinh = e.target.value
                  dat({ ...c, phai: p2 })
                }}>
          {dsDonVi.map(k => <option key={k} value={k}>{boot.don_vi[k]}</option>)}
        </select>
      ) : (
        <span className="o nho don-vi tat"
              title={khongVePhai
                ? chu('Đúng/sai không có vế phải — mệnh đề đã trọn')
                : laDaiLuong
                  ? chu('Hai vế cùng một đại lượng thì đơn vị triệt tiêu')
                  : chu('Đại lượng này không quy đổi được — nó đã có sẵn một đơn vị tự nhiên')}>
          {khongVePhai ? ''
            : (boot.nhan_don_vi[boot.toan_hang_don_vi[ten] ?? ''] ?? '—')}
        </span>
      )}

      <button className="nut nho xoa-dk" onClick={xoa} title={chu("Xoá điều kiện này")}>✕</button>
    </div>
  )
}

/* ---------------------------------- hộp thoại --------------------------------- */

export default function ActionDialog({ action, boot, tab, thamSo, coZone,
                                      onLuu, onDong }: {
  action: HD
  boot: Bootstrap
  tab: Tab
  thamSo: ThamSo[]
  /** Khối này có nằm SAU cổng zone không — `validate.luong[tab].sau_cong_zone` của
   *  Python. Không thì mọi thứ thuộc zone bị GIẤU ĐI thay vì bày ra rồi báo lỗi đỏ. */
  coZone: boolean
  onLuu: (a: HD) => void
  onDong: () => void
}) {
  useNgon()   // đổi ngôn ngữ → vẽ lại (xem `i18n.ts`)
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

  /** ⚠ GỬI ĐI BẢN PYTHON ĐÃ CHUẨN HOÁ, không phải bản nháp trong tay hộp thoại.
   *
   *  Bản trước bấm Lưu là `onLuu(a)` — tức canvas nhận đúng cái nháp thô. Mà nháp thì
   *  mang rác của những lần sửa dở: dòng điều kiện MỚI sinh ra với `{value: 7, tinh:
   *  'bps'}`, đổi vế trái sang `Zone — số nến` thì `tinh: 'bps'` NẰM LẠI. Ô đơn vị trong
   *  hộp thoại hiện đúng "nến" (nó hỏi `don_vi_cua_o`), phần xem trước cũng đúng (nó hỏi
   *  Python) — nhưng thứ được cất đi thì vẫn còn `bps`, và thẻ trên canvas dựng lại từ
   *  đó nên ghi `Zone — số nến ≥ 10 bps của giá`. Người dùng gặp thật.
   *
   *  `normalize_action` vốn đã vứt `tinh` không hợp lệ (`don_vi_cho('zone_dem')` rỗng),
   *  nên chỉ cần LẤY VỀ thứ nó vừa trả. Hộp thoại đã gọi `save_action` cho phần xem
   *  trước rồi mà lại bỏ đi `action`, chỉ giữ `display` — sửa bằng cách dùng nốt.
   *
   *  Gọi LẠI ở đây chứ không dùng kết quả của phần xem trước: xem trước hoãn 200 ms, gõ
   *  xong bấm Lưu ngay là nó chưa kịp chạy và ta cất một bản CŨ hơn cả bản nháp.
   *  Hỏng đường nào thì ngã về `a` — thà giữ nguyên thứ người dùng vừa gõ còn hơn mất. */
  async function luuRoiDong() {
    const r = await py.save_action(a, tab, thamSo)
    onLuu((r.ok && r.value?.action ? r.value.action : a) as HD)
  }

  async function doiLoai(t: string) {
    // Lấy mặc định từ Python chứ không tự nặn ở JS: mấy con số mặc định
    // (ATR 14, ngưỡng 7 bps, SL 1.5×ATR) là kiến thức về chiến lược, thuộc về lõi.
    const r = await py.action_defaults(t)
    setA({ ...(r.value ?? { type: t }), name: a.name })
  }

  const conds: HD[] = a.conditions ?? []
  /** Danh sách điều kiện THỨ HAI của cổng zone — định nghĩa "hợp lệ". Xem `dk_hop_le`
   *  trong `core.normalize_action`. */
  const hopLe: HD[] = (a.dk_hop_le as HD[] | undefined) ?? []

  /** Đổi CƠ CHẾ so sánh của cả khối — viết lại vế phải của MỌI dòng.
   *
   *  Có mất dữ liệu (con số đã gõ, hoặc đại lượng đã chọn), và đó là chủ ý: hình dạng
   *  của khối do cờ quyết, nên không thể vừa bật cờ vừa giữ mấy vế phải kiểu cũ. Hộp
   *  thoại là bản NHÁP — bấm Huỷ là xong, lưu rồi vẫn còn Hoàn tác.
   *
   *  Vế TRÁI và PHÉP giữ nguyên: đó là phần người dùng nghĩ lâu nhất. Toán hạng đúng/sai
   *  cũng KHÔNG tự đổi — soát tĩnh nói ra chứ không sửa lén hộ. */
  const doiCoChe = (bat: boolean) => setA(x => ({
    ...x,
    so_dai_luong: bat,
    conditions: (x.conditions ?? [])
      // XOÁ dòng không còn hợp lệ, đừng để lại một mớ rồi báo lỗi đỏ. Toán hạng
      // đúng/sai không so được với một đại lượng (`lệnh này đã khớp > zone_HH` không
      // phải một câu), và không có toán hạng nào để đổi sang cho hợp — nên xoá.
      // Chiều ngược lại không xoá gì: `close > ma` thành `close > 0`, vẫn dùng được.
      .filter((c: HD) => !bat
        || !boot.toan_hang_dung_sai.includes((c.trai?.ten ?? '') as string))
      .map((c: HD) => ({
        ...c,
        phep: bat && (c.phep === 'la_dung' || c.phep === 'la_sai') ? '<' : c.phep,
        phai: bat ? { ten: '' } : { value: 0 },
      })),
  }))

  /** Một dòng điều kiện MỚI, đúng hình dạng của cơ chế đang bật. */
  const dongMoi = (): HD => ({
    trai: { ten: 'atr', tf: boot.timeframes[1] ?? 'M5', period: 14 },
    phep: '<',
    phai: a.so_dai_luong ? { ten: '' } : { value: 7, tinh: 'bps' },
  })

  return (
    <Modal title={`Hành động — ${boot.action_labels[a.type] ?? a.type}`} width={880}
           onClose={onDong}
           footer={
             <>
               <div className="xem-truoc" title={chu("Đúng câu mà lõi hiểu về hành động này")}>
                 {xem || '…'}
               </div>
               <button className="nut" onClick={onDong}>{chu('Huỷ')}</button>
               <button className="nut chinh" onClick={() => void luuRoiDong()}>{chu('Lưu')}</button>
             </>
           }>

      <div className="hang">
        <span className="nhan-o">{chu('Loại')}</span>
        <select className="o" value={a.type} onChange={e => doiLoai(e.target.value)}>
          {loaiChoPhep.map(t =>
            <option key={t} value={t}>{boot.action_labels[t]}</option>)}
        </select>
        <span className="nhan-o phu">{chu('Tên')}</span>
        <input className="o" value={a.name ?? ''} placeholder="(để trống = dùng tên loại)"
               onChange={e => dat('name', e.target.value)} />
        {/* CƠ CHẾ SO SÁNH — MỘT lựa chọn cho CẢ KHỐI, nằm ngay cạnh tên.
            Trước đây nó là một chip trên TỪNG DÒNG, nên hai dòng cùng khối mang hai
            hình dạng: cột lệch, mắt phải đọc lại hình dạng ở mỗi dòng. Cái chip ấy chỉ
            tồn tại vì một hàng phải gánh hai hình dạng — nâng lựa chọn lên mức khối thì
            nó tự biến mất, và mọi dòng trong khối giống hệt nhau. */}
        {a.type === 'check_cond' && (
          <label className="tick-cochet"
                 title={[
                   chu('Bật: mọi dòng so HAI ĐẠI LƯỢNG (Giá đóng cửa > MA)')
                   + ' — không có ô số, không có đơn vị.',
                   chu('Tắt: mọi dòng so với một GIÁ TRỊ bạn đặt (số · tham số · đúng/sai).'),
                   '',
                   chu('Muốn cả hai kiểu trong một cổng thì nối HAI cổng — nối tiếp là VÀ.'),
                 ].join('\n')}>
            <input type="checkbox" checked={!!a.so_dai_luong}
                   onChange={e => doiCoChe(e.target.checked)} />
            So hai đại lượng
          </label>
        )}
      </div>

      {/* ------------------------------ Kiểm tra điều kiện ---------------------- */}
      {a.type === 'check_cond' && (
        <div className="khoi-form">
          <div className="chu-dan">
            Mọi dòng phải cùng đúng thì mới khớp (<b>VÀ</b>). Muốn <b>HOẶC</b> thì tách
            ra thành hai nhánh riêng trên sơ đồ — nhìn sơ đồ là thấy được, còn chữ
            chu("hoặc") giấu trong hộp thoại thì không.
          </div>
          {conds.map((c, i) => (
            <DongDieuKien key={i} c={c} boot={boot} tab={tab} thamSo={thamSo} so={i + 1}
                          coZone={coZone} haiBen={!!a.so_dai_luong}
                          dat={v => dat('conditions',
                            conds.map((x, k) => (k === i ? v : x)))}
                          xoa={() => dat('conditions', conds.filter((_, k) => k !== i))} />
          ))}
          {!conds.length && (
            <div className="dong rong">{chu('chưa có điều kiện nào — hành động này sẽ luôn khớp')}</div>
          )}
          <button className="nut" onClick={() => dat('conditions', [...conds, dongMoi()])}>
            + Thêm điều kiện
          </button>

          {/* ⭐ CỔNG ZONE. Đây là thứ ĐỊNH NGHĨA zone — không có nó thì `số nến nén`,
              `đỉnh zone`… không có nghĩa gì cả, và soát tĩnh sẽ báo lỗi.
              Trước đây việc đếm do một cỗ máy ẩn chạy ngoài sơ đồ làm, nên nhìn sơ đồ
              không thấy zone sinh ra ở đâu; giờ chính cổng bạn vẽ là điều kiện đếm. */}
          {tab === 'entry' && (
            <label className="tick tick-zone">
              <input type="checkbox" checked={!!a.cong_zone}
                     onChange={e => dat('cong_zone', e.target.checked || undefined)} />
              <b>{chu('Cổng ZONE')}</b>
              <span className="goi-y">
                cổng này là ĐIỀU KIỆN ĐẾM — qua thì zone lớn thêm một nến, trượt thì
                zone chết. Các khối hỏi về zone phải nối SAU nó.
              </span>
            </label>
          )}

          {/* ⭐ PHẦN HỢP LỆ — danh sách điều kiện THỨ HAI, chỉ hiện khi đã bật Cổng ZONE.
              Nó KHÔNG chặn dòng chảy: trượt thì zone vẫn sống, chỉ là chưa dùng được.
              Ranh giới với phần đếm ở trên là câu "trượt vế này nghĩa là gì" — nén HỎNG
              thì để trên (zone chết), CHƯA TỚI LÚC thì để đây. */}
          {tab === 'entry' && a.cong_zone && (
            <div className="khoi-hop-le">
              <div className="chu-dan">
                <b>{chu('Zone thế nào là HỢP LỆ')}</b> — viết một lần ở đây, rồi mọi cổng khác
                (kể cả bên Manage) chỉ việc hỏi <b>{chu('Zone hợp lệ')}</b>. Trượt phần này thì
                zone <b>{chu('vẫn sống')}</b> và đếm tiếp, chỉ là chưa dùng được.
                <br />
                Ranh giới với phần trên: trượt nghĩa là <b>{chu('"nén hỏng rồi"')}</b> thì để ở
                phần đếm (zone chết); trượt nghĩa là <b>{chu('"chưa tới lúc"')}</b> thì để ở đây.
              </div>
              {hopLe.map((c, i) => (
                <DongDieuKien key={i} c={c} boot={boot} tab={tab} thamSo={thamSo}
                              so={i + 1} coZone haiBen={false}
                              dat={v => dat('dk_hop_le',
                                hopLe.map((x, k) => (k === i ? v : x)))}
                              xoa={() => dat('dk_hop_le',
                                hopLe.filter((_, k) => k !== i))} />
              ))}
              {!hopLe.length && (
                <div className="dong rong">
                  chưa khai — hỏi chu("Zone hợp lệ") ở nơi khác sẽ báo lỗi
                </div>
              )}
              <button className="nut"
                      onClick={() => dat('dk_hop_le', [...hopLe, dongMoi()])}>
                + Thêm điều kiện hợp lệ
              </button>
            </div>
          )}
        </div>
      )}

      {/* ------------------------------ Vào lệnh -------------------------------- */}
      {a.type === 'vao_lenh' && (
        <div className="khoi-form">
          <div className="hang">
            <span className="nhan-o">{chu('Hướng')}</span>
            {Object.entries(boot.huong).map(([k, v]) => (
              <label key={k} className="tick">
                <input type="radio" name="huong" checked={a.huong === k}
                       onChange={() => dat('huong', k)} />{v}
              </label>
            ))}
            <span className="nhan-o phu">{chu('Loại lệnh')}</span>
            <select className="o" value={a.loai ?? 'stop'}
                    onChange={e => dat('loai', e.target.value)}>
              {Object.entries(boot.loai_lenh).map(([k, v]) =>
                <option key={k} value={k}>{v}</option>)}
            </select>
            {/* ⭐ RỦI RO % VỐN thay cho LOT — core.md §15.13.
                Lot là con số TUYỆT ĐỐI: 0,01 lot trên $10.000 khác hẳn trên $100.000,
                nên đổi tài khoản là tiền và sụt vốn đổi nghĩa. Khối lượng nay do bộ
                chạy suy ra từ rủi ro và khoảng cách SL. */}
            <span className="nhan-o phu">{chu('Rủi ro')}</span>
            <OSo v={a.rui_ro} thamSo={thamSo} donVi={boot.don_vi_o.rui_ro}
                 dat={x => dat('rui_ro', x)}
                 title={chu("Phần trăm VỐN mạo hiểm cho mỗi lệnh. Khối lượng suy ra từ đây và khoảng cách SL.")} />
          </div>

          <div className="chu-dan">
            Khối lượng <b>{chu('không phải một ô nhập')}</b> nữa — bộ chạy tính
            <code> lot = vốn × rủi ro% ÷ (khoảng cách SL × contract size)</code>.
            Nhờ đó mọi lệnh mạo hiểm <b>{chu('một R bằng nhau')}</b>, và đường tiền nói cùng một
            chuyện với tổng R.
          </div>

          {/* ⭐ MỐC NEO — thứ QUYẾT ĐỊNH lệnh nằm ở đâu, nên nó đứng TRƯỚC đệm.
              Trước đây trường này không tồn tại: việc "neo vào mép zone thuận chiều"
              bị viết cứng trong bộ chạy, nên trên hộp thoại chỉ hiện mỗi ô Đệm — và
              cái đệm, vốn chỉ là tấm khiên mỏng, hoá thành nhân vật chính.
              Danh sách nay lấy THẲNG TỪ KHO (core.md §15.8), không còn gõ tay ba dòng.

              ⚠ ẨN với lệnh THỊ TRƯỜNG: nó khớp ở giá thị trường, mốc neo không có
              nghĩa gì với nó. Bày ra một ô mà bộ chạy bỏ qua là đúng thứ `DON_VI_CHO`
              đã cấm — "bày ra một lựa chọn vô nghĩa rồi soát tĩnh mắng là tệ hơn không
              bày". */}
          {a.loai !== 'market' && (
            <div className="hang">
              <span className="nhan-o">{chu('Đặt tại')}</span>
              <select className="o" value={a.entry?.moc ?? ''}
                      onChange={e => dat('entry', { moc: e.target.value })}>
                {Object.entries(boot.moc_entry).map(([k, v]) =>
                  <option key={k} value={k}>{v}</option>)}
              </select>
              <span className="goi-y">
                {boot.moc_can_zone.includes(a.entry?.moc ?? '')
                  ? chu('cần một cổng ZONE ở phía trên — entry = mốc này ± đệm')
                  : chu('entry = mốc này ± đệm')}
              </span>
            </div>
          )}

          {/* ĐỆM là TUỲ CHỌN. Bỏ trống thì lệnh nằm đúng mốc — hợp lệ, chỉ dễ dính
              một nhịp phá giả hơn. */}
          <OKhoang nhan={chu("Đệm (tuỳ chọn)")} k={a.dem} boot={boot} dat={v => dat('dem', v)}
                   thamSo={thamSo} oDau="dem" coZone={coZone}
                   goiY={chu("đẩy giá đặt ra ngoài mốc — lá chắn chống phá giả")} />
          <OKhoang nhan="Stop Loss" k={a.sl} boot={boot} dat={v => dat('sl', v)}
                   thamSo={thamSo} oDau="sl" coZone={coZone}
                   goiY={chu("khoảng cách này chính là 1R")} />
          <OKhoang nhan="Take Profit" k={a.tp} boot={boot} dat={v => dat('tp', v)}
                   thamSo={thamSo} oDau="tp" coZone={coZone}
                   goiY={chu("thường đặt theo bội của R")} />

          <div className="chu-dan">
            SL/TP đặt ở đây là <b>{chu('ban đầu')}</b>. Khối <b>{chu('Sửa lệnh')}</b> phía sau chỉ để
            DỜI chúng — không có SL ngay từ lúc vào là để ngỏ cả tài khoản.
          </div>
        </div>
      )}

      {/* ------------------------------ Sửa lệnh -------------------------------- */}
      {a.type === 'sua_lenh' && (
        <div className="khoi-form">
          <div className="hang">
            <span className="nhan-o">{chu('Chế độ')}</span>
            <select className="o" value={a.che_do ?? 'doi_sl'}
                    onChange={e => dat('che_do', e.target.value)}>
              {Object.entries(boot.sua_che_do).map(([k, v]) =>
                <option key={k} value={k}>{v}</option>)}
            </select>
          </div>

          {/* ⭐ MỐC NEO cho Sửa lệnh — CÙNG danh sách với khối Vào lệnh.
              Trước đây SL/TP luôn đo từ giá hiện tại (`ctx.bid` viết cứng trong bộ
              chạy), nên không viết được `SL tại đáy zone − 0,2 ATR`. Hai khối cùng nói
              về MỘT vị trí giá thì phải nói bằng cùng một cách — core.md §15.10.
              Khác khối Vào lệnh đúng một chỗ: ở đây mốc là TUỲ CHỌN. Bỏ trống = đo từ
              giá hiện tại, đúng hành vi cũ, nên file cũ mở ra không đổi gì. */}
          {boot.sua_can_gia.includes(a.che_do) && (
            <div className="hang">
              <span className="nhan-o">{chu('Đo từ')}</span>
              <select className="o" value={a.moc ?? ''}
                      onChange={e => dat('moc', e.target.value || undefined)}>
                <option value="">{chu('Giá hiện tại')}</option>
                {Object.entries(boot.moc_entry).map(([k, v]) =>
                  <option key={k} value={k}>{v}</option>)}
              </select>
              <span className="goi-y">
                {boot.moc_can_zone.includes(a.moc ?? '')
                  ? chu('cần một cổng ZONE ở phía trên')
                  : chu('mốc mới = chỗ này ± khoảng cách dưới')}
              </span>
            </div>
          )}

          {boot.sua_can_gia.includes(a.che_do) && (
            <OKhoang nhan={chu("Khoảng cách mới")} k={a.khoang} boot={boot}
                     thamSo={thamSo} oDau="sua" coZone={coZone}
                     dat={v => dat('khoang', v)} />
          )}

          {a.che_do === 'doi_sl' && (
            <div className="chu-dan">
              <b>{chu('SL chỉ được SIẾT, không được nới.')}</b> Mốc mới xa hơn SL đang có thì bộ
              chạy bỏ qua, không sửa gì. Nới SL sau khi vào lệnh là phá luôn định nghĩa
              1R mà mọi con số đang đo bằng nó. TP thì tự do — dời TP xa ra không tăng
              rủi ro.
            </div>
          )}

          {a.che_do === 'hoa_von' && (
            <div className="chu-dan">
              Không có tham số: chế độ này chỉ đặt <b>{chu('SL = giá vào')}</b>. Mốc kích hoạt
              (lãi đủ mấy R) và câu hỏi <b>{chu('"đã dời chưa"')}</b> thuộc về <b>cổng phía
              trước</b> — chỗ nhìn thấy được. D_02 giấu cả ba trong <code>ManageBreakEven</code>.
            </div>
          )}

          {a.che_do === 'ket_thuc' && (
            <div className="chu-dan">
              Không có tham số. Manage chạy <b>một lượt cho MỖI lệnh đang sống</b>, nên
              chu("lệnh này") là duy nhất và bộ chạy tự biết nó đã khớp hay chưa:
              <b> khớp rồi thì đóng, chưa khớp thì huỷ</b>. Trước đây là hai chế độ
              riêng — chọn nhầm thì hành động im lặng không làm gì.
            </div>
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
