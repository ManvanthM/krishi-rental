import os
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from datetime import date, datetime
from functools import wraps

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "krishi-equipment-secret-key")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

DATABASE_URL = os.environ.get("DATABASE_URL", "")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    """Create a PostgreSQL database connection using the DATABASE_URL env variable."""
    return psycopg2.connect(DATABASE_URL)


def query_db(
    query,
    params=None,
    fetchone=False,
    fetchall=False,
    commit=False,
    return_lastrowid=False,
):
    """Run a database query with optional fetch and commit support."""
    connection = get_db_connection()
    cursor = connection.cursor(cursor_factory=RealDictCursor)
    result = None

    try:
        if return_lastrowid:
            # Append RETURNING id so we can retrieve the new row id
            returning_query = query.rstrip().rstrip(';') + " RETURNING id"
            cursor.execute(returning_query, params or ())
            row = cursor.fetchone()
            connection.commit()
            result = row["id"] if row else None
        else:
            cursor.execute(query, params or ())
            if commit:
                connection.commit()
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()

        return result
    finally:
        cursor.close()
        connection.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_obj, prefix):
    """Persist an uploaded file and return the stored filename."""
    if not file_obj or file_obj.filename == "":
        return None

    if not allowed_file(file_obj.filename):
        raise ValueError("Only PNG, JPG, JPEG, WEBP, or PDF files are allowed.")

    extension = file_obj.filename.rsplit(".", 1)[1].lower()
    filename = f"{prefix}_{uuid.uuid4().hex}.{extension}"
    file_obj.save(os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(filename)))
    return filename


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def calculate_total_days(from_date, to_date):
    return (to_date - from_date).days + 1


def is_valid_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    return len(digits) == 10


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id") or not session.get("role"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


def redirect_to_dashboard():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "producer":
        return redirect(url_for("producer_dashboard"))
    if role == "farmer":
        return redirect(url_for("farmer_dashboard"))
    if role == "qc":
        return redirect(url_for("qc_dashboard"))
    return redirect(url_for("login"))


def create_default_admin():
    """Create a default admin when the database has been set up but no admin exists yet."""
    try:
        admin = query_db(
            "SELECT id FROM users WHERE role = 'admin' LIMIT 1",
            fetchone=True,
        )
        if not admin:
            query_db(
                """
                INSERT INTO users (name, email, password, role, phone, address)
                VALUES (%s, %s, %s, 'admin', %s, %s)
                """,
                (
                    "System Admin",
                    "admin@gmail.com",
                    "123456",
                    "9999999999",
                    "Head Office",
                ),
                commit=True,
            )
    except Exception:
        # The database might not be reachable yet (e.g. during first deploy).
        return


@app.context_processor
def inject_session_data():
    return {"today": date.today()}


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect_to_dashboard()
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect_to_dashboard()

    if request.method == "POST":
        role = request.form.get("role", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if role not in {"admin", "producer", "farmer", "qc"}:
            flash("Please choose a valid role.", "danger")
            return redirect(url_for("login"))

        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for("login"))

        try:
            if role == "qc":
                user = query_db(
                    "SELECT * FROM qc_users WHERE email = %s",
                    (email,),
                    fetchone=True,
                )
                if not user or user["password"] != password:
                    flash("Invalid QC credentials.", "danger")
                    return redirect(url_for("login"))

                session.clear()
                session["user_id"] = user["id"]
                session["role"] = "qc"
                session["name"] = user["name"]
                session["producer_id"] = user["producer_id"]
                return redirect(url_for("qc_dashboard"))

            user = query_db(
                "SELECT * FROM users WHERE email = %s AND role = %s",
                (email, role),
                fetchone=True,
            )

            if not user or user["password"] != password:
                flash("Invalid login credentials.", "danger")
                return redirect(url_for("login"))

            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            return redirect_to_dashboard()
        except Exception as exc:
            flash(f"Database error: {exc}", "danger")

    return render_template("login.html")


@app.route("/register/farmer", methods=["GET", "POST"])
def register_farmer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        aadhaar = request.form.get("aadhaar", "").strip()
        aadhaar_image = request.files.get("aadhaar_image")

        if not all([name, email, password, phone, aadhaar]):
            flash("All fields are required for farmer registration.", "danger")
            return redirect(url_for("register_farmer"))

        if len(aadhaar) != 12 or not aadhaar.isdigit():
            flash("Aadhaar number must contain exactly 12 digits.", "danger")
            return redirect(url_for("register_farmer"))

        if not is_valid_phone(phone):
            flash("Phone number must contain 10 digits.", "danger")
            return redirect(url_for("register_farmer"))

        try:
            existing_user = query_db(
                "SELECT id FROM users WHERE email = %s",
                (email,),
                fetchone=True,
            )
            if existing_user:
                flash("An account with this email already exists.", "warning")
                return redirect(url_for("register_farmer"))

            existing_aadhaar = query_db(
                "SELECT id FROM users WHERE aadhaar = %s",
                (aadhaar,),
                fetchone=True,
            )
            if existing_aadhaar:
                flash("This Aadhaar number is already registered.", "warning")
                return redirect(url_for("register_farmer"))

            image_name = save_upload(aadhaar_image, "aadhaar")
            if not image_name:
                flash("Aadhaar image upload is required.", "danger")
                return redirect(url_for("register_farmer"))

            query_db(
                """
                INSERT INTO users (name, email, password, role, phone, aadhaar, aadhaar_image)
                VALUES (%s, %s, %s, 'farmer', %s, %s, %s)
                """,
                (
                    name,
                    email,
                    password,
                    phone,
                    aadhaar,
                    image_name,
                ),
                commit=True,
            )
            flash("Farmer registration completed. Please log in.", "success")
            return redirect(url_for("login"))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            flash(f"Could not register farmer: {exc}", "danger")

    return render_template("register_farmer.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return redirect_to_dashboard()


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    try:
        producer_count = query_db(
            "SELECT COUNT(*) AS total FROM users WHERE role = 'producer'",
            fetchone=True,
        )["total"]
        farmer_count = query_db(
            "SELECT COUNT(*) AS total FROM users WHERE role = 'farmer'",
            fetchone=True,
        )["total"]
        overdue_count = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            WHERE status = 'Rented' AND to_date < CURDATE()
            """,
            fetchone=True,
        )["total"]
        overdue_rentals = query_db(
            """
            SELECT rentals.id, rentals.to_date, users.name AS farmer_name, users.phone,
                   equipment.name AS equipment_name
            FROM rentals
            INNER JOIN users ON rentals.farmer_id = users.id
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE rentals.status = 'Rented' AND rentals.to_date < CURDATE()
            ORDER BY rentals.to_date ASC
            """,
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to load admin dashboard: {exc}", "danger")
        producer_count = farmer_count = overdue_count = 0
        overdue_rentals = []

    return render_template(
        "admin_dashboard.html",
        producer_count=producer_count,
        farmer_count=farmer_count,
        overdue_count=overdue_count,
        overdue_rentals=overdue_rentals,
    )


@app.route("/admin/producers", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_producers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not all([name, email, password, phone, address]):
            flash("All producer fields are required.", "danger")
            return redirect(url_for("admin_producers"))

        if not is_valid_phone(phone):
            flash("Producer phone number must contain 10 digits.", "danger")
            return redirect(url_for("admin_producers"))

        try:
            existing_user = query_db(
                "SELECT id FROM users WHERE email = %s",
                (email,),
                fetchone=True,
            )
            if existing_user:
                flash("Producer email already exists.", "warning")
                return redirect(url_for("admin_producers"))

            query_db(
                """
                INSERT INTO users (name, email, password, role, phone, address)
                VALUES (%s, %s, %s, 'producer', %s, %s)
                """,
                (name, email, password, phone, address),
                commit=True,
            )
            flash("Producer added successfully.", "success")
            return redirect(url_for("admin_producers"))
        except Exception as exc:
            flash(f"Unable to add producer: {exc}", "danger")

    try:
        producers = query_db(
            """
            SELECT id, name, email, phone, address, created_at
            FROM users
            WHERE role = 'producer'
            ORDER BY created_at DESC
            """,
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch producers: {exc}", "danger")
        producers = []

    return render_template("admin_producers.html", producers=producers)


@app.route("/admin/producers/delete/<int:producer_id>", methods=["POST"])
@login_required
@role_required("admin")
def delete_producer(producer_id):
    try:
        query_db(
            "DELETE FROM users WHERE id = %s AND role = 'producer'",
            (producer_id,),
            commit=True,
        )
        flash("Producer deleted successfully.", "success")
    except Exception as exc:
        flash(f"Unable to delete producer: {exc}", "danger")
    return redirect(url_for("admin_producers"))


@app.route("/admin/farmers")
@login_required
@role_required("admin")
def admin_farmers():
    try:
        farmers = query_db(
            """
            SELECT id, name, email, phone, aadhaar, aadhaar_image, created_at
            FROM users
            WHERE role = 'farmer'
            ORDER BY created_at DESC
            """,
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch farmers: {exc}", "danger")
        farmers = []

    return render_template("admin_farmers.html", farmers=farmers)


@app.route("/admin/alerts")
@login_required
@role_required("admin")
def admin_alerts():
    try:
        overdue_rentals = query_db(
            """
            SELECT rentals.id, rentals.from_date, rentals.to_date, rentals.total_days,
                   users.name AS farmer_name, users.phone, users.email,
                   equipment.name AS equipment_name
            FROM rentals
            INNER JOIN users ON rentals.farmer_id = users.id
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE rentals.status = 'Rented' AND rentals.to_date < CURRENT_DATE
            ORDER BY rentals.to_date ASC
            """,
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch overdue alerts: {exc}", "danger")
        overdue_rentals = []

    return render_template("admin_alerts.html", overdue_rentals=overdue_rentals)


@app.route("/producer/dashboard")
@login_required
@role_required("producer")
def producer_dashboard():
    producer_id = session["user_id"]

    try:
        equipment_count = query_db(
            "SELECT COUNT(*) AS total FROM equipment WHERE producer_id = %s",
            (producer_id,),
            fetchone=True,
        )["total"]
        active_rentals = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE equipment.producer_id = %s AND rentals.status = 'Rented'
            """,
            (producer_id,),
            fetchone=True,
        )["total"]
        qc_count = query_db(
            "SELECT COUNT(*) AS total FROM qc_users WHERE producer_id = %s",
            (producer_id,),
            fetchone=True,
        )["total"]
        recent_equipment = query_db(
            """
            SELECT id, name, quantity, rent_per_day, deposit
            FROM equipment
            WHERE producer_id = %s
            ORDER BY created_at DESC
            LIMIT 6
            """,
            (producer_id,),
            fetchall=True,
        )
        overdue_rentals = query_db(
            """
            SELECT rentals.id, rentals.from_date, rentals.to_date, rentals.total_days,
                   users.name AS farmer_name, users.phone, users.email AS farmer_email,
                   equipment.name AS equipment_name,
                   (CURRENT_DATE - rentals.to_date) as days_overdue
            FROM rentals
            INNER JOIN users ON rentals.farmer_id = users.id
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE equipment.producer_id = %s AND rentals.status = 'Rented' AND rentals.to_date < CURRENT_DATE
            ORDER BY rentals.to_date ASC
            """,
            (producer_id,),
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to load producer dashboard: {exc}", "danger")
        equipment_count = active_rentals = qc_count = 0
        recent_equipment = []
        overdue_rentals = []

    return render_template(
        "producer_dashboard.html",
        equipment_count=equipment_count,
        active_rentals=active_rentals,
        qc_count=qc_count,
        recent_equipment=recent_equipment,
        overdue_rentals=overdue_rentals,
    )

@app.route("/producer/send_alert/<int:rental_id>", methods=["POST"])
@login_required
@role_required("producer")
def producer_send_alert(rental_id):
    producer_id = session["user_id"]
    try:
        rental_data = query_db(
            """
            SELECT rentals.id, rentals.to_date, users.name AS farmer_name, users.email AS farmer_email,
                   equipment.name AS equipment_name,
                   (CURRENT_DATE - rentals.to_date) as days_overdue
            FROM rentals
            INNER JOIN users ON rentals.farmer_id = users.id
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE rentals.id = %s AND equipment.producer_id = %s AND rentals.status = 'Rented' AND rentals.to_date < CURRENT_DATE
            """,
            (rental_id, producer_id),
            fetchone=True,
        )
        if not rental_data:
            flash("Invalid or unauthorized alert request.", "danger")
            return redirect(url_for("producer_dashboard"))
        
        smtp_user = os.environ.get("SMTP_USER", "")
        farmer_email = rental_data["farmer_email"]
        equipment_name = rental_data["equipment_name"]
        
        print(f"\n--- SIMULATED EMAIL DISPATCH ---")
        print(f"TO: {farmer_email}")
        print(f"SUBJECT: URGENT: Delayed Equipment Return - {equipment_name}")
        print(f"BODY: Dear {rental_data['farmer_name']},\n\nOur records indicate your rental for '{equipment_name}' is {rental_data['days_overdue']} days overdue. Please return it immediately.\n\nThank you,\nKrishi Rental Platform")
        print(f"--------------------------------\n")
        
        if not smtp_user:
            flash(f"Simulated alert email safely generated on the server for {farmer_email}.", "success")
        else:
            import smtplib
            from email.message import EmailMessage
            try:
                msg = EmailMessage()
                msg.set_content(f"Dear {rental_data['farmer_name']},\n\nOur records indicate your rental for '{equipment_name}' is {rental_data['days_overdue']} days overdue. Please return it to the Quality Checker immediately to minimize further late fines.\n\nThank you,\nKrishi Rental Platform")
                msg['Subject'] = f"URGENT: Delayed Equipment Return - {equipment_name}"
                msg['From'] = smtp_user
                msg['To'] = farmer_email
                
                server = smtplib.SMTP(os.environ.get("SMTP_SERVER", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", 587)))
                server.starttls()
                server.login(smtp_user, os.environ.get("SMTP_PASS", ""))
                server.send_message(msg)
                server.quit()
                flash(f"Alert email successfully sent to {farmer_email}.", "success")
            except Exception as e:
                flash(f"Failed to send real email due to SMTP error: {e}", "danger")
                
    except Exception as exc:
        flash(f"Database error while attempting to send alert: {exc}", "danger")

    return redirect(url_for("producer_dashboard"))


@app.route("/producer/equipment", methods=["GET", "POST"])
@login_required
@role_required("producer")
def producer_equipment():
    producer_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        rent_per_day = request.form.get("rent_per_day", "").strip()
        quantity = request.form.get("quantity", "").strip()
        max_days = request.form.get("max_days", "").strip()
        deposit = request.form.get("deposit", "").strip()
        image = request.files.get("image")

        if not all([name, description, rent_per_day, quantity, max_days, deposit]):
            flash("All equipment fields are required.", "danger")
            return redirect(url_for("producer_equipment"))

        try:
            rent_per_day_value = float(rent_per_day)
            quantity_value = int(quantity)
            max_days_value = int(max_days)
            deposit_value = float(deposit)

            if (
                rent_per_day_value <= 0
                or quantity_value < 0
                or max_days_value <= 0
                or deposit_value < 0
            ):
                raise ValueError("Numeric values must be positive.")

            image_name = save_upload(image, "equipment")
            if not image_name:
                flash("Equipment image upload is required.", "danger")
                return redirect(url_for("producer_equipment"))

            query_db(
                """
                INSERT INTO equipment
                (producer_id, name, description, rent_per_day, quantity, max_days, deposit, image)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    producer_id,
                    name,
                    description,
                    rent_per_day_value,
                    quantity_value,
                    max_days_value,
                    deposit_value,
                    image_name,
                ),
                commit=True,
            )
            flash("Equipment added successfully.", "success")
            return redirect(url_for("producer_equipment"))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            flash(f"Unable to add equipment: {exc}", "danger")

    try:
        equipment_list = query_db(
            """
            SELECT id, name, description, rent_per_day, quantity, max_days, deposit, image, created_at
            FROM equipment
            WHERE producer_id = %s
            ORDER BY created_at DESC
            """,
            (producer_id,),
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch equipment list: {exc}", "danger")
        equipment_list = []

    return render_template("producer_equipment.html", equipment_list=equipment_list)


@app.route("/producer/equipment/edit/<int:equipment_id>", methods=["GET", "POST"])
@login_required
@role_required("producer")
def edit_equipment(equipment_id):
    producer_id = session["user_id"]

    try:
        equipment_item = query_db(
            "SELECT * FROM equipment WHERE id = %s AND producer_id = %s",
            (equipment_id, producer_id),
            fetchone=True,
        )
    except Exception as exc:
        flash(f"Unable to load equipment: {exc}", "danger")
        return redirect(url_for("producer_equipment"))

    if not equipment_item:
        flash("Equipment not found.", "warning")
        return redirect(url_for("producer_equipment"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        rent_per_day = request.form.get("rent_per_day", "").strip()
        quantity = request.form.get("quantity", "").strip()
        max_days = request.form.get("max_days", "").strip()
        deposit = request.form.get("deposit", "").strip()
        image = request.files.get("image")

        if not all([name, description, rent_per_day, quantity, max_days, deposit]):
            flash("All fields except image are required.", "danger")
            return redirect(url_for("edit_equipment", equipment_id=equipment_id))

        try:
            image_name = equipment_item["image"]
            new_image = save_upload(image, "equipment")
            if new_image:
                image_name = new_image

            query_db(
                """
                UPDATE equipment
                SET name = %s, description = %s, rent_per_day = %s, quantity = %s,
                    max_days = %s, deposit = %s, image = %s
                WHERE id = %s AND producer_id = %s
                """,
                (
                    name,
                    description,
                    float(rent_per_day),
                    int(quantity),
                    int(max_days),
                    float(deposit),
                    image_name,
                    equipment_id,
                    producer_id,
                ),
                commit=True,
            )
            flash("Equipment updated successfully.", "success")
            return redirect(url_for("producer_equipment"))
        except ValueError:
            flash("Please enter valid numeric values.", "danger")
        except Exception as exc:
            flash(f"Unable to update equipment: {exc}", "danger")

    return render_template("producer_edit_equipment.html", equipment=equipment_item)


@app.route("/producer/equipment/delete/<int:equipment_id>", methods=["POST"])
@login_required
@role_required("producer")
def delete_equipment(equipment_id):
    producer_id = session["user_id"]

    try:
        query_db(
            "DELETE FROM equipment WHERE id = %s AND producer_id = %s",
            (equipment_id, producer_id),
            commit=True,
        )
        flash("Equipment deleted successfully.", "success")
    except Exception as exc:
        flash(f"Unable to delete equipment: {exc}", "danger")

    return redirect(url_for("producer_equipment"))


@app.route("/producer/qc", methods=["GET", "POST"])
@login_required
@role_required("producer")
def producer_qc():
    producer_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not all([name, email, phone, password]):
            flash("All QC fields are required.", "danger")
            return redirect(url_for("producer_qc"))

        if not is_valid_phone(phone):
            flash("QC phone number must contain 10 digits.", "danger")
            return redirect(url_for("producer_qc"))

        try:
            existing_qc = query_db(
                "SELECT id FROM qc_users WHERE email = %s",
                (email,),
                fetchone=True,
            )
            if existing_qc:
                flash("QC email already exists.", "warning")
                return redirect(url_for("producer_qc"))

            query_db(
                """
                INSERT INTO qc_users (producer_id, name, email, phone, password)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    producer_id,
                    name,
                    email,
                    phone,
                    password,
                ),
                commit=True,
            )
            flash("Quality checker added successfully.", "success")
            return redirect(url_for("producer_qc"))
        except Exception as exc:
            flash(f"Unable to add quality checker: {exc}", "danger")

    try:
        qc_users = query_db(
            """
            SELECT id, name, email, phone, created_at
            FROM qc_users
            WHERE producer_id = %s
            ORDER BY created_at DESC
            """,
            (producer_id,),
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch quality checkers: {exc}", "danger")
        qc_users = []

    return render_template("producer_qc.html", qc_users=qc_users)


@app.route("/producer/qc/delete/<int:qc_id>", methods=["POST"])
@login_required
@role_required("producer")
def delete_qc(qc_id):
    producer_id = session["user_id"]
    try:
        query_db(
            "DELETE FROM qc_users WHERE id = %s AND producer_id = %s",
            (qc_id, producer_id),
            commit=True,
        )
        flash("Quality checker deleted successfully.", "success")
    except Exception as exc:
        flash(f"Unable to delete quality checker: {exc}", "danger")

    return redirect(url_for("producer_qc"))


@app.route("/farmer/dashboard")
@login_required
@role_required("farmer")
def farmer_dashboard():
    farmer_id = session["user_id"]

    try:
        available_equipment = query_db(
            "SELECT COUNT(*) AS total FROM equipment WHERE quantity > 0",
            fetchone=True,
        )["total"]
        active_rentals = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            WHERE farmer_id = %s AND status = 'Rented'
            """,
            (farmer_id,),
            fetchone=True,
        )["total"]
        in_qc = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            WHERE farmer_id = %s AND status = 'In QC'
            """,
            (farmer_id,),
            fetchone=True,
        )["total"]
        featured_equipment = query_db(
            """
            SELECT equipment.*, users.name AS producer_name
            FROM equipment
            INNER JOIN users ON equipment.producer_id = users.id
            WHERE equipment.quantity > 0
            ORDER BY equipment.created_at DESC
            LIMIT 6
            """,
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to load farmer dashboard: {exc}", "danger")
        available_equipment = active_rentals = in_qc = 0
        featured_equipment = []

    return render_template(
        "farmer_dashboard.html",
        available_equipment=available_equipment,
        active_rentals=active_rentals,
        in_qc=in_qc,
        featured_equipment=featured_equipment,
    )


@app.route("/farmer/equipment")
@login_required
@role_required("farmer")
def farmer_equipment():
    search = request.args.get("search", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()

    query = """
        SELECT equipment.*, users.name AS producer_name, users.phone AS producer_phone
        FROM equipment
        INNER JOIN users ON equipment.producer_id = users.id
        WHERE equipment.quantity > 0
    """
    params = []

    if search:
        query += " AND equipment.name ILIKE %s"
        params.append(f"%{search}%")

    if min_price:
        query += " AND equipment.rent_per_day >= %s"
        params.append(min_price)

    if max_price:
        query += " AND equipment.rent_per_day <= %s"
        params.append(max_price)

    query += " ORDER BY equipment.created_at DESC"

    try:
        equipment_list = query_db(query, tuple(params), fetchall=True)
    except Exception as exc:
        flash(f"Unable to fetch equipment catalog: {exc}", "danger")
        equipment_list = []

    return render_template(
        "farmer_equipment.html",
        equipment_list=equipment_list,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )


@app.route("/farmer/rent/<int:equipment_id>", methods=["GET", "POST"])
@login_required
@role_required("farmer")
def rent_equipment(equipment_id):
    farmer_id = session["user_id"]

    try:
        equipment_item = query_db(
            """
            SELECT equipment.*, users.name AS producer_name
            FROM equipment
            INNER JOIN users ON equipment.producer_id = users.id
            WHERE equipment.id = %s
            """,
            (equipment_id,),
            fetchone=True,
        )
    except Exception as exc:
        flash(f"Unable to load equipment: {exc}", "danger")
        return redirect(url_for("farmer_equipment"))

    if not equipment_item or equipment_item["quantity"] <= 0:
        flash("Equipment is not available right now.", "warning")
        return redirect(url_for("farmer_equipment"))

    if request.method == "POST":
        from_date_raw = request.form.get("from_date", "").strip()
        to_date_raw = request.form.get("to_date", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        accepted_terms = request.form.get("accepted_terms")

        if not all([from_date_raw, to_date_raw, payment_method]):
            flash("Please fill in the rental dates and payment method.", "danger")
            return redirect(url_for("rent_equipment", equipment_id=equipment_id))

        if payment_method not in {"UPI", "Card"}:
            flash("Invalid payment method selected.", "danger")
            return redirect(url_for("rent_equipment", equipment_id=equipment_id))

        if accepted_terms != "yes":
            flash("You must accept the terms and conditions.", "danger")
            return redirect(url_for("rent_equipment", equipment_id=equipment_id))

        try:
            from_date = parse_date(from_date_raw)
            to_date = parse_date(to_date_raw)

            if from_date < date.today():
                raise ValueError("Rental start date cannot be in the past.")

            if to_date < from_date:
                raise ValueError("To date must be later than or equal to from date.")

            total_days = calculate_total_days(from_date, to_date)
            if total_days > 5:
                raise ValueError(
                    "Maximum rental period is 5 days."
                )

            latest_equipment_state = query_db(
                "SELECT quantity FROM equipment WHERE id = %s",
                (equipment_id,),
                fetchone=True,
            )
            if not latest_equipment_state or latest_equipment_state["quantity"] <= 0:
                flash("This equipment just went out of stock. Please try another item.", "warning")
                return redirect(url_for("farmer_equipment"))

            total_rent = total_days * float(equipment_item["rent_per_day"])
            deposit = float(equipment_item["deposit"])

            query_db(
                """
                INSERT INTO rentals
                (farmer_id, equipment_id, from_date, to_date, total_days, total_rent, deposit, status, payment_method)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Rented', %s)
                """,
                (
                    farmer_id,
                    equipment_id,
                    from_date,
                    to_date,
                    total_days,
                    total_rent,
                    deposit,
                    payment_method,
                ),
                commit=True,
            )
            query_db(
                "UPDATE equipment SET quantity = quantity - 1 WHERE id = %s AND quantity > 0",
                (equipment_id,),
                commit=True,
            )
            flash("Equipment rented successfully.", "success")
            return redirect(url_for("farmer_rentals"))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            flash(f"Unable to create rental: {exc}", "danger")

    return render_template("farmer_rent.html", equipment=equipment_item)


@app.route("/farmer/rentals")
@login_required
@role_required("farmer")
def farmer_rentals():
    farmer_id = session["user_id"]

    try:
        rentals = query_db(
            """
            SELECT rentals.*, equipment.name AS equipment_name, equipment.image,
                   users.name AS producer_name
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            INNER JOIN users ON equipment.producer_id = users.id
            WHERE rentals.farmer_id = %s
            ORDER BY rentals.created_at DESC
            """,
            (farmer_id,),
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch rentals: {exc}", "danger")
        rentals = []

    return render_template("farmer_rentals.html", rentals=rentals)


@app.route("/farmer/return/<int:rental_id>", methods=["POST"])
@login_required
@role_required("farmer")
def return_equipment(rental_id):
    farmer_id = session["user_id"]

    try:
        rental = query_db(
            """
            SELECT id, status
            FROM rentals
            WHERE id = %s AND farmer_id = %s
            """,
            (rental_id, farmer_id),
            fetchone=True,
        )

        if not rental or rental["status"] != "Rented":
            flash("Only active rentals can be returned.", "warning")
            return redirect(url_for("farmer_rentals"))

        query_db(
            """
            UPDATE rentals
            SET status = 'In QC', returned_on = CURRENT_DATE
            WHERE id = %s AND farmer_id = %s
            """,
            (rental_id, farmer_id),
            commit=True,
        )
        flash("Return request submitted. Waiting for QC review.", "success")
    except Exception as exc:
        flash(f"Unable to submit return request: {exc}", "danger")

    return redirect(url_for("farmer_rentals"))


@app.route("/qc/dashboard")
@login_required
@role_required("qc")
def qc_dashboard():
    producer_id = session.get("producer_id")

    try:
        pending_returns = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE equipment.producer_id = %s AND rentals.status = 'In QC'
            """,
            (producer_id,),
            fetchone=True,
        )["total"]
        accepted_returns = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE equipment.producer_id = %s AND rentals.status = 'Returned'
            """,
            (producer_id,),
            fetchone=True,
        )["total"]
        rejected_returns = query_db(
            """
            SELECT COUNT(*) AS total
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            WHERE equipment.producer_id = %s AND rentals.status = 'Rejected'
            """,
            (producer_id,),
            fetchone=True,
        )["total"]
    except Exception as exc:
        flash(f"Unable to load QC dashboard: {exc}", "danger")
        pending_returns = accepted_returns = rejected_returns = 0

    return render_template(
        "qc_dashboard.html",
        pending_returns=pending_returns,
        accepted_returns=accepted_returns,
        rejected_returns=rejected_returns,
    )


@app.route("/qc/returns")
@login_required
@role_required("qc")
def qc_returns():
    producer_id = session.get("producer_id")

    try:
        pending_rentals = query_db(
            """
            SELECT rentals.*, users.name AS farmer_name, users.phone,
                   equipment.name AS equipment_name, equipment.image
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            INNER JOIN users ON rentals.farmer_id = users.id
            WHERE equipment.producer_id = %s AND rentals.status = 'In QC'
            ORDER BY rentals.returned_on ASC, rentals.created_at DESC
            """,
            (producer_id,),
            fetchall=True,
        )
        processed_rentals = query_db(
            """
            SELECT rentals.*, users.name AS farmer_name, equipment.name AS equipment_name
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            INNER JOIN users ON rentals.farmer_id = users.id
            WHERE equipment.producer_id = %s AND rentals.status IN ('Returned', 'Rejected')
            ORDER BY rentals.qc_processed_on DESC, rentals.created_at DESC
            LIMIT 10
            """,
            (producer_id,),
            fetchall=True,
        )
    except Exception as exc:
        flash(f"Unable to fetch return requests: {exc}", "danger")
        pending_rentals = []
        processed_rentals = []

    return render_template(
        "qc_returns.html",
        pending_rentals=pending_rentals,
        processed_rentals=processed_rentals,
    )


@app.route("/qc/process/<int:rental_id>", methods=["GET", "POST"])
@login_required
@role_required("qc")
def qc_process_return(rental_id):
    producer_id = session.get("producer_id")
    qc_id = session.get("user_id")

    try:
        rental = query_db(
            """
            SELECT rentals.*, users.name AS farmer_name, equipment.name AS equipment_name,
                   equipment.id AS equipment_ref_id, equipment.producer_id
            FROM rentals
            INNER JOIN equipment ON rentals.equipment_id = equipment.id
            INNER JOIN users ON rentals.farmer_id = users.id
            WHERE rentals.id = %s AND equipment.producer_id = %s
            """,
            (rental_id, producer_id),
            fetchone=True,
        )
    except Exception as exc:
        flash(f"Unable to load return record: {exc}", "danger")
        return redirect(url_for("qc_returns"))

    if not rental or rental["status"] != "In QC":
        flash("This return request is no longer pending QC.", "warning")
        return redirect(url_for("qc_returns"))

    returned_on = rental["returned_on"] or date.today()
    extra_days = max((returned_on - rental["to_date"]).days, 0)
    base_fine = extra_days * 200

    if request.method == "POST":
        action = request.form.get("action", "").strip().lower()
        damage_percent_raw = request.form.get("damage_percent", "0").strip()
        damage_cost_raw = request.form.get("damage_cost", "0").strip()
        qc_notes = request.form.get("qc_notes", "").strip()

        try:
            damage_percent = int(damage_percent_raw or 0)
            damage_cost = float(damage_cost_raw or 0)

            if damage_percent < 0 or damage_percent > 100:
                raise ValueError("Damage percentage must be between 0 and 100.")

            if damage_cost < 0:
                raise ValueError("Damage cost cannot be negative.")

            if action == "accept":
                if damage_percent > 80:
                    raise ValueError("Returns with damage above 80% must be rejected.")

                refund_amount = max(float(rental["deposit"]) - base_fine - damage_cost, 0)
                query_db(
                    """
                    UPDATE rentals
                    SET status = 'Returned', fine_amount = %s, damage_cost = %s,
                        refund_amount = %s, damage_percent = %s, qc_notes = %s,
                        qc_id = %s, qc_processed_on = NOW()
                    WHERE id = %s
                    """,
                    (
                        base_fine,
                        damage_cost,
                        refund_amount,
                        damage_percent,
                        qc_notes,
                        qc_id,
                        rental_id,
                    ),
                    commit=True,
                )
                query_db(
                    "UPDATE equipment SET quantity = quantity + 1 WHERE id = %s",
                    (rental["equipment_ref_id"],),
                    commit=True,
                )
                flash(
                    f"Return accepted. Fine: Rs. {base_fine:.2f}, refund: Rs. {refund_amount:.2f}.",
                    "success",
                )
            elif action == "reject":
                if damage_percent <= 80:
                    raise ValueError("Reject return only when damage exceeds 80%.")

                query_db(
                    """
                    UPDATE rentals
                    SET status = 'Rejected', fine_amount = %s, damage_cost = %s,
                        refund_amount = 0, damage_percent = %s, qc_notes = %s,
                        qc_id = %s, qc_processed_on = NOW()
                    WHERE id = %s
                    """,
                    (
                        base_fine,
                        damage_cost,
                        damage_percent,
                        qc_notes,
                        qc_id,
                        rental_id,
                    ),
                    commit=True,
                )
                flash("Return rejected. Full deposit is withheld.", "warning")
            else:
                raise ValueError("Please choose a valid QC action.")

            return redirect(url_for("qc_returns"))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            flash(f"Unable to process return request: {exc}", "danger")

    return render_template(
        "qc_process_return.html",
        rental=rental,
        extra_days=extra_days,
        base_fine=base_fine,
    )


@app.errorhandler(413)
def file_too_large(_error):
    flash("Uploaded file is too large. Maximum size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("login"))


@app.errorhandler(404)
def page_not_found(_error):
    return render_template("404.html"), 404


create_default_admin()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
