import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

st.set_page_config(page_title="Viagem Pro", layout="wide")

# --- INICIALIZAÇÃO DE ESTADO ---
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'gastos' not in st.session_state: st.session_state.gastos = []
if 'participantes' not in st.session_state: st.session_state.participantes = []

# --- ETAPA 1: LOGÍSTICA E MAPA ---
if st.session_state.etapa == 1:
    st.header("📍 Passo 1: Configuração da Viagem")
    
    col1, col2 = st.columns(2)
    with col1:
        origem = st.text_input("De onde você está saindo?", "São Paulo, SP")
        destino = st.text_input("Para onde você vai?", "Rio de Janeiro, RJ")
    
    with col2:
        qtd = st.number_input("Quantas pessoas?", min_value=1, step=1)
    
    if st.button("Calcular Rota e Definir Nomes"):
        try:
            geolocator = Nominatim(user_agent="viagem_app")
            loc1 = geolocator.geocode(origem)
            loc2 = geolocator.geocode(destino)
            distancia = geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
            st.session_state.distancia = distancia
            st.session_state.qtd = qtd
            st.session_state.etapa = 2
            st.rerun()
        except:
            st.error("Não foi possível localizar os endereços. Tente ser mais específico.")

# --- ETAPA 2: NOMES DOS PARTICIPANTES ---
elif st.session_state.etapa == 2:
    st.header("👥 Passo 2: Quem são os viajantes?")
    st.info(f"Distância calculada: {st.session_state.distancia:.2f} KM")
    
    nomes = []
    for i in range(st.session_state.qtd):
        nome = st.text_input(f"Nome do Participante {i+1}", key=f"p_{i}")
        nomes.append(nome)
    
    if st.button("Finalizar Configuração"):
        st.session_state.participantes = [n for n in nomes if n]
        st.session_state.etapa = 3
        st.rerun()

# --- ETAPA 3: GESTÃO DE GASTOS E PAGAMENTOS ---
elif st.session_state.etapa == 3:
    st.sidebar.title("💰 Painel de Controle")
    st.sidebar.write(f"**Destino:** {st.session_state.distancia:.2f} KM de distância")
    
    # Registro de Gasto
    with st.form("novo_gasto"):
        c1, c2, c3 = st.columns(3)
        desc = c1.text_input("O que comprou?")
        valor = c2.number_input("Valor Total", min_value=0.0)
        pago_por = c3.selectbox("Quem pagou na hora?", st.session_state.participantes)
        
        if st.form_submit_button("Registrar Gasto"):
            valor_individual = valor / len(st.session_state.participantes)
            st.session_state.gastos.append({
                "id": len(st.session_state.gastos),
                "item": desc,
                "total": valor,
                "quem_pagou": pago_por,
                "pago_individualmente": {nome: False for nome in st.session_state.participantes if nome != pago_por}
            })

    # Listagem e Botão de Pagar
    st.subheader("📝 Lista de Despesas")
    for idx, g in enumerate(st.session_state.gastos):
        with st.expander(f"{g['item']} - Total: R$ {g['total']:.2f} (Pago por: {g['quem_pagou']})"):
            for pessoa in st.session_state.participantes:
                if pessoa != g['quem_pagou']:
                    valor_devido = g['total'] / len(st.session_state.participantes)
                    status = "✅ Pago" if g['pago_individualmente'].get(pessoa) else "❌ Pendente"
                    col_p, col_b = st.columns([3, 1])
                    col_p.write(f"{pessoa} deve R$ {valor_devido:.2f} | Status: {status}")
                    if not g['pago_individualmente'].get(pessoa):
                        if col_b.button(f"Pagar p/ {pessoa}", key=f"btn_{idx}_{pessoa}"):
                            st.session_state.gastos[idx]['pago_individualmente'][pessoa] = True
                            st.rerun()

    # RANKING
    st.divider()
    st.subheader("🏆 Ranking de Acerto de Contas")
    saldos = {nome: 0.0 for nome in st.session_state.participantes}
    
    for g in st.session_state.gastos:
        val_ind = g['total'] / len(st.session_state.participantes)
        for p, pago in g['pago_individualmente'].items():
            if not pago:
                saldos[p] -= val_ind # Deve
                saldos[g['quem_pagou']] += val_ind # Tem a receber
                
    rank_df = pd.DataFrame(list(saldos.items()), columns=['Nome', 'Saldo (R$)'])
    st.table(rank_df.sort_values(by="Saldo (R$)", ascending=True))
