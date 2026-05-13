"""Mad Planner - Home Assistant Custom Component."""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantView
from aiohttp import web

_LOGGER = logging.getLogger(__name__)
DOMAIN = "mad_planner"
DATA_FILE = "mad_planner_data.json"


def get_data_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DATA_FILE))


def load_data(hass: HomeAssistant) -> dict:
    path = get_data_path(hass)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("retter", [])
            data.setdefault("personer", [])
            return data
    return {"retter": [], "personer": []}


def save_data(hass: HomeAssistant, data: dict) -> None:
    path = get_data_path(hass)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # Register API views
    hass.http.register_view(MadPlannerRetterView(hass))
    hass.http.register_view(MadPlannerRetView(hass))
    hass.http.register_view(MadPlannerSoegView(hass))
    hass.http.register_view(MadPlannerPersonerView(hass))
    hass.http.register_view(MadPlannerPersonView(hass))

    # Register static files for the frontend
    frontend_path = Path(__file__).parent / "frontend"
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([
            StaticPathConfig("/mad_planner_static", str(frontend_path), False)
        ])
    except Exception:
        hass.http.register_static_path("/mad_planner_static", str(frontend_path), False)

    # Register the frontend panel
    from homeassistant.components import frontend
    frontend.async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Mad Planner",
        sidebar_icon="mdi:food-fork-drink",
        frontend_url_path="mad-planner",
        config={"url": "/mad_planner_static/index.html"},
        require_admin=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


# ── Retter ────────────────────────────────────────────────────────────

class MadPlannerRetterView(HomeAssistantView):
    url = "/api/mad_planner/retter"
    name = "api:mad_planner:retter"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data["retter"])

    async def post(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        ret = {
            "id": str(uuid.uuid4()),
            "navn": body.get("navn", ""),
            "ingredienser": body.get("ingredienser", []),
            "kategorier": body.get("kategorier", []),
            "beskrivelse": body.get("beskrivelse", ""),
            "personer": body.get("personer", []),
        }
        data["retter"].append(ret)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(ret, status_code=201)


class MadPlannerRetView(HomeAssistantView):
    url = "/api/mad_planner/retter/{ret_id}"
    name = "api:mad_planner:ret"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def put(self, request: web.Request, ret_id: str) -> web.Response:
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        for i, ret in enumerate(data["retter"]):
            if ret["id"] == ret_id:
                data["retter"][i] = {
                    "id": ret_id,
                    "navn": body.get("navn", ret["navn"]),
                    "ingredienser": body.get("ingredienser", ret["ingredienser"]),
                    "kategorier": body.get("kategorier", ret["kategorier"]),
                    "beskrivelse": body.get("beskrivelse", ret.get("beskrivelse", "")),
                    "personer": body.get("personer", ret.get("personer", [])),
                }
                await self.hass.async_add_executor_job(save_data, self.hass, data)
                return self.json(data["retter"][i])
        return self.json({"error": "Ikke fundet"}, status_code=404)

    async def delete(self, request: web.Request, ret_id: str) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        orig = len(data["retter"])
        data["retter"] = [r for r in data["retter"] if r["id"] != ret_id]
        if len(data["retter"]) == orig:
            return self.json({"error": "Ikke fundet"}, status_code=404)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})


# ── Søg ───────────────────────────────────────────────────────────────

class MadPlannerSoegView(HomeAssistantView):
    url = "/api/mad_planner/soeg"
    name = "api:mad_planner:soeg"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        body = await request.json()
        soeg_ing = [i.lower().strip() for i in body.get("ingredienser", [])]
        soeg_kat = [k.lower().strip() for k in body.get("kategorier", [])]
        soeg_personer = body.get("personer", [])

        data = await self.hass.async_add_executor_job(load_data, self.hass)
        resultater = []
        has_filter = bool(soeg_ing or soeg_kat or soeg_personer)

        for ret in data["retter"]:
            ret_ing = [i.lower().strip() for i in ret.get("ingredienser", [])]
            ret_kat = [k.lower().strip() for k in ret.get("kategorier", [])]
            ret_per = ret.get("personer", [])

            ing_matches = sum(1 for i in soeg_ing if any(i in ri or ri in i for ri in ret_ing))
            kat_matches = sum(1 for k in soeg_kat if k in ret_kat)
            per_matches = sum(1 for pid in soeg_personer if pid in ret_per)
            total = ing_matches + kat_matches + per_matches

            if not has_filter:
                resultater.append({**ret, "matches": 0})
            elif total > 0:
                resultater.append({**ret, "matches": total})

        resultater.sort(key=lambda x: x.get("matches", 0), reverse=True)
        return self.json(resultater)


# ── Personer ──────────────────────────────────────────────────────────

class MadPlannerPersonerView(HomeAssistantView):
    url = "/api/mad_planner/personer"
    name = "api:mad_planner:personer"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data["personer"])

    async def post(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        person = {
            "id": str(uuid.uuid4()),
            "navn": body.get("navn", "").strip(),
        }
        if not person["navn"]:
            return self.json({"error": "Navn mangler"}, status_code=400)
        data["personer"].append(person)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(person, status_code=201)


class MadPlannerPersonView(HomeAssistantView):
    url = "/api/mad_planner/personer/{person_id}"
    name = "api:mad_planner:person"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def delete(self, request: web.Request, person_id: str) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        orig = len(data["personer"])
        data["personer"] = [p for p in data["personer"] if p["id"] != person_id]
        if len(data["personer"]) == orig:
            return self.json({"error": "Ikke fundet"}, status_code=404)
        # Remove person from all retter
        for ret in data["retter"]:
            if person_id in ret.get("personer", []):
                ret["personer"] = [p for p in ret["personer"] if p != person_id]
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})
