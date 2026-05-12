"""Helper to register static files for Mad Planner."""
import os
from pathlib import Path
from homeassistant.components.http import StaticPathConfig


async def async_register_static_paths(hass):
    """Register static paths for the frontend."""
    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths([
        StaticPathConfig("/mad_planner_static", str(frontend_path), False)
    ])
