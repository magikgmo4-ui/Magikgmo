## 2026-02-16 — PERF module (commands)

### Services
- status perf:
  sudo systemctl status perf.service --no-pager -l
- logs perf:
  sudo journalctl -u perf.service -n 200 --no-pager -o cat
- restart perf:
  sudo systemctl restart perf.service

- status tv-webhook:
  sudo systemctl status tv-webhook.service --no-pager -l
- logs tv-webhook:
  sudo journalctl -u tv-webhook.service -n 200 --no-pager -o cat
- restart tv-webhook:
  sudo systemctl restart tv-webhook.service

### Perf API
- summary:
  curl -s http://127.0.0.1:8010/perf/summary | python -m json.tool
- equity:
  curl -s http://127.0.0.1:8010/perf/equity | python -m json.tool
- open trades:
  curl -s http://127.0.0.1:8010/perf/open | python -m json.tool
- trades (last 50):
  curl -s "http://127.0.0.1:8010/perf/trades?limit=50" | python -m json.tool
- trades filter engine:
  curl -s "http://127.0.0.1:8010/perf/trades?engine=XAU_M5_SCALP&limit=50" | python -m json.tool

### SQLite fallback
- list OPEN:
  sqlite3 /opt/trading/perf/perf.db "select trade_id, engine, symbol, side, entry, stop, qty, risk_usd, entry_ts from trades where status='OPEN' order by entry_ts desc;"
- last 20:
  sqlite3 /opt/trading/perf/perf.db "select trade_id, status, engine, symbol, side, entry, exit, pnl_real, r_real, entry_ts, exit_ts from trades order by entry_ts desc limit 20;"

### /tv test (key auto from .env)
sudo bash -lc '
set -a; source /opt/trading/.env; set +a
K="${TV_WEBHOOK_KEY:-${WEBHOOK_KEY:-${TV_SECRET:-${SECRET:-${KEY:-}}}}}"
curl -s http://127.0.0.1:8000/tv -H "Content-Type: application/json" -d "{
  \"key\":\"$K\",
  \"engine\":\"XAU_M5_SCALP\",
  \"signal\":\"BUY\",
  \"symbol\":\"XAUUSD\",
  \"tf\":\"M5\",
  \"price\":5032.5,
  \"tp\":5040.0,
  \"sl\":5026.5,
  \"reason\":\"perf branch test\"
}" | python3 -m json.tool
'


## 2026-02-13 01:14 — Test journal auto OK
1) Objectifs:
- Recréer l’environnement virtuel si supprimé et vérifier l’installation (OpenAI).
- Effectuer un test final du journal automatique.

2) Actions:
- Recréation du venv dans `/opt/trading/venv`.
- Activation du venv.
- Mise à jour de `pip`.
- Installation des dépendances via `requirements.txt`.
- Lancement d’un test du journal auto avec le titre donné.

3) Décisions:
—  

4) Commandes / Code:
```bash
python3 -m venv /opt/trading/venv
source /opt/trading/venv/bin/activate
pip install -U pip
pip install -r /opt/trading/requirements.txt
jpt "Test journal auto OK"
```

5) Points ouverts (next):
- Vérifier que la sortie indique bien “Everything up-to-date”.

## 2026-02-13 01:35 — Validation finale système journal GPT multi-machine
1) Objectifs:
- Obtenir une commande simple pour sauvegarder des sessions/journal Git depuis Debian (admin-trading) en multi-machine via SSH.
- Mettre en place une capture “CTRL-A/CTRL-C/CTRL-V” des conversations ChatGPT vers un journal automatique, versionné et poussé sur GitHub.

2) Actions:
- Vérification de l’historique Git (`git log --oneline`) sur `/opt/trading`.
- Création d’une fonction Bash `savejournal` (commit + push) puis choix d’une automatisation.
- Conception d’un flux “semi-auto” avec script Python lisant stdin (coller conversation + Ctrl-D) et appel OpenAI API pour générer une entrée de journal structurée.
- Installation de la lib `openai` via `venv` (contournement Debian PEP 668).
- Ajout d’une fonction Bash `jpt` pour: activer venv → exécuter script → `savejournal`.
- Création effective de `/opt/trading/tools/journal_from_paste.py` et permissions d’exécution.
- Configuration de `OPENAI_API_KEY` dans `~/.bashrc` (côté admin-trading).
- Correction GitHub: passage HTTPS → SSH (clé existante `github_ed25519`, ajout config `~/.ssh/config`, ajout clé sur GitHub, authent SSH OK).
- Correction du remote `origin` avec URL SSH `git@github.com:magikgmo4-ui/Magikgmo.git`.
- Résolution du rejet push (remote non fast-forward): tentative de `pull --rebase` bloquée par fichiers non suivis (`venv/`, `__pycache__`), puis nettoyage/rebase (résolu).
- Validation du pipeline: génération d’une entrée dans `journal.md`, commit et synchro `origin/main`.
- Standardisation du workflow multi-machine: `ssh admin-trading` + `jpt "titre"` + coller + Ctrl-D.

3) Décisions:
- Ne pas installer de paquets Python en system-wide sur Debian; utiliser un venv dédié dans `/opt/trading/venv`.
- Utiliser SSH pour GitHub (pas HTTPS/password), avec clé dédiée `github_ed25519` forcée via `~/.ssh/config`.
- Workflow utilisateur final: depuis n’importe quelle machine → SSH vers `admin-trading` → lancer `jpt` → coller la conversation → Ctrl-D.

4) Commandes / Code:
```bash
# Git: sauvegarde manuelle / rapide
git add . && git commit -m "..." && git push
git status
git log --oneline

# Debian PEP 668: installation via venv
python3 -m venv /opt/trading/venv
source /opt/trading/venv/bin/activate
pip install -U pip
pip install openai
pip install -r /opt/trading/requirements.txt

# Fonctions Bash (dans ~/.bashrc)
savejournal() {
    TITLE="$1"
    DATE=$(TZ="America/Montreal" date +"%Y-%m-%d %H:%M")
    git add .
    git commit -m "Journal update: $DATE | $TITLE"
    git push
}

jpt() {
  TITLE="$1"
  cd /opt/trading || return 1
  source /opt/trading/venv/bin/activate
  python /opt/trading/tools/journal_from_paste.py "$TITLE"
  deactivate
  savejournal "$TITLE"
}

# Script: création dossier + fichier
mkdir -p /opt/trading/tools
nano /opt/trading/tools/journal_from_paste.py
chmod +x /opt/trading/tools/journal_from_paste.py

# Clé OpenAI
export OPENAI_API_KEY="sk-..."
# (mise ensuite dans ~/.bashrc)

# GitHub remote + SSH
git remote -v
git remote set-url origin git@github.com:magikgmo4-ui/Magikgmo.git

ssh -T git@github.com  # OK après config + ajout clé
nano ~/.ssh/config
chmod 600 ~/.ssh/config

# Résolution push/rebase (tenté; blocage initial par venv/__pycache__)
git fetch origin
git pull --rebase origin main
git rebase --abort

# Workflow final multi-machine
ssh admin-trading
jpt "Titre de session"
# coller conversation (CTRL-V), terminer stdin (CTRL-D)
```

5) Points ouverts (next):
- Corriger/valider l’état de `requirements.txt` (modifié localement) et décider de commit/push (ajout dépendances OpenAI) ou restauration.
- Confirmer que `.gitignore` couvre bien `venv/`, `__pycache__/`, `*.pyc` pour éviter de futurs blocages lors des pulls/rebase.
- Sauvegarder cette session via le workflow final (`ssh admin-trading` → `jpt "Validation finale système journal GPT multi-machine"` → coller ce dump → Ctrl-D).

## 2026-02-14 04:00 — multi-moteurs quannts
1) Objectifs:
- Identifier comment utiliser OpenAI pour le trading (API, agents, tool/function calling).
- Mettre en place une infrastructure quant reproductible sur Debian (data → backtest → rapports), avant de travailler les stratégies.
- Tenir un journal de bord systématique (session + date + titre).

2) Actions:
- Choix de Python sur Debian et progression “une solution à la fois”.
- Mise en place d’un projet `quant-infra` (venv, dépendances, structure dossiers).
- Implémentation et validation:
  - Fetch OHLCV via CCXT → sauvegarde Parquet.
  - Backtest skeleton buy&hold → métriques + `reports/equity.png`.
  - Ajout frais + slippage + génération `reports/trades.csv`.
  - Moteur multi-trades (LONG-only) avec signaux démo MA(20/50).
  - Multi-timeframe: données LTF 15m + signal HTF 1h forward-fill + annualisation adaptée crypto.
  - Reproductibilité via `config.yaml` + dataset déterministe (plus de “dernier parquet”).
  - Modularisation en package `src/` avec runners `python -m src.fetch` et `python -m src.backtest`.
- Correction d’une erreur utilisateur: code Python collé dans bash (création correcte de fichiers `.py`).

3) Décisions:
- Priorité à l’infrastructure quant (data/backtest) avant les stratégies.
- Stockage local Parquet (pas de DB au début).
- Backtester LONG-only d’abord; short plus tard.
- Introduire une config centralisée (`config.yaml`) pour la reproductibilité.
- Prochaine étape annoncée: journal automatique `journal.md` écrit par les runners (I9).

4) Commandes / Code:
```bash
# Bootstrap projet
mkdir -p ~/projects/quant-infra && cd ~/projects/quant-infra
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install pandas numpy pyarrow matplotlib rich pydantic python-dotenv ccxt

# Structure
mkdir -p data/raw data/clean reports src
touch .env .gitignore run_fetch.py run_backtest.py
cat > .gitignore <<'EOF'
.venv/
__pycache__/
data/
reports/
.env
EOF
```

```bash
# Fetch + backtest (validés)
python run_fetch.py
python run_backtest.py
```

```bash
# Passage config reproductible
pip install pyyaml
python run_fetch.py
python run_backtest.py
```

```bash
# Passage projet modulaire
python -m src.fetch
python -m src.backtest
```

5) Points ouverts (next):
- Implémenter I9: écriture automatique d’un `journal.md` (timestamp America/Montreal, titre, params, métriques, artefacts) via `src/quant/journal.py`, appelé depuis `src.fetch` et `src.backtest`.
- Vérifier la sortie `tail -n 60 journal.md` après exécution.
- Étape suivante envisagée après I9: rendre le titre de session paramétrable (ex: option `--title`).

## 2026-02-14 04:18 — python 2
1) Objectifs:
- Recenser les solutions OpenAI applicables au trading, puis appliquer chaque solution une à la fois en Python sur Debian.
- Monter une infrastructure quant (fetch data, backtest) avant de travailler les stratégies.
- Mettre en place une journalisation systématique (session/date/titre).

2) Actions:
- Setup projet Debian Python (`~/projects/quant-infra`) avec venv et dépendances (pandas/numpy/pyarrow/matplotlib/rich/pydantic/python-dotenv/ccxt + pyyaml + python-dateutil).
- Création de scripts puis modularisation en projet `src/`:
  - Fetch OHLCV via CCXT → Parquet.
  - Backtest skeleton (buy&hold) puis ajout coûts/slippage et trade log CSV.
  - Passage à un moteur multi-trades (signaux MA cross).
  - Multi-timeframe: signal HTF (1h) forward-fill sur LTF (15m) + annualisation adaptée.
  - Ajout d’une config `config.yaml` pour reproductibilité et sélection dataset déterministe.
  - Ajout CLI avec `--title` et `--run-id` (reports versionnés).
  - Batch runner `src.sweep` (grid fast/slow/htf) → `summary.csv`, puis hygiène (min_trades + durée) → `summary_all.csv`/`summary_filtered.csv`.
- Mise en place d’un journal automatique `journal.md` (timestamp America/Montreal, params, résultats, artefacts) alimenté par `python -m src.fetch` et `python -m src.backtest`.
- Correction d’erreur d’usage: code Python collé dans bash au lieu d’un fichier `.py`.
- Problème data: `LIMIT` à 10000 ne changeait pas le nombre de bougies (toujours 1000) → implémentation pagination CCXT:
  - 1ère tentative (forward) inefficace.
  - Fix pagination “backward” (Binance) → 10,000 bougies 15m récupérées (2025-11-02 → 2026-02-14).
- Sweep significatif après historique étendu: MA cross long-only globalement négatif (Sharpe filtrés < 0).
- Nettoyage des fichiers legacy `reports/equity.png` et `reports/trades.csv` à la racine (suppression).

3) Décisions:
- Prioriser l’infrastructure quant avant les stratégies.
- Stockage local Parquet (pas de DB au début).
- Standardiser un journal de bord automatique `journal.md`.
- Versionner les sorties backtest via `run_id` dans `reports/<run_id>/`.
- Ajouter hygiène dans les sweeps (min trades + durée).
- Constater que MA cross long-only n’est qu’un placeholder; besoin d’une stratégie robuste (prochaine: passage long/short + ATR/vol targeting envisagé).

4) Commandes / Code:
```bash
# Setup
mkdir -p ~/projects/quant-infra && cd ~/projects/quant-infra
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
pip install pandas numpy pyarrow matplotlib rich pydantic python-dotenv ccxt pyyaml python-dateutil

# Runs (modulaire)
python -m src.fetch
python -m src.backtest

# Backtest versionné
python -m src.backtest --title "BTC 15m infra test" --run-id auto

# Sweep
python -m src.sweep

# Vérif dataset
python - <<'PY'
import pandas as pd
df=pd.read_parquet("data/raw/binance_BTCUSDT_15m.parquet")
print("rows:", len(df), "start:", df.dt.iloc[0], "end:", df.dt.iloc[-1])
PY

# Nettoyage legacy
rm -f reports/equity.png reports/trades.csv
```

5) Points ouverts (next):
- Implémenter le backtester long/short (signal -1/0/+1) et adapter la génération de signaux directionnels.
- Refaire un sweep en mode directionnel (long/short) pour comparer.
- Ajouter une stratégie robuste #1 (ex: trend long/short avec ATR stop et/ou vol targeting) une fois le moteur L/S validé.
- Optionnel: améliorer significativité (min_trades) selon la fenêtre et paramètres.

## 2026-02-15 14:45 — pdf integral
1) Objectifs:
- Centraliser en format “imprimable/PDF” des checklists, journaux et guides opérationnels pour :
  - Trading XAUUSD (V2/V2.1) : checklist pré-trade, plan du jour, journal, stats, règles décisionnelles.
  - Analyse macro BTC bear market + checklists/stratégies de shorts.
  - Pack prop FTMO 50K (EURUSD Pullback EMA) : règles, checklist, sizing, anti-tilt, phase 2.
  - Procédure Debian 12 USB autonome + cgminer (ASIC USB).
  - Archive : node BlockDAG testnet Awakening (Docker) + VoIP via USB tethering + setup VoIP Linux.

2) Actions:
- Définition d’une checklist XAUUSD pré-trade (HTF, DXY, H1, M15, M5, RR ≥ 1:2, news, état mental).
- Mise en place de gabarits XAUUSD :
  - Checklist pré-trade V2 imprimable.
  - “Plan du jour” (biais, filtre DXY, news, niveaux, 3 scénarios).
  - “Journal” par trade (réel/backtest) avec plan/exécution/review et lien TradingView/capture.
- Rédaction d’un tutoriel d’utilisation “XAUUSD V2 Stats” (import Google Sheets, settings, journaux, dashboard, discipline).
- Rédaction d’un “Guide Décisionnel XAUUSD V2.1” basé sur stats (seuils NO TRADE, setups autorisés, sessions).
- Ajout d’un cadrage “Projet XAUUSD – Analyse et Stratégie de Trading” (processus quotidien, MTF, filtre DXY, risque, journalisation, backtests).
- Rédaction d’une synthèse “Bitcoin Bear Market Analysis” (hypothèses, timing M1–M10+, zones TP rally, shorts optimaux, base algo).
- Définition d’un modèle “Algorithme structurel — Long USDT / Short coin”.
- Création d’un “PROP EXAM PACK” FTMO 50K (EURUSD) : stratégie Pullback EMA, règles, checklist, sizing, anti-tilt, gestion phase 2.
- Création d’une checklist BTC short (bear) + fiche “short agressif (rejet confirmé)” avec zones clés.
- Documentation Debian 12 (Bookworm) : création clé USB (EtchDroid), install minimale, build cgminer (GekkoScience), test, autostart.
- Archive : procédure BlockDAG node (Docker + .env) ; guides VoIP USB tethering et setup VoIP Linux.

3) Décisions:
- XAUUSD : checklist pré-trade obligatoire ; si un point critique manque → PAS DE TRADE.
- XAUUSD (V2.1) : règles “NO TRADE” si drawdown > -5%, winrate 20 derniers trades < 45%, checklist non respectée ; losing streak ≥ 3 → risque -50%.
- FTMO : EURUSD uniquement ; max 2 trades/jour ; stop de journée à +1R ou -1R ; risque fixe 0.5% (250$) ; pas de trading pendant news rouges (couper 10–15 min avant/après).
- BTC bear : lecture contrarienne (news bullish + indicateurs rouges) ; privilégier short majeur M4 (févr–avr 2026) ; ne plus shorter en M6+ (préparer accumulation).
- Debian/cgminer : Debian 12 netinst amd64, installation minimale sans GUI ; autostart via script + systemd/rc.local.

4) Commandes / Code:
```bash
# Debian post-install
apt update && apt upgrade -y
apt install -y git build-essential libusb-1.0-0-dev pkg-config

# cgminer (GekkoScience)
git clone https://github.com/ckolivas/cgminer.git
cd cgminer
./autogen.sh
CFLAGS='-O2' ./configure --enable-gekko
make
make install

# test détection ASIC USB
cgminer -n
```

```bash
# Docker (Debian) + BlockDAG (archive)
apt update && apt upgrade -y
apt install -y ca-certificates curl gnupg lsb-release apt-transport-https software-properties-common
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker
systemctl start docker

cd /opt
git clone https://github.com/BlockdagNetworkLabs/blockdag-scripts.git
cd blockdag-scripts
# .env
# PUB_ETH_ADDR=0xVOTRE_ADRESSE_EVM
# CHAIN=awakening
docker compose up -d
docker ps
docker logs -f
```

5) Points ouverts (next):
- Compléter les onglets Google Sheets (Settings : solde, risque %, valeur lot XAUUSD) et commencer à journaliser (Trades_Reels / Backtests).
- Renseigner les valeurs manquantes du tableau “Compte / Solde initial / Risque % / Valeur XAUUSD”.
- Pour l’algo “BEAR■EATER” : définir et fournir les données exactes (funding, Fear & Greed précis, structure HTF).
- Mettre en place concrètement l’autostart cgminer (création `start-cgminer.sh` + service systemd) avec paramètres pool.
- BlockDAG/VoIP : éléments marqués “ARCHIVE — à utiliser plus tard” (pas d’exécution réalisée dans le dump).

## 2026-02-15 15:19 | TV Webhook | TEST | BTCUSDT.P 1H | BUY
1. **Signal**: `BUY`
2. **Engine**: `TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `1H`
4. **Price**: `1`
5. **TP**: `2`
6. **SL**: `0`
7. **Payload brut**:
```json
{"engine": "TEST", "signal": "BUY", "symbol": "BTCUSDT.P", "tf": "1H", "price": 1, "tp": 2, "sl": 0}
```

## 2026-02-15 15:31 | TV Webhook | NGROK_TEST | BTCUSDT.P 1H | SELL
1. **Signal**: `SELL`
2. **Engine**: `NGROK_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `1H`
4. **Price**: `999`
5. **TP**: `888`
6. **SL**: `777`
7. **Payload brut**:
```json
{"engine": "NGROK_TEST", "signal": "SELL", "symbol": "BTCUSDT.P", "tf": "1H", "price": 999, "tp": 888, "sl": 777}
```

## 2026-02-15 16:00 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `68420`
5. **TP**: `0`
6. **SL**: `0`
7. **Payload brut**:
```json
{"engine": "TV_TEST", "signal": "BUY", "symbol": "BTCUSDT.P", "tf": "60", "price": 68420, "tp": 0, "sl": 0}
```

## 2026-02-15 17:04 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY

1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `1.0`
5. **TP**: `2.0`
6. **SL**: `0.0`
7. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 1.0,
  "tp": 2.0,
  "sl": 0.0
}
```

## 2026-02-15 17:13 | TV Webhook | COINM_SHORT | BTCUSDT.P 60 | SELL

1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `68000.0`
5. **TP**: `67000.0`
6. **SL**: `69000.0`
7. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 68000.0,
  "tp": 67000.0,
  "sl": 69000.0
}
```

## 2026-02-15 17:26 — multi-moteur auto-algo
1) Objectifs:
- Formaliser un système multi-moteur: short crypto en COIN-M (accumulation), long crypto en USDT-M (bull confirmé), achat CFD Gold.
- Transformer les signaux TradingView “Smart Money” en alertes webhook vers un serveur Debian, avec journalisation automatique.
- Mettre en place un router côté serveur (secret + lock moteur) et valider le pipeline end-to-end via ngrok.

2) Actions:
- Analyse multi-actifs (BTC/ETH/SOL/XAU) et définition des zones/conditions:
  - BTC short pullback 68600–68900, invalidation > 69200, TP 67200/66200/65000.
  - ETH short pullback 1955–1970, invalidation > 2020, TP 1920/1900/1850.
  - Gold buy pullback 5033–5035, invalidation < 5025 (M15 close), TP 5055/5065/5075.
- Codage d’un pseudo-algo Python (offline) + correction d’exécution: Python collé dans bash → nécessité d’exécuter via `python3`/fichier `.py`.
- Contrainte TradingView: indicateur Smart Money original en lecture seule → recoder un clone Pine “bulletproof” (éviter ternary multi-lignes) jusqu’à compilation OK.
- Mise en place d’alertes TradingView:
  - Compréhension que `alert()` nécessite une alerte TradingView “Any alert() function call” (et non 2 alertes `alertcondition()` BUY/SELL).
  - Ajout d’un test manuel (TV_TEST) pour valider l’envoi.
- Mise en place serveur Debian:
  - Création venv + installation `fastapi`, `uvicorn`.
  - Création `webhook_server.py` (FastAPI) écrivant dans `/opt/trading/journal.md`.
  - Tests locaux `curl` → OK.
- Exposition Internet:
  - Installation/usage ngrok sur Debian.
  - Validation ngrok → Debian via `curl` sur URL publique → OK.
  - Debug TradingView via ngrok dashboard `127.0.0.1:4040` → preuve que TradingView n’envoyait pas tant que l’alerte “Any alert() function call” n’était pas correctement utilisée.
  - Réception confirmée d’un payload `TV_TEST` dans `journal.md`.
- Sécurisation/Router (étape 2.2):
  - Ajout secret côté serveur (clé attendue dans le JSON).
  - Mise en place d’un router: normalisation payload, raw logs JSONL, state/lock moteur (agressifs: COINM_SHORT, USDTM_LONG).
  - Résolution conflit port 8000 “address already in use” + validation `/docs` + `lsof -i :8000`.
  - Validation router via `curl` avec `key` → OK; state reste null tant que moteur non agressif (TV_TEST).

3) Décisions:
- Pipeline retenu: TradingView (Pine clone) = moteur de signaux → webhook JSON → ngrok → FastAPI Debian → append journal.
- Une seule alerte TradingView par chart: “Any alert() function call” avec message `{{alert_message}}`.
- Choix de l’étape suivante: scripts Pine séparés par moteur (option B) plutôt qu’un seul multi-engine.
- Activation d’un “engine lock” côté serveur pour éviter 2 moteurs agressifs simultanés.

4) Commandes / Code:
```bash
# Python venv + deps
cd /opt/trading
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-dotenv

# Lancer serveur
python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000

# Vérifier API
curl http://127.0.0.1:8000/docs
lsof -i :8000

# Test local webhook
curl -X POST http://127.0.0.1:8000/tv \
  -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"TV_TEST","signal":"BUY","symbol":"BTCUSDT.P","tf":"60","price":1,"tp":2,"sl":0}'

tail -n 25 /opt/trading/journal.md

# Test via ngrok URL publique
curl -X POST https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv \
  -H "Content-Type: application/json" \
  -d '{"engine":"NGROK_TEST","signal":"SELL","symbol":"BTCUSDT.P","tf":"1H","price":999,"tp":888,"sl":777}'

# Inspect requêtes ngrok
curl -s http://127.0.0.1:4040/api/requests/http | head

# Reset lock moteur (state)
echo '{"active_engine": null, "updated_at": null}' > /opt/trading/state/router_state.json
cat /opt/trading/state/router_state.json
```

```pine
// Pine: JSON construit en une seule ligne dans les blocs BUY/SELL (évite erreurs multi-lignes)
// Exemple (dans buy/sell condition):
json_msg = "{\"engine\":\"TV_TEST\",\"signal\":\"BUY\",\"symbol\":\"" + syminfo.ticker + "\",\"tf\":\"" + timeframe.period + "\",\"price\":" + str.tostring(close) + ",\"tp\":0,\"sl\":0}"
alert(json_msg, alert.freq_once_per_bar)
```

5) Points ouverts (next):
- Finaliser Étape 2 (router): valider state+lock sur moteurs agressifs (COINM_SHORT puis tentative USDTM_LONG → attendu 409) et définir procédure “reset lock” standard.
- Étape 1 (Pine prod): livrer 3 scripts Pine séparés (COINM_SHORT / USDTM_LONG / GOLD_CFD_LONG) intégrant `key` et payload complet, retirer debug/test.
- Côté TradingView: s’assurer que l’unique alerte “Any alert() function call” est active sur chaque chart/script et que l’URL webhook inclut `/tv`.
- (Optionnel) Durcir la sécurité (au-delà du `key`): limitation IP, rotation secret, ou signature.
- Stabiliser l’exécution (systemd pour uvicorn + démarrage ngrok/tunnel) si objectif “always-on”.

## 2026-02-15 18:31 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY

1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `111.0`
5. **TP**: `222.0`
6. **SL**: `333.0`
7. **Reason**: restart_ok
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 111.0,
  "tp": 222.0,
  "sl": 333.0,
  "reason": "restart_ok"
}
```

## 2026-02-15 18:42 — multi algo suite
1) Objectifs:
- Formaliser un plan multi-moteur : short crypto en COIN-M, long crypto en USDT-M (conditionnel), achat CFD Gold.
- Automatiser la génération de signaux “type TradingView” via alertes + webhook, puis journalisation automatique sur Debian.

2) Actions:
- Analyse multi-actifs (BTC/ETH/SOL/XAU) et définition des zones/invalidations/targets + règles de gestion (TP1/BE, levier, 1 position/coin).
- Codage d’une logique “moteurs” en Python (pseudo algo) puis correction d’exécution (Python collé dans bash → mise en fichier + exécution Python).
- Constat indicateur SMC en lecture seule → recodage d’un clone Pine “bulletproof” (éviter ternaires multi-lignes, concat fragiles).
- Mise en place pipeline : TradingView alert() → webhook ngrok → serveur FastAPI → écriture dans `/opt/trading/journal.md`.
- Debug TradingView : nécessité d’une alerte unique **Any alert() function call** pour capter `alert()` (plutôt que 2 alertconditions).
- Installation/validation côté Debian :
  - venv + `fastapi`, `uvicorn`, `python-dotenv`
  - serveur `webhook_server.py`
  - tests `curl` local + via URL ngrok
  - inspection des requêtes via ngrok API `127.0.0.1:4040`
- Ajout d’un secret `key` (clé partagée) côté serveur + obligation d’inclure `key` dans le JSON Pine.
- Implémentation router (logs bruts JSONL, état lock moteur, journal formaté).
- Validation : `/docs` OK, endpoint `/tv` OK, écriture journal OK, lock testé (COINM_SHORT active_engine, USDTM_LONG → 409), reset lock via écriture du state JSON.
- Passage “GO PROD” : suppression des toggles TEST/DEBUG et livraison de 3 scripts Pine PROD (COINM_SHORT SELL only, USDTM_LONG BUY only, GOLD_CFD_LONG BUY only) avec JSON one-liner incluant `key`, `engine`, `signal`, `symbol`, `tf`, `price`, `tp`, `sl`, `reason`.

3) Décisions:
- Utiliser **1 alerte TradingView par script** : `Any alert() function call` + message `{{alert_message}}` + webhook URL `.../tv`.
- Choix architecture Pine : **B = 3 scripts séparés** (COINM_SHORT / USDTM_LONG / GOLD_CFD_LONG) plutôt qu’un script multi-engine.
- Garder le lock backend disponible mais ne pas le “gérer” opérationnellement tout de suite (discipline : 1 moteur agressif à la fois).
- Utiliser ngrok sur Debian (TradingView sur Windows) pour rendre le webhook accessible publiquement.

4) Commandes / Code:
```bash
# venv + deps
cd /opt/trading
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-dotenv

# démarrage serveur
python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000

# vérification
curl http://127.0.0.1:8000/docs
lsof -i :8000

# test local
curl -X POST http://127.0.0.1:8000/tv \
  -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"TV_TEST","signal":"BUY","symbol":"BTCUSDT.P","tf":"60","price":1,"tp":2,"sl":0,"reason":"manual_test"}'

tail -n 25 /opt/trading/journal.md

# test via ngrok (URL publique)
curl -X POST https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv \
  -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"NGROK_TEST","signal":"SELL","symbol":"BTCUSDT.P","tf":"1H","price":999,"tp":888,"sl":777,"reason":"ngrok_test"}'

# inspect requêtes ngrok
curl -s http://127.0.0.1:4040/api/requests/http | head

# lock reset (state)
echo '{"active_engine": null, "updated_at": null}' > /opt/trading/state/router_state.json
cat /opt/trading/state/router_state.json
```

```pine
// JSON Pine: version stable en 1 ligne (évite erreurs multi-lignes)
f_json(_signal, _tp, _sl, _reason) =>
    "{\"key\":\"" + key + "\",\"engine\":\"" + engine + "\",\"signal\":\"" + _signal + "\",\"symbol\":\"" + syminfo.ticker + "\",\"tf\":\"" + timeframe.period + "\",\"price\":" + str.tostring(close) + ",\"tp\":" + str.tostring(_tp) + ",\"sl\":" + str.tostring(_sl) + ",\"reason\":\"" + _reason + "\"}"
```

5) Points ouverts (next):
- Always-on : créer services systemd pour `uvicorn` + `ngrok` (chemin binaire ngrok à confirmer via `which ngrok`).
- Nettoyage du journal `/opt/trading/journal.md` (il contient des sections/commandes “parasites” en haut).
- Vérifier en live que chaque script Pine PROD envoie bien `key` et que le serveur refuse sans key (403).
- Finaliser la procédure opérationnelle : quand/qui fait `reset lock`, et conventions `reason`/naming pour le routage.

## 2026-02-15 18:53 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY

1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `111.0`
5. **TP**: `222.0`
6. **SL**: `333.0`
7. **Reason**: post_restart_smoke
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 111.0,
  "tp": 222.0,
  "sl": 333.0,
  "reason": "post_restart_smoke"
}
```

## 2026-02-15 18:59 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY

1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `111.0`
5. **TP**: `222.0`
6. **SL**: `333.0`
7. **Reason**: post_restart_smoke
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 111.0,
  "tp": 222.0,
  "sl": 333.0,
  "reason": "post_restart_smoke"
}
```

## 2026-02-15 19:05 — ngrok
1) Objectifs:
- Confirmer le fonctionnement end-to-end du webhook TradingView via ngrok après restart (ngrok → FastAPI/Uvicorn → journal).
- Passer les services en mode always-on (systemd) et valider l’URL publique.
- Préparer la vérification du “fire” réel depuis TradingView (Windows).

2) Actions:
- Restart du service FastAPI: `tv-webhook.service` (écoute sur `*:8000`).
- Identification d’un ngrok lancé en manuel (`pgrep -a ngrok`), arrêt (`pkill ngrok`), puis démarrage du service systemd `ngrok-tv.service`.
- Vérification du tunnel via l’API ngrok `127.0.0.1:4040/api/tunnels` (URL publique active).
- Vérification que l’inspect buffer ngrok est vide après restart.
- Smoke test POST externe via l’URL ngrok sur `/tv` avec payload JSON incluant `key`.
- Contrôle: inspect ngrok (`/api/requests/http`) devient non vide + nouvelle entrée ajoutée à `/opt/trading/journal.md`.
- Validation finale: “GO TradingView”, attente d’un vrai déclenchement d’alerte TV.

3) Décisions:
- Mettre FastAPI (uvicorn) et ngrok en services systemd (always-on), avec un seul ngrok actif (éviter le manuel + service en parallèle).
- URL webhook TradingView à utiliser: `https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv`
- Configuration TradingView par script: Condition “Any alert() function call”, Message `{{alert_message}}`.
- Prochaine étape: attendre un “fire” réel TradingView (tests curl déjà OK).

4) Commandes / Code:
```bash
sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager

pgrep -a ngrok
pkill ngrok

sudo systemctl restart ngrok-tv.service
sudo systemctl status ngrok-tv.service --no-pager

curl -s http://127.0.0.1:4040/api/tunnels | python -m json.tool | head -n 60
curl -s http://127.0.0.1:4040/api/requests/http | head -c 400 ; echo

lsof -i :8000

# Smoke test externe via ngrok
curl -s -X POST https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv \
  -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"TV_TEST","signal":"BUY","symbol":"BTCUSDT.P","tf":"60","price":111,"tp":222,"sl":333,"reason":"post_restart_smoke"}' ; echo

tail -n 30 /opt/trading/journal.md

# Ops/monitoring
sudo systemctl status tv-webhook.service --no-pager
sudo systemctl status ngrok-tv.service --no-pager
journalctl -u tv-webhook.service -n 40 --no-pager
```

5) Points ouverts (next):
- Attendre un déclenchement réel d’une alerte TradingView et vérifier:
  - hit entrant ngrok (`/api/requests/http`)
  - ajout dans `/opt/trading/journal.md`
- Si hit ngrok sans entrée journal: diagnostiquer via `journalctl -u tv-webhook.service` (ex: 403 key/validation).

## 2026-02-15 21:09 | TV Webhook | TV_TEST | BTCUSDT.P 60 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `BTCUSDT.P` / `60`
4. **Price**: `111.0`
5. **TP**: `222.0`
6. **SL**: `333.0`
7. **Reason**: dash_test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 111.0,
  "tp": 222.0,
  "sl": 333.0,
  "reason": "dash_test",
  "_ts": "2026-02-16T02:09:52.457166+00:00",
  "_ip": "127.0.0.1"
}
```

## 2026-02-15 23:03 | TV Webhook | GOLD_CFD_LONG | XAUUSD 15 | BUY
1. **Signal**: `BUY`
2. **Engine**: `GOLD_CFD_LONG`
3. **Symbol/TF**: `XAUUSD` / `15`
4. **Price**: `2000.0`
5. **TP**: `2010.0`
6. **SL**: `1995.0`
7. **Reason**: tg_test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "GOLD_CFD_LONG",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "15",
  "price": 2000.0,
  "tp": 2010.0,
  "sl": 1995.0,
  "reason": "tg_test",
  "_ts": "2026-02-16T04:03:23.857657+00:00",
  "_ip": "127.0.0.1"
}
```

## 2026-02-16 00:06 | TV Webhook | XAU_M5_SCALP | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `XAU_M5_SCALP`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `2000.0`
5. **TP**: `2007.0`
6. **SL**: `1995.0`
7. **Reason**: branch test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "XAU_M5_SCALP",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 2000.0,
  "tp": 2007.0,
  "sl": 1995.0,
  "reason": "branch test",
  "_ts": "2026-02-16T05:06:11.563799+00:00",
  "_ip": "127.0.0.1",
  "qty": 0,
  "risk_usd": 0.0,
  "risk_real_usd": 0
}
```

## 2026-02-16 00:09 — algo 3
1) Objectifs:
- Ajouter un module “Performance” monitor-only (sans broker, sans exécution auto) : ledger trades, KPI (R, PnL théorique), equity curve simulée, drawdown.
- Brancher automatiquement le risk sizing (tv-webhook) vers perf via un event OPEN.

2) Actions:
- Création et déploiement du microservice `perf` (FastAPI + SQLite) avec endpoints `/perf/event`, `/perf/summary`, `/perf/equity`.
- Correction d’erreur systemd: `perf.service` avait été créé comme répertoire → suppression + recréation comme fichier.
- Correction d’exécution systemd: `perf.service` utilisait `/usr/bin/python3` (sans uvicorn) → bascule vers python du venv `/opt/trading/venv/bin/python`.
- Tests fonctionnels perf:
  - OPEN OK → retour `trade_id`.
  - CLOSE OK après correction du `trade_id` réel.
  - Vérification KPI/equity OK (ex: pnl=0.7, R=0.14, equity=10000.7).
- “Branch” perf dans `tv-webhook`:
  - Identification du service: `ExecStart=/opt/trading/venv/bin/python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000`
  - Ajout (prévu/indiqué) de `risk_quote(...)` + appel `perf_open(...)` dans l’endpoint `@app.post("/tv")`, avant création de `evt`.
  - Redémarrage `tv-webhook.service` OK.
- Test POST `/tv` a échoué (`Invalid secret`) car la clé webhook n’était pas la bonne.
- Lecture de la clé `.env` bloquée sans sudo → instruction de lire via `sudo grep ... /opt/trading/.env`.

3) Décisions:
- Rejeter l’alerte Telegram “no activity” (non prioritaire).
- Conserver une intégration non bloquante: l’envoi vers perf ne doit jamais casser le webhook (try/except).

4) Commandes / Code:
```bash
# Services
sudo systemctl status perf.service --no-pager
sudo systemctl daemon-reload
sudo systemctl enable --now perf.service
sudo systemctl restart perf.service
sudo journalctl -u perf.service -n 200 --no-pager -o cat

sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager
sudo systemctl cat tv-webhook.service
sudo journalctl -u tv-webhook.service -n 80 --no-pager -o cat

# Tests perf
curl -s http://127.0.0.1:8010/perf/summary | python -m json.tool
curl -s http://127.0.0.1:8010/perf/event -H "Content-Type: application/json" -d '{...}' | python -m json.tool
curl -s http://127.0.0.1:8010/perf/equity | python -m json.tool

# Recherche dans le code tv-webhook
grep -n "risk_" -n /opt/trading/webhook_server.py | head -n 50
grep -n "qty" /opt/trading/webhook_server.py | head -n 50
grep -n "size" /opt/trading/webhook_server.py | head -n 50

# Récupération de la clé webhook (permission)
sudo grep -E '^(TV_WEBHOOK_KEY|WEBHOOK_KEY|SECRET|TV_SECRET|KEY)=' /opt/trading/.env
sudo grep -iE 'key|secret|token|webhook' /opt/trading/.env
```

```python
# Insertion recommandée dans /tv (avant evt = {...})
q = risk_quote(engine, price=price, sl=sl, tp=tp) if (price and sl) else None
if not q:
    raise HTTPException(status_code=400, detail="Missing/invalid price or sl for risk sizing")

side = "LONG" if signal == "BUY" else "SHORT"

perf_open(
    engine=engine,
    symbol=symbol,
    side=side,
    entry=price,
    stop=sl,
    qty=q["qty"],
    risk_usd=q.get("risk_usd", 0.0),
    meta={"tf": tf, "tp": tp, "reason": reason, "src": "/tv"}
)
```

5) Points ouverts (next):
- Lire la clé webhook dans `/opt/trading/.env` via `sudo`, puis retester POST `/tv` avec la vraie key pour valider le branch end-to-end (OPEN créé dans perf + `last_event_ts` mis à jour).
- Confirmer que `risk_quote` retourne des valeurs valides pour l’engine utilisé (sinon choisir un engine existant dans `risk_config.json`).
- (Optionnel) Ajouter un endpoint `/perf/open` pour lister les trades OPEN et faciliter la récupération des `trade_id` pour CLOSE manuel.

## 2026-02-16 00:11 — algo 5
1) Objectifs:
- Continuer la session “analyse technique multi-actifs” sans alourdir le navigateur.
- Valider la chaîne TradingView → ngrok → FastAPI (/tv) → écriture journal, en mode always-on (systemd).

2) Actions:
- Smoke test webhook via URL publique ngrok (`POST /tv`) et vérification du retour `{"ok":true}`.
- Vérification des requêtes entrantes via l’API d’inspection ngrok (`127.0.0.1:4040`).
- Vérification de l’écriture dans `/opt/trading/journal.md` (entrée ajoutée avec payload).
- Redémarrage et vérification des services systemd:
  - `tv-webhook.service` (Uvicorn/FastAPI sur `*:8000`)
  - `ngrok-tv.service` (tunnel vers `http://localhost:8000`)
- Kill d’un ngrok lancé en ligne de commande puis relance via service systemd.
- Vérification process/ports (`pgrep -a ngrok`, `lsof -i :8000`) et tunnels ngrok (`/api/tunnels`).
- Consultation `journalctl` confirmant des `POST /tv` en `200 OK`; observation d’anciens essais “address already in use” avant stabilisation.

3) Décisions:
- Stack validé “always-on” via systemd (FastAPI + ngrok).
- Attendre un déclenchement réel d’une alerte TradingView (Windows) pour confirmer la chaîne complète.
- Repo GitHub public laissé tel quel pour le moment (pas de refactor/structure maintenant).

4) Commandes / Code:
```bash
# smoke test externe via ngrok
curl -s -X POST https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv \
  -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"TV_TEST","signal":"BUY","symbol":"BTCUSDT.P","tf":"60","price":111,"tp":222,"sl":333,"reason":"post_restart_smoke"}' ; echo

# inspect ngrok
curl -s http://127.0.0.1:4040/api/requests/http | head
curl -s http://127.0.0.1:4040/api/requests/http | head -c 300 ; echo
curl -s http://127.0.0.1:4040/api/tunnels | python -m json.tool | head -n 60

# journal
tail -n 20 /opt/trading/journal.md
tail -n 30 /opt/trading/journal.md

# services
sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager
sudo systemctl restart ngrok-tv.service
sudo systemctl status ngrok-tv.service --no-pager

# process/ports
pgrep -a ngrok
pkill ngrok
lsof -i :8000

# logs services
journalctl -u tv-webhook.service -n 40 --no-pager
journalctl -u tv-webhook.service -n 80 --no-pager
journalctl -u ngrok-tv.service -n 50 --no-pager
```

```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "BTCUSDT.P",
  "tf": "60",
  "price": 111.0,
  "tp": 222.0,
  "sl": 333.0,
  "reason": "post_restart_smoke"
}
```

5) Points ouverts (next):
- Attendre un “fire” réel TradingView et vérifier:
  - hit entrant ngrok (`curl http://127.0.0.1:4040/api/requests/http`)
  - nouvelle entrée dans `/opt/trading/journal.md`
- Si hit ngrok sans entrée journal: diagnostiquer via `journalctl -u tv-webhook.service` (ex: 403 key/validation).

## 2026-02-16 00:12 — algo 6
1) Objectifs:
- Formaliser un système multi-moteur: SHORT crypto en COIN-M, LONG crypto en USDT-M, LONG Gold CFD.
- Automatiser la journalisation via TradingView → webhook → Debian.
- Mettre en place: sécurité (secret), router/lock, always-on (systemd + ngrok), dashboard live, sizing risque, perf live + Telegram (sans exécution auto).

2) Actions:
- Analyse multi-actifs initiale (BTC/ETH/SOL/XAU) et définition des zones/invalidations/targets.
- Création d’une logique pseudo-algo Python (MarketState/Signal/engines), puis correction d’erreur d’exécution (Python collé dans bash).
- Décision d’utiliser TradingView alerts (webhook) plutôt que prix manuels dans Python.
- Re-codage d’un clone Pine “bulletproof” (problèmes Pine multi-lignes/ternaires), puis passage à JSON webhook.
- Mise en place serveur FastAPI (venv + deps), endpoint `/tv`, écriture journal `/opt/trading/journal.md`.
- Validation pipeline:
  - Test local `curl` → OK (`{"ok":true}`) + entrée journal.
  - Exposition via ngrok + test public `NGROK_TEST` → OK.
  - Debug TradingView: nécessité d’une alerte unique **Any alert() function call** pour capter `alert()`; test `TV_TEST` confirmé dans journal.
- Ajout d’un secret “key” obligatoire côté serveur (403 sinon), et adaptation des scripts Pine pour inclure `key`.
- Mise en place d’un router côté serveur:
  - Raw logs JSONL.
  - `router_state.json` pour lock (1 moteur agressif à la fois) + test 409.
  - Reset lock via écriture du state.
- Déploiement always-on:
  - `tv-webhook.service` (uvicorn) + `ngrok-tv.service`.
  - Résolution des conflits: port 8000 déjà utilisé + ERR_NGROK_334 (endpoint ngrok déjà online) en tuant l’instance manuelle puis redémarrant uniquement les services.
- Dashboard live:
  - Ajout `events.jsonl`, endpoints `/api/state`, `/api/events`, `/api/metrics`, page `/dash`.
  - Clarification que `curl -I` (HEAD) sur `/dash` retourne 405 car endpoint en GET.
- Risk sizing:
  - Création `risk_config.json` (crypto equity 6000$ risk 1%, gold equity 1500$ risk 1%, min 0.1 unité, step 0.1).
  - Correction du serveur pour lire `equity` + `risk_pct` au bon format (normalisation).
  - Test sizing Gold: `risk_usd=15`, distance=5 → `qty=3` (oz) + webhook `tg_test`.
- Telegram:
  - Ajout variables d’environnement + envoi Telegram sur signal (validation).
- Performance live (virtual):
  - Demande “go performance” et livraison d’un serveur qui gère:
    - Open/close virtuels (reverse) + fermeture sur BAR (TP/SL) si évènements “BAR” envoyés.
    - Stockage open/closed trades et endpoints perf.

3) Décisions:
- Architecture trading:
  - Short uniquement en COIN-M; long uniquement en USDT-M; Gold en CFD.
  - Priorité signal/approche “risk-off”: short crypto actif, gold pullback buy, long USDT en attente de reclaim.
- Architecture alertes:
  - Utiliser `alert()` + **1 alerte TradingView par script**: **Any alert() function call** + `{{alert_message}}` + webhook `/tv`.
  - Conserver GainzAlgo pour visuel (sans alertes), scripts PROD séparés pour alertes.
- Pine:
  - Choix **B = 3 scripts séparés** (COINM_SHORT / USDTM_LONG / GOLD_CFD_LONG).
  - JSON en **one-liner** (éviter erreurs Pine multi-lignes).
- Backend:
  - Secret obligatoire (403 sinon).
  - Lock backend disponible; pas forcément géré opérationnellement en continu.
- Pas d’exécution auto; monitoring + sizing + perf + Telegram.

4) Commandes / Code:
```bash
# venv + deps
cd /opt/trading
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-dotenv

# Lancer serveur
python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000

# Tests locaux
curl -X POST http://127.0.0.1:8000/tv -H "Content-Type: application/json" \
  -d '{"engine":"TEST","signal":"BUY","symbol":"BTCUSDT.P","tf":"1H","price":1,"tp":2,"sl":0}'
tail -n 40 /opt/trading/journal.md

# ngrok
ngrok http 8000
# Webhook URL (exemple)
# https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv

# Test public via ngrok
curl -X POST https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv \
  -H "Content-Type: application/json" \
  -d '{"engine":"NGROK_TEST","signal":"SELL","symbol":"BTCUSDT.P","tf":"1H","price":999,"tp":888,"sl":777}'

# Inspect requêtes ngrok
curl -s http://127.0.0.1:4040/api/requests/http | head

# Services systemd (restart/status)
sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager
sudo systemctl restart ngrok-tv.service
sudo systemctl status ngrok-tv.service --no-pager

# Vérifications
lsof -i :8000
curl -s http://127.0.0.1:8000/docs | head
curl -s http://127.0.0.1:4040/api/tunnels | python3 -m json.tool | head -n 60
```

```bash
# Reset lock
echo '{"active_engine": null, "updated_at": null}' > /opt/trading/state/router_state.json
cat /opt/trading/state/router_state.json
```

```json
// /opt/trading/state/risk_config.json (exemple utilisé)
{
  "accounts": {
    "COINM_SHORT": { "equity": 6000, "risk_pct": 0.01, "min_qty": 0.001, "qty_step": 0.001 },
    "USDTM_LONG":  { "equity": 6000, "risk_pct": 0.01, "min_qty": 0.001, "qty_step": 0.001 },
    "GOLD_CFD_LONG": { "equity": 1500, "risk_pct": 0.01, "min_units": 0.1, "units_step": 0.1 }
  },
  "gold_cfd": { "units_are_oz": true }
}
```

```bash
# Test sizing Gold
curl -s "http://127.0.0.1:8000/api/risk/quote?engine=GOLD_CFD_LONG&price=2000&sl=1995&tp=2010" | jq .

# Test webhook (signal)
curl -s -X POST http://127.0.0.1:8000/tv -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"GOLD_CFD_LONG","signal":"BUY","symbol":"XAUUSD","tf":"15","price":2000,"tp":2010,"sl":1995,"reason":"tg_test"}' | jq .
```

```pine
// JSON Pine stable 1 ligne (modèle utilisé)
f_json(_signal, _tp, _sl, _reason) =>
    "{\"key\":\"" + key + "\",\"engine\":\"" + engine + "\",\"signal\":\"" + _signal + "\",\"symbol\":\"" + syminfo.ticker + "\",\"tf\":\"" + timeframe.period + "\",\"price\":" + str.tostring(close) + ",\"tp\":" + str.tostring(_tp) + ",\"sl\":" + str.tostring(_sl) + ",\"reason\":\"" + _reason + "\"}"
```

5) Points ouverts (next):
- Sécurité: rotation du token Telegram (token exposé dans la conversation) + mise en place d’un `.env`/EnvironmentFile stable.
- Performance live: valider la stratégie de clôture (reverse vs BAR TP/SL) et définir si TradingView enverra des évènements “BAR” (high/low/close).
- Nettoyage du journal `/opt/trading/journal.md` (contenu “parasite” en haut).
- Standardiser `reason` / noms scripts / conventions (engine/symbol/tf) pour stats par moteur.
- (Option) Ajouter alerte Telegram d’inactivité (global ou par engine) et confirmer le comportement anti-spam.

## 2026-02-16 00:52 | TV Webhook | XAU_M5_SCALP | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `XAU_M5_SCALP`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `5032.5`
5. **TP**: `5040.0`
6. **SL**: `5026.5`
7. **Reason**: perf branch test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "XAU_M5_SCALP",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 5032.5,
  "tp": 5040.0,
  "sl": 5026.5,
  "reason": "perf branch test",
  "_ts": "2026-02-16T05:52:01.342650+00:00",
  "_ip": "127.0.0.1",
  "qty": 10.0,
  "risk_usd": 60.0,
  "risk_real_usd": 60.0
}
```

## 2026-02-16 02:03 — algo 7
1) Objectifs:
- Ajouter un module Performance (monitor-only) : ledger, R-multiple, PnL théorique/réalisé, equity curve simulée, KPIs par engine/global.
- Brancher le risk sizing existant (tv-webhook) vers perf via un POST OPEN.
- Ajouter endpoints utilitaires (/perf/open, /perf/trades) + mini UI /perf/ui.
- Garder zéro automation broker.

2) Actions:
- Création et déploiement d’un microservice FastAPI `perf_app.py` (SQLite + endpoints /perf/event, /perf/summary, /perf/equity) lancé par systemd `perf.service`.
- Correction d’erreur: un répertoire `perf.service` avait été créé au lieu d’un fichier → suppression + création correcte.
- Correction d’exécution systemd: `ExecStart` pointait sur `/usr/bin/python3` sans uvicorn → bascule vers le Python du venv `/opt/trading/venv/bin/python`.
- Tests OK perf:
  - OPEN via /perf/event → création trade_id.
  - CLOSE via /perf/event → calcul PnL et R; mise à jour /perf/summary et /perf/equity.
- Branchement tv-webhook (FastAPI `webhook_server:app`, endpoint `POST /tv`):
  - Ajout d’un call `perf_open(...)` après risk sizing (`risk_quote`) avec mapping BUY/SELL → LONG/SHORT.
  - Ajout d’un garde-fou: refuser le ledger si qty=0 ou risk=0.
- Debug /tv “Invalid secret”:
  - Lecture de la clé depuis `/opt/trading/.env` via `sudo`/subshell sans afficher la valeur.
- Debug risk sizing à 0 pour `XAU_M5_SCALP`:
  - Cause: engine absent de `state/risk_config.json` → `risk_usd=0`, `qty=0`.
  - Fix: ajout d’un compte `XAU_M5_SCALP` dans `state/risk_config.json` (equity=6000, risk_pct=0.01, min_units/units_step).
  - Validation JSON + re-test `risk_quote` → `risk_usd=60`, `qty=10`.
- Test end-to-end /tv → perf:
  - POST /tv (key auto) → création trade OPEN en DB perf (qty=10, risk=60).
  - CLOSE trade via /perf/event → /perf/summary: `pnl_realized=62.2`, equity=10062.2.
- Ajout demandé: endpoints utilitaires à ajouter à perf (`/perf/open`, `/perf/trades`) + proposition d’une page UI `GET /perf/ui`.
- Accès UI depuis Windows non possible via 127.0.0.1 → décision d’ouvrir depuis Debian (localhost).

3) Décisions:
- perf en microservice séparé, monitor-only, sans broker.
- Stockage SQLite + ledger d’événements.
- tv-webhook alimente perf via POST OPEN après `risk_quote` uniquement si sizing valide.
- Ajustement config risk: ajouter `XAU_M5_SCALP` dans `state/risk_config.json`.

4) Commandes / Code:
```bash
# Services / logs
sudo systemctl status perf.service --no-pager
sudo journalctl -u perf.service -n 200 --no-pager -o cat
sudo systemctl restart perf.service

sudo systemctl status tv-webhook.service --no-pager
sudo journalctl -u tv-webhook.service -n 200 --no-pager -o cat
sudo systemctl restart tv-webhook.service

# API perf
curl -s http://127.0.0.1:8010/perf/summary | python -m json.tool
curl -s http://127.0.0.1:8010/perf/equity  | python -m json.tool
curl -s http://127.0.0.1:8010/perf/event -H "Content-Type: application/json" -d '{...}'

# sqlite inspection
sqlite3 /opt/trading/perf/perf.db \
"select trade_id, engine, symbol, side, entry, stop, qty, risk_usd, entry_ts from trades where status='OPEN' order by entry_ts desc;"
sqlite3 /opt/trading/perf/perf.db \
"select trade_id, status, engine, symbol, side, entry, exit, pnl_real, r_real, entry_ts, exit_ts from trades order by entry_ts desc limit 20;"

# Tester /tv en chargeant la key depuis .env (sans afficher la valeur)
sudo bash -lc '
set -a
source /opt/trading/.env
set +a
K="${TV_WEBHOOK_KEY:-${WEBHOOK_KEY:-${TV_SECRET:-${SECRET:-${KEY:-}}}}}"
curl -s http://127.0.0.1:8000/tv -H "Content-Type: application/json" -d "{
  \"key\":\"$K\",
  \"engine\":\"XAU_M5_SCALP\",
  \"signal\":\"BUY\",
  \"symbol\":\"XAUUSD\",
  \"tf\":\"M5\",
  \"price\":5032.5,
  \"tp\":5040.0,
  \"sl\":5026.5,
  \"reason\":\"perf branch test\"
}" | python3 -m json.tool
'

# Test risk_quote local (important: depuis /opt/trading)
cd /opt/trading
/opt/trading/venv/bin/python - <<'PY'
from webhook_server import risk_quote
print(risk_quote("XAU_M5_SCALP", price=5032.5, sl=5026.5, tp=5040.0))
PY

# Validation JSON config
python3 -m json.tool /opt/trading/state/risk_config.json > /dev/null && echo "OK JSON"
```

```json
// state/risk_config.json: ajout du compte
"XAU_M5_SCALP": {
  "equity": 6000,
  "risk_pct": 0.01,
  "min_units": 0.1,
  "units_step": 0.1
}
```

```python
# webhook_server.py (/tv): garde-fou + envoi perf (bloc à placer avant evt = {...})
q = risk_quote(engine, price=price, sl=sl, tp=tp) if (price and sl) else None
if not q:
    raise HTTPException(status_code=400, detail="Missing/invalid price or sl for risk sizing")
if (not q.get("qty")) or ((q.get("risk_real_usd") or 0) <= 0 and (q.get("risk_usd") or 0) <= 0):
    raise HTTPException(status_code=400, detail="Risk quote invalid (qty/risk is 0)")
side = "LONG" if signal == "BUY" else "SHORT"
risk_for_perf = q.get("risk_real_usd") or q.get("risk_usd") or 0.0
perf_open(engine=engine, symbol=symbol, side=side, entry=price, stop=sl, qty=q["qty"], risk_usd=risk_for_perf,
          meta={"tf": tf, "tp": tp, "reason": reason, "src": "/tv"})
```

5) Points ouverts (next):
- Ajouter effectivement dans `perf_app.py` les endpoints:
  - `GET /perf/open`
  - `GET /perf/trades?limit=&engine=&status=&symbol=`
- Ajouter (si retenu) `GET /perf/ui` et valider affichage sur Debian.
- Décider stratégie d’accès Windows (SSH tunnel / bind 0.0.0.0 / ngrok) si besoin ultérieur.
- Éventuel: harmoniser `risk_usd` envoyé à perf (préférer `risk_real_usd`) partout.

## 2026-02-16 02:25 — algo 9
1) Objectifs:
- Reprendre la session Perf Control Center et diagnostiquer le problème “Send CLOSE” (405 / fermeture impossible) + valider le flux OPEN→CLOSE avec tv-webhook/ngrok.

2) Actions:
- Vérification UI Perf: http://127.0.0.1:8010/perf/ui accessible; métriques: total_trades=3, closed_trades=3, open_trades=0, winrate=100%, pnl_realized≈62.2, equity≈10062.2.
- Diagnostic 405: identifié que `curl -I` envoie HEAD; l’endpoint testait n’autorise que GET (allow: GET).
- Utilisation DevTools Réseau: corrigé l’erreur de contexte (DevTools ouvert sur l’onglet ChatGPT au lieu de l’onglet Perf), puis observation des requêtes réelles.
- Constat: aucune requête “close” n’apparaît au clic “Send CLOSE”; confirmé ensuite qu’il n’y avait aucun trade OPEN (`/perf/open` renvoie open=[]).
- Inspection OpenAPI: `/openapi.json` montre une seule route d’écriture `POST /perf/event` (type OPEN|CLOSE|UPDATE); pas de route dédiée `/perf/close`.
- Création d’un trade OPEN via `POST /perf/event`, puis tentative de fermeture via UI: UI affiche “missing trade_id or exit” malgré champs remplis (bug lecture des champs / placeholder).
- Application d’un patch UI (dans `perf/perf_app.py`) pour rendre la fermeture robuste (fallback placeholder pour exit).
- Fermeture validée via API: réponse `{ok:true, event_id:..., trade_id:..., ts:...}` puis vérification finale: `/perf/open` vide et trade en CLOSED dans `/perf/trades`.

3) Décisions:
- Standardiser l’écriture d’événements sur `POST /perf/event` (OPEN/CLOSE) côté UI; abandon de l’hypothèse d’un endpoint `/perf/close`.
- Corriger l’UI “Close trade” pour: lire correctement `trade_id` + `exit` et envoyer un `fetch` POST JSON vers `/perf/event`; gérer le cas exit non saisi (placeholder non envoyé).

4) Commandes / Code:
```bash
# Vérifier open trades et historique
curl -s http://127.0.0.1:8010/perf/open
curl -s "http://127.0.0.1:8010/perf/trades?limit=50"

# Inspecter l'OpenAPI pour trouver les routes
curl -s http://127.0.0.1:8010/openapi.json | head

# Créer un OPEN (test manuel)
curl -s -X POST "http://127.0.0.1:8010/perf/event" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "OPEN",
    "engine": "XAU_M5_SCALP",
    "symbol": "XAUUSD",
    "side": "LONG",
    "entry": 5032.5,
    "stop": 5026.5,
    "qty": 0.2,
    "risk_usd": 12.0,
    "meta": {"src":"manual_test"}
  }'

# Fermer (CLOSE) (test manuel)
curl -s -X POST "http://127.0.0.1:8010/perf/event" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "CLOSE",
    "trade_id": "T_20260216_015408_XAU_M5_SCALP_224a57",
    "exit": 5038.5,
    "meta": {"src":"manual_close"}
  }'

# Vérification finale
curl -s http://127.0.0.1:8010/perf/open
curl -s "http://127.0.0.1:8010/perf/trades?limit=5"
```

```bash
# Application patch fichier (procédure indiquée)
cp /opt/trading/perf/perf_app.py /opt/trading/perf/perf_app.py.bak
# cp /path/to/perf_app_patched.py /opt/trading/perf/perf_app.py
sudo systemctl restart tv-webhook.service
```

5) Points ouverts (next):
- Finaliser le correctif UI pour déclencher réellement un POST `/perf/event` au clic “Send CLOSE” et rafraîchir automatiquement summary/open/trades (sans reload).
- Confirmer le comportement ngrok/tv-webhook sur alertes TradingView (observer un POST entrant via `127.0.0.1:4040/api/requests/http`).

## 2026-02-16 04:18 — resume projet
1) Objectifs:
- Analyser le dépôt GitHub généré (Magikgmo) et en faire une synthèse “par sessions” depuis l’instauration de `jpt "titre"`.
- Présenter le projet (pitch) + identifier points à corriger/solidifier.
- Archiver la conversation en priorité via une entrée `jpt`.
- Produire un roadmap complet annoté + une indexation complète de la documentation.
- Proposer un README “MAIN” (doc maître) sans entrer trop dans les détails.
- Regrouper la documentation en un PDF imprimable, en éliminant les doublons.

2) Actions:
- Cartographie du repo (modules repérés) :
  - Journalisation JPT : `tools/journal_from_paste.py`, `journal.md`, `journal/2026-02-11.md`.
  - Webhook TradingView (FastAPI) : `webhook_server.py`, logs `logs/tv_webhooks.jsonl`, état `state/events.jsonl`, `state/risk_config.json`, `state/router_state.json`, UI `/dash`.
  - Module performance : `perf/perf_app.py`, SQLite `perf/perf.db`, endpoints + UI `/perf/ui`.
  - Jobs macro + Telegram : `jobs/macro_xau/` (dont `macro_xau.py` dupliqué), `shared/telegram_notify.py`.
  - Base “strategy/domain model” : `strategy_logic.py`.
- Synthèse “chronologie par sessions” (basée sur `journal/2026-02-11.md` + `journal.md`) : init serveur, validation journalisation, SSH GitHub, venv obligatoire, ngrok, ajout module perf, etc.
- Rédaction d’une proposition de structure de docs : `README.md`, `docs/INDEX.md`, `docs/ROADMAP.md`, `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md`, `docs/API.md`, `docs/SCHEMAS.md`, `docs/SECURITY.md`.
- Rédaction d’un roadmap annoté (L0→L7) + priorisation (Docs, Access Windows/LAN, Ops, Schémas, Risk, Engines, CI, Exécution optionnelle).
- Rédaction d’un contenu “README MAIN” (vision, composants, quickstart, workflow `jpt`, sécurité).
- Production annoncée d’un PDF imprimable consolidé (“Magikgmo_Project_Doc_2026-02-16.pdf”) incluant résumé, map repo, workflow JPT, architecture/routes, risk config, runbook, schémas, roadmap, checklist nettoyage/doublons.

3) Décisions:
- Ajouter une documentation “MAIN” stable + dossier `docs/` avec indexation stricte (docs par rôle, liens).
- Maintenir le workflow : chaque session = `jpt` + commit/push.
- Priorités techniques à solidifier : access Windows/LAN (bind/firewall), nettoyage duplications, schéma unique Event → Trade → Perf + adaptateur webhook→perf_event.
- Sécurité : ne pas exposer `/tv` sans clé (signature HMAC évoquée comme amélioration future).

4) Commandes / Code:
```bash
cd /opt/trading/Magikgmo
jpt "Archive — Analyse repo + présentation + roadmap complet (README MAIN)"
```

```bash
git status
git add journal.md
git commit -m "Archive: repo analysis + roadmap+readme main (2026-02-16)"
git push
```

```bash
mkdir -p docs
nano docs/ROADMAP.md
nano docs/INDEX.md
nano README.md
```

Exemples de quickstart/test mentionnés :
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python webhook_server.py
```

```bash
curl -s -X POST "http://127.0.0.1:8010/tv?key=$TV_WEBHOOK_KEY" \
  -H "Content-Type: application/json" \
  -d '{"engine":"XAU_M5_SCALP","symbol":"XAUUSD","side":"LONG","price":5032.5,"stop":5026.5}'
```

```bash
python perf/perf_app.py
```

```bash
curl -s http://127.0.0.1:8010/perf/event \
  -H "Content-Type: application/json" \
  -d '{"type":"CLOSE","trade_id":"T_EXAMPLE","exit":5040.0}'
```

5) Points ouverts (next):
- Accessibilité depuis Windows : vérifier bind `0.0.0.0` vs `127.0.0.1`, firewall/ports, reverse proxy si nécessaire.
- Nettoyage du code : duplication dans `jobs/macro_xau/macro_xau.py`, suspicion de sections “collées” dans `webhook_server.py`, doublons d’endpoints signalés.
- Normaliser un schéma unique : Event (TradingView) → Trade → Perf, versionné (`schema_version`) + écrire l’adaptateur `webhook_event → perf_event`.
- Formaliser services systemd, health endpoints, logrotate.
- Finaliser la doc consolidée (PDF imprimable) en supprimant les doublons (contenu et repo).

## 2026-02-16 05:01 — algo 10
1) Objectifs:
- Analyser le dépôt GitHub généré (cartographie modules + historique “par sessions”) et présenter le projet.
- Produire une doc complète (README MAIN + docs/*), une roadmap annotée/indexée, et archiver la conversation.
- Appliquer un patch “fixed.zip” avec nettoyage (doublons), ajout schémas/adaptateur/smoke tests, sans casser la prod.
- Mettre en place une routine de diagnostic (test + log) exécutable en une commande.

2) Actions:
- Cartographie repo : journalisation JPT, serveur webhook FastAPI, module perf (SQLite + UI), jobs macro XAU, notifications Telegram, base “strategy_logic”.
- Production de docs/plan : structure docs/INDEX.md, docs/ROADMAP.md, README MAIN; recommandation schéma unique Event→Trade→Perf + adaptateur webhook_event→perf_event.
- Patch initial appliqué puis rollback (erreur rsync avec `--delete` en source située dans la destination) ; restauration via backup tar.gz.
- Recréation venv et dépannage service systemd `tv-webhook.service` (erreurs `python introuvable`, puis `No module named uvicorn`).
- Reprise patch en mode “v2” par commits petits et sûrs :
  - Ajout `docs/`, `schemas/`, `scripts/smoke.sh` (commit `cc2f9fe`).
  - Ajout `adapters/webhook_to_perf.py` (commit `8ea0483`).
  - Fix `scripts/smoke.sh` (JSON invalide) via heredoc ; smoke OK (commit `8dfc416`).
- Création/exécution d’un script `scripts/diagnose.sh` qui logge statut git, venv, systemd, endpoints 8000/8010, smoke, et écrit un log horodaté dans `logs/diagnostics/`.
- Validation via diagnose :
  - Webhook OK sur `http://127.0.0.1:8000/api/state` (200).
  - Perf OK sur `http://127.0.0.1:8010/perf/summary` et `/perf/open` (200).
  - Smoke OK (création OPEN/CLOSE + vérification trade).

3) Décisions:
- Ne plus appliquer de patch global “rsync --delete” dans le repo ; préférer extraction source hors repo (`/tmp`) et application par lots/commits.
- Conserver `.env`, `state/`, `logs/`, `perf/perf.db`, `journal.md` hors écrasement lors des patchs.
- Maintenir 2 services/ports distincts : webhook (8000) et perf (8010).
- Mettre en place une routine “diagnose” + logs diagnostics.
- (À faire) Ajouter règles `.gitignore` pour éviter de versionner `perf/perf.db`, logs diagnostics et backups smoke.

4) Commandes / Code:
```bash
# Backup avant patch (snapshot)
cd /opt || exit 1
ts=$(date +%Y%m%d_%H%M%S)
sudo tar -czf "/opt/trading_BACKUP_${ts}.tar.gz" --exclude='trading/venv' --exclude='trading/__pycache__' trading
sudo tar -czf "/opt/trading_STATELOGS_${ts}.tar.gz" trading/state trading/logs trading/perf/perf.db 2>/dev/null || true

# Patch safe (source hors repo)
rm -rf /tmp/magikgmo_patch
mkdir -p /tmp/magikgmo_patch
unzip -q /opt/Magikgmo-main-fixed.zip -d /tmp/magikgmo_patch

# Rollback Git du patch global (force-push)
cd /opt/trading || exit 1
sudo systemctl stop tv-webhook.service 2>/dev/null || true
git reset --hard 4428c7d
git clean -fd
git push --force
sudo systemctl start tv-webhook.service 2>/dev/null || true

# Recréation venv + deps (quand venv cassé)
cd /opt/trading || exit 1
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip wheel
pip install -r requirements.txt
pip install "fastapi==0.115.6" "uvicorn[standard]==0.34.0"

# Reprise patch v2 (copie ciblée)
cd /opt/trading || exit 1
mkdir -p docs schemas scripts adapters
cp -a /tmp/magikgmo_patch/Magikgmo-main/docs/. docs/
cp -a /tmp/magikgmo_patch/Magikgmo-main/schemas/. schemas/
cp -a /tmp/magikgmo_patch/Magikgmo-main/scripts/smoke.sh scripts/
chmod +x scripts/smoke.sh
cp -a /tmp/magikgmo_patch/Magikgmo-main/adapters/webhook_to_perf.py adapters/

# Fix smoke.sh (heredoc JSON) + exécution
BASE=http://127.0.0.1:8010 ./scripts/smoke.sh

# Diagnose (script + exécution + log)
./scripts/diagnose.sh
tail -n 200 logs/diagnostics/diag_*.log

# Services
sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager -l
journalctl -u tv-webhook.service -n 80 --no-pager
```

5) Points ouverts (next):
- Ajouter/ajuster `.gitignore` pour : `perf/perf.db`, `logs/diagnostics/*.log`, `scripts/*.bak.*` (éviter pollution git).
- Vérifier/standardiser l’installation des dépendances runtime (fastapi/uvicorn) dans `requirements.txt` pour éviter casse lors d’un rebuild venv.
- Stabiliser la routine `diagnose.sh` (committer le fichier) et décider si les logs `logs/diagnostics/` doivent être exclus systématiquement.
- Continuer les “cleanups” ciblés (macro_xau.py, webhook_server.py, endpoints perf potentiellement dupliqués) fichier par fichier avec smoke entre chaque commit.
- Formaliser le schéma unique Event→Trade→Perf et brancher l’adaptateur dans le flux webhook (feature-flag).

## 2026-02-16 05:32 — algo 12
1) Objectifs:
- Analyser le dépôt GitHub généré (modules, structure, historique “JPT”).
- Archiver la conversation et produire une doc complète (README MAIN + docs indexées + roadmap).
- Appliquer un patch “fixed” sur le serveur Debian (backup, déploiement safe), sans casser l’existant.
- Stabiliser une routine de tests (smoke + diagnostic + logs) et l’automatiser.

2) Actions:
- Cartographie repo (journalisation JPT, webhook TradingView FastAPI, perf module SQLite+UI, jobs macro, Telegram, state/logs, strategy_logic).
- Génération de docs/ (INDEX, ROADMAP, RUNBOOK, API, SCHEMAS, ARCHITECTURE) + README MAIN ; création schemas/ et adapters/webhook_to_perf.py ; ajout scripts/smoke.sh.
- Tentative de patch via rsync avec `--delete` depuis un sous-dossier source situé dans la destination (`/opt/trading/_patch/...`) → suppression partielle/“vanished files” → restauration via backup tar.gz.
- Patch réappliqué correctement en extrayant le zip dans `/tmp` puis rsync avec exclusions (`.git/ state/ logs/ perf/perf.db .env journal.md`), commit/push, puis rollback Git (reset/force-push) vers commit pré-patch pour recommencer en petits commits.
- Recréation du venv (car `venv/bin/python` manquant), installation dépendances manquantes (uvicorn/fastapi), redémarrage systemd `tv-webhook.service` (203/EXEC puis “No module named uvicorn” résolus).
- Fix smoke.sh (JSON cassé) via heredoc ; identification que `curl -I` (HEAD) provoque 405 sur perf/webhook.
- Ajout/commit `.gitignore` pour ignorer `perf/perf.db`, backups smoke, logs diagnostics ; création + commit `scripts/diagnose.sh` (routine test+log) ; création `scripts/autos.sh` (restart+smoke+diagnose+ngrok checks).
- Vérification ngrok via API locale `:4040` (tunnel HTTPS public_url vers `localhost:8000`, hits visibles).
- Observation d’erreurs ngrok dans journaux (`ERR_NGROK_334 endpoint already online`) lors de restarts.

3) Décisions:
- Patcher en “v2” par petits commits (docs/schemas/smoke, puis adapter, puis cleanups ciblés) au lieu d’un rsync global.
- Toujours extraire le zip patch hors du repo (ex `/tmp`) si `rsync --delete` est utilisé.
- Exclure systématiquement `.git/ state/ logs/ perf/perf.db .env journal.md` lors des patchs.
- Stabiliser la routine de validation via scripts (smoke + diagnose + autos) et journaliser les sorties.

4) Commandes / Code:
```bash
# Backup avant patch (exclusion venv/pycache)
cd /opt || exit 1
ts=$(date +%Y%m%d_%H%M%S)
sudo tar -czf "/opt/trading_BACKUP_${ts}.tar.gz" --exclude='trading/venv' --exclude='trading/__pycache__' trading
sudo tar -czf "/opt/trading_STATELOGS_${ts}.tar.gz" trading/state trading/logs trading/perf/perf.db 2>/dev/null || true
```

```bash
# Erreur rencontrée: rsync absent puis installation (proposée)
sudo apt-get update
sudo apt-get install -y rsync unzip
```

```bash
# Restauration complète après rsync --delete mal utilisé
sudo systemctl stop tv-webhook.service 2>/dev/null || true
cd /opt || exit 1
sudo rm -rf /opt/trading
sudo tar -xzf /opt/trading_BACKUP_20260216_043219.tar.gz
sudo systemctl start tv-webhook.service 2>/dev/null || true
```

```bash
# Patch correct: source hors repo
rm -rf /tmp/magikgmo_patch
mkdir -p /tmp/magikgmo_patch
unzip -q /opt/trading/Magikgmo-main-fixed.zip -d /tmp/magikgmo_patch

cd /opt/trading || exit 1
rsync -avi --delete \
  --exclude '.git/' --exclude 'state/' --exclude 'logs/' --exclude 'perf/perf.db' \
  --exclude '.env' --exclude 'journal.md' \
  /tmp/magikgmo_patch/Magikgmo-main/ .
```

```bash
# Rollback Git vers commit avant patch + force push
cd /opt/trading || exit 1
sudo systemctl stop tv-webhook.service 2>/dev/null || true
git reset --hard 4428c7d
git clean -fd
git push --force
sudo systemctl start tv-webhook.service 2>/dev/null || true
```

```bash
# Recréation venv + deps
cd /opt/trading || exit 1
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
rm -rf venv
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip wheel
pip install -r requirements.txt
pip install "fastapi==0.115.6" "uvicorn[standard]==0.34.0"
sudo systemctl restart tv-webhook.service
```

```bash
# Smoke fix (heredoc JSON) + test
BASE=http://127.0.0.1:8010 ./scripts/smoke.sh
```

```bash
# Diagnose routine (création + exécution + logs horodatés)
./scripts/diagnose.sh
tail -n 200 logs/diagnostics/diag_*.log
```

```bash
# Ngrok checks
curl -s http://127.0.0.1:4040/api/tunnels | python -m json.tool | head -n 80
curl -s http://127.0.0.1:4040/api/requests/http | head -c 1200 ; echo
```

```bash
# Commits réalisés (exemples cités dans la conversation)
git commit -m "Docs+Schemas: add docs, schemas, smoke script"
git commit -m "Adapter: webhook_event -> perf_event"
git commit -m "Fix smoke: proper heredoc JSON payloads"
git commit -m "Chore: ignore perf db and smoke backups"
git commit -m "Chore: stop tracking perf db"
git commit -m "Add diagnose routine + ignore runtime logs/db"
```

5) Points ouverts (next):
- `scripts/autos.sh` laisse `scripts/autos.sh` non suivi (diagnose signale `?? scripts/autos.sh`) → décider de le committer.
- `diagnose.sh` relance parfois `smoke.sh` avec une base incorrecte (symptôme: smoke OK au début d’autos puis “SMOKE FAILED” dans diagnose) → à corriger en séparant WEBHOOK_BASE=8000 et PERF_BASE=8010 dans diagnose.
- ngrok: journaux `ERR_NGROK_334 endpoint already online` lors des restarts → éviter de restart ngrok si déjà actif (ou clarifier la stratégie de gestion du tunnel/service).
- Restes: modifications de smoke/diagnose faites via commandes “perl” fragiles (erreurs perl observées) → privilégier réécriture via heredoc/cat ou patch simple.

## 2026-02-16 06:03 — algo 13
1) Objectifs:
- Rendre l’UI perf accessible depuis Windows (LAN) et stabiliser les scripts de tests/diag.
- Déployer un patch depuis un ZIP sans casser l’existant (backups + systemd).

2) Actions:
- Déploiement “safe” depuis ZIP vers `/opt/trading` (backups + rsync `perf/` et `scripts/`).
- Création/activation du service `tv-perf.service` (Uvicorn) sur port 8010.
- Ajout d’un override systemd pour `tv-webhook.service` afin d’écouter sur `0.0.0.0:8000`.
- Ouverture “best effort” des ports 8000/8010 via `ufw`.
- Exécution smoke + diagnose; identification d’un échec `SMOKE FAILED` lié aux variables dans `diagnose.sh`.
- Côté Windows: clarification PowerShell vs bash, tests réseau (ping OK mais TCP 8010 KO).
- Diagnostic Debian: `tv-perf.service` en échec car `8010` déjà utilisé par un process Python bindé sur `127.0.0.1`.
- Kill du PID occupant 8010, reset-failed + restart du service, validation écoute `0.0.0.0:8010`.
- Validation UI sur Windows via `http://192.168.16.155:8010/perf/ui`.
- Lancement et réussite du test final end-to-end (services, ports, endpoints, UI, smoke, Windows).

3) Décisions:
- Standardiser l’accès Windows via IP Debian (pas `127.0.0.1`).
- Forcer les binds LAN: webhook `0.0.0.0:8000`, perf `0.0.0.0:8010` via systemd.
- Résoudre le blocage réseau Windows en supprimant le process “fantôme” sur 8010.
- Accepter que `HEAD /perf/ui` renvoie 405 (non bloquant) tant que GET UI fonctionne.

4) Commandes / Code:
```bash
# Déploiement (avec trap anti-fermeture terminal)
bash -lc '
set -Eeuo pipefail
trap '\''echo; echo "❌ ERREUR à la ligne $LINENO (code=$?)"; echo "➡️ Dernière commande: $BASH_COMMAND"; echo; read -r -p "Appuie Entrée pour fermer..." _; exit 1'\'' ERR

ROOT="/opt/trading"
ZIP="/home/ghost/Téléchargements/Magikgmo-main(1).zip"
cd "$ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
BK="$ROOT/backup/$TS"
mkdir -p "$BK"

cp -a "$ROOT/perf/perf_app.py" "$BK/perf_app.py.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-perf.service" "$BK/tv-perf.service.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-webhook.service" "$BK/tv-webhook.service.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-webhook.service.d" "$BK/tv-webhook.service.d.bak" 2>/dev/null || true

TMP="/tmp/magik_${TS}"
rm -rf "$TMP"
mkdir -p "$TMP"
unzip -q "$ZIP" -d "$TMP"

rsync -a "$TMP"/Magikgmo-main/perf/ "$ROOT"/perf/
rsync -a "$TMP"/Magikgmo-main/scripts/ "$ROOT"/scripts/

sudo tee /etc/systemd/system/tv-perf.service >/dev/null <<'\''EOF'\''
[Unit]
Description=Trading Perf API (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/trading
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=1
ExecStart=/opt/trading/venv/bin/python -m uvicorn perf.perf_app:app --host 0.0.0.0 --port 8010

[Install]
WantedBy=multi-user.target
EOF

sudo mkdir -p /etc/systemd/system/tv-webhook.service.d
sudo tee /etc/systemd/system/tv-webhook.service.d/override.conf >/dev/null <<'\''EOF'\''
[Service]
ExecStart=
ExecStart=/opt/trading/venv/bin/python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tv-perf.service
sudo systemctl restart tv-perf.service tv-webhook.service

sudo ufw allow 8000/tcp >/dev/null 2>&1 || true
sudo ufw allow 8010/tcp >/dev/null 2>&1 || true

BASE="http://127.0.0.1:8010" ./scripts/smoke.sh
./scripts/diagnose.sh || true

IP="$(hostname -I | awk "{print \$1}")"
echo "http://${IP}:8010/perf/ui"
'

# Correction diagnose.sh (variable attendue)
cp -a scripts/diagnose.sh scripts/diagnose.sh.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
perl -0777 -i -pe 's/\bPERF_BASE\b/BASE/g' scripts/diagnose.sh

# Conflit port 8010: process occupant (PID 78706)
sudo kill 78706 || true
sudo kill -9 78706 2>/dev/null || true
sudo systemctl reset-failed tv-perf.service || true
sudo systemctl restart tv-perf.service
sudo ss -lntp | grep :8010

# Validation stabilité
sudo systemctl status tv-perf.service --no-pager
sudo ss -lntp | grep :8010
```

```powershell
# Windows (PowerShell)
Test-NetConnection 192.168.16.155 -Port 8010
Invoke-WebRequest "http://192.168.16.155:8010/perf/summary"
Start-Process "http://192.168.16.155:8010/perf/ui"
```

```bash
# Test final Debian (end-to-end)
set -euo pipefail
cd /opt/trading

sudo systemctl is-active tv-perf.service
sudo systemctl is-active tv-webhook.service

sudo ss -lntp | grep -E ':8000|:8010'

curl -fsS http://127.0.0.1:8010/perf/summary >/dev/null && echo "OK /perf/summary"
curl -fsS http://127.0.0.1:8010/perf/open    >/dev/null && echo "OK /perf/open"
curl -fsS http://127.0.0.1:8010/perf/trades?limit=3 >/dev/null && echo "OK /perf/trades"

curl -fsS http://127.0.0.1:8010/perf/ui | head -c 40; echo
curl -sI  http://127.0.0.1:8010/perf/ui | head -n 1   # renvoie 405 (non bloquant)

BASE="http://127.0.0.1:8010" WEBHOOK_BASE="http://127.0.0.1:8000" ./scripts/smoke.sh
```

5) Points ouverts (next):
- Optionnel: supporter `HEAD` sur `/perf/ui` (actuellement `HTTP/1.1 405 Method Not Allowed`, non bloquant) ou ajuster le test pour utiliser GET uniquement.
- Optionnel: finaliser/standardiser définitivement `diagnose.sh` (variables BASE/PERF_BASE) si d’autres checks l’utilisent.

## 2026-02-16 06:12 — algo 15
1) Objectifs:
- Finaliser la solution Perf Control Center et continuer la session après interruption.
- Rendre l’UI /perf/ui accessible depuis Windows (LAN) et valider les endpoints.
- Éliminer le warning 405 lié à `HEAD /perf/ui` (optionnel).
- Prochaine étape visée: optimiser l’UI “direction pro”.

2) Actions:
- Clarification: `curl -I` envoie `HEAD` ⇒ `405 Method Not Allowed` car `/perf/ui` est GET-only.
- Recommandation appliquée: exposer FastAPI/uvicorn sur `0.0.0.0` + accès Windows via `http://IP_DEBIAN:8010/perf/ui` + ouverture firewall si nécessaire.
- Validation finale rapportée: services `tv-perf` et `tv-webhook` actifs; bind `0.0.0.0:8000` et `0.0.0.0:8010`; endpoints `/perf/summary`, `/perf/open`, `/perf/trades` OK; UI HTML OK; smoke test OPEN→CLOSE→verify OK; Windows TCP/UI OK.
- Choix et application de l’option “zéro warning”: remplacer le check HEAD par un GET.
- Tests exécutés: checks `curl` sur `/perf/ui` et `/perf/summary` retournent HTTP 200; `UI: PASS`.

3) Décisions:
- Considérer `405 sur HEAD /perf/ui` comme non bloquant.
- Choisir l’Option 1 (modifier le script de check pour faire un GET au lieu de HEAD).
- Next: optimisation UI (KPIs, tables, outils opérationnels, commandes utiles avec Copy/Open, form POST /perf/event, CSS/UX pro).

4) Commandes / Code:
```bash
# Service systemd (exemple ExecStart uvicorn) pour écoute LAN
ExecStart=/opt/trading/venv/bin/uvicorn webhook_server:app --host 0.0.0.0 --port 8010

sudo systemctl daemon-reload
sudo systemctl restart tv-webhook.service
sudo systemctl status tv-webhook.service --no-pager -l

# Firewall (si UFW actif)
sudo ufw allow 8010/tcp
```

```bash
# Checks GET (remplace le HEAD/curl -I)
curl -s http://127.0.0.1:8010/perf/ui >/dev/null && echo OK

curl -s -o /dev/null -w "UI /perf/ui HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/ui
curl -s -o /dev/null -w "API /perf/summary HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/summary

curl -sf http://127.0.0.1:8010/perf/ui >/dev/null && echo "UI: PASS" || echo "UI: FAIL"
```

5) Points ouverts (next):
- Identifier le fichier qui contient l’endpoint `@app.get("/perf/ui")` (chemin exact ou ~10 lignes autour) pour fournir un patch “copier-coller” d’une UI améliorée (KPIs, tables open/recent trades, bloc commandes utiles avec Copy/Open, mini form POST `/perf/event`, CSS, gestion erreurs, auto-refresh).

## 2026-02-16 06:12 — algo 16
1) Objectifs:
- Rendre l’UI Perf accessible depuis Windows (LAN) et stabiliser les services/systemd + scripts de diag/smoke.
- Valider un test final end-to-end (API + UI + smoke).

2) Actions:
- Déployé un patch depuis un ZIP vers `/opt/trading` (backup avant copie, `rsync` de `perf/` et `scripts/`).
- Créé/activé `tv-perf.service` (Uvicorn FastAPI) sur `0.0.0.0:8010`.
- Ajouté un override systemd pour `tv-webhook.service` sur `0.0.0.0:8000`.
- Ajouté un wrapper d’exécution `bash -lc` avec `trap ERR` pour éviter la fermeture du terminal lors d’erreurs (`set -Eeuo pipefail`).
- Exécuté `scripts/smoke.sh` + `scripts/diagnose.sh`; diag OK mais incohérence initiale (`SMOKE FAILED`) liée à variable `PERF_BASE`/`BASE`.
- Réparé `scripts/diagnose.sh` (remplacement `PERF_BASE` → `BASE` + fallback `BASE` si absent).
- Accident: `scripts/smoke.sh` a été corrompu lors d’un edit manuel; restauration via réécriture complète du script.
- Diagnostic réseau Windows: Ping OK mais TCP 8010 KO; côté Debian, `tv-perf.service` échouait (port 8010 déjà utilisé).
- Correction: kill du process occupant 8010 (PID 78706, bindé sur `127.0.0.1`), reset-failed + restart `tv-perf.service`, puis vérification `0.0.0.0:8010`.
- Validation Windows: `Test-NetConnection` OK, UI chargée sur `http://192.168.16.155:8010/perf/ui` (capture fournie).
- Vérification service: `tv-perf.service` active/running, écoute `0.0.0.0:8010`.
- Lancement et réussite du test final end-to-end (services, ports, endpoints, UI GET, smoke OPEN→CLOSE→verify).

3) Décisions:
- Standardiser l’accès Windows via IP LAN Debian (pas `127.0.0.1`).
- Forcer les binds réseau via `--host 0.0.0.0` pour `tv-perf` et `tv-webhook`.
- Considérer le `405 Method Not Allowed` sur `HEAD /perf/ui` comme non bloquant (test final PASS malgré ce warning).

4) Commandes / Code:
```bash
# Déploiement (avec trap anti-fermeture) + systemd + smoke/diag
bash -lc '
set -Eeuo pipefail
trap '\''echo; echo "❌ ERREUR à la ligne $LINENO (code=$?)"; echo "➡️ Dernière commande: $BASH_COMMAND"; echo; read -r -p "Appuie Entrée pour fermer..." _; exit 1'\'' ERR

ROOT="/opt/trading"
ZIP="/home/ghost/Téléchargements/Magikgmo-main(1).zip"

TS="$(date +%Y%m%d_%H%M%S)"
BK="$ROOT/backup/$TS"
mkdir -p "$BK"

cp -a "$ROOT/perf/perf_app.py" "$BK/perf_app.py.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-perf.service" "$BK/tv-perf.service.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-webhook.service" "$BK/tv-webhook.service.bak" 2>/dev/null || true
cp -a "/etc/systemd/system/tv-webhook.service.d" "$BK/tv-webhook.service.d.bak" 2>/dev/null || true

TMP="/tmp/magik_${TS}"
rm -rf "$TMP"; mkdir -p "$TMP"
unzip -q "$ZIP" -d "$TMP"

rsync -a "$TMP"/Magikgmo-main/perf/ "$ROOT"/perf/
rsync -a "$TMP"/Magikgmo-main/scripts/ "$ROOT"/scripts/

sudo tee /etc/systemd/system/tv-perf.service >/dev/null <<'\''EOF'\''
[Unit]
Description=Trading Perf API (FastAPI/Uvicorn)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/trading
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=1
ExecStart=/opt/trading/venv/bin/python -m uvicorn perf.perf_app:app --host 0.0.0.0 --port 8010

[Install]
WantedBy=multi-user.target
EOF

sudo mkdir -p /etc/systemd/system/tv-webhook.service.d
sudo tee /etc/systemd/system/tv-webhook.service.d/override.conf >/dev/null <<'\''EOF'\''
[Service]
ExecStart=
ExecStart=/opt/trading/venv/bin/python -m uvicorn webhook_server:app --host 0.0.0.0 --port 8000
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now tv-perf.service
sudo systemctl restart tv-perf.service tv-webhook.service

sudo ufw allow 8000/tcp >/dev/null 2>&1 || true
sudo ufw allow 8010/tcp >/dev/null 2>&1 || true

BASE="http://127.0.0.1:8010" ./scripts/smoke.sh
./scripts/diagnose.sh || true

IP="$(hostname -I | awk "{print \$1}")"
echo "http://${IP}:8010/perf/ui"
'
```

```bash
# Fix diagnose.sh (PERF_BASE -> BASE + fallback)
cd /opt/trading
cp -a scripts/diagnose.sh scripts/diagnose.sh.bak.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
perl -0777 -i -pe 's/\bPERF_BASE\b/BASE/g' scripts/diagnose.sh
grep -q 'BASE=' scripts/diagnose.sh || sed -i '1iBASE="${BASE:-http://127.0.0.1:8010}"' scripts/diagnose.sh
chmod +x scripts/diagnose.sh
```

```bash
# Restauration/réécriture smoke.sh (après corruption)
cat > scripts/smoke.sh <<'BASH'
#!/usr/bin/env bash
set -Eeuo pipefail

PERF_BASE="${BASE:-http://127.0.0.1:8010}"
WEBHOOK_BASE="${WEBHOOK_BASE:-http://127.0.0.1:8000}"

say(){ echo "$*"; }
die(){ echo "❌ $*"; exit 1; }

say "[1/4] webhook health (best-effort)"
curl -fsS "$WEBHOOK_BASE/api/state" >/dev/null 2>&1 || true

say "[2/4] perf summary (wait-ready)"
for i in {1..50}; do
  if curl -fsS "$PERF_BASE/perf/summary" >/dev/null 2>&1; then break; fi
  sleep 0.2
  [[ "$i" == "50" ]] && die "perf not ready at $PERF_BASE"
done

say "[3/4] create dummy trade OPEN/CLOSE"
TID="T_SMOKE_$(date +%Y%m%d_%H%M%S)"

open_json="$(curl -fsS "$PERF_BASE/perf/event" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"OPEN\",\"trade_id\":\"$TID\",\"engine\":\"SMOKE\",\"symbol\":\"XAUUSD\",\"side\":\"LONG\",\"entry\":1.0,\"stop\":0.9,\"qty\":1.0,\"risk_usd\":0.1}")" || die "OPEN failed"

echo "$open_json" | python -m json.tool >/dev/null 2>&1 || die "OPEN response not JSON: $open_json"

close_json="$(curl -fsS "$PERF_BASE/perf/event" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"CLOSE\",\"trade_id\":\"$TID\",\"exit\":1.1}")" || die "CLOSE failed"

echo "$close_json" | python -m json.tool >/dev/null 2>&1 || die "CLOSE response not JSON: $close_json"

say "[4/4] verify trade appears"
found="0"
for i in {1..30}; do
  if curl -fsS "$PERF_BASE/perf/trades?limit=50" | grep -q "$TID"; then found="1"; break; fi
  sleep 0.2
done
[[ "$found" == "1" ]] || die "Trade not found in /perf/trades: $TID"

echo "OK"
BASH
chmod +x scripts/smoke.sh
```

```bash
# Conflit port 8010: tv-perf ne démarrait pas (address already in use) + fix
sudo ss -lntp | grep :8010
sudo kill 78706 || true
sudo kill -9 78706 2>/dev/null || true
sudo systemctl reset-failed tv-perf.service || true
sudo systemctl restart tv-perf.service
sudo ss -lntp | grep :8010
```

```powershell
# Windows: diagnostic + validation
Test-NetConnection 192.168.16.155 -Port 8010
Invoke-WebRequest "http://192.168.16.155:8010/perf/summary"
Start-Process "http://192.168.16.155:8010/perf/ui"
```

```bash
# Test final Debian (résultat PASS, smoke OK; HEAD /perf/ui retourne 405)
sudo systemctl is-active tv-perf.service
sudo systemctl is-active tv-webhook.service
sudo ss -lntp | grep -E ':8000|:8010'
curl -fsS http://127.0.0.1:8010/perf/summary >/dev/null
curl -fsS http://127.0.0.1:8010/perf/open    >/dev/null
curl -fsS http://127.0.0.1:8010/perf/trades?limit=3 >/dev/null
curl -fsS http://127.0.0.1:8010/perf/ui | head -c 40
curl -sI  http://127.0.0.1:8010/perf/ui | head -n 1
BASE="http://127.0.0.1:8010" WEBHOOK_BASE="http://127.0.0.1:8000" ./scripts/smoke.sh
```

5) Points ouverts (next):
- Traiter (optionnel) le `405 Method Not Allowed` sur `HEAD /perf/ui` si on veut zéro warning (actuellement non bloquant, navigateur OK).
- S’assurer que `scripts/smoke.sh` utilise `python3 -m json.tool` si `python -m json.tool` échoue selon environnements (mentionné comme correctif possible).
- Nettoyage/standardisation pour éviter un lancement manuel qui reprend le port 8010 (process “fantôme”).

## 2026-02-16 10:25 — algo 18
1) Objectifs:
- Valider état “GO” (services perf/webhook, endpoints, UI accessible Windows).
- Remplacer les checks HEAD (405) par des GET.
- Appliquer un patch “UI pro” sur `/perf/ui`, puis rendre l’UI plus “user friendly” en supprimant l’affichage des commandes `curl` (tout en gardant les boutons).
- Générer un patch Git propre et journaliser.

2) Actions:
- Confirmé que `curl -I` envoie HEAD ⇒ `405` sur `/perf/ui` (GET-only) ; choix de l’option GET pour les checks.
- Vérifié services/ports/endpoints/UI: `tv-perf` et `tv-webhook` actifs, bind `0.0.0.0:8010`, endpoints `/perf/summary`, `/perf/open`, `/perf/trades`, `/perf/ui` en `200`.
- Alignement repo ↔ machine:
  - `tv-perf.service` lance `uvicorn perf.perf_app:app` depuis `/opt/trading`.
  - fichier cible confirmé: `/opt/trading/perf/perf_app.py`.
- Application du patch UI pro depuis `"/home/ghost/Téléchargements/perf_ui_pro_clean.patch"` + redémarrage + tests `200`.
- Création d’un patch Git “officiel” via commit + `git format-patch`, fichier produit: `/opt/trading/perf_ui_pro.patch` (commit `efa23c1`).
- Ajout utilisateur `ghost` au groupe `adm` pour accès logs.
- Itérations pour nettoyer l’UI (suppression/masquage des commandes `curl` affichées):
  - Tentative de patch manuel `ui_clean_ops_folded.patch` échouée (patch corrompu).
  - Ajout d’une card “Outils” + section “Avancé” repliée (libellés FR + boutons), injections JS via scripts Python.
  - Ajout d’un appel `setTimeout(renderOps, 0);` après `refreshAll(false);`.
  - Remplacement de blocs `<code>...</code>` par texte FR neutre (“Commande masquée…”), mais les `curl` restaient visibles.
  - Preuve serveur: `curl .../perf/ui?v=999 | grep curl` montre que l’UI servie contient encore un bloc legacy `buildCmds()` avec `items=[{label,url,curl:...}]` et rendu `<code class="mono">${c}</code>` où `c = esc(it.curl)` + boutons `Copy URL/Copy cmd`.
  - Constats: plusieurs tentatives de neutralisation n’ont pas matché le code réel (problèmes d’ancrage/recherche dans `perf_app.py`, présence de versions legacy et de backups `.bak.*`, et contenu effectivement servi toujours porteur du legacy).
- Décision finale: pousser sur Git, puis fournir un ZIP pour analyse/correction.

3) Décisions:
- Utiliser des checks GET (option 1) au lieu de HEAD pour éviter le 405.
- UI: objectif “user friendly” = ne plus afficher de texte `curl` (garder actions/boutons), au lieu de supprimer massivement des blocs.
- Basculer vers une résolution “analyse ZIP + correction” après itérations et incohérences perçues entre modifications locales et HTML encore servi.
- Plan: push Git puis envoi d’un ZIP pour analyse.

4) Commandes / Code:
```bash
# Remplacer le check HEAD par GET
curl -s http://127.0.0.1:8010/perf/ui >/dev/null && echo OK
curl -s -o /dev/null -w "UI /perf/ui HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/ui
curl -s -o /dev/null -w "API /perf/summary HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/summary
curl -sf http://127.0.0.1:8010/perf/ui >/dev/null && echo "UI: PASS" || echo "UI: FAIL"

# Vérifier service perf (chemin réel)
sudo systemctl cat tv-perf.service | sed -n '1,120p'
/opt/trading/venv/bin/python -c "import perf.perf_app; print(perf.perf_app.__file__)"

# Backup / patch UI pro
cd /opt/trading || exit 1
cp -a perf/perf_app.py perf/perf_app.py.bak.$(date +%Y%m%d_%H%M%S)
patch --dry-run -p1 < "/home/ghost/Téléchargements/perf_ui_pro_clean.patch"
patch -p1 < "/home/ghost/Téléchargements/perf_ui_pro_clean.patch"
sudo systemctl restart tv-perf.service
curl -s -o /dev/null -w "UI /perf/ui HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/ui
curl -s -o /dev/null -w "API /perf/summary HTTP=%{http_code}\n" http://127.0.0.1:8010/perf/summary

# Check robuste post-restart
for i in {1..10}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8010/perf/summary || true)
  [ "$code" = "200" ] && echo "API: PASS" && break
  sleep 1
done

# Accès logs sans sudo (ops)
sudo usermod -aG adm ghost
newgrp adm

# Générer patch Git “officiel” (commit + format-patch)
cd /opt/trading || exit 1
git add perf/perf_app.py
git commit -m "Perf UI: pro dashboard + endpoints/copy tools"   # commit: efa23c1
git format-patch -1 HEAD --stdout > perf_ui_pro.patch
ls -la perf_ui_pro.patch
head -n 20 perf_ui_pro.patch
```

```bash
# Preuve serveur: l’UI servie contient encore du legacy buildCmds() avec curl affiché
curl -s "http://127.0.0.1:8010/perf/ui?v=999" | grep -n "curl" | head -n 80
curl -s "http://127.0.0.1:8010/perf/ui?v=1001" > /tmp/ui.html
nl -ba /tmp/ui.html | sed -n '130,190p'
```

```bash
# Recherche du legacy dans l’arborescence et preuve fichier réellement chargé
sudo grep -RIn "const c = esc(it.curl)" /opt/trading | head -n 20
/opt/trading/venv/bin/python - <<'PY'
import perf.perf_app
print(perf.perf_app.__file__)
PY
```

```bash
# Tentative de masquage global des blocs <code> (a remplacé 2 occurrences)
python3 - <<'PY'
import re, pathlib
p = pathlib.Path("perf/perf_app.py")
s = p.read_text(encoding="utf-8")
s, n = re.subn(r'(?is)<code[^>]*>.*?</code>',
               '<div class="muted">Commande masquée (copie disponible).</div>',
               s)
print("Replaced <code> blocks:", n)
p.write_text(s, encoding="utf-8")
PY
sudo systemctl restart tv-perf.service
```

5) Points ouverts (next):
- Push Git des changements “UI cleanup” (suppression affichage `curl`) non finalisés de manière stable.
- Fournir un ZIP du repo (état actuel) pour analyse et correction définitive:
  - Identifier précisément le bloc legacy `buildCmds()` dans la source servie et remplacer l’affichage `<code>${c}</code>` par du texte FR (sans afficher `curl`), tout en conservant les boutons.
- Nettoyage repo: éviter la pollution par `perf/perf_app.py.bak.*` et fichiers `.patch` non suivis (ajout `.gitignore` / nettoyage).

## 2026-02-16 18:30 | TV Webhook | XAU_M5_SCALP | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `XAU_M5_SCALP`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `1234.5`
5. **TP**: `1240.0`
6. **SL**: `1230.0`
7. **Reason**: ngrok_buy_ok
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "XAU_M5_SCALP",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 1234.5,
  "tp": 1240.0,
  "sl": 1230.0,
  "reason": "ngrok_buy_ok",
  "_ts": "2026-02-16T23:30:24.257484+00:00",
  "_ip": "67.69.76.141",
  "qty": 13.333,
  "risk_usd": 60.0,
  "risk_real_usd": 59.9985
}
```

## 2026-02-16 18:46 | CLOSE SESSION | ngrok + LAN OK | TV webhook -> perf OK

1. **ngrok-tv.service** patch stable (NGROK_CONFIG + pkill prestart via bash). Tunnel OK.
2. **Windows LAN** confirmé OK:
   - webhook: http://192.168.16.155:8000/api/state (200)
   - perf ui:  http://192.168.16.155:8010/perf/ui (200)
3. **TV webhook validation**:
   - route POST = /tv (secret TV_WEBHOOK_KEY)
   - engine TEST => risk_quote qty=0 (fallback) => rejet attendu
   - engine XAU_M5_SCALP => risk_quote OK => POST /tv via ngrok OK (200)
4. **Perf ledger end-to-end**:
   - OPEN créé depuis /tv (trade_id: T_20260216_183024_XAU_M5_SCALP_f4f04a)
   - CLOSE envoyé (exit=1238.0) => trade CLOSED, R≈0.7778

5. **GO NEXT (prochaine session)**:
   - Tester TradingView alert -> ngrok -> /tv -> perf OPEN
   - Enregistrer signals + ouvrir simulations trades (OPEN/CLOSE) via perf UI

## 2026-02-16 18:50 — algo28
1) Objectifs:
- Valider/corriger le dépôt après push (requirements, endpoints, scripts).
- Stabiliser `journal_add.sh` (commit+push auto).
- Finaliser l’UI PERF (CSS/visuel) sans casser le service.
- Valider end-to-end local (services + smoke/diagnose) puis accès externe via ngrok et tests webhook→perf.
- Vérifier accessibilité LAN/Windows.

2) Actions:
- Analyse repo ZIP: compilation de tous les `.py` OK; corrections proposées: `requirements.txt` (fastapi/uvicorn) et HEAD `/perf/ui` (405).
- Gestion des écrasements lors d’un unzip/copie (cas `yesè`); vérif `journal_add.sh` via `head`.
- Remplacement `journal_add.sh` par une version robuste: `set -euo pipefail`, garde “Usage”, `git commit ... || echo "Nothing to commit."`, `git push`.
- Résolution du rejet git non-fast-forward:
  - Tentative `pull --rebase` bloquée par modifications non commitées.
  - Push forcé effectué: `git push --force-with-lease origin main`.
  - Nettoyage: ajout `.gitignore` (tmp/logs/venv/cache), ajout `scripts/clean_repo.sh`, commit final + push normal.
  - Suppression d’un fichier parasite non suivi: `"cript + perf UI + scripts + ignore tmp\""`.
  - Config git: `pull.rebase=true`, `rebase.autoStash=true`.
- Tests E2E `journal_add.sh`: test sans titre (Usage), test avec titre (création/commit/push), vérifs `tail` + `git log`.
- UI PERF:
  - Problème récurrent: copier/coller corrompant le CSS (injection de bouts de commandes).
  - Déduplication des blocs CSS “prevent overlap” (suppression de 3 duplicats, 1 conservé), redémarrage service, tests GET `/perf/ui`.
  - Ajouts UI: patch “clarity” (lisibilité) + patch “polish” (zebra rows, alignement numérique, chips OPEN/CLOSED) via scripts.
- Tests “système entier” local via `scripts/autos.sh` (smoke + diagnose) + endpoints `/api/state`, `/perf/summary`, `/perf/open`, `/perf/ui` OK; logs sauvegardés.
- `.gitignore` mis à jour pour ignorer `logs/` et `*.log`.
- Backup snapshot avant ngrok/firewall/TV dans `/opt/trading/backups/pre_ngrok_fw_tv_<TS>`.
- ngrok:
  - Diagnostic via API locale 4040 (`/api/status`, `/api/tunnels`); correction de l’extraction `public_url` (éviter pipes -> fichier `/tmp/...json`).
  - Patch `ngrok-tv.service` pour forcer config + éviter double-run (pkill via shell); correction après échec systemd (ExecStartPre).
  - Validation public: `PUBLIC_URL` OK et GET `/api/state` via ngrok OK.
- Webhook externe (ngrok):
  - Découverte routes: POST `/tv` (pas `/api/webhook`).
  - Auth: payload JSON `key` doit matcher `TV_WEBHOOK_KEY` (chargée via `/opt/trading/.env`).
  - Validation métier: `signal` doit être BUY/SELL; risk sizing obligatoire via `risk_quote(engine, price, sl, tp)`.
  - Tests risk_quote: engine `TEST` → qty/risk=0 (fallback); engine `XAU_M5_SCALP` → qty/risk > 0.
  - POST ngrok `/tv` avec `engine=XAU_M5_SCALP` → 200, événement visible via `/api/events`.
- Chaîne webhook→perf:
  - Vérification perf: trade OPEN créé dans `/perf/open` et listé dans `/perf/trades`.
  - CLOSE via `/perf/event` puis vérif status CLOSED via export JSON `/tmp/perf_trades_<TS>.json` + parsing Python.
- LAN:
  - Diag IP/ports: IP 192.168.16.155, listeners 0.0.0.0:8000/8010, reachability LAN OK.
  - Firewall: policy INPUT DROP mais règles accept 22/8000/8010 présentes (stack ufw/iptables).

3) Décisions:
- Endpoint webhook officiel retenu: `POST /tv`.
- Auth webhook: champ JSON `key` (pas header) doit matcher `TV_WEBHOOK_KEY`.
- Risk sizing: ne pas utiliser `engine=TEST` pour tests end-to-end; utiliser un engine avec quote non nulle (ex: `XAU_M5_SCALP`).
- Méthode d’édition UI: privilégier micro-patches/scrips et déduplication; éviter remplacement massif de CSS par copier/coller.
- Stabilisation ngrok: forcer `--config` + `ExecStartPre` (pkill) pour éviter ERR_NGROK_334 (double-run).

4) Commandes / Code:
```bash
# journal_add.sh (patch robuste)
cat > /opt/trading/tmp/Magikgmo-main/journal_add.sh <<'SH'
#!/bin/bash
set -euo pipefail
export TZ=America/Montreal
TODAY=$(date +%F)
FILE="/opt/trading/journal/$TODAY.md"
TITLE="${1:-}"
if [ -z "$TITLE" ]; then
  echo "Usage: $0 \"Titre de session\""
  exit 1
fi
mkdir -p /opt/trading/journal
[ -f "$FILE" ] || touch "$FILE"
echo "" >> "$FILE"
echo "## $(date '+%Y-%m-%d %H:%M:%S') — $TITLE" >> "$FILE"
echo "" >> "$FILE"
cd /opt/trading
git add journal
git commit -m "Journal update: $TITLE" || echo "Nothing to commit."
git push
SH
chmod +x /opt/trading/tmp/Magikgmo-main/journal_add.sh
cp -f /opt/trading/tmp/Magikgmo-main/journal_add.sh /opt/trading/journal_add.sh
chmod +x /opt/trading/journal_add.sh

# résolution divergence git (réalisé via force)
git push --force-with-lease origin main

# commit final patch + ignore tmp/logs
git add .gitignore journal_add.sh perf/perf_app.py scripts/diagnose.sh scripts/smoke.sh scripts/clean_repo.sh
git commit -m "Fix: journal script + perf UI + scripts + ignore tmp"
git push origin main

# suppression fichier parasite non suivi
rm -f "cript + perf UI + scripts + ignore tmp\""

# config git
git config pull.rebase true
git config rebase.autoStash true

# dédup CSS overlap
python - <<'PY'
# (script: suppression duplicats overlap dans <style> puis restart)
PY
sudo systemctl restart tv-perf.service

# patch scripts UI (clarté/polish) + commit
git add perf/perf_app.py scripts/patch_perf_ui_css_clean17.sh scripts/patch_perf_ui_minimal_clarity.sh scripts/patch_perf_ui_polish_min.sh
git commit -m "Perf UI: lock minimal clarity + patch scripts"
git push
printf "\n# runtime\nlogs/\n*.log\n" >> .gitignore
git add .gitignore
git commit -m "Chore: ignore runtime logs"
git push

# test intégral
bash -lc "./scripts/autos.sh" 2>&1 | tee /opt/trading/logs/test_full_<TS>.log

# snapshot backup pré ngrok/fw/tv
BK=/opt/trading/backups/pre_ngrok_fw_tv_<TS>
cp -a /etc/systemd/system/ngrok-tv.service "$BK/"
cp -a /opt/trading/perf/perf_app.py "$BK/perf_app.py"
cp -a /opt/trading/webhook_server.py "$BK/webhook_server.py"

# patch ngrok-tv.service (stabilisation + pkill via shell)
sudo sed -i 's#^ExecStartPre=.*#ExecStartPre=/bin/bash -lc '"'"'pkill -u ghost -x ngrok || true'"'"'#' /etc/systemd/system/ngrok-tv.service
sudo systemctl daemon-reload
sudo systemctl restart ngrok-tv.service

# ngrok: extraction public_url via fichier (évite curl:23)
curl -fsS http://127.0.0.1:4040/api/tunnels/command_line -o /tmp/ngrok_tunnel_cmdline.json
python - <<'PY'
import json
d=json.load(open("/tmp/ngrok_tunnel_cmdline.json"))
print(d.get("public_url",""))
PY

# routes FastAPI (avec python venv)
./venv/bin/python - <<'PY'
from webhook_server import app
for r in app.router.routes:
    if "POST" in (getattr(r,"methods",set()) or set()):
        print(r.path, r.name)
PY

# POST externe validé via ngrok (engine réel + key)
KEY="$(sudo awk -F= '/^TV_WEBHOOK_KEY=/{print $2; exit}' /opt/trading/.env)"
curl -sS -i "https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv" \
  -H "Content-Type: application/json" \
  -d "{\"key\":\"$KEY\",\"engine\":\"XAU_M5_SCALP\",\"signal\":\"BUY\",\"symbol\":\"XAUUSD\",\"tf\":\"M5\",\"price\":1234.5,\"tp\":1240.0,\"sl\":1230.0,\"reason\":\"ngrok_buy_ok\"}"

# perf: CLOSE trade
curl -fsS http://127.0.0.1:8010/perf/event \
  -H "Content-Type: application/json" \
  -d '{"type":"CLOSE","trade_id":"T_20260216_183024_XAU_M5_SCALP_f4f04a","exit":1238.0}'
```

5) Points ouverts (next):
- Éviter définitivement les corruptions de copier/coller dans l’UI (procédure stricte: micro-patches uniquement / patcher via fichiers).
- Commit/push éventuel des changements systemd ngrok-tv (hors repo; documenter dans scripts/backup si besoin).
- Optionnel: ignorer `backups/` dans `.gitignore` (actuellement `git status` montrait `?? backups/` au moment du snapshot).
- Optionnel: corriger les scripts/tests qui utilisent `curl -I /perf/ui` (HEAD → 405 attendu) ou ajouter handler HEAD si souhaité.

## 2026-02-17 00:30 | TV Webhook | COINM_SHORT | BTCUSDT.P 15 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT.P` / `15`
4. **Price**: `68020.1`
5. **TP**: `67893.8`
6. **SL**: `68343.9`
7. **Reason**: smartmoney_sell
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT.P",
  "tf": "15",
  "price": 68020.1,
  "tp": 67893.8,
  "sl": 68343.9,
  "reason": "smartmoney_sell",
  "_ts": "2026-02-17T05:30:01.268677+00:00",
  "_ip": "52.32.178.7",
  "qty": 0.185,
  "risk_usd": 60.0,
  "risk_real_usd": 59.903
}
```

## 2026-02-17 00:30 | TV Webhook | COINM_SHORT | ETHUSDT.P 15 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `ETHUSDT.P` / `15`
4. **Price**: `1972.93`
5. **TP**: `1959.24`
6. **SL**: `1994.15`
7. **Reason**: smartmoney_sell
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "ETHUSDT.P",
  "tf": "15",
  "price": 1972.93,
  "tp": 1959.24,
  "sl": 1994.15,
  "reason": "smartmoney_sell",
  "_ts": "2026-02-17T05:30:02.020309+00:00",
  "_ip": "52.32.178.7",
  "qty": 2.827,
  "risk_usd": 60.0,
  "risk_real_usd": 59.98894
}
```

## 2026-02-17 05:45 | TV Webhook | TV_TEST | XAUUSD 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: curl_test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "curl_test",
  "_ts": "2026-02-17T10:45:11.347747+00:00",
  "_ip": "67.69.76.141",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-17 05:54 | TV Webhook | TV_TEST | XAUUSD 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: curl_smoke
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "curl_smoke",
  "_ts": "2026-02-17T10:54:38.348164+00:00",
  "_ip": "67.69.76.141",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 02:57 — algo 30
1) Objectifs:
- Confirmer le bon ZIP/commit du repo et faire une revue complète.
- Produire un patch unique “audit fixes” et l’appliquer sans erreurs de collage.
- Retester la machine (verify_all) puis enchaîner TradingView → perf simulations.

2) Actions:
- Vérification SHA256 du ZIP uploadé: match exact `a6c42c07…` (commit `a90491d`), arborescence listée, revue en 3 passes réalisée.
- Problèmes identifiés: XSS dashboard (innerHTML/esc), webhook trop permissif si `TV_WEBHOOK_KEY` absent, incohérence env Telegram, `trade_id` collision faible, `verify_all.sh` masque erreurs (|| true).
- Tentatives d’application patch via `git apply` échouent:
  - Patch vide (“PASTE LE PATCH ICI”) → “Pas de rustine valide”.
  - Patch tronqué / heredoc cassé → “patch corrompu”.
  - Collage terminal PowerShell tronqué (scroll/paste buffer).
- Passage à méthode “script upload” via PowerShell + Notepad++ + scp/ssh.
- Script initial: erreur `set: pipef` (caractères invisibles/CRLF). Fix côté serveur: nettoyage CR + zero-width + réécriture ASCII ligne 2.
- Modifs appliquées, commit créé: `54d6a62`.
- Exécution `./scripts/verify_all.sh`: py_compile OK, smoke rc 0, diagnose rc 0, endpoints 200. Messages `sudo` non-interactif observés dans diagnose (non bloquant).

3) Décisions:
- Abandonner `git apply` via gros patch collé; privilégier un script appliquant les changements puis commit.
- Archiver l’état atteint et reprendre en nouvelle session Debian pour retest puis TradingView/perf.

4) Commandes / Code:
```bash
# Export ZIP + SHA (serveur)
cd /opt/trading
git status
git log --oneline -n 1
git archive --format=zip -o /tmp/Magikgmo-clean.zip HEAD
sha256sum /tmp/Magikgmo-clean.zip | tee /tmp/Magikgmo-clean.zip.sha256
ls -lh /tmp/Magikgmo-clean.zip /tmp/Magikgmo-clean.zip.sha256
```

```powershell
# Windows (PowerShell) + Notepad++ + upload/exécution
& "C:\Program Files (x86)\Notepad++\notepad++.exe" "$env:TEMP\apply_audit_fixes.sh"
scp "$env:TEMP\apply_audit_fixes.sh" admin-trading:/tmp/apply_audit_fixes.sh
ssh admin-trading "head -n 5 /tmp/apply_audit_fixes.sh; chmod +x /tmp/apply_audit_fixes.sh && bash /tmp/apply_audit_fixes.sh"
```

```bash
# Fix côté serveur (caractères invisibles) + exécution
# (nettoyage CR + zero-width + réécriture de la ligne 2 "set -euo pipefail")
# puis run script
```

```bash
# Résultat (sur Debian)
git diff --stat
git commit -m "security+ops: xss escape, remote key lock, telegram env unification, verify rc, trade_id ms, readme"
./scripts/verify_all.sh
# Log: tmp/verify_20260218_025054.log
# Diag: logs/diagnostics/diag_20260218_025054.log
```

5) Points ouverts (next):
- Nouvelle session Debian: retest machine (`./scripts/verify_all.sh`) et confirmer logs.
- Préparer TradingView/perf:
  - Définir `TV_WEBHOOK_KEY` (obligatoire pour accès remote/ngrok) via `.env` + restart services si utilisés.
  - Mettre en place l’URL webhook (ngrok) et créer alerte TradingView; valider réception event et création trade perf.

## 2026-02-18 03:20 | TV Webhook | TV_TEST | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: tv test buy
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "tv test buy",
  "_ts": "2026-02-18T08:20:36.379521+00:00",
  "_ip": "67.69.76.11",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 03:21 | TV Webhook | TV_TEST | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: tv test buy
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "tv test buy",
  "_ts": "2026-02-18T08:21:48.711413+00:00",
  "_ip": "67.69.76.11",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 06:35 | TV Webhook | TV_TEST | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: manual_test_after_tv_alert
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "manual_test_after_tv_alert",
  "_ts": "2026-02-18T11:35:11.713441+00:00",
  "_ip": "127.0.0.1",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 06:40 | TV Webhook | TV_TEST | XAUUSD M5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `M5`
4. **Price**: `100.0`
5. **TP**: `110.0`
6. **SL**: `90.0`
7. **Reason**: public_test
8. **Payload brut**:
```json
{
  "key": "GHOST_XAU_2026_ULTRA",
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "M5",
  "price": 100.0,
  "tp": 110.0,
  "sl": 90.0,
  "reason": "public_test",
  "_ts": "2026-02-18T11:40:52.547323+00:00",
  "_ip": "67.69.76.11",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 23:14 — algo 38
1) Objectifs:
- Évaluer une alternative Debian à PineScript/TradingView pour générer des signaux/trades de swing avec les mêmes conditions et un déclenchement quasi simultané.
- Archiver/journaliser l’indicateur Pine v5 et préparer le changement de voie vers un pipeline Debian + module perf.
- Avancer étape par étape avec logs/commandes et critères de réussite.

2) Actions:
- Partage du script Pine v5 **“Smart Money Clone | Bulletproof + Webhook JSON (FINAL)”** (alert JSON, TP/SL, filtres HTF/LTF, volume, breakout, anti-répétition).
- Validation que le module **perf** fonctionne via sortie `/perf/trades?limit=10` montrant des trades `CLOSED` (engine `SMOKE`, `XAUUSD`).
- Identification du problème initial : **TradingView n’envoie pas** (webhook).
- Discussion des causes probables côté TradingView (ports 80/443, 2FA, timeout 3s, URL/HTTPS, IPv6 non supporté).
- Clarification : possibilité de reproduire les signaux “bar close” sans TradingView/Pine via un moteur Debian (Python) en utilisant un feed de données (exchange).
- Ciblage Bitget comme source de bougies et planification d’une nouvelle session dédiée (“bitget”).

3) Décisions:
- Garder le Pine comme **référence** et/ou comme déclencheur temporaire, mais déplacer la journalisation/exécution/perf côté Debian.
- Déclenchement cible : **à la clôture de bougie** (équivalent `alert.freq_once_per_bar_close`) pour le swing.
- Stratégie de debug : si TV n’envoie pas, diagnostiquer d’abord la chaîne TradingView→URL (ngrok/reverse proxy/2FA), sinon basculer vers moteur Debian “sans TV”.
- Prochaine session : titre **“bitget”** ; progression étape par étape + logs ; intégration signaux → perf (OPEN v1, CLOSE plus tard).

4) Commandes / Code:
```pinescript
//@version=5
indicator("Smart Money Clone | Bulletproof + Webhook JSON (FINAL)", overlay=true, max_labels_count=500)
// ... (script complet partagé dans la conversation)
// Alerte JSON via alert(..., alert.freq_once_per_bar_close)
// Payload: key, engine, signal, symbol, tf, price, tp, sl, reason
```

```bash
# Vérifs proposées (webhook/ngrok/perf)
sudo systemctl status tv-webhook.service --no-pager -l
journalctl -u tv-webhook.service -n 80 --no-pager

curl -s http://127.0.0.1:4040/api/requests/http | python3 -m json.tool | tail -n 120

sudo systemctl status tv-perf.service --no-pager -l
curl -fsS http://127.0.0.1:8010/perf/summary ; echo
curl -fsS http://127.0.0.1:8010/perf/open ; echo

curl -s "http://127.0.0.1:8010/perf/trades?limit=10" | python3 -m json.tool
sudo ss -lntp | grep -E ':8000|:8010|:4040'
```

```bash
# Test local proposé (simulation payload TradingView vers webhook)
curl -fsS http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "key":"GHOST_XAU_2026_ULTRA",
    "engine":"GOLD_CFD_LONG",
    "signal":"BUY",
    "symbol":"XAUUSD",
    "tf":"5",
    "price":4880.0,
    "tp":4890.0,
    "sl":4870.0,
    "reason":"TEST_OPEN_V1"
  }' | python3 -m json.tool

curl -fsS "http://127.0.0.1:8010/perf/open" | python3 -m json.tool
```

5) Points ouverts (next):
- (TV) Obtenir une preuve ngrok/logs : TradingView envoie-t-il un POST ? (`/api/requests/http`).
- (TV) Vérifier contraintes bloquantes : port 80/443, 2FA, HTTPS/URL, timeout.
- (Bitget) Démarrer nouvelle session “bitget” et choisir le marché (SPOT / USDT-FUTURES / COIN-FUTURES) + symbole + timeframes (principal/HTF/LTF).
- (Moteur Debian) Implémenter reproduction bar-close des conditions Pine (ATR, EMA/VWAP HTF/LTF, volume, breakout, anti-spam) et push vers `/perf/event` (OPEN v1) avec logs.

## 2026-02-18 23:48 | TV Webhook | TV_TEST | XAUUSD 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `5`
4. **Price**: `100.0`
5. **TP**: `0.0`
6. **SL**: `90.0`
7. **Reason**: probe-tv
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "5",
  "price": 100.0,
  "tp": 0.0,
  "sl": 90.0,
  "reason": "probe-tv",
  "_ts": "2026-02-19T04:48:08.207524+00:00",
  "_ip": "127.0.0.1",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-18 23:52 — algo50
1) Objectifs:
- Centraliser la gestion des secrets (TV_WEBHOOK_KEY, OPS_ADMIN_KEY).
- Déployer une version corrigée de `webhook_server.py` sur Debian.
- Rendre le webhook non-bloquant quand `qty/risk == 0`.
- Diagnostiquer pourquoi une alerte TradingView “réelle” n’arrive pas.

2) Actions:
- Proposition de création de `/opt/trading/webhook_secret.py` avec vérification constant-time (hmac) et helpers `require_tv_key()` / `require_ops_key()`.
- Patch proposé pour remplacer les checks inline dans `webhook_server.py` par import de `webhook_secret.py`.
- Fourniture d’un `webhook_server.py` complet intégrant:
  - Fix XSS dashboard (escape HTML côté JS pour usage `innerHTML`).
  - TV_WEBHOOK_KEY constant-time + mode dev (si clé absente: localhost only).
  - OPS_ADMIN_KEY constant-time.
  - Unification env Telegram (fallback `TELEGRAM_TOKEN`/`TELEGRAM_CHAT`).
  - Ne plus logger la clé reçue (key stockée à `None`).
  - Comportement non-bloquant si sizing invalide (qty/risk=0): log + Telegram optionnel + réponse OK.
- Commande Debian fournie pour backup + remplacement via heredoc `cat > /opt/trading/webhook_server.py` + `py_compile` + restart systemd.
- Remplacement manuel du fichier par l’utilisateur; validation du service:
  - `tv-webhook.service` actif.
  - `/api/state` OK, accès dashboard OK.
  - `perf/summary` et `perf/trades` OK.
- Constat: aucune requête POST /tv lors de l’alerte TradingView; seulement des GET du dashboard.
- Test local réussi: événement `manual_test_after_tv_alert` apparaît (IP 127.0.0.1).
- Diagnostic ngrok:
  - `ngrok-tv.service` actif, écoute sur `127.0.0.1:4040`.
  - Extraction de l’URL ngrok actuelle: `https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev`.
  - Test public réussi via ngrok: événement `public_test` apparaît avec IP publique.
- Correction côté TradingView: le champ “Message” de l’alerte était vide; ajout du JSON (incluant la key). Attente de la prochaine alarme + suggestion de tests/monitoring (`tail -f`, `watch`, test alert TV).

3) Décisions:
- Adopter le comportement “non-bloquant” quand `qty/risk == 0` (pas de 400; skip perf; réponse `{ok:true, sizing_invalid:true}`).
- Mettre à jour l’URL Webhook TradingView vers `https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv`.
- Renseigner un message JSON non vide dans l’alerte TradingView (incluant `"key"`).

4) Commandes / Code:
```bash
cd /opt/trading || exit 1

# backup
sudo cp -a webhook_server.py webhook_server.py.bak.$(date +%Y%m%d_%H%M%S)

# remplacement (heredoc cat > /opt/trading/webhook_server.py <<'PY' ... PY) + checks
python3 -m py_compile /opt/trading/webhook_server.py && echo "PY OK"
sudo systemctl restart tv-webhook.service
sudo systemctl is-active tv-webhook.service && echo "SERVICE OK"
sudo ss -lntp | grep ':8000' || true
curl -fsS http://127.0.0.1:8000/api/state | python3 -m json.tool
curl -fsS "http://127.0.0.1:8000/api/events?limit=10" | python3 -m json.tool
```

```bash
# perf checks
curl -fsS http://127.0.0.1:8010/perf/summary | python3 -m json.tool
curl -fsS "http://127.0.0.1:8010/perf/trades?limit=5" | python3 -m json.tool
```

```bash
# ngrok service / web ui
sudo systemctl is-active ngrok-tv.service
sudo ss -lntp | grep ':4040'
curl -s http://127.0.0.1:4040/api/tunnels
curl -s http://127.0.0.1:4040/api/requests/http
```

```bash
# test public via ngrok (après récupération de PUBLIC_URL)
PUBLIC_URL="https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev"
curl -s -X POST "$PUBLIC_URL/tv" -H "Content-Type: application/json" \
  -d '{"key":"GHOST_XAU_2026_ULTRA","engine":"TV_TEST","signal":"BUY","symbol":"XAUUSD","tf":"M5","price":100,"tp":110,"sl":90,"qty":0,"risk_usd":0,"reason":"public_test"}' \
| python3 -m json.tool

curl -fsS "http://127.0.0.1:8000/api/events?limit=3" | python3 -m json.tool
```

```python
# /opt/trading/webhook_secret.py (proposé)
import os, hmac
from typing import Any, Dict

def tv_key() -> str: return os.getenv("TV_WEBHOOK_KEY","").strip()
def ops_key() -> str: return os.getenv("OPS_ADMIN_KEY","").strip()

def require_tv_key(payload: Dict[str, Any]) -> None:
    expected = tv_key()
    if not expected: return
    got = str(payload.get("key") or "").strip()
    if not hmac.compare_digest(got, expected):
        raise PermissionError("Invalid secret")

def require_ops_key(got_key: str) -> None:
    expected = ops_key()
    if not expected: raise RuntimeError("OPS_ADMIN_KEY not set")
    if not hmac.compare_digest((got_key or "").strip(), expected):
        raise PermissionError("Forbidden")
```

5) Points ouverts (next):
- Déclencher un “Test alert” TradingView (ou forcer une alerte) pour confirmer la réception end-to-end maintenant que le Message n’est plus vide.
- Sur Debian, surveiller l’arrivée d’événements en temps réel:
  - `tail -f /opt/trading/events.jsonl /opt/trading/state/events.jsonl`
  - ou `watch -n 2 'curl -fsS "http://127.0.0.1:8000/api/events?limit=3" | python3 -m json.tool'`
- Confirmer que l’alerte TradingView utilise bien:
  - Webhook URL: `https://phytogeographical-subnodulous-joycelyn.ngrok-free.dev/tv`
  - Message JSON incluant `"key":"GHOST_XAU_2026_ULTRA"`.

## 2026-02-18 23:55 | TV Webhook | TV_TEST | XAUUSD 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `TV_TEST`
3. **Symbol/TF**: `XAUUSD` / `5`
4. **Price**: `100.0`
5. **TP**: `0.0`
6. **SL**: `90.0`
7. **Reason**: probe-tv
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "TV_TEST",
  "signal": "BUY",
  "symbol": "XAUUSD",
  "tf": "5",
  "price": 100.0,
  "tp": 0.0,
  "sl": 90.0,
  "reason": "probe-tv",
  "_ts": "2026-02-19T04:55:01.587752+00:00",
  "_ip": "127.0.0.1",
  "qty": 10.0,
  "risk_usd": 100.0,
  "risk_real_usd": 100.0
}
```

## 2026-02-19 01:06 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67000.0`
5. **TP**: `0.0`
6. **SL**: `66990.0`
7. **Reason**: bitget test real post
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67000.0,
  "tp": 0.0,
  "sl": 66990.0,
  "reason": "bitget test real post",
  "_ts": "2026-02-19T06:06:56.531987+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:09 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `66925.3`
5. **TP**: `0.0`
6. **SL**: `66915.3`
7. **Reason**: bitget bar-close ts=1771481100000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 66925.3,
  "tp": 0.0,
  "sl": 66915.3,
  "reason": "bitget bar-close ts=1771481100000",
  "_ts": "2026-02-19T06:09:07.273515+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:10 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `66938.4`
5. **TP**: `0.0`
6. **SL**: `66928.4`
7. **Reason**: bitget bar-close ts=1771481400000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 66938.4,
  "tp": 0.0,
  "sl": 66928.4,
  "reason": "bitget bar-close ts=1771481400000",
  "_ts": "2026-02-19T06:10:03.495620+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:14 | TV Webhook | COINM_SHORT | BTCUSDT 5 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `66938.4`
5. **TP**: `0.0`
6. **SL**: `66948.4`
7. **Reason**: force flip test
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 66938.4,
  "tp": 0.0,
  "sl": 66948.4,
  "reason": "force flip test",
  "_ts": "2026-02-19T06:14:33.327585+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:15 | TV Webhook | COINM_SHORT | BTCUSDT 5 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `66967.5`
5. **TP**: `0.0`
6. **SL**: `66977.5`
7. **Reason**: bitget bar-close ts=1771481700000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 66967.5,
  "tp": 0.0,
  "sl": 66977.5,
  "reason": "bitget bar-close ts=1771481700000",
  "_ts": "2026-02-19T06:15:02.127766+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:15 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `66967.5`
5. **TP**: `0.0`
6. **SL**: `66957.5`
7. **Reason**: bitget bar-close ts=1771481700000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 66967.5,
  "tp": 0.0,
  "sl": 66957.5,
  "reason": "bitget bar-close ts=1771481700000",
  "_ts": "2026-02-19T06:15:02.791905+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:20 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67091.3`
5. **TP**: `0.0`
6. **SL**: `67081.3`
7. **Reason**: bitget bar-close ts=1771482000000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67091.3,
  "tp": 0.0,
  "sl": 67081.3,
  "reason": "bitget bar-close ts=1771482000000",
  "_ts": "2026-02-19T06:20:02.644932+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:25 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67160.4`
5. **TP**: `0.0`
6. **SL**: `67150.4`
7. **Reason**: bitget bar-close ts=1771482300000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67160.4,
  "tp": 0.0,
  "sl": 67150.4,
  "reason": "bitget bar-close ts=1771482300000",
  "_ts": "2026-02-19T06:25:02.174164+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:30 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67139.6`
5. **TP**: `0.0`
6. **SL**: `67129.6`
7. **Reason**: bitget bar-close ts=1771482600000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67139.6,
  "tp": 0.0,
  "sl": 67129.6,
  "reason": "bitget bar-close ts=1771482600000",
  "_ts": "2026-02-19T06:30:00.890001+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:30 | TV Webhook | COINM_SHORT | SOLUSDT.P 30 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `SOLUSDT.P` / `30`
4. **Price**: `82.356`
5. **TP**: `92.414`
6. **SL**: `71.769`
7. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "SOLUSDT.P",
  "tf": "30",
  "price": 82.356,
  "tp": 92.414,
  "sl": 71.769,
  "reason": "",
  "_ts": "2026-02-19T06:30:01.604826+00:00",
  "_ip": "34.212.75.30",
  "qty": 0.944,
  "risk_usd": 10.0,
  "risk_real_usd": 9.994128
}
```

## 2026-02-19 01:30 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67142.8`
5. **TP**: `0.0`
6. **SL**: `67132.8`
7. **Reason**: bitget bar-close ts=1771482600000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67142.8,
  "tp": 0.0,
  "sl": 67132.8,
  "reason": "bitget bar-close ts=1771482600000",
  "_ts": "2026-02-19T06:30:04.874440+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:35 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67107.9`
5. **TP**: `0.0`
6. **SL**: `67097.9`
7. **Reason**: bitget bar-close ts=1771482900000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67107.9,
  "tp": 0.0,
  "sl": 67097.9,
  "reason": "bitget bar-close ts=1771482900000",
  "_ts": "2026-02-19T06:35:03.902102+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:35 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67107.9`
5. **TP**: `0.0`
6. **SL**: `67097.9`
7. **Reason**: bitget bar-close ts=1771482900000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67107.9,
  "tp": 0.0,
  "sl": 67097.9,
  "reason": "bitget bar-close ts=1771482900000",
  "_ts": "2026-02-19T06:35:05.022430+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:40 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67101.2`
5. **TP**: `0.0`
6. **SL**: `67091.2`
7. **Reason**: bitget bar-close ts=1771483200000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67101.2,
  "tp": 0.0,
  "sl": 67091.2,
  "reason": "bitget bar-close ts=1771483200000",
  "_ts": "2026-02-19T06:40:02.915660+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:42 | TV Webhook | COINM_SHORT | BTCUSDT 5 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67065.3`
5. **TP**: `0.0`
6. **SL**: `67075.3`
7. **Reason**: bitget bar-close ts=1771483200000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67065.3,
  "tp": 0.0,
  "sl": 67075.3,
  "reason": "bitget bar-close ts=1771483200000",
  "_ts": "2026-02-19T06:42:40.105959+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:43 | TV Webhook | COINM_SHORT | BTCUSDT 5 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67060.1`
5. **TP**: `0.0`
6. **SL**: `67070.1`
7. **Reason**: bitget bar-close ts=1771483200000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67060.1,
  "tp": 0.0,
  "sl": 67070.1,
  "reason": "bitget bar-close ts=1771483200000",
  "_ts": "2026-02-19T06:43:35.097800+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:43 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67101.2`
5. **TP**: `0.0`
6. **SL**: `67091.2`
7. **Reason**: manual test
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67101.2,
  "tp": 0.0,
  "sl": 67091.2,
  "reason": "manual test",
  "_ts": "2026-02-19T06:43:56.510649+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:45 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67069.1`
5. **TP**: `0.0`
6. **SL**: `67059.1`
7. **Reason**: bitget bar-close ts=1771483500000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67069.1,
  "tp": 0.0,
  "sl": 67059.1,
  "reason": "bitget bar-close ts=1771483500000",
  "_ts": "2026-02-19T06:45:06.686988+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:45 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67069.1`
5. **TP**: `0.0`
6. **SL**: `67059.1`
7. **Reason**: bitget bar-close ts=1771483500000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67069.1,
  "tp": 0.0,
  "sl": 67059.1,
  "reason": "bitget bar-close ts=1771483500000",
  "_ts": "2026-02-19T06:45:07.396987+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:48 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67103.0`
5. **TP**: `0.0`
6. **SL**: `67093.0`
7. **Reason**: bitget bar-close ts=1771483500000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67103.0,
  "tp": 0.0,
  "sl": 67093.0,
  "reason": "bitget bar-close ts=1771483500000",
  "_ts": "2026-02-19T06:48:22.594840+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:50 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67110.5`
5. **TP**: `0.0`
6. **SL**: `67100.5`
7. **Reason**: bitget bar-close ts=1771483800000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67110.5,
  "tp": 0.0,
  "sl": 67100.5,
  "reason": "bitget bar-close ts=1771483800000",
  "_ts": "2026-02-19T06:50:04.642706+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:50 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67110.5`
5. **TP**: `0.0`
6. **SL**: `67100.5`
7. **Reason**: bitget bar-close ts=1771483800000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67110.5,
  "tp": 0.0,
  "sl": 67100.5,
  "reason": "bitget bar-close ts=1771483800000",
  "_ts": "2026-02-19T06:50:05.386503+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:55 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67136.9`
5. **TP**: `0.0`
6. **SL**: `67126.9`
7. **Reason**: bitget bar-close ts=1771484100000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67136.9,
  "tp": 0.0,
  "sl": 67126.9,
  "reason": "bitget bar-close ts=1771484100000",
  "_ts": "2026-02-19T06:55:03.042751+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 01:55 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67136.9`
5. **TP**: `0.0`
6. **SL**: `67126.9`
7. **Reason**: bitget bar-close ts=1771484100000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67136.9,
  "tp": 0.0,
  "sl": 67126.9,
  "reason": "bitget bar-close ts=1771484100000",
  "_ts": "2026-02-19T06:55:05.811994+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:00 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67121.8`
5. **TP**: `0.0`
6. **SL**: `67111.8`
7. **Reason**: bitget bar-close ts=1771484400000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67121.8,
  "tp": 0.0,
  "sl": 67111.8,
  "reason": "bitget bar-close ts=1771484400000",
  "_ts": "2026-02-19T07:00:03.796011+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:00 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67121.8`
5. **TP**: `0.0`
6. **SL**: `67111.8`
7. **Reason**: bitget bar-close ts=1771484400000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67121.8,
  "tp": 0.0,
  "sl": 67111.8,
  "reason": "bitget bar-close ts=1771484400000",
  "_ts": "2026-02-19T07:00:06.596582+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:05 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67065.6`
5. **TP**: `0.0`
6. **SL**: `67055.6`
7. **Reason**: bitget bar-close ts=1771484700000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67065.6,
  "tp": 0.0,
  "sl": 67055.6,
  "reason": "bitget bar-close ts=1771484700000",
  "_ts": "2026-02-19T07:05:03.027533+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:05 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67065.7`
5. **TP**: `0.0`
6. **SL**: `67055.7`
7. **Reason**: bitget bar-close ts=1771484700000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67065.7,
  "tp": 0.0,
  "sl": 67055.7,
  "reason": "bitget bar-close ts=1771484700000",
  "_ts": "2026-02-19T07:05:04.070246+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:10 | TV Webhook | COINM_SHORT | BTCUSDT 5 | SELL
1. **Signal**: `SELL`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67031.8`
5. **TP**: `0.0`
6. **SL**: `67041.8`
7. **Reason**: bitget bar-close ts=1771485000000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "SELL",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67031.8,
  "tp": 0.0,
  "sl": 67041.8,
  "reason": "bitget bar-close ts=1771485000000",
  "_ts": "2026-02-19T07:10:07.052485+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:13 | TV Webhook | COINM_SHORT | BTCUSDT 1 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `1`
4. **Price**: `67139.7`
5. **TP**: `0.0`
6. **SL**: `67129.7`
7. **Reason**: bitget bar-close ts=1771485180000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "1",
  "price": 67139.7,
  "tp": 0.0,
  "sl": 67129.7,
  "reason": "bitget bar-close ts=1771485180000",
  "_ts": "2026-02-19T07:13:59.610415+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```

## 2026-02-19 02:14 | TV Webhook | COINM_SHORT | BTCUSDT 5 | BUY
1. **Signal**: `BUY`
2. **Engine**: `COINM_SHORT`
3. **Symbol/TF**: `BTCUSDT` / `5`
4. **Price**: `67130.0`
5. **TP**: `0.0`
6. **SL**: `67120.0`
7. **Reason**: bitget bar-close ts=1771485000000
8. **Payload brut**:
```json
{
  "key": null,
  "engine": "COINM_SHORT",
  "signal": "BUY",
  "symbol": "BTCUSDT",
  "tf": "5",
  "price": 67130.0,
  "tp": 0.0,
  "sl": 67120.0,
  "reason": "bitget bar-close ts=1771485000000",
  "_ts": "2026-02-19T07:14:13.542370+00:00",
  "_ip": "127.0.0.1",
  "qty": 1.0,
  "risk_usd": 10.0,
  "risk_real_usd": 10.0
}
```
