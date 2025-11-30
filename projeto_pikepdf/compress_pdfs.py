#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Compressão de PDFs
Comprime todos os PDFs de uma pasta (recursivamente) mantendo qualidade de leitura
"""

import os
import sys
import json
import shutil
import zlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import pikepdf
from PIL import Image
import io


class PDFCompressor:
    """Classe principal para compressão de PDFs"""
    
    def __init__(self, config_path: str = "config.json"):
        """Inicializa o compressor com configurações"""
        self.config = self._load_config(config_path)
        self.log_file_path = self.config["log_file"]
        self.checkpoint_file = "checkpoint_pikepdf.json"
        self.processed_files_set = set()  # Arquivos já processados (para resume)
        self.stats = {
            "total_found": 0,
            "total_compressed": 0,
            "total_errors": 0,
            "total_skipped": 0,
            "total_copied": 0,  # PDFs copiados sem compressão
            "total_original_bytes": 0,  # Tamanho total ANTES da compressão
            "total_final_bytes": 0,     # Tamanho total DEPOIS da compressão
            "space_saved_bytes": 0,
            "errors": [],
            "processed_files": [],
            # Estatísticas detalhadas por tipo de erro
            "error_breakdown": {
                "already_optimized": 0,  # Já está comprimido ao máximo
                "minimal_gain": 0,       # Compressão < 5%
                "password_protected": 0,
                "corrupted": 0,
                "permission_denied": 0,
                "other_errors": 0
            },
            # Estatísticas de compressão
            "compression_ranges": {
                "excellent": 0,      # > 50%
                "good": 0,           # 30-50%
                "moderate": 0,       # 15-30%
                "low": 0,            # 5-15%
                "minimal": 0         # < 5%
            }
        }
        self.current_status = ""
        self.start_time = None
        
        # Inicializa o arquivo de log
        self._initialize_log()
        
    def _load_config(self, config_path: str) -> dict:
        """Carrega arquivo de configuração"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validações de segurança
            self._validate_config(config)
            
            return config
        except FileNotFoundError:
            print(f"❌ ERRO: Arquivo de configuração '{config_path}' não encontrado!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ ERRO: Arquivo de configuração inválido: {e}")
            sys.exit(1)
    
    def _validate_config(self, config: dict):
        """Valida configurações de segurança"""
        # Valida extensões permitidas
        allowed_ext = config.get("processing", {}).get("allowed_extensions", [".pdf", ".PDF"])
        
        if not allowed_ext:
            print("⚠️  AVISO: Nenhuma extensão permitida configurada. Usando padrão: .pdf, .PDF")
            config["processing"]["allowed_extensions"] = [".pdf", ".PDF"]
        
        # Valida que apenas PDFs estão permitidos
        non_pdf_extensions = [ext for ext in allowed_ext if ext.lower() not in [".pdf"]]
        if non_pdf_extensions:
            print(f"❌ ERRO DE SEGURANÇA: Apenas arquivos PDF são permitidos!")
            print(f"   Extensões inválidas encontradas: {non_pdf_extensions}")
            print(f"   Remova-as do config.json e tente novamente.")
            sys.exit(1)
        
        print("✅ Validação: Apenas arquivos PDF serão processados")
    
    def _update_status(self, status: str):
        """Atualiza e exibe status atual"""
        if status != self.current_status:
            self.current_status = status
            print(f"\n{'='*60}")
            print(f"📊 STATUS: {status}")
            print(f"{'='*60}")
    
    def _format_size(self, bytes_size: int) -> str:
        """Formata tamanho em bytes para formato legível (escolhe melhor unidade automaticamente)"""
        if bytes_size == 0:
            return "0 B"
        
        # Escolhe unidade apropriada baseada no tamanho
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                # Mostra sem casas decimais para valores pequenos
                if bytes_size < 10:
                    return f"{bytes_size:.2f} {unit}"
                else:
                    return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"
    
    def _initialize_log(self):
        """Inicializa o arquivo de log com estrutura básica"""
        log_data = {
            "execution_start": datetime.now().isoformat(),
            "execution_end": None,
            "status": "in_progress",
            "config": self.config,
            "statistics": {
                "total_found": 0,
                "total_compressed": 0,
                "total_errors": 0,
                "space_saved_bytes": 0,
                "space_saved_formatted": "0 B"
            },
            "processed_files": [],
            "errors": []
        }
        
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Aviso: Não foi possível criar o log inicial: {e}")
    
    def _load_checkpoint(self) -> bool:
        """Carrega checkpoint de execução anterior (se existir)"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                
                # Restaura lista de arquivos processados
                self.processed_files_set = set(checkpoint.get('processed_files', []))
                
                # Restaura estatísticas parciais
                saved_stats = checkpoint.get('stats', {})
                if saved_stats:
                    self.stats.update(saved_stats)
                
                # Atualiza info de sessão
                self.session_info["resume_count"] = checkpoint.get('resume_count', 0) + 1
                self.session_info["last_resume"] = datetime.now().isoformat()
                self.session_info["first_start"] = checkpoint.get('first_start')
                self.session_info["copy_phase_start"] = checkpoint.get('copy_phase_start')
                
                print(f"\n🔄 RETOMANDO EXECUÇÃO ANTERIOR (Retomada #{self.session_info['resume_count']})")
                print(f"   📅 Primeira execução: {self.session_info['first_start']}")
                print(f"   📋 {len(self.processed_files_set)} arquivos já processados")
                print(f"   ✅ {self.stats.get('total_compressed', 0)} comprimidos")
                print(f"   ❌ {self.stats.get('total_errors', 0)} erros/sem compressão")
                print(f"   💾 {self._format_size(self.stats.get('space_saved_bytes', 0))} economizados\n")
                
                return True
        except Exception as e:
            print(f"⚠️  Erro ao carregar checkpoint: {e}")
            print("   Iniciando do zero...\n")
        
        return False
    
    def _save_checkpoint(self):
        """Salva checkpoint com progresso atual"""
        try:
            checkpoint = {
                'processed_files': list(self.processed_files_set),
                'stats': self.stats,
                'last_update': datetime.now().isoformat(),
                'first_start': self.session_info['first_start'],
                'resume_count': self.session_info['resume_count'],
                'copy_phase_start': self.session_info['copy_phase_start']
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Erro ao salvar checkpoint: {e}")
    
    def _cleanup_checkpoint(self):
        """Remove arquivo de checkpoint após conclusão bem-sucedida"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                print("\n🗑️  Checkpoint removido (processamento completo)")
        except Exception as e:
            print(f"⚠️  Erro ao remover checkpoint: {e}")
    
    def _update_log_realtime(self):
        """Atualiza o arquivo de log em tempo real (resumo geral + últimos 1000 arquivos)"""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        # Carrega histórico existente
        processed_history = []
        existing_files_set = set()  # OTIMIZAÇÃO: set para verificação O(1)
        
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    existing_log = json.load(f)
                    processed_history = existing_log.get("processed_files_history", [])
                    # Cria set de arquivos existentes (MUITO mais rápido)
                    existing_files_set = {item.get("file") or item.get("original_path") for item in processed_history}
            except:
                pass
        
        # Adiciona apenas novos arquivos ao histórico (verificação O(1) com set)
        for file_info in self.stats["processed_files"]:
            file_path = file_info.get("file") or file_info.get("original_path")
            if file_path and file_path not in existing_files_set:
                processed_history.append(file_info)
                existing_files_set.add(file_path)
        
        # Mantém apenas os últimos 1000 (FIFO - First In First Out)
        if len(processed_history) > 1000:
            processed_history = processed_history[-1000:]
        
        # Calcula porcentagem de conclusão
        total_processed = len(self.processed_files_set)
        completion_pct = (total_processed / self.stats['total_found'] * 100) if self.stats['total_found'] > 0 else 0
        
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
                "execution_end": None,
                "status": "in_progress",
                "duration_seconds": round(duration, 2),
                "completion_percentage": round(completion_pct, 2),
                "statistics": {
                    "total_found": self.stats["total_found"],
                    "total_processed": len(self.processed_files_set),
                    "total_compressed": self.stats["total_compressed"],
                    "total_errors": self.stats["total_errors"],
                    "total_copied_without_compression": self.stats.get("total_copied", 0),
                    "total_original_size": self._format_size(self.stats["total_original_bytes"]),
                    "total_final_size": self._format_size(self.stats["total_final_bytes"]),
                    "space_saved": self._format_size(self.stats["space_saved_bytes"]),
                    "error_breakdown": self.stats.get("error_breakdown", {}),
                    "compression_ranges": self.stats.get("compression_ranges", {})
                }
            },
            "processed_files_history": processed_history,
            "recent_errors": self.stats["errors"][-50:]  # Últimos 50 erros
        }
        
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Não interrompe o processamento se o log falhar
            pass
    
    def _finalize_log(self, duration: float):
        """Finaliza o arquivo de log com status completo"""
        # Carrega histórico existente (dos saves incrementais)
        processed_history = []
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, 'r', encoding='utf-8') as f:
                    existing_log = json.load(f)
                    processed_history = existing_log.get("processed_files_history", [])
            except:
                pass
        
        # Adiciona arquivos que ainda não estão no histórico
        existing_paths = {item.get("file") or item.get("original_path") for item in processed_history}
        for file_info in self.stats["processed_files"]:
            file_path = file_info.get("file") or file_info.get("original_path")
            if file_path and file_path not in existing_paths:
                processed_history.append(file_info)
        
        # Mantém últimos 1000 no histórico
        if len(processed_history) > 1000:
            processed_history = processed_history[-1000:]
        
        # Calcula porcentagem de conclusão
        total_processed = len(self.processed_files_set)
        completion_pct = (total_processed / self.stats['total_found'] * 100) if self.stats['total_found'] > 0 else 0
        
        log_data = {
            "log_info": {
                "description": "Log rotativo - mantém resumo geral + últimos 1000 arquivos processados",
                "last_update": datetime.now().isoformat(),
                "total_files_in_history": len(processed_history),
                "history_limit": 1000,
                "note": "Arquivos mais antigos são removidos automaticamente (FIFO)"
            },
            "summary": {
                "execution_start": self.start_time.isoformat() if self.start_time else datetime.now().isoformat(),
                "execution_end": datetime.now().isoformat(),
                "status": "completed",
                "duration_seconds": round(duration, 2),
                "completion_percentage": round(completion_pct, 2),
                "statistics": {
                    "total_found": self.stats["total_found"],
                    "total_processed": total_processed,
                    "total_compressed": self.stats["total_compressed"],
                    "total_errors": self.stats["total_errors"],
                    "total_copied_without_compression": self.stats.get("total_copied", 0),
                    "total_original_size": self._format_size(self.stats["total_original_bytes"]),
                    "total_final_size": self._format_size(self.stats["total_final_bytes"]),
                    "space_saved": self._format_size(self.stats["space_saved_bytes"]),
                    "error_breakdown": self.stats.get("error_breakdown", {}),
                    "compression_ranges": self.stats.get("compression_ranges", {})
                }
            },
            "processed_files_history": processed_history,
            "all_errors": self.stats["errors"]
        }
        
        try:
            # Salva log completo
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
            print(f"📝 Log final salvo em: {self.log_file_path}")
            
            # Cria um resumo separado para facilitar consulta rápida
            summary_path = self.log_file_path.replace('.json', '_summary.json')
            summary_data = {
                "execution_start": self.start_time.isoformat() if self.start_time else datetime.now().isoformat(),
                "execution_end": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "statistics": log_data["statistics"],
                "error_breakdown_details": {
                    "already_optimized": self.stats.get("error_breakdown", {}).get("already_optimized", 0),
                    "minimal_gain": self.stats.get("error_breakdown", {}).get("minimal_gain", 0),
                    "password_protected": self.stats.get("error_breakdown", {}).get("password_protected", 0),
                    "corrupted": self.stats.get("error_breakdown", {}).get("corrupted", 0),
                    "permission_denied": self.stats.get("error_breakdown", {}).get("permission_denied", 0),
                    "other": self.stats.get("error_breakdown", {}).get("other", 0)
                },
                "compression_breakdown": {
                    "excellent_50_plus": self.stats.get("compression_ranges", {}).get("excellent", 0),
                    "good_30_to_50": self.stats.get("compression_ranges", {}).get("good", 0),
                    "moderate_15_to_30": self.stats.get("compression_ranges", {}).get("moderate", 0),
                    "low_5_to_15": self.stats.get("compression_ranges", {}).get("low", 0),
                    "minimal_below_5": self.stats.get("compression_ranges", {}).get("minimal", 0)
                },
                "top_compressions": sorted(
                    [f for f in self.stats["processed_files"] if f["status"] == "success"],
                    key=lambda x: x["original_size"] - x["compressed_size"],
                    reverse=True
                )[:20]  # Top 20 melhores compressões
            }
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"📊 Resumo salvo em: {summary_path}")
            
        except Exception as e:
            print(f"⚠️  Não foi possível salvar o log final: {e}")

    
    def _find_all_files(self, root_path: str) -> tuple[List[Path], List[Path]]:
        """Encontra todos os arquivos (PDFs e não-PDFs) recursivamente (otimizado para grandes volumes)"""
        self._update_status("🔍 Procurando arquivos PDF...")
        
        pdfs = []
        other_files = []
        root = Path(root_path)
        
        if not root.exists():
            print(f"❌ ERRO: Caminho '{root_path}' não existe!")
            return pdfs, other_files
        
        if not root.is_dir():
            print(f"❌ ERRO: '{root_path}' não é um diretório!")
            return pdfs, other_files
        
        compress_folder_name = self.config["compress_folder_name"]
        allowed_extensions = self.config.get("processing", {}).get("allowed_extensions", [".pdf", ".PDF"])
        
        # Busca OTIMIZADA com os.walk (5-10x mais rápido que rglob)
        print("   Escaneando diretórios (otimizado)...", end="", flush=True)
        count_pdfs = 0
        count_others = 0
        
        # os.walk é muito mais rápido para grandes volumes
        for dirpath, dirnames, filenames in os.walk(root):
            # Remove pasta compress da busca ANTES de entrar nela
            dirnames[:] = [d for d in dirnames if d != compress_folder_name]
            
            # Processa todos os arquivos
            for filename in filenames:
                file_path = Path(dirpath) / filename
                
                if any(filename.endswith(ext) for ext in allowed_extensions):
                    pdfs.append(file_path)
                    count_pdfs += 1
                else:
                    other_files.append(file_path)
                    count_others += 1
                    
                # Feedback a cada 1000 arquivos (reduz I/O)
                if (count_pdfs + count_others) % 1000 == 0:
                    print(f"\r   Escaneando... {count_pdfs:,} PDFs, {count_others:,} outros", end="", flush=True)
        
        print(f"\r   ✅ Encontrados {count_pdfs:,} PDFs e {count_others:,} outros arquivos!                    ")
        
        # Ordenação opcional (descomente se precisar)
        # pdfs.sort()
        return pdfs, other_files
    
    
    def _copy_other_file(self, file_path: Path, root_path: str, compress_folder: Path) -> bool:
        """Copia arquivo não-PDF mantendo a estrutura de pastas"""
        try:
            # Calcula caminho relativo ao root
            relative_path = file_path.relative_to(root_path)
            target_path = compress_folder / relative_path
            
            # Cria diretórios necessários
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copia arquivo preservando metadados
            shutil.copy2(file_path, target_path)
            return True
            
        except Exception as e:
            print(f"❌ Erro ao copiar '{file_path.name}': {e}")
            return False
    
    def _get_unique_filename(self, target_path: Path) -> Path:
        """Gera nome único se arquivo já existe"""
        if not target_path.exists():
            return target_path
        
        counter = 1
        suffix_pattern = self.config["processing"]["suffix_pattern"]
        stem = target_path.stem
        extension = target_path.suffix
        parent = target_path.parent
        
        while True:
            new_name = f"{stem}{suffix_pattern.format(counter=counter)}{extension}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _compress_pdf(self, input_path: Path, output_path: Path) -> Tuple[bool, str, int, int, str]:
        """
        Comprime um PDF individual
        Retorna: (sucesso, mensagem, tamanho_original, tamanho_comprimido, categoria_erro)
        """
        try:
            original_size = input_path.stat().st_size
            
            # Abre o PDF com pikepdf
            with pikepdf.open(input_path) as pdf:
                # Configurações de compressão
                compress_settings = self.config["compression_settings"]
                
                # Remove objetos duplicados para reduzir tamanho
                if compress_settings.get("remove_duplicates", True):
                    try:
                        pdf.remove_unreferenced_resources()
                    except:
                        pass
                
                # Processa imagens no PDF para reduzir tamanho (com qualidade alta)
                if compress_settings.get("recompress_images", True):
                    self._compress_images_in_pdf(pdf, compress_settings.get("image_quality", 95))
                
                # Salva com máxima compressão
                # compress_streams: comprime todos os streams
                # stream_decode_level.generalized: máxima descompressão antes de recomprimir
                # object_stream_mode.generate: agrupa objetos em streams para melhor compressão
                # linearize: otimiza estrutura do PDF (não pode usar com normalize_content)
                pdf.save(
                    output_path,
                    compress_streams=True,
                    stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    linearize=True,
                    recompress_flate=True  # Recomprime streams deflate para máxima compressão
                )
            
            compressed_size = output_path.stat().st_size
            
            # Calcula taxa de compressão
            compression_ratio = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0
            
            # Verifica se realmente comprimiu
            if compressed_size >= original_size:
                # Copia o arquivo original ao invés de remover
                shutil.copy2(input_path, output_path)
                return False, f"PDF já otimizado - sem ganho de compressão", original_size, original_size, "already_optimized"
            
            # ACEITA QUALQUER GANHO DE COMPRESSÃO, mesmo que seja 0.1%
            # Prioridade: qualidade + redução de tamanho (velocidade não importa)
            return True, f"Comprimido com sucesso ({compression_ratio:.1f}% de redução)", original_size, compressed_size, None
            
        except pikepdf.PasswordError:
            # Copia o arquivo original mesmo com erro
            try:
                shutil.copy2(input_path, output_path)
            except:
                pass
            return False, "PDF protegido por senha - arquivo copiado", input_path.stat().st_size, input_path.stat().st_size, "password_protected"
        except pikepdf.PdfError as e:
            # Copia o arquivo original mesmo com erro
            try:
                shutil.copy2(input_path, output_path)
            except:
                pass
            error_msg = str(e).lower()
            if "damaged" in error_msg or "corrupt" in error_msg or "invalid" in error_msg:
                return False, f"PDF corrompido - arquivo copiado", input_path.stat().st_size, input_path.stat().st_size, "corrupted"
            return False, f"Erro no PDF - arquivo copiado: {str(e)[:100]}", input_path.stat().st_size, input_path.stat().st_size, "other_errors"
        except PermissionError:
            return False, "PDF em uso ou sem permissão - não copiado", 0, 0, "permission_denied"
        except Exception as e:
            # Copia o arquivo original mesmo com erro
            try:
                shutil.copy2(input_path, output_path)
            except:
                pass
            return False, f"Erro desconhecido - arquivo copiado: {str(e)[:100]}", input_path.stat().st_size, input_path.stat().st_size, "other_errors"
    
    def _compress_images_in_pdf(self, pdf: pikepdf.Pdf, quality: int):
        """Comprime imagens dentro do PDF usando técnicas avançadas"""
        try:
            # Itera sobre todos os objetos do PDF para encontrar imagens
            for obj in list(pdf.objects):
                try:
                    if not isinstance(obj, pikepdf.Stream) or obj.get("/Subtype") != "/Image":
                        continue
                    
                    # Pega o filtro da imagem
                    filt = obj.get("/Filter")
                    if isinstance(filt, pikepdf.Array) and len(filt) > 0:
                        filt = filt[0]
                    
                    # Otimiza apenas imagens PNG/Flate (sem perdas) ou JPEG com alta qualidade
                    if filt == pikepdf.Name.FlateDecode:
                        # Imagem PNG - usa compressão zlib agressiva
                        self._optimize_flate_image(pdf, obj, quality)
                    elif filt == pikepdf.Name.DCTDecode:
                        # Imagem JPEG - recomprime apenas se qualidade for menor que atual
                        self._optimize_jpeg_image(obj, quality)
                    
                except Exception as e:
                    # Se falhar em uma imagem, continua com as outras
                    continue
                    
        except Exception:
            # Se falhar no processamento de imagens, continua sem comprimir imagens
            pass
    
    def _optimize_flate_image(self, pdf: pikepdf.Pdf, obj: pikepdf.Stream, quality: int):
        """Otimiza imagens PNG/Flate usando compressão zlib (técnica da minimalpdfcompress)"""
        try:
            original_size = len(obj.read_raw_bytes())
            if original_size == 0:
                return
            
            # Extrai a imagem
            pdfimage = pikepdf.PdfImage(obj)
            pil_image = pdfimage.as_pil_image()
            
            # Verifica se tem transparência
            has_transparency = 'A' in pil_image.mode
            
            if has_transparency:
                # Separa RGB e Alpha para melhor compressão
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                
                rgb_image = Image.new("RGB", pil_image.size, (255, 255, 255))
                rgb_image.paste(pil_image, mask=pil_image.split()[3])
                alpha_image = pil_image.split()[3]
                
                # Comprime RGB e Alpha separadamente com zlib (máxima compressão)
                compressed_rgb = zlib.compress(rgb_image.tobytes(), level=9)
                compressed_alpha = zlib.compress(alpha_image.tobytes(), level=9)
                total_new_size = len(compressed_rgb) + len(compressed_alpha)
                
                if total_new_size < original_size:
                    # Limpa o stream e escreve novo conteúdo
                    for key in list(obj.keys()):
                        del obj[key]
                    
                    obj.write(compressed_rgb)
                    obj.Type = pikepdf.Name.XObject
                    obj.Subtype = pikepdf.Name.Image
                    obj.Filter = pikepdf.Name.FlateDecode
                    obj.Width = pil_image.width
                    obj.Height = pil_image.height
                    obj.ColorSpace = pikepdf.Name.DeviceRGB
                    obj.BitsPerComponent = 8
                    
                    # Cria stream SMask para transparência
                    smask_stream = pdf.make_stream(compressed_alpha)
                    smask_stream.Type = pikepdf.Name.XObject
                    smask_stream.Subtype = pikepdf.Name.Image
                    smask_stream.Filter = pikepdf.Name.FlateDecode
                    smask_stream.Width = pil_image.width
                    smask_stream.Height = pil_image.height
                    smask_stream.ColorSpace = pikepdf.Name.DeviceGray
                    smask_stream.BitsPerComponent = 8
                    obj.SMask = smask_stream
            else:
                # Sem transparência - comprime direto
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                
                compressed_rgb = zlib.compress(pil_image.tobytes(), level=9)
                
                if len(compressed_rgb) < original_size:
                    for key in list(obj.keys()):
                        del obj[key]
                    
                    obj.write(compressed_rgb)
                    obj.Type = pikepdf.Name.XObject
                    obj.Subtype = pikepdf.Name.Image
                    obj.Filter = pikepdf.Name.FlateDecode
                    obj.Width = pil_image.width
                    obj.Height = pil_image.height
                    obj.ColorSpace = pikepdf.Name.DeviceRGB
                    obj.BitsPerComponent = 8
                    if pikepdf.Name.SMask in obj:
                        del obj[pikepdf.Name.SMask]
        
        except Exception:
            pass
    
    def _optimize_jpeg_image(self, obj: pikepdf.Stream, quality: int):
        """Otimiza imagens JPEG mantendo alta qualidade"""
        try:
            original_size = len(obj.read_raw_bytes())
            if original_size == 0:
                return
            
            # Extrai e recomprime JPEG
            pdfimage = pikepdf.PdfImage(obj)
            pil_image = pdfimage.as_pil_image()
            
            img_byte_arr = io.BytesIO()
            
            # Converte para RGB se necessário
            if pil_image.mode == 'RGBA':
                background = Image.new('RGB', pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[3])
                pil_image = background
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Salva com qualidade alta e otimização agressiva
            pil_image.save(img_byte_arr, format='JPEG', quality=quality, optimize=True, progressive=True)
            new_bytes = img_byte_arr.getvalue()
            
            # Só substitui se for menor
            if len(new_bytes) < original_size:
                obj.write(new_bytes)
                obj.Filter = pikepdf.Name.DCTDecode
                if '/DecodeParms' in obj:
                    del obj['/DecodeParms']
        
        except Exception:
            pass
    
    def _create_compress_folder(self, root_path: str) -> Path:
        """Cria pasta compress no local configurado"""
        compress_output = self.config.get("compress_output_path", "same_as_root")
        
        if compress_output == "same_as_root":
            # Cria pasta compress dentro do root_path
            compress_folder = Path(root_path) / self.config["compress_folder_name"]
        else:
            # Usa caminho personalizado + nome da pasta compress
            compress_folder = Path(compress_output) / self.config["compress_folder_name"]
        
        try:
            compress_folder.mkdir(parents=True, exist_ok=True)
            return compress_folder
        except PermissionError:
            print(f"❌ ERRO: Sem permissão para criar pasta '{compress_folder}'")
            raise
        except Exception as e:
            print(f"❌ ERRO ao criar pasta compress: {e}")
            raise
    
    def process_all_pdfs(self):
        """Processa todos os PDFs encontrados"""
        self.start_time = datetime.now()
        self.session_info['current_start'] = self.start_time.isoformat()
        
        # 1. Tentar acessar a pasta
        self._update_status("🔌 Tentando acessar a pasta...")
        root_path = self.config["root_path"]
        
        if not os.path.exists(root_path):
            print(f"❌ ERRO: Não foi possível acessar '{root_path}'")
            self._finalize_log(0)
            return
        
        print(f"✅ Pasta acessada: {root_path}")
        
        # 2. Criar pasta compress
        compress_folder = self._create_compress_folder(root_path)
        print(f"✅ Pasta de destino criada/verificada: {compress_folder}")
        
        # 3. Carregar checkpoint (se existir)
        resuming = self._load_checkpoint()
        
        # Se não está retomando, esta é a primeira execução
        if not resuming:
            self.session_info['first_start'] = self.start_time.isoformat()
        
        # 4. Procurar arquivos (PDFs e outros)
        pdf_files, other_files = self._find_all_files(root_path)
        
        # Filtrar PDFs já processados
        pdfs_to_process = [pdf for pdf in pdf_files if str(pdf) not in self.processed_files_set]
        
        self.stats["total_found"] = len(pdf_files)
        already_processed = len(pdf_files) - len(pdfs_to_process)
        
        print(f"✅ {self.stats['total_found']} PDFs encontrados, {len(other_files)} outros arquivos")
        if already_processed > 0:
            print(f"⏭️  Pulando {already_processed} arquivos já processados")
        print(f"🎯 {len(pdfs_to_process)} PDFs para comprimir + {len(other_files)} arquivos para copiar\n")
        
        # Atualiza log após encontrar PDFs
        self._update_log_realtime()
        
        if len(pdfs_to_process) == 0:
            print("\n✅ Todos os PDFs já foram processados!")
            # NÃO RETORNA - continua para copiar outros arquivos
        else:
            # 5. Comprimir PDFs (apenas os não processados)
            self._update_status(f"🗜️  Comprimindo {len(pdfs_to_process)} PDFs...")
            
            for idx, pdf_path in enumerate(pdfs_to_process, 1):
                relative_path = pdf_path.relative_to(root_path)
                print(f"\n[{idx}/{len(pdfs_to_process)}] Processando: {relative_path}")
                
                # Define caminho de saída (mantém nome original na pasta compress)
                output_path = compress_folder / pdf_path.name
                
                # Verifica conflito de nome
                if self.config["processing"]["add_suffix_on_conflict"] and output_path.exists():
                    output_path = self._get_unique_filename(output_path)
                
                # Comprime o PDF
                success, message, original_size, compressed_size, error_category = self._compress_pdf(pdf_path, output_path)
                
                # Atualiza estatísticas por categoria
                if success:
                    # Classifica por faixa de compressão
                    compression_ratio = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0
                    if compression_ratio >= 50:
                        self.stats["compression_ranges"]["excellent"] += 1
                    elif compression_ratio >= 30:
                        self.stats["compression_ranges"]["good"] += 1
                    elif compression_ratio >= 15:
                        self.stats["compression_ranges"]["moderate"] += 1
                    elif compression_ratio >= 5:
                        self.stats["compression_ranges"]["low"] += 1
                    else:
                        self.stats["compression_ranges"]["minimal"] += 1
                
                # Registra categoria de erro se houver
                if error_category:
                    self.stats["error_breakdown"][error_category] = self.stats["error_breakdown"].get(error_category, 0) + 1
                    self.stats["total_copied"] += 1
                
                file_info = {
                    "file": str(relative_path),
                    "original_path": str(pdf_path),
                    "compressed_path": str(output_path),
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": round(((original_size - compressed_size) / original_size) * 100, 2) if original_size > 0 else 0,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success" if success else "error",
                    "error_category": error_category if error_category else None,
                    "message": message
                }
                
                if success:
                    self.stats["total_compressed"] += 1
                    self.stats["total_original_bytes"] += original_size
                    self.stats["total_final_bytes"] += compressed_size
                    self.stats["space_saved_bytes"] += (original_size - compressed_size)
                    print(f"   ✅ {message}")
                    print(f"   📦 {self._format_size(original_size)} → {self._format_size(compressed_size)}")
                else:
                    if error_category in ["already_optimized", "minimal_gain"]:
                        print(f"   ℹ️  {message}")
                    elif error_category == "password_protected":
                        print(f"   🔒 {message}")
                    elif error_category == "corrupted":
                        print(f"   ⚠️  {message}")
                    else:
                        print(f"   ❌ {message}")
                    self.stats["total_errors"] += 1
                    self.stats["errors"].append(file_info)
                
                self.stats["processed_files"].append(file_info)
                
                # Adiciona ao set de processados
                self.processed_files_set.add(str(pdf_path))
                
                # Atualiza log e checkpoint a cada 10 arquivos
                if idx % 10 == 0 or idx == len(pdfs_to_process):
                    self._update_log_realtime()
                    self._save_checkpoint()
        
        # 6. Copiar outros arquivos (não-PDFs)
        if len(other_files) > 0:
            # Registra início da fase de cópia (apenas na primeira vez)
            if not self.session_info['copy_phase_start']:
                self.session_info['copy_phase_start'] = datetime.now().isoformat()
            
            print(f"\n{'='*60}")
            print(f"📁 COPIANDO {len(other_files)} OUTROS ARQUIVOS")
            print(f"📅 Fase de cópia iniciada: {self.session_info['copy_phase_start']}")
            print(f"{'='*60}\n")
            
            copied_count = 0
            for idx, file_path in enumerate(other_files, 1):
                try:
                    if self._copy_other_file(file_path, root_path, compress_folder):
                        copied_count += 1
                    
                    # Mostra progresso a cada 100 arquivos
                    if idx % 100 == 0 or idx == len(other_files):
                        print(f"📋 Copiados: {copied_count}/{idx}", end="\r", flush=True)
                        
                except KeyboardInterrupt:
                    print(f"\n\n⚠️  Interrompido pelo usuário após {copied_count} arquivos copiados!")
                    break
            
            print(f"\n✅ Copiados: {copied_count}/{len(other_files)} arquivos\n")
        
        # 7. Finalizar
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Remove checkpoint após conclusão bem-sucedida
        self._cleanup_checkpoint()
        
        self._update_status("✅ TAREFA FINALIZADA")
        
        print(f"\n{'='*60}")
        print("📈 RESUMO DA COMPRESSÃO")
        print(f"{'='*60}")
        print(f"📁 PDFs encontrados: {self.stats['total_found']}")
        print(f"✅ PDFs comprimidos: {self.stats['total_compressed']}")
        print(f"⚠️  Erros/Sem compressão: {self.stats['total_errors']}")
        
        # Breakdown de erros
        error_breakdown = self.stats.get("error_breakdown", {})
        if error_breakdown:
            print(f"\n📊 CATEGORIAS DE ERRO:")
            if error_breakdown.get("already_optimized", 0) > 0:
                print(f"   📦 Já otimizados: {error_breakdown['already_optimized']}")
            if error_breakdown.get("minimal_gain", 0) > 0:
                print(f"   📉 Ganho mínimo (<5%): {error_breakdown['minimal_gain']}")
            if error_breakdown.get("password_protected", 0) > 0:
                print(f"   🔒 Protegidos por senha: {error_breakdown['password_protected']}")
            if error_breakdown.get("corrupted", 0) > 0:
                print(f"   ⚠️  Corrompidos: {error_breakdown['corrupted']}")
            if error_breakdown.get("permission_denied", 0) > 0:
                print(f"   🚫 Sem permissão: {error_breakdown['permission_denied']}")
            if error_breakdown.get("other", 0) > 0:
                print(f"   ❓ Outros: {error_breakdown['other']}")
        
        # Breakdown de compressão
        compression_ranges = self.stats.get("compression_ranges", {})
        if compression_ranges and sum(compression_ranges.values()) > 0:
            print(f"\n📊 FAIXAS DE COMPRESSÃO:")
            if compression_ranges.get("excellent", 0) > 0:
                print(f"   🌟 Excelente (>50%): {compression_ranges['excellent']}")
            if compression_ranges.get("good", 0) > 0:
                print(f"   ✅ Boa (30-50%): {compression_ranges['good']}")
            if compression_ranges.get("moderate", 0) > 0:
                print(f"   📊 Moderada (15-30%): {compression_ranges['moderate']}")
            if compression_ranges.get("low", 0) > 0:
                print(f"   📉 Baixa (5-15%): {compression_ranges['low']}")
            if compression_ranges.get("minimal", 0) > 0:
                print(f"   ⚡ Mínima (<5%): {compression_ranges['minimal']}")
        
        print(f"\n💾 Espaço economizado: {self._format_size(self.stats['space_saved_bytes'])}")
        print(f"⏱️  Tempo total: {duration:.2f} segundos")
        print(f"📂 Todos os PDFs em: {compress_folder}")
        print(f"{'='*60}\n")
        
        # Salvar log final
        self._finalize_log(duration)
    
    def _save_log(self):
        """[DEPRECATED] Mantido para compatibilidade - use _finalize_log"""
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        self._finalize_log(duration)


def main():
    """Função principal"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        SISTEMA DE COMPRESSÃO DE PDFs - ALTA QUALIDADE      ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        compressor = PDFCompressor()
        compressor.process_all_pdfs()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário!")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
