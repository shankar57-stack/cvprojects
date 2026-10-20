import cv2
import socket
from ultralytics import YOLO
import requests
import threading
import time

# 1. SETUP UDP SOCKET FIRST (Before the thread starts)
udp_ip = "127.0.0.1"
udp_port = 4242
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ESP32 Heart Rate Setup
ESP32_URL = "http://192.168.4.1/data"  # Default IP for ESP32 Access Point mode with the /data endpoint
current_heart_rate = "HR: --"

# 2. DEFINE THE FETCH FUNCTION
def fetch_heart_rate():
    global current_heart_rate
    while True:
        try:
            response = requests.get(ESP32_URL, timeout=2)
            if response.status_code == 200:
                # Parse the JSON coming from the ESP32 {"bpm": 85, "emg": 1200}
                data = response.json()
                bpm = data.get("bpm", 0)
                emg = data.get("emg", 0)
                
                # Update OpenCV display text
                current_heart_rate = f"HR: {bpm} BPM | EMG: {emg}"
                
                # Forward the data to Godot via UDP
                sensor_command = f"sensor_{bpm}_{emg}"
                sock.sendto(sensor_command.encode(), (udp_ip, udp_port))
                
                # Print to terminal so you know it is sending successfully
                print(f"Sent: {sensor_command}") 
                
        except Exception as e:
            # Print the error instead of silently hiding it
            print(f"ESP32 Connection Error: {e}") 
            
        time.sleep(0.5) # Match the 500ms interval from your ESP32 web server

# 3. START THE THREAD (Now that the socket exists)
hr_thread = threading.Thread(target=fetch_heart_rate, daemon=True)
hr_thread.start()

# Load the YOLOv8 pose model (this will automatically download the lightweight 'nano' model)
print("Loading YOLOv8 Pose model...")
model = YOLO('yolov8n-pose.pt')

cap = cv2.VideoCapture(1)  # Use the default camera (change the index if you have multiple cameras)

# Track current states
state = {
    "right": False,
    "left": False,
    "jump": False
}

def send_command(action, is_active):
    command = f"{action}_start" if is_active else f"{action}_stop"
    sock.sendto(command.encode(), (udp_ip, udp_port))
    print(f"Sent: {command}")

# Confidence threshold for body parts
threshold = 0.5

while True:
    ret, frame = cap.read()
    if not ret: break
        
    # Mirror effect
    frame = cv2.flip(frame, 1)
    frameHeight = frame.shape[0]
    
    # Run YOLOv8 pose estimation on the frame
    # verbose=False stops it from printing detection info to terminal every frame
    results = model(frame, verbose=False)
    
    # Get the image with the skeleton already drawn on it!
    annotated_frame = results[0].plot()
    
    # Display the heart rate in the top right corner
    text_size = cv2.getTextSize(current_heart_rate, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
    text_x = annotated_frame.shape[1] - text_size[0] - 20 # 20 pixels padding from the right
    cv2.putText(annotated_frame, current_heart_rate, (text_x, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

    # Extract keypoints
    # YOLOv8 returns keypoints for all detected people. We just look at the first one [0]
    if len(results[0].keypoints) > 0 and len(results[0].keypoints.xy[0]) > 0:
        
        # Move tensors to numpy arrays
        points = results[0].keypoints.xy[0].cpu().numpy()
        confs = results[0].keypoints.conf[0].cpu().numpy()
        
        # YOLOv8 COCO Keypoints mapping:
        # 5: LShoulder, 9: LWrist
        # 6: RShoulder, 10: RWrist
        # 11: LHip, 13: LKnee
        
        l_shoulder = points[5]
        l_wrist = points[9]
        r_shoulder = points[6]
        r_wrist = points[10]
        l_hip = points[11]
        l_knee = points[13]
        
        conf_l_shoulder = confs[5]
        conf_l_wrist = confs[9]
        conf_r_shoulder = confs[6]
        conf_r_wrist = confs[10]
        conf_l_hip = confs[11]
        conf_l_knee = confs[13]
        
        # 1. Left Hand Raised
        left_raised = False
        if conf_l_wrist > threshold and conf_l_shoulder > threshold:
            left_raised = l_wrist[1] < l_shoulder[1]
            
        # 2. Right Hand Raised
        right_raised = False
        if conf_r_wrist > threshold and conf_r_shoulder > threshold:
            right_raised = r_wrist[1] < r_shoulder[1]
            
        # 3. Sit to Jump
        is_sitting = False
        if conf_l_hip > threshold and conf_l_knee > threshold:
            hip_y_norm = l_hip[1] / frameHeight
            knee_y_norm = l_knee[1] / frameHeight
            is_sitting = (knee_y_norm - hip_y_norm) < 0.15
            
        # Send commands if state changed
        if left_raised != state["left"]:
            state["left"] = left_raised
            send_command("left", left_raised)
            
        if right_raised != state["right"]:
            state["right"] = right_raised
            send_command("right", right_raised)
            
        if is_sitting != state["jump"]:
            state["jump"] = is_sitting
            send_command("jump", is_sitting)

    cv2.imshow('Motion Controller (YOLOv8 Pose)', annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()