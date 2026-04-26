"""Create sample documents for testing DocuMind AI."""

from pathlib import Path
import sys

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

def create_invoice_pdf():
    """Create a sample invoice PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        pdf_path = Path(__file__).resolve().parent / "sample_invoice.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 750, "INVOICE")
        
        # Invoice details
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Invoice #: INV-2024-001")
        c.drawString(72, 705, f"Date: March 15, 2025")
        c.drawString(72, 690, f"Due Date: April 14, 2025")
        
        # Bill To
        c.drawString(72, 650, "Bill To:")
        c.drawString(72, 635, "Acme Corporation")
        c.drawString(72, 620, "123 Business Street")
        c.drawString(72, 605, "New York, NY 10001")
        c.drawString(72, 590, "Attn: John Smith")
        c.drawString(72, 575, "Email: john.smith@acme.com")
        
        # Payment Terms
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 540, "Payment Terms: Net 30 days")
        c.setFont("Helvetica", 10)
        c.drawString(72, 525, "Payment is due within 30 days of invoice date.")
        c.drawString(72, 510, "Late fee: 1.5% per month on overdue amounts.")
        
        # Items
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 470, "Description")
        c.drawString(400, 470, "Amount")
        
        c.setFont("Helvetica", 11)
        c.drawString(72, 450, "Consulting Services - Q1 2025")
        c.drawString(400, 450, "$5,000.00")
        
        c.drawString(72, 430, "Technical Support Package")
        c.drawString(400, 430, "$1,200.00")
        
        c.drawString(72, 410, "Software License Annual")
        c.drawString(400, 410, "$800.00")
        
        # Total
        c.line(72, 390, 550, 390)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 370, "Subtotal:")
        c.drawString(400, 370, "$7,000.00")
        
        c.drawString(72, 355, "Tax (8.5%):")
        c.drawString(400, 355, "$595.00")
        
        c.drawString(72, 340, "Total Due:")
        c.drawString(400, 340, "$7,595.00")
        
        # Footer
        c.setFont("Helvetica", 9)
        c.drawString(72, 100, "Please remit payment to:")
        c.drawString(72, 85, "Tech Solutions Inc.")
        c.drawString(72, 70, "456 Tech Avenue")
        c.drawString(72, 55, "San Francisco, CA 94105")
        
        c.save()
        print(f"✓ Created invoice: {pdf_path}")
        return pdf_path
        
    except ImportError:
        # Fallback: create with PyMuPDF
        import fitz
        
        pdf_path = Path(__file__).resolve().parent / "sample_invoice.pdf"
        doc = fitz.open()
        
        page = doc.new_page(width=612, height=792)
        
        # Insert text
        page.insert_text((72, 80), "INVOICE", fontsize=18, fontname="helv-bold")
        page.insert_text((72, 100), "Invoice #: INV-2024-001", fontsize=12)
        page.insert_text((72, 120), "Date: March 15, 2025", fontsize=12)
        page.insert_text((72, 140), "Due Date: April 14, 2025", fontsize=12)
        
        page.insert_text((72, 180), "Bill To:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 200), "Acme Corporation", fontsize=11)
        page.insert_text((72, 220), "123 Business Street", fontsize=11)
        page.insert_text((72, 240), "New York, NY 10001", fontsize=11)
        page.insert_text((72, 260), "Attn: John Smith", fontsize=11)
        page.insert_text((72, 280), "Email: john.smith@acme.com", fontsize=11)
        
        page.insert_text((72, 320), "Payment Terms: Net 30 days", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 340), "Payment is due within 30 days of invoice date.", fontsize=10)
        page.insert_text((72, 360), "Late fee: 1.5% per month on overdue amounts.", fontsize=10)
        
        page.insert_text((72, 400), "Description", fontsize=12, fontname="helv-bold")
        page.insert_text((400, 400), "Amount", fontsize=12, fontname="helv-bold")
        
        page.insert_text((72, 420), "Consulting Services - Q1 2025", fontsize=11)
        page.insert_text((400, 420), "$5,000.00", fontsize=11)
        
        page.insert_text((72, 440), "Technical Support Package", fontsize=11)
        page.insert_text((400, 440), "$1,200.00", fontsize=11)
        
        page.insert_text((72, 460), "Software License Annual", fontsize=11)
        page.insert_text((400, 460), "$800.00", fontsize=11)
        
        page.insert_text((72, 500), "Total Due: $7,595.00", fontsize=12, fontname="helv-bold")
        
        page.insert_text((72, 600), "Please remit payment to:", fontsize=9)
        page.insert_text((72, 620), "Tech Solutions Inc.", fontsize=9)
        page.insert_text((72, 640), "456 Tech Avenue", fontsize=9)
        page.insert_text((72, 660), "San Francisco, CA 94105", fontsize=9)
        
        doc.save(pdf_path)
        doc.close()
        print(f"✓ Created invoice (PyMuPDF): {pdf_path}")
        return pdf_path


def create_contract_pdf():
    """Create a sample contract PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        pdf_path = Path(__file__).resolve().parent / "sample_contract.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 750, "SERVICE AGREEMENT")
        
        # Parties
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 710, "Parties:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 695, "This Agreement is entered into on March 1, 2025")
        c.drawString(72, 680, "between Tech Solutions Inc. (\"Provider\") and")
        c.drawString(72, 665, "Acme Corporation (\"Client\").")
        
        # Services
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 625, "Services:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 610, "Provider agrees to provide consulting services,")
        c.drawString(72, 595, "technical support, and software licensing as")
        c.drawString(72, 580, "detailed in Exhibit A attached hereto.")
        
        # Payment Terms
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 540, "Payment Terms:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 525, "Client shall pay Provider $7,595.00 within 30 days")
        c.drawString(72, 510, "of invoice date. Late payments subject to 1.5%")
        c.drawString(72, 495, "monthly late fee.")
        
        # Term and Termination
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 455, "Term and Termination:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 440, "This Agreement shall commence on March 1, 2025")
        c.drawString(72, 425, "and continue for a period of one (1) year.")
        c.drawString(72, 410, "Either party may terminate with 30 days written")
        c.drawString(72, 395, "notice to the other party.")
        
        # Governing Law
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 355, "Governing Law:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 340, "This Agreement shall be governed by the laws")
        c.drawString(72, 325, "of the State of Delaware without regard to")
        c.drawString(72, 310, "conflict of law principles.")
        
        # Signatures
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 250, "Signatures:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 220, "Tech Solutions Inc.")
        c.drawString(72, 205, "By: _________________________")
        c.drawString(72, 190, "Name: Sarah Johnson")
        c.drawString(72, 175, "Title: CEO")
        
        c.drawString(300, 220, "Acme Corporation")
        c.drawString(300, 205, "By: _________________________")
        c.drawString(300, 190, "Name: John Smith")
        c.drawString(300, 175, "Title: Procurement Manager")
        
        c.save()
        print(f"✓ Created contract: {pdf_path}")
        return pdf_path
        
    except ImportError:
        # Fallback: create with PyMuPDF
        import fitz
        
        pdf_path = Path(__file__).resolve().parent / "sample_contract.pdf"
        doc = fitz.open()
        
        page = doc.new_page(width=612, height=792)
        
        # Insert text
        page.insert_text((72, 80), "SERVICE AGREEMENT", fontsize=18, fontname="helv-bold")
        
        page.insert_text((72, 120), "Parties:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 140), "This Agreement is entered into on March 1, 2025", fontsize=11)
        page.insert_text((72, 160), "between Tech Solutions Inc. (\"Provider\") and", fontsize=11)
        page.insert_text((72, 180), "Acme Corporation (\"Client\").", fontsize=11)
        
        page.insert_text((72, 220), "Services:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 240), "Provider agrees to provide consulting services,", fontsize=11)
        page.insert_text((72, 260), "technical support, and software licensing as", fontsize=11)
        page.insert_text((72, 280), "detailed in Exhibit A attached hereto.", fontsize=11)
        
        page.insert_text((72, 320), "Payment Terms:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 340), "Client shall pay Provider $7,595.00 within 30 days", fontsize=11)
        page.insert_text((72, 360), "of invoice date. Late payments subject to 1.5%", fontsize=11)
        page.insert_text((72, 380), "monthly late fee.", fontsize=11)
        
        page.insert_text((72, 420), "Term and Termination:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 440), "This Agreement shall commence on March 1, 2025", fontsize=11)
        page.insert_text((72, 460), "and continue for a period of one (1) year.", fontsize=11)
        page.insert_text((72, 480), "Either party may terminate with 30 days written", fontsize=11)
        page.insert_text((72, 500), "notice to the other party.", fontsize=11)
        
        page.insert_text((72, 540), "Governing Law:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 560), "This Agreement shall be governed by the laws", fontsize=11)
        page.insert_text((72, 580), "of the State of Delaware without regard to", fontsize=11)
        page.insert_text((72, 600), "conflict of law principles.", fontsize=11)
        
        page.insert_text((72, 660), "Signatures:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 680), "Tech Solutions Inc. - Sarah Johnson, CEO", fontsize=10)
        page.insert_text((300, 680), "Acme Corporation - John Smith, Procurement Manager", fontsize=10)
        
        doc.save(pdf_path)
        doc.close()
        print(f"✓ Created contract (PyMuPDF): {pdf_path}")
        return pdf_path


def create_financial_report_pdf():
    """Create a sample financial report PDF."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        pdf_path = Path(__file__).resolve().parent / "sample_financial_report.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        
        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(72, 750, "QUARTERLY FINANCIAL REPORT")
        
        # Subtitle
        c.setFont("Helvetica", 14)
        c.drawString(72, 725, "Q1 2025 - Tech Solutions Inc.")
        c.drawString(72, 710, "Prepared: March 31, 2025")
        
        # Executive Summary
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 670, "Executive Summary:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 655, "Q1 2025 showed strong revenue growth of 15% compared to")
        c.drawString(72, 640, "Q1 2024, driven primarily by new client acquisitions")
        c.drawString(72, 625, "and expansion of existing service contracts.")
        
        # Key Metrics
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 585, "Key Financial Metrics:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 570, "Total Revenue: $2,450,000 (+15% YoY)")
        c.drawString(72, 555, "Gross Profit: $1,225,000 (50% margin)")
        c.drawString(72, 540, "Operating Expenses: $850,000")
        c.drawString(72, 525, "Net Income: $375,000 (+18% YoY)")
        c.drawString(72, 510, "Earnings per Share: $0.75")
        
        # Revenue Breakdown
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 470, "Revenue Breakdown:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 455, "Consulting Services: $1,200,000 (49%)")
        c.drawString(72, 440, "Technical Support: $650,000 (27%)")
        c.drawString(72, 425, "Software Licensing: $450,000 (18%)")
        c.drawString(72, 410, "Training Services: $150,000 (6%)")
        
        # Outlook
        c.setFont("Helvetica-Bold", 12)
        c.drawString(72, 370, "Q2 2025 Outlook:")
        c.setFont("Helvetica", 11)
        c.drawString(72, 355, "We expect continued growth with projected revenue")
        c.drawString(72, 340, "of $2.6M, representing 6% sequential growth.")
        c.drawString(72, 325, "Key initiatives include enterprise software")
        c.drawString(72, 310, "launch and international market expansion.")
        
        # Contact
        c.setFont("Helvetica", 10)
        c.drawString(72, 100, "Questions: finance@techsolutions.com | IR Contact: (555) 123-4567")
        
        c.save()
        print(f"✓ Created financial report: {pdf_path}")
        return pdf_path
        
    except ImportError:
        # Fallback: create with PyMuPDF
        import fitz
        
        pdf_path = Path(__file__).resolve().parent / "sample_financial_report.pdf"
        doc = fitz.open()
        
        page = doc.new_page(width=612, height=792)
        
        # Insert text
        page.insert_text((72, 80), "QUARTERLY FINANCIAL REPORT", fontsize=18, fontname="helv-bold")
        page.insert_text((72, 105), "Q1 2025 - Tech Solutions Inc.", fontsize=14)
        page.insert_text((72, 125), "Prepared: March 31, 2025", fontsize=14)
        
        page.insert_text((72, 165), "Executive Summary:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 185), "Q1 2025 showed strong revenue growth of 15% compared to", fontsize=11)
        page.insert_text((72, 205), "Q1 2024, driven primarily by new client acquisitions", fontsize=11)
        page.insert_text((72, 225), "and expansion of existing service contracts.", fontsize=11)
        
        page.insert_text((72, 265), "Key Financial Metrics:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 285), "Total Revenue: $2,450,000 (+15% YoY)", fontsize=11)
        page.insert_text((72, 305), "Gross Profit: $1,225,000 (50% margin)", fontsize=11)
        page.insert_text((72, 325), "Operating Expenses: $850,000", fontsize=11)
        page.insert_text((72, 345), "Net Income: $375,000 (+18% YoY)", fontsize=11)
        page.insert_text((72, 365), "Earnings per Share: $0.75", fontsize=11)
        
        page.insert_text((72, 405), "Revenue Breakdown:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 425), "Consulting Services: $1,200,000 (49%)", fontsize=11)
        page.insert_text((72, 445), "Technical Support: $650,000 (27%)", fontsize=11)
        page.insert_text((72, 465), "Software Licensing: $450,000 (18%)", fontsize=11)
        page.insert_text((72, 485), "Training Services: $150,000 (6%)", fontsize=11)
        
        page.insert_text((72, 525), "Q2 2025 Outlook:", fontsize=12, fontname="helv-bold")
        page.insert_text((72, 545), "We expect continued growth with projected revenue", fontsize=11)
        page.insert_text((72, 565), "of $2.6M, representing 6% sequential growth.", fontsize=11)
        page.insert_text((72, 585), "Key initiatives include enterprise software", fontsize=11)
        page.insert_text((72, 605), "launch and international market expansion.", fontsize=11)
        
        page.insert_text((72, 680), "Questions: finance@techsolutions.com", fontsize=10)
        page.insert_text((72, 700), "IR Contact: (555) 123-4567", fontsize=10)
        
        doc.save(pdf_path)
        doc.close()
        print(f"✓ Created financial report (PyMuPDF): {pdf_path}")
        return pdf_path


def main():
    """Create all sample documents."""
    print("Creating sample documents for DocuMind AI...")
    print("=" * 50)
    
    docs = []
    docs.append(create_invoice_pdf())
    docs.append(create_contract_pdf())
    docs.append(create_financial_report_pdf())
    
    print("\n" + "=" * 50)
    print("✓ All sample documents created successfully!")
    print("\nYou can now upload these documents to test DocuMind AI:")
    for doc in docs:
        print(f"  - {doc.name}")
    print("\nTest queries you can try:")
    print('  - "What are the payment terms?"')
    print('  - "How much is the total invoice amount?"')
    print('  - "When can either party terminate the contract?"')
    print('  - "What was the revenue growth in Q1 2025?"')
    print('  - "What is the breakdown of revenue by service type?"')
    
    return docs


if __name__ == "__main__":
    main()
