# 08 — `execution_plan.py`

## Propósito

Gera o **plano de execução**: uma lista numerada de passos que
descrevem, na ordem que um SGBD executaria, todas as operações da
consulta otimizada.

A saída deste módulo aparece na aba "Plano de Execução" da GUI e é
o entregável final do pipeline.

## A ideia central: travessia post-order

Dada a árvore de operadores otimizada:

```
        π raiz
          |
          ⋈
        / \
       σ   π
       |   |
      A    σ
           |
           B
```

Uma **travessia post-order** (filhos primeiro, nó por último) visita os
nós nesta ordem:

```
1. A          (folha esquerda)
2. σ A        (σ acima de A)
3. B          (folha direita)
4. σ B        (σ acima de B)
5. π          (π acima do σ B)
6. ⋈          (junção)
7. π raiz     (projeção final)
```

Esse é exatamente o **plano de execução** de baixo para cima:
"primeiro leio a tabela, depois aplico filtro, depois projeto, depois
junto, depois projeto a saída final".

Note como a travessia post-order garante:

- Tabelas são lidas **antes** de qualquer operação sobre elas.
- Seleções (σ) são aplicadas **antes** das junções.
- Projeções intermediárias (π) reduzem dados **antes** das junções.
- A projeção final (π raiz) é a **última** operação.

## Estrutura do módulo

```
execution_plan.py
├── OPERATION_NAMES (dict)             # mapa tipo de nó → texto legível
├── @dataclass ExecutionStep
└── class ExecutionPlanGenerator
    ├── generate()              # gera lista de passos
    ├── _traverse_postorder()   # recursão
    └── format_plan()           # formata como texto para exibição
```

## Constante `OPERATION_NAMES`

```python
OPERATION_NAMES = {
    NodeType.TABLE:      "Ler tabela",
    NodeType.SELECTION:  "Aplicar seleção (σ)",
    NodeType.PROJECTION: "Aplicar projeção (π)",
    NodeType.JOIN:       "Aplicar junção (⋈)",
}
```

Mapa simples de **tipo de nó da árvore** para **texto exibido** ao
usuário. Centralizar aqui facilita traduzir tudo de uma vez se
necessário.

## Dataclass `ExecutionStep`

```python
@dataclass
class ExecutionStep:
    step_number: int    # 1-based
    operation: str      # ex: "Ler tabela"
    description: str    # ex: "Cliente"  ou  "σ cliente.tipo = 1"
    node: TreeNode      # referência ao nó original
```

`description` é exatamente o `label` do nó (ex.: `Cliente`,
`σ cliente.tipo = 1`, `π cliente.nome, pedido.idPedido`,
`⋈ cliente.idcliente = pedido.cliente_id`).

`node` é guardado para inspeção futura — útil se um dia você quiser,
por exemplo, exibir o subgrafo gerado por aquele passo.

## Classe `ExecutionPlanGenerator`

### Estado

```python
def __init__(self, tree: QueryTree):
    self.tree = tree
    self.steps: list[ExecutionStep] = []
```

A geração é determinística: chamar `generate()` duas vezes na mesma
árvore produz a mesma lista. `self.steps` é resetada em cada chamada.

### Método `generate() -> list[ExecutionStep]`

```python
def generate(self) -> list[ExecutionStep]:
    self.steps = []
    self._traverse_postorder(self.tree.root)
    return self.steps
```

Inicializa a lista vazia, dispara a travessia recursiva a partir da
raiz, e retorna a lista. Curto, mas o motor está em
`_traverse_postorder`.

### Método `_traverse_postorder(node)`

```python
def _traverse_postorder(self, node: TreeNode) -> None:
    if node is None:
        return

    for child in node.children:
        self._traverse_postorder(child)

    operation = OPERATION_NAMES.get(node.node_type, "Operação desconhecida")
    step = ExecutionStep(
        step_number=len(self.steps) + 1,
        operation=operation,
        description=node.label,
        node=node,
    )
    self.steps.append(step)
```

Pontos importantes:

- **Recursão simples**: visita todos os filhos primeiro
  (`for child in node.children`), depois processa o próprio nó. Esta é
  a definição de post-order.
- **`step_number = len(self.steps) + 1`**: numeração automática
  baseada no estado atual da lista. Como cada chamada acrescenta na
  ordem correta, os números saem em sequência sem precisar de contador
  separado.
- **Fallback "Operação desconhecida"**: defensivo. Não deveria
  acontecer (todos os tipos do enum estão no mapa), mas evita crash
  se alguém adicionar um novo `NodeType` sem atualizar o mapa.
- **Ordem dos filhos importa**: se a árvore tem `[esquerda, direita]`,
  esquerda é totalmente percorrida antes que direita comece. É o que
  produz a ordem esperada no plano (ex.: "ler Cliente antes de ler
  Pedido" porque Cliente é o filho esquerdo).

### Método `format_plan() -> str`

Formata a lista de passos como texto pronto para exibição:

```python
def format_plan(self) -> str:
    if not self.steps:
        return "(plano vazio)"

    lines = []
    lines.append("=" * 60)
    lines.append("  PLANO DE EXECUÇÃO")
    lines.append("=" * 60)
    lines.append("")

    max_num_width = len(str(len(self.steps)))

    for step in self.steps:
        num = str(step.step_number).rjust(max_num_width)
        lines.append(f"  Passo {num}:  {step.operation}")
        lines.append(f"  {'':>{max_num_width}}   └─ {step.description}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
```

Detalhes estéticos:

- `max_num_width = len(str(len(self.steps)))` calcula quantos
  caracteres ocupa o maior número (ex.: 11 passos → 2 caracteres),
  e usa isso para alinhar todos os números à direita com `.rjust()`.
- Cada passo tem **duas linhas**: a linha do número/operação, e uma
  linha de descrição com indentação `└─` (estética de árvore).
- `"=" * 60` desenha linhas horizontais delimitadoras.

Exemplo de saída:

```
============================================================
  PLANO DE EXECUÇÃO
============================================================

  Passo 1:  Ler tabela
            └─ Cliente

  Passo 2:  Aplicar seleção (σ)
            └─ σ cliente.TipoCliente_idTipoCliente = 1

  Passo 3:  Aplicar projeção (π)
            └─ π cliente.nome, cliente.idcliente

  Passo 4:  Ler tabela
            └─ Pedido

  Passo 5:  Aplicar seleção (σ)
            └─ σ pedido.ValorTotalPedido = 0

  Passo 6:  Aplicar projeção (π)
            └─ π pedido.idPedido, pedido.DataPedido, ...

  Passo 7:  Aplicar junção (⋈)
            └─ ⋈ cliente.idcliente = pedido.Cliente_idCliente

  Passo 8:  Aplicar projeção (π)
            └─ π cliente.nome, pedido.idPedido, ...

============================================================
```

## Como a GUI usa este módulo

```python
planner = ExecutionPlanGenerator(tree)
plan_steps = planner.generate()
plan_text = planner.format_plan()
self._display_plan(plan_text)
```

A GUI chama `generate()` (para obter a lista — não usa muito, mas é
chamada porque `format_plan()` depende dela ter sido executada) e
depois `format_plan()` (para o texto que vai na aba).

## Por que post-order e não pre-order ou in-order?

**Pre-order** (raiz → filhos) listaria a projeção final no passo 1,
o que não faz sentido como ordem de execução: você não pode projetar
o resultado final antes de ter os dados.

**In-order** (esquerda → raiz → direita) só funciona bem em árvores
binárias, e mesmo assim listaria operações intermediárias antes das
folhas — também invertido.

**Post-order** (filhos → raiz) é a ordem natural de execução de
qualquer expressão composta: você precisa do resultado de uma
sub-expressão antes de poder usá-la na expressão maior. É a mesma
razão por que pilhas de avaliação processam expressões dessa forma.

## Características importantes

- **Dependência única**: só `query_tree.py` (e indiretamente todo o
  resto via a árvore).
- **Stateless após `generate()`**: você pode chamar `format_plan()`
  quantas vezes quiser sem reexecutar a travessia.
- **Não modifica a árvore**: a travessia é apenas leitura.
- **Funciona com qualquer árvore válida**: se `query_tree.build()`
  produzir uma raiz válida, este módulo funciona — não importa quantos
  JOINs ou seleções existam.
