import streamlit as st
import pandas as pd
import os
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DO APP ---
st.set_page_config(page_title="Viagem Pro", layout="wide", page_icon="✈️")

# Arquivo para não perder os dados
DB_FILE = "dados_viagem.csv"

def carregar_dados():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Descrição", "Valor", "Pagador", "Forma", "Vencimento", "Quitados"])

def salvar_dados(df):
    df.to_csv(DB_FILE, index=False)

# Inicialização do Estado
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'df_gastos' not in st.session_state: st.session_state.df_gastos = carregar_dados()

# --- ETAPA 1: DESTINO E MAPA ---
if st.session_state.etapa == 1:
    st.title("📍 Configuração Inicial")
    with st.form("config_viagem"):
        col1, col2 = st.columns(2)
        origem = col1.text_input("De onde você sai?", "Feira de Santana, BA")
        destino = col1.text_input("Para onde você vai?", "Salvador, BA")
        qtd = col2.number_input("Total de pessoas (incluindo dependentes)", min_value=1, value=3)
        
        if st.form_submit_button("Avançar"):
            st.session_state.info_viagem = {"destino": destino, "qtd": int(qtd)}
            # Tenta carregar o mapa, mas não trava se der erro
            try:
                geolocator = Nominatim(user_agent="viagem_app_v5_final")
                loc1 = geolocator.geocode(origem, timeout=10)
                loc2 = geolocator.geocode(destino, timeout=10)
                if loc1 and loc2:
                    st.session_state.coords = [[loc1.latitude, loc1.longitude], [loc2.latitude, loc2.longitude]]
            except:
                pass
            st.session_state.etapa = 2
            st.rerun()

# --- ETAPA 2: VIAJANTES E RESPONSÁVEIS ---
elif st.session_state.etapa == 2:
    st.title("👥 Quem vai viajar?")
    with st.form("form_nomes"):
        nomes = []
        for i in range(st.session_state.info_viagem['qtd']):
            nomes.append(st.text_input(f"Nome do Viajante {i+1}", key=f"user_{i}"))
        
        st.write("---")
        st.subheader("🏦 Vínculos Financeiros")
        st.caption("Selecione quem paga as contas de cada um (ex: Pai paga para o Filho)")
        vinculos = {}
        for nome in nomes:
            if nome:
                vinculos[nome] = st.selectbox(f"Responsável por {nome}:", nomes, index=nomes.index(nome), key=f"resp_{nome}")
        
        if st.form_submit_button("Finalizar Configuração"):
            if all(n.strip() != "" for n in nomes):
                st.session_state.participantes = nomes
                st.session_state.vinculos = vinculos
                st.session_state.etapa = 3
                st.rerun()
            else:
                st.error("Preencha todos os nomes!")

# --- ETAPA 3: PAINEL DE CONTROLO ---
elif st.session_state.etapa == 3:
    st.title(f"✈️ Viagem: {st.session_state.info_viagem['destino']}")

    # --- BARRA LATERAL COM SALDOS CLAROS ---
    with st.sidebar:
        st.header("📊 Resumo de Contas")
        # Lógica de cálculo considerando responsáveis
        saldos = {n: 0.0 for n in st.session_state.participantes if st.session_state.vinculos[n] == n}
        for _, g in st.session_state.df_gastos.iterrows():
            v_ind = float(g['Valor']) / len(st.session_state.participantes)
            quitados = eval(str(g['Quitados']))
            for p in st.session_state.participantes:
                if p not in quitados:
                    resp_p = st.session_state.vinculos[p]
                    resp_pagador = st.session_state.vinculos[g['Pagador']]
                    if resp_p != resp_pagador:
                        saldos[resp_p] -= v_ind
                        saldos[resp_pagador] += v_ind

        for n, s in saldos.items():
            if s > 0.01:
                st.success(f"**{n}**\n\n🟢 A receber: R$ {s:.2f}")
            elif s < -0.01:
                st.error(f"**{n}**\n\n🔴 Deve: R$ {abs(s):.2f}")
            else:
                st.info(f"**{n}**\n\n⚪ Está em dia")

        if st.button("Resetar Tudo"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.session_state.clear()
            st.rerun()

    # --- ALERTA DE VENCIMENTO ---
    hoje = datetime.now().date()
    for i, g in st.session_state.df_gastos.iterrows():
        try:
            venc = datetime.strptime(str(g['Vencimento']), '%Y-%m-%d').date()
            if g['Forma'] == "Cartão de Crédito" and (venc - hoje).days <= 3:
                if len(eval(str(g['Quitados']))) < len(st.session_state.participantes):
                    st.warning(f"⏰ **URGENTE:** Pagar R$ {g['Valor']:.2f} de '{g['Descrição']}' para {g['Pagador']} (Vence {venc.strftime('%d/%m')})")
        except: pass

    # --- REGISTRO ---
    with st.expander("➕ Adicionar Despesa", expanded=True):
        with st.form("add_gasto", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            d = col_a.text_input("O que comprou?")
            v = col_b.number_input("Valor Total", min_value=0.0)
            p = col_c.selectbox("Quem pagou?", st.session_state.participantes)
            f = st.selectbox("Forma", ["Dinheiro", "Pix", "Cartão de Crédito"])
            venc_f = st.date_input("Vencimento")
            
            if st.form_submit_button("Salvar"):
                # Quita automaticamente o pagador e seus dependentes
                p_resp = st.session_state.vinculos[p]
                quit_init = [nome for nome, resp in st.session_state.vinculos.items() if resp == p_resp]
                
                novo = pd.DataFrame([{"Descrição": d, "Valor": v, "Pagador": p, "Forma": f, "Vencimento": venc_f, "Quitados": str(quit_init)}])
                st.session_state.df_gastos = pd.concat([st.session_state.df_gastos, novo], ignore_index=True)
                salvar_dados(st.session_state.df_gastos)
                st.rerun()

    # --- LISTA ---
    st.subheader("📑 Histórico")
    for idx, g in st.session_state.df_gastos.iterrows():
        quitados = eval(str(g['Quitados']))
        pendentes = [p for p in st.session_state.participantes if p not in quitados]
        with st.container(border=True):
            ca, cb = st.columns([3, 1])
            ca.write(f"**{g['Descrição']}** - R$ {g['Valor']:.2f} (Pago por {g['Pagador']})")
            if pendentes:
                quem_pagando = cb.selectbox("Confirmar pago de:", pendentes, key=f"sel_{idx}")
                if cb.button("Confirmar", key=f"btn_{idx}"):
                    st.session_state.df_gastos.at[idx, 'Quitados'] = str(quitados + [quem_pagando])
                    salvar_dados(st.session_state.df_gastos)
                    st.rerun()
            else:
                cb.success("Liquidado!")
