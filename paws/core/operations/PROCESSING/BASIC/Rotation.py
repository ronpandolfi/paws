import numpy as np

from ... import Operation as opmod 
from ...Operation import Operation

class Rotation(Operation):
    """Rotate an array by 90, 180, or 270 degrees."""

    def __init__(self):
        input_names = ['image_data','rotation_deg']
        output_names = ['image_data']
        super(Rotation,self).__init__(input_names,output_names)        
        self.input_doc['image_data'] = '2d array representing intensity for each pixel'
        self.input_doc['rotation_deg'] = 'rotation in degrees counter-clockwise: '\
            'must be one of 90, 180, or 270'
        self.output_doc['image_data'] = '2d array representing rotated image'
        self.inputs['rotation_deg'] = 90 

    def run(self):
        """Rotate self.inputs['image_data'] and save as self.outputs['image_data']"""
        img = self.inputs['image_data']
        if img is None:
            return
        rot_deg = int(self.inputs['rotation_deg'])
        if rot_deg==90:
            img_rot = np.rot90(img)
        elif rot_deg==180:
            img_rot = np.rot90(np.rot90(img))
        elif rot_deg==270:
            img_rot = np.rot90(np.rot90(np.rot90(img)))
        else:
            msg = '[{}] expected rot_deg = 90, 180, or 270, got {}'.format(__name__,rot_deg)
            raise ValueError(msg)
        # save results to self.outputs
        self.outputs['image_data'] = img_rot
