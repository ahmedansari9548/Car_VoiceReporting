CREATE TABLE IF NOT EXISTS sessions (
    id           TEXT PRIMARY KEY,
    phase        TEXT NOT NULL DEFAULT 'searching',
    language     TEXT NOT NULL DEFAULT 'roman_urdu',
    slots        JSONB NOT NULL DEFAULT '{}',
    selected_car JSONB,
    status       TEXT NOT NULL DEFAULT 'active',
    turn_count   INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS turns (
    id              SERIAL PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    turn_index      INTEGER NOT NULL,
    role            TEXT NOT NULL,
    text            TEXT,
    transcript_raw  TEXT,
    slots_extracted JSONB,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS corrections (
    id          SERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    turn_index  INTEGER,
    slot        TEXT NOT NULL,
    extracted   TEXT,
    corrected   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS inventory (
    id            SERIAL PRIMARY KEY,
    make          TEXT NOT NULL,
    model         TEXT NOT NULL,
    variant       TEXT,
    model_year    INTEGER NOT NULL,
    price         INTEGER NOT NULL,
    mileage_km    INTEGER,
    city          TEXT NOT NULL,
    transmission  TEXT,
    assembly      TEXT DEFAULT 'Local',
    body_type     TEXT,
    engine_cc     INTEGER,
    engine_type   TEXT DEFAULT 'Petrol',
    color         TEXT,
    image_url     TEXT,
    seller_type   TEXT DEFAULT 'Individual',
    registered_in TEXT
);

CREATE TABLE IF NOT EXISTS inspections (
    id             SERIAL PRIMARY KEY,
    session_id     TEXT NOT NULL,
    car_id         INTEGER REFERENCES inventory(id),
    car_details    JSONB NOT NULL,
    buyer_name     TEXT,
    buyer_phone    TEXT,
    preferred_date TEXT,
    preferred_time TEXT,
    location       TEXT,
    status         TEXT NOT NULL DEFAULT 'pending',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_inventory_make ON inventory(make, model);
CREATE INDEX IF NOT EXISTS idx_inventory_city ON inventory(city);
CREATE INDEX IF NOT EXISTS idx_inventory_price ON inventory(price);