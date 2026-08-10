import React from 'react'
import ReactDOM from 'react-dom/client'
// THỨ TỰ QUAN TRỌNG: stylesheet gốc của React Flow phải nạp TRƯỚC app.css.
// Trước đây nó được import trong App.tsx, mà App lại import SAU css của mình, nên
// nó nằm cuối bundle và đè mất — vùng bấm cổng nối vẫn là 6px dù đã khai 24px.
import '@xyflow/react/dist/style.css'
import './theme.css'
import './app.css'
import App from './App'
import Tester from './tester/Tester'

/** Rẽ trang bằng `?tester=1` — KHÔNG thêm entry thứ hai cho Vite.
 *
 * `api.py` gắn sẵn `?tester=1` vào url cửa sổ Strategy Tester từ lâu, nhưng trước đây
 * KHÔNG chỗ nào đọc nó, nên cửa sổ thứ hai dựng lại y hệt trình soạn thảo — hai thanh
 * tiêu đề, hai ribbon, và mọi lời gọi `py.*` đều nhắm vào cửa sổ chính.
 *
 * Một dòng `if` ở đây rẻ hơn hẳn `build.rollupOptions.input`: một bundle, một `app.css`
 * toàn cục, dùng chung được `TitleBar` / `Modal` / `Icon` mà không phải tách gì. */
const laTester = new URLSearchParams(location.search).get('tester') === '1'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {laTester ? <Tester /> : <App />}
  </React.StrictMode>,
)
