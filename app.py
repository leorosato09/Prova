from flask import Flask, render_template, redirect, url_for, request, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import os
import certifi

# Configurazione di base
app = Flask(__name__)
app.secret_key = 'Nibefile04ProgettoDB'

# Configura MongoDB
app.config["MONGO_URI"] = "mongodb+srv://leorosato09:Nibefile04@progettodb.vrk4x.mongodb.net/ProgettoDB?retryWrites=true&w=majority"
mongo = PyMongo(app, tlsCAFile=certifi.where())

# Configura Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Definizione delle collezioni
users_collection = mongo.db.users
bottiglie_collection = mongo.db.bottiglie

# Modello utente
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password = user_data['password']

    @staticmethod
    def find_by_username(username):
        user_data = users_collection.find_one({'username': username})
        if user_data:
            return User(user_data)
        return None

    @staticmethod
    def get_by_id(user_id):
        user_data = users_collection.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Funzione di login
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

# Funzione di registrazione
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

# Dashboard protetta
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# Funzione per gestire l'inserimento nel magazzino (Configurazione)
@app.route('/configurazione', methods=['GET', 'POST'])
@login_required
def configurazione():
    if request.method == 'POST':
        if 'descrizione' in request.form and 'prezzo_base' in request.form and 'costo' in request.form and 'collocazione_1' in request.form:
            descrizione = request.form['descrizione']
            prezzo_base = request.form.get('prezzo_base', 0.0)
            costo = float(request.form.get('costo', 0.0))
            categoria = request.form.get('categoria', '')
            codice_a_barre = request.form.get('codice_a_barre', '')
            id_interno = request.form.get('id_interno', '')

            collocazioni = []
            quantita_totale = 0

            collocazione_1_list = request.form.getlist('collocazione_1')
            collocazione_2_list = request.form.getlist('collocazione_2')
            quantita_list = request.form.getlist('quantita')

            for collocazione_1, collocazione_2, quantita in zip(collocazione_1_list, collocazione_2_list, quantita_list):
                if collocazione_1 and collocazione_2 and quantita:
                    collocazioni.append({
                        'collocazione_1': collocazione_1,
                        'collocazione_2': collocazione_2,
                        'quantita': int(quantita)
                    })
                    quantita_totale += int(quantita)

            if descrizione and prezzo_base and costo and collocazioni:
                bottiglie_collection.insert_one({
                    'descrizione': descrizione,
                    'categoria': categoria,
                    'id_interno': id_interno,
                    'codice_a_barre': codice_a_barre,
                    'prezzo_base': prezzo_base,
                    'costo': costo,
                    'collocazioni': collocazioni,
                    'quantita_totale': quantita_totale
                })
                flash('Bottiglia registrata con successo!')
            else:
                flash('Compila tutti i campi necessari per l\'inserimento!')

    # Parametri di ordinamento e paginazione
    sort_by = request.args.get('sort_by', 'descrizione')
    sort_options = {
        'costo_desc': ('costo', -1),
        'costo_asc': ('costo', 1),
        'quantita_desc': ('quantita_totale', -1),
        'quantita_asc': ('quantita_totale', 1),
        'prezzo_base_desc': ('prezzo_base', -1),
        'prezzo_base_asc': ('prezzo_base', 1)
    }
    sort_field, sort_direction = sort_options.get(sort_by, ('descrizione', 1))

    # Parametri per la paginazione
    items_per_page = int(request.args.get('items_per_page', 10))
    current_page = int(request.args.get('page', 1))

    # Calcola l'offset per la paginazione
    skip_items = (current_page - 1) * items_per_page

    # Recupera tutte le bottiglie ordinate e paginazione
    total_bottiglie = bottiglie_collection.count_documents({})
    bottiglie_data = list(bottiglie_collection.find()
                          .sort(sort_field, sort_direction)
                          .skip(skip_items)
                          .limit(items_per_page))

    total_pages = (total_bottiglie + items_per_page - 1) // items_per_page  # Calcolo del numero di pagine

    return render_template('configurazione.html', 
                           bottiglie_info=bottiglie_data, 
                           current_page=current_page, 
                           total_pages=total_pages,
                           items_per_page=items_per_page,
                           sort_by=sort_by)



# Funzione per gestire la ricerca nel magazzino (Gestione Magazzino)
@app.route('/gestione_magazzino', methods=['GET'])
@login_required
def gestione_magazzino():
    query = {}
    sort_by = request.args.get('sort_by', 'descrizione')
    items_per_page = int(request.args.get('items_per_page', 10))
    current_page = int(request.args.get('page', 1))

    # Recupero dei parametri di ricerca
    search_descrizione = request.args.get('search_descrizione', '')
    search_categoria = request.args.get('search_categoria', '')
    search_codice_a_barre = request.args.get('search_codice_a_barre', '')
    search_id_interno = request.args.get('search_id_interno', '')
    search_prezzo_base = request.args.get('search_prezzo_base', '')
    search_quantita = request.args.get('search_quantita', '')
    search_collocazione_1 = request.args.get('search_collocazione_1', '')
    search_collocazione_2 = request.args.get('search_collocazione_2', '')
    search_costo = request.args.get('search_costo', '')
    search_costo_comparator = request.args.get('search_costo_comparator', '')

    # Costruzione della query in base ai filtri di ricerca
    if search_descrizione:
        query['descrizione'] = {'$regex': search_descrizione, '$options': 'i'}
    if search_categoria:
        query['categoria'] = search_categoria
    if search_codice_a_barre:
        query['codice_a_barre'] = search_codice_a_barre
    if search_id_interno:
        query['id_interno'] = search_id_interno
    if search_prezzo_base:
        query['prezzo_base'] = float(search_prezzo_base)
    if search_quantita:
        query['quantita_totale'] = int(search_quantita)
    if search_collocazione_1:
        query['collocazioni.collocazione_1'] = search_collocazione_1
    if search_collocazione_2:
        query['collocazioni.collocazione_2'] = search_collocazione_2
    if search_costo:
        if search_costo_comparator == 'maggiore':
            query['costo'] = {'$gt': float(search_costo)}
        elif search_costo_comparator == 'minore':
            query['costo'] = {'$lt': float(search_costo)}

    # Imposta l'ordinamento basato sul parametro sort_by
    sort_options = {
        'costo_desc': ('costo', -1),
        'costo_asc': ('costo', 1),
        'quantita_desc': ('quantita_totale', -1),
        'quantita_asc': ('quantita_totale', 1),
        'prezzo_base_desc': ('prezzo_base', -1),
        'prezzo_base_asc': ('prezzo_base', 1)
    }
    sort_field, sort_direction = sort_options.get(sort_by, ('descrizione', 1))

    # Recupera il numero totale di bottiglie e calcola il numero di pagine
    total_bottiglie = bottiglie_collection.count_documents(query)
    total_pages = (total_bottiglie + items_per_page - 1) // items_per_page  # Calcola il numero di pagine

    # Recupera le bottiglie con l'ordinamento e la paginazione
    bottiglie_data = list(
        bottiglie_collection.find(query)
        .sort(sort_field, sort_direction)
        .skip((current_page - 1) * items_per_page)
        .limit(items_per_page)
    )

    # Calcola il valore del magazzino basato sul prezzo base
    valore_magazzino = sum(float(b.get('prezzo_base', 0)) * int(b.get('quantita_totale', 0)) for b in bottiglie_data)

    return render_template(
        'gestione_magazzino.html',
        bottiglie_info=bottiglie_data,
        valore_magazzino=valore_magazzino,
        current_page=current_page,
        total_pages=total_pages
    )
# Funzione per modificare un elemento del magazzino
@app.route('/configurazione/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_configurazione(id):
    if request.method == 'POST':
        descrizione = request.form['descrizione']
        prezzo_base = float(request.form['prezzo_base'])
        costo = float(request.form['costo'])
        categoria = request.form.get('categoria', '')
        codice_a_barre = request.form.get('codice_a_barre', '')
        id_interno = request.form.get('id_interno', '')

        # Gestione delle collocazioni
        collocazioni = []
        quantita_totale = 0
        collocazione_1_list = request.form.getlist('collocazione_1')
        collocazione_2_list = request.form.getlist('collocazione_2')
        quantita_list = request.form.getlist('quantita')

        for collocazione_1, collocazione_2, quantita in zip(collocazione_1_list, collocazione_2_list, quantita_list):
            if collocazione_1 and collocazione_2 and quantita:
                collocazioni.append({
                    'collocazione_1': collocazione_1,
                    'collocazione_2': collocazione_2,
                    'quantita': int(quantita)
                })
                quantita_totale += int(quantita)

        # Aggiornamento della bottiglia nel database
        bottiglie_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'descrizione': descrizione,
                'prezzo_base': prezzo_base,
                'costo': costo,
                'categoria': categoria,
                'codice_a_barre': codice_a_barre,
                'id_interno': id_interno,
                'collocazioni': collocazioni,
                'quantita_totale': quantita_totale
            }}
        )
        return redirect(url_for('configurazione'))

    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})
    return render_template('modifica_configurazione.html', bottiglia=bottiglia)

@app.route('/configurazione/elimina/<id>')
@login_required
def elimina_configurazione(id):
    bottiglie_collection.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('configurazione'))

@app.route('/gestione_magazzino/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_gestione_magazzino(id):
    if request.method == 'POST':
        # Gestione delle collocazioni e quantità
        collocazioni = []
        quantita_totale = 0
        collocazione_1_list = request.form.getlist('collocazione_1')
        collocazione_2_list = request.form.getlist('collocazione_2')
        quantita_list = request.form.getlist('quantita')

        for collocazione_1, collocazione_2, quantita in zip(collocazione_1_list, collocazione_2_list, quantita_list):
            if collocazione_1 and collocazione_2 and quantita:
                collocazioni.append({
                    'collocazione_1': collocazione_1,
                    'collocazione_2': collocazione_2,
                    'quantita': int(quantita)
                })
                quantita_totale += int(quantita)

        # Aggiornamento delle collocazioni e quantità nel database
        bottiglie_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'collocazioni': collocazioni,
                'quantita_totale': quantita_totale
            }}
        )
        return redirect(url_for('gestione_magazzino'))

    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})
    return render_template('modifica_gestione_magazzino.html', bottiglia=bottiglia)


# Funzione di logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Funzione per gestire l'account utente
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        existing_user = users_collection.find_one({'username': new_username})
        if existing_user and existing_user['_id'] != current_user.get_id():
            flash('Username già in uso, scegline un altro.')
        else:
            if new_username:
                users_collection.update_one(
                    {'_id': ObjectId(current_user.get_id())},
                    {'$set': {'username': new_username}}
                )
                flash('Username aggiornato con successo.')
            if new_password:
                hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
                users_collection.update_one(
                    {'_id': ObjectId(current_user.get_id())},
                    {'$set': {'password': hashed_password}}
                )
                flash('Password aggiornata con successo.')
            user = User.find_by_username(new_username)
            login_user(user)
    return render_template('account.html')

@app.route('/configurazione/elimina_massiva', methods=['POST'])
@login_required
def elimina_massiva_configurazione():
    # Ottieni gli ID delle bottiglie selezionate dal form
    bottiglia_ids = request.form.getlist('bottiglia_ids')

    # Elimina le bottiglie selezionate
    for bottiglia_id in bottiglia_ids:
        bottiglie_collection.delete_one({'_id': ObjectId(bottiglia_id)})

    flash(f'{len(bottiglia_ids)} bottiglie eliminate con successo.')
    return redirect(url_for('configurazione'))

@app.route('/gestione_magazzino/elimina_massiva', methods=['POST'])
@login_required
def elimina_massiva_gestione_magazzino():
    # Ottieni gli ID delle bottiglie selezionate dal form
    bottiglia_ids = request.form.getlist('bottiglia_ids')

    # Elimina le bottiglie selezionate
    for bottiglia_id in bottiglia_ids:
        bottiglie_collection.delete_one({'_id': ObjectId(bottiglia_id)})

    flash(f'{len(bottiglia_ids)} bottiglie eliminate con successo.')
    return redirect(url_for('gestione_magazzino'))

if __name__ == "__main__":
    app.run(debug=True)
