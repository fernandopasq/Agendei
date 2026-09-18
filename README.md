# Agendei

*Read this in other languages: [Português](README.pt-BR.md)*

## 1. Overview

**Agendei** is a web application designed for service discovery and appointment scheduling. It bridges the gap between clients, local businesses, and independent service providers by allowing each appointment to have a specified service, duration, date, time, and assigned professional.

Developed as the final capstone project for Harvard's **CS50** course, the application focuses on Python, Flask, SQL, authentication, HTML, CSS, and JavaScript.

There are two main user roles:

- **Client:** Searches for local businesses, selects services and professionals, checks available time slots, books appointments, tracks upcoming bookings, and cancels future appointments.
- **Partner (Owner/Provider):** Registers business locations, creates service offerings with specific durations, manages staff/providers, and tracks their own service schedule.

The application also features a shared Profile page where both clients and partners can edit personal information, phone numbers, and update passwords (requiring current password verification).

---

## 2. Core Workflows

<details>
  <summary><b>Client Workflow</b> (Click to expand)</summary>

1. Access the home page.
2. Filter business locations by state, city, neighborhood, and category.
3. Select a business and a specific service.
4. Choose a specific service provider or opt for any available professional.
5. Pick a date using the interactive date picker.
6. Select an available time slot (calculated dynamically based on service duration and current time).
7. Confirm the booking.
8. View or cancel the appointment under **My Appointments**.
</details>

<details>
  <summary><b>Partner Workflow</b> (Click to expand)</summary>

1. Create a partner account.
2. Register a business along with contact details and address.
3. Create services specifying price and duration in minutes.
4. Join the business team as either an owner or provider.
5. Link specific services to the provider’s profile.
6. Track bookings in the provider's personal schedule view.
7. Manage staff, services, and account details.
</details>

---

## 3. Tech Stack

<details>
  <summary><b>Backend Technologies</b> (Click to expand)</summary>

- **Python:** Primary programming language.
- **Flask:** Web framework handling routing, templates, and request processing.
- **Flask-Session:** Handles server-side session storage using local files.
- **Werkzeug:** Secure password hashing and verification using `generate_password_hash` and `check_password_hash`.
- **SQLite:** Relational database for local data storage.

*Python dependencies are listed in `requirements.txt`. SQLite is part of the Python standard library, while Werkzeug and Jinja2 are installed automatically alongside Flask.*
</details>

<details>
  <summary><b>Frontend Technologies</b> (Click to expand)</summary>

- **HTML with Jinja:** Dynamic templates rendered by Flask.
- **Bootstrap 5:** Responsive grid layout, navbar, cards, forms, tables, badges, alerts, modals, and collapse components.
- **Bootstrap Icons:** Visual indicators and UI icon buttons.
- **JavaScript:** Asynchronous `fetch` calls for dynamic provider selection, availability checks, filter chaining, and profile interactions.
- **Flatpickr:** Interactive date picker for booking appointments.
- **SCSS:** Visual theme definition and custom stylesheet compilation.
</details>

---

## 4. Architecture

Flask is initialized in `app.py`. Routes are split into two main **Blueprints**:

- `client_bp`: Handles public routes and client-specific functionality.
- `business_bp`: Manages partner registration, business management, and provider dashboards.

`layout.html` serves as the base template. It encapsulates the navbar, CSS/Bootstrap includes, flash alerts, footer, and Jinja blocks inherited by child templates.

Access control is managed via session attributes:
- `user_type = 1`: Partner (Provider / Owner)
- `user_type = 2`: Client

---

## 5. Project Structure

<details>
  <summary><b>View Directory Tree & File Details</b> (Click to expand)</summary>

```text
project/
|-- app.py
|-- helpers.py
|-- schema.sql
|-- requirements.txt
|-- blueprints/
|   |-- __init__.py
|   |-- client.py
|   `-- business.py
|-- templates/
|   |-- layout.html
|   |-- index.html
|   |-- login.html
|   |-- register.html
|   |-- profile.html
|   |-- client-appointments.html
|   |-- appointment_new.html
|   |-- business.html
|   |-- business-login.html
|   |-- business-register.html
|   |-- business-home.html
|   |-- business-addbusiness.html
|   |-- business-manage.html
|   |-- business-provider-view.html
|   |-- business-join.html
|   |-- provider-services.html
|   |-- service-create.html
|   `-- apology.html
|-- static/
|   |-- css/
|   |   `-- main.css
|   |-- scss/
|   |   `-- main.scss
|   |-- js/
|   `-- images/
|-- acompanhamento.md
|-- hello.py
`-- LICENSE
```

### Key Python Files

- **`app.py`**: Application entry point. Instantiates Flask, registers Blueprints, sets up session handling, registers custom Jinja filters (currency, phone formatting), defines the `/profile` route, and manages database teardowns.
- **`helpers.py`**: Shared utilities, including authentication decorators (`login_required`), `apology` error handler, SQLite connection managers (`get_db`, `close_db`), phone and street normalization functions, category slug generators, and lightweight database migration functions.
- **`blueprints/client.py`**: Logic for client registration/login, location filters, appointment creation, availability APIs, and cancellation workflows.
- **`blueprints/business.py`**: Logic for business owners and providers, including team management, service creation, provider assignment, and schedule tracking.
</details>

---

## 6. Database & Migrations

<details>
  <summary><b>Schema & Availability Logic</b> (Click to expand)</summary>

The development database is stored locally in `agendei.db` (ignored by Git). 

### Main Tables
- `users`: User credentials, contact info, and access roles (`user_type`).
- `business`: Business profile, owner ID, location, and contact information.
- `services`: Services offered, pricing, and duration (in minutes).
- `business_providers`: Mapping between businesses and providers/owners.
- `provider_services`: Mapping between providers and the specific services they perform.
- `appointment`: Booked slots tying together client, provider, service, date, time, and status.

### Relational Schema

```text
users 1----N appointment N----1 services N----1 business
    |                                      |
    `----N business_providers N------------`
                            |
                            `----N provider_services ---- services
```

### Dynamic Availability
The `/api/availability` endpoint computes free time slots by evaluating:
- Configured service duration.
- Business working hours (08:00 to 18:00).
- Existing appointments booked for the target provider.
- Interval conflicts (start time to end time overlap).
- Real-time checks (preventing past slots on the current calendar day).

Validation is enforced both on the client side (UI filtering) and re-checked on the server side prior to database insertion.
</details>

---

## 7. Setup & Installation

### Prerequisites

- Python 3.10 or higher
- SQLite 3
- `pip` package manager

### Installation Steps

1. **Clone the repository & create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize the database:**
   ```bash
   sqlite3 agendei.db < schema.sql
   ```

4. **Run the application:**
   ```bash
   python app.py
   # Or using Flask CLI:
   # flask --app app run --debug
   ```
   Navigate to `http://127.0.0.1:5000` in your web browser.

---

## 8. License

Distributed under the MIT License. See `LICENSE` for more information.