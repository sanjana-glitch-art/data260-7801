import {
    useState
} from "react";

import {
    Link,
    Navigate,
    useNavigate
} from "react-router-dom";


function CreateRecord({
    user,
    onCreate
}) {
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
        error,
        setError
    ] = useState("");

    const [
        submitting,
        setSubmitting
    ] = useState(false);

    if (!user) {
        return (
            <Navigate
                to="/login"
                replace
            />
        );
    }

    const handleSubmit = async (
        event
    ) => {
        event.preventDefault();

        setError("");
        setSubmitting(true);

        try {
            await onCreate({
                trial_title:
                    trialTitle.trim(),

                sponsor_name:
                    sponsorName.trim()
            });

            navigate(
                "/",
                {
                    replace: true
                }
            );
        } catch (requestError) {
            setError(
                requestError.message
                || "Unable to create record."
            );
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <main className="page centered-page">
            <section className="card form-card">
                <p className="eyebrow">
                    Create record
                </p>

                <h1>
                    Add a Clinical Trial
                </h1>

                {error && (
                    <div
                        className="alert error"
                        role="alert"
                    >
                        {error}
                    </div>
                )}

                <form
                    className="form-grid"
                    onSubmit={handleSubmit}
                >
                    <label htmlFor="trialTitle">
                        Trial title
                    </label>

                    <input
                        id="trialTitle"
                        name="trialTitle"
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
                        name="sponsorName"
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
                                ? "Adding..."
                                : "Add Clinical Trial"}
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
            </section>
        </main>
    );
}


export default CreateRecord;