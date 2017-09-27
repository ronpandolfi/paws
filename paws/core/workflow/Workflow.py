from __future__ import print_function
from collections import OrderedDict
import copy
from functools import partial
import traceback

from ..models.TreeModel import TreeModel
from ..operations import Operation as opmod
from ..operations.Operation import Operation
from ..operations import optools

class Workflow(TreeModel):
    """
    Tree structure for a Workflow built from paws Operations.
    """

    def __init__(self):
        flag_dict = OrderedDict()
        flag_dict['select'] = False
        flag_dict['enable'] = True
        super(Workflow,self).__init__(flag_dict)
        self.inputs = OrderedDict()
        self.outputs = OrderedDict()
        self.logmethod = print

    def __getitem__(self,key):
        optags = self.keys()
        if key in optags:
            return self.get_data_from_uri(key) 
        else:
            raise KeyError('[{}] {}.__getitem__ only recognizes keys {}'
            .format(__name__,type(self).__name__,optags))
    def __setitem__(self,key,data):
        optags = self.keys() 
        # TODO: ensure that data is an Operation?
        if key in optags:
            self.set_item(key,data)
        else:
            raise KeyError('[{}] {}.__setitem__ only recognizes keys {}'
            .format(__name__,type(self).__name__,optags))

    def keys(self):
        return self.list_op_tags() 

    @classmethod
    def clone(cls):
        return cls()

    def add_op(self,op_tag,op):
        op.message_callback = self.logmethod
        op.data_callback = partial( self.set_op_item,op_tag )
        self.set_item(op_tag,op)

    #def record_op_input(self,opname,inpname,inpdata):
    #    uri = opname+'.'+opmod.inputs_tag+'.'+inpname
    #    op = self.get_data_from_uri(opname)
    #    op.inputs[inpname] = inpdata
    #    self.set_item(uri,inpdata)

    #def record_op_output(self,opname,outname,outdata):
    #    uri = opname+'.'+opmod.outputs_tag+'.'+outname
    #    op = self.get_data_from_uri(opname)
    #    op.outputs[outname] = outdata 
    #    self.set_item(uri,outdata)

    def set_op_item(self,op_tag,item_uri,item_data):
        full_uri = op_tag+'.'+item_uri
        self.set_item(full_uri,item_data)

    def clone_wf(self):
        """
        Produce a Workflow that is a copy of this Workflow.
        """
        new_wf = self.clone() 
        #new_wf = copy.copy(self)
        new_wf.inputs = copy.deepcopy(self.inputs)
        new_wf.outputs = copy.deepcopy(self.outputs)
        # NOTE: is it ok if I don't copy this method?
        new_wf.logmethod = self.logmethod
        for op_tag in self.list_op_tags():
            op = self.get_data_from_uri(op_tag)
            new_wf.set_item(op_tag,op.clone_op())
        return new_wf

    def build_tree(self,x):
        """
        Reimplemented TreeModel.build_tree() 
        so that TreeItems are built from Operations.
        """
        if isinstance(x,Operation):
            d = OrderedDict()
            d[opmod.inputs_tag] = self.build_tree(x.inputs)
            d[opmod.outputs_tag] = self.build_tree(x.outputs)
            return d
        else:
            return super(Workflow,self).build_tree(x) 

    def op_dict(self):
        optags = self.list_op_tags() 
        return OrderedDict(zip(optags,[self.get_data_from_uri(nm) for nm in optags]))

    def list_op_tags(self):
        return self.root_tags()

    def n_ops(self):
        return self.n_children()

    def connect_wf_input(self,wf_input_name,op_input_uri):
        self.inputs[wf_input_name] = op_input_uri

    def connect_wf_output(self,wf_output_name,op_output_uri):
        self.outputs[wf_output_name] = op_output_uri

    def break_wf_input(self,wf_input_name):
        self.inputs.pop(wf_input_name)
    
    def break_wf_output(self,wf_output_name):
        self.outputs.pop(wf_output_name)

    def wf_outputs_dict(self):
        d = OrderedDict()
        for wfoutnm in self.outputs.keys():
            d[wfoutnm] = self.get_data_from_uri(self.outputs[wfoutnm])
        return d

    def get_wf_output(wf_output_name):
        return self.get_data_from_uri(self.outputs[wf_output_name])

    def set_wf_input(self,wf_input_name,val):
        self.set_op_input_at_uri(self.inputs[wf_input_name],val)

    def execute(self):
        stk,diag = self.execution_stack()
        self.logmethod(os.linesep+'running workflow:'+os.linesep+self.print_stack(stk))
        for lst in stk:
            self.logmethod('running: {}'.format(lst))
            for op_tag in lst: 
                op = self.get_data_from_uri(op_tag) 
                for inpnm,il in op.input_locator.items():
                    if il.tp == opmod.workflow_item:
                        #il.data = self.locate_input(il)
                        #op.inputs[inpnm] = il.data
                        op.inputs[inpnm] = self.locate_input(il)
                        self.set_op_item(op_tag+'.'+opmod.inputs_tag+'.'+inpnm,op.inputs[inpnm])
                op.run() 
                for outnm,outdata in op.outputs.items():
                    self.set_op_item(op_tag+'.'+opmod.outputs_tag+'.'+outnm,outdata)
        #        try:
        #        except Exception as ex:
        #            tb = traceback.format_exc()
        #            self.write_log(str('Operation {} threw an error. '
        #            + '\nTrace: {}').format(op_tag,tb)) 

    def locate_input(self,il):
        if isinstance(il.val,list):
            return [self.get_data_from_uri(v) for v in il.val]
        else:
            return self.get_data_from_uri(il.val)
             
    def set_op_input_at_uri(self,uri,val):
        """
        Set an op input at uri to provided value val.
        The uri must be a valid uri in the TreeModel,
        of the form opname.inputs.inpname.
        """
        path = uri.split('.')
        opname = path[0]
        inpname = path[2]
        op = self.get_data_from_uri(opname)
        op.input_locator[inpname].val = val

    def set_op_enabled(self,opname,flag=True):
        op_item = self.get_from_uri(opname)
        op_item.flags['enable'] = flag

    def is_op_enabled(self,opname):
        op_item = self.get_from_uri(opname)
        return op_item.flags['enable']

    def execution_stack(self):
        """
        Build a stack (list) of lists of Operation uris,
        such that each list indicates a set of Operations
        whose dependencies are satisfied by the Operations above them.
        """
        stk = []
        valid_wf_inputs = [] 
        diagnostics = {}
        continue_flag = True
        while not self.stack_size(stk) == self.n_ops() and continue_flag:
            ops_rdy = []
            ops_not_rdy = []
            for op_tag in self.list_op_tags():
                if not self.is_op_enabled(op_tag):
                    op_rdy = False
                    op_diag = {op_tag:'Operation is disabled'}
                elif not self.stack_contains(op_tag,stk):
                    op = self.get_data_from_uri(op_tag)
                    op_rdy,op_diag = self.is_op_ready(op_tag,self,valid_wf_inputs)
                    diagnostics.update(op_diag)
                    if op_rdy:
                        ops_rdy.append(op_tag)
                    else:
                        ops_not_rdy.append(op_tag)
            if any(ops_rdy):
                stk.append(ops_rdy)
                for op_tag in ops_rdy:
                    op = self.get_data_from_uri(op_tag)
                    valid_wf_inputs += self.get_valid_wf_inputs(op_tag,op)
            else:
                continue_flag = False
        return stk,diagnostics

    @staticmethod
    def stack_contains(itm,stk):
        for lst in stk:
            if itm in lst:
                return True
            for lst_itm in lst:
                if isinstance(lst_itm,list):
                    if stack_contains(itm,lst_itm):
                        return True
        return False

    @staticmethod
    def stack_size(stk):
        sz = 0
        for lst in stk:
            for lst_itm in lst:
                if isinstance(lst_itm,list):
                    sz += stack_size(lst_itm)
                else:
                    sz += 1
        return sz

    @staticmethod
    def is_op_ready(op_tag,wf,valid_wf_inputs):
        op = wf.get_data_from_uri(op_tag)
        inputs_rdy = []
        diagnostics = {} 
        for name,il in op.input_locator.items():
            msg = ''
            if (il.tp == opmod.workflow_item 
            and not il.val in valid_wf_inputs): 
                inp_rdy = False
                msg = str('Operation input {} (={}) '.format(name,il.val)
                + 'not found in valid Workflow input list: {}'.format(valid_wf_inputs))
            else:
                inp_rdy = True
            inputs_rdy.append(inp_rdy)
            diagnostics[op_tag+'.'+opmod.inputs_tag+'.'+name] = msg
        if all(inputs_rdy):
            op_rdy = True
        else:
            op_rdy = False
        return op_rdy,diagnostics 

    @staticmethod
    def get_valid_wf_inputs(op_tag,op):
        """
        Return the TreeModel uris of the op and its inputs/outputs 
        that are eligible as downstream inputs in the workflow.
        """
        # valid_wf_inputs should be the operation, its input and output dicts, and their respective entries
        valid_wf_inputs = [op_tag,op_tag+'.'+opmod.inputs_tag,op_tag+'.'+opmod.outputs_tag]
        valid_wf_inputs += [op_tag+'.'+opmod.outputs_tag+'.'+k for k in op.outputs.keys()]
        valid_wf_inputs += [op_tag+'.'+opmod.inputs_tag+'.'+k for k in op.inputs.keys()]
        return valid_wf_inputs

    @staticmethod
    def print_stack(stk):
        stktxt = ''
        opt_newline = '\n'
        for i,lst in zip(range(len(stk)),stk):
            if i == len(stk)-1:
                opt_newline = ''
            if len(lst) > 1:
                if isinstance(lst[1],list):
                    substk = lst[1]
                    stktxt += ('[\'{}\':\n{}\n]'+opt_newline).format(lst[0],print_stack(lst[1]))
                else:
                    stktxt += ('{}'+opt_newline).format(lst)
            else:
                stktxt += ('{}'+opt_newline).format(lst)
        return stktxt


