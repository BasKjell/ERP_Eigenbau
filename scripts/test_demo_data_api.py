#!/usr/bin/env python3
"""Dependency-free unit tests for the repository-wide API orchestrator."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import demo_data_api

ROOT = Path(__file__).resolve().parents[1]


class DemoDataApiTests(unittest.TestCase):
    def test_cleanup_without_exact_confirmation_is_always_a_dry_run(self) -> None:
        observed: list[bool] = []

        class FakePlatform:
            def delete(self, report: demo_data_api.RunReport) -> None:
                observed.append(report.dry_run)
                report.action("platform", "Vorschau")

        output = io.StringIO()
        errors = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(demo_data_api.HANDLERS, {"platform": FakePlatform}),
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
        ):
            result = demo_data_api.main(
                "delete",
                [
                    "--systems",
                    "platform",
                    "--env-file",
                    str(Path(directory) / "missing.env"),
                ],
            )

        self.assertEqual(result, 0)
        self.assertEqual(observed, [True])
        self.assertIn("Sicherheitsmodus", errors.getvalue())
        self.assertIn('"dry_run": true', output.getvalue())

    def test_manifests_use_unique_exact_business_keys(self) -> None:
        erp = json.loads(
            (ROOT / "deployment/erpnext/demo_api_records.json").read_text(encoding="utf-8")
        )
        redmine = json.loads(
            (ROOT / "deployment/redmine/demo_api.json").read_text(encoding="utf-8")
        )

        erp_keys = [
            (record["doctype"], record["key_field"], record["key_value"])
            for record in erp["records"]
        ]
        redmine_keys = [project["identifier"] for project in redmine["projects"]]

        self.assertEqual(len(erp_keys), len(set(erp_keys)))
        self.assertEqual(len(redmine_keys), len(set(redmine_keys)))
        self.assertTrue(
            all(
                record["values"].get(record["key_field"]) == record["key_value"]
                for record in erp["records"]
            )
        )

    def test_system_parser_deduplicates_and_rejects_unknown_targets(self) -> None:
        self.assertEqual(
            demo_data_api.parse_systems("platform,redmine,platform"),
            ("platform", "redmine"),
        )
        with self.assertRaisesRegex(Exception, "Unbekannte Systeme"):
            demo_data_api.parse_systems("platform,unknown")

    def test_every_cleanup_target_has_a_nonempty_exact_key(self) -> None:
        records = json.loads(
            (ROOT / "deployment/erpnext/demo_api_records.json").read_text(encoding="utf-8")
        )["records"]

        for record in records:
            self.assertTrue(record["doctype"].strip())
            self.assertTrue(record["key_field"].strip())
            self.assertNotIn("*", str(record["key_value"]))
            self.assertNotEqual(str(record["key_value"]).strip(), "")
            self.assertTrue(set(record.get("update_omit", [])).issubset(record["values"]))
            self.assertNotIn(record["key_field"], record.get("update_omit", []))

    def test_erp_demo_manifest_contains_a_substantial_multi_year_scenario(self) -> None:
        records = json.loads(
            (ROOT / "deployment/erpnext/demo_api_records.json").read_text(encoding="utf-8")
        )["records"]
        counts = Counter(record["doctype"] for record in records)
        opportunities = [
            record for record in records if record["doctype"] == "Opportunity"
        ]
        closing_years = {
            int(record["values"]["expected_closing"][:4]) for record in opportunities
        }

        self.assertGreaterEqual(len(records), 80)
        self.assertGreaterEqual(counts["Customer"], 8)
        self.assertGreaterEqual(counts["Project"], 10)
        self.assertGreaterEqual(counts["Employee"], 10)
        self.assertGreaterEqual(counts["Opportunity"], 10)
        self.assertEqual(closing_years, {2027, 2028, 2029, 2030, 2031})

    def test_erp_cleanup_reverses_dependencies_before_master_data(self) -> None:
        records = json.loads(
            (ROOT / "deployment/erpnext/demo_api_records.json").read_text(encoding="utf-8")
        )["records"]
        first_opportunity = next(
            index for index, record in enumerate(records) if record["doctype"] == "Opportunity"
        )
        dependency_positions = [
            index
            for index, record in enumerate(records)
            if record["doctype"] in {"Customer", "Item", "Project"}
        ]

        self.assertLess(max(dependency_positions), first_opportunity)

    def test_management_dashboards_use_the_read_only_live_api(self) -> None:
        dashboard_dir = ROOT / "deployment/grafana/provisioning/dashboards/json"
        expectations = {"management-production-live.json", "management-crm-pipeline.json"}
        uids: set[str] = set()

        for filename in expectations:
            dashboard = json.loads((dashboard_dir / filename).read_text(encoding="utf-8"))
            self.assertNotIn(dashboard["uid"], uids)
            uids.add(dashboard["uid"])
            targets = [
                target
                for panel in dashboard["panels"]
                for target in panel.get("targets", [])
            ]
            self.assertTrue(targets)
            self.assertTrue(all(target["datasource"]["uid"] == "platform-live-api" for target in targets))
            self.assertTrue(all(target["url"].endswith("/api/reporting/live") for target in targets))
            self.assertTrue(all(target["root_selector"].startswith("$.") for target in targets))
            self.assertGreaterEqual(len(dashboard["panels"]), 7)


if __name__ == "__main__":
    unittest.main()
