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

# Performance optimizations
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_data(query, params=None):
    """Get cached data from database"""
    return execute_query(query, params, fetch=True)

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_financial_summary_cached():
    """Get cached financial summary"""
    return get_financial_summary()

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
    return get_cached_data("""
        SELECT id, name, position, phone, salary, hire_date, is_active
        FROM employees
        ORDER BY name
    """) or []

# الفواتير
def add_invoice(invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes):
    """إضافة فاتورة جديدة"""
    return execute_query("""
        INSERT INTO invoices (invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes))

def get_invoices():
    """جلب جميع الفواتير"""
    return get_cached_data("""
        SELECT id, invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, status, invoice_date, due_date
        FROM invoices
        ORDER BY invoice_date DESC
    """) or []

# الرواتب
def add_salary(employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes):
    """إضافة راتب موظف"""
    return execute_query("""
        INSERT INTO salaries (employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes))

def get_salaries():
    """جلب جميع الرواتب"""
    return get_cached_data("""
        SELECT s.id, e.name, s.month, s.year, s.basic_salary, s.overtime, s.bonuses, s.deductions, s.net_salary, s.payment_date, s.status
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        ORDER BY s.year DESC, s.month DESC
    """) or []

# المصاريف
def add_expense(expense_type, category, amount, description, payment_method, is_fixed, expense_date):
    """إضافة مصروف جديد"""
    return execute_query("""
        INSERT INTO expenses (expense_type, category, amount, description, payment_method, is_fixed, expense_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (expense_type, category, amount, description, payment_method, is_fixed, expense_date))

def get_expenses():
    """جلب جميع المصاريف"""
    return get_cached_data("""
        SELECT id, expense_type, category, amount, description, payment_method, is_fixed, expense_date
        FROM expenses
        ORDER BY expense_date DESC
    """) or []

# السحوبات
def add_withdrawal(amount, reason, withdrawal_date):
    """إضافة سحب جديد"""
    return execute_query("""
        INSERT INTO withdrawals (amount, reason, withdrawal_date)
        VALUES (%s, %s, %s)
    """, (amount, reason, withdrawal_date))

def get_withdrawals():
    """جلب جميع السحوبات"""
    return get_cached_data("""
        SELECT id, amount, reason, withdrawal_date
        FROM withdrawals
        ORDER BY withdrawal_date DESC
    """) or []

# الذمم
def add_account_receivable(customer_name, amount, due_date, notes):
    """إضافة ذمة جديدة"""
    return execute_query("""
        INSERT INTO accounts_receivable (customer_name, amount, due_date, notes)
        VALUES (%s, %s, %s, %s)
    """, (customer_name, amount, due_date, notes))

def get_accounts_receivable():
    """جلب جميع الذمم"""
    return get_cached_data("""
        SELECT id, customer_name, amount, due_date, status, notes
        FROM accounts_receivable
        ORDER BY due_date
    """) or []

# الإغلاق اليومي
def add_daily_closing(closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes):
    """إضافة إغلاق يومي"""
    return execute_query("""
        INSERT INTO daily_closing (closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes))

def get_daily_closings():
    """جلب جميع الإغلاقات اليومية"""
    return get_cached_data("""
        SELECT id, closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount
        FROM daily_closing
        ORDER BY closing_date DESC
    """) or []

# الإيداعات
def add_deposit(amount, deposit_type, bank_name, account_number, deposit_date, notes):
    """إضافة إيداع جديد"""
    return execute_query("""
        INSERT INTO deposits (amount, deposit_type, bank_name, account_number, deposit_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (amount, deposit_type, bank_name, account_number, deposit_date, notes))

def get_deposits():
    """جلب جميع الإيداعات"""
    return get_cached_data("""
        SELECT id, amount, deposit_type, bank_name, account_number, deposit_date, notes
        FROM deposits
        ORDER BY deposit_date DESC
    """) or []

# كشف الحساب
def add_account_statement_entry(transaction_date, description, debit, credit, balance, transaction_type, reference_id):
    """إضافة قيد في كشف الحساب"""
    return execute_query("""
        INSERT INTO account_statement (transaction_date, description, debit, credit, balance, transaction_type, reference_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (transaction_date, description, debit, credit, balance, transaction_type, reference_id))

def get_account_statement():
    """جلب كشف الحساب"""
    return get_cached_data("""
        SELECT id, transaction_date, description, debit, credit, balance, transaction_type, reference_id
        FROM account_statement
        ORDER BY transaction_date DESC
    """) or []

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
    st.title("💰 نظام المحاسبة الشامل")
    st.markdown("---")
    
    # Initialize database
    init_database()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("📋 القائمة الرئيسية")
        
        page = st.selectbox(
            "اختر الصفحة",
            [
                "🏠 الرئيسية",
                "👥 الموظفين",
                "📄 الفواتير",
                "💰 الرواتب",
                "💸 المصاريف",
                "🏧 السحوبات",
                "📊 الذمم",
                "🔒 الإغلاق اليومي",
                "🏦 الإيداعات",
                "📋 كشف الحساب"
            ]
        )
    
    # Main content area based on selected page
    if page == "🏠 الرئيسية":
        show_dashboard()
    elif page == "👥 الموظفين":
        show_employees()
    elif page == "📄 الفواتير":
        show_invoices()
    elif page == "💰 الرواتب":
        show_salaries()
    elif page == "💸 المصاريف":
        show_expenses()
    elif page == "🏧 السحوبات":
        show_withdrawals()
    elif page == "📊 الذمم":
        show_accounts_receivable()
    elif page == "🔒 الإغلاق اليومي":
        show_daily_closing()
    elif page == "🏦 الإيداعات":
        show_deposits()
    elif page == "📋 كشف الحساب":
        show_account_statement()

def show_dashboard():
    """عرض لوحة التحكم الرئيسية"""
    st.header("📊 لوحة التحكم الرئيسية")
    
    # Get financial summary with caching
    total_sales, total_expenses, total_withdrawals, total_salaries, total_deposits = get_financial_summary_cached()
    
    # Display key metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💰 إجمالي المبيعات", f"{total_sales:,.2f} د.ك")
    
    with col2:
        st.metric("💸 إجمالي المصاريف", f"{total_expenses:,.2f} د.ك")
    
    with col3:
        st.metric("🏧 إجمالي السحوبات", f"{total_withdrawals:,.2f} د.ك")
    
    with col4:
        st.metric("👥 إجمالي الرواتب", f"{total_salaries:,.2f} د.ك")
    
    with col5:
        st.metric("🏦 إجمالي الإيداعات", f"{total_deposits:,.2f} د.ك")
    
    # Net profit calculation
    net_profit = total_sales - total_expenses - total_withdrawals - total_salaries
    st.metric("📈 صافي الربح", f"{net_profit:,.2f} د.ك", delta=f"{net_profit:,.2f}")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Income vs Expenses chart
        fig = go.Figure(data=[
            go.Bar(name='الإيرادات', x=['المبيعات', 'الإيداعات'], y=[total_sales, total_deposits], marker_color='green'),
            go.Bar(name='المصاريف', x=['المصاريف', 'السحوبات', 'الرواتب'], y=[total_expenses, total_withdrawals, total_salaries], marker_color='red')
        ])
        fig.update_layout(title='الإيرادات مقابل المصاريف', barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Pie chart for expenses breakdown
        if total_expenses > 0 or total_withdrawals > 0 or total_salaries > 0:
            fig = px.pie(
                values=[total_expenses, total_withdrawals, total_salaries],
                names=['المصاريف', 'السحوبات', 'الرواتب'],
                title='توزيع المصاريف'
            )
            st.plotly_chart(fig, use_container_width=True)

def show_employees():
    """عرض صفحة الموظفين"""
    st.header("👥 إدارة الموظفين")
    
    # Add new employee form
    with st.expander("➕ إضافة موظف جديد"):
        with st.form("add_employee_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("اسم الموظف", placeholder="أدخل اسم الموظف...")
                position = st.text_input("المنصب", placeholder="أدخل المنصب...")
            
            with col2:
                phone = st.text_input("رقم الهاتف", placeholder="أدخل رقم الهاتف...")
                salary = st.number_input("الراتب", min_value=0.0, step=0.01)
            
            hire_date = st.date_input("تاريخ التوظيف", value=date.today())
            
            submitted = st.form_submit_button("إضافة موظف", type="primary")
            
            if submitted and name:
                if add_employee(name, position, phone, salary, hire_date):
                    st.success("تم إضافة الموظف بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الموظف. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display employees
    st.subheader("📋 قائمة الموظفين")
    employees = get_employees()
    
    if employees:
        df = pd.DataFrame(employees, columns=['ID', 'الاسم', 'المنصب', 'الهاتف', 'الراتب', 'تاريخ التوظيف', 'نشط'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا يوجد موظفين مسجلين بعد.")

def show_invoices():
    """عرض صفحة الفواتير"""
    st.header("📄 إدارة الفواتير")
    
    # Add new invoice form
    with st.expander("➕ إضافة فاتورة جديدة"):
        with st.form("add_invoice_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                invoice_number = st.text_input("رقم الفاتورة", placeholder="أدخل رقم الفاتورة...")
                customer_name = st.text_input("اسم العميل", placeholder="أدخل اسم العميل...")
                amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
                tax_amount = st.number_input("مبلغ الضريبة", min_value=0.0, step=0.01)
            
            with col2:
                total_amount = st.number_input("المبلغ الإجمالي", min_value=0.0, step=0.01)
                payment_method = st.selectbox("طريقة الدفع", ["نقداً", "فيزا", "شيك", "تحويل"])
                due_date = st.date_input("تاريخ الاستحقاق")
                notes = st.text_area("ملاحظات", placeholder="أدخل أي ملاحظات...")
            
            submitted = st.form_submit_button("إضافة فاتورة", type="primary")
            
            if submitted and invoice_number and customer_name:
                if add_invoice(invoice_number, customer_name, amount, tax_amount, total_amount, payment_method, due_date, notes):
                    st.success("تم إضافة الفاتورة بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الفاتورة. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display invoices
    st.subheader("📋 قائمة الفواتير")
    invoices = get_invoices()
    
    if invoices:
        df = pd.DataFrame(invoices, columns=['ID', 'رقم الفاتورة', 'اسم العميل', 'المبلغ', 'الضريبة', 'الإجمالي', 'طريقة الدفع', 'الحالة', 'تاريخ الفاتورة', 'تاريخ الاستحقاق'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد فواتير مسجلة بعد.")

def show_salaries():
    """عرض صفحة الرواتب"""
    st.header("💰 إدارة الرواتب")
    
    # Add new salary form
    with st.expander("➕ إضافة راتب موظف"):
        with st.form("add_salary_form"):
            employees = get_employees()
            if employees:
                employee_options = {f"{emp[1]} (ID: {emp[0]})": emp[0] for emp in employees}
                selected_employee = st.selectbox("اختر الموظف", list(employee_options.keys()))
                employee_id = employee_options[selected_employee]
            else:
                st.warning("لا يوجد موظفين مسجلين. يرجى إضافة موظفين أولاً.")
                employee_id = None
            
            col1, col2 = st.columns(2)
            
            with col1:
                month = st.selectbox("الشهر", list(range(1, 13)))
                year = st.number_input("السنة", min_value=2020, max_value=2030, value=date.today().year)
                basic_salary = st.number_input("الراتب الأساسي", min_value=0.0, step=0.01)
                overtime = st.number_input("ساعات إضافية", min_value=0.0, step=0.01)
            
            with col2:
                bonuses = st.number_input("المكافآت", min_value=0.0, step=0.01)
                deductions = st.number_input("الخصومات", min_value=0.0, step=0.01)
                net_salary = st.number_input("صافي الراتب", min_value=0.0, step=0.01)
                payment_date = st.date_input("تاريخ الدفع")
            
            notes = st.text_area("ملاحظات", placeholder="أدخل أي ملاحظات...")
            
            submitted = st.form_submit_button("إضافة راتب", type="primary")
            
            if submitted and employee_id:
                if add_salary(employee_id, month, year, basic_salary, overtime, bonuses, deductions, net_salary, payment_date, notes):
                    st.success("تم إضافة الراتب بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الراتب. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display salaries
    st.subheader("📋 قائمة الرواتب")
    salaries = get_salaries()
    
    if salaries:
        df = pd.DataFrame(salaries, columns=['ID', 'اسم الموظف', 'الشهر', 'السنة', 'الراتب الأساسي', 'ساعات إضافية', 'المكافآت', 'الخصومات', 'صافي الراتب', 'تاريخ الدفع', 'الحالة'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد رواتب مسجلة بعد.")

def show_expenses():
    """عرض صفحة المصاريف"""
    st.header("💸 إدارة المصاريف")
    
    # Add new expense form
    with st.expander("➕ إضافة مصروف جديد"):
        with st.form("add_expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                expense_type = st.selectbox("نوع المصروف", ["ثابت", "غير ثابت"])
                category = st.text_input("الفئة", placeholder="أدخل فئة المصروف...")
                amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
                description = st.text_area("الوصف", placeholder="أدخل وصف المصروف...")
            
            with col2:
                payment_method = st.selectbox("طريقة الدفع", ["نقداً", "فيزا", "شيك", "تحويل"])
                is_fixed = st.checkbox("مصروف ثابت")
                expense_date = st.date_input("تاريخ المصروف", value=date.today())
            
            submitted = st.form_submit_button("إضافة مصروف", type="primary")
            
            if submitted and category and amount:
                if add_expense(expense_type, category, amount, description, payment_method, is_fixed, expense_date):
                    st.success("تم إضافة المصروف بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة المصروف. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display expenses
    st.subheader("📋 قائمة المصاريف")
    expenses = get_expenses()
    
    if expenses:
        df = pd.DataFrame(expenses, columns=['ID', 'النوع', 'الفئة', 'المبلغ', 'الوصف', 'طريقة الدفع', 'ثابت', 'التاريخ'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد مصاريف مسجلة بعد.")

def show_withdrawals():
    """عرض صفحة السحوبات"""
    st.header("🏧 إدارة السحوبات")
    
    # Add new withdrawal form
    with st.expander("➕ إضافة سحب جديد"):
        with st.form("add_withdrawal_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
                reason = st.text_area("السبب", placeholder="أدخل سبب السحب...")
            
            with col2:
                withdrawal_date = st.date_input("تاريخ السحب", value=date.today())
            
            submitted = st.form_submit_button("إضافة سحب", type="primary")
            
            if submitted and amount and reason:
                if add_withdrawal(amount, reason, withdrawal_date):
                    st.success("تم إضافة السحب بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة السحب. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display withdrawals
    st.subheader("📋 قائمة السحوبات")
    withdrawals = get_withdrawals()
    
    if withdrawals:
        df = pd.DataFrame(withdrawals, columns=['ID', 'المبلغ', 'السبب', 'التاريخ'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد سحوبات مسجلة بعد.")

def show_accounts_receivable():
    """عرض صفحة الذمم"""
    st.header("📊 إدارة الذمم")
    
    # Add new account receivable form
    with st.expander("➕ إضافة ذمة جديدة"):
        with st.form("add_account_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                customer_name = st.text_input("اسم العميل", placeholder="أدخل اسم العميل...")
                amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
            
            with col2:
                due_date = st.date_input("تاريخ الاستحقاق")
                notes = st.text_area("ملاحظات", placeholder="أدخل أي ملاحظات...")
            
            submitted = st.form_submit_button("إضافة ذمة", type="primary")
            
            if submitted and customer_name and amount:
                if add_account_receivable(customer_name, amount, due_date, notes):
                    st.success("تم إضافة الذمة بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الذمة. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display accounts receivable
    st.subheader("📋 قائمة الذمم")
    accounts = get_accounts_receivable()
    
    if accounts:
        df = pd.DataFrame(accounts, columns=['ID', 'اسم العميل', 'المبلغ', 'تاريخ الاستحقاق', 'الحالة', 'ملاحظات'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد ذمم مسجلة بعد.")

def show_daily_closing():
    """عرض صفحة الإغلاق اليومي"""
    st.header("🔒 الإغلاق اليومي")
    
    # Add new daily closing form
    with st.expander("➕ إضافة إغلاق يومي جديد"):
        with st.form("add_closing_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                closing_date = st.date_input("تاريخ الإغلاق", value=date.today())
                cash_start = st.number_input("رصيد الكاش الابتدائي", min_value=0.0, step=0.01)
                cash_end = st.number_input("رصيد الكاش النهائي", min_value=0.0, step=0.01)
                visa_start = st.number_input("رصيد الفيزا الابتدائي", min_value=0.0, step=0.01)
                visa_end = st.number_input("رصيد الفيزا النهائي", min_value=0.0, step=0.01)
            
            with col2:
                total_sales = st.number_input("إجمالي المبيعات", min_value=0.0, step=0.01)
                total_expenses = st.number_input("إجمالي المصاريف", min_value=0.0, step=0.01)
                total_withdrawals = st.number_input("إجمالي السحوبات", min_value=0.0, step=0.01)
                net_amount = st.number_input("المبلغ الصافي", min_value=0.0, step=0.01)
                notes = st.text_area("ملاحظات", placeholder="أدخل أي ملاحظات...")
            
            submitted = st.form_submit_button("إضافة إغلاق يومي", type="primary")
            
            if submitted and closing_date:
                if add_daily_closing(closing_date, cash_start, cash_end, visa_start, visa_end, total_sales, total_expenses, total_withdrawals, net_amount, notes):
                    st.success("تم إضافة الإغلاق اليومي بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الإغلاق اليومي. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display daily closings
    st.subheader("📋 قائمة الإغلاقات اليومية")
    closings = get_daily_closings()
    
    if closings:
        df = pd.DataFrame(closings, columns=['ID', 'التاريخ', 'كاش ابتدائي', 'كاش نهائي', 'فيزا ابتدائي', 'فيزا نهائي', 'إجمالي المبيعات', 'إجمالي المصاريف', 'إجمالي السحوبات', 'المبلغ الصافي'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد إغلاقات يومية مسجلة بعد.")

def show_deposits():
    """عرض صفحة الإيداعات"""
    st.header("🏦 إدارة الإيداعات")
    
    # Add new deposit form
    with st.expander("➕ إضافة إيداع جديد"):
        with st.form("add_deposit_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                amount = st.number_input("المبلغ", min_value=0.0, step=0.01)
                deposit_type = st.selectbox("نوع الإيداع", ["وديعة", "تحويل", "شيك", "أخرى"])
                bank_name = st.text_input("اسم البنك", placeholder="أدخل اسم البنك...")
            
            with col2:
                account_number = st.text_input("رقم الحساب", placeholder="أدخل رقم الحساب...")
                deposit_date = st.date_input("تاريخ الإيداع", value=date.today())
                notes = st.text_area("ملاحظات", placeholder="أدخل أي ملاحظات...")
            
            submitted = st.form_submit_button("إضافة إيداع", type="primary")
            
            if submitted and amount:
                if add_deposit(amount, deposit_type, bank_name, account_number, deposit_date, notes):
                    st.success("تم إضافة الإيداع بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة الإيداع. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display deposits
    st.subheader("📋 قائمة الإيداعات")
    deposits = get_deposits()
    
    if deposits:
        df = pd.DataFrame(deposits, columns=['ID', 'المبلغ', 'النوع', 'اسم البنك', 'رقم الحساب', 'التاريخ', 'ملاحظات'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد إيداعات مسجلة بعد.")

def show_account_statement():
    """عرض صفحة كشف الحساب"""
    st.header("📋 كشف الحساب")
    
    # Add new account statement entry form
    with st.expander("➕ إضافة قيد جديد"):
        with st.form("add_statement_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                transaction_date = st.date_input("تاريخ المعاملة", value=date.today())
                description = st.text_area("الوصف", placeholder="أدخل وصف المعاملة...")
                debit = st.number_input("مدين", min_value=0.0, step=0.01)
            
            with col2:
                credit = st.number_input("دائن", min_value=0.0, step=0.01)
                balance = st.number_input("الرصيد", min_value=0.0, step=0.01)
                transaction_type = st.selectbox("نوع المعاملة", ["بيع", "شراء", "مصروف", "إيراد", "تحويل", "أخرى"])
                reference_id = st.number_input("رقم المرجع", min_value=0, step=1)
            
            submitted = st.form_submit_button("إضافة قيد", type="primary")
            
            if submitted and description:
                if add_account_statement_entry(transaction_date, description, debit, credit, balance, transaction_type, reference_id):
                    st.success("تم إضافة القيد بنجاح!")
                    # Clear cache and refresh
                    get_cached_data.clear()
                    st.rerun()
                else:
                    st.error("فشل في إضافة القيد. يرجى التحقق من الاتصال بقاعدة البيانات.")
    
    # Display account statement
    st.subheader("📋 كشف الحساب")
    statement = get_account_statement()
    
    if statement:
        df = pd.DataFrame(statement, columns=['ID', 'التاريخ', 'الوصف', 'مدين', 'دائن', 'الرصيد', 'نوع المعاملة', 'رقم المرجع'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد قيود مسجلة بعد.")

if __name__ == "__main__":
    main()
