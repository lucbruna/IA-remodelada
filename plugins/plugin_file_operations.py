"""
plugin_file_operations.py
=========================
Plugin de operações avançadas de arquivos e diretórios. Fornece ferramentas para:
- Operações em lote em arquivos
- Sincronização e backup de diretórios
- Busca avançada com filtros
- Organização automática de arquivos
- Conversão e processamento de formatos
"""

import os
import shutil
import hashlib
import mimetypes
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
import fnmatch

__version__ = "1.0.0"
PLUGIN_NAME = "Operações Avançadas de Arquivos"


def _get_file_info(file_path: str) -> dict:
    """Obtém informações detalhadas sobre um arquivo."""
    try:
        stat = os.stat(file_path)
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'is_file': os.path.isfile(file_path),
            'is_dir': os.path.isdir(file_path),
            'extension': os.path.splitext(file_path)[1].lower(),
            'permissions': oct(stat.st_mode)[-3:],
            'mime_type': mimetypes.guess_type(file_path)[0] or 'unknown'
        }
    except Exception as e:
        return {'error': str(e), 'path': file_path}


def batch_rename_files(directory: str, pattern: str, replacement: str,
                      recursive: bool = False, preview: bool = True) -> str:
    """Renomeia múltiplos arquivos baseado em padrão.

    Args:
        directory: Diretório onde procurar arquivos
        pattern: Padrão a ser substituído (suporta wildcards *)
        replacement: Texto de substituição
        recursive: Se deve buscar em subdiretórios
        preview: Se True, apenas mostra o que seria feito sem executar

    Returns:
        Relatório das operações realizadas ou que seriam realizadas
    """
    if not os.path.exists(directory):
        return f"Diretório não encontrado: {directory}"

    files_renamed = []
    errors = []

    walk_func = os.walk if recursive else lambda x: [(x, [], os.listdir(x))]

    try:
        for root, dirs, files in walk_func(directory):
            for filename in files:
                if '*' in pattern:
                    # Simple wildcard handling
                    import re
                    regex_pattern = pattern.replace('*', '.*')
                    if re.search(regex_pattern, filename):
                        new_name = re.sub(regex_pattern, replacement, filename)
                        if new_name != filename:
                            old_path = os.path.join(root, filename)
                            new_path = os.path.join(root, new_name)
                            files_renamed.append((old_path, new_path))
                            if not preview:
                                try:
                                    os.rename(old_path, new_path)
                                except Exception as e:
                                    errors.append(f"{old_path}: {str(e)}")
                else:
                    if pattern in filename:
                        new_name = filename.replace(pattern, replacement)
                        if new_name != filename:
                            old_path = os.path.join(root, filename)
                            new_path = os.path.join(root, new_name)
                            files_renamed.append((old_path, new_path))
                            if not preview:
                                try:
                                    os.rename(old_path, new_path)
                                except Exception as e:
                                    errors.append(f"{old_path}: {str(e)}")

        result = []
        result.append(f"{'PREVISÃO' if preview else 'EXECUÇÃO'} de renomeação em lote")
        result.append(f"Diretório: {directory}")
        result.append(f"Padrão: '{pattern}' -> '{replacement}'")
        result.append(f"Recursivo: {recursive}")
        result.append(f"\nArquivos afetados: {len(files_renamed)}")

        if files_renamed:
            result.append("\nAlterações:")
            for old_path, new_path in files_renamed[:10]:  # Show first 10
                result.append(f"  {os.path.basename(old_path)} → {os.path.basename(new_path)}")
            if len(files_renamed) > 10:
                result.append(f"  ... e mais {len(files_renamed) - 10} arquivos")

        if errors:
            result.append(f"\n❌ Erros ({len(errors)}):")
            for error in errors[:5]:
                result.append(f"  • {error}")

        if preview and not files_renamed:
            result.append("\n💡 Nenhum arquivo corresponde ao padrão especificado.")

        return "\n".join(result)

    except Exception as e:
        return f"Erro durante operação de renomeação em lote: {str(e)}"


def sync_directories(source: str, destination: str, mode: str = "mirror",
                     exclude_patterns: list = None) -> str:
    """Sincroniza dois diretórios.

    Args:
        source: Diretório de origem
        destination: Diretório de destino
        mode: Modo de sincronização ('mirror', 'backup', 'sync')
        exclude_patterns: Lista de padrões para excluir (ex: ['*.tmp', '__pycache__'])

    Returns:
        Relatório da sincronização
    """
    if exclude_patterns is None:
        exclude_patterns = ['*.tmp', '*.log', '__pycache__', '.git']

    if not os.path.exists(source):
        return f"Diretório de origem não encontrado: {source}"

    # Create destination if it doesn't exist (for backup/mirror modes)
    if mode in ['mirror', 'backup'] and not os.path.exists(destination):
        try:
            os.makedirs(destination)
        except Exception as e:
            return f"Erro ao criar diretório de destino: {str(e)}"

    if not os.path.exists(destination):
        return f"Diretório de destino não encontrado: {destination}"

    def should_exclude(path: str) -> bool:
        """Verifica se um caminho deve ser excluído baseado nos padrões."""
        name = os.path.basename(path)
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        return False

    try:
        stats = {
            'copied': 0,
            'updated': 0,
            'deleted': 0,
            'skipped': 0,
            'errors': []
        }

        if mode == "mirror":
            # Make destination exactly like source
            # First, copy/update files from source to destination
            for root, dirs, files in os.walk(source):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

                for file in files:
                    src_file = os.path.join(root, file)
                    if should_exclude(src_file):
                        stats['skipped'] += 1
                        continue

                    # Calculate relative path
                    rel_path = os.path.relpath(src_file, source)
                    dest_file = os.path.join(destination, rel_path)

                    # Ensure destination directory exists
                    dest_dir = os.path.dirname(dest_file)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)

                    # Copy if doesn't exist or is newer
                    if not os.path.exists(dest_file):
                        shutil.copy2(src_file, dest_file)
                        stats['copied'] += 1
                    else:
                        src_time = os.path.getmtime(src_file)
                        dest_time = os.path.getmtime(dest_file)
                        if src_time > dest_time:
                            shutil.copy2(src_file, dest_file)
                            stats['updated'] += 1
                        else:
                            stats['skipped'] += 1

            # Then, delete files in destination that don't exist in source
            for root, dirs, files in os.walk(destination, topdown=False):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

                for file in files:
                    dest_file = os.path.join(root, file)
                    if should_exclude(dest_file):
                        continue

                    # Calculate relative path
                    rel_path = os.path.relpath(dest_file, destination)
                    src_file = os.path.join(source, rel_path)

                    if not os.path.exists(src_file):
                        os.remove(dest_file)
                        stats['deleted'] += 1

                # Remove empty directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if should_exclude(dir_path):
                        continue
                    try:
                        if not os.listdir(dir_path):  # Empty directory
                            os.rmdir(dir_path)
                            stats['deleted'] += 1  # Count as removed
                    except OSError:
                        pass  # Directory not empty or permission issue

        elif mode == "backup":
            # Copy new and updated files from source to destination (don't delete)
            for root, dirs, files in os.walk(source):
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d))]

                for file in files:
                    src_file = os.path.join(root, file)
                    if should_exclude(src_file):
                        stats['skipped'] += 1
                        continue

                    # Calculate relative path
                    rel_path = os.path.relpath(src_file, source)
                    dest_file = os.path.join(destination, rel_path)

                    # Ensure destination directory exists
                    dest_dir = os.path.dirname(dest_file)
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)

                    # Copy if doesn't exist or is newer
                    if not os.path.exists(dest_file):
                        shutil.copy2(src_file, dest_file)
                        stats['copied'] += 1
                    else:
                        src_time = os.path.getmtime(src_file)
                        dest_time = os.path.getmtime(dest_file)
                        if src_time > dest_time:
                            shutil.copy2(src_file, dest_file)
                            stats['updated'] += 1
                        else:
                            stats['skipped'] += 1

        elif mode == "sync":
            # Bidirectional sync (simplified - newer wins)
            # This is a basic implementation - a full bidirectional sync is complex
            return "Modo 'sync' não implementado completamente nesta versão. Use 'mirror' ou 'backup'."

        # Generate report
        result = []
        result.append(f"🔄 SINCRONIZAÇÃO DE DIRETÓRIOS ({mode.upper()})")
        result.append(f"Origem: {source}")
        result.append(f"Destino: {destination}")
        result.append("")
        result.append("📊 ESTATÍSTICAS:")
        result.append(f"  Arquivos copiados: {stats['copied']}")
        result.append(f"  Arquivos atualizados: {stats['updated']}")
        result.append(f"  Arquivos deletados: {stats['deleted']}")
        result.append(f"  Arquivos ignorados: {stats['skipped']}")
        if stats['errors']:
            result.append(f"  Erros: {len(stats['errors'])}")

        if stats['errors']:
            result.append("\n❌ ERROS:")
            for error in stats['errors'][:5]:
                result.append(f"  • {error}")

        total_ops = stats['copied'] + stats['updated'] + stats['deleted']
        if total_ops == 0 and not stats['errors']:
            result.append("\n✅ Nenhuma operação necessária - diretórios já estão sincronizados")
        elif total_ops > 0:
            result.append(f"\n✅ Sincronização concluída com {total_ops} operações")

        return "\n".join(result)

    except Exception as e:
        return f"Erro durante sincronização: {str(e)}"


def find_files_advanced(directory: str, name_pattern: str = None,
                       content_pattern: str = None, file_type: str = None,
                       size_min: int = None, size_max: int = None,
                       date_after: str = None, date_before: str = None,
                       contain_text: str = None, regex_search: bool = False,
                       limit: int = 100) -> str:
    """Busca avançada de arquivos com múltiplos critérios.

    Args:
        directory: Diretório onde buscar
        name_pattern: Padrão de nome do arquivo (suporta wildcards)
        content_pattern: Padrão de conteúdo dentro do arquivo
        file_type: Tipo de arquivo baseado na extensão (ex: 'pdf', 'jpg')
        size_min: Tamanho mínimo em bytes
        size_max: Tamanho máximo em bytes
        date_after: Data pós-que no formato YYYY-MM-DD
        date_before: Data anterior no formato YYYY-MM-DD
        contain_text: Texto que deve estar contido no arquivo
        regex_search: Se deve usar expressão regular para busca de conteúdo
        limit: Número máximo de resultados

    Returns:
        Lista de arquivos encontrados com detalhes
    """
    if not os.path.exists(directory):
        return f"Diretório não encontrado: {directory}"

    results = []
    errors = []

    # Parse dates if provided
    try:
        date_after_dt = datetime.strptime(date_after, "%Y-%m-%d") if date_after else None
        date_before_dt = datetime.strptime(date_before, "%Y-%m-%d") if date_before else None
    except ValueError:
        return "Formato de data inválido. Use YYYY-MM-DD"

    try:
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)

                # Check name pattern
                if name_pattern:
                    if not fnmatch.fnmatch(filename, name_pattern):
                        continue

                # Check file type
                if file_type:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext != f".{file_type.lower()}" and ext != f".{file_type}":
                        continue

                try:
                    # Get file stats
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    file_mtime = datetime.fromtimestamp(stat.st_mtime)

                    # Check size constraints
                    if size_min is not None and file_size < size_min:
                        continue
                    if size_max is not None and file_size > size_max:
                        continue

                    # Check date constraints
                    if date_after_dt and file_mtime < date_after_dt:
                        continue
                    if date_before_dt and file_mtime > date_before_dt:
                        continue

                    # Check content (if requested)
                    if content_pattern or contain_text:
                        try:
                            # Try to read as text file
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()

                            match_found = False
                            if content_pattern:
                                if regex_search:
                                    import re
                                    if re.search(content_pattern, content):
                                        match_found = True
                                else:
                                    if content_pattern in content:
                                        match_found = True

                            if contain_text:
                                if contain_text.lower() in content.lower():
                                    match_found = True

                            if not match_found:
                                continue  # Skip if content doesn't match

                        except (UnicodeDecodeError, OSError):
                            # If we can't read as text, skip content checks
                            if content_pattern or contain_text:
                                continue

                    # All checks passed
                    file_info = _get_file_info(file_path)
                    results.append(file_info)

                    if len(results) >= limit:
                        break

                except (OSError, IOError) as e:
                    errors.append(f"Erro ao processar {file_path}: {str(e)}")

            if len(results) >= limit:
                break

        # Format results
        output = []
        output.append(f"🔍 BUSCA AVANÇADA DE ARQUIVOS")
        output.append(f"Diretório: {directory}")
        if name_pattern:
            output.append(f"Padrão de nome: {name_pattern}")
        if file_type:
            output.append(f"Tipo de arquivo: {file_type}")
        if size_min is not None or size_max is not None:
            size_str = ""
            if size_min is not None:
                size_str += f"≥{size_min} bytes"
            if size_max is not None:
                if size_str:
                    size_str += f" e "
                size_str += f"≤{size_max} bytes"
            output.append(f"Tamanho: {size_str}")
        if date_after or date_before:
            date_str = ""
            if date_after:
                date_str += f"depois de {date_after}"
            if date_before:
                if date_str:
                    date_str += " e "
                date_str += f"antes de {date_before}"
            output.append(f"Data: {date_str}")
        if content_pattern or contain_text:
            output.append(f"Conteúdo: '{content_pattern or contain_text}'")
        output.append("")

        if results:
            output.append(f"📄 RESULTADOS ({len(results)} arquivos encontrados):")
            output.append("")

            for i, file_info in enumerate(results[:20], 1):  # Show first 20
                if 'error' in file_info:
                    output.append(f"{i}. ❌ {file_info['path']} - Erro: {file_info['error']}")
                else:
                    size_str = f"{file_info['size']:,} bytes"
                    if file_info['size'] > 1024*1024:
                        size_str = f"{file_info['size']/(1024*1024):.1f} MB"
                    elif file_info['size'] > 1024:
                        size_str = f"{file_info['size']/1024:.1f} KB"

                    mod_time = datetime.fromisoformat(file_info['modified']).strftime("%m/%d %H:%M")
                    output.append(
                        f"{i}. 📄 {file_info['name']} "
                        f"[{size_str}] "
                        f"[{mod_time}] "
                        f"[{file_info['extension'] or 'sem extensão'}]"
                    )
                    if file_info['path'] != file_info['name']:  # Show relative path if in subdir
                        rel_path = os.path.relpath(file_info['path'], directory)
                        if rel_path != file_info['name']:
                            output.append(f"     📁 {rel_path}")

            if len(results) > 20:
                output.append(f"  ... e mais {len(results) - 20} arquivos")
        else:
            output.append("🔍 Nenhum arquivo encontrado com os critérios especificados.")

        if errors:
            output.append(f"\n⚠️  ERROS ENCOUNTRADOS ({len(errors)}):")
            for error in errors[:5]:
                output.append(f"  • {error}")

        return "\n".join(output)

    except Exception as e:
        return f"Erro durante busca avançada: {str(e)}"


def organize_files_by_type(directory: str, destination_base: str = None,
                          create_date_folders: bool = False) -> str:
    """Organiza arquivos em subpastas baseado em seu tipo/extensão.

    Args:
        directory: Diretório com os arquivos a organizar
        destination_base: Diretório base onde organizar (se None, usa o mesmo diretório)
        create_date_folders: Se deve criar subpastas por data (AAAA/MM)

    Returns:
        Relatório da organização
    """
    if not os.path.exists(directory):
        return f"Diretório não encontrado: {directory}"

    if destination_base is None:
        destination_base = directory

    # Define file type categories
    categories = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma'],
        'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
        'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go', '.rs'],
        'executables': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm'],
    }

    stats = {
        'processed': 0,
        'moved': 0,
        'skipped': 0,
        'errors': []
    }

    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            stats['processed'] += 1

            # Get file extension
            _, ext = os.path.splitext(filename)
            ext = ext.lower()

            # Determine category
            category = 'others'
            for cat, extensions in categories.items():
                if ext in extensions:
                    category = cat
                    break

            # Build destination path
            dest_dir = os.path.join(destination_base, category)

            # Add date folders if requested
            if create_date_folders:
                try:
                    mod_time = os.path.getmtime(file_path)
                    date_obj = datetime.fromtimestamp(mod_time)
                    year_month = date_obj.strftime("%Y/%m")
                    dest_dir = os.path.join(dest_dir, year_month)
                except OSError:
                    pass  # If we can't get modification time, skip date folders

            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)

            # Move file
            dest_path = os.path.join(dest_dir, filename)
            try:
                # Handle duplicates
                counter = 1
                original_dest_path = dest_path
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(original_dest_path)
                    dest_path = f"{name}_{counter}{ext}"
                    counter += 1

                shutil.move(file_path, dest_path)
                stats['moved'] += 1
            except Exception as e:
                stats['errors'].append(f"Erro ao mover {filename}: {str(e)}")
                stats['skipped'] += 1

        # Generate report
        result = []
        result.append(f"📁 ORGANIZAÇÃO DE ARQUIVOS POR TIPO")
        result.append(f"Diretório fonte: {directory}")
        result.append(f"Diretório destino: {destination_base}")
        result.append(f"Pastas por data: {'Sim' if create_date_folders else 'Não'}")
        result.append("")
        result.append("📊 ESTATÍSTICAS:")
        result.append(f"  Arquivos processados: {stats['processed']}")
        result.append(f"  Arquivos movidos: {stats['moved']}")
        result.append(f"  Arquivos pulados: {stats['skipped']}")

        if stats['errors']:
            result.append(f"  Erros: {len(stats['errors'])}")
            result.append("\n❌ ERROS:")
            for error in stats['errors'][:5]:
                result.append(f"  • {error}")

        if stats['moved'] > 0:
            result.append(f"\n✅ Organização concluída! {stats['moved']} arquivos foram organizados em categorias.")
        else:
            result.append("\nℹ️  Nenhum arquivo foi movido (pode já estar organizado ou nenhum arquivo encontrado).")

        return "\n".join(result)

    except Exception as e:
        return f"Erro durante organização de arquivos: {str(e)}"


def calculate_directory_size(directory: str) -> str:
    """Calcula o tamanho total de um diretório e seus subdiretórios.

    Args:
        directory: Diretório para calcular o tamanho

    Returns:
        Tamanho formatado em unidades apropriadas
    """
    if not os.path.exists(directory):
        return f"Diretório não encontrado: {directory}"

    total_size = 0
    file_count = 0
    dir_count = 0

    try:
        for root, dirs, files in os.walk(directory):
            dir_count += len(dirs)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                except (OSError, IOError):
                    pass  # Skip files we can't access

        # Format size
        if total_size < 1024:
            size_str = f"{total_size} bytes"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        elif total_size < 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"

        result = []
        result.append(f"📊 TAMANHO DO DIRETÓRIO: {directory}")
        result.append(f"Tamanho total: {size_str}")
        result.append(f"Arquivos: {file_count:,}")
        result.append(f"Diretórios: {dir_count:,}")

        return "\n".join(result)

    except Exception as e:
        return f"Erro ao calcular tamanho do diretório: {str(e)}"


def find_duplicates(directory: str, method: str = "hash",
                   min_size: int = 1024) -> str:
    """Encontra arquivos duplicados em um diretório.

    Args:
        directory: Diretório onde procurar duplicados
        method: Método de comparação ('hash', 'size', 'name')
        min_size: Tamanho mínimo de arquivo para considerar (em bytes)

    Returns:
        Lista de grupos de arquivos duplicados
    """
    if not os.path.exists(directory):
        return f"Diretório não encontrado: {directory}"

    try:
        if method == "hash":
            # Group by file hash
            hash_map = {}
            files_processed = 0

            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size < min_size:
                            continue

                        # Calculate hash
                        hash_md5 = hashlib.md5()
                        with open(file_path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hash_md5.update(chunk)
                        file_hash = hash_md5.hexdigest()

                        if file_hash not in hash_map:
                            hash_map[file_hash] = []
                        hash_map[file_hash].append({
                            'path': file_path,
                            'size': file_size,
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        })
                        files_processed += 1

                    except (OSError, IOError, ValueError):
                        continue  # Skip files we can't read

            # Filter to only duplicates
            duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

            # Format output
            result = []
            result.append(f"🔍 DETECÇÃO DE ARQUIVOS DUPLICADOS")
            result.append(f"Diretório: {directory}")
            result.append(f"Método: Hash MD5")
            result.append(f"Tamanho mínimo: {min_size} bytes")
            result.append(f"Arquivos processados: {files_processed}")
            result.append("")

            if duplicates:
                result.append(f"📋 ENCONTRADOS {len(duplicates)} GRUPOS DE ARQUIVOS DUPLICADOS:")
                result.append("")

                total_wasted = 0
                for i, (file_hash, files) in enumerate(list(duplicates.items())[:10], 1):  # Show first 10
                    total_size = sum(f['size'] for f in files)
                    wasted = total_size - max(f['size'] for f in files)  # Space wasted (keeping largest)
                    total_wasted += wasted

                    result.append(f"Grupo {i} (Hash: {file_hash[:8]}...):")
                    result.append(f"  {len(files)} arquivos, {total_size:,} bytes total")
                    result.append(f"  Espaço recuperável: {wasted:,} bytes")
                    for j, file_info in enumerate(files[:3], 1):  # Show first 3 files
                        mod_time = datetime.fromisoformat(file_info['modified']).strftime("%m/%d %Y")
                        result.append(f"    {j}. {os.path.basename(file_info['path'])} "
                                    f"[{file_info['size']:,} bytes] [{mod_time}]")
                        if len(file_info['path']) > 50:
                            result.append(f"        {file_info['path']}")
                    if len(files) > 3:
                        result.append(f"    ... e mais {len(files) - 3} arquivos")
                    result.append("")

                if len(duplicates) > 10:
                    result.append(f"... e mais {len(duplicates) - 10} grupos")

                # Calculate total space wasted
                if total_wasted > 0:
                    if total_wasted < 1024:
                        wasted_str = f"{total_wasted} bytes"
                    elif total_wasted < 1024 * 1024:
                        wasted_str = f"{total_wasted / 1024:.1f} KB"
                    else:
                        wasted_str = f"{total_wasted / (1024 * 1024):.1f} MB"
                    result.append(f"💾 ESPAÇO TOTAL RECUPERÁVEL: {wasted_str}")

            else:
                result.append("✅ Nenhum arquivo duplicado encontrado com os critérios especificados.")

            return "\n".join(result)

        else:
            return f"Método '{method}' não implementado. Métodos disponíveis: 'hash'"

    except Exception as e:
        return f"Erro durante detecção de duplicados: {str(e)}"


# Register all tools
def register(api):
    """Registra todas as ferramentas de operações avançadas de arquivos."""
    api.register_tool(
        name="batch_rename_files",
        func=batch_rename_files,
        description="Renomeia múltiplos arquivos baseado em padrão com suporte a wildcards e visualização prévia.",
        parameters={
            "directory": {"type": "string", "description": "Diretório onde procurar arquivos"},
            "pattern": {"type": "string", "description": "Padrão a ser substituído (use * para wildcard)"},
            "replacement": {"type": "string", "description": "Texto de substituição"},
            "recursive": {"type": "boolean", "description": "Buscar em subdiretórios (padrão: false)"},
            "preview": {"type": "boolean", "description": "Apenas mostrar o que seria feito (padrão: true)"},
        },
        required=["directory", "pattern", "replacement"],
    )

    api.register_tool(
        name="sync_directories",
        func=sync_directories,
        description="Sincroniza dois diretórios nos modos mirror, backup ou sync.",
        parameters={
            "source": {"type": "string", "description": "Diretório de origem"},
            "destination": {"type": "string", "description": "Diretório de destino"},
            "mode": {"type": "string", "description": "Modo de sincronização: mirror, backup, sync (padrão: mirror)"},
            "exclude_patterns": {"type": "array", "items": {"type": "string"}, "description": "Padrões de arquivos para excluir"},
        },
        required=["source", "destination"],
    )

    api.register_tool(
        name="find_files_advanced",
        func=find_files_advanced,
        description="Busca avançada de arquivos com múltiplos critérios (nome, conteúdo, tamanho, data, tipo).",
        parameters={
            "directory": {"type": "string", "description": "Diretório onde buscar"},
            "name_pattern": {"type": "string", "description": "Padrão de nome do arquivo (ex: *.txt)"},
            "content_pattern": {"type": "string", "description": "Padrão de conteúdo dentro do arquivo"},
            "file_type": {"type": "string", "description": "Tipo de arquivo baseado na extensão (ex: pdf, jpg)"},
            "size_min": {"type": "integer", "description": "Tamanho mínimo em bytes"},
            "size_max": {"type": "integer", "description": "Tamanho máximo em bytes"},
            "date_after": {"type": "string", "description": "Data após a qual os arquivos devem ser (formato: YYYY-MM-DD)"},
            "date_before": {"type": "string", "description": "Data antes da qual os arquivos devem ser (formato: YYYY-MM-DD)"},
            "contain_text": {"type": "string", "description": "Texto que deve estar contido no arquivo"},
            "regex_search": {"type": "boolean", "description": "Usar expressão regular para busca de conteúdo"},
            "limit": {"type": "integer", "description": "Número máximo de resultados (padrão: 100)"},
        },
        required=["directory"],
    )

    api.register_tool(
        name="organize_files_by_type",
        func=organize_files_by_type,
        description="Organiza arquivos em subpastas baseado em seu tipo/extensão (imagens, documentos, código, etc.).",
        parameters={
            "directory": {"type": "string", "description": "Diretório com os arquivos a organizar"},
            "destination_base": {"type": "string", "description": "Diretório base onde organizar (opcional)"},
            "create_date_folders": {"type": "boolean", "description": "Criar subpastas por ano/mês (padrão: false)"},
        },
        required=["directory"],
    )

    api.register_tool(
        name="calculate_directory_size",
        func=calculate_directory_size,
        description="Calcula o tamanho total de um diretório e seus subdiretórios.",
        parameters={
            "directory": {"type": "string", "description": "Diretório para calcular o tamanho"},
        },
        required=["directory"],
    )

    api.register_tool(
        name="find_duplicates",
        func=find_duplicates,
        description="Encontra arquivos duplicados em um diretório usando hash MD5 para comparação precisa.",
        parameters={
            "directory": {"type": "string", "description": "Diretório onde procurar duplicados"},
            "method": {"type": "string", "description": "Método de comparação: hash, size, name (padrão: hash)"},
            "min_size": {"type": "integer", "description": "Tamanho mínimo de arquivo para considerar em bytes (padrão: 1024)"},
        },
        required=["directory"],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Operações avançadas de arquivos e diretórios com busca, organização, sincronização e detecção de duplicados",
        "tools": [
            "batch_rename_files", "sync_directories", "find_files_advanced",
            "organize_files_by_type", "calculate_directory_size", "find_duplicates"
        ],
    }