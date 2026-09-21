from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPORT_DIRECTORY = (
    PROJECT_ROOT
    / "reports"
    / "hw03"
)

CORPUS_DIRECTORY = (
    REPORT_DIRECTORY
    / "corpus"
)

MANIFEST_PATH = (
    REPORT_DIRECTORY
    / "CORPUS_MANIFEST.json"
)

SOURCES_PATH = (
    REPORT_DIRECTORY
    / "SOURCES.md"
)


SOURCES = [
    {
        "name": "fda_informed_consent",
        "title": (
            "FDA Informed Consent Guidance for IRBs, "
            "Clinical Investigators, and Sponsors"
        ),
        "url": (
            "https://www.fda.gov/media/88915/download"
        )
    },
    {
        "name": "fda_risk_based_monitoring",
        "title": (
            "FDA Oversight of Clinical Investigations: "
            "A Risk-Based Approach to Monitoring"
        ),
        "url": (
            "https://www.fda.gov/media/116754/download"
        )
    },
    {
        "name": "fda_clinical_trial_endpoints",
        "title": (
            "FDA Multiple Endpoints in Clinical Trials Guidance"
        ),
        "url": (
            "https://www.fda.gov/media/162416/download"
        )
    }
]


def download_file(
    url: str,
    destination: Path
) -> None:
    """Download a public source document."""

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "DATA260-HW3-Sanjana-Thummalapalli"
            )
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=120
    ) as response:
        destination.write_bytes(
            response.read()
        )


def extract_pdf_text(
    pdf_path: Path
) -> str:
    """Extract readable text from every PDF page."""

    reader = PdfReader(pdf_path)

    sections: list[str] = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        page_text = (
            page.extract_text()
            or ""
        ).strip()

        if page_text:
            sections.append(
                "\n".join(
                    [
                        (
                            f"--- Page "
                            f"{page_number} ---"
                        ),
                        page_text
                    ]
                )
            )

    return "\n\n".join(sections)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hash of a file."""

    digest = hashlib.sha256()

    with path.open("rb") as source_file:
        for block in iter(
            lambda: source_file.read(65536),
            b""
        ):
            digest.update(block)

    return digest.hexdigest()


def main() -> None:
    CORPUS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    manifest_files: list[
        dict[str, object]
    ] = []

    source_sections = [
        "# Homework 3 Corpus Sources",
        "",
        (
            "Domain: Clinical Trial Listings "
            "(DOMAIN_ID 1)"
        ),
        "",
        f"Access date: {date.today().isoformat()}",
        ""
    ]

    total_text_bytes = 0

    for source in SOURCES:
        name = str(source["name"])
        title = str(source["title"])
        url = str(source["url"])

        pdf_path = (
            CORPUS_DIRECTORY
            / f"{name}.pdf"
        )

        text_path = (
            CORPUS_DIRECTORY
            / f"{name}.txt"
        )

        print(f"Downloading: {title}")

        download_file(
            url,
            pdf_path
        )

        print(f"Extracting: {pdf_path.name}")

        extracted_text = extract_pdf_text(
            pdf_path
        )

        text_path.write_text(
            extracted_text,
            encoding="utf-8"
        )

        text_size = text_path.stat().st_size
        total_text_bytes += text_size

        manifest_files.append({
            "filename": text_path.name,
            "relativePath": str(
                text_path.relative_to(
                    PROJECT_ROOT
                )
            ).replace("\\", "/"),
            "sourceTitle": title,
            "sourceUrl": url,
            "byteSize": text_size,
            "sha256": sha256_file(
                text_path
            )
        })

        source_sections.extend([
            f"## {title}",
            "",
            f"- URL: {url}",
            (
                "- Accessed: "
                f"{date.today().isoformat()}"
            ),
            (
                "- Local snapshot: "
                f"`reports/hw03/corpus/"
                f"{text_path.name}`"
            ),
            ""
        ])

        print(
            f"Created {text_path.name}: "
            f"{text_size:,} bytes"
        )

    manifest = {
        "domainId": 1,
        "domain": "Clinical Trial Listings",
        "generatedAt": (
            date.today().isoformat()
        ),
        "minimumRequiredBytes": 200000,
        "totalTextBytes": total_text_bytes,
        "meetsMinimumSize": (
            total_text_bytes >= 200000
        ),
        "files": manifest_files
    }

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2
        ),
        encoding="utf-8"
    )

    SOURCES_PATH.write_text(
        "\n".join(source_sections),
        encoding="utf-8"
    )

    print()
    print(
        "Total extracted-text size:",
        f"{total_text_bytes:,} bytes"
    )

    print(
        "Meets 200 KB requirement:",
        total_text_bytes >= 200000
    )

    print()
    print("Created:")
    print(MANIFEST_PATH)
    print(SOURCES_PATH)

    if total_text_bytes < 200000:
        raise RuntimeError(
            "The extracted corpus is below "
            "the required 200,000 bytes."
        )


if __name__ == "__main__":
    main()