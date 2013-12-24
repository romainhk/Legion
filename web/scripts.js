// Champs affichés
var champs_vue = new Array();
// Classes connues
var classes = new Array();
// Champs de recherche par défaut
rechVal = $('<input type="text" id="rech-val" size="15" maxlength="50" />');

function init(){
    // Initialisation de l'application

    // Les résultats sont triables
    $("#vue").stupidtable();
    // ... pour la petite flèche
    $("#vue").on("aftertablesort", function (event, data) {
        var th = $(this).find("th");
        th.find(".arrow").remove();
        var dir = $.fn.stupidtable.dir;
        var arrow = data.direction === dir.ASC ? "&uarr;" : "&darr;";
        th.eq(data.column).append('<span class="arrow">' + arrow +'</span>');
    });

    $.get( "/init", function( data ) {
        var entete = "";
        var filtres = "";
        $.each(data, function( i, j ) {
            champ = j[0];
            champs_vue.push(champ);
            type = j[1];
            var sort = '';
            if (type != null) { sort = 'data-sort="'+type+'"'; }
            entete += "<th "+sort+">"+champ+"</th>\n";
            input = "<input id=\""+champ+"\">";
            filtres += "<td class=\"filtre\">"+input+"</td>\n";
        });
        $('#vue > thead').html( "<tr>"+filtres+"</tr>\n<tr>"+entete+"</tr>\n" );
        // Mise à jour de la liste des classes
        listeClasses();
    });
    charger_page('Liste');
    typeDeRecherche();
}

function listeClasses(){
    // Actualise la liste des classes
    $.get( "/liste-classes", function( data ) {
        classes = data;
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
        charger_page('Liste');
    });
}

function rechercher() {
    // Faire une recherche dans la base
    var val = $('#rech-val').val();
    var type = $('#rech-type').val();
    if (val.length > 0) {
        $.get( "/recherche?val="+val+"&type="+type, function( data ) {
            $('#vue > tbody').html( list_to_tab(data, champs_vue) );
        });
    } else {
        $.jGrowl("Seigneur, vous désirez ?", { life : 5000 });
    }
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
                if (v == "1") { v = "Garçon"; } else if (v == "2") { v = "Fille"; }
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

function exportation() {
    // Exporte la table vue en csv
    alert(':P\nNot yet implemented');
}

function charger_page(nom) {
    // Change la page courante
    if (nom == 'Liste') {
        $("#Statistiques").hide();
        // Liste la contenu de la base
        $.get( "/liste", function( data ) {
            $("#Liste").show();
            $('#vue > tbody').html( list_to_tab(data, champs_vue) );
            $.jGrowl("Chargement des "+data.length+" élèves terminé.", { life : 3000 });
        });
    } else if (nom == 'Statistiques') {
        $("#Liste").hide();
        // Page des statistiques
        $.get( "/stats", function( data ) {
            $("#Statistiques").show();
            $('#stats > tbody').html( list_to_tab(data, [0, 1, 2]) );
        });
    }
}
