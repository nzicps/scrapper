-- Run this ONCE in your Supabase SQL editor to create the table.
-- Go to: https://app.supabase.com → your project → SQL Editor → New Query

create table if not exists cars (
  id           bigserial primary key,
  unique_key   text unique not null,    -- "SBT Japan::AL1234" — prevents duplicates
  source       text,                    -- "SBT Japan", "BE FORWARD", etc.
  source_url   text,
  stock_id     text,
  title        text,
  year         int,
  make         text,
  model        text,
  price_jpy    int,
  price_nzd    int,
  mileage_km   int,
  engine_cc    int,
  fuel         text,
  drivetrain   text,
  transmission text,
  color        text,
  seats        int,
  doors        int,
  location     text,
  image_url    text,
  scraped_at   timestamptz default now()
);

-- Useful indexes for filtering/searching
create index if not exists idx_cars_make      on cars(make);
create index if not exists idx_cars_year      on cars(year);
create index if not exists idx_cars_price_nzd on cars(price_nzd);
create index if not exists idx_cars_source    on cars(source);
create index if not exists idx_cars_fuel      on cars(fuel);
