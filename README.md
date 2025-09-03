# PollEv Bot Web Application

A Streamlit-based web application that allows you to run the **PollEverywhere** bot without opening a Python console. Configure credentials through a simple form, start the bot, and watch live logs to confirm that polls are detected and answered.

---

## 📦 Requirements

```bash
python -m pip install -r requirements.txt
```

Python 3.9 or later is recommended.

---

## 🚀 Local Development

```bash
streamlit run streamlit_app.py
```

The app will open in your default browser at <http://localhost:8501>.

---

## 🏗️ Deployment

Because Streamlit is a single-file application, it is straightforward to deploy to popular PaaS providers:

1. **Streamlit Community Cloud** – Create a new app pointing to this repository. Ensure that the `requirements.txt` is present so that `streamlit` and `pollevbot` are installed.
2. **Render.com** – Use the *Web Service* blueprint. Select *Python* as the runtime and provide the command `streamlit run streamlit_app.py --server.port $PORT`.
3. **Fly.io** / **Heroku** – Add a `Procfile` containing:
   ```procfile
   web: streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0
   ```

You may also place the credentials in environment variables and preload them via Streamlit `secrets.toml` for fully automated start-up, but this file is intentionally excluded from version control.

---

## 🔒 Security

The application never stores your credentials server-side. They exist only in memory within the app session while the bot thread is running.

---

## 📝 License

This project inherits the upstream `pollevbot` MIT license.
