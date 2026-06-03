import cv2
import mediapipe as mp
import pyautogui
import math
import time
import threading
import speech_recognition as sr
import os

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

screen_width, screen_height = pyautogui.size()

prev_x, prev_y = 0, 0
click_time = 0
dragging = False
paused = False
command_text = "Waiting..."

CLICK_DELAY = 0.4
prev_time = 0


# -----------------------------
# VOICE ENGINE (SAFE)
# -----------------------------
def voice_listener():
    global command_text, paused

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    while True:
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, phrase_time_limit=3)

            command = recognizer.recognize_google(audio).lower()
            command_text = command

            print("VOICE:", command)

            if "stop system" in command:
                paused = True

            elif "resume system" in command:
                paused = False

            elif "open chrome" in command:
                os.system("start chrome")

            elif "open notepad" in command:
                os.system("notepad")

        except:
            pass


threading.Thread(target=voice_listener, daemon=True).start()


# -----------------------------
# GESTURE SYSTEM
# -----------------------------
def recognize_gesture(lm):
    def up(tip, pip):
        return tip.y < pip.y

    index_up = up(lm[8], lm[6])
    middle_up = up(lm[12], lm[10])
    ring_up = up(lm[16], lm[14])
    pinky_up = up(lm[20], lm[18])

    thumb_up = lm[4].y < lm[2].y
    thumb_down = lm[4].y > lm[2].y

    if not index_up and not middle_up and not ring_up and not pinky_up:
        if thumb_up:
            return "👍 Thumb Up"
        elif thumb_down:
            return "👎 Thumb Down"
        return "✊ Fist"

    if index_up and middle_up and ring_up and pinky_up:
        return "🖐 Open Palm"

    if index_up and not middle_up and not ring_up and not pinky_up:
        return "☝️ Pointing"

    if index_up and middle_up and not ring_up and not pinky_up:
        return "✌️ Peace"

    return "🤷 Unknown"


def dist(a, b):
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)


# -----------------------------
# WINDOW
# -----------------------------
cap = cv2.VideoCapture(0)

cv2.namedWindow("NIKO CONTROL SYSTEM", cv2.WINDOW_NORMAL)
cv2.resizeWindow("NIKO CONTROL SYSTEM", 1000, 700)

print("🧠 NIKO SYSTEM ONLINE")
print("ESC / Q / X to exit")

# -----------------------------
# LOOP
# -----------------------------
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time

    key = cv2.waitKey(1) & 0xFF
    if key in [27, ord('q'), ord('x')]:
        break

    gesture_text = "No Hand"
    status = "ACTIVE" if not paused else "PAUSED"

    if paused:
        cv2.putText(frame, "SYSTEM PAUSED", (50, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        cv2.imshow("NIKO CONTROL SYSTEM", frame)
        continue

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:

            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            lm = hand_landmarks.landmark

            # -----------------------------
            # CURSOR CONTROL
            # -----------------------------
            index = lm[8]
            thumb = lm[4]

            x = int(index.x * screen_width)
            y = int(index.y * screen_height)

            smooth_x = prev_x + (x - prev_x) * 0.25
            smooth_y = prev_y + (y - prev_y) * 0.25

            pyautogui.moveTo(smooth_x, smooth_y)

            prev_x, prev_y = smooth_x, smooth_y

            # -----------------------------
            # CLICK / DRAG
            # -----------------------------
            tx = int(thumb.x * screen_width)
            ty = int(thumb.y * screen_height)

            pinch = dist((x, y), (tx, ty))

            if pinch < 35 and not dragging and time.time() - click_time > CLICK_DELAY:
                pyautogui.click()
                click_time = time.time()

            if pinch < 35 and not dragging:
                pyautogui.mouseDown()
                dragging = True

            elif pinch > 50 and dragging:
                pyautogui.mouseUp()
                dragging = False

            gesture_text = recognize_gesture(lm)

    # -----------------------------
    # TRANSPARENT NIKO HUD
    # -----------------------------
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (650, 260), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.20, frame, 0.80, 0, frame)

    cv2.rectangle(frame, (10, 10), (650, 260), (0, 200, 255), 1)

    cv2.putText(frame, "NIKO CONTROL SYSTEM", (25, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)

    cv2.putText(frame, f"STATUS: {status}", (25, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (0, 255, 0) if not paused else (0, 0, 255), 2)

    cv2.putText(frame, f"GESTURE: {gesture_text}", (25, 150),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 200), 2)

    cv2.putText(frame, f"VOICE: {command_text}", (25, 190),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

    cv2.putText(frame, f"FPS: {int(fps)}", (25, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)

    # -----------------------------
    # SOFT GLOW CURSOR
    # -----------------------------
    cursor = (int(prev_x), int(prev_y))

    cv2.circle(frame, cursor, 10, (0, 200, 255), -1)
    cv2.circle(frame, cursor, 16, (0, 200, 255), 2)

    cv2.imshow("NIKO CONTROL SYSTEM", frame)

# -----------------------------
# CLEAN EXIT
# -----------------------------
cap.release()
cv2.destroyAllWindows()