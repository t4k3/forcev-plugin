#!/usr/bin/env bash
#
# forcelab-migrate — clona lo STORE SwiftData di ForceLab dentro ForceV
# (installazione pulita) + specchia binari curve e video.
#
# PERCHÉ store-clone e NON solo mirror iCloud:
#   I test Dyno / Grow / VBT / Iso vivono SOLO nello store SwiftData locale
#   (ZDINAMICOSESSIONMODEL, ZGROWSESSIONMODEL, ...), NON nei file iCloud.
#   Il vecchio mirror iCloud portava Jump/Balance/Ergo/Casco ma PERDEVA i Dyno.
#   Clonando lo store si migra TUTTO, con relazioni intatte.
#
# Differenza di schema forcelab->forcev: SOLO la colonna ZGROWLOGMODEL.ZLEG
#   (aggiunta da ForceV). È additiva: SwiftData la crea con la migrazione
#   lightweight al primo avvio. Nessun rischio di wipe.
#
# Uso:
#   bash migrate.sh --plan     # rileva i container, stampa il piano, NON tocca nulla
#   bash migrate.sh --go       # esegue (con backup del target)
#   SRC=<uuid> TGT=<uuid> bash migrate.sh --go   # override manuale dei container
#
set -uo pipefail

MODE="${1:---plan}"
CROOT="$HOME/Library/Containers"
ASUP="Data/Library/Application Support"
ICLOUD_FL="$HOME/Library/Mobile Documents/iCloud~com~takeoff~forcelab/Documents"
ICLOUD_FV="$HOME/Library/Mobile Documents/iCloud~com~takeoff~forcev/Documents"

q() { sqlite3 "file:$1?mode=ro" "$2" 2>/dev/null; }

# --- 1. enumera i container candidati (store con tabella ZLOGDATA) ------------
declare -a CAND
for st in "$CROOT"/*/"$ASUP"/default.store; do
  [ -f "$st" ] || continue
  rows=$(q "$st" "SELECT count(*) FROM ZLOGDATA;")
  [ -n "$rows" ] || continue                      # non è uno store delle nostre app
  uuid=$(echo "$st" | sed -E "s#$CROOT/([^/]+)/.*#\1#")
  din=$(q "$st" "SELECT count(*) FROM ZDINAMICOSESSIONMODEL;")
  zleg=$(q "$st" "SELECT count(*) FROM pragma_table_info('ZGROWLOGMODEL') WHERE name='ZLEG';")
  mtime=$(stat -f '%m' "$st")
  CAND+=("$uuid|$rows|${din:-0}|${zleg:-0}|$mtime")
done
[ "${#CAND[@]}" -gt 0 ] || { echo "ERRORE: nessuno store ForceLab/ForceV in $CROOT" >&2; exit 1; }

echo "=== container rilevati (uuid | ZLOGDATA | Dinamico | ZLEG | mtime) ==="
for c in "${CAND[@]}"; do
  IFS='|' read -r u r d z m <<<"$c"
  printf "  %s | log=%-5s | dyno=%-3s | zleg=%s | %s\n" "$u" "$r" "$d" "$z" "$(date -r "$m" '+%Y-%m-%d %H:%M')"
done

# --- 2. auto-pick source/target ---------------------------------------------
# TARGET (ForceV) = ha ZLEG=1 e MENO log (installazione pulita/fresh).
# SOURCE (ForceLab) = NON è il target e ha PIÙ log (dati reali).
SRC="${SRC:-}"; TGT="${TGT:-}"
if [ -z "$TGT" ]; then
  best_t=""; best_t_rows=999999999
  for c in "${CAND[@]}"; do IFS='|' read -r u r d z m <<<"$c"
    if [ "$z" = "1" ] && [ "$r" -le "$best_t_rows" ]; then best_t="$u"; best_t_rows="$r"; fi
  done
  TGT="$best_t"
fi
if [ -z "$SRC" ]; then
  best_s=""; best_s_rows=-1
  for c in "${CAND[@]}"; do IFS='|' read -r u r d z m <<<"$c"
    if [ "$u" != "$TGT" ] && [ "$r" -gt "$best_s_rows" ]; then best_s="$u"; best_s_rows="$r"; fi
  done
  SRC="$best_s"
fi

echo ""
echo "=== PIANO ==="
echo "  SORGENTE (ForceLab): $SRC"
echo "  TARGET   (ForceV):   $TGT"
{ [ -z "$SRC" ] || [ -z "$TGT" ] || [ "$SRC" = "$TGT" ]; } && {
  echo "ERRORE: rilevamento ambiguo. Passa SRC=<uuid> TGT=<uuid> a mano." >&2; exit 1; }

SRC_STORE="$CROOT/$SRC/$ASUP/default.store"
TGT_STORE="$CROOT/$TGT/$ASUP/default.store"
TGT_CACHE="$CROOT/$TGT/$ASUP/ForceCache/ForceData"
TGT_VCACHE="$CROOT/$TGT/$ASUP/ForceCache/ForceVideos"
src_rows=$(q "$SRC_STORE" "SELECT count(*) FROM ZLOGDATA;")
tgt_rows=$(q "$TGT_STORE" "SELECT count(*) FROM ZLOGDATA;")
echo "  clone store: $src_rows log  ->  target attuale $tgt_rows log (SOSTITUITI)"
echo "  binari/video: da iCloud ForceLab  ->  ForceCache locale ForceV (+ iCloud forcefive)"

if [ "$MODE" != "--go" ]; then
  echo ""; echo ">> Dry-run. Per eseguire: bash migrate.sh --go"; exit 0
fi

# --- 3. materializza i placeholder iCloud di ForceLab (binari + video) --------
echo ""
echo "=== materializzo i file iCloud di ForceLab (placeholder) ==="
count_ph() { find "$ICLOUD_FL/ForceData" "$ICLOUD_FL/ForceVideos" -name "*.icloud" 2>/dev/null | wc -l | tr -d ' '; }
if [ "$(count_ph)" -gt 0 ]; then
  find "$ICLOUD_FL/ForceData" "$ICLOUD_FL/ForceVideos" -name "*.icloud" -print0 2>/dev/null | while IFS= read -r -d '' f; do
    d=$(dirname "$f"); b=$(basename "$f"); real="${b#.}"; real="${real%.icloud}"
    brctl download "$d/$real" 2>/dev/null || true
  done
  for _ in $(seq 1 60); do [ "$(count_ph)" -eq 0 ] && break; sleep 2; done
fi
[ "$(count_ph)" -gt 0 ] && echo "  ATT: $(count_ph) file iCloud non scaricati — materializzali in Finder e rilancia."

# --- 4. chiudi ForceV se in esecuzione --------------------------------------
echo "=== chiudo ForceV (se attivo) ==="
pkill -x ForceV 2>/dev/null && sleep 2 || true
pgrep -x ForceV >/dev/null && { pkill -9 -x ForceV 2>/dev/null; sleep 1; } || true

# --- 5. backup target -------------------------------------------------------
BK="$CROOT/forcev_migrate_backup_$(date +%s)"; mkdir -p "$BK"
for f in default.store default.store-wal default.store-shm; do
  cp "$CROOT/$TGT/$ASUP/$f" "$BK/" 2>/dev/null || true
done
echo "backup target store -> $BK"

# --- 6. clone store (VACUUM INTO = snapshot consistente + checkpoint WAL) -----
echo "=== clone store (VACUUM INTO) ==="
rm -f "$TGT_STORE" "$TGT_STORE-wal" "$TGT_STORE-shm"
sqlite3 "file:$SRC_STORE?mode=ro" "VACUUM INTO '$TGT_STORE';" || { echo "ERRORE clone store" >&2; exit 1; }
echo "  store clonato: log=$(q "$TGT_STORE" "SELECT count(*) FROM ZLOGDATA;")  sessioni_dyno=$(q "$TGT_STORE" "SELECT count(*) FROM ZDINAMICOSESSIONMODEL;")"

# --- 7. binari curve + video: iCloud ForceLab -> ForceCache locale (+ iCloud fv)
echo "=== specchio binari curve + video ==="
mkdir -p "$TGT_CACHE" "$TGT_VCACHE"
if [ -d "$ICLOUD_FL/ForceData" ]; then
  rsync -a --exclude="*.icloud" "$ICLOUD_FL/ForceData/"   "$TGT_CACHE/"  2>/dev/null || true
  [ -d "$ICLOUD_FV" ] && { mkdir -p "$ICLOUD_FV/ForceData"; rsync -a --exclude="*.icloud" "$ICLOUD_FL/ForceData/" "$ICLOUD_FV/ForceData/" 2>/dev/null || true; }
fi
if [ -d "$ICLOUD_FL/ForceVideos" ]; then
  rsync -a --exclude="*.icloud" "$ICLOUD_FL/ForceVideos/" "$TGT_VCACHE/" 2>/dev/null || true
  [ -d "$ICLOUD_FV" ] && { mkdir -p "$ICLOUD_FV/ForceVideos"; rsync -a --exclude="*.icloud" "$ICLOUD_FL/ForceVideos/" "$ICLOUD_FV/ForceVideos/" 2>/dev/null || true; }
fi
echo "  ForceCache locale: $(find "$TGT_CACHE" -type f | wc -l | tr -d ' ') binari, $(find "$TGT_VCACHE" -type f | wc -l | tr -d ' ') video"

# --- 8. copertura binari rispetto allo store --------------------------------
python3 - "$TGT_STORE" "$TGT_CACHE" <<'PY'
import sqlite3,os,sys
store,fc=sys.argv[1],sys.argv[2]
con=sqlite3.connect(f"file:{store}?mode=ro",uri=True)
files=[r[0] for r in con.execute("SELECT ZLOGFILE FROM ZLOGDATA") if r[0]]
miss=[f for f in files if not os.path.exists(os.path.join(fc,f))]
print(f"  copertura binari: {len(files)-len(miss)}/{len(files)} (mancanti {len(miss)} = log vecchi gia' senza binario in ForceLab)")
PY

echo ""
echo "✅ Migrazione completata. Rilancia ForceV: SwiftData farà la migrazione"
echo "   lightweight (aggiunge ZLEG) e mostrerà tutti i test, Dyno inclusi."
echo "   Backup vecchio store target: $BK"
