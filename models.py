# models.py
from bson.objectid import ObjectId

class Jugador:
    @staticmethod
    def esquema(nombre, nickname, juego):
        return {
            "nombre": nombre,
            "nickname": nickname,
            "juego": juego
        }