# 📦 Projeto Pikepdf - Compressão Leve

## 🎯 Características

**Método:** Pikepdf + Pillow + zlib  
**Compressão:** 5-15% de redução  
**Taxa de sucesso:** 20-40% dos PDFs  
**Dependências:** Só Python (sem Ghostscript)

## 🚀 Como Usar

### 1. Instalar dependências:
```powershell
pip install -r requirements.txt
```

### 2. Configurar:
Copie o arquivo de exemplo e edite com seus caminhos:
```powershell
copy config.example.json config.json
# Edite config.json com seus caminhos
```

**Exemplo de config.json:**
```json
{
  "root_path": "C:\\caminho\\dos\\pdfs",
  "compress_output_path": "C:\\caminho\\saida"
}
```

### 3. Executar:
```powershell
# Clique duplo em run.bat
# OU
python compress_pdfs.py
```

## 📊 O que faz

- ✅ Compressão zlib level 9 para imagens PNG
- ✅ JPEG com qualidade 95 (quase sem perdas)
- ✅ Remove objetos duplicados
- ✅ Preserva transparência com SMask
- ✅ Otimiza streams internos

## 📁 Arquivos

- `compress_pdfs.py` - Script principal
- `config.json` - Configurações
- `run.bat` - Executor rápido
- `requirements.txt` - Dependências Python
- `compression_log_pikepdf.json` - Log gerado (rotativo)
- `checkpoint_pikepdf.json` - Checkpoint automático (temporário)

## ⚙️ Configurações

### Qualidade de Imagem
```json
"image_quality": 95  // 85-100 (95 recomendado)
```

### Pasta de Saída
```json
"compress_folder_name": "shared_compress_pikepdf"
```

## 📊 Resultado Esperado

**40.000 PDFs:**
- Comprimidos: ~12.000 (30%)
- Espaço economizado: 2-5 GB
- Tempo: 4-6 horas

## ✅ Vantagens

- ✅ Não precisa instalar nada além do Python
- ✅ 100% Python puro
- ✅ Seguro e simples
- ✅ Bom para PDFs já otimizados

## ⚠️ Limitações

- ⚠️ Compressão limitada (5-15%)
- ⚠️ Não reprocessa o PDF completo
- ⚠️ Taxa de sucesso menor

## 🔧 Solução de Problemas

**"ModuleNotFoundError: No module named 'pikepdf'"**
```powershell
pip install pikepdf Pillow tqdm
```

**PDFs não sendo comprimidos:**
- Normal! Muitos PDFs já vêm otimizados
- Use o projeto Ghostscript para compressão real

## 📝 Sistema de Log e Checkpoint

### Log Rotativo
Verifique `compression_log_pikepdf.json` para:
- **Resumo geral no topo:**
  - Total de PDFs encontrados e processados
  - Estatísticas de compressão por faixa
  - Breakdown detalhado de erros
  - Espaço economizado
- **Histórico dos últimos 1000 arquivos processados**
- **Atualizado a cada 10 arquivos** em tempo real

### Checkpoint Automático (Crash Recovery)
**O que faz:**
- ✅ Salva progresso a cada 10 arquivos em `checkpoint_pikepdf.json`
- ✅ Se o processo crashar/PC desligar, retoma automaticamente
- ✅ Mostra quantos arquivos já foram processados
- ✅ Pula arquivos já comprimidos
- ✅ Remove checkpoint ao finalizar com sucesso

**Como usar:**
```powershell
python compress_pdfs.py
# Se interromper (Ctrl+C ou crash), basta executar novamente
# O sistema detecta checkpoint e continua de onde parou!
```

**Vantagens:**
- Processa grandes volumes sem medo de perder progresso
- Pior caso: perde apenas 10 arquivos (último salvamento)
- Checkpoint é automático e transparente

---

**Para compressão REAL (30-60%), use o projeto Ghostscript!**
