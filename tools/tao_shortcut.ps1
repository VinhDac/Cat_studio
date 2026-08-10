# Tạo shortcut "Cat Studio" ra Desktop và cạnh mã nguồn.
#
# ⚠ FILE NÀY PHẢI LƯU KÈM BOM (UTF-8 with BOM). Windows PowerShell 5.1 đọc .ps1 theo
# bảng mã ANSI của hệ thống khi không thấy BOM, nên mọi chữ tiếng Việt vỡ thành ký tự
# lạ — dấu nháy trong chuỗi bị hiểu sai và script gãy ngay dòng đầu tiên có dấu.
#
# Dùng `pythonw.exe` chứ không phải `python.exe`: python.exe kèm theo một cửa sổ
# console đen nằm suốt bên cạnh app. Đổi lại, pythonw không có stderr để nhìn — nên
# `app_web.py` báo mọi lỗi khởi động bằng HỘP THOẠI Windows.

$goc  = Split-Path -Parent $PSScriptRoot
$exe  = Join-Path $goc ".venv\Scripts\pythonw.exe"
$icon = Join-Path $goc "assets\logo.ico"

$thieu = @($exe, $icon, (Join-Path $goc "app_web.py")) | Where-Object { -not (Test-Path $_) }
if ($thieu) {
    Write-Host "Thiếu:" -ForegroundColor Red
    $thieu | ForEach-Object { Write-Host "  $_" }
    Write-Host "`nChạy tools\setup.bat trước đã." -ForegroundColor Yellow
    exit 1
}

$sh = New-Object -ComObject WScript.Shell
$dich = @(
    (Join-Path ([Environment]::GetFolderPath('Desktop')) "Cat Studio.lnk"),
    (Join-Path $goc "Cat Studio.lnk")
)

foreach ($d in $dich) {
    $lnk = $sh.CreateShortcut($d)
    $lnk.TargetPath       = $exe
    $lnk.Arguments        = "app_web.py"
    $lnk.WorkingDirectory = $goc          # bắt buộc: app_web.py tìm webui\dist theo đây
    $lnk.IconLocation     = "$icon,0"
    # KHÔNG dấu tiếng Việt ở đây: WScript.Shell ghi trường mô tả của .lnk bằng ANSI,
    # nên mọi ký tự ngoài bảng mã hệ thống biến thành "?" — đã đo. Tên file shortcut
    # thì lưu Unicode bình thường, chỉ riêng trường này.
    $lnk.Description      = "Cat Studio - trading strategy diagram editor"
    $lnk.WindowStyle      = 1
    $lnk.Save()
    Write-Host "✔ $d" -ForegroundColor Green
}
