from flask import Flask, render_template, request, redirect, url_for
from models import db, Jugador
import redis as redis_lib
from flask_socketio import SocketIO, emit

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret!"
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost/gaming"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins='*')

with app.app_context():
    db.create_all()

# Configuración de Redis
redis = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)

@app.route("/")
def home():
    ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    return render_template("ranking.html", ranking=ranking)

@app.route("/jugadores")
def jugadores():
    jugadores = Jugador.query.all()
    return render_template("jugadores.html", jugadores=jugadores)

@app.route("/jugadores/agregar", methods=["GET", "POST"])
def agregar_jugador():
    if request.method == "POST":
        nombre = request.form["nombre"]
        nickname = request.form["nickname"]

        jugador = Jugador(nombre=nombre, nickname=nickname)
        db.session.add(jugador)
        db.session.commit()

        # Redis
        redis.zadd("ranking", {nickname: 0})
        redis.hset(f"player:{jugador.id}", mapping={
            "nombre": nombre,
            "nickname": nickname
        })
        updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
        socketio.emit('update_ranking', {'ranking': updated_ranking})

        return redirect(url_for("jugadores"))

    return render_template("agregar_jugador.html")


@app.route("/jugadores/editar/<int:id>", methods=["GET", "POST"])
def editar_jugador(id):
    jugador = Jugador.query.get_or_404(id)

    if request.method == "POST":
        antiguo_nickname = jugador.nickname

        jugador.nombre = request.form["nombre"]
        jugador.nickname = request.form["nickname"]
        db.session.commit()

        # Actualizar Redis correctamente
        score = redis.zscore("ranking", antiguo_nickname) or 0

        redis.zrem("ranking", antiguo_nickname)
        redis.zadd("ranking", {jugador.nickname: score})

        # Redis
        redis.hset(f"player:{jugador.id}", mapping={
            "nombre": jugador.nombre,
            "nickname": jugador.nickname
        })

        return redirect(url_for("jugadores"))

    return render_template("editar_jugador.html", jugador=jugador)


@app.route("/jugadores/eliminar/<int:id>")
def eliminar_jugador(id):
    jugador = Jugador.query.get_or_404(id)
    nickname = jugador.nickname

    db.session.delete(jugador)
    db.session.commit()

    # Redis
    redis.zrem("ranking", nickname)
    redis.delete(f"player:{id}")
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    socketio.emit('update_ranking', {'ranking': updated_ranking})

    return redirect(url_for("jugadores"))

@app.route("/agregar_puntaje")
def agregar_puntaje():
    jugadores = Jugador.query.all()
    return render_template("agregar_puntaje.html", jugadores=jugadores)

@app.route("/puntaje/<nickname>")
def puntaje(nickname):
    redis.zincrby("ranking", 1, nickname)
    
    # Obtenemos el ranking actualizado de Redis
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    
    # Enviamos el nuevo ranking a TODOS los conectados
    socketio.emit('update_ranking', {'ranking': updated_ranking})
    
    return redirect(request.referrer or url_for('home'))


if __name__ == "__main__":
    socketio.run(app, debug=True)