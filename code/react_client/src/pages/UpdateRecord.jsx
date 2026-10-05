import {
    useEffect,
    useState
} from "react";

import {
    useDispatch,
    useSelector
} from "react-redux";

import {
    useNavigate,
    useParams
} from "react-router-dom";

import apiClient, {
    getApiError
} from "../api/client";

import TrialForm from "../components/TrialForm";

import {
    clearSelectedTrial,
    clearTrialError,
    clearTrialSuccess,
    fetchTrialById,
    updateTrial
} from "../features/trials/trialsSlice";


const buildInitialForm = (trial) => ({
    trial_title: trial.trial_title || "",
    trial_code: trial.trial_code || "",
    enrollment_target: String(
        trial.enrollment_target ?? 0
    ),
    sponsor_id: String(
        trial.sponsor_id ?? ""
    ),
    submitter_email: trial.submitter_email || "",
    trial_description: (
        trial.trial_description || ""
    ),
    trial_phase: trial.trial_phase || "Phase I"
});


function LoadedUpdateForm({
    trial,
    sponsors
}) {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const {
        mutationLoading,
        error
    } = useSelector(
        (state) => state.trials
    );

    const [formData, setFormData] = useState(
        () => buildInitialForm(trial)
    );

    const handleChange = (event) => {
        const {
            name,
            value
        } = event.target;

        setFormData((current) => ({
            ...current,
            [name]: value
        }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();

        dispatch(clearTrialError());
        dispatch(clearTrialSuccess());

        const payload = {
            trial_title: (
                formData.trial_title.trim()
            ),
            trial_code: (
                formData.trial_code
                    .trim()
                    .toUpperCase()
            ),
            enrollment_target: Number(
                formData.enrollment_target
            ),
            sponsor_id: Number(
                formData.sponsor_id
            ),
            submitter_email: (
                formData.submitter_email.trim()
            ),
            trial_description: (
                formData.trial_description.trim()
            ),
            trial_phase: formData.trial_phase
        };

        try {
            await dispatch(
                updateTrial({
                    trialId: trial.id,
                    trialData: payload
                })
            ).unwrap();

            navigate("/");
        } catch {
            // The rejected thunk stores the API
            // error in the Redux state.
        }
    };

    return (
        <section className="page-card">
            <div className="page-heading">
                <div>
                    <p className="eyebrow">
                        Update record
                    </p>

                    <h1>
                        Update clinical trial
                    </h1>

                    <p>
                        Editing record ID {trial.id}
                    </p>
                </div>
            </div>

            {error && (
                <div
                    className="message error-message"
                    role="alert"
                >
                    {error}
                </div>
            )}

            <TrialForm
                formData={formData}
                sponsors={sponsors}
                loading={mutationLoading}
                submitLabel="Save changes"
                onChange={handleChange}
                onSubmit={handleSubmit}
                onCancel={() => navigate("/")}
            />
        </section>
    );
}


function UpdateRecord({ user }) {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const {
        trialId
    } = useParams();

    const {
        selectedTrial,
        loading,
        error
    } = useSelector(
        (state) => state.trials
    );

    const [sponsors, setSponsors] = useState([]);
    const [sponsorsLoading, setSponsorsLoading] = (
        useState(true)
    );
    const [sponsorsError, setSponsorsError] = (
        useState("")
    );

    const numericTrialId = Number(trialId);

    useEffect(() => {
        let cancelled = false;

        const loadSponsors = async () => {
            try {
                const response = await apiClient.get(
                    "/sponsors",
                    {
                        params: {
                            page: 1,
                            page_size: 100
                        }
                    }
                );

                if (!cancelled) {
                    setSponsors(
                        response.data.items || []
                    );
                }
            } catch (requestError) {
                if (!cancelled) {
                    setSponsorsError(
                        getApiError(requestError)
                    );
                }
            } finally {
                if (!cancelled) {
                    setSponsorsLoading(false);
                }
            }
        };

        loadSponsors();

        return () => {
            cancelled = true;
        };
    }, []);

    useEffect(() => {
        if (
            Number.isInteger(numericTrialId)
            && numericTrialId > 0
        ) {
            dispatch(
                fetchTrialById(numericTrialId)
            );
        }

        return () => {
            dispatch(clearSelectedTrial());
            dispatch(clearTrialError());
            dispatch(clearTrialSuccess());
        };
    }, [
        dispatch,
        numericTrialId
    ]);

    if (!user) {
        return (
            <section className="page-card">
                <h1>Authentication required</h1>

                <p>
                    Log in before updating a clinical
                    trial.
                </p>

                <button
                    type="button"
                    onClick={() => navigate("/login")}
                >
                    Go to login
                </button>
            </section>
        );
    }

    if (
        !Number.isInteger(numericTrialId)
        || numericTrialId <= 0
    ) {
        return (
            <section className="page-card">
                <h1>Invalid record ID</h1>

                <p>
                    The clinical-trial ID must be a
                    positive integer.
                </p>

                <button
                    type="button"
                    onClick={() => navigate("/")}
                >
                    Return home
                </button>
            </section>
        );
    }

    if (loading || sponsorsLoading) {
        return (
            <section className="page-card">
                <p role="status">
                    Loading clinical-trial information...
                </p>
            </section>
        );
    }

    if (sponsorsError) {
        return (
            <section className="page-card">
                <h1>Unable to load sponsors</h1>

                <p role="alert">
                    {sponsorsError}
                </p>

                <button
                    type="button"
                    onClick={() => navigate("/")}
                >
                    Return home
                </button>
            </section>
        );
    }

    if (error || !selectedTrial) {
        return (
            <section className="page-card">
                <h1>Unable to load the record</h1>

                <p role="alert">
                    {error || "Clinical trial not found."}
                </p>

                <button
                    type="button"
                    onClick={() => navigate("/")}
                >
                    Return home
                </button>
            </section>
        );
    }

    return (
        <LoadedUpdateForm
            key={selectedTrial.id}
            trial={selectedTrial}
            sponsors={sponsors}
        />
    );
}


export default UpdateRecord;