
$(document).ready(function() {
    // Setup - add a text input to each footer cell
    // setup combo head
    $('#data thead tr:eq(1) th').each( function (i) {
	if (i==0) {
	    $(this).html('<div class="dropdown-container"><div class="dropdown">'
			 +'<button class="btn btn-sm btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">'
			 +'True</button>'
			 +'<div class="dropdown-menu" aria-labelledby="dropdrownMenuButton">'
			 +'<button class="dropdown-item" type="button" data-text="All" data-value="">All</button>'
			 +'<button class="dropdown-item" type="button" data-text="True" data-value="True">True</button>'
			 +'<button class="dropdown-item" type="button" data-text="False" data-value="False">False</button>'
			 +'</div></div></div>')
	}
	else if(i==1){
	    var title = $(this).text();
	    $(this).html( ' <input type="text" placeholder="Search '+title+'" class="column_search form-control form-control-sm"   />' );
	}
	else
	    $(this).html( '' );

    });

    var $table = $('#data') 
    var table = $table.DataTable( dataTableInitOptions );
    dataTablePostInit($table,table);
   
    createToggles(table);
    

    // Apply the search
    $('table[aria-describedby*="data_info"] thead').on( 'keyup', ".column_search",function () {
	table
	    .column( $(this).parent().index()+':visIdx' )
	    .search( this.value )
	    .draw();

    } );


    // combo curated
    // https://github.com/twbs/bootstrap/issues/24251
    $('.dropdown-item' ).on('click', function () {
	curated = $(this).data("value");
	$('#dropdownMenuButton').html($(this).data("text"));
	if (table.column(0).search() !== curated) {
	    table
		.column(0)
		.search(curated)
		.draw(); 
	}
    });

    $(document).on('show.bs.dropdown', '.dropdown-container', function(e) {
	var dropdown = $(e.target).find('.dropdown-menu');
	
	dropdown.appendTo('body');
	$(this).on('hidden.bs.dropdown', function () {
	    dropdown.appendTo(e.target);
	})
    });

    table.column(0).search("True").draw();
    table.columns.adjust().draw();

} );
  
