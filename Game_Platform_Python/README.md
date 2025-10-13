Yêu cầu
- Python 3.8 hoặc mới hơn

1) Kiểm tra Python:

```powershell
python --version
```

2) Tạo và kích hoạt virtualenv (khuyến nghị):

```powershell
python -m venv .venv
# Nếu PowerShell chặn script, cho phép tạm thời cho phiên hiện tại:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Chạy game

B1: .\.venv\Scripts\Activate.ps1 (chạy thêm đoạn này nếu lỗi Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
B2: cd D:\LapTrinh_Python\Python_game\Game_Platform_Python
B3: python -m game.app