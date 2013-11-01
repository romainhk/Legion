var champs = new Array();
var tableau = $('<table border="1"></table>');

function init(){
    $.get( "/init", function( data ) {
        champs = data;
        // Initialisation de l'application
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
        $('#vue').append( list_to_tab(data) );
    });
}

function importation() {
    // Importation d'un csv
    // TODO : envoie du fichier
    $.get( "/importation", function( data ) {
        $('#notifications').html(data);
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
    // Convertie une liste en ligne de tableau tr
    var ligne = "";
    $.each( liste, function( key, value ) {
        var vals = "";
        for (var i=0;i<champs.length;i++) {
            c = champs[i];
            vals += "<td>"+value[c]+"</td>";
        }
        ligne += "<tr>"+vals+"</tr>\n";
    });
    return(ligne);
}
