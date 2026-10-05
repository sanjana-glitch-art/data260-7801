import axios from "axios";


const apiClient = axios.create({
    baseURL: "/api",
    timeout: 20000,
    withCredentials: true,
    headers: {
        "Content-Type": "application/json"
    }
});


export const getApiError = (error) => {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => item.msg || "Validation error")
            .join("; ");
    }

    if (error.code === "ECONNABORTED") {
        return "The request timed out. Please try again.";
    }

    if (!error.response) {
        return (
            "Unable to reach the API. Confirm that the " +
            "FastAPI server is running on port 8601."
        );
    }

    return (
        error.message ||
        "An unexpected API error occurred."
    );
};


export default apiClient;