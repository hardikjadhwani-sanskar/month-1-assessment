app_name = "employee_hub"
app_title = "Employee Hub"
app_publisher = "hardik"
app_description = "app for employee functionality"
app_email = "hardik.jadhwani@sanskartechnolab.com"
app_license = "mit"

# ─────────────────────────────────────────────
# DOC EVENTS
# ─────────────────────────────────────────────
# doc_events = {
#     # "Employee": {
#     #     "before_save": (
#     #         "employee_hub.employee_hub.doctype"
#     #         ".employee.employee.before_save"
#     #     ),
#     # },
#     "Leave Request": {
#         "before_workflow_action": (
#             "employee_hub.employee_hub.doctype.leave_request.leave_request.before_workflow_action"
#         ),
#     },
# }

# ─────────────────────────────────────────────
# PERMISSION QUERY CONDITIONS
# ─────────────────────────────────────────────
permission_query_conditions = {
    "Employee": (
        "employee_hub.employee_hub.doctype"
        ".employee.employee.get_permission_query_conditions"
    ),
}

has_permission = {
    "Employee": (
        "employee_hub.employee_hub.doctype"
        ".employee.employee.has_permission"
    ),
}

# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────
fixtures = [
    {
        "dt"     : "Role",
        "filters": [
            ["role_name", "in", ["HR Admin", "Employee"]]
        ],
    },
    {
        "dt"     : "Workflow",
        "filters": [
            ["name", "=", "Leave Approval Workflow"]
        ],
    },
    {
        "dt"     : "Workflow State",
        "filters": [
            ["name", "in", [
                "Pending", "Approved", "Rejected", "Cancelled"
            ]]
        ],
    },
    {
        "dt"     : "Workflow Action Master",
        "filters": [
            ["name", "in", [
                "Submit", "Approve", "Reject",
                "Cancel"
            ]]
        ],
    },
    {
        "dt"     : "Custom Field",
        "filters": [
            ["dt", "in", ["Employee", "Leave Request"]]
        ],
    },
    {
        "dt"     : "Property Setter",
        "filters": [
            ["doc_type", "in", [
                "Employee", "Leave Request",
                "Department", "Designation", "Skill"
            ]]
        ],
    },
    {
        "dt"     : "Custom DocPerm",
        "filters": [
            ["parent", "in", [
                "Employee", "Leave Request",
                "Department", "Designation",
                "Skill", "Leave Configuration"
            ]]
        ],
    },
    {
        "dt"     : "Report",
        "filters": [
            ["name", "=", "Department Wise Employee Summary"]
        ],
    },
    {
        "dt"     : "Print Format",
        "filters": [
            ["name", "=", "Employee ID Card"]
        ],
    },
]

# ─────────────────────────────────────────────
# GLOBAL ASSETS
# ─────────────────────────────────────────────
app_include_css = [
    "/assets/employee_hub/css/employee_hub.css"
]

app_include_js = [
    "/assets/employee_hub/js/employee_hub.js"
]
