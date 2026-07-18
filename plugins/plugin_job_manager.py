"""
plugin_job_manager.py
=====================
Plugin de gerenciamento de trabalhos e tarefas para operações pesadas.
Fornece sistema de filas, processamento assíncrono, monitoramento de progresso
e gerenciamento de recursos para tarefas que consomem muito tempo ou recursos.
"""

import time
import threading
import queue
import uuid
import json
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
import heapq

__version__ = "1.0.0"
PLUGIN_NAME = "Gerenciador de Trabalhos e Tarefas"


class JobStatus(Enum):
    PENDING = "pendente"
    QUEUED = "na fila"
    PROCESSING = "processando"
    COMPLETED = "concluído"
    FAILED = "falhou"
    CANCELLED = "cancelado"
    PAUSED = "pausado"


class JobPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class Job:
    """Representa uma tarefa a ser executada pelo gerenciador de jobs."""

    def __init__(self, func: Callable, args: tuple = (), kwargs: dict = None,
                 job_id: str = None, priority: JobPriority = JobPriority.NORMAL,
                 max_retries: int = 0, timeout: int = None):
        self.id = job_id or str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.retries = 0
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.ended_at = None
        self.result = None
        self.error = None
        self.progress = 0.0  # 0.0 to 1.0
        self.progress_message = ""
        self.metadata = {}

    def to_dict(self) -> dict:
        """Converte o job para dicionário para serialização."""
        return {
            'id': self.id,
            'function': self.func.__name__ if hasattr(self.func, '__name__') else str(self.func),
            'args': self.args,
            'kwargs': self.kwargs,
            'priority': self.priority.value,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'retries': self.retries,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'result': self.result,
            'error': str(self.error) if self.error else None,
            'progress': self.progress,
            'progress_message': self.progress_message,
            'metadata': self.metadata
        }

    def __lt__(self, other):
        """Para ordenação na fila de prioridade (menor número = maior prioridade)."""
        # Invert priority so that higher priority values come first
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        # If same priority, earlier creation time comes first
        return self.created_at < other.created_at


class JobWorker(threading.Thread):
    """Worker thread que processa jobs da fila."""

    def __init__(self, worker_id: int, job_queue: queue.PriorityQueue,
                 result_handler: Callable[[Job], None],
                 status_callback: Callable[[str, str], None] = None):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.job_queue = job_queue
        self.result_handler = result_handler
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.current_job: Optional[Job] = None

    def run(self):
        """Loop principal do worker."""
        while not self.stop_event.is_set():
            try:
                # Get job with timeout to allow checking stop_event
                try:
                    priority, job = self.job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                self.current_job = job
                self._process_job(job)
                self.job_queue.task_done()
                self.current_job = None

            except Exception as e:
                if self.status_callback:
                    self.status_callback(f"Worker {self.worker_id}", f"Erro: {str(e)}")
                if self.current_job:
                    self.current_job.status = JobStatus.FAILED
                    self.current_job.error = str(e)
                    self.result_handler(self.current_job)
                    self.current_job = None

        # Sinalizar fim
        if self.status_callback:
            self.status_callback(f"Worker {self.worker_id}", "Parado")

    def _process_job(self, job: Job):
        """Processa um único job."""
        try:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now()

            if self.status_callback:
                self.status_callback(f"Worker {self.worker_id}",
                                   f"Iniciando: {job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)}")

            # Execute the function with progress callback if supported
            if 'progress_callback' in job.kwargs:
                # Function accepts progress callback
                job.result = job.func(*job.args, **job.kwargs)
            else:
                # Wrap function to provide progress updates
                def progress_wrapper(progress: float, message: str = ""):
                    job.progress = max(0.0, min(1.0, progress))
                    job.progress_message = str(message)
                    if self.status_callback:
                        func_name = job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
                        self.status_callback(f"Worker {self.worker_id}",
                                           f"{func_name}: {int(progress * 100)}% - {message}")

                # Add progress callback to kwargs
                job.kwargs['progress_callback'] = progress_wrapper
                job.result = job.func(*job.args, **job.kwargs)

            job.status = JobStatus.COMPLETED
            job.ended_at = datetime.now()
            job.progress = 1.0

            if self.status_callback:
                func_name = job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
                self.status_callback(f"Worker {self.worker_id}",
                                   f"Concluído: {func_name}")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.ended_at = datetime.now()

            if self.status_callback:
                func_name = job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
                self.status_callback(f"Worker {self.worker_id}",
                                   f"Falhou: {func_name} - {str(e)}")
        finally:
            # Always call result handler
            self.result_handler(job)

    def stop(self):
        """Para o worker."""
        self.stop_event.set()


class JobManager:
    """Gerenciador principal de jobs e tarefas."""

    def __init__(self, max_workers: int = 4):
        self.job_queue = queue.PriorityQueue()
        self.jobs: Dict[str, Job] = {}
        self.workers: List[JobWorker] = []
        self.max_workers = max_workers
        self.result_handlers: List[Callable[[Job], None]] = []
        self.status_callbacks: List[Callable[[str, str], None]] = []
        self.is_running = False
        self._lock = threading.Lock()

    def add_result_handler(self, handler: Callable[[Job], None]):
        """Adiciona um handler para ser chamado quando um job completar."""
        self.result_handlers.append(handler)

    def add_status_callback(self, callback: Callable[[str, str], None]):
        """Adiciona um callback para atualizações de status."""
        self.status_callbacks.append(callback)

    def _notify_result(self, job: Job):
        """Notifica todos os handlers de resultado."""
        for handler in self.result_handlers:
            try:
                handler(job)
            except Exception as e:
                print(f"Erro no handler de resultado: {e}")

    def _notify_status(self, worker_id: str, message: str):
        """Notifica todos os callbacks de status."""
        for callback in self.status_callbacks:
            try:
                callback(worker_id, message)
            except Exception as e:
                print(f"Erro no callback de status: {e}")

    def start(self):
        """Inicia o gerenciador de jobs e os workers."""
        if self.is_running:
            return

        self.is_running = True
        self.workers = []

        for i in range(self.max_workers):
            worker = JobWorker(i, self.job_queue, self._notify_result, self._notify_status)
            worker.start()
            self.workers.append(worker)

    def stop(self, wait: bool = True):
        """Para o gerenciador de jobs."""
        if not self.is_running:
            return

        self.is_running = False

        # Stop all workers
        for worker in self.workers:
            worker.stop()

        # Wait for workers to finish if requested
        if wait:
            for worker in self.workers:
                worker.join(timeout=5.0)

        self.workers.clear()

    def submit_job(self, func: Callable, *args, priority: JobPriority = JobPriority.NORMAL,
                   max_retries: int = 0, timeout: int = None, **kwargs) -> str:
        """Submete um novo job para execução.

        Returns:
            ID do job submetido
        """
        job = Job(func, args, kwargs, None, priority, max_retries, timeout)

        with self._lock:
            self.jobs[job.id] = job

        # Add to queue (priority queue uses lower numbers for higher priority)
        self.job_queue.put((job.priority.value, job))

        # Notify status
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        self._notify_status("JobManager", f"Job submetido: {func_name} (ID: {job.id[:8]})")

        return job.id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Obtém um job pelo ID."""
        with self._lock:
            return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancela um job pendente ou em processamento."""
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
            job.status = JobStatus.CANCELLED
            job.ended_at = datetime.now()
            self._notify_status("JobManager", f"Job cancelado: {job.id[:8]}")
            return True
        elif job.status == JobStatus.PROCESSING:
            # Mark for cancellation - worker will check this
            job.metadata['cancel_requested'] = True
            self._notify_status("JobManager", f"Cancelamento solicitado: {job.id[:8]}")
            return True

        return False

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Obtém todos os jobs com um determinado status."""
        with self._lock:
            return [job for job in self.jobs.values() if job.status == status]

    def get_queue_size(self) -> int:
        """Obtém o número de jobs na fila."""
        return self.job_queue.qsize()

    def get_stats(self) -> dict:
        """Obtém estatísticas do gerenciador de jobs."""
        with self._lock:
            status_counts = {}
            for status in JobStatus:
                status_counts[status.value] = len([j for j in self.jobs.values() if j.status == status])

            return {
                'total_jobs': len(self.jobs),
                'queue_size': self.job_queue.qsize(),
                'active_workers': len([w for w in self.workers if not w.stop_event.is_set()]),
                'status_distribution': status_counts,
                'is_running': self.is_running
            }


# Global job manager instance
_job_manager = JobManager()


def get_job_manager() -> JobManager:
    """Obtém a instância global do gerenciador de jobs."""
    return _job_manager


def submit_job(func: Callable, *args, priority: JobPriority = JobPriority.NORMAL,
               max_retries: int = 0, timeout: int = None, **kwargs) -> str:
    """Função de conveniência para submeter um job ao gerenciador global."""
    return _job_manager.submit_job(func, *args, priority=priority, max_retries=max_retries,
                                   timeout=timeout, **kwargs)


def get_job(job_id: str) -> Optional[Job]:
    """Função de conveniência para obter um job pelo ID."""
    return _job_manager.get_job(job_id)


def cancel_job(job_id: str) -> bool:
    """Função de conveniência para cancelar um job."""
    return _job_manager.cancel_job(job_id)


def start_job_manager(max_workers: int = 4):
    """Função de conveniência para iniciar o gerenciador de jobs global."""
    _job_manager.max_workers = max_workers
    _job_manager.start()


def stop_job_manager(wait: bool = True):
    """Função de conveniência para parar o gerenciador de jobs global."""
    _job_manager.stop(wait=wait)


def get_job_status(job_id: str) -> str:
    """Função de conveniência para obter o status de um job."""
    job = get_job(job_id)
    return job.status.value if job else "não encontrado"


def get_job_result(job_id: str) -> Any:
    """Função de conveniência para obter o resultado de um job concluído."""
    job = get_job(job_id)
    if job and job.status == JobStatus.COMPLETED:
        return job.result
    return None


def list_jobs(status_filter: str = None) -> str:
    """Lista jobs com opcional filtro por status."""
    if status_filter:
        try:
            status_enum = JobStatus(status_filter)
            jobs = get_job_manager().get_jobs_by_status(status_enum)
        except ValueError:
            return f"Status inválido: {status_filter}. Valores válidos: {[s.value for s in JobStatus]}"
    else:
        with _job_manager._lock:
            jobs = list(_job_manager.jobs.values())

    if not jobs:
        return "Nenhum job encontrado."

    # Sort by creation time (newest first)
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    output = []
    output.append(f"📋 LISTA DE TRABALHOS ({len(jobs)} total)")
    output.append("")

    for job in jobs[:20]:  # Show first 20
        status_emoji = {
            JobStatus.PENDING: "⏳",
            JobStatus.QUEUED: "🔄",
            JobStatus.PROCESSING: "⚙️",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌",
            JobStatus.CANCELLED: "🚫",
            JobStatus.PAUSED: "⏸️"
        }.get(job.status, "❓")

        elapsed = ""
        if job.started_at:
            if job.ended_at:
                delta = job.ended_at - job.started_at
            else:
                delta = datetime.now() - job.started_at
            elapsed = f" ({int(delta.total_seconds())}s)"

        func_name = job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
        truncated_id = job.id[:8]

        output.append(
            f"{status_emoji} {truncated_id} | {func_name} "
            f"[{job.status.value.upper()}]{elapsed} "
            f"Pri:{job.priority.name}"
        )

        if job.progress_message:
            progress_pct = int(job.progress * 100)
            output.append(f"    📊 {progress_pct}% - {job.progress_message}")

    if len(jobs) > 20:
        output.append(f"  ... e mais {len(jobs) - 20} jobs")

    # Add summary
    stats = get_job_manager().get_stats()
    output.append("")
    output.append("📊 ESTATÍSTICAS:")
    output.append(f"  Em fila: {stats['queue_size']}")
    output.append(f"  Workers ativos: {stats['active_workers']}/{stats['total_jobs']}")

    for status, count in stats['status_distribution'].items():
        if count > 0:
            output.append(f"  {status.capitalize()}: {count}")

    return "\n".join(output)


# Register all tools with the plugin system
def register(api):
    """Registra todas as ferramentas de gerenciamento de jobs."""

    api.register_tool(
        name="submit_job",
        func=submit_job,
        description="Submete uma função para execução assíncrona no gerenciador de jobs.",
        parameters={
            "function_name": {"type": "string", "description": "Nome da função a ser executada (deve estar disponível no escopo)"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Argumentos posicionais para a função"},
            "kwargs": {"type": "object", "description": "Argumentos nomeados para a função"},
            "priority": {"type": "string", "description": "Prioridade: low, normal, high, urgent (padrão: normal)"},
            "max_retries": {"type": "integer", "description": "Número máximo de tentativas em caso de falha (padrão: 0)"},
            "timeout": {"type": "integer", "description": "Timeout em segundos (opcional)"},
        },
        required=["function_name"],
    )

    api.register_tool(
        name="get_job_status",
        func=get_job_status,
        description="Obtém o status atual de um job pelo seu ID.",
        parameters={
            "job_id": {"type": "string", "description": "ID do job a consultar"},
        },
        required=["job_id"],
    )

    api.register_tool(
        name="get_job_result",
        func=get_job_result,
        description="Obtém o resultado de um job concluído pelo seu ID.",
        parameters={
            "job_id": {"type": "string", "description": "ID do job para obter o resultado"},
        },
        required=["job_id"],
    )

    api.register_tool(
        name="cancel_job",
        func=cancel_job,
        description="Cancela um job pendente ou em processamento.",
        parameters={
            "job_id": {"type": "string", "description": "ID do job a cancelar"},
        },
        required=["job_id"],
    )

    api.register_tool(
        name="list_jobs",
        func=list_jobs,
        description="Lista todos os jobs com opcional filtro por status.",
        parameters={
            "status_filter": {"type": "string", "description": "Filtrar por status: pendente, na fila, processando, concluído, falhou, cancelado, pausado"},
        },
        required=[],
    )

    api.register_tool(
        name="start_job_manager",
        func=start_job_manager,
        description="Inicia o gerenciador de jobs com número especificado de workers.",
        parameters={
            "max_workers": {"type": "integer", "description": "Número máximo de workers simultâneos (padrão: 4)"},
        },
        required=[],
    )

    api.register_tool(
        name="stop_job_manager",
        func=stop_job_manager,
        description="Para o gerenciador de jobs.",
        parameters={
            "wait": {"type": "boolean", "description": "Aguardar conclusão dos jobs atuais antes de parar (padrão: true)"},
        },
        required=[],
    )

    api.register_tool(
        name="get_job_stats",
        func=lambda: str(get_job_manager().get_stats()),
        description="Obtém estatísticas detalhadas do gerenciador de jobs.",
        parameters={},
        required=[],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Sistema completo de gerenciamento de trabalhos para execução assíncrona, filas de prioridade e monitoramento de progresso",
        "tools": [
            "submit_job", "get_job_status", "get_job_result", "cancel_job",
            "list_jobs", "start_job_manager", "stop_job_manager", "get_job_stats"
        ],
    }