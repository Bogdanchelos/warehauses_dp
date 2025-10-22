import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QWidget, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QMessageBox,
                             QDialog, QFormLayout, QDoubleSpinBox, QHeaderView,
                             QTabWidget, QDateEdit, QSpinBox, QComboBox,
                             QTextEdit)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtGui import QTextDocument
import sqlite3
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.db_name = "warehouse.db"
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица товаров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                purchase_price REAL DEFAULT 0,
                retail_price REAL DEFAULT 0,
                supplier TEXT,
                category TEXT,
                min_stock INTEGER DEFAULT 0,
                current_stock INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица поставщиков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица поступлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_number TEXT NOT NULL,
                supplier_id INTEGER,
                receipt_date DATE NOT NULL,
                total_amount REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        ''')
        
        # Таблица строк поступлений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (receipt_id) REFERENCES receipts (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Таблица продаж (накладные)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_number TEXT NOT NULL,
                client_name TEXT NOT NULL,
                client_address TEXT,
                sale_date DATE NOT NULL,
                total_amount REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица строк продаж
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES sales (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        # Таблица резервов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                reservation_date DATE NOT NULL,
                expiry_date DATE NOT NULL,
                status TEXT DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()

class SupplierDialog(QDialog):
    def __init__(self, parent=None, supplier_data=None):
        super().__init__(parent)
        self.supplier_data = supplier_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Додати постачальника" if not self.supplier_data else "Редагувати постачальника")
        self.setFixedSize(500, 400)
        
        layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.contact_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.address_input = QLineEdit()
        
        layout.addRow("Назва*:", self.name_input)
        layout.addRow("Контактна особа:", self.contact_input)
        layout.addRow("Телефон:", self.phone_input)
        layout.addRow("Email:", self.email_input)
        layout.addRow("Адреса:", self.address_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Зберегти")
        self.cancel_btn = QPushButton("Скасувати")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
        
        # Заполнение данных если редактирование
        if self.supplier_data:
            self.fill_data()
            
        # Подключение сигналов
        self.save_btn.clicked.connect(self.save_supplier)
        self.cancel_btn.clicked.connect(self.reject)
    
    def fill_data(self):
        self.name_input.setText(self.supplier_data[1])
        self.contact_input.setText(self.supplier_data[2] or "")
        self.phone_input.setText(self.supplier_data[3] or "")
        self.email_input.setText(self.supplier_data[4] or "")
        self.address_input.setText(self.supplier_data[5] or "")
    
    def save_supplier(self):
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Помилка", "Назва постачальника обов'язкова!")
            return
            
        self.supplier_data = (
            name,
            self.contact_input.text(),
            self.phone_input.text(),
            self.email_input.text(),
            self.address_input.text()
        )
        self.accept()

class ReceiptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Надходження товарів")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Шапка документа
        header_layout = QFormLayout()
        
        self.doc_number_input = QLineEdit()
        self.doc_number_input.setText(f"ПН-{QDate.currentDate().toString('ddMMyyyy')}")
        
        self.supplier_combo = QComboBox()
        self.load_suppliers()
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        
        header_layout.addRow("Номер документу:", self.doc_number_input)
        header_layout.addRow("Постачальник:", self.supplier_combo)
        header_layout.addRow("Дата:", self.date_input)
        
        layout.addLayout(header_layout)
        
        # Таблица товаров
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Товар", "Кількість", "Ціна", "Сума", "Видалити"
        ])
        
        layout.addWidget(QLabel("Товари:"))
        layout.addWidget(self.items_table)
        
        # Кнопки для товаров
        item_buttons_layout = QHBoxLayout()
        self.add_item_btn = QPushButton("Додати товар")
        self.remove_item_btn = QPushButton("Видалити товар")
        
        item_buttons_layout.addWidget(self.add_item_btn)
        item_buttons_layout.addWidget(self.remove_item_btn)
        item_buttons_layout.addStretch()
        
        layout.addLayout(item_buttons_layout)
        
        # Итого
        self.total_label = QLabel("Разом: 0.00 грн")
        layout.addWidget(self.total_label)
        
        # Кнопки сохранения
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Провести надходження")
        self.cancel_btn = QPushButton("Скасувати")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.add_item_btn.clicked.connect(self.add_item_row)
        self.remove_item_btn.clicked.connect(self.remove_item_row)
        self.save_btn.clicked.connect(self.save_receipt)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Добавляем первую пустую строку
        self.add_item_row()
    
    def load_suppliers(self):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM suppliers ORDER BY name")
        suppliers = cursor.fetchall()
        conn.close()
        
        self.supplier_combo.clear()
        self.supplier_combo.addItem("-- Оберіть постачальника --", 0)
        for supplier in suppliers:
            self.supplier_combo.addItem(supplier[1], supplier[0])
    
    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Комбобокс товаров
        product_combo = QComboBox()
        self.load_products_to_combo(product_combo)
        
        quantity_input = QSpinBox()
        quantity_input.setMinimum(1)
        quantity_input.setMaximum(99999)
        
        price_input = QDoubleSpinBox()
        price_input.setMaximum(999999.99)
        
        total_label = QLabel("0.00")
        
        delete_btn = QPushButton("🗑️")
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        
        self.items_table.setCellWidget(row, 0, product_combo)
        self.items_table.setCellWidget(row, 1, quantity_input)
        self.items_table.setCellWidget(row, 2, price_input)
        self.items_table.setCellWidget(row, 3, total_label)
        self.items_table.setCellWidget(row, 4, delete_btn)
        
        # Подключаем сигналы для пересчета
        quantity_input.valueChanged.connect(self.calculate_totals)
        price_input.valueChanged.connect(self.calculate_totals)
    
    def load_products_to_combo(self, combo):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, article, name FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        combo.clear()
        combo.addItem("-- Оберіть товар --", 0)
        for product in products:
            combo.addItem(f"{product[1]} - {product[2]}", product[0])
    
    def delete_row(self, row):
        self.items_table.removeRow(row)
        self.calculate_totals()
    
    def remove_item_row(self):
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.items_table.removeRow(current_row)
            self.calculate_totals()
    
    def calculate_totals(self):
        total = 0.0
        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 1)
            price_widget = self.items_table.cellWidget(row, 2)
            total_label = self.items_table.cellWidget(row, 3)
            
            if quantity_widget and price_widget:
                quantity = quantity_widget.value()
                price = price_widget.value()
                row_total = quantity * price
                total_label.setText(f"{row_total:.2f}")
                total += row_total
        
        self.total_label.setText(f"Разом: {total:.2f} грн")
    
    def save_receipt(self):
        # Проверки
        if self.supplier_combo.currentData() == 0:
            QMessageBox.warning(self, "Помилка", "Оберіть постачальника!")
            return
        
        # Проверяем что есть товары
        has_items = False
        for row in range(self.items_table.rowCount()):
            product_combo = self.items_table.cellWidget(row, 0)
            if product_combo.currentData() != 0:
                has_items = True
                break
        
        if not has_items:
            QMessageBox.warning(self, "Помилка", "Додайте хоча б один товар!")
            return
        
        # Сохраняем в базу
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        try:
            # Создаем заголовок поступления
            cursor.execute('''
                INSERT INTO receipts (document_number, supplier_id, receipt_date, total_amount)
                VALUES (?, ?, ?, ?)
            ''', (
                self.doc_number_input.text(),
                self.supplier_combo.currentData(),
                self.date_input.date().toString('yyyy-MM-dd'),
                0  # Пока 0, посчитаем ниже
            ))
            
            receipt_id = cursor.lastrowid
            total_amount = 0.0
            
            # Сохраняем строки
            for row in range(self.items_table.rowCount()):
                product_combo = self.items_table.cellWidget(row, 0)
                quantity_widget = self.items_table.cellWidget(row, 1)
                price_widget = self.items_table.cellWidget(row, 2)
                
                if product_combo.currentData() != 0:
                    product_id = product_combo.currentData()
                    quantity = quantity_widget.value()
                    price = price_widget.value()
                    row_total = quantity * price
                    total_amount += row_total
                    
                    cursor.execute('''
                        INSERT INTO receipt_items (receipt_id, product_id, quantity, price, total)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (receipt_id, product_id, quantity, price, row_total))
                    
                    # Обновляем залишки товара
                    cursor.execute('''
                        UPDATE products SET current_stock = current_stock + ? 
                        WHERE id = ?
                    ''', (quantity, product_id))
            
            # Обновляем общую сумму
            cursor.execute('''
                UPDATE receipts SET total_amount = ? WHERE id = ?
            ''', (total_amount, receipt_id))
            
            conn.commit()
            QMessageBox.information(self, "Успіх", "Надходження успішно проведено!")
            self.accept()
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Помилка", f"Помилка при збереженні: {str(e)}")
        finally:
            conn.close()

class SaleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Створення накладної")
        self.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Шапка документа
        header_layout = QFormLayout()
        
        self.doc_number_input = QLineEdit()
        self.doc_number_input.setText(f"ВН-{QDate.currentDate().toString('ddMMyyyy')}")
        
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("ПІБ або назва клієнта")
        
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Адреса (не обов'язково)")
        
        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        
        header_layout.addRow("Номер накладної*:", self.doc_number_input)
        header_layout.addRow("Клієнт*:", self.client_input)
        header_layout.addRow("Адреса:", self.address_input)
        header_layout.addRow("Дата*:", self.date_input)
        
        layout.addLayout(header_layout)
        
        # Таблица товаров
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels([
            "Товар", "Кількість", "Наявно", "Ціна", "Сума", "Видалити"
        ])
        
        layout.addWidget(QLabel("Товари:"))
        layout.addWidget(self.items_table)
        
        # Кнопки для товаров
        item_buttons_layout = QHBoxLayout()
        self.add_item_btn = QPushButton("Додати товар")
        self.remove_item_btn = QPushButton("Видалити товар")
        
        item_buttons_layout.addWidget(self.add_item_btn)
        item_buttons_layout.addWidget(self.remove_item_btn)
        item_buttons_layout.addStretch()
        
        layout.addLayout(item_buttons_layout)
        
        # Итого
        self.total_label = QLabel("Разом: 0.00 грн")
        layout.addWidget(self.total_label)
        
        # Кнопки сохранения
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Провести накладну")
        self.print_btn = QPushButton("Друк")
        self.cancel_btn = QPushButton("Скасувати")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.print_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.add_item_btn.clicked.connect(self.add_item_row)
        self.remove_item_btn.clicked.connect(self.remove_item_row)
        self.save_btn.clicked.connect(self.save_sale)
        self.print_btn.clicked.connect(self.print_invoice)
        self.cancel_btn.clicked.connect(self.reject)
        
        # Добавляем первую пустую строку
        self.add_item_row()
    
    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Комбобокс товаров
        product_combo = QComboBox()
        self.load_products_to_combo(product_combo)
        
        quantity_input = QSpinBox()
        quantity_input.setMinimum(1)
        quantity_input.setMaximum(99999)
        
        available_label = QLabel("0")
        
        price_input = QDoubleSpinBox()
        price_input.setMaximum(999999.99)
        
        total_label = QLabel("0.00")
        
        delete_btn = QPushButton("🗑️")
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        
        self.items_table.setCellWidget(row, 0, product_combo)
        self.items_table.setCellWidget(row, 1, quantity_input)
        self.items_table.setCellWidget(row, 2, available_label)
        self.items_table.setCellWidget(row, 3, price_input)
        self.items_table.setCellWidget(row, 4, total_label)
        self.items_table.setCellWidget(row, 5, delete_btn)
        
        # Подключаем сигналы для пересчета
        product_combo.currentIndexChanged.connect(lambda: self.update_available_stock(row))
        quantity_input.valueChanged.connect(self.calculate_totals)
        price_input.valueChanged.connect(self.calculate_totals)
    
    def load_products_to_combo(self, combo):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, article, name, current_stock, retail_price FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        combo.clear()
        combo.addItem("-- Оберіть товар --", 0)
        for product in products:
            combo.addItem(f"{product[1]} - {product[2]} ({product[3]} шт.)", product[0])
            # Сохраняем цену и количество в userData
            combo.setItemData(combo.count()-1, product[3], Qt.UserRole)  # available stock
            combo.setItemData(combo.count()-1, product[4], Qt.UserRole+1)  # retail price
    
    def update_available_stock(self, row):
        product_combo = self.items_table.cellWidget(row, 0)
        available_label = self.items_table.cellWidget(row, 2)
        price_input = self.items_table.cellWidget(row, 3)
        
        if product_combo.currentData() != 0:
            available_stock = product_combo.currentData(Qt.UserRole) or 0
            retail_price = product_combo.currentData(Qt.UserRole+1) or 0
            
            available_label.setText(str(available_stock))
            price_input.setValue(retail_price)
        
        self.calculate_totals()
    
    def delete_row(self, row):
        self.items_table.removeRow(row)
        self.calculate_totals()
    
    def remove_item_row(self):
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.items_table.removeRow(current_row)
            self.calculate_totals()
    
    def calculate_totals(self):
        total = 0.0
        for row in range(self.items_table.rowCount()):
            quantity_widget = self.items_table.cellWidget(row, 1)
            price_widget = self.items_table.cellWidget(row, 3)
            total_label = self.items_table.cellWidget(row, 4)
            
            if quantity_widget and price_widget:
                quantity = quantity_widget.value()
                price = price_widget.value()
                row_total = quantity * price
                total_label.setText(f"{row_total:.2f}")
                total += row_total
        
        self.total_label.setText(f"Разом: {total:.2f} грн")
    
    def save_sale(self):
        # Проверки
        if not self.client_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть ім'я клієнта!")
            return
        
        # Проверяем что есть товары
        has_items = False
        for row in range(self.items_table.rowCount()):
            product_combo = self.items_table.cellWidget(row, 0)
            if product_combo.currentData() != 0:
                has_items = True
                break
        
        if not has_items:
            QMessageBox.warning(self, "Помилка", "Додайте хоча б один товар!")
            return
        
        # Проверяем доступность товаров
        for row in range(self.items_table.rowCount()):
            product_combo = self.items_table.cellWidget(row, 0)
            quantity_widget = self.items_table.cellWidget(row, 1)
            available_label = self.items_table.cellWidget(row, 2)
            
            if product_combo.currentData() != 0:
                requested = quantity_widget.value()
                available = int(available_label.text())
                if requested > available:
                    QMessageBox.warning(self, "Помилка", 
                                      f"Недостатньо товару на складі!\n"
                                      f"Запитується: {requested}, Наявно: {available}")
                    return
        
        # Сохраняем в базу
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        try:
            # Создаем заголовок продажи
            cursor.execute('''
                INSERT INTO sales (document_number, client_name, client_address, sale_date, total_amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.doc_number_input.text(),
                self.client_input.text().strip(),
                self.address_input.text(),
                self.date_input.date().toString('yyyy-MM-dd'),
                0  # Пока 0, посчитаем ниже
            ))
            
            sale_id = cursor.lastrowid
            total_amount = 0.0
            
            # Сохраняем строки
            for row in range(self.items_table.rowCount()):
                product_combo = self.items_table.cellWidget(row, 0)
                quantity_widget = self.items_table.cellWidget(row, 1)
                price_widget = self.items_table.cellWidget(row, 3)
                
                if product_combo.currentData() != 0:
                    product_id = product_combo.currentData()
                    quantity = quantity_widget.value()
                    price = price_widget.value()
                    row_total = quantity * price
                    total_amount += row_total
                    
                    cursor.execute('''
                        INSERT INTO sale_items (sale_id, product_id, quantity, price, total)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (sale_id, product_id, quantity, price, row_total))
                    
                    # Обновляем залишки товара
                    cursor.execute('''
                        UPDATE products SET current_stock = current_stock - ? 
                        WHERE id = ?
                    ''', (quantity, product_id))
            
            # Обновляем общую сумму
            cursor.execute('''
                UPDATE sales SET total_amount = ? WHERE id = ?
            ''', (total_amount, sale_id))
            
            conn.commit()
            QMessageBox.information(self, "Успіх", "Накладна успішно проведена!")
            self.accept()
            
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Помилка", f"Помилка при збереженні: {str(e)}")
        finally:
            conn.close()
    
    def print_invoice(self):
        # Создаем HTML для печати
        html_content = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .info {{ margin-bottom: 20px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .table th {{ background-color: #f2f2f2; }}
            .total {{ text-align: right; font-weight: bold; font-size: 16px; }}
        </style>
        </head>
        <body>
            <div class="header">
                <h2>ВИТРАТНА НАКЛАДНА</h2>
                <p>№ {self.doc_number_input.text()} від {self.date_input.date().toString('dd.MM.yyyy')}</p>
            </div>
            
            <div class="info">
                <p><strong>Клієнт:</strong> {self.client_input.text()}</p>
                <p><strong>Адреса:</strong> {self.address_input.text() or 'Не вказано'}</p>
            </div>
            
            <table class="table">
                <thead>
                    <tr>
                        <th>№</th>
                        <th>Товар</th>
                        <th>Кількість</th>
                        <th>Ціна</th>
                        <th>Сума</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        # Добавляем строки товаров
        total_amount = 0.0
        for row in range(self.items_table.rowCount()):
            product_combo = self.items_table.cellWidget(row, 0)
            quantity_widget = self.items_table.cellWidget(row, 1)
            price_widget = self.items_table.cellWidget(row, 3)
            
            if product_combo.currentData() != 0:
                product_name = product_combo.currentText().split(' - ')[1] if ' - ' in product_combo.currentText() else product_combo.currentText()
                quantity = quantity_widget.value()
                price = price_widget.value()
                row_total = quantity * price
                total_amount += row_total
                
                html_content += f"""
                    <tr>
                        <td>{row + 1}</td>
                        <td>{product_name}</td>
                        <td>{quantity}</td>
                        <td>{price:.2f}</td>
                        <td>{row_total:.2f}</td>
                    </tr>
                """
        
        html_content += f"""
                </tbody>
            </table>
            
            <div class="total">
                <p>Всього до сплати: {total_amount:.2f} грн</p>
            </div>
            
            <div style="margin-top: 50px;">
                <p>Відпустив: _________________</p>
                <p>Отримав: _________________</p>
            </div>
        </body>
        </html>
        """
        
        # Печать
        printer = QPrinter()
        print_dialog = QPrintDialog(printer, self)
        
        if print_dialog.exec_() == QPrintDialog.Accepted:
            document = QTextDocument()
            document.setHtml(html_content)
            document.print_(printer)

class ReservationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Резервування товару")
        self.setFixedSize(500, 400)
        
        layout = QFormLayout()
        
        self.client_input = QLineEdit()
        self.client_input.setPlaceholderText("ПІБ або назва клієнта")
        
        self.product_combo = QComboBox()
        self.load_products()
        
        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(99999)
        
        self.reservation_date = QDateEdit()
        self.reservation_date.setDate(QDate.currentDate())
        self.reservation_date.setCalendarPopup(True)
        
        self.expiry_date = QDateEdit()
        self.expiry_date.setDate(QDate.currentDate().addDays(7))
        self.expiry_date.setCalendarPopup(True)
        
        self.available_label = QLabel("0")
        
        layout.addRow("Клієнт*:", self.client_input)
        layout.addRow("Товар*:", self.product_combo)
        layout.addRow("Доступно:", self.available_label)
        layout.addRow("Кількість*:", self.quantity_input)
        layout.addRow("Дата резерву*:", self.reservation_date)
        layout.addRow("Дійсний до*:", self.expiry_date)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Зарезервувати")
        self.cancel_btn = QPushButton("Скасувати")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
        
        # Подключение сигналов
        self.product_combo.currentIndexChanged.connect(self.update_available_stock)
        self.save_btn.clicked.connect(self.save_reservation)
        self.cancel_btn.clicked.connect(self.reject)
    
    def load_products(self):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, article, name, current_stock FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        self.product_combo.clear()
        self.product_combo.addItem("-- Оберіть товар --", 0)
        for product in products:
            self.product_combo.addItem(f"{product[1]} - {product[2]}", product[0])
            self.product_combo.setItemData(self.product_combo.count()-1, product[3], Qt.UserRole)
    
    def update_available_stock(self):
        if self.product_combo.currentData() != 0:
            available_stock = self.product_combo.currentData(Qt.UserRole) or 0
            self.available_label.setText(str(available_stock))
    
    def save_reservation(self):
        if not self.client_input.text().strip():
            QMessageBox.warning(self, "Помилка", "Введіть ім'я клієнта!")
            return
        
        if self.product_combo.currentData() == 0:
            QMessageBox.warning(self, "Помилка", "Оберіть товар!")
            return
        
        available_stock = self.product_combo.currentData(Qt.UserRole) or 0
        requested = self.quantity_input.value()
        
        if requested > available_stock:
            QMessageBox.warning(self, "Помилка", 
                              f"Недостатньо товару на складі!\n"
                              f"Запитується: {requested}, Наявно: {available_stock}")
            return
        
        # Сохраняем в базу
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO reservations (client_name, product_id, quantity, reservation_date, expiry_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.client_input.text().strip(),
                self.product_combo.currentData(),
                requested,
                self.reservation_date.date().toString('yyyy-MM-dd'),
                self.expiry_date.date().toString('yyyy-MM-dd')
            ))
            
            conn.commit()
            QMessageBox.information(self, "Успіх", "Товар успішно зарезервовано!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Помилка", f"Помилка при збереженні: {str(e)}")
        finally:
            conn.close()

class ReportsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Звіти")
        self.setFixedSize(900, 700)
        
        layout = QVBoxLayout()
        
        # Период
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("З:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        
        period_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        
        self.generate_btn = QPushButton("Сформувати звіт")
        period_layout.addWidget(self.generate_btn)
        period_layout.addStretch()
        
        layout.addLayout(period_layout)
        
        # Вкладки звітів
        self.report_tabs = QTabWidget()
        
        # Залишки
        self.stock_tab = QWidget()
        self.setup_stock_tab()
        
        # Рух товару
        self.movement_tab = QWidget()
        self.setup_movement_tab()
        
        # Продажі
        self.sales_tab = QWidget()
        self.setup_sales_tab()
        
        self.report_tabs.addTab(self.stock_tab, "Залишки")
        self.report_tabs.addTab(self.movement_tab, "Рух товару")
        self.report_tabs.addTab(self.sales_tab, "Продажі")
        
        layout.addWidget(self.report_tabs)
        self.setLayout(layout)
        
        # Подключение сигналов
        self.generate_btn.clicked.connect(self.generate_reports)
        
        # Генерируем отчет при открытии
        self.generate_reports()
    
    def setup_stock_tab(self):
        layout = QVBoxLayout()
        self.stock_table = QTableWidget()
        layout.addWidget(self.stock_table)
        self.stock_tab.setLayout(layout)
    
    def setup_movement_tab(self):
        layout = QVBoxLayout()
        self.movement_table = QTableWidget()
        layout.addWidget(self.movement_table)
        self.movement_tab.setLayout(layout)
    
    def setup_sales_tab(self):
        layout = QVBoxLayout()
        self.sales_table = QTableWidget()
        layout.addWidget(self.sales_table)
        self.sales_tab.setLayout(layout)
    
    def generate_reports(self):
        date_from = self.date_from.date().toString('yyyy-MM-dd')
        date_to = self.date_to.date().toString('yyyy-MM-dd')
        
        self.generate_stock_report()
        self.generate_movement_report(date_from, date_to)
        self.generate_sales_report(date_from, date_to)
    
    def generate_stock_report(self):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT article, name, category, current_stock, retail_price,
                   (current_stock * retail_price) as total_value
            FROM products 
            ORDER BY name
        ''')
        
        products = cursor.fetchall()
        conn.close()
        
        self.stock_table.setColumnCount(6)
        self.stock_table.setHorizontalHeaderLabels([
            "Артикул", "Назва", "Категорія", "Залишок", "Ціна", "Загальна вартість"
        ])
        
        self.stock_table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            for col, value in enumerate(product):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.stock_table.setItem(row, col, item)
    
    def generate_movement_report(self, date_from, date_to):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 'Надходження' as type, r.document_number, r.receipt_date as date,
                   p.article, p.name, ri.quantity, ri.price, s.name as counterparty
            FROM receipt_items ri
            JOIN receipts r ON ri.receipt_id = r.id
            JOIN products p ON ri.product_id = p.id
            LEFT JOIN suppliers s ON r.supplier_id = s.id
            WHERE r.receipt_date BETWEEN ? AND ?
            
            UNION ALL
            
            SELECT 'Продаж' as type, s.document_number, s.sale_date as date,
                   p.article, p.name, si.quantity, si.price, s.client_name as counterparty
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.id
            JOIN products p ON si.product_id = p.id
            WHERE s.sale_date BETWEEN ? AND ?
            
            ORDER BY date DESC
        ''', (date_from, date_to, date_from, date_to))
        
        movements = cursor.fetchall()
        conn.close()
        
        self.movement_table.setColumnCount(8)
        self.movement_table.setHorizontalHeaderLabels([
            "Тип", "Номер", "Дата", "Артикул", "Товар", "Кількість", "Ціна", "Контрагент"
        ])
        
        self.movement_table.setRowCount(len(movements))
        
        for row, movement in enumerate(movements):
            for col, value in enumerate(movement):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.movement_table.setItem(row, col, item)
    
    def generate_sales_report(self, date_from, date_to):
        conn = sqlite3.connect("warehouse.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.document_number, s.sale_date, s.client_name, 
                   COUNT(si.id) as items_count, s.total_amount
            FROM sales s
            LEFT JOIN sale_items si ON s.id = si.sale_id
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY s.id
            ORDER BY s.sale_date DESC
        ''', (date_from, date_to))
        
        sales = cursor.fetchall()
        conn.close()
        
        self.sales_table.setColumnCount(5)
        self.sales_table.setHorizontalHeaderLabels([
            "Номер", "Дата", "Клієнт", "Кількість позицій", "Сума"
        ])
        
        self.sales_table.setRowCount(len(sales))
        
        for row, sale in enumerate(sales):
            for col, value in enumerate(sale):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.sales_table.setItem(row, col, item)

class ProductDialog(QDialog):
    def __init__(self, parent=None, product_data=None):
        super().__init__(parent)
        self.product_data = product_data
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Додати товар" if not self.product_data else "Редагувати товар")
        self.setFixedSize(400, 300)
        
        layout = QFormLayout()
        
        self.article_input = QLineEdit()
        self.name_input = QLineEdit()
        self.purchase_price_input = QDoubleSpinBox()
        self.purchase_price_input.setMaximum(999999.99)
        self.retail_price_input = QDoubleSpinBox()
        self.retail_price_input.setMaximum(999999.99)
        self.supplier_input = QLineEdit()
        self.category_input = QLineEdit()
        
        layout.addRow("Артикул:", self.article_input)
        layout.addRow("Назва:", self.name_input)
        layout.addRow("Ціна вхідна:", self.purchase_price_input)
        layout.addRow("Ціна роздрібна:", self.retail_price_input)
        layout.addRow("Постачальник:", self.supplier_input)
        layout.addRow("Категорія:", self.category_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Зберегти")
        self.cancel_btn = QPushButton("Скасувати")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addRow(button_layout)
        
        self.setLayout(layout)
        
        # Заполнение данных если редактирование
        if self.product_data:
            self.fill_data()
            
        # Подключение сигналов
        self.save_btn.clicked.connect(self.save_product)
        self.cancel_btn.clicked.connect(self.reject)
    
    def fill_data(self):
        self.article_input.setText(self.product_data[1])
        self.name_input.setText(self.product_data[2])
        self.purchase_price_input.setValue(self.product_data[3] or 0)
        self.retail_price_input.setValue(self.product_data[4] or 0)
        self.supplier_input.setText(self.product_data[5] or "")
        self.category_input.setText(self.product_data[6] or "")
    
    def save_product(self):
        article = self.article_input.text().strip()
        name = self.name_input.text().strip()
        
        if not article or not name:
            QMessageBox.warning(self, "Помилка", "Заповніть обов'язкові поля: Артикул та Назва")
            return
            
        self.product_data = (
            article, name, 
            self.purchase_price_input.value(),
            self.retail_price_input.value(),
            self.supplier_input.text(),
            self.category_input.text()
        )
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.setup_ui()
        self.load_products()
        
    def setup_ui(self):
        self.setWindowTitle("СкладУчет v1.0 - Продажі та Звіти")
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет с вкладками
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        
        # Вкладка товаров
        self.products_tab = QWidget()
        self.setup_products_tab()
        
        # Вкладка поставщиков
        self.suppliers_tab = QWidget()
        self.setup_suppliers_tab()
        
        # Вкладка надходжений
        self.receipts_tab = QWidget()
        self.setup_receipts_tab()
        
        # Вкладка продаж
        self.sales_tab = QWidget()
        self.setup_sales_tab()
        
        # Вкладка резервов
        self.reservations_tab = QWidget()
        self.setup_reservations_tab()
        
        self.tabs.addTab(self.products_tab, "📦 Товари")
        self.tabs.addTab(self.suppliers_tab, "👥 Постачальники")
        self.tabs.addTab(self.receipts_tab, "📥 Надходження")
        self.tabs.addTab(self.sales_tab, "💰 Продажі")
        self.tabs.addTab(self.reservations_tab, "⏰ Резерви")
        
        layout.addWidget(self.tabs)
        
        # Панель быстрого доступа
        quick_access_layout = QHBoxLayout()
        self.reports_btn = QPushButton("📊 Звіти")
        self.quick_sale_btn = QPushButton("🛒 Швидка накладна")
        self.quick_reserve_btn = QPushButton("⏰ Швидке резервування")
        
        quick_access_layout.addWidget(self.reports_btn)
        quick_access_layout.addWidget(self.quick_sale_btn)
        quick_access_layout.addWidget(self.quick_reserve_btn)
        quick_access_layout.addStretch()
        
        layout.addLayout(quick_access_layout)
        central_widget.setLayout(layout)
        
        # Подключение сигналов
        self.reports_btn.clicked.connect(self.show_reports)
        self.quick_sale_btn.clicked.connect(self.quick_sale)
        self.quick_reserve_btn.clicked.connect(self.quick_reserve)
    
    def setup_products_tab(self):
        layout = QVBoxLayout()
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Додати товар")
        self.edit_btn = QPushButton("✏️ Редагувати")
        self.delete_btn = QPushButton("🗑️ Видалити")
        self.refresh_btn = QPushButton("🔄 Оновити")
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.refresh_btn)
        button_layout.addStretch()
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Пошук по назві або артикулу...")
        
        button_layout.addWidget(QLabel("Пошук:"))
        button_layout.addWidget(self.search_input)
        
        layout.addLayout(button_layout)
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Артикул", "Назва", "Ціна вх.", "Ціна роздр.", "Категорія", "Залишок"
        ])
        
        # Настройка таблицы
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        layout.addWidget(self.table)
        
        self.products_tab.setLayout(layout)
        
        # Подключение сигналов
        self.add_btn.clicked.connect(self.add_product)
        self.edit_btn.clicked.connect(self.edit_product)
        self.delete_btn.clicked.connect(self.delete_product)
        self.refresh_btn.clicked.connect(self.load_products)
        self.search_input.textChanged.connect(self.search_products)
    
    def setup_suppliers_tab(self):
        layout = QVBoxLayout()
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.supplier_add_btn = QPushButton("➕ Додати постачальника")
        self.supplier_edit_btn = QPushButton("✏️ Редагувати")
        self.supplier_delete_btn = QPushButton("🗑️ Видалити")
        self.supplier_refresh_btn = QPushButton("🔄 Оновити")
        
        button_layout.addWidget(self.supplier_add_btn)
        button_layout.addWidget(self.supplier_edit_btn)
        button_layout.addWidget(self.supplier_delete_btn)
        button_layout.addWidget(self.supplier_refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Таблица поставщиков
        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(5)
        self.suppliers_table.setHorizontalHeaderLabels([
            "ID", "Назва", "Контакт", "Телефон", "Email"
        ])
        
        header = self.suppliers_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.suppliers_table)
        
        self.suppliers_tab.setLayout(layout)
        
        # Подключение сигналов
        self.supplier_add_btn.clicked.connect(self.add_supplier)
        self.supplier_edit_btn.clicked.connect(self.edit_supplier)
        self.supplier_delete_btn.clicked.connect(self.delete_supplier)
        self.supplier_refresh_btn.clicked.connect(self.load_suppliers)
    
    def setup_receipts_tab(self):
        layout = QVBoxLayout()
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.receipt_add_btn = QPushButton("📥 Нове надходження")
        self.receipt_refresh_btn = QPushButton("🔄 Оновити")
        
        button_layout.addWidget(self.receipt_add_btn)
        button_layout.addWidget(self.receipt_refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Таблица надходжений
        self.receipts_table = QTableWidget()
        self.receipts_table.setColumnCount(5)
        self.receipts_table.setHorizontalHeaderLabels([
            "ID", "Номер", "Дата", "Постачальник", "Сума"
        ])
        
        header = self.receipts_table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        layout.addWidget(self.receipts_table)
        
        self.receipts_tab.setLayout(layout)
        
        # Подключение сигналов
        self.receipt_add_btn.clicked.connect(self.add_receipt)
        self.receipt_refresh_btn.clicked.connect(self.load_receipts)
    
    def setup_sales_tab(self):
        layout = QVBoxLayout()
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.sale_add_btn = QPushButton("💰 Нова накладна")
        self.sale_refresh_btn = QPushButton("🔄 Оновити")
        
        button_layout.addWidget(self.sale_add_btn)
        button_layout.addWidget(self.sale_refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Таблица продаж
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(6)
        self.sales_table.setHorizontalHeaderLabels([
            "ID", "Номер", "Дата", "Клієнт", "Позицій", "Сума"
        ])
        
        header = self.sales_table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        
        layout.addWidget(self.sales_table)
        
        self.sales_tab.setLayout(layout)
        
        # Подключение сигналов
        self.sale_add_btn.clicked.connect(self.add_sale)
        self.sale_refresh_btn.clicked.connect(self.load_sales)
    
    def setup_reservations_tab(self):
        layout = QVBoxLayout()
        
        # Панель кнопок
        button_layout = QHBoxLayout()
        
        self.reserve_add_btn = QPushButton("⏰ Нове резервування")
        self.reserve_complete_btn = QPushButton("✅ Завершити")
        self.reserve_cancel_btn = QPushButton("❌ Скасувати")
        self.reserve_refresh_btn = QPushButton("🔄 Оновити")
        
        button_layout.addWidget(self.reserve_add_btn)
        button_layout.addWidget(self.reserve_complete_btn)
        button_layout.addWidget(self.reserve_cancel_btn)
        button_layout.addWidget(self.reserve_refresh_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Таблица резервов
        self.reservations_table = QTableWidget()
        self.reservations_table.setColumnCount(7)
        self.reservations_table.setHorizontalHeaderLabels([
            "ID", "Клієнт", "Товар", "Кількість", "Дата резерву", "Дійсний до", "Статус"
        ])
        
        header = self.reservations_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        
        layout.addWidget(self.reservations_table)
        
        self.reservations_tab.setLayout(layout)
        
        # Подключение сигналов
        self.reserve_add_btn.clicked.connect(self.add_reservation)
        self.reserve_complete_btn.clicked.connect(self.complete_reservation)
        self.reserve_cancel_btn.clicked.connect(self.cancel_reservation)
        self.reserve_refresh_btn.clicked.connect(self.load_reservations)
    
    def load_products(self):
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        self.table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            for col, value in enumerate(product[:7]):  # Показываем первые 7 полей
                item = QTableWidgetItem(str(value) if value is not None else "")
                if col > 0:  # Не редактируем ID
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
    
    def load_suppliers(self):
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers ORDER BY name")
        suppliers = cursor.fetchall()
        conn.close()
        
        self.suppliers_table.setRowCount(len(suppliers))
        
        for row, supplier in enumerate(suppliers):
            for col, value in enumerate(supplier[:5]):  # Показываем первые 5 полей
                item = QTableWidgetItem(str(value) if value is not None else "")
                if col > 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.suppliers_table.setItem(row, col, item)
    
    def load_receipts(self):
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.document_number, r.receipt_date, s.name, r.total_amount
            FROM receipts r
            LEFT JOIN suppliers s ON r.supplier_id = s.id
            ORDER BY r.receipt_date DESC
        ''')
        receipts = cursor.fetchall()
        conn.close()
        
        self.receipts_table.setRowCount(len(receipts))
        
        for row, receipt in enumerate(receipts):
            for col, value in enumerate(receipt):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.receipts_table.setItem(row, col, item)
    
    def load_sales(self):
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.document_number, s.sale_date, s.client_name,
                   (SELECT COUNT(*) FROM sale_items WHERE sale_id = s.id) as items_count,
                   s.total_amount
            FROM sales s
            ORDER BY s.sale_date DESC
        ''')
        sales = cursor.fetchall()
        conn.close()
        
        self.sales_table.setRowCount(len(sales))
        
        for row, sale in enumerate(sales):
            for col, value in enumerate(sale):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.sales_table.setItem(row, col, item)
    
    def load_reservations(self):
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.client_name, p.name, r.quantity, 
                   r.reservation_date, r.expiry_date, r.status
            FROM reservations r
            JOIN products p ON r.product_id = p.id
            ORDER BY r.reservation_date DESC
        ''')
        reservations = cursor.fetchall()
        conn.close()
        
        self.reservations_table.setRowCount(len(reservations))
        
        for row, reservation in enumerate(reservations):
            for col, value in enumerate(reservation):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.reservations_table.setItem(row, col, item)
    
    def search_products(self):
        search_text = self.search_input.text().strip()
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        if search_text:
            cursor.execute('''
                SELECT * FROM products 
                WHERE name LIKE ? OR article LIKE ?
                ORDER BY name
            ''', (f'%{search_text}%', f'%{search_text}%'))
        else:
            cursor.execute("SELECT * FROM products ORDER BY name")
            
        products = cursor.fetchall()
        conn.close()
        
        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            for col, value in enumerate(product[:7]):
                item = QTableWidgetItem(str(value) if value is not None else "")
                if col > 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
    
    def add_product(self):
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO products (article, name, purchase_price, retail_price, supplier, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', dialog.product_data)
                conn.commit()
                QMessageBox.information(self, "Успіх", "Товар успішно додано!")
                self.load_products()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Помилка", "Товар з таким артикулом вже існує!")
            finally:
                conn.close()
    
    def edit_product(self):
        current_row = self.table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть товар для редагування!")
            return
            
        product_id = int(self.table.item(current_row, 0).text())
        
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product_data = cursor.fetchone()
        conn.close()
        
        dialog = ProductDialog(self, product_data)
        if dialog.exec_() == QDialog.Accepted:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE products 
                    SET article=?, name=?, purchase_price=?, retail_price=?, supplier=?, category=?
                    WHERE id=?
                ''', (*dialog.product_data, product_id))
                conn.commit()
                QMessageBox.information(self, "Успіх", "Товар успішно оновлено!")
                self.load_products()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Помилка", "Товар з таким артикулом вже існує!")
            finally:
                conn.close()
    
    def delete_product(self):
        current_row = self.table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть товар для видалення!")
            return
            
        product_id = int(self.table.item(current_row, 0).text())
        product_name = self.table.item(current_row, 2).text()
        
        reply = QMessageBox.question(
            self, 
            "Підтвердження", 
            f"Видалити товар '{product_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Успіх", "Товар успішно видалено!")
            self.load_products()
    
    def add_supplier(self):
        dialog = SupplierDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO suppliers (name, contact_person, phone, email, address)
                    VALUES (?, ?, ?, ?, ?)
                ''', dialog.supplier_data)
                conn.commit()
                QMessageBox.information(self, "Успіх", "Постачальника успішно додано!")
                self.load_suppliers()
            except Exception as e:
                QMessageBox.warning(self, "Помилка", f"Помилка при додаванні: {str(e)}")
            finally:
                conn.close()
    
    def edit_supplier(self):
        current_row = self.suppliers_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть постачальника для редагування!")
            return
            
        supplier_id = int(self.suppliers_table.item(current_row, 0).text())
        
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        supplier_data = cursor.fetchone()
        conn.close()
        
        dialog = SupplierDialog(self, supplier_data)
        if dialog.exec_() == QDialog.Accepted:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE suppliers 
                    SET name=?, contact_person=?, phone=?, email=?, address=?
                    WHERE id=?
                ''', (*dialog.supplier_data, supplier_id))
                conn.commit()
                QMessageBox.information(self, "Успіх", "Постачальника успішно оновлено!")
                self.load_suppliers()
            except Exception as e:
                QMessageBox.warning(self, "Помилка", f"Помилка при оновленні: {str(e)}")
            finally:
                conn.close()
    
    def delete_supplier(self):
        current_row = self.suppliers_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть постачальника для видалення!")
            return
            
        supplier_id = int(self.suppliers_table.item(current_row, 0).text())
        supplier_name = self.suppliers_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, 
            "Підтвердження", 
            f"Видалити постачальника '{supplier_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Успіх", "Постачальника успішно видалено!")
            self.load_suppliers()
    
    def add_receipt(self):
        dialog = ReceiptDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_receipts()
            self.load_products()  # Обновляем залишки
    
    def add_sale(self):
        dialog = SaleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_sales()
            self.load_products()  # Обновляем залишки
    
    def add_reservation(self):
        dialog = ReservationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_reservations()
    
    def complete_reservation(self):
        current_row = self.reservations_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть резерв для завершення!")
            return
        
        reservation_id = int(self.reservations_table.item(current_row, 0).text())
        
        reply = QMessageBox.question(
            self, 
            "Підтвердження", 
            "Завершити резерв?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            cursor.execute("UPDATE reservations SET status = 'completed' WHERE id = ?", (reservation_id,))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Успіх", "Резерв успішно завершено!")
            self.load_reservations()
    
    def cancel_reservation(self):
        current_row = self.reservations_table.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Помилка", "Виберіть резерв для скасування!")
            return
        
        reservation_id = int(self.reservations_table.item(current_row, 0).text())
        
        reply = QMessageBox.question(
            self, 
            "Підтвердження", 
            "Скасувати резерв?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db.db_name)
            cursor = conn.cursor()
            cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (reservation_id,))
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Успіх", "Резерв успішно скасовано!")
            self.load_reservations()
    
    def show_reports(self):
        dialog = ReportsDialog(self)
        dialog.exec_()
    
    def quick_sale(self):
        self.tabs.setCurrentIndex(3)  # Переходим на вкладку продаж
        self.add_sale()
    
    def quick_reserve(self):
        self.tabs.setCurrentIndex(4)  # Переходим на вкладку резервов
        self.add_reservation()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()