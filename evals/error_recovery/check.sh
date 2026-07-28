#!/bin/bash
# Verifica se houve tratamento de erro (não deve crashar)
grep -q "não é possível\|erro\|divisão\|impossível\|ZeroDivisionError" output.txt 2>/dev/null
