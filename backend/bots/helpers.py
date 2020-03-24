import time

def to_human_readable(pandas_datetime):
    t = time.strptime(str(pandas_datetime), '%Y-%m-%d %H:%M:%S')
    human_readable = time.strftime('%B %d %Y', t)

    return human_readable