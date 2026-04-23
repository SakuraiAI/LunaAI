const SYSTEM_ACTION_TYPES = new Set([
  'open_app',
  'focus_window',
  'type_text',
  'mouse_click',
  'keyboard_input',
]);

export function routeThroughXeno({ visionResult, draftPlan }) {
  const nextPlan = {
    ...draftPlan,
    summaryParts: [...(draftPlan.summaryParts || [])],
  };

  // Xeno is the heavier reasoning layer: it validates safety and can tighten
  // the plan before anything reaches the execution layer.
  if (Array.isArray(visionResult?.tags) && visionResult.tags.includes('coding_screen')) {
    nextPlan.summaryParts.push('Xeno potvrzuje, ze otevreni debug panelu je nizkorizikova interni akce.');
    if (!nextPlan.action) {
      nextPlan.action = {
        type: 'click_internal_ui',
        target: 'open-share-debug-panel',
        args: {},
        requiresConfirmation: false,
      };
    }
  }

  if (nextPlan.action && SYSTEM_ACTION_TYPES.has(nextPlan.action.type)) {
    nextPlan.action = {
      ...nextPlan.action,
      requiresConfirmation: true,
    };
    nextPlan.confirmationRequest = {
      type: 'action_confirmation',
      message: 'Xeno oznacila tenhle krok jako systemovou akci, takze ceka na potvrzeni.',
      action: nextPlan.action,
      layer: 'system',
    };
    nextPlan.summaryParts.push('Xeno oznacila dalsi krok jako systemovou akci, ktera nesmi bezet automaticky.');
  }

  return nextPlan;
}
