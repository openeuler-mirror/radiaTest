from server.apps.framework.adaptor.mugen import Mugen
from server.apps.framework.adaptor.ltp import Ltp


class Resolver:
    mugen = Mugen.suite2cases_resolver
    ltp = Ltp.suite2cases_resolver