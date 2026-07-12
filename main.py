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

    # Use this pattern: Look specifically for the label, then capture the alphanumeric code
    # This ignores the word "Invoice" if it is at the start of a line and not followed by a label
    inv_match = re.search(r"(?:Invoice\s*(?:No|#)|#)\s*:?\s*([a-z0-9-]+)", text, re.IGNORECASE)
    invoice_no = inv_match.group(1).strip() if inv_match else None
# 2. Extract Date: Updated to include hyphens, slashes, and dots
    date_match = re.search(r"(?:date|dated)[:\s]*([a-zA-Z0-9,\s\-\/\.]+)", text, re.IGNORECASE)
    formatted_date = None
    if date_match:
        try:
            # Strip trailing characters that might have been accidentally captured
            date_str = date_match.group(1).strip()
            formatted_date = parser.parse(date_str).strftime('%Y-%m-%d')
        except:
            formatted_date = None
    # 3. Vendor
    vendor_match = re.search(r"(?:vendor|seller|billed\s*by)[:\s]*([a-z\s]+)", text, re.IGNORECASE)
    vendor = vendor_match.group(1).strip() if vendor_match else None

    # 4. Amount
    amount_match = re.search(r"(?:subtotal|total|amount)[\s\w]*[:\s]*[\$Rs]*\s*([\d,]+\.\d+)", text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0

    # 5. Tax Calculation Logic: 
    # Capture percentage from (XX%) and calculate from amount
    tax_percent_match = re.search(r"(?:gst|vat|tax)[\s\w]*\((\d+)%\)", text, re.IGNORECASE)
    
    if tax_percent_match:
        percentage = float(tax_percent_match.group(1))
        tax = round(amount * (percentage / 100), 2)
    else:
        # Fallback to direct extraction if no percentage is found
        tax_match = re.search(r"(?:gst|vat|tax)[\s\w]*[:\s]*[\$Rs]*\s*([\d,]+\.\d+)", text, re.IGNORECASE)
        tax = float(tax_match.group(1).replace(',', '')) if tax_match else None

    return {
        "invoice_no": invoice_no,
        "date": formatted_date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": "INR" if re.search(r"Rs|INR", text, re.IGNORECASE) else ("USD" if re.search(r"USD|\$", text, re.IGNORECASE) else None)
    }
