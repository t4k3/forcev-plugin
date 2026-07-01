---
name: forcelab-cmj
description: Analizza e VALIDA un CMJ (Counter Movement Jump) di ForceLab ricalcolando le metriche dal segnale grezzo della pedana e confrontando due metodi fisici indipendenti (flight-time vs impulse-momentum). Usa quando l'utente chiede di analizzare, validare o confrontare un salto CMJ di un atleta, o di misurare la precisione/affidabilità dei dati di un CMJ.
---

# ForceLab — Analisi & validazione CMJ

Ricalcola le metriche di un CMJ **in modo indipendente** dal motore dell'app,
partendo dai dati grezzi della pedana, e ne misura la **precisione** confrontando
due metodi fisici indipendenti per l'altezza. La divergenza tra i due metodi (e,
quando disponibile, tra questi e il numero dell'app) è il segnale di qualità degli
algoritmi: se coincidono c'è alta confidenza, se divergono si indaga.

## Quando usarla
- "analizza il CMJ di GIULIA del 22 aprile"
- "valida i salti di <atleta>" / "quanto sono precisi questi CMJ?"
- confronto altezza flight-time vs impulse-momentum.

## Procedura

1. **Trova la sessione** col tool MCP `list_sessions` (test_type `jump`, jump_subtype `CMJ`).
   Prendi il `logFile` (es. `20260422_160719_1014`).

2. **Esporta il raw** col tool MCP `export_session_csv` passando il `logFile`.
   Restituisce `csvPath` (file scritto in `ForceData/exports/<logFile>.csv`).

3. **Esegui l'analizzatore** sul CSV:
   ```bash
   python3 <dir-di-questa-skill>/cmj_analyze.py "<csvPath>"
   ```
   Restituisce JSON con: `body_weight_kg`, `flight_time_ms`, `takeoff_velocity_ms`,
   `height_flighttime_cm`, `height_impulse_cm`, `height_delta_cm`,
   `height_delta_pct`, `peak_force_N`, `peak_force_bw`, `rfd_N_s`, `peak_power_W`,
   `asymmetry_pct`, `valid`.

4. **Interpreta e riporta** (la parte di validazione):
   - Mostra le due altezze e il **Δ**.
   - `|Δ%|` piccolo (≲5%) → metodi concordi, alta confidenza.
   - Δ sistematico (flight-time > impulse in modo costante) → tipico di flessione
     ginocchia al decollo/atterraggio; o problemi di soglia volo / peso.
   - Δ grande o rumoroso → indagare rilevamento decollo/atterraggio o baseline peso.
   - `valid:false` → niente volo rilevato (sessione vuota / atleta non sulle pedane).

5. **Confronto col numero dell'app** (quando disponibile): se esiste un sidecar
   `ForceData/metrics/<logFile>.json` con le metriche calcolate dall'app, confronta
   `height_impulse_cm`/`height_flighttime_cm` con `jump_height` dell'app e riporta il Δ.
   (Finche' il sidecar non esiste, valida solo i due metodi tra loro.)

## Note fisiche (per spiegare i numeri)
- Forza grezza pedana: `N = raw * 0.981` (`kg = raw * 0.1`).
- **Flight-time**: `h = g·t²/8` dal tempo di volo (forza sotto soglia tra decollo e atterraggio).
- **Impulse-momentum**: `v_decollo = ∫(F − peso)dt / massa` (da fermo), `h = v²/2g`.
  Usa l'integrale della forza → percorso fisico DIVERSO dal flight-time, quindi il
  confronto è una vera validazione incrociata.
- Squat/CMJ con bilanciere o pedana scarica → `valid:false`.

## Estensioni possibili
- Batch su tutti i CMJ di un atleta → tabella + statistiche di Δ (precisione media).
- Esportare il report in XLSX/PDF.
- Quando l'MCP esporrà un tool `analyze_cmj`/`session_metrics`, spostare il calcolo
  lì per usarlo anche da Claude Desktop (non solo Claude Code).
