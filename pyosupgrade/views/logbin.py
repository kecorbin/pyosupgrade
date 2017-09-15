import os
from flask import request, url_for, render_template, current_app
from flask_restful import Resource, abort
from bson.objectid import ObjectId
from pymongo import MongoClient

mongo = MongoClient("mongo")



class LogFile(object):

    def __init__(self, text):
        logdir = os.getcwd() + '/logs'
        # make logs directory if one does not exist
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        files = os.listdir('{}/logs'.format(os.getcwd()))
        # only concerned with numbered files e.g 1.log
        files = [f for f in files if f.split('.')[0].isdigit()]
        try:
            self.id = max(map(lambda x: int(x.split('.')[0]), files)) + 1
        # ValueError is raised if no numered files are found (dir is empty)
        except ValueError:
            self.id = 0
        fh = open('./logs/{}.log'.format(self.id), 'w+')
        fh.write(text)
        fh.close()
        self.text = text


class MongoLogFile(object):
    """
    a log file that is stored in mongodb
    :param object:
    :return:
    """
    def __init__(self, id=None, text=None, description=None):

        if not text:
            text="""
            No output was received from the procedure, are you sure you set the status_log_url\n
            """

        self._attributes = dict()
        self._attributes['id'] = id
        self._attributes['description'] = description
        self._attributes['text'] = text

    def as_dict(self):
        # intialize response
        resp = dict()
        #
        # except for a few "reserved" keys
        ignored_keys = ["_id", "password"]

        for key in self._attributes:
            if key not in ignored_keys:
                # we'll also default out any empty parameters
                # ideally the status should always be a bootstrap class
                resp[key] = self._attributes.get(key)
        return resp

    @classmethod
    def from_dict(cls, job_dict):
        # we may not always have these fields
        text = job_dict.get('text', None)
        descr = job_dict.get('description', None)
        id = job_dict.get('id', None)
        # creates new object
        obj = cls(id=id, text=text, description=descr)
        for k, v in job_dict.items():
            obj._attributes[k] = v
        return obj

    @property
    def id(self):
        return self._attributes['id']

    @id.setter
    def id(self, docid):
        self._attributes['id'] = docid

    @property
    def text(self):
        return self._attributes['text']

    @text.setter
    def text(self, text):
        self._attributes['text'] = text

    @property
    def description(self):
        return self._attributes['description']

    @description.setter
    def description(self, text):
        self._attributes['description'] = text


    def create(self):
        object_id = ObjectId()
        data = {"id": str(object_id),
                "text": self.attributes['text'],
                }


def viewer(logid=None, type=None):
    # try:
        if logid:
            print "getting log with id {} ".format(logid)

            job = mongo.db.logbin.find_one({"id": logid}, {"_id": 0})
            print "got log {}".format(job)
            print job
            return render_template('viewer.html',
                                   filename="{}.log".format(logid),
                                   contents=job['text'])

        else:
            print "getting logs"
            cursor = mongo.db.logbin.find()
            logs = [log for log in cursor]
            print logs
            return render_template('log.html',
                                   logs=logs)

    # except Exception:
    #     abort(404)


class Log(Resource):
    def get(self, logid=None):
        if logid:
            print "getting log with id {} ".format(logid)

            job = mongo.db.logbin.find_one({"id": logid}, {"_id": 0})
            print "got log {}".format(job)
            print job
            return job
        else:

            cursor = mongo.db.logbin.find({}, {"_id": 0})
            logs = [doc for doc  in cursor]
            print "staging jobs {}".format(doc)
            return logs



    def post(self):

        if 'text' in request.json:

            object_id = ObjectId()
            # optional fields
            desc = request.json.get('description', None)
            logfile = MongoLogFile(id=str(object_id), description=desc, text=request.json['text'])
            print logfile.description
            mongo.db.logbin.insert(logfile.as_dict())
            print "Created logfile {}".format(logfile.id)
            print "======================================"
            print {"url": url_for('embedded-viewer', logid=logfile.id)}
            return {"url": url_for('embedded-viewer', logid=logfile.id)}
