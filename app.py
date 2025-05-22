from flask import Flask, render_template, redirect, url_for,request
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField
from wtforms.validators import DataRequired
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange
room_selection_to_occupancy_factor = {
        "Office,labs pharmacies, reception areas, waiting room,kid play area Patient Exam and Treatment Room":1,
        "Corridor, Patient Room, Employee Lounges, Staff Rest Room":0.5,
        "Corridor doors": 0.2,
        "Public toilets, unattended vending areas, storage rooms, outdoor areas with seating, unattended waiting rooms, patient holding areas":0.13,
        "Outdoor areas with only transient pedestrian or vehicular traffic, unattended parking lots, vehicular drop off areas (unattended), attics, stairways, unattended elevators, janitor’s closets":0.05,
        "Other":1
    }

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
        choices = [(v, k) for k, v in room_selection_to_occupancy_factor.items()],
        validators=[DataRequired()]
    )
        
    design_goal = SelectField('Design Goal', choices=[
        ('0.1', 'Controlled'),
        ('0.02', 'Uncontrolled')
    ], default='Controlled', validators=[DataRequired()])    
    
    
    occupancy_factor = FloatField('Occupancy Factor (0–1)', default=1, validators=[
        DataRequired(), NumberRange(min=0, max=1, message="Must be between 0 and 1")
    ])
    
    distance_to_barrier = FloatField('Distance to Barrier (m)', default=3,validators=[DataRequired()])
    
    air_kerma = FloatField('Air Kerma at 1 m (mGy)', default=3.8,validators=[DataRequired()])
    
    wall_material = SelectField('Wall Material', choices=[
        ('Lead', 'Lead'),
        ('Concrete', 'Concrete'),
        ('Gypsum', 'Gypsum'),
        ('Steel', 'Steel'),
        ('Plate Glass', 'Plate Glass'),
        ('Wood', 'Wood')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Submit')
def calc_barrier_t(P,d,T,K,U,N):
    return P*d**2 /(T*K*U*N)
def calc_x_barrier(P,T,d,K,N,alpha,beta,gamma,U=1):
    B = calc_barrier_t(P,d,T,K,U,N)
    return (1/(alpha*gamma)) * np.log((B**-gamma + beta/alpha)/(1+beta/alpha))


def get_material_constants(material):
    """
    Returns (alpha, beta, gamma) for a given wall material.
    """
    coeffs = MATERIAL_COEFFICIENTS.get(material)
    if coeffs is None:
        raise ValueError(f"Unknown wall material: {material}")
    return coeffs["alpha"], coeffs["beta"], coeffs["gamma"]

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ShieldingForm()

    if form.validate_on_submit():
        patient_workload = form.patient_workload.data
        distance_to_barrier = form.distance_to_barrier.data
        air_kerma = form.air_kerma.data
        wall_material = form.wall_material.data
        room_type = form.room_type.data
        occupancy_factor = form.occupancy_factor.data
        # Get dynamically calculated hidden fields
        # design_goal = float(request.form.get('design_goal'))
        design_goal = float(request.form.get('design_goal'))
        use_factor = 1

        # Lookup material coefficients
        alpha, beta, gamma = get_material_constants(wall_material)
        P = design_goal
        N = patient_workload
        d = distance_to_barrier
        K = air_kerma
        T= occupancy_factor
        U = use_factor
        print(
            {P,
            N,
            d,
            K,
            T,
            U}
        )
        
        # Perform multiplication
        x_barrier = calc_x_barrier(P,T,d,K,N,alpha,beta ,gamma)
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
            x_barrier=x_barrier
        )

    return render_template('form.html', form=form)


@app.route('/success')
def success():
    return "Form submitted successfully!"

if __name__ == '__main__':
    app.run(debug=True)
