# Notification System Api

A robust and scalable Django-based API for handling email and real-time in-app notifications. This system provides core functionalities for user management, article creation, and a flexible notification delivery mechanism via a database queue and asynchronous workers, leveraging Django Channels for real-time communication.

## ✨ Features

- **User Authentication & Management**: Secure user registration and email verification flows.
- **Article Management**: Authenticated users can create and manage articles.
- **Asynchronous Email Notifications**: Deliver transactional and informational emails.
- Real-time In-App Notifications: Push instant notifications to users via WebSockets using Django Channels.
- Configurable Communication Preferences: Users can opt-in or opt-out of specific notification channels (Email, In-App).
- **Database Queue for Notifications**: Utilizes a `NotificationJob` model to queue notifications for reliable, asynchronous processing by a background worker.
- **Extensible Delivery Handlers**: Easily add new notification channels (e.g., SMS, Push) by implementing a simple abstract interface.
- **JWT-based Email Verification**: Securely handle email verification with JSON Web Tokens.
- **API Documentation**: Integrated OpenAPI/Swagger documentation for easy API exploration and testing using `drf-spectacular`.

## 🏗️ Project Structure

The repository is organized into several Django applications and a core project configuration, following best practices for modularity:

```folders
notification_system_api/
├── README.md
├── LICENSE
├── manage.py                   # Django's command-line utility
├── requirements.txt            # Project dependencies
├── apis/                       # Handles API endpoints (auth, articles)
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── articles/                   # Manages article models and related logic
│   └── models.py
├── notification_system_api/    # Core Django project settings, ASGI, WSGI
│   ├── asgi.py                 # ASGI configuration for Channels
│   ├── settings.py
│   └── urls.py                 # Main URL routing for the project
├── notifications_app/          # Core notification logic
│   ├── models.py               # Defines NotificationJob, UserCommunicationPreference
│   ├── consumers.py            # Handles WebSocket connections for in-app notifications
│   ├── receiver.py             # Signal receivers for enqueuing notifications
│   ├── routing.py              # WebSocket URL routing
│   ├── utils.py                # JWT utilities for email verification
│   ├── backends/               # Notification backend implementations
│   │   ├── database_queue.py   # Database queue backend
│   │   └── notifications_abc.py# Abstract base for notification backends
│   ├── delivery_handlers/      # Specific notification delivery mechanisms
│   |   ├── delivery_handler_abc.py # Abstract base for delivery handlers
│   |   ├── email_handler.py    # Handles sending emails
│   |   └── in_app_handler.py   # Handles sending in-app messages via Channels
│   └── management/
│       └── commands/
│           └── run_notification_worker.py # Custom command to run the notification worker
└── users/                      # Custom user model and related logic
    └── models.py
```

## ⚙️ Getting Started

Follow these steps to set up the project locally for development.

### Prerequisites

- Python 3.10+
- Git
- (Optional but Recommended for Production) Redis: For a production-grade Channels layer. Currently configured for in-memory, but Redis is robust.

### Installation

1. Clone the repository:

```bash
git clone https://github.com/igboke/notification_system_api.git
cd notification_system_api
```

2.Create and activate a virtual environment:

```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3.Install dependencies:

```bash
pip install -r requirements.txt
```

4.Set up Environment Variables:

Create a `.env` file in the root of your project directory (`notification_system_api/`) and add the following:

```ini,TOML
DJANGO_SECRET_KEY='your_very_secret_key_here'

# Email Settings (for EmailDeliveryHandler)
DEFAULT_FROM_EMAIL='your_email@example.com'
EMAIL_HOST='smtp.yourprovider.com'
EMAIL_HOST_USER='your_smtp_username'
EMAIL_HOST_PASSWORD='your_smtp_password'
```

5.Run Database Migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

6.Create a Superuser (for Admin panel access):

```bash
python manage.py createsuperuser
```

## 🚀 Running the Project

This project involves running multiple components: the Django web server, the Django Channels server (Daphne), and a custom notification worker.

1.Start the Django Development Server:

```bash
python manage.py runserver
```

This will run the HTTP API (e.g., user registration, article creation)

2.Start the Django Channels Server (Daphne, Optional(for production)):
When you use python manage.py runserver, the manage.py script automatically handles setting the DJANGO_SETTINGS_MODULE environment variable for you, pointing to your project's settings.py file.
In a *new terminal*, activate your virtual environment and run:

```bash
daphne -b 0.0.0.0 -p 8001 notification_system_api.asgi:application
```

This will serve the WebSocket connections for real-time in-app notifications. Adjust the port (-p) if needed.

3.Start the Notification Worker:
In another new terminal, activate your virtual environment and run the custom management command:

```bash
python manage.py run_notification_worker
```

This worker polls the `NotificationJob` table and dispatches notifications via the appropriate handlers (email, in-app)
