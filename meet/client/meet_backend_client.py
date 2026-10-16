"""HTTP transport for the remote Frappe Meet API."""

import json

import requests


class MeetBackendError(Exception):
	"""Raised when the remote Meet service cannot complete a request."""


class MeetBackendClient:
	def __init__(self, settings):
		self.base_url = settings["base_url"]
		self.api_key = settings["api_key"]
		self.api_secret = settings["api_secret"]

	def call(self, method_name, params):
		try:
			response = requests.post(
				f"{self.base_url}/api/method/{method_name}",
				json=params,
				headers={"Authorization": f"token {self.api_key}:{self.api_secret}"},
				timeout=(3.05, 15),
				allow_redirects=False,
			)
		except requests.RequestException as exc:
			raise MeetBackendError("Could not connect to the Meet server") from exc

		try:
			payload = response.json()
		except ValueError:
			payload = {}
		if not response.ok:
			details = _get_frappe_error_messages(payload)
			message = f"Meet server returned HTTP {response.status_code}"
			if details:
				message = f"{message}: {details}"
			raise MeetBackendError(message)
		return payload.get("message", payload)


def _get_frappe_error_messages(payload):
	"""Extract only user-safe Frappe validation messages, never raw response data."""
	raw_messages = payload.get("_server_messages") if isinstance(payload, dict) else None
	if isinstance(raw_messages, str):
		try:
			raw_messages = json.loads(raw_messages)
		except ValueError:
			return ""
	if not isinstance(raw_messages, list):
		return ""

	messages = []
	for raw_message in raw_messages[:3]:
		if isinstance(raw_message, str):
			try:
				raw_message = json.loads(raw_message)
			except ValueError:
				continue
		if isinstance(raw_message, dict) and isinstance(raw_message.get("message"), str):
			text = raw_message["message"].strip()
			if text:
				messages.append(text[:240])
	return "; ".join(messages)
