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
