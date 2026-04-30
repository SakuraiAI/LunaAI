import { routeThroughLuna } from './lunaRouter';
import { routeThroughXeno } from './xenoRouter';

function inferVisionTags({ description = '', label = '' } = {}) {
  const haystack = `${description}\n${label}`.toLowerCase();
  const tags = [];

  if (/\b(vscode|visual studio code|editor|terminal|debug|python|javascript|typescript|function|project explorer|coding|source file)\b/.test(haystack)) {
    tags.push('coding_screen');
  }

  if (/\b(settings|control panel|system settings|windows settings)\b/.test(haystack)) {
    tags.push('system_settings');
  }

  if (/\b(browser|chrome|edge|youtube|discord|web)\b/.test(haystack)) {
    tags.push('browser');
  }

  return tags;
}

export function createTaskPlanner() {
  return {
    plan({ userIntent = '', visionResult = {}, shareState = {} } = {}) {
      // Vision output enters the planning flow right here.
      // Luna and Xeno both receive the same visual result and can refine the plan in sequence.
      const description = String(visionResult?.description || '').trim();
      const tags = Array.isArray(visionResult?.tags) && visionResult.tags.length
        ? visionResult.tags
        : inferVisionTags({ description, label: shareState?.label || '' });

      let draftPlan = {
        ok: true,
        summaryParts: [],
        action: null,
        confirmationRequest: null,
        debug: {
          userIntent,
          visionDescription: description,
          tags,
          shareLabel: String(shareState?.label || ''),
        },
      };

      if (tags.includes('coding_screen')) {
        draftPlan.summaryParts.push('Rozpoznana coding obrazovka.');
        if (!shareState?.debugPanelOpen) {
          draftPlan.action = {
            type: 'click_internal_ui',
            target: 'open-share-debug-panel',
            args: {},
            requiresConfirmation: false,
          };
        }
      } else if (tags.includes('system_settings')) {
        draftPlan.summaryParts.push('Rozpoznana systemova nastaveni.');
        draftPlan.summaryParts.push('Systemovou aplikaci neoteviram ze samotneho vision kontextu bez jasneho prikazu uzivatele.');
      } else {
        draftPlan.summaryParts.push('Zatim nevidim jasny bezpecny krok pro automatickou akci.');
      }

      draftPlan = routeThroughLuna({ userIntent, visionResult: { ...visionResult, tags }, draftPlan });
      draftPlan = routeThroughXeno({ userIntent, visionResult: { ...visionResult, tags }, draftPlan });

      return {
        ok: true,
        summary: draftPlan.summaryParts.join('\n') || 'Zatim bez strukturovaneho navrhu.',
        action: draftPlan.action,
        confirmationRequest: draftPlan.confirmationRequest,
        debug: draftPlan.debug,
      };
    },
  };
}
