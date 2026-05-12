"""Mad Planner - Home Assistant Custom Component."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

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
            return json.load(f)
    return {"retter": []}


def save_data(hass: HomeAssistant, data: dict) -> None:
    path = get_data_path(hass)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Mad Planner component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mad Planner from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Register API views
    hass.http.register_view(MadPlannerRetterView(hass))
    hass.http.register_view(MadPlannerRetView(hass))
    hass.http.register_view(MadPlannerSoegView(hass))

    # Register the frontend panel
    hass.components.frontend.async_register_built_in_panel(
        component_name="iframe",
        sidebar_title="Mad Planner",
        sidebar_icon="mdi:food-fork-drink",
        frontend_url_path="mad-planner",
        config={"url": "/mad_planner_static/index.html"},
        require_admin=False,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


class MadPlannerRetterView(HomeAssistantView):
    """View to handle listing and creating retter."""

    url = "/api/mad_planner/retter"
    name = "api:mad_planner:retter"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data["retter"])

    async def post(self, request: web.Request) -> web.Response:
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)

        import uuid
        ret = {
            "id": str(uuid.uuid4()),
            "navn": body.get("navn", ""),
            "ingredienser": body.get("ingredienser", []),
            "kategorier": body.get("kategorier", []),
            "beskrivelse": body.get("beskrivelse", ""),
        }
        data["retter"].append(ret)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(ret, status_code=201)


class MadPlannerRetView(HomeAssistantView):
    """View to handle single ret operations."""

    url = "/api/mad_planner/retter/{ret_id}"
    name = "api:mad_planner:ret"
    requires_auth = True

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
                }
                await self.hass.async_add_executor_job(save_data, self.hass, data)
                return self.json(data["retter"][i])

        return self.json({"error": "Ikke fundet"}, status_code=404)

    async def delete(self, request: web.Request, ret_id: str) -> web.Response:
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        original_len = len(data["retter"])
        data["retter"] = [r for r in data["retter"] if r["id"] != ret_id]

        if len(data["retter"]) == original_len:
            return self.json({"error": "Ikke fundet"}, status_code=404)

        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})


class MadPlannerSoegView(HomeAssistantView):
    """View to search/filter retter by ingredients and categories."""

    url = "/api/mad_planner/soeg"
    name = "api:mad_planner:soeg"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        body = await request.json()
        soeg_ingredienser = [i.lower().strip() for i in body.get("ingredienser", [])]
        soeg_kategorier = [k.lower().strip() for k in body.get("kategorier", [])]

        data = await self.hass.async_add_executor_job(load_data, self.hass)
        resultater = []

        for ret in data["retter"]:
            ret_ing = [i.lower().strip() for i in ret.get("ingredienser", [])]
            ret_kat = [k.lower().strip() for k in ret.get("kategorier", [])]

            ing_matches = sum(1 for i in soeg_ingredienser if any(i in ri or ri in i for ri in ret_ing))
            kat_matches = sum(1 for k in soeg_kategorier if k in ret_kat)
            total_matches = ing_matches + kat_matches

            # Include all if no filters, otherwise only those with at least 1 match
            if not soeg_ingredienser and not soeg_kategorier:
                total_matches = 0  # Show all
                resultater.append({**ret, "matches": 0})
            elif total_matches > 0:
                resultater.append({**ret, "matches": total_matches, "ing_matches": ing_matches, "kat_matches": kat_matches})

        resultater.sort(key=lambda x: x.get("matches", 0), reverse=True)
        return self.json(resultater)


async def async_setup_static(hass: HomeAssistant) -> None:
    """Register static files."""
    from pathlib import Path
    frontend_path = Path(__file__).parent / "frontend"
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([
            StaticPathConfig("/mad_planner_static", str(frontend_path), False)
        ])
    except Exception:
        pass
