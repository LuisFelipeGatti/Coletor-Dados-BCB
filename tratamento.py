import pandas as pd


def tratar_serie(registros, codigo, nome):

    if not registros:
        print(f"[AVISO] Série {codigo}: nenhum registro para tratar.")
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
    print(f"Série {codigo} ({nome}): {len(df)} registros válidos, {removidos} removidos.")

    return df[["data", "valor", "codigo_serie", "serie"]]


if __name__ == "__main__":
    from datetime import date
    from coleta import SERIES, coletar_serie

    tabelas = []
    for codigo, nome in SERIES.items():
        registros = coletar_serie(codigo, date(2015, 1, 1), date.today())
        tabelas.append(tratar_serie(registros, codigo, nome))

    # Junta as três séries em uma única tabela
    df_final = pd.concat(tabelas, ignore_index=True)

    print("\n=== Primeiras linhas ===")
    print(df_final.head())

    print("\n=== Tipos das colunas ===")
    print(df_final.dtypes)

    print("\n=== Resumo por série ===")
    print(df_final.groupby("serie")["valor"].agg(["count", "min", "max", "mean"]).round(4))



