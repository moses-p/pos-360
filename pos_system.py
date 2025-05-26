import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from tksheet import Sheet
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image, ImageTk
import os
from datetime import datetime
import json
from collections import defaultdict
import shutil
import math
import hashlib
import sys
import logging
import traceback
import random

# Set up logging
logging.basicConfig(
    filename=os.path.join(os.environ['APPDATA'], 'POS_System', 'pos_system.log'),
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Get the application data directory
APP_DATA_DIR = os.path.join(os.environ['APPDATA'], 'POS_System')
os.makedirs(APP_DATA_DIR, exist_ok=True)

# Update file paths to use APP_DATA_DIR
USERS_FILE = os.path.join(APP_DATA_DIR, 'users.json')
INVENTORY_FILE = os.path.join(APP_DATA_DIR, 'inventory.json')
SALES_FILE = os.path.join(APP_DATA_DIR, 'sales.json')
DB_FILE = os.path.join(APP_DATA_DIR, 'pos_database.db')

def show_error_and_exit(error_msg):
    """Show error message and wait before exiting"""
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Application Error:\n{error_msg}\n\nCheck the log file for details.")
        root.destroy()
    except:
        pass
    sys.exit(1)

class POSSystem:
    def __init__(self):
        # Set up DPI awareness
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
        self.user_roles = {}  # Ensure attribute exists early
        self.window = ctk.CTk()
        self.window.title("Modern POS System")
        # Increase window size for retail environment
        self.window.geometry("1920x1080")  # Full HD resolution
        self.window.state('zoomed')  # Start maximized
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize data
        self.cart = []
        self.products = self.load_products()
        self.sales_history = self.load_sales_history()
        self.settings = self.load_settings()
        self.current_user = None
        self.current_role = None
        self.user_roles = self.load_user_roles()  # Load user roles after initializations
        
        # Initialize logo-related variables
        self.original_logo = None
        self.logo_tk = None
        self.angle = 0
        
        # Initialize search history
        self.search_history = []
        self.max_search_history = 10
        
        # Show login dialog first
        self.show_login()
        
    def hash_password(self, password):
        """Hash password for security"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def load_user_roles(self):
        """Load user roles from JSON file"""
        self.user_roles = {}
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as f:
                    self.user_roles = json.load(f)
        except Exception as e:
            print(f"Error loading user roles: {e}")
            self.user_roles = {}
        return self.user_roles
        
    def save_user_roles(self):
        """Save user roles to JSON file"""
        try:
            with open(USERS_FILE, 'w') as f:
                json.dump(self.user_roles, f)
        except Exception as e:
            print(f"Error saving user roles: {e}")
            
    def show_login(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("POS System Login")
        # Set a minimum size, but not fixed
        min_width, min_height = 600, 400
        dialog.minsize(min_width, min_height)
        # Center the dialog on the screen
        dialog.update_idletasks()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (min_width // 2)
        y = (screen_height // 2) - (min_height // 2)
        dialog.geometry(f"{min_width}x{min_height}+{x}+{y}")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Create main frame for login
        login_frame = ctk.CTkFrame(dialog)
        login_frame.pack(fill="both", expand=True, padx=20, pady=20)  # Responsive padding
        
        # Create canvas for rotating logo
        canvas_frame = ctk.CTkFrame(login_frame)
        canvas_frame.pack(fill="x", pady=(20, 10))  # Responsive padding
        
        # Get the background color from the frame
        bg_color = login_frame._apply_appearance_mode(login_frame._fg_color)
        
        self.canvas = tk.Canvas(
            canvas_frame,
            width=150,  # Adaptive canvas
            height=150,
            bg=bg_color,
            highlightthickness=0
        )
        self.canvas.pack(pady=10)
        
        # Load logo with fallback handling
        if not self.load_logo(canvas_frame):
            print("Failed to load logo, showing text fallback")
        
        # Create login form frame with responsive spacing
        form_frame = ctk.CTkFrame(login_frame)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Username field
        username_frame = ctk.CTkFrame(form_frame)
        username_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(
            username_frame,
            text="Username:",
            font=("Arial", 16, "bold"),
            width=120
        ).pack(side="left", padx=10)
        username_entry = ctk.CTkEntry(username_frame, width=250, height=35)
        username_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        # Password field
        password_frame = ctk.CTkFrame(form_frame)
        password_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(
            password_frame,
            text="Password:",
            font=("Arial", 16, "bold"),
            width=120
        ).pack(side="left", padx=10)
        password_entry = ctk.CTkEntry(password_frame, width=250, height=35, show="•")
        password_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        def login():
            username = username_entry.get()
            password = password_entry.get()
            
            if username in self.user_roles and self.user_roles[username]["password"] == self.hash_password(password):
                self.current_user = username
                self.current_role = self.user_roles[username]["role"]
                # Update last login
                self.user_roles[username]["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_user_roles()
                dialog.destroy()
                self.setup_ui()
                self.setup_keyboard_shortcuts()
            else:
                messagebox.showerror("Error", "Invalid credentials!")
                
        # Login button
        login_btn = ctk.CTkButton(
            form_frame,
            text="Login",
            command=login,
            width=200,
            height=40,
            font=("Arial", 16, "bold")
        )
        login_btn.pack(pady=20)
        
        def on_enter(event):
            login()
        username_entry.bind("<Return>", on_enter)
        password_entry.bind("<Return>", on_enter)
        username_entry.focus()
        
    def animate_logo(self):
        try:
            if not hasattr(self, 'original_logo') or self.original_logo is None:
                print("No logo to animate")
                return
                
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # Canvas not ready yet, try again in 100ms
                self.canvas.after(100, self.animate_logo)
                return
            
            # Rotate the logo
            rotated_logo = self.original_logo.rotate(self.angle, expand=True, resample=Image.Resampling.BICUBIC)
            
            # Convert to PhotoImage
            self.logo_tk = ImageTk.PhotoImage(rotated_logo)
            
            # Clear canvas
            self.canvas.delete("all")
            
            # Calculate center position
            x = (canvas_width - rotated_logo.width) // 2
            y = (canvas_height - rotated_logo.height) // 2
            
            # Draw the rotated logo
            self.canvas.create_image(x, y, image=self.logo_tk, anchor="nw")
            
            # Update angle for next rotation (slower rotation)
            self.angle = (self.angle + 1) % 360
            
            # Schedule next frame only if window still exists
            if self.window.winfo_exists():
                self.canvas.after(30, self.animate_logo)  # ~33 FPS
            
        except Exception as e:
            print(f"Animation error: {e}")
            import traceback
            traceback.print_exc()

    def load_logo(self, canvas_frame):
        """Load the logo image with fallback handling"""
        logo_paths = [
            "mylogo.png",  # Custom logo
            os.path.join(os.path.dirname(__file__), "mylogo.png"),  # In script directory
            os.path.join(os.path.dirname(sys.executable), "mylogo.png"),  # In exe directory
        ]
        
        print("Attempting to load logo...")
        for path in logo_paths:
            print(f"Trying path: {path}")
            try:
                if os.path.exists(path):
                    print(f"Found logo at: {path}")
                    self.original_logo = Image.open(path)
                    logo_size = 150  # Reduced size for better fit
                    self.original_logo = self.original_logo.resize(
                        (logo_size, logo_size),
                        Image.Resampling.LANCZOS
                    )
                    self.angle = 0
                    print("Logo loaded successfully, starting animation")
                    self.animate_logo()
                    return True
            except Exception as e:
                print(f"Error loading logo from {path}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print("No logo found, showing text fallback")
        # If no logo was loaded successfully, show text instead
        ctk.CTkLabel(
            canvas_frame,
            text="POS System",
            font=("Arial", 24, "bold")
        ).pack(pady=20)
        return False
        
    def setup_ui(self):
        # Clear any existing widgets in the window
        for widget in self.window.winfo_children():
            widget.destroy()

        # Set window title and theme
        if self.current_role == "admin":
            self.window.title("Modern POS System - Admin")
        else:
            self.window.title("Modern POS System - Staff")
        self.window.geometry("1920x1080")  # Full HD resolution
        self.window.state('zoomed')  # Start maximized
        ctk.set_appearance_mode(self.settings.get("theme", "dark"))

        # Set a minimum window width to ensure all bars are visible
        self.window.minsize(1400, 800)

        # Main horizontal layout: left bar, center, right bar
        main_layout = ctk.CTkFrame(self.window)
        main_layout.pack(fill="both", expand=True)

        # Left bar (vertical navigation/actions)
        left_bar = ctk.CTkFrame(main_layout, width=180)
        left_bar.pack(side="left", fill="y")

        # Center (spreadsheet/cart)
        center_frame = ctk.CTkFrame(main_layout)
        center_frame.pack(side="left", fill="both", expand=True)

        # Right bar (vertical, large payment controls and actions)
        right_bar = ctk.CTkFrame(main_layout)
        right_bar.pack(side="right", fill="y", expand=False)
        right_bar.grid_propagate(False)
        # Set a minimum and max width for right bar
        min_right_bar_width = 260
        max_right_bar_width = 420
        def update_right_bar_width(event=None):
            win_width = self.window.winfo_width()
            # Responsive width: 18% of window, clamped to min/max
            new_width = max(min_right_bar_width, min(int(win_width * 0.18), max_right_bar_width))
            right_bar.configure(width=new_width)
        self.window.bind('<Configure>', update_right_bar_width)
        update_right_bar_width()

        # --- Left Bar: Navigation/Actions ---
        button_width = 160
        button_height = 40
        button_font = ("Arial", 14, "bold")
        nav_buttons = []
        if self.current_role == "admin":
            nav_buttons = [
                ("Inventory", self.show_inventory),
                ("Sales History", self.show_sales_history),
                ("Dashboard", self.show_dashboard),
                ("Settings", self.show_settings),
                ("Backup Data", self.backup_data),
                ("Restore Data", self.restore_data),
                ("Manage Users", self.show_user_management),
                ("Add Product", self.add_product_dialog),
                ("Scan Barcode", self.scan_barcode),
            ]
        else:
            nav_buttons = [
                ("Scan Barcode", self.scan_barcode),
                ("Print Receipt", self.print_receipt),
            ]
        for text, cmd in nav_buttons:
            ctk.CTkButton(left_bar, text=text, command=cmd, width=button_width, height=button_height, font=button_font).pack(pady=6)
        # Logout always at the bottom
        ctk.CTkButton(left_bar, text="Logout", command=self.logout, width=button_width, height=button_height, font=button_font, fg_color="red").pack(side="bottom", pady=12)

        # --- Center: Search Bar and Spreadsheet/Cart ---
        # Add search bar at the top of center frame
        search_frame = ctk.CTkFrame(center_frame)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        # Search type selection
        search_type_frame = ctk.CTkFrame(search_frame)
        search_type_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            search_type_frame,
            text="Search Type:",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        
        self.search_type = ctk.StringVar(value="name")
        ctk.CTkRadioButton(
            search_type_frame,
            text="Name",
            variable=self.search_type,
            value="name",
            font=("Arial", 12)
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            search_type_frame,
            text="Barcode",
            variable=self.search_type,
            value="barcode",
            font=("Arial", 12)
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            search_type_frame,
            text="Price Range",
            variable=self.search_type,
            value="price",
            font=("Arial", 12)
        ).pack(side="left", padx=5)
        
        # Main search frame
        main_search_frame = ctk.CTkFrame(search_frame)
        main_search_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            main_search_frame,
            text="Search:",
            font=("Arial", 14, "bold")
        ).pack(side="left", padx=5)
        
        self.search_entry = ctk.CTkEntry(
            main_search_frame,
            width=300,
            height=35,
            font=("Arial", 14),
            placeholder_text="Type to search products..."
        )
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Price range frame (initially hidden)
        self.price_range_frame = ctk.CTkFrame(search_frame)
        self.min_price_entry = ctk.CTkEntry(
            self.price_range_frame,
            width=150,
            height=35,
            font=("Arial", 14),
            placeholder_text="Min Price"
        )
        self.min_price_entry.pack(side="left", padx=5)
        ctk.CTkLabel(
            self.price_range_frame,
            text="to",
            font=("Arial", 14)
        ).pack(side="left", padx=5)
        self.max_price_entry = ctk.CTkEntry(
            self.price_range_frame,
            width=150,
            height=35,
            font=("Arial", 14),
            placeholder_text="Max Price"
        )
        self.max_price_entry.pack(side="left", padx=5)
        
        # Search history dropdown
        self.search_history_var = ctk.StringVar()
        self.search_history_dropdown = ctk.CTkOptionMenu(
            main_search_frame,
            values=self.search_history,
            variable=self.search_history_var,
            command=self.use_search_history,
            width=150,
            height=35,
            font=("Arial", 14)
        )
        self.search_history_dropdown.pack(side="left", padx=5)
        
        # Add search button
        search_btn = ctk.CTkButton(
            main_search_frame,
            text="Search",
            command=self.search_products,
            width=100,
            height=35,
            font=("Arial", 14)
        )
        search_btn.pack(side="left", padx=5)
        
        # Add clear button
        clear_btn = ctk.CTkButton(
            main_search_frame,
            text="Clear",
            command=self.clear_search,
            width=100,
            height=35,
            font=("Arial", 14),
            fg_color="gray",
            hover_color="darkgray"
        )
        clear_btn.pack(side="left", padx=5)
        
        # Bind Enter key to search
        self.search_entry.bind("<Return>", self.search_products)
        
        # Bind search type change
        self.search_type.trace("w", self.on_search_type_change)
        
        # Add keyboard shortcut for search focus (Ctrl+F)
        self.window.bind("<Control-f>", self.focus_search)
        
        # Create two frames for products and cart
        products_frame = ctk.CTkFrame(center_frame)
        products_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cart_frame = ctk.CTkFrame(center_frame)
        cart_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Products sheet
        ctk.CTkLabel(products_frame, text="Available Products", font=("Arial", 16, "bold")).pack(pady=5)
        self.products_sheet = Sheet(products_frame, row_height=36)
        self.products_sheet.pack(fill="both", expand=True)
        headers = ["Barcode", "Product", "Price", "Stock"]
        self.products_sheet.headers(headers)
        self.products_sheet.enable_bindings()
        
        # Add a simple click handler
        def on_click(event):
            try:
                # Get the clicked cell coordinates
                x, y = event.x, event.y
                # Get the row and column
                row = self.products_sheet.identify_row(event)
                col = self.products_sheet.identify_column(event)
                
                if row is not None and col is not None:
                    # Get the barcode from the first column
                    barcode = self.products_sheet.get_cell_data(row, 0)
                    if barcode in self.products:
                        product = self.products[barcode]
                        # Check stock
                        if product.get("stock", 0) > 0:
                            self.add_to_cart(product)
                            # Update stock
                            product["stock"] -= 1
                            self.save_products()
                            self.update_spreadsheet()
                        else:
                            messagebox.showerror("Error", "Product out of stock!")
            except Exception as e:
                logging.error(f"Error in click handler: {e}")
                messagebox.showerror("Error", "Failed to process click")
        
        # Bind both single and double click
        self.products_sheet.bind("<ButtonRelease-1>", on_click)
        self.products_sheet.bind("<Double-ButtonRelease-1>", on_click)
        self.products_sheet.set_column_widths([160, 320, 160, 120])

        # Add a selection changed handler
        def on_selection_changed(event):
            try:
                # Get the selected cells
                selected = self.products_sheet.get_selected_cells()
                logging.debug(f"on_selection_changed: selected={selected}")
                if selected:
                    # Convert set to list and get first item
                    selected_list = list(selected)
                    logging.debug(f"on_selection_changed: selected_list={selected_list}")
                    if selected_list:
                        row = selected_list[0][0]  # Get row from first selected cell
                        logging.debug(f"on_selection_changed: row={row}")
                        # Get the barcode from the first column
                        barcode = self.products_sheet.get_cell_data(row, 0)
                        logging.debug(f"on_selection_changed: barcode={barcode}")
                        if barcode in self.products:
                            product = self.products[barcode]
                            # Check stock
                            if product.get("stock", 0) > 0:
                                self.add_to_cart(product)
                                # Update stock
                                product["stock"] -= 1
                                self.save_products()
                                self.update_spreadsheet()
                            else:
                                messagebox.showerror("Error", "Product out of stock!")
                        else:
                            logging.error(f"Barcode {barcode} not found in products!")
                # No else needed; do nothing if no selection
            except Exception as e:
                logging.error(f"Error in selection handler: {e}")
                messagebox.showerror("Error", "Failed to process selection")
        
        # Bind selection changed event
        self.products_sheet.bind("<<SelectionChanged>>", on_selection_changed)

        # Add a cell selected handler
        def on_cell_selected(event):
            try:
                # Get the selected cell
                selected = self.products_sheet.get_selected_cells()
                if selected:
                    # Convert set to list and get first item
                    selected_list = list(selected)
                    if selected_list:
                        row = selected_list[0][0]  # Get row from first selected cell
                        # Get the barcode from the first column
                        barcode = self.products_sheet.get_cell_data(row, 0)
                        if barcode in self.products:
                            product = self.products[barcode]
                            # Check stock
                            if product.get("stock", 0) > 0:
                                self.add_to_cart(product)
                                # Update stock
                                product["stock"] -= 1
                                self.save_products()
                                self.update_spreadsheet()
                            else:
                                messagebox.showerror("Error", "Product out of stock!")
            except Exception as e:
                logging.error(f"Error in cell selected handler: {e}")
        
        # Bind cell selected event
        self.products_sheet.bind("<<CellSelected>>", on_cell_selected)

        # Add a cell clicked handler
        def on_cell_clicked(event):
            try:
                # Get the clicked cell coordinates
                x, y = event.x, event.y
                # Get the row and column
                row = self.products_sheet.identify_row(event)
                col = self.products_sheet.identify_column(event)
                
                if row is not None and col is not None:
                    # Get the barcode from the first column
                    barcode = self.products_sheet.get_cell_data(row, 0)
                    if barcode in self.products:
                        product = self.products[barcode]
                        # Check stock
                        if product.get("stock", 0) > 0:
                            self.add_to_cart(product)
                            # Update stock
                            product["stock"] -= 1
                            self.save_products()
                            self.update_spreadsheet()
                        else:
                            messagebox.showerror("Error", "Product out of stock!")
            except Exception as e:
                logging.error(f"Error in cell clicked handler: {e}")
        
        # Bind cell clicked event
        self.products_sheet.bind("<<CellClicked>>", on_cell_clicked)

        # Add a cell double clicked handler
        def on_cell_double_clicked(event):
            try:
                # Get the clicked cell coordinates
                x, y = event.x, event.y
                # Get the row and column
                row = self.products_sheet.identify_row(event)
                col = self.products_sheet.identify_column(event)
                
                if row is not None and col is not None:
                    # Get the barcode from the first column
                    barcode = self.products_sheet.get_cell_data(row, 0)
                    if barcode in self.products:
                        product = self.products[barcode]
                        # Check stock
                        if product.get("stock", 0) > 0:
                            self.add_to_cart(product)
                            # Update stock
                            product["stock"] -= 1
                            self.save_products()
                            self.update_spreadsheet()
                        else:
                            messagebox.showerror("Error", "Product out of stock!")
            except Exception as e:
                logging.error(f"Error in cell double clicked handler: {e}")
        
        # Bind cell double clicked event
        self.products_sheet.bind("<<CellDoubleClicked>>", on_cell_double_clicked)

        # Cart sheet
        ctk.CTkLabel(cart_frame, text="Shopping Cart", font=("Arial", 16, "bold")).pack(pady=5)
        self.cart_sheet = Sheet(cart_frame, row_height=36)
        self.cart_sheet.pack(fill="both", expand=True)
        headers = ["Barcode", "Product", "Price", "Quantity", "Total"]
        self.cart_sheet.headers(headers)
        self.cart_sheet.enable_bindings()
        self.cart_sheet.set_column_widths([160, 320, 160, 120, 160])

        # --- Right Bar: Payment Controls (retail size) ---
        print('Creating right bar widgets...')
        ctk.CTkLabel(right_bar, text="Discount:", font=("Arial", 0, "bold"))
        self.discount_entry = ctk.CTkEntry(right_bar, font=("Arial", 0))
        # Use place geometry manager for flexible sizing
        def resize_right_widgets(event=None):
            bar_width = right_bar.winfo_width()
            # Responsive font size
            font_size = max(18, min(32, int(bar_width / 10)))
            label_font = ("Arial", font_size, "bold")
            entry_font = ("Arial", font_size)
            btn_font = ("Arial", font_size + 2, "bold")
            self.discount_entry.configure(width=bar_width-40, height=int(font_size*2.5), font=entry_font)
            self.payment_entry.configure(width=bar_width-40, height=int(font_size*2.5), font=entry_font)
            self.total_label.configure(font=("Arial", font_size+8, "bold"))
            self.change_label.configure(font=("Arial", font_size+8, "bold"))
            print_btn.configure(width=bar_width-40, height=int(font_size*2.8), font=btn_font)
            # Update label fonts
            for lbl in [discount_lbl, payment_lbl]:
                lbl.configure(font=label_font)
        discount_lbl = ctk.CTkLabel(right_bar, text="Discount:", font=("Arial", 28, "bold"))
        discount_lbl.pack(pady=(40, 12))
        self.discount_entry.pack(pady=12, fill="x", padx=20)
        self.discount_entry.bind("<KeyRelease>", self.update_totals)

        payment_lbl = ctk.CTkLabel(right_bar, text="Payment:", font=("Arial", 28, "bold"))
        payment_lbl.pack(pady=(40, 12))
        self.payment_entry = ctk.CTkEntry(right_bar, font=("Arial", 28))
        self.payment_entry.pack(pady=12, fill="x", padx=20)
        self.payment_entry.bind("<KeyRelease>", self.update_totals)

        self.total_label = ctk.CTkLabel(right_bar, text="Total: UGX 0", font=("Arial", 36, "bold"))
        self.total_label.pack(pady=(40, 18))
        self.change_label = ctk.CTkLabel(right_bar, text="Change: UGX 0", font=("Arial", 36, "bold"))
        self.change_label.pack(pady=18)

        print_btn = ctk.CTkButton(right_bar, text="Print Receipt", command=self.print_receipt, font=("Arial", 28, "bold"))
        print_btn.pack(pady=(50, 20), fill="x", padx=20)

        # Responsive resizing for right bar widgets
        self.window.bind('<Configure>', resize_right_widgets)
        resize_right_widgets()

        # Force redraw of right bar
        right_bar.update_idletasks()

        # Update spreadsheet/cart
        self.update_spreadsheet()

    def setup_keyboard_shortcuts(self):
        self.window.bind("<F2>", lambda e: self.add_product_dialog())
        self.window.bind("<F3>", lambda e: self.scan_barcode())
        self.window.bind("<F4>", lambda e: self.print_receipt())
        self.window.bind("<F5>", lambda e: self.clear_cart())
        self.window.bind("<F6>", lambda e: self.show_inventory())
        self.window.bind("<F7>", lambda e: self.show_sales_history())
        self.window.bind("<F8>", lambda e: self.show_dashboard())
        self.window.bind("<F9>", lambda e: self.show_settings())
        self.window.bind("<F10>", lambda e: self.backup_data())
        self.window.bind("<F11>", lambda e: self.restore_data())
        self.window.bind("<F12>", lambda e: self.show_user_management())
        
    def on_search_type_change(self, *args):
        """Handle search type change"""
        search_type = self.search_type.get()
        if search_type == "price":
            self.price_range_frame.pack(fill="x", padx=5, pady=5)
            self.search_entry.pack_forget()
        else:
            self.price_range_frame.pack_forget()
            self.search_entry.pack(side="left", padx=5, fill="x", expand=True)

    def focus_search(self, event=None):
        """Focus the search entry when Ctrl+F is pressed"""
        search_type = self.search_type.get()
        if search_type == "price":
            self.min_price_entry.focus()
        else:
            self.search_entry.focus()

    def use_search_history(self, choice):
        """Use a search term from history"""
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, choice)
        self.search_products()

    def add_to_search_history(self, search_term):
        """Add a search term to history"""
        if search_term and search_term not in self.search_history:
            self.search_history.insert(0, search_term)
            if len(self.search_history) > self.max_search_history:
                self.search_history.pop()
            self.search_history_dropdown.configure(values=self.search_history)
        
    def search_products(self, event=None):
        """Enhanced search products with fuzzy matching and price range"""
        search_type = self.search_type.get()
        
        if search_type == "price":
            try:
                min_price = float(self.min_price_entry.get().strip() or 0)
                max_price = float(self.max_price_entry.get().strip() or float('inf'))
            except ValueError:
                messagebox.showerror("Error", "Please enter valid price numbers!")
                return

            filtered_cart = [
                item for item in self.cart
                if min_price <= item["price"] <= max_price
            ]
            # Clear and update spreadsheet with filtered items
            self.products_sheet.set_sheet_data([])
            for item in filtered_cart:
                self.products_sheet.insert_row([
                    item["barcode"],
                    item["name"],
                    f"UGX {item['price']:,.0f}",
                    item["quantity"],
                    f"UGX {item['price'] * item['quantity']:,.0f}"
                ])
            self.update_totals()
            return
        else:
            search_term = self.search_entry.get().strip().lower()
            if not search_term:
                self.update_spreadsheet()
                return
            # Add to search history
            self.add_to_search_history(search_term)
            # Fuzzy search implementation
            from difflib import SequenceMatcher
            def similarity(a, b):
                return SequenceMatcher(None, a.lower(), b.lower()).ratio()
            filtered_cart = []
            for item in self.cart:
                if search_type == "name":
                    # Fuzzy match on name
                    if similarity(item["name"], search_term) > 0.6:
                        filtered_cart.append(item)
                else:  # barcode
                    # Exact match on barcode
                    if search_term in item["barcode"].lower():
                        filtered_cart.append(item)
            # Clear and update spreadsheet with filtered items
            self.products_sheet.set_sheet_data([])
            for item in filtered_cart:
                self.products_sheet.insert_row([
                    item["barcode"],
                    item["name"],
                    f"UGX {item['price']:,.0f}",
                    item["quantity"],
                    f"UGX {item['price'] * item['quantity']:,.0f}"
                ])
            self.update_totals()

    def edit_cell(self, event):
        # Get the clicked cell
        clicked_box = self.products_sheet.identify_region(event.x, event.y)
        if clicked_box == "cells":
            row = self.products_sheet.identify_row(event.y)
            col = self.products_sheet.identify_column(event.x)
            
            # Only allow editing quantity column
            if col == 3:  # Quantity column
                current_value = self.products_sheet.get_cell_data(row, col)
                try:
                    new_quantity = int(current_value)
                    if new_quantity > 0:
                        self.cart[row]["quantity"] = new_quantity
                        self.update_spreadsheet()
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid quantity!")
                    
    def clear_cart(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the cart?"):
            self.cart = []
            self.update_spreadsheet()
            
    def scan_barcode(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Add Product")
        dialog.geometry("400x500")
        
        # Create tabs for barcode and manual selection
        tabview = ctk.CTkTabview(dialog)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Barcode tab
        barcode_tab = tabview.add("Scan Barcode")
        
        # Barcode input frame
        barcode_frame = ctk.CTkFrame(barcode_tab)
        barcode_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(barcode_frame, text="Enter or Scan Barcode:").pack(pady=5)
        barcode_entry = ctk.CTkEntry(barcode_frame)
        barcode_entry.pack(pady=5, fill="x", expand=True)
        barcode_entry.focus()
        
        # Add instructions
        instructions_frame = ctk.CTkFrame(barcode_tab)
        instructions_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            instructions_frame,
            text="Instructions:",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=5, pady=2)
        ctk.CTkLabel(
            instructions_frame,
            text="1. Type barcode manually and press Enter",
            font=("Arial", 11)
        ).pack(anchor="w", padx=5)
        ctk.CTkLabel(
            instructions_frame,
            text="2. Or scan barcode using barcode scanner",
            font=("Arial", 11)
        ).pack(anchor="w", padx=5)
        
        def process_barcode(event=None):
            barcode = barcode_entry.get().strip()
            if not barcode:
                return
                
            if barcode in self.products:
                product = self.products[barcode]
                self.add_to_cart(product)
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Product not found!")
                barcode_entry.delete(0, "end")
                barcode_entry.focus()
        
        # Handle both Enter key and barcode scanner input
        barcode_entry.bind("<Return>", process_barcode)
        
        # Add a small delay to handle barcode scanner input
        def on_barcode_change(*args):
            dialog.after(100, lambda: check_barcode_length())
            
        def check_barcode_length():
            barcode = barcode_entry.get().strip()
            # Most barcode scanners end with Enter key, but some don't
            # If we have a reasonable length barcode, process it
            if len(barcode) >= 8:  # Minimum length for most barcodes
                process_barcode()
        
        barcode_entry.bind("<KeyRelease>", on_barcode_change)
        
        ctk.CTkButton(barcode_tab, text="Add", command=process_barcode).pack(pady=10)
        
        # Manual selection tab
        manual_tab = tabview.add("Select Product")
        
        # Search frame
        search_frame = ctk.CTkFrame(manual_tab)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=5)
        search_entry = ctk.CTkEntry(search_frame)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Product list
        list_frame = ctk.CTkFrame(manual_tab)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create product list
        product_list = Sheet(list_frame)
        product_list.pack(fill="both", expand=True)
        product_list.headers(["Product Name", "Price", "Stock"])
        
        # Define row_barcodes as a list to store barcodes
        row_barcodes = []
        
        def update_product_list(search_term=""):
            product_list.set_sheet_data([])
            row_barcodes.clear()
            for barcode, product in self.products.items():
                if search_term.lower() in product["name"].lower():
                    product_list.insert_row([
                        product["name"],
                        f"UGX {product['price']:,.0f}",
                        product.get("stock", 0)
                    ])
                    row_barcodes.append(barcode)
        
        def manual_product_select(event):
            try:
                logging.debug(f"manual_product_select called with type={type(event)}, value={event}")
                # If event is an int, use it directly as the row
                if isinstance(event, int):
                    row = event
                # If event is an event object, pass it directly to identify_row
                elif hasattr(event, "y"):
                    try:
                        row = product_list.identify_row(event)
                        logging.debug(f"identify_row returned: {row} (type: {type(row)})")
                    except Exception as e:
                        logging.error(f"Error in identify_row: {e}")
                        return
                else:
                    logging.error(f"manual_product_select received unexpected argument: {event}")
                    return  # Unexpected signature

                if row is not None and isinstance(row, int) and 0 <= row < len(row_barcodes):
                    barcode = row_barcodes[row]
                    if barcode in self.products:
                        self.add_to_cart(self.products[barcode])
                        messagebox.showinfo("Added to Cart", f"{self.products[barcode]['name']} added to cart.")
                        dialog.destroy()
                    else:
                        messagebox.showerror("Error", "Barcode not found in products!")
            except Exception as e:
                logging.error(f"Error in manual_product_select (outer): {e}")
                messagebox.showerror("Error", "Failed to process selection")
        # Bind both single and double click to the renamed function
        product_list.bind("<Button-1>", manual_product_select)
        product_list.bind("<Double-Button-1>", manual_product_select)
        
        # Initial product list
        update_product_list()
        
        # Set initial tab
        tabview.set("Select Product")
        
    def load_products(self):
        # Load products from JSON file or create default products
        if os.path.exists(os.path.join(APP_DATA_DIR, "products.json")):
            with open(os.path.join(APP_DATA_DIR, "products.json"), "r") as f:
                return json.load(f)
        return {
            "123456789": {"name": "Sample Product", "price": 9.99}
        }
        
    def save_products(self):
        with open(os.path.join(APP_DATA_DIR, "products.json"), "w") as f:
            json.dump(self.products, f)
            
    def add_product_dialog(self):
        # Check if user is admin
        if self.current_role != "admin":
            messagebox.showerror("Error", "Only administrators can add products!")
            return
            
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Add Product")
        dialog.geometry("800x600")  # Larger dialog size
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Create form with increased sizes
        form_font = ("Arial", 20)  # Larger form font
        label_font = ("Arial", 20, "bold")  # Larger label font
        entry_width = 400  # Wider entry
        entry_height = 50  # Taller entry
        
        # Product Type Selection
        type_frame = ctk.CTkFrame(dialog)
        type_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            type_frame,
            text="Product Type:",
            font=label_font
        ).pack(side="left", padx=10)
        
        type_var = ctk.StringVar(value="barcode")
        ctk.CTkRadioButton(
            type_frame,
            text="With Barcode",
            variable=type_var,
            value="barcode",
            font=form_font
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            type_frame,
            text="Without Barcode",
            variable=type_var,
            value="no_barcode",
            font=form_font
        ).pack(side="left", padx=10)
        
        # Barcode frame
        barcode_frame = ctk.CTkFrame(dialog)
        barcode_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            barcode_frame,
            text="Barcode:",
            font=label_font
        ).pack(side="left", padx=10)
        barcode_entry = ctk.CTkEntry(
            barcode_frame,
            width=entry_width,
            height=entry_height,
            font=form_font
        )
        barcode_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        def generate_internal_id():
            """Generate a unique internal ID for products without barcode"""
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            return f"INT{timestamp}{random_suffix}"
        
        def update_barcode_field(*args):
            if type_var.get() == "no_barcode":
                barcode_entry.configure(state="disabled")
                barcode_entry.delete(0, "end")
                barcode_entry.insert(0, generate_internal_id())
            else:
                barcode_entry.configure(state="normal")
                barcode_entry.delete(0, "end")
        
        type_var.trace("w", update_barcode_field)
        update_barcode_field()
        
        # Name
        ctk.CTkLabel(
            dialog,
            text="Product Name:",
            font=label_font
        ).pack(pady=10)
        name_entry = ctk.CTkEntry(
            dialog,
            width=entry_width,
            height=entry_height,
            font=form_font
        )
        name_entry.pack(pady=10)
        
        # Price
        ctk.CTkLabel(
            dialog,
            text="Price (UGX):",
            font=label_font
        ).pack(pady=10)
        price_entry = ctk.CTkEntry(
            dialog,
            width=entry_width,
            height=entry_height,
            font=form_font
        )
        price_entry.pack(pady=10)
        
        # Stock
        ctk.CTkLabel(
            dialog,
            text="Initial Stock:",
            font=label_font
        ).pack(pady=10)
        stock_entry = ctk.CTkEntry(
            dialog,
            width=entry_width,
            height=entry_height,
            font=form_font
        )
        stock_entry.pack(pady=10)
        
        def add_product():
            try:
                # Get values
                product_type = type_var.get()
                name = name_entry.get().strip()
                price = float(price_entry.get().strip())
                stock = int(stock_entry.get().strip())
                
                # Validate inputs
                if not name:
                    messagebox.showerror("Error", "Please enter product name!")
                    return
                    
                if price <= 0:
                    messagebox.showerror("Error", "Price must be greater than 0!")
                    return
                    
                if stock < 0:
                    messagebox.showerror("Error", "Stock cannot be negative!")
                    return
                    
                # Handle barcode
                if product_type == "barcode":
                    barcode = barcode_entry.get().strip()
                    if not barcode:
                        messagebox.showerror("Error", "Please enter barcode!")
                        return
                else:
                    barcode = generate_internal_id()
                
                # Check if barcode already exists
                if barcode in self.products:
                    if not messagebox.askyesno("Warning", "Product with this barcode already exists. Update it?"):
                        return
                
                # Add/update product with consistent structure
                self.products[barcode] = {
                    "barcode": barcode,  # Always include barcode
                    "name": name,
                    "price": price,
                    "stock": stock,
                    "type": product_type
                }
                
                # Save products
                self.save_products()
                
                # Show success message
                messagebox.showinfo("Success", f"Product {name} added successfully!")
                
                # Close dialog
                dialog.destroy()
                
                # Update the display
                self.update_spreadsheet()
                
            except ValueError as e:
                messagebox.showerror("Error", "Please enter valid numbers for price and stock!")
            except Exception as e:
                logging.error(f"Error adding product: {e}")
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        # Add button with increased size
        add_btn = ctk.CTkButton(
            dialog,
            text="Add Product",
            command=add_product,
            width=300,  # Wider button
            height=60,  # Taller button
            font=("Arial", 20, "bold")  # Larger font
        )
        add_btn.pack(pady=30)
        
        # Bind Enter key to add product
        def on_enter(event):
            add_product()
            
        name_entry.bind("<Return>", on_enter)
        price_entry.bind("<Return>", on_enter)
        stock_entry.bind("<Return>", on_enter)
        
        # Focus first entry
        name_entry.focus()
        
    def add_to_cart(self, product):
        try:
            # Extract product details
            barcode = product.get("barcode")
            if not barcode:
                # Try to find barcode from products dictionary
                for b, p in self.products.items():
                    if p == product:
                        barcode = b
                        break
                if not barcode:
                    logging.error("Could not find barcode for product")
                    return
                    
            name = product["name"]
            price = product["price"]
            
            # Check if the product already exists in the cart
            for item in self.cart:
                if item["barcode"] == barcode:
                    item["quantity"] += 1
                    self.update_spreadsheet()
                    self.update_totals()
                    return
            
            # If the product is not in the cart, add it
            self.cart.append({
                "barcode": barcode,
                "name": name,
                "price": price,
                "quantity": 1
            })
            self.update_spreadsheet()
            self.update_totals()
            
        except Exception as e:
            logging.error(f"Error adding to cart: {e}")
            messagebox.showerror("Error", "Failed to add item to cart")

    def update_spreadsheet(self):
        # Update products sheet
        self.products_sheet.set_sheet_data([])
        for barcode, product in self.products.items():
            self.products_sheet.insert_row([
                barcode,
                product["name"],
                f"UGX {product['price']:,.0f}",
                product.get("stock", 0)
            ])
            
        # Update cart sheet
        self.cart_sheet.set_sheet_data([])
        for item in self.cart:
            self.cart_sheet.insert_row([
                    item["barcode"],
                    item["name"],
                    f"UGX {item['price']:,.0f}",
                    item["quantity"],
                    f"UGX {item['price'] * item['quantity']:,.0f}"
            ])
            
        # Update totals
        self.update_totals()
        
    def update_totals(self, event=None):
        """Update total, discount, and change calculations with robust logic"""
        try:
            # Calculate subtotal
            subtotal = sum(item["price"] * item["quantity"] for item in self.cart)
            
            # Get discount
            discount_text = self.discount_entry.get().strip()
            try:
                discount = float(discount_text) if discount_text else 0
            except ValueError:
                messagebox.showerror("Error", "Invalid discount amount!")
                self.discount_entry.delete(0, "end")
                discount = 0
            
            # Clamp discount to not exceed subtotal
            if discount > subtotal:
                discount = subtotal
                self.discount_entry.delete(0, "end")
                self.discount_entry.insert(0, str(int(subtotal)))
            
            # Calculate total after discount
            total = subtotal - discount
            if total < 0:
                total = 0
            
            # Get payment
            payment_text = self.payment_entry.get().strip()
            try:
                payment = float(payment_text) if payment_text else 0
            except ValueError:
                messagebox.showerror("Error", "Invalid payment amount!")
                self.payment_entry.delete(0, "end")
                payment = 0
            
            # Calculate change or amount due
            if payment >= total:
                change = payment - total
                self.change_label.configure(text=f"Change: UGX {change:,.0f}")
            else:
                amount_due = total - payment
                self.change_label.configure(text=f"Amount Due: UGX {amount_due:,.0f}")
            
            # Update labels
            self.total_label.configure(text=f"Total: UGX {total:,.0f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Calculation error: {e}")
        
    def show_inventory(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Inventory Management")
        dialog.geometry("800x600")
        
        # Create inventory sheet
        inventory_sheet = Sheet(dialog)
        inventory_sheet.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Set up headers
        headers = ["Barcode", "Product Name", "Price", "Stock"]
        inventory_sheet.headers(headers)
        
        # Add products to sheet
        for barcode, product in self.products.items():
            inventory_sheet.insert_row([
                    barcode,
                    product["name"],
                    f"UGX {product['price']:,.0f}",
                    product.get("stock", 0)
            ])
            
        # Add control buttons
        control_frame = ctk.CTkFrame(dialog)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(
            control_frame,
            text="Update Stock",
            command=lambda: self.update_stock(inventory_sheet)
        ).pack(side="left", padx=5)
        
    def show_sales_history(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Sales History")
        dialog.geometry("800x600")
        
        # Create sales history sheet
        history_sheet = Sheet(dialog)
        history_sheet.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Set up headers
        headers = ["Date", "Items", "Total"]
        history_sheet.headers(headers)
        
        # Add sales to sheet
        for sale in self.sales_history:
            history_sheet.insert_row([
                    sale["date"],
                    len(sale["items"]),
                    f"UGX {sale['total']:,.0f}"
            ])
            
    def show_dashboard(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Dashboard")
        dialog.geometry("600x400")
        
        # Calculate statistics
        total_sales = sum(sale["total"] for sale in self.sales_history)
        total_items = sum(len(sale["items"]) for sale in self.sales_history)
        avg_sale = total_sales / len(self.sales_history) if self.sales_history else 0
        
        # Create statistics labels
        stats_frame = ctk.CTkFrame(dialog)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text=f"Total Sales: UGX {total_sales:,.0f}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text=f"Total Items Sold: {total_items}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text=f"Average Sale: UGX {avg_sale:,.0f}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
    def show_settings(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Settings")
        dialog.geometry("400x500")
        
        # Theme selection
        ctk.CTkLabel(dialog, text="Theme:").pack(pady=5)
        theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        theme_frame = ctk.CTkFrame(dialog)
        theme_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkRadioButton(
            theme_frame,
            text="Dark",
            variable=theme_var,
            value="dark"
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            theme_frame,
            text="Light",
            variable=theme_var,
            value="light"
        ).pack(side="left", padx=5)
        
        # Printing method selection
        ctk.CTkLabel(dialog, text="Receipt Printing Method:").pack(pady=5)
        print_method_var = tk.StringVar(value=self.settings.get("print_method", "windows"))
        print_method_frame = ctk.CTkFrame(dialog)
        print_method_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkRadioButton(
            print_method_frame,
            text="Windows/USB",
            variable=print_method_var,
            value="windows"
        ).pack(side="left", padx=5)
        ctk.CTkRadioButton(
            print_method_frame,
            text="ESC/POS",
            variable=print_method_var,
            value="escpos"
        ).pack(side="left", padx=5)
        
        # ESC/POS printer settings
        escpos_frame = ctk.CTkFrame(dialog)
        escpos_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(escpos_frame, text="Printer Model:").pack(anchor="w", padx=5)
        printer_model_entry = ctk.CTkEntry(escpos_frame)
        printer_model_entry.pack(fill="x", padx=5, pady=2)
        printer_model_entry.insert(0, self.settings.get("escpos_model", ""))
        ctk.CTkLabel(escpos_frame, text="Connection Type (usb/network/serial):").pack(anchor="w", padx=5)
        conn_type_entry = ctk.CTkEntry(escpos_frame)
        conn_type_entry.pack(fill="x", padx=5, pady=2)
        conn_type_entry.insert(0, self.settings.get("escpos_conn_type", "usb"))
        ctk.CTkLabel(escpos_frame, text="Connection Details (e.g. USB: vendor_id,product_id | Network: ip,port | Serial: port,baudrate):").pack(anchor="w", padx=5)
        conn_details_entry = ctk.CTkEntry(escpos_frame)
        conn_details_entry.pack(fill="x", padx=5, pady=2)
        conn_details_entry.insert(0, self.settings.get("escpos_conn_details", ""))
        
        def save_settings():
            self.settings["theme"] = theme_var.get()
            ctk.set_appearance_mode(self.settings["theme"])
            self.settings["print_method"] = print_method_var.get()
            self.settings["escpos_model"] = printer_model_entry.get().strip()
            self.settings["escpos_conn_type"] = conn_type_entry.get().strip()
            self.settings["escpos_conn_details"] = conn_details_entry.get().strip()
            self.save_settings()
            dialog.destroy()
            
        ctk.CTkButton(
            dialog,
            text="Save",
            command=save_settings
        ).pack(pady=20)
        
    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                return json.load(f)
        return {"theme": "dark"}
        
    def save_settings(self):
        with open("settings.json", "w") as f:
            json.dump(self.settings, f)
            
    def update_stock(self, sheet):
        try:
            # Update product stock levels
            for row in range(sheet.get_total_rows()):
                barcode = sheet.get_cell_data(row, 0)
                stock = int(sheet.get_cell_data(row, 3))
                if barcode in self.products:
                    self.products[barcode]["stock"] = stock
                    
            self.save_products()
            messagebox.showinfo("Success", "Stock updated successfully!")
        except ValueError:
            messagebox.showerror("Error", "Invalid stock value!")
        
    def load_sales_history(self):
        if os.path.exists("sales_history.json"):
            with open("sales_history.json", "r") as f:
                return json.load(f)
        return []
        
    def save_sales_history(self):
        with open("sales_history.json", "w") as f:
            json.dump(self.sales_history, f)
            
    def print_receipt(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty!")
            return
            
        # Get payment and discount
        try:
            payment = float(self.payment_entry.get().strip() or 0)
            discount = float(self.discount_entry.get().strip() or 0)
        except ValueError:
            messagebox.showerror("Error", "Invalid payment or discount amount!")
            return
            
        # Calculate total
        subtotal = sum(item["price"] * item["quantity"] for item in self.cart)
        total = subtotal - discount
        change = payment - total
        
        if payment < total:
            messagebox.showerror("Error", "Payment amount is less than total!")
            return
            
        # Save to sales history
        self.sales_history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": self.cart.copy(),
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
            "payment": payment,
            "change": change
        })
        self.save_sales_history()
        
        # Print using selected method
        print_method = self.settings.get("print_method", "windows")
        if print_method == "escpos":
            # ESC/POS printing
            try:
                try:
                    from escpos.printer import Usb, Network, Serial
                except ImportError:
                    messagebox.showerror("ESC/POS Library Missing", "ESC/POS printing requires the 'python-escpos' library. Please install it using:\n\npip install python-escpos\n\nThen try again.")
                    return
                conn_type = self.settings.get("escpos_conn_type", "usb").lower()
                conn_details = self.settings.get("escpos_conn_details", "")
                p = None
                if conn_type == "usb":
                    # Example: "0x04b8,0x0e15"
                    vendor_id, product_id = [int(x, 16) for x in conn_details.split(",")[:2]]
                    p = Usb(vendor_id, product_id)
                elif conn_type == "network":
                    # Example: "192.168.1.100,9100"
                    ip, port = conn_details.split(",")[:2]
                    p = Network(ip, int(port))
                elif conn_type == "serial":
                    # Example: "COM3,9600"
                    port, baudrate = conn_details.split(",")[:2]
                    p = Serial(port, baudrate=int(baudrate))
                else:
                    raise Exception("Unknown ESC/POS connection type")
                # Print simple text receipt
                p.text("POS SYSTEM RECEIPT\n")
                p.text(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                p.text("-----------------------------\n")
                for item in self.cart:
                    p.text(f"{item['name']} x{item['quantity']}\tUGX {item['price'] * item['quantity']:,}\n")
                p.text("-----------------------------\n")
                p.text(f"Subtotal: UGX {subtotal:,}\n")
                p.text(f"Discount: UGX {discount:,}\n")
                p.text(f"Total: UGX {total:,}\n")
                p.text(f"Payment: UGX {payment:,}\n")
                p.text(f"Change: UGX {change:,}\n")
                p.cut()
                messagebox.showinfo("Success", "Receipt sent to ESC/POS printer!")
            except Exception as e:
                messagebox.showerror("Error", f"ESC/POS printing failed: {e}\nMake sure you have python-escpos installed and correct printer details.")
        else:
            # Windows/USB printing (PDF)
            # Create PDF receipt
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            receipts_dir = os.path.join(desktop_path, "POS_Receipts")
            if not os.path.exists(receipts_dir):
                os.makedirs(receipts_dir)
            filename = os.path.join(receipts_dir, f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            c = canvas.Canvas(filename, pagesize=letter)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, 750, "POS SYSTEM RECEIPT")
            c.drawString(50, 730, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            y = 680
            c.setFont("Helvetica", 12)
            for item in self.cart:
                c.drawString(50, y, f"{item['name']} x{item['quantity']}")
                c.drawString(400, y, f"UGX {item['price'] * item['quantity']:,}\n")
                y -= 20
            y -= 20
            c.drawString(50, y, f"Subtotal: UGX {subtotal:,.0f}")
            y -= 20
            c.drawString(50, y, f"Discount: UGX {discount:,.0f}")
            y -= 20
            c.drawString(50, y, f"Total: UGX {total:,.0f}")
            y -= 20
            c.drawString(50, y, f"Payment: UGX {payment:,.0f}")
            y -= 20
            c.drawString(50, y, f"Change: UGX {change:,.0f}")
            c.save()
            try:
                import platform
                if platform.system() == "Windows":
                    os.startfile(filename, "print")
            except Exception as e:
                messagebox.showerror("Error", f"Could not send receipt to printer: {e}")
            messagebox.showinfo("Success", f"Receipt saved as {filename}")
        
        # Clear cart and entries
        self.cart = []
        self.discount_entry.delete(0, "end")
        self.payment_entry.delete(0, "end")
        self.update_spreadsheet()
        
    def backup_data(self):
        try:
            # Create backup directory on desktop
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            backup_dir = os.path.join(desktop_path, "POS_System_Backups")
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            # Create backup with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_path)
            
            # Copy all data files
            files_to_backup = ["products.json", "sales_history.json", "settings.json", "users.json"]
            for file in files_to_backup:
                if os.path.exists(file):
                    shutil.copy2(file, backup_path)
                    
            messagebox.showinfo("Success", f"Backup created in {backup_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {str(e)}")
            
    def restore_data(self):
        try:
            # Show backup selection dialog
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            backup_dir = os.path.join(desktop_path, "POS_System_Backups")
            
            if not os.path.exists(backup_dir):
                messagebox.showerror("Error", "No backup directory found on desktop!")
                return
                
            backup_path = filedialog.askdirectory(
                title="Select Backup Directory",
                initialdir=backup_dir
            )
            
            if not backup_path:
                return
                
            # Restore files
            files_to_restore = ["products.json", "sales_history.json", "settings.json", "users.json"]
            for file in files_to_restore:
                backup_file = os.path.join(backup_path, file)
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, ".")
                    
            # Reload data
            self.products = self.load_products()
            self.sales_history = self.load_sales_history()
            self.settings = self.load_settings()
            self.user_roles = self.load_user_roles()
            
            messagebox.showinfo("Success", "Data restored successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Restore failed: {str(e)}")
            
    def remove_from_cart(self, row):
        if 0 <= row < len(self.cart):
            # Restore stock
            item = self.cart[row]
            if item["barcode"] in self.products:
                self.products[item["barcode"]]["stock"] += item["quantity"]
                self.save_products()
                
            del self.cart[row]
            self.update_spreadsheet()
            
    def logout(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to logout?"):
            self.window.destroy()
            self.__init__()  # Restart the application
            
    def show_user_management(self):
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("User Management")
        dialog.geometry("600x400")
        dialog.transient(self.window)
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create form frame
        form_frame = ctk.CTkFrame(main_frame)
        form_frame.pack(fill="x", padx=10, pady=10)
        
        # Username field
        username_frame = ctk.CTkFrame(form_frame)
        username_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(username_frame, text="Username:").pack(side="left", padx=5)
        username_entry = ctk.CTkEntry(username_frame)
        username_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Password field
        password_frame = ctk.CTkFrame(form_frame)
        password_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(password_frame, text="Password:").pack(side="left", padx=5)
        password_entry = ctk.CTkEntry(password_frame, show="•")
        password_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Role selection
        role_frame = ctk.CTkFrame(form_frame)
        role_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(role_frame, text="Role:").pack(side="left", padx=5)
        role_var = ctk.StringVar(value="cashier")
        role_menu = ctk.CTkOptionMenu(
            role_frame,
            values=["admin", "manager", "cashier"],
            variable=role_var
        )
        role_menu.pack(side="left", padx=5, fill="x", expand=True)
        
        def add_user():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            role = role_var.get()
            
            if not username or not password:
                messagebox.showerror("Error", "Please fill in all fields!")
                return
                
            if username in self.user_roles:
                messagebox.showerror("Error", "Username already exists!")
                return
                
            # Add new user
            self.user_roles[username] = {
                "password": self.hash_password(password),
                "role": role,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_login": None
            }
            
            # Save changes
            self.save_user_roles()
            
            # Update user list
            update_user_list()
            
            # Clear fields
            username_entry.delete(0, "end")
            password_entry.delete(0, "end")
            role_var.set("cashier")
            
            messagebox.showinfo("Success", f"User {username} added successfully!")
        
        # Add user button
        add_btn = ctk.CTkButton(
            form_frame,
            text="Add User",
            command=add_user
        )
        add_btn.pack(pady=10)
        
        # User list frame
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create user list
        columns = ("Username", "Role", "Created", "Last Login")
        user_list = Sheet(list_frame)
        user_list.enable_bindings()
        user_list.headers(columns)
        user_list.pack(fill="both", expand=True)
        
        def update_user_list():
            data = []
            for username, info in self.user_roles.items():
                data.append([
                    username,
                    info["role"],
                    info.get("created_at", "N/A"),
                    info.get("last_login", "Never")
                ])
            user_list.set_sheet_data(data)
            user_list.set_column_widths([150, 100, 150, 150])
        
        def delete_user():
            selected = user_list.get_selected_cells()
            if not selected:
                messagebox.showerror("Error", "Please select a user to delete!")
                return
                
            username = user_list.get_cell_data(selected[0][0], 0)
            if username == "admin":
                messagebox.showerror("Error", "Cannot delete admin user!")
                return
                
            if messagebox.askyesno("Confirm", f"Delete user {username}?"):
                del self.user_roles[username]
                self.save_user_roles()
                update_user_list()
                messagebox.showinfo("Success", f"User {username} deleted successfully!")
        
        # Delete user button
        delete_btn = ctk.CTkButton(
            list_frame,
            text="Delete Selected User",
            command=delete_user,
            fg_color="red",
            hover_color="darkred"
        )
        delete_btn.pack(pady=10)
        
        # Initial user list update
        update_user_list()
        
    def show_todays_sales(self):
        """Show today's sales for staff members"""
        dialog = ctk.CTkToplevel(self.window)
        dialog.title("Today's Sales")
        dialog.geometry("800x600")
        
        # Create sales history sheet
        history_sheet = Sheet(dialog)
        history_sheet.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Set up headers
        headers = ["Time", "Items", "Total"]
        history_sheet.headers(headers)
        
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Add today's sales to sheet
        for sale in self.sales_history:
            if sale["date"].startswith(today):
                history_sheet.insert_row([
                        sale["date"].split()[1],  # Time only
                        len(sale["items"]),
                        f"UGX {sale['total']:,.0f}"
                ])
                
        # Calculate today's total
        today_total = sum(
            sale["total"] for sale in self.sales_history
            if sale["date"].startswith(today)
        )
        
        # Add total at the bottom
        total_frame = ctk.CTkFrame(dialog)
        total_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            total_frame,
            text=f"Today's Total: UGX {today_total:,.0f}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)
        
    def clear_search(self):
        """Clear search and restore original view"""
        self.search_entry.delete(0, "end")
        self.min_price_entry.delete(0, "end")
        self.max_price_entry.delete(0, "end")
        self.update_spreadsheet()
        
    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    try:
        logging.info("Starting POS System...")
        pos = POSSystem()
        pos.run()
    except Exception as e:
        error_msg = f"An error occurred: {str(e)}\n\n{traceback.format_exc()}"
        logging.error(error_msg)
        show_error_and_exit(error_msg) 