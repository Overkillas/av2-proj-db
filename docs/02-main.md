# 02 — `main.py`

## Propósito

Ponto de entrada do programa. É deliberadamente **mínimo**: a única
responsabilidade dele é instanciar a interface gráfica e iniciar o
event loop do Tkinter.

## Conteúdo (íntegra)

```python
"""
main.py - Ponto de Entrada do Processador de Consultas SQL

Executa a interface gráfica do processador de consultas.

Para executar:
    python main.py
"""

from gui import ProcessadorConsultasGUI


def main():
    app = ProcessadorConsultasGUI()
    app.run()


if __name__ == "__main__":
    main()
```

## Como funciona

1. **Importação**: `from gui import ProcessadorConsultasGUI` traz a classe
   principal da interface gráfica. Esse import dispara, em cascata, os
   imports de **todos** os outros módulos do projeto (porque `gui.py`
   importa `schema`, `sql_parser`, `relational_algebra`, `optimizer`,
   `query_tree` e `execution_plan`). Ou seja: ao executar `main.py`, o
   Python carrega o sistema inteiro antes mesmo de criar a janela.

2. **Função `main()`**:
   - `app = ProcessadorConsultasGUI()` — Construtor da classe da GUI.
     Internamente: cria a `Tk()` raiz, define título/tamanho, monta
     widgets, configura tema e pré-carrega uma consulta de exemplo.
   - `app.run()` — Atalho para `self.root.mainloop()`. Este é o **loop
     bloqueante** do Tkinter; a função só retorna quando o usuário fecha
     a janela.

3. **Guarda `if __name__ == "__main__"`**: padrão do Python para garantir
   que `main()` só é executada quando o arquivo é rodado diretamente
   (`python main.py`) e **não** quando ele é importado por outro módulo.
   Boa prática mesmo num arquivo trivial.

## Por que ele é tão pequeno?

Por desacoplamento. Toda a lógica de interface fica em `gui.py`, e toda
a lógica de domínio fica nos módulos especializados. `main.py` serve
apenas como "porta de entrada", o que torna o código fácil de testar:
você pode importar `gui.ProcessadorConsultasGUI` em outro contexto
(ex.: testes automatizados) sem efeitos colaterais.

## Quando você mexeria neste arquivo

Quase nunca. Você só edita `main.py` se:

- Quiser adicionar um sistema de **CLI** (ex.: rodar uma consulta sem
  GUI via `python main.py --sql "SELECT ..."`).
- Quiser carregar **configurações iniciais** (ex.: arquivo `.ini`)
  antes de criar a GUI.
- Quiser **trocar a GUI inteira** (ex.: substituir Tkinter por PyQt) —
  então só essa import muda aqui.

## Relacionamento com outros arquivos

```
main.py  ──importa──▶  gui.py  ──importa──▶  (todos os outros)
```

Não há relação inversa: nenhum módulo importa `main.py`.
