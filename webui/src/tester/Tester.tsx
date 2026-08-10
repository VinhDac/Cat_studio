import { useEffect, useState } from 'react'
import { cho_cau_noi, pyTester } from '../api'
import TitleBar from '../components/TitleBar'
import { useKhungCuaSo } from '../useKhungCuaSo'
import type { ProcessDoc } from '../types'

/** Cửa sổ Strategy Tester.
 *
 * Hiện mới là KHUNG, và cái khung đó chính là phần khó: nó chứng minh đường đi đã
 * thông — cửa sổ thứ hai nạp được trang (không còn `file:///` → trang trắng), có
 * `ApiTester` riêng nên bấm ✕ ở đây KHÔNG đóng cửa sổ chính, có `KhungTuVe` riêng nên
 * kéo thanh tiêu đề không kéo nhầm cửa sổ chính, và đọc được sơ đồ đã đóng băng.
 *
 * Nội dung thật — chart · bảng số liệu · nhật ký — theo `core.md` §12.
 *
 * `TitleBar` dùng lại NGUYÊN VẸN: nó gọi `py.cua_so_*`, mà cầu nối tra hàm theo TÊN
 * trên đúng api của cửa sổ đang chạy, nên ở đây những cái tên đó rơi vào `ApiTester`.
 */
export default function Tester() {
  const [doc, setDoc] = useState<ProcessDoc | null>(null)
  const [loi, setLoi] = useState('')

  /* KHÔNG được quên: hook này mới là thứ gắn handler kéo/giãn, và nó nằm ở TRANG chứ
     không nằm trong `TitleBar`. Thiếu nó thì cửa sổ frameless mở ra đẹp nhưng không
     kéo được, không giãn được, không snap được — trông y như lỗi của `khung_cua_so`. */
  useKhungCuaSo(32)

  useEffect(() => {
    void (async () => {
      try {
        // Chờ `bootstrap_tester` chứ không phải `bootstrap`: cửa sổ này không có
        // `bootstrap`, chờ nhầm là treo 10 giây rồi báo mất kết nối.
        await cho_cau_noi('bootstrap_tester')
        const r = await pyTester.bootstrap_tester()
        if (!r.ok) return setLoi(r.error ?? 'không nạp được')
        if (r.value?.accent) {
          document.documentElement.style.setProperty('--accent', r.value.accent)
        }
        setDoc(r.value?.doc ?? null)
      } catch (e) {
        setLoi(String(e))
      }
    })()
    // Bấm ▶ lần nữa trong lúc cửa sổ này còn sống: Python KHÔNG tạo cửa sổ mới (làm
    // vậy là mất con trỏ, mức thu phóng, vị trí cuộn nhật ký) mà bắn sự kiện xuống.
    window.__su_kien = (ten, d) => {
      if (ten === 'so_do_moi') setDoc(d as ProcessDoc)
    }
  }, [])

  const dem = (t: 'entry' | 'manage') => doc?.[t]?.steps?.length ?? 0

  return (
    <div className="khung">
      <TitleBar tieuDe={doc ? `${doc.name} — Strategy Tester` : 'Strategy Tester'}
                menus={[]} />
      <div className="tester-trong">
        {loi ? <div className="tester-loi">{loi}</div>
          : !doc ? <div className="tester-mo">đang nạp sơ đồ…</div>
            : (
              <>
                <div className="tester-ten">{doc.name}</div>
                <div className="tester-phu">
                  {doc.symbol} · Entry {dem('entry')} khối · Manage {dem('manage')} khối
                </div>
                <div className="tester-ghi">
                  Chưa có bộ chạy. Thiết kế đầy đủ ở <code>core.md §12</code>.
                </div>
              </>
            )}
      </div>
    </div>
  )
}
