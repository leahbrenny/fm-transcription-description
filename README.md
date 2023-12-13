Clone down the repo
Make sure you have [Python](https://www.python.org/downloads/) installed (at least version 3)

`pip install -r requirements.txt`

First, create an [OpenAI account](https://platform.openai.com/signup) or [sign in](https://platform.openai.com/login). Next, navigate to the [API key page](https://platform.openai.com/account/api-keys) and "Create new secret key", optionally naming the key. Make sure to save this somewhere safe and do not share it with anyone.

Create a .env file in the root that contains your OpenAI API Key `OPENAI_API_KEY=yourkeyhere`

Run application using `python app.py`
this might also be `python3 app.py` depending on the install