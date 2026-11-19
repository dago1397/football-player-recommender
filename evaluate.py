"""Paso 3: evaluación Precision@20 (original vs 2.0), igual que en el TFM.

Relevancia (definida por el autor, no hay datos reales de qué fichaje es "bueno"):
  gap = promedio de |percentil del recomendado - percentil del jugador elegido| sobre las variables de la posición.
  La recomendación es relevante si gap < límite (10%, 15% o 20%).
Precision@20 = recomendaciones relevantes / 20.

OJO: la métrica es circular (usa los mismos datos que el modelo). Sirve para comparar variantes, no para
afirmar que las recomendaciones son buenas en la realidad. Se reportan dos "reglas de medir":
  * "TFM": variables y percentiles del modelo original (la definición del proyecto).
  * "2.0": variables y percentiles del modelo 2.0.

Uso:  python evaluate.py      Salida: evaluation_results.csv, evaluation_by_player.csv
"""
import numpy as np
import pandas as pd

from config import ROOT, TOP_N
from recommender import POSITIONS, Model, build_models

THRESHOLDS = [0.10, 0.15, 0.20]


def eval_players(orig: Model, v2: Model) -> list[str]:
    names = pd.read_csv(ROOT / "eval_players.csv")["Jugador"].drop_duplicates()
    ok = []
    for name in names:
        if (name in orig.profiles.index and name in v2.profiles.index
                and orig.profiles.at[name, "position"] in POSITIONS
                and name in orig.similarity[orig.profiles.at[name, "position"]].index
                and v2.profiles.at[name, "position"] in v2.similarity
                and name in v2.similarity[v2.profiles.at[name, "position"]].index):
            ok.append(name)
    return ok


def gap(pct: pd.DataFrame, features: list[str], a: str, b: str) -> float:
    return float(np.nanmean(np.abs(pct.loc[a, features].to_numpy() - pct.loc[b, features].to_numpy())))


def evaluate(models: list[Model], yardsticks: dict[str, Model], players: list[str]) -> pd.DataFrame:
    rows = []
    for model in models:
        for p in players:
            recs = model.recommend(p, n=TOP_N).index
            pos = model.profiles.at[p, "position"]
            for ys_name, ys in yardsticks.items():
                ys_pos = ys.profiles.at[p, "position"]
                feats = ys.features[ys_pos]
                gaps = [gap(ys.percentiles, feats, p, r) for r in recs]
                for t in THRESHOLDS:
                    rows.append({"model": model.name, "yardstick": ys_name, "player": p, "position": pos,
                                 "threshold": t, "precision_at_20": np.mean([g < t for g in gaps]),
                                 "mean_gap": np.mean(gaps), "n_recs": len(recs)})
    return pd.DataFrame(rows)


def summarize(res: pd.DataFrame) -> pd.DataFrame:
    by_pos = res.groupby(["yardstick", "model", "position", "threshold"])["precision_at_20"].mean()
    total = res.groupby(["yardstick", "model", "threshold"])["precision_at_20"].mean()
    total = pd.concat({"TOTAL": total}, names=["position"]).reorder_levels([1, 2, 0, 3])
    out = pd.concat([by_pos, total]).unstack("threshold").round(3)
    out.columns = [f"P@20 <{int(t*100)}%" for t in out.columns]
    n = res.drop_duplicates(["yardstick", "model", "player"]).groupby(["yardstick", "model", "position"]).size()
    n_tot = res.drop_duplicates(["yardstick", "model", "player"]).groupby(["yardstick", "model"]).size()
    n_tot = pd.concat({"TOTAL": n_tot}, names=["position"]).reorder_levels([1, 2, 0])
    out["n_players"] = pd.concat([n, n_tot])
    return out.sort_index()


def main() -> None:
    _, orig, v2 = build_models()
    players = eval_players(orig, v2)
    print(f"Jugadores evaluados: {len(players)} (lista del TFM, sin porteros ni jugadores sin datos avanzados)")
    res = evaluate([orig, v2], {"TFM": orig, "2.0": v2}, players)
    res.to_csv(ROOT / "evaluation_by_player.csv", index=False)
    summary = summarize(res)
    summary.to_csv(ROOT / "evaluation_results.csv")
    print(summary.to_string())
    sims = {m.name: np.mean([m.recommend(p).similarity.mean() for p in players]) for m in (orig, v2)}
    print("Similitud coseno promedio del top-20:", {k: round(v, 4) for k, v in sims.items()})


if __name__ == "__main__":
    main()
