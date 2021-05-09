#!/usr/bin/python3
# An autogenerated selection of SurpriseDog's Common functions relevant to this project.
# To see how this file was created visit: https://github.com/SurpriseDog/Star-Wrangler
# Written by SurpriseDog at: https://github.com/SurpriseDog

import os
import re
import sys
import csv
import time
import queue
import shutil
import inspect
import datetime
import threading
import subprocess
from collections import Counter
from urllib.parse import urlparse
from shutil import get_terminal_size
from datetime import datetime as dada

def debug_pass(*args, **kargs):         # pylint: disable=unused-argument
	"Drop in replacement to disable debug lines"
	pass


class DebugSetup:
	'''Print a timestamp, time since start, calling
	function and debuging information about variables
	Quick setup: from common import DebugSetup; debug = DebugSetup(level=1).debug
	Disable with: def debug(*args, **kargs): pass'''

	def __init__(self, show_clock=True, breaks=1, show_types=False, level=1):
		self.start = time.time()        # Start time
		self.show_clock = show_clock    # Print clock on left side
		self.breaks = breaks            # Line breaks before printing
		self.show_types = show_types    # Show types of each variable
		self.level = level              # Don't show messages >= this level

	def debug(self, *args, level=1, **kargs):
		'''breaks = line breaks before output
		Usage: debug(*message)'''
		if not level >= self.level:
			return

		out = []
		timer = time.time() - self.start
		show_clock = kargs.get('show_clock', self.show_clock)
		breaks = kargs.get('breaks', self.breaks)
		show_types = kargs.get('show_types', self.show_types)

		# Show type(arg) and formatted value
		for arg in args:
			if show_types:
				if type(arg) == str:
					out += [repr(arg)]
					continue
				typ = '<' + re.split("'", str(type(arg)))[-2] + '>'
				if type(arg) == int or type(arg) == float:
					arg = sig(arg)
				out += [typ, arg]
			else:
				out += [arg]
		# todo print dictionaries longer than a single line

		# Clock
		if show_clock:
			out = [time.strftime('%H:%M', time.localtime())] + out

		# Timer
		if timer < 3600:
			timer = '+' + sig(timer)
		else:
			timer = '+' + fmt_time(timer, pretty=False)
		out = [timer, inspect.stack()[1].function] + out

		# Print to stderr
		print('\n' * breaks, file=sys.stderr, end='')
		print(*out, file=sys.stderr)


def read_val(file):
	"Read a number from an open file handle"
	file.seek(0)
	return int(file.read())


def pmsleep(seconds):
	"Combination of psleep and msleep"
	print("Sleeping for", fmt_time(seconds, digits=2) + '...', file=sys.stderr)
	return msleep(seconds)


def read_file(filename):
	"Read an entire file into text"
	with open(filename, 'r') as f:
		return f.read()


def chunker(lis, lines=2, overlap=False):
	'''Take a list a return its values n items at a time
	alternate way: zip(*[iter(lis)]*n)'''
	step = 1 if overlap else lines
	for start in range(0, len(lis) - lines + 1, step):
		yield lis[start:start + lines]


def trailing_avg(lis, power=0.5):
	"Weighted average that biases the last parts of this list more:"
	total = 0
	weights = 0
	for index, num in enumerate(lis):
		weight = (index + 1)**power
		total += weight * num
		weights += weight
	return total / weights


def auto_columns(array, space=4, manual=None, printme=True, wrap=0, crop=[]):
	'''Automatically adjust column size
	Takes in a 2d array and prints it neatly
	space = spaces between columns
	manual = dictionary of column adjustments made to space variable
	crop = array of max length for each column, 0 = unlimited
	example: {-1:2} sets the space variable to 2 for the last column'''
	if not manual:
		manual = dict()

	# Convert generators and map objects:
	array = list(array)

	if crop:
		out = []
		for row in array:
			row = list(row)
			for index in range(len(row)):
				line = str(row[index])
				cut = crop[index]
				if cut > 3 and len(line) > cut:
					row[index] = line[:cut-3]+'...'
			out.append(row)
		array = out


	# Fixed so array can have inconsistently sized rows
	col_width = {}
	for row in array:
		row = list(map(str, row))
		for col in range(len(row)):
			length = len(row[col])
			if length > col_width.get(col, 0):
				col_width[col] = length

	col_width = [col_width[key] for key in sorted(col_width.keys())]
	spaces = [space] * len(col_width)
	spaces[-1] = 0

	# Make any manual adjustments
	for col, val in manual.items():
		spaces[col] = val

	col_width = [sum(x) for x in zip(col_width, spaces)]

	# Adjust for line wrap
	max_width = get_terminal_size().columns     # Terminal size
	if wrap:
		max_width = min(max_width, wrap)
	extra = sum(col_width) - max_width          # Amount columns exceed the terminal width

	def fill_remainder():
		"After operation to reduce column sizes, use up any remaining space"
		remain = max_width - sum(col_width)
		for x in range(len(col_width)):
			if remain:
				col_width[x] += 1
				remain -= 1

	if extra > 0:
		# print('extra', extra, 'total', total, 'max_width', max_width)
		# print(col_width, '=', sum(col_width))
		if max(col_width) > 0.5 * sum(col_width):
			# If there's one large column, reduce it
			index = col_width.index(max(col_width))
			col_width[index] -= extra
			if col_width[index] < max_width // len(col_width):
				# However if that's not enough reduce all columns equally
				col_width = [max_width // len(col_width)] * len(col_width)
				fill_remainder()
		else:
			# Otherwise reduce all columns proportionally
			col_width = [int(width * (max_width / (max_width + extra))) for width in col_width]
			fill_remainder()
		# print(col_width, '=', sum(col_width))

	# Turn on for visual representation of columns:
	# print(''.join([str(count) * x  for count, x in enumerate(col_width)]))

	if printme:
		for row in array:
			print_columns(row, columns=col_width, space=0)

	return col_width


def print_columns(args, col_width=20, columns=None, just='left', space=0, wrap=True):
	'''Print columns of col_width size.
	columns = manual list of column widths
	just = justification: left, right or center'''

	just = just[0].lower()
	if not columns:
		columns = [col_width] * len(args)

	output = ""
	_col_count = len(columns)
	extra = []
	for count, section in enumerate(args):
		width = columns[count]
		section = str(section)

		if wrap:
			lines = None
			if len(section) > width - space:
				# print(section, len(section), width)
				# lines = slicer(section, *([width] * (len(section) // width + 1)))
				lines = indenter(section, wrap=width - space)
				if len(lines) >= 2 and len(lines[-1]) <= space:
					lines[-2] += lines[-1]
					lines.pop(-1)
			if '\n' in section:
				lines = section.split('\n')
			if lines:
				section = lines[0]
				for lineno, line in enumerate(lines[1:]):
					if lineno + 1 > len(extra):
						extra.append([''] * len(args))
					extra[lineno][count] = line

		if just == 'l':
			output += section.ljust(width)
		elif just == 'r':
			output += section.rjust(width)
		elif just == 'c':
			output += section.center(width)
	print(output)

	for line in extra:
		print_columns(line, col_width, columns, just, space, wrap=False)


def list_get(lis, index, default=''):

	# Fetch a value from a list if it exists, otherwise return default
	# Now accepts negative indexes
	length = len(lis)
	if -length <= index < length:
		return lis[index]
	else:
		return default


def sorted_array(array, column=-1, reverse=False):
	"Return sorted 2d array line by line"
	pairs = [(line[column], index) for index, line in enumerate(array)]
	for _val, index in sorted(pairs, reverse=reverse):
		# print(index, val)
		yield array[index]


def avg(lis):
	"Average a list"
	return sum(lis) / len(lis)


def percent(num, digits=0):
	if not digits:
		return str(int(num * 100)) + '%'
	else:
		return sig(num * 100, digits) + '%'


class _TmanObj():
	"Used for ThreadManager"

	def __init__(self, func, *args, delay=0, **kargs):
		self.start = time.time()
		self.que, self.thread = spawn(func, *args, delay=delay, **kargs)

	def age(self):
		return time.time() - self.start

	def is_alive(self):
		return self.thread.is_alive()


class ThreadManager():
	"Maintain a list of threads and when they were started, query() to see if done."

	def __init__(self):
		self.threads = dict()

	def query(self, func, *args, delay=0, max_age=0, **kargs):
		"Start thread if new, return status, que.get()"
		serial = id(func)

		obj = self.threads.get(serial, None)
		if max_age and obj and obj.age() > max_age:
			print("Thread aged out")
			del obj
			obj = None
		if obj and obj.is_alive():
			print("Can't get results now, we got quilting to do!")
			return False, None
		if obj:
			del self.threads[serial]
			return True, obj.que.get()

		# print("Starting thread!")
		obj = _TmanObj(func, *args, delay=delay, **kargs)
		self.threads[serial] = obj
		return False, None

	def remove(self, func):
		"Remove thread if in dict"
		serial = id(func)
		if serial in self.threads:
			del self.threads[serial]


tman = ThreadManager()  # pylint: disable=C0103


def shell(cmd, **kargs):
	"Return first line of stdout"
	return quickrun(cmd, **kargs)[0].strip()


def flatten(tree):
	"Flatten a nested list, tuple or dict of any depth into a flat list"
	# For big data sets use this: https://stackoverflow.com/a/45323085/11343425
	out = []
	if isinstance(tree, dict):
		for key, val in tree.items():
			if type(val) in (list, tuple, dict):
				out += flatten(val)
			else:
				out.append({key: val})

	else:
		for item in tree:
			if type(item) in (list, tuple, dict):
				out += flatten(item)
			else:
				out.append(item)
	return out


def quickrun(*cmd, check=False, encoding='utf-8', errors='replace', mode='w', input=None,
			 verbose=0, testing=False, ofile=None, trifecta=False, hidewarning = False, **kargs):
	'''Run a command, list of commands as arguments or any combination therof and return
	the output is a list of decoded lines.
	check    = if the process exits with a non-zero exit code then quit
	testing  = Print command and don't do anything.
	ofile    = output file
	mode     = output file write mode
	trifecta = return (returncode, stdout, stderr)
	input	 = stdinput (auto converted to bytes)
	'''
	cmd = list(map(str, flatten(cmd)))
	if len(cmd) == 1:
		cmd = cmd[0]

	if testing:
		print("Not running command:", cmd)
		return []

	if verbose:
		print("Running command:", cmd)
		print("               =", ' '.join(cmd))

	if ofile:
		output = open(ofile, mode=mode)
	else:
		output = subprocess.PIPE

	if input:
		if type(input) != bytes:
			input = input.encode()

	#Run the command and get return value
	ret = subprocess.run(cmd, check=check, stdout=output, stderr=output, input=input, **kargs)
	code = ret.returncode
	stdout = ret.stdout.decode(encoding=encoding, errors=errors).splitlines() if ret.stdout else []
	stderr = ret.stderr.decode(encoding=encoding, errors=errors).splitlines() if ret.stderr else []

	if ofile:
		output.close()
		return []

	if trifecta:
		return code, stdout, stderr

	if code and not hidewarning:
		warn("Process returned code:", code)

	for line in stderr:
		print(line)

	return stdout


def joiner(char, *args):
	return char.join(map(str, args))


class DotDict(dict):
	'''Example:
	m = dotdict({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
	'''
	# Source: https://stackoverflow.com/questions/2352181/how-to-use-a-dot-to-access-members-of-dictionary

	def __init__(self, *args, **kwargs):
		super(DotDict, self).__init__(*args, **kwargs)
		for arg in args:
			if isinstance(arg, dict):
				for k, v in arg.items():
					self[k] = v

		if kwargs:
			for k, v in kwargs.items():
				self[k] = v

	def __getattr__(self, attr):
		return self.get(attr)

	def __setattr__(self, key, value):
		self.__setitem__(key, value)

	def __setitem__(self, key, value):
		super(DotDict, self).__setitem__(key, value)
		self.__dict__.update({key: value})

	def __delattr__(self, item):
		self.__delitem__(item)

	def __delitem__(self, key):
		super(DotDict, self).__delitem__(key)
		del self.__dict__[key]


def sig(num, digits=3):
	"Return number formatted for significant digits (formerly get_significant)"
	ret = ("{0:." + str(digits) + "g}").format(num)
	if 'e' in ret:
		if abs(num) >= 1:
			return str(int(num))
		else:
			return str(num)
	else:
		return ret


def bisect_small(lis, num):
	'''Given a sorted list, returns the index of the biggest number smaller than num
	Unlike bisect will never return an index which doesn't exist'''
	end = len(lis) - 1
	for x in range(end + 1):
		if lis[x] > num:
			return max(x - 1, 0)
	else:
		return end


def fmt_time(num, digits=2, pretty=True, smallest=None, fields=0, **kargs):
	'''Return a neatly formated time string.
	pretty example: "9 hours, 12 minutes" vs "9:12"
	sig         = the number of significant digits.
	fields      = Instead of siginificant digits, specify the number of date fields to produce.
	fields overrides digits
	todo make fields the default?
	smallest    = smallest units for non pretty printing'''
	if num < 0:
		num *= -1
		return '-' + fmt_time(**locals())

	if 'sig' in kargs:
		digits = kargs['sig']
		print("\nWarning! sig is deprecated. Use <digits> instead.\n")

	if pretty:
		# Return number and unit text
		if num < 5.391e-44:
			return "0 seconds"
		out = []
		# For calculations involving leap years, use the datetime library:
		limits = (5.391e-44, 1e-24, 1e-21, 1e-18, 1e-15, 1e-12, 1e-09, 1e-06, 0.001, 1, 60,
				  3600, 3600 * 24, 3600 * 24 * 7, 3600 * 24 * 30.4167, 3600 * 24 * 365.2422)
		names = (
			'Planck time',
			'yoctosecond',
			'zeptosecond',
			'attosecond',
			'femtosecond',
			'picosecond',
			'nanosecond',
			'microsecond',
			'millisecond',
			'second',
			'minute',
			'hour',
			'day',
			'week',
			'month',
			'year')

		index = bisect_small(limits, num) + 1
		while index > 0 and (digits > 0 or fields > 0):
			index -= 1
			unit = limits[index]
			u_num = num / unit          # example: 3.7122314232145 (days)
			name = names[index]

			if name == 'week' and u_num < 2:
				# Replace weeks with days when less than 2 weeks
				digits -= 1
				continue
			if u_num < 1:
				# Avoids the "3 minutes, 2 nanoseconds" nonsense.
				if name in ('second', 'minute', 'hour', 'week', 'month'):
					digits -= 2
				else:
					digits -= 3
				continue

			fields -= 1
			if num >= 60 or fields:     # Minutes or higher
				u_num = int(u_num)
				out += [str(u_num) + ' ' + name + ('s' if u_num != 1 else '')]
				digits -= len(str(u_num))
				num -= u_num * unit
			else:               # Seconds or lower
				d = digits if digits >= 1 else 1
				out += [sig(u_num, d) + ' ' + name + ('s' if u_num != 1 else '')]
				break
		return ', '.join(out)

	else:
		# Normal "2:40" style format
		num = int(num)
		s = str(datetime.timedelta(seconds=num))
		if num < 3600:
			s = s[2:]  # .lstrip('0')

		# Strip smaller units
		if smallest == 'minutes' or (not smallest and num >= 3600):
			return s[:-3]
		elif smallest == 'seconds' or not smallest:
			return s
		elif smallest == 'hours':
			return s[:-6] + ' hours'


def seconds_since_midnight(seconds=None):
	if seconds:
		t = time.localtime(seconds)
	else:
		t = time.localtime()
	return t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec + time.time() % 1


def argfixer():
	'''Fix up args for argparse. Lowers case and turns -args into --args'''
	out = []
	sys.argv = [word.lower() for word in sys.argv]
	for word in sys.argv:
		word = word.lower()
		if re.match('^-[^-]', word):
			out.append('-' + word)
		else:
			out.append(word)
	return out[1:]


def itercount(start=0, step=1):
	"Save an import itertools"
	x = start
	while True:
		yield x
		x += step


def dict_valtokey(dic, val):
	"Take a dictionary value and return the first key found:"
	for k, v in dic.items():
		if val == v:
			return k


def read_state(filename, multiline=False, forget=False, verbose=True, cleanup_age=86400):
	"todo make this a class"
	'''
	Maintains open file handles to read the state of a file without wasting resources
	forget =        open a file without maintaing open file handle
	multiline =     Return every stdout line instead of just the first.
	cleanup_age =   Minimum age to keep an old unaccessed file around before cleaning it up
	verbose =       1   Print a notification each time a new file opened
	verbose =       2   Print a notification each time a file is accesssed
	'''

	if verbose >= 2:
		print("Reading:", filename)

	# Open a file and don't add it to the log
	if forget:
		with open(filename, 'r') as f:
			if multiline:
				return list(map(str.strip, f.readlines()))
			else:
				return f.readline().strip()

	# Keep a dictionary of open files
	self = read_state
	now = time.time()
	if not hasattr(self, 'filenames'):
		self.filenames = dict()         # dictionary of filenames to file handles
		self.history = dict()           # When was the last time file was opened?
		self.last_cleanup = now         # Cleanup old files, occassionally
		# There is a limit to the number of open file handles.
		self.limit = 64                 # int(resource.getrlimit(resource.RLIMIT_NOFILE)[0] / 4)

	# Cleanup old unused file handles
	if cleanup_age and now - self.last_cleanup > cleanup_age / 2:
		self.last_cleanup = now
		for name in list(self.history.keys()):
			if name == filename:
				continue
			if now - self.history[name] > cleanup_age:
				print("Removing old file handle:", name)
				f = self.filenames[name]
				del self.filenames[name]
				del self.history[name]
				f.close()

	# Remove files if past the limit of file handles
	if len(self.filenames) > self.limit:
		earliest = sorted(list(self.history.values()))[0]
		name = dict_valtokey(self.history, earliest)
		print("\nToo many open handles! Removing:", name)
		f = self.filenames[name]
		f.close()
		del self.filenames[name]
		del self.history[name]

	# Open the file
	if filename not in self.filenames:
		if verbose:
			print("Opening", '#' + str(len(self.filenames) + 1) + ':', filename)
		try:
			f = open(filename, 'r')
		except BaseException:
			raise ValueError("Could not open: " + filename)
		self.filenames[filename] = f
	else:
		f = self.filenames[filename]
		f.seek(0)
	self.history[filename] = now

	# Return data
	if multiline:
		return list(map(str.strip, f.readlines()))
	else:
		return f.readline().strip()


def read_csv(filename, ignore_comments=True, cleanup=True, headers=None, merge=False, delimiter=',', **kargs):
	'''Read a csv while stripping comments and turning numbers into numbers
	ignore_comments = ignore a leading #
	cleanup = remove quotes and fix numbers
	headers = instead of a list return a dict with headers as keys for columns
	delimiter = seperator between columns.
		If you provide a list it will try each one in turn, but the first option must be a single character
	merge = merge repeated delimiter'''

	def clean(row):
		"Strip all the junk off of csv file"
		if not cleanup:
			return row
		out = []
		for item in row:
			# Cleanup any quote wraps
			item = item.strip()
			if item.startswith("'") and item.endswith("'"):
				item.strip("'")
			if item.startswith('"') and item.endswith('"'):
				item.strip('"')


			# Check if its a number
			if item.lstrip('-').replace('.', '', 1).isdigit():
				if '.' in item:
					item = float(item)
				else:
					item = int(item)
			out.append(item)
		return out

	def get_headers(row):
		if not headers:
			return row

		out = {key: None for key in headers}
		length = len(headers)
		count = 0
		for item in row:
			if count >= length:
				if item:
					print("Warning! Unused items while reading line:", row[count:])
				break
			out[headers[count]] = item
			count += 1
		return out

	with open(filename) as f:
		for line in f.readlines():
			if not line:
				yield get_headers(clean([]))

			if delimiter[0] in line:
				row = next(csv.reader([line], delimiter=delimiter[0], **kargs))
			else:
				for d in delimiter[1:]:
					if d in line:
						row = next(csv.reader([line.replace(d, delimiter[0])], delimiter=delimiter[0], **kargs))
						print("Using backup delimiter to read line:", repr(d))
						break
				else:
					continue

			if row:
				if merge:
					# Eliminate empty columns
					copy = row.copy()
					row = []
					for item in copy:
						if item:
							row.append(item)
				if not ignore_comments:
					yield get_headers(clean(row))
				elif not row[0].startswith('#'):
					yield get_headers(clean(row))


		'''
		csv_reader = csv.reader(f, **kargs)
		for row in csv_reader:
		'''


def gohome():
	os.chdir(os.path.dirname(sys.argv[0]))


def error(*args, header='\nError:', **kargs):
	eprint(*args, header=header, v=3, **kargs)
	sys.exit(1)


def msleep(seconds, accuracy=1/60):
	'''Sleep for a time period and return amount of missing time during sleep
	For example, if computer was in suspend mode.
	Average error is about 100ms per 1000 seconds = .01%
	'''
	start = time.time()
	time.sleep(seconds)
	elapsed = time.time() - start
	if elapsed / seconds > 1 + accuracy:
		return elapsed - seconds
	else:
		return 0


def safe_filename(filename, src="/ ", dest="-_", no_http=True, length=200, forbidden="*?\\/:<>|"):
	'''Convert urls and the like to safe filesystem names
	src, dest is the character translation table
	length is the max length allowed, set to 200 so rdiff-backup doesn't get upset
	forbidden characters are deleted'''
	if no_http:
		if filename.startswith("http") or filename.startswith("www."):
			netloc = urlparse(filename).netloc
			filename = filename[filename.find(netloc):]
			filename = re.sub("^www\\.", "", filename)
			filename = filename.strip('/')
	filename = filename.translate(filename.maketrans(src, dest)).strip()
	return ''.join(c for c in filename.strip() if c not in forbidden)[:length]


def spawn(func, *args, daemon=True, delay=0, **kargs):
	'''Spawn a function to run seperately and return the que
	waits for delay seconds before running
	Get the results with que.get()
	Check if the thread is still running with thread.is_alive()
	replaces fork_cmd, mcall
	print('func=', func, id(func))'''

	def worker():
		if delay:
			time.sleep(delay)
		ret = func(*args, **kargs)
		que.put(ret)

	que = queue.Queue()
	# print('args=', args)
	thread = threading.Thread(target=worker)
	thread.daemon = daemon
	thread.start()
	return que, thread


def diff_days(*args):
	'''Return days between two timestamps
	or between now and timestamp
	Ex: diff_days(time.time(), time.time()+86400)
	Ex: diff_days(timestamp)'''
	if len(args) == 2:
		start = args[0]
		end = args[1]
	else:
		end = args[0]
		start = time.time()
	diff = (dada.fromtimestamp(end) - dada.fromtimestamp(start))
	return diff.days + diff.seconds / 86400  # + diff.microseconds/86400e6


def local_time(timestamp=None, user_format=None):
	'''Given a unix timestamp, show the local time in a nice format:
	By default will not show date, unless more than a day into future.Format info here:
	https://docs.python.org/3.5/library/time.html#time.strftime '''
	if not timestamp:
		timestamp = time.time()

	if user_format:
		fmt = user_format
	else:
		fmt = '%I:%M %p'
		if timestamp and time.localtime()[:3] != time.localtime(timestamp)[:3]:
			if time.localtime()[:2] != time.localtime(timestamp)[:2]:
				# New month
				fmt = '%Y-%m-%d'
			else:
				if diff_days(timestamp) < 7:
					# New day of week
					fmt = '%a %I:%M %p'
				else:
					# New day in same month
					fmt = '%m-%d %I:%M %p'

	return time.strftime(fmt, time.localtime(timestamp))


def rint(num):
	return str(int(round(num)))


def search_list(expr, the_list, getfirst=False, func='match', ignorecase=True, searcher=None):
	'''Search for expression in each item in list (or dictionary!)
	getfirst = Return the first value found, otherwise None
	searcher = Custom lamda function'''

	if not searcher:
		# func = dict(search='in').get('search', func)
		# Avoiding regex now in case substring has a regex escape character
		if ignorecase:
			expr = expr.lower()
		if func in ('in', 'search'):
			if ignorecase:
				def searcher(expr, item): return expr in item.lower()   # pylint: disable=E0102
			else:
				def searcher(expr, item): return expr in item           # pylint: disable=E0102
		elif func == 'match':
			if ignorecase:
				def searcher(expr, item): return item.lower().startswith(expr)  # pylint: disable=E0102
			else:
				def searcher(expr, item): return item.startswith(expr)          # pylint: disable=E0102
		else:
			# Could have nested these, but this is faster.
			raise ValueError("Unknown search type:", func)

	output = []
	for item in the_list:
		if searcher(expr, item):
			if isinstance(the_list, dict):
				output.append(the_list[item])
			else:
				output.append(item)
			if getfirst:
				return output[0]
	return output


def convert_user_time(unum, default='hours'):
	'''Convert a user input time like 3.14 days to seconds
	Valid: 3h, 3 hours, 3 a.m., 3pm, 3:14 am, 3:14pm'''
	unum = str(unum).strip().lower()
	if ',' in unum:
		return sum(map(convert_user_time, unum.split(',')))
	if not unum:
		return 0


	# Build conversion table
	self = convert_user_time
	if not hasattr(self, 'conversions'):
		day = 3600 * 24
		year = 365.2422 * day

		self.conversions = dict(
			seconds=1,
			minutes=60,
			hours=3600,
			days=day,
			weeks=7 * day,
			months=30.4167 * day,
			years=year,
			decades=10 * year,
			centuries=100 * year,
			century=100 * year,
			millenia=1000 * year,
			millenium=1000 * year,

			# Esoteric:
			fortnight=14 * day,
			quarter=30.4167 * day * 3,
			jubilees=50 * year,
			biennium=2 * year,
			gigasecond=1e9,
			aeons=1e9 * year, eons=1e9 * year,
			jiffy=1 / 60, jiffies=1 / 60,
			shakes=1e-8,
			svedbergs=1e-13,
			decasecond=10,
			hectosecond=100,

			# Nonstandard years
			tropicalyears=365.24219 * day,
			gregorianyears=year,
			siderealyears=365.242190 * day,

			# <1 second
			plancktimes=5.391e-44, plancks=5.391e-44,
			yoctoseconds=1e-24, ys=1e-24,
			zeptoseconds=1e-21, zs=1e-21,
			attoseconds=1e-18,
			femtoseconds=1e-15, fs=1e-15,
			picoseconds=1e-12, ps=1e-12,
			nanoseconds=1e-09, ns=1e-9,
			microseconds=1e-06, us=1e-6,
			milliseconds=1e-3, ms=1e-3)
		self.conversions['as'] = 1e-18
	conversions = self.conversions

	# Primary units
	units = "seconds minutes hours days months years".split()

	# 12 am fix
	if re.match('12[^1234567890].*am', unum) or unum == '12am':
		unum = unum.replace('12', '0')

	# Text processing:
	text = unum.lstrip('0123456789. \t:')
	num = unum.replace(text, '').strip()

	if ':' in num:
		# Convert a num like 3:14:60 into fractions of 60
		seconds = 0
		for x, t in enumerate(num.split(':')):
			seconds += float(t) / 60**x
		num = seconds

	num = float(num)
	if text:
		text = text.replace('.', '').strip().replace(' ', '')
		if text == 'am':
			return num * 3600
		elif text == 'pm':
			return num * 3600 + 12 * 3600
		else:
			# Match the text with the first unit found in units so that 3m matches minutes, not months
			unit = search_list(text, units, getfirst=True)
			if not unit:

				# Otherwise search for less commonly used units in entire list
				matches = search_list(text, conversions.keys())
				if len(matches) == 1:
					unit = matches[0]
				elif len(matches) > 1:
					if len({conversions[m] for m in matches}) == 1:
						unit = matches[0]
					else:
						print("Multiple Matches found for:", text)
						print("\n".join(matches))
						raise ValueError
				else:
					raise ValueError("Unknown unit:", text)
			return num * conversions[unit]
	else:
		return num * conversions[default]


def convert_ut_range(unum, **kargs):
	"User time ranges like 3-5pm to machine readable"
	unum = unum.lower().strip().split('-')
	count = Counter([item[-2:] for item in unum])
	pm = count['pm']
	am = count['am']
	if (pm or am) and not all([pm, am]):
		unit = 'pm' if pm else 'am'
		value = None		# Value of last time encountered
		for x in range(len(unum)):
			if unum[x]:
				if unum[x].endswith(unit):
					value = convert_user_time(unum[x].strip('pm').strip('am'))
				else:
					if value != None and convert_user_time(unum[x]) < value:
						continue
					unum[x] = unum[x] + unit
	return [convert_user_time(item, **kargs) for item in unum]


def mkdir(target, exist_ok=True, **kargs):
	"Make a directory without fuss"
	os.makedirs(target, exist_ok=exist_ok, **kargs)


def check_install(*programs, msg=''):
	'''Check if program is installed (and reccomend procedure to install)
	programs is the list of programs to test
	prints msg if it can't find any'''

	errors = 0
	for program in programs:
		paths = shutil.which(program)
		if not paths:
			errors += 1
			print(program, 'is not installed.')
	if errors:
		if msg:
			if type(msg) == str:
				print("To install type:", msg)
			else:
				print("To install type:")
				for m in msg:
					print('\t' + m)
		else:
			print("Please install to continue...")
		sys.exit(1)


def indenter(*args, header='', level=0, tab=4, wrap=0, even=False):
	"Break up text into tabbed lines. Wrap at max characters. 0 = Don't wrap"

	if type(tab) == int:
		tab = ' ' * tab
	header = header + tab * level
	words = (' '.join(map(str, args))).split(' ')

	lc = float('inf')       # line count
	for wrap in range(wrap, -1, -1):
		out = []
		line = ''
		count = 0
		for word in words:
			if count:
				new = line + ' ' + word
			else:
				new = header + word
			count += 1
			if wrap and len(new.replace('\t', ' ' * 4)) > wrap:
				out.append(line)
				line = header + word
			else:
				line = new
		if line:
			out.append(line)
		if not even:
			return out
		if len(out) > lc:
			return prev
		prev = out.copy()
		lc = len(out)
	return out


class Eprinter:
	'''Drop in replace to print errors if verbose level higher than setup level
	To replace every print statement type: from common import eprint as print

	eprint(v=-1)    # Normally hidden messages
	eprint(v=0)     # Default level
	eprint(v=1)     # Priority messages
	eprint(v=2)     # Warnings
	eprint(v=3)     # Errors
	'''

	# Setup: eprint = Eprinter(<verbosity level>).eprint
	# Simple setup: from common import eprint
	# Usage: eprint(messages, v=1)

	# Don't forget they must end in 'm'
	BOLD = '\033[1m'
	WARNING = '\x1b[1;33;40m'
	FAIL = '\x1b[0;31;40m'
	END = '\x1b[0m'

	def __init__(self, verbose=0):
		self.level = verbose

	def eprint(self, *args, v=0, color=None, header=None, **kargs):
		'''Print to stderr
		Custom color example: color='1;33;40'
		More colors: https://stackoverflow.com/a/21786287/11343425
		'''
		verbose = v
		# Will print if verbose >= level
		if verbose < self.level:
			return 0

		if not color:
			if v == 2 and not color:
				color = f"{self.WARNING}"
			if v >= 3 and not color:
				color = f"{self.FAIL}" + f"{self.BOLD}"
		else:
			color = '\x1b[' + color + 'm'

		msg = ' '.join(map(str, args))
		if header:
			msg = header + ' ' + msg
		if color:
			print(color + msg + f"{self.END}", file=sys.stderr, **kargs)
		else:
			print(msg, file=sys.stderr, **kargs)
		return len(msg)


eprint = Eprinter(verbose=1).eprint     # pylint: disable=C0103


def warn(*args, header="\n\nWarning:", delay=1 / 64):
	time.sleep(eprint(*args, header=header, v=2) * delay)



'''
&&&&%%%%%&@@@@&&&%%%%##%%%#%%&@@&&&&%%%%%%/%&&%%%%%%%%%%%&&&%%%%%&&&@@@@&%%%%%%%
%%%%%%%%&@&(((((#%%&%%%%%%%%%&@@&&&&&&%%%&&&&&%%%%%%%%%%%&&&&%&%#((((/#@@%%%%%%%
&&%%%%%%&@(*,,,,,,,/%&%%%%%%%&@@&&&&&%%&&&&%%&&%%%%%%%%%%&&&%#*,,,,,,*/&@&%%%%%%
%%%%%%%&@&/*,,,*,*,,*/%&%%%%%&@@&&&&&&%%&&&&&&&%%%%%%&%%%&&%*,,,,,,,,**#@&&%%%%%
&&&&&%%&@#(**********,*(#&%%%&@&&&&%%%%%%%%%&&&%%%%%%&%&&#*****,*******#@&&%%%%%
&&&%%%&&#/***/*****/*,**,*%&%&@@&&&&&&&&&&&&&&&%%%%%%&&#*,,,*/******/***(%&%%%%%
&&&%%%&%/*****///////**,,,,*/%%&&@@@@@@@@@@@@@@@@&&%#*,,,*,*(///////*****#%&%%%%
@@&%%#&#/,,,*/(//((((//**,,*/#&@@@@@&&&&&&&&&&@@@@@%(/*,,**/(/(((/(//*,,*(&&%%%%
&&&%##&#*,,,*////((((/*///(&@&@@&&&#%((//(/###%&@&@@@@#//**//(#(///***,.,/&&%%%%
%%%%%#%#*,,,**////(///((#&&&%@&%%(/*,,......,,/(#%&&&@@@%((/(/#(///**,,,,(&%%%%%
&&%%%#%%/,..***//(#(#%%&@@@&@%(*.,,..       ...,.,/#@&@@@&&%#(((///**,..,#%%%%%%
%&%%%%%#*,****/(##&@@@&@@@@&%*,....           ....,,(&@@@@@@&@&%((//****,(%%%%%%
%&%%%%%#/,**/#&@@@&@@@@@@@&(*,......    .     ..,..,.(&@@@@@@@&@@@&%#**,*(%%%%%%
&&%%%%#&#(#&@@@&@@@@@@@@%((#@@%&&((,,,,,..,,(**(%@@&@%##(&@@@@@@@@&&@@%#(%%%%%%%
&&&%%%%%&&&&&&@@@@@@%###%@(,%&/@@&(%(/*,..,*/%##&&,%@(*&@#((%&@@@@@@&&@&%%%%&&%%
&&%%%%%%&&&@@@@@@@@#((*#@%,#%%&@#%(/**//,****/(#%%%&&%*(@@*/#(&@@@@@@@&&%%%%%%%%
&&&%%%%%&@@@@&%#/,,,,*,(/%&@@&((%(*,*,,*,**,,*,*#%(#@@&%((**,,,,*#(%&@@&&%%%%%%%
&&&%%%%%@@@@%*/*,...,*,,/*#(//#****,***********,**/#/##(/*,*,...,*/*/&@@&%%&%%%%
&&%%%%%%&@@@(//,....,,*/****/,,/**************/***/,,//**/**,....,*//&@@&%%&%%%%
&&&%%%%%&@@%(/*,. ...,****/*/(//*%&@@&%%%%%%&&&&//*/(*/**/**......,/*#&@&%&&&&%%
&&%%%%%%&@@%(**,,....,/**/((/,#&&&&&%#((((((%&&&@&%/*/(/**/*,. ..,,*/((#@&&&&&&%
%&%%%%%%&&#(/**,..,,,***/((,./%&%&&&@&(/#((#@@&&&%&%,,/((*,/*,,..,,,///(%&%&&&&&
&&%%%%%%&#,**,.,..,,*(//(/,,.,&&&@#&@@##%(#&@&%%@&&#.,,/(((//*,,..,,**,*&%&&%&&&
&&%##%%%#/**,,,,..,*/((((*...,,#&##%(#%%&%%###%(%&/,.. **((((/,...,,,,**(%%#%%%&
&&%####(**,,,.,,.,,/(/(//*,,..../%&(##%&&&%%(#%&#, .. .**//(/(*,,..,.,,**/((#%%%
&&&%#///*,........,/(((//**,.   ,,(#%%%%%%&#%##**.   ,,*//((((*,........,*//(%%%
%%%%(/**...       .,/(((///*., .,*(#(%%%%%%%%##/*,..,,*///((/*.      .....**/(%%
%%%%#(,..          .,/((/(//****,/(((###%#%(#///**,,**/((/((*,          .,.,(%%%
&&%%%#/*...          ,*/(/(/((%%&#&#(/%./.*%(#%#%#&&(((/(/*,.          ..,**(&%%
&&%%%%(*.....          ..*((/**(#&&&&&&&%%%&%&&&%(/,*/((*..           .,..*(&&%%
&&%%%%&#*.      .        */(#/*,,*/((%#%%%%%((**,.*/(#(/,       .       ,(%&%%&%
%%%%%%&%#//**,..           .**(((*,...,,**,,..*,/((/*,.          ...,,//(#%%%%%%
%%%&&&%(/*,**,..,,.,..       .,,**//**,*,,,*,////*,,.        .,.,...,,,**//#%&%%
%%%&&%#/*,*,.    ...      ..         ...  ,.. .       .       ...   ..,,*/(#%&%%
&&&&&%(((*.*... . .*,.   .           .*%%#(,.          .    .*,. ..,.,,**/(%#&%%
Generated on: 2021-05-08
'''