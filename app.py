from flask import Flask, render_template, request, flash, redirect, url_for
from flask_restful import Resource, Api
from pyosupgrade.upgrade import DeviceUpgrade

app = Flask(__name__)
api = Api(app)


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        # form = UrlAppForm()
        return render_template('create.html',
                               title='4500 Upgrade Utility',
                               logo='/static/img/4500.jpg')
    elif request.method == 'POST':
        payload = request.form
        upgrade = DeviceUpgrade(payload['hostname'],
                          payload['username'],
                          payload['password'],
                          payload['image'])
        print(upgrade)
        upgrade.start()
        flash("Submitted Job", "success")
        return redirect(url_for('home'))


class Upgrade(Resource):

    def post(self):
        if request.json:
            payload = request.json
            upgrade = DeviceUpgrade(payload['host'],
                              payload['username'],
                              payload['password'],
                              payload['image_filename'])
            upgrade.start()
            return {"status":"ok"}
        else:
            return {"status": "no JSON payload detected"}


api.add_resource(Upgrade, '/api/upgrade')


if __name__ == '__main__':
    app.secret_key = 'CHANGEME'
    app.debug = True
    app.run()
