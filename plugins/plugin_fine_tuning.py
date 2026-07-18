"""
plugin_fine_tuning.py
=====================
Plugin de fine-tuning seguro para modelos de linguagem locais. Fornece ferramentas para:
- Fine-tuning eficiente usando LoRA/QLoRA
- Treinamento de modelos pequenos com recursos limitados
- Avaliação de modelos após fine-tuning
- Exportação e importação de modelos fine-tunados
"""

import os
import json
import torch
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

# Importações opcionais para fine-tuning
try:
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM,
        TrainingArguments, Trainer,
        DataCollatorForLanguageModeling
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_int8_training
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from datasets import Dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

__version__ = "1.0.0"
PLUGIN_NAME = "Fine-tuning Seguro de Modelos"

# Configurações de segurança
MAX_MODEL_SIZE_FOR_TRAINING = 3 * 1024 * 1024 * 1024  # 3GB limite para treinamento seguro
DEFAULT_OUTPUT_DIR = "./fine_tuned_models"


def _check_training_dependencies() -> tuple[bool, str]:
    """Verifica se as dependências necessárias para treinamento estão disponíveis."""
    if not TRANSFORMERS_AVAILABLE:
        return False, "Bibliotecas transformers/peft não instaladas. Execute: pip install transformers peft"

    if not DATASETS_AVAILABLE:
        return False, "Biblioteca datasets não instalada. Execute: pip install datasets"

    return True, "Dependências disponíveis"


def _get_model_size(model_path: str) -> int:
    """Estima o tamanho do modelo em bytes."""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(model_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    except:
        return 0


def safe_fine_tune_model(
    model_name: str,
    train_data: List[Dict[str, str]],
    output_dir: str = None,
    use_lora: bool = True,
    lora_r: int = 8,
    lora_alpha: int = 32,
    lora_dropout: float = 0.1,
    learning_rate: float = 2e-4,
    batch_size: int = 4,
    num_epochs: int = 3,
    max_length: int = 512,
) -> str:
    """
    Executa fine-tuning seguro de um modelo de linguagem usando técnicas eficientes.

    Args:
        model_name: Nome do modelo Hugging Face ou caminho local (ex: "microsoft/Phi-3-mini-4k-instruct")
        train_data: Lista de dicionários com chaves 'input' e 'output' para treinamento
        output_dir: Diretório para salvar o modelo fine-tunado
        use_lora: Se deve usar LoRA para fine-tuning eficiente
        lora_r: Rank do LoRA
        lora_alpha: Parâmetro alpha do LoRA
        lora_dropout: Dropout do LoRA
        learning_rate: Taxa de aprendizado
        batch_size: Tamanho do lote
        num_epochs: Número de épocas
        max_length: Comprimento máximo da sequência

    Returns:
        Mensagem de resultado com informações do treinamento
    """
    # Verificar dependências
    deps_ok, deps_msg = _check_training_dependencies()
    if not deps_ok:
        return f"❌ Erro: {deps_msg}"

    if not train_data:
        return "❌ Erro: Nenhum dado de treinamento fornecido"

    # Configurar diretório de saída
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, f"model_{timestamp}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        # Carregar tokenizer e modelo
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            load_in_8bit=True if not torch.cuda.is_available() else False  # 8-bit para CPU
        )

        # Verificar tamanho do modelo
        model_size = _get_model_size(model_name) if os.path.exists(model_name) else 0
        if model_size > MAX_MODEL_SIZE_FOR_TRAINING and not torch.cuda.is_available():
            return f"⚠️ Aviso: Modelo grande detectado ({model_size // (1024*1024)} MB). Treinamento em CPU pode ser muito lento."

        # Preparar tokenizador
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Preparar dados de treinamento
        def format_example(example):
            # Formato simples: instrução + resposta
            text = f"{example['input']}\n{example['output']}"
            tokenized = tokenizer(
                text,
                truncation=True,
                max_length=max_length,
                padding=False,
                return_tensors=None
            )
            tokenized["labels"] = tokenized["input_ids"].copy()
            return tokenized

        train_dataset = Dataset.from_list([format_example(ex) for ex in train_data])

        # Configurar LoRA se solicitado
        if use_lora:
            model = prepare_model_for_int8_training(model)
            lora_config = LoraConfig(
                r=lora_r,
                lalpha=lora_alpha,
                target_modules=["q_proj", "v_proj"],  # Comum para muitos modelos
                lora_dropout=lora_dropout,
                bias="none",
                task_type="CAUSAL_LM"
            )
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()

        # Argumentos de treinamento
        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            warmup_steps=100,
            num_train_epochs=num_epochs,
            learning_rate=learning_rate,
            fp16=torch.cuda.is_available(),
            logging_steps=10,
            save_strategy="epoch",
            evaluation_strategy="no",
            save_total_limit=2,
            remove_unused_columns=False,
            push_to_hub=False,
            report_to="none",  # Desabilitar wandb, mlflow, etc.
            dataloader_pin_memory=False,
        )

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
        )

        # Treinar
        trainer.train()

        # Salvar modelo e tokenizer
        trainer.save_model()
        tokenizer.save_pretrained(output_dir)

        # Salvar informações de treinamento
        training_info = {
            "base_model": model_name,
            "training_date": datetime.now().isoformat(),
            "num_examples": len(train_data),
            "use_lora": use_lora,
            "lora_params": {"r": lora_r, "alpha": lora_alpha, "dropout": lora_dropout} if use_lora else None,
            "hyperparameters": {
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "epochs": num_epochs,
                "max_length": max_length
            }
        }

        with open(os.path.join(output_dir, "training_info.json"), "w") as f:
            json.dump(training_info, f, indent=2)

        return f"""✅ Fine-tuning concluído com sucesso!
📁 Modelo salvo em: {os.path.abspath(output_dir)}
📊 Exemplos de treinamento: {len(train_data)}
🔧 Técnica utilizada: {'LoRA' if use_lora else 'Fine-tuning completo'}
⏱️ Épocas: {num_epochs}
📈 Taxa de aprendizado: {learning_rate}
💾 Salvado em: {output_dir}

Para usar o modelo fine-tunado, carregue-o com:
model = AutoModelForCausalLM.from_pretrained('{output_dir}')
tokenizer = AutoTokenizer.from_pretrained('{output_dir}')"""

    except Exception as e:
        return f"❌ Erro durante o fine-tuning: {str(e)}"


def list_fine_tuned_models() -> str:
    """
    Lista todos os modelos fine-tunados disponíveis.

    Returns:
        String formatada com a lista de modelos
    """
    if not os.path.exists(DEFAULT_OUTPUT_DIR):
        return f"📭 Nenhum modelo fine-tunado encontrado em {DEFAULT_OUTPUT_DIR}"

    models = []
    for item in os.listdir(DEFAULT_OUTPUT_DIR):
        item_path = os.path.join(DEFAULT_OUTPUT_DIR, item)
        if os.path.isdir(item_path):
            # Verificar se é um modelo válido
            config_path = os.path.join(item_path, "config.json")
            if os.path.exists(config_path):
                try:
                    stat = os.stat(item_path)
                    size_mb = sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, dirnames, filenames in os.walk(item_path)
                        for filename in filenames
                    ) / (1024 * 1024)

                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                    models.append({
                        "name": item,
                        "path": item_path,
                        "size_mb": round(size_mb, 2),
                        "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except:
                    pass

    if not models:
        return f"📭 Nenhum modelo válido encontrado em {DEFAULT_OUTPUT_DIR}"

    result = ["📋 Modelos fine-tunados disponíveis:"]
    result.append("-" * 60)

    for model in models:
        result.append(f"📁 {model['name']}")
        result.append(f"   Caminho: {model['path']}")
        result.append(f"   Tamanho: {model['size_mb']} MB")
        result.append(f"   Modificado: {model['modified']}")
        result.append("")

    return "\n".join(result)


def evaluate_model_performance(
    model_path: str,
    test_data: List[Dict[str, str]],
    max_length: int = 512,
    temperature: float = 0.7,
    max_new_tokens: int = 150
) -> str:
    """
    Avalia o desempenho de um modelo fine-tunado.

    Args:
        model_path: Caminho para o modelo fine-tunado
        test_data: Lista de dicionários com chaves 'input' e 'expected_output'
        max_length: Comprimento máximo da sequência
        temperature: Temperatura para geração
        max_new_tokens: Máximo de novos tokens gerados

    Returns:
        Relatório de avaliação
    """
    if not os.path.exists(model_path):
        return f"❌ Modelo não encontrado em {model_path}"

    try:
        # Carregar modelo e tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model.eval()

        correct = 0
        total = len(test_data)
        results = []

        for i, example in enumerate(test_data):
            input_text = example["input"]
            expected = example["expected_output"]

            # Tokenizar entrada
            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=max_length
            ).to(model.device)

            # Gerar resposta
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )

            # Decodificar resposta
            generated_text = tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            ).strip()

            # Verificar se a resposta contém o esperado (método simples)
            is_correct = expected.lower() in generated_text.lower()
            if is_correct:
                correct += 1

            results.append({
                "input": input_text,
                "expected": expected,
                "generated": generated_text,
                "correct": is_correct
            })

        accuracy = (correct / total) * 100 if total > 0 else 0

        # Formatar resultados
        result_lines = [
            f"📊 Avaliação do Modelo: {model_path}",
            f"🎯 Acurácia: {accuracy:.1f}% ({correct}/{total})",
            f"📝 Exemplos testados: {total}",
            "",
            "📋 Detalhes por exemplo:"
        ]

        for i, res in enumerate(results[:5]):  # Mostrar apenas os primeiros 5
            status = "✅" if res["correct"] else "❌"
            result_lines.append(f"{status} Exemplo {i+1}:")
            result_lines.append(f"   Entrada: {res['input'][:50]}{'...' if len(res['input']) > 50 else ''}")
            result_lines.append(f"   Esperado: {res['expected'][:50]}{'...' if len(res['expected']) > 50 else ''}")
            result_lines.append(f"   Gerado: {res['generated'][:50]}{'...' if len(res['generated']) > 50 else ''}")
            result_lines.append("")

        if total > 5:
            result_lines.append(f"... e mais {total - 5} exemplos")

        return "\n".join(result_lines)

    except Exception as e:
        return f"❌ Erro durante a avaliação: {str(e)}"


# Registro das funções no sistema de plugins
def register(api):
    """Registra todas as ferramentas de fine-tuning."""

    if not TRANSFORMERS_AVAILABLE:
        # Ainda registrar as funções, mas elas retornarão mensagens de erro
        def safe_fine_tune_model_stub(*args, **kwargs):
            return "❌ Erro: Bibliotecas de fine-tuning não instaladas. Execute: pip install transformers peft datasets torch"

        def list_fine_tuned_models_stub(*args, **kwargs):
            return "❌ Erro: Bibliotecas de fine-tuning não instaladas. Execute: pip install transformers peft datasets torch"

        def evaluate_model_performance_stub(*args, **kwargs):
            return "❌ Erro: Bibliotecas de fine-tuning não instaladas. Execute: pip install transformers peft datasets torch"

        api.register_tool(
            name="safe_fine_tune_model",
            func=safe_fine_tune_model_stub,
            description="Executa fine-tuning seguro de um modelo de linguagem (requer dependências)",
            parameters={
                "model_name": {"type": "string", "description": "Nome do modelo Hugging Face ou caminho local"},
                "train_data": {"type": "array", "items": {"type": "object", "properties": {"input": {"type": "string"}, "output": {"type": "string"}}}, "description": "Dados de treinamento"},
                "output_dir": {"type": "string", "description": "Diretório para salvar o modelo (opcional)"},
                "use_lora": {"type": "boolean", "description": "Usar LoRA para fine-tuning eficiente (padrão: true)"},
                "learning_rate": {"type": "number", "description": "Taxa de aprendizado (padrão: 2e-4)"},
                "batch_size": {"type": "integer", "description": "Tamanho do lote (padrão: 4)"},
                "num_epochs": {"type": "integer", "description": "Número de épocas (padrão: 3)"}
            },
            required=["model_name", "train_data"]
        )

        api.register_tool(
            name="list_fine_tuned_models",
            func=list_fine_tuned_models_stub,
            description="Lista todos os modelos fine-tunados disponíveis",
            parameters={},
            required=[]
        )

        api.register_tool(
            name="evaluate_model_performance",
            func=evaluate_model_performance_stub,
            description="Avalia o desempenho de um modelo fine-tunado",
            parameters={
                "model_path": {"type": "string", "description": "Caminho para o modelo fine-tunado"},
                "test_data": {"type": "array", "items": {"type": "object", "properties": {"input": {"type": "string"}, "expected_output": {"type": "string"}}}, "description": "Dados de teste"}
            },
            required=["model_path", "test_data"]
        )
    else:
        # Registrar as funções reais
        api.register_tool(
            name="safe_fine_tune_model",
            func=safety_fine_tune_model,
            description="Executa fine-tuning seguro de um modelo de linguagem usando LoRA/QLoRA para eficiência",
            parameters={
                "model_name": {"type": "string", "description": "Nome do modelo Hugging Face ou caminho local (ex: 'microsoft/Phi-3-mini-4k-instruct')"},
                "train_data": {"type": "array", "items": {"type": "object", "properties": {"input": {"type": "string"}, "output": {"type": "string"}}}, "description": "Dados de treinamento com campos 'input' e 'output'"},
                "output_dir": {"type": "string", "description": "Diretório para salvar o modelo fine-tunado (opcional, padrão: ./fine_tuned_models/model_TIMESTAMP)"},
                "use_lora": {"type": "boolean", "description": "Usar LoRA para fine-tuning eficiente (padrão: true)"},
                "lora_r": {"type": "integer", "description": "Rank do LoRA (padrão: 8)"},
                "lora_alpha": {"type": "integer", "description": "Parâmetro alpha do LoRA (padrão: 32)"},
                "lora_dropout": {"type": "number", "description": "Dropout do LoRA (padrão: 0.1)"},
                "learning_rate": {"type": "number", "description": "Taxa de aprendizado (padrão: 2e-4)"},
                "batch_size": {"type": "integer", "description": "Tamanho do lote (padrão: 4)"},
                "num_epochs": {"type": "integer", "description": "Número de épocas (padrão: 3)"},
                "max_length": {"type": "integer", "description": "Comprimento máximo da sequência (padrão: 512)"}
            },
            required=["model_name", "train_data"]
        )

        api.register_tool(
            name="list_fine_tuned_models",
            func=list_fine_tuned_models,
            description="Lista todos os modelos fine-tunados disponíveis para uso",
            parameters={},
            required=[]
        )

        api.register_tool(
            name="evaluate_model_performance",
            func=evaluate_model_performance,
            description="Avalia o desempenho de um modelo fine-tunado com dados de teste",
            parameters={
                "model_path": {"type": "string", "description": "Caminho para o modelo fine-tunado"},
                "test_data": {"type": "array", "items": {"type": "object", "properties": {"input": {"type": "string"}, "expected_output": {"type": "string"}}}, "description": "Dados de teste com campos 'input' e 'expected_output'"}
            },
            required=["model_path", "test_data"]
        )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Fine-tuning seguro de modelos de linguagem usando LoRA/QLoRA para eficiência de recursos",
        "tools": [
            "safe_fine_tune_model",
            "list_fine_tuned_models",
            "evaluate_model_performance"
        ],
    }
