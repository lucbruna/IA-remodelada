"""
plugin_agendamento.py
=====================
Agendamento de tarefas, lembretes, calendario, temporizadores e alarmes
baseados em SQLite com verificacao sob demanda (sem thread background).
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta

__version__ = "1.0.0"
PLUGIN_NAME = "Agendamento e Lembretes"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "agendamentos.db")


def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            recorrencia TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def register(api):
    _init_db()

    def agendar(tipo: str, descricao: str, data_hora: str, recorrencia: str = "") -> str:
        """Agenda um lembrete ou evento. data_hora: 'YYYY-MM-DD HH:MM'. recorrencia: 'diario', 'semanal', 'mensal' ou vazio."""
        try:
            datetime.strptime(data_hora, "%Y-%m-%d %H:%M")
        except ValueError:
            return "Formato de data invalido. Use YYYY-MM-DD HH:MM."
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO agendamentos (tipo, descricao, data_hora, recorrencia) VALUES (?, ?, ?, ?)",
                     (tipo, descricao, data_hora, recorrencia))
        conn.commit()
        aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return f"Agendamento #{aid} criado: [{tipo}] {descricao} em {data_hora}" + (f" ({recorrencia})" if recorrencia else "")

    def listar_agendamentos(ativos: bool = True, tipo: str = "") -> str:
        """Lista agendamentos. Filtra por tipo (opcional) e ativos."""
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT id, tipo, descricao, data_hora, recorrencia, ativo FROM agendamentos WHERE 1=1"
        params = []
        if ativos:
            query += " AND ativo = 1"
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)
        query += " ORDER BY data_hora ASC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        if not rows:
            return "Nenhum agendamento encontrado."
        lines = [f"Total: {len(rows)} agendamento(s):", ""]
        for r in rows:
            status = "ATIVO" if r[5] else "INATIVO"
            rec = f" ({r[4]})" if r[4] else ""
            lines.append(f"  #{r[0]} [{r[1]}] {r[2]} - {r[3]}{rec} [{status}]")
        return "\n".join(lines)

    def verificar_lembretes() -> str:
        """Verifica lembretes vencidos (ate 1h atras) e ainda ativos."""
        conn = sqlite3.connect(DB_PATH)
        limite = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        rows = conn.execute(
            "SELECT id, tipo, descricao, data_hora, recorrencia FROM agendamentos WHERE ativo = 1 AND data_hora <= ? ORDER BY data_hora",
            (datetime.now().strftime("%Y-%m-%d %H:%M"),)
        ).fetchall()
        resultados = []
        for r in rows:
            resultados.append(f"  #{r[0]} [{r[1]}] {r[2]} - agendado para {r[3]}")
            if r[4]:
                # recalcula proxima ocorrencia
                base = datetime.strptime(r[3], "%Y-%m-%d %H:%M")
                if r[4] == "diario":
                    nova = base + timedelta(days=1)
                elif r[4] == "semanal":
                    nova = base + timedelta(weeks=1)
                elif r[4] == "mensal":
                    nova = base + timedelta(days=30)
                else:
                    nova = None
                if nova:
                    conn.execute("UPDATE agendamentos SET data_hora = ? WHERE id = ?",
                                 (nova.strftime("%Y-%m-%d %H:%M"), r[0]))
                    resultados.append(f"    -> Proxima ocorrencia: {nova.strftime('%Y-%m-%d %H:%M')}")
            else:
                conn.execute("UPDATE agendamentos SET ativo = 0 WHERE id = ?", (r[0],))
        conn.commit()
        conn.close()
        if not resultados:
            return "Nenhum lembrete pendente."
        return f"{len(rows)} lembrete(s) pendente(s):\n" + "\n".join(resultados)

    def cancelar_agendamento(id_agendamento: int) -> str:
        """Cancela/desativa um agendamento pelo ID."""
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("UPDATE agendamentos SET ativo = 0 WHERE id = ? AND ativo = 1", (id_agendamento,))
        conn.commit()
        affected = cur.rowcount
        conn.close()
        if affected:
            return f"Agendamento #{id_agendamento} cancelado."
        return f"Agendamento #{id_agendamento} nao encontrado ou ja inativo."

    def listar_tipos() -> str:
        """Lista tipos de agendamento disponiveis e suas descricoes."""
        return (
            "Tipos de agendamento disponiveis:\n"
            "  lembrete  - Lembrete unico (ex: 'Reuniao as 14h')\n"
            "  evento    - Evento unico (ex: 'Aniversario')\n"
            "  tarefa    - Tarefa com prazo\n"
            "  alarme    - Alarme para horario especifico\n"
            "  meta      - Meta com data limite\n\n"
            "Recorrencia (opcional): diario, semanal, mensal\n"
            "Data/hora: YYYY-MM-DD HH:MM"
        )

    api.register_tool("agendar", agendar,
        "Agenda lembrete/evento/tarefa. data_hora: YYYY-MM-DD HH:MM. recorrencia: diario/semanal/mensal.",
        {"tipo": {"type": "string", "description": "Tipo: lembrete, evento, tarefa, alarme, meta"}, "descricao": {"type": "string", "description": "Descricao"}, "data_hora": {"type": "string", "description": "Data e hora YYYY-MM-DD HH:MM"}, "recorrencia": {"type": "string", "description": "Recorrencia: diario, semanal, mensal (opcional)"}}, ["tipo", "descricao", "data_hora"])

    api.register_tool("listar_agendamentos", listar_agendamentos,
        "Lista agendamentos agendados. Opcional: filtrar por tipo.",
        {"tipo": {"type": "string", "description": "Filtrar por tipo (opcional)"}}, [])

    api.register_tool("verificar_lembretes", verificar_lembretes,
        "Verifica lembretes vencidos pendentes e atualiza recorrencias.",
        {}, [])

    api.register_tool("cancelar_agendamento", cancelar_agendamento,
        "Cancela/desativa agendamento pelo ID.",
        {"id_agendamento": {"type": "integer", "description": "ID do agendamento"}}, ["id_agendamento"])

    api.register_tool("listar_tipos_agendamento", listar_tipos,
        "Lista tipos de agendamento disponiveis e seus usos.",
        {}, [])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Agendamento de tarefas, lembretes, alarmes, calendario com recorrencia",
        "tools": ["agendar", "listar_agendamentos", "verificar_lembretes", "cancelar_agendamento", "listar_tipos_agendamento"],
    }
