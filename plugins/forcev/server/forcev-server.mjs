// Force V — wrapper del connettore MCP.
// Imposta la cartella dati su forcefive (iCloud sul Mac) PRIMA di caricare il
// server, così il path è corretto per qualsiasi utente senza dipendere
// dall'espansione di variabili nel plugin.json. Se l'utente ha già impostato
// FORCELAB_DATA_DIR, lo rispettiamo.
import { homedir } from "node:os";
import { join } from "node:path";

if (!process.env.FORCELAB_DATA_DIR) {
  process.env.FORCELAB_DATA_DIR = join(
    homedir(),
    "Library/Mobile Documents/iCloud~com~takeoff~forcev/Documents/ForceData"
  );
}

await import("./forcelab-server.mjs");
