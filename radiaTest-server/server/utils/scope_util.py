class ScopeKey(object):
    gitee = lambda oauth_scope: f"{oauth_scope}".replace(',', "%20")
    oneid = lambda oauth_scope: f"{oauth_scope}".replace(",", "%20") + "&state=random"
