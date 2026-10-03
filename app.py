import csv
import os
import shutil
import sqlite3
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Optional webcam barcode scanning dependencies.
# Install with: pip install opencv-python pyzbar
try:
    import cv2
except ImportError:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as decode_barcodes
except ImportError:
    decode_barcodes = None


DB_NAME = "medicines.db"
NEAR_EXPIRY_DAYS = 30


class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("Medicine Expiry Tracker | Login")
        self.root.geometry("430x330")
        self.root.resizable(False, False)

        box = ttk.Frame(root, padding=28)
        box.pack(fill="both", expand=True)

        ttk.Label(
            box, text="💊 Medicine Expiry Tracker",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(12, 3))

        ttk.Label(
            box, text="Secure Inventory Login",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 22))

        ttk.Label(box, text="Username").pack(anchor="w")
        self.user = ttk.Entry(box)
        self.user.pack(fill="x", pady=(4, 12))
        self.user.insert(0, "admin")

        ttk.Label(box, text="Password").pack(anchor="w")
        self.password = ttk.Entry(box, show="•")
        self.password.pack(fill="x", pady=(4, 15))
        self.password.insert(0, "admin123")

        ttk.Button(
            box, text="LOGIN", command=self.login
        ).pack(fill="x", ipady=5)

        ttk.Label(
            box, text="Demo credentials: admin / admin123",
            font=("Segoe UI", 8)
        ).pack(pady=12)

        self.root.bind("<Return>", lambda e: self.login())

    def login(self):
        if self.user.get().strip() == "admin" and self.password.get() == "admin123":
            self.root.unbind("<Return>")
            self.root.destroy()
            self.on_success()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


class MedicineExpiryTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("Medicine Expiry Tracker | By Sawan Kumar")
        self.root.geometry("1280x800")
        self.root.minsize(1080, 700)

        self.conn = sqlite3.connect(DB_NAME)
        self.create_table()

        self.setup_style()
        self.build_ui()
        self.refresh()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    # ---------- DATABASE ----------

    def create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                batch TEXT,
                barcode TEXT,
                quantity INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 10,
                price REAL NOT NULL DEFAULT 0,
                expiry_date TEXT NOT NULL,
                manufacturer TEXT
            )
        """)
        self.conn.commit()

        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(medicines)")
        }

        upgrades = {
            "category": "TEXT NOT NULL DEFAULT 'Other'",
            "barcode": "TEXT DEFAULT ''",
            "min_stock": "INTEGER NOT NULL DEFAULT 10",
            "price": "REAL NOT NULL DEFAULT 0",
        }

        for column, definition in upgrades.items():
            if column not in columns:
                self.conn.execute(
                    f"ALTER TABLE medicines ADD COLUMN {column} {definition}"
                )

        self.conn.commit()

    # ---------- STYLE ----------

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("Segoe UI", 23, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("CardValue.TLabel", font=("Segoe UI", 19, "bold"))
        style.configure("Treeview", rowheight=31, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))

    # ---------- UI ----------

    def build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        row = ttk.Frame(header)
        row.pack(fill="x")

        ttk.Label(
            row, text="💊 Medicine Expiry Tracker",
            style="Title.TLabel"
        ).pack(side="left")

        ttk.Label(
            row, text="  |  By Sawan Kumar",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", pady=(8, 0))

        ttk.Label(
            header,
            text="Healthcare inventory management • expiry • stock • reports",
            style="Subtitle.TLabel"
        ).pack(anchor="w", pady=(2, 0))

        # Dashboard
        cards = ttk.Frame(main)
        cards.pack(fill="x", pady=(0, 10))

        self.total_var = tk.StringVar(value="0")
        self.safe_var = tk.StringVar(value="0")
        self.soon_var = tk.StringVar(value="0")
        self.expired_var = tk.StringVar(value="0")
        self.low_var = tk.StringVar(value="0")
        self.value_var = tk.StringVar(value="₹0")

        data = [
            ("TOTAL", self.total_var),
            ("SAFE", self.safe_var),
            ("EXPIRING ≤ 30 DAYS", self.soon_var),
            ("EXPIRED", self.expired_var),
            ("LOW STOCK", self.low_var),
            ("STOCK VALUE", self.value_var),
        ]

        for i, (title, variable) in enumerate(data):
            self.make_card(cards, title, variable, i)

        # Form
        form = ttk.LabelFrame(main, text="Medicine Details", padding=10)
        form.pack(fill="x", pady=(0, 10))

        self.name_var = tk.StringVar()
        self.category_var = tk.StringVar(value="Tablet")
        self.batch_var = tk.StringVar()
        self.barcode_var = tk.StringVar()
        self.qty_var = tk.StringVar()
        self.min_stock_var = tk.StringVar(value="10")
        self.price_var = tk.StringVar()
        self.expiry_var = tk.StringVar()
        self.manufacturer_var = tk.StringVar()

        fields = [
            ("Medicine Name", self.name_var, "entry"),
            ("Category", self.category_var, "combo"),
            ("Batch Number", self.batch_var, "entry"),
            ("Barcode", self.barcode_var, "entry"),
            ("Quantity", self.qty_var, "entry"),
            ("Min. Stock", self.min_stock_var, "entry"),
            ("Price / Unit (₹)", self.price_var, "entry"),
            ("Expiry (DD-MM-YYYY)", self.expiry_var, "entry"),
            ("Manufacturer", self.manufacturer_var, "entry"),
        ]

        for i, (label, variable, kind) in enumerate(fields):
            row, col = divmod(i, 5)
            ttk.Label(form, text=label).grid(
                row=row * 2, column=col, sticky="w", padx=5
            )

            if kind == "combo":
                widget = ttk.Combobox(
                    form, textvariable=variable,
                    values=[
                        "Tablet", "Capsule", "Syrup", "Injection",
                        "Cream", "Drops", "Inhaler", "Vitamin", "Other"
                    ],
                    state="readonly", width=19
                )
            else:
                widget = ttk.Entry(form, textvariable=variable, width=20)

            widget.grid(
                row=row * 2 + 1, column=col,
                sticky="ew", padx=5, pady=(3, 7)
            )
            form.columnconfigure(col, weight=1)

        actions = ttk.Frame(form)
        actions.grid(row=4, column=0, columnspan=5, sticky="w", padx=5)

        ttk.Button(
            actions, text="＋ Add Medicine",
            style="Accent.TButton", command=self.add_medicine
        ).pack(side="left", padx=(0, 7))

        ttk.Button(
            actions, text="✎ Update",
            command=self.update_selected
        ).pack(side="left", padx=7)

        ttk.Button(
            actions, text="Clear",
            command=self.clear_form
        ).pack(side="left", padx=7)

        ttk.Button(
            actions, text="🔎 Find Barcode",
            command=self.find_barcode
        ).pack(side="left", padx=7)

        ttk.Button(
            actions, text="📷 Scan with Webcam",
            command=self.scan_barcode_webcam
        ).pack(side="left", padx=7)

        # Toolbar
        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Label(toolbar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=27)
        search.pack(side="left", padx=(6, 10))
        self.search_var.trace_add("write", lambda *_: self.refresh())

        ttk.Label(toolbar, text="Status:").pack(side="left")
        self.status_var = tk.StringVar(value="All")
        status = ttk.Combobox(
            toolbar, textvariable=self.status_var,
            values=["All", "Safe", "Expiring Soon", "Expired", "Low Stock"],
            state="readonly", width=15
        )
        status.pack(side="left", padx=5)
        status.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(toolbar, text="Category:").pack(side="left", padx=(8, 0))
        self.category_filter_var = tk.StringVar(value="All")
        category = ttk.Combobox(
            toolbar, textvariable=self.category_filter_var,
            values=[
                "All", "Tablet", "Capsule", "Syrup", "Injection",
                "Cream", "Drops", "Inhaler", "Vitamin", "Other"
            ],
            state="readonly", width=12
        )
        category.pack(side="left", padx=5)
        category.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(
            toolbar, text="Export CSV", command=self.export_csv
        ).pack(side="right", padx=(5, 0))

        ttk.Button(
            toolbar, text="PDF Report", command=self.export_pdf
        ).pack(side="right")

        # Table
        table_frame = ttk.Frame(main)
        table_frame.pack(fill="both", expand=True)

        columns = (
            "id", "name", "category", "batch", "barcode",
            "quantity", "min_stock", "price", "expiry",
            "manufacturer", "status"
        )

        self.tree = ttk.Treeview(
            table_frame, columns=columns,
            show="headings", selectmode="browse"
        )

        headings = {
            "id": "ID", "name": "Medicine", "category": "Category",
            "batch": "Batch", "barcode": "Barcode", "quantity": "Qty",
            "min_stock": "Min", "price": "Price", "expiry": "Expiry",
            "manufacturer": "Manufacturer", "status": "Status"
        }

        widths = {
            "id": 40, "name": 145, "category": 85, "batch": 85,
            "barcode": 100, "quantity": 50, "min_stock": 50,
            "price": 75, "expiry": 100, "manufacturer": 135,
            "status": 115
        }

        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.column("name", anchor="w")
        self.tree.column("manufacturer", anchor="w")

        self.tree.tag_configure("expired", foreground="#b42318")
        self.tree.tag_configure("soon", foreground="#b54708")
        self.tree.tag_configure("low", foreground="#7a5d00")
        self.tree.tag_configure("safe", foreground="#067647")

        scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Footer
        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(8, 0))

        ttk.Button(
            footer, text="🗑 Delete", command=self.delete_selected
        ).pack(side="left")

        ttk.Button(
            footer, text="⚠ Expiry Report",
            command=self.show_expiry_report
        ).pack(side="left", padx=8)

        ttk.Button(
            footer, text="💾 Backup DB",
            command=self.backup_db
        ).pack(side="left")

        ttk.Button(
            footer, text="↻ Refresh",
            command=self.refresh
        ).pack(side="left", padx=8)

        ttk.Label(
            footer, text="V3.0 • Developed by Sawan Kumar"
        ).pack(side="right")

        self.info_var = tk.StringVar(value="Ready")
        ttk.Label(
            footer, textvariable=self.info_var
        ).pack(side="right", padx=18)

    def make_card(self, parent, title, variable, column):
        card = ttk.LabelFrame(parent, text=title, padding=8)
        card.grid(row=0, column=column, sticky="ew", padx=3)
        parent.columnconfigure(column, weight=1)
        ttk.Label(
            card, textvariable=variable,
            style="CardValue.TLabel"
        ).pack(anchor="center")

    # ---------- VALIDATION / STATUS ----------

    def parse_date(self, value):
        try:
            return datetime.strptime(
                value.strip(), "%d-%m-%Y"
            ).date()
        except ValueError:
            return None

    def get_status(self, expiry_text, quantity, min_stock):
        expiry = self.parse_date(expiry_text)
        if expiry is None:
            return "Invalid"

        days = (expiry - date.today()).days

        if days < 0:
            return "Expired"
        if days <= NEAR_EXPIRY_DAYS:
            return "Expiring Soon"
        if quantity <= min_stock:
            return "Low Stock"
        return "Safe"

    def validate_form(self):
        name = self.name_var.get().strip()
        category = self.category_var.get().strip() or "Other"
        batch = self.batch_var.get().strip()
        barcode = self.barcode_var.get().strip()
        qty_text = self.qty_var.get().strip()
        min_text = self.min_stock_var.get().strip()
        price_text = self.price_var.get().strip() or "0"
        expiry = self.expiry_var.get().strip()
        manufacturer = self.manufacturer_var.get().strip()

        if not name:
            messagebox.showwarning("Missing Data", "Enter medicine name.")
            return None

        try:
            qty = int(qty_text)
            if qty < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Quantity", "Quantity must be 0 or greater.")
            return None

        try:
            minimum = int(min_text)
            if minimum < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Minimum", "Minimum stock must be 0 or greater.")
            return None

        try:
            price = float(price_text)
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Invalid Price", "Price must be a number.")
            return None

        if self.parse_date(expiry) is None:
            messagebox.showwarning(
                "Invalid Date",
                "Use DD-MM-YYYY, for example 15-12-2026."
            )
            return None

        return (
            name, category, batch, barcode, qty,
            minimum, price, expiry, manufacturer
        )

    # ---------- CRUD ----------

    def add_medicine(self):
        data = self.validate_form()
        if not data:
            return

        self.conn.execute("""
            INSERT INTO medicines
            (name, category, batch, barcode, quantity, min_stock,
             price, expiry_date, manufacturer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()

        self.clear_form()
        self.refresh()
        messagebox.showinfo("Success", "Medicine added successfully.")

    def update_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Medicine", "Select a medicine first.")
            return

        data = self.validate_form()
        if not data:
            return

        medicine_id = self.tree.item(selected[0], "values")[0]

        self.conn.execute("""
            UPDATE medicines
            SET name=?, category=?, batch=?, barcode=?, quantity=?,
                min_stock=?, price=?, expiry_date=?, manufacturer=?
            WHERE id=?
        """, (*data, medicine_id))
        self.conn.commit()

        self.clear_form()
        self.refresh()
        messagebox.showinfo("Updated", "Medicine updated successfully.")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Medicine", "Select a medicine first.")
            return

        values = self.tree.item(selected[0], "values")
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{values[1]}'?"
        ):
            return

        self.conn.execute(
            "DELETE FROM medicines WHERE id=?", (values[0],)
        )
        self.conn.commit()
        self.clear_form()
        self.refresh()

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return

        v = self.tree.item(selected[0], "values")
        self.name_var.set(v[1])
        self.category_var.set(v[2])
        self.batch_var.set(v[3])
        self.barcode_var.set(v[4])
        self.qty_var.set(v[5])
        self.min_stock_var.set(v[6])
        self.price_var.set(v[7].replace("₹", ""))
        self.expiry_var.set(v[8])
        self.manufacturer_var.set(v[9])

    def clear_form(self):
        self.name_var.set("")
        self.category_var.set("Tablet")
        self.batch_var.set("")
        self.barcode_var.set("")
        self.qty_var.set("")
        self.min_stock_var.set("10")
        self.price_var.set("")
        self.expiry_var.set("")
        self.manufacturer_var.set("")

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    # ---------- SEARCH / DASHBOARD ----------

    def refresh(self):
        search = self.search_var.get().strip().lower()
        status_filter = self.status_var.get()
        category_filter = self.category_filter_var.get()

        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.conn.execute("""
            SELECT id, name, category, batch, barcode, quantity,
                   min_stock, price, expiry_date, manufacturer
            FROM medicines
            ORDER BY expiry_date ASC
        """).fetchall()

        counts = {
            "Safe": 0,
            "Expiring Soon": 0,
            "Expired": 0,
            "Low Stock": 0
        }
        total_value = 0

        for row in rows:
            (
                medicine_id, name, category, batch, barcode,
                qty, minimum, price, expiry, manufacturer
            ) = row

            status = self.get_status(expiry, qty, minimum)
            if status in counts:
                counts[status] += 1

            total_value += qty * price

            searchable = (
                f"{name} {category} {batch} {barcode} {manufacturer}"
            ).lower()

            if search and search not in searchable:
                continue

            if category_filter != "All" and category != category_filter:
                continue

            if status_filter == "Low Stock":
                if qty > minimum:
                    continue
            elif status_filter != "All" and status != status_filter:
                continue

            tag = {
                "Expired": "expired",
                "Expiring Soon": "soon",
                "Low Stock": "low",
                "Safe": "safe"
            }.get(status, "")

            self.tree.insert(
                "", "end",
                values=(
                    medicine_id, name, category, batch, barcode,
                    qty, minimum, f"₹{price:.2f}", expiry,
                    manufacturer, status
                ),
                tags=(tag,)
            )

        self.total_var.set(str(len(rows)))
        self.safe_var.set(str(counts["Safe"]))
        self.soon_var.set(str(counts["Expiring Soon"]))
        self.expired_var.set(str(counts["Expired"]))
        self.low_var.set(str(counts["Low Stock"]))
        self.value_var.set(f"₹{total_value:,.2f}")

        alerts = []
        if counts["Expired"]:
            alerts.append(f"{counts['Expired']} expired")
        if counts["Expiring Soon"]:
            alerts.append(f"{counts['Expiring Soon']} expiring soon")
        if counts["Low Stock"]:
            alerts.append(f"{counts['Low Stock']} low stock")

        self.info_var.set(
            "⚠ " + " • ".join(alerts)
            if alerts else "✓ No immediate inventory alerts."
        )

    def find_barcode(self):
        code = self.barcode_var.get().strip()
        if not code:
            messagebox.showinfo(
                "Barcode",
                "Enter or scan/type a barcode in the Barcode field, then click Find Barcode."
            )
            return

        rows = self.conn.execute(
            "SELECT id FROM medicines WHERE barcode=? LIMIT 1",
            (code,)
        ).fetchone()

        if not rows:
            messagebox.showinfo(
                "Barcode",
                f"No medicine found for barcode: {code}"
            )
            return

        for item in self.tree.get_children():
            if str(self.tree.item(item, "values")[0]) == str(rows[0]):
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                self.on_select()
                break


    # ---------- WEBCAM BARCODE SCANNER ----------

    def scanner_dependencies_ok(self):
        missing = []
        if cv2 is None:
            missing.append("opencv-python")
        if decode_barcodes is None:
            missing.append("pyzbar")

        if missing:
            messagebox.showwarning(
                "Barcode Scanner Setup",
                "Webcam scanning needs these packages:\n\n"
                + "\n".join(f"pip install {p}" for p in missing)
                + "\n\nInstall them in VS Code Terminal, then restart the app."
            )
            return False
        return True

    def scan_barcode_webcam(self):
        if not self.scanner_dependencies_ok():
            return

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not cap.isOpened():
            cap.release()
            # Retry without the Windows DirectShow backend.
            cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            messagebox.showerror(
                "Camera Error",
                "Could not open the laptop webcam.\n\n"
                "Check that the camera is connected and not being used "
                "by another application."
            )
            return

        scan_window = tk.Toplevel(self.root)
        scan_window.title("📷 Barcode Scanner | By Sawan Kumar")
        scan_window.geometry("760x620")
        scan_window.resizable(False, False)

        ttk.Label(
            scan_window,
            text="Place the barcode inside the camera frame",
            font=("Segoe UI", 13, "bold")
        ).pack(pady=(12, 4))

        ttk.Label(
            scan_window,
            text="Press Q or click Stop Scanner to close.",
            font=("Segoe UI", 9)
        ).pack(pady=(0, 8))

        video_label = ttk.Label(scan_window)
        video_label.pack(padx=12, pady=8)

        status_var = tk.StringVar(value="Scanning...")
        ttk.Label(
            scan_window,
            textvariable=status_var,
            font=("Segoe UI", 10)
        ).pack(pady=5)

        stopped = {"value": False}

        def stop():
            if stopped["value"]:
                return
            stopped["value"] = True
            try:
                cap.release()
            except Exception:
                pass
            cv2.destroyAllWindows()
            if scan_window.winfo_exists():
                scan_window.destroy()

        ttk.Button(
            scan_window,
            text="Stop Scanner",
            command=stop
        ).pack(pady=(4, 12))

        scan_window.protocol("WM_DELETE_WINDOW", stop)

        def update_frame():
            if stopped["value"] or not scan_window.winfo_exists():
                return

            ok, frame = cap.read()

            if not ok:
                status_var.set("Unable to read camera frame.")
                scan_window.after(60, update_frame)
                return

            # Mirror the webcam for a natural preview.
            frame = cv2.flip(frame, 1)

            # Decode all visible barcodes.
            detected = decode_barcodes(frame)

            # Draw scan guides.
            h, w = frame.shape[:2]
            x1, y1 = int(w * 0.12), int(h * 0.30)
            x2, y2 = int(w * 0.88), int(h * 0.70)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            for barcode in detected:
                x, y, bw, bh = barcode.rect
                cv2.rectangle(
                    frame, (x, y), (x + bw, y + bh), (0, 255, 0), 2
                )

                raw = barcode.data.decode("utf-8", errors="ignore").strip()

                if raw:
                    self.barcode_var.set(raw)
                    status_var.set(f"Detected barcode: {raw}")

                    # Try to find it in the database immediately.
                    row = self.conn.execute("""
                        SELECT id FROM medicines WHERE barcode=? LIMIT 1
                    """, (raw,)).fetchone()

                    if row:
                        for item in self.tree.get_children():
                            if str(self.tree.item(item, "values")[0]) == str(row[0]):
                                self.tree.selection_set(item)
                                self.tree.focus(item)
                                self.tree.see(item)
                                self.on_select()
                                break

                        messagebox.showinfo(
                            "Barcode Found",
                            f"Barcode {raw} matched a medicine record."
                        )
                    else:
                        messagebox.showinfo(
                            "Barcode Scanned",
                            f"Barcode detected: {raw}\n\n"
                            "No matching medicine was found in the database.\n"
                            "The barcode has been placed in the Barcode field."
                        )

                    stop()
                    return

            # Convert OpenCV BGR frame to a Tk-compatible image.
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            try:
                from PIL import Image, ImageTk
            except ImportError:
                stop()
                messagebox.showwarning(
                    "Display Dependency",
                    "Install Pillow for webcam preview:\n\n"
                    "pip install pillow"
                )
                return

            image = Image.fromarray(rgb)

            # Keep the preview within the window.
            max_w, max_h = 720, 450
            scale = min(max_w / image.width, max_h / image.height, 1)
            if scale < 1:
                image = image.resize(
                    (int(image.width * scale), int(image.height * scale)),
                    Image.Resampling.LANCZOS
                )

            photo = ImageTk.PhotoImage(image=image)
            video_label.configure(image=photo)
            video_label.image = photo

            scan_window.after(30, update_frame)

        update_frame()

    # ---------- REPORTS ----------

    def export_csv(self):
        rows = self.conn.execute("""
            SELECT id, name, category, batch, barcode, quantity,
                   min_stock, price, expiry_date, manufacturer
            FROM medicines
            ORDER BY expiry_date ASC
        """).fetchall()

        if not rows:
            messagebox.showinfo("Export", "No medicines available.")
            return

        path = filedialog.asksaveasfilename(
            title="Save Medicine CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Medicine", "Category", "Batch", "Barcode",
                "Quantity", "Minimum Stock", "Price/Unit",
                "Expiry Date", "Manufacturer", "Status"
            ])
            for row in rows:
                writer.writerow([
                    *row,
                    self.get_status(row[8], row[5], row[6])
                ])

        messagebox.showinfo("Export Complete", f"Saved:\n{path}")

    def export_pdf(self):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle,
                Paragraph, Spacer
            )
        except ImportError:
            messagebox.showwarning(
                "PDF Package Missing",
                "Install ReportLab first:\n\npip install reportlab"
            )
            return

        rows = self.conn.execute("""
            SELECT name, category, batch, quantity, expiry_date, manufacturer
            FROM medicines
            ORDER BY expiry_date ASC
        """).fetchall()

        if not rows:
            messagebox.showinfo("PDF Report", "No medicines available.")
            return

        path = filedialog.asksaveasfilename(
            title="Save PDF Report",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return

        doc = SimpleDocTemplate(
            path, pagesize=landscape(A4),
            rightMargin=25, leftMargin=25,
            topMargin=25, bottomMargin=25
        )
        styles = getSampleStyleSheet()

        story = [
            Paragraph(
                "Medicine Expiry Tracker — Inventory Report",
                styles["Title"]
            ),
            Paragraph(
                "Developed by Sawan Kumar",
                styles["Normal"]
            ),
            Spacer(1, 12)
        ]

        data = [[
            "Medicine", "Category", "Batch",
            "Qty", "Expiry", "Manufacturer", "Status"
        ]]

        for r in rows:
            status = self.get_status(r[4], r[3], 0)
            data.append([
                r[0], r[1], r[2], r[3], r[4], r[5], status
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.whitesmoke]),
        ]))

        story.append(table)
        doc.build(story)

        messagebox.showinfo("PDF Report", f"PDF saved:\n{path}")

    def show_expiry_report(self):
        rows = self.conn.execute("""
            SELECT name, category, batch, quantity, expiry_date, manufacturer
            FROM medicines ORDER BY expiry_date ASC
        """).fetchall()

        expired = []
        soon = []

        for r in rows:
            status = self.get_status(r[4], r[3], 0)
            if status == "Expired":
                expired.append(r)
            elif status == "Expiring Soon":
                soon.append(r)

        win = tk.Toplevel(self.root)
        win.title("Expiry Alert Report")
        win.geometry("760x520")

        frame = ttk.Frame(win, padding=15)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="⚠ Medicine Expiry Report",
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=f"Expired: {len(expired)}  |  Expiring within 30 days: {len(soon)}"
        ).pack(anchor="w", pady=(3, 12))

        text = tk.Text(frame, wrap="word", font=("Consolas", 10))
        text.pack(fill="both", expand=True)

        if not expired and not soon:
            text.insert("end", "✓ No expiry alerts at this time.")
        else:
            if expired:
                text.insert("end", "EXPIRED MEDICINES\n" + "-" * 70 + "\n")
                for r in expired:
                    text.insert(
                        "end",
                        f"{r[0]} | Batch: {r[2]} | Expiry: {r[4]} | Qty: {r[3]}\n"
                    )
                text.insert("end", "\n")

            if soon:
                text.insert("end", "EXPIRING WITHIN 30 DAYS\n" + "-" * 70 + "\n")
                for r in soon:
                    text.insert(
                        "end",
                        f"{r[0]} | Batch: {r[2]} | Expiry: {r[4]} | Qty: {r[3]}\n"
                    )

        text.configure(state="disabled")

    # ---------- BACKUP ----------

    def backup_db(self):
        path = filedialog.asksaveasfilename(
            title="Backup Medicine Database",
            defaultextension=".db",
            filetypes=[("SQLite database", "*.db")]
        )
        if not path:
            return

        self.conn.commit()
        shutil.copy2(DB_NAME, path)
        messagebox.showinfo(
            "Backup Complete",
            f"Database backup created:\n{path}"
        )

    def close_app(self):
        self.conn.close()
        self.root.destroy()


def start_app():
    root = tk.Tk()
    LoginWindow(root, open_dashboard)
    root.mainloop()


def open_dashboard():
    dashboard_root = tk.Tk()
    MedicineExpiryTracker(dashboard_root)
    dashboard_root.mainloop()


if __name__ == "__main__":
    start_app()