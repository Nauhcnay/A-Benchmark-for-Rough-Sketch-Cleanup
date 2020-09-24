# A Benchmark for Rough Sketch Cleanup

This is the code repository associated with the paper <a href="https://cragl.cs.gmu.edu/sketchbench/">*A Benchmark for Rough Sketch Cleanup* by Chuan Yan, David Vanderhaeghe, and Yotam Gingold from SIGGRAPH Asia 2020.</a>

This code computes the metrics described in the paper and generates the benchmark website
to compare the output of various sketch cleanup algorithms.

## The Directory Structure

Data directories are defined in the file `cfg.yaml`:

* `dataset_dir`: User puts the dataset here. Needed by the website.
* `alg_dir`: User puts automatic results here. Needed by the website.
* `web_dir`: We generate the website here. Image paths look like `../{alg_dir}/rest/of/path.svg`
* `table_dir`: We generate the metrics computed by the benchmark here. Needed to generate the website, but not needed when hosting the website. (A precomputed version for algorithms we tested is provided below.)
* `test_dir`: We generate resized image files for testing algorithms here. Needed also when computing metrics. Not needed by the website. (A precomputed version is provided below.)

The default values are
```
dataset_dir: './data/Benchmark_Dataset
alg_dir: './data/Automatic_Results'
web_dir: './data/web'
table_dir: './data/Evaluation_Data'
test_dir: './data/Benchmark_Testset'
```

If you are generating your own `test_dir` data, you need Inkscape and ImageMagick.
`run_benchmark.py` tries to find them according to your OS.
You can set the paths directly in `cfg.yaml` by changing `inkscape_path` and `magick_path` to point to Inkscape and ImageMagick's convert executable, respectively.


## Installing Code Dependencies

Clone or download this repository. The code is written in Python. It depends on the following modules: `aabbtree`, `CairoSVG`, `cssutils`, `matplotlib`, `numpy`, `opencv-python`, `pandas`, `Pillow`, `PyYAML`, `scipy`, `svglib`, `svgpathtools`, `tqdm`

You can install these modules with:
```bash
pip3 install -r requirements.txt
```
or, for a more reproducible environment, use [Poetry](https://python-poetry.org/docs/#installation) (`brew install poetry` or `pip install poetry`):
```bash
poetry install --no-root
poetry shell
```
or Pipenv (`pip install pipenv`):
```bash
pipenv install
pipenv shell
```
The `shell` command turns on the virtual environment.
It should be run once before running the scripts.

If you are not downloading the precomputed test images, make sure the following external software has been installed in your system:

1. [Inkscape 1.x](https://inkscape.org/). Please install an up-to-date Inkscape. Versions prior to 1.0 have incompatible command line parameters. `brew cask install inkscape` or `apt-get install inkscape`.
2. [ImageMagick](https://imagemagick.org/script/download.php). `brew install imagemagick` or `apt-get install imagemagick`.


## The Dataset and Precomputed Output

You can download the sketch dataset, precomputed algorithmic output, and computed metrics here: [Benchmark_Dataset.zip](https://drive.google.com/file/d/1UE5MfF3-HNdvCZWhSHGChNs3coKt6rlz/view?usp=sharing).

[`Benchmark_Dataset.zip` (900 MB)](https://cragl.cs.gmu.edu/sketchbench/Benchmark_Dataset.zip), [`Automatic_Results.zip` (440 MB)](https://cragl.cs.gmu.edu/sketchbench/Automatic_Results.zip), [`Evaluation_Data.zip` (20 MB)](https://cragl.cs.gmu.edu/sketchbench/Evaluation_Data.zip)
Unzip them in `./data/` (unless you changed the paths in `cfg.yaml`):
```bash
unzip Benchmark_Dataset.zip
unzip Automatic_Results.zip
unzip Evaluation_Data.zip
```


## Running

### Generating or Downloading the Testset

(If you are trying to regenerate the website from the paper using the precomputed output and already computed metrics, you do not need the Testset. If you want to change anything except the website itself, you need it.)

The Testset consists of files derived from the dataset: rasterized versions of vector images and downsized images.
You can regenerate it (see below) or download [`Benchmark_Testset.zip` (780 MB)](https://cragl.cs.gmu.edu/sketchbench/Benchmark_Testset.zip) and extract it into `./data/` (unless you changed the paths in `cfg.yaml`):
```bash
unzip Benchmark_Testset.zip
```

You can regenerate the Testset (necessary if you change the dataset itself) by running the following commands:
```bash
python3 run_benchmark.py --normalize   # generate normalized versions of SVGs
python3 run_benchmark.py --generate-test # generate rasterized versions of Dataset, at different resolutions
```

This will scan `dataset_dir` and `test_dir`, generate missing
normalized and rasterized images as needed.
It takes approximately 20 to 30 minutes to generate the entire Testset.

### Adding Algorithms to the Benchmark

Run your algorithm on all images in the Testset.
If your algorithm takes raster input, run on all images in `./data/Benchmark_Testset/rough/pixel`.
If your algorithm takes vector input, run on all images in `./data/Benchmark_Testset/rough/vector`.
For each input, save the corresponding output image as a file with the same name
in the directory: `./data/Automatic_Results/{name_of_your_method}{input_type}/{parameter}/`

The algorithm folder name must contain two parts:
`name_of_your_method` with an `input_type` suffix.
The `input_type` suffix must be either `-png` or `-svg`.
The parameter subdirectory can be any string;
the string `none` is replaced with the empty string when generating the website.
Folders beginning with a `.` are ignored.
For examples, see the precomputed algorithmic output in `./Automatic_Results`.
and evaluation result in `./Evaluation_Data` already.

If your algorithm runs via `alg path/to/input.svg path/to/output.png`, here are two example commands to run your algorithm in batch on the entire benchmark. Via `find` and `parallel`
```bash
find ./data/Benchmark_Testset/rough/pixel -name '*.png' -print0 | parallel -0 alg '{}' './data/Automatic_Results/MyAlgorithm-png/none/{/.}.svg'
```
Via `fd`:
```bash
fd ./data/Benchmark_Testset/rough/pixel -e png -x alg '{}' './data/Automatic_Results/MyAlgorithm-png/none/{/.}.svg'
```

### Computing the Metrics

Run the evaluation with the command:

```bash
python3 run_benchmark.py --evaluation
```   

This command creates CSV files in `./data/Evaluation_Data`.
It will not overwrite existing CSV files. If you downloaded the precomputed data, remove a file to regenerate it.

### Generating the Website to View Evaluation Results

After you have called the evaluation step above to compute the metrics, generate the website with the command:

```bash
python3 run_benchmark.py --website
```

You must also generate thumbnails once with the command:

```bash
python3 run_benchmark.py --thumbs
```

Internally, the `--thumbs` command creates a shell that calls `find`, `convert`, and `parallel`.

To view the website, open the `help.html` or `index.html` inside the `web_dir` manually or else call:

```bash
python3 run_benchmark.py --show
```

The website visualizes all algorithms' output and plots the metrics.

### Putting It All Together

If you don't want to call each step separately, simply call:

```bash
python3 run_benchmark.py --all
```

## Computing Metrics on a Single Sketch

### Similarity Metrics

To run the similarity metrics manually, use `tools/metric_multiple.py`. To get help, run:

```bash
python3 tools/metric_multiple.py --help
```

To compare two files:

```bash
python3 tools/metric_multiple.py -gt "example/simple-single-dot.png" -i "example/simple-single-dot-horizontal1.png" -d 0 --f-measure --chamfer --hausdorff
```

### Vector Metrics

To evaluate junction quality:

```bash
python3 tools/junction_quality.py --help
```

To compute arc length statistics:

```bash
python3 tools/svg_arclengths_statistics.py --help
```

### Rasterization

If you need to convert a file from an SVG to a PNG, you can do it specifying the output filename:

```bash
inkscape my_file.svg --export-filename="output-WIDTH.png" --export-width=WIDTH --export-height=HEIGHT
```
or specifying the output type (the input filename's extension is replaced):
```bash
inkscape my_file.svg --export-type=png --export-width=WIDTH --export-height=HEIGHT
```

The shorthand versions of the above rasterization commands are:

```bash
inkscape -o output-WIDTH.png -w WIDTH -h HEIGHT my_file.svg
```

or

```bash
inkscape --export-type=png -w WIDTH -h HEIGHT my_file.svg
```

If you pass only one of width or height, the other is chosen automatically in a manner preserving the aspect ratio.
