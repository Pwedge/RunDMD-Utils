#!/usr/bin/env python3

'''
NOTES:
This is all based on looking at a binary image (B134) and trying to figure out the basic binary format. Once that was determined, then various fields were modified and the image was tested on actual hardware to see what changed

It appears that the last animation frame may be missed (bug in the RunDMD firmware?).  For example, see the "WORLD_CUP_SOCCER_028" animation in the B134 image.  The animation header is:
    00105000: 07c501280002944e33802002010101240b282800574f524c445f4355505f534f434345525f303238000000000000000000000000000000000000000000000000
This shows that there are 40 bitmaps, 51 frames, the clock should start on bitmap 40 and end on bitmap 40, and that the bitmap to frame info is at 0x0002944e * d'512 = 0x5289c00.  The frame header is:
    05289c00: 01730232033201690432053206320732083209320a320b320c320d320e320f3210321132123213321432153216321732183219321a321b321c321d321b321c32
    05289c40: 1d321b321c321d321b321c321d321e321f3220692132226923322432253226322769288727670000000000000000000000000000000000000000000000000000
The frame header clearly has 51 (bitmap, duration) tuples.  Tuple 50 references bitmap 40, so the clock should be displayed.  Tuple 51 references bitmap 39.  Based on this, the expectation is that the clock would quickly show for one frame and then disapear.  When looking at this animation on hardware, though, the clock gets displayed and then never disappears.

Most of the binary image appears to use 1-based numbers for things like bitmap counts and bitmap numbers. This library normalizes everything using 0-based numbering
'''

from struct import pack, unpack
from enum import Enum
import sys
import os
import logging
import json

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

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
                    elif params['type'] == 'function':
                        field_val = params['decode'](field_val)
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
                elif params['type'] == 'function':
                        field_val = params['encode'](field_val)
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
            logger.fatal('Binary did not have the correct marker')
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


rundmd_duration_buckets = [
        # FIXME: This was based on empircal measurements.  Watching in editor shows that something is still not understood here
        # duration granularity is encoded in the upper 2 bits of the 8 bit value
        # encoded duration is the lower 6 bits
        # (gran_ms, max_val)
        (2,     2*63),
        (10,    10*63),
        (100,   100*63),
        (1000,  1000*63) # ??? just guessed 
    ]
def RunDmdDurationEncode(duration_ms):
    for i, (gran, max) in enumerate(rundmd_duration_buckets):
        if duration_ms <= max:
            return (i << 6) | (duration_ms // gran)
    return 15   # Just assume 30ms

def RunDmdDurationDecode(duration_enc):
    bucket = rundmd_duration_buckets[(duration_enc >> 6) & 0x3]
    return (duration_enc & 0x3f) * bucket[0]

class RunDmdAnimation(object):
    block_size =                512
    bitmap_width =              128
    bitmap_height =             32
    bitmap_size =               bitmap_width * bitmap_height // 2 # One pixel per nibble
    flags =                     {'Enable' : 0} # bit position numbers
    clock_type =                {'NoClock' : 0, 'ClockBehind' : 1, 'ClockOnTop' : 2}
    transition =                {'Disable' : 0, 'Enable' : 1}
    clock_size =                {'ClockLarge' : 0, 'ClockSmall' : 1}
    animation_header_format = [ # list in header byte order and width is in bytes
        ('global_id',           {'width' : 2}),
        ('flags',               {'width' : 1, 'type' : 'flags', 'flag_bits' : flags}),
        ('num_bitmaps',         {'width' : 1}), # Number of raw bitmaps stored in the image
        ('frames_addr',         {'width' : 4, 'type' : 'granular', 'granular_unit' : block_size}),
        ('total_frames',        {'width' : 1}), # Number of frames that will be displayed during animation after indirection
        ('display_width',       {'width' : 1}),
        ('display_height',      {'width' : 1}),
        ('clock_type',          {'width' : 1, 'type' : 'enum', 'enum_vals' : clock_type}),
        ('intro_transition',    {'width' : 1, 'type' : 'enum', 'enum_vals' : transition}),
        ('outro_transition',    {'width' : 1, 'type' : 'enum', 'enum_vals' : transition}),
        ('clock_size',          {'width' : 1, 'type' : 'enum', 'enum_vals' : clock_size}),
        ('clock_position_x',    {'width' : 1}),
        ('clock_position_y',    {'width' : 1}),
        ('clock_start_frame',   {'width' : 1}), # In the binary header this is the 1-based bitmap number, not the frame number
        ('clock_end_frame',     {'width' : 1}), # In the binary header this is the 1-based bitmap number, not the frame number
        ('unknown_byte19',      {'width' : 1}),
        ('name',                {'width' : 32, 'type' : 'string'})
    ]
    frames_header_format = [
        ('bitmap_num',          {'width' : 1}),
        ('duration',            {'width' : 1, 'type' : 'function', 'encode' : RunDmdDurationEncode, 'decode' : RunDmdDurationDecode})
    ]


    def __init__(self):
        self.header = {}
        self.frames = []
        self.frame_to_bitmap = {}
        self.bitmap_to_frames = {}
    
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
                logger.error('Frame parsing failed')
                return False
            frame += row[1:-1]
        return frame  
    # Helper methods end
    

    # Animation header handling start
    def load_binary_animation_header(self, data):
        self.header = BinaryHandler().parse_binary(self.animation_header_format, data)

    def load_json_animation_header(self, json_data):
        dummy_header = bytearray(52)
        self.load_binary_animation_header(dummy_header)
        data = json.loads(json_data)
        self.header['flags'] = 'Enable'
        self.header['total_frames'] = len(self.frames)
        self.header['display_width'] = 128
        self.header['display_height'] = 32
        self.header.update(data)
        if self.header['clock_start_frame'] < 0:
            self.header['clock_start_frame'] = 0
        if self.header['clock_end_frame'] >= self.header['total_frames']:
            self.header['clock_end_frame'] = self.header['total_frames'] - 1
    
    def build_binary_animation_header(self):
        binary_data = BinaryHandler().create_binary(self.animation_header_format, self.header)
        padding = bytearray(self.block_size - len(binary_data))
        return binary_data + padding
    
    def build_json_animation_header(self):
        return json.dumps(self.header, indent=2)

    def animation_header_user_format(self):
        logger.debug('Sanitizing header for user consumption')
        logger.debug('Original header was: {}'.format(self.header))
        
        start_bitmap = self.header['clock_start_frame'] - 1
        if start_bitmap == -1:
            logger.info('Converting clock start to first frame number')
            self.header['clock_start_frame'] = 0
        elif start_bitmap not in self.bitmap_to_frames:
            logger.warning('Header requested start bitmap {} (0-based), but this was never referenced. Forcing no clock'.format(start_bitmap))
            self.header['clock_start_frame'] = 0
            self.header['clock_type'] = 'NoClock'
        else:
            logger.debug('Start bitmap is sane.  Converting from {} to {} (both 0-based)'.format(start_bitmap, self.bitmap_to_frames[start_bitmap][0]))
            self.header['clock_start_frame'] = self.bitmap_to_frames[start_bitmap][0]
        
        end_bitmap = self.header['clock_end_frame'] - 1
        if end_bitmap == -1:
            logger.info('Converting clock end to last frame number')
            self.header['clock_end_frame'] = len(self.frames) - 1
        elif end_bitmap not in self.bitmap_to_frames:
            logger.warning('Header requested end bitmap {} (0-based), but this was never referenced. Forcing display until end'.format(end_bitmap))
            self.header['clock_end_frame'] = len(self.frames) - 1
        else:
            logger.debug('End bitmap is sane.  Converting from {} to {}'.format(end_bitmap, self.bitmap_to_frames[end_bitmap][0]))
            self.header['clock_end_frame'] = self.bitmap_to_frames[end_bitmap][0]
        
        user_keys = ['clock_type', 'intro_transition', 'outro_transition', 'clock_size', 'clock_position_x', 'clock_position_y', 'clock_start_frame', 'clock_end_frame']
        for key in list(self.header):
            if key not in user_keys:
                self.header.pop(key)

    def animation_header_system_format(self):
        params = ['clock_start_frame', 'clock_end_frame']
        for param in params:
            self.header[param] = self.frame_to_bitmap[self.header[param]] + 1
    # Animation header handling end
    
    
    # Frame handling start
    def load_binary_frames(self, data):
        referenced_bitmaps = {}
        for frame_num in range(self.header['total_frames']):
            frame_to_bitmap_info = BinaryHandler().parse_binary(self.frames_header_format, data[frame_num*2:frame_num*2+2])
            bitmap_num = frame_to_bitmap_info['bitmap_num'] - 1
            referenced_bitmaps[frame_to_bitmap_info['bitmap_num']] = 1
            self.frame_to_bitmap[frame_num] = bitmap_num
            if bitmap_num not in self.bitmap_to_frames:
                self.bitmap_to_frames[bitmap_num] = [frame_num]
            else:
                self.bitmap_to_frames[bitmap_num].append(frame_num)
            if bitmap_num < 0:
                # Pure transparency frames seem to be indicated by a zero (one-based) frame number
                hex_str = 'a' * self.bitmap_size * 2
            else:
                bitmap_addr = bitmap_num * self.bitmap_size + self.block_size
                #logger.debug('Calling _frame_to_rows method for frame_num {}'.format(frame_num))
                #logger.debug('Using data:')
                hex_str = data[bitmap_addr:bitmap_addr+self.bitmap_size].hex()
            #for i in range(32):
                #logger.debug('  {}'.format(hex_str[i*128:i*128+128]))
            frame_rows_list = self._frame_to_rows(hex_str)
            self.frames.append({'duration' : frame_to_bitmap_info['duration'], 'bitmap' : frame_rows_list})
        #logger.debug('{}'.format(sorted(referenced_bitmaps)))
        for i in range(1, self.header['num_bitmaps'] + 1):
            if i not in referenced_bitmaps:
                logger.warn('Bitmap number {} is unreferenced in {}'.format(i, self.header['name']))
                return False
        return True
    
    def load_json_frames(self, json_data):
        data = json.loads(json_data)
        self.frames = data
        for i, frame in enumerate(self.frames):
            if 'duration' not in frame:
                logger.error('Frame {} does not contain a duration key'.format(i))
            if len(frame['bitmap']) != self.bitmap_height:
                logger.error('Frame {} is not the correct height'.format(i))
            for j, row in enumerate(frame['bitmap']):
                if row[0] != '|' and row[-1] != '|':
                    logger.error('Row {} of frame {} does not have expected starting and ending markers'.format(j, i))
                if len(row) != self.bitmap_width + 2:
                    logger.error('Row {} of frame {} is not the correct width'.format(j, i))
    
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
            self.frame_to_bitmap[i] = known_bitmaps[bitmap]
            if known_bitmaps[bitmap] not in self.bitmap_to_frames:
                self.bitmap_to_frames[known_bitmaps[bitmap]] = [i]
            else:
                self.bitmap_to_frames[known_bitmaps[bitmap]].append(i)
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
        self.load_json_frames(json.dumps(data['frames']))
        self.load_json_animation_header(json.dumps(data['header']))

    def build_binary_data(self, debug=False):
        if debug == False:
            self.animation_header_system_format()
        header = self.build_binary_header()
        frames = self.build_binary_frames()
        return (header, frames)
    
    def build_json_data(self, debug=False):
        if debug == False:
            self.animation_header_user_format()
        formatted_frames = []
        for i, frame in enumerate(self.frames):
            formatted_frames.append({'frame_num' : i, 'duration' : frame['duration'], 'bitmap' : frame['bitmap']})
        out = {'header' : self.header, 'frames' : formatted_frames}
        return json.dumps(out, indent=2)
    # Main loaders and builders end
    

    # Debug methods start
    def debug_dump(self):
        logger.debug('Here is the header:')
        for key in sorted(self.header):
            logger.debug('  {}: {}'.format(key, self.header[key]))
        logger.debug('')
        logger.debug('Here are the frames:')
        for frame in self.frames:
            for key in sorted(frame):
                if key == 'bitmap':
                    logger.debug('  {}:'.format(key))
                    for row in frame['bitmap']:
                        logger.debug('    {}'.format(row))
                else:
                    logger.debug('  {}: {}'.format(key, frame[key]))
    
    def sanity_check_animation_header(self, binary_data):
        # binary -> dic -> json -> dic -> binary
        self.load_binary_animation_header(binary_data)
        orig_dic = self.header.copy()
        
        json_str = self.build_json_animation_header()
        self.load_json_animation_header(json_str)
        new_dic = self.header.copy()
        if new_dic != orig_dic:
            logger.debug('After JSON load, the header data no longer matches')
            sys.exit(1)
        
        new_binary_data = self.build_binary_animation_header()
        if new_binary_data != binary_data:
            logger.debug('After binary dump, the header data no longer matches')
            logger.debug('{}'.format(binary_data.hex()))
            logger.debug('{}'.format(new_binary_data.hex()))
            sys.exit(1)
    
    def sanity_check_frames(self, binary_data):
        # binary -> dic -> json -> dic -> binary
        self.load_binary_frames(binary_data)
        orig_lst = self.frames.copy()
        
        json_str = self.build_json_frames()
        self.load_json_frames(json_str)
        new_lst = self.frames.copy()
        if new_lst != orig_lst:
            logger.debug('After JSON load, the frame data no longer matches')
            sys.exit(1)
        
        new_binary_data = self.build_binary_frames()
        if new_binary_data != binary_data:
            logger.debug('After binary dump, the frame data no longer matches')
            #logger.debug('{}'.format(binary_data.hex()[0:50]))
            #logger.debug('{}'.format(new_binary_data.hex()[0:50]))
            #sys.exit(1)
    # Debug methods end


class RunDmdImage(object):
    known_image_issues = {
        'B134' : [
            'ATTACK_FROM_MARS_033', # Bitmap 16 and 17 are identical, header only references bitmap 16
            'BIG_BANG_BAR_026', # Image problem?  0x00953000: 01320232033204320532066e0732083209320a320b320c32066e0e320f3210321132123213321432153216321732186919321a321b321c321d321e321f322032, 0x953018 should be 0x0d
            'BLACK_ROSE_020', # Bitmap 2 and 3 are identical, header only references bitmap 2
            'BRAM_STOKERS_DRACULA_023', # Bitmap 4 and 5 are identical, header only references bitmap 5
            'CACTUS_CANYON_008', # Bitmap 3 and 4 are identical, header only references bitmap 4
            'CACTUS_CANYON_020', # Bitmap 12 and 13 are identical, header only references bitmap 12
            'CACTUS_CANYON_039', # Bitmap 12 and 13 are identical, header only references bitmap 12
            'CIRQUS_VOLTAIRE_025', # Purposely removed?  Bitmap 1 has the clown facing partially sideways
            'CONGO_029', # Purposely removed?  Bitmap 1 looks out of place compared to {2, 3, 4, ...}
            'CORVETTE_009', # Image problem?  Bitmap 21 could have been included in the animation
            'CREATURE_FROM_THE_BLACK_L_014', # Image problem?  Bitmap 18 could have been included in the animation
            'CREATURE_FROM_THE_BLACK_L_016', # Image problem?  Bitmap 21 could have been included in the animation
            'FISH_TALES_016', # Purposely removed?  Bitmap 4 looks out of place compared to {1, 2, 3}
            'FISH_TALES_035', # Bitmap 16 and 17 are identical, header only references bitmap 16
            'GHOSTBUSTERS_049', # Image problem?  Bitmap 2 could have been included in the animation
            'HURRICANE_022', # Bitmap 10 and 11 are identical, header only references bitmap 10
            'INDIANA_JONES_023', # Appears to be old data.  This is the mine cart succseeding scene, but bitmap 48 is crashing
            'INDIANA_JONES_024', # Image problem?  Bitmap 15 could have been included in the animation
            'JUDGE_DREDD_010', # Bitmap 5 and 6 are identical, header only references bitmap 5
            'JUDGE_DREDD_021', # Purposely removed?  Bitmap 44 looks out of place compared to the final animation bitmaps
            'JUDGE_DREDD_033', # Image problem?  Bitmap 7 could have been included in the animation
            'JUDGE_DREDD_047', # Bitmap 5 and 6 are identical, header only references bitmap 5
            'METALLICA_009', # Bitmap 18 and 19 are identical, header only references bitmap 19
            'MONSTER_BASH_042', # Image problem?  Bitmap 61 could have been included in the animation
            'MUSTANG_022', # Purposely removed?  Bitmap 19 is mostly transparency
            'NO_GOOD_GOFERS_009', # Purposely removed?  Bitmap 5 looks out of place compared to {1, 2, 3, 4}
            'NO_GOOD_GOFERS_050', # Image problem?  Bitmap 7 could have been included in the animation
            'PIRATES_OF_THE_CARIBBEAN_034', # Image problem?  Bitmap 20 could have been included in the animation
            'STAR_TREK_020', # Purposely removed?  Bitmap 37 looks out of place compared to rest of animation
            'STAR_TREK_THE_NEXT_GEN_017', # Image problem?  Bitmap 5 could have been included in the animation
            'THE_CHAMPION_PUB_007', # Bitmap 12 and 13 are identical, header only references bitmap 12
            'THE_CHAMPION_PUB_010', # Image problem?  Bitmap 1 could have been included in the animation
            'THE_CHAMPION_PUB_025', # Image problem?  Bitmap 6 could have been included in the animation
            'THE_CHAMPION_PUB_046', # Image problem?  Bitmap 3 could have been included in the animation
            'THE_CHAMPION_PUB_064', # Bitmap 60 and 61 are identical, header only references bitmap 60
            'THE_SHADOW_037', # Image problem?  Bitmap 9 could have been included in the animation
            'THE_WALKING_DEAD_013', # Purposely removed?  Bitmap 75 looks out of place compared to the final animation bitmaps
            'WHO_DUNNIT_012', # Purposely removed?  Bitmap 7 is axe being pulled back
            'WHO_DUNNIT_018', # Image problem?  Bitmap 11 could have been included in the animation
            'WORLD_CUP_SOCCER_017', # Bitmap 5 and 6 are identical, header only references bitmap 5
            'WORLD_CUP_SOCCER_033', # Bitmap 52 and 53 are identical, header only references bitmap 52
            'X-MEN_054', # Image problem?  Bitmap 33 could have been included in the animation
        ]
    }
    
    ani_header_to_frame_data_padding = 51200
    
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
                
                #if ani.header['name'] == 'AC#DC_012':
                #    sys.exit(1)
                
                # Animation frames
                frames_offset = ani.header['frames_addr']
                frames_segment_size = ani.header['num_bitmaps'] * ani.bitmap_size + ani.block_size
                fh.seek(frames_offset)
                frame_data = fh.read(frames_segment_size)
                if ani.load_binary_frames(frame_data) != True and ani.header['name'] not in self.known_image_issues[self.header.header['version']]:
                #if ani.load_binary_frames(frame_data) !=True or ani.header['name'] == 'AC#DC_011':
                    logger.error('Load unsuccessful')
                    
                    logger.debug('Raw header data: ')
                    data_bytes = header_data
                    row_bytes = 64
                    img_addr = offset - header_segment_size
                    for j in range(0, len(data_bytes), row_bytes):
                        hex_data = data_bytes[j:j+row_bytes].hex()
                        logger.debug('  0x{:08x}: {}'.format(img_addr + j, hex_data))
                    
                    logger.debug('Raw frame indirection data: ')
                    data_bytes = frame_data[:ani.block_size]
                    row_bytes = 64
                    img_addr = frames_offset
                    for j in range(0, len(data_bytes), row_bytes):
                        hex_data = data_bytes[j:j+row_bytes].hex()
                        logger.debug('  0x{:08x}: {}'.format(img_addr + j, hex_data))
                    
                    logger.debug('Raw frames data: ')
                    data_bytes = frame_data[ani.block_size:]
                    row_bytes = 64
                    img_addr = frames_offset + ani.block_size
                    bitmap_num = 0
                    for j in range(0, len(data_bytes), row_bytes):
                        if ((j // row_bytes) % 32) == 0:
                            frame_hash = hash(data_bytes[bitmap_num * 0x800 : bitmap_num * 0x800 + 0x800]) & 0xffffffff
                            logger.debug('  Bitmap {} (0x{:08x})'.format(bitmap_num + 1, frame_hash))
                            bitmap_num += 1
                        hex_data = data_bytes[j:j+row_bytes].hex()
                        logger.debug('  0x{:08x}: {}'.format(img_addr + j, hex_data))
                        if ((j // row_bytes) % 32) + 1 == 32:
                            logger.debug('  ')
                    
                    sys.exit(1)
                
                # Add it
                full_name = ani.header['name']
                name = full_name[:full_name.rfind('_')]
                if name not in self.animations:
                    self.animations[name] = []
                self.animations[name].append(ani)
    
    def load_json_header_data(self, json_data):
        self.header.load_json_data(json_data)
    
    def load_json_animation_data(self, json_data, name=None):
        ani = RunDmdAnimation()
        ani.load_json_data(json_data)
        if name != None:
            ani.header['name'] = name        
        full_name = ani.header['name']
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
        cur_offset += self.ani_header_to_frame_data_padding
        
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
        self.header.header['version'] = 'X001'
    
    def write_full_binary(self, fname, min_size=0):
        with open(fname, 'wb') as fh:
            # Main header
            data = self.header.build_binary_data()
            logger.info('writing main header of size 0x{:x}'.format(len(data)))
            fh.write(self.header.build_binary_data())
            
            # Animation headers
            for title in sorted(self.animations):
                for ani in self.animations[title]:
                    fh.write(ani.build_binary_animation_header())
            
            # Padding
            fh.write(bytearray(self.ani_header_to_frame_data_padding))
            
            # Animation bitmaps
            for title in sorted(self.animations):
                for ani in self.animations[title]:
                    fh.write(ani.build_binary_frames())
            
            # Padding
            cur_size = fh.tell()
            if cur_size < min_size:
                fh.write(bytearray(min_size - cur_size))
    
    def get_header(self):
        return self.header.build_json_data()
    
    def get_animations(self):
        for key in sorted(self.animations):
            for ani in self.animations[key]:
                yield (key, ani.build_json_data())

