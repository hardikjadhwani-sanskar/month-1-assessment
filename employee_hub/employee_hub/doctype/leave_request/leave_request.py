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
        if not self.employee or not self.from_date or not self.to_date:
            return

        overlapping = frappe.db.sql(
            """
            SELECT name, from_date, to_date, approval_status
            FROM `tabLeave Request`
            WHERE
                employee = %(employee)s
                AND docstatus IN (0, 1)
                AND approval_status IN ('Approved', 'Pending')
                AND name != %(name)s
                AND NOT (
                    to_date < %(from_date)s
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
            lines = [
                f"• {r.name} ({r.approval_status}): "
                f"{frappe.utils.formatdate(r.from_date)} "
                f"to {frappe.utils.formatdate(r.to_date)}"
                for r in overlapping
            ]
            frappe.throw(
                "Leave dates overlap with the following existing "
                "leave request(s):\n\n" + "\n".join(lines)
            )

    # ─────────────────────────────────────────────
    # ON SUBMIT
    # Fires when HR Admin clicks Approve or reject
    # 
    # ─────────────────────────────────────────────
    def on_submit(self):
        frappe.logger().info(
            f"on_submit fired | "
            f"doc={self.name} | "
            f"approval_status={self.approval_status} | "
            f"user={frappe.session.user}"
        )

        # Only process if this is an approval
        # (approval_status will be Approved at this point
        # because workflow sets it before on_submit fires)
        if self.approval_status != "Approved":
            frappe.logger().info(
                f"on_submit: status is {self.approval_status} "
                f"not Approved — skipping balance deduction"
            )
            return

        # Resolve approver Employee record from session
        approved_by_employee = frappe.db.get_value(
            "Employee",
            {"employee_email": frappe.session.user},
            "name"
        )
        if not approved_by_employee:
            frappe.throw(
                f"No Employee record found for ({frappe.session.user}). "
                f"The approver must have an Employee record "
                f"with a matching employee_email."
            )

        # Re-validate balance at point of approval
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

        # Set approval metadata
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

    # ─────────────────────────────────────────────
    # ON CANCEL
    # Fires when HR Admin clicks Cancel
    # because Cancel moves docstatus 1 → 2
    # ─────────────────────────────────────────────
    def on_cancel(self):
        frappe.logger().info(
            f"on_cancel fired | "
            f"doc={self.name} | "
            f"user={frappe.session.user}"
        )

        # Restore balance only if it was approved
        was_approved = frappe.db.get_value(
            "Leave Request", self.name, "approved_by"
        )

        if was_approved:
            self._adjust_leave_balance(multiplier=1)

            # Restore employee status if On Leave
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
                frappe.db.commit()

            frappe.msgprint(
                f"Leave cancelled. {self.total_days} day(s) restored "
                f"to {self.employee_name}'s balance.",
                alert=True,
                indicator="orange"
            )

    # ─────────────────────────────────────────────
    # SHARED HELPER
    # ─────────────────────────────────────────────
    def _adjust_leave_balance(self, multiplier: int):
        """
        multiplier = -1  →  deduct  (on approve)
        multiplier = +1  →  restore (on cancel)
        """
        if not self.employee or not self.total_days:
            frappe.logger().info(
                "adjust_leave_balance: skipped — "
                "missing employee or total_days"
            )
            return

        # Read current balance via raw SQL
        result = frappe.db.sql(
            """
            SELECT annual_leave_balance
            FROM `tabEmployee`
            WHERE name = %s
            """,
            (self.employee,),
            as_dict=True
        )

        if not result:
            frappe.throw(
                f"Employee {self.employee} not found in database."
            )

        current_balance = result[0]["annual_leave_balance"] or 0
        new_balance     = current_balance + (multiplier * self.total_days)

        frappe.logger().info(
            f"adjust_leave_balance | "
            f"employee={self.employee} | "
            f"current={current_balance} | "
            f"multiplier={multiplier} | "
            f"days={self.total_days} | "
            f"new={new_balance}"
        )

        if new_balance < 0:
            frappe.throw(
                f"Leave balance cannot go below 0. "
                f"Current: {current_balance}, "
                f"Deduction: {self.total_days}."
            )

        # Write new balance via raw SQL
        frappe.db.sql(
            """
            UPDATE `tabEmployee`
            SET annual_leave_balance = %s
            WHERE name = %s
            """,
            (new_balance, self.employee)
        )
        frappe.db.commit()

        frappe.logger().info(
            f"Balance updated | "
            f"employee={self.employee} | "
            f"{current_balance} → {new_balance}"
        )