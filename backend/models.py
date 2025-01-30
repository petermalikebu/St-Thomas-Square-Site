from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

# Initialize SQLAlchemy
db = SQLAlchemy()

import uuid

def generate_unique_id():
    # Use UUID4 for randomness or UUID1 for uniqueness based on time and machine
    return str(uuid.uuid4())  # Generates a new unique UUID

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Use integer IDs
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # Possible values: 'user', 'admin'
    phone = db.Column(db.String(15), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.username}, Role: {self.role}>"



class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # e.g., 'restaurant', 'snack', etc.

    def __repr__(self):
        return f"<MenuItem {self.name}>"

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    food_item = db.Column(db.String(100), nullable=False)
    pickup_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Completed', etc.
    order_time = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))

    def __repr__(self):
        return f"<Order {self.food_item} for {self.user_id}>"

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='available')  # 'available', 'booked'
    booked_by = db.Column(db.JSON, nullable=True)  # Store booking details
    is_available = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Room {self.name} - {self.status}>"

class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Event {self.name} on {self.date}>"

class Staff(db.Model):
    __tablename__ = 'staff'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=True)


    def __repr__(self):
        return f"<Staff {self.name} - {self.position}>"


class BarStock(db.Model):
    __tablename__ = 'bar_stock'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price_per_bottle = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BarStock {self.name} - {self.quantity} bottles>"

class SalesRecord(db.Model):
    __tablename__ = 'sales_record'

    id = db.Column(db.Integer, primary_key=True)
    bartender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    beer_id = db.Column(db.Integer, db.ForeignKey('bar_stock.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    remaining_stock = db.Column(db.Integer, nullable=False)

    bartender = db.relationship('User', backref='sales')
    beer = db.relationship('BarStock', backref='sales')

    def __repr__(self):
        return f"<SalesRecord {self.quantity_sold} of {self.beer.name}>"


class BartenderStock(db.Model):
    __tablename__ = 'bartender_stocks'
    id = db.Column(db.Integer, primary_key=True)
    bartender_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Updated to use UUID
    beer_id = db.Column(db.Integer, db.ForeignKey('beer.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_bottle = db.Column(db.Float, nullable=False)
    total_value = db.Column(db.Float, nullable=True)  # Add this field

    bartender = db.relationship('User', backref=db.backref('bartender_stocks', lazy=True))
    beer = db.relationship('Beer', backref=db.backref('bartender_stocks', lazy=True))

    def __repr__(self):
        return f"<BartenderStock {self.quantity} of {self.beer.name}>"


class BeerStock(db.Model):
    __tablename__ = 'beer_stock'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    beer_type = db.Column(db.String(50), nullable=False)  # E.g., Lager, Ale
    price_per_bottle = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_value = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BeerStock {self.name}, Type: {self.beer_type}>"


class BartenderTransaction(db.Model):
    __tablename__ = 'bartender_transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bartender_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)  # Updated to use UUID
    beer_id = db.Column(db.Integer, db.ForeignKey('beer_stock.id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)

    bartender = db.relationship('User', backref=db.backref('transactions', lazy=True))
    beer = db.relationship('BeerStock', backref=db.backref('transactions', lazy=True))

    def __repr__(self):
        return f"<BartenderTransaction(Beer ID: {self.beer_id}, Quantity Sold: {self.quantity_sold}, Total Price: {self.total_price})>"


class OpeningBalance(db.Model):
    __tablename__ = 'opening_balance'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    balance = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<OpeningBalance {self.balance} on {self.date}>"


class Beer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price_per_bottle = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    @property
    def total_value(self):
        return self.price_per_bottle * self.quantity

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="Available")  # Available/Out of Stock
    type = db.Column(db.String(50), nullable=False)  # e.g., 'restaurant'
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Food {self.name}>"