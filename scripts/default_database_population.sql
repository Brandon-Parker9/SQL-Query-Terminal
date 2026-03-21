\c insights_db

/* 2. CLEANUP (Optional: Resets the environment)
*/
DROP TABLE IF EXISTS saved_queries, sales_records, employees, departments CASCADE;

/* 3. CORE TABLE STRUCTURE
*/
-- Table 1: Departments
CREATE TABLE departments (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(50) NOT NULL,
    budget NUMERIC(12, 2)
);

-- Table 2: Employees (Depends on Departments)
CREATE TABLE employees (
    emp_id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    dept_id INT REFERENCES departments(dept_id),
    salary NUMERIC(10, 2),
    hire_date DATE
);

-- Table 3: Sales Records (Depends on Employees)
CREATE TABLE sales_records (
    sale_id SERIAL PRIMARY KEY,
    emp_id INT REFERENCES employees(emp_id),
    sale_amount NUMERIC(12, 2),
    sale_date DATE DEFAULT CURRENT_DATE
);

-- Table 4: Saved Queries for UI
CREATE TABLE saved_queries (
    id SERIAL PRIMARY KEY,
    query_name VARCHAR(255) NOT NULL,
    sql_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

/* 4. DATA POPULATION
*/
-- Departments
INSERT INTO departments (dept_name, budget) VALUES 
('Analytics', 500000.00), ('Marketing', 250000.00), ('IT Infrastructure', 750000.00),
('Human Resources', 150000.00), ('Sales & Distribution', 950000.00), ('Quality Assurance', 300000.00),
('Research & Development', 1200000.00), ('Legal', 450000.00), ('Customer Success', 200000.00);

-- Employees
INSERT INTO employees (first_name, last_name, dept_id, salary, hire_date) VALUES 
('James', 'Parker', 1, 85000, '2023-03-15'), ('Krista', 'Armstrong', 1, 92000, '2022-11-10'),
('Edward', 'Norton', 3, 105000, '2021-06-22'), ('Sarah', 'Jenks', 2, 65000, '2024-01-05'),
('Michael', 'Scott', 4, 75000, '2020-05-12'), ('Robert', 'Tables', 3, 115000, '2021-02-14'),
('Linda', 'Belcher', 5, 62000, '2023-08-01'), ('Arthur', 'Morgan', 6, 88000, '2020-01-10'),
('Dutch', 'VanDerLinde', 6, 155000, '2019-11-20'), ('Sadie', 'Adler', 7, 95000, '2022-04-12'),
('Pam', 'Beesly', 8, 55000, '2021-09-30'), ('Dwight', 'Schrute', 5, 98000, '2018-03-22'),
('Angela', 'Martin', 8, 72000, '2019-05-15'), ('Oscar', 'Martinez', 8, 82000, '2017-12-01'),
('Kim', 'Wexler', 9, 145000, '2020-08-19'), ('Mike', 'Ehrmantraut', 3, 120000, '2021-01-05'),
('Gus', 'Fring', 5, 250000, '2015-10-10'), ('Lalo', 'Salamanca', 6, 130000, '2022-11-01'),
('Charles', 'Leclerc', 7, 180000, '2023-01-15'), ('Lewis', 'Hamilton', 7, 210000, '2024-02-01');

-- Sales
INSERT INTO sales_records (emp_id, sale_amount, sale_date) VALUES 
(1, 1500.00, '2026-03-01'), (4, 3200.50, '2026-03-05'), (7, 450.00, '2026-03-10'),
(1, 2100.00, '2026-03-12'), (13, 8900.00, '2026-03-15'), (14, 12500.00, '2026-03-18'),
(15, 14000.00, '2026-03-19');

/* 5. PRESET BUSINESS QUERIES (UI SIDEBAR)
*/
INSERT INTO saved_queries (query_name, sql_text) VALUES 
-- Table Views
('View: All Departments', 'SELECT * FROM departments;'),
('View: All Employees', 'SELECT * FROM employees;'),
('View: All Sales Records', 'SELECT * FROM sales_records;'),
-- Business Insights
('Report: Full Employee Directory', 'SELECT e.first_name, e.last_name, d.dept_name, e.salary FROM employees e JOIN departments d ON e.dept_id = d.dept_id ORDER BY d.dept_name ASC;'),
('Report: Dept Budget vs Payroll', 'SELECT d.dept_name, d.budget, SUM(e.salary) as payroll FROM departments d JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_name, d.budget;'),
('Report: Top Sales Performance', 'SELECT e.first_name, e.last_name, SUM(s.sale_amount) as total_sales FROM employees e JOIN sales_records s ON e.emp_id = s.emp_id GROUP BY e.first_name, e.last_name ORDER BY total_sales DESC;'),
('Report: Average Salary by Dept', 'SELECT d.dept_name, ROUND(AVG(e.salary), 2) as avg_salary FROM departments d JOIN employees e ON d.dept_id = e.dept_id GROUP BY d.dept_name;');

GRANT CONNECT ON DATABASE insights_db TO read_only_user;
GRANT USAGE ON SCHEMA public TO read_only_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO read_only_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO read_only_user;

-- Finish
\q