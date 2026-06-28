import sys
import time
import json
import requests

BASE_URL = "http://localhost:8000"
API_KEY = "meinGeheimnis123"
FLAGS_FILE_PATH = "flags.json"
POLL_CHECK_EVERY_S = 0.05
TIMEOUT_S = 30

def status_headers():
    return {"x-api-key": API_KEY}

def get_status() -> bool:
    r = requests.get(f"{BASE_URL}/admin/hotswap-status", headers=status_headers())
    r.raise_for_status()
    return r.json()["hotswap_enabled"]

def measure_polling():
    current = get_status()
    target = not current
    start = time.perf_counter()
    with open(FLAGS_FILE_PATH, "w") as f:
        json.dump({"hotswap_enabled": target}, f)
    write_time = time.perf_counter()
    while time.perf_counter() - start < TIMEOUT_S:
        if get_status() == target:
            latency_ms = (time.perf_counter() - write_time) * 1000
            print(f"[polling] Datei geschrieben -> Server übernimmt nach {latency_ms:.1f} ms")
            return latency_ms
        time.sleep(POLL_CHECK_EVERY_S)
    print("[polling] TIMEOUT.")
    return None

def measure_inmemory():
    current = get_status()
    target = not current
    start = time.perf_counter()
    r = requests.post(
        f"{BASE_URL}/admin/toggle-hotswap",
        headers={**status_headers(), "Content-Type": "application/json"},
        json={"enabled": target},
    )
    r.raise_for_status()
    latency_ms = (time.perf_counter() - start) * 1000
    print(f"[inmemory] Round-Trip: {latency_ms:.1f} ms")
    return latency_ms

if __name__ == "__main__":
    method = sys.argv[1] if len(sys.argv) > 1 else "polling"
    if method == "polling":
        measure_polling()
    else:
        measure_inmemory()
