# Frontend Masters Transcriptions & Descriptions Generator

### Utilizing [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) and [C2Translate2](https://github.com/OpenNMT/CTranslate2/)

## Setup Instructions
* Clone down this repo

* Make sure you have [Python](https://www.python.org/downloads/) installed (at least version 3)

* Install the repo dependencies ```pip install -r requirements.txt```

* Create an [OpenAI account](https://platform.openai.com/signup) or [sign in](https://platform.openai.com/login). Next, navigate to the [API key page](https://platform.openai.com/account/api-keys) and "Create new secret key".

* Create a .env file in the root that contains your OpenAI API Key ```OPENAI_API_KEY=yourkeyhere```

* Run application using ```python app.py```

### GPU

GPU execution requires the following NVIDIA libraries to be installed:

* [cuBLAS for CUDA 11](https://developer.nvidia.com/cublas)
* [cuDNN 8 for CUDA 11](https://developer.nvidia.com/cudnn)

There are multiple ways to install these libraries. The recommended way is described in the official NVIDIA documentation, but we also suggest other installation methods below.

<details>
<summary>Other installation methods (click to expand)</summary>

#### Use Docker

The libraries are installed in this official NVIDIA Docker image: `nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`.

#### Install with `pip` (Linux only)

On Linux these libraries can be installed with `pip`. Note that `LD_LIBRARY_PATH` must be set before launching Python.

```bash
pip install nvidia-cublas-cu11 nvidia-cudnn-cu11

export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
```

#### Download the libraries from Purfview's repository (Windows only)

Purfview's [whisper-standalone-win](https://github.com/Purfview/whisper-standalone-win) provides the required NVIDIA libraries for Windows in a [single archive](https://github.com/Purfview/whisper-standalone-win/releases/tag/libs). Decompress the archive and place the libraries in a directory included in the `PATH`.

</details>