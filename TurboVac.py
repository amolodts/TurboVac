#!/usr/bin/python3 -u

import sys
import serial
import numpy as np
from dataclasses import dataclass
import turboctl
from turboctl.telegram import telegram, datatypes, parser, api
from turboctl.telegram.codes import (
    ControlBits, StatusBits, get_parameter_code, get_parameter_mode,
    ParameterResponse, ParameterError
)
from turboctl.telegram.datatypes import (Data, Uint, Sint, Bin)
from turboctl.telegram.parser import PARAMETERS
from turboctl.telegram.telegram import Telegram, TelegramBuilder, TelegramReader
from turboctl.telegram.codes import ControlBits

from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, LatestDeviceImpl
from tango.server import Device, attribute, command, pipe, device_property




class TurboVac(Device):
    
    # properties
    Port = device_property(
        dtype="str",
        default_value='/dev/ttyTurboVac',
    )
    Baudrate = device_property(
        dtype='str',
        default_value='19200',
    )
    
    #attribute
    frequency = attribute(label="Frequency", dtype=int,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ,
                         unit="Hz",
                         doc="Current frequency of the pump's rotor blades.")

    frequency_setpoint = attribute(label="Frequency setpoint", dtype=int, #check
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ_WRITE,
                         unit="Hz",
                         doc="Frequency setpoint the pump's rotor blades rotation have to achive.")
    
    temperatur = attribute(label="Temperatur", dtype=int,
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ,
                         unit='C',
                         doc="Current frequency converter temperature.")
    
    current = attribute(label="Current", dtype=float, 
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ,
                         unit="A",
                         doc="Current motor current.")
    
    voltage = attribute(label="Voltage", dtype=int, 
                         display_level=DispLevel.OPERATOR,
                         access=AttrWriteType.READ,
                         unit="V",
                         doc="Current intermediate circuit voltage.")
    
    
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.INIT)

        self.connection=serial.Serial(port=self.Port,baudrate=self.Baudrate, timeout=1)
        self.debug_stream('Initializing...')
        if self.connection.isOpen():
                self.set_state(DevState.ON)
                self.set_status('TurboVac pump is initialised on port %s.'%self.connection.port)
        else:
            self.set_status('Cannot connect on Port: {:s}'.format(self.Port))
            self.set_state(DevState.OFF)            
        
    def delete_device(self):
        self.set_status('close serial')
        self.connection.close()
    
    def read_frequency(self):
        return self.setpoint_status().frequency 

    def read_frequency_setpoint(self):
        return self.setpoint_status().parameter_value

    def write_frequency_setpoint(self, freq):
        self.write(24, freq)
        
    def read_temperatur(self):
        return self.setpoint_status().temperature
    
    def read_voltage(self):
        return self.setpoint_status().voltage
    
    def read_current(self):
        res = float(self.setpoint_status().current)
        self.debug_stream(str(res))
        return res



    @command
    def turnOn(self):
        api.status(self.connection, pump_on=True)
        self.set_state(DevState.RUNNING)
        self.set_status('Pump is running.')

    @command
    def turnOff(self):
        api.status(self.connection, pump_on=False)
        self.set_state(DevState.ON)
        self.set_status('Pump is stopping or already stopped.') 

    @command
    def getError(self):
        if self.dev_state()==DevState.RUNNING:
            pump_on=True
        else:
            pump_on=False
        error=self.get_error(pump_on)[0]
        time=self.get_error(pump_on)[1]
        if error is not None:         
            self.set_status("Last error was Nr. "+str(error)+". It occured at operating hour "+str(time)+".")
    
    @command
    def getStatus(self):
        status=bytes.fromhex('021600000000000000000000000000000000000000000014')
        res = api.send(self.connection,status)[1].flag_bits
        self.set_status(str(res))
            
   
    def setpoint_status(self):
        if self.dev_state()==DevState.RUNNING:
            pump_on=True
        else:
            pump_on=False  
        response=api.read_parameter(self.connection, number=24, index=0, pump_on=pump_on)[1]
        return response
    
    def write(self, parameter, freq):
        if self.dev_state()==DevState.RUNNING:
            pump_on=True
        else:
            pump_on=False  
        response = api.write_parameter(self.connection, number=parameter, value=freq, index=0, pump_on=pump_on)[1].parameter_value
        return response
            
    def get_error(self, pump_on):
        file='/home/labadm/.local/lib/python3.8/site-packages/turboctl/telegram/errors.txt'

        errors=np.loadtxt(file, usecols=0, delimiter=' ')
        error=api.read_parameter(self.connection, number=171, index=0, pump_on=pump_on)[1].parameter_value
        time=api.read_parameter(self.connection, number=176, index=0, pump_on=pump_on)[1].parameter_value
        
        return [error, time]
            
    
           

if __name__ == "__main__":
    TurboVac.run_server()
    
