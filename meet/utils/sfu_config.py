# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.caching import redis_cache
from urllib.parse import urlsplit, urlunsplit


@redis_cache(ttl=5 * 60)
def get_sfu_config():
	"""Read canonical SFU settings, falling back to existing Meet server keys."""
	return {
		"sfu_server_url": frappe.conf.get("sfu_server_url") or frappe.conf.get("meet_server_url", "http://localhost"),
		"sfu_server_port": frappe.conf.get("sfu_server_port") or frappe.conf.get("meet_server_port", 3000),
		"sfu_secret": frappe.conf.get("sfu_secret", ""),
	}


def get_sfu_presence_url():
	"""Use Meet's internal SFU route, falling back to the public SFU URL."""
	settings = get_sfu_config()
	base_url = frappe.conf.get("meet_server_url") or settings["sfu_server_url"]
	port = frappe.conf.get("meet_server_port") or settings["sfu_server_port"]
	return _build_sfu_presence_url(base_url, port)


def _build_sfu_presence_url(base_url, port):
	parsed_url = urlsplit((base_url or "").rstrip("/"))
	if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
		frappe.throw(frappe._("Invalid SFU server URL"), frappe.ValidationError)
	if parsed_url.scheme == "http" and parsed_url.port is None:
		parsed_url = parsed_url._replace(netloc=f"{parsed_url.hostname}:{port}")
	return urlunsplit(parsed_url).rstrip("/") + "/internal/presence"
