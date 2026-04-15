"""
execution_plan.py - Geração do Plano de Execução

Percorre a árvore de operadores otimizada em post-order (folhas primeiro,
raiz por último) para gerar a ordem de execução que o banco de dados
seguiria passo a passo.

A travessia post-order garante que:
  - Tabelas são lidas antes de qualquer operação sobre elas
  - Seleções são aplicadas antes das projeções
  - Projeções são aplicadas antes das junções
  - A projeção final é a última operação

Exemplo (para o arquivo "Montagem Arvore.txt"):
    Passo 1:  Ler tabela Tb1
    Passo 2:  Aplicar seleção (σ) — σ tb1.id > 300
    Passo 3:  Aplicar projeção (π) — π Pk, nome
    Passo 4:  Ler tabela Tb2
    Passo 5:  Aplicar projeção (π) — π Pk, fk
    Passo 6:  Aplicar junção (⋈) — ⋈ Tb1.pk = tb2.fk
    Passo 7:  Ler tabela Tb3
    Passo 8:  Aplicar seleção (σ) — σ tb3.sal <> 0
    Passo 9:  Aplicar projeção (π) — π Sal, fk
    Passo 10: Aplicar junção (⋈) — ⋈ tb2.pk = tb3.fk
    Passo 11: Aplicar projeção final (π) — π Tb1.Nome, tb3.sal
"""

from dataclasses import dataclass
from query_tree import TreeNode, NodeType, QueryTree


# Mapeamento de tipo de nó para descrição legível
OPERATION_NAMES = {
    NodeType.TABLE: "Ler tabela",
    NodeType.SELECTION: "Aplicar seleção (σ)",
    NodeType.PROJECTION: "Aplicar projeção (π)",
    NodeType.JOIN: "Aplicar junção (⋈)",
}


@dataclass
class ExecutionStep:
    """Um passo individual do plano de execução."""
    step_number: int
    operation: str      # nome da operação (ex: "Ler tabela")
    description: str    # detalhe (ex: "σ tb1.id > 300")
    node: TreeNode      # nó correspondente na árvore


class ExecutionPlanGenerator:
    """
    Gera o plano de execução a partir da árvore de operadores otimizada.

    Uso:
        generator = ExecutionPlanGenerator(query_tree)
        steps = generator.generate()
        texto = generator.format_plan()
    """

    def __init__(self, tree: QueryTree):
        self.tree = tree
        self.steps: list[ExecutionStep] = []

    def generate(self) -> list[ExecutionStep]:
        """
        Gera o plano de execução percorrendo a árvore em post-order.
        Retorna a lista ordenada de passos.
        """
        self.steps = []
        self._traverse_postorder(self.tree.root)
        return self.steps

    def _traverse_postorder(self, node: TreeNode) -> None:
        """
        Travessia post-order: visita todos os filhos primeiro,
        depois o nó atual. Isso garante que operações dependentes
        são executadas na ordem correta (bottom-up).
        """
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

    def format_plan(self) -> str:
        """Formata o plano de execução como texto legível para exibição."""
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
