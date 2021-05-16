#!/usr/bin/python3
# LazyCron - "Your computer will get around to it eventually."
# Usage: Run with -h for help.

################################################################################

import os
import time
import random
import argparse
import datetime
from datetime import datetime as dada

from battery_watcher import BatteryWatcher
from how_busy import all_disk_usage, get_network_usage

from sd_common import warn, indenter, check_install, mkdir, convert_ut_range, rint
from sd_common import local_time, convert_user_time, spawn, safe_filename, msleep
from sd_common import search_list, error, gohome, read_csv, read_state, itercount
from sd_common import argfixer, seconds_since_midnight, fmt_time, Eprinter
from sd_common import DotDict, joiner, quickrun, shell, tman, udate, add_date


def is_busy(max_net=100, max_disk=1):
	'''Return True if disk or network usage above defaults
	max_net = Network usage in KB/s
	max_disk = Disk usage in MB/s
	'''

	net_usage = get_network_usage(5, 4)     # KB/s
	disk_usage = all_disk_usage(5, 4)       # MB/s
	if net_usage < max_net and disk_usage < max_disk:
		return False
	else:
		print("Network Usage:", net_usage)
		print("Disk usage:   ", disk_usage)
	return True


def lid_open():
	return read_state("/proc/acpi/button/lid/LID0/state").split()[1] == "open"


def is_val(var):
	if type(var) in (float, int):
		return True
	return len(var) > 1 or var.isdigit()


def get_day(day, cycle):
	"Given a day of the week/month/year, return the next occurence"
	today = dada(*dada.now().timetuple()[:3])
	if cycle == 'week':
		delta = datetime.timedelta((day - today.weekday()))
	elif cycle == 'month':
		delta = datetime.timedelta((day - today.day))
		if delta.days < 0:
			delta = datetime.timedelta(add_date(today, months=1).replace(day=day) - today)
	elif cycle == 'year':
		month, day = day
		date = today.replace(month=month, day=day)
		if date < today:
			date = date.replace(year=date.year)
		return date
	else:
		error('cycle', cycle, "unsupported")
	return today + delta


################################################################################

class Scheduler:
	"Spawn processes during windows of time when certain conditions are met"

	def __init__(self, args):
		"Defaults:"
		self.window = []            # Start and stop times
		self.date_window = []       # Allowed days
		self.start = 0              # Start time in UTC
		self.stop = 0               # End time in UTC
		self.freq = 0               # Frequency
		self.history = []           # When the app last ran

		self.last_elapsed = 0       # Last elapsed time at run
		self.last_run = 0           # Last time the script was run
		self.next_elapsed = 0       # Next run time

		self.args = args            # Preserve initial setup args
		self.path = args['path']    # Path to script
		self.thread = None          # Thread starting running process
		self.log_dir = 'logs'
		mkdir(self.log_dir)
		self.name = list(indenter(os.path.basename(self.path), wrap=64))[0].rstrip(',')

		self.process_reqs()         # Process csv list of requirements
		self.calc_window()

	def process_reqs(self):

		args = self.args
		self.reqs = DotDict(plugged=False, idle=0, closed=False, random=0)
		for arg in args['reqs'].split(','):
			if set(arg) == {'*'}:
				continue
			arg = arg.lower().strip()
			# print(arg, self.reqs.keys())
			match = search_list(arg.split()[0], self.reqs.keys(), getfirst=True)
			if match:
				self.reqs[match] = True
			else:
				error("Can't find requirement:", arg)
			if match == 'idle':
				self.reqs.idle = convert_user_time(''.join(arg.split('idle')[1:]))
			if match == 'random':
				self.reqs.random = convert_user_time(''.join(arg.split('random')[1:]))

		if is_val(args['time']):
			for section in args['time'].split(','):
				vals = convert_ut_range(section)
				if len(vals) == 2:
					self.window.append([vals[0], vals[1]])
				else:
					error("Can't read time:", section)

		if is_val(args['date']):
			for section in args['date'].split(','):
				try:
					days, cycles = list(zip(*map(udate, section.split('-'))))
				except ValueError:
					error("Cannot understand text:", section)
				if len(set(cycles)) != 1:
					error("Cycle length in", section, "must be the same")
				cycles = cycles[0]
				start = days[0]
				if len(days) == 1:
					end = start
				else:
					end = days[1]

				self.date_window.append((start, end, cycles))


		if is_val(args['frequency']):
			self.freq = convert_user_time(args['frequency'])
			self.next_elapsed = self.freq

	def __str__(self):
		return str({key: val for key, val in self.__dict__.items() if key != 'args'})

	def __repr__(self):
		return self.name

	def print(self):
		"Print a detailed representation of each app"

		print('Name: ', self.name)
		if self.window:
			now = time.time()
			print('Start:', local_time(self.start, '%a %m-%d %I:%M %p'), '=', fmt_time(self.start - now))
			print('Stop: ', local_time(self.stop, '%a %m-%d %I:%M %p'), '=', fmt_time(self.stop - now))
		if self.freq:
			print('Freq: ', fmt_time(self.freq))
		print('Path: ', self.path)
		print('Reqs: ', self.reqs)
		print('in_window:', self.in_window())


	def running(self):
		"Check if process is already running."
		if self.thread and self.thread.is_alive():
			return True
		# Search system wide
		# return ps_running(self.path)


	def calc_date(self):
		"Get seconds until next date when allowed to run"
		inf = float("inf")
		new_start = inf
		new_stop = 0
		for sd, ed, cycle in self.date_window:
			if cycle == 'year':
				if dada.now() > ed:
					sd = sd.replace(year=sd.year+1)
					ed = ed.replace(year=ed.year+1)
				start = sd.timestamp()
				stop = ed.timestamp()
			else:
				#start = get_day(sd, cycle).timestamp()
				stop = get_day(ed, cycle).timestamp()
				start = stop - (ed - sd) * 86400
			if start < new_start:
				new_start = start
				new_stop = stop
		return new_start, new_stop


	def calc_window(self):
		"Calculate the next start and stop window for the proc in unix time"
		inf = float("inf")
		now = time.time()
		midnight = round(now - seconds_since_midnight())
		if self.date_window:
			self.start, self.stop = self.calc_date()
		else:
			self.start = midnight
			self.stop = midnight

		def get_first():
			"Find earliest start, return True if updated."
			new_start = inf
			for start, stop in self.window:
				if stop < start: 				# ex: 11pm-1am
					stop += 86400
				start += self.start
				stop += self.stop
				if start < new_start and stop > now:
					new_start = start
					new_stop = stop
			if new_start < inf:
				self.start = new_start
				self.stop = new_stop
				return True
			return False

		if self.window:
			if not get_first():
				self.start += 86400
				self.stop += 86400
				get_first()
		else:
			self.stop += 86400

		if self.history and (self.window or self.date_window):
			if self.start > now:
				print("Next run of", self.name, 'in', fmt_time(self.start - now))
			else:
				print("Time window for", self.name, 'closes in', fmt_time(self.stop - now))
		#print('Start:', local_time(self.start, '%a %m-%d %I:%M %p'), 'in', fmt_time(self.start - now))
		#print('Stop :', local_time(self.stop, '%a %m-%d %I:%M %p'), 'in', fmt_time(self.stop - now))


	def in_window(self):
		"Check if within time window to run, otherwise recalculate a new time window"
		now = time.time()
		if now < self.start:
			return False
		if self.start <= now <= self.stop:
			if not self.freq and self.start <= self.last_run <= self.stop:
				# print("Already ran in this window")
				return False
			return True
		else:
			# Recalculate
			self.calc_window()
			return False

	def run(self, elapsed, polling_rate, testing_mode, idle=0):
		"Run the process in seperate thread while appending info to log."

		if self.reqs:
			if self.reqs.closed and lid_open():
				print("\tLid not closed", v=-1)
				return False
			if self.reqs.plugged and not BATTERY.is_plugged():
				print("\tNot plugged in", v=-1)
				return False
			if self.reqs.idle > idle:
				print("\tIdle time not reached", v=-1)
				return False
			if self.reqs.random and random.random() > polling_rate / self.reqs.random:
				return False
		if self.running():
			print("\tStill running!")
			return False

		self.last_elapsed = elapsed
		self.last_run = int(time.time())
		self.next_elapsed = elapsed + self.freq

		filename = safe_filename(self.name + '.' + str(int(time.time())) + '.log')
		log_file = os.path.abspath(os.path.join(self.log_dir, filename))
		if self.path.lstrip().startswith('#'):
			testing_mode = True
		if testing_mode:
			text = "Did not start process:"
		else:
			self.history.append(int(time.time()))
			text = "Started process:"
			dirname = os.path.dirname(self.path)
			if not os.path.exists(dirname):
				dirname = None
			_que, self.thread = spawn(quickrun, self.path, ofile=log_file, shell=True, cwd=dirname)
		print('\n' + local_time(), text, self.name, v=1)
		print(joiner(', ', *self.history))
		return True


def read_schedule(schedule_apps, schedule_file):
	"Read the schedule file:"
	new_sched = []
	headers = "time frequency date reqs path".split()
	for line in read_csv(schedule_file, headers=headers, delimiter=("\t", " " * 4), merge=True):
		print('\n\nData =', repr(line))
		if not all(line.values()):
			warn("Empty columns must have a * in them")
			continue
		if len(line) >= 3:
			for proc in schedule_apps:
				if line == proc.args:
					new_sched.append(proc)
					break
			else:
				proc = Scheduler(line)
				proc.print()
				new_sched.append(proc)
		else:
			print("Could not process:", line)
	return new_sched


################################################################################
# Main Loop

def parse_args():
	'''Parse arguments'''
	parser = argparse.ArgumentParser(allow_abbrev=True, usage='%(prog)s [options]',
	description='Monitor the system for idle states and run scripts at the best time.')

	parser.add_argument('schedule', default='schedule.txt',
						nargs='?',
						help="Filename to read schedule from.")

	parser.add_argument('--polling', dest='polling_rate', default=1,
						nargs='?', type=float,
						help="How often to check (minutes)")

	parser.add_argument('--idle', default=0,
						nargs='?', type=float,
						help="How long to wait before going to sleep (minutes) 0=Disable")

	parser.add_argument('--verbose', default=1,
						nargs='?', type=int,
						help="What messages to print")

	parser.add_argument('--testing', default=False, action='store_true',
						help="Do everything, but actually run the scripts.")

	parser.add_argument('--skip', default=False, action='store_true',
						help="Don't run apps on startup, wait a bit.")

	return parser.parse_args(argfixer())


def main(args):
	polling_rate = args.polling_rate * 60
	idle_sleep = args.idle * 60
	if idle_sleep:
		check_install('iostat', 'sar',
		msg='''sudo apt install sysstat sar
		--idle requires iostat () to determine if the computer can be put to sleep.''')
	check_install('xprintidle', msg="sudo apt install xprintidle")

	schedule_file = args.schedule
	testing_mode = args.testing

	sleep_time = polling_rate   # Time to rest at the end of every loop
	idle = 0                    # Seconds without user inteaction.
	elapsed = 0                 # Total time Computer has spent not idle
	total_idle = 0
	last_idle = 0
	timestamp = time.time()     # Timestamp at start of loop
	last_schedule_read = 0      # last time the schedule file was read
	schedule_apps = []
	for counter in itercount():

		# Sleep at the end of every loop
		if counter:
			missing = msleep(sleep_time)
			if missing:
				if missing > 2:
					print("Unaccounted for time during sleep:", fmt_time(missing))
				# Loop again to avoid edge case where the machine wakes up and is immediately put back to sleep
				total_idle = float(shell('xprintidle')) / 1000
				timestamp = time.time()
				continue

			# Get idle time and calculate elapsed time
			last_idle = total_idle
			total_idle = float(shell('xprintidle')) / 1000

			if total_idle > last_idle:
				idle = total_idle - last_idle
			else:
				idle = total_idle
			new_time = time.time()
			_old = elapsed
			elapsed += new_time - timestamp - idle
			if counter == 1:
				elapsed = 0
			timestamp = new_time
			if args.verbose >= 2:   # not (counter - 1) % 10:
				print(local_time(), 'Elapsed:', fmt_time(elapsed), 'Idle:', rint(idle))

		# Read the schedule file if it's been updated
		if os.path.getmtime(schedule_file) > last_schedule_read:
			if counter:
				print("\n\nSchedule file updated:")
			last_schedule_read = time.time()
			schedule_apps = read_schedule(schedule_apps, schedule_file)

		# Run scripts if enough elapsed time has passed
		for proc in schedule_apps:
			if proc.in_window() and proc.next_elapsed <= elapsed:
				if args.skip and counter < 10:
					testing = True
				else:
					testing = testing_mode
				proc.run(elapsed=elapsed, idle=idle, polling_rate=polling_rate, testing_mode=testing)


		# Put the computer to sleep after checking to make sure nothing is going on.
		if idle_sleep and total_idle > idle_sleep:
			if BATTERY.is_plugged():
				# Plugged mode waits for idle system.
				ready, results = tman.query(is_busy, max_age=sleep_time * 1.5)
				if ready:
					if not results:
						print("Going to sleep\n")
						if not testing_mode:
							quickrun('systemctl', 'suspend')
					else:
						print("Too busy to sleep")
			else:
				# Battery Mode doesn't wait for idle system.
				print("Idle and unplugged. Going to sleep.")
				if not testing_mode:
					quickrun('systemctl', 'suspend')




if __name__ == "__main__":
	UA = parse_args()

	# Min level to print messages:
	print = Eprinter(verbose=1 - UA.verbose).eprint     # pylint: disable=W0622,C0103
	# Workaround for desktop computers:
	try:
		BATTERY = BatteryWatcher()
	except ValueError:
		print("Battery monitoring will not work.")
		class BatteryWatcher:		# pylint: disable=function-redefined
			def is_plugged(self):
				return True
		BATTERY = BatteryWatcher()
	gohome()
	main(UA)
