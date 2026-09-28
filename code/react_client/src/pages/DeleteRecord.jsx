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


function DeleteRecord({
    user,
    onDelete
}) {
    const {
        id
    } = useParams();

    const navigate = useNavigate();

    const [
        trial,
        setTrial
    ] = useState(null);

    const [
        loading,
        setLoading
    ] = useState(Boolean(id));

    const [
        deleting,
        setDeleting
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
                        setTrial(record);
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
                        Select Delete beside a
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

    const handleDelete = async () => {
        setError("");
        setDeleting(true);

        try {
            await onDelete(id);

            navigate(
                "/",
                {
                    replace: true
                }
            );
        } catch (requestError) {
            setError(
                requestError.message
                || "Unable to delete record."
            );

            setDeleting(false);
        }
    };

    return (
        <main className="page centered-page">
            <section className="card form-card">
                <p className="eyebrow">
                    Delete record {id}
                </p>

                <h1>
                    Delete Clinical Trial
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

                {!loading && trial && (
                    <>
                        <div className="delete-summary">
                            <p>
                                <strong>
                                    Trial:
                                </strong>{" "}
                                {
                                    trial
                                        .trial_title
                                }
                            </p>

                            <p>
                                <strong>
                                    Sponsor:
                                </strong>{" "}
                                {
                                    trial
                                        .sponsor_name
                                }
                            </p>
                        </div>

                        <p>
                            This action cannot be
                            undone.
                        </p>

                        <div className="form-actions">
                            <button
                                className="danger-button"
                                type="button"
                                onClick={
                                    handleDelete
                                }
                                disabled={deleting}
                            >
                                {deleting
                                    ? "Deleting..."
                                    : (
                                        "Delete Clinical " +
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
                    </>
                )}
            </section>
        </main>
    );
}


export default DeleteRecord;