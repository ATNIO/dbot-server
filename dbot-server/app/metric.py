#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Blueprint, request, Response, abort, make_response, jsonify, json
import requests
import datetime

from dbot_metrics import DBotMetricsCollector

bp = Blueprint('metric', __name__)


class MyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return str(obj, encoding='utf-8');
        return json.JSONEncoder.default(self, obj)


bp.json_encoder = MyJSONEncoder


@bp.route('/query', methods=('GET', 'POST'))
def query_metrics():
    print("query metrics")
    req = request.get_json()
    print(req)
    ts_from = req['range']['from']
    ts_to = req['range']['to']
    print(datetime.datetime.strptime(ts_from, '%Y-%m-%dT%H:%M:%S.%fZ'))
    print(datetime.datetime.strptime(ts_to, '%Y-%m-%dT%H:%M:%S.%fZ'))
    ts_from = float(datetime.datetime.strptime(ts_from, '%Y-%m-%dT%H:%M:%S.%fZ').strftime("%s.%f"))
    ts_to = float(datetime.datetime.strptime(ts_to, '%Y-%m-%dT%H:%M:%S.%fZ').strftime("%s.%f"))
    r = {'range':{'from': ts_from, 'to': ts_to},
         'targets': [{'table': 'apicallinterval', 'type':'all', 'sentence':''}]}
    result = DBotMetricsCollector().Query(r)
    table_rows = []
    results = []
    for target in req['targets']:
        req_type = target.get('type', 'timeserie')
        for r in result:
            content = r.get('content')
            if req_type == 'table':
                for record in content:
                    strtime = datetime.datetime.fromtimestamp(record['time']+28800).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    table_rows.append([strtime, record['tags']['name'], record['tags']['user'], str(record['fields']['latency']),
                                       record['fields']['calltimes'], record['fields']['errors']])
            else:
                target_name = target.get('target')
                if target_name != None:
                    datapoints = []
                    for record in content:
                        timeint = float(record['time'])+28800
                        datapoint = record['fields'][target_name]
                        datapoints.append([datapoint, timeint*1000])
                    results.extend([{"target": target_name, "datapoints": datapoints}])
    if len(table_rows) > 0:
        results.extend([{'type': 'table',
                         'columns': [ {"text":"time","type":"time"},
                                     {"text":"name","type":"string"},
                                     {"text":"user","type":"string"},
                                     {"text":"latency","type":"number"},
                                     {"text":"calltimes", "type":"number"},
                                     {"text":"errors", "type":"number"} ],
                         'rows': table_rows}])
    print("query end...")
    #print(results)
    return jsonify(results)
