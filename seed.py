from app import app, db, Jugador, redis
import random

def seed():
    with app.app_context():
        jugadores_demo = [
            ("Diego Ramos", "Shadow"),
            ("Valeria Cruz", "Luna"),
            ("Andrés Vega", "DarkSoul"),
            ("Camila Ortiz", "PixelQueen"),
            ("Javier Flores", "NoScopePro"),
            ("Ricardo Méndez", "GhostRider"),
        ]

        for nombre, nickname in jugadores_demo:
            existe = Jugador.query.filter_by(nickname=nickname).first()
            if existe:
                continue

            jugador = Jugador(nombre=nombre, nickname=nickname)
            db.session.add(jugador)
            db.session.commit()

            # Ranking aleatorio tipo leaderboard
            redis.zadd("ranking", {nickname: 0})

            # Hash por jugador
            redis.hset(f"player:{jugador.id}", mapping={
                "nombre": nombre,
                "nickname": nickname
            })

        print("✅ Seeder ejecutado correctamente con jugadores gamers")


if __name__ == "__main__":
    seed()