from flask import Flask, render_template, redirect, url_for, request, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
import pymongo
import certifi
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Sostituisci con una chiave segreta sicura

# Configura il database MongoDB
app.config["MONGO_URI"] = "mongodb+srv://leorosato09:Nibefile04@progettodb.vrk4x.mongodb.net/ProgettoDB?retryWrites=true&w=majority"
mongo = PyMongo(app, tlsCAFile=certifi.where())
db = mongo.db
users_collection = db['users']
utenti_collection = db['utenti']

# Crea indici sui campi di ricerca
users_collection.create_index([('username', pymongo.ASCENDING)])
utenti_collection.create_index([('nome', pymongo.ASCENDING), ('cognome', pymongo.ASCENDING), ('data_nascita', pymongo.ASCENDING)])

# Configura Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password = user_data['password']

    @staticmethod
    def find_by_username(username):
        user_data = users_collection.find_one({'username': username}, {'_id': 1, 'username': 1, 'password': 1})
        if user_data:
            return User(user_data)
        return None

    def get_id(self):
        return self.id

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

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
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/magazzino', methods=['GET', 'POST'])
@login_required
def magazzino():
    if request.method == 'POST' and 'nome' in request.form:
        nome = request.form['nome']
        cognome = request.form['cognome']
        data_nascita = request.form['data_nascita']

        if nome and cognome and data_nascita:
            utenti_collection.insert_one({
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

    sort_order = []
    if sort_by == 'eta_asc':
        sort_order = [('eta', pymongo.ASCENDING)]
    elif sort_by == 'eta_desc':
        sort_order = [('eta', pymongo.DESCENDING)]
    elif sort_by == 'compleanno':
        sort_order = [('giorni_al_compleanno', pymongo.ASCENDING)]

    start_time = time.time()
    utenti_data = list(utenti_collection.find(query).sort(sort_order))
    end_time = time.time()
    print(f"Tempo di esecuzione: {end_time - start_time} secondi")

    utenti_info = []
    for utente in utenti_data:
        data_nascita = utente['data_nascita']
        eta, giorni_al_compleanno = calcola_eta_e_giorni(data_nascita)
        utenti_info.append({
            'id': str(utente['_id']),
            'nome': utente['nome'],
            'cognome': utente['cognome'],
            'data_nascita': utente['data_nascita'],
            'eta': eta,
            'giorni_al_compleanno': giorni_al_compleanno
        })

    return render_template('magazzino.html', utenti_info=utenti_info)

@app.route('/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica(id):
    if request.method == 'POST':
        nome = request.form['nome']
        cognome = request.form['cognome']
        data_nascita = request.form['data_nascita']

        if nome and cognome and data_nascita:
            utenti_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {'nome': nome, 'cognome': cognome, 'data_nascita': data_nascita}}
            )
            return redirect(url_for('magazzino'))

    utente = utenti_collection.find_one({'_id': ObjectId(id)})
    return render_template('modifica.html', utente=utente)

@app.route('/elimina/<id>')
@login_required
def elimina(id):
    utenti_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('magazzino'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.find_by_username(username)
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login fallito. Controlla il tuo username e password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.find_by_username(username)
        if existing_user:
            flash('Username già in uso, scegline un altro.')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            users_collection.insert_one({
                'username': username,
                'password': hashed_password
            })
            user = User.find_by_username(username)
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')

        # Verifica se il nuovo username è già in uso
        existing_user = users_collection.find_one({'username': new_username})
        if existing_user and existing_user['_id'] != current_user.get_id():
            flash('Username già in uso, scegline un altro.')
        else:
            # Aggiorna l'username se fornito e non in uso
            if new_username:
                users_collection.update_one(
                    {'_id': current_user.get_id()},
                    {'$set': {'username': new_username}}
                )
                flash('Username aggiornato con successo.')
            # Aggiorna la password se fornita
            if new_password:
                hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
                users_collection.update_one(
                    {'_id': current_user.get_id()},
                    {'$set': {'password': hashed_password}}
                )
                flash('Password aggiornata con successo.')

            # Aggiorna l'utente corrente
            user = User.find_by_username(new_username)
            login_user(user)

    return render_template('account.html')

if __name__ == "__main__":
    app.run(debug=False)
