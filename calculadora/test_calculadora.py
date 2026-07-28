"""test_calculadora.py - Testes unitários para a Calculadora.

Cobre:
    - Operações matemáticas básicas
    - Operações unárias (√, %)
    - Validação de entradas
    - Histórico de operações
    - Memória
    - Formatação de números
    - Casos de borda (divisão por zero, negativos, etc.)
"""

import pytest
import math
from calculadora.core import Calculadora, Operacao, formatar_numero, validar_expressao, avaliar_expressao


# ═══════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture
def calc() -> Calculadora:
    """Fixture que retorna uma calculadora limpa."""
    return Calculadora()


# ═══════════════════════════════════════════════════════════════════
# Testes: Operações Básicas
# ═══════════════════════════════════════════════════════════════════

class TestOperacoesBasicas:
    """Testa as quatro operações fundamentais."""

    def test_soma(self, calc):
        assert calc.calcular(2, 3, Operacao.SOMA) == 5

    def test_soma_negativos(self, calc):
        assert calc.calcular(-2, -3, Operacao.SOMA) == -5

    def test_soma_decimais(self, calc):
        assert calc.calcular(2.5, 3.7, Operacao.SOMA) == pytest.approx(6.2)

    def test_subtracao(self, calc):
        assert calc.calcular(10, 4, Operacao.SUBTRACAO) == 6

    def test_subtracao_resultado_negativo(self, calc):
        assert calc.calcular(3, 10, Operacao.SUBTRACAO) == -7

    def test_multiplicacao(self, calc):
        assert calc.calcular(6, 7, Operacao.MULTIPLICACAO) == 42

    def test_multiplicacao_por_zero(self, calc):
        assert calc.calcular(5, 0, Operacao.MULTIPLICACAO) == 0

    def test_divisao(self, calc):
        assert calc.calcular(10, 3, Operacao.DIVISAO) == pytest.approx(3.3333333333)

    def test_divisao_exata(self, calc):
        assert calc.calcular(9, 3, Operacao.DIVISAO) == 3

    def test_divisao_por_zero_levanta_erro(self, calc):
        with pytest.raises(ZeroDivisionError, match="Divisão por zero"):
            calc.calcular(10, 0, Operacao.DIVISAO)

    def test_potencia(self, calc):
        assert calc.calcular(2, 3, Operacao.POTENCIA) == 8

    def test_potencia_zero(self, calc):
        assert calc.calcular(5, 0, Operacao.POTENCIA) == 1

    def test_potencia_negativo(self, calc):
        assert calc.calcular(2, -1, Operacao.POTENCIA) == 0.5


# ═══════════════════════════════════════════════════════════════════
# Testes: Operações Unárias
# ═══════════════════════════════════════════════════════════════════

class TestOperacoesUnarias:
    """Testa operações que usam apenas um operando."""

    def test_raiz_quadrada(self, calc):
        assert calc.calcular_unico(9, Operacao.RAIZ) == 3

    def test_raiz_quadrada_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.RAIZ) == 0

    def test_raiz_quadrada_decimal(self, calc):
        assert calc.calcular_unico(2, Operacao.RAIZ) == pytest.approx(1.414213562)

    def test_raiz_quadrada_negativo_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="negativo"):
            calc.calcular_unico(-4, Operacao.RAIZ)

    def test_porcentagem(self, calc):
        assert calc.calcular_unico(50, Operacao.PORCENTAGEM) == 0.5

    def test_porcentagem_100(self, calc):
        assert calc.calcular_unico(100, Operacao.PORCENTAGEM) == 1.0

    def test_porcentagem_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.PORCENTAGEM) == 0


# ═══════════════════════════════════════════════════════════════════
# Testes: Histórico
# ═══════════════════════════════════════════════════════════════════

class TestHistorico:
    """Testa o registro de histórico de operações."""

    def test_historico_inicia_vazio(self, calc):
        assert len(calc.historico) == 0

    def test_historico_registra_operacao(self, calc):
        calc.calcular(2, 3, Operacao.SOMA)
        assert len(calc.historico) == 1
        assert "2" in calc.historico[0].expressao
        assert "5" in calc.historico[0].resultado

    def test_historico_multiplas_operacoes(self, calc):
        calc.calcular(10, 5, Operacao.SOMA)
        calc.calcular(20, 4, Operacao.MULTIPLICACAO)
        assert len(calc.historico) == 2

    def test_ultimo_resultado(self, calc):
        calc.calcular(7, 8, Operacao.MULTIPLICACAO)
        assert calc.ultimo_resultado() == 56

    def test_ultimo_resultado_vazio(self, calc):
        assert calc.ultimo_resultado() is None

    def test_limpar_historico(self, calc):
        calc.calcular(1, 1, Operacao.SOMA)
        calc.calcular(2, 2, Operacao.SOMA)
        calc.limpar_historico()
        assert len(calc.historico) == 0


# ═══════════════════════════════════════════════════════════════════
# Testes: Memória
# ═══════════════════════════════════════════════════════════════════

class TestMemoria:
    """Testa as funções de memória."""

    def test_memoria_inicia_zero(self, calc):
        assert calc.memoria == 0.0

    def test_memoria_guardar(self, calc):
        calc.memoria_guardar(42.5)
        assert calc.memoria == 42.5

    def test_memoria_limpar(self, calc):
        calc.memoria_guardar(100)
        calc.memoria_limpar()
        assert calc.memoria == 0.0

    def test_memoria_somar(self, calc):
        calc.memoria = 10
        calc.memoria_somar(5)
        assert calc.memoria == 15.0

    def test_memoria_subtrair(self, calc):
        calc.memoria = 10
        calc.memoria_subtrair(3)
        assert calc.memoria == 7.0


# ═══════════════════════════════════════════════════════════════════
# Testes: Formatação
# ═══════════════════════════════════════════════════════════════════

class TestFormatacao:
    """Testa a formatação de números."""

    def test_inteiro(self):
        assert formatar_numero(5.0) == "5"

    def test_decimal(self):
        assert formatar_numero(3.14) == "3.14"

    def test_zero(self):
        assert formatar_numero(0) == "0"

    def test_grande(self):
        assert formatar_numero(1_000_000) == "1000000"

    def test_muitas_casas(self):
        assert formatar_numero(1.0 / 3.0)  # Não quebra


# ═══════════════════════════════════════════════════════════════════
# Testes: Validação
# ═══════════════════════════════════════════════════════════════════

class TestValidacao:
    """Testa a validação de expressões."""

    def test_expressao_valida(self):
        assert validar_expressao("2+2") is True

    def test_expressao_vazia(self):
        assert validar_expressao("") is False

    def test_expressao_com_letras(self):
        assert validar_expressao("2+abc") is False

    def test_parenteses_balanceados(self):
        assert validar_expressao("(2+3)*4") is True

    def test_parenteses_desbalanceados(self):
        assert validar_expressao("(2+3") is False


# ═══════════════════════════════════════════════════════════════════
# Testes: Operações Científicas
# ═══════════════════════════════════════════════════════════════════

class TestOperacoesAvancadas:
    """Testa exponencial, valor absoluto, fatorial, inverso e π."""

    def test_exp_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.EXP) == pytest.approx(1.0)

    def test_exp_um(self, calc):
        assert calc.calcular_unico(1, Operacao.EXP) == pytest.approx(math.e)

    def test_exp_negativo(self, calc):
        assert calc.calcular_unico(-1, Operacao.EXP) == pytest.approx(1/math.e)

    def test_abs_positivo(self, calc):
        assert calc.calcular_unico(5, Operacao.ABS) == 5

    def test_abs_negativo(self, calc):
        assert calc.calcular_unico(-5, Operacao.ABS) == 5

    def test_abs_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.ABS) == 0

    def test_fatorial_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.FATORIAL) == 1

    def test_fatorial_cinco(self, calc):
        assert calc.calcular_unico(5, Operacao.FATORIAL) == 120

    def test_fatorial_dez(self, calc):
        assert calc.calcular_unico(10, Operacao.FATORIAL) == 3628800

    def test_fatorial_negativo_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="não negativos"):
            calc.calcular_unico(-1, Operacao.FATORIAL)

    def test_fatorial_decimal_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="não negativos"):
            calc.calcular_unico(3.5, Operacao.FATORIAL)

    def test_inverso(self, calc):
        assert calc.calcular_unico(4, Operacao.INVERSO) == 0.25

    def test_inverso_zero_levanta_erro(self, calc):
        with pytest.raises(ZeroDivisionError):
            calc.calcular_unico(0, Operacao.INVERSO)

    def test_inverso_negativo(self, calc):
        assert calc.calcular_unico(-2, Operacao.INVERSO) == -0.5


# ═══════════════════════════════════════════════════════════════════
# Testes: Operações Científicas (trigonométricas)
# ═══════════════════════════════════════════════════════════════════

class TestOperacoesCientificas:
    """Testa seno, cosseno, tangente e logaritmos."""

    def test_seno_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.SENO) == pytest.approx(0)

    def test_seno_90(self, calc):
        assert calc.calcular_unico(90, Operacao.SENO) == pytest.approx(1.0)

    def test_seno_180(self, calc):
        assert calc.calcular_unico(180, Operacao.SENO) == pytest.approx(0, abs=1e-10)

    def test_cosseno_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.COSSENO) == pytest.approx(1.0)

    def test_cosseno_90(self, calc):
        assert calc.calcular_unico(90, Operacao.COSSENO) == pytest.approx(0, abs=1e-10)

    def test_cosseno_180(self, calc):
        assert calc.calcular_unico(180, Operacao.COSSENO) == pytest.approx(-1.0)

    def test_tangente_zero(self, calc):
        assert calc.calcular_unico(0, Operacao.TANGENTE) == pytest.approx(0)

    def test_tangente_45(self, calc):
        assert calc.calcular_unico(45, Operacao.TANGENTE) == pytest.approx(1.0)

    def test_tangente_90_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="indefinida"):
            calc.calcular_unico(90, Operacao.TANGENTE)

    def test_tangente_270_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="indefinida"):
            calc.calcular_unico(270, Operacao.TANGENTE)

    def test_log10(self, calc):
        assert calc.calcular_unico(100, Operacao.LOGARITMO) == pytest.approx(2.0)

    def test_log10_um(self, calc):
        assert calc.calcular_unico(1, Operacao.LOGARITMO) == pytest.approx(0)

    def test_log10_dez(self, calc):
        assert calc.calcular_unico(10, Operacao.LOGARITMO) == pytest.approx(1.0)

    def test_log10_negativo_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="não positivo"):
            calc.calcular_unico(-5, Operacao.LOGARITMO)

    def test_log10_zero_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="não positivo"):
            calc.calcular_unico(0, Operacao.LOGARITMO)

    def test_ln(self, calc):
        assert calc.calcular_unico(math.e, Operacao.LOG_NATURAL) == pytest.approx(1.0)

    def test_ln_um(self, calc):
        assert calc.calcular_unico(1, Operacao.LOG_NATURAL) == pytest.approx(0)

    def test_ln_negativo_levanta_erro(self, calc):
        with pytest.raises(ValueError, match="não positivo"):
            calc.calcular_unico(-1, Operacao.LOG_NATURAL)


# ═══════════════════════════════════════════════════════════════════
# Testes: Avaliador de Expressões (precedência de operadores)
# ═══════════════════════════════════════════════════════════════════

class TestAvaliarExpressao:
    """Testa o avaliador de expressões completas com precedência."""

    # ── Operações básicas ────────────────────────────────────────

    def test_soma_simples(self):
        assert avaliar_expressao("2+3") == 5

    def test_subtracao(self):
        assert avaliar_expressao("10-4") == 6

    def test_multiplicacao(self):
        assert avaliar_expressao("6×7") == 42

    def test_divisao(self):
        assert avaliar_expressao("10÷2") == 5

    def test_divisao_decimal(self):
        assert avaliar_expressao("10÷3") == pytest.approx(3.3333333333)

    def test_divisao_por_zero(self):
        with pytest.raises(ZeroDivisionError):
            avaliar_expressao("5÷0")

    def test_potencia(self):
        assert avaliar_expressao("2^3") == 8

    def test_potencia_zero(self):
        assert avaliar_expressao("5^0") == 1

    def test_decimal(self):
        assert avaliar_expressao("2.5+3.7") == pytest.approx(6.2)

    # ── Precedência ─────────────────────────────────────────────

    def test_precedencia_multiplicacao_antes_soma(self):
        """2+3×4 = 2+(3×4) = 14"""
        assert avaliar_expressao("2+3×4") == 14

    def test_precedencia_divisao_antes_subtracao(self):
        """10-6÷3 = 10-(6÷3) = 8"""
        assert avaliar_expressao("10-6÷3") == 8

    def test_precedencia_multiplus_soma(self):
        """2+3×4+5 = 2+12+5 = 19"""
        assert avaliar_expressao("2+3×4+5") == 19

    def test_precedencia_potencia_antes_multiplicacao(self):
        """2×3^2 = 2×(3^2) = 18"""
        assert avaliar_expressao("2×3^2") == 18

    def test_precedencia_completa(self):
        """2+3×4-6÷2+2^3 = 2+12-3+8 = 19"""
        assert avaliar_expressao("2+3×4-6÷2+2^3") == 19

    # ── Parênteses ──────────────────────────────────────────────

    def test_parenteses_muda_precedencia(self):
        """(2+3)×4 = 5×4 = 20"""
        assert avaliar_expressao("(2+3)×4") == 20

    def test_parenteses_aninhados(self):
        """((2+3)×4) = 20"""
        assert avaliar_expressao("((2+3)×4)") == 20

    def test_parenteses_complexo(self):
        """(2+3)×(4+1) = 5×5 = 25"""
        assert avaliar_expressao("(2+3)×(4+1)") == 25

    def test_parenteses_triplo(self):
        """(1+2)×(3+4)×(5+6) = 3×7×11 = 231"""
        assert avaliar_expressao("(1+2)×(3+4)×(5+6)") == 231

    # ── Sinal unário ────────────────────────────────────────────

    def test_negativo_inicio(self):
        assert avaliar_expressao("-5+3") == -2

    def test_duplo_negativo(self):
        assert avaliar_expressao("--5") == 5

    def test_negativo_apos_parenteses(self):
        assert avaliar_expressao("(-3)×(-4)") == 12

    def test_positivo_explicito(self):
        assert avaliar_expressao("+5") == 5

    # ── Raiz e Porcentagem ──────────────────────────────────────

    def test_raiz(self):
        assert avaliar_expressao("√9") == 3

    def test_raiz_em_expressao(self):
        assert avaliar_expressao("2+√9") == 5

    def test_raiz_negativo(self):
        with pytest.raises(ValueError, match="negativo"):
            avaliar_expressao("√-4")

    def test_porcentagem(self):
        assert avaliar_expressao("50%") == 0.5

    def test_porcentagem_em_expressao(self):
        assert avaliar_expressao("200%+1") == 3.0

    # ── Novas funções: exp, abs, fatorial, inverso, π ────────────

    def test_exp(self):
        assert avaliar_expressao("exp(0)") == pytest.approx(1.0)

    def test_exp_um(self):
        assert avaliar_expressao("exp(1)") == pytest.approx(math.e)

    def test_exp_em_expressao(self):
        """exp(0)+exp(1) = 1 + e ≈ 3.718"""
        assert avaliar_expressao("exp(0)+exp(1)") == pytest.approx(1 + math.e)

    def test_abs_positivo(self):
        assert avaliar_expressao("abs(5)") == 5

    def test_abs_negativo(self):
        assert avaliar_expressao("abs(-5)") == 5

    def test_abs_em_expressao(self):
        assert avaliar_expressao("abs(-5)+abs(3)") == 8

    def test_fatorial(self):
        assert avaliar_expressao("5!") == 120

    def test_fatorial_zero(self):
        assert avaliar_expressao("0!") == 1

    def test_fatorial_em_expressao(self):
        """3!+4! = 6+24 = 30"""
        assert avaliar_expressao("3!+4!") == 30

    def test_fatorial_precedencia(self):
        """2+3!×2 = 2+6×2 = 2+12 = 14"""
        assert avaliar_expressao("2+3!×2") == 14

    def test_fatorial_negativo_levanta_erro(self):
        with pytest.raises(ValueError, match="não negativos"):
            avaliar_expressao("(-3)!")

    def test_inverso(self):
        assert avaliar_expressao("inv(4)") == 0.25

    def test_inverso_em_expressao(self):
        """inv(2)+inv(4) = 0.5+0.25 = 0.75"""
        assert avaliar_expressao("inv(2)+inv(4)") == 0.75

    def test_inverso_zero_levanta_erro(self):
        with pytest.raises(ZeroDivisionError):
            avaliar_expressao("inv(0)")

    def test_constante_pi(self):
        assert avaliar_expressao("π") == pytest.approx(math.pi)

    def test_constante_pi_expressao(self):
        """π×2 ≈ 6.283"""
        assert avaliar_expressao("π×2") == pytest.approx(math.pi * 2)

    def test_pi_em_seno(self):
        """sin(π) em rad = 0"""
        assert avaliar_expressao("sin(π)", modo_angulo="rad") == pytest.approx(0, abs=1e-10)

    # ── Funções científicas ─────────────────────────────────────

    def test_sin(self):
        assert avaliar_expressao("sin(90)") == pytest.approx(1.0)

    def test_cos(self):
        assert avaliar_expressao("cos(0)") == pytest.approx(1.0)

    def test_tan(self):
        assert avaliar_expressao("tan(45)") == pytest.approx(1.0)

    def test_log(self):
        assert avaliar_expressao("log(100)") == pytest.approx(2.0)

    def test_ln(self):
        assert avaliar_expressao("ln(2.718281828459045)") == pytest.approx(1.0, abs=1e-5)

    def test_funcao_em_expressao(self):
        """sin(90)+cos(0) = 1+1 = 2"""
        assert avaliar_expressao("sin(90)+cos(0)") == pytest.approx(2.0)

    def test_funcao_aninhada(self):
        """sin(sin(90)) = sin(1) ≈ 0.01745..."""
        # sin(90) = 1, sin(1°) = 0.01745
        assert avaliar_expressao("sin(sin(90))") == pytest.approx(math.sin(math.radians(1.0)))

    def test_tan_90_levanta_erro(self):
        with pytest.raises(ValueError, match="indefinida"):
            avaliar_expressao("tan(90)")

    def test_log_negativo_levanta_erro(self):
        with pytest.raises(ValueError, match="não positivo"):
            avaliar_expressao("log(-5)")

    # ── Modo radianos ───────────────────────────────────────────

    def test_sin_rad_pi_meio(self):
        """sin(π/2) em rad = 1"""
        assert avaliar_expressao("sin(1.57079632679)", modo_angulo="rad") == pytest.approx(1.0)

    def test_cos_rad_pi(self):
        """cos(π) em rad = -1"""
        assert avaliar_expressao("cos(3.14159265359)", modo_angulo="rad") == pytest.approx(-1.0)

    def test_tan_rad_pi_quatro(self):
        """tan(π/4) em rad = 1"""
        assert avaliar_expressao("tan(0.78539816339)", modo_angulo="rad") == pytest.approx(1.0)

    def test_tan_rad_pi_meio_levanta_erro(self):
        """tan(π/2) em rad é indefinida"""
        with pytest.raises(ValueError, match="indefinida"):
            avaliar_expressao("tan(1.57079632679)", modo_angulo="rad")

    def test_calcular_unico_sin_rad(self):
        """Calculadora.calcular_unico com angulo_modo='rad'"""
        c = Calculadora()
        c.angulo_modo = "rad"
        assert c.calcular_unico(math.pi / 2, Operacao.SENO) == pytest.approx(1.0)

    def test_calcular_unico_cos_rad(self):
        c = Calculadora()
        c.angulo_modo = "rad"
        assert c.calcular_unico(math.pi, Operacao.COSSENO) == pytest.approx(-1.0)

    def test_calcular_unico_tan_rad(self):
        c = Calculadora()
        c.angulo_modo = "rad"
        assert c.calcular_unico(math.pi / 4, Operacao.TANGENTE) == pytest.approx(1.0)

    def test_calcular_unico_tan_rad_indefinido(self):
        c = Calculadora()
        c.angulo_modo = "rad"
        with pytest.raises(ValueError, match="indefinida"):
            c.calcular_unico(math.pi / 2, Operacao.TANGENTE)

    def test_calcular_unico_sin_deg_default(self):
        """Por padrão (deg), sin(90) = 1"""
        c = Calculadora()
        assert c.calcular_unico(90, Operacao.SENO) == pytest.approx(1.0)

    def test_calcular_unico_sin_muda_modo(self):
        """Alternar modo entre deg e rad"""
        c = Calculadora()
        c.angulo_modo = "deg"
        assert c.calcular_unico(90, Operacao.SENO) == pytest.approx(1.0)
        c.angulo_modo = "rad"
        assert c.calcular_unico(math.pi / 2, Operacao.COSSENO) == pytest.approx(0, abs=1e-10)

    # ── Erros e bordas ──────────────────────────────────────────

    def test_expressao_vazia(self):
        with pytest.raises(ValueError, match="vazia"):
            avaliar_expressao("")

    def test_parenteses_desbalanceados(self):
        with pytest.raises(ValueError):
            avaliar_expressao("(2+3")

    def test_caractere_invalido(self):
        with pytest.raises(ValueError):
            avaliar_expressao("2+abc")

    def test_funcao_desconhecida(self):
        with pytest.raises(ValueError, match="desconhecida"):
            avaliar_expressao("foo(5)")

    def test_operador_sozinho(self):
        with pytest.raises(ValueError):
            avaliar_expressao("+")

    def test_expressao_muito_longa(self):
        # Apenas não quebra com expressões longas
        expr = "1+2×3-4÷5+6×7-8÷9"
        assert isinstance(avaliar_expressao(expr), float)


# ═══════════════════════════════════════════════════════════════════
# Testes: Casos de Borda
# ═══════════════════════════════════════════════════════════════════

class TestCasosBorda:
    """Testa casos extremos e situações inesperadas."""

    def test_operacao_invalida(self, calc):
        with pytest.raises(ValueError):
            calc.calcular(1, 2, "invalido")  # type: ignore

    def test_unario_invalido(self, calc):
        with pytest.raises(ValueError):
            calc.calcular_unico(10, Operacao.SOMA)  # SOMA é binária

    def test_historico_limitado(self, calc):
        # Preenche mais que o limite de 50
        for i in range(60):
            calc.calcular(i, 1, Operacao.SOMA)
        assert len(calc.historico) <= 50

    def test_float_grande(self, calc):
        resultado = calc.calcular(1e15, 1, Operacao.SOMA)
        assert isinstance(resultado, float)
