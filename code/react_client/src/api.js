"use strict";


export class ApiError extends Error {
    constructor(message, status) {
        super(message);

        this.name = "ApiError";
        this.status = status;
    }
}


const request = async (
    path,
    options = {}
) => {
    const response = await fetch(
        path,
        {
            credentials: "include",
            ...options,
            headers: {
                ...(options.body
                    ? {
                        "Content-Type":
                            "application/json"
                    }
                    : {}),
                ...(options.headers || {})
            }
        }
    );

    if (response.status === 204) {
        return null;
    }

    const contentType =
        response.headers.get(
            "content-type"
        ) || "";

    const data = contentType.includes(
        "application/json"
    )
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        let message = (
            `Request failed with status ` +
            `${response.status}.`
        );

        if (
            data
            && typeof data === "object"
            && data.detail
        ) {
            message = data.detail;
        } else if (
            typeof data === "string"
            && data.trim()
        ) {
            message = data;
        }

        throw new ApiError(
            message,
            response.status
        );
    }

    return data;
};


export const getCurrentUser = () => (
    request("/api/auth/me")
);


export const login = (
    email,
    password
) => (
    request(
        "/api/auth/login",
        {
            method: "POST",
            body: JSON.stringify({
                email,
                password
            })
        }
    )
);


export const logout = () => (
    request(
        "/api/auth/logout",
        {
            method: "POST"
        }
    )
);


export const getTrials = () => (
    request("/api/trials")
);


export const getTrial = (trialId) => (
    request(`/api/trials/${trialId}`)
);


export const createTrial = (
    trialData
) => (
    request(
        "/api/trials",
        {
            method: "POST",
            body: JSON.stringify(
                trialData
            )
        }
    )
);


export const updateTrial = (
    trialId,
    trialData
) => (
    request(
        `/api/trials/${trialId}`,
        {
            method: "PUT",
            body: JSON.stringify(
                trialData
            )
        }
    )
);


export const deleteTrial = (
    trialId
) => (
    request(
        `/api/trials/${trialId}`,
        {
            method: "DELETE"
        }
    )
);