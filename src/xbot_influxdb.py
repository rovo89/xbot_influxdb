#!/usr/bin/env python3
import rospy
from influxdb_client import InfluxDBClient
from threading import Thread
import utm
import time
from iwlib.iwconfig import get_iwconfig
from mower_msgs.msg import Status, HighLevelStatus
from xbot_msgs.msg import AbsolutePose

def get_origin():
  global ORIGIN_X, ORIGIN_Y, ORIGIN_Z, ORIGIN_ZONE_NUMBER, ORIGIN_ZONE_LETTER
  datum_lat = rospy.get_param('/xbot_driver_gps/datum_lat')
  datum_lon = rospy.get_param('/xbot_driver_gps/datum_long')
  ORIGIN_Z = rospy.get_param('/xbot_driver_gps/datum_height')
  (ORIGIN_X, ORIGIN_Y, ORIGIN_ZONE_NUMBER, ORIGIN_ZONE_LETTER) = utm.from_latlon(datum_lat, datum_lon)

LAST_CALLED = dict()
def check_rate_limit(name: str) -> bool:
  now = time.monotonic()
  last = LAST_CALLED.get(name, None)
  if last is None or now >= last + MIN_INTERVAL:
    LAST_CALLED[name] = now
    return True
  else:
    return False


def on_mower_logic_current_state(msg):
  if not check_rate_limit('status1'): return
  write_api.write(bucket=BUCKET, record={
    'measurement': 'status1',
    'fields': {
      'state_name': msg.state_name,
      'sub_state_name': msg.sub_state_name,
      'current_area': msg.current_area,
      'current_path': msg.current_path,
      'current_path_index': msg.current_path_index,
      'is_charging': msg.is_charging,
    },
  })

def on_mower_status(msg):
  if not check_rate_limit('status2'): return

  write_api.write(bucket=BUCKET, record={
    'measurement': 'status2',
    'fields': {
      'mower_status': msg.mower_status,
      'gps_power': msg.gps_power,
      'esc_power': msg.esc_power,
      'rain_detected': msg.rain_detected,
      'emergency': msg.emergency,
      'v_charge': msg.v_charge,
      'v_battery': msg.v_battery,
      'charge_current': msg.charge_current,
    },
  })

  for esc in ('mow', 'left', 'right'):
    status = getattr(msg, esc + '_esc_status')
    write_api.write(bucket=BUCKET, record={
      'measurement': 'esc',
      'tags': {'esc': esc},
      'fields': {
        'status': status.status,
        'current': status.current,
        'tacho': status.tacho,
        'temperature_motor': status.temperature_motor,
        'temperature_pcb': status.temperature_pcb,
      },
    })

def on_xbot_driver_gps_xb_pose(msg):
  if not check_rate_limit('gnss'): return
  position = msg.pose.pose.position
  (lat, lon) = utm.to_latlon(ORIGIN_X + position.x, ORIGIN_Y + position.y, ORIGIN_ZONE_NUMBER, ORIGIN_ZONE_LETTER)
  write_api.write(bucket=BUCKET, record={
    'measurement': 'gnss',
    'fields': {
      'flags': msg.flags,
      'position_accuracy': msg.position_accuracy,
      'lat': lat,
      'lon': lon,
      'height': ORIGIN_Z + position.z,
    }
  })

def wifi(interface):
  while True:
    try:
      wifi = get_iwconfig(interface)
      write_api.write(bucket=BUCKET, record={
        'measurement': 'wifi',
        'fields': {
          'access_point': wifi['Access Point'].decode('utf-8'),
          'rssi': wifi['stats']['level'] - 256,
          'quality': wifi['stats']['quality'],
          'level': wifi['stats']['level'],
        },
      })
    except Exception as e:
      rospy.logerr(e)
    time.sleep(MIN_INTERVAL)

if __name__ == '__main__':
  rospy.init_node('xbot_influxdb')
  rospy.loginfo("xbot_influxdb started!")

  MIN_INTERVAL = rospy.get_param('min_interval', 2)
  BUCKET = rospy.get_param('bucket', 'openmower')

  influx = InfluxDBClient.from_config_file('/config/influxdb.ini')
  write_api = influx.write_api()

  get_origin()
  rospy.Subscriber('/mower/status', Status, on_mower_status)
  rospy.Subscriber('/mower_logic/current_state', HighLevelStatus, on_mower_logic_current_state)
  # /mower/wheel_ticks
  rospy.Subscriber('/xbot_driver_gps/xb_pose', AbsolutePose, on_xbot_driver_gps_xb_pose)
  Thread(target=wifi, args=(rospy.get_param('wifi_interface', 'wlan0'),), daemon=True).start()

  try:
    rospy.spin()
  except KeyboardInterrupt:
    pass
