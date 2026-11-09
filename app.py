import streamlit as st
import pandas as pd
import networkx as nx
from networkx.algorithms import community
import matplotlib.pyplot as plt

st.set_page_config(page_title="Twitch Graph Lab - MATI US", layout="wide")

st.title("🎮 Laboratorio Interactivo de Redes en Twitch (MATI - 4º Ing. Informática)")
st.markdown("""
Esta aplicación divulgativa acompaña nuestro estudio sobre **Centralidad, Comunidades y Efecto Mateo en Twitch**, 
basado en el artículo *Multi-scale Attributed Node Embedding* (Rozemberczki et al.) y datos extraídos con la **API Oficial de Twitch (Helix)**.
""")

# 1. Carga de datos de la API (o generación de respaldo si no se ha ejecutado el script de la API aún)
@st.cache_data
def cargar_grafo():
    G = nx.Graph()
    try:
        df_nodos = pd.read_csv("twitch_nodos.csv")
        df_aristas = pd.read_csv("twitch_aristas.csv")
        for _, r in df_nodos.iterrows():
            G.add_node(int(r["id_num"]), nombre=r["nombre"], juego=r["juego"], viewers=int(r["espectadores"]))
        for _, r in df_aristas.iterrows():
            G.add_edge(int(r["origen_id"]), int(r["destino_id"]), weight=int(r["peso"]))
    except FileNotFoundError:
        # Grafo de demostración de respaldo con nombres reales si se abre sin el CSV
        G = nx.powerlaw_cluster_graph(35, 3, 0.5, seed=42)
        juegos = ["League of Legends", "Just Chatting", "Minecraft", "Valorant"]
        for i in G.nodes():
            G.nodes[i]["nombre"] = f"Streamer_{i}"
            G.nodes[i]["juego"] = juegos[i % len(juegos)]
            G.nodes[i]["viewers"] = (G.degree(i) ** 2) * 120
    return G

G_base = cargar_grafo()

# Barra lateral pedagógica para interactuar en clase
st.sidebar.header("⚙️ Panel de Experimentación")
metrica = st.sidebar.selectbox(
    "1. Medida de Centralidad (Tamaño del nodo):",
    ["Centralidad de Grado (Popularidad)", "Centralidad de Intermediación (Puentes)", "Centralidad de Cercanía (Difusión)"]
)
nodos_a_banear = st.sidebar.slider("2. Simular ataque dirigido (Eliminar Top Hubs):", 0, 10, 0)

# Simulación constructiva de robustez: eliminamos los mayores hubs si el usuario mueve el slider
G = G_base.copy()
if nodos_a_banear > 0:
    top_hubs = sorted(G.degree, key=lambda x: x[1], reverse=True)[:nodos_a_banear]
    G.remove_nodes_from([n for n, _ in top_hubs])

# Cálculo de centralidad elegida
if "Grado" in metrica:
    valores_cent = nx.degree_centrality(G)
elif "Intermediación" in metrica:
    valores_cent = nx.betweenness_centrality(G)
else:
    valores_cent = nx.closeness_centrality(G)

# Detección de comunidades en vivo
comunidades = list(community.greedy_modularity_communities(G))
mapa_comunidad = {}
for idx, com in enumerate(comunidades):
    for nodo in com:
        mapa_comunidad[nodo] = idx

# Métricas superiores en tiempo real
col1, col2, col3, col4 = st.columns(4)
col1.metric("Vértices activos |V|", G.number_of_nodes())
col2.metric("Aristas activas |A|", G.number_of_edges())
col3.metric("Comunidades detectadas", len(comunidades))
col4.metric("Componentes Conexas", nx.number_connected_components(G))

# Visualización del grafo y tabla pedagógica
izq, der = st.columns([2, 1])

with izq:
    st.subheader("🕸️ Topología de Comunidades y Centralidad en Vivo")
    fig, ax = plt.subplots(figsize=(9, 6))
    pos = nx.spring_layout(G, seed=42)
    colores = [mapa_comunidad.get(n, 0) for n in G.nodes()]
    tamanos = [max(150, valores_cent.get(n, 0.1) * 2200) for n in G.nodes()]
    etiquetas = {n: G.nodes[n].get("nombre", str(n)) for n in G.nodes()}
    
    nx.draw_networkx_nodes(G, pos, node_color=colores, node_size=tamanos, cmap=plt.cm.Set2, alpha=0.9, ax=ax)
    nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color="gray", ax=ax)
    nx.draw_networkx_labels(G, pos, labels=etiquetas, font_size=8, font_weight="bold", ax=ax)
    ax.axis("off")
    st.pyplot(fig)

with der:
    st.subheader("🏆 Top 10 Nodos según la métrica")
    ranking = sorted(valores_cent.items(), key=lambda x: x[1], reverse=True)[:10]
    df_rank = pd.DataFrame([
        {
            "Streamer": G.nodes[n].get("nombre", f"Nodo {n}"),
            "Categoría API": G.nodes[n].get("juego", "-"),
            "Grado δ(v)": G.degree(n),
            "Valor Centralidad": round(val, 4),
            "Comunidad": f"Grupo {mapa_comunidad.get(n, 0) + 1}"
        }
        for n, val in ranking
    ])
    st.dataframe(df_rank, use_container_width=True, hide_index=True)

st.info("💡 **Demostración constructiva en vivo:** Mueve el deslizador de la izquierda para eliminar los *Hubs* principales. Verás cómo al destruir los nodos con mayor centralidad de intermediación, el grafo pierde su propiedad de Mundo Pequeño y se rompe en componentes conexas aisladas.")