import pytesseract
from PIL import Image
from flask import Flask, request, jsonify
import re
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'  # Directory to temporarily store uploaded images
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Define the IDCard class
class IDCard:
    def __init__(self, first_name, last_name, date_of_birth, place_of_birth, id_code):
        self.first_name = first_name
        self.last_name = last_name
        self.date_of_birth = date_of_birth
        self.place_of_birth = place_of_birth
        self.id_code = id_code

    def to_dict(self):
        """Convert the IDCard object to a dictionary."""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth,
            "place_of_birth": self.place_of_birth,
            "id_code": self.id_code,
        }

# Specify the path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        # Save the uploaded file to the server
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Perform OCR on the uploaded image
        img = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(img)
        print(extracted_text)
        lines = extracted_text.split('\n')
        lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines

        # Check if it contains ID card specific text
        id_card_identifier = "ROYAUME DU MAROC\nCARTE NATIONALE D'IDENTITE"
        if id_card_identifier not in extracted_text:
            os.remove(file_path)
            return jsonify({"error": "This is not an ID card"}), 400

        # Initialize variables
        first_name = ""
        last_name = ""
        date_of_birth = ""
        place_of_birth = ""
        id_code = ""

        # Parse the information dynamically
        for line in lines:
            # Detect the first name and last name (assume uppercase names in separate lines)
            if line.isupper() and not any(keyword in line for keyword in ["ROYAUME", "CARTE", "IDENTITE"]):
                if not first_name:
                    first_name = line
                elif not last_name:
                    last_name = line

            # Extract date of birth
            if "Né le" in line:
                match = re.search(r"Né le (\d{2}\.\d{2}\.\d{4})", line)
                if match:
                    date_of_birth = match.group(1)

            # Extract place of birth
            if "a " in line:
                place_of_birth = line.split("a ", 1)[-1].strip()

            # Extract ID code (e.g., EE926239)
            if re.match(r"[A-Z]{2}\d{6,}$", line):
                id_code = line

        # Create an instance of the class
        id_card = IDCard(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            place_of_birth=place_of_birth,
            id_code=id_code
        )

        # Remove the uploaded file after processing
        os.remove(file_path)

        # Return the IDCard object as JSON
        return jsonify(id_card.to_dict())

if __name__ == '__main__':
    app.run(debug=True)
