"""
plugin_banco_dados.py
======================
Operacoes com bancos de dados: SQLite, CSV, Excel,
importacao/exportacao, migracao e consultas.
"""

import os
import json
import csv
import io
import sqlite3
import logging
from datetime import datetime

__version__ = "1.0.0"
PLUGIN_NAME = "Banco de Dados"


def register(api):
    def sql_executar(db_path: str, sql: str) -> str:
        """Executa SQL em banco SQLite. SELECT retorna tabela formatada."""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(sql)
            if sql.strip().upper().startswith(("SELECT", "PRAGMA", "EXPLAIN")):
                rows = cur.fetchall()
                if not rows:
                    conn.close()
                    return "Nenhum resultado."
                cols = [d[0] for d in cur.description]
                header = " | ".join(cols)
                sep = "-" * len(header)
                lines = [header, sep]
                for row in rows[:100]:
                    lines.append(" | ".join(str(row[c] or "") for c in cols))
                if len(rows) > 100:
                    lines.append(f"... e mais {len(rows) - 100} linhas.")
                conn.close()
                return "\n".join(lines)
            conn.commit()
            aff = cur.rowcount
            conn.close()
            return f"Comando executado. Linhas afetadas: {aff}"
        except Exception as e:
            return f"Erro SQL: {e}"

    def sql_tabelas(db_path: str) -> str:
        """Lista todas as tabelas de um banco SQLite."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            rows = cur.fetchall()
            conn.close()
            if not rows:
                return "Nenhuma tabela encontrada."
            return "Tabelas:\n" + "\n".join(f"  {r[0]}" for r in rows)
        except Exception as e:
            return f"Erro: {e}"

    def sql_esquema(db_path: str, tabela: str = "") -> str:
        """Mostra esquema de tabela(s) do banco SQLite."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            if tabela:
                cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
                row = cur.fetchone()
                conn.close()
                return f"Esquema de '{tabela}':\n{row[0]}" if row else f"Tabela '{tabela}' nao encontrada."
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND sql NOT NULL")
            rows = cur.fetchall()
            conn.close()
            return "\n\n".join(r[0] for r in rows) if rows else "Nenhuma tabela."
        except Exception as e:
            return f"Erro: {e}"

    def csv_para_sqlite(csv_path: str, db_path: str, tabela: str = "", delimiter: str = ",") -> str:
        """Importa arquivo CSV para tabela SQLite."""
        try:
            if not tabela:
                tabela = os.path.splitext(os.path.basename(csv_path))[0]
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader, None)
                if not headers:
                    return "CSV vazio."
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                col_defs = ", ".join(f'"{h}" TEXT' for h in headers)
                cur.execute(f'DROP TABLE IF EXISTS "{tabela}"')
                cur.execute(f'CREATE TABLE "{tabela}" ({col_defs})')
                placeholders = ", ".join("?" for _ in headers)
                count = 0
                for row in reader:
                    cur.execute(f'INSERT INTO "{tabela}" VALUES ({placeholders})', row)
                    count += 1
                conn.commit()
                conn.close()
                return f"CSV importado: {count} linhas em '{tabela}' ({len(headers)} colunas)."
        except Exception as e:
            return f"Erro ao importar CSV: {e}"

    def sqlite_para_csv(db_path: str, sql: str, csv_path: str = "", delimiter: str = ",") -> str:
        """Exporta resultado de consulta SQL para CSV."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            if not rows:
                conn.close()
                return "Nenhum dado para exportar."
            cols = [d[0] for d in cur.description]
            if not csv_path:
                csv_path = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=delimiter)
                writer.writerow(cols)
                writer.writerows(rows)
            conn.close()
            return f"Exportado: {csv_path} ({len(rows)} linhas, {len(cols)} colunas)."
        except Exception as e:
            return f"Erro ao exportar: {e}"

    def sqlite_migrar(db_path: str, sql_script: str) -> str:
        """Executa script SQL de migracao (multiplas statements)."""
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            statements = [s.strip() for s in sql_script.split(";") if s.strip()]
            count = 0
            for stmt in statements:
                try:
                    cur.execute(stmt)
                    count += 1
                except Exception as e:
                    conn.close()
                    return f"Erro na statement {count + 1}: {e}\nSQL: {stmt[:200]}"
            conn.commit()
            conn.close()
            return f"Migracao concluida: {count} statements executadas."
        except Exception as e:
            return f"Erro na migracao: {e}"

    def sqlite_info(db_path: str) -> str:
        """Informacoes do banco SQLite: tamanho, tabelas, indices."""
        try:
            if not os.path.exists(db_path):
                return "Arquivo nao encontrado."
            size = os.path.getsize(db_path)
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            num_tabelas = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
            num_indices = cur.fetchone()[0]
            conn.close()
            return (
                f"Banco: {os.path.basename(db_path)}\n"
                f"Tamanho: {size:,} bytes ({size/1024:.1f} KB)\n"
                f"Tabelas: {num_tabelas}\n"
                f"Indices: {num_indices}"
            )
        except Exception as e:
            return f"Erro: {e}"

    def json_para_sqlite(json_path: str, db_path: str, tabela: str = "") -> str:
        """Importa arquivo JSON (lista de objetos) para SQLite."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            if not data:
                return "JSON vazio."
            if not tabela:
                tabela = os.path.splitext(os.path.basename(json_path))[0]
            headers = list(data[0].keys())
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            col_defs = ", ".join(f'"{h}" TEXT' for h in headers)
            cur.execute(f'DROP TABLE IF EXISTS "{tabela}"')
            cur.execute(f'CREATE TABLE "{tabela}" ({col_defs})')
            placeholders = ", ".join("?" for _ in headers)
            for item in data:
                row = [json.dumps(item.get(h), ensure_ascii=False) if not isinstance(item.get(h), str) else item.get(h) for h in headers]
                cur.execute(f'INSERT INTO "{tabela}" VALUES ({placeholders})', row)
            conn.commit()
            conn.close()
            return f"JSON importado: {len(data)} registros em '{tabela}'."
        except Exception as e:
            return f"Erro: {e}"

    api.register_tool("sql_executar", sql_executar,
        "Executa SQL em banco SQLite. SELECT retorna tabela formatada. INSERT/UPDATE/DELETE retorna linhas afetadas.",
        {"db_path": {"type": "string", "description": "Caminho do arquivo .db"}, "sql": {"type": "string", "description": "Comando SQL"}}, ["db_path", "sql"])

    api.register_tool("sql_tabelas", sql_tabelas,
        "Lista todas as tabelas de um banco SQLite.",
        {"db_path": {"type": "string", "description": "Caminho do arquivo .db"}}, ["db_path"])

    api.register_tool("sql_esquema", sql_esquema,
        "Mostra esquema de tabela(s) do banco SQLite.",
        {"db_path": {"type": "string", "description": "Caminho do arquivo .db"}, "tabela": {"type": "string", "description": "Nome da tabela (opcional)"}}, ["db_path"])

    api.register_tool("csv_para_sqlite", csv_para_sqlite,
        "Importa arquivo CSV para tabela SQLite. Cria tabela automaticamente.",
        {"csv_path": {"type": "string", "description": "Caminho do CSV"}, "db_path": {"type": "string", "description": "Caminho do .db"}, "tabela": {"type": "string", "description": "Nome da tabela (opcional)"}, "delimiter": {"type": "string", "description": "Delimitador do CSV (opcional, padrao ,)"}}, ["csv_path", "db_path"])

    api.register_tool("sqlite_para_csv", sqlite_para_csv,
        "Exporta resultado de consulta SQL para arquivo CSV.",
        {"db_path": {"type": "string", "description": "Caminho do .db"}, "sql": {"type": "string", "description": "Consulta SELECT"}, "csv_path": {"type": "string", "description": "Caminho de saida (opcional)"}, "delimiter": {"type": "string", "description": "Delimitador (opcional)"}}, ["db_path", "sql"])

    api.register_tool("sqlite_migrar", sqlite_migrar,
        "Executa script SQL de migracao (multiplas statements separadas por ;).",
        {"db_path": {"type": "string", "description": "Caminho do .db"}, "sql_script": {"type": "string", "description": "Script SQL completo"}}, ["db_path", "sql_script"])

    api.register_tool("sqlite_info", sqlite_info,
        "Informacoes do banco SQLite: tamanho, numero de tabelas, indices.",
        {"db_path": {"type": "string", "description": "Caminho do .db"}}, ["db_path"])

    api.register_tool("json_para_sqlite", json_para_sqlite,
        "Importa arquivo JSON (lista de objetos) para tabela SQLite.",
        {"json_path": {"type": "string", "description": "Caminho do JSON"}, "db_path": {"type": "string", "description": "Caminho do .db"}, "tabela": {"type": "string", "description": "Nome da tabela (opcional)"}}, ["json_path", "db_path"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Operacoes com bancos de dados: SQLite, CSV, Excel, JSON, migracoes",
        "tools": ["sql_executar", "sql_tabelas", "sql_esquema", "csv_para_sqlite", "sqlite_para_csv", "sqlite_migrar", "sqlite_info", "json_para_sqlite"],
    }
