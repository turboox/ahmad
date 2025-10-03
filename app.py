import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="نظام المحاسبة الشامل",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_db_connection():
    """Create and return a fresh database connection"""
    try:
        # Try to get connection from Streamlit secrets (for deployment)
        if 'connections' in st.secrets and 'postgres' in st.secrets['connections']:
            conn = psycopg2.connect(**st.secrets["connections"]["postgres"])
        else:
            # Fallback to environment variables (for local development)
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'taskmanager'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                port=os.getenv('DB_PORT', '5432')
            )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        return None

def execute_query(query, params=None, fetch=False):
    """Execute a database query with proper connection handling"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = True
            
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Database query failed: {str(e)}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# Initialize database tables
def init_database():
    """Create tables if they don't exist"""
    
    # الموظفين
    execute_query("""
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            position VARCHAR(255),
            phone VARCHAR(20),
            salary DECIMAL(10,2) DEFAULT 0,
            hire_date DATE DEFAULT CURRENT_DATE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # الفواتير
    execute_query("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            invoice_number VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            tax_amount DECIMAL(10,2) DEFAULT 0,
            total_amount DECIMAL(10,2) NOT NULL,
            payment_method VARCHAR(20) DEFAULT 'cash',
            status VARCHAR(20) DEFAULT 'pending',
            invoice_date DATE DEFAULT CURRENT_DATE,
            due_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # الرواتب
    execute_query("""
        CREATE TABLE IF NOT EXISTS salaries (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER REFERENCES employees(id),
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            basic_salary DECIMAL(10,2) NOT NULL,
            overtime DECIMAL(10,2) DEFAULT 0,
            bonuses DECIMAL(10,2) DEFAULT 0,
            deductions DECIMAL(10,2) DEFAULT 0,
            net_salary DECIMAL(10,2) NOT NULL,
            payment_date DATE,
            status VARCHAR(20) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # المصاريف
    execute_query("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            expense_type VARCHAR(50) NOT NULL,
            category VARCHAR(100) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            description TEXT,
            payment_method VARCHAR(20) DEFAULT 'cash',
            is_fixed BOOLEAN DEFAULT FALSE,
            expense_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # السحوبات
    execute_query("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id SERIAL PRIMARY KEY,
            amount DECIMAL(10,2) NOT NULL,
            reason TEXT NOT NULL,
            withdrawal_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # الذمم
    execute_query("""
        CREATE TABLE IF NOT EXISTS accounts_receivable (
            id SERIAL PRIMARY KEY,
            customer_name VARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            due_date DATE,
            status VARCHAR(20) DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # الإغلاق اليومي
    execute_query("""
        CREATE TABLE IF NOT EXISTS daily_closing (
            id SERIAL PRIMARY KEY,
            closing_date DATE UNIQUE NOT NULL,
            cash_start DECIMAL(10,2) DEFAULT 0,
            cash_end DECIMAL(10,2) DEFAULT 0,
            visa_start DECIMAL(10,2) DEFAULT 0,
            visa_end DECIMAL(10,2) DEFAULT 0,
            total_sales DECIMAL(10,2) DEFAULT 0,
            total_expenses DECIMAL(10,2) DEFAULT 0,
            total_withdrawals DECIMAL(10,2) DEFAULT 0,
            net_amount DECIMAL(10,2) DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # الإيداعات
    execute_query("""
        CREATE TABLE IF NOT EXISTS deposits (
            id SERIAL PRIMARY KEY,
            amount DECIMAL(10,2) NOT NULL,
            deposit_type VARCHAR(50) NOT NULL,
            bank_name VARCHAR(255),
            account_number VARCHAR(100),
            deposit_date DATE DEFAULT CURRENT_DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # كشف الحساب
    execute_query("""
        CREATE TABLE IF NOT EXISTS account_statement (
            id SERIAL PRIMARY KEY,
            transaction_date DATE NOT NULL,
            description TEXT NOT NULL,
            debit DECIMAL(10,2) DEFAULT 0,
            credit DECIMAL(10,2) DEFAULT 0,
            balance DECIMAL(10,2) NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            reference_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# CRUD operations for accounting system

# الموظفين
def add_employee(name, position, phone, salary, hire_date):
    """إضافة موظف جديد"""
    return execute_query("""
        INSERT INTO employees (name, position, phone, salary, hire_date)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, position, phone, salary, hire_date))

def get_employees():
    """جلب جميع الموظفين"""
    result = execute_query("""
        SELECT id, name, position, phone, salary, hire_date, is_active
        FROM employees
        ORDER BY name
    """, fetch=True)
    return result if result is not None else []

# الفواتير
def add_invoice(invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes):
    """إضافة فاتورة جديدة"""
    return execute_query("""
        INSERT INTO invoices (invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes))

def get_invoices():
    """جلب جميع الفواتير"""
    result = execute_query("""
        SELECT id, invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, status, invoice_date, due_date
        FROM invoices
        ORDER BY invoice_date DESC
    """, fetch=True)
    return result if result is not None else []

# الرواتب
def add_salary(employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes):
    """إضافة راتب موظف"""
    return execute_query("""
        INSERT INTO salaries (employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes))

def get_salaries():
    """جلب جميع الرواتب"""
    result = execute_query("""
        SELECT s.id, e.name, s.month, s.year, s.basic_salary, s.overtime, s.bonuses, s.deductions, s.net_salary, s.payment_date, s.status
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        ORDER BY s.year DESC, s.month DESC
    """, fetch=True)
    return result if result is not None else []

# المصاريف
def add_expense(expense_type, category, amount, description, payment_method, is_fixed, expense_date):
    """إضافة مصروف جديد"""
    return execute_query("""
        INSERT INTO expenses (expense_type, category, amount, description, payment_method, is_fixed, expense_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (expense_type, category, amount, description, payment_method, is_fixed, expense_date))

def get_expenses():
    """جلب جميع المصاريف"""
    result = execute_query("""
        SELECT id, expense_type, category, amount, description, payment_method, is_fixed, expense_date
        FROM expenses
        ORDER BY expense_date DESC
    """, fetch=True)
    return result if result is not None else []

# السحوبات
def add_withdrawal(amount, reason, withdrawal_date):
    """إضافة سحب جديد"""
    return execute_query("""
        INSERT INTO withdrawals (amount, reason, withdrawal_date)
        VALUES (%s, %s, %s)
    """, (amount, reason, withdrawal_date))

def get_withdrawals():
    """جلب جميع السحوبات"""
    result = execute_query("""
        SELECT id, amount, reason, withdrawal_date
        FROM withdrawals
        ORDER BY withdrawal_date DESC
    """, fetch=True)
    return result if result is not None else []

# الذمم
def add_account_receivable(customer_name, amount, due_date, notes):
    """إضافة ذمة جديدة"""
    return execute_query("""
        INSERT INTO accounts_receivable (customer_name, amount, due_date, notes)
        VALUES (%s, %s, %s, %s)
    """, (customer_name, amount, due_date, notes))

def get_accounts_receivable():
    """جلب جميع الذمم"""
    result = execute_query("""
        SELECT id, customer_name, amount, due_date, status, notes
        FROM accounts_receivable
        ORDER BY due_date
    """, fetch=True)
    return result if result is not None else []

# الإغلاق اليومي
def add_daily_closing(closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes):
    """إضافة إغلاق يومي"""
    return execute_query("""
        INSERT INTO daily_closing (closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes))

def get_daily_closings():
    """جلب جميع الإغلاقات اليومية"""
    result = execute_query("""
        SELECT id, closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount
        FROM daily_closing
        ORDER BY closing_date DESC
    """, fetch=True)
    return result if result is not None else []

# الإيداعات
def add_deposit(amount, deposit_type, bank_name, account_number, deposit_date, notes):
    """إضافة إيداع جديد"""
    return execute_query("""
        INSERT INTO deposits (amount, deposit_type, bank_name, account_number, deposit_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (amount, deposit_type, bank_name, account_number, deposit_date, notes))

def get_deposits():
    """جلب جميع الإيداعات"""
    result = execute_query("""
        SELECT id, amount, deposit_type, bank_name, account_number, deposit_date, notes
        FROM deposits
        ORDER BY deposit_date DESC
    """, fetch=True)
    return result if result is not None else []

# كشف الحساب
def add_account_statement_entry(transaction_date, description, debit, credit, balance, transaction_type, reference_id):
    """إضافة قيد في كشف الحساب"""
    return execute_query("""
        INSERT INTO account_statement (transaction_date, description, debit, credit, balance, transaction_type, reference_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (transaction_date, description, debit, credit, balance, transaction_type, reference_id))

def get_account_statement():
    """جلب كشف الحساب"""
    result = execute_query("""
        SELECT id, transaction_date, description, debit, credit, balance, transaction_type, reference_id
        FROM account_statement
        ORDER BY transaction_date DESC
    """, fetch=True)
    return result if result is not None else []

# الإحصائيات
def get_financial_summary():
    """جلب ملخص مالي"""
    result = execute_query("""
        SELECT 
            (SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE status = 'paid') as total_sales,
            (SELECT COALESCE(SUM(amount), 0) FROM expenses) as total_expenses,
            (SELECT COALESCE(SUM(amount), 0) FROM withdrawals) as total_withdrawals,
            (SELECT COALESCE(SUM(net_salary), 0) FROM salaries WHERE status = 'paid') as total_salaries,
            (SELECT COALESCE(SUM(amount), 0) FROM deposits) as total_deposits
    """, fetch=True)
    return result[0] if result and len(result) > 0 else (0, 0, 0, 0, 0)

# Main app
def main():
    st.title("📋 Personal Task Manager")
    st.markdown("---")
    
    # Initialize database
    init_database()
    
    # Sidebar for adding new tasks
    with st.sidebar:
        st.header("➕ Add New Task")
        
        with st.form("add_task_form"):
            title = st.text_input("Task Title", placeholder="Enter task title...")
            description = st.text_area("Description", placeholder="Enter task description...")
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
            due_date = st.date_input("Due Date", value=None)
            
            submitted = st.form_submit_button("Add Task", type="primary")
            
            if submitted and title:
                if add_task(title, description, priority, due_date):
                    st.success("Task added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add task. Please check your database connection.")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📝 Your Tasks")
        
        # Get and display tasks
        tasks = get_tasks()
        
        if tasks:
            for task in tasks:
                task_id, title, description, priority, status, due_date, created_at = task
                
                with st.container():
                    # Priority color coding
                    priority_colors = {
                        "Low": "🟢",
                        "Medium": "🟡", 
                        "High": "🟠",
                        "Urgent": "🔴"
                    }
                    
                    # Status color coding
                    status_colors = {
                        "Pending": "⚪",
                        "In Progress": "🟡",
                        "Completed": "🟢"
                    }
                    
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <h4>{priority_colors.get(priority, '⚪')} {title}</h4>
                        <p><strong>Status:</strong> {status_colors.get(status, '⚪')} {status}</p>
                        <p><strong>Priority:</strong> {priority}</p>
                        {f'<p><strong>Due Date:</strong> {due_date}</p>' if due_date else ''}
                        {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
                        <p><small>Created: {created_at.strftime("%Y-%m-%d %H:%M")}</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Task actions
                    col_a, col_b, col_c = st.columns([1, 1, 1])
                    
                    with col_a:
                        if st.button(f"✅ Complete", key=f"complete_{task_id}"):
                            update_task_status(task_id, "Completed")
                            st.rerun()
                    
                    with col_b:
                        if st.button(f"🔄 In Progress", key=f"progress_{task_id}"):
                            update_task_status(task_id, "In Progress")
                            st.rerun()
                    
                    with col_c:
                        if st.button(f"🗑️ Delete", key=f"delete_{task_id}"):
                            delete_task(task_id)
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No tasks yet. Add your first task using the sidebar!")
    
    with col2:
        st.header("📊 Statistics")
        
        # Get task statistics
        total, completed, pending, in_progress = get_task_stats()
        
        if total > 0:
            # Display stats
            st.metric("Total Tasks", total)
            st.metric("Completed", completed)
            st.metric("Pending", pending)
            st.metric("In Progress", in_progress)
            
            # Progress bar
            completion_rate = (completed / total) * 100 if total > 0 else 0
            st.progress(completion_rate / 100)
            st.caption(f"Completion Rate: {completion_rate:.1f}%")
            
            # Pie chart
            if total > 0:
                status_data = {
                    'Completed': completed,
                    'Pending': pending,
                    'In Progress': in_progress
                }
                
                fig = px.pie(
                    values=list(status_data.values()),
                    names=list(status_data.keys()),
                    title="Task Status Distribution",
                    color_discrete_map={
                        'Completed': '#28a745',
                        'Pending': '#ffc107',
                        'In Progress': '#17a2b8'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tasks to display statistics for yet!")

if __name__ == "__main__":
    main()
