// Tableau des résultats
var tableau = $('<table border="1"></table>');
// Champs de ce tableau
var champs = new Array();
// Classes
var classes = new Array();
// Champs de recherche par défaut
rechVal = $("<input type=\"text\" id=\"rech-val\" size=\"15\" maxlength=\"50\" />");

function init(){
    // Initialisation de l'application
    $.get( "/init", function( data ) {
        champs = data;
        var ligne = "";
        for (var i=0;i<champs.length;i++) {
            ligne += "<th>"+champs[i]+"</th>\n";
        }
        tableau.append( "<thead>\n<tr>"+ligne+"</tr>\n</head>\n" );
        $('#vue').html(tableau);
        // Mise à jour de la liste des classes
        listeClasses();
    });
    liste();
    typeDeRecherche();
}

function listeClasses(){
    // Actualise la liste des classes
    $.get( "/liste-classes", function( data ) {
        classes = data;
        // TODO : select classe dans la recherche
        var lignes = "";
        $.each(classes, function( i, j ) {
            lignes += "<tr><td>"+j+"</td>\n";
            lignes += "<td>0 (0%)</td>\n<td>50% / 50%</td>\n</tr>\n";
        });
        $("#stats").html(lignes);
    });
}

function liste() {
    // Liste la contenu de la base
    $.get( "/liste", function( data ) {
        var tab = tableau.clone();
        tab.append( list_to_tab(data) );
        $('#vue').html(tab);
        $.jGrowl("Chargement des "+data.length+" élèves de la base terminé.", { life : 3000 });
    });
}

function typeDeRecherche() {
    var mode = $("#rech-type").val();
    if (mode=='Classe') {
        // On remplace le champs de recherche par une liste déroulante des classes
        var s = $("<select id=\"rech-val\" />");
        $.each(classes, function(i, j) {
            $("<option />", {value: j, text: j}).appendTo(s);
        });
        $("#rech-val").replaceWith(s)
    } else {
        $("#rech-val").replaceWith(rechVal)
    }
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
        // Mise à jour de la liste des classes
        listeClasses();
    });
}

function rechercher() {
    // Faire une recherche dans la base
    var val = $('#rech-val').val();
    var type = $('#rech-type').val();
    // TODO : par classe, utiliser une liste déroulante des classes connues
    if (val.length > 0) {
        $.get( "/recherche?val="+val+"&type="+type, function( data ) {
            var tab = tableau.clone();
            $('#vue').html(tab);
            $('#vue table').append( list_to_tab(data) );
        });
    } else {
        $.jGrowl("Seigneur, vous désirez ?", { life : 5000 });
    }
}

function list_to_tab(liste) {
    // Convertie une liste en lignes de tableau tr
    // TODO : pagination ?
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
    return("<tbody>\n"+ligne+"</tbody>\n");
}

function charger_stats() {
    // TODO : Charge les stats d'une année
    console.log($('#stats-annee').val());
}
