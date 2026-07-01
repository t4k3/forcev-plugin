---
name: forcelab-export-xlsx
description: Esporta i test ForceLab in un foglio Excel (.xlsx) formattato, come l'export dell'app — pensato come ponte per chi lavora ancora coi fogli di calcolo. v1 copre i CMJ (un salto per riga) ricalcolando le metriche dal raw e includendo le colonne di validazione. Usa quando l'utente chiede un export Excel / un foglio dei test / "come l'export dell'app".
---

# ForceLab — Export Excel (ponte dai fogli di calcolo)

Genera un `.xlsx` dei test di un atleta, **senza dipendenze esterne** (writer XLSX
in stdlib). Pensata come **ponte**: dà a chi è abituato ai fogli un output
familiare, ma calcolato in modo indipendente dal raw e con le colonne di
**validazione** (Δ flight-time vs impulse) che l'export dell'app non ha.

> Obiettivo strategico: abituare gradualmente all'analisi con Claude, partendo da
> un formato familiare (Excel) per poi superarlo.

## Quando usarla
- "esportami in Excel i CMJ di GIULIA"
- "voglio un foglio dei salti di <atleta> di aprile"
- "fammi l'export come quello dell'app"

## Procedura (v1: CMJ di un atleta)

1. **Trova le sessioni** col tool MCP `list_sessions` (test_type `jump`,
   jump_subtype `CMJ`, eventuale `from_date`/`to_date`). Raccogli i `logFile`.

2. **Esporta il raw** di ciascuna col tool MCP `export_session_csv` → ottieni i
   `csvPath` (in `ForceData/exports/`).

3. **Costruisci il foglio**:
   ```bash
   python3 <dir-skill>/build_cmj_xlsx.py \
       --athlete "GIULIA BOZZOLI" --out "<percorso>/GIULIA_CMJ.xlsx" \
       <csv1> <csv2> ...
   ```
   Lo script ricalcola ogni CMJ (riusa la skill `forcelab-cmj`) e scrive un foglio
   "CMJ" con una riga per salto. Colonne: Atleta, Data, Peso, Tempo volo, Altezza FT,
   Altezza Imp, Δ (cm), Δ (%), Picco forza, Picco/BW, RFD, Potenza, Asimmetria, Valido.

4. **Consegna**: dai all'utente il percorso del file e un breve riepilogo (n. salti,
   eventuali Δ alti = salti da rivedere).

## Note
- **Dipende dalla skill `forcelab-cmj`** (ne importa l'analizzatore): vanno tenute
  insieme, entrambe sotto `.claude/skills/`.
- **Niente openpyxl**: il file è scritto con `forcelab_xlsx.py` (solo stdlib). Apre
  in Excel / Numbers / Google Sheets.
- La data del salto è ricavata dal nome file (`YYYYMMDD_HHMMSS_...`).
- `Valido = no/ERRORE` → sessione senza volo (pedana scarica / atleta non sopra).

## Estensioni
- **Multi-atleta / squadra**: girare per ogni atleta, oppure estendere lo script con
  un manifest (atleta+csv) e un foglio per squadra.
- **Altri test** (MTP, Dyno…): aggiungere builder analoghi quando esisteranno gli
  analizzatori corrispondenti.
- **PDF / grafici**: aggiungere un export PDF con trend (passo successivo del "ponte").
- Quando l'app esporrà il sidecar metriche, aggiungere la colonna "numero app" per
  il confronto diretto.
