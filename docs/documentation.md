# Documentação do Processador de Consultas SQL

Este diretório contém a documentação detalhada de **cada arquivo** do projeto.
Ela explica o que cada módulo faz, como ele funciona internamente, e como
ele se conecta com o restante do sistema.

A documentação está dividida em arquivos menores para facilitar a leitura.
Comece pela **visão geral** se for a primeira vez que você lê o projeto;
ela dá o panorama completo do fluxo de dados e mostra como os módulos
se encaixam.

---

## Índice

| # | Arquivo da documentação | Cobre o módulo | O que você aprende |
|---|---|---|---|
| 1 | [01-overview.md](01-overview.md) | (todos) | Arquitetura, fluxo end-to-end, ordem de execução, glossário |
| 2 | [02-main.md](02-main.md) | `main.py` | Ponto de entrada, como o programa é iniciado |
| 3 | [03-schema.md](03-schema.md) | `schema.py` | Metadados das tabelas, funções de validação |
| 4 | [04-sql-parser.md](04-sql-parser.md) | `sql_parser.py` | Tokenizer regex, parser, validações, dataclasses |
| 5 | [05-relational-algebra.md](05-relational-algebra.md) | `relational_algebra.py` | Conversão SQL → álgebra relacional |
| 6 | [06-optimizer.md](06-optimizer.md) | `optimizer.py` | Heurísticas de redução de tuplas e atributos |
| 7 | [07-query-tree.md](07-query-tree.md) | `query_tree.py` | Construção da árvore de operadores |
| 8 | [08-execution-plan.md](08-execution-plan.md) | `execution_plan.py` | Geração do plano de execução (post-order) |
| 9 | [09-gui.md](09-gui.md) | `gui.py` | Interface gráfica Tkinter, tema, callbacks, desenho da árvore |

Documentos de apoio que **já existiam** no repositório:

- [`tests.md`](tests.md) — Roteiro completo de testes manuais cobrindo as
  histórias de usuário (HU1 a HU5).
- [`../implementation_plan.md`](../implementation_plan.md) — Plano de
  implementação original com decisões de projeto.
- `../references/` — Materiais de referência (PDF do trabalho e
  arquivos `.txt` de exemplo).

---

## Estrutura do projeto

```
av2-alan/
├── main.py                    # Ponto de entrada (lança a GUI)
├── gui.py                     # Interface gráfica Tkinter
├── schema.py                  # Metadados (tabelas e colunas)
├── sql_parser.py              # Tokenizer + parser + validador
├── relational_algebra.py      # SQL → álgebra relacional
├── optimizer.py               # Heurísticas de otimização
├── query_tree.py              # Árvore de operadores em memória
├── execution_plan.py          # Plano de execução ordenado
├── requirements.txt           # Dependências (todas opcionais)
├── implementation_plan.md     # Plano de implementação original
├── docs/
│   ├── tests.md               # Roteiro de testes
│   └── (arquivos desta documentação)
└── references/                # Material de referência (PDF + .txt)
```

---

## Como ler esta documentação

A ordem natural de leitura é:

1. **`01-overview.md`** — Entenda o pipeline completo.
2. **`03-schema.md`** — A base de dados de metadados que tudo usa.
3. **`04-sql-parser.md`** — O parser é o maior módulo; lê o SQL e
   produz um `ParsedQuery` que alimenta todo o resto.
4. **`05-relational-algebra.md`** — A primeira transformação aplicada
   sobre o `ParsedQuery`.
5. **`06-optimizer.md`** — As heurísticas que reorganizam a expressão.
6. **`07-query-tree.md`** — A versão em árvore (DAG) da expressão otimizada.
7. **`08-execution-plan.md`** — Travessia post-order da árvore.
8. **`09-gui.md`** — A camada visual que orquestra todos os módulos
   anteriores.
9. **`02-main.md`** — Trivial; pode ler por último.
