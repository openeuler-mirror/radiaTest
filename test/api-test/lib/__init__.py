import logging


logger = logging.getLogger()
logger.setLevel('DEBUG')
fmt = logging.Formatter('\n%(asctime)s - %(name)s - %(levelname)s: %(message)s')
sh = logging.StreamHandler()
sh.setFormatter(fmt)
sh.setLevel('INFO')
logger.addHandler(sh)