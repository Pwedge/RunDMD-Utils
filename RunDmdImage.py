#!/usr/bin/env python3

from struct import pack, unpack
from enum import Enum
import sys
import os
import json

class BinaryHandler(object):
    def __init__(self):
        return
    
    def parse_binary(self, binary_format, data):
        parsed = {}
        cur_offset = 0
        for field, params in binary_format:
            width = params['width']
            if 'type' in params and params['type'] == 'string':
                field_val = unpack('>{}s'.format(width), data[cur_offset:cur_offset+width])[0].strip(b'\x00').decode('ascii')
            else:
                field_bytes = unpack('>{}'.format('B' * width), data[cur_offset:cur_offset+width])
                field_val = 0
                for field_byte in field_bytes:
                    field_val = (field_val << 8) | field_byte
                if 'type' in params:
                    if params['type'] == 'enum':
                        for enum_key in params['enum_vals']:
                            if params['enum_vals'][enum_key] == field_val:
                                field_val = enum_key
                                break
                    elif params['type'] == 'flags':
                        field_val_tmp = ''
                        for flag_bit_key in params['flag_bits']:
                            if field_val & (1 << params['flag_bits'][flag_bit_key]):
                                field_val_tmp = ' | {}'.format(flag_bit_key)
                        field_val = field_val_tmp[3:]
                    elif params['type'] == 'granular':
                        field_val = int(field_val * params['granular_unit'])
            parsed[field] = field_val
            cur_offset += width
        return parsed
    
    def create_binary(self, binary_format, data):
        binary_data = bytearray()
        for field, params in binary_format:
            width = params['width']
            field_val = data[field]
            byte_vals = None

            if 'type' in params:
                if params['type'] == 'string':
                    byte_vals = pack('>{}s'.format(width), data[field].encode('ascii'))
                elif params['type'] == 'enum':
                    for enum_key in params['enum_vals']:
                        if enum_key == field_val:
                            field_val = params['enum_vals'][enum_key]
                            break
                elif params['type'] == 'flags':
                    flags = [f.strip() for f in field_val.split('|')]
                    field_val = 0
                    for flag in flags:
                        if flag in params['flag_bits']:
                            field_val |= 1 << params['flag_bits'][flag]
                elif params['type'] == 'granular':
                    field_val = int(field_val / params['granular_unit'])
            if byte_vals == None:
                byte_vals = field_val.to_bytes(width, 'big')
            binary_data += byte_vals
        return binary_data


class RunDmdHeader(object):
    block_size =                512
    image_marker =              'DGD'
    startup_pic_size =          0xc600
    main_header_format = [ # list in header byte order and width is in bytes
        ('marker',              {'width' : 3, 'type' : 'string'}),
        ('total_animations',    {'width' : 2}),
        ('unknown_field1',      {'width' : 16}),
        ('enabled_animations',  {'width' : 2}),
        ('unknown_field2',      {'width' : 472}),
        ('version',             {'width' : 4, 'type' : 'string'}),
        ('unknown_field3',      {'width' : 13}),
        ('startup_picture',     {'width' : startup_pic_size})
    ]

    def __init__(self):
        self.header = {}
    
    # Main loaders and builders start
    def load_binary_data(self, data):
        self.header = BinaryHandler().parse_binary(self.main_header_format, data)
        if self.header['marker'] != self.image_marker:
            print('Binary did not have the correct marker')
            return False

    def load_json_data(self, json_data):
        data = json.loads(json_data)
        self.header.update(data)
    
    def build_binary_data(self):
        binary_data = BinaryHandler().create_binary(self.main_header_format, self.header)
        return binary_data
    
    def build_json_data(self):
        return json.dumps(self.header, indent=2)
    # Main loaders and builders end
    

class RunDmdAnimation(object):
    block_size =                512
    bitmap_width =              128
    bitmap_height =             32
    bitmap_size =               bitmap_width * bitmap_height // 2 # One pixel per nibble
    flags =                     {'Enable' : 0} # bit position numbers
    clock_type =                {'NoClock' : 0, 'ClockBehind' : 1, 'ClockOnTop' : 2}
    clock_size =                {'ClockSmall' : 0, 'ClockLarge' : 1}
    animation_header_format = [ # list in header byte order and width is in bytes
        ('global_id',           {'width' : 2}),
        ('flags',               {'width' : 1, 'type' : 'flags', 'flag_bits' : flags}),
        ('num_bitmaps',         {'width' : 1}), # Number of raw bitmaps stored in the image
        ('frames_addr',         {'width' : 4, 'type' : 'granular', 'granular_unit' : block_size}),
        ('total_frames',        {'width' : 1}), # Number of frames that will be displayed during animation after indirection
        ('display_width',       {'width' : 1}),
        ('display_height',      {'width' : 1}),
        ('clock_type',          {'width' : 1, 'type' : 'enum', 'enum_vals' : clock_type}),
        ('unknown_byte12',      {'width' : 1}),
        ('unknown_byte13',      {'width' : 1}),
        ('clock_size',          {'width' : 1, 'type' : 'enum', 'enum_vals' : clock_size}),
        ('clock_position_x',    {'width' : 1}),
        ('clock_position_y',    {'width' : 1}),
        ('clock_start_frame',   {'width' : 1}),
        ('clock_end_frame',     {'width' : 1}),
        ('unknown_byte19',      {'width' : 1}),
        ('name',                {'width' : 32, 'type' : 'string'})
    ]
    frames_header_format = [
        ('bitmap_num',          {'width' : 1}),
        ('duration',            {'width' : 1})
    ]

    def __init__(self):
        self.header = {}
        self.frames = []
    
    # Helper methods start
    def _frame_to_rows(self, frame_data):
        frame_rows = []
        for i in range(0, self.bitmap_width * self.bitmap_height, self.bitmap_width):
            frame_rows.append('|{}|'.format(frame_data[i:i+self.bitmap_width]))
        return frame_rows
    
    def _rows_to_frame(self, frame_rows):
        frame = ''
        for row in frame_rows:
            if row[0] != '|' or row[-1:] != '|':
                print('Frame parsing failed')
                return False
            frame += row[1:-1]
        return frame
    # Helper methods end
    

    # Animation header handling start
    def load_binary_animation_header(self, data):
        self.header = BinaryHandler().parse_binary(self.animation_header_format, data)

    def load_json_animation_header(self, json_data):
        data = json.loads(json_data)
        self.header.update(data)
    
    def build_binary_animation_header(self):
        binary_data = BinaryHandler().create_binary(self.animation_header_format, self.header)
        padding = bytearray(self.block_size - len(binary_data))
        return binary_data + padding
    
    def build_json_animation_header(self):
        return json.dumps(self.header, indent=2)
    # Animation header handling end
    
    
    # Frame handling start
    def load_binary_frames(self, data):
        for i in range(self.header['total_frames']):
            frame_to_bitmap_info = BinaryHandler().parse_binary(self.frames_header_format, data[i*2:i*2+2])
            bitmap_addr = (frame_to_bitmap_info['bitmap_num'] - 1) * self.bitmap_size + self.block_size
            frame_rows_list = self._frame_to_rows(data[bitmap_addr:bitmap_addr+self.bitmap_size].hex())
            self.frames.append({'duration' : frame_to_bitmap_info['duration'], 'bitmap' : frame_rows_list})
    
    def load_json_frames(self, json_data):
        data = json.loads(json_data)
        self.frames = data
    
    def build_binary_frames(self):
        known_bitmaps = {}
        animation_binary = bytearray(self.block_size)

        for i, frame_info in enumerate(self.frames):
            bitmap = self._rows_to_frame(frame_info['bitmap'])
            if bitmap not in known_bitmaps:
                # New bitmap
                known_bitmaps[bitmap] = len(known_bitmaps) + 1
                bitmap_binary = bytearray.fromhex(bitmap)
                animation_binary += bitmap_binary
            tmp_info = BinaryHandler().create_binary(self.frames_header_format, {'duration' : frame_info['duration'], 'bitmap_num' : known_bitmaps[bitmap]})
            animation_binary[i*2:i*2+2] = tmp_info
        return animation_binary
    
    def build_json_frames(self):
        return json.dumps(self.frames, indent=2)
    # Frame handling end
    

    # Main loaders and builders start
    def load_binary_data(self, header_data, frames_data):
        self.load_binary_animation_header(header_data)
        self.load_binary_frames(frames_data)
    
    def load_json_data(self, json_data):
        data = json.loads(json_data)
        self.load_json_animation_header(json.dumps(data['header']))
        self.load_json_frames(json.dumps(data['frames']))

    def build_binary_data(self):
        header = self.build_binary_header()
        frames = self.build_binary_frames()
        return (header, frames)
    
    def build_json_data(self):
        formatted_frames = []
        for frame in self.frames:
            formatted_frames.append({'duration' : frame['duration'], 'bitmap' : frame['bitmap']})
        out = {'header' : self.header, 'frames' : formatted_frames}
        return json.dumps(out, indent=2)
    # Main loaders and builders end
    

    # Debug methods start
    def debug_dump(self):
        print('Here is the header:')
        for key in sorted(self.header):
            print('  {}: {}'.format(key, self.header[key]))
        print('')
        print('Here are the frames:')
        for frame in self.frames:
            for key in sorted(frame):
                if key == 'bitmap':
                    print('  {}:'.format(key))
                    for row in frame['bitmap']:
                        print('    {}'.format(row))
                else:
                    print('  {}: {}'.format(key, frame[key]))
    
    def sanity_check_animation_header(self, binary_data):
        # binary -> dic -> json -> dic -> binary
        self.load_binary_animation_header(binary_data)
        orig_dic = self.header.copy()
        
        json_str = self.build_json_animation_header()
        self.load_json_animation_header(json_str)
        new_dic = self.header.copy()
        if new_dic != orig_dic:
            print('After JSON load, the header data no longer matches')
            sys.exit(1)
        
        new_binary_data = self.build_binary_animation_header()
        if new_binary_data != binary_data:
            print('After binary dump, the header data no longer matches')
            print('{}'.format(binary_data.hex()))
            print('{}'.format(new_binary_data.hex()))
            sys.exit(1)
    
    def sanity_check_frames(self, binary_data):
        # binary -> dic -> json -> dic -> binary
        self.load_binary_frames(binary_data)
        orig_lst = self.frames.copy()
        
        json_str = self.build_json_frames()
        self.load_json_frames(json_str)
        new_lst = self.frames.copy()
        if new_lst != orig_lst:
            print('After JSON load, the frame data no longer matches')
            sys.exit(1)
        
        new_binary_data = self.build_binary_frames()
        if new_binary_data != binary_data:
            print('After binary dump, the frame data no longer matches')
            #print('{}'.format(binary_data.hex()[0:50]))
            #print('{}'.format(new_binary_data.hex()[0:50]))
            #sys.exit(1)
    # Debug methods end


class RunDmdImage(object):
    def __init__(self):
        self.header = RunDmdHeader()
        self.animations = {}
        return

    def load_full_binary(self, fname):
        offset = 0
        with open(fname, 'rb') as fh:
            # Main header
            fh.seek(0)
            segment_size = RunDmdHeader.block_size + RunDmdHeader.startup_pic_size
            data = fh.read(segment_size)
            self.header.load_binary_data(data)
            offset += segment_size

            # Animations
            for i in range(self.header.header['total_animations']):
                ani = RunDmdAnimation()

                # Animation header
                header_segment_size = ani.block_size
                fh.seek(offset)
                header_data = fh.read(header_segment_size)
                ani.load_binary_animation_header(header_data)
                offset += header_segment_size

                # Animation frames
                frames_offset = ani.header['frames_addr']
                frames_segment_size = ani.header['num_bitmaps'] * ani.bitmap_size + ani.block_size
                fh.seek(frames_offset)
                frame_data = fh.read(frames_segment_size)
                ani.load_binary_frames(frame_data)

                # Add it
                full_name = ani.header['name']
                name = full_name[:full_name.rfind('_')]
                if name not in self.animations:
                    self.animations[name] = []
                self.animations[name].append(ani)
    
    def load_json_header_data(self, json_data):
        self.header.load_json_data(json_data)
    
    def load_json_animation_data(self, json_data):
        ani = RunDmdAnimation()
        ani.load_json_data(json_data)        
        full_name = ani.header['name']
        print('{}'.format(full_name))
        name = full_name[:full_name.rfind('_')]
        if name not in self.animations:
            self.animations[name] = []
        self.animations[name].append(ani)
    
    def finalize(self, enable_all=False):
        '''
        Update in main header
            animation count
            enable count
        Update in each animation header:
            frame address
            num bitmaps
            num frames
            global_id
            enable flag (optional)
        '''
        ani_count = 0
        for title in self.animations:
            ani_count += len(self.animations[title])
        
        cur_offset = self.header.block_size + self.header.startup_pic_size
        cur_offset += ani_count * RunDmdAnimation.block_size

        enable_count = 1 # For some reason, the enable count is +1
        global_id = 1
        for title in sorted(self.animations):
            for ani in self.animations[title]:
                frames_binary = ani.build_binary_frames()
                ani.header['global_id'] = global_id
                ani.header['total_frames'] = len(ani.frames)
                ani.header['frames_addr'] = cur_offset
                ani.header['num_bitmaps'] = (len(frames_binary) - ani.block_size) // ani.bitmap_size
                if enable_all == True:
                    ani.header['flags'] += ' | Enable'
                    enable_count += 1
                else:
                    if 'Enable' in ani.header['flags']:
                        enable_count += 1

                cur_offset += len(frames_binary)
                global_id += 1
        self.header.header['total_animations'] = ani_count
        self.header.header['enabled_animations'] = enable_count
        self.header.header['version'] = 'J001'

    def write_full_binary(self, fname):
        with open(fname, 'wb') as fh:
            # Main header
            data = self.header.build_binary_data()
            print('writing main header of size 0x{:x}'.format(len(data)))
            fh.write(self.header.build_binary_data())

            # Animation headers
            for title in sorted(self.animations):
                for ani in self.animations[title]:
                    fh.write(ani.build_binary_animation_header())
            
            # Animation bitmaps
            for title in sorted(self.animations):
                for ani in self.animations[title]:
                    fh.write(ani.build_binary_frames())

    def get_header(self):
        return self.header.build_json_data()
    
    def get_animations(self):
        for key in sorted(self.animations):
            for ani in self.animations[key]:
                yield (key, ani.build_json_data())
