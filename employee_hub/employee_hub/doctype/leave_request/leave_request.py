# Copyright (c) 2026, hardik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, date_diff, now_datetime

from employee_hub.employee_hub.doctype.leave_configuration.leave_configuration import get_leave_config


class LeaveRequest(Document):

    # ─────────────────────────────────────────────
    # VALIDATE
    # ─────────────────────────────────────────────
    def validate(self):
        self._calculate_total_days()
        self._validate_date_range()
        self._validate_from_date_not_past()
        self._validate_total_days_limit()
        self._validate_leave_type_limit()
        self._validate_leave_balance()
        self._check_overlapping_leaves()

    def _calculate_total_days(self):
        if self.from_date and self.to_date:
            self.total_days = date_diff(self.to_date, self.from_date) + 1

    def _validate_date_range(self):
        if self.from_date and self.to_date:
            if getdate(self.to_date) < getdate(self.from_date):
                frappe.throw("To Date cannot be before From Date.")

    def _validate_from_date_not_past(self):
        config = get_leave_config()
        if config["allow_backdated_leave"]:
            return
        if self.from_date and getdate(self.from_date) < getdate(today()):
            frappe.throw("From Date cannot be in the past.")

    def _validate_total_days_limit(self):
        if not self.total_days:
            return
        config = get_leave_config()
        limit = config["max_leave_days_per_request"]
        if self.total_days > limit:
            frappe.throw(
                f"A single leave request cannot exceed {limit} day(s). "
                f"Requested: {self.total_days} day(s)."
            )

    def _validate_leave_type_limit(self):
        if not self.leave_type or not self.total_days:
            return
        config = get_leave_config()

        type_limits = {
            "Casual Leave":       config["max_casual_leave"],
            "Sick Leave":         config["max_sick_leave"],
            "Earned Leave":       config["max_earned_leave"],
            "Compensatory Leave": None,
        }

        limit = type_limits.get(self.leave_type)
        if limit is None:
            return

        if self.total_days > limit:
            frappe.throw(
                f"Maximum allowed days for {self.leave_type} is {limit}. "
                f"Requested: {self.total_days} day(s)."
            )

    def _validate_leave_balance(self):
        if not self.employee or not self.total_days:
            return
        balance = frappe.db.get_value("Employee", self.employee, "annual_leave_balance")
        if balance is None:
            frappe.throw(f"Could not fetch leave balance for employee {self.employee}.")
        if self.total_days > balance:
            frappe.throw(
                f"Insufficient leave balance. Requested: {self.total_days} day(s), "
                f"Available: {balance} day(s)."
            )

    def _check_overlapping_leaves(self):
        if not self.employee or not self.from_date or not self.to_date:
            return

        overlapping = frappe.db.sql(
            """
            SELECT name FROM `tabLeave Request`
            WHERE employee = %(employee)s
              AND docstatus = 1
              AND approval_status = 'Approved'
              AND name != %(name)s
              AND NOT (to_date < %(from_date)s OR from_date > %(to_date)s)
            """,
            {
                "employee": self.employee,
                "name": self.name or "",
                "from_date": self.from_date,
                "to_date": self.to_date,
            },
            as_dict=True,
        )

        if overlapping:
            refs = ", ".join(r.name for r in overlapping)
            frappe.throw(
                f"Leave dates overlap with existing approved request(s): {refs}."
            )

    # ─────────────────────────────────────────────
    # ON SUBMIT
    # ─────────────────────────────────────────────
    def on_submit(self):
        self._approve()

    def _approve(self):
        # approved_by_employee = frappe.db.get_value(
        #     "Employee",
        #     {"employee_email": frappe.session.user},
        #     "name"
        # )

        # if not approved_by_employee:
        #     frappe.throw(
        #         f"No Employee record found for the logged-in user ({frappe.session.user}). "
        #         "Only employees can approve leave requests."
        #     )

        
        self.db_set("approval_status", "Approved")
        self.db_set("approved_by", frappe.session.user)
        self.db_set("approval_date", now_datetime())

        # Deduct from employee's leave balance
        self._adjust_leave_balance(multiplier=-1)

    # ─────────────────────────────────────────────
    # ON CANCEL
    # ─────────────────────────────────────────────
    def on_cancel(self):
        self._cancel_leave()

    def _cancel_leave(self):
        # Read current approval_status before overwriting
        current_status = frappe.db.get_value(
            "Leave Request", self.name, "approval_status"
        )

        new_status = "Rejected" if self.rejection_reason else "Cancelled"
        self.db_set("approval_status", new_status)

        # Restore balance only if the request was previously approved
        if current_status == "Approved":
            self._adjust_leave_balance(multiplier=1)

        # Restore employee_status to Active if they were marked On Leave
        current_emp_status = frappe.db.get_value(
            "Employee", self.employee, "employee_status"
        )
        if current_emp_status == "On Leave":
            frappe.db.set_value(
                "Employee", self.employee, "employee_status", "Active"
            )

    # ─────────────────────────────────────────────
    # SHARED HELPER
    # ─────────────────────────────────────────────
    def _adjust_leave_balance(self, multiplier: int):
        """
        multiplier = -1  →  deduct  (on submit / approval)
        multiplier = +1  →  restore (on cancel)
        """
        if not self.employee or not self.total_days:
            return

        current_balance = frappe.db.get_value(
            "Employee", self.employee, "annual_leave_balance"
        )
        if current_balance is None:
            frappe.throw(
                f"Could not update leave balance for employee {self.employee}."
            )

        new_balance = current_balance + (multiplier * self.total_days)
        frappe.db.set_value(
            "Employee", self.employee, "annual_leave_balance", new_balance
        )