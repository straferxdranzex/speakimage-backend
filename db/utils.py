import datetime

def get_curr_timestamp():
    current_datetime = datetime.datetime.now()
    datetime_string = current_datetime.strftime("%Y-%m-%dT%H:%M:%S")
    return datetime_string