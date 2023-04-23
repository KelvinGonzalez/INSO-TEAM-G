import time
import json
import os
import calendar
import datetime
import pytz
from flask_login import UserMixin
import hashlib

# Database equivalent
#users = {}
#events = {}

def save(name, dict):
    dict = {int(k) : v.to_dict() for k, v in dict.items()}
    file = open(name, "w")
    json.dump(dict, file, indent=2)
    file.close()

def load(name):
    dict = {}
    if os.path.exists(name):
        with open(name, "r") as file:
            dict = json.load(file)
        file.close()
    return {int(k) : (Event.from_dict(v) if name == "events" else User.from_dict(v)) for k, v in dict.items()}

# Backend
class Notification:
    def __init__(self, event_id, update_index):
        self.event_id = event_id
        self.update_index = update_index

    def get_event_update(self):
        events = load("events")
        if not events.get(self.event_id) or self.update_index < 0 or self.update_index >= len(events[self.event_id].updates):
            return None
        return events[self.event_id].updates[self.update_index]
    
    def get_event(self):
        events = load("events")
        return events.get(self.event_id)
    
    def to_dict(self):
        return {"event_id": self.event_id, "update_index": self.update_index}
    
    @staticmethod
    def from_dict(dict):
        return Notification(dict["event_id"], dict["update_index"])

class CalendarDay:
    def __init__(self, month_number, year, day_number, week_day, event_ids):
        self.month_number = month_number
        self.year = year
        self.day_number = day_number
        self.week_day = week_day
        self.event_ids = event_ids

    def __str__(self):
        events = load("events")
        return f"{self.week_day}, {self.day_number}" + (": " + ", ".join([events[id].title for id in self.event_ids]) if len(self.event_ids) > 0 else "")
    
    def get_events_in_time_interval(self, start_min, end_min):
        start_epoch = (datetime.datetime(self.year, self.month_number, self.day_number, start_min // 60, start_min % 60) + datetime.timedelta(hours=4)).replace(tzinfo=datetime.timezone.utc).timestamp()
        end_epoch = (datetime.datetime(self.year, self.month_number, self.day_number, (end_min-1) // 60, end_min % 60 + 59) + datetime.timedelta(hours=4)).replace(tzinfo=datetime.timezone.utc).timestamp()
        events = load("events")
        result = []
        for event_id in self.event_ids:
            if start_epoch <= events.get(event_id).time <= end_epoch:
                result.append(events.get(event_id))
        return result

class Calendar:
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, event_ids=None, notifications=None):
        if not event_ids:
            event_ids = []
        if not notifications:
            notifications = []
        self.event_ids = event_ids
        self.notifications = notifications

    def to_dict(self):
        return {"event_ids": self.event_ids, "notifications": [x.to_dict() for x in self.notifications]}
    
    @staticmethod
    def from_dict(dict):
        return Calendar(dict["event_ids"], [Notification.from_dict(x) for x in dict["notifications"]])

    def sorting_key(self, e):
        events = load("events")
        return events[e].time

    def get_events_in_day(self, month, day, year):
        events = load("events")
        result = []
        for event_id in self.event_ids:
            event_date = datetime.date.fromtimestamp(events[event_id].time)
            if event_date.month == month and event_date.day == day and event_date.year == year:
                result.append(event_id)
        return sorted(result, key=self.sorting_key)

    def generate_month(self, month, year):
        if month == None and year == None:
            #raise Exception("Both arguments missing")
            return None
        if month == None or year == None:
            #raise Exception("1 missing argument")
            return None
        if str(month).isdigit() == False or month > 12 or month < 1:
            #raise Exception("Invalid month")
            return None
        if str(year).isdigit() == False or (len(str(year)) < 4) == True:
            #raise Exception("Invalid year")
            return None
                            
        month_matrix = calendar.Calendar().monthdayscalendar(year, month)
        for i in range(len(month_matrix)):
            for j in range(len(month_matrix[0])):
                if month_matrix[i][j] == 0:
                    month_matrix[i][j] = None
                else:
                    month_matrix[i][j] = CalendarDay(month, year, month_matrix[i][j], self.week_days[j%7], self.get_events_in_day(month, month_matrix[i][j], year))
        return month_matrix
    
    def get_day_from_month(self, month, day_number):
        for week in month:
            for day in week:
                if day and day.day_number == day_number:
                    return day
        return None

class User(UserMixin):
    def __init__(self, id, username, email, password, calendar=None, created_events=None, moderator=False):
        if not calendar:
            calendar = Calendar()
        if not created_events:
            created_events = []
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.calendar = calendar
        self.created_events = created_events
        self.moderator = moderator

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email, "password": self.password, "calendar": self.calendar.to_dict(), "created_events": self.created_events, "moderator": self.moderator}
    
    @staticmethod
    def from_dict(dict):
        return User(dict["id"], dict["username"], dict["email"], dict["password"], Calendar.from_dict(dict["calendar"]), dict["created_events"], dict["moderator"])

    def create_event(self, title, body, time_param, location, contact_info, price_fee):
        events = load("events")
        users = load("users")
        if not title or not body or not time_param or not location or not contact_info or not price_fee and price_fee != 0:
            return None
        # Add to DB
        id = list(events.keys())[-1] + 1 if len(events) > 0 else 0
        events[id] = Event(id, title, body, time_param, location, contact_info, price_fee, time_stamp=time.time(), host_id=self.id)
        self.created_events.append(id)
        users[self.id] = self
        save("events", events)
        save("users", users)
        return events[id]

    def edit_event(self, event_id, title=None, body=None, time=None, location=None, contact_info=None, price_fee=None):
        events = load("events")
        if not events.get(event_id) or (events[event_id].host_id != self.id and not self.moderator):
            return False
        
        if title:
            events[event_id].title = title
        if body:
            events[event_id].body = body
        if time:
            events[event_id].time = time
        if location:
            events[event_id].location = location
        if contact_info:
            events[event_id].contact_info = contact_info
        if price_fee or price_fee == 0:
            events[event_id].price_fee = price_fee

        save("events", events)
        return True

    def delete_event(self, event_id):
        events = load("events")
        users = load("users")
        if not events.get(event_id) or (events[event_id].host_id != self.id and not self.moderator):
            return False
        for user_id in events[event_id].subscribed_users:
            users[user_id].calendar.event_ids.remove(event_id)
        save("users", users)
        while len(events[event_id].updates) > 0:
            events[event_id].delete_update(0)
            events = load("events")
        users = load("users")
        self.created_events.remove(event_id)
        events.pop(event_id)
        users[self.id] = self
        save("events", events)
        save("users", users)
        return True

    def rate_event(self, event_id, rating):
        events = load("events")
        if not events.get(event_id) or self.id == events[event_id].host_id or self.id in [x[0] for x in events[event_id].ratings]:
            return False
        events[event_id].ratings.append((self.id, int(min(max(rating, 1), 5))))
        save("events", events)
        return True
    
    def add_event(self, event_id):
        events = load("events")
        users = load("users")
        if not events.get(event_id) or event_id in self.calendar.event_ids or event_id in self.created_events:
            return False
        self.calendar.event_ids.append(event_id)
        events[event_id].subscribed_users.append(self.id)
        users[self.id] = self
        save("events", events)
        save("users", users)
        return True

    def remove_event(self, event_id):
        events = load("events")
        users = load("users")
        if not events.get(event_id) and event_id not in self.calendar.event_ids:
            return False
        i = 0
        while i < len(self.calendar.notifications):
            if self.calendar.notifications[i].event_id == event_id:
                self.delete_notification(i)
                continue
            i += 1
        events[event_id].subscribed_users.remove(self.id)
        self.calendar.event_ids.remove(event_id)
        users[self.id] = self
        save("events", events)
        save("users", users)
        return True

    def delete_notification(self, notification_index):
        users = load("users")
        if notification_index < 0 or notification_index >= len(self.calendar.notifications):
            return False
        self.calendar.notifications.pop(notification_index)
        users[self.id] = self
        save("users", users)
        return True

class EventUpdate:
    def __init__(self, event_id, title, body, time_stamp=-1):
        if time_stamp == -1:
            time_stamp = time.time()
        self.event_id = event_id
        self.title = title
        self.body = body
        self.time_stamp = time_stamp

    def __eq__(self, other):
        return self.event_id == other.event_id and self.title == other.title and self.body == other.body and self.time_stamp == other.time_stamp

    def to_dict(self):
        return {"event_id": self.event_id, "title": self.title, "body": self.body, "time_stamp": self.time_stamp}
    
    @staticmethod
    def from_dict(dict):
        return EventUpdate(dict["event_id"], dict["title"], dict["body"], dict["time_stamp"])

    def send_notification(self):
        events = load("events")
        users = load("users")
        if not events.get(self.event_id):
            return False
        print(events[self.event_id].updates)
        for user_id in events[self.event_id].subscribed_users:
            users[user_id].calendar.notifications.append(Notification(self.event_id, events[self.event_id].updates.index(self)))
        save("users", users)
        return True

class Event:
    def __init__(self, id, title, body, time, location, contact_info, price_fee, ratings=None, time_stamp=-1, host_id=-1, subscribed_users=None, updates=None):
        if not ratings:
            ratings = []
        if time_stamp == -1:
            time_stamp = time.time()
        if not subscribed_users:
            subscribed_users = []
        if not updates:
            updates = []
        self.id = id
        self.title = title
        self.body = body
        self.time = time
        self.location = location
        self.contact_info = contact_info
        self.price_fee = price_fee
        self.ratings = ratings
        self.time_stamp = time_stamp
        self.host_id = host_id
        self.subscribed_users = subscribed_users
        self.updates = updates

    def to_dict(self):
        return {"id": self.id, "title": self.title, "body": self.body, "time": self.time, "location": self.location, "contact_info": self.contact_info, "price_fee": self.price_fee, "ratings": self.ratings, "time_stamp": self.time_stamp, "host_id": self.host_id, "subscribed_users": self.subscribed_users, "updates": [x.to_dict() for x in self.updates]}
    
    @staticmethod
    def from_dict(dict):
        return Event(dict["id"], dict["title"], dict["body"], dict["time"], dict["location"], dict["contact_info"], dict["price_fee"], dict["ratings"], dict["time_stamp"], dict["host_id"], dict["subscribed_users"], [EventUpdate.from_dict(x) for x in dict["updates"]])

    def create_update(self, title, body):
        events = load("events")
        if not title or not body:
            return None
        update = EventUpdate(self.id, title, body, time_stamp=time.time())
        self.updates.append(update)
        events[self.id] = self
        save("events", events)
        update.send_notification()
        return update

    def edit_update(self, update_index, title=None, body=None):
        events = load("events")
        if update_index < 0 or update_index >= len(self.updates):
            return False
        if title:
            self.updates[update_index].title = title
        if body:
            self.updates[update_index].body = body
        events[self.id] = self
        save("events", events)
        return True

    def delete_update(self, update_index):
        users = load("users")
        events = load("events")
        if update_index < 0 or update_index >= len(self.updates):
            return False
        for user_id in self.subscribed_users:
            for i, notification in enumerate(list(users[user_id].calendar.notifications)):
                if notification.event_id == self.id and notification.update_index == update_index:
                    users[user_id].calendar.notifications.pop(i)
                    break
            for notification in users[user_id].calendar.notifications:
                if notification.event_id == self.id and notification.update_index > update_index:
                    notification.update_index -= 1
        self.updates.pop(update_index)
        events[self.id] = self
        save("events", events)
        save("users", users)
        return True

    def generate_shareable_link(self):
        pass

    def get_rating(self):
        if len(self.ratings) == 0:
            return 5.0
        return sum([x[1] for x in self.ratings]) / len(self.ratings)

def sign_up(username, email, password, password_confirm):
    users = load("users")
    if not username or not email or not password or not password_confirm:
        return None
    if password != password_confirm:
        return None
    for user in users.values():
        if user.email == email:
            return None
        
    # Add to DB
    id = list(users.keys())[-1] + 1 if len(users) > 0 else 0
    users[id] = User(id, username, email, hashlib.md5(password.encode()).hexdigest())
    save("users", users)
    return users[id]

def login(email, password):
    users = load("users")
    for user in users.values():
        if user.email == email and user.password == hashlib.md5(password.encode()).hexdigest():
            return user
    return None

def key_popularity(e):
    x = len(e.subscribed_users)
    return 1/x if x != 0 else 2

def key_recently_updated(e):
    if len(e.updates) == 0:
        return 1/e.time_stamp
    return 1/e.updates[-1].time_stamp

def key_event_date(e):
    return e.time

def search_event(query, parameters):
    events = load("events")
    if not query or query.strip() == "":
        result = list(events.values())
    else:
        query = query.split(" ")
        result = []
        for event in events.values():
            valid = True
            for p in query:
                if p.lower() not in event.title.lower() and p.lower() not in event.body.lower():
                    valid = False
                    break
            if valid:
                result.append(event)

    min_price = -float("inf")
    max_price = float("inf")
    if parameters.get("min-price") or parameters.get("min-price") == 0:
        min_price = parameters.get("min-price")
    if parameters.get("max-price") or parameters.get("max-price") == 0:
        max_price = parameters.get("max-price")
    temp = list(result)
    result = []
    for event in temp:
        if min_price <= event.price_fee <= max_price:
            result.append(event)
    
    min_time = -float("inf")
    max_time = float("inf")
    if parameters.get("min-time") or parameters.get("min-time") == 0:
        min_time = parameters.get("min-time")
    if parameters.get("max-time") or parameters.get("max-time") == 0:
        max_time = parameters.get("max-time")
    temp = list(result)
    result = []
    for event in temp:
        if min_time <= event.time <= max_time:
            result.append(event)

    min_rating = -float("inf")
    max_rating = float("inf")
    if parameters.get("min-rating") or parameters.get("min-rating") == 0:
        min_rating = parameters.get("min-rating")
    if parameters.get("max-rating") or parameters.get("max-rating") == 0:
        max_rating = parameters.get("max-rating")
    temp = list(result)
    result = []
    for event in temp:
        if min_rating <= event.get_rating() <= max_rating:
            result.append(event)

    if parameters.get("host"):
        users = load("users")
        temp = list(result)
        result = []
        for event in temp:
            if users[event.host_id].username == parameters.get("host"):
                result.append(event)

    if parameters and (parameters.get("sort") or parameters.get("sort") == 0):
        return sorted(result, key=[key_popularity, key_recently_updated, key_event_date][parameters["sort"]])
    return result

def search_user(query):
    pass

def edit_user(user_id, username=None, email=None, password=None, moderator=None):
    users = load("users")
    if not users.get(user_id):
        return False

    if username:
        users[user_id].username = username
    if email:
        users[user_id].email = email
    if password:
        users[user_id].password = password
    if moderator:
        users[user_id].moderator = moderator
    
    save("users", users)
    return True

def delete_user(user_id):
    events = load("events")
    users = load("users")
    if not users.get(user_id):
        return False
    for event_id in users[user_id].calendar.event_ids:
        events[event_id].subscribed_users.remove(user_id)
    save("users", users)
    for event_id in users[user_id].created_events:
        users[user_id].delete_event(event_id)
        events = load("events")
    users = load("users")
    users.pop(user_id)
    save("events", events)
    save("users", users)
    return True

def generate_recommendations(user_id):
    pass

def datetime_to_epoch(datetime_string):
    return int((datetime.datetime.strptime(datetime_string, '%b %d, %Y, %I:%M%p') + datetime.timedelta(hours=4)).replace(tzinfo=datetime.timezone.utc).timestamp())

def datetime_to_epoch_html(datetime_string):
    datetime_string = datetime_string.split("T")
    date = datetime_string[0].split("-")
    time = datetime_string[1].split(":")
    return int((datetime.datetime(int(date[0]), int(date[1]), int(date[2]), int(time[0]), int(time[1])) + datetime.timedelta(hours=4)).replace(tzinfo=datetime.timezone.utc).timestamp())

def epoch_to_datetime(epoch):
    date_time = datetime.datetime.utcfromtimestamp(epoch) - datetime.timedelta(hours=4) # AST Timezone
    return date_time.strftime('%b %d, %Y, %I:%M%p')

def epoch_to_datetime_html(epoch):
    date_time = datetime.datetime.utcfromtimestamp(epoch) - datetime.timedelta(hours=4)
    return f"{str(date_time.year).zfill(4)}-{str(date_time.month).zfill(2)}-{str(date_time.day).zfill(2)}T{str(date_time.hour).zfill(2)}:{str(date_time.minute).zfill(2)}"

def get_today_month():
    date_time = datetime.datetime.fromtimestamp(time.time())
    return (int(date_time.month), int(date_time.year))

def get_host(event_id):
    events = load("events")
    users = load("users")
    event = events.get(event_id)
    if event:
        return users.get(event.host_id)
    return None

# General app and user specific info
user = None
page = "login"
page_data = {}
alert_queue = []

def goto(page_name, data=None):
    global page, page_data
    if page_name in ["login", "signup"]:
        if user:
            send_alert("Cannot access this page while signed in")
            return
    else:
        if not user:
            send_alert("Cannot access this page while logged out")
            return
    if not data and page_name in ["user", "event", "event_update", "create_event_update", "calendar", "schedule", "edit_user"]:
        send_alert("Cannot access this page with \"goto\"")
        return
    if page_name != page:
        page = page_name
        page_data.clear()
        if data:
            page_data.update(data)

# HTML + Jinja equivalent
def show_page():
    global user, page, page_data
    events = load("events")
    page_format = ""
    if page == "login":
        page_format = f"Login\nEmail: {page_data.get('email')}\nPassword: {'*'*len(page_data['password']) if page_data.get('password') else None}\nEnter 'submit' to login"
    elif page == "signup":
        page_format = f"Sign Up\nUsername: {page_data.get('username')}\nEmail: {page_data.get('email')}\nPassword: {'*'*len(page_data['password']) if page_data.get('password') else None}\nConfirm: {'*'*len(page_data['confirm']) if page_data.get('confirm') else None}\nEnter 'submit' to sign up"
    elif page == "home":
        page_format = f"Welcome {user.username}!\nBrowse pages: Events, Calendar, Notifications, Profile"
    elif page == "create_event":
        page_format = f"Create Event\nTitle: {page_data.get('title')}\nBody: {page_data.get('body')}\nDate and Time: {epoch_to_datetime(page_data.get('time')) if page_data.get('time') else None}\nLocation: {page_data.get('location')}\nContact Info: {page_data.get('contact')}\nPrice Fee: {str(page_data.get('price'))}\nEnter 'submit' to create event"
    elif page == "events":
        formatted_events = "Events\n" + "\n".join([f'{i}: {event.title}' for i, event in enumerate(events.values())])
        page_format = formatted_events
    elif page == "calendar":
        formatted_days = "\n".join(["\n".join([str(day) for day in week if day]) for week in page_data.get('month')])
        page_format = f"{user.calendar.month_names[page_data.get('month_number')-1]}, {str(page_data.get('year'))}:\n\n" + formatted_days
    elif page == "schedule":
        page_format = f"{user.calendar.month_names[page_data.get('month_number')-1]} {page_data.get('calendar_day').day_number}, {str(page_data.get('year'))}, {page_data.get('calendar_day').week_day}:\n\n" + "\n".join([f"{events[id].title}: {epoch_to_datetime(events[id].time)}" for id in page_data.get('calendar_day').event_ids])
    elif page == "event":
        temp_event = page_data.get('event')
        if temp_event:
            formatted_updates = "Updates:\n" + "\n".join([f"{i}: {update.title}" for i, update in enumerate(temp_event.updates)])
            page_format = f"{temp_event.title}\n\n{temp_event.body}\n\nDate and Time: {epoch_to_datetime(temp_event.time)}\nLocation: {temp_event.location}\nContact Info: {temp_event.contact_info}\nPrice Fee: ${str(temp_event.price_fee)}\nRating: {str(temp_event.get_rating())}\nSubscribed Users: {', '.join([str(x) for x in temp_event.subscribed_users])}\n\n" + formatted_updates
    elif page == "create_event_update":
        temp_event = page_data.get('event')
        if temp_event:
            page_format = f"Create Event Update\nTitle: {page_data.get('title')}\nBody: {page_data.get('body')}\nEnter 'submit' to create update"
    elif page == "event_update":
        temp_update = page_data.get('update')
        if temp_update:
            page_format = f"{events.get(temp_update.event_id).title} - {temp_update.title}\n\n{temp_update.body}"
    elif page == "user":
        temp_user = page_data.get('user')
        if not temp_user:
            temp_user = user
        if temp_user:
            formatted_created_events = "Created Events:\n" + "\n".join([f'{i}: {events[id].title}' for i, id in enumerate(temp_user.created_events)])
            formatted_subscribed_events = "Subscribed Events:\n" + "\n".join([f'{i}: {events[id].title}' for i, id in enumerate(temp_user.calendar.event_ids)])
            page_format = f"{temp_user.username}'s Page\nID: {temp_user.id}\n{formatted_created_events}\n{formatted_subscribed_events}"
    elif page == "edit_user":
        temp_user = page_data.get('user')
        if not temp_user:
            temp_user = user
        if temp_user:
            page_format = f"Username: {temp_user.username}\nEmail: {temp_user.email}\nPassword: {temp_user.password}"
    elif page == "notifications":
        if user:
            page_format = "Notifications\n" + "\n".join([f"{i}: {events.get(notification.event_id).title} - {notification.get_event_update().title}" for i, notification in enumerate(user.calendar.notifications)])
    print(page_format)

def send_alert(text):
    alert_queue.append("Alert: " + text)

def resplit(x, n):
    return x[:-1] + x[-1].split(" ", n-len(x)+1)

# Views equivalent
def parse_input(prompt):
    global user, page, page_data
    users = load("users")
    events = load("events")
    prompt = prompt.split(" ", 1)
    if page == "login":
        if prompt[0] == "password":
            page_data["password"] = prompt[1]
        if prompt[0] == "email":
            page_data["email"] = prompt[1]   
        if prompt[0] == "submit":
            user = login(page_data.get("email"), page_data.get("password"))
            if user:
                goto("home")
            else:
                send_alert("Login info is incorrect")
        if prompt[0] == "signup":
            goto("signup")
    elif page == "signup":
        if prompt[0] == "username":
            page_data["username"] = prompt[1]
        if prompt[0] == "email":
            page_data["email"] = prompt[1]
        if prompt[0] == "password":
            page_data["password"] = prompt[1]
        if prompt[0] == "confirm":
            page_data["confirm"] = prompt[1]
        if prompt[0] == "submit":
            user = sign_up(page_data.get("username"), page_data.get("email"), page_data.get("password"), page_data.get("confirm"))
            if user:
                goto("home")
            else:
                send_alert("Could not sign up")
        if prompt[0] == "login":
            goto("login")
    elif page == "home":
        pass
    elif page == "create_event":
        if prompt[0] == "title":
            page_data["title"] = prompt[1]
        if prompt[0] == "body":
            page_data["body"] = prompt[1]
        if prompt[0] == "datetime":
            page_data["time"] = datetime_to_epoch(prompt[1])
        if prompt[0] == "location":
            page_data["location"] = prompt[1]
        if prompt[0] == "contact":
            page_data["contact"] = prompt[1]
        if prompt[0] == "price":
            page_data["price"] = float(prompt[1])
        if prompt[0] == "submit":
            event = user.create_event(page_data.get("title"), page_data.get("body"), page_data.get("time"), page_data.get("location"), page_data.get("contact"), page_data.get("price"))
            if event:
                goto("event", {"event": event})
            else:
                send_alert("Could not create event")
    elif page == "events":
        if prompt[0] == "event":
            goto("event", {"event": events[list(events.keys())[int(prompt[1])]]})
    elif page == "calendar":
        if prompt[0] == "day":
            goto("schedule", {"month": page_data["month"], "month_number": page_data["month_number"], "year": page_data["year"], "calendar_day": user.calendar.get_day_from_month(page_data["month"], int(prompt[1]))})
        if prompt[0] == "next":
            if page_data["month_number"] == 12:
                page_data["month_number"] = 0
                page_data["year"] += 1
            page_data["month_number"] += 1
            page_data["month"] = user.calendar.generate_month(page_data["month_number"], page_data["year"])
        if prompt[0] == "prev":
            if page_data["month_number"] == 1:
                page_data["month_number"] = 13
                page_data["year"] -= 1
            page_data["month_number"] -= 1
            page_data["month"] = user.calendar.generate_month(page_data["month_number"], page_data["year"])
    elif page == "schedule":
        if prompt[0] == "month":
            goto("calendar", {"month": page_data["month"], "month_number": page_data["month_number"], "year": page_data["year"]})
    elif page == "event":
        if prompt[0] == "subscribe":
            if user.add_event(page_data["event"].id):
                send_alert("Event has been added to your calendar")
            else:
                send_alert("Event could not be added to your calendar")
        if prompt[0] == "unsubscribe":
            if user.remove_event(page_data["event"].id):
                send_alert("Event has been removed from your calendar")
            else:
                send_alert("Event could not be removed from your calendar")
        if prompt[0] == "edit":
            temp_prompt = resplit(prompt, 2)
            if temp_prompt[1] == "title":
                if user.edit_event(page_data["event"].id, title=temp_prompt[2]):
                    pass
                else:
                    send_alert("Event title could not be modified")
            if temp_prompt[1] == "body":
                if user.edit_event(page_data["event"].id, body=temp_prompt[2]):
                    pass
                else:
                    send_alert("Event body could not be modified")
            if temp_prompt[1] == "datetime":
                if user.edit_event(page_data["event"].id, time=datetime_to_epoch(prompt[1])):
                    pass
                else:
                    send_alert("Event time could not be modified")
            if temp_prompt[1] == "location":
                if user.edit_event(page_data["event"].id, location=temp_prompt[2]):
                    pass
                else:
                    send_alert("Event location could not be modified")
            if temp_prompt[1] == "contact":
                if user.edit_event(page_data["event"].id, contact_info=temp_prompt[2]):
                    pass
                else:
                    send_alert("Event contact info could not be modified")
            if temp_prompt[1] == "price":
                if user.edit_event(page_data["event"].id, price_fee=float(temp_prompt[2])):
                    pass
                else:
                    send_alert("Event price fee could not be modified")
        if prompt[0] == "delete":
            if user.delete_event(page_data["event"].id):
                goto("events")
                send_alert("Event successfully deleted")
            else:
                send_alert("Event could not be deleted")
        if prompt[0] == "rate":
            if user.rate_event(page_data["event"].id, int(prompt[1])):
                send_alert("Event successfully rated")
            else:
                send_alert("Event could not be rated")
        if prompt[0] == "update":
            goto("event_update", {"update": page_data["event"].updates[int(prompt[1])]})
        if prompt[0] == "create_update":
            if user.id == page_data["event"].host_id or user.moderator:
                goto("create_event_update", {"event": page_data["event"]})
            else:
                send_alert("User cannot create an update for this event")
    elif page == "create_event_update":
        if prompt[0] == "title":
            page_data["title"] = prompt[1]
        if prompt[0] == "body":
            page_data["body"] = prompt[1]
        if prompt[0] == "submit":
            update = page_data["event"].create_update(page_data.get("title"), page_data.get("body"))
            if update:
                goto("event_update", {"update": update})
            else:
                send_alert("Could not create event update")
    elif page == "event_update":
        temp_event = events[page_data["update"].event_id]
        if prompt[0] == "event":
            goto("event", {"event": temp_event})
        if prompt[0] == "edit":
            if user.id == temp_event.host_id or user.moderator:
                temp_prompt = resplit(prompt, 2)
                if temp_prompt[1] == "title":
                    if temp_event.edit_update(page_data["update"].update_index, title=temp_prompt[2]):
                        pass
                    else:
                        send_alert("Update title could not be modified")
                if temp_prompt[1] == "body":
                    if temp_event.edit_update(page_data["update"].update_index, body=temp_prompt[2]):
                        pass
                    else:
                        send_alert("Update body could not be modified")
            else:
                send_alert("User cannot edit this event update")
        if prompt[0] == "delete":
            if user.id == temp_event.host_id or user.moderator:
                if temp_event.delete_update(events[page_data["update"].event_id].updates.index(page_data["update"])):
                    send_alert("Update successfully deleted")
                    goto("event", {"event": temp_event})
                else:
                    send_alert("Update could not be deleted")
            else:
                send_alert("User cannot delete this event update")
    elif page == "user":
        if prompt[0] == "c_event":
            goto("event", {"event": events[page_data["user"].created_events[int(prompt[1])]]})
        if prompt[0] == "s_event":
            goto("event", {"event": events[page_data["user"].calendar.event_ids[int(prompt[1])]]})
        if prompt[0] == "edit":
            if page_data["user"] == user or user.moderator:
                goto("edit_user", {"user": page_data["user"]})
            else:
                send_alert("Cannot edit this user")
    elif page == "edit_user":
        if prompt[0] == "username":
            if edit_user(page_data["user"].id, username=prompt[1]):
                pass
            else:
                send_alert("Username could not be modified")
        if prompt[0] == "email":
            send_alert("Email cannot be modified")
        if prompt[0] == "password":
            if edit_user(page_data["user"].id, password=prompt[1]):
                pass
            else:
                send_alert("Password could not be modified")
        if prompt[0] == "user":
            goto("user", {"user": page_data["user"]})
    elif page == "notifications":
        if prompt[0] == "delete":
            if user.delete_notification(int(prompt[1])):
                send_alert("Notification successfully deleted")
            else:
                send_alert("Notification could not be deleted")
        if prompt[0] == "update":
            goto("event_update", {"update": user.calendar.notifications[int(prompt[1])].get_event_update()})
    
    if prompt[0] == "exit":
        page_data["exit"] = True
    elif prompt[0] == "logout":
        email, password = user.email, user.password
        user = None
        goto("login", {'email': email, 'password': password})
    elif prompt[0] == "create_event":
        goto("create_event")
    elif prompt[0] == "events":
        goto("events")
    elif prompt[0] == "calendar":
        month = get_today_month()
        goto("calendar", {"month": user.calendar.generate_month(month[0], month[1]), "month_number": month[0], "year": month[1]})
    elif prompt[0] == "profile":
        goto("user", {'user': user})
    elif prompt[0] == "notifications":
        goto("notifications")
    elif prompt[0] == "home":
        goto("home")

# App run equivalent
def run():
    while True:
        try:
            show_page()
            parse_input(input("-"*50 + "\nEnter command: "))
            if page_data.get('exit'):
                break
        except:
            send_alert("Error has occurred")
        os.system('cls')
        for alert in alert_queue:
            print(alert)
            alert_queue.clear()

if __name__ == "__main__":
    run()