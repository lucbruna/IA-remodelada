"""gui.py - Interface Gráfica Tkinter da Calculadora.

Fornece uma calculadora visual completa com:
    - Display de largura total com expressão e resultado
    - Botões numéricos e de operação
    - Suporte a expressões completas com precedência (2+3×4 = 14)
    - Parênteses para agrupamento
    - Funções científicas (sin, cos, tan, log, ln)
    - Atalhos de teclado
    - Histórico de operações
    - Suporte a memória
"""

import tkinter as tk
from typing import Optional
from .core import (
    Calculadora, Operacao, formatar_numero, avaliar_expressao
)


# Mapeamento de Operacao para símbolo de exibição
SIMBOLO_OP: dict[Operacao, str] = {
    Operacao.SOMA: "+",
    Operacao.SUBTRACAO: "-",
    Operacao.MULTIPLICACAO: "×",
    Operacao.DIVISAO: "÷",
    Operacao.POTENCIA: "^",
}


class CalculadoraGUI:
    """Interface gráfica da calculadora usando Tkinter.

    Layout (nova versão com expressões):
        ┌──────────────────────────┐
        │   Display (expressão)    │
        │   Display (valor/result) │
        ├───┬───┬───┬───┬───┬─────┤
        │ MC│ MR│ MS│ M+│ M- │    │
        ├───┴───┴───┴───┴───┴─────┤
        │ sin│cos│tan│log│  ln    │
        ├───┬───┬───┬───┬─────────┤
        │ C │ ± │ % │ ÷ │         │
        ├───┼───┼───┼───┤         │
        │ 7 │ 8 │ 9 │ × │         │
        ├───┼───┼───┼───┤   =     │
        │ 4 │ 5 │ 6 │ - │         │
        ├───┼───┼───┼───┤         │
        │ 1 │ 2 │ 3 │ + │         │
        ├───┼───┼───┼───┼─────────┤
        │ 0 │ . │ ← │ ^ │         │
        ├───┼───┼───┼───┼─────────┤
        │ ( │ ) │ √ │   │   =     │
        └───┴───┴───┴───┴─────────┘
    """

    # Paleta de cores
    CORES = {
        "bg": "#1a1a2e",
        "display_bg": "#0f0f23",
        "btn_num": "#16213e",
        "btn_op": "#0f3460",
        "btn_eq": "#e94560",
        "btn_mem": "#533483",
        "btn_clear": "#e94560",
        "btn_special": "#1a1a40",
        "btn_paren": "#1a1a50",
        "text": "#ffffff",
        "text_secondary": "#a0a0b0",
        "text_display": "#00ff88",
        "text_expr": "#6a9fb5",
        "border": "#2a2a4a",
    }

    def __init__(self, titulo: str = "Calculadora Científica"):
        self.calc = Calculadora()
        self._janela = tk.Tk()
        self._janela.title(titulo)
        self._janela.geometry("320x680")
        self._janela.minsize(300, 600)
        self._janela.resizable(False, False)
        self._janela.configure(bg=self.CORES["bg"])

        # ─── Estado do modo expressão ────────────────────────────
        self._expressao: str = ""             # Expressão sendo construída (ex: "2+3×4")
        self._mostrando_resultado: bool = False  # Display mostra resultado?
        self._cursor_ativo: bool = False      # Para piscar o cursor no display

        # ─── Modo angular (DEG / RAD) ────────────────────────────
        self._modo_angulo: str = "deg"
        self.calc.angulo_modo = "deg"

        self._construir_interface()
        self._configurar_atalhos()

    # ─── Propriedades ───────────────────────────────────────────

    @property
    def janela(self) -> tk.Tk:
        return self._janela

    # ─── Construção da Interface ─────────────────────────────────

    def _construir_interface(self):
        """Constrói todos os elementos da interface."""
        self._janela.columnconfigure(0, weight=1)
        self._janela.rowconfigure(1, weight=1)

        # Display
        self._criar_display()

        # Botões
        frame_botoes = tk.Frame(self._janela, bg=self.CORES["bg"])
        frame_botoes.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        self._criar_botoes_memoria(frame_botoes)
        self._criar_botoes_cientificos(frame_botoes)
        self._criar_botoes_avancados(frame_botoes)
        self._criar_botoes_principais(frame_botoes)

    def _criar_display(self):
        """Cria o display duplo: expressão + valor/resultado + indicador DEG/RAD."""
        frame = tk.Frame(self._janela, bg=self.CORES["display_bg"], height=110)
        frame.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        frame.grid_propagate(False)
        frame.columnconfigure(1, weight=1)

        # ── Indicador DEG/RAD (canto superior esquerdo) ───────────
        self._label_modo = tk.Label(
            frame,
            text="DEG",
            font=("Consolas", 8, "bold"),
            fg=self.CORES["text_display"],
            bg=self.CORES["display_bg"],
            cursor="hand2",
            padx=6,
            pady=2,
        )
        self._label_modo.grid(row=0, column=0, sticky="nw", padx=(4, 0), pady=(4, 0))
        self._label_modo.bind("<Button-1>", lambda e: self._alternar_modo_angulo())

        # Label da expressão (mostra a expressão sendo digitada)
        self._label_expr = tk.Label(
            frame,
            text="",
            font=("Consolas", 12),
            fg=self.CORES["text_expr"],
            bg=self.CORES["display_bg"],
            anchor="e",
            padx=12,
            height=1,
        )
        self._label_expr.grid(row=0, column=0, columnspan=2, sticky="e", pady=(8, 0))

        # Label do resultado/valor atual (fonte grande)
        self._label_display = tk.Label(
            frame,
            text="0",
            font=("Consolas", 28, "bold"),
            fg=self.CORES["text_display"],
            bg=self.CORES["display_bg"],
            anchor="e",
            padx=12,
        )
        self._label_display.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def _clarear_cor(self, hex_cor: str, fator: float = 0.2) -> str:
        """Clareia uma cor hex."""
        hex_cor = hex_cor.lstrip("#")
        r, g, b = int(hex_cor[0:2], 16), int(hex_cor[2:4], 16), int(hex_cor[4:6], 16)
        r = min(255, int(r + (255 - r) * fator))
        g = min(255, int(g + (255 - g) * fator))
        b = min(255, int(b + (255 - b) * fator))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _criar_botoes_memoria(self, parent):
        """Cria a linha de botões de memória."""
        frame = tk.Frame(parent, bg=self.CORES["bg"])
        frame.pack(fill="x", pady=(0, 3))
        botoes_mem = [
            ("MC", self._memoria_limpar),
            ("MR", self._memoria_recuperar),
            ("MS", self._memoria_guardar),
            ("M+", self._memoria_somar),
            ("M-", self._memoria_subtrair),
        ]
        for i in range(len(botoes_mem)):
            frame.columnconfigure(i, weight=1)

        for i, (texto, cmd) in enumerate(botoes_mem):
            btn = tk.Button(
                frame,
                text=texto,
                font=("Segoe UI", 9, "bold"),
                fg=self.CORES["text_secondary"],
                bg=self.CORES["btn_mem"],
                activeforeground=self.CORES["text"],
                activebackground=self._clarear_cor(self.CORES["btn_mem"]),
                relief="flat",
                bd=0,
                cursor="hand2",
                command=cmd,
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)

    def _criar_botoes_cientificos(self, parent):
        """Cria a linha de botões de operações científicas."""
        frame = tk.Frame(parent, bg=self.CORES["bg"])
        frame.pack(fill="x", pady=(0, 3))

        botoes_cient = [
            ("sin", lambda: self._apertar_unario(Operacao.SENO)),
            ("cos", lambda: self._apertar_unario(Operacao.COSSENO)),
            ("tan", lambda: self._apertar_unario(Operacao.TANGENTE)),
            ("log", lambda: self._apertar_unario(Operacao.LOGARITMO)),
            ("ln",  lambda: self._apertar_unario(Operacao.LOG_NATURAL)),
        ]

        for i in range(len(botoes_cient)):
            frame.columnconfigure(i, weight=1)

        for i, (texto, cmd) in enumerate(botoes_cient):
            btn = tk.Button(
                frame,
                text=texto,
                font=("Consolas", 11, "bold"),
                fg=self.CORES["text_display"],
                bg=self.CORES["btn_special"],
                activeforeground=self.CORES["text"],
                activebackground=self._clarear_cor(self.CORES["btn_special"]),
                relief="flat",
                bd=0,
                cursor="hand2",
                command=cmd,
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=1, pady=1, ipady=3)

    def _criar_botoes_avancados(self, parent):
        """Cria a linha de botões avançados: e^x, |x|, x!, 1/x, π."""
        frame = tk.Frame(parent, bg=self.CORES["bg"])
        frame.pack(fill="x", pady=(0, 3))

        botoes_avanc = [
            ("e^x", lambda: self._apertar_unario(Operacao.EXP)),
            ("|x|", lambda: self._apertar_unario(Operacao.ABS)),
            ("x!",  lambda: self._apertar_unario(Operacao.FATORIAL)),
            ("1/x", lambda: self._apertar_unario(Operacao.INVERSO)),
            ("π",   self._inserir_pi),
        ]

        for i in range(len(botoes_avanc)):
            frame.columnconfigure(i, weight=1)

        for i, (texto, cmd) in enumerate(botoes_avanc):
            cor = self.CORES["btn_eq"] if texto == "π" else self.CORES["btn_special"]
            btn = tk.Button(
                frame,
                text=texto,
                font=("Consolas", 11, "bold"),
                fg=self.CORES["text"],
                bg=cor,
                activeforeground=self.CORES["text"],
                activebackground=self._clarear_cor(cor),
                relief="flat",
                bd=0,
                cursor="hand2",
                command=cmd,
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=1, pady=1, ipady=3)

    def _criar_botoes_principais(self, parent):
        """Cria o grid de botões principal com 4 colunas."""
        for i in range(4):
            parent.columnconfigure(i, weight=1)

        # ── Linha 1: C, ±, %, ÷ ──────────────────────────────────
        linha1 = [
            ("C", self._limpar, self.CORES["btn_clear"]),
            ("±", self._inverter_sinal, self.CORES["btn_special"]),
            ("%", self._calcular_porcentagem, self.CORES["btn_special"]),
            ("÷", lambda: self._inserir_operador(Operacao.DIVISAO), self.CORES["btn_op"]),
        ]
        for col, (txt, cmd, cor) in enumerate(linha1):
            self._criar_btn(parent, txt, cmd, cor, row=1, col=col, ipady=5)

        # ── Linhas 2-4: Números ──────────────────────────────────
        nums = [
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("4", 3, 0), ("5", 3, 1), ("6", 3, 2),
            ("1", 4, 0), ("2", 4, 1), ("3", 4, 2),
        ]
        for txt, row, col in nums:
            self._criar_btn(
                parent, txt,
                lambda t=txt: self._inserir_numero(t),
                self.CORES["btn_num"],
                row=row, col=col, ipady=5,
            )

        # ── Operadores do lado direito: ×, -, + ──────────────────
        ops = [
            ("×", Operacao.MULTIPLICACAO, 2),
            ("-", Operacao.SUBTRACAO, 3),
            ("+", Operacao.SOMA, 4),
        ]
        for txt, op, row in ops:
            self._criar_btn(
                parent, txt,
                lambda o=op: self._inserir_operador(o),
                self.CORES["btn_op"],
                row=row, col=3, ipady=5,
            )

        # ── Botão = (grande, 2 linhas) ────────────────────────────
        btn_igual = tk.Button(
            parent,
            text="=",
            font=("Segoe UI", 22, "bold"),
            fg=self.CORES["text"],
            bg=self.CORES["btn_eq"],
            activeforeground=self.CORES["text"],
            activebackground=self._clarear_cor(self.CORES["btn_eq"]),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._calcular_resultado,
        )
        btn_igual.grid(row=6, column=3, rowspan=2, sticky="nsew", padx=1, pady=1)

        # ── Linha 5: 0, ., ←, ^ ──────────────────────────────────
        linha5 = [
            ("0",  lambda: self._inserir_numero("0"), self.CORES["btn_num"]),
            (".",  self._inserir_ponto, self.CORES["btn_num"]),
            ("←",  self._apagar_ultimo, self.CORES["btn_special"]),
            ("^",  lambda: self._inserir_operador(Operacao.POTENCIA), self.CORES["btn_op"]),
        ]
        for col, (txt, cmd, cor) in enumerate(linha5):
            self._criar_btn(parent, txt, cmd, cor, row=5, col=col, ipady=5)

        # ── Linha 6: (, ), √, (espaço vazio para =) ──────────────
        linha6 = [
            ("(", lambda: self._inserir_texto("("), self.CORES["btn_paren"]),
            (")", lambda: self._inserir_texto(")"), self.CORES["btn_paren"]),
            ("√", self._calcular_raiz, self.CORES["btn_special"]),
            ("", None, self.CORES["bg"]),  # placeholder ( = ocupa aqui)
        ]
        for col, (txt, cmd, cor) in enumerate(linha6):
            if cmd is None:
                continue  # = ocupa esta posição via rowspan
            self._criar_btn(parent, txt, cmd, cor, row=6, col=col, ipady=5)

    def _criar_btn(self, parent, texto, comando, cor_fundo,
                   row=None, col=None, ipady=5):
        """Helper para criar um botão estilizado."""
        btn = tk.Button(
            parent,
            text=texto,
            font=("Segoe UI", 14, "bold"),
            fg=self.CORES["text"],
            bg=cor_fundo,
            activeforeground=self.CORES["text"],
            activebackground=self._clarear_cor(cor_fundo),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=comando,
        )
        btn.grid(row=row, column=col, sticky="nsew", padx=1, pady=1, ipady=ipady)

    # ─── Configuração de Atalhos ─────────────────────────────────

    def _configurar_atalhos(self):
        """Configura atalhos de teclado."""
        atalhos = {
            "<Key-0>": lambda e: self._inserir_numero("0"),
            "<Key-1>": lambda e: self._inserir_numero("1"),
            "<Key-2>": lambda e: self._inserir_numero("2"),
            "<Key-3>": lambda e: self._inserir_numero("3"),
            "<Key-4>": lambda e: self._inserir_numero("4"),
            "<Key-5>": lambda e: self._inserir_numero("5"),
            "<Key-6>": lambda e: self._inserir_numero("6"),
            "<Key-7>": lambda e: self._inserir_numero("7"),
            "<Key-8>": lambda e: self._inserir_numero("8"),
            "<Key-9>": lambda e: self._inserir_numero("9"),
            "<Key-plus>": lambda e: self._inserir_operador(Operacao.SOMA),
            "<Key-minus>": lambda e: self._inserir_operador(Operacao.SUBTRACAO),
            "<Key-asterisk>": lambda e: self._inserir_operador(Operacao.MULTIPLICACAO),
            "<Key-slash>": lambda e: self._inserir_operador(Operacao.DIVISAO),
            "<Key-percent>": lambda e: self._calcular_porcentagem(),
            "<Key-period>": lambda e: self._inserir_ponto(),
            "<Key-comma>": lambda e: self._inserir_ponto(),
            "<Key-parenleft>": lambda e: self._inserir_texto("("),
            "<Key-parenright>": lambda e: self._inserir_texto(")"),
            "<Key-s>": lambda e: self._apertar_unario(Operacao.SENO),
            "<Key-o>": lambda e: self._apertar_unario(Operacao.COSSENO),
            "<Key-t>": lambda e: self._apertar_unario(Operacao.TANGENTE),
            "<Key-l>": lambda e: self._apertar_unario(Operacao.LOGARITMO),
            "<Key-n>": lambda e: self._apertar_unario(Operacao.LOG_NATURAL),
            "<Key-d>": lambda e: self._alternar_modo_angulo(),
            "<Key-e>": lambda e: self._apertar_unario(Operacao.EXP),
            "<Key-a>": lambda e: self._apertar_unario(Operacao.ABS),
            "<Key-exclam>": lambda e: self._apertar_unario(Operacao.FATORIAL),
            "<Key-i>": lambda e: self._apertar_unario(Operacao.INVERSO),
            "<Key-p>": lambda e: self._inserir_pi(),
            "<Return>": lambda e: self._calcular_resultado(),
            "<KP_Enter>": lambda e: self._calcular_resultado(),
            "<BackSpace>": lambda e: self._apagar_ultimo(),
            "<Escape>": lambda e: self._limpar(),
            "<Key-c>": lambda e: self._limpar(),
            "<Control-c>": lambda e: self._copiar_resultado(),
        }
        for tecla, funcao in atalhos.items():
            self._janela.bind(tecla, funcao)

    # ─── Helpers de Expressão ────────────────────────────────────

    def _extrair_ultimo_numero(self) -> str:
        """Extrai o último número sendo digitado na expressão."""
        import re
        # Procura o último número (com sinal opcional, decimal opcional) no fim
        match = re.search(r'(-?\d+(?:\.\d*)?)$', self._expressao)
        return match.group(1) if match else ""

    def _obter_valor_atual(self) -> float:
        """Obtém o valor do último número na expressão, ou 0."""
        if self._mostrando_resultado or not self._expressao:
            try:
                return float(self._expressao) if self._expressao else 0.0
            except ValueError:
                return 0.0
        ultimo = self._extrair_ultimo_numero()
        return float(ultimo) if ultimo else 0.0

    def _expressao_termina_em_operador(self) -> bool:
        """Verifica se a expressão termina com operador binário."""
        if not self._expressao:
            return False
        return self._expressao[-1] in "+-×÷^"

    def _atualizar_display(self):
        """Atualiza os labels do display."""
        if not self._expressao:
            self._label_expr.configure(text="")
            self._label_display.configure(text="0")
            return

        if self._mostrando_resultado:
            # Mostra expressão no label superior, resultado no principal
            self._label_expr.configure(text=self._expressao + " =")
            # O resultado já foi armazenado em _expressao
            self._label_display.configure(text=self._expressao)
        else:
            # Mostra a expressão sendo construída
            expr_display = self._expressao
            if len(expr_display) > 28:
                expr_display = "…" + expr_display[-27:]
            self._label_expr.configure(text=expr_display)

            # Último número digitado aparece no display principal
            ultimo = self._extrair_ultimo_numero()
            if ultimo:
                self._label_display.configure(text=ultimo)
            elif self._expressao and self._expressao[-1] in "()":
                # Depois de fechar parêntese, mostra resultado parcial
                self._label_display.configure(text=")")
            else:
                self._label_display.configure(text="0")

    # ─── Inserção na Expressão ───────────────────────────────────

    def _inserir_numero(self, digito: str):
        """Insere um dígito na expressão."""
        if self._mostrando_resultado:
            # Começa nova expressão
            self._expressao = ""
            self._mostrando_resultado = False

        # Limita a 15 dígitos no número atual
        ultimo = self._extrair_ultimo_numero()
        if ultimo and len(ultimo.replace(".", "")) >= 15:
            return

        self._expressao += digito
        self._atualizar_display()

    def _inserir_ponto(self):
        """Insere ponto decimal no número atual."""
        if self._mostrando_resultado:
            self._expressao = "0."
            self._mostrando_resultado = False
            self._atualizar_display()
            return

        ultimo = self._extrair_ultimo_numero()
        if "." not in ultimo:
            if not ultimo and self._expressao and self._expressao[-1].isdigit() is False:
                # Começando número novo: "2+." → "2+0."
                self._expressao += "0."
            elif not ultimo:
                self._expressao += "0."
            else:
                self._expressao += "."
        self._atualizar_display()

    def _inserir_operador(self, operacao: Operacao):
        """Insere um operador binário na expressão."""
        if self._mostrando_resultado:
            # Continua da expressão atual para o próximo cálculo
            self._mostrando_resultado = False
            # O resultado está em _expressao, só adiciona operador
            self._expressao += SIMBOLO_OP[operacao]
            self._atualizar_display()
            return

        if not self._expressao and operacao == Operacao.SUBTRACAO:
            # Começar com negativo: "-5+3"
            self._expressao += "-"
            self._atualizar_display()
            return
        elif not self._expressao:
            return  # Ignora operadores no início (exceto -)

        # Substitui operador se expressão terminar em operador
        if self._expressao_termina_em_operador():
            self._expressao = self._expressao[:-1]

        self._expressao += SIMBOLO_OP[operacao]
        self._atualizar_display()

    def _inserir_texto(self, texto: str):
        """Insere texto literal na expressão (parênteses, etc.)."""
        if self._mostrando_resultado:
            self._expressao = ""
            self._mostrando_resultado = False
        self._expressao += texto
        self._atualizar_display()

    # ─── Avaliação e Resultado ───────────────────────────────────

    def _calcular_resultado(self):
        """Avalia a expressão completa e mostra o resultado."""
        if not self._expressao or self._mostrando_resultado:
            return

        try:
            resultado = avaliar_expressao(self._expressao, modo_angulo=self._modo_angulo)
            expr_original = self._expressao
            resultado_str = formatar_numero(resultado)

            # Atualiza display
            self._label_expr.configure(text=expr_original + " =")
            self._label_display.configure(text=resultado_str)

            # Prepara para continuação
            self._expressao = resultado_str
            self._mostrando_resultado = True

            # Registra no histórico
            self.calc._registrar_historico(expr_original, resultado)
        except (ValueError, ZeroDivisionError) as e:
            self._mostrar_erro(str(e))

    # ─── Operações Unárias / Imediatas ───────────────────────────

    def _apertar_unario(self, operacao: Operacao):
        """Executa operação unária imediata (sin, cos, tan, log, ln)."""
        try:
            self.calc.angulo_modo = self._modo_angulo
            valor = self._obter_valor_atual()
            resultado = self.calc.calcular_unico(valor, operacao)
            resultado_str = formatar_numero(resultado)

            expr_label = f"{operacao.value}({formatar_numero(valor)}) ="
            # Mostra modo angular para funções trigonométricas
            if operacao in (Operacao.SENO, Operacao.COSSENO, Operacao.TANGENTE):
                expr_label = f"{operacao.value}({formatar_numero(valor)}{'°' if self._modo_angulo == 'deg' else ' rad'}) ="

            self._label_expr.configure(text=expr_label)
            self._label_display.configure(text=resultado_str)
            self._expressao = resultado_str
            self._mostrando_resultado = True
        except (ValueError, ZeroDivisionError) as e:
            self._mostrar_erro(str(e))

    def _inserir_pi(self):
        """Insere o valor de π (3.14159...) na expressão."""
        import math
        if self._mostrando_resultado or not self._expressao:
            self._expressao = ""
        self._expressao += str(math.pi)
        self._mostrando_resultado = False
        self._atualizar_display()

    def _calcular_raiz(self):
        """Calcula raiz quadrada imediata do valor atual."""
        try:
            valor = self._obter_valor_atual()
            if valor < 0:
                raise ValueError("Raiz quadrada de número negativo")
            resultado = self.calc.calcular_unico(valor, Operacao.RAIZ)
            resultado_str = formatar_numero(resultado)

            self._label_expr.configure(text=f"√({formatar_numero(valor)}) =")
            self._label_display.configure(text=resultado_str)
            self._expressao = resultado_str
            self._mostrando_resultado = True
        except (ValueError, ZeroDivisionError) as e:
            self._mostrar_erro(str(e))

    def _calcular_porcentagem(self):
        """Calcula porcentagem imediata do valor atual."""
        try:
            valor = self._obter_valor_atual()
            resultado = self.calc.calcular_unico(valor, Operacao.PORCENTAGEM)
            resultado_str = formatar_numero(resultado)

            self._label_expr.configure(text=f"{formatar_numero(valor)}%")
            self._label_display.configure(text=resultado_str)
            self._expressao = resultado_str
            self._mostrando_resultado = True
        except (ValueError, ZeroDivisionError) as e:
            self._mostrar_erro(str(e))

    # ─── Edição ──────────────────────────────────────────────────

    def _inverter_sinal(self):
        """Inverte o sinal do valor atual da expressão."""
        if not self._expressao:
            self._expressao = "-"
            self._atualizar_display()
            return

        if self._mostrando_resultado:
            try:
                valor = float(self._expressao)
                self._expressao = formatar_numero(-valor)
                self._label_display.configure(text=self._expressao)
                self._label_expr.configure(text="-(" + self._expressao + ")")
                self._expressao = self._expressao  # mantém o valor
                self._atualizar_display()
            except ValueError:
                pass
            return

        # Verifica se o último número pode ser negado
        import re
        match = re.search(r'(-?\d+(?:\.\d*)?)$', self._expressao)
        if match:
            num = match.group(1)
            if num.startswith("-"):
                novo_num = num[1:]
            else:
                novo_num = "-" + num
            self._expressao = self._expressao[:match.start()] + novo_num
        else:
            self._expressao += "(-"
        self._atualizar_display()

    def _apagar_ultimo(self):
        """Apaga o último carácter da expressão."""
        if self._mostrando_resultado or not self._expressao:
            self._limpar()
            return

        # Apaga último char
        self._expressao = self._expressao[:-1]

        # Se apagou tudo, reseta
        if not self._expressao:
            self._label_expr.configure(text="")
            self._label_display.configure(text="0")
            return

        self._atualizar_display()

    def _limpar(self):
        """Limpa tudo (C)."""
        self._expressao = ""
        self._mostrando_resultado = False
        self._label_expr.configure(text="")
        self._label_display.configure(text="0")

    def _mostrar_erro(self, msg: str):
        """Mostra uma mensagem de erro no display."""
        self._label_expr.configure(text=" ERRO!")
        self._label_display.configure(text="✗")
        self._janela.after(1500, self._limpar)

    # ─── Modo Angular (DEG/RAD) ─────────────────────────────────

    def _alternar_modo_angulo(self):
        """Alterna entre graus (DEG) e radianos (RAD)."""
        if self._modo_angulo == "deg":
            self._modo_angulo = "rad"
            self._label_modo.configure(
                text="RAD",
                fg=self.CORES["btn_eq"],
            )
        else:
            self._modo_angulo = "deg"
            self._label_modo.configure(
                text="DEG",
                fg=self.CORES["text_display"],
            )
        self.calc.angulo_modo = self._modo_angulo

    # ─── Operações de Memória ────────────────────────────────────

    def _memoria_guardar(self):
        try:
            self.calc.memoria_guardar(self._obter_valor_atual())
        except ValueError:
            pass

    def _memoria_recuperar(self):
        valor_str = formatar_numero(self.calc.memoria)
        if self._mostrando_resultado or not self._expressao:
            self._expressao = valor_str
            self._mostrando_resultado = False
        else:
            self._expressao += valor_str
        self._atualizar_display()

    def _memoria_somar(self):
        try:
            self.calc.memoria_somar(self._obter_valor_atual())
        except ValueError:
            pass

    def _memoria_subtrair(self):
        try:
            self.calc.memoria_subtrair(self._obter_valor_atual())
        except ValueError:
            pass

    def _memoria_limpar(self):
        self.calc.memoria_limpar()

    def _copiar_resultado(self):
        """Copia o resultado atual para a área de transferência."""
        self._janela.clipboard_clear()
        self._janela.clipboard_append(self._label_display.cget("text"))

    # ─── Execução ────────────────────────────────────────────────

    def iniciar(self):
        """Inicia o loop principal da interface."""
        self._janela.mainloop()


def main():
    """Função principal para executar a calculadora."""
    app = CalculadoraGUI("Calculadora Científica")
    app.iniciar()


if __name__ == "__main__":
    main()
