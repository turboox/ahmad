import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Personal Task Manager",
    page_icon="📋",
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
    # Create tasks table
    execute_query("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            priority VARCHAR(20) DEFAULT 'Medium',
            status VARCHAR(20) DEFAULT 'Pending',
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create categories table
    execute_query("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            color VARCHAR(7) DEFAULT '#FF6B6B',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default categories
    execute_query("""
        INSERT INTO categories (name, color) 
        VALUES 
            ('Work', '#4ECDC4'),
            ('Personal', '#45B7D1'),
            ('Health', '#96CEB4'),
            ('Learning', '#FFEAA7')
        ON CONFLICT (name) DO NOTHING
    """)

# CRUD operations
def add_task(title, description, priority, due_date, category_id=None):
    """Add a new task"""
    return execute_query("""
        INSERT INTO tasks (title, description, priority, due_date)
        VALUES (%s, %s, %s, %s)
    """, (title, description, priority, due_date))

def get_tasks():
    """Get all tasks"""
    result = execute_query("""
        SELECT id, title, description, priority, status, due_date, created_at
        FROM tasks
        ORDER BY created_at DESC
    """, fetch=True)
    return result if result is not None else []

def update_task_status(task_id, new_status):
    """Update task status"""
    return execute_query("""
        UPDATE tasks 
        SET status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (new_status, task_id))

def delete_task(task_id):
    """Delete a task"""
    return execute_query("DELETE FROM tasks WHERE id = %s", (task_id,))

def get_task_stats():
    """Get task statistics"""
    result = execute_query("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status = 'Pending' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'In Progress' THEN 1 END) as in_progress
        FROM tasks
    """, fetch=True)
    return result[0] if result and len(result) > 0 else (0, 0, 0, 0)

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
