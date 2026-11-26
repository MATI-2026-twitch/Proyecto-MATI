import csv
import gzip
import io
import random
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Twitch Graph Lab — MATI (US)", layout="wide")

# Paleta Twitch (a juego con la presentación)
TW_PURPLE = "#9146FF"
TW_DARK_PURPLE = "#6441A5"
TW_LIGHT_PURPLE = "#BF94FF"
TW_DARK = "#18181B"
TW_GOLD = "#F59E0B"

st.markdown(
    f"""
    <style>
        .titulo-twitch {{
            background-color: {TW_DARK};
            padding: 1.05rem 1.4rem;
            border-radius: 10px;
            border-left: 8px solid {TW_PURPLE};
            margin-bottom: 1rem;
        }}
        .titulo-twitch h1 {{
            color: #FFFFFF;
            margin: 0;
            font-size: 1.8rem;
        }}
        .titulo-twitch p {{
            color: #D2D2DC;
            margin: 0.35rem 0 0 0;
            font-size: 0.93rem;
        }}
    </style>
    <div class="titulo-twitch">
        <h1>Teoría de Grafos aplicada a Twitch · Graph Lab</h1>
        <p>MATI · Grado en Ingeniería Informática (TI) — Universidad de Sevilla |
        Centralidad, comunidades, simulación de ataques y demostraciones constructivas (2018–2026)</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# UTILIDADES DE LECTURA RESILIENTE (.csv, .zip y .csv.gz)
# ==============================================================================
@contextmanager
def abrir_csv_resiliente(ruta_csv, ruta_zip=None, subcadena_zip=None):
    """Abre un CSV directamente o, si no existe, lo busca dentro de un ZIP."""
    if ruta_csv and ruta_csv.exists():
        with ruta_csv.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            yield f
        return
    if ruta_zip and ruta_zip.exists():
        with zipfile.ZipFile(ruta_zip, "r") as zf:
            candidatos = [
                n for n in zf.namelist()
                if n.lower().endswith(".csv")
                and "__macosx" not in n.lower()
                and (not subcadena_zip or subcadena_zip.lower() in Path(n).name.lower())
            ]
            if candidatos:
                with zf.open(candidatos[0], "r") as raw:
                    yield io.TextIOWrapper(raw, encoding="utf-8-sig", errors="ignore", newline="")
                return
    yield None


DATASETS = [
    "2026 Captura Propia (ES + PT · En directo)",
    "2022 GitHub Overlap (Enero · Auge Hispano)",
    "2021 GitHub Overlap (Diciembre)",
    "2019 Kaggle Live (Audiencia Top-15)",
    "2018 SNAP — Comunidad Español (ES)",
    "2018 SNAP — Comunidad Portugués (PT)",
]


def _cargar_overlap(ruta_e, ruta_n, ruta_zip=None, top_k=15, es_2026=False):
    G = nx.Graph()
    idiomas = {}
    nombres = {}

    with abrir_csv_resiliente(ruta_n, ruta_zip, "nodes") as fn:
        if fn is not None:
            for fila in csv.DictReader(fn):
                nid = (fila.get("Id") or fila.get("id") or fila.get("login") or "").strip()
                lbl = (fila.get("Label") or fila.get("label") or fila.get("login") or "").strip()
                lang = (fila.get("language") or "").strip().upper()
                if nid:
                    clave = nid.lower() if es_2026 else (lbl.lower() if lbl.isascii() else nid.lower())
                    nombres[nid] = clave
                    if lang:
                        idiomas[clave] = lang

    vecinos = defaultdict(list)
    with abrir_csv_resiliente(ruta_e, ruta_zip, "edges") as fe:
        if fe is None:
            return G, idiomas, False
        lector = csv.reader(fe)
        next(lector, None)
        for fila in lector:
            if len(fila) < 2:
                continue
            u_raw, v_raw = fila[0].strip(), fila[1].strip()
            u = nombres.get(u_raw, u_raw.lower())
            v = nombres.get(v_raw, v_raw.lower())
            try:
                w = float(fila[2]) if len(fila) > 2 else 1.0
            except ValueError:
                w = 1.0
            if u != v:
                vecinos[u].append((w, v))
                vecinos[v].append((w, u))

    for u, lista in vecinos.items():
        for w, v in sorted(lista, key=lambda x: x[0], reverse=True)[:top_k]:
            G.add_edge(u, v, weight=w)
    return G, idiomas, True


def _cargar_snap_idioma(lang_code):
    G = nx.Graph()
    precomp = Path(f"datos/salidas/twitch_{lang_code}_edges.csv")
    if precomp.exists():
        with precomp.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            lector = csv.reader(f)
            next(lector, None)
            for fila in lector:
                if len(fila) >= 2 and fila[0] != fila[1]:
                    G.add_edge(fila[0].strip(), fila[1].strip())
        return G, {}, True

    ruta_feat = Path("datos/datos_twitch_2018/large_twitch_features.csv")
    ruta_edges = Path("datos/datos_twitch_2018/large_twitch_edges.csv")
    ruta_zip = Path("datos/datos_twitch_2018/twitch_gamers.zip")

    nodos_lang = set()
    with abrir_csv_resiliente(ruta_feat, ruta_zip, "features") as ff:
        if ff is None:
            return G, {}, False
        for fila in csv.DictReader(ff):
            if (fila.get("language") or "").strip().upper() == lang_code:
                nid = (fila.get("numeric_id") or fila.get("id") or "").strip()
                if nid:
                    nodos_lang.add(nid)
                    G.add_node(nid)

    with abrir_csv_resiliente(ruta_edges, ruta_zip, "edges") as fe:
        if fe is None:
            return G, {}, False
        lector = csv.reader(fe)
        next(lector, None)
        for fila in lector:
            if len(fila) >= 2:
                u, v = fila[0].strip(), fila[1].strip()
                if u != v and u in nodos_lang and v in nodos_lang:
                    G.add_edge(u, v)

    return G, {}, True


def _cargar_kaggle_2019(top_k=15):
    G = nx.Graph()
    for cand in [
        Path("datos/salidas/2023_kaggle_podado_edges.csv"),
        Path("datos/salidas/2023_kaggle_podadoedges.csv"),
    ]:
        if cand.exists():
            with cand.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                lector = csv.reader(f)
                next(lector, None)
                for fila in lector:
                    if len(fila) >= 2 and fila[0] != fila[1]:
                        G.add_edge(fila[0].strip(), fila[1].strip())
            return G, {}, True

    # Fallback directo desde datos/datos_twitch_2023/100k_a.csv.gz
    ruta_gz = Path("datos/datos_twitch_2023/100k_a.csv.gz")
    if not ruta_gz.exists():
        return G, {}, False

    user_canales = defaultdict(set)
    conteo_canales = Counter()
    with gzip.open(ruta_gz, "rt", encoding="utf-8-sig", errors="ignore", newline="") as f:
        lector = csv.reader(f)
        for fila in lector:
            if len(fila) < 3:
                continue
            uid, canal = fila[0].strip(), fila[2].strip().lower()
            if not canal or canal in ("streamer", "channel", "streamer_username"):
                continue
            if canal not in user_canales[uid]:
                user_canales[uid].add(canal)
                conteo_canales[canal] += 1

    top_canales = {c for c, _ in conteo_canales.most_common(450)}
    pesos = Counter()
    for canales in user_canales.values():
        filtrados = sorted(canales & top_canales)
        if 2 <= len(filtrados) <= 25:
            for u, v in combinations(filtrados, 2):
                pesos[(u, v)] += 1

    vecinos = defaultdict(list)
    for (u, v), w in pesos.items():
        if w >= 3:
            vecinos[u].append((w, v))
            vecinos[v].append((w, u))

    for u, lista in vecinos.items():
        for w, v in sorted(lista, reverse=True)[:top_k]:
            G.add_edge(u, v, weight=w)
    return G, {}, True


@st.cache_data(show_spinner="Cargando grafo desde los datos del proyecto...")
def cargar_grafo(nombre_red):
    if "2026" in nombre_red:
        return _cargar_overlap(
            Path("datos/twitch_2026_edges.csv"),
            Path("datos/twitch_2026_nodes.csv"),
            es_2026=True,
        )
    if "2022" in nombre_red:
        return _cargar_overlap(
            Path("datos/datos_twitch_2022/2022-01-edges.csv"),
            Path("datos/datos_twitch_2022/2022-01-nodes.csv"),
            Path("datos/datos_twitch_2022/twitch_2022.zip"),
        )
    if "2021" in nombre_red:
        return _cargar_overlap(
            Path("datos/datos_twitch_2021/2021-12-edges.csv"),
            Path("datos/datos_twitch_2021/2021-12-nodes.csv"),
            Path("datos/datos_twitch_2021/twitch_2021.zip"),
        )
    if "2019" in nombre_red:
        return _cargar_kaggle_2019()
    if "Español" in nombre_red:
        return _cargar_snap_idioma("ES")
    return _cargar_snap_idioma("PT")


@st.cache_data(show_spinner="Calculando tabla de los 21 idiomas (SNAP 2018)...")
def cargar_tabla_idiomas():
    ruta_pre = Path("datos/salidas/comparativa_idiomas.csv")
    if ruta_pre.exists():
        return pd.read_csv(ruta_pre)

    ruta_feat = Path("datos/datos_twitch_2018/large_twitch_features.csv")
    ruta_edges = Path("datos/datos_twitch_2018/large_twitch_edges.csv")
    ruta_zip = Path("datos/datos_twitch_2018/twitch_gamers.zip")

    nodo_lang = {}
    nodos_por_lang = Counter()
    with abrir_csv_resiliente(ruta_feat, ruta_zip, "features") as ff:
        if ff is None:
            return None
        for fila in csv.DictReader(ff):
            nid = (fila.get("numeric_id") or fila.get("id") or "").strip()
            lg = (fila.get("language") or "OTHER").strip().upper()
            if nid:
                nodo_lang[nid] = lg
                nodos_por_lang[lg] += 1

    aristas_int = Counter()
    con_enlace = defaultdict(set)
    with abrir_csv_resiliente(ruta_edges, ruta_zip, "edges") as fe:
        if fe is None:
            return None
        lector = csv.reader(fe)
        next(lector, None)
        for fila in lector:
            if len(fila) < 2:
                continue
            u, v = fila[0].strip(), fila[1].strip()
            if u != v:
                lu, lv = nodo_lang.get(u), nodo_lang.get(v)
                if lu and lu == lv:
                    aristas_int[lu] += 1
                    con_enlace[lu].add(u)
                    con_enlace[lu].add(v)

    filas = []
    for lg, n in nodos_por_lang.most_common():
        m = aristas_int[lg]
        dens = (2.0 * m / (n * (n - 1)) * 100.0) if n > 1 else 0.0
        g_med = (2.0 * m / n) if n > 0 else 0.0
        aisl = n - len(con_enlace[lg])
        filas.append({
            "Idioma": lg,
            "Usuarios |V|": n,
            "Aristas internas |A|": m,
            "Densidad (%)": round(dens, 3),
            "Grado medio": round(g_med, 2),
            "Aislados": aisl,
        })
    return pd.DataFrame(filas)


# ==============================================================================
# PESTAÑAS PRINCIPALES
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "1. Explorador de Centralidad y Ataques",
    "2. Idiomas y Comparativa PT vs. ES",
    "3. Ajustes y Modelos (2018)",
    "4. Demostraciones Constructivas",
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: EXPLORADOR INTERACTIVO
# ------------------------------------------------------------------------------
with tab1:
    col_ctrl, col_vis = st.columns([1.05, 2.25])
    with col_ctrl:
        st.subheader("Configuración")
        red_sel = st.selectbox("1. Dataset / Corte temporal:", DATASETS)
        metrica = st.radio(
            "2. Centralidad (tamaño del nodo):",
            [
                "Grado (Popularidad directa)",
                "Intermediación (Canales puente)",
                "Vector propio (Núcleo cerrado)",
                "Cercanía (Velocidad de difusión)",
            ],
        )
        nodos_viz = st.slider(
            "3. Nodos del núcleo a dibujar:",
            25, 160, 90 if "2026" in red_sel else 50, step=5,
        )
        tipo_ataque = st.selectbox(
            "4. Simular fallo / ataque dirigido:",
            [
                "Sin ataque",
                "Ataque a Puentes (Top Intermediación)",
                "Ataque a Hubs (Top Grado)",
                "Fallo aleatorio",
            ],
        )
        k_eliminar = 0
        if tipo_ataque != "Sin ataque":
            k_eliminar = st.slider("Nodos a eliminar:", 1, 25, 10)

    G_base, idiomas_map, ok = cargar_grafo(red_sel)
    if not ok or G_base.number_of_nodes() == 0:
        st.error(f"No se encontraron los datos para **{red_sel}** dentro de `datos/`.")
    else:
        G_act = G_base.copy()
        borrados = []
        if k_eliminar > 0:
            if "Puentes" in tipo_ataque:
                top_tmp = [u for u, _ in sorted(G_act.degree, key=lambda x: x[1], reverse=True)[:300]]
                bet_tmp = nx.betweenness_centrality(G_act.subgraph(top_tmp))
                borrados = [u for u, _ in sorted(bet_tmp.items(), key=lambda x: x[1], reverse=True)[:k_eliminar]]
            elif "Hubs" in tipo_ataque:
                borrados = [u for u, _ in sorted(G_act.degree, key=lambda x: x[1], reverse=True)[:k_eliminar]]
            else:
                rng = random.Random(2026)
                borrados = rng.sample(list(G_act.nodes()), min(k_eliminar, G_act.number_of_nodes()))
            G_act.remove_nodes_from(borrados)

        comps = sorted(nx.connected_components(G_act), key=len, reverse=True)
        G_gig = G_act.subgraph(comps[0]).copy()
        top_sub = [u for u, _ in sorted(G_gig.degree, key=lambda x: x[1], reverse=True)[:nodos_viz]]
        G_sub = G_gig.subgraph(top_sub).copy()

        if "Grado" in metrica:
            dic_c = {u: float(G_gig.degree(u)) for u in G_gig.nodes()}
        elif "Vector propio" in metrica:
            dic_c = nx.eigenvector_centrality(G_gig, max_iter=600)
        elif "Intermediación" in metrica:
            dic_c = nx.betweenness_centrality(G_gig if G_gig.number_of_nodes() <= 400 else G_sub, normalized=True)
        else:
            dic_c = nx.closeness_centrality(G_gig if G_gig.number_of_nodes() <= 400 else G_sub)

        with col_ctrl:
            if borrados:
                st.warning(
                    f"Eliminados ({len(borrados)}): {', '.join(map(str, borrados[:6]))}"
                    + ("..." if len(borrados) > 6 else "")
                )
            st.markdown("**Top 10 según la centralidad elegida:**")
            top10 = sorted(dic_c.items(), key=lambda x: x[1], reverse=True)[:10]
            filas_top = []
            for u, val in top10:
                fila = {"Canal / ID": str(u), "Grado": G_gig.degree(u), "Valor": round(float(val), 4)}
                if idiomas_map:
                    fila["Idioma"] = idiomas_map.get(u, "-")
                filas_top.append(fila)
            st.dataframe(pd.DataFrame(filas_top), hide_index=True)

        with col_vis:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vértices activos |V|", f"{G_act.number_of_nodes():,}".replace(",", " "))
            m2.metric("Aristas activas |A|", f"{G_act.number_of_edges():,}".replace(",", " "))
            m3.metric("Componentes conexas", f"{len(comps)}")
            m4.metric("Clustering núcleo", f"{nx.average_clustering(G_sub):.3f}")

            fig, ax = plt.subplots(figsize=(9.5, 5.8), facecolor="white")
            pos = nx.spring_layout(G_sub, seed=2026, k=0.52)
            max_v = max((dic_c.get(u, 0.0) for u in G_sub.nodes()), default=1.0) or 1.0
            tams = [95 + 880 * (dic_c.get(u, 0.0) / max_v) for u in G_sub.nodes()]

            if "2026" in red_sel and idiomas_map:
                cols = [TW_PURPLE if idiomas_map.get(u, "ES") == "ES" else TW_GOLD for u in G_sub.nodes()]
                nx.draw_networkx_nodes(
                    G_sub, pos, node_size=tams, node_color=cols,
                    edgecolors=TW_DARK, linewidths=0.9, alpha=0.93, ax=ax,
                )
                ax.scatter([], [], c=TW_PURPLE, s=110, edgecolors=TW_DARK, label="Español (ES)")
                ax.scatter([], [], c=TW_GOLD, s=110, edgecolors=TW_DARK, label="Portugués (PT)")
                ax.legend(loc="upper right", frameon=True)
            else:
                coms_sub = list(greedy_modularity_communities(G_sub))
                mapa_com = {nodo: idx for idx, com in enumerate(coms_sub) for nodo in com}
                cols = [mapa_com.get(u, 0) for u in G_sub.nodes()]
                nx.draw_networkx_nodes(
                    G_sub, pos, node_size=tams, node_color=cols,
                    cmap=plt.cm.Purples, edgecolors=TW_DARK, linewidths=1.0, alpha=0.92, ax=ax,
                )

            nx.draw_networkx_edges(G_sub, pos, alpha=0.18, edge_color="#666677", ax=ax)

            etiq_top = [
                u for u, _ in sorted(
                    ((u, dic_c.get(u, 0.0)) for u in G_sub.nodes()), key=lambda x: x[1], reverse=True
                )[:14]
            ]
            nx.draw_networkx_labels(
                G_sub, pos, labels={u: str(u) for u in etiq_top},
                font_size=8.5, font_weight="bold",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.80, pad=1.0),
                ax=ax,
            )
            ax.set_title(
                f"{red_sel} — Tamaño por {metrica.split(' (')[0]}",
                fontsize=11, fontweight="bold", color=TW_DARK,
            )
            ax.axis("off")
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

# ------------------------------------------------------------------------------
# PESTAÑA 2: IDIOMAS Y COMPARATIVA PT vs ES
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("Frontera lingüística: SNAP 2018 (21 idiomas) frente a Captura 2026")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aristas globales (2018)", "6 797 557")
    c2.metric("Mismo idioma (2018)", "90,00 %", delta="+16,69 % vs. azar")
    c3.metric("Assortatividad Newman (r)", "0,6254")
    c4.metric("Mismo idioma (Captura 2026)", "88,82 %")

    col_iz, col_de = st.columns([1.05, 1.35])
    with col_iz:
        st.markdown("#### Comparativa estructural: Portugués (`PT`) vs. Español (`ES`)")
        df_ptes = pd.DataFrame([
            ("Vértices |V| / Aristas |A|", "2 536 / 42 952", "5 699 / 85 893"),
            ("Densidad", "1,336 %", "0,529 %"),
            ("Grado medio / Mediana / Máx.", "33,87 / 17 / 880", "30,14 / 14 / 1 131"),
            ("Aislados / Componentes", "90 / 93", "161 / 169"),
            ("Vértices de corte / Puentes", "108 / 136", "252 / 295"),
            ("Radio / Diámetro / Centro", "4 / 7 / 144 nodos", "4 / 8 / 4 nodos"),
            ("Distancia media (BFS)", "2,641 saltos", "2,872 saltos"),
            ("Clustering real vs. GNP", "0,3031 (22,3×)", "0,2247 (40,9×)"),
            ("Paradoja de la Amistad", "93,9 %", "95,0 %"),
            ("Comunidades / Modularidad Q", "15 / 0,2529", "31 / 0,3862"),
            ("Clique núcleo (Top 150)", "K_18", "K_18"),
            ("Ataque Top 20 (Azar / Autov. / Puen.)", "3 / 34 / 36 comp.", "1 / 27 / 54 comp."),
        ], columns=["Medida", "PT (2018)", "ES (2018)"])
        st.dataframe(df_ptes, hide_index=True)

    with col_de:
        st.markdown("#### Los 21 idiomas de SNAP 2018")
        df_id = cargar_tabla_idiomas()
        if df_id is not None:
            st.dataframe(df_id, hide_index=True, height=450)
        else:
            st.info("No se encontraron los ficheros de SNAP 2018 para generar la tabla.")

# ------------------------------------------------------------------------------
# PESTAÑA 3: AJUSTES Y MODELOS (2018)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("Ajustes por mínimos cuadrados y contraste con modelos aleatorios")
    idioma_graf = st.radio("Seleccionar comunidad de 2018:", ["Español (ES 2018)", "Portugués (PT 2018)"], horizontal=True)
    col_a, col_b = st.columns(2)

    if "Español" in idioma_graf:
        df_sse = pd.DataFrame([
            {"Modelo": "Potencial Desplazado: a·|x - c|^b", "SSE": 4443.64, "Detalle": "b = -3,642; c = -44,17"},
            {"Modelo": "Exponencial: a·e^(bx)", "SSE": 8285.93, "Detalle": "Decae muy rápido en la cola"},
            {"Modelo": "Potencial Puro: a·x^b", "SSE": 121535.01, "Detalle": "Penalizado por recorte en k < 15"},
        ])
        df_mod = pd.DataFrame([
            {"Modelo": "Twitch ES (Real)", "Aristas": 85893, "G. Medio": 30.14, "Clustering": 0.2247},
            {"Modelo": "Holme–Kim (m=15)", "Aristas": 85052, "G. Medio": 29.85, "Clustering": 0.0871},
            {"Modelo": "Barabási–Albert (m=15)", "Aristas": 85260, "G. Medio": 29.92, "Clustering": 0.0224},
            {"Modelo": "Erdős–Rényi GNP", "Aristas": 85724, "G. Medio": 30.08, "Clustering": 0.0055},
        ])
        img1, img2 = Path("datos/salidas/grafica_ES_2_ajustes.png"), Path("datos/salidas/grafica_ES_3_modelos.png")
    else:
        df_sse = pd.DataFrame([
            {"Modelo": "Potencial Desplazado: a·|x - c|^b", "SSE": 2677.55, "Detalle": "b = -2,825; c = -39,29"},
            {"Modelo": "Exponencial: a·e^(bx)", "SSE": 3469.86, "Detalle": "Decae muy rápido en la cola"},
            {"Modelo": "Potencial Puro: a·x^b", "SSE": 14984.01, "Detalle": "Penalizado por recorte en k < 15"},
        ])
        df_mod = pd.DataFrame([
            {"Modelo": "Twitch PT (Real)", "Aristas": 42952, "G. Medio": 33.87, "Clustering": 0.3031},
            {"Modelo": "Holme–Kim (m=17)", "Aristas": 42609, "G. Medio": 33.60, "Clustering": 0.1101},
            {"Modelo": "Barabási–Albert (m=17)", "Aristas": 42823, "G. Medio": 33.77, "Clustering": 0.0436},
            {"Modelo": "Erdős–Rényi GNP", "Aristas": 43107, "G. Medio": 34.00, "Clustering": 0.0136},
        ])
        img1, img2 = Path("datos/salidas/grafica_2_ajustes_PT.png"), Path("datos/salidas/grafica_3_modelos_PT.png")

    with col_a:
        st.dataframe(df_sse, hide_index=True)
        if img1.exists():
            st.image(str(img1))
        else:
            fig_s, ax_s = plt.subplots(figsize=(5.5, 3.4), facecolor="white")
            ax_s.bar(["Pot. Desplazado", "Exponencial", "Pot. Puro"], df_sse["SSE"], color=[TW_PURPLE, TW_LIGHT_PURPLE, "#BDBDCA"])
            ax_s.set_ylabel("Error cuadrático total (SSE)")
            ax_s.set_title(f"Comparativa SSE ({idioma_graf})")
            st.pyplot(fig_s)
            plt.close(fig_s)

    with col_b:
        st.dataframe(df_mod, hide_index=True)
        if img2.exists():
            st.image(str(img2))
        else:
            fig_m, ax_m = plt.subplots(figsize=(5.5, 3.4), facecolor="white")
            ax_m.bar(["Real", "Holme–Kim", "Barabási–Albert", "GNP"], df_mod["Clustering"], color=[TW_PURPLE, TW_LIGHT_PURPLE, "#8E8E9E", "#C8C8D4"])
            ax_m.set_ylabel("Clustering medio")
            ax_m.set_title(f"Clustering: Red real vs. Modelos ({idioma_graf})")
            st.pyplot(fig_m)
            plt.close(fig_m)

# ------------------------------------------------------------------------------
# PESTAÑA 4: DEMOSTRACIONES CONSTRUCTIVAS
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("Demostraciones constructivas interactivas")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. Corte de Puentes (Girvan–Newman)")
        cortar = st.checkbox("Eliminar arista puente (3, 4) [16 caminos]", value=False)
        Gd = nx.Graph([(0,1),(0,2),(1,2),(1,3),(2,3),(3,4),(4,5),(4,6),(5,6),(5,7),(6,7)])
        if cortar:
            Gd.remove_edge(3, 4)
        fig1, ax1 = plt.subplots(figsize=(4.8, 3.4), facecolor="white")
        pos1 = {0:(-2.2,1), 1:(-1.3,1.65), 2:(-1.3,0.35), 3:(-0.5,1), 4:(0.5,1), 5:(1.3,1.65), 6:(1.3,0.35), 7:(2.2,1)}
        cols_gn = [TW_PURPLE if n < 4 else TW_DARK for n in Gd.nodes()]
        nx.draw(
            Gd, pos1, with_labels=True, node_color=cols_gn, font_color="white",
            node_size=450, edge_color="#8E8E9E", width=2, font_weight="bold", ax=ax1,
        )
        ax1.set_xlim(-2.6, 2.6)
        st.pyplot(fig1)
        plt.close(fig1)
        st.caption(f"Componentes conexas: {[len(c) for c in nx.connected_components(Gd)]}")

    with col2:
        st.markdown("#### 2. Proyección Bipartita → Clique $K_k$")
        k_proy = st.slider("Canales que comparte un grupo de espectadores (k):", 3, 6, 4)
        Gp = nx.complete_graph(k_proy)
        fig2, ax2 = plt.subplots(figsize=(4.8, 3.4), facecolor="white")
        nx.draw_circular(
            Gp, with_labels=True, labels={i: f"S{i+1}" for i in range(k_proy)},
            node_color=TW_PURPLE, font_color="white", node_size=550,
            edge_color=TW_DARK_PURPLE, width=2, font_weight="bold", ax=ax2,
        )
        st.pyplot(fig2)
        plt.close(fig2)
        st.caption(f"Induce un clique K_{k_proy} ({k_proy*(k_proy-1)//2} aristas, clustering = 1,0).")

    with col3:
        st.markdown("#### 3. Havel–Hakimi (6 mayores Hubs 2018)")
        sel_hh = st.radio("Subgrafo inducido:", ["Español (ES)", "Portugués (PT)"], horizontal=True)
        if "Español" in sel_hh:
            st.write("IDs: `[25951, 31958, 151558, 8555, 151200, 49235]`")
            st.code("Paso 0: [5, 5, 3, 3, 2, 2]\nPaso 1: [4, 2, 2, 1, 1]\nPaso 2: [1, 1, 0, 0]\nPaso 3: [0, 0, 0]  -> Gráfica")
        else:
            st.write("IDs: `[122266, 161540, 55969, 128589, 160961, 50779]`")
            st.code("Paso 0: [4, 4, 4, 4, 4, 2]\nPaso 1: [3, 3, 3, 3, 2]\nPaso 2: [2, 2, 2, 2]\nPaso 3: [2, 1, 1]\nPaso 4: [0, 0]     -> Gráfica")