from flask import Flask, render_template, request, redirect, url_for, abort
from pymongo import MongoClient
from bson.objectid import ObjectId
import redis as redis_lib
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"

# --- CONFIGURACIÓN DE PYMONGO DIRECTO ---
client = MongoClient("mongodb://localhost:27017/")
db_mongo = client["gaming"] 
# Colección explícita
jugadores_col = db_mongo.jugadores 

socketio = SocketIO(app, cors_allowed_origins='*')
redis = redis_lib.Redis(host="localhost", port=6379, decode_responses=True)

@app.route("/")
def home():
    redis.incr("visitas")
    visitas = redis.get("visitas")
    
    ip = request.remote_addr
    redis.set(f"online:{ip}", 1, ex=30)
    usuarios_online = len(redis.keys("online:*"))

    ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    return render_template("ranking.html", ranking=ranking, visitas=visitas, usuarios_online=usuarios_online)

@app.route("/jugadores")
def jugadores():
    # .find() devuelve un cursor, lo convertimos a lista
    lista_jugadores = list(jugadores_col.find())
    return render_template("jugadores.html", jugadores=lista_jugadores)

@app.route("/jugadores/agregar", methods=["GET", "POST"])
def agregar_jugador():
    if request.method == "POST":
        nombre = request.form["nombre"]
        nickname = request.form["nickname"]

        nuevo_jugador = {"nombre": nombre, "nickname": nickname}
        result = jugadores_col.insert_one(nuevo_jugador)
        player_id = str(result.inserted_id)

        # Sincronización con Redis
        redis.hset(f"player:{player_id}", mapping={"nombre": nombre, "nickname": nickname})
        redis.zadd("ranking", {nickname: 0})
        
        updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
        socketio.emit('update_ranking', {'ranking': updated_ranking})

        return redirect(url_for("jugadores"))
    return render_template("agregar_jugador.html")

@app.route("/jugadores/editar/<id>", methods=["GET", "POST"])
def editar_jugador(id):
    # Reemplazo de find_one_or_404
    jugador = jugadores_col.find_one({"_id": ObjectId(id)})
    if not jugador:
        abort(404)

    if request.method == "POST":
        antiguo_nickname = jugador["nickname"]
        nuevo_nombre = request.form["nombre"]
        nuevo_nickname = request.form["nickname"]

        jugadores_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"nombre": nuevo_nombre, "nickname": nuevo_nickname}}
        )

        # Lógica de Redis para actualizar nickname en el ranking
        score = redis.zscore("ranking", antiguo_nickname) or 0
        redis.zrem("ranking", antiguo_nickname)
        redis.zadd("ranking", {nuevo_nickname: score})

        redis.hset(f"player:{id}", mapping={"nombre": nuevo_nombre, "nickname": nuevo_nickname})
        
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

    # Limpieza en Redis
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
    redis.zincrby("ranking", 1, nickname)
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    socketio.emit('update_ranking', {'ranking': updated_ranking})
    return redirect(request.referrer or url_for('home'))

if __name__ == "__main__":
    socketio.run(app, debug=True)