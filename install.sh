#!/usr/bin/env bash
#
# Force V -> Claude Desktop — installer connettore locale (una volta sola).
# Scarica il server MCP in ~/.forcev e registra il connettore "forcev" in
# Claude Desktop. Legge i dati Force V dalla cartella iCloud sul Mac.
# Nessun server pubblico, nessun token — tutto locale.
#
set -euo pipefail

RAW="https://raw.githubusercontent.com/t4k3/forcev-plugin/main/plugins/forcev/server"
DEST="$HOME/.forcev"
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

echo "== Force V -> Claude (connettore locale) =="

# 1) Node
if ! command -v node >/dev/null 2>&1; then
  echo "ERRORE: Node.js non installato. Scaricalo da https://nodejs.org (LTS) e rilancia."
  exit 1
fi
echo "  Node $(node --version) ok"

# 2) Scarica il server MCP
mkdir -p "$DEST"
curl -fsSL "$RAW/forcelab-server.mjs" -o "$DEST/forcelab-server.mjs"
curl -fsSL "$RAW/forcev-server.mjs"   -o "$DEST/forcev-server.mjs"
echo "  server installato in $DEST"

# 3) Registra 'forcev' in Claude Desktop (merge: non tocca gli altri connettori)
mkdir -p "$(dirname "$CFG")"
node -e '
const fs=require("fs"), os=require("os"), p=process.argv[1];
let c={}; try{ c=JSON.parse(fs.readFileSync(p,"utf8")) }catch(e){}
c.mcpServers=c.mcpServers||{};
c.mcpServers.forcev={ command:"node", args:[os.homedir()+"/.forcev/forcev-server.mjs"] };
fs.writeFileSync(p, JSON.stringify(c,null,2));
console.log("  connettore forcev registrato in Claude Desktop");
' "$CFG"

echo ""
echo "FATTO. Ora: chiudi Claude del tutto (Cmd-Q) e riaprilo →"
echo "menu + → Connettori → attiva \"forcev\"."
echo "Poi in chat: \"elenca i miei atleti in forcev\"."
