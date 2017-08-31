import sys

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def info(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()

def fail(msg):
    sys.stdout.write(bcolors.FAIL + msg + bcolors.ENDC + "\n")

def success(msg):
    sys.stdout.write(bcolors.OKGREEN + msg + bcolors.ENDC + "\n")
