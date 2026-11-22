\set ON_ERROR_STOP on

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM reporting.management_order_forecast) <> 9 THEN
        RAISE EXCEPTION 'expected nine order forecast rows';
    END IF;
    IF (SELECT production_order_value FROM reporting.management_executive_kpi) <> 599500 THEN
        RAISE EXCEPTION 'unexpected production order value';
    END IF;
    IF (SELECT production_weighted_revenue FROM reporting.management_executive_kpi) <> 505125 THEN
        RAISE EXCEPTION 'unexpected weighted production revenue';
    END IF;
    IF (SELECT COUNT(*) FROM reporting.management_budget_status WHERE variance < 0) <> 2 THEN
        RAISE EXCEPTION 'expected two over-forecast budgets';
    END IF;
    IF (SELECT COUNT(*) FROM reporting.management_production_wip) <> 6 THEN
        RAISE EXCEPTION 'expected six active production work orders';
    END IF;
    IF (
        SELECT current_operation
        FROM reporting.management_production_wip
        WHERE work_order_id = 'WO-2027-0051'
    ) <> 'Funktionstest' THEN
        RAISE EXCEPTION 'unexpected current operation for WO-2027-0051';
    END IF;
    IF (SELECT blocked_work_orders FROM reporting.management_executive_kpi) <> 1 THEN
        RAISE EXCEPTION 'expected one blocked work order';
    END IF;
    IF (SELECT COUNT(*) FROM reporting.management_crm_pipeline) <> 20 THEN
        RAISE EXCEPTION 'expected twenty CRM opportunities';
    END IF;
    IF (SELECT COUNT(*) FROM reporting.management_crm_pipeline_yearly) <> 5 THEN
        RAISE EXCEPTION 'expected CRM pipeline for five closing years';
    END IF;
    IF (SELECT COUNT(*) FROM reporting.cash_forecast) <> 49 THEN
        RAISE EXCEPTION 'expected 49 monthly cash rows for the four-year horizon';
    END IF;
    IF (SELECT MIN(month) FROM reporting.cash_forecast) <> DATE '2024-11-01'
       OR (SELECT MAX(month) FROM reporting.cash_forecast) <> DATE '2028-11-01' THEN
        RAISE EXCEPTION 'cash horizon must span November 2024 through November 2028';
    END IF;
    IF (
        SELECT weighted_pipeline
        FROM reporting.management_crm_pipeline_yearly
        WHERE close_year = 2027
    ) <> 328800 THEN
        RAISE EXCEPTION 'unexpected weighted CRM pipeline for 2027';
    END IF;
END
$$;

SET ROLE grafana_management_reader;
SELECT COUNT(*) FROM reporting.management_order_forecast;
SELECT COUNT(*) FROM reporting.cash_forecast;
SELECT COUNT(*) FROM reporting.management_production_wip;
SELECT COUNT(*) FROM reporting.management_crm_pipeline;
RESET ROLE;
