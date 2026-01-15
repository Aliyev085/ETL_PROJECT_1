CREATE TABLE IF NOT EXISTS bina_apartments (
    listing_id BIGINT PRIMARY KEY,

    url TEXT,
    title TEXT,

    price_azn INTEGER,
    area_sqm INTEGER,
    price_per_sqm FLOAT,

    rooms INTEGER,
    floor_current INTEGER,
    floor_total INTEGER,

    has_mortgage BOOLEAN,
    has_deed BOOLEAN,

    location_area TEXT,
    location_city TEXT,
    owned_type TEXT,

    posted_at TIMESTAMP,
    scraped_at TIMESTAMP,

    description TEXT,
    posted_by TEXT,
    contact_number TEXT,
    view_count INTEGER,
    is_constructed BOOLEAN,
    is_scraped BOOLEAN DEFAULT FALSE
);
