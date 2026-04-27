# 05 — `relational_algebra.py`

## Propósito

Converte um `ParsedQuery` em uma **string** de álgebra relacional usando
os símbolos clássicos: σ (seleção), π (projeção), ⋈ (junção), ∧ (AND).

Esta é a **conversão direta** — sem otimização nenhuma. É a "tradução
literal" do SQL: o que o WHERE diz vai para um único σ envolvendo tudo,
o SELECT vira um único π no topo, e os JOINs encadeiam-se da esquerda
para a direita.

A otimização propriamente dita acontece em `optimizer.py` (próximo
documento).

## Símbolos (constantes)

```python
SIGMA       = "σ"
PI          = "π"
JOIN_SYMBOL = "⋈"
AND_SYMBOL  = "∧"
```

Estes são caracteres **Unicode**. O Python lida com eles nativamente
(strings Python são Unicode por padrão), e o Tkinter os renderiza
corretamente nas fontes Consolas/Segoe UI usadas pela GUI.

Outros módulos (`optimizer.py`, `query_tree.py`) **importam estas
constantes** em vez de redeclará-las — assim você muda o símbolo num
único lugar e tudo se atualiza.

## Helpers públicos

### `format_condition(cond: Condition) -> str`

Formata uma `Condition` (do `sql_parser`) como string `"left op right"`.

```python
def format_condition(cond: Condition) -> str:
    left_str = cond.left.original
    op = cond.operator
    if isinstance(cond.right, ColumnRef):
        right_str = cond.right.original
    else:
        right_str = str(cond.right)
    return f"{left_str} {op} {right_str}"
```

Pontos importantes:

- Usa `cond.left.original` (texto digitado pelo usuário), **não**
  `cond.left.column` (lowercase). Isso preserva a grafia original na
  saída exibida.
- Trata o lado direito caso ele seja `ColumnRef` ou literal (string),
  pois `Condition.right` tem tipo união `ColumnRef | str`.

Exemplo:
```python
Condition(
  left=ColumnRef("cliente","nome","cliente.Nome"),
  operator="=",
  right="'João'",
)
# → "cliente.Nome = 'João'"
```

### `format_select_columns(columns: list[ColumnRef]) -> str`

Junta as colunas de um SELECT em uma string separada por vírgulas:

```python
def format_select_columns(columns: list[ColumnRef]) -> str:
    return ", ".join(col.original for col in columns)
```

Exemplo: `[cliente.Nome, pedido.idPedido]` → `"cliente.Nome, pedido.idPedido"`.

Estes dois helpers são **reutilizados** por `optimizer.py` e
`query_tree.py` — por isso ficam no escopo do módulo (e não como
métodos de uma classe).

## Classe `RelationalAlgebraConverter`

### Estado

```python
class RelationalAlgebraConverter:
    def __init__(self, parsed_query: ParsedQuery):
        self.query = parsed_query
```

Stateless além da query: cada conversão é independente e idempotente.

### Método `convert() -> str`

```python
def convert(self) -> str:
    cols_str = format_select_columns(self.query.select_columns)
    join_expr = self._build_join_expression()

    if self.query.where_conditions:
        sigma_str = self._build_where_expression()
        return f"{PI} {cols_str} ({SIGMA} {sigma_str} ({join_expr}))"
    else:
        return f"{PI} {cols_str} ({join_expr})"
```

Decisão por casos:

- **Com WHERE**: `π cols (σ conds (joins))`
- **Sem WHERE**: `π cols (joins)`

A diferença existe para evitar gerar uma seleção vazia (`σ  (...)`),
que seria sintaticamente esquisito e visualmente feio.

### Método `_build_join_expression() -> str`

```python
def _build_join_expression(self) -> str:
    expr = self.query.from_table_original
    for join in self.query.joins:
        cond_str = format_condition(join.condition)
        expr = f"({expr} {JOIN_SYMBOL} {cond_str} {join.table_original})"
    return expr
```

Comportamento por número de JOINs:

| #JOINs | Saída |
|--------|-------|
| 0 | `Cliente` |
| 1 | `(Cliente ⋈ cliente.idCliente = pedido.Cliente_idCliente Pedido)` |
| 2 | `((Cliente ⋈ ... Pedido) ⋈ ... Status)` |
| N | encadeado à esquerda, com parênteses crescentes |

A associação é à esquerda (left-deep tree) — escolha clássica em
projetos acadêmicos: simples de gerar e simples de visualizar.

### Método `_build_where_expression() -> str`

```python
def _build_where_expression(self) -> str:
    parts = [format_condition(c) for c in self.query.where_conditions]
    return f" {AND_SYMBOL} ".join(parts)
```

Junta múltiplas condições com `∧`. Como o parser separa o WHERE por
`AND` e elimina parênteses, este passo só precisa concatenar.

Exemplo: três condições resultam em
`a > 1 ∧ b = 0 ∧ c <> 5`.

## Exemplo end-to-end

Entrada SQL (referência `references/Select Exemplo 1.txt`):

```sql
SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
FROM Cliente
JOIN Pedido ON cliente.idcliente = pedido.Cliente_idCliente
WHERE cliente.TipoCliente_idTipoCliente = 1
  AND pedido.ValorTotalPedido = 0
```

Saída do `RelationalAlgebraConverter.convert()`:

```
π cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
  (σ cliente.TipoCliente_idTipoCliente = 1 ∧ pedido.ValorTotalPedido = 0
    (Cliente ⋈ cliente.idcliente = pedido.Cliente_idCliente Pedido))
```

(Na prática o resultado vem em uma única linha; quebrei aqui para
legibilidade.)

## Por que este módulo é tão pequeno

Porque o `ParsedQuery` já tem **toda** a informação estruturada. A
conversão para álgebra relacional é só "trocar palavras-chave SQL por
símbolos" — um trabalho puramente de formatação.

A complexidade real (otimização, montagem da árvore, plano de execução)
está nos módulos seguintes. Este módulo é a "ponte" mais simples do
pipeline.

## Onde este módulo é usado

- **`gui.py`**: ao processar uma consulta, chama `convert()` e exibe
  o resultado na aba "Álgebra Relacional".
- **`optimizer.py`**: importa as **constantes** (`SIGMA`, `PI`, etc.)
  e os **helpers** (`format_condition`, `format_select_columns`) para
  gerar suas próprias expressões otimizadas.
- **`query_tree.py`**: idem — importa constantes e helpers para
  rotular os nós da árvore.

Note que `optimizer.py` **não chama** `RelationalAlgebraConverter`.
Ele constrói as expressões otimizadas do zero (com aninhamento
diferente). O converter daqui só faz a versão "ingênua".
