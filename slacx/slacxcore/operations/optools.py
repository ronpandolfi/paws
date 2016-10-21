from PySide import QtGui

##### DEFINITIONS OF SOURCES FOR OPERATION INPUTS
input_sources = ['(select source)','Text','Images','Operations','Filesystem'] 
text_input = 1
image_input = 2
op_input = 3
fs_input = 4
valid_sources = [text_input,image_input,op_input,fs_input]

##### VALID TYPES FOR TEXT BASED OPERATION INPUTS 
input_types = ['(select type)','string','int','float','array','bool']
string_type = 1
int_type = 2
float_type = 3
array_type = 4
bool_type = 5
valid_types = [string_type,int_type,float_type,array_type,bool_type]

##### IMAGE LOADER EXTENSIONS    
def loader_extensions():
    return str(
    "ALL (*.*);;"
    + "TIFF (*.tif *.tiff);;"
    + "RAW (*.raw);;"
    + "MAR (*.mar*)"
    )

##### CONVENIENCE METHOD FOR PRINTING DOCUMENTATION
def parameter_doc(name,value,doc):
    if type(value).__name__ == 'InputLocator':
        val_str = str(value.val)
    else:
        val_str = str(value)
    return "- name: {} \n- value: {} \n- doc: {}".format(name,val_str,doc) 

##### CONVENIENCE CLASS FOR STORING OR LOCATING OPERATION INPUTS
class InputLocator(object):
    """
    The presence of an object of this type as input to an Operation 
    indicates that this input has not yet been loaded or computed.
    Objects of this class contain the information needed to find the relevant input data.
    If raw textual input is provided, it is stored in self.val after typecasting.
    """
    def __init__(self,src,val):
        if src < 0 or src > len(input_sources):
            msg = 'found input source {}, should be between 0 and {}'.format(
            src, len(input_sources))
            raise ValueError(msg)
        self.src = src
        self.val = val 

##### MINIMAL CLASS FOR VERTICAL HEADERS
#class VertQLineEdit(QtGui.QLineEdit):
class VertQLineEdit(QtGui.QWidget):
    """QLineEdit, but vertical"""
    def __init__(self,text):
        super(VertQLineEdit,self).__init__()
        self.text = text
        #wid = self.geometry().width()
        #ht = self.geometry().height()
        #rt = self.geometry().right()
        #t = self.geometry().top()
        # QWidget.setGeometry(left,top,width,height)
        #self.setGeometry(t, rt, ht, wid)

    def paintEvent(self,event):
        qp = QtGui.QPainter()
        qp.begin(self)
        qp.rotate(90)
        qp.drawText(0,0,self.text)
        qp.end()

