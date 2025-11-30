# 🚀 Instruções para Publicar no GitHub

## Passo 1: Preparar o Repositório Local

```bash
# Entre na pasta do projeto
cd c:\laragon\www\Compress_pdf

# Inicialize o Git (se ainda não foi feito)
git init

# Adicione todos os arquivos
git add .

# Faça o primeiro commit
git commit -m "Initial commit: Sistema de compressão de PDFs com dois métodos"
```

## Passo 2: Criar Repositório no GitHub

1. Acesse: https://github.com/new
2. Nome do repositório: `pdf-compressor` (ou o nome que preferir)
3. Descrição: `Sistema de compressão de PDFs com dois métodos: pikepdf (leve) e Ghostscript (agressivo)`
4. **Deixe PÚBLICO** para ser open source
5. **NÃO marque** "Add README" (já temos um)
6. **NÃO marque** "Add .gitignore" (já temos um)
7. **NÃO marque** "Choose a license" (já temos MIT)
8. Clique em **"Create repository"**

## Passo 3: Conectar e Enviar

Após criar o repositório, o GitHub mostrará comandos. Use estes:

```bash
# Adicione o remote (substitua SEU-USUARIO pelo seu username)
git remote add origin https://github.com/SEU-USUARIO/pdf-compressor.git

# Renomeie a branch para main (padrão moderno)
git branch -M main

# Envie para o GitHub
git push -u origin main
```

## Passo 4: Verificações Finais no GitHub

Após o push, verifique se aparecem:

- ✅ README.md renderizado na página principal
- ✅ Estrutura de pastas correta
- ✅ LICENSE aparecendo
- ✅ .gitignore funcionando (config.json não deve aparecer)
- ✅ Badges funcionando no README

## Passo 5: Configurações Recomendadas

No GitHub, vá em **Settings** do repositório:

### General
- ✅ Features: Marque "Issues" para receber feedback
- ✅ Pull Requests: Ativado para contribuições

### Topics (Tags)
Adicione tags para facilitar busca:
- `pdf`
- `compression`
- `python`
- `ghostscript`
- `pikepdf`
- `pdf-compression`
- `batch-processing`

### About (Descrição)
Edite e adicione:
- **Description:** Sistema de compressão de PDFs com dois métodos
- **Website:** (deixe em branco ou adicione se tiver)
- **Topics:** Use as sugeridas acima

## Passo 6: Adicione um README Badge

Opcional - adicione mais badges ao README:

```markdown
[![GitHub stars](https://img.shields.io/github/stars/SEU-USUARIO/pdf-compressor?style=social)](https://github.com/SEU-USUARIO/pdf-compressor)
[![GitHub forks](https://img.shields.io/github/forks/SEU-USUARIO/pdf-compressor?style=social)](https://github.com/SEU-USUARIO/pdf-compressor)
```

## Comandos Úteis

### Atualizar o repositório após mudanças:
```bash
git add .
git commit -m "Descrição da mudança"
git push
```

### Ver status:
```bash
git status
```

### Ver histórico:
```bash
git log --oneline
```

## 📋 Checklist Final

Antes de publicar, certifique-se:

- [ ] README.md está completo e claro
- [ ] LICENSE existe (MIT)
- [ ] .gitignore está correto
- [ ] config.json NÃO está no repositório
- [ ] config.example.json existe em ambos os projetos
- [ ] requirements.txt de ambos os projetos estão corretos
- [ ] Não há dados sensíveis ou caminhos pessoais
- [ ] Todos os READMEs dos projetos estão atualizados

## 🎉 Pronto!

Seu projeto agora está público e outros desenvolvedores podem:
- ⭐ Dar estrela
- 🍴 Fazer fork
- 🐛 Reportar bugs
- 💡 Sugerir melhorias
- 🤝 Contribuir com código

**Link do repositório será:**
`https://github.com/SEU-USUARIO/pdf-compressor`

---

## Dicas Extras

### Adicionar Screenshot
Crie uma pasta `docs/images/` e adicione prints do funcionamento

### Criar Releases
Quando fizer versões:
```bash
git tag -a v1.0.0 -m "Versão 1.0.0 - Release inicial"
git push origin v1.0.0
```

### Habilitar GitHub Pages (opcional)
Para criar uma página web do projeto em Settings > Pages

---

**Boa sorte com o projeto open source! 🚀**
