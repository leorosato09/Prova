from flask import Flask, request, render_template_string

app = Flask(__name__)

# Route principale per chiedere nome, cognome e data di nascita
@app.route('/', methods=['GET', 'POST'])
def chiedi_dati():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cognome = request.form.get('cognome')
        data_nascita = request.form.get('data_nascita')
        if nome and cognome and data_nascita:
            return render_template_string('''
                <!DOCTYPE html>
                <html lang="it">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Risultato</title>
                </head>
                <body>
                    <p>Ciao, {{ nome }} {{ cognome }}!</p>
                    <p>Sei nato/a il {{ data_nascita }}.</p>
                    <p>L'operazione è andata a buon fine</p> <!-- Messaggio di successo -->
                </body>
                </html>
            ''', nome=nome, cognome=cognome, data_nascita=data_nascita)

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Chiedi Dati</title>
            <style>
                .error { border: 2px solid red; } /* Stile per casella di input rossa */
            </style>
            <script>
                function validateForm() {
                    var nome = document.getElementById('nome').value;
                    var cognome = document.getElementById('cognome').value;
                    var dataNascita = document.getElementById('data_nascita').value;
                    var valid = true;

                    if (nome == "") {
                        document.getElementById('nome').classList.add('error');
                        valid = false;
                    }
                    if (cognome == "") {
                        document.getElementById('cognome').classList.add('error');
                        valid = false;
                    }
                    if (dataNascita == "") {
                        document.getElementById('data_nascita').classList.add('error');
                        valid = false;
                    }

                    if (!valid) {
                        document.getElementById('error-message').innerText = "Per favore inserisci tutti i dati richiesti.";
                    }

                    return valid;
                }
            </script>
        </head>
        <body>
            <form method="post" onsubmit="return validateForm()">
                <label for="nome">Nome:</label>
                <input type="text" id="nome" name="nome"><br><br>

                <label for="cognome">Cognome:</label>
                <input type="text" id="cognome" name="cognome"><br><br>

                <label for="data_nascita">Data di nascita:</label>
                <input type="date" id="data_nascita" name="data_nascita"><br><br>

                <input type="submit" value="Invia">
            </form>
            <p id="error-message" style="color:red;"></p> <!-- Messaggio di errore -->
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
