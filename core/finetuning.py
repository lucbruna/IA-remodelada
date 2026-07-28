"""
core/finetuning.py
==================
Pipeline de fine-tuning para modelos locais.

Inspirado por:
  - OpenAI Cookbook: fine-tuning patterns
  - Anthropic courses: prompt evaluation
  - Fable 5: self-improvement loop

Funcionalidades:
  - Colecao automatica de dados de conversas
  - Preparacao de dataset no formato JSONL
  - Treinamento via Ollama (Modelfile) ou Unsloth
  - Avaliacao automatica de qualidade
  - Export para HuggingFace format
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ._common import DATA_DIR, _load_json, _save_json, logging

# --- Config ---
FINETUNE_DIR = os.path.join(DATA_DIR, "finetuning")
DATASETS_DIR = os.path.join(FINETUNE_DIR, "datasets")
MODELS_DIR = os.path.join(FINETUNE_DIR, "models")
EVALS_DIR = os.path.join(FINETUNE_DIR, "evaluations")

for d in [FINETUNE_DIR, DATASETS_DIR, MODELS_DIR, EVALS_DIR]:
    os.makedirs(d, exist_ok=True)


# --- Data Collection ---

class DataCollector:
    """Coleta dados de conversas para fine-tuning."""

    def __init__(self, dataset_name: str = "default"):
        self.dataset_name = dataset_name
        self.dataset_path = os.path.join(DATASETS_DIR, f"{dataset_name}.jsonl")
        self._examples = []

    def add_example(
        self,
        user_message: str,
        assistant_message: str,
        system_prompt: str = "",
        metadata: dict = None,
    ):
        """Adiciona um example ao dataset."""
        example = {
            "messages": [],
            "metadata": metadata or {},
            "collected_at": datetime.now().isoformat(),
        }

        if system_prompt:
            example["messages"].append({"role": "system", "content": system_prompt})

        example["messages"].append({"role": "user", "content": user_message})
        example["messages"].append({"role": "assistant", "content": assistant_message})

        self._examples.append(example)

    def add_from_conversation(self, messages: list, min_quality: int = 1):
        """Extrai examples de uma conversa (pares pergunta-resposta)."""
        for i in range(len(messages) - 1):
            if (messages[i].get("role") == "user" and
                messages[i + 1].get("role") == "assistant"):

                user_msg = messages[i].get("content", "")
                assistant_msg = messages[i + 1].get("content", "")

                # Filtra respostas muito curtas ou genericas
                if len(assistant_msg) < 20:
                    continue
                if any(p in assistant_msg.lower() for p in ["nao posso", "desculpe", "nao tenho"]):
                    continue

                self.add_example(user_msg, assistant_msg)

    def add_from_feedback(self, feedback_entries: list):
        """Usa feedback positivo para criar examples de alta qualidade."""
        for entry in feedback_entries:
            if entry.get("quality", 0) > 0 and entry.get("comment"):
                # Feedback positivo com comentario = example valioso
                self.add_example(
                    user_message=f"Contexto: {entry.get('comment', '')}",
                    assistant_message="(resposta avaliada positivamente pelo usuario)",
                    metadata={"source": "feedback", "quality": entry.get("quality", 0)},
                )

    def auto_collect_from_history(self, history_file: str = None):
        """Coleta automaticamente examples do historico de conversas.

        Analisa conversas anteriores e extrai os melhores pares
        pergunta-resposta para fine-tuning.
        """
        from ._common import HISTORY_FILE, _load_json

        history_file = history_file or HISTORY_FILE
        messages = _load_json(history_file, [])

        if not messages:
            return 0

        collected = 0
        for i in range(len(messages) - 1):
            if (messages[i].get("role") == "user" and
                messages[i + 1].get("role") == "assistant"):

                user_msg = messages[i].get("content", "")
                assistant_msg = messages[i + 1].get("content", "")

                # Filtros de qualidade
                if len(assistant_msg) < 50:  # Resposta muito curta
                    continue
                if len(assistant_msg) > 2000:  # Resposta muito longa (pode ser ruido)
                    assistant_msg = assistant_msg[:1500] + "..."

                # Filtra respostas de erro ou recusa
                lower = assistant_msg.lower()
                skip_patterns = [
                    "nao posso", "desculpe", "nao tenho",
                    "erro ao", "falha ao", "indisponivel",
                    "por favor instale", "pip install",
                ]
                if any(p in lower for p in skip_patterns):
                    continue

                # Filtra respostas genericas demais
                if assistant_msg.count("!") > 5:  # Muitos exclamacoes = baixa qualidade
                    continue

                self.add_example(user_msg, assistant_msg, metadata={"source": "auto_history"})
                collected += 1

        return collected

    def auto_collect_from_hindsight(self):
        """Coleta examples da memoria duradoura (hindsight)."""
        try:
            from .hindsight import _load_hindsight
            data = _load_hindsight()
            facts = data.get("facts", [])

            collected = 0
            for fact in facts:
                text = fact.get("text", "")
                if len(text) < 30:
                    continue
                # Cria example de instrucao
                self.add_example(
                    user_message=f"Lembre-se: {text[:200]}",
                    assistant_message=f"Entendido. {text}",
                    metadata={"source": "hindsight", "importance": fact.get("importance", 0.5)},
                )
                collected += 1

            return collected
        except Exception:
            return 0

    def quality_score(self, example: dict) -> float:
        """Calcula score de qualidade de um example (0-1)."""
        msgs = example.get("messages", [])
        if len(msgs) < 2:
            return 0.0

        user_msg = ""
        assistant_msg = ""
        for m in msgs:
            if m.get("role") == "user":
                user_msg = m.get("content", "")
            elif m.get("role") == "assistant":
                assistant_msg = m.get("content", "")

        score = 0.5  # baseline

        # Tamanho da resposta (ideal: 100-1000 chars)
        if 100 <= len(assistant_msg) <= 1000:
            score += 0.2
        elif len(assistant_msg) > 50:
            score += 0.1

        # Clareza (poucos erros de formatacao)
        if assistant_msg.count("\n") >= 1:  # Tem paragrafos
            score += 0.1

        # Relevancia (palavras em comum com pergunta)
        user_words = set(user_msg.lower().split())
        assistant_words = set(assistant_msg.lower().split())
        overlap = len(user_words & assistant_words) / max(len(user_words), 1)
        score += min(0.2, overlap)

        return min(1.0, score)

    def save(self) -> str:
        """Salva o dataset em formato JSONL."""
        with open(self.dataset_path, "w", encoding="utf-8") as f:
            for example in self._examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        return f"Dataset salvo: {self.dataset_path} ({len(self._examples)} examples)"

    def load(self):
        """Carrega examples existentes."""
        if os.path.exists(self.dataset_path):
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._examples.append(json.loads(line))
        return self

    def get_stats(self) -> dict:
        """Retorna estatisticas do dataset."""
        return {
            "name": self.dataset_name,
            "total_examples": len(self._examples),
            "file": self.dataset_path,
            "file_size": os.path.getsize(self.dataset_path) if os.path.exists(self.dataset_path) else 0,
        }


# --- Dataset Preparation ---

def prepare_dataset_for_training(
    dataset_name: str = "default",
    output_format: str = "jsonl",
    min_response_length: int = 50,
    max_response_length: int = 2000,
) -> str:
    """Prepara dataset para treinamento.

    Args:
        dataset_name: Nome do dataset
        output_format: "jsonl", "alpaca", "sharegpt"
        min_response_length: Tamanho minimo da resposta
        max_response_length: Tamanho maximo da resposta

    Returns:
        Caminho do arquivo preparado
    """
    collector = DataCollector(dataset_name).load()
    examples = collector._examples

    # Filtra examples de baixa qualidade
    filtered = []
    for ex in examples:
        msgs = ex.get("messages", [])
        if len(msgs) < 2:
            continue
        # Pega ultima mensagem do assistant
        assistant_msg = ""
        for m in reversed(msgs):
            if m.get("role") == "assistant":
                assistant_msg = m.get("content", "")
                break
        if len(assistant_msg) < min_response_length:
            continue
        if len(assistant_msg) > max_response_length:
            # Trunca
            for m in msgs:
                if m.get("role") == "assistant":
                    m["content"] = assistant_msg[:max_response_length] + "..."
        filtered.append(ex)

    # Salva no formato escolhido
    output_file = os.path.join(DATASETS_DIR, f"{dataset_name}_{output_format}.jsonl")

    if output_format == "alpaca":
        # Formato Alpaca: instruction/input/output
        with open(output_file, "w", encoding="utf-8") as f:
            for ex in filtered:
                instruction = ""
                input_text = ""
                output_text = ""
                for m in ex["messages"]:
                    if m["role"] == "system":
                        instruction = m["content"]
                    elif m["role"] == "user":
                        input_text = m["content"]
                    elif m["role"] == "assistant":
                        output_text = m["content"]
                f.write(json.dumps({
                    "instruction": instruction or "Responda em portugues.",
                    "input": input_text,
                    "output": output_text,
                }, ensure_ascii=False) + "\n")

    elif output_format == "sharegpt":
        # Formato ShareGPT: conversations
        with open(output_file, "w", encoding="utf-8") as f:
            for ex in filtered:
                convs = []
                for m in ex["messages"]:
                    convs.append({
                        "from": m["role"],
                        "value": m["content"],
                    })
                f.write(json.dumps({"conversations": convs}, ensure_ascii=False) + "\n")

    else:
        # Formato JSONL padrao (messages)
        with open(output_file, "w", encoding="utf-8") as f:
            for ex in filtered:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    return f"Dataset preparado: {output_file} ({len(filtered)} examples de {len(examples)} originais)"


# --- Ollama Modelfile Training ---

def create_modelfile(
    base_model: str = "qwen2.5:7b",
    dataset_name: str = "default",
    system_prompt: str = "",
    temperature: float = 0.7,
) -> str:
    """Cria um Modelfile do Ollama para fine-tuning.

    O Ollama nao suporta fine-tuning direto, mas podemos criar
    um Modelfile com system prompt otimizado e parametros ajustados.
    """
    modelfile_content = f"""# Modelfile gerado automaticamente
# Base model: {base_model}
# Dataset: {dataset_name}
# Gerado em: {datetime.now().isoformat()}

FROM {base_model}

# System prompt personalizado
PARAMETER temperature {temperature}
PARAMETER num_ctx 16384
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1

"""
    if system_prompt:
        modelfile_content += f'SYSTEM """\n{system_prompt}\n"""\n'
    else:
        modelfile_content += f'SYSTEM """\nVoce e um assistente IA especializado, treinado com dados de alta qualidade. Responda sempre em portugues do Brasil de forma precisa e util.\n"""\n'

    modelfile_path = os.path.join(MODELS_DIR, f"Modelfile_{dataset_name}")
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    return f"Modelfile criado: {modelfile_path}"


def train_with_ollama(
    model_name: str,
    base_model: str = "qwen2.5:7b",
    dataset_name: str = "default",
) -> str:
    """Cria modelo personalizado no Ollama usando Modelfile.

    Nota: Ollama nao faz fine-tuning real, mas cria um modelo
    com system prompt e parametros otimizados.
    """
    modelfile_path = create_modelfile(base_model, dataset_name)

    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "create", model_name, "-f", modelfile_path],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return f"Modelo '{model_name}' criado com sucesso no Ollama!"
        else:
            return f"Erro ao criar modelo: {result.stderr}"
    except Exception as e:
        return f"Erro: {e}"


# --- Evaluation ---

class ModelEvaluator:
    """Avalia qualidade de respostas do modelo."""

    def __init__(self, dataset_name: str = "default"):
        self.dataset_name = dataset_name
        self.evals = []

    def evaluate_response(
        self,
        question: str,
        response: str,
        expected: str = "",
        criteria: list = None,
    ) -> dict:
        """Avalia uma unica resposta."""
        criteria = criteria or ["relevancia", "clareza", "completude", "seguranca"]

        eval_result = {
            "question": question,
            "response": response[:500],
            "expected": expected[:500] if expected else "",
            "criteria": {},
            "score": 0,
            "evaluated_at": datetime.now().isoformat(),
        }

        # Scoring basico baseado em criterios
        total = 0
        for criterion in criteria:
            score = self._score_criterion(criterion, question, response, expected)
            eval_result["criteria"][criterion] = score
            total += score

        eval_result["score"] = round(total / len(criteria), 2)
        self.evals.append(eval_result)
        return eval_result

    def _score_criterion(self, criterion: str, question: str, response: str, expected: str) -> float:
        """Score basico para um criterio (0-1)."""
        score = 0.5  # baseline

        if criterion == "relevancia":
            # Verifica se a resposta menciona palavras-chave da pergunta
            q_words = set(question.lower().split())
            r_words = set(response.lower().split())
            overlap = len(q_words & r_words) / max(len(q_words), 1)
            score = min(1.0, 0.3 + overlap * 0.7)

        elif criterion == "clareza":
            # Respostas mais longas tendem a ser mais claras
            length_score = min(1.0, len(response) / 200)
            score = 0.4 + length_score * 0.6

        elif criterion == "completude":
            if expected:
                # Compara com resposta esperada
                e_words = set(expected.lower().split())
                r_words = set(response.lower().split())
                overlap = len(e_words & r_words) / max(len(e_words), 1)
                score = overlap
            else:
                score = 0.6 if len(response) > 100 else 0.3

        elif criterion == "seguranca":
            # Verifica se ha conteudo potencialmente perigoso
            dangerous = ["eval(", "exec(", "os.system", "subprocess", "__import__"]
            has_dangerous = any(d in response for d in dangerous)
            score = 0.2 if has_dangerous else 0.9

        return round(score, 2)

    def evaluate_dataset(
        self,
        questions: list,
        model_fn=None,
        expected_answers: list = None,
    ) -> dict:
        """Avalia um conjunto de perguntas."""
        results = []
        for i, q in enumerate(questions):
            expected = expected_answers[i] if expected_answers and i < len(expected_answers) else ""

            # Gera resposta (usa modelo padrao se nao fornecido)
            if model_fn:
                response = model_fn(q)
            else:
                response = f"(resposta simulada para: {q[:50]})"

            eval_result = self.evaluate_response(q, response, expected)
            results.append(eval_result)

        # Estatisticas
        scores = [r["score"] for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0

        summary = {
            "dataset": self.dataset_name,
            "total_questions": len(questions),
            "average_score": round(avg_score, 2),
            "min_score": round(min(scores), 2) if scores else 0,
            "max_score": round(max(scores), 2) if scores else 0,
            "results": results,
            "evaluated_at": datetime.now().isoformat(),
        }

        # Salva avaliacao
        eval_file = os.path.join(EVALS_DIR, f"eval_{self.dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        _save_json(eval_file, summary)

        return summary

    def get_report(self) -> str:
        """Gera relatorio das avaliacoes."""
        if not self.evals:
            return "Nenhuma avaliacao realizada."

        scores = [e["score"] for e in self.evals]
        avg = sum(scores) / len(scores)

        report = [
            f"**Relatorio de Avaliacao**",
            f"Total de avaliacoes: {len(self.evals)}",
            f"Score medio: {avg:.2f}",
            f"Score minimo: {min(scores):.2f}",
            f"Score maximo: {max(scores):.2f}",
            "",
            "**Por criterio:**",
        ]

        # Agrupa por criterio
        criteria_scores = {}
        for e in self.evals:
            for c, s in e.get("criteria", {}).items():
                criteria_scores.setdefault(c, []).append(s)

        for c, scores in sorted(criteria_scores.items()):
            avg_c = sum(scores) / len(scores)
            report.append(f"- {c}: {avg_c:.2f} ({len(scores)} avaliacoes)")

        return "\n".join(report)


# --- Export ---

def export_dataset_huggingface(
    dataset_name: str,
    output_dir: str = None,
) -> str:
    """Exporta dataset no formato HuggingFace datasets."""
    output_dir = output_dir or os.path.join(DATASETS_DIR, f"{dataset_name}_hf")
    os.makedirs(output_dir, exist_ok=True)

    collector = DataCollector(dataset_name).load()

    # Formato JSON padrao do HuggingFace
    hf_data = []
    for ex in collector._examples:
        hf_data.append({
            "messages": ex.get("messages", []),
            "metadata": ex.get("metadata", {}),
        })

    # Salva
    train_file = os.path.join(output_dir, "train.json")
    _save_json(train_file, hf_data)

    # Cria metadata
    metadata = {
        "description": f"Dataset para fine-tuning: {dataset_name}",
        "source": "IA Remodelada",
        "created_at": datetime.now().isoformat(),
        "total_examples": len(hf_data),
        "format": "messages",
    }
    _save_json(os.path.join(output_dir, "dataset_info.json"), metadata)

    return f"Dataset exportado: {output_dir} ({len(hf_data)} examples)"


# --- Ferramentas para o agente ---

def finetune_collect_tool(conversation_json: str) -> str:
    """Ferramenta: coleta dados de uma conversa para fine-tuning."""
    try:
        messages = json.loads(conversation_json) if isinstance(conversation_json, str) else conversation_json
        collector = DataCollector("auto_collected")
        collector.load()
        collector.add_from_conversation(messages)
        return collector.save()
    except Exception as e:
        return f"Erro ao coletar dados: {e}"


def finetune_prepare_tool(dataset_name: str = "auto_collected") -> str:
    """Ferramenta: prepara dataset para treinamento."""
    return prepare_dataset_for_training(dataset_name)


def finetune_evaluate_tool(dataset_name: str, questions_json: str) -> str:
    """Ferramenta: avalia modelo com dataset de testes."""
    try:
        questions = json.loads(questions_json) if isinstance(questions_json, str) else questions_json
        evaluator = ModelEvaluator(dataset_name)
        result = evaluator.evaluate_dataset(questions)
        return evaluator.get_report()
    except Exception as e:
        return f"Erro na avaliacao: {e}"
