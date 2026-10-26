import os
import json
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings

class DatabaseManager:
    """
    Unified Database Manager for SR Enterprise.
    Uses high-speed, zero-dependency SQLite database engine.
    """
    def __init__(self):
        self.sqlite_path = str(settings.SQLITE_PATH)
        self._init_sqlite_schema()
        self._seed_default_data_if_empty()

    def is_firebase_active(self) -> bool:
        return False

    def _get_connection(self):
        conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite_schema(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                sku TEXT UNIQUE,
                name TEXT NOT NULL,
                name_bn TEXT,
                category TEXT NOT NULL,
                unit TEXT NOT NULL,
                buy_price REAL DEFAULT 0,
                sell_price REAL DEFAULT 0,
                stock REAL DEFAULT 0,
                alert_qty REAL DEFAULT 10,
                qr_code TEXT,
                image_url TEXT,
                description TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS farmers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                pin TEXT NOT NULL DEFAULT '1234',
                shed_name TEXT,
                address TEXT,
                shed_capacity INTEGER DEFAULT 1000,
                image_url TEXT,
                total_due REAL DEFAULT 0,
                total_batches INTEGER DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                batch_no TEXT NOT NULL,
                farmer_id TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                bird_type TEXT NOT NULL,
                chick_qty INTEGER DEFAULT 0,
                chick_unit_cost REAL DEFAULT 0,
                total_chick_cost REAL DEFAULT 0,
                start_date TEXT NOT NULL,
                harvest_date TEXT,
                status TEXT DEFAULT 'active',
                total_feed_bags REAL DEFAULT 0,
                total_feed_cost REAL DEFAULT 0,
                total_med_cost REAL DEFAULT 0,
                total_other_cost REAL DEFAULT 0,
                total_investment REAL DEFAULT 0,
                total_birds_sold INTEGER DEFAULT 0,
                total_weight_kg REAL DEFAULT 0,
                avg_rate_per_kg REAL DEFAULT 0,
                total_sale_amount REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                dealer_recovery REAL DEFAULT 0,
                farmer_profit REAL DEFAULT 0,
                mortality_count INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS batch_logs (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                farmer_id TEXT NOT NULL,
                log_type TEXT NOT NULL,
                log_date TEXT NOT NULL,
                item_id TEXT,
                item_name TEXT NOT NULL,
                qty REAL DEFAULT 0,
                unit TEXT,
                unit_price REAL DEFAULT 0,
                total_amount REAL DEFAULT 0,
                note TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                invoice_no TEXT UNIQUE NOT NULL,
                farmer_id TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                batch_id TEXT,
                items_json TEXT NOT NULL,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                net_total REAL DEFAULT 0,
                payment_type TEXT DEFAULT 'credit',
                paid_amount REAL DEFAULT 0,
                due_amount REAL DEFAULT 0,
                invoice_date TEXT NOT NULL,
                note TEXT,
                receipt_image_url TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                receipt_no TEXT UNIQUE NOT NULL,
                farmer_id TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                batch_id TEXT,
                amount REAL NOT NULL,
                payment_method TEXT DEFAULT 'cash',
                transaction_ref TEXT,
                voucher_image_url TEXT,
                payment_date TEXT NOT NULL,
                note TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS feed_requests (
                id TEXT PRIMARY KEY,
                farmer_id TEXT NOT NULL,
                farmer_name TEXT NOT NULL,
                batch_id TEXT,
                items_requested TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                farmer_note TEXT,
                created_at TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)

            # Ensure all products use SKU as QR code
            cur.execute("UPDATE products SET qr_code = sku WHERE qr_code IS NULL OR qr_code LIKE 'SRE:PRD:%'")

            conn.commit()

    def _seed_default_data_if_empty(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            if count == 0:
                print("[DATABASE] Seeding realistic initial products, farmer, and active batch...")
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                initial_products = [
                    # পৌল্ট্রি খাদ্য
                    ("P001", "SRE-FD-01", "নুরিশ ব্রয়লার স্টার্টার", "Nourish Broiler Starter", "পৌল্ট্রি খাদ্য", "বস্তা (৫০ কেজি)", 3350, 3550, 85, 20, "SRE:PRD:P001:SRE-FD-01", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "০১-১৪ দিন বয়সের ব্রয়লার বাচ্চার প্রিমিয়াম স্টার্টার ফিড"),
                    ("P002", "SRE-FD-02", "সিপি ব্রয়লার গ্রোয়ার", "CP Broiler Grower", "পৌল্ট্রি খাদ্য", "বস্তা (৫০ কেজি)", 3250, 3450, 120, 25, "SRE:PRD:P002:SRE-FD-02", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "১৫-২৮ দিন বয়সের ব্রয়লার মুরগীর সুষম বাড়ন্ত খাদ্য"),
                    ("P003", "SRE-FD-03", "কাজী ব্রয়লার ফিনিশার", "Kazi Broiler Finisher", "পৌল্ট্রি খাদ্য", "বস্তা (৫০ কেজি)", 3200, 3400, 60, 20, "SRE:PRD:P003:SRE-FD-03", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "ব্রয়লার বিক্রয়ের পূর্বের শেষ পর্যায়ের খাদ্য"),
                    ("P004", "SRE-FD-04", "আফতাব সোনালী স্টার্টার", "Aftab Sonali Starter", "পৌল্ট্রি খাদ্য", "বস্তা (৫০ কেজি)", 3100, 3300, 45, 15, "SRE:PRD:P004:SRE-FD-04", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "সোনালী মুরগীর জন্য বিশেষ গ্রোথ ফর্মুলা ফিড"),
                    ("P005", "SRE-FD-05", "নুরিশ লেয়ার লেয়ার-১", "Nourish Layer-1", "পৌল্ট্রি খাদ্য", "বস্তা (৫০ কেজি)", 2950, 3150, 35, 15, "SRE:PRD:P005:SRE-FD-05", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "ডিমপাড়া লেয়ার মুরগীর জন্য উচ্চ ক্যালসিয়ামযুক্ত খাদ্য"),

                    # গরুর খাদ্য
                    ("P006", "SRE-CF-01", "ডেইরি স্পেশাল গাভীর ফিড", "Dairy Special Milk Feed", "গরুর খাদ্য", "বস্তা (৫০ কেজি)", 2200, 2400, 50, 15, "SRE:PRD:P006:SRE-CF-01", "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=400&q=80", "দুধালো গাভীর দুধ বৃদ্ধি ও সুস্বাস্থ্যের জন্য"),
                    ("P007", "SRE-CF-02", "ক্যাটল ফ্যাটেনিং ফিড", "Cattle Fattening Feed", "গরুর খাদ্য", "বস্তা (৫০ কেজি)", 2150, 2350, 40, 15, "SRE:PRD:P007:SRE-CF-02", "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=400&q=80", "ষাঁড় দ্রুত মোটাতাজাকরণ স্পেশাল ব্যালান্সড ফিড"),
                    ("P008", "SRE-CF-03", "স্পেশাল গমের ভূষি", "Premium Wheat Bran", "গরুর খাদ্য", "বস্তা (৩৫ কেজি)", 1650, 1800, 8, 15, "SRE:PRD:P008:SRE-CF-03", "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=400&q=80", "উচ্চ আঁশ ও ফাইবার সমৃদ্ধ পরিষ্কার লাল গমের ভূষি"),
                    ("P009", "SRE-CF-04", "খাঁটি সরিষার খৈল", "Mustard Oil Cake", "গরুর খাদ্য", "বস্তা (৫০ কেজি)", 2300, 2500, 25, 10, "SRE:PRD:P009:SRE-CF-04", "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=400&q=80", "উচ্চ প্রোটিন সমৃদ্ধ দেশি ঘানির সরিষার খৈল"),

                    # ভেটেরিনারি ঔষধ ও ভ্যাকসিন
                    ("P010", "SRE-MED-01", "রেনামাইসিন ১০০ গ্রাম", "Renamycin 100g Powder", "ভেটেরিনারি ঔষধ", "প্যাকেট", 110, 130, 90, 20, "SRE:PRD:P010:SRE-MED-01", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "অক্সিটেট্রাসাইক্লিন ব্রড-স্পেকট্রাম অ্যান্টিবায়োটিক"),
                    ("P011", "SRE-MED-02", "সিপ্রোসিন ভেট ১০০ মিলি", "Ciprocin Vet 100ml", "ভেটেরিনারি ঔষধ", "বোতল", 175, 200, 65, 15, "SRE:PRD:P011:SRE-MED-02", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "সিপ্রোফ্লক্সাসিন অ্যান্টিমাইক্রোবিয়াল সলিউশন"),
                    ("P012", "SRE-MED-03", "রেনা-ডব্লিউএস ১০০ গ্রাম", "Rena-WS Vitamin Powder", "ভেটেরিনারি ঔষধ", "প্যাকেট", 145, 170, 75, 20, "SRE:PRD:P012:SRE-MED-03", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "পানিতে দ্রবণীয় মাল্টি-ভিটামিন ও অ্যামাইনো এসিড"),
                    ("P013", "SRE-MED-04", "ইলেক্ট্রোম্যাক্স ওরস্যালাইন", "Electromax Oral Saline", "ভেটেরিনারি ঔষধ", "প্যাকেট", 55, 70, 110, 25, "SRE:PRD:P013:SRE-MED-04", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "হিট স্ট্রোক প্রতিরোধ ও পানিশূন্যতা দূরীকরণ স্যালাইন"),
                    ("P014", "SRE-MED-05", "রেনালিভ লিভার টনিক ৫০০ মিলি", "Renalive Liver Tonic 500ml", "ভেটেরিনারি ঔষধ", "বোতল", 260, 295, 4, 10, "SRE:PRD:P014:SRE-MED-05", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "লিভার সুরক্ষাকারী ও হজমশক্তি বৃদ্ধিকারক টনিক"),
                    ("P015", "SRE-MED-06", "ক্যালপেক্স ডি৩ ১ লিটার", "Calpex D3 Calcium 1L", "ভেটেরিনারি ঔষধ", "বোতল", 420, 480, 22, 8, "SRE:PRD:P015:SRE-MED-06", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80", "দুধালো গাভী ও ডিমপাড়া মুরগীর উচ্চ ক্ষমতার তরল ক্যালসিয়াম"),

                    # বাচ্চা (Day Old Chicks)
                    ("P016", "SRE-CHK-01", "ব্রয়লার বাচ্চা (Cobb 500)", "Broiler Day Old Chick", "বাচ্চা (DOC)", "পিস", 48, 55, 1200, 300, "SRE:PRD:P016:SRE-CHK-01", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "উন্নত মানের একদিন বয়সী ব্রয়লার বাচ্চা"),
                    ("P017", "SRE-CHK-02", "সোনালী হাইব্রিড বাচ্চা", "Sonali Hybrid Chick", "বাচ্চা (DOC)", "পিস", 36, 42, 800, 200, "SRE:PRD:P017:SRE-CHK-02", "https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?auto=format&fit=crop&w=400&q=80", "এ গ্রেডের রোগ প্রতিরোধী সোনালী বাচ্চা")
                ]

                cur.executemany("""
                INSERT INTO products (id, sku, name_bn, name, category, unit, buy_price, sell_price, stock, alert_qty, qr_code, image_url, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], now_str, now_str) for p in initial_products])

                # Seed sample Farmers
                f1_id = "FARMER-101"
                cur.execute("""
                INSERT INTO farmers (id, name, phone, pin, shed_name, address, shed_capacity, image_url, total_due, total_batches, notes, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f1_id,
                    "মোঃ রফিকুল ইসলাম",
                    "01712345678",
                    "1234",
                    "রফিক ব্রয়লার ফার্ম (শেড ১)",
                    "কালিগঞ্জ, গাজীপুর",
                    1500,
                    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=300&q=80",
                    84500,
                    3,
                    "চুক্তিবদ্ধ বিশ্বস্ত খামারি, নিয়মিত শেড তোলে।",
                    "active",
                    now_str
                ))

                f2_id = "FARMER-102"
                cur.execute("""
                INSERT INTO farmers (id, name, phone, pin, shed_name, address, shed_capacity, image_url, total_due, total_batches, notes, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f2_id,
                    "আব্দুল মোতালেব",
                    "01812345678",
                    "1234",
                    "মোতালেব ডেইরি ও পোল্ট্রি শেড",
                    "শ্রীপুর, গাজীপুর",
                    2000,
                    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=300&q=80",
                    42000,
                    2,
                    "গরুর খামার ও সোনালী মুরগীর শেড পরিচালনা করেন।",
                    "active",
                    now_str
                ))

                # Seed sample ongoing batch for Farmer 1
                b1_id = "BATCH-2026-01"
                cur.execute("""
                INSERT INTO batches (
                    id, batch_no, farmer_id, farmer_name, bird_type, chick_qty, chick_unit_cost, total_chick_cost,
                    start_date, harvest_date, status, total_feed_bags, total_feed_cost, total_med_cost, total_other_cost,
                    total_investment, total_birds_sold, total_weight_kg, avg_rate_per_kg, total_sale_amount,
                    net_profit, dealer_recovery, farmer_profit, mortality_count, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    b1_id,
                    "ব্যাচ-০৩ (ব্রয়লার)",
                    f1_id,
                    "মোঃ রফিকুল ইসলাম",
                    "ব্রয়লার (Cobb 500)",
                    1200,
                    55,
                    66000,
                    "2026-10-05",
                    None,
                    "active",
                    22,
                    77500,
                    5200,
                    1800,
                    150500, # 66000 + 77500 + 5200 + 1800
                    0, 0, 0, 0, 0, 0, 0,
                    28,
                    "শেডের বয়স ২১ দিন চলছে। সুস্থ ও স্বাভাবিক বৃদ্ধি।",
                    now_str
                ))

                # Seed batch logs for this batch
                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("LOG-01", b1_id, f1_id, "chick", "2026-10-05", "P016", "ব্রয়লার বাচ্চা (Cobb 500)", 1200, "পিস", 55, 66000, "১ম দিন: বাচ্চা ডেলিভারি ও শেডে উঠানো", now_str))

                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("LOG-02", b1_id, f1_id, "feed", "2026-10-05", "P001", "নুরিশ ব্রয়লার স্টার্টার", 6, "বস্তা", 3550, 21300, "বাচ্চা আসার দিনে ১ম কিস্তির স্টার্টার ফিড", now_str))

                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("LOG-03", b1_id, f1_id, "medicine", "2026-10-06", "P012", "রেনা-ডব্লিউএস ১০০ গ্রাম", 4, "প্যাকেট", 170, 680, "বাচ্চার স্ট্রেস কাটাতে ভিটামিন কোর্স", now_str))

                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("LOG-04", b1_id, f1_id, "feed", "2026-10-15", "P002", "সিপি ব্রয়লার গ্রোয়ার", 16, "বস্তা", 3450, 55200, "গ্রোয়ার ফিড ডেলিভারি (চালান #INV-1002)", now_str))

                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("LOG-05", b1_id, f1_id, "mortality", "2026-10-18", None, "মুরগী মৃত্যু হিসাব", 28, "পিস", 0, 0, "২১ দিন পর্যন্ত মোট মর্টালিটি ২৮ টি", now_str))

                # Seed sample payment
                cur.execute("""
                INSERT INTO payments (id, receipt_no, farmer_id, farmer_name, batch_id, amount, payment_method, transaction_ref, payment_date, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, ("PAY-01", "REC-8801", f1_id, "মোঃ রফিকুল ইসলাম", b1_id, 25000, "bKash", "TRX9923841", "2026-10-20", "পূর্বের বকেয়া ও চলতি ব্যাচের অগ্রিম বাবদ বিকাশ পেমেন্ট", now_str))

                # Settings
                settings_data = [
                    ("shop_name", "SR Enterprise (এস আর এন্টারপ্রাইজ)"),
                    ("owner_name", "মোঃ সারোয়ার হোসেন"),
                    ("phone", "01700-000000"),
                    ("alt_phone", "01800-000000"),
                    ("address", "স্টেশন রোড, কাপাসিয়া, গাজীপুর"),
                    ("bkash_merchant", "01700-000000 (মার্চেন্ট)"),
                    ("nagad_personal", "01800-000000 (পার্সোনাল)"),
                    ("bank_info", "ইসলামী ব্যাংক বাংলাদেশ লিঃ, কাপাসিয়া শাখা, হি/নং: ২০৫০...")
                ]
                cur.executemany("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", settings_data)

                conn.commit()

    # ==================== STATS & DASHBOARD ====================
    def get_dashboard_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*) FROM farmers WHERE status = 'active'")
            active_farmers = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(total_due), 0) FROM farmers")
            total_farmer_dues = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM batches WHERE status = 'active'")
            active_sheds = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(total_investment), 0) FROM batches WHERE status = 'active'")
            live_shed_investment = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM products")
            total_products = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM products WHERE stock <= alert_qty")
            low_stock_count = cur.fetchone()[0]

            today_date = datetime.now().strftime("%Y-%m-%d")
            cur.execute("SELECT COALESCE(SUM(net_total), 0) FROM invoices WHERE invoice_date LIKE ?", (f"{today_date}%",))
            today_dispatch = cur.fetchone()[0]

            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_date LIKE ?", (f"{today_date}%",))
            today_received = cur.fetchone()[0]

            return {
                "active_farmers": active_farmers,
                "total_farmer_dues": total_farmer_dues,
                "active_sheds": active_sheds,
                "live_shed_investment": live_shed_investment,
                "total_products": total_products,
                "low_stock_count": low_stock_count,
                "today_dispatch": today_dispatch,
                "today_received": today_received,
                "is_firebase": self.is_firebase_active(),
            }

    # ==================== PRODUCTS / INVENTORY ====================
    def get_products(self, category: Optional[str] = None, low_stock_only: bool = False) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM products WHERE 1=1"
            params = []
            if category:
                query += " AND category = ?"
                params.append(category)
            if low_stock_only:
                query += " AND stock <= alert_qty"
            query += " ORDER BY category ASC, name_bn ASC"
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM products 
                WHERE id = ? OR sku = ? OR qr_code = ? 
                   OR LOWER(sku) = LOWER(?) OR LOWER(id) = LOWER(?)
            """, (product_id, product_id, product_id, product_id, product_id))
            row = cur.fetchone()
            return dict(row) if row else None

    def save_product(self, data: Dict[str, Any]) -> str:
        product_id = data.get("id") or f"P{uuid.uuid4().hex[:8].upper()}"
        sku = (data.get("sku") or "").strip() or f"SRE-{uuid.uuid4().hex[:6].upper()}"
        qr_code = sku
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO products (id, sku, name, name_bn, category, unit, buy_price, sell_price, stock, alert_qty, qr_code, image_url, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                sku=excluded.sku,
                name=excluded.name,
                name_bn=excluded.name_bn,
                category=excluded.category,
                unit=excluded.unit,
                buy_price=excluded.buy_price,
                sell_price=excluded.sell_price,
                stock=excluded.stock,
                alert_qty=excluded.alert_qty,
                image_url=COALESCE(excluded.image_url, products.image_url),
                description=excluded.description,
                updated_at=excluded.updated_at
            """, (
                product_id, sku, data.get("name", ""), data.get("name_bn", ""),
                data.get("category", "পৌল্ট্রি খাদ্য"), data.get("unit", "বস্তা"),
                float(data.get("buy_price", 0)), float(data.get("sell_price", 0)),
                float(data.get("stock", 0)), float(data.get("alert_qty", 10)),
                qr_code, data.get("image_url", ""), data.get("description", ""),
                now_str, now_str
            ))
            conn.commit()

        # If Firebase is active, sync product to Firestore
        if self.is_firebase_active():
            try:
                doc_ref = _firestore_client.collection("products").document(product_id)
                doc_data = dict(data)
                doc_data.update({"id": product_id, "sku": sku, "qr_code": qr_code, "updated_at": now_str})
                doc_ref.set(doc_data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE SYNC ERROR] {e}")

        return product_id

    def adjust_stock(self, product_id: str, delta_qty: float):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ? OR sku = ? OR qr_code = ?",
                        (delta_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id, product_id, product_id))
            conn.commit()

    def delete_product(self, product_id: str):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
        if self.is_firebase_active():
            try:
                _firestore_client.collection("products").document(product_id).delete()
            except Exception as e:
                print(f"[FIRESTORE DELETE ERROR] {e}")

    # ==================== FARMERS ====================
    def get_farmers(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM farmers WHERE 1=1"
            params = []
            if search:
                query += " AND (name LIKE ? OR phone LIKE ? OR shed_name LIKE ?)"
                term = f"%{search}%"
                params.extend([term, term, term])
            query += " ORDER BY name ASC"
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_farmer_by_id(self, farmer_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM farmers WHERE id = ? OR phone = ?", (farmer_id, farmer_id))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_farmer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        clean_phone = phone.strip()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM farmers WHERE phone = ?", (clean_phone,))
            row = cur.fetchone()
            return dict(row) if row else None

    def save_farmer(self, data: Dict[str, Any]) -> str:
        farmer_id = data.get("id") or f"FARMER-{uuid.uuid4().hex[:6].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO farmers (id, name, phone, pin, shed_name, address, shed_capacity, image_url, total_due, total_batches, notes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                phone=excluded.phone,
                pin=COALESCE(NULLIF(excluded.pin, ''), farmers.pin),
                shed_name=excluded.shed_name,
                address=excluded.address,
                shed_capacity=excluded.shed_capacity,
                image_url=COALESCE(excluded.image_url, farmers.image_url),
                notes=excluded.notes,
                status=excluded.status
            """, (
                farmer_id, data.get("name", ""), data.get("phone", ""),
                data.get("pin", "1234"), data.get("shed_name", ""),
                data.get("address", ""), int(data.get("shed_capacity", 1000)),
                data.get("image_url", ""), float(data.get("total_due", 0)),
                int(data.get("total_batches", 0)), data.get("notes", ""),
                data.get("status", "active"), now_str
            ))
            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("farmers").document(farmer_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE FARMER SYNC ERROR] {e}")

        return farmer_id

    def delete_farmer(self, farmer_id: str) -> bool:
        """
        Deletes a farmer record from local database and Firestore.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM farmers WHERE id = ?", (farmer_id,))
            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("farmers").document(farmer_id).delete()
            except Exception as e:
                print(f"[FIRESTORE FARMER DELETE ERROR] {e}")
        return True

    def update_farmer_due(self, farmer_id: str, delta_amount: float):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE farmers SET total_due = total_due + ? WHERE id = ?", (delta_amount, farmer_id))
            conn.commit()

    # ==================== BATCHES (SHED LIFE-CYCLE) ====================
    def get_batches(self, status: Optional[str] = None, farmer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM batches WHERE 1=1"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            if farmer_id:
                query += " AND farmer_id = ?"
                params.append(farmer_id)
            query += " ORDER BY start_date DESC"
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_batch_by_id(self, batch_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def save_batch(self, data: Dict[str, Any]) -> str:
        batch_id = data.get("id") or f"BATCH-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        chick_qty = int(data.get("chick_qty", 0))
        chick_unit_cost = float(data.get("chick_unit_cost", 0))
        total_chick_cost = chick_qty * chick_unit_cost

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO batches (
                id, batch_no, farmer_id, farmer_name, bird_type, chick_qty, chick_unit_cost, total_chick_cost,
                start_date, harvest_date, status, total_feed_bags, total_feed_cost, total_med_cost, total_other_cost,
                total_investment, total_birds_sold, total_weight_kg, avg_rate_per_kg, total_sale_amount,
                net_profit, dealer_recovery, farmer_profit, mortality_count, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                batch_no=excluded.batch_no,
                bird_type=excluded.bird_type,
                notes=excluded.notes
            """, (
                batch_id, data.get("batch_no", ""), data.get("farmer_id", ""), data.get("farmer_name", ""),
                data.get("bird_type", "ব্রয়লার"), chick_qty, chick_unit_cost, total_chick_cost,
                data.get("start_date", datetime.now().strftime("%Y-%m-%d")), None, "active",
                0, 0, 0, 0,
                total_chick_cost, # Initial investment is chick cost
                0, 0, 0, 0, 0, 0, 0, 0, data.get("notes", ""), now_str
            ))

            # Also create initial batch log for chick delivery
            if chick_qty > 0 and not data.get("id"):
                cur.execute("""
                INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"LOG-{uuid.uuid4().hex[:8].upper()}", batch_id, data.get("farmer_id", ""), "chick",
                    data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                    "", f"{data.get('bird_type', 'বাচ্চা')} ডেলিভারি", chick_qty, "পিস", chick_unit_cost, total_chick_cost,
                    "শেড শুরু: একদিন বয়সী বাচ্চা প্রদান", now_str
                ))

                # Update farmer's due by the chick cost
                cur.execute("UPDATE farmers SET total_due = total_due + ?, total_batches = total_batches + 1 WHERE id = ?",
                            (total_chick_cost, data.get("farmer_id", "")))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("batches").document(batch_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE BATCH SYNC ERROR] {e}")

        return batch_id

    def get_batch_logs(self, batch_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batch_logs WHERE batch_id = ? ORDER BY log_date ASC, created_at ASC", (batch_id,))
            return [dict(row) for row in cur.fetchall()]

    def add_batch_log(self, data: Dict[str, Any]) -> str:
        log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        batch_id = data.get("batch_id")
        log_type = data.get("log_type", "feed")
        qty = float(data.get("qty", 0))
        unit_price = float(data.get("unit_price", 0))
        total_amount = float(data.get("total_amount", qty * unit_price))

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, batch_id, data.get("farmer_id", ""), log_type,
                data.get("log_date", datetime.now().strftime("%Y-%m-%d")),
                data.get("item_id", ""), data.get("item_name", ""),
                qty, data.get("unit", ""), unit_price, total_amount,
                data.get("note", ""), now_str
            ))

            # Recalculate batch cumulative figures
            if log_type == "feed":
                cur.execute("""
                UPDATE batches SET
                    total_feed_bags = total_feed_bags + ?,
                    total_feed_cost = total_feed_cost + ?,
                    total_investment = total_investment + ?
                WHERE id = ?
                """, (qty, total_amount, total_amount, batch_id))
            elif log_type == "medicine":
                cur.execute("""
                UPDATE batches SET
                    total_med_cost = total_med_cost + ?,
                    total_investment = total_investment + ?
                WHERE id = ?
                """, (total_amount, total_amount, batch_id))
            elif log_type == "other_expense":
                cur.execute("""
                UPDATE batches SET
                    total_other_cost = total_other_cost + ?,
                    total_investment = total_investment + ?
                WHERE id = ?
                """, (total_amount, total_amount, batch_id))
            elif log_type == "mortality":
                cur.execute("""
                UPDATE batches SET
                    mortality_count = mortality_count + ?
                WHERE id = ?
                """, (int(qty), batch_id))

            # If inventory item_id was specified and log_type is feed or medicine, deduct from product stock
            item_id = data.get("item_id")
            if item_id and log_type in ["feed", "medicine"]:
                cur.execute("UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ? OR sku = ?",
                            (qty, now_str, item_id, item_id))

            # Update farmer due if it's an expense borne by SR Enterprise
            if total_amount > 0 and log_type in ["feed", "medicine", "other_expense"]:
                cur.execute("UPDATE farmers SET total_due = total_due + ? WHERE id = ?", (total_amount, data.get("farmer_id", "")))

            conn.commit()

        return log_id

    def close_and_settle_batch(self, batch_id: str, settlement_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates poultry shed harvest settlement:
        - Total birds sold
        - Total weight in KG
        - Average price / kg
        - Total bird revenue = Total Weight * Avg Price
        - Net Profit / Loss = Bird Revenue - Total SR Enterprise Investment
        - Dealer Recovery = Deducting SR Enterprise investment
        - Farmer Profit = Remaining amount paid to farmer
        """
        harvest_date = settlement_data.get("harvest_date", datetime.now().strftime("%Y-%m-%d"))
        birds_sold = int(settlement_data.get("birds_sold", 0))
        total_weight_kg = float(settlement_data.get("total_weight_kg", 0))
        rate_per_kg = float(settlement_data.get("rate_per_kg", 0))
        total_sale_amount = total_weight_kg * rate_per_kg

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            b = dict(cur.fetchone())
            total_inv = float(b["total_investment"])
            farmer_id = b["farmer_id"]

            net_profit = total_sale_amount - total_inv
            # Dealer recovers their investment from sales
            dealer_recovery = min(total_inv, total_sale_amount)
            # Remaining goes to farmer profit, or if deficit, farmer owes difference
            farmer_profit = total_sale_amount - dealer_recovery

            cur.execute("""
            UPDATE batches SET
                status = 'completed',
                harvest_date = ?,
                total_birds_sold = ?,
                total_weight_kg = ?,
                avg_rate_per_kg = ?,
                total_sale_amount = ?,
                net_profit = ?,
                dealer_recovery = ?,
                farmer_profit = ?,
                notes = COALESCE(notes, '') || ?
            WHERE id = ?
            """, (
                harvest_date, birds_sold, total_weight_kg, rate_per_kg,
                total_sale_amount, net_profit, dealer_recovery, farmer_profit,
                f" [শেড সম্পন্ন: বিক্রয় ৳{total_sale_amount:,.2f}, নীট লাভ: ৳{net_profit:,.2f}]",
                batch_id
            ))

            # Since the dealer recovers their investment from harvest revenue,
            # we credit the farmer's account with the dealer recovery amount!
            cur.execute("UPDATE farmers SET total_due = total_due - ? WHERE id = ?", (dealer_recovery, farmer_id))

            # Log the harvest event
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
            INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"LOG-{uuid.uuid4().hex[:8].upper()}", batch_id, farmer_id, "harvest",
                harvest_date, "", "মুরগী বিক্রয় ও শেড সম্পন্ন", total_weight_kg, "কেজি", rate_per_kg, total_sale_amount,
                f"মোট বিক্রয়: ৳{total_sale_amount:,.2f} | ডিলার সমন্বয়: ৳{dealer_recovery:,.2f} | খামারির লাভ: ৳{farmer_profit:,.2f}", now_str
            ))

            conn.commit()

            return {
                "batch_id": batch_id,
                "total_sale_amount": total_sale_amount,
                "total_investment": total_inv,
                "net_profit": net_profit,
                "dealer_recovery": dealer_recovery,
                "farmer_profit": farmer_profit
            }

    # ==================== INVOICES / DISPATCH ====================
    def get_invoices(self, farmer_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM invoices WHERE 1=1"
            params = []
            if farmer_id:
                query += " AND farmer_id = ?"
                params.append(farmer_id)
            query += " ORDER BY invoice_date DESC, created_at DESC LIMIT ?"
            params.append(limit)
            cur.execute(query, params)
            invoices = []
            for row in cur.fetchall():
                inv = dict(row)
                try:
                    inv["items"] = json.loads(inv["items_json"])
                except Exception:
                    inv["items"] = []
                invoices.append(inv)
            return invoices

    def get_invoice_by_id(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM invoices WHERE id = ? OR invoice_no = ?", (invoice_id, invoice_id))
            row = cur.fetchone()
            if not row:
                return None
            inv = dict(row)
            try:
                inv["items"] = json.loads(inv["items_json"])
            except Exception:
                inv["items"] = []
            return inv

    def create_invoice(self, data: Dict[str, Any]) -> str:
        invoice_id = f"INV-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        invoice_no = data.get("invoice_no") or f"SR-{datetime.now().strftime('%y%m')}-{uuid.uuid4().hex[:4].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items = data.get("items", [])
        subtotal = float(data.get("subtotal", 0))
        discount = float(data.get("discount", 0))
        net_total = float(data.get("net_total", subtotal - discount))
        paid_amount = float(data.get("paid_amount", 0))
        due_amount = float(data.get("due_amount", net_total - paid_amount))
        farmer_id = data.get("farmer_id", "")
        farmer_name = data.get("farmer_name", "")
        batch_id = data.get("batch_id")

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO invoices (
                id, invoice_no, farmer_id, farmer_name, batch_id, items_json,
                subtotal, discount, net_total, payment_type, paid_amount, due_amount,
                invoice_date, note, receipt_image_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id, invoice_no, farmer_id, farmer_name, batch_id, json.dumps(items, ensure_ascii=False),
                subtotal, discount, net_total, data.get("payment_type", "credit"), paid_amount, due_amount,
                data.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                data.get("note", ""), data.get("receipt_image_url", ""), now_str
            ))

            # Deduct items from inventory & add to batch logs if batch_id exists
            for it in items:
                prod_id = it.get("product_id") or it.get("id")
                qty = float(it.get("qty", 1))
                unit_price = float(it.get("price", 0))
                total_line = float(it.get("total", qty * unit_price))
                name = it.get("name") or it.get("name_bn") or "মালামাল"
                category = it.get("category", "")

                if prod_id:
                    cur.execute("UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ? OR sku = ?",
                                (qty, now_str, prod_id, prod_id))

                if batch_id:
                    log_type = "feed" if "খাদ্য" in category or "Feed" in category else "medicine"
                    cur.execute("""
                    INSERT INTO batch_logs (id, batch_id, farmer_id, log_type, log_date, item_id, item_name, qty, unit, unit_price, total_amount, note, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"LOG-{uuid.uuid4().hex[:8].upper()}", batch_id, farmer_id, log_type,
                        data.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
                        prod_id, name, qty, it.get("unit", "বস্তা"), unit_price, total_line,
                        f"চালান #{invoice_no}", now_str
                    ))
                    if log_type == "feed":
                        cur.execute("UPDATE batches SET total_feed_bags = total_feed_bags + ?, total_feed_cost = total_feed_cost + ?, total_investment = total_investment + ? WHERE id = ?",
                                    (qty, total_line, total_line, batch_id))
                    else:
                        cur.execute("UPDATE batches SET total_med_cost = total_med_cost + ?, total_investment = total_investment + ? WHERE id = ?",
                                    (total_line, total_line, batch_id))

            # Update farmer balance by due amount
            if due_amount > 0 and farmer_id:
                cur.execute("UPDATE farmers SET total_due = total_due + ? WHERE id = ?", (due_amount, farmer_id))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("invoices").document(invoice_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE INVOICE SYNC ERROR] {e}")

        return invoice_id

    # ==================== PAYMENTS ====================
    def get_payments(self, farmer_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM payments WHERE 1=1"
            params = []
            if farmer_id:
                query += " AND farmer_id = ?"
                params.append(farmer_id)
            query += " ORDER BY payment_date DESC, created_at DESC LIMIT ?"
            params.append(limit)
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def record_payment(self, data: Dict[str, Any]) -> str:
        payment_id = f"PAY-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        receipt_no = data.get("receipt_no") or f"REC-{datetime.now().strftime('%y%m')}-{uuid.uuid4().hex[:4].upper()}"
        amount = float(data.get("amount", 0))
        farmer_id = data.get("farmer_id", "")
        farmer_name = data.get("farmer_name", "")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO payments (id, receipt_no, farmer_id, farmer_name, batch_id, amount, payment_method, transaction_ref, voucher_image_url, payment_date, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment_id, receipt_no, farmer_id, farmer_name, data.get("batch_id"),
                amount, data.get("payment_method", "cash"), data.get("transaction_ref", ""),
                data.get("voucher_image_url", ""), data.get("payment_date", datetime.now().strftime("%Y-%m-%d")),
                data.get("note", ""), now_str
            ))

            # Deduct paid amount from farmer dues
            if farmer_id and amount > 0:
                cur.execute("UPDATE farmers SET total_due = total_due - ? WHERE id = ?", (amount, farmer_id))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("payments").document(payment_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE PAYMENT SYNC ERROR] {e}")

        return payment_id

    def get_payment_by_id(self, payment_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payments WHERE id = ? OR receipt_no = ?", (payment_id, payment_id))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_payment(self, payment_id: str, data: Dict[str, Any]) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
            old = cur.fetchone()
            if not old:
                return False
            old_payment = dict(old)
            old_amount = float(old_payment.get("amount", 0))
            farmer_id = old_payment.get("farmer_id")

            new_amount = float(data.get("amount", old_amount))
            delta = new_amount - old_amount

            cur.execute("""
            UPDATE payments SET
                amount = ?,
                payment_date = ?,
                payment_method = ?,
                transaction_ref = ?,
                note = ?
            WHERE id = ?
            """, (
                new_amount,
                data.get("payment_date", old_payment.get("payment_date")),
                data.get("payment_method", old_payment.get("payment_method")),
                data.get("transaction_ref", old_payment.get("transaction_ref", "")),
                data.get("note", old_payment.get("note", "")),
                payment_id
            ))

            # Adjust farmer's due (if paid amount increases, due decreases; if paid decreases, due increases)
            if delta != 0 and farmer_id:
                cur.execute("UPDATE farmers SET total_due = total_due - ? WHERE id = ?", (delta, farmer_id))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("payments").document(payment_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE PAYMENT UPDATE ERROR] {e}")
        return True

    def delete_payment(self, payment_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
            row = cur.fetchone()
            if not row:
                return False
            payment = dict(row)
            farmer_id = payment.get("farmer_id")
            amount = float(payment.get("amount", 0))

            cur.execute("DELETE FROM payments WHERE id = ?", (payment_id,))

            # Add back amount to farmer's total due
            if farmer_id and amount > 0:
                cur.execute("UPDATE farmers SET total_due = total_due + ? WHERE id = ?", (amount, farmer_id))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("payments").document(payment_id).delete()
            except Exception as e:
                print(f"[FIRESTORE PAYMENT DELETE ERROR] {e}")
        return True

    def update_invoice(self, invoice_id: str, data: Dict[str, Any]) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            row = cur.fetchone()
            if not row:
                return False
            old_inv = dict(row)
            farmer_id = old_inv.get("farmer_id")
            old_due = float(old_inv.get("due_amount", 0))

            subtotal = float(data.get("subtotal", old_inv.get("subtotal", 0)))
            discount = float(data.get("discount", old_inv.get("discount", 0)))
            net_total = float(data.get("net_total", subtotal - discount))
            paid_amount = float(data.get("paid_amount", old_inv.get("paid_amount", 0)))
            new_due = max(0.0, net_total - paid_amount)
            delta_due = new_due - old_due

            cur.execute("""
            UPDATE invoices SET
                invoice_date = ?,
                payment_type = ?,
                discount = ?,
                net_total = ?,
                paid_amount = ?,
                due_amount = ?,
                note = ?
            WHERE id = ?
            """, (
                data.get("invoice_date", old_inv.get("invoice_date")),
                data.get("payment_type", old_inv.get("payment_type", "credit")),
                discount, net_total, paid_amount, new_due,
                data.get("note", old_inv.get("note", "")),
                invoice_id
            ))

            if delta_due != 0 and farmer_id:
                cur.execute("UPDATE farmers SET total_due = total_due + ? WHERE id = ?", (delta_due, farmer_id))

            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("invoices").document(invoice_id).set(data, merge=True)
            except Exception as e:
                print(f"[FIRESTORE INVOICE UPDATE ERROR] {e}")
        return True

    def delete_invoice(self, invoice_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            row = cur.fetchone()
            if not row:
                return False
            invoice = dict(row)
            farmer_id = invoice.get("farmer_id")
            due_amount = float(invoice.get("due_amount", 0))
            batch_id = invoice.get("batch_id")
            invoice_no = invoice.get("invoice_no")

            # Restore product inventory stock
            try:
                items = json.loads(invoice.get("items_json", "[]"))
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for it in items:
                    prod_id = it.get("product_id") or it.get("id")
                    qty = float(it.get("qty", 0))
                    if prod_id and qty > 0:
                        cur.execute("UPDATE products SET stock = stock + ?, updated_at = ? WHERE id = ? OR sku = ?",
                                    (qty, now_str, prod_id, prod_id))
            except Exception as e:
                print(f"Error restoring stock during invoice delete: {e}")

            # Reconcile batch logs if invoice was tied to a batch
            if batch_id and invoice_no:
                cur.execute("SELECT * FROM batch_logs WHERE batch_id = ? AND note LIKE ?", (batch_id, f"%{invoice_no}%"))
                for rlog in cur.fetchall():
                    log_item = dict(rlog)
                    lamount = float(log_item.get("total_amount", 0))
                    lqty = float(log_item.get("qty", 0))
                    ltype = log_item.get("log_type")
                    if ltype == "feed":
                        cur.execute("UPDATE batches SET total_feed_bags = total_feed_bags - ?, total_feed_cost = total_feed_cost - ?, total_investment = total_investment - ? WHERE id = ?",
                                    (lqty, lamount, lamount, batch_id))
                    else:
                        cur.execute("UPDATE batches SET total_med_cost = total_med_cost - ?, total_investment = total_investment - ? WHERE id = ?",
                                    (lamount, lamount, batch_id))
                cur.execute("DELETE FROM batch_logs WHERE batch_id = ? AND note LIKE ?", (batch_id, f"%{invoice_no}%"))

            # Deduct due amount from farmer balance
            if farmer_id and due_amount > 0:
                cur.execute("UPDATE farmers SET total_due = total_due - ? WHERE id = ?", (due_amount, farmer_id))

            cur.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
            conn.commit()

        if self.is_firebase_active():
            try:
                _firestore_client.collection("invoices").document(invoice_id).delete()
            except Exception as e:
                print(f"[FIRESTORE INVOICE DELETE ERROR] {e}")
        return True

    def get_batch_log_by_id(self, log_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batch_logs WHERE id = ?", (log_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_batch_log(self, log_id: str, data: Dict[str, Any]) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batch_logs WHERE id = ?", (log_id,))
            row = cur.fetchone()
            if not row:
                return False
            old_log = dict(row)
            batch_id = old_log["batch_id"]
            old_type = old_log["log_type"]
            old_qty = float(old_log.get("qty", 0))
            old_amount = float(old_log.get("total_amount", 0))

            new_qty = float(data.get("qty", old_qty))
            new_unit_price = float(data.get("unit_price", old_log.get("unit_price", 0)))
            new_type = data.get("log_type", old_type)
            new_amount = 0.0 if new_type == "mortality" else (new_qty * new_unit_price)

            delta_amount = new_amount - old_amount
            delta_qty = new_qty - old_qty

            cur.execute("""
            UPDATE batch_logs SET
                log_date = ?,
                log_type = ?,
                item_name = ?,
                qty = ?,
                unit = ?,
                unit_price = ?,
                total_amount = ?,
                note = ?
            WHERE id = ?
            """, (
                data.get("log_date", old_log["log_date"]),
                new_type,
                data.get("item_name", old_log["item_name"]),
                new_qty,
                data.get("unit", old_log["unit"]),
                new_unit_price,
                new_amount,
                data.get("note", old_log.get("note", "")),
                log_id
            ))

            if new_type == "feed" and old_type == "feed":
                cur.execute("""
                UPDATE batches SET
                    total_feed_bags = total_feed_bags + ?,
                    total_feed_cost = total_feed_cost + ?,
                    total_investment = total_investment + ?
                WHERE id = ?
                """, (delta_qty, delta_amount, delta_amount, batch_id))
            elif new_type == "medicine" and old_type == "medicine":
                cur.execute("""
                UPDATE batches SET
                    total_med_cost = total_med_cost + ?,
                    total_investment = total_investment + ?
                WHERE id = ?
                """, (delta_amount, delta_amount, batch_id))
            elif new_type != "mortality":
                cur.execute("UPDATE batches SET total_investment = total_investment + ? WHERE id = ?", (delta_amount, batch_id))

            conn.commit()
        return True

    def delete_batch_log(self, log_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM batch_logs WHERE id = ?", (log_id,))
            row = cur.fetchone()
            if not row:
                return False
            log_item = dict(row)
            batch_id = log_item["batch_id"]
            ltype = log_item["log_type"]
            amount = float(log_item.get("total_amount", 0))
            qty = float(log_item.get("qty", 0))

            cur.execute("DELETE FROM batch_logs WHERE id = ?", (log_id,))

            if ltype == "feed":
                cur.execute("UPDATE batches SET total_feed_bags = total_feed_bags - ?, total_feed_cost = total_feed_cost - ?, total_investment = total_investment - ? WHERE id = ?",
                            (qty, amount, amount, batch_id))
            elif ltype == "medicine":
                cur.execute("UPDATE batches SET total_med_cost = total_med_cost - ?, total_investment = total_investment - ? WHERE id = ?",
                            (amount, amount, batch_id))
            elif ltype == "chick":
                cur.execute("UPDATE batches SET total_chick_cost = total_chick_cost - ?, total_investment = total_investment - ? WHERE id = ?",
                            (amount, amount, batch_id))
            elif ltype != "mortality":
                cur.execute("UPDATE batches SET total_investment = total_investment - ? WHERE id = ?", (amount, batch_id))

            conn.commit()
        return True

    # ==================== FEED REQUESTS ====================
    def get_feed_requests(self, farmer_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT * FROM feed_requests WHERE 1=1"
            params = []
            if farmer_id:
                query += " AND farmer_id = ?"
                params.append(farmer_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def create_feed_request(self, data: Dict[str, Any]) -> str:
        req_id = f"REQ-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO feed_requests (id, farmer_id, farmer_name, batch_id, items_requested, status, farmer_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req_id, data.get("farmer_id", ""), data.get("farmer_name", ""),
                data.get("batch_id", ""), data.get("items_requested", ""),
                "pending", data.get("farmer_note", ""), now_str
            ))
            conn.commit()
        return req_id

    def update_feed_request_status(self, req_id: str, status: str):
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE feed_requests SET status = ? WHERE id = ?", (status, req_id))
            conn.commit()

    # ==================== SETTINGS ====================
    def get_settings(self) -> Dict[str, str]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    def update_settings(self, settings_dict: Dict[str, str]):
        with self._get_connection() as conn:
            cur = conn.cursor()
            for k, v in settings_dict.items():
                cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
            conn.commit()


# Singleton database instance
db = DatabaseManager()
