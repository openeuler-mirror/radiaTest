from celeryservice.lib.framework.mugen.mugen_executor import MugenExecutor
from celeryservice.lib.framework.mugen.mugen_log_resolver import MugenLogResolver


class Mugen:
    @property
    def executor(self):
        return MugenExecutor()

    @property
    def logresolver(self):
        return MugenLogResolver()