
function button_html(name, id, title){
    return '<label class="btn btn-outline-secondary active toggle"><input type="checkbox" name="'+name+'" id="'+id+'" autocomplete="off" checked>'+title+'</label>';
}

var dataTableInitOptions = {
    'autoWidth':     false,
    'paging':        false,
    'dom':           'iprt',
    'orderCellsTop': true,
    'drawCallback':  function(){
	$("img.lazyload").lazyload();
    },
};

function dataTablePostInit($table, table){

}

// from https://colorbrewer2.org/#type=qualitative&scheme=Paired&n=12
lineColors=[
    "rgb(166,206,227)",
    "rgb(31,120,180)",
    "rgb(178,223,138)",
    "rgb(51,160,44)",
    "rgb(251,154,153)",
    "rgb(227,26,28)",
    "rgb(253,191,111)",
    "rgb(255,127,0)",
    "rgb(202,178,214)",
    "rgb(106,61,154)",
    "rgb(255,255,153)",
    "rgb(177,89,40)",
];

lightbox.option({
    'resizeDuration': 180,
    'fadeDuration': 180,
    'imageFadeDuration': 0, 
    'wrapAround': true
})

function createToggles(table, activate_func=null, id=''){
    var toggleVisibleLinks='';
    toggleVisibleLinks+='<div class="btn-group-toggle flex-wrap" data-toggle="buttons">';

    var buttonClass = 'toggle-vis';
    if(id !== '') buttonClass += '-'+id;
    
    var colcpt = 0;
    table.columns().every( function () {
	var title = this.header();
	toggleVisibleLinks += button_html(buttonClass, colcpt, $(title).html());
	colcpt = colcpt +1;
    } );
    toggleVisibleLinks+='</div>';

    var togglesId = 'toggles';
    if(id !== '') togglesId += "-"+id;
    
    document.getElementById(togglesId).innerHTML= toggleVisibleLinks;
    $('[name='+buttonClass).on( 'click', function (e) {
  	// Get the column API object
	var column = table.column( $(this).attr('id') );
	// Toggle the visibility
	column.visible( ! column.visible() );
	console.log("toggle", id);
    } );

    if(activate_func !== null){
        $('[name=toggle-vis]').each(activate_func);
    } 
}


function createTogglesMulti(tables,select_func=null, id=''){
    var toggleVisibleLinks='';
    toggleVisibleLinks+='<div class="btn-group-toggle flex-wrap" data-toggle="buttons">';
    
    var colcpt = 0;
    var buttonClass = 'toggle-vis';
    if(id !== '' ) buttonClass+='-'+id;

    tables[activeTableKey].columns().every( function () {
	if(select_func!== null && select_func(colcpt)){
	    var title = this.header();
	    toggleVisibleLinks += button_html(buttonClass, colcpt, $(title).html());
	}
	colcpt = colcpt+1;
    } );

    var togglesId = 'toggles';
    if(id !== '') togglesId += "-"+id;
    
    document.getElementById(togglesId).innerHTML= toggleVisibleLinks;
    $('[name='+buttonClass+']').on( 'click', function (e) {
	// Get the column API object
	var id =$(this).attr('id');
	var column = tables[activeTableKey].column( id );
	column.visible( ! column.visible() );
	$('[name=toggle-label]').each(function(){
	    // Get the column API object
	    var visible = $(this).parent().hasClass("active");
	    var label = $(this).attr('id');
	    $(label).toggle(visible);
	});
    });
}


function createLabelsTogglesMulti(tables, id=''){
    var toggleVisibleLinks = '';
    toggleVisibleLinks += '<div class="btn-group-toggle flex-wrap" data-toggle="buttons">';
    toggleVisibleLinks += button_html("toggle-label", ".distance", "distance");
    toggleVisibleLinks += button_html("toggle-label", ".running_time", "runtime");
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
