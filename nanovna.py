# -*- coding: utf-8 -*-
"""
 A very crude driver to communicate with the NanoVNA. 
"""

import serial as _serial
import numpy as _np
import skrf as _rf
import matplotlib.pyplot as _plt
from serial.tools import list_ports as _list_ports

# %% subfunctions
def _plot_complex(data_rf, fig=None, label=None):
	
	ls = None
	marker = None
	lw = None
	ms = None
	c = None
	
	if type(fig) is type(None):
		fig, axes = _plt.subplots(2, 2, sharex=True)
	else:
		axes = _np.array(fig.get_axes())
		
	axes = axes.flatten()
	data_rf.plot_s_mag(ax=axes[0], label=label, ls=ls, marker=marker, lw=lw, ms=ms, c=c)
	data_rf.plot_s_re(ax=axes[1], label=label, ls=ls, marker=marker, lw=lw, ms=ms, c=c)
	data_rf.plot_s_deg(ax=axes[2], label=label, ls=ls, marker=marker, lw=lw, ms=ms, c=c)
	data_rf.plot_s_im(ax=axes[3], label=label, ls=ls, marker=marker, lw=lw, ms=ms, c=c)
	
	return fig
		

# %% main class
class nanovna:
	"""
	A very crude driver to communicate with the NanoVNA. 
	
	References
	----------
	 * list of commands: https://github.com/Ho-Ro/nanovna-tools/blob/main/shellcommands.txt
     * more commands: https://groups.io/g/nanovna-users/topic/list_of_nanovna_console/32286625
	 * this code is strongly influenced by: https://github.com/Ho-Ro/nanovna-tools
	"""
	

	# %% special characters
	_cr = b'\r'
	_lf = b'\n'
	_crlf = _cr + _lf
	_prompt = b'ch> '


	# %% class functions 
	def __init__(self, port=''):
		
		if port == '':
			self.port = self.get_device_port()
		else:
			self.port = port
		
		self.connect()
		self.resume()
		
		
	def __enter__(self):
		return self
	
	
	def __exit__(self, a, b, c):
		self.close()
		
	
	# %% connect/disconnect
	
	def connect(self, verbose=True):
		self.NanoVNA = _serial.Serial(self.port, timeout=1)
		if verbose: print("Connected to device at address: ", self.port)
		
		
	def close(self):
		self.NanoVNA.close()

	# %% communication

	def write(self, cmd):
		if type(cmd) is str:
			cmd = cmd.encode()
		
		## This is a dumb way to clear the buffer.  It slows everything WAAAY down.  Find a better way to do this.
		loop = True
		while loop:
			data = self.NanoVNA.read_until() # clear buffer
			if len(data) == 0:
				loop = False
				
		## write command
		self.NanoVNA.write( cmd + self._cr )                     # send command and options terminated by CR
		echo = self.NanoVNA.read_until( cmd + self._crlf )       # wait for command echo terminated by CR LF
	   
		
	def query(self, cmd):
		self.write(cmd)
		result = self.NanoVNA.read_until( self._crlf + self._prompt )        # get command response until prompt
		return result
	
	
	# %% get data
	
	def get_frequencies(self):
		f = _np.array(self.query('frequencies').decode().strip((self._crlf + self._prompt).decode()).split(self._crlf.decode()), dtype=float)
		f = _rf.Frequency.from_f(f, unit='Hz')
		return f
	
	def measure_S11(self, num_avg = 1, plot=False):
		#self.pause()
		
		# get frequencies
		f = self.get_frequencies()
		
		# perform the measurement N-times
		data = _np.zeros(len(f), dtype=complex)	
		for i in range(num_avg):
			data += _np.array(self.query('data').decode().strip((self._lf + self._prompt).decode()).replace('\r', 'j').replace(' ', '+').replace('+-', '-').split('\n')).astype(complex)
		data = data.real / num_avg + 1j * data.imag / num_avg
		#self.resume()
			
		# convert data to skrf network object
		S11 = _rf.Network(s=data, frequency=f, z0=50)
		
		if plot is True:
			_plot_complex(S11)
		
		return S11
	
	
	# %% get dveice properties
    
	def info(self):
		""" returns device info """
		return self.query("info")
    
    
	def help(self): 
		""" returns list of device commands """
		return self.query("help")
    
	
	# %% misc device operation
    
	def pause(self):
		self.write('pause')
		
	
	def resume(self):
		self.write('resume')
		
		
	# %% device setup
	
	def perform_1port_cal(self):
		self.write('cal off')
		
		input('Connect open')
		self.write('cal open')
		
		input('Connect short')
		self.write('cal short')
		
		input('Connect load')
		self.write('cal load')
		
		self.write('cal done')
		self.write('cal on')	
		
		print('Calibration completed.  ')
		
		
# 	def set_bandwidth(self, bw=0):
# 		# 0 = 4000 Hz
# 		# 1 = 2000 Hz
# 		# 2 = 1333 Hz
# 		# 3 = 1000 Hz
# 		# 4 = 800 Hz
# 		# 5 = 666 Hz
# 		# ...
# 		# N = (4000 / (N+1)) Hz
# 		self.write('bandwidth %d' % bw)
# 		print("Bandwidth set to: ", self.get_bandwidth())
# 		
# 		
# 	def get_bandwidth(self):
# 		return self.query('bandwidth')
		
		
	def setup_sweep(self, f_start_Hz, f_stop_Hz, num_points=101):
		self.write('sweep %d %d %d' % (int(f_start_Hz), int(f_stop_Hz), int(num_points)))
		print("Sweep set to: ", self.get_sweep())
		
		
	def get_sweep(self):
		return self.query('sweep')
		
		
	def get_power(self):
		return self.query('power')
		# print("legend: 0 to 3.  255 = auto")
		
	
	def set_power(self, pw):
		self.write('power %d' % pw)
		print("Power set to: ", self.get_power())
		#("legend: 0 to 3.  255 = auto")
		
	
	def get_device_port(self) -> str: # Get nanovna device automatically
		VID = 0x0483 #1155
		PID = 0x5740 #22336
	
		device_list = _list_ports.comports()
		for device in device_list:
			if device.vid == VID and device.pid == PID:
				return device.device
		raise OSError("device not found")
		
		
		
		
if __name__ == "__main__":
 	
	with nanovna() as vna:
        
		print(vna.info())
		print(vna.help())

		if False:
			data1 = vna.measure_S11(1, plot=False)
			data3 = vna.measure_S11(3, plot=False)
			data10 = vna.measure_S11(10, plot=False)
			data33 = vna.measure_S11(33, plot=False)
    		
			fig = _plot_complex(data1, fig=None, label='1 avg')
			fig = _plot_complex(data3, fig=fig, label='3 avg')
			fig = _plot_complex(data10, fig=fig, label='10 avg')
			fig = _plot_complex(data33, fig=fig, label='33 avg')
