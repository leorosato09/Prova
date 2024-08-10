from flask import Flask, request, render_template_string

app = Flask(__name__)

# Route principale per chiedere il nome
@app.route('/', methods=['GET', 'POST'])
def chiedi_nome():
    if request.method == 'POST':
        nome = request.form.get('nome')
        if nome:
            return render_template_string('''
                <!DOCTYPE html>
                <html lang="it">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Risultato</title>
                </head>
                <body>
                    <p>Ciao, {{ nome }}!</p>
                    <p>L'operazione è andata a buon fine</p> <!-- Messaggio di successo -->
                </body>
                </html>
            ''', nome=nome)

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Chiedi Nome</title>
            <style>
                .error { border: 2px solid red; } /* Stile per casella di input rossa */
            </style>
            <script>
                function validateForm() {
                    var nome = document.getElementById('nome').value;
                    if (nome == "") {
                        document.getElementById('nome').classList.add('error');
                        document.getElementById('error-message').innerText = "Per favore inserisci un nome.";
                        return false;
                    }
                    return true;
                }
            </script>
        </head>
        <body>
            <form method="post" onsubmit="return validateForm()">
                <label for="nome">Inserisci il tuo nome qui:</label>
                <input type="text" id="nome" name="nome">
                <input type="submit" value="Invia">
            </form>
            <p id="error-message" style="color:red;"></p> <!-- Messaggio di errore -->
            <p>Buongiorno, la vita è bella!</p> <!-- Messaggio fisso sotto l'input -->
        </body>
        </html>
    ''')

# Route per la pulizia della cache
@app.route('/clear-cache')
def clear_cache():
    print("Cache cleared!")  # Messaggio di debug o logica di pulizia cache
    return "Cache cleared!"

if __name__ == '__main__':
    app.run(debug=True)
