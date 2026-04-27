# Copyright (c) 2026, hardik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LeaveConfiguration(Document):
	pass



def get_leave_config():
    
    config = frappe.get_cached_doc("Leave Configuration")
    return {
        "max_casual_leave":           config.max_casual_leave           or 12,
        "max_sick_leave":             config.max_sick_leave             or 6,
        "max_earned_leave":           config.max_earned_leave           or 15,
        "default_annual_balance":     config.default_annual_balance     or 24,
        "allow_backdated_leave":      config.allow_backdated_leave      or 0,
        "max_leave_days_per_request": config.max_leave_days_per_request or 15,
    }