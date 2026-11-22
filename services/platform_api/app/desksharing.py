from __future__ import annotations

from datetime import date
from typing import Any

from .store import ScenarioStore, utc_now


class DesksharingError(RuntimeError):
    pass


class DesksharingNotFoundError(DesksharingError):
    pass


class DesksharingService:
    ACTIVE_STATUSES = {"booked", "checked_in"}
    SLOT_LABELS = {
        "full_day": "Ganztägig",
        "morning": "Vormittag",
        "afternoon": "Nachmittag",
    }

    def __init__(self, store: ScenarioStore) -> None:
        self.store = store

    def dashboard(
        self,
        user_id: str = "USR-001",
        booking_date: str | None = None,
        site_id: str | None = None,
        slot: str = "full_day",
    ) -> dict[str, Any]:
        state = self.store.get()
        selected_date = self._date(booking_date or date.today().isoformat())
        desk_state = self._domain(state)
        user = self._user(state, user_id)
        selected_site = site_id or user.get("site_id") or desk_state["sites"][0]["id"]
        self._site(desk_state, selected_site)
        self._slot(slot)

        bookings = desk_state["bookings"]
        desks = [desk for desk in desk_state["desks"] if desk["site_id"] == selected_site]
        rooms = [room for room in desk_state.get("rooms", []) if room["site_id"] == selected_site]
        visible_desks = []
        for desk in desks:
            collisions = [
                booking
                for booking in bookings
                if booking["desk_id"] == desk["id"]
                and booking["date"] == selected_date
                and booking["status"] in self.ACTIVE_STATUSES
                and self._overlaps(booking["slot"], slot)
            ]
            own = next((item for item in collisions if item["user_id"] == user_id), None)
            occupied = next((item for item in collisions if item["user_id"] != user_id), None)
            item = dict(desk)
            item["availability"] = (
                "mine" if own else "occupied" if occupied else "available"
            )
            item["booking_id"] = own["id"] if own else None
            item["room"] = self._room(desk_state, desk["room_id"])
            visible_desks.append(item)

        my_bookings = [
            self._enrich_booking(state, booking)
            for booking in bookings
            if booking["user_id"] == user_id and booking["status"] != "cancelled"
        ]
        my_bookings.sort(key=lambda item: (item["date"], item["slot"], item["id"]))
        active = sum(item["availability"] != "available" for item in visible_desks)
        available = sum(item["availability"] == "available" for item in visible_desks)
        people = {
            booking["user_id"]
            for booking in bookings
            if booking["date"] == selected_date
            and booking["status"] in self.ACTIVE_STATUSES
            and self._desk(desk_state, booking["desk_id"])["site_id"] == selected_site
        }
        colleague_locations = [
            self._colleague_location(state, booking)
            for booking in bookings
            if booking["user_id"] != user_id
            and booking["date"] == selected_date
            and booking["status"] in self.ACTIVE_STATUSES
            and self._overlaps(booking["slot"], slot)
            and self._desk(desk_state, booking["desk_id"])["site_id"] == selected_site
        ]
        colleague_locations.sort(key=lambda item: (item["user_name"], item["desk_id"]))

        return {
            "selected_date": selected_date,
            "selected_site": selected_site,
            "selected_slot": slot,
            "slot_labels": self.SLOT_LABELS,
            "current_user": self._public_user(user),
            "permissions": {
                "can_manage": self._is_admin(user),
                "can_book": "desksharing-user" in user.get("roles", [])
                or self._is_admin(user),
            },
            "sites": desk_state["sites"],
            "rooms": rooms,
            "metrics": {
                "total_desks": len(visible_desks),
                "available_desks": available,
                "occupied_desks": active,
                "expected_people": len(people),
                "utilization_percent": round(active / len(visible_desks) * 100)
                if visible_desks
                else 0,
            },
            "desks": visible_desks,
            "colleague_locations": colleague_locations,
            "my_bookings": my_bookings,
            "demo_users": [self._public_user(item) for item in state["iam"]["users"]],
        }

    def create_booking(
        self,
        user_id: str,
        desk_id: str,
        booking_date: str,
        slot: str,
        note: str = "",
    ) -> dict[str, Any]:
        parsed_date = self._date(booking_date)
        self._slot(slot)
        if len(note) > 300:
            raise DesksharingError("Notiz darf höchstens 300 Zeichen enthalten")

        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            user = self._user(state, user_id)
            if "desksharing-user" not in user.get("roles", []) and not self._is_admin(user):
                raise DesksharingError("Benutzer darf keine Arbeitsplätze buchen")
            desk = self._desk(domain, desk_id)
            if desk["status"] != "active":
                raise DesksharingError("Arbeitsplatz ist nicht buchbar")

            for booking in domain["bookings"]:
                if (
                    booking["date"] != parsed_date
                    or booking["status"] not in self.ACTIVE_STATUSES
                    or not self._overlaps(booking["slot"], slot)
                ):
                    continue
                if booking["desk_id"] == desk_id:
                    raise DesksharingError("Arbeitsplatz ist im gewählten Zeitraum belegt")
                if booking["user_id"] == user_id:
                    raise DesksharingError(
                        "Benutzer hat im gewählten Zeitraum bereits einen Arbeitsplatz"
                    )

            booking = {
                "id": self._next_id(domain["bookings"]),
                "user_id": user_id,
                "desk_id": desk_id,
                "date": parsed_date,
                "slot": slot,
                "status": "booked",
                "note": note.strip(),
                "created_at": utc_now(),
            }
            domain["bookings"].append(booking)
            self._audit(domain, user_id, "booking_created", booking["id"], desk_id)
            result = self._enrich_booking(state, booking)

        self.store.mutate(operation)
        return result

    def cancel_booking(self, booking_id: str, actor_id: str) -> dict[str, Any]:
        return self._change_booking(booking_id, actor_id, "cancelled", "booking_cancelled")

    def check_in(self, booking_id: str, actor_id: str) -> dict[str, Any]:
        return self._change_booking(booking_id, actor_id, "checked_in", "checked_in")

    def check_out(self, booking_id: str, actor_id: str) -> dict[str, Any]:
        return self._change_booking(booking_id, actor_id, "completed", "checked_out")

    def admin_dashboard(self, actor_id: str) -> dict[str, Any]:
        state = self.store.get()
        actor = self._user(state, actor_id)
        if not self._is_admin(actor):
            raise DesksharingError("Desksharing-Administration erforderlich")
        domain = self._domain(state)
        active = [item for item in domain["bookings"] if item["status"] in self.ACTIVE_STATUSES]
        by_site = []
        for site in domain["sites"]:
            site_desks = {desk["id"] for desk in domain["desks"] if desk["site_id"] == site["id"]}
            site_bookings = [item for item in active if item["desk_id"] in site_desks]
            by_site.append(
                {
                    "site_id": site["id"],
                    "site_name": site["name"],
                    "desks": len(site_desks),
                    "active_bookings": len(site_bookings),
                }
            )
        return {
            "actor": self._public_user(actor),
            "sites": by_site,
            "users": len(state["iam"]["users"]),
            "desks": len(domain["desks"]),
            "bookings": len(domain["bookings"]),
            "audit": list(reversed(domain["audit"][-25:])),
        }

    def reset(self, user_id: str = "USR-001") -> dict[str, Any]:
        self.store.reset_domain("desksharing")
        return self.dashboard(user_id)

    def _change_booking(
        self, booking_id: str, actor_id: str, target: str, audit_action: str
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        def operation(state: dict[str, Any]) -> None:
            nonlocal result
            domain = self._domain(state)
            actor = self._user(state, actor_id)
            booking = next(
                (item for item in domain["bookings"] if item["id"] == booking_id), None
            )
            if booking is None:
                raise DesksharingNotFoundError("Buchung nicht gefunden")
            if booking["user_id"] != actor_id and not self._is_admin(actor):
                raise DesksharingError("Nur eigene Buchungen dürfen geändert werden")
            allowed = {
                "cancelled": {"booked", "checked_in"},
                "checked_in": {"booked"},
                "completed": {"checked_in"},
            }
            if booking["status"] not in allowed[target]:
                raise DesksharingError(
                    f"Buchung mit Status {booking['status']} kann nicht auf {target} gesetzt werden"
                )
            booking["status"] = target
            booking["updated_at"] = utc_now()
            self._audit(domain, actor_id, audit_action, booking_id, booking["desk_id"])
            result = self._enrich_booking(state, booking)

        self.store.mutate(operation)
        return result

    @staticmethod
    def _domain(state: dict[str, Any]) -> dict[str, Any]:
        domain = state.get("desksharing")
        if not isinstance(domain, dict):
            raise DesksharingError("Desksharing-Daten fehlen")
        return domain

    @staticmethod
    def _is_admin(user: dict[str, Any]) -> bool:
        roles = set(user.get("roles", []))
        return bool({"platform-admin", "desksharing-admin"} & roles)

    @staticmethod
    def _public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {
            key: user.get(key)
            for key in ("id", "username", "name", "department", "site_id", "roles", "manager")
        }

    @staticmethod
    def _site(domain: dict[str, Any], site_id: str) -> dict[str, Any]:
        site = next((item for item in domain["sites"] if item["id"] == site_id), None)
        if site is None:
            raise DesksharingNotFoundError("Standort nicht gefunden")
        return site

    @staticmethod
    def _desk(domain: dict[str, Any], desk_id: str) -> dict[str, Any]:
        desk = next((item for item in domain["desks"] if item["id"] == desk_id), None)
        if desk is None:
            raise DesksharingNotFoundError("Arbeitsplatz nicht gefunden")
        return desk

    @staticmethod
    def _room(domain: dict[str, Any], room_id: str) -> dict[str, Any]:
        room = next((item for item in domain.get("rooms", []) if item["id"] == room_id), None)
        if room is None:
            raise DesksharingNotFoundError("Raum nicht gefunden")
        return room

    @staticmethod
    def _user(state: dict[str, Any], user_id: str) -> dict[str, Any]:
        if user_id == "platform-admin":
            return {
                "id": "platform-admin",
                "username": "platform-admin",
                "name": "Plattform Administrator",
                "department": "IT",
                "site_id": "BER",
                "roles": ["platform-admin"],
                "manager": True,
            }
        user = next(
            (item for item in state.get("iam", {}).get("users", []) if item["id"] == user_id),
            None,
        )
        if user is None:
            raise DesksharingNotFoundError("Benutzer nicht gefunden")
        return user

    def _enrich_booking(self, state: dict[str, Any], booking: dict[str, Any]) -> dict[str, Any]:
        domain = self._domain(state)
        desk = self._desk(domain, booking["desk_id"])
        user = self._user(state, booking["user_id"])
        site = self._site(domain, desk["site_id"])
        result = dict(booking)
        result.update(
            {
                "slot_label": self.SLOT_LABELS[booking["slot"]],
                "desk_label": desk["label"],
                "site_id": site["id"],
                "site_name": site["name"],
                "user_name": user["name"],
                "floor": desk["floor"],
                "room_id": desk["room_id"],
                "room_name": self._room(domain, desk["room_id"])["name"],
            }
        )
        return result

    def _colleague_location(
        self, state: dict[str, Any], booking: dict[str, Any]
    ) -> dict[str, Any]:
        domain = self._domain(state)
        desk = self._desk(domain, booking["desk_id"])
        room = self._room(domain, desk["room_id"])
        user = self._user(state, booking["user_id"])
        return {
            "user_id": user["id"],
            "user_name": user["name"],
            "department": user["department"],
            "booking_status": booking["status"],
            "slot": booking["slot"],
            "slot_label": self.SLOT_LABELS[booking["slot"]],
            "desk_id": desk["id"],
            "desk_label": desk["label"],
            "floor": desk["floor"],
            "room_id": room["id"],
            "room_name": room["name"],
            "map_x": desk["map_x"],
            "map_y": desk["map_y"],
        }

    @staticmethod
    def _date(value: str) -> str:
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise DesksharingError("Datum muss im Format YYYY-MM-DD vorliegen") from exc

    def _slot(self, value: str) -> None:
        if value not in self.SLOT_LABELS:
            raise DesksharingError("Unbekanntes Zeitfenster")

    @staticmethod
    def _overlaps(left: str, right: str) -> bool:
        return left == "full_day" or right == "full_day" or left == right

    @staticmethod
    def _next_id(bookings: list[dict[str, Any]]) -> str:
        numbers = [
            int(item["id"].split("-")[-1])
            for item in bookings
            if item.get("id", "").startswith("DSB-")
            and item["id"].split("-")[-1].isdigit()
        ]
        return f"DSB-{max(numbers, default=0) + 1:04d}"

    @staticmethod
    def _audit(
        domain: dict[str, Any], actor_id: str, action: str, booking_id: str, desk_id: str
    ) -> None:
        domain["audit"].append(
            {
                "timestamp": utc_now(),
                "actor_id": actor_id,
                "action": action,
                "booking_id": booking_id,
                "desk_id": desk_id,
            }
        )
