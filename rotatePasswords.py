#!/usr/bin/python
"""Rotate the KittenCoin password on a machine and in the database.

Rotate all passwords
rotatePasswords.py

Rotate just a few users
rotatePasswords.py --users team1,team2

Alternative config file (default is config.yml)
rotatePasswords.py --config myconf.yml
"""

import argparse
from paramiko import client
import random
import string
import sys
import yaml
import MySQLdb

PASS_CHARS = string.ascii_letters + string.digits

def RotateUser(username, hostname, db, ssh):
  newpass = ''.join(random.choice(PASS_CHARS) for _ in xrange(20))

  ssh.connect(hostname, username='irsec')
  sftp = ssh.open_sftp()
  f = sftp.file('/home/irsec/password', 'w')
  f.write(newpass)
  f.close()
  sftp.close()

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--users',
      help='Comma-separated list of users whose passwords should be updated')
  parser.add_argument('--config', default='config.yml',
      help='Alternative config file to use (default is config.yml)')
  args = parser.parse_args()

  config_file = open(args.config)
  config = yaml.safe_load(config_file)
  config_file.close()

  db = MySQLdb.connect(
      host=config['hostname'],
      user=config['user'],
      port=config['port'],
      passwd=config['password'])

  ssh = client.SSHClient()
  client.load_system_host_keys()

  if args.users:
    users = args.users.split(',')
  else:
    users = config['users'].keys()

  for user in users:
    try:
      hostname = config['users'][user]
    except KeyError:
      print >>sys.stderr, 'User %s not configured' % user
      continue
    RotateUser(user, hostname, db, ssh)

if __name__ == '__main__':
  main()
