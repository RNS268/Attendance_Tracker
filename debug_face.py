import face_recognition

image = face_recognition.load_image_file(
    "registration_images/24054-EC-004/img3.jpeg"
)

encodings = face_recognition.face_encodings(image)

print("Encodings found:", len(encodings))
