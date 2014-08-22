/*
 * Ici : les fonctions stables et peu interactives
 */

/*
 * Donne les coordonnées de la cellule dans son tableau
 */
function coordonnees(cell) {
    x = cell.cellIndex;
    y = cell.parentNode.rowIndex;
    return {'x':x, 'y':y};
}

/*
 * Renvoie la liste triée inversée des clés du dictionnaire donné
 * - le booléen reversed permet de renverser le tri
 */
function dict_key_sort(dict, reversered){
    var keys = new Array();
    for (k in dict) {
        if (dict.hasOwnProperty(k)) {
            keys.push(k);
        }
    }
    if (reversered) {
        return keys.sort().reverse();
    } else {
        return keys.sort();
    }
}

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
        // Mise à jour générale
        location.reload(true);
    });
}

/*
 * Recherche dans les statistiques
 */
function stats_recherche() {
    var stat = $('#stats-liste option:selected').text();
    var annee = $('#stats-annee option:selected').text();
    var niveaux = [];
    $('#stats-options td input:checked').each(function(i, j) {
        niveaux.push($(j).val());
    }); // S'il te plaît, n'ajoute pas d'autres checkbox à stats-options
    params = "stat="+stat+"&annee="+annee+"&niveaux="+niveaux;
    // On masque la recherche précédente
    $.each(les_stats, function( i, p ) {
        $("#stats-"+p.replace(/ |\(|\)/g, '')).hide();
    });
    $.get( "/stats?"+params, function( data ) {
        if (stat == "Général") {
            var id = "#stats-Général";
            $(id+' tbody').html('');
            cles = dict_key_sort(data['data'], false);
            $.each(cles, function(i,k) {
                l = data['data'][k];
                $(id+' tbody').append('<tr><td>'+k+'</td><td>'+l+'</td></tr>');
            });
        } else if (stat == "Par niveau") {
            var id = "#stats-Parniveau";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Par section") {
            var id = "#stats-Parsection";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Provenance") {
            var id = "#stats-Provenance";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Provenance (classe)") {
            var id = "#stats-Provenanceclasse";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Taux de passage") {
            var id = "#stats-Tauxdepassage";
            list_to_tab($(id+' table'), data);
        } else if (stat == "EPS (activite)") {
            var id = "#stats-EPSactivite";
            list_to_tab($(id+' table'), data);
        } else {
            console.log("Stat inconnue");
        }
        $(id).show();
        $(id+' .graph').html('');
        $.each(data['graph'], function(i, g) {
            $(id+' .graph').append('<img src="'+g+'" />');
        });
    });
}

/*
 * Mise à jour d'un des champs autorisés
 */
function maj_cellule(event) {
    // http://css-tricks.com/snippets/javascript/saving-contenteditable-content-changes-as-json-with-ajax/
    var esc = event.which == 27,
        nl = event.which == 13,
        el = event.target,
        input = el.nodeName != 'INPUT' && el.nodeName != 'TEXTAREA',
        data = {};
    if (input) {
        if (esc) { // Annulation
            document.execCommand('undo');
            el.blur();
        } else if (nl) {
            data[el.getAttribute('data-name')] = el.innerHTML;
            cell = $(el);
            var val = cell.text();
            var ine = cell.parent().attr('id');
            if (page_active == 'eps') {
                var champ = $('#eps-table').find('th').eq(cell.index()).html();
            } else {
                var champ = champs_liste[cell.index()];
            }
            params = "ine="+ine+"&champ="+champ+"&d="+val;
            $.get( "/maj?"+params, function( data ) {
                if (data == 'Oui') { cell.addClass("maj_oui"); }
                else if (data == 'Non') { cell.addClass("maj_non"); }
            });
            el.blur();
            event.preventDefault();
        }
    }
}

/* 
 * Convertir une liste en lignes de tableau (tr)
 */
function list_to_tab_simple(liste, champs) {
    var lignes = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        ine = value['INE'];
        $.each( champs, function( i, j ) {
            v = value[j];
            if(v != undefined){
                if (j == "Genre") { // Traduction de la colonne genre
                    if (v == "1") { v = "Homme"; } else if (v == "2") { v = "Femme"; }
                } else if (j == "Doublement") { // Traduction de la colonne doublement
                    if (v == "0") { v = "Non"; } else if (v == "1") { v = "Oui"; } else { v = "?"; }
                }
            } else { v= ''; }
            vals += "<td>"+v+"</td>";
        });
        lignes += "<tr id='"+ine+"'>"+vals+"</tr>\n";
    });
    return(lignes);
}

/* 
 * Convertir une liste en tableau complet
 * cell: le tableau visé, list: toutes les donnees, donnee: id de la donnée voulue
 */
function list_to_tab(cell, list) {
    // Pour l'en-tête
    cell.find('thead').remove();
    var thead = $('<thead>').appendTo(cell);
    var entete = $('<tr>').appendTo(thead);
    $.each( list['ordre'], function( key, value ) {
        entete.append('<th data-sort="'+value[1]+'">'+value[0]+'</th>');
    });
    // Pour les données
    cell.find('tbody').remove();
    var tbody = $('<tbody>').appendTo(cell);
    $.each( list['data'], function( key, value ) {
        vals = "";
        $.each( list['ordre'], function( i, j ) {
            vals += "<td>"+value[j[0]]+"</td>";
        });
        tbody.append('<tr>'+vals+'</tr>');
    });
}


/*
 * Conversion d'un tableau html en fichier CSV
 * FROM http://jsfiddle.net/terryyounghk/KPEGU/
 */
function exportTableToCSV($table, filename) {
    var $rows = $table.find('tr:visible:has(td,th):not(".removeme")'),

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
 * Mailer toutes les personnes affichée
 */
function mailer_tous() {
    index = $.inArray('Mail', champs_liste) + 1;
    col_mail = $("#liste-table > tbody").children('tr').children('td:nth-child('+index+')');
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
        col = cell.parentsUntil('table').parent().find("th:nth-child("+(c['x']+1)+")").html();
        if (col == "Niveau") { valeurs = niveaux; }
        else if (col == "Filière") { valeurs = filières; }
        else if (col == "Section") { valeurs = sections; }
        else if (col == "Situation") { valeurs = situations; }
        else if (col == "Activité 1" || col == "Activité 2" || col == "Activité 3" || col == "Activité 4" || col == "Activité 5") { valeurs = activités; }
        if (valeurs != null) {
            selected = cell.html();
            cell.html('');
            var sel = $('<select>').appendTo(cell);
            sel.append('<option value="">...</option>'); // Option vide
            $.each(valeurs, function(i, j) {
                pardefaut = "";
                if (j == selected) { pardefaut = ' selected="selected"' ; }
                sel.append('<option value="'+i+'"'+pardefaut+'>'+j+'</option>');
            });
            sel.change( function(){
                // Au changement de valeur, on l'enregistre dans la base
                val = $(this).val();
                txt = $('option:selected', this).text(); // option sélectionnée fils de l'élément this
                ine = cell.closest('tr').attr('id');
                if (ine == 'borntobewild') {
                    // Cas de l'"Affectation à tous" de la page EPS
                    $(this).parentsUntil('table').find('tr:not(".affecter_a_tous")').each(function(i,j) {
                        id=$(j).attr('id');
                        enregistrer_select(cell, col, val, txt, id);
                    });
                    charger_page('eps');
                } else { enregistrer_select(cell, col, val, txt, ine); }
            });
        }
    }
}
/*
 * Enregistre un élément sélectionné par liste déroulante (suite de cell_to_select)
 */
function enregistrer_select(cell, col, val, txt, ine) {
    // Génération de l'url
    if (col == "Situation" || col == "Activité 1" || col == "Activité 2" || col == "Activité 3" || col == "Activité 4" || col == "Activité 5") {
        params = "ine="+ine+"&d="+val+"&champ="+col;
        url = "/maj?"+params;
    } else {
        row = cell.parents('tr').find('td').first().html();
        params = "classe="+row+"&val="+val+"&champ="+col;
        url = "/maj_classe?"+params;
    }
    // Envoie des données
    $.get( url, function( data ) {
        c = cell.parents('td');
        if (data == 'Oui') { c.addClass("maj_oui"); }
        else if (data == 'Non') { c.addClass("maj_non"); }
        c.html(txt); // Et on retire le select
    });
}

/*
 * Ajoute un delay à une action
 */
var delay = (function(){
    var timer = 0;
    return function(callback, ms){
        clearTimeout (timer);
        timer = setTimeout(callback, ms);
    };
})();

