import os
from flask import request, url_for, render_template
from flask_restful import Resource, abort


class LogFile(object):

    def __init__(self, text):
        files = os.listdir('{}/logs'.format(os.getcwd()))
        print os.getcwd()
        self.id = max(map(lambda x: int(x.split('.')[0]), files)) + 1
        fh = open('./logs/{}.log'.format(self.id), 'w+')
        fh.write(text)
        fh.close()
        self.text = text


def viewer(id):
    try:
        with open('{}/logs/{}.log'.format(os.getcwd(), id), 'r') as fh:
            contents = fh.read()
        print contents
        return render_template('viewer.html', filename="{}.log".format(id), contents=contents)
    except IOError:
        abort(404)

class Log(Resource):
    def get(self, id):
        try:
            with open('logs/{}.log'.format(id)) as fh:
                log = fh.read()
        except IOError as e:
            return {"error": "{}".format(e)}
        if log:
            return {"text": log}

    def post(self):
        print request.data
        print request.json
        if 'text' in request.json:
            logfile = LogFile(request.json['text'])
            print "Created logfile {}".format(logfile.id)
            return {"url": url_for('viewer', id=logfile.id, _external=True)}
