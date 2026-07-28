"""
diagnostico_gui.py
==================
Abre uma janela para diagnosticar por que os botões não aparecem no agente_gui.py.
Execute: python diagnostico_gui.py
"""
import tkinter as tk
import sys

root = tk.Tk()
root.title("Diagnóstico GUI - Botões")
root.geometry("700x500")
root.configure(bg="#1e1e2e")

# Frame principal
main = tk.Frame(root, bg="#1e1e2e", padx=20, pady=20)
main.pack(fill=tk.BOTH, expand=True)

tk.Label(
    main, text="DIAGNÓSTICO DE RENDERIZAÇÃO", 
    font=("Segoe UI", 14, "bold"),
    fg="#cdd6f4", bg="#1e1e2e"
).pack(pady=(0, 20))

# Teste 1: Botões COM emoji (como está no agente_gui.py)
grupo1 = tk.LabelFrame(
    main, text="Botões COM emoji (igual ao agente_gui.py)",
    font=("Segoe UI", 10, "bold"),
    fg="#a6adc8", bg="#1e1e2e",
    relief=tk.GROOVE, bd=1,
    padx=10, pady=10
)
grupo1.pack(fill=tk.X, pady=(0, 15))

botoes_emoji = [
    ("🗑️  Nova Conversa", "#89b4fa"),
    ("📄  Exportar MD", "#89b4fa"),
    ("🌐  Exportar HTML", "#89b4fa"),
    ("🔌  Plugins", "#89b4fa"),
    ("💾  Salvar Histórico", "#89b4fa"),
    ("⚠️  Limpar (perigo)", "#f38ba8"),
]

for texto, cor in botoes_emoji:
    btn = tk.Button(
        grupo1, text=texto,
        font=("Segoe UI", 10),
        bg=cor, fg="#1e1e2e",
        relief=tk.FLAT, bd=0, padx=12, pady=4,
        cursor="hand2"
    )
    btn.pack(side=tk.LEFT, padx=(0, 6))

# Teste 2: Botões SEM emoji (versão simplificada)
grupo2 = tk.LabelFrame(
    main, text="Botões SEM emoji (alternativa)",
    font=("Segoe UI", 10, "bold"),
    fg="#a6adc8", bg="#1e1e2e",
    relief=tk.GROOVE, bd=1,
    padx=10, pady=10
)
grupo2.pack(fill=tk.X, pady=(0, 15))

botoes_texto = [
    ("[X] Nova Conversa", "#89b4fa"),
    ("[MD] Exportar MD", "#89b4fa"),
    ("[HTML] Exportar HTML", "#89b4fa"),
    ("[Plugin] Plugins", "#89b4fa"),
    ("[Save] Salvar", "#89b4fa"),
]

for texto, cor in botoes_texto:
    btn = tk.Button(
        grupo2, text=texto,
        font=("Segoe UI", 10),
        bg=cor, fg="#1e1e2e",
        relief=tk.FLAT, bd=0, padx=12, pady=4,
        cursor="hand2"
    )
    btn.pack(side=tk.LEFT, padx=(0, 6))

# Teste 3: Informações do sistema
info_frame = tk.LabelFrame(
    main, text="Informações do Sistema",
    font=("Segoe UI", 10, "bold"),
    fg="#a6adc8", bg="#1e1e2e",
    relief=tk.GROOVE, bd=1,
    padx=10, pady=10
)
info_frame.pack(fill=tk.X)

info_text = tk.Text(info_frame, height=8, font=("Consolas", 9),
    bg="#181825", fg="#cdd6f4",
    relief=tk.FLAT, bd=0, padx=8, pady=4)
info_text.pack(fill=tk.X)

# Coletar informações
import tkinter.font as tkfont
try:
    f = tkfont.Font(family="Segoe UI", size=10, exists=True)
    font_ok = f.measure("Teste")
    info_text.insert(tk.END, f"Fonte 'Segoe UI' disponível: SIM\n")
except:
    info_text.insert(tk.END, f"Fonte 'Segoe UI' disponível: NÃO\n")

# Testar se emoji renderiza
try:
    test_font = tkfont.Font(family="Segoe UI", size=10)
    emoji_width = test_font.measure("🗑️")
    text_width = test_font.measure("X")
    info_text.insert(tk.END, f"Emoji '🗑️' renderiza: {'SIM' if emoji_width > 0 else 'NÃO'}\n")
    info_text.insert(tk.END, f"Largura emoji: {emoji_width}px | Largura 'X': {text_width}px\n")
except Exception as e:
    info_text.insert(tk.END, f"Erro ao testar emoji: {e}\n")

info_text.insert(tk.END, f"\nPython: {sys.version.split()[0]}\n")
info_text.insert(tk.END, f"tkinter: {tk.TkVersion}\n")
info_text.insert(tk.END, f"OS: {sys.platform}\n")
info_text.insert(tk.END, f"\n👆 VOCÊ CONSEGUE VER OS BOTÕES ACIMA?\n")
info_text.insert(tk.END, f"   Grupo 1 (com emoji) aparece?   [ ] SIM  [ ] NÃO\n")
info_text.insert(tk.END, f"   Grupo 2 (sem emoji) aparece?   [ ] SIM  [ ] NÃO\n")
info_text.configure(state="disabled")

# Botão de fechar
tk.Button(
    main, text="Fechar Diagnóstico",
    font=("Segoe UI", 11, "bold"),
    bg="#89b4fa", fg="#1e1e2e",
    relief=tk.FLAT, bd=0, padx=20, pady=6,
    cursor="hand2",
    command=root.destroy
).pack(pady=(15, 0))

root.mainloop()
