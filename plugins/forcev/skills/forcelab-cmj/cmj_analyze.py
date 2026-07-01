#!/usr/bin/env python3
"""
CMJ analyzer — ricalcolo INDIPENDENTE dal raw (force plate ForceDeck).
Due metodi fisici indipendenti per l'altezza -> la loro divergenza misura la
precisione (cross-validation). NON riusa il motore dell'app.

Input CSV (da export_session_csv): timestamp_s, force_L, force_R, force_total, ...
Forza in raw ADC: N = raw * 0.1 * 9.81 ; kg = raw * 0.1.
"""
import sys, csv, json

G = 9.81
RAW_TO_KG = 0.1
RAW_TO_N = RAW_TO_KG * G  # N per raw count


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load(path):
    t, F, FL, FR = [], [], [], []
    with open(path) as f:
        # Salta le righe di commento iniziali (#...) fino all'header reale.
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
        for d in csv.DictReader(lines):
            tv = num(d.get("timestamp_s"))
            tot = num(d.get("force_total"))
            if tv is None or tot is None:
                continue
            t.append(tv)
            F.append(tot * RAW_TO_N)
            FL.append((num(d.get("force_L")) or 0.0) * RAW_TO_N)
            FR.append((num(d.get("force_R")) or 0.0) * RAW_TO_N)
    return t, F, FL, FR


def analyze(path):
    t, F, FL, FR = load(path)
    n = len(F)
    if n < 100:
        return {"error": "troppi pochi campioni di forza"}
    dts = [t[i + 1] - t[i] for i in range(n - 1) if t[i + 1] > t[i]]
    dt = sorted(dts)[len(dts) // 2] if dts else 0.001

    # --- Body weight: finestra di QUIETE piu' stabile nei primi 2 s (min SD), non
    # i primi 0.4 s "ciechi": il metodo impulse e' sensibilissimo a un offset di peso. ---
    win = max(10, int(0.4 / dt))
    lim = min(n - win, max(1, int(2.0 / dt)))
    step = max(1, int(0.05 / dt))
    bw, bw_sd, bw_i = None, None, 0
    for a in range(0, lim, step):
        seg = F[a:a + win]
        m = sum(seg) / len(seg)
        sd = (sum((x - m) ** 2 for x in seg) / len(seg)) ** 0.5
        if bw_sd is None or sd < bw_sd:
            bw, bw_sd, bw_i = m, sd, a
    if bw is None:
        bw = sum(F[:win]) / win
        bw_sd = 0.0
        bw_i = 0
    mass = bw / G

    # --- Volo: piu' lunga corsa sotto soglia (CMJ = un volo) ---
    thr = max(20.0, 0.05 * bw)
    best = (0, -1, -1)
    s = None
    for i in range(n):
        if F[i] < thr:
            if s is None:
                s = i
        else:
            if s is not None:
                if i - s > best[0]:
                    best = (i - s, s, i)
                s = None
    if s is not None and n - s > best[0]:
        best = (n - s, s, n - 1)
    flight_len, to_idx, land_idx = best
    if land_idx >= n:
        land_idx = n - 1

    have_flight = flight_len > int(0.1 / dt) and to_idx > 0   # >=100ms = volo plausibile

    # --- Metodo 1: FLIGHT-TIME ---  h = g * t^2 / 8
    flight_time = (t[land_idx] - t[to_idx]) if have_flight else 0.0
    h_flight = G * flight_time ** 2 / 8.0

    # --- Metodo 2: IMPULSE-MOMENTUM ---  v = integral(F-BW)/m ; h = v^2/2g
    # Integra dall'ONSET del movimento (prima deviazione dal peso) al decollo, NON
    # da inizio file: integrare la lunga fase ferma amplifica un offset di peso
    # (3 N -> ~3 cm). All'onset l'atleta e' ancora fermo (v=0).
    thr_on = max(10.0, 5.0 * bw_sd)
    onset = min(bw_i + win, (to_idx if have_flight else n) - 1)
    if have_flight:
        for i in range(bw_i, to_idx):
            if abs(F[i] - bw) > thr_on:
                onset = i
                break
    vel = [0.0] * n
    for i in range(onset + 1, n):
        ddt = t[i] - t[i - 1]
        if ddt <= 0:
            ddt = dt
        vel[i] = vel[i - 1] + ((F[i] - bw) / mass) * ddt
    v_to = vel[to_idx] if have_flight else 0.0
    h_imp = v_to ** 2 / (2 * G) if v_to > 0 else 0.0

    # --- Picco forza, RFD, potenza, asimmetria ---
    # Finestra di analisi = tutto cio' che precede il decollo (la salita propulsiva
    # contiene il max di forza, di dF/dt e di potenza). Niente ancoraggio al "min
    # forza", che cade vicino al decollo (forza->0) e azzerava i range.
    hi = to_idx if (have_flight and to_idx > 1) else n
    peakF = max(F[:hi])
    peakF_idx = F.index(peakF)
    # RFD = max pendenza positiva su finestra 20ms (la rampa concentrica).
    w = max(2, int(0.02 / dt))
    rfd = 0.0
    for i in range(0, max(1, hi - w)):
        if t[i + w] > t[i]:
            d = (F[i + w] - F[i]) / (t[i + w] - t[i])
            if d > rfd:
                rfd = d
    # Potenza di picco = max F*v nella fase concentrica (v>0).
    peakP = 0.0
    for i in range(0, hi):
        if vel[i] > 0:
            p = F[i] * vel[i]
            if p > peakP:
                peakP = p
    # asimmetria al picco di forza (R-L)/(R+L)
    asym = None
    L, R = FL[peakF_idx], FR[peakF_idx]
    if (L + R) > 0:
        asym = (R - L) / (R + L) * 100.0

    # --- Confronto dei due metodi (LA validazione) ---
    delta_cm = (h_flight - h_imp) * 100.0
    delta_pct = (delta_cm / (h_imp * 100.0) * 100.0) if h_imp > 0 else None

    return {
        "samples": n,
        "sample_rate_hz": round(1.0 / dt) if dt else None,
        "body_weight_kg": round(mass, 1),
        "body_weight_N": round(bw, 0),
        "flight_time_ms": round(flight_time * 1000, 0),
        "takeoff_velocity_ms": round(v_to, 3),
        "height_flighttime_cm": round(h_flight * 100, 1),
        "height_impulse_cm": round(h_imp * 100, 1),
        "height_delta_cm": round(delta_cm, 1),
        "height_delta_pct": round(delta_pct, 1) if delta_pct is not None else None,
        "peak_force_N": round(peakF, 0),
        "peak_force_bw": round(peakF / bw, 2) if bw else None,
        "rfd_N_s": round(rfd, 0),
        "peak_power_W": round(peakP, 0),
        "asymmetry_pct": round(asym, 1) if asym is not None else None,
        "valid": have_flight,
    }


if __name__ == "__main__":
    res = analyze(sys.argv[1])
    print(json.dumps(res, indent=2))
