# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe


def get_sfu_config():
	"""Get SFU configuration from site config or defaults"""
	site_host = frappe.conf.get("host_name")
	sfu_server_port = frappe.conf.get("socketio_port")
	if ":" in site_host.replace("://", ""):
		from urllib.parse import urlparse

		parsed = urlparse(site_host)
		site_host = f"{parsed.scheme}://{parsed.hostname}"

	return {
		"sfu_server_url": frappe.conf.get("sfu_server_url", site_host),
		"sfu_server_port": frappe.conf.get("sfu_server_port", sfu_server_port),
		"sfu_secret": frappe.conf.get("sfu_secret", ""),
	}
