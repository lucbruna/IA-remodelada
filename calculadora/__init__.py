"""calculadora - Pacote de Calculadora com Interface Gráfica e Testes.

Módulos:
    core   - Lógica matemática, validação e histórico de operações.
    gui    - Interface gráfica Tkinter com display, botões e atalhos.
"""

from .core import Calculadora, Operacao, formatar_numero
from .gui import CalculadoraGUI

__all__ = ["Calculadora", "Operacao", "formatar_numero", "CalculadoraGUI"]
