# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe

from sae.install import get_app_status, validate_config
from sae.utils.sfu_config import get_media_constraints, get_sfu_config, get_webrtc_config, validate_sfu_config
from sae.utils.sfu_manager import get_sfu_manager


@frappe.whitelist()
def get_sfu_status():
	"""Get the current status of SFU connection and configuration"""
	try:
		status = get_app_status()
		config = get_sfu_config()

		return {
			"success": True,
			"status": status,
			"config": {
				"sfu_server_url": config.get("sfu_server_url"),
				"sfu_server_port": config.get("sfu_server_port"),
				"sfu_timeout": config.get("sfu_timeout"),
				"enable_sfu_logging": config.get("enable_sfu_logging"),
			},
		}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_sfu_connection():
	"""Test the connection to SFU server"""
	try:
		validate_config()
		sfu_manager = get_sfu_manager()

		if not sfu_manager.connected:
			sfu_manager.connect_to_sfu()

		return {
			"success": True,
			"message": "Successfully connected to SFU server",
			"connected": sfu_manager.connected,
		}
	except Exception as e:
		frappe.log_error(f"SFU connection test failed: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_webrtc_configuration():
	"""Get WebRTC configuration for client"""
	try:
		return {"success": True, "config": get_webrtc_config()}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_media_configuration(quality="medium"):
	"""Get media constraints configuration for specified quality"""
	try:
		return {"success": True, "constraints": get_media_constraints(quality)}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def reconnect_sfu():
	"""Manually reconnect to SFU server"""
	try:
		sfu_manager = get_sfu_manager()

		# Disconnect if already connected
		if sfu_manager.connected:
			sfu_manager.disconnect_from_sfu()

		# Reconnect
		sfu_manager.connect_to_sfu()

		return {
			"success": True,
			"message": "Successfully reconnected to SFU server",
			"connected": sfu_manager.connected,
		}
	except Exception as e:
		frappe.log_error(f"SFU reconnection failed: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_active_meetings():
	"""Get list of currently active meetings"""
	try:
		# Get all active meetings from database
		meetings = frappe.get_all(
			"Sae Meeting", filters={"is_active": 1}, fields=["name", "creation", "members", "modified"]
		)

		# Parse members and add participant count
		for meeting in meetings:
			try:
				import json

				members = json.loads(meeting.get("members", "[]"))
				meeting["participant_count"] = len(members)
				meeting["participants"] = members
			except Exception as e:
				frappe.log_error(f"Failed to parse members for meeting {meeting.name}: {e!s}")
				# If parsing fails, set defaults
				meeting["participant_count"] = 0
				meeting["participants"] = []

		return {"success": True, "meetings": meetings}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def force_close_meeting(meeting_id):
	"""Force close a meeting (admin function)"""
	try:
		meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Mark as inactive
		meeting.is_active = 0
		meeting.save(ignore_permissions=True)

		# Notify all participants
		meeting.notify_room_closed()

		# Disconnect from SFU
		sfu_manager = get_sfu_manager()
		members = meeting.get_members()
		for member in members:
			sfu_manager.leave_room(meeting_id, member)

		return {"success": True, "message": f"Meeting {meeting_id} has been closed"}
	except Exception as e:
		frappe.log_error(f"Failed to force close meeting {meeting_id}: {e!s}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_meeting_analytics():
	"""Get analytics data for video conferencing usage"""
	try:
		# Get meeting statistics
		total_meetings = frappe.db.count("Sae Meeting")
		active_meetings = frappe.db.count("Sae Meeting", {"is_active": 1})

		# Get recent meeting activity (last 7 days)
		from frappe.utils import add_days, nowdate

		week_ago = add_days(nowdate(), -7)
		recent_meetings = frappe.db.count("Sae Meeting", {"creation": [">=", week_ago]})

		# Get most active users (by meeting participation)
		most_active_query = """
            SELECT COUNT(*) as meeting_count, creation
            FROM `tabSae Meeting`
            WHERE creation >= %s
            GROUP BY DATE(creation)
            ORDER BY creation DESC
            LIMIT 7
        """
		daily_usage = frappe.db.sql(most_active_query, (week_ago,), as_dict=True)

		return {
			"success": True,
			"analytics": {
				"total_meetings": total_meetings,
				"active_meetings": active_meetings,
				"recent_meetings": recent_meetings,
				"daily_usage": daily_usage,
			},
		}
	except Exception as e:
		return {"success": False, "error": str(e)}
