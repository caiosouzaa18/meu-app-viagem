import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from streamlit_folium import st_folium
import folium

st.set_page_config(page_title="Viagem Pro", layout="wide")

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
                geolocator = Nominatim(user_agent="viagem_app_v2")
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
                    st.error("Endereço não encontrado. Verifique a grafia (Ex: Cidade, Estado).")
            except:
                st.error("Erro de conexão com o serviço de mapas.")

# --- ETAPA 2: CADASTRO OBRIGATÓRIO DE NOMES ---
elif st.session_state.etapa == 2:
    st.header("👥 Passo 2: Quem são os viajantes?")
    st.info(f"Distância: {st.session_state.distancia:.2f} km")
    
    with st.form("cadastro_nomes"):
        lista_nomes = []
        for i in range(st.session_state.qtd):
            n = st.text_input(f"Nome do Viajante {i+1}", key=f"user_{i}")
            lista_nomes.append(n)
        
        if st.form_submit_button("Finalizar e Abrir Painel"):
            if all(n.strip() != "" for n in lista_nomes):
                st.session_state.participantes = lista_nomes
                st.session_state.etapa = 3
                st.rerun()
            else:
                st.error("Todos os nomes devem ser preenchidos!")

# --- ETAPA 3: PAINEL DE GASTOS E RANKING ---
elif st.session_state.etapa == 3:
    st.title(f"🚗 Viagem: {st.session_state.local_destino}")
    
    # Exibição do Mapa
    with st.expander("🗺️ Ver Rota no Mapa"):
        m = folium.Map(location=st.session_state.coord_origem, zoom_start=6)
        folium.Marker(st.session_state.coord_origem, tooltip="Origem", icon=folium.Icon(color='blue')).add_to(m)
        folium.Marker(st.session_state.coord_destino, tooltip="Destino", icon=folium.Icon(color='red')).add_to(m)
        folium.PolyLine([st.session_state.coord_origem, st.session_state.coord_destino], color="red", weight=2.5).add_to(m)
        st_folium(m, width=1200, height=300)

    # Registro de Gasto
    st.divider()
    with st.form("novo_gasto", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        desc = c1.text_input("Descrição do Gasto")
        valor = c2.number_input("Valor Total (R$)", min_value=0.01)
        pagador = c3.selectbox("Quem pagou?", st.session_state.participantes)
        cat = c4.selectbox("Categoria", ["Alimentação", "Transporte", "Hospedagem", "Lazer"])
        
        c5, c6 = st.columns(2)
        forma = c5.selectbox("Forma de Pagamento", ["Dinheiro", "Pix", "Cartão de Crédito"])
        venc = c6.date_input("Vencimento (Se Cartão)")

        if st.form_submit_button("Registrar Gasto"):
            st.session_state.gastos.append({
                "id": len(st.session_state.gastos),
                "desc": desc, "valor": valor, "pagador": pagador,
                "cat": cat, "forma": forma, "venc": venc,
                "quitado_por": [pagador] # O pagador já começa como quitado
            })
            st.rerun()

    # Listagem de Gastos com Botão Pagar
    st.subheader("💳 Gastos e Quitações")
    for i, g in enumerate(st.session_state.gastos):
        valor_ind = g['valor'] / len(st.session_state.participantes)
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 2])
            col_info.write(f"**{g['desc']}** | Total: R$ {g['valor']:.2f} (R$ {valor_ind:.2f} p/ pessoa)")
            col_info.caption(f"Pago por: {g['pagador']} | Categoria: {g['cat']} | Vencimento: {g['venc']}")
            
            # Mostrar quem falta pagar e botão
            pendentes = [p for p in st.session_state.participantes if p not in g['quitado_por']]
            if not pendentes:
                col_btn.success("✅ Gasto totalmente quitado por todos!")
            else:
                col_btn.write(f"Falta pagar: {', '.join(pendentes)}")
                p_selecionado = col_btn.selectbox("Marcar como pago para:", pendentes, key=f"sel_{i}")
                if col_btn.button(f"Confirmar Pagamento de {p_selecionado}", key=f"btn_{i}"):
                    st.session_state.gastos[i]['quitado_por'].append(p_selecionado)
                    st.rerun()

    # RANKING
    st.divider()
    st.subheader("🏆 Ranking Financeiro")
    saldos = {n: 0.0 for n in st.session_state.participantes}
    
    for g in st.session_state.gastos:
        v_ind = g['valor'] / len(st.session_state.participantes)
        for p in st.session_state.participantes:
            if p == g['pagador']:
                # Ele recebe de todos que ainda não pagaram
                pendentes_count = len(st.session_state.participantes) - len(g['quitado_por'])
                saldos[p] += (v_ind * pendentes_count)
            elif p not in g['quitado_por']:
                # Ele deve a sua parte
                saldos[p] -= v_ind

    col_rank1, col_rank2 = st.columns(2)
    for i, (nome, saldo) in enumerate(sorted(saldos.items(), key=lambda x: x[1])):
        cor = "red" if saldo < 0 else "green"
        col_target = col_rank1 if i % 2 == 0 else col_rank2
        col_target.markdown(f"**{nome}**: :{cor}[R$ {saldo:.2f}]")

    # Botão de Exportar
    if st.session_state.gastos:
        csv = pd.DataFrame(st.session_state.gastos).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Relatório Completo", csv, "viagem.csv", "text/csv")
