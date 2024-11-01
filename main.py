import openai
import speech_recognition as sr
import webbrowser
import requests
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from resemble import Resemble
import os
import time

#MAKE SURE the name is lowercase or it will not recognize it, this will be the name displayed in output but also the wake world (Like a Alexa for example)
Bot_Name = "Your_Bot_Name"

# set this to how long you want the bot to wait for a response before reuiring its name to be spoken again.
silence_duration = 5

# Set your API keys Here, You need 1 for Open AI, 3 Api keys for resemble.
openai.api_key = "Open_AI_API_KEY"

resemble_api_key = "Your_Resemble_API"

project_uuid = "Resemble_Project_UUID"  
#Which is found in the URL
voice_uuid = "Voice_UUID" 
# which is listed after creating a new Voice clone

Resemble.api_key(resemble_api_key)

# Function to get all projects
def get_all_projects():
    response = Resemble.v2.projects.all(page=1, page_size=10)
    return response['items']

# Function to check to OpenAI and get a response
def get_chatgpt_response(query):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ],
            temperature=0.7
        )
        return response['choices'][0]['message']['content']
    except openai.OpenAIError as e:
        print(f"An error occurred: {e}")
        return None

# Resemble AI Voice gen thingy
def generate_voice(text):
    payload = {
        "data": {
            "text": text,
            "voice_uuid": voice_uuid
        }
    }
    
    try:
        response = Resemble.v2.clips.create_sync(project_uuid, voice_uuid, text)
        if response['success']:
            audio_url = response['item']['audio_src']
            return audio_url
        else:
            print(f"Error generating voice: {response['message']}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Function to download audio Which will be played
def download_audio(audio_url, file_name):
    try:
        response = requests.get(audio_url)
        if response.status_code == 200:
            # Save the audio file in the current directory
            with open(file_name, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"Failed to download audio: {response.status_code}")
            return False
    except Exception as e:
        print(f"An error occurred while downloading audio: {e}")
        return False

# Function to play audio using sounddevice Library (I tried other librarys most of them wouldnt work the same)

def play_audio(file_name):
    print(f"Playing audio from {file_name}...")
    # Read the audio file as WAV format
    fs, data = wavfile.read(file_name) 
    sd.play(data, fs)  # Play the audio file
    sd.wait()  # Wait until sound is done.

# Speech recognition for listening to the bot name variable at the top
def listen_for_Bot():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("Listening for "+Bot_Name+"...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        speech_text = recognizer.recognize_google(audio)
        print(f"You said: {speech_text}")

        if Bot_Name in speech_text:
            print(Bot_Name+" detected. Listening for further input...")
            return True
        return False

    except sr.UnknownValueError:
        print("Could not understand the audio.")
        return False
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return False

# Capture user's query after detecting  the bots name
def capture_user_query():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("Listening for your query...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        query = recognizer.recognize_google(audio)
        print(f"User query: {query}")
        return query

    except sr.UnknownValueError:
        print("Could not understand the audio.")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return ""

# Continuous listening for user input with a timeout
def continuous_listening(): 
    last_time = time.time()

    while True:
        if listen_for_Bot():  # Wait for the wake word, which you name at the top
            while True:
                user_query = capture_user_query()
                if user_query:
                    # Get response from ChatGPT with API 
                    chatgpt_response = get_chatgpt_response(user_query)
                    if chatgpt_response:
                        print(f"ChatGPT Response: {chatgpt_response}")

                        # Generate voice for the ChatGPT response
                        audio_url = generate_voice(chatgpt_response)
                        if audio_url:
                            print(f"Audio URL: {audio_url}")
                            # Name the file to save
                            audio_file = "response_audio.wav"
                            if download_audio(audio_url, audio_file):
                                print(f"Downloaded audio to {audio_file}.")
                                
                                # Check if the audio file is valid before playing
                                if os.path.getsize(audio_file) > 0:  
                                    play_audio(audio_file)  # Play the audio file using sounddevice library
                                else:
                                    print("Downloaded audio file is empty.")
                            else:
                                print("Failed to download audio.")
                        else:
                            print("Failed to generate voice.")
                    
                    last_time = time.time()  # Reset the timer if user speaks
                else:
                    # Check for silence
                    if time.time() - last_time > silence_duration:
                        print("No input detected for "+str(silence_duration)+" seconds. Going back to listening for 'Nathan'...")
                        break  # Exit to the outer loop to wait for the wake word

if __name__ == "__main__":
    # Verify project UUID
    projects = get_all_projects()
    print("Available Projects:")
    for project in projects:
        print(f"Project ID: {project['uuid']}, Name: {project['name']}")

    continuous_listening()  # Start the continuous listening loop
