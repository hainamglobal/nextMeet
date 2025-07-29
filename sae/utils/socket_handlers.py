# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json

import frappe

from sae.utils.sfu_manager import ensure_sfu_connection


@frappe.whitelist()
def handle_webrtc_signal(meeting_id, type, signal_data, target_user=None):
	"""Handle WebRTC signaling events from client"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Get SFU manager
		sfu_manager = ensure_sfu_connection()

		# Prepare relay data with consistent format
		relay_data = {
			"fromUser": frappe.session.user,
			"targetUser": target_user,
			"roomId": meeting_id,
			"signalData": signal_data,
			"signalType": type,
			"timestamp": frappe.utils.now(),
		}

		# Map signal types to SFU events
		sfu_event_map = {
			"offer": "webrtc_offer",
			"answer": "webrtc_answer",
			"ice-candidate": "ice_candidate",
			"producer": "create_producer",
			"consumer": "create_consumer",
			"connect_transport": "connect_transport",
			"produce": "produce",
			"consume": "consume",
			"get_router_capabilities": "get_router_capabilities",
			"create_transport": "create_transport",
		}

		sfu_event = sfu_event_map.get(type, type)
		sfu_manager.relay_to_sfu(sfu_event, relay_data, meeting_id)

		frappe.logger().info(f"WebRTC signal {type} relayed to SFU for meeting {meeting_id}")

	except Exception as e:
		frappe.log_error(f"Error handling WebRTC signal: {e}")
		frappe.publish_realtime(
			"webrtc_signal_error",
			{"error": str(e), "signal_type": type, "meeting_id": meeting_id},
			user=frappe.session.user,
		)


@frappe.whitelist()
def handle_join_meeting(meeting_id):
	"""Handle meeting join request from client"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Get meeting document
		meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Join the meeting
		meeting.join(frappe.session.user)

		user = frappe.db.get_value("User", frappe.session.user, ["full_name", "user_image"], as_dict=True)

		# Prepare user data for SFU
		enhanced_user_data = {
			"name": user.get("full_name") or frappe.session.user,
			"email": frappe.session.user,
			"avatar": user.get("user_image") or "",
			"userId": frappe.session.user,
			# **user_data
		}

		# Join room on SFU
		sfu_manager = ensure_sfu_connection()
		success = sfu_manager.join_room(meeting_id, frappe.session.user, enhanced_user_data)

		if success:
			# Send confirmation back to client
			frappe.publish_realtime(
				"meeting_joined_success",
				{
					"meeting_id": meeting_id,
					"user_id": frappe.session.user,
					"user_data": enhanced_user_data,
					"members": meeting.get_members(),
					"sfu_connected": True,
				},
				user=frappe.session.user,
			)

			# Request router RTP capabilities from SFU
			sfu_manager.relay_to_sfu(
				"get_router_capabilities", {"roomId": meeting_id, "userId": frappe.session.user}, meeting_id
			)

			frappe.logger().info(f"User {frappe.session.user} successfully joined meeting {meeting_id}")

			# Return success response for the API call
			return {
				"status": "success",
				"meeting_id": meeting_id,
				"user_id": frappe.session.user,
				"user_data": enhanced_user_data,
				"members": meeting.get_members(),
				"sfu_connected": True,
				"message": "Successfully joined meeting",
			}
		else:
			raise Exception("Failed to join SFU room")

	except Exception as e:
		frappe.log_error(f"Error joining meeting: {e}")
		frappe.publish_realtime(
			"meeting_join_error", {"error": str(e), "meeting_id": meeting_id}, user=frappe.session.user
		)
		frappe.throw(f"Failed to join meeting: {e}")


@frappe.whitelist()
def handle_leave_meeting(meeting_id):
	"""Handle meeting leave request from client"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Get meeting document
		meeting = frappe.get_doc("Sae Meeting", meeting_id)

		# Leave room on SFU first
		sfu_manager = ensure_sfu_connection()
		success = sfu_manager.leave_room(meeting_id, frappe.session.user)

		# Leave the meeting in Frappe
		meeting.leave(frappe.session.user)

		# Send confirmation back to client
		frappe.publish_realtime(
			"meeting_left_success",
			{"meeting_id": meeting_id, "user_id": frappe.session.user, "sfu_disconnected": success},
			user=frappe.session.user,
		)

		frappe.logger().info(f"User {frappe.session.user} successfully left meeting {meeting_id}")

		# Return success response for the API call
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"user_id": frappe.session.user,
			"sfu_disconnected": success,
			"message": "Successfully left meeting",
		}

	except Exception as e:
		frappe.log_error(f"Error leaving meeting: {e}")
		frappe.publish_realtime(
			"meeting_leave_error", {"error": str(e), "meeting_id": meeting_id}, user=frappe.session.user
		)
		frappe.throw(f"Failed to leave meeting: {e}")


@frappe.whitelist()
def handle_media_control(meeting_id, action):
	"""Handle media control events (mute/unmute, camera on/off)"""
	try:
		if not meeting_id or not action:
			frappe.throw("Meeting ID and action are required")

		# Relay to SFU
		sfu_manager = ensure_sfu_connection()
		relay_data = {
			"userId": frappe.session.user,
			"roomId": meeting_id,
			"action": action,
			"timestamp": frappe.utils.now(),
		}
		sfu_manager.relay_to_sfu("media_control", relay_data, meeting_id)

	except Exception as e:
		frappe.log_error(f"Error handling media control: {e}")
		frappe.throw(f"Failed to handle media control: {e}")


@frappe.whitelist()
def handle_screen_share(meeting_id, action, share_data=None):
	"""Handle screen sharing events"""
	try:
		if not meeting_id or not action:
			frappe.throw("Meeting ID and action are required")

		# Relay to SFU
		sfu_manager = ensure_sfu_connection()
		relay_data = {
			"userId": frappe.session.user,
			"roomId": meeting_id,
			"action": action,
			"shareData": share_data or {},
			"timestamp": frappe.utils.now(),
		}
		sfu_manager.relay_to_sfu("screen_share", relay_data, meeting_id)

	except Exception as e:
		frappe.log_error(f"Error handling screen share: {e}")
		frappe.throw(f"Failed to handle screen share: {e}")


@frappe.whitelist()
def handle_chat_message(meeting_id, message):
	"""Handle chat messages in meeting"""
	try:
		if not meeting_id or not message:
			frappe.throw("Meeting ID and message are required")

		# Get meeting document
		meeting = frappe.get_doc("Sae Meeting", meeting_id)
		members = meeting.get_members()

		# Create chat message data
		chat_data = {
			"meeting_id": meeting_id,
			"user_id": frappe.session.user,
			"user_name": frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user,
			"message": message,
			"timestamp": frappe.utils.now(),
		}

		# Send to all members
		for member in members:
			frappe.publish_realtime("meeting_chat_message", chat_data, user=member)

	except Exception as e:
		frappe.log_error(f"Error handling chat message: {e}")
		frappe.throw(f"Failed to handle chat message: {e}")


@frappe.whitelist()
def handle_get_router_capabilities(meeting_id):
	"""Handle request for router RTP capabilities from SFU"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Get capabilities directly from SFU with callback
		sfu_manager = ensure_sfu_connection()
		rtp_capabilities = sfu_manager.get_router_rtp_capabilities(meeting_id)

		# Also send via real-time event for socket listeners
		frappe.publish_realtime(
			"router_rtp_capabilities",
			{"rtpCapabilities": rtp_capabilities, "meeting_id": meeting_id, "user_id": frappe.session.user},
			user=frappe.session.user,
		)

		# Return capabilities directly in the API response
		return {
			"status": "success",
			"rtpCapabilities": rtp_capabilities,
			"meeting_id": meeting_id,
			"message": "Router capabilities retrieved successfully",
		}

	except Exception as e:
		frappe.log_error(f"Error getting router capabilities: {e}")
		frappe.publish_realtime("router_capabilities_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to request router capabilities: {e}")


@frappe.whitelist()
def handle_create_transport(meeting_id, transport_type="send", options=None):
	"""Handle WebRTC transport creation request"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Validate transport type
		if transport_type not in ["send", "recv"]:
			frappe.throw("Transport type must be 'send' or 'recv'")

		# Create transport through SFU
		sfu_manager = ensure_sfu_connection()
		transport_options = sfu_manager.create_webrtc_transport(
			meeting_id, frappe.session.user, transport_type
		)

		# Return success response with transport options
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"transport_type": transport_type,
			"transportOptions": transport_options,
			"message": "Transport created successfully",
		}

	except Exception as e:
		frappe.log_error(f"Error creating transport: {e}")
		frappe.publish_realtime("transport_creation_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to create transport: {e}")


@frappe.whitelist()
def handle_connect_transport(meeting_id, transport_id, dtls_parameters):
	"""Handle WebRTC transport connection"""
	try:
		if not meeting_id or not transport_id or not dtls_parameters:
			frappe.throw("Meeting ID, transport ID, and DTLS parameters are required")

		# Send transport connection to SFU
		sfu_manager = ensure_sfu_connection()
		sfu_manager.relay_to_sfu(
			"connect_transport",
			{
				"roomId": meeting_id,
				"userId": frappe.session.user,
				"transportId": transport_id,
				"dtlsParameters": dtls_parameters,
			},
			meeting_id,
		)

		# Return success response
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"transport_id": transport_id,
			"message": "Transport connection request sent to SFU",
		}

	except Exception as e:
		frappe.log_error(f"Error connecting transport: {e}")
		frappe.publish_realtime("transport_connection_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to connect transport: {e}")


@frappe.whitelist()
def handle_produce_media(meeting_id, transport_id, kind, rtp_parameters, paused=False, app_data=None):
	"""Handle media production (sending audio/video)"""
	try:
		if not all([meeting_id, transport_id, kind, rtp_parameters]):
			frappe.throw("Meeting ID, transport ID, kind, and RTP parameters are required")

		# Send produce request to SFU
		sfu_manager = ensure_sfu_connection()
		sfu_manager.relay_to_sfu(
			"produce",
			{
				"roomId": meeting_id,
				"userId": frappe.session.user,
				"transportId": transport_id,
				"kind": kind,
				"rtpParameters": rtp_parameters,
				"paused": paused,
				"appData": app_data or {},
			},
			meeting_id,
		)

		# Return success response
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"transport_id": transport_id,
			"kind": kind,
			"message": "Media production request sent to SFU",
		}

	except Exception as e:
		frappe.log_error(f"Error producing media: {e}")
		frappe.publish_realtime("produce_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to produce media: {e}")


@frappe.whitelist()
def handle_consume_media(meeting_id, producer_id, rtp_capabilities, paused=False):
	"""Handle media consumption (receiving audio/video)"""
	try:
		if not all([meeting_id, producer_id, rtp_capabilities]):
			frappe.throw("Meeting ID, producer ID, and RTP capabilities are required")

		# Send consume request to SFU
		sfu_manager = ensure_sfu_connection()
		sfu_manager.relay_to_sfu(
			"consume",
			{
				"roomId": meeting_id,
				"userId": frappe.session.user,
				"producerId": producer_id,
				"rtpCapabilities": rtp_capabilities,
				"paused": paused,
			},
			meeting_id,
		)

		# Return success response
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"producer_id": producer_id,
			"message": "Media consumption request sent to SFU",
		}

	except Exception as e:
		frappe.log_error(f"Error consuming media: {e}")
		frappe.publish_realtime("consume_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to consume media: {e}")


@frappe.whitelist()
def handle_pause_resume_producer(meeting_id, producer_id, action):
	"""Handle pausing/resuming media producer"""
	try:
		if not all([meeting_id, producer_id, action]):
			frappe.throw("Meeting ID, producer ID, and action are required")

		# Send pause/resume request to SFU
		sfu_manager = ensure_sfu_connection()
		sfu_manager.relay_to_sfu(
			f"{action}_producer",
			{"roomId": meeting_id, "userId": frappe.session.user, "producerId": producer_id},
			meeting_id,
		)

		# Return success response
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"producer_id": producer_id,
			"action": action,
			"message": f"Producer {action} request sent to SFU",
		}

	except Exception as e:
		frappe.log_error(f"Error {action} producer: {e}")
		frappe.publish_realtime("producer_control_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to {action} producer: {e}")


@frappe.whitelist()
def handle_pause_resume_consumer(meeting_id, consumer_id, action):
	"""Handle pausing/resuming media consumer"""
	try:
		if not all([meeting_id, consumer_id, action]):
			frappe.throw("Meeting ID, consumer ID, and action are required")

		# Send pause/resume request to SFU
		sfu_manager = ensure_sfu_connection()
		sfu_manager.relay_to_sfu(
			f"{action}_consumer",
			{"roomId": meeting_id, "userId": frappe.session.user, "consumerId": consumer_id},
			meeting_id,
		)

		# Return success response
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"consumer_id": consumer_id,
			"action": action,
			"message": f"Consumer {action} request sent to SFU",
		}

	except Exception as e:
		frappe.log_error(f"Error {action} consumer: {e}")
		frappe.publish_realtime("consumer_control_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to {action} consumer: {e}")


@frappe.whitelist()
def handle_get_existing_producers(meeting_id):
	"""Get existing producers in a meeting for new participants"""
	try:
		if not meeting_id:
			frappe.throw("Meeting ID is required")

		# Get existing producers from SFU
		sfu_manager = ensure_sfu_connection()
		producers_data = sfu_manager.get_existing_producers(meeting_id, frappe.session.user)

		# Return success response with producers data
		return {
			"status": "success",
			"meeting_id": meeting_id,
			"producers": producers_data or [],
			"message": "Existing producers retrieved successfully",
		}

	except Exception as e:
		frappe.log_error(f"Error getting existing producers: {e}")
		frappe.publish_realtime("existing_producers_error", {"error": str(e)}, user=frappe.session.user)
		frappe.throw(f"Failed to get existing producers: {e}")


# Event handler mapping for socket events
SOCKET_EVENTS = {
	"webrtc_signal": handle_webrtc_signal,
	"join_meeting": handle_join_meeting,
	"leave_meeting": handle_leave_meeting,
	"media_control": handle_media_control,
	"screen_share": handle_screen_share,
	"chat_message": handle_chat_message,
	"get_router_capabilities": handle_get_router_capabilities,
	"create_transport": handle_create_transport,
	"connect_transport": handle_connect_transport,
	"produce_media": handle_produce_media,
	"consume_media": handle_consume_media,
	"pause_resume_producer": handle_pause_resume_producer,
	"pause_resume_consumer": handle_pause_resume_consumer,
	"get_existing_producers": handle_get_existing_producers,
}
