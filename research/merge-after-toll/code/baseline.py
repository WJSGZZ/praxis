import sys
from model import main
if __name__ == '__main__':
    sys.argv.extend(['--phase', 'baseline'])
    main()
