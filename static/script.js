document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("fileInput");
  const folderInput = document.getElementById("folderInput");
  const nameDisplay = document.getElementById("nameDisplay");
  const downloadButton = document.getElementById("downloadButton");
  const resetButton = document.getElementById("resetButton");
  const orText = document.getElementById("orText");
  const fileLabel = document.getElementById("fileLabel");
  const folderLabel = document.getElementById("folderLabel");
  const fileHeader = document.getElementById("fileHeader");
  const stepOneDescription = document.getElementById("stepOneDescription");
  const generateButton = document.getElementById("generateButton");
  const socket = io();
  let currentFileDuration;
  let currentWordEnd;
  let currentFile = null;
  let previousFile = null;

  fileInput.addEventListener("change", updateFileDisplay);
  folderInput.addEventListener("change", updateFileDisplay);
  document.getElementById("generateButton").disabled = true;
  document.getElementById("stepTwoDescription").classList.add("waiting")

  function updateFileDisplay() {
    const files = fileInput.files;
    resetFolderInput(); // Clear folder selection

    if (files.length > 0) {
      const filteredFileNames = Array.from(files)
        .map((file) => file.name.replace(/\.\w+$/, ""))
        .sort();
      displayFileNames(filteredFileNames, nameDisplay);
      showButtons();
      hideLabels();
      showHeaders();
    } else {
      hideButtons();
      showLabels();
      hideHeaders();
    }
  }

  function enableGenerateButton() {
    generateButton.disabled = false;
    document.getElementById("stepTwoDescription").innerText = "Transcripts ready. Generate descriptions?"
    document.getElementById("stepTwoDescription").classList.remove("waiting")
  }

  function disableGenerateButton() {
    generateButton.disabled = true;
    document.getElementById("stepTwoDescription").innerText =
      "Waiting on Step 1...";
    document.getElementById("stepTwoDescription").classList.add("waiting");
  }

  function resetFileInput() {
    fileInput.value = null;
    nameDisplay.innerHTML = ""; // Change innerText to innerHTML
   currentFileDuration = null;
   currentWordEnd = null;
   currentFile = null;
   previousFile = null;
  }

  function resetFolderInput() {
    folderInput.value = null;
    nameDisplay.innerHTML = ""; // Change innerText to innerHTML
    currentFileDuration = null;
    currentWordEnd = null;
    currentFile = null;
    previousFile = null;
  }

  function displayFileNames(fileNames, displayElement) {
    displayElement.innerHTML = fileNames
      .map(
        (name) =>
          `<div class="file-container"><h4 class="file-name">${name}</h4><div id="${name}Status" class="message" style="display:none;">...(waiting)</div><div id="${name}loaderback" class="loading-bar-background"><div id="${name}loader" class="loading-bar"></div></div></div>`
      )
      .join("\n");
  }

  // Add event listener to the download button
  downloadButton.addEventListener("click", function () {
    const fileContainers = document.querySelectorAll(".file-container");
    fileContainers.forEach((container) => {
      const fileName = container.querySelector(".file-name").textContent;
      document.getElementById(`${fileName}Status`).style.display = "block"; // Show the waiting message
    });
  });

  function showHeaders() {
    fileHeader.style.display = "flex";
    stepOneDescription.style.display = "none";
  }

  function hideHeaders() {
    fileHeader.style.display = "none";
    stepOneDescription.style.display = "block";
  }

  function showButtons() {
    downloadButton.style.display = "inline-block";
    resetButton.style.display = "inline-block";
    orText.style.display = "none";
  }

  function hideButtons() {
    downloadButton.style.display = "none";
    resetButton.style.display = "none";
    orText.style.display = "block";
  }

  function hideLabels() {
    fileLabel.style.display = "none";
    folderLabel.style.display = "none";
  }

  function showLabels() {
    fileLabel.style.display = "block";
    folderLabel.style.display = "block";
  }

  resetButton.addEventListener("click", function () {
    resetFileInput();
    resetFolderInput();
    hideButtons();
    showLabels();
    hideHeaders();
    disableGenerateButton();
  });

  socket.on("current_file", function (data) {
    const filename = data.message;
    const fileNameWithoutExtension = filename.split(".")[0];
    const statusElement = document.getElementById(
      `${fileNameWithoutExtension}Status`
    );

    console.log("Transcribing:", fileNameWithoutExtension);

    // Update previousFile to the currentFile before updating currentFile
    previousFile = currentFile;
    // Update currentFile to the new file received
    currentFile = fileNameWithoutExtension;

    if (statusElement) {
      statusElement.style.display = "none"; // Hide the message
      document.getElementById(`${fileNameWithoutExtension}loaderback`).style.display = "flex"; // Show the loading bar background
      console.log("Loading bar shown");
    }

    console.log(currentFile, previousFile);
    // If previousFile is not null, update its status to 100%
    if (previousFile !== null) {
      const previousStatusElement = document.getElementById(
        `${previousFile}Status`
      );
      if (previousStatusElement) {
        document.getElementById(`${previousFile}loaderback`).style.display =
          "none"; // Hide the loading bar background
        previousStatusElement.style.display = "block"; // Show the message
        previousStatusElement.innerText = "Complete";
      }
    }
  });


  socket.on("audio_duration", function (data) {
    console.log("Received audio_duration:", data);

    // Assign the duration value to the currentFileDuration variable
    currentFileDuration = data.duration;
    console.log("duration set:", currentFileDuration);
  });

  socket.on("word_end", function (data) {
    console.log("Current Word End:", data);
    currentWordEnd = data.word_end;
    console.log("current word end set", currentWordEnd);

    const loaderElement = document.getElementById(`${currentFile}loader`);
    document.getElementById(`${currentFile}loader`).style.display = "flex"; // Show the loading bar
    // Calculate completion percentage
    const completionPercentage = (
      (currentWordEnd / currentFileDuration) *
      100
    ).toFixed(2);

    // Update the progress bar width
    if (loaderElement) {
      loaderElement.style.width = completionPercentage + "%";
    }
  });

  // Event listener for "transcription_complete"
  socket.on("transcription_complete", function (data) {
    console.log("Transcription Completed:", data);
    const statusElement = document.getElementById(`${currentFile}Status`);
    if (statusElement) {
      document.getElementById(`${currentFile}loaderback`).style.display =
        "none"; // Hide the loading bar background
      statusElement.style.display = "block";
      statusElement.innerText = "Complete";
      enableGenerateButton();
    }
  });

  // Example of listening for transcription error event
  socket.on("transcription_error", function (data) {
    console.error("Transcription Error:", data.error);
    // Handle error and update UI accordingly
  });

  // AJAX form submission
  document
    .getElementById("transcription")
    .addEventListener("submit", function (event) {
      event.preventDefault();

      var formElement = event.target;
      var formData = new FormData(formElement);

      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/transcribe", true);
      xhr.onload = function () {
        if (xhr.status === 200) {
          var response = JSON.parse(xhr.responseText);
        } else {
          console.error(
            "Transcription request failed with status " + xhr.status
          );
        }
      };
      xhr.send(formData);
    });
});
