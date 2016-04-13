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

def dbConnect(db_config):
  return MySQLdb.connect(
      host=db_config['hostname'],
      port=db_config['port'],
      user=db_config['user'],
      passwd=db_config['password'],
      db=db_config['db'])

class sshPasswordUpdater(object):
  def __init__(self, ssh_config):
    self.ssh = client.SSHClient()
    client.load_system_host_keys()
    self.username = ssh_config['user']
    self.filename = ssh_config['filename']

  def UpdatePassword(hostname, password):
    self.ssh.connect(hostname, username=self.username)
    sftp = self.ssh.open_sftp()
    f = sftp.file(self.filename, 'w')
    f.write(password)
    f.close()
    sftp.close()

def RotateUser(username, hostname, db, ssh):
  newpass = ''.join(random.choice(PASS_CHARS) for _ in xrange(20))

  ssh.UpdatePassword(hostname, newpass)

  c = db.cursor()
  c.execute("UPDATE users SET password='%s' where username='%s'",
      (newpass, username))
  c.close()

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

  db = dbConnect(config['db'])
  ssh = sshPasswordUpdater(config['ssh'])
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
