# Employee Hub

A custom Frappe application for managing employees, leave requests,
and HR workflows. Built as a standalone module with role-based access control,
configurable leave policies, and a structured approval workflow.

---

## Table of Contents

- [App Description](#app-description)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [DocType List](#doctype-list)
- [Roles and Permissions](#roles-and-permissions)
- [Workflow](#workflow)
- [Configuration](#configuration)
- [Reports and Print Formats](#reports-and-print-formats)
- [Assumptions](#assumptions)

---

## App Description

Employee Hub provides a complete HR management layer on top of Frappe Framework.
It covers the full employee lifecycle — from onboarding and profile management
to leave applications and HR approvals — without depending on ERPNext's built-in
HR module.

### Key Features

- Employee profiles with photo, skills, blood group, and leave balance tracking
- Leave request creation, submission, and structured HR approval workflow
- Configurable leave policies via a Single DocType (no hardcoded limits)
- Role-based access — employees see only their own data
- Script report for department-wise employee summary with bar chart
- ID card print format with photo, barcode-style footer, and auto company name

---

## Tech Stack

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Framework    | Frappe v16                  |
| Backend      | Python 3.14+ , Node 24+                    |
| Frontend     | Frappe JS (client scripts)        |
| Database     | MariaDB 10.6+                     |
| Templating   | Jinja2 (print formats)            |
| Styles       | Inline CSS + app_include_css      |

---

## Setup Instructions

### 1. Prerequisites

Ensure you have a working Frappe bench setup:

```bash
# Frappe bench must already be installed
bench --version

# MariaDB and Redis must be running
sudo systemctl status mariadb
sudo systemctl status redis
```

### 2. Get the App

```bash
# Navigate to your bench directory


# Get the app from your repository
bench get-app employee_hub https://github.com/hardikjadhwani-sanskar/month-1-assessment.git
```

### 3. Install on Your Site

```bash
bench --site your-site-name install-app employee_hub
```

### 4. Run Migrations

This applies all fixtures (roles, workflow, custom fields, permissions):

```bash
bench --site your-site-name migrate
```

### 5. Build Assets

Compiles and serves the custom CSS and JS files:

```bash
bench --site your-site-name build --app employee_hub
```

### 6. Restart Bench

```bash
bench restart
```

### 7. Verify Installation

Log in as Administrator and confirm the following are present:

```
✓ Module "Employee Hub" appears in the desk sidebar
✓ Role: HR Admin exists
✓ Role: Employee exists
✓ Workflow: Leave Approval Workflow is active on Leave Request
✓ Leave Configuration Single DocType is accessible under Settings
✓ Custom field blood_group appears on the Employee form
✓ Print Format: Employee ID Card is available on Employee
✓ Report: Department Wise Employee Summary is accessible
```

---

## Configuration

### Step 1 — Create HR Admin User

```
Search → User → New

Email         : hradmin@yourcompany.com
First Name    : HR Admin
Roles         :
  ├── HR Admin
  └── Employee


```

### Step 2 — Create Employee Record for HR Admin

```
Search → Employee → New

First Name      : HR Admin
Last Name       : User
Employee Email  : hradmin@yourcompany.com   ← must match User email exactly
Department      : Human Resources
Designation     : HR Manager
Date of Birth   : (any valid date, 18+ years ago)
Date of Joining : (today or earlier)

Save → Employee ID auto-generated (EMP-YYYY-NNNNN)
```

### Step 3 — Create Employee Users

For each employee repeat:

```
1. Search → User → New
   Email    : john@yourcompany.com
   Roles    : Employee

2. Search → Employee → New
   employee_email : john@yourcompany.com   ← must match User email
   department, designation, etc.
   
```
### User Credentials - created for testing purposes

```
1. Administrator role 
   id - Administrator
   password - President@2014

2. Employee role
   id - karan@sanskar.io
   password - sanskar

3. HR Admin role
   id - priya@sanskar.io
   password- sanskar

```


### Step 4 — Configure Leave Policy 

```
Search → Leave Configuration → open the single record

max_casual_leave           : 12   (default)
max_sick_leave             : 6    (default)
max_earned_leave           : 15   (default)
default_annual_balance     : 24   (default)
allow_backdated_leave      : No   (default)
max_leave_days_per_request : 15   (default)

Adjust as per your company policy and Save.
```

---

## DocType List

### Core DocTypes

| DocType              | Type         | Description                                                      |
|----------------------|--------------|------------------------------------------------------------------|
| Employee             | Standard     | Employee profile with personal details, skills, and leave balance|
| Employee Skill       | Child Table  | Skills linked to an Employee with proficiency and experience     |
| Leave Request        | Submittable  | Leave application created by employee, approved by HR Admin      |
| Leave Configuration  | Single       | Company-wide leave policy settings, accessible under Settings    |

### Supporting DocTypes (used via Link fields)

| DocType     | Type     | Description                                      |
|-------------|----------|--------------------------------------------------|
| Department  | Standard | Organisational departments                       |
| Designation | Standard | Job titles linked to departments                 |
| Skill       | Standard | Skill master list referenced in Employee Skills  |

---

## DocType Field Reference

### Employee

| Field                | Type         | Notes                                              |
|----------------------|--------------|----------------------------------------------------|
| first_name           | Data         | Mandatory                                          |
| last_name            | Data         | Mandatory                                          |
| full_name            | Data         | Read-only, auto-generated on before_save           |
| employee_email       | Data         | Mandatory, unique — must match the User login email|
| phone                | Data         |                                                    |
| date_of_birth        | Date         | Mandatory, must be 18+ years before today          |
| date_of_joining      | Date         | Mandatory, must not be in the future               |
| department           | Link         | Mandatory → Department                             |
| designation          | Link         | Mandatory → Designation (filtered by department)   |
| reporting_manager    | Link         | Self-link → Employee                               |
| employee_status      | Select       | Active / Inactive / On Leave / Terminated          |
| annual_leave_balance | Int          | Read-only, default from Leave Configuration        |
| profile_photo        | Attach Image |                                                    |
| address              | Small Text   |                                                    |
| blood_group          | Select       | Custom field: A+ A- B+ B- AB+ AB- O+ O-           |
| skills               | Table        | Child table → Employee Skill                       |

**Naming Series:** `EMP-.YYYY.-.#####`

---

### Employee Skill (Child Table)

| Field               | Type   | Notes                                           |
|---------------------|--------|-------------------------------------------------|
| skill               | Link   | Mandatory → Skill                               |
| proficiency         | Select | Beginner / Intermediate / Advanced / Expert     |
| years_of_experience | Float  |                                                 |
| notes               | Small Text |                                             |

---

### Leave Request

| Field           | Type      | Notes                                                   |
|-----------------|-----------|---------------------------------------------------------|
| employee        | Link      | Mandatory → Employee                                    |
| employee_name   | Data      | fetch_from employee.full_name, read-only                |
| department      | Link      | fetch_from employee.department, read-only               |
| from_date       | Date      | Mandatory, cannot be in the past                        |
| to_date         | Date      | Mandatory, must be >= from_date                         |
| total_days      | Float     | Read-only, auto-calculated                              |
| leave_type      | Select    | Casual / Sick / Earned / Compensatory Leave             |
| reason          | Text      | Mandatory                                               |
| approval_status | Select    | Pending / Approved / Rejected / Cancelled (workflow)    |
| approved_by     | Link      | Read-only → User, auto-set on approval              |
| approval_date   | Datetime  | Read-only, auto-set on approval                         |
| rejection_reason| Small Text| Required when HR Admin rejects                          |

**Naming Series:** `LR-.YYYY.-.#####`
**Is Submittable:** Yes

---

### Leave Configuration (Single)

| Field                    | Type  | Default |
|--------------------------|-------|---------|
| max_casual_leave         | Int   | 12      |
| max_sick_leave           | Int   | 6       |
| max_earned_leave         | Int   | 15      |
| default_annual_balance   | Int   | 24      |
| allow_backdated_leave    | Check | 0       |
| max_leave_days_per_request | Int | 15      |

---

## Roles and Permissions

### HR Admin 

| DocType             | Read | Write | Create | Delete | Submit | Cancel |
|---------------------|------|-------|--------|--------|--------|--------|
| Employee            | ✓    | ✓     | ✓      | ✓      | —      | —      |
| Leave Request       | ✓    | ✓     | ✓      | ✓      | ✓      | ✓      |
| Department          | ✓    | ✓     | ✓      | ✓      | —      | —      |
| Designation         | ✓    | ✓     | ✓      | ✓      | —      | —      |
| Skill               | ✓    | ✓     | ✓      | ✓      | —      | —      |
| Leave Configuration | ✓    | ✓     | ✓      | —      | —      | —      |


### Employee (role)

| DocType       | Read     | Write    | Create   | Delete | Submit   | If Owner |
|---------------|----------|----------|----------|--------|----------|----------|
| Employee      | ✓        | —        | —        | —      | —        | -        |
| Leave Request | ✓        | ✓        | ✓        | —      | ✓        | -        |
| Department    | ✓        | —        | —        | —      | —        | —        |
| Designation   | ✓        | —        | —        | —      | —        | —        |
| Skill         | ✓        | —        | —        | —      | —        | —        |


---

## Workflow

### Leave Approval Workflow

Applied on: **Leave Request**
Workflow State Field: `approval_status`

| Current State | Action | Role     | Next State |
|---------------|--------|----------|------------|  
| Pending       | Approve| HR Admin | Approved   |
| Pending       | Reject | HR Admin | Rejected   |
| Approved      | Cancel | HR Admin | Cancelled  |



---

## Reports and Print Formats

### Department Wise Employee Summary (Script Report)

**Location:** Employee Hub → Reports

**Columns:**

| Column               | Description                                      |
|----------------------|--------------------------------------------------|
| Department           | Department name                                  |
| Total Employees      | All employees in the department                  |
| Active Employees     | Employees with status = Active                   |
| Inactive/Terminated  | Employees with status Inactive or Terminated     |
| Avg Leave Balance    | Average annual_leave_balance across department   |
| Top Skill            | Most common skill across employees in department |

**Filters:** Department (Link), Employee Status (Select)

**Chart:** Grouped bar chart — Total vs Active vs Inactive per department


---

### Employee ID Card (Print Format)

**DocType:** Employee

**Contains:**
- Profile photo (initials avatar fallback if no photo)
- Full name and designation pill
- Employee ID badge strip
- Department, Date of Joining, Email, Phone
- Decorative barcode-style footer
- Company name auto-pulled from site defaults

**How to use:**
```
Open any Employee record → Print → Select "Employee ID Card"
```

---

## Assumptions

1. **One User per Employee** — each employee has exactly one User account
   and one Employee record. They are linked by `employee_email = User.email`.
   The system does not support multiple User accounts per employee.

2. **HR Admin should have it's own Employee record** — the `approved_by` field links
   to User. 

3. **Leave balance is calendar-year based** — `annual_leave_balance` is a
   flat integer on the Employee record. There is no automatic yearly reset
   or carry-forward logic in this version. Reset must be done manually or
   via a scheduled script.


4. **Weekends and holidays are not excluded** — `total_days` is calculated
   as a simple calendar day difference (`date_diff + 1`). Working day
   calendars and holiday lists are not factored in this version.

5. **Designation must belong to a Department** — the client script filters
   the Designation Link field based on the selected Department. Designations
   without a linked Department will not appear in the dropdown.


6. **Frappe v16** — this app is developed and tested on Frappe v16. 
    Compatibility with earlier versions is not guaranteed due to
   use of `before_workflow_action` hook and `frappe.get_cached_doc`.

7. **Leave Configuration must be saved once** — the Single DocType
    `Leave Configuration` ships with default values in field definitions
    but must be opened and saved at least once after installation for
    `frappe.get_cached_doc` to return values correctly.

---

## Development

### Export Fixtures After Changes

```bash
bench --site your-site-name export-fixtures --app employee_hub
```

### Run After Any Code Change

```bash
bench --site your-site-name migrate
bench --site your-site-name build --app employee_hub
bench restart
```


