"""
gui.py - Interface Gráfica do Processador de Consultas SQL

Construída com Tkinter (nativo do Python, sem dependências externas).

Layout:
  +-----------------------------------------------------------+
  |  PROCESSADOR DE CONSULTAS SQL                             |
  +-----------------------------------------------------------+
  |  [ Campo de entrada SQL (Text multilinha) ]               |
  |  [ Botão: Processar Consulta ]  [ Botão: Limpar ]        |
  +-----------------------------------------------------------+
  |  Abas:                                                    |
  |  [ Álgebra Relacional | Otimização | Grafo | Plano Exec ] |
  |                                                           |
  |  Conteúdo da aba selecionada                              |
  +-----------------------------------------------------------+
  |  Barra de status (erros / mensagens)                      |
  +-----------------------------------------------------------+
"""

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


# ---------------------------------------------------------------------------
# Paleta de cores do tema (azul-escuro moderno)
# ---------------------------------------------------------------------------

THEME = {
    "bg":            "#1E293B",   # fundo principal (slate-800)
    "bg_panel":      "#273548",   # painel interno
    "bg_input":      "#0F172A",   # fundo do editor de SQL (slate-900)
    "bg_output":     "#F8FAFC",   # fundo das áreas de resultado
    "fg":            "#E2E8F0",   # texto principal claro
    "fg_muted":      "#94A3B8",   # texto secundário
    "fg_dark":       "#1E293B",   # texto escuro (sobre fundo claro)
    "accent":        "#38BDF8",   # ciano/azul primário
    "accent_hover":  "#0EA5E9",
    "accent_dark":   "#0369A1",
    "danger":        "#EF4444",
    "success":       "#22C55E",
    "warning":       "#F59E0B",
    "border":        "#334155",
    "canvas_bg":     "#FAFAFA",
}

# Cores para os nós da árvore no Canvas
NODE_COLORS = {
    NodeType.TABLE: "#FEF3C7",       # amarelo pastel
    NodeType.SELECTION: "#DBEAFE",   # azul pastel
    NodeType.PROJECTION: "#DCFCE7",  # verde pastel
    NodeType.JOIN: "#FEE2E2",        # rosa/salmão pastel
}

NODE_BORDER_COLORS = {
    NodeType.TABLE: "#D97706",
    NodeType.SELECTION: "#2563EB",
    NodeType.PROJECTION: "#16A34A",
    NodeType.JOIN: "#DC2626",
}


class TreeDrawer:
    """
    Desenha a árvore de operadores em um Canvas Tkinter.

    Algoritmo de layout:
    - Folhas recebem posições x sequenciais (0, 1, 2, ...)
    - Nós internos recebem x = média dos filhos
    - y é baseado na profundidade do nó
    """

    H_SPACING = 200     # espaçamento horizontal entre folhas (pixels)
    V_SPACING = 90      # espaçamento vertical entre níveis
    NODE_PADX = 14      # padding horizontal do texto no nó
    NODE_PADY = 8       # padding vertical do texto no nó
    MARGIN = 60         # margem ao redor da árvore

    def __init__(self, canvas: tk.Canvas, root_node: TreeNode):
        self.canvas = canvas
        self.root = root_node
        self.positions: dict[int, tuple[float, float]] = {}
        self._leaf_counter = 0

    def draw(self):
        """Calcula o layout e desenha a árvore no Canvas."""
        self.canvas.delete("all")
        self.positions = {}
        self._leaf_counter = 0

        if self.root is None:
            return

        # 1) Calcular posições lógicas (grid)
        self._calculate_layout(self.root, depth=0)

        # 2) Converter para coordenadas de pixel
        pixel_positions = {}
        for nid, (gx, gy) in self.positions.items():
            px = gx * self.H_SPACING + self.MARGIN
            py = gy * self.V_SPACING + self.MARGIN
            pixel_positions[nid] = (px, py)
        self.positions = pixel_positions

        # 3) Desenhar arestas (linhas)
        self._draw_edges(self.root)

        # 4) Desenhar nós (retângulos com texto)
        self._draw_nodes(self.root)

        # 5) Ajustar scroll region
        all_x = [p[0] for p in self.positions.values()]
        all_y = [p[1] for p in self.positions.values()]
        if all_x and all_y:
            self.canvas.configure(scrollregion=(
                0, 0,
                max(all_x) + self.H_SPACING + self.MARGIN,
                max(all_y) + self.V_SPACING + self.MARGIN,
            ))

    def _calculate_layout(self, node: TreeNode, depth: int):
        """Layout recursivo: folhas sequenciais, internos = média dos filhos."""
        if not node.children:
            self.positions[id(node)] = (self._leaf_counter, depth)
            self._leaf_counter += 1
            return

        for child in node.children:
            self._calculate_layout(child, depth + 1)

        children_x = [self.positions[id(c)][0] for c in node.children]
        avg_x = sum(children_x) / len(children_x)
        self.positions[id(node)] = (avg_x, depth)

    def _draw_edges(self, node: TreeNode):
        """Desenha linhas do nó pai para cada filho."""
        if id(node) not in self.positions:
            return
        px, py = self.positions[id(node)]

        for child in node.children:
            if id(child) in self.positions:
                cx, cy = self.positions[id(child)]
                self.canvas.create_line(
                    px, py + 20, cx, cy - 20,
                    fill="#555555", width=2, arrow=tk.LAST,
                )
            self._draw_edges(child)

    def _draw_nodes(self, node: TreeNode):
        """Desenha um nó como retângulo arredondado com texto."""
        if id(node) not in self.positions:
            return
        x, y = self.positions[id(node)]

        label = node.label
        fill_color = NODE_COLORS.get(node.node_type, "#FFFFFF")
        border_color = NODE_BORDER_COLORS.get(node.node_type, "#000000")

        # Calcular tamanho do texto
        text_id = self.canvas.create_text(x, y, text=label, anchor="center",
                                          font=("Consolas", 9))
        bbox = self.canvas.bbox(text_id)
        self.canvas.delete(text_id)

        if bbox:
            tx1, ty1, tx2, ty2 = bbox
            w = (tx2 - tx1) / 2 + self.NODE_PADX
            h = (ty2 - ty1) / 2 + self.NODE_PADY
        else:
            w, h = 60, 18

        # Retângulo arredondado (simulado com oval + retângulo)
        x1, y1 = x - w, y - h
        x2, y2 = x + w, y + h
        r = 8  # raio de arredondamento

        # Desenhar retângulo arredondado usando polígono
        self.canvas.create_polygon(
            x1 + r, y1,  x2 - r, y1,
            x2, y1,  x2, y1 + r,
            x2, y2 - r,  x2, y2,
            x2 - r, y2,  x1 + r, y2,
            x1, y2,  x1, y2 - r,
            x1, y1 + r,  x1, y1,
            fill=fill_color, outline=border_color, width=2, smooth=True,
        )

        # Texto do nó
        self.canvas.create_text(
            x, y, text=label, anchor="center",
            font=("Consolas", 9), fill="#222222",
        )

        # Recursão para filhos
        for child in node.children:
            self._draw_nodes(child)


# ---------------------------------------------------------------------------
# Interface Gráfica Principal
# ---------------------------------------------------------------------------

class ProcessadorConsultasGUI:
    """Interface gráfica principal do Processador de Consultas SQL."""

    # Consulta de exemplo pré-carregada
    EXEMPLO_SQL = (
        "SELECT cliente.Nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido\n"
        "FROM Cliente\n"
        "JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente\n"
        "WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0"
    )

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Processador de Consultas SQL")
        self.root.geometry("1200x850")
        self.root.minsize(960, 680)
        self.root.configure(bg=THEME["bg"])

        self._configure_style()
        self._create_widgets()

    # -------------------------------------------------------------------
    # Estilo / Tema
    # -------------------------------------------------------------------

    def _configure_style(self):
        """Configura o estilo ttk do aplicativo (tema moderno escuro)."""
        style = ttk.Style()
        style.theme_use("clam")

        bg = THEME["bg"]
        bg_panel = THEME["bg_panel"]
        fg = THEME["fg"]
        fg_muted = THEME["fg_muted"]
        accent = THEME["accent"]
        accent_hover = THEME["accent_hover"]
        accent_dark = THEME["accent_dark"]
        border = THEME["border"]

        # Frames e labels base
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=bg_panel)
        style.configure("TLabel", background=bg, foreground=fg,
                        font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=bg, foreground=fg_muted,
                        font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=bg, foreground=fg,
                        font=("Segoe UI Semibold", 18))
        style.configure("Subheader.TLabel", background=bg, foreground=fg_muted,
                        font=("Segoe UI", 10))

        # LabelFrame
        style.configure("Card.TLabelframe", background=bg_panel,
                        foreground=fg, bordercolor=border, borderwidth=1,
                        relief="solid")
        style.configure("Card.TLabelframe.Label", background=bg_panel,
                        foreground=accent, font=("Segoe UI Semibold", 10))

        # Botão primário
        style.configure("Primary.TButton",
                        background=accent, foreground=THEME["fg_dark"],
                        font=("Segoe UI Semibold", 10),
                        padding=(16, 8), borderwidth=0, focusthickness=0)
        style.map("Primary.TButton",
                  background=[("active", accent_hover), ("pressed", accent_dark)],
                  foreground=[("active", THEME["fg_dark"])])

        # Botão secundário
        style.configure("Secondary.TButton",
                        background=bg_panel, foreground=fg,
                        font=("Segoe UI", 10),
                        padding=(14, 8), borderwidth=1,
                        bordercolor=border, focusthickness=0)
        style.map("Secondary.TButton",
                  background=[("active", border)],
                  foreground=[("active", fg)])

        # Notebook (abas)
        style.configure("TNotebook", background=bg, borderwidth=0,
                        tabmargins=(2, 4, 2, 0))
        style.configure("TNotebook.Tab",
                        background=bg_panel, foreground=fg_muted,
                        padding=(18, 8), font=("Segoe UI", 10),
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", accent), ("active", border)],
                  foreground=[("selected", THEME["fg_dark"]),
                              ("active", fg)])

        # Barra de status
        style.configure("Status.TLabel", background=bg_panel, foreground=fg,
                        font=("Segoe UI", 9), padding=(12, 6))
        style.configure("StatusError.TLabel", background=bg_panel,
                        foreground=THEME["danger"], font=("Segoe UI Semibold", 9),
                        padding=(12, 6))
        style.configure("StatusOK.TLabel", background=bg_panel,
                        foreground=THEME["success"], font=("Segoe UI Semibold", 9),
                        padding=(12, 6))

        # Scrollbar
        style.configure("Vertical.TScrollbar",
                        background=bg_panel, troughcolor=bg,
                        bordercolor=bg, arrowcolor=fg_muted)
        style.configure("Horizontal.TScrollbar",
                        background=bg_panel, troughcolor=bg,
                        bordercolor=bg, arrowcolor=fg_muted)

    def _create_widgets(self):
        """Cria todos os widgets da interface."""

        # ====== Cabeçalho ======
        header = ttk.Frame(self.root, style="TFrame")
        header.pack(fill=tk.X, padx=20, pady=(18, 4))

        ttk.Label(
            header,
            text="⚙  Processador de Consultas SQL",
            style="Header.TLabel",
        ).pack(side=tk.LEFT)

        ttk.Label(
            header,
            text="SQL → Álgebra Relacional → Otimização → Plano de Execução",
            style="Subheader.TLabel",
        ).pack(side=tk.RIGHT, pady=(6, 0))

        # Linha divisória
        sep = tk.Frame(self.root, bg=THEME["border"], height=1)
        sep.pack(fill=tk.X, padx=20, pady=(0, 12))

        # ====== Frame Superior: Entrada SQL ======
        input_frame = ttk.LabelFrame(
            self.root, text="  Consulta SQL  ",
            style="Card.TLabelframe", padding=14,
        )
        input_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # Editor de SQL (visual de "code editor")
        editor_wrapper = tk.Frame(input_frame, bg=THEME["border"], bd=0)
        editor_wrapper.pack(fill=tk.X, pady=(0, 12))

        self.sql_input = scrolledtext.ScrolledText(
            editor_wrapper, height=7, font=("Consolas", 11),
            wrap=tk.WORD,
            bg=THEME["bg_input"], fg="#E2E8F0",
            insertbackground=THEME["accent"],
            selectbackground=THEME["accent_dark"],
            selectforeground="#FFFFFF",
            relief=tk.FLAT, padx=12, pady=10,
            borderwidth=0,
        )
        self.sql_input.pack(fill=tk.X, padx=1, pady=1)
        self.sql_input.insert("1.0", self.EXEMPLO_SQL)

        # Aplicar syntax highlighting simples
        self._setup_sql_highlighting()
        self._highlight_sql()
        self.sql_input.bind("<KeyRelease>", lambda e: self._highlight_sql())

        # Frame de botões + info
        btn_frame = ttk.Frame(input_frame, style="Panel.TFrame")
        btn_frame.pack(fill=tk.X)

        self.btn_process = ttk.Button(
            btn_frame, text="▶  Processar Consulta",
            style="Primary.TButton",
            command=self._on_process,
        )
        self.btn_process.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_example = ttk.Button(
            btn_frame, text="Carregar Exemplo",
            style="Secondary.TButton",
            command=self._on_example,
        )
        self.btn_example.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = ttk.Button(
            btn_frame, text="Limpar",
            style="Secondary.TButton",
            command=self._on_clear,
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 8))

        # Label com tabelas/operadores suportados (lado direito)
        info_frame = ttk.Frame(btn_frame, style="Panel.TFrame")
        info_frame.pack(side=tk.RIGHT)

        tables_str = ", ".join(sorted(SCHEMA.keys()))
        tk.Label(
            info_frame,
            text=f"Operadores: =  >  <  <=  >=  <>  AND  ( )",
            bg=THEME["bg_panel"], fg=THEME["accent"],
            font=("Consolas", 9),
        ).pack(anchor="e")
        tk.Label(
            info_frame,
            text=f"Tabelas: {tables_str}",
            bg=THEME["bg_panel"], fg=THEME["fg_muted"],
            font=("Segoe UI", 8), wraplength=560, justify="right",
        ).pack(anchor="e", pady=(2, 0))

        # ====== Frame Inferior: Resultados (Notebook com abas) ======
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 6))

        # Aba 1: Álgebra Relacional
        self.tab_algebra = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_algebra, text="  📐  Álgebra Relacional  ")
        self.txt_algebra = self._make_output_text(self.tab_algebra)

        # Aba 2: Otimização
        self.tab_optim = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_optim, text="  ⚡  Otimização  ")
        self.txt_optim = self._make_output_text(self.tab_optim)

        # Aba 3: Grafo de Operadores
        self.tab_graph = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_graph, text="  🌳  Grafo de Operadores  ")

        # Canvas com scrollbars para o grafo
        graph_container = ttk.Frame(self.tab_graph, style="TFrame")
        graph_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.canvas = tk.Canvas(
            graph_container, bg=THEME["canvas_bg"],
            highlightthickness=1, highlightbackground=THEME["border"],
        )
        scrollbar_x = ttk.Scrollbar(graph_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        scrollbar_y = ttk.Scrollbar(graph_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Aba 4: Plano de Execução
        self.tab_plan = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_plan, text="  📋  Plano de Execução  ")
        self.txt_plan = self._make_output_text(self.tab_plan)

        # Aba 5: Árvore Texto
        self.tab_tree_text = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_tree_text, text="  🧾  Árvore (Texto)  ")
        self.txt_tree = self._make_output_text(self.tab_tree_text, wrap=tk.NONE)

        # ====== Barra de Status ======
        status_wrap = tk.Frame(self.root, bg=THEME["bg_panel"])
        status_wrap.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Frame(status_wrap, bg=THEME["border"], height=1).pack(fill=tk.X)

        self.status_var = tk.StringVar(
            value="Pronto. Digite uma consulta SQL e clique em ‘Processar Consulta’."
        )
        self.status_label = ttk.Label(
            status_wrap, textvariable=self.status_var,
            style="Status.TLabel", anchor=tk.W,
        )
        self.status_label.pack(fill=tk.X)

    # -------------------------------------------------------------------
    # Helpers de construção
    # -------------------------------------------------------------------

    def _make_output_text(self, parent, wrap=tk.WORD) -> scrolledtext.ScrolledText:
        """Cria um widget de texto de resultado com estilo padrão."""
        widget = scrolledtext.ScrolledText(
            parent, font=("Consolas", 11), wrap=wrap,
            state=tk.DISABLED,
            bg=THEME["bg_output"], fg=THEME["fg_dark"],
            insertbackground=THEME["accent"],
            selectbackground="#BAE6FD",
            selectforeground=THEME["fg_dark"],
            relief=tk.FLAT, padx=14, pady=12,
            borderwidth=0,
        )
        widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        return widget

    # -------------------------------------------------------------------
    # Syntax highlighting (leve) do editor SQL
    # -------------------------------------------------------------------

    _SQL_KEYWORDS = ("SELECT", "FROM", "WHERE", "JOIN", "ON", "AND")

    def _setup_sql_highlighting(self):
        self.sql_input.tag_configure(
            "kw", foreground="#38BDF8", font=("Consolas", 11, "bold")
        )
        self.sql_input.tag_configure("str", foreground="#FCD34D")
        self.sql_input.tag_configure("num", foreground="#A78BFA")
        self.sql_input.tag_configure("op", foreground="#F472B6")

    def _highlight_sql(self):
        import re
        text = self.sql_input.get("1.0", tk.END)

        for tag in ("kw", "str", "num", "op"):
            self.sql_input.tag_remove(tag, "1.0", tk.END)

        # Palavras-chave
        for kw in self._SQL_KEYWORDS:
            for m in re.finditer(rf"\b{kw}\b", text, re.IGNORECASE):
                start = f"1.0 + {m.start()} chars"
                end = f"1.0 + {m.end()} chars"
                self.sql_input.tag_add("kw", start, end)

        # Strings
        for m in re.finditer(r"'[^']*'", text):
            self.sql_input.tag_add(
                "str", f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars"
            )

        # Números
        for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
            self.sql_input.tag_add(
                "num", f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars"
            )

        # Operadores
        for m in re.finditer(r"<=|>=|<>|[=<>]", text):
            self.sql_input.tag_add(
                "op", f"1.0 + {m.start()} chars", f"1.0 + {m.end()} chars"
            )

    # -------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------

    def _on_process(self):
        """
        Callback do botão 'Processar Consulta'.
        Executa o pipeline completo: Parse -> AR -> Otimização -> Grafo -> Plano
        """
        sql = self.sql_input.get("1.0", tk.END).strip()
        if not sql:
            self._set_status("Erro: consulta SQL vazia.", kind="error")
            return

        try:
            # 1) PARSING E VALIDAÇÃO
            parser = SQLParser()
            parsed = parser.parse(sql)

            # 2) CONVERSÃO PARA ÁLGEBRA RELACIONAL
            converter = RelationalAlgebraConverter(parsed)
            algebra_expr = converter.convert()
            self._display_algebra(algebra_expr, parsed)

            # 3) OTIMIZAÇÃO
            optimizer = QueryOptimizer(parsed)
            steps = optimizer.optimize()
            self._display_optimization(algebra_expr, steps)

            # 4) CONSTRUÇÃO DA ÁRVORE
            tree = QueryTree(parsed, optimizer)
            root_node = tree.build()
            self._display_tree(tree, root_node)

            # 5) PLANO DE EXECUÇÃO
            planner = ExecutionPlanGenerator(tree)
            plan_steps = planner.generate()
            plan_text = planner.format_plan()
            self._display_plan(plan_text)

            self._set_status("✓ Processamento concluído com sucesso.", kind="ok")
            self.notebook.select(0)  # Ir para primeira aba

        except UnknownTableError as e:
            # Erro específico de tabela inexistente
            self._set_status(
                f"✗ Tabela inexistente: '{e.table_name}'.", kind="error",
            )
            self._clear_results()
            body = (
                f"❌ TABELA NÃO ENCONTRADA\n\n"
                f"A tabela \"{e.table_name}\" não existe no schema.\n\n"
                f"Tabelas disponíveis:\n"
                f"  • " + "\n  • ".join(sorted(e.available_tables))
            )
            self._set_text(self.txt_algebra, body)
            messagebox.showerror("Tabela inexistente", str(e))

        except InvalidOperatorError as e:
            self._set_status("✗ Operador ou palavra-chave inválida.", kind="error")
            self._clear_results()
            body = (
                f"❌ OPERADOR / PALAVRA-CHAVE INVÁLIDA\n\n"
                f"{str(e)}\n\n"
                f"Símbolos suportados: =, >, <, <=, >=, <>, AND, ( )"
            )
            self._set_text(self.txt_algebra, body)
            messagebox.showerror("Operador inválido", str(e))

        except SQLValidationError as e:
            self._set_status("✗ Erro de validação.", kind="error")
            self._clear_results()
            self._set_text(self.txt_algebra, f"❌ ERRO DE VALIDAÇÃO\n\n{str(e)}")
            messagebox.showerror("Erro de Validação", str(e))

        except ValueError as e:
            self._set_status("✗ Erro de validação.", kind="error")
            self._clear_results()
            self._set_text(self.txt_algebra, f"❌ ERRO DE VALIDAÇÃO\n\n{str(e)}")
            messagebox.showerror("Erro de Validação", str(e))

        except Exception as e:
            self._set_status(f"✗ Erro inesperado: {type(e).__name__}", kind="error")
            self._clear_results()
            self._set_text(
                self.txt_algebra,
                f"❌ ERRO INESPERADO\n\n{type(e).__name__}: {str(e)}",
            )
            messagebox.showerror("Erro", f"{type(e).__name__}: {str(e)}")

    def _set_status(self, text: str, kind: str = "info"):
        """Atualiza o status bar com estilo conforme o tipo (info/ok/error)."""
        self.status_var.set(text)
        style_map = {
            "ok": "StatusOK.TLabel",
            "error": "StatusError.TLabel",
            "info": "Status.TLabel",
        }
        self.status_label.configure(style=style_map.get(kind, "Status.TLabel"))

    def _on_clear(self):
        """Limpa a entrada e os resultados."""
        self.sql_input.delete("1.0", tk.END)
        self._clear_results()
        self._highlight_sql()
        self._set_status("Pronto.", kind="info")

    def _on_example(self):
        """Carrega a consulta de exemplo."""
        self.sql_input.delete("1.0", tk.END)
        self.sql_input.insert("1.0", self.EXEMPLO_SQL)
        self._highlight_sql()
        self._set_status(
            "Exemplo carregado. Clique em ‘Processar Consulta’.", kind="info",
        )

    # -------------------------------------------------------------------
    # Exibição de resultados
    # -------------------------------------------------------------------

    # -------------------------------------------------------------------
    # Helpers de formatação
    # -------------------------------------------------------------------

    _BOX_WIDTH = 68

    def _box_header(self, title: str) -> list[str]:
        w = self._BOX_WIDTH
        inner = w - 2
        top = "╔" + "═" * inner + "╗"
        mid = "║" + title.center(inner) + "║"
        bot = "╚" + "═" * inner + "╝"
        return [top, mid, bot]

    def _section(self, title: str) -> list[str]:
        line = "─" * self._BOX_WIDTH
        return ["", line, f"  ▸ {title}", line]

    # -------------------------------------------------------------------
    # Exibição de resultados
    # -------------------------------------------------------------------

    def _display_algebra(self, expression: str, parsed: ParsedQuery):
        """Exibe a álgebra relacional na aba correspondente."""
        text = []
        text += self._box_header("CONVERSÃO SQL  →  ÁLGEBRA RELACIONAL")

        text += self._section("SQL Original")
        for line in parsed.original_sql.splitlines():
            text.append(f"    {line}")

        text += self._section("Álgebra Relacional (conversão direta)")
        text.append("")
        text.append(f"    {expression}")
        text.append("")

        text += self._section("Resumo do parsing")
        text.append(f"    Tabelas envolvidas : {', '.join(parsed.all_tables_original.values())}")
        text.append(f"    Número de JOINs    : {len(parsed.joins)}")
        text.append(f"    Condições WHERE    : {len(parsed.where_conditions)}")
        text.append(f"    Colunas SELECT     : {len(parsed.select_columns)}")

        self._set_text(self.txt_algebra, "\n".join(text))

    def _display_optimization(self, original_expr: str, steps: list):
        """Exibe os passos de otimização na aba correspondente."""
        text = []
        text += self._box_header("OTIMIZAÇÃO DA CONSULTA")

        text += self._section("Expressão original (antes da otimização)")
        text.append("")
        text.append(f"    {original_expr}")

        for i, step in enumerate(steps, 1):
            text += self._section(f"PASSO {i} — {step.name}")
            text.append("")
            text.append(f"    {step.description}")
            text.append("")
            text.append("    Resultado:")
            text.append(f"    {step.expression}")

        text.append("")
        text.append("─" * self._BOX_WIDTH)

        self._set_text(self.txt_optim, "\n".join(text))

    def _display_tree(self, tree: QueryTree, root_node: TreeNode):
        """Exibe o grafo de operadores (Canvas visual + texto)."""
        # Desenhar no Canvas
        drawer = TreeDrawer(self.canvas, root_node)
        drawer.draw()

        # Exibir representação textual na aba de texto
        tree_text = []
        tree_text += self._box_header("ÁRVORE DE OPERADORES (GRAFO OTIMIZADO)")

        tree_text += self._section("Legenda")
        tree_text.append("    Tabela    →  nó folha (tabela base)")
        tree_text.append("    σ (sigma) →  seleção (filtro de tuplas)")
        tree_text.append("    π (pi)    →  projeção (filtro de colunas)")
        tree_text.append("    ⋈ (join)  →  junção")

        tree_text += self._section("Árvore")
        tree_text.append("")
        tree_text.append(tree.to_text())

        self._set_text(self.txt_tree, "\n".join(tree_text))

    def _display_plan(self, plan_text: str):
        """Exibe o plano de execução na aba correspondente."""
        self._set_text(self.txt_plan, plan_text)

    # -------------------------------------------------------------------
    # Utilitários
    # -------------------------------------------------------------------

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        """Define o texto de um widget ScrolledText (que está desabilitado)."""
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def _clear_results(self):
        """Limpa todas as abas de resultado."""
        for widget in (self.txt_algebra, self.txt_optim, self.txt_plan, self.txt_tree):
            self._set_text(widget, "")
        self.canvas.delete("all")

    def run(self):
        """Inicia o loop principal da interface gráfica."""
        self.root.mainloop()
