# 06 — `optimizer.py`

## Propósito

Aplica **heurísticas de otimização** sobre a álgebra relacional,
produzindo duas versões intermediárias progressivamente mais eficientes
da consulta.

As heurísticas são as duas mais clássicas dos cursos de banco de dados:

1. **Redução de tuplas** (push-down de σ): empurrar as seleções para
   junto das tabelas-base, para reduzir o número de linhas **antes**
   das junções.
2. **Redução de atributos** (push-down de π): inserir projeções
   intermediárias para descartar colunas que não são usadas mais
   adiante, reduzindo o tráfego de dados entre operações.

Além de gerar as **strings** de álgebra otimizada (exibidas na aba
"Otimização"), este módulo também **produz dois mapas auxiliares** que
o `query_tree.py` consome para construir a árvore visual:

- `table_conditions: dict[str, list[Condition]]` — quais condições WHERE
  vão ficar em cada tabela.
- `needed_columns: dict[str, list[str]]` — quais colunas cada tabela
  deve projetar.

## Estrutura do módulo

```
optimizer.py
├── @dataclass OptimizationStep
└── class QueryOptimizer
    ├── optimize()                          # ponto de entrada
    ├── _classify_conditions()              # bucket WHERE por tabela
    ├── _calculate_needed_columns()         # SELECT + JOIN ON
    ├── _wrap_table_with_sigma()            # tabela → "σ ... (T)"
    ├── _wrap_table_with_sigma_and_pi()     # tabela → "π ... (σ ... (T))"
    ├── _build_join_chain(wrapper)          # encadeia subexpressões
    ├── _apply_tuple_reduction()            # gera string do passo 1
    └── _apply_attribute_reduction()        # gera string do passo 2
```

## Dataclass `OptimizationStep`

```python
@dataclass
class OptimizationStep:
    name: str           # ex: "Heurística de Redução de Tuplas"
    description: str    # texto explicativo (mostrado na GUI)
    expression: str     # álgebra relacional resultante deste passo
```

A GUI lê esses três campos e renderiza um bloco por passo na aba
"Otimização".

## Classe `QueryOptimizer`

### Estado

```python
def __init__(self, parsed_query: ParsedQuery):
    self.query = parsed_query
    self.steps: list[OptimizationStep] = []
    self.table_conditions: dict[str, list[Condition]] = {}
    self.needed_columns: dict[str, list[str]] = {}
```

`table_conditions` e `needed_columns` ficam expostos como **atributos
públicos** porque `query_tree.py` lê ambos para montar a árvore. Não é
acidente: foi uma decisão deliberada para não duplicar lógica.

### Método `optimize() -> list[OptimizationStep]`

Pipeline de 4 etapas:

```python
def optimize(self) -> list[OptimizationStep]:
    self.steps = []
    self._classify_conditions()                           # 1
    expr1 = self._apply_tuple_reduction()                 # 2
    self.steps.append(OptimizationStep(name="...", ..., expression=expr1))
    self._calculate_needed_columns()                      # 3
    expr2 = self._apply_attribute_reduction()             # 4
    self.steps.append(OptimizationStep(name="...", ..., expression=expr2))
    return self.steps
```

Note a ordem: primeiro os filtros (σ), depois as projeções (π).
Isso reflete a heurística clássica: **filtrar tuplas antes de projetar
campos** porque (a) projeção pode descartar uma coluna usada em outro
filtro futuro e (b) a redução de tuplas tende a ter mais impacto.

### `_classify_conditions()` — bucketing do WHERE

```python
def _classify_conditions(self):
    self.table_conditions = {}
    self._remaining_conditions = []  # condições multi-tabela

    for cond in self.query.where_conditions:
        tables_in_cond = set()
        tables_in_cond.add(cond.left.table)
        if isinstance(cond.right, ColumnRef):
            tables_in_cond.add(cond.right.table)

        if len(tables_in_cond) == 1:
            table = list(tables_in_cond)[0]
            self.table_conditions.setdefault(table, []).append(cond)
        else:
            self._remaining_conditions.append(cond)
```

Para cada condição, descobrir **quantas tabelas distintas** ela toca:

- **1 tabela** → cabe na heurística: vai para `table_conditions[tabela]`.
- **2 tabelas** (ex.: `a.x = b.y`) → não pode ser empurrada (depende
  das duas tabelas), permanece em `self._remaining_conditions` no
  nível global do σ.

Exemplo:
```sql
WHERE cliente.tipo = 1 AND pedido.valor = 0 AND cliente.id <> pedido.cliente_id
```
→
```python
table_conditions = {
  "cliente": [Condition("cliente.tipo = 1")],
  "pedido":  [Condition("pedido.valor = 0")],
}
_remaining_conditions = [Condition("cliente.id <> pedido.cliente_id")]
```

### `_calculate_needed_columns()` — quais colunas projetar

A pergunta: **para cada tabela, quais colunas **precisam** sair dela**
(serão usadas downstream)?

A resposta:

1. **Colunas do SELECT final** que pertencem à tabela.
2. **Colunas usadas em condições JOIN ON** (de qualquer JOIN) que
   pertencem à tabela.

```python
# 1) SELECT
for col in self.query.select_columns:
    self.needed_columns.setdefault(col.table, [])
    if col.original not in self.needed_columns[col.table]:
        self.needed_columns[col.table].append(col.original)

# 2) JOINs
for join in self.query.joins:
    cond = join.condition
    self.needed_columns.setdefault(cond.left.table, [])
    if cond.left.original not in self.needed_columns[cond.left.table]:
        self.needed_columns[cond.left.table].append(cond.left.original)
    if isinstance(cond.right, ColumnRef):
        self.needed_columns.setdefault(cond.right.table, [])
        if cond.right.original not in self.needed_columns[cond.right.table]:
            self.needed_columns[cond.right.table].append(cond.right.original)
```

**Por que não incluir colunas do WHERE?** Porque a seleção (σ) é aplicada
**antes** da projeção (π) na árvore otimizada. Quando o π é aplicado,
o WHERE já foi consumido — e a coluna do WHERE só é necessária se ela
também aparece em SELECT ou JOIN, casos esses já cobertos pelas duas
regras acima.

**Por que `if col.original not in ...`?** Para não duplicar entradas
quando a mesma coluna aparece tanto no SELECT quanto num JOIN ON.

### `_wrap_table_with_sigma(table_norm, table_orig) -> str`

Helper para a primeira heurística. Dada uma tabela, devolve a string:

- Se há condições WHERE para ela: `(σ cond1 ∧ cond2 (Tabela))`
- Senão: `Tabela`

```python
def _wrap_table_with_sigma(self, table_norm, table_orig):
    if table_norm in self.table_conditions:
        conds = self.table_conditions[table_norm]
        conds_str = f" {AND_SYMBOL} ".join(format_condition(c) for c in conds)
        return f"({SIGMA} {conds_str} ({table_orig}))"
    return table_orig
```

### `_wrap_table_with_sigma_and_pi(table_norm, table_orig) -> str`

Helper para a segunda heurística. Combina σ e π:

```python
# Primeiro, monta a parte do σ
if table_norm in self.table_conditions:
    inner = f"σ ... ({table_orig})"
else:
    inner = table_orig

# Depois envolve com π — mas só se há JOINs!
has_joins = len(self.query.joins) > 0
if has_joins and self.needed_columns.get(table_norm):
    return f"(π cols ({inner}))"

# Sem π, mas com σ → mantém parênteses externos por consistência
if table_norm in self.table_conditions:
    return f"({inner})"
return inner
```

**Por que omitir π intermediário sem JOINs?** Sem JOINs, a árvore vira
`π cols (σ cond (Tabela))`. Inserir um π intermediário entre σ e π
final daria `π cols (π cols (σ cond (Tabela)))` — o π intermediário
seria idêntico ao final, redundante. A omissão deixa a saída mais
limpa.

### `_build_join_chain(table_wrapper) -> str`

Encadeia as junções aplicando uma função `wrapper` em cada tabela:

```python
def _build_join_chain(self, table_wrapper) -> str:
    q = self.query
    left_expr = table_wrapper(q.from_table, q.from_table_original)
    if not q.joins:
        return left_expr
    for join in q.joins:
        right_expr = table_wrapper(join.table, join.table_original)
        cond_str = format_condition(join.condition)
        left_expr = f"({left_expr} {JOIN_SYMBOL} {cond_str} {right_expr})"
    return left_expr
```

Esta função é **parametrizada pelo wrapper** — exatamente para que possa
ser reutilizada com `_wrap_table_with_sigma` (passo 1) e
`_wrap_table_with_sigma_and_pi` (passo 2). Isso evita duplicação de
código.

A associatividade é à esquerda (left-deep), igual ao `_build_join_expression`
do `relational_algebra.py`, mantendo consistência visual.

### `_apply_tuple_reduction() -> str`

```python
def _apply_tuple_reduction(self) -> str:
    cols_str = format_select_columns(self.query.select_columns)
    join_expr = self._build_join_chain(self._wrap_table_with_sigma)

    if self._remaining_conditions:
        remaining_str = f" {AND_SYMBOL} ".join(
            format_condition(c) for c in self._remaining_conditions
        )
        return f"{PI} {cols_str} ({SIGMA} {remaining_str} ({join_expr}))"

    return f"{PI} {cols_str} ({join_expr})"
```

Saída típica (com 1 JOIN e WHERE em ambas tabelas):
```
π cliente.nome, pedido.idPedido (
  (σ cliente.tipo = 1 (Cliente))
   ⋈ cliente.idcliente = pedido.cliente_id
  (σ pedido.valor = 0 (Pedido))
)
```

Se houver condições multi-tabela (`_remaining_conditions`), elas
permanecem num σ global no topo (acima das junções, abaixo do π
final).

### `_apply_attribute_reduction() -> str`

Mesma estrutura do método anterior, mas usando o wrapper que adiciona
π intermediário:

```
π cliente.nome, pedido.idPedido (
  (π cliente.nome, cliente.idcliente
    (σ cliente.tipo = 1 (Cliente)))
   ⋈ cliente.idcliente = pedido.cliente_id
  (π pedido.idPedido, pedido.cliente_id
    (σ pedido.valor = 0 (Pedido)))
)
```

Note que `cliente.idcliente` aparece no π de Cliente porque é usada na
condição do JOIN, mesmo não estando no SELECT final. Idem para
`pedido.cliente_id`.

## Comparação dos dois passos

```
ENTRADA (do relational_algebra.py):
  π cols (σ a.x>5 ∧ b.y=0 (A ⋈ c B))

PASSO 1 (redução de tuplas):
  π cols ((σ a.x>5 (A)) ⋈ c (σ b.y=0 (B)))

PASSO 2 (redução de atributos):
  π cols (
    (π a.col, a.pk (σ a.x>5 (A)))
     ⋈ c
    (π b.col, b.fk (σ b.y=0 (B)))
  )
```

A diferença visual é discreta, mas semanticamente importante: o passo 2
reduz a quantidade de **bytes** que cada subárvore propaga para cima.

## Limitações conscientes

- Não tenta reordenar JOINs por seletividade (heurística "mais
  restritivo primeiro"). A ordem dos JOINs segue a ordem digitada.
- Não detecta condições redundantes (`x > 5 AND x > 5`).
- Não combina condições contraditórias (`x > 5 AND x < 3`).
- Não trata `OR`.

Estas otimizações ficaram fora de escopo do trabalho.

## Como `query_tree.py` usa este módulo

Lê **três coisas** do `QueryOptimizer`:

1. `optimizer.table_conditions` — quais σ pôr em cada folha.
2. `optimizer.needed_columns` — quais π intermediários inserir.
3. `optimizer.query` — para ler `select_columns`, `joins`, etc.

Todos os mapas são preenchidos durante `optimize()`, então o
**usuário precisa chamar `optimize()` antes** de instanciar a
`QueryTree` (a GUI faz isso automaticamente).

## Como a GUI usa este módulo

```python
optimizer = QueryOptimizer(parsed)
steps = optimizer.optimize()
self._display_optimization(algebra_expr, steps)
```

Cada `OptimizationStep` vira um bloco "PASSO N — Nome" com a descrição
e a expressão resultante.
