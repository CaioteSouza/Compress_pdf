#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Compressão AGRESSIVA de PDFs
Usa Ghostscript para compressão real de 50%+ mantendo qualidade visual
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import pikepdf


class AggressivePDFCompressor:
    """Compressor agressivo usando Ghostscript"""
    
    def __init__(self, config_path: str = "config_ghostscript.json"):
        """Inicializa o compressor"""
        self.config = self._load_config(config_path)
        self.log_file_path = self.config["log_file"]
        self.checkpoint_file = "checkpoint_ghostscript.json"  # Arquivo de checkpoint
        self.gs_path = self._find_ghostscript()
        self.start_time = None
        self.processed_files_set = set()  # Arquivos já processados
        
        # Rastreamento de sessão
        self.session_info = {
            "first_start": None,
            "current_start": None,
            "resume_count": 0,
            "last_resume": None,
            "copy_phase_start": None
        }
        
        self.stats = {
            "total_found": 0,
            "total_compressed": 0,
            "total_errors": 0,
            "total_original_bytes": 0,  # Tamanho total ANTES da compressão
            "total_final_bytes": 0,     # Tamanho total DEPOIS da compressão
            "space_saved_bytes": 0,
            "errors": [],
            "processed_files": [],
            "compression_ranges": {
                "excellent": 0,      # > 50%
                "good": 0,           # 30-50%
                "moderate": 0,       # 15-30%
                "low": 0,            # < 15%
            }
        }
    
    def _find_ghostscript(self) -> str:
        """Encontra Ghostscript no sistema"""
        # Tenta caminhos comuns do Windows
        possible_paths = [
            r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe",
            r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe",
            r"C:\Program Files\gs\gs10.03.1\bin\gswin64c.exe",
            r"C:\Program Files\gs\gs10.03.0\bin\gswin64c.exe",
        ]
        
        gs_path = None
        for path in possible_paths:
            if os.path.exists(path):
                gs_path = path
                break
        
        # Tenta encontrar no PATH
        if not gs_path:
            gs_cmd = "gswin64c.exe" if sys.platform == "win32" else "gs"
            if shutil.which(gs_cmd):
                gs_path = gs_cmd
        
        if not gs_path:
            print("\n❌ GHOSTSCRIPT NÃO ENCONTRADO!")
            print("\n📥 Para instalar o Ghostscript:")
            print("   1. Baixe em: https://ghostscript.com/releases/gsdnld.html")
            print("   2. Instale a versão 64-bit para Windows")
            print("   3. Reinicie este script\n")
            sys.exit(1)
        
        # Verifica versão
        try:
            result = subprocess.run(
                [gs_path, "--version"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            version = result.stdout.strip()
            print(f"✅ Ghostscript versão {version} encontrado")
        except:
            print(f"✅ Ghostscript encontrado: {gs_path}")
        
        return gs_path
    
    def _load_config(self, config_path: str) -> dict:
        """Carrega configurações do JSON"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ Arquivo de configuração '{config_path}' não encontrado!")
            sys.exit(1)
    
    def _load_checkpoint(self) -> bool:
        """Carrega checkpoint se existir"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                
                self.processed_files_set = set(checkpoint.get("processed_files", []))
                self.stats["total_compressed"] = checkpoint.get("total_compressed", 0)
                self.stats["total_errors"] = checkpoint.get("total_errors", 0)
                self.stats["total_original_bytes"] = checkpoint.get("total_original_bytes", 0)
                self.stats["total_final_bytes"] = checkpoint.get("total_final_bytes", 0)
                self.stats["space_saved_bytes"] = checkpoint.get("space_saved_bytes", 0)
                self.stats["compression_ranges"] = checkpoint.get("compression_ranges", {
                    "excellent": 0, "good": 0, "moderate": 0, "low": 0
                })
                
                # Atualiza info de sessão
                self.session_info["resume_count"] = checkpoint.get('resume_count', 0) + 1
                self.session_info["last_resume"] = datetime.now().isoformat()
                self.session_info["first_start"] = checkpoint.get('first_start')
                self.session_info["copy_phase_start"] = checkpoint.get('copy_phase_start')
                
                print(f"♻️  CHECKPOINT ENCONTRADO! (Retomada #{self.session_info['resume_count']})")
                print(f"   📅 Primeira execução: {self.session_info['first_start']}")
                print(f"   Já processados: {len(self.processed_files_set):,} arquivos")
                print(f"   Comprimidos: {self.stats['total_compressed']:,}")
                print(f"   Espaço economizado: {self._format_size(self.stats['space_saved_bytes'])}")
                print(f"\n➡️  Continuando de onde parou...\n")
                return True
        except Exception as e:
            print(f"⚠️  Erro ao carregar checkpoint: {e}")
        return False
    
    def _save_checkpoint(self):
        """Salva checkpoint para retomar depois"""
        try:
            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "processed_files": list(self.processed_files_set),
                "total_compressed": self.stats["total_compressed"],
                "total_errors": self.stats["total_errors"],
                "total_original_bytes": self.stats["total_original_bytes"],
                "total_final_bytes": self.stats["total_final_bytes"],
                "space_saved_bytes": self.stats["space_saved_bytes"],
                "compression_ranges": self.stats["compression_ranges"]
            }
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass  # Não interrompe se falhar
    
    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível (escolhe melhor unidade automaticamente)"""
        if size_bytes == 0:
            return "0 B"
        
        # Escolhe unidade apropriada baseada no tamanho
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                # Mostra sem casas decimais para valores pequenos
                if size_bytes < 10:
                    return f"{size_bytes:.2f} {unit}"
                else:
                    return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _compress_pdf_ghostscript(self, input_path: Path, output_path: Path, dpi: int = 150) -> Tuple[bool, str, int, int]:
        """
        Comprime PDF usando Ghostscript (COMPRESSÃO REAL)
        DPI: 72=screen (max), 150=ebook (alto), 300=printer (médio), 600=prepress (baixo)
        """
        try:
            original_size = input_path.stat().st_size
            
            # Configuração AGRESSIVA do Ghostscript
            # Essa é a ÚNICA forma de comprimir PDFs de verdade (50%+ de redução)
            cmd = [
                self.gs_path,
                '-dSAFER',  # MODO SEGURO: Previne acesso ao sistema de arquivos
                '-dNOPAUSE',
                '-dQUIET',
                '-dBATCH',
                '-sDEVICE=pdfwrite',
                '-dCompatibilityLevel=1.4',
                f'-dPDFSETTINGS=/ebook',  # Qualidade alta mas compacta
                f'-dColorImageResolution={dpi}',
                f'-dGrayImageResolution={dpi}',
                f'-dMonoImageResolution={dpi}',
                '-dColorImageDownsampleType=/Bicubic',  # Melhor qualidade
                '-dGrayImageDownsampleType=/Bicubic',
                '-dDownsampleColorImages=true',
                '-dDownsampleGrayImages=true',
                '-dDownsampleMonoImages=true',
                '-dColorImageDownsampleThreshold=1.0',  # Sempre reduzir imagens
                '-dGrayImageDownsampleThreshold=1.0',
                '-dAutoFilterColorImages=false',
                '-dAutoFilterGrayImages=false',
                '-dColorImageFilter=/DCTEncode',  # JPEG para cores
                '-dGrayImageFilter=/DCTEncode',   # JPEG para cinza
                '-dJPEGQ=85',  # Qualidade JPEG (85 = boa qualidade)
                '-dDetectDuplicateImages=true',
                '-dCompressFonts=true',
                '-dSubsetFonts=true',
                '-dEmbedAllFonts=true',
                '-dFastWebView=true',  # Otimiza para visualização
                f'-sOutputFile={str(output_path)}',
                str(input_path)
            ]
            
            # Executa Ghostscript
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            if result.returncode != 0:
                # Se falhar, copia o original
                shutil.copy2(input_path, output_path)
                return False, f"Erro GS: {result.stderr[:100]}", original_size, original_size
            
            if not output_path.exists():
                shutil.copy2(input_path, output_path)
                return False, "GS não gerou arquivo de saída", original_size, original_size
            
            compressed_size = output_path.stat().st_size
            
            # Se o arquivo ficou MAIOR, usa o original
            if compressed_size >= original_size:
                shutil.copy2(input_path, output_path)
                return False, "PDF já otimizado", original_size, original_size
            
            compression_ratio = ((original_size - compressed_size) / original_size) * 100
            
            return True, f"Comprimido ({compression_ratio:.1f}% de redução)", original_size, compressed_size
            
        except Exception as e:
            try:
                shutil.copy2(input_path, output_path)
            except:
                pass
            return False, f"Erro: {str(e)[:100]}", input_path.stat().st_size if input_path.exists() else 0, 0
    
    def _find_all_files(self, root_path: str) -> tuple[List[Path], List[Path]]:
        """Encontra todos os arquivos (PDFs e não-PDFs) rapidamente"""
        print("   🔍 Escaneando arquivos...", end="", flush=True)
        
        pdfs = []
        other_files = []
        root = Path(root_path)
        compress_folder_name = self.config["compress_folder_name"]
        pdf_extensions = [".pdf", ".PDF"]
        
        count_pdfs = 0
        count_others = 0
        
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != compress_folder_name]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                
                if any(filename.endswith(ext) for ext in pdf_extensions):
                    pdfs.append(file_path)
                    count_pdfs += 1
                    if count_pdfs % 1000 == 0:
                        print(f"\r   🔍 Escaneando... {count_pdfs:,} PDFs, {count_others:,} outros", end="", flush=True)
                else:
                    other_files.append(file_path)
                    count_others += 1
                    if count_others % 1000 == 0:
                        print(f"\r   🔍 Escaneando... {count_pdfs:,} PDFs, {count_others:,} outros", end="", flush=True)
        
        print(f"\r   ✅ Encontrados {count_pdfs:,} PDFs e {count_others:,} outros arquivos!          ")
        return pdfs, other_files
    
    def _create_compress_folder(self, root_path: str) -> Path:
        """Cria pasta de saída"""
        compress_output = self.config.get("compress_output_path", "same_as_root")
        
        if compress_output == "same_as_root":
            compress_folder = Path(root_path) / self.config["compress_folder_name"]
        else:
            compress_folder = Path(compress_output) / self.config["compress_folder_name"]
        
        compress_folder.mkdir(parents=True, exist_ok=True)
        return compress_folder
    
    def _copy_other_file(self, file_path: Path, root_path: Path, compress_folder: Path) -> bool:
        """Copia arquivo não-PDF mantendo estrutura de pastas"""
        try:
            # Calcula caminho relativo e de destino
            relative_path = file_path.relative_to(root_path)
            output_path = compress_folder / relative_path
            
            # Cria diretórios necessários
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copia arquivo preservando metadados
            shutil.copy2(file_path, output_path)
            return True
        except Exception as e:
            print(f"   ⚠️  Erro ao copiar {file_path.name}: {e}")
            return False
    
    def process_all_pdfs(self):
        """Processa todos os PDFs com compressão agressiva"""
        self.start_time = datetime.now()
        self.session_info['current_start'] = self.start_time.isoformat()
        
        root_path = self.config["root_path"]
        print(f"\n📂 Pasta: {root_path}")
        
        # Carrega checkpoint se existir
        has_checkpoint = self._load_checkpoint()
        
        # Se não está retomando, esta é a primeira execução
        if not has_checkpoint:
            self.session_info['first_start'] = self.start_time.isoformat()
        
        # Encontra todos os arquivos (PDFs e outros)
        pdfs, other_files = self._find_all_files(root_path)
        self.stats["total_found"] = len(pdfs)
        
        print(f"\n📊 Resumo:")
        print(f"   📄 {len(pdfs):,} PDFs para comprimir")
        print(f"   📁 {len(other_files):,} outros arquivos para copiar")
        print(f"   📁 {len(other_files):,} outros arquivos para copiar")
        
        if len(pdfs) == 0:
            print("❌ Nenhum PDF encontrado!")
            return
        
        # Filtra PDFs já processados
        if has_checkpoint:
            pdfs_to_process = [pdf for pdf in pdfs if str(pdf) not in self.processed_files_set]
            skipped = len(pdfs) - len(pdfs_to_process)
            print(f"\n⏩ Pulando {skipped:,} arquivos já processados")
            print(f"🔄 Restam {len(pdfs_to_process):,} arquivos para processar\n")
            pdfs = pdfs_to_process
        
        # Cria pasta de saída sempre (mesmo se não tiver PDFs para processar)
        compress_folder = self._create_compress_folder(root_path)
        
        if len(pdfs) == 0:
            print("✅ Todos os PDFs já foram processados!")
            # NÃO RETORNA AQUI - continua para copiar outros arquivos
        else:
            print(f"📁 Saída: {compress_folder}\n")
            
            # Obtém configuração de DPI
            dpi = self.config.get("compression_settings", {}).get("dpi", 150)
            print(f"⚙️  DPI: {dpi} (72=max compressão, 150=boa, 300=alta qualidade)\n")
            
            # Processa cada PDF
            print(f"{'='*60}")
            print(f"🚀 PROCESSANDO {len(pdfs):,} PDFs COM GHOSTSCRIPT")
            print(f"{'='*60}\n")
            
            for idx, pdf_path in enumerate(pdfs, 1):
                try:
                    # Calcula caminho de saída
                    relative_path = pdf_path.relative_to(Path(root_path))
                    output_path = compress_folder / relative_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    print(f"[{idx}/{len(pdfs)}] {pdf_path.name}")
                    
                    # Comprime com Ghostscript
                    success, message, original_size, compressed_size = self._compress_pdf_ghostscript(
                        pdf_path, output_path, dpi
                    )
                    
                    # Adiciona aos processados
                    self.processed_files_set.add(str(pdf_path))
                    
                    # Estatísticas
                    if success:
                        compression_ratio = ((original_size - compressed_size) / original_size) * 100
                        
                        if compression_ratio >= 50:
                            self.stats["compression_ranges"]["excellent"] += 1
                        elif compression_ratio >= 30:
                            self.stats["compression_ranges"]["good"] += 1
                        elif compression_ratio >= 15:
                            self.stats["compression_ranges"]["moderate"] += 1
                        else:
                            self.stats["compression_ranges"]["low"] += 1
                        
                        self.stats["total_compressed"] += 1
                        self.stats["total_original_bytes"] += original_size
                        self.stats["total_final_bytes"] += compressed_size
                        self.stats["space_saved_bytes"] += (original_size - compressed_size)
                        
                        print(f"   ✅ {message}")
                        print(f"   📦 {self._format_size(original_size)} → {self._format_size(compressed_size)}\n")
                    else:
                        self.stats["total_errors"] += 1
                        print(f"   ⚠️  {message}\n")
                    
                    # Salva checkpoint a cada 10 arquivos
                    if idx % 10 == 0:
                        self._save_checkpoint()
                        self._save_progress()
                
                except KeyboardInterrupt:
                    print("\n\n⏸️  Ctrl+C detectado! Salvando progresso e encerrando...")
                    self._save_checkpoint()
                    self._save_progress()
                    print("✅ Progresso salvo! Você pode retomar depois executando novamente.\n")
                    sys.exit(0)
                        
                except Exception as e:
                    print(f"   ❌ Erro: {str(e)}\n")
                    self.stats["total_errors"] += 1
                    self.processed_files_set.add(str(pdf_path))
        
        # Copia arquivos não-PDF
        if len(other_files) > 0:
            # Registra início da fase de cópia (apenas na primeira vez)
            if not self.session_info['copy_phase_start']:
                self.session_info['copy_phase_start'] = datetime.now().isoformat()
            
            print(f"\n{'='*60}")
            print(f"📁 COPIANDO {len(other_files):,} OUTROS ARQUIVOS")
            print(f"📅 Fase de cópia iniciada: {self.session_info['copy_phase_start']}")
            print(f"{'='*60}\n")
            
            copied_count = 0
            for idx, file_path in enumerate(other_files, 1):
                try:
                    if self._copy_other_file(file_path, Path(root_path), compress_folder):
                        copied_count += 1
                    
                    if idx % 100 == 0:
                        print(f"\r   📋 Copiados: {copied_count:,}/{idx:,}", end="", flush=True)
                
                except KeyboardInterrupt:
                    print("\n\n⏸️  Ctrl+C detectado durante cópia!")
                    break
                except Exception as e:
                    pass
            
            print(f"\r   ✅ Copiados: {copied_count:,}/{len(other_files):,} arquivos          \n")
        
        # Resumo final e limpa checkpoint
        self._print_summary(compress_folder)
        self._cleanup_checkpoint()
    
    def _save_progress(self):
        """Salva log de progresso durante execução (resumo geral + últimos 1000 arquivos)"""
        try:
            # Carrega log existente para manter histórico
            processed_history = []
            existing_files_set = set()  # OTIMIZAÇÃO: set para verificação O(1)
            
            if os.path.exists(self.log_file_path):
                try:
                    with open(self.log_file_path, 'r', encoding='utf-8') as f:
                        existing_log = json.load(f)
                        processed_history = existing_log.get("processed_files_history", [])
                        # Cria set de arquivos existentes (MUITO mais rápido)
                        existing_files_set = {item.get("file") for item in processed_history}
                except:
                    pass
            
            # Adiciona apenas novos arquivos (verificação O(1) com set)
            new_files = []
            for file_path in self.processed_files_set:
                if file_path not in existing_files_set:
                    new_files.append({
                        "file": file_path,
                        "timestamp": datetime.now().isoformat(),
                        "status": "processed"
                    })
            
            # Adiciona novos ao histórico
            processed_history.extend(new_files)
            
            # Mantém apenas os últimos 1000 (FIFO - First In First Out)
            if len(processed_history) > 1000:
                processed_history = processed_history[-1000:]
            
            # Calcula porcentagem de conclusão
            total_processed = len(self.processed_files_set)
            completion_pct = (total_processed / self.stats['total_found'] * 100) if self.stats['total_found'] > 0 else 0
            
            # Salva log completo com resumo no topo
            log_data = {
                "log_info": {
                    "description": "Log rotativo - mantém resumo geral + últimos 1000 arquivos processados",
                    "last_update": datetime.now().isoformat(),
                    "total_files_in_history": len(processed_history),
                    "history_limit": 1000
                },
                "session_info": {
                    "first_start": self.session_info['first_start'],
                    "current_start": self.session_info['current_start'],
                    "resume_count": self.session_info['resume_count'],
                    "last_resume": self.session_info['last_resume'],
                    "copy_phase_start": self.session_info['copy_phase_start']
                },
                "summary": {
                    "execution_start": self.start_time.isoformat() if self.start_time else datetime.now().isoformat(),
                    "last_update": datetime.now().isoformat(),
                    "status": "in_progress",
                    "completion_percentage": round(completion_pct, 2),
                    "statistics": {
                        "total_found": self.stats["total_found"],
                        "total_processed": len(self.processed_files_set),
                        "total_compressed": self.stats["total_compressed"],
                        "total_errors": self.stats["total_errors"],
                        "total_original_size": self._format_size(self.stats["total_original_bytes"]),
                        "total_final_size": self._format_size(self.stats["total_final_bytes"]),
                        "space_saved": self._format_size(self.stats["space_saved_bytes"]),
                        "compression_ranges": self.stats["compression_ranges"]
                    }
                },
                "processed_files_history": processed_history
            }
            
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            pass  # Não interrompe se falhar
    
    def _cleanup_checkpoint(self):
        """Remove checkpoint após conclusão bem-sucedida"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                print(f"\n✅ Checkpoint removido (processo concluído)")
        except:
            pass
    
    def _print_summary(self, compress_folder: Path):
        """Imprime resumo final"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Calcula porcentagem de conclusão
        total_processed = len(self.processed_files_set)
        completion_pct = (total_processed / self.stats['total_found'] * 100) if self.stats['total_found'] > 0 else 0
        
        print(f"\n{'='*60}")
        print("📈 RESUMO FINAL")
        print(f"{'='*60}")
        print(f"📁 PDFs encontrados: {self.stats['total_found']:,}")
        print(f"✅ PDFs comprimidos: {self.stats['total_compressed']:,}")
        print(f"⚠️  Erros: {self.stats['total_errors']:,}")
        print(f"📊 Progresso: {completion_pct:.1f}% ({total_processed:,}/{self.stats['total_found']:,})")
        
        if self.stats['total_found'] > 0:
            taxa = (self.stats['total_compressed'] / self.stats['total_found']) * 100
            print(f"🎯 Taxa de sucesso: {taxa:.1f}%")
        
        print(f"\n📊 FAIXAS DE COMPRESSÃO:")
        ranges = self.stats["compression_ranges"]
        if ranges["excellent"] > 0:
            print(f"   🌟 Excelente (>50%): {ranges['excellent']:,}")
        if ranges["good"] > 0:
            print(f"   ✅ Boa (30-50%): {ranges['good']:,}")
        if ranges["moderate"] > 0:
            print(f"   📊 Moderada (15-30%): {ranges['moderate']:,}")
        if ranges["low"] > 0:
            print(f"   📉 Baixa (<15%): {ranges['low']:,}")
        
        print(f"\n💾 Espaço economizado: {self._format_size(self.stats['space_saved_bytes'])}")
        print(f"⏱️  Tempo total: {duration:.1f}s ({duration/60:.1f} minutos)")
        print(f"📂 Arquivos em: {compress_folder}")
        print(f"{'='*60}\n")
        
        self._save_progress()


def main():
    """Função principal"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     COMPRESSÃO AGRESSIVA DE PDFs - GHOSTSCRIPT            ║
    ║     Compressão REAL de 50%+ mantendo qualidade visual     ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        compressor = AggressivePDFCompressor()
        compressor.process_all_pdfs()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
