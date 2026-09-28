import {
    useEffect,
    useState
} from "react";

import {
    Link
} from "react-router-dom";

import {
    getTrials
} from "../api";


function Home({
    user,
    refreshKey
}) {
    const [
        trials,
        setTrials
    ] = useState([]);

    const [
        loading,
        setLoading
    ] = useState(false);

    const [
        error,
        setError
    ] = useState("");

    useEffect(
        () => {
            let cancelled = false;

            if (!user) {
                return () => {
                    cancelled = true;
                };
            }

            const loadTrials = async () => {
                setLoading(true);
                setError("");

                try {
                    const records =
                        await getTrials();

                    if (!cancelled) {
                        setTrials(records);
                    }
                } catch (requestError) {
                    if (!cancelled) {
                        setError(
                            requestError.message
                            || (
                                "Unable to load " +
                                "clinical trials."
                            )
                        );
                    }
                } finally {
                    if (!cancelled) {
                        setLoading(false);
                    }
                }
            };

            loadTrials();

            return () => {
                cancelled = true;
            };
        },
        [
            user,
            refreshKey
        ]
    );

    if (!user) {
        return (
            <main className="page centered-page">
                <section className="card form-card">
                    <p className="eyebrow">
                        DATA 260 · Homework 4
                    </p>

                    <h1>
                        Clinical Trial Listings
                    </h1>

                    <div
                        className="alert warning"
                        role="alert"
                    >
                        Login required
                    </div>

                    <p className="muted">
                        Log in to view and manage
                        clinical-trial records.
                    </p>

                    <Link
                        className={
                            "primary-button " +
                            "link-button"
                        }
                        to="/login"
                    >
                        Go to login
                    </Link>
                </section>
            </main>
        );
    }

    return (
        <main className="page">
            <section className="page-heading">
                <div>
                    <p className="eyebrow">
                        Authenticated records
                    </p>

                    <h1>
                        Clinical Trial Listings
                    </h1>

                    <p className="muted">
                        Welcome, {user.name}.
                    </p>
                </div>

                <Link
                    className={
                        "primary-button " +
                        "link-button"
                    }
                    to="/create"
                >
                    Add Clinical Trial
                </Link>
            </section>

            {loading && (
                <div className="state-card">
                    Loading clinical trials...
                </div>
            )}

            {error && (
                <div
                    className="alert error"
                    role="alert"
                >
                    {error}
                </div>
            )}

            {!loading
                && !error
                && trials.length === 0
                && (
                    <div className="state-card">
                        No clinical trials found.
                    </div>
                )}

            {!loading
                && !error
                && trials.length > 0
                && (
                    <section className="card table-card">
                        <div className="table-scroll">
                            <table>
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>
                                            Trial title
                                        </th>
                                        <th>
                                            Sponsor
                                        </th>
                                        <th>
                                            Actions
                                        </th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {trials.map(
                                        (trial) => (
                                            <tr
                                                key={
                                                    trial.id
                                                }
                                            >
                                                <td>
                                                    {
                                                        trial.id
                                                    }
                                                </td>

                                                <td>
                                                    {
                                                        trial
                                                            .trial_title
                                                    }
                                                </td>

                                                <td>
                                                    {
                                                        trial
                                                            .sponsor_name
                                                    }
                                                </td>

                                                <td>
                                                    <div className="actions">
                                                        <Link
                                                            className={
                                                                "secondary-button " +
                                                                "link-button"
                                                            }
                                                            to={
                                                                `/update/${trial.id}`
                                                            }
                                                        >
                                                            Update
                                                        </Link>

                                                        <Link
                                                            className={
                                                                "danger-button " +
                                                                "link-button"
                                                            }
                                                            to={
                                                                `/delete/${trial.id}`
                                                            }
                                                        >
                                                            Delete
                                                        </Link>
                                                    </div>
                                                </td>
                                            </tr>
                                        )
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}
        </main>
    );
}


export default Home;