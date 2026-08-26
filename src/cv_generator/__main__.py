import sys

from cv_generator.cli import main

ret_code = main(sys.argv[1:])
sys.exit(ret_code)
