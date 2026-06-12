"""Mad Planner - Home Assistant Custom Component."""
from __future__ import annotations

import base64
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
IMAGES_DIR = "mad_planner_images"


def get_data_path(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(DATA_FILE))


def get_images_dir(hass: HomeAssistant) -> Path:
    p = Path(hass.config.path(IMAGES_DIR))
    p.mkdir(exist_ok=True)
    return p


def load_data(hass: HomeAssistant) -> dict:
    path = get_data_path(hass)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            data.setdefault("retter", [])
            data.setdefault("personer", [])
            data.setdefault("kogehistorik", [])
            return data
    return {"retter": [], "personer": [], "kogehistorik": []}


def save_data(hass: HomeAssistant, data: dict) -> None:
    path = get_data_path(hass)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    hass.http.register_view(MadPlannerRetterView(hass))
    hass.http.register_view(MadPlannerRetView(hass))
    hass.http.register_view(MadPlannerSoegView(hass))
    hass.http.register_view(MadPlannerPersonerView(hass))
    hass.http.register_view(MadPlannerPersonView(hass))
    hass.http.register_view(MadPlannerBilledeView(hass))
    hass.http.register_view(MadPlannerBilledeSletView(hass))
    hass.http.register_view(MadPlannerKogehistorikView(hass))
    hass.http.register_view(MadPlannerKogehistorikSletView(hass))

    frontend_path = Path(__file__).parent / "frontend"
    try:
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([
            StaticPathConfig("/mad-plan-static", str(frontend_path), False),
            StaticPathConfig("/mad-plan-images", str(get_images_dir(hass)), False),
        ])
    except Exception:
        hass.http.register_static_path("/mad-plan-static", str(frontend_path), False)
        hass.http.register_static_path("/mad-plan-images", str(get_images_dir(hass)), False)

    from homeassistant.components.panel_custom import async_register_panel
    await async_register_panel(
        hass,
        component_name="mad-plan-panel",
        sidebar_title="Mad Planner",
        sidebar_icon="mdi:food-fork-drink",
        frontend_url_path="mad-plan",
        require_admin=False,
        config=None,
        js_url="/mad-plan-static/panel.js",
        embed_iframe=False,
        trust_external=False,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return True


# ── Retter ────────────────────────────────────────────────────────────

class MadPlannerRetterView(HomeAssistantView):
    url = "/api/mad-plan/retter"
    name = "api:mad-plan:retter"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data["retter"])

    async def post(self, request):
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        ret = {
            "id": str(uuid.uuid4()),
            "navn": body.get("navn", ""),
            "ingredienser": body.get("ingredienser", []),
            "kategorier": body.get("kategorier", []),
            "beskrivelse": body.get("beskrivelse", ""),
            "personer": body.get("personer", []),
            "billeder": [],
        }
        data["retter"].append(ret)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(ret, status_code=201)


class MadPlannerRetView(HomeAssistantView):
    url = "/api/mad-plan/retter/{ret_id}"
    name = "api:mad-plan:ret"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def put(self, request, ret_id):
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
                    "billeder": ret.get("billeder", []),
                }
                await self.hass.async_add_executor_job(save_data, self.hass, data)
                return self.json(data["retter"][i])
        return self.json({"error": "Ikke fundet"}, status_code=404)

    async def delete(self, request, ret_id):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        # Delete associated images
        images_dir = get_images_dir(self.hass)
        ret = next((r for r in data["retter"] if r["id"] == ret_id), None)
        if ret:
            for bil in ret.get("billeder", []):
                img_path = images_dir / bil["filename"]
                if img_path.exists():
                    img_path.unlink()
        orig = len(data["retter"])
        data["retter"] = [r for r in data["retter"] if r["id"] != ret_id]
        if len(data["retter"]) == orig:
            return self.json({"error": "Ikke fundet"}, status_code=404)
        # Delete kogehistorik for this ret
        data["kogehistorik"] = [k for k in data.get("kogehistorik", []) if k.get("ret_id") != ret_id]
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})


# ── Søg ───────────────────────────────────────────────────────────────

class MadPlannerSoegView(HomeAssistantView):
    url = "/api/mad-plan/soeg"
    name = "api:mad-plan:soeg"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request):
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


# ── Billeder ──────────────────────────────────────────────────────────

class MadPlannerBilledeView(HomeAssistantView):
    """Upload et billede til en ret (multipart/form-data eller base64 JSON)."""
    url = "/api/mad-plan/retter/{ret_id}/billeder"
    name = "api:mad-plan:billeder"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def post(self, request, ret_id):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        ret = next((r for r in data["retter"] if r["id"] == ret_id), None)
        if not ret:
            return self.json({"error": "Ret ikke fundet"}, status_code=404)

        images_dir = get_images_dir(self.hass)
        content_type = request.content_type or ""

        if "multipart" in content_type:
            reader = await request.multipart()
            field = await reader.next()
            if field is None:
                return self.json({"error": "Ingen fil"}, status_code=400)
            original_name = field.filename or "billede.jpg"
            ext = Path(original_name).suffix.lower() or ".jpg"
            filename = f"{ret_id}_{uuid.uuid4().hex[:8]}{ext}"
            img_path = images_dir / filename
            with open(img_path, "wb") as f:
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)
        else:
            body = await request.json()
            b64 = body.get("data", "")
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            ext = body.get("ext", ".jpg")
            filename = f"{ret_id}_{uuid.uuid4().hex[:8]}{ext}"
            img_path = images_dir / filename
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(b64))

        billede = {"id": str(uuid.uuid4()), "filename": filename, "url": f"/mad-plan-images/{filename}"}
        ret.setdefault("billeder", []).append(billede)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(billede, status_code=201)


class MadPlannerBilledeSletView(HomeAssistantView):
    url = "/api/mad-plan/retter/{ret_id}/billeder/{billede_id}"
    name = "api:mad-plan:billede_slet"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def delete(self, request, ret_id, billede_id):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        ret = next((r for r in data["retter"] if r["id"] == ret_id), None)
        if not ret:
            return self.json({"error": "Ret ikke fundet"}, status_code=404)
        bil = next((b for b in ret.get("billeder", []) if b["id"] == billede_id), None)
        if not bil:
            return self.json({"error": "Billede ikke fundet"}, status_code=404)
        img_path = get_images_dir(self.hass) / bil["filename"]
        if img_path.exists():
            img_path.unlink()
        ret["billeder"] = [b for b in ret["billeder"] if b["id"] != billede_id]
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})


# ── Kogehistorik ──────────────────────────────────────────────────────

class MadPlannerKogehistorikView(HomeAssistantView):
    url = "/api/mad-plan/kogehistorik"
    name = "api:mad-plan:kogehistorik"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data.get("kogehistorik", []))

    async def post(self, request):
        body = await request.json()
        ret_id = body.get("ret_id")
        dato = body.get("dato")  # ISO date string: "2024-12-31"
        if not ret_id or not dato:
            return self.json({"error": "ret_id og dato er påkrævet"}, status_code=400)
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        ret = next((r for r in data["retter"] if r["id"] == ret_id), None)
        if not ret:
            return self.json({"error": "Ret ikke fundet"}, status_code=404)
        entry = {"id": str(uuid.uuid4()), "ret_id": ret_id, "dato": dato}
        data.setdefault("kogehistorik", []).append(entry)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(entry, status_code=201)


class MadPlannerKogehistorikSletView(HomeAssistantView):
    url = "/api/mad-plan/kogehistorik/{entry_id}"
    name = "api:mad-plan:kogehistorik_slet"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def delete(self, request, entry_id):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        orig = len(data.get("kogehistorik", []))
        data["kogehistorik"] = [k for k in data.get("kogehistorik", []) if k["id"] != entry_id]
        if len(data["kogehistorik"]) == orig:
            return self.json({"error": "Ikke fundet"}, status_code=404)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})


# ── Personer ──────────────────────────────────────────────────────────

class MadPlannerPersonerView(HomeAssistantView):
    url = "/api/mad-plan/personer"
    name = "api:mad-plan:personer"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def get(self, request):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        return self.json(data["personer"])

    async def post(self, request):
        body = await request.json()
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        person = {"id": str(uuid.uuid4()), "navn": body.get("navn", "").strip()}
        if not person["navn"]:
            return self.json({"error": "Navn mangler"}, status_code=400)
        data["personer"].append(person)
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json(person, status_code=201)


class MadPlannerPersonView(HomeAssistantView):
    url = "/api/mad-plan/personer/{person_id}"
    name = "api:mad-plan:person"
    requires_auth = True

    def __init__(self, hass):
        self.hass = hass

    async def delete(self, request, person_id):
        data = await self.hass.async_add_executor_job(load_data, self.hass)
        orig = len(data["personer"])
        data["personer"] = [p for p in data["personer"] if p["id"] != person_id]
        if len(data["personer"]) == orig:
            return self.json({"error": "Ikke fundet"}, status_code=404)
        for ret in data["retter"]:
            ret["personer"] = [p for p in ret.get("personer", []) if p != person_id]
        await self.hass.async_add_executor_job(save_data, self.hass, data)
        return self.json({"success": True})
