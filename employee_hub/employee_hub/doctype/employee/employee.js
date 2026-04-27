// Copyright (c) 2026, hardik and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee", {
    // Filter designation to only show those linked to the selected department
    department(frm) {
        frm.set_query("designation", () => {
            return {
                filters: {
                    department: frm.doc.department || ""
                }
            };
        });

        // Clear designation if department changes
        if (frm.doc.designation) {
            frm.set_value("designation", "");
        }
    },

    // Apply the filter on form load too (in case department is already set)
    refresh(frm) {
        frm.set_query("designation", () => {
            return {
                filters: {
                    department: frm.doc.department || ""
                }
            };
        });

        // Prevent manual edit of read-only computed fields
        frm.set_df_property("full_name", "read_only", 1);
        frm.set_df_property("employee_status", "read_only", 1);
        frm.set_df_property("annual_leave_balance", "read_only", 1);
    }
});