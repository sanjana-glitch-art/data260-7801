import {
    configureStore
} from "@reduxjs/toolkit";

import trialsReducer from "../features/trials/trialsSlice";


const store = configureStore({
    reducer: {
        trials: trialsReducer
    }
});


export default store;