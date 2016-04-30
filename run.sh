#!/bin/bash

export PYTHONUNBUFFERED=1
cd $(dirname $0)
timeout --kill-after=1h 50m ./rotatePasswords.py &>> rotate.log
