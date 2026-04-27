# 04 — `sql_parser.py`

## Propósito

Este é o **maior e mais importante módulo do projeto**. Ele transforma
uma string SQL bruta em uma estrutura de dados validada (`ParsedQuery`)
que todos os módulos seguintes consomem.

Responsabilidades:

1. **Normalizar** o SQL (espaços, case).
2. **Tokenizar** com expressões regulares.
3. **Detectar typos** em palavras-chave (`WHER`, `ANDDD`, `JON`, ...).
4. **Extrair** as cláusulas SELECT, FROM, JOIN…ON, WHERE.
5. **Validar** tabelas e colunas contra o `schema.py`.
6. **Validar** operadores (`=`, `>`, `<`, `<=`, `>=`, `<>`, `AND`).
7. **Devolver** um `ParsedQuery` ou levantar uma exceção específica.

## Como o módulo está estruturado

```
sql_parser.py
├── Exceções
│   ├── SQLValidationError(ValueError)
│   ├── UnknownTableError(SQLValidationError)
│   └── InvalidOperatorError(SQLValidationError)
├── Dataclasses (estruturas de saída)
│   ├── ColumnRef
│   ├── Condition
│   ├── JoinClause
│   └── ParsedQuery
├── Funções/constantes utilitárias (escopo do módulo)
│   ├── KEYWORDS, VALID_OPERATORS, SUPPORTED_SYMBOLS_TEXT
│   ├── _levenshtein()
│   ├── _looks_like_keyword()
│   ├── TOKEN_PATTERN (regex)
│   └── tokenize()
└── Classe SQLParser
    ├── parse()                          # ponto de entrada
    ├── _check_keyword_typos()
    ├── _find_keyword_positions()
    ├── _get_tokens_between()
    ├── _get_from_tokens()
    ├── _get_join_groups()
    ├── _get_where_tokens()
    ├── _parse_from()
    ├── _parse_join()
    ├── _parse_select_columns()
    ├── _resolve_column_ref()
    ├── _parse_where()
    ├── _parse_single_condition()
    ├── _validate_tables()
    ├── _validate_columns()
    └── _validate_condition_columns()
```

## Exceções

```python
class SQLValidationError(ValueError):
    """Erro genérico de validação de SQL."""

class UnknownTableError(SQLValidationError):
    """Tabela referenciada não existe no schema."""
    def __init__(self, table_name, available_tables):
        self.table_name = table_name
        self.available_tables = available_tables
        super().__init__(...)

class InvalidOperatorError(SQLValidationError):
    """Operador ou palavra-chave inválida (ex: 'ANDDD', 'WHER')."""
```

Todas herdam de `ValueError` (compatibilidade) e de `SQLValidationError`
(específico do domínio). A GUI usa esses tipos para escolher **qual
diálogo mostrar**:

- `UnknownTableError` → diálogo "Tabela inexistente" com lista das
  tabelas disponíveis (`e.available_tables`).
- `InvalidOperatorError` → diálogo "Operador inválido" com lista de
  símbolos suportados.
- Demais `SQLValidationError`/`ValueError` → diálogo genérico de
  validação.

## Dataclasses

São contêineres de dados imutáveis-na-prática (sem `frozen=True`,
mas usados como tal). Servem para passar resultado do parser de forma
clara e tipada.

### `ColumnRef`

```python
@dataclass
class ColumnRef:
    table: str        # 'cliente' (sempre minúsculo)
    column: str       # 'nome'    (sempre minúsculo)
    original: str     # 'cliente.Nome' (como digitado pelo usuário)
```

Por que guardar `original`? Para poder mostrar ao usuário a mesma
grafia que ele digitou nas mensagens (e na álgebra relacional final).
Internamente, comparações usam `table` e `column` (já normalizados).

### `Condition`

```python
@dataclass
class Condition:
    left: ColumnRef               # sempre uma coluna no lado esquerdo
    operator: str                 # '=', '>', '<', '<=', '>=', '<>'
    right: "ColumnRef | str"      # coluna OU literal (número/string)
    original: str                 # texto formatado da condição
```

Decisão de projeto: **lado esquerdo é sempre coluna**. O lado direito
pode ser uma coluna (caso de `cliente.id = pedido.cliente_id`) ou um
**literal** (caso de `cliente.id = 1`). Quando é literal, é guardado
como `str` simples (ex.: `"1"` ou `"'texto'"`).

### `JoinClause`

```python
@dataclass
class JoinClause:
    table: str             # nome normalizado
    table_original: str    # como digitado
    condition: Condition   # condição do ON
```

Cada `JOIN ... ON ...` vira um `JoinClause`. Múltiplos JOINs viram
uma lista, na ordem em que aparecem na consulta.

### `ParsedQuery`

```python
@dataclass
class ParsedQuery:
    select_columns: list[ColumnRef]
    from_table: str                          # normalizado
    from_table_original: str                 # como digitado
    joins: list[JoinClause]
    where_conditions: list[Condition]
    all_tables: list[str]                    # todas as tabelas (norm)
    all_tables_original: dict[str, str]      # norm -> original
    original_sql: str                        # SQL completo digitado
```

É a **saída canônica** do parser. Nada de novo é gerado depois disto:
todos os outros módulos só **leem** o `ParsedQuery`.

`all_tables_original` (mapa norm → original) facilita exibir as tabelas
na grafia original em álgebra relacional, mesmo após normalização
interna.

## Constantes do módulo

```python
KEYWORDS         = {"SELECT", "FROM", "WHERE", "JOIN", "ON", "AND"}
VALID_OPERATORS  = {"=", ">", "<", "<=", ">=", "<>"}
SUPPORTED_SYMBOLS_TEXT = "=, >, <, <=, >=, <>, AND, ( )"
```

`SUPPORTED_SYMBOLS_TEXT` é só uma string formatada para mensagens de
erro — concentra o conteúdo num único ponto.

## Detecção de typos

### `_levenshtein(a, b) -> int`

Implementação clássica de **distância de Levenshtein** (programação
dinâmica em uma única linha de DP — usa só duas linhas vizinhas em
memória). Calcula o número mínimo de inserções, remoções ou
substituições para transformar `a` em `b`.

Usada para encontrar palavras-chave digitadas com erro: `WHER` está a
distância 1 de `WHERE`.

### `_looks_like_keyword(identifier) -> str | None`

Heurística que decide se um identificador parece ser uma palavra-chave
mal digitada. Duas estratégias combinadas:

1. **Substring/prefixo**: se a keyword cabe dentro do identificador e
   a diferença de tamanho é ≤ 3, retorna a keyword.
   Pega casos como `ANDDD`, `WHEREEE`.
   ```python
   if kw in up and abs(len(up) - len(kw)) <= 3:
       return kw
   ```

2. **Distância de edição**: se Levenshtein ≤ 1 (para keywords curtas)
   ou ≤ 2 (para keywords ≥ 5 letras), retorna a keyword.
   Pega casos como `WHER`, `JON`, `SELCT`.

Retorna `None` se o identificador não parece ser nenhum typo.

## Tokenizador

### A regex `TOKEN_PATTERN`

```python
TOKEN_PATTERN = re.compile(r"""
      (?P<NUMBER>\d+(?:\.\d+)?)
    | (?P<STRING>'[^']*')
    | (?P<DOTTED>[a-zA-Z_]\w*\s*\.\s*[a-zA-Z_]\w*)
    | (?P<WORD>[a-zA-Z_]\w*)
    | (?P<OP><=|>=|<>|[=<>])
    | (?P<COMMA>,)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<SEMI>;)
    | (?P<SKIP>\s+)
""", re.VERBOSE | re.IGNORECASE)
```

Cada **alternativa** tem um nome via `(?P<nome>...)`. Quando houver
match, `match.lastgroup` devolve o nome — assim o tokenizador sabe a
**categoria** do token.

Pontos sutis da regex:

- **Ordem importa**: `NUMBER` vem antes de `WORD` para que `123` seja
  reconhecido como número e não como início de identificador inválido.
- **`DOTTED` antes de `WORD`**: `cliente.nome` casa primeiro com
  `DOTTED` (devolvendo o token completo) antes de o regex tentar
  partir em `cliente`, `.`, `nome`.
- **`OP` reconhece operadores de 2 chars antes de 1 char**: `<=`, `>=`,
  `<>` antes de `<`, `>`, `=`. Sem isso, `<=` viraria dois tokens.
- **`SKIP`** captura whitespace para que o iterador continue avançando
  na string (no `tokenize()` esses tokens são descartados).
- **`re.VERBOSE`** permite quebrar a regex em várias linhas com
  comentários.

### `tokenize(sql) -> list[tuple[str, str]]`

Itera pelos matches da regex e devolve uma lista de tuplas
`(tipo, valor)`:

- `SKIP` e `SEMI` são **descartados** (espaços e ponto-e-vírgula).
- `WORD` é re-classificado: se está em `KEYWORDS`, vira `KEYWORD`
  (e o valor é convertido para maiúsculas); senão, vira `ID`.
- `DOTTED` tem espaços ao redor do `.` removidos:
  `cliente . nome` → `cliente.nome`.
- Demais tipos passam direto.

**Resultado típico:**

```
SQL: "SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 1"

Tokens:
  ("KEYWORD", "SELECT")
  ("DOTTED",  "cliente.Nome")
  ("KEYWORD", "FROM")
  ("ID",      "Cliente")
  ("KEYWORD", "WHERE")
  ("DOTTED",  "cliente.idCliente")
  ("OP",      ">")
  ("NUMBER",  "1")
```

## A classe `SQLParser`

### Estado

```python
def __init__(self):
    self.errors: list[str] = []
```

A lista `errors` é **populada durante o parsing** e, ao final, virada
em uma exceção. Erros não-fatais são acumulados (assim o usuário vê
todos de uma vez), exceto erros muito sérios que abortam imediatamente
(tabela inexistente, palavra-chave mal-digitada).

### Método público `parse(sql) -> ParsedQuery`

Este é o orquestrador. Em ordem:

1. **Limpar estado** (`self.errors = []`).
2. Validar **não vazio**.
3. **Normalizar**: `re.sub(r'\s+', ' ', sql).strip()` — colapsa
   qualquer sequência de espaços/tabs/quebras-de-linha em um único
   espaço.
4. **Tokenizar** (chama `tokenize` global).
5. **Checar typos** em palavras-chave (`_check_keyword_typos`). Se
   acharmos qualquer typo, levantamos `InvalidOperatorError`
   imediatamente — não faz sentido continuar parseando.
6. Validar que o **primeiro token é `SELECT`**.
7. Achar **posições** de cada palavra-chave (`_find_keyword_positions`).
8. Validar que existem `SELECT` e `FROM`.
9. **Fatiar** os tokens em sub-blocos: SELECT, FROM, JOIN…ON (vários),
   WHERE.
10. Parsear cada sub-bloco.
11. **Validar tabelas** primeiro (`_validate_tables`) — se uma tabela
    não existe, lançamos `UnknownTableError` direto, porque qualquer
    erro de coluna seria consequência.
12. **Validar colunas** (SELECT, ONs, WHERE).
13. Se sobraram erros em `self.errors`, decidir entre
    `InvalidOperatorError` e `SQLValidationError` baseado em
    palavras-chave do texto ("operador", "token", etc.).
14. **Retornar** `ParsedQuery`.

### Helpers de extração de tokens

#### `_find_keyword_positions(tokens) -> dict[str, list[int]]`

Devolve um dicionário do tipo:
```python
{
  "SELECT": [0],
  "FROM":   [3],
  "JOIN":   [5, 9],   # múltiplos JOINs!
  "ON":     [7, 11],
  "WHERE":  [13],
  "AND":    [17],
}
```

Note que cada keyword pode aparecer **várias vezes** (especialmente
`JOIN`, `ON` e `AND`). Por isso o valor é uma lista.

#### `_get_tokens_between(tokens, kw_positions, start_kw, end_kw)`

Pega tokens entre a primeira ocorrência de `start_kw` e a primeira de
`end_kw` (exclusivo). Usado para pegar tokens do SELECT (entre
`SELECT` e `FROM`).

#### `_get_from_tokens(tokens, kw_pos)`

Pega tokens depois de `FROM` até o próximo de: `JOIN`, `WHERE` ou fim
da consulta. Usa `min()` para pegar o mais próximo.

#### `_get_join_groups(tokens, kw_pos) -> list[tuple]`

A mais delicada. Para cada JOIN, devolve `(tokens_da_tabela, tokens_da_condicao)`:

- `tokens_da_tabela` = tokens entre `JOIN` e o `ON` correspondente.
- `tokens_da_condicao` = tokens depois do `ON` até o **próximo** JOIN,
  ou WHERE, ou fim.

Validação: o número de `JOIN` deve ser igual ao número de `ON`. Se não,
adiciona erro e devolve lista vazia.

#### `_get_where_tokens(tokens, kw_pos)`

Pega tudo depois do `WHERE` até o fim. Lista vazia se não houver WHERE.

### Parsing de cláusulas

#### `_parse_from(from_tokens) -> tuple[str, str]`

A `FROM` é a mais simples: deve ter **exatamente um** identificador
(o nome da tabela). Se houver tokens extras, é provável que o usuário
digitou uma keyword errada (ex.: `FROM Cliente WHER ...`) — registra
erro com sugestão.

Devolve `(original, normalizado_lowercase)`.

#### `_parse_join(table_tokens, cond_tokens, all_tables_original) -> JoinClause`

1. Pega o primeiro token do `table_tokens` como nome da tabela.
2. Tokens extras antes do `ON` → erro.
3. Atualiza o dict `all_tables_original` com a nova tabela.
4. Parseia a condição com `_parse_single_condition`.

#### `_parse_select_columns(select_tokens, all_tables) -> list[ColumnRef]`

Itera pelos tokens dividindo por vírgula:

```python
current_tokens = []
for ttype, tval in select_tokens:
    if ttype == "COMMA":
        # finalizar coluna atual
        col = self._resolve_column_ref(current_tokens, all_tables)
        if col: columns.append(col)
        current_tokens = []
    else:
        current_tokens.append((ttype, tval))
# último grupo
if current_tokens: ...
```

Resultado: lista de `ColumnRef`. Se nenhuma coluna foi extraída, erro.

#### `_resolve_column_ref(tokens, all_tables) -> ColumnRef | None`

Lógica para um único item:
- Se é `DOTTED` (`cliente.nome`): split no `.` e devolve `ColumnRef`.
- Se é `ID` (`nome`): chama `schema.resolve_column()` para descobrir
  a tabela. Se ambíguo ou inexistente, registra erro.
- Qualquer outra coisa (literal, operador, etc.) → erro.

#### `_parse_where(where_tokens, all_tables) -> list[Condition]`

Itera pelos tokens, separando em **grupos** delimitados por `AND`:

```python
for ttype, tval in where_tokens:
    if ttype == "KEYWORD" and tval == "AND":
        # finalizar condição atual
        cond = self._parse_single_condition(current, all_tables)
        if cond: conditions.append(cond)
        current = []
    elif ttype in ("LPAREN", "RPAREN"):
        continue   # parênteses ignorados (simplificação)
    else:
        current.append((ttype, tval))
# último grupo
```

**Limitação consciente**: parênteses são tratados como não significativos.
Isso aceita `(a > 1) AND (b = 0)` mas não suporta lógica complexa como
`(a > 1 AND b = 0) OR c = 5`. O escopo do trabalho exige apenas AND
plano, então isso é OK.

#### `_parse_single_condition(tokens, all_tables) -> Condition | None`

Espera o formato `LEFT OP RIGHT`:

1. Filtra parênteses.
2. Mínimo de 3 tokens (left, op, right).
3. Procura o primeiro `OP`. Sem operador → erro.
4. Splita em `left_tokens`, `operator`, `right_tokens`.
5. Valida operador contra `VALID_OPERATORS`.
6. **Tokens extras no lado direito**: erro (cobre o caso clássico
   `X = 0 ANDDD Y = 1`, onde depois do `0` aparece `ANDDD` não
   reconhecido). Para evitar duplicação de erros (se já foi reportado
   pelo `_check_keyword_typos`), só acrescenta se não pareça keyword.
7. Resolve `left` como `ColumnRef`.
8. Resolve `right`: pode ser `ColumnRef` (se `DOTTED`/`ID` resolvível),
   ou literal `str` (se `NUMBER`/`STRING` ou `ID` que não existe em
   nenhuma tabela).
9. Retorna `Condition`.

### Validações finais contra o schema

#### `_validate_tables(tables, tables_original)`

Itera pelas tabelas. Na primeira que não existir, **levanta
`UnknownTableError`** imediatamente — esse erro é severo o bastante
para abortar o parsing.

#### `_validate_columns(columns)`

Para cada coluna do SELECT, checa se existe na sua tabela. Se não,
acrescenta erro à lista (não aborta — coleta todos os erros de uma vez).

#### `_validate_condition_columns(cond)`

Mesma ideia, mas para condições do ON e WHERE: checa lado esquerdo
sempre, e lado direito só se for `ColumnRef` (literais não validamos).

## Fluxo end-to-end (exemplo)

Entrada:
```sql
SELECT cliente.Nome, pedido.idPedido
FROM Cliente
JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente
WHERE cliente.TipoCliente_idTipoCliente = 1
```

Resultado (`ParsedQuery`):
```python
ParsedQuery(
  select_columns=[
    ColumnRef("cliente", "nome", "cliente.Nome"),
    ColumnRef("pedido", "idpedido", "pedido.idPedido"),
  ],
  from_table="cliente",
  from_table_original="Cliente",
  joins=[
    JoinClause(
      table="pedido",
      table_original="Pedido",
      condition=Condition(
        left=ColumnRef("cliente","idcliente","cliente.idCliente"),
        operator="=",
        right=ColumnRef("pedido","cliente_idcliente","pedido.Cliente_idCliente"),
        original="cliente.idCliente = pedido.Cliente_idCliente",
      ),
    ),
  ],
  where_conditions=[
    Condition(
      left=ColumnRef("cliente","tipocliente_idtipocliente","cliente.TipoCliente_idTipoCliente"),
      operator="=",
      right="1",
      original="cliente.TipoCliente_idTipoCliente = 1",
    ),
  ],
  all_tables=["cliente", "pedido"],
  all_tables_original={"cliente": "Cliente", "pedido": "Pedido"},
  original_sql="SELECT cliente.Nome, pedido.idPedido FROM Cliente ...",
)
```

## O que este módulo **não** faz

- Não suporta `OR` ou `NOT` no WHERE — apenas `AND`.
- Não suporta `GROUP BY`, `ORDER BY`, `HAVING`, `DISTINCT`, `LIMIT`,
  funções agregadas, subqueries.
- Não suporta `LEFT JOIN`/`RIGHT JOIN`/`OUTER JOIN`.
- Não suporta `*` (selecionar todas as colunas).
- Não suporta aliases (`SELECT c.Nome FROM Cliente c`).

Estas limitações são deliberadas: o trabalho restringe o escopo aos
itens listados em `KEYWORDS` e `VALID_OPERATORS`.
