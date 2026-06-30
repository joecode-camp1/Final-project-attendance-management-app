# Final-Project--Group--2
# 📚 Attendance Management System

A modern web-based Attendance Management System built with **Flask** that enables administrators, teachers, and students to manage and track attendance efficiently. The system provides secure authentication, role-based access control, attendance analytics, and an intuitive user interface for educational institutions.

---

## 📖 Overview

Traditional attendance recording methods are often time-consuming, prone to errors, and difficult to manage. This project digitizes the attendance process by allowing teachers and administrators to record attendance electronically while also enabling students to submit their own attendance when permitted.

The application is designed using the **Model-View-Controller (MVC)** architecture to ensure scalability, maintainability, and clean code organization.

---

## ✨ Features

### 👨‍💼 Administrator

- Secure administrator login
- Dashboard with system overview
- Manage teachers
- Manage students
- Manage classes
- Approve student registrations
- View attendance statistics
- Generate attendance reports
- Manage user accounts

### 👨‍🏫 Teacher

- Secure login
- Dashboard
- Create and manage classes
- Mark student attendance manually
- View attendance history
- Generate attendance reports
- Monitor student attendance records

### 👨‍🎓 Student

- Secure login
- View enrolled classes
- Submit attendance (when enabled)
- View personal attendance history
- Monitor attendance percentage

---

## 🚀 Technologies Used

### Backend

- Python
- Flask
- SQLAlchemy
- Flask-Login
- Jinja2

### Frontend

- HTML5
- CSS3
- JavaScript
- Bootstrap

### Database

- SQLite (Development)
- PostgreSQL (Recommended for Production)

### Development Tools

- Git
- GitHub
- Visual Studio Code

---

## 🏗️ Project Structure

```
Attendance-Management-System/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── database/
│   └── __init__.py
│
├── migrations/
├── instance/
├── config.py
├── run.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/attendance-management-system.git
```

### 2. Navigate to the project

```bash
cd attendance-management-system
```

### 3. Create a virtual environment

Windows

```bash
python -m venv venv
```

Activate it

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the database

Run database migrations or initialize the database according to your project setup.

### 6. Start the application

```bash
python run.py
```

The application will be available at:


http://127.0.0.1:5000

---

## 🔐 User Roles

The system supports three user roles:

| Role | Permissions |
|------|-------------|
| Administrator | Full system management |
| Teacher | Attendance management and reporting |
| Student | Attendance submission and history |

---

## 📊 Core Modules

- Authentication
- User Management
- Class Management
- Attendance Recording
- Attendance Reports
- Student Approval
- Dashboard Analytics
- Profile Management

---

## 🎯 System Objectives

- Reduce manual attendance errors
- Improve attendance tracking efficiency
- Provide secure access using role-based authentication
- Enable quick report generation
- Improve record management for educational institutions

---

## 🔒 Security Features

- Password authentication
- Session management
- Role-based authorization
- Protected routes
- Secure database interactions using SQLAlchemy

---

## 📈 Future Improvements

- QR Code attendance
- Facial recognition attendance
- Email notifications
- SMS notifications
- Mobile application
- Export reports to Excel and PDF
- Real-time attendance analytics
- API integration

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push to your branch.
5. Open a Pull Request.

---

## 📄 License

This project is developed for educational purposes.

---

## 👨‍💻 Author

**Joseph Jedidiah Acquah

Cellusys CodeCamp

GitHub: https://github.com/joecode-camp1/Final-Project--Group--2

---

## ⭐ Acknowledgements

- Flask Documentation
- SQLAlchemy Documentation
- Bootstrap Documentation
- Open Source Community