from flask import Flask, request, render_template, jsonify, redirect, url_for, send_file
from PIL import Image, ImageDraw
import pytesseract
import json
import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Path to files and data
UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data.json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return []

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

@app.route('/download-json')
def download_json():
    try:
        json_file_path = 'data.json'
        return send_file(json_file_path, as_attachment=True, download_name='document_data.json')
    except Exception as e:
        print(f"Error sending file: {e}")
        return jsonify({'success': False, 'message': 'File not found or error occurred'}), 500


@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['GET','POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        selected_fields = request.form.getlist('checkbox')

        patient = 1 if 'patient' in selected_fields else 0
        admit_discharge = 1 if 'admit_discharge' in selected_fields else 0
        insurance = 1 if 'insurance' in selected_fields else 0
        provider = 1 if 'provider' in selected_fields else 0
        occurance = 1 if 'occurance' in selected_fields else 0
        value = 1 if 'value' in selected_fields else 0
        payer = 1 if 'payer' in selected_fields else 0

        new_data = process_image(file_path, patient, admit_discharge, insurance, provider, occurance, value, payer)
        
        existing_data = load_data()
        existing_data.append(new_data)
   
        save_data(existing_data)
        
        return render_template('upload.html', message="File uploaded successfully! Click 'View Documents' to see results.")
    return 'Invalid file type', 400

@app.route('/view')
def view_documents():
    data = load_data()
    return render_template('result.html', json_data=data)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png'}


#--Error Checking and Validation--
err_array = [0] * 124

#--some functions used for validation:
#Checks MM-DD-YYYY format
def validate_date(date_string):
    # Regular expression pattern for MM-DD-YYYY format
    pattern = r"^(0[1-9]|1[0-2])-(0[1-9]|1[0-9]|2[0-9]|3[0-1])-\d{4}$"
    pattern2 = r"^(0[1-9]|1[0-2])/(0[1-9]|1[0-9]|2[0-9]|3[0-1])/\d{4}$"

    # Check if the date string matches the pattern
    if re.match(pattern, date_string) or re.match(pattern2, date_string):
        return True
    else:
        return False

def process_image(image_path, patient, admit_discharge, insurance, provider, occurance, value, payer):
    image = Image.open(image_path)
    width = 2550
    height = 3300
    image = image.resize((width, height))
    
    draw = ImageDraw.Draw(image)
    
    json_data = {}
    
    
    labels = ['Patient control num','Medical Recipient num', 'bill-type', 'fed tax num', 'statement from',   #1
        'statement to', 'patient name', 'address a', 'address b', 'address c', #2
        'address d', 'address e','birthdate', 'sex', 'admission date', #3
        'admission hour', 'admission type', 'admission src', 'discharge hour', 'patient status', #4
        'cc', 'ACDT', 'occurance code 1', 'occurance date 1', #5
        'occurance code 2', 'occurance date 2', 'occurance code 3', 'occurance date 3', 'occurance code 4', #6
        'occurance date 1', 'span 1 code', 'span 1 from', 'span 1 through', 'span 2 code', #7
        'span 2 from', 'span 2 through', 'value code 1', 'value code 2', 'value code 3', #8
        'value code 4', 'value code 5', 'value code 6', 'value code 7', 'value code 8', #9
        'value code 9', 'value code 10', 'value code 11', 'value code 12', 'value amount 1', #10
        'value amount 2', 'value amount 3', 'value amount 4', 'value amount 5', 'value amount 6', #11
        'value amount 7', 'value amount 8', 'value amount 9', 'value amount 10', 'value amount 11', #12
        'value amount 12']
    xVals = [1637, 1637, 2357, 1547, 1848,#1
            2059, 378, 1278, 978, 1967,   
            2087, 2418, 46, 317, 407,      
            586, 677, 765, 857, 947,       
            1037, 2027, 47, 137,    #5       
            347, 437, 648, 738, 948,       
            1032, 1248, 1338, 1548, 1758,  
            1848, 2058, 1338, 1338, 1338,  
            1338, 1728, 1728, 1728, 1728, 
            2118, 2118, 2118, 2118, 1428, #10 
            1428, 1428, 1428, 1818, 1818, 
            1818, 1818, 2208, 2208, 2208,
            2208]
    Width = [2351, 2351, 2504, 1842, 2053,      #1
            2263, 942, 2505, 1931, 2051,
            2382, 2505, 311, 401, 581,
            625, 759, 851, 941, 1031, 
            2021, 2119, 131, 341,              #5
            431, 642, 732, 942, 1032,
            1242, 1332, 1542, 1752, 1842,
            2052, 2262, 1422, 1422, 1422,
            1422, 1812, 1812, 1812, 1812,
            2202, 2202, 2202, 2202, 1722,      #10
            1722, 1722, 1722, 2112, 2112,
            2112, 2112, 2505, 2505, 2505,
            2505]
    yVals = [59, 107, 107, 207, 207,        #1
            207, 256, 256, 306, 306,       
            306, 306, 406, 406, 406,
            406, 406, 406, 406, 406, 
            406, 406, 506, 506,            #5
            506, 506, 506, 506, 506,
            506, 506, 506, 506, 506,
            506, 506, 656, 705, 756,
            805, 656, 705, 755, 805,
            656, 705, 756, 805, 656,       #10
            705, 756, 805, 656, 705,
            755, 805, 656, 705, 755,
            805]
    Height = [101, 151, 151, 250, 250,      #1
            250, 300, 300, 350, 350,
            350, 350, 450, 450, 450,
            450, 450, 450, 450, 450, 
            450, 450, 552, 552,           #5
            552, 552, 552, 552, 552,
            552, 552, 552, 552, 552,
            552, 552, 702, 753, 802,
            850, 702, 753, 802, 850,
            702, 753, 802, 850, 702,      #10
            753, 802, 850, 702, 753,
            802, 850, 702, 753, 802,
            850]


    #Seperating form in half for simplicity
    labels2= ['payer name 1', 'payer name 2', 'payer name 3', 'health plan 1', 'health plan 2',     #1
            'health plan 3', 'Rel Info 1', 'Rel Info 2', 'Rel Info 3', 'asg ben 1',
            'asg ben 2', 'asg ben 3', 'prior pay 1', 'prior pay 2', 'prior pay 3',
            'amount due 1', 'amount due 2', 'amount due 3', 'npi', 'insured name 1',
            'insured name 2', 'insured name 3', 'p. rel 1', 'p. rel 2', 'p. rel 3',           #5
            'insured id 1', 'insured id 2', 'insured id 3', 'group name 1', 'group name 2',
            'group name 3', 'insured group num 1', 'insured group num 2', 'insured group num 3', 'treatment auth code 1',
            'treatment auth code 2',  'treatment auth code 3', 'doc control num 1',  'doc control num 2', 'doc control num 3',
            'employer name 1', 'employer name 2', 'employer name 3']

    xVals2 =[46, 46, 46, 737, 737,                  #1
            737, 1188, 1188, 1188, 1277,
            1277, 1277, 1338, 1338, 1338,
            1637, 1637, 1637, 2057, 46,
            46, 46, 826, 826, 826,                 #5
            916, 916, 916, 1517, 1517,
            1517, 1967, 1967, 1967, 46,
            46, 46, 975, 975, 975,
            1756, 1756, 1756]

    Width2 = [731, 731, 731, 1182, 1182,            #1
            1182, 1242, 1242, 1242, 1322,
            1322, 1322, 1632, 1632, 1632,
            1961, 1961, 1961, 2505, 820,
            820, 820, 910, 910, 910,              #5
            1511, 1511, 1511, 1961, 1961,
            1961, 2505, 2505, 2505, 970,
            970, 970, 1751, 1751, 1751,
            2505, 2505, 2505]

    Yvals2 = [2106, 2154, 2205, 2106, 2154,         #1
            2205, 2106, 2154, 2205, 2106,
            2154, 2205, 2106, 2154, 2205,
            2106, 2154, 2205, 2056, 2306,
            2354, 2405, 2306, 2354, 2405,        #5
            2306, 2354, 2405, 2306, 2354,
            2405, 2306, 2354, 2405, 2506,
            2554, 2605, 2506, 2554, 2605,
            2506, 2554, 2605]

    Height2 = [2151, 2202, 2250, 2151, 2202,        #1
            2250, 2151, 2202, 2250, 2151,
            2202, 2250, 2151, 2202, 2250,
            2151, 2202, 2250, 2100, 2351,
            2402, 2450, 2351, 2402, 2450,        #5
            2351, 2402, 2450, 2351, 2402,
            2450, 2351, 2402, 2450, 2551,
            2602, 2650, 2551, 2602, 2650,
            2551, 2602, 2650]
    labels = labels + labels2
    xVals += xVals2
    yVals += Yvals2
    Width += Width2
    Height += Height2
    comments=''
    # categorize the sections so the user can choose what they want to get in the csv
    draw = ImageDraw.Draw(image)
    final_text = ''
    roi = image.crop((63, 58, 790, 101))
    extracted_text = pytesseract.image_to_string(roi).strip()
    roi = image.crop((46, 107, 790, 151))
    extracted_text = extracted_text + ' ' + pytesseract.image_to_string(roi).strip()
    roi = image.crop((46, 157, 790, 201))
    extracted_text = extracted_text + ' ' + pytesseract.image_to_string(roi).strip()
    roi = image.crop((46, 207, 790, 250))
    extracted_text = extracted_text + ' ' + pytesseract.image_to_string(roi).strip()
    json_data['Hospital'] = extracted_text
    for val in range(len(labels)):
        #draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
        #patient info
        if patient == 1 and (labels[val] == 'Patient control num' or labels[val] == 'patient name' or labels[val] == 'birthdate' or labels[val] == 'sex' or labels[val] == 'patient status'):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()

            #validation
            #verify patient ctrl num is alphanumeric
            if labels[val] == 'Patient control num':
                if extracted_text.isalnum() or extracted_text == '':
                    err_array[val] = 0
                else:
                    err_array[val] = 1
                    print("Error: Invalid patient control number value:", extracted_text)
                    comments = comments + "Error: Invalid patient control number value: " + extracted_text + '\n'

            #verify patient name is alphabetical
            elif 'patient name' in labels[val]:
                cleaned_text = extracted_text.replace(" ", "")
                if cleaned_text.isalpha() or extracted_text == '':
                    err_array[val] = 0
                else:
                    print("Error: Invalid patient name value:", extracted_text)
                    comments = comments + "Error: Invalid patient name value:" + extracted_text + '\n'
                    err_array[val] = 1
            
            #verify date format and validity MM-DD-YYYY
            elif 'birthdate' in labels[val]:
                if validate_date(extracted_text) or extracted_text == '':
                    err_array[val] = 0
                else:
                    comments = comments + "Error: Invalid birthdate value: " + extracted_text + '\n'
                    err_array[val] = 1

            #M or F
            elif 'sex' in labels[val]:
                extracted_text = extracted_text.upper()  # Convert to uppercase for case-insensitive comparison
                if extracted_text not in ('M', 'F', 'MALE', 'FEMALE', 'Male', 'Female') and extracted_text != '':
                    # Handle invalid sex value
                    comments = comments + "Error: Invalid sex value:" + extracted_text +'\n'
                    err_array[val] = 1
                else:
                    # Valid sex value, set labels[val] to 0
                    err_array[val] = 0

            #01-19, 30, numeric
            elif 'patientStatus' in labels[val]:
                extracted_text = extracted_text.strip()  # Remove leading/trailing whitespace
                try:
                    age = int(extracted_text)
                    if 0 <= age <= 19 or age == 30 or extracted_text == '':
                        err_array[val] = 0
                    else:
                        comments = comments + "Error for " + labels[val] +": Invalid patient status value: " + extracted_text +'\n'
                        err_array[val] = 1
                except ValueError:
                    print("Error for " + labels[val] + ": Invalid patient status format:", extracted_text)
                    err_array[val] = 1
                    
            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
        elif patient == 0 and (labels[val] == 'Patient control num' or labels[val] == 'patient name' or labels[val] == 'birthdate' or labels[val] == 'sex' or labels[val] == 'patient status'):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

        #admission and discharge info
        if admit_discharge == 1 and ('admission' in labels[val] or labels[val] == 'discharge hour'):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()

            #validation
            #consider checking if outpatient(causes many cases to be optional)
            #'admission date', 'admission hour', 'admission type', 'admission src'
            #admission date
            if 'admission date' in labels[val]:
                if validate_date(extracted_text) or extracted_text == '':
                    err_array[val] = 0
                else:
                    print("Error: Invalid admission date value:", extracted_text)
                    comments = comments + "Error for " + labels[val] + ":Invalid admission date value: " + extracted_text +'\n'
                    err_array[val] = 1
            
            #admission hour
            elif 'admission hour' in labels[val]:
                #extracted_text = extracted_text.strip()  # Remove leading/trailing whitespace
                try:
                    hour = int(extracted_text)
                    if (0 <= hour <= 23) or extracted_text == '':
                        err_array[val] = 0
                    else:
                        print("Error for " + labels[val] + ": Invalid admission hour value:", extracted_text)
                        comments = comments + "Error:Invalid admission hour value: " + extracted_text +'\n'
                        err_array[val] = 1
                except ValueError:
                    print("Error for " + labels[val] + ": Invalid admission hour format:", extracted_text)
                    #comments = comments + "Error:Invalid admission hour value: " + extracted_text +'\n'
                    err_array[val] = 1

            #admission type
            elif 'admission type' in labels[val]:
                #extracted_text = extracted_text.strip()  # Remove leading/trailing whitespace
                try:
                    type = int(extracted_text)
                    if 0 <= type <= 3 or type == 5 or type == 9 or extracted_text == '':
                        err_array[val] = 0
                    else:
                        print("Error: Invalid admission type value:", extracted_text)
                        comments = comments + "Error for " + labels[val] + ": Invalid admission type value: " + extracted_text +'\n'
                        err_array[val] = 1
                except ValueError:
                    print("Error for " + labels[val] + ": Invalid admission type format:", extracted_text)
                    comments = comments + "Error for " + labels[val] + ": Invalid admission type value: " + extracted_text +'\n'
                    err_array[val] = 1

            #admission src
            elif 'admission src' in labels[val]:
                #extracted_text = extracted_text.strip()  # Remove leading/trailing whitespace
                try:
                    src = int(extracted_text)
                    if (0 <= src <= 9) or extracted_text == '':
                        err_array[val] = 0
                    else:
                        print("Error: Invalid admission src value:", extracted_text)
                        comments = comments + "Error for " + labels[val] + ": Invalid admission src value: " + extracted_text +'\n'
                        err_array[val] = 1
                except ValueError:
                    print("Error: Invalid admission src format:", extracted_text)
                    #comments = comments + "Error for " + labels[val] + ": Invalid admission src format: " + extracted_text +'\n'
                    err_array[val] = 1

            #discharge hour
            elif 'discharge hour' in labels[val]:
                #extracted_text = extracted_text.strip()  # Remove leading/trailing whitespace
                try:
                    hour = int(extracted_text)
                    if (0 <= hour <= 23) or extracted_text == '':
                        err_array[val] = 0
                    else:
                        print("Error: Invalid discharge hour value:", extracted_text)
                        comments = comments + "Error for " + labels[val] + ": Invalid discharge hour value: " + extracted_text +'\n'
                        err_array[val] = 1
                except ValueError:
                    print("Error: Invalid discharge hour format:", extracted_text)
                    #comments = comments + "Error for " + labels[val] + ": Invalid discharge hour format: " + extracted_text +'\n'
                    err_array[val] = 1

            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
        elif admit_discharge == 0 and ('admission' in labels[val] or labels[val] == 'discharge hour'):
            final_text = final_text + ', '
            json_data[labels[val]] = ''
        
        #insurance and financial info
        if insurance == 1 and (labels[val] == 'bill-type' or labels[val] == 'Medical Recipient num' or labels[val] == 'fed tax num' or labels[val] == 'cc' or labels[val] == 'ACDT' or 'insured' in labels[val] or 'employer' in labels[val] or 'treatment auth' in labels[val] or 'p. rel' in labels[val] or 'group name' in labels[val] or 'doc control' in labels[val] or 'npi' in labels[val]):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()
            final_text = final_text + ', ' + extracted_text 
            json_data[labels[val]] = extracted_text
            if 'bill-type' in labels[val] or 'Medical Recipient num' in labels[val] or 'fed tax num' in labels[val] or 'ACDT' in labels[val] or 'p. rel' in labels[val] or 'doc control' in labels[val]:
                if extracted_text.isalnum() or extracted_text == '':
                    err_array[val] = 0
                else: 
                    err_array[val] = 1
                    print("Error: value must be a number:", extracted_text)
                    comments = comments + "Error for " + labels[val] + ": value must be a number: " + extracted_text +'\n'
        elif insurance == 0 and (labels[val] == 'bill-type' or labels[val] == 'Medical Recipient num' or labels[val] == 'fed tax num' or labels[val] == 'cc' or labels[val] == 'ACDT' or 'insured' in labels[val] or 'employer' in labels[val] or 'treatment auth' in labels[val] or 'p. rel' in labels[val] or 'group name' in labels[val] or 'doc control' in labels[val] or 'npi' in labels[val]):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

        #provider info
        if provider == 1 and (labels[val] == 'statement to' or 'address' in labels[val] or labels[val] == 'statement from'):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()
            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
            if 'statement to' in labels[val] or 'statement from' in labels[val]:
                if validate_date(extracted_text) or extracted_text == '':
                    err_array[val] = 0
                else:
                    print("Error for " + labels[val] + ": Invalid date value:", extracted_text)
                    comments = comments + "Error: Invalid date value: " + extracted_text +'\n'
                    err_array[val] = 1
        elif provider == 0 and (labels[val] == 'statement to' or 'address' in labels[val] or labels[val] == 'statement from'):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

        #occurance info
        if occurance == 1 and ('occurance' in labels[val] or 'occurance' in labels[val] or 'span' in labels[val]):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()
            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
            if 'occurance code' in labels[val] or 'span code' in labels[val]:
                if extracted_text.isalnum() or extracted_text == '':
                    err_array[val] = 0
                else: 
                    err_array[val] = 1
                    print("Error: value must be a number:", extracted_text)
                    comments = comments + "Error for " + labels[val] + ": value must be a number: " + extracted_text +'\n'
            elif 'span from' in labels[val] or 'span through' in labels[val]:
                if validate_date(extracted_text):
                    err_array[val] = 0
                else:
                    print("Error for " + labels[val] + ": Invalid date value:", extracted_text)
                    comments = comments + "Error: Invalid date value: " + extracted_text +'\n'
                    err_array[val] = 1

        elif occurance == 0 and ('occurance' in labels[val] or 'occurance' in labels[val] or 'span' in labels[val]):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

        #value codes
        if value == 1 and ('value code' in labels[val] or 'value amount' in labels[val]):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()
            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
            cleaned_text = extracted_text.replace('$', '')
            cleaned_text = cleaned_text.replace('.', '')
            cleaned_text = cleaned_text.replace(',', '')
            if cleaned_text.isalnum() or extracted_text == '':
                err_array[val] = 0
            else: 
                err_array[val] = 1
                print("Error: value must be a number:", extracted_text)
                comments = comments + "Error for " + labels[val] + ": value must be a number: " + extracted_text +'\n'


        elif value == 0 and ('value code' in labels[val] or 'value amount' in labels[val]):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

        #payer info
        if payer == 1 and ('payer' in labels[val] or 'pay' in labels[val] or 'Rel Info' in labels[val] or 'health plan' in labels[val] or 'asg ben' in labels[val] or 'amount due' in labels[val]):
            draw.rectangle([xVals[val], yVals[val], Width[val], Height[val]], outline="red", width=2)
            roi = image.crop((xVals[val], yVals[val], Width[val], Height[val]))
            extracted_text = pytesseract.image_to_string(roi).strip()
            final_text = final_text + ', ' + extracted_text
            json_data[labels[val]] = extracted_text
            if 'prior pay' in labels[val] or 'amount due' in labels[val]:
                cleaned_text = extracted_text.replace('$', '')
                cleaned_text = cleaned_text.replace('.', '')
                cleaned_text = cleaned_text.replace(',', '')
                if cleaned_text.isalnum() or extracted_text == '':
                    err_array[val] = 0
                else: 
                    err_array[val] = 1
                    print("Error: value must be a number:", extracted_text)
                    comments = comments + "Error for " + labels[val] + ": value must be a number: " + extracted_text +'\n'

        elif payer == 0 and ('payer' in labels[val] or 'pay' in labels[val] or 'Rel Info' in labels[val] or 'health plan' in labels[val] or 'asg ben' in labels[val] or 'amount due' in labels[val]):
            final_text = final_text + ', '
            json_data[labels[val]] = ''

    n = 0
    claimCodes=[906, 955, 1006, 1055, 1106, 1155, 1206, 1255, 1306, 1355, 1406, 1455, 1506, 1555, 1606, 1655, 1706, 1755, 1806, 1855, 1906, 1955]
    for i in range(22):
        code = pytesseract.image_to_string(image.crop((47, claimCodes[i], 181, claimCodes[i] + 46))).strip()
        if (code):
            #hipps_num = f" HIPPS code {n}"
            end = False
            n = n + 1
            json_data[f" rev code {n}"] = code
            json_data[f" HIPPS code {n}"] = pytesseract.image_to_string(image.crop((936, claimCodes[i], 1380, claimCodes[i] + 46))).strip()
            json_data[f" Serv. Date {n}"] = pytesseract.image_to_string(image.crop((1386, claimCodes[i], 1590, claimCodes[i] + 46))).strip()
            json_data[f" Serv. Units {n}"] = pytesseract.image_to_string(image.crop((1596, claimCodes[i], 1830, claimCodes[i] + 46))).strip()
            json_data[f" Total Charges {n}"] = pytesseract.image_to_string(image.crop((1836, claimCodes[i], 2131, claimCodes[i] + 46))).strip()
            json_data[f" Uncovered Charges {n}"] = pytesseract.image_to_string(image.crop((2137, claimCodes[i], 2427, claimCodes[i] + 46))).strip()
            description_num = f"description {n}"
            k=0
            j = i
            while not end and j<21:
                k = k + 1
                j = j + 1
                if (pytesseract.image_to_string(image.crop((47, claimCodes[j], 181, claimCodes[j] + 46))).strip()):
                    end = True
            Description = pytesseract.image_to_string(image.crop((187, claimCodes[i], 930, claimCodes[i] + 46))).strip()
            for num in range(1, k):
                i = i + 1
                Description = Description + ' ' + pytesseract.image_to_string(image.crop((187, claimCodes[i], 930, claimCodes[i] + 46))).strip()
            i = j - 1
            json_data[description_num] = Description

    if n < 22:
        for m in range(n + 1, 22):
            json_data[f" rev code {m}"] = ''
            json_data[f" HIPPS code {m}"] = ''
            json_data[f" Serv. Date {m}"] = ''
            json_data[f" Serv. Units {m}"] = ''
            json_data[f" Total Charges {m}"] = ''
            json_data[f" Uncovered Charges {m}"] = ''
    json_data['errors'] = comments
    return json_data

'''for element in err_array:
    print(element)'''

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

#smtp uses the email and sends an email to itself using the feedback info
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'MetaScanSpprt@gmail.com'
SMTP_APPPASSWORD = 'iynl ferj vies kfjx'
SUPPORT_EMAIL = 'MetaScanSpprt@gmail.com'

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    feedback_type = data.get('type')
    feedback_text = data.get('text')

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = SUPPORT_EMAIL
    msg['Subject'] = 'New Feedback Submitted!'

    body = f"Feedback Type: {feedback_type} \n\nFeedback: {feedback_text}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        #smtp sends email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_APPPASSWORD)
            server.send_message(msg)
        return jsonify({"message": "Feedback submitted successfully!"}), 200
    except smtplib.SMTPException as e:
        app.logger.error(f"SMTP error{str(e)}")
        return jsonify({"error": 'Failed to send feedback due to SMTP error'}), 500
    except Exception as e:
        app.logger.error(f"Failed to send email{str(e)}")
        return jsonify({'error': 'Failed to send feedback'}), 500

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/update-json', methods=['POST'])
def update_json():
    try:
        updated_data = request.json
        if not updated_data:
            return jsonify({'success': False, 'message': 'No data received'}), 400

        # Save the updated data to a JSON file
        with open('data.json', 'w') as json_file:
            json.dump(updated_data, json_file, indent=4)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving JSON: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
