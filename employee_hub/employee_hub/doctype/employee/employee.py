# Copyright (c) 2026, hardik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today
import re

class Employee(Document):

    def before_save(self):
        self.set_full_name()

    def validate(self):
        self.validate_age()
        self.validate_joining_date()
        self.validate_email()
        self.validate_dob_vs_joining()



    def set_full_name(self):
        self.full_name = f"{self.first_name.strip()} {self.last_name.strip()}"

    def validate_age(self):
        if self.date_of_birth:
            dob = getdate(self.date_of_birth)
            today_date = getdate(today())

            age = (today_date - dob).days / 365

            if age < 18:
                frappe.throw("Employee must be at least 18 years old.")

    def validate_joining_date(self):
        if self.date_of_joining:
            if getdate(self.date_of_joining) > getdate(today()):
                frappe.throw("Date of Joining cannot be in the future.")

    def validate_email(self):
        if self.employee_email:
            pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not re.match(pattern, self.employee_email):
                frappe.throw("Invalid Email Format.")

    def validate_dob_vs_joining(self):
        if self.date_of_birth and self.date_of_joining:
            if getdate(self.date_of_joining) <= getdate(self.date_of_birth):
                frappe.throw("Date of Joining must be after Date of Birth.")


def get_permission_query_conditions(user=None):
    """
    Appended as a WHERE clause to every Employee list/search query.

    HR Admin    → "" (no restriction, all records visible)
    Employee    → filters to only the row where employee_email = session user
    """
    if not user:
        user = frappe.session.user

    if "HR Admin" in frappe.get_roles(user) or user == "Administrator":
        return ""

    return f"""(
        `tabEmployee`.`employee_email` = {frappe.db.escape(user)}
    )"""


def has_permission(doc, ptype="read", user=None):
    """
    Guards individual document access.
    Called when a user opens a specific Employee record directly.

    HR Admin    → always True
    Employee    → True only if doc.employee_email matches their login
    """
    if not user:
        user = frappe.session.user

    if "HR Admin" in frappe.get_roles(user) or user == "Administrator":
        return True

    return doc.employee_email == user