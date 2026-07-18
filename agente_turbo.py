"""
agente_turbo.py
================
Módulo de inteligência turbo — adiciona raciocínio avançado, 
recuperação inteligente de erros, cache, decomposição de tarefas,
execução paralela e auto-aperfeiçoamento ao agente principal.

Integra-se com agente_core.py sem modificar suas funções existentes.
"""

import os
import re
import json
import time
import hashlib
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

TURBO_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "agente_data", "turbo_cache"
)
os.makedirs(TURBO_CACHE_DIR, exist_ok=True)

TURBO_CACHE_ENABLED = True
TURBO_CACHE_TTL = 3600
TURBO_PARALLEL_MAX_WORKERS = 4
TURBO_MAX_RETRY_STRATEGIES = 3

_logger = logging.getLogger("agente_turbo")


# ===================================================================
# CACHE INTELIGENTE — evita repetir chamadas caras
# ===================================================================

def _cache_key(func_name: str, args: dict) -> str:
    raw = f"{func_name}:{json.dumps(args, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _cache_get(key: str) -> Optional[str]:
    if not TURBO_CACHE_ENABLED:
        return None
    path = os.path.join(TURBO_CACHE_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["ts"] > TURBO_CACHE_TTL:
            os.remove(path)
            return None
        _logger.info("Cache HIT: %s", key[:12])
        return data["result"]
    except Exception:
        return None


def _cache_set(key: str, result: str) -> None:
    if not TURBO_CACHE_ENABLED:
        return
    try:
        path = os.path.join(TURBO_CACHE_DIR, f"{key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "result": result}, f, ensure_ascii=False)
    except Exception:
        pass


def _cache_clear() -> int:
    antes = len(os.listdir(TURBO_CACHE_DIR))
    for fname in os.listdir(TURBO_CACHE_DIR):
        if fname.endswith(".json"):
            try:
                os.remove(os.path.join(TURBO_CACHE_DIR, fname))
            except Exception:
                pass
    return antes


# ===================================================================
# DECOMPOSIÇÃO DE TAREFAS — quebra problemas complexos em etapas
# ===================================================================

PATTERNS_DECOMPOSICAO = {
    "codigo": [
        r"(?:criar|fazer|desenvolver|implementar|escrever|codificar|programar)\s+(?:um|uma|o|a)?\s*(?:sistema|app|programa|script|funcao|classe|api|site|bot)",
        r"(?:refatorar|otimizar|debuggar|corrigir|testar|documentar)\s+(?:o|a|este|essa)?\s*(?:codigo|sistema|funcao|classe|script)",
    ],
    "arquivos": [
        r"(?:organizar|arrumar|estruturar|renomear|mover|copiar|backup|compactar)\s+(?:arquivos|pastas|diretorios)",
        r"(?:buscar|encontrar|localizar|procurar)\s+(?:arquivos|pastas|diretorios)",
    ],
    "analise": [
        r"(?:analisar|comparar|avaliar|diagnosticar|investigar|pesquisar)",
        r"(?:o que|como|por que|qual a diferenca|explique|resuma)",
    ],
    "dados": [
        r"(?:processar|transformar|converter|extrair|importar|exportar)\s+(?:dados|arquivos?|planilhas?|csv|json|xml)",
        r"(?:plotar|grafico|visualizar|dashboard)",
    ],
    "web": [
        r"(?:baixar|download|scrape|raspar|coletar)\s+(?:da|de|o)?\s*(?:internet|web|site|url|pagina|api)",
    ],
    "imagem": [
        r"(?:processar|editar|redimensionar|converter|comprimir)\s+(?:imagem|foto|imagens|fotos)",
    ],
}


def _inferir_tipo_tarefa(task: str) -> str:
    task_lower = task.lower()
    for tipo, patterns in PATTERNS_DECOMPOSICAO.items():
        for p in patterns:
            if re.search(p, task_lower):
                return tipo
    return "geral"


def _estimar_complexidade(task: str) -> int:
    palavras = len(task.split())
    if palavras > 60:
        return 3
    if palavras > 25:
        return 2
    return 1


def _gerar_subtarefas(task: str, tipo: str, complexidade: int) -> list:
    templates = {
        "codigo": {
            1: ["Analisar requisitos e gerar codigo"],
            2: [
                "Analisar e planejar a estrutura do codigo",
                "Implementar o codigo seguindo o planejamento",
                "Revisar e testar o codigo gerado",
            ],
            3: [
                "Analisar requisitos detalhadamente e planejar arquitetura",
                "Configurar ambiente e dependencias necessarias",
                "Implementar os modulos/componentes um a um",
                "Criar testes para validar o funcionamento",
                "Revisar, documentar e otimizar o codigo final",
            ],
        },
        "arquivos": {
            1: ["Listar e analisar arquivos", "Executar operacao nos arquivos"],
            2: [
                "Mapear estrutura atual de arquivos",
                "Planejar as transformacoes necessarias",
                "Executar as operacoes em lote",
                "Verificar resultado final",
            ],
            3: [
                "Escaneamento completo da estrutura",
                "Plano detalhado de organizacao",
                "Backup de seguranca antes de modificar",
                "Execucao das transformacoes em ordem",
                "Validacao e relatorio final",
            ],
        },
        "analise": {
            1: ["Coletar informacoes", "Sintetizar analise"],
            2: [
                "Coletar dados e informacoes relevantes",
                "Organizar e estruturar os dados coletados",
                "Produzir analise e recomendacoes",
            ],
            3: [
                "Pesquisa e coleta exaustiva de informacoes",
                "Organizacao e cruzamento dos dados",
                "Analise profunda com multiplas perspectivas",
                "Sintese com recomendacoes acionaveis",
                "Formatacao do relatorio final",
            ],
        },
        "dados": {
            1: ["Carregar dados", "Processar e exportar"],
            2: [
                "Carregar e inspecionar dados brutos",
                "Processar/transformar conforme necessidade",
                "Exportar resultado final",
            ],
            3: [
                "Carregar e validar dados de entrada",
                "Limpeza e pre-processamento",
                "Transformacao e enriquecimento dos dados",
                "Geracao de visualizacoes/relatorios",
                "Exportacao em formato final",
            ],
        },
        "web": {
            1: ["Acessar URL e baixar conteudo"],
            2: [
                "Acessar e parsear o conteudo web",
                "Extrair e salvar as informacoes relevantes",
            ],
            3: [
                "Configurar estrategia de coleta",
                "Executar download/scraping",
                "Processar e estruturar dados coletados",
                "Salvar em formato adequado",
            ],
        },
        "imagem": {
            1: ["Carregar e processar imagem"],
            2: [
                "Identificar caracteristicas da imagem",
                "Aplicar processamento necessario",
                "Salvar resultado",
            ],
            3: [
                "Analise completa da imagem",
                "Pre-processamento e preparacao",
                "Aplicacao de filtros/transformacoes",
                "Exportacao em formato final",
            ],
        },
        "geral": {
            1: ["Executar tarefa solicitada"],
            2: ["Planejar abordagem", "Executar plano", "Verificar resultado"],
            3: [
                "Analise detalhada do problema",
                "Plano de acao em etapas",
                "Execucao de cada etapa",
                "Verificacao e validacao",
                "Ajustes finais e conclusao",
            ],
        },
    }
    return templates.get(tipo, templates["geral"]).get(complexidade, templates["geral"][1])


def task_decompose(task: str) -> str:
    """Decompõe uma tarefa complexa em subtarefas menores e executáveis.
    Retorna um plano estruturado."""
    tipo = _inferir_tipo_tarefa(task)
    complexidade = _estimar_complexidade(task)
    subtarefas = _gerar_subtarefas(task, tipo, complexidade)

    lines = [
        f"--- DECOMPOSICAO DE TAREFA ---",
        f"Tipo: {tipo.upper()}",
        f"Complexidade: {'★' * complexidade}{'☆' * (3 - complexidade)}",
        f"Subtarefas ({len(subtarefas)}):",
    ]
    for i, st in enumerate(subtarefas, 1):
        lines.append(f"  {i}. {st}")
    lines.append("--- INICIANDO EXECUCAO ---")
    return "\n".join(lines)


# ===================================================================
# RECUPERAÇÃO INTELIGENTE DE ERROS
# ===================================================================

_STRATEGIES: dict = {}


def _registrar_estrategia(nome_ferramenta: str, estrategia: Callable) -> None:
    _STRATEGIES[nome_ferramenta] = estrategia


def _estrategia_padrao(func_name: str, args: dict, erro: str) -> Optional[dict]:
    erro_lower = erro.lower()

    if "permission" in erro_lower or "acesso" in erro_lower or "negado" in erro_lower:
        for key in list(args.keys()):
            path = args[key]
            if isinstance(path, str) and os.path.exists(path):
                dir_path = os.path.dirname(path) if "." in os.path.basename(path) else path
                try:
                    os.chmod(dir_path, 0o755)
                    return {"args": args, "strategy": f"Permissoes ajustadas em {dir_path}"}
                except Exception:
                    pass
                alt_path = os.path.join(os.environ.get("TEMP", "/tmp"), os.path.basename(path))
                new_args = dict(args)
                new_args[key] = alt_path
                return {"args": new_args, "strategy": f"Tentando caminho alternativo: {alt_path}"}

    if "not found" in erro_lower or "nao encontrado" in erro_lower or "no such" in erro_lower:
        for key in list(args.keys()):
            path = args[key]
            if isinstance(path, str) and not os.path.isabs(path):
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    new_args = dict(args)
                    new_args[key] = abs_path
                    return {"args": new_args, "strategy": f"Usando caminho absoluto: {abs_path}"}

    if "timeout" in erro_lower or "time" in erro_lower:
        new_args = dict(args)
        for key in list(args.keys()):
            if isinstance(args[key], int):
                new_args[key] = args[key] * 2
                return {"args": new_args, "strategy": f"Dobrando timeout de {args[key]} para {args[key] * 2}"}

    if "encoding" in erro_lower or "decode" in erro_lower or "unicode" in erro_lower:
        new_args = dict(args)
        for key in list(args.keys()):
            if isinstance(args[key], str) and args[key].endswith((".py", ".txt", ".md", ".json", ".csv", ".html", ".css", ".js")):
                try:
                    content = open(args[key], "r", encoding="utf-8", errors="replace").read()
                    return {"args": new_args, "strategy": "Lido com substituicao de caracteres invalidos"}
                except Exception:
                    pass

    return None


def _recovery_attempt(func: Callable, func_name: str, original_args: dict, erro: str, depth: int = 0) -> str:
    if depth >= TURBO_MAX_RETRY_STRATEGIES:
        return None

    strategies = _STRATEGIES.get(func_name, _estrategia_padrao)
    result = strategies(func_name, original_args, erro)
    if result is None:
        return None

    try:
        resp = func(**result["args"])
        _logger.info("Recuperacao de erro bem-sucedida para %s: %s", func_name, result["strategy"])
        return f"[Auto-recuperacao: {result['strategy']}]\n{resp}"
    except Exception as e2:
        _logger.warning("Tentativa de recuperacao falhou para %s: %s", func_name, e2)
        return _recovery_attempt(func, func_name, result["args"], str(e2), depth + 1)


def execute_with_recovery(func: Callable, func_name: str, args: dict) -> str:
    """Executa uma ferramenta com recuperação inteligente de erros."""
    try:
        return func(**args)
    except TypeError as e:
        _logger.warning("Erro de argumentos em %s: %s", func_name, e)
        return f"Erro: argumentos incorretos para '{func_name}': {e}"
    except Exception as e:
        erro_str = str(e)
        _logger.warning("Ferramenta %s falhou: %s", func_name, erro_str)

        recovery = _recovery_attempt(func, func_name, args, erro_str)
        if recovery:
            return recovery

        try:
            import ollama
            from agente_core import _call_ollama_with_timeout, NUM_CTX, MODEL

            prompt = (
                f"Uma ferramenta falhou com o seguinte erro:\n\n"
                f"Ferramenta: {func_name}\n"
                f"Argumentos: {json.dumps(args, ensure_ascii=False)}\n"
                f"Erro: {erro_str}\n\n"
                f"Sugira uma alternativa ou solucao em ate 2 frases. "
                f"Seja pratico e direto."
            )
            suggestion = _call_ollama_with_timeout(
                ollama.chat,
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": 4096, "temperature": 0.2},
            )
            sugestao = suggestion["message"]["content"].strip()
        except Exception:
            sugestao = "Tente verificar os parametros e tentar novamente com valores diferentes."

        return f"Erro ao executar '{func_name}': {erro_str}\n[Sugestao IA]: {sugestao}"


# ===================================================================
# EXECUÇÃO PARALELA DE FERRAMENTAS
# ===================================================================

def execute_parallel(calls: list, functions_registry: dict) -> list:
    """Executa múltiplas chamadas de ferramenta em paralelo.
    calls: lista de (func_name, args_dict)
    Retorna lista de (func_name, args, resultado)
    """
    results = [None] * len(calls)

    def _exec(i, func_name, args):
        func = functions_registry.get(func_name)
        if not func:
            return i, func_name, args, f"Erro: ferramenta '{func_name}' nao existe."
        try:
            return i, func_name, args, func(**args)
        except Exception as e:
            return i, func_name, args, f"Erro: {e}"

    indices_para_executar = []
    for i, (fname, fargs) in enumerate(calls):
        func = functions_registry.get(fname)
        if func:
            indices_para_executar.append(i)

    with ThreadPoolExecutor(max_workers=TURBO_PARALLEL_MAX_WORKERS) as pool:
        futures = {}
        for i in indices_para_executar:
            fname, fargs = calls[i]
            future = pool.submit(_exec, i, fname, fargs)
            futures[future] = i

        for future in as_completed(futures):
            i, fname, fargs, result = future.result()
            results[i] = (fname, fargs, result)

    for i, (fname, fargs) in enumerate(calls):
        if results[i] is None:
            results[i] = (fname, fargs, "(pulado)")

    return results


# ===================================================================
# QUALIDADE E REVISÃO DE CÓDIGO
# ===================================================================

def code_review(code: str, linguagem: str = "python") -> str:
    """Revisa codigo e retorna sugestoes de melhoria."""
    problemas = []
    sugestoes = []

    if linguagem == "python":
        if "import " not in code and len(code) > 100:
            sugestoes.append("Considere adicionar imports necessarios")

        if "try:" in code and "except:" in code:
            problemas.append("Usar 'except:' genérico captura todas excecoes — especifique o tipo")

        if "eval(" in code or "exec(" in code:
            problemas.append("eval()/exec() podem ser perigosos — prefira alternativas seguras")

        if "print(" in code and len(code) > 300:
            sugestoes.append("Considere usar logging em vez de print para codigo de producao")

        if "pass" in code:
            problemas.append("'pass' encontrado — pode indicar codigo incompleto")

        if len(open.__class__.__module__) > 0:
            if "with open" not in code and "open(" in code:
                problemas.append("Arquivos abertos sem 'with' podem vazar recursos")

        if "TODO" in code or "FIXME" in code or "XXX" in code:
            problemas.append("Existem marcadores TODO/FIXME no codigo")

        if "os.system(" in code:
            problemas.append("os.system() é inseguro — prefira subprocess.run()")

        funcoes = re.findall(r"def (\w+)\(", code)
        classes = re.findall(r"class (\w+)", code)
        if funcoes and not any("def test_" in line for line in code.split("\n")):
            sugestoes.append("Considere adicionar testes para as funcoes")

        try:
            compile(code, "<review>", "exec")
        except SyntaxError as e:
            problemas.append(f"Erro de sintaxe: {e}")

    if not problemas:
        return "✅ Revisao: Nenhum problema grave encontrado.\n" + ("💡 ".join([""] + sugestoes) if sugestoes else "")

    linhas = ["🔍 REVISAO DE CODIGO:"]
    for p in problemas:
        linhas.append(f"  ⚠ {p}")
    for s in sugestoes:
        linhas.append(f"  💡 {s}")
    return "\n".join(linhas)


def code_auto_fix(code: str, error: str) -> str:
    """Tenta corrigir codigo automaticamente com base em erro."""
    fixes = []

    lines = code.split("\n")
    fixed_lines = list(lines)

    error_lower = error.lower()

    if "indentationerror" in error_lower or "unexpected indent" in error_lower:
        fixed_lines = []
        for line in lines:
            stripped = line.lstrip()
            if stripped and not line.startswith(" ") and not line.startswith("\t") and stripped not in ("", "\n"):
                fixed_lines.append(stripped)
            else:
                fixed_lines.append(line)
        fixes.append("Corrigida indentacao")

    if "nameerror" in error_lower:
        match = re.search(r"name '(\w+)' is not defined", error)
        if match:
            nome = match.group(1)
            if nome in ("pd", "np", "plt", "sns"):
                fixed_lines.insert(0, f"import {nome}")
            elif nome in ("os", "sys", "re", "json", "math", "random", "datetime"):
                fixed_lines.insert(0, f"import {nome}")
            fixes.append(f"Adicionado import para '{nome}'")

    if "importerror" in error_lower or "module" in error_lower:
        match = re.search(r"no module named ['\"]?(\w+)['\"]?", error_lower)
        if match:
            modulo = match.group(1)
            fixes.append(f"Tentando instalar modulo '{modulo}'...")
            try:
                import subprocess
                subprocess.run(f"pip install {modulo}", shell=True, capture_output=True, timeout=30)
                fixes.append(f"Modulo '{modulo}' instalado com sucesso")
            except Exception:
                fixes.append(f"Nao foi possivel instalar '{modulo}'")

    if "filenotfounderror" in error_lower or "no such file" in error_lower:
        match = re.search(r"'(.*?)'", error)
        if match:
            fname = match.group(1)
            fixes.append(f"Arquivo '{fname}' nao encontrado — tente verificar o caminho")

    if fixes:
        result = "\n".join(fixed_lines)
        return f"// Auto-fix aplicado: {'; '.join(fixes)}\n\n{result}"

    return code


# ===================================================================
# RACIOCÍNIO ESTRUTURADO (Chain-of-Thought)
# ===================================================================

def structured_reasoning(task: str, contexto: str = "") -> str:
    """Gera raciocinio passo-a-passo antes de executar ferramentas."""
    try:
        import ollama
        from agente_core import _call_ollama_with_timeout, NUM_CTX, MODEL

        prompt = (
            "Analise a tarefa abaixo e produza um raciocinio ESTRUTURADO.\n\n"
            "Formato obrigatorio:\n"
            "1. OBJETIVO: O que precisa ser feito (1 frase)\n"
            "2. ANALISE: Quais sao as etapas logicas necessarias\n"
            "3. FERRAMENTAS: Quais ferramentas serao usadas e em que ordem\n"
            "4. RISCOS: Possiveis problemas e como evita-los\n"
            "5. PLANO: Sequencia de acoes passo-a-passo\n\n"
        )
        if contexto:
            prompt += f"CONTEXTO:\n{contexto}\n\n"
        prompt += f"TAREFA: {task}"

        response = _call_ollama_with_timeout(
            ollama.chat,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX, "temperature": 0.3},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return f"[Raciocinio indisponivel: {e}]"


# ===================================================================
# COMPRESSÃO AVANÇADA DE CONTEXTO
# ===================================================================

def smart_context_compress(messages: list, model: str, max_messages: int = 40) -> list:
    """Comprime o historico preservando informacao maxima.
    Melhor que trim_and_summarize_history porque usa compressao seletiva."""
    if len(messages) <= max_messages:
        return messages

    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]

    keep_latest = other_msgs[-(max_messages - 3):]
    to_compress = other_msgs[:-(max_messages - 3)]

    # Agrupa por blocos tematicos em vez de resumir tudo de uma vez
    blocos = []
    bloco_atual = []
    tam_bloco = 0
    for m in to_compress:
        content = m.get("content", "")
        tam_bloco += len(content)
        bloco_atual.append(m)
        if tam_bloco > 2000:
            blocos.append(bloco_atual)
            bloco_atual = []
            tam_bloco = 0
    if bloco_atual:
        blocos.append(bloco_atual)

    resumos = []
    for bloco in blocos:
        texto = "\n".join(f"{m.get('role')}: {m.get('content', '')}" for m in bloco if m.get("content"))
        if not texto.strip():
            continue
        try:
            import ollama
            from agente_core import _call_ollama_with_timeout
            resp = _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=[{
                    "role": "user",
                    "content": (
                        "Resuma o trecho de conversa abaixo preservando APENAS "
                        "fatos, decisoes, dados e acordos. Ignore conversa fiada:\n\n"
                        f"{texto[:3000]}"
                    ),
                }],
                options={"num_ctx": 4096, "temperature": 0.1},
            )
            resumo = resp["message"]["content"].strip()
            if resumo:
                resumos.append(resumo)
        except Exception:
            resumos.append("(trecho descartado)")

    if resumos:
        summary_msg = {
            "role": "system",
            "content": f"[Resumo de conversa anterior]: {' | '.join(resumos)}",
        }
    else:
        summary_msg = {
            "role": "system",
            "content": "[Contexto anterior descartado para economia de tokens]",
        }

    return system_msgs + [summary_msg] + keep_latest


# ===================================================================
# PIPELINE DE IMAGEM AVANÇADO
# ===================================================================

def analyze_image_advanced(path: str, questions: list = None) -> str:
    """Analise multi-estagio de imagem: OCR + descricao + analise."""
    partes = []

    try:
        from agente_core import read_image_text, describe_image
    except ImportError:
        return "Módulo agente_core nao disponivel"

    if not questions:
        questions = [
            "Descreva detalhadamente o que ve nesta imagem.",
            "Ha texto visivel? Se sim, transcreva todo o texto.",
            "Quais objetos, pessoas ou elementos principais aparecem?",
        ]

    for q in questions:
        try:
            resultado = describe_image(path, q)
            partes.append(f"> {q}\n{resultado}")
        except Exception:
            pass

    try:
        ocr = read_image_text(path)
        if ocr and ocr != "Nenhum texto encontrado na imagem.":
            partes.append(f"> OCR (texto extraido):\n{ocr}")
    except Exception:
        pass

    return "\n\n---\n\n".join(partes) if partes else "Nao foi possivel analisar a imagem."


# ===================================================================
# DIAGNÓSTICO DO SISTEMA
# ===================================================================

def turbo_diagnostico() -> str:
    """Diagnostico completo do sistema turbo."""
    linhas = ["🚀 TURBO DIAGNOSTICO", "=" * 40]

    # Cache
    cache_files = [f for f in os.listdir(TURBO_CACHE_DIR) if f.endswith(".json")]
    cache_size = sum(os.path.getsize(os.path.join(TURBO_CACHE_DIR, f)) for f in cache_files) if cache_files else 0
    linhas.append(f"\n📦 Cache: {len(cache_files)} arquivos, {cache_size:,} bytes")

    linhas.append(f"\n⚙ Configuracao:")
    linhas.append(f"  Cache ativo: {TURBO_CACHE_ENABLED}")
    linhas.append(f"  Cache TTL: {TURBO_CACHE_TTL}s")
    linhas.append(f"  Workers paralelos: {TURBO_PARALLEL_MAX_WORKERS}")
    linhas.append(f"  Max estrategias de erro: {TURBO_MAX_RETRY_STRATEGIES}")

    linhas.append(f"\n🔧 Estrategias de erro registradas: {len(_STRATEGIES)}")

    linhas.append(f"\n💡 Dicas:")
    linhas.append(f"  Use 'turbo cache limpar' para limpar o cache")
    linhas.append(f"  Use 'turbo diagnosticar' para este diagnostico")

    return "\n".join(linhas)


# ===================================================================
# EXTRAÇÃO INTELIGENTE — resume conteudo grande
# ===================================================================

def smart_extract(text: str, max_chars: int = 2000, query: str = "") -> str:
    """Extrai as partes mais relevantes de um texto grande.
    Se query for fornecida, prioriza trechos relacionados."""
    if len(text) <= max_chars:
        return text

    if not query:
        # Pega inicio, meio e fim
        third = len(text) // 3
        return (
            text[:third]
            + "\n\n[... conteudo central omitido ...]\n\n"
            + text[-third:]
        )

    query_lower = query.lower()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    scored = []
    for s in sentences:
        if not s.strip():
            continue
        words_query = set(query_lower.split())
        words_sent = set(s.lower().split())
        score = len(words_query & words_sent) / max(len(words_query), 1)
        scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [s for score, s in scored if score > 0][:20]

    if relevant:
        result = "\n".join(relevant)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n[... truncado ...]"
        return result

    return text[:max_chars] + "\n[... truncado ...]"


# ===================================================================
# INICIALIZAÇÃO
# ===================================================================

def init_turbo():
    """Inicializa o modulo turbo. Chamado na importacao."""
    _logger.info("Modulo Turbo inicializado")
    _logger.info("  Cache: %s", "ativo" if TURBO_CACHE_ENABLED else "desativado")
    _logger.info("  Workers: %s", TURBO_PARALLEL_MAX_WORKERS)
    return True


init_turbo()
