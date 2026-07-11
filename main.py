import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil import parser

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceInput(BaseModel):
    invoice_text: str

@app.post("/extract")
async def extract_invoice(data: InvoiceInput):
    text = data.invoice_text

    # Search for keywords and capture everything that follows as a value
    # This logic ignores what's before the keyword and looks for the nearest value
    
    # 1. Invoice Number: Look for keyword then alphanumeric code
    inv_match = re.search(r"(?:invoice|#)\s*(?:no|num|number|#)?[:#]?\s*([a-z0-9-]+)", text, re.IGNORECASE)
    invoice_no = inv_match.group(1).strip() if inv_match else None

    # 2. Date: Look for date keyword then capture the rest of the line
    date_match = re.search(r"(?:date|dated)[:\s]*([a-z0-9,\s]+)", text, re.IGNORECASE)
    formatted_date = None
    if date_match:
        try:
            formatted_date = parser.parse(date_match.group(1).strip()).strftime('%Y-%m-%d')
        except:
            formatted_date = None

    # 3. Vendor: Look for keyword then the name
    vendor_match = re.search(r"(?:vendor|seller|billed\s*by)[:\s]*([a-z\s]+)", text, re.IGNORECASE)
    vendor = vendor_match.group(1).strip() if vendor_match else None

    # 4. Amount & 5. Tax: Look for keyword, then ignore potential currency labels, capture the number
    # This pattern works by finding the keyword and taking the next numerical value it finds
    amount_match = re.search(r"(?:subtotal|total|amount)[\s\w]*[:\s]*[\$Rs]*\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

    tax_match = re.search(r"(?:gst|vat|tax)[\s\w]*[\(\d%\)]*[:\s]*[\$Rs]*\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    tax = float(tax_match.group(1).replace(',', '')) if tax_match else 0.0

    return {
        "invoice_no": invoice_no,
        "date": formatted_date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": "INR" if re.search(r"Rs|INR", text, re.IGNORECASE) else ("USD" if re.search(r"USD|\$", text, re.IGNORECASE) else None)
    }
