export function createSystemActions() {
    return {
        async execute(action) {
            return {
                ok: false,
                executed: false,
                message: `System action stub reached for ${action.type}. Hook OS automation here later.`,
                action,
            };
        },
    };
}
