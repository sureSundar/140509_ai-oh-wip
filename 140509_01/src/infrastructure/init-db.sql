-- PostgreSQL Database Initialization
-- AI-Powered Retail Inventory Optimization System

-- Create databases
CREATE DATABASE retailai;
CREATE DATABASE mlflow;

-- Connect to retailai database
\c retailai;

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Create stores table
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    population_density INTEGER,
    avg_income DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create suppliers table
CREATE TABLE suppliers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    lead_time_days INTEGER DEFAULT 7,
    minimum_order_qty INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create product categories table
CREATE TABLE product_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    parent_category_id UUID REFERENCES product_categories(id),
    seasonality_factor DECIMAL(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create products table
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category_id UUID REFERENCES product_categories(id),
    supplier_id UUID REFERENCES suppliers(id),
    cost_price DECIMAL(10, 2) NOT NULL,
    selling_price DECIMAL(10, 2) NOT NULL,
    weight_kg DECIMAL(8, 3),
    dimensions_cm VARCHAR(50),
    is_seasonal BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create inventory table
CREATE TABLE inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    store_id UUID REFERENCES stores(id) NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    reserved_stock INTEGER NOT NULL DEFAULT 0,
    min_stock_level INTEGER DEFAULT 10,
    max_stock_level INTEGER DEFAULT 100,
    reorder_point INTEGER DEFAULT 20,
    safety_stock INTEGER DEFAULT 5,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, store_id)
);

-- Create sales transactions table
CREATE TABLE sales_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    store_id UUID REFERENCES stores(id) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    transaction_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create forecasts table
CREATE TABLE forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    store_id UUID REFERENCES stores(id) NOT NULL,
    forecast_date DATE NOT NULL,
    forecast_horizon_days INTEGER NOT NULL,
    predicted_demand DECIMAL(10, 2) NOT NULL,
    confidence_lower DECIMAL(10, 2),
    confidence_upper DECIMAL(10, 2),
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, store_id, forecast_date, forecast_horizon_days)
);

-- Create reorder recommendations table
CREATE TABLE reorder_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) NOT NULL,
    store_id UUID REFERENCES stores(id) NOT NULL,
    recommended_quantity INTEGER NOT NULL,
    recommended_date DATE NOT NULL,
    urgency_level VARCHAR(20) DEFAULT 'medium',
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create alerts table
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    product_id UUID REFERENCES products(id),
    store_id UUID REFERENCES stores(id),
    is_read BOOLEAN DEFAULT false,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Create external data tables
CREATE TABLE weather_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID REFERENCES stores(id) NOT NULL,
    date DATE NOT NULL,
    temperature_avg DECIMAL(5, 2),
    temperature_min DECIMAL(5, 2),
    temperature_max DECIMAL(5, 2),
    humidity DECIMAL(5, 2),
    precipitation_mm DECIMAL(8, 2),
    weather_condition VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(store_id, date)
);

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    store_id UUID REFERENCES stores(id),
    impact_factor DECIMAL(3, 2) DEFAULT 1.0,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_sales_transactions_product_store_date ON sales_transactions(product_id, store_id, transaction_timestamp);
CREATE INDEX idx_inventory_product_store ON inventory(product_id, store_id);
CREATE INDEX idx_forecasts_product_store_date ON forecasts(product_id, store_id, forecast_date);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_alerts_unread ON alerts(is_read) WHERE is_read = false;

-- Insert sample data
INSERT INTO users (email, username, password_hash, role) VALUES
('admin@retailai.com', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6k8JsM.1yC', 'admin'),
('manager@retailai.com', 'manager', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6k8JsM.1yC', 'manager'),
('analyst@retailai.com', 'analyst', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6k8JsM.1yC', 'analyst');

INSERT INTO stores (name, city, state, latitude, longitude, population_density, avg_income) VALUES
('Downtown Store', 'New York', 'NY', 40.7128, -74.0060, 8000, 75000),
('Suburban Store', 'Los Angeles', 'CA', 34.0522, -118.2437, 3000, 65000),
('Mall Store', 'Chicago', 'IL', 41.8781, -87.6298, 4500, 70000);

INSERT INTO suppliers (name, contact_email, lead_time_days, minimum_order_qty) VALUES
('Global Electronics Corp', 'orders@globalelec.com', 14, 50),
('Fashion Wholesale Inc', 'supply@fashionwholesale.com', 7, 25),
('Home Goods Distributor', 'orders@homegoods.com', 10, 100);

INSERT INTO product_categories (name, seasonality_factor) VALUES
('Electronics', 1.0),
('Clothing', 1.5),
('Home & Garden', 1.2),
('Sports & Outdoors', 1.3);

-- Create functions and triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();