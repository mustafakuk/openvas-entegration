import flask
import json
import time
import xml.etree.ElementTree as ET
import xmltodict
import threading
import configparser
import requests
from flask import request, jsonify, Response
from gvm.connections import UnixSocketConnection
from gvm.errors import GvmError
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform


app = flask.Flask(__name__)

@app.route('/openscan', methods = ['POST'])
def openscan():
      try:
          currentdate = round(time.time() * 1000)
          config = configparser.ConfigParser()
          config.read('openvas.conf')
          data = json.loads(request.data)["data"]
          connection = UnixSocketConnection(path=config['INFO']['path'])
          transform = EtreeCheckCommandTransform()
          with Gmp(connection=connection, transform=transform) as gmp:
              gmp.authenticate(config['INFO']["username"],config['INFO']["pass"])
              try:
                  target = gmp.create_target('enteg' + data[0]["targetIP"] + "-" + str(currentdate), asset_hosts_filter=str(data[0]["targetIP"]), port_list_id = config['INFO']['portlistid'], port_range=None)
              except GvmError as e:
                  gmp.create_host(data[0]["targetIP"])
                  target = gmp.create_target('enteg' + data[0]["targetIP"] + "-" + str(currentdate), asset_hosts_filter=str(data[0]["targetIP"]), port_list_id = config['INFO']['portlistid'], port_range=None)
              task = gmp.create_task(name='enteg' + data[0]["targetIP"] + "-"  + str(currentdate), config_id= config['INFO']['configid'], target_id=target.get('id'), scanner_id = config['INFO']['scannerid'])
              start = gmp.start_task(task_id=task.get('id'))
              return Response(json.dumps({"agentId":data[0]["agentId"],"reportId": start[0].text, "taskId": task.get('id') }, ensure_ascii=False), mimetype='text/json')
      except GvmError as e:
          return Response(json.dumps({"error": str(e) }, ensure_ascii=False), mimetype='text/json')

@app.route('/reportscan', methods = ['POST'])
def reportscan():
      try:
          config = configparser.ConfigParser()
          config.read('openvas.conf')
          data = json.loads(request.data)["data"]
          connection = UnixSocketConnection(path=config['INFO']["path"])
          transform = EtreeCheckCommandTransform()
          with Gmp(connection=connection, transform=transform) as gmp:
              gmp.authenticate(config['INFO']["username"],config['INFO']["pass"])
              report = gmp.get_report(report_id = data[0]["reportId"])
              report_content_str = ET.tostring(report, encoding='unicode')
              report_result_dict = xmltodict.parse(report_content_str)
              report_json_result = json.loads(json.dumps(report_result_dict, ensure_ascii=False))
          # results = report_json_result['get_reports_response']['report']['report']['results']['result']
              task_result = gmp.get_task(task_id= data[0]["taskId"])
              task_result_str = ET.tostring(task_result, encoding='unicode')
              task_result_dict = xmltodict.parse(task_result_str)
              json_result = json.loads(json.dumps(task_result_dict, ensure_ascii=False))
              status = json_result['get_tasks_response']['task']['status']
              progres = json_result['get_tasks_response']['task']['progress']
              return Response(json.dumps({"taskId":data[0]["taskId"], "status": status , "progress":progres, "results":report_json_result},ensure_ascii=False) ,mimetype='text/json')
      except GvmError as e:
          return Response(json.dumps({"error": str(e) }, ensure_ascii=False), mimetype='text/json')

config = configparser.ConfigParser()
config.read('openvas.conf')
app.run(port=config['INFO']['port'], host=config['INFO']['host'])
