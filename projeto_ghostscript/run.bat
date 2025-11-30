@echo off
chcp 65001 > nul
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║     COMPRESSÃO AGRESSIVA COM GHOSTSCRIPT 10.06.0          ║
echo ║     Compressão REAL de 50%%+ mantendo qualidade visual     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

echo 📊 Método: Ghostscript (profissional)
echo 📁 Saída: shared_compress_ghostscript
echo 📝 Log: compression_log_ghostscript.json
echo.
echo ⚙️  Configurações:
echo    - DPI: 150 (boa compressão)
echo    - Modo SAFER: Ativado
echo    - Ghostscript: 10.06.0
echo.

REM Verifica se o Ghostscript está instalado
echo 🔍 Verificando Ghostscript...
where gswin64c.exe > nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe" (
        echo ✅ Ghostscript 10.06.0 encontrado!
    ) else (
        echo.
        echo ❌ GHOSTSCRIPT NÃO ENCONTRADO!
        echo.
        echo 📥 Baixe e instale em:
        echo    https://ghostscript.com/releases/gsdnld.html
        echo.
        pause
        exit /b 1
    )
) else (
    echo ✅ Ghostscript encontrado!
)

echo.
echo 🚀 Iniciando compressão agressiva...
echo.

python compress_aggressive.py

echo.
echo ✅ Processo finalizado!
echo.
pause
