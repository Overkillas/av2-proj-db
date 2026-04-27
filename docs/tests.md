# Roteiro de Testes - Processador de Consultas SQL

## Como executar o sistema

```
cd C:\av2-alan
venv\Scripts\python.exe main.py
```

---

## 1. HU1 - Entrada e Validacao da Consulta

### 1.1 Interface grafica com campo de entrada

> **PDF:** "Interface grafica com campo de entrada da consulta."

| # | Teste | Como executar | Resultado esperado |
|---|-------|--------------|-------------------|
| 1.1.1 | Tela abre corretamente | Executar `python main.py` | Janela abre com campo de texto para SQL, botao "Processar Consulta", abas de resultado |
| 1.1.2 | Campo de texto aceita digitacao | Clicar no campo e digitar qualquer texto | Texto aparece normalmente no campo |
| 1.1.3 | Exemplo pre-carregado | Observar o campo ao abrir | Consulta de exemplo ja aparece preenchida |
| 1.1.4 | Botao "Limpar" funciona | Clicar em "Limpar" | Campo de texto e todas as abas ficam vazios |
| 1.1.5 | Botao "Exemplo" funciona | Clicar em "Limpar" e depois em "Exemplo" | Consulta de exemplo e recarregada no campo |

---

### 1.2 Parser valida comandos SQL basicos

> **PDF:** "Parser deve validar comandos SQL basicos selecionados para o trabalho (SELECT, FROM, WHERE, JOIN, ON)."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.2.1 | SELECT + FROM basico | `SELECT cliente.Nome FROM Cliente` | Processamento com sucesso, algebra relacional exibida |
| 1.2.2 | SELECT + FROM + WHERE | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente = 1` | Sucesso, sigma aparece na algebra |
| 1.2.3 | SELECT + FROM + JOIN + ON | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente` | Sucesso, join aparece na algebra |
| 1.2.4 | Consulta completa | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1` | Sucesso, todas as abas preenchidas |
| 1.2.5 | Consulta vazia | (campo vazio, clicar Processar) | Mensagem de erro: consulta vazia |
| 1.2.6 | Sem SELECT | `FROM Cliente` | Erro: "A consulta deve comecar com SELECT" |
| 1.2.7 | Sem FROM | `SELECT cliente.Nome` | Erro: "A consulta deve conter SELECT e FROM" |
| 1.2.8 | JOIN sem ON | `SELECT cliente.Nome FROM Cliente JOIN Pedido` | Erro: numero de JOINs diferente do numero de ONs |

---

### 1.3 Operadores validos

> **PDF:** "Operadores validos para o trabalho (=, >, <, <=, >=, <>, AND, ( ))."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.3.1 | Operador = | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente = 1` | Sucesso |
| 1.3.2 | Operador > | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 10` | Sucesso |
| 1.3.3 | Operador < | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente < 100` | Sucesso |
| 1.3.4 | Operador <= | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente <= 50` | Sucesso |
| 1.3.5 | Operador >= | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente >= 5` | Sucesso |
| 1.3.6 | Operador <> | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente <> 0` | Sucesso |
| 1.3.7 | AND com duas condicoes | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 1 AND cliente.TipoCliente_idTipoCliente = 2` | Sucesso, ambas condicoes aparecem na algebra com simbolo "e logico" |
| 1.3.8 | Parenteses no WHERE | `SELECT cliente.Nome FROM Cliente WHERE (cliente.idCliente > 1) AND (cliente.TipoCliente_idTipoCliente = 2)` | Sucesso (parenteses sao aceitos e ignorados na simplificacao) |

---

### 1.4 Verificacao de existencia de tabelas e atributos

> **PDF:** "Verificacao de existencia de tabelas e atributos."
> **PDF:** "Apenas tabelas/atributos listados no modelo podem ser usados (Imagem 01)."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.4.1 | Tabela inexistente | `SELECT xyz.nome FROM xyz` | Erro: "Tabela 'xyz' nao existe no schema" |
| 1.4.2 | Coluna inexistente | `SELECT cliente.telefone FROM Cliente` | Erro: "Coluna 'cliente.telefone' nao existe" com lista de colunas validas |
| 1.4.3 | Tabela valida, coluna de outra tabela | `SELECT cliente.idPedido FROM Cliente` | Erro: coluna nao existe na tabela cliente |
| 1.4.4 | Tabela do JOIN inexistente | `SELECT cliente.Nome FROM Cliente JOIN Xyz ON cliente.idCliente = xyz.id` | Erro: tabela 'Xyz' nao existe |
| 1.4.5 | Coluna do WHERE inexistente | `SELECT cliente.Nome FROM Cliente WHERE cliente.xyz = 1` | Erro: coluna nao existe |
| 1.4.6 | Todas as 10 tabelas validas | Testar SELECT de cada tabela individualmente (ver lista abaixo) | Todas processam sem erro |

**Tabelas validas para o teste 1.4.6:**
- `SELECT categoria.idCategoria FROM Categoria`
- `SELECT produto.Nome FROM Produto`
- `SELECT tipocliente.Descricao FROM TipoCliente`
- `SELECT cliente.Nome FROM Cliente`
- `SELECT tipoendereco.Descricao FROM TipoEndereco`
- `SELECT endereco.Logradouro FROM Endereco`
- `SELECT telefone.Numero FROM Telefone`
- `SELECT status.Descricao FROM Status`
- `SELECT pedido.DataPedido FROM Pedido`
- `SELECT pedido_has_produto.Quantidade FROM Pedido_has_Produto`

---

### 1.5 Multiplos JOINs

> **PDF:** "Consultas devem suportar multiplos JOINs (0, 1,...,N)."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.5.1 | 0 JOINs | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente = 1` | Sucesso, sem juncao na algebra |
| 1.5.2 | 1 JOIN | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente` | Sucesso, uma juncao na algebra |
| 1.5.3 | 2 JOINs | `SELECT cliente.Nome, pedido.idPedido, status.Descricao FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente JOIN Status ON pedido.Status_idStatus = status.idStatus` | Sucesso, duas juncoes encadeadas |
| 1.5.4 | 3 JOINs | `SELECT cliente.Nome, pedido.DataPedido, produto.Nome FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente JOIN Pedido_has_Produto ON pedido.idPedido = pedido_has_produto.Pedido_idPedido JOIN Produto ON pedido_has_produto.Produto_idProduto = produto.idProduto` | Sucesso, tres juncoes encadeadas |
| 1.5.5 | 4 JOINs | `SELECT cliente.Nome, pedido.DataPedido, produto.Nome, categoria.Descricao FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente JOIN Pedido_has_Produto ON pedido.idPedido = pedido_has_produto.Pedido_idPedido JOIN Produto ON pedido_has_produto.Produto_idProduto = produto.idProduto JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria` | Sucesso, quatro juncoes |

---

### 1.6 Case-insensitive

> **PDF:** "Deve ignorar a diferenca entre palavras maiusculas e minusculas."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.6.1 | Tudo maiusculo | `SELECT CLIENTE.NOME FROM CLIENTE` | Sucesso |
| 1.6.2 | Tudo minusculo | `select cliente.nome from cliente` | Sucesso |
| 1.6.3 | Misturado | `SeLeCt CLIENTE.nome FrOm cliente` | Sucesso |
| 1.6.4 | Keywords minusculas | `select cliente.Nome from Cliente where cliente.idCliente = 1` | Sucesso |

---

### 1.7 Espacos em branco

> **PDF:** "Deve ignorar repeticoes de espacos em branco."

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 1.7.1 | Espacos extras entre palavras | `SELECT   cliente.Nome   FROM   Cliente` | Sucesso, mesma saida que sem espacos extras |
| 1.7.2 | Espacos antes e depois | `   SELECT cliente.Nome FROM Cliente   ` | Sucesso |
| 1.7.3 | Tabs e quebras de linha | Digitar com Enter entre clausulas (multilinha) | Sucesso |

---

## 2. HU2 - Conversao para Algebra Relacional

### 2.1 Exibicao na interface

> **PDF:** "Exibir a consulta equivalente em algebra relacional na interface grafica."
> **PDF:** "A conversao deve preservar operadores e condicoes."

| # | Teste | SQL de entrada | Resultado esperado na aba "Algebra Relacional" |
|---|-------|---------------|-----------------------------------------------|
| 2.1.1 | SELECT simples | `SELECT cliente.Nome FROM Cliente` | `pi cliente.Nome (Cliente)` |
| 2.1.2 | SELECT + WHERE | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente = 1` | `pi cliente.Nome (sigma cliente.idCliente = 1 (Cliente))` |
| 2.1.3 | SELECT + JOIN | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente` | `pi cols (Cliente join cond Pedido)` |
| 2.1.4 | Consulta completa (exemplo do .txt) | `SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0` | `pi cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido (sigma cliente.TipoCliente_idTipoCliente = 1 ^ pedido.ValorTotalPedido = 0 (Cliente join cond pedido))` |

---

### 2.2 Simbolos corretos

> **PDF:** "Representacao deve incluir selecao (sigma), projecao (pi) e juncoes (bowtie)."

| # | Teste | O que verificar | Resultado esperado |
|---|-------|----------------|-------------------|
| 2.2.1 | Simbolo de selecao | Na expressao da aba "Algebra Relacional" | Aparece o simbolo sigma ao lado das condicoes WHERE |
| 2.2.2 | Simbolo de projecao | Na expressao da aba "Algebra Relacional" | Aparece o simbolo pi ao lado das colunas SELECT |
| 2.2.3 | Simbolo de juncao | Na expressao da aba "Algebra Relacional" | Aparece o simbolo bowtie entre tabelas com JOIN |
| 2.2.4 | Simbolo de AND | Na expressao com multiplas condicoes WHERE | Aparece o simbolo logico "e" entre as condicoes |

---

## 3. HU3 - Construcao do Grafo de Operadores

> **PDF:** "O grafo deve ser gerado em memoria e exibido na interface."

### 3.1 Estrutura do grafo

| # | Teste | O que verificar | Resultado esperado |
|---|-------|----------------|-------------------|
| 3.1.1 | Grafo gerado em memoria | Processar qualquer consulta valida | Aba "Grafo de Operadores" exibe desenho da arvore no Canvas |
| 3.1.2 | Representacao textual | Aba "Arvore (Texto)" | Arvore formatada com identacao mostrando hierarquia |

---

### 3.2 Nos e arestas

> **PDF:** "Cada no deve representar operadores."
> **PDF:** "Arestas devem representar fluxo de resultados intermediarios."
> **PDF:** "As folhas devem representar as tabelas."
> **PDF:** "A raiz deve representar a ultima projecao."

| # | Teste | SQL de entrada | O que verificar no grafo |
|---|-------|---------------|------------------------|
| 3.2.1 | Folhas sao tabelas | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1` | Os nos mais inferiores (folhas) sao "Cliente" e "Pedido" (nomes de tabelas, cor amarela) |
| 3.2.2 | Raiz e projecao final | Mesma consulta | O no mais superior (raiz) e "pi cliente.Nome, pedido.idPedido" (cor verde) |
| 3.2.3 | Nos intermediarios - selecao | Mesma consulta | Nos sigma aparecem acima das tabelas que tem WHERE (cor azul) |
| 3.2.4 | Nos intermediarios - projecao | Mesma consulta | Nos pi aparecem acima dos sigma (cor verde) |
| 3.2.5 | Nos intermediarios - juncao | Mesma consulta | No bowtie conecta as duas subarvores (cor salmao) |
| 3.2.6 | Arestas (setas) | Mesma consulta | Setas conectam cada no ao seu pai, indicando fluxo de dados |
| 3.2.7 | Scroll do Canvas | Consulta com 3+ JOINs (arvore grande) | Scrollbars aparecem e permitem navegar pela arvore completa |

---

### 3.3 Grafo com diferentes complexidades

> **PDF:** "O grafo deve respeitar dependencias logicas da consulta."

| # | Teste | SQL de entrada | Estrutura esperada da arvore |
|---|-------|---------------|----------------------------|
| 3.3.1 | Sem JOIN, sem WHERE | `SELECT cliente.Nome FROM Cliente` | `pi -> Cliente` (2 nos) |
| 3.3.2 | Sem JOIN, com WHERE | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 5` | `pi -> sigma -> Cliente` (3 nos) |
| 3.3.3 | 1 JOIN, sem WHERE | `SELECT produto.Nome, categoria.Descricao FROM Produto JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria` | `pi_final -> join -> (pi_Produto -> Produto, pi_Categoria -> Categoria)` |
| 3.3.4 | 1 JOIN, com WHERE nos dois lados | Consulta do exemplo 2.1.4 | `pi_final -> join -> (pi -> sigma -> Cliente, pi -> sigma -> Pedido)` |
| 3.3.5 | 3 JOINs | Consulta do teste 1.5.4 | Arvore com 3 nos de juncao encadeados |

---

## 4. HU4 - Otimizacao da Consulta

### 4.1 Heuristica de reducao de tuplas

> **PDF:** "Aplicar heuristicas: selecoes que reduzem tuplas primeiro."
> **PDF (Heuristicas):** "Aplicar primeiro as operacoes que reduzem o tamanho dos resultados intermediarios - operacoes de selecao - reduzem o numero de tuplas."

| # | Teste | SQL de entrada | O que verificar na aba "Otimizacao" |
|---|-------|---------------|-------------------------------------|
| 4.1.1 | Sigma empurrado para tabela correta | `SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0` | No Passo 1: sigma de TipoCliente fica junto de Cliente, sigma de ValorTotal fica junto de Pedido. Formato: `((sigma cond1 (Cliente)) join cond (sigma cond2 (Pedido)))` |
| 4.1.2 | Condicao unica empurrada | `SELECT cliente.Nome, pedido.idPedido FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1` | Sigma aparece apenas em Cliente; Pedido fica sem sigma |
| 4.1.3 | Sem WHERE - nada muda | `SELECT produto.Nome, categoria.Descricao FROM Produto JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria` | Passo 1 mostra expressao sem nenhum sigma (identica a original sem sigma) |
| 4.1.4 | Comparar com .txt referencia | Consulta do teste 4.1.1 | Comparar saida com o "Passo 2" do arquivo "Select Exemplo 1 Convertido para Algebra Relacional.txt": `pi cols ((sigma cond1 (Cliente)) join cond (sigma cond2 (Pedido)))` |

---

### 4.2 Heuristica de reducao de atributos

> **PDF:** "Aplicar heuristicas: projecoes que reduzem atributos na sequencia."
> **PDF (Heuristicas):** "operacoes de projecao - reduzem o numero de atributos."

| # | Teste | SQL de entrada | O que verificar na aba "Otimizacao" |
|---|-------|---------------|-------------------------------------|
| 4.2.1 | Pi com colunas minimas por tabela | `SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0` | No Passo 2: Cliente recebe `pi cliente.nome, cliente.idcliente` (nome do SELECT + idcliente do JOIN). Pedido recebe `pi pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido, pedido.Cliente_idCliente` (colunas do SELECT + Cliente_idCliente do JOIN) |
| 4.2.2 | Tabela sem SELECT mas com JOIN | `SELECT cliente.Nome, produto.Nome FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente JOIN Pedido_has_Produto ON pedido.idPedido = pedido_has_produto.Pedido_idPedido JOIN Produto ON pedido_has_produto.Produto_idProduto = produto.idProduto` | Pedido recebe pi com colunas de JOIN apenas (Cliente_idCliente, idPedido). Pedido_has_Produto recebe pi com colunas de JOIN apenas (Pedido_idPedido, Produto_idProduto) |
| 4.2.3 | Comparar com .txt referencia | Consulta do teste 4.2.1 | Comparar saida com o "Heuristica da reducao de campos" do arquivo "Select Exemplo 1 Convertido para Algebra Relacional.txt" |
| 4.2.4 | Sem JOIN - pi intermediario omitido | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 5` | Passo 2 NAO mostra pi intermediario redundante (so o pi final ja basta) |

---

### 4.3 Juncao e produto cartesiano

> **PDF:** "selecoes e juncoes mais restritivas primeiro."
> **PDF (Heuristicas):** "evitar a operacao de produto cartesiano."

| # | Teste | O que verificar | Resultado esperado |
|---|-------|----------------|-------------------|
| 4.3.1 | Todas as juncoes usam condicao ON | Processar qualquer consulta com JOIN | Na algebra relacional, todos os JOINs aparecem com condicao (bowtie + condicao), nunca como produto cartesiano (X) |
| 4.3.2 | Arvore reflete juncoes | No grafo otimizado | Nos de juncao sempre mostram a condicao (ex: "bowtie cliente.id = pedido.Cliente_id") |

---

### 4.4 Grafo otimizado exibido

> **PDF:** "Exibir o grafo otimizado."
> **PDF:** "A arvore deve ser reordenada (ou construida) para eficiencia, aplicando heuristicas."

| # | Teste | O que verificar | Resultado esperado |
|---|-------|----------------|-------------------|
| 4.4.1 | Grafo mostra arvore otimizada | Aba "Grafo de Operadores" | Arvore desenhada ja incorpora sigma empurrado e pi intermediarios |
| 4.4.2 | Arvore texto confirma otimizacao | Aba "Arvore (Texto)" | Texto identado mostra: pi_final -> join -> (pi -> sigma -> Tabela) |

---

## 5. HU5 - Plano de Execucao

### 5.1 Ordem de execucao

> **PDF:** "Exibir ordem de execucao (plano de execucao ordenado)."
> **PDF:** "Listar operacoes na ordem correta."
> **PDF:** "Execucao deve seguir ordem definida pelo grafo otimizado."

| # | Teste | SQL de entrada | Ordem esperada na aba "Plano de Execucao" |
|---|-------|---------------|------------------------------------------|
| 5.1.1 | Plano para 1 JOIN + WHERE em ambos | `SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0` | Passo 1: Ler tabela Cliente / Passo 2: sigma TipoCliente=1 / Passo 3: pi nome,idcliente / Passo 4: Ler tabela pedido / Passo 5: sigma ValorTotal=0 / Passo 6: pi colunas_pedido / Passo 7: Join / Passo 8: pi final |
| 5.1.2 | Plano sem WHERE | `SELECT produto.Nome, categoria.Descricao FROM Produto JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria` | Passo 1: Ler Produto / Passo 2: pi / Passo 3: Ler Categoria / Passo 4: pi / Passo 5: Join / Passo 6: pi final |
| 5.1.3 | Plano sem JOIN | `SELECT cliente.Nome FROM Cliente WHERE cliente.idCliente > 5` | Passo 1: Ler Cliente / Passo 2: sigma / Passo 3: pi final |
| 5.1.4 | Plano com 3 JOINs | Consulta do teste 1.5.4 | 13 passos: leitura de 4 tabelas + sigma + pis intermediarios + 3 joins + pi final |

---

### 5.2 Coerencia grafo x plano

| # | Teste | O que verificar | Resultado esperado |
|---|-------|----------------|-------------------|
| 5.2.1 | Numero de passos = numero de nos | Comparar quantidade de passos no plano com nos da arvore | Devem ser iguais |
| 5.2.2 | Ordem bottom-up | Comparar plano com arvore | Tabelas (folhas) aparecem primeiro nos passos; pi final (raiz) aparece por ultimo |
| 5.2.3 | Operacoes de cada passo correspondem ao no | Para cada passo, verificar se "Ler tabela" corresponde a folha, "sigma" a selecao, etc. | Tipos de operacao coincidem com os tipos dos nos da arvore |

---

## 6. Testes de Integracao (Fluxo Completo)

> **PDF (Funcionamento):** "A string com a consulta SQL e entrada na interface grafica; A string e parseada e o comando SQL e validado; O comando SQL e convertido para algebra relacional; Mostrar na Interface a conversao do SQL para algebra relacional; A algebra relacional e otimizada conforme as heuristicas; O grafo de operadores e construido em memoria; O grafo de operadores deve ser mostrado na Interface grafica; O resultado da consulta mostrando cada operacao e a ordem que sera executada, e exibido na interface grafica (plano de execucao)."

### 6.1 Consulta do exemplo principal do PDF

| Passo | Acao | Resultado esperado |
|-------|------|-------------------|
| 1 | Digitar: `SELECT cliente.nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido FROM Cliente JOIN pedido ON cliente.idcliente = pedido.Cliente_idCliente WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0` | SQL aparece no campo |
| 2 | Clicar "Processar Consulta" | Barra de status: "Processamento concluido com sucesso" |
| 3 | Verificar aba "Algebra Relacional" | Expressao com pi, sigma, join. Mostra SQL original e detalhes do parsing |
| 4 | Verificar aba "Otimizacao" | Passo 1: sigma empurrado. Passo 2: pi intermediario inserido |
| 5 | Verificar aba "Grafo de Operadores" | Arvore desenhada com nos coloridos, setas, scroll funcional |
| 6 | Verificar aba "Arvore (Texto)" | Arvore identada: pi_final -> join -> (pi->sigma->Cli, pi->sigma->Ped) |
| 7 | Verificar aba "Plano de Execucao" | 8 passos ordenados corretamente |

---

### 6.2 Consulta complexa com multiplos JOINs

| Passo | Acao | Resultado esperado |
|-------|------|-------------------|
| 1 | Digitar: `SELECT cliente.Nome, pedido.DataPedido, produto.Nome, categoria.Descricao FROM Cliente JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente JOIN Pedido_has_Produto ON pedido.idPedido = pedido_has_produto.Pedido_idPedido JOIN Produto ON pedido_has_produto.Produto_idProduto = produto.idProduto JOIN Categoria ON produto.Categoria_idCategoria = categoria.idCategoria WHERE cliente.TipoCliente_idTipoCliente = 1` | SQL aparece no campo |
| 2 | Clicar "Processar Consulta" | Sucesso |
| 3 | Verificar aba "Algebra Relacional" | 4 juncoes encadeadas com sigma global |
| 4 | Verificar aba "Otimizacao" | Sigma empurrado apenas para Cliente. Pi intermediarios em todas as 5 tabelas |
| 5 | Verificar aba "Grafo de Operadores" | Arvore grande com 4 juncoes, scrollavel |
| 6 | Verificar aba "Plano de Execucao" | Muitos passos, tabelas lidas primeiro, pi final por ultimo |

---

### 6.3 Consulta minima (sem JOIN, sem WHERE)

| Passo | Acao | Resultado esperado |
|-------|------|-------------------|
| 1 | Digitar: `SELECT cliente.Nome, cliente.Email FROM Cliente` | SQL aparece |
| 2 | Clicar "Processar Consulta" | Sucesso |
| 3 | Aba "Algebra Relacional" | `pi cliente.Nome, cliente.Email (Cliente)` |
| 4 | Aba "Otimizacao" | Sem sigma, sem pi intermediario (nada a otimizar) |
| 5 | Aba "Grafo" | Arvore simples: pi -> Cliente |
| 6 | Aba "Plano" | 2 passos: Ler Cliente, pi final |

---

## 7. Testes de Robustez

| # | Teste | SQL de entrada | Resultado esperado |
|---|-------|---------------|-------------------|
| 7.1 | SQL com ponto e virgula no final | `SELECT cliente.Nome FROM Cliente;` | Sucesso (ponto e virgula ignorado) |
| 7.2 | Multiplos processamentos seguidos | Processar uma consulta, depois outra diferente | Segunda consulta substitui resultados da primeira em todas as abas |
| 7.3 | Processar apos erro | Digitar consulta invalida (erro), corrigir e processar novamente | Segunda tentativa funciona normalmente |
| 7.4 | Coluna ambigua (descricao existe em varias tabelas) | `SELECT descricao FROM Categoria` | Sucesso (so ha uma tabela, sem ambiguidade) |
| 7.5 | Consulta multilinha | Digitar consulta com Enter entre clausulas | Sucesso |
| 7.6 | Numeros decimais no WHERE | `SELECT produto.Nome FROM Produto WHERE produto.Preco > 99.99` | Sucesso |

---

## Checklist Final de Criterios de Avaliacao

> **PDF:** Tabela "Criterios de Avaliacao"

| Criterio | Peso | Testes que cobrem | Passou? |
|----------|------|-------------------|---------|
| Interface grafica funcional | 1.0 | 1.1.1 a 1.1.5, 6.1 a 6.3 | [ ] |
| Parsing e validacao correta | 2.0 | 1.2.x, 1.3.x, 1.4.x, 1.5.x, 1.6.x, 1.7.x | [ ] |
| Conversao algebra relacional | 1.5 | 2.1.x, 2.2.x | [ ] |
| Grafo operadores otimizado | 1.0 | 3.1.x, 3.2.x, 3.3.x, 4.4.x | [ ] |
| Ordem de execucao | 1.5 | 5.1.x, 5.2.x | [ ] |
| Heuristica reducao de tuplas | 1.0 | 4.1.x | [ ] |
| Heuristica reducao de atributos | 1.0 | 4.2.x | [ ] |
| Uso da juncao | 1.0 | 4.3.x, 1.5.x | [ ] |
| **TOTAL** | **10.0** | | |
