import sqlite3
from pathlib import Path
import logging
from datetime import date


logger = logging.getLogger(__name__)

CAMINHO_BANCO = Path(__file__).parent / "dados" / "bcb.db"

def conectar():
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
        logger.warning("Nada para salvar.")
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
    logger.info("%s registros gravados/atualizados em %s.", len(df), CAMINHO_BANCO.name)
    return len(df)


def ultima_data(conexao, codigo):
    """Devolve a data mais recente gravada para a série, ou None se não houver."""
    resultado = conexao.execute(
        "SELECT MAX(data) FROM observacoes WHERE codigo_serie = ?", (codigo,)
    ).fetchone()[0]
    return date.fromisoformat(resultado) if resultado else None


def resumo_banco(conexao):
    consulta = """
        SELECT s.nome, COUNT(*) AS registros, MIN(o.data) AS primeira, MAX(o.data) AS ultima
        FROM observacoes AS o
        JOIN series AS s ON s.codigo = o.codigo_serie
        GROUP BY s.nome
        ORDER BY s.nome
    """
    logger.info("=== Conteúdo do banco ===")
    for nome, registros, primeira, ultima in conexao.execute(consulta):
        logger.info("%-12s %6s registros  (%s a %s)", nome, registros, primeira, ultima)




