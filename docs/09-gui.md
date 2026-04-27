# 09 — `gui.py`

## Propósito

Interface gráfica completa do processador de consultas. Construída com
**Tkinter** (sem dependências externas), implementa:

- Editor de SQL com syntax highlighting básico.
- Botões "Processar Consulta", "Carregar Exemplo", "Limpar".
- 5 abas de resultados (Álgebra, Otimização, Grafo desenhado, Plano,
  Árvore em texto).
- Tema visual escuro moderno (paleta slate/cyan).
- Barra de status colorida (info, sucesso, erro).
- Diálogos modais para erros específicos.
- Desenho da árvore de operadores em um Canvas.

Este é o **orquestrador** do projeto: ao clicar "Processar Consulta",
ele chama, em ordem, todos os módulos do pipeline (parser → álgebra →
otimização → árvore → plano).

## Estrutura geral do arquivo

```
gui.py
├── Imports (tkinter + módulos do projeto)
├── THEME (dict com paleta de cores)
├── NODE_COLORS / NODE_BORDER_COLORS (cores dos nós da árvore)
├── class TreeDrawer
│   ├── __init__
│   ├── draw()
│   ├── _calculate_layout()
│   ├── _draw_edges()
│   └── _draw_nodes()
└── class ProcessadorConsultasGUI
    ├── EXEMPLO_SQL (consulta pré-carregada)
    ├── __init__
    ├── _configure_style()
    ├── _create_widgets()
    ├── _make_output_text()
    ├── _setup_sql_highlighting()
    ├── _highlight_sql()
    ├── _on_process()         # callback principal
    ├── _on_clear()
    ├── _on_example()
    ├── _set_status()
    ├── _box_header(), _section()  (helpers de formatação)
    ├── _display_algebra()
    ├── _display_optimization()
    ├── _display_tree()
    ├── _display_plan()
    ├── _set_text(), _clear_results()
    └── run()
```

## Imports

```python
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont

from schema import SCHEMA
from sql_parser import (
    SQLParser, ParsedQuery,
    UnknownTableError, InvalidOperatorError, SQLValidationError,
)
from relational_algebra import RelationalAlgebraConverter
from optimizer import QueryOptimizer
from query_tree import QueryTree, TreeNode, NodeType
from execution_plan import ExecutionPlanGenerator
```

A GUI **importa todos os módulos do projeto**. É o único arquivo com
essa abrangência (porque é o orquestrador).

`tkinter.ttk` traz os widgets temáveis (botões, abas, label-frames,
scrollbars). `scrolledtext` é o widget de texto multi-linha com
scrollbar embutida. `messagebox` faz diálogos modais
("Erro de Validação", etc.). `font as tkfont` permite personalizar
fontes (mas no fim acabou não sendo muito usado — fontes ficam
definidas inline).

## Tema visual (`THEME` e `NODE_COLORS`)

```python
THEME = {
    "bg":            "#1E293B",   # slate-800 (fundo principal)
    "bg_panel":      "#273548",   # painel interno
    "bg_input":      "#0F172A",   # editor SQL (slate-900)
    "bg_output":     "#F8FAFC",   # áreas de resultado (claro)
    "fg":            "#E2E8F0",   # texto principal claro
    "fg_muted":      "#94A3B8",   # texto secundário
    "fg_dark":       "#1E293B",   # texto escuro sobre fundo claro
    "accent":        "#38BDF8",   # cyan/azul primário
    "accent_hover":  "#0EA5E9",
    "accent_dark":   "#0369A1",
    "danger":        "#EF4444",
    "success":       "#22C55E",
    "warning":       "#F59E0B",
    "border":        "#334155",
    "canvas_bg":     "#FAFAFA",
}
```

Inspirada no Tailwind CSS (paleta slate/sky). Centralizar as cores num
único dict facilita manutenção: para mudar o tema inteiro basta alterar
estas constantes.

```python
NODE_COLORS = {
    NodeType.TABLE:      "#FEF3C7",   # amarelo pastel
    NodeType.SELECTION:  "#DBEAFE",   # azul pastel
    NodeType.PROJECTION: "#DCFCE7",   # verde pastel
    NodeType.JOIN:       "#FEE2E2",   # rosa/salmão pastel
}
NODE_BORDER_COLORS = {
    NodeType.TABLE:      "#D97706",
    NodeType.SELECTION:  "#2563EB",
    NodeType.PROJECTION: "#16A34A",
    NodeType.JOIN:       "#DC2626",
}
```

Quatro cores pasteis para preenchimento + bordas em tons mais
saturados. A escolha cromática faz cada tipo de nó ser identificável
de longe sem precisar ler o label.

## Classe `TreeDrawer`

Responsável por **desenhar** a árvore de operadores no `tk.Canvas`.

### Constantes de layout

```python
H_SPACING = 200    # espaçamento horizontal entre folhas (pixels)
V_SPACING = 90     # espaçamento vertical entre níveis
NODE_PADX = 14     # padding horizontal do texto no nó
NODE_PADY = 8      # padding vertical
MARGIN    = 60     # margem ao redor da árvore
```

Ajustáveis se você quiser árvores mais compactas ou mais espaçadas.

### Algoritmo de layout (`_calculate_layout`)

```python
def _calculate_layout(self, node: TreeNode, depth: int):
    if not node.children:
        self.positions[id(node)] = (self._leaf_counter, depth)
        self._leaf_counter += 1
        return

    for child in node.children:
        self._calculate_layout(child, depth + 1)

    children_x = [self.positions[id(c)][0] for c in node.children]
    avg_x = sum(children_x) / len(children_x)
    self.positions[id(node)] = (avg_x, depth)
```

Algoritmo bem simples (categoria *naive tree layout*):

1. **Folhas** recebem posições x sequenciais: 0, 1, 2, 3...
2. **Nós internos** recebem x = média dos x dos filhos.
3. **y** = profundidade (depth) na árvore.

Vantagens: O(n), determinístico, óbvio de entender.
Desvantagens: pode haver sobreposição em árvores muito amplas com
muitas profundidades; não centraliza filhos perfeitamente.

Para o tamanho de árvore típico deste projeto (até ~20 nós), o
algoritmo simples funciona bem.

A chave do dict é `id(node)` (identidade do objeto Python), não o
label, porque labels podem se repetir.

### Conversão para pixels

```python
for nid, (gx, gy) in self.positions.items():
    px = gx * self.H_SPACING + self.MARGIN
    py = gy * self.V_SPACING + self.MARGIN
    pixel_positions[nid] = (px, py)
self.positions = pixel_positions
```

Multiplica as coordenadas lógicas pelos espaçamentos e adiciona a
margem. Reescreve `self.positions` (sobrescrita intencional).

### `_draw_edges` — arestas

Desenha uma linha de cada nó pai a cada filho:

```python
self.canvas.create_line(
    px, py + 20, cx, cy - 20,
    fill="#555555", width=2, arrow=tk.LAST,
)
```

`+20`/`-20` desloca os endpoints para fora dos retângulos dos nós,
para a linha não atravessar o texto. `arrow=tk.LAST` adiciona uma
seta no extremo final.

### `_draw_nodes` — retângulos arredondados com texto

Aqui está um truque interessante: o Canvas do Tkinter **não tem**
primitivo nativo para retângulos arredondados. A solução adotada é
desenhar um polígono com 12 vértices (4 cantos × 3 vértices cada) e
usar `smooth=True`:

```python
self.canvas.create_polygon(
    x1 + r, y1,  x2 - r, y1,
    x2, y1,  x2, y1 + r,
    x2, y2 - r,  x2, y2,
    x2 - r, y2,  x1 + r, y2,
    x1, y2,  x1, y2 - r,
    x1, y1 + r,  x1, y1,
    fill=fill_color, outline=border_color, width=2, smooth=True,
)
```

Com `smooth=True`, o Tkinter desenha curvas Bézier entre os vértices,
arredondando os cantos. O efeito visual é o de um botão moderno.

Antes de desenhar o retângulo, o código mede o tamanho do texto:

```python
text_id = self.canvas.create_text(x, y, text=label, anchor="center", font=...)
bbox = self.canvas.bbox(text_id)
self.canvas.delete(text_id)
```

Cria o texto temporário, lê seu bounding box, e o deleta. Depois usa
as dimensões para calcular o retângulo. Em seguida, desenha o texto
final por cima do polígono.

### Scroll automático

```python
self.canvas.configure(scrollregion=(
    0, 0,
    max(all_x) + self.H_SPACING + self.MARGIN,
    max(all_y) + self.V_SPACING + self.MARGIN,
))
```

Define a região de scroll para acomodar a árvore inteira. As
scrollbars (criadas no `_create_widgets`) atualizam-se automaticamente.

## Classe `ProcessadorConsultasGUI`

### Constante `EXEMPLO_SQL`

```python
EXEMPLO_SQL = (
    "SELECT cliente.Nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido\n"
    "FROM Cliente\n"
    "JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente\n"
    "WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0"
)
```

Consulta de teste pré-carregada — corresponde ao **Exemplo 1** do
arquivo `references/Select Exemplo 1.txt`. Permite validar visualmente
todo o pipeline imediatamente após abrir a aplicação.

### `__init__`

```python
def __init__(self):
    self.root = tk.Tk()
    self.root.title("Processador de Consultas SQL")
    self.root.geometry("1200x850")
    self.root.minsize(960, 680)
    self.root.configure(bg=THEME["bg"])

    self._configure_style()
    self._create_widgets()
```

Cria a janela principal, define dimensões e cor de fundo, configura
estilo e widgets. **Não chama `mainloop()`** — quem chama é `run()`,
permitindo que o caller faça setup adicional antes do loop.

### `_configure_style()` — temas ttk

Os widgets `ttk` usam estilos nomeados. O método configura:

- `TFrame`, `Panel.TFrame` — frames base e de painel.
- `TLabel` (e variantes `Muted`, `Header`, `Subheader`) — labels.
- `Card.TLabelframe` — frames com borda e título.
- `Primary.TButton`, `Secondary.TButton` — dois estilos de botão
  (azul cheio vs. neutro).
- `TNotebook`, `TNotebook.Tab` — abas.
- `Status.TLabel`, `StatusError.TLabel`, `StatusOK.TLabel` —
  variantes da barra de status.
- `Vertical.TScrollbar`, `Horizontal.TScrollbar` — scrollbars
  combinando com o tema.

Cada `style.configure(...)` define propriedades default (background,
foreground, font, padding) e `style.map(...)` define propriedades
para estados dinâmicos (`active`, `pressed`, `selected`).

`style.theme_use("clam")` escolhe o tema base "clam" do Tkinter — é o
que aceita customização de cores mais facilmente (outros temas como
"vista" ou "default" travam algumas propriedades).

### `_create_widgets()` — montagem da interface

Estrutura visual de cima para baixo:

1. **Cabeçalho**: título + subtítulo, com linha divisória.
2. **Frame "Consulta SQL"**: `LabelFrame` contendo o editor + botões
   + info lateral.
3. **Notebook (abas)**: 5 abas com diferentes conteúdos.
4. **Barra de status**: rodapé fixo.

#### Editor SQL

Um `scrolledtext.ScrolledText` configurado com aparência de "code
editor" (fonte Consolas, fundo escuro, cursor cyan). Preenchido com
`EXEMPLO_SQL` na criação. Recebe binding em `<KeyRelease>` para
re-aplicar syntax highlighting a cada digitação.

#### Botões

Três botões na ordem: **▶ Processar** (estilo primário azul),
**Carregar Exemplo** (secundário), **Limpar** (secundário). Cada um
chama um callback `_on_process`/`_on_example`/`_on_clear`.

#### Painel de info lateral

Mostra os operadores e tabelas suportados, do lado direito do frame
de botões — usuário descobre o que está disponível sem precisar
abrir documentação.

#### Notebook (5 abas)

| Aba | Tipo | Conteúdo |
|-----|------|----------|
| 📐 Álgebra Relacional | `ScrolledText` | SQL original + AR + resumo do parsing |
| ⚡ Otimização | `ScrolledText` | Expressão original + 2 passos da otimização |
| 🌳 Grafo de Operadores | `Canvas` (com scrollbars) | Árvore desenhada |
| 📋 Plano de Execução | `ScrolledText` | Saída de `format_plan()` |
| 🧾 Árvore (Texto) | `ScrolledText` (sem wrap) | Saída de `tree.to_text()` |

A primeira aba recebe foco automaticamente após processamento bem
sucedido (`self.notebook.select(0)`).

#### Barra de status

`ttk.Label` com texto controlado por `tk.StringVar`. Estilo muda
entre `Status.TLabel` (info), `StatusOK.TLabel` (sucesso, verde),
`StatusError.TLabel` (erro, vermelho).

### Syntax highlighting (`_setup_sql_highlighting` + `_highlight_sql`)

```python
_SQL_KEYWORDS = ("SELECT", "FROM", "WHERE", "JOIN", "ON", "AND")
```

Configura **tags** no widget de texto, cada uma com cor própria:
- `kw` — palavras-chave (ciano, negrito).
- `str` — strings entre aspas (amarelo).
- `num` — números (lilás).
- `op` — operadores (rosa).

A função `_highlight_sql()` é chamada a cada `<KeyRelease>`. Ela:

1. Remove todas as tags.
2. Para cada keyword, faz regex com `\b{kw}\b` e aplica tag `kw`.
3. Para strings, números e operadores: regex e aplica tag.

A conversão de **offset de regex** para **posição Tk** usa o formato
`f"1.0 + {match.start()} chars"` — sintaxe específica do Tkinter
(que mistura linha.coluna com offsets em chars).

**Custo**: re-tokeniza tudo a cada tecla pressionada. Para SQLs
pequenos isso é instantâneo; para SQLs muito longos pode dar
latência perceptível. Na prática, irrelevante para este projeto.

### `_on_process()` — pipeline completo

Esta é a **função mais importante da GUI**. Ao clicar "Processar
Consulta", ela executa todo o pipeline:

```python
def _on_process(self):
    sql = self.sql_input.get("1.0", tk.END).strip()
    if not sql:
        self._set_status("Erro: consulta SQL vazia.", kind="error")
        return

    try:
        # 1) PARSING
        parser = SQLParser()
        parsed = parser.parse(sql)

        # 2) ÁLGEBRA RELACIONAL
        converter = RelationalAlgebraConverter(parsed)
        algebra_expr = converter.convert()
        self._display_algebra(algebra_expr, parsed)

        # 3) OTIMIZAÇÃO
        optimizer = QueryOptimizer(parsed)
        steps = optimizer.optimize()
        self._display_optimization(algebra_expr, steps)

        # 4) ÁRVORE
        tree = QueryTree(parsed, optimizer)
        root_node = tree.build()
        self._display_tree(tree, root_node)

        # 5) PLANO
        planner = ExecutionPlanGenerator(tree)
        plan_steps = planner.generate()
        plan_text = planner.format_plan()
        self._display_plan(plan_text)

        self._set_status("✓ Processamento concluído com sucesso.", kind="ok")
        self.notebook.select(0)

    except UnknownTableError as e:
        # diálogo específico
    except InvalidOperatorError as e:
        # diálogo específico
    except SQLValidationError as e:
        # diálogo genérico
    except ValueError as e:
        # diálogo genérico
    except Exception as e:
        # fallback
```

Note a **hierarquia de exceções**: as exceções mais específicas
(`UnknownTableError`, `InvalidOperatorError`) são capturadas
primeiro, e cada uma exibe uma mensagem customizada com lista de
sugestões. A genérica `SQLValidationError` é uma rede de segurança
para o resto. `ValueError` e `Exception` cobrem erros inesperados.

A ordem **`except UnknownTableError → InvalidOperatorError → SQLValidationError → ValueError → Exception`** é crucial: como
`UnknownTableError` herda de `SQLValidationError` que herda de
`ValueError`, se você invertesse a ordem o `except ValueError` pegaria
tudo primeiro e os blocos específicos nunca rodariam.

Cada bloco de erro:
1. Atualiza a barra de status com mensagem curta.
2. Limpa os resultados anteriores (`_clear_results()`).
3. Escreve mensagem detalhada na aba "Álgebra".
4. Mostra um `messagebox` modal.

### Helpers de formatação (`_box_header`, `_section`)

```python
_BOX_WIDTH = 68

def _box_header(self, title: str) -> list[str]:
    w = self._BOX_WIDTH
    inner = w - 2
    top = "╔" + "═" * inner + "╗"
    mid = "║" + title.center(inner) + "║"
    bot = "╚" + "═" * inner + "╝"
    return [top, mid, bot]
```

Cria caixas decorativas usando caracteres Unicode de bordas duplas
(`╔ ═ ╗ ║ ╚ ╝`). O método `_section` cria um separador menor com
`─ ─ ─` e um título prefixado com `▸`.

Esses helpers são puramente cosméticos — fazem as áreas de saída
ficarem com aparência de "relatório técnico" em vez de texto cru.

### Métodos `_display_*`

Quatro funções de exibição, uma por aba:

#### `_display_algebra(expression, parsed)`

Monta um texto com:
- Header "CONVERSÃO SQL → ÁLGEBRA RELACIONAL"
- Seção "SQL Original" com a consulta digitada (linha por linha)
- Seção "Álgebra Relacional (conversão direta)" com a string da AR
- Seção "Resumo do parsing" com contagens (tabelas, JOINs, condições,
  colunas)

#### `_display_optimization(original_expr, steps)`

- Header "OTIMIZAÇÃO DA CONSULTA"
- Seção com a expressão original
- Para cada `OptimizationStep`: seção "PASSO N — Nome", descrição, e
  expressão resultante

#### `_display_tree(tree, root_node)`

Faz duas coisas distintas:

1. **Desenha** no Canvas: `TreeDrawer(self.canvas, root_node).draw()`.
2. **Texto** na aba "Árvore (Texto)": chama `tree.to_text()` com
   header e legenda.

#### `_display_plan(plan_text)`

Trivial: só joga `plan_text` (já formatado por `format_plan()`)
dentro do widget.

### Utilitários

#### `_set_text(widget, text)`

```python
def _set_text(self, widget, text):
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)
    widget.configure(state=tk.DISABLED)
```

Os widgets de saída ficam em `state=tk.DISABLED` (read-only) por
padrão — para o usuário não conseguir editar a saída. Para alterar
o conteúdo é preciso reabilitar, modificar e desabilitar de novo.
Esse helper encapsula esse padrão.

#### `_clear_results()`

Limpa todas as áreas de resultado (incluindo o Canvas).

### `run()`

```python
def run(self):
    self.root.mainloop()
```

Inicia o event loop do Tkinter. Bloqueia até a janela fechar.

## Por que tudo numa classe só?

A classe `ProcessadorConsultasGUI` tem ~480 linhas e ~15 métodos.
Poderia ser dividida em sub-classes (ex.: `SQLEditorPanel`,
`ResultsNotebook`), mas o ganho de complexidade não compensa para um
trabalho acadêmico. Tudo numa classe é mais fácil de ler de uma vez.

A separação real do projeto está **entre módulos** (parser vs
optimizer vs tree etc.), não dentro da GUI.

## Como você customiza esta GUI

| Quero mudar... | Onde editar |
|----------------|-------------|
| Cor de algum elemento | dict `THEME` |
| Cor dos nós da árvore | `NODE_COLORS` / `NODE_BORDER_COLORS` |
| Espaçamento da árvore | constantes em `TreeDrawer` |
| Consulta de exemplo | `EXEMPLO_SQL` |
| Tamanho da janela | `geometry()` em `__init__` |
| Tamanho mínimo | `minsize()` em `__init__` |
| Fonte do editor | `font=("Consolas", 11)` em `_create_widgets` |
| Adicionar nova aba | `_create_widgets` (criar `tab_xxx`, `txt_xxx`) e novo método `_display_xxx` |

## Resumo das responsabilidades

`gui.py` é a única camada que:

- Conhece o Tkinter.
- Conhece o usuário (em sentido humano-interativo).
- Orquestra o pipeline (chama os outros módulos).
- Lida com erros (try/except + diálogos).
- Decide aparência (cores, fontes, layouts).

Os outros módulos são **bibliotecas puras** (sem efeitos colaterais
visíveis), e podem ser usados em outros contextos (CLI, web, testes
automatizados) sem trazer dependência do Tkinter.
