import os
from flask import request, url_for, render_template
from flask_restful import Resource, abort

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


def viewer(id):
    try:
        with open('{}/logs/{}.log'.format(os.getcwd(), id), 'r') as fh:
            contents = fh.read()
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
        if 'text' in request.json:
            logfile = LogFile(request.json['text'])
            print "Created logfile {}".format(logfile.id)
            return {"url": url_for('viewer', id=logfile.id, _external=True)}
