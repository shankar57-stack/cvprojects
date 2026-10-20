const videoElement = document.getElementById('videoElement');
const canvasElement = document.getElementById('outputCanvas');
const canvasCtx = canvasElement.getContext('2d');
const currentAngleSpan = document.getElementById('currentAngle');
const evalStatusSpan = document.getElementById('evalStatus');
const repCountSpan = document.getElementById('repCount');
const bigRepCount = document.getElementById('bigRepCount');
const feedbackOverlay = document.getElementById('feedbackOverlay');
const exerciseName = document.getElementById('exerciseName').innerText.trim();

let validatedReps = 0;
const TARGET_REPS = 10;
let exerciseState = 'up'; // Can be 'up' or 'down' based on the exercise phase
let sessionStartTime = new Date();
let measuredValues = [];
let feedbackEvents = [];
let isSessionComplete = false;

// Initialize rep count text
updateRepCount();

function calculateAngle(a, b, c) {
    const radians = Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);
    if (angle > 180.0) {
        angle = 360 - angle;
    }
    return angle;
}

function processExerciseLogic(landmarks) {
    if (isSessionComplete) return;

    let angle = 0;
    
    if (exerciseName === 'Squats' || exerciseName === 'Lunges') {
        const hip = landmarks[23];
        const knee = landmarks[25];
        const ankle = landmarks[27];
        
        if (hip && knee && ankle) {
            angle = calculateAngle(hip, knee, ankle);
            
            if (angle > 160) {
                if (exerciseState === 'down') {
                    validatedReps++;
                    showFeedback("Good rep!");
                    updateRepCount();
                    measuredValues.push(Math.round(angle));
                }
                exerciseState = 'up';
                evalStatusSpan.innerText = "Go Down";
                evalStatusSpan.style.color = "orange";
            } else if (angle < 100) {
                exerciseState = 'down';
                evalStatusSpan.innerText = "Go Up";
                evalStatusSpan.style.color = "green";
            } else {
                evalStatusSpan.innerText = "Keep going";
                evalStatusSpan.style.color = "black";
            }
        }
    } else if (exerciseName === 'Push-ups' || exerciseName === 'Shoulder Press') {
        const shoulder = landmarks[11];
        const elbow = landmarks[13];
        const wrist = landmarks[15];
        
        if (shoulder && elbow && wrist) {
            angle = calculateAngle(shoulder, elbow, wrist);
            
            if (angle > 150) {
                if (exerciseState === 'down') {
                    validatedReps++;
                    showFeedback("Good rep!");
                    updateRepCount();
                    measuredValues.push(Math.round(angle));
                }
                exerciseState = 'up';
                evalStatusSpan.innerText = "Go Down";
                evalStatusSpan.style.color = "orange";
            } else if (angle < 90) {
                exerciseState = 'down';
                evalStatusSpan.innerText = "Go Up";
                evalStatusSpan.style.color = "green";
            }
        }
    } else if (exerciseName === 'Jumping Jacks') {
        const leftWrist = landmarks[15];
        const rightWrist = landmarks[16];
        const leftShoulder = landmarks[11];
        
        if (leftWrist && rightWrist && leftShoulder) {
            if (leftWrist.y < leftShoulder.y && rightWrist.y < leftShoulder.y) {
                if (exerciseState === 'down') {
                    validatedReps++;
                    showFeedback("Good rep!");
                    updateRepCount();
                }
                exerciseState = 'up';
                evalStatusSpan.innerText = "Arms Down";
                evalStatusSpan.style.color = "orange";
                angle = 180;
            } else if (leftWrist.y > leftShoulder.y && rightWrist.y > leftShoulder.y) {
                exerciseState = 'down';
                evalStatusSpan.innerText = "Arms Up";
                evalStatusSpan.style.color = "green";
                angle = 0;
            }
        }
    }
    
    currentAngleSpan.innerText = Math.round(angle);
    
    if (validatedReps >= TARGET_REPS) {
        isSessionComplete = true;
        evalStatusSpan.innerText = "Set Complete!";
        evalStatusSpan.style.color = "green";
        showFeedback("Set Complete!");
        setTimeout(endSession, 2000);
    }
}

function updateRepCount() {
    repCountSpan.innerText = `${validatedReps} / ${TARGET_REPS}`;
    bigRepCount.innerText = `${validatedReps} / ${TARGET_REPS}`;
}

function isFullBodyVisible(landmarks) {
    // Check nose, wrists, and ankles
    const requiredPoints = [0, 15, 16, 27, 28];
    for (let idx of requiredPoints) {
        if (!landmarks[idx] || landmarks[idx].visibility < 0.5) {
            return false;
        }
    }
    return true;
}

function onResults(results) {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    
    // Draw video frame
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);
    
    if (results.poseLandmarks) {
        // Draw the pose
        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {color: '#00FF00', lineWidth: 4});
        drawLandmarks(canvasCtx, results.poseLandmarks, {color: '#FF0000', lineWidth: 2});
        
        if (!isFullBodyVisible(results.poseLandmarks)) {
            evalStatusSpan.innerText = "Please ensure full body is visible in the camera.";
            evalStatusSpan.style.color = "red";
        } else {
            processExerciseLogic(results.poseLandmarks);
        }
    } else {
        evalStatusSpan.innerText = "No pose detected. Please step into frame.";
        evalStatusSpan.style.color = "red";
    }
    canvasCtx.restore();
}

function showFeedback(msg) {
    feedbackOverlay.innerText = msg;
    feedbackOverlay.style.display = 'block';
    feedbackEvents.push({time: new Date().toISOString(), message: msg});
    setTimeout(() => {
        feedbackOverlay.style.display = 'none';
    }, 1500);
}

const pose = new Pose({locateFile: (file) => {
  return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
}});

pose.setOptions({
  modelComplexity: 1,
  smoothLandmarks: true,
  enableSegmentation: false,
  smoothSegmentation: false,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5
});

pose.onResults(onResults);

const camera = new Camera(videoElement, {
  onFrame: async () => {
    await pose.send({image: videoElement});
  },
  width: 640,
  height: 480
});
camera.start();

function endSession() {
    camera.stop();
    const duration = Math.round((new Date() - sessionStartTime) / 1000);
    
    fetch('/api/log_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            exercise_name: exerciseName,
            duration: duration,
            validated_reps: validatedReps,
            measured_values: JSON.stringify(measuredValues),
            feedback_events: JSON.stringify(feedbackEvents)
        })
    }).then(response => response.json())
      .then(data => {
          if (data.status === 'success') {
              window.location.href = '/report/' + data.session_id;
          }
      });
}

// Handle manual ending of session
document.getElementById('endSessionBtn').addEventListener('click', endSession);
