POS System - Spreadsheet Style
=============================

This is a simple Point of Sale (POS) system with a spreadsheet-like interface, barcode scanning support, and receipt printing for Windows.

---

**How to Run:**
1. Make sure you have Python 3.8+ installed.
2. Install dependencies:
   pip install -r requirements.txt
3. Run the application:
   python pos_system.py

---

**How to Package as Standalone .exe:**
1. Install PyInstaller:
   pip install pyinstaller
2. Build the executable:
   pyinstaller --onefile --windowed pos_system.py
3. The .exe will be in the 'dist' folder.

---

**Features:**
- Spreadsheet-style sales table
- Barcode scanning (works with most USB barcode scanners)
- Receipt printing (requires a printer and pywin32)
- Basic inventory management
- Save sales to CSV

---

**Product Database:**
- Edit the PRODUCTS dictionary in pos_system.py to add/remove products and barcodes.

---

**Note:**
- For receipt printing, you need a Windows system with a default printer set up.
- If pywin32 is not available, receipts will be saved as receipt.txt instead. 