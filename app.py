from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_pymongo import PyMongo
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime
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
magazzino_collection = mongo.db.magazzino
movimenti_collection = mongo.db.movimenti

# ---------------------------
# Modelli
# ---------------------------

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

def registra_movimento(utente, descrizione, quantita, collocazione_origine, collocazione_destinazione, tipo_movimento, orario, prodotto_id):
    movimento = {
        'utente': utente,
        'descrizione': descrizione,
        'quantita': quantita,
        'collocazione_origine': collocazione_origine,
        'collocazione_destinazione': collocazione_destinazione,
        'tipo_movimento': tipo_movimento,
        'orario': orario,
        'prodotto_id': prodotto_id,
        'data': datetime.now()
    }
    movimenti_collection.insert_one(movimento)

# ---------------------------
# Rotte di autenticazione
# ---------------------------

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
        email = request.form['email']
        password = request.form['password']
        
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('Username già in uso, scegline un altro.')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            user_id = users_collection.insert_one({
                'username': username,
                'email': email,
                'password': hashed_password,
                'active': False,
                'role': None
            }).inserted_id
            
            msg = Message('Nuova richiesta di registrazione', 
                          sender='your_email@gmail.com', 
                          recipients=['leorosato.rosato@gmail.com'])
            msg.body = f"""Un nuovo utente si è registrato con i seguenti dettagli:

Username: {username}
Email: {email}

Per attivare l'account e assegnare un ruolo, visita il link:
http://localhost:5000/admin/activate_user/{user_id}
"""
            mail.send(msg)
            flash('Registrazione avvenuta con successo! Attendi l\'approvazione dell\'amministratore.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/activate_user/<user_id>', methods=['GET', 'POST'])
@login_required
def activate_user(user_id):
    if current_user.role != 'admin':
        flash('Non hai i permessi per accedere a questa pagina.')
        return redirect(url_for('dashboard'))
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash('Utente non trovato.')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        role = request.form['role']
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'active': True, 'role': role}}
        )
        msg = Message('Account attivato', 
                      sender='your_email@gmail.com', 
                      recipients=[user['email']])
        msg.body = f"""Ciao {user['username']},

Il tuo account è stato attivato con successo! Ora puoi accedere utilizzando le tue credenziali.

Buona giornata!
"""
        mail.send(msg)
        flash('Utente attivato con successo.')
        return redirect(url_for('dashboard'))
    
    return render_template('activate_user.html', user=user)

# ---------------------------
# Dashboard
# ---------------------------

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/cercadashboard', methods=['GET'])
@login_required
def cerca_bottiglia_dashboard():
    query = request.args.get('query')
    if query:
        risultati = list(bottiglie_collection.find({'descrizione': {'$regex': query, '$options': 'i'}}))
        if risultati:
            return render_template('dashboard.html', risultati=risultati, query=query)
        else:
            return render_template('dashboard.html', nessun_risultato=True, query=query)
    return redirect(url_for('dashboard'))


# ---------------------------
# Gestione Bottiglie
# ---------------------------

@app.route('/sposta_bottiglia/<id>', methods=['POST'])
@login_required
def sposta_bottiglia(id):
    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})
    if not bottiglia:
        flash('Bottiglia non trovata.', 'danger')
        return redirect(url_for('scheda_bottiglia', id=id))

    collocazione_esistente = request.form.get('collocazione_esistente')
    nuova_area = request.form.get('nuova_area')
    nuova_sotto_area = request.form.get('nuova_sotto_area')
    nuovo_riquadro = request.form.get('nuovo_riquadro')
    quantita_da_spostare = int(request.form.get('quantita_da_spostare'))

    if not nuova_area or not nuova_sotto_area or quantita_da_spostare <= 0:
        flash('Informazioni mancanti o non valide.', 'danger')
        return redirect(url_for('scheda_bottiglia', id=id))

    for collocazione in bottiglia['collocazioni']:
        if (collocazione.get('collocazione_1') == collocazione_esistente.split('/')[0] and 
            collocazione.get('collocazione_2') == collocazione_esistente.split('/')[1] and 
            collocazione.get('riquadro') == (collocazione_esistente.split('/')[2] if len(collocazione_esistente.split('/')) > 2 else None)):

            quantita_disponibile = collocazione['quantita']

            if quantita_da_spostare > quantita_disponibile:
                flash(f'Non puoi spostare {quantita_da_spostare} bottiglie. Quantità disponibile: {quantita_disponibile}', 'danger')
                return redirect(url_for('scheda_bottiglia', id=id))

            collocazione['quantita'] -= quantita_da_spostare
            if collocazione['quantita'] == 0:
                bottiglia['collocazioni'].remove(collocazione)
            break

    nuova_collocazione_trovata = False
    for collocazione in bottiglia['collocazioni']:
        if (collocazione['collocazione_1'] == nuova_area and 
            collocazione['collocazione_2'] == nuova_sotto_area and 
            collocazione.get('riquadro') == (nuovo_riquadro if nuovo_riquadro else None)):
            
            collocazione['quantita'] += quantita_da_spostare
            nuova_collocazione_trovata = True
            break

    if not nuova_collocazione_trovata:
        bottiglia['collocazioni'].append({
            'collocazione_1': nuova_area,
            'collocazione_2': nuova_sotto_area,
            'riquadro': nuovo_riquadro if nuovo_riquadro else None,
            'quantita': quantita_da_spostare
        })

    bottiglie_collection.update_one({'_id': ObjectId(id)}, {'$set': {'collocazioni': bottiglia['collocazioni']}})
    flash('Spostamento eseguito con successo.', 'success')
    return redirect(url_for('scheda_bottiglia', id=id))

@app.route('/aggiungi_quantita/<id>', methods=['POST'])
@login_required
def aggiungi_bottiglia(id):
    try:
        area = request.form.get('area')
        sotto_area = request.form.get('sotto_area')
        riquadro = request.form.get('riquadro')
        quantita = int(request.form.get('quantita'))

        bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})

        nuove_collocazioni = bottiglia.get('collocazioni', [])
        for collocazione in nuove_collocazioni:
            if collocazione['collocazione_1'] == area and collocazione['collocazione_2'] == sotto_area and collocazione.get('riquadro') == riquadro:
                collocazione['quantita'] += quantita
                break
        else:
            nuove_collocazioni.append({
                'collocazione_1': area,
                'collocazione_2': sotto_area,
                'riquadro': riquadro,
                'quantita': quantita
            })

        bottiglie_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {'collocazioni': nuove_collocazioni, 'quantita_totale': bottiglia['quantita_totale'] + quantita}}
        )

        registra_movimento(
            utente=current_user.username,
            descrizione=bottiglia['descrizione'],
            quantita=quantita,
            collocazione_origine=None,
            collocazione_destinazione=f'{area}/{sotto_area}/{riquadro}',
            tipo_movimento='Aggiunta',
            orario=request.form.get('orario'),
            prodotto_id=id
        )

        flash('Quantità aggiunta con successo!', 'success')
    except Exception as e:
        flash(f'Errore durante l\'aggiunta della quantità: {str(e)}', 'danger')

    return redirect(url_for('scheda_bottiglia', id=id))

# ---------------------------
# Gestione del Magazzino
# ---------------------------

@app.route('/giacenze', methods=['GET'])
@login_required
def giacenze():
    query = {}
    sort_by = request.args.get('sort_by', 'descrizione')
    items_per_page = int(request.args.get('items_per_page', 10))
    current_page = int(request.args.get('page', 1))

    search_descrizione = request.args.get('search_descrizione', '')
    if search_descrizione:
        query['descrizione'] = {'$regex': search_descrizione, '$options': 'i'}

    sort_field, sort_direction = 'descrizione', 1

    total_bottiglie = bottiglie_collection.count_documents(query)
    total_pages = (total_bottiglie + items_per_page - 1) // items_per_page
    bottiglie_data = list(
        bottiglie_collection.find(query)
        .sort(sort_field, sort_direction)
        .skip((current_page - 1) * items_per_page)
        .limit(items_per_page)
    )
    valore_magazzino = sum(float(b.get('prezzo_base', 0)) * int(b.get('quantita_totale', 0)) for b in bottiglie_data)
    return render_template('giacenze.html', bottiglie_info=bottiglie_data, valore_magazzino=valore_magazzino, current_page=current_page, total_pages=total_pages)

@app.route('/prodotti/modificagiacenza/<id>', methods=['GET', 'POST'])
@login_required
def modifica_giacenze(id):
    prodotto = bottiglie_collection.find_one({'_id': ObjectId(id)})

    if request.method == 'POST':
        nuove_collocazioni = []
        quantita_totale = 0

        tipo_movimento = request.form.get('tipo_movimento')
        orario = request.form.get('orario')
        app.logger.debug(f"Tipo movimento: {tipo_movimento}, Orario: {orario}")

        vecchia_collocazione = prodotto.get('collocazioni', [])

        vecchia_mappa = {f"{c['collocazione_1']}/{c['collocazione_2']}": c['quantita'] for c in vecchia_collocazione}
        movimenti_tolti = []
        movimenti_aggiunti = []

        for collocazione_1, collocazione_2, quantita in zip(
            request.form.getlist('collocazione_1[]'), 
            request.form.getlist('collocazione_2[]'), 
            request.form.getlist('quantita[]')):

            if collocazione_1 and collocazione_2:
                quantita = int(quantita)
                chiave = f"{collocazione_1}/{collocazione_2}"

                # Se la chiave esiste nella vecchia mappa, calcoliamo la differenza
                if chiave in vecchia_mappa:
                    differenza = quantita - vecchia_mappa[chiave]
                    if differenza > 0:
                        movimenti_aggiunti.append(f"{chiave} ({differenza})")
                    elif differenza < 0:
                        movimenti_tolti.append(f"{chiave} ({-differenza})")
                    del vecchia_mappa[chiave]
                else:
                    movimenti_aggiunti.append(f"{chiave} ({quantita})")

                # Aggiungi la collocazione alle nuove collocazioni, anche se la quantità è zero
                nuove_collocazioni.append({
                    'collocazione_1': collocazione_1,
                    'collocazione_2': collocazione_2,
                    'quantita': quantita
                })

                # Somma solo le quantità positive per il totale
                quantita_totale += max(quantita, 0)  # Somma anche se zero, per mantenere la collocazione

        # Eventuali collocazioni residue in vecchia_mappa sono state tolte completamente
        for chiave, quantita in vecchia_mappa.items():
            movimenti_tolti.append(f"{chiave} ({quantita})")

        bottiglie_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'collocazioni': nuove_collocazioni,
                'quantita_totale': quantita_totale
            }}
        )

        movimento_descrizione = []
        if movimenti_tolti:
            movimento_descrizione.append(f"Tolte {sum(int(x.split('(')[1].replace(')', '')) for x in movimenti_tolti)} da {', '.join(movimenti_tolti)}")
        if movimenti_aggiunti:
            movimento_descrizione.append(f"Aggiunte {sum(int(x.split('(')[1].replace(')', '')) for x in movimenti_aggiunti)} a {', '.join(movimenti_aggiunti)}")

        if movimento_descrizione:
            registra_movimento(
                utente=current_user.username,
                descrizione=prodotto['descrizione'],
                quantita=quantita_totale,
                collocazione_origine=None if not movimenti_tolti else ', '.join(movimenti_tolti),
                collocazione_destinazione=None if not movimenti_aggiunti else ', '.join(movimenti_aggiunti),
                tipo_movimento=tipo_movimento,
                orario=orario,
                prodotto_id=str(prodotto['_id'])
            )

        flash('Giacenze modificate con successo!', 'success')
        return redirect(url_for('giacenze'))

    return render_template('modifica_giacenze.html', prodotto=prodotto)

@app.route('/assegna_riquadro', methods=['POST'])
@login_required
def assegna_riquadro():
    data = request.get_json()
    bottiglia_id = data['bottiglia_id']
    area = data['area']
    sotto_area = data['sotto_area']
    assegnazioni = data['assegnazioni']

    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(bottiglia_id)})
    if not bottiglia:
        return jsonify({'success': False, 'message': 'Bottiglia non trovata'})

    for assegnazione in assegnazioni:
        riquadro = assegnazione['riquadro']
        quantita = int(assegnazione['quantita'])

        for collocazione in bottiglia['collocazioni']:
            if collocazione['collocazione_1'] == area and collocazione['collocazione_2'] == sotto_area and not collocazione.get('riquadro'):
                collocazione['riquadro'] = riquadro
                collocazione['quantita'] = quantita
                break
        else:
            bottiglia['collocazioni'].append({
                'collocazione_1': area,
                'collocazione_2': sotto_area,
                'riquadro': riquadro,
                'quantita': quantita
            })

    bottiglie_collection.update_one({'_id': ObjectId(bottiglia_id)}, {'$set': {'collocazioni': bottiglia['collocazioni']}})
    return jsonify({'success': True})

# ---------------------------
# Movimenti
# ---------------------------

@app.route('/movimenti')
@login_required
def movimenti():
    movimenti_lista = list(movimenti_collection.find().sort("orario", -1)) 
    for movimento in movimenti_lista:
        movimento['_id'] = str(movimento['_id']) 

    return render_template('movimenti.html', movimenti=movimenti_lista)

# ---------------------------
# Modifica e eliminazione delle bottiglie
# ---------------------------

@app.route('/prodotti')
@login_required
def prodotti():
    bottiglie_info = list(bottiglie_collection.find().sort("descrizione", 1))
    categorie = list(categorie_collection.find().sort("nome", 1))
    reparti = list(reparti_collection.find().sort("nome", 1))
    return render_template('prodotti.html', bottiglie_info=bottiglie_info, categorie=categorie, reparti=reparti)

@app.route('/prodotti/modifica/<id>', methods=['GET', 'POST'])
@login_required
def modifica_configurazione(id):
    prodotto = bottiglie_collection.find_one({'_id': ObjectId(id)})
    
    if request.method == 'POST':
        aggiornamenti = {
            'descrizione': request.form['descrizione'],
            'categoria': request.form['categoria'],
            'reparto': request.form['reparto'],
            'prezzo_base': float(request.form['prezzo_base']),
            'codice_a_barre': request.form['codice_a_barre'], 
        }
        
        if 'costo' in request.form and request.form['costo']:
            aggiornamenti['costo'] = float(request.form['costo'])
        
        if 'riquadro' in request.form and request.form['riquadro']:
            aggiornamenti['riquadro'] = request.form['riquadro']
        
        bottiglie_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': aggiornamenti}
        )
        flash('Prodotto modificato con successo!')
        return redirect(url_for('lista_prodotti'))
    
    categorie = list(categorie_collection.find().sort("nome", 1))
    reparti = list(reparti_collection.find().sort("nome", 1))
    return render_template('modifica_prodotto.html', prodotto=prodotto, categorie=categorie, reparti=reparti)

@app.route('/prodotti/elimina/<id>', methods=['POST', 'GET'])
@login_required
def elimina_configurazione(id):
    bottiglie_collection.delete_one({'_id': ObjectId(id)})
    flash('Prodotto eliminato con successo!')
    return redirect(url_for('lista_prodotti'))

@app.route('/configurazione/elimina_massiva', methods=['POST'])
@login_required
def elimina_massiva_configurazione():
    bottiglia_ids = request.form.getlist('bottiglia_ids')
    for bottiglia_id in bottiglia_ids:
        bottiglie_collection.delete_one({'_id': ObjectId(bottiglia_id)})
    flash(f'{len(bottiglia_ids)} bottiglie eliminate con successo.')
    return redirect(url_for('configurazione'))

# ---------------------------
# Creazione e gestione dei prodotti
# ---------------------------

@app.route('/cerca_bottiglia_ajax', methods=['GET'])
@login_required
def cerca_bottiglia_ajax():
    codici = request.args.get('codici', '')
    if codici:
        codici_lista = codici.split(',')
        risultati = list(bottiglie_collection.find({
            'codice_a_barre': {'$in': codici_lista}
        }))
        return jsonify([{'descrizione': b['descrizione'], 'codice_a_barre': b['codice_a_barre']} for b in risultati])
    return jsonify([])

@app.route('/cerca_bottiglia_ajax_dashboard', methods=['GET'])
@login_required
def cerca_bottiglia_ajax_dashboard():
    query = request.args.get('query', '').strip()
    if query:
        risultati = list(bottiglie_collection.find({
            '$or': [
                {'descrizione': {'$regex': query, '$options': 'i'}},
                {'codice_a_barre': {'$regex': query, '$options': 'i'}}
            ]
        }))
        return jsonify([{'_id': str(b['_id']), 'descrizione': b['descrizione']} for b in risultati])
    return jsonify([])


@app.route('/cerca', methods=['GET'])
@login_required
def cerca_bottiglia():
    query = request.args.get('query')
    if query:
        risultati = list(bottiglie_collection.find({'descrizione': {'$regex': query, '$options': 'i'}}))
        if risultati:
            return render_template('dashboard.html', risultati=risultati, query=query)
        else:
            return render_template('dashboard.html', nessun_risultato=True, query=query)
    return redirect(url_for('dashboard'))

@app.route('/bottiglia/<id>')
@login_required
def scheda_bottiglia(id):
    bottiglia = bottiglie_collection.find_one({'_id': ObjectId(id)})
    if not bottiglia:
        flash('Bottiglia non trovata.')
        return redirect(url_for('dashboard'))

    # Recupera il reparto associato
    reparto = reparti_collection.find_one({'nome': bottiglia['reparto']})

    # Aggiungi il valore del reparto all'oggetto bottiglia, se il reparto esiste
    if reparto:
        bottiglia['reparto_valore'] = reparto.get('valore', 'N/A')

    collocazioni_aggregate = {}
    for collocazione in bottiglia.get('collocazioni', []):
        chiave = f"{collocazione['collocazione_1']}/{collocazione['collocazione_2']}"
        if chiave in collocazioni_aggregate:
            collocazioni_aggregate[chiave] += collocazione['quantita']
        else:
            collocazioni_aggregate[chiave] = collocazione['quantita']

    collocazioni_aggregate_list = [{'collocazione': k, 'quantita': v} for k, v in collocazioni_aggregate.items()]

    return render_template('bottiglia.html', bottiglia=bottiglia)

@app.route('/prodotti')
@login_required
def lista_prodotti():
    bottiglie_info = list(bottiglie_collection.find().sort("descrizione", 1))
    return render_template('prodotti.html', bottiglie_info=bottiglie_info)


import requests
from flask import request, redirect, url_for, flash

@app.route('/crea_prodotto', methods=['GET', 'POST'])
@login_required
def crea_prodotto():
    if request.method == 'POST':
        descrizione = request.form['descrizione']
        prezzo_base = float(request.form['prezzo_base'])
        categoria = request.form['categoria']
        reparto = request.form['reparto']
        
        costo = request.form.get('costo')
        if costo:
            costo = float(costo)
        else:
            costo = 0.0
        
        codice_a_barre = request.form.get('codice_a_barre', '')
        id_interno = request.form.get('id_interno', '')
        
        collocazioni = []
        quantita_totale = 0
        
        collocazione_1_list = request.form.getlist('collocazione_1[]')
        collocazione_2_list = request.form.getlist('collocazione_2[]')
        quantita_list = request.form.getlist('quantita[]')
        
        if collocazione_1_list and collocazione_2_list and quantita_list:
            for collocazione_1, collocazione_2, quantita in zip(collocazione_1_list, collocazione_2_list, quantita_list):
                if collocazione_1 and collocazione_2 and quantita:
                    collocazioni.append({
                        'collocazione_1': collocazione_1,
                        'collocazione_2': collocazione_2,
                        'quantita': int(quantita)
                    })
                    quantita_totale += int(quantita)

        nuovo_prodotto = {
            'descrizione': descrizione,
            'prezzo_base': prezzo_base,
            'costo': costo,
            'categoria': categoria,
            'reparto': reparto,
            'codice_a_barre': codice_a_barre,
            'id_interno': id_interno,
            'quantita_totale': quantita_totale,
            'collocazioni': collocazioni
        }
        
        # Inserisci il prodotto nel database locale
        bottiglie_collection.insert_one(nuovo_prodotto)
        
        # Creazione del prodotto in Cassa in Cloud tramite API
        access_token = 'eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIxMzU3NiIsImlzcyI6Im5pY29sb0BzcGF6aW91YXUuaXQiLCJleHAiOjE3MjUwOTY4NzAsInNjb3BlIjoicmVhZCwgd3JpdGUiLCJhbGxvd0FjY291bnRPcGVyYXRpb24iOmZhbHNlLCJ3ZWJNZW51IjpmYWxzZSwiaWRzU2FsZXNQb2ludCI6IjE1NTU2In0.saVB30afDrij1mh3iYkBOexIcE0ES1fkxCTV6eGgF24vEz6lg4RP86U4uxRBBVqca-3KhWnFxqfDhRSc7t7_Yw'
        api_url = 'https://api.cassanova.com/products'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'X-Version': '1.0.0'
        }

        data = {
            'description': descrizione,
            'descriptionLabel': descrizione,
            'descriptionExtended': descrizione,
            'idDepartment': reparto,
            'idCategory': categoria,
            'prices': [{'idSalesMode': 'default', 'idSalesPoint': 1, 'value': prezzo_base}],
            'barcodes': [{'value': codice_a_barre, 'format': 'EAN13', 'salable': True}]
        }

        # Logging prima della richiesta
        app.logger.debug(f"Request URL: {api_url}")
        app.logger.debug(f"Headers: {headers}")
        app.logger.debug(f"Data: {data}")

        try:
            response = requests.post(api_url, json=data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            app.logger.error(f"HTTP error occurred: {http_err}")
            flash('Errore HTTP durante l\'interazione con Cassa in Cloud.', 'danger')
        except Exception as err:
            app.logger.error(f"Other error occurred: {err}")
            flash('Errore durante l\'interazione con Cassa in Cloud.', 'danger')
        else:
            if response.status_code == 201:
                flash('Prodotto aggiunto con successo anche in Cassa in Cloud!', 'success')
            else:
                flash('Prodotto aggiunto localmente, ma c\'è stato un errore in Cassa in Cloud.', 'danger')
                app.logger.error(f"Errore Cassa in Cloud: {response.status_code} - {response.text}")

        return redirect(url_for('lista_prodotti'))

    categorie = list(categorie_collection.find().sort("nome", 1))
    reparti = list(reparti_collection.find().sort("nome", 1))
    return render_template('prodotti.html', categorie=categorie, reparti=reparti)

@app.route('/reparti', methods=['GET', 'POST'])
@login_required
def reparti():
    if request.method == 'POST':
        nome_reparto = request.form['nome_reparto']
        valore_reparto = request.form.get('valore_reparto', '0')
        
        nuovo_reparto = {
            'nome': nome_reparto,
            'valore': float(valore_reparto) if valore_reparto else 0.0
        }
        reparti_collection.insert_one(nuovo_reparto)
        flash('Reparto aggiunto con successo!')
    
    reparti = list(reparti_collection.find())
    return render_template('reparti.html', reparti=reparti)

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

@app.route('/reparti/elimina/<id>', methods=['GET', 'POST'])
@login_required
def elimina_reparto(id):
    reparto = reparti_collection.find_one({'_id': ObjectId(id)})
    
    if request.method == 'POST':
        reparti_collection.delete_one({'_id': ObjectId(id)})
        flash('Reparto eliminato con successo!', "success")
        return redirect(url_for('reparti'))
    
    return render_template('elimina_reparto.html', reparto=reparto)

# ---------------------------
# Gestione delle categorie
# ---------------------------

@app.route('/categorie', methods=['GET', 'POST'])
@login_required
def categorie():
    if request.method == 'POST':
        nome_categoria = request.form['nome_categoria']
        nuova_categoria = {'nome': nome_categoria}
        categorie_collection.insert_one(nuova_categoria)
        flash('Categoria aggiunta con successo!')
    categorie = list(categorie_collection.find())
    return render_template('categorie.html', categorie=categorie)

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

@app.route('/categorie/elimina/<id>', methods=['POST', 'GET'])
@login_required
def elimina_categoria(id):
    try:
        categorie_collection.delete_one({'_id': ObjectId(id)})
        flash('Categoria eliminata con successo!', 'success')
    except Exception as e:
        flash('Errore nell\'eliminazione della categoria.', 'error')
    return redirect(url_for('categorie'))

# ---------------------------
# Gestione degli attributi
# ---------------------------

@app.route('/attributi', methods=['GET', 'POST'])
@login_required
def attributi():
    if request.method == 'POST':
        nome_attributo = request.form['nome_attributo']
        valore_attributo = request.form.get('valore_attributo', '')

        nuovo_attributo = {
            'nome_attributo': nome_attributo,
            'valore_attributo': valore_attributo
        }

        attributi_collection.insert_one(nuovo_attributo)
        flash('Attributo aggiunto con successo!')

    attributi = list(attributi_collection.find())
    return render_template('attributi.html', attributi=attributi)

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

@app.route('/attributi/elimina/<id>', methods=['GET','POST'])
@login_required
def elimina_attributo(id):
    attributo = attributi_collection.find_one({'_id': ObjectId(id)})
    
    if request.method == 'POST':
        attributi_collection.delete_one({'_id': ObjectId(id)})
        flash('Attributo eliminato con successo!', "success")
        return redirect(url_for('attributi'))
    
    return render_template('elimina_attributo.html', attributo=attributo)

# ---------------------------
# Configurazione del Magazzino
# ---------------------------

@app.route('/salva_codici_a_barre', methods=['POST'])
@login_required
def salva_codici_a_barre():
    area = request.form.get('area')
    sotto_area = request.form.get('sotto_area')
    riquadro = request.form.get('riquadro')
    codici_a_barre = request.form.get('codici_a_barre').splitlines()

    for codice in codici_a_barre:
        codice = codice.strip()
        if not codice:
            continue

        # Cerca la bottiglia nel database
        bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice})
        
        if bottiglia:
            # Aggiungi la bottiglia alla collocazione e riquadro specificato
            nuova_collocazione = {
                'collocazione_1': area,
                'collocazione_2': sotto_area,
                'riquadro': riquadro,
                'quantita': 1  # Aggiungi la quantità desiderata qui
            }

            if 'collocazioni' in bottiglia:
                bottiglia['collocazioni'].append(nuova_collocazione)
            else:
                bottiglia['collocazioni'] = [nuova_collocazione]

            bottiglia['quantita_totale'] = bottiglia.get('quantita_totale', 0) + 1

            # Aggiorna il documento della bottiglia nel database
            bottiglie_collection.update_one(
                {'_id': ObjectId(bottiglia['_id'])},
                {'$set': {
                    'collocazioni': bottiglia['collocazioni'],
                    'quantita_totale': bottiglia['quantita_totale']
                }}
            )
        else:
            flash(f'Bottiglia con codice a barre {codice} non trovata.', 'danger')

    flash('Codici a barre salvati con successo!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/configura_riquadro/<area>/<sotto_area>/<riquadro>', methods=['GET', 'POST'])
@login_required
def configura_riquadro(area, sotto_area, riquadro):
    if request.method == 'POST':
        # Ottieni i codici a barre dal textarea
        codici_a_barre = request.form.get('codici_a_barre_textarea').splitlines()

        # Processa ciascun codice a barre
        for codice in codici_a_barre:
            codice = codice.strip()
            if not codice:
                continue

            # Cerca la bottiglia nel database utilizzando il codice a barre
            bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice})

            if bottiglia:
                # Verifica se la collocazione esiste già
                collocazione_trovata = False
                for collocazione in bottiglia.get('collocazioni', []):
                    if (collocazione['collocazione_1'] == area and
                        collocazione['collocazione_2'] == sotto_area and
                        collocazione['riquadro'] == riquadro):
                        # Incrementa la quantità della bottiglia nella collocazione esistente
                        collocazione['quantita'] += 1
                        collocazione_trovata = True
                        break

                if not collocazione_trovata:
                    # Se la collocazione non esiste, aggiungila
                    nuova_collocazione = {
                        'collocazione_1': area,
                        'collocazione_2': sotto_area,
                        'riquadro': riquadro,
                        'quantita': 1
                    }
                    bottiglia['collocazioni'].append(nuova_collocazione)

                # Aggiorna la quantità totale della bottiglia
                bottiglia['quantita_totale'] = bottiglia.get('quantita_totale', 0) + 1

                # Aggiorna il documento della bottiglia nel database
                bottiglie_collection.update_one(
                    {'_id': bottiglia['_id']},
                    {'$set': {
                        'collocazioni': bottiglia['collocazioni'],
                        'quantita_totale': bottiglia['quantita_totale']
                    }}
                )

                # Registra il movimento
                registra_movimento(
                    utente=current_user.username,
                    descrizione=bottiglia['descrizione'],
                    quantita=1,  # Poiché si sta inserendo una bottiglia alla volta
                    collocazione_origine=None,
                    collocazione_destinazione=f'{area}/{sotto_area}/{riquadro}',
                    tipo_movimento='Configurazione Riquadro',
                    orario=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    prodotto_id=str(bottiglia['_id'])
                )
            else:
                flash(f'Bottiglia con codice a barre {codice} non trovata.', 'danger')

        flash('Configurazione del riquadro completata con successo!', 'success')
        return redirect(url_for('dashboard'))

    # Renderizza il template per inserire i codici a barre
    return render_template('configura_riquadro.html', area=area, sotto_area=sotto_area, riquadro=riquadro)

@app.route('/bottiglie_da_posizionare', methods=['GET'])
@login_required
def bottiglie_da_posizionare():
    area = request.args.get('area')
    sotto_area = request.args.get('sotto_area')

    bottiglie_da_posizionare = list(bottiglie_collection.find({
        'collocazioni.collocazione_1': area,
        'collocazioni.collocazione_2': sotto_area,
        'collocazioni.riquadro': None
    }))

    totale_bottiglie = sum(int(collocazione['quantita']) 
                           for bottiglia in bottiglie_da_posizionare 
                           for collocazione in bottiglia['collocazioni'] 
                           if collocazione['riquadro'] is None)

    return render_template('bottiglie_da_posizionare.html', 
                           area=area, 
                           sotto_area=sotto_area, 
                           bottiglie=bottiglie_da_posizionare, 
                           totale_bottiglie=totale_bottiglie)


@app.route('/posiziona_bottiglie', methods=['POST'])
@login_required
def posiziona_bottiglie():
    area = request.form.get('area')
    sotto_area = request.form.get('sotto_area')
    riquadro = request.form.get('riquadro')

    bottiglie_da_posizionare = list(bottiglie_collection.find({
        'collocazioni.collocazione_1': area,
        'collocazioni.collocazione_2': sotto_area,
        'collocazioni.riquadro': None
    }))

    for bottiglia in bottiglie_da_posizionare:
        for collocazione in bottiglia['collocazioni']:
            if collocazione['riquadro'] is None:
                collocazione['riquadro'] = riquadro

        bottiglie_collection.update_one(
            {'_id': bottiglia['_id']},
            {'$set': {'collocazioni': bottiglia['collocazioni']}}
        )

    flash('Le bottiglie sono state posizionate con successo nel riquadro selezionato!')
    return redirect(url_for('dashboard'))

@app.route('/aggiorna_riquadro', methods=['GET'])
@login_required
def aggiorna_riquadro():
    bottiglie_collection.update_many(
        {'collocazioni.riquadro': {'$exists': False}},
        {'$set': {'collocazioni.$[].riquadro': 'N/A'}}
    )
    flash('Tutte le bottiglie senza riquadro sono state aggiornate.')
    return redirect(url_for('dashboard'))

@app.route('/ricerca_riquadri', methods=['GET', 'POST'])
@login_required
def ricerca_riquadri():
    if request.method == 'POST':
        area = request.form.get('area')
        sotto_area = request.form.get('sotto_area')

        if area == "Sala Principale" and sotto_area == "Frighi":
            riquadri_disponibili = ['Frigo Sx', 'Frigo Dx']
        else:
            riquadri_disponibili = visione_riquadri(area, sotto_area)

        if riquadri_disponibili:
            return render_template('visione_riquadri.html', riquadri_disponibili=riquadri_disponibili, area=area, sotto_area=sotto_area)
        else:
            flash('Non ci sono riquadri disponibili per l\'area e la sotto-area selezionata.', 'warning')
            return redirect(url_for('dashboard'))
    
    return render_template('seleziona_area_sotto_area.html')

@app.route('/visualizza_riquadro', methods=['GET'])
@login_required
def visualizza_riquadro():
    area = request.args.get('area')
    sotto_area = request.args.get('sotto_area')
    riquadro = request.args.get('riquadro')

    bottiglie_posizionate = list(bottiglie_collection.find({
        'collocazioni.collocazione_1': area,
        'collocazioni.collocazione_2': sotto_area,
        'collocazioni.riquadro': riquadro
    }))

    valore_totale_riquadro = 0
    totale_quantita = 0

    bottiglie_dettagli = []

    for bottiglia in bottiglie_posizionate:
        for collocazione in bottiglia['collocazioni']:
            if (collocazione.get('collocazione_1') == area and 
                collocazione.get('collocazione_2') == sotto_area and 
                collocazione.get('riquadro') == riquadro):
                
                valore_totale_riquadro += float(bottiglia['prezzo_base']) * int(collocazione['quantita'])
                totale_quantita += int(collocazione['quantita'])

                bottiglie_dettagli.append({
                    'descrizione': bottiglia['descrizione'],
                    'quantita': collocazione['quantita'],
                    'categoria': bottiglia.get('categoria', 'N/A'), 
                    'prezzo_base': bottiglia['prezzo_base']
                })

    return render_template('visualizza_riquadro.html', 
                           area=area, 
                           sotto_area=sotto_area, 
                           riquadro=riquadro, 
                           bottiglie=bottiglie_dettagli,  
                           valore_totale_riquadro=valore_totale_riquadro,
                           totale_quantita=totale_quantita)

def visione_riquadri(area, sotto_area, frigo=None):
    riquadri_disponibili = []

    if area == "Sala Principale" and sotto_area == "Scaffali":
        riquadri_disponibili.extend([f"A{number}" for number in range(1, 6)])
        riquadri_disponibili.extend([f"B{number}" for number in range(1, 6)])
        riquadri_disponibili.extend([f"{letter}{number}" for letter in "CDEFG" for number in range(1, 4)])
        riquadri_disponibili.extend([f"H{number}" for number in range(1, 6)])
        riquadri_disponibili.extend([f"I{number}" for number in range(1, 6)])
    elif area == "Sala Principale" and sotto_area == "Frighi":
        if frigo == "Frigo Sx":
            riquadri_disponibili.extend([f"{i}º Alto" for i in range(1, 5)])
        elif frigo == "Frigo Dx":
            riquadri_disponibili.extend([f"{i}º Alto" for i in range(1, 4)])
    elif area == "Sala Secondaria" and sotto_area == "Scaffali":
        riquadri_disponibili.extend([f"A{number}" for number in range(1, 7)])
        riquadri_disponibili.extend([f"B{number}" for number in range(1, 7)])
    elif area == "Soppalco" and sotto_area == "Scaffali":
        riquadri_disponibili.extend(["A", "B", "C", "D"])
    elif area == "Sala Principale" and sotto_area == "Frighetto":
        riquadri_disponibili.append("Unico")
    elif area == "Soppalco" and sotto_area == "Chiuso":
        riquadri_disponibili.append("Unico")

    return riquadri_disponibili

@app.route('/assegna_bottiglia_ajax')
@login_required
def assegna_bottiglia_ajax():
    codice_a_barre = request.args.get('codice_a_barre', '').strip()
    print(f"Codice a barre ricevuto: {codice_a_barre}")
    if codice_a_barre:
        bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice_a_barre})
        if bottiglia:
            print(f"Bottiglia trovata: {bottiglia.get('nome')}")
            return jsonify({'Descrizione': bottiglia.get('nome')})
    print("Bottiglia non trovata o codice a barre mancante")
    return jsonify({'Descrizione': None})

@app.route('/aggiungi_bottiglie_riquadro', methods=['POST'])
@login_required
def aggiungi_bottiglie_riquadro():
    riquadro = request.form.get('riquadro').strip()
    codici_a_barre = request.form.get('codici_a_barre_textarea').splitlines()

    for codice in codici_a_barre:
        codice = codice.strip()
        if not codice:
            continue

        bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice})
        
        if bottiglia:
            nuova_collocazione = {
                'collocazione_1': 'Sala Principale',  
                'collocazione_2': 'Scaffali',  
                'riquadro': riquadro,  
                'quantita': 1  
            }

            if 'collocazioni' in bottiglia:
                bottiglia['collocazioni'].append(nuova_collocazione)
            else:
                bottiglia['collocazioni'] = [nuova_collocazione]

            bottiglia['quantita_totale'] = bottiglia.get('quantita_totale', 0) + 1

            bottiglie_collection.update_one(
                {'_id': bottiglia['_id']},
                {'$set': {
                    'collocazioni': bottiglia['collocazioni'],
                    'quantita_totale': bottiglia['quantita_totale']
                }}
            )
        else:
            flash(f'Bottiglia con codice a barre {codice} non trovata.', 'danger')

    flash('Configurazione salvata con successo!', 'success')
    return redirect(url_for('dashboard'))

# ---------------------------
# Visione del Magazzino
# ---------------------------

@app.route('/visione_magazzino', methods=['GET', 'POST'])
@login_required
def visione_magazzino():
    if request.method == 'POST':
        area = request.form.get('area')
        sotto_area = request.form.get('sotto_area')

        if area == "Sala Principale" and sotto_area == "Frighi":
            riquadri_disponibili = ['Frigo Sx', 'Frigo Dx']
        else:
            riquadri_disponibili = visione_riquadri(area, sotto_area)

        if riquadri_disponibili:
            return render_template('visione_magazzino.html', riquadri_disponibili=riquadri_disponibili, area=area, sotto_area=sotto_area)
        else:
            flash('Non ci sono riquadri disponibili per l\'area e la sotto-area selezionata.', 'warning')
            return redirect(url_for('visione_magazzino'))
    
    return render_template('seleziona_area_sotto_area_magazzino.html')

@app.route('/configura_bottiglia', methods=['POST'])
@login_required
def configura_bottiglia():
    area = request.form.get('area')
    sotto_area = request.form.get('sotto_area')
    codici_a_barre = request.form.get('codici_a_barre_textarea').splitlines()

    for codice in codici_a_barre:
        codice = codice.strip()
        if not codice:
            continue

        bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice})

        if bottiglia:
            nuova_collocazione = {
                'collocazione_1': area,
                'collocazione_2': sotto_area,
                'riquadro': None,
                'quantita': 1
            }

            if 'collocazioni' in bottiglia:
                bottiglia['collocazioni'].append(nuova_collocazione)
            else:
                bottiglia['collocazioni'] = [nuova_collocazione]

            bottiglia['quantita_totale'] = bottiglia.get('quantita_totale', 0) + 1

            bottiglie_collection.update_one(
                {'_id': bottiglia['_id']},
                {'$set': {
                    'collocazioni': bottiglia['collocazioni'],
                    'quantita_totale': bottiglia['quantita_totale']
                }}
            )
        else:
            flash(f'Bottiglia con codice a barre {codice} non trovata.', 'danger')

    flash('Configurazione bottiglia completata con successo!')
    return redirect(url_for('dashboard'))

@app.route('/magazzino/inserisci_bottiglia_riquadro', methods=['GET', 'POST'])
@login_required
def inserisci_bottiglia_riquadro():
    area = request.args.get('area')
    sotto_area = request.args.get('sotto_area')
    riquadro = request.args.get('riquadro')

    app.logger.debug(f"Ricevuto codice a barre: {codice_a_barre}, quantità: {quantita}, area: {area}, sotto_area: {sotto_area}, riquadro: {riquadro}")

    if request.method == 'POST':
        codici_a_barre = request.form.get('codici_a_barre').splitlines()

        for codice_a_barre in codici_a_barre:
            bottiglia = bottiglie_collection.find_one({'codice_a_barre': codice_a_barre.strip()})

            if bottiglia:
                for collocazione in bottiglia.get('collocazioni', []):
                    if (collocazione['collocazione_1'] == area and
                        collocazione['collocazione_2'] == sotto_area and
                        collocazione['riquadro'] == riquadro):
                        collocazione['quantita'] += 1
                        break
                else:
                    bottiglia['collocazioni'].append({
                        'collocazione_1': area,
                        'collocazione_2': sotto_area,
                        'riquadro': riquadro,
                        'quantita': 1
                    })

                bottiglie_collection.update_one(
                    {'_id': ObjectId(bottiglia['_id'])},
                    {'$set': {
                        'collocazioni': bottiglia['collocazioni'],
                        'quantita_totale': bottiglia['quantita_totale'] + 1
                    }}
                )
            else:
                flash(f'Errore: Bottiglia con codice a barre {codice_a_barre.strip()} non trovata.')

        flash('Bottiglie aggiunte al riquadro con successo!')
        return redirect(url_for('visione_magazzino', area=area, sotto_area=sotto_area))

    return render_template('inserisci_bottiglia_riquadro.html', area=area, sotto_area=sotto_area, riquadro=riquadro)

# ---------------------------
# Gestione dell'account
# ---------------------------

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

if __name__ == "__main__":
    app.run(debug=True)
