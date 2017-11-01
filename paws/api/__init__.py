"""This module presents an API for paws."""
from __future__ import print_function
import warnings
import os
from collections import OrderedDict
import re
import importlib
import yaml

from ..core import pawstools
from ..core import operations as ops
from ..core import workflows as wfs
from ..core import plugins 
from ..core.operations import Operation as opmod
from ..core.operations.OpManager import OpManager 
from ..core.workflows.WfManager import WfManager 
from ..core.plugins.PluginManager import PluginManager 

def start():
    """Instantiate and return a PawsAPI object. 

    Returns
    -------
    a PawsAPI instance. 
    """
    return PawsAPI()

class PawsAPI(object):
    """Interface for using PAWS Operations, Workflows, and Plugins.

    This class facilitates interaction with a set of PAWS objects:
    an Operations Manager, a Workflow Manager, and a Plugins Manager. 
    """

    def __init__(self):
        super(PawsAPI,self).__init__()
        self._op_manager = OpManager()
        self._plugin_manager = PluginManager()
        self._wf_manager = WfManager()
        self._wf_manager.plugin_manager = self._plugin_manager
        self._current_wf_name = None 

        # TODO: load_cats and load_ops should happen outside the api.__init__
        # so that different api instances can have different operations loaded
        self._op_manager.load_cats(ops.cat_list) 
        self._op_manager.load_ops(ops.cat_op_list)

        # Assign a function(str) to PawsAPI.logmethod
        # to change where messages get printed
        #self.logmethod = print
        self.set_logmethod(print)

    def set_logmethod(self,lm):
        """Set the message logging method for this instance.

        Sets the logmethod, which is the function
        that is called to handle messages.

        Parameters
        ----------
        lm : function
            function to be called for logging messages
        """
        self.logmethod = lm
        self._op_manager.logmethod = lm
        self._plugin_manager.logmethod = lm
        self._wf_manager.logmethod = lm

    def activate_op(self,op_uri):
        """Activate an Operation for use in Workflows.

        Import the Operation indicated by op_uri, 
        and tag it as active.
        The Operation becomes available 
        to add to workflows via paws.api.add_op()
        
        Parameters
        ----------
        op_uri : str
            URI indicating which Operation to activate,
            e.g., 'CATEGORY.SUBCATEGORY.OperationName'
        """
        self._op_manager.set_op_enabled(op_uri)

    def disable_op(self,op_tag,wfname=None):
        """Disable an Operation to exclude it from its Workflow.

        This is for setting up Operations to be excluded
        from a Workflow without deleting the Operations.
        For example, you may want to turn off an Operation
        that generates a large output file,
        in cases where the output file is not needed.

        Parameters
        ----------
        op_tag : str
            name of Operation to be disabled
        wfname : str
            name of the Workflow containing the Operation,
            defaults to the current workflow

        See Also
        --------
        enable_op
        current_wf
        """
        self.get_wf(wfname).set_op_enabled(op_tag,False)

    def enable_op(self,op_tag,wfname=None):
        """Enable an Operation to include it in its Workflow.

        This is for re-enabling an Operation 
        that was previously disabled by calling disable_op().

        Parameters
        ----------
        op_tag : str
            name of Operation to be disabled
        wfname : str
            name of the Workflow containing the Operation-
            defaults to the current workflow

        See Also
        --------
        disable_op
        current_wf
        """
        self.get_wf(wfname).set_op_enabled(op_tag,True)

    def save_to_wfl(self,wfl_filename):
        """Save everything about the current state to a YAML (*.wfl) file.

        Saves the current workflows, plugins, and Operation environment
        to a .wfl (YAML) file, specified by wfl_filename.

        Parameters
        ----------
        wfl_filename : str
            Full path the file where the YAML file will be save.
            If the given filename does not have the .wfl extension,
            it will be appended automatically.
        """
        self.logmethod( 'saving current state to {}'.format(wfl_filename) )
        if not os.path.splitext(wfl_filename)[1] == '.wfl':
            wfl_filename = wfl_filename + '.wfl'
        d = self.wfl_dict()
        #pawstools.update_file(wfl_filename,d)
        pawstools.save_file(wfl_filename,d)

    def load_from_wfl(self,wfl_filename,wf_names=[],plugin_names=[]):
        """Load the state from a YAML (*.wfl) file.

        Loads workflows, plugins, and Operation environment
        from a .wfl (YAML) file, specified by wfl_filename.

        Parameters
        ----------
        wfl_filename : str
            Full path the file to be loaded.
        wf_names : list of str
            List of strings used to name the loaded Workflows.
            If not provided, Workflow tags from the .wfl file will be used.
        plugin_names : list of str
            List of strings used to name the loaded Plugins.
            If not provided, Plugin tags from the .wfl file will be used.
            
        """
        f = open(wfl_filename,'r')
        d = yaml.load(f)
        f.close()
        if 'PAWS_VERSION' in d.keys():
            wfl_version = d['PAWS_VERSION']
        else:
            wfl_version = '0.0.0'
        wfl_vparts = re.match(r'(\d+)\.(\d+)\.(\d+)',wfl_version)
        wfl_vparts = list(map(int,wfl_vparts.groups()))
        current_vparts = re.match(r'(\d+)\.(\d+)\.(\d+)',pawstools.version)  
        current_vparts = list(map(int,current_vparts.groups()))
        if wfl_vparts[0] < current_vparts[0] or wfl_vparts[1] < current_vparts[1]:
            # WARNING
            self.logmethod('WARNING: paws (version {}) '\
            'is trying to load a state built in version {} - '\
            'this is likely to cause things to crash, '\
            'until the workflows and plugins are reviewed/refactored '\
            'under the current version.'.format(pawstools.version,wfl_version))  
            self.logmethod(msg)
            warnings.warn(msg) 
        if 'OP_ACTIVATION_FLAGS' in d.keys():
            for opname,flag in d['OP_ACTIVATION_FLAGS'].items():
                if opname in ops.op_keys:
                    if flag:
                        self.activate_op(opname)
                    else:
                        self.deactivate_op(opname)
        if 'WORKFLOWS' in d.keys():
            wf_dict = d['WORKFLOWS']
            wf_keys = wf_dict.keys()
            if len(wf_dict) == len(wf_names):
                wf_keys = wf_names
            for wfname,wfspec in zip(wf_keys,wf_dict.values()):
                self._wf_manager.load_from_dict(wfname,wfspec,self._op_manager)
                self.select_wf(wfname)
        if 'PLUGINS' in d.keys():
            pgin_dict = d['PLUGINS']
            pgin_keys = pgin_dict.keys()
            if len(pgin_dict) == len(plugin_names):
                pgin_keys = plugin_names
            for pgin_name,pgin_spec in zip(pgin_keys,pgin_dict.values()):
                self._plugin_manager.load_from_dict(pgin_name,pgin_spec)

    def load_workflow(self,wf_uri,wfname=None):
        """Load a packaged Workflow from PAWS.

        This method retrieves a Workflow from the standard Workflows 
        that are included in the PAWS package.
        If a name is not specified, a default name will be taken
        from the YAML (.wfl) file where the workflow is saved.

        Parameters
        ----------
        wf_uri : str
            uri used to locate the desired Workflow.
        wfname : str
            name to be applied to the workflow once it is loaded. 
        """ 
        wfl_path = wfs.wf_paths[wf_uri]
        f = open(wfl_path,'r')
        d = yaml.load(f)
        f.close()
        if 'OP_ACTIVATION_FLAGS' in d.keys():
            for opname,flag in d['OP_ACTIVATION_FLAGS'].items():
                if opname in ops.op_keys:
                    if flag:
                        self.activate_op(opname)
                    else:
                        self.deactivate_op(opname)
        wf_dict = d['WORKFLOWS']
        # only one workflow is expected for these .wfl files.
        wfspec = wf_dict[wf_dict.keys()[0]]
        if not wfname:
            wfname = wf_dict.keys()[0]
        self._wf_manager.load_from_dict(wfname,wfspec,self._op_manager)
        self.select_wf(wfname)

    def get_wf(self,wfname=None):
        """Get a workflow from the workflow manager.

        Parameters
        ----------
        wfname : str
            Name of the desired Workflow.
            For valid workflow names, see list_wf_names().
            If wfname is not provided, 
            the current workflow is returned.

        See Also
        --------
        list_wf_names
        current_wf
        """
        if wfname is None:
            return self.current_wf()
        else:
            return self._wf_manager.workflows[wfname]

    def enable_plugin(self,pgin_name=''):
        """
        This tests the compatibility between the environment and the named plugin
        by attempting to import the plugin.
        If this does not throw an ImportError, 
        then the environment satisfies the plugin dependencies.
        """
        pkg = plugins.__name__
        mod = importlib.import_module('.'+pgin_name,pkg)

    def select_wf(self,wfname):
        """
        Sets the current workflow for the API instance.
        This is only to simplify subsequent api calls:
        anywhere there is an optional workflow name input,
        the default behavior is to apply the call to the current workflow.
        """
        if wfname in self._wf_manager.workflows.keys():
            self._current_wf_name = wfname
        else:
            msg = str('requested workflow {} not found in {}'
            .format(wfname,self._wf_manager.workflows.keys()))
            raise ValueError(msg)

    def n_wf(self):
        return self._wf_manager.n_wf()

    def current_wf_name(self):
        return self._current_wf_name

    def current_wf(self):
        if self._current_wf_name:
            return self._wf_manager.workflows[self._current_wf_name]    
        else:
            return None

    def get_op(self,opname,wfname=None):
        return self.get_wf(wfname).get_data_from_uri(opname) 

    def add_op(self,op_tag,op_spec,wfname=None):
        if self._op_manager.is_op_enabled(op_spec):
            wf = self.get_wf(wfname)
            # get the op referred to by op_spec
            op = self._op_manager.get_data_from_uri(op_spec)
            # instantiate with default inputs
            op = op()
            op.load_defaults()
            wf.add_op(op_tag,op)
        else:
            msg = str('Attempted to add Operation {}, '.format(op_spec)
            + 'but this Operation has not been activated. '
            + 'Activate it with paws.api.activate_op() '
            + 'before adding it to a workflow.')
            self.logmethod(msg) 
            raise pawstools.OperationDisabledError(msg)

    def add_wf(self,wfname):
        """
        Adds a workflow to the workflow manager.
        Input the workflow name.
        If no current workflow is selected,
        calls self.select_wf(wfname) at the end,
        selecting the new workflow for subsequent api calls.
        """
        self._wf_manager.add_wf(wfname)
        if not self._current_wf_name:
            self.select_wf(wfname)

    def add_plugin(self,pgin_tag,pgin_name):
        pgin = self._plugin_manager.load_plugin(pgin_name)
        self._plugin_manager.add_plugin(pgin_tag,pgin())

    def load_plugin(self,pgin_module):
        return self._plugin_manager.load_plugin(pgin_module)

    def set_plugin_input(self,pgin_tag,input_name,val=None):
        pgin = self._plugin_manager.get_data_from_uri(pgin_tag)
        pgin.inputs[input_name] = val

    def start_plugin(self,pgin_name):
        pgin = self.get_plugin(pgin_name)
        pgin.start()

    def get_plugin(self,pgin_name):
        return self._plugin_manager.get_plugin(pgin_name)

    def remove_op(self,op_tag,wfname=None):
        wf = self.get_wf(wfname)
        wf.remove_item(op_tag)

    def add_wf_input(self,wf_input_name,input_uris,wfname=None):
        """
        Add an input to the workflow specified by wfname,
        and specify its workflow routing by any number of input_uris,
        which should refer to the inputs of operations in the workflow.
        When the workflow is asked to set this input to some value x,
        it will set all of the provided input_uris to x.
        """
        self.get_wf(wfname).connect_wf_input(wf_input_name,input_uris) 

    def add_wf_output(self,wf_output_name,output_uris,wfname=None):
        """
        Add an output to the workflow specified by wfname,
        and specify one or more output_uris for pieces of workflow data
        that will be referenced to this workflow output.
        If multiple output_uris are specified, they will be packed as a list.
        """
        self.get_wf(wfname).connect_wf_output(wf_output_name,output_uris) 

    def remove_wf_input(self,wf_input_name,wfname=None):
        self.get_wf(wfname).break_wf_input(wf_input_name) 

    def remove_wf_output(self,wf_output_name,wfname=None):
        self.get_wf(wfname).break_wf_output(wf_output_name) 

    def set_wf_input(self,wf_input_name,val=None,wfname=None):
        if wfname is None:
            wfname = self._current_wf_name
        self.get_wf(wfname).set_wf_input(wf_input_name,val) 

    def set_input(self,opname,input_name,val=None,tp=None,wfname=None):
        if wfname is None:
            wfname = self._current_wf_name
        op = self.get_op(opname,wfname)
        if not input_name in op.inputs.keys():
            msg = str('Input name {} not valid for Operation {} ({}).'
            .format(input_name,opname,type(op).__name__))
            raise KeyError(msg)
        if tp is None:
            # if type is not specified, take the operation's default 
            tp = op.input_type[input_name]
        elif tp in opmod.input_types:
            # type specified by string: convert to enum
            tp = opmod.valid_types[ opmod.input_types.index(tp) ]
        if not tp in opmod.valid_types:
            # tp is neither a string or an enum
            msg = '[{}] failed to parse input type: {}'.format(
            __name__,tp)
            raise ValueError(msg)
        elif tp == opmod.runtime_type:
            # set inputlocator.val to None, 
            # so that this object will NOT attempt
            # to be serialized when save_to_wfl() is called.
            il = opmod.InputLocator(tp,None)
        else:
            # all other types, val can be serialized,
            # so it is referenced in the InputLocator. 
            il = opmod.InputLocator(tp,val)
        op.input_locator[input_name] = il
        if tp == opmod.basic_type:
            self.get_wf(wfname).set_op_item(opname,'inputs.'+input_name,val)

    def get_input_data(self,opname,input_name,wfname=None):
        if wfname is None:
            wfname = self._current_wf_name
        op = self.get_op(opname,wfname) 
        if not input_name in op.inputs.keys():
            msg = str('Input name {} not valid for Operation {} ({}).'
            .format(input_name,opname,type(op).__name__))
            raise KeyError(msg)
        return op.inputs[input_name]

    def get_input_setting(self,opname,input_name,wfname=None):
        if wfname is None:
            wfname = self._current_wf_name
        op = self.get_op(opname,wfname) 
        if not input_name in op.inputs.keys():
            msg = str('Input name {} not valid for Operation {} ({}).'
            .format(input_name,opname,type(op).__name__))
            raise KeyError(msg)
        return op.input_locator[input_name].val

    def get_output(self,opname,output_name=None,wfname=None):
        op = self.get_op(opname,wfname)
        if output_name is not None:
            return op.outputs[output_name]
        else:
            return op.outputs

    def execute(self,wfname=None):
        if wfname is None:
            wfname = self._current_wf_name
        self._wf_manager.run_wf(wfname)
        
    def wfl_dict(self):
        d = {} 
        d['OP_ACTIVATION_FLAGS'] = {k:True for k in ops.op_keys if self._op_manager.is_op_enabled(k)}
        d['PAWS_VERSION'] = pawstools.version 
        wfman_dict = OrderedDict()
        for wfname,wf in self._wf_manager.workflows.items():
            wfman_dict[wfname] = wf.wf_setup_dict() 
        d['WORKFLOWS'] = wfman_dict
        pgin_dict = OrderedDict() 
        for pgin_name in self._plugin_manager.list_plugin_tags():
            pgin = self._plugin_manager.get_data_from_uri(pgin_name)
            pgin_dict[pgin_name] = self._plugin_manager.plugin_setup_dict(pgin)
        d['PLUGINS'] = pgin_dict
        return d

    def op_count(self,wfname=None):
        return self.get_wf(wfname).n_children()

    def list_wf_names(self):
        return self._wf_manager.workflows.keys()
    
    def list_op_tags(self,wfname=None):
        return self.get_wf(wfname).list_op_tags()

    def list_plugin_tags(self):
        return self._plugin_manager.list_plugin_tags()

    def info(self):
        """Produce a string describing the PAWS package being used.""" 
        info_msg = str('PAWS: the Platform for Automated Workflows by SSRL. '
        + 'Version: {}'.format(pawstools.version))
        return info_msg
 
    #def deactivate_op(self,op_uri):
    #    """Deactivate an Operation so that it cannot be used.
    #
    #    Disable the Operation indicated by op_uri.
    #    The Operation cannot be added to Workflows until it is enabled again. 
    #    """
    #    self._op_manager.set_op_enabled(op_uri,False)


