# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    option_list = BaseCommand.option_list + ()
    help = "Reset  redis data"
    args = ''
 
    def handle(self, *args, **options):
        from base.sync_api import reset_data
        reset_data()
        
