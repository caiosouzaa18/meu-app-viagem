import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestor de Gastos de Viagem", layout="wide")

st.title("✈️ Gestor de Custos de Viagem")

# --- CONFIGURAÇÃO DA VIAGEM ---
with st.sidebar:
    st.header("Configurações da Viagem")
    destino = st.text_input("Local da Viagem", "Paris")
    qtd_pessoas = st.number_input("Quantidade de Pessoas", min_value=1, value=2)
    moeda_internacional = st.checkbox("Viagem Internacional?")
    taxa_cambio = 1.0
    if moeda_internacional:
        taxa_cambio = st.number_input("Taxa de Câmbio (1 Moeda = X Reais)", value=5.50)

# Inicializar estado do aplicativo para salvar dados
if 'gastos' not in st.session_state:
    st.session_state.gastos = []

# --- FORMULÁRIO DE CADASTRO DE GASTO ---
st.subheader("Registrar Nova Despesa")
col1, col2, col3 = st.columns(3)

with col1:
    descricao = st.text_input("Descrição do Gasto")
    valor = st.number_input("Valor (na moeda local)", min_value=0.0)
    categoria = st.selectbox("Categoria", ["Alimentação", "Transporte", "Hospedagem", "Lazer"])

with col2:
    quem_pagou = st.text_input("Quem pagou? (Nome)")
    forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão de Crédito"])

with col3:
    data_vencimento = None
    if forma_pagamento == "Cartão de Crédito":
        data_vencimento = st.date_input("Vencimento da Fatura")

if st.button("Adicionar Despesa"):
    valor_convertido = valor * taxa_cambio
    st.session_state.gastos.append({
        "Descrição": descricao,
        "Categoria": categoria,
        "Valor Original": valor,
        "Valor em R$": valor_convertido,
        "Quem Pagou": quem_pagou,
        "Forma": forma_pagamento,
        "Vencimento": data_vencimento,
        "Por Pessoa": valor_convertido / qtd_pessoas
    })
    st.success("Gasto registrado!")

# --- RELATÓRIOS ---
if st.session_state.gastos:
    df = pd.DataFrame(st.session_state.gastos)
    
    st.divider()
    st.subheader(f"📊 Relatório Geral: {destino}")
    
    # Métricas principais
    total_geral = df["Valor em R$"].sum()
    st.metric("Gasto Total da Viagem", f"R$ {total_geral:,.2f}")

    # Tabela de Gastos
    st.dataframe(df)

    # --- ANÁLISE POR CATEGORIA ---
    st.subheader("Gastos por Categoria")
    gastos_cat = df.groupby("Categoria")["Valor em R$"].sum()
    st.bar_chart(gastos_cat)

    # --- DIVISÃO POR PESSOA E REEMBOLSOS ---
    st.subheader("💰 Divisão e Acertos")
    
    # Cálculo simplificado de quem deve a quem
    pagos_por_pessoa = df.groupby("Quem Pagou")["Valor em R$"].sum()
    custo_ideal_por_pessoa = total_geral / qtd_pessoas
    
    for pessoa, total_pago in pagos_por_pessoa.items():
        saldo = total_pago - custo_ideal_por_pessoa
        if saldo > 0:
            st.info(f"**{pessoa}** pagou R$ {total_pago:,.2f} e deve **receber** R$ {saldo:,.2f}")
        else:
            st.warning(f"**{pessoa}** pagou R$ {total_pago:,.2f} e deve **pagar** R$ {abs(saldo):,.2f}")

    # --- ALERTAS DE CARTÃO ---
    st.subheader("💳 Próximos Vencimentos de Cartão")
    df_cartao = df[df["Forma"] == "Cartão de Crédito"].copy()
    if not df_cartao.empty:
        df_cartao = df_cartao.sort_values(by="Vencimento")
        st.table(df_cartao[["Descrição", "Quem Pagou", "Valor em R$", "Vencimento"]])
    else:
        st.write("Nenhum gasto em cartão registrado.")

else:
    st.info("Aguardando o primeiro registro de gasto para gerar relatórios.")