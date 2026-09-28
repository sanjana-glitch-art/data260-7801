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
import DeleteRecord from "./pages/DeleteRecord";
import Home from "./pages/Home";
import Login from "./pages/Login";
import UpdateRecord from "./pages/UpdateRecord";

import {
    ApiError,
    createTrial,
    deleteTrial,
    getCurrentUser,
    login,
    logout,
    updateTrial
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

    const [
        refreshKey,
        setRefreshKey
    ] = useState(0);

    useEffect(
        () => {
            let cancelled = false;

            const loadCurrentUser = async () => {
                try {
                    const response =
                        await getCurrentUser();

                    if (!cancelled) {
                        setUser(
                            response.user
                            || response
                        );
                    }
                } catch (error) {
                    if (
                        !cancelled
                        && !(
                            error
                            instanceof ApiError
                            && error.status === 401
                        )
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
        },
        []
    );

    const handleLogin = async (
        email,
        password
    ) => {
        const response = await login(
            email,
            password
        );

        const loggedInUser = (
            response.user
            || response
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

    const handleCreate = async (
        trialData
    ) => {
        const createdRecord =
            await createTrial(
                trialData
            );

        setRefreshKey(
            (currentValue) => (
                currentValue + 1
            )
        );

        return createdRecord;
    };

    const handleUpdate = async (
        trialId,
        trialData
    ) => {
        const updatedRecord =
            await updateTrial(
                trialId,
                trialData
            );

        setRefreshKey(
            (currentValue) => (
                currentValue + 1
            )
        );

        return updatedRecord;
    };

    const handleDelete = async (
        trialId
    ) => {
        await deleteTrial(trialId);

        setRefreshKey(
            (currentValue) => (
                currentValue + 1
            )
        );
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
                        <Home
                            user={user}
                            refreshKey={
                                refreshKey
                            }
                        />
                    }
                />

                <Route
                    path="/login"
                    element={
                        <Login
                            user={user}
                            onLogin={
                                handleLogin
                            }
                        />
                    }
                />

                <Route
                    path="/create"
                    element={
                        <CreateRecord
                            user={user}
                            onCreate={
                                handleCreate
                            }
                        />
                    }
                />

                <Route
                    path="/update"
                    element={
                        <UpdateRecord
                            user={user}
                            onUpdate={
                                handleUpdate
                            }
                        />
                    }
                />

                <Route
                    path="/update/:id"
                    element={
                        <UpdateRecord
                            user={user}
                            onUpdate={
                                handleUpdate
                            }
                        />
                    }
                />

                <Route
                    path="/delete"
                    element={
                        <DeleteRecord
                            user={user}
                            onDelete={
                                handleDelete
                            }
                        />
                    }
                />

                <Route
                    path="/delete/:id"
                    element={
                        <DeleteRecord
                            user={user}
                            onDelete={
                                handleDelete
                            }
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