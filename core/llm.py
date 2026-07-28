from ._common import *
def ensure_ollama() -> bool:
    """
    Verifica se o Ollama esta rodando e tenta iniciar automaticamente se nao estiver.
    
    Tenta conectar na API do Ollama (localhost:11434). Se falhar, tenta
    executar 'ollama serve' em background e espera alguns segundos.
    
    Returns:
        True se conseguiu conectar, False se nao foi possivel.
    """
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=3)
        return True  # Ollama ja esta rodando
    except Exception:
        pass
    
    # Tenta iniciar o Ollama
    try:
        logging.info("Ollama nao detectado. Tentando iniciar...")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        # Aguarda alguns segundos para iniciar
        for _ in range(10):
            time.sleep(1)
            try:
                req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
                urllib.request.urlopen(req, timeout=2)
                logging.info("Ollama iniciado com sucesso!")
                return True
            except Exception:
                continue
        logging.warning("Nao foi possivel iniciar o Ollama automaticamente.")
        return False
    except Exception as e:
        logging.warning("Erro ao tentar iniciar Ollama: %s", e)
        return False


def _call_ollama_with_timeout(
    func: Callable,
    *args: Any,
    timeout: Optional[float] = None,
    **kwargs: Any
) -> Any:
    """
    Roda uma chamada ao Ollama com timeout real usando uma thread DAEMON.

    Se a chamada travar (modelo nao responde, Ollama nao esta rodando, etc.),
    o programa segue em frente com um erro em vez de esperar para sempre.
    Uma thread daemon nunca impede o programa de continuar ou de fechar,
    mesmo que a chamada original fique presa para sempre em segundo plano
    (o sistema operacional a encerra quando o processo termina).

    Args:
        func: Funcao a ser chamada (ex: ollama.chat)
        timeout: Tempo maximo de espera em segundos (padrao: OLLAMA_TIMEOUT_SECONDS)
        *args, **kwargs: Repassados para func

    Returns:
        O valor retornado por func

    Raises:
        TimeoutError: Se a chamada exceder o timeout
        Exception: Qualquer excecao levantada por func
    """
    if timeout is None:
        timeout = OLLAMA_TIMEOUT_SECONDS

    result_box: dict = {}

    def _target() -> None:
        try:
            result_box["value"] = func(*args, **kwargs)
        except Exception as e:
            result_box["error"] = e

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logging.error("Timeout esperando resposta do Ollama (%ss)", timeout)
        raise TimeoutError(
            f"O modelo nao respondeu em {timeout}s. Verifique se o Ollama esta "
            "rodando (comando 'ollama serve') e se o modelo foi baixado."
        )

    if "error" in result_box:
        raise result_box["error"]

    return result_box.get("value")


def _stream_chat(model: str, messages: list, tools: list, on_token=None, on_tool=None):
    """
    Versao com streaming de tokens do ollama.chat.

    Args:
        model: nome do modelo.
        messages: historico ja limpo.
        tools: lista de ferramentas (igual a _chat_with_retries).
        on_token(callable): recebe cada pedaco de texto (str) assim que chega.
        on_tool(callable): opcional; se o modelo retornar tool_calls num chunk,
            recebe (nome, args) — usado para feedback em tempo real.

    Retorna o mesmo dict de resposta de ollama.chat (message com content +
    tool_calls), montado a partir do stream.
    """
    import ollama

    messages = _clean_messages(messages)
    last_error = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 2):
        try:
            stream = ollama.chat(
                model=model,
                messages=messages,
                tools=tools,
                keep_alive=OLLAMA_KEEP_ALIVE,
                options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
                stream=True,
            )
            content_parts = []
            tool_calls = []
            last_message = None
            for chunk in stream:
                last_message = chunk
                msg = chunk.get("message", {})
                delta = msg.get("content")
                if delta:
                    content_parts.append(delta)
                    if on_token:
                        try:
                            on_token(delta)
                        except Exception:
                            pass
                # Alguns modelos emitem tool_calls dentro do chunk.
                tc = msg.get("tool_calls")
                if tc:
                    if on_tool:
                        try:
                            for call in tc:
                                fn = call.get("function", {})
                                on_tool(fn.get("name"), fn.get("arguments"))
                        except Exception:
                            pass
                    # Acumula tool_calls (pode vir fragmentado).
                    tool_calls.extend(tc)
            # Monta resposta final no formato esperado por run_agent_turn.
            final_msg = dict(last_message.get("message", {})) if last_message else {}
            final_msg["content"] = "".join(content_parts)
            if tool_calls:
                final_msg["tool_calls"] = tool_calls
            return {"message": final_msg}
        except TimeoutError as e:
            last_error = e
            logging.warning("Stream tentativa %s falhou por timeout.", attempt)
        except Exception as e:
            last_error = e
            logging.warning("Stream tentativa %s falhou: %s", attempt, e)
            time.sleep(1.5 * attempt)
    raise RuntimeError(
        f"Nao consegui falar com o modelo '{model}' apos {OLLAMA_MAX_RETRIES + 1} "
        f"tentativas (stream). Ultimo erro: {last_error}"
    )


def _clean_messages(messages):
    """Remove campos extras (timestamp, etc.) que o Ollama nao aceita."""
    allowed = {"role", "content", "tool_calls", "tool_call_id"}
    cleaned = []
    for m in messages:
        if isinstance(m, dict):
            cleaned.append({k: v for k, v in m.items() if k in allowed})
        else:
            cleaned.append({k: getattr(m, k, None) for k in allowed if getattr(m, k, None) is not None})
    return cleaned


def _chat_with_retries(model: str, messages: list, tools: list) -> Any:
    """Chama ollama.chat com retentativas e mensagens de erro claras."""
    import ollama

    messages = _clean_messages(messages)

    last_error = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 2):
        try:
            return _call_ollama_with_timeout(
                ollama.chat,
                model=model,
                messages=messages,
                tools=tools,
                keep_alive=OLLAMA_KEEP_ALIVE,
                options={"num_ctx": NUM_CTX, "temperature": TEMPERATURE},
            )
        except TimeoutError as e:
            last_error = e
            logging.warning("Tentativa %s falhou por timeout.", attempt)
        except Exception as e:
            last_error = e
            logging.warning("Tentativa %s falhou: %s", attempt, e)
            time.sleep(1.5 * attempt)  # espera progressiva antes de tentar de novo
    raise RuntimeError(
        f"Nao consegui falar com o modelo '{model}' apos {OLLAMA_MAX_RETRIES + 1} "
        f"tentativas. Ultimo erro: {last_error}\n"
        "Verifique: 1) o Ollama esta rodando? 2) o modelo foi baixado "
        f"(ollama pull {model})? 3) o nome do modelo em MODEL esta certo?"
    )


