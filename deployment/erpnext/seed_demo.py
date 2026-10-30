#!/usr/bin/env python3
"""Prepare the SCU-100 demo for a manual end-to-end run in ERPNext.

The script is intentionally idempotent. It creates missing setup and master
data, but it neither overwrites existing records nor creates the downstream
transaction chain. Users start with opportunity OPP-2027-0018 and create the
quotation, sales order, production plan, purchase documents, work order,
delivery and invoice themselves in the ERPNext web client.

Run this file inside the ERPNext bench image. Docker Compose exposes that as:

    docker compose --profile full run --rm erpnext-seed
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import frappe
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime, nowdate

SITE = os.environ.get("FRAPPE_SITE", "frontend")
SITES_PATH = os.environ.get("FRAPPE_SITES_PATH", "/home/frappe/frappe-bench/sites")
DATA_FILE = Path(os.environ.get("ERP_DEMO_DATA_FILE", "/seed/scenario.json"))

CREATED: list[str] = []
EXISTING: list[str] = []
NOTES: list[str] = []

COMPONENT_COSTS = {
    "CASE-100-C": 800.0,
    "PCB-MAIN-42": 4500.0,
    "PSU-24V-80": 320.0,
    "CON-M12": 45.0,
    "HARNESS-100": 180.0,
    "DISPLAY-7": 700.0,
    "FW-SCU-3": 0.0,
    "ENC-IOX-24": 55.0,
    "PCB-IOX-24": 260.0,
    "TERM-24": 18.0,
    "FW-IOX-2": 0.0,
    "CASE-HMI-7": 110.0,
    "PCB-HMI-7": 380.0,
    "PSU-24V-40": 75.0,
    "HARNESS-HMI": 40.0,
    "FW-HMI-1": 0.0,
    "CASE-GW-200": 160.0,
    "PCB-GW-88": 650.0,
    "SSD-IND-256": 180.0,
    "HARNESS-GW": 65.0,
    "FW-GW-4": 0.0,
}

EXTRA_PRODUCTS: list[dict[str, Any]] = [
    {
        "item": "IOX-24",
        "name": "Remote-I/O-Modul 24 Kanal",
        "price": 890.0,
        "components": [
            {
                "item": "ENC-IOX-24",
                "name": "I/O-Aluminiumgehäuse",
                "qty": 1,
                "source": "make",
                "available": 60,
            },
            {
                "item": "PCB-IOX-24",
                "name": "I/O-Controllerplatine",
                "qty": 1,
                "source": "buy",
                "available": 45,
            },
            {
                "item": "TERM-24",
                "name": "24-polige Klemmenleiste",
                "qty": 2,
                "source": "buy",
                "available": 120,
            },
            {
                "item": "CON-M12",
                "name": "M12 Steckverbinder",
                "qty": 4,
                "source": "buy",
                "available": 40,
            },
            {
                "item": "FW-IOX-2",
                "name": "Firmware IOX v2",
                "qty": 1,
                "source": "software",
                "available": 999,
            },
        ],
        "operations": [
            ("Mechanische Montage", 20),
            ("Elektronikmontage", 35),
            ("Firmware-Station", 15),
            ("Endpruefung", 20),
        ],
    },
    {
        "item": "HMI-070",
        "name": "Bedienpanel 7 Zoll",
        "price": 1490.0,
        "components": [
            {
                "item": "CASE-HMI-7",
                "name": "HMI-Frontgehäuse",
                "qty": 1,
                "source": "make",
                "available": 25,
            },
            {
                "item": "PCB-HMI-7",
                "name": "HMI-Prozessorplatine",
                "qty": 1,
                "source": "buy",
                "available": 30,
            },
            {
                "item": "DISPLAY-7",
                "name": "Display-Modul 7 Zoll",
                "qty": 1,
                "source": "buy",
                "available": 7,
            },
            {
                "item": "PSU-24V-40",
                "name": "Netzteil 24 V / 40 W",
                "qty": 1,
                "source": "buy",
                "available": 50,
            },
            {
                "item": "HARNESS-HMI",
                "name": "HMI-Kabelsatz",
                "qty": 1,
                "source": "make",
                "available": 40,
            },
            {
                "item": "FW-HMI-1",
                "name": "Firmware HMI v1",
                "qty": 1,
                "source": "software",
                "available": 999,
            },
        ],
        "operations": [
            ("Mechanische Montage", 25),
            ("Elektronikmontage", 45),
            ("Firmware-Station", 20),
            ("Pruefstand A", 35),
            ("Endpruefung", 20),
        ],
    },
    {
        "item": "GW-EDGE-200",
        "name": "Industrial Edge Gateway",
        "price": 2390.0,
        "components": [
            {
                "item": "CASE-GW-200",
                "name": "Gateway-Aluminiumgehäuse",
                "qty": 1,
                "source": "make",
                "available": 18,
            },
            {
                "item": "PCB-GW-88",
                "name": "Edge-Computer-Platine",
                "qty": 1,
                "source": "buy",
                "available": 20,
            },
            {
                "item": "PSU-24V-80",
                "name": "Netzteil 24 V",
                "qty": 1,
                "source": "buy",
                "available": 8,
            },
            {
                "item": "CON-M12",
                "name": "M12 Steckverbinder",
                "qty": 4,
                "source": "buy",
                "available": 40,
            },
            {
                "item": "SSD-IND-256",
                "name": "Industrie-SSD 256 GB",
                "qty": 1,
                "source": "buy",
                "available": 22,
            },
            {
                "item": "HARNESS-GW",
                "name": "Gateway-Kabelsatz",
                "qty": 1,
                "source": "make",
                "available": 30,
            },
            {
                "item": "FW-GW-4",
                "name": "Firmware Gateway v4",
                "qty": 1,
                "source": "software",
                "available": 999,
            },
        ],
        "operations": [
            ("Mechanische Montage", 35),
            ("Elektronikmontage", 55),
            ("Firmware-Station", 30),
            ("Pruefstand A", 45),
            ("Endpruefung", 25),
        ],
    },
]


def log(message: str) -> None:
    print(f"[erpnext-seed] {message}", flush=True)


def load_scenario() -> dict[str, Any]:
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"Demo data file not found: {DATA_FILE}")
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def filtered_values(doctype: str, values: dict[str, Any]) -> dict[str, Any]:
    """Keep only fields that exist in the installed ERPNext version."""
    meta = frappe.get_meta(doctype)
    result: dict[str, Any] = {"doctype": doctype}
    for key, value in values.items():
        field = meta.get_field(key)
        if not field:
            continue
        if field.fieldtype == "Table" and isinstance(value, list):
            result[key] = [
                {
                    child_key: child_value
                    for child_key, child_value in row.items()
                    if frappe.get_meta(field.options).get_field(child_key)
                }
                for row in value
            ]
        else:
            result[key] = value
    return result


def insert_missing(
    doctype: str,
    name: str,
    values: dict[str, Any],
    *,
    submit: bool = False,
) -> Any:
    if frappe.db.exists(doctype, name):
        EXISTING.append(f"{doctype}: {name}")
        return frappe.get_doc(doctype, name)

    doc = frappe.get_doc(filtered_values(doctype, values))
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True, set_name=name)
    if submit and doc.docstatus == 0:
        doc.submit()
    CREATED.append(f"{doctype}: {doc.name}")
    return doc


def insert_missing_by_filter(
    doctype: str,
    filters: dict[str, Any],
    values: dict[str, Any],
) -> Any:
    name = frappe.db.get_value(doctype, filters, "name")
    if name:
        EXISTING.append(f"{doctype}: {name}")
        return frappe.get_doc(doctype, name)

    doc = frappe.get_doc(filtered_values(doctype, values))
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    CREATED.append(f"{doctype}: {doc.name}")
    return doc


def set_single_if_present(doctype: str, values: dict[str, Any]) -> None:
    meta = frappe.get_meta(doctype)
    for field, value in values.items():
        if meta.get_field(field):
            frappe.db.set_single_value(doctype, field, value)


def ensure_tree_node(
    doctype: str,
    name: str,
    *,
    label_field: str,
    parent_field: str,
    root_name: str,
) -> str:
    if frappe.db.exists(doctype, name):
        EXISTING.append(f"{doctype}: {name}")
        return name

    if not frappe.db.exists(doctype, root_name):
        insert_missing(
            doctype,
            root_name,
            {label_field: root_name, "is_group": 1},
        )

    insert_missing(
        doctype,
        name,
        {
            label_field: name,
            parent_field: root_name,
            "is_group": 0,
        },
    )
    return name


def ensure_company(company: str, currency: str) -> Any:
    # A bare `bench new-site --install-app erpnext` has no setup-wizard
    # defaults yet. Company creation links its in-transit warehouse to this
    # master record, so create it before the Company document itself.
    insert_missing(
        "Warehouse Type",
        "Transit",
        {"description": "Warehouses used for goods in transit"},
    )
    if frappe.db.exists("Company", company):
        EXISTING.append(f"Company: {company}")
        company_doc = frappe.get_doc("Company", company)
    else:
        # The v16 Company hook creates Department children before their required
        # company-scoped root exists on a site that skipped the Setup Wizard.
        # Defer only that hook, then create the root once the Company row exists.
        from erpnext.setup.doctype.company.company import Company

        create_default_departments = Company.create_default_departments
        Company.create_default_departments = lambda self: None
        try:
            company_doc = insert_missing(
                "Company",
                company,
                {
                    "company_name": company,
                    "abbr": "OMD",
                    "default_currency": currency,
                    "country": "Germany",
                    "create_chart_of_accounts_based_on": "Standard Template",
                    "chart_of_accounts": "Standard",
                    "domain": "Manufacturing",
                },
            )
        finally:
            Company.create_default_departments = create_default_departments

    insert_missing(
        "Department",
        "All Departments",
        {
            "department_name": "All Departments",
            "parent_department": "",
            "is_group": 1,
            "company": company,
        },
    )
    company_doc.create_default_departments()

    frappe.db.set_default("company", company)
    frappe.db.set_default("currency", currency)
    frappe.db.set_default("country", "Germany")
    set_single_if_present(
        "Global Defaults",
        {
            "default_company": company,
            "default_currency": currency,
            "country": "Germany",
        },
    )
    return company_doc


def ensure_fiscal_years(company: str) -> None:
    for year in ("2026", "2027"):
        insert_missing(
            "Fiscal Year",
            year,
            {
                "year": year,
                "year_start_date": f"{year}-01-01",
                "year_end_date": f"{year}-12-31",
                "companies": [{"company": company}],
            },
        )
    frappe.db.set_default("fiscal_year", str(getdate(nowdate()).year))


def ensure_parties(scenario: dict[str, Any]) -> tuple[str, str, str]:
    customer_group = ensure_tree_node(
        "Customer Group",
        "Demo Industriekunden",
        label_field="customer_group_name",
        parent_field="parent_customer_group",
        root_name="All Customer Groups",
    )
    supplier_group = ensure_tree_node(
        "Supplier Group",
        "Demo Elektroniklieferanten",
        label_field="supplier_group_name",
        parent_field="parent_supplier_group",
        root_name="All Supplier Groups",
    )
    territory = ensure_tree_node(
        "Territory",
        "Deutschland",
        label_field="territory_name",
        parent_field="parent_territory",
        root_name="All Territories",
    )

    customer = scenario["scenario"]["customer"]
    insert_missing(
        "Customer",
        customer,
        {
            "customer_name": customer,
            "customer_type": "Company",
            "customer_group": customer_group,
            "territory": territory,
            "default_currency": scenario["scenario"]["currency"],
        },
    )

    for supplier in ("Baltic Electronics", "Display Components Europe"):
        insert_missing(
            "Supplier",
            supplier,
            {
                "supplier_name": supplier,
                "supplier_group": supplier_group,
                "supplier_type": "Company",
                "country": "Germany",
                "default_currency": scenario["scenario"]["currency"],
            },
        )

    set_single_if_present(
        "Selling Settings",
        {"customer_group": customer_group, "territory": territory},
    )
    set_single_if_present("Buying Settings", {"supplier_group": supplier_group})
    return customer, customer_group, supplier_group


def ensure_price_list(name: str, currency: str, *, selling: bool) -> None:
    insert_missing(
        "Price List",
        name,
        {
            "price_list_name": name,
            "currency": currency,
            "enabled": 1,
            "selling": int(selling),
            "buying": int(not selling),
        },
    )


def ensure_items(
    scenario: dict[str, Any], company: str, stores: str
) -> tuple[str, list[dict[str, Any]]]:
    set_single_if_present(
        "Stock Settings",
        {
            "enable_serial_and_batch_no_for_item": 1,
            "use_serial_batch_fields": 1,
        },
    )
    insert_missing(
        "UOM",
        "Nos",
        {
            "uom_name": "Nos",
            "symbol": "Stk",
            "enabled": 1,
            "must_be_whole_number": 1,
        },
    )
    product_group = ensure_tree_node(
        "Item Group",
        "Demo Fertigerzeugnisse",
        label_field="item_group_name",
        parent_field="parent_item_group",
        root_name="All Item Groups",
    )
    component_group = ensure_tree_node(
        "Item Group",
        "Demo Komponenten",
        label_field="item_group_name",
        parent_field="parent_item_group",
        root_name="All Item Groups",
    )

    order = scenario["order"]
    product = order["product"]
    insert_missing(
        "Item",
        product,
        {
            "item_code": product,
            "item_name": order["product_name"],
            "description": (
                f"{order['product_name']}, Revision {order['revision']} (ausschliesslich Demodaten)"
            ),
            "item_group": product_group,
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "is_sales_item": 1,
            "is_purchase_item": 0,
            "has_serial_no": 1,
            "include_item_in_manufacturing": 1,
            "item_defaults": [{"company": company, "default_warehouse": stores}],
        },
    )

    source_to_request_type = {
        "buy": "Purchase",
        "make": "Manufacture",
        "software": "",
    }
    for row in scenario["bom"]:
        is_stock = row["source"] != "software"
        insert_missing(
            "Item",
            row["item"],
            {
                "item_code": row["item"],
                "item_name": row["name"],
                "description": f"{row['name']} (SCU-100 Demokomponente)",
                "item_group": component_group,
                "stock_uom": "Nos",
                "is_stock_item": int(is_stock),
                "is_sales_item": 0,
                "is_purchase_item": int(row["source"] == "buy"),
                "include_item_in_manufacturing": 1,
                "default_material_request_type": source_to_request_type[row["source"]],
                "valuation_rate": COMPONENT_COSTS[row["item"]],
                "item_defaults": [{"company": company, "default_warehouse": stores}],
            },
        )

    return product, scenario["bom"]


def ensure_prices(scenario: dict[str, Any], currency: str, bom_rows: list[dict[str, Any]]) -> None:
    ensure_price_list("Standard Selling", currency, selling=True)
    ensure_price_list("Standard Buying", currency, selling=False)

    insert_missing_by_filter(
        "Item Price",
        {"item_code": scenario["order"]["product"], "price_list": "Standard Selling"},
        {
            "item_code": scenario["order"]["product"],
            "price_list": "Standard Selling",
            "price_list_rate": scenario["order"]["unit_price"],
            "currency": currency,
            "selling": 1,
        },
    )
    for row in bom_rows:
        if row["source"] != "buy":
            continue
        insert_missing_by_filter(
            "Item Price",
            {"item_code": row["item"], "price_list": "Standard Buying"},
            {
                "item_code": row["item"],
                "price_list": "Standard Buying",
                "price_list_rate": COMPONENT_COSTS[row["item"]],
                "currency": currency,
                "buying": 1,
            },
        )


def ensure_additional_products(company: str, currency: str, stores: str) -> list[dict[str, Any]]:
    """Create extra demo products and their shared components."""
    product_group = ensure_tree_node(
        "Item Group",
        "Demo Fertigerzeugnisse",
        label_field="item_group_name",
        parent_field="parent_item_group",
        root_name="All Item Groups",
    )
    component_group = ensure_tree_node(
        "Item Group",
        "Demo Komponenten",
        label_field="item_group_name",
        parent_field="parent_item_group",
        root_name="All Item Groups",
    )
    source_to_request_type = {
        "buy": "Purchase",
        "make": "Manufacture",
        "software": "",
    }
    seen_components: set[str] = set()
    for product in EXTRA_PRODUCTS:
        insert_missing(
            "Item",
            product["item"],
            {
                "item_code": product["item"],
                "item_name": product["name"],
                "description": f"{product['name']} (ausschliesslich Demodaten)",
                "item_group": product_group,
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "is_sales_item": 1,
                "is_purchase_item": 0,
                "has_serial_no": 0,
                "include_item_in_manufacturing": 1,
                "item_defaults": [{"company": company, "default_warehouse": stores}],
            },
        )
        insert_missing_by_filter(
            "Item Price",
            {"item_code": product["item"], "price_list": "Standard Selling"},
            {
                "item_code": product["item"],
                "price_list": "Standard Selling",
                "price_list_rate": product["price"],
                "currency": currency,
                "selling": 1,
            },
        )
        for row in product["components"]:
            if row["item"] in seen_components or frappe.db.exists("Item", row["item"]):
                seen_components.add(row["item"])
                continue
            seen_components.add(row["item"])
            is_stock = row["source"] != "software"
            insert_missing(
                "Item",
                row["item"],
                {
                    "item_code": row["item"],
                    "item_name": row["name"],
                    "description": f"{row['name']} (Demokomponente)",
                    "item_group": component_group,
                    "stock_uom": "Nos",
                    "is_stock_item": int(is_stock),
                    "is_sales_item": 0,
                    "is_purchase_item": int(row["source"] == "buy"),
                    "include_item_in_manufacturing": 1,
                    "default_material_request_type": source_to_request_type[row["source"]],
                    "valuation_rate": COMPONENT_COSTS[row["item"]],
                    "item_defaults": [{"company": company, "default_warehouse": stores}],
                },
            )
            if row["source"] == "buy":
                insert_missing_by_filter(
                    "Item Price",
                    {"item_code": row["item"], "price_list": "Standard Buying"},
                    {
                        "item_code": row["item"],
                        "price_list": "Standard Buying",
                        "price_list_rate": COMPONENT_COSTS[row["item"]],
                        "currency": currency,
                        "buying": 1,
                    },
                )
    return EXTRA_PRODUCTS


def product_operations(
    product: dict[str, Any], base_operations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name = {str(row["operation"]): row for row in base_operations}
    operations: list[dict[str, Any]] = []
    for sequence, (name, minutes) in enumerate(product["operations"], start=1):
        if name not in by_name:
            raise RuntimeError(f"Operation {name} is unavailable for {product['item']}")
        operations.append(
            {
                "sequence_id": sequence,
                "operation": name,
                "workstation": by_name[name]["workstation"],
                "time_in_mins": minutes,
                "fixed_time": 0,
            }
        )
    return operations


def warehouse_for(company: str, field: str, warehouse_name: str) -> str:
    value = frappe.db.get_value("Company", company, field)
    if value:
        return value
    value = frappe.db.get_value(
        "Warehouse",
        {"company": company, "warehouse_name": warehouse_name, "is_group": 0},
        "name",
    )
    if not value:
        value = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    if not value:
        raise RuntimeError(f"No leaf warehouse exists for {company}")
    if frappe.get_meta("Company").get_field(field):
        frappe.db.set_value("Company", company, field, value)
    return value


def ensure_workstations_and_operations(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for row in scenario["capacity"]:
        start_time, end_time = [f"{value}:00" for value in row["shift"].split("-")]
        workstation = insert_missing(
            "Workstation",
            row["id"],
            {
                "workstation_name": row["id"],
                "description": (
                    f"{row['name']} – Demokapazitaet {row['capacity']}, "
                    f"Auslastung {row['utilization']} %"
                ),
                "production_capacity": row["capacity"],
                "status": "Production",
                "working_hours": [{"start_time": start_time, "end_time": end_time}],
            },
        ).name
        operation = insert_missing(
            "Operation",
            row["name"],
            {
                "operation": row["name"],
                "description": f"SCU-100 Demoarbeitsgang an {workstation}",
                "workstation": workstation,
                "default_workstation": workstation,
            },
        ).name
        operations.append(
            {
                "operation": operation,
                "workstation": workstation,
                "time_in_mins": row["operation_minutes"],
                "fixed_time": 0,
            }
        )
    return operations


def ensure_quality_template(product: str) -> None:
    if not frappe.db.exists("DocType", "Quality Inspection Template"):
        NOTES.append("Quality Inspection Template is unavailable in this ERPNext build")
        return

    template_name = "SCU-100 Endpruefung"
    for parameter in (
        "Versorgungsspannung",
        "Funktionstest",
        "Sichtpruefung",
    ):
        insert_missing(
            "Quality Inspection Parameter",
            parameter,
            {
                "parameter": parameter,
                "description": f"SCU-100 Demopruefmerkmal: {parameter}",
            },
        )
    template = insert_missing(
        "Quality Inspection Template",
        template_name,
        {
            "quality_inspection_template_name": template_name,
            "item_quality_inspection_parameter": [
                {
                    "specification": "Versorgungsspannung",
                    "parameter": "Versorgungsspannung",
                    "numeric": 1,
                    "min_value": 23.5,
                    "max_value": 24.5,
                },
                {
                    "specification": "Funktionstest",
                    "parameter": "Funktionstest",
                    "numeric": 0,
                    "value": "Bestanden",
                },
                {
                    "specification": "Sichtpruefung",
                    "parameter": "Sichtpruefung",
                    "numeric": 0,
                    "value": "Bestanden",
                },
            ],
        },
    )
    if frappe.get_meta("Item").get_field("quality_inspection_template"):
        frappe.db.set_value("Item", product, "quality_inspection_template", template.name)


def ensure_bom(
    company: str,
    product: str,
    bom_rows: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    stores: str,
    finished_goods: str,
) -> str:
    existing = frappe.db.get_value(
        "BOM",
        {"company": company, "item": product, "docstatus": ["<", 2]},
        "name",
    )
    if existing:
        EXISTING.append(f"BOM: {existing}")
        return existing

    doc = frappe.get_doc(
        filtered_values(
            "BOM",
            {
                "company": company,
                "item": product,
                "quantity": 1,
                "is_active": 1,
                "is_default": 1,
                "with_operations": 1,
                "default_source_warehouse": stores,
                "default_target_warehouse": finished_goods,
                "rm_cost_as_per": "Valuation Rate",
                "items": [
                    {
                        "item_code": row["item"],
                        "qty": row["qty"],
                        "uom": "Nos",
                        "source_warehouse": stores,
                        "rate": COMPONENT_COSTS[row["item"]],
                        "include_item_in_manufacturing": 1,
                    }
                    for row in bom_rows
                ],
                "operations": operations,
            },
        )
    )
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    CREATED.append(f"BOM: {doc.name}")
    return doc.name


def ensure_opening_stock(company: str, bom_rows: list[dict[str, Any]], stores: str) -> None:
    stock_rows = []
    seen: set[str] = set()
    for row in bom_rows:
        item_code = row["item"]
        if item_code in seen or row["source"] == "software" or row["available"] <= 0:
            continue
        seen.add(item_code)
        if frappe.db.exists(
            "Stock Ledger Entry",
            {"company": company, "item_code": item_code, "is_cancelled": 0},
        ):
            continue
        stock_rows.append(
            {
                "item_code": item_code,
                "warehouse": stores,
                "qty": row["available"],
                "valuation_rate": COMPONENT_COSTS[item_code],
            }
        )
    if not stock_rows:
        NOTES.append("Opening stock already exists for all demo components")
        return

    opening_account = frappe.db.get_value(
        "Account",
        {
            "company": company,
            "account_name": "Temporary Opening",
            "is_group": 0,
        },
        "name",
    ) or frappe.db.get_value(
        "Account",
        {
            "company": company,
            "report_type": "Balance Sheet",
            "is_group": 0,
            "account_type": ["!=", "Stock"],
        },
        "name",
    )
    if not opening_account:
        raise RuntimeError(f"No opening balance account exists for {company}")

    doc = frappe.get_doc(
        filtered_values(
            "Stock Reconciliation",
            {
                "company": company,
                # Use a normal reconciliation so the company's stock
                # adjustment account is valid; this is disposable demo stock,
                # not a legally relevant opening balance.
                "purpose": "Stock Reconciliation",
                "posting_date": nowdate(),
                "posting_time": "06:00:00",
                "set_posting_time": 1,
                "expense_account": opening_account,
                "items": stock_rows,
            },
        )
    )
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    CREATED.append(f"Stock Reconciliation: {doc.name}")


def ensure_stock_entry(
    marker: str,
    company: str,
    stock_entry_type: str,
    items: list[dict[str, Any]],
    *,
    posting_time: str,
    bom_no: str = "",
) -> str:
    remarks = f"[ERP-EIGENBAU-DEMO:{marker}] automatisch erzeugte Demobuchung"
    existing = frappe.db.get_value(
        "Stock Entry",
        {"remarks": remarks, "docstatus": ["<", 2]},
        "name",
    )
    if existing:
        EXISTING.append(f"Stock Entry: {existing}")
        return str(existing)
    values: dict[str, Any] = {
        "company": company,
        "stock_entry_type": stock_entry_type,
        "purpose": stock_entry_type,
        "posting_date": nowdate(),
        "posting_time": posting_time,
        "set_posting_time": 1,
        "remarks": remarks,
        "items": items,
    }
    if bom_no:
        values.update(
            {
                "from_bom": 1,
                "bom_no": bom_no,
                "fg_completed_qty": next(
                    float(row["qty"]) for row in items if row.get("is_finished_item")
                ),
            }
        )
    doc = frappe.get_doc(filtered_values("Stock Entry", values))
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    doc.submit()
    # Make the ledger row visible to the next dependent stock movement.
    frappe.db.commit()
    CREATED.append(f"Stock Entry: {doc.name}")
    return doc.name


def stock_items_for_product(
    product: dict[str, Any], quantity: float, source_warehouse: str, target_warehouse: str
) -> list[dict[str, Any]]:
    rows = [
        {
            "item_code": component["item"],
            "qty": float(component["qty"]) * quantity,
            "s_warehouse": source_warehouse,
            "uom": "Nos",
            "stock_uom": "Nos",
            "conversion_factor": 1,
            "basic_rate": COMPONENT_COSTS[component["item"]],
        }
        for component in product["components"]
        if component["source"] != "software"
    ]
    rows.append(
        {
            "item_code": product["item"],
            "qty": quantity,
            "t_warehouse": target_warehouse,
            "uom": "Nos",
            "stock_uom": "Nos",
            "conversion_factor": 1,
            "is_finished_item": 1,
        }
    )
    return rows


def ensure_demo_stock_movements(
    company: str,
    products: list[dict[str, Any]],
    bom_names: dict[str, str],
    stores: str,
    work_in_progress: str,
    finished_goods: str,
) -> None:
    latest_time = frappe.db.get_value(
        "Stock Ledger Entry",
        {"posting_date": nowdate(), "is_cancelled": 0},
        "posting_time",
        order_by="posting_time desc",
    )
    ledger_time = get_datetime(f"{nowdate()} {latest_time}") if latest_time else now_datetime()
    base_time = max(now_datetime(), ledger_time)

    def demo_time(offset_minutes: int) -> str:
        return add_to_date(base_time, minutes=offset_minutes).strftime("%H:%M:%S")

    ensure_stock_entry(
        "RECEIPT-PCB-MAIN",
        company,
        "Material Receipt",
        [
            {
                "item_code": "PCB-MAIN-42",
                "qty": 25,
                "t_warehouse": stores,
                "uom": "Nos",
                "stock_uom": "Nos",
                "conversion_factor": 1,
                "basic_rate": COMPONENT_COSTS["PCB-MAIN-42"],
            }
        ],
        posting_time=demo_time(0),
    )

    iox = next(product for product in products if product["item"] == "IOX-24")
    transfer_rows = []
    for component in iox["components"]:
        if component["source"] == "software":
            continue
        transfer_rows.append(
            {
                "item_code": component["item"],
                "qty": float(component["qty"]) * 3,
                "s_warehouse": stores,
                "t_warehouse": work_in_progress,
                "uom": "Nos",
                "stock_uom": "Nos",
                "conversion_factor": 1,
            }
        )
    ensure_stock_entry(
        "TRANSFER-IOX-24",
        company,
        "Material Transfer",
        transfer_rows,
        posting_time=demo_time(1),
    )
    ensure_stock_entry(
        "MANUFACTURE-IOX-24",
        company,
        "Manufacture",
        stock_items_for_product(iox, 3, work_in_progress, finished_goods),
        posting_time=demo_time(2),
        bom_no=bom_names["IOX-24"],
    )

    for marker, item_code, quantity, offset_minutes in (
        ("MANUFACTURE-HMI-070", "HMI-070", 2, 3),
        ("MANUFACTURE-GW-EDGE-200", "GW-EDGE-200", 1, 4),
    ):
        product = next(row for row in products if row["item"] == item_code)
        ensure_stock_entry(
            marker,
            company,
            "Manufacture",
            stock_items_for_product(product, quantity, stores, finished_goods),
            posting_time=demo_time(offset_minutes),
            bom_no=bom_names[item_code],
        )

    ensure_stock_entry(
        "ISSUE-DAMAGED-ENCLOSURE",
        company,
        "Material Issue",
        [
            {
                "item_code": "CASE-GW-200",
                "qty": 1,
                "s_warehouse": stores,
                "uom": "Nos",
                "stock_uom": "Nos",
                "conversion_factor": 1,
            }
        ],
        posting_time=demo_time(5),
    )


def ensure_opportunity(scenario: dict[str, Any], company: str, customer: str, product: str) -> None:
    order = scenario["order"]
    insert_missing(
        "Opportunity Type",
        "Sales",
        {"description": "Sales opportunity"},
    )
    insert_missing(
        "Sales Stage",
        "Prospecting",
        {"stage_name": "Prospecting"},
    )
    insert_missing(
        "Opportunity",
        order["opportunity"],
        {
            "opportunity_from": "Customer",
            "party_name": customer,
            "customer_name": customer,
            "company": company,
            "currency": scenario["scenario"]["currency"],
            "transaction_date": nowdate(),
            "expected_closing": order["delivery_date"],
            "opportunity_type": "Sales",
            "sales_stage": "Prospecting",
            "status": "Open",
            "with_items": 1,
            "title": f"{product} Revision {order['revision']} – Demofall",
            "items": [
                {
                    "item_code": product,
                    "item_name": order["product_name"],
                    "description": f"Revision {order['revision']}",
                    "qty": order["quantity"],
                    "uom": "Nos",
                    "rate": order["unit_price"],
                    "amount": order["total"],
                }
            ],
        },
    )


def seed() -> None:
    scenario = load_scenario()
    company = scenario["scenario"]["company"]
    currency = scenario["scenario"]["currency"]

    ensure_company(company, currency)
    ensure_fiscal_years(company)
    customer, _, _ = ensure_parties(scenario)

    stores = warehouse_for(company, "default_warehouse", "Stores")
    finished_goods = warehouse_for(company, "default_fg_warehouse", "Finished Goods")
    work_in_progress = warehouse_for(company, "default_wip_warehouse", "Work In Progress")
    set_single_if_present("Stock Settings", {"default_warehouse": stores})

    product, bom_rows = ensure_items(scenario, company, stores)
    ensure_prices(scenario, currency, bom_rows)
    extra_products = ensure_additional_products(company, currency, stores)
    operations = ensure_workstations_and_operations(scenario)
    ensure_quality_template(product)
    bom_names = {
        product: ensure_bom(
            company,
            product,
            bom_rows,
            operations,
            stores,
            finished_goods,
        )
    }
    for extra_product in extra_products:
        bom_names[extra_product["item"]] = ensure_bom(
            company,
            extra_product["item"],
            extra_product["components"],
            product_operations(extra_product, operations),
            stores,
            finished_goods,
        )
    all_bom_rows = list(bom_rows)
    for extra_product in extra_products:
        all_bom_rows.extend(extra_product["components"])
    ensure_opening_stock(company, all_bom_rows, stores)
    # ERPNext v16 calculates following stock entries from committed ledger rows.
    # Persist setup/opening stock before the separate, idempotently marked demo
    # movements so negative-stock validation sees the newly seeded balances.
    frappe.db.commit()
    ensure_demo_stock_movements(
        company,
        extra_products,
        bom_names,
        stores,
        work_in_progress,
        finished_goods,
    )
    ensure_opportunity(scenario, company, customer, product)

    frappe.db.set_default("setup_complete", "1")
    frappe.clear_cache()
    frappe.db.commit()

    log(f"Completed for site {SITE}")
    log(f"Created: {len(CREATED)}; already present: {len(EXISTING)}")
    for entry in CREATED:
        log(f"created {entry}")
    for note in NOTES:
        log(f"note: {note}")
    log("Manual process starts at CRM > Opportunity > OPP-2027-0018")


def main() -> int:
    # Frappe's file logger resolves ../logs relative to the sites directory.
    # Bench commands use the same working directory before initialising a site.
    os.chdir(SITES_PATH)
    frappe.init(site=SITE, sites_path=SITES_PATH)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        seed()
        return 0
    except Exception:
        frappe.db.rollback()
        log("FAILED; transaction was rolled back")
        traceback.print_exc()
        return 1
    finally:
        frappe.destroy()


if __name__ == "__main__":
    sys.exit(main())
