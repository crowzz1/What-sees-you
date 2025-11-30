import cv2
import numpy as np
import time
import os

# Suppress TF warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

print("Initializing...")

# 1. Import InsightFace
try:
    import insightface
    from insightface.app import FaceAnalysis
    print("InsightFace imported.")
except ImportError:
    print("Error: InsightFace not installed.")
    exit(1)

# 2. Import DeepFace
try:
    from deepface import DeepFace
    print("DeepFace imported.")
except ImportError:
    print("Error: DeepFace not installed.")
    exit(1)

# Initialize InsightFace
print("Loading InsightFace model...")
app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))  # Same as main program
print("InsightFace loaded.")

# Open Camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit(1)

print("\nStarting loop. Press 'q' to quit.")
print("Wait for emotion analysis (may take time for first run)...")

frame_count = 0
last_emotion = "Analyzing..."
last_conf = 0.0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Mirror flip (same as main program)
    frame = cv2.flip(frame, 1)
        
    frame_count += 1
    
    # Detect faces
    faces = app.get(frame)
    
    # DEBUG: Print detection status
    if frame_count % 30 == 0:
        print(f"Frame {frame_count}: Detected {len(faces)} faces, Frame shape: {frame.shape}")
    
    for face in faces:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Draw face box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Analyze emotion every 5 frames
        if frame_count % 5 == 0:
            try:
                # Crop face with padding
                h, w = frame.shape[:2]
                pad_x = int((x2 - x1) * 0.2)
                pad_y = int((y2 - y1) * 0.2)
                x1_pad = max(0, x1 - pad_x)
                y1_pad = max(0, y1 - pad_y)
                x2_pad = min(w, x2 + pad_x)
                y2_pad = min(h, y2 + pad_y)
                
                face_img = frame[y1_pad:y2_pad, x1_pad:x2_pad]
                
                if face_img.size > 0:
                    # DeepFace Analysis
                    # print("Analyzing emotion...")
                    result = DeepFace.analyze(
                        img_path=face_img,
                        actions=['emotion'],
                        enforce_detection=False,
                        detector_backend='skip',
                        silent=True
                    )
                    
                    if isinstance(result, list):
                        result = result[0]
                        
                    last_emotion = result['dominant_emotion']
                    last_conf = result['emotion'][last_emotion]
                    print(f"Detected: {last_emotion} ({last_conf:.1f}%)")
                    
            except Exception as e:
                print(f"DeepFace Error: {e}")
                last_emotion = "Error"
        
        # Display emotion
        text = f"{last_emotion} ({last_conf:.1f}%)"
        cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow('Emotion Test', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

