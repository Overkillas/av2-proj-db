"""
sql_parser.py - Parser e Validação de Consultas SQL

Responsável por:
- Normalizar a entrada (case-insensitive, espaços extras)
- Tokenizar a consulta SQL usando expressões regulares
- Extrair cláusulas SELECT, FROM, JOIN...ON, WHERE
- Validar tabelas e colunas contra o schema de metadados
- Validar operadores (=, >, <, <=, >=, <>, AND)

Comandos suportados: SELECT, FROM, WHERE, JOIN, ON
Operadores válidos: =, >, <, <=, >=, <>, AND, ( )
"""

import re
from dataclasses import dataclass, field
from schema import SCHEMA, table_exists, column_exists, resolve_column, get_table_columns, get_all_table_names


# ---------------------------------------------------------------------------
# Exceções específicas
# ---------------------------------------------------------------------------

class SQLValidationError(ValueError):
    """Erro genérico de validação de SQL."""
    pass


class UnknownTableError(SQLValidationError):
    """Tabela referenciada não existe no schema."""
    def __init__(self, table_name: str, available_tables: list[str]):
        self.table_name = table_name
        self.available_tables = available_tables
        msg = (
            f"Tabela '{table_name}' não existe no schema.\n"
            f"Tabelas disponíveis: {', '.join(sorted(available_tables))}"
        )
        super().__init__(msg)


class InvalidOperatorError(SQLValidationError):
    """Operador ou palavra-chave inválida (ex.: 'ANDDD', 'WHER')."""
    pass


# ---------------------------------------------------------------------------
# Estruturas de dados do resultado do parsing
# ---------------------------------------------------------------------------

@dataclass
class ColumnRef:
    """Referência a uma coluna no formato tabela.coluna."""
    table: str        # nome da tabela normalizado (minúsculo)
    column: str       # nome da coluna normalizado (minúsculo)
    original: str     # texto original digitado pelo usuário (ex: "cliente.Nome")


@dataclass
class Condition:
    """Condição de filtro ou junção: left operador right."""
    left: ColumnRef                # lado esquerdo (sempre coluna)
    operator: str                  # operador (=, >, <, <=, >=, <>)
    right: "ColumnRef | str"       # lado direito (coluna ou valor literal)
    original: str                  # condição completa como texto


@dataclass
class JoinClause:
    """Cláusula JOIN: tabela ON condição."""
    table: str               # nome da tabela normalizado
    table_original: str      # nome original digitado
    condition: Condition      # condição do ON


@dataclass
class ParsedQuery:
    """Resultado completo do parsing de uma consulta SQL."""
    select_columns: list[ColumnRef]          # colunas do SELECT
    from_table: str                           # tabela do FROM (normalizado)
    from_table_original: str                  # tabela do FROM (original)
    joins: list[JoinClause]                   # lista de JOINs
    where_conditions: list[Condition]         # condições do WHERE
    all_tables: list[str]                     # todas as tabelas (normalizado)
    all_tables_original: dict[str, str]       # normalizado -> original
    original_sql: str                         # SQL completo original


# ---------------------------------------------------------------------------
# Tokenizador
# ---------------------------------------------------------------------------

# Palavras-chave reconhecidas
KEYWORDS = {"SELECT", "FROM", "WHERE", "JOIN", "ON", "AND"}

# Operadores válidos
VALID_OPERATORS = {"=", ">", "<", "<=", ">=", "<>"}

# Texto exibido ao usuário com operadores/palavras-chave suportados
SUPPORTED_SYMBOLS_TEXT = "=, >, <, <=, >=, <>, AND, ( )"


def _levenshtein(a: str, b: str) -> int:
    """Distância de edição entre duas strings (para detectar typos)."""
    a, b = a.upper(), b.upper()
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def _looks_like_keyword(identifier: str) -> str | None:
    """
    Se o identificador parece uma palavra-chave mal digitada, retorna qual.
    Exemplos: 'WHER' -> 'WHERE', 'ANDDD' -> 'AND', 'JON' -> 'JOIN',
              'SELCT' -> 'SELECT', 'OR' -> 'ON' (operador não suportado).
    """
    up = identifier.upper()
    if up in KEYWORDS:
        return None  # já é a própria palavra-chave

    # 1) Match por substring/prefixo: ex. 'ANDDD' contém 'AND'
    for kw in KEYWORDS:
        if kw in up and abs(len(up) - len(kw)) <= 3:
            return kw

    # 2) Match por distância de edição (typos clássicos)
    for kw in KEYWORDS:
        dist = _levenshtein(up, kw)
        if dist == 0:
            continue
        max_dist = 2 if len(kw) >= 5 else 1
        if dist <= max_dist:
            return kw

    return None

# Padrão regex para tokenização
TOKEN_PATTERN = re.compile(
    r"""
      (?P<NUMBER>\d+(?:\.\d+)?)                         # números (inteiros ou decimais)
    | (?P<STRING>'[^']*')                                # strings entre aspas simples
    | (?P<DOTTED>[a-zA-Z_]\w*\s*\.\s*[a-zA-Z_]\w*)      # tabela.coluna
    | (?P<WORD>[a-zA-Z_]\w*)                             # palavra (keyword ou identificador)
    | (?P<OP><=|>=|<>|[=<>])                             # operadores de comparação
    | (?P<COMMA>,)                                       # vírgula
    | (?P<LPAREN>\()                                     # parêntese esquerdo
    | (?P<RPAREN>\))                                     # parêntese direito
    | (?P<SEMI>;)                                        # ponto e vírgula
    | (?P<SKIP>\s+)                                      # espaços (ignorados)
    """,
    re.VERBOSE | re.IGNORECASE
)


def tokenize(sql: str) -> list[tuple[str, str]]:
    """
    Divide a string SQL em uma lista de tokens (tipo, valor).
    Tipos possíveis: KEYWORD, DOTTED, ID, OP, NUMBER, STRING, COMMA, LPAREN, RPAREN
    """
    tokens = []
    for match in TOKEN_PATTERN.finditer(sql):
        kind = match.lastgroup
        value = match.group()

        if kind == "SKIP" or kind == "SEMI":
            continue

        if kind == "WORD":
            if value.upper() in KEYWORDS:
                tokens.append(("KEYWORD", value.upper()))
            else:
                tokens.append(("ID", value))

        elif kind == "DOTTED":
            # Remove espaços ao redor do ponto
            clean = re.sub(r'\s*\.\s*', '.', value)
            tokens.append(("DOTTED", clean))

        else:
            tokens.append((kind, value))

    return tokens


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

class SQLParser:
    """
    Parser de consultas SQL.

    Uso:
        parser = SQLParser()
        result = parser.parse("SELECT cliente.nome FROM cliente WHERE cliente.id > 5")
        # result é um ParsedQuery
        # parser.errors contém erros encontrados (se houver)
    """

    def __init__(self):
        self.errors: list[str] = []

    def parse(self, sql: str) -> ParsedQuery:
        """
        Método principal. Recebe SQL como string, retorna ParsedQuery.
        Levanta ValueError se houver erros de validação.
        """
        self.errors = []
        original_sql = sql.strip()

        if not original_sql:
            raise ValueError("Consulta SQL vazia.")

        # Normalizar: colapsar espaços múltiplos
        normalized = re.sub(r'\s+', ' ', original_sql).strip()

        # Tokenizar
        tokens = tokenize(normalized)
        if not tokens:
            raise ValueError("Não foi possível tokenizar a consulta SQL.")

        # Detectar palavras-chave mal digitadas (WHER, ANDDD, JON, SELCT, etc.)
        self._check_keyword_typos(tokens)
        if self.errors:
            raise InvalidOperatorError("\n".join(self.errors))

        # Verificar que começa com SELECT
        if tokens[0] != ("KEYWORD", "SELECT"):
            self.errors.append("A consulta deve começar com SELECT.")
            raise ValueError("\n".join(self.errors))

        # Encontrar posições das palavras-chave
        kw_positions = self._find_keyword_positions(tokens)

        # Validar estrutura básica
        if "SELECT" not in kw_positions or "FROM" not in kw_positions:
            self.errors.append("A consulta deve conter SELECT e FROM.")
            raise ValueError("\n".join(self.errors))

        # Extrair cada cláusula
        select_tokens = self._get_tokens_between(tokens, kw_positions, "SELECT", "FROM")
        from_tokens = self._get_from_tokens(tokens, kw_positions)
        join_groups = self._get_join_groups(tokens, kw_positions)
        where_tokens = self._get_where_tokens(tokens, kw_positions)

        # Parsear tabela FROM
        from_table_original, from_table = self._parse_from(from_tokens)

        # Coletar todas as tabelas (para resolver colunas sem prefixo)
        all_tables_original = {from_table: from_table_original}

        # Parsear JOINs
        joins = []
        for table_toks, cond_toks in join_groups:
            join_clause = self._parse_join(table_toks, cond_toks, all_tables_original)
            joins.append(join_clause)

        all_tables = list(all_tables_original.keys())

        # Validar tabelas contra o schema ANTES de validar colunas:
        # se a tabela não existe o erro de coluna seria acessório.
        # _validate_tables lança UnknownTableError diretamente.
        self._validate_tables(all_tables, all_tables_original)

        # Parsear colunas do SELECT
        select_columns = self._parse_select_columns(select_tokens, all_tables)

        # Parsear condições do WHERE
        where_conditions = self._parse_where(where_tokens, all_tables)

        # Validar colunas contra o schema
        self._validate_columns(select_columns)
        for join in joins:
            self._validate_condition_columns(join.condition)
        for cond in where_conditions:
            self._validate_condition_columns(cond)

        if self.errors:
            msg = "\n".join(self.errors)
            # Se algum dos erros menciona operador/token inesperado, classificar
            # como InvalidOperatorError para o front-end exibir mensagem específica.
            lowered = msg.lower()
            if any(k in lowered for k in (
                "operador", "token", "palavra-chave",
                "inválido", "inesperado",
            )):
                raise InvalidOperatorError(msg)
            raise SQLValidationError(msg)

        return ParsedQuery(
            select_columns=select_columns,
            from_table=from_table,
            from_table_original=from_table_original,
            joins=joins,
            where_conditions=where_conditions,
            all_tables=all_tables,
            all_tables_original=all_tables_original,
            original_sql=original_sql,
        )

    # -------------------------------------------------------------------
    # Detecção de palavras-chave / operadores mal digitados
    # -------------------------------------------------------------------

    def _check_keyword_typos(self, tokens):
        """
        Percorre os tokens procurando identificadores (IDs) que se parecem
        com palavras-chave mal digitadas (WHER, ANDDD, JON, SELCT, FRM...).

        Só considera suspeitos os IDs que não são seguidos de '.' (i.e., que
        não fazem parte de um nome de coluna qualificado tipo 'tabela.coluna').
        """
        for i, (ttype, tval) in enumerate(tokens):
            if ttype != "ID":
                continue

            # Se o próximo token é '.', então é um nome de tabela qualificado,
            # não uma palavra-chave mal digitada.
            # (Na prática o tokenizer já capta 'tabela.coluna' como DOTTED,
            #  mas mantemos a checagem por robustez.)
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            if next_tok and next_tok[0] == "OP" and next_tok[1] == ".":
                continue

            suggested = _looks_like_keyword(tval)
            if suggested is not None:
                self.errors.append(
                    f"Palavra-chave ou operador inválido: '{tval}'. "
                    f"Você quis dizer '{suggested}'? "
                    f"Símbolos suportados: {SUPPORTED_SYMBOLS_TEXT}."
                )

    # -------------------------------------------------------------------
    # Métodos auxiliares de extração de tokens
    # -------------------------------------------------------------------

    def _find_keyword_positions(self, tokens):
        """Encontra as posições de cada palavra-chave na lista de tokens."""
        positions = {}
        for i, (ttype, tval) in enumerate(tokens):
            if ttype == "KEYWORD":
                positions.setdefault(tval, [])
                positions[tval].append(i)
        return positions

    def _get_tokens_between(self, tokens, kw_positions, start_kw, end_kw):
        """Retorna tokens entre duas palavras-chave."""
        start = kw_positions[start_kw][0] + 1
        end = kw_positions[end_kw][0]
        return tokens[start:end]

    def _get_from_tokens(self, tokens, kw_pos):
        """Extrai tokens da cláusula FROM (até JOIN ou WHERE ou fim)."""
        start = kw_pos["FROM"][0] + 1
        end = len(tokens)
        if "JOIN" in kw_pos and kw_pos["JOIN"]:
            end = min(end, kw_pos["JOIN"][0])
        if "WHERE" in kw_pos and kw_pos["WHERE"]:
            end = min(end, kw_pos["WHERE"][0])
        return tokens[start:end]

    def _get_join_groups(self, tokens, kw_pos):
        """Extrai pares (table_tokens, condition_tokens) para cada JOIN...ON."""
        groups = []
        if "JOIN" not in kw_pos:
            return groups

        join_positions = kw_pos["JOIN"]
        on_positions = kw_pos.get("ON", [])

        if len(join_positions) != len(on_positions):
            self.errors.append(
                f"Número de JOINs ({len(join_positions)}) diferente do número de ONs ({len(on_positions)})."
            )
            return groups

        for i, join_idx in enumerate(join_positions):
            on_idx = on_positions[i]

            # Tokens entre JOIN e ON = nome da tabela
            table_tokens = tokens[join_idx + 1: on_idx]

            # Tokens após ON até o próximo JOIN, WHERE ou fim
            cond_start = on_idx + 1
            cond_end = len(tokens)
            if i + 1 < len(join_positions):
                cond_end = min(cond_end, join_positions[i + 1])
            if "WHERE" in kw_pos and kw_pos["WHERE"]:
                cond_end = min(cond_end, kw_pos["WHERE"][0])
            cond_tokens = tokens[cond_start:cond_end]

            groups.append((table_tokens, cond_tokens))

        return groups

    def _get_where_tokens(self, tokens, kw_pos):
        """Extrai tokens da cláusula WHERE até o fim."""
        if "WHERE" not in kw_pos:
            return []
        start = kw_pos["WHERE"][0] + 1
        return tokens[start:]

    # -------------------------------------------------------------------
    # Métodos de parsing de cláusulas
    # -------------------------------------------------------------------

    def _parse_from(self, from_tokens):
        """Parseia a cláusula FROM e retorna (original, normalizado)."""
        if not from_tokens:
            self.errors.append("Cláusula FROM vazia.")
            return ("", "")

        # O FROM deve ter exatamente um identificador (nome da tabela)
        if from_tokens[0][0] not in ("ID", "DOTTED"):
            self.errors.append(
                f"Esperado nome de tabela após FROM, encontrado: '{from_tokens[0][1]}'."
            )
            return ("", "")

        table_original = from_tokens[0][1]
        table_normalized = table_original.lower()

        # Tokens extras após o nome da tabela indicam palavras inválidas
        # (ex.: "FROM Cliente WHER ..." onde WHER foi digitado errado).
        extras = [v for _, v in from_tokens[1:]]
        if extras:
            self.errors.append(
                f"Tokens inesperados após a tabela '{table_original}' no FROM: "
                f"{' '.join(extras)}. Verifique se há palavras-chave mal "
                f"digitadas (WHERE, JOIN, etc.)."
            )

        return (table_original, table_normalized)

    def _parse_join(self, table_tokens, cond_tokens, all_tables_original):
        """Parseia uma cláusula JOIN...ON."""
        if not table_tokens:
            self.errors.append("JOIN sem nome de tabela.")
            return None

        if table_tokens[0][0] not in ("ID", "DOTTED"):
            self.errors.append(
                f"Esperado nome de tabela após JOIN, encontrado: '{table_tokens[0][1]}'."
            )
            return None

        table_original = table_tokens[0][1]
        table_normalized = table_original.lower()
        all_tables_original[table_normalized] = table_original

        # Tokens extras após o nome da tabela (antes do ON)
        extras = [v for _, v in table_tokens[1:]]
        if extras:
            self.errors.append(
                f"Tokens inesperados após a tabela '{table_original}' no JOIN: "
                f"{' '.join(extras)}."
            )

        # Parsear condição do ON
        condition = self._parse_single_condition(cond_tokens, list(all_tables_original.keys()))

        return JoinClause(
            table=table_normalized,
            table_original=table_original,
            condition=condition,
        )

    def _parse_select_columns(self, select_tokens, all_tables):
        """Parseia as colunas do SELECT."""
        columns = []
        # Remover vírgulas e agrupar
        current_tokens = []
        for ttype, tval in select_tokens:
            if ttype == "COMMA":
                if current_tokens:
                    col = self._resolve_column_ref(current_tokens, all_tables)
                    if col:
                        columns.append(col)
                    current_tokens = []
            else:
                current_tokens.append((ttype, tval))
        if current_tokens:
            col = self._resolve_column_ref(current_tokens, all_tables)
            if col:
                columns.append(col)

        if not columns:
            self.errors.append("Nenhuma coluna especificada no SELECT.")

        return columns

    def _resolve_column_ref(self, tokens, all_tables) -> ColumnRef | None:
        """Converte tokens em ColumnRef. Suporta 'tabela.coluna' e 'coluna'."""
        if not tokens:
            return None

        ttype, tval = tokens[0]

        if ttype == "DOTTED":
            parts = tval.split(".")
            table_orig = parts[0]
            col_orig = parts[1]
            return ColumnRef(
                table=table_orig.lower(),
                column=col_orig.lower(),
                original=tval,
            )
        elif ttype == "ID":
            # Coluna sem prefixo de tabela - tentar resolver
            try:
                table = resolve_column(tval, all_tables)
                return ColumnRef(
                    table=table,
                    column=tval.lower(),
                    original=tval,
                )
            except ValueError as e:
                self.errors.append(str(e))
                return None
        else:
            self.errors.append(f"Token inesperado no SELECT: {tval}")
            return None

    def _parse_where(self, where_tokens, all_tables) -> list[Condition]:
        """Parseia condições do WHERE, separando por AND."""
        if not where_tokens:
            return []

        conditions = []
        # Separar por AND e remover parênteses
        current = []
        for ttype, tval in where_tokens:
            if ttype == "KEYWORD" and tval == "AND":
                if current:
                    cond = self._parse_single_condition(current, all_tables)
                    if cond:
                        conditions.append(cond)
                    current = []
            elif ttype in ("LPAREN", "RPAREN"):
                # Ignorar parênteses (simplificação - tratamos AND flat)
                continue
            else:
                current.append((ttype, tval))

        if current:
            cond = self._parse_single_condition(current, all_tables)
            if cond:
                conditions.append(cond)

        return conditions

    def _parse_single_condition(self, tokens, all_tables) -> Condition | None:
        """
        Parseia uma condição simples: left OP right
        Onde left é coluna, OP é operador, right é coluna ou literal.
        """
        # Filtrar parênteses
        filtered = [(t, v) for t, v in tokens if t not in ("LPAREN", "RPAREN")]

        if len(filtered) < 3:
            self.errors.append(f"Condição incompleta: {' '.join(v for _, v in tokens)}")
            return None

        # Encontrar o operador
        op_idx = None
        for i, (ttype, tval) in enumerate(filtered):
            if ttype == "OP":
                op_idx = i
                break

        if op_idx is None:
            self.errors.append(f"Operador não encontrado na condição: {' '.join(v for _, v in tokens)}")
            return None

        # Lado esquerdo (antes do operador)
        left_tokens = filtered[:op_idx]
        operator = filtered[op_idx][1]
        right_tokens = filtered[op_idx + 1:]

        # Validar operador
        if operator not in VALID_OPERATORS:
            self.errors.append(
                f"Operador inválido: '{operator}'. "
                f"Operadores suportados: {SUPPORTED_SYMBOLS_TEXT}."
            )

        # Rejeitar tokens extras no lado direito. Isso captura casos como
        # "X = 0 ANDDD Y = 1": depois do '0' o parser esperava um AND ou o
        # fim da condição, não um identificador solto.
        if len(right_tokens) > 1:
            extras = [v for _, v in right_tokens[1:]]
            # Se o primeiro token extra parece uma keyword mal digitada,
            # a checagem em _check_keyword_typos já reportou — evitar duplicar.
            first_extra = right_tokens[1][1] if right_tokens[1:] else ""
            if _looks_like_keyword(first_extra) is None:
                self.errors.append(
                    f"Tokens inesperados após '{right_tokens[0][1]}' na condição: "
                    f"{' '.join(extras)}. "
                    f"Símbolos suportados: {SUPPORTED_SYMBOLS_TEXT}."
                )

        # Parsear lado esquerdo (deve ser coluna)
        left_ref = self._resolve_column_ref(left_tokens, all_tables)
        if left_ref is None:
            return None

        # Parsear lado direito (pode ser coluna ou literal)
        right_ttype, right_tval = right_tokens[0] if right_tokens else ("", "")

        if right_ttype == "DOTTED":
            parts = right_tval.split(".")
            right_ref = ColumnRef(
                table=parts[0].lower(),
                column=parts[1].lower(),
                original=right_tval,
            )
        elif right_ttype == "ID":
            # Pode ser coluna sem prefixo ou um identificador
            try:
                table = resolve_column(right_tval, all_tables)
                right_ref = ColumnRef(
                    table=table,
                    column=right_tval.lower(),
                    original=right_tval,
                )
            except ValueError:
                # Tratar como valor literal
                right_ref = right_tval
        elif right_ttype in ("NUMBER", "STRING"):
            right_ref = right_tval
        else:
            right_ref = right_tval if right_tval else "?"

        # Montar string original da condição
        original = f"{left_ref.original} {operator} {right_ref.original if isinstance(right_ref, ColumnRef) else right_ref}"

        return Condition(
            left=left_ref,
            operator=operator,
            right=right_ref,
            original=original,
        )

    # -------------------------------------------------------------------
    # Métodos de validação contra o schema
    # -------------------------------------------------------------------

    def _validate_tables(self, tables, tables_original):
        """
        Valida se todas as tabelas existem no schema.

        Lança UnknownTableError imediatamente para a primeira tabela
        desconhecida (erro específico e distinto dos demais).
        """
        for table in tables:
            if not table_exists(table):
                orig = tables_original.get(table, table)
                raise UnknownTableError(orig, get_all_table_names())

    def _validate_columns(self, columns: list[ColumnRef]):
        """Valida se todas as colunas do SELECT existem no schema."""
        for col in columns:
            if not column_exists(col.table, col.column):
                self.errors.append(
                    f"Coluna '{col.original}' não existe. "
                    f"A tabela '{col.table}' possui: {get_table_columns(col.table)}"
                )

    def _validate_condition_columns(self, cond: Condition):
        """Valida as colunas de uma condição contra o schema."""
        if cond is None:
            return
        if not column_exists(cond.left.table, cond.left.column):
            self.errors.append(
                f"Coluna '{cond.left.original}' não existe na tabela '{cond.left.table}'."
            )
        if isinstance(cond.right, ColumnRef):
            if not column_exists(cond.right.table, cond.right.column):
                self.errors.append(
                    f"Coluna '{cond.right.original}' não existe na tabela '{cond.right.table}'."
                )
