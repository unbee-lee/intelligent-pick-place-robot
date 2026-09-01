"""Browser-observable acceptance test for the controlled UCS composition."""

import socket
import threading
import time
from typing import Iterator
from urllib.request import urlopen

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from ucs_app import create_controlled_app


@pytest.fixture
def controlled_ucs_url() -> Iterator[str]:
    """Run the controlled UCS composition on an available local port."""

    host = "127.0.0.1"
    with socket.socket() as listener:
        listener.bind((host, 0))
        port = listener.getsockname()[1]

    application = create_controlled_app(result_delay_seconds=0.75)
    server = uvicorn.Server(
        uvicorn.Config(application, host=host, port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    for _ in range(100):
        try:
            with urlopen(f"{base_url}/health", timeout=0.1) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("controlled UCS did not start")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)
    if thread.is_alive():
        raise RuntimeError("controlled UCS did not stop")


def test_user_confirms_current_draft_before_controlled_delivery(
    controlled_ucs_url: str,
) -> None:
    """A typed Arrangement request reaches the SC only after confirmation."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(controlled_ucs_url)
        expect(page.get_by_test_id("connection-status")).to_have_text("Connected")

        request_input = page.get_by_test_id("arrangement-request")
        request_input.fill(
            "Put the elephant left, the bear in the centre, and the hippo right."
        )
        page.get_by_role("button", name="Create draft").click()

        current_draft = page.get_by_test_id("current-draft")
        expect(current_draft).to_be_visible()
        expect(page.get_by_test_id("draft-E")).to_contain_text("front left")
        expect(page.get_by_test_id("draft-B")).to_contain_text("front center")
        expect(page.get_by_test_id("draft-H")).to_contain_text("front right")
        expect(page.get_by_role("button", name="Confirm")).to_be_visible()
        expect(page.get_by_role("button", name="Cancel")).to_be_visible()

        expect(page.locator('[data-event-kind="input"]')).to_have_count(1)
        expect(page.locator('[data-event-kind="proposal"]')).to_have_count(1)
        expect(page.locator('[data-event-kind="validation"]')).to_have_count(1)
        expect(page.locator('[data-event-kind="confirmation_required"]')).to_have_count(
            1
        )
        expect(page.locator('[data-event-kind="command_publication"]')).to_have_count(
            0
        )

        page.get_by_role("button", name="Confirm").click()

        expect(page.get_by_test_id("active-command")).to_contain_text("In progress")
        expect(page.get_by_role("button", name="Create draft")).to_be_disabled()
        expect(page.locator('[data-event-kind="confirmation"]')).to_have_count(1)
        expect(page.locator('[data-event-kind="command_publication"]')).to_have_count(
            1
        )
        expect(page.locator('[data-event-kind="progress"]')).to_have_count(1)

        expect(page.get_by_test_id("execution-result")).to_have_text("COMPLETED")
        expect(page.get_by_test_id("verification-result")).to_have_text("NOT_RUN")
        expect(page.get_by_test_id("result-explanation")).to_have_text(
            "Simulation completed the requested arrangement. "
            "Visual verification was not run."
        )
        expect(page.locator('[data-event-kind="result"]')).to_have_count(1)
        expect(page.get_by_test_id("active-command")).to_have_text(
            "No Active command"
        )
        expect(page.get_by_role("button", name="Create draft")).to_be_enabled()

        browser.close()
