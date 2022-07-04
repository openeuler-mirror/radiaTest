from celeryservice.lib.framework.mugen.mugen_executor import MugenExecutor
from celeryservice.lib.framework.mugen.mugen_log_resolver import MugenLogResolver


class Mugen:
    @staticmethod
    def executor():
        return MugenExecutor()

    @staticmethod
    def logresolver():
        return MugenLogResolver()