frappe.ui.form.on("Leave Request", {

    // ── Auto fill employee on new form ────────────────────────────────────
    onload(frm) {
        if (frm.is_new() && !frappe.user.has_role("HR Admin")) {
            _set_employee_from_session(frm);
        }
    },

    refresh(frm) {
        _setReadOnlyFields(frm);
        _updateTotalDaysLabel(frm);
        _lockEmployeeField(frm);
        _showStatusBanner(frm);
        _handleRejectionReasonVisibility(frm);
        _showLeaveBalanceInfo(frm);
    },

    from_date(frm) {
        _calculateTotalDays(frm);
        _warnIfPast(frm);
    },

    to_date(frm) {
        _calculateTotalDays(frm);
    },

    employee(frm) {
        if (!frm.doc.employee) {
            frm.set_value("employee_name", "");
            frm.set_value("department",    "");
        }
    },
});


// ── Auto fill employee from session ───────────────────────────────────────

function _set_employee_from_session(frm) {
    frappe.call({
        method  : "frappe.client.get_list",
        args    : {
            doctype : "Employee",
            filters : { employee_email: frappe.session.user },
            fields  : ["name", "full_name", "department",
                       "annual_leave_balance"],
            limit   : 1,
        },
        callback(r) {
            if (r.message && r.message.length > 0) {
                const emp = r.message[0];
                frm.set_value("employee",      emp.name);
                frm.set_value("employee_name", emp.full_name);
                frm.set_value("department",    emp.department);
                _lockEmployeeField(frm);

                // Show available balance as a hint
                frappe.show_alert({
                    message  : __("Available Leave Balance: {0} day(s)",
                                  [emp.annual_leave_balance]),
                    indicator: emp.annual_leave_balance > 5
                                 ? "green" : "orange",
                });
            } else {
                frappe.msgprint({
                    title    : __("Employee Record Not Found"),
                    message  : __(
                        "No Employee record is linked to your account "
                        + "({0}). Please contact HR Admin.",
                        [frappe.session.user]
                    ),
                    indicator: "red",
                });
            }
        },
    });
}


// ── Lock employee field for non HR Admin ──────────────────────────────────

function _lockEmployeeField(frm) {
    const isHrAdmin = frappe.user.has_role("HR Admin");
    frm.set_df_property("employee",      "read_only", isHrAdmin ? 0 : 1);
    frm.set_df_property("employee_name", "read_only", 1);
    frm.set_df_property("department",    "read_only", 1);
}


// ── Rejection reason visibility ───────────────────────────────────────────
// Shows to HR Admin on Pending submitted docs so they can fill
// it before clicking the workflow Reject button.
// Always visible when status is already Rejected / Cancelled.

function _handleRejectionReasonVisibility(frm) {
    const isHrAdmin       = frappe.user.has_role("HR Admin");
    const isPendingSubmit = frm.doc.docstatus === 1
                         && frm.doc.approval_status === "Pending";
    const isRejected      = ["Rejected", "Cancelled"]
                             .includes(frm.doc.approval_status);

    const shouldShow = isRejected || (isHrAdmin && isPendingSubmit);
    frm.toggle_display("rejection_reason", shouldShow);

    if (isHrAdmin && isPendingSubmit) {
        // Make it visually obvious the field must be filled before rejecting
        frm.set_df_property(
            "rejection_reason",
            "description",
            "⚠ Fill this before clicking Reject."
        );
        frm.set_df_property("rejection_reason", "bold", 1);
    } else {
        frm.set_df_property("rejection_reason", "description", "");
        frm.set_df_property("rejection_reason", "bold", 0);
    }
}


// ── Leave balance indicator on form ──────────────────────────────────────

function _showLeaveBalanceInfo(frm) {
    if (!frm.doc.employee || frm.doc.docstatus !== 0) return;

    frappe.call({
        method  : "frappe.client.get_value",
        args    : {
            doctype   : "Employee",
            filters   : { name: frm.doc.employee },
            fieldname : "annual_leave_balance",
        },
        callback(r) {
            if (!r.message) return;
            const balance = r.message.annual_leave_balance;
            const color   = balance > 10 ? "green"
                          : balance > 5  ? "orange"
                          :                "red";
            frm.dashboard.add_indicator(
                __("Leave Balance: {0} day(s)", [balance]),
                color
            );
        },
    });
}


// ── Status banner ─────────────────────────────────────────────────────────

function _showStatusBanner(frm) {
    if (frm.doc.docstatus !== 1) return;

    const approvalDate = frm.doc.approval_date
        ? frappe.datetime.str_to_user(frm.doc.approval_date)
        : "—";

    const config = {
        "Pending": {
            msg: "Awaiting HR Admin approval.",
            cls: "alert-warning",
        },
        "Approved": {
            msg: `Approved by <b>${frm.doc.approved_by || "HR Admin"}</b>`
               + ` on ${approvalDate}.`,
            cls: "alert-success",
        },
        "Rejected": {
            msg: `Rejected. Reason: <b>${frm.doc.rejection_reason || "—"}</b>`,
            cls: "alert-danger",
        },
        "Cancelled": {
            msg: "This leave request has been cancelled.",
            cls: "alert-secondary",
        },
    };

    const banner = config[frm.doc.approval_status];
    if (!banner) return;

    frm.dashboard.set_headline_alert(
        `<div class="${banner.cls}"
              style="padding:8px 14px;font-size:12px;
                     border-radius:4px;margin-bottom:4px;">
            ${__(banner.msg)}
        </div>`
    );
}


// ── Read only guards ──────────────────────────────────────────────────────

function _setReadOnlyFields(frm) {
    ["approval_status", "approved_by", "approval_date", "total_days"]
        .forEach(f => frm.set_df_property(f, "read_only", 1));
}


// ── Total days ────────────────────────────────────────────────────────────

function _calculateTotalDays(frm) {
    const { from_date, to_date } = frm.doc;
    if (!from_date || !to_date) return;

    if (
        frappe.datetime.str_to_obj(to_date) <
        frappe.datetime.str_to_obj(from_date)
    ) {
        frappe.msgprint(__("To Date cannot be before From Date."));
        frm.set_value("total_days", 0);
        return;
    }

    const diff = frappe.datetime.get_diff(to_date, from_date) + 1;
    frm.set_value("total_days", diff);
    _updateTotalDaysLabel(frm);
}

function _updateTotalDaysLabel(frm) {
    if (frm.doc.total_days > 0) {
        frm.set_df_property(
            "total_days",
            "description",
            `${frm.doc.total_days} working day(s) requested`
        );
    }
}


// ── Past date warning ─────────────────────────────────────────────────────

function _warnIfPast(frm) {
    const from = frm.doc.from_date;
    if (
        from &&
        frappe.datetime.str_to_obj(from) <
        frappe.datetime.str_to_obj(frappe.datetime.get_today())
    ) {
        frappe.show_alert({
            message  : __("From Date is in the past."),
            indicator: "orange",
        });
    }
}