\set ON_ERROR_STOP on

SELECT format(
    'CREATE ROLE grafana_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
    :'reporting_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader')
\gexec

SELECT format('ALTER ROLE grafana_reader PASSWORD %L', :'reporting_password')
\gexec

ALTER ROLE grafana_reader NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE paperless TO grafana_reader;

CREATE SCHEMA IF NOT EXISTS reporting AUTHORIZATION paperless;
REVOKE ALL ON SCHEMA reporting FROM PUBLIC;

CREATE OR REPLACE VIEW reporting.dms_document_schedule
WITH (security_barrier = true)
AS
WITH custom_fields AS (
    SELECT
        instance.document_id,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Projekt / Kommission'
        ) AS project,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Artikel'
        ) AS item_code,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Revision'
        ) AS revision,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Dokumentverantwortung'
        ) AS responsible,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Meilenstein'
        ) AS milestone,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Dokumentlieferobjekt'
        ) AS deliverable_package,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Baseline-Version'
        ) AS baseline_version,
        MAX(instance.value_date) FILTER (
            WHERE field.name = 'Baseline-Termin'
        ) AS baseline_date,
        MAX(instance.value_date) FILTER (
            WHERE field.name = 'Liefertermin'
        ) AS due_date,
        MAX(instance.value_date) FILTER (
            WHERE field.name = 'Forecast-Termin'
        ) AS forecast_date,
        MAX(instance.value_date) FILTER (
            WHERE field.name = 'Tatsächliches Lieferdatum'
        ) AS actual_delivery_date,
        MAX(instance.value_text) FILTER (
            WHERE field.name = 'Lieferempfänger'
        ) AS recipient,
        BOOL_OR(instance.value_bool) FILTER (
            WHERE field.name = 'Vertragsdokument'
        ) AS contractual,
        MAX(instance.value_int) FILTER (
            WHERE field.name = 'Fortschritt (%)'
        ) AS progress_percent,
        MAX(instance.value_long_text) FILTER (
            WHERE field.name = 'Terminnotiz'
        ) AS schedule_note
    FROM documents_customfieldinstance AS instance
    INNER JOIN documents_customfield AS field ON field.id = instance.field_id
    WHERE instance.deleted_at IS NULL
    GROUP BY instance.document_id
), workflow_tags AS (
    SELECT
        document_tags.document_id,
        STRING_AGG(tag.name, ', ' ORDER BY tag.name) AS workflow_status
    FROM documents_document_tags AS document_tags
    INNER JOIN documents_tag AS tag ON tag.id = document_tags.tag_id
    WHERE tag.name LIKE 'Status/%'
    GROUP BY document_tags.document_id
), schedule AS (
    SELECT
        document.id AS document_id,
        document.title,
        document.original_filename,
        document.created AS document_date,
        document.added,
        document.modified,
        document_type.name AS document_type,
        fields.project,
        fields.item_code,
        fields.revision,
        fields.responsible,
        fields.milestone,
        fields.deliverable_package,
        fields.baseline_version,
        fields.baseline_date,
        fields.due_date,
        fields.forecast_date,
        fields.actual_delivery_date,
        fields.recipient,
        COALESCE(fields.contractual, false) AS contractual,
        COALESCE(fields.progress_percent, 0) AS progress_percent,
        fields.schedule_note,
        tags.workflow_status
    FROM documents_document AS document
    LEFT JOIN documents_documenttype AS document_type
        ON document_type.id = document.document_type_id
    LEFT JOIN custom_fields AS fields ON fields.document_id = document.id
    LEFT JOIN workflow_tags AS tags ON tags.document_id = document.id
    WHERE document.deleted_at IS NULL
      AND fields.project IS NOT NULL
)
SELECT
    schedule.*,
    CASE
        WHEN workflow_status LIKE '%Status/Obsolet%' THEN 'Obsolet'
        WHEN actual_delivery_date IS NOT NULL THEN 'Geliefert'
        WHEN due_date IS NULL THEN 'Ohne Termin'
        WHEN due_date < CURRENT_DATE THEN 'Überfällig'
        WHEN forecast_date IS NOT NULL AND forecast_date > due_date THEN 'Gefährdet'
        WHEN due_date <= CURRENT_DATE + 14 THEN 'Fällig ≤ 14 Tage'
        ELSE 'Im Plan'
    END AS schedule_status,
    due_date - CURRENT_DATE AS days_to_due,
    due_date - baseline_date AS baseline_variance_days,
    forecast_date - due_date AS forecast_variance_days,
    actual_delivery_date IS NOT NULL AS delivered,
    actual_delivery_date IS NULL
        AND due_date IS NOT NULL
        AND due_date < CURRENT_DATE AS overdue
FROM schedule;

COMMENT ON VIEW reporting.dms_document_schedule IS
    'Read-only DMS document delivery schedule for Grafana; contains no OCR content.';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM grafana_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA reporting FROM PUBLIC;
GRANT USAGE ON SCHEMA reporting TO grafana_reader;
GRANT SELECT ON reporting.dms_document_schedule TO grafana_reader;
