# Medicine Expiry Tracker — V4
### Developed by Sawan Kumar

V4 adds real-time webcam barcode scanning to the V3 healthcare inventory application.

## Main features
- Admin login
- Professional inventory dashboard
- SQLite database
- Add / update / delete medicines
- Medicine categories
- Batch and barcode records
- Search and filters
- Expiry monitoring
- Low-stock monitoring
- CSV export
- PDF report
- Database backup
- **Laptop webcam barcode scanner**
- Automatic database lookup after scanning

## Login
Username: admin
Password: admin123

## Install webcam scanner dependencies
Open VS Code Terminal inside this project folder:

```bash
pip install opencv-python pyzbar pillow reportlab
```

On Windows, `pyzbar` may require the ZBar runtime depending on the Python environment.
If the scanner reports a ZBar/DLL error, tell me the exact error and I will guide you through the Windows setup.

## Run

```bash
python app.py
```

or double-click:

`run_app.bat`

## How webcam scanning works
1. Open the application and log in.
2. Click **Scan with Webcam**.
3. Allow camera access if Windows asks.
4. Hold a barcode in the green scan area.
5. The application reads the barcode.
6. If that barcode exists in the SQLite database, its medicine record is selected automatically.
7. If it does not exist, the scanned value is placed into the Barcode field so you can add a new medicine record.

## Important
The barcode itself does not automatically contain the medicine's complete database record. The application must have a medicine record associated with that barcode, unless an external medicine database/API is integrated.

This application is for inventory and expiry tracking, not medical diagnosis or treatment recommendations.
My Medicine Tracker Application