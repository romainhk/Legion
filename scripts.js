// Tableau des résultats
var tableau = $('<table border="1"></table>');
// Champs de ce tableau
var champs = new Array();

function init(){
    // Initialisation de l'application
    $.get( "/init", function( data ) {
        champs = data;
        var ligne = "";
        for (var i=0;i<champs.length;i++) {
            ligne += "<th>"+champs[i]+"</th>\n";
        }
        tableau.append( "<tr>"+ligne+"</tr>\n" );
        $('#vue').html(tableau);
    });
}

function liste() {
    // Liste la contenu de la base
    $.get( "/liste", function( data ) {
        var tab = tableau.clone();
        tab.append( list_to_tab(data) );
        $('#vue').html(tab);
        $.jGrowl("Chargement de la liste réussi", { life : 4000 });
        //$.jGrowl("Listage<br/>voila", { header: 'Important', life : 50000 });
    });
}

// TODO Validation du champs d'upload
$(document).ready(function() {
    $("#progress").hide();
});
function importation() {
    // Lecture du fichier à importer
    var file = document.getElementById('fichier').files[0];
    var reader = new FileReader();
    $("#progress").show();
    reader.readAsText(file, 'UTF-8');
    reader.onload = envoie_du_fichier;
}
function envoie_du_fichier(event) {
    // Envoie du fichier à importer
    var result = event.target.result;
    var fileName = document.getElementById('fichier').files[0].name;
    $.post('/importation', { data: result, name: fileName }, function(reponse) {
        $.jGrowl(reponse, { life : 6000 });
        $("#progress").hide();
    });
}

function rechercher() {
    // Faire une recherche dans la base
    var val = $('#rech-val').val();
    var type = $('#rech-type').val();
    console.log(val);
    console.log(type);
    $.get( "/recherche?val="+val+"&type="+type, function( data ) {
        $('#vue').html(tableau);
        $('#vue table').append( list_to_tab(data) );
    });
}

function list_to_tab(liste) {
    // Convertie une liste en lignes de tableau tr
    // TODO : pagination
    var ligne = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        for (var i=0;i<champs.length;i++) {
            c = champs[i];
            if (c == "Doublement") { // Traduction de la colonne doublement
                if (value[c] == "0") {
                    value[c] = "Non";
                } else {
                    value[c] = "Oui";
                }
            }
            vals += "<td>"+value[c]+"</td>";
        }
        ligne += "<tr>"+vals+"</tr>\n";
    });
    return(ligne);
}

function charger_stats() {
    // TODO : Charge les stats d'une année
    console.log($('#stats-annee').val());
}
