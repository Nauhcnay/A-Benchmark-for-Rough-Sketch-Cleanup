
$(document).ready(function() {   
    $('#data thead tr:eq(1) th').each( function (i) {
	var title = $(this).text();
	if(i==0) $(this).html( ' <input type="text" placeholder="Search '+title+'" class="column_search form-control form-control-sm" />' );
	else  $(this).html( '' );
    } );

    var options = dataTableInitOptions;

    options['columnDefs'] =  [
	    {		
		'targets': [1,2,3,4,5,6,7,8,9],
		'render': $.fn.dataTable.render.number( '', '.', 3 )	
	    }
    ];
        
    var $table = $('#data') 
    var table = $table.DataTable( options );
    dataTablePostInit($table,table);

    createToggles(table);
    $('[name=toggle-vis]').on( 'click', function (e) {
	var index = $(this).attr('id') -1;
        myChart.chart.data.datasets[index].hidden = !myChart.chart.data.datasets[index].hidden;
        myChart.update();
    });
    
    // Apply the search
    $('table[aria-describedby*="data_info"] thead').on( 'keyup', ".column_search",function () {
	table
	    .column( $(this).parent().index()+':visIdx' )
	    .search( this.value )
	    .draw();
	updateChartFromData(table);

    } );

    $('table[aria-describedby*="data_info"]').on( 'click', 'thead th',function () {
	updateChartFromData(table);
    });
   
    updateChartFromData(table);
    table.columns.adjust().draw();

} );


var ctx = document.getElementById('myChart').getContext('2d');

var defaultLegendClickHandler = Chart.defaults.global.legend.onClick;
var newLegendClickHandler = function (e, legendItem) {
    var index = legendItem.datasetIndex+1;
    $('#'+index).trigger( 'click' );
};

var myChart = new Chart(ctx, {
    type: 'line',
    data: {
	labels: [],
	datasets: [{data: [], fill: false, borderColor:lineColors[0], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[1], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[2], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[3], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[4], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[5], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[6], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[7], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		   {data: [], fill: false, borderColor:lineColors[8], borderWidth:2, pointRadius:1, pointHitRadius:8, pointHoverRadius:4},
		  ]
    },
    options: {
        scales: {
            yAxes: [{
                ticks: {
                    beginAtZero: true
                }
            }],
	    xAxes: [{
		display: false,
		ticks: {
		    callback: function(dataLabel, index) {
			// Hide the label of every 2nd dataset. return null to hide the grid line too
			return index;
		    }
		}
	    }],
        },
	elements: { line: { tension: 0 } },
	legend: { onClick: newLegendClickHandler }
    }
});



// https://stackoverflow.com/questions/44661671/chart-js-scatter-chart-displaying-label-specific-to-point-in-tooltip
var messiness_to_distance_elt = document.getElementById('chart-messiness_to_distance').getContext('2d');
var messiness_to_distance = new Chart(messiness_to_distance_elt, {
    type: 'scatter',
    data: {
	labels: [],
	datasets: [
	    {fill: false, borderColor:lineColors[0], borderWidth:2, pointRadius:2, pointHitRadius:8, pointHoverRadius:4,	label:'IOU',data:[]},
	    {fill: false, borderColor:lineColors[1], borderWidth:2, pointRadius:2, pointHitRadius:8, pointHoverRadius:4,	label:'Chamfer',data:[]},
	    {fill: false, borderColor:lineColors[2], borderWidth:2, pointRadius:2, pointHitRadius:8, pointHoverRadius:4,	label:'Hausdorff',data:[]}]
    },
    options: {
	   animation: {
            duration: 0 // general animation time
        },
            scales: {
		yAxes: [{
                    ticks: {
			beginAtZero: true
                    }
		}],

            },
	    tooltips: {
		callbacks: {
		    label: function(tooltipItem, data) {
			var label = data.labels[tooltipItem.index];
			return label + ': (' + Math.round(tooltipItem.xLabel * 100) / 100 + ', ' + Math.round(tooltipItem.yLabel * 100) / 100 + ')';
            }
         }
      }
	}
});


function updateChartFromData(table) {
    var data_array=[[],[],[],[],[],[],[],[],[],[]];
    var nb = 0;
    var nb_array = [];

    var messiness_to_distance_data=[[], [], []]

    table.rows({ 'search': 'applied', 'filter': 'applied'}).every( function (rowIdx, tableLoop, rowLoop ) {
	var data = this.data();
	data_array[0].push(data[1]);
	data_array[1].push(data[2]);
	data_array[2].push(data[3]);
	data_array[3].push(data[4]);
	data_array[4].push(data[5]);
	data_array[5].push(data[6]);
	data_array[6].push(data[7]);
	data_array[7].push(data[8]);
	data_array[8].push(data[9]);
	messiness_to_distance_data[0].push({'x':data[1], 'y':data[2]});
	messiness_to_distance_data[1].push({'x':data[1], 'y':data[3]});
	messiness_to_distance_data[2].push({'x':data[1], 'y':data[4]});
	nb_array.push($(data[0]).text());
	nb = nb+1;
    } );

  
    
    var data_labels = []
    table.columns().every( function () {
	var title = this.header();
	if($(title).html().search("sketch id") == -1)
	    data_labels.push($(title).html());
    } );
    
    
    myChart.data.datasets[0].data = data_array[0];
    myChart.data.datasets[1].data = data_array[1];
    myChart.data.datasets[2].data = data_array[2];
    myChart.data.datasets[3].data = data_array[3];
    myChart.data.datasets[4].data = data_array[4];
    myChart.data.datasets[5].data = data_array[5];
    myChart.data.datasets[6].data = data_array[6];
    myChart.data.datasets[7].data = data_array[7];
    myChart.data.datasets[8].data = data_array[8];
    
    myChart.data.datasets[0].label = data_labels[0];
    myChart.data.datasets[1].label = data_labels[1];
    myChart.data.datasets[2].label = data_labels[2];
    myChart.data.datasets[3].label = data_labels[3];
    myChart.data.datasets[4].label = data_labels[4];
    myChart.data.datasets[5].label = data_labels[5];
    myChart.data.datasets[6].label = data_labels[6];
    myChart.data.datasets[7].label = data_labels[7];
    myChart.data.datasets[8].label = data_labels[8];

    myChart.data.labels = nb_array;
    
    myChart.update();


    messiness_to_distance.data.datasets[0].data = messiness_to_distance_data[0];
    messiness_to_distance.data.datasets[1].data = messiness_to_distance_data[1];
    messiness_to_distance.data.datasets[2].data = messiness_to_distance_data[2];
    messiness_to_distance.data.labels = nb_array;
    messiness_to_distance.update();

    
}

