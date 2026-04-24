#!/bin/sh
set -e
# Substitute env vars into ACL template
envsubst < /usr/local/etc/redis/users.acl.template > /usr/local/etc/redis/users.acl
exec redis-server "$@"