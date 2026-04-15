# Plano de Implementacao - Processador de Consultas SQL

## Visao Geral do Projeto

Implementacao de um **Processador de Consultas SQL** em Python que recebe uma consulta SQL via interface grafica, valida a sintaxe, converte para algebra relacional, aplica heuristicas de otimizacao, constroi um grafo de operadores e exibe o plano de execucao.

**Linguagem:** Python 3.10+
**Interface Grafica:** Tkinter (nativo do Python, sem dependencias externas)
**Visualizacao de Grafos:** Graphviz (via biblioteca `graphviz`) ou renderizacao com `matplotlib`/`networkx`

---

## Modelo de Dados de Referencia (Metadados)

O sistema deve conhecer EXATAMENTE estas tabelas e seus campos para validacao:

```python
SCHEMA = {
    "categoria": ["idcategoria", "descricao"],
    "produto": ["idproduto", "nome", "descricao", "preco", "quantestoque", "categoria_idcategoria"],
    "tipocliente": ["idtipocliente", "descricao"],
    "cliente": ["idcliente", "nome", "email", "nascimento", "senha", "tipocliente_idtipocliente", "dataregistro"],
    "tipoendereco": ["idtipoendereco", "descricao"],
    "endereco": ["idendereco", "enderecopadrao", "logradouro", "numero", "complemento", "bairro", "cidade", "uf", "cep", "tipoendereco_idtipoendereco", "cliente_idcliente"],
    "telefone": ["numero", "cliente_idcliente"],
    "status": ["idstatus", "descricao"],
    "pedido": ["idpedido", "status_idstatus", "datapedido", "valortotalpedido", "cliente_idcliente"],
    "pedido_has_produto": ["idpedidoproduto", "pedido_idpedido", "produto_idproduto", "quantidade", "precounitario"],
}
```

---

## Estrutura de Arquivos

```
processador_consultas/
|-- main.py                  # Ponto de entrada - lanca a interface grafica
|-- gui.py                   # HU1/HU3/HU5 - Interface grafica (Tkinter)
|-- schema.py                # Definicao dos metadados (tabelas e campos)
|-- sql_parser.py            # HU1 - Parsing e validacao da consulta SQL
|-- relational_algebra.py    # HU2 - Conversao SQL -> Algebra Relacional
|-- optimizer.py             # HU4 - Otimizacao via heuristicas
|-- query_tree.py            # HU3 - Construcao do grafo/arvore de operadores
|-- execution_plan.py        # HU5 - Geracao do plano de execucao ordenado
|-- requirements.txt         # Dependencias do projeto
```

---

## HU1 - Entrada e Validacao da Consulta (Peso: 2.0 + 1.0 da GUI)

### Objetivo
Receber SQL via GUI, fazer parsing e validar sintaxe, tabelas e atributos.

### Arquivo: `schema.py`

```python
"""
Modulo de metadados - define todas as tabelas e campos validos
conforme o modelo de dados de referencia (Imagem 01 do PDF).
"""

# Dicionario com todas as tabelas e seus campos (tudo em minusculo para comparacao case-insensitive)
SCHEMA = { ... }  # conforme definido acima

def table_exists(table_name: str) -> bool:
    """Verifica se a tabela existe no schema (case-insensitive)."""

def get_table_columns(table_name: str) -> list[str]:
    """Retorna a lista de colunas de uma tabela."""

def column_exists(table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe em uma tabela especifica."""

def resolve_column(column_ref: str, available_tables: list[str]) -> tuple[str, str]:
    """
    Resolve uma referencia de coluna (ex: 'cliente.nome' ou 'nome')
    retornando (tabela, coluna). Levanta erro se ambiguo ou inexistente.
    """
```

### Arquivo: `sql_parser.py`

```python
"""
Modulo de parsing e validacao de consultas SQL.
Valida comandos: SELECT, FROM, WHERE, JOIN, ON
Operadores validos: =, >, <, <=, >=, <>, AND, ( )

Regras:
- Case-insensitive (maiusculas/minusculas sao ignoradas)
- Espacos em branco repetidos sao ignorados
- Apenas tabelas/atributos do schema sao aceitos
- Suporta 0, 1, ..., N JOINs
"""

from dataclasses import dataclass, field

@dataclass
class ColumnRef:
    """Referencia a uma coluna: tabela.coluna"""
    table: str       # nome da tabela (normalizado em minusculo)
    column: str      # nome da coluna (normalizado em minusculo)
    original: str    # texto original digitado pelo usuario

@dataclass
class Condition:
    """Condicao do WHERE: left_operand operador right_operand"""
    left: ColumnRef | str
    operator: str          # =, >, <, <=, >=, <>
    right: ColumnRef | str
    original: str

@dataclass
class JoinClause:
    """Clausula JOIN: tabela ON condicao"""
    table: str
    alias: str | None
    on_condition: Condition

@dataclass
class ParsedQuery:
    """Resultado do parsing de uma consulta SQL."""
    select_columns: list[ColumnRef]   # Colunas do SELECT
    from_table: str                    # Tabela principal do FROM
    joins: list[JoinClause]            # Lista de JOINs (pode ser vazia)
    where_conditions: list[Condition]  # Condicoes do WHERE (pode ser vazia)
    all_tables: list[str]              # Todas as tabelas envolvidas
    original_sql: str                  # SQL original


class SQLParser:
    """
    Parser de consultas SQL.

    Fluxo de parsing:
    1. Normalizar a string (remover espacos extras, converter para minusculo para comparacao)
    2. Tokenizar a string em palavras-chave e identificadores
    3. Identificar clausulas: SELECT, FROM, JOIN...ON, WHERE
    4. Validar existencia de tabelas no schema
    5. Validar existencia de colunas nas tabelas referenciadas
    6. Validar operadores nas condicoes
    7. Retornar ParsedQuery ou lista de erros
    """

    def __init__(self, schema: dict):
        self.schema = schema
        self.errors: list[str] = []

    def parse(self, sql: str) -> ParsedQuery:
        """
        Metodo principal de parsing.
        Levanta ValueError com mensagens detalhadas se a consulta for invalida.
        """

    def _normalize(self, sql: str) -> str:
        """Remove espacos extras e normaliza a string."""
        # Usa regex para colapsar multiplos espacos em um so
        # Faz strip() nas extremidades

    def _tokenize(self, sql: str) -> list[str]:
        """
        Divide o SQL em tokens.
        Reconhece: palavras-chave, identificadores, operadores, parenteses.
        Usa expressao regular para tokenizacao robusta.
        """

    def _extract_select(self, tokens) -> list[ColumnRef]:
        """Extrai as colunas da clausula SELECT."""

    def _extract_from(self, tokens) -> str:
        """Extrai a tabela principal do FROM."""

    def _extract_joins(self, tokens) -> list[JoinClause]:
        """Extrai todas as clausulas JOIN...ON."""

    def _extract_where(self, tokens) -> list[Condition]:
        """
        Extrai as condicoes do WHERE.
        Suporta AND para multiplas condicoes.
        Suporta parenteses para agrupamento.
        """

    def _validate_tables(self, tables: list[str]) -> None:
        """Valida se todas as tabelas existem no schema."""

    def _validate_columns(self, columns: list[ColumnRef], tables: list[str]) -> None:
        """Valida se todas as colunas existem nas tabelas referenciadas."""

    def _validate_operator(self, op: str) -> bool:
        """Valida se o operador esta entre os permitidos: =, >, <, <=, >=, <>"""
```

### Detalhes de Implementacao do Parser

**Estrategia de tokenizacao (regex):**
```python
import re

# Padrao regex para tokenizacao:
TOKEN_PATTERN = re.compile(
    r"""
    (\bSELECT\b|\bFROM\b|\bWHERE\b|\bJOIN\b|\bON\b|\bAND\b)  # palavras-chave
    | ([a-zA-Z_]\w*\.[a-zA-Z_]\w*)                              # tabela.coluna
    | ([a-zA-Z_]\w*)                                             # identificador simples
    | (<=|>=|<>|[=<>])                                           # operadores
    | ([(),])                                                    # parenteses e virgula
    | (\d+\.?\d*)                                                # numeros
    | ('[^']*')                                                  # strings entre aspas
    """,
    re.IGNORECASE | re.VERBOSE
)
```

**Validacao passo a passo:**
1. Normalizar entrada (espacos, case)
2. Verificar que comeca com SELECT
3. Extrair colunas ate encontrar FROM
4. Extrair tabela do FROM
5. Extrair 0..N blocos JOIN...ON
6. Extrair condicoes do WHERE (se existir)
7. Validar cada tabela contra o schema
8. Validar cada coluna (tabela.coluna) contra o schema
9. Validar operadores nas condicoes

---

## HU2 - Conversao para Algebra Relacional (Peso: 1.5)

### Objetivo
Converter o ParsedQuery em uma expressao de algebra relacional textual usando os simbolos corretos.

### Arquivo: `relational_algebra.py`

```python
"""
Modulo de conversao SQL -> Algebra Relacional.

Simbolos utilizados:
- Selecao:  sigma (filtro de tuplas)
- Projecao: pi (filtro de colunas)
- Juncao:   |X| (join)

Logica de conversao (conforme exemplos dos arquivos .txt):

Passo 1 - Conversao direta (Heuristica de Juncao):
  SQL: SELECT cols FROM T1 JOIN T2 ON cond1 JOIN T3 ON cond2 WHERE filtros
  AR:  pi cols ( sigma filtros ( (T1 |X|cond1 T2) |X|cond2 T3 ) )

  - A projecao (pi) envolve tudo
  - A selecao (sigma) com condicoes do WHERE envolve as juncoes
  - As juncoes sao encadeadas da esquerda para a direita
"""

SIGMA = "σ"    # Selecao
PI = "π"        # Projecao
JOIN = "⋈"     # Juncao (tambem pode ser representado como |X|)
AND = "∧"      # E logico


@dataclass
class RelationalExpression:
    """Representacao da expressao de algebra relacional."""
    text: str                  # Expressao textual formatada
    parsed_query: ParsedQuery  # Query original parseada


class RelationalAlgebraConverter:
    """
    Converte um ParsedQuery em algebra relacional.

    Fluxo (baseado nos exemplos dos arquivos .txt de referencia):

    Exemplo do arquivo "Select Exemplo 1 Convertido para Algebra Relacional.txt":
      SQL: SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
           FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente
           WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0

      AR (Passo 1 - conversao direta):
        pi cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
          ( sigma cliente.TipoCliente_idTipoCliente = 1 ^ pedido.ValorTotalPedido = 0
            ( Cliente |X| cliente.idcliente = pedido.Cliente_idCliente Pedido ) )
    """

    def __init__(self, parsed_query: ParsedQuery):
        self.query = parsed_query

    def convert(self) -> RelationalExpression:
        """
        Converte a consulta SQL para algebra relacional.
        Retorna a expressao no formato textual.
        """

    def _build_join_expression(self) -> str:
        """
        Constroi a parte de juncao da expressao.
        Para 0 joins: apenas o nome da tabela.
        Para 1+ joins: encadeia (T1 |X|cond T2) |X|cond T3 ...
        """

    def _build_where_expression(self) -> str:
        """
        Constroi a expressao sigma com as condicoes do WHERE.
        Multiplas condicoes sao unidas com ^ (AND).
        """

    def _build_select_expression(self) -> str:
        """
        Constroi a expressao pi com as colunas do SELECT.
        """

    def format_expression(self) -> str:
        """
        Monta a expressao completa:
        pi <cols> ( sigma <conds> ( <joins> ) )

        Se nao houver WHERE, omite o sigma:
        pi <cols> ( <joins> )
        """
```

---

## HU4 - Otimizacao da Consulta (Peso: 1.0 + 1.0 + 1.0)

### Objetivo
Aplicar heuristicas de otimizacao sobre a algebra relacional, gerando a versao otimizada.

### Arquivo: `optimizer.py`

```python
"""
Modulo de otimizacao de consultas via heuristicas.

Heuristicas implementadas (conforme PDF e exemplos .txt):

1. HEURISTICA DE REDUCAO DE TUPLAS (sigma push-down):
   - "Empurrar" as selecoes (sigma) para o mais proximo possivel das tabelas base.
   - Cada condicao WHERE que referencia apenas UMA tabela eh movida
     para ficar imediatamente acima dessa tabela.

   Exemplo (arquivo "Montagem Arvore.txt", Passo 2):
     ANTES:  pi cols ( sigma tb1.id > 300 ^ tb3.sal <> 0 ( (T1 |X| T2) |X| T3 ) )
     DEPOIS: pi cols ( ( (sigma tb1.id > 300 (T1)) |X| T2 ) |X| (sigma tb3.sal <> 0 (T3)) )

   Exemplo (arquivo "Select Exemplo 1"):
     ANTES:  pi cols ( sigma cli.tipo=1 ^ ped.valor=0 ( Cli |X| Ped ) )
     DEPOIS: pi cols ( (sigma cli.tipo=1 (Cli)) |X| (sigma ped.valor=0 (Ped)) )

2. HEURISTICA DE REDUCAO DE ATRIBUTOS (pi push-down):
   - Inserir projecoes (pi) apos cada selecao/tabela para carregar apenas
     os campos necessarios para o restante da consulta.
   - Para cada tabela, projetar apenas:
     a) Campos que aparecem no SELECT final
     b) Campos que aparecem em condicoes JOIN (ON)
     c) Campos que aparecem no WHERE (ja resolvidos pela selecao, mas
        podem ser necessarios se a selecao for parcial)

   Exemplo (arquivo "Montagem Arvore.txt", Passo 3):
     pi Tb1.Nome, tb3.sal (
       ( (pi Pk,nome (sigma tb1.id>300 (T1))) |X| (pi Pk,fk (T2)) )
       |X| (pi Sal,fk (sigma tb3.sal<>0 (T3)))
     )

   Exemplo (arquivo "Select Exemplo 1"):
     pi cli.nome, ped.idPedido, ped.DataPedido, ped.ValorTotalPedido (
       (pi cli.nome, cli.idcliente (sigma cli.tipo=1 (Cli)))
       |X| (pi ped.idPedido, ped.DataPedido, ped.ValorTotalPedido, ped.Cli_idCli (sigma ped.valor=0 (Ped)))
     )

3. JUNCAO (uso correto de join em vez de produto cartesiano):
   - Garantir que todas as juncoes usem condicoes ON (nunca produto cartesiano).
   - A ordem das juncoes pode ser reordenada para aplicar as mais restritivas primeiro.
"""

from dataclasses import dataclass


@dataclass
class OptimizationStep:
    """Representa um passo da otimizacao."""
    name: str            # Nome da heuristica aplicada
    description: str     # Descricao do que foi feito
    expression: str      # Expressao resultante apos este passo


class QueryOptimizer:
    """
    Aplica heuristicas de otimizacao a uma expressao de algebra relacional.

    Ordem de aplicacao:
    1. Reducao de tuplas (push-down de sigma)
    2. Reducao de atributos (push-down de pi)
    """

    def __init__(self, parsed_query: ParsedQuery):
        self.query = parsed_query
        self.steps: list[OptimizationStep] = []

    def optimize(self) -> list[OptimizationStep]:
        """
        Aplica todas as heuristicas em sequencia.
        Retorna a lista de passos de otimizacao.
        """
        # Passo 0: Expressao original (conversao direta)
        # Passo 1: Reducao de tuplas
        # Passo 2: Reducao de atributos
        # Retorna todos os passos

    def _apply_tuple_reduction(self) -> str:
        """
        Heuristica de reducao de tuplas.

        Para cada condicao do WHERE:
        1. Identificar a qual tabela a condicao pertence
           (analisa as colunas referenciadas na condicao)
        2. Mover o sigma para ficar imediatamente acima da tabela
        3. Remover o sigma global (pois as condicoes foram distribuidas)

        Logica:
        - where_conditions_by_table: dict[str, list[Condition]]
          Agrupa condicoes por tabela
        - Para cada tabela na expressao de join:
          Se tem condicoes, envolve com sigma: sigma <cond> (<tabela>)
          Se nao tem condicoes, mantem apenas: <tabela>
        """

    def _apply_attribute_reduction(self) -> str:
        """
        Heuristica de reducao de atributos.

        Para cada tabela:
        1. Identificar quais campos sao necessarios:
           a) Campos no SELECT final que pertencem a esta tabela
           b) Campos em condicoes ON de JOIN que pertencem a esta tabela
           c) Campos ja usados no sigma que ainda precisam fluir
        2. Inserir pi com esses campos apos o sigma (ou apos a tabela se nao ha sigma)

        Logica:
        - needed_columns_per_table: dict[str, set[str]]
          Para cada tabela, calcula o conjunto minimo de colunas necessarias
        - Envolve cada tabela/sigma com pi: pi <cols> (sigma <cond> (<tabela>))
        """

    def _get_needed_columns(self, table: str) -> set[str]:
        """
        Calcula as colunas necessarias para uma tabela especifica.
        Considera: SELECT, JOIN ON, WHERE.
        """

    def _classify_conditions(self) -> dict[str, list]:
        """
        Classifica as condicoes do WHERE por tabela.
        Uma condicao que referencia apenas uma tabela vai para essa tabela.
        Condicoes que referenciam 2+ tabelas ficam no nivel do join.
        """
```

---

## HU3 - Construcao do Grafo de Operadores (Peso: 1.0)

### Objetivo
Construir em memoria e exibir graficamente a arvore de operadores da consulta otimizada.

### Arquivo: `query_tree.py`

```python
"""
Modulo de construcao do grafo (arvore) de operadores.

Estrutura da arvore (conforme exemplos dos .txt):

- RAIZ: Projecao final (pi) com as colunas do SELECT
- NOS INTERNOS: Juncoes (|X|), Selecoes (sigma), Projecoes intermediarias (pi)
- FOLHAS: Tabelas base

Exemplo do arquivo "Montagem Arvore.txt" (Passo 4):

                pi Tb1.Nome, tb3.sal            <-- RAIZ (projecao final)
                         |
                 |X| tb2.pk = tb3.fk            <-- juncao
                 /               \
     |X| Tb1.pk = tb2.fk          |             <-- juncao
           /        \             |
   pi Pk, nome     pi Pk,fk    pi Sal, fk       <-- projecoes intermediarias
         |             |            |
sigma tb1.id > 300    Tb2     sigma tb3.sal <> 0 <-- selecoes ou tabelas
         |                          |
        Tb1                        Tb3           <-- FOLHAS (tabelas)
"""

from dataclasses import dataclass
from enum import Enum


class NodeType(Enum):
    """Tipos de nos na arvore de operadores."""
    TABLE = "table"            # Folha - tabela base
    SELECTION = "selection"    # sigma - selecao
    PROJECTION = "projection"  # pi - projecao
    JOIN = "join"              # |X| - juncao


@dataclass
class TreeNode:
    """No da arvore de operadores."""
    node_type: NodeType
    label: str              # Descricao do no (ex: "sigma tb1.id > 300")
    children: list          # Lista de filhos (TreeNode)
    table_name: str = None  # Nome da tabela (apenas para folhas)


class QueryTree:
    """
    Constroi a arvore de operadores a partir da consulta otimizada.

    Construcao bottom-up:
    1. Criar nos folha para cada tabela
    2. Aplicar sigma sobre cada folha que tem condicao WHERE
    3. Aplicar pi sobre cada sigma/folha com as colunas necessarias
    4. Construir juncoes conectando as subarvores
    5. Aplicar projecao final como raiz
    """

    def __init__(self, parsed_query: ParsedQuery, optimizer: QueryOptimizer):
        self.query = parsed_query
        self.optimizer = optimizer
        self.root: TreeNode = None

    def build(self) -> TreeNode:
        """
        Constroi a arvore completa.
        Retorna o no raiz.
        """

    def _build_table_subtree(self, table: str) -> TreeNode:
        """
        Constroi a subarvore para uma tabela:
        pi <cols> ( sigma <cond> ( <tabela> ) )
        Retorna o no mais externo da subarvore.
        """

    def _build_join_tree(self, subtrees: dict[str, TreeNode]) -> TreeNode:
        """
        Constroi a arvore de juncoes encadeando as subarvores.
        A ordem segue a ordem dos JOINs na consulta.
        """

    def to_display_string(self, node: TreeNode = None, indent: int = 0) -> str:
        """
        Gera representacao textual da arvore para exibicao.
        Formato identado mostrando a hierarquia.
        """

    def to_graphviz(self) -> str:
        """
        Gera codigo DOT para visualizacao com Graphviz.
        Cada no recebe um ID unico e arestas conectam pai -> filhos.
        """
```

### Visualizacao do Grafo

Para renderizar o grafo na interface, duas opcoes:

**Opcao A - Graphviz (recomendada):**
```python
import graphviz

def render_tree(root: TreeNode) -> graphviz.Digraph:
    """Renderiza a arvore como imagem PNG usando Graphviz."""
    dot = graphviz.Digraph(comment='Grafo de Operadores')
    dot.attr(rankdir='TB')  # Top to Bottom

    def add_nodes(node, parent_id=None, counter=[0]):
        node_id = f"n{counter[0]}"
        counter[0] += 1

        # Estilo do no baseado no tipo
        if node.node_type == NodeType.TABLE:
            dot.node(node_id, node.label, shape='box', style='filled', fillcolor='lightyellow')
        elif node.node_type == NodeType.SELECTION:
            dot.node(node_id, node.label, shape='ellipse', style='filled', fillcolor='lightblue')
        elif node.node_type == NodeType.PROJECTION:
            dot.node(node_id, node.label, shape='ellipse', style='filled', fillcolor='lightgreen')
        elif node.node_type == NodeType.JOIN:
            dot.node(node_id, node.label, shape='diamond', style='filled', fillcolor='lightsalmon')

        if parent_id:
            dot.edge(parent_id, node_id)

        for child in node.children:
            add_nodes(child, node_id, counter)

    add_nodes(root)
    return dot
```

**Opcao B - Texto ASCII (fallback se Graphviz nao estiver instalado):**
```
Renderizar a arvore como texto identado na interface,
similar ao formato dos arquivos .txt de referencia.
```

---

## HU5 - Plano de Execucao (Peso: 1.5)

### Objetivo
Exibir a ordem de execucao das operacoes, percorrendo a arvore otimizada de baixo para cima.

### Arquivo: `execution_plan.py`

```python
"""
Modulo de geracao do plano de execucao.

O plano de execucao percorre a arvore de operadores de baixo para cima
(post-order traversal), listando cada operacao na ordem que seria executada.

Exemplo para a consulta do arquivo "Montagem Arvore.txt":

  Passo 1: Ler tabela Tb1
  Passo 2: Aplicar selecao sigma tb1.id > 300 sobre Tb1
  Passo 3: Aplicar projecao pi Pk, nome
  Passo 4: Ler tabela Tb2
  Passo 5: Aplicar projecao pi Pk, fk
  Passo 6: Aplicar juncao |X| Tb1.pk = tb2.fk
  Passo 7: Ler tabela Tb3
  Passo 8: Aplicar selecao sigma tb3.sal <> 0 sobre Tb3
  Passo 9: Aplicar projecao pi Sal, fk
  Passo 10: Aplicar juncao |X| tb2.pk = tb3.fk
  Passo 11: Aplicar projecao final pi Tb1.Nome, tb3.sal
"""

@dataclass
class ExecutionStep:
    """Um passo do plano de execucao."""
    step_number: int
    operation: str       # Tipo: "Ler tabela", "Selecao", "Projecao", "Juncao"
    description: str     # Descricao detalhada
    node: TreeNode       # No correspondente na arvore


class ExecutionPlanGenerator:
    """
    Gera o plano de execucao a partir da arvore de operadores otimizada.
    """

    def __init__(self, tree: QueryTree):
        self.tree = tree
        self.steps: list[ExecutionStep] = []

    def generate(self) -> list[ExecutionStep]:
        """
        Percorre a arvore em post-order (folhas primeiro, raiz por ultimo).
        Cada no visitado gera um passo no plano.
        """
        self.steps = []
        self._traverse_postorder(self.tree.root)
        return self.steps

    def _traverse_postorder(self, node: TreeNode) -> None:
        """
        Travessia post-order: visita filhos primeiro, depois o no.
        Isso garante que as operacoes mais basicas (leitura de tabelas)
        acontecam antes das operacoes que dependem delas.
        """
        if node is None:
            return

        for child in node.children:
            self._traverse_postorder(child)

        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            operation=self._get_operation_name(node),
            description=node.label,
            node=node
        )
        self.steps.append(step)

    def _get_operation_name(self, node: TreeNode) -> str:
        """Retorna o nome legivel da operacao."""
        mapping = {
            NodeType.TABLE: "Ler tabela",
            NodeType.SELECTION: "Aplicar selecao (sigma)",
            NodeType.PROJECTION: "Aplicar projecao (pi)",
            NodeType.JOIN: "Aplicar juncao (join)",
        }
        return mapping[node.node_type]

    def format_plan(self) -> str:
        """Formata o plano de execucao como texto legivel."""
        lines = ["=== PLANO DE EXECUCAO ===\n"]
        for step in self.steps:
            lines.append(f"Passo {step.step_number}: {step.operation} - {step.description}")
        return "\n".join(lines)
```

---

## Interface Grafica (Peso: 1.0)

### Arquivo: `gui.py`

```python
"""
Interface grafica do Processador de Consultas.
Construida com Tkinter.

Layout:
+---------------------------------------------------------------+
|  PROCESSADOR DE CONSULTAS SQL                                 |
+---------------------------------------------------------------+
|  [Campo de entrada SQL - Text multilinha]                     |
|                                                               |
|  [Botao: Processar Consulta]                                  |
+---------------------------------------------------------------+
|  Abas:                                                        |
|  [Algebra Relacional] [Otimizacao] [Grafo] [Plano Execucao]  |
|                                                               |
|  Aba 1 - Algebra Relacional:                                  |
|    Expressao original convertida                              |
|                                                               |
|  Aba 2 - Otimizacao:                                          |
|    Passo 1: Reducao de tuplas -> expressao                    |
|    Passo 2: Reducao de atributos -> expressao                 |
|                                                               |
|  Aba 3 - Grafo de Operadores:                                 |
|    Imagem da arvore (Graphviz ou texto ASCII)                 |
|                                                               |
|  Aba 4 - Plano de Execucao:                                   |
|    Passo 1: ...                                               |
|    Passo 2: ...                                               |
|    ...                                                        |
+---------------------------------------------------------------+
|  [Barra de status: erros de validacao / mensagens]            |
+---------------------------------------------------------------+
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox


class ProcessadorConsultasGUI:
    """Interface grafica principal."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Processador de Consultas SQL")
        self.root.geometry("1000x750")

    def _create_widgets(self):
        """Cria todos os widgets da interface."""
        # Frame superior: entrada SQL
        # Frame de botoes
        # Notebook (abas) para resultados
        # Barra de status

    def _on_process(self):
        """
        Callback do botao 'Processar Consulta'.
        Fluxo completo:
        1. Ler SQL do campo de entrada
        2. Chamar SQLParser.parse() -> ParsedQuery
        3. Se erro, exibir na barra de status e parar
        4. Chamar RelationalAlgebraConverter.convert() -> exibir na aba 1
        5. Chamar QueryOptimizer.optimize() -> exibir passos na aba 2
        6. Chamar QueryTree.build() -> renderizar na aba 3
        7. Chamar ExecutionPlanGenerator.generate() -> exibir na aba 4
        """

    def _display_algebra(self, expression: str):
        """Exibe a algebra relacional na aba correspondente."""

    def _display_optimization(self, steps: list):
        """Exibe os passos de otimizacao na aba correspondente."""

    def _display_tree(self, tree: QueryTree):
        """Exibe o grafo de operadores na aba correspondente."""

    def _display_plan(self, plan: list):
        """Exibe o plano de execucao na aba correspondente."""

    def run(self):
        """Inicia o loop principal da interface."""
        self.root.mainloop()
```

---

## Arquivo: `main.py`

```python
"""
Ponto de entrada do Processador de Consultas SQL.
"""
from gui import ProcessadorConsultasGUI


def main():
    app = ProcessadorConsultasGUI()
    app.run()


if __name__ == "__main__":
    main()
```

---

## Arquivo: `requirements.txt`

```
graphviz>=0.20
Pillow>=10.0
```

> **Nota:** Tkinter ja vem incluso no Python padrao. `graphviz` requer que o software
> Graphviz esteja instalado no sistema (`apt install graphviz` ou download em graphviz.org).
> `Pillow` e necessario para exibir a imagem do grafo no Tkinter.

---

## Mapeamento: Criterios de Avaliacao -> Implementacao

| Criterio (Peso) | Modulo(s) | O que cobre |
|---|---|---|
| Interface grafica funcional (1.0) | `gui.py`, `main.py` | Campo de entrada SQL, abas de resultado, exibicao do grafo |
| Parsing e validacao correta (2.0) | `sql_parser.py`, `schema.py` | Tokenizacao via regex, validacao SELECT/FROM/WHERE/JOIN/ON, validacao tabelas e colunas do schema, operadores validos, case-insensitive, espacos extras |
| Conversao para algebra relacional (1.5) | `relational_algebra.py` | Conversao SQL->AR com simbolos sigma, pi, join; preserva operadores e condicoes |
| Grafo de operadores otimizado (1.0) | `query_tree.py`, `gui.py` | Arvore em memoria com nos (operadores), arestas (fluxo), folhas (tabelas), raiz (projecao); exibicao grafica |
| Ordem de execucao (1.5) | `execution_plan.py` | Post-order traversal da arvore otimizada; lista ordenada de operacoes |
| Heuristica reducao de tuplas (1.0) | `optimizer.py` | Push-down de sigma para junto das tabelas base |
| Heuristica reducao de atributos (1.0) | `optimizer.py` | Push-down de pi apos sigma/tabela com campos minimos necessarios |
| Uso da juncao (1.0) | `sql_parser.py`, `relational_algebra.py`, `optimizer.py` | Suporte a 0..N JOINs, representacao como |X| na AR, evitar produto cartesiano |

---

## Fluxo Completo de Execucao (Passo a Passo)

```
Entrada do usuario (SQL na GUI)
        |
        v
[1] sql_parser.py: parse(sql)
    - Normaliza string (case, espacos)
    - Tokeniza com regex
    - Extrai SELECT, FROM, JOIN..ON, WHERE
    - Valida tabelas e colunas contra schema.py
    - Retorna ParsedQuery ou erros
        |
        v
[2] relational_algebra.py: convert(parsed_query)
    - Monta expressao de algebra relacional
    - Formato: pi <cols> ( sigma <conds> ( <joins> ) )
    -> Exibe na GUI (Aba "Algebra Relacional")
        |
        v
[3] optimizer.py: optimize(parsed_query)
    - Passo 1: Reducao de tuplas (push-down de sigma)
    - Passo 2: Reducao de atributos (push-down de pi)
    -> Exibe cada passo na GUI (Aba "Otimizacao")
        |
        v
[4] query_tree.py: build(parsed_query, optimizer)
    - Constroi arvore em memoria (TreeNode)
    - Folhas = tabelas, raiz = projecao final
    - Renderiza com Graphviz ou texto ASCII
    -> Exibe na GUI (Aba "Grafo de Operadores")
        |
        v
[5] execution_plan.py: generate(tree)
    - Post-order traversal da arvore
    - Lista cada operacao na ordem de execucao
    -> Exibe na GUI (Aba "Plano de Execucao")
```

---

## Exemplos de Teste (Baseados nos Arquivos .txt)

### Teste 1 (do arquivo "Select Exemplo 1"):
```sql
SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
FROM Cliente
JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente
WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0
```

**Resultado esperado - AR original:**
```
pi cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
  ( sigma cliente.TipoCliente_idTipoCliente = 1 ^ pedido.ValorTotalPedido = 0
    ( Cliente |X| cliente.idcliente = pedido.Cliente_idCliente Pedido ) )
```

**Resultado esperado - Apos reducao de tuplas:**
```
pi cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
  ( ( sigma cliente.TipoCliente_idTipoCliente = 1 (Cliente) )
    |X| cliente.idcliente = pedido.Cliente_idCliente
    ( sigma pedido.ValorTotalPedido = 0 (Pedido) ) )
```

**Resultado esperado - Apos reducao de atributos:**
```
pi cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido
  ( ( pi cliente.nome, cliente.idcliente
        ( sigma cliente.TipoCliente_idTipoCliente = 1 (Cliente) ) )
    |X| cliente.idcliente = pedido.Cliente_idCliente
    ( pi pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido, pedido.Cliente_idCliente
        ( sigma pedido.ValorTotalPedido = 0 (Pedido) ) ) )
```

### Teste 2 (do arquivo "Montagem Arvore"):
```sql
SELECT Tb1.Nome, tb3.sal
FROM Tb1
JOIN Tb2 ON tb1.pk = tb2.fk
JOIN tb3 ON tb2.pk = tb3.fk
WHERE tb1.id > 300 AND tb3.sal <> 0
```

> **Nota:** Este teste usa tabelas ficticias (Tb1, Tb2, Tb3) que NAO estao no schema.
> Serve apenas como referencia de formato. Para testes reais, usar tabelas do schema.

### Teste 3 (usando o schema real, sem WHERE):
```sql
SELECT produto.Nome, categoria.Descricao
FROM Produto
JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria
```

### Teste 4 (usando o schema real, multiplos JOINs):
```sql
SELECT cliente.Nome, pedido.DataPedido, produto.Nome
FROM Cliente
JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente
JOIN Pedido_has_Produto ON pedido.idPedido = pedido_has_produto.Pedido_idPedido
JOIN Produto ON pedido_has_produto.Produto_idProduto = produto.idProduto
WHERE cliente.TipoCliente_idTipoCliente = 1
```

---

## Ordem de Implementacao Recomendada

Seguir esta ordem respeita as dependencias entre modulos:

1. **`schema.py`** - Base de tudo, sem dependencias
2. **`sql_parser.py`** - Depende de `schema.py`
3. **`relational_algebra.py`** - Depende de `sql_parser.py`
4. **`optimizer.py`** - Depende de `sql_parser.py` e `relational_algebra.py`
5. **`query_tree.py`** - Depende de `optimizer.py`
6. **`execution_plan.py`** - Depende de `query_tree.py`
7. **`gui.py`** - Integra todos os modulos acima
8. **`main.py`** - Apenas lanca a GUI
