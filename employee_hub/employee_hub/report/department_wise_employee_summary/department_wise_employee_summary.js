frappe.query_reports["Department Wise Employee Summary"] = {

    filters: [
        {
            fieldname: "department",
            fieldtype: "Link",
            options  : "Department",
            label    : __("Department"),
        },
        {
            fieldname: "employee_status",
            fieldtype: "Select",
            label    : __("Employee Status"),
            options  : [
                { value: "",            label: __("All")        },
                { value: "Active",      label: __("Active")     },
                { value: "Inactive",    label: __("Inactive")   },
                { value: "On Leave",    label: __("On Leave")   },
                { value: "Terminated",  label: __("Terminated") },
            ],
        },
    ],

    // ── Triggered when any filter value changes ──
    onload(report) {
        // Auto-run the report on load with no filters
        report.refresh();
    },

    // ── Format cell values for better readability ──
    formatter(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname === "active_employees") {
            value = `<span style="color:#28a745;font-weight:600;">${value}</span>`;
        }

        if (column.fieldname === "inactive_terminated") {
            value = `<span style="color:#dc3545;font-weight:600;">${value}</span>`;
        }

        if (column.fieldname === "avg_leave_balance") {
            if (data && data.avg_leave_balance <= 5) {
                value = `<span style="color:#fd7e14;font-weight:600;">${value}</span>`;
            }
        }

        if (column.fieldname === "top_skill" && value && value !== "—") {
            value = `<span style="background:#e8f0fe;color:#2d6a9f;
                         padding:2px 10px;border-radius:12px;
                         font-size:11px;font-weight:600;">
                         ${value}
                     </span>`;
        }

        return value;
    },
};