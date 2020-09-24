import sys
import argparse
from PIL import Image
import matplotlib.pyplot as plt
from math import *
import numpy as np
import os
try:
    import metrics
    import files
except:
    from tools import metrics
    from tools import files

def getArgs():
    parser = argparse.ArgumentParser(description='Sketch evaluation 0.1')
    parser.add_argument("-i", "--input", help="The cleaned sketch file (raster format or SVG)")
    parser.add_argument("-gt", "--groundtruth", help="The corresponding groundtruth file (raster format or SVG)")
    parser.add_argument("--f-measure", action="store_true", help="If present, compute the f-measure.")
    parser.add_argument("--chamfer", action="store_true", help="If present, compute the Chamfer distance.")
    parser.add_argument("--hausdorff", action="store_true", help="If present, compute the Hausdorff distance.")
    parser.add_argument("-d", "--distance", action='append', type=float, required=True, help="The radius to dilate groundtruth when calculating precision & recall. Units: 1 means 1/1000 of the long edge.")
    parser.add_argument("-b", "--batch", help="Batch mode on if given a list of sketches", default=None)

    ## Note: type=bool does not do what we think it does. bool("False") == True.
    ## For more, see https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    def str2bool(s): return {'true': True, 'yes': True, 'false': False, 'no': False}[s.lower()]
    parser.add_argument('-p', type=str2bool, default=False, help='Whether to take the random subset after computing PCA. Default: False.')
    parser.add_argument("-v", "--visualize", type=str2bool, default=False, help="Whether to show the input and ground truth sketches. Default: False.")
    args = parser.parse_args()
    ## There is no way to have a default with 'append', so manually add one
    ## here.
    ## UPDATE: We'll make distance required.
    # if args.distance is None: args.distance = [0.]
    return args

def precompute(img_a, img_b, threshold = 0.25, visualize=None):
    ## Test is a, Ground Truth is b
    
    if visualize is None: visualize = False
    
    # get image size and length of diagonal
    f_scores = []
    assert(img_a.size == img_b.size)
    w, h = img_a.size
    print("size: %d x %d"%(w, h))
    
    if visualize: img_a.show()
    if visualize: img_b.show()

    diagonal_distance = sqrt(w**2 + h**2)
    bool_A = files.image_to_boolean_array(img_a, threshold)
    bool_B = files.image_to_boolean_array(img_b, threshold)
    
    if visualize: Image.fromarray( bool_A ).show()
    if visualize: Image.fromarray( bool_B ).show()
    
    # get distance from i to g and g to i
    if True not in bool_A or True not in bool_B:
        distances_i_to_g = 0
        distances_g_to_i = 0
    else:
        distances_i_to_g = metrics.find_closest_point_distances_for_images_boolean_fast( bool_A, bool_B )
        distances_g_to_i = metrics.find_closest_point_distances_for_images_boolean_fast( bool_B, bool_A )
    
    if visualize: Image.fromarray( ( distances_i_to_g.data/distances_i_to_g.data.max()*255. ).round().clip(0,255).astype( np.uint8 ) ).show()
    if visualize: Image.fromarray( ( distances_g_to_i.data/distances_g_to_i.data.max()*255. ).round().clip(0,255).astype( np.uint8 ) ).show()
    
    long_edge = w if w>h else h
    
    ## return precomputed things
    class Struct(object): pass
    precomputed = Struct()
    precomputed.long_edge = long_edge
    precomputed.distances_i_to_g = distances_i_to_g
    precomputed.distances_g_to_i = distances_g_to_i
    return precomputed

def get_f_measure(precomputed, distances, visualize=None):
    '''
    Given:
        precomputed: The return value of precompute()
        distances: A sequence of thresholds to use when computing the F-measure;
                   each is a distance cutoff as a per thousandth of the long edge
        visualize (optional): if True, show intermediate images (default False)
    Returns:
        f_scores: a list of f-measure scores for each distance in `distances`
    '''
    
    distances_i_to_g = precomputed.distances_i_to_g
    distances_g_to_i = precomputed.distances_g_to_i
    
    f_scores = []
    distance_base = precomputed.long_edge * 0.001  
    for d in distances:
        if visualize: print( "distance threshold:", distance_base * d )
        if type(distances_i_to_g) == int or type(distances_g_to_i) == int:
            f_scores.append("Blank Image")
        else:
            precision = ( distances_i_to_g <= distance_base * d ).sum() / distances_i_to_g.count()
            recall = ( distances_g_to_i <= distance_base * d ).sum() / distances_g_to_i.count()
            if precision + recall == 0.:
                assert precision == 0.
                assert recall == 0.
                f1 = 0.
            else:
                f1 = 2 * (precision * recall / (precision + recall))
            if visualize: print( "precision:", precision )
            if visualize: print( "recall:", recall )
            if visualize: print( "F-measure:", f1 )
            f_scores.append(f1)

    return f_scores

def get_chamfer_distance(precomputed, visualize=None):
    '''
    Given:
        precomputed: The return value of precompute()
        visualize (optional): if True, show intermediate images (default False)
    Returns:
        The Chamfer distance between the two images as a fraction of the long edge.
    '''
    distances_i_to_g = precomputed.distances_i_to_g
    distances_g_to_i = precomputed.distances_g_to_i
    long_edge = precomputed.long_edge
    
    '''
    Chamfer distance is:
        sum( DT(B)[ black_pixels( A ) ] ) / #( black_pixels( A ) )
    average A to B with B to A
    Chamfer distance units are pixel distances.
    We should divide by something to make it comparable between images.
    For example, divide by long edge length.
    '''
    if type(distances_i_to_g) == int or type(distances_g_to_i) == int:
        chamfer = "Blank Image"
    else:
        i_to_g = distances_i_to_g.sum() / distances_i_to_g.count()
        g_to_i = distances_g_to_i.sum() / distances_g_to_i.count()
        
        chamfer = ( i_to_g + g_to_i )/2
        ## Normalize by long edge
        chamfer /= long_edge
        if visualize: print( "chamfer:", chamfer )
    
    return chamfer

def get_hausdorff_distance(precomputed, visualize=None):
    '''
    Given:
        precomputed: The return value of precompute()
        visualize (optional): if True, show intermediate images (default False)
    Returns:
        The Hausdorff distance between the two images as a fraction of the long edge.
    '''
    
    distances_i_to_g = precomputed.distances_i_to_g
    distances_g_to_i = precomputed.distances_g_to_i
    long_edge = precomputed.long_edge
    
    '''
    Hausdorff distance is:
        max ( max ( DT(B)[ black_pixels(A) ] ), max ( DT(A)[ black_pixels(B) ] ) )
    Again, Hausdorff units are pixel distances, so divide by the long edge length.
    '''
    if type(distances_i_to_g) == int or type(distances_g_to_i) == int:
        hausdorff = "Blank Image"
    else:
        hausdorff = max( distances_i_to_g.max(), distances_g_to_i.max() )
        ## Normalize by long edge
        hausdorff /= long_edge
        if visualize: print( "hausdorff:", hausdorff )
    
    return hausdorff

def test():
    arr_a = np.ones((2,4),dtype=np.uint8)*255
    arr_a[0,0] = 0
    arr_a[0,1] = 0
    arr_b = np.ones((2,4),dtype=np.uint8)*255
    arr_b[1,1] = 0
    img_a = Image.fromarray( arr_a )
    img_b = Image.fromarray( arr_b )
    distances = [250]
    
    precomputed = precompute( img_a, img_b )
    
    print( "get_f_measure()" )
    print( get_f_measure( precomputed, distances ) )
    
    print( "get_chamfer_distance()" )
    print( get_chamfer_distance( precomputed ) )
    
    print( "get_hausdorff_distance()" )
    print( get_hausdorff_distance( precomputed ) )

def run(test, gt, which, threshold = 0.25, distances = None, visualize=False, force = False):
    '''
    Given:
        test: A path to an image to load as the test image
        gt: A path to an image to load as the ground truth image
        which: a set of 'f_scores', 'chamfer', 'hausdorff' to compute
        distances (optional): A sequence of thresholds to use when computing the
                              F-measure. Each is a distance cutoff as a per thousandth
                              of the long edge. Required if 'f_score' is in `which`.
        gui (optional): unused
        visualize (optional): if True, show intermediate images (default False)
    Returns a dictionary with the following elements if present in `which`:
        f_scores: a list of f-measure scores for each distance in `distances`
        chamfer: the chamfer distance
        hausdorff: the hausdorff distance
    '''
    
    if len( which ) == 0:
        raise RuntimeError( "run() called with no desired metric. This doesn't make sense." )
    
    print( "Loading test image:", test )
    print( "Loading gt image:", gt )
    img_a, img_b = files.open_images(test, gt, mode='GRAY', force = force)
    
    precomputed = precompute( img_a, img_b, threshold, visualize = visualize )
    
    result = {}
    if 'f_score' in which:
        if distances is None: raise RuntimeError
        result['f_score'] = get_f_measure( precomputed, distances, visualize = visualize)
    if 'chamfer' in which:
        result['chamfer'] = get_chamfer_distance( precomputed, visualize = visualize)
    if 'hausdorff' in which:
        result['hausdorff'] = get_hausdorff_distance( precomputed, visualize = visualize)
    return result

def main():
    args = getArgs()
    which = set()
    if args.f_measure: which.add( 'f_score' )
    if args.chamfer: which.add( 'chamfer' )
    if args.hausdorff: which.add( 'hausdorff' )
    result = run(args.input, args.groundtruth, which, distances = args.distance, visualize = args.visualize)
    print( result )

if __name__ == '__main__':
    main()
