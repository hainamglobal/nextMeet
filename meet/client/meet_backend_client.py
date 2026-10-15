"""HTTP transport for the remote Frappe Meet API."""

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
			raise MeetBackendError(f"Meet server returned HTTP {response.status_code}")
		return payload.get("message", payload)
