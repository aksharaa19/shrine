import logging
from pythonjsonlogger import jsonlogger

class ShrineLogger:
    def __init__(self):
        self.logger = logging.getLogger('shrine')
        self.logger.setLevel(logging.INFO)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            rename_fields={
                'asctime': 'timestamp',
                'levelname': 'severity'
            }
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def info(self, message, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def error(self, message, **kwargs):
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message, **kwargs):
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message, **kwargs):
        self.logger.debug(message, extra=kwargs)

logger = ShrineLogger()