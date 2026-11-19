"""Paso 1: une las 9 tablas de FBref y genera la base jugador-temporada.

Reproduce los notebooks originales `Juntar Archivos` + `Agrupación EStadísticas`, con dos correcciones:
  1. Se eliminan filas duplicadas en cada tabla ANTES de unirlas (en el original el merge multiplicaba filas).
  2. Las claves repetidas que no son duplicados exactos (homónimos en el mismo equipo y temporada) se
     descartan y se reportan, en vez de generar combinaciones cruzadas.

Uso:  python prepare_data.py
Entrada: data/raw/*.xlsx   Salida: data/processed/player_seasons.csv
"""
import pandas as pd

from config import DATA_PROCESSED, DATA_RAW, KEYS, MIN_90S, PER90_FROM_COUNTS, RATE_COLUMNS, SEASONS, TABLES


def load_table(file_name: str, columns: list[str], log: dict) -> pd.DataFrame:
    path = DATA_RAW / file_name
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}. Revisa la sección 'Datos' del README.")
    df = pd.read_excel(path)
    df = df[df["Temporada"].isin(SEASONS)]
    df = df[~df["Jugador"].isin(["Total del equipo", "Total del oponente"])]
    df = df[KEYS + [c for c in columns if c in df.columns]]
    n0 = len(df)
    df = df.drop_duplicates()
    n_exact = n0 - len(df)
    dup_mask = df.duplicated(KEYS, keep=False)
    n_ambiguous = int(dup_mask.sum())
    df = df[~dup_mask]
    log[file_name] = {"filas_temporadas_objetivo": n0, "duplicados_exactos": n_exact,
                      "claves_ambiguas_descartadas": n_ambiguous, "filas_finales": len(df)}
    return df


def build_player_seasons() -> tuple[pd.DataFrame, dict]:
    log: dict = {}
    tables = {name: load_table(name, cols, log) for name, cols in TABLES.items()}
    base = tables.pop("Estandar_Total.xlsx")
    n_base = len(base)
    for name, df in tables.items():
        base = base.merge(df, on=KEYS, how="left", validate="one_to_one")
    assert len(base) == n_base, "El merge no debe crear filas nuevas"
    log["filas_tras_merge"] = len(base)

    base = base[base["Mín"] > 0].copy()
    log["filas_min_mayor_0"] = len(base)

    info = base[KEYS + ["Liga", "País", "Posc", "Edad", "PJ", "Titular", "Mín", "90 s", "Gls.", "Ass"]]
    per90 = base[PER90_FROM_COUNTS].div(base["90 s"], axis=0).add_suffix(" P90")
    out = pd.concat([info, base[RATE_COLUMNS], per90], axis=1)

    out = out[out["90 s"] > MIN_90S].reset_index(drop=True)
    log["filas_finales_90s_mayor_5"] = len(out)
    log["jugadores_unicos"] = out["Jugador"].nunique()
    return out, log


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    df, log = build_player_seasons()
    df.to_csv(DATA_PROCESSED / "player_seasons.csv", index=False)
    pd.Series(log, dtype=object).to_json(DATA_PROCESSED / "prepare_log.json", force_ascii=False, indent=1)
    for k, v in log.items():
        print(f"{k}: {v}")
    print(f"Guardado: {DATA_PROCESSED / 'player_seasons.csv'}  ({df.shape[0]} filas x {df.shape[1]} columnas)")


if __name__ == "__main__":
    main()
