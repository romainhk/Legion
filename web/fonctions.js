/*
 * Ici : les fonctions stables et peu interactives
 */

/* Placeholder */
function nyi(message) { alert ('Not yet implemented :)\n'+message); }

/* 
 * Importation
 */
function importation() {
    // Lecture du fichier à importer
    var file = document.getElementById('fichier').files[0];
    if (file == undefined) {
        alert("Veuillez selectionner un fichier pour lancer l'importation.");
        return false;
    }
    var reader = new FileReader();
    $("#progress").show();
    reader.readAsText(file, 'ISO-8859-15');
    reader.onload = envoie_du_fichier;
}
function envoie_du_fichier(event) {
    // Envoie du fichier au serveur
    var result = event.target.result;
    var fileName = document.getElementById('fichier').files[0].name;
    $.post('/importation', { data: result, name: fileName }, function(reponse) {
        $("#progress").hide();
        $( "#onglets li:first-child" ).trigger( "click" );
        stats_annees(); // Une nouvelle année est peut-être disponible...
    });
}

/*
 * Mise à jour d'un des champs autorisé
 */
function maj_cellule(cell) {
    var val = cell.text();
    var ine = cell.parent().attr('id');
    index_x = cell.parent().children().index(cell);
    var champ = champs_vue[index_x];
    params = "ine="+ine+"&champ="+champ+"&d="+val;
    $.get( "/maj?"+params, function( data ) {
        if (data == 'Oui') { cell.addClass("maj_oui"); }
        else if (data == 'Non') { cell.addClass("maj_non"); }
    });
}

/*
 * Traduction des données de la base en quelque chose de plus lisible
 */
function trad_db_val(v, j) {
    if(v != undefined){
        if (j == "Classe") { // Traduction des doublements
            v = v.replace(/([^, ]+)\*/g, '<span class="doublement">$1</span>');
        } else if (j == "Genre") { // Traduction de la colonne genre
            if (v == "1") { v = "Homme"; } else if (v == "2") { v = "Femme"; }
        } else if (j == "Mail") { // Mise en page des mails
            if (v != "") { v = '<a href="mailto:'+v+'">@</a>'; }
        } else if (j == "Doublement") { // Traduction de la colonne doublement
            if (v == "0") { v = "Non"; } else { v = "Oui"; }
        }
    } else { v= ''; }
    return v;
}

/* 
 * Convertir une liste en lignes de tableau (tr)
 */
function list_to_tab(liste, champs) {
    var lignes = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        ine = value['INE'];
        $.each( champs, function( i, j ) {
            v = trad_db_val(value[j], j);
            vals += "<td>"+v+"</td>";
        });
        lignes += "<tr id='"+ine+"'>"+vals+"</tr>\n";
    });
    return(lignes);
}

/*
 * Renvoie la liste triée inversée des clés du dictionnaire donné
 */
function reverse_key_sort(dict){
    var keys = new Array();
    for (k in dict) {
        if (dict.hasOwnProperty(k)) {
            keys.push(k);
        }
    }
    return keys.sort().reverse();
}

/*
 * Conversion d'un tableau html en fichier CSV
 * FROM http://jsfiddle.net/terryyounghk/KPEGU/
 */
function exportTableToCSV($table, filename) {
    var $rows = $table.find('tr:visible:has(td,th):not(".tablesorter-filter-row"):not(".remove-me")'),

    // Temporary delimiter characters unlikely to be typed by keyboard
    // This is to avoid accidentally splitting the actual contents
    tmpColDelim = String.fromCharCode(11), // vertical tab character
    tmpRowDelim = String.fromCharCode(0), // null character

    // actual delimiter characters for CSV format
    colDelim = '","',
    rowDelim = '"\r\n"',

    // Grab text from table into CSV formatted string
    csv = '"' + $rows.map(function (i, row) {
        var $row = $(row),
            $cols = $row.find('th,td');

        return $cols.map(function (j, col) {
            var $col = $(col),
                text = $col.text();
            // On remplace les colspan vides par autant de td
            var colspan = $col.attr('colspan');
            if (colspan != undefined) {
                var t = new Array();
                for (var m=0; m < colspan; m++) { t.push(''); }
                return t;
            }
            // Cas de la colonne mail
            if (text == "@") { return $col.find('a').attr('href').replace('mailto:',''); }

            return text.replace('"', '""'); // escape double quotes
        }).get().join(tmpColDelim);

    }).get().join(tmpRowDelim)
        .split(tmpRowDelim).join(rowDelim)
        .split(tmpColDelim).join(colDelim) + '"',

    // Data URI
    csvData = 'data:application/csv;charset=utf-8,' + encodeURIComponent(csv);
    $(this).attr({
        'download': filename,
        'href': csvData,
        'target': '_blank'
    });
}

