#!/bin/bash
redis-server /etc/redis/redis.conf --daemonize yes
python bot.py

