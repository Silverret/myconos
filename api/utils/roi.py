"""
Modified by Silvestre Perret, made Python3 compatible + zip + etc.
"""
"""
PymageJ Copyright (C) 2015 Jochem Smit

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License
 as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
 of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the
Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import numpy as np

import struct
import re
from collections import namedtuple
import os
import zipfile

# http://rsb.info.nih.gov/ij/developer/source/ij/io/RoiDecoder.java.html
# http://rsb.info.nih.gov/ij/developer/source/ij/io/RoiEncoder.java.html


#  Base class for all ROI classes
class ROIObject(object):

    def __init__(self, top, left, bottom, right, name, position):
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.name = name
        self.position = position

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.bottom - self.top

    @property
    def area(self):
        raise NotImplementedError('Area not implemented')


class ROIRect(ROIObject):
    type = 'rect'

    def __init__(self, top, left, bottom, right, arc, name, position):
        super().__init__(top, left, bottom, right, name, position)
        self.arc = arc

    @property
    def area(self):
        if self.arc == 0:
            return self.width * self.height
        else:
            raise NotImplementedError('Rounded rectangle area not implemented')


class ROIShape(ROIObject):
    type = 'shape'

    def __init__(self, x_coords, y_coords, name, position, top=None, left=None, bottom=None, right=None):
        self.x_coords = x_coords
        self.y_coords = y_coords
        top = top if not top is None else self.x_coords.min()
        left = left if not left is None else self.x_coords.min()
        bottom = bottom if not bottom is None else self.x_coords.max()
        right = right if not right is None else self.y_coords.max()
        super().__init__(top, left, bottom, right, name, position)

    def get_shapeArray(self):
        shapeArray = list()
        shapeArray.append(0.0)
        for x,y in zip(self.x_coords, self.y_coords):
            shapeArray.append(float(y))
            shapeArray.append(float(x))
            shapeArray.append(1.0)
        shapeArray.pop()
        shapeArray.append(4.0)
        return shapeArray

    @staticmethod
    def get_coords_from_shapeArray(shapeArray):
        x_coords = [value for index, value in enumerate(shapeArray) if index%3==2]
        y_coords = [value for index, value in enumerate(shapeArray) if index%3==1]
        return x_coords, y_coords




HeaderTuple = namedtuple('Header_variables', 'type size offset')


class ROIFileObject(object):

    _header1_fields = [
        # 'VAR_NAME', 'type', offset'
        ['MAGIC', '4s', 0],
        ['VERSION_OFFSET', 'h', 4],
        ['TYPE', 'b', 6],
        ['TOP', 'h', 8],
        ['LEFT', 'h', 10],
        ['BOTTOM', 'h', 12],
        ['RIGHT', 'h', 14],
        ['N_COORDINATES', 'h', 16],
        ['X1', 'f', 18],
        ['Y1', 'f', 22],
        ['X2', 'f', 26],
        ['Y2', 'f', 30],
        ['XD', 'f', 18],  # D vars for sub pixel resolution ROIs
        ['YD', 'f', 22],
        ['WIDTHD', 'f', 26],
        ['HEIGHTD', 'f', 30],
        ['STROKE_WIDTH', 'h', 34],
        ['SHAPE_ROI_SIZE', 'i', 36],
        ['STROKE_COLOR', 'i', 40],
        ['FILL_COLOR', 'i', 44],
        ['SUBTYPE', 'h', 48],
        ['OPTIONS', 'h', 50],
        ['ARROW_STYLE', 'b', 52],
        ['FLOAT_PARAM', 'b', 52],
        ['POINT_TYPE', 'b', 52],
        ['ARROW_HEAD_SIZE', 'b', 53],
        ['ROUNDED_RECT_ARC_SIZE', 'h', 54],
        ['POSITION', 'i', 56],
        ['HEADER2_OFFSET', 'i', 60],
        ['COORDINATES', 'i', 64]
    ]

    _header2_fields = [
        ['C_POSITION', 'i', 4],
        ['Z_POSITION', 'i', 8],
        ['T_POSITION', 'i', 12],
        ['NAME_OFFSET', 'i', 16],
        ['NAME_LENGTH', 'i', 20],
        ['OVERLAY_LABEL_COLOR', 'i', 24],
        ['OVERLAY_FONT_SIZE', 'h', 28],
        ['AVAILABLE_BYTE1', 'b', 30],
        ['IMAGE_OPACITY', 'b', 31],
        ['IMAGE_SIZE', 'i', 32],
        ['FLOAT_STROKE_WIDTH', 'f', 36],
        ['ROI_PROPS_OFFSET', 'i', 40],
        ['ROI_PROPS_LENGTH', 'i', 44]
    ]

    _header1_size = 64
    _header2_size = 64

    _roi_types_rev = {'polygon': 0, 'rect': 1, 'oval': 2, 'line': 3, 'freeline': 4, 'polyline':5, 'no_roi': 6,
                      'freehand': 7, 'traced': 8, 'angle': 9, 'point': 10}

    _roi_types = {0: 'polygon', 1: 'rect', 2: 'oval', 3: 'line', 4: 'freeline', 5: 'polyline', 6: 'no_roi',
                  7: 'freehand', 8: 'traces', 9: 'angle', 10: 'point'}

    def __init__(self):
        self._header1_dict = {e[0]: HeaderTuple(e[1], self._type_size(e[1]), e[2]) for e in self._header1_fields}
        self._header2_dict = {e[0]: HeaderTuple(e[1], self._type_size(e[1]), e[2]) for e in self._header2_fields}
    
    @staticmethod
    def _type_size(_type):
        sizes = {'h': 2, 'f': 4, 'i': 4, 's': 1, 'b': 1}
        char = re.findall(r'\D', _type)[0]
        size = sizes[char]
        number = re.findall(r'\d', _type)

        if number:
            size *= int(number[0])
        return size


class ROIEncoder(ROIFileObject):

    def write(self, path, roi_obj):
        self.roi_obj = roi_obj
        self.header2_offset = self._header1_size

        self.f_obj = open(path, 'wb')
        pad = struct.pack('128b', *np.zeros(128, np.int8))
        self.f_obj.write(pad)

        self._write_header('MAGIC', b'Iout')
        self._write_header('VERSION_OFFSET', 225)  # todo or 226??

        roi_writer = getattr(self, '_write_roi_' + self.roi_obj.type)
        roi_writer()
        
        self.f_obj.close()

    def write_zip(self, arc_path, rois):
        import shutil
        dir_name = os.path.dirname(arc_path)
        arc_name = os.path.splitext(os.path.basename(arc_path))[0]
        temp_dir_name = "{}//RoiSet_{}".format(dir_name, arc_name[:-4])
        os.mkdir(temp_dir_name)
        zf = zipfile.ZipFile(arc_path, 'w', zipfile.ZIP_DEFLATED)
        for roi in rois:
            file_path = "{}//{}.roi".format(temp_dir_name, roi.name)
            self.write(file_path, roi)
            zf.write(file_path)
        shutil.rmtree(temp_dir_name)
        zf.close()

    def _write_roi_rect(self):
        self._write_header('TYPE', self._roi_types_rev[self.roi_obj.type])
        self._write_header('TOP', self.roi_obj.top)
        self._write_header('LEFT', self.roi_obj.left)
        self._write_header('BOTTOM', self.roi_obj.bottom)
        self._write_header('RIGHT', self.roi_obj.right)
        self._write_header('POSITION', self.roi_obj.position)
        self._write_header('HEADER2_OFFSET', self._header1_size)
        self._write_name()

    def _write_roi_shape(self):
        shapeArray = self.roi_obj.get_shapeArray()
        
        self._write_header('TYPE', self._roi_types_rev['rect'])
        self._write_header('TOP', self.roi_obj.top)
        self._write_header('LEFT', self.roi_obj.left)
        self._write_header('BOTTOM', self.roi_obj.bottom)
        self._write_header('RIGHT', self.roi_obj.right)
        self._write_header('POSITION', self.roi_obj.position)
        self._write_header('SHAPE_ROI_SIZE', len(shapeArray))

        base = self.header2_offset #TODO
        for f in shapeArray:
            self._write_var(base, 'f', f)
            base += 4

        self.header2_offset = self.header2_offset + 4 * len(shapeArray)
        self._write_header('HEADER2_OFFSET', self.header2_offset)
        self._write_name()

    def _write_roi_polygon(self):
        raise NotImplementedError('Writing roi type polygon is not implemented')

    def _write_roi_oval(self):
        raise NotImplementedError('Writing roi type oval is not implemented')

    def _write_roi_line(self):
        raise NotImplementedError('Writing roi type line is not implemented')

    def _write_roi_freeline(self):
        raise NotImplementedError('Writing roi type freeline is not implemented')

    def _write_roi_polyline(self):
        raise NotImplementedError('Writing roi type polyline is not implemented')

    def _write_roi_no_roi(self):
        raise NotImplementedError('Writing roi type no roi is not implemented')

    def _write_roi_freehand(self):
        raise NotImplementedError('Writing roi type freehand is not implemented')

    def _write_roi_traced(self):
        raise NotImplementedError('Writing roi type traced is not implemented')

    def _write_roi_angle(self):
        raise NotImplementedError('Writing roi type angle is not implemented')

    def _write_roi_point(self):
        raise NotImplementedError('Writing roi type point is not implemented')

    def _write_header(self, header_name, value):
        if header_name in self._header1_dict:
            header = self._header1_dict[header_name]
            offset = header.offset
        elif header_name in self._header2_dict:
            header = self._header2_dict[header_name]
            offset = header.offset + self.header2_offset
        else:
            raise Exception('Header variable %s not found' % header_name)
        
        self._write_var(offset, header.type, value)

    def _write_var(self, offset, var_type, value):
        self.f_obj.seek(offset)
        binary = struct.pack('>' + var_type, value)
        self.f_obj.write(binary)

    def _write_name(self):
        offset = self._header2_size + self.header2_offset
        name = self.roi_obj.name
        self._write_header('NAME_OFFSET', offset)
        self._write_header('NAME_LENGTH', len(name))
        self._write_var(offset, '{}s'.format(len(name)), bytes(name, 'utf-8'))


class ROIDecoder(ROIFileObject):

    def read(self, roi_path):
        if isinstance(roi_path, zipfile.ZipExtFile):
            self.data = roi_path.read()
            self.name = os.path.splitext(os.path.basename(roi_path.name))[0]
        elif isinstance(roi_path, str):
            with open(roi_path, 'rb') as fp:
                self.data = fp.read()
            self.name = os.path.splitext(os.path.basename(roi_path))[0]

        self.read_header()

        self.is_composite = self.header['SHAPE_ROI_SIZE']>0

        if self.is_composite:
            return self._read_roi_shape()

        try:
            roi_reader = getattr(self, '_read_roi_' + self._roi_types[self.header['TYPE']])
        except AttributeError:
            raise NotImplementedError('Reading roi type %s not implemented' % self._roi_types[self.header['TYPE']])

        return roi_reader()
    
    def read_zip(self, zip_path):
        rois = []
        zf = zipfile.ZipFile(zip_path)
        for n in zf.namelist():
            rois.append(self.read(zf.open(n)))
        zf.close()
        return rois
        
    def read_header(self):
        self.header = {}
        if self._get_header('MAGIC') != b'Iout':
            raise IOError('Invalid ROI file, magic number mismatch')

        to_read_h1 = ['VERSION_OFFSET', 'TYPE', 'SUBTYPE', 'TOP', 'LEFT', 'BOTTOM', 'RIGHT', 'N_COORDINATES',
                      'STROKE_WIDTH', 'SHAPE_ROI_SIZE', 'STROKE_COLOR', 'FILL_COLOR', 'SUBTYPE', 'OPTIONS', 'POSITION',
                      'HEADER2_OFFSET']
        to_read_h2 = [e for e in self._header2_dict]  # Read everything in header2

        set_zero = ['OVERLAY_LABEL_COLOR', 'OVERLAY_FONT_SIZE', 'IMAGE_OPACITY']

        for h in to_read_h1 + to_read_h2:
            self._set_header(h)

        for h in set_zero:
            self.header[h] = 0


    def _read_roi_rect(self):
        self._set_header('ROUNDED_RECT_ARC_SIZE')
        arc = self.header['ROUNDED_RECT_ARC_SIZE']

        params = ['TOP', 'LEFT', 'BOTTOM', 'RIGHT', 'POSITION']
        for p in params:
            self._set_header(p)

        top, left, bottom, right, position = [self.header[p] for p in params]
        name = self.name

        return ROIRect(top, left, bottom, right, arc, name, position)

    def _read_roi_shape(self):
        if self.header['TYPE'] != self._roi_types_rev['rect']:
            raise Exception("Invalid composite ROI type")
        top = self.header['TOP']
        left = self.header['LEFT']
        bottom = self.header['BOTTOM']
        right = self.header['RIGHT']
        position = self.header['POSITION']
        n = self.header['SHAPE_ROI_SIZE']

        base = 64 #TODO
        shapeArray = list()
        for _ in range(n):
            shapeArray.append(self._get_var(base, 4, 'f'))
            base += 4
        
        x_coords, y_coords = ROIShape.get_coords_from_shapeArray(shapeArray)
        return ROIShape(x_coords, y_coords, self.name,  position, top, left, bottom, right)

    def _read_roi_polygon(self):
        raise NotImplementedError('Reading roi type polygon is not implemented')

    def _read_roi_oval(self):
        raise NotImplementedError('Reading roi type oval is not implemented')

    def _read_roi_line(self):
        raise NotImplementedError('Reading roi type line is not implemented')

    def _read_roi_freeline(self):
        raise NotImplementedError('Reading roi type freeline is not implemented')

    def _read_roi_polyline(self):
        raise NotImplementedError('Reading roi type polyline is not implemented')

    def _read_roi_no_roi(self):
        raise NotImplementedError('Reading roi type no roi is not implemented')

    def _read_roi_freehand(self):
        raise NotImplementedError('Reading roi type freehand is not implemented')

    def _read_roi_traced(self):
        raise NotImplementedError('Reading roi type traced is not implemented')

    def _read_roi_angle(self):
        raise NotImplementedError('Reading roi type angle is not implemented')

    def _read_roi_point(self):
        raise NotImplementedError('Reading roi type point is not implemented')

    def _get_header(self, header_name):
        if header_name in self._header1_dict:
            header = self._header1_dict[header_name]
            offset = header.offset
        elif header_name in self._header2_dict:
            header = self._header2_dict[header_name]
            offset = header.offset + self.header['HEADER2_OFFSET']
        else:
            raise Exception('Header variable %s not found' % header_name)

        return self._get_var(offset, header.size, header.type)
    
    def _get_var(self, offset, var_size, var_type):
        binary = self.data[offset:offset+var_size]
        return struct.unpack('>' + var_type, binary)[0]  # read header variable, big endian

    def _set_header(self, header_name):
        self.header[header_name] = self._get_header(header_name)



""" 
def read_roi_zip(zip_path):
    rois = []
    zf = zipfile.ZipFile(zip_path)
    roid = ROIDecoder()
    for n in zf.namelist():
        rois.append(roid.read(zf.open(n)))
    zf.close()
    return rois 
"""

""" 
def write_roi_zip(arcname, rois):
    import shutil
    temp_dir_name = ".//RoiSet_{}".format(arcname[:-4])
    os.mkdir(temp_dir_name)
    roie = ROIEncoder()
    zf = zipfile.ZipFile(arcname, 'w', zipfile.ZIP_DEFLATED)
    for roi in rois:
        file_path = "{}//{}.roi".format(temp_dir_name, roi.name)
        roie.write(file_path, roi)
        zf.write(file_path)
    shutil.rmtree(temp_dir_name)
    zf.close() 
"""