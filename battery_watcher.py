#!/usr/bin/python3
# Popup a warning box when you battery is getting low and puts the computer to sleep
# Usage: ./low_battery_countdown target_power_level
# Requires tkinter for the standalone script: sudo apt install python3-tk

import time
import sys
import os

from sd_common import chunker, trailing_avg, warn, read_val, read_file, list_get
from sd_common import debug_pass as debug, Eprinter
from sd_chronology import local_time, fmt_time, msleep, pmsleep

eprint = Eprinter(verbose=1).eprint		# pylint: disable=C0103

class BatteryWatcher:
	"Keep track of the battery levels over time to predict when it will run out"

	def __init__(self):
		self.max_power = int(read_file(self.get_filename('charge_full')))
		self.capacity = open(self.get_filename('charge_now'))
		self.plug = open(self.get_filename('online'))
		self.levels = dict()                # Dict of power level percents to timestamps
		self.charge = self.check_batt()  	# Updated only with call to check_batt

	def get_filename(self, expr, path='/sys/class/power_supply/'):
		"Custom filename finder for init"
		for sub in os.listdir(path):
			for _paths, _dirs, names in os.walk(os.path.join(path, sub)):
				for name in names:
					if expr == name:
						name = os.path.join(path, sub, name)
						eprint("Using filename:", name)
						return name
		else:
			warn("Could not find file:", expr, 'in', path)
			raise ValueError

	def is_plugged(self):
		return bool(read_val(self.plug))

	def reset(self):
		"Reset the dictionary of levels if there's not a continuous time history of batt discharge"
		self.levels = dict()

	def check_batt(self):
		"Check the battery level and update self.levels return charge level"
		if read_val(self.plug):
			self.reset()
			debug("Plugged in")
			return 100
		else:
			charge = round(read_val(self.capacity) / self.max_power * 100, 1)
			self.levels[charge] = int(time.time())
			self.charge = charge
			eprint(self.levels)
			return charge

	def get_rate(self):
		'''Get discharge time per power percent.
		Skips last level because it hasn't been exhausted yet.'''
		if len(self.levels) >= 3:
			rates = []
			for t1, t2 in chunker(sorted(self.levels.keys(), reverse=True)[:-1], overlap=True):
				power_delta = t1 - t2
				time_delta = self.levels[t2] - self.levels[t1]
				rates.append(time_delta / power_delta)
			eprint(list(map(int, rates)), '=', int(trailing_avg(rates)))
			return trailing_avg(rates)
		return None

	def time_left(self, target, update=True):
		"Estimate seconds until power level will reach target"
		if update:
			charge = self.check_batt()
		else:
			charge = self.charge
		rate = self.get_rate()
		if rate:
			seconds = (charge - target) * rate
			debug('ETA:', local_time(seconds + time.time()), charge, target, rate, seconds)
			eprint()
			return seconds
		return float('inf')

	def wait_until(self, target):
		"Wait until target is reached, then return"
		charge = 100
		while True:
			charge = self.check_batt()
			if charge <= target:
				return True
			if charge == 100 or charge - target > 20:
				missing = msleep(600)
			elif len(self.levels) < 3:
				# Can't make estimation with no data
				missing = msleep(60)
			else:
				seconds = self.time_left(target, update=False)
				missing = msleep(seconds / 5 if seconds > 100 else 20)
			if missing:
				self.reset()


def wait4popup(batt, target):
	grace_time = 1          # Time after end_time before it actually goes to sleep
	warning_time = 90       # Time remaining before popup window
	loop_id = 0

	def delay():
		nonlocal end_time
		end_time += 60

	def loop():
		nonlocal end_time
		nonlocal loop_id

		time_left = end_time - time.time()
		loop_id += 1

		if time_left < -grace_time:
			# Sleepy Time
			explanation.config(text="Going to sleep...", fg='black')
			root.update()
			print("todo putting computer to sleep")
			root.destroy()
			return

		# With less than 60 seconds left, show time rainbowing
		if time_left < 60:
			text = str(int(time_left)) + (':%.2f' % (time_left % 1))[2:]
			countdown.config(fg="red")
			color = int(time_left * 10)
			r = (color * 10) % 256
			g = (color + 100) % 256
			b = (color + 200) % 256
			color = '#%02x%02x%02x' % (r, g, b)
			explanation.config(fg=color)
			interval = 20
		else:
			if loop_id % 600 == 0:
				# Reestimate every minute
				time_left = batt.time_left(target)
				if time_left < 60:
					time_left = 60
				end_time = time_left + time.time()
			text = fmt_time(time_left, pretty=False)
			interval = 100

		# Every 1 second check to see if battery plugged in
		if loop_id % (1000 // interval) == 0:
			charge = batt.check_batt()
			if charge >= 100:
				return

		countdown.config(text=text)
		root.update()
		root.after(interval, loop)

	# Nonlocal loop
	while True:

		# Wait until time is less than 5 minutes, then popup window
		while True:
			time_left = batt.time_left(target)
			debug(time_left, 'warning_time', warning_time)
			if time_left and time_left < warning_time:
				break
			if pmsleep(80):
				batt.reset()

		if time_left < warning_time:
			time_left = warning_time
		end_time = time_left + time.time()

		# Popup the warning box
		root = tk.Tk()

		explanation = tk.Label(root, font=("Arial", 12))
		explanation.config(text="Battery Low! Your computer will enter sleep mode in:")
		explanation.pack(pady=10)

		countdown = tk.Label(root, text="", font=("Helvetica", 40), justify='center')
		countdown.pack()

		delay_b = tk.Button(root, text="Delay 1 Minute", command=delay, width=10, font=("Arial", 12))
		delay_b.pack()

		root.update()
		x = explanation.winfo_width() + 20
		y = delay_b.winfo_height() + delay_b.winfo_y() + 20
		root.geometry(str(x) + 'x' + str(y))

		root.lift()
		root.after(10, loop)

		root.mainloop()
		debug('Global loop Finished')


def _main():
	"Wait until the battery gets to target level and then popup a warning"
	batt = BatteryWatcher()
	target = list_get(sys.argv, 1, 5)
	batt.wait_until(target+10)
	wait4popup(batt, target)


if __name__ == "__main__":
	import tkinter as tk
	_main()
