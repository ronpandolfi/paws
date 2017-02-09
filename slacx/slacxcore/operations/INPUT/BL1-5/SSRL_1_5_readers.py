import time
import tifffile
from os import rename, mkdir, listdir
from os.path import splitext, split, join
from collections import OrderedDict

from ...slacxop import Operation
from ... import optools

class ImageAndHeaderSSRL15(Operation):
    """
    Read an image and header generated by beamline 1-5 at SSRL.
    Returns ndarray image and dictionary header.
    """

    def __init__(self):
        input_names = ['file']
        output_names = ['image', 'header','header_file_name']
        super(ImageAndHeaderSSRL15, self).__init__(input_names, output_names)
        self.input_doc['file'] = 'path to a tif file image produced by beamline 1-5 at SSRL'
        self.output_doc['image'] = 'the image as an ndarray'
        self.output_doc['header'] = 'the header file as a python dictionary'
        self.output_doc['header_file_name'] = 'path to the header file'
        self.input_src['file'] = optools.fs_input
        self.input_type['file'] = optools.path_type

    def run(self):
        #txtname = txtname_from_tifname(self.inputs['file'])
        hdr_file_name = splitext(self.inputs['file'])[0] + '.txt'
        self.outputs['image'] = tifffile.imread(self.inputs['file'])
        d = OrderedDict()
        for l in open(hdr_file_name,'r').readlines():
            try:
                if not l.strip() == '' and not l.strip()[0] == '#':
                    kvs = l.split(',')
                    # special case for the string headers on line 1
                    if not kvs[0].find('User') == -1:
                        u_str = kvs[0].split('User:')[1].strip()
                        t_str = kvs[1].split('time:')[1].strip()
                        d['User'] = u_str
                        d['time'] = t_str
                    # and filter out the redundant temperature line
                    elif not (len(kvs)==1 and kvs[0].strip()[-1]=='C'):
                        for kv in kvs:
                            kv_arr = kv.split('=')
                            d[kv_arr[0].strip()] = float(kv_arr[1].strip())
            except e:
                d['ERROR'] = e.message
        self.outputs['header'] = d
        self.outputs['header_file_name'] = hdr_file_name 

#ii = ii.split(sep)
#key = ii[0].strip()
#value = float(ii[1].strip())
#if int(value) == value:
#    value = int(value)
#dict[key] = value

#class ReadTxtSSRL15(Operation):
#    """
#    Read a txtfile header generated by beamline 1-5 at SSRL.
#    Returned as dictionary with predominantly float entries.
#    """
#
#    def __init__(self):
#        input_names = ['file']
#        output_names = ['header']
#        super(ReadTxtSSRL15, self).__init__(input_names, output_names)
#        self.input_doc['file'] = 'path to a text file header produced by beamline 1-5 at SSRL'
#        self.output_doc['header'] = 'the header file as a python dictionary'
#        self.input_src['file'] = optools.fs_input
#
#    def run(self):
#        self.outputs['header'] = read_header(self.inputs['file'])

#def read_header(txtfile):
#    """Read in a .txt header to a dict."""
#    header = {}
#    file = open(txtfile, 'r')
#    file.readline()  # pass first, commented line
#    line = file.readline()
#    firstline_to_dict_entries(line, header)
#    for i in range(3):
#        line = file.readline()  # scroll forward to temp line
#    header['temp_celsius'] = float(line[:-2])  # read temperature
#    line = file.readline()
#    while len(line) > 0:
#        if not (line[0] == '#'):
#            if len(line.strip()) > 0:
#                line_to_dict_entries(line, '=', header)
#        line = file.readline()
#    return header


#def read_header(txtfile):
#    """Read in a .txt header to a dict."""
#    header = {}
#    try:
#        self.outputs['header'] = read_header(txtname)
#    except IOError:
#        print "No corresponding header to file %s was found." % self.inputs['file']
#        self.outputs['header'] = {}
#    except IndexError:
#        print "There was an error reading %s.  It may be caused by a malformed header file."  % self.inputs['file']
#    except:
#        print "Some unexpected error occured."  ###

#def txtname_from_tifname(tifname):
#    txtname = splitext(tifname)[0] + '.txt'
#    return txtname

#def firstline_to_dict_entries(line, dict):
#    """Splits apart the first line of header only."""
#    entries = line.split(',')
#    for ii in entries:
#        ii = ii.strip()
#    dict['User'] = entries[0][6:]
#    dict['time'] = entries[1][6:]
#    dict['time_float'] = time_from_text(dict['time'])
#    #dict['time'] = time_from_text(entries[1][6:])
#
#def time_from_text(text):
#    """Converts time from text to float."""
#    # Sample value of *text*: Sat Nov 19 14:05:29 2016
#    format = "%a %b %d %H:%M:%S %Y"
#    timetuple = time.strptime(text, format)
#    timefloat = time.mktime(timetuple)
#    return timefloat
#
#def line_to_dict_entries(line, sep, dict):
#    """
#    Reads 'Counters' and 'Motors' lines.
#    Forces all to float type.  
#    Changing to optional int format worth considering.
#    """
#    entries = line.split(',')
#    for ii in entries:
#        ii = ii.split(sep)
#        key = ii[0].strip()
#        value = float(ii[1].strip())
#        #if int(value) == value:
#        #    value = int(value)
#        dict[key] = value

