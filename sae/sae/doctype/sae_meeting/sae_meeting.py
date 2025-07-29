# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import json
import random
import string

import frappe
from frappe.model.document import Document


class SaeMeeting(Document):
	def autoname(self):
		"""Set the name of the meeting"""
		if not self.name:
			self.name = generate()

	def before_insert(self):
		"""Initialize meeting room"""
		if not hasattr(self, "members") or not self.members:
			self.members = json.dumps([])
		if not hasattr(self, "is_active"):
			self.is_active = 1

	def after_insert(self):
		"""Notify room creation and auto-join creator"""
		self.notify_room_created()
		self.join(frappe.session.user)

	def join(self, user=None):
		"""
		Join the meeting room

		Args:
			user: User to join (defaults to current session user)
		"""
		if not user:
			user = frappe.session.user

		# Get current members list
		members = self.get_members()

		# Add user if not already in room
		if user not in members:
			members.append(user)
			self.update_members(members)

			# Notify all members about new user joining
			self.notify_member_joined(user)

		# Send join confirmation to the user
		frappe.publish_realtime(
			"sae_meeting_joined",
			{"meeting": self.name, "user": user, "members": members, "member_count": len(members)},
			user=user,
		)

	def leave(self, user=None):
		"""
		Leave the meeting room

		Args:
			user: User to remove (defaults to current session user)
		"""
		if not user:
			user = frappe.session.user

		# Get current members list
		members = self.get_members()

		# Remove user if in room
		if user in members:
			members.remove(user)
			self.update_members(members)

			# Notify remaining members about user leaving
			self.notify_member_left(user)

			# If no members left, mark room as inactive
			if not members:
				self.is_active = 0
				self.save(ignore_permissions=True)
				self.notify_room_closed()

	def get_members(self):
		"""Get list of current members"""
		try:
			return json.loads(self.members or "[]")
		except (json.JSONDecodeError, AttributeError):
			return []

	def can_join(self, user=None):
		"""
		Check if a user can join this meeting

		Args:
			user: User to check (defaults to current session user)

		Returns:
			bool: True if user can join, False otherwise
		"""
		if not user:
			user = frappe.session.user

		# Check if meeting is active
		# if not self.get("is_active", True):
		# 	return False

		# Check if user has read permission on the meeting
		# if not frappe.has_permission("Sae Meeting", "read", self):
		# 	return False

		# Additional checks can be added here (e.g., meeting capacity, invitation status, etc.)

		return True

	def update_members(self, members_list):
		"""Update members list and save"""
		self.members = json.dumps(members_list)
		self.save(ignore_permissions=True)

	def notify_room_created(self):
		"""Notify that room was created"""
		frappe.publish_realtime(
			"sae_meeting_created",
			{"meeting": self.name, "creator": frappe.session.user, "created_at": self.creation},
			doctype=self.doctype,
			docname=self.name,
		)

	def notify_member_joined(self, user):
		"""Notify all members that someone joined"""
		members = self.get_members()
		frappe.publish_realtime(
			"sae_meeting_member_joined",
			{"meeting": self.name, "user": user, "members": members, "member_count": len(members)},
			doctype=self.doctype,
			docname=self.name,
		)

	def notify_member_left(self, user):
		"""Notify remaining members that someone left"""
		members = self.get_members()
		frappe.publish_realtime(
			"sae_meeting_member_left",
			{"meeting": self.name, "user": user, "members": members, "member_count": len(members)},
			doctype=self.doctype,
			docname=self.name,
		)

	def notify_room_closed(self):
		"""Notify that room was closed due to no members"""
		frappe.publish_realtime(
			"sae_meeting_closed",
			{"meeting": self.name, "closed_at": frappe.utils.now()},
			doctype=self.doctype,
			docname=self.name,
		)

	def send_signal(self, signal_data, target_user=None):
		"""
		Send signaling data between members

		Args:
			signal_data: The signaling data to send
			target_user: Specific user to send to (if None, broadcasts to all)
		"""
		event_data = {"meeting": self.name, "from_user": frappe.session.user, "signal": signal_data}

		if target_user:
			# Send to specific user
			frappe.publish_realtime("sae_meeting_signal", event_data, user=target_user)
		else:
			# Broadcast to all members except sender
			members = self.get_members()
			for member in members:
				if member != frappe.session.user:
					frappe.publish_realtime("sae_meeting_signal", event_data, user=member)


def generate(segment_length=4, num_segments=3, separator="-"):
	# Define the character set: only lowercase letters
	characters = string.ascii_lowercase

	# Generate segments
	segments = []
	for _ in range(num_segments):
		segment = "".join(random.choice(characters) for _ in range(segment_length))
		segments.append(segment)

	# Join segments with the separator
	random_id = separator.join(segments)
	return random_id
