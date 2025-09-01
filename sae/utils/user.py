# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.core.doctype.user.user import User


def assign_sae_role(user: User, method: str) -> None:
	"""Assign the "Sae User" role to a newly created User."""
	role_name = "Sae User"
	user_name = user.name

	if not user_name or user_name in ("Guest", "Administrator"):
		return

	if not frappe.db.exists("Role", role_name):
		frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)

	user_doc = frappe.get_doc("User", user_name)
	user_doc.add_roles(role_name)
