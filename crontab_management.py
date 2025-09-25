#! /usr/bin/python3

from crontab import CronTab

cron = CronTab(user='entomoscope')

minute = 5

for job in cron:

    if job.comment.startswith('Enable environment monitoring every'):

        job.minute.every(minute)
        job.comment = f'Enable environment monitoring every {minute} minutes'

        cron.write()
        print(job)


