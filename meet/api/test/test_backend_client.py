import json
from unittest import TestCase
from unittest.mock import Mock, patch

from meet.client.meet_backend_client import MeetBackendClient, MeetBackendError
from meet.utils.user import validate_guest_name


class TestMeetBackendClient(TestCase):
	def setUp(self):
		self.client = MeetBackendClient(
			{
				"base_url": "https://meet.nextgrp.vn",
				"api_key": "test-key",
				"api_secret": "test-secret",
			}
		)

	@patch("meet.client.meet_backend_client.requests.post")
	def test_call_uses_remote_frappe_auth_and_returns_message(self, post):
		response = Mock(ok=True)
		response.json.return_value = {"message": "meeting-id"}
		post.return_value = response

		result = self.client.call("meet.api.meeting.create", {"meeting_title": "Review"})

		self.assertEqual(result, "meeting-id")
		post.assert_called_once_with(
			"https://meet.nextgrp.vn/api/method/meet.api.meeting.create",
			json={"meeting_title": "Review"},
			headers={"Authorization": "token test-key:test-secret"},
			timeout=(3.05, 15),
			allow_redirects=False,
		)

	@patch("meet.client.meet_backend_client.requests.post")
	def test_call_rejects_http_errors(self, post):
		response = Mock(ok=False, status_code=403)
		post.return_value = response

		with self.assertRaisesRegex(MeetBackendError, "HTTP 403"):
			self.client.call("meet.api.meeting.create", {})

	@patch("meet.client.meet_backend_client.requests.post")
	def test_call_preserves_frappe_validation_message_without_raw_payload(self, post):
		response = Mock(ok=False, status_code=417)
		response.json.return_value = {
			"_server_messages": json.dumps([json.dumps({"message": "Callback host must match the registered site"})]),
			"exception": "Traceback with internal details",
		}
		post.return_value = response

		with self.assertRaisesRegex(MeetBackendError, "Callback host must match the registered site") as error:
			self.client.call("meet.api.integration.configure_presence_callback", {})
		self.assertNotIn("Traceback", str(error.exception))


class TestGuestNameValidation(TestCase):
	def test_accepts_vietnamese_display_names(self):
		self.assertEqual(validate_guest_name("Nguyễn Văn An"), (True, None))
