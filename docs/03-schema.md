# 03 — `schema.py`

## Propósito

Define os **metadados** do banco de dados de referência. Em outras
palavras: é a "fonte da verdade" sobre quais tabelas e colunas existem.

Todos os outros módulos consultam este arquivo para validar entradas
do usuário. Se uma tabela ou coluna não está aqui, o parser rejeita a
consulta com erro.

O schema corresponde exatamente ao **diagrama de dados (Imagem 01) do
PDF do trabalho** — não invente novas tabelas, isso quebraria os testes.

## A constante `SCHEMA`

```python
SCHEMA: dict[str, list[str]] = {
    "categoria": ["idcategoria", "descricao"],
    "produto":   ["idproduto", "nome", "descricao", "preco",
                  "quantestoque", "categoria_idcategoria"],
    "tipocliente": ["idtipocliente", "descricao"],
    "cliente":     ["idcliente", "nome", "email", "nascimento",
                    "senha", "tipocliente_idtipocliente", "dataregistro"],
    "tipoendereco": ["idtipoendereco", "descricao"],
    "endereco":    ["idendereco", "enderecopadrao", "logradouro",
                    "numero", "complemento", "bairro", "cidade",
                    "uf", "cep", "tipoendereco_idtipoendereco",
                    "cliente_idcliente"],
    "telefone":    ["numero", "cliente_idcliente"],
    "status":      ["idstatus", "descricao"],
    "pedido":      ["idpedido", "status_idstatus", "datapedido",
                    "valortotalpedido", "cliente_idcliente"],
    "pedido_has_produto": ["idpedidoproduto", "pedido_idpedido",
                           "produto_idproduto", "quantidade",
                           "precounitario"],
}
```

### Detalhes importantes

- **Tudo em minúsculo.** Tanto chaves (nomes de tabelas) quanto valores
  (nomes de colunas) estão sempre em lowercase. Isso é a base da
  estratégia case-insensitive: para comparar, basta normalizar a
  entrada do usuário com `.lower()` e comparar.
- **Foreign keys** seguem a convenção `<tabela_referenciada>_<pk>`.
  Exemplo: `cliente_idcliente` em `pedido` aponta para `cliente.idcliente`.
- **Tabela ponte** `pedido_has_produto` representa a relação N-N
  entre `pedido` e `produto`.
- O dict é **ordenado** (Python 3.7+): a ordem de declaração é mantida
  ao iterar.

## Função `table_exists(table_name) -> bool`

```python
def table_exists(table_name: str) -> bool:
    return table_name.strip().lower() in SCHEMA
```

Verifica se uma tabela existe. Faz `strip()` para tolerar espaços e
`.lower()` para tornar case-insensitive.

**Onde é usada:** `sql_parser.SQLParser._validate_tables()` chama esta
função (indiretamente via `table_exists`) para garantir que toda tabela
referenciada na consulta existe.

## Função `get_table_columns(table_name) -> list[str]`

```python
def get_table_columns(table_name: str) -> list[str]:
    return SCHEMA.get(table_name.strip().lower(), [])
```

Retorna a lista de colunas de uma tabela. Devolve **lista vazia** se a
tabela não existe — não levanta exceção. Isso simplifica o código de
validação (você pode iterar sem precisar de try/except).

**Onde é usada:**
- `sql_parser._validate_columns()` — para gerar mensagem de erro
  contendo a lista de colunas válidas quando o usuário usa uma coluna
  inexistente.
- `resolve_column()` (logo abaixo) — para varrer todas as tabelas
  candidatas.

## Função `column_exists(table_name, column_name) -> bool`

```python
def column_exists(table_name: str, column_name: str) -> bool:
    columns = get_table_columns(table_name)
    return column_name.strip().lower() in columns
```

Combina as duas anteriores: pega as colunas da tabela e checa se a
coluna está lá. Case-insensitive em ambos os argumentos.

**Onde é usada:** o parser chama em três pontos durante a validação:
1. Cada coluna do `SELECT`.
2. Cada coluna em condições `ON` de `JOIN`.
3. Cada coluna em condições do `WHERE`.

## Função `resolve_column(column_name, available_tables) -> str`

A mais "inteligente" do módulo. Resolve o caso em que o usuário
digitou uma coluna **sem prefixo de tabela** (ex.: `nome` em vez de
`cliente.nome`).

```python
def resolve_column(column_name: str, available_tables: list[str]) -> str:
    col_lower = column_name.strip().lower()
    matches = []
    for table in available_tables:
        if col_lower in get_table_columns(table):
            matches.append(table.lower())

    if len(matches) == 0:
        raise ValueError("Coluna ... não encontrada ...")
    if len(matches) > 1:
        raise ValueError("Coluna ... é ambígua ...")
    return matches[0]
```

### Lógica passo a passo

1. Normaliza o nome da coluna (`.strip().lower()`).
2. Para cada tabela disponível na consulta, verifica se a coluna
   pertence a ela.
3. **Zero matches** → ninguém tem essa coluna → erro "não encontrada".
4. **Dois ou mais matches** → ambígua → erro pedindo para usar o
   formato `tabela.coluna`. Exemplo: a coluna `descricao` aparece em
   `categoria`, `tipocliente`, `tipoendereco` e `status`. Se o usuário
   escrever só `SELECT descricao FROM ...` envolvendo várias dessas
   tabelas, é impossível decidir qual ele quis.
5. **Um match único** → retorna o nome da tabela.

### Por que retornar só a tabela e não `(tabela, coluna)`?

Porque a coluna o caller já tem em mãos (foi ele quem passou).
A única informação nova é a qual tabela ela pertence.

**Onde é usada:** `sql_parser._resolve_column_ref()` — chamada quando
um token do tipo `ID` (identificador simples sem ponto) aparece em
SELECT, ON ou WHERE.

## Função `get_all_table_names() -> list[str]`

```python
def get_all_table_names() -> list[str]:
    return list(SCHEMA.keys())
```

Retorna a lista de todas as tabelas. Usada apenas em **mensagens de
erro**: quando uma tabela é inexistente, a `UnknownTableError` mostra
ao usuário a lista de tabelas válidas.

## Resumo do papel de `schema.py`

| Função | Para quem serve | Quando é chamada |
|--------|-----------------|------------------|
| `SCHEMA` (dict) | Todo o sistema | Sempre (referência fixa) |
| `table_exists` | Parser | Validação durante o parsing |
| `get_table_columns` | Parser, mensagens de erro | Validação e formatação de erros |
| `column_exists` | Parser | Validação de SELECT/ON/WHERE |
| `resolve_column` | Parser | Quando coluna vem sem prefixo de tabela |
| `get_all_table_names` | GUI/erros | Mensagens de "tabela inexistente" |

`schema.py` é **stateless** — não tem classes, não tem variáveis
globais mutáveis, não tem efeitos colaterais. Pode ser importado
livremente sem custo.

## Como você estende este módulo

Para adicionar uma nova tabela ou coluna:

1. Edite o dict `SCHEMA`.
2. **Use sempre minúsculo.**
3. Pronto — todos os módulos passam a aceitar a nova entrada
   automaticamente, porque consultam `SCHEMA` em runtime.

Não há código gerado, nem cache; basta reiniciar a GUI.
