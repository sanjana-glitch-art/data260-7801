function TrialForm({
    formData,
    sponsors,
    loading,
    submitLabel,
    onChange,
    onSubmit,
    onCancel
}) {
    return (
        <form
            className="record-form"
            onSubmit={onSubmit}
        >
            <div className="form-grid">
                <div className="form-field">
                    <label htmlFor="trial_title">
                        Trial title
                    </label>

                    <input
                        id="trial_title"
                        name="trial_title"
                        type="text"
                        value={formData.trial_title}
                        onChange={onChange}
                        required
                        autoFocus
                    />
                </div>

                <div className="form-field">
                    <label htmlFor="trial_code">
                        Unique trial code
                    </label>

                    <input
                        id="trial_code"
                        name="trial_code"
                        type="text"
                        value={formData.trial_code}
                        onChange={onChange}
                        placeholder="S7801-CT-005001"
                        pattern="[A-Za-z0-9_-]+"
                        required
                    />
                </div>

                <div className="form-field">
                    <label htmlFor="sponsor_id">
                        Sponsor
                    </label>

                    <select
                        id="sponsor_id"
                        name="sponsor_id"
                        value={formData.sponsor_id}
                        onChange={onChange}
                        required
                    >
                        <option value="">
                            Select a sponsor
                        </option>

                        {sponsors.map((sponsor) => (
                            <option
                                key={sponsor.id}
                                value={sponsor.id}
                            >
                                {sponsor.sponsor_name}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="form-field">
                    <label htmlFor="enrollment_target">
                        Enrollment target
                    </label>

                    <input
                        id="enrollment_target"
                        name="enrollment_target"
                        type="number"
                        min="0"
                        value={formData.enrollment_target}
                        onChange={onChange}
                        required
                    />
                </div>

                <div className="form-field">
                    <label htmlFor="submitter_email">
                        Submitter email
                    </label>

                    <input
                        id="submitter_email"
                        name="submitter_email"
                        type="email"
                        value={formData.submitter_email}
                        onChange={onChange}
                        required
                    />
                </div>

                <div className="form-field">
                    <label htmlFor="trial_phase">
                        Trial phase
                    </label>

                    <select
                        id="trial_phase"
                        name="trial_phase"
                        value={formData.trial_phase}
                        onChange={onChange}
                        required
                    >
                        <option value="Phase I">
                            Phase I
                        </option>

                        <option value="Phase II">
                            Phase II
                        </option>

                        <option value="Phase III">
                            Phase III
                        </option>

                        <option value="Phase IV">
                            Phase IV
                        </option>
                    </select>
                </div>

                <div className="form-field full-width">
                    <label htmlFor="trial_description">
                        Trial description
                    </label>

                    <textarea
                        id="trial_description"
                        name="trial_description"
                        value={formData.trial_description}
                        onChange={onChange}
                        rows="6"
                        minLength="26"
                        required
                    />
                </div>
            </div>

            <div className="form-actions">
                <button
                    className="primary-button"
                    type="submit"
                    disabled={loading}
                >
                    {loading
                        ? "Saving..."
                        : submitLabel}
                </button>

                <button
                    className="secondary-button"
                    type="button"
                    onClick={onCancel}
                    disabled={loading}
                >
                    Cancel
                </button>
            </div>
        </form>
    );
}


export default TrialForm;