from __future__ import print_function
import unittest
import sys

import paws.api
import paws.core.workflows as wfs 
from paws.core.workflows.Workflow import Workflow

class TestWf(unittest.TestCase):

    def __init__(self,test_name,wf_uri,paw):
        super(TestWf,self).__init__(test_name)
        self.wf_uri = wf_uri
        self.paw = paw

    def test_load_wf(self):
        print('testing {} ...'.format(self.wf_uri),end=''); sys.stdout.flush()
        wfname = self.wf_uri[self.wf_uri.rfind('.')+1:]
        self.paw.load_workflow(self.wf_uri,'test_'+wfname)
        wf = self.paw.get_wf('test_'+wfname)
        self.assertIsInstance(wf,Workflow)

