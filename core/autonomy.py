from ._common import *
from .memory import *
# =======================================================================
# INTELIGENCIA AUTONOMA: roteamento, contexto e aprendizado leve
# =======================================================================

_INTENT_RULES = [
    {
        "intent": "codigo",
        "keywords": [
            "codigo", "código", "programa", "script", "bug", "erro", "debug",
            "refator", "api", "classe", "funcao", "função", "teste", "pytest",
            "javascript", "python", "html", "css", "sql", "git", "repo",
        ],
        "delegate": "subagente_codigo",
        "tools": ["executor_autonomo", "subagente_codigo", "subagente_debug", "subagente_testes", "grep_in_files", "read_file", "code_review", "run_python_code"],
        "policy": "Ler o codigo existente, localizar causa raiz, alterar pouco, testar e corrigir em ciclo.",
    },
    {
        "intent": "brasil_mundo",
        "keywords": [
            "brasil", "mundo", "noticia", "notícias", "noticias", "hoje",
            "atual", "atualizado", "ultimas", "últimas", "economia",
            "politica", "política", "internacional", "cotacao", "cotação",
            "clima", "pais", "país",
        ],
        "delegate": "subagente_analise",
        "tools": ["contexto_brasil_mundo", "subagente_brasil_mundo", "noticias_do_momento", "buscar_noticias", "web_search", "fetch_url"],
        "policy": "Tratar como conhecimento temporal: buscar fonte atual, separar Brasil/mundo e citar data/fonte.",
    },
    {
        "intent": "pesquisa_analise",
        "keywords": [
            "analise", "análise", "comparar", "planejar", "estrategia",
            "estratégia", "decidir", "vantagens", "desvantagens", "resumo",
            "sintetize", "pesquise", "pesquisa",
        ],
        "delegate": "subagente_analise",
        "tools": ["executor_autonomo", "subagente_analise", "structured_reasoning", "task_decompose", "web_search", "smart_extract"],
        "policy": "Quebrar a pergunta, coletar evidencias e entregar recomendacao acionavel.",
    },
    {
        "intent": "criativo",
        "keywords": [
            "ideia", "criativo", "nome", "marca", "slogan", "roteiro",
            "texto", "post", "campanha", "historia", "história", "design",
        ],
        "delegate": "subagente_criativo",
        "tools": ["subagente_criativo", "gerar_codigo", "generate_image"],
        "policy": "Gerar alternativas prontas para uso e adaptar tom ao publico.",
    },
    {
        "intent": "arquivos_sistema",
        "keywords": [
            "arquivo", "pasta", "diretorio", "diretório", "baixar", "download",
            "zip", "extrair", "copiar", "mover", "apagar", "renomear",
            "instalar", "comando", "terminal",
        ],
        "delegate": "subagente_analise",
        "tools": ["executor_autonomo", "list_files", "search_files", "download_file", "git_clone", "extract_file", "run_command"],
        "policy": "Confirmar caminhos e evitar acoes irreversiveis sem confirmacao.",
    },
    {
        "intent": "projeto_completo",
        "keywords": [
            "programa completo", "app completo", "sistema completo", "desenvolva",
            "desenvolver", "projeto completo", "frontend", "backend", "api",
            "dashboard", "site", "aplicativo",
        ],
        "delegate": "subagente_arquitetura",
        "tools": ["desenvolver_projeto", "executor_autonomo", "subagente_arquitetura", "subagente_frontend", "subagente_backend", "subagente_testes"],
        "policy": "Criar projeto funcional por template, validar sintaxe/testes, corrigir erros e registrar solucoes.",
    },
]


def _latest_user_text(messages: list) -> str:
    for msg in reversed(messages or []):
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def _score_intents(text: str) -> list[dict]:
    lower = text.lower()
    scored = []
    for rule in _INTENT_RULES:
        hits = [kw for kw in rule["keywords"] if kw in lower]
        if hits:
            scored.append({
                "intent": rule["intent"],
                "score": len(hits),
                "hits": hits[:8],
                "delegate": rule["delegate"],
                "tools": rule["tools"],
                "policy": rule["policy"],
            })
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def _detect_complexity(text: str) -> dict:
    lower = text.lower()
    step_words = [" e ", " depois ", " tambem ", " também ", " alem ", " além ", "integrar", "automat", "melhor", "projeto"]
    action_verbs = re.findall(
        r"\b(faca|faça|crie|adicione|analise|melhore|corrija|implemente|ensine|delegue|busque|organize)\b",
        lower,
    )
    score = 0
    score += min(4, len(action_verbs))
    score += sum(1 for w in step_words if w in lower)
    score += 2 if len(text) > 180 else 0
    score += 1 if "?" in text else 0
    if score >= 6:
        nivel = "alta"
    elif score >= 3:
        nivel = "media"
    else:
        nivel = "baixa"
    return {"nivel": nivel, "score": score, "acoes_detectadas": action_verbs[:8]}


def autonomia_planejar(tarefa: str) -> str:
    """Classifica uma tarefa, recomenda sub-agentes, ferramentas e plano de execucao."""
    tarefa = (tarefa or "").strip()
    if not tarefa:
        return "Informe uma tarefa para planejar."

    intents = _score_intents(tarefa)
    complexity = _detect_complexity(tarefa)
    primary = intents[0] if intents else {
        "intent": "geral",
        "delegate": "subagente_analise",
        "tools": ["structured_reasoning", "task_decompose", "web_search"],
        "policy": "Entender objetivo, dividir em etapas e executar com ferramentas reais.",
        "hits": [],
    }

    linhas = [
        "--- Plano Autonomo de Responsabilidade ---",
        f"Intencao principal: {primary['intent']}",
        f"Complexidade: {complexity['nivel']} (score {complexity['score']})",
        f"Sub-agente responsavel: {primary['delegate']}",
        f"Ferramentas recomendadas: {', '.join(primary['tools'])}",
        f"Regra de execucao: {primary['policy']}",
    ]
    if len(intents) > 1:
        secundarios = ", ".join(i["intent"] for i in intents[1:4])
        linhas.append(f"Intencoes secundarias: {secundarios}")
    if primary.get("hits"):
        linhas.append(f"Sinais detectados: {', '.join(primary['hits'])}")

    if complexity["nivel"] in ("media", "alta"):
        linhas.extend([
            "",
            "Delegacao sugerida:",
            "1. subagente_analise para dividir responsabilidades e riscos.",
            "2. subagente_codigo quando houver alteracao, revisao ou teste de codigo.",
            "3. Agente principal integra resultados, executa ferramentas e valida saidas.",
        ])
    else:
        linhas.extend([
            "",
            "Delegacao sugerida:",
            "Executar diretamente; delegar apenas se surgirem subtarefas especializadas.",
        ])

    return "\n".join(linhas)


def contexto_brasil_mundo(topico: str = "geral", quantidade: int = 5) -> str:
    """Busca contexto atualizado sobre Brasil/mundo usando plugins de noticias quando disponiveis."""
    topico = (topico or "geral").strip()
    quantidade = max(1, min(int(quantidade or 5), 10))

    try:
        if topico.lower() in ("geral", "brasil", "mundo", "tecnologia", "ciencia", "negocios"):
            fn = AVAILABLE_FUNCTIONS.get("noticias_do_momento")
            if fn:
                categoria = "geral" if topico.lower() == "brasil" else topico.lower()
                return fn(categoria=categoria, quantidade=quantidade)
        fn = AVAILABLE_FUNCTIONS.get("buscar_noticias")
        if fn:
            return fn(termo=topico, quantidade=quantidade)
    except Exception as e:
        logging.warning("Falha em contexto_brasil_mundo via plugin: %s", e)

    return web_search(f"{topico} Brasil mundo noticias recentes", max_results=quantidade)


def _autonomous_context_for_turn(messages: list) -> str:
    """Gera contexto barato e deterministico para orientar o proximo turno.

    IMPORTANTE: o texto retornado e tratado como CONTEXTO de roteamento,
    NUNCA como uma ordem para o modelo listar ou executar ferramentas.
    Modelos pequenos (ex: qwen2.5:1.5b) confundem listas de "Ferramentas
    recomendadas" com uma ordem de acao, entao aqui geramos uma instrucao
    curta e direta em segunda pessoa, sem enumerar ferramentas soltas.
    """
    from .memory_pipeline import get_memory_context_str
    user_text = _latest_user_text(messages)
    if not user_text:
        return ""

    intents = _score_intents(user_text)
    primary = intents[0] if intents else {
        "intent": "geral",
        "delegate": "subagente_analise",
        "policy": "Entender objetivo e responder diretamente em portugues.",
    }

    lines = [
        "CONTEXTO INTERNO DE ROTEAMENTO (leia, mas NAO execute nem liste "
        "ferramentas a partir daqui):",
        f"- Classificacao desta mensagem: {primary['intent']}.",
        f"- Sub-agente de apoio sugerido: {primary['delegate']}.",
        f"- Conduta: {primary['policy']}",
    ]

    intent_names = {i["intent"] for i in intents}
    if "brasil_mundo" in intent_names:
        lines.append(
            "- Se a resposta envolver fatos temporais (data, politica, economia, "
            "noticia), busque fontes atuais com contexto_brasil_mundo ou web_search "
            "ANTES de afirmar o fato."
        )
    if "codigo" in intent_names:
        lines.append(
            "- Se for alterar codigo, leia os arquivos antes e valide com teste ou "
            "execucao apos a mudanca."
        )

    memory_ctx = get_memory_context_str()
    if memory_ctx:
        lines.append("Memoria ativa relevante:\n" + memory_ctx)

    lines.append(
        "Responda ao usuario normalmente em portugues, usando ferramentas reais "
        "somente quando a tarefa exigir. Nao reproduza esta secao de contexto."
    )

    context = "\n".join(lines)
    if len(context) > AUTO_CONTEXT_MAX_CHARS:
        context = context[:AUTO_CONTEXT_MAX_CHARS] + "\n[contexto autonomo truncado]"
    return context


def _record_autonomy_event(user_text: str, assistant_text: str = "") -> None:
    """Registra sinais de autonomia sem depender de LLM."""
    if not user_text:
        return
    data = _load_json(AUTONOMY_FILE, {"turnos": 0, "intencoes": {}, "ultimos": []})
    intents = _score_intents(user_text)
    data["turnos"] = int(data.get("turnos", 0)) + 1
    for item in intents[:3]:
        name = item["intent"]
        data.setdefault("intencoes", {})[name] = int(data["intencoes"].get(name, 0)) + 1
    data.setdefault("ultimos", []).append({
        "data": datetime.now().isoformat(),
        "intencoes": [i["intent"] for i in intents[:3]] or ["geral"],
        "complexidade": _detect_complexity(user_text)["nivel"],
        "tarefa": user_text[:240],
        "resposta_preview": assistant_text[:240],
    })
    data["ultimos"] = data["ultimos"][-50:]
    _save_json(AUTONOMY_FILE, data)


def autonomia_status() -> str:
    """Mostra estatisticas do roteador autonomo e das intencoes aprendidas."""
    data = _load_json(AUTONOMY_FILE, {"turnos": 0, "intencoes": {}, "ultimos": []})
    linhas = ["--- Status da Inteligencia Autonoma ---"]
    linhas.append(f"Turnos observados: {data.get('turnos', 0)}")
    intencoes = data.get("intencoes", {})
    if intencoes:
        ordenadas = sorted(intencoes.items(), key=lambda kv: kv[1], reverse=True)
        linhas.append("Intencoes mais frequentes:")
        for nome, qtd in ordenadas[:8]:
            linhas.append(f"  - {nome}: {qtd}")
    else:
        linhas.append("Ainda sem intencoes registradas.")
    ultimos = data.get("ultimos", [])[-5:]
    if ultimos:
        linhas.append("Ultimos roteamentos:")
        for item in ultimos:
            linhas.append(f"  - {item.get('complexidade')} | {', '.join(item.get('intencoes', []))}: {item.get('tarefa', '')[:90]}")
    return "\n".join(linhas)


# =======================================================================
