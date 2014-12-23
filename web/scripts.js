// Champs affichés dans la vue
var champs_liste = new Array();
// Page affichée
var page_active = "";
// Liste des pages et correspondance id-titre
var les_pages = {
        'accueil': '',
        'noauth': '',
        'quitter': '',
        'liste': 'Liste',
        'stats': 'Stats',
        'eps': 'EPS',
        'pending': 'Attente', 
        'options': 'Options' };
// Total d'élèves dans la base
var nb_eleves = 0;
// Champs du pending (tous)
var champs_pending = [ "INE", "Nom", "Prénom" , "Naissance", "Genre", "Mail", "Entrée", "Classe", "Établissement", "Doublement", "Raison" ];
// Liste des situations possibles
var situations = new Array();
// Les niveaux, filières et sections reconnues
var niveaux = new Array();
var filières = new Array();
var sections = new Array();
// Des infos plus détaillées, pour chaque classe
var infos_classes = {};
// Liste des activités possibles (EPS)
var activités = new Array();
// Les statistiques disponibles
var les_stats = ['Général', 'Par niveau', 'Par section', 'Par situation', 'Provenance', 'Provenance (classe)', 'Taux de passage', 'EPS (activite)'];
// Le login de l'utilisateur connecté
var login = '';

/*
 * Mets à jour les listes de la page de statistiques
 */
function stats_listes(les_stats, niveaux) {
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
        var options_ascolaire = "";
        $.each(data, function( i, an ) {
            options += "<option>"+an+"</option>\n";
            options_ascolaire += '<option value="'+an+'">'+an+'-'+(an+1)+"</option>\n";
        });
        $('#stats-annee').html( options );
        $('#stats-annee option:last').attr("selected","selected");
        $('#liste-annee').html( options_ascolaire );
        $('#liste-annee option:last').attr("selected","selected");
    });
    // Liste des niveaux
    $('#stats-recherche th').css({'text-transform':'none'});
    $('#stats-recherche th').last().attr('colspan', niveaux.length);
    if ($("#stats-options td").size() > 3) { // = déjà initialisé => nettoyage
        $("#stats-boutton-rech").insertAfter("#stats-options td:eq(1)");
        $("#stats-niveaux td:gt(1)").remove();
        $("#stats-options td:gt(2)").remove();
    }
    $.each(niveaux, function( i, j ) {
        $("#stats-niveaux").append('<td>'+j+'</td>');
        if (i < 3) { checked = ' checked="checked"'; } else { checked = ''; }
        $("#stats-options td").last().before('<td><input type="checkbox"'+checked+' value="'+i+'" /></td>');
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
function maj_sortable(sens, col) {
    $('#liste-table').css('opacity', '0.3');
    var annee = $('#liste-annee option:selected').val();
    var niveau = $('#liste-niveau option:selected').val();
    parametres = '?annee='+annee+'&sens='+sens+'&col='+col+'&niveau='+niveau;
    $.get( "/liste"+parametres, function( data ) {
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
        // Remplacement des années scolaires
        $('#liste-table tr[id] td:nth-child(6), #liste-table tr.sousligne td:nth-child(2)').each(function(i,j) {
            v = $(j).html();
            if (v != "") { $(j).html(v+'-'+(parseInt(v)+1)); }
        });
        // Colonnes éditables
        $("#liste-table td:nth-child(12)").click(cell_to_select);
        $('#liste-table td[contenteditable]').on('keydown', maj_cellule);
        $('#liste-table').css('opacity', '1');
        maj_total($('#liste-table'));
        // On relance le filtrage
        rechercher();
    }).fail(noauth);
}

/* 
 * Le switch de page
 */
function charger_page(nom) {
    // Mise à jour de l'onglet actif
    $("#onglets").children().removeClass('actif');
    $("#onglets").find(':contains('+nom+')').addClass('actif');
    // Cachement des pages et normalisation du nom
    $.each(les_pages, function( i, p ) {
        $("#"+i).hide();
        if (p==nom) { nom = i; }
    });

    if (nom == 'accueil') {
        page_active = 'accueil';
    } else if (nom == 'quitter') {
        page_active = 'quitter';
        $.get( "/quitter", function( data ) {
            $('#quitter').html(data);
        });
    } else if (nom == 'liste') {
        page_active = 'liste';
        maj_sortable('', '');
    } else if (nom == 'stats') {
        page_active = 'stats';
        $.get( "/stats?stat=ouverture", function( data ) {
            if (data['data'] != "100") {
                msg = "Les informations sur les classes sont complétées à "+data['data']+"%. Pour améliorer l'analyse des résultats, veuillez passer <a href=\"#\" onclick=\"charger_page('Options')\">sur la page d'options</a> pour définir le niveau et la section des classes de l'établissement.";
            } else { msg = ''; }
            $('#stats-Avertissement').html(msg);
        }).fail(noauth);
    } else if (nom == 'eps') {
        page_active = 'eps';
        var eps_classe = $('#eps-classes option:selected').val();
        if (eps_classe == undefined) { eps_classe = ''; }
        var eps_tier = $('#eps-tier option:selected').val();
        if (eps_tier == undefined) { eps_tier = ''; }
        $.get( "/eps?classe="+eps_classe+"&tier="+eps_tier, function( data ) {
            liste = data['liste'];
            infos_classes = data['classes']; // global
            // Traduction des notes, absence et dispense
            $.each(liste, function(i, j) {
                $.each( ['Note 1', 'Note 2', 'Note 3', 'Note 4', 'Note 5'], function (n, note) {
                    k = j[note];
                    if (k == -1)      { liste[i][note] = ''; }
                    else if (k == -2) { liste[i][note] = 'Abs'; }
                    else if (k == -3) { liste[i][note] = 'Disp'; }
                });
            });
            // Liste des notes
            if (liste != '') {
                $('#eps-table > tbody').html( list_to_tab_simple(liste, ['Élèves','Activité 1','Note 1','Activité 2','Note 2','Activité 3','Note 3','Activité 4','Note 4','Activité 5','Note 5','x̄','Protocole','Notes']) );
                // Ligne pour affecter une activité à toute une classe
                $('#eps-table > tbody').append('<tr id="borntobewild" class="affecter_a_tous"><td><i>Affecter à tous</i></td><td>?</td><td></td><td>?</td><td></td><td>?</td><td></td><td>?</td><td></td><td>?</td><td></td><td></td><td></td></tr>');

                $("#eps-table > tbody td").click(cell_to_select);
                // Coloration des notes utilisées pour le calcul de la moyenne
                offset = 1; // Position de la colonne "Activité 1"
                $.each(data['liste'], function(i, j) {
                    ine = i;
                    if (j['Notes']) {
                        $.each(j['Notes'], function(k,l) {
                            $('#eps-table #'+ine+' td:nth-child('+(offset+2*l)+')').addClass('eps-selection');
                        });
                    }
                });
                // Affichage du tier
                var tier = $("#eps-tier option[value='"+data['tier']+"']").html();
                $("#eps-table th:contains(x̄)").html('x̄ '+tier);
            }
            // Les colonnes "Notes x"
            $('#eps-table > tbody td:nth-child(3), #eps-table > tbody td:nth-child(5)').attr('contenteditable','true');
            $('#eps-table > tbody td:nth-child(7), #eps-table > tbody td:nth-child(9)').attr('contenteditable','true');
            $('#eps-table > tbody td:nth-child(11)').attr('contenteditable','true');
            // Et la colonne "Protocole"
            $('#eps-table > tbody td:nth-child(13)').attr('contenteditable','true');
            $('#eps-table td[contenteditable]').on('keydown', maj_cellule);
            // Ligne de démarcation selon le niveau
            if (eps_tier == "1") { col = '7'; } else { col = '5'; }
            $('#eps-table > tbody td:nth-child('+ col +')').css({'border-right':'2px dashed #5b6b5b'});
        }).fail(noauth);
    } else if (nom == 'pending') {
        page_active = 'pending';
        $.get( "/pending", function( data ) {
            $('#pending-table > tbody').html( list_to_tab_simple(data, champs_pending) );
            maj_total($('#pending'));
            $('#pending-dateExport').html(data['date']);
        }).fail(noauth);
    } else if (nom == 'options') {
        page_active = 'options';
        $.get( "/options", function( data ) {
            niveaux = data['niveaux']; // global
            filières = data['filières']; // global
            sections = data['sections']; // global
            var tab = '';
            var parite = 'paire';
            $.each(data['affectations'], function(i, j) {
                var c = j['Classe'];
                var n = j['Niveau'];
                var s = j['Section'];
                if (parite == 'impaire') {parite='paire';} else {parite='impaire';}
                tab += '<tr class="'+parite+'"><td>'+c+'</td><td>'+n+'</td><td>'+s+'</td></tr>\n';
            });
            $('#options-table > tbody').html(tab);
            $("#options-table td").click(cell_to_select);
        }).fail(noauth);
    }
    $("#"+page_active).show();
}

$(document).ready(function() {
    $("#progress").hide();

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
        charger_page(target.html());
    });
    // Bouton quitter
    $(".quitter").hover(function(event) {
        $(this).attr("src", 'img/quitter_hover.png');
    }).mouseout(function(event) {
        $(this).attr("src", 'img/quitter.png');
    }).on('click', function (event) {
        charger_page('quitter');
    });
    // Formulaire de login
    $("#login-message").hide();
    $("#login").on('submit', authentification);
    // Ajout d'une méthode de tri par date
    $.fn.stupidtable.default_sort_fns["date"] = function(a, b) {
        aa = a.split('/');
        bb = b.split('/');
        // Année
        if (aa[2] < bb[2]) { return -1; }
        else if (aa[2] > bb[2]) { return 1; }
        else { // Mois
            if (aa[1] < bb[1]) { return -1; }
            else if (aa[1] > bb[1]) { return 1; }
            else { // Jour
                if (aa[0] < bb[0]) { return -1; }
                else if (aa[0] > bb[0]) { return 1; }
                else { return 0; }
            }
        }
    }

    // Initialisation de l'application
    $.get( "/init", function( data ) {
        situations = data['situations'];
        niveaux = data['niveaux']; // global
        activités = data['activités'];

        stats_listes(les_stats, niveaux);
        // Init des entêtes
        var entete = "";
        $.each(data['header'], function( i, j ) {
            champs_liste.push(j);
            entete += '<th>'+j+"</th>\n";
        });
        $('#liste-table > thead').html( "<tr>"+entete+"</tr>\n" );
        entete = ""
        $.each(champs_pending, function( i, j ) {
            if (j == 'Naissance') { ds = "date"; }
            else { ds = "string"; }
            entete += '<th data-sort="'+ds+'">'+j+"</th>\n";
        });
        $('#pending-table > thead').html( "<tr>"+entete+"</tr>\n" );
        // EPS : Liste des classes
        var options = '<option value="">...</option>\n';
        $.each(data['eps'], function( i, s ) {
            options += "<option>"+i+"</option>\n";
        });
        $('#eps-classes').html(options);
        $('#eps-classes, #eps-tier').on('change', function(i,j) {
            // Sélection auto du bon niveau si le choix est fait par classe
            if (i.target.id == "eps-classes") {
                classe = $('#eps-classes option:selected').val();
                niveau = infos_classes[classe]['Niveau'];
                if (niveau == niveaux[0]) {         // Seconde
                    $("#eps-tier option[value='BEP']").prop('selected', true);
                } else if (niveau == niveaux[2]) {  // Terminale
                    $("#eps-tier option[value='BAC']").prop('selected', true);
                }
            }
            charger_page('EPS');
        });
        // Tri des colonnes
        $(".sortable th").click(function(event) {
            target = $(event.target);
            table = target.parentsUntil('div').last();
            if (table.attr('id') == 'liste-table') {
                // Tri par le serveur
                classe = target.attr('class');
                target.removeClass('sorting-desc').removeClass('sorting-asc');
                if (classe == 'sorting-desc') {
                    sens = 'DESC';
                    target.addClass('sorting-asc');
                } else if (classe == 'sorting-asc' || classe == undefined) {
                    sens = 'ASC';
                    target.addClass('sorting-desc');
                } else { return false; }
                col = target.html();
                maj_sortable(sens, col);
            } else { // Tri local
            }
        });
        // Fonction de filtrage de la liste
        $("#filtre").keypress(function (event) { rechercher(500); });
        $('.sortable').stupidtable();
        // Test d'authentification
        authentification();
    });
    $('#liste-annee, #liste-niveau').on('change', function(i,j) {
        $('#liste table th').removeClass('sorting-desc').removeClass('sorting-asc');
        charger_page('Liste');
    });
    // Chargement de la page accueil
    charger_page('accueil');
});

