from mugen_executor import MugenExecutor
from mugen_log_resolver import MugenLogResolver


class Mugen:
    @property
    def executor(self):
        return MugenExecutor()

    @property
    def logresolver(self):
        return MugenLogResolver()