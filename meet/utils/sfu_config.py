# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json
from pathlib import Path

import frappe

_RUNTIME_PORT_FILE = Path(frappe.get_app_path("meet")).parent / "sfu-server" / ".runtime-port.json"


def _read_runtime_port() -> int | None:
	try:
		if _RUNTIME_PORT_FILE.exists():
			with _RUNTIME_PORT_FILE.open("r", encoding="utf-8") as f:
				data = json.load(f)
			port = data.get("port")
			if isinstance(port, int):
				return port
			if isinstance(port, str) and port.isdigit():
				return int(port)
	except Exception:
		return None
	return None


def get_sfu_config():
	"""Get SFU configuration from runtime port file, site config or defaults"""
	site_host = frappe.conf.get("host_name")
	runtime_port = _read_runtime_port()
	sfu_server_port = runtime_port
	if site_host and ":" in site_host.replace("://", ""):
		from urllib.parse import urlparse

		parsed = urlparse(site_host)
		site_host = f"{parsed.scheme}://{parsed.hostname}"

	return {
		"sfu_server_url": frappe.conf.get("sfu_server_url", site_host),
		"sfu_server_port": sfu_server_port,
		"sfu_secret": frappe.conf.get("sfu_secret", ""),
	}
