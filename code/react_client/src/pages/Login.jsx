import {
    useState
} from "react";

import {
    Navigate,
    useNavigate
} from "react-router-dom";


function Login({
    user,
    onLogin
}) {
    const navigate = useNavigate();

    const [
        email,
        setEmail
    ] = useState("");

    const [
        password,
        setPassword
    ] = useState("");

    const [
        error,
        setError
    ] = useState("");

    const [
        submitting,
        setSubmitting
    ] = useState(false);

    if (user) {
        return (
            <Navigate
                to="/"
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
            await onLogin(
                email.trim(),
                password
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
                || "Login failed."
            );
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <main className="page centered-page">
            <section className="card form-card">
                <p className="eyebrow">
                    Secure access
                </p>

                <h1>
                    Clinical Trial Login
                </h1>

                <p className="muted">
                    Enter your email and password
                    to manage clinical trials.
                </p>

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
                    <label htmlFor="email">
                        Email
                    </label>

                    <input
                        id="email"
                        name="email"
                        type="email"
                        value={email}
                        onChange={(event) => {
                            setEmail(
                                event.target.value
                            );
                        }}
                        autoComplete="email"
                        required
                        autoFocus
                    />

                    <label htmlFor="password">
                        Password
                    </label>

                    <input
                        id="password"
                        name="password"
                        type="password"
                        value={password}
                        onChange={(event) => {
                            setPassword(
                                event.target.value
                            );
                        }}
                        autoComplete={
                            "current-password"
                        }
                        required
                    />

                    <button
                        className="primary-button"
                        type="submit"
                        disabled={submitting}
                    >
                        {submitting
                            ? "Logging in..."
                            : "Log in"}
                    </button>
                </form>
            </section>
        </main>
    );
}


export default Login;