import csv
import os
from datetime import datetime
from functools import wraps
from io import BytesIO
from io import StringIO
import pandas as pd
from flask import Blueprint
from flask import flash, redirect, request, session, url_for
from flask import render_template
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from backend.app import login_manager  # Import the login_manager
from backend.models import BarStock
from backend.models import BartenderStock
from backend.models import BartenderTransaction
from backend.models import Beer  # Adjust the path based on your app structure
from backend.models import BeerStock, OpenStockModel
from backend.models import Event
from backend.models import Room
from backend.models import User, db  # Import models and db from the correct location
from backend.models import Food
from flask_login import current_user


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
    if admin_count >= 7:
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

    # Retrieve current bar stock from BeerStock table
    beers = BeerStock.query.all()
    open_stocks = OpenStockModel.query.all()  # Retrieve selected beers

    # Retrieve bartender's specific stock
    bartender_stocks = BartenderStock.query.filter_by(bartender_id=session.get('user_id')).all()

    return render_template(
        'bartender_dashboard.html',
        beers=beers,
        open_stocks=open_stocks,  # Pass to template
        bartender_stocks=bartender_stocks
    )


@main.route('/bartender/select-beer', methods=['POST'])
@login_required
def bartender_select_beer():
    try:
        beer_id = request.form['beer_id']
        quantity = int(request.form['quantity'])
    except (KeyError, ValueError):
        flash('Invalid input data!', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    beer = BeerStock.query.get(beer_id)

    if beer and beer.quantity >= quantity > 0:
        total_value = beer.price_per_bottle * quantity

        # Deduct stock from warehouse
        beer.quantity -= quantity

        # Check if the beer is already in OpenStockModel
        existing_stock = OpenStockModel.query.filter_by(beer_id=beer_id).first()

        if existing_stock:
            existing_stock.quantity += quantity
            existing_stock.total_value += total_value
        else:
            new_stock = OpenStockModel(
                beer_id=beer.id,
                quantity=quantity,
                total_value=total_value
            )
            db.session.add(new_stock)

        db.session.commit()  # Commit the changes
        flash(f'{quantity} bottles of {beer.name} moved to bartender stock.', 'success')
    else:
        flash('Not enough stock available in the warehouse', 'danger')

    return redirect(url_for('main.bartender_dashboard'))

@main.route('/bartender/record-sales', methods=['POST'])
@login_required
def record_sales():
    # Debugging: Check if the user is authenticated
    if not current_user.is_authenticated:
        flash('You need to log in to record sales!', 'danger')
        return redirect(url_for('main.login'))  # Redirect to the login page

    try:
        beer_id = request.form['beer_id']
        quantity_sold = int(request.form['quantity_sold'])
        sale_type = request.form['sale_type']
    except (KeyError, ValueError) as e:
        flash(f'Missing or invalid form data: {str(e)}', 'danger')
        return redirect(url_for('main.bartender_dashboard'))

    stock = OpenStockModel.query.filter_by(beer_id=beer_id).first()

    if stock and stock.quantity >= quantity_sold:
        # Calculate the sale total
        beer = stock.beer
        if sale_type == 'bottle':
            total_price = beer.price_per_bottle * quantity_sold
        else:  # If it's a shot, adjust the price accordingly
            total_price = (beer.price_per_bottle / 5) * quantity_sold  # Example price for shots

        # Subtract the sold quantity from OpenStockModel
        stock.quantity -= quantity_sold
        stock.total_value -= total_price

        if stock.quantity == 0:
            db.session.delete(stock)

        # Record the transaction
        transaction = BartenderTransaction(
            bartender_id=current_user.id,
            beer_id=beer.id,
            quantity_sold=quantity_sold,
            total_price=total_price,
            sale_type=sale_type,
            transaction_date=datetime.utcnow()
        )
        db.session.add(transaction)
        db.session.commit()

        flash('Sale recorded successfully!', 'success')
    else:
        flash('Not enough stock or invalid sale!', 'danger')

    return redirect(url_for('main.bartender_dashboard'))


@main.route('/sales_transactions')
@login_required
def sales_transactions():
    # Debugging: Check if the user is authenticated
    if not current_user.is_authenticated:
        flash('You need to log in to view sales transactions!', 'danger')
        return redirect(url_for('main.login'))  # Redirect to the login page

    # Query transactions specific to the logged-in bartender
    transactions = BartenderTransaction.query.filter_by(bartender_id=current_user.id).all()

    return render_template('sales_transactions.html', transactions=transactions)



def generate_report():
    # Query all transactions from the database
    transactions = BartenderTransaction.query.filter_by(bartender_id=session['user_id']).all()

    # Ensure the reports directory exists
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    filename = os.path.join(report_dir, 'bartender_report.pdf')
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, "Bartender Transactions Report")
    c.drawString(100, 730, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Add table headers
    y = 700
    c.drawString(100, y, "Beer Name")
    c.drawString(250, y, "Quantity")
    c.drawString(350, y, "Total Revenue")
    c.drawString(450, y, "Profit/Shortage")

    # Populate the table with transaction data
    y -= 20
    for transaction in transactions:
        c.drawString(100, y, transaction.beer.name)
        c.drawString(250, y, str(transaction.quantity_sold))
        c.drawString(350, y, f"${transaction.total_price:.2f}")
        c.drawString(450, y, f"${transaction.profit_or_shortage:.2f}")
        y -= 20

    c.save()



# Route to download the bartender report
@main.route('/download_report')
@login_required
def download_report():
    # Ensure the file exists before attempting to send it
    filename = os.path.join(report_dir, 'bartender_report.pdf')

    if not os.path.exists(filename):
        return "Report file not found", 404  # Return 404 if file is not found

    # Send the file as an attachment
    return send_file(filename, as_attachment=True)


# Route to download the shortage report
@main.route('/admin/download_shortage_report')
@login_required
def download_shortage_report():
    # Query for shortage data
    shortages = BartenderTransaction.query.filter(BartenderTransaction.shortage > 0).all()

    # Check if there are shortages
    if not shortages:
        return "No shortage data available", 404

    # Generate CSV content
    csv_output = StringIO()
    writer = csv.writer(csv_output)
    writer.writerow(["Beer Name", "Shortage Quantity", "Loss Amount", "Bartender ID"])

    for shortage in shortages:
        writer.writerow([
            shortage.beer.name,
            shortage.shortage_quantity,
            shortage.loss,
            shortage.bartender_id
        ])

    # Seek to the beginning of the CSV output for reading
    csv_output.seek(0)

    # Send the CSV content as a downloadable file
    return send_file(
        StringIO(csv_output.read()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="shortage_report.csv"
    )




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
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        time = request.form.get('time')
        description = request.form.get('description')

        # Create new event and save to the database
        event = Event(
            name=name,
            date=f"{date} {time}",
            location="Location not specified",  # You can add location field if needed
            description=description
        )
        db.session.add(event)
        db.session.commit()

        flash('Event created successfully!', 'success')

    # Fetch unconfirmed events
    events = Event.query.filter_by(confirmed=False).all()
    return render_template('event_planner_dashboard.html', events=events)

@main.route('/confirm_event/<int:event_id>', methods=['POST'])
@login_required
def confirm_event(event_id):
    if session.get('user_role') != 'event_planner':
        return jsonify({'error': 'Unauthorized'}), 403

    event = Event.query.get(event_id)
    if event:
        event.confirmed = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Event confirmed successfully!'})

    return jsonify({'error': 'Event not found'}), 404



@main.route('/bar-events')
def bar_events():
    events = Event.query.filter_by(confirmed=True).all()  # Fetch confirmed events
    return render_template('bar_events.html', events=events)



@main.route('/menu/restaurant', methods=['GET'])
@login_required
def restaurant_menu():
    # Query to fetch only available items of type 'restaurant'
    result = db.session.execute(text("SELECT * FROM food WHERE type='restaurant' AND status='Available'")).fetchall()

    # Check if the restaurant is open (9 AM to 9 PM)
    is_open = 9 <= datetime.now().hour <= 21

    # Convert the result into a list of dictionaries (easier to work with in the template)
    food_items = [
        {'id': food.id, 'name': food.name, 'price': food.price} for food in result
    ]

    return render_template('restaurant_menu.html', available_food_items=food_items, is_open=is_open)


@main.route('/restaurant')
def restaurant():
    # Fetch only available food items for customers
    available_food_items = Food.query.filter_by(status='Available').all()
    return render_template('restaurant.html', available_food_items=available_food_items)


@main.route('/restaurant_dashboard', methods=['GET'])
@login_required
def restaurant_dashboard():
    if session.get('user_role') != 'restaurant_tender':
        flash('Access denied!', 'error')
        return redirect(url_for('main.dashboard'))

    # Filter for food items that are available and of type 'restaurant'
    food_items = Food.query.filter_by(type='restaurant', status='Available').all()
    return render_template('restaurant_chef_dashboard.html', food_items=food_items)


@main.route('/order_food/<int:food_id>', methods=['GET', 'POST'])
def order_food(food_id):
    food = Food.query.get(food_id)

    if food.status == 'Unavailable':
        flash('This food item is currently unavailable.', 'error')
        return redirect(url_for('main.restaurant_menu'))

    if request.method == 'POST':
        customer_name = request.form['name']
        phone_number = request.form['phone']
        collection_time = request.form['collection_time']

        # Validate collection time is between 9:30 and 21:30
        if not (9 <= int(collection_time.split(":")[0]) <= 21):
            flash('Invalid collection time. Must be between 9:30 and 21:30.', 'error')
            return redirect(url_for('main.order_food', food_id=food.id))

        # Process payment (this could integrate with a payment gateway)
        payment_method = request.form['payment_method']

        flash(f"Thank you! Your order for {food.name} will be ready at {collection_time}.", 'success')
        return redirect(url_for('main.restaurant_dashboard'))  # Redirect to chef dashboard

    return render_template('order_food.html', food=food)



@main.route('/place_order', methods=['POST'], endpoint='place_order_endpoint')
def place_order():
    food_id = request.form['food_id']
    food_name = request.form['food_name']
    quantity = int(request.form['quantity'])
    customer_name = request.form['customer_name']
    table_number = request.form.get('table_number', '')
    address = request.form.get('address', '')
    phone = request.form['phone']

    # Create a new order
    order = Order(
        food_id=food_id,
        food_name=food_name,
        quantity=quantity,
        customer_name=customer_name,
        table_number=table_number,
        address=address,
        phone=phone
    )

    # Save order to the database
    db.session.add(order)
    db.session.commit()

    flash(f"Order for {food_name} placed successfully!", 'success')
    return redirect(url_for('main.restaurant'))




@main.route('/add_food', methods=['GET', 'POST'])
def add_food():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])  # Convert the price to float
        status = request.form['status']
        type_of_food = 'restaurant'  # Assuming you want to always categorize the food under 'restaurant'

        # Add the new food item to the database
        new_food = Food(name=name, price=price, status=status, type=type_of_food)
        db.session.add(new_food)
        db.session.commit()

        # Fetch all food items for the chef dashboard
        food_items = Food.query.all()

        # Fetch only available food items for the restaurant menu (to be shown in the restaurant's menu page)
        available_food_items = Food.query.filter_by(status='Available').all()

        # Render the chef's dashboard with the updated list of food items
        return render_template('restaurant_chef_dashboard.html', food_items=food_items,
                               available_food_items=available_food_items, added_food=new_food)

    # If it's a GET request, fetch all food items and available items for the menu
    food_items = Food.query.all()
    available_food_items = Food.query.filter_by(status='Available').all()
    return render_template('restaurant_chef_dashboard.html', food_items=food_items,
                           available_food_items=available_food_items)


# Route to delete a food item
@main.route('/delete_food/<int:food_id>', methods=['GET', 'POST'])
@login_required
def delete_food(food_id):
    food = Food.query.get(food_id)

    if food:
        db.session.delete(food)
        db.session.commit()
        flash(f"The food item '{food.name}' has been deleted.", 'success')
    else:
        flash("Food item not found.", 'error')

    return redirect(url_for('main.restaurant_dashboard'))


@main.route('/open_stock')
def open_stock():
    return render_template('open_stock.html')

@main.route('/close_stock')
def closing_stock():
    return render_template('closing_stock.html')


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
