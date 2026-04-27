# 07 — `query_tree.py`

## Propósito

Constrói a **árvore de operadores otimizada** em memória. Esta árvore
é a representação estrutural daquilo que `optimizer.py` produziu como
texto — agora numa forma que pode ser:

- Desenhada visualmente (Canvas do Tkinter, ver `gui.py`).
- Percorrida em post-order para gerar o plano de execução
  (`execution_plan.py`).
- Renderizada como texto identado (também usada na GUI, na aba
  "Árvore (Texto)").

A estrutura segue exatamente o exemplo "Montagem Árvore" do material
de referência:

```
                π cliente.nome, pedido.idPedido     <- RAIZ (projeção final)
                              |
              ⋈ cliente.idcliente = pedido.cliente_id  <- junção
              /                                  \
   π cliente.nome, cliente.idcliente     π pedido.idPedido, pedido.cliente_id
            |                                          |
   σ cliente.tipo = 1                    σ pedido.valor = 0
            |                                          |
        Cliente                                     Pedido           <- FOLHAS
```

## Estrutura do módulo

```
query_tree.py
├── enum NodeType        (TABLE, SELECTION, PROJECTION, JOIN)
├── @dataclass TreeNode  (nó da árvore)
└── class QueryTree
    ├── build()                    # ponto de entrada
    ├── _build_table_subtree()     # constrói uma "perna" da árvore
    └── to_text()                  # renderização ASCII
```

## Enum `NodeType`

```python
class NodeType(Enum):
    TABLE      = "table"
    SELECTION  = "selection"   # σ
    PROJECTION = "projection"  # π
    JOIN       = "join"        # ⋈
```

Os quatro tipos cobrem todas as operações que aparecem na árvore.
`gui.py` usa este enum para escolher **cores** dos nós no Canvas:

| Tipo | Cor de preenchimento | Cor da borda |
|------|----------------------|--------------|
| `TABLE` | amarelo pastel | laranja |
| `SELECTION` | azul pastel | azul |
| `PROJECTION` | verde pastel | verde |
| `JOIN` | rosa/salmão pastel | vermelho |

## Dataclass `TreeNode`

```python
@dataclass
class TreeNode:
    node_type: NodeType
    label: str                          # texto exibido no nó
    children: list = field(default_factory=list)
```

- **`label`** é a string já formatada com símbolos (`π col1, col2`,
  `σ cond`, `⋈ cond`, ou apenas o nome da tabela).
- **`children`** começa vazio (graças a `field(default_factory=list)`)
  e cresce conforme a árvore é montada.

Usar `field(default_factory=list)` em vez de `children: list = []`
**é obrigatório** com dataclasses: o segundo padrão compartilharia a
mesma lista entre todas as instâncias (bug clássico de Python).

## Classe `QueryTree`

### Estado

```python
def __init__(self, parsed_query: ParsedQuery, optimizer: QueryOptimizer):
    self.query = parsed_query
    self.optimizer = optimizer
    self.root: TreeNode = None
```

Recebe **ambos** o `ParsedQuery` (estrutura inicial) e o
`QueryOptimizer` (que carrega os resultados intermediários
`table_conditions` e `needed_columns`). Por isso, **`optimizer.optimize()`
deve já ter sido chamado** antes — caso contrário esses dois mapas
estão vazios e a árvore sai sem σ e sem π intermediários.

### Método `build() -> TreeNode`

Algoritmo bottom-up:

```python
def build(self) -> TreeNode:
    q = self.query
    opt = self.optimizer

    # 1) Construir subárvore para cada tabela
    all_tables_ordered = [q.from_table] + [j.table for j in q.joins]
    subtrees = {}
    for table in all_tables_ordered:
        table_orig = q.all_tables_original.get(table, table)
        subtrees[table] = self._build_table_subtree(table, table_orig, opt)

    # 2) Encadear junções (left-deep)
    current = subtrees[q.from_table]
    for join in q.joins:
        cond_str = format_condition(join.condition)
        join_node = TreeNode(
            node_type=NodeType.JOIN,
            label=f"⋈ {cond_str}",
            children=[current, subtrees[join.table]],
        )
        current = join_node

    # 3) Projeção final como raiz
    cols_str = format_select_columns(q.select_columns)
    root = TreeNode(
        node_type=NodeType.PROJECTION,
        label=f"π {cols_str}",
        children=[current],
    )

    self.root = root
    return root
```

Em prosa, etapa por etapa:

1. **Para cada tabela, construir uma "perna"** da árvore via
   `_build_table_subtree`. Cada perna pode ter até 3 níveis:
   tabela → σ → π. Mais sobre isso abaixo.
2. **Encadear as junções** da esquerda para a direita. A subárvore da
   tabela do FROM começa como `current`. Para cada JOIN, criamos um
   novo nó `JOIN` com filhos `[current, subtree_da_tabela_do_join]`,
   e fazemos `current = novo_join`. Isso constrói uma árvore
   **left-deep** (os JOINs antigos ficam embaixo à esquerda).
3. **Adicionar o π raiz** com as colunas do SELECT por cima de tudo.

### Método `_build_table_subtree(table_norm, table_orig, opt) -> TreeNode`

```python
def _build_table_subtree(self, table_norm, table_orig, opt):
    # 1) Folha: tabela
    node = TreeNode(node_type=NodeType.TABLE, label=table_orig)

    # 2) σ se há condições WHERE para esta tabela
    if table_norm in opt.table_conditions:
        conds = opt.table_conditions[table_norm]
        conds_str = " ∧ ".join(format_condition(c) for c in conds)
        node = TreeNode(
            node_type=NodeType.SELECTION,
            label=f"σ {conds_str}",
            children=[node],
        )

    # 3) π intermediário (apenas se há JOINs e colunas calculadas)
    has_joins = len(self.query.joins) > 0
    if has_joins and opt.needed_columns.get(table_norm):
        cols_str = ", ".join(opt.needed_columns[table_norm])
        node = TreeNode(
            node_type=NodeType.PROJECTION,
            label=f"π {cols_str}",
            children=[node],
        )

    return node
```

A função usa o **idiom funcional do Python** de "wrap and replace":
`node` é reatribuído a cada nível, sempre com o anterior como filho.
Resultado típico:

| Cenário | Estrutura da subárvore |
|---------|-------------------------|
| Sem WHERE, sem JOIN | `Cliente` (só folha) |
| Com WHERE, sem JOIN | `σ cond → Cliente` |
| Sem WHERE, com JOINs | `π cols → Cliente` |
| Com WHERE, com JOINs | `π cols → σ cond → Cliente` |

A condição `has_joins` evita inserir π redundante quando ele seria
idêntico ao π raiz (mesma decisão tomada em `optimizer.py`).

### Método `to_text(...)` — render ASCII

```python
def to_text(self, node=None, prefix="", is_last=True, is_root=True) -> str:
    if node is None:
        node = self.root

    lines = []
    if is_root:
        lines.append(node.label)
    else:
        connector = "└── " if is_last else "├── "
        lines.append(prefix + connector + node.label)

    child_prefix = "" if is_root else prefix + ("    " if is_last else "│   ")

    for i, child in enumerate(node.children):
        is_last_child = (i == len(node.children) - 1)
        lines.append(self.to_text(child, child_prefix, is_last_child, False))

    return "\n".join(lines)
```

Renderização recursiva no estilo `tree`/`ls -l` — exibida na aba
"Árvore (Texto)" da GUI.

Saída típica:

```
π cliente.nome, pedido.idPedido
└── ⋈ cliente.idcliente = pedido.cliente_id
    ├── π cliente.nome, cliente.idcliente
    │   └── σ cliente.tipo = 1
    │       └── Cliente
    └── π pedido.idPedido, pedido.cliente_id
        └── σ pedido.valor = 0
            └── Pedido
```

A lógica dos prefixos:
- `└── ` para o último filho de um nível.
- `├── ` para os outros filhos.
- `│   ` para níveis acima de um filho não-último (mantém a "linha
  vertical").
- `    ` (quatro espaços) para níveis acima de um filho último (sem
  linha).

## Como o desenho visual usa este módulo

Em `gui.py`, a classe `TreeDrawer` recebe `root_node: TreeNode` e:

1. **Calcula posições** com layout simples:
   - Folhas recebem x sequencial (0, 1, 2, ...).
   - Nós internos recebem x = média dos filhos.
   - y = profundidade.
2. **Converte para pixels** multiplicando por `H_SPACING` e `V_SPACING`.
3. **Desenha arestas** com `canvas.create_line` e setas.
4. **Desenha nós** como retângulos arredondados (polígono com
   `smooth=True`) coloridos por tipo.

O algoritmo é simplista (não evita sobreposição em árvores muito
densas), mas funciona perfeitamente para o tamanho de árvore desse
projeto (até 4-5 JOINs).

## Como o `execution_plan.py` usa este módulo

Apenas pega `tree.root` e percorre em **post-order**:
- folhas (TABLE) primeiro,
- σ acima delas,
- π intermediários,
- ⋈ que conecta subárvores,
- π raiz por último.

Detalhes em `08-execution-plan.md`.

## Resumo da divisão de responsabilidades

| Aspecto | Quem decide |
|---------|-------------|
| Quais σ vão em cada tabela | `optimizer.py` (`table_conditions`) |
| Quais colunas projetar em cada tabela | `optimizer.py` (`needed_columns`) |
| **Estrutura** da árvore (quem é filho de quem) | `query_tree.py` |
| **Posição visual** dos nós | `gui.py` (`TreeDrawer`) |
| **Cores** dos nós | `gui.py` (mapas `NODE_COLORS`) |
| **Texto** dentro dos nós (label) | `query_tree.py` (usa helpers de `relational_algebra.py`) |

A separação é limpa: `query_tree.py` cuida de **estrutura**, `gui.py`
cuida de **apresentação**, `optimizer.py` cuida de **dados auxiliares**.
