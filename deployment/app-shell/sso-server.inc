resolver 127.0.0.11 valid=10s ipv6=off;
set $flow_platform_upstream platform-api:8080;

auth_request /_company/sso-auth;
error_page 401 = @flow_sso_login;
auth_request_set $flow_sso_user $upstream_http_x_flow_sso_user;
auth_request_set $flow_sso_email $upstream_http_x_flow_sso_email;
auth_request_set $flow_sso_name $upstream_http_x_flow_sso_name;
auth_request_set $flow_sso_roles $upstream_http_x_flow_sso_roles;
auth_request_set $flow_sso_department $upstream_http_x_flow_sso_department;
auth_request_set $flow_sso_app_role $upstream_http_x_flow_sso_app_role;

location = /_company/sso-auth {
    internal;
    auth_request off;
    proxy_pass http://$flow_platform_upstream/auth/proxy?app_id=$flow_sso_app;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header Cookie $http_cookie;
}

location @flow_sso_login {
    auth_request off;
    return 302 http://localhost:8088/auth/app-login?app_id=$flow_sso_app;
}

location = /_company/health {
    auth_request off;
    access_log off;
    return 204;
}
