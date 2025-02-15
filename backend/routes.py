import os
from functools import wraps
from datetime import datetime
import pandas as pd
import plotly.express as px
from flask import Blueprint
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import current_user
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app import login_manager  # Import the login_manager
from backend.models import ActivityLog
from backend.models import BarStock
from backend.models import BartenderStock
from backend.models import BartenderTransaction
from backend.models import Beer  # Adjust the path based on your app structure
from backend.models import BeerStock, OpenStockModel
from backend.models import Event
from backend.models import Room,SalesTransaction
from backend.models import User, db  # Import models and db from the correct location
from .models import StockMovement, Food, ClosedStock, SoldFood
from random import choice

main = Blueprint('main', __name__)
report_dir = os.path.join(os.getcwd(), 'reports')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Session:", session)  # Debugging line
        if 'user_id' not in session:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'manager':
            flash('You must be a manager to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)  # Ensure this returns the user object correctly


# Function to generate unique ID
def generate_unique_id():
    last_user = db.session.query(User).order_by(User.id.desc()).first()
    if last_user:
        return str(int(last_user.id) + 1)  # Increment last user ID
    else:
        return '001'  # Return '001' if no users are present

def get_all_beers():
    # This is just an example assuming you're using SQLAlchemy or similar ORM
    beers = Beer.query.all()  # Fetch all beer stock from the database
    return beers

def get_all_events():
    # Fetch all events from the database
    return Event.query.all()

def get_rooms_available():
    # Query rooms where the 'is_available' attribute is True
    available_rooms = Room.query.filter_by(is_available=True).all()  # Adjust if your column is named differently
    return len(available_rooms)


# Ensure report directory exists
report_dir = os.path.join(os.getcwd(), 'reports')
if not os.path.exists(report_dir):
    os.makedirs(report_dir)

def get_closing_stock():
    closing_stock = db.session.query(
        Food.id,
        Food.name,
        StockMovement.closed_stock.label('quantity_left'),  # Get remaining stock
        case(
            (StockMovement.closed_stock <= 5, "Low Stock"),
            (StockMovement.closed_stock == 0, "Out of Stock"),
            else_="Available"
        ).label('status')
    ).join(StockMovement, Food.id == StockMovement.food_id).all()

    return closing_stock

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@main.route('/')
def home():
    return render_template('st_thomas.html')

# Routes
@main.route('/base')
def index():
    return render_template('base.html')


@main.route('/booking')
def booking():
    # This will render the HTML page you've provided in the 'templates' folder
    return render_template('booking.html')



@main.route('/signup', methods=['GET', 'POST'])
def signup():
    # Check if admin accounts are limited to two
    admin_count = User.query.filter_by(role='admin').count()
    if admin_count >= 3:
        flash('Admin registration limit reached. Contact an existing admin.', 'error')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']

        # Check if the email is already registered
        if User.query.filter_by(email=email).first():
            flash('Email is already registered.', 'error')
            return redirect(url_for('main.signup'))

        # Create a new user object (admin or user based on your logic)
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password, role='admin', phone=phone)

        # Add the new user to the session and commit to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Admin registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('signup.html')



@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            # Check if the user is an admin
            if user.role == 'admin':
                # Successful login for admin
                session['user_id'] = str(user.id)
                session['username'] = user.username
                session['user_role'] = user.role
                # Set is_active to True when logged in
                user.is_active = True
                db.session.commit()

                flash('Login successful!', 'success')
                return redirect(url_for('main.dashboard'))

            # Check role-based redirection
            elif user.role == 'bartender':
                session['user_id'] = str(user.id)
                session['username'] = user.username
                session['user_role'] = user.role
                user.is_active = True
                db.session.commit()

                flash('Login successful!', 'success')
                return redirect(url_for('main.bartender_dashboard'))  # Redirect to bartender dashboard

            elif user.role == 'event_planner':
                session['user_id'] = str(user.id)
                session['username'] = user.username
                session['user_role'] = user.role
                user.is_active = True
                db.session.commit()

                flash('Login successful!', 'success')
                return redirect(url_for('main.event_planner_dashboard'))  # Redirect to event planner dashboard


            elif user.role == 'restaurant_tender':

                session['user_id'] = str(user.id)

                session['username'] = user.username

                session['user_role'] = user.role

                user.is_active = True

                db.session.commit()

                flash('Login successful!', 'success')

                return redirect(url_for('main.restaurant_dashboard'))  # Redirect to restaurant chef dashboard


            else:
                flash('Invalid role assigned.', 'error')
                return redirect(url_for('main.login'))

        flash('Invalid email or password.', 'error')
    return render_template('login.html')


@main.route('/dashboard')
def dashboard():
    # Fetch all beers from the database
    beers = Beer.query.all()

    # Calculate the total quantity of beer remaining
    beer_remaining = sum(beer.quantity for beer in beers)

    # Optionally, you could also calculate the total value of the beer stock
    total_stock_value = sum(beer.total_value for beer in beers)

    # Fetch other data for the dashboard (events, rooms available, etc.)
    events = get_all_events()
    rooms_available = get_rooms_available()

    # Pass all necessary data to the template
    return render_template('dashboard.html', events=events, rooms_available=rooms_available, beers=beers,
                           beer_remaining=beer_remaining, total_stock_value=total_stock_value)



@main.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Extract form data
    full_name = request.form['full_name']
    email = request.form['email']
    password = request.form['password']
    id_number = request.form['id_number']
    phone = request.form['phone']
    role = request.form['role']

    # Check if email is already registered
    if User.query.filter_by(email=email).first():
        flash('Email is already registered.', 'error')
        return redirect(url_for('main.add_user_page'))

    # Generate a unique user ID
    new_user_id = generate_unique_id()

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Create the new user with the unique ID
    new_user = User(
        id=new_user_id,  # Use the generated unique ID
        username=full_name,
        email=email,
        password=hashed_password,
        role=role,
        phone=phone
    )

    # Add and commit the new user to the database
    db.session.add(new_user)
    db.session.commit()

    flash('User added successfully!', 'success')
    return redirect(url_for('main.dashboard'))



@main.route('/export_users')  # Use the blueprint 'main' instead of 'app'
@login_required
def export_users():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Fetch all users
    users = User.query.all()

    # Prepare data for Excel
    user_data = []
    for user in users:
        user_data.append({
            'Full Name': user.username,
            'Email': user.email,
            'Role': user.role,
            'Phone': user.phone,
            'ID Number': user.id_number,
            'Status': 'Active' if user.is_active else 'Not Active'
        })

    # Create a DataFrame
    df = pd.DataFrame(user_data)

    # Convert to Excel in-memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Users')

    output.seek(0)

    # Send file as download
    return send_file(output, as_attachment=True, download_name="users_list.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@main.route('/add_user_page')
@login_required
def add_user_page():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('add_user.html')

@main.route('/delete_user_page')
@login_required
def delete_user_page():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()  # Fetch all users
    return render_template('delete_user.html', users=users)

@main.route('/delete_user/<string:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('main.view_users'))

    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully!', 'success')
    return redirect(url_for('main.view_users'))

@main.route('/view_users')
@login_required
def view_users():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()
    return render_template('view_users.html', users=users)

@main.route('/edit_user/<uuid:user_id>', methods=['GET', 'POST'])  # UUID parameter in the route
@login_required
def edit_user(user_id):
    # Ensure user_id is a UUID before querying
    user_id_str = str(user_id)  # Convert UUID to string for SQLite compatibility
    user = User.query.get_or_404(user_id_str)  # Query by the string representation of the UUID

    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.email = request.form['email']
        user.id_number = request.form['id_number']
        user.phone = request.form['phone']
        user.role = request.form['role']

        # Optional: Handle password update
        password = request.form.get('password')
        if password:
            user.set_password(password)  # Assuming a method to hash the password

        db.session.commit()  # Save changes to the database
        return redirect(url_for('main.manage_users'))  # Redirect to the manage users page

    return render_template('edit_user.html', user=user)



@main.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)

    # Process the form data
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.email = request.form['email']
        user.id_number = request.form['id_number']
        user.phone = request.form['phone']
        user.role = request.form['role']

        password = request.form.get('password')
        if password:
            user.set_password(password)  # Assuming a method to hash the password

        db.session.commit()  # Save changes to the database

        return redirect(url_for('main.manage_users'))  # Redirect to the manage users page

    return render_template('edit_user.html', user=user)


@main.route('/assign_roles')
@login_required
def assign_roles():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.all()
    return render_template('assign_roles.html', users=users)



@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.username = request.form['name']
        user.phone = request.form['phone']
        # email field will not be updated, as it is read-only
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html', user=user)



@main.route('/menu/order', methods=['POST'])
@login_required
def place_order():
    order_details = {
        'user_id': session['user_id'],
        'food_item': request.form['food_item'],
        'pickup_time': request.form['pickup_time'],
        'status': 'Pending',
        'order_time': datetime.now()
    }

    pickup_hour = int(order_details['pickup_time'].split(':')[0])
    if pickup_hour < 9 or pickup_hour > 21:
        flash('Pickup time must be between 9:00 AM and 9:00 PM.', 'error')
        return redirect(url_for('main.restaurant_menu'))

    db.session.execute(
        "INSERT INTO orders (user_id, food_item, pickup_time, status, order_time) "
        "VALUES (:user_id, :food_item, :pickup_time, :status, :order_time)",
        order_details
    )
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/admin_dashboard')
@login_required
def admin_dashboard():
    # Retrieve all beer stock data from the database
    beers = BeerStock.query.all()
    transactions = BartenderTransaction.query.all()
    return render_template("admin_dashboard.html", beers=beers, transactions=transactions)


@main.route('/admin_bar_stock', methods=['GET', 'POST'])
@login_required
def admin_bar_stock():
    if request.method == 'POST':
        # Retrieve form data
        beer_name = request.form['name']
        beer_type = request.form['type']
        price_per_bottle = float(request.form['price_per_bottle'])
        quantity = int(request.form['quantity'])

        # Calculate total value
        total_value = price_per_bottle * quantity

        # Create a new BeerStock instance and add it to the database
        new_beer = BeerStock(
            name=beer_name,
            beer_type=beer_type,
            price_per_bottle=price_per_bottle,
            quantity=quantity,
            total_value=total_value
        )
        db.session.add(new_beer)
        db.session.commit()

        flash('Beer stock added successfully!', 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('admin_bar_stock.html')

@main.route('/bartender_dashboard')
@login_required
def bartender_dashboard():
    if session.get('user_role') != 'bartender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Retrieve current bar stock
    beers = BeerStock.query.all()
    open_stocks = OpenStockModel.query.all()

    # Retrieve bartender's specific stock
    bartender_stocks = BartenderStock.query.filter_by(
        bartender_id=session.get('user_id')
    ).all()

    return render_template(
        'bartender_dashboard.html',
        beers=beers,
        open_stocks=open_stocks,
        bartender_stocks=bartender_stocks
    )


@main.route('/bartender/select-beer', methods=['POST'])
@login_required
def bartender_select_beer():
    try:
        beer_id = int(request.form['beer_id'])
        quantity = int(request.form['quantity'])
    except (KeyError, ValueError):
        flash('Invalid input data!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Retrieve the selected beer from BeerStock
    beer = BeerStock.query.get(beer_id)

    if beer and beer.quantity >= quantity > 0:
        total_value = beer.price_per_bottle * quantity
        beer.quantity -= quantity  # Subtract from warehouse stock

        # Check if the beer already exists in BartenderStock
        existing_bartender_stock = BartenderStock.query.filter_by(
            bartender_id=session.get('user_id'),
            beer_id=beer_id
        ).first()

        if existing_bartender_stock:
            # If it exists, update the quantity and total value
            existing_bartender_stock.quantity += quantity
            existing_bartender_stock.total_value += total_value
        else:
            # If it doesn't exist, create a new BartenderStock entry
            new_bartender_stock = BartenderStock(
                bartender_id=session.get('user_id'),
                beer_id=beer.id,
                quantity=quantity,
                price_per_bottle=beer.price_per_bottle,
                total_value=total_value
            )
            db.session.add(new_bartender_stock)

        # Commit stock updates to the database
        db.session.commit()

        flash(f'{quantity} bottles of {beer.name} moved to bartender stock.', 'success')
    else:
        flash('Not enough stock available in the warehouse.', 'danger')

    return redirect(url_for('main.bartender_dashboard'))


@main.route('/bartender/record-sales', methods=['POST'])
@login_required
def record_sales():
    # Ensure only bartenders can record sales
    if session.get('user_role') != 'bartender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Extract form data safely
    try:
        beer_id = int(request.form.get('beer_id', 0))
        quantity_sold = int(request.form.get('quantity_sold', 0))
        cash_in_hand = float(request.form.get('cash_in_hand', 0.0))
    except ValueError:
        flash('Invalid form data!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Validate form input values
    if not beer_id or quantity_sold <= 0 or cash_in_hand < 0:
        flash('Invalid sale details. Please check your inputs.', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Check if the beer exists in the BartenderStock
    bartender_stock = BartenderStock.query.filter_by(
        bartender_id=session.get('user_id'),
        beer_id=beer_id
    ).first()

    if not bartender_stock:
        flash('Beer not found in your stock!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Check if enough stock is available in BartenderStock
    if bartender_stock.quantity < quantity_sold:
        flash('Not enough stock available in your stock!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Check if the beer exists in the BeerStock database
    beer = BeerStock.query.get(beer_id)
    if not beer:
        flash('Beer not found in the database!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    # Validate cash in hand is sufficient
    total_price = beer.price_per_bottle * quantity_sold
    if cash_in_hand < total_price:
        flash('Insufficient cash in hand!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    try:
        # Update the quantity in BartenderStock
        bartender_stock.quantity -= quantity_sold
        bartender_stock.total_value -= total_price  # Update total value if needed
        db.session.commit()  # Commit the changes to BartenderStock

        # Record the bartender transaction
        new_transaction = BartenderTransaction(
            bartender_id=session.get('user_id'),
            beer_id=beer_id,
            quantity_sold=quantity_sold,
            total_price=total_price,
            sale_type="bottle",  # Sale type is fixed to 'bottle'
            transaction_date=datetime.utcnow()
        )
        db.session.add(new_transaction)

        # Record the sales transaction
        new_sales_transaction = SalesTransaction(
            bartender_id=session.get('user_id'),  # Add bartender_id
            beer_id=beer_id,
            quantity_sold=quantity_sold,
            total_price=total_price,
            cash_in_hand=cash_in_hand,
            transaction_date=datetime.utcnow()  # Add transaction date
        )
        db.session.add(new_sales_transaction)

        # Commit database changes
        db.session.commit()

        flash('Sale recorded successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Database error: {str(e)}', 'danger')

    return redirect(url_for('main.bartender_dashboard'))



@main.route('/beer_total_sales', methods=['GET'])
@login_required
def beer_total_sales():
    # Ensure only bartenders can view sales
    if session.get('user_role') != 'bartender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Retrieve all sales transactions for the logged-in bartender
    sales = SalesTransaction.query.filter_by(bartender_id=session.get('user_id')).all()

    return render_template('beer_total_sales.html', sales=sales)

@main.route('/view_closed_stock')
def view_closed_stock():
    closed_stocks = ClosedStock.query.all()
    return render_template('view_closed_stock.html', closed_stocks=closed_stocks)


@main.route('/submit_sales', methods=['POST'])
def submit_sales():
    # Your logic here
    pass



def generate_combined_report():
    transactions = BartenderTransaction.query.filter_by(
        bartender_id=current_user.id  # Replaced session.get('user_id')
    ).all()

    shortages = BartenderTransaction.query.filter(BartenderTransaction.shortage > 0).all()

    filename = os.path.join(report_dir, 'restaurant_report.pdf')
    os.makedirs(report_dir, exist_ok=True)  # Ensure directory exists
    c = canvas.Canvas(filename, pagesize=letter)

    # Report Title
    c.drawString(100, 750, "Restaurant Transactions & Shortage Report")
    c.drawString(100, 730, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Transactions Section
    y = 700
    c.drawString(100, y, "Beer Name")
    c.drawString(250, y, "Quantity Sold")
    c.drawString(350, y, "Total Revenue")
    c.drawString(450, y, "Profit/Shortage")

    y -= 20
    for transaction in transactions:
        c.drawString(100, y, transaction.beer.name)
        c.drawString(250, y, str(transaction.quantity_sold))
        c.drawString(350, y, f"${transaction.total_price:.2f}")
        c.drawString(450, y, f"${getattr(transaction, 'profit_or_shortage', 0):.2f}")

        y -= 20

    # Move to new section
    y -= 40
    c.drawString(100, y, "Shortage Report")

    y -= 20
    c.drawString(100, y, "Beer Name")
    c.drawString(250, y, "Shortage Qty")
    c.drawString(350, y, "Loss Amount")
    c.drawString(450, y, "Bartender ID")

    y -= 20
    for shortage in shortages:
        c.drawString(100, y, shortage.beer.name)
        c.drawString(250, y, str(shortage.shortage_quantity))
        c.drawString(350, y, f"${shortage.loss:.2f}")
        c.drawString(450, y, str(shortage.bartender_id))

        y -= 20

    c.save()

@main.route('/download_combined_report')
@login_required
def download_combined_report():
    filename = os.path.join(report_dir, 'restaurant_report.pdf')

    if not os.path.exists(filename):
        return "Report file not found", 404

    return send_file(filename, as_attachment=True)

@main.route('/bar_dashboard')
@login_required
def bar_dashboard():
    if session.get('user_role') != 'bartender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Retrieve bar events and other necessary information
    events = BarEvent.query.all()
    opening_balance = BarStock.query.first() or 0  # Retrieve opening balance or None if not found
    return render_template('bar_dashboard.html', events=events, opening_balance=opening_balance)


@main.route('/bar-menu')
def bar_menu():
    return render_template('bar_menu.html')


@main.route('/event_planner_dashboard', methods=['GET', 'POST'])
@login_required
def event_planner_dashboard():
    if session.get('user_role') != 'event_planner':
        flash('Access denied! You do not have the correct permissions.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        time = request.form.get('time')
        description = request.form.get('description')

        # Ensure all fields are provided
        if not name or not date or not time:
            flash("All fields are required!", 'error')
            return redirect(url_for('main.event_planner_dashboard'))

        # Combine date and time to create a datetime object
        try:
            event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            flash("Invalid date or time format!", 'error')
            return redirect(url_for('main.event_planner_dashboard'))

        # Create new event and save to the database
        event = Event(
            name=name,
            date=event_datetime,  # Save as DateTime
            location="Location not specified",  # You can add a location field if needed
            description=description,
            time=time  # Save time as well
        )
        db.session.add(event)
        db.session.commit()

        flash('Event created successfully!', 'success')

    # Fetch unconfirmed events that have not passed
    current_datetime = datetime.now()
    events = Event.query.filter(Event.confirmed == False, Event.date >= current_datetime).all()

    return render_template('event_planner_dashboard.html', events=events)



@main.route('/upload', methods=['POST'])
def upload_event():
    if 'image' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['image']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)  # Save the file to static/images

        # Assuming other event details are stored in a database
        event_data = {
            'name': request.form.get('name'),
            'date': request.form.get('date'),
            'time': request.form.get('time'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'image_url': filename  # Store filename in the database
        }

        # Save event_data to database (MongoDB, SQLite, etc.)
        flash('Event added successfully!')
        return redirect(url_for('confirmed_events'))  # Redirect to event page

    flash('Invalid file format')
    return redirect(request.url)



# Confirm event (POST method)
@main.route('/confirm_event/<int:event_id>', methods=['POST'])
@login_required
def confirm_event(event_id):
    if session.get('user_role') != 'event_planner':
        return jsonify({'error': 'Unauthorized'}), 403

    event = Event.query.get(event_id)
    if event:
        event.confirmed = True
        db.session.commit()
        flash('Event confirmed successfully!', 'success')
        return redirect(url_for('main.event_planner_dashboard'))  # Redirect to dashboard

    flash('Event not found', 'error')
    return redirect(url_for('main.event_planner_dashboard'))


@main.route('/bar-events')
def bar_events():
    events = Event.query.filter_by(confirmed=True).all()  # Fetch confirmed events

    # Example: Select a random image from a list of images
    images = ['hero 1.jpg', 'hero 2.jpg', 'hero 3.jpg', 'hero 4.jpg', 'hero 5.jpg', 'hero 6.jpg']
    selected_image = choice(images)  # Choose a random image

    return render_template('bar_events.html', events=events, selected_image=selected_image)






# Restaurant Page - Shows all available food items
@main.route('/restaurant')
def restaurant():
    available_food_items = Food.query.filter_by(status='Available').all()
    return render_template('restaurant.html', available_food_items=available_food_items)


# Restaurant Menu - Displays available food items
@main.route('/menu/restaurant', methods=['GET'])
@login_required
def restaurant_menu():
    result = db.session.execute(text("SELECT * FROM food WHERE type='restaurant' AND status='Available'")).fetchall()
    is_open = 9 <= datetime.now().hour <= 21
    food_items = [{'id': food.id, 'name': food.name, 'price': food.price} for food in result]
    return render_template('restaurant_menu.html', available_food_items=food_items, is_open=is_open)


# Restaurant Dashboard - For restaurant tenders to manage the menu
@main.route('/restaurant_dashboard', methods=['GET'])
@login_required
def restaurant_dashboard():
    if session.get('user_role') != 'restaurant_tender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))
    food_items = Food.query.filter_by(type='restaurant').all()
    return render_template('restaurant_chef_dashboard.html', food_items=food_items)


# Add new food item to the menu
@main.route('/add_food', methods=['GET', 'POST'])
@login_required
def add_food():
    if request.method == 'POST':
        name = request.form['name']
        quantity = float(request.form['quantity'])
        status = 'open_stock'
        type_of_food = 'restaurant'

        new_food = Food(name=name, quantity=quantity, sold_quantity=0, status=status, type=type_of_food)
        db.session.add(new_food)
        db.session.commit()

        flash(f"Food item '{name}' added successfully!", 'success')
        # Log the activity
        log_entry = ActivityLog(activity_type="Food Added", description=f"Added {name} with {quantity} quantity.")
        db.session.add(log_entry)
        db.session.commit()

        return redirect(url_for('main.restaurant_dashboard'))
    return render_template('add_food.html')


# Order food item - Handles food ordering
@main.route('/order_food/<int:food_id>', methods=['GET', 'POST'])
def order_food(food_id):
    food = Food.query.get_or_404(food_id)

    if food.status == 'Unavailable':
        flash('This food item is currently unavailable.', 'error')
        return redirect(url_for('main.restaurant_menu'))

    if request.method == 'POST':
        customer_name = request.form['name']
        phone_number = request.form['phone']
        collection_time = request.form['collection_time']
        payment_method = request.form['payment_method']
        quantity_ordered = float(request.form['quantity_ordered'])

        try:
            collection_hour = int(collection_time.split(":")[0])
            if not (9 <= collection_hour <= 21):
                flash('Invalid collection time. Must be between 9:30 and 21:30.', 'error')
                return redirect(url_for('main.order_food', food_id=food.id))
        except ValueError:
            flash('Invalid time format.', 'error')
            return redirect(url_for('main.order_food', food_id=food.id))

        if food.quantity >= quantity_ordered:
            food.quantity -= quantity_ordered
            food.sold_quantity += quantity_ordered
            db.session.commit()
            flash(f"Thank you! Your order for {food.name} will be ready at {collection_time}.", 'success')
        else:
            flash('Not enough stock available.', 'error')
            return redirect(url_for('main.order_food', food_id=food.id))

        return redirect(url_for('main.restaurant_dashboard'))

    return render_template('order_food.html', food=food)


# Update stock for a specific food item
@main.route('/update_stock/<int:food_id>', methods=['POST'])
def update_stock(food_id):
    food = Food.query.get_or_404(food_id)
    quantity_used = int(request.form['quantity_used'])

    stock = StockMovement.query.filter_by(food_id=food_id).first()
    if not stock:
        flash("Stock movement record not found.", 'error')
        return redirect(url_for('main.restaurant_dashboard'))

    if quantity_used > stock.closed_stock:
        flash("Quantity used exceeds available stock.", 'error')
        return redirect(url_for('main.restaurant_dashboard'))

    food.quantity -= quantity_used
    stock.closed_stock -= quantity_used
    stock.quantity_used += quantity_used
    db.session.commit()
    flash("Stock updated successfully.", 'success')

    return redirect(url_for('main.restaurant_dashboard'))


# Delete a food item from the menu
@main.route('/delete_food/<int:food_id>', methods=['POST'])
@login_required
def delete_food(food_id):
    food = Food.query.get_or_404(food_id)
    db.session.delete(food)
    db.session.commit()
    flash(f"The food item '{food.name}' has been deleted.", 'success')
    return redirect(url_for('main.restaurant_dashboard'))


# Restaurant Open Stock - Display open stock status
@main.route('/restaurant_open_stock')
def restaurant_open_stock():
    return render_template('restaurant_open_stock.html')


@main.route('/subtract_food/<int:food_id>', methods=['POST'])
def subtract_food(food_id):
    food = Food.query.get_or_404(food_id)
    try:
        quantity_used = float(request.form['quantity_used'])
    except ValueError:
        flash("Invalid quantity.", "error")
        return redirect(url_for('main.restaurant_dashboard'))

    if quantity_used > food.quantity:
        flash("Quantity used exceeds available stock.", 'error')
        return redirect(url_for('main.restaurant_dashboard'))

    # Record the current stock before sale (optional, if you use a StockMovement model)
    open_stock = food.quantity

    # Update the Food record
    food.quantity -= quantity_used
    food.sold_quantity += quantity_used
    closed_stock = food.quantity

    # Calculate the total amount for this sale.
    # (Make sure your Food model’s price is set when adding the food item)
    sale_total = quantity_used * (food.price if food.price else 0)

    # Create a new SoldFood record
    sold_food_record = SoldFood(
        food_name=food.name,
        quantity=quantity_used,
        total_amount=sale_total
    )
    db.session.add(sold_food_record)

    # (Optional) If you are using a StockMovement model, update it here.
    # stock_entry = StockMovement(food_id=food_id, open_stock=open_stock,
    #                             closed_stock=closed_stock, quantity_used=quantity_used)
    # db.session.add(stock_entry)

    db.session.commit()

    flash("Stock subtracted and sale recorded successfully.", 'success')
    return redirect(url_for('main.restaurant_dashboard'))


@main.route('/restaurant_closing_stock')
def restaurant_closing_stock():
    sold_food_records = SoldFood.query.order_by(SoldFood.sold_date.desc()).all()
    return render_template('restaurant_closing_stock.html', sold_food_records=sold_food_records)


# Route to download the activity report as CSV
@main.route('/download_activity_report')
@login_required
def download_activity_report():
    if session.get('user_role') != 'admin':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    logs = ActivityLog.query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Activity Type', 'Description', 'Timestamp'])
    for log in logs:
        writer.writerow([log.activity_type, log.description, log.timestamp])

    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True,
                     download_name="restaurant_activity_report.csv")

# Generate and save a bar chart for orders per food item
@main.route('/orders_report')
def orders_report():
    order_data = db.session.query(Food.name, func.sum(ActivityLog.quantity_ordered).label('total_orders')) \
        .join(ActivityLog, ActivityLog.food_id == Food.id) \
        .group_by(Food.name).all()

    df = pd.DataFrame(order_data, columns=['Food', 'Total Orders'])
    fig = px.bar(df, x='Food', y='Total Orders', title='Food Orders Report')

    fig.write_html("static/reports/orders_report.html")
    return send_file("static/reports/orders_report.html", mimetype='text/html')


@main.route('/rooms', methods=['GET'])
@login_required
def room_list():
    # Correct the raw SQL query by wrapping it with text()
    rooms = db.session.execute(text("SELECT * FROM rooms")).fetchall()
    return render_template('rooms.html', rooms=rooms)

@main.route('/rooms/book', methods=['POST'])
@login_required
def book_room():
    room_id = request.form['room_id']
    user_details = {
        'name': request.form['name'],
        'phone': request.form['phone'],
        'arrival_date': request.form['arrival_date'],
        'hours': request.form['hours'],
    }

    room = db.session.execute(
        "SELECT * FROM rooms WHERE id=:room_id AND status='available'", {'room_id': room_id}
    ).fetchone()

    if not room:
        flash('Room is not available.', 'error')
        return redirect(url_for('main.room_list'))

    db.session.execute(
        "UPDATE rooms SET status='booked', booked_by=:user_details WHERE id=:room_id",
        {'user_details': json.dumps(user_details), 'room_id': room_id}
    )
    db.session.commit()

    flash('Room booked successfully!', 'success')
    send_booking_notification(user_details, room_id)
    return redirect(url_for('main.room_list'))

# Notification functions
def send_booking_notification(user_details, room_id):
    message = (
        f"Hello {user_details['name']},\n\n"
        f"Your room (ID: {room_id}) is booked.\n"
        f"Arrival Date: {user_details['arrival_date']}\n"
        f"Duration: {user_details['hours']} hours\n\n"
        "Thank you for choosing our service!"
    )
    print(f"Notification sent: {message}")

@main.route('/room_dashboard')
@login_required
def room_dashboard():
    if session.get('user_role') != 'event_planner':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    rooms = Room.query.filter_by(is_available=True).all()  # Fetch available rooms
    return render_template('event_planner_dashboard.html', rooms=rooms)


# Route for booking a specific room with a given room_id
@main.route('/book_room/<int:room_id>', methods=['GET', 'POST'], endpoint='book_specific_room')
@login_required
def book_room(room_id):
    room = Room.query.get(room_id)

    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        arrival_date = request.form['arrival_date']
        duration = request.form['duration']

        # Process payment (integrate with a payment gateway)
        payment_method = request.form['payment_method']

        # Send confirmation message and notify the manager
        flash('Room booking successful!', 'success')
        return redirect(url_for('main.room_dashboard'))

    return render_template('book_room.html', room=room)

# Route for the general room list (no room_id) - renamed function
@main.route('/book_room_list', methods=['POST'], endpoint='book_room_list')
@login_required
def book_room_list():
    room_id = request.form['room_id']
    # Your logic for booking a room from the list

    return redirect(url_for('main.room_list'))


@main.route('/logout', methods=['POST'])
@login_required
def logout():
    # Check if the user is logged in
    if not session.get('user_id'):
        flash('No user is logged in', 'error')
        return redirect(url_for('main.login'))

    # Retrieve the user from the database
    user = User.query.get(session['user_id'])

    if user is None:
        flash('User not found', 'error')
        return redirect(url_for('main.login'))

    # Set the user's 'is_active' to False on logout
    user.is_active = False
    db.session.commit()

    # Clear session variables
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_role', None)

    # Flash a success message
    flash('You have been logged out successfully!', 'success')

    # Redirect to the login page
    return redirect(url_for('main.login'))
