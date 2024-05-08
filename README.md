Preparation:
1. Clone repository
2. Add to `/etc/systemd/system/openmower.service`:
```
  --volume /home/openmower/xbot_influxdb:/opt/open_mower_ros/src/lib/xbot_influxdb \
  --volume /boot/openmower/influxdb.ini:/config/influxdb.ini \
```
3. Reload systemd config with `systemctl daemon-reload`
4. Restart container with `service openmower restart`
5. Maintain InfluxDB connection details in `/boot/openmower/influxdb.ini`.

Installation (must be repeated on every container restart):
```bash
/opt/open_mower_ros/src/lib/xbot_influxdb/install.sh
```


Execution:
```bash
/opt/open_mower_ros/src/lib/xbot_influxdb/run.sh &
```
