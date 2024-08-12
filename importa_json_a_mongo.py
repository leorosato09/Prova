import json
from pymongo import MongoClient

def get_mongo_connection():
    client = MongoClient("mongodb://localhost:27017")
    return client['progetto']  # Sostituisci con il nome del tuo database MongoDB

def importa_dati():
    db = get_mongo_connection()
    collection = db['utenti']  # Sostituisci con il nome della tua collezione MongoDB

    with open('dati_utenti.json') as json_file:
        data = json.load(json_file)
        collection.insert_many(data)

if __name__ == "__main__":
    importa_dati()
