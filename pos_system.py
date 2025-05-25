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
            
            # Schedule next frame
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
        right_bar = ctk.CTkFrame(main_layout, width=220)
        right_bar.pack(side="right", fill="y")

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
                ("Add Product", self.add_product_dialog),
                ("Scan Barcode", self.scan_barcode),
                ("Print Receipt", self.print_receipt),
            ]
        for text, cmd in nav_buttons:
            ctk.CTkButton(left_bar, text=text, command=cmd, width=button_width, height=button_height, font=button_font).pack(pady=6)
        # Logout always at the bottom
        ctk.CTkButton(left_bar, text="Logout", command=self.logout, width=button_width, height=button_height, font=button_font, fg_color="red").pack(side="bottom", pady=12)

        # --- Center: Spreadsheet/Cart ---
        self.sheet = Sheet(center_frame, row_height=36)
        self.sheet.pack(fill="both", expand=True, padx=10, pady=10)
        headers = ["Barcode", "Product", "Price", "Quantity", "Total"]
        self.sheet.headers(headers)
        self.sheet.enable_bindings()
        self.sheet.bind("<Double-Button-1>", self.edit_cell)
        self.sheet.set_column_widths([160, 320, 160, 120, 160])

        # --- Right Bar: Payment Controls (retail size) ---
        print('Creating right bar widgets...')
        print('Adding Discount label')
        ctk.CTkLabel(right_bar, text="Discount:", font=("Arial", 22, "bold")).pack(pady=(30, 8))
        print('Adding Discount entry')
        self.discount_entry = ctk.CTkEntry(right_bar, width=220, height=60, font=("Arial", 22))
        self.discount_entry.pack(pady=8)
        self.discount_entry.bind("<KeyRelease>", self.update_totals)

        print('Adding Payment label')
        ctk.CTkLabel(right_bar, text="Payment:", font=("Arial", 22, "bold")).pack(pady=(30, 8))
        print('Adding Payment entry')
        self.payment_entry = ctk.CTkEntry(right_bar, width=220, height=60, font=("Arial", 22))
        self.payment_entry.pack(pady=8)
        self.payment_entry.bind("<KeyRelease>", self.update_totals)

        print('Adding Total label')
        self.total_label = ctk.CTkLabel(right_bar, text="Total: UGX 0", font=("Arial", 28, "bold"))
        self.total_label.pack(pady=(30, 12))
        print('Adding Change label')
        self.change_label = ctk.CTkLabel(right_bar, text="Change: UGX 0", font=("Arial", 28, "bold"))
        self.change_label.pack(pady=12)

        print('Adding Print Receipt button')
        ctk.CTkButton(right_bar, text="Print Receipt", command=self.print_receipt, width=220, height=70, font=("Arial", 22, "bold")).pack(pady=(40, 16))
        print('Finished creating right bar widgets')

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
        
    def search_products(self, event=None):
        search_term = self.search_entry.get().lower()
        if not search_term:
            self.update_spreadsheet()
            return
            
        filtered_cart = [
            item for item in self.cart
            if search_term in item["name"].lower() or search_term in item["barcode"]
        ]
        
        # Clear and update spreadsheet with filtered items
        self.sheet.set_sheet_data([])
        for item in filtered_cart:
            self.sheet.insert_row(
                values=[
                    item["barcode"],
                    item["name"],
                    f"UGX {item['price']:,.0f}",
                    item["quantity"],
                    f"UGX {item['price'] * item['quantity']:,.0f}"
                ]
            )
            
    def edit_cell(self, event):
        # Get the clicked cell
        clicked_box = self.sheet.identify_region(event.x, event.y)
        if clicked_box == "cells":
            row = self.sheet.identify_row(event.y)
            col = self.sheet.identify_column(event.x)
            
            # Only allow editing quantity column
            if col == 3:  # Quantity column
                current_value = self.sheet.get_cell_data(row, col)
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
        dialog.title("Enter Barcode")
        dialog.geometry("300x150")
        
        ctk.CTkLabel(dialog, text="Enter barcode:").pack(pady=5)
        barcode_entry = ctk.CTkEntry(dialog)
        barcode_entry.pack(pady=5)
        barcode_entry.focus()
        
        def process_barcode():
            barcode = barcode_entry.get()
            if barcode in self.products:
                product = self.products[barcode]
                self.add_to_cart(barcode, product)
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Product not found!")
                
        barcode_entry.bind("<Return>", lambda e: process_barcode())
        ctk.CTkButton(dialog, text="Add", command=process_barcode).pack(pady=10)
        
    def load_products(self):
        # Load products from JSON file or create default products
        if os.path.exists("products.json"):
            with open("products.json", "r") as f:
                return json.load(f)
        return {
            "123456789": {"name": "Sample Product", "price": 9.99}
        }
        
    def save_products(self):
        with open("products.json", "w") as f:
            json.dump(self.products, f)
            
    def add_product_dialog(self):
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
        
        # Barcode
        ctk.CTkLabel(
            dialog,
            text="Barcode:",
            font=label_font
        ).pack(pady=10)
        barcode_entry = ctk.CTkEntry(
            dialog,
            width=entry_width,
            height=entry_height,
            font=form_font
        )
        barcode_entry.pack(pady=10)
        
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
                barcode = barcode_entry.get().strip()
                name = name_entry.get().strip()
                price = float(price_entry.get().strip())
                stock = int(stock_entry.get().strip())
                
                # Validate inputs
                if not barcode or not name:
                    messagebox.showerror("Error", "Please fill in all fields!")
                    return
                    
                if price <= 0:
                    messagebox.showerror("Error", "Price must be greater than 0!")
                    return
                    
                if stock < 0:
                    messagebox.showerror("Error", "Stock cannot be negative!")
                    return
                    
                # Check if barcode already exists
                if barcode in self.products:
                    if not messagebox.askyesno("Warning", "Product with this barcode already exists. Update it?"):
                        return
                
                # Add/update product
                self.products[barcode] = {
                    "name": name,
                    "price": price,
                    "stock": stock
                }
                
                # Save products
                self.save_products()
                
                # Show success message
                messagebox.showinfo("Success", f"Product {name} added successfully!")
                
                # Close dialog
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Error", "Please enter valid numbers for price and stock!")
            except Exception as e:
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
            
        barcode_entry.bind("<Return>", on_enter)
        name_entry.bind("<Return>", on_enter)
        price_entry.bind("<Return>", on_enter)
        stock_entry.bind("<Return>", on_enter)
        
        # Focus first entry
        barcode_entry.focus()
        
    def add_to_cart(self, barcode, product):
        # Check stock
        if product.get("stock", 0) <= 0:
            messagebox.showerror("Error", "Product out of stock!")
            return
            
        # Add product to cart and update spreadsheet
        self.cart.append({
            "barcode": barcode,
            "name": product["name"],
            "price": product["price"],
            "quantity": 1
        })
        
        # Update stock
        self.products[barcode]["stock"] -= 1
        self.save_products()
        
        self.update_spreadsheet()
        
    def update_spreadsheet(self):
        # Clear current data
        self.sheet.set_sheet_data([])
        
        # Add cart items to spreadsheet
        for i, item in enumerate(self.cart):
            self.sheet.insert_row(
                values=[
                    item["barcode"],
                    item["name"],
                    f"UGX {item['price']:,.0f}",
                    item["quantity"],
                    f"UGX {item['price'] * item['quantity']:,.0f}"
                ]
            )
            
            # Add remove button
            self.sheet.create_text(
                x=600,
                y=i * 30 + 30,
                text="❌",
                font=("Arial", 14),
                fill="red",
                tags=f"remove_{i}",
                command=lambda row=i: self.remove_from_cart(row)
            )
            
        # Update totals
        self.update_totals()
        
    def update_totals(self, event=None):
        """Update total, discount, and change calculations"""
        try:
            # Calculate subtotal
            subtotal = sum(item["price"] * item["quantity"] for item in self.cart)
            
            # Get discount
            discount_text = self.discount_entry.get().strip()
            discount = float(discount_text) if discount_text else 0
            
            # Calculate total after discount
            total = subtotal - discount
            
            # Get payment
            payment_text = self.payment_entry.get().strip()
            payment = float(payment_text) if payment_text else 0
            
            # Calculate change
            change = payment - total if payment >= total else 0
            
            # Update labels
            self.total_label.configure(text=f"Total: UGX {total:,.0f}")
            self.change_label.configure(text=f"Change: UGX {change:,.0f}")
            
        except ValueError:
            # Handle invalid input
            pass
        
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
            inventory_sheet.insert_row(
                values=[
                    barcode,
                    product["name"],
                    f"UGX {product['price']:,.0f}",
                    product.get("stock", 0)
                ]
            )
            
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
            history_sheet.insert_row(
                values=[
                    sale["date"],
                    len(sale["items"]),
                    f"UGX {sale['total']:,.0f}"
                ]
            )
            
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
        dialog.geometry("400x300")
        
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
        
        def save_settings():
            self.settings["theme"] = theme_var.get()
            ctk.set_appearance_mode(self.settings["theme"])
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
            
        # Create PDF receipt
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        receipts_dir = os.path.join(desktop_path, "POS_Receipts")
        if not os.path.exists(receipts_dir):
            os.makedirs(receipts_dir)
            
        filename = os.path.join(receipts_dir, f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        c = canvas.Canvas(filename, pagesize=letter)
        
        # Add header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, "POS SYSTEM RECEIPT")
        c.drawString(50, 730, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Add items
        y = 680
        c.setFont("Helvetica", 12)
        for item in self.cart:
            c.drawString(50, y, f"{item['name']} x{item['quantity']}")
            c.drawString(400, y, f"UGX {item['price'] * item['quantity']:,.0f}")
            y -= 20
            
        # Add totals
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
        
        # Clear cart and entries
        self.cart = []
        self.discount_entry.delete(0, "end")
        self.payment_entry.delete(0, "end")
        self.update_spreadsheet()
        
        messagebox.showinfo("Success", f"Receipt saved as {filename}")
        
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
                history_sheet.insert_row(
                    values=[
                        sale["date"].split()[1],  # Time only
                        len(sale["items"]),
                        f"UGX {sale['total']:,.0f}"
                    ]
                )
                
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