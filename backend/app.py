from datetime import timedelta

from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from backend.models import db, User  # Ensure User is imported

# Initialize Flask extensions outside of create_app
login_manager = LoginManager()

def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
    app.secret_key = 'your_secret_key'  # Replace with a secure key

    # Configure SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Initialize the database
    db.init_app(app)

    # Initialize Flask-Login
    login_manager.init_app(app)

    # Set the login view
    login_manager.login_view = 'main.login'  # Adjust according to your login route

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Import and register blueprints
    from backend.routes import main
    app.register_blueprint(main)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
