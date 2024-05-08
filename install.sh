#!/usr/bin/bash
set -euo pipefail

apt update
apt install -y python3-pip libiw-dev
pip install influxdb_client utm iwlib
