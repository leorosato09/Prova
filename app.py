from flask import Flask, request, redirect, url_for, render_template_string
import logging
import traceback
from datetime import datetime
import os
from dotenv import load_dotenv
import mysql.connector

# Carica le variabili d'ambiente dal file .env
load_dotenv()

app = Flask(__name__)

# Configura il logging
logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USERNAME'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_DATABASE'),
        port=os.getenv('DB_PORT', 3306)  # Usa la porta di default 3306 se non specificata
    )
    return conn

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

@app.route('/', methods=['GET', 'POST'])
def chiedi_dati():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST' and 'nome' in request.form:
            nome = request.form['nome']
            cognome = request.form['cognome']
            data_nascita = request.form['data_nascita']

            if nome and cognome and data_nascita:
                cursor.execute('INSERT INTO utenti (nome, cognome, data_nascita) VALUES (%s, %s, %s)',
                               (nome, cognome, data_nascita))
                conn.commit()
                return redirect(url_for('chiedi_dati'))

        query_nome = request.form.get('query_nome', '')
        query_cognome = request.form.get('query_cognome', '')
        query_data_nascita = request.form.get('query_data_nascita', '')
        sort_by = request.form.get('sort_by', 'eta_asc')

        sql_query = 'SELECT * FROM utenti WHERE 1=1'
        params = []

        if query_nome:
            sql_query += ' AND nome LIKE %s'
            params.append(f'%{query_nome}%')
        if query_cognome:
            sql_query += ' AND cognome LIKE %s'
            params.append(f'%{query_cognome}%')
        if query_data_nascita:
            sql_query += ' AND data_nascita = %s'
            params.append(query_data_nascita)

        cursor.execute(sql_query, params)
        utenti = cursor.fetchall()
        utenti_info = []

        for utente in utenti:
            data_nascita = utente['data_nascita']
            if isinstance(data_nascita, str):
                data_nascita = datetime.strptime(data_nascita, '%Y-%m-%d').date()
            eta, giorni_al_compleanno = calcola_eta_e_giorni(data_nascita)
            utenti_info.append({
                'id': utente['id'],
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

        conn.close()

        return render_template_string('''
            <!DOCTYPE html>
            <html lang="it">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Gestione Dati Utenti</title>
                <style>
                    .container {
                        display: flex;
                    }
                    .form-container, .search-container {
                        flex: 1;
                        margin-right: 20px;
                    }
                    .user-list {
                        margin-top: 20px;
                    }
                    .user-list ul {
                        list-style-type: none;
                        padding: 0;
                    }
                    .user-list li {
                        padding: 10px;
                        border: 1px solid #ccc;
                        margin-bottom: 5px;
                        border-radius: 5px;
                    }
                    .user-list h2 {
                        margin-bottom: 10px;
                    }
                    .sort-options {
                        margin-bottom: 15px;
                    }
                    .sort-options label {
                        margin-right: 10px;
                    }
                    .sort-options select {
                        padding: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="form-container">
                        <form method="post">
                            <label for="nome">Inserisci il tuo nome qui:</label>
                            <input type="text" id="nome" name="nome" required>
                            <br>
                            <label for="cognome">Inserisci il tuo cognome qui:</label>
                            <input type="text" id="cognome" name="cognome" required>
                            <br>
                            <label for="data_nascita">Inserisci la tua data di nascita:</label>
                            <input type="date" id="data_nascita" name="data_nascita" required>
                            <br>
                            <input type="submit" value="Invia">
                        </form>
                    </div>
                    <div class="search-container">
                        <form method="post">
                            <label for="query_nome">Cerca per nome:</label>
                            <input type="text" id="query_nome" name="query_nome" value="{{ query_nome }}">
                            <br>
                            <label for="query_cognome">Cerca per cognome:</label>
                            <input type="text" id="query_cognome" name="query_cognome" value="{{ query_cognome }}">
                            <br>
                            <label for="query_data_nascita">Cerca per data di nascita:</label>
                            <input type="date" id="query_data_nascita" name="query_data_nascita" value="{{ query_data_nascita }}">
                            <br>
                            <input type="submit" value="Cerca">
                        </form>
                    </div>
                </div>

                <div class="user-list">
                    <h2>Utenti Registrati</h2>
                    <div class="sort-options">
                        <form method="post">
                            <label for="sort_by">Ordina per:</label>
                            <select name="sort_by" id="sort_by" onchange="this.form.submit()">
                                <option value="eta_asc" {% if sort_by == 'eta_asc' %}selected{% endif %}>Età crescente</option>
                                <option value="eta_desc" {% if sort_by == 'eta_desc' %}selected{% endif %}>Età decrescente</option>
                                <option value="compleanno" {% if sort_by == 'compleanno' %}selected{% endif %}>Compleanno</option>
                            </select>
                        </form>
                    </div>
                    <ul>
                        {% for utente in utenti_info %}
                            <li>
                                {{ utente.nome }} {{ utente.cognome }} - Data di nascita: {{ utente.data_nascita }} - Età: {{ utente.eta }} anni - Mancano {{ utente.giorni_al_compleanno }} giorni al tuo compleanno
                                <br>
                                <a href="/modifica/{{ utente.id }}">Modifica</a> |
                                <a href="/elimina/{{ utente.id }}">Elimina</a>
                            </li>
                        {% endfor %}
                    </ul>
                </div>
            </body>
            </html>
        ''', utenti_info=utenti_info, query_nome=query_nome, query_cognome=query_cognome, query_data_nascita=query_data_nascita, sort_by=sort_by)

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

@app.route('/modifica/<int:id>', methods=['GET', 'POST'])
def modifica(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM utenti WHERE id = %s', (id,))
        utente = cursor.fetchone()

        if request.method == 'POST':
            nome = request.form['nome']
            cognome = request.form['cognome']
            data_nascita = request.form['data_nascita']

            if nome, cognome, and data_nascita:
                cursor.execute('UPDATE utenti SET nome = %s, cognome = %s, data_nascita = %s WHERE id = %s',
                               (nome, cognome, data_nascita, id))
                conn.commit()
                conn.close()
                return redirect(url_for('chiedi_dati'))

        conn.close()

        return render_template_string('''
            <!DOCTYPE html>
            <html lang="it">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Modifica Dati</title>
            </head>
            <body>
                <h2>Modifica Dati Utente</h2>
                <form method="post">
                    <label for="nome">Nome:</label>
                    <input type="text" id="nome" name="nome" value="{{ utente['nome'] }}" required>
                    <br>
                    <label for="cognome">Cognome:</label>
                    <input type="text" id="cognome" name="cognome" value="{{ utente['cognome'] }}" required>
                    <br>
                    <label for="data_nascita">Data di nascita:</label>
                    <input type="date" id="data_nascita" name="data_nascita" value="{{ utente['data_nascita'] }}" required>
                    <br>
                    <input type="submit" value="Salva modifiche">
                </form>
                <br>
                <a href="/">Torna indietro</a>
            </body>
            </html>
        ''', utente=utente)

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

@app.route('/elimina/<int:id>')
def elimina(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM utenti WHERE id = %s', (id,))
        conn.commit()
        conn.close()
        return redirect(url_for('chiedi_dati'))

    except Exception as e:
        logging.error(f"Errore: {e}")
        logging.error(traceback.format_exc())
        return "Si è verificato un errore nel server", 500

if __name__ == "__main__":
    app.run(debug=True)
