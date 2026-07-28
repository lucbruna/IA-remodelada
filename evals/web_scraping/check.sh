#!/bin/bash
# Verifica se a resposta contém título e conteúdo
grep -q "Example Domain\|titulo" output.txt 2>/dev/null
