'''
this script contains funcitons that organinzing 
and checking sketches, writing and reporting file status
Maybe I should call this file as dataset_api.py
'''
import csv
import os
from os.path import *
import xml.etree.ElementTree as ET
import numpy as np
import cv2
import shutil
import subprocess
from PIL import Image
try:
    import svg_standardize
    from svg_resize import resize_svg
except:
    from tools import svg_standardize
    from tools.svg_resize import resize_svg

color = {'BLK_AND_WHT':'1', 'GRAY':'L', 'RGBA':"RGBA"}

def get_header(file = None, row = None):
    '''
    Given:
        file, path to data set label csv file
        row, one row form the opened csv list, the row
            should be a dict, which looks like {header1: val1, ...}
    Return:
        a string list as the table header
    '''
    if file is not None:
        with open(file, 'r', newline = '') as f:
            reader = csv.reader(f)
            return next(reader)
    elif row is not None:
        keys = []
        for key in row:
            keys.append(key)
        return keys
    else:
        raise ValueError("Please give any one parameter of 'file' or 'row'")

def initial_sketch_list(header, save_name, path = None, sketch_tag = None, sket_list = None):
    '''
    Given:
        header, evaluation result table header
        save_name, name of table csv file
        path, path to the folder of testset rough input sketch
        sketch_tag, list of dict from opened alg log table
        sket_list, list of string as all names of test input rough sketch
    Caution:
        there should at least one of them is not None in [path, sketch_tag, sket_list]
    Action:
        generate and save a empty evaluation table csv file
    Return:
        a list of dict which contains the initialized evaluation table content
    '''
    sketch_list = []
    if path != None:
        for file in os.listdir(path):
            row = {}
            for i in range(len(header)):
                if i == 0:
                    row[header[i]] = file
                else:
                    row[header[i]] = ''
            sketch_list.append(row)
    elif sketch_tag != None:
        h = get_header(row = sketch_tag[0])
        for sketch in sketch_tag:
            row = {}
            for i in range(len(header)):
                if i == 0:
                    row[header[i]] = sketch[h[0]]
                else:
                    row[header[i]] = ''
            sketch_list.append(row)
    elif sket_list != None:
        for sketch in sket_list:
            row = {}
            for i in range(len(header)):
                if i == 0:
                    row[header[i]] = sketch
                else:
                    row[header[i]] = ''
            sketch_list.append(row) 
    else:
        raise ValueError("Insufficient table information")
    save_sketch_list(save_name, sketch_list)
    return sketch_list

def open_sketch_list(file, basemode = False):
    '''
    Given:
        file, path to dataset label csv file
        basemode, decide how to group and return the labels
    Return:
        1. basemode == True, return a single list of dict which contains all sketch labels
        2. basemode == False, return:
            sketch_list, list of all rough sketch, which is same as basemode's return
            cleaned_sketch_list, list of cleaned rough sketch
            cb_sketch_list, list of rough sketch which has additional clean background version
            rv_list, list of cleaned raster sketch only
            resize_list, list of sketch which has additional differnet size variants
    Caution:
        the first header should always be the sketch name
        the last header should always be the clean status (indicate if this sketch is cleaned or not)
        the second last header should always be background status (indicate the sketch's background type, like clean or texture)
    '''
    
    if not exists(file):
        print("Failed to open file at location: \n%s"%file)
        raise ValueError
    
    header = get_header(file = file)
    
    with open(file, newline = '') as f:
        
        dict_reader = csv.DictReader(f)
        sketch_list = [] # list of all sketches
        cleaned_sketch_list = [] # list of sketches with gt
        cb_sketch_list = [] # list of sketches with clean background version
        rv_list = [] # list of vector rough sketches
        resize_list = [] # list of sketches that need to generate additional size variants
        
        if basemode:
            # basic mode, return all information readed from file
            for row in dict_reader:
                sketch_list.append(row)
            return sketch_list
        else:
            for row in dict_reader:
                sketch_list.append(row)
                if row[header[-1]].lower() == 'yes':
                    cleaned_sketch_list.append(row[header[0]] + ".png")
                    # hard code for artist gw, one of his works are raster sketches but without clean backgournd version
                    if (row[header[-2]].lower() == 'clean' or 'paper' in row[header[-2]].lower()) and\
                            'Art_freeform_GW_01'.lower() not in row[header[0]].lower():
                        cb_sketch_list.append(row[header[0]] + "_cb.png")
                        resize_list.append(row[header[0]] + "_cb.png")
                    if row[header[-2]].lower() != 'clean (vector)':
                        rv_list.append(row[header[0]] + ".png")
                    if row[header[-2]].lower() == 'clean (vector)' or \
                        ('Art_freeform_GW_01'.lower() in row[header[0]].lower() and
                        row[header[-2]].lower() == 'clean'):
                        resize_list.append(row[header[0]] + ".png")
            return sketch_list, cleaned_sketch_list, cb_sketch_list, rv_list, resize_list

def save_sketch_list(file, sketch_list):
    '''
    Given:
        file, full path to save as a csv file
        sketch_list, a list of dict as whole table
    Action:
        save sketch_list as a csv table
    '''

    # it will over write old table if exists
    with open(file, 'w', newline = '') as f:
        header = get_header(row = sketch_list[0])
        dict_writer = csv.DictWriter(f, fieldnames = header)
        dict_writer.writeheader()
        for row in sketch_list:
            dict_writer.writerow(row)

def extract_file_list_from(sketch_source, mode = "base"):
    '''
    Given
        sketch_source, could be one of the following types:
            1. path to the sketch folder
            2. a python list which returned by open_sketch_list(), it should be a list of dict
    Return:
        all or subset sketch name list from sketch_source, which depends:      
            1. mode == "full", return all sketch's full name
            2. mode == "base", return all sketch's base name, sketches with same base name will be combined
            3. mode == "gt", return all sketch's gt name
    '''

    extension_list = ['.svg', '.png']
    sketch_list = []
    
    if str == type(sketch_source):
        for file in os.listdir(sketch_source):
            name, extension = os.path.splitext(file)
            if extension in extension_list:
                if "full" == mode:
                    sketch = file
                else:
                    sketch = extract_sketch_name(file, mode)
                if sketch not in sketch_list:
                    sketch_list.append(sketch)
    
    elif list == type(sketch_source):
        header = get_header(row = sketch_source[0])
        for row in sketch_source:
            sketch_list.append(row[header[0]] + ".png")
    else:
        raise ValueError("Unsupported sketch source, only str or list are supported")

    return sketch_list

def extract_sketch_name(sketch_name, mode = 'base'):
    '''
    Given
        sketch_name, full sketch name
        mode, decide what protion of sketch name will be extracted:
            base: extract basename only
            gt: extract basename + author name
            full: don't remove any thing, return sketch name directly
    Return
        extracted name
    '''
    name, extension = os.path.splitext(sketch_name)
    name_list = name.strip().split('_')
    # a base sketch name will always have 4 levels
    # or 5 levels for ground turth
    if 'gt' == mode:
        return '_'.join(name_list[0:5]) + extension
    elif 'base' == mode:
        return '_'.join(name_list[0:4]) + extension
    elif 'extra' == mode:
        return '_'.join(name_list[0:6]) + extension
    elif 'full' == mode:
        return sketch_name
    else:
        print("Unsupport mode %s, please check mode name"%mode)
        raise ValueError
    

def compare_file_list(list1, list2):
    '''
    Given:
        list1, list2, contain list of file names
    Return:
        list of names that in list2 but not in list1
    '''
    list1_without_ext = []
    list2_without_ext = []

    # remove extension name if exists
    for i in list1:
        name, _ = os.path.splitext(i)
        list1_without_ext.append(name)
    for i in list2:
        name, _ = os.path.splitext(i)
        list2_without_ext.append(name)
    
    # find difference
    find_list = []
    for item in list2_without_ext:
        if item not in list1_without_ext:
            find_list.append(item)
    return find_list

def check_sketch_status(config, sketch_list, png_dir, svg_dir, gt_dir, cleaned_list = None):
    '''
    Given：
        sketch_list, list of all rough sketches
        png_dir, path to pixel rough sketch folder
        svg_dir, path to vector rough sketch folder
        gt_dir, path to vector cleaned sketch folder
        cleaned_list, list of rough sketch which has been cleaned
    Action:
        check the completeness of benchmark dataset, inlucding:
            1. check if all rough sketch have same size as cleaned sketch
            2. check if clear background version of rough sketch recorded in sketch_list really exists
            3. check if vector rough sketch recorded in sketch_list really exists
            4. check if cleaned sketch recorded in cleaned_list really exists, if cleaned_list if None, then re-index cleaned sketch
        report scan result
    
    '''
    need_report = False
    png_list = extract_file_list_from(png_dir)
    # make sure there is no duplicate name in list
    assert(len(png_list) == len(set(png_list)))
    png_list_full = extract_file_list_from(png_dir, mode = "full")
    svg_list = extract_file_list_from(svg_dir)
    assert(len(svg_list) == len(set(svg_list)))
    svg_list_full = extract_file_list_from(svg_dir, mode = "full")
    gt_list = extract_file_list_from(gt_dir)
    gt_list_with_author = extract_file_list_from(gt_dir, mode = "gt")
    gt_list_full = extract_file_list_from(gt_dir, mode = "full")
    assert(len(gt_list) == len(set(gt_list)))
    png_list_csv = extract_file_list_from(sketch_list)
    assert(len(png_list_csv) == len(set(png_list_csv)))
    
    # make sure every gt should have 3 different version
    assert(3 * len(gt_list) + 2 == len(gt_list_with_author))
    

    # get scan result of cleaned sketch statistics
    cleaned_list_scan, baseline_num_scan, cleaned_sketch_num_scan = get_cleaned_list(png_list_full)
    
    # if cleaned_list statistics from sketch label is not given, initialize it from the scan result
    if cleaned_list is None:
        print("Error: No cleaned sketch statistics in label, initialize it with scaned result")
        cleaned_list = cleaned_list_scan
        header = get_header(row = sketch_list[0])
        # reset sketch labels accroding to scan result
        for sketch in cleaned_list:
            name, _ = os.path.splitext(sketch)
            row, i = find_sketch(sketch_list, name)
            row[header[-1]] = True
            row[header[-2]] = True
            sketch_list[i] = row
        print("Log:\tsaving initialized label as %s"%config["label"])
        save_sketch_list(config["label"], sketch_list)

    # else compare results from scanning and label, report any difference
    elif len(cleaned_list) != len(cleaned_list_scan) or len(png_list) != len(png_list_csv):
        need_report = True
        print("Error: Inconsistency found!")
        not_in_csv = compare_file_list(cleaned_list, cleaned_list_scan)
        if len(not_in_csv) > 0:
            print("Error: Missing label cleaned sketches:\n%s"%('\n'.join(not_in_csv)))
        
        not_in_folder = compare_file_list(cleaned_list_scan, cleaned_list)
        if len(not_in_folder) > 0:
            print("Error: Missing scan cleaned sketches:\n%s"%('\n'.join(not_in_folder)))
        
        not_in_csv = compare_file_list(png_list_csv, png_list)
        if len(not_in_csv) > 0:
            print("Error: Missing label sketches:\n%s"%('\n'.join(not_in_csv)))
        
        not_in_folder = compare_file_list(png_list, png_list_csv)
        if len(not_in_folder) > 0:
            print("Error: Missing scan sketches:\n%s"%('\n'.join(not_in_folder)))
    
    # check file completeness in gt sketch folder and vector rough sketch folder
    svg_missing_list = []
    gt_missing_list = []
    missing_size_cb = []
    missing_size_rv = []
    missing_size_gt = []
    baseline_num = 0

    for sketch in cleaned_list:
        name, extension = os.path.splitext(sketch)
        
        # check if rough vector exist
        if "baseline" in name:
            baseline_num += 1
        if name + ".svg" not in svg_list:
            svg_missing_list.append(sketch)
            size_rv = None
        else:
            rvs = get_sketches_by_name(svg_list_full, sketch)
            assert(len(rvs) == 1)
            size_rv = get_sketch_size(rvs[0], path = svg_dir)
        
        # check if gt exist
        size_gts = []
        if name + ".svg" not in gt_list:
            gt_missing_list.append(sketch)
        else:
            gts = get_sketches_by_name(gt_list_full, sketch)
            for gt in gts:
                size_gts.append(get_sketch_size(gt, path = gt_dir))
        if (name + "_cb.png") in png_list_full:
            size_cb = get_sketch_size(name + "_cb.png", path = png_dir)
        else:
            size_cb = None
        size_org = get_sketch_size(sketch, path = png_dir)
        if size_org != size_cb and size_cb is not None:
            missing_size_cb.append(name + "_cb.png")
        if size_org != size_rv and size_rv is not None and abs(size_org[1] - size_rv[1]) > 1:
            s = size_org[0] / size_rv[0]
            if abs(size_org[1] - s*size_rv[1]) > 1:
                print("Report: resize error on %s"%join(svg_dir, name + ".svg"))
                print("Report: target size: %s"%str(size_org))
                print("Report: current size: %f, %f"%(s*size_rv[0], s*size_rv[1]))
                print("Report: please fix it manually")
                missing_size_rv.append(rvs[0])
            else:
                try:
                    resize_svg(join(svg_dir, name + ".svg"), width=size_org[0], height = size_org[1],
                        output_path = join(svg_dir, name + ".svg"))
                except AssertionError as e:
                    print("Report: resize error on %s"%join(svg_dir, name + ".svg"))
                    print("Report: target size: %s"%str(size_org))
                    print("Report: current size: %f, %f"%(s*size_rv[0], s*size_rv[1]))
                    print("Report: please fix it manually")
                    missing_size_rv.append(rvs[0])

        for i in range(len(size_gts)):
            if size_org != size_gts[i]:
                s = size_org[0] / size_gts[i][0]
                if abs(size_org[1] - s*size_gts[i][1]) > 1:
                    missing_size_gt.append(gts[i])
                    print("Report: resize error on %s"%join(join(gt_dir, gts[i])))
                    print("Report: target size: %s"%str(size_org))
                    print("Report: current size: %f, %f"%(s*size_gts[i][0], s*size_gts[i][1]))
                    print("Report: please fix it manually")
                else:
                    try:
                        resize_svg(join(gt_dir, gts[i]), width=size_org[0], height = size_org[1],
                            output_path = join(gt_dir, gts[i]))
                    except AssertionError as e:
                        print("Report: resize error on %s"%join(gt_dir, gts[i]))
                        print("Report: target size: %s"%str(size_org))
                        print("Report: current size: %f, %f"%(s*size_gts[i][0], s*size_gts[i][1]))
                        print("Report: please fix it manually")
                        missing_size_gt.append(gts[i])

    # print out summary
    assert baseline_num == baseline_num_scan
    print("Log:\tscan result:")
    print("\t" + "="*20)
    print("\tBaseline:\t%d"%baseline_num)
    print("\tWild sketch:\t%d"%(len(cleaned_list) - baseline_num))
    print("\tTotal:\t\t%d / %d"%(len(cleaned_list), len(sketch_list)))
    print("\tMissing vector rough:\t%d "%len(svg_missing_list))
    if len(svg_missing_list) > 0:
        print("\t\t\n".join(svg_missing_list))
        need_report = True
    print("\tMissing ground turth:\t%d"%len(gt_missing_list))
    if len(gt_missing_list) > 0:
        print("\t\t\n".join(gt_missing_list))
        need_report = True
    print("\tMiss match size of clear background:\t%d"%len(missing_size_cb))
    if len(missing_size_cb) > 0:
        print("\t\t\n".join(missing_size_cb))
        need_report = True
    print("\tMiss match size of vector rough:\t%d"%len(missing_size_rv))
    if len(missing_size_rv) > 0:
        print("\t\t\n".join(missing_size_rv))
        need_report = True
    print("\tMiss match size of ground turth:\t%d"%len(missing_size_gt))
    if len(missing_size_gt) > 0:
        print("\t\t\n".join(missing_size_gt))
        need_report = True
    print("\t" + "="*20)
    if need_report:
        print("Log:\tData completeness check failed!\nFollowing steps are recommended before evaluation:\n 1. check and fix them manually\n 2. re-normalize dataset")
        print("Log:\tDo you wish to continue anyway? [y]/n")
        
        def yes_no():
            yes = set(['yes','y', 'ye', ''])
            no = set(['no','n'])
             
            while True:
                choice = input().lower()
                if choice in yes:
                   return True
                elif choice in no:
                   return False
                else:
                   print ("Log:\tPlease respond with 'yes' or 'no'\n")
        if yes_no() == False:
            quit()

def get_sketches_by_name(sketch_list_full, sketch, layers = None):
    '''
    Given
        sketch_list_full, list of all GT sketch name
        sketch, sketch base name
        layers, list of layer name as a filter, only sketch with the given layers will be collected
    Return
        sketches, list of GT sketch name with same base name
    '''
    sketches = []
    key, _ = os.path.splitext(sketch)
    for sketch in sketch_list_full:
        name, extension = os.path.splitext(sketch)
        if key in name:
            if layers is not None:
                for layer in layers:
                    if layer in name:
                        sketches.append(sketch)
            elif "norm" not in name:
                sketches.append(sketch)
    return sketches

def group_sketch_by_name(sketch_list_full, sketch_list_basic, mode = 'test', alg = None):
    '''
    Given:
        sketch_list_full, a list of dict that contains all rough sketches record from a algorithm execu log
            or a list of string that contains all gt sketches full name
        sketch_list_basic, a list of str that contains rough sketch basename 
        mode, grouping mode, all of them doing the same function, but just treat sketch_list_full as different data structure
            if mode is test, treat sketch_list_full as list of dict
            if mode is gt, treat sketch_list_full as list of string
        alg, algorithm name
    Return:
        A dict that grouped by base name
    '''
    sketch_group_dict = {}
    if mode == 'test':
        h = get_header(row = sketch_list_full[0])
        for base in sketch_list_basic:
            if base not in sketch_group_dict:
                sketch_group_dict[base] = []
            name, _ = splitext(base)
            if alg.lower() == "strokeaggregator":
                base = name + ".png"
            for sketch in sketch_list_full:
                # only collect rough sketch that has been cleaned successfully
                # (the running time record is a number, not error message)
                if sketch[h[1]].isnumeric() and name in sketch[h[0]]:
                    sketch_group_dict[base].append(sketch[h[0]])
    elif mode == 'gt':
        for base in sketch_list_basic:
            name, _ = splitext(base)
            for sketch in sketch_list_full:
                if name in sketch:
                    if base in sketch_group_dict:
                        sketch_group_dict[base].append(sketch)
                    else:
                        sketch_group_dict[base] = [sketch]
    else:
        raise ValueError("Wrong grouping mode %s"%mode)
    return sketch_group_dict

def get_cleaned_list(png_full_list, verbal = False):
    '''
    Given:
        png_full_list, full name list of all rough sketches
    Return:
        cleaned_list, scan result as a list which contains cleaned sketch only
        baseline_num, number of baseline sketch
        cleaned_sketch_num, number of cleaned wild sketch
    '''
    cleaned_list = []
    baseline_num = 0
    cleaned_sketch_num = 0
    cb_sketch_num = 0
    for sketch in png_full_list:
        name, extension = os.path.splitext(sketch)
        name_list = name.split('_')
        if "baseline" in name_list and "cb" not in name_list:
            baseline_num += 1        
            cleaned_list.append(sketch)
        else:
            if ("cb" not in name_list and name + "_cb.png" in png_full_list) \
                or "Art_freeform_GW_01" == name:
                cleaned_sketch_num += 1
                cleaned_list.append(sketch)
        if "cb" in name_list:
            cb_sketch_num += 1            
    sketch_total_num = len(png_full_list) - cb_sketch_num
    
    if verbal:
        print('=' * 20)
        print("Folder scan result")
        print('=' * 20)
        print("Baseline:\t%d"%baseline_num)
        print("Cleaned:\t%d"%cleaned_sketch_num)
        print("Total:\t%d/%d"%(baseline_num+cleaned_sketch_num, sketch_total_num))
    return cleaned_list, baseline_num, cleaned_sketch_num

def find_sketch(sketch_list, name):
    '''
    Given a sketch_list, a specific name
    Return dictionary of found sketch and corresponding index
    Assume the name of sketch will be a key value in the whole dataset
    '''
    header = get_header(row = sketch_list[0])
    for i in range(len(sketch_list)):
        if name == sketch_list[i][header[0]]:
            return sketch_list[i], i
    return False, False

def update_sketch(sketch_list, index, rows):
    # maybe this function is not neccessary
    assert(len(index) == len(rows))
    for i in range(len(index)):
        sketch_list[index[i]] = rows[i]

def compare_sketch_size(sketch1, sketch2, path1 = None, path2 = None):
    '''
    Given two sketches, which could be svg or png format
    Return if the size of two sketches are same
    '''
    size1 = get_sketch_size(sketch1, path1)
    size2 = get_sketch_size(sketch2, path2)
    if size1 == size2:
        return True
    else:
        return False

def get_sketch_size(sketch, path = None, root = None):
    '''
    Given:
        sketch, pixel sketch(.png) or vector sketch(.svg) name
        path, path to search folder
        root, xml root element
    Return:
        the size of sketch in give path with same name
        if path is given, it could be either png file or svg file
        if root is given, it could only be a xml root element of a svg file
    Caution:
        The unit of svg artboart should only be "pixel"
    '''
    cwd = os.getcwd()
    if path is not None:
        os.chdir(path)

    if sketch is None:
        if root is None:
            print("xml mode detected, but no root given!")
            raise ValueError
        else:
            extension = '.svg'
    else:
        _, extension = os.path.splitext(sketch)
    if '.svg' == extension:
        if root is None:
            tree = ET.parse(sketch)
            root = tree.getroot()
        if "viewBox" in root.attrib:
            if ',' in root.attrib['viewBox']:
                width = float(root.attrib['viewBox'].split(',')[2])
                height = float(root.attrib['viewBox'].split(',')[3])
            else:
                width = float(root.attrib['viewBox'].split(' ')[2])
                height = float(root.attrib['viewBox'].split(' ')[3])
        elif "width" in root.attrib and "height" in root.attrib:
            width = float(root.attrib['width'].strip('px'))
            height = float(root.attrib['height'].strip('px'))
        else:
            print("Error:\tparsing svg failed")
        os.chdir(cwd)
        return width, height
    elif '.png' == extension:
        img = Image.open(sketch)
        os.chdir(cwd)
        width, height = img.size
        return (float(width), float(height))
    else:
        print("Error:\tunspport input")
        raise ValueError

def add_suffix(file, suffix):
    name, extension = os.path.splitext(file)
    return name+suffix+extension

def open_images(input_a, input_b, mode = 'BLK_AND_WHT', debug = False, size = None, thres = None, force = False):
    '''
    Given:
        input_a as cleaned raster sketch
        input_b as ground truth
    Return:
        PIL object of input_a and input_b
    Support file type:
        png, jpg, bmp

    NOTE: Black and white mode thresholds at 50%.
          If you want a different threshold, use mode = 'GRAY'
          and do it yourself.
    '''
    if os.path.splitext(input_a.lower())[-1] in ('.png', '.jpg', '.bmp'):
        img_a = Image.open(input_a)
    else:
        raise TypeError('Invalid file type ' + os.path.splitext(input_a)[-1])
    w_a, h_a = img_a.size
    if os.path.splitext(input_a.lower())[-1] in ('.png', '.jpg', '.bmp'):
        img_b = Image.open(input_b)
    else:
        raise TypeError('Invalid file type' + os.path.splitext(input_b)[-1])
    w_b, h_b = img_b.size
    if mode == 'BLK_AND_WHT': print( "Warning: open_images( ..., mode='BLK_AND_WHT' ) thresholds at 50%." )
    if thres:
        img_a = img_a.convert(color["GRAY"], dither=Image.NONE)
        img_a = img_threshold(img_a)
        img_b = img_b.convert(color["GRAY"], dither=Image.NONE)
        img_b = img_threshold(img_b)

    else:
        img_a = img_a.convert(color[mode], dither=Image.NONE)
        if debug: img_a.save(add_suffix(input_a, "thresholded"))
        img_b = img_b.convert(color[mode], dither=Image.NONE)
        if debug: img_b.save(add_suffix(input_b, "thresholded"))
        # assume the size of two sketch should aways the same
    if force:
        try:
            h1, w1 = img_a.size
            h2, w2 = img_b.size
        except:
            print("Error:\tget image size failed")
            raise ValueError()
        # check two img size ratio 
        assert(abs(h1/w1 - h2/w2) < 0.001)
        if h1 > h2:
            img_a = img_a.resize(img_b.size)
        elif h2 > h1:
            img_b = img_b.resize(img_a.size)
    
    if img_a.size != img_b.size:
        print("Error:\timage size of two images are different. %s vs. %s"%(str(img_a.size), str(img_b.size)))
        raise ValueError()
    return img_a, img_b

def png_resize(path_to_png, size, path_to_magick, save_dir = None, save_name = None):
    '''
    Given
        path_to_png, path to original png file
        size, new size of longer side
        path_to_magick, path to magick
        save_dir, path to new png folder
        save_name, new png name
    Action:
        create a resized new png file
    '''
    path, png = os.path.split(path_to_png)
    name, extension = os.path.splitext(png)
    if save_dir is None:
        save_dir = path
    if save_name is None:
        save_name = name + "_" + str(size) + ".png"
    subprocess.run([path_to_magick, path_to_png, "-resize", "%dx%d"%(size, size), join(save_dir, save_name)])

def img_threshold(image, save_dir = None, save_name = None, win = 11, const = 2):
    '''
    Given a PIL image, aussme image color is always grayscale
    Return a thresholded PIL image 
    '''
    img = np.asarray(image)
    img = cv2.fastNlMeansDenoising(img)
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, win, const)
    im = Image.fromarray(img)
    if save_name is not None and save_dir is not None:
        im.save(join(save_dir, save_name), '.png')
    return im

def image_to_mask(img):
    img_a = np.array(img)
    pixel_max = np.max(img_a)
    return img_a == pixel_max

def image_to_points(img):
    img_a = np.array(img)
    pixel_max = np.max(img_a)
    indices = np.nonzero(np.abs(np.array(img)-pixel_max))
    points = np.array(indices).T
    return points, indices

def image_to_boolean_array( img, threshold = 0.25 ):
    '''
    Given:
        img: A PIL Image whose values range from 0 to 255.
        threshold: A in [0,1]. Pixels blacker than threshold are interpreted as black.
    Returns:
        An boolean numpy array with the same width and height as `img` with
        a True value for every black pixel.
    '''
    arr = np.asfarray( img.convert('L') )/255.
    boolean_arr = (arr < (1.0 - threshold))
    return boolean_arr

def generate_test_set(config):
    '''
    Action:
        Generate rough test sketch and clean ground truth with different size and layers

    '''

    # initialize paths
    png_dir = join(normcase(config['dataset_dir']), normcase("Rough/PNG"))
    svg_dir = join(normcase(config['dataset_dir']), normcase("Rough/SVG"))
    gt_dir = join(normcase(config['dataset_dir']), "GT")
    path_to_label = normcase(config['label'])
    path_to_test_set = normcase(config['test_dir'])
    path_to_ink = config["inkscape_path"]
    path_to_magick = config["magick_path"]

    # initailize sketch layers and size config
    rough_layers = config['rough_layers']
    gt_layers = config['gt_layers']
    size_list = config['size']

    # create test set folder if necessary
    if isdir(path_to_test_set) is False:
        os.makedirs(path_to_test_set)

    path_to_gt_png = join(path_to_test_set, normcase(config["gt_png"]))
    if isdir(path_to_gt_png) is False:
        os.makedirs(path_to_gt_png)
    
    path_to_png = join(path_to_test_set, normcase(config["test_png"]))
    if isdir(path_to_png) is False:
        os.makedirs(path_to_png)
    
    path_to_svg = join(path_to_test_set, normcase(config["test_svg"]))
    if isdir(path_to_svg) is False:
        os.makedirs(path_to_svg)

    # get all sketch full name list from sketch folder
    gt_list_full = extract_file_list_from(gt_dir, mode = "full")
    svg_list_full = extract_file_list_from(svg_dir, mode = "full")

    # get all sketch name list from label
    sketches, cleaned_list, cb_list, rv_list, resize_list = open_sketch_list(path_to_label)
    
    # check if name lists from different source match to each other 
    print("Log:\tscan sketch folders")
    check_sketch_status(config, sketches, png_dir, svg_dir, gt_dir, cleaned_list)
    
    count_test = 0
    count_gt = 0
    

    # copy all cleaned base sketch to test path
    print("Log:\tcopying files to testset folder %s"%config['test_dir'])
    gts = []
    for png in cleaned_list:
        if exists(join(path_to_png, png)) is False:
            shutil.copyfile(join(png_dir, png), join(path_to_png, png))
            count_test += 1
        gts += get_sketches_by_name(gt_list_full, png, gt_layers)
        

    for png in cb_list:
        if exists(join(path_to_png, png)) is False:
            shutil.copyfile(join(png_dir, png), join(path_to_png, png))
            count_test += 1

    # rasterize corresponding vector sketch to test path
    remove_list = []
    for png in cleaned_list:
        name, _ = os.path.splitext(png)
        for layer in rough_layers:
            # need to copy the test svg sketches as well
            if (name + layer + '.svg') in svg_list_full and exists(join(path_to_svg, name + layer + '.svg')) is False:
                shutil.copyfile(join(svg_dir, name + layer + '.svg'), join(path_to_svg, name + layer + '.svg'))
            # this is not a good way to check if rasterization has been done.
            if png in rv_list:
                if exists(join(path_to_png, name + layer + '_1000.png')) is False and (name + layer + '.svg') in svg_list_full:
                    svg_standardize.to_png(join(svg_dir, name + layer + '.svg'), path_to_ink, 'base', None, png_dir, save_dir = path_to_png)
                    remove_list.append(name + layer + '.png')
                elif (name + layer + '.svg') in svg_list_full:
                    remove_list.append(name + layer + '.png')
    
    # generate all test sketch variants in testset folder
    print("Log:\tgenerate rough sketch variants with size %s"%str(size_list))
    resize_list += remove_list
    for png in resize_list:
        for size in size_list:
            if exists(join(path_to_png, png[:-4] + "_%d.png"%size)) is False:
                png_resize(join(path_to_png, png), size, path_to_magick, path_to_png)
                count_test += 1
    for png in remove_list:
        try:
            os.remove(join(path_to_png, png))
        except:
            pass

    
    # rasterize corresponding gt sketch to gt sketch folder
    print("Log:\trasterize GT sketch")
    for gt in gts:
        if exists(join(path_to_gt_png, gt[0:-4] + '.png')) is False:
            svg_standardize.to_png(join(gt_dir, gt), path_to_ink, 'base', None, png_dir, save_dir = path_to_gt_png)
            count_gt += 1
    print("Log:\tgenerate GT sketch variants with size %s"%str(size_list))
    for gt in gts:
        for size in size_list:
            if exists(join(path_to_gt_png, gt[:-4] + "_%d.png"%size)) is False:
                png_resize(join(path_to_gt_png, gt[0:-4] + '.png'), size, path_to_magick, path_to_gt_png)
                count_gt += 2
    
    # output summary
    print("Log:\trough sketches:\t%d created\n\tclean sketches:\t%d created"%(count_test, count_gt))


def get_external_link_command(folder):
    from sys import platform
    if (platform == "linux" or platform == "linux2") or\
        (platform == "darwin"):

        return "ln -s ../%s ./%s"%(folder, folder)
    elif platform == "win32":
        # Windows...
        return "mklink /J .\\%s ..\\%s"%(folder, folder)
    else:
        print("Error:\tunspport platform")
        raise ValueError

def get_external_exec_path(program):
    '''
    Action:
        find external execuatable app path, Inkscape and Magick
        These two app have different path on different platform
    '''
    from sys import platform
    search_path = {
        "inkscape":{
            "name": "Inkscape",
            "linux" : "/usr/bin/inkscape",
            "linux2" : "/usr/bin/inkscape",
            "darwin" : "/Applications/Inkscape.app/Contents/MacOS/inkscape",
            "win32" : "C:/Program Files/Inkscape/inkscape.exe",
        },
        "magick":{
            "name" : "ImageMagick convert",
            "linux" : "/usr/bin/convert",
            "linux2" : "/usr/bin/convert",
            "darwin" : "/usr/local/bin/convert",
            "win32" : "C:/Program Files/ImageMagick-7.0.9-Q16/magick.exe"
        }
    }

    if not exists(search_path[program][platform]):
        print(f"Error:\t can't find {search_path[program]['name']} in your system, please install it before evaluation, or set path in cfg.yaml")
        raise ValueError()
    return search_path[program][platform]

def init_alg_log(save_name, test_dir, alg_out_dir, mode = 'png'):
    '''
    Given:
        save_name, full path to save initailized log
        test_dir, path to the testset rough sketch
        alg_out_dir, path to the folder of algorithm results
        mode, the testset file type which algorithm used as input
            "png" means pixel test input
            "svg" means vector test input
    Action:
        generate a csv version of log file
    Reture:
        sketch list, which is a list of dictionary
    '''

    header = ["Sketch Name", "Used Time"]
    sketch_list = []

    alg_out_list = os.listdir(alg_out_dir)
    test_list = os.listdir(test_dir)
    
    # check if input files have correct name format
    i = len(alg_out_list)-1
    while i >= 0:
        if ".png" not in alg_out_list[i]:
            alg_out_list.pop(i)
        i -= 1

    assert(len(test_list) >= len(alg_out_list))
    not_in_test = compare_file_list(test_list, alg_out_list)
    if len(not_in_test) > 0:
        print("Error:\tinvalid input %s"%str(not_in_test))
        raise ValueError

    # initialize sketch list
    for file in test_list:
        name, extension = splitext(file)
        row = {}
        if extension.strip('.') == mode:
            row[header[0]] = file
            if name+".png" in alg_out_list:
                row[header[1]] = -1
            else:
                row[header[1]] = ""
            sketch_list.append(row)
    # write sketch list
    if exists(save_name) == False:
        with open(save_name, 'w', newline = '') as f:
            dict_writer = csv.DictWriter(f, fieldnames = header)
            dict_writer.writeheader()
            for row in sketch_list:
                dict_writer.writerow(row)
    else:
        print("Error:\tfind old version log file %s, initalization stopped"%save_name)
    return sketch_list

def scan_algs(alg_dir):
    '''
    Action:
        scan folder in `alg_dir`, build up the index of benchmark algorithms
    Return:
        alg_scan, A dict that contains all algorithm which is going to be evaluated
    '''
    alg_scan = {"alg_list":[]}
    for alg in os.listdir(alg_dir):
        ## Skip files beginning with ".", since they are often hidden files
        ## like ".DS_Store".
        if alg.startswith('.'): continue
        
        alg_name, input_type = alg.rsplit("-",1)
        if input_type not in ("svg","png"):
            print("Warn:\tfailed to detect algorithm's input type, use raster file (png) as default")
            input_type = "png"
        alg_scan[alg_name] = {"input_type": input_type, "folder": alg}

        # scan subfolder as parameter 
        alg_scan["alg_list"].append(alg_name)
        for parameter in os.listdir(join(alg_dir, alg)):
            ## Skip files beginning with ".", since they are often hidden files
            ## like ".DS_Store".
            if parameter.startswith('.'): continue
            alg_scan[alg_name].setdefault("parameter", []).append([parameter, join(alg_dir, alg, parameter)])
    return alg_scan
