# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.realtime import emit_via_redis

from sae.utils.socket_handlers import SOCKET_EVENTS


def setup_realtime_listeners():
	"""Setup real-time event listeners for Sae socket events"""

	# Map real-time events to socket handlers
	realtime_event_map = {
		"sae_webrtc_signal": "webrtc_signal",
		"sae_join_meeting": "join_meeting",
		"sae_leave_meeting": "leave_meeting",
		"sae_media_control": "media_control",
		"sae_screen_share": "screen_share",
		"sae_chat_message": "chat_message",
		"sae_get_router_capabilities": "get_router_capabilities",
		"sae_create_transport": "create_transport",
		"sae_connect_transport": "connect_transport",
		"sae_produce_media": "produce_media",
		"sae_consume_media": "consume_media",
		"sae_pause_resume_producer": "pause_resume_producer",
		"sae_pause_resume_consumer": "pause_resume_consumer",
		"sae_user_disconnect": "user_disconnect",
	}

	for realtime_event, socket_event in realtime_event_map.items():
		frappe.realtime.on(realtime_event, create_event_handler(socket_event))


def create_event_handler(socket_event):
	"""Create a handler function for a specific socket event"""

	def handler(data):
		"""Handle real-time event and forward to socket handler"""
		try:
			# Extract user from data
			user = data.get("from_user")
			if user:
				# Set user context for the handler
				frappe.set_user(user)

			# Remove metadata fields
			clean_data = {k: v for k, v in data.items() if k not in ["from_user", "timestamp"]}

			# Get the appropriate socket handler
			if socket_event in SOCKET_EVENTS:
				handler_func = SOCKET_EVENTS[socket_event]
				handler_func(clean_data)
			elif socket_event == "user_disconnect":
				handle_user_disconnect(clean_data)
			else:
				frappe.logger().warning(f"No handler found for socket event: {socket_event}")

		except Exception as e:
			frappe.log_error(f"Error handling real-time event {socket_event}: {e!s}")

			# Send error back to user if possible
			if user:
				frappe.publish_realtime(f"{socket_event}_error", {"error": str(e)}, user=user)

	return handler


def handle_user_disconnect(data):
	"""Handle user disconnection cleanup"""
	try:
		user = data.get("user")
		if not user:
			return

		# Find all active meetings for this user
		meetings = frappe.get_all("Sae Meeting", filters={"status": "Active"}, fields=["name"])

		from sae.utils.sfu_manager import get_sfu_manager

		sfu_manager = get_sfu_manager()

		for meeting in meetings:
			meeting_doc = frappe.get_doc("Sae Meeting", meeting.name)
			if user in meeting_doc.get_members():
				# Leave the meeting
				try:
					meeting_doc.leave(user)
					sfu_manager.leave_room(meeting.name, user)
					frappe.logger().info(f"Cleaned up user {user} from meeting {meeting.name}")
				except Exception as e:
					frappe.logger().error(f"Error cleaning up user {user} from meeting {meeting.name}: {e!s}")

	except Exception as e:
		frappe.log_error(f"Error in user disconnect cleanup: {e!s}")


@frappe.whitelist()
def initialize_realtime_bridge():
	"""Initialize the real-time bridge - called from hooks"""
	try:
		setup_realtime_listeners()
		frappe.logger().info("Sae real-time bridge initialized successfully")
		return True
	except Exception as e:
		frappe.log_error(f"Failed to initialize Sae real-time bridge: {e!s}")
		return False


# Auto-initialize when module is imported
if frappe.local.conf.get("auto_init_sae_bridge", True):
	try:
		setup_realtime_listeners()
	except Exception as e:
		frappe.logger().warning(f"Could not auto-initialize Sae real-time bridge: {e!s}")
