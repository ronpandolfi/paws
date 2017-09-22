from fabio import edfimage
from fabio import tifimage

from ... import Operation as opmod 
from ...Operation import Operation
import os

class FabIOWrite(Operation):
    """
    Use FabIO to write out an image, given image data,
    directory path, filename, file tag, extension, 
    an image header (dict), and a flag for whether or not to overwrite. 

    Outputs the full file path where the image was written,
    which should be dir_path+filename+filetag+ext.
    """

    def __init__(self):
        input_names = ['image_data','header','dir_path','filename','filetag','ext','overwrite']
        output_names = ['file_path']
        super(FabIOWrite,self).__init__(input_names,output_names)
        self.input_doc['image_data'] = 'image/array data to be saved'
        self.input_doc['header'] = 'dict-like image metadata header'
        self.input_doc['dir_path'] = 'parent directory path'
        self.input_doc['filename'] = 'base filename to be saved as'
        self.input_doc['filetag'] = 'string tag to be appended to base filename'
        self.input_doc['ext'] = 'file extension (overwrites base filename extension)'
        self.input_doc['overwrite'] = 'allow overwrite of already existing files'
        self.output_doc['file_path'] = 'path to the file that will be written: dir_path+filename+filetag+ext'

        self.input_type['image_data'] = opmod.workflow_item
        self.input_type['header'] = opmod.workflow_item
        self.input_type['filename'] = opmod.workflow_item

        self.inputs['filetag'] = ''
        self.inputs['ext'] = '.tif'
        self.inputs['overwrite'] = False

    def run(self):
        """
        Call on fabIO to extract image data
        """
        img = self.inputs['image_data']
        p = self.inputs['dir_path']
        fnm = self.inputs['filename'] 
        if p is None or fnm is None or img is None:
            return
        ext = self.inputs['ext'].lower()
        tg = self.inputs['filetag']
        hdr = self.inputs['header']
        outfile = fnm + tg + ext
        filepath = os.path.join(self.inputs['dir_path'],outfile)
        self.outputs['file_path'] = filepath
        if os.path.isfile(filepath) and not self.inputs['overwrite']:
            raise IOError('File already exists.')

        cls = None

        if ext == '.edf': cls = edfimage.edfimage
        elif ext == '.tif': cls = tifimage.tifimage
        # TODO: add JPEG support

        if not cls: raise ValueError('Extension not supported.')

        cls(img,header=hdr).write(filepath)


