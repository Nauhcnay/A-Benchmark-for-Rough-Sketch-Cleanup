
import glob
import os.path
import re
import itertools
import pandas as pd
import numpy as np
import sys
import yaml

from pathlib import Path
import fnmatch

from multiprocessing import Pool
from tqdm import tqdm

import urllib.parse

img_width=150
path_to_GT_images = '../Benchmark_Dataset/GT/'
path_to_Rough_images = '../Benchmark_Dataset/Rough/'
path_to_Automatic_images = '../Automatic_Results/'

evaluation_dir = "../Evaluation_Data"
inpath = evaluation_dir + "/GT_to_GT.csv"
auto_inpath = evaluation_dir + "/Auto_to_GT.csv"
#auto_inpath = "AutoTest.csv"
sketch_tags_inpath='../Benchmark_Dataset/sketch_tags.csv'
web_output="../output"

path_jpg="JPG"
path_png="PNG"
path_svg="SVG"

f_score_parameters=(2, 4, 6, 8, 10)

cr = '\n'
row_base_class="flex-xl-nowrap mt-3"
row_base_class="mt-3"

input_types = {'original':'original', 'cb':'thresholded', 'norm_full':'all layers', 'norm_rough':'shape', 'norm_Light':'lighting', 'norm_scaffolds':'scaffold', 'norm_shadows':'shading'}

# see  generate_layers_artists(data)
# from layer in filename to layer type
gt_types_merge ={
#    'norm':'norm',
    'norm_cleaned':'norm_cleaned',
    'norm_color region':'norm_color region',
    'norm_dash line':'norm_extra',
#    'norm_discarded':'norm_discarded',
    'norm_extra_lines':'norm_scaffolds',
    'norm_full':'norm_full',
    'norm_Layer_4':'norm_scaffolds',
    'norm_light':'norm_scaffolds',
    'norm_reflection':'norm_extra',
#    'norm_rough':'norm_rough',
    'norm_scaffolds':'norm_scaffolds',
    'norm_scafold_line':'norm_scaffolds',
    'norm_scagffold_line':'norm_scaffolds',
    'norm_shadows':'norm_shadows',
    'norm_sketch':'norm_shadows',
    'norm_text':'norm_text',
    'norm_texture':'norm_extra',
}

# from layer type to display name
gt_types={
#    'norm':'norm',
    'norm_full':'all layers',
    'norm_cleaned':'shape',
    'norm_scaffolds':'scaffold',
    'norm_shadows':'shading',
    'norm_color region':'color region',
#    'norm_dash line':'norm_dash line',
#    'norm_discarded':'norm_discarded',
#    'norm_extra_lines':'norm_extra_lines',
#    'norm_Layer_4':'norm_Layer_4',
#    'norm_light':'norm_light',
#    'norm_reflection':'norm_reflection',
#    'norm_rough':'norm_rough',
#    'norm_scafold_line':'norm_scafold_line',
#    'norm_scagffold_line':'norm_scagffold_line',
#    'norm_sketch':'norm_sketch',
    'norm_text':'text',
#    'norm_texture':'extra',
    'norm_extra':'extra',
}

dummy_page={'id':'dummy', 'url':'', 'name':''}
pages=[{'id':'rough', 'url':'rough-table.html', 'name':'Rough Sketches', 'title':'Rough Sketches in the Wild'},
       {'id':'gt', 'url':'gt-table.html', 'name':'Ground Truth (artist cleaned)', 'title':'Ground Truth: sketch cleanup by professional artists' },
       {'id':'gt-to-gt', 'url':'gt-to-gt.html', 'name':'Ground Truth metrics', 'title':'Messiness and Ambiguity'},
       {'id':'auto', 'url':'auto-table.html', 'name':'Algorithm Output', 'title':'Output from state-of-the-art sketch cleanup algorithms'},
       {'id':'help', 'url':'help.html', 'name':'Help', 'title':'Organization and References'},]
pages_desc={'rough':('''
This website presents all the rough sketches we collected in the wild,
along with 40 baseline sketches used in prior work.
We curated a subset of all the sketches with a more even distribution of genre and style.
For each curated sketch, we manually thresholded them to remove the background.
We also commissioned professional artists to vectorize the rough input and
classify the strokes into different layers for the rough shape strokes and other kinds of
strokes, such as shading strokes, scaffold lines, and lighting.
The thresholded and vectorized images form the variants of the input.
We ran a set of automatic cleanup algorithms with these variants.
We ran the thresholded images at the original size and resampled to 500px and 1000px.
We ran the vectorized images at 500px and 1000px.

<p class="text-muted">Click on a sketch id to see all of its information in one place.
'''),
            'gt':('''
We commissioned three artists to clean each curated and baseline sketch.
Artists drew a cleaner version of each sketch.
They created a layer for the clean shape strokes and layers
for shading, scaffold lines, color regions, text, or extra (e.g. texture) strokes.

<p class="text-muted">Click on a sketch id to see all of its information in one place.
'''),
            'gt-to-gt':('''
<emph>Messiness</emph> captures how much non-essential information the input sketch contains.
We compute the amount of coverage removed during cleanup by artists when creating ground truth
as the ratio of pixels in all layers of the input image, since that is how it is given, to the number of pixels in the shape strokes of the ground truth, since that is the desired output.
<emph>Ambiguity</emph> measures the distance between different artists' ground truth
cleanings of the same sketch (using only shape strokes).

<p class="text-muted">Click on a sketch id to see all of its information in one place.
Click on the chart legends to show and hide information.
'''),
            'auto':('''
For each sketch, the best output (among all input variants and algorithm parameters) according to the selected metric.
Sorting the table updates the chart.

<p class="text-muted">Click on a sketch id to see all of its information in one place.
Click on the chart legend to show and hide information.
'''),
            'help':('')}

# scan and generate algorithm name and parameter without hardcode them
from tools.files import scan_algs

# from generate_input_variant_list() 
input_variant_list = ['.png',
                      'cb.png',
                      'cb_1000.png',
                      'cb_500.png',
                      'norm_full_1000.png',
                      'norm_full_500.png',
                      'norm_rough_1000.png',
                      'norm_rough_500.png',
                      '1000.png',
                      '500.png',
                      'norm_full.svg',
                      'norm_rough.svg']


# metric and parameter display in auto table

def generate_mlist(data):
    l = list((data[['metric_name', 'metric_parameter']].drop_duplicates().to_records(index=False)))
    return [ list(e) for e in l ]
    

mlist = [['Chamfer', '']] + [['F1',  f'{i}/1000'] for i in f_score_parameters ] +[['Hausdorff', '']]



# from input_variant to display label name 
variant_to_label = {'.png':'original',
                    '500.png':'original 500px',
                    '1000.png':'original 1000px',
                    'cb.png':'thresholded',
                    'cb.svg':'thresholded',
                    'cb_500.png':'thresholded 500px',
                    'cb_1000.png':'thresholded 1000px',
                    'norm_full.png':'vectorized (all layers)',
                    'norm_full.svg':'vectorized (all layers)',
                    'norm_full_500.png':'vectorized (all layers) 500px',
                    'norm_full_1000.png':'vectorized (all layers) 1000px',
                    'norm_rough.png':'vectorized (shape strokes)',
                    'norm_rough.svg':'vectorized (shape strokes)',
                    'norm_rough_500.png':'vectorized (shape strokes) 500px',
                    'norm_rough_1000.png':'vectorized (shape strokes) 1000px'}

#from input_variant (as in auto_data) to input_type (as in rough_images_desc)
variant_to_input_type = {'.png':'original',
                         '500.png':'original',
                         '1000.png':'original',
                         'cb.svg':'cb',
                         'cb.png':'cb',
                         'cb_500.png':'cb',
                         'cb_1000.png':'cb',
                         'norm_full.png':'norm_full',
                         'norm_full.svg':'norm_full',
                         'norm_full_500.png':'norm_full',
                         'norm_full_1000.png':'norm_full',
                         'norm_rough.png':'norm_rough',
                         'norm_rough.svg':'norm_rough',
                         'norm_rough_500.png':'norm_rough',
                         'norm_rough_1000.png':'norm_rough'}
        

###########################################################################
################### GENERAL HTML FUNC  ####################################
###########################################################################
###########################################################################

def img(image_path, desc=None):
  #  return f'<div class="lds-dual-ring"  data-src="{image_path}"></div>'
  #  return f'<img src="{image_path}" loading="lazy" width="200px" />'
    #return 'TEST';
    if desc is None: desc = 'image thumbnail'
    return f'<img data-src="{urllib.parse.quote(image_path)}" src="data:image/gif;base64,R0lGODdhAQABAPAAAMPDwwAAACwAAAAAAQABAAACAkQBADs=" class="lazyload img-thumbnail" alt="{desc}" width="{img_width}" />'

def img_gallery(href_path, img_path, gallery, desc):    
    rel_href_path = os.path.relpath(os.path.abspath(href_path), os.path.abspath(web_output))
    rel_img_path =  os.path.relpath(os.path.abspath(img_path), os.path.abspath(web_output))

    return f'<a href="{urllib.parse.quote(str(rel_href_path))}" data-lightbox="{gallery}" data-title="{desc}" target="_blank">{img(rel_img_path)}</a>'

def script(name):
    return f'<script src="./js/{name}.js"></script>'

def begin_controls():
    return begin_div() # +'<h3>Table display options</h3>'

def end_controls():
    return f'</div>{cr}'

def controls_toggles(suffix=None):
    if suffix is None:
        suffix=''
    else:
        suffix = '-'+suffix
    ret=''
    ret+= f'<div class="col">'
    ret+= '<h4>Column visibility:</h4>'
    ret+=f'<div class="mb-4" id="toggles{suffix}"></div>{cr}'
    ret+= f'</div>'
    return ret

def controls_labels(suffix=None):
    if suffix is None:
        suffix=''
    else:
        suffix = '-'+suffix
    ret=''
    ret+= f'<div class="col">'
    ret += '<h4>Display labels:</h4>'
    ret += f'<div class="mb-4" id="labels{suffix}"></div>{cr}'
    ret+= f'</div>'
    return ret

def controls(toggles, suffix=None):
    ret=''
    ret+=begin_controls()
    if toggles : ret+=controls_toggles(suffix)
    ret+=end_controls()
    return ret

def distance_combo(keys):
    ret = '<div class="col">'
    ret += '<h4>Select metric</h4>'
    combo =''
    combo+='<div class="dropdown">'
    combo+='<button class="btn btn-sm btn-secondary dropdown-toggle active" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">'
    combo+='Distance</button>'
    combo+='<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">'

    for key in keys:
        #id with . do not work, and we want id as value here
        key=key.replace('.','_')
        combo+= f'<button class="dropdown-item" type="button" data-value="{key}">{key}</button>'
        #combo+= f'<button class="dropdown-item" type="button" data-value="{key}">{key}</button>'
    combo+=f'</div></div>{cr}'
        
    ret += f'<div class="mb-4">{combo}<span id="dist-current"></span></div>'
    ret += '</div>'
    return ret

def begin_table(table_id, table_class):
    return f'<table id="{table_id}" class="{table_class+" " if table_class != "" else ""}table table-striped table-bordered bg-light table-hover table-sm">'

def table(header, body, tableid=None, tableclass=None):
    if tableid is None:
        tableid='data'
    if tableclass is None:
        tableclass=''
    ret = ''
    ret += f'<div class="row {row_base_class}">'
    ret += f'<div class="col col-sm-12">'
    ret += f'<div class="d-inline-flex table-container" id="{tableid}-container">'
    ret += begin_table(tableid, tableclass)
    ret += header
    ret += body
    ret += end_table()
    ret += end_div()
    ret += end_div()
    ret += end_div()
    return ret

def end_table():
    return f'</table>{cr}'

def header_and_nav(page_id):
    ret = ''

    # container have margin
    # ret += begin_div('container')
    # while fuild span all width
    ret += begin_div('container-fluid')
    ret += begin_div(name=f"row {row_base_class}")
    ret += begin_div(name="col")
    ret += page_header()
    ret += end_div()
    ret += end_div()
    ret += nav(pages[page_id])
    ret += begin_div(name=f"row {row_base_class}")
    ret += f'<div class="col-12"><h1>{pages[page_id]["title"]}</h1></div>'
    ret += page_desc(pages_desc[pages[page_id]['id']])
    ret += end_div()
    return ret

def header_and_nav_sketch_page():
    ret = ''
    ret += begin_div('container-fluid')
    ret += begin_div(name=f"row {row_base_class}")
    ret += begin_div(name="col")
    ret += page_header()
    ret += end_div()
    ret += end_div()
    ret += nav(dummy_page)
    ret += begin_div(name=f"row {row_base_class}")
    ret += end_div()
    return ret


def page_desc(txt):
    ret = f'<div class="col col-lg-8">{txt}</div>{cr}';
    return ret
                     
def nav(page):
    ret = ''
#    ret += '<nav class="navbar navbar-expand-lg  navbar-dark bg-dark fixed-top">'
#    ret += '<nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">'
    ret += '<nav class="navbar navbar-expand-lg navbar-dark bg-dark sticky-top">'
    ret += '<button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">'
    ret += '<span class="navbar-toggler-icon"></span></button>'
    ret += '<div class="collapse navbar-collapse" id="navbarSupportedContent">'
    ret += '<ul class="navbar-nav mr-auto">'
    ret += '<li class="nav-item"><a class="nav-link" href="https://cragl.cs.gmu.edu/sketchbench/">Index</a></li>' 
    ret += ' '.join( f'<li class="nav-item {"active bg-primary" if p["id"] == page["id"] else ""}"><a class="nav-link" href="{p["url"]}">{p["name"]}</a></li>' for p in pages )
    ret += f'</ul></div></nav>{cr}'
    return ret;

def page_header():
    ret = ''
    ret +=  f'<h1>A Benchmark for Rough Sketch Cleanup</h1>'
    return ret

def rough_header():
    return Path(os.path.join(os.path.dirname(__file__),'..','template','header.html')).read_text()

def begin_div(name=None, idtag=None):
    class_str = ''
    id_str = ''
    if name is not None: class_str = f'class="{name}"'  
    if idtag is not None: id_str = f'id="{idtag}"'  
    return f'<div {class_str} {id_str}>{cr}'

def end_div():
    return '</div>'

def chart_div(wrapper_class, chart_id):
    ret = ''
    ret += f'<div class="{wrapper_class}">'
    ret+= '<div class="card" style="width:100%"><div class="card-body">'
    ret += f'<canvas id="{chart_id}"></canvas>'
    ret += f'</div>{cr}'
    ret += f'</div>{cr}'
    ret += f'</div>{cr}'
    #ret += '<canvas id="myChart" width="400" height="400"></canvas>'
    return ret



############################## PER INPUT PAGE
#############################################
#############################################
#############################################
    
def get_output_image_from_row_bis( input_id, variant, algorithm, parameter ):
    
    missing_underscore = '_' if not variant.startswith('.') else ''
   
    ## Get both:
    image_stem = input_id + missing_underscore + variant.split('.')[0]
    image_glob = image_stem + '.*'
    
    images = get_auto_images( image_glob, algorithm, parameter )
 
    if len( images ) == 0:
        return None
    else:
        return images[0]

#deprecated
#def get_auto_image_desc(data, input_id):
#    subdata = data.loc[data['Input'] == input_id]
#    data_metric = subdata
#    #df = data_metric.drop(columns=['source', 'artist', 'genre', 'input_category', 'Running Time'])
#    df = data_metric.drop(columns=['source', 'artist', 'genre', 'input_category', 'Running Time', 'cleaner'])
#    df['metric_parameter'] = df['metric_parameter'].fillna('none')
#    
#    df['algorithm_with_parameter'] = df.agg('{0[algorithm]} {0[parameter]}'.format, axis=1)
#    #df = df.set_index(['Input', 'input_variant', 'metric_name','metric_parameter', 'cleaner'])
#   
#    df = df.set_index(['Input', 'input_variant', 'metric_name', 'metric_parameter'])
#    df = pd.pivot_table(df,index=['Input', 'input_variant', 'metric_name', 'metric_parameter'], columns=['algorithm', 'parameter', 'algorithm_with_parameter'], values='distance', aggfunc=np.mean)
#    return df
#


#for debug
#input_variant = input_variant_list[1]
#algorithm, parameter  = alg_param_list[2]
#ldf = auto_data.loc[(auto_data['Input'] == input_id)]    
#sdf = ldf.loc[(ldf['input_variant'] == input_variant) & (ldf['algorithm'] == algorithm) & (ldf['parameter'] == parameter)] 
#distances = sdf['distance']
#print(input_id, input_variant, algorithm, parameter, sdf)   

def get_sketch_all_table(df, input_id):
    ths='<tr><th>variant</th>'

    for algorithm, parameter in alg_param_list:
        ths+=f'<th>{alg_display_name[algorithm.lower()]} {alg_param_display_name[(algorithm.lower(), parameter)]}</th>'
    ths+='</tr>'
    header =f'<thead>{ths}</thead>{cr}'

    body='<tbody>'

    ldf = df.loc[(df['Input'] == input_id)]
    for input_variant in input_variant_list:
        row = ''
        have_value=False
        row+=f'<tr><td>{variant_to_label[input_variant]}</td>{cr}'
        for algorithm, parameter in alg_param_list:
            sdf = ldf.loc[(ldf['input_variant'] == input_variant) & (ldf['algorithm'] == algorithm) & (ldf['parameter'] == parameter)] 
            distances = sdf['distance']
            if not distances.hasnans :
                img_src, img_thumb = get_auto_img(input_id, input_variant, algorithm, parameter)
                if img_src is not None:
                    row+=f'<td>'+img_gallery(img_src, img_thumb, f'{input_id}-{input_variant}', f'{input_id} {input_variant} - {alg_display_name[algorithm.lower()]} {alg_param_display_name[(algorithm.lower(), parameter)]}')
                    #for row in sdf.itertuples():
                    #    body+=f'<span class="label distance" style="">{row.metric_name} {row.metric_parameter}: {round(row.distance, 5)}</span>'
                    row += f'</td>{cr}'
                    have_value = True
                else:
                    row += f'<td></td>{cr}'
            else:
                row += f'<td></td>{cr}'
        row += f'</tr>{cr}'
        if have_value : body += row
    body+=f'</tbody>{cr}'
    return header, body
                    
def get_auto_img(input_id, variant, algorithm, parameter):
    image_path = get_output_image_from_row_bis(input_id, variant, algorithm, parameter)
    if image_path is not None:
        image_path = str(image_path)
        image_src = get_auto_thumb_abspath(image_path)
        return image_path, image_src
    return None, None

def link_to_sketch_page(input_id):
    return f'<a href="{input_id}.html">{input_id}</a>'

## deprecated
##def get_auto_image_table(df):
##    clist = df.columns.tolist()
##    ilist= [[i[0],i[1]] for i in df.index.tolist()]
##    ilist.sort()
##    ilist = list(k for k,_ in itertools.groupby(ilist))
##
##    ths='<tr><th>rough id</th><th>variant</th><th>image</th>'
##    for c in clist:
##        ths+=f'<th>{c[0]} {c[1]}</th>'
##    ths+='</tr>'
##    header =f'<thead>{ths}{ths}</thead>{cr}'
##    
##    body='<tbody>'
##    for i in ilist:
##        input_id = i[0]
##        variant = i[1]
##        body+='<tr>'
##        body+=f'<td>{link_to_sketch_page(input_id)}</td><td>{variant}</td>'
##        
##        body+= rough_table_cell(rough_images_desc[input_id],variant_to_input_type[variant],input_id)
##        
##        for c in clist:
##            algorithm = c[0]
##            parameter = c[1]
##            image_path, image_src = get_auto_img(input_id, variant, algorithm, parameter)
##          #  image_path = get_output_image_from_row_bis(input_id, variant, algorithm, parameter)
##            if image_path is not None:
##           #     image_path = str(image_path)
##           #     image_src = image_path
##           #     if not image_path.lower().endswith(".svg"):
##           #         dirname, filename = os.path.split(image_path)
##           #         filename, extension = os.path.splitext(filename)
##           #         image_src = '/thumbs/auto/'+dirname.replace('/','_')+'_'+filename+'.jpg'
##                
##              #  body+=f'<td><a href="{image_path}" data-lightbox="{input_id}-{variant}" data-title="{input_id} {variant} - {algorithm} {parameter}" target="_blank">{img(image_src)}</a></td>'
##                body+=f'<td>'+img_gallery(image_path, image_src, f'{input_id}-{variant}', f'{input_id} {variant} - {alg_display_name[algorithm]} {alg_param_display_name[(algorithm, parameter)]}')+'</td>'
##            else:
##                body+= '<td></td>'
##        body+=f'</tr>{cr}'
##    body+=f'</tbody>{cr}'
##    return header, body


def get_auto_thumb_abspath(image_path):
    image_src = image_path
    if not image_path.lower().endswith(".svg"):
        filename = str(Path(image_path).relative_to(path_to_Automatic_images).with_suffix('.jpg').as_posix()).replace('/','_')
        image_src = web_output+'/thumbs/auto/'+filename
    return image_src


def get_auto_image_table2(input_id, data):
       
    df = data.sort_values( 'distance', ascending = True ).drop_duplicates( ['algorithm','Input'] ).sort_index()

    ths='<tr><th>algorithm</th><th>distance</th><th>result</th><th>running time</th>'
    ths+='</tr>'
    header =f'<thead>{ths}</thead>{cr}'
        
    body='<tbody>'

    for row in df.itertuples():
        body+='<tr>'
        body+=f'<td>{alg_display_name[row.algorithm.lower()]}</td>'
        body+=f'<td>{row.distance}</td>'
        cell=''
        image_path = get_output_image_from_row(row)
        if image_path is not None:
            image_path = str(image_path)
            image_src = get_auto_thumb_abspath(image_path)
            
            dist = row.distance
            variant = row.input_variant
            cell+=img_gallery(image_path, image_src, f'auto-results', f'{alg_display_name[row.algorithm.lower()]}')
            cell+=f'<span class="label distance"><span class="info-title">distance:</span>&nbsp;{round(row.distance, 5)}</span>'
            #cell+=f'<span class="label running_time">running-time:&nbsp;{row._8}</span>'
            cell+=f'<span class="label variant"><span class="info-title">variant:</span>&nbsp;{variant_to_label[row.input_variant]}</span>'
            if alg_param_display_name[(row.algorithm.lower(), row.parameter)] != '':
                cell+=f'<span class="label parameter"><span class="info-title">alg. parameter:</span>&nbsp;{alg_param_display_name[(row.algorithm.lower(), row.parameter)]}</span>'
     
        body+=f'<td>{cell}</td>'
        body+=f'<td>{row._8 if not np.isnan(row._8) else "" }</td>'
        body+='</tr>'
    body+=f'</tbody>{cr}'
    return header, body


def get_auto_image_distance_table(df):
    ths = '<tr>'
    ths+= '<th>sketch id</th>'
    ths+= '<th>variant</th>'
    ths+= '<th>metric</th>'
    for h in df.columns:
        t = h[0]
        if h[1] != 'none':
            t += ' - ' + h[1]
        ths += f'<th>{t}</th>'
    ths += '</tr>'

    header = f'<thead>{ths}{ths}</thead>{cr}'
    ret = f'<tbody>{cr}'
    for row in df.itertuples():
        ret+='<tr>'
        index = row[0]
        input_id = index[0]
        variant = index[1]
        filename = index[0]+index[1]
        metric_name = index[2]
        metric_parameter = index[3]
        ret += f'<td>{link_to_sketch_page(input_id)}</td>'
        ret += f'<td>{variant}</td>'
        ret += f'<td>{metric_name} {metric_parameter}</td>'
        for d in row[1:]:
            ret+=f'<td>{d}</td>'
        ret+=f'</tr>{cr}'
    ret+=f'<tbody>{cr}'
    return header,ret

def image_controls(title, suffix):
    return f'{cr}<div class="row {row_base_class}"><div class="col"><h3>{title}</h3>{controls(True, suffix)}</div></div>{cr}'



###########################################################################
################## Init data func #########################################
###########################################################################
###########################################################################

#################### pandas dataframe

stats_scale={}
def init_gt_data():
    data = pd.read_csv( inpath )
    
    ## Let's make nice names for the columns:
    ## warning, rough id is used in javascript to filter columns, if change here, also change in gt-to-gt.js
    column_remapping = { 'GT': 'sketch id', 'Messiness':'Messiness', 'Ambiguity_union': 'IOU', 'Ambiguity_chamfer': 'Chamfer', 'Ambiguity_hausdorff': 'Hausdorff' }
    column_reorder = list(column_remapping.values())

    for threshold in f_score_parameters:
        value = f'F1 {threshold}/1000'
        column_remapping[ f"Ambiguity_f1_{threshold}" ] = value
        column_reorder.append( value )

    data = data.rename( columns = column_remapping )
    data = data[ column_reorder ]

    # normalize stat value to [0,1]
    for stat in  data.columns.tolist()[1:]:
        dist_min = data[[stat]].min()
        data[[stat]] = data[[stat]]-dist_min
        dist_max = data[[stat]].max()
        data[[stat]] = data[[stat]]/dist_max
        stats_scale[stat]={'dist_min':dist_min[0], 'dist_max':dist_max[0]}
    #data.div(messiness_max,fill_value = 50 )
    return data



############ taken from process_Auto_to_GT_examples
###################################################
###################################################
###################################################

def init_auto_images_data():
    data = pd.read_csv( auto_inpath, dtype = 'category', na_values = [], keep_default_na = False )
    ## All columns in order.
    columns = ['source', 'artist', 'genre', 'input_variant', 'input_category', 'algorithm', 'parameter', 'Input', 'Running Time', 'metric_name', 'metric_parameter', 'distance', 'cleaner']
    assert tuple( data.columns ) == tuple( columns )
    ## This conversion of data['parameter'] converts the `category` dtype to `object` rather than strings. That's not what we want. Comment out.
    # data['parameter'] = data['parameter'].astype(str)

    # drop mse mse_resize and gan_resize
    data = data[data.parameter != 'mse_resize']
    data = data[data.parameter != 'gan_resize']
    data = data[data.parameter != 'mse']

    data["Running Time"] = pd.to_numeric(data["Running Time"], errors = 'coerce')
    # data['Running Time'] = data['Running Time'].astype(str).replace( r'Failed with code [-]?[0-9]+', np.nan, regex = True ).replace(['timeout','memory overflow','out of memory','scap converting error'],np.nan).astype(float)

    #data['metric_parameter'] = pd.to_numeric( data['metric_parameter'] )
    #data['metric_parameter'] = data['metric_parameter']/1000.
    #data['metric_parameter'] = data['metric_parameter'].fillna('none')
    #data['distance'] = data['distance'].astype(str).replace( ["N/A","Blank Image"], np.nan ).astype(float)

    data['metric_name'] = data['metric_name'].replace('F-score', 'F1')


    # convert f1 paramter from i to i/1000 e.g. 10 -> 10/1000, if parameter is empty (e.g. for Chamfer) do not change it
    params = list(dict.fromkeys(data['metric_parameter'].tolist()))
    for i in params: 
        if i != '':
            data['metric_parameter'] = data['metric_parameter'].replace(f'{i}', f'{i}/1000')

    data['distance'] = pd.to_numeric(data['distance'], errors='coerce').astype(float)
    
    return data


_get_auto_images_cache = {}
def get_auto_images( input_name_glob, alg, params = None ):
    
    def get_alg_path( alg, params ):
        params = str(params)
        path = Path(path_to_Automatic_images) / Path(alg2dir[alg.lower()]) / Path(params)
        # if alg == 'FidelitySimplicity': path = path / Path( params)
        # elif alg == 'PolyVector': path = path / Path(params)
        # elif alg == 'PolyVector2StrokeAggregator': path = path / Path(params)
        # elif alg == 'MasteringSketching': path = path / Path( params )
        # elif alg == 'DelaunayTriangulation': path = path / Path(params)
        return path
    
    # print( ( Path(path_to_Rough_images) / Path(suffix.upper()).suffix[1:] )/Path( '_'.join( Path(name).stem.split('_')[:4] ) + '*' + suffix ) )
    # print( list( ( Path(path_to_Rough_images) / Path(suffix.upper()).suffix[1:] ).glob( '_'.join( Path(name).stem.split('_')[:4] ) + '*' + suffix ) ) )
    
    ## Replaced with the cached version below.
    # image_paths = sorted( get_alg_path( alg, params ).glob( input_name_glob ) )
    
    def get_sorted_alg_path_contents_glob( alg, params, glob ):
        if ( alg, params ) not in _get_auto_images_cache:
            dir = get_alg_path( alg, params )
            _get_auto_images_cache[ ( alg, params ) ] = dir, [ x.name for x in dir.iterdir() ]
        
        dir, names = _get_auto_images_cache[ ( alg, params ) ]
        return sorted([ dir / x for x in fnmatch.filter( names, glob ) ])
    
    image_paths_fast = get_sorted_alg_path_contents_glob( alg, params, input_name_glob )
    # assert tuple([ str(p) for p in image_paths ]) == tuple([ str(p) for p in image_paths_fast ])
    image_paths = image_paths_fast
    
    suffix2priority = {'.jpg': 1, '.png': 2, '.svg': 0, '.gmi': 100, '.name': 100, '.scap': 100, '.error': 100}
    ## .gmi, .name, .scap are weird. We don't want them.
    image_paths.sort( key = lambda x: suffix2priority[x.suffix] )
    image_paths = [x for x in image_paths if suffix2priority[x.suffix]<100] 
    
    return image_paths

def generate_alg_param_list():
    alg_param_list=[]
    for row in auto_data[['algorithm', 'parameter']].drop_duplicates().iterrows():
        alg_param_list.append ( (row[1].algorithm, row[1].parameter))
    return alg_param_list

def generate_input_variant_list():
    return auto_data['input_variant'].drop_duplicates().tolist()

#### sketch info ###########

def init_sketch_tags():
    data = pd.read_csv( sketch_tags_inpath, dtype = 'category', na_values = [], keep_default_na = False ) 

    data = data.set_index('Name')
    data[['Ambiguity (Chamfer)']] = data[['Ambiguity (Chamfer)']].replace('',np.nan).astype(float)
    data[['Messiness']] = data[['Messiness']].replace('', np.nan).astype(float)

    data[['Ambiguity (Chamfer)']] = data[['Ambiguity (Chamfer)']]-stats_scale['Chamfer']['dist_min']
    data[['Ambiguity (Chamfer)']] = data[['Ambiguity (Chamfer)']]/stats_scale['Chamfer']['dist_max']

    data[['Messiness']] = data[['Messiness']]-stats_scale['Messiness']['dist_min']
    data[['Messiness']] = data[['Messiness']]/stats_scale['Messiness']['dist_max']

    return data;

def prepare_sketch_desc():
    df = auto_data.drop(columns=['source', 'artist', 'genre', 'input_category', 'Running Time', 'cleaner'])
    #df['metric_parameter'] = df['metric_parameter'].fillna('none')
#    df['algorithm_with_parameter'] = df.agg('{0[algorithm]} {0[parameter]}'.format, axis=1)
    return df


#### image desc as python dict
#extracted from init_gt_images_desc
def generate_layers_artists(data):
    layers = set()
    artists = set()
    for index, row in data.iterrows():
        gts_images = get_GTs(row['sketch id'],'')
        for image in gts_images:
            dirname, filename = os.path.split(str(image))
            filename, extension = os.path.splitext(filename)
            parts = re.split('_', filename)
            artist = parts[4]
            artists.add(artist)
            input_id = '_'.join(parts[:4]) 
            layer='norm_full'
            if len(parts) > 5 :
                layer = '_'.join(parts[5:])
            layers.add(layer)
    return layers, artists

def init_gt_images_desc(data):
    artist_images = {}
    for index, row in data.iterrows():
        gts_images = get_GTs(row['sketch id'],'')
        for image in gts_images:
            dirname, filename = os.path.split(str(image))
            filename, extension = os.path.splitext(filename)
            parts = re.split('_', filename)
            artist = parts[4]
            input_id = '_'.join(parts[:4]) 
            layer='norm_full'
            if len(parts) > 5 :
                layer = '_'.join(parts[5:])
            if layer in gt_types_merge.keys():
                layer = gt_types_merge[layer]
            else:
                #skip theses "undef" layers
                continue
            if not input_id in artist_images.keys():
                artist_images[input_id] = {}
            if not artist in artist_images[input_id].keys():
                artist_images[input_id][artist] = {}
            if not layer in artist_images[input_id][artist].keys():
                artist_images[input_id][artist][layer] = {}
            
            artist_images[input_id][artist][layer]=image
    return artist_images;



def init_rough_images_desc():
    ret = {}
    rough_images = sorted(glob.glob(path_to_Rough_images+"/*/*.*"))
    for f in rough_images:
        dirname, filename = os.path.split(f)
        filename, extension = os.path.splitext(filename)
        parts = re.split('_', filename)
        if(extension == '.png'): continue
        category = parts[0]
        subcategory = parts[1]
        artist = parts[2]
        number = parts[3]
        separator='_'
        input_type='original'
        separator='_'
        if len(parts)>4 :
            input_type = separator.join(parts[4:])

        #skip "original svg" which is norm_full
        if extension == '.svg' and input_type == 'original':
            continue
            
        input_id = separator.join([category, subcategory, artist, number])
        if input_id in ret.keys():
            ret[input_id][input_type] = { 'filename':filename, 'vector': extension == '.svg' };
            ret[input_id]['curated'] = True
        else:
            ret[input_id] = { input_type: { 'filename':filename, 'vector': extension == '.svg'}, 'curated':False};
    return ret;



def init_auto_images_desc(data):

    ret = {}
    for metric,parameter in mlist:
        
        data_metric = data[ (data['metric_name'] == metric) & (data['metric_parameter'] == parameter) ]
       
        best_per_input_alg = data_metric.sort_values( 'distance', ascending = True ).drop_duplicates( ['algorithm','Input'] ).sort_index()
        best_per_input_alg = best_per_input_alg.sort_values( ['Input', 'distance'] )
        
        if best_per_input_alg['distance'].isna().sum() > 0:
            distnan = best_per_input_alg['distance'].isna()
            print( distnan.sum(), 'NaN distances caused by', set( best_per_input_alg[distnan].algorithm ) )
        
        
        alg_images = {}
        for index, row in best_per_input_alg.iterrows():
            img_input_id =  row['Input']
            img_alg = row['algorithm']
        
            if not img_input_id in alg_images.keys():
                alg_images[img_input_id] = {}
            if not img_alg in alg_images[img_input_id].keys():
                alg_images[img_input_id][img_alg] = {}
                
            alg_images[img_input_id][img_alg]=row

        key = metric
        if parameter != '':
            key += f' {parameter}'
            
        ret[key] = alg_images
    return ret



###########################################################################
################## data access func, generate specific html ###############
###########################################################################
###########################################################################


## Make a symbolic link from "GT" to the real location "SSEB_Data-Set/SSEB_Data-set_Benchmark/GT"
## if suffix='' get all GT images.
def get_GTs( name, suffix ):
    image_paths = sorted(Path(path_to_GT_images).glob( '_'.join( os.path.splitext( name )[0].split('_')[:4] ) + '*' + suffix ))
    return image_paths


def get_rough(input_id, input_type=None):
    if input_type is None:
        input_type='original'
    image_desc = rough_images_desc[input_id][input_type]
    if image_desc['vector']:
        return f'{path_to_Rough_images}/{path_svg}/{image_desc["filename"]}.svg'
    else:
        # return f'{path_to_Rough_images}/{path_png}/{image_desc["filename"]}.png'
        return f'{path_to_Rough_images}/{path_jpg}/{image_desc["filename"]}.jpg'

def get_rough_thumb(input_id, input_type=None):
    if input_type is None:
        input_type='original'
        
    image_desc = rough_images_desc[input_id][input_type]
    if image_desc['vector']:
        return f'{path_to_Rough_images}/{path_svg}/{image_desc["filename"]}.svg'
    else:
        return f'{web_output}/thumbs/{image_desc["filename"]}.jpg'

def gt_cell(image_path, gallery, layer):
    return f'<td>'+img_gallery(image_path, image_path, gallery, f'{gallery}: {layer}')+'</td>'

def gt_rows(input_id, desc, with_id=True):
    ret = ''
    for artist, layers in desc.items():
        ret+='<tr>'
        if with_id: ret+=f'<td>{link_to_sketch_page(input_id)}</td>'
        ret+=f'<td>{artist}</td>'
        for gt_type in gt_types.keys():
      
            if gt_type in layers:
                ret+= gt_cell(desc[artist][gt_type], f'{input_id}_{artist}', gt_types[gt_type])
            else:
                ret += '<td></td>'
        ret+=f'</tr>{cr}'
    return ret

def gt_table_body(desc):
    ret= '<tbody>';

    for input_id, artists in desc.items():
        ret += gt_rows(input_id, artists)
        
    ret +='</tbody>'
    return ret

def gt_table_ths(with_id):
    ret=''
    if with_id: ret+='<th>sketch id</th>'
    ret+='<th>artist</th>'
    for input_type in gt_types.values():
        ret+=f'<th>{input_type}</th>'
    return ret

def gt_table_header(with_id=True):
    return f'<thead><tr>{gt_table_ths(with_id)}</tr><tr>{gt_table_ths(with_id)}</tr></thead>'

def gt_table_footer():
    return f'<tfoot><tr>{gt_table_ths()}</tr></tfoot>'

def gt_script():
    return Path(os.path.join(os.path.dirname(__file__), '../template/gt-script.html')).read_text()

def rough_table_image_ths():
    ret = '' 
    for input_type in input_types.values():
        ret+=f'<th>{input_type}</th>'
    return ret

def rough_table_ths():
    ret=''
    ret+='<th>Curated</th><th>sketch id</th>'
    #name
    ret+= rough_table_image_ths()
    return ret

def rough_table_header():
    return f'<thead><tr>{rough_table_ths()}</tr><tr>{rough_table_ths()}</tr></thead>'

def rough_table_footer():
    return f'<tfoot><tr>{rough_table_ths()}</tr></tfoot>'

def rough_table_cell(f, input_type, key):
    ret='';
    if input_type in f:
        if  f[input_type]['vector']:
            ret+=rough_table_cell_vector(f, input_type, key)
        else:
            ret+=rough_table_cell_bitmap(f, input_type, key)
    else:
        ret+='<td></td>'
    return ret


def rough_table_cell_bitmap(f, input_type, key):
    return '<td>'+img_gallery(get_rough(key, input_type), get_rough_thumb(key, input_type), key, f'{key}: {input_types[input_type]}')+'</td>'

def rough_table_cell_vector(f, input_type, key):    
    return '<td>'+img_gallery(get_rough(key, input_type),  get_rough_thumb(key, input_type), key, f'{key}: {input_types[input_type]}')+'</td>'

def rough_table_image_cells(image_desc, key):
    ret = ''
    for input_type in input_types.keys():
        ret+=rough_table_cell(image_desc, input_type, key)
    return ret
        
def rough_table_row(image_desc, key):
    ret ='<tr>';
    ret += f'<td>{image_desc["curated"]}</td>'
    ret += f'<td>{link_to_sketch_page(key)}</td>'
    ret += rough_table_image_cells(image_desc, key)
    ret +=f'</tr>{cr}'
    return ret
        
def rough_table_body(rough_images_desc):
    ret='<tbody>'
    for key in rough_images_desc:
        ret += rough_table_row(rough_images_desc[key], key)
    ret+='</tbody>'
    return ret

def gt_to_gt_table_body(data):
    ret= '<tbody>';
    
    def getid(x):
        filename, extension = os.path.splitext(x);
        return link_to_sketch_page(filename)
    data[['sketch id']] = data[['sketch id']].applymap(getid)

    for index, row in data.iterrows():
        ret+='<tr>'
        for val in row:
            ret += f'<td>{val}</td>'
        ret+=f'</tr>{cr}'
   
    ret +='</tbody>'
    return ret

def gt_to_gt_table_ths(data):
    ret=''
    columnsNamesArr = data.columns.values
    listOfColumnNames = list(columnsNamesArr)
    for name in listOfColumnNames:
        ret+= f'<th>{name}</th>'
    return ret

def gt_to_gt_table_header(data):
    return f'<thead><tr>{gt_to_gt_table_ths(data)}</tr><tr>{gt_to_gt_table_ths(data)}</tr></thead>'

def gt_to_gt_table_footer(data):
    return f'<tfoot><tr>{gt_to_gt_table_ths(data)}</tr></tfoot>'



def get_output_image_from_row( row ):
    missing_underscore = '_' if not row.input_variant.startswith('.') else ''
  
    ## Get both:
    image_stem = row.Input + missing_underscore + row.input_variant.split('.')[0]
    image_glob = image_stem + '.*'
    
    images = get_auto_images( image_glob, row.algorithm, row.parameter )
  
    if len( images ) == 0:
        return None
    else:
        return images[0]



def get_row_table_from_input_id(key, data, input_id):
    ret  = ""
    ret += f'<td>{link_to_sketch_page(input_id)}</td>'    
    for a in alg:
        data_lower = {k.lower(): v for k, v in data[input_id].items()}
        a = a.lower()
        if a in data_lower:
            image_path = get_output_image_from_row(data_lower[a])
            if image_path is not None:
                image_path = str(image_path)
                image_src = image_path
                image_src = get_auto_thumb_abspath(image_path)


                
                dist = data_lower[a]["distance"]
                variant = data_lower[a]["input_variant"]
                running_time = data_lower[a]["Running Time"]
                parameter = data_lower[a]["parameter"]
                
                ret+=f'<td>{dist}</td>'
                ret+='<td>'
                ret+=img_gallery(image_path, image_src, f'{input_id}-{key}', f'{input_id} {variant} {alg_display_name[a.lower()]}')
                ret+=f'<span class="label distance"><span class="info-title">distance:</span>&nbsp;{round(dist, 5)}</span>'
                ret+=f'<span class="label running_time"><span class="info-title">running-time:</span>&nbsp;{running_time}</span>'
                ret+=f'<span class="label variant"><span class="info-title">variant:</span>&nbsp;{variant_to_label[variant]}</span>'
                if alg_param_display_name[(a.lower(), parameter)] != '':
                    ret+=f'<span class="label parameter"><span class="info-title">alg. parameter:</span>&nbsp;{alg_param_display_name[(a.lower(), parameter)]}</span>'
                ret+='</td>'
            else:
                ret+= '<td></td><td></td>'
        else:
            ret+= '<td></td><td></td>'
    return ret

def auto_table_body(key, data):
    ret ='' 
    for input_id in data.keys():
        ret+= '<tr>'
        ret+= get_row_table_from_input_id(key, data, input_id)
        ret+= '</tr>'
    return ret

def auto_table_ths():
    ret='<th>sketch id</th>'
    for a in alg: 
        ret += f'<th>{alg_display_name[a.lower()]}</th>'
        ret += f'<th>{alg_display_name[a.lower()]}</th>'
    return ret
    
def auto_table_header():
    return f'<thead><tr>{auto_table_ths()}</tr><tr>{auto_table_ths()}</tr></thead>'


###########################################################################
###########  #  ###   ###   ###  ###  #####################################
########### # # ## ### ### #### # ## ######################################
########### ### ##     ### #### ## # ######################################
########### ### ## ### ##   ##  ###  ######################################
###########################################################################

#### GLOBALS ###############

rough_images_desc = []
gt_data = []
gt_images_desc =  []
auto_data = [] 
auto_images_desc = []
sketch_tags_data = []
alg_display_name = {}
alg2dir={}
alg_param_display_name ={}

def init_globals(dataset, auto, evaluation, out):
    '''
    '''
    global rough_images_desc
    global gt_data
    global gt_images_desc 
    global auto_data 
    global auto_images_desc 
    global sketch_tags_data
    global path_to_GT_images
    global path_to_Rough_images
    global path_to_Automatic_images
    global web_output
    global evaluation_dir
    global inpath
    global auto_inpath
    global sketch_tags_inpath
    global alg_param_display_name
    global alg_param_list
    global alg
    global alg_display_name
    global alg2dir
    
    path_to_GT_images = os.path.abspath(Path(dataset)/'GT')
    path_to_Rough_images = os.path.abspath(Path(dataset)/'Rough')
    path_to_Automatic_images = os.path.abspath(auto)
    
    evaluation_dir = Path(evaluation)
    inpath = evaluation_dir / "GT_to_GT.csv"
    auto_inpath = evaluation_dir / "Auto_to_GT.csv"
    #auto_inpath = "AutoTest.csv"
    sketch_tags_inpath= Path(dataset) / 'sketch_tags.csv'

    web_output =os.path.abspath( out )


    print("*** config ***")
    print(path_to_Automatic_images)
    print(web_output)
    print(os.path.relpath(path_to_Automatic_images, web_output))
              
    rough_images_desc = init_rough_images_desc()
    gt_data = init_gt_data()
    gt_images_desc = init_gt_images_desc(gt_data)
    auto_data = init_auto_images_data()
    auto_images_desc = init_auto_images_desc(auto_data)
    sketch_tags_data = init_sketch_tags()
    
    alg_scan = scan_algs(path_to_Automatic_images)

    # get alg list
    alg = alg_scan['alg_list']

    # predefine and update alg display name
    alg_display_name = {
        # 'fidelitysimplicity': 'Fidelity Simplicity',
        # 'masteringsketching': 'Mastering Sketching',
        # 'polyvector': 'Poly Vector',
        # 'strokeaggregator': 'Stroke Aggregator',
        # 'topologydriven': 'Topology Driven',
        # 'polyvector2strokeaggregator':'Poly Vector → Stroke Aggregator',
        # 'topologydriven2strokeaggregator':'Topology Driven → Stroke Aggregator',
        # 'delaunaytriangulation':'Delaunay Triangulation',
        # 'realtimeinking':'Real-Time Inking',
    }

    for key in alg:
        if key.lower() not in alg_display_name:
            alg_display_name[key.lower()] = key

    # predefine and update alg parameter display name
    alg_param_display_name ={
        # ('delaunaytriangulation', 'dl4dle4m40p30s60'):'',
        # ('fidelitysimplicity', 'w0l0.25dt0.999995'):'0.25',
        # ('fidelitysimplicity', 'w0l0.3dt0.999995'):'0.3',
        # ('fidelitysimplicity', 'w0l0.5dt0.999995'):'0.5',
        # ('fidelitysimplicity', 'w0l0.6dt0.999995'):'0.6',
        # ('fidelitysimplicity', 'w0l0.75dt0.999995'):'0.75',
        # ('masteringsketching', 'gan'):'',
        # ('polyvector2strokeaggregator', 'noisy'):'noisy',
        # ('polyvector2strokeaggregator', 'none'):'',
        # ('polyvector', 'noisy'):'noisy',
        # ('polyvector', 'none'):'',
        # ('realtimeinking', 'none'):'',
        # ('strokeaggregator', 'none'):'',
        # ('topologydriven2strokeaggregator', 'none'):'',
        # ('topologydriven', 'none'):''
        }
    alg_scan.pop("alg_list")

    for key in alg_scan:
        for p, ppath in alg_scan[key]['parameter']:
            if (key.lower(), p) not in alg_param_display_name:
                ## If the parameter is "none", then make it blank.
                alg_param_display_name[(key.lower(), p)] = ( p if p != 'none' else '' )

    # update alg parameter list
    #from  generate_alg_param_list() 
    alg_param_list = []

    for key in alg_scan:
        for p, ppath in alg_scan[key]['parameter']:
            alg_param_list.append((key, p))

    alg2dir = {}
    for key in alg_scan:
        alg2dir[key.lower()] = alg_scan[key]['folder']

def generate_pages():

    page_id = 0  
    html_file = open(f'{web_output}/{pages[page_id]["url"]}', "w");
    html_file.write(rough_header())
    html_file.write("<body>")

    html_file.write(header_and_nav(page_id))
    
    html_file.write(f'<div class="row {row_base_class}">')
    html_file.write('<div class="col">')
    html_file.write(controls(True))
    html_file.write(end_div()) #col
    html_file.write(end_div()) #row
    
    html_file.write(table(rough_table_header(), rough_table_body(rough_images_desc)))
    html_file.write(end_div())
    html_file.write(script(pages[page_id]['id']))
    html_file.write('</body></html>')
    html_file.close()
    
    page_id += 1
    
    html_file = open(f'{web_output}/{pages[page_id]["url"]}', "w");
    html_file.write(rough_header())
    html_file.write("<body>")
    
    html_file.write(header_and_nav( page_id))
    
    html_file.write(f'<div class="row {row_base_class}">')
    html_file.write('<div class="col">')
    html_file.write(controls(True))
    html_file.write(end_div()) #col
    html_file.write(end_div()) #row
    
    html_file.write(table(gt_table_header(), gt_table_body(gt_images_desc)))
    html_file.write(end_div())
    html_file.write(script(pages[page_id]['id']))
    html_file.write('</body></html>')
    
    html_file.close()
    
    
    page_id += 1    
    html_file = open(f'{web_output}/{pages[page_id]["url"]}',"w")
    html_file.write(rough_header())
    html_file.write("<body>")
    
    html_file.write(header_and_nav(page_id))
    
    html_file.write(f'<div class="row {row_base_class}">')
    html_file.write('<div class="col col-xl-2 col-12">')
    html_file.write(controls(True))
    html_file.write(end_div()) #col
    html_file.write(chart_div("col col-12 col-xl-5 col-lg-6", "myChart"))
    html_file.write(chart_div("col col-12 col-xl-5 col-lg-6", "chart-messiness_to_distance"))
    html_file.write(end_div()) #row
    html_file.write(table(gt_to_gt_table_header(gt_data), gt_to_gt_table_body(gt_data)))
    html_file.write(end_div())
    html_file.write(script(pages[page_id]['id']))
    html_file.write('</body></html>')
    html_file.close()

    page_id += 1

    html_file =  open(f'{web_output}/{pages[page_id]["url"]}',"w")
    html_file.write(rough_header())
    html_file.write('<body>')
    
    html_file.write(header_and_nav(page_id))
    
    html_file.write(f'<div class="row {row_base_class}">')
    html_file.write('<div class="col">')
    html_file.write(begin_controls())
      
    html_file.write(distance_combo(auto_images_desc.keys()));
    html_file.write(controls_toggles())
    html_file.write(controls_labels())

    html_file.write(end_controls())
    html_file.write(end_div()) #col
    html_file.write(chart_div("col col-12 col-lg-8 col-xl-7", "myChart"))
    html_file.write(end_div()) #row

    for key, value in auto_images_desc.items():
        key=key.replace('.','_');
        html_file.write(begin_div(idtag=f'wrapper-{key}'))
        html_file.write(f'<h3>{key}</h3>')
        html_file.write(table(auto_table_header(), auto_table_body(key, value), key))
        html_file.write(end_div())
        
    html_file.write(end_div()) #container
    html_file.write(script(pages[page_id]['id']))
    html_file.write('</body></html>')
    html_file.close()
    ######
    ##

    page_id += 1

    html_file =  open(f'{web_output}/{pages[page_id]["url"]}',"w")
    html_file.write((f'<!doctype html>{cr}'
                     '<html lang="en">'
                     '  <head>'
                     '    <!-- Required meta tags -->'
                     '    <meta charset="utf-8">'
                     '    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">'
                     '    <title>A Benchmark for Rough Sketch Cleanup</title>'
                     '    <link rel="stylesheet" type="text/css" href="./pkg/node_modules/bootstrap/dist/css/bootstrap.min.css" />'
                     '    <link rel="stylesheet" type="text/css" href="./css/style.css" />'
                     '    <script src="./pkg/node_modules/jquery/dist/jquery.min.js"></script>'
                     '    <script src="./pkg/node_modules/popper.js/dist/umd/popper.min.js"></script>'
                     '    <script src="./pkg/node_modules/bootstrap/dist/js/bootstrap.min.js" ></script>'
                     '    <script src="./pkg/node_modules/citation-js/build/citation.js"></script>'
                     '  </head>'))
    html_file.write("<body>")
    html_file.write(header_and_nav(page_id))

    html_file.write(begin_div('container'))

    html_file.write(('<div class="alert alert-danger" role="alert" id="js_gate">'
                     'You must have JavaScript enabled.'
                     '</div>'))

    html_file.write(f'<div class="row {row_base_class}">')
    html_file.write('<div class="col">')

    html_file.write(Path(os.path.join(os.path.dirname(__file__),'../template/index.html')).read_text())
    html_file.write('<ul id="bibtex_out"></ul>')
    html_file.write('<div id="bibtex_in" style="display:none;">')
    html_file.write(Path(os.path.join(os.path.dirname(__file__),'../template/bib.bib')).read_text())
    html_file.write(end_div())
    html_file.write(end_div()) #col
    html_file.write(end_div()) #row
    
    html_file.write(("""
<script>
// $('#js_gate').removeClass("alert-danger").addClass("alert-primary");
$('#js_gate').remove();

var entry_to_disp={'favreau_fidelity_2016':'Fidelity Simplicity',
	    'liu_strokeaggregator:_2018':'Stroke Aggregator',
	    'parakkat_delaunay_2018':'Delaunay Triangulation',
	    'simo-serra_mastering_2018':'Mastering Sketching',
	    'SimoSerraSIGGRAPH2018':'Real-Time Inking',
	    'bessmeltsev_vectorization_2019':'Poly Vector',
	    'noris_topology-driven_2013':'Topology Driven'};
const Cite = require('citation-js');
var cite = new Cite($(bibtex_in).html());
var opt = {format: 'string'};
$('#bibtex_out').html(cite.format('bibliography', {prepend (entry) { return `<li><span class=\"info-title\">${entry_to_disp[entry.id]}: </span>` }, append() { return '</li>'; },
 format: 'html',
 template: 'apa',
 lang: 'en-US'
}));
</script>
"""))

    html_file.write('</body></html>')
    html_file.close()
    


    
def get_sketch_info(input_id, sketch_tags):
    info=' <br/>'
    author = ''
    if sketch_tags['Preferred Attribution'] == '':
        author= sketch_tags['Author']
    else:
        author = f'{sketch_tags["Preferred Attribution"]} (aka {sketch_tags["Author"]})'
    info += f'<h2>{input_id}</h2><span class="artist"><span class="info-title">Author:</span> {author}</span> '
    
   # if sketch_tags['Author Email'] != '':
   #     info += f'<span class="email"><span class="info-title">Author Email:</span> <a mailto="{sketch_tags["Author Email"]}">{sketch_tags["Author Email"]}</a></span> '

    if sketch_tags['Author Homepage'] != '':
        info += f'<span class="www"><span class="info-title">Author Homepage: </span> <a href="{sketch_tags["Author Homepage"]}">{sketch_tags["Author Homepage"]}</a></span> '

    if sketch_tags['Copyright'] != '':
        info += f'<span class="licence"><span class="info-title">Licence: </span> {sketch_tags["Copyright"]}</span> '
    else:
        print(f'Warning {input_id} has no copyright')

        
    tags=''

    if not np.isnan(sketch_tags["Messiness"]):
        tags += f'<div class="pr-3 d-inline-flex stats"><span class="info-title">Messiness:</span> &nbsp;{round(sketch_tags["Messiness"], 5)}</div> '

    if not np.isnan(sketch_tags["Ambiguity (Chamfer)"]):
        tags  += f'<div class="pr-3 d-inline-flex stats"><span class="info-title">Ambiguity (Chamfer):</span> &nbsp;{round(sketch_tags["Ambiguity (Chamfer)"], 5)}</div> '

    for key in ['Shading', 'Scaffold', 'Texture Strokes', 'Background']:    
        if sketch_tags[key] != '' :
            tags+=f'<div class="pr-3 d-inline-flex stats"><span class="info-title">{key}:</span> &nbsp;{sketch_tags[key]}</div> '

    info += tags
    return info
    
######################## SKETCH PAGES

def gt_ranking_rows(input_id):
    ret = ''
    for artist, layers in gt_images_desc[input_id].items():
        gt_type='norm_cleaned'
        if gt_type in layers:
            ret+= gt_cell(gt_images_desc[input_id][artist][gt_type], f'ranking', 'norm_cleaned')
        else:
            ret += '<td></td>'
    return ret



def get_auto_image_table_ranking(input_id, data):
    
    df = data.sort_values( 'distance', ascending = True ).drop_duplicates( ['algorithm','Input'] )

    #ths='<tr><th>algorithm</th><th>distance</th><th>result</th><th>running time</th>'
    #ths+='</tr>'
    # header =f'<thead>{ths}</thead>{cr}'
    header=''
    body=''
    #body+=f'<td>{alg_display_name[row.algorithm]}</td>'
    
    save_ranking = False
    if save_ranking:
        ranking_dir = Path(evaluation_dir) / 'ranking'
        if not ranking_dir.is_dir(): os.makedirs( ranking_dir )
        ranking_file = open(ranking_dir / f'{input_id}.txt',"w")

    for row in df.itertuples():
        cell=''
        image_path = get_output_image_from_row(row)
        if image_path is not None:
            header+=f'<th>{alg_display_name[row.algorithm.lower()]}</th>'
            image_path = str(image_path)
            image_src = get_auto_thumb_abspath(image_path)

            dist = row.distance
            variant = row.input_variant
            if save_ranking: ranking_file.write(f'{dist} \t {alg_display_name[row.algorithm.lower()]} \t {image_path}\n')

            cell+=img_gallery(image_path, image_src, f'ranking', f'{alg_display_name[row.algorithm.lower()]}')
            cell+=f'<span class="label distance"><span class="info-title">distance:</span>&nbsp;{round(row.distance, 5)}</span>'
            #cell+=f'<span class="label running_time">running-time:&nbsp;{row._8}</span>'
    #        cell+=f'<span class="label variant"><span class="info-title">variant:</span>&nbsp;{variant_to_label[row.input_variant]}</span>'
     #       if alg_param_display_name[(row.algorithm, row.parameter)] != '':
     #           cell+=f'<span class="label parameter"><span class="info-title">alg. parameter:</span>&nbsp;{alg_param_display_name[(row.algorithm, row.parameter)]}</span>'
            body+=f'<td>{cell}</td>'
    if save_ranking: ranking_file.close()
    return header, body



#note ready yet
def get_table_ranking(input_id, df):
    header=f'<thead><tr><th>Original</th><th colspan="3">Ground Truth</th>'
    body='<tbody><tr>'

    body+= rough_table_cell(rough_images_desc[input_id], 'original', input_id)
    body+= gt_ranking_rows(input_id)
        
    metric='Chamfer'
    parameter=''
    sparam = str(parameter) if parameter != 'none' else ''
    key = metric + sparam
    key = key.replace('.','_');

    data = df[ (df['metric_name'] == metric) & (df['metric_parameter'] == parameter) ]

    header2, body2 = get_auto_image_table_ranking(input_id, data)

    header+=header2
    header+='</tr></thead>'
    body+=body2
    body+=f'</tr></tbody>{cr}'
      
    return header, body


def image_page(input_id):
    sketch_tags = sketch_tags_data.loc[input_id]
    
    html_file =  open(f'{web_output}/{input_id}.html',"w")
    html_file.write(rough_header())
    html_file.write('<body>')
    
    html_file.write(header_and_nav_sketch_page())
    
    html_file.write(begin_div(name="row mt-3 justify-content-md-center"))
    html_file.write(begin_div(name="col"))
    html_file.write(begin_div(name="card-group"))
    html_file.write(begin_div(name="card"))
    html_file.write(begin_div(name="card-body"))
    # html_file.write('<h1 class="card-title">Image information</h1>')
    html_file.write(get_sketch_info(input_id, sketch_tags))
    html_file.write(end_div())
    html_file.write(end_div())
    
    html_file.write(begin_div(name="card col-12 col-md-4"))
    html_file.write(begin_div(name="card-body text-center"))

    #    html_file.write(begin_div(name="col-12 col-md-4"))
    rel_src=os.path.relpath(get_rough(input_id), web_output)
    html_file.write(f'<img src="{rel_src}" class="img-fluid rough-preview" alt="rough image"  />{cr}')
    #    html_file.write(end_div())

    html_file.write(end_div())
    html_file.write(end_div())

    html_file.write(end_div())
    
    html_file.write(end_div())
    html_file.write(f'<hr/></div>{cr}')

    
    if sketch_tags['Cleaned'] == 'Yes':

        df = auto_data.loc[auto_data['Input'] == input_id]
        df = df.drop(['genre', 'cleaner'], axis=1)
    

    #### ranking
        html_file.write(image_controls('Best automatic results (chamfer distance)', 'ranking'))
        html_file.write(begin_div(name=f'row {row_base_class}'))
        html_file.write(begin_div(name="col"))
        
        html_file.write('<h2>Best automatic results</h2>')

        header, body = get_table_ranking(input_id, df)
        html_file.write(table(header, body, 'ranking'))
        html_file.write(end_div())
        html_file.write(end_div())

    ###########
        
        html_file.write(image_controls('Rough Sketch', 'rough'))


        html_file.write(table(f'<thead><tr>{rough_table_image_ths()}</tr></thead>',
                              '<tbody><tr>'+
                              rough_table_image_cells(rough_images_desc[input_id], input_id)+
                              f'</tr></tbody>{cr}','rough'))

        html_file.write(image_controls('Ground Truth', 'gt'))
        html_file.write(table(f'<thead><tr>{gt_table_ths(False)}</tr></thead>',
                              f'<tbody>{cr}'+
                              gt_rows(input_id, gt_images_desc[input_id], False)+
                              f'</tbody>{cr}', 'gt'))

        html_file.write(f'<div class="row {row_base_class}">')
        html_file.write('<div class="col">')
        html_file.write('<h3>Automatic results, best result per algorithm</h3>')
        html_file.write(begin_controls())

        html_file.write(distance_combo(auto_images_desc.keys()));

        html_file.write(controls_toggles('autoBest'))
        html_file.write(controls_labels('autoBest'))

        html_file.write(end_controls())
        html_file.write(end_div()) #col
        html_file.write(end_div()) #row
        
        for metric, parameter in mlist:
            sparam = str(parameter) if parameter != 'none' else ''
            key = metric + sparam
            key = key.replace('.','_');
            html_file.write(begin_div(idtag=f'wrapper-{key}'))
            html_file.write(f'<h3>{key}</h3>')
            data = df[ (df['metric_name'] == metric) & (df['metric_parameter'] == parameter) ]
            header, body = get_auto_image_table2(input_id, data)
            html_file.write(table(header, body, f'{key}', tableclass='autoBestTable'))
            html_file.write(end_div())

            
        html_file.write(image_controls('Automatic results for each input variant','auto'))
        header, body =  get_sketch_all_table(auto_data, input_id)
        html_file.write(table(header, body,'auto'))

        #df = get_auto_image_desc(auto_data, input_id)
        #html_file.write('<h3>Automatic results distances to ground truth</h3>')
        #html_file.write(image_controls('dist'))
        #header, body = get_auto_image_distance_table(df)
        #html_file.write(table(header, body, 'dist'))

    html_file.write(end_div()) #container

    html_file.write(script('sketch'))
    html_file.write(f'{cr}</body>{cr}</html>{cr}')
    html_file.close()



def generate_sketch_pages():
    ## TODO: To turn this back on, we need to set our global variables
    ##       properly for each image.
    use_multiprocessing = True
    if use_multiprocessing:
        print("Generate sketch pages using", os.cpu_count(), "threads")
        with Pool() as p:
            input_ids = sketch_tags_data.index.tolist()
            for _ in tqdm(p.imap_unordered(image_page, input_ids, 5), total=len(input_ids)):
                pass
    else:
        print("Generate sketch pages using main thread")
        for input_id in tqdm( sketch_tags_data.index.tolist() ): image_page( input_id )

            
### MAIN CALLS
#print(generate_alg_param_list())
#print(generate_input_variant_list())
if __name__ == '__main__':
    init_globals("../../data/Benchmark_Dataset/", "../../data/Automatic_Results/", "../../generated/Evaluation_Data/", "../output/")
    generate_pages()
    if len(sys.argv) == 1:
        ## Disable use_multiprocessing for profiling or debugging:
        # use_multiprocessing = False
        generate_sketch_pages()
    else:
        input_id = "Art_freeform_AG_02"
        print("generate only",input_id)
        image_page(input_id)
else:
    with open("cfg.yaml", 'r') as f:
        config = yaml.safe_load(f)
        init_globals(config['dataset_dir'], config['alg_dir'], config['table_dir'], config['web_dir'])
