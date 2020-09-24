from __future__ import print_function, division

import pandas as pd
from pprint import pprint

def load_Auto_to_GT_polished_and_melted( paths ):
    import os
    
    # data = pd.read_csv( inpath )
    dataframes = []
    columns2filename = {}
    for path in paths:
        print( "Loading:", path )
        ## Preserve F-measure N/A for this script so we can compute failure rate.
        ## To do that, read as string.
        df = pd.read_csv( path, dtype = str, na_values = [], keep_default_na = False )
        
        ## Add the filename as a column.
        ## paths may be strings, so let's use os.
        # basename = path.name
        basename = os.path.basename( path )
        ## Add the new column at position 0 so it's the first column.
        # df['source'] = basename
        df.insert( 0, 'source', basename )
        
        ## Drop any cleanup_rate columns.
        df = df.drop( columns = [ col for col in df.columns if col.endswith('_cleanup_rate') ] )
        
        dataframes.append( df )
        
        columns2filename.setdefault( tuple( df.columns.tolist() ), [] ).append( basename )
    
    if len( columns2filename ) != 1:
        print( "Columns not identical:" )
        pprint( columns2filename )
        print( "Different columns follow this distribution:", [ len( v ) for v in columns2filename.values() ] )
    
    print( "Concatenating." )
    data = pd.concat( dataframes )
    del dataframes
    # data.to_csv( outpath, index = False )
    # data.columns
    
    print( "Polishing columns." )
    ## Add useful columns:
    # Input_fixed = [ name.replace( 'bk_Manga', 'freeform' ).replace( 'bk_manga', 'freeform' ).replace( 'bk_comic', 'freeform' ) for name in data['Input'] ]
    ## No need to do the above anymore.
    Input_fixed = data['Input'].tolist()
    data['Input'] = [ '_'.join( os.path.splitext(name)[0].split('_')[:4] ) for name in Input_fixed ]
    
    artist = [ name.split('_')[2] for name in Input_fixed ]
    data.insert( 1, 'artist', artist )
    
    genre = [ name.split('_')[1] for name in Input_fixed ]
    data.insert( 2, 'genre', genre )
    
    input_variant = [ '_'.join( os.path.splitext(name)[0].split('_')[4:] ) + os.path.splitext(name)[1] for name in Input_fixed ]
    data.insert( 3, 'input_variant', input_variant )
    ## UPDATE: The vectorization+cleanup pipelines has .svg
    ##         as the suffix. But the true pipeline input is still .png,
    ##         so let's put them back.
    data.loc[ data['source'].str.contains('2StrokeAggregator'), 'input_variant' ] = data[ data['source'].str.contains('2StrokeAggregator') ]['input_variant'].str.rsplit('.',n=1).str.get(0) + '.png'
    
    # [ os.path.splitext(v)[0] + '.png' for v in input_variant ]
    
    data.insert( 4, 'input_category', input_variant )
    category2variant = {
            'original': [ '.png' ],
            'thresholded': [ 'cb.png','cb_500.png','cb_1000.png','500.png','1000.png' ],
            'vectorized': [ 'norm_full_1000.png', 'norm_full_500.png', 'norm_full.svg' ],
            'vectorized shape only': [ 'norm_rough_1000.png', 'norm_rough_500.png', 'norm_rough.svg' ]
            }
    for category, variant in category2variant.items():
        data.loc[ data['input_variant'].isin( variant ), 'input_category' ] = category
    # data.loc[ data['input_variant'].str.contains('full layers'), 'input_category' ] = 'vectorized'
    # data.loc[ data['input_variant'].str.contains('cb'), 'input_category' ] = 'thresholded'
    # data.loc[ data['input_variant'].isin([ '','500','1000' ]), 'input_category' ] = 'original'
    if frozenset( data.input_category ) != frozenset( category2variant.keys() ):
        print( "Data is missing some categories:", frozenset( data.input_category ) ^ frozenset( category2variant.keys() ) )
    
    algorithm = [ name.replace('.csv','')[len('Auto_to_GT_'):] for name in data['source'] ]
    data.insert( 5, 'algorithm', algorithm )
    
    ## Only one split, since some algorithm parameters themselves have an underscore.
    data.insert( 6, 'parameter', data['algorithm'].str.split('_',n=1).str.get(1) )
    data['algorithm'] = data['algorithm'].str.split('_',n=1).str.get(0)
    
    print( "Found the following algorithms and parameters:" )
    for alg in set( data.algorithm ): print( f"{alg}:", set( data[ data.algorithm == alg ].parameter ) )
    
    ## Rename "Used time" to "Running Time"
    data = data.rename( columns = { "Used time": "Running Time" } )
    
    print( "Melting." )
    data = pd.melt( data, id_vars = [ "source", "artist", "genre", "input_variant", "input_category", "algorithm", "parameter", "Input", "Running Time" ], var_name = "metric_parameter", value_name = "distance" )
                # .drop(['variable'],axis=1).sort_values('Quarter')
    
    ## Drop rows with empty F-measures.
    ## Don't drop N/A, which means failure. We load all columns as strings,
    ## so N/A won't be dropped.
    data = data[ data['distance'] != '' ]
    
    print( "Polishing melted columns." )
    data['cleaner'] = data['metric_parameter'].str.split('_').str.get(0)
    data['metric_parameter'] = data['metric_parameter'].str.split('_').str.get(1)
    ## Make a new 'metric' column
    # data['metric'] = 'F-score'
    ## UPDATE: Make the new 'metric' column before to 'metric_parameter'
    data.insert( data.columns.get_loc( 'metric_parameter' ), 'metric_name', 'F-score' )
    data.loc[ data['metric_parameter'] == 'chamfer', 'metric_name' ] = 'Chamfer'
    data.loc[ data['metric_parameter'] == 'hausdorff', 'metric_name' ] = 'Hausdorff'
    
    ## Clear the parameters for hausdorff and chamfer
    data.loc[ data['metric_parameter'] == 'hausdorff', 'metric_parameter' ] = ''
    data.loc[ data['metric_parameter'] == 'chamfer', 'metric_parameter' ] = ''
    
    return data


def load(inpaths, outpath):
    ## Merge CSV via: https://stackoverflow.com/questions/56882725/python-pandas-combine-csvs-and-add-filename/56883447#56883447
    
    # Only regenerate if any input is newer than the output.
    # mtime returns seconds since an absolute time in the past.
    import os.path
    if os.path.exists(outpath):
        output_mtime = os.path.getmtime(outpath)
        if all([ os.path.getmtime(path) < output_mtime for path in inpaths ]):
            print( "Melted data up-to-date, not regenerating:", outpath )
            return
    
    data = load_Auto_to_GT_polished_and_melted( inpaths )
    
    ## Save the file
    print( "Saving:", outpath )
    data.to_csv( outpath, index = False )
    print( "... Saved." )

def main():
    from pathlib import Path
    
    # inpaths = ["merged.csv"]
    #inpaths = sorted(Path('Auto_to_GT').glob('Auto_to_GT*Aggre*.csv'))
    #inpaths = inpaths + sorted(Path('Auto_to_GT').glob('Auto_to_GT*Mast*.csv'))
    #inpaths.sort()
    load_as_melted(sorted(Path('./Evaluation_Data/Auto_to_GT').glob('Auto_to_GT*.csv')),  "./Evaluation_Data/Auto_to_GT.csv")

if __name__ == '__main__': main()
