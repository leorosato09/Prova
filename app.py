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

if __name__ == '__main__':
    app.run(debug=True)
