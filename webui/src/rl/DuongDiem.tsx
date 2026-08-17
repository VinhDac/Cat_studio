/** ĐƯỜNG ĐIỂM TỐT NHẤT theo số sơ đồ đã chấm.
 *
 *     core.md §18.6.3
 *
 * Trả lời đúng MỘT câu, và là câu thực dụng nhất của cả bàn điều khiển:
 * **"còn tìm được gì nữa không — dừng được chưa"**. Đường phẳng vài nghìn lượt là tín
 * hiệu tắt máy, khỏi đốt cả đêm cho 4.000 lượt cuối không tìm thêm được gì.
 *
 * ⚠ Điểm tốt nhất chỉ TĂNG, nên đây là một hàm BẬC THANG — vẽ bậc thang thật
 * (`H` rồi `V`) chứ không nối xiên. Nối xiên là vẽ ra một cú cải thiện từ từ đã không
 * hề xảy ra: nó nhảy đúng một cái, tại đúng một lượt.
 *
 * ⚠ Và luôn kẻ mốc **0**: điểm âm là chuyện thường (phần lớn sơ đồ sinh bừa đều lỗ),
 * nên một đường đi lên mà không biết nó đã qua vạch 0 chưa thì đọc ra nghĩa ngược.
 */

/** Cao/rộng khung vẽ. Toạ độ trong SVG là toạ độ ẢO — `viewBox` co giãn theo ô chứa,
 *  nên không cần đo DOM và không có chuyện vẽ lệch một khung hình sau khi resize. */
const W = 320
const H = 132
const LE = { tren: 10, duoi: 18, trai: 34, phai: 8 }

export default function DuongDiem({ duong, daCham, tong, dangChay }: {
  /** `[[đã chấm, điểm tốt nhất], …]` — chỉ có bậc, không có điểm ở giữa. */
  duong: [number, number][]
  daCham: number
  tong: number
  dangChay: boolean
}) {
  if (!duong.length) {
    return (
      <div className="rl-plot-trong">
        {dangChay ? 'chưa sơ đồ nào qua cửa — đường sẽ hiện khi có cái đầu tiên'
                  : 'không sơ đồ nào qua cửa'}
      </div>
    )
  }

  const xMax = Math.max(daCham, tong, 1)
  const ys = duong.map(d => d[1])
  // Luôn kéo khoảng y ôm lấy 0 — xem chú thích đầu file.
  let y0 = Math.min(0, ...ys)
  let y1 = Math.max(0, ...ys)
  if (y1 - y0 < 1e-9) { y0 -= 0.5; y1 += 0.5 }
  const dem = (y1 - y0) * 0.12
  y0 -= dem; y1 += dem

  const px = (x: number) => LE.trai + (x / xMax) * (W - LE.trai - LE.phai)
  const py = (y: number) => LE.tren + (1 - (y - y0) / (y1 - y0)) * (H - LE.tren - LE.duoi)

  // BẬC THANG: tới bậc thì đi ngang trước, rồi mới nhảy dọc.
  let d = `M ${px(duong[0][0]).toFixed(1)} ${py(duong[0][1]).toFixed(1)}`
  for (let i = 1; i < duong.length; i++) {
    d += ` H ${px(duong[i][0]).toFixed(1)} V ${py(duong[i][1]).toFixed(1)}`
  }
  // Kéo dài tới chỗ đã chấm: phần phẳng ở đuôi CHÍNH LÀ thứ cần nhìn.
  d += ` H ${px(daCham).toFixed(1)}`

  const cuoi = duong[duong.length - 1]
  const phang = daCham - cuoi[0]
  const tot = cuoi[1]

  return (
    <div className="rl-plot-boc">
      <svg viewBox={`0 0 ${W} ${H}`} className="rl-svg" preserveAspectRatio="none">
        {/* mốc 0 */}
        {y0 < 0 && y1 > 0 && (
          <line x1={LE.trai} x2={W - LE.phai} y1={py(0)} y2={py(0)} className="rl-moc0" />
        )}
        <text x={LE.trai - 5} y={py(y1) + 8} className="rl-truc">{y1.toFixed(2)}</text>
        <text x={LE.trai - 5} y={py(y0)} className="rl-truc">{y0.toFixed(2)}</text>
        <path d={d} className="rl-duong" />
        <circle cx={px(daCham)} cy={py(tot)} r="2.6" className="rl-cham" />
        <text x={LE.trai} y={H - 4} className="rl-truc rl-truc-x">0</text>
        <text x={W - LE.phai} y={H - 4} className="rl-truc rl-truc-x rl-phai">
          {xMax.toLocaleString('vi-VN')}
        </text>
      </svg>
      <div className="rl-plot-chu">
        {/* Con số QUYẾT ĐỊNH: phẳng bao lâu rồi. */}
        {phang > 0
          ? <>phẳng <b>{phang.toLocaleString('vi-VN')}</b> lượt gần nhất
              {phang > xMax * 0.35 && <span className="rl-mach"> — dừng được rồi</span>}</>
          : <>vừa tìm được cái tốt hơn</>}
      </div>
    </div>
  )
}
