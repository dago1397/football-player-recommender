"""Configuración compartida del proyecto / Shared project configuration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"            # Excel scrapeados de FBref (no se versionan)
DATA_PROCESSED = ROOT / "data" / "processed"
IMAGES = ROOT  # versión plana: las imágenes se guardan en la raíz

SEASONS = ["2017-2018", "2018-2019", "2019-2020", "2020-2021", "2021-2022", "2022-2023"]
KEYS = ["Jugador", "Temporada", "Equipo"]
MIN_90S = 5          # el jugador debe tener más de 5 partidos completos (90 s > 5) en la temporada
TOP_N = 20
ACTIVE_SEASONS = ["2021-2022", "2022-2023"]   # candidatos: jugadores cuya última temporada es una de estas

# Factor de penalización según temporadas disponibles (igual que el proyecto original)
SEASON_PENALTY = {1: 0.6, 2: 0.7, 3: 0.8}     # 4 o más temporadas -> 1.0

# Columnas que se toman de cada tabla (mismas selecciones del notebook original)
TABLES = {
    "Estandar_Total.xlsx": ["País", "Posc", "Edad", "PJ", "Titular", "Mín", "90 s", "xG", "npxG", "xAG",
                            "npxG+xAG", "PrgC", "PrgP", "PrgR", "Gls. P90", "Ast P90", "G+A P90", "G-TP P90",
                            "G+A-TP P90", "xG P90", "xAG P90", "xG+xAG P90", "npxG P90", "npxG+xAG P90",
                            "Gls.", "Ass", "Liga"],
    "Variadas_Total.xlsx": ["Fls", "FR", "Pcz", "Int", "Recup.", "Duel_Aer Perdidos", "Duel_Aer Ganados",
                            "% Del_Aer ganados"],
    "Tiros_Total.xlsx": ["Dis", "DaP", "% de TT", "T/90", "TalArc/90", "G/T", "G/TalArc", "Dist", "npxG/Sh",
                         "G-xG", "np:G-xG"],
    "Pases_Total.xlsx": ["Int. Total", "% Cmp Total", "Dist. tot.", "Dist. prg.", "Cmp Corto", "Int. Corto",
                         "% Cmp Corto", "Cmp Medio", "Int. Medio", "% Cmp Medio", "Cmp Largo", "Int. Largo",
                         "% Cmp Largo", "xA", "A-xAG", "PC", "PPA", "CrAP"],
    "Tipo_Pases_Total.xlsx": ["Balón muerto", "FK", "PL", "Camb.", "Lanz."],
    "Crea_Gol_Total.xlsx": ["SCA90", "PasesVivos Tiro", "PasesMuertos Tiro", "HASTA Tiro", "Dis Tiro", "FR Tiro",
                            "Def Tiro", "GCA90", "PasesVivos Gol", "PasesMuertos Gol", "HASTA Gol", "Dis Gol",
                            "FR Gol", "Def Gol"],
    "Defensa_Total.xlsx": ["Tkl", "TklG", "Entrada 3.º def.", "Entrada 3.º cent.", "Entrada 3.º ataq.",
                           "Tkl Regate", "Att", "Tkl%", "Pérdida", "Bloqueos", "Disp. Bloq", "Pases", "Tkl+Int",
                           "Desp.", "Err"],
    "Posecion_Total.xlsx": ["Def. pen.", "3.º def.", "3.º cent.", "3.º ataq.", "Ataq. pen.", "Balón vivo", "Succ",
                            "Exitosa%", "Tkld", "Tkld%", "Transportes", "1/3", "TAP", "Errores de control",
                            "Des", "Rec"],
}

# Conteos que se pasan a "por 90 minutos" (columna nueva: "<col> P90"), como en el original
PER90_FROM_COUNTS = ["PrgC", "PrgP", "PrgR", "Fls", "FR", "Pcz", "Int", "Recup.", "Duel_Aer Ganados",
                     "Duel_Aer Perdidos", "Dis", "DaP", "Int. Total", "Dist. tot.", "Dist. prg.", "Cmp Corto",
                     "Int. Corto", "Cmp Medio", "Int. Medio", "Cmp Largo", "Int. Largo", "PC", "PPA", "CrAP",
                     "Balón muerto", "FK", "PL", "Camb.", "Lanz.", "PasesVivos Tiro", "PasesMuertos Tiro",
                     "HASTA Tiro", "Dis Tiro", "FR Tiro", "Def Tiro", "PasesVivos Gol", "PasesMuertos Gol",
                     "HASTA Gol", "Dis Gol", "FR Gol", "Def Gol", "Tkl", "TklG", "Entrada 3.º def.",
                     "Entrada 3.º cent.", "Entrada 3.º ataq.", "Tkl Regate", "Att", "Pérdida", "Bloqueos",
                     "Disp. Bloq", "Pases", "Tkl+Int", "Desp.", "Err", "Def. pen.", "3.º def.", "3.º cent.",
                     "3.º ataq.", "Ataq. pen.", "Balón vivo", "Succ", "Tkld", "Transportes", "1/3", "TAP",
                     "Errores de control", "Des", "Rec"]

# Columnas que ya vienen como tasa, porcentaje o promedio y se usan tal cual
RATE_COLUMNS = ["xG", "npxG", "xAG", "npxG+xAG", "Gls. P90", "Ast P90", "G+A P90", "G-TP P90", "G+A-TP P90",
                "xG P90", "xAG P90", "xG+xAG P90", "npxG P90", "npxG+xAG P90", "% Del_Aer ganados", "% de TT",
                "T/90", "TalArc/90", "G/T", "G/TalArc", "Dist", "npxG/Sh", "G-xG", "np:G-xG", "% Cmp Total",
                "% Cmp Corto", "% Cmp Medio", "% Cmp Largo", "xA", "A-xAG", "SCA90", "GCA90", "Tkl%",
                "Exitosa%", "Tkld%"]

# En la versión 2.0 estos totales de temporada se reemplazan por su equivalente por 90 minutos
SEASON_TOTALS_TO_PER90 = ["xG", "npxG", "xAG", "npxG+xAG", "xA", "G-xG", "np:G-xG", "A-xAG"]
