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
from paramiko import client, ssh_exception
import random
import socket
import string
import yaml
import MySQLdb

PASS_CHARS = string.ascii_letters + string.digits

def dbConnect(db_config):
  """Open a connection to the database."""
  return MySQLdb.connect(
      host=db_config['hostname'],
      port=db_config['port'],
      user=db_config['user'],
      passwd=db_config['password'],
      db=db_config['db'])

class sshPasswordUpdater(object):
  """Convenience class for updating password files via SSH.

  Username for connections and the filename to update on the remote hosts are
  set via the config dict at initialization time, and then used for each call to
  the UpdatePassword method.
  """
  def __init__(self, ssh_config):
    self.ssh = client.SSHClient()
    self.ssh.load_system_host_keys()
    self.username = ssh_config['user']
    self.filename = ssh_config['filename']

  def UpdatePassword(self, hostname, password):
    self.ssh.connect(hostname, username=self.username)
    sftp = self.ssh.open_sftp()
    f = sftp.file(self.filename, 'w')
    f.write(password + '\n')
    f.close()
    sftp.close()

def RotateUser(username, hostname, db, ssh):
  """Rotate the password of a user in database and via SSH.

  Generates a new password, then uses the provided database and SSH clients to
  set that as the user's password.
  """
  newpass = ''.join(random.choice(PASS_CHARS) for _ in xrange(20))

  try:
    ssh.UpdatePassword(hostname, newpass)
  except (ssh_exception.SSHException, socket.error) as e:
    print 'Error updating password for %s on %s via SSH: %s' % (
        username, hostname, e)

  try:
    c = db.cursor()
    c.execute("UPDATE users SET password=%s where name=%s",
        (newpass, username))
    db.commit()
    if not c.rowcount:
      print 'Username %s not found in database' % username
    elif c.rowcount > 1:
      print 'Too many entries for user %s found in database' % username
  except MySQLdb.MySQLError as e:
    print 'Error updating %s in database: %s' % (username, e)
  finally:
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

  # Set up connections
  db = dbConnect(config['db'])
  ssh = sshPasswordUpdater(config['ssh'])

  # Determine users to update
  if args.users:
    users = args.users.split(',')
  else:
    users = config['users'].keys()

  # Perform updates
  for user in users:
    try:
      hostname = config['users'][user]
    except KeyError:
      print 'User %s not in config file' % user
      continue
    RotateUser(user, hostname, db, ssh)

if __name__ == '__main__':
  main()
