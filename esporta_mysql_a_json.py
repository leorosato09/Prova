import mysql.connector
import json
from datetime import datetime

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="leorosato09",
        password="leo09",
        database="progetto"
    )

def convert_date_to_string(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def esporta_dati():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM utenti")
    rows = cursor.fetchall()
    conn.close()

    # Convert date fields to string before dumping to JSON
    for row in rows:
        if isinstance(row['data_nascita'], datetime.date):
            row['data_nascita'] = row['data_nascita'].isoformat()

    with open('dati_utenti.json', 'w') as json_file:
        json.dump(rows, json_file, indent=4)

if __name__ == "__main__":
    esporta_dati()
