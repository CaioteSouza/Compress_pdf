# 📄 PDF Compressor - Sistema de Compressão de PDFs

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ghostscript](https://img.shields.io/badge/Ghostscript-10.06.0-orange.svg)](https://ghostscript.com/)

Sistema completo de compressão de PDFs com **dois métodos diferentes**: compressão leve (pikepdf) e compressão agressiva (Ghostscript). Escolha o método ideal para suas necessidades!

## 🎯 Características Principais

- ✅ **Dois métodos independentes** de compressão
- ✅ **Processamento em lote** de milhares de arquivos
- ✅ **Sistema de checkpoint** automático (retoma se crashar)
- ✅ **Logs rotativos** com estatísticas detalhadas
- ✅ **Detecção automática** de PDFs já comprimidos
- ✅ **Preservação de estrutura** de pastas
- ✅ **Tratamento robusto** de erros

---

## 📊 Comparação dos Métodos

| Característica | 🔷 Pikepdf | 🔶 Ghostscript |
|----------------|------------|----------------|
| **Compressão média** | 5-15% | 30-60% |
| **Taxa de sucesso** | 20-40% dos PDFs | 80-95% dos PDFs |
| **Velocidade** | Rápido | Médio |
| **Dependências** | Só Python | Python + Ghostscript |
| **Qualidade** | 100% original | Imperceptível |
| **Melhor para** | PDFs já otimizados | Compressão real |

---

## 🚀 Instalação Rápida

### Pré-requisitos

- Python 3.8 ou superior
- Ghostscript 10.06.0 (apenas para compressão agressiva)

### Passo 1: Clone o repositório

```bash
git clone https://github.com/seu-usuario/pdf-compressor.git
cd pdf-compressor
```

### Passo 2: Escolha seu método

#### 🔷 Método 1: Pikepdf (Compressão Leve)

```bash
cd projeto_pikepdf
pip install -r requirements.txt

# Copie e configure
copy config.example.json config.json
# Edite config.json com seus caminhos

# Execute
python compress_pdfs.py
# OU clique duplo em run.bat (Windows)
```

#### 🔶 Método 2: Ghostscript (Compressão Agressiva)

**Primeiro, instale o Ghostscript:**
- Baixe: https://ghostscript.com/releases/gsdnld.html
- Versão: GPL Ghostscript 10.06.0 for Windows (64 bit)
- Instale em: `C:\Program Files\gs\gs10.06.0\`

```bash
cd projeto_ghostscript
pip install -r requirements.txt

# Copie e configure
copy config.example.json config_ghostscript.json
# Edite config_ghostscript.json com seus caminhos

# Execute
python compress_aggressive.py
# OU clique duplo em run.bat (Windows)
```

---

## ⚙️ Configuração

### Exemplo de config.json (Pikepdf)

```json
{
  "root_path": "C:\\seus\\pdfs",
  "compress_output_path": "C:\\saida",
  "compress_folder_name": "shared_compress_pikepdf",
  "compression_settings": {
    "image_quality": 95,
    "remove_duplicates": true
  }
}
```

### Exemplo de config_ghostscript.json (Ghostscript)

```json
{
  "root_path": "C:\\seus\\pdfs",
  "compress_output_path": "C:\\saida",
  "compress_folder_name": "shared_compress_ghostscript",
  "compression_settings": {
    "dpi": 150
  }
}
```

**Ajuste de DPI (Ghostscript):**
- `72` = Máxima compressão (50-70% de redução)
- `150` = Boa compressão (30-50% de redução) ⭐ **Recomendado**
- `300` = Alta qualidade (15-30% de redução)

---

## 📁 Estrutura do Projeto

```
pdf-compressor/
│
├── projeto_pikepdf/              # Método 1: Compressão Leve
│   ├── compress_pdfs.py          # Script principal
│   ├── config.example.json       # Configuração exemplo
│   ├── requirements.txt          # Dependências Python
│   ├── run.bat                   # Executor Windows
│   └── README.md                 # Documentação detalhada
│
├── projeto_ghostscript/          # Método 2: Compressão Agressiva
│   ├── compress_aggressive.py    # Script principal
│   ├── config.example.json       # Configuração exemplo
│   ├── requirements.txt          # Dependências Python
│   ├── run.bat                   # Executor Windows
│   └── README.md                 # Documentação detalhada
│
├── .gitignore                    # Arquivos ignorados
└── README.md                     # Este arquivo
```

---

## 🎯 Casos de Uso

### Use **Pikepdf** quando:

- ✅ Não quer instalar ferramentas externas
- ✅ PDFs já estão razoavelmente otimizados
- ✅ Precisa de processamento rápido
- ✅ Quer 100% Python puro
- ✅ Manutenção e otimização leve

### Use **Ghostscript** quando:

- ✅ Precisa de compressão real (50%+ de redução)
- ✅ Tem PDFs grandes (vários MB)
- ✅ Quer economizar muito espaço em disco
- ✅ Qualidade visual é mais importante que resolução técnica
- ✅ Arquivamento de longo prazo

---

## 📊 Resultados Esperados

### Exemplo: 40.000 PDFs

| Métrica | Pikepdf | Ghostscript |
|---------|---------|-------------|
| PDFs comprimidos | ~12.000 (30%) | ~35.000 (87%) |
| Espaço economizado | 2-5 GB | 20-35 GB |
| Tempo estimado | 4-6 horas | 8-12 horas |

---

## 🔧 Recursos Avançados

### Sistema de Checkpoint

Ambos os métodos salvam progresso automaticamente a cada 10 arquivos:

- ✅ Se o PC desligar, retoma de onde parou
- ✅ Pula arquivos já processados
- ✅ Mostra resumo do progresso
- ✅ Checkpoint removido após conclusão

### Logs Rotativos

Logs mantêm os últimos 1000 arquivos processados:

- 📊 Estatísticas gerais sempre no topo
- 📝 Histórico dos últimos processamentos
- 🔄 Atualização em tempo real (a cada 10 arquivos)
- 📈 Breakdown detalhado de erros

Arquivos de log:
- `compression_log_pikepdf.json`
- `compression_log_ghostscript.json`

---

## 🛠️ Solução de Problemas

### "ModuleNotFoundError: No module named 'pikepdf'"

```bash
pip install pikepdf Pillow tqdm
```

### "Ghostscript não encontrado"

Verifique a instalação:

```bash
"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe" --version
```

Deve retornar: `10.06.0`

### PDFs não sendo comprimidos

- **Normal!** Muitos PDFs já vêm otimizados
- Use o método Ghostscript para compressão real
- Ajuste o DPI no config (tente 72 para máxima compressão)

---

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um Fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abrir um Pull Request

---

## 📧 Suporte

Se encontrar problemas ou tiver sugestões:

- Abra uma [Issue](https://github.com/seu-usuario/pdf-compressor/issues)
- Consulte a documentação detalhada em cada projeto

---

## 👥 Autores

- **Caio** - Desenvolvimento e implementação
- **GitHub Copilot** - Assistência técnica e documentação

---

## ⭐ Agradecimentos

- [Ghostscript](https://ghostscript.com/) - Motor de processamento PostScript/PDF
- [pikepdf](https://github.com/pikepdf/pikepdf) - Biblioteca Python para manipulação de PDFs
- [Pillow](https://python-pillow.org/) - Processamento de imagens

---

<div align="center">

**Feito com ❤️ para facilitar a compressão de PDFs**

**Desenvolvido por Caio com assistência do GitHub Copilot**

</div>
