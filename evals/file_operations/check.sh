#!/bin/bash
# Verifica se o arquivo foi criado com o conteúdo correto
test -f test_output/hello.txt && grep -q "Hello, World!" test_output/hello.txt
