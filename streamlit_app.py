import threading
import queue
import time
from typing import Optional, List, Dict, Any

from uuid import uuid4

import streamlit as st
from pollevbot import PollBot


class BotThread(threading.Thread):
    """Thread wrapper around :class:`pollevbot.PollBot` to enable
    concurrent execution while the Streamlit UI remains responsive."""

    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        login_type: str,
        lifetime: float,
        log_queue: "queue.Queue[str]",
    ) -> None:
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self._bot = PollBot(
            user=user,
            password=password,
            host=host,
            login_type=login_type,
            lifetime=lifetime,
        )
        self._log_queue = log_queue

    # ---------------------------------------------------------------------
    # Public helpers
    # ---------------------------------------------------------------------
    def stop(self) -> None:
        """Signal the thread to stop and wait at most five seconds."""
        self._stop_event.set()
        self.join(timeout=5.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        """Push *msg* to the log queue along with a timestamp."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self._log_queue.put(f"[{timestamp}] {msg}")

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 – Simple imperative is fine here.
        self._log("Bot initialising …")
        try:
            self._bot.login()
            token = self._bot.get_firehose_token()
        except Exception as exc:  # pylint: disable=broad-except
            self._log(f"Login failed: {exc}")
            return

        self._log("Login successful. Bot is now watching for polls …")

        while not self._stop_event.is_set() and self._bot.alive():
            self._log("Checking for new polls …")
            poll_id: Optional[str] = self._bot.get_new_poll_id(token)

            if poll_id is None:
                self._log("No new polls detected – sleeping …")
                time.sleep(self._bot.closed_wait)
                continue

            self._log(f"Detected new poll {poll_id}. Waiting to answer …")
            time.sleep(self._bot.open_wait)
            response = self._bot.answer_poll(poll_id)
            self._log(f"Answered poll → {response}")

        self._log("Bot stopped.")


# -------------------------------------------------------------------------
# Global bot-manager stored in Streamlit cache
# -------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def get_bot_manager() -> Dict[str, Dict[str, Any]]:
    """Process-wide storage for running bots keyed by a unique token.

    Each entry is a mapping with keys:
        • "thread": BotThread
        • "log_queue": queue.Queue[str]
    This survives across browser sessions until the Streamlit process is
    restarted.
    """

    return {}


# -------------------------------------------------------------------------
# Streamlit helpers
# -------------------------------------------------------------------------
def init_session_state() -> None:
    """Ensure required keys exist in *st.session_state*."""
    defaults = {
        "bot_thread": None,
        "log_queue": queue.Queue(),
        "logs": [],
        "token": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def flush_logs() -> None:
    """Drain the internal queue into *st.session_state['logs']*."""
    log_queue: "queue.Queue[str]" = st.session_state["log_queue"]
    while not log_queue.empty():
        st.session_state["logs"].append(log_queue.get())


# -------------------------------------------------------------------------
# UI layout
# -------------------------------------------------------------------------

def credentials_form() -> None:
    """Render the credentials form when the bot is not running."""
    st.header("Configure and Start PollEv Bot")
    with st.form(key="credentials_form", clear_on_submit=False):
        user = st.text_input("Username (e.g. netid@cornell.edu)", key="cred_user")
        password = st.text_input("Password", type="password", key="cred_password")
        host = st.text_input("PollEv Host", help="e.g. cs3410", key="cred_host")
        login_type = st.selectbox(
            "Login Type",
            options=["pollev", "uw"],
            help="Choose 'uw' for university SSO or 'pollev' for regular login.",
            key="cred_login_type",
        )
        lifetime = st.number_input(
            "Session Lifetime (seconds)",
            min_value=60,
            value=4800,
            step=60,
            key="cred_lifetime",
        )
        submitted: bool = st.form_submit_button("Start Bot")

    if submitted:
        required: List[str] = [user, password, host]
        if any(not field.strip() for field in required):
            st.error("Please provide username, password, and host.")
            return

        # Instantiate objects and save into session state —––––––––––––––––––––––
        log_q: "queue.Queue[str]" = queue.Queue()
        bot_thread = BotThread(
            user=user,
            password=password,
            host=host,
            login_type=login_type,
            lifetime=float(lifetime),
            log_queue=log_q,
        )
        bot_thread.start()

        # Create unique token and store in global manager
        token = uuid4().hex
        manager = get_bot_manager()
        manager[token] = {"thread": bot_thread, "log_queue": log_q}

        # Persist token in URL and session state
        st.query_params.token = token
        st.session_state["token"] = token
        st.session_state["bot_thread"] = bot_thread
        st.session_state["log_queue"] = log_q

        st.success("Bot started! Scroll down to see real-time logs.")
        st.rerun()


def running_layout() -> None:
    """Render the UI when the bot is currently running."""
    st.header("PollEv Bot – Running")

    if st.button("Stop Bot", type="primary"):
        bot_thread: BotThread = st.session_state["bot_thread"]
        bot_thread.stop()

        # Remove from global manager
        token = st.session_state.get("token")
        if token:
            manager = get_bot_manager()
            manager.pop(token, None)
            # Clear token from URL
            st.query_params = {}

        st.session_state["bot_thread"] = None
        st.session_state["token"] = None
        st.success("Bot stopped.")
        st.rerun()

    # Periodically refresh the logs.
    flush_logs()

    # Display newest entries at the top.
    ordered_logs = list(reversed(st.session_state["logs"]))

    # Use a scrollable text area for better UX.
    st.text_area(
        label="Logs",
        value="\n".join(ordered_logs),
        height=400,
        key="log_area",
    )

    # Auto-refresh every 2 seconds while running.
    time.sleep(2)
    st.rerun()


# -------------------------------------------------------------------------
# Main entry point
# -------------------------------------------------------------------------

def main() -> None:  # noqa: D401 – Simple imperative is fine here.
    st.set_page_config(page_title="PollEv Bot", page_icon="📊", layout="centered")

    # Attempt to restore from token in URL if no bot in session
    if st.session_state.get("bot_thread", None) is None:
        params = st.query_params
        token_param = params.get("token", None) if "token" in params else None

        if token_param:
            manager = get_bot_manager()
            entry = manager.get(token_param)
            if entry and entry["thread"]:
                # Re-attach to running bot
                st.session_state["bot_thread"] = entry["thread"]
                st.session_state["log_queue"] = entry["log_queue"]
                st.session_state["token"] = token_param
                st.session_state["logs"] = []
                running_layout()
        else:
            init_session_state()
            credentials_form()
    else:
        running_layout()


if __name__ == "__main__":
    main()
