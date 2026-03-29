from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Player(db.Model):

    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Player {self.nickname}>"