#!/usr/bin/env python3
"""Generate 25 diverse test PDFs for DocuMind AI evaluation."""

import sys
from pathlib import Path
import random
from datetime import datetime, timedelta

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("ReportLab not available, using PyMuPDF fallback")

OUTPUT_DIR = Path(__file__).resolve().parent / "pdfs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Document templates with varying complexity
def create_invoice_pdf(filename, invoice_num, amount, company, date):
    """Create an invoice PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 750, "INVOICE")
        
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Invoice #: {invoice_num}")
        c.drawString(72, 705, f"Date: {date}")
        c.drawString(72, 690, f"Due Date: {(datetime.strptime(date, '%B %d, %Y') + timedelta(days=30)).strftime('%B %d, %Y')}")
        
        c.drawString(72, 650, "Bill To:")
        c.drawString(72, 635, company)
        c.drawString(72, 620, f"{random.randint(100, 999)} Business Street")
        c.drawString(72, 605, f"{random.choice(['New York', 'San Francisco', 'Chicago', 'Austin'])}, {random.choice(['NY', 'CA', 'IL', 'TX'])} {random.randint(10000, 99999)}")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 560, f"Payment Terms: Net {random.choice([15, 30, 45, 60])} days")
        c.setFont("Helvetica", 10)
        c.drawString(72, 545, f"Payment is due within the specified terms.")
        c.drawString(72, 530, f"Late fee: {random.choice([1.0, 1.5, 2.0, 2.5])}% per month on overdue amounts.")
        
        # Items
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 490, "Description")
        c.drawString(400, 490, "Amount")
        
        c.setFont("Helvetica", 11)
        services = [
            ("Consulting Services", amount * 0.6),
            ("Technical Support", amount * 0.25),
            ("Software License", amount * 0.15),
        ]
        y = 470
        for service, amt in services:
            c.drawString(72, y, service)
            c.drawString(400, y, f"${amt:,.2f}")
            y -= 20
        
        c.line(72, y-5, 550, y-5)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, y-25, "Total Due:")
        c.drawString(400, y-25, f"${amount:,.2f}")
        
        c.save()
    else:
        # PyMuPDF fallback
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        
        page.insert_text((72, 80), "INVOICE", fontsize=18)
        page.insert_text((72, 100), f"Invoice #: {invoice_num}", fontsize=12)
        page.insert_text((72, 120), f"Date: {date}", fontsize=12)
        page.insert_text((72, 140), f"Total: ${amount:,.2f}", fontsize=12)
        page.insert_text((72, 180), f"Bill To: {company}", fontsize=11)
        
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def create_contract_pdf(filename, parties, start_date, duration_months, governing_law):
    """Create a service contract PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, "SERVICE AGREEMENT")
        
        c.setFont("Helvetica", 11)
        c.drawString(72, 710, f"This Agreement is entered into on {start_date}")
        c.drawString(72, 695, f"between {parties[0]} (\"Provider\") and")
        c.drawString(72, 680, f"{parties[1]} (\"Client\").")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 640, "Services:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 625, "Provider agrees to provide consulting and technical support")
        c.drawString(72, 610, "services as detailed in the statement of work.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 580, "Term:")
        c.setFont("Helvetica", 10)
        end_date = (datetime.strptime(start_date, "%B %d, %Y") + timedelta(days=30*duration_months)).strftime("%B %d, %Y")
        c.drawString(72, 565, f"This Agreement shall commence on {start_date}")
        c.drawString(72, 550, f"and continue until {end_date}.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 520, "Payment Terms:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 505, f"Payment due within {random.choice([15, 30, 45])} days of invoice.")
        c.drawString(72, 490, f"Late fee: {random.choice([1.5, 2.0, 2.5])}% per month.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 460, "Termination:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 445, f"Either party may terminate with {random.choice([30, 60, 90])} days written notice.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 415, f"Governing Law:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 400, f"This Agreement shall be governed by the laws of {governing_law}.")
        
        c.save()
    else:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        
        page.insert_text((72, 80), "SERVICE AGREEMENT", fontsize=16)
        page.insert_text((72, 110), f"Parties: {parties[0]} and {parties[1]}", fontsize=11)
        page.insert_text((72, 130), f"Start Date: {start_date}", fontsize=11)
        page.insert_text((72, 150), f"Duration: {duration_months} months", fontsize=11)
        page.insert_text((72, 170), f"Governing Law: {governing_law}", fontsize=11)
        
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def create_financial_report_pdf(filename, quarter, year, revenue, growth):
    """Create a quarterly financial report PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 750, f"QUARTERLY FINANCIAL REPORT")
        
        c.setFont("Helvetica", 14)
        c.drawString(72, 720, f"{quarter} {year}")
        c.drawString(72, 700, f"Prepared: {datetime.now().strftime('%B %d, %Y')}")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 660, "Executive Summary:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 645, f"{quarter} {year} showed {'strong' if growth > 10 else 'moderate' if growth > 0 else 'declining'} revenue growth")
        c.drawString(72, 630, f"of {growth}% compared to the previous year.")
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 590, "Key Financial Metrics:")
        c.setFont("Helvetica", 11)
        
        metrics = [
            ("Total Revenue", f"${revenue:,.0f}", growth),
            ("Gross Profit", f"${revenue * 0.5:,.0f}", "50% margin"),
            ("Operating Expenses", f"${revenue * 0.35:,.0f}", ""),
            ("Net Income", f"${revenue * 0.15:,.0f}", f"{growth * 0.8:.1f}% margin"),
        ]
        
        y = 570
        for metric, value, note in metrics:
            c.drawString(72, y, f"{metric}: {value}")
            if note:
                c.drawString(300, y, f"({note})")
            y -= 15
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, y-20, "Revenue Breakdown:")
        c.setFont("Helvetica", 11)
        
        breakdowns = [
            ("Product Sales", revenue * 0.45),
            ("Services", revenue * 0.30),
            ("Subscriptions", revenue * 0.20),
            ("Other", revenue * 0.05),
        ]
        
        y -= 40
        for category, amount in breakdowns:
            pct = (amount / revenue) * 100
            c.drawString(72, y, f"{category}: ${amount:,.0f} ({pct:.0f}%)")
            y -= 15
        
        c.save()
    else:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        
        page.insert_text((72, 80), f"{quarter} {year} Financial Report", fontsize=18)
        page.insert_text((72, 110), f"Revenue: ${revenue:,.0f}", fontsize=14)
        page.insert_text((72, 140), f"Growth: {growth}%", fontsize=14)
        
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def create_nda_pdf(filename, parties, effective_date):
    """Create a Non-Disclosure Agreement PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, "NON-DISCLOSURE AGREEMENT")
        
        c.setFont("Helvetica", 11)
        c.drawString(72, 710, f"This NDA is entered into on {effective_date}")
        c.drawString(72, 695, f"between {parties[0]} and {parties[1]}.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 655, "Definition of Confidential Information:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 640, "Confidential Information means any and all non-public, proprietary,")
        c.drawString(72, 625, "or confidential information disclosed by either party.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 595, "Obligations of Receiving Party:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 580, "The Receiving Party agrees to hold all Confidential Information in")
        c.drawString(72, 565, "strict confidence and not disclose to any third parties.")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 535, "Term:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 520, f"This Agreement shall remain in effect for {random.choice([2, 3, 5])} years")
        c.drawString(72, 505, f"from the Effective Date.")
        
        c.save()
    else:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 80), "NON-DISCLOSURE AGREEMENT", fontsize=16)
        page.insert_text((72, 110), f"Parties: {parties[0]} and {parties[1]}", fontsize=11)
        page.insert_text((72, 130), f"Date: {effective_date}", fontsize=11)
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def create_employment_contract_pdf(filename, employee, position, salary, start_date):
    """Create an employment contract PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, "EMPLOYMENT AGREEMENT")
        
        c.setFont("Helvetica", 11)
        c.drawString(72, 710, f"This Employment Agreement is between:")
        c.drawString(72, 695, f"Employer: TechCorp Inc.")
        c.drawString(72, 680, f"Employee: {employee}")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 640, "Position and Duties:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 625, f"Employee is hired as {position}.")
        c.drawString(72, 610, f"Start Date: {start_date}")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 580, "Compensation:")
        c.setFont("Helvetica", 10)
        c.drawString(72, 565, f"Annual Salary: ${salary:,.0f}")
        c.drawString(72, 550, f"Pay Frequency: {'Bi-weekly' if random.choice([True, False]) else 'Monthly'}")
        
        benefits = random.choice([
            ["Health Insurance", "401(k) Match", "PTO: 20 days"],
            ["Health & Dental", "Stock Options", "PTO: 15 days"],
            ["Full Benefits", "Bonus Eligible", "PTO: Unlimited"],
        ])
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 520, "Benefits:")
        c.setFont("Helvetica", 10)
        y = 505
        for benefit in benefits:
            c.drawString(72, y, f"- {benefit}")
            y -= 15
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y-10, "Termination:")
        c.setFont("Helvetica", 10)
        c.drawString(72, y-25, f"Either party may terminate with {random.choice([2, 4])} weeks notice.")
        
        c.save()
    else:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 80), "EMPLOYMENT AGREEMENT", fontsize=16)
        page.insert_text((72, 110), f"Employee: {employee}", fontsize=11)
        page.insert_text((72, 130), f"Position: {position}", fontsize=11)
        page.insert_text((72, 150), f"Salary: ${salary:,.0f}", fontsize=11)
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def create_meeting_minutes_pdf(filename, meeting_date, attendees, topics):
    """Create meeting minutes PDF."""
    pdf_path = OUTPUT_DIR / filename
    
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 750, "MEETING MINUTES")
        
        c.setFont("Helvetica", 11)
        c.drawString(72, 720, f"Date: {meeting_date}")
        c.drawString(72, 705, f"Time: {random.choice(['9:00 AM', '2:00 PM', '10:30 AM'])} - {random.choice(['10:30 AM', '3:30 PM', '12:00 PM'])}")
        c.drawString(72, 690, f"Location: {random.choice(['Conference Room A', 'Zoom', 'Board Room'])}")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 660, "Attendees:")
        c.setFont("Helvetica", 10)
        y = 645
        for attendee in attendees:
            c.drawString(72, y, f"- {attendee}")
            y -= 12
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, y-15, "Agenda Items:")
        c.setFont("Helvetica", 10)
        y -= 30
        
        for i, topic in enumerate(topics, 1):
            c.drawString(72, y, f"{i}. {topic}")
            c.drawString(90, y-15, f"   Discussion: {random.choice(['Reviewed current status', 'Approved proposal', 'Deferred decision'])}")
            c.drawString(90, y-30, f"   Action: {random.choice(['Follow-up next week', 'Assign to team', 'Schedule review'])}")
            y -= 50
        
        c.save()
    else:
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 80), "MEETING MINUTES", fontsize=16)
        page.insert_text((72, 110), f"Date: {meeting_date}", fontsize=11)
        for i, attendee in enumerate(attendees):
            page.insert_text((72, 140 + i*20), f"Attendee: {attendee}", fontsize=10)
        doc.save(pdf_path)
        doc.close()
    
    return pdf_path


def main():
    """Generate 25 test PDFs with varying content."""
    print("Generating 25 test PDFs...")
    
    companies = [
        ("Acme Corporation", "Tech Solutions Inc."),
        ("Global Dynamics", "Innovation Labs LLC"),
        ("Strategic Partners", "DataFlow Systems"),
        ("Enterprise Co", "CloudFirst Technologies"),
        ("Metro Industries", "Smart Analytics Corp"),
    ]
    
    states = ["Delaware", "California", "New York", "Texas", "Illinois"]
    employees = ["John Smith", "Sarah Johnson", "Michael Chen", "Emily Davis", "Robert Wilson"]
    positions = ["Software Engineer", "Product Manager", "Data Scientist", "Sales Director", "UX Designer"]
    
    generated = []
    
    # Generate 8 invoices
    for i in range(8):
        inv_num = f"INV-2024-{100 + i:03d}"
        amount = random.choice([5000, 7500, 10000, 15000, 25000, 35000, 50000, 75000])
        company = random.choice([c[0] for c in companies])
        date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%B %d, %Y")
        
        pdf = create_invoice_pdf(f"test_invoice_{i+1:02d}.pdf", inv_num, amount, company, date)
        generated.append({
            "filename": pdf.name,
            "type": "invoice",
            "amount": amount,
            "company": company,
            "date": date,
        })
        print(f"  ✓ {pdf.name}")
    
    # Generate 6 contracts
    for i in range(6):
        parties = random.choice(companies)
        start_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300))).strftime("%B %d, %Y")
        duration = random.choice([6, 12, 24, 36])
        governing = random.choice(states)
        
        pdf = create_contract_pdf(f"test_contract_{i+1:02d}.pdf", parties, start_date, duration, governing)
        generated.append({
            "filename": pdf.name,
            "type": "contract",
            "parties": parties,
            "start_date": start_date,
            "duration_months": duration,
            "governing_law": governing,
        })
        print(f"  ✓ {pdf.name}")
    
    # Generate 5 financial reports
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    for i in range(5):
        quarter = random.choice(quarters)
        year = random.choice([2023, 2024])
        revenue = random.choice([500000, 1000000, 2000000, 5000000, 10000000])
        growth = random.choice([-5, 5, 10, 15, 25, 35])
        
        pdf = create_financial_report_pdf(f"test_financial_{i+1:02d}.pdf", quarter, year, revenue, growth)
        generated.append({
            "filename": pdf.name,
            "type": "financial_report",
            "quarter": quarter,
            "year": year,
            "revenue": revenue,
            "growth_pct": growth,
        })
        print(f"  ✓ {pdf.name}")
    
    # Generate 3 NDAs
    for i in range(3):
        parties = random.choice(companies)
        date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%B %d, %Y")
        
        pdf = create_nda_pdf(f"test_nda_{i+1:02d}.pdf", parties, date)
        generated.append({
            "filename": pdf.name,
            "type": "nda",
            "parties": parties,
            "effective_date": date,
        })
        print(f"  ✓ {pdf.name}")
    
    # Generate 3 employment contracts
    for i in range(3):
        employee = random.choice(employees)
        position = random.choice(positions)
        salary = random.choice([60000, 80000, 100000, 120000, 150000])
        start_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 180))).strftime("%B %d, %Y")
        
        pdf = create_employment_contract_pdf(f"test_employment_{i+1:02d}.pdf", employee, position, salary, start_date)
        generated.append({
            "filename": pdf.name,
            "type": "employment_contract",
            "employee": employee,
            "position": position,
            "salary": salary,
            "start_date": start_date,
        })
        print(f"  ✓ {pdf.name}")
    
    print(f"\n✓ Generated {len(generated)} PDFs in {OUTPUT_DIR}")
    
    # Save manifest
    import json
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(generated, f, indent=2)
    print(f"✓ Saved manifest to {manifest_path}")
    
    return generated


if __name__ == "__main__":
    main()
