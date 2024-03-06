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

  fileInput.addEventListener("change", updateFileDisplay);
  folderInput.addEventListener("change", updateFileDisplay);

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
      enableGenerateButton();
    } else {
      hideButtons();
      showLabels();
      hideHeaders();
      disableGenerateButton();
    }
  }

  function enableGenerateButton() {
    generateButton.disabled = false;
  }

  function disableGenerateButton() {
    generateButton.disabled = true;
  }

  function resetFileInput() {
    fileInput.value = null;
    nameDisplay.innerHTML = ""; // Change innerText to innerHTML
  }

  function resetFolderInput() {
    folderInput.value = null;
    nameDisplay.innerHTML = ""; // Change innerText to innerHTML
  }

  function displayFileNames(fileNames, displayElement) {
    displayElement.innerHTML = fileNames
      .map(
        (name) =>
          `<div class="file-container"><h4 class="file-name">${name}</h4><div id="${name}Message" class="message" style="display:none;">...(waiting)</div><div class="loading-bar-background"><div id="${name}loader" class="loading-bar"></div></div></div>`
      )
      .join("\n");
  }

  // Add event listener to the download button
  downloadButton.addEventListener("click", function () {
    const fileContainers = document.querySelectorAll(".file-container");
    fileContainers.forEach((container) => {
      const fileName = container.querySelector(".file-name").textContent;
      document.getElementById(`${fileName}Message`).style.display = "block"; // Show the waiting message
    });
  });


  function showHeaders() {
    fileHeader.style.display = "block";
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
          const fileContainers = document.querySelectorAll(".file-container");
          fileContainers.forEach((container) => {
            const fileName = container.querySelector(".file-name").textContent;
            document.getElementById(`${fileName}Message`).innerText =
              "Complete";
          });
        } else {
          console.error(
            "Transcription request failed with status " + xhr.status
          );
        }
      };
      xhr.send(formData);
    });
});
