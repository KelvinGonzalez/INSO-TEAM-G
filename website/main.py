from flask import Flask
from views import views
from flask_login import LoginManager
import backend
from os import path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkeyuwu'

app.register_blueprint(views, url_prefix='/')

login_manager = LoginManager()
login_manager.login_view = 'views.events'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return backend.load("users").get(int(id))

if __name__ == '__main__':
  app.run(debug=True, host="0.0.0.0", port=5000)
