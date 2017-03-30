from functools import partial
from collections import OrderedDict

from PySide import QtCore

from ..plugins.WorkflowPlugin import WorkflowPlugin
from .workflow import Workflow
from ..operations.operation import Operation        
from ..operations import optools        
# TODO: consider migrating threading to a ThreadPool 

class WfManager(QtCore.QObject):
    """
    Manager for paws Workflows. 
    Stores a list of Workflow objects, performs operations on them.
    """

    def __init__(self,plugin_manager,qapp_reference):
        self.workflows = {} 
        self.appref = qapp_reference 
        self.plugman = plugin_manager
        self._n_threads = QtCore.QThread.idealThreadCount()
        # TODO: get more wf_threads working
        self._n_wf_threads = 1
        self._wf_threads = dict.fromkeys(range(self._n_threads)[:self._n_wf_threads]) 
        #self._wf_threads = dict.fromkeys(range(self._n_threads)) 
        self.logmethod = None
        super(WfManager,self).__init__()

    # this signal should emit the name (self.workflows dict key) of the workflow that finished.
    wfdone = QtCore.Signal(str)

    @QtCore.Slot(str)
    def run_wf(self,wfname):
        self.workflows[wfname].run_wf()

    @QtCore.Slot(str)
    def stop_wf(self,wfname):
        self.workflows[wfname].stop_wf()

    @QtCore.Slot(str)
    def finish_wf(self,wfname):
        self.wfdone.emit(wfname)

    @staticmethod
    def op_dict(op):
        dct = OrderedDict() 
        dct['type'] = type(op).__name__ 
        inp_dct = OrderedDict() 
        for name in op.inputs.keys():
            il = op.input_locator[name]
            inp_dct[name] = {'src':il.src,'tp':il.tp,'val':il.val}
        dct[optools.inputs_tag] = inp_dct 
        return dct

    def auto_name(self,wfname):
        """
        Generate the next unique workflow name by appending '_x',
        where x is a minimal nonnegative integer.
        """
        goodname = False
        prefix = wfname
        idx = 1
        while not goodname:
            if not wfname in self.workflows.keys():
                goodname = True
            else:
                wfname = prefix+'_{}'.format(idx)
                idx += 1
        return wfname 

    def finish_thread(self,th_idx):
        #print 'finishing thread {}'.format(th_idx)
        self.appref.processEvents()
        self._wf_threads[th_idx] = None

    def register_thread(self,th_idx,th):
        #print 'saving thread {}'.format(th_idx)
        self._wf_threads[th_idx] = th

    def wait_for_thread(self,th_idx):
        """Wait for the thread at self._wf_threads[th_idx] to be finished"""
        #print 'waiting for thread {}'.format(th_idx)
        # when waiting for a thread to execute something,
        # best processEvents() to ensure that the application has a chance
        # to prepare the thing that will be executed
        self.appref.processEvents()
        done = False
        interval = 1
        wait_iter = 0
        total_wait = 0
        while not done:
            #if wait_iter > 0:
            #    print '{}... still waiting for thread {} for {}ms'.format(wait_iter,th_idx,total_wait)
            done = True
            if self._wf_threads[th_idx] is not None:
                if not self._wf_threads[th_idx].isFinished():
                    done = False
                if not done:
                    if interval <= float(total_wait)*0.1 and interval <= 100:
                        interval = interval * 10
                    self.loopwait(interval)
                    wait_iter += 1
                    total_wait += interval

    def next_available_thread(self):
        for idx,th in self._wf_threads.items():
            if not th:
                #print '[{}] found available thread {}'.format(__name__,idx)
                return idx
        # if none found, wait for first thread in self.wfman.wf_threads 
        self.wait_for_thread(0)
        #print '[{}] falling back on thread 0'.format(__name__)
        return 0

    def wait_for_threads(self):
        """Wait for all workflow execution threads to finish"""
        for idx,th in self._wf_threads.items():
            self.wait_for_thread(idx)

    def loopwait(self,interval):
        """
        Create an event loop to delay some time without busywaiting.
        Time interval is specified in milliseconds.
        """
        l = QtCore.QEventLoop()
        t = QtCore.QTimer()
        t.setSingleShot(True)
        t.timeout.connect(l.quit)
        t.start(interval)
        l.exec_()
        # processEvents() to continue the main event loop while waiting.
        self.appref.processEvents()

    def n_wf(self):
        return len(self.workflows)

    def write_log(self,msg):
        if self.logmethod:
            self.logmethod(msg)
        else:
            print(msg)

    def wf_threads(self):
        return self._wf_threads

    def add_wf(self,wfname):
        """
        Add a workflow to self.workflows, with key specified by wfname.
        If wfname is not unique (i.e. a workflow with that name already exists),
        this method will overwrite the existing workflow with a new one.
        """
        wf = Workflow(self)
        wf.exec_finished.connect( partial(self.finish_wf,wfname) )
        self.workflows[wfname] = wf
        # for every new workflow, add a plugin 
        wf_pgin = WorkflowPlugin()
        wf_pgin.inputs['workflow'] = self.workflows[wfname] 
        wf_pgin.start()
        wf.wf_updated.connect( partial(self.plugman.update_plugin,wfname) )
        self.plugman.add_plugin(wfname,wf_pgin)

    def load_from_dict(self,wfname,opman,opdict):
        """
        Create a workflow with name (self.workflows dict key) wfname.
        If wfname is not unique, self.workflows[wfname] is overwritten.
        Input opdict specifies operation setup,
        where each item in opdict provides enough information
        to get and set inputs for an Operation from OpManager opman.
        """
        #while any(self.root_items):
        #    idx = self.index(self.rowCount(QtCore.QModelIndex())-1,0,QtCore.QModelIndex())
        #    self.remove_op(idx)
        self.add_wf(wfname)
        for uri, op_spec in opdict.items():
            opname = op_spec['type']
            op = opman.get_op_byname(opname)
            if op is not None:
                if not issubclass(op,Operation):
                    self.write_log('Did not find Operation {} - skipping.'.format(opname))
                else:
                    op = op()
                    op.load_defaults()
                    ilspec = op_spec[optools.inputs_tag]
                    for name in op.inputs.keys():
                        if name in ilspec.keys():
                            src = ilspec[name]['src']
                            if 'tp' in ilspec[name].keys():
                                tp = ilspec[name]['tp']
                            val = ilspec[name]['val']
                            if tp in optools.invalid_types[src]:
                                il = optools.InputLocator(src,optools.none_type,None)
                            else:
                                il = optools.InputLocator(src,tp,val)
                            op.input_locator[name] = il
                            # dereference any existing inputs
                            op.inputs[name] = None
                        else:
                            self.write_log('Did not find input {} for {} - skipping.'.format(name,opname))
                    self.workflows[wfname].add_op(uri,op)
            else:
                self.write_log('Did not find Operation {} - skipping.'.format(opname))
        # the wf_updated signal for this workflow is expected at this point
        # to be connected to the plugin manager
        self.workflows[wfname].wf_updated.emit()

