// Champs affichés dans la vue
var champs_vue = new Array();
// Page affichée
var page_active = "";
var les_pages = new Array();

/* Importation
 */
function importation() {
    // Lecture du fichier à importer
    var file = document.getElementById('fichier').files[0];
    if (file == undefined) {
        $.jGrowl("Veuillez selectionner un fichier pour lancer l'importation.", {life : 5000 });
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
        $.jGrowl(reponse, { header: 'Importation', life : 6000 });
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
        td.html("<input type='text' value='"+val+"' size='12'></input>");
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
            var champ = "Après";
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
 * Convertir une liste en lignes de tableau (tr)
 */
function list_to_tab(liste, champs) {
    var lignes = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        ine = value['INE'];
        $.each( champs, function( i, j ) {
            v = value[j];
            if (j == "Parcours") { // Traduction des doublements
                v = v.replace(/([^, ]+)\*/g, '<span class="doublement">$1</span>');
            } else if (j == "Genre") { // Traduction de la colonne genre
                if (v == "1") { v = "Homme"; } else if (v == "2") { v = "Femme"; }
            }
            vals += "<td>"+v+"</td>";
        });
        lignes += "<tr id='"+ine+"'>"+vals+"</tr>\n";
    });
    return(lignes);
}

/* 
 * Le switch de page
 */
function charger_page(nom) {
    $.each(les_pages, function( i, p ) { $("#"+p).hide(); });
    if (nom == 'Liste') {
        page_active = 'Liste';
        $.get( "/liste", function( data ) {
            // Construction du tableau
            $('#vue > tbody').html( list_to_tab(data, champs_vue) );
            // Ajout des input auto sur la colonne 'Après'
            index = $.inArray('Après', champs_vue);
            var col_apres = $('#vue > tbody td:nth-child('+(index+1)+')');
            col_apres.on('click', add_input);
            col_apres.on('focusout', push_input);

            $.jGrowl("Chargement des "+data.length+" élèves terminé.", { life : 3000 });
            $("#vue").tablesorter({
                theme:'blue',
                sortList: [ [0,0] ],
                widgets: ["zebra", "filter"]
            });
        });
    } else if (nom == 'Statistiques') {
        page_active = 'Statistiques';
        annee = $('#stats-annee').val();
        $.get( "/stats?annee="+annee, function( data ) {
            $('#stats > tbody').html( list_to_tab(data, [0, 1, 2, 3, 4]) );
            $("#stats").tablesorter({
                theme:'blue',
                sortList: [ [0,0] ],
                widgets: ["zebra"],
                headers: {
                    3: { sorter: false },
                    4: { sorter: false }
                }
            });
        });
    }
    $("#"+page_active).show();
}

/* Mets à jour la liste des années connues sur la page de stats
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

/* Conversion d'un tableau html en fichier CSV
 * FROM http://jsfiddle.net/terryyounghk/KPEGU/
 */
function exportTableToCSV($table, filename) {
    var $rows = $table.find('tr:visible:has(td,th):not(".tablesorter-filter-row")'),

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
        var filtres = "";
        $.each(data, function( i, j ) {
            champ = j[0];
            champs_vue.push(champ);
            type = j[1];
            entete += "<th data-placeholder=\""+type+"\">"+champ+"</th>\n";
        });
        $('#vue > thead').html( "<tr>"+entete+"</tr>\n" );
    });
    stats_annees();
    // Chargement de la première page
    $( "#onglets li:first-child" ).trigger( "click" );
});
