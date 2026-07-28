from ._common import *
import ollama
# =======================================================================
# SISTEMA, CODIGO, WEB
# =======================================================================

def run_command(command: str, timeout: int = 30) -> str:
    """Executa um comando de terminal/shell e retorna a saida.
    timeout: segundos maximos de execucao (padrao 30).

    Usa shell=False por seguranca. Comandos com pipes/redirects devem
    ser executados via run_python_code com subprocess.
    """
    try:
        # Parse seguro do comando (evita shell injection)
        try:
            args = shlex.split(command)
        except ValueError:
            # Se shlex.split falhar (pipes, redirects), usa shell=True com WARNING
            args = command
            logging.warning("Comando com shell=True (possivel injection risk): %s", command[:100])

        result = subprocess.run(
            args,
            shell=isinstance(args, str),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip()
        if result.stderr.strip():
            output += f"\n[stderr]: {result.stderr.strip()}"
        return output or "(comando executado, sem saida)"
    except subprocess.TimeoutExpired:
        return f"Comando cancelado apos {timeout}s de execucao (timeout)."
    except Exception as e:
        return f"Erro ao executar comando: {e}"


def run_python_code(code: str, auto_fix: bool = True) -> str:
    from agente_core import _call_ollama_with_timeout, _chat_with_retries  # lazy p/ suportar patches de teste
    """Executa um trecho de codigo Python e retorna o que foi impresso (print).

    ATENCAO: Esta funcao executa codigo arbitrario. Use apenas com
    codigo confiavel ou gerado pelo proprio modelo.

    Args:
        code: String com codigo Python a ser executado
        auto_fix: Se True, tenta corrigir erros comuns automaticamente

    Returns:
        Saida capturada do print, ou mensagem de erro
    """
    buffer = io.StringIO()
    try:
        safe_builtins = {
            "abs": abs, "all": all, "any": any, "ascii": ascii,
            "bin": bin, "bool": bool, "bytearray": bytearray, "bytes": bytes,
            "chr": chr, "complex": complex, "dict": dict, "dir": dir,
            "divmod": divmod, "enumerate": enumerate, "filter": filter,
            "float": float, "format": format, "frozenset": frozenset,
            "hasattr": hasattr, "hash": hash, "hex": hex, "id": id,
            "int": int, "isinstance": isinstance, "issubclass": issubclass,
            "iter": iter, "len": len, "list": list, "map": map,
            "max": max, "min": min, "next": next, "object": object,
            "oct": oct, "ord": ord, "pow": pow, "print": print,
            "range": range, "repr": repr, "reversed": reversed,
            "round": round, "set": set, "slice": slice, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip, "True": True, "False": False, "None": None,
            "Exception": Exception, "ValueError": ValueError,
            "TypeError": TypeError, "KeyError": KeyError,
            "IndexError": IndexError, "ZeroDivisionError": ZeroDivisionError,
            "StopIteration": StopIteration, "KeyboardInterrupt": KeyboardInterrupt,
        }
        safe_globals = {
            "__name__": "__main__",
            "__builtins__": safe_builtins,
            "math": __import__("math"),
            "random": __import__("random"),
            "json": __import__("json"),
            "datetime": __import__("datetime"),
            "re": __import__("re"),
            "itertools": __import__("itertools"),
            "collections": __import__("collections"),
            "statistics": __import__("statistics"),
        }
        with contextlib.redirect_stdout(buffer):
            exec(code, safe_globals)
        output = buffer.getvalue().strip()
        return output or "(codigo executado, sem saida impressa)"
    except Exception as e:
        erro_str = str(e)
        # Turbo: auto-fix com N tentativas
        if auto_fix and TURBO_AVAILABLE and len(code) < 5000:
            for attempt in range(3):
                fixed_code = agente_turbo.code_auto_fix(code, erro_str)
                if fixed_code != code:
                    try:
                        buffer2 = io.StringIO()
                        with contextlib.redirect_stdout(buffer2):
                            exec(fixed_code, safe_globals)
                        output = buffer2.getvalue().strip()
                        return (
                            f"[Auto-fix tentativa {attempt + 1} aplicada]\n"
                            f"{output or '(codigo executado, sem saida)'}"
                        )
                    except Exception as e2:
                        code = fixed_code
                        erro_str = str(e2)
                break
        return f"Erro ao executar codigo: {e}"


def gerar_codigo(descricao: str, linguagem: str = "python", salvar_em: str = "") -> str:
    from agente_core import _call_ollama_with_timeout, _chat_with_retries  # lazy p/ suportar patches de teste
    """Gera codigo fonte a partir de descricao em linguagem natural usando IA.

    Args:
        descricao: Descricao natural do que o codigo deve fazer
        linguagem: Linguagem de programacao (python, javascript, html, css, java, c, cpp, etc.)
        salvar_em: Caminho do arquivo para salvar o codigo gerado (opcional)

    Returns:
        O codigo gerado e o caminho do arquivo se salvo
    """
    prompt = (
        f"Gere codigo {linguagem} para a seguinte tarefa. "
        "Responda APENAS com o codigo, sem explicacoes, sem markdown, sem ```.\n\n"
        f"Tarefa: {descricao}\n\n"
        f"Requisitos:\n"
        f"- Codigo completo e funcional em {linguagem}\n"
        f"- Com tratamento de erros basico\n"
        f"- Comentarios explicativos em portugues\n"
        f"- Variaveis com nomes descritivos em ingles\n"
        f"- Seguro e sem vulnerabilidades"
    )

    try:
        import ollama
        resp = _call_ollama_with_timeout(
            ollama.chat,
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": NUM_CTX, "temperature": 0.2},
        )
        codigo = resp["message"]["content"].strip()

        # Limpa marcadores markdown comuns que o modelo insiste em incluir
        for marker in ["```" + linguagem, "```python", "```javascript", "```html", "```css",
                        "```java", "```c", "```cpp", "```typescript", "```bash", "```sql",
                        "```json", "```", "`"]:
            codigo = codigo.replace(marker, "")
        codigo = codigo.strip()

        if not codigo:
            return "Erro: modelo nao gerou codigo valido."

        resultado = f"Codigo {linguagem} gerado com sucesso ({len(codigo)} caracteres).\n\n"
        resultado += codigo

        if salvar_em:
            parent = os.path.dirname(os.path.abspath(salvar_em))
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(salvar_em, "w", encoding="utf-8") as f:
                f.write(codigo)
            resultado += f"\n\nArquivo salvo em: {os.path.abspath(salvar_em)}"

        # Tenta guardar na memoria semantica se o plugin estiver disponivel
        try:
            from plugins.plugin_memoria_evolutiva import grafo_adicionar, memoria_guardar
            grafo_adicionar(linguagem, f"Codigo gerado: {descricao[:100]}")
            memoria_guardar(f"Codigo {linguagem} criado: {descricao[:200]}", categoria="codigo", importancia=4)
        except Exception:
            pass

        # Turbo: revisao e melhoria automatica do codigo gerado
        if TURBO_AVAILABLE:
            try:
                review = agente_turbo.code_review(codigo, linguagem)
                if "⚠" in review:
                    resultado += f"\n\n---\n{review}"
                    # Tenta auto-corrigir problemas graves
                    if "sintaxe" in review.lower() or "incompleto" in review.lower():
                        prompt_fix = (
                            f"O codigo abaixo tem problemas. Corrija-os e retorne APENAS "
                            f"o codigo corrigido, sem explicacoes:\n\n{codigo}"
                        )
                        try:
                            resp_fix = _call_ollama_with_timeout(
                                ollama.chat,
                                model=MODEL,
                                messages=[{"role": "user", "content": prompt_fix}],
                                options={"num_ctx": NUM_CTX, "temperature": 0.2},
                            )
                            codigo_corrigido = resp_fix["message"]["content"].strip()
                            for marker in ["```" + linguagem, "```python", "```", "`"]:
                                codigo_corrigido = codigo_corrigido.replace(marker, "")
                            codigo_corrigido = codigo_corrigido.strip()
                            if codigo_corrigido and len(codigo_corrigido) > 10:
                                codigo = codigo_corrigido
                                if salvar_em:
                                    with open(salvar_em, "w", encoding="utf-8") as f:
                                        f.write(codigo)
                                resultado += f"\n\n✅ Codigo auto-corrigido ({len(codigo)} caracteres)"
                        except Exception:
                            pass
            except Exception:
                pass

        return resultado

    except Exception as e:
        return f"Erro ao gerar codigo: {e}"


# Mapeamento seguro de operadores para eval()
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(expression: str) -> float:
    """Avalia expressao matematica de forma segura usando AST.

    Diferente de eval(), esta funcao nao executa codigo arbitrario -
    ela percorre a arvore sintatica e so permite nos de operacoes
    matematicas e numeros, bloqueando chamadas de funcao, atribuicoes
    e qualquer outro tipo de expressao.

    Args:
        expression: String com expressao matematica (ex: "(3 + 4) * 2 / 7")

    Returns:
        Resultado numerico da expressao

    Raises:
        ValueError: Se a expressao contiver operacoes nao permitidas
        ZeroDivisionError: Se houver divisao por zero
    """
    tree = ast.parse(expression.strip(), mode="eval")

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Constante nao numerica: {node.value}")
        elif isinstance(node, ast.BinOp):
            op_func = _SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Operador nao permitido: {type(node.op).__name__}")
            return op_func(_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_func = _SAFE_OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Operador unario nao permitido: {type(node.op).__name__}")
            return op_func(_eval(node.operand))
        else:
            raise ValueError(f"Expressao nao permitida: {type(node).__name__}")

    return _eval(tree.body)


def calculate(expression: str) -> str:
    """Calcula uma expressao matematica simples de forma segura.

    Usa analise de AST (arvore sintatica) em vez de eval(),
    bloqueando execucao de codigo arbitrario.

    Exemplos validos:
      "(3 + 4) * 2 / 7"
      "2 ** 8"
      "10 % 3"
      "-5 + 3"

    Args:
        expression: Expressao matematica como string

    Returns:
        Resultado como string ou mensagem de erro
    """
    try:
        result = _safe_eval(expression)
        # Se for inteiro, mostra sem casas decimais
        if result == int(result):
            return str(int(result))
        formatted = f"{result:.4f}".rstrip("0").rstrip(".")
        # Evita string vazia para numeros muito pequenos (ex: 1e-7)
        return formatted if formatted else "0"
    except ZeroDivisionError:
        return "Erro: divisao por zero nao permitida."
    except (ValueError, SyntaxError, TypeError) as e:
        return f"Expressao invalida: {e}"
    except Exception as e:
        return f"Erro ao calcular: {e}"


def get_datetime() -> str:
    """Retorna a data e hora atuais."""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def get_system_info() -> str:
    """Retorna informacoes do sistema: SO, CPU, memoria e disco."""
    try:
        info = [
            f"Sistema: {platform.system()} {platform.release()}",
            f"Processador: {platform.processor() or 'desconhecido'}",
        ]
        try:
            import psutil
            info.append(f"Uso de CPU: {psutil.cpu_percent(interval=0.5)}%")
            mem = psutil.virtual_memory()
            info.append(f"Memoria: {mem.percent}% usada ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)")
            disk = psutil.disk_usage("/")
            info.append(f"Disco: {disk.percent}% usado ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
        except ImportError:
            info.append("(instale 'psutil' para ver CPU/memoria/disco: pip install psutil)")
        return "\n".join(info)
    except Exception as e:
        return f"Erro ao obter info do sistema: {e}"


def fetch_url(url: str, max_chars: int = 5000) -> str:
    """Busca o conteudo de texto de uma URL (precisa de conexao com a internet).

    Args:
        url: URL completa a ser acessada
        max_chars: Numero maximo de caracteres a retornar (padrao: 5000)

    Returns:
        Conteudo textual da URL, truncado se necessario
    """
    try:
        import requests
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AgenteLocal/1.0)"
        })
        resp.raise_for_status()
        text = resp.text
        if len(text) > max_chars:
            return text[:max_chars] + f"\n[...conteudo truncado de {len(text):,} para {max_chars:,} caracteres...]"
        return text
    except ImportError:
        return "Instale a lib 'requests' primeiro: pip install requests"
    except Exception as e:
        return f"Erro ao buscar URL: {e}"


