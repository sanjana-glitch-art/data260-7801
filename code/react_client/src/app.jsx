import {
    useEffect,
    useState
} from "react";

import {
    Navigate,
    Route,
    Routes,
    useNavigate
} from "react-router-dom";

import Navigation from "./components/Navigation";
import CreateRecord from "./pages/CreateRecord";
import Home from "./pages/Home";
import Login from "./pages/Login";
import UpdateRecord from "./pages/UpdateRecord";

import {
    ApiError,
    getCurrentUser,
    login,
    logout
} from "./api";


function App() {
    const navigate = useNavigate();

    const [
        user,
        setUser
    ] = useState(null);

    const [
        authLoading,
        setAuthLoading
    ] = useState(true);

    useEffect(() => {
        let cancelled = false;

        const loadCurrentUser = async () => {
            try {
                const response = (
                    await getCurrentUser()
                );

                if (!cancelled) {
                    setUser(
                        response.user || response
                    );
                }
            } catch (error) {
                const unauthorized = (
                    error instanceof ApiError
                    && error.status === 401
                );

                if (
                    !cancelled
                    && !unauthorized
                ) {
                    console.error(
                        "Session check failed:",
                        error
                    );
                }

                if (!cancelled) {
                    setUser(null);
                }
            } finally {
                if (!cancelled) {
                    setAuthLoading(false);
                }
            }
        };

        loadCurrentUser();

        return () => {
            cancelled = true;
        };
    }, []);

    const handleLogin = async (
        email,
        password
    ) => {
        const response = await login(
            email,
            password
        );

        const loggedInUser = (
            response.user || response
        );

        setUser(loggedInUser);

        return loggedInUser;
    };

    const handleLogout = async () => {
        try {
            await logout();
        } catch (error) {
            console.error(
                "Logout request failed:",
                error
            );
        } finally {
            setUser(null);

            navigate(
                "/login",
                {
                    replace: true
                }
            );
        }
    };

    if (authLoading) {
        return (
            <div className="app-loading">
                Checking session...
            </div>
        );
    }

    return (
        <>
            <Navigation
                user={user}
                onLogout={handleLogout}
            />

            <Routes>
                <Route
                    path="/"
                    element={
                        <Home user={user} />
                    }
                />

                <Route
                    path="/login"
                    element={
                        <Login
                            user={user}
                            onLogin={handleLogin}
                        />
                    }
                />

                <Route
                    path="/trials/create"
                    element={
                        user
                            ? (
                                <CreateRecord
                                    user={user}
                                />
                            )
                            : (
                                <Navigate
                                    to="/login"
                                    replace
                                />
                            )
                    }
                />

                <Route
                    path="/trials/:trialId/update"
                    element={
                        user
                            ? (
                                <UpdateRecord
                                    user={user}
                                />
                            )
                            : (
                                <Navigate
                                    to="/login"
                                    replace
                                />
                            )
                    }
                />

                <Route
                    path="/create"
                    element={
                        <Navigate
                            to="/trials/create"
                            replace
                        />
                    }
                />

                <Route
                    path="*"
                    element={
                        <Navigate
                            to="/"
                            replace
                        />
                    }
                />
            </Routes>
        </>
    );
}


export default App;