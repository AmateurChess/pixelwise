# PixelWise – Feature Flags & Downtime Reduction

Dieses Repository erweitert PixelWise (Full Stack Handwerk, Block 4 & 5) um
zwei Feature-Flag-Implementierungen, die den bestehenden In-Memory Hot Swap
zur Laufzeit absichern. Der vollständige Projektbericht liegt im
Repository-Root.

## Methoden

- **Feature Flag Methode 1 – Dateibasiertes Polling**: liest `flags.json`
  in festen Intervallen (Standard: 5s) neu ein.
- **Feature Flag Methode 2 – In-Memory Flag mit Lock**: hält den
  Flag-Zustand als geschützte globale Variable, gesetzt über einen
  dedizierten Endpoint. Wirkt sofort, ohne Neustart.

Beide Methoden steuern, ob der bestehende `/admin/swap-model` Endpoint
(In-Memory Hot Swap des ML-Modells) erreichbar ist.

## Setup

```bash
cd /opt/pixelwise   # bzw. der jeweilige Projektpfad
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` muss mindestens enthalten:
```
MODEL_PATH=/pfad/zu/digit_classifier_v1.pkl
SECRET_API_KEY=<beliebiger Schlüssel>
DATABASE_URL=<Postgres-Connection-String>
```

## Server starten

```bash
export FLAG_METHOD=inmemory   # oder: polling
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`FLAG_METHOD` bestimmt, welche der beiden Methoden den Swap-Endpoint
absichert. Auf dem Produktionsserver erfolgt dieselbe Auswahl über die
Umgebungsvariable in der jeweiligen systemd-Unit
(`pixelwise-hotswap.service`).

## Testablauf

```bash
# 1. Health-Check
curl http://localhost:8000/health

# 2. Flag-Status abfragen (startet deaktiviert)
curl http://localhost:8000/admin/hotswap-status -H "x-api-key: <KEY>"

# 3. Swap ohne aktiviertes Flag -> erwartet: 403
curl -X POST http://localhost:8000/admin/swap-model \
  -H "x-api-key: <KEY>" -H "Content-Type: application/json" \
  -d '{"model_path": "/pfad/zu/digit_classifier_v1.pkl"}'

# 4. Flag aktivieren (nur bei FLAG_METHOD=inmemory; bei polling
#    statt dessen flags.json direkt editieren, siehe unten)
curl -X POST http://localhost:8000/admin/toggle-hotswap \
  -H "x-api-key: <KEY>" -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 5. Swap erneut versuchen -> erwartet: 200
curl -X POST http://localhost:8000/admin/swap-model \
  -H "x-api-key: <KEY>" -H "Content-Type: application/json" \
  -d '{"model_path": "/pfad/zu/digit_classifier_v1.pkl"}'

# 6. Klassifikation funktioniert nach dem Swap weiterhin normal
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"pixels": [[...]]}'
```

Für `FLAG_METHOD=polling` wird Schritt 4 ersetzt durch direktes Editieren
der Datei:
```bash
echo '{"hotswap_enabled": true}' > flags.json
```
Die Änderung wird hier erst nach Ablauf des Polling-Intervalls wirksam
(Standard 5s, einstellbar über `FLAG_POLL_INTERVAL_SECONDS`).

## Reaktionszeit messen

```bash
python measure_flag_latency.py polling    # bei FLAG_METHOD=polling
python measure_flag_latency.py inmemory   # bei FLAG_METHOD=inmemory
```

Misst die Zeit zwischen Flag-Änderung und sichtbarer Übernahme durch den
Dienst. `API_KEY` und `BASE_URL` im Skript ggf. anpassen.

## Produktionsbetrieb (systemd)

```bash
bash deploy/switch-method.sh [baseline|gunicorn|hotswap]
bash deploy/status.sh
```

`baseline` und `gunicorn` sind unverändert aus dem Kursumfeld übernommen
und nicht Teil der hier untersuchten Feature-Flag-Methoden. `hotswap`
startet den Dienst mit `FLAG_METHOD=inmemory` (siehe
`pixelwise-hotswap.service`).
