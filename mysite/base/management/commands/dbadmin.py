#!/usr/bin/env python
#coding=utf-8
from django.core.management.base import BaseCommand, CommandError
import time
from base.backup import backupdb
import sched

schedule = sched.scheduler(time.time,time.sleep)
def execute_command(cmd,inc):
    cmd()
    schedule.enter(inc,0,execute_command,(backupdb,inc))

class Command(BaseCommand):
    def handle(self, *args, **options):
        print "starting  service..." 
        while True:
            backupdb()
            time.sleep(10)
#        schedule.enter(0,0,execute_command,(backupdb,60))
#        schedule.run()
        
    
    
    