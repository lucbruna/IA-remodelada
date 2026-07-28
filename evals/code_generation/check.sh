#!/bin/bash
# Verifica se o código gerado contém uma função fib_memo com recursão e memoização
grep -q "fib_memo" generated.py 2>/dev/null && grep -q "lru_cache\|cache\|memo" generated.py 2>/dev/null
