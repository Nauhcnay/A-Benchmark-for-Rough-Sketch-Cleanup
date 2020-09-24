## We could replace that script with:
from pathlib import Path
import subprocess
from tqdm import tqdm
import os
import multiprocessing

def create_one_thumbnail( inpath, outpath, convert_path, resize_geometry, quality, clobber ):
    # print( 'Thumbnailing:', inpath )
    if not clobber and Path(outpath).exists(): return
    subprocess.run([ convert_path, inpath, '-resize', resize_geometry, '-quality', quality, outpath ])

def create_one_thumbnail_wrapper( args ): return create_one_thumbnail( *args )

def create_thumbnails_recursive( input_paths, output_path_transformer, convert_path, resize_geometry, quality, clobber = False, parallel = True ):
    '''
    Given:
        input_paths: An iterator over images.
        output_path_transformer: A function taking a Path object and returning another Path object to use as the output path.
        convert_path: The path to the ImageMagick convert executable
        resize_geometry: The resize parameter to pass to ImageMagick, as in: convert -resize {resize_geometry}
        quality: The quality parameter to pass to ImageMagick, as in: convert -quality {quality}
        parallel: If True, calls ImageMagick in parallel, once per CPU core
    Returns:
        A dictionary mapping input paths to output paths.
    '''
    
    result = {}
    
    args = [
        ( inpath, output_path_transformer( inpath ), convert_path, resize_geometry, quality, clobber )
        for inpath in input_paths
        ]
    
    if parallel:
        with multiprocessing.Pool() as p:
            for _ in tqdm( p.imap_unordered( create_one_thumbnail_wrapper, args ), total = len( args ) ): pass
    else:
        for arg in tqdm(args): create_one_thumbnail( *arg )
    
    result = { arg[0]: arg[1] for arg in args }
    return result

if __name__ == '__main__':
    pass