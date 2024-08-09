from flask import Flask, request, render_template_string

app = Flask(__name__)

# Route principale per chiedere il nome
@app.route('/', methods=['GET', 'POST'])
def chiedi_nome():
    if request.method == 'POST':
        nome = request.form['nome']
        return f'Ciao, {nome}!'
    return '''
        <form method="post">
            Inserisci il tuo nome qui: <input type="text" name="nome">
            <input type="submit" value="Invia">
        </form>
    '''

# Route per pulire la cache (esempio semplice)
@app.route('/clear-cache')
def clear_cache():
    # Qui puoi inserire la logica per pulire la cache della tua applicazione
    # Se usi Flask-Caching, potresti chiamare cache.clear(), ma in questo esempio semplice, stamperemo solo un messaggio
    # Se hai una cache personalizzata, inserisci qui il codice per pulirla
    print("Cache cleared!")  # Messaggio di debug
    return "Cache cleared!"

if __name__ == '__main__':
    app.run(debug=True)
