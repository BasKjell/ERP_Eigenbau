\set ON_ERROR_STOP on

SELECT format(
    'CREATE ROLE grafana_management_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %L',
    :'reporting_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_management_reader')
\gexec

SELECT format('ALTER ROLE grafana_management_reader PASSWORD %L', :'reporting_password')
\gexec

ALTER ROLE grafana_management_reader NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
SELECT format(
    'GRANT CONNECT ON DATABASE %I TO grafana_management_reader',
    current_database()
)
\gexec

CREATE SCHEMA IF NOT EXISTS reporting AUTHORIZATION platform;
REVOKE ALL ON SCHEMA reporting FROM PUBLIC;

CREATE TABLE IF NOT EXISTS reporting.order_forecast (
    order_id text PRIMARY KEY,
    project_id text NOT NULL,
    customer text NOT NULL,
    product text NOT NULL,
    stage text NOT NULL,
    status text NOT NULL,
    order_value numeric(14,2) NOT NULL,
    probability numeric(5,2) NOT NULL,
    planned_cost numeric(14,2) NOT NULL,
    actual_cost numeric(14,2) NOT NULL,
    forecast_cost numeric(14,2) NOT NULL,
    progress numeric(5,2) NOT NULL,
    expected_invoice_date date NOT NULL,
    risk text NOT NULL,
    owner_name text NOT NULL,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.cash_forecast (
    month date PRIMARY KEY,
    opening_balance numeric(14,2) NOT NULL,
    inflow numeric(14,2) NOT NULL,
    outflow numeric(14,2) NOT NULL,
    closing_balance numeric(14,2) NOT NULL,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.open_items (
    item_id text PRIMARY KEY,
    item_type text NOT NULL CHECK (item_type IN ('AR', 'AP')),
    partner text NOT NULL,
    document_reference text NOT NULL,
    due_date date NOT NULL,
    amount numeric(14,2) NOT NULL,
    status text NOT NULL,
    project_id text,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.budget_forecast (
    budget_id text PRIMARY KEY,
    budget_name text NOT NULL,
    owner_name text NOT NULL,
    cost_center text NOT NULL,
    budget_amount numeric(14,2) NOT NULL,
    actual_amount numeric(14,2) NOT NULL,
    forecast_amount numeric(14,2) NOT NULL,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.innovation_portfolio (
    portfolio_id text PRIMARY KEY,
    portfolio_type text NOT NULL,
    name text NOT NULL,
    owner_name text NOT NULL,
    status text NOT NULL,
    actual_cost numeric(14,2) NOT NULL,
    forecast_cost numeric(14,2) NOT NULL,
    target_date date,
    risk text NOT NULL,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.quality_cost (
    quality_id text PRIMARY KEY,
    category text NOT NULL,
    project_id text NOT NULL,
    amount numeric(14,2) NOT NULL,
    period date NOT NULL,
    snapshot_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS reporting.production_operation (
    operation_id text PRIMARY KEY,
    work_order_id text NOT NULL,
    sales_order_id text NOT NULL,
    project_id text NOT NULL,
    customer text NOT NULL,
    product text NOT NULL,
    quantity numeric(12,2) NOT NULL,
    due_date date NOT NULL,
    operation_sequence integer NOT NULL,
    operation text NOT NULL,
    workstation text NOT NULL,
    assigned_employee text,
    operation_status text NOT NULL CHECK (
        operation_status IN ('completed', 'in_progress', 'ready', 'waiting', 'blocked')
    ),
    planned_start timestamp with time zone NOT NULL,
    planned_end timestamp with time zone NOT NULL,
    actual_start timestamp with time zone,
    actual_end timestamp with time zone,
    completed_quantity numeric(12,2) NOT NULL DEFAULT 0,
    planned_minutes numeric(12,2) NOT NULL,
    actual_minutes numeric(12,2) NOT NULL DEFAULT 0,
    risk text NOT NULL,
    order_value numeric(14,2) NOT NULL,
    snapshot_at date NOT NULL,
    UNIQUE (work_order_id, operation_sequence)
);

CREATE TABLE IF NOT EXISTS reporting.crm_opportunity (
    opportunity_id text PRIMARY KEY,
    opportunity_name text NOT NULL,
    customer text NOT NULL,
    product text NOT NULL,
    stage text NOT NULL,
    status text NOT NULL CHECK (status IN ('open', 'won', 'lost')),
    sales_owner text NOT NULL,
    expected_close_date date NOT NULL,
    opportunity_value numeric(14,2) NOT NULL,
    probability numeric(5,2) NOT NULL CHECK (probability BETWEEN 0 AND 100),
    source text NOT NULL,
    region text NOT NULL,
    snapshot_at date NOT NULL
);

TRUNCATE TABLE
    reporting.order_forecast,
    reporting.cash_forecast,
    reporting.open_items,
    reporting.budget_forecast,
    reporting.innovation_portfolio,
    reporting.quality_cost,
    reporting.production_operation,
    reporting.crm_opportunity;

INSERT INTO reporting.order_forecast VALUES
    ('SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 'Produktion', 'in_progress', 62500, 95, 45500, 31200, 46800, 68, '2027-01-20', 'on_track', 'Paula Planung', '2026-11-04'),
    ('SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 'Produktion', 'in_progress', 145000, 80, 101500, 48600, 108500, 43, '2027-02-12', 'at_risk', 'Paula Planung', '2026-11-04'),
    ('SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 'Endprüfung', 'in_progress', 48000, 100, 31500, 29700, 32900, 92, '2026-11-18', 'on_track', 'Clara Qualität', '2026-11-04'),
    ('SO-4734', 'KOM-2027-4734', 'Hanseatic Sensorik GmbH', 'Edge Gateway 200', 'Engineering', 'released', 84000, 70, 57000, 11400, 59600, 21, '2027-03-25', 'on_track', 'System Engineering', '2026-11-04'),
    ('SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 'Produktion', 'in_progress', 97500, 90, 67400, 42100, 69100, 56, '2027-04-16', 'on_track', 'Paula Planung', '2026-11-04'),
    ('SO-4748', 'KOM-2027-4748', 'Arctic Marine AS', 'SCU-100 Erweiterung', 'Disposition', 'released', 76000, 85, 51800, 8600, 53500, 14, '2027-05-07', 'at_risk', 'Daniel Disposition', '2026-11-04'),
    ('SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 'Produktion', 'in_progress', 210000, 75, 148000, 37700, 154000, 24, '2027-05-28', 'at_risk', 'Sven Schichtleitung', '2026-11-04'),
    ('SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 'Endprüfung', 'in_progress', 36500, 100, 24200, 22600, 25100, 88, '2027-02-26', 'on_track', 'Clara Qualität', '2026-11-04'),
    ('QTN-2027-0088', 'PRE-2027-0088', 'Arctic Marine AS', 'SCU-100 Erweiterung', 'Vertrieb', 'quotation', 31500, 45, 21800, 1200, 22400, 8, '2027-04-30', 'at_risk', 'Anna Schneider', '2026-11-04');

INSERT INTO reporting.cash_forecast VALUES
    ('2024-11-01', 190000, 122500, 122100, 190400, '2026-11-04'),
    ('2024-12-01', 190400, 140000, 130900, 199500, '2026-11-04'),
    ('2025-01-01', 199500, 118000, 113900, 203600, '2026-11-04'),
    ('2025-02-01', 203600, 105000, 107500, 201100, '2026-11-04'),
    ('2025-03-01', 201100, 121500, 113300, 209300, '2026-11-04'),
    ('2025-04-01', 209300, 121000, 120100, 210200, '2026-11-04'),
    ('2025-05-01', 210200, 123000, 120900, 212300, '2026-11-04'),
    ('2025-06-01', 212300, 124500, 118500, 218300, '2026-11-04'),
    ('2025-07-01', 218300, 132000, 122300, 228000, '2026-11-04'),
    ('2025-08-01', 228000, 117000, 123100, 221900, '2026-11-04'),
    ('2025-09-01', 221900, 135500, 128900, 228500, '2026-11-04'),
    ('2025-10-01', 228500, 134000, 125500, 237000, '2026-11-04'),
    ('2025-11-01', 237000, 126000, 124300, 238700, '2026-11-04'),
    ('2025-12-01', 238700, 143500, 133100, 249100, '2026-11-04'),
    ('2026-01-01', 249100, 121500, 116100, 254500, '2026-11-04'),
    ('2026-02-01', 254500, 108500, 109700, 253300, '2026-11-04'),
    ('2026-03-01', 253300, 125000, 115500, 262800, '2026-11-04'),
    ('2026-04-01', 262800, 124500, 122300, 265000, '2026-11-04'),
    ('2026-05-01', 265000, 126500, 123100, 268400, '2026-11-04'),
    ('2026-06-01', 268400, 128000, 120700, 275700, '2026-11-04'),
    ('2026-07-01', 275700, 135500, 124500, 286700, '2026-11-04'),
    ('2026-08-01', 286700, 120500, 125300, 281900, '2026-11-04'),
    ('2026-09-01', 281900, 139000, 131100, 289800, '2026-11-04'),
    ('2026-10-01', 289800, 137500, 127700, 299600, '2026-11-04'),
    ('2026-11-01', 299600, 129500, 126500, 302600, '2026-11-04'),
    ('2026-12-01', 302600, 147000, 135300, 314300, '2026-11-04'),
    ('2027-01-01', 314300, 134000, 119800, 328500, '2026-11-04'),
    ('2027-02-01', 328500, 115000, 113400, 330100, '2026-11-04'),
    ('2027-03-01', 330100, 131500, 122200, 339400, '2026-11-04'),
    ('2027-04-01', 339400, 137000, 126000, 350400, '2026-11-04'),
    ('2027-05-01', 350400, 133000, 126800, 356600, '2026-11-04'),
    ('2027-06-01', 356600, 134500, 127400, 363700, '2026-11-04'),
    ('2027-07-01', 363700, 148000, 128200, 383500, '2026-11-04'),
    ('2027-08-01', 383500, 127000, 129000, 381500, '2026-11-04'),
    ('2027-09-01', 381500, 145500, 137800, 389200, '2026-11-04'),
    ('2027-10-01', 389200, 150000, 131400, 407800, '2026-11-04'),
    ('2027-11-01', 407800, 136000, 130200, 413600, '2026-11-04'),
    ('2027-12-01', 413600, 153500, 142000, 425100, '2026-11-04'),
    ('2028-01-01', 425100, 137500, 122000, 440600, '2026-11-04'),
    ('2028-02-01', 440600, 118500, 115600, 443500, '2026-11-04'),
    ('2028-03-01', 443500, 135000, 124400, 454100, '2026-11-04'),
    ('2028-04-01', 454100, 140500, 128200, 466400, '2026-11-04'),
    ('2028-05-01', 466400, 136500, 129000, 473900, '2026-11-04'),
    ('2028-06-01', 473900, 138000, 129600, 482300, '2026-11-04'),
    ('2028-07-01', 482300, 151500, 130400, 503400, '2026-11-04'),
    ('2028-08-01', 503400, 130500, 131200, 502700, '2026-11-04'),
    ('2028-09-01', 502700, 149000, 140000, 511700, '2026-11-04'),
    ('2028-10-01', 511700, 153500, 133600, 531600, '2026-11-04'),
    ('2028-11-01', 531600, 139500, 132400, 538700, '2026-11-04');

INSERT INTO reporting.open_items VALUES
    ('AR-2026-1018', 'AR', 'Oceanic Survey Ltd.', 'INV-2026-1018', '2026-10-28', 28750, 'overdue', 'KOM-2026-4699', '2026-11-04'),
    ('AR-2026-1042', 'AR', 'NordMarine Systems GmbH', 'INV-2026-1042', '2026-11-21', 41250, 'open', 'KOM-2027-4711', '2026-11-04'),
    ('AP-2026-0811', 'AP', 'PCB Solutions GmbH', 'PINV-2026-0811', '2026-11-12', 18400, 'open', 'KOM-2027-4711', '2026-11-04'),
    ('AP-2026-0822', 'AP', 'Cloud Tools Europe', 'PINV-2026-0822', '2026-11-18', 7200, 'open', 'RND-EDGE-AI', '2026-11-04');

INSERT INTO reporting.budget_forecast VALUES
    ('BUD-ENG-2027', 'Engineering & Entwicklung', 'CTO', 'CC-ENG', 480000, 286000, 492000, '2026-11-04'),
    ('BUD-PROD-2027', 'Produktion', 'COO', 'CC-PROD', 720000, 438000, 701000, '2026-11-04'),
    ('BUD-IT-2027', 'IT & Software', 'CIO', 'CC-IT', 210000, 131000, 226000, '2026-11-04'),
    ('BUD-SALES-2027', 'Vertrieb', 'CSO', 'CC-SALES', 185000, 97000, 179000, '2026-11-04');

INSERT INTO reporting.innovation_portfolio VALUES
    ('RND-EDGE-AI', 'R&D', 'Edge-AI Zustandsdiagnose', 'System Engineering', 'active', 202000, 236000, '2027-09-30', 'medium', '2026-11-04'),
    ('RND-SCU-NEXT', 'R&D', 'SCU Next Generation', 'Hardware Engineering', 'active', 143000, 188000, '2028-03-31', 'high', '2026-11-04'),
    ('SUB-ALM', 'Software', 'Engineering ALM Cloud', 'CIO', 'active', 32400, 43200, '2027-02-01', 'low', '2026-11-04'),
    ('SUB-SCA', 'Software', 'SCA & Container Security', 'CISO', 'active', 13950, 18600, '2027-05-15', 'low', '2026-11-04');

INSERT INTO reporting.quality_cost VALUES
    ('QCO-0001', 'Nacharbeit', 'KOM-2027-4711', 3200, '2026-10-01', '2026-11-04'),
    ('QCO-0002', 'Ausschuss', 'KOM-2027-4720', 6850, '2026-10-01', '2026-11-04'),
    ('QCO-0003', 'Prüfung', 'KOM-2026-4699', 4200, '2026-10-01', '2026-11-04'),
    ('RMA-0042', 'Gewährleistung', 'KOM-2025-4412', 7800, '2026-10-01', '2026-11-04'),
    ('RMA-0037', 'Gewährleistung', 'KOM-2025-4387', 3400, '2026-10-01', '2026-11-04');

INSERT INTO reporting.production_operation VALUES
    ('OP-WO-2026-0097-10', 'WO-2026-0097', 'SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 10, '2026-11-18', 10, 'Demontage Altgerät', 'WS-MECH', 'Mara Montage', 'completed', '2026-11-01 06:00+01', '2026-11-01 10:00+01', '2026-11-01 06:05+01', '2026-11-01 09:42+01', 10, 240, 217, 'on_track', 48000, '2026-11-04'),
    ('OP-WO-2026-0097-20', 'WO-2026-0097', 'SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 10, '2026-11-18', 20, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'completed', '2026-11-01 10:00+01', '2026-11-02 12:00+01', '2026-11-01 10:04+01', '2026-11-02 11:35+01', 10, 720, 686, 'on_track', 48000, '2026-11-04'),
    ('OP-WO-2026-0097-30', 'WO-2026-0097', 'SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 10, '2026-11-18', 30, 'Firmware aufspielen', 'WS-FW', 'Fiona Firmware', 'completed', '2026-11-02 12:00+01', '2026-11-02 17:00+01', '2026-11-02 12:10+01', '2026-11-02 16:18+01', 10, 300, 248, 'on_track', 48000, '2026-11-04'),
    ('OP-WO-2026-0097-40', 'WO-2026-0097', 'SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 10, '2026-11-18', 40, 'Funktionstest', 'WS-TEST-A', 'Theo Test', 'completed', '2026-11-03 06:00+01', '2026-11-03 16:00+01', '2026-11-03 06:01+01', '2026-11-03 15:47+01', 10, 600, 586, 'on_track', 48000, '2026-11-04'),
    ('OP-WO-2026-0097-50', 'WO-2026-0097', 'SO-4699', 'KOM-2026-4699', 'Oceanic Survey Ltd.', 'HMI Retrofit Kit', 10, '2026-11-18', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'in_progress', '2026-11-04 06:00+01', '2026-11-04 13:30+01', '2026-11-04 06:12+01', NULL, 7, 450, 295, 'on_track', 48000, '2026-11-04'),

    ('OP-WO-2027-0042-10', 'WO-2027-0042', 'SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 5, '2027-01-15', 10, 'Mechanische Montage', 'WS-MECH', 'Mara Montage', 'completed', '2027-01-08 06:00+01', '2027-01-08 08:00+01', '2027-01-08 06:10+01', '2027-01-08 07:08+01', 5, 60, 58, 'on_track', 62500, '2026-11-04'),
    ('OP-WO-2027-0042-20', 'WO-2027-0042', 'SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 5, '2027-01-15', 20, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'ready', '2027-01-08 08:00+01', '2027-01-08 11:00+01', NULL, NULL, 0, 90, 0, 'on_track', 62500, '2026-11-04'),
    ('OP-WO-2027-0042-30', 'WO-2027-0042', 'SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 5, '2027-01-15', 30, 'Firmware aufspielen', 'WS-FW', 'Fiona Firmware', 'waiting', '2027-01-09 08:00+01', '2027-01-09 09:30+01', NULL, NULL, 0, 30, 0, 'on_track', 62500, '2026-11-04'),
    ('OP-WO-2027-0042-40', 'WO-2027-0042', 'SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 5, '2027-01-15', 40, 'Funktionstest', 'WS-TEST-A', 'Theo Test', 'waiting', '2027-01-09 10:00+01', '2027-01-09 16:00+01', NULL, NULL, 0, 120, 0, 'on_track', 62500, '2026-11-04'),
    ('OP-WO-2027-0042-50', 'WO-2027-0042', 'SO-4711', 'KOM-2027-4711', 'NordMarine Systems GmbH', 'SCU-100', 5, '2027-01-15', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'waiting', '2027-01-11 06:00+01', '2027-01-11 09:45+01', NULL, NULL, 0, 45, 0, 'on_track', 62500, '2026-11-04'),

    ('OP-WO-2027-0051-10', 'WO-2027-0051', 'SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 4, '2027-02-12', 10, 'Mechanische Montage', 'WS-MECH', 'Mara Montage', 'completed', '2027-01-18 06:00+01', '2027-01-19 12:00+01', '2027-01-18 06:03+01', '2027-01-19 11:40+01', 4, 720, 697, 'at_risk', 145000, '2026-11-04'),
    ('OP-WO-2027-0051-20', 'WO-2027-0051', 'SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 4, '2027-02-12', 20, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'completed', '2027-01-20 06:00+01', '2027-01-22 14:00+01', '2027-01-20 06:15+01', '2027-01-22 16:20+01', 4, 960, 1085, 'at_risk', 145000, '2026-11-04'),
    ('OP-WO-2027-0051-30', 'WO-2027-0051', 'SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 4, '2027-02-12', 30, 'Firmware aufspielen', 'WS-FW', 'Fiona Firmware', 'completed', '2027-01-25 08:00+01', '2027-01-25 14:00+01', '2027-01-25 08:02+01', '2027-01-25 13:34+01', 4, 360, 332, 'at_risk', 145000, '2026-11-04'),
    ('OP-WO-2027-0051-40', 'WO-2027-0051', 'SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 4, '2027-02-12', 40, 'Funktionstest', 'WS-TEST-B', 'Tina Test', 'blocked', '2027-01-26 06:00+01', '2027-01-28 14:00+01', '2027-01-26 06:08+01', NULL, 1, 960, 310, 'at_risk', 145000, '2026-11-04'),
    ('OP-WO-2027-0051-50', 'WO-2027-0051', 'SO-4720', 'KOM-2027-4720', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 4, '2027-02-12', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'waiting', '2027-01-29 06:00+01', '2027-01-29 12:00+01', NULL, NULL, 0, 360, 0, 'at_risk', 145000, '2026-11-04'),

    ('OP-WO-2027-0063-10', 'WO-2027-0063', 'SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 25, '2027-04-16', 10, 'Mechanische Montage', 'WS-MECH', 'Mara Montage', 'completed', '2027-03-22 06:00+01', '2027-03-23 14:00+01', '2027-03-22 06:05+01', '2027-03-23 13:45+01', 25, 840, 820, 'on_track', 97500, '2026-11-04'),
    ('OP-WO-2027-0063-20', 'WO-2027-0063', 'SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 25, '2027-04-16', 20, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'completed', '2027-03-24 06:00+01', '2027-03-27 14:00+01', '2027-03-24 06:10+01', '2027-03-27 13:25+01', 25, 1440, 1395, 'on_track', 97500, '2026-11-04'),
    ('OP-WO-2027-0063-30', 'WO-2027-0063', 'SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 25, '2027-04-16', 30, 'Firmware aufspielen', 'WS-FW', 'Fiona Firmware', 'in_progress', '2027-03-29 08:00+02', '2027-03-30 14:00+02', '2027-03-29 08:02+02', NULL, 14, 600, 315, 'on_track', 97500, '2026-11-04'),
    ('OP-WO-2027-0063-40', 'WO-2027-0063', 'SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 25, '2027-04-16', 40, 'Funktionstest', 'WS-TEST-A', 'Theo Test', 'waiting', '2027-03-31 06:00+02', '2027-04-05 14:00+02', NULL, NULL, 0, 1800, 0, 'on_track', 97500, '2026-11-04'),
    ('OP-WO-2027-0063-50', 'WO-2027-0063', 'SO-4741', 'KOM-2027-4741', 'DeepSea Automation BV', 'Sensor Hub 8', 25, '2027-04-16', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'waiting', '2027-04-06 06:00+02', '2027-04-08 14:00+02', NULL, NULL, 0, 900, 0, 'on_track', 97500, '2026-11-04'),

    ('OP-WO-2027-0069-10', 'WO-2027-0069', 'SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 8, '2027-05-28', 10, 'Mechanische Bearbeitung', 'WS-CNC', 'Chris CNC', 'in_progress', '2027-04-12 06:00+02', '2027-04-20 14:00+02', '2027-04-12 06:00+02', NULL, 3, 2400, 980, 'at_risk', 210000, '2026-11-04'),
    ('OP-WO-2027-0069-20', 'WO-2027-0069', 'SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 8, '2027-05-28', 20, 'Kabelkonfektion', 'WS-CABLE', 'Karla Kabel', 'waiting', '2027-04-21 06:00+02', '2027-04-26 14:00+02', NULL, NULL, 0, 1440, 0, 'at_risk', 210000, '2026-11-04'),
    ('OP-WO-2027-0069-30', 'WO-2027-0069', 'SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 8, '2027-05-28', 30, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'waiting', '2027-04-27 06:00+02', '2027-05-04 14:00+02', NULL, NULL, 0, 2160, 0, 'at_risk', 210000, '2026-11-04'),
    ('OP-WO-2027-0069-40', 'WO-2027-0069', 'SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 8, '2027-05-28', 40, 'Funktionstest', 'WS-TEST-B', 'Tina Test', 'waiting', '2027-05-05 06:00+02', '2027-05-14 14:00+02', NULL, NULL, 0, 2880, 0, 'at_risk', 210000, '2026-11-04'),
    ('OP-WO-2027-0069-50', 'WO-2027-0069', 'SO-4752', 'KOM-2027-4752', 'Atlantic Research Systems Ltd.', 'Kompaktprüfstand', 8, '2027-05-28', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'waiting', '2027-05-17 06:00+02', '2027-05-19 14:00+02', NULL, NULL, 0, 720, 0, 'at_risk', 210000, '2026-11-04'),

    ('OP-WO-2027-0075-10', 'WO-2027-0075', 'SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 15, '2027-02-26', 10, 'Mechanische Montage', 'WS-MECH', 'Mara Montage', 'completed', '2027-02-08 06:00+01', '2027-02-09 14:00+01', '2027-02-08 06:02+01', '2027-02-09 13:40+01', 15, 840, 818, 'on_track', 36500, '2026-11-04'),
    ('OP-WO-2027-0075-20', 'WO-2027-0075', 'SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 15, '2027-02-26', 20, 'Elektronikmontage', 'WS-ELEC', 'Emil Elektronik', 'completed', '2027-02-10 06:00+01', '2027-02-12 14:00+01', '2027-02-10 06:06+01', '2027-02-12 13:50+01', 15, 1320, 1304, 'on_track', 36500, '2026-11-04'),
    ('OP-WO-2027-0075-30', 'WO-2027-0075', 'SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 15, '2027-02-26', 30, 'Firmware aufspielen', 'WS-FW', 'Fiona Firmware', 'completed', '2027-02-15 08:00+01', '2027-02-16 14:00+01', '2027-02-15 08:01+01', '2027-02-16 13:25+01', 15, 600, 574, 'on_track', 36500, '2026-11-04'),
    ('OP-WO-2027-0075-40', 'WO-2027-0075', 'SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 15, '2027-02-26', 40, 'Funktionstest', 'WS-TEST-A', 'Theo Test', 'completed', '2027-02-17 06:00+01', '2027-02-19 14:00+01', '2027-02-17 06:05+01', '2027-02-19 13:44+01', 15, 1320, 1299, 'on_track', 36500, '2026-11-04'),
    ('OP-WO-2027-0075-50', 'WO-2027-0075', 'SO-4760', 'KOM-2027-4760', 'North Sea Energy A/S', 'IOX-24', 15, '2027-02-26', 50, 'Endprüfung', 'WS-QC', 'Clara Qualität', 'ready', '2027-02-22 06:00+01', '2027-02-23 14:00+01', NULL, NULL, 0, 660, 0, 'on_track', 36500, '2026-11-04');

INSERT INTO reporting.crm_opportunity VALUES
    ('OPP-DEMO-2027-001', 'SCU-100 Flottenerweiterung', 'NordMarine Systems GmbH', 'SCU-100', 'Angebot', 'open', 'Anna Schneider', '2027-03-31', 150000, 80, 'Bestandskunde', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2027-002', 'AUV Rack Pilotserie', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 'Lösungskonzept', 'open', 'Jonas Weber', '2027-06-30', 168000, 65, 'Partner', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2027-003', 'HMI Retrofit Phase 2', 'Oceanic Survey Ltd.', 'HMI-070', 'Verhandlung', 'open', 'Anna Schneider', '2027-09-30', 96000, 70, 'Bestandskunde', 'UK & Ireland', '2026-11-04'),
    ('OPP-DEMO-2027-004', 'Edge Gateway Erprobung', 'Hanseatic Sensorik GmbH', 'GW-EDGE-200', 'Qualifizierung', 'open', 'Mehmet Kaya', '2027-11-30', 72000, 45, 'Messe', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2028-001', 'Edge Gateway Rollout', 'Hanseatic Sensorik GmbH', 'GW-EDGE-200', 'Lösungskonzept', 'open', 'Mehmet Kaya', '2028-02-29', 248000, 55, 'Bestandskunde', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2028-002', 'Sensor Hub Rahmenvertrag', 'DeepSea Automation BV', 'SENSOR-HUB-8', 'Qualifizierung', 'open', 'Sophie de Vries', '2028-05-31', 234000, 45, 'Empfehlung', 'Benelux', '2026-11-04'),
    ('OPP-DEMO-2028-003', 'Prüfstände Forschungsflotte', 'Atlantic Research Systems Ltd.', 'TEST-RIG-MINI', 'Erstkontakt', 'open', 'Oliver Smith', '2028-10-31', 228000, 35, 'Website', 'UK & Ireland', '2026-11-04'),
    ('OPP-DEMO-2028-004', 'SCU-100 Servicepaket', 'NordMarine Systems GmbH', 'SCU-100 Service', 'Angebot', 'open', 'Anna Schneider', '2028-12-15', 84000, 75, 'Bestandskunde', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2029-001', 'IOX-24 Plattformvertrag', 'North Sea Energy A/S', 'IOX-24', 'Qualifizierung', 'open', 'Lars Jensen', '2029-03-31', 252000, 40, 'Partner', 'Nordics', '2026-11-04'),
    ('OPP-DEMO-2029-002', 'SCU-100 Generation D', 'NordMarine Systems GmbH', 'SCU-100', 'Erstkontakt', 'open', 'Anna Schneider', '2029-08-31', 396000, 30, 'Roadmap', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2029-003', 'AUV Sensorpaket', 'Baltic Offshore Robotics AG', 'SENSOR-HUB-8', 'Lösungskonzept', 'open', 'Jonas Weber', '2029-10-31', 310000, 50, 'Bestandskunde', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2029-004', 'HMI Flottenstandard', 'Oceanic Survey Ltd.', 'HMI-070', 'Qualifizierung', 'open', 'Oliver Smith', '2029-12-15', 185000, 40, 'Bestandskunde', 'UK & Ireland', '2026-11-04'),
    ('OPP-DEMO-2030-001', 'Edge Fleet Analytics', 'Hanseatic Sensorik GmbH', 'GW-EDGE-200', 'Erstkontakt', 'open', 'Mehmet Kaya', '2030-04-30', 512000, 25, 'Roadmap', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2030-002', 'AUV Rack Serienprogramm', 'Baltic Offshore Robotics AG', 'AUV Control Rack', 'Erstkontakt', 'open', 'Jonas Weber', '2030-09-30', 648000, 20, 'Roadmap', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2030-003', 'Prüfautomatisierung Phase 2', 'Atlantic Research Systems Ltd.', 'TEST-RIG-MINI', 'Qualifizierung', 'open', 'Oliver Smith', '2030-11-30', 342000, 35, 'Bestandskunde', 'UK & Ireland', '2026-11-04'),
    ('OPP-DEMO-2030-004', 'Sensor Hub Nordsee', 'North Sea Energy A/S', 'SENSOR-HUB-8', 'Lösungskonzept', 'open', 'Lars Jensen', '2030-12-15', 425000, 45, 'Partner', 'Nordics', '2026-11-04'),
    ('OPP-DEMO-2031-001', 'Offshore Digitalisierung', 'North Sea Energy A/S', 'IOX-24', 'Erstkontakt', 'open', 'Lars Jensen', '2031-06-30', 492000, 15, 'Roadmap', 'Nordics', '2026-11-04'),
    ('OPP-DEMO-2031-002', 'DeepSea Plattform Gen 2', 'DeepSea Automation BV', 'SENSOR-HUB-8', 'Erstkontakt', 'open', 'Sophie de Vries', '2031-09-30', 730000, 20, 'Roadmap', 'Benelux', '2026-11-04'),
    ('OPP-DEMO-2031-003', 'SCU-100 Langzeitprogramm', 'NordMarine Systems GmbH', 'SCU-100', 'Qualifizierung', 'open', 'Anna Schneider', '2031-11-30', 575000, 35, 'Bestandskunde', 'DACH', '2026-11-04'),
    ('OPP-DEMO-2031-004', 'Autonome Prüfflotte', 'Atlantic Research Systems Ltd.', 'TEST-RIG-MINI', 'Erstkontakt', 'open', 'Oliver Smith', '2031-12-15', 810000, 15, 'Roadmap', 'UK & Ireland', '2026-11-04');

CREATE OR REPLACE VIEW reporting.management_order_forecast
WITH (security_barrier = true)
AS
SELECT
    order_id,
    project_id,
    customer,
    product,
    stage,
    status,
    order_value,
    probability,
    ROUND(order_value * probability / 100, 2) AS weighted_revenue,
    planned_cost,
    actual_cost,
    forecast_cost,
    order_value - forecast_cost AS expected_margin,
    ROUND((order_value - forecast_cost) / NULLIF(order_value, 0) * 100, 1) AS expected_margin_percent,
    progress,
    expected_invoice_date,
    DATE_TRUNC('month', expected_invoice_date)::date AS expected_invoice_month,
    risk,
    owner_name,
    snapshot_at
FROM reporting.order_forecast;

CREATE OR REPLACE VIEW reporting.management_monthly_revenue
WITH (security_barrier = true)
AS
SELECT
    expected_invoice_month AS month,
    SUM(order_value) AS order_value,
    SUM(weighted_revenue) AS weighted_revenue,
    SUM(expected_margin) AS expected_margin
FROM reporting.management_order_forecast
GROUP BY expected_invoice_month;

CREATE OR REPLACE VIEW reporting.management_production_wip
WITH (security_barrier = true)
AS
WITH operation_rollup AS (
    SELECT
        work_order_id,
        COUNT(*) AS operation_count,
        COUNT(*) FILTER (WHERE operation_status = 'completed') AS completed_operations,
        ROUND(
            SUM(completed_quantity) / NULLIF(MAX(quantity) * COUNT(*), 0) * 100,
            1
        ) AS progress_percent,
        SUM(planned_minutes) AS planned_minutes,
        SUM(actual_minutes) AS actual_minutes
    FROM reporting.production_operation
    GROUP BY work_order_id
), current_operation AS (
    SELECT
        operation.*,
        ROW_NUMBER() OVER (
            PARTITION BY work_order_id
            ORDER BY
                CASE operation_status
                    WHEN 'in_progress' THEN 1
                    WHEN 'blocked' THEN 2
                    WHEN 'ready' THEN 3
                    WHEN 'waiting' THEN 4
                    ELSE 5
                END,
                operation_sequence
        ) AS current_rank
    FROM reporting.production_operation operation
    WHERE operation_status <> 'completed'
)
SELECT
    current_operation.work_order_id,
    current_operation.sales_order_id,
    current_operation.project_id,
    current_operation.customer,
    current_operation.product,
    current_operation.quantity,
    current_operation.due_date,
    current_operation.operation_sequence,
    current_operation.operation AS current_operation,
    current_operation.workstation,
    current_operation.assigned_employee,
    current_operation.operation_status,
    current_operation.planned_start,
    current_operation.planned_end,
    current_operation.actual_start,
    current_operation.completed_quantity,
    operation_rollup.operation_count,
    operation_rollup.completed_operations,
    operation_rollup.progress_percent,
    operation_rollup.planned_minutes,
    operation_rollup.actual_minutes,
    current_operation.risk,
    current_operation.order_value,
    current_operation.snapshot_at
FROM current_operation
JOIN operation_rollup USING (work_order_id)
WHERE current_operation.current_rank = 1;

CREATE OR REPLACE VIEW reporting.management_workstation_load
WITH (security_barrier = true)
AS
SELECT
    workstation,
    COUNT(*) FILTER (WHERE operation_status <> 'completed') AS open_operations,
    COUNT(*) FILTER (WHERE operation_status = 'in_progress') AS active_operations,
    COUNT(*) FILTER (WHERE operation_status = 'blocked') AS blocked_operations,
    SUM(planned_minutes) FILTER (WHERE operation_status <> 'completed') AS remaining_planned_minutes,
    SUM(actual_minutes) AS actual_minutes,
    MAX(snapshot_at) AS snapshot_at
FROM reporting.production_operation
GROUP BY workstation;

CREATE OR REPLACE VIEW reporting.management_crm_pipeline
WITH (security_barrier = true)
AS
SELECT
    opportunity_id,
    opportunity_name,
    customer,
    product,
    stage,
    status,
    sales_owner,
    expected_close_date,
    EXTRACT(YEAR FROM expected_close_date)::integer AS close_year,
    opportunity_value,
    probability,
    ROUND(opportunity_value * probability / 100, 2) AS weighted_value,
    source,
    region,
    snapshot_at
FROM reporting.crm_opportunity;

CREATE OR REPLACE VIEW reporting.management_crm_pipeline_yearly
WITH (security_barrier = true)
AS
SELECT
    close_year,
    COUNT(*) FILTER (WHERE status = 'open') AS opportunity_count,
    SUM(opportunity_value) FILTER (WHERE status = 'open') AS pipeline_value,
    SUM(weighted_value) FILTER (WHERE status = 'open') AS weighted_pipeline,
    ROUND(AVG(probability) FILTER (WHERE status = 'open'), 1) AS average_probability
FROM reporting.management_crm_pipeline
GROUP BY close_year;

CREATE OR REPLACE VIEW reporting.management_executive_kpi
WITH (security_barrier = true)
AS
SELECT
    SUM(order_value) FILTER (WHERE status NOT IN ('cancelled', 'invoiced')) AS backlog_value,
    SUM(weighted_revenue) FILTER (WHERE status NOT IN ('cancelled', 'invoiced')) AS weighted_backlog,
    SUM(order_value) FILTER (WHERE stage IN ('Produktion', 'Endprüfung')) AS production_order_value,
    SUM(weighted_revenue) FILTER (WHERE stage IN ('Produktion', 'Endprüfung')) AS production_weighted_revenue,
    SUM(expected_margin) FILTER (WHERE status NOT IN ('cancelled', 'invoiced')) AS expected_margin,
    COUNT(*) FILTER (WHERE risk = 'at_risk') AS orders_at_risk,
    MAX(snapshot_at) AS snapshot_at,
    (SELECT COUNT(*) FROM reporting.management_production_wip) AS active_work_orders,
    (
        SELECT COUNT(*)
        FROM reporting.management_production_wip
        WHERE operation_status = 'blocked'
    ) AS blocked_work_orders
FROM reporting.management_order_forecast;

CREATE OR REPLACE VIEW reporting.management_budget_status
WITH (security_barrier = true)
AS
SELECT
    *,
    budget_amount - forecast_amount AS variance,
    ROUND(forecast_amount / NULLIF(budget_amount, 0) * 100, 1) AS forecast_usage_percent
FROM reporting.budget_forecast;

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM grafana_management_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA reporting FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA reporting FROM grafana_management_reader;
GRANT USAGE ON SCHEMA reporting TO grafana_management_reader;
GRANT SELECT ON
    reporting.management_order_forecast,
    reporting.management_monthly_revenue,
    reporting.management_executive_kpi,
    reporting.management_budget_status,
    reporting.management_production_wip,
    reporting.management_workstation_load,
    reporting.management_crm_pipeline,
    reporting.management_crm_pipeline_yearly,
    reporting.cash_forecast,
    reporting.open_items,
    reporting.innovation_portfolio,
    reporting.quality_cost
TO grafana_management_reader;

COMMENT ON SCHEMA reporting IS
    'Read-only management reporting model. Demo snapshot; productive ETL must replace seed inserts.';
COMMENT ON VIEW reporting.management_executive_kpi IS
    'Executive KPIs for backlog, production revenue and expected margin.';
COMMENT ON VIEW reporting.management_production_wip IS
    'One row per active work order with its current or next actionable operation.';
COMMENT ON VIEW reporting.management_crm_pipeline_yearly IS
    'Multi-year open CRM pipeline with gross and probability-weighted values.';
