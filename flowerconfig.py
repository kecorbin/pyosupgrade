from flower.utils.template import humanize
from ast import literal_eval

def format_task(task):
    print "sanitizing ui output"
    task.args = literal_eval(task.args)[1]
    task.result = humanize(task.result, length=20)
    return task