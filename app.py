# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
import uuid
import os
from datetime import datetime, UTC
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)
admin = Admin(app)

# Define the Client model
class Client(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String)
    phone_number = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    gender = db.Column(db.String)
    national_id = db.Column(db.String)
    nationality = db.Column(db.String)
    is_admin = db.Column(db.Boolean, default=False, nullable=False) 

    quotations = db.relationship('Quotation', backref='client', lazy=True)


# Define the Quotation model
class Quotation(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    park_choice = db.Column(db.String)
    num_people = db.Column(db.Integer)
    num_days = db.Column(db.Integer)
    accommodation_choice = db.Column(db.String)
    transportation_choice = db.Column(db.String)
    ages = db.Column(db.PickleType)  # Store ages as a list of integers
    quotation_text = db.Column(db.String)
    client_id = db.Column(db.String(36), db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
# Function to save booking details
def save_booking_details(client_id, park_choice, num_people, num_days, accommodation_choice, transportation_choice, ages, quotation_text):
    quotation = Quotation(
        park_choice=park_choice,
        num_people=num_people,
        num_days=num_days,
        accommodation_choice=accommodation_choice,
        transportation_choice=transportation_choice,
        ages=ages,
        quotation_text=quotation_text,
        client_id=client_id
    )

    db.session.add(quotation)
    db.session.commit()


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

admin.add_view(ModelView(Client, db))
admin.add_view(ModelView(Quotation, db))

@login_manager.user_loader
def load_user(user_id):
    return Client.query.get(user_id)
def admin_required(view):
    @login_required
    def wrapped_view(*args, **kwargs):

        if not current_user.is_admin:
            abort(403)

        return view(*args, **kwargs)

    wrapped_view.__name__ = view.__name__

    return wrapped_view

@app.route('/view_password')
@login_required
def view_password():
    return render_template('view_password.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Check the current password and update it with the new one
        if check_password_hash(current_user.password, form.current_password.data):
            new_hashed_password = generate_password_hash(form.new_password.data, method='pbkdf2:sha256')
            current_user.password = new_hashed_password
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect current password. Please try again.', 'danger')

    return render_template('change_password.html', form=form)

@app.route('/admin')
@admin_required
def admin_dashboard():

    total_clients = Client.query.count()
    total_quotations = Quotation.query.count()

    recent_quotations = (
        Quotation.query
        .order_by(Quotation.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        total_clients=total_clients,
        total_quotations=total_quotations,
        recent_quotations=recent_quotations
    )

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/maasai_mara')
def maasai_mara():
    # Route for Maasai Mara page
    return render_template('maasai_mara.html')

@app.route('/lake_nakuru')
def lake_nakuru():
    # Route for Lake Nakuru page
    return render_template('lake_nakuru.html')

@app.route('/oldonyo_sabuk')
def oldonyo_sabuk():
    # Route for Oldonyo Sabuk page
    return render_template('oldonyo_sabuk.html')

@app.route('/tsavo')
def tsavo():
    # Route for Tsavo page
    return render_template('tsavo.html')

@app.route('/group_tours')
def group_tours():
    return render_template('group_tours.html')


@app.route('/solo_tours')
def solo_tours():
    return render_template('solo_tours.html')


@app.route('/events')
def events():
    return render_template('events.html')


@app.route('/campsite')
def campsite():
    return render_template('campsite.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Replace the following logic with your actual authentication logic
        client = Client.query.filter_by(email=email).first()
        if client and check_password_hash(client.password, password):
            login_user(client)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        # Get user input from the registration form
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        password = request.form.get('password')
        gender = request.form.get('gender')
        national_id = request.form.get('national_id')
        nationality = request.form.get('nationality')

        # Check if the email is already registered
        existing_user = Client.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered. Please use a different email.', 'error')
            return redirect(url_for('registration'))

        # Hash the password before storing it
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new Client instance and add it to the database
        new_client = Client(
            name=name,
            phone_number=phone_number,
            email=email,
            password=hashed_password,
            gender=gender,
            national_id=national_id,
            nationality=nationality
        )

        db.session.add(new_client)
        db.session.commit()

        flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('registration.html')


@app.route('/generate_quotation', methods=['GET', 'POST'])
@login_required
def generate_quotation():
    quotation_text = None  # Initialize the variable
    
    if request.method == 'POST':
        try:
            # Fetch quotation details from the form
            park_choice = request.form['park_choice']
            num_people = int(request.form['num_people'])
            num_days = int(request.form['num_days'])
            accommodation_choice = request.form['accommodation_choice']
            transportation_choice = request.form['transportation_choice']
            ages = [int(request.form.get(f'age{i}', 0)) for i in range(1, num_people + 1)]

            # Call a function to generate the quotation text based on the form inputs
            quotation_text = generate_quotation_text(park_choice, num_people, num_days, accommodation_choice, transportation_choice, ages)

            # Create a new Quotation instance
            new_quotation = Quotation(
                id=str(uuid.uuid4()),
                park_choice=park_choice,
                num_people=num_people,
                num_days=num_days,
                accommodation_choice=accommodation_choice,
                transportation_choice=transportation_choice,
                ages=ages,
                quotation_text=quotation_text,
                client_id=current_user.id,
                created_at=datetime.now(UTC)  # Add the current timestamp
            )

            db.session.add(new_quotation)
            db.session.commit()

            flash('Quotation generated successfully!', 'success')
            return redirect(url_for('quotation_result', quotation_text=quotation_text))

        except IntegrityError:
            db.session.rollback()
            flash('Error generating quotation. Please try again.', 'danger')

    # For GET requests, simply render the template
    return render_template('generate_quotation.html', quotation_text=quotation_text)


@app.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():

    if request.method == 'POST':

        try:
            park_choice = request.form.get('park_choice')

            num_people = int(
                request.form.get('num_people', 0)
            )

            num_days = int(
                request.form.get('num_days', 0)
            )

            accommodation_choice = request.form.get(
                'accommodation_choice'
            )

            transportation_choice = request.form.get(
                'transportation_choice'
            )

            # Get ages from the form
            ages_string = request.form.get('ages', '')

            ages = [
                int(age.strip())
                for age in ages_string.split(',')
                if age.strip()
            ]

            # Basic validation
            if not park_choice:
                flash(
                    'Please select a destination.',
                    'danger'
                )
                return redirect(url_for('booking'))

            if num_people <= 0:
                flash(
                    'Please enter the number of people.',
                    'danger'
                )
                return redirect(url_for('booking'))

            if num_days <= 0:
                flash(
                    'Please enter the number of days.',
                    'danger'
                )
                return redirect(url_for('booking'))

            if len(ages) != num_people:
                flash(
                    f'Please enter exactly {num_people} traveller ages.',
                    'danger'
                )
                return redirect(url_for('booking'))

            # Generate quotation
            quotation_text = generate_quotation_text(
                park_choice,
                num_people,
                num_days,
                accommodation_choice,
                transportation_choice,
                ages
            )

            # Create quotation record
            new_quotation = Quotation(
                id=str(uuid.uuid4()),
                park_choice=park_choice,
                num_people=num_people,
                num_days=num_days,
                accommodation_choice=accommodation_choice,
                transportation_choice=transportation_choice,
                ages=ages,
                quotation_text=quotation_text,
                client_id=current_user.id,
                created_at=datetime.now(UTC)
            )

            db.session.add(new_quotation)

            db.session.commit()

            # Send confirmation email
            send_confirmation_email(
                current_user.email,
                current_user.name,
                park_choice,
                num_people,
                num_days,
                accommodation_choice,
                transportation_choice,
                ages,
                quotation_text
            )

            flash(
                'Booking successful! Confirmation email sent.',
                'success'
            )

            return redirect(url_for('success'))

        except ValueError:

            db.session.rollback()

            flash(
                'Please enter valid ages and numbers.',
                'danger'
            )

            return redirect(url_for('booking'))

        except Exception as e:

            db.session.rollback()

            print("BOOKING ERROR:", e)

            flash(
                'An error occurred while processing your booking.',
                'danger'
            )

            return redirect(url_for('booking'))

    # GET request
    return render_template('booking.html')


def send_confirmation_email(
    client_email,
    client_name,
    park_choice,
    num_people,
    num_days,
    accommodation_choice,
    transportation_choice,
    ages,
    quotation_text
):
    subject = 'Booking Confirmation'

    body = f"""Dear {client_name},

Thank you for your booking with Ngary Tour & Travel.

Booking Details:

Park Choice: {park_choice}
Number of People: {num_people}
Number of Days: {num_days}
Accommodation Choice: {accommodation_choice}
Transportation Choice: {transportation_choice}
Ages: {', '.join(map(str, ages))}

Quotation:

{quotation_text}

Best regards,
Ngary Tour & Travel
"""

    api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('MAIL_DEFAULT_SENDER')

    if not api_key:
        raise RuntimeError('BREVO_API_KEY is not configured.')

    if not sender_email:
        raise RuntimeError('MAIL_DEFAULT_SENDER is not configured.')

    response = requests.post(
        'https://api.brevo.com/v3/smtp/email',
        headers={
            'accept': 'application/json',
            'api-key': api_key,
            'content-type': 'application/json'
        },
        json={
            'sender': {
                'name': 'Ngary Tour & Travel',
                'email': sender_email
            },
            'to': [
                {
                    'email': client_email,
                    'name': client_name
                }
            ],
            'subject': subject,
            'textContent': body
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()

@app.route('/quotation_result')
@login_required
def quotation_result():
    # Retrieve the quotation_text from the query parameters
    quotation_text = request.args.get('quotation_text', '')

    # Render the quotation result template, passing the quotation_text
    return render_template('quotation_result.html', quotation_text=quotation_text)


@app.route('/success')
@login_required
def success():
    # Fetch the latest booking details for the current user
    booking_details = get_latest_booking_details(current_user.id)

    if not booking_details:
        flash('Booking details not found.', 'warning')
        return redirect(url_for('index'))

    return render_template('success.html', booking_details=booking_details)

def get_latest_booking_details(client_id):
    # Query the Quotation model based on the client_id and order by created_at
    latest_booking = Quotation.query.filter_by(client_id=client_id).order_by(Quotation.created_at.desc()).first()

    return latest_booking
    #return Quotation.query.filter_by(client_id=client_id).order_by(Quotation.created_at.desc()).first()


def get_quotation_details(quotation_id):
    # Fetch the Quotation from the database based on the quotation_id
    quotation = Quotation.query.get(quotation_id)

    if quotation:
        # Format the quotation details as needed
        details = f"Quotation for {quotation.num_people} people for {quotation.num_days} days at {quotation.park_choice}:\n"
        details += f"Accommodation: {quotation.accommodation_choice}\n"
        details += f"Transportation: {quotation.transportation_choice}\n"
        details += f"Ages: {', '.join(map(str, quotation.ages))}\n"
        # Add more details as needed

        return details

    return None

@app.route('/quotation/<quotation_id>')
@login_required
def view_quotation(quotation_id):
    quotation_details = get_quotation_details(quotation_id)

    if quotation_details:
        return render_template('quotation_details.html', quotation_details=quotation_details)
    else:
        flash('Quotation not found.', 'warning')
        return redirect(url_for('index'))

@app.route('/quotations')
def list_quotations():
    quotations = Quotation.query.all()
    return render_template('quotations.html', quotations=quotations)


def generate_quotation_text(park_choice, num_people, num_days, accommodation_choice, transportation_choice, ages):
    # Calculate the quotation based on the received data
    # Define costs for accommodation and transportation
    accommodation_costs = {
        "Luxury Lodges": 15000,
        "Tented Camps": 9000,
        "Budget Camps": 5000,
    }
    transportation_costs = {
        "Private Safari Vehicle": 3000,
        "Shared Safari Vehicle": 1000,
    }
    
    # Calculate accommodation cost based on the number of nights (one less than days)
    accommodation_cost = accommodation_costs.get(accommodation_choice, 0) * (num_days - 1)
    transportation_cost = transportation_costs.get(transportation_choice, 0)

    total_cost = (accommodation_cost + transportation_cost) * num_people

    quotation = f"Quotation for {num_people} people for {num_days} days at {park_choice} ({num_people} people):\n"
    quotation += f"Accommodation: {accommodation_cost} Ksh for {num_days - 1} nights\n"
    quotation += f"Transportation: {transportation_cost} Ksh per person\n"

    for i, age in enumerate(ages, start=1):
        if age < 7:
            child_accommodation_cost = (accommodation_costs.get(accommodation_choice, 0) * (num_days - 1)) / 2
            quotation += f"Person {i} (Age {age}): {child_accommodation_cost} Ksh for {num_days - 1} nights (Child rate)\n"
        else:
            quotation += f"Person {i} (Age {age}): {accommodation_cost} Ksh for {num_days - 1} nights (Adult rate)\n"

    quotation += f"Total Cost: {total_cost} Ksh\n"

    return quotation

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
    app.run(debug=True)

