import os
import glob
import csv
try:
    import junction_quality
    import svg_arclengths_statistics
    import files
except:
    from tools import junction_quality, files
    from tools import svg_arclengths_statistics

from numpy import mean, median, percentile

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

def generate_stroke_analyze_csv(config, path_to_table = None, alg = None, p = None, 
                                path_to_csv = None, path_to_svg_folder = None):
    '''
    '''
    # initialize path information
    if path_to_table != None and alg != None and p != None:
        path_to_csv = os.path.join(path_to_table, "Stroke_Analysis", "SA_%s_%s.csv"%(alg, p[0]))
        path_to_svg_folder = p[1]
    elif path_to_csv != None and path_to_svg_folder != None:
        print("Log:\tworking in command line mode")
    else:
        print("Error:\tincorrect parameter")

    # initalize header
    # let's use messiness instead of number strokes!
    header = ["sketch", "arc_len_min", "arc_len_25-th", "arc_len_median", 
              "arc_len_75-th", "arc_len_max", "arc_len_mean", "junc_min_dist_sum", "junc_dist_count_0.1", "used time"]

    if os.path.exists(path_to_csv):
        print("Log:\tfind %s exists, skip stroke analyze"%path_to_csv)
        return None
    else:
        print("Log:\tcreating stroke analysis table: %s"%path_to_csv)

    row_list = []

    log = os.path.join(config['log_dir'], "%s_%s.csv"%(alg, p[0]))

    alg_input_full_tag = files.open_sketch_list(log, basemode = True)
    h = files.get_header(row = alg_input_full_tag[0])
    
    

    for i in range(len(alg_input_full_tag)):
        
            
        file = alg_input_full_tag[i][h[0]]
        name, extension = os.path.splitext(file)
        file = name + ".svg"
        path_to_svg = os.path.join(path_to_svg_folder, file)
        running_time = alg_input_full_tag[i][h[1]]
    
        
        if os.path.exists(path_to_svg):
            print("Log:\topen %s"%path_to_svg)
            
            # evaluate svg paths, there may have some exception case that interrupt analysis
            # so any expection will be caught and recorded
            try:
                lengths = svg_arclengths_statistics.arc_length_statistics(path_to_svg)
                arc_num = len(lengths)
                arc_mean = mean( lengths )
                arc_min = min( lengths )
                arc_25 = percentile( lengths, 25 )
                arc_50 = median( lengths )
                arc_75 = percentile( lengths, 75 )
                arc_max = max( lengths )
            
            except ValueError as e:
                print("Log:\t" + str(e))
                arc_num = "svgpathtool open error"
                arc_mean = "svgpathtool open error"
                arc_min = "svgpathtool open error"
                arc_25 = "svgpathtool open error"
                arc_50 = "svgpathtool open error"
                arc_75 = "svgpathtool open error"
                arc_max = "svgpathtool open error"
            except Exception as e:
                print("Log:\t" + str(e))
                arc_num = "unknown error"
                arc_mean = "unknown error"
                arc_min = "unknown error"
                arc_25 = "unknown error"
                arc_50 = "unknown error"
                arc_75 = "unknown error"
                arc_max = "unknown error"
                
            
            try:
                minimum_distances = junction_quality.endpoint_statistics(path_to_svg)
                junc_sum = minimum_distances.sum()
                junc_count = ( minimum_distances > 0.0001 ).sum()
            except ValueError as e:
                print("Log:\t" + str(e))
                junc_sum = "svgpathtool open error"
                junc_count = "svgpathtool open error"
            except RecursionError as e:
                print("Log:\t" + str(e))
                junc_sum = "excess of points"
                junc_count = "excess of points"
            except Exception as e:
                print("Log:\t" + str(e))
                if "has not yet been implemented" in str(e):
                    junc_sum = "svgpathtool func error"
                    junc_count = "svgpathtool func error"
                else:
                    junc_sum = "unknown error"
                    junc_count = "unknown error"
                
            
            value = [file, arc_min, arc_25, arc_50, arc_75, arc_max, arc_mean,
                    junc_sum, junc_count, running_time]
            row = {}
            for i in range(len(header)):
                row[header[i]] = value[i]
            row_list.append(row)
                # write results
           
    # write csv
    folder, _ = os.path.split(path_to_csv)
    if os.path.isdir(folder) is False:
        os.makedirs(folder)
    
    with open(path_to_csv, 'w', newline = '') as f:
        dict_writer = csv.DictWriter(f, fieldnames = header)
        dict_writer.writeheader()
        for row in row_list:
            dict_writer.writerow(row)

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser( description = "Compute svg stroke statistics and write to csv" )
    parser.add_argument( "svg", help = "The root folder of algorithm output (SVG file) to analyze." )
    parser.add_argument( "csv", help = "Path to save the analyze csv results" )
    args = parser.parse_args()

    generate_stroke_analyze_csv(path_to_csv = args.csv, path_to_svg_folder = args.svg)
