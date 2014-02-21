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
// Indique si les sous-cellules (childrows) sont visibles ou non
var vue_depliee = true;
// Les niveaux et les sections reconnues
var niveaux = new Array();
var sections = new Array();

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
 * Mises à jour après une recherche
 */
function fin_filtrage(e, filter){
    // MAJ du total de résultat
    a = $(this).find('tr:visible:not(".tablesorter-childRow")').length - 2; // - le header et le filtre
    t = 'Résultats : ' + a + ' / ' + nb_eleves + ' élèves.';
    $("#filter_end").html(t);
    // Reaffichage des childrows
    $.each($(this).find('tr.tablesorter-childRow'), function(i, cr) {
        cr = $(cr);
        if (cr.prev().css('display') == 'table-row') {
            cr.removeClass('filtered').removeClass('remove-me').show();
        }
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

            nb_eleves = Object.keys(data['data']).length;
            index = $.inArray("Année", champs_vue);
            var champs_editables = [
                    $.inArray('Diplômé', champs_vue),
                    $.inArray('Situation', champs_vue),
                    $.inArray('Lieu', champs_vue)];
            $("#vue").tablesorter({
                theme:'blue',
                showProcessing: true,
                sortList: [ [0,0] ],
                headers: {
                    3: { sorter: false }
                },
                widgets: ["zebra", "filter", "cssStickyHeaders", "editable"],
                widgetOptions: {
                    filter_reset : '.reset',
                    cssStickyHeaders_offset   : 4,
                    cssStickyHeaders_attachTo : null,
                    editable_columns       : champs_editables,
                    editable_enterToAccept : true,
                    editable_editComplete  : 'editComplete'
                },
                cssChildRow: "tablesorter-childRow"
            }).bind('filterEnd', fin_filtrage
            ).delegate('.toggle', 'click' ,function(){
                $(this).closest('tr').nextUntil('tr:not(.tablesorter-childRow)').find('td').toggle();
                return false;
            }).children('tbody').on('editComplete', 'td', function(){
                maj_cellule($(this));
            });
            $("#vue").trigger('update'); // Mise à jour des widgets
            $("#vue").trigger('filterEnd'); // Mise à jour du total
            // Pliage de toutes les lignes
            if (vue_depliee) { $('button.toggle-deplier').trigger('click'); }
            $('#vue .tablesorter-childRow td').hide();
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
        $.get( "/options", function( data ) {
            niveaux = data['niveaux'];
            sections = data['sections'];
            var affectations = data['affectations'];
            var tab = '';
            $.each(affectations, function(i, j) {
                var c = j['Classe'];
                var n = j['Niveau'];
                var s = j['Section'];
                tab += '<tr><td>'+c+'</td><td>'+n+'</td><td>'+s+'</td></tr>\n';
            });
            $('#options > tbody').html(tab);
        });
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

        // Modifier l'affichage des childrows et permet la recherche sur eux
        $('button.toggle-deplier').click(function(){
            $('#vue .tablesorter-childRow').toggleClass('remove-me');
            $('#vue .tablesorter-childRow').find('td').toggle();
            var c = $('#vue')[0].config.widgetOptions, o = !c.filter_childRows;
            c.filter_childRows = o;
            var text = "Replier tout";
            if (vue_depliee) { text = "Déplier tout"; }
            vue_depliee = !vue_depliee;
            $(this).html(text);
            $('table').trigger('search', false);
            return false;
        });
    });
    stats_annees();
    // Chargement de la première page
    $("#onglets li:first-child").trigger("click");
});
