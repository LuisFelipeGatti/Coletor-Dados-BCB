"""Painel interativo das séries do Banco Central.

Lê o banco gerado pelo pipeline (dados/bcb.db) e exibe gráficos e indicadores.

Execute com:
    streamlit run painel.py
"""

import sqlite3
from contextlib import closing
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from banco import CAMINHO_BANCO

st.set_page_config(page_title="Indicadores do Banco Central", page_icon="📈", layout="wide")

COR_DOLAR = "#2E7D32"
COR_SELIC = "#1565C0"
COR_IPCA = "#C62828"
COR_JURO_REAL = "#6A1B9A"


# ---------------------------------------------------------------------------
# Carregamento e cálculos
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def carregar_series():
    consulta = """
        SELECT s.nome AS serie, o.data, o.valor
        FROM observacoes AS o
        JOIN series AS s ON s.codigo = o.codigo_serie
        ORDER BY o.data
    """
    with closing(sqlite3.connect(CAMINHO_BANCO)) as conexao:
        df = pd.read_sql_query(consulta, conexao, parse_dates=["data"])

    return {nome: grupo.set_index("data")["valor"] for nome, grupo in df.groupby("serie")}


def ipca_acumulado_12m(ipca_mensal):
    fatores = 1 + ipca_mensal / 100
    return (fatores.rolling(12).apply(lambda x: x.prod(), raw=True) - 1) * 100


def juro_real(selic_mensal, ipca_12m):
    return ((1 + selic_mensal / 100) / (1 + ipca_12m / 100) - 1) * 100


def recortar(serie, inicio, fim):
    return serie.loc[pd.Timestamp(inicio):pd.Timestamp(fim)]


def br(valor, casas=2):

    if pd.isna(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def estilizar(fig, titulo_y):
    fig.update_layout(
        separators=",.",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.08, x=0),
        yaxis_title=titulo_y,
        xaxis_title=None,
        xaxis_tickformat="%m/%Y",
    )
    return fig


# ---------------------------------------------------------------------------
# Verificação do banco
# ---------------------------------------------------------------------------

if not CAMINHO_BANCO.exists():
    st.error("Banco de dados não encontrado. Rode primeiro: `python main.py`")
    st.stop()

series = carregar_series()
faltando = {"dolar", "selic_meta", "ipca"} - series.keys()
if faltando:
    st.error(f"O banco não tem as séries: {', '.join(sorted(faltando))}. Rode `python main.py`.")
    st.stop()

dolar = series["dolar"]
selic = series["selic_meta"]
ipca = series["ipca"]


selic_mensal = selic.resample("MS").last()
ipca_12m = ipca_acumulado_12m(ipca)
juro = juro_real(selic_mensal, ipca_12m).dropna()

primeira_data = min(s.index.min() for s in series.values()).date()
ultima_data = max(s.index.max() for s in series.values()).date()


# ---------------------------------------------------------------------------
# Barra lateral: filtro de período
# ---------------------------------------------------------------------------

st.sidebar.header("Período")
opcao = st.sidebar.radio(
    "Exibir",
    ["Últimos 12 meses", "Últimos 3 anos", "Últimos 5 anos", "Todo o histórico", "Personalizado"],
    index=2,
)

anos = {"Últimos 12 meses": 1, "Últimos 3 anos": 3, "Últimos 5 anos": 5}
if opcao in anos:
    inicio = max(primeira_data, date(ultima_data.year - anos[opcao], ultima_data.month, 1))
    fim = ultima_data
elif opcao == "Todo o histórico":
    inicio, fim = primeira_data, ultima_data
else:
    escolha = st.sidebar.date_input(
        "Intervalo", value=(primeira_data, ultima_data),
        min_value=primeira_data, max_value=ultima_data, format="DD/MM/YYYY",
    )
    if len(escolha) != 2:
        st.sidebar.info("Selecione a data final.")
        st.stop()
    inicio, fim = escolha

st.sidebar.caption(f"Dados disponíveis de {primeira_data:%d/%m/%Y} a {ultima_data:%d/%m/%Y}.")
st.sidebar.caption("Fonte: Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS).")

dolar_p = recortar(dolar, inicio, fim)
selic_p = recortar(selic, inicio, fim)
ipca_p = recortar(ipca, inicio, fim)
ipca_12m_p = recortar(ipca_12m, inicio, fim).dropna()
juro_p = recortar(juro, inicio, fim)

if dolar_p.empty or selic_p.empty:
    st.warning("Não há dados no período selecionado.")
    st.stop()



st.title("📈 Indicadores do Banco Central")
st.caption(f"Período exibido: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")

col1, col2, col3, col4 = st.columns(4)

variacao_dolar = (dolar_p.iloc[-1] / dolar_p.iloc[0] - 1) * 100
col1.metric(
    f"Dólar ({dolar_p.index[-1]:%d/%m/%Y})",
    f"R$ {br(dolar_p.iloc[-1], 4)}",
    f"{br(variacao_dolar)}% no período",
    delta_color="inverse",  # alta do dólar aparece em vermelho
)

variacao_selic = selic_p.iloc[-1] - selic_p.iloc[0]
col2.metric(
    "Meta Selic",
    f"{br(selic_p.iloc[-1])}% a.a.",
    f"{br(variacao_selic)} p.p. no período",
    delta_color="off",
)

if not ipca_p.empty:
    col3.metric(f"IPCA de {ipca_p.index[-1]:%m/%Y}", f"{br(ipca_p.iloc[-1])}%")
if not ipca_12m_p.empty:
    col4.metric("IPCA acumulado em 12 meses", f"{br(ipca_12m_p.iloc[-1])}%",
                f"juro real: {br(juro_p.iloc[-1])}% a.a." if not juro_p.empty else None,
                delta_color="off")



aba_dolar, aba_selic, aba_ipca, aba_comp, aba_dados = st.tabs(
    ["Dólar", "Selic", "IPCA", "Juro real", "Dados"]
)

# --- Dólar -----------------------------------------------------------------
with aba_dolar:
    media_movel = st.checkbox("Mostrar média móvel de 21 dias úteis (≈ 1 mês)", value=True)

    fig = go.Figure()
    fig.add_scatter(x=dolar_p.index, y=dolar_p, name="Cotação diária",
                    line=dict(color=COR_DOLAR, width=1.5))
    if media_movel:
        mm = dolar.rolling(21).mean()
        mm_p = recortar(mm, inicio, fim)
        fig.add_scatter(x=mm_p.index, y=mm_p, name="Média móvel 21d",
                        line=dict(color="#FB8C00", width=2, dash="dot"))
    st.plotly_chart(estilizar(fig, "R$ por US$"), width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("Máxima no período", f"R$ {br(dolar_p.max(), 4)}")
    c1.caption(f"em {dolar_p.idxmax():%d/%m/%Y}")
    c2.metric("Mínima no período", f"R$ {br(dolar_p.min(), 4)}")
    c2.caption(f"em {dolar_p.idxmin():%d/%m/%Y}")
    c3.metric("Média no período", f"R$ {br(dolar_p.mean(), 4)}")

# --- Selic -----------------------------------------------------------------
with aba_selic:
    fig = px.line(x=selic_p.index, y=selic_p, line_shape="hv",
                  color_discrete_sequence=[COR_SELIC])
    fig.update_traces(name="Meta Selic", hovertemplate="%{y:.2f}% a.a.")
    st.plotly_chart(estilizar(fig, "% ao ano"), width="stretch")

    # Decisões do Copom: datas em que a meta mudou
    mudancas = selic.diff()
    mudancas = recortar(mudancas[mudancas != 0].dropna(), inicio, fim)
    if mudancas.empty:
        st.info("A meta Selic não mudou no período selecionado.")
    else:
        st.subheader(f"Mudanças na meta ({len(mudancas)} no período)")
        tabela = pd.DataFrame({
            "Data": mudancas.index.strftime("%d/%m/%Y"),
            "De (%)": (selic.loc[mudancas.index] - mudancas).map(br),
            "Para (%)": selic.loc[mudancas.index].map(br),
            "Variação (p.p.)": mudancas.map(lambda v: ("+" if v > 0 else "") + br(v)),
            "Tipo": mudancas.map(lambda v: "Alta" if v > 0 else "Corte"),
        }).iloc[::-1]  # mais recentes primeiro
        st.dataframe(tabela, hide_index=True, width="stretch")

# --- IPCA ------------------------------------------------------------------
with aba_ipca:
    if ipca_p.empty:
        st.info("Não há dados de IPCA no período selecionado.")
    else:
        cores = ["#1E88E5" if v < 0 else COR_IPCA for v in ipca_p]
        fig = go.Figure(go.Bar(x=ipca_p.index, y=ipca_p, marker_color=cores,
                               name="IPCA mensal", hovertemplate="%{x|%m/%Y}: %{y:.2f}%<extra></extra>"))
        fig.update_layout(title="Variação mensal (azul = deflação)")
        st.plotly_chart(estilizar(fig, "% no mês"), width="stretch")

        if not ipca_12m_p.empty:
            fig = px.line(x=ipca_12m_p.index, y=ipca_12m_p, color_discrete_sequence=[COR_IPCA])
            fig.update_traces(name="IPCA 12 meses", hovertemplate="%{x|%m/%Y}: %{y:.2f}%")
            fig.update_layout(title="Acumulado em 12 meses")
            st.plotly_chart(estilizar(fig, "% em 12 meses"), width="stretch")

        c1, c2 = st.columns(2)
        c1.metric("Meses com deflação no período", int((ipca_p < 0).sum()))
        c2.metric("Maior alta mensal", f"{br(ipca_p.max())}%")
        c2.caption(f"em {ipca_p.idxmax():%m/%Y}")

# --- Juro real -------------------------------------------------------------
with aba_comp:
    st.markdown(
        "O **juro real** mostra quanto a Selic rende acima da inflação. Aqui ele é calculado "
        "*ex-post*: meta Selic no fim de cada mês deflacionada pelo IPCA acumulado nos 12 meses "
        "anteriores, pela fórmula `(1 + Selic) / (1 + IPCA 12m) − 1`."
    )
    if juro_p.empty:
        st.info("São necessários pelo menos 12 meses de IPCA para calcular o juro real.")
    else:
        fig = go.Figure()
        fig.add_scatter(x=recortar(selic_mensal, inicio, fim).index,
                        y=recortar(selic_mensal, inicio, fim), name="Meta Selic",
                        line=dict(color=COR_SELIC, shape="hv"))
        fig.add_scatter(x=ipca_12m_p.index, y=ipca_12m_p, name="IPCA 12 meses",
                        line=dict(color=COR_IPCA))
        fig.add_scatter(x=juro_p.index, y=juro_p, name="Juro real",
                        line=dict(color=COR_JURO_REAL, width=3), fill="tozeroy",
                        fillcolor="rgba(106, 27, 154, 0.12)")
        fig.add_hline(y=0, line_color="gray", line_width=1)
        fig.update_traces(hovertemplate="%{y:.2f}%")
        st.plotly_chart(estilizar(fig, "%"), width="stretch")

# --- Dados -----------------------------------------------------------------
with aba_dados:
    nome_serie = st.selectbox("Série", ["Dólar", "Meta Selic", "IPCA mensal", "IPCA 12 meses",
                                        "Juro real"])
    escolhida = {
        "Dólar": dolar_p, "Meta Selic": selic_p, "IPCA mensal": ipca_p,
        "IPCA 12 meses": ipca_12m_p, "Juro real": juro_p,
    }[nome_serie]

    tabela = escolhida.rename("valor").reset_index().sort_values("data", ascending=False)
    st.dataframe(
        tabela, hide_index=True, width="stretch",
        column_config={
            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "valor": st.column_config.NumberColumn("Valor", format="%.4f"),
        },
    )
    st.download_button(
        "Baixar CSV",
        tabela.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),  # abre certo no Excel
        file_name=f"{nome_serie.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )

