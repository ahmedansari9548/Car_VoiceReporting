"""
app/core/constants.py

Constants for the buy flow.
"""

COLORS = [
    "White", "Silver", "Black", "Grey", "Blue", "Red", "Maroon",
    "Green", "Beige", "Gold", "Brown", "Yellow", "Orange", "Other",
]

COLOR_SYNONYMS = {
    "safed": "White", "sufaid": "White", "white": "White",
    "kaali": "Black", "kala": "Black", "black": "Black",
    "chandi": "Silver", "silver": "Silver",
    "neeli": "Blue", "neela": "Blue", "blue": "Blue",
    "laal": "Red", "red": "Red",
    "sabz": "Green", "hari": "Green", "green": "Green",
    "grey": "Grey", "gray": "Grey", "sleti": "Grey",
    "maroon": "Maroon", "gold": "Gold", "sunehri": "Gold",
    "white pearl": "White", "gun metallic": "Grey",
}

ENGINE_TYPES = ["Petrol", "Diesel", "Hybrid", "Electric", "CNG", "LPG"]
TRANSMISSIONS = ["Manual", "Automatic"]
ASSEMBLIES = ["Local", "Imported"]
BODY_TYPES = [
    "Sedan", "Hatchback", "SUV", "Crossover", "MPV", "Mini Van",
    "Double Cabin", "Pick Up", "Compact SUV",
]

SEARCH_SLUGS = {
    "make": "mk", "model": "md", "city": "ct",
    "price": "pr", "transmission": "tr",
    "body_type": "bt", "doors": "dr",
}

PAKWHEELS_SEARCH_BASE = "https://www.pakwheels.com/used-cars/search/-/"

SOURCE_SAID = "said"
SOURCE_DERIVED = "derived"