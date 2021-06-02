#!/usr/bin/python3
# LazyCron - "Your computer will get around to it eventually."
# Usage: Run with -h for help.

################################################################################

import os
import time

import how_busy
import scheduler

from sd_common import itercount, warn, gohome, quickrun, check_install, easy_parse
from sd_common import shell, rint, read_csv, tman

from sd_chronology import local_time, msleep, fmt_time

def parse_args():
	"Parse arguments"
	positionals = [\
	["schedule", '', str, 'schedule.txt'],
	"Filename to read schedule from."
	]
	args = [\
	['polling', 'polling_rate', float, 1],
	"How often to check (minutes)",
	['idle', '', float, 0],
	"How long to wait before going to sleep (minutes) 0=Disable",
	['verbose', '', int, 1],
	"What messages to print",
	['testing', '', bool],
	"Do everything, but actually run the scripts.",
	['skip', '', bool],
	"Don't run apps on startup, wait a bit."
	]
	return easy_parse(args,
					  positionals,
					  usage='<schedule file>, options...',
					  description='Monitor the system for idle states and run scripts at the best time.')


def read_schedule(schedule_apps, schedule_file):
	"Read the schedule file"
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
				proc = scheduler.Scheduler(line)
				proc.print()
				new_sched.append(proc)
		else:
			print("Could not process:", line)
	return new_sched


def is_busy(max_net=100, max_disk=1):
	'''Return True if disk or network usage above defaults
	max_net = Network usage in KB/s
	max_disk = Disk usage in MB/s
	'''

	net_usage = how_busy.get_network_usage(5, 4)     # KB/s
	disk_usage = how_busy.all_disk_usage(5, 4)       # MB/s

	if net_usage < max_net and disk_usage < max_disk:
		return False
	else:
		print("Network Usage:", net_usage)
		print("Disk usage:   ", disk_usage)
	return True


def main(args):
	polling_rate = args.polling_rate * 60
	idle_sleep = args.idle * 60
	if idle_sleep:
		check_install('iostat', 'sar',
					  msg='''sudo apt install sysstat sar
					  --idle requires iostat () to determine if the computer can be put to sleep.''')
	check_install('xprintidle', msg="sudo apt install xprintidle")

	schedule_file = args.schedule	# Tab seperated input file
	testing_mode = args.testing		# Don't actually do anything

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
				if missing > 5:
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
				print(local_time(), 'Elapsed:', fmt_time(elapsed), 'Idle:', rint(total_idle))


		# Read the schedule file if it's been updated
		if os.path.getmtime(schedule_file) > last_schedule_read:
			if counter:
				print("\n\nSchedule file updated:")
			last_schedule_read = time.time()
			schedule_apps = read_schedule(schedule_apps, schedule_file)


		# Run scripts if enough elapsed time has passed
		for proc in schedule_apps:
			if proc.in_window() and proc.next_elapsed <= elapsed:
				if args.skip and counter < 2:
					testing = True
				else:
					testing = testing_mode
				proc.run(elapsed=elapsed, idle=total_idle, polling_rate=polling_rate, testing_mode=testing)


		# Put the computer to sleep after checking to make sure nothing is going on.
		if idle_sleep and total_idle > idle_sleep:
			if scheduler.is_plugged():
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
	scheduler.EP.verbose = 1 - UA.verbose
	gohome()
	main(UA)
