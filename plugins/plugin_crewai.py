"""
plugin_crewai.py
================
Integracao com CrewAI — orquestracao de agentes multi-IA.

Requer: pip install crewai crewai-tools
"""

__version__ = "1.0.0"
PLUGIN_NAME = "CrewAI Integration"

import os
import json
import logging

logger = logging.getLogger(__name__)


def register(api):

    def crewai_status() -> str:
        try:
            import crewai
            return f"✅ CrewAI {crewai.__version__} disponivel"
        except ImportError:
            return "❌ CrewAI nao instalado. Rode: pip install crewai"

    def crewai_create_crew(name: str, agents_json: str, tasks_json: str, verbose: bool = True) -> str:
        try:
            from crewai import Agent, Task, Crew, Process

            agents_data = json.loads(agents_json)
            tasks_data = json.loads(tasks_json)

            agents = []
            for a in agents_data:
                agent = Agent(
                    role=a.get("role", "generalist"),
                    goal=a.get("goal", "Help the user"),
                    backstory=a.get("backstory", "You are a helpful assistant."),
                    verbose=verbose,
                    allow_delegation=a.get("allow_delegation", False),
                    tools=[],
                )
                agents.append(agent)

            tasks = []
            for t in tasks_data:
                agent_idx = t.get("agent_index", 0)
                if agent_idx >= len(agents):
                    agent_idx = 0
                task = Task(
                    description=t.get("description", ""),
                    expected_output=t.get("expected_output", "Complete task"),
                    agent=agents[agent_idx],
                )
                tasks.append(task)

            crew = Crew(
                name=name,
                agents=agents,
                tasks=tasks,
                verbose=verbose,
                process=Process.sequential,
            )

            result = crew.kickoff()

            return (
                f"✅ Crew '{name}' executado com sucesso!\n\n"
                f"**Resultado:**\n{result}"
            )
        except json.JSONDecodeError as e:
            return f"❌ JSON invalido: {e}"
        except Exception as e:
            return f"❌ Erro ao executar crew: {e}"

    def crewai_quick_task(crew_description: str, task_description: str) -> str:
        try:
            from crewai import Agent, Task, Crew, Process

            agent = Agent(
                role="Universal Assistant",
                goal=crew_description,
                backstory="You are a versatile assistant capable of handling any task.",
                verbose=True,
                allow_delegation=False,
                tools=[],
            )

            task = Task(
                description=task_description,
                expected_output="Complete and detailed response",
                agent=agent,
            )

            crew = Crew(
                name="QuickTask",
                agents=[agent],
                tasks=[task],
                verbose=True,
                process=Process.sequential,
            )

            result = crew.kickoff()
            return f"**Resultado:**\n{result}"
        except Exception as e:
            return f"❌ Erro: {e}"

    def crewai_multi_agent(agents_json: str, objective: str) -> str:
        try:
            from crewai import Agent, Task, Crew, Process

            agents_data = json.loads(agents_json)

            agents = []
            for a in agents_data:
                agent = Agent(
                    role=a.get("role", "specialist"),
                    goal=a.get("goal", f"Complete tasks related to {objective}"),
                    backstory=a.get("backstory", f"You are an expert in {a.get('role', 'your field')}."),
                    verbose=True,
                    allow_delegation=True,
                    tools=[],
                )
                agents.append(agent)

            task = Task(
                description=objective,
                expected_output="Comprehensive solution addressing all aspects of the objective",
                agent=agents[0] if agents else None,
            )

            crew = Crew(
                name="MultiAgent",
                agents=agents,
                tasks=[task],
                verbose=True,
                process=Process.hierarchical,
            )

            result = crew.kickoff()
            return f"**Resultado do Multi-Agent:**\n{result}"
        except json.JSONDecodeError as e:
            return f"❌ JSON invalido: {e}"
        except Exception as e:
            return f"❌ Erro: {e}"

    api.register_tool("crewai_status", crewai_status,
        "Verifica se CrewAI esta instalado.", {}, [])

    api.register_tool("crewai_create_crew", crewai_create_crew,
        "Cria e executa um crew com multiplos agentes e tarefas.",
        {"name": {"type": "string", "description": "Nome do crew"},
         "agents_json": {"type": "string", "description": "JSON array de agentes: [{role, goal, backstory}]"},
         "tasks_json": {"type": "string", "description": "JSON array de tarefas: [{description, expected_output, agent_index}]"},
         "verbose": {"type": "boolean", "description": "Modo verboso (opcional)"}}, ["name", "agents_json", "tasks_json"])

    api.register_tool("crewai_quick_task", crewai_quick_task,
        "Executa uma tarefa rapida com um agente unico.",
        {"crew_description": {"type": "string", "description": "Descricao do objetivo do agente"},
         "task_description": {"type": "string", "description": "Descricao da tarefa"}}, ["crew_description", "task_description"])

    api.register_tool("crewai_multi_agent", crewai_multi_agent,
        "Executa objetivo com equipe de agentes e delegacao hierarquica.",
        {"agents_json": {"type": "string", "description": "JSON array de agentes"},
         "objective": {"type": "string", "description": "Objetivo geral"}}, ["agents_json", "objective"])

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Orquestracao multi-agente via CrewAI: crews, delegacao, tarefas complexas.",
        "tools": ["crewai_status", "crewai_create_crew", "crewai_quick_task", "crewai_multi_agent"],
    }
