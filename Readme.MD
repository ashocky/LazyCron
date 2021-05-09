Using Cron is nice if you have a server or never turn off your computer, but what if your laptop goes to sleep during the exact minute you have set to run your script? What if you have to reboot? What if your computer is actually running, but you would rather wait until its idle with the lid closed before running a backup process or other intensive script?

With LazyCron, "Your computer will get around to it eventually." LazyCron takes a more lackadaisical approach to life. Sure it will get the job done, but there's no rush. Nap time takes priority.

You don't set a time to run, you set a range. In the schedule.txt example below, "Time" is the window is when the script is allowed to run. You can have multiple windows seperated with commas. For example: 1-3am, 2pm-4m, 11:30-11:34 - Play around with these numbers, the system is very flexible. When you run my script it will show you the next time window available for each program.

Not sure if your schedule will work correctly?
Run the program with the --testing option to show what it would do.

"Frequency" is how often the program. m = minutes, h = hours and so on. My script should allow most natural language inputs here. Set as * and it will only run once a day.

Requirements is a comma seperated list of additional requirements needed for the script to run. Available ones are as follows:


     idle    = Time the computer has been idle for

     plugged = Power cord must be attached

     closed  = Lid must be closed

     random  = Script will run randomly. On average it will run every so many minutes.

Usage: Edit schedule.txt and run LazyCron.py

Type -h for help