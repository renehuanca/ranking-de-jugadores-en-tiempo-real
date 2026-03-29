from flask import Flask, render_template, request, redirect, url_for
from models import db, Player
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

@app.route("/players")
def players():
    players = Player.query.all()
    return render_template("players.html", players=players)

@app.route("/players/add", methods=["GET", "POST"])
def add_player():
    if request.method == "POST":
        name = request.form["name"]
        nickname = request.form["nickname"]

        player = Player(name=name, nickname=nickname)
        db.session.add(player)
        db.session.commit()

        # Redis
        redis.zadd("ranking", {nickname: 0})
        redis.hset(f"player:{player.id}", mapping={
            "name": name,
            "nickname": nickname
        })

        return redirect(url_for("players"))

    return render_template("add_player.html")


@app.route("/players/edit/<int:id>", methods=["GET", "POST"])
def edit_player(id):
    player = Player.query.get_or_404(id)

    if request.method == "POST":
        player.name = request.form["name"]
        player.nickname = request.form["nickname"]
        db.session.commit()

        # Redis
        redis.hset(f"player:{player.id}", mapping={
            "name": player.name,
            "nickname": player.nickname
        })

        return redirect(url_for("players"))

    return render_template("edit_player.html", player=player)


@app.route("/players/delete/<int:id>")
def delete_player(id):
    player = Player.query.get_or_404(id)
    nickname = player.nickname

    db.session.delete(player)
    db.session.commit()

    # Redis
    redis.zrem("ranking", nickname)
    redis.delete(f"player:{id}")

    return redirect(url_for("players"))


@app.route("/score/<nickname>")
def score(nickname):
    redis.zincrby("ranking", 10, nickname)
    
    # Obtenemos el ranking actualizado de Redis
    updated_ranking = redis.zrevrange("ranking", 0, -1, withscores=True)
    
    # Enviamos el nuevo ranking a TODOS los conectados
    socketio.emit('update_ranking', {'ranking': updated_ranking})
    
    return redirect(request.referrer or url_for('home'))


if __name__ == "__main__":
    socketio.run(app, debug=True)