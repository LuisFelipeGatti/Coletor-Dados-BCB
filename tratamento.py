import pandas as pd
import logging


logger = logging.getLogger(__name__)

def tratar_serie(registros, codigo, nome):

    if not registros:
        logger.warning("Série %s: nenhum registro para tratar.", codigo)
        return pd.DataFrame(columns=["data", "valor", "codigo_serie", "serie"])

    df = pd.DataFrame(registros)
    total_inicial = len(df)

    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    df = df.dropna(subset=["data", "valor"])

    df = df.drop_duplicates(subset="data", keep="last")

    df = df.sort_values("data").reset_index(drop=True)

    df["codigo_serie"] = codigo
    df["serie"] = nome

    removidos = total_inicial - len(df)

    if removidos:
        logger.warning("Série %s (%s): %s registros inválidos removidos.", codigo, nome, removidos)
    logger.info("Série %s (%s): %s registros válidos.", codigo, nome, len(df))

    return df[["data", "valor", "codigo_serie", "serie"]]



