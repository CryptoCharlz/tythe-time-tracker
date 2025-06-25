# 🚀 Supabase Setup Guide (For Beginners)

This guide will help you set up a free Supabase database and connect it to The Tythe Barn Time Tracker app. No technical experience needed!

---

## 1. Create a Free Supabase Account

1. Go to [https://supabase.com/](https://supabase.com/)
2. Click **Start your project** (top right)
3. Sign up with your email and create a password

---

## 2. Create a New Project

1. After logging in, click the **New project** button
2. **Project Name:** (anything you like, e.g. `tythe-time-tracker`)
3. **Password:** Create a strong password (write it down!)
4. **Region:** Choose the default or your closest region
5. Click **Create new project**

*Wait a minute for your project to be ready.*

---

## 3. Get Your Database Credentials

1. In your Supabase project, click **Settings** (left menu)
2. Click **Database**
3. Scroll down to **Connection string** section
4. **Choose "Direct connection"** (not pooler)
5. You'll see a connection string that looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.abc123.supabase.co:5432/postgres
   ```

**Extract these values:**
- **Host:** `db.abc123.supabase.co` (the part after @ and before :5432)
- **Database:** `postgres`
- **User:** `postgres`
- **Password:** `[YOUR-PASSWORD]` (the password you set)
- **Port:** `5432`

---

## 4. Fill in the `.env` File

1. In your project folder, find the file called `env.example`
2. Make a copy and rename it to `.env` (just remove `example`)
3. Open `.env` in a text editor
4. Fill in the values from your Supabase project:

```
SUPABASE_HOST=db.abc123.supabase.co
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your-database-password
SUPABASE_PORT=5432
MANAGER_PASSWORD=tythe2024
```

Replace the values after `=` with your actual details.

---

## 5. Save and Close `.env`

- Make sure to **save** the file after editing.
- **Never share** your `.env` file with anyone else!

---

## 6. Test the Connection

1. Open a terminal (or ask for help)
2. Run:
   ```
   python test_connection.py
   ```
3. You should see messages like:
   - `✅ Database connection successful!`
   - `✅ Table creation/verification successful!`
   - `🎉 All tests passed! Your database is ready to use.`

If you see errors, double-check your `.env` values.

---

## 7. Run the App!

1. In the terminal, run:
   ```
   streamlit run app.py
   ```
2. The app will open in your browser (usually at [http://localhost:8501](http://localhost:8501))
3. Try clocking in, clocking out, and using the manager dashboard!

---

## 💡 Need Help?
- Ask a friend or the developer for help if you get stuck
- Supabase has a friendly [Discord community](https://discord.supabase.com/)

---

**You did it! 🎉**

*Built for The Tythe Barn* 