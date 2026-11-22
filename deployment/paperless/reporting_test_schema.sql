\set ON_ERROR_STOP on

CREATE TABLE documents_customfield (
    id bigint PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE documents_documenttype (
    id bigint PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE documents_document (
    id bigint PRIMARY KEY,
    title text NOT NULL,
    original_filename text NOT NULL,
    created date NOT NULL,
    added timestamptz NOT NULL,
    modified timestamptz NOT NULL,
    document_type_id bigint,
    deleted_at timestamptz,
    content text
);

CREATE TABLE documents_customfieldinstance (
    id bigint PRIMARY KEY,
    document_id bigint NOT NULL,
    field_id bigint NOT NULL,
    value_text text,
    value_date date,
    value_bool boolean,
    value_int integer,
    value_long_text text,
    deleted_at timestamptz
);

CREATE TABLE documents_tag (
    id bigint PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE documents_document_tags (
    document_id bigint NOT NULL,
    tag_id bigint NOT NULL
);

INSERT INTO documents_customfield (id, name) VALUES
    (1, 'Projekt / Kommission'),
    (2, 'Artikel'),
    (3, 'Revision'),
    (4, 'Dokumentverantwortung'),
    (5, 'Meilenstein'),
    (6, 'Dokumentlieferobjekt'),
    (7, 'Baseline-Version'),
    (8, 'Baseline-Termin'),
    (9, 'Liefertermin'),
    (10, 'Forecast-Termin'),
    (11, 'Tatsächliches Lieferdatum'),
    (12, 'Lieferempfänger'),
    (13, 'Vertragsdokument'),
    (14, 'Fortschritt (%)'),
    (15, 'Terminnotiz');

INSERT INTO documents_documenttype (id, name)
VALUES (1, 'Prüfplan');

INSERT INTO documents_document (
    id, title, original_filename, created, added, modified,
    document_type_id, deleted_at, content
) VALUES
    (
        101, 'Gefährdeter Prüfplan', 'pruefplan.pdf', CURRENT_DATE,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, NULL, 'vertraulicher OCR-Inhalt'
    ),
    (
        102, 'Gelieferter Prüfplan', 'geliefert.pdf', CURRENT_DATE,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, NULL, 'weiterer OCR-Inhalt'
    );

INSERT INTO documents_customfieldinstance (
    id, document_id, field_id, value_text, value_date,
    value_bool, value_int, value_long_text, deleted_at
) VALUES
    (1, 101, 1, 'KOM-TEST', NULL, NULL, NULL, NULL, NULL),
    (2, 101, 4, 'Qualität', NULL, NULL, NULL, NULL, NULL),
    (3, 101, 5, 'Kundenabnahme', NULL, NULL, NULL, NULL, NULL),
    (4, 101, 6, 'Prüfdokumentation', NULL, NULL, NULL, NULL, NULL),
    (5, 101, 7, 'BL-01', NULL, NULL, NULL, NULL, NULL),
    (6, 101, 8, NULL, CURRENT_DATE + 2, NULL, NULL, NULL, NULL),
    (7, 101, 9, NULL, CURRENT_DATE + 3, NULL, NULL, NULL, NULL),
    (8, 101, 10, NULL, CURRENT_DATE + 5, NULL, NULL, NULL, NULL),
    (9, 101, 12, 'Testkunde', NULL, NULL, NULL, NULL, NULL),
    (10, 101, 13, NULL, NULL, true, NULL, NULL, NULL),
    (11, 101, 14, NULL, NULL, NULL, 80, NULL, NULL),
    (12, 101, 15, NULL, NULL, NULL, NULL, 'Freigabe ausstehend', NULL),
    (13, 102, 1, 'KOM-TEST', NULL, NULL, NULL, NULL, NULL),
    (14, 102, 9, NULL, CURRENT_DATE - 1, NULL, NULL, NULL, NULL),
    (15, 102, 11, NULL, CURRENT_DATE, NULL, NULL, NULL, NULL),
    (16, 102, 14, NULL, NULL, NULL, 100, NULL, NULL);

INSERT INTO documents_tag (id, name)
VALUES (1, 'Status/In Prüfung'), (2, 'Status/Freigegeben');

INSERT INTO documents_document_tags (document_id, tag_id)
VALUES (101, 1), (102, 2);
