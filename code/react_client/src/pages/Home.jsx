import { useEffect, useState } from "react";
import {
    useDispatch,
    useSelector
} from "react-redux";
import {
    Link,
    useNavigate
} from "react-router-dom";

import {
    clearTrialError,
    clearTrialSuccess,
    deleteTrial,
    fetchTrials
} from "../features/trials/trialsSlice";


function Home({
    user
}) {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const [searchInput, setSearchInput] = (
        useState("")
    );

    const [activeSearch, setActiveSearch] = (
        useState("")
    );

    const {
        items,
        total,
        page,
        pageSize,
        totalPages,
        loading,
        mutationLoading,
        error,
        successMessage
    } = useSelector(
        (state) => state.trials
    );


    useEffect(() => {
        dispatch(
            fetchTrials({
                page: 1,
                pageSize: 20,
                search: ""
            })
        );
    }, [dispatch]);


    const handleSearch = (event) => {
        event.preventDefault();

        const cleanedSearch = (
            searchInput.trim()
        );

        setActiveSearch(
            cleanedSearch
        );

        dispatch(
            fetchTrials({
                page: 1,
                pageSize,
                search: cleanedSearch
            })
        );
    };


    const handleClearSearch = () => {
        setSearchInput("");
        setActiveSearch("");

        dispatch(
            fetchTrials({
                page: 1,
                pageSize,
                search: ""
            })
        );
    };


    const changePage = (newPage) => {
        if (
            newPage < 1
            || newPage > totalPages
            || newPage === page
        ) {
            return;
        }

        dispatch(
            fetchTrials({
                page: newPage,
                pageSize,
                search: activeSearch
            })
        );
    };


    const handleDelete = async (
        trial
    ) => {
        const confirmed = window.confirm(
            (
                `Delete "${trial.trial_title}"? `
                + "This action cannot be undone."
            )
        );

        if (!confirmed) {
            return;
        }

        try {
            await dispatch(
                deleteTrial(
                    trial.id
                )
            ).unwrap();

            const shouldMoveBack = (
                items.length === 1
                && page > 1
            );

            const nextPage = (
                shouldMoveBack
                ? page - 1
                : page
            );

            dispatch(
                fetchTrials({
                    page: nextPage,
                    pageSize,
                    search: activeSearch
                })
            );
        } catch {
            // Redux stores and displays the API error.
        }
    };


    if (!user) {
        return (
            <main className="page-shell">
                <section className="panel">
                    <h1>Login required</h1>

                    <p>
                        Log in to view and manage
                        clinical-trial records.
                    </p>

                    <Link
                        className="primary-button"
                        to="/login"
                    >
                        Go to login
                    </Link>
                </section>
            </main>
        );
    }


    return (
        <main className="page-shell">
            <section className="hero-panel">
                <div>
                    <p className="eyebrow">
                        DATA 260 · HOMEWORK 5
                    </p>

                    <h1>
                        Clinical Trial Listings
                    </h1>

                    <p>
                        Records are loaded from MySQL through
                        Redux Toolkit and Axios.
                    </p>
                </div>

                <div className="hero-actions">
                    <span className="record-badge">
                        {total} records
                    </span>

                    <Link
                        className="primary-button"
                        to="/trials/create"
                    >
                        Create trial
                    </Link>
                </div>
            </section>

            <section className="panel">
                <div className="section-heading">
                    <div>
                        <p className="eyebrow">
                            PRIMARY DOMAIN ENTITY
                        </p>

                        <h2>
                            Clinical trials
                        </h2>
                    </div>
                </div>

                {successMessage && (
                    <div
                        className="success-message"
                        role="status"
                    >
                        <span>
                            {successMessage}
                        </span>

                        <button
                            type="button"
                            onClick={() => {
                                dispatch(
                                    clearTrialSuccess()
                                );
                            }}
                        >
                            Dismiss
                        </button>
                    </div>
                )}

                {error && (
                    <div
                        className="error-message"
                        role="alert"
                    >
                        <span>
                            {error}
                        </span>

                        <button
                            type="button"
                            onClick={() => {
                                dispatch(
                                    clearTrialError()
                                );
                            }}
                        >
                            Dismiss
                        </button>
                    </div>
                )}

                <form
                    className="search-row"
                    onSubmit={handleSearch}
                >
                    <label
                        className="visually-hidden"
                        htmlFor="trialSearch"
                    >
                        Search clinical trials
                    </label>

                    <input
                        id="trialSearch"
                        type="search"
                        value={searchInput}
                        placeholder={
                            "Search by title, code, or sponsor"
                        }
                        onChange={(event) => {
                            setSearchInput(
                                event.target.value
                            );
                        }}
                    />

                    <button
                        className="primary-button"
                        type="submit"
                    >
                        Search
                    </button>

                    <button
                        className="secondary-button"
                        type="button"
                        onClick={handleClearSearch}
                    >
                        Clear
                    </button>
                </form>

                {loading && (
                    <div className="state-message">
                        Loading clinical trials...
                    </div>
                )}

                {!loading && items.length === 0 && (
                    <div className="state-message">
                        No clinical-trial records matched
                        the current search.
                    </div>
                )}

                {!loading && items.length > 0 && (
                    <>
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Trial code</th>
                                        <th>Trial title</th>
                                        <th>Sponsor</th>
                                        <th>Phase</th>
                                        <th>
                                            Enrollment target
                                        </th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {items.map((trial) => (
                                        <tr key={trial.id}>
                                            <td>
                                                {trial.id}
                                            </td>

                                            <td>
                                                <code>
                                                    {
                                                        trial.trial_code
                                                    }
                                                </code>
                                            </td>

                                            <td>
                                                {
                                                    trial.trial_title
                                                }
                                            </td>

                                            <td>
                                                {
                                                    trial.sponsor
                                                        ?.sponsor_name
                                                    || trial.sponsor_name
                                                }
                                            </td>

                                            <td>
                                                {
                                                    trial.trial_phase
                                                }
                                            </td>

                                            <td>
                                                {
                                                    trial
                                                        .enrollment_target
                                                }
                                            </td>

                                            <td>
                                                <div
                                                    className={
                                                        "table-actions"
                                                    }
                                                >
                                                    <button
                                                        className={
                                                            "small-button"
                                                        }
                                                        type="button"
                                                        onClick={() => {
                                                            navigate(
                                                                (
                                                                    "/trials/"
                                                                    + `${trial.id}`
                                                                    + "/update"
                                                                )
                                                            );
                                                        }}
                                                    >
                                                        Update
                                                    </button>

                                                    <button
                                                        className={
                                                            "small-button "
                                                            + "danger-button"
                                                        }
                                                        type="button"
                                                        disabled={
                                                            mutationLoading
                                                        }
                                                        onClick={() => {
                                                            handleDelete(
                                                                trial
                                                            );
                                                        }}
                                                    >
                                                        Delete
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="pagination-row">
                            <button
                                className="secondary-button"
                                type="button"
                                disabled={page <= 1}
                                onClick={() => {
                                    changePage(
                                        page - 1
                                    );
                                }}
                            >
                                Previous
                            </button>

                            <span>
                                Page {page} of{" "}
                                {Math.max(
                                    totalPages,
                                    1
                                )}
                            </span>

                            <button
                                className="secondary-button"
                                type="button"
                                disabled={
                                    page >= totalPages
                                }
                                onClick={() => {
                                    changePage(
                                        page + 1
                                    );
                                }}
                            >
                                Next
                            </button>
                        </div>
                    </>
                )}
            </section>
        </main>
    );
}


export default Home;