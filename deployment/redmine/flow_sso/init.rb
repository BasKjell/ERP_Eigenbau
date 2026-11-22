# frozen_string_literal: true

require_relative "lib/flow_sso/application_controller_patch"

Redmine::Plugin.register :flow_sso do
  name "FLOWID trusted proxy SSO"
  author "Open Manufacturing Platform"
  description "Uses the Keycloak identity verified by the private company shell."
  version "1.0.0"
end

attach_flow_sso = proc do
  require_dependency "application_controller"
  unless ApplicationController.ancestors.include?(FlowSso::ApplicationControllerPatch)
    ApplicationController.prepend(FlowSso::ApplicationControllerPatch)
  end
end

Rails.application.config.after_initialize(&attach_flow_sso)
Rails.application.reloader.to_prepare(&attach_flow_sso)
