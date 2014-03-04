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
            if (v == "0") { v = "Non"; } else if (v == "1") { v = "Oui"; } else { v = "?"; }
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
 * Convertir un dictionnaire en tableau complet
 * cell: le tableau visé, dict: toutes les donnees, donnee: la clé de dict voulue
 */
function dict_to_tab(cell, dict, donnee) {
    // Pour l'en-tête
    cell.find('thead').remove();
    var thead = $('<thead>').appendTo(cell);
    thead.append('<th>'+donnee+'</th>');
    $.each( dict['ordre'][donnee], function( key, value ) {
        thead.append('<th>'+value+'</th>');
    });
    // Pour les données
    cell.find('tbody').remove();
    var tbody = $('<tbody>').appendTo(cell);
    $.each( dict[donnee], function( key, value ) {
        vals = "<td>"+key+"</td>";
        $.each( dict['ordre'][donnee], function( i, j ) {
            vals += "<td>"+value[j]+"</td>";
        });
        tbody.append('<tr>'+vals+'</tr>');
    });
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
    var $rows = $table.find('tr:visible:has(td,th):not(".tablesorter-filter-row"):not(".removeme")'),

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

/*
 * Donne les coordonnées de la cellule dans son tableau
 */
function coordonnees(cell) {
    x = cell.cellIndex;
    y = cell.parentNode.rowIndex;
    return {'x':x, 'y':y};
}

/*
 * Mailer toutes les personnes affichée
 */
function mailer_tous() {
    index = $.inArray('Mail', champs_vue) + 1;
    col_mail = $("#vue > tbody").find('td:visible:nth-child('+index+')');
    mailto = new Array();
    $.each(col_mail, function(i,j){
        val = $(j).html();
        if (val) {
            mailto.push($(val).attr('href').split(':')[1]);
        }
    });
    window.location.href = "mailto:"+mailto.join(' ,');
    // À tester : l'utilisation du , pour de multiples destinataires n'est pas standard
    // http://www.sightspecific.com/~mosh/www_faq/multrec.html
    // Une autre solution serait d'envoyer ça au serveur python
}

/*
 * Ajoute une liste de choix à un element
 */
function cell_to_select(e) {
    cell = $(e.target);
    c = coordonnees(e.target);
    s = cell.find('select');
    // S'il n'y a pas encore de select et si le click vient d'une cellule
    if (s.length == 0 && c['x']) {
        valeurs = null;
        col = cell.parentsUntil('table').parent().find("th:nth-child("+(c['x']+1)+") div").html();
        if (col == "Niveau") { valeurs = niveaux; }
        else if (col == "Filière") { valeurs = filières; }
        else if (col == "Section") { valeurs = sections; }
        else if (col == "Situation") { valeurs = situations; }
        if (valeurs != null) {
            selected = cell.html();
            cell.html('');
            var sel = $('<select>').appendTo(cell);
            sel.append('<option value="?">...</option>'); // Option vide
            $.each(valeurs, function(i, j) {
                pardefaut = "";
                if (j == selected) { pardefaut = ' selected="selected"' ; }
                sel.append('<option value="'+j+'"'+pardefaut+'>'+j+'</option>');
            });
            sel.change( function(){
                // Au changement de valeur, on l'enregistre dans la base
                val = $(this).val();
                if (col == "Situation") {
                    ine = cell.parentsUntil('table').find('tr').attr('id');
                    params = "ine="+ine+"&champ="+col+"&d="+val;
                    url = "/maj?"+params;
                } else {
                    row = cell.parents('tr').find('td').first().html();
                    params = "classe="+row+"&val="+val+"&champ="+col;
                    url = "/maj_classe?"+params;
                }
                $.get( url, function( data ) {
                    c = cell.parents('td');
                    if (data == 'Oui') { c.addClass("maj_oui"); }
                    else if (data == 'Non') { c.addClass("maj_non"); }
                    c.html(val); // Et on retire le select
                });
            });
        }
    }
}
 
