from __future__ import print_function
import unittest
import os

import paws.api
import test_api
import test_op

runner = unittest.TextTestRunner(verbosity=3)

print(os.linesep+'--- testing paws.api ---'+os.linesep)
# Smoke test PAWS API
api_tests = unittest.TestSuite()
api_tests.addTest(test_api.TestAPI('test_start_stop'))
runner.run(api_tests)
print(os.linesep+'--- done testing paws.api ---'+os.linesep)

# Start an API to use in subsequent tests
paw = paws.api.start()

print(os.linesep+'--- testing paws.api.activate_op ---'+os.linesep)
# Test paw.activate_op for all Operations
activate_op_tests = unittest.TestSuite()
for op_uri in paw._op_manager.list_ops():
    activate_op_tests.addTest(test_op.TestOp('test_activate_op',op_uri,paw))
activate_op_result = runner.run(activate_op_tests)
print(os.linesep+'--- done testing paws.api.activate_op ---'+os.linesep)

# Make a list of the Operations that could be activated
ops_skipped = [t[0].op_uri for t in activate_op_result.skipped]
ops_active = [opname for opname in paw._op_manager.list_ops() if opname not in ops_skipped]

print(os.linesep+'--- testing active Operations ---'+os.linesep)
# Test instantiation for all active Operations
op_tests = unittest.TestSuite()
for op_uri in ops_active:
    op_tests.addTest(test_op.TestOp('test_op',op_uri,paw))
op_result = runner.run(op_tests)
op_run_tests = unittest.TestSuite()
for op_uri in ops_active:
    op_run_tests.addTest(test_op.TestOp('test_run',op_uri,paw))
op_run_result = runner.run(op_run_tests)
print(os.linesep+'--- done testing active Operations ---'+os.linesep)



