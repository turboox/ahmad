# 📋 Personal Task Manager

A beautiful, functional Streamlit app for managing your personal tasks with a real database backend.

## Features

- ✅ Add, edit, and delete tasks
- 📊 Real-time statistics and progress tracking
- 🎨 Beautiful, responsive UI with color-coded priorities
- 📈 Interactive charts and progress bars
- 🔄 Status management (Pending, In Progress, Completed)
- 📅 Due date tracking
- 🏷️ Priority levels (Low, Medium, High, Urgent)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Database

Choose one of these free database options:

#### Option A: Neon.tech (Recommended - Free PostgreSQL)
1. Go to [neon.tech](https://neon.tech)
2. Sign up for free
3. Create a new project
4. Copy your connection string
5. Create a `.env` file with your credentials:

```env
DB_HOST=your-neon-host.neon.tech
DB_NAME=neondb
DB_USER=your-username
DB_PASSWORD=your-password
DB_PORT=5432
```

#### Option B: Supabase (Free PostgreSQL + API)
1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings > Database
4. Copy your connection details
5. Create a `.env` file with your credentials

#### Option C: Local PostgreSQL
If you have PostgreSQL installed locally:

```env
DB_HOST=localhost
DB_NAME=taskmanager
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432
```

### 3. Run the App

```bash
streamlit run app.py
```

Visit `http://localhost:8501` to see your app!

## Deployment to Streamlit Cloud

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/task-manager.git
git push -u origin main
```

### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select your repository
4. Add your database credentials in the Secrets section:

```toml
[connections.postgres]
host = "your-database-host.com"
database = "your-database-name"
user = "your-username"
password = "your-password"
port = 5432
```

### 3. Deploy!
Click "Deploy" and get your public URL!

## Database Schema

The app automatically creates these tables:

### Tasks Table
- `id` - Primary key
- `title` - Task title
- `description` - Task description
- `priority` - Low, Medium, High, Urgent
- `status` - Pending, In Progress, Completed
- `due_date` - Due date
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Categories Table
- `id` - Primary key
- `name` - Category name
- `color` - Hex color code
- `created_at` - Creation timestamp

## Free Database Options

| Service | Free Tier | PostgreSQL | Notes |
|---------|-----------|------------|-------|
| [Neon.tech](https://neon.tech) | ✅ | ✅ | 0.5GB storage, serverless |
| [Supabase](https://supabase.com) | ✅ | ✅ | 500MB storage, includes API |
| [Railway.app](https://railway.app) | ✅ | ✅ | $5 credit monthly |
| [PlanetScale](https://planetscale.com) | ✅ | ❌ | MySQL only, 1GB storage |

## Troubleshooting

### Database Connection Issues
- Check your `.env` file credentials
- Ensure your database is accessible from your IP
- For cloud databases, check if your IP is whitelisted

### Streamlit Cloud Deployment Issues
- Verify your `requirements.txt` includes all dependencies
- Check your secrets configuration in Streamlit Cloud
- Ensure your database allows connections from Streamlit Cloud IPs

## Contributing

Feel free to fork this project and add your own features!

## License

MIT License - feel free to use this for your own projects!
