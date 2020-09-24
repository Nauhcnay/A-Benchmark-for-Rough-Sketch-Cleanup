from __future__ import print_function, division

import pandas as pd
from pprint import pprint

def load_vector_quality( paths ):
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
        # df['algorithm'] = basename
        df.insert( 0, 'algorithm', basename )
        
        dataframes.append( df )
    
    print( "Concatenating." )
    data = pd.concat( dataframes )
    del dataframes
    
    print( "Polishing columns." )
    ## Add useful columns:
    sketch = data['sketch'].tolist()
    # data['sketch'] = [ '_'.join( os.path.splitext(name)[0].split('_')[:4] ) for name in sketch ]
    
    artist = [ name.split('_')[2] for name in sketch ]
    data.insert( 2, 'artist', artist )
    
    genre = [ name.split('_')[1] for name in sketch ]
    data.insert( 3, 'genre', genre )
    
    input_variant = [ '_'.join( os.path.splitext(name)[0].split('_')[4:] ) + os.path.splitext(name)[1] for name in sketch ]
    data.insert( 4, 'input_variant', input_variant )
    
    # [ os.path.splitext(v)[0] + '.png' for v in input_variant ]
    
    data.insert( 5, 'input_category', input_variant )
    category2variant = {
            'original': [ '.svg' ],
            'thresholded': [ 'cb.svg','cb_500.svg','cb_1000.svg','500.svg','1000.svg' ],
            'vectorized': [ 'norm_full_1000.svg', 'norm_full_500.svg', 'norm_full.svg' ],
            'vectorized shape only': [ 'norm_rough_1000.svg', 'norm_rough_500.svg', 'norm_rough.svg' ]
            }
    for category, variant in category2variant.items():
        data.loc[ data['input_variant'].isin( variant ), 'input_category' ] = category
    # data.loc[ data['input_variant'].str.contains('full layers'), 'input_category' ] = 'vectorized'
    # data.loc[ data['input_variant'].str.contains('cb'), 'input_category' ] = 'thresholded'
    # data.loc[ data['input_variant'].isin([ '','500','1000' ]), 'input_category' ] = 'original'
    if frozenset( data.input_category ) != frozenset( category2variant.keys() ):
        print( "Data is missing some categories:", frozenset( data.input_category ) ^ frozenset( category2variant.keys() ) )
    
    algorithm = [ name.replace('.csv','') for name in data['algorithm'] ]
    data['algorithm'] = algorithm
    
    ## Only one split, since some algorithm parameters themselves have an underscore.
    data.insert( 1, 'parameter', data['algorithm'].str.split('_',n=1).str.get(1) )
    data['algorithm'] = data['algorithm'].str.split('_',n=1).str.get(0)
    
    print( "Found the following algorithms and parameters:" )
    for alg in set( data.algorithm ): print( f"{alg}:", set( data[ data.algorithm == alg ].parameter ) )
    
    return data

def load(inpaths, outpath):
    # Only regenerate if any input is newer than the output.
    # mtime returns seconds since an absolute time in the past.
    import os.path
    if os.path.exists(outpath):
        output_mtime = os.path.getmtime(outpath)
        if all([ os.path.getmtime(path) < output_mtime for path in inpaths ]):
            print( "Melted data up-to-date, not regenerating:", outpath )
            return
    
    data = load_vector_quality( inpaths, )
    
    ## Save the file
    print( "Saving:", outpath )
    data.to_csv( outpath, index = False )
    print( "... Saved." )


def main():
    ## Merge CSV via: https://stackoverflow.com/questions/56882725/python-pandas-combine-csvs-and-add-filename/56883447#56883447
    from pathlib import Path
    
    # inpaths = ["merged.csv"]
    inpaths = sorted(Path('./Evaluation_Data/Stroke_Analysis').glob('SA_*.csv'))
    outpath = "./Evaluation_Data/vector_quality.csv"
    load(inpaths, outpath)
    
if __name__ == '__main__': main()
