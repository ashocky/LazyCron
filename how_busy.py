#!/usr/bin/python3
# Tell me how busy the device running the directory is.
# Requires: sudo apt-get install sysstat
# Exit 0 if device not busy
# Usage ./how_busy folder_name

import re
import os
import sys
import time
import itertools

from sd.common import avg, qrun, sorted_array, auto_cols, flatten, check_install
from sd.common import percent, list_get

def is_device_busy(dev, wait=2, reps=4, verbose=0):
	"Check how busy the device is"
	if reps < 2:
		reps = 2

	usage = []
	get_ready = False     #next line contains the percentage
	for line in qrun('nice', 'iostat', '-d', '-x', dev, wait, reps + 1, verbose=verbose):
		val = re.split(' +', line)[-1]
		if get_ready:
			usage.append(float(val))
		get_ready = bool(val == '%util')
	# print(dev+':', usage[1:], '=', percent(avg(usage[1:])))
	return avg(usage[1:])


def all_disk_usage(wait=5, reps=4, verbose=0, ignore_links=True):
	'''Return total i/o for all devices in MB/s
	ignore_links will ignore loop and dm-? devs for total'''

	ready = False
	total = 0
	table = dict()
	rep = -1
	for line in qrun('nice', 'iostat', '-d', wait, reps + 1, verbose=verbose):
		if verbose >= 2:
			print(rep, line)
		if not line:
			continue
		if line.startswith('Device'):
			ready = True
			rep += 1
			continue
		if ready and rep > 0:
			# Skip the first rep because it contains bad data
			line = line.split()
			dev = line[0]
			usage = sum(map(float, line[2:4])) / 1e3
			table.setdefault(dev, []).append(usage)
			if ignore_links and (dev.startswith('dm-') or dev.startswith('loop')):
				continue
			total += usage
	if verbose:
		out = [['Device'] + ['Rep ' + str(rep + 1) for rep in range(reps)] + ['', 'Average MB/s']]
		for dev in sorted(table.keys()):
			out.append([dev] + list(map(int, table[dev])))
			out[-1] += ['=', int(avg(table[dev]))]
		out = [out[0]] + list(sorted_array(out[1:], reverse=True))
		auto_cols(out, manual={-3: 2, -2: 2})
	return total / reps


def get_network_usage(interval=1, samples=4, verbose=0):
	'''Return total network usage in kB/s, adds up rxkB/s and txkB/s columns from sar
	Requires: sudo apt install sysstat'''

	out = qrun('sar', '-n', 'DEV', interval, samples, verbose=verbose)
	if verbose:
		auto_cols(map(str.split, out[-3:]))
	out = [line for line in out if line.startswith('Average:')]
	out = flatten([line.split()[4:6] for line in out[1:]])
	return int(sum(map(float, out)))


def find_device(folder):
	"Given a directory, find the device"
	if os.path.isdir(folder):
		return qrun(['df', folder])[1].split()[0]
	return None


def wait_until_not_busy(folder, threshold=11, wait=2, reps=8, delta=2, sleep=2):
	'''Threshold in % points
	Loop waiting until device isn't busy.
	every loop the threshold grows higher by delta'''

	dev = find_device(folder)
	print("Probing", dev)

	for x in itertools.count():
		usage = is_device_busy(dev, wait, reps)
		if usage * 100 < threshold:
			break
		else:
			print(percent(usage), '>', int(threshold))
		threshold += ((x + 1) * delta)
		time.sleep(x * sleep)




if __name__ == "__main__":
	check_install('iostat', msg='sudo apt-get install sysstat')
	wait_until_not_busy(list_get(sys.argv, 1, '/home'))
