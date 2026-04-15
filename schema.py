"""
schema.py - Metadados do Modelo de Dados de Referência

Define todas as tabelas e campos válidos conforme a Imagem 01 do PDF.
Usado pelo parser para validar se tabelas e colunas existem.
Todas as comparações são case-insensitive (armazenado em minúsculo).
"""

# Dicionário com todas as tabelas e seus campos (chaves em minúsculo)
SCHEMA: dict[str, list[str]] = {
    "categoria": [
        "idcategoria", "descricao"
    ],
    "produto": [
        "idproduto", "nome", "descricao", "preco",
        "quantestoque", "categoria_idcategoria"
    ],
    "tipocliente": [
        "idtipocliente", "descricao"
    ],
    "cliente": [
        "idcliente", "nome", "email", "nascimento",
        "senha", "tipocliente_idtipocliente", "dataregistro"
    ],
    "tipoendereco": [
        "idtipoendereco", "descricao"
    ],
    "endereco": [
        "idendereco", "enderecopadrao", "logradouro", "numero",
        "complemento", "bairro", "cidade", "uf", "cep",
        "tipoendereco_idtipoendereco", "cliente_idcliente"
    ],
    "telefone": [
        "numero", "cliente_idcliente"
    ],
    "status": [
        "idstatus", "descricao"
    ],
    "pedido": [
        "idpedido", "status_idstatus", "datapedido",
        "valortotalpedido", "cliente_idcliente"
    ],
    "pedido_has_produto": [
        "idpedidoproduto", "pedido_idpedido", "produto_idproduto",
        "quantidade", "precounitario"
    ],
}


def table_exists(table_name: str) -> bool:
    """Verifica se a tabela existe no schema (case-insensitive)."""
    return table_name.strip().lower() in SCHEMA


def get_table_columns(table_name: str) -> list[str]:
    """Retorna a lista de colunas de uma tabela (minúsculo). Lista vazia se não existe."""
    return SCHEMA.get(table_name.strip().lower(), [])


def column_exists(table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe em uma tabela específica (case-insensitive)."""
    columns = get_table_columns(table_name)
    return column_name.strip().lower() in columns


def resolve_column(column_name: str, available_tables: list[str]) -> str:
    """
    Dado um nome de coluna sem prefixo de tabela, encontra a qual tabela pertence.
    Retorna o nome da tabela (normalizado).
    Levanta ValueError se ambíguo ou inexistente.
    """
    col_lower = column_name.strip().lower()
    matches = []
    for table in available_tables:
        if col_lower in get_table_columns(table):
            matches.append(table.lower())

    if len(matches) == 0:
        raise ValueError(f"Coluna '{column_name}' não encontrada em nenhuma das tabelas: {available_tables}")
    if len(matches) > 1:
        raise ValueError(
            f"Coluna '{column_name}' é ambígua, encontrada nas tabelas: {matches}. "
            f"Use o formato tabela.coluna para desambiguar."
        )
    return matches[0]


def get_all_table_names() -> list[str]:
    """Retorna todos os nomes de tabelas do schema."""
    return list(SCHEMA.keys())
