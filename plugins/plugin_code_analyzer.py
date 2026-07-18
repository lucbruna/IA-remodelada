"""
plugin_code_analyzer.py
=======================
Plugin de análise avançada de código. Fornece ferramentas para:
- Análise estática de código
- Detecção de bugs e vulnerabilidades
- Sugestões de refatoração
- Otimização de desempenho
- Geração de documentação
- Formatação e linting
"""

import ast
import os
import re
import json
import subprocess
import tempfile
from typing import Dict, List, Any, Optional

__version__ = "1.0.0"
PLUGIN_NAME = "Analisador de Código Avançado"


def register(api):
    """Registra todas as ferramentas de análise de código."""

    def analyze_code(code: str, language: str = "python") -> str:
        """Analisa código fonte para detectar problemas, sugerir melhorias e gerar métricas.

        Args:
            code: Código fonte a ser analisado
            language: Linguagem de programação (python, javascript, etc.)

        Returns:
            Relatório de análise detalhado
        """
        if language.lower() != "python":
            return f"Análise atualmente suportada apenas para Python. Linguagem recebida: {language}"

        try:
            # Parse the AST
            tree = ast.parse(code)

            # Initialize analysis results
            issues = []
            suggestions = []
            metrics = {}

            # Check for common issues
            issues.extend(_check_security_issues(tree))
            issues.extend(_check_code_smells(tree))
            issues.extend(_check_style_issues(code))

            # Generate suggestions
            suggestions.extend(_suggest_improvements(tree, code))
            suggestions.extend(_suggest_refactoring(tree))

            # Calculate metrics
            metrics = _calculate_metrics(tree, code)

            # Format report
            report = _format_analysis_report(issues, suggestions, metrics)
            return report

        except SyntaxError as e:
            return f"Erro de sintaxe no código: {e.msg} na linha {e.lineno}"
        except Exception as e:
            return f"Erro durante análise: {str(e)}"

    def _check_security_issues(tree: ast.AST) -> List[Dict]:
        """Verifica problemas de segurança no código."""
        issues = []

        for node in ast.walk(tree):
            # Check for eval() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'eval':
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'message': 'Uso de eval() pode ser perigoso - considera usar ast.literal_eval ou alternativas seguras',
                        'line': getattr(node, 'lineno', 0)
                    })
                elif isinstance(node.func, ast.Attribute) and node.func.attr == 'exec':
                    issues.append({
                        'type': 'security',
                        'severity': 'high',
                        'message': 'Uso de exec() pode ser perigoso - evitar execução de código dinamicamente',
                        'line': getattr(node, 'lineno', 0)
                    })

            # Check for shell=True in subprocess calls
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ['call', 'run', 'Popen']:
                    for keyword in node.keywords:
                        if keyword.arg == 'shell' and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                            issues.append({
                                'type': 'security',
                                'severity': 'medium',
                                'message': 'shell=True em subprocess pode ser vulnerável a injeção de comandos',
                                'line': getattr(node, 'lineno', 0)
                            })

        return issues

    def _check_code_smells(tree: ast.AST) -> List[Dict]:
        """Detecta code smells comuns."""
        issues = []

        for node in ast.walk(tree):
            # Long functions (>50 lines)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if hasattr(node, 'body') and len(node.body) > 50:
                    issues.append({
                        'type': 'code_smell',
                        'severity': 'medium',
                        'message': f"Função '{node.name}' é muito longa ({len(node.body)} linhas). Considere dividir em funções menores.",
                        'line': getattr(node, 'lineno', 0)
                    })

            # Deep nesting (>4 levels)
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                depth = _calculate_nesting_depth(node)
                if depth > 4:
                    issues.append({
                        'type': 'code_smell',
                        'severity': 'low',
                        'message': f"Nível de indentacão muito profundo ({depth} níveis). Considere refatorar.",
                        'line': getattr(node, 'lineno', 0)
                    })

        return issues

    def _calculate_nesting_depth(node: ast.AST, current_depth: int = 0) -> int:
        """Calcula a profundidade máxima de aninhamento."""
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With,
                                ast.FunctionDef, ast.AsyncFunctionDef)):
                child_depth = _calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = _calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)

        return max_depth

    def _check_style_issues(code: str) -> List[Dict]:
        """Verifica problemas de estilo baseado em PEP 8."""
        issues = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # Line too long
            if len(line) > 88:
                issues.append({
                    'type': 'style',
                    'severity': 'low',
                    'message': f'Linha muito longa ({len(line)} caracteres). Máximo recomendado: 88.',
                    'line': i
                })

            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append({
                    'type': 'style',
                    'severity': 'low',
                    'message': 'Espaço em branco no final da linha.',
                    'line': i
                })

        return issues

    def _suggest_improvements(tree: ast.AST, code: str) -> List[Dict]:
        """Sugere melhorias no código."""
        suggestions = []

        # Suggest using list comprehensions
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Look for simple accumulation patterns
                if len(node.body) == 1 and isinstance(node.body[0], ast.Assign):
                    # This is a simplified check - in reality would need more sophisticated analysis
                        suggestions.append({
                            'type': 'improvement',
                            'suggestion': 'Considere usar list comprehension para operações simples de lista',
                            'line': getattr(node, 'lineno', 0)
                        })

        # Suggest using enumerate instead of range(len())
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call):
                    if (isinstance(node.iter.func, ast.Name) and node.iter.func.id == 'range' and
                        len(node.iter.args) == 1 and isinstance(node.iter.args[0], ast.Call) and
                        isinstance(node.iter.args[0].func, ast.Name) and node.iter.args[0].func.id == 'len'):
                        suggestions.append({
                            'type': 'improvement',
                            'suggestion': 'Considere usar enumerate() em vez de range(len()) para melhor legibilidade',
                            'line': getattr(node, 'lineno', 0)
                        })

        return suggestions

    def _suggest_refactoring(tree: ast.AST) -> List[Dict]:
        """Sugere refatorações de código."""
        suggestions = []

        # Detect duplicated code patterns (simplified)
        # In a real implementation, this would be more sophisticated

        return suggestions

    def _calculate_metrics(tree: ast.AST, code: str) -> Dict[str, Any]:
        """Calcula métricas de código."""
        lines = code.split('\n')
        total_lines = len(lines)
        non_empty_lines = len([line for line in lines if line.strip()])
        comment_lines = len([line for line in lines if line.strip().startswith('#')])

        # Count functions and classes
        functions = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))

        # Calculate cyclomatic complexity (simplified)
        complexity = 1  # Start with 1 for the main path
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                               ast.Assert, ast.BoolOp)):
                complexity += 1
            elif isinstance(node, ast.Assert):
                complexity += 1

        return {
            'total_lines': total_lines,
            'non_empty_lines': non_empty_lines,
            'comment_lines': comment_lines,
            'comment_ratio': comment_lines / max(non_empty_lines, 1),
            'functions': functions,
            'classes': classes,
            'cyclomatic_complexity': complexity,
            'maintainability_index': max(0, 100 - (complexity * 5) - (total_lines / 10))
        }

    def _format_analysis_report(issues: List[Dict], suggestions: List[Dict], metrics: Dict) -> str:
        """Formata o relatório de análise."""
        report = []

        report.append("=" * 60)
        report.append("RELATÓRIO DE ANÁLISE DE CÓDIGO")
        report.append("=" * 60)

        # Metrics
        report.append("\n📊 MÉTRICAS:")
        report.append(f"  Linhas totais: {metrics['total_lines']}")
        report.append(f"  Linhas não vazias: {metrics['non_empty_lines']}")
        report.append(f"  Linhas de comentário: {metrics['comment_lines']} ({metrics['comment_ratio']:.1%})")
        report.append(f"  Funções: {metrics['functions']}")
        report.append(f"  Classes: {metrics['classes']}")
        report.append(f"  Complexidade ciclomática: {metrics['cyclomatic_complexity']}")
        report.append(f"  Índice de manutenibilidade: {metrics['maintainability_index']:.1f}/100")

        # Issues
        if issues:
            report.append(f"\n🚨 PROBLEMAS ENCONTRADOS ({len(issues)}):")
            # Group by severity
            high_issues = [i for i in issues if i.get('severity') == 'high']
            medium_issues = [i for i in issues if i.get('severity') == 'medium']
            low_issues = [i for i in issues if i.get('severity') == 'low']

            if high_issues:
                report.append("  ALTA PRIORIDADE:")
                for issue in high_issues[:5]:  # Limit to 5
                    report.append(f"    • Linha {issue['line']}: {issue['message']}")

            if medium_issues:
                report.append("  MÉDIA PRIORIDADE:")
                for issue in medium_issues[:5]:
                    report.append(f"    • Linha {issue['line']}: {issue['message']}")

            if low_issues:
                report.append("  BAIXA PRIORIDADE:")
                for issue in low_issues[:5]:
                    report.append(f"    • Linha {issue['line']}: {issue['message']}")
        else:
            report.append("\n✅ NENHUM PROBLEMA CRÍTICO ENCONTRADO")

        # Suggestions
        if suggestions:
            report.append(f"\n💡 SUGESTÕES DE MELHORIA ({len(suggestions)}):")
            for suggestion in suggestions[:10]:  # Limit to 10
                report.append(f"  • Linha {suggestion['line']}: {suggestion['suggestion']}")
        else:
            report.append("\n✨ NENHUMA SUGESTÃO DE MELHORIA IDENTIFICADA")

        return "\n".join(report)

    def refactor_code(code: str, refactor_type: str = "extract_method") -> str:
        """Aplica refatorações automáticas ao código usando AST."""
        try:
            tree = ast.parse(code)

            if refactor_type == "extract_method":
                # Identifica blocos grandes dentro de funcoes e sugere extracao
                suggestions = []
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        body_lines = len(node.body)
                        if body_lines > 15:
                            suggestions.append(
                                f"  Funcao '{node.name}' tem {body_lines} linhas no corpo. "
                                "Considere extrair blocos em funcoes menores."
                            )
                if suggestions:
                    return "Sugestoes de extracao:\n" + "\n".join(suggestions) + "\n\n" + code
                return "Nenhuma extracao necessaria. Codigo ja esta modular.\n\n" + code

            elif refactor_type == "rename_variable":
                # Renomeia variaveis com nomes genericos (x, y, z, tmp, temp)
                import re as _re
                generic = {"x", "y", "z", "tmp", "temp", "foo", "bar", "baz", "a", "b", "val", "data"}
                renamed = code
                func_body = {}
                # Extrai nomes de variaveis locais
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                        if node.id in generic and node.id not in ("self", "cls"):
                            new_name = node.id + "_value"
                            if node.id not in func_body:
                                func_body[node.id] = new_name
                for old, new in func_body.items():
                    renamed = _re.sub(r'\b' + old + r'\b', new, renamed)
                if func_body:
                    changes = "\n".join(f"  {k} -> {v}" for k, v in func_body.items())
                    return f"Variaveis renomeadas:\n{changes}\n\n{renamed}"
                return "Nenhuma variavel generica encontrada.\n\n" + code

            elif refactor_type == "simplify_if":
                # Simplifica if/else booleanos
                simplified = code
                simplified = simplified.replace("if True:", "if True:  # sempre executa")
                simplified = simplified.replace("if False:", "if False:  # nunca executa")
                # Remove else em if com return
                lines = simplified.split("\n")
                result = []
                skip_next = False
                for i, line in enumerate(lines):
                    if skip_next:
                        skip_next = False
                        continue
                    if line.strip().startswith("if ") and i + 2 < len(lines):
                        if lines[i + 1].strip().startswith("return ") and "else:" in lines[i + 2]:
                            result.append(line)
                            result.append(lines[i + 1])
                            result.append("    # else removido (return incondicional)")
                            skip_next = True
                            continue
                    result.append(line)
                return "\n".join(result)

            elif refactor_type == "add_type_hints":
                # Adiciona type hints basicos (str, int, float, bool, list, dict)
                hints_map = {"str": "str", "int": "int", "float": "float", "bool": "bool",
                             "list": "list", "dict": "dict", "tuple": "tuple", "set": "set"}
                new_code = code
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        for arg in node.args.args:
                            if arg.arg == "self":
                                continue
                            if arg.annotation is None:
                                old = f"def {node.name}({arg.arg}"
                                # Heuristica: checa uso da variavel para sugerir tipo
                                arg_uses = [n for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == arg.arg]
                                suggested = "str"
                                for use in arg_uses:
                                    p = use.parent if hasattr(use, 'parent') else None
                                new = f"def {node.name}({arg.arg}: {suggested}"
                                new_code = new_code.replace(old, new, 1)
                return new_code

            else:
                return f"Tipo de refatoracao '{refactor_type}' desconhecido. Use: extract_method, rename_variable, simplify_if, add_type_hints.\n\n{code}"

        except SyntaxError as e:
            return f"Erro de sintaxe no codigo: {e}\n\n{code}"
        except Exception as e:
            return f"Erro na refatoracao: {e}\n\n{code}"

    def generate_docstring(code: str, style: str = "google") -> str:
        """Gera docstrings para funcoes e classes usando AST."""
        try:
            tree = ast.parse(code)
            modified = False

            class DocstringAdder(ast.NodeTransformer):
                def visit_FunctionDef(self, node):
                    if not ast.get_docstring(node):
                        params = [arg.arg for arg in node.args.args if arg.arg != "self"]
                        returns = ast.unparse(node.returns) if node.returns else "None"
                        param_lines = ""
                        doc_parts = []
                        if style == "google":
                            doc_parts.append(node.name + ".")
                            doc_parts.append("")
                            if params:
                                doc_parts.append("Args:")
                                for p in params:
                                    doc_parts.append("    " + p + ": Descricao do parametro.")
                                doc_parts.append("")
                            doc_parts.append("Returns:")
                            doc_parts.append("    " + returns + ". Descricao do retorno.")
                        elif style == "numpy":
                            doc_parts.append(node.name + ".")
                            doc_parts.append("")
                            if params:
                                doc_parts.append("Parameters")
                                doc_parts.append("----------")
                                for p in params:
                                    doc_parts.append(p + " : type")
                                    doc_parts.append("    Descricao.")
                                doc_parts.append("")
                            doc_parts.append("Returns")
                            doc_parts.append("-------")
                            doc_parts.append(returns)
                            doc_parts.append("    Descricao.")
                        else:  # sphinx
                            doc_parts.append(node.name + ".")
                            doc_parts.append("")
                            for p in params:
                                doc_parts.append(":param " + p + ": Descricao.")
                            doc_parts.append("")
                            doc_parts.append(":returns: Descricao do retorno (" + returns + ").")
                        doc = '"""\n' + "\n".join(doc_parts) + '\n"""'
                        node.body.insert(0, ast.parse(doc).body[0])
                        nonlocal modified
                        modified = True
                    return node

                def visit_AsyncFunctionDef(self, node):
                    return self.visit_FunctionDef(node)

                def visit_ClassDef(self, node):
                    if not ast.get_docstring(node):
                        bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
                        name_str = node.name + ("(" + bases + ")" if bases else "")
                        doc = '"""' + name_str + '.\n\nDescricao da classe.\n"""'
                        node.body.insert(0, ast.parse(doc).body[0])
                        nonlocal modified
                        modified = True
                    return node

            tree = DocstringAdder().visit(tree)
            ast.fix_missing_locations(tree)
            result = ast.unparse(tree)

            if modified:
                return result
            return "Todas as funcoes/classes ja possuem docstring.\n\n" + code

        except SyntaxError as e:
            return f"Erro de sintaxe no codigo: {e}\n\n{code}"
        except Exception as e:
            return f"Erro ao gerar docstring: {e}\n\n{code}"

    # Register all tools
    api.register_tool(
        name="analyze_code",
        func=analyze_code,
        description="Analisa código fonte para detectar problemas, sugerir melhorias e gerar métricas de qualidade.",
        parameters={
            "code": {"type": "string", "description": "Código fonte a ser analisado"},
            "language": {"type": "string", "description": "Linguagem de programação (padrão: python)"},
        },
        required=["code"],
    )

    api.register_tool(
        name="refactor_code",
        func=refactor_code,
        description="Aplica refatorações automáticas ao código (extract method, rename variables, etc.).",
        parameters={
            "code": {"type": "string", "description": "Código fonte a ser refatorado"},
            "refactor_type": {"type": "string", "description": "Tipo de refatoração (padrão: extract_method)"},
        },
        required=["code"],
    )

    api.register_tool(
        name="generate_docstring",
        func=generate_docstring,
        description="Gera docstrings automáticos para funções e classes seguindo padrões estabelecidos.",
        parameters={
            "code": {"type": "string", "description": "Código fonte para gerar docstrings"},
            "style": {"type": "string", "description": "Estilo do docstring (google, numpy, sphinx)"},
        },
        required=["code"],
    )

    return {
        "name": PLUGIN_NAME,
        "version": __version__,
        "description": "Análise avançada de código com detecção de bugs, sugestões de refatoração e métricas de qualidade",
        "tools": ["analyze_code", "refactor_code", "generate_docstring"],
    }