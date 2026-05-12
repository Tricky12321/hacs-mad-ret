"""Config flow for Mad Planner."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import voluptuous as vol

DOMAIN = "mad_planner"


class MadPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mad Planner."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Mad Planner", data={})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
