# ICON PUCLIC SCHOOL – School Fee & Transport Management System

Offline-first Windows desktop starter application using Python Tkinter + SQLite.

## Run on Windows
1. Install Python 3.11+ (only needed for source-code run; end users can use the EXE).
2. Extract this folder.
3. Open Command Prompt in this folder and run `python app.py`.
4. First login: **admin** / **admin123**. Change the password immediately from School Settings.

## Build Windows EXE with GitHub Actions
1. Create a GitHub repository and upload all files in this folder (including `.github`).
2. Open **Actions** → **Build Windows EXE** → **Run workflow**.
3. When complete, open the run and download artifact `ICON-PUCLIC-SCHOOL-Windows`.
4. Extract the ZIP and run `IconPublicSchoolPro.exe`.

## Data and backup
Database and generated receipt HTML files are stored under `%LOCALAPPDATA%\IconPublicSchoolPro`. Use Reports & Backup to create or restore a database backup.

## Implemented in this starter build
- Local SQLite database; Admin login with salted PBKDF2 password hashing.
- Student add/edit/search and status management.
- Fee category setup and class-wise fee rates.
- Bus records and stop-wise monthly fee setup.
- Combined payment collection with selectable fee heads, partial payments, discount, fine, payment modes and a single printable combined receipt.
- Recent transaction dashboard, CSV exports, database backup/restore, school branding settings and audit events.

## Important limitations before live school deployment
This is a functional starter build, not yet a fully audited production accounting package. The current fee due calculation is based on configured class rates and recorded payments; it does not yet create a month-by-month assessment ledger, so it cannot reliably calculate previous dues across every academic session. Student-to-bus assignment UI, cashier-user creation/permission editor, receipt cancellation workflow, PDF/Excel export, photo upload, automatic scheduled backups, and installer packaging are not included yet. Receipts open as printable HTML in the default browser; use the browser Print command and choose Save as PDF or a printer. Test with sample records and verify balances before using it for real collections.
