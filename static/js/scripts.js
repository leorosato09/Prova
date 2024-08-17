function updateSearchCollocazione2() {
    var collocazione1 = document.getElementById('search_collocazione_1').value;
    var collocazione2 = document.getElementById('search_collocazione_2');

    // Resetta le opzioni di "Collocazione 2"
    collocazione2.innerHTML = '';

    // Aggiungi l'opzione predefinita
    var defaultOption = new Option('Tutte', '');
    collocazione2.add(defaultOption);

    // Aggiungi opzioni basate sulla selezione di "Collocazione 1"
    if (collocazione1 === 'Sala Principale') {
        collocazione2.add(new Option('Frigo', 'Frigo'));
        collocazione2.add(new Option('Scaffali', 'Scaffali'));
    } else if (collocazione1 === 'Sala Secondaria' || collocazione1 === 'Soppalco') {
        collocazione2.add(new Option('Scaffali', 'Scaffali'));
    }
    
    // Mantieni la selezione precedente se ancora valida
    var selectedValue = collocazione2.getAttribute('data-selected');
    if (selectedValue) {
        for (var i = 0; i < collocazione2.options.length; i++) {
            if (collocazione2.options[i].value === selectedValue) {
                collocazione2.selectedIndex = i;
                break;
            }
        }
    }
}

// Inizializza il menù a discesa della ricerca quando la pagina viene caricata
window.onload = function() {
    updateSearchCollocazione2();
};
