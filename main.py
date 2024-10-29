import os
import json
import pickle
import datetime
import numpy as np
import matplotlib.pyplot as plt
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.lang import Builder
from kivy.uix.slider import Slider
from kivy.core.window import Window
from kivy.clock import Clock
from googleapiclient.http import MediaFileUpload
import sounddevice as sd

# Define kv design inline for better structure
kv = '''
ScreenManager:
    LoginScreen:
    AdminScreen:
    PatientScreen:
    AudiometerScreen:
    VisionTestScreen:

<LoginScreen>:
    name: 'login'
    BoxLayout:
        orientation: 'vertical'
        padding: [40, 50, 40, 50]
        spacing: 20
        canvas.before:
            Color:
                rgba: 0.2, 0.6, 0.86, 1  # Light blue background
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [20]

        Label:
            text: "SENSORY-CHECK"
            font_size: 32
            bold: True
            color: 1, 1, 1, 1

        TextInput:
            id: username_input
            hint_text: "Username"
            multiline: False
            height: 50
            size_hint_y: None
            background_color: 1, 1, 1, 0.8
            foreground_color: 0, 0, 0, 1
            padding_x: 10

        TextInput:
            id: password_input
            hint_text: "Password"
            password: True
            multiline: False
            height: 50
            size_hint_y: None
            background_color: 1, 1, 1, 0.8
            foreground_color: 0, 0, 0, 1
            padding_x: 10

        Button:
            text: "Login"
            size_hint_y: None
            height: 50
            background_color: (0.3, 0.8, 0.3, 1)
            on_press: root.verify_login()

<AdminScreen>:
    name: 'admin'
    BoxLayout:
        orientation: 'vertical'
        padding: [40, 50, 40, 50]
        spacing: 20

        Label:
            text: "Welcome Admin"
            font_size: 24
            color: 0, 0, 0, 1

        Button:
            text: "Manage Users"
            size_hint_y: None
            height: 50
            background_color: (0.3, 0.7, 0.9, 1)

        Button:
            text: "View Reports"
            size_hint_y: None
            height: 50
            background_color: (0.3, 0.7, 0.9, 1)

        Button:
            text: "Log Out"
            size_hint_y: None
            height: 50
            background_color: (0.8, 0.2, 0.2, 1)
            on_press: app.root.current = 'login'

<PatientScreen>:
    name: 'patient'
    BoxLayout:
        orientation: 'vertical'
        padding: [40, 50, 40, 50]
        spacing: 20

        Label:
            text: "Welcome Patient"
            font_size: 24
            color: 0, 0, 0, 1

        Button:
            text: "Perform Audiometer Test"
            size_hint_y: None
            height: 50
            background_color: (0.4, 0.8, 0.4, 1)
            on_press: app.root.current = 'audiometer'

        Button:
            text: "Perform Vision Test"
            size_hint_y: None
            height: 50
            background_color: (0.4, 0.8, 0.4, 1)
            on_press: app.root.current = 'vision_test'

        Button:
            text: "Log Out"
            size_hint_y: None
            height: 50
            background_color: (0.8, 0.2, 0.2, 1)
            on_press: app.root.current = 'login'

<AudiometerScreen>:
    name: 'audiometer'
    BoxLayout:
        orientation: 'vertical'
        padding: [40, 50, 40, 50]
        spacing: 20

        Label:
            text: "Audiometer Test"
            font_size: 24
            color: 0, 0, 0, 1

        Label:
            id: frequency_label
            text: "Adjust the slider to your hearing level."
            font_size: 18
            color: 0, 0, 0, 1

        Slider:
            id: frequency_slider
            min: 0
            max: 100
            value: 50
            on_value: root.update_frequency(self.value)

        Button:
            text: "Play Test Tone"
            size_hint_y: None
            height: 50
            background_color: (0.4, 0.8, 0.4, 1)
            on_press: root.play_test_tone()

        Button:
            text: "Submit Result"
            size_hint_y: None
            height: 50
            background_color: (0.4, 0.8, 0.4, 1)
            on_press: root.submit_result()

        Button:
            text: "Back to Patient Menu"
            size_hint_y: None
            height: 50
            background_color: (0.8, 0.2, 0.2, 1)
            on_press: app.root.current = 'patient'

<VisionTestScreen>:
    name: 'vision_test'
    BoxLayout:
        orientation: 'vertical'
        padding: [40, 50, 40, 50]
        spacing: 20

        Label:
            text: "Vision Test"
            font_size: 24
            color: 0, 0, 0, 1

        Image:
            source: 'snellen_chart.jpg'  # Ensure this image is in the same directory
            allow_stretch: True
            size_hint: (1, 0.6)

        TextInput:
            id: acuity_input
            hint_text: "Enter Visual Acuity (e.g., 20/20)"
            multiline: False
            height: 50
            size_hint_y: None
            background_color: 1, 1, 1, 0.8
            foreground_color: 0, 0, 0, 1
            padding_x: 10

        Button:
            text: "Submit Vision Result"
            size_hint_y: None
            height: 50
            background_color: (0.4, 0.8, 0.4, 1)
            on_press: root.submit_result()

        Button:
            text: "Back to Patient Menu"
            size_hint_y: None
            height: 50
            background_color: (0.8, 0.2, 0.2, 1)
            on_press: app.root.current = 'patient'
'''

# Set the background color globally (light gray)
Window.clearcolor = (0.9, 0.9, 0.9, 1)

# Simulated user login data
users = {
    "admin": {"password": "admin", "role": "admin"},
    "patient": {"password": "patient", "role": "patient"}
}

# File for storing test results
results_file = "test_results.json"
graph_file = "audiometer_results.png"

# Google Drive API scopes
SCOPES = ['POST https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart']

class LoginScreen(Screen):
    def verify_login(self):
        username = self.ids.username_input.text
        password = self.ids.password_input.text
        user_data = users.get(username)

        if user_data and user_data['password'] == password:
            if user_data['role'] == 'admin':
                self.manager.current = 'admin'
            else:
                self.manager.current = 'patient'
        else:
            popup = Popup(title='Login Failed',
                          content=Label(text='Invalid username or password.'),
                          size_hint=(None, None), size=(300, 200))
            popup.open()

class AdminScreen(Screen):
    pass

class PatientScreen(Screen):
    pass

class AudiometerScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.drive_service = None

    def initialize_drive(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        service = build('drive', 'v3', credentials=creds)

    def update_frequency(self, value):
        self.ids.frequency_label.text = f"Selected Frequency: {value} dB"

    def play_test_tone(self):
        frequency = self.ids.frequency_slider.value
        duration = 10  # seconds
        sample_rate = 44100  # Hz
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)  # time variable
        tone = 0.5 * np.sin(2 * np.pi * frequency * t)  # generate a sine wave
        sd.play(tone, samplerate=sample_rate)

    def submit_result(self):
        frequency = self.ids.frequency_slider.value
        result = {"frequency": frequency, "timestamp": datetime.datetime.now().isoformat()}
        
        self.save_result(result)
        self.generate_graph()

        # Show confirmation
        popup = Popup(title='Result Submitted',
                      content=Label(text='Your result has been submitted.'),
                      size_hint=(None, None), size=(300, 200))
        popup.open()

    def save_result(self, result):
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
                except json.JSONDecodeError:
                    data = {}        
        else:
            data = {}

        timestamp = result["timestamp"]
        data[timestamp] = result["frequency"]

        with open(results_file, 'w') as f:
            json.dump(data, f)

        # Ensure the Google Drive API is initialized
        self.initialize_drive()
        # Upload the results file to Google Drive
        self.upload_to_drive(results_file)

    def generate_graph(self):
        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                data = json.load(f)

            frequencies = list(data.values())
            timestamps = list(data.keys())

            plt.figure(figsize=(10, 5))
            plt.plot(timestamps, frequencies, marker='o')
            plt.title('Audiometer Test Results')
            plt.xlabel('Timestamp')
            plt.ylabel('Frequency (Hz)')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(graph_file)
            plt.close()

        # Ensure the Google Drive API is initialized
        self.initialize_drive()
        # Upload the graph to Google Drive
        self.upload_to_drive(graph_file)

    def upload_to_drive(self, file_name):
        if self.drive_service:
            file_metadata = {'name': os.path.basename(file_name)}
            media = MediaFileUpload(file_name, mimetype='application/json' if file_name.endswith('.json') else 'image/png')
            self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

class VisionTestScreen(Screen):
    def submit_result(self):
        acuity = self.ids.acuity_input.text
        result = {"acuity": acuity, "timestamp": datetime.datetime.now().isoformat()}

        if os.path.exists(results_file):
            with open(results_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}

        timestamp = result["timestamp"]
        data[timestamp] = result["acuity"]

        with open(results_file, 'w') as f:
            json.dump(data, f)

        # Show confirmation
        popup = Popup(title='Result Submitted',
                      content=Label(text='Your vision result has been submitted.'),
                      size_hint=(None, None), size=(300, 200))
        popup.open()

class SensoryCheckApp(App):
    def build(self):
        return Builder.load_string(kv)

if __name__ == '__main__':
    SensoryCheckApp().run()
