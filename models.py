# models.py
from bson.objectid import ObjectId

class Jugador:
    @staticmethod
    def esquema(nombre, nickname):
        return {
            "nombre": nombre,
            "nickname": nickname
        }