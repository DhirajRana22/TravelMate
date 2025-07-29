# TravelMate - Bus Booking System

A comprehensive Django-based bus booking system that allows users to search for bus routes, book tickets, and manage their travel bookings.

## Features

- **User Authentication**: Register and login with email or phone number
- **Route Search**: Search for bus routes between different locations
- **Bus Management**: View bus details, schedules, and availability
- **Booking System**: Book tickets with seat selection
- **Payment Integration**: Handle payments for bookings
- **User Dashboard**: Manage profile, view booking history
- **Admin Dashboard**: Comprehensive admin panel for managing buses, routes, and bookings
- **QR Code Generation**: Generate QR codes for tickets
- **Responsive Design**: Mobile-friendly interface

## Technology Stack

- **Backend**: Django 5.2.4
- **Database**: SQLite (development)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Authentication**: Custom email/phone authentication backend
- **Forms**: Django Crispy Forms
- **Image Processing**: Pillow
- **QR Code**: qrcode library
- **Machine Learning**: scikit-learn (for analytics)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

### Setup Instructions

1. **Clone the repository**

   ```bash
   git clone <https://github.com/DhirajRana22/TravelMate>
   cd TravelMate
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Run database migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a superuser (optional)**

   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**

   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**

   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Open your browser and go to `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## Project Structure

```
TravelMate/
├── TravelMate/          # Main project settings
├── accounts/            # User authentication and profiles
├── buses/              # Bus management
├── routes/             # Route management
├── bookings/           # Booking system
├── payments/           # Payment processing
├── dashboard/          # Admin dashboard
├── home/               # Home page and static pages
├── templates/          # HTML templates
├── static/             # CSS, JS, and images
├── media/              # User uploaded files
├── requirements.txt    # Python dependencies
├── manage.py          # Django management script
└── README.md          # Project documentation
```

## Key Applications

### Accounts

- User registration and authentication
- Custom authentication backend for email/phone login
- User profile management
- Booking and payment history

### Buses

- Bus information management
- Bus schedules and availability
- Bus image uploads

### Routes

- Route creation and management
- Location management
- Route search functionality

### Bookings

- Ticket booking system
- Seat selection
- Booking confirmation
- QR code generation for tickets

### Payments

- Payment processing
- Payment history
- Payment status tracking

### Dashboard

- Admin interface for system management
- Analytics and reporting
- User and booking management

## Configuration

### Environment Variables

For production deployment, create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=your-database-url
```

### Database Configuration

The project uses SQLite by default for development. For production, configure PostgreSQL or MySQL in `settings.py`.

## Usage

### For Users

1. Register an account using email or phone number
2. Search for bus routes between locations
3. Select a bus and book tickets
4. Make payment for the booking
5. Receive QR code ticket via email
6. Manage bookings through user profile

### For Administrators

1. Access admin dashboard at `/admin/`
2. Manage buses, routes, and schedules
3. View booking analytics and reports
4. Handle user management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue in the GitHub repository.

## Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Configure proper database (PostgreSQL/MySQL)
- [ ] Set up static file serving
- [ ] Configure email backend
- [ ] Set up SSL/HTTPS
- [ ] Configure domain and allowed hosts
- [ ] Set up backup strategy
- [ ] Configure logging

### Recommended Hosting Platforms

- Heroku
- DigitalOcean
- AWS EC2
- Google Cloud Platform
- PythonAnywhere

## Version History

- v1.0.0 - Initial release with core booking functionality
- Features: User auth, route search, booking system, payment integration
