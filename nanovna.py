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
def _plot_complex(data_rf):
	
	ls = None
	marker = None
	lw = None
	ms = None
	c = None
	label = None
	
	fig, axes = _plt.subplots(2, 2, sharex=True)
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
			self.port = self.find_device_port()
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
		
		loop = True
		while loop:
			data = self.NanoVNA.read_until() # clear buffer
			if len(data) == 0:
				loop = False
				
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
	
	def measure_S11(self, plot=False):
		self.pause()
		
		# get frequencies
		f = self.get_frequencies()
		
		# get data
		a = self.query('data').decode().strip((self._crlf + self._prompt).decode()).split(self._crlf.decode())
		
		self.resume()
		
		# convert data to complex numpy array
		data = _np.zeros(len(a), dtype=complex)	
		for i, ai in enumerate(a):
			# print(ai)
			re, im = ai.split(' ')
			data[i] = float(re) + 1j * float(im)
			
		# convert data to skrf network object
		S11 = _rf.Network(s=data, frequency=f, z0=50)
		
		if plot is True:
			_plot_complex(S11)
		
		return S11
	
	
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
		
		
	def set_bandwidth(self, bw=0):
		# 0 = 4000 Hz
		# 1 = 2000 Hz
		# 2 = 1333 Hz
		# 3 = 1000 Hz
		# 4 = 800 Hz
		# 5 = 666 Hz
		# ...
		# N = (4000 / (N+1)) Hz
		self.write('bandwidth %d' % bw)
		
		
	def setup_sweep(self, f_start_Hz, f_stop_Hz, num_points=101):
		self.write('sweep %d %d %d' % (int(f_start_Hz), int(f_stop_Hz), int(num_points)))
		
		
	def get_bandwidth(self):
		print(self.query('bandwidth'))
		
		
	def get_power(self):
		print(self.query('power'))
		print("legend: 0 to 3.  255 = auto")
		
	
	def set_power(self, pw):
		self.write('power %d' % pw)
		print("legend: 0 to 3.  255 = auto")
		
	
	def find_device_port(self) -> str: # Get nanovna device automatically
		VID = 0x0483 #1155
		PID = 0x5740 #22336
	
		device_list = _list_ports.comports()
		for device in device_list:
			if device.vid == VID and device.pid == PID:
				return device.device
		raise OSError("device not found")
		
		
		
		
if __name__ == "__main__":
 	
	with nanovna() as vna:
		data = vna.measure_S11(plot=True)
