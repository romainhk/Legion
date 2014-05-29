// Champs affichés dans la vue
var champs_vue = new Array();
// Page affichée
var page_active = "";
var les_pages = new Array();
// Total d'élèves dans la base
var nb_eleves = 0;
// Champs du pending (tous)
var champs_pending = [ "INE", "Nom", "Prénom" , "Naissance", "Genre", "Mail", "Entrée", "Diplômé", "Situation", "Lieu", "Année", "Classe", "Établissement", "Doublement", "Raison" ];
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
    //$("#stats-Général").show();
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
 * Mises à jour après une recherche
 */
function fin_filtrage(e, filter){
    // MAJ du total de résultat
    var a = $(this).find('tr:visible:not(".tablesorter-childRow"):not(".tablesorter-filter-row")').length - 1; // - le header
    var id = '';
    if (page_active == 'Liste') {
        id = 'totalListe';
        t = 'Résultats : ' + a + ' / ' + nb_eleves + ' élèves.';
    } else if (page_active == 'Pending') {
        id = 'totalPending';
        t = a + ' enregistrements en attente.';
    }
    $("#"+id).html(t);
    // Réaffichage des childrows
    $.each($(this).find('tr.tablesorter-childRow'), function(i, cr) {
        cr = $(cr);
        if (cr.prev().css('display') == 'table-row') {
            cr.removeClass('filtered').show();
        }
    });
}

/* 
 * Le switch de page
 */
function charger_page(nom) {
    $.each(les_pages, function( i, p ) { $("#"+p).hide(); });

    if (nom == 'Liste') {
        page_active = 'Liste';
        vue_depliee = true;
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
    cles = dict_key_sort(parcours, true);
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
            // Les champs modifiables
            var champs_editables = [
                    $.inArray('Diplômé', champs_vue),
                    $.inArray('Lieu', champs_vue)];
            $("#vue").tablesorter({
                showProcessing: true,
                headers: {
                    3: { sorter: false }
                },
                widgets: ["zebra", "filter", "cssStickyHeaders", "editable"],
                widgetOptions: {
                    filter_reset : '.reset',
                    filter_childRows : true,
                    editable_columns       : champs_editables,
                    editable_enterToAccept : true,
                    editable_editComplete  : 'editComplete'
                },
                cssChildRow: "tablesorter-childRow"
            }).bind('filterEnd', fin_filtrage
            ).delegate('td', 'click', cell_to_select
            ).delegate('.toggle', 'click' ,function(){
                $(this).closest('tr').nextUntil('tr:not(.tablesorter-childRow)').find('td').toggle();
                $(this).closest('tr').nextUntil('tr:not(.tablesorter-childRow)').toggleClass('removeme');
                return false;
            }).children('tbody').on('editComplete', 'td', function(){
                maj_cellule($(this));
            });
            $("#vue").trigger('update'); // Mise à jour des widgets
            $("#vue").trigger('filterEnd'); // Mise à jour du total
            // Pliage de toutes les lignes
            if (vue_depliee) { $('button.toggle-deplier').trigger('click'); }
        });
    } else if (nom == 'Statistiques') {
        page_active = 'Statistiques';
    } else if (nom == 'Pending') {
        page_active = 'Pending';
        $.get( "/pending", function( data ) {
            $('#pending > tbody').html( list_to_tab_simple(data, champs_pending) );
            $("#pending").tablesorter({
                sortList: [ [1,0] ]
            }).bind('filterEnd', fin_filtrage
            );
            $("#pending").trigger('update');
            $("#pending").trigger('filterEnd'); // Mise à jour du total
        });
    } else if (nom == 'Options') {
        page_active = 'Options';
        $.get( "/options", function( data ) {
            niveaux = data['niveaux'];
            filières = data['filières'];
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
            $("#options").tablesorter().delegate('td', 'click', cell_to_select);
            $("#options").trigger('update');
        });
    }
    $("#"+page_active).show();
}

$(document).ready(function() {
    $("#progress").hide();

    // Paramétrage général de tablesorter
    $.tablesorter.defaults.sortList = [ [0,0] ];
    $.tablesorter.defaults.widgets = ["zebra", "cssStickyHeaders"];
    $.tablesorter.defaults.widgetOptions.cssStickyHeaders_offset = 4;
    $.tablesorter.defaults.theme = 'blue';

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
    // Bouton quitter
    $("#onglets .img_quitter").hover(function(event) {
        $(this).attr("src", 'quitter_hover.png');
    }).mouseout(function(event) {
        $(this).attr("src", 'quitter.png');
    }).on('click', function (event) {
        $.get( "/quitter", function( data ) {
            var msg = $('<div>').append(data);
            msg.addClass('msg_quitter');
            $('#'+page_active).replaceWith( msg );
        });
    });

    // Initialisation de l'application
    $.get( "/init", function( data ) {
        var entete = "";
        var filtre = "";
        situations = data['situations'];
        niveaux = data['niveaux'];
        $('#stats-recherche th').css({'text-transform':'none'});
        $('#stats-recherche th').last().attr('colspan', niveaux.length);
        $.each(niveaux, function( i, j ) {
            $("#stats-niveaux").append('<td>'+j+'</td>');
            if (i < 3) { checked = ' checked="checked"'; } else { checked = ''; }
            $("#stats-options td").last().before('<td><input type="checkbox"'+checked+' value="'+i+'" /></td>');
        });
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
            if (vue_depliee){
                $('#vue .tablesorter-childRow').find('td').hide();
                $('#vue .tablesorter-childRow').addClass('removeme');
            } else {
                $('#vue .tablesorter-childRow').find('td').show();
                $('#vue .tablesorter-childRow').removeClass('removeme');
            }
            //var c = $('#vue')[0].config.widgetOptions, o = !c.filter_childRows;
            //c.filter_childRows = o;
            // Modification du bouton
            var text = "Replier tout";
            if (vue_depliee) { text = "Déplier tout"; }
            vue_depliee = !vue_depliee;
            $(this).html(text);

            $('table').trigger('search', false);
            return false;
        });
    });
    stats_listes();
    // Chargement de la première page
    $("#onglets li:first-child").trigger("click");
});
