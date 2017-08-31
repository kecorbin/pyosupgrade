from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api
from pyosupgrade.upgrade import DeviceUpgrader, CodeUploader
import yaml
app = Flask(__name__)
api = Api(app)


@app.route('/upgrade', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        # form = UrlAppForm()
        return render_template('upgrade.html',
                               title="Code Upgrade",
                               logo='/static/img/4500.jpg')
    elif request.method == 'POST':
        payload = request.form
        upgrade = DeviceUpgrader(payload['hostname'],
                          payload['username'],
                          payload['password'],
                          payload['image'])
        print(upgrade)
        upgrade.start()
        flash("Submitted Job", "success")
        return redirect(url_for('upgrade'))

@app.route('/staging', methods=['GET', 'POST'])
def staging():

    if request.method == 'GET':
        return render_template('staging.html',
                               title='Code Staging',
                               logo='/static/img/4500.jpg')

    elif request.method == 'POST':
        payload = request.form
        devices = payload['hostnames'].split('\r\n')
        print devices
        for d in devices:
            if len(d) > 5:
                print "Starting code upload thread for {}".format(d)
                t = CodeUploader(d, payload['username'], payload['password'], REGIONS, IMAGES)
                t.start()

        print payload
        flash("Submitted Job", "success")
        return redirect(url_for('staging'))


class Upgrade(Resource):

    def post(self):
        if request.json:
            payload = request.json
            upgrade = DeviceUpgrader(payload['host'],
                              payload['username'],
                              payload['password'],
                              payload['image_filename'])
            upgrade.start()
            return {"status":"ok"}
        else:
            return {"status": "no JSON payload detected"}


api.add_resource(Upgrade, '/api/upgrade')


if __name__ == '__main__':
    with open('regions.yaml', 'r') as regions:
        REGIONS = yaml.safe_load(regions)

    with open('images.yaml', 'r') as images:
        IMAGES = yaml.safe_load(images)


    app.secret_key = 'CHANGEME'
    app.debug = True
    app.run()
