# import json
from flask import json
from datetime import date, datetime
from bson import ObjectId


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        elif isinstance(o, ObjectId):
            return str(o)
        else:
            return json.JSONEncoder.default(self, o)
