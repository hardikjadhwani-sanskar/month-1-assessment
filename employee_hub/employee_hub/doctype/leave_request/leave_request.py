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
        limit  = config["max_leave_days_per_request"]
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
            "Casual Leave"      : config["max_casual_leave"],
            "Sick Leave"        : config["max_sick_leave"],
            "Earned Leave"      : config["max_earned_leave"],
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
        balance = frappe.db.get_value(
            "Employee", self.employee, "annual_leave_balance"
        )
        if balance is None:
            frappe.throw(
                f"Could not fetch leave balance for employee {self.employee}."
            )
        if self.total_days > balance:
            frappe.throw(
                f"Insufficient leave balance. "
                f"Requested: {self.total_days} day(s), "
                f"Available: {balance} day(s)."
            )

    def _check_overlapping_leaves(self):
        """
        Block if this employee already has an Approved or Pending
        submitted leave request whose date range overlaps with this one.
        Both Approved and Pending are checked to prevent double-booking
        before HR Admin even approves.
        """
        if not self.employee or not self.from_date or not self.to_date:
            return

        overlapping = frappe.db.sql(
            """
            SELECT
                name,
                from_date,
                to_date,
                approval_status
            FROM
                `tabLeave Request`
            WHERE
                employee        = %(employee)s
                AND docstatus   = 1
                AND approval_status IN ('Approved', 'Pending')
                AND name       != %(name)s
                AND NOT (
                    to_date   < %(from_date)s
                    OR from_date > %(to_date)s
                )
            """,
            {
                "employee" : self.employee,
                "name"     : self.name or "",
                "from_date": self.from_date,
                "to_date"  : self.to_date,
            },
            as_dict=True,
        )

        if overlapping:
            lines = []
            for r in overlapping:
                lines.append(
                    f"• {r.name} ({r.approval_status}): "
                    f"{frappe.utils.formatdate(r.from_date)} "
                    f"to {frappe.utils.formatdate(r.to_date)}"
                )
            frappe.throw(
                "Leave dates overlap with the following existing "
                "leave request(s) for this employee:\n\n"
                + "\n".join(lines)
            )

    # ─────────────────────────────────────────────
    # ON SUBMIT
    # ─────────────────────────────────────────────
    def on_submit(self):
        # Document submitted by Employee.
        # approval_status stays Pending.
        # Workflow engine takes over from here.
        self.db_set("approval_status", "Pending")

    # ─────────────────────────────────────────────
    # BEFORE WORKFLOW ACTION
    # Fires when HR Admin clicks Approve / Reject / Cancel
    # ─────────────────────────────────────────────
    def before_workflow_action(self, action):
        if action == "Approve":
            self._handle_approve()
        elif action == "Reject":
            self._handle_reject()
        elif action == "Cancel":
            self._handle_cancel()

    def _handle_approve(self):
        self._assert_hr_admin()

        # Resolve HR Admin's Employee record from session email
        approved_by_employee = frappe.db.get_value(
            "Employee",
            {"employee_email": frappe.session.user},
            "name"
        )
        if not approved_by_employee:
            frappe.throw(
                f"No Employee record found for the logged-in user "
                f"({frappe.session.user}). "
                f"The approver must have an Employee record "
                f"with a matching employee_email."
            )

        # Re-validate balance at point of approval
        # (balance may have changed since submission)
        balance = frappe.db.get_value(
            "Employee", self.employee, "annual_leave_balance"
        )
        if self.total_days > (balance or 0):
            frappe.throw(
                f"Cannot approve. Insufficient leave balance for "
                f"{self.employee_name}. "
                f"Available: {balance} day(s), "
                f"Requested: {self.total_days} day(s)."
            )

        # Re-check overlaps at point of approval
        self._check_overlapping_leaves()

        # Persist approval metadata
        self.db_set("approved_by",   approved_by_employee)
        self.db_set("approval_date", now_datetime())

        # Deduct leave balance
        self._adjust_leave_balance(multiplier=-1)

        frappe.msgprint(
            f"Leave approved. {self.total_days} day(s) deducted "
            f"from {self.employee_name}'s balance.",
            alert=True,
            indicator="green"
        )

    def _handle_reject(self):
        self._assert_hr_admin()

        # rejection_reason is mandatory — HR Admin must fill it
        # on the form before clicking Reject
        if not self.rejection_reason or not self.rejection_reason.strip():
            frappe.throw(
                "Rejection Reason is mandatory. "
                "Please fill in the Rejection Reason field "
                "before rejecting this leave request."
            )

        frappe.msgprint(
            f"Leave request rejected for {self.employee_name}.",
            alert=True,
            indicator="red"
        )

    def _handle_cancel(self):
        self._assert_hr_admin()

        # Fetch the approval_status that is currently saved in DB
        # (self.approval_status may already reflect the new state)
        current_status = frappe.db.get_value(
            "Leave Request", self.name, "approval_status"
        )

        # Only restore balance if the leave was approved
        if current_status == "Approved":
            self._adjust_leave_balance(multiplier=1)

            # Restore employee_status if they were marked On Leave
            current_emp_status = frappe.db.get_value(
                "Employee", self.employee, "employee_status"
            )
            if current_emp_status == "On Leave":
                frappe.db.set_value(
                    "Employee",
                    self.employee,
                    "employee_status",
                    "Active"
                )

        frappe.msgprint(
            f"Leave request cancelled for {self.employee_name}.",
            alert=True,
            indicator="orange"
        )

    # ─────────────────────────────────────────────
    # ON CANCEL (fallback — outside workflow)
    # ─────────────────────────────────────────────
    def on_cancel(self):
        current_status = frappe.db.get_value(
            "Leave Request", self.name, "approval_status"
        )
        if current_status == "Approved":
            self._adjust_leave_balance(multiplier=1)

        current_emp_status = frappe.db.get_value(
            "Employee", self.employee, "employee_status"
        )
        if current_emp_status == "On Leave":
            frappe.db.set_value(
                "Employee", self.employee, "employee_status", "Active"
            )

    # ─────────────────────────────────────────────
    # SHARED HELPERS
    # ─────────────────────────────────────────────
    def _assert_hr_admin(self):
        if "HR Admin" not in frappe.get_roles(frappe.session.user):
            frappe.throw(
                "Only HR Admins can perform this action.",
                frappe.PermissionError
            )

    def _adjust_leave_balance(self, multiplier: int):
        """
        multiplier = -1  →  deduct  (on approve)
        multiplier = +1  →  restore (on cancel)
        """
        if not self.employee or not self.total_days:
            return

        current_balance = frappe.db.get_value(
            "Employee", self.employee, "annual_leave_balance"
        )
        if current_balance is None:
            frappe.throw(
                f"Could not update leave balance for "
                f"employee {self.employee}."
            )

        new_balance = current_balance + (multiplier * self.total_days)
        frappe.db.set_value(
            "Employee",
            self.employee,
            "annual_leave_balance",
            new_balance
        )