"""Cat_Studio — điểm khởi động cửa sổ (pywebview + WebView2).

    python app_web.py

Giao diện là React + React Flow chạy trong WebView2; Python lo lõi.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Tiêu đề lúc mở. Sau đó JS ghi đè thành "<tên chiến lược> — Cat Studio".
TIEU_DE_GOC = "Cat Studio"

def _uu_tien_namespace_dotnet():
    """Cho namespace .NET thắng gói Python cùng tên. PHẢI chạy TRƯỚC `import webview`.

    pywebview (backend WinForms) cần `Microsoft.Win32.SystemEvents` — một namespace
    .NET. pythonnet gắn bộ tìm của nó vào CUỐI `sys.meta_path`, tức là SAU bộ tìm đọc
    `site-packages`. Nên chỉ cần môi trường có một gói tên `Microsoft/` là gói đó cướp
    mất tên: `quantconnect-stubs` chẳng hạn ship đúng một cái như thế, và app chết ngay
    lúc mở cửa sổ với `FileNotFoundException: Could not load ... 'Microsoft'` — một câu
    không liên quan gì tới lỗi thật.

    Đẩy bộ tìm của pythonnet lên đầu là hết. Nó chỉ nhận những namespace .NET có thật,
    nên không gói Python nào bị nó nuốt nhầm."""
    try:
        import clr                                # noqa: F401  (gắn DotNetFinder)
    except Exception:
        return                                    # không có pythonnet -> kệ, để lỗi sau
    for f in [x for x in sys.meta_path if type(x).__name__ == "DotNetFinder"]:
        sys.meta_path.remove(f)
        sys.meta_path.insert(0, f)


_uu_tien_namespace_dotnet()

import webview                                    # noqa: E402
from api import Api                               # noqa: E402
import luu_tru                                    # noqa: E402


# .NET Framework tối thiểu. `Python.Runtime.dll` của pythonnet 3.x build cho
# .NET Standard 2.0, mà .NET Framework chỉ nạp được netstandard2.0 từ 4.7.2 trở đi.
# Thiếu nó là hỏng ngay lúc pywebview khởi động, TRƯỚC khi một dòng code nào của app
# chạy — nên phải kiểm sớm và nói bằng tiếng người thay vì ném ra một hộp traceback.
DOTNET_TOI_THIEU = 461808        # = .NET Framework 4.7.2
KHOA_DOTNET = r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full"
KHOA_WEBVIEW2 = (r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
                 r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}")


def thieu_dotnet(release):
    """`release` = số trong registry, None nếu máy không có .NET v4. True = thiếu."""
    if release is None:
        return True
    try:
        return int(release) < DOTNET_TOI_THIEU
    except (TypeError, ValueError):
        return True          # đọc ra thứ không phải số -> coi như không tin được


def _doc_registry(goc, duong, ten):
    """Đọc một giá trị registry, thử cả hai view 32/64-bit rồi mới chịu thua."""
    import winreg
    for view in (0, winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(goc, duong, 0, winreg.KEY_READ | view) as k:
                return winreg.QueryValueEx(k, ten)[0]
        except OSError:
            continue
    return None


def kiem_moi_truong():
    """Những thứ Windows PHẢI có sẵn. Trả về danh sách vấn đề; rỗng nghĩa là đủ."""
    import winreg
    van_de = []
    rel = _doc_registry(winreg.HKEY_LOCAL_MACHINE, KHOA_DOTNET, "Release")
    if thieu_dotnet(rel):
        van_de.append(
            "THIẾU .NET Framework 4.7.2 trở lên"
            + (f" (máy đang có bản cũ hơn, mã {rel})" if rel
               else " (máy chưa cài .NET Framework 4)")
            + ".\n   Tải tại: https://dotnet.microsoft.com/download/dotnet-framework")

    # WebView2: Windows 10/11 thường có sẵn theo Edge, nhưng Windows Server và mấy
    # bản Windows gọt nhẹ thì không.
    pv = (_doc_registry(winreg.HKEY_LOCAL_MACHINE, KHOA_WEBVIEW2, "pv")
          or _doc_registry(winreg.HKEY_CURRENT_USER, KHOA_WEBVIEW2, "pv"))
    if not pv:
        van_de.append(
            "THIẾU Microsoft Edge WebView2 Runtime.\n"
            "   Tải tại: https://developer.microsoft.com/microsoft-edge/webview2/")
    return van_de


def bao_loi(tieu_de, noi_dung):
    """Hộp thoại lỗi của Windows.

    Bản đóng gói chạy `--windowed` nên KHÔNG có console: in ra stderr thì không ai
    thấy, người dùng chỉ thấy app im lặng không mở lên."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, noi_dung, tieu_de, 0x10 | 0x1000)
    except Exception:
        print(f"{tieu_de}: {noi_dung}", file=sys.stderr)


def duong_dan_giao_dien():
    """Trang giao diện đã build. Chưa build thì báo rõ phải chạy npm chứ không mở một
    cửa sổ trắng rồi để người dùng tự đoán."""
    return os.path.join(HERE, "webui", "dist", "index.html")


def tim_cua_so(chua_chuoi=TIEU_DE_GOC):
    """HWND của cửa sổ app. Bản cài đặt nằm ở `khung_cua_so.tim_hwnd` — giờ có HAI cửa
    sổ cần tìm hwnd để vá khung (app chính và Strategy Tester), nên nó thuộc về file lo
    chuyện khung chứ không phải file khởi động."""
    import khung_cua_so
    return khung_cua_so.tim_hwnd(chua_chuoi)


def main():
    trang = duong_dan_giao_dien()
    if not os.path.exists(trang):
        # Cũng phải báo bằng HỘP THOẠI, không chỉ stderr: shortcut trên Desktop chạy
        # bằng `pythonw.exe` nên KHÔNG có console — in ra stderr là không ai thấy, và
        # người dùng chỉ thấy bấm đúp mà chẳng có gì mở lên.
        bao_loi("Cat Studio — chưa build giao diện",
                "Thư mục webui\\dist chưa có.\n\n"
                "Chạy một lần:\n\n    tools\\setup.bat\n\n"
                "hoặc:\n\n    cd webui && npm install && npm run build")
        print("Chưa build giao diện. Chạy:  tools\\setup.bat", file=sys.stderr)
        return 1

    thieu = kiem_moi_truong()
    if thieu:
        bao_loi("Cat Studio — thiếu thành phần của Windows",
                "Máy này chưa đủ thứ để chạy app:\n\n · "
                + "\n\n · ".join(thieu)
                + "\n\nCài xong rồi mở lại app.")
        return 1

    # Bản cũ để `settings.json` + `templates/` ngay cạnh app. Chép sang `du_lieu/`
    # trước khi `Api()` đọc cài đặt — chỉ chép cái chưa có, không đè, không xoá bản cũ.
    da = luu_tru.di_cu()
    if da:
        print(f"[khởi động] đã chuyển sang du_lieu/: {', '.join(da)}", file=sys.stderr)

    api = Api()
    win = webview.create_window(
        TIEU_DE_GOC,
        url=trang,
        js_api=api,
        width=1360, height=860,
        min_size=(1020, 660),
        background_color="#202020",       # tránh chớp trắng trước khi CSS kịp chạy
        # Bỏ khung hệ thống để tự vẽ thanh tiêu đề đúng màu app. Windows 10 không cho
        # đổi màu caption gốc (`DWMWA_CAPTION_COLOR` trả E_INVALIDARG), nên đây là
        # đường duy nhất. Mọi tính năng của cửa sổ được vá lại trong `khung_cua_so.py`;
        # vá hỏng thì app vẫn chạy, chỉ là không có viền.
        frameless=True,
        easy_drag=False,      # cách kéo của pywebview đi qua IPC mỗi mousemove và giết
                              # Aero Snap — ta để Windows tự kéo bằng HTCAPTION
    )
    # Api cần cửa sổ để ĐẨY sự kiện ngược về JS. Tên có '_' vì pywebview đệ quy vào
    # thuộc tính công khai của js_api và sẽ treo cứng nếu chạm đối tượng Window.
    api._gan_window(win)
    win.events.closing += api.dong_app

    def sau_khi_mo():
        import time
        time.sleep(0.35)                  # đợi cửa sổ được map xong mới vá được
        h = tim_cua_so()
        if h and api._khung.va(h):
            print("[khởi động] đã vá khung cửa sổ (thanh tiêu đề tự vẽ)", file=sys.stderr)
        else:
            # Không vá được thì thôi: app vẫn dùng được, chỉ là cửa sổ không viền và
            # không kéo giãn. Thà vậy còn hơn không mở nổi.
            print("[khởi động] KHÔNG vá được khung cửa sổ — chạy với khung trần",
                  file=sys.stderr)

    # debug MẶC ĐỊNH TẮT: bật lên thì pywebview mở luôn DevTools đè lên app.
    # Cần dò lỗi thì:  set CATSTUDIO_DEBUG=1  rồi chạy lại.
    debug = os.environ.get("CATSTUDIO_DEBUG", "") not in ("", "0", "false")
    # http_server=True: trang build ra dùng ES module, nạp qua file:// thì Chromium
    # chặn vì origin là "null" -> trang trắng. Phục vụ qua http://127.0.0.1 là hết.
    try:
        webview.start(sau_khi_mo, debug=debug, http_server=True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        bao_loi("Cat Studio — không mở được cửa sổ",
                f"{type(e).__name__}: {e}\n\n"
                "Hai nguyên nhân hay gặp nhất trên máy mới:\n\n"
                " · Windows CHẶN file vì tải từ mạng. Chuột phải vào file .zip → "
                "Properties → tick 'Unblock' → OK, RỒI MỚI giải nén lại.\n\n"
                " · Thiếu .NET Framework 4.7.2 trở lên, hoặc thiếu Microsoft Edge "
                "WebView2 Runtime.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
