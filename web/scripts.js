// Champs affichés dans la vue
var champs_vue = new Array();
// Page affichée
var page_active = "";
var les_pages = new Array();
// Total d'élèves dans la base
var nb_eleves = 0;
// Champs du pending (tous)
var champs_pending = [ "INE", "Nom", "Prénom" , "Naissance", "Genre", "Mail", "Entrée", "Diplômé", "Situation", "Lieu", "Année", "Classe", "Établissement", "Doublement" ];
// Liste des situations possibles
var liste_situations = new Array();

/* Placeholder */
function nyi(message) { alert ('Not yet implemented :)\n'+message); }

/* Importation
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
 * Système d'input pour modifier le contenu d'une colonne
 */
/*   Création de l'input   */
function add_input() {
    var td = $(this);
    td.removeClass('maj_oui maj_non'); // Nettoyage du marqueur d'envoie précédent
    if ( td.children().first().prop("tagName") != "INPUT" ) { // S'il n'y a pas encore d'input
        var val = td.html();
        if (val == "?") { val = ""; }
        td.html("<input type='text' value='"+val+"' size='10'></input>");
        td.children().first().focus(); // Focus auto sur ce nouvel input
    }
}
/*   Envoie de la modification   */
function push_input() {
    var td = $(this);
    if ( td.html() != "?" ) {
        var input = td.children().first();
        var val = input.val();
        old = input.attr('value');
        if (val != "" && val != old) {
            var ine = td.parent().attr('id');
            index_x = td.parent().children().index(td);
            var champ = champs_vue[index_x];
            params = "ine="+ine+"&champ="+champ+"&d="+val;
            $.get( "/maj?"+params, function( data ) {
                if (data == 'Oui') { td.addClass("maj_oui"); }
                else if (data == 'Non') { td.addClass("maj_non"); }
            });
        }
        td.html(val); // Suppression de l'input
    }
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
 * Mise à jour de l'affiche du nombre  total de résultats lors d'une recherche
 */
function total_resultats(e, filter){
    a = $(this).find('tr:visible:not(".tablesorter-childRow")').length - 2; // - le header et le filtre
    t = 'Résultats : ' + a + ' / ' + nb_eleves + ' élèves.';
    $("#filter_end").html(t);
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
 * Le switch de page
 */
function charger_page(nom) {
    $.each(les_pages, function( i, p ) { $("#"+p).hide(); });

    if (nom == 'Liste') {
        page_active = 'Liste';
        $.get( "/liste", function( data ) {
            annee = data['annee'];
            // Construction du tableau
var tab = $('#vue > tbody');
tab.html( '' );
$.each( data['data'], function( key, value ) {
    var vals = "";
    ine = value['INE'];
    $.each( champs_vue, function( i, j ) {
        if (j != 'Parcours') {
            v = trad_db_val(value[j], j);
            vals += '<td id="'+ine+'-'+j+'">'+v+"</td>";
        }
    });
    tab.append("<tr id='"+ine+"'>"+vals+"</tr>\n");
    var parcours = value['Parcours'];
    // Le parcours des classes est rétrograde
    cles = reverse_key_sort(parcours);
    $.each( cles, function( i, an ) {
        var t = parcours[an];
        var doub = trad_db_val(t[2], "Doublement");
        if (annee == an) {
            // Données de l'année en cours
            $("#"+ine+'-'+'Année').html(an)
            $("#"+ine+'-'+'Classe').html(t[0])
            $("#"+ine+'-'+'Établissement').html(t[1])
            $("#"+ine+'-'+'Doublement').html(doub)
        } else {
            // Année précédente : ajout sur une ligne dépliante
            index = $.inArray("Année", champs_vue);
            vals = '<td colspan="'+index+'"></td>\n';
            vals += '<td>'+an+'</td>';
            vals += '<td>'+t[0]+'</td>';
            vals += '<td>'+t[1]+'</td>';
            vals += '<td>'+doub+'</td>';
            var taille_fin = champs_vue.length - index - 4;
            vals += '\n<td colspan="'+taille_fin+'"></td>\n';
            tab.append('<tr class="tablesorter-childRow">'+vals+"</tr>\n");
            var nom = $("#"+ine+' td:first-child');
            nom.html('<a href="#" class="toggle">'+nom.html()+'</a>');
        }
    });
});
            // Ajout des input auto sur les colonnes
            $.each(['Situation', 'Lieu'], function( i, col ) {
                index = $.inArray(col, champs_vue);
                var col_apres = $('#vue > tbody td:nth-child('+(index+1)+')');
                col_apres.on('click', add_input);
                col_apres.on('focusout', push_input);
            });

            nb_eleves = Object.keys(data['data']).length;
            $("#vue").tablesorter({
                theme:'blue',
                showProcessing: true,
                sortList: [ [0,0] ],
                headers: {
                    3: { sorter: false }
                },
                widgets: ["zebra", "filter", "cssStickyHeaders"],
                widgetOptions: {
                    cssStickyHeaders_offset   : 4,
                    cssStickyHeaders_attachTo : null
                },
                cssChildRow: "tablesorter-childRow"
            }).bind('filterEnd', total_resultats
            ).delegate('.toggle', 'click' ,function(){
                $(this).closest('tr').nextUntil('tr:not(.tablesorter-childRow)').find('td').toggle();
                return false;
            });
            // Modifier l'affichage des lignes et la recherche globale (sur les sous-cellules)
            $('button.toggle-deplier').click(function(){
                $('.tablesorter-childRow').toggleClass('remove-me');
                $('.tablesorter-childRow').find('td').toggle();
                var c = $('.tablesorter')[0].config.widgetOptions, o = !c.filter_childRows;
                c.filter_childRows = o;
                var text = "Replier tout";
                if (o) { text = "Déplier tout"; }
                $(this).html(text);
                $('table').trigger('search', false);
                return false;
            });
            $("#vue").trigger('update'); // Mise à jour des widgets
            $("#vue").trigger('filterEnd'); // Mise à jour du total
            $('button.toggle-deplier').trigger('click'); // Pliage de toutes les lignes
        });
    } else if (nom == 'Statistiques') {
        page_active = 'Statistiques';
        annee = $('#stats-annee').val();
        $.get( "/stats?annee="+annee, function( data ) {
            $('#stats > tbody').html( list_to_tab(data, [0, 1, 2, 3, 4]) );
            $("#stats").tablesorter({
                theme:'blue',
                sortList: [ [0,0] ],
                headers: {
                    3: { sorter: false },
                    4: { sorter: false }
                },
                widgets: ["zebra", "cssStickyHeaders"],
                widgetOptions: {
                    cssStickyHeaders_offset     : 4,
                    cssStickyHeaders_attachTo   : null
                }
            });
            $("#stats").trigger('update');
        });
    } else if (nom == 'Pending') {
        page_active = 'Pending';
        $.get( "/pending", function( data ) {
            $('#pending > tbody').html( list_to_tab(data, champs_pending) );
            $("#pending").tablesorter({
                theme:'blue',
                widgets: ["zebra", "cssStickyHeaders"],
            });
            $("#pending").trigger('update');
        });
    } else if (nom == 'Options') {
        page_active = 'Options';
    }
    $("#"+page_active).show();
}

/*
 * Mets à jour la liste des années connues sur la page de stats
 */
function stats_annees() {
    $.get( "/liste-annees", function( data ) {
        var options = "";
        $.each(data, function( i, an ) {
            options += "<option>"+an+"</option>\n";
        });
        $('#stats-annee').html( options );
        $('#stats-annee option:last').attr("selected","selected");
    });
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

$(document).ready(function() {
    $("#progress").hide();
    // Création du lien d'exportation
    $(".export").on('click', function (event) {
        exportTableToCSV.apply(this, [$('#'+page_active), 'export_'+page_active+'.csv']);
        // IF CSV, don't do event.preventDefault() or return false
        // We actually need this to be a typical hyperlink
    });

    // Préparation du menu
    $("#onglets").children().each(function() { les_pages.push($(this).html()) });
    $("#onglets li").click(function(event) {
        target = $(event.target);
        $("#onglets").children().removeClass('onglet_actif');
        target.addClass('onglet_actif');
        charger_page(target.html());
    });

    // Initialisation de l'application
    $.get( "/init", function( data ) {
        var entete = "";
        var filtre = "";
        liste_situations = data['situations'];
        $.each(data['header'], function( i, j ) {
            champ = j[0];
            champs_vue.push(champ);
            type = j[1];
            if (champ!="Nom" && champ!="Prénom" && champ!="Diplômé" && champ!="Lieu") {
                filter = 'class="filter-select"';
            } else { filter = ""; }
            entete += "<th "+filter+" data-placeholder=\""+type+"\">"+champ+"</th>\n";
        });
        $('#vue > thead').html( "<tr>"+entete+"</tr>\n" );
        entete = ""
        $.each(champs_pending, function( i, j ) {
            entete += "<th>"+j+"</th>\n";
        });
        $('#pending > thead').html( "<tr>"+entete+"</tr>\n" );
    });
    stats_annees();
    // Chargement de la première page
    $("#onglets li:first-child").trigger("click");
});
