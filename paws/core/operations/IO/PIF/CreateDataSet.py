from ... import Operation as opmod 
from ...Operation import Operation

class CreateDataSet(Operation):
    """
    Take a Citrination client as input and use it to create a data set.
    Output the index of the created data set.
    """

    def __init__(self):
        input_names = ['client','name','description','share']
        output_names = ['ok_flag','dsid']
        super(CreateDataSet,self).__init__(input_names,output_names)
        self.input_doc['client'] = 'A reference to a running Citrination client.'
        self.input_doc['name'] = 'Name for the new data set.'
        self.input_doc['description'] = 'Description for the new data set.'
        self.input_doc['share'] = 'Flag for whether or not dataset should be public.'
        self.output_doc['ok_flag'] = 'Indicator of whether or not the data set was created successfully.'
        self.output_doc['dsid'] = 'The index of the new data set, if created successfully.'
        self.input_type['client'] = opmod.workflow_item
        self.inputs['description'] = 'New Citrination data set'
        self.inputs['share'] = False

    def run(self):
        c = self.inputs['client']
        f = True
        try:
            r = c.create_data_set()
            #if 'dataset' in r.keys():
            #    s = 'client successfully queried data set {}.'.format(dsid)
            #    f = True
            #else:
            #    s = 'client queried data set {} but found no dataset in response dict: Response: {}'.format(dsid,r)
            #    f = True
        except Exception as ex:
            s = 'client failed to create data set. Error message: {}'.format(ex.message)
            f = False
        self.outputs['ok_flag'] = f
        self.outputs['dsid'] = -1 

