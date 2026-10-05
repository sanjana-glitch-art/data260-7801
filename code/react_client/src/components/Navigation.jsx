import {
    Link,
    NavLink
} from "react-router-dom";


function Navigation({
    user,
    onLogout
}) {
    const navigationClass = ({
        isActive
    }) => (
        isActive
            ? "nav-link active"
            : "nav-link"
    );

    return (
        <header className="site-header">
            <nav className="navigation">
                <Link
                    className="brand"
                    to="/"
                >
                    Clinical Trial Portal
                </Link>

                <div className="navigation-links">
                    <NavLink
                        className={navigationClass}
                        to="/"
                        end
                    >
                        Trial listings
                    </NavLink>

                    {user && (
                        <NavLink
                            className={navigationClass}
                            to="/trials/create"
                        >
                            Create trial
                        </NavLink>
                    )}

                    {user ? (
                        <>
                            <span className="signed-in-user">
                                {(
                                    user.display_name
                                    || user.email
                                    || user.username
                                )}
                            </span>

                            <button
                                className="logout-button"
                                type="button"
                                onClick={onLogout}
                            >
                                Log out
                            </button>
                        </>
                    ) : (
                        <NavLink
                            className={navigationClass}
                            to="/login"
                        >
                            Log in
                        </NavLink>
                    )}
                </div>
            </nav>
        </header>
    );
}


export default Navigation;