"""
agente_gui.py
==============
Interface gráfica (tkinter) para o agente. Mostra a conversa, o passo a
passo das ferramentas em tempo real, e nunca trava a janela: as chamadas
ao modelo rodam em uma thread separada, com timeout de segurança vindo
do agente_core.

Melhorias desta versão:
  ✅ Campo de entrada MULTILINHA (Text widget) — escreva parágrafos inteiros
  ✅ Ctrl+Enter ou Ctrl+Return para enviar mensagem
  ✅ Ctrl+L para limpar conversa
  ✅ Ctrl+W para fechar
  ✅ Temas de cores refinados com cantos arredondados
  ✅ Exportação com filtro por data (diálogo de datas)

REQUISITOS:
  pip install ollama requests psutil PyPDF2 pillow pytesseract

COMO RODAR:
  python agente_gui.py
"""

import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog, simpledialog
import tkinter.font as tkfont
import time
from datetime import datetime
import sys
import re

from agente_core import (
    SYSTEM_PROMPT,
    MODEL,
    run_agent_turn,
    load_conversation_history,
    export_conversation_markdown,
    export_conversation_html,
    list_plugins,
    reload_plugins,
)


# ────────────────────────────────────────────────────────────────────
# FONTE UNIVERSAL (compatível com qualquer Windows)
# ────────────────────────────────────────────────────────────────────

def _detectar_fonte():
    """Detecta automaticamente a melhor fonte disponível no sistema.
    Tenta Segoe UI primeiro (mais bonita), se não existir usa Arial.
    """
    # NOTA: exists=True levanta TclError se a fonte nao existir
    # (medir com measure() nao funciona pois tkinter usa fallback silencioso)
    try:
        root = tk.Tk()
        root.withdraw()
        _ = tkfont.Font(family="Segoe UI", size=10, exists=True)
        root.destroy()
        return "Segoe UI"
    except Exception:
        pass
    # Arial existe em TODO Windows desde 1992
    return "Arial"

# Fonte universal: detectada automaticamente no momento do primeiro uso
FONTE = None  # será inicializado quando o Tk root for criado

# ────────────────────────────────────────────────────────────────────
# TEMA DE CORES
# ────────────────────────────────────────────────────────────────────

class Tema:
    """Paleta de cores centralizada para fácil customização."""
    BG_PRINCIPAL = "#1e1e2e"        # fundo geral
    BG_CHAT = "#181825"             # fundo da área de chat
    BG_INPUT = "#313244"            # fundo do campo de entrada
    BG_TOOLBAR = "#181825"          # fundo da barra de ferramentas
    FG_PRIMARY = "#cdd6f4"          # texto principal
    FG_SECONDARY = "#a6adc8"        # texto secundário
    BORDA = "#45475a"               # cor das bordas

    # Cores das mensagens
    USER_FG = "#89b4fa"             # azul claro (usuário)
    AGENT_FG = "#a6e3a1"            # verde claro (agente)
    SYSTEM_FG = "#6c7086"           # cinza (sistema)
    STEP_FG = "#f9e2af"             # amarelo (passos)
    ERROR_FG = "#f38ba8"            # vermelho (erros)
    INFO_FG = "#74c7ec"             # ciano (informação)
    SUCCESS_FG = "#a6e3a1"          # verde (sucesso)
    TIMESTAMP_FG = "#585b70"        # timestamp discreto

    # Botões
    BTN_BG = "#89b4fa"
    BTN_FG = "#1e1e2e"
    BTN_HOVER_BG = "#b4d0fb"
    BTN_DANGER_BG = "#f38ba8"
    BTN_DANGER_FG = "#1e1e2e"

    # Scrollbar
    SCROLL_BG = "#313244"
    SCROLL_FG = "#585b70"


class DateRangeDialog(tk.Toplevel):
    """Diálogo para entrada de range de datas e filtro por remetente."""

    ROLES = ["Todos", "user", "assistant", "tool"]
    ROLE_LABELS = ["Todos", "Usuário", "Agente", "Ferramenta"]

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Filtrar Exportação")
        self.configure(bg=Tema.BG_PRINCIPAL)
        self.resizable(False, False)
        self.result = None  # (start_date, end_date, role_filter) ou None

        # Centralizar
        self.transient(parent)
        self.grab_set()

        frame = tk.Frame(self, bg=Tema.BG_PRINCIPAL, padx=20, pady=16)
        frame.pack()

        tk.Label(
            frame, text="Filtrar mensagens por período",
            font=(FONTE, 11, "bold"),
            fg=Tema.FG_PRIMARY, bg=Tema.BG_PRINCIPAL
        ).pack(pady=(0, 12))

        # Data inicial
        row1 = tk.Frame(frame, bg=Tema.BG_PRINCIPAL)
        row1.pack(fill=tk.X, pady=4)
        tk.Label(
            row1, text="Data inicial:", font=(FONTE, 10),
            fg=Tema.FG_SECONDARY, bg=Tema.BG_PRINCIPAL, width=12, anchor="w"
        ).pack(side=tk.LEFT)
        self.start_entry = tk.Entry(
            row1, font=(FONTE, 10), width=14,
            bg=Tema.BG_INPUT, fg=Tema.FG_PRIMARY,
            relief=tk.FLAT, bd=0, insertbackground=Tema.FG_PRIMARY,
            highlightthickness=1, highlightbackground=Tema.BORDA,
        )
        self.start_entry.insert(0, "dd/mm/aaaa")
        self.start_entry.pack(side=tk.LEFT, padx=(0, 8))
        self.start_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(self.start_entry, "dd/mm/aaaa"))

        # Data final
        row2 = tk.Frame(frame, bg=Tema.BG_PRINCIPAL)
        row2.pack(fill=tk.X, pady=4)
        tk.Label(
            row2, text="Data final:", font=(FONTE, 10),
            fg=Tema.FG_SECONDARY, bg=Tema.BG_PRINCIPAL, width=12, anchor="w"
        ).pack(side=tk.LEFT)
        self.end_entry = tk.Entry(
            row2, font=(FONTE, 10), width=14,
            bg=Tema.BG_INPUT, fg=Tema.FG_PRIMARY,
            relief=tk.FLAT, bd=0, insertbackground=Tema.FG_PRIMARY,
            highlightthickness=1, highlightbackground=Tema.BORDA,
        )
        self.end_entry.insert(0, "dd/mm/aaaa")
        self.end_entry.pack(side=tk.LEFT)
        self.end_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(self.end_entry, "dd/mm/aaaa"))

        # Filtro por remetente
        row3 = tk.Frame(frame, bg=Tema.BG_PRINCIPAL)
        row3.pack(fill=tk.X, pady=(10, 4))
        tk.Label(
            row3, text="Remetente:", font=(FONTE, 10),
            fg=Tema.FG_SECONDARY, bg=Tema.BG_PRINCIPAL, width=12, anchor="w"
        ).pack(side=tk.LEFT)

        self.role_var = tk.StringVar(value="Todos")
        self.role_combo = ttk.Combobox(
            row3, textvariable=self.role_var,
            values=self.ROLE_LABELS,
            state="readonly", width=14,
            font=(FONTE, 10),
        )
        self.role_combo.pack(side=tk.LEFT)
        # Estilizar combobox para tema escuro
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
            fieldbackground=Tema.BG_INPUT,
            background=Tema.BTN_BG,
            foreground=Tema.FG_PRIMARY,
            arrowcolor=Tema.FG_PRIMARY,
            selectbackground=Tema.BG_INPUT,
            selectforeground=Tema.FG_PRIMARY,
        )

        # Ajuda
        tk.Label(
            frame, text="Deixe campos vazios e 'Todos' para exportar tudo.",
            font=(FONTE, 8), fg=Tema.TIMESTAMP_FG, bg=Tema.BG_PRINCIPAL
        ).pack(pady=(6, 0))

        # Botões
        btn_frame = tk.Frame(frame, bg=Tema.BG_PRINCIPAL)
        btn_frame.pack(pady=(12, 0))

        tk.Button(
            btn_frame, text="Exportar Tudo", font=(FONTE, 10),
            bg=Tema.BG_INPUT, fg=Tema.FG_PRIMARY,
            relief=tk.FLAT, bd=0, padx=16, pady=4,
            cursor="hand2",
            command=lambda: self._confirm("", "", ""),
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame, text="Filtrar", font=(FONTE, 10, "bold"),
            bg=Tema.BTN_BG, fg=Tema.BTN_FG,
            relief=tk.FLAT, bd=0, padx=20, pady=4,
            cursor="hand2",
            command=self._apply_filter,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame, text="Cancelar", font=(FONTE, 10),
            bg=Tema.BG_INPUT, fg=Tema.ERROR_FG,
            relief=tk.FLAT, bd=0, padx=12, pady=4,
            cursor="hand2",
            command=self.destroy,
        ).pack(side=tk.LEFT)

        self.start_entry.focus()

        # Atalho Enter para confirmar
        self.bind("<Return>", lambda e: self._apply_filter())
        self.bind("<Escape>", lambda e: self.destroy())

    def _clear_placeholder(self, entry, placeholder):
        if entry.get() == placeholder:
            entry.delete(0, tk.END)
            entry.configure(fg=Tema.FG_PRIMARY)

    def _validar_data(self, texto):
        """Valida se a data existe (dd/mm/aaaa ou dd/mm/aa)."""
        from datetime import datetime as dt
        if not texto.strip():
            return True  # vazio é válido
        try:
            data = texto.strip()
            if len(data) <= 8:
                dt.strptime(data, "%d/%m/%y")
            else:
                dt.strptime(data, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    def _apply_filter(self):
        start = self.start_entry.get().strip()
        end = self.end_entry.get().strip()

        # Se for placeholder, trata como vazio
        if start == "dd/mm/aaaa":
            start = ""
        if end == "dd/mm/aaaa":
            end = ""

        if start and not self._validar_data(start):
            messagebox.showwarning("Data inválida", "Data inicial inválida. Use o formato dd/mm/aaaa.")
            self.start_entry.focus()
            return
        if end and not self._validar_data(end):
            messagebox.showwarning("Data inválida", "Data final inválida. Use o formato dd/mm/aaaa.")
            self.end_entry.focus()
            return

        # Mapeia o label para o valor do role
        role_label = self.role_var.get()
        role_idx = self.ROLE_LABELS.index(role_label) if role_label in self.ROLE_LABELS else 0
        role_filter = self.ROLES[role_idx] if role_idx > 0 else ""

        self._confirm(start, end, role_filter)

    def _confirm(self, start, end, role_filter=""):
        self.result = (start, end, role_filter)
        self.destroy()


class AgenteGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Agente Local ({MODEL})")
        self.root.geometry("860x720")
        self.root.minsize(600, 500)
        self.busy = False
        self.message_count = 0
        self.start_time = time.time()

        # Inicializa fonte (usa Segoe UI se disponível, senão Arial)
        global FONTE
        if FONTE is None:
            FONTE = _detectar_fonte()

        # Aplicar tema escuro à janela
        self.root.configure(background=Tema.BG_PRINCIPAL)

        # Carregar histórico ou iniciar nova conversa
        self._load_history()

        # Criar interface
        self._create_widgets()

        # Atalhos de teclado globais
        self.root.bind("<Control-Return>", lambda e: self.send_message())
        self.root.bind("<Control-KP_Enter>", lambda e: self.send_message())
        self.root.bind("<Control-l>", lambda e: self.clear_conversation())
        self.root.bind("<Control-w>", lambda e: self._on_close())

        # Mensagem de boas-vindas
        if self.history_loaded is not None:
            count = len(self.history_loaded)
            self._append("Sistema", f"Histórico anterior carregado ({count} mensagens).", "system")
        self._append("Sistema", "Agente pronto. Pergunte algo ou peça uma tarefa.", "system")
        self._update_stats()

    def _load_history(self):
        """Carregar histórico de conversa"""
        try:
            history = load_conversation_history()
            if history:
                self.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
                    m for m in history if m.get("role") != "system"
                ]
                self.history_loaded = history
            else:
                self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                self.history_loaded = None
        except Exception as e:
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            self.history_loaded = None
            messagebox.showwarning("Aviso", f"Não foi possível carregar histórico: {e}")

    def _criar_botao(self, parent, text, command, bg=Tema.BTN_BG, fg=Tema.BTN_FG):
        """Cria um botão com hover effect."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=(FONTE, 10),
            bg=bg,
            fg=fg,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            activebackground=bg,
            activeforeground=fg,
        )

        def on_enter(e):
            btn.configure(bg=Tema.BTN_HOVER_BG)

        def on_leave(e):
            btn.configure(bg=bg)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def _create_widgets(self):
        """Criar todos os widgets da interface"""

        # ── Barra de ferramentas ─────────────────────────────────
        toolbar = tk.Frame(self.root, bg=Tema.BG_TOOLBAR)
        toolbar.pack(fill=tk.X, padx=0, pady=(0, 0))

        # Linha sutil embaixo da toolbar
        tk.Frame(toolbar, bg=Tema.BORDA, height=1).pack(fill=tk.X)

        inner_toolbar = tk.Frame(toolbar, bg=Tema.BG_TOOLBAR, padx=12, pady=8)
        inner_toolbar.pack(fill=tk.X)

        self.clear_btn = self._criar_botao(
            inner_toolbar, "🗑️  Nova Conversa", self.clear_conversation
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 6))

        # Separador visual
        tk.Frame(inner_toolbar, bg=Tema.BORDA, width=1, height=24).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        self.export_md_btn = self._criar_botao(
            inner_toolbar, "📄  Exportar MD", self._export_markdown_com_data
        )
        self.export_md_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.export_html_btn = self._criar_botao(
            inner_toolbar, "🌐  Exportar HTML", self._export_html_com_data
        )
        self.export_html_btn.pack(side=tk.LEFT, padx=(0, 6))

        # Separador visual
        tk.Frame(inner_toolbar, bg=Tema.BORDA, width=1, height=24).pack(
            side=tk.LEFT, padx=(8, 8)
        )

        self.plugins_btn = self._criar_botao(
            inner_toolbar, "🔌  Plugins", self.show_plugins
        )
        self.plugins_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.save_btn = self._criar_botao(
            inner_toolbar, "💾  Salvar Histórico", self.save_conversation
        )
        self.save_btn.pack(side=tk.LEFT)

        # Estatísticas
        self.stats_label = tk.Label(
            inner_toolbar,
            text="",
            font=(FONTE, 9),
            fg=Tema.FG_SECONDARY,
            bg=Tema.BG_TOOLBAR
        )
        self.stats_label.pack(side=tk.RIGHT)

        # ── Área de chat ─────────────────────────────────────────
        self.chat_frame = tk.Frame(self.root, bg=Tema.BG_CHAT)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 5))

        self.chat_area = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            state="disabled",
            font=(FONTE, 11),
            bg=Tema.BG_CHAT,
            fg=Tema.FG_PRIMARY,
            insertbackground=Tema.FG_PRIMARY,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=8,
            highlightthickness=0,
        )

        # Customizar scrollbar para combinar com o tema
        self.chat_area.configure(
            highlightbackground=Tema.BORDA,
            highlightcolor=Tema.BORDA,
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)

        # Configurar tags para diferentes tipos de mensagem
        self.chat_area.tag_config("user", foreground=Tema.USER_FG, font=(FONTE, 11))
        self.chat_area.tag_config("agent", foreground=Tema.AGENT_FG, font=(FONTE, 11))
        self.chat_area.tag_config("system", foreground=Tema.SYSTEM_FG, font=(FONTE, 10))
        self.chat_area.tag_config("step", foreground=Tema.STEP_FG, font=(FONTE, 9))
        self.chat_area.tag_config("error", foreground=Tema.ERROR_FG, font=(FONTE, 11, "bold"))
        self.chat_area.tag_config("info", foreground=Tema.INFO_FG, font=(FONTE, 10))
        self.chat_area.tag_config("success", foreground=Tema.SUCCESS_FG, font=(FONTE, 11))
        self.chat_area.tag_config("bold", font=(FONTE, 11, "bold"))
        self.chat_area.tag_config("timestamp", foreground=Tema.TIMESTAMP_FG, font=(FONTE, 9))
        self.chat_area.tag_config("header", foreground=Tema.FG_PRIMARY, font=(FONTE, 11, "bold"))

        # ── Frame inferior ────────────────────────────────────────
        bottom_frame = tk.Frame(self.root, bg=Tema.BG_PRINCIPAL)
        bottom_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        # Área de entrada de texto (MULTILINHA)
        input_frame = tk.Frame(bottom_frame, bg=Tema.BG_PRINCIPAL)
        input_frame.pack(fill=tk.X, pady=(0, 6))

        self.text_input = tk.Text(
            input_frame,
            height=3,
            font=(FONTE, 11),
            bg=Tema.BG_INPUT,
            fg=Tema.FG_PRIMARY,
            insertbackground=Tema.FG_PRIMARY,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=8,
            highlightthickness=1,
            highlightbackground=Tema.BORDA,
            highlightcolor=Tema.BTN_BG,
            wrap=tk.WORD,
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.text_input.focus()

        # Placeholder personalizado
        self._placeholder_ativo = True
        self._placeholder_texto = "Digite sua mensagem aqui... (Ctrl+Enter para enviar)"
        self._inserir_placeholder()

        self.text_input.bind("<FocusIn>", self._on_focus_in)
        self.text_input.bind("<FocusOut>", self._on_focus_out)
        self.text_input.bind("<KeyRelease>", self._on_key_release)

        self.send_button = self._criar_botao(
            input_frame,
            "Enviar\nCtrl+⏎",
            self.send_message,
            bg=Tema.BTN_BG,
            fg=Tema.BTN_FG,
        )
        self.send_button.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Barra de status ──────────────────────────────────────
        status_frame = tk.Frame(bottom_frame, bg=Tema.BG_PRINCIPAL)
        status_frame.pack(fill=tk.X)

        self.status_indicator = tk.Label(
            status_frame,
            text="●",
            fg=Tema.SUCCESS_FG,
            bg=Tema.BG_PRINCIPAL,
            font=(FONTE, 8),
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 4))

        self.status_label = tk.Label(
            status_frame,
            text="Pronto.",
            anchor="w",
            fg=Tema.FG_SECONDARY,
            bg=Tema.BG_PRINCIPAL,
            font=(FONTE, 9),
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Indicador de "pensando" (bolinhas animadas)
        self.pensando_label = tk.Label(
            status_frame,
            text="",
            fg=Tema.STEP_FG,
            bg=Tema.BG_PRINCIPAL,
            font=(FONTE, 10),
        )
        self.pensando_label.pack(side=tk.RIGHT, padx=(5, 0))

        # Progress bar (indeterminada)
        self.progress = ttk.Progressbar(
            status_frame,
            mode="indeterminate",
            length=80,
            maximum=10,
        )
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))

        # Personalizar progressbar para tema escuro
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Horizontal.TProgressbar",
            background=Tema.BTN_BG,
            troughcolor=Tema.BG_INPUT,
            bordercolor=Tema.BG_PRINCIPAL,
            lightcolor=Tema.BTN_BG,
            darkcolor=Tema.BTN_BG,
        )

        # ── Configurar fechamento ────────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Placeholder ───────────────────────────────────────────────

    def _inserir_placeholder(self):
        """Insere o placeholder no campo de texto."""
        self.text_input.delete("1.0", tk.END)
        self.text_input.insert("1.0", self._placeholder_texto)
        self.text_input.configure(fg=Tema.FG_SECONDARY)

    def _on_focus_in(self, event=None):
        """Remove o placeholder quando o campo recebe foco."""
        if self._placeholder_ativo:
            self.text_input.delete("1.0", tk.END)
            self.text_input.configure(fg=Tema.FG_PRIMARY)
            self._placeholder_ativo = False

    def _on_focus_out(self, event=None):
        """Reinsere o placeholder se o campo estiver vazio."""
        if not self.text_input.get("1.0", tk.END).strip():
            self._inserir_placeholder()
            self._placeholder_ativo = True

    def _on_key_release(self, event=None):
        """Atualiza placeholder e redimensiona o campo de texto."""
        conteudo = self.text_input.get("1.0", tk.END).strip()

        if not conteudo and not self._placeholder_ativo:
            self._inserir_placeholder()
            self._placeholder_ativo = True
        elif conteudo and self._placeholder_ativo:
            self._on_focus_in()

        # Auto-redimensionar altura do campo de texto (max 6 linhas)
        if conteudo:
            linhas = int(self.text_input.index("end-1c").split(".")[0])
            nova_altura = min(max(linhas, 2), 6)
            if nova_altura != int(self.text_input.cget("height")):
                self.text_input.configure(height=nova_altura)

    # ── Mensagens ─────────────────────────────────────────────────

    def _append(self, who, text, tag="system", timestamp=True):
        """Adicionar mensagem à área de chat formatada."""
        self.chat_area.configure(state="normal")

        # Adicionar timestamp
        if timestamp:
            time_str = datetime.now().strftime("%H:%M")
            self.chat_area.insert(tk.END, f"[{time_str}] ", "timestamp")

        # Adicionar nome do remetente com negrito
        self.chat_area.insert(tk.END, f"{who}: ", "bold")

        # Adicionar conteúdo com a tag apropriada
        self.chat_area.insert(tk.END, f"{text}\n\n", tag)
        self.chat_area.configure(state="disabled")

        # Scroll suave para o final
        self.chat_area.see(tk.END)

    def _update_stats(self):
        """Atualizar estatísticas da conversa."""
        runtime = int(time.time() - self.start_time)
        hours = runtime // 3600
        minutes = (runtime % 3600) // 60
        if hours > 0:
            time_str = f"{hours}h{minutes}m"
        else:
            time_str = f"{minutes}m"

        self.stats_label.config(text=f"Mensagens: {self.message_count}  •  Tempo: {time_str}")

    # ── Envio de mensagens ────────────────────────────────────────

    def send_message(self):
        """Enviar mensagem do usuário."""
        if self.busy:
            return

        if self._placeholder_ativo:
            return

        user_text = self.text_input.get("1.0", tk.END).strip()
        if not user_text:
            return

        # Limpar campo
        self.text_input.delete("1.0", tk.END)
        self.text_input.configure(height=2)
        self._placeholder_ativo = False
        self.text_input.focus()

        self.message_count += 1
        self._append("Você", user_text, "user")
        self._update_stats()

        # Comandos especiais
        if user_text.lower() == "nova conversa":
            self.clear_conversation()
            return
        elif user_text.lower() == "salvar":
            self.save_conversation()
            return
        elif user_text.lower() in ("ajuda", "help"):
            self._show_help()
            return

        self.busy = True
        self.send_button.config(state="disabled")
        self.clear_btn.config(state="disabled")
        self.export_md_btn.config(state="disabled")
        self.export_html_btn.config(state="disabled")
        self.plugins_btn.config(state="disabled")
        self.status_indicator.config(fg=Tema.STEP_FG)
        self.status_label.config(text="Processando...")
        self.progress.start()
        self._animar_pensando()

        thread = threading.Thread(target=self._run_agent, args=(user_text,), daemon=True)
        thread.start()

    def _animar_pensando(self):
        """Animação de bolinhas 'pensando'."""
        dots = ["", ".", "..", "...", ".."]

        def _update(i=0):
            if not self.busy:
                self.pensando_label.config(text="")
                return
            self.pensando_label.config(text=f"pensando{dots[i % len(dots)]}")
            self.root.after(400, _update, i + 1)

        _update()

    def _run_agent(self, user_text):
        """Executar agente em thread separada."""
        def on_step(text):
            self.root.after(0, lambda: self._append("⚙  Passo", text, "step", timestamp=True))
            self.root.after(0, lambda: self.status_label.config(text=text))

        try:
            self.messages.append({
                "role": "user",
                "content": user_text,
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            })
            self.messages = run_agent_turn(self.messages, model=MODEL, on_step=on_step)

            reply = ""
            for m in reversed(self.messages):
                if m.get("role") == "assistant" and m.get("content"):
                    reply = m["content"]
                    break

            self.root.after(0, self._show_reply, reply)
        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    def _show_reply(self, reply):
        """Mostrar resposta do agente."""
        self._append("Agente", reply or "(sem resposta)", "agent")
        self._restore_ui()

    def _show_error(self, error_text):
        """Mostrar erro."""
        self._append("Erro", error_text, "error")
        self.status_label.config(text="Erro — verifique logs.")
        self._restore_ui()

    def _restore_ui(self):
        """Restaurar interface ao estado normal."""
        self.progress.stop()
        self.busy = False
        self.send_button.config(state="normal")
        self.clear_btn.config(state="normal")
        self.export_md_btn.config(state="normal")
        self.export_html_btn.config(state="normal")
        self.plugins_btn.config(state="normal")
        self.status_indicator.config(fg=Tema.SUCCESS_FG)
        self.status_label.config(text="Pronto.")
        self.pensando_label.config(text="")
        self.text_input.focus()
        self._update_stats()

    # ── Exportação com filtro de data ────────────────────────────

    def _perguntar_datas(self):
        """Abre diálogo de range de datas. Retorna (start, end) ou None."""
        dialog = DateRangeDialog(self.root)
        self.root.wait_window(dialog)
        return dialog.result

    def _export_markdown_com_data(self):
        """Exporta Markdown com filtro por data e remetente."""
        filtros = self._perguntar_datas()
        if filtros is None:
            return  # cancelou

        start_date, end_date, role_filter = filtros

        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Todos", "*.*")],
            title="Exportar como Markdown",
        )
        if not filepath:
            return

        resultado = export_conversation_markdown(
            self.messages, filepath,
            start_date=start_date, end_date=end_date,
            role_filter=role_filter,
        )
        if "Nao ha mensagens" in resultado:
            self._append("Sistema", f"⚠ {resultado}", "system")
        elif resultado.startswith("Conversa exportada"):
            self._append("Sistema", f"✅ {resultado}", "success")
        else:
            self._append("Erro", resultado, "error")

    def _export_html_com_data(self):
        """Exporta HTML com filtro por data e remetente."""
        filtros = self._perguntar_datas()
        if filtros is None:
            return  # cancelou

        start_date, end_date, role_filter = filtros

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("Todos", "*.*")],
            title="Exportar como HTML",
        )
        if not filepath:
            return

        resultado = export_conversation_html(
            self.messages, filepath,
            start_date=start_date, end_date=end_date,
            role_filter=role_filter,
        )
        if "Nao ha mensagens" in resultado:
            self._append("Sistema", f"⚠ {resultado}", "system")
        elif resultado.startswith("Conversa exportada"):
            self._append("Sistema", f"✅ {resultado}", "success")
        else:
            self._append("Erro", resultado, "error")

    def show_plugins(self):
        """Mostra lista de plugins carregados."""
        plugins_info = list_plugins()
        self._append("🔌 Plugins", plugins_info, "info")

    def _show_help(self):
        """Mostrar ajuda."""
        help_text = """Comandos disponíveis:

• nova conversa — Reiniciar conversa (Ctrl+L)
• exportar MD — Exportar conversa como Markdown (com filtro de data)
• exportar HTML — Exportar conversa como HTML (com filtro de data)
• salvar — Salvar histórico interno
• ajuda/help — Mostrar esta mensagem

Atalhos de teclado:
• Ctrl+Enter — Enviar mensagem
• Ctrl+L — Nova conversa
• Ctrl+W — Fechar

Exportação com filtro de data:
  Antes de exportar, um diálogo permite escolher um período.
  Deixe os campos vazios para exportar tudo.

O agente pode:
• Responder perguntas
• Manipular arquivos e pastas
• Ler PDFs e imagens (OCR)
• Executar comandos e código Python
• Acessar URLs (se houver internet)
• Lembrar fatos entre conversas"""
        self._append("Ajuda", help_text, "info")

    def clear_conversation(self):
        """Limpar conversa atual."""
        if messagebox.askyesno(
            "Nova Conversa",
            "Deseja realmente reiniciar a conversa?\n(A memória de fatos continua intacta.)"
        ):
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            self.message_count = 0
            self.start_time = time.time()
            self.chat_area.configure(state="normal")
            self.chat_area.delete("1.0", tk.END)
            self.chat_area.configure(state="disabled")
            self._append("Sistema", "Conversa reiniciada. Memória de fatos continua guardada.", "system")
            self._update_stats()

    def save_conversation(self):
        """Salvar conversa atual."""
        try:
            from agente_core import save_conversation_history
            messages_to_save = [m for m in self.messages if m.get("role") != "system"]
            if messages_to_save:
                save_conversation_history(messages_to_save)
                self._append("Sistema", "Histórico salvo com sucesso!", "success")
            else:
                self._append("Sistema", "Nenhuma mensagem para salvar.", "system")
        except Exception as e:
            self._append("Erro", f"Erro ao salvar: {e}", "error")

    def _on_close(self):
        """Fechar aplicação."""
        if self.message_count > 0:
            resposta = messagebox.askyesnocancel(
                "Sair",
                "Deseja salvar o histórico antes de sair?",
            )
            if resposta is None:
                return  # cancelou
            elif resposta:
                self.save_conversation()
        self.root.destroy()


if __name__ == "__main__":
    # Verificar dependências essenciais
    try:
        import ollama
    except ImportError:
        messagebox.showerror(
            "Erro de Dependência",
            "Biblioteca 'ollama' não encontrada.\n\n"
            "Execute: pip install ollama"
        )
        sys.exit(1)

    try:
        root = tk.Tk()
        app = AgenteGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror(
            "Erro Fatal",
            f"Erro ao iniciar aplicação: {e}"
        )
        sys.exit(1)
