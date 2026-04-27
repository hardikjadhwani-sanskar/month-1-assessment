frappe.ui.form.on('Employee', {

    // ----------------------------
    // On Load / Refresh
    // ----------------------------
    refresh: function(frm) {

        // 1. Dashboard Indicator
        
        set_status_indicator(frm);
        // 2. Custom Button: Create Leave Request
        if (!frm.is_new()) {
            
            frm.add_custom_button('Create Leave Request', () => {
                frappe.route_options = {
                    employee: frm.doc.name
                };
                frappe.new_doc('Leave Request');
            });
        }

        // 3. Custom Button: View Skills Summary
        if (!frm.is_new()) {
            frm.add_custom_button('View Skills Summary', () => {
                show_skills_dialog(frm);
            });
        }
    },

    // ----------------------------
    // Department Change
    // ----------------------------
    department: function(frm) {

        // Clear designation when department changes
        frm.set_value('designation', null);

        // Set filter on designation
        frm.set_query('designation', function() {
            return {
                filters: {
                    department: frm.doc.department
                }
            };
        });
    },

    // ----------------------------
    // Auto Full Name
    // ----------------------------
    first_name: function(frm) {
        set_full_name(frm);
    },

    last_name: function(frm) {
        set_full_name(frm);
    }
});


// ----------------------------
// Helper: Full Name Generator
// ----------------------------
function set_full_name(frm) {
    if (frm.doc.first_name || frm.doc.last_name) {
        let full_name = `${frm.doc.first_name || ''} ${frm.doc.last_name || ''}`.trim();
        frm.set_value('full_name', full_name);
    }
}


// ----------------------------
// Helper: Dashboard Indicator
// ----------------------------
function set_status_indicator(frm) {
    if (!frm.doc.employee_status) return;

    let status = frm.doc.employee_status;
    let color = "blue";

    if (status === "Active") color = "green";
    else if (status === "On Leave") color = "orange";
    else if (status === "Terminated") color = "red";
    else if (status === "Inactive") color = "gray";

    // Clear previous indicators (important)
    frm.dashboard.clear_headline();

    frm.dashboard.set_headline(
        `<span class="indicator ${color}">${status}</span>`
    );
}


// ----------------------------
// Helper: Skills Dialog
// ----------------------------
function show_skills_dialog(frm) {

    let data = frm.doc.skills || [];

    if (!data.length) {
        frappe.msgprint('No skills found for this employee.');
        return;
    }

    let table_html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Skill</th>
                    <th>Proficiency</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td>${row.skill || ''}</td>
                        <td>${row.proficiency || ''}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    let dialog = new frappe.ui.Dialog({
        title: 'Skills Summary',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'skills_table',
                options: table_html
            }
        ],
        size: 'large'
    });

    dialog.show();
}