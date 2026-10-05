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


const initialValues = {
    trial_title: "",
    trial_code: "",
    enrollment_target: "0",
    sponsor_id: "",
    submitter_email: (
        "sanjana@example.edu"
    ),
    trial_description: "",
    trial_phase: "Phase I"
};


function CreateRecord() {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    const {
        mutationLoading,
        error
    } = useSelector(
        (state) => state.trials
    );

    const [values, setValues] = useState(
        initialValues
    );

    const [sponsors, setSponsors] = (
        useState([])
    );

    const [
        sponsorLoading,
        setSponsorLoading
    ] = useState(true);

    const [
        sponsorError,
        setSponsorError
    ] = useState("");


    useEffect(() => {
        let active = true;

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

                if (active) {
                    setSponsors(
                        response.data.items
                    );

                    setSponsorError("");
                }
            } catch (requestError) {
                if (active) {
                    setSponsorError(
                        getApiError(
                            requestError
                        )
                    );
                }
            } finally {
                if (active) {
                    setSponsorLoading(false);
                }
            }
        };

        dispatch(
            clearTrialError()
        );

        dispatch(
            clearTrialSuccess()
        );

        loadSponsors();

        return () => {
            active = false;
        };
    }, [dispatch]);


    const handleChange = (event) => {
        const {
            name,
            value
        } = event.target;

        setValues(
            (currentValues) => ({
                ...currentValues,
                [name]: value
            })
        );
    };


    const handleSubmit = async (
        event
    ) => {
        event.preventDefault();

        const payload = {
            ...values,
            trial_code: (
                values.trial_code
                    .trim()
                    .toUpperCase()
            ),
            enrollment_target: Number(
                values.enrollment_target
            ),
            sponsor_id: Number(
                values.sponsor_id
            )
        };

        try {
            await dispatch(
                createTrial(
                    payload
                )
            ).unwrap();

            navigate("/");
        } catch {
            // Redux stores and displays the API error.
        }
    };


    return (
        <main className="page-shell">
            <section className="panel">
                <p className="eyebrow">
                    REDUX CREATE THUNK
                </p>

                <h1>
                    Create a clinical trial
                </h1>

                <p>
                    Submit a new MySQL record through
                    the Redux Toolkit data layer.
                </p>

                {sponsorError && (
                    <div
                        className="error-message"
                        role="alert"
                    >
                        {sponsorError}
                    </div>
                )}

                {error && (
                    <div
                        className="error-message"
                        role="alert"
                    >
                        {error}
                    </div>
                )}

                {sponsorLoading ? (
                    <div className="state-message">
                        Loading sponsors...
                    </div>
                ) : sponsors.length === 0 ? (
                    <div className="error-message">
                        No sponsors are available.
                        Create a sponsor through the
                        API before creating a trial.
                    </div>
                ) : (
                    <TrialForm
                        values={values}
                        sponsors={sponsors}
                        loading={mutationLoading}
                        submitLabel="Create trial"
                        onChange={handleChange}
                        onSubmit={handleSubmit}
                        onCancel={() => {
                            navigate("/");
                        }}
                    />
                )}
            </section>
        </main>
    );
}


export default CreateRecord;