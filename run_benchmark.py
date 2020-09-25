from os.path import *
from pathlib import Path
from PIL import Image
from tools import files, svg_standardize
from tools import metric_multiple
from tools import metrics_stroke
from tools import load_as_melted, load_vector_quality
from tools import svg_arclengths_statistics as svg_len
from tools import thumbnails

import csv
import os, sys
import cv2
import subprocess
import numpy as np
import xml.etree.ElementTree as ET
import yaml
import argparse

def generate_test_table(config, table_mode, alg = None, p = None):
    '''
    Given:
        table_mode, decide what kink of table will be created for current algorithm
            if table_mode is 0, generate auto_to_auto table
            if table_mode is 1, generate auto_to_auto table
            if table_mode is 2, generate gt_to_gt table
        alg, algrithm name
        p, algrithm parameter
    Action:
        generate corresponding evaluation talbe to given path
    '''

    # only gt_to_gt table doesn't need algorithm name and parameter
    if alg == None or p == None:
        assert table_mode == 2

    
    else:
        # find current algorithms output reuslt path, test input path, parameter and execute log
        parameter = p[0]
        path_test_result = p[1]
        log = join(config['log_dir'], "%s_%s.csv"%(alg, parameter))
        if config[alg]["input_type"] == "png":
            path_test = join(config["test_dir"], config["test_png"])
        elif config[alg]["input_type"] == "svg":
            path_test = join(config["test_dir"], config["test_svg"])

        # if the log file is missing, reconstruct it by scanning the path_test_result
        # the running time will not exists of course, it will be set as -1
        if exists(log) is False:
            print("Log:\tcan't find run log, start to initilize %s"%log)
            files.init_alg_log(log, path_test, path_test_result, mode = config[alg]["input_type"])

        # get full sketch list and log table header from log files
        alg_input_full_tag = files.open_sketch_list(log, basemode = True)
        h = files.get_header(row = alg_input_full_tag[0])

    # find the path to test png and gt png images for ambiguity and messiness computation
    path_test_atg = join(normcase(config['test_dir']), normcase(config['test_png']))
    path_gt = join(normcase(config['test_dir']), normcase(config['gt_png']))
    test_input_full_list = files.extract_file_list_from(path_test_atg, mode = 'full')
    test_input_base_list = files.extract_file_list_from(path_test_atg, mode = 'base')
    
    # find evaluation parameter
    distance_start = config['dis_start']
    distance_end = config['dis_end']
    distance_step = config['dis_step']
    target_layer = config['rough_layers']
    table_dir = config['table_dir']
    
    # generate header of test table
    header = generate_header(table_mode, config['authors'], 
        distance_start, distance_end, distance_step,
        config["ambiguity_distance"])
    
    
    
    # get gt input full list, base list, grouped list
    gt_full_list = files.extract_file_list_from(path_gt, mode = "full")
    gt_base_list = files.extract_file_list_from(path_gt, mode = "gt")
    gt_dict = files.group_sketch_by_name(gt_full_list, gt_base_list, mode = 'gt')
    
    # generate table file name
    if 0 == table_mode:
        table_name = "Auto_to_GT_%s_%s.csv"%(alg, parameter)
        table_dir = join(table_dir, "Auto_to_GT")
    if 2 == table_mode:
        table_name = "GT_to_GT.csv"
        table_dir = table_dir
    if exists(table_dir) is False:
        os.makedirs(table_dir)
    
    # if exists the target tabel already, skip all following steps
    if exists(join(table_dir, table_name)) and alg != None and parameter != None:
        # open existing file
        print("Log:\t %s exists, skip evaluation for %s with parameter %s"%(
            join(table_dir, table_name), alg, parameter))
        return None
    else:
        # initilize csv file and tag
        if 0 == table_mode:
            sketch_list = files.initial_sketch_list(header, join(table_dir, table_name), sketch_tag = alg_input_full_tag)
            assert(len(alg_input_full_tag) == len(sketch_list))
        if 1 == table_mode or 2 == table_mode:
            sketch_list = files.initial_sketch_list(header, join(table_dir, table_name), sket_list = test_input_base_list)
            assert(len(test_input_base_list) == len(sketch_list))
    
    
    
    if 0 == table_mode: #auto to gt
        for i in range(len(sketch_list)):
            input_file_name = sketch_list[i][header[0]]
            input_name, extension = splitext(input_file_name)
            gt_by_same_name = get_gt_by_sketch(input_file_name, gt_full_list)
            input_file_name = splitext(input_file_name)[0] + '.png'
            used_time = alg_input_full_tag[i][h[1]]
            
            # compute the stroke number
            strokes = \
                len(svg_len.arc_length_statistics(join(config['test_dir'], 
                    config['test_svg'], 
                    '_'.join(input_name.split('_')[0:4])+"_norm_full.svg")))
            

            # compute the dot pixel number
            if exists(join(path_test_atg, input_file_name)):
                print("Log:\topen %s"%join(path_test_atg, input_file_name))
                img_rough = Image.open(join(path_test_atg, input_file_name)).convert("L", dither=Image.NONE)
            else:
                print(input_file_name)
                assert 'strokeaggregator' == alg.lower()
                print("Log:\topen %s"%join(path_test_atg, '_'.join(input_name.split('_')[0:4]) + ".png"))
                img_rough = Image.open(join(path_test_atg, '_'.join(input_name.split('_')[0:4]) + ".png")).convert("L", dither=Image.NONE)
            pixels_rough_05 = (files.image_to_boolean_array(img_rough, threshold = 0.05)).sum()
            pixels_rough_25 = (files.image_to_boolean_array(img_rough, threshold = 0.25)).sum()
            
            # record resolution, strokes, pxiles and pxiel
            sketch_list[i][header[1]] = (img_rough.size[0] * img_rough.size[1])
            sketch_list[i][header[2]] = strokes
            
            sketch_list[i][header[3]] = pixels_rough_05
            sketch_list[i][header[4]] = pixels_rough_05 / (img_rough.size[0] * img_rough.size[1])

            sketch_list[i][header[6]] = pixels_rough_25
            sketch_list[i][header[7]] = pixels_rough_25 / (img_rough.size[0] * img_rough.size[1])

            # generate distance sequence
            distance = []
            d = distance_start
            while d <= distance_end:
                distance.append(d)
                d += distance_step

            messi_05 = 0
            messi_25 = 0
            # evaluate current sketch to each gt by author
            for au in gt_by_same_name:
                # get basename and sketch size for the gt sketch
                gt_name = '_'.join(input_name.split('_')[0:4])
                gt_size = input_name.split("_")[-1]

                # check if the automatic cleaned sketch is resized
                if "500" == gt_size or "1000" == gt_size:
                    # we should always expect a ideal cleaned sketch should similar to 
                    # the groundturth sketch with cleaned layer only, 
                    # whatever input rough sketch is (norm cleaned or norm full)
                    gt_name_list = [gt_name, au, "norm_cleaned", gt_size]
                else:
                    gt_name_list = [gt_name, au, "norm_cleaned"]
                gt_file_name = "_".join(gt_name_list) + '.png'
                
                assert(gt_file_name in gt_by_same_name[au])
                
                # compute messiness for the rough input to current cleaned sketch 
                # print("Log:\topen %s"%join(path_gt, gt_file_name))
                # img_clean = Image.open(join(path_gt, gt_file_name)).convert("L", dither=Image.NONE)
                
                # pixels_clean = (files.image_to_boolean_array(img_clean, threshold = 0.05)).sum()
                # messi_05 += pixels_rough_05 / pixels_clean
                
                # pixels_clean = (files.image_to_boolean_array(img_clean, threshold = 0.25)).sum()
                # messi_25 += pixels_rough_25 / pixels_clean

                # compute all evaluation metric
                print("Log:\tevalutaing %s and %s"%(input_file_name, gt_file_name))
                test_result = join(path_test_result, input_file_name)
                gt = join(path_gt, gt_file_name)
                
                if used_time.isnumeric() or used_time == "-1": #if this sketch is cleaned successfully then evaluate it         
                    eval_result = metric_multiple.run(test_result, gt, 
                        set(config['metrics']), distances = distance, visualize=False)
                    
                    # update it to current tag
                    if "f_score" in set(config['metrics']):
                        for j in range(len(distance)):
                            key = au + "_%d"%(distance[j])
                            assert key in sketch_list[i]    
                            sketch_list[i][key] = eval_result['f_score'][j]
                    if "chamfer" in set(config['metrics']):
                        key = au + "_%s"%("chamfer")
                        assert key in sketch_list[i]
                        sketch_list[i][key] = eval_result['chamfer']
                    if "hausdorff" in set(config['metrics']):
                        key = au + "_%s"%("hausdorff")
                        assert(key in sketch_list[i])
                        sketch_list[i][key] = eval_result['hausdorff']
                else:# algorithm fail on this input, set everything as failed
                    for title in sketch_list[i]:
                        for au in gt_by_same_name:
                            if au in title:
                                sketch_list[i][title] = "N/A" 

            # messi_05 /= len(gt_by_same_name)
            # messi_25 /= len(gt_by_same_name)

            # sketch_list[i][header[5]] = messi_05
            # sketch_list[i][header[8]] = messi_25

            sketch_list[i][header[-1]] = used_time

    if 2 == table_mode:# gt_to_gt
        distance = config["ambiguity_distance"]
        for i in range(len(sketch_list)):
            
            # get gt name
            gt_file_name = sketch_list[i][header[0]]
            gt_name, _ = splitext(gt_file_name)
            
            # get author list from sketch base name
            au_list = get_gt_by_sketch(gt_file_name, gt_full_list)
            
            # initialize metric variables
            ambiguity_sum_union = 0
            ambiguity_sum_f1 = [0] * len(distance)
            ambiguity_sum_chamfer = 0
            ambiguity_sum_hausdorff = 0
            avg_count = 0
            pixels_gt = 0
            pixels_test = 0
            gt_count = 0

            # construct rough sketch name, we compute all messiness on uniformed sketch size
            test = "_".join([gt_name, "norm_full_1000"]) + '.png'
            if test not in test_input_full_list:
                test = "_".join([gt_name, "1000"]) + '.png'
            assert(test in test_input_full_list)
            

            # main loop for ambiguity and messiness computation
            for au1 in au_list:
                # construct gt sketch of author1
                gt1 = "_".join([gt_name, au1, "norm_cleaned"]) + '.png'
                gt = "_".join([gt_name, au1, "norm_cleaned_1000"]) + '.png'
                assert gt in au_list[au1]

                # some sketches don't contain 2 layers. for those sketches,
                # the normalization code will only generate "*_norm_full.svg".
                # if gt1 not in au_list[au1]:
                #     print( "Warn:\timage not found, falling back to all layers:", gt1 )
                #     gt1 = "_".join([gt_name, au1, "norm_full"]) + '.png'
                #     gt = "_".join([gt_name, au1, "norm_full_1000"]) + '.png'
                
                # open the uniformed size rough sketch and gt sketch 
                # count the number of pixels of gt sketch and sketch number
                # the messiness will be (pixel number of rough sketch) / (average pixles number of gt sketches)
                img_gt, img_test = files.open_images(join(path_gt, gt), join(path_test_atg, test), mode = 'GRAY')
                pixels_gt += (files.image_to_boolean_array(img_gt) == True).sum()
                gt_count += 1
                
                # compute ambiguity
                for au2 in au_list:
                    if au1 != au2:
                        # construct gt sketch of author2
                        gt2 = "_".join([gt_name, au2, "norm_cleaned"]) + '.png'
                        assert gt2 in au_list[au2]

                        # some sketches don't contain 2 layers. for those sketches,
                        # the normalization code will only getnerate "*_norm_full.svg".
                        if gt2 not in au_list[au2]:
                            print( "Warn:\timage not found, falling back to all layers:", gt2 )
                            gt2 = "_".join([gt_name, au2, "norm_full"]) + '.png'
                        
                        # compute ambiguity between au1 and au2
                        ambiguity_sum_union += (1-compute_consistency((gt1, gt2), path_gt))
                        eval_result = metric_multiple.run(join(path_gt, gt1), 
                            join(path_gt, gt2), set(config['metrics']), 
                            distances = distance, visualize=False, force = True)
                        for j in range(len(distance)):
                            ambiguity_sum_f1[j] += (1 - eval_result['f_score'][j])
                        ambiguity_sum_chamfer += eval_result['chamfer']
                        ambiguity_sum_hausdorff += eval_result['hausdorff']
                        avg_count += 1
            
            # sum and averge ambiguities between all authors
            ambiguity_sum_union = ambiguity_sum_union / avg_count
            for j in range(len(distance)):
                ambiguity_sum_f1[j] = ambiguity_sum_f1[j] / avg_count
            ambiguity_sum_chamfer = ambiguity_sum_chamfer / avg_count
            ambiguity_sum_hausdorff = ambiguity_sum_hausdorff / avg_count
            ambiguity_all = [ambiguity_sum_union] + ambiguity_sum_f1 +\
                        [ambiguity_sum_chamfer] + [ambiguity_sum_hausdorff] 
            
            # compute messiness
            pixels_test = (files.image_to_boolean_array(img_test)).sum()
            messiness = pixels_test / (pixels_gt / gt_count)
            
            # record compute results
            sketch_list[i][header[1]] = messiness
            for j in range(2, len(header)):
                sketch_list[i][header[j]] = ambiguity_all[j-2]
            

    files.save_sketch_list(join(table_dir, table_name), sketch_list)       

def generate_header(mode, authors, distance_start, distance_end, distance_step, distance_ambiguity):
    '''
    Given:
        mode, what kind of table header to gerenate
            mode 0: generate auto to gt header
            mode 1: generate auto to auto header
            mode 2: generate gt to gt header
        authors, complete author name list
        distance_start, the start of distance used in f1 score computation of auto to gt metiric
        distance_end, the end of distance used in f1 score computation of auto to gt metiric
        distance_step, the step length between distance_start and distance_end in auto to gt metiric
        distance_ambiguity, a list of distances for gt to gt ambiguity
    Return:
        a string list as table header
    '''
    if 0 == mode:
        # precision and recall mode
        auto_to_gt_header = ['Input']
        # auto_to_gt_header.append("Resolution")
        # auto_to_gt_header.append("Strokes")
        # auto_to_gt_header.append("Pixels_0.05")
        # auto_to_gt_header.append("Pixel_ratio_0.05")
        # auto_to_gt_header.append("Messiness_0.05")
        # auto_to_gt_header.append("Pixels_0.25")
        # auto_to_gt_header.append("Pixel_ratio_0.25")
        # auto_to_gt_header.append("Messiness_0.25")
        for author in authors:
            d = distance_start
            while d <= distance_end: 
                auto_to_gt_header.append(author+"_%d"%(d))
                d += distance_step
            auto_to_gt_header.append(author+"_%s"%('chamfer'))
            auto_to_gt_header.append(author+"_%s"%('hausdorff'))

        auto_to_gt_header.append("Used time")
        return auto_to_gt_header
    if 1 == mode:
        # consistency mode
        auto_to_auto_header = ["Input", "org-cb", "500-1000-raster", 
        "500-1000-vector-full", "500-1000-vector-rough"]
        return auto_to_auto_header
    if 2 == mode:
        # messiness and ambiguity mode
        header_f1 = []
        for d in distance_ambiguity:
            header_f1.append("Ambiguity_f1_%d"%d)
        gt_to_gt_header = ["GT", "Messiness", "Ambiguity_union"] + header_f1 +\
         ["Ambiguity_chamfer", "Ambiguity_hausdorff"]
        return gt_to_gt_header


def get_gt_by_sketch(sketch, gt_list):
    '''
    Given:
        sketch, name of a single sketch
        gt_list, full list of all gt sketches
    Return:
        a dict as retrieves that contains all gt sketch with same base name of that given sketch
        all gts are also grouped by author name, such as {author1: [gt1, gt2,...], ...}
    '''
    
    gt_dict_by_test = {}
    name, _ = splitext(sketch)
    base_sketch_name = '_'.join(name.split('_')[0:4])
    for gt in gt_list:
        gt_name, _ = splitext(gt)
        author = gt_name.split('_')[4]
        if base_sketch_name in gt:
            if author in gt_dict_by_test:
                gt_dict_by_test[author].append(gt)
            else:
                gt_dict_by_test[author] = [gt]
    return gt_dict_by_test

def eval(config, algs):
    '''
    Given:
        algs, algorithm list that is going to be evaluated
    Action:
        generate evaluation result table
    '''
    
    path_to_ink = normcase(config['inkscape_path'])
    png_dir = join(normcase(config['test_dir']), normcase(config['test_png']))
    
    for alg in algs:
        # localize config infomations
        for pl in config[alg]['parameter']:
            # get automatic reuslt path for each parameter
            p = pl[0]
            save_dir = pl[1]
            # rasterize svg to png if necessary 
            if 'auto_to_gt' in config["table_list"]:
                # check if evaluation result already exists
                path_to_table = join(config["table_dir"], "Auto_to_GT", "Auto_to_GT_%s_%s.csv"%(alg, p))
                print("Log:\tstart creating %s"%path_to_table)
                if (exists(path_to_table)):
                    print("Log:\tfind evaluation table exists, skip creating: %s"%path_to_table)
                else:
                    # normalize and rasterize all svg files
                    print("Log:\tnormalize and rasterize auto results in %s"%save_dir)
                    for file in os.listdir(save_dir):
                        name, extension = splitext(file)
                        if extension == '.svg':
                            if exists(join(save_dir, name + '.png')) == False:
                                # normalize and rasterize svg
                                if config[alg]["input_type"] == "svg": 
                                    svg_standardize.run_single(join(save_dir, file), path_to_ink, 
                                        save_dir = None, norm = 0.001, add_transform = False, 
                                        inplace = True)
                                    # mode decide which sketch should be referenced to get the target size
                                    svg_standardize.to_png(join(save_dir, file), path_to_ink, mode = 'base', 
                                        target_size = None, png_dir = png_dir, save_dir = None)    
                                
                                elif config[alg]["input_type"] == "png":
                                    svg_standardize.run_single(join(save_dir, file), path_to_ink, 
                                        save_dir = None, norm = 0.001, inplace = True)
                                    svg_standardize.to_png(join(save_dir, file), path_to_ink, mode = 'full', 
                                        target_size = None, png_dir = png_dir, save_dir = None)
                                else:
                                    print("Error:\tcan't recognize input type: %s"%config[alg]["input_type"])
                                    raise ValueError

                    print("Log:\tcreate auto_to_gt evaluation table for: %s"%(
                        join(config["table_dir"], "Auto_to_GT", "%s_%s.csv"%(alg, p))))
                    print("Log:\tevaluation metric:")
                    for i in range(len(config['metrics'])):
                        print(" \t%d. %s"%(i+1, config['metrics'][i]))
                    generate_test_table(config, table_mode = 0, alg = alg, p = pl)
            
            # generate stroke anaylsis table
            metrics_stroke.generate_stroke_analyze_csv(config, 
                path_to_table = config["table_dir"], 
                alg = alg, p = pl)

    if 'gt_to_gt' in config["table_list"]:
        # generate ambiguity table
        if exists(join(config["table_dir"], "GT_to_GT.csv")):
            print("Log:\tfind GT_to_GT.csv exists, skip generating table")
        else:
            print("Log:\t create gt_to_gt evaluation table at %s"%join(config["table_dir"], "GT_to_GT.csv"))
            generate_test_table(config, table_mode = 2)

def procedure_all(config):

    # self check if all path configuration is correct
    print("Log:\tdataset path:\t%s"%config['dataset_dir'])
    print("Log:\ttestset path:\t%s"%config['test_dir'])
    print("Log:\tlabel path:\t%s"%config['label'])

    ink, magick = config["inkscape_path"], config["magick_path"]
    print("Log:\tInkscape path:\t%s"%ink)
    print("Log:\tMagick path:\t%s"%magick)

    # standardize all svg files
    if config['normalize']:
        svg_dir = join(normcase(config['dataset_dir']), normcase("Rough/SVG"))
        gt_dir = join(normcase(config['dataset_dir']), "GT")
        print("Log:\tnormalize testset...")
        svg_standardize.run_batch(svg_dir, ink, None, norm = 0.001, remove_rough = False)
        print("Log:\tnormalize testset complete")
        print("Log:\tnormalize gt set...")
        svg_standardize.run_batch(gt_dir, ink, None, norm = 0.001, remove_rough = True)
        print("Log:\tnormalize gt set complete")

    # generate whole test benchmark data, skip this stage if exist testing folder
    if config['generate_test']:
        print("Log:\tgenerating testset...")
        files.generate_test_set(config)
        print("Log:\tgenerating testset complete")


    # evaluate all automatic results and generate metric table
    if config['evaluation']:
        # evaluate 
        print("Log:\tstart evaluation...")
        eval(config, config['alg_list'])
        print("Log:\tevaluation complete")

    # TODO: integrate benchmark HTML here, or we can just ask user to update the benchmark manunally

    # Create web output directory
    if (config["thumbs"] or config["website"]) and not Path( config['web_dir'] ).is_dir()  :
        os.makedirs(Path(config['web_dir']))
    
    if config["thumbs"]:
        print("Log:\tgenerating thumbnails for HTML pages...")
        
        thumbs_dir = Path( config['web_dir'] ) / 'thumbs'
        if not thumbs_dir.is_dir(): os.makedirs( thumbs_dir )
        thumbnails.create_thumbnails_recursive(
            ( Path(config['dataset_dir']) / 'Rough'/ 'JPG' ).rglob('*.jpg'),
            lambda p: thumbs_dir / p.name,
            config["magick_path"],
            '200x', '70%'
            )
        
        thumbs_dir = Path( config['web_dir'] ) / 'thumbs' / 'auto'
        if not thumbs_dir.is_dir(): os.makedirs( thumbs_dir )
        thumbnails.create_thumbnails_recursive(
            Path(config['alg_dir']).rglob('*.png'),
            lambda p: thumbs_dir / str(p.with_suffix('.jpg').relative_to(Path(config['alg_dir']))).replace('/','_'),
            config["magick_path"],
            '200x', '70%'
            )

    if config["website"]:
        print("Log:\tupdating benchmark HTML pages...")
        
        load_as_melted.load(
            sorted((Path(config['table_dir'])/'Auto_to_GT').glob('Auto_to_GT*.csv')),
            Path(config['table_dir'])/"Auto_to_GT.csv"
            )

        load_vector_quality.load(
            sorted((Path(config['table_dir'])/'Stroke_Analysis').glob('SA_*.csv')),
            Path(config['table_dir'])/"vector_quality.csv"
            )

        from html_generator.script import generate_html_pages
        # generate_html_pages.init_globals(config['dataset_dir'], config['alg_dir'], config['table_dir'], config['web_dir'])
        generate_html_pages.generate_pages()
        generate_html_pages.generate_sketch_pages()

        import shutil
        for directory in ("css","js","pkg"):
            from_directory = Path("html_generator")/directory
            to_directory = Path(config['web_dir'])/directory

            if (Path(config['web_dir'])/directory).exists():
                shutil.rmtree(to_directory)
            shutil.copytree(from_directory, to_directory)

    # open the page
    if config["show"]:
        import webbrowser
        webbrowser.open("file://" + realpath(f"{config['web_dir']}/help.html"))
        

def compute_consistency(img_pair, path_to_input, visualize = False):
    '''
    Given:
        img_pair, image names as a list, which length should always eq 2
        path_to_input, path to both images
        visualize, visualize the union and instersection of two images if true
        sketch name and path to two sketches
    Return:
        consistency score
    '''
    img_name1 = img_pair[0]
    img_name2 = img_pair[1]
    
    if not exists(join(path_to_input, img_name1)) or not exists(join(path_to_input, img_name1)):
        print("Error:\tpath error, %s and %s"%(join(path_to_input, img_name1), join(path_to_input, img_name1)))
        raise ValueError
    img1 = cv2.imread(join(path_to_input, img_name1),0)
    img2 = cv2.imread(join(path_to_input, img_name2),0)
    if visualize:
        plt.imshow(img1)
        plt.show()
        plt.imshow(img2)
        plt.show()
    # resize the larger image to smaller size
    try:
        h1, w1 = img1.shape
        h2, w2 = img2.shape
    except:
        print("Error:\topen image failed")
        raise ValueError
    # check two img size ratio 
    assert(abs(h1/w1 - h2/w2) < 0.01)
    if h1 > h2:
        img1 = cv2.resize(img1, (w2, h2))
    elif h2 > h1:
        img2 = cv2.resize(img2, (w1, h1))
    # img1 = cv2.threshold(img1, 0, 255, cv2.THRESH_BINARY)
    # img2 = cv2.threshold(img2, 0, 255, cv2.THRESH_BINARY)
    
    img1 = cv2.adaptiveThreshold(img1, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 3)
    img2 = cv2.adaptiveThreshold(img2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 3)
    if visualize:
        plt.imshow(img1)
        plt.show()
        plt.imshow(img2)
        plt.show()
    # thanks to https://stackoverflow.com/questions/11262312/opencv-intersection-between-two-binary-images
    img_intersection = cv2.bitwise_or(img1, img2)
    img_union = cv2.bitwise_and(img1, img2)
    if visualize:
        plt.imshow(img_intersection)
        plt.show()
        plt.imshow(img_union)
        plt.show()
    
    return abs(img_intersection.astype(float)/255. - 1).sum() / abs(img_union.astype(float)/255. - 1).sum()

if __name__ == "__main__":
    # get args ready
    parser = argparse.ArgumentParser(description='Sketch Cleanup Benchmark')
    parser.add_argument('--evaluation', action="store_true", help ='If present, evaluates all automatic outputs in ./alg_out')
    parser.add_argument('--website', action="store_true", help ='If present, generates a website to visualize the evaluated output')
    parser.add_argument('--thumbs', action="store_true", help ='If present, updates thumbnails when generating the website. (Ignored if --website is not present.)')
    parser.add_argument('--show', action="store_true", help ='If present, opens the website in a browser window after website generation completes. (Ignored if --website is not present.)')
    parser.add_argument('--all', action="store_true", help ='If present, equivalent to all options (generates and evaluates everything and opens a browser window when complete)')
    parser.add_argument('--normalize', action="store_true", help ='If present, normalizes input SVG appearance and saves a raster copy.')
    ## argparse replaces '-' with '_' for the result of `parse_args()`.
    parser.add_argument('--generate-test', action="store_true", help ='If present, generates downsampled images.')
    args = parser.parse_args()
   
    # read configuration
    with open("cfg.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # verify dataset folder exists
    assert exists(config["dataset_dir"])
    assert exists(config["alg_dir"])

    alg_scan = files.scan_algs(config["alg_dir"])

    # update config
    config.update(alg_scan)

    for key in ("normalize", "generate_test", "evaluation", "website", "thumbs", "show"):
        config[key] = config[key] or vars(args).get(key) or args.all
        print (f'{key} : {config[key]}')
        
    for program in ["inkscape", "magick"]:
        
        if f"{program}_path" not in config.keys():
            print(f"{program} path is not specified in cfg.yaml. Trying to find it in a standard location.")
            config[f"{program}_path"] = files.get_external_exec_path(program)
  
    # start main process
    procedure_all(config)
    
