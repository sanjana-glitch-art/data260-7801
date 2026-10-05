import {
    useEffect,
    useState
} from "react";

import {
    useDispatch,
    useSelector
} from "react-redux";

import {
    useNavigate
} from "react-router-dom";

import apiClient, {
    getApiError
} from "../api/client";

import TrialForm from "../components/TrialForm";

import {
    clearTrialError,
    clearTrialSuccess,
    createTrial
} from "../features/trials/trialsSlice";


const initialFormData = {
    trial_title: "",
    trial_code: "",
    sponsor_id: "",
    enrollment_target: "0",
    submitter_email: "",
    trial_description: "",
    trial_phase: "Phase I"
};


function CreateRecord({ user }) {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const {
        mutationLoading,
        error
    } = useSelector(
        (state) => state.trials
    );

    const [
        formData,
        setFormData
    ] = useState(initialFormData);

    const [
        sponsors,
        setSponsors
    ] = useState([]);

    const [
        sponsorsLoading,
        setSponsorsLoading
    ] = useState(true);

    const [
        sponsorsError,
        setSponsorsError
    ] = useState("");

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

        dispatch(clearTrialError());
        dispatch(clearTrialSuccess());

        loadSponsors();

        return () => {
            cancelled = true;
        };
    }, [dispatch]);

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
            sponsor_id: Number(
                formData.sponsor_id
            ),
            enrollment_target: Number(
                formData.enrollment_target
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
                createTrial(payload)
            ).unwrap();

            navigate("/");
        } catch {
            // Redux stores and displays the rejected
            // API request message.
        }
    };

    if (!user) {
        return (
            <section className="page-card">
                <h1>Authentication required</h1>

                <p>
                    Log in before creating a clinical
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

    if (sponsorsLoading) {
        return (
            <section className="page-card">
                <p role="status">
                    Loading sponsors...
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

    return (
        <section className="page-card">
            <div className="page-heading">
                <div>
                    <p className="eyebrow">
                        Create record
                    </p>

                    <h1>
                        Add a clinical trial
                    </h1>

                    <p>
                        Create a trial and connect it
                        to an existing sponsor.
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
                submitLabel="Add Clinical Trial"
                onChange={handleChange}
                onSubmit={handleSubmit}
                onCancel={() => navigate("/")}
            />
        </section>
    );
}


export default CreateRecord;