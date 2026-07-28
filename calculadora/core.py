"""core.py - Lógica principal da Calculadora.

Fornece:
    - Operações matemáticas básicas (soma, subtração, multiplicação, divisão)
    - Validação de entrada
    - Histórico de operações
    - Formatação de números
    - Operações avançadas (porcentagem, raiz quadrada, potência)
"""

import math
import operator
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum


class Operacao(Enum):
    """Enum com as operações suportadas pela calculadora."""
    SOMA = "+"
    SUBTRACAO = "-"
    MULTIPLICACAO = "×"
    DIVISAO = "÷"
    PORCENTAGEM = "%"
    POTENCIA = "^"
    RAIZ = "√"
    SENO = "sin"
    COSSENO = "cos"
    TANGENTE = "tan"
    LOGARITMO = "log"
    LOG_NATURAL = "ln"
    EXP = "exp"
    ABS = "abs"
    FATORIAL = "fact"
    INVERSO = "inv"
    PI = "π"


# Mapeamento de operadores para funções matemáticas
OPERACOES_FUNC: dict[Operacao, Callable[[float, float], float]] = {
    Operacao.SOMA: operator.add,
    Operacao.SUBTRACAO: operator.sub,
    Operacao.MULTIPLICACAO: operator.mul,
    Operacao.DIVISAO: operator.truediv,
    Operacao.POTENCIA: operator.pow,
}


@dataclass
class HistoricoItem:
    """Um item no histórico de operações."""
    expressao: str
    resultado: str
    timestamp: str = ""


@dataclass
class Calculadora:
    """Calculadora com suporte a operações básicas e memória.

    Attributes:
        memoria: Valor armazenado na memória.
        historico: Lista de operações realizadas.
        precisao: Casas decimais para formatação.
        angulo_modo: Modo angular ('deg' ou 'rad') para funções trigonométricas.
    """
    memoria: float = 0.0
    historico: list[HistoricoItem] = field(default_factory=list)
    precisao: int = 10
    angulo_modo: str = "deg"

    def calcular(self, a: float, b: float, operacao: Operacao) -> float:
        """Executa uma operação entre dois números.

        Args:
            a: Primeiro operando.
            b: Segundo operando.
            operacao: Operação a ser executada.

        Returns:
            Resultado da operação.

        Raises:
            ValueError: Se a operação não for suportada.
            ZeroDivisionError: Se tentar divisão por zero.
        """
        if operacao == Operacao.DIVISAO and b == 0:
            raise ZeroDivisionError("Divisão por zero não permitida")

        # Verifica se a operação é válida
        if not isinstance(operacao, Operacao):
            raise ValueError(f"Operação inválida: {operacao}. Use os valores de Operacao.")

        func = OPERACOES_FUNC.get(operacao)
        if func is None:
            raise ValueError(f"Operação não suportada: {operacao.value}")

        resultado = func(a, b)

        # Registrar no histórico
        expr = f"{formatar_numero(a)} {operacao.value} {formatar_numero(b)}"
        self._registrar_historico(expr, resultado)

        return resultado

    def calcular_unico(self, valor: float, operacao: Operacao) -> float:
        """Executa operação com um único operando (ex: √, sin, cos, log).

        Args:
            valor: Operando.
            operacao: Operação a ser executada.

        Returns:
            Resultado da operação.

        Raises:
            ValueError: Se a operação ou o valor forem inválidos.
        """
        if operacao == Operacao.RAIZ:
            if valor < 0:
                raise ValueError("Raiz quadrada de número negativo")
            resultado = math.sqrt(valor)
        elif operacao == Operacao.PORCENTAGEM:
            resultado = valor / 100.0
        elif operacao == Operacao.SENO:
            resultado = math.sin(self._converter_angulo(valor))
        elif operacao == Operacao.COSSENO:
            resultado = math.cos(self._converter_angulo(valor))
        elif operacao == Operacao.TANGENTE:
            # Verifica ângulos onde tan é indefinida
            self._verificar_tangente(valor)
            resultado = math.tan(self._converter_angulo(valor))
        elif operacao == Operacao.LOGARITMO:
            if valor <= 0:
                raise ValueError("Logaritmo de número não positivo")
            resultado = math.log10(valor)
        elif operacao == Operacao.LOG_NATURAL:
            if valor <= 0:
                raise ValueError("Logaritmo natural de número não positivo")
            resultado = math.log(valor)
        elif operacao == Operacao.EXP:
            resultado = math.exp(valor)
        elif operacao == Operacao.ABS:
            resultado = abs(valor)
        elif operacao == Operacao.FATORIAL:
            if valor < 0 or valor != int(valor):
                raise ValueError("Fatorial definido apenas para inteiros não negativos")
            resultado = float(math.factorial(int(valor)))
        elif operacao == Operacao.INVERSO:
            if valor == 0:
                raise ZeroDivisionError("Inverso de zero não definido")
            resultado = 1.0 / valor
        else:
            raise ValueError(f"Operação unária não suportada: {operacao.value}")

        # Formata label da expressão
        if operacao == Operacao.EXP:
            expr = f"exp({formatar_numero(valor)})"
        elif operacao == Operacao.ABS:
            expr = f"|{formatar_numero(valor)}|"
        elif operacao == Operacao.FATORIAL:
            expr = f"{formatar_numero(valor)}!"
        elif operacao == Operacao.INVERSO:
            expr = f"1/{formatar_numero(valor)}"
        else:
            expr = f"{operacao.value}({formatar_numero(valor)})"
        self._registrar_historico(expr, resultado)
        return resultado

    def _registrar_historico(self, expressao: str, resultado: float):
        """Adiciona uma operação ao histórico."""
        from datetime import datetime
        item = HistoricoItem(
            expressao=expressao,
            resultado=formatar_numero(resultado),
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        self.historico.append(item)
        # Mantém apenas os últimos 50 itens
        if len(self.historico) > 50:
            self.historico = self.historico[-50:]

    def limpar_historico(self):
        """Limpa todo o histórico de operações."""
        self.historico.clear()

    def ultimo_resultado(self) -> Optional[float]:
        """Retorna o último resultado calculado, ou None se vazio."""
        if not self.historico:
            return None
        try:
            return float(self.historico[-1].resultado)
        except (ValueError, IndexError):
            return None

    # ─── Modo angular ────────────────────────────────────────────

    def _converter_angulo(self, valor: float) -> float:
        """Converte o ângulo para radianos conforme o modo atual."""
        if self.angulo_modo == "rad":
            return valor  # já está em radianos
        return math.radians(valor)  # graus → radianos

    def _verificar_tangente(self, valor: float):
        """Verifica se a tangente é indefinida para o ângulo dado.
        Em graus: 90°, 270°; em radianos: π/2, 3π/2."""
        if self.angulo_modo == "rad":
            # Verifica proximidade de π/2 e 3π/2
            meio_pi = math.pi / 2
            mod = valor % math.pi
            if abs(mod - meio_pi) < 1e-10:
                raise ValueError("Tangente indefinida para este ângulo")
        else:
            ang_mod = valor % 180
            if abs(ang_mod - 90) < 1e-10:
                raise ValueError("Tangente indefinida para este ângulo")

    # ─── Operações de memória ───────────────────────────────────

    def memoria_guardar(self, valor: float):
        """Guarda um valor na memória."""
        self.memoria = valor

    def memoria_limpar(self):
        """Limpa o valor da memória."""
        self.memoria = 0.0

    def memoria_somar(self, valor: float):
        """Soma um valor ao valor atual da memória."""
        self.memoria += valor

    def memoria_subtrair(self, valor: float):
        """Subtrai um valor do valor atual da memória."""
        self.memoria -= valor


def formatar_numero(valor: float) -> str:
    """Formata um número para exibição, removendo decimais desnecessários.

    Args:
        valor: Número a ser formatado.

    Returns:
        String formatada (ex: "1.234" ou "1.234,56").
    """
    if isinstance(valor, float):
        if valor == int(valor) and not abs(valor) > 1e15:
            return f"{int(valor)}"
        # Limita a 10 casas decimais
        return f"{valor:.10g}"
    return str(valor)


def validar_expressao(expressao: str) -> bool:
    """Valida se uma expressão matemática é segura para avaliação.

    Args:
        expressao: String com a expressão.

    Returns:
        True se a expressão é válida, False caso contrário.
    """
    if not expressao or not expressao.strip():
        return False

    # Caracteres permitidos
    permitidos = set("0123456789.,+-*/%()^√ \t")
    for char in expressao:
        if char not in permitidos:
            return False

    # Verifica parênteses balanceados
    count = 0
    for char in expressao:
        if char == '(':
            count += 1
        elif char == ')':
            count -= 1
        if count < 0:
            return False

    return count == 0


# ═══════════════════════════════════════════════════════════════════
# Avaliador de Expressões (precedência de operadores)
# ═══════════════════════════════════════════════════════════════════

from enum import Enum as _Enum
from dataclasses import dataclass as _dataclass


class _TokenType(_Enum):
    NUMBER = "NUMBER"
    ADD = "+"
    SUB = "-"
    MUL = "×"
    DIV = "÷"
    POW = "^"
    SQRT = "√"
    PERCENT = "%"
    LPAREN = "("
    RPAREN = ")"
    SIN = "sin"
    COS = "cos"
    TAN = "tan"
    LOG = "log"
    LN = "ln"
    EXP = "exp"
    ABS = "abs"
    FACT = "!"
    INV = "inv"
    PI = "π"
    EOF = "EOF"


@_dataclass
class _Token:
    type: _TokenType
    value: float | None = None

    def __repr__(self):
        if self.value is not None:
            return f"Token({self.type.value}, {self.value})"
        return f"Token({self.type.value})"


def _tokenizar(expr: str) -> list[_Token]:
    """Converte uma expressão string em lista de tokens."""
    tokens: list[_Token] = []
    i = 0
    while i < len(expr):
        ch = expr[i]

        # Espaços
        if ch in " \t":
            i += 1
            continue

        # Números
        if ch.isdigit() or (ch == '.' and i + 1 < len(expr) and expr[i + 1].isdigit()):
            start = i
            i += 1
            while i < len(expr) and (expr[i].isdigit() or expr[i] == '.'):
                i += 1
            tokens.append(_Token(_TokenType.NUMBER, float(expr[start:i])))
            continue

        # Operadores de um carácter
        if ch == '+':
            tokens.append(_Token(_TokenType.ADD))
        elif ch == '-':
            tokens.append(_Token(_TokenType.SUB))
        elif ch == '×':
            tokens.append(_Token(_TokenType.MUL))
        elif ch == '*':
            tokens.append(_Token(_TokenType.MUL))
        elif ch == '÷':
            tokens.append(_Token(_TokenType.DIV))
        elif ch == '/':
            tokens.append(_Token(_TokenType.DIV))
        elif ch == '^':
            tokens.append(_Token(_TokenType.POW))
        elif ch == '√':
            tokens.append(_Token(_TokenType.SQRT))
        elif ch == '%':
            tokens.append(_Token(_TokenType.PERCENT))
        elif ch == '(':
            tokens.append(_Token(_TokenType.LPAREN))
        elif ch == ')':
            tokens.append(_Token(_TokenType.RPAREN))
        elif ch == '!':
            tokens.append(_Token(_TokenType.FACT))
        elif ch == 'π':
            tokens.append(_Token(_TokenType.PI, math.pi))
        elif ch.isalpha():
            start = i
            i += 1
            while i < len(expr) and expr[i].isalpha():
                i += 1
            nome = expr[start:i]
            mapeamento = {
                "sin": _TokenType.SIN,
                "cos": _TokenType.COS,
                "tan": _TokenType.TAN,
                "log": _TokenType.LOG,
                "ln": _TokenType.LN,
                "exp": _TokenType.EXP,
                "abs": _TokenType.ABS,
                "inv": _TokenType.INV,
                "sqrt": _TokenType.SQRT,
                "pi": _TokenType.PI,
            }
            if nome in mapeamento:
                if nome == "pi":
                    tokens.append(_Token(mapeamento[nome], math.pi))
                else:
                    tokens.append(_Token(mapeamento[nome]))
            else:
                raise ValueError(f"Função desconhecida: '{nome}'")
            continue
        else:
            raise ValueError(f"Caractere inesperado: '{ch}'")

        i += 1

    tokens.append(_Token(_TokenType.EOF))
    return tokens


class _Parser:
    """Parser recursivo descendente com precedência de operadores.

    Gramática:
        expression = term (("+" | "-") term)*
        term       = unary (("×" | "÷") unary)*
        unary      = ("-" | "+" | "√" | "%" | função) unary | power
        power      = primary ("^" power)*
        primary    = NUMBER | "(" expression ")"
    """

    def __init__(self, tokens: list[_Token], modo_angulo: str = "deg"):
        self.tokens = tokens
        self.pos = 0
        self.modo_angulo = modo_angulo

    def _peek(self) -> _TokenType:
        return self.tokens[self.pos].type

    def _consumir(self, esperado: _TokenType | None = None) -> _Token:
        token = self.tokens[self.pos]
        if esperado is not None and token.type != esperado:
            raise ValueError(
                f"Esperava '{esperado.value}', obteve '{token.type.value}'"
            )
        self.pos += 1
        return token

    def parse(self) -> float:
        """Avalia a expressão completa."""
        resultado = self._expression()
        if self._peek() != _TokenType.EOF:
            restantes = [t.type.value for t in self.tokens[self.pos:-1]]
            raise ValueError(f"Tokens inesperados: {' '.join(restantes)}")
        return resultado

    def _expression(self) -> float:
        """Gerencia + e - (precedência mais baixa)."""
        result = self._term()
        while self._peek() in (_TokenType.ADD, _TokenType.SUB):
            op = self._consumir()
            right = self._term()
            if op.type == _TokenType.ADD:
                result += right
            else:
                result -= right
        return result

    def _term(self) -> float:
        """Gerencia × e ÷."""
        result = self._unary()
        while self._peek() in (_TokenType.MUL, _TokenType.DIV):
            op = self._consumir()
            right = self._unary()
            if op.type == _TokenType.MUL:
                result *= right
            else:
                if right == 0:
                    raise ZeroDivisionError("Divisão por zero não permitida")
                result /= right
        return result

    def _unary(self) -> float:
        """Gerencia operadores prefixo: +, -, √, %, sin(), cos(), etc."""
        tok = self._peek()

        # Sinais unários
        if tok == _TokenType.ADD:
            self._consumir()
            return self._unary()
        if tok == _TokenType.SUB:
            self._consumir()
            return -self._unary()

        # √ e % como prefixo
        if tok == _TokenType.SQRT:
            self._consumir()
            arg = self._unary()
            if arg < 0:
                raise ValueError("Raiz quadrada de número negativo")
            return math.sqrt(arg)

        # % agora é tratado em _power() como postfixo

        # Funções científicas: sin(...), cos(...), tan(...), log(...), ln(...), exp(...), abs(...)
        if tok in (_TokenType.SIN, _TokenType.COS, _TokenType.TAN,
                   _TokenType.LOG, _TokenType.LN, _TokenType.EXP,
                   _TokenType.ABS, _TokenType.INV):
            return self._funcao()

        # Power e primary
        return self._power()

    def _funcao(self) -> float:
        """Processa sin(expr), cos(expr), tan(expr), log(expr), ln(expr)."""
        func = self._consumir()
        self._consumir(_TokenType.LPAREN)
        arg = self._expression()
        self._consumir(_TokenType.RPAREN)

        if func.type == _TokenType.SIN:
            return math.sin(self._conv_ang(arg))
        elif func.type == _TokenType.COS:
            return math.cos(self._conv_ang(arg))
        elif func.type == _TokenType.TAN:
            self._verif_tan(arg)
            return math.tan(self._conv_ang(arg))
        elif func.type == _TokenType.LOG:
            if arg <= 0:
                raise ValueError("Logaritmo de número não positivo")
            return math.log10(arg)
        elif func.type == _TokenType.LN:
            if arg <= 0:
                raise ValueError("Logaritmo natural de número não positivo")
            return math.log(arg)
        elif func.type == _TokenType.EXP:
            return math.exp(arg)
        elif func.type == _TokenType.ABS:
            return abs(arg)
        elif func.type == _TokenType.INV:
            if arg == 0:
                raise ZeroDivisionError("Inverso de zero não definido")
            return 1.0 / arg
        raise ValueError(f"Função não implementada: {func.type.value}")

    def _conv_ang(self, valor: float) -> float:
        """Converte ângulo conforme modo (deg/rad)."""
        if self.modo_angulo == "rad":
            return valor
        return math.radians(valor)

    def _verif_tan(self, valor: float):
        """Verifica se tangente é indefinida no modo atual."""
        if self.modo_angulo == "rad":
            meio_pi = math.pi / 2
            mod = valor % math.pi
            if abs(mod - meio_pi) < 1e-10:
                raise ValueError("Tangente indefinida para este ângulo")
        else:
            ang_mod = valor % 180
            if abs(ang_mod - 90) < 1e-10:
                raise ValueError("Tangente indefinida para este ângulo")

    def _power(self) -> float:
        """Gerencia ^ (potência), % (porcentagem), ! (fatorial) postfixos."""
        result = self._primary()
        while self._peek() == _TokenType.POW:
            self._consumir()
            right = self._power()  # associativo à direita
            result = math.pow(result, right)
        # % como operador postfixo: "200%" = 200/100 = 2
        if self._peek() == _TokenType.PERCENT:
            self._consumir()
            result = result / 100.0
        # ! como operador postfixo: "5!" = 120
        if self._peek() == _TokenType.FACT:
            self._consumir()
            if result < 0 or result != int(result):
                raise ValueError("Fatorial definido apenas para inteiros não negativos")
            result = float(math.factorial(int(result)))
        return result

    def _primary(self) -> float:
        """Gerencia números, parênteses e constantes (π)."""
        if self._peek() == _TokenType.LPAREN:
            self._consumir()
            result = self._expression()
            self._consumir(_TokenType.RPAREN)
            return result
        if self._peek() == _TokenType.NUMBER:
            return self._consumir().value
        if self._peek() == _TokenType.PI:
            return self._consumir().value  # math.pi
        raise ValueError(f"Token inesperado: '{self._peek().value}'")


def avaliar_expressao(expr: str, modo_angulo: str = "deg") -> float:
    """Avalia uma expressão matemática completa com precedência de operadores.

    Suporta:
        - Operadores: +, -, ×, ÷, ^
        - Funções: sin(), cos(), tan(), log(), ln(), exp(), abs(), inv()
        - Operadores prefixo: √ (raiz)
        - Operadores postfixo: % (porcentagem), ! (fatorial)
        - Constante: π
        - Parênteses para agrupamento
        - Números decimais
        - Sinal unário (-)

    Precedência (maior para menor):
        1.  ^  (potência, associativo à direita)
        2.  ×, ÷
        3.  +, -

    Args:
        expr: Expressão matemática (ex: "2+3×4" ou "sin(45)^2").
        modo_angulo: Modo angular para funções trigonométricas
                     ("deg" para graus, "rad" para radianos).

    Returns:
        Resultado numérico.

    Raises:
        ValueError: Se a expressão for inválida.
        ZeroDivisionError: Se houver divisão por zero.
    """
    if not expr or not expr.strip():
        raise ValueError("Expressão vazia")

    tokens = _tokenizar(expr)
    parser = _Parser(tokens, modo_angulo=modo_angulo)
    return parser.parse()