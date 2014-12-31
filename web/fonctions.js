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
    // Traduction des niveaux sélectionnés
    var les_niveaux = new Array();
    $('#stats-niveaux td').not(":empty").each( function(i,j) {
        les_niveaux.push($(j).text());
    });
    $('#stats-options td input:checked').each(function(i, j) {
        niveaux.push(les_niveaux[$(j).val()]);
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
        } else if (stat == "Par situation") {
            var id = "#stats-Parsituation";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Provenance") {
            var id = "#stats-Provenance";
            list_to_tab($(id+' table'), data);
        } else if (stat == "Provenance (classe)") {
            var id = "#stats-Provenanceclasse";
            list_to_tab($(id+' table'), data);
            $('th:contains("liste")').width('35ex'); // la liste peut être longue
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
            if (page_active == 'eps') {
                var tier = $('#eps-tier option:selected').val();
                params = params + "&tier="+tier;
            }
            $.get( "/maj?"+params, function( data ) {
                if (data == 'Oui') {
                    cell.removeClass("maj_non");
                    cell.addClass("maj_oui");
                    // On passe à la cellule suivante
                    tr = cell.closest('tr').next();
                    // Sauf si c'est la dernière ligne
                    if (tr.attr('id') != "borntobewild") {
                        suivant = tr.children().eq(cell.index());
                        suivant.focus();
                    }
                }
                else if (data == 'Non') {
                    cell.addClass("maj_non");
                    // On reste sur la même cellule
                    el.focus();
                }
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
        var type_option = 1;
        if (col == "Niveau") { valeurs = niveaux; }
        else if (col == "Filière") { valeurs = filières; }
        else if (col == "Section") { valeurs = sections; }
        else if (col == "Situation") { valeurs = situations; }
        else if (col == "Activité 1" || col == "Activité 2" || col == "Activité 3" || col == "Activité 4" || col == "Activité 5") { 
            valeurs = activités;
            type_option = 2;
        }
        if (valeurs != null) {
            selected = cell.html();
            cell.html('');
            var sel = $('<select>').appendTo(cell);
            sel.append('<option value="">...</option>'); // Option vide
            var ordinal = 0;
            $.each(valeurs, function(i, j) {
                pardefaut = "";
                if (type_option == 1) {
                    donnee = i
                    label = j;
                } else {
                    donnee = ordinal;
                    ordinal = ordinal + 1;
                    label = valeurs[i]+') '+i;
                }
                if (j == selected) { pardefaut = ' selected="selected"' ; }
                sel.append('<option value="'+donnee+'"'+pardefaut+'>'+label+'</option>');
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
        if (col != 'Situation') { // Page d'EPS, ajout du tier
            var tier = $('#eps-tier option:selected').val();
            params = params + "&tier="+tier;
        }
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
        if (tier != undefined) { // EPS : selection d'une activité
            ajouter_datetimepicker(c);
        }
    });
}

/*
 * Recherche les éléments dans la liste
 */
function rechercher(delay){
    delay = typeof delay !== 'undefined' ? delay : 0;
    setTimeout(function() {
        var data = $('#filtre').val().toLowerCase();
        $("#liste-table > tbody > tr[id]").show();
        $("#liste-table > tbody > tr[id]").filter(function (i, v) {
            trouve = false;
            $(this).find('td').each(function (i,j) {
                if (j.innerHTML.toLowerCase().indexOf(data) >= 0) {
                    trouve = true;
                    return false;
                }
            });
            return !trouve; // on cache quand on a pas trouvé
        }).hide();
        maj_total($('#liste-table'));
    }, delay);
}

/*
 * Test d'authentification
 */
function authentification(e) {
    e = typeof e !== 'undefined' ? e : null;
    if (e) { e.preventDefault(); // no-reload
    }
    $("#login-message").hide();
    var shaObj = new jsSHA($("#motdepasse").val(), "TEXT");
    motdepasse = shaObj.getHash("SHA-512", "HEX");
    $.ajax({
        type: "POST",
        url: "auth",
        data: { mdp: motdepasse },
        success: function(html){
            $("#login-message").show();
            $("#motdepasse").val('');
            statut = html['statut'];
            login = html['message'];
            $('#onglets li').hide();
            if (statut == 0) {
                $("#login").hide();
                $("#login-message").html('Bonjour '+login);
                if (login == 'admin') {
                    $('#onglets li').show();
                } else if (login == 'eps') {
                    $("#onglets li:contains('EPS')").show();
                    $("#onglets li:contains('Stats')").show();
                }
                // Rechargement de la première page
                $("#onglets").children().removeClass('actif');
                $('#export').show();
                $('.quitter').show();
                // Chargement de la page d'accueil
                $.get( "/accueil.html", function( data ) {
                    if (login == "admin") {
                        $("#accueil").html(data);
                    } else if (login == "eps") {
                        $("#accueil").html("<h2>Bienvenue sur Legion/EPS</h2>");
                        // Modification de l'écran de stats
                        stats_listes(['EPS (activite)'], ['BEP','BAC']);
                    }
                    charger_page('accueil');
                });
            } else {
                // Échec de connection
                $("#login-message").html(login);
                $('#export').hide();
            }
        }
    });
    return false;
}

/*
 * Ajouter datetimepicker à une cellule
 */
function ajouter_datetimepicker(cell) {
    ine = cell.closest('tr').attr('id');
    indice = 'Date '+( (cell.index()+1)/2 );
    if (ine in liste_eps && indice in liste_eps[ine]) {
        d = liste_eps[ine][indice].split('-');
        if (d.length == 3) { date = d[2]+'/'+d[1]+'/'+d[0]; }
        else { date = ''; }
        cell.append('<br><input type="text" class="datetimepicker" size="10" maxlength="10" value="'+date+'">');
        cell.find('.datetimepicker').datetimepicker({
            lazyInit:true,
            lang:'fr',
            timepicker:false,
            closeOnDateSelect:true,
            format:'d/m/Y',
            yearStart:'2010',
            onChangeDateTime:function(dp,$input){
                ine = $input.closest('tr').attr('id');
                indice = 'Date '+( ($input.parent().index()+1)/2 );
                a = $input.val().split('/');
                date = a[2]+'-'+a[1]+'-'+a[0];
                url = "/maj?ine="+ine+"&champ="+indice+"&d="+date;
                $.get( url, function( data ) {
                    if (data == 'Oui') {
                        $input.removeClass("maj_non");
                        $input.addClass("maj_oui");
                        liste_eps[ine][indice] = date;
                    } else {
                        $input.addClass("maj_non");
                        $input.removeClass("maj_oui");
                    }
                });
            }
        });
    }
}
