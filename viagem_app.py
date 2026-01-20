import streamlit as st
import pandas as pd
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES E ESTILIZAÇÃO ---
st.set_page_config(page_title="Viagem Pro | Gestor Financeiro", layout="wide", page_icon="✈️")

DB_FILE = "dados_viagem.csv"

# --- FUNÇÕES DE PERSISTÊNCIA ---
def carregar_dados():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Descrição", "Valor", "Pagador", "Forma", "Vencimento", "Categoria", "Quitados"])

def salvar_dados(df):
    df.to_csv(DB_FILE, index=False)

# --- INICIALIZAÇÃO DO ESTADO ---
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'df_gastos' not in st.session_state: st.session_state.df_gastos = carregar_dados()

# --- ETAPA 1: LOGÍSTICA DE ROTA ---
if st.session_state.etapa == 1:
    st.title("📍 Configuração da Viagem")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        origem = c1.text_input("Origem", "Feira de Santana, BA")
        destino = c1.text_input("Destino", "Salvador, BA")
        qtd = c2.number_input("Total de Viajantes", min_value=1, value=3)
        
        if st.button("Confirmar Destino e Rota"):
            try:
                geolocator = Nominatim(user_agent="viagem_pro_app_v4")
                loc1 = geolocator.geocode(origem, timeout=10)
                loc2 = geolocator.geocode(destino, timeout=10)
                
                if loc1 and loc2:
                    st.session_state.coords = [[loc1.latitude, loc1.longitude], [loc2.latitude, loc2.longitude]]
                    st.session_state.distancia = geodesic(st.session_state.coords[0], st.session_state.coords[1]).km
                    st.session_state.info_viagem = {"destino": destino, "qtd": qtd}
                    st.session_state.etapa = 2
                    st.rerun()
                else:
                    st.error("Cidades não encontradas. Tente 'Cidade, Estado'.")
            except:
                st.warning("Serviço de mapas indisponível. Continuando configuração...")
                st.session_state.distancia = 0
                st.session_state.info_viagem = {"destino": destino, "qtd": qtd}
                st.session_state.etapa = 2
                st.rerun()

# --- ETAPA 2: VÍNCULOS FAMILIARES ---
elif st.session_state.etapa == 2:
    st.title("👥 Gestão de Viajantes")
    st.info("Defina quem é o responsável financeiro por cada pessoa (ex: Pai responsável pelo Filho).")
    
    with st.form("form_viajantes"):
        nomes = []
        for i in range(st.session_state.info_viagem['qtd']):
            nomes.append(st.text_input(f"Nome do Viajante {i+1}", key=f"v_{i}"))
        
        st.markdown("---")
        vinculos = {}
        if all(n.strip() != "" for n in nomes):
            for n in nomes:
                vinculos[n] = st.selectbox(f"Responsável financeiro por {n}:", nomes, index=nomes.index(n))
        
        if st.form_submit_button("Finalizar e Abrir Painel"):
            if all(n.strip() != "" for n in nomes):
                st.session_state.participantes = nomes
                st.session_state.vinculos = vinculos
                st.session_state.etapa = 3
                st.rerun()
            else: st.error("Preencha todos os nomes.")

# --- ETAPA 3: PAINEL PROFISSIONAL ---
elif st.session_state.etapa == 3:
    st.title(f"✈️ Painel: {st.session_state.info_viagem['destino']}")
    
    # --- BARRA LATERAL (RANKING E ALERTAS) ---
    with st.sidebar:
        st.header("📊 Resumo Financeiro")
        # Lógica de Ranking considerando Responsáveis
        saldos = {n: 0.0 for n in st.session_state.participantes if st.session_state.vinculos[n] == n}
        for _, g in st.session_state.df_gastos.iterrows():
            v_ind = g['Valor'] / len(st.session_state.participantes)
            quitados = eval(str(g['Quitados'])) # Converte string do CSV para lista
            
            for p in st.session_state.participantes:
                resp_p = st.session_state.vinculos[p]
                resp_pagador = st.session_state.vinculos[g['Pagador']]
                if p not in quitados and resp_p != resp_pagador:
                    saldos[resp_p] -= v_ind
                    saldos[resp_pagador] += v_ind
        
        for n, s in saldos.items():
            st.metric(f"Saldo de {n}", f"R$ {s:.2f}", delta=f"{s:.2f}")

        if st.button("Zerar Dados da Viagem"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.session_state.clear()
            st.rerun()

    # --- MAPA E ALERTAS ---
    col_map, col_alert = st.columns([2, 1])
    with col_map:
        if 'coords' in st.session_state:
            m = folium.Map(location=st.session_state.coords[0], zoom_start=7)
            folium.PolyLine(st.session_state.coords, color="blue", weight=3).add_to(m)
            st_folium(m, height=250, width=700)
    
    with col_alert:
        st.subheader("⚠️ Alertas de Fatura")
        hoje = datetime.now().date()
        for _, g in st.session_state.df_gastos.iterrows():
            venc = datetime.strptime(str(g['Vencimento']), '%Y-%m-%d').date()
            if g['Forma'] == "Cartão de Crédito" and (venc - hoje).days <= 3:
                if len(eval(str(g['Quitados']))) < len(st.session_state.participantes):
                    st.error(f"Pagar '{g['Descrição']}' até {venc.strftime('%d/%m')}")

    # --- REGISTRO DE GASTOS ---
    with st.expander("➕ Novo Gasto", expanded=False):
        with st.form("novo_gasto", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            desc = c1.text_input("Descrição")
            valor = c2.number_input("Valor Total", min_value=0.0)
            pagador = c3.selectbox("Quem pagou?", st.session_state.participantes)
            
            c4, c5, c6 = st.columns(3)
            forma = c4.selectbox("Forma", ["Dinheiro", "Pix", "Cartão de Crédito"])
            venc = c5.date_input("Vencimento")
            cat = c6.selectbox("Categoria", ["Alimentação", "Transporte", "Lazer", "Outros"])
            
            if st.form_submit_button("Salvar Despesa"):
                # Quitação automática para o pagador e seus dependentes
                resp_pagador = st.session_state.vinculos[pagador]
                quitados_init = [n for n, r in st.session_state.vinculos.items() if r == resp_pagador]
                
                novo_gasto = pd.DataFrame([{
                    "Descrição": desc, "Valor": valor, "Pagador": pagador,
                    "Forma": forma, "Vencimento": venc, "Categoria": cat,
                    "Quitados": str(quitados_init)
                }])
                st.session_state.df_gastos = pd.concat([st.session_state.df_gastos, novo_gasto], ignore_index=True)
                salvar_dados(st.session_state.df_gastos)
                st.rerun()

    # --- HISTÓRICO ---
    st.subheader("📑 Histórico de Despesas")
    for i, g in st.session_state.df_gastos.iterrows():
        quitados = eval(str(g['Quitados']))
        pendentes = [p for p in st.session_state.participantes if p not in quitados]
        
        with st.container(border=True):
            col_info, col_acao = st.columns([3, 1])
            col_info.write(f"**{g['Descrição']}** | R$ {g['Valor']:.2f} (Pago por {g['Pagador']})")
            
            if pendentes:
                p_pagando = col_acao.selectbox("Quitar para:", pendentes, key=f"p_{i}")
                if col_acao.button("Confirmar", key=f"b_{i}"):
                    # Se quem está pagando é dependente, o sistema deve tratar o responsável
                    st.session_state.df_gastos.at[i, 'Quitados'] = str(quitados + [p_pagando])
                    salvar_dados(st.session_state.df_gastos)
                    st.rerun()
            else:
                col_acao.success("Liquidado")
