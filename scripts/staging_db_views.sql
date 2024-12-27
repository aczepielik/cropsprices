CREATE OR REPLACE VIEW vegetables_year_over_year AS
WITH base_dates AS (
    -- Get the earliest date per week for each unique combination
    SELECT 
        TRIM(Product) as Product,
        CASE WHEN Unit = 'szt' THEN 'szt.' ELSE Unit END as Unit,
        Place,
        Origin,
        Statistic,
        Price,
        Date,
        EXTRACT(YEAR FROM Date) || '-' || EXTRACT(WEEK FROM Date) as year_week,
        ROW_NUMBER() OVER (
            PARTITION BY 
                TRIM(Product),
                CASE WHEN Unit = 'szt' THEN 'szt.' ELSE Unit END,
                Place, 
                Origin, 
                Statistic,
                EXTRACT(YEAR FROM Date) || '-' || EXTRACT(WEEK FROM Date)
            ORDER BY Date
        ) as rn
    FROM vegetables
),
current_prices AS (
    -- Select only the earliest date per week
    SELECT *
    FROM base_dates
    WHERE rn = 1
)
SELECT 
    c.Product,
    c.Unit,
    c.Place,
    c.Origin,
    c.Statistic,
    c.Date as current_date,
    c.Price as current_price,
    p.Date as year_ago_date,
    p.Price as year_ago_price
FROM current_prices c
LEFT JOIN current_prices p
    ON c.Product = p.Product
    AND c.Unit = p.Unit
    AND c.Place = p.Place
    AND c.Origin = p.Origin
    AND c.Statistic = p.Statistic
    AND EXTRACT(WEEK FROM c.Date) = EXTRACT(WEEK FROM p.Date)  -- Same week of year
    AND EXTRACT(YEAR FROM c.Date) = EXTRACT(YEAR FROM p.Date) + 1;   -- Previous year

CREATE OR REPLACE VIEW fruits_year_over_year AS
WITH base_dates AS (
    -- Get the earliest date per week for each unique combination
    SELECT 
        TRIM(Product) as Product,
        CASE WHEN Unit = 'szt' THEN 'szt.' ELSE Unit END as Unit,
        Place,
        Origin,
        Statistic,
        Price,
        Date,
        EXTRACT(YEAR FROM Date) || '-' || EXTRACT(WEEK FROM Date) as year_week,
        ROW_NUMBER() OVER (
            PARTITION BY 
                TRIM(Product),
                CASE WHEN Unit = 'szt' THEN 'szt.' ELSE Unit END,
                Place, 
                Origin, 
                Statistic,
                EXTRACT(YEAR FROM Date) || '-' || EXTRACT(WEEK FROM Date)
            ORDER BY Date
        ) as rn
    FROM fruits
),
current_prices AS (
    -- Select only the earliest date per week
    SELECT *
    FROM base_dates
    WHERE rn = 1
)
SELECT 
    c.Product,
    c.Unit,
    c.Place,
    c.Origin,
    c.Statistic,
    c.Date as current_date,
    c.Price as current_price,
    p.Date as year_ago_date,
    p.Price as year_ago_price
FROM current_prices c
LEFT JOIN current_prices p
    ON c.Product = p.Product
    AND c.Unit = p.Unit
    AND c.Place = p.Place
    AND c.Origin = p.Origin
    AND c.Statistic = p.Statistic
    AND EXTRACT(WEEK FROM c.Date) = EXTRACT(WEEK FROM p.Date)  -- Same week of year
    AND EXTRACT(YEAR FROM c.Date) = EXTRACT(YEAR FROM p.Date) + 1;   -- Previous year