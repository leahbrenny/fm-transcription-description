from flask import Flask, request, render_template, send_file, jsonify
from dotenv import load_dotenv
import os
import openai
import re
import shutil
import zipfile  # Import the zipfile module
from faster_whisper import WhisperModel
from faster_whisper.utils import format_timestamp

app = Flask(__name__)

# Define global variables to store transcription results and text file paths
transcription_results = []
txt_file_paths = []  # Initialize the list for text file paths

# Create the 'temp' directory if it doesn't exist
if not os.path.exists("temp"):
    os.makedirs("temp")


@app.route("/")
def index():
    return render_template("index.html")


# ...


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_files = request.files.getlist("audio_files")

    if not audio_files:
        return "No files provided."

    try:
        # Check if GPU is available
        use_gpu = False
        try:
            # Attempt to create a WhisperModel with GPU support
            model_size = "medium.en"
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            use_gpu = True
        except Exception as gpu_error:
            print(f"GPU not available: {gpu_error}")

        # If GPU is not available, use CPU with INT8
        if not use_gpu:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")

        # Clear the 'temp' directory if it contains any files
        temp_directory = "temp"
        for filename in os.listdir(temp_directory):
            file_path = os.path.join(temp_directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")

        # Remove previously generated .zip file
        for filename in os.listdir(os.getcwd()):
            if filename.endswith(".zip"):
                os.unlink(filename)

        transcription_results = []  # Store transcription results
        txt_file_paths = []

        for audio_file in audio_files:
            # Determine the file extension
            file_extension = os.path.splitext(audio_file.filename)[1].lower()

            if file_extension in (".mp3", ".mp4"):
                # Save the uploaded file to a temporary location
                audio_file_path = os.path.join("temp", audio_file.filename)
                audio_file.save(audio_file_path)

                segments, info = model.transcribe(audio_file_path, beam_size=5)

                transcription_text = ""

                total_duration = info.duration  # Total duration of the audio file

                for segment in segments:
                    start_time = None
                    end_time = None

                    for word in segment.words:
                        # Update start_time with the start time of the first word
                        if start_time is None:
                            start_time = word.start

                        # Update end_time with the end time of the current word
                        end_time = word.end

                    # Calculate progress percentage based on end_time compared to total duration
                    progress_percentage = (end_time / total_duration) * 100
                    print(f"Transcription progress: {progress_percentage:.2f}%")

                    # Update transcription_text to use start_time and end_time
                    transcription_text += f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n {segment.text}\n"


                transcription_results.append((audio_file.filename, transcription_text))

                # Remove the temporary audio file
                os.remove(audio_file_path)
            else:
                return f"Invalid file type: {audio_file.filename}. Supported types: .mp3 and .mp4"

        # Create and save .txt and .vtt files
        txt_file_paths = []
        vtt_file_paths = []

        for filename, transcription_text in transcription_results:
            txt_file_path = os.path.join("temp", f"{os.path.splitext(filename)[0]}.txt")
            vtt_file_path = os.path.join("temp", f"{os.path.splitext(filename)[0]}.vtt")

            with open(txt_file_path, "w") as text_file, open(
                vtt_file_path, "w"
            ) as vtt_file:
                lines = transcription_text.strip().split("\n")
                vtt_file.write("WEBVTT\n\n")

                line_number = 1

                for i, line in enumerate(lines):
                    if i % 2 == 0:  # Timestamp lines
                        vtt_file.write(
                            f"{line_number}\n{line.strip()}\n"
                        )  # Write line number and timestamp
                        line_number += 1
                    else:  # Text lines
                        vtt_file.write(
                            f"{line.strip()}\n\n"
                        )  # Add an empty line only after the text

            txt_file_paths.append(txt_file_path)
            vtt_file_paths.append(vtt_file_path)

        # Generate a single .zip file containing both .txt and .vtt files
        if len(txt_file_paths) > 0:
            zip_filename = "transcriptions.zip"
            with zipfile.ZipFile(zip_filename, "w") as zipf:
                for txt_file_path in txt_file_paths:
                    zipf.write(txt_file_path, os.path.basename(txt_file_path))
                    vtt_file_path = txt_file_path.replace(".txt", ".vtt")
                    if os.path.exists(vtt_file_path):
                        zipf.write(vtt_file_path, os.path.basename(vtt_file_path))

        # Automatically download the .zip file
        if os.path.exists(zip_filename):
            response = send_file(zip_filename, as_attachment=True)
            return response

        return "No valid transcription files found."

    except Exception as e:
        # Handle exceptions here
        return "An error occurred during transcription: " + str(e)


# ...


@app.route("/generate_descriptions", methods=["POST"])
def generate_descriptions():
    try:
        # Load environment variables from .env
        load_dotenv()

        # Set OpenAI API key
        openai.api_key = os.getenv("OPENAI_API_KEY")

        temp_directory = "temp"
        response_descriptions = []

        for filename in os.listdir(temp_directory):
            if filename.endswith(".txt"):
                # Extract the file name without extension
                file_name_without_extension = os.path.splitext(filename)[0]

                txt_file_path = os.path.join(temp_directory, filename)
                with open(txt_file_path, "r") as text_file:
                    transcription_text = text_file.read()

                # Use regular expressions to extract the text within square brackets
                timestamps_removed = re.sub(
                    r"\[\d+\.\d+s -> \d+\.\d+s\] ", "", transcription_text
                )

                # Combine the entire text into a single message
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-16k",
                    messages=[
                        {
                            "role": "system",
                            "content": "Provide a 2 to 3 sentence description of what happens in the lesson you are provided",
                        },
                        {"role": "user", "content": timestamps_removed},
                    ],
                    temperature=0,
                    max_tokens=1024,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )

                # Get the generated description from the API response and replace '\t' with '&nbsp;'
                description = (
                    response.choices[0].message["content"].replace("\t", "&nbsp;")
                )

                # Append the "lesson_name\tlesson_description" to the response_descriptions list
                response_descriptions.append(
                    f"{file_name_without_extension}\\t{description}"
                )

        # Join the descriptions into a single string with HTML non-breaking spaces and return it
        return "<br>".join(response_descriptions)

    except Exception as e:
        # Handle exceptions here
        return jsonify(
            {"error": "An error occurred during description generation: " + str(e)}
        )


# ...

if __name__ == "__main__":
    app.run(debug=True)
