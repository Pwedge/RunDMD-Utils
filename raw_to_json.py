#!/usr/bin/env python3

import sys
import os
import argparse
import RunDmdImage
import json
from struct import unpack

def parse_arguments():
    def dir_path(string):
        if os.path.isdir(string) and os.access(string, os.R_OK):
            return string
        else:
            raise argparse.ArgumentTypeError('Unable to read from: {}'.format(string))

    parser = argparse.ArgumentParser(description='Convert a RAW file captured from the https://playfield.dev emulator to JSON used for RunDMD image creation')
    parser.add_argument('--input-raw', help='Input RAW filename', type=argparse.FileType('r'), required=True)
    parser.add_argument('--frame-start', help='Starting frame number', type=int, default=0)
    parser.add_argument('--frame-end', help='Ending frame number', type=int, default=1000000000)
    parser.add_argument('--x-start', help='Starting X coordinate', type=int)
    parser.add_argument('--x-end', help='Ending X coordinate', type=int)
    parser.add_argument('--y-start', help='Starting Y coordinate', type=int)
    parser.add_argument('--y-end', help='Ending Y coordinate', type=int)
    parser.add_argument('--output-json', help='Output JSON filename', type=argparse.FileType('w'), required=True)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    map_vals = {
        0 : 0,
        1 : 5,
        2 : 9,
        3 : 15
    }

    ani = RunDmdImage.RunDmdAnimation()
    ani.load_binary_animation_header(bytearray(ani.block_size))

    with open(args.input_raw.name, 'rb') as fh:
        header_vals = unpack('>3sHBBB', fh.read(8))
        if header_vals[0].decode('ascii') != 'RAW':
            print('Not a raw file!')
            sys.exit(1)
        version = header_vals[1]
        width = header_vals[2]
        height = header_vals[3]
        bitmaps_per_frame = header_vals[4]
        frame_size_bytes = width * height // 8
        
        frame_num = 0
        last_time = None
        while True:
            try:
                frame_time = unpack('<I', fh.read(4))[0]
                if last_time == None:
                    frame_dur = 30
                else:
                    frame_dur = frame_time - last_time
                last_time = frame_time
                frames = []
                for i in range(bitmaps_per_frame):
                    frames.append(fh.read(frame_size_bytes))
            except:
                break
            
            frame_num += 1
            if frame_num < args.frame_start or frame_num > args.frame_end:
                continue
            img_str = ''
            for i in range(width * height):
                this_pixel = 0
                for j in range(bitmaps_per_frame):
                    this_pixel += (frames[j][i // 8] >> ((i % 8))) & 0x1
                img_str += '{:x}'.format(map_vals[this_pixel])
            frame_rows = ani._frame_to_rows(img_str)
            print('--- Frame number {}:'.format(frame_num))
            for row in frame_rows:
                print('  {}'.format(row))
            frame_info = {'duration' : frame_dur, 'bitmap' : frame_rows}
            ani.frames.append(frame_info)
    
    print('Processed {} frames'.format(frame_num))
    
    ani.header['flags'] = 'Enable'
    ani.header['display_width'] = width
    ani.header['display_height'] = height
    ani.header['num_bitmaps'] = len(ani.frames)
    ani.header['total_frames'] = len(ani.frames)
    
    with open(args.output_json.name, 'w') as fh:
        fh.write(ani.build_json_data())

