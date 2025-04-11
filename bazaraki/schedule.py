#!/usr/bin/env python3

import click
import subprocess
import sys
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import signal
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('scheduler')

def run_command(command):
    """Execute a shell command and log its output"""
    logger.info(f"Running command: {command}")
    try:
        result = subprocess.run(command, shell=True, text=True)
        
        return result.returncode
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return 1

@click.command()
@click.option('-s', '--schedule', required=True, help='Cron schedule expression (e.g. "* * * * *" for every minute)')
@click.argument('command', required=True)
def cli(schedule, command):
    """Schedule a command to run at the specified cron schedule.
    
    Example: schedule -s "* * * * *" "make crawl"
    This will run 'make crawl' every minute.
    """
    try:
        scheduler = BackgroundScheduler()
        
        scheduler.add_job(
            run_command, 
            CronTrigger.from_crontab(schedule),
            args=[command]
        )
        
        # Start the scheduler
        scheduler.start()
        
        click.echo(f"Command scheduled: '{command}'")
        click.echo(f"Schedule: {schedule}")
        click.echo("Scheduler is running. Press Ctrl+C to exit.")
        
        # Handle graceful shutdownd
        def signal_handler(sig, frame):
            click.echo("\nShutting down scheduler...")
            scheduler.shutdown()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except ValueError as ve:
        click.echo(f"Error: {str(ve)}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()
