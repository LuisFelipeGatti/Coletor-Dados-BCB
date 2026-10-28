import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from banco import conectar, criar_tabelas, resumo_banco, salvar_dados, ultima_data
from coleta import SERIES, coletar_serie
from tratamento import tratar_serie

DATA_INICIAL = date(2015, 1, 1)  # início do histórico
MARGEM_DIAS = 60                 # recoleta os últimos 60 dias para pegar revisões
PASTA_LOGS = Path(__file__).parent / "logs"


def configurar_logs():
    """Envia as mensagens para a tela e para o arquivo logs/pipeline.log."""
    PASTA_LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        handlers=[
            logging.FileHandler(PASTA_LOGS / "pipeline.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def definir_inicio(conexao, codigo, completo):
    """Decide a partir de qual data coletar cada série."""
    if completo:
        return DATA_INICIAL

    ultima = ultima_data(conexao, codigo)
    if ultima is None:
        return DATA_INICIAL  # banco vazio para esta série: coleta tudo

    return max(DATA_INICIAL, ultima - timedelta(days=MARGEM_DIAS))


def executar(completo=False):
    logger = logging.getLogger("main")
    modo = "COMPLETO" if completo else "INCREMENTAL"
    logger.info("===== Início do pipeline (modo %s) =====", modo)

    conexao = conectar()
    houve_falha = False

    try:
        criar_tabelas(conexao)
        hoje = date.today()

        for codigo, nome in SERIES.items():
            inicio = definir_inicio(conexao, codigo, completo)
            registros = coletar_serie(codigo, inicio, hoje)
            df = tratar_serie(registros, codigo, nome)

            if df.empty:
                houve_falha = True
                logger.error("Série %s (%s): nenhum dado novo gravado.", codigo, nome)
                continue

            salvar_dados(conexao, df)

        resumo_banco(conexao)

    except Exception:
        houve_falha = True
        logger.exception("Erro inesperado durante o pipeline.")

    finally:
        conexao.close()

    if houve_falha:
        logger.warning("===== Pipeline concluído COM FALHAS (veja as mensagens acima) =====")
    else:
        logger.info("===== Pipeline concluído com sucesso =====")

    return 1 if houve_falha else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coletor de séries do Banco Central.")
    parser.add_argument("--completo", action="store_true",
                        help="recoleta todo o histórico desde 2015")
    argumentos = parser.parse_args()

    configurar_logs()
    sys.exit(executar(completo=argumentos.completo))




