import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, Label, Button, Frame, messagebox
from PIL import Image, ImageTk
import csv
import sqlite3
from datetime import datetime

# متغیرهای جهانی
current_eye_colors = []
cap = None  # متغیر برای وب‌کم

# تابع انتخاب و پردازش تصویر از فایل
def select_image():
    global current_eye_colors
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
    if not file_path:
        return
    image = cv2.imread(file_path)
    if image is None:
        messagebox.showerror("Error", "Failed to load image.")
        return
    process_image(image)

# تابع شروع وب‌کم
def start_camera():
    global cap
    if cap is not None and cap.isOpened():
        messagebox.showinfo("Info", "Camera is already running!")
        return
    cap = cv2.VideoCapture(0)  # باز کردن وب‌کم پیش‌فرض
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to open camera!")
        return
    update_camera_frame()

# تابع توقف وب‌کم
def stop_camera():
    global cap
    if cap is not None and cap.isOpened():
        cap.release()
        image_label.config(image='')
        result_label.config(text="Camera stopped.")
        cap = None

# تابع به‌روزرسانی فریم‌های وب‌کم
def update_camera_frame():
    global cap, current_eye_colors
    if cap is None or not cap.isOpened():
        return
    ret, frame = cap.read()
    if ret:
        process_image(frame)
        root.after(10, update_camera_frame)  # هر 10 میلی‌ثانیه فریم جدید بگیر

# تابع پردازش تصویر
def process_image(image):
    global current_eye_colors
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    gray = cv2.equalizeHist(gray)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(30, 30))
    eye_colors = []

    for (x, y, w, h) in faces:
        cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
        roi_gray = gray[y:y+h, x:x+w]
        roi_color = image[y:y+h, x:x+w]
        
        eyes = eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=5)
        
        for i, (ex, ey, ew, eh) in enumerate(eyes[:2]):
            eye = roi_color[ey:ey+eh, ex:ex+ew]
            pupil = detect_pupil(eye)
            if pupil is not None:
                (px, py, pr) = pupil
                pupil_region = eye[max(0, py-pr):py+pr, max(0, px-pr):px+pr]
                eye_color = detect_eye_color(pupil_region)
                cv2.circle(roi_color, (ex + px, ey + py), pr, (0, 255, 0), 2)
            else:
                eye_color = detect_eye_color(eye)
            eye_colors.append(f"Eye {i+1}: {eye_color}")
            cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)

    current_eye_colors = eye_colors
    display_image(image)
    update_results(eye_colors)

# تابع تشخیص مردمک
def detect_pupil(eye):
    eye_gray = cv2.cvtColor(eye, cv2.COLOR_BGR2GRAY)
    eye_gray = cv2.GaussianBlur(eye_gray, (5, 5), 0)
    circles = cv2.HoughCircles(eye_gray, cv2.HOUGH_GRADIENT, dp=1, minDist=20,
                               param1=50, param2=30, minRadius=5, maxRadius=20)
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        return circles[0]
    return None

# تابع تشخیص رنگ
def detect_eye_color(region):
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    avg_hue = np.mean(h)
    avg_sat = np.mean(s)
    avg_val = np.mean(v)

    if avg_hue < 15 or avg_hue > 165:
        return "Brown" if avg_sat > 50 else "Black"
    elif 15 <= avg_hue < 35:
        return "Amber"
    elif 35 <= avg_hue < 85:
        return "Green" if avg_sat > 40 else "Hazel"
    elif 85 <= avg_hue < 135:
        return "Blue" if avg_val > 80 else "Gray"
    else:
        return "Gray"
    # تابع نمایش image در Tkinter
def display_image(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)
    max_size = (600, 400)
    image_pil.thumbnail(max_size, Image.Resampling.LANCZOS)
    image_tk = ImageTk.PhotoImage(image_pil)
    image_label.config(image=image_tk)
    image_label.image = image_tk

# تابع به‌روزرسانی نتایج
def update_results(eye_colors):
    result_text = "Detected Eye Colors:\n" + "\n".join(eye_colors) if eye_colors else "No eyes detected."
    result_label.config(text=result_text)

# تابع ذخیره نتایج
def save_results():
    if not current_eye_colors:
        messagebox.showwarning("Warning", "No eye colors detected to save!")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"eye_colors_{timestamp}.csv"
    try:
        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Eye Number", "Eye Color", "Timestamp"])
            for eye_color in current_eye_colors:
                eye_num, color = eye_color.split(": ")
                writer.writerow([eye_num, color, timestamp])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save to CSV: {str(e)}")
        return

    try:
        conn = sqlite3.connect("eye_colors.db")
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS eye_colors
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          eye_number TEXT,
                          eye_color TEXT,
                          timestamp TEXT)''')
        for eye_color in current_eye_colors:
            eye_num, color = eye_color.split(": ")
            cursor.execute("INSERT INTO eye_colors (eye_number, eye_color, timestamp) VALUES (?, ?, ?)",
                           (eye_num, color, timestamp))
        conn.commit()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save to SQLite: {str(e)}")
        return

    messagebox.showinfo("Success", f"Results saved to {csv_filename} and SQLite database!")

# ایجاد رابط کاربری
root = tk.Tk()
root.title("Eye Color Detector")
root.geometry("800x600")
root.configure(bg="#00CED1")

button_frame = Frame(root, bg="#00CED1")
button_frame.pack(pady=10)

select_btn = Button(button_frame, text="Select Image", command=select_image, 
                    bg="#4682B4", fg="white", font=("Arial", 12, "bold"), relief="raised")
select_btn.pack(side=tk.LEFT, padx=5)

camera_btn = Button(button_frame, text="Start Camera", command=start_camera, 
                    bg="#32CD32", fg="white", font=("Arial", 12, "bold"), relief="raised")
camera_btn.pack(side=tk.LEFT, padx=5)

stop_btn = Button(button_frame, text="Stop Camera", command=stop_camera, 
                  bg="#FF4500", fg="white", font=("Arial", 12, "bold"), relief="raised")
stop_btn.pack(side=tk.LEFT, padx=5)

save_btn = Button(button_frame, text="Save Results", command=save_results, 
                  bg="#FF6347", fg="white", font=("Arial", 12, "bold"), relief="raised")
save_btn.pack(side=tk.LEFT, padx=5)

image_label = Label(root, bg="#00CED1", borderwidth=2, relief="solid")
image_label.pack(pady=10)

result_label = Label(root, text="No image selected.", font=("Arial", 14, "bold"), 
                     bg="#00CED1", fg="#FFFFFF")
result_label.pack(pady=10)

root.mainloop()

# آزاد کردن منابع هنگام بستن برنامه
def on_closing():
    stop_camera()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)