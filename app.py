from flask import Flask, render_template, request, redirect, url_for, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
import redis as redis_lib
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"

# --- CONFIGURACIÓN DE PYMONGO ---
client = MongoClient("mongodb://localhost:27017/")
db_mongo = client["gaming"] 
jugadores_col = db_mongo.jugadores 

socketio = SocketIO(app, cors_allowed_origins='*')

# --- CONFIGURACIÓN DE REDIS ---
redis = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)

@app.route("/")
def home():
    # Incrementa el contador global de visitas (String)
    redis.incr("visitas")
    visitas = redis.get("visitas")
    
    # Registra IP con expiración de 30s para conteo de usuarios online
    ip = request.remote_addr
    redis.set(f"online:{ip}", 1, ex=30)
    usuarios_online = len(redis.keys("online:*"))

    # Recupera el ranking completo del Sorted Set (ZSET) de mayor a menor
    ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    return render_template("ranking.html", ranking=ranking, visitas=visitas, usuarios_online=usuarios_online)

@app.route("/jugadores")
def jugadores():
    lista_jugadores = list(jugadores_col.find())
    return render_template("jugadores.html", jugadores=lista_jugadores)

@app.route("/jugadores/agregar", methods=["GET", "POST"])
def agregar_jugador():
    if request.method == "POST":
        nombre = request.form["nombre"]
        nickname = request.form["nickname"]
        juego = request.form["juego"]

        nuevo_jugador = {
            "nombre": nombre, 
            "nickname": nickname,
            "juego": juego
        }
        result = jugadores_col.insert_one(nuevo_jugador)
        player_id = str(result.inserted_id)

        # Almacena el perfil del jugador en un Hash (HSET)
        redis.hset(f"player:{player_id}", mapping={
            "nombre": nombre, 
            "nickname": nickname,
            "juego": juego
        })
        # Inicializa al jugador en el ranking con puntaje 0 (ZSET)
        redis.zadd("ranking", {nickname: 0})
        
        updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
        socketio.emit('update_ranking', {'ranking': updated_ranking})

        return redirect(url_for("jugadores"))
    return render_template("agregar_jugador.html")

@app.route("/jugadores/editar/<id>", methods=["GET", "POST"])
def editar_jugador(id):
    jugador = jugadores_col.find_one({"_id": ObjectId(id)})
    if not jugador:
        abort(404)

    if request.method == "POST":
        antiguo_nickname = jugador["nickname"]
        nuevo_nombre = request.form["nombre"]
        nuevo_nickname = request.form["nickname"]
        nuevo_juego = request.form["juego"]

        jugadores_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "nombre": nuevo_nombre, 
                "nickname": nuevo_nickname,
                "juego": nuevo_juego
            }}
        )

        # Mantiene el puntaje actual al cambiar el nickname en el ranking
        score = redis.zscore("ranking", antiguo_nickname) or 0
        redis.zrem("ranking", antiguo_nickname) # Elimina el miembro antiguo
        redis.zadd("ranking", {nuevo_nickname: score}) # Agrega el nuevo miembro

        # Actualiza los datos del perfil en el Hash
        redis.hset(f"player:{id}", mapping={
            "nombre": nuevo_nombre, 
            "nickname": nuevo_nickname,
            "juego": nuevo_juego
        })
        
        updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
        socketio.emit('update_ranking', {'ranking': updated_ranking})

        return redirect(url_for("jugadores"))

    return render_template("editar_jugador.html", jugador=jugador)

@app.route("/jugadores/eliminar/<id>")
def eliminar_jugador(id):
    jugador = jugadores_col.find_one({"_id": ObjectId(id)})
    if not jugador:
        abort(404)
        
    nickname = jugador["nickname"]
    jugadores_col.delete_one({"_id": ObjectId(id)})

    # Elimina al jugador del ranking (ZSET) y borra su Hash de perfil
    redis.zrem("ranking", nickname)
    redis.delete(f"player:{id}")
    
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    socketio.emit('update_ranking', {'ranking': updated_ranking})

    return redirect(url_for("jugadores"))

@app.route("/agregar_puntaje")
def agregar_puntaje():
    jugadores = list(jugadores_col.find())
    return render_template("agregar_puntaje.html", jugadores=jugadores)

@app.route("/puntaje/<nickname>")
def puntaje(nickname):
    # Incrementa en 1 el puntaje del jugador en el ranking (ZSET)
    redis.zincrby("ranking", 1, nickname)
    
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    socketio.emit('update_ranking', {'ranking': updated_ranking})
    return redirect(request.referrer or url_for('home'))

if __name__ == "__main__":
    socketio.run(app, debug=True)