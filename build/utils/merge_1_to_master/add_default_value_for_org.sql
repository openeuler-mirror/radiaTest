-- add default values for new fields in the organization table
update organization
set authority="gitee",
    oauth_login_url="https://gitee.com/oauth/authorize",
    oauth_client_id="xxx",
    oauth_client_secret="xxx",
    oauth_scope="user_info,emails,enterprises,issues",
    oauth_get_token_url="https://gitee.com/oauth/token",
    oauth_get_user_info_url="https://gitee.com/api/v5/user"
where oauth_client_id is NULL;

update organization
set authority="gitee",
    oauth_login_url="https://gitee.com/oauth/authorize",
    oauth_get_token_url="https://gitee.com/oauth/token",
    oauth_get_user_info_url="https://api.gitee.com/enterprises/users"
where oauth_client_id is not NULL;
