#!/usr/bin/env python3

from os import path
from configparser import ConfigParser
from notify_run import Notify
import logging
from logging.handlers import RotatingFileHandler

FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
LOG_FILE = path.realpath(__file__)[:-3] + '.log'
LOG_LEVEL = 'INFO'

def get_file_handler():
    file_handler = RotatingFileHandler(LOG_FILE, mode='a', maxBytes=1000000, backupCount=2)
    file_handler.setFormatter(FORMATTER)
    return file_handler

def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.getLevelName(LOG_LEVEL))
    logger.addHandler(get_file_handler())
    logger.propagate = False
    return logger

def get_account_attributes(section):
    server = config[section]['server']
    login = config[section]['login']
    access_token = config[section]['access-token']
    return server, login, access_token

def register_notify_channel():
    notify = Notify()

    if config.has_option('notify-run','channel'):
        notify.endpoint = 'https://notify.run/' + config['notify-run']['channel']
        main_logger.info('Will use self provided channel: https://notify.run/c/' + config['notify-run']['channel'])
    elif notify.config_file_exists:
        main_logger.info('Will use notify-run saved config: https://notify.run/c/' + notify.endpoint[19:])
    else:
        main_logger.info('Neither my own nor notify-run config channel was found. Will register new...')
        main_logger.info(notify.register())

    return notify

def check_jira_updates(notify):
    from jira import JIRA
    from urllib import parse
    server, login, access_token = get_account_attributes('jira-options')
    mins_ago = config['notify-run']['mins-ago']
    jql = f"created >= -{mins_ago}m OR (updatedDate >= -{mins_ago}m and key in watchedIssues())"

    jira_options = {'server': config['jira-options']['server'] }
    jira = JIRA(options=jira_options, auth=(login, access_token))
    if int(jira.search_issues(jql).total) > 0:
        notify.send('You have updated JIRA issues!', server + '/secure/IssueNavigator.jspa?jqlQuery=' + parse.quote(jql))
    else:
        main_logger.info("There's no updates in watched Issues")

def check_gitlab_updates(notify):
    import gitlab
    from dateutil import parser as dp, tz
    from datetime import datetime, timedelta

    server, _, access_token = get_account_attributes('gitlab-options')
    mins_ago = int(config['notify-run']['mins-ago'])

    gl = gitlab.Gitlab(server, private_token=access_token)
    gl.auth()

    for project_id in config['gitlab-options']['projects'].split(','):
        project = gl.projects.get(project_id)
        events = project.events.list()
        events_total = 0
        for event in events:
            if (event.attributes['author']['id'] != gl.user.attributes['id'] and 
                dp.parse(event.attributes['created_at']) > datetime.utcnow().replace(tzinfo=tz.tzutc()) - timedelta(minutes=mins_ago)):
                events_total += 1
        if events_total > 0:
            notify.send('You have ' + str(events_total) + ' new GitLab events in \'' + project.attributes['name'] + '\' project!', server + '/' + project.attributes['path_with_namespace'] + '/activity')
        else:
            main_logger.info(f"There's no updates in project {project.attributes['name']}")

def main():
    notify = register_notify_channel()
 
    if config.getboolean('jira-options','watch'):
        main_logger.info('Check JIRA updates')
        try:
            check_jira_updates(notify)
        except:
            main_logger.exception('Something went wrong...')
 
    if config.getboolean('gitlab-options','watch'):
        main_logger.info('Check GitLab updates')
        try:
            check_gitlab_updates(notify)
        except:
            main_logger.exception('Something went wrong...')


main_logger = get_logger(__name__)

config = ConfigParser()
config.read(path.dirname(path.realpath(__file__)) + '/config.ini')

if __name__ == "__main__":
    main()
