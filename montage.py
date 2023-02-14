import json
import os
import sys
import shlex
import subprocess
import re
import tempfile

def get_modded_filename(orig_file):
    sep_index = input_file.rfind(".")
    if sep_index < 0:
        return orig_file + "_mod"
    else:
        return orig_file[:sep_index] + "_mod." + orig_file[sep_index+1:]  

def get_file_extension(orig_file):
    sep_index = input_file.rfind(".")
    if sep_index < 0:
        return "mp4"
    else:
        return orig_file[sep_index+1:]

def get_video_info(video_file):
    info_cmd = "ffmpeg -i " + input_file
    info_data = subprocess.Popen(info_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = info_data.communicate()
    # print("Stream data: ", stdout)
    # print("Stream error: ", stderr)
    return stderr.decode('utf-8')

def get_geometry(video_file):
    info_data = get_video_info(video_file)
    for line in info_data.splitlines():
        if line.find("Stream") >=0  and line.find("Video") >= 0:
            geom_match = geometry_pattern.search(line)
            if (geom_match):
                geom = geom_match.group().replace("x", ":")
                break
    return geom

def get_rotation(video_file):
    info_data = get_video_info(video_file)
    for line in info_data.splitlines():
        if line.find("rotate") >=0  and line.find(":") >= 0:
            rotation = line.split(":")[1]
            rotation = rotation.strip()
            if rotation == "90":
                transpose = "1"
            elif rotation =="-90":
                transpose = "2"
            else:
                transpose = "0"
            break
    return transpose
    

# main flow
############################################################################

if len(sys.argv) <= 1:
    print("Usage:", sys.argv[0], "<input_file> [<resized_geometry>]")
    print("   where <input_file> - path to the input file which will be sliced and montaged")
    print("     and <resized_geometry> - optional, geometry of the final file")
    print("         (if omitted, geometry of input file will be preserved)")
    sys.exit(1)

input_file = sys.argv[1]
if len(sys.argv) > 2:
    resized_geometry = sys.argv[2]
else:
    resized_geometry = None

if not input_file:
    print("Error: no input filename was provided in the arguments list")
    sys.exit(1)

ext = get_file_extension(input_file) 
montaged_file = get_modded_filename(input_file)

geometry_pattern = re.compile("([0-9]{2,}x[0-9]+)")

print("Getting geometry and rotation of the input file ...")
geom = get_geometry(input_file)
rotation = get_rotation(input_file)
print("Geometry:", geom)
print("Rotation:", rotation)

# load the slices.json information file
slices_file = "slices.json"
if not slices_file:
    print("Error: no file with slice information was provided")
    sys.exit(1)
data = json.load(open("slices.json", "r"))
slices = data['slices']

# create a concat temp file and use it to perform part concatenation
concat_file = tempfile.NamedTemporaryFile(dir=".", delete=False)
try:
    for slice in slices:
        slice_file = slice['name'] + "." + ext
        print("creating slice:", slice_file, "....")
        slice_cmd = "ffmpeg -y -ss " + slice['start'] + " -to " + slice['end'] + " -i " + input_file + " -c copy " + slice_file
        print("command: ", slice_cmd)
        os.system(slice_cmd)
        print("Writing slice file", slice_file, "to tempfile", concat_file.name)
        slice_info = "file '" + slice_file + "'\n"
        concat_file.write(str.encode(slice_info))
finally:
    concat_file.close()

print("concatenating part files into a final video ...")
if resized_geometry:
    concat_cmd = "ffmpeg -y -f concat -i " + concat_file.name + " -vf \"scale=" + resized_geometry + ",transpose=" + rotation + "\" -acodec aac -b:a 256k -preset slow " + montaged_file
else:
    concat_cmd = "ffmpeg -y -f concat -i " + concat_file.name + " -c:v copy -acodec aac -b:a 256k " + montaged_file

os.system(concat_cmd)

os.unlink(concat_file.name)

sys.exit(0)
