import {
    Link,
    NavLink
} from "react-router-dom";


function Navigation({
    user,
    onLogout
}) {
    const linkClass = ({
        isActive
    }) => (
        isActive
            ? "nav-link active"
            : "nav-link"
    );

    return (
        <header className="site-header">
            <nav className="navbar">
                <Link
                    className="brand"
                    to="/"
                >
                    Clinical Trial Portal
                </Link>

                <div className="nav-links">
                    <NavLink
                        className={linkClass}
                        to="/"
                    >
                        Home
                    </NavLink>

                    {user && (
                        <NavLink
                            className={linkClass}
                            to="/create"
                        >
                            Add Record
                        </NavLink>
                    )}

                    {!user && (
                        <NavLink
                            className={linkClass}
                            to="/login"
                        >
                            Login
                        </NavLink>
                    )}

                    {user && (
                        <button
                            className="button-link"
                            type="button"
                            onClick={onLogout}
                        >
                            Logout
                        </button>
                    )}
                </div>
            </nav>
        </header>
    );
}


export default Navigation;