# frozen_string_literal: true

require "json"
require "securerandom"

# Idempotent FLOWWORK demo seed. Redmine stays the source of truth for
# projects, issues, time entries and wiki content; versioned requirements live
# in the platform service and reference these records.

api_key = ENV.fetch("REDMINE_API_KEY", "f6ab4d1c02fe9a7b3e5d8c4f1a6b9e2c7d0f3a5b")
admin_password = ENV.fetch("REDMINE_ADMIN_PASSWORD", "admin-demo-change-me")

Setting.rest_api_enabled = "1"
Setting.default_language = "de"
Setting.login_required = "1"

# A fresh Redmine database contains the schema and administrator account, but
# not the business defaults required by issues (trackers, statuses and
# priorities). Loading them here keeps the one-shot seed self-contained and
# idempotent across clean installations.
if Tracker.none? || IssueStatus.none? || IssuePriority.none?
  Redmine::DefaultData::Loader.load(:de)
end

admin = User.find_by!(login: "admin")
admin.password = admin_password
admin.password_confirmation = admin_password
admin.must_change_passwd = false if admin.respond_to?(:must_change_passwd=)
admin.save!

token = Token.find_or_initialize_by(user: admin, action: "api")
token.value = api_key
token.save!

def ensure_project(identifier, name, description)
  project = Project.find_or_initialize_by(identifier: identifier)
  project.name = name
  project.description = description
  project.is_public = true
  project.enabled_module_names = %w[issue_tracking time_tracking wiki calendar gantt]
  project.trackers = Tracker.all
  project.save!
  project
end

def ensure_wiki_page(project, title, text, admin)
  wiki = project.wiki || Wiki.create!(project: project, start_page: "Projektstart")
  page = WikiPage.find_or_initialize_by(wiki: wiki, title: title)
  page.save! if page.new_record?
  content = page.content || WikiContent.new(page: page)
  content.text = text
  content.author = admin
  content.comments = "FLOWWORK Demo-Seed"
  content.save!
end

def ensure_issue(project, subject, description, admin, due_date, done_ratio = 0)
  issue = Issue.find_or_initialize_by(project: project, subject: subject)
  issue.tracker = project.trackers.first || Tracker.first
  issue.status = IssueStatus.where(is_closed: done_ratio == 100).first || IssueStatus.first
  issue.priority = IssuePriority.default || IssuePriority.first
  issue.author = admin
  issue.assigned_to = admin
  issue.description = description
  issue.due_date = Date.parse(due_date)
  issue.done_ratio = done_ratio
  issue.save!
  issue
end

def ensure_sso_users(projects)
  realm = JSON.parse(File.read("/seed/realm.json"))
  roles = {
    manager: Role.find_by(name: "Manager") || Role.where(builtin: 0).first,
    developer: Role.find_by(name: "Developer") || Role.find_by(name: "Entwickler") || Role.where(builtin: 0).first,
    reporter: Role.find_by(name: "Reporter") || Role.where(builtin: 0).first
  }
  realm.fetch("users").each do |entry|
    login = entry.fetch("username")
    realm_roles = entry.fetch("realmRoles", [])
    user = User.find_or_initialize_by(login: login)
    user.firstname = entry.fetch("firstName", login)
    user.lastname = entry.fetch("lastName", "SSO")
    user.mail = entry.fetch("email")
    user.status = User::STATUS_ACTIVE
    user.language = "de"
    user.admin = realm_roles.include?("platform-admin")
    if user.new_record?
      password = SecureRandom.base64(36)
      user.password = password
      user.password_confirmation = password
    end
    user.must_change_passwd = false if user.respond_to?(:must_change_passwd=)
    user.save!

    member_role = if realm_roles.intersect?(%w[platform-admin work-admin])
                    roles[:manager]
                  elsif realm_roles.include?("requirements-user")
                    roles[:developer]
                  else
                    roles[:reporter]
                  end
    projects.each do |project|
      member = Member.find_or_initialize_by(project: project, user: user)
      member.roles = [member_role]
      member.save!
    end
  end
end

scu = ensure_project(
  "scu-100",
  "SCU-100 Produktentwicklung",
  "Kundenprojekt NordMarine Systems · Kommission KOM-4711"
)
platform = ensure_project(
  "platform-rollout",
  "Open Manufacturing Rollout",
  "Einführung der integrierten Unternehmensplattform"
)

ensure_wiki_page(
  scu,
  "Projektstart",
  "h1. SCU-100 Projektstart\n\n* Kommission: KOM-4711\n* Kunde: NordMarine Systems\n* Requirements: [[SCU-100_Requirements]]\n* Verifikation: [[SCU-100_Verification]]",
  admin
)
ensure_wiki_page(
  scu,
  "SCU-100_Requirements",
  "h1. SCU-100 Requirements\n\nDie versionierten Anforderungen werden in FLOWWORK geführt. Diese Wiki-Seite dokumentiert Entscheidungen, Reviews und offene Punkte.\n\nh2. Verknüpfung\n\n* REQ-SCU-001 → Ticket zur CAN-Kommunikation\n* REQ-SCU-002 → MES-Seriennummern-Rückmeldung\n* REQ-SCU-003 → EMV-Prüfplan",
  admin
)
ensure_wiki_page(
  scu,
  "SCU-100_Verification",
  "h1. Verifikationsstrategie\n\nJede Must-Anforderung benötigt einen Test, Prüfbericht oder dokumentierten Abnahmenachweis.",
  admin
)
ensure_wiki_page(
  platform,
  "Projektstart",
  "h1. Plattform-Rollout\n\nBetrieb, Schnittstellen und Abnahmekriterien der Open Manufacturing Platform.",
  admin
)

ensure_issue(scu, "[REQ-SCU-001] CAN-Kommunikation spezifizieren", "Schnittstellenparameter aus Kundenanforderung ableiten und im Wiki dokumentieren.", admin, "2026-11-08", 50)
ensure_issue(scu, "[REQ-SCU-003] EMV-Prüfplan freigeben", "Review und Freigabe des Verifikationsnachweises.", admin, "2026-11-12", 80)
ensure_issue(scu, "Lieferantendokumente mit Projekt verknüpfen", "DMS-Metadaten und Wiki-Anleitung abstimmen.", admin, "2026-11-15", 0)
ensure_issue(platform, "[REQ-SCU-002] Seriennummern-Rückmeldung im MES", "Pflichtprüfung und API-Mapping ergänzen.", admin, "2026-11-02", 100)

ensure_sso_users([scu, platform])

puts "FLOWWORK Redmine demo is ready (projects=#{Project.count}, issues=#{Issue.count})"
