frappe.ui.form.on("Leave Request", {

    refresh(frm) {
        // Show rejection_reason only when cancelling / already rejected
        frm.toggle_display(
            "rejection_reason",
            ["Rejected", "Cancelled"].includes(frm.doc.approval_status)
        );

        // Read-only guard: approval block is always system-managed
        const approvalFields = [
            "approval_status", "approved_by", "approval_date"
        ];
        approvalFields.forEach(f => frm.set_df_property(f, "read_only", 1));

        // Recalculate display label when form loads
        _updateTotalDaysLabel(frm);
    },

    from_date(frm) {
        _calculateTotalDays(frm);
        _warnIfPast(frm);
    },

    to_date(frm) {
        _calculateTotalDays(frm);
    },

    before_submit: function(frm) {

        let message = `
            <b>Leave Request Summary:</b><br><br>
            Employee: ${frm.doc.employee}<br>
            From: ${frm.doc.from_date}<br>
            To: ${frm.doc.to_date}<br>
            Total Days: ${frm.doc.total_days}<br>
            Type: ${frm.doc.leave_type}
        `;

        frappe.confirm(
            message,
            () => {
                // user clicked YES → continue
                frm.submit();
            },
            () => {
                // user clicked NO → cancel
                frappe.validated = false;
            }
        );

        // stop default submit (important)
        frappe.validated = false;
    },

    employee(frm) {
        // Clear dependent fetched fields when employee changes
        if (!frm.doc.employee) {
            frm.set_value("employee_name", "");
            frm.set_value("department", "");
        }

        if (!frm.doc.employee) return;

        // Fetch leave balance from Employee
        frappe.db.get_value('Employee', frm.doc.employee, 'annual_leave_balance')
            .then(r => {
                let balance = r.message.annual_leave_balance || 0;

                frm.set_intro(
                    `Remaining Leave Balance: <b>${balance}</b> days`,
                    'blue'
                );
            });
    },
});


// ── Helpers ────────────────────────────────────────────────────────────────

function _calculateTotalDays(frm) {
    const { from_date, to_date } = frm.doc;
    if (!from_date || !to_date) return;

    const from = frappe.datetime.str_to_obj(from_date);
    const to   = frappe.datetime.str_to_obj(to_date);

    if (to < from) {
        frappe.msgprint(__("To Date cannot be before From Date."));
        frm.set_value("total_days", 0);
        return;
    }

    const diff = frappe.datetime.get_diff(to_date, from_date) + 1;
    frm.set_value("total_days", diff);
    _updateTotalDaysLabel(frm);
}

function _updateTotalDaysLabel(frm) {
    const days = frm.doc.total_days;
    if (days > 0) {
        frm.set_df_property(
            "total_days",
            "description",
            `${days} working day(s) requested`
        );
    }
}

function _warnIfPast(frm) {
    const from = frm.doc.from_date;
    if (from && frappe.datetime.str_to_obj(from) < frappe.datetime.str_to_obj(frappe.datetime.get_today())) {
        frappe.show_alert({
            message: __("From Date is in the past."),
            indicator: "orange"
        });
    }
}