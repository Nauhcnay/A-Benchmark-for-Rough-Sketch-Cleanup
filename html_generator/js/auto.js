


var activeTableKey;
var tables = {};
var $tables = {};
var ids = [];

$(document).ready(function() {

    $('table').each(function(){
	ids.push($(this).attr("id"));
    })

    // Sort column i+1 (img) by column i (hidden distance)  
    var hiddenSort=[];
    $('[id=\''+ids[0] +'\'] thead tr:eq(1) th').each( function (i) {
	if(i%2==1){
	    hiddenSort.push({ "orderData":[ i ], "targets": [ i+1 ] });
	    hiddenSort.push({ "targets": [ i ], "visible": false, "searchable": false });
	}
    });
	
    var options = $.extend({},dataTableInitOptions);
    options['columnDefs'] = hiddenSort;
    options['paging']=    true;
    options["deferRender"]=true;
    var idCpt=0
    ids.forEach(function(item){
	var tableid = "[id='"+item+"']";
	var data_info = item+'_info';
	
	$(tableid+' thead tr:eq(1) th').each( function (i) {    
	    if(i%2==0){
		var title = $(this).text();
		$(this).html( '<input type="text" placeholder="Search '+title+'" class="column_search form-control form-control-sm" />' );
	    }
	});
	
	var options = $.extend({},dataTableInitOptions);
   
	options['columnDefs'] = hiddenSort;
	options['paging']=    true;
	options['dom']=       'iprtp';
    	
	var $table = $(tableid);
	
	var table = $table.DataTable( options );
	dataTablePostInit($table,table);
	
	// Apply the search
	$('table[aria-describedby*="'+data_info+'"] thead').on( 'keyup', ".column_search",function () {
	    table
		.column( $(this).parent().index()+':visIdx' )
		.search( this.value )
		.draw();
	    updateChartFromData(table);
	} );
	
	$('table[aria-describedby*="'+data_info+'"]').on( 'click', 'thead th',function () {
	    updateChartFromData(table);
	});
	
	tables[item]=table;
	$tables[item]=$table;
	if(idCpt==0){
	    
	    initChartFromData(table);
	    updateChartFromData(table);
	    activeTableKey=item;
	}
	else{
	    $("[id='wrapper-"+item+"']").hide();
	}
	idCpt ++;
    });

    
    createTogglesMulti(tables, function(cpt){return cpt % 2 == 0;});
    createLabelsTogglesMulti(tables);

    $('[name=toggle-vis]').on( 'click', function (e) {
	var index = $(this).attr('id')/2-1;
        myChart.chart.data.datasets[index].hidden = !myChart.chart.data.datasets[index].hidden;
        myChart.update();
    });
    
    // combo table
    $('.dropdown-item' ).on('click', function () {
	$("[id='wrapper-"+activeTableKey+"']").toggle();
	activeTableKey = $(this).data("value");
	$("[id='wrapper-"+activeTableKey+"']").toggle();
//	$('#dist-current').html('current: XXX '+activeTableKey);
	$('#dropdownMenuButton').html(activeTableKey);

	tables[activeTableKey].columns.adjust().draw();	
	updateChartFromData(tables[activeTableKey]);
	
	$('[name=toggle-vis]').each(function(){
	    // Get the column API object
	    var column = tables[activeTableKey].column( $(this).attr('id') );
	    var visible = $(this).parent().hasClass("active");
	    //console.log($(this).attr('id'), $(this).parent().hasClass("active")) 
	    // Toggle the visibility
	    column.visible( visible );
	});
    });
    $('#combo-table' ).val(activeTableKey);
    
} );


var newLegendClickHandler = function (e, legendItem) {
    var index = 2*legendItem.datasetIndex+2;
    $('#'+index).trigger( 'click' );
};

var ctx = document.getElementById('myChart').getContext('2d');
var myChart = new Chart(ctx, {
    type: 'line',
    data: {
	labels: [],
	datasets: []
    },
    options: {
        scales: {
            yAxes: [{
                ticks: {
                    beginAtZero: true,
                }
            }],
	    xAxes: [{
		display: false,
		ticks: {
		    callback: function(dataLabel, index) {
			return index;
		    }
		}
	    }],
	},
        elements: { line: { tension: 0 } },
	legend: { onClick: newLegendClickHandler }
    }
});



function initChartFromData(table) {
    
    var datasets = [];
    var nb_array = [];
    
    var dataCount = ~~((table.row(0).data().length-1)/2);

    myChart.data.datasets = [];
    myChart.data.labels = [];
    
    for(let i=0; i  < dataCount; i++){
	myChart.data.datasets.push(
	    {data: [],
	     fill: false,
	     borderColor:lineColors[i%lineColors.length],
	     borderWidth:2,
	     pointRadius:1,
	     pointHitRadius:8,
	     pointHoverRadius:4}
	);
    }

    colcpt=0
    chartcpt=0
    table.columns().every( function () {
	var title = this.header();
	if(colcpt%2==1){
	    myChart.data.datasets[chartcpt].label = $(title).html();
	    chartcpt = chartcpt+1;
	}
	colcpt = colcpt+1;
    } );
    
    myChart.update();
}



function updateChartFromData(table) {
    
    var datasets=[];
    var nb_array = [];

    var dataCount = ~~((table.row(0).data().length-1)/2);

    for(let i=0; i  < dataCount; i++){
	myChart.data.datasets[i].data = [];
    }
    myChart.data.labels=[];
		       
    table.rows({ 'search': 'applied'}).every( function (rowIdx, tableLoop, rowLoop ) {
	var data = this.data();
	
	// data has one sketch_id col, then (dist, img) times the number of alg.
	for(let i=0; i  < dataCount; i++){
	    myChart.data.datasets[i].data.push(data[2*i+1]);
	}

	myChart.data.labels.push($(data[0]).text());
    } );
  
    myChart.update();
}
