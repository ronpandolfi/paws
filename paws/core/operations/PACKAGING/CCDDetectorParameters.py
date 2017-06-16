import numpy as np

from ..Operation import Operation
from .. import optools

class CCDDetectorParameters(Operation):
    """
    Create a dictionary describing the properties of a CCD detector.

    If the CCD is being used with binning, please enter the values of the binned configuration in use,
    not the unbinned values.

    This operation accepts values of None, but dependent operations may not.  Empty fields may
    cause undesirable results in dependent processes like zinger/cosmic removal.

    Zinger/cosmic removal needs inverse_gain, readnoise, and saturation_level.

    Sensitivity is assumed to be proportional to photon energy about the base sensitivity.

    Default values represent a Rayonix SX165 detector at 2x2 binning.
    """

    def __init__(self):
        input_names = ['inverse_gain','readnoise','saturation_level']
        output_names = ['detector_params_dict']
        super(CCDDetectorParameters, self).__init__(input_names, output_names)
        # Documentation
        self.input_doc['inverse_gain'] = 'Electrons per ADU.  Sometimes, confusingly, called gain.'
        self.input_doc['readnoise'] = 'Readnoise in electrons'
        self.input_doc['saturation_level'] = 'Maximum number of counts the detector can register in ADU'
        self.input_doc['base_sensitivity'] = 'Electrons per detected photon.  Sometimes, confusingly, called gain.'
        self.input_doc['base_energy'] = 'Energy at which the sensitivity is quoted, in keV.'
        self.input_doc['experiment_energy'] = 'Photon energy in this experiment, in keV.'
        self.output_doc['detector_params_dict'] = 'A dictionary of detector parameters'
        # Source
        self.input_src['inverse_gain'] = optools.text_input
        self.input_src['readnoise'] = optools.text_input
        self.input_src['saturation_level'] = optools.text_input
        self.input_src['base_sensitivity'] = optools.text_input
        self.input_src['base_energy'] = optools.text_input
        self.input_src['experiment_energy'] = optools.no_input
        # Type
        self.input_type['inverse_gain'] = optools.float_type
        self.input_type['readnoise'] = optools.float_type
        self.input_type['saturation_level'] = optools.int_type
        self.input_type['base_sensitivity'] = optools.float_type
        self.input_type['base_energy'] = optools.float_type
        # Defaults
        self.inputs['detector_params_dict'] = 5.5
        self.inputs['readnoise'] = 9.0
        self.inputs['saturation_level'] = 65535
        self.inputs['base_sensitivity'] = 8.0
        self.inputs['base_energy'] = 12.0

    def run(self):
        inputs = self.inputs
        detector_params_dict = {}
        for ii in inputs:
            detector_params_dict[ii] = inputs[ii]
        try:
            detector_params_dict['experiment_sensitivity'] = \
                float(inputs['base_sensitivity'])*inputs['experiment_energy']/inputs['base_energy']
        except TypeError:
            detector_params_dict['experiment_sensitivity'] = None
        self.outputs['detector_params_dict'] = detector_params_dict