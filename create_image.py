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
        cnt = 1
        for f in sorted(os.listdir(path)):
            filepath = os.path.join(path, f)
            if not os.path.isfile(filepath):
                continue
            if os.path.splitext(filepath)[1] != '.json':
                continue
            with open(filepath, 'r') as fh:
                json_data = fh.read()
            print('Loading  {}/{}'.format(d, f))
            name = '{}_{:03d}'.format(d, cnt)
            rundmd.load_json_animation_data(json_data, name=name)
            cnt += 1
    
    rundmd.finalize()
    image_path = os.path.join(base_dir, args.image.name)
    rundmd.write_full_binary(image_path)
