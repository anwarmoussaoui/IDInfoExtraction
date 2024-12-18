import pytesseract
from PIL import Image
from flask import Flask, request, jsonify
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'im' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['im']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif"}), 400

    # Save the uploaded file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # Perform OCR for Arabic and French separately
    img = Image.open(file_path)
    arabic_text = pytesseract.image_to_string(img, lang='ara')
    french_text = pytesseract.image_to_string(img, lang='fra')

    # Combine both extracted texts for debugging
    print("Arabic Text:", arabic_text)
    print("French Text:", french_text)

    # Process French Text (First/Last Name, DOB, ID Code)
    first_name, last_name, date_of_birth, place_of_birth, id_code = "", "", "", "", ""

    for line in french_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Extract ID code
        if not id_code:
            match = re.search(r"[A-Z0-9]{2,}\d{6,}", line)
            if match:
                id_code = match.group(0)

        # Extract First and Last Name (fix the inversion)
        if line.isupper() and not any(keyword in line for keyword in ["CARTE", "NATIONALE"]):
            if not last_name:
                last_name = line  # Last name first (ELALAMI)
            elif not first_name:
                first_name = line  # First name second (ZAINEB)

        # Extract date of birth
        if not date_of_birth:
            date_match = re.search(r"(\d{2}[-./]\d{2}[-./]\d{4})", line)
            if date_match:
                date_of_birth = date_match.group(1)

        # Extract place of birth with "s LOCATION"
        if not place_of_birth:
            place_match = re.search(r"s\s+([\w\s-]+)", line, re.IGNORECASE)
            if place_match:
                place_of_birth = place_match.group(1).strip()

    # If place of birth is still not found, try searching for "à LOCATION"
    if not place_of_birth:
        for line in french_text.split('\n'):
            line = line.strip()
            place_match = re.search(r"à\s+([\w\s-]+)", line)
            if place_match:
                place_of_birth = place_match.group(1).strip()
                break

    # Process Arabic Text (First/Last Name, DOB, ID Code, Place of Birth)
    arabic_first_name, arabic_last_name, arabic_place_of_birth = "", "", ""
    arabic_date_of_birth = date_of_birth  # Using the same date of birth from French text if not found in Arabic

    # Here we attempt to align the Arabic text with French (Parallel matching)
    arabic_lines = arabic_text.split('\n')
    french_lines = french_text.split('\n')

    for i in range(min(len(arabic_lines), len(french_lines))):
        arabic_line = arabic_lines[i].strip()
        french_line = french_lines[i].strip()

        # Check for first name (Arabic and French)
        if not arabic_first_name and arabic_line == french_line:  # When names match across both texts
            arabic_first_name = arabic_line

        # Check for last name (Arabic and French)
        if not arabic_last_name and arabic_line == french_line:  # When last names match across both texts
            arabic_last_name = arabic_line

        # If we find a match for place of birth
        if not arabic_place_of_birth and "المغرب" in arabic_line:  # Morocco typically appears here
            arabic_place_of_birth = arabic_line

    # Remove the file after processing
    os.remove(file_path)

    # Validation
    if not (first_name and last_name and date_of_birth and id_code):
        return jsonify({"error": "Failed to extract complete ID card details"}), 400

    # Return extracted data with correct Arabic fields (no default values)
    return jsonify({
        "prénom": first_name,
        "nom_de_famille": last_name,
        "date_de_naissance": date_of_birth,
        "code_identifiant": id_code,
        "lieu_de_naissance": place_of_birth,
        "تاريخ_الميلاد": arabic_date_of_birth,
        "الاسم_الأول": arabic_first_name,
        "اسم_العائلة": arabic_last_name,
        "رمز_الهوية": id_code,
        "مكان_الميلاد": arabic_place_of_birth
    })

if __name__ == '__main__':
    app.run(debug=True)
