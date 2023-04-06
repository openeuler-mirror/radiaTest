class ProfileMap(object):
    gitee = lambda oauth_user: {
        "user_id": "gitee_" + str(oauth_user.get("id")),
        "user_login": oauth_user.get("login"),
        "user_name": oauth_user.get("name"),
        "avatar_url": oauth_user.get("avatar_url")
    }
    oneid = lambda oauth_user: {
        "user_id": "oneid_" + str(oauth_user.get("sub")),
        "user_login": oauth_user.get("username"),
        "user_name": oauth_user.get("username"),
        "avatar_url": oauth_user.get("picture")
    }
