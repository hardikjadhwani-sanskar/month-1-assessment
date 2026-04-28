(function () {
    "use strict";

    // ── App loaded confirmation ───────────────────────────────────────────
    console.log("Employee Hub App Loaded");

    // ── Utility: check if the current user has a given role ──────────────
    function userHasRole(role) {
        return (frappe.user_roles || []).includes(role);
    }

    // ── Global list view enhancements ────────────────────────────────────
    $(document).on("page-change", function () {
        const route = frappe.get_route();
        if (!route) return;

        // Employee list — highlight terminated rows
        if (route[0] === "List" && route[1] === "Employee") {
            _applyEmployeeListStyles();
        }

        // Leave Request list — colour approval_status cells
        if (route[0] === "List" && route[1] === "Leave Request") {
            _applyLeaveStatusBadges();
        }
    });

    function _applyEmployeeListStyles() {
        $(".list-row").each(function () {
            const status = $(this).attr("data-employee_status");
            if (status === "Terminated") {
                $(this).css("opacity", "0.55");
            }
            if (status === "On Leave") {
                $(this).css("border-left", "3px solid #fb923c");
            }
        });
    }

    function _applyLeaveStatusBadges() {
        $(".list-row").each(function () {
            const cell = $(this).find("[data-fieldname='approval_status']");
            if (!cell.length) return;

            const status = cell.text().trim();
            const classMap = {
                "Pending" : "approval-pending",
                "Approved": "approval-approved",
                "Rejected": "approval-rejected",
            };
            const cls = classMap[status];
            if (cls) {
                cell.find(".text-muted, span").addBack()
                    .wrapInner(`<span class="${cls}"></span>`);
            }
        });
    }

    // ── Global form enhancements ──────────────────────────────────────────
    frappe.ui.form.on("Employee", {
        refresh(frm) {
            // Show leave balance as a coloured indicator in the form header
            if (frm.doc.annual_leave_balance !== undefined) {
                const balance = frm.doc.annual_leave_balance;
                const color   = balance > 10 ? "green"
                              : balance > 5  ? "orange"
                              :                "red";
                frm.dashboard.add_indicator(
                    __("Leave Balance: {0}", [balance]),
                    color
                );
            }
        }
    });

    frappe.ui.form.on("Leave Request", {
        refresh(frm) {
            // Show a banner based on approval_status
            const banners = {
                "Pending" : { msg: "This leave request is awaiting HR approval.", color: "yellow" },
                "Approved": { msg: "This leave request has been approved.",        color: "green"  },
                "Rejected": { msg: "This leave request was rejected.",             color: "red"    },
            };
            const banner = banners[frm.doc.approval_status];
            if (banner && frm.doc.docstatus === 1) {
                frm.dashboard.set_headline_alert(
                    `<div class="alert alert-${banner.color === "yellow" ? "warning"
                                             : banner.color === "green"  ? "success"
                                             :                             "danger"}"
                          style="margin:0;padding:8px 14px;font-size:12px;">
                        ${__(banner.msg)}
                    </div>`
                );
            }
        }
    });

})();