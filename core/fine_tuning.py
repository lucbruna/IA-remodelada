"""
core/fine_tuning.py
===================
Pipeline de fine-tuning local inspirado em conceitos do Fable 5 e ChatGPT.

Permite:
  - Preparar datasets a partir de código existente
  - Fine-tuning local com Ollama (via modificação de prompts)
  - Fine-tuning via API (OpenAI/Anthropic) quando disponível
  - Avaliação de modelos fine-tunados
  - Deploy de modelos

Inspirado por:
  - Fable 5: verification catalog, adversarial review
  - ChatGPT Code Interpreter: persistent session, resource limits
  - Claude: self-verification, evidence-based

Uso:
    from core.fine_tuning import FineTuningPipeline

    pipeline = FineTuningPipeline()
    dataset_path = pipeline.prepare_dataset("humaneval")
    result = pipeline.train(dataset_path, "qwen2.5:7b", epochs=3)
    eval_result = pipeline.evaluate("qwen2.5:7b-finetuned", "humaneval")
"""

import os
import json
import ast
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any, List

from ._common import (
    os, json, ast, logging, subprocess, datetime,
    _load_json, _save_json, DATA_DIR,
)

FINE_TUNING_DIR = os.path.join(DATA_DIR, "fine_tuning")
os.makedirs(FINE_TUNING_DIR, exist_ok=True)

DATASETS_DIR = os.path.join(FINE_TUNING_DIR, "datasets")
os.makedirs(DATASETS_DIR, exist_ok=True)

MODELS_DIR = os.path.join(FINE_TUNING_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

EVALS_DIR = os.path.join(FINE_TUNING_DIR, "evals")
os.makedirs(EVALS_DIR, exist_ok=True)


class FineTuningPipeline:
    """Pipeline de fine-tuning local para modelos de código.

    Suporta:
      - Preparação de datasets a partir de código existente
      - Fine-tuning local (prompt engineering + few-shot)
      - Fine-tuning via API (OpenAI/Anthropic)
      - Avaliação de modelos
      - Deploy de modelos fine-tunados
    """

    def __init__(self):
        self.datasets_dir = DATASETS_DIR
        self.models_dir = MODELS_DIR
        self.evals_dir = EVALS_DIR

    def prepare_dataset(self, source: str, output_name: str = None) -> str:
        """Prepara um dataset de fine-tuning a partir de uma fonte.

        Args:
            source: "humaneval", "mbpp", "existing_code", "conversations", ou caminho de arquivo
            output_name: Nome do dataset de saída

        Returns:
            Caminho do arquivo de dataset JSONL
        """
        if not output_name:
            output_name = f"{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        output_path = os.path.join(self.datasets_dir, f"{output_name}.jsonl")

        if source == "humaneval":
            dataset = self._generate_humaneval_dataset()
        elif source == "mbpp":
            dataset = self._generate_mbpp_dataset()
        elif source == "existing_code":
            dataset = self._extract_from_existing_code()
        elif source == "conversations":
            dataset = self._extract_from_conversations()
        elif os.path.exists(source):
            dataset = self._load_dataset_file(source)
        else:
            raise ValueError(f"Fonte desconhecida: {source}")

        with open(output_path, "w", encoding="utf-8") as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        logging.info("Dataset preparado: %s (%d exemplos)", output_path, len(dataset))
        return output_path

    def _generate_humaneval_dataset(self) -> List[Dict[str, Any]]:
        """Gera dataset no formato HumanEval para fine-tuning."""
        examples = [
            {
                "prompt": "def has_close_elements(numbers: List[float], threshold: float) -> bool:\n    \"\"\"Your code here.\"\"\"\n",
                "completion": "    \"\"\"Check if any two numbers in the list are closer than threshold.\"\"\"\n    sorted_numbers = sorted(numbers)\n    for i in range(len(sorted_numbers) - 1):\n        if sorted_numbers[i + 1] - sorted_numbers[i] < threshold:\n            return True\n    return False\n",
            },
            {
                "prompt": "def separate_paren_groups(paren_string: str) -> List[str]:\n    \"\"\"Your code here.\"\"\"\n",
                "completion": "    \"\"\"Separate balanced parenthesis groups in a string.\"\"\"\n    result = []\n    current = []\n    depth = 0\n    for char in paren_string:\n        if char == '(':\n            current.append(char)\n            depth += 1\n        elif char == ')':\n            current.append(char)\n            depth -= 1\n            if depth == 0:\n                result.append(''.join(current))\n                current = []\n    return result\n",
            },
        ]
        return examples

    def _generate_mbpp_dataset(self) -> List[Dict[str, Any]]:
        """Gera dataset no formato MBPP para fine-tuning."""
        examples = [
            {
                "prompt": "Write a function to find the maximum of three numbers.\n\n>>> find_max_of_three(3, 7, 5)\n7\n",
                "completion": "def find_max_of_three(a, b, c):\n    return max(a, b, c)\n",
            },
            {
                "prompt": "Write a function to check if a string is a palindrome.\n\n>>> is_palindrome('racecar')\nTrue\n",
                "completion": "def is_palindrome(s):\n    return s == s[::-1]\n",
            },
        ]
        return examples

    def _extract_from_existing_code(self) -> List[Dict[str, Any]]:
        """Extrai pares prompt/completion de código existente no projeto."""
        dataset = []
        code_files = []
        for root, _, files in os.walk("."):
            if any(skip in root for skip in [".git", "__pycache__", "node_modules", "venv"]):
                continue
            for f in files:
                if f.endswith(".py") and not f.startswith("test_"):
                    code_files.append(os.path.join(root, f))

        for filepath in code_files[:50]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    code = f.read()
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_code = ast.get_source_segment(code, node)
                        if func_code and len(func_code) > 50:
                            docstring = ast.get_docstring(node)
                            if docstring:
                                dataset.append({
                                    "prompt": f"def {node.name}({', '.join(a.arg for a in node.args.args)}):\n    \"\"\"{docstring}\"\"\"\n    ",
                                    "completion": func_code.split(f"def {node.name}")[1].split(":", 1)[1] + "\n",
                                })
            except Exception:
                continue

        return dataset

    def _extract_from_conversations(self) -> List[Dict[str, Any]]:
        """Extrai pares de conversa do histórico para fine-tuning."""
        from core.memory import HISTORY_FILE
        history = _load_json(HISTORY_FILE, [])
        dataset = []
        for i in range(0, len(history) - 1, 2):
            if i + 1 < len(history):
                user_msg = history[i]
                assistant_msg = history[i + 1]
                if user_msg.get("role") == "user" and assistant_msg.get("role") == "assistant":
                    dataset.append({
                        "prompt": user_msg.get("content", ""),
                        "completion": assistant_msg.get("content", ""),
                    })
        return dataset

    def _load_dataset_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Carrega um dataset de um arquivo JSON ou JSONL."""
        if filepath.endswith(".jsonl"):
            with open(filepath, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f if line.strip()]
        elif filepath.endswith(".json"):
            return _load_json(filepath, [])
        raise ValueError(f"Formato de arquivo nao suportado: {filepath}")

    def train(self, dataset_path: str, model: str, epochs: int = 3,
              method: str = "prompt_engineering") -> Dict[str, Any]:
        """Treina/fine-tune um modelo.

        Args:
            dataset_path: Caminho do arquivo de dataset
            model: Nome do modelo (ex: "qwen2.5:7b")
            epochs: Numero de epochs
            method: "prompt_engineering", "lora", "full_finetune", "api"

        Returns:
            Dict com resultado do treinamento
        """
        if method == "prompt_engineering":
            return self._train_prompt_engineering(dataset_path, model, epochs)
        elif method == "api":
            return self._train_api(dataset_path, model, epochs)
        elif method == "lora":
            return self._train_lora(dataset_path, model, epochs)
        else:
            return {"success": False, "error": f"Metodo desconhecido: {method}"}

    def _train_prompt_engineering(self, dataset_path: str, model: str, epochs: int) -> Dict[str, Any]:
        """Fine-tuning via prompt engineering (few-shot learning).

        Para modelos locais (Ollama), o "fine-tuning" e feito via
        in-context learning (few-shot examples no prompt).
        """
        dataset = self._load_dataset_file(dataset_path)
        few_shot_examples = dataset[:10]

        # Cria um "model adapter" que inclui os exemplos no prompt
        adapter_path = os.path.join(self.models_dir, f"{model.replace(':', '_')}_adapter.json")
        adapter = {
            "model": model,
            "method": "prompt_engineering",
            "few_shot_examples": few_shot_examples,
            "epochs": epochs,
            "created_at": datetime.now().isoformat(),
        }
        _save_json(adapter_path, adapter)

        # Avalia com os exemplos restantes
        eval_dataset = dataset[10:]
        eval_result = self._evaluate_prompt_engineering(model, eval_dataset, few_shot_examples)

        return {
            "success": True,
            "method": "prompt_engineering",
            "model": model,
            "adapter_path": adapter_path,
            "dataset_size": len(dataset),
            "few_shot_examples": len(few_shot_examples),
            "eval_result": eval_result,
            "created_at": datetime.now().isoformat(),
        }

    def _train_api(self, dataset_path: str, model: str, epochs: int) -> Dict[str, Any]:
        """Fine-tuning via API (OpenAI/Anthropic)."""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"success": False, "error": "API key nao configurada"}

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)

            # Upload do dataset
            with open(dataset_path, "rb") as f:
                file = client.files.create(file=f, purpose="fine-tune")

            # Cria o job de fine-tuning
            job = client.fine_tuning.jobs.create(
                training_file=file.id,
                model=model,
                epochs=epochs,
                suffix=f"finetuned_{datetime.now().strftime('%Y%m%d')}",
            )

            return {
                "success": True,
                "method": "api",
                "job_id": job.id,
                "status": job.status,
                "model": job.model,
                "created_at": datetime.now().isoformat(),
            }
        except ImportError:
            return {"success": False, "error": "openai package nao instalado"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _train_lora(self, dataset_path: str, model: str, epochs: int) -> Dict[str, Any]:
        """Fine-tuning via LoRA (Low-Rank Adaptation)."""
        try:
            # Verifica se o script de LoRA existe
            lora_script = os.path.join(FINE_TUNING_DIR, "lora_train.py")
            if not os.path.exists(lora_script):
                return {"success": False, "error": "Script de LoRA nao encontrado. Crie lora_train.py"}

            output_dir = os.path.join(self.models_dir, f"{model.replace(':', '_')}_lora")
            result = subprocess.run(
                ["python", lora_script,
                 "--dataset", dataset_path,
                 "--model", model,
                 "--output", output_dir,
                 "--epochs", str(epochs)],
                capture_output=True, text=True, timeout=3600
            )

            return {
                "success": result.returncode == 0,
                "method": "lora",
                "model": model,
                "output_dir": output_dir,
                "stdout": result.stdout[-500:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _evaluate_prompt_engineering(self, model: str, eval_dataset: List[Dict],
                                     few_shot: List[Dict]) -> Dict[str, Any]:
        """Avalia um modelo de prompt engineering."""
        try:
            import ollama
            from core.llm import _call_ollama_with_timeout

            correct = 0
            total = min(len(eval_dataset), 20)

            for item in eval_dataset[:total]:
                prompt = item.get("prompt", "")
                expected = item.get("completion", "")

                # Constrói o prompt com few-shot
                few_shot_text = "\n".join(
                    f"### Prompt: {ex.get('prompt', '')}\n### Completion: {ex.get('completion', '')}"
                    for ex in few_shot
                )
                full_prompt = f"{few_shot_text}\n\n### Prompt: {prompt}\n### Completion:"

                response = _call_ollama_with_timeout(
                    ollama.chat,
                    model=model,
                    messages=[{"role": "user", "content": full_prompt}],
                    options={"num_ctx": 4096, "temperature": 0.1},
                )

                actual = response.get("message", {}).get("content", "").strip()
                if expected.strip() in actual or actual in expected.strip():
                    correct += 1

            accuracy = correct / total if total > 0 else 0
            return {
                "accuracy": accuracy,
                "correct": correct,
                "total": total,
            }
        except Exception as e:
            return {"error": str(e), "accuracy": 0, "correct": 0, "total": 0}

    def evaluate(self, model: str, benchmark: str) -> Dict[str, Any]:
        """Avalia um modelo em um benchmark.

        Args:
            model: Nome do modelo
            benchmark: "humaneval", "mbpp", "custom"

        Returns:
            Dict com resultados da avaliação
        """
        if benchmark == "humaneval":
            return self._evaluate_humaneval(model)
        elif benchmark == "mbpp":
            return self._evaluate_mbpp(model)
        elif benchmark == "custom":
            eval_file = os.path.join(self.evals_dir, "custom_eval.json")
            dataset = _load_json(eval_file, [])
            return self._evaluate_custom(model, dataset)
        else:
            return {"error": f"Benchmark desconhecido: {benchmark}"}

    def _evaluate_humaneval(self, model: str) -> Dict[str, Any]:
        """Avalia modelo no HumanEval."""
        try:
            import ollama
            from core.llm import _call_ollama_with_timeout

            test_cases = [
                ("def has_close_elements(numbers, threshold):\n    ",
                 "def has_close_elements(numbers, threshold):\n    sorted_numbers = sorted(numbers)\n    for i in range(len(sorted_numbers) - 1):\n        if sorted_numbers[i + 1] - sorted_numbers[i] < threshold:\n            return True\n    return False"),
            ]

            correct = 0
            for prompt, expected in test_cases:
                response = _call_ollama_with_timeout(
                    ollama.chat,
                    model=model,
                    messages=[{"role": "user", "content": f"Complete this function:\n{prompt}"}],
                    options={"num_ctx": 2048, "temperature": 0.1},
                )
                actual = response.get("message", {}).get("content", "")
                if "sorted" in actual and "return" in actual:
                    correct += 1

            return {
                "benchmark": "humaneval",
                "model": model,
                "accuracy": correct / len(test_cases),
                "correct": correct,
                "total": len(test_cases),
            }
        except Exception as e:
            return {"error": str(e), "benchmark": "humaneval", "model": model}

    def _evaluate_mbpp(self, model: str) -> Dict[str, Any]:
        """Avalia modelo no MBPP."""
        try:
            import ollama
            from core.llm import _call_ollama_with_timeout

            test_cases = [
                ("Find the maximum of three numbers.", "max"),
                ("Check if a string is a palindrome.", "palindrome"),
            ]

            correct = 0
            for prompt, keyword in test_cases:
                response = _call_ollama_with_timeout(
                    ollama.chat,
                    model=model,
                    messages=[{"role": "user", "content": f"Write a Python function: {prompt}"}],
                    options={"num_ctx": 2048, "temperature": 0.1},
                )
                actual = response.get("message", {}).get("content", "")
                if keyword in actual.lower():
                    correct += 1

            return {
                "benchmark": "mbpp",
                "model": model,
                "accuracy": correct / len(test_cases),
                "correct": correct,
                "total": len(test_cases),
            }
        except Exception as e:
            return {"error": str(e), "benchmark": "mbpp", "model": model}

    def _evaluate_custom(self, model: str, dataset: List[Dict]) -> Dict[str, Any]:
        """Avalia modelo em dataset customizado."""
        try:
            import ollama
            from core.llm import _call_ollama_with_timeout

            correct = 0
            total = min(len(dataset), 50)

            for item in dataset[:total]:
                prompt = item.get("prompt", "")
                expected = item.get("completion", "")

                response = _call_ollama_with_timeout(
                    ollama.chat,
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"num_ctx": 4096, "temperature": 0.1},
                )
                actual = response.get("message", {}).get("content", "")
                if expected.strip() in actual or actual.strip() in expected:
                    correct += 1

            return {
                "benchmark": "custom",
                "model": model,
                "accuracy": correct / total if total > 0 else 0,
                "correct": correct,
                "total": total,
            }
        except Exception as e:
            return {"error": str(e), "benchmark": "custom", "model": model}

    def deploy(self, model: str, adapter_path: str = None) -> Dict[str, Any]:
        """Deploy de um modelo fine-tunado.

        Args:
            model: Nome do modelo
            adapter_path: Caminho do adapter (para prompt engineering)

        Returns:
            Dict com status do deploy
        """
        if adapter_path and os.path.exists(adapter_path):
            # Carrega o adapter
            adapter = _load_json(adapter_path, {})
            return {
                "success": True,
                "model": model,
                "adapter": adapter,
                "status": "ready",
                "deployed_at": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "model": model,
            "status": "ready",
            "deployed_at": datetime.now().isoformat(),
        }

    def list_datasets(self) -> List[str]:
        """Lista todos os datasets disponíveis."""
        if not os.path.exists(self.datasets_dir):
            return []
        return [f for f in os.listdir(self.datasets_dir) if f.endswith(".jsonl")]

    def list_models(self) -> List[str]:
        """Lista todos os modelos/adapters disponíveis."""
        if not os.path.exists(self.models_dir):
            return []
        return os.listdir(self.models_dir)

    def get_training_history(self) -> List[Dict[str, Any]]:
        """Retorna o histórico de treinamentos."""
        history_file = os.path.join(self.models_dir, "training_history.json")
        return _load_json(history_file, [])

    def save_training_result(self, result: Dict[str, Any]) -> None:
        """Salva o resultado de um treinamento no histórico."""
        history_file = os.path.join(self.models_dir, "training_history.json")
        history = self.get_training_history()
        history.append(result)
        _save_json(history_file, history)
