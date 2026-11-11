# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import secrets
import time
import hashlib
import hmac
import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import frappe
import jwt
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import get_datetime, now_datetime

from meet.utils.sfu_config import (
	get_sfu_config,
	get_sfu_presence_callback_url,
	get_sfu_presence_url,
)
from meet.utils.user import (
	get_guest_session,
	get_user_info,
	set_guest_session,
	validate_guest_name,
)

if TYPE_CHECKING:
	from meet.meet.doctype.sae_meeting.sae_meeting import SaeMeeting


def _generate_sfu_token(
	user_id: str,
	meeting_id: str,
	scope: str = "full",
	expires_in: int = 3600,
	**extra,
) -> str:
	"""Generate a JWT token for SFU authentication."""
	sfu_config = get_sfu_config()
	secret = sfu_config.get("sfu_secret") or frappe.conf.get("secret_key")
	if not secret:
		frappe.throw(_("SFU secret not configured"))

	now = int(time.time())
	payload = {
		"user_id": user_id,
		"meeting_id": meeting_id,
		"site": getattr(frappe.local, "site", None),
		"scope": scope,
		"exp": now + expires_in,
		"iat": now,
		**extra,
	}
	if scope == "full":
		payload["presence_callback_url"] = get_sfu_presence_callback_url()
		payload["presence_host_name"] = frappe.db.get_value(
			"Sae Meeting", meeting_id, "host_name"
		) or frappe.local.site
	return jwt.encode(payload, secret, algorithm="HS256")


def _get_codec_strategy() -> str:
	return frappe.get_cached_doc("Sae Settings").codec_strategy or "svc"


def _resolve_meeting_host_name(host_name: str | None, created_by_email: str | None) -> str:
	"""Resolve the MTP tenant for a Meet-created room when no tenant was passed."""
	if host_name:
		return host_name.strip().lower().rstrip(".")

	creator_email = (created_by_email or "").strip().lower()
	if creator_email:
		known_hosts = {
			(host or "").strip().lower().rstrip(".")
			for host in frappe.get_all(
				"User Domain", filters={"user_email": creator_email}, pluck="host_name"
			)
			if host
		}
		if len(known_hosts) == 1:
			return known_hosts.pop()
		if len(known_hosts) > 1:
			frappe.throw(
				_("This user is linked to multiple MTP sites. Open Meet from the intended MTP site."),
				frappe.ValidationError,
			)

	mtp_hosts = frappe.get_all("Meet Domain", pluck="host_name")
	if len(mtp_hosts) == 1:
		return (mtp_hosts[0] or "").strip().lower().rstrip(".")
	if len(mtp_hosts) > 1:
		frappe.throw(
			_("Multiple MTP sites are connected. Open Meet from the intended MTP site."),
			frappe.ValidationError,
		)
	return frappe.local.site


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 60)
def create(
	meeting_title: str | None = None,
	meeting_type: str = "open",
	allow_guest: bool = True,
	host_name: str | None = None,
	created_by_name: str | None = None,
	created_by_email: str | None = None,
) -> str:
	"""Create a new meeting with specified type"""
	meeting_title = (meeting_title or "").strip() or _("Meeting")
	global_settings = frappe.get_cached_doc("Sae Settings")
	if not global_settings.allow_guest:
		allow_guest = False

	meeting: SaeMeeting = frappe.get_doc(
		{
			"doctype": "Sae Meeting",
			"meeting_title": meeting_title,
			"created_by_name": (created_by_name or "").strip()[:140],
			"created_by_email": (created_by_email or "").strip().lower()[:140],
			"host_name": _resolve_meeting_host_name(host_name, created_by_email),
			"meeting_type": meeting_type,
			"allow_guest": allow_guest,
		}
	).insert()

	return meeting.name


def _get_mtp_managed_meeting(meeting_id: str, expected_host_name: str | None, actor_email: str, allow_co_host: bool = True):
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	if (meeting.host_name or "").strip().lower().rstrip(".") != host_name:
		frappe.throw(_("Meeting does not belong to this site"), frappe.PermissionError)
	if meeting.is_deleted:
		frappe.throw(_("Meeting is no longer available"), frappe.DoesNotExistError)
	is_creator = bool(actor_email and (meeting.created_by_email or "").strip().lower() == actor_email.strip().lower())
	is_admin = False
	if actor_email:
		user_name = frappe.db.get_value("User", {"email": actor_email.strip().lower()}, "name") or actor_email
		roles = frappe.get_roles(user_name) or []
		if "System Manager" in roles or "Administrator" in roles or user_name == "Administrator":
			is_admin = True
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
		is_admin = True
	is_co_host = allow_co_host and any(
		(row.user or "").strip().lower() == (actor_email or "").strip().lower()
		for row in meeting.co_hosts or []
	)
	if not is_creator and not is_admin and not is_co_host:
		frappe.throw(_("Only the meeting creator can manage this meeting"), frappe.PermissionError)
	return meeting


@frappe.whitelist()
def can_invite_meeting_users(
	meeting_id: str,
	actor_email: str,
	expected_host_name: str | None = None,
) -> bool:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	is_creator = bool(actor_email and (meeting.created_by_email or "").strip().lower() == actor_email.strip().lower())
	is_admin = False
	if actor_email:
		user_name = frappe.db.get_value("User", {"email": actor_email.strip().lower()}, "name") or actor_email
		roles = frappe.get_roles(user_name) or []
		if "System Manager" in roles or "Administrator" in roles or user_name == "Administrator":
			is_admin = True
	if frappe.session.user == "Administrator" or "System Manager" in frappe.get_roles():
		is_admin = True
	is_co_host = any(
		(row.user or "").strip().lower() == (actor_email or "").strip().lower()
		for row in meeting.co_hosts or []
	)
	return bool(
		not meeting.is_deleted
		and (meeting.host_name or "").strip().lower().rstrip(".") == host_name
		and (is_creator or is_admin or is_co_host)
	)


@frappe.whitelist()
def set_meeting_co_hosts(meeting_id: str, co_host_emails: str, actor_email: str, expected_host_name: str | None = None) -> list[dict]:
	meeting = _get_mtp_managed_meeting(meeting_id, expected_host_name, actor_email)
	try:
		emails = frappe.parse_json(co_host_emails) if isinstance(co_host_emails, str) else co_host_emails
	except Exception:
		frappe.throw(_("Invalid co-host list"), frappe.ValidationError)
	if not isinstance(emails, list):
		frappe.throw(_("Invalid co-host list"), frappe.ValidationError)
	creator = (meeting.created_by_email or "").strip().lower()
	clean_emails = list(dict.fromkeys(str(email).strip().lower() for email in emails if email))
	if creator in clean_emails or len(clean_emails) != len(emails):
		frappe.throw(_("Co-hosts must be unique and cannot include the meeting host"), frappe.ValidationError)
	meeting.set("co_hosts", [])
	for email in clean_emails:
		meeting.append("co_hosts", {"user": email, "user_name": email})
	meeting.save(ignore_permissions=True)
	return [
		{"user": row.user, "user_name": row.user_name}
		for row in meeting.co_hosts
	]


@frappe.whitelist()
def update_meeting_title(
	meeting_id: str,
	meeting_title: str,
	actor_email: str,
	expected_host_name: str | None = None,
) -> dict:
	meeting = _get_mtp_managed_meeting(meeting_id, expected_host_name, actor_email)
	title = (meeting_title or "").strip()
	if not title:
		frappe.throw(_("Meeting title is required"), frappe.ValidationError)
	if len(title) > 140:
		frappe.throw(_("Meeting title cannot exceed 140 characters"), frappe.ValidationError)
	meeting.meeting_title = title
	meeting.save(ignore_permissions=True)
	return {"name": meeting.name, "meeting_title": meeting.meeting_title}


@frappe.whitelist()
def delete_mtp_meeting(
	meeting_id: str,
	actor_email: str,
	expected_host_name: str | None = None,
) -> dict:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	if (meeting.host_name or "").strip().lower().rstrip(".") != host_name or meeting.is_deleted:
		frappe.throw(_("Meeting is not available"), frappe.PermissionError)
	actor = (actor_email or "").strip().lower()
	is_creator = _is_meeting_creator(meeting, actor)
	is_co_host = any((row.user or "").strip().lower() == actor for row in meeting.co_hosts or [])
	if not actor or not (is_creator or is_co_host):
		frappe.throw(_("Only the meeting host or a co-host can delete this meeting"), frappe.PermissionError)
	if not meeting.is_deleted:
		meeting.is_deleted = 1
		meeting.deleted_by = actor
		meeting.deleted_on = now_datetime()
		meeting.save(ignore_permissions=True)
	return {"deleted": True, "name": meeting_id}


@frappe.whitelist()
def invite_meeting_user(
	meeting_id: str,
	invitee_email: str,
	actor_email: str,
	actor_name: str = "",
	invitation_type: str = "Participant",
	expected_host_name: str | None = None,
) -> dict:
	results = invite_meeting_users(
		meeting_id=meeting_id,
		invitee_emails=[invitee_email],
		actor_email=actor_email,
		actor_name=actor_name,
		invitation_type=invitation_type,
		expected_host_name=expected_host_name,
	)
	if not results:
		frappe.throw(_("Could not invite user"), frappe.ValidationError)
	return results[0]


@frappe.whitelist()
def invite_meeting_users(
	meeting_id: str,
	invitee_emails: list[str] | str,
	actor_email: str,
	actor_name: str = "",
	invitation_type: str = "Participant",
	expected_host_name: str | None = None,
) -> list[dict]:
	meeting = _get_mtp_managed_meeting(meeting_id, expected_host_name, actor_email)
	if isinstance(invitee_emails, str):
		invitee_emails = (
			frappe.parse_json(invitee_emails)
			if invitee_emails.strip().startswith("[")
			else [e.strip() for e in invitee_emails.split(",") if e.strip()]
		)
	if not isinstance(invitee_emails, (list, tuple)):
		frappe.throw(_("invitee_emails must be a list of email addresses"), frappe.ValidationError)
	if invitation_type not in {"Participant", "CoHost"}:
		frappe.throw(_("Invalid invitation type"), frappe.ValidationError)

	now = now_datetime()
	host_email = (meeting.created_by_email or "").strip().lower()

	for row in meeting.invitations or []:
		if row.status == "Invited" and _invitation_expired(row, now):
			row.status = "Expired"
			row.responded_on = _invitation_expiration(row)

	pending_emails = {
		(row.invitee_email or "").strip().lower()
		for row in meeting.invitations or []
		if row.status == "Invited" and row.invitee_email
	}

	created_invitations = []
	for raw_email in invitee_emails:
		clean_email = (raw_email or "").strip().lower()
		if not clean_email or "@" not in clean_email:
			continue
		if clean_email == host_email:
			continue
		if clean_email in pending_emails:
			continue

		pending_emails.add(clean_email)
		invitation_id = secrets.token_urlsafe(18)
		invitation = meeting.append("invitations", {
			"invitation_id": invitation_id,
			"invitation_type": invitation_type,
			"invitee_email": clean_email,
			"invitee_name": clean_email,
			"invited_by": actor_email.strip().lower(),
			"invited_by_name": (actor_name or meeting.created_by_name or actor_email).strip()[:140],
			"status": "Invited",
			"invited_on": now,
		})
		created_invitations.append((invitation, clean_email))

	results = []
	if created_invitations:
		meeting.save(ignore_permissions=True)

		for invitation, clean_email in created_invitations:
			_schedule_mtp_invitation_event(
				host_name=meeting.host_name,
				meeting_id=meeting.name,
				event_type="meeting_invitation",
				invitation_id=invitation.invitation_id,
				invitee_email=clean_email,
				invitee_name=invitation.invitee_name or clean_email,
				invited_by=invitation.invited_by,
				invited_by_name=invitation.invited_by_name,
				title=meeting.meeting_title or "",
				invitation_type=invitation_type,
			)
			results.append({
				"invitation_id": invitation.invitation_id,
				"invitee_email": clean_email,
				"invitee_name": invitation.invitee_name,
				"invited_by_name": invitation.invited_by_name,
				"invited_on": invitation.invited_on,
				"meeting_id": meeting.name,
				"meeting_title": meeting.meeting_title,
				"status": invitation.status,
				"invitation_type": invitation.invitation_type or invitation_type,
			})

	return results


@frappe.whitelist()
def invite_meeting_co_host(
	meeting_id: str,
	invitee_email: str,
	actor_email: str,
	actor_name: str = "",
	expected_host_name: str | None = None,
) -> dict:
	return add_meeting_co_host(
		meeting_id=meeting_id,
		co_host_email=invitee_email,
		co_host_name=invitee_email,
		actor_email=actor_email,
		expected_host_name=expected_host_name,
	)


@frappe.whitelist()
def add_meeting_co_host(
	meeting_id: str,
	co_host_email: str,
	co_host_name: str,
	actor_email: str,
	expected_host_name: str | None = None,
) -> dict:
	meeting = _get_mtp_managed_meeting(meeting_id, expected_host_name, actor_email)
	email = (co_host_email or "").strip().lower()
	name = (co_host_name or email).strip()[:140]
	if not email or "@" not in email:
		frappe.throw(_("A valid co-host email is required"), frappe.ValidationError)
	if _is_meeting_creator(meeting, email):
		return {
			"user": email,
			"user_name": meeting.created_by_name or email,
			"already_added": True,
			"already_host": True,
		}
	row = next(
		(row for row in meeting.co_hosts or [] if (row.user or "").strip().lower() == email),
		None,
	)
	if row:
		return {"user": email, "user_name": row.user_name or name, "already_added": True}
	meeting.append("co_hosts", {"user": email, "user_name": name})
	meeting.save(ignore_permissions=True)
	return {"user": email, "user_name": name, "already_added": False}


@frappe.whitelist()
def get_my_meeting_invitations(
	invitee_email: str, expected_host_name: str | None = None
) -> list[dict]:
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	invitee_email = (invitee_email or "").strip().lower()
	if not invitee_email:
		return []
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	meeting_ids = frappe.get_all(
		"Sae Meeting", filters={"host_name": host_name, "is_deleted": 0}, pluck="name"
	)
	if not meeting_ids:
		return []
	rows = frappe.get_all(
		"Sae Meeting Invitation",
		filters={
			"invitee_email": invitee_email,
			"status": "Invited",
			"parenttype": "Sae Meeting",
			"parent": ["in", meeting_ids],
		},
		fields=["name", "invitation_id", "invitee_email", "invitee_name", "invited_by_name", "invited_on", "parent"],
		order_by="creation desc",
		limit=500,
	)
	now = now_datetime()
	active_rows = []
	for row in rows:
		if _invitation_expired(row, now):
			frappe.db.set_value(
				"Sae Meeting Invitation",
				row.name,
				{"status": "Expired", "responded_on": _invitation_expiration(row)},
				update_modified=False,
			)
		else:
			active_rows.append(row)
	return [
		{
			"invitation_id": row.invitation_id,
			"invitee_email": row.invitee_email,
			"invitee_name": row.invitee_name,
			"invited_by_name": row.invited_by_name,
			"invited_on": row.invited_on,
			"meeting_id": row.parent,
			"meeting_title": frappe.db.get_value("Sae Meeting", row.parent, "meeting_title"),
		}
		for row in active_rows
	]


def _get_user_joined_meeting_ids(actor_email: str, host_name: str) -> set[str]:
	if not actor_email:
		return set()
	joined_ids = {
		row.meeting
		for row in frappe.get_all(
			"User Domain",
			filters={"host_name": host_name, "user_email": actor_email},
			fields=["meeting", "user_id"],
		)
		if row.meeting and row.user_id
	}
	meet_user = frappe.db.get_value("User", {"email": actor_email}, "name")
	member_ids = {actor_email}
	if meet_user:
		member_ids.add(meet_user)
	joined_ids.update(
		row.parent
		for row in frappe.get_all(
			"Sae Meeting User",
			filters={"user": ["in", list(member_ids)], "parenttype": "Sae Meeting"},
			fields=["parent"],
		)
		if row.parent
	)
	return joined_ids


@frappe.whitelist()
def get_user_meetings(
	actor_email: str,
	expected_host_name: str | None = None,
	limit: int = 100,
	start: int = 0,
) -> list[dict]:
	"""Return only this MTP user's created meetings and successful attendances."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)

	actor_email = (actor_email or "").strip().lower()
	if not actor_email:
		return []
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	try:
		limit = min(max(int(limit), 1), 500)
		start = max(int(start), 0)
	except (TypeError, ValueError):
		frappe.throw(_("Invalid meeting list pagination"), frappe.ValidationError)

	created_ids = set(
		frappe.get_all(
			"Sae Meeting",
			filters={
				"host_name": host_name,
				"is_deleted": 0,
				"created_by_email": actor_email,
			},
			pluck="name",
		)
	)

	joined_ids = _get_user_joined_meeting_ids(actor_email, host_name)
	actor_users = {actor_email}
	user_name = frappe.db.get_value("User", {"email": actor_email}, "name")
	if user_name:
		actor_users.add(user_name)
	co_host_ids = {
		row.parent
		for row in frappe.get_all(
			"Sae Meeting User",
			filters={
				"user": ["in", list(actor_users)],
				"parenttype": "Sae Meeting",
				"parentfield": "co_hosts",
			},
			fields=["parent"],
		)
		if row.parent
	}

	meeting_ids = created_ids | joined_ids | co_host_ids
	if not meeting_ids:
		return []

	meetings = frappe.get_all(
		"Sae Meeting",
		filters={
			"name": ["in", list(meeting_ids)],
			"host_name": host_name,
			"is_deleted": 0,
		},
		fields=[
			"name",
			"meeting_title",
			"meeting_type",
			"allow_guest",
			"active_meeting_started_at",
			"last_meeting_started_at",
			"last_meeting_duration_seconds",
			"owner",
			"created_by_name",
			"created_by_email",
			"creation",
			"modified",
		],
		order_by="creation desc",
		limit_start=start,
		limit_page_length=limit,
	)
	meeting_by_id = {meeting.name: meeting for meeting in meetings}
	started_ids = {
		row.meeting
		for row in frappe.get_all(
			"User Domain",
			filters={"meeting": ["in", list(meeting_by_id)], "host_name": host_name},
			fields=["meeting", "user_id"],
		)
		if row.meeting and row.user_id
	}
	last_meeting_times = {}
	for row in frappe.get_all(
		"User Domain",
		filters={"meeting": ["in", list(meeting_by_id)], "host_name": host_name},
		fields=["meeting", "joined_at"],
		order_by="joined_at desc",
	):
		if row.meeting and row.joined_at and row.meeting not in last_meeting_times:
			last_meeting_times[row.meeting] = row.joined_at
	member_rows = frappe.get_all(
		"Sae Meeting User",
		filters={
			"parent": ["in", list(meeting_by_id)],
			"parenttype": "Sae Meeting",
		},
		fields=["parent", "user"],
	)
	creator_emails = {
		(meeting.created_by_email or "").strip().lower()
		for meeting in meetings
		if meeting.created_by_email
	}
	creator_users = {}
	if creator_emails:
		creator_users = {
			(user.email or "").strip().lower(): user.name
			for user in frappe.get_all(
				"User",
				filters={"email": ["in", list(creator_emails)]},
				fields=["name", "email"],
			)
			if user.email
		}
	for member in member_rows:
		meeting = meeting_by_id.get(member.parent)
		if not meeting or not member.user:
			continue
		creator_email = (meeting.created_by_email or "").strip().lower()
		auto_added_users = {
			meeting.owner,
			creator_email,
			creator_users.get(creator_email),
		}
		if member.user not in auto_added_users:
			started_ids.add(meeting.name)

	for meeting in meetings:
		meeting.is_created_by_me = meeting.name in created_ids
		meeting.is_participant = meeting.name in joined_ids and meeting.name not in created_ids
		meeting.is_co_host = meeting.name in co_host_ids and meeting.name not in created_ids
		meeting.has_started = meeting.name in started_ids
		meeting.last_meeting_at = meeting.last_meeting_started_at or last_meeting_times.get(meeting.name)
		duration_seconds = meeting.last_meeting_duration_seconds
		duration_available = bool(meeting.last_meeting_started_at and duration_seconds is not None)
		if meeting.active_meeting_started_at:
			duration_seconds = max(
				0,
				int((now_datetime() - get_datetime(meeting.active_meeting_started_at)).total_seconds()),
			)
			duration_available = True
		meeting.last_meeting_duration_minutes = (
			math.ceil(duration_seconds / 60) if duration_available else None
		)
	return meetings


@frappe.whitelist()
def get_user_meeting(
	meeting_id: str,
	actor_email: str,
	expected_host_name: str | None = None,
) -> dict:
	"""Return a meeting document only to its creator or a confirmed attendee."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)

	actor_email = (actor_email or "").strip().lower()
	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	meeting = frappe.get_doc("Sae Meeting", meeting_id)
	if (meeting.host_name or "").strip().lower().rstrip(".") != host_name or meeting.is_deleted:
		frappe.throw(_("Meeting is not available"), frappe.PermissionError)
	is_creator = (meeting.created_by_email or "").strip().lower() == actor_email
	is_co_host = any(
		(row.user or "").strip().lower() == actor_email for row in meeting.co_hosts or []
	)
	is_participant = meeting_id in _get_user_joined_meeting_ids(actor_email, host_name)
	if not actor_email or not (is_creator or is_co_host or is_participant):
		frappe.throw(_("You cannot view this meeting"), frappe.PermissionError)
	result = meeting.as_dict()
	for row in result.get("co_hosts", []):
		row["user"] = (row.get("user") or "").strip().lower()
	return result


@frappe.whitelist()
def respond_meeting_invitation(
	meeting_id: str,
	invitation_id: str,
	response: str,
	invitee_email: str,
	expected_host_name: str | None = None,
) -> dict:
	if response not in {"Accepted", "Declined"}:
		frappe.throw(_("Invalid invitation response"), frappe.ValidationError)
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	if (meeting.host_name or "").strip().lower().rstrip(".") != (
		(expected_host_name or "").strip().lower().rstrip(".")
	):
		frappe.throw(_("Meeting does not belong to this site"), frappe.PermissionError)
	if meeting.is_deleted:
		frappe.throw(_("Meeting is no longer available"), frappe.PermissionError)
	email = (invitee_email or "").strip().lower()
	invitation = next((row for row in meeting.invitations or [] if row.invitation_id == invitation_id), None)
	if not invitation or invitation.invitee_email != email:
		frappe.throw(_("Invitation not found for this user"), frappe.PermissionError)
	if invitation.status != "Invited":
		return {
			"meeting_id": meeting_id,
			"invitation_id": invitation_id,
			"status": invitation.status,
			"invited_by": invitation.invited_by,
			"already_responded": True,
		}
	if _invitation_expired(invitation, now_datetime()):
		invitation.status = "Expired"
		invitation.responded_on = _invitation_expiration(invitation)
		meeting.save(ignore_permissions=True)

		_schedule_mtp_invitation_event(
                host_name=meeting.host_name,
                meeting_id=meeting.name,
                event_type="meeting_invitation_response",
                invitation_id=invitation_id,
                invitee_email=email,
                invited_by=invitation.invited_by,
                invitation_status="Expired",
        )
		return {
			"meeting_id": meeting_id,
			"invitation_id": invitation_id,
			"status": "Expired",
			"invited_by": invitation.invited_by,
		}
	invitation.status = response
	invitation.responded_on = frappe.utils.now_datetime()
	meeting.save(ignore_permissions=True)

	_schedule_mtp_invitation_event(
        host_name=meeting.host_name,
        meeting_id=meeting.name,
        event_type="meeting_invitation_response",
        invitation_id=invitation_id,
        invitee_email=email,
        invited_by=invitation.invited_by,
        invitation_status=response,
	)

	return {
		"meeting_id": meeting_id,
		"invitation_id": invitation_id,
		"status": response,
		"invited_by": invitation.invited_by,
	}


def _has_accepted_invitation(meeting: "SaeMeeting", invitee_email: str) -> bool:
	email = (invitee_email or "").strip().lower()
	return any(
		(row.invitee_email or "").strip().lower() == email and row.status == "Accepted"
		for row in meeting.invitations or []
	)


def _invitation_expired(invitation, now=None) -> bool:
	if not invitation.invited_on:
		return False
	return (now or now_datetime()) >= _invitation_expiration(invitation)


def _invitation_expiration(invitation):
	return get_datetime(invitation.invited_on) + timedelta(minutes=5)


def notify_mtp_meeting_created(host_name: str, meeting_id: str, title: str):
	"""Relay a newly created meeting to its registered MTP site."""
	host_name = (host_name or "").strip().lower().rstrip(".")
	callback = frappe.db.get_value(
		"Meet Domain", host_name, ["callback_url", "callback_secret"], as_dict=True
	)
	if not callback:
		return
	timestamp = int(time.time())
	payload = f"{host_name}\n{meeting_id}\nmeeting_created\n{title or ''}\n{timestamp}".encode()
	signature = hmac.new(callback.callback_secret.encode(), payload, hashlib.sha256).hexdigest()
	try:
		response = requests.post(
			callback.callback_url,
			json={
				"host_name": host_name,
				"meeting_id": meeting_id,
				"event_type": "meeting_created",
				"title": title or "",
				"timestamp": timestamp,
			},
			headers={"X-Meet-Event-Signature": signature},
			timeout=(3.05, 6),
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		frappe.log_error("Meet Meeting Created Relay", str(exc))


def _relay_mtp_invitation_event(
        host_name: str,
        meeting_id: str,
        event_type: str,
        invitation_id: str,
        invitee_email: str,
        invitee_name: str = "",
        invited_by: str = "",
        invited_by_name: str = "",
        title: str = "",
        invitation_status: str | None = None,
):
        """Relay invitation events to the registered NextGRP site."""
        host_name = (host_name or "").strip().lower().rstrip(".")
        invitee_email = (invitee_email or "").strip().lower()
        invited_by = (invited_by or "").strip().lower()

        callback = frappe.db.get_value(
                "Meet Domain",
                host_name,
                ["callback_url", "callback_secret"],
                as_dict=True,
        )

        if not callback or not callback.callback_url or not callback.callback_secret:
                frappe.logger("meet_invitation_realtime").error(
                        "No callback registered for host=%s event=%s",
                        host_name,
                        event_type,
                )
                return False

        timestamp = int(time.time())

        if event_type == "meeting_invitation":
                payload = {
                        "host_name": host_name,
                        "meeting_id": meeting_id,
                        "event_type": event_type,
                        "timestamp": timestamp,
                        "invitation_id": invitation_id,
                        "invitee_email": invitee_email,
                        "invitee_name": invitee_name or invitee_email,
                        "invited_by": invited_by,
                        "invited_by_name": invited_by_name or invited_by,
                        "title": title or "",
                }

                signature_payload = "\n".join([
                        host_name,
                        meeting_id,
                        invitation_id,
                        invitee_email,
                        invitee_name or invitee_email,
                        invited_by,
                        invited_by_name or invited_by,
                        title or "",
                        str(timestamp),
                ]).encode()

        elif event_type == "meeting_invitation_response":
                payload = {
                        "host_name": host_name,
                        "meeting_id": meeting_id,
                        "event_type": event_type,
                        "timestamp": timestamp,
                        "invitation_id": invitation_id,
                        "invitee_email": invitee_email,
                        "invited_by": invited_by,
                        "invitation_status": invitation_status,
                }

                signature_payload = "\n".join([
                        host_name,
                        meeting_id,
                        invitation_id,
                        invitee_email,
                        invited_by,
                        invitation_status or "",
                        str(timestamp),
                ]).encode()

        else:
                frappe.logger("meet_invitation_realtime").error(
                        "Unsupported invitation event: %s", event_type
                )
                return False

        signature = hmac.new(
                callback.callback_secret.encode(),
                signature_payload,
                hashlib.sha256,
        ).hexdigest()

        try:
                response = requests.post(
                        callback.callback_url,
                        json=payload,
                        headers={
                                "X-Meet-Event-Signature": signature,
                        },
                        timeout=(3.05, 6),
                )
                response.raise_for_status()

                frappe.logger("meet_invitation_realtime").info(
                        "Relayed invitation event: host=%s meeting=%s "
                        "invitation=%s type=%s",
                        host_name,
                        meeting_id,
                        invitation_id,
                        event_type,
                )
                return True

        except requests.RequestException as exc:
                frappe.log_error(
                        f"Host: {host_name}\n"
                        f"Meeting: {meeting_id}\n"
                        f"Invitation: {invitation_id}\n"
                        f"Event: {event_type}\n"
                        f"Error: {exc}",
                        "Meet Invitation Realtime Relay",
                )
                return False


def _schedule_mtp_invitation_event(**kwargs):
        """Send the callback only after the invitation transaction commits."""
        frappe.db.after_commit.add(
                lambda: _relay_mtp_invitation_event(**kwargs)
        )


def _is_meeting_host(meeting: "SaeMeeting", user: str) -> bool:
	if not user or user == "Guest":
		return False
	if meeting.owner == user or user == "Administrator":
		return True
	if meeting.created_by_email:
		clean_creator = meeting.created_by_email.strip().lower()
		clean_user = user.strip().lower()
		if clean_user == clean_creator:
			return True
		user_email = (frappe.db.get_value("User", user, "email") or "").strip().lower()
		if user_email and user_email == clean_creator:
			return True
	return False


def _is_meeting_creator(meeting: "SaeMeeting", actor_email: str | None) -> bool:
	actor = (actor_email or "").strip().lower()
	if not actor:
		return False

	creator_email = (meeting.created_by_email or "").strip().lower()
	if creator_email:
		return actor == creator_email

	owner = (meeting.owner or "").strip()
	if owner.lower() == actor:
		return True
	owner_email = (frappe.db.get_value("User", owner, "email") or "").strip().lower()
	return bool(owner_email and owner_email == actor)


@frappe.whitelist()
def get_sfu_connection_details(meeting_id: str) -> dict:
	"""
	Get SFU connection details for direct client-to-SFU communication
	"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	user = frappe.session.user

	if meeting.is_user_banned(user):
		frappe.throw(_("You are banned from this meeting"), frappe.PermissionError)

	if user not in meeting.get_members():
		frappe.throw(_("Not a meeting member"), frappe.PermissionError)

	if not meeting.can_join(user):
		frappe.throw(_("Access denied"), frappe.PermissionError)

	sfu_config = get_sfu_config()

	user_fullname, user_avatar = frappe.db.get_value("User", user, ["full_name", "user_image"]) or (
		user,
		None,
	)

	is_host = _is_meeting_host(meeting, user)
	is_cohost = bool(meeting.is_host_or_cohost(user) and not is_host)

	auth_token = _generate_sfu_token(
		user_id=user,
		meeting_id=meeting_id,
		user_name=user_fullname,
		user_avatar=user_avatar,
		is_host=is_host,
		is_cohost=is_cohost,
	)

	return {
		"sfu_url": sfu_config["sfu_server_url"],
		"sfu_port": sfu_config["sfu_server_port"],
		"auth_token": auth_token,
		"user_id": user,
		"meeting_id": meeting_id,
		"codec_strategy": _get_codec_strategy(),
		"user_data": {
			"name": user_fullname,
			"email": user,
			"avatar": user_avatar,
		},
		"expires_in": 3600,
		"host_only_chat": bool(meeting.host_only_chat),
	}


@frappe.whitelist()
def join_meeting(meeting_id: str) -> dict:
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)

	if meeting.is_user_banned(frappe.session.user):
		frappe.throw(_("You are banned from this meeting"), frappe.PermissionError)

	if meeting.can_join(frappe.session.user):
		result = meeting.join(frappe.session.user)

		if isinstance(result, dict):
			if result.get("status") == "waiting_for_approval":
				sfu_config = get_sfu_config()

				user_fullname, user_avatar = frappe.db.get_value(
					"User", frappe.session.user, ["full_name", "user_image"]
				) or (frappe.session.user, None)

				lobby_token = _generate_sfu_token(
					user_id=frappe.session.user,
					meeting_id=meeting_id,
					scope="presence-preview",
					user_name=user_fullname,
					user_avatar=user_avatar,
					is_host=False,
					is_guest=False,
				)

				return {
					"status": "waiting_for_approval",
					"meeting_id": meeting_id,
					"message": result.get("message", "Waiting for host approval"),
					"lobby_token": lobby_token,
					"sfu_url": sfu_config["sfu_server_url"],
					"sfu_port": sfu_config["sfu_server_port"],
					"user_data": {
						"name": user_fullname,
						"avatar": user_avatar,
					},
				}
			elif result.get("status") == "joined":
				from meet.api.integration import record_meeting_participant

				user_info = frappe.db.get_value(
					"User", frappe.session.user, ["email", "full_name"], as_dict=True
				) or {}
				record_meeting_participant(
					meeting,
					user_info.get("full_name") or frappe.session.user,
					user_email=user_info.get("email") or "",
					user_id=frappe.session.user,
				)
				is_host = _is_meeting_host(meeting, frappe.session.user)
				is_cohost = bool(meeting.is_host_or_cohost(frappe.session.user) and not is_host)
				return {
					"status": "joined",
					"meeting_id": meeting_id,
					"message": result.get("message", "Successfully joined meeting"),
					"is_host": is_host,
					"is_cohost": is_cohost,
					"host_only_chat": bool(meeting.host_only_chat),
				}
	else:
		frappe.throw(_("Access denied"))


def _get_meeting_caller(meeting: "SaeMeeting", guest_id: str | None = None) -> str | None:
	if frappe.session.user != "Guest":
		return frappe.session.user

	if guest_id:
		session_data = get_guest_session(guest_id)
		if session_data and session_data.get("meeting_id") == meeting.name:
			return guest_id

	req_guest_id = frappe.form_dict.get("guest_id") or (
		frappe.request.headers.get("X-Guest-ID") if hasattr(frappe, "request") and frappe.request else None
	)
	if req_guest_id:
		session_data = get_guest_session(req_guest_id)
		if session_data and session_data.get("meeting_id") == meeting.name:
			return req_guest_id

	return None


@frappe.whitelist(allow_guest=True)
def approve_join_request(meeting_id: str, user_id: str, guest_id: str | None = None) -> dict:
	"""Approve a user's join request from waiting room"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Only hosts and co-hosts can approve join requests"), frappe.PermissionError)

	meeting.approve_user(user_id, approved_by=caller)
	return {"meeting_id": meeting_id, "user_id": user_id, "message": "User approved successfully"}


@frappe.whitelist(allow_guest=True)
def approve_all_join_requests(meeting_id: str, guest_id: str | None = None) -> dict:
	"""Approve all users' join requests from waiting room"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Only hosts and co-hosts can approve join requests"), frappe.PermissionError)

	meeting.approve_all_users(approved_by=caller)
	return {"meeting_id": meeting_id, "message": "All users approved successfully"}


@frappe.whitelist(allow_guest=True)
def reject_join_request(meeting_id: str, user_id: str, guest_id: str | None = None) -> dict:
	"""Reject a user's join request from waiting room"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Only hosts and co-hosts can reject join requests"), frappe.PermissionError)

	meeting.reject_user(user_id, rejected_by=caller)
	return {"meeting_id": meeting_id, "user_id": user_id, "message": "User rejected successfully"}


@frappe.whitelist(allow_guest=True)
def ban_meeting_participant(meeting_id: str, user_id: str, guest_id: str | None = None) -> dict:
	"""Prevent a removed meeting participant from rejoining."""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Only hosts and co-hosts can block participants"), frappe.PermissionError)

	meeting.add_user_to_table("banned_users", user_id, save=True, ignore_permissions=True)
	return {"meeting_id": meeting_id, "user_id": user_id, "message": "Participant banned successfully"}


@frappe.whitelist(allow_guest=True)
def get_waiting_room(meeting_id: str, guest_id: str | None = None) -> dict:
	"""Get list of users waiting for approval"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Access denied"), frappe.PermissionError)

	waiting_rows = meeting.waiting_room or []

	user_details = []
	for row in waiting_rows:
		user = row.user
		user_info = get_user_info(user)
		user_name = row.user_name or (user_info.get("full_name") if user_info else None)
		user_details.append(
			{
				"user_id": user,
				"full_name": user_name or user,
				"user_name": user_name or user,
				"user_image": user_info.get("user_image") if user_info else None,
				"is_guest": user_info.get("is_guest", False) if user_info else user.startswith("guest_"),
			}
		)

	return {"meeting_id": meeting_id, "waiting_users": user_details}


@frappe.whitelist()
def get_join_status(meeting_id: str) -> dict:
	"""Return the current user's persisted meeting admission state."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)

	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	user = frappe.session.user
	if meeting.is_user_banned(user):
		status = "rejected"
	elif user in meeting.get_waiting_room():
		status = "waiting_for_approval"
	elif user in meeting.get_members():
		status = "joined"
	else:
		status = "not_requested"

	return {"meeting_id": meeting_id, "user": user, "status": status}


@frappe.whitelist(allow_guest=True)
def check_is_host(meeting_id: str, guest_id: str | None = None) -> bool:
	"""Check if caller is host or cohost (used by realtime socket handler)"""
	if not frappe.db.exists("Sae Meeting", meeting_id):
		return False
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	return bool(caller and meeting.is_host_or_cohost(caller))


@frappe.whitelist()
def refresh_sfu_token(meeting_id: str) -> dict:
	"""
	Refresh SFU authentication token for ongoing meetings
	"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)

	if frappe.session.user not in meeting.get_members():
		frappe.throw(_("Not a meeting member"))
	if not meeting.can_join(frappe.session.user):
		frappe.throw(_("Meeting is no longer available"), frappe.PermissionError)

	user_fullname, user_avatar = frappe.db.get_value(
		"User", frappe.session.user, ["full_name", "user_image"]
	) or (frappe.session.user, None)

	is_host = _is_meeting_host(meeting, frappe.session.user)
	is_cohost = bool(meeting.is_host_or_cohost(frappe.session.user) and not is_host)

	auth_token = _generate_sfu_token(
		user_id=frappe.session.user,
		meeting_id=meeting_id,
		user_name=user_fullname,
		user_avatar=user_avatar,
		is_host=is_host,
		is_cohost=is_cohost,
	)

	return {"auth_token": auth_token, "expires_in": 3600, "codec_strategy": _get_codec_strategy()}


@frappe.whitelist()
def get_sfu_presence_preview_token(
	meeting_id: str,
	expected_host_name: str | None = None,
	actor_email: str | None = None,
) -> dict:
	"""Get a short-lived presence token, with kick permission for the creator.

	This is used by the meeting preview page to fetch live participants
	from the SFU without granting media capabilities.
	"""

	try:
		meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	except frappe.DoesNotExistError:
		frappe.throw(_("Meeting not found"))

	if meeting.is_user_banned(frappe.session.user):
		frappe.throw(_("You are banned from this meeting"), frappe.PermissionError)
	if expected_host_name and (meeting.host_name or "").strip().lower().rstrip(".") != expected_host_name.strip().lower().rstrip("."):
		frappe.throw(_("Meeting does not belong to this site"), frappe.PermissionError)

	if not meeting.can_join(frappe.session.user):
		frappe.throw(_("Access denied"), frappe.PermissionError)

	is_creator = _is_meeting_creator(meeting, actor_email)
	actor_email_clean = (actor_email or "").strip().lower()
	is_co_host = any(
		(row.user or "").strip().lower() == actor_email_clean for row in meeting.co_hosts or []
	)
	can_manage_participants = is_creator or is_co_host

	sfu_config = get_sfu_config()

	expiry_seconds = 300
	session_id = str(secrets.token_urlsafe(16))
	token_user_id = actor_email.strip() if can_manage_participants and actor_email else frappe.session.user

	auth_token = _generate_sfu_token(
		user_id=token_user_id,
		meeting_id=meeting_id,
		scope="presence-preview",
		expires_in=expiry_seconds,
		session_id=session_id,
		is_host=can_manage_participants,
	)

	return {
		"sfu_url": sfu_config["sfu_server_url"],
		"sfu_port": sfu_config.get("sfu_server_port"),
		"auth_token": auth_token,
		"expires_in": expiry_seconds,
		"user_id": token_user_id,
		"is_creator": is_creator,
		"can_manage_participants": can_manage_participants,
	}


@frappe.whitelist()
@rate_limit(limit=30, seconds=60)
def get_presence_counts(meeting_ids, expected_host_name: str | None = None) -> dict:
	"""Return live SFU participant counts for meetings owned by one MTP site."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication is required"), frappe.AuthenticationError)
	if isinstance(meeting_ids, str):
		meeting_ids = frappe.parse_json(meeting_ids)
	if (
		not isinstance(meeting_ids, list)
		or len(meeting_ids) > 100
		or any(not isinstance(meeting_id, str) or not meeting_id.strip() for meeting_id in meeting_ids)
	):
		frappe.throw(_("A list of at most 100 meeting IDs is required"), frappe.ValidationError)

	meeting_ids = list(dict.fromkeys(meeting_id.strip() for meeting_id in meeting_ids))
	if not meeting_ids:
		return {"available": True, "counts": {}}

	host_name = (expected_host_name or frappe.local.site).strip().lower().rstrip(".")
	owned_meetings = set(
		frappe.get_all(
			"Sae Meeting",
			filters={"name": ["in", meeting_ids], "host_name": host_name, "is_deleted": 0},
			pluck="name",
		)
	)
	if owned_meetings != set(meeting_ids):
		frappe.throw(_("One or more meetings do not belong to this site"), frappe.PermissionError)

	sfu_config = get_sfu_config()
	secret = sfu_config.get("sfu_secret") or frappe.conf.get("secret_key")
	if not secret:
		frappe.throw(_("SFU secret not configured"), frappe.ValidationError)

	token = _generate_sfu_token(
		user_id=frappe.session.user,
		meeting_id="presence-list",
		scope="presence-list",
		expires_in=30,
		meeting_ids=meeting_ids,
	)
	sfu_endpoint = get_sfu_presence_url()

	try:
		response = requests.post(
			sfu_endpoint,
			json={"meeting_ids": meeting_ids},
			headers={"Authorization": f"Bearer {token}"},
			timeout=3,
		)
		response.raise_for_status()
		payload = response.json()
		counts = payload.get("counts") or {}
		return {
			"available": True,
			"counts": {
				meeting_id: max(0, int(counts.get(meeting_id, 0))) for meeting_id in meeting_ids
			},
		}
	except requests.Timeout as exc:
		frappe.log_error("Meet SFU Presence", str(exc))
		return {"available": False, "counts": {}, "reason": "Meet cannot reach the SFU within 3 seconds"}
	except requests.HTTPError as exc:
		status = exc.response.status_code if exc.response is not None else "unknown"
		frappe.log_error("Meet SFU Presence", str(exc))
		reason = (
			"SFU presence endpoint /internal/presence returned HTTP 404; verify the configured SFU URL and deploy the current SFU server"
			if status == 404
			else f"SFU returned HTTP {status}"
		)
		return {"available": False, "counts": {}, "reason": reason}
	except requests.RequestException as exc:
		frappe.log_error("Meet SFU Presence", str(exc))
		return {
			"available": False,
			"counts": {},
			"reason": "Meet cannot reach the SFU's internal HTTP endpoint; verify meet_server_url and meet_server_port in the Meet site_config.json",
		}
	except (ValueError, TypeError) as exc:
		frappe.log_error("Meet SFU Presence", str(exc))
		return {"available": False, "counts": {}, "reason": "SFU returned an invalid presence response"}


@frappe.whitelist(allow_guest=True)
def sfu_presence_event():
	"""Validate an SFU-signed room count and relay it to its registered MTP site."""
	request = frappe.local.request
	token = request.headers.get("X-SFU-Presence-Token", "")
	if not token:
		frappe.throw(_("SFU authentication is required"), frappe.AuthenticationError)

	sfu_config = get_sfu_config()
	secret = sfu_config.get("sfu_secret") or frappe.conf.get("secret_key")
	try:
		claims = jwt.decode(token, secret, algorithms=["HS256"])
	except jwt.InvalidTokenError:
		frappe.throw(_("Invalid SFU event token"), frappe.AuthenticationError)
	if claims.get("scope") != "sfu-presence-event":
		frappe.throw(_("Invalid SFU event scope"), frappe.AuthenticationError)

	meeting_id = claims.get("meeting_id")
	host_name = (claims.get("host_name") or "").strip().lower().rstrip(".")
	count = claims.get("count")
	if (
		claims.get("site") != frappe.local.site
		or not meeting_id
		or not host_name
		or not isinstance(count, int)
		or count < 0
	):
		frappe.throw(_("Invalid presence event"), frappe.ValidationError)
	if not frappe.db.exists("Sae Meeting", {"name": meeting_id, "host_name": host_name}):
		frappe.throw(_("Meeting does not belong to this site"), frappe.PermissionError)

	meeting = frappe.get_doc("Sae Meeting", meeting_id)
	event_at = claims.get("event_at")
	if not isinstance(event_at, int) or event_at <= 0:
		event_at = int(time.time() * 1000)
	if _update_meeting_session_presence(meeting, count, event_at):
		meeting.save(ignore_permissions=True)

	callback = frappe.db.get_value(
		"Meet Domain", host_name, ["callback_url", "callback_secret"], as_dict=True
	)
	if not callback:
		frappe.log_error("Meet Presence Relay", f"No callback registered for {host_name}")
		frappe.local.response["http_status_code"] = 503
		return {"relayed": False, "reason": "No NextGRP presence callback registered"}

	timestamp = int(time.time())
	signature_payload = f"{host_name}\n{meeting_id}\n{count}\n{timestamp}".encode()
	signature = hmac.new(
		callback.callback_secret.encode(), signature_payload, hashlib.sha256
	).hexdigest()
	payload = {
		"host_name": host_name,
		"meeting_id": meeting_id,
		"count": count,
		"timestamp": timestamp,
	}
	if not _relay_presence_callback(callback.callback_url, payload, signature):
		frappe.local.response["http_status_code"] = 502
		return {"relayed": False, "reason": "NextGRP presence callback failed"}
	frappe.logger("meet_presence").info(
		"Relayed room presence: host=%s meeting=%s count=%s",
		host_name,
		meeting_id,
		count,
	)
	return {"relayed": True}


def _update_meeting_session_presence(meeting, count: int, event_at: int) -> bool:
	"""Apply an ordered SFU presence snapshot to the meeting's latest session."""
	event_time = datetime.fromtimestamp(event_at / 1000)
	previous_event_time = meeting.get("last_presence_event_at")
	if previous_event_time and event_time <= get_datetime(previous_event_time):
		return False

	meeting.last_presence_event_at = event_time
	active_started_at = meeting.get("active_meeting_started_at")
	if count > 0 and not active_started_at:
		meeting.active_meeting_started_at = event_time
		meeting.last_meeting_started_at = event_time
	elif count == 0 and active_started_at:
		started_at = get_datetime(active_started_at)
		meeting.last_meeting_ended_at = event_time
		meeting.last_meeting_duration_seconds = max(
			0, int((event_time - started_at).total_seconds())
		)
		meeting.active_meeting_started_at = None
	return True


def _relay_presence_callback(callback_url, payload, signature):
	"""Retry one short transient failure; presence snapshots are idempotent."""
	for attempt in range(2):
		try:
			response = requests.post(
				callback_url,
				json=payload,
			headers={"X-Meet-Event-Signature": signature},
				timeout=(3.05, 6),
			)
			response.raise_for_status()
			return True
		except requests.HTTPError as exc:
			status = exc.response.status_code if exc.response is not None else 0
			if status and status < 500 and status != 429:
				frappe.log_error("Meet Presence Relay", str(exc))
				return False
			last_error = exc
		except requests.RequestException as exc:
			last_error = exc

		if attempt == 0:
			time.sleep(0.25)

	frappe.log_error("Meet Presence Relay", str(last_error))
	return False


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=60, seconds=10 * 60)
def join_meeting_as_guest(
	meeting_id: str,
	guest_name: str,
	guest_id: str | None = None,
	domain_entry: str | None = None,
) -> dict:
	"""
	Allow guest users to join a meeting without authentication.
	Generates a guest session and JWT token for SFU access.
	"""
	is_valid, error_message = validate_guest_name(guest_name)
	if not is_valid:
		frappe.throw(_(error_message))

	if not frappe.db.exists("Sae Meeting", meeting_id):
		frappe.throw(_("Meeting not found"))

	meeting = frappe.get_doc("Sae Meeting", meeting_id)
	if meeting.is_deleted:
		frappe.throw(_("Meeting is no longer available"), frappe.PermissionError)

	global_settings = frappe.get_cached_doc("Sae Settings")
	if not global_settings.allow_guest or not meeting.allow_guest:
		frappe.throw(_("Guests are not allowed in this meeting"))
	# Check if reusing existing guest_id
	session_data = None
	if guest_id:
		session_data = get_guest_session(guest_id)
		if session_data and session_data.get("meeting_id") == meeting_id:
			# Reuse existing guest_id
			guest_name_clean = session_data.get("guest_name", guest_name.strip())
		else:
			# Invalid or expired, generate new
			guest_id = None
			session_data = None

	if not guest_id:
		guest_id = f"guest_{secrets.token_urlsafe(16)}"
		guest_name_clean = guest_name.strip()

	if meeting.is_user_banned(guest_id):
		frappe.throw(_("You are banned from this meeting"))

	sfu_config = get_sfu_config()
	domain_email = None
	if domain_entry:
		entry = frappe.db.get_value(
			"User Domain",
			domain_entry,
			["meeting", "host_name", "user_email", "user_name", "joined_at"],
			as_dict=True,
		)
		if entry:
			if entry.meeting != meeting_id:
				frappe.throw(_("Thông tin xác thực không khớp với cuộc họp này"), frappe.PermissionError)
			if (entry.host_name or "").strip().lower().rstrip(".") != (meeting.host_name or "").strip().lower().rstrip("."):
				frappe.throw(_("Cuộc họp không thuộc về hệ thống của bạn"), frappe.PermissionError)
			domain_email = (entry.user_email or "").strip().lower()
			if (not guest_name_clean or not guest_name_clean.strip()) and entry.user_name:
				guest_name_clean = entry.user_name.strip()

	creator_email = (meeting.created_by_email or "").strip().lower()
	is_creator = bool(
		domain_email
		and creator_email
		and domain_email == creator_email
	)
	if not is_creator and session_data and (session_data.get("is_creator") or session_data.get("is_host")):
		is_creator = True
	is_invited = bool(domain_email and _has_accepted_invitation(meeting, domain_email))

	# Store / update guest session
	session_payload = {
		"guest_id": guest_id,
		"guest_name": guest_name_clean,
		"meeting_id": meeting_id,
		"ip_address": frappe.local.request_ip,
		"joined_at": int(time.time()),
		"is_host": is_creator or (session_data.get("is_host") if session_data else False),
		"is_creator": is_creator or (session_data.get("is_creator") if session_data else False),
		"user_email": domain_email or (session_data.get("user_email") if session_data else ""),
	}
	set_guest_session(guest_id, session_payload, ttl=24 * 3600)

	if meeting.meeting_type == "restricted":
		if meeting.is_user_approved(guest_id) or is_creator or is_invited:
			if (is_creator or is_invited) and guest_id not in meeting.get_members():
				meeting.add_guest_to_members(guest_id)
			from meet.api.integration import record_meeting_guest

			record_meeting_guest(
				meeting, guest_name_clean, guest_id=guest_id, guest_email=session_payload["user_email"]
			)
			auth_token = _generate_sfu_token(
				user_id=guest_id,
				meeting_id=meeting_id,
				expires_in=24 * 3600,
				user_name=guest_name_clean,
				is_host=is_creator,
				is_guest=True,
			)
			return {
				"status": "joined",
				"meeting_id": meeting_id,
				"guest_id": guest_id,
				"guest_name": guest_name_clean,
				"auth_token": auth_token,
				"sfu_url": sfu_config["sfu_server_url"],
				"sfu_port": sfu_config["sfu_server_port"],
				"host_only_chat": bool(meeting.host_only_chat),
				"is_host": is_creator,
				"is_creator": is_creator,
				"message": "Successfully joined meeting",
			}
		elif guest_id not in meeting.get_waiting_room():
			meeting.add_guest_to_waiting_room(guest_id)

		return {
			"status": "waiting_for_approval",
			"meeting_id": meeting_id,
			"guest_id": guest_id,
			"guest_name": guest_name_clean,
			"message": "Waiting for host approval",
			"host_only_chat": bool(meeting.host_only_chat),
			"is_host": False,
			"is_creator": False,
		}

	# open meeting
	auth_token = _generate_sfu_token(
		user_id=guest_id,
		meeting_id=meeting_id,
		expires_in=24 * 3600,
		user_name=guest_name_clean,
		is_host=is_creator,
		is_guest=True,
	)

	meeting.add_guest_to_members(guest_id)
	from meet.api.integration import record_meeting_guest
	record_meeting_guest(
		meeting, guest_name_clean, guest_id=guest_id, guest_email=session_payload["user_email"]
	)

	return {
		"status": "joined",
		"meeting_id": meeting_id,
		"guest_id": guest_id,
		"guest_name": guest_name_clean,
		"auth_token": auth_token,
		"sfu_url": sfu_config["sfu_server_url"],
		"sfu_port": sfu_config["sfu_server_port"],
		"host_only_chat": bool(meeting.host_only_chat),
		"is_host": is_creator,
		"is_creator": is_creator,
		"message": "Successfully joined meeting",
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def get_approved_guest_connection_details(meeting_id: str, guest_id: str) -> dict:
	"""
	Get SFU connection details for an approved guest.
	This is called after a guest receives approval notification.
	"""
	session_data = get_guest_session(guest_id)
	if not session_data:
		frappe.throw(_("Guest session not found or expired"))

	if not frappe.db.exists("Sae Meeting", meeting_id):
		frappe.throw(_("Meeting not found"))

	meeting = frappe.get_doc("Sae Meeting", meeting_id)
	if meeting.is_deleted:
		frappe.throw(_("Meeting is no longer available"), frappe.PermissionError)
	if session_data.get("meeting_id") != meeting_id:
		frappe.throw(_("Guest session does not belong to this meeting"), frappe.PermissionError)

	if meeting.is_user_banned(guest_id):
		return {
			"status": "rejected",
			"meeting_id": meeting_id,
			"guest_id": guest_id,
		}

	if not meeting.is_user_approved(guest_id):
		return {
			"status": "waiting_for_approval",
			"meeting_id": meeting_id,
			"guest_id": guest_id,
		}

	sfu_config = get_sfu_config()

	guest_name = session_data.get("guest_name", f"Guest-{guest_id[:8]}")
	from meet.api.integration import record_meeting_guest

	record_meeting_guest(
		meeting,
		guest_name,
		guest_id=guest_id,
		guest_email=session_data.get("user_email"),
	)

	auth_token = _generate_sfu_token(
		user_id=guest_id,
		meeting_id=meeting_id,
		expires_in=24 * 3600,
		user_name=guest_name,
		is_host=False,
		is_guest=True,
	)

	return {
		"status": "joined",
		"meeting_id": meeting_id,
		"guest_id": guest_id,
		"guest_name": guest_name,
		"auth_token": auth_token,
		"sfu_url": sfu_config["sfu_server_url"],
		"sfu_port": sfu_config["sfu_server_port"],
		"host_only_chat": bool(meeting.host_only_chat),
		"message": "Successfully joined meeting",
	}


@frappe.whitelist(allow_guest=True)
def get_guest_sfu_connection_details(meeting_id: str, guest_token: str) -> dict:
	"""
	Get SFU connection details for guest users.
	Validates the guest token and returns SFU URL/port.
	"""
	sfu_config = get_sfu_config()
	secret = sfu_config.get("sfu_secret") or frappe.conf.get("secret_key")
	if not secret:
		frappe.throw(_("SFU secret not configured"))

	try:
		decoded = jwt.decode(guest_token, secret, algorithms=["HS256"])
	except jwt.ExpiredSignatureError:
		frappe.throw(_("Guest token has expired"))
	except jwt.InvalidTokenError:
		frappe.throw(_("Invalid guest token"))

	if not decoded.get("is_guest"):
		frappe.throw(_("Not a guest token"))

	if decoded.get("meeting_id") != meeting_id:
		frappe.throw(_("Token meeting ID does not match"))

	if not frappe.db.exists("Sae Meeting", meeting_id):
		frappe.throw(_("Meeting not found"))

	return {
		"sfu_url": sfu_config["sfu_server_url"],
		"sfu_port": sfu_config["sfu_server_port"],
		"codec_strategy": _get_codec_strategy(),
	}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=10, seconds=60 * 60)
def validate_guest_session(guest_id: str) -> dict:
	"""
	Validate that a guest session exists and is active.

	Args:
		guest_id: The guest ID to validate

	Returns:
		dict: {"valid": bool}
	"""
	if not guest_id or not guest_id.startswith("guest_"):
		return {"valid": False, "error": "Invalid guest ID format"}

	session_data = get_guest_session(guest_id)
	if not session_data:
		return {"valid": False, "error": "Guest session not found"}

	return {
		"valid": True,
	}


@frappe.whitelist(allow_guest=True)
def promote_to_cohost(meeting_id: str, user_id: str, guest_id: str | None = None) -> dict:
	"""
	Promote a user to co-host during an active meeting (host only)
	"""
	meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
	caller = _get_meeting_caller(meeting, guest_id)
	if not caller or not meeting.is_host_or_cohost(caller):
		frappe.throw(_("Only the meeting host can promote users to co-host"), frappe.PermissionError)
	return meeting.promote_to_cohost(caller, user_id)


@frappe.whitelist(allow_guest=True)
def check_meeting_access(meeting_id: str) -> dict:
	"""
	Check if a meeting allows guest access without authentication

	Args:
		meeting_id: The meeting ID to check

	Returns:
		dict: Access information for the meeting
	"""
	try:
		if not meeting_id or not frappe.db.exists("Sae Meeting", meeting_id):
			frappe.throw(_("Meeting not found"), frappe.DoesNotExistError)

		meeting: SaeMeeting = frappe.get_doc("Sae Meeting", meeting_id)
		if meeting.is_deleted:
			frappe.throw(_("Meeting is no longer available"), frappe.PermissionError)

		settings = frappe.get_cached_doc("Sae Settings")
		allow_guest = bool(settings.allow_guest and meeting.allow_guest)

		return {
			"exists": True,
			"title": meeting.meeting_title or meeting.name,
			"allow_guest": allow_guest,
			"meeting_type": meeting.meeting_type,
			"host_only_chat": bool(meeting.host_only_chat),
		}
	except frappe.DoesNotExistError:
		frappe.throw(_("Meeting not found"), frappe.DoesNotExistError)
	except Exception as e:
		frappe.throw(str(e))
