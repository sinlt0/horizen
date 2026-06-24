import sys
import os
import logging
from datetime import datetime

class Logger:
    @staticmethod
    def setup():
        if not os.path.exists('logs'):
            os.makedirs('logs')

        count = 1
        while os.path.exists(f'logs/logs-{count}.txt'):
            count += 1
        
        log_file = f'logs/logs-{count}.txt'
        master_file = 'logs.txt'
        
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        master_handler = logging.FileHandler(master_file, mode='a')
        master_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(file_handler)
        root.addHandler(master_handler)
        root.addHandler(console_handler)

        class StreamToLogger:
            def __init__(self, logger, log_level):
                self.logger = logger
                self.log_level = log_level
                self.linebuf = ''

            def write(self, buf):
                for line in buf.rstrip().splitlines():
                    self.logger.log(self.log_level, line.rstrip())

            def flush(self):
                pass

        sys.stdout = StreamToLogger(root, logging.INFO)
        sys.stderr = StreamToLogger(root, logging.ERROR)

        print(f"Session logging initialized: {log_file}")
