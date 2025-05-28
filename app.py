from flask import request, jsonify
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
import numpy as np
from pdf2image import convert_from_bytes
from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Mapping of room types to occupancy factors
ROOM_OCCUPANCY_FACTORS = {
    "Office, labs, pharmacies, reception areas, waiting room, kid play area, Patient Exam and Treatment Room": 1,
    "Corridor, Patient Room, Employee Lounges, Staff Rest Room": 0.5,
    "Corridor doors": 0.2,
    "Public toilets, unattended vending areas, storage rooms, outdoor areas with seating, unattended waiting rooms, patient holding areas": 0.13,
    "Outdoor areas with only transient pedestrian or vehicular traffic, unattended parking lots, vehicular drop off areas (unattended), attics, stairways, unattended elevators, janitor’s closets": 0.05,
    "Other": 1
}

# Material constants for barrier calculations
MATERIAL_COEFFICIENTS = {
    "Lead":        {"alpha": 2.322,    "beta": 12.9,    "gamma": 0.758},
    "Concrete":    {"alpha": 3.63e-2,  "beta": 9.36e-2, "gamma": 0.596},
    "Gypsum":      {"alpha": 1.33e-2,  "beta": 4.10e-2, "gamma": 0.957},
    "Steel":       {"alpha": 2.33e-1,  "beta": 2.21e+0, "gamma": 0.805},
    "Plate Glass": {"alpha": 3.89e-2,  "beta": 8.09e-2, "gamma": 0.852},
    "Wood":        {"alpha": 7.06e-3,  "beta": 4.22e-4, "gamma": 1.66}
}


class ShieldingForm(FlaskForm):
    patient_workload = FloatField('Patient Workload (mA-min/week)', default=7, validators=[
        DataRequired(), NumberRange(min=0.0001, message="Must be > 0")
    ])
    room_type = SelectField(
        'Room Type',
        choices=[(v, k) for k, v in ROOM_OCCUPANCY_FACTORS.items()],
        validators=[DataRequired()]
    )
    design_goal = SelectField('Design Goal', choices=[
        ('0.1', 'Controlled'),
        ('0.02', 'Uncontrolled')
    ], default='Controlled', validators=[DataRequired()])
    occupancy_factor = FloatField('Occupancy Factor (0–1)', default=1, validators=[
        DataRequired(), NumberRange(min=0, max=1, message="Must be between 0 and 1")
    ])

    distance_to_barrier = FloatField(
        'Distance to Barrier (m)', default=3, validators=[DataRequired()])
    air_kerma = FloatField('Air Kerma at 1 m (mGy)',
                           default=3.8, validators=[DataRequired()])

    wall_material = SelectField('Wall Material', choices=[
        ('Lead', 'Lead'),
        ('Concrete', 'Concrete'),
        ('Gypsum', 'Gypsum'),
        ('Steel', 'Steel'),
        ('Plate Glass', 'Plate Glass'),
        ('Wood', 'Wood')
    ], validators=[DataRequired()])

    submit = SubmitField('Submit')


def calc_barrier_t(P, d, T, K, U, N):
    """Calculate the transmission factor B."""
    return P * d**2 / (T * K * U * N)


def calc_x_barrier(P, T, d, K, N, alpha, beta, gamma, U=1):
    """Calculate barrier thickness x."""
    B = calc_barrier_t(P, d, T, K, U, N)
    return (1 / (alpha * gamma)) * np.log((B**-gamma + beta / alpha) / (1 + beta / alpha))

def lead_size(mmLead):
    if mmLead <= 0.79:
        return 2
    if mmLead <= 1:
        return 2.5
    if mmLead <= 1.19:
        return 3
    if mmLead <= 1.58:
        return 4
    if mmLead <= 1.98:
        return 5
    if mmLead <= 2.38:
        return 6
    if mmLead <= 3.17:
        return 8
    return ">8"
def get_material_constants(material):
    """Return (alpha, beta, gamma) for the given wall material."""
    coeffs = MATERIAL_COEFFICIENTS.get(material)
    if coeffs is None:
        raise ValueError(f"Unknown wall material: {material}")
    return coeffs["alpha"], coeffs["beta"], coeffs["gamma"]


@app.route('/', methods=['GET', 'POST'])
def welcome_page():
    return render_template('welcome.html')


@app.route('/basic', methods=['GET', 'POST'])
def index():
    form = ShieldingForm()

    if form.validate_on_submit():
        # Extract form values
        print(form.occupancy_factor.data)
        patient_workload = form.patient_workload.data
        distance_to_barrier = form.distance_to_barrier.data
        air_kerma = form.air_kerma.data
        wall_material = form.wall_material.data
        room_type = form.room_type.data
        occupancy_factor = form.occupancy_factor.data
        design_goal = float(form.design_goal.data)
        use_factor = 1  # Default use factor

        # Get material constants
        alpha, beta, gamma = get_material_constants(wall_material)

        # Compute barrier thickness
        x_barrier = calc_x_barrier(
            P=design_goal,
            T=occupancy_factor,
            d=distance_to_barrier,
            K=air_kerma,
            N=patient_workload,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            U=use_factor
        )

        return render_template(
            'result.html',
            patient_workload=patient_workload,
            distance_to_barrier=distance_to_barrier,
            air_kerma=air_kerma,
            wall_material=wall_material,
            design_goal=design_goal,
            use_factor=use_factor,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            room_type=room_type,
            occupancy_factor=occupancy_factor,
            x_barrier=f"{x_barrier:.3f}"
        )

    return render_template('form.html', form=form)


@app.route('/success')
def success():
    return "Form submitted successfully!"


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/draw', methods=['GET', 'POST'])
def draw():
    if request.method == 'POST':
        file = request.files.get('image')
        if not file or file.filename == '':
            return "No file uploaded", 400

        if not allowed_file(file.filename):
            return "Only image files are allowed (PNG, JPG, JPEG, BMP, GIF).", 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        image_url = url_for('static', filename=f'uploads/{filename}')
        return render_template('draw.html', image_url=image_url)

    return render_template('upload.html')


@app.route("/calculate-thickness", methods=["POST"])
def calculate_thickness_api():
    data = request.get_json()
    workload = data.get("workload")
    air_kerma = data.get("airKerma")
    lines = data.get("lines", [])
    for line in lines:
        try:
            
            # Convert to mm
            distance = line["realLength"] * 2.54 * 1/100

            design_goal = 0.02 if line['designGoal'] == "Uncontrolled" else 0.1
            occupancy = ROOM_OCCUPANCY_FACTORS.get(line['roomType'], 1)
            material = line['wallMaterial']

            alpha, beta, gamma = get_material_constants(material)
            alphaLead, betaLead, gammaLead = get_material_constants("Lead")

            print({alpha, beta, gamma})
            xLead = calc_x_barrier(
                P=design_goal,
                T=occupancy,
                d=distance,
                K=air_kerma,
                N=workload,
                alpha=alphaLead,
                beta=betaLead,
                gamma=gammaLead
            )

            x = calc_x_barrier(
                P=design_goal,
                T=occupancy,
                d=distance,
                K=air_kerma,
                N=workload,
                alpha=alpha,
                beta=beta,
                gamma=gamma
            )
            line['requiredLead'] = lead_size(xLead)


            line['requiredThickness'] = round(x, 2) if x > 0 else "N/A"

        except Exception as e:
            line['requiredThickness'] = f"Error: {str(e)}"
    print(lines)
    return jsonify({"lines": lines})


if __name__ == '__main__':
    app.run(debug=True)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# source .venv/Scripts/activate
# flask --app app run --debug
