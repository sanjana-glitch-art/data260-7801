import {
    createAsyncThunk,
    createSlice
} from "@reduxjs/toolkit";

import apiClient, {
    getApiError
} from "../../api/client";


export const fetchTrials = createAsyncThunk(
    "trials/fetchTrials",
    async (
        {
            search = "",
            page = 1,
            pageSize = 10,
            sponsorId = null
        } = {},
        {
            rejectWithValue
        }
    ) => {
        try {
            const params = {
                page,
                page_size: pageSize
            };

            if (search.trim()) {
                params.search = search.trim();
            }

            if (sponsorId) {
                params.sponsor_id = sponsorId;
            }

            const response = await apiClient.get(
                "/trials",
                {
                    params
                }
            );

            return response.data;
        } catch (error) {
            return rejectWithValue(
                getApiError(error)
            );
        }
    }
);


export const fetchTrialById = createAsyncThunk(
    "trials/fetchTrialById",
    async (
        trialId,
        {
            rejectWithValue
        }
    ) => {
        try {
            const response = await apiClient.get(
                `/trials/${trialId}`
            );

            return response.data;
        } catch (error) {
            return rejectWithValue(
                getApiError(error)
            );
        }
    }
);


export const createTrial = createAsyncThunk(
    "trials/createTrial",
    async (
        trialData,
        {
            rejectWithValue
        }
    ) => {
        try {
            const response = await apiClient.post(
                "/trials",
                trialData
            );

            return response.data;
        } catch (error) {
            return rejectWithValue(
                getApiError(error)
            );
        }
    }
);


export const updateTrial = createAsyncThunk(
    "trials/updateTrial",
    async (
        {
            trialId,
            trialData
        },
        {
            rejectWithValue
        }
    ) => {
        try {
            const response = await apiClient.put(
                `/trials/${trialId}`,
                trialData
            );

            return response.data;
        } catch (error) {
            return rejectWithValue(
                getApiError(error)
            );
        }
    }
);


export const deleteTrial = createAsyncThunk(
    "trials/deleteTrial",
    async (
        trialId,
        {
            rejectWithValue
        }
    ) => {
        try {
            await apiClient.delete(
                `/trials/${trialId}`
            );

            return trialId;
        } catch (error) {
            return rejectWithValue(
                getApiError(error)
            );
        }
    }
);


const initialState = {
    items: [],
    selectedTrial: null,
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    loading: false,
    mutationLoading: false,
    error: "",
    successMessage: ""
};


const trialsSlice = createSlice({
    name: "trials",
    initialState,
    reducers: {
        clearTrialError: (state) => {
            state.error = "";
        },

        clearTrialSuccess: (state) => {
            state.successMessage = "";
        },

        clearSelectedTrial: (state) => {
            state.selectedTrial = null;
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(
                fetchTrials.pending,
                (state) => {
                    state.loading = true;
                    state.error = "";
                }
            )
            .addCase(
                fetchTrials.fulfilled,
                (state, action) => {
                    state.loading = false;

                    const payload = action.payload;

                    if (Array.isArray(payload)) {
                        state.items = payload;
                        state.total = payload.length;
                        state.page = 1;
                        state.pageSize = (
                            payload.length || 10
                        );
                        state.totalPages = 1;
                        return;
                    }

                    state.items = payload.items || [];
                    state.total = payload.total || 0;
                    state.page = payload.page || 1;
                    state.pageSize = (
                        payload.page_size || 10
                    );
                    state.totalPages = (
                        payload.total_pages || 1
                    );
                }
            )
            .addCase(
                fetchTrials.rejected,
                (state, action) => {
                    state.loading = false;
                    state.error = (
                        action.payload ||
                        "Unable to load trials."
                    );
                }
            )

            .addCase(
                fetchTrialById.pending,
                (state) => {
                    state.loading = true;
                    state.error = "";
                    state.selectedTrial = null;
                }
            )
            .addCase(
                fetchTrialById.fulfilled,
                (state, action) => {
                    state.loading = false;
                    state.selectedTrial = (
                        action.payload
                    );
                }
            )
            .addCase(
                fetchTrialById.rejected,
                (state, action) => {
                    state.loading = false;
                    state.error = (
                        action.payload ||
                        "Unable to load the trial."
                    );
                }
            )

            .addCase(
                createTrial.pending,
                (state) => {
                    state.mutationLoading = true;
                    state.error = "";
                    state.successMessage = "";
                }
            )
            .addCase(
                createTrial.fulfilled,
                (state, action) => {
                    state.mutationLoading = false;
                    state.items.unshift(
                        action.payload
                    );
                    state.total += 1;
                    state.successMessage = (
                        "Clinical trial created successfully."
                    );
                }
            )
            .addCase(
                createTrial.rejected,
                (state, action) => {
                    state.mutationLoading = false;
                    state.error = (
                        action.payload ||
                        "Unable to create the trial."
                    );
                }
            )

            .addCase(
                updateTrial.pending,
                (state) => {
                    state.mutationLoading = true;
                    state.error = "";
                    state.successMessage = "";
                }
            )
            .addCase(
                updateTrial.fulfilled,
                (state, action) => {
                    state.mutationLoading = false;
                    state.selectedTrial = (
                        action.payload
                    );

                    const index = (
                        state.items.findIndex(
                            (trial) => (
                                trial.id ===
                                action.payload.id
                            )
                        )
                    );

                    if (index !== -1) {
                        state.items[index] = (
                            action.payload
                        );
                    }

                    state.successMessage = (
                        "Clinical trial updated successfully."
                    );
                }
            )
            .addCase(
                updateTrial.rejected,
                (state, action) => {
                    state.mutationLoading = false;
                    state.error = (
                        action.payload ||
                        "Unable to update the trial."
                    );
                }
            )

            .addCase(
                deleteTrial.pending,
                (state) => {
                    state.mutationLoading = true;
                    state.error = "";
                    state.successMessage = "";
                }
            )
            .addCase(
                deleteTrial.fulfilled,
                (state, action) => {
                    state.mutationLoading = false;

                    state.items = state.items.filter(
                        (trial) => (
                            trial.id !==
                            action.payload
                        )
                    );

                    state.total = Math.max(
                        state.total - 1,
                        0
                    );

                    state.successMessage = (
                        "Clinical trial deleted successfully."
                    );
                }
            )
            .addCase(
                deleteTrial.rejected,
                (state, action) => {
                    state.mutationLoading = false;
                    state.error = (
                        action.payload ||
                        "Unable to delete the trial."
                    );
                }
            );
    }
});


export const {
    clearSelectedTrial,
    clearTrialError,
    clearTrialSuccess
} = trialsSlice.actions;


export default trialsSlice.reducer;