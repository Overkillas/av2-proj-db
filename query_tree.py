"""
query_tree.py - Construção do Grafo (Árvore) de Operadores

Constrói em memória a árvore de operadores da consulta otimizada.

Estrutura da árvore:
    RAIZ:         Projeção final (π) com colunas do SELECT
    NÓS INTERNOS: Junções (⋈), Seleções (σ), Projeções intermediárias (π)
    FOLHAS:        Tabelas base

Exemplo (do arquivo 'Montagem Arvore.txt'):

                π Tb1.Nome, tb3.sal            <- RAIZ
                         |
                 ⋈ tb2.pk = tb3.fk             <- junção
                 /               \\
     ⋈ Tb1.pk = tb2.fk          |              <- junção
           /        \\             |
   π Pk, nome     π Pk,fk    π Sal, fk         <- projeções
         |             |            |
  σ tb1.id > 300      Tb2    σ tb3.sal <> 0    <- seleções ou tabelas
         |                          |
        Tb1                        Tb3          <- FOLHAS
"""

from enum import Enum
from dataclasses import dataclass, field
from sql_parser import ParsedQuery, Condition, ColumnRef
from optimizer import QueryOptimizer
from relational_algebra import format_condition, format_select_columns, SIGMA, PI, JOIN_SYMBOL, AND_SYMBOL


class NodeType(Enum):
    """Tipos de nós na árvore de operadores."""
    TABLE = "table"
    SELECTION = "selection"
    PROJECTION = "projection"
    JOIN = "join"


@dataclass
class TreeNode:
    """Nó da árvore de operadores."""
    node_type: NodeType
    label: str
    children: list = field(default_factory=list)


class QueryTree:
    """
    Constrói a árvore de operadores otimizada.

    A construção é bottom-up:
    1. Criar nós folha para cada tabela
    2. Aplicar σ sobre tabelas com condições WHERE
    3. Aplicar π sobre cada σ/tabela com colunas necessárias
    4. Construir junções conectando subárvores
    5. Aplicar projeção final como raiz

    Uso:
        tree = QueryTree(parsed_query, optimizer)
        root = tree.build()
    """

    def __init__(self, parsed_query: ParsedQuery, optimizer: QueryOptimizer):
        self.query = parsed_query
        self.optimizer = optimizer
        self.root: TreeNode = None

    def build(self) -> TreeNode:
        """Constrói a árvore completa e retorna o nó raiz."""
        q = self.query
        opt = self.optimizer

        # Construir subárvore para cada tabela (ordem: FROM, JOINs)
        all_tables_ordered = [q.from_table] + [j.table for j in q.joins]
        subtrees = {}

        for table in all_tables_ordered:
            table_orig = q.all_tables_original.get(table, table)
            subtrees[table] = self._build_table_subtree(table, table_orig, opt)

        # Encadear junções
        current = subtrees[q.from_table]
        for join in q.joins:
            cond_str = format_condition(join.condition)
            join_node = TreeNode(
                node_type=NodeType.JOIN,
                label=f"{JOIN_SYMBOL} {cond_str}",
                children=[current, subtrees[join.table]],
            )
            current = join_node

        # Projeção final (raiz)
        cols_str = format_select_columns(q.select_columns)
        root = TreeNode(
            node_type=NodeType.PROJECTION,
            label=f"{PI} {cols_str}",
            children=[current],
        )

        self.root = root
        return root

    def _build_table_subtree(self, table_norm: str, table_orig: str,
                             opt: QueryOptimizer) -> TreeNode:
        """
        Constrói a subárvore para uma tabela individual:
          π cols (σ cond (Tabela))
        ou
          π cols (Tabela)
        ou apenas
          Tabela (se não há otimizações aplicáveis)
        """
        # 1) Nó folha: tabela
        node = TreeNode(
            node_type=NodeType.TABLE,
            label=table_orig,
        )

        # 2) Envolver com σ se houver condições WHERE para esta tabela
        if table_norm in opt.table_conditions:
            conds = opt.table_conditions[table_norm]
            conds_str = f" {AND_SYMBOL} ".join(format_condition(c) for c in conds)
            sigma_node = TreeNode(
                node_type=NodeType.SELECTION,
                label=f"{SIGMA} {conds_str}",
                children=[node],
            )
            node = sigma_node

        # 3) Envolver com π se houver colunas necessárias calculadas
        #    Sem JOINs, o π intermediário seria idêntico ao final — omitir
        has_joins = len(self.query.joins) > 0
        if has_joins and table_norm in opt.needed_columns and opt.needed_columns[table_norm]:
            cols_str = ", ".join(opt.needed_columns[table_norm])
            pi_node = TreeNode(
                node_type=NodeType.PROJECTION,
                label=f"{PI} {cols_str}",
                children=[node],
            )
            node = pi_node

        return node

    def to_text(self, node: TreeNode = None, prefix: str = "",
                is_last: bool = True, is_root: bool = True) -> str:
        """
        Gera representação textual da árvore (formato tree).
        """
        if node is None:
            node = self.root
        if node is None:
            return "(árvore vazia)"

        lines = []

        if is_root:
            lines.append(node.label)
        else:
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + node.label)

        if is_root:
            child_prefix = ""
        else:
            child_prefix = prefix + ("    " if is_last else "│   ")

        for i, child in enumerate(node.children):
            is_last_child = (i == len(node.children) - 1)
            child_text = self.to_text(child, child_prefix, is_last_child, False)
            lines.append(child_text)

        return "\n".join(lines)
