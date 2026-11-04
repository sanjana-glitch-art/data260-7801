import {
    useState
} from "react";


const DEFAULT_PRICING_URL = (
    "https://citibikenyc.com/pricing"
);


const readableError = (
    payload,
    response
) => {
    const detail = payload?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (
        detail
        && typeof detail === "object"
    ) {
        return (
            detail.message
            || detail.error
            || JSON.stringify(detail)
        );
    }

    return (
        `Request failed with status `
        + `${response.status}.`
    );
};


function BikeShare() {
    const [
        csvFile,
        setCsvFile
    ] = useState(null);

    const [
        pricingUrl,
        setPricingUrl
    ] = useState(
        DEFAULT_PRICING_URL
    );

    const [
        scenarioLabel,
        setScenarioLabel
    ] = useState(
        "bikeshare_ui_run"
    );

    const [
        loading,
        setLoading
    ] = useState(false);

    const [
        error,
        setError
    ] = useState("");

    const [
        result,
        setResult
    ] = useState(null);


    const handleSubmit = async (
        event
    ) => {
        event.preventDefault();

        if (!csvFile) {
            setError(
                "Choose a Bike Share CSV file."
            );

            return;
        }

        if (!pricingUrl.trim()) {
            setError(
                "Enter the official pricing URL."
            );

            return;
        }

        setLoading(true);
        setError("");
        setResult(null);

        const formData = new FormData();

        formData.append(
            "csv_file",
            csvFile
        );

        formData.append(
            "pricing_url",
            pricingUrl.trim()
        );

        formData.append(
            "scenario_label",
            scenarioLabel.trim()
            || "bikeshare_ui_run"
        );

        try {
            const response = await fetch(
                "/api/bikeshare/analyze",
                {
                    method: "POST",
                    body: formData
                }
            );

            let payload = null;

            try {
                payload = await response.json();
            } catch {
                payload = null;
            }

            if (!response.ok) {
                throw new Error(
                    readableError(
                        payload,
                        response
                    )
                );
            }

            setResult(
                payload.data
            );
        } catch (requestError) {
            setError(
                requestError.message
                || "Bike Share analysis failed."
            );
        } finally {
            setLoading(false);
        }
    };


    return (
        <main className="bikeshare-page">
            <section className="page-heading">
                <p className="eyebrow">
                    DATA-260 Homework 7 · Part 4
                </p>

                <h1>
                    Bike Share Cost Advisor
                </h1>

                <p>
                    Compare monthly membership with
                    pay-per-use using an uploaded trip CSV
                    and official pricing-policy evidence.
                </p>
            </section>

            <section className="panel bikeshare-form-panel">
                <h2>
                    Run an analysis
                </h2>

                <form
                    className="bikeshare-form"
                    onSubmit={handleSubmit}
                >
                    <label>
                        <span>
                            Trip CSV
                        </span>

                        <input
                            type="file"
                            accept=".csv,text/csv"
                            onChange={(event) => {
                                setCsvFile(
                                    event.target.files?.[0]
                                    || null
                                );
                            }}
                            required
                        />
                    </label>

                    <label>
                        <span>
                            Official pricing URL
                        </span>

                        <input
                            type="url"
                            value={pricingUrl}
                            onChange={(event) => {
                                setPricingUrl(
                                    event.target.value
                                );
                            }}
                            required
                        />
                    </label>

                    <label>
                        <span>
                            Scenario label
                        </span>

                        <input
                            type="text"
                            value={scenarioLabel}
                            onChange={(event) => {
                                setScenarioLabel(
                                    event.target.value
                                );
                            }}
                            maxLength="80"
                        />
                    </label>

                    <button
                        type="submit"
                        disabled={loading}
                    >
                        {
                            loading
                                ? "Running agent..."
                                : "Run Bike Share Agent"
                        }
                    </button>
                </form>

                {
                    csvFile
                    && (
                        <p className="selected-file">
                            Selected file:
                            {" "}
                            <strong>
                                {csvFile.name}
                            </strong>
                        </p>
                    )
                }

                {
                    error
                    && (
                        <div
                            className="message error-message"
                            role="alert"
                        >
                            {error}
                        </div>
                    )
                }
            </section>

            {
                result
                ? (
                    <>
                        <section className="metrics-strip">
                            <article>
                                <span>
                                    Steps
                                </span>

                                <strong>
                                    {result.step_count}
                                </strong>
                            </article>

                            <article>
                                <span>
                                    Total time
                                </span>

                                <strong>
                                    {
                                        Number(
                                            result.total_time_ms
                                        ).toFixed(2)
                                    }
                                    {" "}
                                    ms
                                </strong>
                            </article>

                            <article>
                                <span>
                                    Stop reason
                                </span>

                                <strong>
                                    {result.stop_reason}
                                </strong>
                            </article>

                            <article>
                                <span>
                                    Dataset rows
                                </span>

                                <strong>
                                    {
                                        result
                                            .dataset_row_count
                                    }
                                </strong>
                            </article>
                        </section>

                        <section className="panel decision-panel">
                            <p className="eyebrow">
                                Final decision
                            </p>

                            <h2>
                                {result.decision}
                            </h2>

                            <p>
                                {result.justification}
                            </p>
                        </section>

                        <section className="cost-grid">
                            <article className="panel">
                                <span>
                                    Pay per use
                                </span>

                                <strong>
                                    $
                                    {
                                        Number(
                                            result
                                                .pay_per_use_cost
                                        ).toFixed(2)
                                    }
                                </strong>
                            </article>

                            <article className="panel">
                                <span>
                                    Monthly membership
                                </span>

                                <strong>
                                    $
                                    {
                                        Number(
                                            result
                                                .membership_cost
                                        ).toFixed(2)
                                    }
                                </strong>
                            </article>

                            <article className="panel">
                                <span>
                                    Break-even rides
                                </span>

                                <strong>
                                    {
                                        Number(
                                            result
                                                .break_even_rides
                                        ).toFixed(2)
                                    }
                                </strong>
                            </article>

                            <article className="panel">
                                <span>
                                    Actual rides
                                </span>

                                <strong>
                                    {result.ride_count}
                                </strong>
                            </article>
                        </section>

                        <section className="panel">
                            <h2>
                                Weekly usage and spend
                            </h2>

                            <div className="table-scroll">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>
                                                Week
                                            </th>

                                            <th>
                                                Rides
                                            </th>

                                            <th>
                                                Average duration
                                            </th>

                                            <th>
                                                Pay spend
                                            </th>

                                            <th>
                                                Membership spend
                                            </th>
                                        </tr>
                                    </thead>

                                    <tbody>
                                        {
                                            result.weekly_rows.map(
                                                (row) => (
                                                    <tr
                                                        key={
                                                            row
                                                                .week_number
                                                        }
                                                    >
                                                        <td>
                                                            {
                                                                row
                                                                    .week_number
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                row
                                                                    .ride_count
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                Number(
                                                                    row
                                                                        .average_duration_minutes
                                                                ).toFixed(2)
                                                            }
                                                            {" "}
                                                            min
                                                        </td>

                                                        <td>
                                                            {
                                                                row
                                                                    .estimated_pay_spend
                                                                !== undefined
                                                                    ? (
                                                                        `$${Number(
                                                                            row
                                                                                .estimated_pay_spend
                                                                        ).toFixed(2)}`
                                                                    )
                                                                    : "See total"
                                                            }
                                                        </td>

                                                        <td>
                                                            {
                                                                row
                                                                    .estimated_membership_spend
                                                                !== undefined
                                                                    ? (
                                                                        `$${Number(
                                                                            row
                                                                                .estimated_membership_spend
                                                                        ).toFixed(2)}`
                                                                    )
                                                                    : "See total"
                                                            }
                                                        </td>
                                                    </tr>
                                                )
                                            )
                                        }
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section className="panel">
                            <h2>
                                Tool-call timeline
                            </h2>

                            <ol className="timeline">
                                {
                                    result.timeline.map(
                                        (
                                            event,
                                            index
                                        ) => (
                                            <li
                                                key={
                                                    `${event.tool}-${index}`
                                                }
                                            >
                                                <div className="timeline-title">
                                                    <strong>
                                                        Step
                                                        {" "}
                                                        {event.step}
                                                        :
                                                        {" "}
                                                        {event.tool}
                                                    </strong>
                                                </div>

                                                <details>
                                                    <summary>
                                                        Inputs and observation
                                                    </summary>

                                                    <pre>
                                                        {
                                                            JSON.stringify(
                                                                {
                                                                    inputs:
                                                                        event.inputs,
                                                                    observation:
                                                                        event.observation
                                                                },
                                                                null,
                                                                2
                                                            )
                                                        }
                                                    </pre>
                                                </details>
                                            </li>
                                        )
                                    )
                                }
                            </ol>
                        </section>

                        <section className="panel">
                            <h2>
                                Pricing citations
                            </h2>

                            <p>
                                Source:
                                {" "}
                                <a
                                    href={
                                        result.policy_source
                                    }
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    {
                                        result
                                            .policy_source
                                    }
                                </a>
                            </p>

                            <p>
                                Captured:
                                {" "}
                                {
                                    result.snapshot
                                        ?.accessed_at
                                }
                            </p>

                            <p className="hash-value">
                                SHA-256:
                                {" "}
                                {
                                    result.snapshot
                                        ?.sha256
                                }
                            </p>

                            <ul className="citation-list">
                                {
                                    result.citations.map(
                                        (
                                            citation,
                                            index
                                        ) => (
                                            <li
                                                key={
                                                    `${citation.source}-${index}`
                                                }
                                            >
                                                <blockquote>
                                                    {
                                                        citation.text
                                                    }
                                                </blockquote>

                                                <small>
                                                    Score:
                                                    {" "}
                                                    {
                                                        citation.score
                                                    }
                                                </small>
                                            </li>
                                        )
                                    )
                                }
                            </ul>
                        </section>

                        <section className="panel">
                            <h2>
                                Assumptions and caveats
                            </h2>

                            <ul>
                                {
                                    result.assumptions.map(
                                        (
                                            assumption,
                                            index
                                        ) => (
                                            <li
                                                key={
                                                    `${assumption}-${index}`
                                                }
                                            >
                                                {assumption}
                                            </li>
                                        )
                                    )
                                }
                            </ul>
                        </section>
                    </>
                )
                : (
                    <section className="panel empty-results">
                        Upload a CSV and run the agent to
                        display the recommendation,
                        timeline, costs, and citations.
                    </section>
                )
            }
        </main>
    );
}


export default BikeShare;