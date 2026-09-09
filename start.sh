#!/bin/bash

# Run both services with the same production process definition used on the
# server. Install PM2 first if it is not already available.
exec pm2 startOrReload ecosystem.config.js --update-env
