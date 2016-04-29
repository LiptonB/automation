#!/bin/bash

timeout --kill-after=1h 50m ./rotatePasswords.py > rotate.log 2>&1
