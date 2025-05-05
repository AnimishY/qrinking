# QR Code Generator with Flask and Firebase

A web application built with Flask that allows users to create QR codes for links and store them using Firebase authentication and storage.

## Features
- User authentication (signup/login) using Firebase Authentication
- Generate QR codes from URLs
- Store QR codes in Firebase Storage
- View all generated QR codes in a dashboard
- Delete unwanted QR codes

## Setup Instructions

### 1. Prerequisites
- Python 3.7+
- Firebase account

### 2. Create a Firebase Project
1. Go to the [Firebase Console](https://console.firebase.google.com/)
2. Create a new project
3. Set up Firebase Authentication with Email/Password provider
4. Set up Firebase Realtime Database
5. Set up Firebase Storage

### 3. Install Dependencies
```
pip install -r requirements.txt
```

### 4. Configure Firebase
Update the Firebase configuration in `app.py`:

```python
config = {
    "apiKey": "YOUR_API_KEY",
    "authDomain": "YOUR_PROJECT_ID.firebaseapp.com",
    "databaseURL": "https://YOUR_PROJECT_ID.firebaseio.com",
    "projectId": "YOUR_PROJECT_ID",
    "storageBucket": "YOUR_PROJECT_ID.appspot.com",
    "messagingSenderId": "YOUR_MESSAGING_SENDER_ID",
    "appId": "YOUR_APP_ID"
}
```

You can find these values in the Firebase console: Project settings > General > Your apps > SDK setup and configuration.

### 5. Run the Application
```
python app.py
```

The application will be available at http://127.0.0.1:5000/

## Usage
1. Sign up for a new account or log in with existing credentials
2. On the dashboard, enter a URL to generate a QR code
3. View all your generated QR codes
4. Click on "Delete" to remove a QR code
5. Click on "Visit Link" to open the URL in a new tab
