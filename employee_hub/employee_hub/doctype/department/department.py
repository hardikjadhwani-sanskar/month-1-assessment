# Copyright (c) 2026, hardik and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

class Department(Document):
    def validate(self):
        self.department_name = self.department_name.strip()
        self.validate_unique_department_name()

    def validate_unique_department_name(self):
        existing = frappe.db.sql("""
            SELECT name FROM `tabDepartment`
            WHERE LOWER(department_name) = LOWER(%s)
            AND name != %s
        """, (self.department_name, self.name))

        if existing:
            frappe.throw("Department Name must be unique (case-insensitive).")


    
    
	
	
