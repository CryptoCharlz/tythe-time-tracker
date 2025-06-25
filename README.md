# 🕒 The Tythe Barn - Time Tracker

A simple, web-based time tracking system for employees at The Tythe Barn to clock in/out and for managers to view and manage timesheets.

## ✨ Features

### 👤 Employee Features
- **Simple Clock In/Out**: Just enter your name and click to clock in or out
- **Duplicate Prevention**: Prevents multiple open shifts for the same employee
- **Quick Status**: See if you're currently clocked in
- **Personal Timesheet**: View your own time entries with dates, times, and durations

### 👨‍💼 Manager Features
- **Password Protection**: Secure access to manager dashboard
- **All Entries View**: See time entries from all employees
- **Delete Functionality**: Remove incorrect entries
- **Real-time Updates**: Data refreshes automatically

## 🚀 Quick Start

### 1. Set Up Supabase Database

1. Go to [Supabase](https://supabase.com) and create a free account
2. Create a new project
3. Go to Settings → Database to get your connection details
4. Copy the connection string details

### 2. Configure Environment Variables

1. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your Supabase credentials:
   ```env
   SUPABASE_HOST=your-project-ref.supabase.co
   SUPABASE_DATABASE=postgres
   SUPABASE_USER=postgres
   SUPABASE_PASSWORD=your-database-password
   SUPABASE_PORT=5432
   MANAGER_PASSWORD=tythe2024
   ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## 🌐 Deployment to Streamlit Cloud

1. Push your code to a GitHub repository
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub account
4. Deploy your app by selecting the repository
5. Add your environment variables in the Streamlit Cloud dashboard

## 📊 Database Schema

The app automatically creates the required table:

```sql
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee TEXT NOT NULL,
    clock_in TIMESTAMPTZ NOT NULL,
    clock_out TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔧 Configuration

### Manager Password
Change the default manager password by setting the `MANAGER_PASSWORD` environment variable.

### Database Connection
All database connection parameters are configurable via environment variables:
- `SUPABASE_HOST`: Your Supabase project host
- `SUPABASE_DATABASE`: Database name (usually 'postgres')
- `SUPABASE_USER`: Database user (usually 'postgres')
- `SUPABASE_PASSWORD`: Your database password
- `SUPABASE_PORT`: Database port (usually 5432)

## 📱 Mobile-Friendly

The app is designed to work well on mobile devices through web browsers. Employees can easily clock in/out from their phones.

## 🔒 Security Notes

- This MVP uses simple password protection for the manager dashboard
- No user accounts are required - employees just enter their names
- All data is stored in Supabase (PostgreSQL)
- Consider implementing proper authentication for production use

## 🛠️ Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **Database**: Supabase (PostgreSQL)
- **Hosting**: Streamlit Community Cloud
- **Database Client**: psycopg2

## 📝 Usage Instructions

### For Employees:
1. Navigate to "Employee Clock In/Out"
2. Enter your full name
3. Click "Clock In" to start a shift
4. Click "Clock Out" to end your shift
5. Use "Personal Timesheet" to view your history

### For Managers:
1. Navigate to "Manager Dashboard"
2. Enter the manager password
3. View all employee time entries
4. Delete incorrect entries by entering the Entry ID

## 🐛 Troubleshooting

### Database Connection Issues
- Verify your Supabase credentials in the `.env` file
- Ensure your Supabase project is active
- Check that your IP is allowed in Supabase settings

### App Not Starting
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that the `.env` file exists and has correct values
- Verify Python version compatibility (3.7+)

## 📈 Future Enhancements

- User authentication system
- Export functionality (CSV, PDF)
- Payroll integration
- Break time tracking
- Shift scheduling
- Mobile app version

## 🤝 Contributing

This is an MVP for The Tythe Barn. For questions or improvements, please contact the development team.

---

**Built with ❤️ for The Tythe Barn** 