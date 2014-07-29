// Champs affichés dans la vue
var champs_liste = new Array();
// Page affichée
var page_active = "";
// Liste des pages et correspondance id-titre
var les_pages = {
        'accueil': '',
        'noauth': '',
        'liste': 'Liste',
        'stats': 'Stats',
        'pending': 'En<br>Attente', 
        'options': 'Options' };
// Total d'élèves dans la base
var nb_eleves = 0;
// Champs du pending (tous)
var champs_pending = [ "INE", "Nom", "Prénom" , "Naissance", "Genre", "Mail", "Entrée", "Classe", "Établissement", "Doublement", "Raison" ];
// Indique si les sous-cellules (childrows) sont visibles ou non
var vue_depliee = true;
// Liste des situations possibles
var situations = new Array();
// Les niveaux, filières et sections reconnues
var niveaux = new Array();
var filières = new Array();
var sections = new Array();
// Les statistiques disponibles
var les_stats = ['Général', 'Par niveau', 'Par section', 'Provenance', 'Provenance (classe)', 'Taux de passage'];

/*
 * Mets à jour les listes de la page de statistiques
 */
function stats_listes() {
    // Masquage des tableaux de résultat, sauf Général
    $.each(les_stats, function( i, p ) {
        $("#stats-"+p.replace(/ |\(|\)/g, '')).hide();
    });
    // Choix de la statistiques à recherche
    var options = "";
    $.each(les_stats, function( i, s ) {
        options += "<option>"+s+"</option>\n";
    });
    $('#stats-liste').html( options );
    // Choix de l'année
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
 * Mises à jour du total (après une recherche)
 */
function maj_total(tableau){
    var a = tableau.find('tr:visible:not("sousligne")').length - 1; // - le header
    var id = '';
    if (page_active == 'liste') {
        id = 'totalListe';
        t = 'Résultats : ' + a + ' / ' + nb_eleves + ' élèves.';
    } else if (page_active == 'pending') {
        id = 'totalPending';
        t = a + ' enregistrements.';
    }
    $("#"+id).html(t);
}

/*
 * Charge la page demandant une authentification
 */
function noauth() {
    page_active = 'noauth';
    charger_page(page_active);
    $("#login-message").hide();
    $("#login").show();
}

/*
 * Mise à jour d'un tableau triable
 */
function maj_sortable(parametre) {
    $.get( "/liste"+parametre, function( data ) {
        annee = data['annee'];
        $('#liste-table > tbody').html( data['html'] );
        nb_eleves = data['nb eleves'];
        $('#liste-table tr').hover(function() { // On mouse over
            tr = $(this).nextUntil('tr:not(".sousligne")');
            tr.removeClass('sousligne');
        }, function() { // On mouse out
            tr = $(this).nextUntil('tr[id]');
            tr.addClass('sousligne');
        });
        // Remplacement des adresses mails
        $('#liste-table tr[id] td:nth-child(4)').each(function(i,j) {
            v = $(j).html();
            if (v != "") { $(j).html('<a href="mailto:'+v+'">@</a>'); }
        });
        $("#liste-table td:nth-child(12)").click(cell_to_select);
        maj_total($('#liste-table'));
    }).fail(noauth);
}

/* 
 * Le switch de page
 */
function charger_page(nom) {
    $.each(les_pages, function( i, p ) { $("#"+i).hide(); });

    if (nom == 'accueil') {
        page_active = 'accueil';
        $.get( "/accueil.html", function( data ) {
            $("#accueil").html(data);
        });
    } else if (nom == 'liste') {
        page_active = 'liste';
        vue_depliee = true;
        maj_sortable('');
    } else if (nom == 'stats') {
        page_active = 'stats';
        $.get( "/stats?stat=test", function( data ) {
        }).fail(noauth);
    } else if (nom == 'pending') {
        page_active = 'pending';
        $.get( "/pending", function( data ) {
            $('#pending table > tbody').html( list_to_tab_simple(data, champs_pending) );
            maj_total($('#pending'));
        }).fail(noauth);
    } else if (nom == 'options') {
        page_active = 'options';
        $.get( "/options", function( data ) {
            niveaux = data['niveaux'];
            filières = data['filières'];
            sections = data['sections'];
            var affectations = data['affectations'];
            var tab = '';
            var parite = 'paire';
            $.each(affectations, function(i, j) {
                var c = j['Classe'];
                var n = j['Niveau'];
                var s = j['Section'];
                if (parite == 'impaire') {parite='paire';} else {parite='impaire';}
                tab += '<tr class="'+parite+'"><td>'+c+'</td><td>'+n+'</td><td>'+s+'</td></tr>\n';
            });
            $('#options table > tbody').html(tab);
            $("#options table td").click(cell_to_select);
        }).fail(noauth);
    }
    $("#"+page_active).show();
}

$(document).ready(function() {
    $("#progress").hide();

    var tables_stats = ['Général', 'Parniveau', 'Parsection', 'Provenance', 'Provenanceclasse', 'Tauxdepassage'];
    // Création du lien d'exportation
    $("#export").on('click', function (event) {
        exportTableToCSV.apply(this, [$('#'+page_active), 'export_'+page_active+'.csv']);
        // IF CSV, don't do event.preventDefault() or return false
        // We actually need this to be a typical hyperlink
    });

    // Préparation du menu
    $.each(les_pages, function(i,j) {
        if (j != "") {
            $("#onglets").append('<li>'+j+'</li>');
        }
    });
    $("#onglets li").click(function(event) {
        target = $(event.target);
        $("#onglets").children().removeClass('actif');
        target.addClass('actif');
        $.each(les_pages, function(i,j) {
            if (j == target.html()) {
                charger_page(i);
                return false; //break
            }
        });
    });
    // Bouton quitter
    $(".quitter").hover(function(event) {
        $(this).attr("src", 'img/quitter_hover.png');
    }).mouseout(function(event) {
        $(this).attr("src", 'img/quitter.png');
    }).on('click', function (event) {
        $.get( "/quitter", function( data ) {
            var msg = $('<div>').append(data);
            msg.addClass('msg_quitter');
            $('#'+page_active).replaceWith( msg );
        });
    });
    // Formulaire de login
    $("#login-message").hide();
    $("#login").on('submit', function(e){    
        e.preventDefault(); // no-reload
        $("#login-message").hide();
        $.ajax({
            type: "POST",
            url: "auth",
            data: { mdp: $("#motdepasse").val() },
            success: function(html){
                $("#login-message").show();
                $("#motdepasse").val('');
                statut = html['statut'];
                message = html['message'];
                if (statut == 0) {
                    $("#login").hide();
                    $("#login-message").html('Bienvenue '+message);
                    // Rechargement de la première page
                    $("#onglets").children().removeClass('actif');
                    charger_page('accueil');
                } else {
                    // Échec de connection
                    $("#login-message").html(message);
                }
            }
        });
        return false;
    });

    // Initialisation de l'application
    $.get( "/init", function( data ) {
        situations = data['situations'];
        niveaux = data['niveaux'];
        $('#stats-recherche th').css({'text-transform':'none'});
        $('#stats-recherche th').last().attr('colspan', niveaux.length);
        $.each(niveaux, function( i, j ) {
            $("#stats-niveaux").append('<td>'+j+'</td>');
            if (i < 3) { checked = ' checked="checked"'; } else { checked = ''; }
            $("#stats-options td").last().before('<td><input type="checkbox"'+checked+' value="'+i+'" /></td>');
        });
        // Init des entêtes
        var entete = "";
        $.each(data['header'], function( i, j ) {
            champs_liste.push(j);
            entete += '<th>'+j+"</th>\n";
        });
        $('#liste-table > thead').html( "<tr>"+entete+"</tr>\n" );
        entete = ""
        $.each(champs_pending, function( i, j ) {
            entete += "<th>"+j+"</th>\n";
        });
        $('#pending > thead').html( "<tr>"+entete+"</tr>\n" );
        // Tri des colonnes
        $("#liste-table th").click(function(event) {
            target = $(event.target);
            col = target.html();
            classe = target.attr('class');
            $('#liste-table th').removeClass('sortable_trie').removeClass('sortable_retrie');
            if (classe == 'sortable_trie') {
                sens = 'DESC';
                target.addClass('sortable_retrie');
            } else if (classe == 'sortable_retrie' || classe == undefined) {
                sens = 'ASC';
                target.addClass('sortable_trie');
            } else { return false; }
            params = "?sens="+sens+"&col="+col;
            maj_sortable(params);
        });
        // Fonction de filtrage de la liste
        $("#filtre").keypress(function (event) {
            delay(function(){
                var data = event.target.value.toLowerCase();
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
            }, 500 );
        });
    });
    stats_listes();
    // Chargement de la page accueil
    charger_page('accueil');
});

