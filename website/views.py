from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
import backend
import datetime
import time

views = Blueprint('views', __name__)


@views.route('/', methods=["GET", "POST"])
@login_required
def home():
  events = backend.load("events")
  if request.method == "POST":
    if request.form.get("d_notification"):
      current_user.delete_notification(int(request.form.get("index")))
  return render_template("home.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()), subscribed_events=sorted([events[id] for id in current_user.calendar.event_ids], key=backend.key_event_date), created_events=sorted([events[id] for id in current_user.created_events], key=backend.key_event_date), epoch_to_datetime=backend.epoch_to_datetime, get_host=backend.get_host)

@views.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == "POST":
    user = backend.login(request.form.get("email"), request.form.get("password"))
    if user:
      login_user(user, remember=True)
      return redirect(url_for('views.home'))

  return render_template("login.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()))

@views.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
  if request.method == "POST":
    user = backend.sign_up(request.form.get("username"), request.form.get("email"), request.form.get("password"), request.form.get("confirm-password"))
    if user:
      login_user(user, remember=True)
      return redirect(url_for('views.home'))
    print("Invalid sign up")

  return render_template("signup.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()))

@views.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('views.events'))

@views.route('/event', methods=["GET", "POST"])
def event():
  events = backend.load("events")
  event = None
  if request.method == "GET":
    event = events.get(int(request.args["id"]))
  elif request.method == "POST":
    if request.form.get("c_event"):
      users = backend.load("users")
      event = current_user.create_event(request.form.get("title"), request.form.get("body"), backend.datetime_to_epoch_html(request.form.get("time")) if request.form.get("time") else None, request.form.get("location"), request.form.get("contact"), float(request.form.get("price")))
      if event:
        return redirect(url_for("views.event")+"?id="+str(event.id))
      
    elif request.form.get("e_event"):
      event = events.get(int(request.form["id"]))
      if current_user.edit_event(int(request.form["id"]), request.form.get("title"), request.form.get("body"), backend.datetime_to_epoch_html(request.form.get("time")) if request.form.get("time") else None, request.form.get("location"), request.form.get("contact"), float(request.form.get("price")) if request.form.get("price") else None):
        return redirect(url_for("views.event")+"?id="+str(event.id))
      
    elif request.form.get("d_event"):
      users = backend.load("users")
      event = events.get(int(request.form["id"]))
      if current_user.delete_event(event.id):
        return redirect(url_for("views.home"))
      
    elif request.form.get("r_event"):
      event = events.get(int(request.form["id"]))
      if current_user.rate_event(event.id, int(request.form.get("rating"))):
        return redirect(url_for("views.event")+"?id="+str(event.id))

    elif request.form.get("c_update"):
      event = events.get(int(request.form["id"]))
      if event.create_update(request.form.get("title"), request.form.get("body")):
        return redirect(url_for("views.event")+"?id="+request.form["id"])
      
    elif request.form.get("d_update"):
      event = events.get(int(request.form["id"]))
      if event.delete_update(int(request.form["index"])):
        return redirect(url_for("views.event")+"?id="+request.form["id"])
      
    elif request.form.get("subscribe"):
      event = events.get(int(request.form["id"]))
      users = backend.load("users")
      if request.form.get("subscribe") == "1" and current_user.add_event(event.id) or request.form.get("subscribe") == "0" and current_user.remove_event(event.id):
        return redirect(url_for("views.event")+"?id="+request.form["id"])
      
  if not event:
    return redirect(url_for("views.page_not_found"))
  
  return render_template("event.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()), event=event, updates=event.updates, epoch_to_datetime=backend.epoch_to_datetime, epoch_to_datetime_html=backend.epoch_to_datetime_html, get_host=backend.get_host)

@views.route('/events', methods=["GET"])
def events():
  events = None
  if request.method == "GET":
    query = request.args.get("query")
    parameters = {}
    if request.args.get("sort"):
      parameters["sort"] = int(request.args.get("sort"))
    if request.args.get("min-price"):
      parameters["min-price"] = float(request.args.get("min-price"))
    if request.args.get("max-price"):
      parameters["max-price"] = float(request.args.get("max-price"))
    if request.args.get("min-time"):
      parameters["min-time"] = backend.datetime_to_epoch_html(request.args.get("min-time"))
    if request.args.get("max-time"):
      parameters["max-time"] = backend.datetime_to_epoch_html(request.args.get("max-time"))
    if request.args.get("min-rating"):
      parameters["min-rating"] = int(request.args.get("min-rating"))
    if request.args.get("max-rating"):
      parameters["max-rating"] = int(request.args.get("max-rating"))
    if request.args.get("host"):
      parameters["host"] = request.args.get("host")

    events = backend.search_event(query, parameters)
  return render_template("events.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()), events=events, epoch_to_datetime=backend.epoch_to_datetime, get_host=backend.get_host)

@views.route('/calendar', methods=["GET", "POST"])
@login_required
def calendar():
  month = None
  month_name = None
  if request.method == "GET":
    if request.args.get("setup") == "1":
      now = datetime.datetime.now()
      return redirect(f"{url_for('views.calendar')}?month={now.month}&year={now.year}")
    
    month = current_user.calendar.generate_month(int(request.args.get("month")), int(request.args.get("year")))
    month_name = backend.Calendar.month_names[int(request.args.get("month"))-1]

  if not month:
    return redirect(url_for("views.page_not_found"))

  return render_template("calendar.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()), month=month, month_name=month_name, month_num=request.args.get("month"), year=request.args.get("year"))

@views.route('/schedule', methods=["GET"])
@login_required
def schedule():
  if request.method == "GET":
    day = current_user.calendar.get_day_from_month(current_user.calendar.generate_month(int(request.args.get("month")), int(request.args.get("year"))), int(request.args.get("day")))
    if not day:
      return redirect(url_for("views.page_not_found"))
    
    return render_template("schedule.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()), day=day, months=backend.Calendar.month_names)
  
@views.route('/404', methods=["GET"])
def page_not_found():
  return render_template("404.html", user=current_user, time_now=backend.epoch_to_datetime_html(time.time()))