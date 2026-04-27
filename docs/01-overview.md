# 01 — Visão Geral do Projeto

## O que é este projeto

Um **Processador de Consultas SQL** acadêmico. O usuário digita uma
consulta SQL na interface gráfica e o programa devolve, passo a passo,
tudo o que um SGBD faria internamente para processar essa consulta:

1. **Parsing e validação** da string SQL (tokens, sintaxe, schema).
2. **Conversão** da SQL em **álgebra relacional** (com símbolos σ, π, ⋈, ∧).
3. **Otimização** da álgebra usando heurísticas clássicas
   (push-down de seleção e projeção).
4. **Construção** da **árvore de operadores** otimizada (em memória e
   desenhada em um Canvas).
5. **Plano de execução** ordenado (post-order da árvore — passo a passo).

O modelo de dados é fixo: existe um schema embutido com 10 tabelas
(`cliente`, `pedido`, `produto`, ...) que o parser usa para validar
nomes de tabelas e colunas.

## Stack

- **Python 3.10+** (usa `dict[str, list[str]]`, union types `X | Y`,
  e `dataclasses`).
- **Tkinter** (já vem no Python padrão) — interface gráfica.
- **Sem dependências externas obrigatórias** (`requirements.txt` lista
  apenas dependências opcionais comentadas).

## Pipeline de execução completo

```
                     +---------------------------+
   string SQL  -->   |  sql_parser.SQLParser     |  -->  ParsedQuery
                     +---------------------------+

                     +-----------------------------------+
   ParsedQuery -->   | relational_algebra                |  -->  string AR
                     | RelationalAlgebraConverter        |       (não otimizada)
                     +-----------------------------------+

                     +---------------------------+
   ParsedQuery -->   |  optimizer.QueryOptimizer |  -->  list[OptimizationStep]
                     +---------------------------+       (2 passos: σ-push, π-push)
                                |
                                | preenche table_conditions
                                | e needed_columns (usados pela árvore)
                                v

                     +---------------------------+
   ParsedQuery + -->  | query_tree.QueryTree     |  -->  TreeNode (raiz)
   QueryOptimizer    +---------------------------+

                     +-------------------------------------+
   QueryTree   -->   | execution_plan.ExecutionPlanGenerator|  -->  list[ExecutionStep]
                     +-------------------------------------+

                     +---------------------------+
   tudo isso  -->    |  gui.ProcessadorConsultasGUI       |  --> renderiza nas abas
                     +---------------------------+
```

A `gui.py` é o **orquestrador**: ao apertar "Processar Consulta", ela
chama os módulos na ordem acima e atualiza cada uma das suas 5 abas.

## Dependências entre módulos (diagrama "quem importa quem")

```
main.py
  └── gui.py
        ├── schema.py
        ├── sql_parser.py
        │     └── schema.py
        ├── relational_algebra.py
        │     └── sql_parser.py (apenas dataclasses)
        ├── optimizer.py
        │     ├── sql_parser.py (dataclasses)
        │     └── relational_algebra.py (constantes e helpers)
        ├── query_tree.py
        │     ├── sql_parser.py (dataclasses)
        │     ├── optimizer.py
        │     └── relational_algebra.py
        └── execution_plan.py
              └── query_tree.py
```

Não há ciclos. A direção é sempre de cima para baixo (a GUI depende
de tudo, o `schema.py` não depende de nada).

## Cobertura das histórias de usuário (HU)

O `implementation_plan.md` mapeia cada peso/critério de avaliação a
uma HU. Aqui está a correspondência **HU → módulo**:

| HU  | Função                                        | Onde está implementado                  |
|-----|----------------------------------------------|-----------------------------------------|
| HU1 | Entrada e validação                           | `gui.py` + `sql_parser.py` + `schema.py`|
| HU2 | Conversão para álgebra relacional             | `relational_algebra.py`                 |
| HU3 | Construção/exibição do grafo de operadores    | `query_tree.py` + `gui.py` (Canvas)     |
| HU4 | Otimização via heurísticas                    | `optimizer.py`                          |
| HU5 | Plano de execução                             | `execution_plan.py`                     |

## Glossário rápido

| Símbolo | Nome | Significado |
|---------|------|-------------|
| **σ** (sigma) | Seleção | Filtra **linhas** (corresponde ao `WHERE`) |
| **π** (pi) | Projeção | Filtra **colunas** (corresponde ao `SELECT`) |
| **⋈** (bowtie) | Junção | Combina linhas de duas tabelas (corresponde ao `JOIN ... ON`) |
| **∧** | E lógico | Conecta duas condições (corresponde ao `AND`) |

| Termo | Significado neste projeto |
|-------|---------------------------|
| **`ParsedQuery`** | Dataclass produzida pelo parser; resultado canônico do parsing |
| **`ColumnRef`** | Referência a uma coluna `(tabela, coluna, original)` |
| **`Condition`** | `left OP right`, usada em ON e WHERE |
| **`JoinClause`** | Uma cláusula `JOIN tabela ON condição` |
| **`OptimizationStep`** | Um dos dois passos de otimização (push-down σ, push-down π) |
| **`TreeNode`** | Nó da árvore de operadores (TABLE, SELECTION, PROJECTION, JOIN) |
| **`ExecutionStep`** | Um passo individual do plano de execução |

## Convenções de código observadas

- **Tudo é case-insensitive** internamente. O parser converte tabelas e
  colunas para minúsculo via `.lower()`, mas guarda também o `original`
  digitado para exibição amigável.
- **Espaços extras** são colapsados com `re.sub(r'\s+', ' ', ...)` antes
  da tokenização.
- **Mensagens de erro são em português**, e o `sql_parser.py` define
  exceções específicas (`UnknownTableError`, `InvalidOperatorError`)
  que a GUI captura para mostrar diálogos personalizados.
- **Python type hints** modernos (`X | Y`, `list[Y]`, `dict[K, V]`)
  são usados consistentemente.
- O **bottom-up** da árvore reflete o bottom-up da otimização: primeiro
  σ próximo às folhas, depois π acima do σ, depois junções, e por fim
  a projeção final.

## Como executar

```cmd
cd C:\Users\kaike\Desktop\av2-alan
venv\Scripts\python.exe main.py
```

A janela abre com uma consulta de exemplo já preenchida. Basta clicar em
**▶ Processar Consulta** para ver os resultados nas abas.
