# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.rate_limiter import rate_limit


@frappe.whitelist()
@rate_limit(limit=10, seconds=60 * 60)
def create() -> str:
	meeting = frappe.get_doc(
		{
			"doctype": "Sae Meeting",
		}
	).insert()

	return meeting.name


@frappe.whitelist()
def get_sfu_connection_details(meeting_id: str) -> dict:
	"""
	Get SFU connection details for direct client-to-SFU communication
	"""
	try:
		# Validate meeting access
		meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Check if user can join this meeting
		if not meeting.can_join(frappe.session.user):
			return {"success": False, "error": "Access denied"}

		# Get SFU configuration
		from sae.utils.sfu_config import get_sfu_config

		sfu_config = get_sfu_config()

		# Create auth token for SFU access
		import time

		import jwt

		# Generate JWT token for SFU authentication
		user_fullname, user_avatar = frappe.db.get_value(
			"User", frappe.session.user, ["full_name", "user_image"]
		) or (frappe.session.user, None)

		auth_payload = {
			"user_id": frappe.session.user,
			"meeting_id": meeting_id,
			"user_name": user_fullname,
			"user_avatar": user_avatar,
			"exp": int(time.time()) + 3600,  # 1 hour expiry
			"iat": int(time.time()),
		}

		# Use SFU secret or fall back to site secret
		secret = sfu_config.get("sfu_secret") or frappe.conf.get("secret_key", "fallback-secret")
		auth_token = jwt.encode(auth_payload, secret, algorithm="HS256")

		return {
			"success": True,
			"sfu_url": sfu_config["sfu_server_url"],
			"sfu_port": sfu_config["sfu_server_port"],
			"auth_token": auth_token,
			"user_id": frappe.session.user,
			"meeting_id": meeting_id,
			"user_data": {"name": user_fullname, "email": frappe.session.user, "avatar": user_avatar},
		}
	except Exception as e:
		frappe.log_error(f"Failed to get SFU connection details for meeting {meeting_id}: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def join_meeting(meeting_id: str) -> dict:
	try:
		# Get meeting document
		meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Join the meeting in Frappe
		if meeting.can_join(frappe.session.user):
			return {
				"success": True,
				"meeting_id": meeting_id,
			}
		else:
			return {"success": False, "error": "Access denied"}
	except Exception as e:
		frappe.log_error(f"Failed to join meeting {meeting_id}: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def leave_meeting(meeting_id: str) -> dict:
	try:
		# Get meeting document
		# meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Leave the meeting in Frappe
		# meeting.leave(frappe.session.user)

		return {"success": True, "meeting_id": meeting_id, "user_id": frappe.session.user}
	except Exception as e:
		frappe.log_error(f"Failed to leave meeting {meeting_id}: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def cleanup_user_meetings(user_id: str | None = None) -> dict:
	"""
	Cleanup all meetings for a user (called when user disconnects)
	"""
	try:
		if not user_id:
			user_id = frappe.session.user

		# Find all active meetings for this user
		meetings = frappe.get_all("Sae Meeting", filters={"status": "Active"}, fields=["name"])

		cleaned_meetings = []

		for meeting in meetings:
			meeting_doc = frappe.get_doc("Sae Meeting", meeting.name)
			if user_id in meeting_doc.get_members():
				try:
					# Leave the meeting
					meeting_doc.leave(user_id)
					cleaned_meetings.append(meeting.name)
					frappe.logger().info(f"Cleaned up user {user_id} from meeting {meeting.name}")
				except Exception as e:
					frappe.logger().error(
						f"Error cleaning up user {user_id} from meeting {meeting.name}: {e!s}"
					)

		return {"success": True, "cleaned_meetings": cleaned_meetings, "user_id": user_id}
	except Exception as e:
		frappe.log_error(f"Error in user meeting cleanup: {e!s}")
		return {"success": False, "error": str(e)}
