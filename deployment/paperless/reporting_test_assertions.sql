\set ON_ERROR_STOP on

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM reporting.dms_document_schedule) <> 2 THEN
        RAISE EXCEPTION 'expected two reporting rows';
    END IF;

    IF (
        SELECT schedule_status
        FROM reporting.dms_document_schedule
        WHERE document_id = 101
    ) <> 'Gefährdet' THEN
        RAISE EXCEPTION 'expected document 101 to be at risk';
    END IF;

    IF (
        SELECT schedule_status
        FROM reporting.dms_document_schedule
        WHERE document_id = 102
    ) <> 'Geliefert' THEN
        RAISE EXCEPTION 'expected document 102 to be delivered';
    END IF;

    IF (
        SELECT baseline_variance_days
        FROM reporting.dms_document_schedule
        WHERE document_id = 101
    ) <> 1 THEN
        RAISE EXCEPTION 'expected one day baseline variance';
    END IF;

    IF (
        SELECT forecast_variance_days
        FROM reporting.dms_document_schedule
        WHERE document_id = 101
    ) <> 2 THEN
        RAISE EXCEPTION 'expected two days forecast variance';
    END IF;
END
$$;

SET ROLE grafana_reader;
SELECT COUNT(*) FROM reporting.dms_document_schedule;
RESET ROLE;
