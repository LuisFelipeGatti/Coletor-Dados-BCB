from datetime import date, timedelta
import requests
import logging
import time

logger = logging.getLogger(__name__)

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


def coletar_bloco(codigo, data_inicial, data_final, tentativas=3):
    url = (
        f"{URL_BASE.format(codigo=codigo)}"
        f"?formato=json"
        f"&dataInicial={data_inicial:%d/%m/%Y}"
        f"&dataFinal={data_final:%d/%m/%Y}"
    )

    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, timeout=30)
            resposta.raise_for_status()
            return resposta.json()

        except requests.exceptions.Timeout:
            print(f"[ERRO] Série {codigo}: o servidor demorou demais para responder.")
        except requests.exceptions.HTTPError:
            motivo = f"a API respondeu com status {resposta.status_code}"
            if resposta.status_code < 500:
                logger.error("Série %s: %s.", codigo, motivo)
                return []
        except requests.exceptions.RequestException as erro:
            print(f"[ERRO] Série {codigo}: falha de conexão ({erro}).")
        except ValueError:
            print(f"[ERRO] Série {codigo}: a resposta não veio em formato JSON.")

        if tentativa < tentativas:
            espera = 5 * tentativa  # 5s, depois 10s
            logger.warning("Série %s: %s. Nova tentativa em %ss (%s/%s)...",
                           codigo, motivo, espera, tentativa + 1, tentativas)
            time.sleep(espera)
        else:
            logger.error("Série %s: %s. Desistindo após %s tentativas.",
                         codigo, motivo, tentativas)

    return []


def coletar_serie(codigo, data_inicial, data_final):
    registros = []

    for inicio, fim in dividir_periodo(data_inicial, data_final):
        logger.info("Coletando série %s de %s a %s...",
                    codigo, f"{inicio:%d/%m/%Y}", f"{fim:%d/%m/%Y}")
        registros.extend(coletar_bloco(codigo, inicio, fim))

    logger.info("Série %s: %s registros coletados.", codigo, len(registros))
    return registros



