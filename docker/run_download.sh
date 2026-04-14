#!/bin/bash
set -e
cd /app
/usr/local/bin/python -m bustag.main download
/usr/local/bin/python -m bustag.main recommend