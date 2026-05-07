import os
from app import app, db, Department, KPIDefinition

def seed_data():
    with app.app_context():
        # Create Departments
        depts_data = [
            "Sales Team", "Clearance Team", "After-Use Team", 
            "Customer Issue Management", "Call Confirmation", 
            "Order Invoice Creation Team", "Warehouse & Fulfillment", 
            "Delivery Team", "Operation Manager"
        ]
        
        dept_map = {}
        for name in depts_data:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name)
                db.session.add(dept)
                db.session.commit()
            dept_map[name] = dept.id

        # KPI Data
        kpis = [
            # Sales Team
            ("Sales Team", "Response Professionalism", "percentage", 100, "Review chat history for tone and accuracy."),
            ("Sales Team", "Message Success Rate", "percentage", 100, "Weekly count of correct replies. Target: 0% error."),
            ("Sales Team", "Follow-up Conversion", "percentage", 25, "Target: 20%-30% conversion of pending customers."),
            ("Sales Team", "Cross-sell Ratio", "percentage", 20, "At least 15-20% orders should have related products added."),
            ("Sales Team", "Data Error Rate", "percentage", 0, "Parcels returned due to data entry errors."),
            ("Sales Team", "Note Compliance", "percentage", 100, "Percentage of orders with text notes (Address + List)."),
            ("Sales Team", "Stock-out Confirmation", "percentage", 0, "Orders confirmed for out-of-stock items."),
            ("Sales Team", "Daily Reporting", "percentage", 100, "On-time and accurate EOD report submission."),

            # Clearance Team
            ("Clearance Team", "Message Clearance Speed", "number", 75, "Target: 60-90 messages per hour."),
            ("Clearance Team", "Priority Handling", "percentage", 100, "Handling labels like 'Ordered Customer' first."),
            ("Clearance Team", "Information Accuracy", "percentage", 100, "Zero pricing or info errors from Doc."),
            ("Clearance Team", "Push/Motivation Rate", "percentage", 50, "Percentage of price queries pushed towards sales."),
            ("Clearance Team", "Meta Response Rate", "percentage", 90, "Overall meta response rate target."),

            # After-Use Team
            ("After-Use Team", "First Response Time", "number", 5, "Target: Within 5 minutes (max 10)."),
            ("After-Use Team", "Daily Case Volume", "number", 35, "Target: 25-40+ cases handled per day."),
            ("After-Use Team", "Documentation Rate", "percentage", 100, "Notes for Problem + Solution + Follow-up."),
            ("After-Use Team", "Reopen Case Rate", "percentage", 15, "Target: Below 15% (same issue returning)."),
            ("After-Use Team", "Sensitive Follow-up", "percentage", 100, "100% sensitive cases followed up within 1 week."),

            # Issue Management
            ("Customer Issue Management", "Resolution Time", "number", 24, "Target: 100% issues updated/resolved within 24h."),
            ("Customer Issue Management", "Exchange Processing", "number", 0, "Delay in notifying delivery team for exchange."),
            ("Customer Issue Management", "Comment Response Rate", "percentage", 100, "100% coverage of group/page comments."),
            ("Customer Issue Management", "Backlog Prevention", "percentage", 100, "Zero pending receipts/invoices at end of day."),

            # Call Confirmation
            ("Call Confirmation", "SOP Compliance", "percentage", 100, "Script, behavior, and verification accuracy."),
            ("Call Confirmation", "Data Accuracy", "percentage", 100, "Zero errors in product, size, or price during call."),
            ("Call Confirmation", "Advance Compliance", "percentage", 100, "Collecting advance for 10k+ or high-risk orders."),
            ("Call Confirmation", "Tagging Accuracy", "percentage", 100, "Correct usage of Confirmed, Mirpur, Hold, etc."),

            # Invoice Team
            ("Order Invoice Creation Team", "Profile Accuracy", "percentage", 100, "Zero duplicate profiles or data entry errors."),
            ("Order Invoice Creation Team", "Stock Alert Speed", "number", 0, "Immediate reporting of stock-outs to sales."),
            ("Order Invoice Creation Team", "Daily Receipt Count", "number", 150, "Minimum 150 receipts cut per day."),
            ("Order Invoice Creation Team", "Advance Policy Adherence", "percentage", 100, "Ensuring advance for return-history orders."),

            # Warehouse
            ("Warehouse & Fulfillment", "Picking Accuracy", "percentage", 100, "Zero errors in product, shade, or quantity."),
            ("Warehouse & Fulfillment", "Packaging Safety", "percentage", 100, "100% bubble wrap and secure sealing."),
            ("Warehouse & Fulfillment", "Dispatch Safety", "percentage", 100, "Zero 'Hold' or 'Cancel' parcels shipped."),
            ("Warehouse & Fulfillment", "Fulfillment Volume", "number", 1000, "Target: 1000 parcels per day."),
            ("Warehouse & Fulfillment", "Resolution TAT", "number", 48, "Average 24-48h to resolve stock/hold issues."),

            # Delivery Team
            ("Delivery Team", "Delivery Success Rate", "percentage", 95, "Target 95%-100% successful delivery."),
            ("Delivery Team", "Pickup Accuracy", "percentage", 100, "Zero errors or damage during supplier pickup."),
            ("Delivery Team", "Cash Handling", "percentage", 100, "Zero mismatch in cash collection reports."),

            # Operations
            ("Operation Manager", "SOP Compliance Audit", "percentage", 98, "Random audit scores across all teams."),
            ("Operation Manager", "Response Time Improvement", "percentage", 10, "MoM improvement in response times."),
            ("Operation Manager", "Reporting Timeliness", "percentage", 100, "On-time submission of daily/weekly reports.")
        ]
        
        for dept_name, metric, mtype, target, desc in kpis:
            dept_id = dept_map[dept_name]
            existing = KPIDefinition.query.filter_by(department_id=dept_id, metric_name=metric).first()
            if not existing:
                kpi = KPIDefinition(
                    department_id=dept_id,
                    metric_name=metric,
                    metric_type=mtype,
                    target_value=target,
                    description=desc
                )
                db.session.add(kpi)
        
        db.session.commit()
        print("Database seeded successfully with Choice Legacy KPIs!")

if __name__ == "__main__":
    seed_data()
