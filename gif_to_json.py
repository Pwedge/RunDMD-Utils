#!/usr/bin/env python3

import sys
import os
import argparse
import RunDmdImage
import json
from PIL import Image

def parse_arguments():
    def dir_path(string):
        if os.path.isdir(string) and os.access(string, os.R_OK):
            return string
        else:
            raise argparse.ArgumentTypeError('Unable to read from: {}'.format(string))

    parser = argparse.ArgumentParser(description='Create a RunDMD binary image based on a directory with header and animation files')
    parser.add_argument('--input-gif', help='Input GIF filename', type=argparse.FileType('r'), required=True)
    parser.add_argument('--frame-start', help='Starting frame number', type=int)
    parser.add_argument('--frame-end', help='Ending frame number', type=int)
    parser.add_argument('--x-start', help='Starting X coordinate', type=int)
    parser.add_argument('--x-end', help='Ending X coordinate', type=int)
    parser.add_argument('--y-start', help='Starting Y coordinate', type=int)
    parser.add_argument('--y-end', help='Ending Y coordinate', type=int)
    parser.add_argument('--output-json', help='Output JSON filename', type=argparse.FileType('w'), required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    original = Image.open(args.input_gif.name)
    #original.show()

    width, height = original.size
    left = 0
    right = width
    top = 0
    bottom = height
    if args.x_start:
        left = args.x_start
    if args.x_end:
        right = args.x_end
    if args.y_start:
        top = args.y_start
    if args.y_end:
        bottom = args.y_end

    buckets = 15
    map_vals = []
    stride = 256 // buckets
    for i, s in enumerate(range(0, 255, stride)):
        if i >= 10:
            map_vals.append((s, s + stride - 1, i + 1))
        else:
            map_vals.append((s, s + stride - 1, i))
    s, e, i = map_vals[-1]
    map_vals[-1] = (s, 255, i)

    ani = RunDmdImage.RunDmdAnimation()
    ani.load_binary_animation_header(bytearray(ani.block_size))

    for frame_index in range(original.n_frames):
        original.seek(frame_index)
        cropped = original.crop((left, top, right, bottom))
        #cropped.show()

        resized = cropped.resize((128, 32))
        #resized.show()

        greyscale = resized.convert('LA')
        #greyscale.show()

        img_str = ''
        for y in range(32):
            for x in range(128):
                #print('{},{}: {}'.format(x, y, greyscale.getpixel((x,y))))
                l, a = greyscale.getpixel((x,y))
                if a == 0:
                    img_str += 'a'
                else:
                    for s, e, i in map_vals:
                        if l >= s and l <= e:
                            img_str += '{:x}'.format(i)
        frame_rows = ani._frame_to_rows(img_str)
        frame_info = {'duration' : original.info['duration'], 'bitmap' : frame_rows}
        ani.frames.append(frame_info)
    
    ani.header['flags'] = 'Enable'
    ani.header['display_width'] = 128
    ani.header['display_height'] = 32
    ani.header['num_bitmaps'] = len(ani.frames)
    ani.header['total_frames'] = len(ani)
    
    with open(args.output_json.name, 'w') as fh:
        fh.write(ani.build_json_data())

