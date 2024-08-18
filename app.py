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
reparti_collection = mongo.db.reparti
categorie_collection = mongo.db.categorie
attributi_collection = mongo.db.attributi

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

# Rotte di autenticazione
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

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

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
    total_pages = (total_bottiglie + items_per_page - 1) // items_per_page

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

# Modifica e eliminazione delle bottiglie
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
    categorie = list(categorie_collection.find().sort("nome", 1))  # Recupera le categorie dal database
    return render_template('modifica_configurazione.html', bottiglia=bottiglia, categorie=categorie)

@app.route('/configurazione')
@login_required
def configurazione():
    # Logica per visualizzare la configurazione (ad esempio, liste di categorie, reparti, ecc.)
    return render_template('prodotti.html')  # Assumendo che esista un template configurazione.html

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
        collocazione_1_list = request.form.getlist('collocazione_1[]')
        collocazione_2_list = request.form.getlist('collocazione_2[]')
        quantita_list = request.form.getlist('quantita[]')

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
    categorie = list(categorie_collection.find().sort("nome", 1))
    return render_template('modifica_gestione_magazzino.html', bottiglia=bottiglia, categorie=categorie)

# Funzioni di eliminazione massiva
@app.route('/configurazione/elimina_massiva', methods=['POST'])
@login_required
def elimina_massiva_configurazione():
    bottiglia_ids = request.form.getlist('bottiglia_ids')
    for bottiglia_id in bottiglia_ids:
        bottiglie_collection.delete_one({'_id': ObjectId(bottiglia_id)})
    flash(f'{len(bottiglia_ids)} bottiglie eliminate con successo.')
    return redirect(url_for('configurazione'))

@app.route('/gestione_magazzino/elimina_massiva', methods=['POST'])
@login_required
def elimina_massiva_gestione_magazzino():
    bottiglia_ids = request.form.getlist('bottiglia_ids')
    for bottiglia_id in bottiglia_ids:
        bottiglie_collection.delete_one({'_id': ObjectId(bottiglia_id)})
    flash(f'{len(bottiglia_ids)} bottiglie eliminate con successo.')
    return redirect(url_for('gestione_magazzino'))

# Gestione dei prodotti
@app.route('/prodotti', methods=['GET', 'POST'])
@login_required
def crea_prodotto():
    if request.method == 'POST':
        descrizione = request.form['descrizione']
        categoria = request.form['categoria']
        prezzo_base = float(request.form['prezzo_base'])
        costo = float(request.form['costo'])
        codice_a_barre = request.form.get('codice_a_barre', '')
        id_interno = request.form.get('id_interno', '')
        quantita = int(request.form['quantita'])
        collocazione_1 = request.form.getlist('collocazione_1[]')
        collocazione_2 = request.form.getlist('collocazione_2[]')

        collocazioni = []
        for c1, c2 in zip(collocazione_1, collocazione_2):
            collocazioni.append({
                'collocazione_1': c1,
                'collocazione_2': c2,
                'quantita': quantita  # Modifica questa parte se ogni collocazione ha una quantità diversa
            })

        nuovo_prodotto = {
            'descrizione': descrizione,
            'categoria': categoria,
            'prezzo_base': prezzo_base,
            'costo': costo,
            'codice_a_barre': codice_a_barre,
            'id_interno': id_interno,
            'quantita_totale': quantita,
            'collocazioni': collocazioni
        }

        bottiglie_collection.insert_one(nuovo_prodotto)
        flash('Prodotto aggiunto con successo!')

    # Recupera le categorie dal database
    categorie = list(categorie_collection.find().sort("nome", 1))
    bottiglie_info = list(bottiglie_collection.find().sort("descrizione", 1))

    return render_template('prodotti.html', categorie=categorie, bottiglie_info=bottiglie_info)

# Gestione dei reparti
@app.route('/reparti', methods=['GET', 'POST'])
@login_required
def reparti():
    if request.method == 'POST':
        nome_reparto = request.form['nome_reparto']
        valore_reparto = request.form.get('valore_reparto', '0')  # Imposta a '0' se il campo è vuoto
        
        # Aggiungi il nuovo reparto al database
        nuovo_reparto = {
            'nome': nome_reparto,
            'valore': float(valore_reparto) if valore_reparto else 0.0  # Converti in float o imposta a 0.0
        }
        reparti_collection.insert_one(nuovo_reparto)
        flash('Reparto aggiunto con successo!')
    
    # Recupera tutti i reparti dal database
    reparti = list(reparti_collection.find())
    return render_template('reparti.html', reparti=reparti)

# Gestione delle categorie
@app.route('/categorie', methods=['GET', 'POST'])
@login_required
def categorie():
    if request.method == 'POST':
        nome_categoria = request.form['nome_categoria']

        # Aggiungi la nuova categoria al database
        nuova_categoria = {'nome': nome_categoria}
        categorie_collection.insert_one(nuova_categoria)
        flash('Categoria aggiunta con successo!')

    # Recupera tutte le categorie dal database
    categorie = list(categorie_collection.find())
    return render_template('categorie.html', categorie=categorie)

@app.route('/categorie/elimina/<id>', methods=['POST', 'GET'])
def elimina_categoria(id):
    try:
        categorie_collection.delete_one({'_id': ObjectId(id)})
        flash('Categoria eliminata con successo!', 'success')
    except Exception as e:
        flash('Errore nell\'eliminazione della categoria.', 'error')
    return redirect(url_for('categorie'))

# Gestione degli attributi
@app.route('/attributi', methods=['GET', 'POST'])
@login_required
def attributi():
    if request.method == 'POST':
        nome_attributo = request.form['nome_attributo']
        valore_attributo = request.form.get('valore_attributo', '')

        # Aggiungi il nuovo attributo al database
        nuovo_attributo = {
            'nome_attributo': nome_attributo,
            'valore_attributo': valore_attributo
        }

        # Inserisci l'attributo nel database
        attributi_collection.insert_one(nuovo_attributo)
        flash('Attributo aggiunto con successo!')

    # Recupera tutti gli attributi per visualizzarli
    attributi = list(attributi_collection.find())

    return render_template('attributi.html', attributi=attributi)

@app.route('/reparti/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_reparto(id):
    reparto = reparti_collection.find_one({'_id': ObjectId(id)})
    
    if not reparto:
        flash("Reparto non trovato.", "error")
        return redirect(url_for('reparti'))
    
    if request.method == 'POST':
        nuovo_nome = request.form['nome_reparto']
        nuovo_valore = request.form.get('valore_reparto', 0.0)
        reparti_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'nome': nuovo_nome, 'valore': float(nuovo_valore)}}
        )
        flash('Reparto modificato con successo!', "success")
        return redirect(url_for('reparti'))
    
    return render_template('modifica_reparto.html', reparto=reparto)

@app.route('/reparti/elimina/<id>', methods=['POST'])
@login_required
def elimina_reparto(id):
    reparti_collection.delete_one({'_id': ObjectId(id)})
    flash('Reparto eliminato con successo!', "success")
    return redirect(url_for('reparti'))

@app.route('/attributi/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_attributo(id):
    attributo = attributi_collection.find_one({'_id': ObjectId(id)})
    
    if not attributo:
        flash("Attributo non trovato.", "error")
        return redirect(url_for('attributi'))
    
    if request.method == 'POST':
        nuovo_nome = request.form['nome_attributo']
        nuovo_valore = request.form['valore_attributo']
        attributi_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'nome_attributo': nuovo_nome, 'valore_attributo': nuovo_valore}}
        )
        flash('Attributo modificato con successo!', "success")
        return redirect(url_for('attributi'))
    
    return render_template('modifica_attributo.html', attributo=attributo)

@app.route('/attributi/elimina/<id>', methods=['POST'])
@login_required
def elimina_attributo(id):
    attributi_collection.delete_one({'_id': ObjectId(id)})
    flash('Attributo eliminato con successo!', "success")
    return redirect(url_for('attributi'))


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

@app.route('/categorie/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_categoria(id):
    categoria = categorie_collection.find_one({'_id': ObjectId(id)})
    
    if not categoria:
        flash("Categoria non trovata.", "error")
        return redirect(url_for('categorie'))
    
    if request.method == 'POST':
        nuovo_nome = request.form['nome_categoria']
        if nuovo_nome:
            categorie_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {'nome': nuovo_nome}}
            )
            flash('Categoria modificata con successo!', "success")
        else:
            flash('Il nome della categoria non può essere vuoto.', "error")
        return redirect(url_for('categorie'))
    
    return render_template('modifica_categoria.html', categoria=categoria)


if __name__ == "__main__":
    app.run(debug=True)
