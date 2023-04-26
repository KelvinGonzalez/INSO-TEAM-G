from flask import Flask, redirect, url_for, render_template
from views import views
from flask_login import LoginManager, current_user
import backend
from os import path
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkeyuwu'

app.register_blueprint(views, url_prefix='/')

login_manager = LoginManager()

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("views.events")+"?min-time="+backend.epoch_to_datetime_html(time.time()))

login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return backend.load("users").get(int(id))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', user=current_user, time_now=backend.epoch_to_datetime_html(time.time())), 404

if __name__ == '__main__':
  app.run(debug=True, host="0.0.0.0", port=5000)
