from __future__ import print_function, division

from tqdm import tqdm
# from svgpathtools import Document, svg2paths
from svgpathtools import *
from numpy import asfarray, arange, abs
import scipy.spatial, scipy.optimize
from aabbtree import AABBTree, AABB
import sys
from os.path import *

eps = 1e-8

def distance_point_to_segment( point, segment ):
    ## From https://github.com/mathandy/svgpathtools/blob/master/svgpathtools/path.py
    ## Simpler than: https://gist.github.com/mathandy/c85736a70b7a54ba301696aacfbc4dbb
    return segment.radialrange( complex( *point ) )[0][0]

def get_global_scale( tree ):
    root = tree.getroot()
    
    ## Search for transform nodes. If there is one and everything above it is a <g> or <svg>,
    ## and it has a uniform scale, we can extract the scale and apply that manually.
    transforms = root.findall( './/*[@transform]' )
    ## If there are no transforms, we're fine. Scale is 1.0.
    if len( transforms ) == 0: return 1.0
    
    ## If there is more than one transform, we can't handle it.
    if len( transforms ) > 1: raise NotImplementedError( "More than one transform." )
    
    ## We may be able to handle a single transform node.
    transform = transforms[0]
    
    ## If the transform node is not the only child of the root or a chain
    ## of only children from the root.
    xml_prefix = '{http://www.w3.org/2000/svg}'
    ## These tags are the ones that svgpathtools parses, along with groups (g).
    forbidden_siblings = frozenset( xml_prefix + tag for tag in [ 'g', 'path', 'polyline', 'polygon', 'line', 'ellipse', 'circle', 'rect' ] )
    parent_map = {c:p for p in tree.iter() for c in p}
    ancestors = set([transform])
    node = transform
    while True:
        parent = parent_map[ node ]
        for sibling in parent:
            if sibling not in ancestors and sibling.tag in forbidden_siblings:
                raise NotImplementedError( "Transform is not global." )
        if parent.tag == xml_prefix + 'svg': break
        ancestors.add( parent )
        node = parent
    
    import re
    match = re.match( r'matrix\(([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\)', transform.attrib['transform'] )
    if match is None: raise NotImplementedError( "Unsupported transform." )
    
    import numpy.linalg
    m = [ float(match.group(i)) for i in range( 1,5 ) ]
    m = numpy.asarray( [[ m[0], m[1] ], [ m[2], m[3] ]], order = 'F' )
    _, s, _ = numpy.linalg.svd( m )
    if ( s[0] - s[1] ) > eps: raise NotImplementedError( "Non-uniform scale." )
    
    scale = s[0]
    print( "Found a global transform with uniform scale", scale )
    return scale

def set_segment_by_point(seg, start=None, end=None):
    '''
    Given:
        seg: a segement of a path element
        start: new start point that close the segement junction
        end: new end point that close the segement junction
    Return:
        A new snapped segment

    Now this function only support Line, QuadraticBezier, CubicBezier and Arc elements
    '''
    if start == None and end == None:
        raise SyntaxError("At least one point should be given.")
    
    if type(seg) == Line:
        if start != None:
            if seg.end == start: return seg
            new_seg = Line(start, seg.end)
        if end != None:
            if seg.start == end: return seg
            new_seg = Line(seg.start, end)
    
    elif type(seg) == QuadraticBezier:
        if start != None:
            if seg.end == start: return seg
            new_seg = QuadraticBezier(start, seg.control, seg.end)
        if end != None:
            if seg.start == end: return seg
            new_seg = QuadraticBezier(seg.start, seg.control, end)
    
    elif type(seg) == CubicBezier:
        if start != None:
            if seg.end == start: return seg
            new_seg = CubicBezier(start, seg.control1, seg.control2, seg.end)
        if end != None:
            if seg.start == end: return seg
            new_seg = CubicBezier(seg.start, seg.control1, seg.control2, end)
    
    elif type(seg) == Arc:
        if start != None:
            if start == seg.end: return seg
            new_seg = Arc(start, seg.radius, seg.rotation, seg.large_arc, seg.sweep, seg.end)
        if end != None:
            if seg.start == end: return seg
            new_seg = Arc(seg.start, seg.radius, seg.rotation, seg.large_arc, seg.sweep, end)
    else:
        raise ValueError("Unspport segment types! %s"%type(seg))
    
    return new_seg


def snap_svg(path_to_svg, distance1, distance2):
    
    # generate closed SVG file
    endpoint_snapping(path_to_svg, float(distance1), float(distance2))
    
    # visualize this result
    # import sys
    # from PyQt5 import QtWidgets, QtSvg
    # filepath, filename = split(path_to_svg)
    # name, _ = splitext(filename)
    # app = QtWidgets.QApplication(sys.argv)
    # window = QtWidgets.QWidget()
    # layout = QtWidgets.QVBoxLayout()
    # svgWidget = QtSvg.QSvgWidget(name + "_closed.svg")
    # layout.addWidget(svgWidget)
    # window.setLayout(layout)
    # window.show()
    # sys.exit(app.exec_())

def endpoint_generate(paths):
    '''
    Given:
        paths, the list of path elements of whole SVG
    Return:
        endpoints, a list of tuple of point coordination, which get from the end point of each segment
        endpoint_addtresses, a list of segment index and point index corresponding to the endpoints list
    '''
    endpoints = [] # a copy of point coordinations
    endpoint_addresses = []
    
    for path_index, path in enumerate( paths ):
        for seg_index, seg in enumerate( path ):
            for t in (0,1):
                pt = seg.point(t)
                endpoints.append( ( pt.real, pt.imag ) )
                endpoint_addresses.append( ( path_index, seg_index, t ) )
    return endpoints, endpoint_addresses

def endpoint_snapping(path_to_svg, distance, distance_j = 3):
    '''
    Given: 
        path_to_svg: A path to an SVG file.
        distance: A threshold of point distance that we will close junction points, which 

    Save the snapped result to a svg file with surfix "_closed"
    '''
    
    filepath, svg = split(path_to_svg)
    name, _ = splitext(svg)
    global_scale = 1.0

    try:
        doc = Document( path_to_svg )
        flatpaths = doc.flatten_all_paths()
        paths = [ path for ( path, _, _ ) in flatpaths ]
    except:
        global_scale = get_global_scale( doc.tree )
        ## Let's truly fail if there are transform nodes we can't handle.
        # try: global_scale = get_global_scale( doc.tree )
        # except: print( "WARNING: There are transforms, but flatten_all_paths() failed. Falling back to unflattened paths and ignoring transforms.", file = sys.stderr )
        
        paths, _ = svg2paths( path_to_svg )
    for i in range(len(paths)):
        if paths[i] == Path():
            paths.pop(i)
    # convert relative distance to real distance
    if 'viewBox' in doc.root.attrib:
        import re
        _, _, width, height = [ float(v) for v in re.split( '[ ,]+', doc.root.attrib['viewBox'].strip() ) ]
        long_edge = max( width, height )
        
    elif "width" in doc.root.attrib and "height" in doc.root.attrib:
        width = doc.root.attrib["width"].strip().strip("px")
        height = doc.root.attrib["height"].strip().strip("px")
        long_edge = max( float(width), float(height) )
    else:
        raise ValueError("Can't find viewBox or Width&Height info!")
    
    distance_real = distance * long_edge /1000 / global_scale
    distance_real_j = distance_j * long_edge /1000 / global_scale

    print("Closing open junctions within distance %f (%f pixel distance) "%(distance, distance_real))
    print("Closing T-junctions within distance %f (%f pixel distance) "%(distance_j, distance_real_j))
    
    paths, snapped = endpoint_close(paths, distance_real)

    paths = t_junction_close(paths, distance_real_j, snapped)

    print("Saving")
    wsvg(paths = paths, filename = join(filepath, name + "_closed.svg"))
    return join(filepath, name + "_closed.svg")

def endpoint_close(paths, distance):
    ## Gather all endpoints, path index, segment index, t value
    endpoints, endpoint_addresses =  endpoint_generate(paths)
    
    print( "Creating spatial data structures:" )
    
    dist_finder = scipy.spatial.cKDTree( endpoints )

    import numpy as np
    endpoints_find = np.array(dist_finder.query_ball_tree(dist_finder, distance))
    endpoints_find = np.unique(endpoints_find)
    snapped = []
    ## Close open junctions
    for pts in endpoints_find:
        if len(pts) == 1: continue
        # first pass to get average point that is used to snap junctions
        avg_point = complex()
        pc = 0
        for i in range(len(pts)):
            if endpoint_addresses[pts[i]] not in snapped: 
                path, seg, t = endpoint_addresses[pts[i]][0], endpoint_addresses[pts[i]][1], endpoint_addresses[pts[i]][2] 
                avg_point += paths[path][seg].point(t)
                pc += 1
        
        if avg_point != complex() and pc > 1: # if there have points that need to be snapped
            avg_point = avg_point / pc
            # second pass to set new segments
            for i in range(len(pts)):
                path, seg, t = endpoint_addresses[pts[i]][0], endpoint_addresses[pts[i]][1], endpoint_addresses[pts[i]][2] 
                if endpoint_addresses[pts[i]] not in snapped:
                    snapped.append(endpoint_addresses[pts[i]])
                    endpoints[pts[i]] = (avg_point.real, avg_point.imag)
                    if t == 0:
                        new_seg = set_segment_by_point(paths[path][seg], start=avg_point)
                    elif t == 1:
                        new_seg = set_segment_by_point(paths[path][seg], end=avg_point)
                    else:
                        raise ValueError("Invalid point value %f"%t)
                    paths[path][seg] = new_seg
    
    return paths, snapped

def t_junction_close(paths, distance, snapped):
    def t_junction_close_recursive(pt_with_index, distance, pre_seg_with_index, paths, bbtree, depth, snapped):
        # Search in AABB tree for overlap bboxes
        if depth == 0: return paths
        if pt_with_index[1] in snapped: return paths

        depth = depth -1
        bbox_edge = 2 * distance
        pt = pt_with_index[0]
        path_index, seg_index, t = pt_with_index[1]
        query = AABB([ ( pt[0] - bbox_edge, pt[0] + bbox_edge ), ( pt[1] - bbox_edge, pt[1] + bbox_edge ) ])
        min_j_dist = float('inf')
        min_t = None
        min_path_index = None
        min_seg_index = None
        min_seg = None
        for other_path_index, other_seg_index, seg in bbtree.overlap_values( query ):
            if other_path_index == path_index and other_seg_index == seg_index: continue
            try:
                j_dist, j_t = seg.radialrange( complex( *pt ) )[0]
            except Exception as e:
                print(str(e))
                continue
            if min_j_dist > j_dist:
                min_j_dist =  j_dist
                min_t = j_t
                min_path_index = other_path_index
                min_seg_index = other_seg_index
                min_seg = seg

        # if find target segment
        if min_j_dist < distance and min_j_dist > eps:
            # if the fixment of current pt(seg) depends on pre_seg, then fixment of pre_seg also depends on current pt
            # in other word, seg and pre_seg need to be fixed that the same time
            if (min_path_index, min_seg_index) == pre_seg_with_index[1]:
                # find closest point of two segmet endpoints to each other
                # cloeset point on min_seg(pre_seg) to cur_seg endpoint
                point1 = min_seg.point(min_t)
                # cloeset point on cur_seg to min_seg(pre_seg) endpoint
                t1 = 0 if min_t < 0.5 else 1
                dist2, t2 = paths[path_index][seg_index].radialrange(min_seg.point(t1))[0]
                point2 = paths[path_index][seg_index].point(t2)
                
                # point2 should also satisfy the distance requirement
                assert(dist2 < distance and dist2 > eps)
                # fix both segments
                avg_point = (point1 + point2) / 2
                # set current segment
                if t == 0:
                    new_seg_1 = set_segment_by_point(paths[path_index][seg_index], start=avg_point)
                elif t == 1:
                    new_seg_1 = set_segment_by_point(paths[path_index][seg_index], end=avg_point)
                else:
                    raise ValueError("Invalid point value %f"%t)
                paths[path_index][seg_index] = new_seg_1

                # set previous segment
                if t1 == 0:
                    new_seg_2 = set_segment_by_point(min_seg, start=avg_point)
                elif t1 == 1:
                    new_seg_2 = set_segment_by_point(min_seg, end=avg_point)
                else:
                    raise ValueError("Invalid point value %f"%t1)
                paths[min_path_index][min_seg_index] = new_seg_2
                
                # return result
                return paths

            else:
                org_seg = paths[path_index][seg_index]
                # call it self recursively by two endpoints of min_seg to find if there is addtional dependency 
                pt_start = ((min_seg.start.real, min_seg.start.imag), (min_path_index, min_seg_index, 0))
                pre_seg = (paths[path_index][seg_index], (path_index, seg_index))
                paths = t_junction_close_recursive(pt_start, distance, pre_seg, paths, bbtree, depth, snapped)

                pt_end = ((min_seg.end.real, min_seg.end.imag), (min_path_index, min_seg_index, 1))
                paths = t_junction_close_recursive(pt_end, distance, pre_seg, paths, bbtree, depth, snapped)

                # generate current new segments after all denpent segments are fixed
                if org_seg == paths[path_index][seg_index]:
                    t_point = paths[min_path_index][min_seg_index].point(min_t)
                    if t == 0:
                        new_seg = set_segment_by_point(paths[path_index][seg_index], start=t_point)
                    elif t == 1:
                        new_seg = set_segment_by_point(paths[path_index][seg_index], end=t_point)
                    else:
                        raise ValueError("Invalid point value %f"%t)
                    paths[path_index][seg_index] = new_seg

                return paths
        else:
            # nothing need to change, return paths directly
            return paths
    ## Close T-junctions
    endpoints, endpoint_addresses =  endpoint_generate(paths)
    # Build an axis-aligned bounding box tree for the segments.
    bbtree = AABBTree()

    for path_index, path in enumerate( paths ):
        for seg_index, seg in enumerate( path ):
            xmin, xmax, ymin, ymax = seg.bbox()
            bbtree.add( AABB( [(xmin, xmax), (ymin, ymax)] ), ( path_index, seg_index, seg ) )
    
    # for each point, find the hit segments and fix them if necessary
    for i, ( pt, ( path_index, seg_index, t ) ) in enumerate( zip( endpoints, endpoint_addresses )):
        pt_with_index = (pt, ( path_index, seg_index, t ))
        pre_seg_with_index = (None, None)
        paths = t_junction_close_recursive(pt_with_index, distance, pre_seg_with_index, paths, bbtree, 10, snapped)
        
    
    return paths
    
def endpoint_statistics( path_to_svg ):
    '''
    Given:
        path_to_svg: A path to an SVG file.
    
    Normalizes by the svg's long edge as defined by its viewBox.
    
    Ignores <svg> width or height attributes.

    '''
    
    global_scale = 1.0
    
    try:
        doc = Document( path_to_svg )
        flatpaths = doc.flatten_all_paths()
        paths = [ path for ( path, _, _ ) in flatpaths ]
    except:
        global_scale = get_global_scale( doc.tree )
        ## Let's truly fail if there are transform nodes we can't handle.
        # try: global_scale = get_global_scale( doc.tree )
        # except: print( "WARNING: There are transforms, but flatten_all_paths() failed. Falling back to unflattened paths and ignoring transforms.", file = sys.stderr )
        
        paths, _ = svg2paths( path_to_svg )
    
    ## First pass: Gather all endpoints, path index, segment index, t value
    endpoints = [] # a copy of point coordinations
    endpoints_p = [] # real points, we will do the snapping by changing points in this list
    endpoint_addresses = []
    
    for path_index, path in enumerate( paths ):
        for seg_index, seg in enumerate( path ):
            for t in (0,1):
                pt = seg.point(t)
                endpoints.append( ( pt.real, pt.imag ) )
                endpoint_addresses.append( ( path_index, seg_index, t ) )
    
    
    print( "Creating spatial data structures:" )
    ## Point-point queries.
    dist_finder = scipy.spatial.cKDTree( endpoints )
    ## Build an axis-aligned bounding box tree for the segments.
    bbtree = AABBTree() # but, why?
    # for path_index, path in tqdm( enumerate( paths ), total = len( paths ), ncols = 50 ):
    for path_index, path in enumerate( paths ):
        for seg_index, seg in enumerate( path ):
            xmin, xmax, ymin, ymax = seg.bbox() # record bbox of each segmentation?
            bbtree.add( AABB( [(xmin, xmax), (ymin, ymax)] ), ( path_index, seg_index, seg ) )
    
    # Second pass: Gather all minimum distances
    print( "Finding minimum distances:" )
    
    minimum_distances = []
    for i, ( pt, ( path_index, seg_index, t ) ) in enumerate( zip( endpoints, endpoint_addresses )):
        ## 1. Find the minimum distance to any other endpoints
        
        ## Find two closest points, since the point itself is in dist_finder with distance 0.
        mindist, closest_pt_indices = dist_finder.query( [pt], k = 2 )
        
        ## These come back as 1-by-2 matrices.
        mindist = mindist[0]
        closest_pt_indices = closest_pt_indices[0]
        ## If we didn't find 2 points, then pt is the only point in this file.
        ## There is no point element in SVG, so that should never happen.
        
        assert len( closest_pt_indices ) == 2
        ## If there are two or more other points identical to pt,
        ## then pt might not actually be one of the two returned, but both distances
        ## should be zero.
        assert i in closest_pt_indices or ( mindist < eps ).all()
        assert min( mindist ) <= eps
        
        ## The larger distance corresponds to the point that is not pt.
        mindist = max( mindist )
        
        ## If we already found the minimum distance is 0, then there's no point also
        ## searching for T-junctions.
        if mindist < eps:
            minimum_distances.append( mindist )
            continue
        
        ## 2. Find the closest point on any other paths (T-junction).
        ## We are looking for any segments closer than mindist to pt.
        # why? why mindist?
        query = AABB([ ( pt[0] - mindist, pt[0] + mindist ), ( pt[1] - mindist, pt[1] + mindist ) ])
        
        for other_path_index, other_seg_index, seg in bbtree.overlap_values( query ):
            ## Don't compare the point with its own segment.
            if other_path_index == path_index and other_seg_index == seg_index: continue
            
            ## Optimization: If the distance to the bounding box is larger
            ## than mindist, skip it.
            ## This is still relevant, because mindist will shrink as we iterate over
            ## the results of our AABB tree query.
            # why? this is also not reasonable to me
            xmin, xmax, ymin, ymax = seg.bbox()
            if(
                pt[0] < xmin - mindist or
                pt[0] > xmax + mindist or
                pt[1] < ymin - mindist or
                pt[1] > ymin + mindist ):
                continue
            
            ## Get the point to segment distance.
            dist_to_other_path = distance_point_to_segment( pt, seg )
            ## Keep it if it's smaller.
            if mindist is None or dist_to_other_path < mindist:
                mindist = dist_to_other_path
            
            ## Terminate early if the minimum distance found already is 0
            if mindist < eps: break
        
        ## Accumulate the minimum distance
        minimum_distances.append( mindist )
   
    minimum_distances = global_scale * asfarray( minimum_distances )
    
    ## Divide by long edge.
    if 'viewBox' in doc.root.attrib:
        import re
        _, _, width, height = [ float(v) for v in re.split( '[ ,]+', doc.root.attrib['viewBox'].strip() ) ]
        long_edge = max( width, height )
        print( "Normalizing by long edge:", long_edge )
        minimum_distances /= long_edge
    elif "width" in doc.root.attrib and "height" in doc.root.attrib:
        width = doc.root.attrib["width"].strip().strip("px")
        height = doc.root.attrib["height"].strip().strip("px")
        long_edge = max( float(width), float(height) )
        print( "Normalizing by long edge:", long_edge )
        minimum_distances /= long_edge
    else:
        print( "WARNING: No viewBox found in <svg>. Not normalizing by long edge." )
    print("Done")
    return minimum_distances

def analyze_distances( minimum_distances, percent_threshold = 0.1 ):
    minimum_distances = asfarray( minimum_distances )
    
    print( "total minimum distances:", minimum_distances.sum() )
    print( "count of minimum distances over 0.1% of long edge:", ( minimum_distances > percent_threshold/100. ).sum() )

def test_endpoint_statistics():
    '''
    Install the tester with:
        pip install pytest
    or
        pipenv install --dev
    
    Run the test with:
    
    >>> pytest junction_quality.py
    '''
    
    eps = 1e-8
    
    ## Too slow
    # ds = endpoint_statistics( '../evaluation_examples/Art_freeform_AG_02.svg' )
    # truth = 7.581131695541737
    # assert abs( ds.sum() - truth ) < eps
    
    ds = endpoint_statistics( '../evaluation_examples/Art_freeform_AG_02-crop.svg' )
    truth = 1.1532169833382522
    assert abs( ds.sum() - truth ) < eps
    
    ds = endpoint_statistics( '../evaluation_examples/Ind_architecture_JJ_03_norm_full_500-crop.svg' )
    truth = 0.9172898080003837
    assert abs( ds.sum() - truth ) < eps

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser( description = "Print statistics on an SVG file's junctions." )
    parser.add_argument( "path_to_svg", help = "The SVG file to analyze." )
    # parser.add_argument( "--snap", help = "close junctions in SVG file", action="store_true" )
    parser.add_argument( "--snap_dist", help = "close junctions in SVG file", default = False)
    parser.add_argument( "--snap_dist_T", help = "close junctions in SVG file", default = 3)
    args = parser.parse_args()
    
    if args.snap_dist:
        snap_svg(args.path_to_svg, args.snap_dist, args.snap_dist_T)
    else:
        minimum_distances = endpoint_statistics( args.path_to_svg )
        analyze_distances( minimum_distances )
