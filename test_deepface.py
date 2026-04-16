import cv2
from deepface import DeepFace

print("Initializing live camera test... (Press 'q' on the video window to quit)")

# Open the default camera (index 0)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera. Please make sure no other app is using it.")
    exit()

print("Camera opened successfully. Analyzing frames...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break
        
    try:
        # Analyze frame with enforce_detection=False to prevent crashes if no face is visible
        results = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False, silent=True)
        
        if results:
            result = results[0]
            dominant_emotion = result.get('dominant_emotion', 'unknown')
            confidence = result.get('face_confidence', 0.0)
            
            # Draw on the frame if it confidently sees a face
            if confidence > 0.5:
                # Put the text
                cv2.putText(
                    frame, 
                    f"Emotion: {dominant_emotion}", 
                    (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    (0, 255, 0), 
                    2
                )
                
                # Draw a bounding box around the face
                region = result.get('region')
                if region:
                    x, y, w, h = region['x'], region['y'], region['w'], region['h']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            else:
                cv2.putText(
                    frame, 
                    "No confident face detected", 
                    (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    (0, 0, 255), 
                    2
                )
                
    except Exception as e:
        cv2.putText(frame, "Error in analysis", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
    # Show the video feed
    cv2.imshow("DeepFace Live Test - Press 'q' to quit", frame)
    
    # Wait for the 'q' key to stop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up
cap.release()
cv2.destroyAllWindows()
print("Live test ended.")
