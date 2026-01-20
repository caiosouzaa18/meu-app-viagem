import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta

st.set_page_config(page_title="Viagem Pro - Alertas", layout="wide")

# Inicialização do estado
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'gastos' not in st.session_state: st.session_state.gastos = []

# --- ETAPA 1: ROTA E MAPA ---
if st.session_state.etapa == 1:
    st.header("📍 Passo 1: Destino e Logística")
    with st.form("config_inicial"):
        col1, col2 = st.columns(2)
        origem = col1.text_input("De onde você está saindo?", "Feira de Santana, BA")
        destino = col1.text_input("Para onde você vai?", "Juazeiro, BA")
        qtd = col2.number_input("Quantas pessoas na viagem?", min_value=1, step=1, value=2)
        
        if st.form_submit_button("Calcular Rota e Definir Nomes"):
            try:
                # User_agent único evita erros de conexão
                geolocator = Nominatim(user_agent="gestor_viagem_v3_alerta")
                loc1 = geolocator.geocode(origem)
                loc2 = geolocator.geocode(destino)
                
                if loc1 and loc2:
                    dist = geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
                    st.session_state.coord_origem = [loc1.latitude, loc1.longitude]
                    st.session_state.coord_destino = [loc2.latitude, loc2.longitude]
                    st.session_state.distancia = dist
                    st.session_state.qtd = qtd
                    st.session_state.local_destino = destino
                    st.session_state.etapa = 2
                    st.rerun()
                else:
                    st.error("Endereço não encontrado. Digite 'Cidade, Estado'.")
            except:
                st.error("Serviço de mapas ocupado. Aguarde 2 segundos e tente novamente.")

# --- ETAPA 2: CADASTRO DE NOMES ---
elif st.session_state.etapa == 2:
    st.header("👥 Passo 2: Quem são os viajantes?")
    with st.form("cadastro_nomes"):
        lista_nomes = []
        for i in range(st.session_state.qtd):
            n = st.text_input(f"Nome do Viajante {i+1}")
            lista_nomes.append(n)
        if st.form_submit_button("Começar Viagem"):
            if all(lista_nomes):
                st.session_state.participantes = lista_nomes
                st.session_state.etapa = 3
                st.rerun()

# --- ETAPA 3: PAINEL COM ALERTAS ---
elif st.session_state.etapa == 3:
    st.title(f"🚗 Viagem: {st.session_state.local_destino}")

    # --- SEÇÃO DE ALERTAS CRÍTICOS ---
    hoje = datetime.now().date()
    prazo_alerta = hoje + timedelta(days=3)
    
    alertas = []
    for g in st.session_state.gastos:
        if g['forma'] == "Cartão de Crédito" and isinstance(g['venc'], datetime):
            venc_data = g['venc']
        elif g['forma'] == "Cartão de Crédito" and hasattr(g['venc'], 'date'): # Caso venha do date_input
            venc_data = g['venc']
        else: continue

        if hoje <= venc_data <= prazo_alerta:
            # Verifica se ainda há alguém que não pagou esse gasto
            if len(g['quitado_por']) < len(st.session_state.participantes):
                alertas.append(f"⚠️ **{g['desc']}** vence dia {venc_data.strftime('%d/%m')}! (Faltam pagamentos)")

    if alertas:
        for alerta in alertas:
            st.error(alerta)

    # Registro de Gasto
    with st.expander("➕ Adicionar Novo Gasto"):
        with st.form("novo_gasto", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            desc = c1.text_input("O que comprou?")
            valor = c2.number_input("Valor Total", min_value=0.0)
            pagador = c3.selectbox("Quem pagou?", st.session_state.participantes)
            
            c4, c5 = st.columns(2)
            forma = c4.selectbox("Pagamento", ["Dinheiro", "Pix", "Cartão de Crédito"])
            venc = c5.date_input("Vencimento")
            
            if st.form_submit_button("Salvar"):
                st.session_state.gastos.append({
                    "desc": desc, "valor": valor, "pagador": pagador,
                    "forma": forma, "venc": venc, "quitado_por": [pagador]
                })
                st.rerun()

    # Exibição e Quitação
    st.subheader("📋 Gestão de Pagamentos")
    for i, g in enumerate(st.session_state.gastos):
        valor_ind = g['valor'] / len(st.session_state.participantes)
        pendentes = [p for p in st.session_state.participantes if p not in g['quitado_por']]
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{g['desc']}** | R$ {g['valor']:.2f}")
            if pendentes:
                p_pago = col2.selectbox("Quitar para:", pendentes, key=f"q_{i}")
                if col2.button("✔ Confirmar", key=f"b_{i}"):
                    st.session_state.gastos[i]['quitado_por'].append(p_pago)
                    st.rerun()
            else:
                col2.success("Tudo Pago!")
