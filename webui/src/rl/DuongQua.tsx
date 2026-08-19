import { chu, useNgon } from '../i18n'
/** ĐƯỜNG "QUA CỬA" — bao nhiêu sơ đồ đã SỐNG, theo số lượt đã chấm.
 *
 *     core.md §18.6.3, §18.9c
 *
 * Trả lời đúng MỘT câu, và là câu thực dụng nhất của cả bàn điều khiển:
 * **"còn tìm được gì nữa không — dừng được chưa"**. Đường phẳng vài nghìn lượt là tín
 * hiệu tắt máy, khỏi đốt cả đêm cho phần cuối không tìm thêm được gì.
 *
 * ⭐ **Thay cho đường "điểm tốt nhất" của bản cũ.** Cùng là hàm bậc thang, nhưng đường
 * cũ vẽ một con số đã đo được là nhiễu: cửa "đều qua thời gian" cho thấy **6 trong 8**
 * cái ở bảng đầu bảng chỉ ăn may một đoạn (§18.5f). Vẽ đẹp một con số rỗng thì tệ hơn
 * không vẽ — nó khiến người đọc tin.
 *
 * "Số sơ đồ đã sống" thì không dính bệnh ấy: nó chỉ đếm, không xếp hạng.
 *
 * ⚠ Đếm CỘNG DỒN, không phải kích thước bảng đầu bảng — bảng ấy bị chặn ở `giu` nên nó
 * bão hoà rồi nằm im, và một đường nằm im vì bão hoà trông y hệt một đường nằm im vì
 * hết tìm được gì.
 *
 * ⚠ Vẽ BẬC THANG thật (`H` rồi `V`), không nối xiên: nối xiên là vẽ ra một cú tăng từ
 * từ đã không hề xảy ra — nó nhảy đúng một cái, tại đúng một lượt.
 */

/** Cao/rộng khung vẽ. Toạ độ trong SVG là toạ độ ẢO — `viewBox` co giãn theo ô chứa,
 *  nên không cần đo DOM và không có chuyện vẽ lệch một khung hình sau khi resize. */
const W = 320
const H = 132
const LE = { tren: 10, duoi: 18, trai: 30, phai: 8 }

export default function DuongQua({ duong, daCham, tong, dangChay }: {
  /** `[[đã chấm, số qua cửa cộng dồn], …]` — chỉ có bậc, không có điểm ở giữa. */
  duong: [number, number][]
  daCham: number
  tong: number
  dangChay: boolean
}) {
  useNgon()   // đổi ngôn ngữ → vẽ lại cả cây (xem `i18n.ts`)
  if (!duong.length) {
    return (
      <div className="rl-plot-trong">
        {dangChay ? chu('chưa sơ đồ nào qua cửa — đường sẽ hiện khi có cái đầu tiên')
                  : chu('không sơ đồ nào qua cửa')}
      </div>
    )
  }

  const xMax = Math.max(daCham, tong, 1)
  const yMax = Math.max(1, duong[duong.length - 1][1]) * 1.15

  const px = (x: number) => LE.trai + (x / xMax) * (W - LE.trai - LE.phai)
  const py = (y: number) => LE.tren + (1 - y / yMax) * (H - LE.tren - LE.duoi)

  let d = `M ${px(duong[0][0]).toFixed(1)} ${py(duong[0][1]).toFixed(1)}`
  for (let i = 1; i < duong.length; i++) {
    d += ` H ${px(duong[i][0]).toFixed(1)} V ${py(duong[i][1]).toFixed(1)}`
  }
  // Kéo dài tới chỗ đã chấm: phần phẳng ở ĐUÔI chính là thứ cần nhìn.
  d += ` H ${px(daCham).toFixed(1)}`

  const cuoi = duong[duong.length - 1]
  const phang = daCham - cuoi[0]

  return (
    <div className="rl-plot-boc">
      <svg viewBox={`0 0 ${W} ${H}`} className="rl-svg" preserveAspectRatio="none">
        <line x1={LE.trai} x2={W - LE.phai} y1={py(0)} y2={py(0)} className="rl-moc0" />
        <text x={LE.trai - 5} y={py(yMax) + 8} className="rl-truc">
          {Math.ceil(yMax)}
        </text>
        <text x={LE.trai - 5} y={py(0)} className="rl-truc">0</text>
        <path d={d} className="rl-duong" />
        <circle cx={px(daCham)} cy={py(cuoi[1])} r="2.6" className="rl-cham" />
        <text x={LE.trai} y={H - 4} className="rl-truc rl-truc-x">0</text>
        <text x={W - LE.phai} y={H - 4} className="rl-truc rl-truc-x rl-phai">
          {xMax.toLocaleString('vi-VN')}
        </text>
      </svg>
      <div className="rl-plot-chu">
        {phang > 0
          ? <>phẳng <b>{phang.toLocaleString('vi-VN')}</b> lượt gần nhất
              {phang > xMax * 0.35 && <span className="rl-mach"> — dừng được rồi</span>}</>
          : <>{chu('vừa có thêm một cái qua cửa')}</>}
      </div>
    </div>
  )
}
