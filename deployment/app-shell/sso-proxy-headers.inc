proxy_set_header X-Flow-Sso-User $flow_sso_user;
proxy_set_header X-Flow-Sso-Email $flow_sso_email;
proxy_set_header X-Flow-Sso-Name $flow_sso_name;
proxy_set_header X-Flow-Sso-Roles $flow_sso_roles;
proxy_set_header X-Flow-Sso-Department $flow_sso_department;
proxy_set_header X-Flow-Sso-App-Role $flow_sso_app_role;
proxy_set_header Remote-User $flow_sso_user;
