"""
Integrate an image, given calibration parameters.

This module builds a PyFAI.AzimuthalIntegrator 
to integrate an input image to I(q,chi).
"""

import numpy as np
import pyFAI

from ... import Operation as opmod 
from ...Operation import Operation

class Integrate2d(Operation):
    """
    Input image data (ndarray) and a dict of calibration parameters 
    Return q, chi, I(q,chi) 
    """
    def __init__(self):
        input_names = ['image_data','poni_dict']
        output_names = ['q','chi','I_at_q_chi','I_at_q','q_I']
        super(Integrate2d,self).__init__(input_names,output_names)
        self.input_doc['image_data'] = '2d array representing intensity for each pixel'
        self.input_doc['poni_dict'] = str( 'dict of calibration parameters; '
        + 'minimally including keys dist, poni1, poni2, rot1, rot2, rot3, pixel1, pixel2, wavelength;'
        + 'optionally including keys fpolz, detector, splineFile; '
        + 'same specifications as pyFAI .poni format calibration parameters')
        self.input_type['image_data'] = opmod.workflow_item
        self.input_type['poni_dict'] = opmod.workflow_item
        self.output_doc['q'] = 'scattering vector magnitude in 1/Angstrom'
        self.output_doc['chi'] = 'azimuthal angle in degrees'     
        self.output_doc['I_at_q_chi'] = 'integrated intensity at q, chi'
        self.output_doc['I_at_q'] = 'chi-integrated intensity at q'
        self.output_doc['q_I'] = 'q and I_at_q zipped together into an n-by-2 numpy array'

    def run(self):
        img = self.inputs['image_data']
        pd = self.inputs['poni_dict']
        if img is None or pd is None:
            return
        p = pyFAI.AzimuthalIntegrator()
        p.setPyFAI(**pd)
        fpolz = pd['fpolz']
        # use a mask to screen negative pixels
        # mask should be 1 for masked pixels, 0 for unmasked pixels
        s = int(img.shape[0])
        msk = np.ones((s,s))*(img <= 0)
        I_q_chi, q, chi = p.integrate2d(img, 1000, mask=msk, polarization_factor=fpolz, unit='q_A^-1')
        I_at_q = np.sum(I_q_chi,axis=0)
        #q = q * 1E9
        # save results to self.outputs
        self.outputs['q'] = q
        self.outputs['chi'] = chi 
        self.outputs['I_at_q_chi'] = I_q_chi 
        self.outputs['I_at_q'] = I_at_q 
        self.outputs['q_I'] = np.array([q,I_at_q]).T

