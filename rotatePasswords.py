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
import datetime
import hashlib
from paramiko import client, ssh_exception
import random
import socket
import string
import time
import yaml
import MySQLdb

PASS_CHARS = string.ascii_letters + string.digits
RETRIES = [5*60] * 6


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
  def __init__(self, ssh_config, accept_all):
    self.username = ssh_config['user']
    self.filename = ssh_config['filename']
    self.key = ssh_config['key']
    self.hostkeys = ssh_config.get('hostkeys')

    self.ssh = client.SSHClient()
    self.ssh.load_system_host_keys()
    if self.hostkeys:
        self.ssh.load_host_keys(self.hostkeys)
    if accept_all:
        self.ssh.set_missing_host_key_policy(client.AutoAddPolicy())
    self.todo = {}

  def UpdatePassword(self, hostname, password):
    """Attempt to perform update, record todo if error."""
    print 'Updating password via SSH for %s' % hostname
    try:
      self.DoUpdate(hostname, password)
    except (ssh_exception.SSHException, socket.error) as e:
      print 'Error updating password on %s via SSH: %s' % (hostname, e)
      self.todo[hostname] = password

  def DoUpdate(self, hostname, password):
    """Actually perform the update by connecting to host over SSH."""
    self.ssh.connect(hostname, username=self.username, key_filename=self.key,
	timeout=10, banner_timeout=10)
    sftp = self.ssh.open_sftp()
    f = sftp.file(self.filename, 'w')
    f.write(password + '\n')
    f.close()
    sftp.close()

  def RetryFailedUpdates(self):
    """Retry all failed updates up to RETRIES times."""
    for i, retry_time in enumerate(RETRIES):
      if not self.todo:
        break
      time.sleep(retry_time)
      for hostname, password in self.todo.items():
        print 'Retrying update of password on %s (Attempt %d of %d)' % (
            hostname, i+1, len(RETRIES))
        try:
          self.DoUpdate(hostname, password)
          del self.todo[hostname]
	  print 'Retry of %s succeeded' % hostname
        except (ssh_exception.SSHException, socket.error) as e:
          print 'Error updating password on %s via SSH: %s' % (hostname, e)

  def SaveHostKeys(self):
    self.ssh.save_host_keys(self.hostkeys)


def DbUpdate(db, username, md5pass):
  print 'Updating DB password for %s' % username
  try:
    c = db.cursor()
    c.execute("UPDATE users SET password=%s where name=%s",
        (md5pass, username))
    db.commit()
  except MySQLdb.MySQLError as e:
    print 'Error updating %s in database: %s' % (username, e)
    return False
  finally:
    c.close()

  if not c.rowcount:
    print 'Username %s not found in database' % username
    return False
  elif c.rowcount > 1:
    print 'Warning: Too many entries for user %s found in database' % username
  return True


def RotateUser(username, hostname, db, ssh):
  """Rotate the password of a user in database and via SSH.

  Generates a new password, then uses the provided database and SSH clients to
  set that as the user's password.
  """
  newpass = ''.join(random.choice(PASS_CHARS) for _ in xrange(20))
  md5pass = hashlib.md5(newpass).hexdigest()

  db_success = DbUpdate(db, username, md5pass)

  if db_success:
    ssh.UpdatePassword(hostname, newpass)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--users',
      help='Comma-separated list of users whose passwords should be updated')
  parser.add_argument('--config', default='config.yml',
      help='Alternative config file to use (default is config.yml)')
  parser.add_argument('--accept', action='store_true',
      help='Accept all SSH host keys permanently')
  args = parser.parse_args()

  config_file = open(args.config)
  config = yaml.safe_load(config_file)
  config_file.close()

  print 'Beginning run at %s' % datetime.datetime.now()

  # Set up connections
  db = dbConnect(config['db'])
  ssh = sshPasswordUpdater(config['ssh'], args.accept)

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

  ssh.RetryFailedUpdates()
  ssh.SaveHostKeys()


if __name__ == '__main__':
  main()
