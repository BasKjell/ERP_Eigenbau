# frozen_string_literal: true

module FlowSso
  module ApplicationControllerPatch
    LOGIN_PATTERN = /\A[a-zA-Z0-9_.@-]{1,100}\z/

    def find_current_user
      login = request.headers["X-Flow-Sso-User"].to_s.strip
      if ENV["FLOW_SSO_ENABLED"] == "true" && LOGIN_PATTERN.match?(login)
        user = User.find_by(login: login, status: User::STATUS_ACTIVE)
        return user if user
      end
      super
    end
  end
end
