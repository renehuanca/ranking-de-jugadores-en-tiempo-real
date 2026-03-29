from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Jugador(db.Model):

    __tablename__ = "jugadores"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Jugador {self.nickname}>"