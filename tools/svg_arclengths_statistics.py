from __future__ import print_function, division

from svgpathtools import Document, svg2paths
from numpy import allclose
import pdb

def arc_length_statistics( path_to_svg ):
    '''
    Given:
        path_to_svg: A path to an SVG file.
    
    Normalizes by the svg's long edge as defined by its viewBox.
    
    Ignores <svg> width or height attributes.
    '''
    flatpaths = None
    paths = None
    try:
        doc = Document( path_to_svg )
        flatpaths = doc.flatten_all_paths()
    except:
        paths, _ = svg2paths (path_to_svg)
        flatpaths = paths

    ## Absolute distances
    lengths = []
    for path in flatpaths:
        total_path_length = 0.
        last_pt = None
        # if this is get by flatten_all_paths, then we just need to get the first item
        if paths == None:
            path =  path[0]
        for seg in path:
            ## Make sure this segment is connected to the previous one.
            ## If not, start a new one.
            ## I checked and it doesn't look like svgpathtools tells us when a Move
            ## command happens, so we have to figure it out.
            if not( last_pt is None or allclose( last_pt, seg.point(0) ) ):
                lengths.append( total_path_length )
                total_path_length = 0.
            
            ## Add the current segment to the running tally.
            total_path_length += seg.length()
            last_pt = seg.point(1)
        
        lengths.append( total_path_length )
    
    ## Divide by long edge.
    if 'viewBox' in doc.root.attrib:
        import re
        _, _, width, height = [ float(v) for v in re.split( '[ ,]+', doc.root.attrib['viewBox'].strip() ) ]
        long_edge = max( width, height )
        print( "Normalizing by long edge:", long_edge )
        lengths = [ l/long_edge for l in lengths ]
    elif "width" in doc.root.attrib and "height" in doc.root.attrib:
        width = doc.root.attrib["width"].strip().strip("px")
        height = doc.root.attrib["height"].strip().strip("px")
        long_edge = max( float(width), float(height) )
        print( "Normalizing by long edge:", long_edge )
        lengths = [ l/long_edge for l in lengths ]
    else:
        print( "WARNING: No viewBox found in <svg>. Not normalizing by long edge." )
    print("Done")
    return lengths

def analyze_lengths( lengths ):
    from numpy import mean, median, percentile
    
    print( "mean:", mean( lengths ) )
    print( "min (0-th percentile):", min( lengths ) )
    ## Same:
    # print( "min (0-th percentile):", percentile( lengths, 0 ) )
    print( "25-th percentile", percentile( lengths, 25 ) )
    print( "median (50-th percentile):", median( lengths ) )
    ## Same:
    # print( "median (50-th percentile):", percentile( lengths, 50 ) )
    print( "75-th percentile", percentile( lengths, 75 ) )
    print( "max (100-th percentile):", max( lengths ) )
    ## Same:
    # print( "max (100-th percentile):", percentile( lengths, 100 ) )
    
    ## TODO: print/plot a histogram.

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser( description = "Print statistics on an SVG file's path lengths." )
    parser.add_argument( "path_to_svg", help = "The SVG file to analyze." )
    parser.add_argument( "--print-num-strokes", help = "If set, prints the number of strokes.", action="store_true" )
    args = parser.parse_args()
    
    lengths = arc_length_statistics( args.path_to_svg )
    if args.print-num-strokes: print( "Number of strokes:", len( lengths ) )
    analyze_lengths( lengths )
