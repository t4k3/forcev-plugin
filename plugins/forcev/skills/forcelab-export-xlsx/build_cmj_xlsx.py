#!/usr/bin/env python3
"""
Costruisce un report Excel (.xlsx) dei CMJ di un atleta, ricalcolando le metriche
dal raw con la skill forcelab-cmj (cmj_analyze.py) e includendo la VALIDAZIONE
(divergenza flight-time vs impulse). Senza dipendenze esterne.

Uso:
    python3 build_cmj_xlsx.py --athlete "GIULIA BOZZOLI" --out report.xlsx \
        /path/20260422_160719_1014.csv /path/20260422_160702_1013.csv ...

La data di ogni salto e' ricavata dal nome file (logFile: YYYYMMDD_HHMMSS_...).
"""
import sys
import os
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
# Riusa l'analizzatore della skill sorella forcelab-cmj (stessa cartella skills).
sys.path.insert(0, os.path.join(HERE, "..", "forcelab-cmj"))
from cmj_analyze import analyze  # noqa: E402
from forcelab_xlsx import write_workbook  # noqa: E402

HEADERS = [
    "Atleta", "Data", "Peso (kg)", "Tempo volo (ms)",
    "Altezza FT (cm)", "Altezza Imp (cm)", "Δ (cm)", "Δ (%)",
    "Picco forza (N)", "Picco/BW", "RFD (N/s)", "Potenza (W)",
    "Asimmetria (%)", "Valido",
]


def date_from_logfile(csv_path):
    base = os.path.basename(csv_path)
    name = base[:-4] if base.lower().endswith(".csv") else base
    parts = name.split("_")
    if len(parts) >= 2 and len(parts[0]) == 8 and len(parts[1]) == 6:
        d, t = parts[0], parts[1]
        return f"{d[0:4]}-{d[4:6]}-{d[6:8]} {t[0:2]}:{t[2:4]}:{t[4:6]}"
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--athlete", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("csv", nargs="+")
    args = ap.parse_args()

    rows = []
    for csv_path in args.csv:
        res = analyze(csv_path)
        if "error" in res:
            rows.append([args.athlete, date_from_logfile(csv_path),
                         "", "", "", "", "", "", "", "", "", "", "", "ERRORE"])
            continue
        rows.append([
            args.athlete,
            date_from_logfile(csv_path),
            res.get("body_weight_kg", ""),
            res.get("flight_time_ms", ""),
            res.get("height_flighttime_cm", ""),
            res.get("height_impulse_cm", ""),
            res.get("height_delta_cm", ""),
            res.get("height_delta_pct", ""),
            res.get("peak_force_N", ""),
            res.get("peak_force_bw", ""),
            res.get("rfd_N_s", ""),
            res.get("peak_power_W", ""),
            res.get("asymmetry_pct", ""),
            "sì" if res.get("valid") else "no",
        ])

    # ordina per data
    rows.sort(key=lambda r: r[1])
    write_workbook(args.out, [("CMJ", HEADERS, rows)])
    print(f"OK -> {args.out}  ({len(rows)} salti)")


if __name__ == "__main__":
    main()
