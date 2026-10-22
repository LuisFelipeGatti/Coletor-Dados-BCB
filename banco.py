import sqlite3
from pathlib import Path


CAMINHO_BANCO = Path(__file__).parent / "dados" / "bcb.db"

def conectar():
    """Abre (ou cria, se não existir) o arquivo do banco SQLite."""
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)  # garante que a pasta exista
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

def criar_tabelas(conexao):
    """Cria as tabelas, caso ainda não existam."""
    conexao.executescript("""
        CREATE TABLE IF NOT EXISTS series (
            codigo  INTEGER PRIMARY KEY,
            nome    TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS observacoes (
            codigo_serie  INTEGER NOT NULL,
            data          TEXT    NOT NULL,   -- formato AAAA-MM-DD
            valor         REAL    NOT NULL,
            PRIMARY KEY (codigo_serie, data),
            FOREIGN KEY (codigo_serie) REFERENCES series (codigo)
        );
    """)

def salvar_dados(conexao, df):

    if df.empty:
        print("[AVISO] Nada para salvar.")
        return 0

    series = df[["codigo_serie", "serie"]].drop_duplicates()
    conexao.executemany(
        "INSERT OR IGNORE INTO series (codigo, nome) VALUES (?, ?)",
        series.itertuples(index=False, name=None),
    )

    linhas = zip(
        df["codigo_serie"].astype(int),
        df["data"].dt.strftime("%Y-%m-%d"),
        df["valor"].astype(float),
    )
    conexao.executemany(
        """
        INSERT INTO observacoes (codigo_serie, data, valor)
        VALUES (?, ?, ?)
        ON CONFLICT (codigo_serie, data) DO UPDATE SET valor = excluded.valor
        """,
        linhas,
    )

    conexao.commit()  # confirma a gravação
    print(f"{len(df)} registros gravados/atualizados em {CAMINHO_BANCO.name}.")
    return len(df)


def resumo_banco(conexao):
    consulta = """
        SELECT s.nome, COUNT(*) AS registros, MIN(o.data) AS primeira, MAX(o.data) AS ultima
        FROM observacoes AS o
        JOIN series AS s ON s.codigo = o.codigo_serie
        GROUP BY s.nome
        ORDER BY s.nome
    """
    print("\n=== Conteúdo do banco ===")
    for nome, registros, primeira, ultima in conexao.execute(consulta):
        print(f"{nome:<12} {registros:>6} registros  ({primeira} a {ultima})")


if __name__ == "__main__":
    from datetime import date
    import pandas as pd
    from coleta import SERIES, coletar_serie
    from tratamento import tratar_serie

    tabelas = []

    for codigo, nome in SERIES.items():
        registros = coletar_serie(codigo, date(2015, 1, 1), date.today())
        tabelas.append(tratar_serie(registros, codigo, nome))
    df_final = pd.concat(tabelas, ignore_index=True)

    conexao = conectar()

    try:
        criar_tabelas(conexao)
        salvar_dados(conexao, df_final)
        resumo_banco(conexao)
    finally:
        conexao.close()

