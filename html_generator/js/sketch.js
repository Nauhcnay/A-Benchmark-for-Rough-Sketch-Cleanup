


var activeTableKey;
var tables = {};
var $tables = {};
var ids = [];


// specific version to remove running time
function createLabelsTogglesMulti(tables, id=''){
    var toggleVisibleLinks = '';
    toggleVisibleLinks += '<div class="btn-group-toggle flex-wrap" data-toggle="buttons">';
    toggleVisibleLinks += button_html("toggle-label", ".distance", "distance");
    
    toggleVisibleLinks += button_html("toggle-label", ".variant", "variant");
    toggleVisibleLinks += button_html("toggle-label", ".parameter", "parameter");

    var labelsId = "labels";
    if(id !== '') labelsId+='-'+id;
    document.getElementById(labelsId).innerHTML = toggleVisibleLinks;
    $('[name=toggle-label').on( 'click', function (e) {
	var label = $(this).attr('id');
	$(label).toggle();
	tables[activeTableKey].columns.adjust().draw();
    } );
}


$(document).ready(function() {
    // on sketch page, do not use vertical scroll.
//    dataTableInitOptions['scrollY'] = false;



    /*
dataTableInitOptions['dom'] = 'prt';
    
    var $table_ranking = $('#ranking')

    
    rankingOptions = $.extend( {},  dataTableInitOptions);
    rankingOptions['orderCellsTop'] = false;
    rankingOptions["ordering"]= false
   

    var table_ranking = $table_ranking.DataTable( rankingOptions );
    dataTablePostInit($table_ranking,table_ranking);


    //  createToggles(table_ranking, null, 'ranking');
    */
    var $table_rough = $('#rough')
    options = $.extend( {},  dataTableInitOptions);
    var table_rough = $table_rough.DataTable( options );
    dataTablePostInit($table_rough,table_rough);
    createToggles(table_rough, null, 'rough');

    
    var $table_gt = $('#gt') 
    var table_gt = $table_gt.DataTable( dataTableInitOptions );
    dataTablePostInit($table_gt,table_gt);
    createToggles(table_gt, null, 'gt');


    $('.autoBestTable').each(function(){
	ids.push($(this).attr("id"));
    });

    var idCpt=0;
    ids.forEach(function(item){
	var tableid = '[if="'+item+'"]'
	var data_info = item+'_info'
	options =$.extend( true, {},  dataTableInitOptions);
	var hiddenSort = [];
	hiddenSort.push({ "orderData":[ 1 ], "targets": [ 2 ] });
	hiddenSort.push({ "targets": [ 1 ], "visible": false, "searchable": false });
	
	options['columnDefs'] = hiddenSort;
		
	var $table = $(tableid);
	var table = $table.DataTable( options );
	dataTablePostInit($table,table);
	$('#autoBest-container').css( 'display', 'block' );
	table.columns.adjust().draw();
    	tables[item]=table;
	$tables[item]=$table;
	if(idCpt==0){
	    activeTableKey=item;
	}
	else{
	    $('[id="wrapper-'+item+'"]').hide();
	}
	idCpt ++;
    });

    createTogglesMulti(tables, function(cpt){return cpt != 1;}, 'autoBest');
    createLabelsTogglesMulti(tables, 'autoBest');

    // combo table
    $('.dropdown-item' ).on('click', function () {
	$('#wrapper-'+activeTableKey).toggle();
	activeTableKey = $(this).data("value");
	$('#wrapper-'+activeTableKey).toggle();
	$('#dropdownMenuButton').html(activeTableKey);
//	$('#dist-current').html('current: '+activeTableKey);
	tables[activeTableKey].columns.adjust().draw();	
	
	$('[name=toggle-vis-autoBest]').each(function(){ 
	    // Get the column API object
	    var column = tables[activeTableKey].column( $(this).attr('id') );
	    var visible = $(this).parent().hasClass("active");
	    //console.log($(this).attr('id'), $(this).parent().hasClass("active")) 
	    // Toggle the visibility
	    column.visible( visible );
	});
    });
    $('#combo-table' ).val(activeTableKey);
    
    
    var $table_auto = $('#auto') 
    var table_auto = $table_auto.DataTable( dataTableInitOptions );
    dataTablePostInit($table_auto,table_auto);
    createToggles(table_auto, null, 'auto');
    table_auto.columns.adjust().draw();

//
//    var $table_dist = $('#dist') 
//    var table_dist = $table_dist.DataTable( dataTableInitOptions );
//    dataTablePostInit($table_dist,table_dist);
//    createToggles(table_dist, 'dist');

} );
  
