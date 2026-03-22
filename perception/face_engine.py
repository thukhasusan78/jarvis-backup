import os
import logging
import face_recognition

logger = logging.getLogger("JARVIS_FACE_ENGINE")

class FaceEngine:
    def __init__(self):
        self.known_faces = []
        self.known_names = []
        self.load_known_faces()

    def load_known_faces(self):
        """မှတ်ဉာဏ်ထဲက ဆရာ့ရဲ့ မျက်နှာပုံကို ကြိုတင် ကျက်မှတ်ထားမည်"""
        faces_dir = os.path.join("memory", "known_faces")
        os.makedirs(faces_dir, exist_ok=True)

        for file_name in os.listdir(faces_dir):
            if file_name.endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(faces_dir, file_name)
                try:
                    image = face_recognition.load_image_file(path)
                    # မျက်နှာရဲ့ Vector Data ကို ဆွဲထုတ်မည်
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        self.known_faces.append(encodings[0])
                        # 'sir.jpg' ဆိုလျှင် 'sir' ဟု မှတ်မည်
                        self.known_names.append(os.path.splitext(file_name)[0].upper())
                        logger.info(f"👁️ Learned face: {file_name}")
                except Exception as e:
                    logger.error(f"Error loading face {file_name}: {e}")

    def analyze_image(self, image_path: str) -> str:
        """
        ပုံထဲမှာ လူပါမပါ စစ်မည်။
        (မှတ်ချက်: ဤ Function သည် CPU အများကြီးသုံးသဖြင့် Background Thread တွင်သာ Run ရမည်)
        """
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if not face_encodings:
                return "ပုံထဲတွင် လူမျက်နှာ မတွေ့ရပါ။"

            detected_names = []
            for encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_faces, encoding, tolerance=0.5)
                name = "Unknown Person"

                if True in matches:
                    first_match_index = matches.index(True)
                    name = self.known_names[first_match_index]

                detected_names.append(name)

            if "SIR" in detected_names:
                return "ပုံထဲတွင် ဆရာ့ (Sir) ကို တွေ့ရှိရပါသည်။"
            else:
                return f"ပုံထဲတွင် {', '.join(detected_names)} ကို တွေ့ရှိရပါသည်။"

        except Exception as e:
            logger.error(f"Face Analysis Error: {e}")
            return "ပုံကို စစ်ဆေးရာတွင် အခက်အခဲ ဖြစ်သွားပါသည်။"

# Singleton
face_engine = FaceEngine()