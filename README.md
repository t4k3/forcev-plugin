# Force V — plugin per Claude

Un'**unica installazione** che collega i tuoi dati **Force V** a Claude sul Mac e
aggiunge le skill di analisi. Porta insieme:

- **Connettore dati (MCP)** — Claude legge i tuoi test Force V dalla cartella iCloud
  locale (nessun server pubblico, nessun token).
- **Skill**:
  - `forcelab-cmj` — analizza e valida un CMJ dai dati grezzi.
  - `forcelab-export-xlsx` — esporta i test in un foglio Excel.
  - `forcelab-migrate` — migra i dati da ForceLab a Force V.

Flusso: **iPad/iPhone registra i test → iCloud sincronizza → sul Mac Claude analizza.**

## Prerequisiti (Mac)
- App **Force V** su iPhone/iPad (genera i dati).
- **iCloud Drive attivo** con lo stesso Apple ID.
- **Claude** (Desktop / cowork) sul Mac.
- **Node.js** LTS — https://nodejs.org (unico componente tecnico).

## Installazione (una volta sola)
In una chat di Claude:

```
/plugin marketplace add t4k3/forcev-plugin
/plugin install forcev@forcev
```

Fatto: connettore **e** skill sono attivi insieme. Nessuna cartella da copiare,
nessun file di config da editare.

> In locale (per test, senza GitHub):
> `/plugin marketplace add /Users/ross/EVAL/forcev-plugin`

## Uso
```
elenca i miei atleti
quante sessioni di salti ho registrato questo mese?
analizza il CMJ di <atleta> del <data>
migra i dati da ForceLab a Force V
```

## Aggiornare / disinstallare
```
/plugin update forcev@forcev
/plugin uninstall forcev@forcev
```

## Note
- Il connettore legge `~/Library/Mobile Documents/iCloud~com~takeoff~forcefive/Documents/ForceData`.
  Se un test risulta "non scaricato da iCloud", aprilo una volta nel Finder per
  forzarne il download.
- Tutto locale: i dati non lasciano il tuo Mac.
