---
name: forcelab-migrate
description: Migra TUTTI i dati da ForceLab (vecchia app) a Force V clonando lo store SwiftData locale (non il solo mirror iCloud, che perde i test Dyno/Grow/VBT/Iso). Cattura test, sessioni, atleti, curve e video, poi allinea i binari nella ForceCache di ForceV. Usa quando l'utente vuole migrare/trasferire i dati da ForceLab a Force V, o dice "migra i dati", "porta i dati in ForceV".
---

# ForceLab → Force V — migrazione via clone dello store SwiftData

Trasferisce **TUTTI** i dati da **ForceLab** a **Force V** clonando lo store
SwiftData locale (`default.store`) + specchiando i binari delle curve e i video.

## Perché store-clone (e NON il mirror iCloud)
I test **Dyno / Grow / VBT / Iso** vivono SOLO nei **modelli SwiftData dedicati**
(`ZDINAMICOSESSIONMODEL`, `ZGROWSESSIONMODEL`, `ZVBTSESSIONMODEL`,
`ZISOSERIESSTRUCT`, …) presenti **solo nello store locale**, NON nei file iCloud.
Il mirror iCloud copiava solo `ForceData`/`ForceVideos` → portava Jump/Balance/
Ergo/Casco ma **perdeva i Dyno**. Clonando lo store si migra tutto, con le
relazioni intatte.

## Come funziona (sicuro)
Le due app sono lo stesso codebase (fork): schema **identico** tranne UNA colonna
additiva, `ZGROWLOGMODEL.ZLEG` (aggiunta da ForceV). Lo store di ForceLab non ce
l'ha; quando ForceV apre lo store clonato, **SwiftData esegue la migrazione
lightweight** e crea `ZLEG` da solo. Nessun rischio di wipe. Verificato: dopo la
migrazione+avvio, la colonna ricompare (zleg=1).

Il clone usa `VACUUM INTO` = snapshot consistente (fa il checkpoint del WAL, un
solo file). La **sorgente ForceLab non viene mai modificata** (sola lettura).

## Prerequisito: installazione PULITA di Force V
1. Installa/avvia **Force V una volta** (crea uno store vuoto con lo schema
   corrente) e poi **chiudilo**.
2. ForceLab deve essere presente su questo Mac (il suo container con i dati).
   > Nota: lo store locale è per-device. I dati Dyno/… di un collaboratore stanno
   > sul SUO dispositivo: per migrarli, il suo `default.store` di ForceLab deve
   > essere su un Mac dove gira questa skill (o passare SRC=<uuid> a mano).

## Procedura
1. **Dry-run** (rileva i container, mostra il piano, NON tocca nulla):
   ```bash
   bash <dir-skill>/migrate.sh --plan
   ```
   Rileva automaticamente SORGENTE (ForceLab = più log, `zleg=0`) e TARGET
   (Force V = `zleg=1`, meno log). **Mostra il piano all'utente e fatti
   confermare** prima di procedere.
2. **Esegui**:
   ```bash
   bash <dir-skill>/migrate.sh --go
   ```
   Lo script: materializza i placeholder iCloud, chiude ForceV, fa il **backup**
   dello store target, clona lo store (`VACUUM INTO`), specchia binari+video nella
   ForceCache locale di ForceV (+ iCloud forcefive), stampa la copertura binari.
3. **Rilancia Force V** → migrazione lightweight (aggiunge `ZLEG`) → tutti i test,
   Dyno inclusi, presenti e apribili.

## Override manuale
Se il rilevamento è ambiguo (più installazioni), passa gli UUID a mano:
```bash
SRC=<uuid-forcelab> TGT=<uuid-forcev> bash <dir-skill>/migrate.sh --go
```
Gli UUID si leggono dall'output di `--plan`.

## Note / caveat
- **Backup** dello store target salvato in `~/Library/Containers/forcev_migrate_backup_<ts>/`.
  Se ForceV non si aprisse dopo il clone, ripristina quel `default.store`.
- Alcuni log molto vecchi di ForceLab possono essere già **senza binario** (curve
  mai sincronizzate): lo script riporta la copertura. Non è un dato perso da noi.
- Idempotente: rilanciabile (rsync additivo + VACUUM INTO sovrascrive lo store).
- I dati Dyno/Grow/VBT/Iso NON sono nei file iCloud → il solo mirror iCloud NON
  basta. Questo è il motivo per cui questa skill clona lo store.

## MCP su Force V (analisi)
Il connettore MCP legge i **file** `ForceData` (manifest + binari), non lo store.
Per analizzare i dati di Force V, registra un secondo connettore `forcev` con
`FORCELAB_DATA_DIR` puntato a `iCloud~com~takeoff~forcefive/Documents/ForceData`
(path stabile, indipendente dall'UUID del container).
