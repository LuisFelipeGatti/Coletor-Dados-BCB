import re
import sqlite3
from pathlib import Path

import pandas as pd

from banco import CAMINHO_BANCO

ARQUIVO_SQL = Path(__file__).parent / "sql" / "perguntas.sql"


def ler_perguntas(caminho):
    texto = caminho.read_text(encoding="utf-8")
    perguntas = []

    # Divide o texto em cada linha que COMEÇA com "-- PERGUNTA"
    blocos = re.split(r"^-- (?=PERGUNTA)", texto, flags=re.MULTILINE)

    for bloco in blocos[1:]:
        titulo, _, consulta = bloco.partition("\n")
        consulta = consulta.strip().rstrip(";")
        perguntas.append((titulo.strip(), consulta))

    return perguntas


def main():
    if not CAMINHO_BANCO.exists():
        print("Banco não encontrado. Rode primeiro: python main.py")
        return

    pd.set_option("display.width", 200)
    pd.set_option("display.max_rows", 200)

    conexao = sqlite3.connect(CAMINHO_BANCO)
    try:
        for titulo, consulta in ler_perguntas(ARQUIVO_SQL):
            print("\n" + "=" * 80)
            print(titulo)
            print("=" * 80)
            resultado = pd.read_sql_query(consulta, conexao)
            print(resultado.to_string(index=False))
    finally:
        conexao.close()


if __name__ == "__main__":
    main()

