from flask import Flask, request, render_template, send_file, jsonify
from extensions import socketio
from dotenv import load_dotenv
import json
import math
import os
import openai
import re
import shutil
import string
import zipfile
from faster_whisper import WhisperModel
from faster_whisper.utils import format_timestamp, format_txt_timestamp

app = Flask(__name__)
socketio.init_app(app)


# Define global variables to store transcription results and text file paths
transcription_results = []
txt_file_paths = []

# Create the 'temp' directory if it doesn't exist
if not os.path.exists("temp"):
    os.makedirs("temp")


def segments_to_json(segments):
    json_segments = []
    for segment in segments:
        json_segment = {
            "id": segment.id,
            "seek": segment.seek,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "temperature": segment.temperature,
            "avg_logprob": segment.avg_logprob,
            "compression_ratio": segment.compression_ratio,
            "no_speech_prob": segment.no_speech_prob,
            "words": [],
        }
        if segment.words:
            for word in segment.words:
                json_segment["words"].append(
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                        "probability": word.probability,
                    }
                )
        json_segments.append(json_segment)
    return json_segments


@app.route("/")
def index():
    # Check if a message indicating transcription completion is in the query parameters
    message = request.args.get("message")
    return render_template("index.html", message=message)


@app.route("/test")
def test_formatting():
    try:
        test_json = "last/enterprise-typescript_3A.mp4.json"
        with open(test_json, "r") as json_file:
            json_data = json.load(json_file)

        # Empty the temp directory
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

        test_format_txt(json_data)  # Pass json_data to format_txt function
        test_format_vtt(json_data)  # Pass json_data to format_vtt function

        return "Test successful!"

    except Exception as e:
        return "An error occurred during testing: " + str(e)


@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    audio_files = request.files.getlist("audio_files")

    if not audio_files:
        return jsonify({"message": "No files provided."}), 400

    try:
        # Check if GPU is available
        use_gpu = False
        try:
            model_size = "medium.en"
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
            use_gpu = True
        except Exception as gpu_error:
            print(f"GPU not available: {gpu_error}")

        if not use_gpu:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")

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

        transcription_results = []

        for index, audio_file in enumerate(audio_files):
            file_extension = os.path.splitext(audio_file.filename)[1].lower()

            if file_extension in (".mp3", ".mp4"):
                audio_file_path = os.path.join("temp", audio_file.filename)
                audio_file.save(audio_file_path)
                socketio.emit(
                    "current_file",
                    {"message": f"{audio_file.filename}"},
                )  # Emit transcription progress
                segments, info = model.transcribe(audio_file_path, beam_size=5)

                # Process segments and convert to JSON-compatible format
                transcription_results.append(
                    (audio_file.filename, segments_to_json(segments))
                )
                os.remove(audio_file_path)

            else:
                return f"Invalid file type: {audio_file.filename}. Supported types: .mp3 and .mp4"

        # Convert transcription data to JSON format
        json_results = []
        for filename, segments in transcription_results:
            json_results.append({"filename": filename, "segments": segments})

        # Write JSON data to a file in the temp directory
        json_filename = os.path.join("temp", "transcription_results.json")
        with open(json_filename, "w") as json_file:
            json.dump(json_results, json_file, indent=2)

        # Call format_txt function to create .txt files
        format_txt(json_results)

        format_vtt(json_results)

        # Transcription completion...
        socketio.emit(
            "transcription_complete",
            {"message": "Transcription completed successfully."},
        )

        # Return a success response
        return jsonify({"message": "Transcription completed successfully."}), 200

    except Exception as e:
        # Handle exceptions...
        socketio.emit("transcription_error", {"error": str(e)})
        return jsonify({"error": str(e)}), 500  # Return an error response


def format_txt(json_data):
    for item in json_data:
        filename_without_extension = os.path.splitext(item["filename"])[0]
        filename = os.path.join("temp", filename_without_extension)
        segments = item["segments"]
        with open(f"{filename}.txt", "w") as txt_file:
            total_duration = 0
            current_block = ""
            start_time = segments[0]["words"][0][
                "start"
            ]  # Start time of the first word in the first segment
            for i, segment in enumerate(segments):
                segment_duration = (
                    segment["words"][-1]["end"] - segment["words"][0]["start"]
                )
                segment_text = segment["text"]
                # Remove leading space from text
                if segment_text.startswith(" "):
                    segment_text = segment_text[1:]
                # Check if adding this segment exceeds 30 seconds
                if total_duration + segment_duration <= 30:
                    if total_duration == 0:  # Add '>>' prefix only to the first line
                        current_block += f">> {segment_text} "
                    else:
                        current_block += f"{segment_text} "
                    total_duration += segment_duration
                else:
                    # Write the current block to file
                    txt_file.write(
                        f"{format_txt_timestamp(start_time)}\n{current_block.strip()}\n\n"
                    )
                    # Update start time for the next block
                    start_time = segment["words"][0]["start"]
                    # Start a new block
                    total_duration = segment_duration
                    current_block = f"{segment_text} "
            # Write the remaining block if any
            if current_block:
                txt_file.write(
                    f"{format_txt_timestamp(start_time)}\n{current_block.strip()}\n\n"
                )

# If new vtt_block set start time to word.start

# Check if vtt_block >= 90
# Create new vtt_block

# Check if word contains an end punctuation and vtt_block >= 60
# Add word w/ puncuation to to vtt_block
# Create new vtt_block

# Add word to vtt_block and current_line
# Set end time to word.end


def format_vtt(json_data):
    # Iterate through each item in the JSON data
    for item in json_data:
        # Extract filename without extension
        filename_without_extension = os.path.splitext(item["filename"])[0]
        # Generate file path for VTT file
        filename = os.path.join("temp", filename_without_extension)
        # Extract segments from the item
        segments = item["segments"]
        # Create VTT file name
        vtt_filename = f"{filename}.vtt"

        # Open VTT file for writing
        with open(vtt_filename, "w") as vtt_file:
            # Write VTT header
            vtt_file.write("WEBVTT\n\n")
            # Initialize segment number
            segment_number = 1
            # Iterate through each segment
            for segment in segments:
                # Using the start/end time of the first/last words in the segment
                start_time = segment["words"][0]["start"]
                end_time = segment["words"][-1]["end"]

                # Adjust start time if it's 0.0
                if start_time == 0.0:
                    start_time += 0.2  # Add 200 milliseconds

                # Remove the extra single space before the first word of each segment
                text = segment["text"]
                if text.startswith(" "):
                    text = text[1:]

                # Split text into lines at spaces without breaking words
                words = text.split()
                lines = []
                current_line = ""
                # Iterate through words and create lines without breaking words
                for word in words:
                    if len(current_line) + len(word) + 1 <= 50:
                        current_line += " " + word
                    else:
                        lines.append(current_line.strip())
                        current_line = word
                # Append the last line
                if current_line:
                    lines.append(current_line.strip())

                # Write segment number to VTT file
                vtt_file.write(f"{segment_number}\n")
                # Write start and end time of segment to VTT file
                vtt_file.write(
                    f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n"
                )
                # Write lines to VTT file
                for line in lines:
                    vtt_file.write(f"{line}\n")
                # Add empty line between segments
                vtt_file.write("\n")
                # Increment segment number
                segment_number += 1


def wrap_text(text):
    # Calculate the length of the text
    text_length = len(text)

    # Find the midpoint
    midpoint = text_length // 2

    # Find the nearest space before or after the midpoint
    split_index = text_length
    for i in range(midpoint, -1, -1):
        if text[i] == " ":
            split_index = i
            break
    for i in range(midpoint, text_length):
        if text[i] == " ":
            split_index = i
            break

    # Split the text into two parts
    if split_index != -1:
        first_part = text[:split_index].strip()
        second_part = text[split_index:].strip()
    else:
        first_part = text.strip()
        second_part = ""

    return f"{first_part}\n{second_part}" if second_part else first_part


def test_format_vtt(json_data):
    # Iterate through each item in the JSON data
    for item in json_data:
        # Extract filename without extension
        filename_without_extension = os.path.splitext(item["filename"])[0]
        # Generate file path for VTT file
        filename = os.path.join("temp", f"test_{filename_without_extension}")
        # Extract segments from the item
        segments = item["segments"]
        # Create VTT file name
        vtt_filename = f"{filename}.vtt"

        # Open VTT file for writing
        with open(vtt_filename, "w") as vtt_file:
            # Write VTT header
            vtt_file.write("WEBVTT\n\n")

            # Initialize block number
            block_number = 1
            vtt_block = ""

            # Iterate through each segment
            for segment in segments:
                segment_text = segment["text"]
                start_time = (
                    0.2
                    if segment["words"][0]["start"] == 0.0
                    else segment["words"][0]["start"]
                )
                end_time = segment["words"][-1]["end"]
                vtt_file.write(f"{block_number}\n")  # Write block number
                vtt_file.write(
                    f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n"
                )  # Write timestamp
                wrapped_text = wrap_text(segment_text)  # Wrap text
                vtt_file.write(
                    wrapped_text + "\n\n"
                )  # Write the wrapped text block to VTT file
                block_number += 1  # Increment block number


def test_format_txt(json_data):
    for item in json_data:
        filename_without_extension = os.path.splitext(item["filename"])[0]
        filename = os.path.join("temp", filename_without_extension)
        segments = item["segments"]
        with open(f"{filename}.txt", "w") as txt_file:
            total_duration = 0
            current_block = ""
            start_time = segments[0]["words"][0][
                "start"
            ]  # Start time of the first word in the first segment
            for i, segment in enumerate(segments):
                segment_duration = (
                    segment["words"][-1]["end"] - segment["words"][0]["start"]
                )
                segment_text = segment["text"]
                # Remove leading space from text
                if segment_text.startswith(" "):
                    segment_text = segment_text[1:]
                # Check if adding this segment exceeds 30 seconds
                if total_duration + segment_duration <= 30:
                    if total_duration == 0:  # Add '>>' prefix only to the first line
                        current_block += f">> {segment_text} "
                    else:
                        current_block += f"{segment_text} "
                    total_duration += segment_duration
                else:
                    # Write the current block to file
                    txt_file.write(
                        f"{format_txt_timestamp(start_time)}\n{current_block.strip()}\n\n"
                    )
                    # Update start time for the next block
                    start_time = segment["words"][0]["start"]
                    # Start a new block
                    total_duration = segment_duration
                    current_block = f"{segment_text} "
            # Write the remaining block if any
            if current_block:
                txt_file.write(
                    f"{format_txt_timestamp(start_time)}\n{current_block.strip()}\n\n"
                )


# ...


@app.route("/generate_descriptions", methods=["POST"])
def generate_descriptions():
    try:
        with open('run.env', 'r') as file:
            for line in file:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

        # Set OpenAI API key
        openai.api_key = os.getenv("OPENAI_API_KEY")

        temp_directory = "temp"
        response_descriptions = []

        for filename in os.listdir(temp_directory):
            if filename.endswith(".vtt"):  # Check for .vtt files
                # Extract the file name without extension
                file_name_without_extension = os.path.splitext(filename)[0]

                vtt_file_path = os.path.join(temp_directory, filename)
                with open(vtt_file_path, "r") as vtt_file:
                    vtt_content = vtt_file.read()

                # Use regular expressions to extract relevant information
                pattern = re.compile(
                    r"(\d+)\n(\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}\.\d{3})\n(.*?)(?=\d+\n\d{2}:\d{2}\.\d{3} -->|\Z)",
                    re.DOTALL,
                )
                matches = pattern.findall(vtt_content)

                timestamps_removed = ""
                for match in matches:
                    timestamps_removed += f"{match[0]}\n{match[1]}\n{match[2]}\n\n"

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
    # Run the application with SocketIO support
    socketio.run(app, debug=True)
