#!/usr/bin/env python3

import sys
import os
import argparse
import RunDmdImage


def parse_arguments():
    def dir_path(string):
        if os.path.isdir(string) and os.access(string, os.W_OK):
            return string
        try:
            os.makedirs(string)
            return string
        except:
            raise argparse.ArgumentTypeError('Unable to create or write to: {}'.format(string))

    parser = argparse.ArgumentParser(description='Rip all headers and animations from a RunDMD binary image')
    parser.add_argument('--image', help='RunDMD raw binary image path', type=argparse.FileType('r'), required=True)
    parser.add_argument('--output-dir', help='Path to extract the RunDMD yaml files to', type=dir_path, required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    rundmd = RunDmdImage.RunDmdImage()
    rundmd.load_full_binary(args.image.name)
    main_header_yaml = rundmd.get_header()
    output_dir = os.path.abspath(args.output_dir)
    os.chdir(output_dir)
    print('Writing main header')
    with open ('header.yaml', 'w') as fh:
        fh.write(main_header_yaml)

    prev_ani_name = None
    cur_ani_cnt = 0
    for ani in rundmd.get_animations():
        ani_name, ani_yaml = ani
        print('Processing yaml {}'.format(ani_name))
        if prev_ani_name != ani_name:
            ani_path = os.path.join(output_dir, ani_name)
            if not os.path.isdir(ani_path):
                os.mkdir(ani_path)
            os.chdir(ani_path)
            prev_ani_name = ani_name
            cur_ani_cnt = 0
        cur_file = '{}_{:03d}.yaml'.format(ani_name, cur_ani_cnt)
        print('Processing: file {}'.format(cur_file))
        with open(cur_file, 'w') as fh:
            fh.write(ani_yaml)
        cur_ani_cnt += 1
