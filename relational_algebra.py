"""
relational_algebra.py - Conversão de SQL para Álgebra Relacional

Converte um ParsedQuery (resultado do parser) em uma expressão
de álgebra relacional usando os símbolos padrão:

    σ (sigma)  - Seleção (filtro de tuplas / WHERE)
    π (pi)     - Projeção (filtro de colunas / SELECT)
    ⋈ (bowtie) - Junção (JOIN)
    ∧ (and)    - Conjunção lógica (AND)

Fluxo de conversão (baseado nos exemplos de referência):

  SQL: SELECT cols FROM T1 JOIN T2 ON c1 WHERE w1 AND w2
  AR:  π cols (σ w1 ∧ w2 (T1 ⋈ c1 T2))
"""

from sql_parser import ParsedQuery, Condition, ColumnRef


# Símbolos da álgebra relacional
SIGMA = "σ"
PI = "π"
JOIN_SYMBOL = "⋈"
AND_SYMBOL = "∧"


def format_condition(cond: Condition) -> str:
    """Formata uma condição como string: 'left op right'."""
    left_str = cond.left.original
    op = cond.operator
    if isinstance(cond.right, ColumnRef):
        right_str = cond.right.original
    else:
        right_str = str(cond.right)
    return f"{left_str} {op} {right_str}"


def format_select_columns(columns: list[ColumnRef]) -> str:
    """Formata a lista de colunas do SELECT como string separada por vírgula."""
    return ", ".join(col.original for col in columns)


class RelationalAlgebraConverter:
    """
    Converte um ParsedQuery em expressão de álgebra relacional.

    Exemplo de uso:
        converter = RelationalAlgebraConverter(parsed_query)
        expressao = converter.convert()
    """

    def __init__(self, parsed_query: ParsedQuery):
        self.query = parsed_query

    def convert(self) -> str:
        """
        Gera a expressão de álgebra relacional (conversão direta, sem otimização).

        Formato:
          - Com WHERE:  π cols (σ conds (joins))
          - Sem WHERE:  π cols (joins)
        """
        cols_str = format_select_columns(self.query.select_columns)
        join_expr = self._build_join_expression()

        if self.query.where_conditions:
            sigma_str = self._build_where_expression()
            return f"{PI} {cols_str} ({SIGMA} {sigma_str} ({join_expr}))"
        else:
            return f"{PI} {cols_str} ({join_expr})"

    def _build_join_expression(self) -> str:
        """
        Constrói a expressão de junção.

        - 0 JOINs: apenas o nome da tabela
        - 1 JOIN:  T1 ⋈ cond T2
        - N JOINs: (...(T1 ⋈ c1 T2) ⋈ c2 T3)... encadeado à esquerda
        """
        expr = self.query.from_table_original

        for join in self.query.joins:
            cond_str = format_condition(join.condition)
            expr = f"({expr} {JOIN_SYMBOL} {cond_str} {join.table_original})"

        return expr

    def _build_where_expression(self) -> str:
        """
        Constrói a expressão sigma com as condições do WHERE.
        Múltiplas condições unidas por ∧ (AND).
        """
        parts = [format_condition(c) for c in self.query.where_conditions]
        return f" {AND_SYMBOL} ".join(parts)
