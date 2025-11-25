import streamlit as st
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from datetime import date

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="SIPREV - Art Velas", page_icon="🕯️", layout="wide")

# --- CABEÇALHO COM LOGO E TÍTULO ---
col_logo, col_titulo = st.columns([1, 5])

with col_logo:
    try:
        st.image("logo.png", width=120)
    except:
        st.header("🕯️")

with col_titulo:
    st.title("SIPREV - Art Velas")
    st.markdown("**SAD - Planejamento de Produção e Compras**")
    st.caption("Tecnologia: Python | Holt-Winters | Simulação de Cenários")

st.markdown("---")

# --- 2. DADOS ---
@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv("dados_vendas.csv")
        df['Data'] = pd.to_datetime(df['Data'])
        return df
    except FileNotFoundError:
        st.error("❌ Rode o script 'unificar_dados.py' primeiro.")
        return pd.DataFrame()


df_raw = carregar_dados()
if df_raw.empty: st.stop()


# --- 3. PESOS ---
def estimar_peso(nome_produto):
    nome = nome_produto.upper()
    tabela_pesos = {
        "2X5": 0.05, "3X5": 0.071, "5X5": 0.091, "7X5": 0.128, "10X5": 0.184, "15X5": 0.261,
        "2X7": 0.07, "10X7": 0.329, "15X7": 0.5, "20X7": 0.664, "25X7": 0.822, "30X7": 0.987,
        "35X7": 1.167, "40X7": 1.31,
        "2X8": 0.094, "10X8": 0.422, "15X8": 0.614, "20X8": 0.812, "25X8": 1.024, "30X8": 1.207,
        "35X8": 1.431, "40X8": 1.619,
        "BATISMO": 0.04, "CRISMA": 0.04, "COMUNHÃO": 0.04, "SACRAMENTO": 0.04,
        "10X2,7": 0.057, "15X2,7": 0.089, "20X2,7": 0.117, "25X2,7": 0.145, "30X2,7": 0.168,
        "35X2,7": 0.198, "40X2,7": 0.224,
        "20X3,5": 0.173, "25X3,5": 0.216, "30X3,5": 0.259, "35X3,5": 0.3, "40X3,5": 0.338,
        "NÚMERO 3": 0.148, "NÚMERO 5": 0.168, "NÚMERO 6": 0.2, "NÚMERO 8": 0.248,
        "PALITO": 0.48, "LITÚRGICA": 1.7, "LIBRA": 0.85,
        "CORAÇÃO P": 0.101, "CORAÇÃO G": 0.029, "RECHAUD": 0.05
    }
    for chave, peso in tabela_pesos.items():
        if chave in nome: return peso
    if "VOTIVA" in nome or "7 DIAS" in nome: return 0.35
    return 0.3


# --- 4. INTERFACE ---
st.sidebar.header("⚙️ Parâmetros")
lista_produtos = sorted(df_raw['Produto'].unique())
produto_selecionado = st.sidebar.selectbox("Produto:", lista_produtos)
peso_unitario = estimar_peso(produto_selecionado)
st.sidebar.markdown(f"**Peso Unitário:** {peso_unitario:.3f} Kg")
st.sidebar.markdown("---")

# --- SIMULAÇÃO DE CENÁRIOS (A VOLTA DA INTERATIVIDADE) ---
st.sidebar.subheader("🕹️ Simulação de Cenários")
ajuste_manual = st.sidebar.slider(
    "Ajuste de Expectativa (%)",
    min_value=-50,
    max_value=50,
    value=0,
    help="Use para simular cenários (ex: +20% para promoção, -10% para crise)."
)

st.sidebar.markdown("---")
estoque_atual = st.sidebar.number_input("Estoque Acabado (Un):", min_value=0, value=100)
estoque_parafina = st.sidebar.number_input("Estoque Parafina (Kg):", min_value=0.0, value=500.0)

# --- 5. PROCESSAMENTO ---
df_prod = df_raw[df_raw['Produto'] == produto_selecionado].copy()
if df_prod.empty:
    st.warning("Sem dados.")
    st.stop()

df_prod = df_prod.set_index('Data').resample('MS').sum(numeric_only=True)
df_prod = df_prod.asfreq('MS', fill_value=0)

# --- 6. MODELO MATEMÁTICO ---
st.subheader(f"📈 Análise: {produto_selecionado}")
col_graph, col_kpi = st.columns([3, 1])

qtd_algoritmo = 0
msg_modelo = ""
cor_msg = "blue"

try:
    if len(df_prod) >= 12:
        modelo = ExponentialSmoothing(
            df_prod['Quantidade'], trend='add', seasonal='add', seasonal_periods=12
        ).fit()
        previsao = modelo.forecast(1)
        qtd_algoritmo = int(previsao.iloc[0])
        msg_modelo = "Holt-Winters (Sazonal)"
        cor_msg = "green"
    else:
        raise ValueError("Dados insuficientes")

except Exception as e:
    # Fallback Média 6 meses
    if len(df_prod) >= 6:
        qtd_algoritmo = int(df_prod['Quantidade'].tail(6).mean())
        msg_modelo = "Média Recente (Fallback)"
    else:
        qtd_algoritmo = int(df_prod['Quantidade'].mean())
        msg_modelo = "Média Simples"
    cor_msg = "orange"

if qtd_algoritmo < 0: qtd_algoritmo = 0

# --- APLICAÇÃO DO CENÁRIO SIMULADO ---
# Aqui a "mágica" do SAD acontece. O Gestor interfere no algoritmo.
fator = 1 + (ajuste_manual / 100)
qtd_final_decisao = int(qtd_algoritmo * fator)

# Preparação do Gráfico
df_historico = df_prod.copy()
df_historico['Tipo'] = 'Histórico'

# Linha do Algoritmo (Referência)
df_prev_alg = pd.DataFrame({'Quantidade': [qtd_algoritmo], 'Tipo': ['Previsão IA']},
                           index=[df_prod.index[-1] + pd.DateOffset(months=1)])

# Linha da Decisão (Simulada)
df_prev_sim = pd.DataFrame({'Quantidade': [qtd_final_decisao], 'Tipo': ['Cenário Ajustado']},
                           index=[df_prod.index[-1] + pd.DateOffset(months=1)])

# Monta o gráfico dependendo se houve ajuste ou não
if ajuste_manual != 0:
    df_grafico = pd.concat([df_historico, df_prev_alg, df_prev_sim])
    cor_status = "orange"  # Avisa que tem interferência manual
else:
    df_grafico = pd.concat([df_historico, df_prev_alg])
    cor_status = cor_msg  # Mantém a cor do algoritmo

df_grafico_reset = df_grafico.reset_index().rename(columns={'index': 'Data'})

with col_graph:
    st.line_chart(df_grafico_reset, x='Data', y='Quantidade', color='Tipo')
    if ajuste_manual != 0:
        st.caption(f"ℹ️ Base Algoritmo: {qtd_algoritmo} un | 🖐️ **Ajuste Manual: {ajuste_manual}%**")
    else:
        st.caption(f"ℹ️ Algoritmo: :{cor_msg}[{msg_modelo}]")

with col_kpi:
    st.markdown("### Demanda Final")
    # Mostra o valor FINAL (Pós simulação)
    st.metric("PCP deve planejar:", f"{qtd_final_decisao} un",
              delta=f"{ajuste_manual}% sobre IA" if ajuste_manual != 0 else "0% Ajuste")

    st.divider()
    st.caption("Base Estatística:")
    st.text(f"IA Sugeriu: {qtd_algoritmo}")
    st.text(f"Média Hist: {int(df_prod['Quantidade'].mean())}")

# --- 7. DECISÃO (BASEADA NO CENÁRIO SIMULADO) ---
st.divider()
st.header("📢 Relatório PCP (Baseado no Cenário)")
necessidade = max(0, qtd_final_decisao - estoque_atual)
parafina_nec = necessidade * peso_unitario
saldo_parafina = estoque_parafina - parafina_nec

c1, c2, c3, c4 = st.columns(4)
c1.info(f"📦 Estoque:\n\n{estoque_atual}")
c2.warning(f"🔮 Demanda Ajustada:\n\n{qtd_final_decisao}")
if necessidade > 0:
    c3.error(f"🔨 Produzir:\n\n{necessidade}")
else:
    c3.success("✅ Produzir:\n\n0")
c4.metric("Parafina Nec.", f"{parafina_nec:.1f} Kg")

# --- 8. RECOMENDAÇÃO ---
st.subheader("🤖 Recomendação")
if necessidade == 0:
    st.success("✅ Estoque cobre a demanda do cenário simulado.")
elif saldo_parafina < 0:
    st.error(f"🚨 RUPTURA! Faltam {abs(saldo_parafina):.1f} Kg de parafina para este cenário.")
elif saldo_parafina < 50:
    st.warning(f"⚠️ Atenção! Estoque de insumo baixo ({saldo_parafina:.1f} Kg).")
else:
    st.success(f"✅ Produção Autorizada. Saldo insumo OK ({saldo_parafina:.1f} Kg).")