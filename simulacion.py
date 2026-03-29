"""Simulación de puntajes para el ranking.

Ejecuta este script con el servidor Flask levantado. Cada iteración
llama a /puntaje/<nickname> para incrementar el puntaje y generar la
actualización en tiempo real.

Opciones de entorno:
- SIM_URL: URL base del servidor (por defecto http://127.0.0.1:5000)
- SIM_INTERVAL: segundos entre cada incremento (por defecto 1.0)
- SIM_STEPS: cantidad de incrementos a realizar (por defecto 0, ejecución continua)
- REDIS_URL: URL de Redis para obtener nicknames si no se especifica la lista
"""

import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import redis
except ImportError:
    redis = None

BASE_URL = os.environ.get("SIM_URL", "http://127.0.0.1:5000")
INTERVAL = float(os.environ.get("SIM_INTERVAL", "0.5"))
STEPS = int(os.environ.get("SIM_STEPS", "0"))
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

DEFAULT_NICKNAMES = []


def get_nicknames_from_redis():
    if redis is None:
        return []
    client = redis.from_url(REDIS_URL, decode_responses=True)
    return client.zrange("ranking", 0, -1)


def run_simulation(nicknames):
    if not nicknames:
        raise ValueError("No se encontró ningún nickname para simular.")

    total_label = "ilimitados" if STEPS == 0 else str(STEPS)
    print(f"Simulación en {BASE_URL} con {len(nicknames)} jugadores.")
    print(f"Intervalo: {INTERVAL}s, pasos: {total_label}")
    print("---")

    step = 0
    while STEPS == 0 or step < STEPS:
        step += 1
        nickname = random.choice(nicknames)
        encoded = urllib.parse.quote_plus(nickname)
        url = f"{BASE_URL}/puntaje/{encoded}"
        request = urllib.request.Request(url, method="GET")

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status = response.status
            print(f"[{step}/{STEPS}] +10 puntos a {nickname} -> {status}")
        except urllib.error.HTTPError as exc:
            print(f"[{step}/{STEPS}] Error HTTP {exc.code} en {nickname}: {exc.reason}")
        except urllib.error.URLError as exc:
            print(f"[{step}/{STEPS}] Error de conexión: {exc}")
            break

        time.sleep(INTERVAL)


if __name__ == "__main__":
    nicknames = DEFAULT_NICKNAMES or get_nicknames_from_redis()
    if not nicknames:
        print("No se encontraron nicknames en Redis. Agrega jugadores primero.")
    else:
        run_simulation(nicknames)
