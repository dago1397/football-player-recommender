"""App opcional (Streamlit): elige un jugador y mira su top 20 y el radar de percentiles.

Uso:  streamlit run app.py      (requiere data/processed/player_seasons.csv; ver README)
"""
import matplotlib
matplotlib.use("Agg")
import streamlit as st

from config import DATA_PROCESSED, TOP_N
from figures import POS_LABEL, RADAR_VARS
from recommender import POSITIONS, build_models

st.set_page_config(page_title="Recomendador de jugadores", layout="wide")
st.title("⚽ Recomendador de jugadores de fútbol")
st.caption("Top 5 ligas europeas, temporadas 2017-18 a 2022-23. Datos de FBref (2023), solo uso local.")

if not (DATA_PROCESSED / "player_seasons.csv").exists():
    st.error("No encuentro data/processed/player_seasons.csv. Coloca los datos en data/raw/ y ejecuta "
             "`python prepare_data.py` (ver README).")
    st.stop()


@st.cache_resource(show_spinner="Construyendo los modelos...")
def load():
    _, orig, v2 = build_models()
    return {"2.0 (escalado)": v2, "Original (TFM)": orig}


models = load()
choice = st.sidebar.radio("Modelo", list(models))
model = models[choice]
prof = model.profiles
pool = prof[prof.index.isin(set().union(*[set(model.similarity[p].index) for p in POSITIONS]))]
pool = pool[pool["last_season"] == "2022-2023"]

league = st.sidebar.selectbox("Liga (2022-23)", sorted(pool["last_league"].dropna().unique()))
team = st.sidebar.selectbox("Equipo", sorted(pool.loc[pool["last_league"] == league, "last_team"].unique()))
players = pool[(pool["last_league"] == league) & (pool["last_team"] == team)].sort_index()
player = st.sidebar.selectbox("Jugador", players.index,
                              format_func=lambda p: f"{p} ({POS_LABEL.get(prof.at[p, 'position'], '')})")

recs = model.recommend(player, n=TOP_N)
col1, col2 = st.columns([1.1, 1])
with col1:
    st.subheader(f"Top {TOP_N} parecidos a {player}")
    st.dataframe(recs.rename(columns={"similarity": "similitud", "last_team": "equipo", "last_league": "liga",
                                      "last_season": "temporada", "age": "edad", "n_seasons": "temporadas"}),
                 width="stretch", height=740)
with col2:
    other = st.selectbox("Comparar con", recs.index)
    import matplotlib.pyplot as plt
    import numpy as np
    pos = prof.at[player, "position"]
    vars_ = [v for v in RADAR_VARS[pos] if v in model.percentiles.columns]
    ang = np.linspace(0, 2 * np.pi, len(vars_), endpoint=False).tolist()
    ang += ang[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
    for name, color in [(player, "#1f3b73"), (other, "#e07a1f")]:
        vals = (model.percentiles.loc[name, vars_].fillna(0.5) * 100).tolist()
        vals += vals[:1]
        ax.plot(ang, vals, color=color, linewidth=2, label=name)
        ax.fill(ang, vals, color=color, alpha=0.15)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(vars_, fontsize=8)
    ax.set_ylim(0, 100)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2)
    st.pyplot(fig)
    st.caption("Percentil (0-100) de cada estadística frente a todos los jugadores de la base.")
