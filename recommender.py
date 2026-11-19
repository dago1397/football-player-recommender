"""Paso 2: perfiles de jugador y recomendador por similitud coseno.

Dos variantes:
  * "original": replica la lógica del Excel del TFM (promedio con ceros en los faltantes, temporadas contadas
    como filas, variables originales por posición, vectores normalizados por fila y similitud coseno SIN
    escalar las columnas).
  * "v2": misma idea, con correcciones: temporadas distintas, promedios que ignoran faltantes, totales de
    temporada pasados a "por 90", selección de variables recalculada, imputación por mediana de la posición y
    StandardScaler por columna antes del coseno.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from config import (ACTIVE_SEASONS, DATA_PROCESSED, PER90_FROM_COUNTS, RATE_COLUMNS, ROOT, SEASON_PENALTY,
                    SEASON_TOTALS_TO_PER90, TOP_N)

POSITIONS = ["DL", "CC", "DF"]           # delanteros, mediocampistas, defensas (porteros "PO" excluidos)
ORIGINAL_STATS = RATE_COLUMNS + [f"{c} P90" for c in PER90_FROM_COUNTS]    # 104 estadísticas del TFM
ADVANCED_CHECK = ["Int. Total P90", "Tkl P90", "SCA90", "Toques"]           # bloques que faltan en 2.ª división


def load_player_seasons() -> pd.DataFrame:
    path = DATA_PROCESSED / "player_seasons.csv"
    if not path.exists():
        raise FileNotFoundError("Primero ejecuta: python prepare_data.py")
    df = pd.read_csv(path)
    # Identificador: el nombre; si dos jugadores distintos comparten nombre, se agrega el país.
    n_countries = df.groupby("Jugador")["País"].transform("nunique")
    df["player_id"] = np.where(n_countries > 1, df["Jugador"] + " (" + df["País"].fillna("?") + ")",
                               df["Jugador"])
    df["primary_pos"] = df["Posc"].astype(str).str.split(",").str[0]
    return df


def season_penalty(n_seasons: pd.Series) -> pd.Series:
    return n_seasons.map(lambda n: SEASON_PENALTY.get(int(n), 1.0))


def v2_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Totales de temporada -> por 90. xG, npxG, xAG y npxG+xAG se eliminan porque ya existen en versión P90."""
    df = df.copy()
    stats = [c for c in ORIGINAL_STATS if c not in SEASON_TOTALS_TO_PER90]
    for col in ["xA", "G-xG", "np:G-xG", "A-xAG"]:
        df[f"{col} P90"] = df[col] / df["90 s"]
        stats.append(f"{col} P90")
    return df, stats


@dataclass
class Model:
    name: str
    profiles: pd.DataFrame              # info + estadísticas ponderadas por jugador
    percentiles: pd.DataFrame           # percentil (0-1) de cada jugador en cada estadística
    features: dict[str, list[str]]      # variables usadas por posición
    similarity: dict[str, pd.DataFrame] = field(default_factory=dict)

    def recommend(self, player: str, n: int = TOP_N, active_only: bool = True) -> pd.DataFrame:
        if player not in self.profiles.index:
            raise KeyError(f"Jugador no encontrado: {player}")
        pos = self.profiles.at[player, "position"]
        if pos not in self.similarity:
            raise ValueError(f"{player} es portero o no tiene posición recomendable ({pos})")
        sims = self.similarity[pos][player].drop(player)
        cand = self.profiles.loc[sims.index]
        if active_only:
            sims = sims[cand["last_season"].isin(ACTIVE_SEASONS)]
        top = sims.sort_values(ascending=False).head(n)
        cols = ["last_team", "last_league", "last_season", "age", "n_seasons"]
        out = self.profiles.loc[top.index, cols].copy()
        out.insert(0, "similarity", top.round(4))
        out.index.name = "player"
        return out


def _player_info(df: pd.DataFrame, n_seasons: pd.Series) -> pd.DataFrame:
    last = df.sort_values(["Temporada", "Mín"]).groupby("player_id").tail(1).set_index("player_id")
    pos = (df[df["primary_pos"].isin(POSITIONS + ["PO"])]
           .groupby(["player_id", "primary_pos"]).size().rename("n").reset_index()
           .sort_values(["player_id", "n"], ascending=[True, False])
           .drop_duplicates("player_id").set_index("player_id")["primary_pos"])
    info = pd.DataFrame({"name": last["Jugador"], "position": pos, "n_seasons": n_seasons,
                         "last_season": last["Temporada"], "last_team": last["Equipo"],
                         "last_league": last["Liga"], "age": last["Edad"]})
    info["penalty"] = season_penalty(info["n_seasons"])
    return info


def _select_features(pct: pd.DataFrame, positions: pd.Series, threshold: float = 0.6) -> dict[str, list[str]]:
    """Variables cuyo percentil promedio en la posición supera el 60% (regla del TFM)."""
    means = pct.groupby(positions).mean()
    return {p: [c for c in pct.columns if means.at[p, c] > threshold] for p in POSITIONS}


def build_original(df: pd.DataFrame) -> Model:
    stats = ORIGINAL_STATS
    n_rows = df.groupby("player_id").size()                       # el Excel contaba filas, no temporadas
    info = _player_info(df, n_rows)
    avg = df[stats].fillna(0).groupby(df["player_id"]).mean()     # faltantes = 0, como en el Excel
    weighted = avg.mul(info["penalty"], axis=0)
    pct = weighted.rank(pct=True)
    with open(ROOT / "original_features.json", encoding="utf-8") as f:
        features = json.load(f)
    model = Model("original", info.join(weighted), pct, features)
    for pos in POSITIONS:
        ids = info.index[info["position"] == pos]
        X = weighted.loc[ids, features[pos]].to_numpy()
        model.similarity[pos] = pd.DataFrame(cosine_similarity(X), index=ids, columns=ids)  # L2 por fila
    return model


def build_v2(df: pd.DataFrame) -> Model:
    df, stats = v2_stats(df)
    n_seasons = df.groupby("player_id")["Temporada"].nunique()
    info = _player_info(df, n_seasons)
    avg = df[stats].groupby(df["player_id"]).mean()               # ignora faltantes (NaN)
    has_adv = df.groupby("player_id")["Int. Total P90"].apply(lambda s: s.notna().any())
    info["has_advanced"] = has_adv
    weighted = avg.mul(info["penalty"], axis=0)
    pct = weighted.rank(pct=True)
    eligible = info.index[info["has_advanced"] & info["position"].isin(POSITIONS)]
    features = _select_features(pct.loc[eligible], info.loc[eligible, "position"])
    model = Model("v2", info.join(weighted), pct, features)
    for pos in POSITIONS:
        ids = info.index[(info["position"] == pos) & info["has_advanced"]]
        X = weighted.loc[ids, features[pos]]
        X = X.fillna(X.median())                                   # imputación por mediana de la posición
        Xs = StandardScaler().fit_transform(X)                     # escalado por columna (z-score)
        model.similarity[pos] = pd.DataFrame(cosine_similarity(Xs), index=ids, columns=ids)
    return model


def build_models() -> tuple[pd.DataFrame, Model, Model]:
    df = load_player_seasons()
    return df, build_original(df), build_v2(df)


if __name__ == "__main__":
    import sys
    _, orig, v2 = build_models()
    player = sys.argv[1] if len(sys.argv) > 1 else "İlkay Gündoğan"
    for m in (orig, v2):
        print(f"\n=== {m.name}: top {TOP_N} para {player} ===")
        print(m.recommend(player).to_string())
