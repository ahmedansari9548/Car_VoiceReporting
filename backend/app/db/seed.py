"""
app/db/seed.py

Seeds the inventory table with sample cars for the buy flow.
Run once after init_db(). Safe to re-run — skips if data exists.
"""

from app.db.database import get_connection


SEED_DATA = [
    # Toyota Corolla
    ("Toyota", "Corolla", "GLi", 2019, 3200000, 68000, "Lahore", "Automatic", "Local", "Sedan", 1300, "Petrol", "White", "Individual", "Lahore"),
    ("Toyota", "Corolla", "GLi", 2020, 3500000, 42000, "Lahore", "Manual", "Local", "Sedan", 1300, "Petrol", "Silver", "Individual", "Lahore"),
    ("Toyota", "Corolla", "XLi", 2018, 2900000, 85000, "Karachi", "Manual", "Local", "Sedan", 1300, "Petrol", "White", "Individual", "Sindh"),
    ("Toyota", "Corolla", "Altis Grande", 2019, 4200000, 55000, "Islamabad", "Automatic", "Local", "Sedan", 1800, "Petrol", "Black", "Individual", "Islamabad"),
    ("Toyota", "Corolla", "Altis 1.6", 2020, 3800000, 38000, "Lahore", "Automatic", "Local", "Sedan", 1600, "Petrol", "Grey", "Dealer", "Lahore"),
    ("Toyota", "Corolla", "Altis X 1.6", 2022, 4500000, 22000, "Rawalpindi", "Automatic", "Local", "Sedan", 1600, "Petrol", "White", "Individual", "Rawalpindi"),
    ("Toyota", "Corolla", "GLi", 2017, 2700000, 95000, "Faisalabad", "Automatic", "Local", "Sedan", 1300, "Petrol", "Silver", "Individual", "Punjab"),

    # Honda Civic
    ("Honda", "Civic", "VTi Oriel", 2019, 4800000, 52000, "Lahore", "Automatic", "Local", "Sedan", 1800, "Petrol", "White", "Individual", "Lahore"),
    ("Honda", "Civic", "VTi Oriel UG", 2020, 5500000, 35000, "Lahore", "Automatic", "Local", "Sedan", 1500, "Petrol", "Black", "Individual", "Lahore"),
    ("Honda", "Civic", "VTi", 2018, 3900000, 72000, "Karachi", "Manual", "Local", "Sedan", 1800, "Petrol", "Grey", "Individual", "Karachi"),
    ("Honda", "Civic", "RS Turbo 1.5", 2020, 5800000, 40000, "Islamabad", "Automatic", "Local", "Sedan", 1500, "Petrol", "Red", "Individual", "Islamabad"),
    ("Honda", "Civic", "Oriel", 2023, 7200000, 15000, "Lahore", "Automatic", "Local", "Sedan", 1500, "Petrol", "White", "Dealer", "Lahore"),

    # Honda City
    ("Honda", "City", "1.3 i-VTEC", 2019, 2600000, 58000, "Lahore", "Manual", "Local", "Sedan", 1300, "Petrol", "White", "Individual", "Lahore"),
    ("Honda", "City", "Aspire 1.5", 2020, 3200000, 42000, "Karachi", "Automatic", "Local", "Sedan", 1500, "Petrol", "Silver", "Individual", "Sindh"),
    ("Honda", "City", "1.2L CVT", 2022, 3400000, 28000, "Rawalpindi", "Automatic", "Local", "Sedan", 1200, "Petrol", "White", "Individual", "Rawalpindi"),
    ("Honda", "City", "1.5L CVT Aspire", 2023, 4100000, 12000, "Lahore", "Automatic", "Local", "Sedan", 1500, "Petrol", "Grey", "Dealer", "Lahore"),

    # Suzuki Cultus
    ("Suzuki", "Cultus", "VXR", 2020, 2100000, 48000, "Lahore", "Manual", "Local", "Hatchback", 1000, "Petrol", "White", "Individual", "Lahore"),
    ("Suzuki", "Cultus", "VXL", 2021, 2400000, 35000, "Karachi", "Manual", "Local", "Hatchback", 1000, "Petrol", "Silver", "Individual", "Karachi"),
    ("Suzuki", "Cultus", "AGS", 2022, 2700000, 22000, "Islamabad", "Automatic", "Local", "Hatchback", 1000, "Petrol", "White", "Individual", "Islamabad"),
    ("Suzuki", "Cultus", "AGS", 2019, 2200000, 55000, "Faisalabad", "Automatic", "Local", "Hatchback", 1000, "Petrol", "Grey", "Individual", "Punjab"),

    # Suzuki Alto
    ("Suzuki", "Alto", "VXR", 2021, 1800000, 30000, "Lahore", "Manual", "Local", "Hatchback", 660, "Petrol", "White", "Individual", "Lahore"),
    ("Suzuki", "Alto", "VXL AGS", 2022, 2200000, 18000, "Karachi", "Automatic", "Local", "Hatchback", 660, "Petrol", "Blue", "Individual", "Sindh"),
    ("Suzuki", "Alto", "VX", 2020, 1500000, 45000, "Multan", "Manual", "Local", "Hatchback", 660, "Petrol", "White", "Individual", "Punjab"),

    # Suzuki Wagon R
    ("Suzuki", "Wagon R", "VXR", 2019, 2000000, 52000, "Lahore", "Manual", "Local", "Hatchback", 1000, "Petrol", "Silver", "Individual", "Lahore"),
    ("Suzuki", "Wagon R", "VXL", 2021, 2400000, 28000, "Karachi", "Manual", "Local", "Hatchback", 1000, "Petrol", "White", "Individual", "Karachi"),

    # Toyota Yaris
    ("Toyota", "Yaris", "GLI 1.3 MT", 2021, 2800000, 38000, "Lahore", "Manual", "Local", "Sedan", 1300, "Petrol", "White", "Individual", "Lahore"),
    ("Toyota", "Yaris", "ATIV 1.3 CVT", 2022, 3300000, 25000, "Islamabad", "Automatic", "Local", "Sedan", 1300, "Petrol", "Silver", "Individual", "Islamabad"),
    ("Toyota", "Yaris", "ATIV X 1.5 CVT", 2022, 3800000, 20000, "Rawalpindi", "Automatic", "Local", "Sedan", 1500, "Petrol", "White", "Dealer", "Rawalpindi"),

    # Toyota Vitz (Imported)
    ("Toyota", "Vitz", "F", 2015, 2100000, 78000, "Karachi", "Automatic", "Imported", "Hatchback", 1000, "Petrol", "Silver", "Individual", "Karachi"),
    ("Toyota", "Vitz", "Jewela", 2017, 2600000, 55000, "Lahore", "Automatic", "Imported", "Hatchback", 1000, "Petrol", "White", "Individual", "Lahore"),
    ("Toyota", "Vitz", "F Safety Edition", 2018, 2800000, 42000, "Islamabad", "Automatic", "Imported", "Hatchback", 1000, "Petrol", "Blue", "Individual", "Islamabad"),

    # Toyota Aqua (Imported Hybrid)
    ("Toyota", "Aqua", "S", 2017, 2900000, 65000, "Lahore", "Automatic", "Imported", "Hatchback", 1500, "Hybrid", "White", "Individual", "Lahore"),
    ("Toyota", "Aqua", "G", 2018, 3200000, 48000, "Karachi", "Automatic", "Imported", "Hatchback", 1500, "Hybrid", "Silver", "Individual", "Sindh"),

    # Toyota Prius (Imported Hybrid)
    ("Toyota", "Prius", "S", 2016, 3500000, 72000, "Islamabad", "Automatic", "Imported", "Hatchback", 1800, "Hybrid", "White", "Individual", "Islamabad"),
    ("Toyota", "Prius", "S Touring", 2018, 4200000, 45000, "Lahore", "Automatic", "Imported", "Hatchback", 1800, "Hybrid", "Silver", "Individual", "Lahore"),

    # KIA Sportage
    ("KIA", "Sportage", "Alpha", 2021, 6500000, 35000, "Lahore", "Automatic", "Local", "SUV", 2000, "Petrol", "White", "Individual", "Lahore"),
    ("KIA", "Sportage", "FWD", 2022, 7800000, 22000, "Islamabad", "Automatic", "Local", "SUV", 2000, "Petrol", "Black", "Individual", "Islamabad"),
    ("KIA", "Sportage", "AWD", 2021, 8200000, 30000, "Karachi", "Automatic", "Local", "SUV", 2000, "Petrol", "Grey", "Dealer", "Sindh"),

    # Changan Alsvin
    ("Changan", "Alsvin", "1.3 Comfort DCT", 2022, 3000000, 25000, "Lahore", "Automatic", "Local", "Sedan", 1300, "Petrol", "White", "Individual", "Lahore"),
    ("Changan", "Alsvin", "1.5 Lumiere", 2023, 3800000, 12000, "Karachi", "Automatic", "Local", "Sedan", 1500, "Petrol", "Black", "Individual", "Sindh"),
    ("Changan", "Alsvin", "1.3 Comfort MT", 2022, 2700000, 30000, "Faisalabad", "Manual", "Local", "Sedan", 1300, "Petrol", "Silver", "Individual", "Punjab"),

    # Honda BR-V
    ("Honda", "BR-V", "i-VTEC S", 2022, 4800000, 28000, "Lahore", "Automatic", "Local", "Crossover", 1500, "Petrol", "White", "Individual", "Lahore"),
    ("Honda", "BR-V", "i-VTEC S", 2020, 4200000, 48000, "Karachi", "Automatic", "Local", "Crossover", 1500, "Petrol", "Grey", "Individual", "Sindh"),

    # Toyota Fortuner
    ("Toyota", "Fortuner", "2.7 G", 2019, 8500000, 55000, "Lahore", "Automatic", "Local", "SUV", 2700, "Petrol", "White", "Individual", "Lahore"),
    ("Toyota", "Fortuner", "Sigma 4", 2021, 12000000, 30000, "Islamabad", "Automatic", "Local", "SUV", 2800, "Diesel", "Black", "Dealer", "Islamabad"),
    ("Toyota", "Fortuner", "Legender", 2023, 15000000, 12000, "Karachi", "Automatic", "Local", "SUV", 2800, "Diesel", "White", "Dealer", "Sindh"),

    # Hyundai Tucson
    ("Hyundai", "Tucson", "GLS Sport", 2022, 7500000, 25000, "Lahore", "Automatic", "Local", "SUV", 2000, "Petrol", "Grey", "Individual", "Lahore"),
    ("Hyundai", "Tucson", "Ultimate", 2023, 8800000, 15000, "Islamabad", "Automatic", "Local", "SUV", 2000, "Petrol", "Black", "Dealer", "Islamabad"),

    # Suzuki Swift
    ("Suzuki", "Swift", "DLX", 2019, 2300000, 48000, "Karachi", "Manual", "Local", "Hatchback", 1300, "Petrol", "Red", "Individual", "Karachi"),
    ("Suzuki", "Swift", "GLX CVT", 2023, 3400000, 10000, "Lahore", "Automatic", "Local", "Hatchback", 1200, "Petrol", "White", "Dealer", "Lahore"),

    # Suzuki Mehran
    ("Suzuki", "Mehran", "VXR", 2018, 950000, 120000, "Multan", "Manual", "Local", "Hatchback", 800, "Petrol", "White", "Individual", "Punjab"),
    ("Suzuki", "Mehran", "VX", 2015, 750000, 150000, "Faisalabad", "Manual", "Local", "Hatchback", 800, "Petrol", "Silver", "Individual", "Punjab"),
]


def seed_inventory() -> None:
    """Insert sample cars if the table is empty."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM inventory")
    count = cur.fetchone()[0]

    if count > 0:
        print(f"  inventory already has {count} rows — skipping seed")
        cur.close()
        conn.close()
        return

    for row in SEED_DATA:
        image_url = ""  # filled by scripts/fetch_images.py

        cur.execute(
            "INSERT INTO inventory "
            "(make, model, variant, model_year, price, mileage_km, city, "
            "transmission, assembly, body_type, engine_cc, engine_type, "
            "color, seller_type, registered_in, image_url) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            row + (image_url,),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"  seeded {len(SEED_DATA)} cars into inventory")