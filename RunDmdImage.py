#!/usr/bin/env python3

from struct import pack, unpack
from enum import Enum
import sys
import os
import yaml

class BinaryHandler(object):
    def __init__(self):
        return
    
    def binary_extract(self, binary_format, data):
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
                        print('extract: {}'.format(field_val))
                        field_val = int(field_val * params['granular_unit'])
                        print('extract: {}'.format(field_val))
            parsed[field] = field_val
            cur_offset += width
        return parsed
    
    def binary_create(self, binary_format, data):
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
                    print('build: {}'.format(field_val))
                    field_val = int(field_val / params['granular_unit'])
                    print('build: {}'.format(field_val))
            if byte_vals == None:
                byte_vals = field_val.to_bytes(width, 'big')
            binary_data += byte_vals
        return binary_data


class RunDmdHeader(object):
    image_header_size = 512
    image_marker = 'DGD'
    startup_pic_size = 0xc600 

    def __init__(self):
        self.header = {
            'total_animations' : 0,
            'unknown1' : 0,
            'enabled_animations' : 0,
            'unknown2' : 0,
            'version' : 'X000',
            'unknown3' : 0,
        }
        self.startup_pic = bytearray(RunDmdHeader.startup_pic_size)
        for i in range(RunDmdHeader.startup_pic_size):
            self.startup_pic[i] = i & 0xf

    def parse_binary_header(self, data):
        header = unpack('>3sH16sH472s4s13s', data[:RunDmdHeader.image_header_size])
        if header[0].decode('ascii') != RunDmdHeader.image_marker:
            raise
        self.header['total_animations'] = header[1]
        self.header['unknown1'] = header[2]
        self.header['enabled_animations'] = header[3]
        self.header['unknown2'] = header[4]
        self.header['version'] = header[5].decode('ascii')
        self.header['unknown3'] = header[6]

    def build_binary_header(self):
        return pack('>3sH16sH472s4s13s',
            self.header['total_animations'],
            self.header['unknown1'],
            self.header['enabled_animations'],
            self.header['unknown2'],
            self.header['version'].encode('ascii'),
            self.header['unknown3'])

    def load_from_binary(self, filepath, addr=0):
        if not os.path.isfile(filepath):
            raise ValueError
        with open(filepath, 'rb') as fh:
            fh.seek(addr)
            self.parse_binary_header(fh.read(RunDmdHeader.image_header_size))

    def load_from_yaml(self, filepath):
        if not os.path.isfile(filepath):
            raise ValueError
        with open(filepath, 'r') as fh:
            yaml_data = yaml.safe_load(fh)
        self.header.update(yaml_data['header'])

    def dump_to_binary(self):
        return self.build_binary_header()
    
    def dump_to_yaml(self):
        out = {'header' : self.header}
        return yaml.dump(out)
    
    @property
    def total_animations(self):
        return self.header['total_animations']
    @total_animations.setter
    def total_animations(self, value):
        self.header['total_animations'] = value
    

class RunDmdAnimation(object):
    block_size =                512
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
    frames_header = [
        ('bitmap_num',          {'width' : 1}),
        ('frame_duration',      {'width' : 1})
    ]

    def __init__(self):
        self.header = {}
        self.frames = []
        
    def parse_binary_animation_header(self, data):
        self.header = BinaryHandler().binary_extract(RunDmdAnimation.animation_header_format, data)
        # recreated_bytes = BinaryHandler().binary_build(RunDmdAnimation.animation_header_format, self.header)
        # if (recreated_bytes != data[:len(recreated_bytes)]):
        #     print('The extracted and recreated are not binary equivalents!')
        #     print('{}'.format(data[:len(recreated_bytes)].hex()))
        #     print('{}'.format(recreated_bytes.hex()))
        #     sys.exit(1)

    
    def parse_binary_frames(self):
        pass
    
    def build_binary_header(self):
        return BinaryHandler().binary_create(RunDmdAnimation.animation_header_format, self.header)

    def build_binary_frames(self):
        known_frames = {}
        frame_cnt = 0
        ani_binary = bytearray(RunDmdAnimation.block_size)

        for i, frame in enumerate(self.frames):
            if frame['bitmap'].hex() not in known_frames:
                old_size = len(ani_binary)
                # New bitmap
                known_frames[frame['bitmap'].hex()] = frame_cnt
                frame_cnt += 1
                frame_binary = bytearray(128 * 32 // 2)
                for j, (pixel_h, pixel_l) in enumerate(zip(frame['bitmap'][::2], frame['bitmap'][1::2])):
                    frame_binary[j] = ((pixel_h & 0xf) << 4) | (pixel_l & 0xf)
                ani_binary += frame_binary
            ani_binary[i*2] = known_frames[frame['bitmap'].hex()]
            ani_binary[i*2+1] = frame['duration']
        return ani_binary

    def load_from_binary(self, filepath, addr):
        if not os.path.isfile(filepath):
            raise ValueError
        with open(filepath, 'rb') as fh:
            fh.seek(addr)
            self.parse_binary_animation_header(fh.read(RunDmdAnimation.block_size))
            
            # New header at this address.  Indexed by frame_num and provides (bitmap_num, duration) tuples
            fh.seek(self.header['frames_addr'])
            frame_header = fh.read(2 * self.header['total_frames'])
            frame_ids = frame_header[0::2]
            frame_durs = frame_header[1::2]
            for i in range(self.header['total_frames']):
                frame_id = frame_ids[i]
                frame_dur = frame_durs[i]
                bitmap_size = int(128 * 32 / 2)
                addr = int(self.header['frames_addr'] + self.block_size + bitmap_size * (frame_id - 1))
                fh.seek(addr)
                frame_data = fh.read(bitmap_size)
                # Convert nibble -> byte
                frame = bytearray(128 * 32)
                frame[0::2] = [((i & 0xf0) >> 4) for i in frame_data]
                frame[1::2] = [(i & 0xf) for i in frame_data]
                self.frames.append({'duration' : frame_dur, 'bitmap' : frame}) # Duration in ms

    def load_from_yaml(self, filepath):
        if not os.path.isfile(filepath):
            raise ValueError
        with open(filepath, 'r') as fh:
            yaml_data = yaml.safe_load(fh)
        self.header.update(yaml_data['header'])
        self.frames = yaml_data['frames']
    
    def dump_to_binary(self):
        header = self.build_binary_header()
        frames = self.build_binary_frames()
        return (header, frames)

    def dump_to_yaml(self):
        formatted_frames = []
        for frame in self.frames:
            bitmap_lst = []
            for i in range(0, 128 * 32, 128):
                row = frame['bitmap'][i:i+128]
                row_str = '|'
                for val in row:
                    if val >= 0x0 and val <= 0x9:
                        row_str += chr(val + 0x30)
                    elif val >= 0xa and val <= 0xf:
                        row_str += chr(val + 0x61 - 0xa)
                    else:
                        row_str += '?'
                row_str += '|'
                bitmap_lst.append(row_str)
            formatted_frames.append({'duration' : frame['duration'], 'bitmap' : bitmap_lst})
        out = {'header' : self.header, 'frames' : formatted_frames}
        return yaml.dump(out)

    @property
    def global_id(self):
        return self.header['global_id']
    @global_id.setter
    def global_id(self, val):
        self.header['global_id'] = val
    
    @property
    def name(self):
            return self.header['name']
    @name.setter
    def name(self, val):
        self.header['name'] = val

class RunDmdImage(object):
    def __init__(self):
        self.header = RunDmdHeader()
        self.animations = {}
        return

    def load_full_binary(self, fname):
        self.header.load_from_binary(fname)
        cur_offset = RunDmdHeader.image_header_size + RunDmdHeader.startup_pic_size
        for i in range(self.header.total_animations):
            ani = RunDmdAnimation()
            ani.load_from_binary(fname, cur_offset)
            full_name = ani.name
            name = full_name[:full_name.rfind('_')]
            if name not in self.animations:
                self.animations[name] = []
            self.animations[name].append(ani)
            cur_offset += RunDmdAnimation.block_size

    def get_header(self):
        return self.header.dump_to_yaml()
    
    def get_animations(self):
        for key in sorted(self.animations):
            for ani in self.animations[key]:
                yield (key, ani.dump_to_yaml())





if __name__ == '__main__':
    import sys

    fname = sys.argv[1]

    rundmd_image = RunDmdImage()
    rundmd_image.load_from_binary(fname)

    addr = 0x105400
    #addr = 0xcc00
    rundmd_ani = RunDmdAnimation()
    rundmd_ani.load_from_binary(fname, addr)
    print('{}'.format(rundmd_ani.dump_to_yaml()))
    print('{}'.format(rundmd_ani.build_binary_header().hex()))
    print('{}'.format(rundmd_ani.build_binary_frames().hex()))

    with open('test.yaml', 'w') as fh:
        fh.write(rundmd_ani.dump_to_yaml())









