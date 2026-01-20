import streamlit as st
import pandas as pd
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Viagem Pro | Gestor Financeiro", layout="wide", page_icon="✈️")

DB_FILE = "dados_viagem.csv"

def carregar_dados():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Descrição", "Valor", "Pagador", "Forma", "Vencimento", "Categoria", "Quitados"])

def salvar_dados(df):
    df.to_csv(DB_FILE, index=False)

if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'df_gastos' not in st.session_state: st.session_state.df_gastos = carregar_dados()

# --- ETAPA 1 E 2 (Mantidas as lógicas anteriores de Destino e Nomes) ---
# ... (Código de Etapa 1 e 2 omitido para brevidade, permanece igual ao anterior)

# --- ETAPA 3: PAINEL COM TEXTOS EXPLICITOS ---
if st.session_state.etapa == 3:
    st.title(f"✈️ Painel: {st.session_state.info_viagem['destino']}")
    
    # --- BARRA LATERAL (RANKING COM TEXTO) ---
    with st.sidebar:
        st.header("📊 Resumo de Acertos")
        
        # Cálculo de Saldos
        saldos = {n: 0.0 for n in st.session_state.participantes if st.session_state.vinculos[n] == n}
        for _, g in st.session_state.df_gastos.iterrows():
            v_ind = g['Valor'] / len(st.session_state.participantes)
            quitados = eval(str(g['Quitados']))
            
            for p in st.session_state.participantes:
                resp_p = st.session_state.vinculos[p]
                resp_pagador = st.session_state.vinculos[g['Pagador']]
                if p not in quitados and resp_p != resp_pagador:
                    saldos[resp_p] -= v_ind
                    saldos[resp_pagador] += v_ind
        
        # EXIBIÇÃO EXPLÍCITA
        for n, s in saldos.items():
            if s > 0.01: # Crédito
                st.success(f"**{n}**\n\n🟢 A receber: R$ {s:.2f}")
            elif s < -0.01: # Débito
                st.error(f"**{n}**\n\n🔴 Deve: R$ {abs(s):.2f}")
            else:
                st.info(f"**{n}**\n\n⚪ Está em dia")

        if st.button("Zerar Viagem"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.session_state.clear()
            st.rerun()

    # --- REGISTRO DE GASTOS ---
    with st.expander("➕ Novo Gasto"):
        with st.form("novo_gasto", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            desc = c1.text_input("Descrição")
            valor = c2.number_input("Valor Total", min_value=0.0)
            pagador = c3.selectbox("Quem pagou?", st.session_state.participantes)
            
            if st.form_submit_button("Salvar"):
                resp_pagador = st.session_state.vinculos[pagador]
                quitados_init = [n for n, r in st.session_state.vinculos.items() if r == resp_pagador]
                
                novo_gasto = pd.DataFrame([{
                    "Descrição": desc, "Valor": valor, "Pagador": pagador,
                    "Forma": "Dinheiro", "Vencimento": datetime.now().date(), "Categoria": "Geral",
                    "Quitados": str(quitados_init)
                }])
                st.session_state.df_gastos = pd.concat([st.session_state.df_gastos, novo_gasto], ignore_index=True)
                salvar_dados(st.session_state.df_gastos)
                st.rerun()

    # --- HISTÓRICO COM TEXTO DE PENDÊNCIA ---
    st.subheader("📑 Histórico de Despesas")
    for i, g in st.session_state.df_gastos.iterrows():
        quitados = eval(str(g['Quitados']))
        pendentes = [p for p in st.session_state.participantes if p not in quitados]
        valor_cada = g['Valor'] / len(st.session_state.participantes)
        
        with st.container(border=True):
            col_info, col_acao = st.columns([3, 1])
            col_info.write(f"**{g['Descrição']}** | Total: R$ {g['Valor']:.2f}")
            
            if pendentes:
                # Texto explicativo por linha
                col_info.write(f"⚠️ **Pendente:** Cada um deve R$ {valor_cada:.2f} para {g['Pagador']}")
                p_pagando = col_acao.selectbox("Confirmar pagamento de:", pendentes, key=f"p_{i}")
                if col_acao.button("Confirmar", key=f"b_{i}"):
                    st.session_state.df_gastos.at[i, 'Quitados'] = str(quitados + [p_pagando])
                    salvar_dados(st.session_state.df_gastos)
                    st.rerun()
            else:
                col_acao.success("✅ Tudo Pago")
