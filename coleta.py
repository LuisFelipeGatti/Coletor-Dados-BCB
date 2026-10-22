from datetime import date, timedelta
import requests

SERIES = {
    1: "dolar",
    432: "selic_meta",
    433: "ipca",
}

URL_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

def dividir_periodo(data_inicial, data_final, anos_por_bloco=5):
    blocos = []
    inicio = data_inicial

    while inicio <= data_final:
        fim = date(inicio.year + anos_por_bloco, 1, 1) - timedelta(days=1)
        fim = min(fim, data_final)
        blocos.append((inicio, fim))
        inicio = fim + timedelta(days=1)

    return blocos


def coletar_bloco(codigo, data_inicial, data_final):
    """Faz UMA requisição à API para um período de até 10 anos."""
    url = (
        f"{URL_BASE.format(codigo=codigo)}"
        f"?formato=json"
        f"&dataInicial={data_inicial:%d/%m/%Y}"
        f"&dataFinal={data_final:%d/%m/%Y}"
    )

    try:
        resposta = requests.get(url, timeout=30)
        resposta.raise_for_status()  # gera erro se o status não for 2xx
        return resposta.json()

    except requests.exceptions.Timeout:
        print(f"[ERRO] Série {codigo}: o servidor demorou demais para responder.")
    except requests.exceptions.HTTPError:
        print(f"[ERRO] Série {codigo}: a API respondeu com status {resposta.status_code}.")
    except requests.exceptions.RequestException as erro:
        print(f"[ERRO] Série {codigo}: falha de conexão ({erro}).")
    except ValueError:
        print(f"[ERRO] Série {codigo}: a resposta não veio em formato JSON.")

    return []  # em caso de erro, devolve lista vazia para o programa não parar


def coletar_serie(codigo, data_inicial, data_final):
    """Coleta uma série inteira, dividindo o período em blocos se necessário."""
    registros = []

    for inicio, fim in dividir_periodo(data_inicial, data_final):
        print(f"Coletando série {codigo} de {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}...")
        registros.extend(coletar_bloco(codigo, inicio, fim))

    print(f"Série {codigo}: {len(registros)} registros coletados.\n")
    return registros


if __name__ == "__main__":
    inicio = date(2015, 1, 1)
    fim = date.today()

    for codigo, nome in SERIES.items():
        dados = coletar_serie(codigo, inicio, fim)
        if dados:
            print(f"  {nome} - primeiro registro: {dados[0]}")
            print(f"  {nome} - último registro:   {dados[-1]}\n")

