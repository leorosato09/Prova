from flask import Flask, request, redirect, url_for, render_template
from pymongo import MongoClient
from bson.objectid import ObjectId
import logging
import traceback
from datetime import datetime

# Configura il logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

def get_db_connection():
    try:
        client = MongoClient(
            "mongodb+srv://leorosato09:Nibefile04@progettodb.vrk4x.mongodb.net/?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
        )
        db = client['ProgettoDB']
        return db
    except Exception as err:
        logging.error(f"Errore di connessione al database: {err}")
        raise

def calcola_eta_e_giorni(data_nascita):
    oggi = datetime.now()
    if isinstance(data_nascita, str):
        data_nascita = datetime.strptime(data_nascita, '%Y-%m-%d').date()

    eta = oggi.year - data_nascita.year - ((oggi.month, oggi.day) < (data_nascita.month, data_nascita.day))
    prossimo_compleanno = datetime(oggi.year, data_nascita.month, data_nascita.day)
    if prossimo_compleanno < oggi:
        prossimo_compleanno = datetime(oggi.year + 1, data_nascita.month, data_nascita.day)
    giorni_al_compleanno = (prossimo_compleanno - oggi).days
    return eta, giorni_al_compleanno

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/magazzino', methods=['GET', 'POST'])
def magazzino():
    try:
        db = get_db_connection()
        collection = db['utenti']

        if request.method == 'POST' and 'nome' in request.form:
            nome = request.form['nome']
            cognome = request.form['cognome']
            data_nascita = request.form['data_nascita']

            if nome and cognome and data_nascita:
                collection.insert_one({
                    'nome': nome,
                    'cognome': cognome,
                    'data_nascita': data_nascita
                })
                return redirect(url_for('magazzino'))

        query_nome = request.form.get('query_nome', '')
        query_cognome = request.form.get('query_cognome', '')
        query_data_nascita = request.form.get('query_data_nascita', '')
        sort_by = request.form.get('sort_by', 'eta_asc')

        query = {}
        if query_nome:
            query['nome'] = {'$regex': query_nome, '$options': 'i'}
        if query_cognome:
            query['cognome'] = {'$regex': query_cognome, '$options': 'i'}
        if query_data_nascita:
            query['data_nascita'] = query_data_nascita

        utenti_data = list(collection.find(query))

        utenti_info = []
        for utente in utenti_data:
            data_nascita = utente['data_nascita']
            if isinstance(data_nascita, str):
                data_nascita = datetime.strptime(data_nascita, '%Y-%m-%d').date()
            eta, giorni_al_compleanno = calcola_eta_e_giorni(data_nascita)
            utenti_info.append({
                'id': str(utente['_id']),
                'nome': utente['nome'],
                'cognome': utente['cognome'],
                'data_nascita': utente['data_nascita'],
                'eta': eta,
                'giorni_al_compleanno': giorni_al_compleanno
            })

        if sort_by == 'eta_asc':
            utenti_info.sort(key=lambda u: u['eta'])
        elif sort_by == 'eta_desc':
            utenti_info.sort(key=lambda u: u['eta'], reverse=True)
        elif sort_by == 'compleanno':
            utenti_info.sort(key=lambda u: u['giorni_al_compleanno'])

        return render_template('magazzino.html', utenti_info=utenti_info, query_nome=query_nome, query_cognome=query_cognome, query_data_nascita=query_data_nascita, sort_by=sort_by)

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

@app.route('/modifica/<id>', methods=['GET', 'POST'])
def modifica(id):
    try:
        db = get_db_connection()
        collection = db['utenti']

        if request.method == 'POST':
            nome = request.form['nome']
            cognome = request.form['cognome']
            data_nascita = request.form['data_nascita']

            if nome and cognome and data_nascita:
                collection.update_one(
                    {'_id': ObjectId(id)},
                    {'$set': {'nome': nome, 'cognome': cognome, 'data_nascita': data_nascita}}
                )
                return redirect(url_for('magazzino'))

        utente = collection.find_one({'_id': ObjectId(id)})

        return render_template('modifica.html', utente=utente)

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

@app.route('/elimina/<id>')
def elimina(id):
    try:
        db = get_db_connection()
        collection = db['utenti']
        collection.delete_one({'_id': ObjectId(id)})
        return redirect(url_for('magazzino'))

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
