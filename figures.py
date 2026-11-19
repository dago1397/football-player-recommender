"""Paso 4: genera las imágenes del README (images/*.png). Requiere haber corrido evaluate.py.

Uso:  python figures.py ["Nombre del jugador"]
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from config import IMAGES, ROOT
from recommender import POSITIONS, Model, build_models

POS_LABEL = {"DL": "Delanteros", "CC": "Mediocampistas", "DF": "Defensas"}

RADAR_VARS = {
    "CC": ["PrgP P90", "PC P90", "PPA P90", "SCA90", "xA P90", "T/90", "Succ P90", "1/3 P90",
           "Tkl+Int P90", "Recup. P90", "Pases P90", "Pérdida P90"],
    "DL": ["npxG P90", "Gls. P90", "xAG P90", "SCA90", "T/90", "% de TT", "PrgR P90", "Succ P90",
           "Ataq. pen. P90", "PC P90", "Fls P90", "Duel_Aer Perdidos P90"],
    "DF": ["Int P90", "Tkl+Int P90", "Desp. P90", "Bloqueos P90", "Duel_Aer Ganados P90", "% Del_Aer ganados",
           "Dist. prg. P90", "Cmp Largo P90", "Int. Total P90", "Tkl%", "Def. pen. P90", "Balón vivo P90"],
}


def radar(model: Model, player: str, others: list[str], path) -> None:
    pos = model.profiles.at[player, "position"]
    vars_ = [v for v in RADAR_VARS[pos] if v in model.percentiles.columns]
    angles = np.linspace(0, 2 * np.pi, len(vars_), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
    colors = ["#1f3b73", "#e07a1f", "#2a9d8f", "#c0392b"]
    for name, color in zip([player] + others, colors):
        vals = (model.percentiles.loc[name, vars_].fillna(0.5) * 100).tolist()
        vals += vals[:1]
        ax.plot(angles, vals, color=color, linewidth=2, label=name)
        ax.fill(angles, vals, color=color, alpha=0.12)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(vars_, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_rlabel_position(100)
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["25", "50", "75", "100"], fontsize=8, color="grey")
    ax.set_title(f"Percentiles: {player} vs. sus 3 primeras recomendaciones (modelo 2.0)", fontsize=12, pad=30)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def precision_chart(summary: pd.DataFrame, path, yardstick: str = "TFM") -> None:
    cols = [c for c in summary.columns if c.startswith("P@20")]
    groups = POSITIONS + ["TOTAL"]
    fig, axes = plt.subplots(1, len(cols), figsize=(14, 4.6), sharey=True)
    x = np.arange(len(groups))
    for ax, col in zip(axes, cols):
        for j, (model, color, label) in enumerate([("original", "#9aa5b1", "Original (sin escalar)"),
                                                   ("v2", "#1f3b73", "2.0 (escalado)")]):
            vals = [summary.loc[(yardstick, model, g), col] * 100 for g in groups]
            bars = ax.bar(x + (j - 0.5) * 0.38, vals, 0.38, color=color, label=label)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([POS_LABEL.get(g, "Total") for g in groups], fontsize=9)
        ax.set_title(f"Límite de relevancia {col[5:]}")
        ax.set_ylim(0, 110)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Precision@20 (%)")
    axes[0].legend(loc="upper left", fontsize=8)
    n = int(summary.loc[(yardstick, "v2", "TOTAL"), "n_players"])
    fig.suptitle(f"Precision@20 original vs 2.0 por posición ({n} jugadores, relevancia con la definición del TFM)",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def dominance_chart(orig: Model, v2: Model, path) -> pd.DataFrame:
    """Qué parte de la longitud del vector (norma al cuadrado) aporta la variable más grande."""
    rows = []
    for pos in POSITIONS:
        ids_o = orig.similarity[pos].index
        Xo = orig.profiles.loc[ids_o, orig.features[pos]].fillna(0).to_numpy(float)
        sq = Xo ** 2
        share_o = (sq / sq.sum(1, keepdims=True).clip(1e-12)).mean(0)
        ids_v = v2.similarity[pos].index
        Xv = v2.profiles.loc[ids_v, v2.features[pos]]
        Xv = StandardScaler().fit_transform(Xv.fillna(Xv.median()))
        sq = Xv ** 2
        share_v = (sq / sq.sum(1, keepdims=True).clip(1e-12)).mean(0)
        io, iv = share_o.argmax(), share_v.argmax()
        rows.append({"position": pos, "original_top_var": orig.features[pos][io],
                     "original_share": share_o[io], "v2_top_var": v2.features[pos][iv], "v2_share": share_v[iv]})
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(df))
    ax.bar(x - 0.2, df["original_share"] * 100, 0.4, color="#9aa5b1", label="Original (sin escalar)")
    ax.bar(x + 0.2, df["v2_share"] * 100, 0.4, color="#1f3b73", label="2.0 (StandardScaler)")
    for i, r in df.iterrows():
        ax.text(i - 0.2, r.original_share * 100 + 1.5, f"{r.original_top_var}\n{r.original_share*100:.0f}%", ha="center", fontsize=8)
        ax.text(i + 0.2, r.v2_share * 100 + 1.5, f"{r.v2_share*100:.0f}%", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([POS_LABEL[p] for p in df["position"]])
    ax.set_ylabel("% de la norma² aportado por la variable dominante")
    ax.set_ylim(0, 100)
    ax.set_title("Peso de la variable más grande en la similitud coseno")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return df


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    player = sys.argv[1] if len(sys.argv) > 1 else "İlkay Gündoğan"
    _, orig, v2 = build_models()
    top = v2.recommend(player).index[:3].tolist()
    radar(v2, player, top, IMAGES / "radar_gundogan.png")
    summary = pd.read_csv(ROOT / "evaluation_results.csv", index_col=[0, 1, 2])
    precision_chart(summary, IMAGES / "precision_comparison.png")
    dom = dominance_chart(orig, v2, IMAGES / "feature_dominance.png")
    print(dom.round(3).to_string())
    print("Imágenes en", IMAGES)


if __name__ == "__main__":
    main()
