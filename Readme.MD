Using Cron is nice if you have a server or never turn off your computer, but what if your laptop is asleep during the exact minute you have set to run your script? What if you have to reboot? What if your computer is actually running, but you would rather wait until its idle with the lid closed before running a backup process or other intensive script?

With LazyCron, "Your computer will get around to it eventually." LazyCron takes a more lackadaisical approach to life. Sure it will get the job done, but there's no rush.

You don't set a time to run, you set a range. In schedule.txt, "Time" is the window is when the script is allowed to run. You can have multiple time windows separated with commas. For example: 1-3am, 2pm-4pm, 11:30-11:34 - Play around with these numbers, the system is very flexible. When you run my script it will show you the next time window available for each program so you can confirm it's doing what you expected.


"Frequency" is how often the program. m = minutes, h = hours and so on. My script should allow most natural language inputs here. Time towards frequency is only counted when the computer is actively in use. Set as * and it will only run once a day.

"Date" field can limit it to run on certain days of the week:
Example m-f, every 2nd Thursday

Requirements is a comma separated list of additional requirements needed for the script to run. Available ones are as follows:


     idle    = Time the computer has been idle for

     busy    = Computer must have been in use within time specified

     plugged = Power cord must be attached

     closed  = Lid must be closed

     random  = Script will run randomly. Example: random 8h will (on average) run every 8 hours. Some days it will run 3+ times, other days not at all.


Not sure if your schedule will work correctly?
Run the program with the --testing option to show what it would have done and when.

===

Bonus Functionality:

	--idle will put the computer to sleep after so many minutes, but it will check first to make sure you don't have any disk or network activity. I find this more useful than using the default sleep timer which will put the computer to sleep regardless of what's going on.

====

Requirements:

	* xprintidle to get the idle time
	* systat package to get iostat which is used to measure disk activity before putting computer to sleep.


====


Usage: Edit schedule.txt and run LazyCron.py

Type -h for help
