import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data     = get_data(filters)
    chart    = get_chart(data)
    return columns, data, None, chart


# ─────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────
def get_columns():
    return [
        {
            "label"    : "Department",
            "fieldname": "department",
            "fieldtype": "Link",
            "options"  : "Department",
            "width"    : 180,
        },
        {
            "label"    : "Total Employees",
            "fieldname": "total_employees",
            "fieldtype": "Int",
            "width"    : 140,
        },
        {
            "label"    : "Active Employees",
            "fieldname": "active_employees",
            "fieldtype": "Int",
            "width"    : 150,
        },
        {
            "label"    : "Inactive / Terminated",
            "fieldname": "inactive_terminated",
            "fieldtype": "Int",
            "width"    : 170,
        },
        {
            "label"    : "Avg Leave Balance",
            "fieldname": "avg_leave_balance",
            "fieldtype": "Float",
            "width"    : 160,
        },
        {
            "label"    : "Top Skill",
            "fieldname": "top_skill",
            "fieldtype": "Data",
            "width"    : 160,
        },
    ]


# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
def get_data(filters):
    conditions, values = _build_conditions(filters)

    # ── Main summary query ────────────────────
    main_query = """
        SELECT
            e.department,
            COUNT(e.name)                                           AS total_employees,
            SUM(CASE WHEN e.employee_status = 'Active' THEN 1 ELSE 0 END)
                                                                    AS active_employees,
            SUM(CASE WHEN e.employee_status IN ('Inactive','Terminated') THEN 1 ELSE 0 END)
                                                                    AS inactive_terminated,
            ROUND(AVG(e.annual_leave_balance), 2)                   AS avg_leave_balance
        FROM
            `tabEmployee` e
        WHERE
            e.docstatus < 2
            {conditions}
        GROUP BY
            e.department
        ORDER BY
            total_employees DESC
    """.format(conditions=conditions)

    rows = frappe.db.sql(main_query, values, as_dict=True)

    if not rows:
        return []

    # ── Top skill per department ──────────────
    departments = [r["department"] for r in rows if r["department"]]
    top_skills  = _get_top_skills(departments)

    for row in rows:
        row["top_skill"] = top_skills.get(row["department"], "—")

    return rows


def _build_conditions(filters):
    conditions = ""
    values     = {}

    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
        values["department"] = filters["department"]

    if filters.get("employee_status"):
        conditions += " AND e.employee_status = %(employee_status)s"
        values["employee_status"] = filters["employee_status"]

    return conditions, values


def _get_top_skills(departments):
    """
    For each department return the most frequently listed skill
    across all Employee Skill child-table rows.
    Uses a subquery rank so we get exactly one skill per department
    even on MySQL 5.7 (no WINDOW functions needed).
    """
    if not departments:
        return {}

    # Build a safe IN clause placeholder
    placeholders = ", ".join(["%s"] * len(departments))

    query = """
        SELECT
            dept_skill.department,
            dept_skill.skill,
            dept_skill.skill_count
        FROM (
            SELECT
                e.department,
                es.skill,
                COUNT(es.skill)  AS skill_count
            FROM
                `tabEmployee Skill` es
            INNER JOIN
                `tabEmployee` e ON e.name = es.parent
            WHERE
                e.department IN ({placeholders})
                AND e.docstatus < 2
                AND es.skill IS NOT NULL
                AND es.skill != ''
            GROUP BY
                e.department,
                es.skill
        ) AS dept_skill
        INNER JOIN (
            SELECT
                department,
                MAX(skill_count) AS max_count
            FROM (
                SELECT
                    e2.department,
                    es2.skill,
                    COUNT(es2.skill) AS skill_count
                FROM
                    `tabEmployee Skill` es2
                INNER JOIN
                    `tabEmployee` e2 ON e2.name = es2.parent
                WHERE
                    e2.department IN ({placeholders})
                    AND e2.docstatus < 2
                    AND es2.skill IS NOT NULL
                    AND es2.skill != ''
                GROUP BY
                    e2.department,
                    es2.skill
            ) AS inner_counts
            GROUP BY
                department
        ) AS dept_max
            ON  dept_skill.department = dept_max.department
            AND dept_skill.skill_count = dept_max.max_count
        GROUP BY
            dept_skill.department
    """.format(placeholders=placeholders)

    # departments list passed twice (once for each IN clause)
    skill_rows = frappe.db.sql(query, departments + departments, as_dict=True)

    return {r["department"]: r["skill"] for r in skill_rows}


# ─────────────────────────────────────────────
# CHART
# ─────────────────────────────────────────────
def get_chart(data):
    if not data:
        return None

    labels          = [r["department"]         for r in data]
    total_values    = [r["total_employees"]     for r in data]
    active_values   = [r["active_employees"]    for r in data]
    inactive_values = [r["inactive_terminated"] for r in data]

    return {
        "data": {
            "labels"  : labels,
            "datasets": [
                {
                    "name"  : "Total Employees",
                    "values": total_values,
                    "chartType": "bar",
                },
                {
                    "name"  : "Active",
                    "values": active_values,
                    "chartType": "bar",
                },
                {
                    "name"  : "Inactive / Terminated",
                    "values": inactive_values,
                    "chartType": "bar",
                },
            ],
        },
        "type"       : "bar",
        "colors"     : ["#2d6a9f", "#28a745", "#dc3545"],
        "barOptions" : {"stacked": 0, "spaceRatio": 0.3},
        "axisOptions": {"xIsSeries": 1},
        "height"     : 300,
    }