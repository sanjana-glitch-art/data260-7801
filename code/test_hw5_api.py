from __future__ import annotations

import sys
import time
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8601"

LOGIN_EMAIL = "sanjana@example.edu"
LOGIN_PASSWORD = "Data260!7801"

TIMEOUT_SECONDS = 20


passed_count = 0
failed_count = 0


def record_result(
    name: str,
    passed: bool,
    details: str,
) -> None:
    """Print and count one test result."""

    global passed_count
    global failed_count

    if passed:
        passed_count += 1
        status_text = "PASS"
    else:
        failed_count += 1
        status_text = "FAIL"

    print(
        f"{status_text}: {name} - {details}"
    )


def require_status(
    name: str,
    response: requests.Response,
    expected_status: int,
) -> bool:
    """Check an HTTP response status."""

    passed = (
        response.status_code
        == expected_status
    )

    if passed:
        details = (
            f"HTTP {response.status_code}"
        )
    else:
        details = (
            f"expected HTTP {expected_status}, "
            f"received HTTP {response.status_code}; "
            f"response={response.text[:500]}"
        )

    record_result(
        name,
        passed,
        details,
    )

    return passed


def response_json(
    response: requests.Response,
) -> dict[str, Any]:
    """Return a JSON response as a dictionary."""

    data = response.json()

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Expected a JSON object."
        )

    return data


def main() -> None:
    """Run authenticated CRUD tests against FastAPI."""

    session = requests.Session()

    unique_suffix = str(
        int(
            time.time()
        )
    )

    sponsor_id: int | None = None
    trial_id: int | None = None

    print(
        "=== Homework 5 API Smoke Test ==="
    )

    print(
        "Base URL:",
        BASE_URL,
    )

    try:
        health_response = session.get(
            f"{BASE_URL}/health",
            timeout=TIMEOUT_SECONDS,
        )

        if not require_status(
            "Health endpoint",
            health_response,
            200,
        ):
            raise RuntimeError(
                "FastAPI health check failed."
            )

        health_data = response_json(
            health_response
        )

        record_result(
            "Health payload",
            (
                health_data.get("status")
                == "ok"
            ),
            str(health_data),
        )

        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD,
            },
            timeout=TIMEOUT_SECONDS,
        )

        if not require_status(
            "User login",
            login_response,
            200,
        ):
            raise RuntimeError(
                "Login failed."
            )

        record_result(
            "Session cookie created",
            (
                "s7801_session"
                in session.cookies
            ),
            (
                "HTTP-only session token "
                "received by client"
            ),
        )

        me_response = session.get(
            f"{BASE_URL}/api/auth/me",
            timeout=TIMEOUT_SECONDS,
        )

        require_status(
            "Current-user endpoint",
            me_response,
            200,
        )

        sponsor_payload = {
            "sponsor_name": (
                f"HW5 Test Sponsor "
                f"{unique_suffix}"
            ),
            "headquarters": (
                "San Jose, CA"
            ),
            "contact_email": (
                f"hw5-{unique_suffix}"
                "@example.edu"
            ),
        }

        create_sponsor_response = (
            session.post(
                f"{BASE_URL}/api/sponsors",
                json=sponsor_payload,
                timeout=TIMEOUT_SECONDS,
            )
        )

        if not require_status(
            "Create sponsor",
            create_sponsor_response,
            201,
        ):
            raise RuntimeError(
                "Sponsor creation failed."
            )

        created_sponsor = response_json(
            create_sponsor_response
        )

        sponsor_id = int(
            created_sponsor["id"]
        )

        list_sponsors_response = (
            session.get(
                f"{BASE_URL}/api/sponsors",
                params={
                    "page": 1,
                    "page_size": 20,
                    "search": "HW5 Test Sponsor",
                },
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "List sponsors",
            list_sponsors_response,
            200,
        )

        sponsor_list = response_json(
            list_sponsors_response
        )

        record_result(
            "Sponsor pagination",
            (
                sponsor_list.get("page")
                == 1
                and sponsor_list.get(
                    "page_size"
                )
                == 20
                and isinstance(
                    sponsor_list.get("items"),
                    list,
                )
            ),
            (
                f"total="
                f"{sponsor_list.get('total')}"
            ),
        )

        get_sponsor_response = (
            session.get(
                (
                    f"{BASE_URL}"
                    f"/api/sponsors/"
                    f"{sponsor_id}"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Get sponsor",
            get_sponsor_response,
            200,
        )

        updated_sponsor_payload = {
            **sponsor_payload,
            "headquarters": (
                "Santa Clara, CA"
            ),
        }

        update_sponsor_response = (
            session.put(
                (
                    f"{BASE_URL}"
                    f"/api/sponsors/"
                    f"{sponsor_id}"
                ),
                json=updated_sponsor_payload,
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Update sponsor",
            update_sponsor_response,
            200,
        )

        trial_payload = {
            "trial_title": (
                "HW5 API Smoke Test Trial"
            ),
            "trial_code": (
                f"S7801-HW5-"
                f"{unique_suffix}"
            ),
            "enrollment_target": 125,
            "sponsor_id": sponsor_id,
            "submitter_email": (
                "sanjana@example.edu"
            ),
            "trial_description": (
                "This temporary clinical trial "
                "verifies the Homework 5 API."
            ),
            "trial_phase": "Phase II",
        }

        create_trial_response = (
            session.post(
                f"{BASE_URL}/api/trials",
                json=trial_payload,
                timeout=TIMEOUT_SECONDS,
            )
        )

        if not require_status(
            "Create clinical trial",
            create_trial_response,
            201,
        ):
            raise RuntimeError(
                "Clinical-trial creation failed."
            )

        created_trial = response_json(
            create_trial_response
        )

        trial_id = int(
            created_trial["id"]
        )

        list_trials_response = (
            session.get(
                f"{BASE_URL}/api/trials",
                params={
                    "page": 1,
                    "page_size": 20,
                    "search": (
                        trial_payload[
                            "trial_code"
                        ]
                    ),
                },
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "List clinical trials",
            list_trials_response,
            200,
        )

        trial_list = response_json(
            list_trials_response
        )

        record_result(
            "Clinical-trial pagination",
            (
                trial_list.get("total")
                == 1
                and len(
                    trial_list.get(
                        "items",
                        [],
                    )
                )
                == 1
            ),
            (
                f"total="
                f"{trial_list.get('total')}"
            ),
        )

        get_trial_response = (
            session.get(
                (
                    f"{BASE_URL}"
                    f"/api/trials/"
                    f"{trial_id}"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Get clinical trial",
            get_trial_response,
            200,
        )

        relationship_response = (
            session.get(
                (
                    f"{BASE_URL}"
                    f"/api/sponsors/"
                    f"{sponsor_id}"
                    f"/trials"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Sponsor-to-trials relationship",
            relationship_response,
            200,
        )

        relationship_data = response_json(
            relationship_response
        )

        record_result(
            "Relationship contains trial",
            any(
                item.get("id")
                == trial_id
                for item in relationship_data.get(
                    "items",
                    [],
                )
            ),
            (
                f"relationship total="
                f"{relationship_data.get('total')}"
            ),
        )

        updated_trial_payload = {
            **trial_payload,
            "trial_title": (
                "Updated HW5 API Smoke Test Trial"
            ),
            "enrollment_target": 175,
            "trial_phase": "Phase III",
        }

        update_trial_response = (
            session.put(
                (
                    f"{BASE_URL}"
                    f"/api/trials/"
                    f"{trial_id}"
                ),
                json=updated_trial_payload,
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Update clinical trial",
            update_trial_response,
            200,
        )

        blocked_delete_response = (
            session.delete(
                (
                    f"{BASE_URL}"
                    f"/api/sponsors/"
                    f"{sponsor_id}"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        require_status(
            "Block sponsor deletion with trials",
            blocked_delete_response,
            409,
        )

        delete_trial_response = (
            session.delete(
                (
                    f"{BASE_URL}"
                    f"/api/trials/"
                    f"{trial_id}"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        if require_status(
            "Delete clinical trial",
            delete_trial_response,
            204,
        ):
            trial_id = None

        delete_sponsor_response = (
            session.delete(
                (
                    f"{BASE_URL}"
                    f"/api/sponsors/"
                    f"{sponsor_id}"
                ),
                timeout=TIMEOUT_SECONDS,
            )
        )

        if require_status(
            "Delete sponsor",
            delete_sponsor_response,
            204,
        ):
            sponsor_id = None

        logout_response = session.post(
            f"{BASE_URL}/api/auth/logout",
            timeout=TIMEOUT_SECONDS,
        )

        require_status(
            "User logout",
            logout_response,
            200,
        )

    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
        KeyError,
    ) as error:
        record_result(
            "Unexpected smoke-test exception",
            False,
            (
                f"{type(error).__name__}: "
                f"{error}"
            ),
        )

    finally:
        # Best-effort cleanup if a prior assertion failed.
        if trial_id is not None:
            try:
                session.delete(
                    (
                        f"{BASE_URL}"
                        f"/api/trials/"
                        f"{trial_id}"
                    ),
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException:
                pass

        if sponsor_id is not None:
            try:
                session.delete(
                    (
                        f"{BASE_URL}"
                        f"/api/sponsors/"
                        f"{sponsor_id}"
                    ),
                    timeout=TIMEOUT_SECONDS,
                )
            except requests.RequestException:
                pass

    total_count = (
        passed_count
        + failed_count
    )

    print(
        "\n=== Final Summary ==="
    )

    print(
        f"{passed_count}/"
        f"{total_count} tests passed."
    )

    if failed_count:
        print(
            f"{failed_count} test(s) failed."
        )

        raise SystemExit(1)

    print(
        "All API smoke tests passed."
    )


if __name__ == "__main__":
    main()