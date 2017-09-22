import os.path

import tifffile
import numpy as np

from ... import Operation as opmod 
from ...Operation import Operation

class LoadTif(Operation):
    """
    Takes a filesystem path that points to a .tif,
    outputs image data from the file. 
    """

    def __init__(self):
        input_names = ['file_path']
        output_names = ['image_data','dir_path','filename']
        super(LoadTif,self).__init__(input_names,output_names)
        self.input_doc['file_path'] = 'path to a .tif image'
        self.output_doc['image_data'] = '2D array representing pixel values'
        self.output_doc['filename'] = 'Filename for image, path and extension stripped'
        
    def run(self):
        p = self.inputs['file_path']
        if p is None:
            return
        dir_path = os.path.split(p)[0]
        file_nopath = os.path.split(p)[1]
        file_noext = os.path.splitext(file_nopath)[0]
        self.outputs['dir_path'] = dir_path 
        self.outputs['filename'] = file_noext 
        try:
            self.outputs['image_data'] = tifffile.imread(p)
        except IOError as ex:
            ex.message = "[{}] IOError for file {}. \nError message:".format(__name__,p,ex.message)
            raise ex
        except ValueError as ex:
            ex.message = "[{}] ValueError for file {}. \nError message:".format(__name__,p,ex.message)
            raise ex

