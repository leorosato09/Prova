from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, current_user, logout_user
from bson.objectid import ObjectId
from . import app
from .models import User, users_collection, bottiglie_collection
from werkzeug.security import generate_password_hash, check_password_hash

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/magazzino', methods=['GET', 'POST'])
@login_required
def magazzino():
    if request.method == 'POST':
        descrizione = request.form['descrizione']
        categoria = request.form['categoria']
        id_interno = request.form.get('id_interno', '')
        codice_a_barre = request.form.get('codice_a_barre', '')
        prezzo_base = request.form.get('prezzo_base', 0.0)
        collocazione = request.form.get('collocazione', '')
        quantita = int(request.form.get('quantita', 0))

        if descrizione and categoria:
            bottiglie_collection.insert_one({
                'descrizione': descrizione,
                'categoria': categoria,
                'id_interno': id_interno,
                'codice_a_barre': codice_a_barre,
                'prezzo_base': prezzo_base,
                'collocazione': collocazione,
                'quantita': quantita
            })
            return redirect(url_for('magazzino'))

    query_descrizione = request.form.get('query_descrizione', '')
    query_categoria = request.form.get('query_categoria', '')
    query_id_interno = request.form.get('query_id_interno', '')
    query_codice_a_barre = request.form.get('query_codice_a_barre', '')
    query_prezzo_base = request.form.get('query_prezzo_base', '')
    query_collocazione = request.form.get('query_collocazione', '')
    query_quantita = request.form.get('query_quantita', '')

    query = {}
    if query_descrizione:
        query['descrizione'] = {'$regex': query_descrizione, '$options': 'i'}
    if query_categoria:
        query['categoria'] = query_categoria
    if query_id_interno:
        query['id_interno'] = query_id_interno
    if query_codice_a_barre:
        query['codice_a_barre'] = query_codice_a_barre
    if query_prezzo_base:
        query['prezzo_base'] = float(query_prezzo_base)
    if query_collocazione:
        query['collocazione'] = query_collocazione
    if query_quantita:
        query['quantita'] = int(query_quantita)

    bottiglie_data = list(bottiglie_collection.find(query))

    return render_template('magazzino.html', bottiglie_info=bottiglie_data,
                           query_descrizione=query_descrizione,
                           query_categoria=query_categoria,
                           query_id_interno=query_id_interno,
                           query_codice_a_barre=query_codice_a_barre,
                           query_prezzo_base=query_prezzo_base,
                           query_collocazione=query_collocazione,
                           query_quantita=query_quantita)

@app.route('/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica(id):
    if request.method == 'POST':
        descrizione = request.form['descrizione']
        categoria = request.form['categoria']
        id_interno = request.form.get('id_interno', '')
        codice_a_barre = request.form.get('codice_a_barre', '')
        prezzo_base = float(request.form['prezzo_base'])
        collocazione = request.form.get('collocazione', '')
        quantita = int(request.form.get('quantita', 0))

        if descrizione and categoria and prezzo_base:
            bottiglie_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'descrizione': descrizione,
                    'categoria': categoria,
                    'id_interno': id_interno,
                    'codice_a_barre': codice_a_barre,
                    'prezzo_base': prezzo_base,
                    'collocazione': collocazione,
                    'quantita': quantita
                }}
            )
            return redirect(url_for('magazzino'))

    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})
    return render_template('modifica.html', bottiglia=bottiglia)

@app.route('/elimina/<id>')
@login_required
def elimina(id):
    bottiglie_collection.delete_one({'_id': ObjectId(id)})
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
        
        # Verifica se l'utente esiste già
        existing_user = User.find_by_username(username)
        if existing_user:
            flash('Username già in uso, scegline un altro.')
        else:
            # Crea un nuovo utente
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            users_collection.insert_one({
                'username': username,
                'password': hashed_password
            })
            user = User.find_by_username(username)
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('register.html', title="Registrati")

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
                    {'_id': ObjectId(current_user.get_id())},
                    {'$set': {'username': new_username}}
                )
                flash('Username aggiornato con successo.')
            # Aggiorna la password se fornita
            if new_password:
                hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
                users_collection.update_one(
                    {'_id': ObjectId(current_user.get_id())},
                    {'$set': {'password': hashed_password}}
                )
                flash('Password aggiornata con successo.')

            # Aggiorna l'utente corrente
            user = User.find_by_username(new_username)
            login_user(user)

    return render_template('account.html')
