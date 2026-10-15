"""Settings for the remote Meet backend connection."""

from urllib.parse import urlsplit

import frappe
from frappe import _


DEFAULT_BACKEND_URL = "https://meet.nextgrp.vn"


def get_backend_settings():
	base_url = (frappe.conf.get("meet_backend_url") or DEFAULT_BACKEND_URL).rstrip("/")
	api_key = frappe.conf.get("meet_api_key")
	api_secret = frappe.conf.get("meet_api_secret")
	parsed_url = urlsplit(base_url)

	if not base_url.startswith("https://") and not frappe.conf.get("developer_mode"):
		frappe.throw(_("Meet backend URL must use HTTPS"), frappe.ValidationError)
	if not parsed_url.hostname or parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
		frappe.throw(_("Meet backend URL is invalid"), frappe.ValidationError)
	if not api_key or not api_secret:
		frappe.throw(_("Meet API key and secret are not configured on this site"), frappe.ValidationError)

	return {
		"base_url": base_url,
		"api_key": api_key,
		"api_secret": api_secret,
	}


def get_site_host_name():
	configured_host = frappe.conf.get("host_name") or frappe.local.site
	url = configured_host if "://" in configured_host else f"//{configured_host}"
	host_name = urlsplit(url).hostname
	return (host_name or frappe.local.site).strip().lower().rstrip(".")
