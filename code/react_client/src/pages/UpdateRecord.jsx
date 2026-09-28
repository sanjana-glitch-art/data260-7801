import {
    useEffect,
    useState
} from "react";

import {
    Link,
    Navigate,
    useNavigate,
    useParams
} from "react-router-dom";

import {
    getTrial
} from "../api";


function UpdateRecord({
    user,
    onUpdate
}) {
    const {
        id
    } = useParams();

    const navigate = useNavigate();

    const [
        trialTitle,
        setTrialTitle
    ] = useState("");

    const [
        sponsorName,
        setSponsorName
    ] = useState("");

    const [
        loading,
        setLoading
    ] = useState(Boolean(id));

    const [
        submitting,
        setSubmitting
    ] = useState(false);

    const [
        error,
        setError
    ] = useState("");

    useEffect(
        () => {
            let cancelled = false;

            if (!user || !id) {
                return () => {
                    cancelled = true;
                };
            }

            const loadRecord = async () => {
                setLoading(true);
                setError("");

                try {
                    const record =
                        await getTrial(id);

                    if (!cancelled) {
                        setTrialTitle(
                            record.trial_title
                        );

                        setSponsorName(
                            record.sponsor_name
                        );
                    }
                } catch (requestError) {
                    if (!cancelled) {
                        setError(
                            requestError.message
                            || (
                                "Unable to load " +
                                "the record."
                            )
                        );
                    }
                } finally {
                    if (!cancelled) {
                        setLoading(false);
                    }
                }
            };

            loadRecord();

            return () => {
                cancelled = true;
            };
        },
        [
            id,
            user
        ]
    );

    if (!user) {
        return (
            <Navigate
                to="/login"
                replace
            />
        );
    }

    if (!id) {
        return (
            <main className="page centered-page">
                <section className="card form-card">
                    <h1>
                        Select a Clinical Trial
                    </h1>

                    <p className="muted">
                        Select Update beside a
                        record on the home page.
                    </p>

                    <Link
                        className={
                            "primary-button " +
                            "link-button"
                        }
                        to="/"
                    >
                        Return home
                    </Link>
                </section>
            </main>
        );
    }

    const handleSubmit = async (
        event
    ) => {
        event.preventDefault();

        setError("");
        setSubmitting(true);

        try {
            await onUpdate(
                id,
                {
                    trial_title:
                        trialTitle.trim(),

                    sponsor_name:
                        sponsorName.trim()
                }
            );

            navigate(
                "/",
                {
                    replace: true
                }
            );
        } catch (requestError) {
            setError(
                requestError.message
                || "Unable to update record."
            );
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <main className="page centered-page">
            <section className="card form-card">
                <p className="eyebrow">
                    Update record {id}
                </p>

                <h1>
                    Update Clinical Trial
                </h1>

                {loading && (
                    <p>
                        Loading record...
                    </p>
                )}

                {error && (
                    <div
                        className="alert error"
                        role="alert"
                    >
                        {error}
                    </div>
                )}

                {!loading && (
                    <form
                        className="form-grid"
                        onSubmit={handleSubmit}
                    >
                        <label htmlFor="trialTitle">
                            Trial title
                        </label>

                        <input
                            id="trialTitle"
                            value={trialTitle}
                            onChange={(event) => {
                                setTrialTitle(
                                    event.target.value
                                );
                            }}
                            required
                            autoFocus
                        />

                        <label htmlFor="sponsorName">
                            Sponsor name
                        </label>

                        <input
                            id="sponsorName"
                            value={sponsorName}
                            onChange={(event) => {
                                setSponsorName(
                                    event.target.value
                                );
                            }}
                            required
                        />

                        <div className="form-actions">
                            <button
                                className="primary-button"
                                type="submit"
                                disabled={submitting}
                            >
                                {submitting
                                    ? "Updating..."
                                    : (
                                        "Update Clinical " +
                                        "Trial"
                                    )}
                            </button>

                            <Link
                                className={
                                    "secondary-button " +
                                    "link-button"
                                }
                                to="/"
                            >
                                Cancel
                            </Link>
                        </div>
                    </form>
                )}
            </section>
        </main>
    );
}


export default UpdateRecord;