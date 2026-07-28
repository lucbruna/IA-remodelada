"""
conftest.py — garante que os imports do projeto funcionem a partir de tests/.

Como os testes fazem `from agente_core import ...` e o pacote `core` vive na
raiz do projeto, adicionamos a raiz ao sys.path antes da coleta.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
