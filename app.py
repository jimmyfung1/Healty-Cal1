from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuration for MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '66102010187supawit'
app.config['MYSQL_DB'] = 'healthycal'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Example BMR calculation function (adjust as needed)
def calculate_bmr(user_info):
    try:
        weight = float(user_info['weight'])
        height = float(user_info['height'])
        age = int(user_info['age'])
        gender = user_info['gender'].lower()

        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        return round(bmr, 2)
    except:
        return 0

def calculate_daily_calories(bmr, activity_multiplier):
    try:
        multiplier = float(activity_multiplier)
        return round(multiplier * bmr, 2)
    except:
        return 0

def generate_recommendation(daily_calories):
    try:
        if daily_calories < 1500:
            recommendation = "Your daily calorie intake is below average. Consider incorporating more nutritious foods and regular light exercise into your routine."
        elif 1500 <= daily_calories < 2000:
            recommendation = "Your daily calorie intake is average. Maintain a balanced diet and consider adding moderate exercise for better health."
        elif 2000 <= daily_calories < 2500:
            recommendation = "Your daily calorie intake is above average. Ensure you're getting adequate nutrients and incorporate regular exercise to manage your weight."
        else:
            recommendation = "Your daily calorie intake is high. It's advisable to consult a nutritionist and include regular physical activity to maintain a healthy weight."
        return recommendation
    except Exception as e:
        print(f'Error in generate_recommendation: {e}')
        return "No recommendation available."

# Function to Generate Exercise Recommendation
def generate_exercise_recommendation(activity_multiplier):
    try:
        activity_multiplier = float(activity_multiplier)
        if activity_multiplier <= 1.2:
            exercise = "We recommend incorporating light exercises such as walking, stretching, or yoga into your daily routine."
        elif 1.375 <= activity_multiplier < 1.55:
            exercise = "Consider engaging in moderate exercises like brisk walking, cycling, or light jogging 3-5 times a week."
        elif 1.55 <= activity_multiplier < 1.725:
            exercise = "You should include vigorous exercises such as running, swimming, or high-intensity interval training (HIIT) most days of the week."
        elif 1.725 <= activity_multiplier < 1.9:
            exercise = "Maintain your current high-intensity exercise regimen, including strength training and endurance workouts."
        else:
            exercise = "You have an extremely active lifestyle. Ensure you have adequate rest and recovery periods to prevent overtraining."
        return exercise
    except Exception as e:
        print(f'Error in generate_exercise_recommendation: {e}')
        return "No exercise recommendation available."
    
@app.route('/')
def home():
    return render_template('HomeLogin.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        weight = request.form['weight']
        height = request.form['height']
        age = request.form['age']
        gender = request.form['gender']

        hashed_password = generate_password_hash(password)
        cur = mysql.connection.cursor()
        try:
            cur.execute('SELECT * FROM Users WHERE email = %s OR username = %s', (email, username))
            existing_user = cur.fetchone()
            if existing_user:
                flash('Email or Username already exists.', 'danger')
                return redirect(url_for('register'))

            cur.execute('''INSERT INTO Users (username, email, password, weight, height, age, gender) 
                           VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                        (username, email, hashed_password, weight, height, age, gender))
            mysql.connection.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')
        cur = mysql.connection.cursor()
        try:
            cur.execute('SELECT * FROM Users WHERE email = %s', [email])
            user = cur.fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect email or password.', 'danger')
        except Exception as e:
            flash(f'Login failed: {e}', 'danger')
        finally:
            cur.close()
    return render_template('login.html')

def calculate_macros(weight, bmr):
    # โปรตีน: 1.2-2.0 กรัมต่อน้ำหนักตัว 1 กิโลกรัม
    protein = weight * 1.5  # ใช้อัตรากลาง 1.5 กรัม
    # ไขมัน: 0.8-1.0 กรัมต่อน้ำหนักตัว 1 กิโลกรัม
    fat = weight * 0.8  # ใช้อัตรากลาง 0.8 กรัม
    # คาร์โบไฮเดรต: คำนวณจากแคลอรี่ที่เหลือหลังจากหักโปรตีนและไขมัน
    total_calories = bmr * 1.2  # คำนวณจากอัตราการใช้พลังงานที่ไม่ออกกำลังกาย
    protein_calories = protein * 4  # โปรตีน 1 กรัม = 4 แคลอรี่
    fat_calories = fat * 9  # ไขมัน 1 กรัม = 9 แคลอรี่
    carbs_calories = total_calories - (protein_calories + fat_calories)  # คำนวณแคลอรี่ที่เหลือ
    carbs = carbs_calories / 4  # แป้ง 1 กรัม = 4 แคลอรี่
    return protein, fat, carbs

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor()

    try:
        if request.method == 'POST':
            # อัปเดตข้อมูลผู้ใช้ เช่น น้ำหนัก, ส่วนสูง หรือกิจกรรม
            weight = request.form.get('weight', type=float)
            height = request.form.get('height', type=float)
            age = request.form.get('age', type=int)
            gender = request.form.get('gender', type=str)
            activity_multiplier = request.form.get('activity_multiplier', type=float, default=1.2)

            # อัปเดตข้อมูลในฐานข้อมูล
            cursor.execute('''UPDATE users SET weight=%s, height=%s, age=%s, gender=%s 
                           WHERE user_id=%s''', (weight, height, age, gender, user_id))
            cursor.execute('''INSERT INTO weight_tracking (user_id, weight, activity_multiplier, tracking_date)
                           VALUES (%s, %s, %s, NOW())''', (user_id, weight, activity_multiplier))
            mysql.connection.commit()

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        # ดึงข้อมูลผู้ใช้จากฐานข้อมูล
        cursor.execute('SELECT * FROM users WHERE user_id=%s', [user_id])
        user_info = cursor.fetchone()

        if user_info:
            bmr = calculate_bmr(user_info)
            weight = user_info['weight']

            # คำนวณโปรตีน, ไขมัน และแป้ง
            protein, fat, carbs = calculate_macros(weight, bmr)

            # ดึงข้อมูล activity multiplier จาก weight_tracking หรือ fallback เป็น 1.2
            cursor.execute('''SELECT activity_multiplier FROM weight_tracking 
                           WHERE user_id=%s ORDER BY tracking_date DESC LIMIT 1''', [user_id])
            activity_data = cursor.fetchone()
            activity_multiplier = activity_data['activity_multiplier'] if activity_data and activity_data['activity_multiplier'] else 1.2

            daily_calories = calculate_daily_calories(bmr, activity_multiplier)

            # สร้างคำแนะนำสำหรับอาหารและการออกกำลังกาย
            recommendation = generate_recommendation(daily_calories)
            exercise_recommendation = generate_exercise_recommendation(activity_multiplier)

            # ดึงข้อมูลการติดตามน้ำหนัก
            cursor.execute('''SELECT tracking_id, weight, tracking_date FROM weight_tracking 
                           WHERE user_id=%s ORDER BY tracking_date DESC''', [user_id])
            weight_tracking = cursor.fetchall()

            # ส่งข้อมูลไปยัง template
            return render_template('dashboard.html', user_info=user_info, bmr=bmr, daily_calories=daily_calories,
                                   weight_tracking=weight_tracking, recommendation=recommendation,
                                   exercise_recommendation=exercise_recommendation, protein=protein,
                                   fat=fat, carbs=carbs, activity_multiplier=activity_multiplier)
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
    except Exception as e:
        flash(f'Error loading dashboard: {e}', 'danger')
        return redirect(url_for('login'))
    finally:
        cursor.close()




@app.route('/update_weight', methods=['POST'])
def update_weight():
    if 'user_id' not in session:
        flash('You must log in to update your weight.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    weight = request.form.get('weight', type=float)
    tracking_date = request.form.get('tracking_date')
    activity_level = request.form.get('activity_level', type=float)

    if weight <= 0 or not tracking_date or not activity_level:
        flash('Please provide valid weight, date, and activity level.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # บันทึกน้ำหนักลงใน weight_tracking table
        query = """
            INSERT INTO weight_tracking (user_id, weight, tracking_date, activity_multiplier)
            VALUES (%s, %s, %s, %s)
        """
        cursor = mysql.connection.cursor()
        cursor.execute(query, (user_id, weight, tracking_date, activity_level))
        mysql.connection.commit()

        # คำนวณค่า BMR และ Daily Calories Needed ใหม่
        user_query = "SELECT height, age, gender FROM users WHERE user_id = %s"
        cursor.execute(user_query, (user_id,))
        user = cursor.fetchone()

        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('dashboard'))

        height = user['height']
        age = user['age']
        gender = user['gender']

        if gender == 'male':
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161

        daily_calories = bmr * activity_level

        # บันทึกค่าที่คำนวณลงใน Calorie_Calculations table
        calorie_query = """
            INSERT INTO Calorie_Calculations (user_id, bmr, daily_calories)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE bmr = VALUES(bmr), daily_calories = VALUES(daily_calories)
        """
        cursor.execute(calorie_query, (user_id, bmr, daily_calories))
        mysql.connection.commit()

        flash('Weight updated and calorie calculations recalculated.', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {e}', 'error')
    finally:
        cursor.close()

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'info')
    return redirect(url_for('home'))

@app.route('/reset_password_request', methods=['GET','POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        cur = mysql.connection.cursor()
        try:
            cur.execute('SELECT * FROM Users WHERE email=%s',[email])
            user = cur.fetchone()
            if user:
                flash('We found your account. Please set a new password.', 'info')
                return redirect(url_for('reset_password'))
            else:
                flash('No account with that email.', 'danger')
        except Exception as e:
            flash(f'Error: {e}','danger')
        finally:
            cur.close()
    return render_template('reset_password_request.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        new_password = request.form.get('password')
        
        if not email or not new_password:
            flash('Email and Password are required.', 'danger')
            return redirect(url_for('reset_password'))
        
        hashed = generate_password_hash(new_password)
        cur = mysql.connection.cursor()
        try:
            cur.execute('UPDATE Users SET password=%s WHERE email=%s', (hashed, email))
            mysql.connection.commit()
            flash('Password updated. Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {e}', 'danger')
        finally:
            cur.close()
    return render_template('reset_password_direct.html')


@app.route('/details/<category>/<int:item_id>')
def details(category, item_id):
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM food_items WHERE food_id = %s", (item_id,))
        item = cur.fetchone()
        
        if not item:
            flash("Food item not found.", "danger")
            return redirect(url_for('menu_food'))

        return render_template('details.html', item=item)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for('menu_food'))
    finally:
        cur.close()

@app.route('/menu_food')
def menu_food():
    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT * FROM food_items")
        food_items = cur.fetchall()

        # Separate fruits and meals
        fruits = [item for item in food_items if item['category'] == 'fruit']
        meals = [item for item in food_items if item['category'] == 'meal']

        return render_template('menu_food.html', fruits=fruits, meals=meals)
    except Exception as e:
        flash(f"Error: {e}", "danger")
        return redirect(url_for('home'))
    finally:
        cur.close()



app.run(debug=True, host='0.0.0.0', port=5000)