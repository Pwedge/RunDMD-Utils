#!/usr/bin/env python3

import sys
import os
import argparse
import RunDmdImage


def parse_arguments():
    def dir_path(string):
        if os.path.isdir(string) and os.access(string, os.R_OK):
            return string
        else:
            raise argparse.ArgumentTypeError('Unable to read from: {}'.format(string))

    parser = argparse.ArgumentParser(description='Create a RunDMD binary image based on a directory with header and animation files')
    parser.add_argument('--input-dir', help='Path to read the extracted JSON files from', type=dir_path, required=True)
    parser.add_argument('--image', help='RunDMD raw binary image name to be created', type=argparse.FileType('w'), required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    input_dir = os.path.abspath(args.input_dir)
    base_dir = os.getcwd()

    rundmd = RunDmdImage.RunDmdImage()
    print('Loading header.json')
    os.chdir(input_dir)
    with open ('header.json', 'r') as fh:
        json_data = fh.read()
    rundmd.load_json_header_data(json_data)

    for d in sorted(os.listdir(input_dir)):
        path = os.path.join(input_dir, d)
        if not os.path.isdir(path):
            continue
        for f in sorted(os.listdir(path)):
            filepath = os.path.join(path, f)
            if not os.path.isfile(filepath):
                continue
            if os.path.splitext(filepath)[1] != '.json':
                continue
            with open(filepath, 'r') as fh:
                json_data = fh.read()
            print('Loading  {}/{}'.format(d, f))
            rundmd.load_json_animation_data(json_data)
    
    rundmd.finalize()
    image_path = os.path.join(base_dir, args.image.name)
    rundmd.write_full_binary(image_path)

    sys.exit(0)


    print('Loading and processing image')
    rundmd.load_full_binary(args.image.name)
    main_header_json = rundmd.get_header()
    output_dir = os.path.abspath(args.output_dir)
    os.chdir(output_dir)
    print('Writing header.json')
    with open ('header.json', 'w') as fh:
        fh.write(main_header_json)

    prev_ani_name = None
    cur_ani_cnt = 0
    for ani in rundmd.get_animations():
        ani_name, ani_json = ani
        if prev_ani_name != ani_name:
            ani_path = os.path.join(output_dir, ani_name)
            if not os.path.isdir(ani_path):
                os.mkdir(ani_path)
            os.chdir(ani_path)
            prev_ani_name = ani_name
            cur_ani_cnt = 0
        cur_file = '{}_{:03d}.json'.format(ani_name, cur_ani_cnt)
        print('Writing {}/{}'.format(ani_name, cur_file))
        with open(cur_file, 'w') as fh:
            fh.write(ani_json)
        cur_ani_cnt += 1
