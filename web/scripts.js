// Champs affichés
var champs_vue = new Array();
// Page affichée
var page_active = "";
var les_pages = [ 'Liste', 'Statistiques' ];

/* Initialisation */
function init(){
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
    charger_page('Liste');
}

/* Importation */
function importation() {
    // Lecture du fichier à importer
    var file = document.getElementById('fichier').files[0];
    var reader = new FileReader();
    $("#progress").show();
    reader.readAsText(file, 'ISO-8859-15');
    reader.onload = envoie_du_fichier;
}
function envoie_du_fichier(event) {
    // Envoie du fichier à importer
    var result = event.target.result;
    var fileName = document.getElementById('fichier').files[0].name;
    $.post('/importation', { data: result, name: fileName }, function(reponse) {
        $.jGrowl(reponse, { header: 'Important', life : 6000 });
        $("#progress").hide();
        charger_page('Liste');
    });
}

function list_to_tab(liste, champs) {
    // Convertie une liste en lignes de tableau tr
    var lignes = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        $.each( champs, function( i, j ) {
            v = value[j];
            if (j == "Doublement") { // Traduction de la colonne doublement
                if (v == "0") { v = "Non"; } else { v = "Oui"; }
            } else if (j == "Genre") { // Traduction de la colonne genre
                if (v == "1") { v = "Homme"; } else if (v == "2") { v = "Femme"; }
            }
            vals += "<td>"+v+"</td>";
        });
        lignes += "<tr>"+vals+"</tr>\n";
    });
    return(lignes);
}

function charger_stats() {
    console.log($('#stats-annee').val());
}

function charger_page(nom) {
    // Change la page courante
    $.each(les_pages, function( i, p ) { $("#"+p).hide(); });
    if (nom == 'Liste') {
        page_active = 'Liste';
        $.get( "/liste", function( data ) {
            $('#vue > tbody').html( list_to_tab(data, champs_vue) );
            $.jGrowl("Chargement des "+data.length+" élèves terminé.", { life : 3000 });
            $("#vue").tablesorter({
                theme:'blue',
                sortList: [ [0,0] ],
                widgets: ["zebra", "filter"]
            });
        });
    } else if (nom == 'Statistiques') {
        page_active = 'Statistiques';
        $.get( "/stats", function( data ) {
            $('#stats > tbody').html( list_to_tab(data, [0, 1, 2, 3]) );
            $("#stats").tablesorter({
                theme:'blue',
                widgets: ["zebra"],
                sortList: [ [0,0] ],
                headers: {
                    1: { sorter: false },
                    2: { sorter: false },
                    3: { sorter: false }
                }
            });
        });
    }
    $("#"+page_active).show();
}

/* Conversion d'une table html en fichier CSV
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
    // On cache toutes les pages
    $.each(les_pages, function( i, p ) { $("#"+p).hide(); });

    // Lien d'exportation
    $(".export").on('click', function (event) {
        exportTableToCSV.apply(this, [$('#'+page_active), 'export_'+page_active+'.csv']);
        // IF CSV, don't do event.preventDefault() or return false
        // We actually need this to be a typical hyperlink
    });
});
