@echo off
chcp 65001 > nul
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          COMPRESSÃO COM PIKEPDF - SEM GHOSTSCRIPT         ║
echo ║          Otimização de streams e imagens (5-15%%)          ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

echo 📊 Método: pikepdf + Pillow + zlib
echo 📁 Saída: shared_compress_pikepdf
echo 📝 Log: compression_log_pikepdf.json
echo.
echo ⚙️  Configurações:
echo    - Qualidade de imagem: 95%%
echo    - Compressão zlib: Level 9
echo    - Remove duplicatas: Sim
echo.
echo 🚀 Iniciando compressão com pikepdf...
echo.

python compress_pdfs.py

echo.
echo ✅ Processo finalizado!
echo.
pause
