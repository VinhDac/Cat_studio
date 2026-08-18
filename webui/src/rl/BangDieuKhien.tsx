import { useCallback } from 'react'
import { pyRL } from '../api'
import DuongQua from './DuongQua'
import PhanBoCot from './PhanBoCot'
import type { DauBang, RLBoot, ThongKeTim, TrangThaiLuot } from '../types'

/** Mép thùng — phải khớp `tim_kiem.MEP_*`. Khai lại ở đây chứ không bơm qua cầu nối:
 *  chúng là hằng số của phép đo, đổi một bên mà quên bên kia thì nhãn trục nói dối. */
const MEP_DIEM = [-0.6, -0.4, -0.25, -0.15, -0.08, -0.03, 0, 0.03, 0.08, 0.15, 0.25, 0.4]
const MEP_LENH = [1, 10, 50, 200, 1000, 5000]
const MEP_GIAY = [0.5, 1, 2, 5, 10, 30]
/** Thùng đầu tiên KHÔNG âm — từ đây trở lên tô màu "tốt". */
const THUNG_0 = MEP_DIEM.indexOf(0) + 1

/** DASHBOARD của cửa sổ RL — *"tôi không muốn chạy mù"*.
 *
 *     core.md §18.6.3, §18.9c
 *
 * ⚠ **Đây là đợt THAY, không phải đợt THÊM.** Bản cũ trưng ra bốn con số trông rất có
 * thẩm quyền mà rỗng, và mỗi cái có một số đo giết nó:
 *
 * ```
 * "điểm tốt nhất +0,9686"   6/8 cái đầu bảng chỉ ăn may một đoạn      (§18.5f)
 * đường "điểm tốt nhất"      cùng bệnh — vẽ đẹp một con số rỗng
 * "còn 13m"                  trung bình, mà chi phí mỗi sơ đồ chênh 1.000 lần
 * ô "Chuỗi tuần (chưa dựng)" lời hứa treo suốt phase
 * ```
 *
 * ⭐ Ba câu người ta thật sự hỏi khi ngồi nhìn máy chạy, mỗi câu một ô:
 *
 * ```
 * TIẾN ĐỘ       bao giờ xong        → và KHOẢNG, không phải một con số giả chính xác
 * TÌM ĐƯỢC GÌ   có gì SỐNG không    → và đám kia CHẾT VÌ ĐÂU
 * MÁY           nó ăn bao nhiêu máy → và kéo xuống được NGAY, không đợi lượt sau
 * ```
 */
export default function BangDieuKhien({ tt, nhan, dangChay, tongNhan, dauBang,
                                       boot, moSoDo }: {
  tt: TrangThaiLuot | null
  /** Một dòng mô tả lượt này chạy với gì — xem `api._nhan_cau_hinh`. */
  nhan: string
  dangChay: boolean
  tongNhan: number
  dauBang: DauBang[]
  boot: RLBoot
  moSoDo: (hang: number) => void
}) {
  const datNhan = useCallback((n: number) => {
    if (tt) void pyRL.rl_dat_nhan(tt.ma, n)
  }, [tt])

  if (!tt) {
    return (
      <div className="rl-bang-dieu-khien">
        <section className="rl-o rl-trong">chưa chạy lượt nào — bấm ▶ Chạy</section>
      </div>
    )
  }
  const tk: ThongKeTim | undefined = tt.thong_ke ?? undefined
  const pt = tt.tong ? (tt.da_chay / tt.tong) * 100 : 0
  const daDung = tt.nhan_dung ?? tt.so_nhan ?? tongNhan

  return (
    <div className="rl-bang-dieu-khien">
      {/* ⭐ CẤU HÌNH ĐANG CHẠY. Giấu cài đặt vào cửa sổ ⚙ chỉ AN TOÀN khi màn hình luôn
          hiện thứ đang có hiệu lực — không thì đó là quay lại chạy mù. */}
      <div className="bdk-cau-hinh" title={nhan}>{nhan || '—'}</div>

      <div className="bdk-hang">
        {/* ---------------------------------------------------------- TIẾN ĐỘ */}
        <section className="rl-o bdk-o">
          <div className="bdk-ten">TIẾN ĐỘ</div>
          <div className="bdk-to">
            {tt.da_chay.toLocaleString('vi-VN')}
            <em> / {tt.tong.toLocaleString('vi-VN')}</em>
          </div>
          <div className="rl-thanh"><div className="rl-thanh-day"
                                         style={{ width: `${pt}%` }} /></div>
          <div className="bdk-dong"><span>đã chạy</span>
            <b>{lau(giay(tt))}</b></div>
          <div className="bdk-dong"><span>còn</span><b>{conLai(tt, dangChay)}</b></div>
          <div className="bdk-chu">
            {tt.dang_chay ? (tt.chu || 'đang chạy')
              : tt.dung_giua_chung ? 'đã dừng giữa chừng'
              : (tk?.vi_sao_ngung || 'xong')}
          </div>
          {tt.loi && <div className="rl-loi">{tt.loi}</div>}
        </section>

        {/* ------------------------------------------------------ TÌM ĐƯỢC GÌ */}
        <section className="rl-o bdk-o">
          <div className="bdk-ten">TÌM ĐƯỢC GÌ</div>
          {/* ⚠ Con số lớn là SỐ SỐNG, không phải điểm cao nhất. Điểm cao nhất đã đo
              được là chuyện may rủi; "có mấy cái sống" thì không. */}
          <div className="bdk-to bdk-tot">{tt.qua_cong_don ?? 0}
            <em> qua cửa</em></div>
          {/* Vì sao đám kia CHẾT — xếp theo số lượng, vì đó là thứ mách nên chỉnh gì:
              rớt "đều" nhiều → không gian nghèo; nã lệnh nhiều → siết trần; không lệnh
              nhiều → kho đồ đang bày ra sơ đồ câm. */}
          {tk ? (
            <>
              <Dong ten="rớt cửa" so={tk.rot_cua} />
              <Dong ten="không vào lệnh" so={tk.khong_lenh} />
              <Dong ten="nã lệnh" so={tk.na_lenh} />
              <Dong ten="quá nặng" so={tk.qua_nang} />
              <Dong ten="trùng, bỏ qua" so={tk.trung_lap} />
              {!!tk.no && <Dong ten="bộ chạy từ chối" so={tk.no} xau />}
            </>
          ) : <div className="bdk-chu">chưa có số nào</div>}
        </section>

        {/* -------------------------------------------------------------- MÁY */}
        <section className="rl-o bdk-o">
          <div className="bdk-ten">MÁY</div>
          <div className="bdk-to">{daDung}<em> / {tongNhan} nhân</em></div>
          {/* ⭐ Kéo là ĂN NGAY. Máy tìm chạy hàng giờ trong chính app đang mở, nên
              "nhường lại máy" mà bắt dừng lượt chạy mới làm được thì không ai dùng.
              Rẻ vì chỉ thu hẹp cửa sổ công việc — không dựng lại bể tiến trình. */}
          <input className="bdk-keo" type="range" min={1} max={Math.max(1, tongNhan)}
                 value={daDung} disabled={!dangChay}
                 onChange={e => datNhan(+e.target.value)}
                 title="Kéo để nhường lại máy — ăn ngay, không đợi lượt sau" />
          <div className="bdk-dong"><span>mỗi sơ đồ</span>
            <b>{tt.giay_moi_luot != null ? `${tt.giay_moi_luot.toFixed(1)}s` : '—'}</b></div>
          <div className="bdk-dong"><span>gần đây</span>
            <b>{tt.giay_gan_day != null ? `${tt.giay_gan_day.toFixed(1)}s` : '—'}</b></div>
          <div className="bdk-dong"><span>mỗi giờ</span>
            <b>{tt.giay_moi_luot ? Math.round(3600 / tt.giay_moi_luot)
                                     .toLocaleString('vi-VN') : '—'}</b></div>
        </section>
      </div>

      {/* --- HÀNG GIỮA: đường "còn tìm được gì nữa" + nhóm đầu bảng cạnh nó ---
          Đặt cạnh nhau cố ý: đường trả lời *"dừng được chưa"*, mấy thẻ trả lời
          *"dừng thì được cái gì"*. Hai câu đi liền nhau. */}
      <div className="bdk-giua">
        <section className="rl-o rl-plot">
          <div className="rl-plot-dau">
            Số sơ đồ QUA CỬA theo số lượt đã chấm
            <span>còn tìm được gì nữa không — dừng được chưa</span>
          </div>
          <DuongQua duong={tt.duong_qua || []} daCham={tt.da_chay} tong={tt.tong}
                    dangChay={dangChay} />
        </section>

        <section className="rl-o bdk-dau-bang">
          <div className="pbc-dau">
            <b>ĐẦU BẢNG</b>
            <span>⚠ số TRAIN — và "dương n/m" mới là con số đáng đọc, không phải điểm</span>
          </div>
          {dauBang.length === 0 ? (
            <div className="rl-plot-trong">
              {dangChay ? 'chưa sơ đồ nào qua cửa' : 'không sơ đồ nào qua cửa'}
            </div>
          ) : (
            <div className="bdk-hang-db">
              {dauBang.slice(0, 8).map(d => (
                <button className="bdk-db" key={d.hang} onClick={() => moSoDo(d.hang)}
                        title="Mở sang cửa sổ vẽ">
                  <i>#{d.hang}</i>
                  <b className={(d.diem ?? 0) < 0 ? 'xau' : 'tot'}>
                    {d.diem?.toFixed(4)}</b>
                  <span className={dinhDeu(d) ? 'tot' : ''}>
                    dương {d.cua_so_duong ?? 0}/{d.so_cua_so ?? 0}
                  </span>
                  <em>{d.so_lenh?.toLocaleString('vi-VN')} lệnh · {d.so_nuoc} nước</em>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* --- BA PHÂN BỐ, cùng MỘT hàng. Chúng là đồ thị nhỏ, xếp ba ngang thì mỗi cái
          đủ rộng mà không ô nào bị kéo cao quá nội dung. --- */}
      <div className="bdk-hist">
        {/* ⚠ Phân bố ĐIỂM là ô đáng nhìn nhất khi hỏi "không gian này có gì không".
            Đo được: sơ đồ bốc bừa thua CÓ HỆ THỐNG, nên nếu cả đống dồn về bên trái
            mốc 0 thì đó không phải xui — đó là spread + hoa hồng. */}
        <PhanBoCot ten="Phân bố ĐIỂM" phu="cả đống, kể cả cái rớt cửa"
                   mep={MEP_DIEM} so={tk?.hist_diem || []} tot={THUNG_0} />
        <PhanBoCot ten="Phân bố SỐ LỆNH" phu="cấu trúc của rác"
                   mep={MEP_LENH} so={tk?.hist_lenh || []} />
        {/* ⭐ Ô này GIẢI THÍCH cái khoảng "còn bao lâu" ở hàng trên: cái đuôi bên phải
            chính là mấy con ngốn cả lô. */}
        <PhanBoCot ten="CHI PHÍ mỗi sơ đồ" phu="vì sao 'còn bao lâu' là một khoảng"
                   mep={MEP_GIAY} so={tk?.hist_giay || []} dv="s" />
      </div>
    </div>
  )
}

/** Có dương ở quá nửa cửa sổ không — cùng luật với cửa `deu_toi_thieu` (§18.5f). */
const dinhDeu = (d: DauBang) =>
  !!d.so_cua_so && (d.cua_so_duong ?? 0) * 2 > d.so_cua_so

function Dong({ ten, so, xau }: { ten: string; so?: number; xau?: boolean }) {
  return (
    <div className={'bdk-dong' + (xau ? ' xau' : '')}>
      <span>{ten}</span><b>{(so ?? 0).toLocaleString('vi-VN')}</b>
    </div>
  )
}

const giay = (tt: TrangThaiLuot) =>
  (tt.xong_luc ?? Date.now() / 1000) - tt.bat_dau

function lau(g: number): string {
  g = Math.max(0, Math.round(g))
  if (g < 60) return `${g}s`
  if (g < 3600) return `${Math.floor(g / 60)}m ${g % 60}s`
  return `${Math.floor(g / 3600)}h ${Math.floor((g % 3600) / 60)}m`
}

/** "Còn bao lâu" — một KHOẢNG, và im lặng khi chưa đủ mẫu.
 *
 * ⚠ Bản cũ đưa một con số (`trung bình × số còn lại`). Về thống kê nó không sai — tổng
 * của N mẫu độc lập thì ước bằng `N × trung bình` là chuẩn. Cái sai là TRƯNG NÓ RA NHƯ
 * MỘT CON SỐ CHÍNH XÁC, trong khi chi phí mỗi sơ đồ chênh nhau tới 1.000 lần (0,1 s →
 * 134 s) nên ở lượt thứ ba nó thuần tuý là bịa.
 *
 * Độ chắc tăng theo `√N`. Nên: dưới 30 mẫu thì không hiện gì; từ đó trở lên hiện một
 * khoảng (nhịp cả lượt ↔ nhịp gần đây), và khoảng ấy tự thu hẹp khi máy chạy lâu hơn. */
function conLai(tt: TrangThaiLuot, dangChay: boolean): string {
  if (!dangChay) return '—'
  if (!tt.du_de_uoc) return 'đang đo…'
  const a = tt.con_lai_som, b = tt.con_lai_muon
  if (a == null || b == null) return tt.con_lai != null ? lau(tt.con_lai) : '—'
  // Chênh dưới 10% thì hai đầu khoảng nói cùng một chuyện — đưa một số cho đỡ rối.
  if (b - a < Math.max(30, a * 0.1)) return lau((a + b) / 2)
  return `${lau(a)} – ${lau(b)}`
}
