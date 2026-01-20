import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium
from datetime import datetime, timedelta

st.set_page_config(page_title="Viagem Pro", layout="wide")

# Inicialização do estado
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'gastos' not in st.session_state: st.session_state.gastos = []

# --- ETAPA 1: DESTINO ---
if st.session_state.etapa == 1:
    st.header("📍 Passo 1: Destino e Logística")
    with st.form("config_inicial"):
        col1, col2 = st.columns(2)
        origem = col1.text_input("Origem (Ex: Feira de Santana, BA)", "Feira de Santana, BA")
        destino = col1.text_input("Destino (Ex: Juazeiro, BA)", "Juazeiro, BA")
        qtd = col2.number_input("Quantas pessoas?", min_value=1, step=1, value=2)
        
        if st.form_submit_button("Confirmar Destino"):
            # Usando um User Agent bem específico para evitar bloqueios
            geolocator = Nominatim(user_agent="viagem_app_final_user_123")
            try:
                loc1 = geolocator.geocode(origem, timeout=10)
                loc2 = geolocator.geocode(destino, timeout=10)
                
                if loc1 and loc2:
                    st.session_state.distancia = geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
                    st.session_state.coords = [[loc1.latitude, loc1.longitude], [loc2.latitude, loc2.longitude]]
                    st.session_state.local_destino = destino
                    st.session_state.qtd = qtd
                    st.session_state.etapa = 2
                    st.rerun()
                else:
                    st.error("Endereço não encontrado. Tente adicionar ', Brasil' ao final.")
            except:
                st.warning("Serviço de mapa instável. Vamos prosseguir sem os KMs por enquanto.")
                st.session_state.distancia = 0
                st.session_state.local_destino = destino
                st.session_state.qtd = qtd
                st.session_state.etapa = 2
                st.rerun()

# --- ETAPA 2: NOMES OBRIGATÓRIOS ---
elif st.session_state.etapa == 2:
    st.header("👥 Passo 2: Nomes dos Viajantes")
    with st.form("nomes"):
        lista = []
        for i in range(st.session_state.qtd):
            lista.append(st.text_input(f"Nome do Viajante {i+1}"))
        if st.form_submit_button("Salvar Nomes"):
            if all(lista):
                st.session_state.participantes = lista
                st.session_state.etapa = 3
                st.rerun()
            else:
                st.error("Preencha todos os nomes!")

# --- ETAPA 3: PAINEL PRINCIPAL ---
elif st.session_state.etapa == 3:
    st.title(f"🚗 Viagem para {st.session_state.local_destino}")
    
    # Exibição do Mapa Estilo Google
    if 'coords' in st.session_state:
        m = folium.Map(location=st.session_state.coords[0], zoom_start=6)
        folium.Marker(st.session_state.coords[0], popup="Origem", icon=folium.Icon(color='blue')).add_to(m)
        folium.Marker(st.session_state.coords[1], popup="Destino", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine(st.session_state.coords, color="blue", weight=3).add_to(m)
        st_folium(m, width=1200, height=350)

    # Alerta de Vencimento
    hoje = datetime.now().date()
    for g in st.session_state.gastos:
        if g['forma'] == "Cartão de Crédito" and (g['venc'] - hoje).days <= 3:
            if len(g['quitado_por']) < len(st.session_state.participantes):
                st.error(f"🚨 ALERTA: O gasto '{g['desc']}' vence em breve! ({g['venc'].strftime('%d/%m')})")

    # Registro e Ranking (Colunas)
    col_reg, col_rank = st.columns([2, 1])
    
    with col_reg:
        st.subheader("➕ Novo Gasto")
        with st.form("gasto", clear_on_submit=True):
            d = st.text_input("O que foi pago?")
            v = st.number_input("Valor", min_value=0.0)
            p = st.selectbox("Quem pagou?", st.session_state.participantes)
            f = st.selectbox("Forma", ["Dinheiro", "Cartão de Crédito"])
            dt = st.date_input("Vencimento")
            if st.form_submit_button("Registrar"):
                st.session_state.gastos.append({"desc": d, "valor": v, "pagador": p, "forma": f, "venc": dt, "quitado_por": [p]})
                st.rerun()

    with col_rank:
        st.subheader("🏆 Ranking Financeiro")
        saldos = {n: 0.0 for n in st.session_state.participantes}
        for g in st.session_state.gastos:
            v_ind = g['valor'] / len(st.session_state.participantes)
            for part in st.session_state.participantes:
                if part == g['pagador']:
                    saldos[part] += (v_ind * (len(st.session_state.participantes) - len(g['quitado_por'])))
                elif part not in g['quitado_por']:
                    saldos[part] -= v_ind
        
        for n, s in saldos.items():
            st.write(f"{n}: {'🟢' if s >= 0 else '🔴'} R$ {s:.2f}")

    # Listagem com Botão de Pagamento
    st.divider()
    st.subheader("📑 Histórico e Quitação")
    for i, g in enumerate(st.session_state.gastos):
        pendentes = [p for p in st.session_state.participantes if p not in g['quitado_por']]
        c1, c2 = st.columns([3, 1])
        c1.write(f"**{g['desc']}** - Pago por {g['pagador']} (R$ {g['valor']:.2f})")
        if pendentes:
            quem = c2.selectbox("Quem está pagando?", pendentes, key=f"sel_{i}")
            if c2.button("Confirmar Pagar", key=f"btn_{i}"):
                st.session_state.gastos[i]['quitado_por'].append(quem)
                st.rerun()
        else:
            c2.success("Quitado!")
