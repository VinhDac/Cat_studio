import { useMemo, useState } from 'react'
import Modal from '../components/Modal'
import type { KhoNen, NhomChon, RLBoot } from '../types'

/** CỬA SỔ CÀI ĐẶT của một lượt tìm — mọi thứ chỉnh được, mỗi mục một trang.
 *
 *     core.md §18.6.1, §18.9c
 *
 * ⭐ **Vì sao tách khỏi ribbon.** Ribbon cũ có sáu nút thả xuống, và cả sáu đều là đồ
 * ĐẶT MỘT LẦN — symbol, khoảng thời gian, chi phí, kho đồ, thang số, trần. Thứ thật sự
 * bấm nhiều chỉ có Chạy · Dừng · số sơ đồ · hạt giống. Sáu panel setup phục vụ hai cái
 * nút hành động là một cái ribbon đặt sai chỗ.
 *
 * Và mấy panel ấy vốn KHÔNG vừa một hộp thả xuống: panel Thưởng·Phạt gần 100 dòng, có
 * hai vế, hai nấc, sáu ô cửa và mấy đoạn giải thích — nhét vào khung 420 px là đọc
 * không nổi. Ở đây chúng có chỗ thở.
 *
 * ⚠ **Nội dung mấy trang này bê NGUYÊN từ ribbon sang, không viết lại.** Đổi chỗ ở và
 * đổi nội dung cùng lúc thì hỏng cái gì cũng không biết tại đổi chỗ hay tại viết lại.
 * Viết lại (nếu cần) là một lượt riêng.
 *
 * ⚠ Giấu cài đặt vào đây chỉ AN TOÀN nếu bàn điều khiển luôn hiện cấu hình đang chạy —
 * xem dải tóm tắt ở `RL.tsx`. Không có nó thì đây là quay lại chạy mù.
 */

/** Mọi thứ cửa sổ này chỉnh. Gom làm MỘT bọc thay vì hai chục props rời: hộp thoại này
 *  đúng là chỉnh tất, nên danh sách dài là sự thật chứ không phải chỗ để giấu. */
export interface DieuKhien {
  boot: RLBoot
  tat: Set<string>
  setTat: (f: (s: Set<string>) => Set<string>) => void
  tran: Record<string, number>
  setTran: (f: (t: Record<string, number>) => Record<string, number>) => void
  cua: Record<string, number | string | null>
  setCua: (f: (c: Record<string, number | string | null>) =>
    Record<string, number | string | null>) => void
  dat: Record<string, unknown>
  datD: (k: string, v: unknown) => void
  khoNen: KhoNen | null
  soLuot: number; setSoLuot: (n: number) => void
  hat: number; setHat: (n: number) => void
  giu: number; setGiu: (n: number) => void
  gioToiDa: number | null; setGioToiDa: (n: number | null) => void
  phangToiDa: number | null; setPhangToiDa: (n: number | null) => void
  soNhan: number; setSoNhan: (n: number) => void
}

/* ---- suy ra từ cài đặt. MỘT chỗ, vì `RL.tsx` cũng đọc mấy thứ này ---- */
export const kyCham = (cua: Record<string, unknown>) => (cua.ky as string) ?? 'tuan'
export const tenKyCua = (cua: Record<string, unknown>) =>
  (kyCham(cua) === 'thang' ? 'tháng' : 'tuần')
/** Vế DAO ĐỘNG có tham gia không — `0` chỉ nhìn lãi · `1` cân bằng. */
export const manhDeuCua = (cua: Record<string, unknown>) =>
  (cua.manh_deu as number | null) ?? 1
export const coKhoaCua = (dat: Record<string, unknown>) => !!(dat.khoa_tu && dat.khoa_den)
export const cuonCua = (dat: Record<string, unknown>) =>
  String(dat.cach_chia ?? 'cuon_toi') === 'cuon_toi'
export const buocCua = (dat: Record<string, unknown>) => String(dat.buoc_cuon ?? 'quy')

export const TEN_BUOC: Record<string, string> = {
  thang: 'tháng', quy: 'quý', nua_nam: 'nửa năm' }

/** Bảng bật/tắt THẺ — dùng chung cho trang "Kho đồ" và "Thang số".
 *
 * ⭐ Không phân biệt hai trang: với giao diện, "tắt toán hạng ATR" và "tắt nấc SL 1,5"
 * là **cùng một việc** — bỏ một chuỗi thẻ vào tập `tat`. Nhờ vậy Python thêm chiều mới
 * (chế độ sửa, khung giờ, một thang nữa) là trang dài ra, JS không sửa một dòng nào. */
function ChonThe({ nhom, tat, datTat }: {
  nhom: NhomChon[]
  tat: Set<string>
  datTat: (f: (s: Set<string>) => Set<string>) => void
}) {
  const bat = (the: string) => datTat(s => {
    const n = new Set(s)
    if (n.has(the)) n.delete(the); else n.add(the)
    return n
  })
  /** Bật/tắt CẢ NHÓM — 22 toán hạng mà bấm từng cái thì không ai dùng. */
  const caNhom = (g: NhomChon, tatHet: boolean) => datTat(s => {
    const n = new Set(s)
    for (const m of g.muc) { if (tatHet) n.add(m.the); else n.delete(m.the) }
    return n
  })

  return (
    <>
      {nhom.map(g => {
        const off = g.muc.filter(m => tat.has(m.the)).length
        return (
          <div className="rl-nhom" key={g.nhom}>
            <div className="rl-nhom-ten">
              <span>{g.nhan}{g.don_vi && <em> · {g.don_vi}</em>}</span>
              <button onClick={() => caNhom(g, off < g.muc.length)}>
                {off < g.muc.length ? 'tắt hết' : 'bật hết'}
              </button>
            </div>
            <div className="rl-chip-hang">
              {g.muc.map(m => (
                <button key={m.the}
                        title={m.z ? 'cần cổng zone đứng trước (§12.6c)'
                                   : m.manage ? 'chỉ dùng được ở sơ đồ Manage' : ''}
                        className={'rl-chip' + (tat.has(m.the) ? ' tat' : '')}
                        onClick={() => bat(m.the)}>
                  {m.nhan}
                  {m.z && <span className="rl-z">z</span>}
                  {m.manage && <span className="rl-z rl-m">m</span>}
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </>
  )
}


/* ======================================================== các TRANG ==== */

function TrangKhoDo({ d }: { d: DieuKhien }) {
  const { boot, tat, setTat } = d
  const nhomKho = useMemo(
    () => d.boot.chon.filter(g => g.cho === 'kho'), [d.boot])
  return (
    <>
          <p className="rl-giai">
            Tắt bớt là <b>lần này tôi không muốn dùng</b> — không phải "cái này hỏng".
            Luật thì không tắt được.
          </p>
          <ChonThe nhom={nhomKho} tat={tat} datTat={setTat} />
          <div className="rl-nho">{boot.so_nuoc_di.toLocaleString('vi-VN')} nước đi
            trong kho — thêm một toán hạng là kho tự lớn.</div>
    </>
  )
}

function TrangThangSo({ d }: { d: DieuKhien }) {
  const { boot, tat, setTat } = d
  const nhomThang = useMemo(
    () => d.boot.chon.filter(g => g.cho === 'thang'), [d.boot])
  return (
    <>
          <p className="rl-giai">
            Máy <b>không dò số tự do</b>, nó chọn nấc. Đo được: dò SL thang mịn bước
            0,1 trên 2025 ra <i>2,7</i> — thắng năm đó, nhưng sang ba năm chưa thấy thì
            THUA cả bản thô <i>3,0</i>. Hai nấc cạnh nhau lệch trung bình 5,11 R: đó là
            nhiễu, không phải tín hiệu.
          </p>
          <ChonThe nhom={nhomThang} tat={tat} datTat={setTat} />
          <div className="rl-nho">
            Tắt một nấc <b>không đụng tới kho nước đi</b> — kho vẫn nguyên
            {' '}{boot.so_nuoc_di.toLocaleString('vi-VN')} ô, chỉ là mấy ô mang nấc đó
            bị che. Sửa thang thật thì một mạng đã học phải học lại; che thì không.
          </div>
    </>
  )
}

function TrangTran({ d }: { d: DieuKhien }) {
  const { tran, setTran } = d
  return (
    <>
          <p className="rl-giai">
            Chỉ áp cho <b>máy</b> — bạn vẽ tay bao nhiêu khối cũng được. Người vẽ 28
            khối thì biết mình đang làm gì; máy sinh 28 khối là nó bịa.
          </p>
          {[['dk_moi_cong', 'điều kiện một cổng'],
            ['nhanh_moi_re', 'nhánh một ngã rẽ'],
            ['khoi_entry', 'khối sơ đồ Entry'],
            ['khoi_manage', 'khối sơ đồ Manage']].map(([k, nhan]) => (
            <label className="rl-hang" key={k}>
              <span>{nhan}</span>
              <input type="number" min={1} max={40} value={tran[k] ?? 0}
                     onChange={e => setTran(t => ({ ...t, [k]: +e.target.value }))} />
            </label>
          ))}
    </>
  )
}

function TrangThuongPhat({ d }: { d: DieuKhien }) {
  const { boot, cua, setCua } = d
  const manhDeu = manhDeuCua(cua)
  const tenKy = tenKyCua(cua)
  const ky = kyCham(cua)
  return (
    <>
          <div className="rl-nhom-ten rl-to"><span>THƯỞNG — cái máy đi tìm</span></div>
          <div className="rl-cong-thuc">
            điểm = <b>{manhDeu <= 0 ? 'trung bình' : 'trung bình ÷ dao động'}</b>
            <em>{manhDeu <= 0 ? 'chỉ vế trên' : 'cả hai vế'}</em>
          </div>
          {/* HAI VẾ, tách ra nhìn thấy. Một công thức gộp thì không nâng riêng được
              vế nào — mà đó đúng là câu hỏi: "kiếm nhiều" và "kiếm đều" là hai thứ
              khác nhau, và người dùng phải nói được mình đang ưu tiên cái nào. */}
          <div className="rl-ve">
            <div>
              <i>vế TRÊN</i><b>trung bình</b>
              <span>lãi mỗi {tenKy}, tính bằng <b>% vốn ĐẦU</b> — kiếm được
                <b> bao nhiêu</b></span>
            </div>
            <div className={manhDeu <= 0 ? 'tat' : ''}>
              <i>vế DƯỚI</i><b>dao động</b>
              <span>chuỗi lãi {tenKy} lệch nhau bao nhiêu — kiếm có
                <b> đều</b> không</span>
            </div>
          </div>

          <div className="rl-nhom-ten"><span>nâng vế nào</span></div>
          <div className="rl-chip-hang">
            {([[0, 'CHỈ NHÌN LÃI'], [1, 'CÂN BẰNG']] as const).map(([k, n]) => (
              <button key={k}
                      className={'rl-chip' + (manhDeu === k ? '' : ' tat')}
                      onClick={() => setCua(c => ({ ...c, manh_deu: k }))}>{n}</button>
            ))}
          </div>
          <p className="rl-nho">
            <b>Chỉ nhìn lãi</b> bỏ hẳn vế dưới — máy đi tìm cái kiếm nhiều, mặc kệ
            giật cục. <b>Cân bằng</b> chia cho dao động: cùng một mức lãi thì cái đều
            hơn thắng.
          </p>
          <p className="rl-nho">
            ⚠ <b>Không có nấc thứ ba</b> ("ưu tiên đều", chia cho dao động bình
            phương) — đã thử rồi bỏ. Đo trên sơ đồ mẫu: trung bình <i>−0,161%</i> ·
            dao động <i>1,115%</i> ⇒ cân bằng cho <i>−0,1446</i> còn nấc ấy cho
            <i> −0,1296</i>, tức nó chấm <b>CAO HƠN</b>. Vì trung bình ÂM thì càng
            chia càng gần 0. Muốn siết chặt hơn thì dùng cửa <b>dao động tối đa</b> ở
            phần PHẠT — nó phát biểu được, và không đụng vào thước.
          </p>
          <p className="rl-nho">
            Cái THƯỚC vẫn KHÔNG chỉnh được: hai vế đều đo bằng thứ cố định. Bạn chỉnh
            <i> coi trọng vế nào</i>, không chỉnh <i>đo bằng gì</i>.
          </p>

          <div className="rl-nhom-ten"><span>chấm theo kỳ</span></div>
          <div className="rl-chip-hang">
            {[['tuan', 'TUẦN'], ['thang', 'THÁNG']].map(([k, n]) => (
              <button key={k} className={'rl-chip' + (ky === k ? '' : ' tat')}
                      onClick={() => setCua(c => ({ ...c, ky: k }))}>{n}</button>
            ))}
          </div>
          <p className="rl-nho">
            Đổi kỳ KHÔNG phải đổi thước — vẫn là trung bình ÷ dao động, chỉ đổi độ
            phân giải nhìn. Tuần bắt được cái giật cục mà tháng làm mượt mất.
          </p>

          <label className="rl-hang">
            <span>{tenKy} có lệnh tối thiểu</span>
            <input type="number" min={boot.tuan_co_lenh_toi_thieu * 100} max={100}
                   value={Math.round(((cua.tuan_co_lenh as number) ?? 0) * 100)}
                   onChange={e => setCua(c => ({
                     ...c, tuan_co_lenh: +e.target.value / 100 }))} />
            <em>%</em>
          </label>
          <p className="rl-nho">
            Khoá cứng ở {Math.round(boot.tuan_co_lenh_toi_thieu * 100)}% — siết thêm
            được, nới ra thì không. Một sơ đồ vào <b>đúng một lệnh</b> trong 3,5 năm ăn
            điểm cao hơn sơ đồ vào 929 lệnh; cái cửa này chặn đúng chỗ đó.
          </p>

          <div className="rl-nhom-ten rl-to"><span>PHẠT — loại thẳng</span></div>
          <p className="rl-nho">
            ⚠ Phạt ở đây là <b>nhị phân</b>: rớt một cửa là loại, không phải trừ điểm.
            Có chủ ý — sụt vốn không đổi chác được với lãi, cháy 60% tài khoản thì
            không mức lãi nào bù lại. Và <i>"tôi không nhận sụt quá 25%"</i> là câu
            phát biểu được, còn một hệ số phạt thì phải dò mới biết nặng hay nhẹ — mà
            dò cái nút chấm điểm là dò trên chính thứ dùng để chấm.
          </p>
          {([['so_lenh_toi_thieu', 'số lệnh tối thiểu', 'lệnh'],
             ['sut_von_toi_da', 'sụt vốn tối đa', '%'],
             ['te_nhat_toi_da', `${tenKy} tệ nhất không quá`, '%'],
             ['dao_dong_toi_da', `dao động ${tenKy} tối đa`, '%'],
             ['lai_toi_thieu', 'lãi tối thiểu', '%/năm'],
             ['diem_toi_thieu', 'điểm tối thiểu', '']] as const).map(([k, nhan, dv]) => (
            <label className="rl-hang" key={k}>
              <span>{nhan}</span>
              <input type="number" step="any" placeholder="không lọc"
                     value={(cua[k] as number | null) ?? ''}
                     onChange={e => setCua(c => ({
                       ...c, [k]: e.target.value === '' ? null : +e.target.value }))} />
              <em>{dv}</em>
            </label>
          ))}
          <div className="rl-nho">Để trống là không lọc.</div>
    </>
  )
}

function TrangDuLieu({ d }: { d: DieuKhien }) {
  const { dat, datD, khoNen } = d
  const coKhoa = coKhoaCua(dat)
  const cuon = cuonCua(dat)
  const buoc = buocCua(dat)
  return (
    <>
          <p className="rl-giai">
            ⭐ <b>Cài đặt RIÊNG của RL</b>, không dùng chung với Strategy Test. Tester
            có đúng MỘT khoảng; RL cần ít nhất HAI — đoạn máy đào thoải mái, và đoạn
            KHOÁ mở đúng một lần.
          </p>
          <label className="rl-hang">
            <span>symbol</span>
            <input value={String(dat.symbol ?? '')} spellCheck={false}
                   onChange={e => datD('symbol', e.target.value.toUpperCase())} />
          </label>
          {khoNen && (
            <div className={'rl-kho-nen' + (khoNen.co ? '' : ' xau')}>
              {khoNen.co
                ? <>kho có <b>{(khoNen.so_nen ?? 0).toLocaleString('vi-VN')}</b> nến M1
                    {' · '}{khoNen.tu} → {khoNen.den}</>
                : <>⚠ chưa có nến nào cho «{khoNen.symbol}» — chạy sẽ phải tải từ MT5</>}
            </div>
          )}

          <div className="rl-nhom-ten"><span>TRAIN — máy đào thoải mái</span></div>
          <label className="rl-hang"><span>từ</span>
            <input value={String(dat.tu ?? '')} placeholder="2021-07-01"
                   onChange={e => datD('tu', e.target.value)} /></label>
          <label className="rl-hang"><span>đến</span>
            <input value={String(dat.den ?? '')} placeholder="2025-01-01"
                   onChange={e => datD('den', e.target.value)} /></label>

          <div className="rl-nhom-ten"><span>KHOÁ — mở đúng một lần</span></div>
          <label className="rl-hang"><span>từ</span>
            <input value={String(dat.khoa_tu ?? '')} placeholder="2025-01-01"
                   onChange={e => datD('khoa_tu', e.target.value)} /></label>
          <label className="rl-hang"><span>đến</span>
            <input value={String(dat.khoa_den ?? '')} placeholder="2026-01-01"
                   onChange={e => datD('khoa_den', e.target.value)} /></label>
          <p className={'rl-nho' + (coKhoa ? '' : ' rl-canh')}>
            {coKhoa
              ? <>Đã mở <b>{Number(dat.khoa_da_mo ?? 0)}</b> lần. Không cấm bấm — nhưng
                  nhìn một đoạn đủ nhiều lần thì nó thôi là "chưa thấy", và cái đồng hồ
                  này là chỗ duy nhất nói ra chuyện đó.</>
              : <>⚠ Chưa đặt đoạn khoá — <b>mọi con số sẽ chỉ là số TRAIN</b>, đo trên
                  chính đoạn máy vừa đào bới. Đặt một khoảng KHÔNG nằm trong train.</>}
          </p>

          <div className="rl-nhom-ten"><span>cách chia thời gian</span></div>
          <div className="rl-chip-hang">
            {([['mot_khoi', 'MỘT KHỐI'], ['cuon_toi', 'CUỐN TỚI']] as const)
              .map(([k, n]) => (
              <button key={k}
                      className={'rl-chip' + (cuon === (k === 'cuon_toi')
                                              ? '' : ' tat')}
                      onClick={() => datD('cach_chia', k)}>{n}</button>
            ))}
          </div>
          {cuon && (
            <>
              <div className="rl-nhom-ten" style={{ marginTop: 8 }}>
                <span>bước mỗi cửa sổ</span></div>
              <div className="rl-chip-hang">
                {(['thang', 'quy', 'nua_nam'] as const).map(k => (
                  <button key={k} className={'rl-chip' + (buoc === k ? '' : ' tat')}
                          onClick={() => datD('buoc_cuon', k)}>{TEN_BUOC[k]}</button>
                ))}
              </div>
            </>
          )}
          <p className="rl-nho">
            {cuon
              ? <>Đoạn khoá bị cắt thành nhiều <b>cửa sổ nối nhau</b>, chấm từng cái.
                  Vì "kiếm đều" chỉ có nghĩa khi đo <b>qua thời gian</b>: đo được trên
                  XAUUSD, một sơ đồ điểm gộp <i>+0,0009</i> mà chỉ <b>8/18</b> quý
                  dương. Một con số gộp cả dải giấu mất chuyện đó.</>
              : <>Cả đoạn khoá chấm thành <b>một con số</b>. Gọn, nhưng nó vẫn đẹp với
                  sơ đồ ăn đậm quý đầu rồi lỗ năm quý sau.</>}
          </p>
          <p className="rl-nho">
            ⚠ Bước nhỏ nhất là <b>tháng</b>, không có "tuần". Đo được: hai chiến lược
            chênh nhau 38 điểm % qua 4,5 năm mà xét từng tuần chỉ hơn nhau ở
            <b> 52%</b> số tuần — tung đồng xu. Một tuần lẻ không mang tin.
          </p>

          <div className="rl-nhom-ten"><span>Chi phí</span></div>
          {([['deposit', 'vốn', '$'], ['commission', 'hoa hồng', '$/lot'],
             ['spread_diem', 'spread', 'điểm'],
             ['truot_diem', 'trượt giá', 'điểm']] as const).map(([k, nhan, dv]) => (
            <label className="rl-hang" key={k}>
              <span>{nhan}</span>
              <input type="number" step="any" value={String(dat[k] ?? '')}
                     onChange={e => datD(k, e.target.value === '' ? 0
                                            : +e.target.value)} />
              <em>{dv}</em>
            </label>
          ))}
          <div className="rl-nho">
            Spread <b>0</b> = lấy trung vị đo được lúc tải nến
            {khoNen?.spread_tb ? ` (${khoNen.spread_tb} điểm)` : ''}. Đo được: spread
            bịa 20 điểm biến một chiến lược thua thành thắng.
          </div>
    </>
  )
}

function TrangNganSach({ d }: { d: DieuKhien }) {
  const { dat, datD, soLuot, setSoLuot, giu, setGiu, hat, setHat,
          gioToiDa, setGioToiDa, phangToiDa, setPhangToiDa,
          soNhan, setSoNhan } = d
  return (
    <>
          <label className="rl-hang">
            <span>số sơ đồ thử</span>
            <input type="number" min={1} max={500000} value={soLuot}
                   onChange={e => setSoLuot(+e.target.value)} />
          </label>
          <label className="rl-hang">
            <span>giữ lại đầu bảng</span>
            <input type="number" min={1} max={100} value={giu}
                   onChange={e => setGiu(+e.target.value)} />
          </label>
          <label className="rl-hang">
            <span>hạt giống</span>
            <input type="number" value={hat} onChange={e => setHat(+e.target.value)} />
          </label>
          <p className="rl-nho">
            Cùng hạt giống + cùng dữ liệu = <b>cùng kết quả</b>, luôn luôn. Không thế
            thì "cách này hơn cách kia" là câu không kiểm được.
          </p>

          <div className="rl-nhom-ten"><span>Dừng sớm</span></div>
          <label className="rl-hang">
            <span>chạy tối đa</span>
            <input type="number" min={0} step={0.5} placeholder="không giới hạn"
                   value={gioToiDa ?? ''}
                   onChange={e => setGioToiDa(
                     e.target.value === '' ? null : +e.target.value)} />
            <em>giờ</em>
          </label>
          <p className="rl-nho">
            Chạy qua đêm thì đặt <b>giờ</b> hợp lý hơn đặt số lượt: chi phí mỗi sơ đồ
            dao động 3–24 giây tuỳ nó đẻ ra bao nhiêu lệnh, nên "10.000 sơ đồ" không
            dịch được ra mấy tiếng.
          </p>
          <label className="rl-hang">
            <span>dừng khi phẳng</span>
            <input type="number" min={0} placeholder="không dừng"
                   value={phangToiDa ?? ''}
                   onChange={e => setPhangToiDa(
                     e.target.value === '' ? null : +e.target.value)} />
            <em>lượt</em>
          </label>
          <p className="rl-nho">
            Ngần này lượt liền mà điểm tốt nhất không nhúc nhích thì tự tắt — bản tự
            động của thứ đồ thị đang mách bằng mắt.
          </p>

          <div className="rl-nhom-ten rl-to"><span>SONG SONG</span></div>
          <label className="rl-hang">
            <span>số nhân</span>
            <input type="number" min={0} max={64} placeholder="tự chọn"
                   value={soNhan || ''}
                   onChange={e => setSoNhan(e.target.value === ''
                                            ? 0 : +e.target.value)} />
            <em>tiến trình</em>
          </label>
          <p className="rl-nho">
            Để trống là <b>tự chọn</b> — số nhân của máy trừ đi 2. Chừa lại 2 là cố ý:
            máy tìm chạy hàng giờ ngay trong app đang mở, ăn hết sạch nhân thì cửa sổ
            giật và bạn không kéo nổi một cái panel. Nhanh hơn 8% không đáng đổi lấy
            tám tiếng app đơ.
          </p>
          <p className="rl-nho">
            ⭐ Phải là <b>tiến trình</b>, không phải luồng: bộ chạy là Python thuần và
            GIL chỉ cho một luồng chạy bytecode tại một thời điểm — tám luồng nhanh
            bằng đúng một luồng. Và <b>8 nhân cho kết quả y hệt 1 nhân</b>: sơ đồ vẫn
            do tiến trình cha bốc theo đúng thứ tự hạt giống, kết quả vẫn gộp theo
            đúng thứ tự ấy chứ không theo thứ tự nhân nào xong trước.
          </p>
          <p className="rl-nho">
            Đây cũng chính là <b>nửa actor</b> của một hệ RL — cái đàn tiến trình này
            dùng lại được nguyên vẹn khi nào gắn mạng.
          </p>

          <div className="rl-nhom-ten rl-to"><span>CẮT RÁC</span></div>
          <label className="rl-hang">
            <span>trần nhịp vào lệnh</span>
            <input type="number" min={0} placeholder="không cắt"
                   value={Number(dat.lenh_moi_tuan_toi_da ?? 0) || ''}
                   onChange={e => datD('lenh_moi_tuan_toi_da',
                                       e.target.value === '' ? 0 : +e.target.value)} />
            <em>lệnh/tuần</em>
          </label>
          <p className="rl-nho">
            ⭐ Đây là ô <b>quan trọng nhất</b> của panel này, và nó là van <b>thời
            gian</b> chứ không phải một cái cửa. Vượt trần thì <b>bỏ dở ngay giữa
            chừng</b>, không chấm nốt — vì chi phí một lượt chấm đi theo <b>số lệnh</b>
            sơ đồ đẻ ra, không theo số nến.
          </p>
          <p className="rl-nho">
            Đo được: máy sinh ra sơ đồ <b>11.425 lệnh trong một quý</b> (≈ 879/tuần),
            trong khi sơ đồ mẫu người viết là <b>≈ 4/tuần</b>. Chính mấy con ấy nuốt
            hết ngân sách — 15 phút chỉ chấm nổi <b>38</b> sơ đồ.
          </p>
          <p className="rl-nho">
            200/tuần ≈ 40 lệnh một ngày, cao hơn hẳn mọi chiến lược thật — nó cắt rác
            mà không phán xét phong cách. Còn <i>"vào lệnh thế nào là hợp lý"</i> là
            việc của mấy cái cửa ở <b>Thưởng·Phạt</b>. Để <b>0</b> là không cắt.
          </p>
          <p className="rl-nho rl-canh">
            ⚠ Chỉ áp cho máy tìm. Bạn vẽ tay bao nhiêu lệnh cũng được — Strategy Test
            không có ô này.
          </p>
    </>
  )
}


/* ========================================================= vỏ cửa sổ ==== */

/** GHI CHÚ — vì sao lượt này đặt như thế.
 *
 * ⭐ Không phải đồ trang trí. Chạy tới lượt thứ hai mươi thì không ai nhớ nổi vì sao
 * lượt số bảy đặt `chỉ nhìn lãi`, hay vì sao lượt kia tắt hết khung giờ lớn. Bảng số
 * nói CÁI GÌ xảy ra; chỗ này là chỗ duy nhất nói ĐỊNH LÀM GÌ. */
function TrangGhiChu({ d }: { d: DieuKhien }) {
  return (
    <>
      <p className="rl-giai">
        Ghi lại <b>vì sao</b> lượt này đặt như thế — thứ bảng số không bao giờ nói được.
        Nó được <b>chụp lại theo mỗi lượt chạy</b>, nên đọc lại lượt cũ là thấy đúng ý
        định lúc bấm Chạy, không phải ý định hôm nay.
      </p>
      <textarea className="rl-ghi-chu" spellCheck={false}
                placeholder={'ví dụ:\nthử bỏ vế dao động xem máy có đi tìm cái lãi to\n'
                             + 'hơn không — nghi là cửa "tuần có lệnh" đang giết hết\n'
                             + 'mấy sơ đồ đánh thưa'}
                value={String(d.dat.ghi_chu ?? '')}
                onChange={e => d.datD('ghi_chu', e.target.value)} />
    </>
  )
}

/** ⚠ `ve` là một COMPONENT, không phải hàm trả JSX — và phải dựng bằng `<m.ve d={…} />`,
 *  KHÔNG gọi `m.ve(d)`.
 *
 *  Đây là một lỗi đã cắn thật: gọi như hàm thường thì mấy cái hook bên trong trang
 *  (`useMemo` ở Kho đồ và Thang số) trở thành hook của CHÍNH `CuaSoCaiDat`. Đổi từ
 *  "Kho đồ" (1 hook) sang "Trần" (0 hook) là số hook giữa hai lần vẽ khác nhau, React
 *  ném lỗi và cả cửa sổ RL chết. Dựng bằng JSX thì mỗi trang là một component riêng,
 *  đổi trang là tháo cái này lắp cái kia — hook muốn thêm bao nhiêu cũng được. */
const MUC: Array<{ khoa: string; nhan: string; nhom: string
                   ve: (p: { d: DieuKhien }) => JSX.Element
                   tom: (d: DieuKhien) => string }> = [
  { khoa: 'kho', nhan: 'Kho đồ', nhom: 'Luật chơi', ve: TrangKhoDo,
    tom: d => demThe(d, 'kho') },
  { khoa: 'thang', nhan: 'Thang số', nhom: 'Luật chơi', ve: TrangThangSo,
    tom: d => demThe(d, 'thang') },
  { khoa: 'tran', nhan: 'Trần độ phức tạp', nhom: 'Luật chơi', ve: TrangTran,
    tom: d => `${d.tran.dk_moi_cong}·${d.tran.nhanh_moi_re}`
              + `·${d.tran.khoi_entry}·${d.tran.khoi_manage}` },
  { khoa: 'cua', nhan: 'Thưởng · Phạt', nhom: 'Luật chơi', ve: TrangThuongPhat,
    tom: d => nhanCua(d) },
  { khoa: 'du_lieu', nhan: 'Dữ liệu', nhom: 'Chạy trên gì', ve: TrangDuLieu,
    tom: d => `${d.dat.symbol || '—'}${coKhoaCua(d.dat) ? ' · có khoá' : ''}` },
  { khoa: 'ngan', nhan: 'Ngân sách', nhom: 'Chạy trên gì', ve: TrangNganSach,
    tom: d => (d.gioToiDa ? `${d.gioToiDa}h` : d.soLuot.toLocaleString('vi-VN'))
              + ` · ${d.soNhan || 'tự'} nhân` },
  { khoa: 'ghi_chu', nhan: 'Ghi chú', nhom: 'Chạy trên gì', ve: TrangGhiChu,
    tom: d => (String(d.dat.ghi_chu ?? '').trim() ? 'có' : '—') },
]

function demThe(d: DieuKhien, cho: string) {
  const gs = d.boot.chon.filter(g => g.cho === cho)
  const tong = gs.reduce((s, g) => s + g.muc.length, 0)
  const off = gs.reduce((s, g) => s + g.muc.filter(m => d.tat.has(m.the)).length, 0)
  return `${tong - off}/${tong}`
}

/** Nhãn của trang Thưởng·Phạt. ⚠ `manh_deu` KHÔNG được đếm vào "n phạt" — nó là nút
 *  của vế THƯỞNG, đếm vào đó thì nhãn nói dối ngay từ ngoài. */
export function nhanCua(d: DieuKhien): string {
  const n = Object.entries(d.cua).filter(
    ([k, v]) => v !== null
      && k !== 'ky' && k !== 'tuan_co_lenh' && k !== 'manh_deu').length
  const g = manhDeuCua(d.cua) <= 0 ? `${tenKyCua(d.cua)} · chỉ lãi` : tenKyCua(d.cua)
  return n ? `${g} · ${n} phạt` : g
}

export default function CuaSoCaiDat({ d, onClose, mucDau }: {
  d: DieuKhien; onClose: () => void; mucDau?: string
}) {
  const [muc, setMuc] = useState(mucDau || MUC[0].khoa)
  const m = MUC.find(x => x.khoa === muc) || MUC[0]
  const nhom = [...new Set(MUC.map(x => x.nhom))]

  return (
    <Modal title="Cài đặt lượt tìm" width={980} onClose={onClose}>
      <div className="ct-vo">
        <nav className="ct-muc">
          {nhom.map(g => (
            <div key={g}>
              <div className="ct-nhom">{g}</div>
              {MUC.filter(x => x.nhom === g).map(x => (
                <button key={x.khoa}
                        className={'ct-nut' + (x.khoa === muc ? ' dang' : '')}
                        onClick={() => setMuc(x.khoa)}>
                  <b>{x.nhan}</b>
                  <em>{x.tom(d)}</em>
                </button>
              ))}
            </div>
          ))}
        </nav>
        <div className="ct-trang">
          <h3>{m.nhan}</h3>
          <m.ve d={d} />
        </div>
      </div>
    </Modal>
  )
}
