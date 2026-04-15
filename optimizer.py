"""
optimizer.py - Otimização de Consultas via Heurísticas

Aplica duas heurísticas de otimização sobre a álgebra relacional:

1. HEURÍSTICA DE REDUÇÃO DE TUPLAS (push-down de σ):
   - Move seleções (σ) do nível global para junto das tabelas base.
   - Cada condição WHERE que referencia apenas UMA tabela é empurrada
     para ficar imediatamente acima dessa tabela.

   Exemplo:
     ANTES:  π cols (σ a.x>5 ∧ b.y=0 (A ⋈ c B))
     DEPOIS: π cols ((σ a.x>5 (A)) ⋈ c (σ b.y=0 (B)))

2. HEURÍSTICA DE REDUÇÃO DE ATRIBUTOS (push-down de π):
   - Insere projeções (π) após cada seleção/tabela para carregar
     apenas os campos necessários para o restante da consulta.
   - Colunas necessárias = colunas do SELECT + colunas dos JOIN ON.

   Exemplo:
     ANTES:  π cols ((σ a.x>5 (A)) ⋈ c (σ b.y=0 (B)))
     DEPOIS: π cols ((π a.col1,a.pk (σ a.x>5 (A))) ⋈ c (π b.col2,b.fk (σ b.y=0 (B))))
"""

from dataclasses import dataclass, field
from sql_parser import ParsedQuery, Condition, ColumnRef, JoinClause
from relational_algebra import (
    format_condition, format_select_columns,
    SIGMA, PI, JOIN_SYMBOL, AND_SYMBOL,
)


@dataclass
class OptimizationStep:
    """Representa um passo da otimização com nome, descrição e expressão resultante."""
    name: str
    description: str
    expression: str


class QueryOptimizer:
    """
    Aplica heurísticas de otimização a uma consulta parseada.

    Uso:
        optimizer = QueryOptimizer(parsed_query)
        steps = optimizer.optimize()
        # steps[0] = redução de tuplas
        # steps[1] = redução de atributos
    """

    def __init__(self, parsed_query: ParsedQuery):
        self.query = parsed_query
        self.steps: list[OptimizationStep] = []
        # Condições classificadas por tabela (preenchido durante otimização)
        self.table_conditions: dict[str, list[Condition]] = {}
        # Colunas necessárias por tabela (preenchido durante otimização)
        self.needed_columns: dict[str, list[str]] = {}

    def optimize(self) -> list[OptimizationStep]:
        """
        Executa todas as heurísticas em sequência e retorna os passos.
        """
        self.steps = []

        # Classificar condições WHERE por tabela
        self._classify_conditions()

        # Passo 1: Redução de tuplas
        expr1 = self._apply_tuple_reduction()
        self.steps.append(OptimizationStep(
            name="Heurística de Redução de Tuplas",
            description=(
                "Aplicar primeiro as operações de seleção que reduzem o número de tuplas.\n"
                "As seleções (σ) são empurradas para junto das tabelas base."
            ),
            expression=expr1,
        ))

        # Passo 2: Redução de atributos
        self._calculate_needed_columns()
        expr2 = self._apply_attribute_reduction()
        self.steps.append(OptimizationStep(
            name="Heurística de Redução de Atributos",
            description=(
                "Aplicar projeções (π) para reduzir o número de campos desnecessários.\n"
                "Cada tabela projeta apenas os campos utilizados no SELECT e nos JOINs."
            ),
            expression=expr2,
        ))

        return self.steps

    # -------------------------------------------------------------------
    # Classificação de condições
    # -------------------------------------------------------------------

    def _classify_conditions(self):
        """
        Classifica cada condição WHERE pela tabela a que pertence.
        Condições que referenciam UMA tabela vão para essa tabela.
        Condições multi-tabela ficam separadas (não são empurradas).
        """
        self.table_conditions = {}
        self._remaining_conditions = []  # condições que não podem ser empurradas

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

    # -------------------------------------------------------------------
    # Colunas necessárias por tabela
    # -------------------------------------------------------------------

    def _calculate_needed_columns(self):
        """
        Calcula as colunas mínimas necessárias para cada tabela.
        Uma coluna é necessária se aparece em:
          1) SELECT final
          2) Condições ON de algum JOIN
        As colunas do WHERE são consumidas pelo σ (abaixo do π),
        então não precisam ser incluídas no π.
        """
        self.needed_columns = {}

        # 1) Colunas do SELECT
        for col in self.query.select_columns:
            self.needed_columns.setdefault(col.table, [])
            if col.original not in self.needed_columns[col.table]:
                self.needed_columns[col.table].append(col.original)

        # 2) Colunas dos JOINs (ON conditions)
        for join in self.query.joins:
            cond = join.condition
            # Lado esquerdo do ON
            self.needed_columns.setdefault(cond.left.table, [])
            if cond.left.original not in self.needed_columns[cond.left.table]:
                self.needed_columns[cond.left.table].append(cond.left.original)
            # Lado direito do ON (se for coluna)
            if isinstance(cond.right, ColumnRef):
                self.needed_columns.setdefault(cond.right.table, [])
                if cond.right.original not in self.needed_columns[cond.right.table]:
                    self.needed_columns[cond.right.table].append(cond.right.original)

    # -------------------------------------------------------------------
    # Geração de expressões textuais
    # -------------------------------------------------------------------

    def _wrap_table_with_sigma(self, table_norm: str, table_orig: str) -> str:
        """
        Envolve uma tabela com σ se houver condições WHERE para ela.
        Retorna: '(σ cond (Tabela))' ou apenas 'Tabela'.
        Parênteses externos garantem formatação correta na cadeia de junções.
        """
        if table_norm in self.table_conditions:
            conds = self.table_conditions[table_norm]
            conds_str = f" {AND_SYMBOL} ".join(format_condition(c) for c in conds)
            return f"({SIGMA} {conds_str} ({table_orig}))"
        return table_orig

    def _wrap_table_with_sigma_and_pi(self, table_norm: str, table_orig: str) -> str:
        """
        Envolve uma tabela com σ e π conforme as heurísticas.
        Retorna: '(π cols (σ cond (Tabela)))' ou '(π cols (Tabela))'.
        Parênteses externos garantem formatação correta na cadeia de junções.
        """
        # Se não há JOINs, o pi intermediário é desnecessário (idêntico ao final)
        has_joins = len(self.query.joins) > 0

        # Primeiro, aplica sigma (se necessário) — sem parênteses externos aqui,
        # pois o pi externo já vai envolver tudo
        if table_norm in self.table_conditions:
            conds = self.table_conditions[table_norm]
            conds_str = f" {AND_SYMBOL} ".join(format_condition(c) for c in conds)
            inner = f"{SIGMA} {conds_str} ({table_orig})"
        else:
            inner = table_orig

        # Depois, aplica pi (se há colunas necessárias e existem JOINs)
        if has_joins and table_norm in self.needed_columns and self.needed_columns[table_norm]:
            cols_str = ", ".join(self.needed_columns[table_norm])
            return f"({PI} {cols_str} ({inner}))"

        # Sem pi, mas se tem sigma, retornar com parênteses externos
        if table_norm in self.table_conditions:
            return f"({inner})"

        return inner

    def _build_join_chain(self, table_wrapper) -> str:
        """
        Constrói a cadeia de junções usando uma função wrapper para cada tabela.
        table_wrapper: função(table_norm, table_orig) -> string da subexpressão.
        """
        q = self.query
        left_expr = table_wrapper(q.from_table, q.from_table_original)

        if not q.joins:
            return left_expr

        for join in q.joins:
            right_expr = table_wrapper(join.table, join.table_original)
            cond_str = format_condition(join.condition)
            left_expr = f"({left_expr} {JOIN_SYMBOL} {cond_str} {right_expr})"

        return left_expr

    def _apply_tuple_reduction(self) -> str:
        """
        Gera a expressão após aplicar a heurística de redução de tuplas.
        """
        cols_str = format_select_columns(self.query.select_columns)
        join_expr = self._build_join_chain(self._wrap_table_with_sigma)

        # Se houver condições remanescentes (multi-tabela), manter sigma global
        if self._remaining_conditions:
            remaining_str = f" {AND_SYMBOL} ".join(
                format_condition(c) for c in self._remaining_conditions
            )
            return f"{PI} {cols_str} ({SIGMA} {remaining_str} ({join_expr}))"

        return f"{PI} {cols_str} ({join_expr})"

    def _apply_attribute_reduction(self) -> str:
        """
        Gera a expressão após aplicar a heurística de redução de atributos.
        """
        cols_str = format_select_columns(self.query.select_columns)
        join_expr = self._build_join_chain(self._wrap_table_with_sigma_and_pi)

        if self._remaining_conditions:
            remaining_str = f" {AND_SYMBOL} ".join(
                format_condition(c) for c in self._remaining_conditions
            )
            return f"{PI} {cols_str} ({SIGMA} {remaining_str} ({join_expr}))"

        return f"{PI} {cols_str} ({join_expr})"
