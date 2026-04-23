export function routeThroughLuna({ userIntent, visionResult, draftPlan }) {
  const normalizedIntent = String(userIntent || '').toLowerCase();
  const nextPlan = {
    ...draftPlan,
    summaryParts: [...(draftPlan.summaryParts || [])],
  };

  // Luna is the user-facing layer: this is where immediate phrasing and
  // active intent can soften or redirect the draft action plan.
  if (normalizedIntent.includes('debug') && !nextPlan.action) {
    nextPlan.summaryParts.push('Luna zachytila primy zamer na debug workflow.');
    nextPlan.action = {
      type: 'click_internal_ui',
      target: 'open-share-debug-panel',
      args: {},
      requiresConfirmation: false,
    };
  }

  if (Array.isArray(visionResult?.tags) && visionResult.tags.includes('coding_screen')) {
    nextPlan.summaryParts.push('Luna vidi coding workspace a drzi navrh uvnitr bezpecne internich UI kroku.');
  }

  return nextPlan;
}
