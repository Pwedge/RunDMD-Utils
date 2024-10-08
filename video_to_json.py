#!/usr/bin/env python3

import sys
import os
import argparse
import RunDmdImage
import json
import imageio as iio
from PIL import Image, ImageOps

def parse_arguments():
    def dir_path(string):
        if os.path.isdir(string) and os.access(string, os.R_OK):
            return string
        else:
            raise argparse.ArgumentTypeError('Unable to read from: {}'.format(string))

    parser = argparse.ArgumentParser(description='Generate a JSON output from a video file')
    parser.add_argument('--input', help='Input video filename', type=argparse.FileType('r'), required=True)
    parser.add_argument('--frame-start', help='Starting frame number', type=int)
    parser.add_argument('--frame-end', help='Ending frame number', type=int)
    parser.add_argument('--x-start', help='Starting X coordinate', type=int)
    parser.add_argument('--x-end', help='Ending X coordinate', type=int)
    parser.add_argument('--y-start', help='Starting Y coordinate', type=int)
    parser.add_argument('--y-end', help='Ending Y coordinate', type=int)
    parser.add_argument('--frame-skip', help='Number of frames to skip', type=int, default=0)
    parser.add_argument('--invert', help='Invert the colors', action='store_true', default=False)
    parser.add_argument('--output-json', help='Output JSON filename', type=argparse.FileType('w'), required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    reader = iio.get_reader(args.input.name)
    print('{}'.format(reader.get_meta_data()['size']))

    width, height = reader.get_meta_data()['size']
    frame_time_ms = int(1000 / reader.get_meta_data()['fps'])
    frame_time_ms *= (args.frame_skip + 1)
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

    #for i, im in enumerate(reader):
    for i in range(len(reader)):
        try:
            im = reader.get_next_data()
        except RuntimeError:
            pass
        if i % (args.frame_skip + 1) != 0:
            continue
        if args.frame_start and i < args.frame_start:
            continue
        if args.frame_end and i > args.frame_end:
            break

        original = Image.fromarray(im)
        #original.show()

        cropped = original.crop((left, top, right, bottom))
        #cropped.show()

        if args.invert == True:
            inverted = ImageOps.invert(cropped)
            cropped = inverted
            #inverted.show()

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
        frame_info = {'duration' : frame_time_ms, 'bitmap' : frame_rows}
        ani.frames.append(frame_info)
    
    ani.header['flags'] = 'Enable'
    ani.header['display_width'] = 128
    ani.header['display_height'] = 32
    ani.header['num_bitmaps'] = len(ani.frames)
    ani.header['total_frames'] = len(ani.frames)
    
    with open(args.output_json.name, 'w') as fh:
        fh.write(ani.build_json_data())

