

$(document).ready(function() {

    // Setup - add a text input to each footer cell
    $('#data thead tr:eq(1) th').each( function (i) {
	if(i<2){
	    var title = $(this).text();	
	    $(this).html( '<input type="text" placeholder="Search '+title+'" class="column_search form-control form-control-sm" />' );
	}
	else
	    $(this).html( '' );
    } );


    var $table = $('#data') 
    var table = $table.DataTable( dataTableInitOptions );
    dataTablePostInit($table,table);
    createToggles(table, function (index, element) {
	// 0 rough id
	// 1 artist
	// 2 full
	// 3 cleaned
	// 4 scaffold lines
	// 5 shadows
	// 6 color region
	// 7 text
	// 8 extra
	if($(element).attr('id') == 6 ) $(element).trigger('click');
	if($(element).attr('id') == 7 ) $(element).trigger('click');
	if($(element).attr('id') == 8 ) $(element).trigger('click');
    });
    
    // Apply the search
    $('table[aria-describedby*="data_info"] thead').on( 'keyup', ".column_search",function () {
	table
	    .column( $(this).parent().index()+':visIdx' )
	    .search( this.value )
	    .draw();

    } );
    table.columns.adjust().draw();
    
} );

