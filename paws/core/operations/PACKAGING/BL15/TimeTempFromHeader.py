import datetime
import time

import tzlocal

from ... import Operation as opmod 
from ...Operation import Operation

class TimeTempFromHeader(Operation):
    """
    Get time and temperature from a detector output header file.
    Return string time, float time (utc in seconds), and float temperature.
    Time is assumed to be in the format Day Mon dd hh:mm:ss yyyy.
    """
    def __init__(self):
        input_names = ['header_dict','time_key','temp_key']
        output_names = ['date_time','time','temp']
        super(TimeTempFromHeader,self).__init__(input_names,output_names)        
        self.input_type['header_dict'] = opmod.workflow_item
        self.input_doc['header_dict'] = 'workflow uri of dict produced from detector output header file.'
        self.input_doc['time_key'] = 'key in header_dict that refers to the time' 
        self.input_doc['temp_key'] = 'key in header_dict that refers to the temperature' 
        self.output_doc['date_time'] = 'string representation of the time'
        self.output_doc['time'] = 'UTC time in seconds'
        self.output_doc['temp'] = 'Temperature'

    def run(self):
        d = self.inputs['header_dict']
        ktime = self.inputs['time_key']
        ktemp = self.inputs['temp_key']
        if d is None or ktime is None or ktemp is None:
            return
        time_str = str(d[ktime])
        temp = float(d[ktemp])
        # process the UTC time in seconds assuming %a %b %d %H:%M:%S %Y format
        # set local time zone for utc-awareness 
        tz = tzlocal.get_localzone()
        # use strptime to create a naive datetime object
        dt = datetime.datetime.strptime(time_str.strip(),"%a %b %d %H:%M:%S %Y")
        # add in timezone information to make a utc-aware datetime object
        dt_aware = datetime.datetime(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second,dt.microsecond,tz)
        # interpret the time in UTC milliseconds
        t_utc = time.mktime(dt_aware.timetuple())
        self.outputs['date_time'] = time_str
        self.outputs['time'] = float(t_utc)
        self.outputs['temp'] = temp

