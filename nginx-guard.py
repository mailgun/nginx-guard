#!/usr/bin/env python3

import argparse
import importlib
import logging
import pickle
import requests
import subprocess
import sys
import yaml

# Plans are to add additional modes like a continuous.
MODES = ['one-shot']

class NginxGuard(object):
    def __init__(self, config):
        self.cfg = config
        self.log = logging.getLogger('nginxguard')
        self.dynamic_sources = []

        if self.cfg['mode'] not in MODES:
            self.log.critical("{} is not a supported mode.".format(self.cfg['mode']))
            sys.exit(1)
        self.log.debug("Starting NginxGuard in mode: {}".format(self.cfg['mode']))
        self.run()
        
    def run(self):
        # gather sources from config
        sources = self.cfg['allow_static']
        # get sources from github
        github = self.get_github_sources()
        sources.extend(github)

        if self.is_updated(sources):
            self.log.info("Changes detected, updating whitelist.")
            self.update_whitelist(sources)
            self.reload_nginx()
        else:
            self.log.info("No changes detected.")

    def update_whitelist(self, sources):
        msg = "allow {};\n"
        lines = [msg.format(s) for s in sources]

        # Write whitelist file
        try:
            with open(self.cfg['whitelist_file'], 'w') as f:
                f.writelines(lines)
        except Exception as e:
            self.log.critical("Unable to write {0}: {1}".format(self.cfg['whitelist_file'], e))
            sys.exit(1)

        # Write state
        try:
            with open('.nginxguard', 'wb') as f:
                pickle.dump(sources, f)
        except Exception as e:
            self.log.warning("Unable to write state file. This will cause frequent nginx reloads.")

    def get_github_sources(self):
        self.log.debug("Getting source ips from Github.")
        url = 'https://api.github.com/meta'
        res = requests.get(url).json()
        subnets = []
        for key in ['hooks', 'git']:
            subnets.extend(res[key])
        return subnets

    def is_updated(self, sources):
        # Read state
        try:
            with open('.nginxguard', 'rb') as f:
                current_sources =  pickle.load(f)
        except Exception as e:
            self.log.warning("Cannot access state: {} Forcing reload.".format(e))
            return True

        return not current_sources == sources

    def reload_nginx(self):
        self.log.debug("Reloading nginx")
        cmd = [self.cfg['nginx_bin'], '-s', 'reload']
        try:
            subprocess.check_call(cmd, shell=True, check=True)
            self.log.debug("Nginx was reloaded successfully.")
        except subprocess.CalledProcessError:
            self.log.error("Failed to reload nginx!")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='NginxGuard')
    parser.add_argument('-c', action='store', dest='config_file', default='config.yaml')
    args = parser.parse_args()

    logging.basicConfig(
            stream=sys.stdout,
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    log = logging.getLogger(__name__)

    log.debug("Reading config file: {}".format(args.config_file))
    config = None
    try:
        with open(args.config_file, 'r') as f:
            config = yaml.load(f)
    except Exception as e:
        log.critical("Cannot read config file: {}".format(e))
        sys.exit(1)

    guard = NginxGuard(config)
