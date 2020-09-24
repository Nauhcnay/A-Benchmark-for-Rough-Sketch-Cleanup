from __future__ import print_function, division
# import xml.etree.ElementTree as ET
import lxml.etree as ET
import lxml
import sys, os
import argparse
import subprocess
import copy
import time
from PIL import Image
from os.path import *
try:
    import files
except:
    from tools import files

def get_name(name):
    return name[name.rfind("}") + 1 : ]

def to_png(svg, path_to_ink, mode = 'base', target_size = None, png_dir = None, save_dir = None):
    '''
    Given:
        svg, path to svg file, 
        path_to_ink, path to inkscape
        mode, decide what reference png file should be used to get target size
            base: extract basename only
            gt: extract basename + author name
            full: don't remove any thing, return sketch name directly
        target_size, target new size shape as a tuple: (width, height), 
            if None is given, it will be extracted from reference png file
        png_dir, path to reference png folder
        save_dir, path to save new png
    Action:
        Rasterize svg to png with given target size and save to save_dir
    '''
    path, file = split(svg)
    name, extension = splitext(file)
    # get base name of current svg
    name_base = files.extract_sketch_name(name, mode)
    png = name_base + '.png'
    # get targe size from base rough sketch
    if target_size is None:
        target_size = files.get_sketch_size(png, png_dir)
    # if save path is not given, save png at same folder
    if extension != '':
        assert('.svg' == extension)

        
    # parse the svg file, get artboard size   
    svg_size = files.get_sketch_size(file, path)
    if save_dir is None:
        save_dir = path
    print("Log:\tconverting %s ..."%join(path, file))
    print("Log:\tsource svg size:\t%s\n\ttarget png size:\t%s"%(str(svg_size), str(target_size)))

    # thanks to https://www.iprintfromhome.com/mso/UnderstandingDPI.pdf

    # Inkscape 1.0:
    inkscape_args = [path_to_ink, join(os.getcwd(),svg), "--export-filename=" + join(os.getcwd(), save_dir, name+'.png'),  "--export-background=white"] 
    # Inkscape 0.92:
    # inkscape_args = [path_to_ink, "--without-gui", "--file=" + join(os.getcwd(),svg), "--export-png=" + join(os.getcwd(), save_dir, name+'.png'),  "--export-background=white"]
    dpi = int(target_size[0] / (svg_size[0] / 96.0))    
    print(inkscape_args + ["--export-dpi=%d"%dpi])
    subprocess.run(inkscape_args + ["--export-dpi=%d"%dpi]) 
    png_size = files.get_sketch_size(name+'.png', save_dir)
    

    if target_size != png_size:
        if abs(target_size[0] - png_size[0]) > 1 or abs(target_size[1] - png_size[1]) > 1:
            print('=' * 20)
            print("Warn:\tWRONG size of %s "%svg)
            print('=' * 20)
            raise ValueError()
        else:
            subprocess.run(inkscape_args+ ["--export-width=%d"%target_size[0], "--export-height=%d"%target_size[1]])        
            png_size = files.get_sketch_size(name+'.png', save_dir)
    print("Log:\trasterized %s, \n\tresult png size:\t%s"%(join(save_dir, name+'.png'), str(png_size)))

def open_svg(path_to_svg):
    '''
    Given:
        path_to_svg, full path to svg file
    Return:
        XML tree and root element of this svg
    '''
    path, svg = split(path_to_svg)
    name, extension = splitext(svg)
    if extension == '.svg':
        # initialize xml reader
        
        try:
            tree = ET.parse( path_to_svg )
        except lxml.etree.XMLSyntaxError:
            ## Fix missing xlink
            ## From: https://stackoverflow.com/questions/49685230/lxml-hiding-xmlns-attribute-of-root-svg-tag
            parser = ET.XMLParser( recover = True )
            tree = ET.parse( path_to_svg, parser = parser )
            root = tree.getroot()
            
            nsmap = root.nsmap
            nsmap['xlink'] = "http://www.w3.org/1999/xlink"
            root2 = ET.Element( root.tag, nsmap = nsmap )
            root2[:] = root[:]
            for a in root.attrib: root2.attrib[a] = root.attrib[a]
            from io import StringIO
            tree = ET.parse( StringIO( ET.tostring( root2, encoding="unicode") ) )
        
        root = tree.getroot()
        return tree, root

def layer_clean(root, remove_rough = False):
    '''
    Given:
        root, the root xml element of svg 
        remove_rough, remove layer name contains "rough" in svg, this is ready for clean GT svg sketches
    Action:
        remove any unecessary layers
    '''
    try:
        for i in range(len(root)-1, -1, -1):
            if get_name(root[i].tag) == "g":
                if  "raster" in root[i].attrib['id'].lower() or \
                    "orig" in root[i].attrib['id'].lower() or \
                    "layer" in root[i].attrib['id'].lower() or \
                    "comment" in root[i].attrib['id'].lower() or\
                    "discard" in root[i].attrib['id'].lower() or \
                    remove_rough and "rough" in root[i].attrib['id'].lower():
                        root.remove(root[i]) 
            if "rect" in get_name(root[i].tag):
                root.remove(root[i]) 
        return True
    except Exception as e:
        print(str(e))
        return False

def normalize(root, threshold = 0.001, color = "#000000", cap = "round", join = "round"):
    '''
    Given:
        root, the root xml element of svg
        threshold, stroke width which equals thershold * length of artboard longer side
        color, stroke color, default is black "#000000"
        cap, stroke cap type
        join, stroke joint type
    Return:
        root of normalized svg
    '''

    # get namespace
    tag_root = root.tag
    namespace = tag_root[tag_root.find('{'):tag_root.rfind('}')+1]
    try:
        # get all strokes in root
        # only XPath could work, I don't know why
        strokes = root.findall(".//" + namespace + "path")
        polygons = root.findall(".//" + namespace + "polygon")
        polylines = root.findall(".//" + namespace + "polyline")
        styles = root.findall(".//" + namespace + "style")
        lines = root.findall(".//" + namespace + "line")
        ellipses = root.findall(".//" + namespace + "ellipse")
        rects = root.findall(".//" + namespace + "rect")
        circles = root.findall(".//" + namespace + "circle")
        # this is for any special case that all elements above are not in the svg
        g = root.findall(".//" + namespace + "g")

        # get the size of artboard
        width, height = files.get_sketch_size(sketch = None, root = root)
        root.attrib["width"] = str(width)
        root.attrib["height"] = str(height)
        root.attrib["style"] = "background-color:white"
        stroke_width = width if width > height else height
        stroke_width = stroke_width * threshold
        for style in styles:
            # split styles
            style_text = style.text.strip("\n")
            style_lines = []
            end = style_text.find("}")
            while end != -1:
                style_lines.append(style_text[:end+1])
                style_text = style_text[end+1:]
                end = style_text.find("}")        
            for i in range(len(style_lines)):
                st = style_lines[i].strip("\t")
                if "stroke-width" in style_lines[i]:
                    style_lines[i] = st[: st.find("stroke-width:") + len("stroke-width:")] + '%f'%stroke_width + st[st.find(';', st.find("stroke-width")) :]
                else:
                    style_lines[i] = st[: st.find("}")] + 'stroke-width:%f;'%stroke_width + "}"
                st = style_lines[i].strip("\t")
                if "stroke-linecap" in style_lines[i]:
                    style_lines[i] = st[: st.find("stroke-linecap:") + len("stroke-linecap:")] + cap + st[st.find(';', st.find("stroke-linecap")) :]
                else:
                    style_lines[i] = st[: st.find("}")] + 'stroke-linecap:%s;'%cap + "}"
                st = style_lines[i].strip("\t")
                if "stroke-linejoin" in style_lines[i]:
                    style_lines[i] = st[: st.find("stroke-linejoin:") + len("stroke-linejoin:")] + join + st[st.find(';', st.find("stroke-linejoin")) :]
                else:
                    style_lines[i] = st[: st.find("}")] + 'stroke-linejoin:%s;'%join + "}"
                st = style_lines[i].strip("\t")
                if "stroke:" in style_lines[i]:
                    style_lines[i] = st[: st.find("stroke:") + len("stroke:")] + color + st[st.find(';', st.find("stroke:")) :]
                else:
                    style_lines[i] = st[: st.find("}")] + 'stroke:%s;'%color + "}"
            style.text = '\n'.join(style_lines)
        
        # then change every stroke style individually
        for elements in [strokes, polylines, polygons, lines, ellipses, rects, circles, g]:
            for element in elements:
                element.attrib["stroke"] = color
                element.attrib["stroke-width"] = str("%f"%stroke_width)
                element.attrib["stroke-linecap"] = cap
                element.attrib["stroke-linejoin"] = join
                element.attrib["fill"] = "none"
                element.attrib.pop("style", None)
                
                for key in element.attrib:
                    if key == "points":
                        points = element.attrib[key].split(" ")
                        for i in range(len(points)-1, -1, -1):
                            if "nan" in points[i]:
                                points.pop(i)
                        element.attrib[key] = " ".join(points)
        return True
    except Exception as e:
        print(str(e))
        return False
        
def svg_write(root, tree, name, path_to_inkscape, save_dir,
            separate = True, acc = False, inplace = False):
    '''
    Given:
        root, the root element of a normalized svg
        tree, tree element of a normalized svg
        name, saving name of normalized svg
        path_to_inkscape, path to inkscape
        separate, spearate all layers into different file if it is True, for example:
            name_layer1.svg
            name_layer2.svg
            ...
        acc, save accumulate layers into different file if it is True, for example:
            name_layer1.svg
            name_layer1+layer2.svg
            ...
        inplace, overwrite the original svg file with normalized svg
    Action:
        normalze one svg and save it into file
    '''

    # wirte normalized svg first
    if inplace:
        tree.write(join(save_dir, name + ".svg"))
        name_list = []
        name_list.append(name + ".svg")      
    else:
        tree.write(join(save_dir, name + "_norm_full.svg"))
        name_list = []
        name_list.append(name + "_norm_full.svg")  
        if separate == True:
            # generate a list of layers
            layers = []
            for layer in root:
                if get_name(layer.tag) == "g":
                    layers.append(layer)
            # it is only necessary to separate when there is more than one layers
            if len(layers) > 1:
                # deep copy serval roots 
                tree_list = []
                for i in range(len(layers)):
                    tree_list.append(copy.deepcopy(tree))
                    
                # split each layer into a single file
                if len(root) <= 20:
                    for i in range(len(tree_list)):
                        iroot = tree_list[i].getroot()
                        # I think we have to use reverse order
                        for j in range(len(iroot)-1, -1, -1):
                            if get_name(iroot[j].tag) == "g":    
                                if iroot[j].attrib['id'] != layers[i].attrib['id']:
                                    iroot.remove(iroot[j])
                        if "shad" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "shadows"
                        if "clea" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "cleaned"
                        if "sketch" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "shadows"
                        if "layer" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "scaffolds"
                        if "scaf" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "scaffolds"
                        if "textu" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "texture"
                        if "color" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "color region"
                        if "roug" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "rough"
                        if "dash" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "extra"
                        if "reflection" in layers[i].attrib['id'].lower():
                            layers[i].attrib['id'] = "extra"
                        tree_list[i].write(join(save_dir, name + "_norm_%s.svg"%layers[i].attrib['id']))
                        name_list.append(name + "_norm_%s.svg"%layers[i].attrib['id'])
                else:
                    print("Error:\tfind too many layers, please fix the svg file manually")
                    raise ValueError()

                # accumilate one layer and save as a file each time
                if acc:
                    if len(layers) > 0:
                        root.remove(layers[-1])
                        for i in range(len(layers)-2, -1, -1):
                            tree.write(join(save_dir, name + "_norm_full_%d.svg"%i))
                            name_list.append(name + "_norm_full_%d.svg"%i)
                            root.remove(layers[i])
                    elif len(layers) == 0 and 'id' in root.attrib:
                        tree.write(join(save_dir, name + "_norm_%s.svg"%root.attrib['id']))
    
    # if there is only one layer, then duplicate this file to "norm cleaned", 
    # to make sure every sketch will at least has two normalizaion output 
    if len(name_list) == 1 and "norm" in name_list[0] and len(name.split("_")) > 4 and inplace is False:
        tree.write(join(save_dir, name) + "_norm_cleaned.svg")
        name_list.append(name + "_norm_cleaned.svg")
    # convert svg to ink svg, which has the best compatablity to most clean up algorithms
    for name in name_list:
        cp = subprocess.run([path_to_inkscape, 
            ## Inkscape 0.92:
            # "--without-gui",
            # "--file=" + join(os.getcwd(), save_dir, name),
            # "--export-plain-svg", join(os.getcwd(), save_dir, name)])
            ## Inkscape 1.0:
            join(os.getcwd(), save_dir, name),
            "--export-plain-svg",
            "--export-filename=" + join(os.getcwd(), save_dir, name)])
        # need to check if inkscape works correctly
        if cp.returncode != 0:
            raise RuntimeError("Inkscape Error")
        time.sleep(2)

def run_single(path_to_svg, path_to_ink, save_dir = None, norm = 0.001,
            add_transform = False, color = "#000000", cap = "round", joint = "round",
            inplace = False, remove_rough = False):
    '''
    Given
        path_to_svg, path to svg file which is waiting for normalization
        path_to_ink, path to inckscape
        save_dir, path to new normalized svg
        norm, the width of stroke, which means stroke width = norm * length of artboard longer side
        mode, remove rouhg layers if it is "clean"
        add_transform, add missing transform matrix back to svg, this is a fix to pipline topologydriven2strokeaggregator only
        color, stroke color, default is black "#000000"
        cap, stroke cap type
        join, stroke joint type
        inplace, overwrite 
    Action:
        normalize all svg files in the folder_to_svg, save the new svg file to save_dir

    '''
    path, svg = split(path_to_svg)
    name, extension = splitext(svg)
    print("Log:\tnormalizing %s"%svg)
    
    if (save_dir == None or inplace):
        save_dir = path
    assert isdir(save_dir)
    
    # safe open svg
    tree, root = open_svg(path_to_svg)
    
    if add_transform:
        tag_root = root.tag
        namespace = tag_root[tag_root.find('{'):tag_root.rfind('}')+1]
        g = root.findall(".//" + namespace + "g")
        find_transform = False
        for i in g:
            if "transform" in i.attrib:
                find_transform = True
        
        # for the svg which need keep there transform matrix
        if find_transform == False:
            paths = root.findall(".//" + namespace + "path")
            g = ET.Element(namespace + "g")

            g.attrib["transform"] = "matrix(0.5,0,0,-0.5,0,%f)"%float(root.attrib["height"].strip("px"))
            for path in paths:
                g.insert(-1, path)
            root.insert(-1, g)

    # remove additional layer
    if layer_clean(root, remove_rough) is False:
        print("Error:\tlayer removing error")

    # normalize strokes
    if normalize(root, norm, color, cap, joint) is False:
        print("Error:\tstroke normlize error")
    
    # wirte normalized svg, separate layers if necessary
    svg_write(root, tree, name, path_to_ink, save_dir, inplace = inplace)
    
def gmi_to_svg(inpath, outpath, width, height):
    '''
    Given
        inpath, the path to gmi file
        outpath, the path to output svg
        width, artboard width
        height, artboard height
    Action
        convert the gmi output from implementation of paper "Topology-driven vectorization of clean line drawings" to svg file
    '''
    _, svg_name = os.path.split(inpath)
    SVG_HEADER = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <svg viewBox="0 0 %f %f"
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"  version="1.2" baseProfile="tiny">
    <title>%s</title>

    <defs>
    </defs>
    <g fill="none" stroke="black" stroke-width="1" fill-rule="evenodd" stroke-linecap="square" stroke-linejoin="bevel" >

    <g fill="none" stroke="#000000" stroke-opacity="1" stroke-width="1" stroke-linecap="round" stroke-linejoin="bevel" transform="matrix(0.5,0,0,-0.5,0,%f)"
    font-family="MS Shell Dlg 2" font-size="7.5" font-weight="400" font-style="normal" 
    >
    """ % (width, height, svg_name, height)

    SVG_FOOTER = """</g>
    </g>
    </svg>
    """

    print( "Saving to:", outpath )

    with open( outpath, "w" ) as out:
        
        print( SVG_HEADER, file = out )
        
        tree = ET.parse( inpath )
        root = tree.getroot()
        
        ## We assume there is only 1 curves child. If this isn't true, we need to
        ## make sure we understand the format.
        assert len( root.findall("curves") ) == 1
        
        curves = root.find("curves")
        for child in curves:
            
            ## Start the path.
            print( '<path vector-effect="non-scaling-stroke" fill-rule="evenodd" d="', file = out, end = "" )
            
            if child.tag == "linear":
                ## The first element is a move to. The rest are line to.
                first = True
                for p in child:
                    assert p.tag == "p"
                    print( "%s %s,%s" % ( "M" if first else " L", p.get("x"), p.get("y") ), file=out, end = "" )
                    first = False
            
            elif child.tag == "spline":
                ## The first element is a move to. The rest are curve to.
                first = True
                assert len( child ) == 4
                for p in child: assert p.tag == "p"
                
                print( "M %s,%s C %s,%s %s,%s %s,%s" % (
                    child[0].get("x"), child[0].get("y"),
                    child[1].get("x"), child[1].get("y"),
                    child[2].get("x"), child[2].get("y"),
                    child[3].get("x"), child[3].get("y")
                    ), file = out, end = "" )
            
            else:
                raise RuntimeError( "Unknown curve type: %s" % child.tag )
            
            ## Close the path.
            print( '"/>', file = out )
        
        print( SVG_FOOTER, file = out )

    print( "Saved." )

def run_batch(folder_to_svg, path_to_ink, save_dir = None, norm = 0.001, 
                color = "#000000", cap = "round", joint = "round", 
                remove_rough = True):
    '''
    Given
        folder_to_svg, path to svg folder which waiting for normalization
        path_to_ink, path to inckscape
        save_dir, path to new normalized svg
        norm, the width of stroke, which means stroke width = norm * length of artboard longer side
        mode, remove rouhg layers if it is "clean"
        color, stroke color, default is black "#000000"
        cap, stroke cap type
        join, stroke joint type
    Action:
        normalize all svg files in the folder_to_svg, save the new svg file to save_dir

    '''
    

    for svg in os.listdir(folder_to_svg):
        name, extension = splitext(svg)
        if "norm" not in name and exists(join(folder_to_svg, name + "_norm_full.svg")) is False and extension==".svg":
            run_single(join(folder_to_svg, svg), path_to_ink, save_dir = save_dir, norm = norm,
            add_transform = False, color = color, cap = cap, joint = joint,
            inplace = False, remove_rough = remove_rough)
            


def parse():
    parser = argparse.ArgumentParser(description='SVG standardize tools')

    parser.add_argument('--ink', help ='path to Inkscape')
    parser.add_argument('--input',
                    help='path to input files')
    parser.add_argument('--output',
                    help='path to output files')
    parser.add_argument('--norm',
                    help='stroke width as ratio to length of artboard longer side (default: 0.001)',
                    default = 0.001)
    parser.add_argument('--color',
                    help='stroke color (default: "#000000")',
                    default = "#000000")
    parser.add_argument('--cap',
                    help='shape of stroke caps (default: "round")',
                    default = "round")
    parser.add_argument('--joint',
                    help='shape of stroke joints (default: "round")',
                    default = "round")
     
    return parser
if __name__ =="__main__":
    args = parse().parse_args()
    run_batch(args.input, args.ink, args.output, args.norm, args.color, args.cap, args.joint)
