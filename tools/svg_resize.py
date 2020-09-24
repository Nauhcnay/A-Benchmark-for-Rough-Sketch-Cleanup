from __future__ import print_function, division

import xml.etree.ElementTree as ET
import re

import cssutils
## From: https://stackoverflow.com/questions/20371448/stop-cssutils-from-generating-warning-messages
import logging
cssutils.log.setLevel( logging.CRITICAL )


def resize_svg( path_to_svg, scale = None, width = None, height = None, long_edge = None, output_path = None ):
    '''
    Given:
        path_to_svg: A path to an SVG file.
        scale (optional): A scale factor. If not specified, scale is determined via width or height or long_edge.
        width (optional): A target viewBox width. If not specified, calculated based on height or long_edge via uniform scaling.
        height (optional): A target viewBox height. If not specified, calculated based on width or long_edge via uniform scaling.
        long_edge (optional): A target viewBox long edge.
        output_path (optional): Where to save the SVG. By default, appends '-scaled' to `path_to_svg`.
    
    The SVG must not contain images or text or transformation matrices.
    Unknown results if the viewBox is not rooted at 0 0. Ignores <svg> width or height attributes.
    
    At least one of `scale` or `width` or `height` or `long_edge` must be specified.
    If more than one is specified, they must agree on the scale parameter.
    If `width` and `height` are both specified, it is an error if they are not a uniform scale of the input dimensions.
    '''
    
    ### 1 Load the file
    ### 2 Check that only supported elements are present
    ### 3 Compute scale factor
    ### 4 Scale elements
    ### 5 Scale CSS
    ### 6 Save
    
    
    if output_path is None:
        import os
        base, _ = os.path.splitext( path_to_svg )
        output_path = base + '-scaled.svg'
    
    ### 1 Load the file
    namespace = 'http://www.w3.org/2000/svg'
    ## This next line prevents an ns0 namespace from being saved into the output file.
    ET.register_namespace( '', namespace )
    tree = ET.parse( path_to_svg )
    root = tree.getroot()
    early_terminate = False
    ## Strip namespace
    ## From: https://stackoverflow.com/questions/13412496/python-elementtree-module-how-to-ignore-the-namespace-of-xml-files-to-locate-ma/25920989#25920989
    def strip_namespace( root, namespace ):
        for el in root.iter():
            if '{' + namespace + '}' in el.tag:
                _, _, el.tag = el.tag.rpartition('}') # strip ns
    def replace_namespace( root, namespace ):
        for el in root.iter():
            if '}' not in el.tag:
                el.tag = '{' + namespace + '}' + el.tag
    strip_namespace( root, namespace )
    
    
    ### 2 Check that only supported elements are present
    ## TODO: Should we whitelist only g and the elements we support?
    assert len( root.findall( './/text' ) ) == 0
    assert len( root.findall( './/clipPath' ) ) == 0
    assert len( root.findall( './/use' ) ) == 0
    # assert no transformation matrices
    assert len( root.findall( './/*[@transform]' ) ) == 0
    
    
    ### 3 Compute scale factor
    import re
    # find width and height
    if 'viewBox' in root.attrib:
        viewBox = [ float(v) for v in re.split( '[ ,]+', root.attrib['viewBox'].strip() ) ]
        assert viewBox[0] == 0
        assert viewBox[1] == 0
        w = viewBox[2]
        h = viewBox[3]
    elif 'width' in root.attrib and 'height' in root.attrib:
        w = float(root.attrib['width'].strip().strip('px'))
        h = float(root.attrib['height'].strip().strip('px'))   
    else:
        raise ValueError("Can't find width & height, invalid svg file, stop processing")
    
    if scale is not None:
        assert scale > 0
        assert long_edge is None
        if width is not None:
            assert width == scale * w
        if height is not None:
            assert height == scale * h
        if long_edge is not None:
            assert long_edge == scale * max( w, h )
    elif width is not None:
        scale = width / w
        if height is not None and abs(height - h) > 1:
            assert scale == height / h
        elif height is not None and abs(height - h) <= 1:
            early_terminate = True
        if long_edge is not None:
            assert long_edge == scale * max( w, h )
    elif height is not None:
        scale = height / h
        if width is not None:
            assert scale == width / w
        if long_edge is not None:
            assert long_edge == scale * max( w, h )
    elif long_edge is not None:
        scale = long_edge / max( w, h )
    else:
        raise RuntimeError( "At least one of width, height, or long_edge must be specified." )
    
    # no matter viewBox and width, height attribute are in root or not. create them
    
    root.attrib['viewBox'] = ' '.join([ '0', '0', '%f' % (scale*w), '%f' % (height if early_terminate else scale*h) ])
    root.attrib['width'] = str(scale * w)
    root.attrib['height'] = str(height if early_terminate else scale*h)
    root.attrib['style'] = 'enable-background:new ' + ' '.join([ '0', '0', '%f' % (scale*w), '%f' % (height if early_terminate else scale*h) ])
    ### 4 Scale elements
    '''
    scale any x and y and width
    scale points in a path (relative or absolute)
    scale style
    scale radius
    other shape parameters?
    '''
    if early_terminate is False:
        def scale_attributes( el, attributes, scale ):
            for a in attributes:
                ## These might not all be specified if the default
                ## is desired, which should be fine.
                if a in el.attrib:
                    el.attrib[a] = "%f" % ( scale * float( el.attrib[a] ) )
        
        ## https://developer.mozilla.org/en-US/docs/Web/SVG/Tutorial/Basic_Shapes
        ## scale: x1, y1, x2, y2
        for el in root.findall(".//line"):
            scale_attributes( el, ["x1","y1","x2","y2"], scale )
        for el in root.findall(".//ellipse"):
            scale_attributes( el, ["cx","cy","rx","ry"], scale )
        for el in root.findall(".//circle"):
            scale_attributes( el, ["cx","cy","r"], scale )
        for el in root.findall(".//rect"):
            scale_attributes( el, ["x","y","width","height","rx","ry"], scale )
        ## https://developer.mozilla.org/en-US/docs/Web/SVG/Element/image
        ## scale: x, y, width, height
        for el in root.findall(".//image"):
            scale_attributes( el, ["x","y","width","height"], scale )
        
        ## parse the points and scale them
        def scale_points( el, scale ):
            if 'points' not in el.attrib: return
            ## points is a string of numbers separated by non-numbers like commas or spaces
            points = [ scale*float(v) for v in re.findall( r'[-+]?[0-9]*\.[0-9]+|[-+]?[0-9]+\.?', el.attrib['points'] ) ]
            el.attrib['points'] = ' '.join([ '%f' % v for v in points ])
        
        # points = [ scale*float(v) for v in points.split(" ,") ]
        for el in root.findall(".//polygon"): scale_points( el, scale )
        for el in root.findall(".//polyline"): scale_points( el, scale )
        
        ## parse the path d and scale everything
        def scale_path( el, scale ):
            if 'd' not in el.attrib: return
            # d is a string containing single letters followed by number commands
            tokens = re.findall( r'[a-zA-Z]|[-+]?[0-9]*\.[0-9]+|[-+]?[0-9]+\.?', el.attrib['d'] )
            
            alphabet = [ 'M', 'm', 'L', 'l', 'H', 'h', 'V', 'v', 'C', 'c', 'S', 's', 'Q', 'q', 'T', 't', 'A', 'a', 'Z', 'z' ]
            for i in range(len( tokens )):
                tok = tokens[i]
                if tok.isalpha():
                    last_command = tok
                    last_command_index = i
                    if tok not in alphabet: raise RuntimeError( "Invalid path d: " + el.attrib['d'] )
                else:
                    ## scale the number unless it's the third, fourth, or fifth modular number after 'a' or 'A'
                    if last_command in ('a','A'):
                        offset = ( i - last_command_index + 1 ) % 7
                        if offset in (2,3,4): continue
                    
                    tokens[i] = "%f" % ( scale * float(tok) )
            
            el.attrib['d'] = ' '.join( tokens )
        
        for el in root.findall(".//path"):
            scale_path( el, scale )
        
        ### 5 Scale CSS
        def scaled_strokeWidth( strokeWidth, scale ):
            sw = strokeWidth
            ## Skip fractions
            if sw.strip().endswith('%'): return sw
            ## Store the units
            # suffix = sw.lstrip('0123456789')
            # number = sw[ :len(sw)-len(suffix) ]
            # rule.style["stroke-width"] = "%f%s" % ( float(number) * scale, suffix )
            _, number, suffix = re.split( r'([-+]?[0-9]*\.[0-9]+|[-+]?[0-9]+\.?)', sw, maxsplit = 1 )
            result = "%f%s" % ( float(number) * scale, suffix )
            return result
        
        ## Scale line widths in <style>
        for el in root.findall(".//style"):
            css = cssutils.parseString( el.text )
            for rule in css:
                if rule.type == rule.STYLE_RULE:
                    if "stroke-width" in rule.style:
                        sw = rule.style["stroke-width"]
                        rule.style["stroke-width"] = scaled_strokeWidth( sw, scale )
            el.text = css.cssText.decode( css.encoding )
        
        ## Scale line widths in style attributes
        for el in root.findall(".//*[@style]"):
            style = cssutils.parseStyle( el.attrib['style'] )
            if "stroke-width" in style:
                sw = style["stroke-width"]
                style["stroke-width"] = scaled_strokeWidth( sw, scale )
            el.attrib['style'] = style.cssText
        
        ## Scale line-width attributes elsewhere
        for el in root.findall(".//*[@stroke-width]"):
            sw = el.attrib['stroke-width']
            el.attrib['stroke-width'] = scaled_strokeWidth( sw, scale )
    
    
    ### 6 Save
    ## Put the default namespace back
    replace_namespace( root, namespace )
    tree.write( output_path )
    print( "Saved:", output_path )

def test():
    resize_svg( "../evaluation_examples/Art_freeform_AG_02-test.svg", long_edge = 1000 )

if __name__ == '__main__':
    # test()
    
    import argparse
    parser = argparse.ArgumentParser( description = 'Uniformly scale an SVG, including line widths. Does not handle transform attributes.' )
    parser.add_argument( "path_to_svg", help = "The SVG file to scale." )
    parser.add_argument( "--scale", type = float, help = "The scale factor to multiply with the current width and height." )
    parser.add_argument( "--width", type = float, help = "The target width." )
    parser.add_argument( "--height", type = float, help = "The target height." )
    parser.add_argument( "--long-edge", type = float, help = "The target long edge dimension." )
    parser.add_argument( "output_path", nargs = '?', default = None, help = "Where to save the resulting SVG. By default, saves to the input path with '-scaled' appended." )
    args = parser.parse_args()
    
    resize_svg( args.path_to_svg,
        scale = args.scale,
        width = args.width,
        height = args.height,
        long_edge = args.long_edge,
        output_path = args.output_path
        )

