from flask import Flask, request, render_template_string

app = Flask(__name__)

# Route principale per chiedere il nome
@app.route('/', methods=['GET', 'POST'])
def chiedi_nome():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome:
            return f'Ciao, {nome}!'
        else:
            return 'Nome non inserito!', 400  # Restituisce un errore 400 se il nome non è fornito
    return '''
        <form method="post">
            Inserisci il tuo nome qui: <input type="text" name="nome">
            <input type="submit" value="Invia">
        </form>
    '''

# Route per la pulizia della cache
@app.route('/clear-cache')
def clear_cache():
    print("Cache cleared!")  # Messaggio di debug o logica di pulizia cache
    return "Cache cleared!"

if __name__ == '__main__':
    app.run(debug=True)
