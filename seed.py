from app import jugadores_col, redis
from models import Jugador

def seed():
    jugadores_demo = [
        ("Diego Ramos", "Shadow", "Dota 2"),
        ("Valeria Cruz", "Luna", "League of Legends"),
        ("Andrés Vega", "DarkSoul", "StarCraft II"),
        ("Camila Ortiz", "PixelQueen", "Minecraft"),
        ("Javier Flores", "NoScopePro", "Call of Duty"),
        ("Ricardo Méndez", "GhostRider", "Fortnite")
    ]

    for nombre, nickname, juego in jugadores_demo:
        existe = jugadores_col.find_one({"nickname": nickname})
        if existe:
            continue

        nuevo_jugador = Jugador.esquema(nombre, nickname, juego)
        result = jugadores_col.insert_one(nuevo_jugador)
        player_id = str(result.inserted_id)

        redis.zadd("ranking", {nickname: 0})

        redis.hset(f"player:{player_id}", mapping={
            "nombre": nombre,
            "nickname": nickname,
            "juego": juego
        })

    print("✅ Seeder ejecutado correctamente con jugadores gamers")

if __name__ == "__main__":
    seed()