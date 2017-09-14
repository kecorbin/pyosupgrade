from flower.utils.template import humanize
from ast import literal_eval

def format_task(task):
    print "sanitizing ui output"
    args_tuple = literal_eval(task.args)
    task.args = args_tuple[1]
    task.result = "{} upgrade task details at {}".format(args_tuple[1], args_tuple[0])
    return task