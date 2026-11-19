"""LEGADO (2023): bot de web scraping de FBref usado para construir los datos del proyecto.

AVISO: este script ya NO funciona tal cual. En enero de 2026 FBref eliminó las estadísticas avanzadas
(xG, pases, creación de goles, defensa, posesión, etc.) porque su proveedor (Opta / Stats Perform)
terminó el acuerdo de datos. Además, en noviembre de 2026 FBref responde 403 (prohibido) a este tipo de
solicitudes automatizadas. Se conserva como código histórico para mostrar cómo se obtuvieron los datos en 2023.
Es la versión limpia del notebook original `Proyecto Final.ipynb`: rutas relativas, configuración
separada, manejo de errores explícito y pausas entre solicitudes.

Si lo adaptas a otra fuente, respeta sus términos de uso y límites de tráfico. FBref (Sports Reference)
bloquea a quien haga más de 10 solicitudes por minuto: https://www.sports-reference.com/bot-traffic.html

Uso histórico:
    python scraper_fbref_legacy.py
"""
from __future__ import annotations

import logging
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT_DIR = Path(__file__).resolve().parent / "data" / "raw_legacy"
BASE = "https://fbref.com/es/equipos"
PAUSE_SECONDS = 7           # ~8 solicitudes por minuto, por debajo del límite de FBref
HEADERS = {"User-Agent": "Mozilla/5.0 (proyecto academico IEBS; uso no comercial)"}

# Tablas que se descargaban: id de la tabla en la página "todas las competencias" -> nombre del archivo
TABLES = {
    "stats_standard_combined": "Estandar",
    "stats_shooting_combined": "Tiros",
    "stats_passing_combined": "Pases",
    "stats_passing_types_combined": "Tipo_Pases",
    "stats_gca_combined": "Crea_Gol",
    "stats_defense_combined": "Defensa",
    "stats_possession_combined": "Posecion",
    "stats_playing_time_combined": "Tiempo_jugado",
    "stats_misc_combined": "Variadas",
}

# Ejemplo de configuración (en el proyecto se corrió liga por liga con ~20 equipos cada una).
# (nombre del equipo en la URL de FBref, código del equipo en FBref, sufijo de la liga en las tablas)
TEAMS = {
    "La Liga": [("Barcelona", "206d90db", "_12")],
}
SEASONS = ["2017-2018", "2018-2019", "2019-2020", "2020-2021", "2021-2022", "2022-2023"]

log = logging.getLogger("scraper")


def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Fallo la solicitud %s: %s", url, exc)
        return None
    finally:
        time.sleep(PAUSE_SECONDS)
    return BeautifulSoup(resp.text, "html.parser")


def parse_table(soup: BeautifulSoup | None, table_id: str) -> pd.DataFrame | None:
    if soup is None:
        return None
    html = soup.find("table", {"id": table_id})
    if html is None:
        return None
    df = pd.read_html(StringIO(str(html)))[0]
    if isinstance(df.columns, pd.MultiIndex):
        df = df.droplevel(0, axis=1)
    return df


def scrape_team_season(team: str, code: str, comp_suffix: str, season: str) -> tuple[dict, list[str]]:
    """Devuelve {nombre_tabla: DataFrame} y la lista de tablas no encontradas."""
    url = f"{BASE}/{code}/{season}/all_comps/Estadisticas-de-{team}-Todas-las-competencias"
    soup = fetch(url)
    fallback = None
    tables, missing = {}, []
    for table_id, name in TABLES.items():
        df = parse_table(soup, table_id)
        if df is None:   # algunas temporadas solo tienen la tabla de liga (id con sufijo de la competición)
            if fallback is None:
                fallback = fetch(f"{BASE}/{code}/{season}/Estadisticas-de-{team}") or False
            df = parse_table(fallback or None, table_id.replace("_combined", comp_suffix))
        if df is None:
            missing.append(f"{name} {team} {season}")
            continue
        df["Equipo"], df["Temporada"] = team, season
        tables[name] = df
    return tables, missing


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected: dict[str, list[pd.DataFrame]] = {name: [] for name in TABLES.values()}
    not_found: list[str] = []
    for league, teams in TEAMS.items():
        for team, code, suffix in teams:
            for season in SEASONS:
                log.info("%s | %s | %s", league, team, season)
                tables, missing = scrape_team_season(team, code, suffix, season)
                not_found += missing
                for name, df in tables.items():
                    df["Liga"] = league
                    collected[name].append(df)
    for name, frames in collected.items():
        if frames:
            pd.concat(frames, ignore_index=True).drop_duplicates().to_excel(OUT_DIR / f"{name}_Total.xlsx",
                                                                             index=False)
    pd.Series(not_found, name="no_encontradas").to_csv(OUT_DIR / "no_encontradas.csv", index=False)
    log.info("Listo. Tablas no encontradas: %d", len(not_found))


if __name__ == "__main__":
    main()
