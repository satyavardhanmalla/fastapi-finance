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
# 2. Extract Date: Improved to catch dates regardless of label formatting
    # The pattern looks for 'date', optional colon/space, then captures until end of line
    date_match = re.search(r"(?:date|dated)\s*[:\-]?\s*(.*)", text, re.IGNORECASE)
    
    formatted_date = None
    if date_match:
        try:
            # Get the raw string and strip away any potential extra characters
            raw_date = date_match.group(1).strip()
            # Remove any trailing non-date characters like punctuation if they exist
            clean_date = re.sub(r'[^\w\s\-\/\.]+', '', raw_date).strip()
            formatted_date = parser.parse(clean_date).strftime('%Y-%m-%d')
        except:
            formatted_date = None
# 3. Extract Vendor: Stop capturing if it hits "Subtotal", "Total", or "Amount"
    # The (?!...) part is a negative lookahead that stops the capture group
    vendor_match = re.search(r"(?:vendor|seller|billed\s*by)[:\s]*(.*?)(?=\s*(?:subtotal|total|amount|invoice|date|$))", text, re.IGNORECASE | re.DOTALL)
    vendor = vendor_match.group(1).strip() if vendor_match else None
# 4. Extract Amount: Look for variations of total and capture the digits
    # This pattern searches for "subtotal", "total", or "amount" and captures the following number
    amount_match = re.search(r"(?:subtotal|total|amount)[\s\w]*[:\s]*[\$Rs]*\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    
    if amount_match:
        # Remove commas and convert to float
        amount = float(amount_match.group(1).replace(',', ''))
    else:
        amount = None
# 5. Extract Tax: Look for explicit amount or calculate from percentage
    # First, look for an explicit tax amount line (e.g., GST: 500)
    tax_match = re.search(r"(?:gst|vat|tax)[\s\w]*[:\s]*[\$Rs]*\s*([\d,]+\.?\d*)", text, re.IGNORECASE)
    
    # Second, look for a percentage (e.g., GST (10%):)
    tax_percent_match = re.search(r"(?:gst|vat|tax)[\s\w]*\((\d+)%\)", text, re.IGNORECASE)
    
    tax = None
    if tax_match:
        # Extract the explicit tax value
        tax = float(tax_match.group(1).replace(',', ''))
    elif tax_percent_match and amount is not None:
        # Fallback: Calculate tax from percentage and amount
        percentage = float(tax_percent_match.group(1))
        tax = round(amount * (percentage / 100), 2)
    return {
        "invoice_no": invoice_no,
        "date": formatted_date,
        "vendor": vendor,
        "amount": amount,
        "tax": tax,
        "currency": "INR" if re.search(r"Rs|INR", text, re.IGNORECASE) else ("USD" if re.search(r"USD|\$", text, re.IGNORECASE) else None)
    }
