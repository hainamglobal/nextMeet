# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
import jwt
import requests
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from meet.api.integration import record_meeting_guest
from meet.api.meeting import (
	_relay_presence_callback,
	_resolve_meeting_host_name,
	get_approved_guest_connection_details,
	get_join_status,
	get_sfu_connection_details,
	delete_mtp_meeting,
	invite_meeting_user,
	get_my_meeting_invitations,
	get_user_meeting,
	get_user_meetings,
	respond_meeting_invitation,
	_has_accepted_invitation,
)


class IntegrationTestMeetingApi(IntegrationTestCase):
	def setUp(self):
		frappe.conf.sfu_secret = "test-sfu-secret"

		self.host_email = "host-meet@example.com"
		self.member_email = "member-meet@example.com"
		self.outsider_email = "outsider-meet@example.com"

		for email, first_name in (
			(self.host_email, "Host"),
			(self.member_email, "Member"),
			(self.outsider_email, "Outsider"),
		):
			self._ensure_user(email, first_name)

		self.meeting = self._create_meeting(self.host_email, meeting_type="restricted")

	@patch("meet.api.meeting.frappe.get_all")
	def test_create_meeting_resolves_the_only_registered_mtp_site(self, get_all):
		get_all.side_effect = [[], ["mtp.example.com"]]

		host_name = _resolve_meeting_host_name(None, self.host_email)

		self.assertEqual(host_name, "mtp.example.com")

	@patch("meet.api.meeting.frappe.get_all")
	def test_create_meeting_uses_creator_mtp_site(self, get_all):
		get_all.return_value = ["mtp-b.example.com"]

		host_name = _resolve_meeting_host_name(None, self.host_email)

		self.assertEqual(host_name, "mtp-b.example.com")

	@patch("meet.api.meeting.frappe.get_all")
	def test_create_meeting_rejects_ambiguous_mtp_site(self, get_all):
		get_all.side_effect = [[], ["mtp-a.example.com", "mtp-b.example.com"]]

		with self.assertRaises(frappe.ValidationError):
			_resolve_meeting_host_name(None, self.host_email)

	def test_member_can_get_sfu_connection_details(self):
		self.meeting.add_user_to_table("members", self.member_email, save=True, ignore_permissions=True)

		frappe.set_user(self.member_email)

		result = get_sfu_connection_details(self.meeting.name)

		self.assertEqual(result["user_id"], self.member_email)
		self.assertEqual(result["meeting_id"], self.meeting.name)
		self.assertTrue(result["auth_token"])

	def test_restricted_meeting_non_member_cannot_get_sfu_connection_details(self):
		frappe.set_user(self.outsider_email)

		with self.assertRaises(frappe.PermissionError):
			get_sfu_connection_details(self.meeting.name)

	def test_mtp_meeting_delete_is_soft_and_only_creator_can_delete(self):
		self.meeting.host_name = frappe.local.site
		self.meeting.created_by_email = self.host_email
		self.meeting.save(ignore_permissions=True)

		with self.assertRaises(frappe.PermissionError):
			delete_mtp_meeting(self.meeting.name, actor_email=self.member_email, expected_host_name=frappe.local.site)

		self.assertFalse(self.meeting.reload().is_deleted)

		result = delete_mtp_meeting(
			self.meeting.name,
			actor_email=self.host_email,
			expected_host_name=frappe.local.site,
		)

		self.assertTrue(result["deleted"])
		self.assertTrue(frappe.db.exists("Sae Meeting", self.meeting.name))
		self.assertTrue(self.meeting.reload().is_deleted)
		self.assertFalse(self.meeting.can_join(self.host_email))

	def test_meeting_invitation_is_recorded_and_response_is_saved(self):
		self.meeting.host_name = frappe.local.site
		self.meeting.created_by_email = self.host_email
		self.meeting.save(ignore_permissions=True)
		frappe.set_user(self.host_email)

		invitation = invite_meeting_user(
			self.meeting.name,
			self.member_email,
			actor_email=self.host_email,
			actor_name="Meeting Host",
			expected_host_name=frappe.local.site,
		)
		self.assertEqual(invitation["status"], "Invited")
		self.assertEqual(len(get_my_meeting_invitations(self.member_email, frappe.local.site)), 1)

		frappe.set_user(self.member_email)
		result = respond_meeting_invitation(
			self.meeting.name,
			invitation["invitation_id"],
			"Accepted",
			invitee_email=self.member_email,
			expected_host_name=frappe.local.site,
		)
		self.assertEqual(result["status"], "Accepted")
		self.meeting.reload()
		self.assertTrue(_has_accepted_invitation(self.meeting, self.member_email))
		self.assertEqual(self.meeting.invitations[0].status, "Accepted")

	def test_user_meeting_list_contains_only_created_and_attended_meetings(self):
		host_name = frappe.local.site
		created = self._create_meeting(self.member_email)
		created.host_name = host_name
		created.created_by_email = self.member_email
		created.save(ignore_permissions=True)

		joined = self._create_meeting(self.host_email)
		joined.host_name = host_name
		joined.created_by_email = self.host_email
		joined.add_user_to_table("members", "guest_member_session")
		joined.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Domain",
				"meeting": joined.name,
				"host_name": host_name,
				"user_email": self.member_email,
				"user_name": "Member",
				"user_id": "guest_member_session",
			}
		).insert(ignore_permissions=True)

		member_only = self._create_meeting(self.host_email)
		member_only.host_name = host_name
		member_only.created_by_email = self.host_email
		member_only.add_user_to_table("members", self.member_email)
		member_only.save(ignore_permissions=True)

		pending = self._create_meeting(self.host_email)
		pending.host_name = host_name
		pending.created_by_email = self.host_email
		pending.save(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "User Domain",
				"meeting": pending.name,
				"host_name": host_name,
				"user_email": self.member_email,
				"user_name": "Member",
			}
		).insert(ignore_permissions=True)

		unrelated = self._create_meeting(self.outsider_email)
		unrelated.host_name = host_name
		unrelated.created_by_email = self.outsider_email
		unrelated.save(ignore_permissions=True)

		other_site = self._create_meeting(self.member_email)
		other_site.host_name = "another-site.example"
		other_site.created_by_email = self.member_email
		other_site.save(ignore_permissions=True)

		frappe.set_user(self.member_email)
		rows = get_user_meetings(self.member_email, expected_host_name=host_name)
		meetings = {row.name: row for row in rows}

		self.assertEqual(set(meetings), {created.name, joined.name, member_only.name})
		self.assertTrue(meetings[created.name].is_created_by_me)
		self.assertTrue(meetings[created.name].is_participant)
		self.assertFalse(meetings[created.name].has_started)
		self.assertFalse(meetings[joined.name].is_created_by_me)
		self.assertTrue(meetings[joined.name].is_participant)
		self.assertTrue(meetings[joined.name].has_started)
		self.assertTrue(meetings[member_only.name].is_participant)
		self.assertTrue(meetings[member_only.name].has_started)

		self.assertEqual(get_user_meeting(joined.name, self.member_email, host_name).name, joined.name)
		with self.assertRaises(frappe.PermissionError):
			get_user_meeting(joined.name, self.outsider_email, host_name)

	def test_guest_attendance_is_recorded_and_listed_by_meeting_code(self):
		host_name = frappe.local.site
		meeting = self._create_meeting(self.host_email)
		meeting.host_name = host_name
		meeting.created_by_email = self.host_email
		meeting.save(ignore_permissions=True)

		record_meeting_guest(
			meeting,
			"Member",
			guest_id="guest_member_attended",
			guest_email=self.member_email,
		)

		rows = get_user_meetings(self.member_email, expected_host_name=host_name)
		listed_meeting = next(row for row in rows if row.name == meeting.name)
		attendance = frappe.get_all(
			"User Domain",
			filters={"meeting": meeting.name, "user_id": "guest_member_attended"},
			fields=["user_email"],
			limit=1,
		)

		self.assertEqual(attendance[0].user_email, self.member_email)
		self.assertTrue(listed_meeting.is_participant)

	def test_expired_meeting_invitation_can_be_resent_after_five_minutes(self):
		self.meeting.host_name = frappe.local.site
		self.meeting.created_by_email = self.host_email
		self.meeting.save(ignore_permissions=True)
		frappe.set_user(self.host_email)

		first = invite_meeting_user(
			self.meeting.name,
			self.member_email,
			actor_email=self.host_email,
			expected_host_name=frappe.local.site,
		)
		self.meeting.reload()
		self.meeting.invitations[0].invited_on = add_to_date(now_datetime(), minutes=-6)
		self.meeting.save(ignore_permissions=True)

		second = invite_meeting_user(
			self.meeting.name,
			self.member_email,
			actor_email=self.host_email,
			expected_host_name=frappe.local.site,
		)

		self.meeting.reload()
		self.assertNotEqual(first["invitation_id"], second["invitation_id"])
		self.assertEqual([row.status for row in self.meeting.invitations], ["Expired", "Invited"])

	def test_restricted_meeting_creator_joins_without_approval(self):
		self.meeting.created_by_email = self.member_email
		self.meeting.save(ignore_permissions=True)

		result = self.meeting.join(self.member_email)

		self.assertEqual(result["status"], "joined")
		self.assertIn(self.member_email, self.meeting.get_members())

	def test_restricted_meeting_other_user_still_waits_for_approval(self):
		self.meeting.created_by_email = self.member_email
		self.meeting.save(ignore_permissions=True)

		result = self.meeting.join(self.outsider_email)

		self.assertEqual(result["status"], "waiting_for_approval")
		self.assertNotIn(self.outsider_email, self.meeting.get_members())

	def test_join_status_tracks_waiting_and_approved_users(self):
		self.meeting.join(self.outsider_email)
		frappe.set_user(self.outsider_email)

		self.assertEqual(get_join_status(self.meeting.name)["status"], "waiting_for_approval")

		self.meeting.approve_user(self.outsider_email, approved_by=self.host_email)

		self.assertEqual(get_join_status(self.meeting.name)["status"], "joined")

	@patch("meet.api.meeting.get_guest_session")
	def test_guest_connection_status_stays_waiting_until_host_approves(self, get_guest_session):
		guest_id = "guest_realtime_test"
		get_guest_session.return_value = {
			"guest_id": guest_id,
			"meeting_id": self.meeting.name,
			"guest_name": "Realtime Guest",
		}
		self.meeting.append("waiting_room", {"user": guest_id, "user_name": "Realtime Guest"})
		self.meeting.save(ignore_permissions=True)

		result = get_approved_guest_connection_details(self.meeting.name, guest_id)

		self.assertEqual(result["status"], "waiting_for_approval")
		self.assertEqual(result["guest_id"], guest_id)
		self.assertNotIn("auth_token", result)

	@patch("meet.api.meeting.get_guest_session")
	def test_guest_connection_status_reports_a_missed_rejection(self, get_guest_session):
		guest_id = "guest_realtime_test"
		get_guest_session.return_value = {
			"guest_id": guest_id,
			"meeting_id": self.meeting.name,
			"guest_name": "Realtime Guest",
		}
		self.meeting.append("banned_users", {"user": guest_id})
		self.meeting.save(ignore_permissions=True)

		result = get_approved_guest_connection_details(self.meeting.name, guest_id)

		self.assertEqual(result["status"], "rejected")

	def test_sfu_token_includes_site_claim(self):
		"""The SFU JWT must carry the source site so the SFU can namespace rooms
		across multiple frappe sites sharing one SFU instance."""
		self.meeting.add_user_to_table("members", self.member_email, save=True, ignore_permissions=True)

		frappe.set_user(self.member_email)

		result = get_sfu_connection_details(self.meeting.name)

		decoded = jwt.decode(
			result["auth_token"],
			frappe.conf.sfu_secret,
			algorithms=["HS256"],
		)

		self.assertEqual(decoded["site"], frappe.local.site)
		self.assertEqual(decoded["meeting_id"], self.meeting.name)
		self.assertTrue(decoded["presence_callback_url"].endswith("/api/method/meet.api.meeting.sfu_presence_event"))
		self.assertEqual(decoded["presence_host_name"], self.meeting.host_name)

	@patch("meet.api.meeting.time.sleep")
	@patch("meet.api.meeting.requests.post")
	def test_presence_webhook_retries_a_transient_delivery_failure(self, post, sleep):
		failed_response = Mock()
		failed_response.raise_for_status.side_effect = requests.ConnectionError("temporary")
		success_response = Mock()
		post.side_effect = [failed_response, success_response]

		result = _relay_presence_callback(
			"https://nextgrp.example/api/method/nextgrp.next_meet.controller.meet_controller.meet_event",
			{"meeting_id": self.meeting.name, "count": 1},
			"signature",
		)

		self.assertTrue(result)
		self.assertEqual(post.call_count, 2)
		sleep.assert_called_once_with(0.25)

	def test_sfu_token_site_claim_keeps_cross_site_meetings_isolated(self):
		"""Two sites with meetings of the same name must mint tokens that
		carry different `site` claims so the SFU can route them to distinct
		rooms."""
		from meet.api.meeting import _generate_sfu_token

		token_a = _generate_sfu_token(
			user_id="user-a",
			meeting_id="all-hands",
			site="site-a.example.com",
		)
		token_b = _generate_sfu_token(
			user_id="user-b",
			meeting_id="all-hands",
			site="site-b.example.com",
		)

		decoded_a = jwt.decode(token_a, frappe.conf.sfu_secret, algorithms=["HS256"])
		decoded_b = jwt.decode(token_b, frappe.conf.sfu_secret, algorithms=["HS256"])

		self.assertEqual(decoded_a["meeting_id"], decoded_b["meeting_id"])
		self.assertNotEqual(decoded_a["site"], decoded_b["site"])

	def _ensure_user(self, email: str, first_name: str):
		if frappe.db.exists("User", email):
			return frappe.get_doc("User", email)

		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"enabled": 1,
				"new_password": "password",
			}
		)
		user.insert(ignore_permissions=True)
		return user

	def _create_meeting(self, owner: str, meeting_type: str = "open"):
		frappe.set_user(owner)
		meeting = frappe.get_doc(
			{
				"doctype": "Sae Meeting",
				"meeting_type": meeting_type,
				"allow_guest": 1,
			}
		)
		meeting.insert(ignore_permissions=True)
		return meeting
